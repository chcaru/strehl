//! Compact activity rail and a single modular sidebar around the process.
use super::*;
use crate::workspace_history::{NodeId, StackDraft};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Sidebar {
    Projects,
    Adjust,
    Edit,
    Export,
    Agent,
    Review,
    Activity,
}
impl Sidebar {
    fn label(self) -> &'static str {
        match self {
            Self::Projects => "Projects",
            Self::Adjust => "Adjust",
            Self::Edit => "Edit",
            Self::Export => "Export",
            Self::Agent => "Agent",
            Self::Review => "Review",
            Self::Activity => "Activity",
        }
    }
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
        let opening = self.scan.is_some() || self.replay.is_some();
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
                        |stack| stack.directory.display().to_string(),
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
                        self.sidebar = Some(Sidebar::Adjust);
                    }
                }
            });
        let (line, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 1.0), egui::Sense::hover());
        theme::rule(ui.painter(), line.left_center(), line.right_center(), LINE);
    }

    pub(super) fn welcome_workspace(&mut self, ctx: &egui::Context) {
        let mut add = false;
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(BG))
            .show(ctx, |ui| {
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
                    "Choose a stack in Projects, or bring in a new capture bracket.",
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
            });
        if add {
            self.capture_parent = self.catalog.selected_container();
            self.pick(Dialog::Source);
        }
    }
    pub(super) fn persist_catalog(&mut self) {
        self.catalog_edit_pending = None;
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
            let name = draft
                .source
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned();
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
        self.import(run.source.clone());
        self.active_stack = id;
        if let Some(id) = id {
            self.catalog.selected = Some(id);
            self.project_explorer.select_stack(id);
            self.project_explorer.select_revision(&run.directory);
        }
        self.expected_run = Some(run.clone());
        self.controls.settings = run.settings.clone();
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
        let Some(draft) = self.catalog.node(id).and_then(|n| n.stack.clone()) else {
            return;
        };
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
    pub(super) fn navigation_rail(&mut self, ctx: &egui::Context) {
        egui::SidePanel::left("activity-rail")
            .exact_width(crate::window_chrome::RAIL_WIDTH)
            .resizable(false)
            .show_separator_line(false)
            .frame(egui::Frame::new().fill(PANEL).inner_margin(0))
            .show(ctx, |ui| {
                ui.add_space(6.0);
                let rail = ui.max_rect();
                theme::rule(ui.painter(), rail.right_top(), rail.right_bottom(), LINE);
                if self.picker_active() {
                    ui.disable();
                }
                for (index, pane) in [
                    (0, Sidebar::Projects),
                    (1, Sidebar::Adjust),
                    (7, Sidebar::Edit),
                    (9, Sidebar::Export),
                    (8, Sidebar::Agent),
                    (2, Sidebar::Review),
                    (3, Sidebar::Activity),
                ]
                .into_iter()
                {
                    if rail_command(ui, pane.label(), index, self.sidebar == Some(pane), true)
                        .clicked()
                    {
                        self.sidebar = if self.sidebar == Some(pane) {
                            None
                        } else {
                            Some(pane)
                        };
                        self.process_view = true;
                    }
                }
                let spare = ui.available_rect_before_wrap();
                let drag = egui::Rect::from_min_max(
                    spare.min + egui::vec2(7.0, 4.0),
                    spare.max - egui::vec2(7.0, 106.0),
                );
                if drag.is_positive() {
                    crate::window_chrome::drag_space(ui, drag, self.picker_active());
                }
                ui.with_layout(egui::Layout::bottom_up(egui::Align::Center), |ui| {
                    ui.add_space(5.0);
                    if rail_command(ui, "Reset layout", 5, false, true).clicked() {
                        self.process_space.set_layout(Default::default());
                        self.catalog.layout = Default::default();
                        self.persist_catalog();
                    }
                    let enabled = self.job.is_some() || self.stack_start_blocker().is_none();
                    if rail_command(ui, "Stack", 4, self.job.is_some(), enabled).clicked() {
                        if self.job.is_some() {
                            self.sidebar = Some(Sidebar::Projects);
                        } else {
                            self.start_render();
                        }
                    }
                });
            });
    }
    pub(super) fn sidebar(&mut self, ctx: &egui::Context) {
        let Some(pane) = self.sidebar else { return };
        let mut action = None;
        let mut changed = false;
        egui::SidePanel::left("workspace-sidebar")
            .default_width(270.0)
            .width_range(230.0..=440.0)
            .resizable(true)
            .show_separator_line(false)
            .frame(egui::Frame::new().fill(PANEL).inner_margin(0))
            .show(ctx, |ui| {
                let pane_rect = ui.max_rect();
                theme::rule(
                    ui.painter(),
                    pane_rect.right_top(),
                    pane_rect.right_bottom(),
                    LINE,
                );
                let (heading, _) = ui.allocate_exact_size(
                    egui::vec2(ui.available_width(), 29.0),
                    egui::Sense::hover(),
                );
                ui.painter().text(
                    heading.left_center() + egui::vec2(12.0, 0.0),
                    egui::Align2::LEFT_CENTER,
                    pane.label().to_uppercase(),
                    egui::FontId::proportional(10.0),
                    INK,
                );
                let close = egui::Rect::from_center_size(
                    heading.right_center() - egui::vec2(14.0, 0.0),
                    egui::vec2(24.0, 24.0),
                );
                let close_hit =
                    ui.interact(close, ui.id().with("hide-sidebar"), egui::Sense::click());
                close_hit.widget_info(|| {
                    egui::WidgetInfo::labeled(egui::WidgetType::Button, true, "Hide sidebar")
                });
                let c = close.center();
                let color = if close_hit.hovered() { INK } else { MUTED };
                theme::rule(
                    ui.painter(),
                    c - egui::vec2(3.0, 3.0),
                    c + egui::vec2(3.0, 3.0),
                    color,
                );
                theme::rule(
                    ui.painter(),
                    c + egui::vec2(-3.0, 3.0),
                    c + egui::vec2(3.0, -3.0),
                    color,
                );
                if close_hit.on_hover_text("Hide sidebar").clicked() {
                    self.sidebar = None;
                }
                theme::rule(
                    ui.painter(),
                    heading.left_bottom(),
                    heading.right_bottom(),
                    LINE,
                );
                if matches!(pane, Sidebar::Projects | Sidebar::Adjust)
                    && (pane == Sidebar::Adjust
                        || self.stack.is_some()
                        || self.scan.is_some()
                        || self.replay.is_some()
                        || self.job.is_some())
                {
                    self.stack_launch_panel(ui, pane);
                }
                if pane == Sidebar::Projects {
                    self.photo_history_panel(ui);
                    self.project_explorer.set_current_photo(
                        self.editor.path.as_deref(),
                        self.editor.loaded.as_ref().map(|photo| &photo.image),
                        self.editor.loaded.as_ref().map(|photo| &photo.preview),
                    );
                    let busy = self.job.is_some() || self.picker_active() || self.scan.is_some();
                    let response = self.project_explorer.show(ui, &mut self.catalog, busy);
                    changed = response.changed;
                    action = response.action;
                } else if pane == Sidebar::Edit {
                    self.edit_panel(ui);
                } else if pane == Sidebar::Export {
                    self.export_panel(ui);
                } else {
                    egui::Frame::NONE.inner_margin(10).show(ui, |ui| {
                        egui::ScrollArea::vertical()
                        .id_salt(("workspace-pane", pane.label()))
                        .auto_shrink([false, false])
                        .scroll_bar_visibility(
                            egui::scroll_area::ScrollBarVisibility::AlwaysVisible,
                        )
                        .show(ui, |ui| match pane {
                            Sidebar::Adjust => {
                                let recipe_before = history::Recipe::capture(&self.controls);
                                let before = (
                                    self.controls.settings.clone(),
                                    self.controls.exposure,
                                    self.controls.gate,
                                    self.controls.workers,
                                );
                                self.controls.show(ui, self.job.is_none());
                                changed = before
                                    != (
                                        self.controls.settings.clone(),
                                        self.controls.exposure,
                                        self.controls.gate,
                                        self.controls.workers,
                                    );
                                if changed {
                                    self.edits.changed_recipe(recipe_before, ui.input(|i| i.time));
                                }
                                ui.add_space(8.0);
                                egui::CollapsingHeader::new("Destination")
                                    .show(ui, |ui| self.destination_controls(ui));
                            }
                            Sidebar::Review => self.review_panel(ui),
                            Sidebar::Edit | Sidebar::Export => unreachable!(),
                            Sidebar::Agent => self.agent_panel(ui),
                            Sidebar::Activity => {
                                if let Some(error) = &self.error {
                                    ui.colored_label(AMBER, error);
                                    ui.separator();
                                }
                                if self.logs.is_empty() {
                                    theme::caption(
                                        ui,
                                        "Engine observations will be retained with each render.",
                                    );
                                }
                                for line in &self.logs {
                                    ui.add(
                                        egui::Label::new(
                                            RichText::new(line).monospace().size(10.0).color(MUTED),
                                        )
                                        .wrap(),
                                    );
                                }
                            }
                            Sidebar::Projects => unreachable!(),
                        });
                    });
                }
            });
        if changed {
            if pane == Sidebar::Adjust {
                self.save_active_draft();
            }
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
                ExplorerAction::OpenStack { id } => self.open_project_stack(id),
                ExplorerAction::OpenRun { run } => self.reopen_run(*run),
                action @ (ExplorerAction::RestoreVersion { .. }
                | ExplorerAction::OpenExport { .. }
                | ExplorerAction::RevealPath { .. }) => self.handle_photo_history_action(action),
            }
        }
    }
    fn review_panel(&mut self, ui: &mut egui::Ui) {
        if !self.activity {
            theme::caption(
                ui,
                "Stack a capture to inspect its retained alignment, coverage and blending evidence.",
            );
            return;
        }
        if let Some(focus) = crate::controls::show_review(ui, &self.progress) {
            self.process_space.review_focus(focus, self.selected);
        }
        if let Some(output) = &self.result {
            ui.separator();
            if ui.button("Copy photograph path").clicked() {
                ui.ctx().copy_text(output.display().to_string());
            }
            let confidence = output.with_file_name("confidence.tiff");
            if confidence.is_file()
                && ui
                    .button("Copy confidence map path")
                    .on_hover_text("Aligned-observation centrality rank saved alongside this render; not a defect map")
                    .clicked()
            {
                ui.ctx().copy_text(confidence.display().to_string());
            }
        }
    }
    pub(super) fn status_bar(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::bottom("status-v2")
            .exact_height(23.0)
            .show_separator_line(false)
            .frame(
                egui::Frame::new()
                    .fill(PANEL)
                    .inner_margin(egui::Margin::symmetric(10, 0)),
            )
            .show(ctx, |ui| {
                let frame = ui.max_rect().expand2(egui::vec2(10.0, 0.0));
                theme::rule(ui.painter(), frame.left_top(), frame.right_top(), LINE);
                ui.spacing_mut().interact_size.y = 19.0;
                ui.horizontal_centered(|ui| {
                    for redo in [false, true] {
                        let enabled = self.can_undo_edit(redo);
                        let label = self.undo_label(redo);
                        if history_command(ui, redo, enabled, &label).clicked() {
                            self.undo_edit(redo);
                        }
                    }
                    dot(
                        ui,
                        if self.error.is_some() {
                            AMBER
                        } else if self.job.is_some() {
                            ACCENT
                        } else {
                            MUTED
                        },
                    );
                    let message = self.error.as_deref().unwrap_or(&self.status);
                    let identity = self
                        .active_stack
                        .and_then(|id| self.catalog.node(id))
                        .map(|node| node.name.as_str())
                        .or_else(|| {
                            self.stack
                                .as_ref()
                                .and_then(|stack| stack.directory.file_name())
                                .and_then(|name| name.to_str())
                        });
                    let status = identity
                        .map_or_else(|| message.to_owned(), |name| format!("{name} · {message}"));
                    let label = ui.add_sized(
                        [
                            (ui.available_width()
                                - if self.editor.loaded.is_some() {
                                    365.0
                                } else {
                                    320.0
                                })
                            .max(20.0),
                            19.0,
                        ],
                        egui::Label::new(
                            RichText::new(&status)
                                .size(10.0)
                                .color(if self.error.is_some() { AMBER } else { MUTED }),
                        )
                        .truncate()
                        .sense(egui::Sense::click()),
                    );
                    if label.clone().on_hover_text(&status).clicked() {
                        self.sidebar = Some(Sidebar::Activity);
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.add(egui::Button::new("Activity").frame(false)).clicked() {
                            self.sidebar = Some(Sidebar::Activity);
                        }
                        if self.editor.loaded.is_some()
                            && let Some(presenter) = &self.editor.viewport.presenter
                        {
                            let display = presenter.status();
                            let hdr = display.active
                                && self.editor.loaded.as_ref().is_some_and(|photo| {
                                    photo.image.origin == strehl_edit::ImageOrigin::SceneLinear
                                });
                            ui.label(
                                RichText::new(if hdr { "HDR" } else { "SDR" })
                                    .size(10.0)
                                    .color(if hdr { ACCENT } else { MUTED }),
                            )
                            .on_hover_text(format!(
                                "{}\nVisible photo detail refines to source pixels as you zoom.",
                                display.reason
                            ));
                        }
                        if self.recorded {
                            theme::caption(ui, "Recorded");
                        }
                        if let Some(started) = self.started.filter(|_| self.job.is_some()) {
                            theme::caption(ui, &elapsed(started.elapsed()));
                        }
                        theme::caption(ui, &format!("{} workers", self.controls.workers));
                        if let Some(stack) = &self.stack {
                            theme::caption(
                                ui,
                                &format!(
                                    "{} RAW · {}",
                                    stack.frames.len(),
                                    bytes(stack.total_bytes)
                                ),
                            );
                        }
                    });
                });
            });
    }
}

fn history_command(ui: &mut egui::Ui, redo: bool, enabled: bool, label: &str) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(22.0, 19.0),
        if enabled {
            egui::Sense::click()
        } else {
            egui::Sense::hover()
        },
    );
    response.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, enabled, label));
    let p = ui.painter_at(rect);
    if enabled && response.hovered() {
        p.rect_filled(rect, 0.0, theme::RAISED);
    }
    let color = if enabled {
        INK
    } else {
        MUTED.gamma_multiply(0.4)
    };
    let c = rect.center();
    let flip = if redo { -1.0 } else { 1.0 };
    let point = |x: f32, y: f32| c + egui::vec2(x * flip, y);
    let stroke = Stroke::new(1.0 / ui.ctx().pixels_per_point(), color);
    p.add(egui::Shape::line(
        vec![
            point(-5.0, -3.0),
            point(2.0, -3.0),
            point(5.0, 0.0),
            point(5.0, 4.0),
        ],
        stroke,
    ));
    p.add(egui::Shape::line(
        vec![point(-1.0, -6.0), point(-5.0, -3.0), point(-1.0, 0.0)],
        stroke,
    ));
    response.on_hover_text(format!(
        "{label} · {}",
        if redo {
            "Ctrl+Shift+Z / Ctrl+Y"
        } else {
            "Ctrl+Z"
        }
    ))
}

fn rail_command(
    ui: &mut egui::Ui,
    label: &str,
    kind: usize,
    selected: bool,
    enabled: bool,
) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(48.0, 48.0),
        if enabled {
            egui::Sense::click()
        } else {
            egui::Sense::hover()
        },
    );
    response.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, enabled, label));
    let p = ui.painter_at(rect);
    let c = rect.center() - egui::vec2(0.0, 5.0);
    let color = if enabled && (selected || response.hovered() || kind == 4) {
        ACCENT
    } else {
        MUTED
    };
    if selected {
        p.rect_filled(
            egui::Rect::from_min_size(
                rect.min,
                egui::vec2(1.0 / ui.ctx().pixels_per_point(), rect.height()),
            ),
            0.0,
            ACCENT,
        );
    }
    if response.hovered() {
        p.rect_filled(rect.shrink(3.0), 0.0, theme::RAISED);
    }
    let icon = match kind {
        0 => crate::workspace_icons::Icon::Projects,
        1 => crate::workspace_icons::Icon::Adjust,
        2 => crate::workspace_icons::Icon::Review,
        3 => crate::workspace_icons::Icon::Activity,
        4 => crate::workspace_icons::Icon::Stack,
        7 => crate::workspace_icons::Icon::Edit,
        8 => crate::workspace_icons::Icon::Agent,
        9 => crate::workspace_icons::Icon::Export,
        _ => crate::workspace_icons::Icon::Layout,
    };
    crate::workspace_icons::paint(&p, c, 20.0, icon, color);
    p.text(
        rect.center_bottom() - egui::vec2(0.0, 3.0),
        egui::Align2::CENTER_BOTTOM,
        if kind == 5 { "Layout" } else { label },
        egui::FontId::proportional(8.0),
        color,
    );
    response.on_hover_text(match kind {
        0 => "Projects · folders, stacks and saved renders",
        1 => "Adjust · settings for the next render",
        2 => "Review · retained processing evidence",
        3 => "Activity · engine observations",
        4 if selected => "Opens current stack",
        4 => "Stack · build a new render with these settings",
        6 => "Space · explore the photograph, capture order, detail sizes and construction history as one object · experimental",
        _ => "Reset workspace proportions",
    })
}
