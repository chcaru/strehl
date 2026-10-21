//! Delivery has its own pane; changing file options never edits the photograph.
use super::*;
use strehl_edit::{ExportFormat, ExportSettings, ImageOrigin, OutputColorSpace};

#[cfg(test)]
#[path = "export-pane-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "export-independent-tests.rs"]
mod independent_tests;

pub(super) struct PendingExport {
    document: PathBuf,
    revision: u64,
    settings: ExportSettings,
}

#[derive(Default)]
pub(super) struct ExportPaneState {
    settings: ExportSettings,
    pub(super) destination: Option<PathBuf>,
    pub(super) pending: Option<PendingExport>,
    started: Option<std::time::Instant>,
}

fn extension(format: ExportFormat) -> &'static str {
    match format {
        ExportFormat::Avif => "avif",
        ExportFormat::Tiff => "tiff",
        ExportFormat::Png => "png",
        ExportFormat::Jpeg => "jpg",
    }
}

fn format_label(format: ExportFormat) -> &'static str {
    match format {
        ExportFormat::Avif => "AVIF",
        ExportFormat::Tiff => "TIFF",
        ExportFormat::Png => "PNG",
        ExportFormat::Jpeg => "JPEG",
    }
}

fn effective_settings(settings: &ExportSettings, origin: ImageOrigin) -> ExportSettings {
    let mut effective = settings.clone();
    effective.hdr =
        settings.hdr && settings.format == ExportFormat::Avif && origin == ImageOrigin::SceneLinear;
    effective
}

fn formatted_path(mut path: PathBuf, format: ExportFormat) -> PathBuf {
    let suffix = path
        .extension()
        .and_then(|v| v.to_str())
        .unwrap_or_default();
    let matches = match format {
        ExportFormat::Avif => suffix.eq_ignore_ascii_case("avif"),
        ExportFormat::Tiff => ["tif", "tiff"]
            .iter()
            .any(|ext| suffix.eq_ignore_ascii_case(ext)),
        ExportFormat::Png => suffix.eq_ignore_ascii_case("png"),
        ExportFormat::Jpeg => ["jpg", "jpeg"]
            .iter()
            .any(|ext| suffix.eq_ignore_ascii_case(ext)),
    };
    if !matches {
        path.set_extension(extension(format));
    }
    path
}

fn information_row(ui: &mut egui::Ui, name: &str, value: &str) {
    ui.horizontal(|ui| {
        ui.label(RichText::new(name).small().color(MUTED));
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.label(RichText::new(value).small().color(INK));
        });
    });
}

impl StrehlApp {
    pub(super) fn set_export_directory(&mut self, path: PathBuf) -> anyhow::Result<()> {
        jobs::validate_export_destination(
            self.stack.as_ref().map(|s| s.directory.as_path()),
            &path,
        )?;
        anyhow::ensure!(path.is_dir(), "Choose an existing export folder.");
        self.export_pane.destination = Some(path);
        self.editor.error = None;
        Ok(())
    }

    pub(super) fn finish_export_dialog(&mut self, path: PathBuf) -> anyhow::Result<()> {
        let pending = self
            .export_pane
            .pending
            .take()
            .ok_or_else(|| anyhow::anyhow!("Choose an export format and try Export again."))?;
        anyhow::ensure!(
            self.editor.path.as_ref() == Some(&pending.document)
                && self.editor.revision == pending.revision,
            "The photograph changed while choosing a destination. Review it and export again."
        );
        let path = formatted_path(path, pending.settings.format);
        jobs::validate_export_destination(
            self.stack.as_ref().map(|stack| stack.directory.as_path()),
            path.parent()
                .ok_or_else(|| anyhow::anyhow!("Choose an export folder."))?,
        )?;
        let destination = path.parent().map(Path::to_path_buf);
        self.editor.export_with_settings(path, pending.settings)?;
        self.export_pane.destination = destination;
        self.export_pane.started = Some(std::time::Instant::now());
        Ok(())
    }

    pub(super) fn export_panel(&mut self, ui: &mut egui::Ui) {
        let Some(loaded) = self.editor.loaded.as_ref() else {
            egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                ui.label(if self.editor.loading.is_some() {
                    "Opening photograph…"
                } else {
                    "Choose a completed photograph to export."
                });
                if let Some(error) = &self.editor.error {
                    ui.colored_label(AMBER, error);
                }
            });
            return;
        };
        let origin = loaded.image.origin;
        let dimensions = [loaded.image.width, loaded.image.height];
        let pending_repair = self.source_repairs_pending();
        let current_photo = self.editor.path == self.result && self.editor.loading.is_none();
        let exporting = self.editor.exporting.is_some();
        let can_export = current_photo
            && !pending_repair
            && !exporting
            && self.editor.dialog.is_none()
            && !self.adaptive_busy()
            && !self.presets_busy();
        let effective = effective_settings(&self.export_pane.settings, origin);

        egui::TopBottomPanel::bottom("export-action")
            .resizable(false)
            .show_separator_line(false)
            .frame(egui::Frame::NONE.fill(PANEL))
            .show_inside(ui, |ui| {
                editing::controls::rule(ui);
                egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                    if let Some(task) = &self.editor.exporting {
                        ui.horizontal(|ui| {
                            ui.spinner();
                            let elapsed =
                                self.export_pane.started.map(|t| t.elapsed().as_secs_f32());
                            ui.label(if task.is_cancelled() {
                                "Cancelling export…".into()
                            } else {
                                elapsed
                                    .map(|s| format!("Encoding · {s:.0}s"))
                                    .unwrap_or_else(|| "Encoding photograph…".into())
                            });
                            if !task.is_cancelled() && ui.small_button("Cancel").clicked() {
                                task.cancel();
                            }
                        });
                        ui.ctx().request_repaint_after(Duration::from_millis(100));
                    } else if ui
                        .add_enabled(
                            can_export,
                            egui::Button::new(
                                RichText::new(format!(
                                    "Export {}…",
                                    format_label(effective.format)
                                ))
                                .color(ACCENT),
                            )
                            .min_size(egui::vec2(ui.available_width(), 31.0)),
                        )
                        .on_disabled_hover_text(if pending_repair {
                            "Re-stack the pending source changes before exporting."
                        } else {
                            "Wait for the current photograph operation to finish."
                        })
                        .clicked()
                    {
                        self.editor.commit_edit();
                        if let Some(document) = self.editor.path.clone() {
                            let suffix = extension(effective.format);
                            let stem = document.file_stem().unwrap_or_default().to_string_lossy();
                            let name = format!("{stem}-edited.{suffix}");
                            let directory = self.export_pane.destination.clone();
                            self.export_pane.pending = Some(PendingExport {
                                document,
                                revision: self.editor.revision,
                                settings: effective.clone(),
                            });
                            self.editor.dialog_kind = Some("export");
                            self.editor.dialog =
                                Some(jobs::spawn_task("strehl-export-picker", move |_| {
                                    let mut picker = rfd::FileDialog::new()
                                        .set_file_name(name)
                                        .add_filter(format_label(effective.format), &[suffix]);
                                    if let Some(directory) = directory {
                                        picker = picker.set_directory(directory);
                                    }
                                    Ok(picker.save_file())
                                }));
                        }
                    }
                    if pending_repair {
                        theme::caption(ui, "Source repair is waiting for Re-stack.");
                    }
                    if let Some(path) = &self.editor.last_export {
                        ui.colored_label(GREEN, "Photograph saved");
                        ui.label(
                            RichText::new(path.file_name().unwrap_or_default().to_string_lossy())
                                .small(),
                        )
                        .on_hover_text(path.display().to_string());
                        if ui.small_button("Copy path").clicked() {
                            ui.ctx().copy_text(path.display().to_string());
                        }
                    }
                    if let Some(error) = &self.editor.error {
                        ui.colored_label(AMBER, error);
                    }
                });
            });

        egui::ScrollArea::vertical().id_salt("export-options")
            .auto_shrink([false, false]).show(ui, |ui| {
                egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                    information_row(ui, "Photograph", if origin == ImageOrigin::SceneLinear {
                        "RAW-derived master"
                    } else { "SDR image" });
                    information_row(ui, "Output size", &format!("{} × {}", dimensions[0], dimensions[1]));
                    theme::caption(ui, "Full resolution · current edits");
                    ui.add_space(9.0);
                    ui.label(RichText::new("Destination").small().color(MUTED));
                    if let Some(directory) = &self.export_pane.destination {
                        ui.add(egui::Label::new(RichText::new(directory.file_name().unwrap_or_default().to_string_lossy()).small()).truncate())
                            .on_hover_text(directory.display().to_string());
                    }
                    if ui.add_enabled(self.editor.dialog.is_none() && !exporting, egui::Button::new(
                        if self.export_pane.destination.is_some() { "Change folder…" } else { "Choose folder…" })).clicked() {
                        let directory = self.export_pane.destination.clone();
                        self.editor.dialog_kind = Some("export-destination");
                        self.editor.dialog = Some(jobs::spawn_task("strehl-export-folder", move |_| {
                            let mut picker = rfd::FileDialog::new();
                            if let Some(directory) = directory { picker = picker.set_directory(directory); }
                            Ok(picker.pick_folder())
                        }));
                    }
                    if self.editor.before {
                        theme::caption(ui, "Before is a viewing comparison. Export includes your edits.");
                    }
                });
                editing::controls::rule(ui);
                egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                    ui.label(RichText::new("File format").small().color(MUTED));
                    let width = (ui.available_width() - 9.0) / 4.0;
                    ui.horizontal(|ui| {
                        ui.spacing_mut().item_spacing.x = 3.0;
                        for format in [ExportFormat::Avif, ExportFormat::Tiff, ExportFormat::Png, ExportFormat::Jpeg] {
                            if ui.add_sized([width, 27.0], egui::Button::new(format_label(format))
                                .selected(self.export_pane.settings.format == format)).clicked() {
                                self.export_pane.settings.format = format;
                            }
                        }
                    });
                    ui.add_space(12.0);
                    ui.label(RichText::new("Dynamic range").small().color(MUTED));
                    let supports_hdr = origin == ImageOrigin::SceneLinear
                        && self.export_pane.settings.format == ExportFormat::Avif;
                    let shown = effective_settings(&self.export_pane.settings, origin);
                    ui.horizontal(|ui| {
                        if ui.add_enabled(supports_hdr, egui::Button::new("HDR").selected(shown.hdr))
                            .on_disabled_hover_text("HDR requires the RAW-derived master and AVIF.").clicked() {
                            self.export_pane.settings.hdr = true;
                        }
                        if ui.selectable_label(!shown.hdr, "SDR").clicked() {
                            self.export_pane.settings.hdr = false;
                        }
                    });
                    if origin != ImageOrigin::SceneLinear {
                        theme::caption(ui, "This saved image is SDR. New stacks retain an HDR master.");
                    }
                    ui.add_space(12.0);
                    ui.label(RichText::new("Color space").small().color(MUTED));
                    let shown = effective_settings(&self.export_pane.settings, origin);
                    egui::ComboBox::from_id_salt("export-gamut")
                        .width(ui.available_width())
                        .selected_text(format!("{}{}", if shown.hdr { "HDR " } else { "" }, shown.color_space.label()))
                        .show_ui(ui, |ui| {
                            for space in [OutputColorSpace::Srgb, OutputColorSpace::DisplayP3, OutputColorSpace::Rec2020] {
                                ui.selectable_value(&mut self.export_pane.settings.color_space, space,
                                    format!("{}{}", if shown.hdr { "HDR " } else { "" }, space.label()));
                            }
                        });
                    ui.add_space(10.0);
                    let current = effective_settings(&self.export_pane.settings, origin);
                    information_row(ui, "Precision", match current.format {
                        ExportFormat::Avif => "10-bit · full color (4:4:4)",
                        ExportFormat::Jpeg => "8-bit",
                        _ => "16-bit · lossless",
                    });
                    information_row(ui, "Color tagging", if current.hdr { "PQ · embedded CICP" }
                        else if current.format == ExportFormat::Avif { "Embedded CICP" }
                        else { "Embedded ICC profile" });
                    if matches!(current.format, ExportFormat::Avif | ExportFormat::Jpeg) {
                        information_row(ui, "Quality", &format!("{} / 100", current.quality));
                    }
                });
                let current = effective_settings(&self.export_pane.settings, origin);
                if current.hdr && editing::controls::section(ui, "export-luminance", "HDR luminance", false) {
                    egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                        let before = self.editor.recipe.clone();
                        editing::controls::adjustment_scope(ui, self.editor.path.as_deref(), None, |ui| {
                            editing::hdr_luminance_controls(ui, &mut self.editor.recipe.hdr);
                        });
                        if before != self.editor.recipe {
                            self.editor.begin_edit(before, ui.input(|i| i.time));
                        }
                        theme::caption(ui, "Shared with the HDR photograph preview.");
                    });
                }
                if matches!(current.format, ExportFormat::Avif | ExportFormat::Jpeg)
                    && editing::controls::section(ui, "export-encoding", "Encoding options", false) {
                    egui::Frame::NONE.inner_margin(12).show(ui, |ui| {
                        let mut quality = f32::from(self.export_pane.settings.quality);
                        if editing::controls::slider(ui, "Quality", &mut quality, 1.0..=100.0, 100.0, 0, "").changed() {
                            self.export_pane.settings.quality = quality.round() as u8;
                        }
                        theme::caption(ui, "100 is the highest codec quality; AVIF and JPEG remain lossy.");
                        if current.format == ExportFormat::Avif {
                            let mut effort = f32::from(10 - self.export_pane.settings.speed);
                            if editing::controls::slider(ui, "Encoder effort", &mut effort, 0.0..=10.0,
                                f32::from(10 - ExportSettings::default().speed), 0, "").changed() {
                                self.export_pane.settings.speed = 10 - effort.round() as u8;
                            }
                            theme::caption(ui, "Less effort finishes faster. More effort searches longer and can improve compression or quality.");
                        }
                    });
                }
            });
    }
}
