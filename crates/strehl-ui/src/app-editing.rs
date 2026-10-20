use super::*;
use crate::edit_workspace::DrawingTool;
use strehl_edit::{Adjustments, DevelopmentRecipe};

#[derive(Default)]
pub(super) struct RegionalInspector {
    key: Option<(PathBuf, u64, String, bool)>,
    pending: Option<Task<(serde_json::Value, serde_json::Value)>>,
    value: Option<(serde_json::Value, serde_json::Value)>,
}

impl StrehlApp {
    pub(super) fn handle_close(&mut self, ctx: &egui::Context) {
        let requested = ctx.input(|input| input.viewport().close_requested());
        if !requested && !self.close_after_export {
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
            // Encoding failed: keep its explanation and the editable image
            // visible instead of closing on a failed background operation.
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.sidebar = Some(workspace::Sidebar::Edit);
            return;
        }
        if let Err(error) = self.editor.ensure_saved_on_close() {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.editor.error = Some(format!("Edits could not be saved: {error:#}"));
            self.sidebar = Some(workspace::Sidebar::Edit);
        } else if waited {
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
        self.poll_adaptive(ctx);
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
                Ok(Some(path)) if kind == Some("preset") => {
                    if let Err(error) = self.editor.import_preset(path) {
                        self.editor.error = Some(error.to_string());
                    }
                }
                Ok(Some(path)) => {
                    if let Err(error) = self.editor.export(path, kind == Some("hdr")) {
                        self.editor.error = Some(error.to_string());
                    }
                }
                Ok(None) => {}
                Err(error) => self.editor.error = Some(error),
            }
        }
        if self.editor.dialog.is_some() {
            ctx.request_repaint_after(Duration::from_millis(100));
        }
    }

    pub(super) fn edit_panel(&mut self, ui: &mut egui::Ui) {
        self.editor.recovery_panel(ui);
        let ready = self.editor.loaded.is_some();
        if !ready {
            ui.label(if self.editor.loading.is_some() {
                "Opening the editable photograph…"
            } else {
                "Stack a photograph, then develop its light and color here."
            });
            if let Some(error) = &self.editor.error {
                ui.colored_label(AMBER, error);
            }
            return;
        }
        let hdr_available = self
            .editor
            .loaded
            .as_ref()
            .is_some_and(|loaded| loaded.image.origin == strehl_edit::ImageOrigin::SceneLinear);
        let before = self.editor.recipe.clone();
        let history_before = self.editor.history_revision();
        ui.horizontal(|ui| {
            ui.label(RichText::new("DEVELOP").monospace().size(9.0).color(ACCENT));
            ui.checkbox(&mut self.editor.before, "Before");
            if ui.button("Reset").clicked() {
                let _ = self.editor.replace(DevelopmentRecipe::default());
                self.editor.selected = None;
            }
        });
        ui.checkbox(&mut self.edit_photo_focus, "Photograph focus")
            .on_hover_text("Give the photograph room while editing. Turn off to bring the process instruments alongside it.");
        if let Some(loaded) = &self.editor.loaded {
            let origin = match loaded.image.origin {
                strehl_edit::ImageOrigin::SceneLinear => "RAW-derived master",
                strehl_edit::ImageOrigin::DisplayReferred => "SDR photograph",
            };
            theme::caption(
                ui,
                &format!(
                    "{} × {} · {origin}",
                    loaded.image.width, loaded.image.height
                ),
            );
        }
        ui.add_space(8.0);
        self.adaptive_panel(ui);
        ui.horizontal(|ui| {
            if ui.button("Import preset…").clicked() && self.editor.dialog.is_none() {
                self.editor.dialog_kind = Some("preset");
                self.editor.dialog = Some(jobs::spawn_task("strehl-preset-picker", |_| {
                    Ok(rfd::FileDialog::new()
                        .add_filter("Camera Raw preset", &["xmp"])
                        .pick_file())
                }));
            }
            if ui
                .add_enabled(self.editor.can_undo(), egui::Button::new("Undo"))
                .clicked()
            {
                self.editor.undo();
            }
        });
        ui.separator();
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.editor.selected, None, "Whole photograph");
        });
        ui.horizontal(|ui| {
            for (tool, label) in [
                (DrawingTool::Navigate, "Pan"),
                (DrawingTool::Ellipse, "Circle"),
                (DrawingTool::Rectangle, "Box"),
                (DrawingTool::Polygon, "Lasso"),
            ] {
                if ui
                    .selectable_value(&mut self.editor.tool, tool, label)
                    .clicked()
                {
                    self.editor.drag = None;
                    self.editor.polygon.clear();
                }
            }
        });
        if self.editor.tool != DrawingTool::Navigate {
            theme::caption(
                ui,
                if self.editor.tool == DrawingTool::Polygon {
                    "Click points on the photograph · Enter finishes · Esc cancels"
                } else {
                    "Drag over the photograph to make a feathered region · Esc cancels"
                },
            );
        }
        let mut delete = None;
        for region in &self.editor.recipe.regions {
            ui.horizontal(|ui| {
                if ui
                    .selectable_label(
                        self.editor.selected.as_ref() == Some(&region.id),
                        &region.name,
                    )
                    .clicked()
                {
                    self.editor.selected = Some(region.id.clone());
                }
                if ui
                    .small_button("×")
                    .on_hover_text("Remove this region; original pixels stay intact")
                    .clicked()
                {
                    delete = Some(region.id.clone());
                }
            });
        }
        if let Some(id) = delete {
            self.editor.recipe.regions.retain(|region| region.id != id);
            if self.editor.selected.as_ref() == Some(&id) {
                self.editor.selected = None;
            }
        }
        ui.checkbox(&mut self.editor.show_regions, "Show region outlines");
        let selected = self.editor.selected.clone();
        if let Some(region) = self
            .editor
            .recipe
            .regions
            .iter_mut()
            .find(|region| Some(&region.id) == selected.as_ref())
        {
            ui.separator();
            ui.text_edit_singleline(&mut region.name);
            ui.add(
                egui::TextEdit::multiline(&mut region.note)
                    .hint_text("What needs attention here?")
                    .desired_rows(2),
            );
            ui.checkbox(&mut region.enabled, "Apply this region");
            ui.add(egui::Slider::new(&mut region.feather, 0.0..=1.0).text("Feather"));
            egui::CollapsingHeader::new("Stack repair · next run").show(ui, |ui| {
                let mut enabled = region.source_range.is_some();
                if ui.checkbox(&mut enabled, "Use only a capture span here").changed() {
                    region.source_range = enabled.then_some(strehl_edit::SourceRange { first: self.selected, last: self.selected });
                }
                if let Some(range) = &mut region.source_range {
                    let count = self.stack.as_ref().map_or(1, |stack| stack.frames.len()).max(1);
                    let (mut first, mut last) = (range.first + 1, range.last + 1);
                    ui.horizontal(|ui| {
                        ui.label("Captures");
                        ui.add(egui::DragValue::new(&mut first).range(1..=count));
                        ui.label("to");
                        ui.add(egui::DragValue::new(&mut last).range(first..=count));
                    });
                    range.first = first - 1; range.last = last.max(first) - 1;
                    theme::caption(ui, "Reconstruct this region from these captures on the next Stack. Feather joins it to the original merge. Extra reconstruction pass; no new alignment.");
                }
            });
            adjustment_controls(ui, &mut region.adjustments);
        } else {
            adjustment_controls(ui, &mut self.editor.recipe.global);
        }
        ui.separator();
        egui::CollapsingHeader::new("HDR display & output").default_open(hdr_available).show(ui, |ui| {
            if let Some(presenter) = &self.editor.viewport.presenter {
                let status = presenter.status();
                ui.label(RichText::new(if status.active && hdr_available {
                    "HDR photograph · native display"
                } else {
                    "SDR photograph preview"
                }).color(if status.active && hdr_available { ACCENT } else { MUTED }));
                theme::caption(ui, &status.reason);
                if status.active && hdr_available {
                    theme::caption(ui, &format!("{:.1}× display headroom · visible detail refines automatically", status.headroom));
                }
            }
            if !hdr_available {
                theme::caption(ui, "Re-stack to retain a RAW-derived master for HDR. This saved photograph has SDR pixels.");
                return;
            }
            ui.add(egui::Slider::new(&mut self.editor.recipe.hdr.peak_nits, 203.0..=4000.0).logarithmic(true).text("Peak nits"));
            ui.add(egui::Slider::new(&mut self.editor.recipe.hdr.reference_white_nits, 80.0..=self.editor.recipe.hdr.peak_nits.min(500.0)).text("White nits"));
            ui.add(egui::Slider::new(&mut self.editor.recipe.hdr.quality, 1..=100).text("AVIF quality"));
            ui.add(egui::Slider::new(&mut self.editor.recipe.hdr.speed, 0..=10).text("Encode speed"));
            theme::caption(ui, "AVIF: 10-bit PQ · BT.2020 container\nWorking color: linear BT.709");
        });
        let needs_restack = self.editor.loaded.as_ref().is_some_and(|loaded| {
            loaded
                .image
                .validate_source_repairs(&self.editor.recipe)
                .is_err()
        });
        if needs_restack {
            ui.colored_label(
                AMBER,
                "Stack again to apply the changed capture regions before exporting.",
            );
        }
        ui.horizontal(|ui| {
            for (kind, label, extension) in [
                ("hdr", "Export HDR AVIF…", "avif"),
                ("sdr", "TIFF…", "tiff"),
            ] {
                if ui
                    .add_enabled(
                        self.editor.exporting.is_none()
                            && self.editor.dialog.is_none()
                            && !needs_restack
                            && (kind != "hdr" || hdr_available),
                        egui::Button::new(label),
                    )
                    .on_disabled_hover_text(if needs_restack {
                        "The photograph still contains the previous source repair. Stack to rebuild it."
                    } else if kind == "hdr" && !hdr_available {
                        "HDR needs a RAW-derived master. The next stack saves one automatically."
                    } else {
                        "Finish the current export or file selection first."
                    })
                    .clicked()
                {
                    self.editor.dialog_kind = Some(kind);
                    let name = format!("Strehl-edited.{extension}");
                    self.editor.dialog =
                        Some(jobs::spawn_task("strehl-export-picker", move |_| {
                            Ok(rfd::FileDialog::new()
                                .set_file_name(name)
                                .add_filter("Photograph", &[extension])
                                .save_file())
                        }));
                }
            }
        });
        if self.editor.exporting.is_some() {
            ui.label("Encoding photograph… You can keep exploring.");
        }
        if let Some(path) = &self.editor.last_export {
            ui.colored_label(GREEN, "Export saved");
            ui.label(path.file_name().unwrap_or_default().to_string_lossy());
        }
        for warning in &self.editor.warnings {
            ui.colored_label(AMBER, warning);
        }
        if let Some(error) = &self.editor.error {
            ui.colored_label(AMBER, error);
        }
        if before != self.editor.recipe && history_before == self.editor.history_revision() {
            self.editor.begin_edit(before, ui.input(|input| input.time));
        }
        self.region_inspector(ui);
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

fn adjustment_controls(ui: &mut egui::Ui, controls: &mut Adjustments) {
    ui.add(
        egui::Slider::new(&mut controls.exposure, -8.0..=8.0)
            .text("Exposure")
            .suffix(" EV"),
    );
    for (label, value) in [
        ("Contrast", &mut controls.contrast),
        ("Highlights", &mut controls.highlights),
        ("Shadows", &mut controls.shadows),
        ("Whites", &mut controls.whites),
        ("Blacks", &mut controls.blacks),
        ("Vibrance", &mut controls.vibrance),
        ("Saturation", &mut controls.saturation),
        ("Warmth", &mut controls.temperature),
        ("Tint", &mut controls.tint),
    ] {
        let hit = ui.add(egui::Slider::new(value, -100.0..=100.0).text(label));
        hit.on_hover_text("Drag to adjust · click the number to type");
    }
}
