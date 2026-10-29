//! Explicit pass/segment editing and session output selection.
use super::*;
use crate::session_workspace::{
    MODES, PassSpec, SessionChoose, SessionDraft, SessionMode, mode_description, mode_label,
};

enum LayoutEdit {
    MovePass(usize, usize),
    RemovePass(usize),
    MoveSegment(usize, usize, usize),
    RemoveSegment(usize, usize),
}

impl StrehlApp {
    pub(super) fn reload_session(&mut self, mut session: SessionDraft, preserve_stack: bool) {
        if let Err(error) = session.validate() {
            self.error = Some(error.to_string());
            return;
        }
        self.prepare_session_controls();
        let active = preserve_stack.then_some(self.active_stack).flatten();
        session.sources.clear();
        self.reset_capture();
        self.active_stack = active;
        if active.is_none() {
            self.session_ui.pending_name =
                Some(format!("Session · {}", session.manifest.passes[0].name));
        }
        self.controls.settings.session = Some(session.clone());
        self.scan = Some(jobs::scan_session(session));
        self.status = "Reading ordered session passes…".into();
        self.sidebar = Some(workspace::Sidebar::Projects);
    }

    pub(super) fn prepare_session_controls(&mut self) {
        if self.controls.settings.session.is_none() {
            self.ordinary_recipe = Some(history::Recipe::capture(&self.controls));
        }
        self.controls.settings.temporal_energy = false;
        self.controls.settings.frame_limit = None;
        self.controls.settings.auto_exposure = false;
        self.controls.settings.crop_to_coverage = false;
        self.controls.settings.binned = false;
        self.controls.settings.confidence_map = false;
        self.controls.settings.correct_lateral_ca = false;
    }

    pub(super) fn add_session_directory(&mut self, path: PathBuf, choose: SessionChoose) {
        let Some(mut session) = self.controls.settings.session.clone() else {
            return;
        };
        let path = match std::fs::canonicalize(&path) {
            Ok(path) => path,
            Err(error) => {
                self.error = Some(error.to_string());
                return;
            }
        };
        match choose {
            SessionChoose::Pass => session.manifest.passes.push(PassSpec {
                name: path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned(),
                directories: vec![path],
            }),
            SessionChoose::Segment(pass) => {
                let Some(pass) = session.manifest.passes.get_mut(pass) else {
                    self.error = Some("This pass is no longer present.".into());
                    return;
                };
                pass.directories.push(path);
            }
        }
        self.reload_session(session, true);
    }

    fn choose_session_directory(&mut self, choose: SessionChoose) {
        if self.picker_active() || self.job.is_some() || self.scan.is_some() {
            return;
        }
        self.bracket_browser
            .open(self.stack.as_ref().map(|stack| stack.directory.clone()));
        self.session_ui.chooser = Some(choose);
    }

    pub(super) fn session_start_blocker(&self) -> Option<&'static str> {
        let session = self.controls.settings.session.as_ref()?;
        if session.validate().is_err() {
            return Some("Check the session pass names, folders and RAM budget");
        }
        if session.sources.is_empty()
            || self.session_ui.groups.len() != session.manifest.passes.len()
        {
            return Some("Reload the session sources before stacking");
        }
        let settings = &self.controls.settings;
        if settings.temporal_energy
            || settings.frame_limit.is_some()
            || settings.auto_exposure
            || settings.crop_to_coverage
            || settings.binned
        {
            return Some(
                "Session renders require full resolution and their own pass coverage settings",
            );
        }
        if self.editor.loaded.is_some()
            && self.editor.path == self.result
            && self
                .editor
                .recipe
                .regions
                .iter()
                .any(|region| region.enabled && region.source_range.is_some())
        {
            return Some("Session stacking does not yet support source-range repairs");
        }
        None
    }

    pub(super) fn session_panel(&mut self, ui: &mut egui::Ui) {
        let enabled = self.job.is_none()
            && self.scan.is_none()
            && self.replay.is_none()
            && !self.picker_active();
        let Some(mut session) = self.controls.settings.session.clone() else {
            if self.stack.is_some() && ui.add_enabled(enabled, egui::Button::new("Create multi-stack session…")).on_hover_text("Use this stack as the first pass, then add repeats, exposure passes or aligned layers. The original stack remains in Projects.").clicked() {
                let source = self.stack.as_ref().unwrap().directory.clone();
                self.reload_session(SessionDraft::from_directory(source), false);
            }
            return;
        };
        let before = session.clone();
        let mut edit = None;
        let mut choose = None;
        let mut reload = false;
        ui.add_enabled_ui(enabled, |ui| {
            ui.label(RichText::new("MULTI-STACK SESSION").monospace().size(10.0).color(ACCENT));
            egui::ComboBox::from_id_salt("session-mode").selected_text(mode_label(session.manifest.mode)).show_ui(ui, |ui| {
                for mode in MODES { ui.selectable_value(&mut session.manifest.mode, mode, mode_label(mode)); }
            });
            if session.manifest.mode != before.manifest.mode { session.normalize_mode_options(); }
            theme::caption(ui, mode_description(session.manifest.mode));
            if !matches!(session.manifest.mode, SessionMode::Layers | SessionMode::Mosaic | SessionMode::IndependentViews) {
                theme::caption(ui, "Combine uses matching aperture and ISO. Exposure range may vary shutter time. Keep other differences as aligned layers.");
            }
            ui.add_space(4.0);
            if crate::session_workspace::primary_available(session.manifest.mode) {
            let selected = session.manifest.primary_pass.and_then(|i| session.manifest.passes.get(i)).map_or("Automatic · no preferred pass", |pass| pass.name.as_str()).to_owned();
            egui::ComboBox::from_id_salt("session-primary").selected_text(selected).show_ui(ui, |ui| {
                ui.selectable_value(&mut session.manifest.primary_pass, None, "Automatic · no preferred pass");
                for (i, pass) in session.manifest.passes.iter().enumerate() { ui.selectable_value(&mut session.manifest.primary_pass, Some(i), format!("Primary: {}", pass.name)); }
            });
            theme::caption(ui, if session.manifest.mode == SessionMode::Layers {
                "Primary sets the common reference frame and the first layer to view. Each layer retains its own appearance."
            } else {
                "Primary sets framing and appearance, and keeps its reliable content when matched sources disagree. Automatic framing gives no pass that preference."
            });
            } else {
                theme::caption(ui, if session.manifest.mode == SessionMode::IndependentViews { "Each view keeps its own coordinates and focus evidence; no primary or cross-view alignment." } else { "Mosaic uses measured overlap and coverage; no pass has primary preference." });
            }
            ui.add_space(6.0);
            let pass_count = session.manifest.passes.len();
            for (i, pass) in session.manifest.passes.iter_mut().enumerate() {
                ui.push_id(("session-pass", i), |ui| {
                    egui::Frame::group(ui.style()).show(ui, |ui| {
                        ui.horizontal(|ui| {
                            ui.label(RichText::new(format!("{:02}", i + 1)).color(ACCENT));
                            ui.add(egui::TextEdit::singleline(&mut pass.name).desired_width((ui.available_width() - 78.0).max(50.0)));
                            if ui.add_enabled(i > 0, egui::Button::new("↑").small()).on_hover_text("Move pass earlier").clicked() { edit = Some(LayoutEdit::MovePass(i, i - 1)); }
                            if ui.add_enabled(i + 1 < pass_count, egui::Button::new("↓").small()).on_hover_text("Move pass later").clicked() { edit = Some(LayoutEdit::MovePass(i, i + 1)); }
                            if ui.add_enabled(pass_count > 1, egui::Button::new("×").small()).on_hover_text("Remove this pass from the session").clicked() { edit = Some(LayoutEdit::RemovePass(i)); }
                        });
                        if let Some(group) = self.session_ui.groups.get(i) { theme::caption(ui, &format!("{} captures · {}–{}", group.range.len(), group.range.start + 1, group.range.end)); }
                        for (segment, directory) in pass.directories.iter().enumerate() {
                            ui.horizontal(|ui| {
                                ui.add_sized([(ui.available_width() - 78.0).max(40.0), 18.0], egui::Label::new(RichText::new(format!("{}  {}", segment + 1, directory.file_name().unwrap_or_default().to_string_lossy())).size(10.0).color(MUTED)).truncate()).on_hover_text(directory.display().to_string());
                                if ui.add_enabled(segment > 0, egui::Button::new("↑").small()).on_hover_text("Move folder segment earlier").clicked() { edit = Some(LayoutEdit::MoveSegment(i, segment, segment - 1)); }
                                if ui.add_enabled(segment + 1 < pass.directories.len(), egui::Button::new("↓").small()).on_hover_text("Move folder segment later").clicked() { edit = Some(LayoutEdit::MoveSegment(i, segment, segment + 1)); }
                                if ui.add_enabled(pass.directories.len() > 1, egui::Button::new("×").small()).on_hover_text("Remove folder segment").clicked() { edit = Some(LayoutEdit::RemoveSegment(i, segment)); }
                            });
                        }
                        if ui.small_button("Add continuation folder…").on_hover_text("Append a folder that continues this pass. Captures stay ordered within each folder.").clicked() { choose = Some(SessionChoose::Segment(i)); }
                    });
                });
            }
            ui.horizontal(|ui| {
                if ui.add_enabled(pass_count < 64, egui::Button::new("Add independent pass…")).clicked() { choose = Some(SessionChoose::Pass); }
                if ui.small_button("Reload").on_hover_text("Rescan every ordered source folder and capture a new source snapshot.").clicked() { reload = true; }
            });
            theme::caption(ui, "A pass can continue across folders. Add repeats or changed exposure/lighting as separate passes.");
        });
        if let Some(edit) = edit {
            match edit {
                LayoutEdit::MovePass(from, to) => session.move_pass(from, to),
                LayoutEdit::RemovePass(index) => session.remove_pass(index),
                LayoutEdit::MoveSegment(pass, from, to) => {
                    session.manifest.passes[pass].directories.swap(from, to)
                }
                LayoutEdit::RemoveSegment(pass, segment) => {
                    session.manifest.passes[pass].directories.remove(segment);
                }
            }
            reload = true;
        }
        if reload {
            self.reload_session(session, true);
        } else if session != before {
            self.controls.settings.session = Some(session.clone());
            if let Some(scan) = &self.stack {
                self.session_ui.groups = session.groups(scan).unwrap_or_default();
            }
            self.save_active_draft();
            self.catalog_edit_pending = Some(Instant::now());
        }
        if let Some(choose) = choose {
            self.choose_session_directory(choose);
        }
        ui.add_space(6.0);
    }

    pub(super) fn refresh_session_outputs(&mut self, directory: &Path) {
        self.session_ui.layers.clear();
        self.session_ui.summary = None;
        let Some(session) = &self.controls.settings.session else {
            return;
        };
        let imported = self
            .catalog
            .runs
            .iter()
            .find(|run| run.directory == directory)
            .and_then(|run| run.imported.as_ref());
        self.session_ui.summary = Some(if let Some(provenance) = imported {
            crate::session_workspace::SessionSummary::load_imported(
                directory,
                session,
                provenance.scope(),
            )
        } else {
            crate::session_workspace::SessionSummary::load(directory, session)
        });
        let output = if imported.is_some() {
            directory.to_path_buf()
        } else {
            directory.join("session-output")
        };
        if let Some(prefix) = crate::session_workspace::output_prefix(session.manifest.mode) {
            self.session_ui.layers = (0..session.manifest.passes.len())
                .map(|i| {
                    output
                        .join(format!("{prefix}-{:02}", i + 1))
                        .join("photograph.tiff")
                })
                .filter(|path| path.is_file())
                .collect();
        }
    }

    pub(super) fn session_result_picker(&mut self, ui: &mut egui::Ui) {
        if self.session_ui.layers.is_empty() {
            return;
        }
        let mut selected = self.result.clone();
        ui.horizontal(|ui| {
            ui.label(
                RichText::new(
                    if self
                        .session_ui
                        .summary
                        .as_ref()
                        .is_some_and(|s| s.mode == SessionMode::IndependentViews)
                    {
                        "INDEPENDENT VIEW"
                    } else {
                        "ALIGNED LAYER"
                    },
                )
                .monospace()
                .size(9.0)
                .color(MUTED),
            );
            let current = self
                .session_ui
                .layers
                .iter()
                .position(|path| Some(path) == selected.as_ref())
                .unwrap_or(0);
            let names = self
                .session_ui
                .summary
                .as_ref()
                .map(|summary| {
                    summary
                        .passes
                        .iter()
                        .map(|pass| pass.name.clone())
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default();
            egui::ComboBox::from_id_salt("session-layer-view")
                .selected_text(names.get(current).map_or("Photograph", String::as_str))
                .show_ui(ui, |ui| {
                    for (index, path) in self.session_ui.layers.iter().enumerate() {
                        ui.selectable_value(
                            &mut selected,
                            Some(path.clone()),
                            names.get(index).map_or("Photograph", String::as_str),
                        );
                    }
                });
        });
        self.view_bundle_export_action(ui);
        if selected != self.result
            && let Some(path) = selected
            && let Some(index) = self.session_ui.layers.iter().position(|p| p == &path)
            && let Err(error) = self.select_session_output(index)
        {
            self.error = Some(error.to_string());
        }
    }
}
