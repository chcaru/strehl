//! Today's panes and the document actions behind them. The Studio 2 frame
//! (`studio-shell.rs`) places these panes inside its stations.
use super::*;
use crate::workspace_history::{NodeId, StackDraft};

/// The pane flags today's code reads and writes. The shell's route is the
/// source of truth and writes these through its adapter (`studio-route.rs`).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Sidebar {
    Projects,
    Capture,
    Adjust,
    Edit,
    Export,
    Agent,
    Review,
    Activity,
}

impl StrehlApp {
    /// The displayed action and every launch entry point use the same gate.
    /// Nothing is persisted or queued until it is satisfied.
    pub(super) fn stack_start_blocker(&self) -> Option<&'static str> {
        if self.job.is_some() {
            Some("A stack is already running")
        } else if self.picker_active() {
            Some("Finish choosing your photos")
        } else if self.scan.is_some() {
            Some("Reading source photos…")
        } else if self.replay.is_some() {
            Some("Opening the saved result…")
        } else if self.editor.loading.is_some() {
            Some("Opening the photograph's saved edits…")
        } else if self.editor.path == self.result
            && self.editor.path.is_some()
            && self.editor.loaded.is_none()
        {
            Some("Resolve the photograph's edit-loading error before restacking")
        } else if self.draft_job.is_some() {
            Some("Finishing the preview…")
        } else if self
            .stack
            .as_ref()
            .is_none_or(|stack| stack.frames.is_empty())
        {
            Some("Choose source photos to begin")
        } else if self.output.as_os_str().is_empty() {
            Some("Choose an output folder in Adjust > Destination")
        } else if self.engine.is_none() {
            Some("Stacking engine unavailable")
        } else if self.controls.settings.frame_limit == Some(0) {
            Some("Choose at least one source photo")
        } else if let Some(reason) = self.session_start_blocker() {
            Some(reason)
        } else {
            jobs::temporal_settings_blocker(
                &self.controls.settings,
                self.controls.gate,
                (self.editor.loaded.is_some() && self.editor.path == self.result)
                    .then_some(&self.editor.recipe),
            )
        }
    }

    fn stack_launch_panel(&mut self, ui: &mut egui::Ui, pane: Sidebar) {
        let busy = self.job.is_some();
        let cancelling = self
            .job
            .as_ref()
            .is_some_and(jobs::RenderJob::is_cancelling);
        let opening = self.scan.is_some() || self.replay.is_some() || self.session_import.is_some();
        let name = self
            .active_stack
            .and_then(|id| self.catalog.node(id))
            .map(|node| node.name.clone())
            .or_else(|| {
                self.stack.as_ref().map(|stack| {
                    stack
                        .directory
                        .file_name()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .into_owned()
                })
            })
            .unwrap_or_else(|| {
                if opening {
                    "Opening capture…"
                } else {
                    "No capture selected"
                }
                .into()
            });
        let total = self.stack.as_ref().map_or(0, |stack| stack.frames.len());
        let included = self
            .controls
            .settings
            .frame_limit
            .unwrap_or(total)
            .min(total);
        let blocker = self.stack_start_blocker();
        let state = if cancelling {
            "STOPPING"
        } else if busy {
            if self.pending_run.is_some() {
                "STARTING"
            } else {
                "STACKING"
            }
        } else if opening {
            "OPENING"
        } else {
            "CURRENT STACK"
        };
        let detail = if cancelling {
            "Stopping stack…".into()
        } else if busy {
            if self.pending_run.is_some() {
                "Starting stack…".into()
            } else {
                "Progress is live in the workspace".into()
            }
        } else if let Some(reason) = blocker {
            reason.into()
        } else if included != total {
            format!("First {included} of {total} photos · new result")
        } else {
            format!("{total} photos · ready to stack")
        };
        egui::Frame::NONE
            .inner_margin(egui::Margin::symmetric(8, 7))
            .show(ui, |ui| {
                ui.spacing_mut().item_spacing = egui::vec2(4.0, 3.0);
                ui.label(RichText::new(state).monospace().size(8.0).color(if busy {
                    ACCENT
                } else {
                    MUTED
                }));
                ui.add(egui::Label::new(RichText::new(&name).size(12.0).color(INK)).truncate())
                    .on_hover_text(self.stack.as_ref().map_or_else(
                        || name.clone(),
                        |stack| crate::display_path::display_path(&stack.directory),
                    ));
                ui.add(egui::Label::new(RichText::new(&detail).size(10.0).color(MUTED)).truncate())
                    .on_hover_text(&detail);
                ui.add_space(3.0);
                let (row, _) = ui.allocate_exact_size(
                    egui::vec2(ui.available_width(), 32.0),
                    egui::Sense::hover(),
                );
                let adjust_width = if busy || pane == Sidebar::Projects && total > 0 {
                    58.0
                } else {
                    0.0
                };
                let command = egui::Rect::from_min_max(
                    row.min,
                    egui::pos2(row.right() - adjust_width, row.bottom()),
                );
                let mut command_ui = ui.new_child(
                    egui::UiBuilder::new()
                        .id_salt("current-stack-command")
                        .max_rect(command),
                );
                if busy {
                    // A second click at the launch position cannot cancel the
                    // run just started. Stop has its own adjacent target.
                    command_ui.add_sized(
                        command.size(),
                        egui::Button::new(if cancelling {
                            "Stopping…"
                        } else if self.pending_run.is_some() {
                            "Starting…"
                        } else {
                            "Stacking…"
                        })
                        .sense(egui::Sense::hover()),
                    );
                } else if total == 0 && !opening && !self.picker_active() {
                    if command_ui
                        .add_sized(command.size(), egui::Button::new("Choose photos…"))
                        .clicked()
                    {
                        self.capture_parent = self.catalog.selected_container();
                        self.pick(Dialog::Source);
                    }
                } else if theme::stack_action(
                    &mut command_ui,
                    command.size(),
                    blocker.is_none(),
                    None,
                )
                .on_hover_text(blocker.map_or_else(
                    || format!("Stack {included} photos into a new result in {name}\nCtrl+Enter"),
                    str::to_owned,
                ))
                .clicked()
                {
                    self.start_render();
                    ui.ctx().request_repaint();
                }
                if adjust_width > 0.0 {
                    let adjust = egui::Rect::from_min_max(
                        egui::pos2(command.right() + 4.0, row.top()),
                        row.max,
                    );
                    if busy {
                        let hit = ui.put(
                            adjust,
                            egui::Button::new("Stop").frame(false).sense(if cancelling {
                                egui::Sense::hover()
                            } else {
                                egui::Sense::click()
                            }),
                        );
                        if hit.on_hover_text("Stop this run").clicked() {
                            if let Some(job) = &self.job {
                                job.cancel();
                            }
                            self.status = "Stopping stack…".into();
                        }
                    } else if ui
                        .put(adjust, egui::Button::new("Adjust").frame(false))
                        .on_hover_text("Adjust this stack's recipe")
                        .clicked()
                    {
                        self.shell
                            .navigator
                            .set_stack_tab(super::studio_route::StackTab::Adjust);
                        self.go_station(super::studio_route::Station::Stack);
                    }
                }
            });
        let (line, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 1.0), egui::Sense::hover());
        theme::rule(ui.painter(), line.left_center(), line.right_center(), LINE);
    }

    pub(super) fn welcome_workspace(&mut self, ui: &mut egui::Ui) {
        let add;
        {
            {
                let bounds = ui.max_rect();
                let width = (bounds.width() - 64.0).clamp(220.0, 520.0);
                let origin = bounds.center() - egui::vec2(width * 0.5, 95.0);
                let p = ui.painter();
                p.text(
                    origin,
                    egui::Align2::LEFT_TOP,
                    "A photograph begins with a stack.",
                    egui::FontId::proportional(22.0),
                    INK,
                );
                p.text(
                    origin + egui::vec2(0.0, 38.0),
                    egui::Align2::LEFT_TOP,
                    "Choose a stack in the Library, or bring in a new capture bracket.",
                    egui::FontId::proportional(11.0),
                    MUTED,
                );
                let line_y = origin.y + 98.0;
                let columns = ["PROJECT", "STACK", "RESULT"];
                let captions = ["Related captures", "A source bracket", "A saved photograph"];
                for index in 0..3 {
                    let left = origin.x + index as f32 * width / 3.0;
                    p.text(
                        egui::pos2(left, line_y - 18.0),
                        egui::Align2::LEFT_BOTTOM,
                        columns[index],
                        egui::FontId::monospace(9.0),
                        ACCENT,
                    );
                    theme::rule(
                        p,
                        egui::pos2(left, line_y),
                        egui::pos2(left + width / 3.0 - 20.0, line_y),
                        LINE,
                    );
                    p.text(
                        egui::pos2(left, line_y + 10.0),
                        egui::Align2::LEFT_TOP,
                        captions[index],
                        egui::FontId::proportional(10.0),
                        MUTED,
                    );
                }
                let button = egui::Rect::from_min_size(
                    origin + egui::vec2(0.0, 151.0),
                    egui::vec2(138.0, 30.0),
                );
                let loading = self.scan.is_some();
                add = ui
                    .put(
                        button,
                        egui::Button::new(if loading {
                            "Reading bracket…"
                        } else {
                            "New stack"
                        })
                        .sense(if loading || self.picker_active() {
                            egui::Sense::hover()
                        } else {
                            egui::Sense::click()
                        }),
                    )
                    .on_hover_text(
                        "Choose a folder of source photographs in the visual bracket browser",
                    )
                    .clicked();
            }
        }
        if add {
            self.capture_parent = self.catalog.selected_container();
            self.pick(Dialog::Source);
        }
    }
    pub(super) fn persist_catalog(&mut self) {
        self.catalog_edit_pending = None;
        self.shell.catalog_changed();
        if let Err(error) = self.catalog.save() {
            self.error = Some(format!("Saving projects: {error}"));
        }
    }
    fn draft(&self) -> Option<StackDraft> {
        self.stack.as_ref().map(|stack| {
            StackDraft::from_scan(
                stack,
                self.controls.settings.clone(),
                self.controls.exposure,
                self.controls.gate,
                self.controls.workers,
            )
        })
    }
    pub(super) fn save_active_draft(&mut self) {
        if let (Some(id), Some(draft)) = (self.active_stack, self.draft())
            && let Err(error) = self.catalog.update_stack_draft(id, draft)
        {
            self.error = Some(error.to_string());
        }
    }
    pub(super) fn ensure_project_stack(&mut self) {
        let Some(draft) = self.draft() else { return };
        if let Some(id) = self.active_stack {
            if let Err(error) = self.catalog.update_stack_draft(id, draft) {
                self.error = Some(error.to_string());
            }
        } else {
            let parent = match self
                .capture_parent
                .take()
                .or_else(|| self.catalog.selected_container())
            {
                Some(id) => id,
                None => match self.catalog.create_project("Untitled project") {
                    Ok(id) => id,
                    Err(error) => {
                        self.error = Some(error.to_string());
                        return;
                    }
                },
            };
            // A camera folder (`107MSDCF`) names nothing; its parent names the subject.
            let name = self
                .session_ui
                .pending_name
                .take()
                .unwrap_or_else(|| crate::workspace_history::default_stack_name(&draft.source));
            match self.catalog.create_stack(parent, &name, draft) {
                Ok(id) => self.active_stack = Some(id),
                Err(error) => self.error = Some(error.to_string()),
            }
        }
        if let Some(id) = self.active_stack {
            self.catalog.selected = Some(id);
            self.project_explorer.select_stack(id);
        }
        self.persist_catalog();
    }
    fn apply_draft(&mut self, draft: &StackDraft) {
        self.controls.settings = draft.settings.clone();
        self.controls.exposure = draft.exposure;
        self.controls.gate = draft.gate;
        self.controls.workers = draft
            .workers
            .clamp(1, jobs::MachineResources::detect().maximum_workers());
    }
    pub(super) fn reopen_run(&mut self, run: crate::workspace_history::Run) {
        if self.job.is_some() || self.picker_active() {
            return;
        }
        let id = self.catalog.stack_for_run(&run.directory);
        if run.imported.is_some() {
            self.prepare_session_controls();
            self.reset_capture();
        } else if let Some(session) = run.settings.session.clone() {
            self.reload_session(session, false);
        } else {
            self.import(run.source.clone());
        }
        self.active_stack = id;
        if let Some(id) = id {
            self.catalog.selected = Some(id);
            self.project_explorer.select_stack(id);
            self.project_explorer.select_revision(&run.directory);
        }
        self.expected_run = Some(run.clone());
        self.controls.settings = run.settings.clone();
        self.refresh_session_outputs(&run.directory);
        self.controls.exposure = run.exposure;
        self.controls.gate = run.gate;
        self.controls.workers = run
            .workers
            .clamp(1, jobs::MachineResources::detect().maximum_workers());
        self.replay = Some(crate::workspace_history::reopen(run));
        self.status = "Opening saved render and observations…".into();
    }
    pub(super) fn open_project_stack(&mut self, id: NodeId) {
        if self.job.is_some() || self.picker_active() {
            return;
        }
        if let Some(run) = self
            .catalog
            .latest_run(id)
            .filter(|r| r.imported.is_some())
            .cloned()
        {
            self.reopen_run(run);
            return;
        }
        let Some(draft) = self.catalog.node(id).and_then(|n| n.stack.clone()) else {
            return;
        };
        if let Some(session) = draft.settings.session.clone() {
            self.reload_session(session, false);
            self.active_stack = Some(id);
            self.catalog.selected = Some(id);
            self.project_explorer.select_stack(id);
            self.apply_draft(&draft);
            return;
        }
        if let Some(run) = self.catalog.latest_run(id).cloned() {
            self.reopen_run(run);
        } else {
            self.import(draft.source.clone());
        }
        self.active_stack = Some(id);
        self.catalog.selected = Some(id);
        self.project_explorer.select_stack(id);
        self.apply_draft(&draft);
        self.process_view = true;
    }
    /// Today's Projects pane: the current stack's command, session controls,
    /// saved photographs and the project tree. Returns whether the catalog
    /// changed and any explorer action, for `after_pane`.
    pub(super) fn projects_pane(
        &mut self,
        ui: &mut egui::Ui,
    ) -> (bool, Option<crate::project_explorer::ExplorerAction>) {
        let mut changed = false;
        let mut action = None;
        if self.stack.is_some()
            || self.scan.is_some()
            || self.replay.is_some()
            || self.job.is_some()
        {
            self.stack_launch_panel(ui, Sidebar::Projects);
        }
        if self.controls.settings.session.is_some() {
            // Always show the bar: a long pass list otherwise ends at the
            // clip edge with no sign that it scrolls.
            egui::Frame::NONE
                .inner_margin(egui::Margin::symmetric(8, 0))
                .show(ui, |ui| {
                    egui::ScrollArea::vertical()
                        .id_salt("project-session-editor")
                        .max_height((ui.available_height() * 0.55).clamp(180.0, 420.0))
                        .auto_shrink([false, true])
                        .scroll_bar_visibility(
                            egui::scroll_area::ScrollBarVisibility::AlwaysVisible,
                        )
                        .show(ui, |ui| self.session_panel(ui));
                });
            ui.add_space(6.0);
        } else {
            self.session_panel(ui);
        }
        self.session_result_picker(ui);
        self.photo_history_panel(ui);
        self.project_explorer.set_current_photo(
            self.editor.path.as_deref(),
            self.editor.loaded.as_ref().map(|photo| &photo.image),
            self.editor.loaded.as_ref().map(|photo| &photo.preview),
        );
        let busy = self.job.is_some() || self.picker_active() || self.scan.is_some();
        // Keep the primary source workflow beside the Projects heading.
        // Reserve a footer for completed-result import instead of pushing New
        // stack down with an unrelated action row.
        let import_height = if self.session_import.is_some() {
            76.0
        } else {
            30.0
        };
        let response = ui
            .allocate_ui(
                egui::vec2(
                    ui.available_width(),
                    (ui.available_height() - import_height).max(70.0),
                ),
                |ui| self.project_explorer.show(ui, &mut self.catalog, busy),
            )
            .inner;
        changed |= response.changed;
        action = action.or(response.action);
        ui.horizontal(|ui| {
            if cfg!(feature = "multi-stack") && ui.add_enabled(!busy && self.replay.is_none(), egui::Button::new("Stack everything…")).on_hover_text("Pick a folder of related captures. Every folder of RAW files inside becomes a pass, and Best result plans what each contributes to one photograph.").clicked() { self.pick(Dialog::StackEverything); }
            if cfg!(feature = "multi-stack") && ui.add_enabled(!busy && self.replay.is_none(), egui::Button::new("Open completed CLI session…")).on_hover_text("Import saved photographs and diagnostics without opening original capture folders.").clicked() { self.pick(Dialog::CompletedSession); }
        });
        if let Some((_, _, task)) = &self.session_import {
            ui.label("Verifying imported artifacts…");
            if ui.button("Cancel import").clicked() {
                task.cancel();
            }
        }
        (changed, action)
    }

    /// After a pane painted: debounce the catalog save, ask `tick` to save
    /// the next render's recipe, and carry out the explorer's action.
    pub(super) fn after_pane(
        &mut self,
        changed: bool,
        recipe: bool,
        action: Option<crate::project_explorer::ExplorerAction>,
    ) {
        if changed {
            self.shell.request_draft_save(recipe);
            // Editing a title or dragging a recipe control must not serialize
            // an entire project library on every pointer or keyboard event.
            self.catalog_edit_pending = Some(Instant::now());
        }
        if let Some(action) = action {
            use crate::project_explorer::ExplorerAction;
            match action {
                ExplorerAction::NewCapture { parent } => {
                    self.capture_parent = parent;
                    self.pick(Dialog::Source);
                }
                // Opening from the tree keeps the Library: its canvas shows the
                // stack, and the tree stays beside it. The Stack station is one
                // click away in the top bar.
                ExplorerAction::OpenStack { id } => self.open_project_stack(id),
                ExplorerAction::OpenRun { run } => self.reopen_run(*run),
                action @ (ExplorerAction::RestoreVersion { .. }
                | ExplorerAction::OpenExport { .. }
                | ExplorerAction::RevealPath { .. }) => self.handle_photo_history_action(action),
            }
        }
    }
    pub(super) fn review_panel(&mut self, ui: &mut egui::Ui) {
        self.session_result_picker(ui);
        if !self.activity {
            theme::caption(
                ui,
                "Stack a capture to inspect its retained alignment, coverage and blending evidence.",
            );
            return;
        }
        if let Some(focus) = crate::controls::show_review(ui, &self.progress) {
            let selected = self
                .progress
                .active_view()
                .map_or(self.selected, |v| v.local_frame(self.selected).unwrap_or(0));
            self.process_space.review_focus(focus, selected);
        }
        if let Some(output) = &self.result {
            ui.separator();
            if ui.button("Copy photograph path").clicked() {
                ui.ctx()
                    .copy_text(crate::display_path::display_path(output));
            }
            let confidence = output.with_file_name("confidence.tiff");
            if confidence.is_file()
                && ui
                    .button("Copy confidence map path")
                    .on_hover_text("Aligned-observation centrality rank saved alongside this render; not a defect map")
                    .clicked()
            {
                ui.ctx().copy_text(crate::display_path::display_path(&confidence));
            }
        }
    }
}
