//! Preferences (implementation plan 7.1): theme, surround and reduced motion,
//! plus the shell's own memory (inspector width, last station).
//!
//! They are kept in `studio.json` beside the projects catalog, not in the
//! catalog itself: the catalog's format is being migrated (plan 6.7) and
//! these are display choices, not project data. A missing or unreadable
//! file means the defaults.
use crate::studio_theme::{Surround, ThemeName};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

pub(crate) const INSPECTOR_DEFAULT: f32 = 348.0;
pub(crate) const INSPECTOR_MIN: f32 = 300.0;
pub(crate) const INSPECTOR_MAX: f32 = 440.0;
const MAX_BYTES: u64 = 64 * 1024;

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub(crate) struct StudioPrefs {
    pub theme: ThemeName,
    pub surround: Surround,
    pub reduced_motion: bool,
    pub inspector_width: f32,
    /// The last station, 1 to 5; 0 when none was recorded.
    pub station: u8,
}
impl Default for StudioPrefs {
    fn default() -> Self {
        Self {
            theme: ThemeName::Graphite,
            surround: Surround::Theme,
            reduced_motion: false,
            inspector_width: INSPECTOR_DEFAULT,
            station: 0,
        }
    }
}
impl StudioPrefs {
    pub(crate) fn sanitized(mut self) -> Self {
        self.inspector_width = if self.inspector_width.is_finite() {
            self.inspector_width.clamp(INSPECTOR_MIN, INSPECTOR_MAX)
        } else {
            INSPECTOR_DEFAULT
        };
        if self.station > 5 {
            self.station = 0;
        }
        self
    }
}

/// `studio.json` beside a catalog file.
pub(crate) fn path_beside(catalog: &Path) -> PathBuf {
    catalog.with_file_name("studio.json")
}

pub(crate) fn load(path: Option<&Path>) -> StudioPrefs {
    path.filter(|p| std::fs::metadata(p).is_ok_and(|m| m.len() <= MAX_BYTES))
        .and_then(|p| std::fs::read(p).ok())
        .and_then(|bytes| serde_json::from_slice::<StudioPrefs>(&bytes).ok())
        .unwrap_or_default()
        .sanitized()
}

/// Write atomically: a partial file can never replace a good one.
pub(crate) fn save(path: &Path, prefs: &StudioPrefs) -> anyhow::Result<()> {
    let bytes = serde_json::to_vec_pretty(&prefs.sanitized())?;
    let temporary = path.with_extension("json.tmp");
    std::fs::write(&temporary, bytes)?;
    std::fs::rename(&temporary, path)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preferences_round_trip_and_bad_values_fall_back() {
        let directory = tempfile::tempdir().unwrap();
        let path = path_beside(&directory.path().join("projects.json"));
        assert_eq!(path.file_name().unwrap(), "studio.json");
        assert_eq!(load(Some(&path)), StudioPrefs::default(), "missing file");
        let prefs = StudioPrefs {
            theme: ThemeName::Lightbox,
            surround: Surround::Grey,
            reduced_motion: true,
            inspector_width: 412.0,
            station: 3,
        };
        save(&path, &prefs).unwrap();
        assert_eq!(load(Some(&path)), prefs);
        assert!(!path.with_extension("json.tmp").exists());
        std::fs::write(
            &path,
            br#"{"theme":"lightbox","inspector_width":9000,"station":9,"future":1}"#,
        )
        .unwrap();
        let loaded = load(Some(&path));
        assert_eq!(loaded.theme, ThemeName::Lightbox);
        assert_eq!(loaded.inspector_width, INSPECTOR_MAX);
        assert_eq!(loaded.station, 0);
        std::fs::write(&path, b"not json").unwrap();
        assert_eq!(load(Some(&path)), StudioPrefs::default());
        assert_eq!(load(None), StudioPrefs::default());
    }
}
