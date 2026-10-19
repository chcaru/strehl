//! Bounded spatial history of actual per-capture admission masks.
//!
//! A set bit means the sampled kernel weight was positive, not that a capture
//! won, supplied a measured fraction, or improved quality. An observed zero is
//! distinct from a missing packet. Capture identities never use accepted counts.

use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};

const LEVELS: usize = 64;
pub(crate) const SAMPLE_LIMIT: [usize; 2] = [128, 96];
const WORDS: usize = SAMPLE_LIMIT[0] * SAMPLE_LIMIT[1] / u64::BITS as usize;
const MAX_ENTRIES: usize = 8192;

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

#[derive(Debug)]
struct Mask {
    level: usize,
    frame: usize,
    meta: AdmissionMeta,
    bits: [u64; WORDS],
}

/// A borrowed binary mask with real random skips. Map<Range> would evaluate
/// its mapping closure for every skipped sample when nth is called, defeating
/// the small-region reader used while the pointer moves across a photograph.
pub(crate) struct AdmissionCells<'a> {
    bits: &'a [u64; WORDS],
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

/// Sorted, fixed-size entries bound the payload and its indexing allocation.
/// At most 8192 masks are retained (under 14 MiB on the desktop target). New keys
/// at capacity are explicitly omitted; retained keys may still be refreshed.
/// Geometry changes clear only that level, never reinterpret its old samples.
#[derive(Debug)]
pub(crate) struct AdmissionArchive {
    entries: Vec<Mask>,
    scopes: [Option<LevelScope>; LEVELS],
    dropped: usize,
    resets: usize,
    revision: u64,
}

impl Default for AdmissionArchive {
    fn default() -> Self {
        Self {
            entries: Vec::new(),
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
        if !valid(packet, extent) {
            return;
        }
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
                self.entries.retain(|entry| entry.level != packet.level);
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
        let key = (packet.level, packet.frame);
        let position = self
            .entries
            .binary_search_by_key(&key, |entry| (entry.level, entry.frame));
        if let Ok(index) = position {
            if packet.sequence <= self.entries[index].meta.sequence {
                return;
            }
        } else if self.entries.len() == MAX_ENTRIES {
            self.dropped = self.dropped.saturating_add(1);
            return;
        }
        let mut bits = [0; WORDS];
        for (index, &value) in packet.pixels.iter().enumerate() {
            if value == 255 {
                bits[index / 64] |= 1u64 << (index % 64);
            }
        }
        let entry = Mask {
            level: packet.level,
            frame: packet.frame,
            meta: AdmissionMeta {
                sequence: packet.sequence,
                samples: domain.samples,
                extent: domain.extent,
            },
            bits,
        };
        match position {
            Ok(index) => self.entries[index] = entry,
            Err(index) => {
                // Doubling is explicit so the allocation never exceeds the cap,
                // including after removals caused by a level's domain change.
                if self.entries.len() == self.entries.capacity() {
                    let capacity = (self.entries.capacity().max(1) * 2).min(MAX_ENTRIES);
                    self.entries.reserve_exact(capacity - self.entries.len());
                }
                self.entries.insert(index, entry);
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
        let start = self.entries.partition_point(|entry| entry.level < level);
        self.entries[start..]
            .iter()
            .take_while(move |entry| entry.level == level)
            .map(|entry| entry.frame)
    }

    pub(crate) fn len(&self) -> usize {
        self.entries.len()
    }

    /// Capacity omissions count packets, not unique captures or refused inputs.
    pub(crate) fn dropped(&self) -> usize {
        self.dropped
    }

    /// Number of explicit per-level sampling-domain changes.
    pub(crate) fn resets(&self) -> usize {
        self.resets
    }

    /// Owned data storage, including spare vector capacity and inline state;
    /// allocator bookkeeping is not included. There are no per-entry allocations.
    #[cfg(test)]
    pub(crate) fn allocated_bytes(&self) -> usize {
        std::mem::size_of::<Self>() + self.entries.capacity() * std::mem::size_of::<Mask>()
    }

    fn entry(&self, level: usize, frame: usize) -> Option<&Mask> {
        self.entries
            .binary_search_by_key(&(level, frame), |entry| (entry.level, entry.frame))
            .ok()
            .map(|index| &self.entries[index])
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
        && packet.pixels.iter().all(|value| matches!(value, 0 | 255))
        && !extent.contains(&0)
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
