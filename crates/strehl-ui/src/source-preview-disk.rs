//! Persistent small derivatives of camera previews (Studio 2, spec 5.5 item 1).
//!
//! The resident scrub and sparse tiers are rebuilt from each RAW's embedded
//! JPEG on every open. A bounded disk derivative lets a reopened long stack
//! warm without decoding: raw RGBA at the tier's side, keyed by the source's
//! path, size, modification time and the requested side. A source still
//! inside the two-second write window is never cached. All access runs on the
//! preview workers; nothing here is called from paint.
//!
//! Bounded like `explorer-preview-cache.rs`: 160 MiB and 1,024 entries, the
//! oldest pruned first. `STREHL_SOURCE_PREVIEW_CACHE` sets another folder, or
//! `off` disables it (benchmarks measure cold and reopened stacks apart).
use super::*;
use sha2::{Digest, Sha256};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    sync::{Mutex, OnceLock, atomic::AtomicU64},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

const FORMAT: u32 = 1;
const MAX_SIDE: usize = 640;
const MAX_HEADER: usize = 1024;
const DISK_BUDGET: u64 = 160 * 1024 * 1024;
const DISK_ENTRIES: usize = 1024;
const PRUNE_EVERY: u64 = 64;

#[derive(serde::Serialize, serde::Deserialize)]
struct Header {
    format: u32,
    identity: String,
    source_size: [u32; 2],
    size: [usize; 2],
    is_overview: bool,
}

fn configured() -> &'static Mutex<Option<Option<PathBuf>>> {
    static ROOT: OnceLock<Mutex<Option<Option<PathBuf>>>> = OnceLock::new();
    ROOT.get_or_init(|| Mutex::new(None))
}

/// Override the folder (None disables). Tests and benchmarks only.
#[cfg(test)]
pub(crate) fn set_root(root: Option<PathBuf>) {
    *configured().lock().unwrap_or_else(|e| e.into_inner()) = Some(root);
}

pub(crate) fn root() -> Option<PathBuf> {
    if let Some(root) = configured()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .clone()
    {
        return root;
    }
    if let Some(value) = std::env::var_os("STREHL_SOURCE_PREVIEW_CACHE") {
        return (value != "off").then(|| PathBuf::from(value));
    }
    // Unit tests never touch the owner's real cache unless they opt in.
    if cfg!(test) {
        return None;
    }
    crate::workspace_history::default_path()
        .and_then(|path| path.parent().map(|parent| parent.join("source-previews")))
}

fn digest(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

/// Path, length and modification time (never within the write window), plus
/// the requested side and policy, so different tiers never share an entry.
fn identity(path: &Path, side: u32, policy: &str) -> Option<String> {
    let metadata = fs::metadata(path).ok()?;
    let modified = metadata.modified().ok()?;
    if SystemTime::now().duration_since(modified).ok()? < Duration::from_secs(2) {
        return None;
    }
    let nanos = modified.duration_since(UNIX_EPOCH).ok()?.as_nanos();
    let key = serde_json::to_vec(&(FORMAT, path, metadata.len(), nanos, side, policy)).ok()?;
    Some(digest(&key))
}

/// A cached derivative for this source and side, if present and intact.
pub(crate) fn load(path: &Path, side: u32, policy: &str) -> Option<PreviewImage> {
    let root = root()?;
    let identity = identity(path, side, policy)?;
    let entry = root.join(format!("{identity}.scrub"));
    let image = read(&entry, path, &identity).ok()?;
    // Reading refreshes the entry's age, so pruning drops the least used.
    if let Ok(file) = OpenOptions::new().write(true).open(&entry) {
        let _ = file.set_modified(SystemTime::now());
    }
    Some(image)
}

/// Store a freshly decoded derivative. Best effort: failures are ignored.
pub(crate) fn store(path: &Path, side: u32, policy: &str, image: &PreviewImage) {
    let Some(root) = root() else { return };
    let Some(identity) = identity(path, side, policy) else {
        return;
    };
    if write(&root.join(format!("{identity}.scrub")), &identity, image).is_ok() {
        static WRITES: AtomicU64 = AtomicU64::new(0);
        if WRITES
            .fetch_add(1, Ordering::Relaxed)
            .is_multiple_of(PRUNE_EVERY)
        {
            prune(&root);
        }
    }
}

fn read(entry: &Path, source: &Path, identity: &str) -> Result<PreviewImage> {
    let mut file = File::open(entry)?;
    let bytes = file.metadata()?.len();
    ensure!(
        bytes <= (4 + MAX_HEADER + MAX_SIDE * MAX_SIDE * 4) as u64,
        "Preview derivative is oversized"
    );
    let mut prefix = [0; 4];
    file.read_exact(&mut prefix)?;
    let header_bytes = u32::from_le_bytes(prefix) as usize;
    ensure!(
        header_bytes <= MAX_HEADER,
        "Preview derivative header is oversized"
    );
    let mut body = vec![0; header_bytes];
    file.read_exact(&mut body)?;
    let header: Header = serde_json::from_slice(&body)?;
    ensure!(
        header.format == FORMAT
            && header.identity == identity
            && header.size.iter().all(|&n| n > 0 && n <= MAX_SIDE)
            && header.source_size.iter().all(|&n| n > 0),
        "Preview derivative does not match its source"
    );
    let count = header.size[0] * header.size[1] * 4;
    ensure!(
        bytes == (4 + header_bytes + count) as u64,
        "Preview derivative is incomplete"
    );
    let mut rgba = vec![0; count];
    file.read_exact(&mut rgba)?;
    Ok(PreviewImage {
        path: source.to_path_buf(),
        source_size: header.source_size,
        size: header.size,
        rgba,
        is_overview: header.is_overview,
    })
}

fn write(entry: &Path, identity: &str, image: &PreviewImage) -> Result<()> {
    ensure!(
        image.size.iter().all(|&n| n > 0 && n <= MAX_SIDE)
            && image.rgba.len() == image.size[0] * image.size[1] * 4,
        "Preview derivative dimensions are invalid"
    );
    let parent = entry.parent().context("Preview derivative has no folder")?;
    fs::create_dir_all(parent)?;
    let header = serde_json::to_vec(&Header {
        format: FORMAT,
        identity: identity.into(),
        source_size: image.source_size,
        size: image.size,
        is_overview: image.is_overview,
    })?;
    let mut random = [0; 8];
    getrandom::fill(&mut random).map_err(|e| anyhow::anyhow!("Creating a derivative: {e}"))?;
    let temporary = parent.join(format!("{}.pending", digest(&random)));
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(&(header.len() as u32).to_le_bytes())?;
        file.write_all(&header)?;
        file.write_all(&image.rgba)?;
        drop(file);
        fs::rename(&temporary, entry)?;
        Ok(())
    })();
    let _ = fs::remove_file(&temporary);
    result
}

/// Drop the oldest entries until both bounds hold.
pub(crate) fn prune(root: &Path) {
    let Ok(files) = fs::read_dir(root) else {
        return;
    };
    let mut entries: Vec<_> = files
        .flatten()
        .filter_map(|entry| {
            let path = entry.path();
            if path
                .extension()
                .is_none_or(|extension| extension != "scrub")
            {
                return None;
            }
            let metadata = entry.metadata().ok()?;
            metadata.is_file().then_some((
                metadata.modified().unwrap_or(UNIX_EPOCH),
                metadata.len(),
                path,
            ))
        })
        .collect();
    entries.sort_unstable_by_key(|entry| entry.0);
    let mut bytes: u64 = entries.iter().map(|entry| entry.1).sum();
    let mut count = entries.len();
    for (_, size, path) in entries {
        if bytes <= DISK_BUDGET && count <= DISK_ENTRIES {
            break;
        }
        if fs::remove_file(path).is_ok() {
            bytes = bytes.saturating_sub(size);
            count -= 1;
        }
    }
}

#[cfg(test)]
#[path = "source-preview-disk-tests.rs"]
mod tests;
