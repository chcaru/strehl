//! Bounded original active-u16 CFA cache for opt-in multi-pass processing.
//!
//! The resident budget covers retained u16 samples, including pinned handles.
//! Decoder scratch, metadata, fixed 64-KiB I/O scratch, green guides and a caller's
//! reconstructed Frame are separate working allocations. No aligned frames,
//! f32 pixels or synthetic padding are stored on disk.
use crate::session_input::{ResolvedSession, SourceFrame, SourceIdentity, hex};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use strehl_core::noise::Levels;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_raw::{Frame, Region};

const MAGIC: &[u8; 8] = b"STRHCFA1";
const CACHE_VERSION: u32 = 1;
const MAX_HEADER_BYTES: usize = 256 * 1024;
static TEMP_SEQUENCE: AtomicU64 = AtomicU64::new(0);

pub type CacheResult<T> = std::result::Result<T, CacheError>;

#[derive(Debug)]
pub enum CacheError {
    Io {
        path: PathBuf,
        source: std::io::Error,
    },
    Corrupt {
        path: PathBuf,
        message: String,
    },
    Stale {
        path: PathBuf,
        message: String,
    },
    Budget {
        requested_bytes: usize,
        budget_bytes: usize,
        pinned_bytes: usize,
    },
    Invalid(String),
    Decode {
        path: PathBuf,
        message: String,
    },
}
impl fmt::Display for CacheError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io { path, source } => write!(f, "source cache I/O {}: {source}", path.display()),
            Self::Corrupt { path, message } => {
                write!(f, "corrupt source cache {}: {message}", path.display())
            }
            Self::Stale { path, message } => {
                write!(f, "stale source/cache {}: {message}", path.display())
            }
            Self::Budget {
                requested_bytes,
                budget_bytes,
                pinned_bytes,
            } => write!(
                f,
                "source cache needs {requested_bytes} bytes with {pinned_bytes} bytes pinned, exceeding {budget_bytes}-byte CFA budget"
            ),
            Self::Invalid(message) => write!(f, "invalid source cache request: {message}"),
            Self::Decode { path, message } => {
                write!(f, "source decode {}: {message}", path.display())
            }
        }
    }
}
impl std::error::Error for CacheError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            _ => None,
        }
    }
}
fn io(path: &Path, source: std::io::Error) -> CacheError {
    CacheError::Io {
        path: path.to_path_buf(),
        source,
    }
}
fn corrupt(path: &Path, message: impl Into<String>) -> CacheError {
    CacheError::Corrupt {
        path: path.to_path_buf(),
        message: message.into(),
    }
}
fn stale(identity: &SourceIdentity, message: impl Into<String>) -> CacheError {
    CacheError::Stale {
        path: identity.path.clone(),
        message: message.into(),
    }
}

/// Original decoder coordinates, retained even though payload contains only the
/// active rectangle. Reconstructing a Frame restores these offsets exactly.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CachedGeometry {
    pub stride: usize,
    pub buffer_height: usize,
    pub active_x: usize,
    pub active_y: usize,
    pub width: usize,
    pub height: usize,
}
impl CachedGeometry {
    pub fn active(&self) -> Region {
        Region {
            x: self.active_x,
            y: self.active_y,
            width: self.width,
            height: self.height,
        }
    }
    fn sample_count(&self) -> Option<usize> {
        self.width.checked_mul(self.height)
    }
    pub fn full_frame_bytes(&self) -> Option<usize> {
        self.stride.checked_mul(self.buffer_height)?.checked_mul(2)
    }
    fn validate(&self) -> std::result::Result<(), String> {
        if self.width == 0 || self.height == 0 || self.stride == 0 || self.buffer_height == 0 {
            return Err("zero-sized source geometry".into());
        }
        if self
            .active_x
            .checked_add(self.width)
            .is_none_or(|x| x > self.stride)
            || self
                .active_y
                .checked_add(self.height)
                .is_none_or(|y| y > self.buffer_height)
            || self.sample_count().and_then(|n| n.checked_mul(2)).is_none()
            || self.full_frame_bytes().is_none()
        {
            return Err("source active rectangle overflows its original buffer".into());
        }
        Ok(())
    }
}

/// Float metadata is encoded as IEEE-754 bits, preserving decoder NaNs (notably
/// WB's unused fourth entry) and every supplied calibration value exactly.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CachedFrameMetadata {
    pub black_bits: u32,
    pub white_bits: u32,
    pub iso_bits: Option<u32>,
    pub wb_bits: [u32; 4],
    pub xyz_to_cam_bits: [[u32; 3]; 4],
    pub color_matrices_bits: Vec<(String, [[u32; 3]; 3])>,
    pub camera: String,
}
impl CachedFrameMetadata {
    fn from_frame(frame: &Frame) -> Self {
        Self {
            black_bits: frame.levels.black.to_bits(),
            white_bits: frame.levels.white.to_bits(),
            iso_bits: frame.iso.map(f32::to_bits),
            wb_bits: frame.wb_coeffs.map(f32::to_bits),
            xyz_to_cam_bits: frame.xyz_to_cam_rgbe.map(|row| row.map(f32::to_bits)),
            color_matrices_bits: frame
                .color_matrices
                .iter()
                .map(|(name, matrix)| (name.clone(), matrix.map(|row| row.map(f32::to_bits))))
                .collect(),
            camera: frame.camera.clone(),
        }
    }
    fn validate(&self) -> std::result::Result<(), String> {
        let black = f32::from_bits(self.black_bits);
        let white = f32::from_bits(self.white_bits);
        if !black.is_finite()
            || !white.is_finite()
            || black < 0.0
            || white <= black
            || white > 65535.0
        {
            return Err("invalid decoded sensor levels".into());
        }
        if self.iso_bits.is_some_and(|v| {
            let iso = f32::from_bits(v);
            !iso.is_finite() || iso <= 0.0
        }) {
            return Err("invalid decoded ISO".into());
        }
        if self.camera.len() > 4096
            || self.color_matrices_bits.len() > 64
            || self
                .color_matrices_bits
                .iter()
                .any(|(name, _)| name.len() > 4096)
        {
            return Err("oversized decoder metadata".into());
        }
        Ok(())
    }
}

#[derive(Debug, Clone)]
pub struct CachedSource {
    pub identity: SourceIdentity,
    pub geometry: CachedGeometry,
    pub metadata: CachedFrameMetadata,
    /// Original active-area samples, row-major, never warped or black-subtracted.
    pub data: Vec<u16>,
}
impl CachedSource {
    pub fn cfa_bytes(&self) -> usize {
        self.data.len() * 2
    }
    pub fn levels(&self) -> Levels {
        Levels {
            black: f32::from_bits(self.metadata.black_bits),
            white: f32::from_bits(self.metadata.white_bits),
        }
    }
    pub fn iso(&self) -> Option<f32> {
        self.metadata.iso_bits.map(f32::from_bits)
    }
    pub fn camera(&self) -> &str {
        &self.metadata.camera
    }
    pub fn active_row(&self, y: usize) -> &[u16] {
        &self.data[y * self.geometry.width..(y + 1) * self.geometry.width]
    }
    /// Restore original active offsets/stride for legacy consumers. Padding is
    /// synthetic zero, never evidence. The caller explicitly budgets this copy.
    pub fn to_frame(&self, max_allocation_bytes: usize) -> CacheResult<Frame> {
        let bytes = self
            .geometry
            .full_frame_bytes()
            .ok_or_else(|| CacheError::Invalid("full frame allocation overflows".into()))?;
        if bytes > max_allocation_bytes {
            return Err(CacheError::Budget {
                requested_bytes: bytes,
                budget_bytes: max_allocation_bytes,
                pinned_bytes: 0,
            });
        }
        let mut data = Vec::new();
        data.try_reserve_exact(bytes / 2)
            .map_err(|error| CacheError::Invalid(format!("frame allocation: {error}")))?;
        data.resize(bytes / 2, 0);
        for y in 0..self.geometry.height {
            let start =
                (self.geometry.active_y + y) * self.geometry.stride + self.geometry.active_x;
            data[start..start + self.geometry.width].copy_from_slice(self.active_row(y));
        }
        Ok(Frame {
            data,
            stride: self.geometry.stride,
            buffer_height: self.geometry.buffer_height,
            active: self.geometry.active(),
            levels: self.levels(),
            iso: self.iso(),
            wb_coeffs: self.metadata.wb_bits.map(f32::from_bits),
            xyz_to_cam_rgbe: self
                .metadata
                .xyz_to_cam_bits
                .map(|row| row.map(f32::from_bits)),
            color_matrices: self
                .metadata
                .color_matrices_bits
                .iter()
                .map(|(name, matrix)| (name.clone(), matrix.map(|row| row.map(f32::from_bits))))
                .collect(),
            camera: self.metadata.camera.clone(),
            path: self.identity.path.clone(),
        })
    }
}
impl QuadSource for CachedSource {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry::from_active(self.geometry.width, self.geometry.height)
    }
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        (self.active_row(2 * py), self.active_row(2 * py + 1))
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Header {
    version: u32,
    decoder_key: String,
    source: SourceIdentity,
    cfa: String,
    geometry: CachedGeometry,
    metadata: CachedFrameMetadata,
}
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct CacheStats {
    pub resident_cfa_bytes: usize,
    pub peak_resident_cfa_bytes: usize,
    pub memory_hits: u64,
    pub disk_hits: u64,
    pub decodes: u64,
}
struct Entry {
    source: Arc<CachedSource>,
    last_use: u64,
}
pub struct SourceCache {
    root: PathBuf,
    session: ResolvedSession,
    decoder_key: String,
    budget: usize,
    entries: HashMap<String, Entry>,
    clock: u64,
    stats: CacheStats,
}
impl SourceCache {
    pub fn new(
        root: &Path,
        session: &ResolvedSession,
        resident_cfa_budget_bytes: usize,
    ) -> CacheResult<Self> {
        if resident_cfa_budget_bytes == 0 {
            return Err(CacheError::Invalid(
                "resident CFA budget must be positive".into(),
            ));
        }
        let root = session
            .ensure_output_outside_sources(root)
            .map_err(|e| CacheError::Invalid(e.to_string()))?;
        fs::create_dir_all(&root).map_err(|e| io(&root, e))?;
        let root = session
            .ensure_output_outside_sources(&root)
            .map_err(|e| CacheError::Invalid(e.to_string()))?;
        if !root.is_dir() {
            return Err(CacheError::Invalid("cache root is not a directory".into()));
        }
        let mut hasher = Sha256::new();
        hasher.update(b"strehl-original-active-cfa-v1");
        hasher.update(include_bytes!("../../../Cargo.lock"));
        hasher.update(include_bytes!("../../strehl-raw/src/lib.rs"));
        let decoder_key = hex(&hasher.finalize());
        Ok(Self {
            root,
            session: session.clone(),
            decoder_key,
            budget: resident_cfa_budget_bytes,
            entries: HashMap::new(),
            clock: 0,
            stats: CacheStats::default(),
        })
    }
    pub fn stats(&self) -> CacheStats {
        self.stats
    }
    pub fn budget_bytes(&self) -> usize {
        self.budget
    }
    pub fn root(&self) -> &Path {
        &self.root
    }

    pub fn cache_path(&self, identity: &SourceIdentity) -> CacheResult<PathBuf> {
        identity
            .validate()
            .map_err(|e| CacheError::Invalid(e.to_string()))?;
        let mut hasher = Sha256::new();
        hasher.update(self.decoder_key.as_bytes());
        let identity_bytes =
            serde_json::to_vec(identity).map_err(|e| CacheError::Invalid(e.to_string()))?;
        hasher.update(identity_bytes);
        let name = format!("{}.cfa", hex(&hasher.finalize()));
        let path = self.root.join(name);
        self.session
            .ensure_output_outside_sources(&path)
            .map_err(|e| CacheError::Invalid(e.to_string()))
    }

    fn check_source(&self, identity: &SourceIdentity) -> CacheResult<()> {
        identity
            .check_unchanged()
            .map_err(|e| stale(identity, e.to_string()))?;
        if !self.session.frames.iter().any(|frame| {
            frame.path == identity.path
                && frame.bytes == identity.bytes
                && frame.modified_unix_nanos == identity.modified_unix_nanos
        }) {
            return Err(CacheError::Invalid(
                "source identity is not in this resolved session".into(),
            ));
        }
        Ok(())
    }
    fn reserve(&mut self, bytes: usize) -> CacheResult<()> {
        loop {
            if bytes <= self.budget.saturating_sub(self.stats.resident_cfa_bytes) {
                return Ok(());
            }
            let evict = self
                .entries
                .iter()
                .filter(|(_, entry)| Arc::strong_count(&entry.source) == 1)
                .min_by_key(|(_, entry)| entry.last_use)
                .map(|(key, _)| key.clone());
            if let Some(key) = evict {
                if let Some(entry) = self.entries.remove(&key) {
                    self.stats.resident_cfa_bytes -= entry.source.cfa_bytes();
                }
            } else {
                return Err(CacheError::Budget {
                    requested_bytes: bytes,
                    budget_bytes: self.budget,
                    pinned_bytes: self.stats.resident_cfa_bytes,
                });
            }
        }
    }
    fn insert(&mut self, key: String, source: CachedSource) -> Arc<CachedSource> {
        self.clock = self.clock.wrapping_add(1);
        let source = Arc::new(source);
        self.stats.resident_cfa_bytes += source.cfa_bytes();
        self.stats.peak_resident_cfa_bytes = self
            .stats
            .peak_resident_cfa_bytes
            .max(self.stats.resident_cfa_bytes);
        self.entries.insert(
            key,
            Entry {
                source: Arc::clone(&source),
                last_use: self.clock,
            },
        );
        source
    }

    pub fn load(&mut self, identity: &SourceIdentity) -> CacheResult<Option<Arc<CachedSource>>> {
        self.check_source(identity)?;
        let path = self.cache_path(identity)?;
        let key = path.to_string_lossy().into_owned();
        self.clock = self.clock.wrapping_add(1);
        if let Some(entry) = self.entries.get_mut(&key) {
            entry.last_use = self.clock;
            self.stats.memory_hits += 1;
            return Ok(Some(Arc::clone(&entry.source)));
        }
        let mut file = match File::open(&path) {
            Ok(file) => file,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(error) => return Err(io(&path, error)),
        };
        let length = file.metadata().map_err(|e| io(&path, e))?.len();
        let mut prefix = [0_u8; 12];
        file.read_exact(&mut prefix)
            .map_err(|e| corrupt(&path, format!("incomplete envelope: {e}")))?;
        if &prefix[..8] != MAGIC {
            return Err(corrupt(&path, "wrong format magic"));
        }
        let header_len = u32::from_le_bytes(prefix[8..12].try_into().expect("four bytes")) as usize;
        if header_len == 0 || header_len > MAX_HEADER_BYTES {
            return Err(corrupt(&path, "invalid header length"));
        }
        let mut header_bytes = vec![0_u8; header_len];
        file.read_exact(&mut header_bytes)
            .map_err(|e| corrupt(&path, format!("incomplete header: {e}")))?;
        let header: Header =
            serde_json::from_slice(&header_bytes).map_err(|e| corrupt(&path, e.to_string()))?;
        if header.version != CACHE_VERSION
            || header.decoder_key != self.decoder_key
            || header.source != *identity
        {
            return Err(CacheError::Stale {
                path,
                message: "format, decoder or original input identity differs".into(),
            });
        }
        if header.cfa != "RGGB" {
            return Err(corrupt(&path, "unsupported CFA phase"));
        }
        header.geometry.validate().map_err(|e| corrupt(&path, e))?;
        header.metadata.validate().map_err(|e| corrupt(&path, e))?;
        let samples = header
            .geometry
            .sample_count()
            .ok_or_else(|| corrupt(&path, "sample count overflow"))?;
        let bytes = samples
            .checked_mul(2)
            .ok_or_else(|| corrupt(&path, "payload byte count overflow"))?;
        let expected_len = 12_u64
            .checked_add(header_len as u64)
            .and_then(|v| v.checked_add(bytes as u64))
            .and_then(|v| v.checked_add(32))
            .ok_or_else(|| corrupt(&path, "envelope length overflow"))?;
        if length != expected_len {
            return Err(corrupt(&path, "truncated payload or trailing bytes"));
        }
        self.reserve(bytes)?;
        let mut data = Vec::new();
        data.try_reserve_exact(samples)
            .map_err(|e| CacheError::Invalid(format!("CFA allocation: {e}")))?;
        let mut digest = Sha256::new();
        digest.update(&header_bytes);
        let mut block = [0_u8; 64 * 1024];
        let mut remaining = bytes;
        while remaining > 0 {
            let count = remaining.min(block.len());
            file.read_exact(&mut block[..count])
                .map_err(|e| corrupt(&path, format!("payload read: {e}")))?;
            digest.update(&block[..count]);
            data.extend(
                block[..count]
                    .as_chunks::<2>()
                    .0
                    .iter()
                    .map(|pair| u16::from_le_bytes(*pair)),
            );
            remaining -= count;
        }
        let mut expected_digest = [0_u8; 32];
        file.read_exact(&mut expected_digest)
            .map_err(|e| corrupt(&path, format!("missing digest: {e}")))?;
        let actual_digest: [u8; 32] = digest.finalize().into();
        if actual_digest != expected_digest {
            return Err(corrupt(&path, "metadata/payload digest mismatch"));
        }
        self.check_source(identity)?;
        self.stats.disk_hits += 1;
        Ok(Some(self.insert(
            key,
            CachedSource {
                identity: identity.clone(),
                geometry: header.geometry,
                metadata: header.metadata,
                data,
            },
        )))
    }

    /// Store only the untouched decoded original. The caller owns decode scratch;
    /// this method copies real active samples and never stores synthetic padding.
    pub fn store_original(
        &mut self,
        identity: &SourceIdentity,
        frame: &Frame,
    ) -> CacheResult<Arc<CachedSource>> {
        if let Some(source) = self.load(identity)? {
            return Ok(source);
        }
        let frame_path = fs::canonicalize(&frame.path).map_err(|e| io(&frame.path, e))?;
        if frame_path != identity.path {
            return Err(CacheError::Invalid(
                "decoded frame path differs from original identity".into(),
            ));
        }
        let geometry = CachedGeometry {
            stride: frame.stride,
            buffer_height: frame.buffer_height,
            active_x: frame.active.x,
            active_y: frame.active.y,
            width: frame.active.width,
            height: frame.active.height,
        };
        geometry.validate().map_err(CacheError::Invalid)?;
        if frame.data.len() != geometry.full_frame_bytes().expect("validated") / 2 {
            return Err(CacheError::Invalid(
                "decoded data length differs from original geometry".into(),
            ));
        }
        let metadata = CachedFrameMetadata::from_frame(frame);
        metadata.validate().map_err(CacheError::Invalid)?;
        let samples = geometry.sample_count().expect("validated");
        self.reserve(samples * 2)?;
        let mut data = Vec::new();
        data.try_reserve_exact(samples)
            .map_err(|e| CacheError::Invalid(format!("CFA allocation: {e}")))?;
        for y in 0..geometry.height {
            data.extend_from_slice(frame.active_row(y));
        }
        let source = CachedSource {
            identity: identity.clone(),
            geometry,
            metadata,
            data,
        };
        let path = self.cache_path(identity)?;
        self.publish(&path, &source)?;
        self.check_source(identity)?;
        let key = path.to_string_lossy().into_owned();
        Ok(self.insert(key, source))
    }

    pub fn load_or_decode(
        &mut self,
        source: &SourceFrame,
        identity: &SourceIdentity,
    ) -> CacheResult<Arc<CachedSource>> {
        if source.path != identity.path
            || source.bytes != identity.bytes
            || source.modified_unix_nanos != identity.modified_unix_nanos
        {
            return Err(CacheError::Invalid(
                "source frame and hashed identity disagree".into(),
            ));
        }
        if let Some(cached) = self.load(identity)? {
            return Ok(cached);
        }
        source
            .check_unchanged()
            .map_err(|e| stale(identity, e.to_string()))?;
        let decoded = strehl_raw::decode(&source.path).map_err(|e| CacheError::Decode {
            path: source.path.clone(),
            message: e.to_string(),
        })?;
        self.stats.decodes += 1;
        source
            .check_unchanged()
            .map_err(|e| stale(identity, e.to_string()))?;
        self.store_original(identity, &decoded)
    }

    fn publish(&self, path: &Path, source: &CachedSource) -> CacheResult<()> {
        let header = Header {
            version: CACHE_VERSION,
            decoder_key: self.decoder_key.clone(),
            source: source.identity.clone(),
            cfa: "RGGB".into(),
            geometry: source.geometry,
            metadata: source.metadata.clone(),
        };
        let header_bytes =
            serde_json::to_vec(&header).map_err(|e| CacheError::Invalid(e.to_string()))?;
        if header_bytes.len() > MAX_HEADER_BYTES {
            return Err(CacheError::Invalid(
                "decoded metadata exceeds cache header limit".into(),
            ));
        }
        let temp = self.root.join(format!(
            ".source-{}-{}.tmp",
            std::process::id(),
            TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed)
        ));
        self.session
            .ensure_output_outside_sources(&temp)
            .map_err(|e| CacheError::Invalid(e.to_string()))?;
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp)
            .map_err(|e| io(&temp, e))?;
        let result = (|| {
            file.write_all(MAGIC).map_err(|e| io(&temp, e))?;
            file.write_all(&(header_bytes.len() as u32).to_le_bytes())
                .map_err(|e| io(&temp, e))?;
            file.write_all(&header_bytes).map_err(|e| io(&temp, e))?;
            let mut digest = Sha256::new();
            digest.update(&header_bytes);
            let mut block = [0_u8; 64 * 1024];
            for chunk in source.data.chunks(block.len() / 2) {
                for (pixel, bytes) in chunk.iter().zip(block.as_chunks_mut::<2>().0.iter_mut()) {
                    bytes.copy_from_slice(&pixel.to_le_bytes());
                }
                let count = chunk.len() * 2;
                file.write_all(&block[..count]).map_err(|e| io(&temp, e))?;
                digest.update(&block[..count]);
            }
            file.write_all(&digest.finalize())
                .map_err(|e| io(&temp, e))?;
            file.sync_all().map_err(|e| io(&temp, e))?;
            self.check_source(&source.identity)?;
            Ok(())
        })();
        drop(file);
        if let Err(error) = result {
            let _ = fs::remove_file(&temp);
            return Err(error);
        }
        // Publish complete bytes without replacing an existing destination.
        // Cache writers are serialized by &mut SourceCache; parallel consumers
        // should share this owner rather than creating competing writers.
        if let Err(error) = self.session.ensure_output_outside_sources(path) {
            let _ = fs::remove_file(&temp);
            return Err(CacheError::Invalid(error.to_string()));
        }
        if let Err(error) = publish_without_replace(&temp, path) {
            let _ = fs::remove_file(&temp);
            return Err(io(path, error));
        }
        Ok(())
    }
}

#[cfg(windows)]
fn publish_without_replace(from: &Path, to: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{MOVEFILE_WRITE_THROUGH, MoveFileExW};
    let from: Vec<u16> = from.as_os_str().encode_wide().chain(Some(0)).collect();
    let to: Vec<u16> = to.as_os_str().encode_wide().chain(Some(0)).collect();
    if from[..from.len() - 1].contains(&0) || to[..to.len() - 1].contains(&0) {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "cache path contains NUL",
        ));
    }
    // SAFETY: owned terminated UTF-16 buffers stay live. Omitting
    // REPLACE_EXISTING makes a concurrently created destination an error.
    if unsafe { MoveFileExW(from.as_ptr(), to.as_ptr(), MOVEFILE_WRITE_THROUGH) } == 0 {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
}
#[cfg(not(windows))]
fn publish_without_replace(from: &Path, to: &Path) -> std::io::Result<()> {
    // Hard-link creation is atomic and refuses an existing name. Both paths
    // are in this cache directory, so no cross-filesystem copy is attempted.
    fs::hard_link(from, to)?;
    fs::remove_file(from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session_input::{PassSpec, SessionSpec};
    struct Fixture {
        root: PathBuf,
        session: ResolvedSession,
        identities: Vec<SourceIdentity>,
    }
    impl Fixture {
        fn new() -> Self {
            let root = std::env::temp_dir().join(format!(
                "strehl-session-cache-{}-{}",
                std::process::id(),
                TEMP_SEQUENCE.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&root).unwrap();
            fs::create_dir(root.join("raw")).unwrap();
            fs::write(root.join("raw/a.ARW"), b"original a").unwrap();
            fs::write(root.join("raw/b.ARW"), b"original b").unwrap();
            let session = SessionSpec {
                passes: vec![PassSpec {
                    name: "A".into(),
                    directories: vec![PathBuf::from("raw")],
                }],
                ..Default::default()
            }
            .resolve_from(&root)
            .unwrap();
            let identities = session.hash_sources(true).unwrap();
            Self {
                root,
                session,
                identities,
            }
        }
        fn cache(&self, budget: usize) -> SourceCache {
            SourceCache::new(&self.root.join("cache"), &self.session, budget).unwrap()
        }
        fn frame(&self, index: usize) -> Frame {
            let mut data = vec![65535; 8 * 6];
            for y in 0..3 {
                for x in 0..4 {
                    data[(y + 1) * 8 + x + 2] = (100 * y + x + index) as u16;
                }
            }
            Frame {
                data,
                stride: 8,
                buffer_height: 6,
                active: Region {
                    x: 2,
                    y: 1,
                    width: 4,
                    height: 3,
                },
                levels: Levels {
                    black: 0.0,
                    white: 15360.0,
                },
                iso: Some(100.0),
                wb_coeffs: [2.0, 1.0, 1.5, f32::from_bits(0x7fc01234)],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: vec![(
                    "D65".into(),
                    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                )],
                camera: "fixture".into(),
                path: self.identities[index].path.clone(),
            }
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.root);
        }
    }

    #[test]
    fn session_cache_roundtrip_preserves_original_active_coordinates_samples_and_nan_bits() {
        let f = Fixture::new();
        let mut cache = f.cache(48);
        let original = f.frame(0);
        let source = cache.store_original(&f.identities[0], &original).unwrap();
        assert_eq!(
            source.data,
            vec![0, 1, 2, 3, 100, 101, 102, 103, 200, 201, 202, 203]
        );
        assert_eq!(source.cfa_bytes(), 24);
        let geometry = source.geometry;
        let path = cache.cache_path(&f.identities[0]).unwrap();
        drop(source);
        drop(cache);
        let mut cache = f.cache(48);
        let source = cache.load(&f.identities[0]).unwrap().unwrap();
        assert_eq!(source.geometry, geometry);
        assert!(source.to_frame(95).is_err());
        let restored = source.to_frame(96).unwrap();
        assert_eq!(restored.active, original.active);
        assert_eq!(restored.stride, original.stride);
        assert_eq!(
            restored.wb_coeffs.map(f32::to_bits),
            original.wb_coeffs.map(f32::to_bits)
        );
        for y in 0..3 {
            assert_eq!(restored.active_row(y), original.active_row(y));
        }
        assert_eq!(restored.data[0], 0); // synthetic padding is never stored.
        assert!(fs::metadata(path).unwrap().len() < MAX_HEADER_BYTES as u64);
        assert_eq!(cache.stats().disk_hits, 1);
    }
    #[test]
    fn session_cache_pinned_handles_cannot_be_evicted_over_budget() {
        let f = Fixture::new();
        let mut cache = f.cache(24);
        let a = cache.store_original(&f.identities[0], &f.frame(0)).unwrap();
        assert!(matches!(
            cache.store_original(&f.identities[1], &f.frame(1)),
            Err(CacheError::Budget { .. })
        ));
        assert_eq!(cache.stats().resident_cfa_bytes, 24);
        drop(a);
        let b = cache.store_original(&f.identities[1], &f.frame(1)).unwrap();
        assert_eq!(b.data[0], 1);
        assert_eq!(cache.stats().peak_resident_cfa_bytes, 24);
        let f2 = Fixture::new();
        let mut pair_cache = f2.cache(48);
        let _a = pair_cache
            .store_original(&f2.identities[0], &f2.frame(0))
            .unwrap();
        let _b = pair_cache
            .store_original(&f2.identities[1], &f2.frame(1))
            .unwrap();
        assert_eq!(pair_cache.stats().resident_cfa_bytes, 48);
    }
    #[test]
    fn session_cache_rejects_corruption_truncation_stale_inputs_and_unsafe_roots() {
        let f = Fixture::new();
        let mut cache = f.cache(48);
        assert!(SourceCache::new(&f.root.join("raw/cache"), &f.session, 48).is_err());
        let source = cache.store_original(&f.identities[0], &f.frame(0)).unwrap();
        let path = cache.cache_path(&f.identities[0]).unwrap();
        drop(source);
        drop(cache);
        let original = fs::read(&path).unwrap();
        let mut corrupted = original.clone();
        let last = corrupted.len() - 33;
        corrupted[last] ^= 0x80;
        fs::write(&path, &corrupted).unwrap();
        assert!(matches!(
            f.cache(48).load(&f.identities[0]),
            Err(CacheError::Corrupt { .. })
        ));
        fs::write(&path, &original[..original.len() - 1]).unwrap();
        assert!(matches!(
            f.cache(48).load(&f.identities[0]),
            Err(CacheError::Corrupt { .. })
        ));
        fs::write(&path, &original).unwrap();
        fs::write(&f.identities[0].path, b"different source length").unwrap();
        assert!(matches!(
            f.cache(48).load(&f.identities[0]),
            Err(CacheError::Stale { .. })
        ));
        assert!(
            fs::read_dir(f.root.join("cache")).unwrap().all(|e| e
                .unwrap()
                .path()
                .extension()
                .is_some_and(|e| e == "cfa"))
        );
    }
    #[test]
    fn session_cache_publication_never_replaces_a_racing_destination() {
        let f = Fixture::new();
        let temporary = f.root.join("complete.tmp");
        let destination = f.root.join("existing.cfa");
        fs::write(&temporary, b"new complete payload").unwrap();
        fs::write(&destination, b"existing payload").unwrap();
        assert!(publish_without_replace(&temporary, &destination).is_err());
        assert_eq!(fs::read(&destination).unwrap(), b"existing payload");
        assert_eq!(fs::read(&temporary).unwrap(), b"new complete payload");
        fs::remove_file(&destination).unwrap();
        publish_without_replace(&temporary, &destination).unwrap();
        assert_eq!(fs::read(&destination).unwrap(), b"new complete payload");
        assert!(!temporary.exists());
    }

    #[test]
    fn session_cache_rejects_invalid_decoded_geometry_before_publication() {
        let f = Fixture::new();
        let mut cache = f.cache(48);
        let mut frame = f.frame(0);
        frame.active.width = usize::MAX;
        assert!(cache.store_original(&f.identities[0], &frame).is_err());
        assert_eq!(fs::read_dir(cache.root()).unwrap().count(), 0);
    }
}
