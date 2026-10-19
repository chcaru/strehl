//! The desktop carries the CLI engine and invokes it in an owned child process.
//!
//! This preserves cancellation, pipe-based observation, memory isolation and the
//! CLI's startup-only environment writes without requiring a sibling executable.

use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{Context, Result};

const WORKER_FLAG: &str = "--engine-worker";

/// Called at the very beginning of `main`, before GUI or worker initialization.
/// `None` means this is an ordinary desktop launch.
pub fn run_worker() -> Option<i32> {
    let mut args = std::env::args_os();
    let _program = args.next();
    if args.next().as_deref() != Some(std::ffi::OsStr::new(WORKER_FLAG)) {
        return None;
    }
    let argv = std::iter::once(std::ffi::OsString::from("strehl")).chain(args);
    // SAFETY: main calls this before the desktop starts any threads or runtime.
    match unsafe { strehl_cli::run_from(argv) } {
        Ok(()) => Some(0),
        Err(error) => {
            eprintln!("Error: {error:?}");
            Some(1)
        }
    }
}

pub fn bundled_executable() -> Option<PathBuf> {
    std::env::current_exe().ok()
}

/// Explicit external overrides remain useful for development. Only our exact
/// executable receives the worker flag; names alone never select worker mode.
pub fn command(executable: &Path) -> Result<Command> {
    let executable = resolve(executable)?;
    let mut command = Command::new(&executable);
    if bundled_executable()
        .and_then(|path| resolve(&path).ok())
        .is_some_and(|own| own == executable)
    {
        command.arg(WORKER_FLAG);
    }
    Ok(command)
}

fn resolve(path: &Path) -> Result<PathBuf> {
    if path.is_file() || path.components().count() > 1 || path.is_absolute() {
        std::fs::canonicalize(path)
            .with_context(|| format!("Finding the engine at {}", path.display()))
    } else {
        Ok(path.to_path_buf())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn own_process_uses_worker_mode_but_external_cli_does_not() {
        let bundled = bundled_executable().expect("running executable");
        let own = command(&bundled).unwrap();
        assert_eq!(own.get_program(), resolve(&bundled).unwrap());
        assert_eq!(own.get_args().collect::<Vec<_>>(), [WORKER_FLAG]);
        let external = command(Path::new("strehl-external-engine")).unwrap();
        assert_eq!(external.get_program(), "strehl-external-engine");
        assert_eq!(external.get_args().count(), 0);
    }

    #[test]
    fn missing_explicit_engine_reports_the_path() {
        let missing = std::env::temp_dir()
            .join(format!("strehl-missing-engine-{}", std::process::id()))
            .join("engine");
        assert!(!missing.exists());
        let error = command(&missing).unwrap_err();
        assert!(error.to_string().contains(&missing.display().to_string()));
    }
}
