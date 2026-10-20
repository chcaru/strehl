//! Durable recipe-only recovery. Original photograph files are never backups.
//! Old-session records are offered explicitly, not applied over newer edits.
use super::*;
use anyhow::{Context as _, ensure};
use serde::{Deserialize, Serialize};
use std::hash::{Hash, Hasher};

const MAX_RECORD_BYTES: usize = 2 * 1024 * 1024;
const MAX_RECOVERY_BYTES: usize = 8 * 1024 * 1024;

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Record {
    version: u32,
    photograph: PathBuf,
    recipe: DevelopmentRecipe,
}

impl EditorState {
    fn recovery_directory(&self) -> anyhow::Result<PathBuf> {
        self.recovery_root
            .clone()
            .or_else(|| {
                crate::workspace_history::default_path()
                    .and_then(|path| path.parent().map(|parent| parent.join("recovered-edits")))
            })
            .ok_or_else(|| anyhow::anyhow!("The application state directory is unavailable"))
    }

    pub(super) fn retain_current_recipe(&mut self) {
        if self.loaded.is_some()
            && self.saved_revision != Some(self.revision)
            && let Some(path) = &self.path
        {
            self.recoveries.insert(path.clone(), self.recipe.clone());
            self.recovered_from_disk.remove(path);
        }
    }

    pub(super) fn forget_recovery(&mut self, path: &Path) {
        if self.recovered_from_disk.contains(path) {
            return;
        }
        self.recoveries.remove(path);
        if let Some(file) = self.recovery_files.remove(path) {
            // A failed cleanup cannot lose edits: the sidecar has already been
            // saved and startup offers any leftover record explicitly.
            let _ = std::fs::remove_file(file);
        }
    }

    pub(super) fn persist_recoveries(&mut self) -> anyhow::Result<()> {
        let records = self
            .recoveries
            .iter()
            .filter(|(path, _)| !self.recovered_from_disk.contains(*path))
            .map(|(path, recipe)| (path.clone(), recipe.clone()))
            .collect::<Vec<_>>();
        if records.is_empty() {
            return Ok(());
        }
        let directory = self.recovery_directory()?;
        std::fs::create_dir_all(&directory).context("Creating edit recovery storage")?;
        for (path, recipe) in records {
            recipe.validate()?;
            let photograph = std::path::absolute(&path)?;
            let mut hasher = std::collections::hash_map::DefaultHasher::new();
            photograph.hash(&mut hasher);
            let file = directory.join(format!("photo-{:016x}.json", hasher.finish()));
            let record = Record {
                version: 1,
                photograph,
                recipe,
            };
            let bytes = serde_json::to_vec_pretty(&record)?;
            ensure!(
                bytes.len() <= MAX_RECORD_BYTES,
                "Recovery recipe exceeds the size limit"
            );
            if file.exists() {
                let previous: Record =
                    serde_json::from_slice(&read_bounded(&file, MAX_RECORD_BYTES)?)?;
                ensure!(
                    previous.photograph == record.photograph,
                    "Recovery record identity conflict"
                );
            }
            write_json_atomic(&file, &bytes).context("Saving recovery recipe")?;
            self.recovery_files.insert(path, file);
        }
        Ok(())
    }

    /// Called once during launch. These records remain opt-in until the human
    /// restores one onto its matching photograph.
    pub fn restore_recoveries(&mut self) {
        if self.recovery_root.is_none() && crate::workspace_history::default_path().is_none() {
            return;
        }
        if let Err(error) = self.read_recoveries() {
            self.error = Some(format!("Reading retained edits: {error:#}"));
        }
    }

    fn read_recoveries(&mut self) -> anyhow::Result<()> {
        let directory = self.recovery_directory()?;
        if !directory.exists() {
            return Ok(());
        }
        let mut total = 0usize;
        let mut errors = Vec::new();
        for entry in std::fs::read_dir(directory)?.take(128) {
            let entry = entry?;
            if !entry.file_type()?.is_file()
                || entry.path().extension().is_none_or(|ext| ext != "json")
            {
                continue;
            }
            let result = (|| -> anyhow::Result<()> {
                let bytes = read_bounded(&entry.path(), MAX_RECORD_BYTES)?;
                total = total.saturating_add(bytes.len());
                ensure!(
                    total <= MAX_RECOVERY_BYTES,
                    "Retained edits exceed the startup read budget"
                );
                let record: Record = serde_json::from_slice(&bytes)?;
                ensure!(
                    record.version == 1 && record.photograph.is_absolute(),
                    "Invalid recovery record"
                );
                record.recipe.validate()?;
                self.recovery_files
                    .insert(record.photograph.clone(), entry.path());
                self.recovered_from_disk.insert(record.photograph.clone());
                self.recoveries
                    .entry(record.photograph)
                    .or_insert(record.recipe);
                Ok(())
            })();
            if let Err(error) = result {
                errors.push(error.to_string());
            }
            if total > MAX_RECOVERY_BYTES {
                break;
            }
        }
        ensure!(
            errors.is_empty(),
            "{} recovery record(s) were not loaded; originals retained. {}",
            errors.len(),
            errors.first().map_or("", String::as_str)
        );
        Ok(())
    }

    /// Closing is safe once the exact current recipe is saved either beside
    /// its photograph or in application-state recovery. If both fail, refuse.
    pub fn ensure_saved_on_close(&mut self) -> anyhow::Result<()> {
        if let Err(primary) = self.flush() {
            self.retain_current_recipe();
            self.persist_recoveries().with_context(|| {
                format!("Photo edits could not be saved ({primary:#}); recovery also failed")
            })?;
            self.error = Some(format!(
                "Edits retained in application recovery because the photograph destination could not be written: {primary:#}"
            ));
        }
        Ok(())
    }
}
