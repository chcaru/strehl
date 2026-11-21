//! Export presets: named export settings ticked and run together as one batch,
//! a file-name template, and a destination remembered per subject. Stored in
//! `export-presets.json` beside the catalog with the develop presets' pattern:
//! a version, an OS lock, an expected-bytes check and an explicit recovery file.
//!
//! A preset carries switches, never personal text: the artist and copyright
//! come from the preferences and the description from the photograph when the
//! batch runs (`ImagePreset::resolve`).
// The Export station (P7 UI) is the first caller; until it lands only the
// tests use this module.
#![allow(dead_code)]
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, HashSet},
    io::{Read, Write},
    path::{Path, PathBuf},
};
use strehl_edit::{
    ExportFormat, ExportMetadata, ExportSettings, OutputColorSpace, Resize, ResizeFilter,
};

const VERSION: u32 = 1;
const MAX_BYTES: usize = 1024 * 1024;
const MAX_PRESETS: usize = 64;
const MAX_NAME_BYTES: usize = 192;
const MAX_TEMPLATE_BYTES: usize = 256;
const MAX_DESTINATIONS: usize = 4096;
/// File stems are kept well below Windows' 255-character component limit.
const MAX_STEM_CHARS: usize = 120;
pub(crate) const DEFAULT_TEMPLATE: &str = "{subject}-{view}-{preset}";

/// One photograph file, encoded from the developed master.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ImagePreset {
    /// `metadata` stays empty here; the switches below fill it per batch.
    pub settings: ExportSettings,
    /// Write the preferences' artist and copyright.
    #[serde(default)]
    pub copyright: bool,
    /// Write the photograph's description.
    #[serde(default)]
    pub description: bool,
}

impl ImagePreset {
    pub fn validate(&self) -> Result<()> {
        self.settings.validate()?;
        ensure!(
            self.settings.metadata.is_empty(),
            "A preset carries metadata switches, not the text itself"
        );
        Ok(())
    }

    /// The settings for one export, with the batch's text filled in.
    pub fn resolve(
        &self,
        artist: &str,
        copyright: &str,
        description: &str,
    ) -> Result<ExportSettings> {
        let mut settings = self.settings.clone();
        settings.metadata = ExportMetadata {
            artist: if self.copyright {
                artist.trim().into()
            } else {
                String::new()
            },
            copyright: if self.copyright {
                copyright.trim().into()
            } else {
                String::new()
            },
            description: if self.description {
                description.trim().into()
            } else {
                String::new()
            },
        };
        settings.validate()?;
        Ok(settings)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum PresetOutput {
    Image(ImagePreset),
    /// The scene-linear master and its development recipe, copied as they are.
    Archive,
}

impl PresetOutput {
    pub fn validate(&self) -> Result<()> {
        match self {
            Self::Image(image) => image.validate(),
            Self::Archive => Ok(()),
        }
    }

    /// File extension of the main file, without the dot.
    pub fn extension(&self) -> &'static str {
        match self {
            Self::Image(image) => match image.settings.format {
                ExportFormat::Avif => "avif",
                ExportFormat::Tiff => "tiff",
                ExportFormat::Png => "png",
                ExportFormat::Jpeg => "jpg",
            },
            Self::Archive => "tiff",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ExportPreset {
    pub id: String,
    pub name: String,
    /// Ticked presets run together.
    pub enabled: bool,
    pub output: PresetOutput,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Library {
    version: u32,
    pub presets: Vec<ExportPreset>,
    pub template: String,
    /// Last destination per subject key.
    #[serde(default)]
    pub destinations: BTreeMap<String, PathBuf>,
}

fn image(name: &str, id: u8, enabled: bool, settings: ExportSettings) -> ExportPreset {
    ExportPreset {
        id: format!("{id:032x}"),
        name: name.into(),
        enabled,
        output: PresetOutput::Image(ImagePreset {
            settings,
            copyright: false,
            description: false,
        }),
    }
}

/// The four starting presets of implementation plan 7.6.
pub(crate) fn default_presets() -> Vec<ExportPreset> {
    let sdr = |format, color_space| ExportSettings {
        format,
        color_space,
        hdr: false,
        quality: 100,
        ..Default::default()
    };
    vec![
        image(
            "Web",
            1,
            true,
            ExportSettings {
                quality: 90,
                resize: Some(Resize {
                    long_edge: 2560,
                    filter: ResizeFilter::Mitchell,
                }),
                ..sdr(ExportFormat::Jpeg, OutputColorSpace::Srgb)
            },
        ),
        image(
            "HDR",
            2,
            true,
            ExportSettings {
                format: ExportFormat::Avif,
                color_space: OutputColorSpace::Rec2020,
                hdr: true,
                ..Default::default()
            },
        ),
        image(
            "Print",
            3,
            false,
            sdr(ExportFormat::Tiff, OutputColorSpace::DisplayP3),
        ),
        ExportPreset {
            id: format!("{:032x}", 4),
            name: "Archive".into(),
            enabled: false,
            output: PresetOutput::Archive,
        },
    ]
}

impl Default for Library {
    fn default() -> Self {
        Self {
            version: VERSION,
            presets: default_presets(),
            template: DEFAULT_TEMPLATE.into(),
            destinations: BTreeMap::new(),
        }
    }
}

impl Library {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.version == VERSION,
            "This export preset library requires a newer Strehl version"
        );
        ensure!(
            self.presets.len() <= MAX_PRESETS,
            "The export preset library is limited to {MAX_PRESETS} presets"
        );
        let mut ids = HashSet::new();
        let mut names = HashSet::new();
        for preset in &self.presets {
            ensure!(
                preset.id.len() == 32 && preset.id.bytes().all(|b| b.is_ascii_hexdigit()),
                "Invalid export preset identity"
            );
            ensure!(ids.insert(&preset.id), "Duplicate export preset identity");
            ensure!(
                checked_name(&preset.name)? == preset.name,
                "Preset names cannot start or end with whitespace"
            );
            ensure!(
                names.insert(preset.name.to_lowercase()),
                "Export preset names must be distinct"
            );
            preset.output.validate()?;
        }
        validate_template(&self.template)?;
        ensure!(
            self.destinations.len() <= MAX_DESTINATIONS,
            "Too many remembered destinations"
        );
        for (subject, path) in &self.destinations {
            ensure!(
                !subject.is_empty() && subject.len() <= 256 && path.is_absolute(),
                "Remembered destinations need a subject and an absolute folder"
            );
        }
        Ok(())
    }

    pub fn add(&mut self, name: &str, output: PresetOutput) -> Result<String> {
        output.validate()?;
        let name = self.available_name(name, None)?;
        ensure!(
            self.presets.len() < MAX_PRESETS,
            "The export preset library is full"
        );
        let id = random_id()?;
        self.presets.push(ExportPreset {
            id: id.clone(),
            name,
            enabled: true,
            output,
        });
        Ok(id)
    }

    fn preset_mut(&mut self, id: &str) -> Result<&mut ExportPreset> {
        self.presets
            .iter_mut()
            .find(|p| p.id == id)
            .context("This export preset no longer exists")
    }

    pub fn rename(&mut self, id: &str, name: &str) -> Result<()> {
        let name = self.available_name(name, Some(id))?;
        self.preset_mut(id)?.name = name;
        Ok(())
    }

    pub fn update(&mut self, id: &str, output: PresetOutput) -> Result<()> {
        output.validate()?;
        self.preset_mut(id)?.output = output;
        Ok(())
    }

    pub fn set_enabled(&mut self, id: &str, enabled: bool) -> Result<()> {
        self.preset_mut(id)?.enabled = enabled;
        Ok(())
    }

    pub fn remove(&mut self, id: &str) -> Result<(usize, ExportPreset)> {
        let index = self
            .presets
            .iter()
            .position(|p| p.id == id)
            .context("This export preset no longer exists")?;
        Ok((index, self.presets.remove(index)))
    }

    pub fn restore(&mut self, index: usize, preset: ExportPreset) -> Result<()> {
        let mut candidate = self.clone();
        candidate
            .presets
            .insert(index.min(candidate.presets.len()), preset);
        candidate.validate()?;
        *self = candidate;
        Ok(())
    }

    /// Ticked presets, in library order: one batch.
    pub fn ticked(&self) -> impl Iterator<Item = &ExportPreset> {
        self.presets.iter().filter(|p| p.enabled)
    }

    pub fn set_template(&mut self, template: &str) -> Result<()> {
        validate_template(template)?;
        self.template = template.into();
        Ok(())
    }

    pub fn destination(&self, subject: &str) -> Option<&Path> {
        self.destinations.get(subject).map(PathBuf::as_path)
    }

    pub fn remember_destination(&mut self, subject: &str, folder: &Path) -> Result<()> {
        ensure!(
            !subject.is_empty() && subject.len() <= 256,
            "A destination needs a subject"
        );
        ensure!(
            folder.is_absolute(),
            "Choose an absolute destination folder"
        );
        ensure!(
            self.destinations.contains_key(subject) || self.destinations.len() < MAX_DESTINATIONS,
            "Too many remembered destinations"
        );
        self.destinations.insert(subject.into(), folder.into());
        Ok(())
    }

    pub fn forget_destination(&mut self, subject: &str) -> Option<PathBuf> {
        self.destinations.remove(subject)
    }

    fn available_name(&self, name: &str, except: Option<&str>) -> Result<String> {
        let name = checked_name(name)?;
        ensure!(
            !self
                .presets
                .iter()
                .any(|p| Some(p.id.as_str()) != except
                    && p.name.to_lowercase() == name.to_lowercase()),
            "An export preset with that name already exists"
        );
        Ok(name)
    }
}

fn checked_name(name: &str) -> Result<String> {
    let name = name.trim();
    ensure!(!name.is_empty(), "Give the preset a name");
    ensure!(
        name.len() <= MAX_NAME_BYTES && name.chars().count() <= 96,
        "Use at most 96 characters and 192 UTF-8 bytes for a preset name"
    );
    ensure!(
        !name.chars().any(char::is_control),
        "Preset names cannot contain control characters"
    );
    Ok(name.into())
}

/// The values a file-name template can use.
#[derive(Clone, Debug, Default)]
pub(crate) struct NameFields<'a> {
    pub subject: &'a str,
    /// The version or view name, for example "Natural" or "Version 2".
    pub view: &'a str,
    pub preset: &'a str,
    /// Caller-formatted, for example `2026-11-21`.
    pub date: &'a str,
}

const TOKENS: [&str; 4] = ["subject", "view", "preset", "date"];

fn validate_template(template: &str) -> Result<()> {
    ensure!(
        !template.trim().is_empty() && template.len() <= MAX_TEMPLATE_BYTES,
        "The name template must be 1..{MAX_TEMPLATE_BYTES} bytes"
    );
    ensure!(
        !template.chars().any(char::is_control),
        "The name template cannot contain control characters"
    );
    let mut rest = template;
    let mut tokens = 0;
    while let Some(open) = rest.find('{') {
        let close = rest[open..]
            .find('}')
            .context("The name template has an unclosed {")?;
        let token = &rest[open + 1..open + close];
        ensure!(
            TOKENS.contains(&token),
            "Unknown name token {{{token}}}; use {{subject}}, {{view}}, {{preset}} or {{date}}"
        );
        tokens += 1;
        rest = &rest[open + close + 1..];
    }
    ensure!(!rest.contains('}'), "The name template has a stray }}");
    ensure!(tokens > 0, "The name template needs at least one {{token}}");
    Ok(())
}

/// Expand a template into a safe file stem (no extension).
pub(crate) fn expand_name(template: &str, fields: &NameFields<'_>) -> Result<String> {
    validate_template(template)?;
    let mut out = String::new();
    let mut rest = template;
    while let Some(open) = rest.find('{') {
        out.push_str(&rest[..open]);
        let close = open + rest[open..].find('}').unwrap_or(0);
        out.push_str(match &rest[open + 1..close] {
            "subject" => fields.subject,
            "view" => fields.view,
            "preset" => fields.preset,
            _ => fields.date,
        });
        rest = &rest[close + 1..];
    }
    out.push_str(rest);
    Ok(sanitize_stem(&out))
}

/// A file stem valid on Windows, macOS and Linux: separators, reserved and
/// control characters become `-`, runs collapse, trailing dots and spaces go,
/// reserved device names gain a `_`, and the length is bounded.
pub(crate) fn sanitize_stem(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        let c = if c.is_control()
            || matches!(c, '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*')
        {
            '-'
        } else {
            c
        };
        if c == '-' && out.ends_with('-') {
            continue;
        }
        out.push(c);
    }
    let mut out: String = out
        .trim_matches(|c: char| c == '-' || c.is_whitespace())
        .chars()
        .take(MAX_STEM_CHARS)
        .collect();
    while out.ends_with('.') || out.ends_with(' ') || out.ends_with('-') {
        out.pop();
    }
    while out.starts_with('.') {
        out.remove(0);
    }
    if out.is_empty() {
        return "untitled".into();
    }
    let base = out
        .split('.')
        .next()
        .unwrap_or_default()
        .to_ascii_uppercase();
    let reserved = matches!(base.as_str(), "CON" | "PRN" | "AUX" | "NUL")
        || ((base.starts_with("COM") || base.starts_with("LPT"))
            && base.len() == 4
            && base.as_bytes()[3].is_ascii_digit());
    if reserved {
        out.push('_');
    }
    out
}

/// The first `stem.ext`, `stem (2).ext`, ... in `folder` that `exists` says is
/// free. Exports never overwrite, so a batch picks fresh names up front.
pub(crate) fn available_path(
    folder: &Path,
    stem: &str,
    extension: &str,
    exists: impl Fn(&Path) -> bool,
) -> Result<PathBuf> {
    for n in 1..=9999u32 {
        let name = if n == 1 {
            format!("{stem}.{extension}")
        } else {
            format!("{stem} ({n}).{extension}")
        };
        let path = folder.join(name);
        if !exists(&path) {
            return Ok(path);
        }
    }
    anyhow::bail!(
        "No free file name for {stem} in {}",
        crate::display_path::display_path(folder)
    )
}

fn random_id() -> Result<String> {
    let mut bytes = [0u8; 16];
    getrandom::fill(&mut bytes)
        .map_err(|e| anyhow::anyhow!("Creating export preset identity: {e}"))?;
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}

pub(crate) fn library_path(catalog: &Path) -> PathBuf {
    catalog.with_file_name("export-presets.json")
}

/// An explicit recovery action makes the pending library durable before its
/// caller reloads another window's saved version. Originals stay untouched.
pub(crate) fn save_recovery(path: &Path, library: &Library) -> Result<PathBuf> {
    let recovery = path.with_file_name(format!("export-presets-recovered-{}.json", random_id()?));
    save(&recovery, library, None)?;
    Ok(recovery)
}

/// The exact bytes read are kept for conflict detection. A malformed library
/// is an error; callers must not replace it with a default writable library.
pub(crate) struct LoadedLibrary {
    pub library: Library,
    pub bytes: Option<Vec<u8>>,
}

pub(crate) fn load(path: &Path) -> Result<LoadedLibrary> {
    let bytes = read_optional(path)?;
    let library = match &bytes {
        Some(bytes) => {
            serde_json::from_slice::<Library>(bytes).context("Reading saved export presets")?
        }
        None => Library::default(),
    };
    library.validate()?;
    Ok(LoadedLibrary { library, bytes })
}

fn read_optional(path: &Path) -> Result<Option<Vec<u8>>> {
    let file = match std::fs::File::open(path) {
        Ok(file) => file,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(e.into()),
    };
    ensure!(
        file.metadata()?.len() <= MAX_BYTES as u64,
        "Export preset library exceeds its size limit"
    );
    let mut bytes = Vec::new();
    file.take((MAX_BYTES + 1) as u64).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() <= MAX_BYTES,
        "Export preset library exceeds its size limit"
    );
    Ok(Some(bytes))
}

/// Worker-only persistence. Replace on the same filesystem after syncing, and
/// leave the original intact on validation, write or conflict failures.
pub(crate) fn save(path: &Path, library: &Library, expected: Option<&[u8]>) -> Result<Vec<u8>> {
    library.validate()?;
    let bytes = serde_json::to_vec_pretty(library)?;
    ensure!(
        bytes.len() <= MAX_BYTES,
        "Export preset library exceeds its size limit"
    );
    let parent = path
        .parent()
        .context("Export preset library needs a parent directory")?;
    std::fs::create_dir_all(parent)?;
    // A persistent inode plus an OS lock, as for the develop presets: never
    // unlinked, because another process may hold a handle to it.
    let lock = std::fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(path.with_extension("lock"))?;
    lock.try_lock().map_err(|error| {
        anyhow::anyhow!("Another window is saving export presets. Retry when it finishes: {error}")
    })?;
    ensure!(
        read_optional(path)?.as_deref() == expected,
        "Saved export presets changed in another window. Your pending changes remain here; reload before replacing them."
    );
    let temporary = path.with_extension(format!("pending-{}", random_id()?));
    let result = (|| {
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        drop(file);
        ensure!(
            read_optional(path)?.as_deref() == expected,
            "Saved export presets changed during the save"
        );
        std::fs::rename(&temporary, path)?;
        Ok(())
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&temporary);
    }
    result?;
    drop(lock);
    Ok(bytes)
}

#[cfg(test)]
#[path = "export-presets-tests.rs"]
mod tests;
