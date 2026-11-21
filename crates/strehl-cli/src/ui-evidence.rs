//! The binary evidence side file for the desktop (implementation plan 6.8):
//! per-plane maps written beside the output instead of as hex log lines.
//!
//! Format, little-endian, append-only:
//!
//! - Header: `"STRHEVD1"`, `u32 version`, `u32 levels`, per level
//!   `u16 lattice_w, u16 lattice_h, u32 extent_w, u32 extent_h` (the level's
//!   coefficient grid; level 0's is the analysis domain), `u32 frames_total`.
//! - Records: `u32 frame, u8 level, u8 kind, u16 reserved (0), u32 sequence,
//!   u32 payload_len`, then the payload.
//!   - Kind 0, a plane's gate support: one bit per lattice site, row-major,
//!     least significant bit first, unused tail bits zero.
//!   - Kinds 2 (focus energy) and 3 (gate floor): `f32 min, f32 max` and one
//!     quantised byte per site, the bytes the hex lines carried.
//!   - Kind 1, the stack's averaging map after an accepted plane: `u32
//!     folded` (the accepted count it describes), then kind 0's bits.
//!   - Kind 6, the revision sample of that generation's coarse preview:
//!     `u32 folded, u16 preview_w, u16 preview_h, u16 w, u16 h, f32 min,
//!     f32 max`, then the preview's bytes at the desktop's revision lattice
//!     (`process-revision.rs`: at most 64 x 48, nearest sites). The desktop's
//!     revision trace needs every generation, but only these samples.
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
//! Every accepted plane gets its gate-support maps, and every accepted
//! generation its averaging maps and revision sample. The float kinds are
//! kept for at most [`MAX_FLOAT_PLANES`] planes spread evenly through the
//! stack ([`float_kept`]), the desktop's own retention. The sequence is the
//! diagnostic sequence the log's remaining maps also use, so the sources
//! order as one stream.
//!
//! The newest generation's coefficient maps and full coarse preview, which
//! the desktop only ever shows newest, are in a bounded side file replaced
//! whole ([`LiveWriter`], `live.strehl`): `"STRHLIV1"`, `u32 version`, `u32
//! frames_total`, `u32 records`, then records framed as above, kind 4
//! (coefficient) and 5 (preview) with the payload `u32 folded, u16 w, u16 h,
//! f32 min, f32 max` and `w x h` bytes. Before this file, those maps were
//! hex lines for every accepted plane: about 0.5 MB a plane of log.
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

/// The live side file's name, beside the evidence file.
pub(crate) const LIVE_FILE_NAME: &str = "live.strehl";
pub(crate) const LIVE_VERSION: u32 = 1;

/// The desktop's revision lattice (`process-revision.rs` `WIDTH`, `HEIGHT`).
pub(crate) const REVISION_LATTICE: [usize; 2] = [64, 48];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
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

/// The nearest sites of a `width x height` preview at the revision lattice,
/// as the desktop's `process-revision.rs` `compare` takes them.
pub(crate) fn revision_sites(width: usize, height: usize) -> ([usize; 2], Vec<usize>) {
    let [mw, mh] = REVISION_LATTICE;
    let scale = (mw as f64 / width as f64)
        .min(mh as f64 / height as f64)
        .min(1.0);
    let w = (width as f64 * scale).floor().max(1.0) as usize;
    let h = (height as f64 * scale).floor().max(1.0) as usize;
    let mut sites = Vec::with_capacity(w * h);
    for y in 0..h {
        let source_y = ((2 * y + 1) * height / (2 * h)).min(height - 1);
        for x in 0..w {
            let source_x = ((2 * x + 1) * width / (2 * w)).min(width - 1);
            sites.push(source_y * width + source_x);
        }
    }
    ([w, h], sites)
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
        let u16_at = |at: usize| {
            payload
                .get(at..at + 2)
                .map(|b| u16::from_le_bytes([b[0], b[1]]))
        };
        let fits = match kind {
            Kind::GateSupport => payload.len() == sites.div_ceil(8),
            Kind::FocusEnergy | Kind::GateFloor => payload.len() == 8 + sites,
            Kind::Averaging => payload.len() == 4 + sites.div_ceil(8),
            Kind::PreviewSample => match (u16_at(8), u16_at(10)) {
                (Some(w), Some(h))
                    if usize::from(w) <= REVISION_LATTICE[0]
                        && usize::from(h) <= REVISION_LATTICE[1] =>
                {
                    payload.len() == 20 + usize::from(w) * usize::from(h)
                }
                _ => false,
            },
            // The focus field is one whole-run map on level 0's lattice.
            Kind::FocusDepth | Kind::FocusShare => {
                level == 0 && frame == 0 && payload.len() == 8 + sites
            }
            Kind::FocusSummary => level == 0 && frame == 0 && payload.len() <= MAX_SUMMARY_BYTES,
            // The live file's kinds.
            Kind::Coefficient | Kind::Preview => false,
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

/// The live side file: the newest accepted generation's coefficient maps and
/// coarse preview, gathered while the generation is observed and published
/// whole by a rename, so a reader sees one complete generation or the one
/// before. Owned by one render pass's [`crate::ui_progress::Progress`].
pub(crate) struct LiveWriter {
    path: PathBuf,
    staging: PathBuf,
    frames: usize,
    /// The generation being gathered: encoded records and their count.
    records: Vec<u8>,
    count: u32,
    /// A gathered generation the last rename could not publish (a reader
    /// held the file without delete sharing); retried at the next commit.
    unpublished: bool,
}

impl LiveWriter {
    pub(crate) fn open(directory: &Path, frames: usize) -> Result<Self, String> {
        if frames == 0 || frames > u32::MAX as usize {
            return Err("frame count outside the format".into());
        }
        let path = directory.join(LIVE_FILE_NAME);
        let staging = directory.join(format!("{LIVE_FILE_NAME}.partial"));
        // A previous pass's or render's newest generation is not this one's.
        match std::fs::remove_file(&path) {
            Ok(()) => (),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(e) => return Err(format!("{}: {e}", path.display())),
        }
        Ok(Self {
            path,
            staging,
            frames,
            records: Vec::new(),
            count: 0,
            unpublished: false,
        })
    }

    /// Gather one map of the current generation: kind 4 or 5, `w x h` bytes.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn add(
        &mut self,
        frame: usize,
        level: usize,
        kind: Kind,
        sequence: u64,
        folded: usize,
        size: [usize; 2],
        range: (f32, f32),
        pixels: &[u8],
    ) -> bool {
        if !matches!(kind, Kind::Coefficient | Kind::Preview)
            || frame >= self.frames
            || level > u8::MAX as usize
            || sequence > u32::MAX as u64
            || folded > u32::MAX as usize
            || size.iter().any(|&v| v == 0 || v > u16::MAX as usize)
            || pixels.len() != size[0] * size[1]
        {
            return false;
        }
        let length = 16 + pixels.len();
        self.records.extend((frame as u32).to_le_bytes());
        self.records.extend([level as u8, kind as u8, 0, 0]);
        self.records.extend((sequence as u32).to_le_bytes());
        self.records.extend((length as u32).to_le_bytes());
        self.records.extend((folded as u32).to_le_bytes());
        self.records.extend((size[0] as u16).to_le_bytes());
        self.records.extend((size[1] as u16).to_le_bytes());
        self.records.extend(range.0.to_le_bytes());
        self.records.extend(range.1.to_le_bytes());
        self.records.extend_from_slice(pixels);
        self.count += 1;
        true
    }

    /// Publish the gathered generation. With `last` (the fold has ended), a
    /// rename a reader is holding up is retried for up to half a second, so
    /// the final generation is the one left on disk. False on an I/O failure.
    pub(crate) fn commit(&mut self, last: bool) -> bool {
        if self.count > 0 {
            let mut bytes = Vec::with_capacity(16 + self.records.len());
            bytes.extend_from_slice(b"STRHLIV1");
            bytes.extend(LIVE_VERSION.to_le_bytes());
            bytes.extend((self.frames as u32).to_le_bytes());
            bytes.extend(self.count.to_le_bytes());
            bytes.extend_from_slice(&self.records);
            self.records.clear();
            self.count = 0;
            if std::fs::write(&self.staging, &bytes).is_err() {
                return false;
            }
            self.unpublished = true;
        }
        let attempts = if last { 20 } else { 1 };
        for attempt in 0..attempts {
            if !self.unpublished {
                break;
            }
            if attempt > 0 {
                std::thread::sleep(std::time::Duration::from_millis(25));
            }
            self.unpublished = std::fs::rename(&self.staging, &self.path).is_err();
        }
        true
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
