//! The binary evidence side file for the desktop (implementation plan 6.8):
//! per-plane maps written beside the output instead of as hex log lines.
//!
//! Format, little-endian, append-only:
//!
//! - Header: `"STRHEVD1"`, `u32 version`, `u32 levels`, per level
//!   `u16 lattice_w, u16 lattice_h, u32 extent_w, u32 extent_h` (the level's
//!   coefficient grid; level 0's is the analysis domain), `u32 frames_total`.
//! - Records: `u32 frame, u8 level, u8 kind, u16 reserved (0), u32 sequence,
//!   u32 payload_len`, then the payload. Kinds 0 (gate support) and 1
//!   (averaging, reserved: the stack's maps stay in the log) carry one bit
//!   per lattice site, row-major, least significant bit first, unused tail
//!   bits zero. Kinds 2 (focus energy) and 3 (gate floor) carry `f32 min,
//!   f32 max` and one quantised byte per site: the bytes the hex lines carried.
//! - `strehl stack --focus-evidence` (plan E5) appends a compact focus field
//!   at the end, on level 0's lattice with frame 0: kinds 7 (focus depth) and
//!   8 (focus share) carry `f32 min, f32 max` and one byte per site, kind 9
//!   (focus summary) at most [`MAX_SUMMARY_BYTES`]. Their sequences are the
//!   largest, after every plane map. Readers that predate them skip unknown
//!   kinds; every payload stays under their framing limit (`8 + 128 x 96`).
//!   See `merge_cmd/focus-evidence.rs` for their meaning.
//!
//! Every record kind, once ([`Kind`]; `evidence.strehl` and P2's
//! `live.strehl` share one numbering):
//!
//! | Kind | Record | File |
//! | --- | --- | --- |
//! | 0 | gate support | evidence |
//! | 1 | averaging map | evidence |
//! | 2 | focus energy | evidence |
//! | 3 | gate floor | evidence |
//! | 4 | coefficient | live (P2) |
//! | 5 | preview | live (P2) |
//! | 6 | preview's revision sample | evidence (P2) |
//! | 7 | focus depth | evidence (E5) |
//! | 8 | focus share | evidence (E5) |
//! | 9 | focus summary | evidence (E5) |
//!
//! Every accepted plane gets its gate-support maps. The float kinds are kept
//! for at most [`MAX_FLOAT_PLANES`] planes spread evenly through the stack
//! ([`float_kept`]), the desktop's own retention. The sequence is the
//! diagnostic sequence the log's stack maps also use, so the two sources
//! order as one stream.
//!
//! Like every observer here, the writer receives values the fold already
//! computed and returns nothing to it; it is created only when
//! `STREHL_UI_PROGRESS=1`. Output equality is checked by on/off/placebo
//! hashes (engineering ledger rule 26).

use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

/// The file's name inside the output's folder (the desktop's run folder).
pub(crate) const FILE_NAME: &str = "evidence.strehl";
pub(crate) const VERSION: u32 = 1;
/// Planes whose float maps are kept: `MAX_SURFACES` in the desktop's
/// `process-scales.rs`.
pub(crate) const MAX_FLOAT_PLANES: usize = 384;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
// Kinds 1 and 4-6 are named for the table; P2's writer uses them.
#[allow(dead_code)]
pub(crate) enum Kind {
    GateSupport = 0,
    Averaging = 1,
    FocusEnergy = 2,
    GateFloor = 3,
    Coefficient = 4,
    Preview = 5,
    PreviewSample = 6,
    FocusDepth = 7,
    FocusShare = 8,
    FocusSummary = 9,
}

impl Kind {
    /// Every kind, in number order (the module's table).
    #[cfg(test)]
    pub(crate) const ALL: [Kind; 10] = [
        Kind::GateSupport,
        Kind::Averaging,
        Kind::FocusEnergy,
        Kind::GateFloor,
        Kind::Coefficient,
        Kind::Preview,
        Kind::PreviewSample,
        Kind::FocusDepth,
        Kind::FocusShare,
        Kind::FocusSummary,
    ];
}

/// The longest focus summary payload.
pub(crate) const MAX_SUMMARY_BYTES: usize = 1090;

impl Kind {
    pub(crate) fn of(name: &str) -> Option<Self> {
        match name {
            "gate-support" => Some(Self::GateSupport),
            "focus-energy" => Some(Self::FocusEnergy),
            "gate-floor" => Some(Self::GateFloor),
            _ => None,
        }
    }
}

/// Whether `frame` of `total` keeps its float maps: the `MAX_FLOAT_PLANES`
/// planes `floor(j (total - 1) / (K - 1))`, `j < K`, first and last included.
pub(crate) fn float_kept(frame: usize, total: usize) -> bool {
    let kept = MAX_FLOAT_PLANES.min(total);
    if frame >= total {
        return false;
    }
    if kept == total {
        return true;
    }
    // The smallest j whose plane is at or after `frame`.
    let j = (frame * (kept - 1)).div_ceil(total - 1);
    j * (total - 1) / (kept - 1) == frame
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Header {
    /// Per level: lattice `[w, h]` and the level's coefficient grid.
    pub levels: Vec<([usize; 2], [usize; 2])>,
    pub frames: usize,
}

impl Header {
    fn bytes(&self) -> Vec<u8> {
        let mut bytes = b"STRHEVD1".to_vec();
        bytes.extend(VERSION.to_le_bytes());
        bytes.extend((self.levels.len() as u32).to_le_bytes());
        for (lattice, extent) in &self.levels {
            bytes.extend((lattice[0] as u16).to_le_bytes());
            bytes.extend((lattice[1] as u16).to_le_bytes());
            bytes.extend((extent[0] as u32).to_le_bytes());
            bytes.extend((extent[1] as u32).to_le_bytes());
        }
        bytes.extend((self.frames as u32).to_le_bytes());
        bytes
    }
}

/// One render pass's writer, owned by its [`crate::ui_progress::Progress`].
pub(crate) struct Writer {
    file: File,
    header: Header,
    path: PathBuf,
    failed: bool,
}

/// Files this process created, with their geometry: a render's later passes
/// (an optical-restoration retry, a calibrated fusion's second fold) append
/// to the same file when their geometry is the same, and otherwise keep
/// their maps in the log.
static CREATED: Mutex<Vec<(PathBuf, Header)>> = Mutex::new(Vec::new());

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Opened {
    /// The file was created here; the log should name it.
    Created,
    /// An earlier pass of this process created it with the same geometry.
    Joined,
}

impl Writer {
    /// Create the evidence file in `directory`, or join this process's file
    /// there when it has the same geometry.
    pub(crate) fn open(directory: &Path, header: Header) -> Result<(Self, Opened), String> {
        if header.levels.is_empty()
            || header.levels.len() > 64
            || header.frames == 0
            || header.frames > u32::MAX as usize
            || header.levels.iter().any(|(lattice, extent)| {
                lattice.iter().any(|&v| v == 0 || v > u16::MAX as usize)
                    || extent.iter().any(|&v| v == 0 || v > u32::MAX as usize)
            })
        {
            return Err("geometry outside the format".into());
        }
        let path = directory.join(FILE_NAME);
        let mut created = CREATED.lock().unwrap_or_else(|e| e.into_inner());
        let (file, opened) = match created.iter().find(|(known, _)| *known == path) {
            Some((_, known)) if *known == header => (
                std::fs::OpenOptions::new()
                    .append(true)
                    .open(&path)
                    .map_err(|e| format!("{}: {e}", path.display()))?,
                Opened::Joined,
            ),
            Some(_) => {
                return Err(format!(
                    "{} already holds another pass's geometry",
                    path.display()
                ));
            }
            None => {
                let mut file =
                    File::create(&path).map_err(|e| format!("{}: {e}", path.display()))?;
                file.write_all(&header.bytes())
                    .map_err(|e| format!("{}: {e}", path.display()))?;
                created.push((path.clone(), header.clone()));
                (file, Opened::Created)
            }
        };
        Ok((
            Self {
                file,
                header,
                path,
                failed: false,
            },
            opened,
        ))
    }

    /// Append one record. False if the file cannot take it (a lattice or
    /// identity its header does not describe, or a failed write); the caller
    /// then keeps the map in the log.
    pub(crate) fn append(
        &mut self,
        frame: usize,
        level: usize,
        kind: Kind,
        sequence: u64,
        payload: &[u8],
    ) -> bool {
        let mut record = Vec::with_capacity(16 + payload.len());
        self.encode(frame, level, kind, sequence, payload, &mut record) && self.write(&record)
    }

    /// Append one record's bytes to `out` (not yet written), or false if the
    /// header does not describe it.
    pub(crate) fn encode(
        &self,
        frame: usize,
        level: usize,
        kind: Kind,
        sequence: u64,
        payload: &[u8],
        out: &mut Vec<u8>,
    ) -> bool {
        let Some(&(lattice, _)) = self.header.levels.get(level) else {
            return false;
        };
        let sites = lattice[0] * lattice[1];
        let fits = match kind {
            Kind::GateSupport => payload.len() == sites.div_ceil(8),
            Kind::FocusEnergy | Kind::GateFloor => payload.len() == 8 + sites,
            // The focus field is one whole-run map on level 0's lattice.
            Kind::FocusDepth | Kind::FocusShare => {
                level == 0 && frame == 0 && payload.len() == 8 + sites
            }
            Kind::FocusSummary => level == 0 && frame == 0 && payload.len() <= MAX_SUMMARY_BYTES,
            // Written by P2's code paths, not this writer.
            Kind::Averaging | Kind::Coefficient | Kind::Preview | Kind::PreviewSample => false,
        };
        if self.failed || frame >= self.header.frames || !fits || sequence > u32::MAX as u64 {
            return false;
        }
        out.extend((frame as u32).to_le_bytes());
        out.extend([level as u8, kind as u8, 0, 0]);
        out.extend((sequence as u32).to_le_bytes());
        out.extend((payload.len() as u32).to_le_bytes());
        out.extend_from_slice(payload);
        true
    }

    /// Write whole encoded records in one call: a reader following the
    /// file's length sees whole records, except at most a torn tail it waits
    /// on. False, and no later writes, after a failure.
    pub(crate) fn write(&mut self, records: &[u8]) -> bool {
        if self.failed {
            return false;
        }
        if self.file.write_all(records).is_err() {
            self.failed = true;
            eprintln!(
                "evidence file   : writing {} failed; later per-plane maps stay in this log",
                self.path.display()
            );
            return false;
        }
        true
    }
}

/// The focus field's records, written in one call to `directory`'s evidence
/// file: appended to the file this process created there, or to a new file
/// with `header` (a render without the desktop's progress). `records` gets
/// level 0's lattice and returns `(kind, payload)` in order; their sequences
/// are the largest the format holds, after every plane map.
pub(crate) fn write_focus(
    directory: &Path,
    header: Header,
    records: impl FnOnce([usize; 2]) -> Vec<(Kind, Vec<u8>)>,
) -> Result<PathBuf, String> {
    let joined = CREATED
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .iter()
        .find(|(known, _)| *known == directory.join(FILE_NAME))
        .map(|(_, header)| header.clone());
    let (mut writer, _) = Writer::open(directory, joined.unwrap_or(header))?;
    let lattice = writer.header.levels[0].0;
    let records = records(lattice);
    let first = u32::MAX as u64 + 1 - records.len() as u64;
    let mut bytes = Vec::new();
    for (index, (kind, payload)) in records.iter().enumerate() {
        if !writer.encode(0, 0, *kind, first + index as u64, payload, &mut bytes) {
            return Err(format!("the evidence file cannot hold a {kind:?} record"));
        }
    }
    if writer.write(&bytes) {
        Ok(writer.path)
    } else {
        Err(format!("writing {} failed", writer.path.display()))
    }
}

/// Pack `pixels` (0 or 255 per site) into the format's bits.
pub(crate) fn pack_support(pixels: &[u8]) -> Vec<u8> {
    let mut bits = vec![0u8; pixels.len().div_ceil(8)];
    for (index, &value) in pixels.iter().enumerate() {
        if value == 255 {
            bits[index / 8] |= 1 << (index % 8);
        }
    }
    bits
}

#[cfg(test)]
#[path = "ui-evidence-tests.rs"]
mod tests;
