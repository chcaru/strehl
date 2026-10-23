//! Compact saved-look browser. Disk and adaptive work stay outside UI painting.
use super::*;
use crate::develop_presets::{
    self, AdaptivePreset, Library, LoadedLibrary, Preset, PresetSettings,
};
use std::sync::Arc;
use strehl_edit::{AdaptiveIntent, DevelopmentRecipe, LinearImage};

struct Applying {
    path: Option<PathBuf>,
    image: Arc<LinearImage>,
    revision: u64,
    region: Option<String>,
    magic_generation: u64,
    name: String,
    task: Task<DevelopmentRecipe>,
}

struct RecoveredLibrary {
    path: PathBuf,
    loaded: Result<LoadedLibrary, String>,
}

enum NameForm {
    Save {
        name: String,
        settings: PresetSettings,
        scope: String,
    },
    Rename {
        id: String,
        name: String,
    },
}

#[derive(Default)]
pub(super) struct PresetState {
    initialized: bool,
    path: Option<PathBuf>,
    library: Library,
    bytes: Option<Vec<u8>>,
    loading: Option<Task<LoadedLibrary>>,
    saving: Option<(u64, Task<Vec<u8>>)>,
    recovering: Option<Task<RecoveredLibrary>>,
    recovery_path: Option<PathBuf>,
    revision: u64,
    saved_revision: u64,
    load_error: Option<String>,
    error: Option<String>,
    filter: String,
    selected: Option<String>,
    form: Option<NameForm>,
    form_generation: u64,
    deleted: Option<(usize, Preset)>,
    applying: Option<Applying>,
    status: Option<String>,
}

fn completed<T>(task: &Task<T>) -> Option<Result<T, String>> {
    match task.receiver.try_recv() {
        Ok(result) => Some(result),
        Err(mpsc::TryRecvError::Empty) => None,
        Err(mpsc::TryRecvError::Disconnected) => {
            Some(Err("The background operation ended. Try again.".into()))
        }
    }
}

impl PresetState {
    fn start_load(&mut self, ctx: &egui::Context) {
        let Some(path) = self.path.clone() else {
            return;
        };
        self.load_error = None;
        let wake = ctx.clone();
        self.loading = Some(jobs::spawn_notifying_task(
            "strehl-load-looks",
            move |_| develop_presets::load(&path),
            move || wake.request_repaint(),
        ));
    }

    fn changed(&mut self) {
        self.revision = self.revision.wrapping_add(1);
        self.error = None;
    }

    fn start_save(&mut self, ctx: &egui::Context) {
        if self.saving.is_some()
            || self.recovering.is_some()
            || self.loading.is_some()
            || self.load_error.is_some()
            || self.error.is_some()
            || self.revision == self.saved_revision
        {
            return;
        }
        let Some(path) = self.path.clone() else {
            self.error =
                Some("No app-state folder is available; these presets are not saved.".into());
            return;
        };
        let library = self.library.clone();
        let expected = self.bytes.clone();
        let wake = ctx.clone();
        self.saving = Some((
            self.revision,
            jobs::spawn_notifying_task(
                "strehl-save-looks",
                move |_| develop_presets::save(&path, &library, expected.as_deref()),
                move || wake.request_repaint(),
            ),
        ));
    }

    fn finish_form(&mut self) -> anyhow::Result<()> {
        match self.form.as_ref() {
            Some(NameForm::Save { name, settings, .. }) => {
                self.selected = Some(self.library.add(name, settings.clone())?);
                self.filter.clear();
            }
            Some(NameForm::Rename { id, name }) => self.library.rename(id, name)?,
            None => return Ok(()),
        }
        self.form = None;
        self.changed();
        Ok(())
    }

    fn keep_recovery_and_reload(&mut self, ctx: &egui::Context) {
        if self.saving.is_some() || self.recovering.is_some() {
            return;
        }
        let Some(path) = self.path.clone() else {
            return;
        };
        let library = self.library.clone();
        let wake = ctx.clone();
        self.recovering = Some(jobs::spawn_notifying_task(
            "strehl-recover-looks",
            move |_| {
                let recovery = develop_presets::save_recovery(&path, &library)?;
                let loaded = develop_presets::load(&path).map_err(|e| e.to_string());
                Ok(RecoveredLibrary {
                    path: recovery,
                    loaded,
                })
            },
            move || wake.request_repaint(),
        ));
    }
}

impl StrehlApp {
    pub(super) fn presets_busy(&self) -> bool {
        self.presets.applying.is_some()
    }

    pub(super) fn poll_presets(&mut self, ctx: &egui::Context) {
        if !self.presets.initialized {
            self.presets.initialized = true;
            self.presets.path = self
                .catalog
                .path
                .as_deref()
                .map(develop_presets::library_path);
            self.presets.start_load(ctx);
        }
        if let Some(result) = self.presets.loading.as_ref().and_then(completed) {
            self.presets.loading = None;
            match result {
                Ok(loaded) => {
                    self.presets.library = loaded.library;
                    self.presets.bytes = loaded.bytes;
                    self.presets.load_error = None;
                }
                Err(error) => {
                    self.presets.load_error = Some(format!(
                        "Presets could not be opened. The saved file has been preserved. {error}"
                    ))
                }
            }
        }
        if let Some(result) = self
            .presets
            .saving
            .as_ref()
            .and_then(|(_, task)| completed(task))
        {
            let (revision, _) = self.presets.saving.take().unwrap();
            match result {
                Ok(bytes) => {
                    self.presets.bytes = Some(bytes);
                    self.presets.saved_revision = revision;
                }
                Err(error) => {
                    self.presets.error = Some(format!("Presets are not saved yet. {error}"))
                }
            }
        }
        if let Some(result) = self.presets.recovering.as_ref().and_then(completed) {
            self.presets.recovering = None;
            match result {
                Ok(recovered) => {
                    self.presets.recovery_path = Some(recovered.path);
                    self.presets.library = Library::default();
                    self.presets.bytes = None;
                    self.presets.saved_revision = self.presets.revision;
                    self.presets.error = None;
                    self.presets.selected = None;
                    self.presets.form = None;
                    self.presets.deleted = None;
                    self.presets.status = Some(
                        "Pending looks kept in a recovery copy; saved presets reloaded.".into(),
                    );
                    match recovered.loaded {
                        Ok(loaded) => {
                            self.presets.library = loaded.library;
                            self.presets.bytes = loaded.bytes;
                            self.presets.load_error = None;
                        }
                        Err(error) => {
                            self.presets.load_error = Some(format!(
                                "The saved library could not be opened. Your pending looks are safe in the recovery copy. {error}"
                            ))
                        }
                    }
                }
                Err(error) => {
                    self.presets.error = Some(format!(
                        "Recovery copy could not be saved; all pending presets remain here. {error}"
                    ))
                }
            }
        }
        self.presets.start_save(ctx);
        if self.presets.applying.as_ref().is_some_and(|pending| {
            pending.path != self.editor.path
                || pending.path != self.result
                || pending.path != self.image_path
                || pending.revision != self.editor.revision
                || pending.region != self.editor.selected
                || pending.magic_generation != self.editor.magic_generation()
                || self.editor.loading.is_some()
                || self
                    .editor
                    .loaded
                    .as_ref()
                    .is_none_or(|loaded| !Arc::ptr_eq(&loaded.image, &pending.image))
        }) {
            self.presets.applying = None;
            self.presets.status =
                Some("Preset cancelled because the photograph or selection changed.".into());
        }
        if let Some(result) = self
            .presets
            .applying
            .as_ref()
            .and_then(|pending| completed(&pending.task))
        {
            let pending = self.presets.applying.take().unwrap();
            match result.and_then(|recipe| self.editor.replace(recipe).map_err(|e| e.to_string())) {
                Ok(()) => {
                    self.editor.before = false;
                    self.presets.status = Some(format!("Applied {}", pending.name));
                }
                Err(error) => {
                    self.presets.status = Some(format!("Preset could not be applied: {error}"))
                }
            }
        }
    }

    /// Used by the deferred close guard: never block the UI on disk work.
    pub(super) fn flush_presets(&mut self, ctx: &egui::Context) -> anyhow::Result<bool> {
        self.poll_presets(ctx);
        if self.presets.recovering.is_some() || self.presets.applying.is_some() {
            return Ok(false);
        }
        if self.presets.revision == self.presets.saved_revision {
            return Ok(true);
        }
        if let Some(error) = &self.presets.error {
            anyhow::bail!(error.clone());
        }
        Ok(false)
    }

    fn save_current_look(&mut self) -> anyhow::Result<()> {
        let target = self.editor.selected.as_deref();
        let mut settings = PresetSettings::capture(&self.editor.recipe, target)?;
        if let Some(spatial) = self.editor.recipe.adaptive_scope(target) {
            settings.adaptive = Some(AdaptivePreset {
                intent: AdaptiveIntent::Balance,
                amount: spatial.amount,
                parameters: spatial.parameters,
            });
        }
        let scope = target
            .and_then(|id| self.editor.recipe.regions.iter().find(|r| r.id == id))
            .map_or_else(|| "Photograph".into(), |r| r.name.clone());
        self.presets.form = Some(NameForm::Save {
            name: String::new(),
            settings,
            scope,
        });
        self.presets.form_generation = self.presets.form_generation.wrapping_add(1);
        self.presets.error = None;
        Ok(())
    }

    fn apply_saved_look(&mut self, id: &str, ctx: &egui::Context) -> anyhow::Result<()> {
        anyhow::ensure!(
            !self.presets_busy() && !self.adaptive_busy() && !self.editor.magic_pending(),
            "Finish or cancel the current adjustment first"
        );
        anyhow::ensure!(
            self.editor.loading.is_none()
                && self.editor.path.is_some()
                && self.editor.path == self.result
                && self.editor.path == self.image_path,
            "Wait for the photograph to open"
        );
        let loaded = self
            .editor
            .loaded
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open a photograph first"))?;
        let preset = self
            .presets
            .library
            .presets
            .iter()
            .find(|p| p.id == id)
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("This preset no longer exists"))?;
        let target = self.editor.selected.clone();
        let candidate = preset
            .settings
            .apply_controls(&self.editor.recipe, target.as_deref())?;
        let Some(adaptive) = preset.settings.adaptive else {
            self.editor.replace(candidate)?;
            self.editor.before = false;
            self.presets.status = Some(format!("Applied {}", preset.name));
            return Ok(());
        };
        let image = Arc::clone(&loaded.image);
        self.editor.commit_edit();
        let worker_image = Arc::clone(&image);
        let worker_target = target.clone();
        let wake = ctx.clone();
        let task = jobs::spawn_notifying_task(
            "strehl-adapt-saved-look",
            move |cancelled| {
                anyhow::ensure!(
                    !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                    "Preset cancelled"
                );
                let suggestion = strehl_edit::analyze_adaptive_with_parameters(
                    &worker_image,
                    &candidate,
                    worker_target.as_deref(),
                    adaptive.intent,
                    adaptive.parameters,
                )?;
                anyhow::ensure!(
                    !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                    "Preset cancelled"
                );
                suggestion.recipe_at(adaptive.amount)
            },
            move || wake.request_repaint(),
        );
        self.presets.applying = Some(Applying {
            path: self.editor.path.clone(),
            image,
            revision: self.editor.revision,
            region: target,
            magic_generation: self.editor.magic_generation(),
            name: preset.name,
            task,
        });
        self.presets.status = None;
        Ok(())
    }

    pub(super) fn presets_panel(&mut self, ui: &mut egui::Ui) {
        let ready = self.editor.loaded.is_some()
            && self.editor.loading.is_none()
            && self.editor.path.is_some()
            && self.editor.path == self.result
            && self.editor.path == self.image_path;
        let writable = self.presets.loading.is_none()
            && self.presets.recovering.is_none()
            && self.presets.load_error.is_none();
        let idle = !self.presets_busy() && !self.adaptive_busy() && !self.editor.magic_pending();
        let target_enabled = self.editor.selected.as_ref().is_none_or(|id| {
            self.editor
                .recipe
                .regions
                .iter()
                .any(|r| &r.id == id && r.enabled)
        });
        ui.horizontal(|ui| {
            theme::caption(
                ui,
                if self.editor.selected.is_some() {
                    "For this selection"
                } else {
                    "For this photograph"
                },
            );
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui
                    .add_enabled(
                        ready && writable && idle,
                        egui::Button::new("Save look…").frame(false),
                    )
                    .clicked()
                    && let Err(error) = self.save_current_look()
                {
                    self.presets.status = Some(error.to_string());
                }
            });
        });
        if self.presets.loading.is_some() {
            theme::caption(ui, "Opening saved looks…");
            return;
        }
        if self.presets.recovering.is_some() {
            theme::caption(ui, "Keeping a recovery copy before reloading…");
            return;
        }
        if let Some(path) = &self.presets.recovery_path {
            ui.horizontal(|ui| {
                theme::caption(ui, "Recovery copy saved");
                if ui
                    .button("Copy path")
                    .on_hover_text(path.display().to_string())
                    .clicked()
                {
                    ui.ctx().copy_text(path.display().to_string());
                }
            });
        }
        if let Some(error) = self.presets.load_error.clone() {
            ui.colored_label(AMBER, error);
            if ui.button("Retry opening presets").clicked() {
                self.presets.start_load(ui.ctx());
            }
            return;
        }
        self.preset_name_form(ui);
        if self.presets.library.presets.is_empty() {
            theme::caption(
                ui,
                "Save the current light and color treatment to reuse it on another photograph or selection.",
            );
        } else {
            if self.presets.library.presets.len() > 5 {
                ui.add(
                    egui::TextEdit::singleline(&mut self.presets.filter)
                        .hint_text("Find a look…")
                        .desired_width(f32::INFINITY),
                );
            }
            let filter = self.presets.filter.to_lowercase();
            let mut apply = None;
            let mut rename = None;
            let mut delete = None;
            egui::ScrollArea::vertical().id_salt("saved-looks").max_height(168.0).auto_shrink([false, true]).show(ui, |ui| {
                for preset in &self.presets.library.presets {
                    if !preset.name.to_lowercase().contains(&filter) { continue; }
                    let selected = self.presets.selected.as_deref() == Some(&preset.id);
                    let response = ui.add(egui::Button::new(&preset.name).truncate().selected(selected).frame(false).min_size(egui::vec2(ui.available_width(), 25.0)));
                    if response.clicked() { self.presets.selected = Some(preset.id.clone()); }
                    if response.double_clicked() && ready && idle && target_enabled { apply = Some(preset.id.clone()); }
                    response.on_hover_text(if preset.settings.adaptive.is_some() { "Light, color and Adaptive — recalculated for the destination. Double-click to apply." } else { "Light and color. Double-click to apply." }).context_menu(|ui| {
                        if ui.button("Rename…").clicked() { rename = Some((preset.id.clone(), preset.name.clone())); ui.close(); }
                        if ui.button("Delete preset").clicked() { delete = Some(preset.id.clone()); ui.close(); }
                    });
                }
            });
            if let Some((id, name)) = rename {
                self.presets.form = Some(NameForm::Rename { id, name });
                self.presets.form_generation = self.presets.form_generation.wrapping_add(1);
            }
            if let Some(id) = delete {
                match self.presets.library.remove(&id) {
                    Ok(deleted) => {
                        self.presets.deleted = Some(deleted);
                        if self.presets.selected.as_ref() == Some(&id) {
                            self.presets.selected = None;
                        }
                        self.presets.changed();
                    }
                    Err(error) => self.presets.status = Some(error.to_string()),
                }
            }
            let label = if self.editor.selected.is_some() {
                "Apply to selection"
            } else {
                "Apply to photograph"
            };
            if ui
                .add_enabled(
                    ready && idle && target_enabled && self.presets.selected.is_some(),
                    egui::Button::new(label).frame(false),
                )
                .clicked()
            {
                apply = self.presets.selected.clone();
            }
            if let Some(id) = apply
                && let Err(error) = self.apply_saved_look(&id, ui.ctx())
            {
                self.presets.status = Some(error.to_string());
            }
        }
        if self.presets.applying.is_some() {
            ui.horizontal(|ui| {
                theme::caption(ui, "Adapting look to this photograph…");
                if ui.button("Cancel").clicked() {
                    self.presets.applying = None;
                    self.presets.status = Some("Preset cancelled.".into());
                }
            });
        }
        if let Some((_, preset)) = &self.presets.deleted {
            let label = format!("Deleted {}", preset.name);
            ui.horizontal(|ui| {
                theme::caption(ui, &label);
                if ui.button("Undo").clicked() {
                    let (index, preset) = self.presets.deleted.clone().unwrap();
                    match self.presets.library.restore(index, preset) {
                        Ok(()) => {
                            self.presets.deleted = None;
                            self.presets.changed();
                        }
                        Err(error) => self.presets.status = Some(error.to_string()),
                    }
                }
            });
        }
        if let Some(error) = self.presets.error.clone() {
            ui.colored_label(AMBER, error);
            if ui.button("Retry saving presets").clicked() {
                self.presets.error = None;
                self.presets.start_save(ui.ctx());
            }
            if ui.button("Keep a recovery copy & reload").on_hover_text("Save every pending look in a separate file, then reload the current saved library. Neither version is overwritten.").clicked() {
                self.presets.keep_recovery_and_reload(ui.ctx());
            }
        } else if self.presets.revision != self.presets.saved_revision {
            theme::caption(ui, "Saving presets…");
        }
        if let Some(status) = &self.presets.status {
            theme::caption(ui, status);
        }
    }

    fn preset_name_form(&mut self, ui: &mut egui::Ui) {
        let Some(form) = self.presets.form.as_mut() else {
            return;
        };
        let (name, scope) = match form {
            NameForm::Save { name, scope, .. } => (name, format!("Save · {scope}")),
            NameForm::Rename { name, .. } => (name, "Rename preset".into()),
        };
        theme::caption(ui, &scope);
        let id = ui.id().with(("preset-name", self.presets.form_generation));
        let response = ui.add(
            egui::TextEdit::singleline(name)
                .id(id)
                .hint_text("Name this look")
                .desired_width(f32::INFINITY)
                .char_limit(96),
        );
        // egui may surrender TextEdit focus at the beginning of Escape's frame.
        let owns_keys = response.has_focus() || ui.memory(|m| m.had_focus_last_frame(id));
        let cancel =
            owns_keys && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape));
        let mut accept =
            owns_keys && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Enter));
        let mut dismiss = cancel;
        ui.horizontal(|ui| {
            accept |= ui.button("Save").clicked();
            dismiss |= ui.button("Cancel").clicked();
        });
        if dismiss {
            self.presets.form = None;
            response.surrender_focus();
        } else if accept {
            match self.presets.finish_form() {
                Ok(()) => response.surrender_focus(),
                Err(error) => self.presets.status = Some(error.to_string()),
            }
        }
    }
}

#[cfg(test)]
#[path = "app-presets-tests.rs"]
mod tests;
