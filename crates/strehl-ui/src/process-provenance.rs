//! Bounded spatial history of actual per-capture admission masks.
//!
//! A set bit means the sampled kernel weight was positive, not that a capture
//! won, supplied a measured fraction, or improved quality. An observed zero is
//! distinct from a missing packet. Capture identities never use accepted counts.

use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};
use std::sync::Arc;

const LEVELS: usize = 64;
pub(crate) const SAMPLE_LIMIT: [usize; 2] = [128, 96];
pub(crate) const WORDS: usize = SAMPLE_LIMIT[0] * SAMPLE_LIMIT[1] / u64::BITS as usize;
/// Eight levels of 8,192 planes (plan 5.5 item 6): about 1.55 KiB a mask, so
/// about 100 MiB at the cap plus at most an eighth of growth slack (DERIVED;
/// MEASURED by `allocated_bytes` in the tests).
const MAX_ENTRIES: usize = 65_536;

/// One retained mask's sample bits, row-major, least significant bit first.
pub(crate) type MaskBits = [u64; WORDS];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct AdmissionMeta {
    pub sequence: u64,
    pub samples: [usize; 2],
    /// Dimensions of the aligned analysis domain, not original camera pixels.
    pub extent: [usize; 2],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Domain {
    samples: [usize; 2],
    extent: [usize; 2],
}

#[derive(Clone, Copy, Debug)]
struct LevelScope {
    domain: Domain,
    /// Before the first domain change, out-of-order distinct captures are valid.
    /// After a change, packets older than its starting sequence cannot return.
    start_sequence: u64,
    last_sequence: u64,
}

#[derive(Clone, Debug)]
struct Mask {
    frame: usize,
    meta: AdmissionMeta,
    bits: MaskBits,
}

/// A borrowed binary mask with real random skips. Map<Range> would evaluate
/// its mapping closure for every skipped sample when nth is called, defeating
/// the small-region reader used while the pointer moves across a photograph.
pub(crate) struct AdmissionCells<'a> {
    bits: &'a MaskBits,
    next: usize,
    end: usize,
    #[cfg(test)]
    reads: usize,
}
impl Iterator for AdmissionCells<'_> {
    type Item = bool;
    fn next(&mut self) -> Option<bool> {
        self.nth(0)
    }
    fn nth(&mut self, n: usize) -> Option<bool> {
        let Some(index) = self.next.checked_add(n).filter(|&index| index < self.end) else {
            self.next = self.end;
            return None;
        };
        self.next = index + 1;
        #[cfg(test)]
        {
            self.reads += 1;
        }
        Some(self.bits[index / 64] & (1u64 << (index % 64)) != 0)
    }
    fn size_hint(&self) -> (usize, Option<usize>) {
        let remaining = self.end - self.next;
        (remaining, Some(remaining))
    }
}
impl ExactSizeIterator for AdmissionCells<'_> {}
impl std::iter::FusedIterator for AdmissionCells<'_> {}
#[cfg(test)]
impl AdmissionCells<'_> {
    pub(crate) fn bit_reads(&self) -> usize {
        self.reads
    }
}

/// Fixed-size entries, sorted by capture within each level, bound the payload
/// and its indexing allocation. At most [`MAX_ENTRIES`] masks are retained in
/// all. New keys at capacity are explicitly omitted; retained keys may still be
/// refreshed. Geometry changes clear only that level, never reinterpret its old
/// samples.
///
/// Each level is its own vector, so a capture-ordered stream appends instead of
/// shifting every later level's masks, and clones share it: a probe task's copy
/// copies no masks, and the first later write to a level copies that level.
#[derive(Clone, Debug)]
pub(crate) struct AdmissionArchive {
    levels: [Option<Arc<Vec<Mask>>>; LEVELS],
    len: usize,
    scopes: [Option<LevelScope>; LEVELS],
    dropped: usize,
    resets: usize,
    revision: u64,
}

impl Default for AdmissionArchive {
    fn default() -> Self {
        Self {
            levels: [const { None }; LEVELS],
            len: 0,
            scopes: [None; LEVELS],
            dropped: 0,
            resets: 0,
            revision: 0,
        }
    }
}

impl AdmissionArchive {
    /// Call at packet ingestion, before the recent display-packet ring evicts.
    /// Invalid/stale packets cannot erase a previously observed zero or one.
    pub(crate) fn ingest(&mut self, packet: &DiagnosticSurface, extent: [usize; 2]) {
        if !valid(packet, extent) || !binary_pixels(packet) {
            return;
        }
        let mut bits = [0; WORDS];
        for (index, &value) in packet.pixels.iter().enumerate() {
            if value == 255 {
                bits[index / 64] |= 1u64 << (index % 64);
            }
        }
        self.store(packet, extent, &bits);
    }

    /// [`Self::ingest`] for a mask whose bits were packed off the UI thread
    /// (the evidence file's reader), so its pixels are not scanned again here.
    /// Bits beyond the packet's samples must be zero, as `counts` relies on.
    pub(crate) fn ingest_packed(
        &mut self,
        packet: &DiagnosticSurface,
        extent: [usize; 2],
        bits: &MaskBits,
    ) {
        let total = packet.width * packet.height;
        let tail_clear = bits.iter().enumerate().all(|(word, &value)| {
            let first = word * 64;
            if first >= total {
                value == 0
            } else if first + 64 > total {
                value >> (total - first) == 0
            } else {
                true
            }
        });
        if valid(packet, extent) && tail_clear {
            self.store(packet, extent, bits);
        }
    }

    fn store(&mut self, packet: &DiagnosticSurface, extent: [usize; 2], bits: &MaskBits) {
        let domain = Domain {
            samples: [packet.width, packet.height],
            extent,
        };
        let scope = &mut self.scopes[packet.level];
        match scope {
            Some(current) if current.domain != domain => {
                if packet.sequence <= current.last_sequence {
                    return;
                }
                if let Some(level) = self.levels[packet.level].take() {
                    self.len -= level.len();
                }
                *current = LevelScope {
                    domain,
                    start_sequence: packet.sequence,
                    last_sequence: packet.sequence,
                };
                self.resets = self.resets.saturating_add(1);
                self.revision = self.revision.wrapping_add(1);
            }
            Some(current) => {
                if packet.sequence < current.start_sequence {
                    return;
                }
                current.last_sequence = current.last_sequence.max(packet.sequence);
            }
            None => {
                *scope = Some(LevelScope {
                    domain,
                    start_sequence: 0,
                    last_sequence: packet.sequence,
                });
            }
        }
        let position = self.levels[packet.level].as_ref().map_or(Err(0), |level| {
            level.binary_search_by_key(&packet.frame, |entry| entry.frame)
        });
        match position {
            Ok(index) => {
                let retained = &self.levels[packet.level].as_ref().expect("found level")[index];
                if packet.sequence <= retained.meta.sequence {
                    return;
                }
            }
            Err(_) if self.len == MAX_ENTRIES => {
                self.dropped = self.dropped.saturating_add(1);
                return;
            }
            Err(_) => (),
        }
        let entry = Mask {
            frame: packet.frame,
            meta: AdmissionMeta {
                sequence: packet.sequence,
                samples: domain.samples,
                extent: domain.extent,
            },
            bits: *bits,
        };
        let room = MAX_ENTRIES - self.len;
        let level = Arc::make_mut(self.levels[packet.level].get_or_insert_with(Default::default));
        match position {
            Ok(index) => level[index] = entry,
            Err(index) => {
                // Growth is explicit and proportional (an eighth), never past
                // the global room, so spare capacity stays a small fraction of
                // the cap and a capture-ordered stream rarely reallocates.
                if level.len() == level.capacity() {
                    level.reserve_exact((level.len() / 8).clamp(1, room));
                }
                level.insert(index, entry);
                self.len += 1;
            }
        }
        self.revision = self.revision.wrapping_add(1);
    }

    /// Revision of retained observations. Rejected packets leave it unchanged;
    /// an actual domain reset changes it even if no replacement fits the cap.
    pub(crate) fn revision(&self) -> u64 {
        self.revision
    }

    /// Shared normalized aligned-domain pin. Finite outside coordinates clamp
    /// to its edge; NaN/infinity yield no observation. This reads the nearest
    /// transmitted coefficient centre, without interpolation or inferred
    /// neighbours. The observation can be spatially displaced from the pin;
    /// exact overlays use SampleGeometry::observed_index_at instead.
    pub(crate) fn sample(&self, level: usize, frame: usize, pin: [f32; 2]) -> Option<bool> {
        if pin.iter().any(|value| !value.is_finite()) {
            return None;
        }
        let entry = self.entry(level, frame)?;
        let geometry = crate::process_sample_glyphs::SampleGeometry::new(level, entry.meta)?;
        let index = geometry.nearest_index_at(eframe::egui::pos2(pin[0], pin[1]))?;
        Some(entry.bits[index / 64] & (1u64 << (index % 64)) != 0)
    }

    pub(crate) fn metadata(&self, level: usize, frame: usize) -> Option<AdmissionMeta> {
        self.entry(level, frame).map(|entry| entry.meta)
    }

    /// Exact retained positive/observed counts, without walking individual
    /// pixels. Unused tail bits are zeroed when a validated mask is ingested.
    pub(crate) fn counts(&self, level: usize, frame: usize) -> Option<(usize, usize)> {
        let entry = self.entry(level, frame)?;
        let total = entry.meta.samples[0] * entry.meta.samples[1];
        let admitted = entry.bits[..total.div_ceil(64)]
            .iter()
            .map(|word| word.count_ones() as usize)
            .sum();
        Some((admitted, total))
    }

    /// Exact rectangle in the retained sample lattice, counted a word at a
    /// time. Half-open ranges never include padding or adjacent row samples.
    pub(crate) fn window_counts(
        &self,
        level: usize,
        frame: usize,
        columns: [usize; 2],
        rows: [usize; 2],
    ) -> Option<(usize, usize)> {
        let entry = self.entry(level, frame)?;
        let [width, height] = entry.meta.samples;
        if columns[0] > columns[1] || columns[1] > width || rows[0] > rows[1] || rows[1] > height {
            return None;
        }
        let mut admitted = 0;
        for row in rows[0]..rows[1] {
            let mut start = row * width + columns[0];
            let end = row * width + columns[1];
            while start < end {
                let word_end = ((start / 64 + 1) * 64).min(end);
                let length = word_end - start;
                let mask = if length == 64 {
                    u64::MAX
                } else {
                    (1u64 << length) - 1
                };
                admitted += ((entry.bits[start / 64] >> (start % 64)) & mask).count_ones() as usize;
                start = word_end;
            }
        }
        Some((admitted, (columns[1] - columns[0]) * (rows[1] - rows[0])))
    }

    /// Exact retained binary samples in row-major order. This is the observed
    /// telemetry grid, not a full-resolution mask or a fractional blend weight.
    /// The iterator borrows storage without materialising another image.
    pub(crate) fn cells(
        &self,
        level: usize,
        frame: usize,
    ) -> Option<(AdmissionMeta, AdmissionCells<'_>)> {
        let entry = self.entry(level, frame)?;
        let count = entry.meta.samples[0] * entry.meta.samples[1];
        Some((
            entry.meta,
            AdmissionCells {
                bits: &entry.bits,
                next: 0,
                end: count,
                #[cfg(test)]
                reads: 0,
            },
        ))
    }

    pub(crate) fn levels(&self) -> impl Iterator<Item = usize> + '_ {
        self.scopes
            .iter()
            .enumerate()
            .filter_map(|(level, scope)| scope.is_some().then_some(level))
    }

    pub(crate) fn frames(&self, level: usize) -> impl Iterator<Item = usize> + '_ {
        self.levels
            .get(level)
            .and_then(Option::as_ref)
            .into_iter()
            .flat_map(|level| level.iter().map(|entry| entry.frame))
    }

    pub(crate) fn len(&self) -> usize {
        self.len
    }

    /// Capacity omissions count packets, not unique captures or refused inputs.
    pub(crate) fn dropped(&self) -> usize {
        self.dropped
    }

    /// Number of explicit per-level sampling-domain changes.
    pub(crate) fn resets(&self) -> usize {
        self.resets
    }

    /// Owned data storage, including spare vector capacity, each level's shared
    /// header and inline state; allocator bookkeeping is not included. There
    /// are no per-entry allocations.
    #[cfg(test)]
    pub(crate) fn allocated_bytes(&self) -> usize {
        std::mem::size_of::<Self>()
            + self
                .levels
                .iter()
                .flatten()
                .map(|level| {
                    2 * std::mem::size_of::<usize>()
                        + std::mem::size_of::<Vec<Mask>>()
                        + level.capacity() * std::mem::size_of::<Mask>()
                })
                .sum::<usize>()
    }

    /// Masks the retained vectors can hold without reallocating.
    #[cfg(test)]
    pub(crate) fn capacity(&self) -> usize {
        self.levels
            .iter()
            .flatten()
            .map(|level| level.capacity())
            .sum()
    }

    fn entry(&self, level: usize, frame: usize) -> Option<&Mask> {
        let level = self.levels.get(level)?.as_ref()?;
        level
            .binary_search_by_key(&frame, |entry| entry.frame)
            .ok()
            .map(|index| &level[index])
    }
}

fn valid(packet: &DiagnosticSurface, extent: [usize; 2]) -> bool {
    packet.kind == DiagnosticKind::GateSupport
        && packet.scope == DiagnosticScope::Frame
        && packet.scale == DiagnosticScale::Linear
        && packet.folded == 1
        && packet.sequence > 0
        && packet.frame < 65_536
        && packet.level < LEVELS
        && packet.min == 0.0
        && packet.max == 1.0
        && packet.width > 0
        && packet.width <= SAMPLE_LIMIT[0]
        && packet.height > 0
        && packet.height <= SAMPLE_LIMIT[1]
        && packet.pixels.len() == packet.width * packet.height
        && !extent.contains(&0)
}

fn binary_pixels(packet: &DiagnosticSurface) -> bool {
    packet.pixels.iter().all(|value| matches!(value, 0 | 255))
}

#[cfg(test)]
#[path = "process-provenance-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "process-provenance-iterator-tests.rs"]
mod iterator_tests;

#[cfg(test)]
#[path = "process-provenance-window-tests.rs"]
mod window_tests;
