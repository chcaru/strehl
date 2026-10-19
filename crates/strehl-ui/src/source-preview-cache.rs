//! Compressed camera previews only. No decoded RAW or full-resolution RGB is
//! retained. Metadata is checked on the open file before every lookup.
use super::*;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex, OnceLock};
use std::time::{Duration, SystemTime};

const CATALOG_LIMIT: usize = 256;
const PAYLOAD_LIMIT: usize = 64;
const PAYLOAD_BYTES: usize = 48 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Stamp {
    path: PathBuf,
    bytes: u64,
    modified: SystemTime,
}
impl Stamp {
    pub(super) fn new(path: &Path, metadata: &std::fs::Metadata) -> Option<Self> {
        let modified = metadata.modified().ok()?;
        // A writer can replace same-length TIFF metadata more quickly than its
        // filesystem timestamp advances. Do not reuse either orientation or
        // JPEG bytes while a source is still within that timestamp window.
        // Future timestamps are equally unsuitable as a stable cache identity.
        if SystemTime::now().duration_since(modified).ok()? < Duration::from_secs(2) {
            return None;
        }
        Some(Self {
            path: path.to_path_buf(),
            bytes: metadata.len(),
            modified,
        })
    }
}

type Catalog = Arc<[(JpegCandidate, [u32; 2])]>;
struct Payload {
    stamp: Stamp,
    offset: u64,
    length: u64,
    bytes: Arc<[u8]>,
}
#[derive(Default)]
struct Cache {
    catalogs: VecDeque<(Stamp, Catalog)>,
    payloads: VecDeque<Payload>,
    bytes: usize,
}
impl Cache {
    fn catalog(&mut self, stamp: &Stamp) -> Option<Catalog> {
        let at = self.catalogs.iter().position(|(key, _)| key == stamp)?;
        let item = self.catalogs.remove(at)?;
        let result = item.1.clone();
        self.catalogs.push_back(item);
        Some(result)
    }
    fn insert_catalog(&mut self, stamp: Stamp, catalog: Catalog) {
        self.catalogs.retain(|(key, _)| key.path != stamp.path);
        self.catalogs.push_back((stamp, catalog));
        while self.catalogs.len() > CATALOG_LIMIT {
            self.catalogs.pop_front();
        }
    }
    fn payload(&mut self, stamp: &Stamp, candidate: JpegCandidate) -> Option<Arc<[u8]>> {
        let at = self.payloads.iter().position(|item| {
            item.stamp == *stamp
                && item.offset == candidate.offset
                && item.length == candidate.length
        })?;
        let item = self.payloads.remove(at)?;
        let bytes = item.bytes.clone();
        self.payloads.push_back(item);
        Some(bytes)
    }
    fn insert_payload(&mut self, stamp: Stamp, candidate: JpegCandidate, bytes: Arc<[u8]>) {
        if bytes.len() > PAYLOAD_BYTES {
            return;
        }
        // Superseded file contents cannot occupy the budget or satisfy a new
        // request. Concurrent duplicate readers still publish only one entry.
        self.payloads.retain(|item| {
            !(item.stamp.path == stamp.path
                && (item.stamp != stamp || item.offset == candidate.offset))
        });
        self.bytes = self.payloads.iter().map(|item| item.bytes.len()).sum();
        self.bytes += bytes.len();
        self.payloads.push_back(Payload {
            stamp,
            offset: candidate.offset,
            length: candidate.length,
            bytes,
        });
        while self.bytes > PAYLOAD_BYTES || self.payloads.len() > PAYLOAD_LIMIT {
            if let Some(item) = self.payloads.pop_front() {
                self.bytes -= item.bytes.len();
            }
        }
    }
}

fn cache() -> &'static Mutex<Cache> {
    static CACHE: OnceLock<Mutex<Cache>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(Cache::default()))
}

pub(super) fn catalog(
    reader: &mut (impl Read + Seek),
    file_len: u64,
    stamp: Option<&Stamp>,
    cancelled: &AtomicBool,
) -> Result<Catalog> {
    check_cancelled(cancelled)?;
    if let Some(stamp) = stamp
        && let Some(found) = cache()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .catalog(stamp)
    {
        return Ok(found);
    }
    // Do not hold the cache mutex while reading a file: a slow source must not
    // serialize the independent contact lane or selected preview decoder.
    let candidates = jpeg_candidates(reader, file_len, cancelled)?;
    let sized: Catalog = sized_candidates(reader, file_len, candidates, cancelled)?.into();
    check_cancelled(cancelled)?;
    if let Some(stamp) = stamp {
        cache()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert_catalog(stamp.clone(), sized.clone());
    }
    Ok(sized)
}

pub(super) fn payload(
    reader: &mut (impl Read + Seek),
    file_len: u64,
    stamp: Option<&Stamp>,
    candidate: JpegCandidate,
    cancelled: &AtomicBool,
) -> Result<Arc<[u8]>> {
    check_cancelled(cancelled)?;
    if let Some(stamp) = stamp
        && let Some(found) = cache()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .payload(stamp, candidate)
    {
        return Ok(found);
    }
    let mut bytes = vec![0; candidate.length as usize];
    read_at(reader, file_len, candidate.offset, &mut bytes, cancelled)?;
    let bytes: Arc<[u8]> = bytes.into();
    if let Some(stamp) = stamp {
        cache()
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert_payload(stamp.clone(), candidate, bytes.clone());
    }
    Ok(bytes)
}

#[cfg(test)]
#[path = "source-preview-cache-tests.rs"]
mod tests;
