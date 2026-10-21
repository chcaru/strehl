use super::*;
use crate::edit_workspace::DrawingTool;
use strehl_edit::{Adjustments, DevelopmentRecipe};

#[cfg(test)]
#[path = "edit-pane-tests.rs"]
mod tests;

#[path = "edit-controls.rs"]
pub(super) mod controls;

#[derive(Default)]
pub(super) struct EditPaneState {
    document: Option<PathBuf>,
    rename: Option<(String, String)>,
}

impl EditPaneState {
    fn reconcile(&mut self, editor: &crate::edit_workspace::EditorState) {
        if self.document != editor.path {
            self.document = editor.path.clone();
            self.rename = None;
        } else if self
            .rename
            .as_ref()
            .is_some_and(|(id, _)| !editor.recipe.regions.iter().any(|region| &region.id == id))
        {
            self.rename = None;
        }
    }
}

fn bounded_text(text: &str, max_bytes: usize) -> String {
    let mut end = text.len().min(max_bytes);
    while !text.is_char_boundary(end) {
        end -= 1;
    }
    text[..end].to_owned()
}

/// Rename consumes its own completion keys so Escape cannot also deselect the canvas.
fn rename_region(
    ui: &mut egui::Ui,
    rect: egui::Rect,
    id: &str,
    text: &mut String,
    name: &mut String,
) -> bool {
    let field_id = egui::Id::new(("rename-region", id));
    let response = ui.put(
        rect,
        egui::TextEdit::singleline(text)
            .id(field_id)
            .desired_width(f32::INFINITY),
    );
    if ui
        .ctx()
        .data_mut(|d| d.remove_temp::<bool>(field_id.with("request-focus")))
        .unwrap_or(false)
    {
        response.request_focus();
    }
    let cancel = ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape));
    let accept = ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Enter));
    if cancel || accept || response.lost_focus() {
        if !cancel && !text.trim().is_empty() {
            *name = bounded_text(text.trim(), 256);
        }
        response.surrender_focus();
        true
    } else {
        false
    }
}

fn duplicate_region(
    editor: &mut crate::edit_workspace::EditorState,
    id: &str,
) -> anyhow::Result<()> {
    anyhow::ensure!(
        editor.recipe.regions.len() < 128,
        "A photograph can contain up to 128 regions."
    );
    let mut region = editor
        .recipe
        .regions
        .iter()
        .find(|r| r.id == id)
        .cloned()
        .ok_or_else(|| anyhow::anyhow!("This region no longer exists."))?;
    let adaptive = editor.recipe.adaptive_scope(Some(id)).cloned();
    // The source ID can already use the entire schema budget. Allocate a new short ID.
    let mut suffix = 1;
    let id = loop {
        let candidate = format!("region-copy-{suffix}");
        if !editor.recipe.regions.iter().any(|r| r.id == candidate) {
            break candidate;
        }
        suffix += 1;
    };
    region.id = id.clone();
    region.name = format!("{} copy", bounded_text(&region.name, 251));
    // Duplicating an edit must not silently schedule a second source repair.
    region.source_range = None;
    let mut recipe = editor.recipe.clone();
    recipe.regions.push(region);
    if let Some(mut field) = adaptive {
        field.target_region = Some(id.clone());
        recipe.spatial.push(field);
    }
    editor.replace(recipe)?;
    editor.selected = Some(id);
    editor.set_tool(DrawingTool::Select);
    editor.before = false;
    Ok(())
}

fn region_shelf(ui: &mut egui::Ui, open: bool, contents: impl FnOnce(&mut egui::Ui)) {
    // A collapsed panel must not overwrite the persisted expanded height.
    let mut shelf = egui::TopBottomPanel::bottom(if open {
        "edit-regions-shelf"
    } else {
        "edit-regions-shelf-collapsed"
    })
    .show_separator_line(false)
    .frame(egui::Frame::NONE.fill(PANEL));
    if open {
        let max_height = (ui.available_height() * 0.48).max(174.0);
        shelf = shelf
            .resizable(true)
            .default_height(222.0)
            .height_range(174.0..=max_height);
    } else {
        shelf = shelf.resizable(false).exact_height(29.0);
    }
    shelf.show_inside(ui, |ui| {
        // Even an empty list retains the chosen height. Frame::NONE otherwise
        // reports only its contents' minimum size to the persistent panel state.
        ui.set_min_height(ui.available_height());
        contents(ui);
    });
}

fn source_range_controls(
    ui: &mut egui::Ui,
    source_range: &mut Option<strehl_edit::SourceRange>,
    count: Option<usize>,
    selected: usize,
) {
    let count = count.filter(|&count| count > 0);
    let mut enabled = source_range.is_some();
    if ui
        .add_enabled(
            count.is_some() || enabled,
            egui::Checkbox::new(&mut enabled, "Use a capture range"),
        )
        .changed()
    {
        *source_range = enabled.then(|| {
            let frame = selected.min(count.unwrap_or(1) - 1);
            strehl_edit::SourceRange {
                first: frame,
                last: frame,
            }
        });
    }
    if let Some(range) = source_range {
        let (mut first, mut last) = (range.first.saturating_add(1), range.last.saturating_add(1));
        let mut changed = false;
        ui.add_enabled_ui(count.is_some(), |ui| {
            ui.horizontal(|ui| {
                ui.label("From");
                changed |= ui
                    .add(
                        egui::DragValue::new(&mut first)
                            .range(1..=count.unwrap_or(usize::MAX))
                            .clamp_existing_to_range(false),
                    )
                    .changed();
                ui.label("to");
                changed |= ui
                    .add(
                        egui::DragValue::new(&mut last)
                            .range(1..=count.unwrap_or(usize::MAX))
                            .clamp_existing_to_range(false),
                    )
                    .changed();
            });
        });
        // A saved range is evidence, even when its original captures are missing.
        // Rendering a control must never rewrite it or silently queue a repair.
        if changed && let Some(count) = count {
            range.first = first.clamp(1, count) - 1;
            range.last = last.clamp(1, count).max(range.first + 1) - 1;
        }
        if count.is_some_and(|count| range.last >= count || range.first > range.last) {
            ui.colored_label(AMBER, "Saved range exceeds the available captures. Choose a valid range before re-stacking.");
        }
    }
    if count.is_none() {
        theme::caption(
            ui,
            "Original captures unavailable. The saved range is preserved.",
        );
    }
}

pub(super) fn hdr_luminance_controls(ui: &mut egui::Ui, hdr: &mut strehl_edit::HdrSettings) {
    controls::slider(
        ui,
        "Peak brightness",
        &mut hdr.peak_nits,
        hdr.reference_white_nits..=10_000.0,
        1000.0,
        0,
        " nits",
    );
    let max_white = hdr.peak_nits.min(500.0);
    controls::slider(
        ui,
        "Reference white",
        &mut hdr.reference_white_nits,
        80.0..=max_white,
        203.0_f32.min(max_white),
        0,
        " nits",
    );
}

#[derive(Default)]
pub(super) struct RegionalInspector {
    key: Option<(PathBuf, u64, String, bool)>,
    pending: Option<Task<(serde_json::Value, serde_json::Value)>>,
    value: Option<(serde_json::Value, serde_json::Value)>,
}

impl StrehlApp {
    pub(super) fn handle_close(&mut self, ctx: &egui::Context) {
        let requested = ctx.input(|input| input.viewport().close_requested());
        if !requested && !self.close_after_export && !self.close_after_presets {
            return;
        }
        if self.editor.exporting.is_some() {
            self.close_after_export = true;
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.status = "Finishing the photograph export before closing…".into();
            ctx.request_repaint_after(Duration::from_millis(100));
            return;
        }
        let waited = std::mem::take(&mut self.close_after_export);
        if waited && self.editor.last_export.is_none() {
            self.close_after_presets = false;
            // Encoding failed: keep its explanation and the editable image
            // visible instead of closing on a failed background operation.
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.sidebar = Some(workspace::Sidebar::Export);
            return;
        }
        let waited_for_presets = std::mem::take(&mut self.close_after_presets);
        match self.flush_presets(ctx) {
            Ok(false) => {
                self.close_after_presets = true;
                ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
                self.status = "Saving presets before closing…".into();
                ctx.request_repaint_after(Duration::from_millis(100));
                return;
            }
            Err(error) => {
                ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
                self.editor.error = Some(format!("Presets could not be saved: {error:#}"));
                self.sidebar = Some(workspace::Sidebar::Edit);
                return;
            }
            Ok(true) => {}
        }
        if let Err(error) = self.editor.ensure_saved_on_close() {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.editor.error = Some(format!("Edits could not be saved: {error:#}"));
            self.sidebar = Some(workspace::Sidebar::Edit);
        } else if waited || waited_for_presets {
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
        }
    }

    pub(super) fn poll_editing(&mut self, ctx: &egui::Context) {
        if let Some(path) = self
            .result
            .as_ref()
            .filter(|path| Some(*path) == self.image_path.as_ref())
        {
            self.editor.open(path.clone());
        }
        self.editor.poll(ctx, self.max_texture_side);
        self.edit_pane.reconcile(&self.editor);
        self.poll_adaptive(ctx);
        self.poll_presets(ctx);
        self.poll_region_inspector(ctx);
        if let Some((_, time)) = self.editor.pending_edit
            && !ctx.input(|input| input.pointer.any_down())
            && ctx.input(|input| input.time) - time > 0.3
        {
            self.editor.commit_edit();
        }
        if let Some(result) = self
            .editor
            .dialog
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.editor.dialog = None;
            let kind = self.editor.dialog_kind.take();
            match result {
                Ok(Some(path)) if kind == Some("export-destination") => {
                    if let Err(error) = self.set_export_directory(path) {
                        self.editor.error = Some(error.to_string());
                    }
                }
                Ok(Some(path)) if kind == Some("preset") => {
                    if let Err(error) = self.editor.import_preset(path) {
                        self.editor.error = Some(error.to_string());
                    }
                }
                Ok(Some(path)) => {
                    if let Err(error) = self.finish_export_dialog(path) {
                        self.editor.error = Some(error.to_string());
                    }
                }
                Ok(None) => self.export_pane.pending = None,
                Err(error) => {
                    self.export_pane.pending = None;
                    self.editor.error = Some(error);
                }
            }
        }
        if self.editor.dialog.is_some() {
            ctx.request_repaint_after(Duration::from_millis(100));
        }
    }

    pub(super) fn edit_panel(&mut self, ui: &mut egui::Ui) {
        if self.editor.loaded.is_none() {
            egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                self.editor.recovery_panel(ui);
                ui.label(if self.editor.loading.is_some() {
                    "Opening photograph…"
                } else {
                    "Choose a completed stack to edit its photograph."
                });
                if let Some(error) = &self.editor.error {
                    ui.colored_label(AMBER, error);
                }
            });
            return;
        }
        let before = self.editor.recipe.clone();
        let history_before = self.editor.history_revision();
        let document_before = self.editor.path.clone();
        self.editor.reconcile_selection();
        self.edit_pane.reconcile(&self.editor);
        self.edit_header(ui);
        let shelf_open = ui
            .ctx()
            .data_mut(|data| data.get_temp::<bool>(egui::Id::new("regions-shelf-open")))
            .unwrap_or(true);
        region_shelf(ui, shelf_open, |ui| self.edit_region_shelf(ui, shelf_open));
        let control_scope = (self.editor.path.clone(), self.editor.selected.clone());
        egui::ScrollArea::vertical()
            .id_salt("photo-adjustments-scroll")
            .auto_shrink([false, false])
            .show(ui, |ui| {
                controls::adjustment_scope(
                    ui,
                    control_scope.0.as_deref(),
                    control_scope.1.as_deref(),
                    |ui| {
                        ui.spacing_mut().item_spacing.y = 0.0;
                        egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                            self.editor.recovery_panel(ui);
                            self.adaptive_panel(ui);
                        });
                        if controls::section(ui, "presets", "Presets", false) {
                            egui::Frame::NONE
                                .inner_margin(12)
                                .show(ui, |ui| self.presets_panel(ui));
                        }
                        if controls::section(ui, "light", "Light", true) {
                            egui::Frame::NONE
                                .inner_margin(egui::Margin::symmetric(12, 7))
                                .show(ui, |ui| {
                                    let adjustments = self.current_adjustments();
                                    controls::slider(
                                        ui,
                                        "Exposure",
                                        &mut adjustments.exposure,
                                        -8.0..=8.0,
                                        0.0,
                                        2,
                                        " EV",
                                    );
                                    for (label, value) in [
                                        ("Contrast", &mut adjustments.contrast),
                                        ("Highlights", &mut adjustments.highlights),
                                        ("Shadows", &mut adjustments.shadows),
                                        ("Whites", &mut adjustments.whites),
                                        ("Blacks", &mut adjustments.blacks),
                                    ] {
                                        controls::slider(
                                            ui,
                                            label,
                                            value,
                                            -100.0..=100.0,
                                            0.0,
                                            0,
                                            "",
                                        );
                                    }
                                });
                        }
                        if controls::section(ui, "color", "Color", true) {
                            egui::Frame::NONE
                                .inner_margin(egui::Margin::symmetric(12, 7))
                                .show(ui, |ui| {
                                    let adjustments = self.current_adjustments();
                                    for (label, value) in [
                                        ("Warmth", &mut adjustments.temperature),
                                        ("Tint", &mut adjustments.tint),
                                        ("Vibrance", &mut adjustments.vibrance),
                                        ("Saturation", &mut adjustments.saturation),
                                    ] {
                                        controls::slider(
                                            ui,
                                            label,
                                            value,
                                            -100.0..=100.0,
                                            0.0,
                                            0,
                                            "",
                                        );
                                    }
                                });
                        }
                        if self.editor.selected.is_some() {
                            if controls::section(ui, "mask", "Selection", false) {
                                egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                                    let selected = self.editor.selected.clone();
                                    if let Some(region) = self
                                        .editor
                                        .recipe
                                        .regions
                                        .iter_mut()
                                        .find(|r| Some(&r.id) == selected.as_ref())
                                    {
                                        controls::slider(
                                            ui,
                                            "Feather",
                                            &mut region.feather,
                                            0.0..=1.0,
                                            0.4,
                                            2,
                                            "",
                                        );
                                        ui.add(
                                            egui::TextEdit::multiline(&mut region.note)
                                                .hint_text("Add a note…")
                                                .desired_rows(2)
                                                .desired_width(f32::INFINITY),
                                        );
                                        if region.note.len() > 4096 {
                                            region.note = bounded_text(&region.note, 4096);
                                        }
                                    }
                                });
                            }
                            if controls::section(
                                ui,
                                "source-repair",
                                if self.source_repairs_pending() {
                                    "Source repair · pending"
                                } else {
                                    "Source repair"
                                },
                                false,
                            ) {
                                egui::Frame::NONE
                                    .inner_margin(12)
                                    .show(ui, |ui| self.source_repair_panel(ui));
                            }
                            if controls::section(ui, "source-evidence", "Source evidence", false) {
                                egui::Frame::NONE
                                    .inner_margin(12)
                                    .show(ui, |ui| self.region_inspector(ui));
                            }
                        }
                        if controls::section(ui, "display", "Display", false) {
                            egui::Frame::NONE
                                .inner_margin(12)
                                .show(ui, |ui| self.edit_display_panel(ui));
                        }
                        if !self.editor.warnings.is_empty() || self.editor.error.is_some() {
                            egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                                for warning in &self.editor.warnings {
                                    ui.colored_label(AMBER, warning);
                                }
                                if let Some(error) = &self.editor.error {
                                    ui.colored_label(AMBER, error);
                                }
                            });
                        }
                    },
                );
            });
        if self.editor.loaded.is_some()
            && self.editor.path == document_before
            && before != self.editor.recipe
            && history_before == self.editor.history_revision()
        {
            self.editor.before = false;
            self.editor.begin_edit(before, ui.input(|input| input.time));
        }
    }

    fn current_adjustments(&mut self) -> &mut Adjustments {
        if let Some(index) = self
            .editor
            .recipe
            .regions
            .iter()
            .position(|r| Some(&r.id) == self.editor.selected.as_ref())
        {
            &mut self.editor.recipe.regions[index].adjustments
        } else {
            &mut self.editor.recipe.global
        }
    }

    fn edit_header(&mut self, ui: &mut egui::Ui) {
        egui::Frame::NONE
            .inner_margin(egui::Margin::symmetric(12, 8))
            .show(ui, |ui| {
                ui.horizontal(|ui| {
                    let selected = self.editor.selected.is_some();
                    if controls::quiet_button(ui, "Photograph", !selected)
                        .on_hover_text("Adjust the whole photograph")
                        .clicked()
                    {
                        self.editor.selected = None;
                        self.editor.cancel_geometry();
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.menu_button("···", |ui| {
                            if ui.button("Import XMP preset…").clicked()
                                && self.editor.dialog.is_none()
                            {
                                self.editor.dialog_kind = Some("preset");
                                self.editor.dialog =
                                    Some(jobs::spawn_task("strehl-preset-picker", |_| {
                                        Ok(rfd::FileDialog::new()
                                            .add_filter("Camera Raw preset", &["xmp"])
                                            .pick_file())
                                    }));
                                ui.close();
                            }
                            if ui.button("Reset selected adjustments").clicked() {
                                *self.current_adjustments() = Adjustments::default();
                                self.editor
                                    .recipe
                                    .clear_adaptive_scope(self.editor.selected.as_deref());
                                ui.close();
                            }
                            ui.separator();
                            ui.checkbox(&mut self.edit_photo_focus, "Give photograph more room");
                            ui.checkbox(&mut self.editor.show_regions, "Show selections");
                        });
                        if controls::quiet_button(ui, "Before", self.editor.before)
                            .on_hover_text("Compare with the original photograph")
                            .clicked()
                        {
                            self.editor.before = !self.editor.before;
                        }
                    });
                });
                if let Some(presenter) = &self.editor.viewport.presenter {
                    let display = presenter.status();
                    let raw =
                        self.editor.loaded.as_ref().is_some_and(|p| {
                            p.image.origin == strehl_edit::ImageOrigin::SceneLinear
                        });
                    let caption = match (display.active, raw) {
                        (true, true) => "HDR display · HDR photograph",
                        (true, false) => "HDR display · SDR photograph",
                        (false, true) => "SDR display · HDR photograph",
                        (false, false) => "SDR display · SDR photograph",
                    };
                    ui.add(
                        egui::Label::new(RichText::new(caption).size(10.0).color(MUTED)).truncate(),
                    )
                    .on_hover_text(format!(
                        "{} · {}\nDisplay & export has the full display and photo details.",
                        display.monitor, display.reason
                    ));
                }
                let region = self
                    .editor
                    .selected
                    .as_ref()
                    .and_then(|id| self.editor.recipe.regions.iter().find(|r| &r.id == id));
                if let Some(region) = region {
                    ui.add(
                        egui::Label::new(RichText::new(&region.name).size(13.0).color(ACCENT))
                            .truncate(),
                    );
                    theme::caption(
                        ui,
                        if region.enabled {
                            "Light & color · selected region · live"
                        } else {
                            "Region disabled · enable it in Regions to see edits"
                        },
                    );
                } else {
                    theme::caption(ui, "Light & color · whole photograph · live");
                }
            });
    }

    fn edit_region_shelf(&mut self, ui: &mut egui::Ui, open: bool) {
        let (heading, hit) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 29.0), egui::Sense::click());
        theme::rule(ui.painter(), heading.left_top(), heading.right_top(), LINE);
        let center = heading.left_center() + egui::vec2(12.0, 0.0);
        let points = if open {
            [
                center + egui::vec2(-3.0, -1.5),
                center + egui::vec2(0.0, 1.5),
                center + egui::vec2(3.0, -1.5),
            ]
        } else {
            [
                center + egui::vec2(-1.5, -3.0),
                center + egui::vec2(1.5, 0.0),
                center + egui::vec2(-1.5, 3.0),
            ]
        };
        ui.painter().add(egui::Shape::line(
            points.to_vec(),
            Stroke::new(1.0f32, MUTED),
        ));
        ui.painter().text(
            heading.left_center() + egui::vec2(25.0, 0.0),
            egui::Align2::LEFT_CENTER,
            format!("Regions  {}", self.editor.recipe.regions.len()),
            egui::FontId::proportional(11.0),
            INK,
        );
        if hit.clicked() {
            ui.ctx()
                .data_mut(|data| data.insert_temp(egui::Id::new("regions-shelf-open"), !open));
        }
        if !open {
            return;
        }
        egui::Frame::NONE
            .inner_margin(egui::Margin::symmetric(8, 4))
            .show(ui, |ui| {
                for tools in [
                    [
                        (DrawingTool::Select, "Select", "Select, move, resize, or reshape a region"),
                        (DrawingTool::Lasso, "Lasso", "Draw a freehand selection · release to close"),
                        (DrawingTool::MagicLasso, "Magic lasso", "Enclose an object or defect with a little surrounding background · refine from image contrast"),
                    ],
                    [
                        (DrawingTool::Polygon, "Polygon", "Click vertices · Enter or first point finishes"),
                        (DrawingTool::Rectangle, "Rectangle", "Drag a rectangular region"),
                        (DrawingTool::Ellipse, "Ellipse", "Drag an elliptical region"),
                    ],
                ] {
                    ui.horizontal(|ui| {
                        ui.spacing_mut().item_spacing.x = 3.0;
                        let width = (ui.available_width() - 6.0) / 3.0;
                    for (tool, label, hint) in tools {
                            let active = self.editor.tool == tool;
                            if ui.add_sized([width, 24.0], egui::Button::new(
                                RichText::new(label).color(if active { ACCENT } else { MUTED }))
                                .selected(active).frame(active))
                            .on_hover_text(hint)
                            .clicked()
                        {
                            self.editor.set_tool(tool);
                        }
                    }
                    });
                }
                theme::caption(ui, "Space: pan / zoom · Alt: inspect · Esc: cancel");
                if let Some(status) = self.editor.magic_status() {
                    theme::caption(ui, status);
                }
            });
        controls::rule(ui);
        egui::ScrollArea::vertical()
            .id_salt("edit-regions-list")
            .auto_shrink([false, false])
            .show(ui, |ui| {
                let mut selected = None;
                let mut remove = None;
                let mut duplicate = None;
                let mut rename = None;
                let mut reset = None;
                let can_duplicate = self.editor.recipe.regions.len() < 128;
                for (index, region) in self.editor.recipe.regions.iter_mut().enumerate() {
                    let active = self.editor.selected.as_ref() == Some(&region.id);
                    let color = crate::process_sample_glyphs::level_color(index % 7);
                    let (row, _) = ui.allocate_exact_size(
                        egui::vec2(ui.available_width(), 29.0),
                        egui::Sense::hover(),
                    );
                    if active {
                        ui.painter().rect_filled(row, 0.0, crate::theme::RAISED);
                        theme::rule(ui.painter(), row.left_top(), row.left_bottom(), color);
                    }
                    let enabled = egui::Rect::from_center_size(
                        row.left_center() + egui::vec2(15.0, 0.0),
                        egui::vec2(18.0, 20.0),
                    );
                    ui.put(enabled, egui::Checkbox::without_text(&mut region.enabled))
                        .on_hover_text("Enable this region");
                    let name_rect = egui::Rect::from_min_max(
                        row.min + egui::vec2(30.0, 3.0),
                        row.max - egui::vec2(10.0, 3.0),
                    );
                    if let Some((id, text)) = &mut self.edit_pane.rename
                        && id == &region.id
                    {
                        if rename_region(ui, name_rect, id, text, &mut region.name) {
                            self.edit_pane.rename = None;
                        }
                    } else {
                        let response = ui
                            .interact(
                                name_rect,
                                ui.id().with(("region-row", &region.id)),
                                egui::Sense::click(),
                            )
                            .on_hover_text(&region.name);
                        let galley = ui.painter().layout_no_wrap(
                            region.name.clone(),
                            egui::FontId::proportional(11.0),
                            if active { INK } else { MUTED },
                        );
                        ui.painter().with_clip_rect(name_rect).galley(
                            name_rect.left_center() - egui::vec2(0.0, galley.size().y * 0.5),
                            galley,
                            INK,
                        );
                        if response.clicked() {
                            selected = Some(region.id.clone());
                        }
                        if response.double_clicked() {
                            rename = Some((region.id.clone(), region.name.clone()));
                        }
                        response.context_menu(|ui| {
                            if ui.button("Rename").clicked() {
                                rename = Some((region.id.clone(), region.name.clone()));
                                ui.close();
                            }
                            if ui
                                .add_enabled(can_duplicate, egui::Button::new("Duplicate"))
                                .on_disabled_hover_text("This photograph already has 128 regions.")
                                .clicked()
                            {
                                duplicate = Some(region.id.clone());
                                ui.close();
                            }
                            if ui.button("Reset light & color").clicked() {
                                region.adjustments = Adjustments::default();
                                reset = Some(region.id.clone());
                                ui.close();
                            }
                            ui.separator();
                            if ui.button("Delete region").clicked() {
                                remove = Some(region.id.clone());
                                ui.close();
                            }
                        });
                    }
                }
                if let Some(id) = selected {
                    self.editor.commit_edit();
                    self.editor.selected = Some(id);
                    self.editor.set_tool(DrawingTool::Select);
                    self.editor.show_regions = true;
                }
                if let Some((id, name)) = rename {
                    self.edit_pane.rename = Some((id.clone(), name));
                    // The text field exists on the next frame. Request focus only once.
                    let field_id = egui::Id::new(("rename-region", id));
                    ui.ctx()
                        .data_mut(|d| d.insert_temp(field_id.with("request-focus"), true));
                }
                if let Some(id) = remove {
                    self.editor.recipe.regions.retain(|r| r.id != id);
                    self.editor.recipe.clear_adaptive_scope(Some(&id));
                    if self.editor.selected.as_ref() == Some(&id) {
                        self.editor.selected = None;
                    }
                    self.editor.cancel_geometry();
                }
                if let Some(id) = reset {
                    self.editor.recipe.clear_adaptive_scope(Some(&id));
                }
                if let Some(id) = duplicate
                    && let Err(error) = duplicate_region(&mut self.editor, &id)
                {
                    self.editor.error = Some(error.to_string());
                }
                if self.editor.recipe.regions.is_empty() {
                    egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                        theme::caption(ui, "Draw on the photograph to adjust just that area.");
                    });
                }
            });
    }

    fn source_repair_panel(&mut self, ui: &mut egui::Ui) {
        theme::caption(
            ui,
            "Choose different captures for this area. This changes the stack itself; Light and Color above update the current photograph immediately.",
        );
        let selected = self.editor.selected.clone();
        if let Some(region) = self
            .editor
            .recipe
            .regions
            .iter_mut()
            .find(|r| Some(&r.id) == selected.as_ref())
        {
            source_range_controls(
                ui,
                &mut region.source_range,
                self.stack.as_ref().map(|stack| stack.frames.len()),
                self.selected,
            );
        }
        let pending = self.source_repairs_pending();
        ui.add_space(7.0);
        if pending {
            ui.colored_label(AMBER, "Source change pending · photograph unchanged");
            let blocker = self.stack_start_blocker();
            if ui
                .add_enabled(
                    blocker.is_none(),
                    egui::Button::new("Re-stack with source changes"),
                )
                .on_disabled_hover_text(blocker.unwrap_or_default())
                .clicked()
            {
                self.editor.commit_edit();
                self.start_render();
            }
        } else {
            theme::caption(ui, "No source changes waiting to be applied.");
        }
    }

    pub(super) fn source_repairs_pending(&self) -> bool {
        self.editor.loaded.as_ref().is_some_and(|loaded| {
            loaded
                .image
                .validate_source_repairs(&self.editor.recipe)
                .is_err()
        })
    }

    fn edit_display_panel(&mut self, ui: &mut egui::Ui) {
        let hdr_photo = self
            .editor
            .loaded
            .as_ref()
            .is_some_and(|loaded| loaded.image.origin == strehl_edit::ImageOrigin::SceneLinear);
        if let Some(presenter) = &self.editor.viewport.presenter {
            let display = presenter.status();
            ui.label(
                RichText::new(if display.active {
                    "Display · HDR active"
                } else {
                    "Display · SDR"
                })
                .color(if display.active { GREEN } else { MUTED }),
            );
            theme::caption(ui, &display.monitor);
            theme::caption(ui, &display.reason);
            if display.active {
                theme::caption(
                    ui,
                    &format!(
                        "{:.0} nits white · {:.0} nits peak",
                        display.sdr_white_nits, display.peak_nits
                    ),
                );
            }
        }
        ui.add_space(6.0);
        if hdr_photo {
            ui.label("Photograph · RAW-derived HDR master");
            hdr_luminance_controls(ui, &mut self.editor.recipe.hdr);
        } else {
            ui.label("Photograph · SDR file");
            theme::caption(
                ui,
                "This saved image has no HDR highlight data. A new stack retains the RAW-derived HDR master.",
            );
        }
    }

    fn poll_region_inspector(&mut self, ctx: &egui::Context) {
        let selected = self.editor.selected.as_ref().and_then(|id| {
            self.editor
                .recipe
                .regions
                .iter()
                .find(|region| &region.id == id)
        });
        let current = self.result.as_ref().filter(|path| {
            self.editor.path.as_ref() == Some(*path) && self.image_path.as_ref() == Some(*path)
        });
        let desired = current.zip(selected).map(|(path, region)| {
            (
                path.clone(),
                self.editor.revision,
                region.id.clone(),
                self.editor.before,
            )
        });
        if desired != self.regional.key {
            self.regional = RegionalInspector {
                key: desired,
                ..Default::default()
            };
        }
        if let Some(result) = self
            .regional
            .pending
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.regional.pending = None;
            if let Ok(value) = result {
                self.regional.value = Some(value);
            }
        }
        if self.sidebar == Some(workspace::Sidebar::Edit)
            && self.regional.value.is_none()
            && self.regional.pending.is_none()
            && self.editor.pending_edit.is_none()
            && let (Some(region), Some(loaded)) = (selected, self.editor.loaded.as_ref())
            && current.is_some()
        {
            let region = region.shape.clone();
            let image = std::sync::Arc::clone(&loaded.preview);
            let recipe = if self.editor.before {
                DevelopmentRecipe::default()
            } else {
                self.editor.recipe.clone()
            };
            let archive = self.progress.admission_archive.clone();
            let certified = crate::process_output_space::OutputSpace::from_progress(
                &self.progress,
                self.result_viewer.source_size,
            )
            .is_some();
            self.regional.pending = Some(jobs::spawn_task("strehl-region-inspection", move |_| {
                Ok((
                    agent::region_statistics(&image, &recipe, &region),
                    agent::probe_region(&archive, &region, 6, certified),
                ))
            }));
        }
        if self.regional.pending.is_some() {
            ctx.request_repaint_after(Duration::from_millis(50));
        }
    }

    fn region_inspector(&mut self, ui: &mut egui::Ui) {
        if self.editor.selected.is_none() {
            return;
        }
        ui.separator();
        ui.label(
            RichText::new("REGION / SOURCE EVIDENCE")
                .monospace()
                .size(9.0)
                .color(ACCENT),
        );
        let Some((pixels, evidence)) = &self.regional.value else {
            theme::caption(ui, "Measuring the selected region…");
            return;
        };
        if let Some(samples) = pixels["samples"].as_u64() {
            theme::caption(ui, &format!("{samples} linear preview samples"));
            if let (Some(mean), Some(peak)) = (
                pixels["mean_luminance"].as_f64(),
                pixels["maximum_luminance"].as_f64(),
            ) {
                theme::caption(ui, &format!("Light: {:.3} mean · {:.3} peak", mean, peak));
                if let Some(over) = pixels["above_source_reference"].as_u64() {
                    theme::caption(
                        ui,
                        &format!(
                            "{:.1}% above {} · before display placement",
                            100.0 * over as f64 / samples.max(1) as f64,
                            pixels["reference_kind"]
                                .as_str()
                                .unwrap_or("source reference")
                        ),
                    );
                }
            }
        }
        if self.progress.source_repair.is_some() {
            ui.colored_label(AMBER, "Source bars describe the original merge. This result includes local source repairs.");
        }
        let mut inspect = None;
        if let Some(sources) = evidence["sources"].as_array() {
            theme::caption(ui, "Fine-detail admission · click a capture to compare");
            for source in sources {
                let Some(frame) = source["frame"].as_u64().map(|value| value as usize) else {
                    continue;
                };
                let Some(level) = source["levels"]
                    .as_array()
                    .and_then(|levels| levels.first())
                else {
                    continue;
                };
                let fraction = level["admitted"].as_f64().unwrap_or(0.0)
                    / level["observed"].as_f64().unwrap_or(1.0).max(1.0);
                let (rect, response) = ui.allocate_exact_size(
                    egui::vec2(ui.available_width(), 23.0),
                    egui::Sense::click(),
                );
                let bar = egui::Rect::from_min_max(
                    rect.min + egui::vec2(65.0, 5.0),
                    rect.max - egui::vec2(38.0, 5.0),
                );
                ui.painter().rect_filled(bar, 0.0, BG);
                ui.painter().rect_filled(
                    egui::Rect::from_min_size(
                        bar.min,
                        egui::vec2(bar.width().max(0.0) * fraction as f32, bar.height()),
                    ),
                    0.0,
                    GREEN,
                );
                ui.painter().text(
                    rect.left_center(),
                    egui::Align2::LEFT_CENTER,
                    format!("{:03}", frame + 1),
                    egui::FontId::monospace(10.0),
                    INK,
                );
                ui.painter().text(
                    rect.right_center(),
                    egui::Align2::RIGHT_CENTER,
                    format!("{:.0}%", 100.0 * fraction),
                    egui::FontId::monospace(10.0),
                    MUTED,
                );
                if response.clicked() {
                    inspect = Some(frame);
                }
            }
            theme::caption(
                ui,
                "Recorded coefficient admissions, not a percentage of final RGB pixels.",
            );
        } else {
            theme::caption(
                ui,
                evidence["reason"]
                    .as_str()
                    .unwrap_or("No retained source evidence in this region."),
            );
        }
        if let Some(frame) = inspect {
            self.inspect_frame(frame);
        }
    }
}
