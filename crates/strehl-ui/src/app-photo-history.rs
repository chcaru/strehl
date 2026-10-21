//! Photograph-specific versions. Workers own hashing; UI owns publication.
use super::*;
use crate::workspace_history::{PhotoExport, PhotoVersion, photographs};
use std::sync::Arc;
use strehl_edit::{DevelopmentRecipe, ExportSettings, LinearImage};

struct Guard {
    path: PathBuf,
    revision: u64,
    image: Arc<LinearImage>,
    source: PathBuf,
}
enum Prepared {
    Saved(PhotoVersion),
    Unchanged {
        version_id: String,
    },
    Restore {
        version_id: String,
        backup: PhotoVersion,
        recipe: DevelopmentRecipe,
    },
    Export {
        version: PhotoVersion,
        path: PathBuf,
        settings: ExportSettings,
    },
    Recorded(PhotoExport),
    Opened,
}
struct Pending {
    durable: bool,
    guard: Option<Guard>,
    task: Task<Prepared>,
}
struct Delivery {
    version: PhotoVersion,
    path: PathBuf,
    settings: ExportSettings,
}
struct NameDraft {
    path: PathBuf,
    name: String,
    focus: bool,
}

#[derive(Default)]
pub(super) struct PhotoHistoryState {
    pending: Option<Pending>,
    delivery: Option<Delivery>,
    restore_after_open: Option<(String, PathBuf)>,
    draft: Option<NameDraft>,
    error: Option<String>,
    status: Option<String>,
    dirty: bool,
    failed_operation: bool,
}

impl StrehlApp {
    pub(super) fn photo_history_snapshot(&self) -> serde_json::Value {
        let versions: Vec<_> = self
            .catalog
            .photo_versions
            .iter()
            .filter(|v| Some(&v.owner.output) == self.editor.path.as_ref())
            .rev()
            .take(64)
            .collect();
        let exports: Vec<_> = self
            .catalog
            .photo_exports
            .iter()
            .filter(|e| {
                self.catalog.photo_versions.iter().any(|v| {
                    v.id == e.version && Some(&v.owner.output) == self.editor.path.as_ref()
                })
            })
            .rev()
            .take(128)
            .collect();
        serde_json::json!({"busy":self.photo_history_busy(),"error":self.photo_history.error,"status":self.photo_history.status,"versions":versions,"exports":exports,"list_limit":{"versions":64,"exports":128}})
    }

    pub(super) fn photo_history_busy(&self) -> bool {
        self.photo_history.pending.is_some()
            || self.photo_history.delivery.is_some()
            || self.photo_history.restore_after_open.is_some()
    }

    fn photo_history_guard(&self) -> anyhow::Result<Guard> {
        let path = self
            .editor
            .path
            .clone()
            .ok_or_else(|| anyhow::anyhow!("Open a photograph first."))?;
        anyhow::ensure!(
            self.result.as_ref() == Some(&path)
                && self.editor.loading.is_none()
                && !self.adaptive_busy()
                && !self.presets_busy()
                && !self.editor.magic_pending(),
            "Wait for the current photograph operation to finish."
        );
        let image = self
            .editor
            .loaded
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("The photograph is still opening."))?
            .image
            .clone();
        Ok(Guard {
            path,
            revision: self.editor.revision,
            image,
            source: self.editor.loaded.as_ref().unwrap().source.clone(),
        })
    }

    fn history_guard_matches(&self, guard: &Guard) -> bool {
        self.editor.path.as_ref() == Some(&guard.path)
            && self.result.as_ref() == Some(&guard.path)
            && self.editor.revision == guard.revision
            && self.editor.loading.is_none()
            && self
                .editor
                .loaded
                .as_ref()
                .is_some_and(|p| Arc::ptr_eq(&p.image, &guard.image))
            && !self.adaptive_busy()
            && !self.presets_busy()
            && !self.editor.magic_pending()
    }

    pub(super) fn open_save_edit_version(&mut self) {
        if let Some(path) = self.editor.path.clone() {
            self.photo_history.draft = Some(NameDraft {
                path,
                name: "Untitled edit".into(),
                focus: true,
            });
            self.photo_history.error = None;
        }
    }

    pub(super) fn save_edit_version(&mut self, name: &str) -> anyhow::Result<()> {
        anyhow::ensure!(
            !self.photo_history_busy(),
            "Wait for photograph history to finish."
        );
        let name = photographs::checked_name(name)?;
        self.editor.commit_edit();
        let guard = self.photo_history_guard()?;
        let owner = self.catalog.photo_owner(&guard.path);
        let root = self
            .catalog
            .history_root()
            .ok_or_else(|| anyhow::anyhow!("No project storage folder is available."))?;
        let image = guard.image.clone();
        let source = guard.source.clone();
        let recipe = self.editor.recipe.clone();
        self.photo_history.pending = Some(Pending {
            durable: true,
            guard: None,
            task: jobs::spawn_task("strehl-save-version", move |cancelled| {
                Ok(Prepared::Saved(photographs::save_version(
                    &root, owner, &name, recipe, &image, &source, &cancelled,
                )?))
            }),
        });
        self.photo_history.error = None;
        self.photo_history.failed_operation = false;
        Ok(())
    }

    pub(super) fn restore_edit_version(&mut self, id: &str) -> anyhow::Result<()> {
        anyhow::ensure!(
            !self.photo_history_busy(),
            "Wait for photograph history to finish."
        );
        let version = self
            .catalog
            .photo_versions
            .iter()
            .find(|v| v.id == id)
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("This edit version is no longer available."))?;
        if self.editor.path.as_ref() != Some(&version.owner.output)
            || self.result.as_ref() != Some(&version.owner.output)
        {
            self.editor.ensure_saved_on_close()?;
            self.open_history_photograph(&version.owner)?;
            self.photo_history.restore_after_open = Some((id.into(), version.owner.output));
            return Ok(());
        }
        self.editor.commit_edit();
        let guard = self.photo_history_guard()?;
        let root = self
            .catalog
            .history_root()
            .ok_or_else(|| anyhow::anyhow!("No project storage folder is available."))?;
        let owner = self.catalog.photo_owner(&guard.path);
        let image = guard.image.clone();
        let source = guard.source.clone();
        let current = self.editor.recipe.clone();
        self.photo_history.pending = Some(Pending {
            durable: true,
            guard: Some(guard),
            task: jobs::spawn_task("strehl-restore-version", move |cancelled| {
                let recipe = photographs::read_version(
                    &root, &version, &owner, &image, &source, &cancelled,
                )?;
                if recipe == current {
                    return Ok(Prepared::Unchanged {
                        version_id: version.id,
                    });
                }
                let name = format!(
                    "Before restoring {}",
                    version.name.chars().take(90).collect::<String>()
                );
                let backup = photographs::save_version(
                    &root, owner, &name, current, &image, &source, &cancelled,
                )?;
                Ok(Prepared::Restore {
                    version_id: version.id,
                    backup,
                    recipe,
                })
            }),
        });
        Ok(())
    }

    pub(super) fn start_tracked_export(
        &mut self,
        path: PathBuf,
        settings: ExportSettings,
    ) -> anyhow::Result<()> {
        anyhow::ensure!(
            !self.photo_history_busy() && self.editor.exporting.is_none(),
            "Wait for the current export or version operation."
        );
        settings.validate()?;
        anyhow::ensure!(
            !path.exists(),
            "Choose a new filename; existing photographs are never replaced."
        );
        jobs::validate_export_destination(
            self.stack.as_ref().map(|s| s.directory.as_path()),
            path.parent()
                .ok_or_else(|| anyhow::anyhow!("Choose an export folder."))?,
        )?;
        self.editor.commit_edit();
        let guard = self.photo_history_guard()?;
        let root = self
            .catalog
            .history_root()
            .ok_or_else(|| anyhow::anyhow!("No project storage folder is available."))?;
        let owner = self.catalog.photo_owner(&guard.path);
        let image = guard.image.clone();
        let source = guard.source.clone();
        let recipe = self.editor.recipe.clone();
        let name = format!(
            "Export · {}",
            path.file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .chars()
                .take(100)
                .collect::<String>()
        );
        self.photo_history.pending = Some(Pending {
            durable: true,
            guard: Some(guard),
            task: jobs::spawn_task("strehl-export-version", move |cancelled| {
                let version = photographs::save_version(
                    &root, owner, &name, recipe, &image, &source, &cancelled,
                )?;
                Ok(Prepared::Export {
                    version,
                    path,
                    settings,
                })
            }),
        });
        self.photo_history.error = None;
        self.photo_history.failed_operation = false;
        Ok(())
    }

    pub(super) fn handle_photo_history_action(
        &mut self,
        action: crate::project_explorer::ExplorerAction,
    ) {
        use crate::project_explorer::ExplorerAction;
        let result = match action {
            ExplorerAction::RestoreVersion { id } => self.restore_edit_version(&id),
            ExplorerAction::OpenExport { id } => self.open_recorded_export(&id),
            ExplorerAction::RevealPath { path } => {
                if self.photo_history_busy() {
                    Err(anyhow::anyhow!("Wait for photograph history to finish."))
                } else {
                    self.photo_history.pending = Some(Pending {
                        durable: false,
                        guard: None,
                        task: jobs::spawn_task("strehl-reveal-path", move |_| {
                            crate::reveal_path::reveal(&path)?;
                            Ok(Prepared::Opened)
                        }),
                    });
                    Ok(())
                }
            }
            _ => Ok(()),
        };
        if let Err(error) = result {
            self.photo_history.error = Some(error.to_string());
        }
    }

    fn open_recorded_export(&mut self, id: &str) -> anyhow::Result<()> {
        anyhow::ensure!(
            !self.photo_history_busy(),
            "Wait for photograph history to finish."
        );
        let record = self
            .catalog
            .photo_exports
            .iter()
            .find(|e| e.id == id)
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("This export is no longer available."))?;
        self.photo_history.pending = Some(Pending {
            durable: false,
            guard: None,
            task: jobs::spawn_task("strehl-open-export", move |cancelled| {
                photographs::verify_export(&record, &cancelled)?;
                #[cfg(windows)]
                let mut command = std::process::Command::new("explorer.exe");
                #[cfg(target_os = "macos")]
                let mut command = std::process::Command::new("open");
                #[cfg(all(not(windows), not(target_os = "macos")))]
                let mut command = std::process::Command::new("xdg-open");
                command.arg(&record.path).spawn()?;
                Ok(Prepared::Opened)
            }),
        });
        Ok(())
    }

    pub(super) fn poll_photo_history(&mut self, ctx: &egui::Context) {
        if let Some((id, path)) = self.photo_history.restore_after_open.clone() {
            if self.editor.path.as_ref() == Some(&path)
                && self.editor.loading.is_none()
                && self.result.as_ref() == Some(&path)
            {
                self.photo_history.restore_after_open = None;
                if let Err(e) = self.restore_edit_version(&id) {
                    self.photo_history.error = Some(e.to_string());
                }
            } else if self.replay.is_none()
                && self.scan.is_none()
                && self.editor.loading.is_none()
                && self.pending_result.is_none()
            {
                self.photo_history.restore_after_open = None;
                self.photo_history.error = Some(
                    "Opening the saved photograph was interrupted. Select its version again."
                        .into(),
                );
            }
        }
        let ready =
            self.photo_history
                .pending
                .as_ref()
                .and_then(|p| match p.task.receiver.try_recv() {
                    Ok(v) => Some(v),
                    Err(mpsc::TryRecvError::Empty) => None,
                    Err(mpsc::TryRecvError::Disconnected) => {
                        Some(Err("Photograph history worker ended; try again.".into()))
                    }
                });
        if let Some(ready) = ready {
            let pending = self.photo_history.pending.take().unwrap();
            let current = pending
                .guard
                .as_ref()
                .is_none_or(|g| self.history_guard_matches(g));
            let result = (|| -> anyhow::Result<()> {
                match ready.map_err(anyhow::Error::msg)? {
                    Prepared::Saved(version) => {
                        let output = version.owner.output.clone();
                        let id = version.id.clone();
                        self.catalog.add_photo_version(version)?;
                        if self.editor.path.as_ref() == Some(&output) {
                            self.project_explorer.reveal_photo_history(
                                &mut self.catalog,
                                &output,
                                Some(&id),
                            );
                        }
                        self.photo_history.status = Some("Edit version saved in Projects.".into());
                        self.photo_history.dirty = true;
                    }
                    Prepared::Unchanged { version_id } => {
                        anyhow::ensure!(
                            current,
                            "The photograph changed while restoring. Your current edits were kept."
                        );
                        if let Some(path) = self.editor.path.as_ref() {
                            self.project_explorer.reveal_photo_history(
                                &mut self.catalog,
                                path,
                                Some(&version_id),
                            );
                        }
                        self.photo_history.status =
                            Some("This edit version is already applied.".into());
                    }
                    Prepared::Restore {
                        version_id,
                        backup,
                        recipe,
                    } => {
                        self.catalog.add_photo_version(backup)?;
                        self.photo_history.dirty = true;
                        anyhow::ensure!(
                            current,
                            "The photograph changed while restoring. Your current edits were kept."
                        );
                        // Persist the recovery version before changing the live recipe.
                        self.catalog.save()?;
                        self.photo_history.dirty = false;
                        self.editor.replace(recipe)?;
                        self.editor.before = false;
                        if let Some(path) = self.editor.path.as_ref() {
                            self.project_explorer.reveal_photo_history(
                                &mut self.catalog,
                                path,
                                Some(&version_id),
                            );
                        }
                        self.photo_history.status =
                            Some("Version restored · Undo returns to your previous edits.".into());
                    }
                    Prepared::Export {
                        version,
                        path,
                        settings,
                    } => {
                        self.catalog.add_photo_version(version.clone())?;
                        self.photo_history.dirty = true;
                        anyhow::ensure!(
                            current,
                            "The photograph changed while preparing export. Review it and export again."
                        );
                        self.catalog.save()?;
                        self.photo_history.dirty = false;
                        self.editor
                            .export_with_settings(path.clone(), settings.clone())?;
                        self.photo_history.delivery = Some(Delivery {
                            version,
                            path,
                            settings,
                        });
                    }
                    Prepared::Recorded(record) => {
                        self.catalog.add_photo_export(record)?;
                        self.photo_history.dirty = true;
                        self.photo_history.status = Some("Export recorded in Projects.".into());
                    }
                    Prepared::Opened => {}
                }
                Ok(())
            })();
            if let Err(e) = result {
                // Browser/open actions do not put unsaved history at risk.
                // Their feedback must not replace an earlier durable failure.
                if pending.durable || !self.photo_history.failed_operation {
                    self.photo_history.error = Some(e.to_string());
                }
                self.photo_history.failed_operation |= pending.durable;
            }
        }
        if self.photo_history.delivery.is_some() && self.editor.exporting.is_none() {
            let delivery = self.photo_history.delivery.take().unwrap();
            if self.editor.last_export.as_ref() == Some(&delivery.path) {
                self.photo_history.pending = Some(Pending {
                    durable: true,
                    guard: None,
                    task: jobs::spawn_task("strehl-record-export", move |cancelled| {
                        Ok(Prepared::Recorded(photographs::record_export(
                            &delivery.version,
                            delivery.path,
                            delivery.settings,
                            &cancelled,
                        )?))
                    }),
                });
            }
        }
        if self.photo_history.dirty && self.photo_history.error.is_none() {
            match self.catalog.save() {
                Ok(()) => self.photo_history.dirty = false,
                Err(e) => {
                    self.photo_history.error = Some(format!("Saving photograph history: {e}"))
                }
            }
        }
        if self.photo_history_busy() {
            ctx.request_repaint_after(Duration::from_millis(60));
        }
    }

    pub(super) fn flush_photo_history(&mut self, ctx: &egui::Context) -> anyhow::Result<bool> {
        self.poll_photo_history(ctx);
        if self.photo_history_busy() {
            return Ok(false);
        }
        if self.photo_history.failed_operation {
            anyhow::bail!(
                "Photograph history needs attention: {}",
                self.photo_history
                    .error
                    .as_deref()
                    .unwrap_or("Review the failed action in Projects")
            );
        }
        if self.photo_history.dirty {
            self.catalog.save()?;
            self.photo_history.dirty = false;
        }
        Ok(true)
    }

    pub(super) fn photo_history_edit_actions(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            if ui
                .add_enabled(
                    !self.photo_history_busy(),
                    egui::Button::new("Save version…"),
                )
                .clicked()
            {
                self.open_save_edit_version();
            }
            if ui
                .small_button("Versions")
                .on_hover_text("Browse this photograph’s versions and exports in Projects")
                .clicked()
            {
                if let Some(path) = self.editor.path.as_ref() {
                    self.project_explorer
                        .reveal_photo_history(&mut self.catalog, path, None);
                }
                self.sidebar = Some(workspace::Sidebar::Projects);
            }
        });
        self.photo_history_panel(ui);
    }

    pub(super) fn photo_history_panel(&mut self, ui: &mut egui::Ui) {
        if self
            .photo_history
            .draft
            .as_ref()
            .is_some_and(|d| self.editor.path.as_ref() != Some(&d.path))
        {
            self.photo_history.draft = None;
        }
        let busy = self.photo_history_busy();
        let mut save = None;
        let mut cancel = false;
        if let Some(draft) = &mut self.photo_history.draft {
            ui.label(RichText::new("Save edit version").small().color(MUTED));
            let field = ui.add(
                egui::TextEdit::singleline(&mut draft.name)
                    .desired_width((ui.available_width() - 8.0).max(1.0))
                    .char_limit(120),
            );
            if draft.focus {
                field.request_focus();
                draft.focus = false;
            }
            ui.horizontal(|ui| {
                if ui.add_enabled(!busy, egui::Button::new("Save")).clicked() {
                    save = Some(());
                }
                cancel = ui.small_button("Cancel").clicked();
            });
            if field.has_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                save = Some(());
            }
        } else if self.sidebar == Some(workspace::Sidebar::Projects)
            && self.editor.loaded.is_some()
            && ui
                .add_enabled(
                    !self.photo_history_busy(),
                    egui::Button::new("Save current edit version…"),
                )
                .clicked()
        {
            self.open_save_edit_version();
        }
        if save.is_some() {
            let name = self.photo_history.draft.as_ref().unwrap().name.clone();
            match self.save_edit_version(&name) {
                Ok(()) => self.photo_history.draft = None,
                Err(e) => self.photo_history.error = Some(e.to_string()),
            }
        } else if cancel {
            self.photo_history.draft = None;
        }
        if self.photo_history_busy() {
            ui.horizontal(|ui| {
                ui.spinner();
                ui.label("Preserving photograph history…");
            });
        }
        if let Some(error) = self.photo_history.error.clone() {
            ui.colored_label(AMBER, error);
            if ui
                .small_button(if self.photo_history.dirty {
                    "Retry saving history"
                } else {
                    "Dismiss failed action"
                })
                .clicked()
            {
                self.photo_history.error = None;
                self.photo_history.failed_operation = false;
            }
            if self.photo_history.dirty
                && ui
                    .small_button("Keep recovery copy and reload Projects")
                    .clicked()
            {
                match self.catalog.recover_and_reload() {
                    Ok(path) => {
                        self.photo_history.dirty = false;
                        self.photo_history.failed_operation = false;
                        self.photo_history.error = None;
                        self.photo_history.status = Some(format!(
                            "This window’s history was preserved in {}",
                            path.display()
                        ));
                    }
                    Err(e) => self.photo_history.error = Some(e.to_string()),
                }
            }
        } else if let Some(status) = &self.photo_history.status {
            theme::caption(ui, status);
        }
    }
}

#[cfg(test)]
#[path = "app-photo-history-review-tests.rs"]
mod independent_review_tests;
#[cfg(test)]
#[path = "app-photo-history-tests.rs"]
mod tests;
