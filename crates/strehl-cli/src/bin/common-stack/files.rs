use std::fs::{self, File, Metadata, OpenOptions};
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub type Result<T> = std::result::Result<T, String>;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct FileRef {
    pub path: String,
    pub bytes: u64,
    pub sha256: String,
}

pub fn require(ok: bool, reason: &str) -> Result<()> {
    if ok { Ok(()) } else { Err(reason.to_string()) }
}

pub fn hash(raw: &[u8]) -> String {
    format!("{:x}", Sha256::digest(raw))
}

pub fn valid_hash(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn plain(meta: &Metadata) -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        !meta.file_type().is_symlink() && meta.file_attributes() & 0x400 == 0
    }
    #[cfg(not(windows))]
    {
        !meta.file_type().is_symlink()
    }
}

fn shared(a: &Metadata, b: &Metadata) -> bool {
    let same = a.len() == b.len()
        && a.modified().ok() == b.modified().ok()
        && a.is_file() == b.is_file()
        && plain(a)
        && plain(b);
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        same && a.file_attributes() == b.file_attributes()
    }
    #[cfg(not(windows))]
    {
        use std::os::unix::fs::MetadataExt;
        same && a.dev() == b.dev() && a.ino() == b.ino()
    }
}

fn stable(a: &Metadata, b: &Metadata) -> bool {
    // Compare creation time only within each API family, never across stat/open.
    shared(a, b) && a.created().ok() == b.created().ok()
}

pub fn path(base: &Path, value: &str, fresh: bool) -> Result<PathBuf> {
    require(
        !value.is_empty() && value.is_ascii() && value.len() <= 384,
        "bounded ASCII path",
    )?;
    let input = Path::new(value);
    require(
        !input
            .components()
            .any(|c| matches!(c, Component::ParentDir)),
        "parent path component forbidden",
    )?;
    let joined = if input.is_absolute() {
        input.to_path_buf()
    } else {
        base.join(input)
    };
    for ancestor in joined.ancestors() {
        if ancestor.as_os_str().is_empty() {
            continue;
        }
        match fs::symlink_metadata(ancestor) {
            Ok(meta) => require(plain(&meta), "symlink/reparse path forbidden")?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound && fresh && ancestor == joined => {}
            Err(e) => return Err(format!("path inspection {}: {e}", ancestor.display())),
        }
    }
    if fresh {
        require(!joined.exists(), "output path already exists")?;
        let parent = joined.parent().ok_or("output parent")?;
        let parent = fs::canonicalize(parent).map_err(|e| format!("output parent: {e}"))?;
        require(parent.is_dir(), "plain output directory")?;
        Ok(parent.join(joined.file_name().ok_or("output filename")?))
    } else {
        fs::canonicalize(joined).map_err(|e| format!("canonical input path: {e}"))
    }
}

pub fn key(path: &Path) -> String {
    let text = path.to_string_lossy().into_owned();
    if cfg!(windows) {
        text.to_lowercase()
    } else {
        text
    }
}

pub fn read(path: &Path, cap: u64, expected: Option<&FileRef>) -> Result<(Vec<u8>, FileRef)> {
    let before = fs::symlink_metadata(path).map_err(|e| format!("stat {}: {e}", path.display()))?;
    require(
        before.is_file() && plain(&before) && before.len() <= cap,
        "bounded plain file",
    )?;
    if let Some(pin) = expected {
        require(
            pin.bytes > 0 && pin.bytes <= cap && valid_hash(&pin.sha256),
            "typed bounded FileRef",
        )?;
        require(before.len() == pin.bytes, "file extent mismatch")?;
    }
    let mut file = File::open(path).map_err(|e| format!("open {}: {e}", path.display()))?;
    let opened = file.metadata().map_err(|e| format!("open metadata: {e}"))?;
    require(shared(&before, &opened), "open file identity")?;
    let mut raw = Vec::with_capacity(before.len() as usize);
    (&mut file)
        .take(cap + 1)
        .read_to_end(&mut raw)
        .map_err(|e| format!("read {}: {e}", path.display()))?;
    let after = file
        .metadata()
        .map_err(|e| format!("final handle metadata: {e}"))?;
    let named = fs::symlink_metadata(path).map_err(|e| format!("final path metadata: {e}"))?;
    require(
        raw.len() as u64 == before.len()
            && raw.len() as u64 <= cap
            && stable(&before, &named)
            && stable(&opened, &after)
            && shared(&before, &after),
        "file changed during bounded read",
    )?;
    let pin = FileRef {
        path: path.to_string_lossy().into_owned(),
        bytes: raw.len() as u64,
        sha256: hash(&raw),
    };
    if let Some(expected) = expected {
        require(pin.sha256 == expected.sha256, "file hash mismatch")?;
    }
    Ok((raw, pin))
}

pub fn hash_file(path: &Path, cap: u64) -> Result<FileRef> {
    let before = fs::symlink_metadata(path).map_err(|e| format!("hash stat: {e}"))?;
    require(
        before.is_file() && plain(&before) && before.len() > 0 && before.len() <= cap,
        "bounded binary",
    )?;
    let mut file = File::open(path).map_err(|e| format!("hash open: {e}"))?;
    let opened = file.metadata().map_err(|e| e.to_string())?;
    require(shared(&before, &opened), "hash open identity")?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 65536];
    let mut count = 0u64;
    loop {
        let n = file
            .read(&mut buffer)
            .map_err(|e| format!("hash read: {e}"))?;
        if n == 0 {
            break;
        }
        count += n as u64;
        require(count <= cap, "binary grew beyond cap")?;
        digest.update(&buffer[..n]);
    }
    let after = file.metadata().map_err(|e| e.to_string())?;
    let named = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    require(
        count == before.len()
            && stable(&before, &named)
            && stable(&opened, &after)
            && shared(&before, &after),
        "binary changed while hashing",
    )?;
    Ok(FileRef {
        path: path.to_string_lossy().into_owned(),
        bytes: count,
        sha256: format!("{:x}", digest.finalize()),
    })
}

pub fn encoded<T: Serialize>(value: &T, cap: usize) -> Result<Vec<u8>> {
    let mut raw = serde_json::to_vec(value).map_err(|e| format!("receipt encoding: {e}"))?;
    raw.push(b'\n');
    require(raw.len() <= cap, "receipt encoding capacity")?;
    Ok(raw)
}

pub fn write_new(path: &Path, raw: &[u8], cap: usize) -> Result<FileRef> {
    require(raw.len() <= cap, "fresh file capacity")?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|e| format!("create {}: {e}", path.display()))?;
    file.write_all(raw)
        .map_err(|e| format!("write {}: {e}", path.display()))?;
    file.sync_all()
        .map_err(|e| format!("sync {}: {e}", path.display()))?;
    drop(file);
    let (observed, pin) = read(path, cap as u64, None)?;
    require(observed == raw, "written bytes differ")?;
    Ok(pin)
}

pub fn staged(path: &Path, stage: &Path, raw: &[u8], cap: usize) -> Result<FileRef> {
    require(!path.exists(), "final output already exists")?;
    write_new(stage, raw, cap)?;
    // The destination is fresh; never replace a previous result.
    require(!path.exists(), "final output appeared before rename")?;
    fs::hard_link(stage, path)
        .map_err(|e| format!("publish create-only {}: {e}", path.display()))?;
    fs::remove_file(stage).map_err(|e| format!("remove owned publication stage: {e}"))?;
    let (observed, pin) = read(path, cap as u64, None)?;
    require(observed == raw, "published bytes differ")?;
    Ok(pin)
}

pub fn f32_hash(values: impl IntoIterator<Item = f32>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}
