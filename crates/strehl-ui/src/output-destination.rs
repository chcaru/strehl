//! A launcher's working directory is not a suitable place for photographs.
//! Resolve the user's Pictures folder without creating anything at startup;
//! the normal job path validates source/corpus boundaries before any write.
use std::path::PathBuf;

pub(super) fn default_output() -> PathBuf {
    #[cfg(windows)]
    let home = std::env::var_os("USERPROFILE").map(PathBuf::from);
    #[cfg(not(windows))]
    let home = std::env::var_os("HOME").map(PathBuf::from);
    choose_output(pictures_folder(), home)
}

fn choose_output(pictures: Option<PathBuf>, home: Option<PathBuf>) -> PathBuf {
    pictures
        .filter(|path| path.is_absolute())
        .or_else(|| {
            home.filter(|path| path.is_absolute())
                .map(|path| path.join("Pictures"))
        })
        .map(|path| path.join("Strehl"))
        // An unavailable user folder requires an explicit choice. Never use the
        // launcher's cwd, an installation folder, or a temporary directory.
        .unwrap_or_default()
}

#[cfg(windows)]
fn pictures_folder() -> Option<PathBuf> {
    use std::{ffi::OsString, os::windows::ffi::OsStringExt};
    use windows_sys::Win32::{
        System::Com::CoTaskMemFree,
        UI::Shell::{FOLDERID_Pictures, KF_FLAG_DEFAULT, SHGetKnownFolderPath},
    };

    let mut path = std::ptr::null_mut();
    // SAFETY: the folder ID and output pointer remain valid throughout the call.
    // Windows allocates the returned null-terminated UTF-16 path; release it with
    // CoTaskMemFree even if the lookup reports an error.
    unsafe {
        let result = SHGetKnownFolderPath(
            &FOLDERID_Pictures,
            KF_FLAG_DEFAULT as u32,
            std::ptr::null_mut(),
            &mut path,
        );
        let folder = if result >= 0 && !path.is_null() {
            let mut length = 0;
            while *path.add(length) != 0 {
                length += 1;
            }
            Some(PathBuf::from(OsString::from_wide(
                std::slice::from_raw_parts(path, length),
            )))
        } else {
            None
        };
        CoTaskMemFree(path.cast());
        folder
    }
}

#[cfg(not(windows))]
fn pictures_folder() -> Option<PathBuf> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::jobs::tests::TestDirectory;
    use std::{fs, process::Command};

    const RECEIPT: &str = "STREHL_TEST_DEFAULT_OUTPUT_RECEIPT";

    #[test]
    fn default_output_preserves_redirected_pictures_and_refuses_relative_fallbacks() {
        let files = TestDirectory::new("destination-folders");
        let redirected = files.path().join("relocated-pictures");
        let home = files.path().join("user-home");
        assert_eq!(
            choose_output(Some(redirected.clone()), Some(home.clone())),
            redirected.join("Strehl")
        );
        assert_eq!(
            choose_output(Some(PathBuf::from("relative")), Some(home.clone())),
            home.join("Pictures").join("Strehl")
        );
        assert_eq!(choose_output(None, None), PathBuf::new());
        assert_eq!(
            choose_output(None, Some(PathBuf::from("relative"))),
            PathBuf::new()
        );
        assert!(!redirected.exists());
        assert!(!home.exists());
    }

    #[test]
    fn default_output_launch_witness() {
        let Some(receipt) = std::env::var_os(RECEIPT) else {
            return;
        };
        fs::write(receipt, serde_json::to_vec(&default_output()).unwrap()).unwrap();
    }

    #[test]
    fn default_output_ignores_application_launch_directory() {
        let files = TestDirectory::new("destination-launch");
        let launch = files.path().join("installed-application");
        fs::create_dir_all(launch.join("outputs")).unwrap();
        let receipt = files.path().join("destination.json");
        let output = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "app::output_destination::tests::default_output_launch_witness",
                "--nocapture",
            ])
            .current_dir(&launch)
            .env(RECEIPT, &receipt)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "child failed: {} {}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        let actual: PathBuf = serde_json::from_slice(&fs::read(receipt).unwrap()).unwrap();
        assert_eq!(actual, default_output());
        assert!(!actual.starts_with(&launch));
        assert!(actual.as_os_str().is_empty() || actual.is_absolute());
        assert_eq!(fs::read_dir(launch.join("outputs")).unwrap().count(), 0);
    }
}
