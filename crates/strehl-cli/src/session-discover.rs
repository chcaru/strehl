//! Folder discovery for the one-step "stack everything" workflow.
//!
//! A user can point Strehl at a folder of related captures instead of writing
//! a manifest. Every directory under the root (bounded depth) that directly
//! contains RAW files becomes one pass, ordered by its earliest RAW timestamp,
//! and the session is planned automatically. Discovery only proposes passes;
//! the automatic planner still measures and explains what each contributes.
use crate::session_input::{PassSpec, SessionMode, SessionSpec};
use anyhow::{Context, Result, ensure};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

/// Directory levels searched below each root.
pub const MAX_DEPTH: usize = 4;
/// Passes accepted from one discovery; beyond this the user should choose.
pub const MAX_PASSES: usize = 64;

fn is_raw(path: &Path) -> bool {
    path.extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| e.eq_ignore_ascii_case("arw"))
}

/// Earliest direct RAW modification time in `directory`, or `None` without RAWs.
fn earliest_raw(directory: &Path) -> Result<Option<(u128, usize)>> {
    let mut earliest: Option<u128> = None;
    let mut count = 0usize;
    for entry in
        fs::read_dir(directory).with_context(|| format!("listing {}", directory.display()))?
    {
        let path = entry?.path();
        if is_raw(&path) && path.is_file() {
            count += 1;
            let stamp = fs::metadata(&path)?
                .modified()
                .ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map_or(u128::MAX, |d| d.as_nanos());
            earliest = Some(earliest.map_or(stamp, |e| e.min(stamp)));
        }
    }
    Ok(earliest.map(|e| (e, count)))
}

fn walk(directory: &Path, depth: usize, found: &mut Vec<(u128, PathBuf)>) -> Result<()> {
    if let Some((stamp, _)) = earliest_raw(directory)? {
        found.push((stamp, directory.to_path_buf()));
    }
    if depth == MAX_DEPTH {
        return Ok(());
    }
    let mut children: Vec<PathBuf> = fs::read_dir(directory)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            // Follow real directories only; never traverse links or hidden folders.
            fs::symlink_metadata(p).is_ok_and(|m| m.is_dir())
                && !p
                    .file_name()
                    .and_then(|n| n.to_str())
                    .is_some_and(|n| n.starts_with('.'))
        })
        .collect();
    children.sort();
    for child in children {
        walk(&child, depth + 1, found)?;
    }
    Ok(())
}

/// Build an automatic session from one or more folders.
pub fn discover(roots: &[PathBuf]) -> Result<SessionSpec> {
    ensure!(!roots.is_empty(), "no folders to discover");
    let mut found = Vec::new();
    for root in roots {
        let root = fs::canonicalize(root)
            .with_context(|| format!("resolving folder {}", root.display()))?;
        ensure!(root.is_dir(), "{} is not a folder", root.display());
        walk(&root, 0, &mut found)?;
    }
    found.sort();
    found.dedup_by(|a, b| a.1 == b.1);
    ensure!(
        !found.is_empty(),
        "no folder below the given roots contains ARW files"
    );
    ensure!(
        found.len() <= MAX_PASSES,
        "{} capture folders found; choose at most {MAX_PASSES} explicitly",
        found.len()
    );
    // Names: the folder's own name, disambiguated by its parent when repeated.
    let base = |p: &Path| {
        p.file_name().map_or_else(
            || p.display().to_string(),
            |n| n.to_string_lossy().into_owned(),
        )
    };
    let passes = found
        .iter()
        .map(|(_, path)| {
            let mut name = base(path);
            if found
                .iter()
                .filter(|(_, other)| base(other) == name)
                .count()
                > 1
            {
                let parent = path.parent().map(base).unwrap_or_default();
                name = format!("{parent}/{name}");
            }
            PassSpec {
                name,
                directories: vec![path.clone()],
            }
        })
        .collect();
    let spec = SessionSpec {
        mode: SessionMode::Auto,
        passes,
        primary_pass: None,
        ..SessionSpec::default()
    };
    spec.validate()?;
    Ok(spec)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{Duration, SystemTime};

    static NEXT: AtomicU64 = AtomicU64::new(0);

    fn root() -> PathBuf {
        let path = std::env::temp_dir().join(format!(
            "strehl-session-discover-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&path).unwrap();
        path
    }

    fn raw(directory: &Path, name: &str, age_seconds: u64) {
        fs::create_dir_all(directory).unwrap();
        let path = directory.join(name);
        fs::write(&path, b"raw").unwrap();
        let file = fs::File::options().write(true).open(&path).unwrap();
        file.set_modified(SystemTime::now() - Duration::from_secs(age_seconds))
            .unwrap();
    }

    #[test]
    fn discovery_orders_capture_folders_by_time_and_ignores_empty_and_hidden() {
        let r = root();
        raw(&r.join("bug/102MSDCF"), "DSC01.ARW", 100);
        raw(&r.join("bug/100MSDCF"), "DSC01.arw", 300);
        raw(&r.join("bug/103MSDCF"), "DSC01.ARW", 50);
        fs::create_dir_all(r.join("bug/empty")).unwrap();
        fs::write(r.join("bug/empty/notes.txt"), b"x").unwrap();
        raw(&r.join("bug/.hidden"), "DSC01.ARW", 400);
        let spec = discover(&[r.join("bug")]).unwrap();
        let names: Vec<_> = spec.passes.iter().map(|p| p.name.as_str()).collect();
        assert_eq!(names, ["100MSDCF", "102MSDCF", "103MSDCF"]);
        assert_eq!(spec.mode, SessionMode::Auto);
        assert_eq!(spec.primary_pass, None);
    }

    #[test]
    fn discovery_disambiguates_repeated_names_and_refuses_empty_roots() {
        let r = root();
        raw(&r.join("a/100MSDCF"), "DSC01.ARW", 20);
        raw(&r.join("b/100MSDCF"), "DSC01.ARW", 10);
        let spec = discover(std::slice::from_ref(&r)).unwrap();
        let names: Vec<_> = spec.passes.iter().map(|p| p.name.as_str()).collect();
        assert_eq!(names, ["a/100MSDCF", "b/100MSDCF"]);
        let empty = root();
        assert!(discover(&[empty]).is_err());
        assert!(discover(&[]).is_err());
    }

    #[test]
    fn discovery_treats_a_raw_folder_itself_as_one_pass() {
        let r = root();
        raw(&r, "DSC01.ARW", 5);
        let spec = discover(&[r]).unwrap();
        assert_eq!(spec.passes.len(), 1);
    }
}
