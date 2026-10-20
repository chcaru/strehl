//! New-file exports become visible only after the complete file is durable.
use anyhow::{Context, Result, bail};
use std::{
    fs::{File, OpenOptions},
    path::{Path, PathBuf},
    sync::atomic::{AtomicU64, Ordering},
    time::{SystemTime, UNIX_EPOCH},
};

static SEQUENCE: AtomicU64 = AtomicU64::new(0);

struct OwnedTemporary(PathBuf);
impl Drop for OwnedTemporary {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

/// `write` must flush any buffered writer before returning. Publication never
/// replaces even a destination created during encoding.
pub(crate) fn new_file(path: &Path, write: impl FnOnce(&mut File) -> Result<()>) -> Result<()> {
    if path.try_exists()? {
        bail!("destination already exists: {}", path.display());
    }
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let nonce = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
    let mut owned = None;
    for _ in 0..128 {
        let candidate = parent.join(format!(
            ".strehl-export-{}-{nonce}-{}.tmp",
            std::process::id(),
            SEQUENCE.fetch_add(1, Ordering::Relaxed)
        ));
        match OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&candidate)
        {
            Ok(file) => {
                owned = Some((OwnedTemporary(candidate), file));
                break;
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(e) => return Err(e).context("reserving export temporary file"),
        }
    }
    let (temporary, mut file) = owned.context("could not reserve export temporary file")?;
    let result =
        write(&mut file).and_then(|()| file.sync_all().context("flushing completed export"));
    drop(file);
    result?;
    publish_without_replace(&temporary.0, path)
        .with_context(|| format!("publishing new export without replacing {}", path.display()))?;
    // The final name now refers to complete bytes. Drop cleans only our own name.
    Ok(())
}

#[cfg(not(windows))]
fn publish_without_replace(temporary: &Path, destination: &Path) -> std::io::Result<()> {
    // Both paths are on the same filesystem. No unlink+rename fallback: that
    // would destroy a competing export and expose incomplete output.
    std::fs::hard_link(temporary, destination)
}

#[cfg(windows)]
fn publish_without_replace(temporary: &Path, destination: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{MOVEFILE_WRITE_THROUGH, MoveFileExW};
    let from: Vec<u16> = temporary.as_os_str().encode_wide().chain(Some(0)).collect();
    let to: Vec<u16> = destination
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    // SAFETY: Both strings are owned, terminated UTF-16 buffers that remain
    // live for the call. Omitting REPLACE_EXISTING is the no-overwrite contract.
    let success = unsafe { MoveFileExW(from.as_ptr(), to.as_ptr(), MOVEFILE_WRITE_THROUGH) };
    if success == 0 {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn concurrent_destination_is_not_replaced_and_temporary_is_removed() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("photo.tiff");
        let result = new_file(&path, |file| {
            file.write_all(b"new image")?;
            // A competing application creates the destination after our check.
            std::fs::write(&path, b"other application")?;
            Ok(())
        });
        assert!(result.is_err());
        assert_eq!(std::fs::read(&path).unwrap(), b"other application");
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 1);
    }

    #[test]
    fn write_error_leaves_neither_a_final_nor_temporary_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("photo.tiff");
        assert!(
            new_file(&path, |file| {
                file.write_all(b"incomplete")?;
                bail!("injected encoder failure")
            })
            .is_err()
        );
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 0);
        new_file(&path, |file| Ok(file.write_all(b"complete")?)).unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), b"complete");
        assert_eq!(std::fs::read_dir(dir.path()).unwrap().count(), 1);
    }
}
