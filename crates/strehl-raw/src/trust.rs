//! Which archives a full decode may take as verified without hashing every
//! sample again (round-2 performance plan, stage Q5f).
//!
//! # Why
//!
//! Every full decode of an `STRHARC1` archive hashed the whole original file
//! to check the SHA-256 its envelope declares: 46 ms of a 123 ms decode, 37 %
//! (MEASURED 2026-11-18, `experiments/a7cr-stacking-performance-2026-11-18`,
//! `bench2 dec`), on every file of every render. What the check protects is
//! already protected once:
//!
//! - **the transfer**: the PC's receiver writes an archive only by decoding
//!   the wire stream against the sender's SHA-256 (`archive::retain`), and
//!   only then records an `ok` receipt in the capture's
//!   `transfer-receipts.jsonl`, with the archive's length and save time;
//! - **anything else**: the first full decode in any process verifies the
//!   file and records its name, length, modification time and declared hash
//!   in a store beside the warp maps ([`set_store`], `cache_root()/verified`).
//!
//! A later decode of a file whose length, modification time and declared
//! hash match a receipt or a record skips the hash. The bytes it decodes are
//! the same; what is given up is detecting a file damaged on disk after it
//! was verified, unless the damage breaks the Zstd stream. `strehl verify`
//! and [`ARCHIVE_VERIFY_ENV`]`=always` check everything again.
//!
//! # What cannot change
//!
//! Decoding is a pure function of the file. Skipping the hash removes a check,
//! never a sample.
use std::collections::HashMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, OnceLock};

/// `STREHL_ARCHIVE_VERIFY`: `always` hashes every full decode, as before;
/// unset, empty or `recorded` trusts receipts and records.
pub const ARCHIVE_VERIFY_ENV: &str = "STREHL_ARCHIVE_VERIFY";

/// What is known of one archive in a directory.
#[derive(Clone, Debug)]
struct Known {
    length: u64,
    sha256: String,
    /// A receipt: the archive must not have been written after it was saved.
    saved_unix_ms: Option<u64>,
    /// A record: the modification time it had when verified.
    modified_ns: Option<u128>,
}

#[derive(Default)]
struct DirIndex {
    by_name: HashMap<String, Vec<Known>>,
}

static STORE: OnceLock<PathBuf> = OnceLock::new();
static INDEX: Mutex<Option<HashMap<PathBuf, Arc<Mutex<DirIndex>>>>> = Mutex::new(None);
static WRITE: Mutex<()> = Mutex::new(());
static HASHED: AtomicU64 = AtomicU64::new(0);
static TRUSTED: AtomicU64 = AtomicU64::new(0);

/// Keep records of verified archives in `dir` (created when needed). Takes
/// effect for directories not yet consulted in this process.
pub fn set_store(dir: PathBuf) {
    let _ = STORE.set(dir);
}

fn always() -> bool {
    std::env::var(ARCHIVE_VERIFY_ENV).is_ok_and(|v| v.trim().eq_ignore_ascii_case("always"))
}

/// The record file for a capture directory: its name and a hash of its
/// full path, so two folders of one name do not share records.
fn record_file(dir: &Path) -> Option<PathBuf> {
    let store = STORE.get()?;
    let mut h = 0xcbf2_9ce4_8422_2325u64;
    for b in dir.to_string_lossy().bytes() {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
    }
    let name = dir
        .file_name()
        .map_or_else(|| "root".into(), |n| n.to_string_lossy().into_owned());
    Some(store.join(format!("{name}-{h:016x}.tsv")))
}

fn modified_ns(meta: &std::fs::Metadata) -> Option<u128> {
    meta.modified()
        .ok()?
        .duration_since(std::time::UNIX_EPOCH)
        .ok()
        .map(|d| d.as_nanos())
}

fn load(dir: &Path) -> DirIndex {
    let mut index = DirIndex::default();
    // The receiver's receipts: `ok` and durable archive receipts only.
    if let Ok(text) = std::fs::read_to_string(dir.join("transfer-receipts.jsonl")) {
        for line in text.lines() {
            let Ok(v) = serde_json::from_str::<serde_json::Value>(line) else {
                continue;
            };
            let ok = v["ok"].as_bool() == Some(true) && v["durable"].as_bool() == Some(true);
            let archive = v["storage_encoding"].as_str() == Some("strehl-archive-v1");
            let (Some(path), Some(length), Some(sha), Some(saved)) = (
                v["path"].as_str(),
                v["storage_bytes"].as_u64(),
                v["sha256"].as_str(),
                v["saved_unix_ms"].as_u64(),
            ) else {
                continue;
            };
            if !(ok && archive) {
                continue;
            }
            let Some(name) = Path::new(path).file_name() else {
                continue;
            };
            index
                .by_name
                .entry(name.to_string_lossy().into_owned())
                .or_default()
                .push(Known {
                    length,
                    sha256: sha.to_ascii_lowercase(),
                    saved_unix_ms: Some(saved),
                    modified_ns: None,
                });
        }
    }
    // This store's records: `name \t length \t modified_ns \t sha256`.
    if let Some(file) = record_file(dir)
        && let Ok(text) = std::fs::read_to_string(file)
    {
        for line in text.lines() {
            let f: Vec<&str> = line.split('\t').collect();
            if let [name, length, modified, sha] = f[..]
                && let (Ok(length), Ok(modified)) = (length.parse(), modified.parse())
            {
                index
                    .by_name
                    .entry(name.to_owned())
                    .or_default()
                    .push(Known {
                        length,
                        sha256: sha.to_owned(),
                        saved_unix_ms: None,
                        modified_ns: Some(modified),
                    });
            }
        }
    }
    index
}

fn index_of(dir: &Path) -> Arc<Mutex<DirIndex>> {
    let mut guard = INDEX.lock().unwrap_or_else(|e| e.into_inner());
    let map = guard.get_or_insert_with(HashMap::new);
    Arc::clone(
        map.entry(dir.to_path_buf())
            .or_insert_with(|| Arc::new(Mutex::new(load(dir)))),
    )
}

/// The SHA-256 the archive at `path` was verified against, if a receipt or
/// a record says it was and the file has not changed since (its length,
/// and its modification time no later than the receipt or equal to the
/// record's). The caller still requires the envelope to declare this hash.
pub fn trusted_sha256(path: &Path) -> Option<String> {
    if always() {
        return None;
    }
    let meta = std::fs::metadata(path).ok()?;
    let modified = modified_ns(&meta)?;
    let (dir, name) = (path.parent()?, path.file_name()?.to_string_lossy());
    let index = index_of(dir);
    let index = index.lock().unwrap_or_else(|e| e.into_inner());
    index
        .by_name
        .get(name.as_ref())?
        .iter()
        .rev()
        .find_map(|k| {
            let fresh = match (k.saved_unix_ms, k.modified_ns) {
                // Written before the receipt was saved (and its commit, a rename,
                // keeps the time); two seconds of clock slack.
                (Some(saved), _) => modified <= (u128::from(saved) + 2000) * 1_000_000,
                (None, Some(m)) => modified == m,
                (None, None) => false,
            };
            (fresh && k.length == meta.len()).then(|| k.sha256.clone())
        })
}

/// Note that a full decode of `path` verified the declared `sha256`: kept
/// for this process and, with a store, for later ones.
pub fn record_verified(path: &Path, sha256: &str) {
    HASHED.fetch_add(1, Ordering::Relaxed);
    let Ok(meta) = std::fs::metadata(path) else {
        return;
    };
    let Some(modified) = modified_ns(&meta) else {
        return;
    };
    let (Some(dir), Some(name)) = (path.parent(), path.file_name()) else {
        return;
    };
    let name = name.to_string_lossy().into_owned();
    let known = Known {
        length: meta.len(),
        sha256: sha256.to_ascii_lowercase(),
        saved_unix_ms: None,
        modified_ns: Some(modified),
    };
    {
        let index = index_of(dir);
        let mut index = index.lock().unwrap_or_else(|e| e.into_inner());
        let entries = index.by_name.entry(name.clone()).or_default();
        if entries.iter().any(|k| {
            k.modified_ns == Some(modified) && k.length == known.length && k.sha256 == known.sha256
        }) {
            return;
        }
        entries.push(known.clone());
    }
    let Some(file) = record_file(dir) else {
        return;
    };
    // One appending writer at a time in this process; a line is small enough
    // to land whole. A failed write costs a later render its skip, nothing else.
    let _guard = WRITE.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(parent) = file.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&file)
    {
        let _ = writeln!(
            f,
            "{name}\t{}\t{}\t{}",
            known.length, modified, known.sha256
        );
    }
}

/// Count a full decode that skipped the hash.
pub(crate) fn note_trusted() {
    TRUSTED.fetch_add(1, Ordering::Relaxed);
}

/// Full archive decodes since the last call: hashed, and trusted without
/// hashing.
pub fn take_counts() -> (u64, u64) {
    (
        HASHED.swap(0, Ordering::Relaxed),
        TRUSTED.swap(0, Ordering::Relaxed),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn receipts_and_records_trust_only_unchanged_files() {
        let root = std::env::temp_dir().join(format!(
            "strehl-trust-test-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&root).unwrap();
        struct Cleanup(PathBuf);
        impl Drop for Cleanup {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
        let _cleanup = Cleanup(root.clone());
        let dir = &root;
        let a = dir.join("a.ARW.straw");
        let b = dir.join("b.ARW.straw");
        std::fs::write(&a, b"0123456789").unwrap();
        std::fs::write(&b, b"abc").unwrap();
        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;
        let receipt = |path: &Path, bytes: u64, ok: bool| {
            serde_json::json!({
                "ok": ok, "durable": true, "storage_encoding": "strehl-archive-v1",
                "path": path.to_string_lossy(), "storage_bytes": bytes,
                "sha256": "ABCDEF", "saved_unix_ms": now_ms + 1000,
            })
            .to_string()
        };
        std::fs::write(
            dir.join("transfer-receipts.jsonl"),
            format!("{}\n{}\n", receipt(&a, 10, true), receipt(&b, 3, false)),
        )
        .unwrap();
        // A receipt of the right length, saved after the file was written.
        assert_eq!(trusted_sha256(&a).as_deref(), Some("abcdef"));
        // Not `ok`: not trusted.
        assert_eq!(trusted_sha256(&b), None);
        // A record: trusted while the file is unchanged.
        record_verified(&b, "0011");
        assert_eq!(trusted_sha256(&b).as_deref(), Some("0011"));
        std::fs::write(&b, b"abcd").unwrap();
        assert_eq!(trusted_sha256(&b), None, "a changed file is not trusted");
    }
}
