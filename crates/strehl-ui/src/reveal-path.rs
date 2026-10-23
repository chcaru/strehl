//! Explicit Explorer actions. Call on a worker: validation can touch a slow
//! volume, and none of these commands invoke a shell or evaluate a filename.
use anyhow::{Context, Result, ensure};
use std::{ffi::OsString, path::Path, process::Command};

#[derive(Clone, Copy)]
enum Platform {
    #[cfg(any(windows, test))]
    Windows,
    #[cfg(any(target_os = "macos", test))]
    Mac,
    #[cfg(any(all(not(windows), not(target_os = "macos")), test))]
    Unix,
}

impl Platform {
    fn current() -> Self {
        #[cfg(windows)]
        {
            Self::Windows
        }
        #[cfg(target_os = "macos")]
        {
            Self::Mac
        }
        #[cfg(all(not(windows), not(target_os = "macos")))]
        {
            Self::Unix
        }
    }
}

struct RevealCommand {
    program: &'static str,
    arguments: Vec<OsString>,
}

fn command_for(path: &Path, platform: Platform) -> Result<RevealCommand> {
    ensure!(
        !path.as_os_str().is_empty(),
        "Choose a file or folder to reveal."
    );
    let metadata = std::fs::metadata(path).with_context(|| {
        format!(
            "This file or folder is no longer available: {}",
            path.display()
        )
    })?;
    ensure!(
        metadata.is_file() || metadata.is_dir(),
        "Only files and folders can be revealed: {}",
        path.display()
    );
    // Keep the visible path (including a symlink), rather than unexpectedly
    // opening a different directory containing its resolved target.
    let absolute =
        std::path::absolute(path).with_context(|| format!("Resolving {}", path.display()))?;
    let is_file = metadata.is_file();
    Ok(match platform {
        #[cfg(any(windows, test))]
        Platform::Windows => {
            let mut argument = OsString::new();
            if is_file {
                argument.push("/select,");
            }
            argument.push(absolute);
            RevealCommand {
                program: "explorer.exe",
                arguments: vec![argument],
            }
        }
        #[cfg(any(target_os = "macos", test))]
        Platform::Mac => {
            let mut arguments = Vec::with_capacity(2);
            if is_file {
                arguments.push(OsString::from("-R"));
            }
            arguments.push(absolute.into_os_string());
            RevealCommand {
                program: "open",
                arguments,
            }
        }
        #[cfg(any(all(not(windows), not(target_os = "macos")), test))]
        Platform::Unix => {
            let folder = if is_file {
                absolute
                    .parent()
                    .context("The file has no containing folder.")?
                    .to_path_buf()
            } else {
                absolute
            };
            RevealCommand {
                program: "xdg-open",
                arguments: vec![folder.into_os_string()],
            }
        }
    })
}

pub(crate) fn reveal(path: &Path) -> Result<()> {
    let launch = command_for(path, Platform::current())?;
    let mut child = Command::new(launch.program)
        .args(launch.arguments)
        .spawn()
        .with_context(|| {
            format!(
                "Could not open the system file browser for {}",
                path.display()
            )
        })?;
    // Some file browsers delegate to an existing window immediately; others
    // remain alive with that window. Reap either case without retaining the
    // action worker or leaving a zombie on Unix.
    std::thread::spawn(move || {
        let _ = child.wait();
    });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn files_are_selected_and_folders_open_with_literal_structured_arguments() {
        let directory = tempfile::tempdir().unwrap();
        let folder = directory.path().join("édition & $(literal), folder");
        std::fs::create_dir(&folder).unwrap();
        let file = folder.join("-photo, sample & literal.tiff");
        std::fs::write(&file, b"reveal fixture").unwrap();
        let absolute_file = std::path::absolute(&file).unwrap().into_os_string();
        let absolute_folder = std::path::absolute(&folder).unwrap().into_os_string();
        let file_before = std::fs::read(&file).unwrap();
        let windows = command_for(&file, Platform::Windows).unwrap();
        let mut select = OsString::from("/select,");
        select.push(&absolute_file);
        assert_eq!(windows.program, "explorer.exe");
        assert_eq!(windows.arguments, vec![select]);
        assert_eq!(
            command_for(&folder, Platform::Windows).unwrap().arguments,
            vec![absolute_folder.clone()]
        );
        let mac = command_for(&file, Platform::Mac).unwrap();
        assert_eq!(mac.program, "open");
        assert_eq!(mac.arguments, vec![OsString::from("-R"), absolute_file]);
        assert_eq!(
            command_for(&folder, Platform::Mac).unwrap().arguments,
            vec![absolute_folder.clone()]
        );
        let unix = command_for(&file, Platform::Unix).unwrap();
        assert_eq!(unix.program, "xdg-open");
        assert_eq!(unix.arguments, vec![absolute_folder.clone()]);
        assert_eq!(
            command_for(&folder, Platform::Unix).unwrap().arguments,
            vec![absolute_folder]
        );
        assert_eq!(std::fs::read(&file).unwrap(), file_before);
    }

    #[test]
    fn missing_and_empty_paths_fail_before_any_browser_is_started() {
        let directory = tempfile::tempdir().unwrap();
        for platform in [Platform::Windows, Platform::Mac, Platform::Unix] {
            assert!(command_for(Path::new(""), platform).is_err());
            let missing = directory.path().join("missing photograph.tiff");
            let error = command_for(&missing, platform).err().unwrap().to_string();
            assert!(
                error.contains("no longer available") && error.contains("missing photograph.tiff")
            );
        }
    }
}
