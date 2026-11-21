//! The engine's binary evidence side file, `<run>/evidence.strehl`
//! (implementation plan 6.8): the per-plane maps the engine used to print as
//! hex lines in the render log.
//!
//! Format, little-endian, append-only:
//!
//! - Header: `"STRHEVD1"`, `u32 version`, `u32 levels`, per level
//!   `u16 lattice_w, u16 lattice_h, u32 extent_w, u32 extent_h` (the level's
//!   coefficient grid; level 0's is the analysis domain), `u32 frames_total`.
//! - Records: `u32 frame, u8 level, u8 kind, u16 reserved, u32 sequence,
//!   u32 payload_len`, then the payload.
//!   - Kind 0, a plane's gate support: one bit per lattice site, row-major,
//!     least significant bit first.
//!   - Kinds 2 (focus energy) and 3 (gate floor): `f32 min, f32 max` and one
//!     quantised byte per site, the bytes the hex lines carried.
//!   - Kind 1, the stack's averaging map after an accepted plane: `u32
//!     folded`, then kind 0's bits.
//!   - Kind 6, that generation's coarse preview sampled at the revision
//!     lattice (`process-revision.rs`): `u32 folded, u16 preview_w, u16
//!     preview_h, u16 w, u16 h, f32 min, f32 max`, then `w x h` bytes. The
//!     revision trace needs every generation, but only these samples.
//!
//! The newest generation's coefficient maps and full preview, which views
//! only show newest, are in a side file the engine replaces whole
//! (`live.strehl`, [`LiveTail`], [`decode_live`]): `"STRHLIV1"`, `u32
//! version`, `u32 frames_total`, `u32 records`, then records framed as
//! above, kinds 4 (coefficient) and 5 (preview), payload `u32 folded, u16
//! w, u16 h, f32 min, f32 max` and `w x h` bytes.
//!
//! A set gate-support bit means the sampled kernel weight was positive at that
//! site, not that the plane won it or supplied a measured share of the blend.
//! The sequence is the engine's diagnostic sequence, shared with the stack
//! maps that stay in the log, so the two sources order as one stream.
//!
//! A run's file is tailed by length while the engine appends
//! ([`EvidenceTail`], on the render job's thread) and read whole on reopen
//! ([`read_into`]). A torn final record is held until it completes. A malformed
//! file stops being read; it never yields a partial or reinterpreted map.

use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};
use crate::process_provenance::{MaskBits, SAMPLE_LIMIT, WORDS};
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};

/// The file's name inside a run's folder; the engine's log line names it too.
pub(crate) const FILE_NAME: &str = "evidence.strehl";
pub(crate) const VERSION: u32 = 1;
/// The live side file's name, beside the evidence file.
pub(crate) const LIVE_FILE_NAME: &str = "live.strehl";
pub(crate) const LIVE_VERSION: u32 = 1;
const LIVE_MAGIC: [u8; 8] = *b"STRHLIV1";
/// The largest live file read: a 512 x 384 preview and 64 levels of
/// 128 x 96 coefficients, with framing, fit several times over.
const MAX_LIVE_BYTES: u64 = 8 << 20;
/// The revision lattice (`process-revision.rs` `WIDTH`, `HEIGHT`).
const REVISION_LATTICE: [usize; 2] = [64, 48];
const MAGIC: [u8; 8] = *b"STRHEVD1";
const MAX_LEVELS: usize = 64;
const MAX_FRAMES: usize = 65_536;
const RECORD_HEAD: usize = 16;
/// The largest payload any kind carries at the lattice limit; a longer
/// declared length means the framing cannot be trusted.
const MAX_PAYLOAD: usize = 8 + SAMPLE_LIMIT[0] * SAMPLE_LIMIT[1];
/// A reopened file larger than this is not read (about 50 times a 6,000-plane
/// run's file, DERIVED from 6.8's bounds).
const MAX_FILE_BYTES: u64 = 4 << 30;

/// One level's lattice and the grid it samples.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct LevelLattice {
    pub samples: [usize; 2],
    pub extent: [usize; 2],
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct EvidenceHeader {
    pub levels: Vec<LevelLattice>,
    pub frames_total: usize,
}

impl EvidenceHeader {
    /// The aligned analysis domain the archive's sample geometry refers to.
    pub(crate) fn analysis_extent(&self) -> [usize; 2] {
        self.levels[0].extent
    }
}

/// One decoded map, prepared off the UI thread: its display packet and, for
/// binary kinds, its bits packed as the archive and history keep them.
#[derive(Clone, Debug)]
pub(crate) struct EvidenceRecord {
    pub surface: DiagnosticSurface,
    pub packed: Option<PackedMask>,
    pub role: Role,
}

/// Where a record's map belongs.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Role {
    /// A plane's own map (kinds 0, 2, 3).
    Plane,
    /// The stack's averaging map after an accepted plane (kind 1).
    Averaging,
    /// A preview's revision sample (kind 6): for the revision trace only,
    /// never displayed as the preview.
    RevisionSample,
}

/// The newest generation's coefficient maps and coarse preview.
#[derive(Clone, Debug)]
pub(crate) struct LiveSet {
    pub frames_total: usize,
    pub surfaces: Vec<DiagnosticSurface>,
}

#[derive(Clone, Debug)]
pub(crate) struct PackedMask {
    pub bits: Box<MaskBits>,
    /// Set sites, so the history needs no second scan.
    pub on: u64,
}

/// Records decoded together, with the header they belong to, and possibly
/// a newer live generation.
#[derive(Clone, Debug)]
pub(crate) struct EvidenceBatch {
    pub header: Option<EvidenceHeader>,
    pub records: Vec<EvidenceRecord>,
    pub live: Option<LiveSet>,
}

/// Incremental decoder over the file's bytes in order.
#[derive(Default)]
pub(crate) struct EvidenceDecoder {
    header: Option<EvidenceHeader>,
    pending: Vec<u8>,
    failed: Option<String>,
    skipped: usize,
}

fn u16_at(bytes: &[u8], at: usize) -> usize {
    u16::from_le_bytes([bytes[at], bytes[at + 1]]) as usize
}

fn u32_at(bytes: &[u8], at: usize) -> u32 {
    u32::from_le_bytes(bytes[at..at + 4].try_into().expect("four bytes"))
}

fn f32_at(bytes: &[u8], at: usize) -> f32 {
    f32::from_le_bytes(bytes[at..at + 4].try_into().expect("four bytes"))
}

impl EvidenceDecoder {
    pub(crate) fn header(&self) -> Option<&EvidenceHeader> {
        self.header.as_ref()
    }

    /// Why decoding stopped, if it did.
    pub(crate) fn failure(&self) -> Option<&str> {
        self.failed.as_deref()
    }

    /// Well-framed records that were not maps this reader accepts (an unknown
    /// kind, an out-of-range identity or a payload that disagrees with its
    /// level's lattice). They are skipped, never reinterpreted.
    pub(crate) fn skipped(&self) -> usize {
        self.skipped
    }

    /// Decode every complete record in `bytes` (after any held tail) into
    /// `out`; a torn record waits for the next call.
    pub(crate) fn feed(&mut self, bytes: &[u8], out: &mut Vec<EvidenceRecord>) {
        if self.failed.is_some() {
            return;
        }
        self.pending.extend_from_slice(bytes);
        let mut at = 0;
        if self.header.is_none() {
            match self.parse_header() {
                Ok(Some(length)) => at = length,
                Ok(None) => return,
                Err(why) => {
                    self.fail(why);
                    return;
                }
            }
        }
        while self.pending.len() - at >= RECORD_HEAD {
            let head = &self.pending[at..at + RECORD_HEAD];
            let length = u32_at(head, 12) as usize;
            if length > MAX_PAYLOAD {
                self.fail(format!("a record declares {length} payload bytes"));
                return;
            }
            if self.pending.len() - at - RECORD_HEAD < length {
                break;
            }
            let end = at + RECORD_HEAD + length;
            match self.record(&self.pending[at..end]) {
                Some(record) => out.push(record),
                None => self.skipped += 1,
            }
            at = end;
        }
        self.pending.drain(..at);
    }

    fn fail(&mut self, why: String) {
        self.failed = Some(why);
        self.pending = Vec::new();
    }

    /// The header's length once it is complete.
    fn parse_header(&mut self) -> Result<Option<usize>, String> {
        let bytes = &self.pending;
        if bytes.len() < 16 {
            return Ok(None);
        }
        if bytes[..8] != MAGIC {
            return Err("not a Strehl evidence file".into());
        }
        let version = u32_at(bytes, 8);
        if version != VERSION {
            return Err(format!(
                "evidence format version {version} is not supported"
            ));
        }
        let levels = u32_at(bytes, 12) as usize;
        if levels == 0 || levels > MAX_LEVELS {
            return Err(format!("{levels} levels"));
        }
        let length = 16 + 12 * levels + 4;
        if bytes.len() < length {
            return Ok(None);
        }
        let mut lattices = Vec::with_capacity(levels);
        for level in 0..levels {
            let at = 16 + 12 * level;
            let lattice = LevelLattice {
                samples: [u16_at(bytes, at), u16_at(bytes, at + 2)],
                extent: [
                    u32_at(bytes, at + 4) as usize,
                    u32_at(bytes, at + 8) as usize,
                ],
            };
            if lattice.samples.contains(&0)
                || lattice.samples[0] > SAMPLE_LIMIT[0]
                || lattice.samples[1] > SAMPLE_LIMIT[1]
                || lattice.extent.contains(&0)
                || lattice.samples[0] > lattice.extent[0]
                || lattice.samples[1] > lattice.extent[1]
            {
                return Err(format!("level {level}'s lattice is out of range"));
            }
            lattices.push(lattice);
        }
        let frames_total = u32_at(bytes, length - 4) as usize;
        if frames_total == 0 || frames_total > MAX_FRAMES {
            return Err(format!("{frames_total} frames"));
        }
        self.header = Some(EvidenceHeader {
            levels: lattices,
            frames_total,
        });
        Ok(Some(length))
    }

    fn record(&self, bytes: &[u8]) -> Option<EvidenceRecord> {
        let header = self.header.as_ref()?;
        let frame = u32_at(bytes, 0) as usize;
        let level = bytes[4] as usize;
        let kind = bytes[5];
        let sequence = u64::from(u32_at(bytes, 8));
        let payload = &bytes[RECORD_HEAD..];
        let lattice = header.levels.get(level)?;
        if frame >= header.frames_total || sequence == 0 {
            return None;
        }
        let [width, height] = lattice.samples;
        let sites = width * height;
        let surface = |kind, scale, min, max, pixels: Vec<u8>| DiagnosticSurface {
            sequence,
            frame,
            level,
            kind,
            scope: DiagnosticScope::Frame,
            scale,
            width,
            height,
            min,
            max,
            pixels: pixels.into(),
            folded: 1,
        };
        match kind {
            0 => {
                if payload.len() != sites.div_ceil(8) {
                    return None;
                }
                let mut bits: Box<MaskBits> = Box::new([0; WORDS]);
                let mut pixels = vec![0u8; sites];
                let mut on = 0;
                for (index, pixel) in pixels.iter_mut().enumerate() {
                    if payload[index / 8] & (1 << (index % 8)) != 0 {
                        *pixel = 255;
                        bits[index / 64] |= 1 << (index % 64);
                        on += 1;
                    }
                }
                // Bits past the last site must be clear: a writer that set
                // them disagrees with its own lattice.
                if !sites.is_multiple_of(8) && payload[sites / 8] >> (sites % 8) != 0 {
                    return None;
                }
                Some(EvidenceRecord {
                    surface: surface(
                        DiagnosticKind::GateSupport,
                        DiagnosticScale::Linear,
                        0.0,
                        1.0,
                        pixels,
                    ),
                    packed: Some(PackedMask { bits, on }),
                    role: Role::Plane,
                })
            }
            1 => {
                let folded = u32_at(payload.get(..4)?, 0) as usize;
                let (packed, pixels) = unpack(&payload[4..], sites)?;
                if folded == 0 || folded > header.frames_total {
                    return None;
                }
                let mut packet = surface(
                    DiagnosticKind::Averaging,
                    DiagnosticScale::Linear,
                    0.0,
                    1.0,
                    pixels,
                );
                packet.scope = DiagnosticScope::Stack;
                packet.folded = folded;
                Some(EvidenceRecord {
                    surface: packet,
                    packed: Some(packed),
                    role: Role::Averaging,
                })
            }
            6 => {
                if payload.len() < 20 {
                    return None;
                }
                let folded = u32_at(payload, 0) as usize;
                let [pw, ph, w, h] = [4, 6, 8, 10].map(|at| u16_at(payload, at));
                let (min, max) = (f32_at(payload, 12), f32_at(payload, 16));
                if folded == 0
                    || folded > header.frames_total
                    || pw == 0
                    || ph == 0
                    || pw > 512
                    || ph > 384
                    || revision_lattice(pw, ph) != [w, h]
                    || payload.len() != 20 + w * h
                    || !min.is_finite()
                    || !max.is_finite()
                    || min > max
                {
                    return None;
                }
                Some(EvidenceRecord {
                    surface: DiagnosticSurface {
                        sequence,
                        frame,
                        level,
                        kind: DiagnosticKind::Preview,
                        scope: DiagnosticScope::Stack,
                        scale: DiagnosticScale::Linear,
                        width: w,
                        height: h,
                        min,
                        max,
                        pixels: payload[20..].to_vec().into(),
                        folded,
                    },
                    packed: None,
                    role: Role::RevisionSample,
                })
            }
            2 | 3 => {
                if payload.len() != 8 + sites {
                    return None;
                }
                let (min, max) = (f32_at(payload, 0), f32_at(payload, 4));
                if !min.is_finite() || !max.is_finite() || min > max || min < 0.0 {
                    return None;
                }
                let kind = if kind == 2 {
                    DiagnosticKind::FocusEnergy
                } else {
                    DiagnosticKind::GateFloor
                };
                Some(EvidenceRecord {
                    surface: surface(kind, DiagnosticScale::Log, min, max, payload[8..].to_vec()),
                    packed: None,
                    role: Role::Plane,
                })
            }
            // Unknown kinds are skipped.
            _ => None,
        }
    }
}

/// The revision lattice of a `width x height` preview, as
/// `process-revision.rs` `compare` derives it.
fn revision_lattice(width: usize, height: usize) -> [usize; 2] {
    let [mw, mh] = REVISION_LATTICE;
    let scale = (mw as f64 / width as f64)
        .min(mh as f64 / height as f64)
        .min(1.0);
    [
        (width as f64 * scale).floor().max(1.0) as usize,
        (height as f64 * scale).floor().max(1.0) as usize,
    ]
}

/// A binary payload's bits, packed for the archive, and its 0/255 pixels;
/// `None` if its length or tail bits disagree with `sites`.
fn unpack(payload: &[u8], sites: usize) -> Option<(PackedMask, Vec<u8>)> {
    if payload.len() != sites.div_ceil(8)
        || !sites.is_multiple_of(8) && payload[sites / 8] >> (sites % 8) != 0
    {
        return None;
    }
    let mut bits: Box<MaskBits> = Box::new([0; WORDS]);
    let mut pixels = vec![0u8; sites];
    let mut on = 0;
    for (index, pixel) in pixels.iter_mut().enumerate() {
        if payload[index / 8] & (1 << (index % 8)) != 0 {
            *pixel = 255;
            bits[index / 64] |= 1 << (index % 64);
            on += 1;
        }
    }
    Some((PackedMask { bits, on }, pixels))
}

/// Decode a whole live file. A file that does not parse completely yields
/// nothing: the engine publishes it whole, so a partial one is never shown.
pub(crate) fn decode_live(bytes: &[u8]) -> Result<LiveSet, String> {
    if bytes.len() < 20 || bytes[..8] != LIVE_MAGIC {
        return Err("not a Strehl live file".into());
    }
    let version = u32_at(bytes, 8);
    if version != LIVE_VERSION {
        return Err(format!("live format version {version} is not supported"));
    }
    let frames_total = u32_at(bytes, 12) as usize;
    let count = u32_at(bytes, 16) as usize;
    if frames_total == 0 || frames_total > MAX_FRAMES || count > 256 {
        return Err("live header out of range".into());
    }
    let mut surfaces = Vec::with_capacity(count);
    let mut at = 20;
    while at < bytes.len() {
        let head = bytes.get(at..at + RECORD_HEAD).ok_or("torn live record")?;
        let length = u32_at(head, 12) as usize;
        let payload = bytes
            .get(at + RECORD_HEAD..at + RECORD_HEAD + length)
            .ok_or("torn live record")?;
        at += RECORD_HEAD + length;
        let (frame, level, kind) = (u32_at(head, 0) as usize, head[4] as usize, head[5]);
        let sequence = u64::from(u32_at(head, 8));
        if payload.len() < 16 {
            return Err("short live record".into());
        }
        let folded = u32_at(payload, 0) as usize;
        let [w, h] = [4, 6].map(|at| u16_at(payload, at));
        let (min, max) = (f32_at(payload, 8), f32_at(payload, 12));
        let (kind, scale, limit) = match kind {
            4 => (
                DiagnosticKind::Coefficient,
                DiagnosticScale::Symmetric,
                SAMPLE_LIMIT,
            ),
            5 => (DiagnosticKind::Preview, DiagnosticScale::Linear, [512, 384]),
            _ => return Err(format!("live record of kind {kind}")),
        };
        if frame >= frames_total
            || level >= MAX_LEVELS
            || sequence == 0
            || folded == 0
            || folded > frames_total
            || w == 0
            || h == 0
            || w > limit[0]
            || h > limit[1]
            || payload.len() != 16 + w * h
            || !min.is_finite()
            || !max.is_finite()
            || min > max
        {
            return Err("live record out of range".into());
        }
        surfaces.push(DiagnosticSurface {
            sequence,
            frame,
            level,
            kind,
            scope: DiagnosticScope::Stack,
            scale,
            width: w,
            height: h,
            min,
            max,
            pixels: payload[16..].to_vec().into(),
            folded,
        });
    }
    if surfaces.len() != count {
        return Err("live record count disagrees".into());
    }
    Ok(LiveSet {
        frames_total,
        surfaces,
    })
}

/// A run's live file, re-read whenever its length or time changes: the
/// engine replaces it whole after each accepted generation.
pub(crate) struct LiveTail {
    path: PathBuf,
    seen: Option<(u64, Option<std::time::SystemTime>)>,
}

impl LiveTail {
    pub(crate) fn new(path: PathBuf) -> Self {
        Self { path, seen: None }
    }

    /// The live set, if the file changed since the last successful read. A
    /// missing or unreadable file is retried later, never an error.
    pub(crate) fn poll(&mut self) -> Option<LiveSet> {
        let metadata = std::fs::metadata(&self.path).ok()?;
        let stamp = (metadata.len(), metadata.modified().ok());
        if self.seen == Some(stamp) || stamp.0 > MAX_LIVE_BYTES {
            return None;
        }
        let set = std::fs::read(&self.path)
            .ok()
            .and_then(|bytes| decode_live(&bytes).ok())?;
        self.seen = Some(stamp);
        Some(set)
    }
}

/// Read a run's live file once (reopen).
pub(crate) fn read_live(path: &Path) -> anyhow::Result<LiveSet> {
    let mut file = File::open(path)?;
    anyhow::ensure!(
        file.metadata()?.len() <= MAX_LIVE_BYTES,
        "The live file exceeds its bound"
    );
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)?;
    decode_live(&bytes).map_err(anyhow::Error::msg)
}

/// A run's evidence file followed by its length, as `capture-follow.rs`
/// follows its journal: each poll reads at most a budget of new bytes.
pub(crate) struct EvidenceTail {
    path: PathBuf,
    file: Option<File>,
    offset: u64,
    decoder: EvidenceDecoder,
}

impl EvidenceTail {
    pub(crate) fn new(path: PathBuf) -> Self {
        Self {
            path,
            file: None,
            offset: 0,
            decoder: EvidenceDecoder::default(),
        }
    }

    /// Read up to `budget` new bytes. Returns the records they completed (or
    /// `None`) and whether more bytes were already waiting. A missing file
    /// is not an error: older engines and session renders write none.
    pub(crate) fn poll(&mut self, budget: usize) -> std::io::Result<(Option<EvidenceBatch>, bool)> {
        if self.decoder.failure().is_some() {
            return Ok((None, false));
        }
        let length = match std::fs::metadata(&self.path) {
            Ok(metadata) => metadata.len(),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok((None, false)),
            Err(error) => return Err(error),
        };
        if length <= self.offset {
            return Ok((None, false));
        }
        if self.file.is_none() {
            self.file = Some(File::open(&self.path)?);
        }
        let want = (length - self.offset).min(budget as u64) as usize;
        let mut bytes = vec![0; want];
        let mut read = 0;
        let file = self.file.as_mut().expect("opened above");
        while read < want {
            let count = file.read(&mut bytes[read..])?;
            if count == 0 {
                break;
            }
            read += count;
        }
        self.offset += read as u64;
        let mut records = Vec::new();
        self.decoder.feed(&bytes[..read], &mut records);
        let more = length > self.offset;
        let batch = self.decoder.header().cloned().map(|header| EvidenceBatch {
            header: Some(header),
            records,
            live: None,
        });
        Ok((batch.filter(|batch| !batch.records.is_empty()), more))
    }

    #[cfg(test)]
    pub(crate) fn decoder(&self) -> &EvidenceDecoder {
        &self.decoder
    }
}

/// The file a log's `event=evidence-file` line names, inside `directory`.
/// Only a plain file name is accepted: a log cannot point outside its run.
pub(crate) fn named_path(directory: &Path, name: &str) -> Option<PathBuf> {
    let plain = !name.is_empty()
        && name != "."
        && name != ".."
        && !name.contains(['/', '\\', ':'])
        && Path::new(name).file_name().is_some_and(|file| file == name);
    plain.then(|| directory.join(name))
}

/// Read a whole evidence file, handing each record to `each` with its header
/// as it is decoded, so memory stays one chunk plus one record.
pub(crate) fn read_into(
    path: &Path,
    cancelled: &AtomicBool,
    mut each: impl FnMut(&EvidenceHeader, EvidenceRecord),
) -> anyhow::Result<EvidenceSummary> {
    let mut file = File::open(path)?;
    anyhow::ensure!(
        file.metadata()?.len() <= MAX_FILE_BYTES,
        "The evidence file exceeds the replay limit"
    );
    let mut decoder = EvidenceDecoder::default();
    let mut buffer = vec![0u8; 1 << 20];
    let mut records = Vec::new();
    let mut summary = EvidenceSummary::default();
    loop {
        anyhow::ensure!(!cancelled.load(Ordering::Relaxed), "Replay cancelled");
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        decoder.feed(&buffer[..count], &mut records);
        if let Some(header) = decoder.header() {
            for record in records.drain(..) {
                summary.records += 1;
                each(header, record);
            }
        }
    }
    summary.skipped = decoder.skipped();
    summary.torn = decoder.pending.len();
    summary.failure = decoder.failure().map(str::to_owned);
    Ok(summary)
}

/// What a whole-file read found besides its records.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct EvidenceSummary {
    pub records: usize,
    pub skipped: usize,
    /// Bytes of an incomplete final record (an interrupted engine).
    pub torn: usize,
    pub failure: Option<String>,
}

#[cfg(test)]
#[path = "evidence-file-tests.rs"]
pub(crate) mod tests;
