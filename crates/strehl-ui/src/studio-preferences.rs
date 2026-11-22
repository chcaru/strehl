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

/// The longest artist and copyright Strehl writes (`strehl_edit`'s limits).
pub(crate) const MAX_ARTIST_BYTES: usize = 256;
pub(crate) const MAX_COPYRIGHT_BYTES: usize = 512;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub(crate) struct StudioPrefs {
    pub theme: ThemeName,
    pub surround: Surround,
    pub reduced_motion: bool,
    pub inspector_width: f32,
    /// The last station, 1 to 5; 0 when none was recorded.
    pub station: u8,
    /// Quiet mode: hold stacks, repairs and compaction while a full-screen
    /// program is in front (plan 6.6). On unless switched off.
    pub quiet: bool,
    /// The owner's standing text for exports: written when a preset's
    /// "Copyright and description" is on. Export presets never carry it
    /// (`export-presets.rs`); empty writes nothing.
    #[serde(skip_serializing_if = "String::is_empty")]
    pub artist: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub copyright: String,
}
impl Default for StudioPrefs {
    fn default() -> Self {
        Self {
            theme: ThemeName::Graphite,
            surround: Surround::Theme,
            reduced_motion: false,
            inspector_width: INSPECTOR_DEFAULT,
            station: 0,
            quiet: true,
            artist: String::new(),
            copyright: String::new(),
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
        self.artist = export_line(&self.artist, MAX_ARTIST_BYTES);
        self.copyright = export_line(&self.copyright, MAX_COPYRIGHT_BYTES);
        self
    }
}

/// One line of export text as Strehl writes it: trimmed, without control
/// characters, at most `max` UTF-8 bytes (cut at a character boundary).
pub(crate) fn export_line(text: &str, max: usize) -> String {
    let mut out: String = text.chars().filter(|c| !c.is_control()).collect();
    out = out.trim().to_owned();
    if out.len() > max {
        let mut end = max;
        while !out.is_char_boundary(end) {
            end -= 1;
        }
        out.truncate(end);
        out = out.trim_end().to_owned();
    }
    out
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
    let bytes = serde_json::to_vec_pretty(&prefs.clone().sanitized())?;
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
            quiet: false,
            artist: "Chris Caruso".into(),
            copyright: "© 2026 Chris Caruso".into(),
        };
        save(&path, &prefs).unwrap();
        assert_eq!(load(Some(&path)), prefs);
        assert!(!path.with_extension("json.tmp").exists());
        // The export text is cleaned as it is read: trimmed, no controls,
        // within strehl_edit's limits, and an earlier file without it reads.
        std::fs::write(
            &path,
            format!(
                r#"{{"artist":"  Chris\tCaruso \n","copyright":"{}"}}"#,
                "©".repeat(300)
            ),
        )
        .unwrap();
        let loaded = load(Some(&path));
        assert_eq!(loaded.artist, "ChrisCaruso");
        assert!(loaded.copyright.len() <= MAX_COPYRIGHT_BYTES);
        assert!(loaded.copyright.chars().all(|c| c == '©'));
        std::fs::write(&path, br#"{"theme":"lightbox"}"#).unwrap();
        assert_eq!(load(Some(&path)).artist, "");
        let saved = serde_json::to_string(&StudioPrefs::default()).unwrap();
        assert!(!saved.contains("artist"), "empty text is not written");
        std::fs::write(
            &path,
            br#"{"theme":"lightbox","inspector_width":9000,"station":9,"future":1}"#,
        )
        .unwrap();
        let loaded = load(Some(&path));
        assert_eq!(loaded.theme, ThemeName::Lightbox);
        assert_eq!(loaded.inspector_width, INSPECTOR_MAX);
        assert_eq!(loaded.station, 0);
        assert!(loaded.quiet, "Quiet is on unless switched off");
        std::fs::write(&path, b"not json").unwrap();
        assert_eq!(load(Some(&path)), StudioPrefs::default());
        assert_eq!(load(None), StudioPrefs::default());
    }
}
