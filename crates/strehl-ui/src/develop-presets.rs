//! Portable photographic looks. No photograph identity, mask geometry, source
//! repair instructions or measured Adaptive fields may enter this format.
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::{
    collections::HashSet,
    io::{Read, Write},
    path::{Path, PathBuf},
};
use strehl_edit::{AdaptiveIntent, AdaptiveParameters, Adjustments, DevelopmentRecipe};

const VERSION: u32 = 1;
const MAX_BYTES: usize = 1024 * 1024;
const MAX_PRESETS: usize = 256;
const MAX_NAME_BYTES: usize = 192;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct AdaptivePreset {
    pub intent: AdaptiveIntent,
    pub amount: f32,
    pub parameters: AdaptiveParameters,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PresetSettings {
    pub adjustments: Adjustments,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub adaptive: Option<AdaptivePreset>,
}

impl PresetSettings {
    pub fn validate(&self) -> Result<()> {
        self.adjustments.validate()?;
        if let Some(adaptive) = &self.adaptive {
            ensure!(
                adaptive.amount.is_finite() && (0.0..=1.0).contains(&adaptive.amount),
                "Adaptive amount must be between 0 and 1"
            );
            adaptive.parameters.validate()?;
        }
        Ok(())
    }

    /// Target identity is supplied by the destination, never by the preset.
    pub fn capture(recipe: &DevelopmentRecipe, region: Option<&str>) -> Result<Self> {
        recipe.validate()?;
        let adjustments = match region {
            Some(id) => {
                recipe
                    .regions
                    .iter()
                    .find(|r| r.id == id)
                    .context("The selected region no longer exists")?
                    .adjustments
            }
            None => recipe.global,
        };
        Ok(Self {
            adjustments,
            adaptive: None,
        })
    }

    /// Prepare a candidate only. The caller publishes once after any Adaptive
    /// analysis of the destination, keeping one application one Undo action.
    pub fn apply_controls(
        &self,
        recipe: &DevelopmentRecipe,
        region: Option<&str>,
    ) -> Result<DevelopmentRecipe> {
        self.validate()?;
        recipe.validate()?;
        let mut candidate = recipe.clone();
        match region {
            Some(id) => {
                let target = candidate
                    .regions
                    .iter_mut()
                    .find(|r| r.id == id)
                    .context("The selected region no longer exists")?;
                ensure!(
                    target.enabled,
                    "Enable the selected region before applying a preset"
                );
                target.adjustments = self.adjustments;
            }
            None => candidate.global = self.adjustments,
        }
        candidate.clear_adaptive_scope(region);
        candidate.validate()?;
        Ok(candidate)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Preset {
    pub id: String,
    pub name: String,
    pub settings: PresetSettings,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Library {
    version: u32,
    pub presets: Vec<Preset>,
}

impl Default for Library {
    fn default() -> Self {
        Self {
            version: VERSION,
            presets: Vec::new(),
        }
    }
}

impl Library {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.version == VERSION,
            "This preset library requires a newer Strehl version"
        );
        ensure!(
            self.presets.len() <= MAX_PRESETS,
            "The preset library is limited to {MAX_PRESETS} looks"
        );
        let mut ids = HashSet::new();
        let mut names = HashSet::new();
        for preset in &self.presets {
            ensure!(
                preset.id.len() == 32 && preset.id.bytes().all(|b| b.is_ascii_hexdigit()),
                "Invalid preset identity"
            );
            ensure!(ids.insert(&preset.id), "Duplicate preset identity");
            ensure!(
                checked_name(&preset.name)? == preset.name,
                "Preset names cannot start or end with whitespace"
            );
            ensure!(
                names.insert(preset.name.to_lowercase()),
                "Preset names must be distinct"
            );
            preset.settings.validate()?;
        }
        Ok(())
    }

    pub fn add(&mut self, name: &str, settings: PresetSettings) -> Result<String> {
        settings.validate()?;
        let name = self.available_name(name, None)?;
        ensure!(
            self.presets.len() < MAX_PRESETS,
            "The preset library is full"
        );
        let id = random_id()?;
        self.presets.push(Preset {
            id: id.clone(),
            name,
            settings,
        });
        Ok(id)
    }

    pub fn rename(&mut self, id: &str, name: &str) -> Result<()> {
        let name = self.available_name(name, Some(id))?;
        self.presets
            .iter_mut()
            .find(|p| p.id == id)
            .context("This preset no longer exists")?
            .name = name;
        Ok(())
    }

    pub fn remove(&mut self, id: &str) -> Result<(usize, Preset)> {
        let index = self
            .presets
            .iter()
            .position(|p| p.id == id)
            .context("This preset no longer exists")?;
        Ok((index, self.presets.remove(index)))
    }

    pub fn restore(&mut self, index: usize, preset: Preset) -> Result<()> {
        let mut candidate = self.clone();
        candidate
            .presets
            .insert(index.min(candidate.presets.len()), preset);
        candidate.validate()?;
        *self = candidate;
        Ok(())
    }

    fn available_name(&self, name: &str, except: Option<&str>) -> Result<String> {
        let name = checked_name(name)?;
        ensure!(
            !self
                .presets
                .iter()
                .any(|p| Some(p.id.as_str()) != except
                    && p.name.to_lowercase() == name.to_lowercase()),
            "A preset with that name already exists"
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

fn random_id() -> Result<String> {
    let mut bytes = [0u8; 16];
    getrandom::fill(&mut bytes).map_err(|e| anyhow::anyhow!("Creating preset identity: {e}"))?;
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}

pub(crate) fn library_path(catalog: &Path) -> PathBuf {
    catalog.with_file_name("develop-presets.json")
}

/// An explicit recovery action always makes the pending library durable before
/// its caller reloads another window's saved version. Originals stay untouched.
pub(crate) fn save_recovery(path: &Path, library: &Library) -> Result<PathBuf> {
    let recovery = path.with_file_name(format!("develop-presets-recovered-{}.json", random_id()?));
    save(&recovery, library, None)?;
    Ok(recovery)
}

/// Retain the exact input bytes for conflict detection. A malformed library
/// returns an error; callers must not replace it with an empty writable library.
pub(crate) struct LoadedLibrary {
    pub library: Library,
    pub bytes: Option<Vec<u8>>,
}

pub(crate) fn load(path: &Path) -> Result<LoadedLibrary> {
    let bytes = read_optional(path)?;
    let library = match &bytes {
        Some(bytes) => serde_json::from_slice::<Library>(bytes).context("Reading saved presets")?,
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
        "Preset library exceeds its size limit"
    );
    let mut bytes = Vec::new();
    file.take((MAX_BYTES + 1) as u64).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() <= MAX_BYTES,
        "Preset library exceeds its size limit"
    );
    Ok(Some(bytes))
}

/// Worker-only persistence. Replace on the same filesystem after syncing, and
/// leave the original file intact on validation, write or conflict failures.
pub(crate) fn save(path: &Path, library: &Library, expected: Option<&[u8]>) -> Result<Vec<u8>> {
    library.validate()?;
    let bytes = serde_json::to_vec_pretty(library)?;
    ensure!(
        bytes.len() <= MAX_BYTES,
        "Preset library exceeds its size limit"
    );
    let parent = path
        .parent()
        .context("Preset library needs a parent directory")?;
    std::fs::create_dir_all(parent)?;
    // A persistent inode plus an OS lock avoids both the read/rename race
    // between windows and stale create-new locks after a process crash. Do not
    // unlink it: another process may already hold a handle to this same inode.
    let lock = std::fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(path.with_extension("lock"))?;
    lock.try_lock().map_err(|error| {
        anyhow::anyhow!("Another window is saving presets. Retry when it finishes: {error}")
    })?;
    ensure!(
        read_optional(path)?.as_deref() == expected,
        "Saved presets changed in another window. Your pending changes remain here; reload before replacing them."
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
        // Check again after preparing the file, before touching saved content.
        ensure!(
            read_optional(path)?.as_deref() == expected,
            "Saved presets changed during the save"
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
#[path = "develop-presets-tests.rs"]
mod tests;
