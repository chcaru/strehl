//! Develop and Export in the Studio 2 shell (implementation plan 7.5, 7.6).
//! The shell's Develop and Export arms are one-line calls into this file; the
//! parts live in `develop-station.rs` and `export-station.rs`, their app glue
//! in `app-develop.rs`.
//!
//! The depth rail: while the depth brush is out, Develop's rail slot shows
//! `station::depth_rail` with `RangeFallback` (two plane fields). The Stack
//! station's depth rail (P3) plugs in by implementing `DepthRail` and being
//! passed to `depth_rail` in `show_develop_rail`; nothing else changes.
use super::studio_route::Station;
use super::studio_shell::{RAIL_HEAD, StationLayout};
use super::*;
use crate::{
    develop_station::{self as station, DevelopTool, style},
    studio_theme, studio_widgets as w,
};

/// The export history under the Export canvas (mockup `.exports`).
const EXPORT_HISTORY: f32 = 152.0;
/// The depth brush's rail: the head and one row of plane fields.
const DEPTH_RAIL: f32 = RAIL_HEAD + 34.0;

impl StrehlApp {
    /// Develop has the tools strip; both have the inspector and the control
    /// strip; the rail slot holds the depth rail (Develop, depth brush out)
    /// or the export history (Export).
    pub(super) fn develop_layout(&self, station: Station) -> StationLayout {
        let open = self.editor.loaded.is_some();
        StationLayout {
            sidebar: None,
            // Tools need a photograph; without one the strip starts at the edge.
            tools: station == Station::Develop && open,
            inspector: true,
            control_strip: true,
            rail: match station {
                Station::Develop => (open && self.editor.develop.tool == DevelopTool::DepthBrush)
                    .then_some(DEPTH_RAIL),
                _ => open.then_some(EXPORT_HISTORY),
            },
            owns_body: false,
        }
    }

    pub(super) fn develop_tools(&mut self, ui: &mut egui::Ui) {
        if self.editor.loaded.is_some() {
            self.show_develop_tools(ui);
        }
    }

    pub(super) fn develop_strip(&mut self, ui: &mut egui::Ui, station: Station) {
        if self.editor.loaded.is_none() {
            let t = studio_theme::tokens(ui.ctx());
            w::caps(ui, station.label());
            ui.label(
                egui::RichText::new(if self.editor.loading.is_some() {
                    "Opening the photograph…"
                } else {
                    "Nothing open"
                })
                .size(12.5)
                .color(t.ink3),
            );
            return;
        }
        match station {
            Station::Develop => self.show_develop_strip(ui),
            _ => {
                self.show_export_strip(ui);
                self.export_zoom(ui);
            }
        }
    }

    /// Export's Fit / Actual pixels, right-aligned in the strip.
    fn export_zoom(&mut self, ui: &mut egui::Ui) {
        let (Some((image, clip)), Some(loaded)) = (
            self.process_space.edit_mapping(),
            self.editor.loaded.as_ref(),
        ) else {
            return;
        };
        if !(image.is_finite() && image.is_positive() && clip.is_positive()) {
            return;
        }
        let size = [loaded.image.width as f32, loaded.image.height as f32];
        let ppp = ui.ctx().pixels_per_point();
        // Points per photograph pixel now, at 1:1 and when fitted.
        let scale = image.width() / size[0];
        let native = 1.0 / ppp;
        let fit = (clip.width() / size[0]).min(clip.height() / size[1]);
        let current = if (scale / native - 1.0).abs() < 0.02 {
            Some(1)
        } else if (scale / fit - 1.0).abs() < 0.02 {
            Some(0)
        } else {
            None
        };
        let pal = style::StudioPalette::of(ui.ctx());
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            match style::seg(ui, &pal, &["Fit", "Actual pixels"], current) {
                Some(0) => self.process_space.fit_edit_view(),
                Some(_) => {
                    let visible = image.intersect(clip);
                    let center = [
                        ((visible.center().x - image.left()) / image.width()).clamp(0.0, 1.0),
                        ((visible.center().y - image.top()) / image.height()).clamp(0.0, 1.0),
                    ];
                    self.process_space
                        .set_photo_view(center, native / fit.max(1e-6));
                }
                None => return,
            }
            ui.ctx().request_repaint();
        });
    }

    pub(super) fn develop_rail(&mut self, ui: &mut egui::Ui, station: Station) {
        match station {
            Station::Develop => self.show_develop_rail(ui),
            _ => self.show_export_history(ui),
        }
    }

    /// After the photograph is painted: on Export, what the selected preset
    /// will write (its crop and, when it burns one, the scale bar). Develop's
    /// overlays run through the editor's canvas hook.
    pub(super) fn develop_canvas_overlay(&mut self, ui: &mut egui::Ui, station: Station) {
        if station != Station::Export {
            return;
        }
        let (Some((image, clip)), Some(loaded)) = (
            self.process_space.edit_mapping(),
            self.editor.loaded.as_ref(),
        ) else {
            return;
        };
        let size = [loaded.image.width, loaded.image.height];
        let painter = ui.painter().with_clip_rect(clip);
        let palette = style::StudioPalette::of(ui.ctx());
        let recipe = &self.editor.recipe;
        let mut frame = image;
        if let Some(crop) = recipe.crop {
            station::paint_crop_outline(&painter, image, crop, size);
            frame = egui::Rect::from_min_max(
                egui::pos2(
                    image.left() + crop.min[0] * image.width(),
                    image.top() + crop.min[1] * image.height(),
                ),
                egui::pos2(
                    image.left() + crop.max[0] * image.width(),
                    image.top() + crop.max[1] * image.height(),
                ),
            );
        }
        let burns = self
            .export_preview_settings()
            .is_some_and(|settings| settings.scale_bar);
        if burns
            && let (Some(bar), Some(um)) = (
                recipe.scale_bar.filter(|b| b.enabled),
                self.editor.um_per_px,
            )
        {
            let out = recipe
                .crop
                .map_or(size, |c| c.output_size(size[0], size[1]));
            station::paint_scale_bar(&painter, frame, &bar, um, out, &palette);
        }
    }

    /// Develop: Adjust, Layers · n, Versions · n. Export has one tab.
    pub(super) fn develop_tabs(&mut self, ui: &mut egui::Ui, station: Station) {
        if station == Station::Develop
            && let Some((labels, current)) = self.develop_tab_labels()
        {
            for (tab, label) in labels {
                if w::tab(ui, &label, tab == current, None).clicked() {
                    self.edit_pane.develop.panel.tab = tab;
                }
            }
        } else {
            w::tab(ui, station.label(), true, None);
        }
    }

    pub(super) fn develop_inspector_body(&mut self, ui: &mut egui::Ui, station: Station) {
        if self.editor.loaded.is_none() {
            self.develop_empty(ui, station);
            return;
        }
        match station {
            Station::Develop => self.develop_body(ui),
            _ if self.export_pane.station.library.is_some() => self.show_export_inspector(ui),
            _ => {
                let t = studio_theme::tokens(ui.ctx());
                padded(ui, |ui| {
                    ui.label(
                        egui::RichText::new("Reading the export presets…")
                            .size(12.5)
                            .color(t.ink3),
                    );
                });
            }
        }
    }

    /// Adjust, Layers or Versions, padded and scrolling; Adjust ends with
    /// the groups that still use today's controls.
    fn develop_body(&mut self, ui: &mut egui::Ui) {
        self.edit_pane.develop.palette = style::StudioPalette::of(ui.ctx());
        let rect = ui.max_rect();
        let body = egui::Rect::from_min_max(
            egui::pos2(rect.left() + 16.0, rect.top() + 14.0),
            egui::pos2(rect.right() - 16.0, rect.bottom() - 8.0),
        );
        let mut child = ui.new_child(
            egui::UiBuilder::new()
                .max_rect(body)
                .layout(egui::Layout::top_down(egui::Align::Min)),
        );
        let intents = egui::ScrollArea::vertical()
            .id_salt("develop-inspector")
            .auto_shrink([false, false])
            .show(&mut child, |ui| {
                ui.spacing_mut().item_spacing.y = 9.0;
                self.develop_notes(ui);
                if self.edit_pane.develop.panel.tab == station::InspectorTab::Versions {
                    // Save version's name field, progress and result.
                    let pal = self.edit_pane.develop.palette;
                    self.develop_version_head(ui, &pal);
                }
                let intents = self.show_develop_tab(ui);
                match self.edit_pane.develop.panel.tab {
                    station::InspectorTab::Adjust => self.develop_more(ui),
                    station::InspectorTab::Layers => self.develop_regions_detail(ui),
                    station::InspectorTab::Versions => {}
                }
                intents
            })
            .inner;
        let time = ui.input(|i| i.time);
        self.handle_develop_intents(intents, time);
    }

    /// The station's last notice (an action that could not run, a partial
    /// white balance), the editor's error and warnings, and edits kept from
    /// another session.
    fn develop_notes(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        if let Some(notice) = self.edit_pane.develop.notice.clone() {
            let pal = self.edit_pane.develop.palette;
            if style::notice_line(ui, &pal, style::Mark::Warn, &notice, &["Dismiss"]).is_some() {
                self.edit_pane.develop.dismiss_notice();
            }
        }
        if let Some(error) = &self.editor.error {
            ui.label(egui::RichText::new(error).size(12.0).color(t.warn));
        }
        for warning in &self.editor.warnings {
            ui.label(egui::RichText::new(warning).size(12.0).color(t.ink3));
        }
        if self.editor.has_recovery() {
            legacy_inset(ui, |ui| self.editor.recovery_panel(ui));
        }
    }

    /// The look in detail (treatment, where it changes, analysis notes),
    /// saved looks (presets, XMP, reset) and the selected region's source
    /// evidence: today's panels, kept reachable inside a Graphite inset.
    fn develop_more(&mut self, ui: &mut egui::Ui) {
        let pal = self.edit_pane.develop.palette;
        let open = self.edit_pane.develop.panel.groups[5];
        if station::group_header(
            ui,
            &pal,
            "Look in detail",
            "treatment and where it acts",
            open,
        )
        .clicked()
        {
            self.edit_pane.develop.panel.groups[5] = !open;
        }
        if self.edit_pane.develop.panel.groups[5] {
            legacy_inset(ui, |ui| self.adaptive_panel(ui));
        }
        let open = self.edit_pane.develop.panel.groups[3];
        if station::group_header(ui, &pal, "Saved looks", "presets and XMP", open).clicked() {
            self.edit_pane.develop.panel.groups[3] = !open;
        }
        if self.edit_pane.develop.panel.groups[3] {
            legacy_inset(ui, |ui| {
                self.presets_panel(ui);
                ui.horizontal(|ui| {
                    if ui
                        .add_enabled(
                            self.editor.dialog.is_none(),
                            egui::Button::new("Import XMP preset…"),
                        )
                        .clicked()
                    {
                        self.editor.dialog_kind = Some("preset");
                        self.editor.dialog = Some(jobs::spawn_task("strehl-preset-picker", |_| {
                            Ok(rfd::FileDialog::new()
                                .add_filter("Camera Raw preset", &["xmp"])
                                .pick_file())
                        }));
                    }
                    let label = if self.editor.selected.is_some() {
                        "Reset this region"
                    } else {
                        "Reset adjustments"
                    };
                    if ui.button(label).clicked() {
                        let before = self.editor.recipe.clone();
                        *self.current_adjustments() = strehl_edit::Adjustments::default();
                        self.editor
                            .recipe
                            .clear_adaptive_scope(self.editor.selected.as_deref());
                        if self.editor.recipe != before {
                            self.editor.before = false;
                            self.editor.begin_edit(before, ui.input(|i| i.time));
                        }
                    }
                });
            });
        }
        if self.editor.selected.is_some() {
            let open = self.edit_pane.develop.panel.groups[4];
            if station::group_header(ui, &pal, "Source evidence", "the selected region", open)
                .clicked()
            {
                self.edit_pane.develop.panel.groups[4] = !open;
            }
            if self.edit_pane.develop.panel.groups[4] {
                legacy_inset(ui, |ui| self.region_inspector(ui));
            }
        }
    }

    /// Under Layers: today's region manager (rename, duplicate, enable,
    /// source planes, shapes), folded by default.
    fn develop_regions_detail(&mut self, ui: &mut egui::Ui) {
        let id = egui::Id::new("develop-regions-detail");
        let open = ui.ctx().data(|d| d.get_temp::<bool>(id)).unwrap_or(false);
        let pal = self.edit_pane.develop.palette;
        let summary = format!(
            "{} · rename, duplicate, source planes",
            self.editor.recipe.regions.len()
        );
        if station::group_header(ui, &pal, "Regions in detail", &summary, open).clicked() {
            ui.ctx().data_mut(|d| d.insert_temp(id, !open));
        }
        if open {
            legacy_inset(ui, |ui| self.edit_region_shelf(ui, true));
        }
    }

    /// Nothing open, opening, or a photograph that failed to open.
    fn develop_empty(&mut self, ui: &mut egui::Ui, station: Station) {
        let t = studio_theme::tokens(ui.ctx());
        padded(ui, |ui| {
            ui.spacing_mut().item_spacing.y = 9.0;
            let text = if self.editor.loading.is_some() {
                "Opening the photograph…"
            } else if station == Station::Develop {
                "Choose a completed stack to develop its photograph."
            } else {
                "Choose a completed photograph to export."
            };
            ui.label(egui::RichText::new(text).size(12.5).color(t.ink2));
            if let Some(error) = &self.editor.error {
                ui.label(egui::RichText::new(error).size(12.0).color(t.warn));
            }
            if self.editor.has_recovery() {
                legacy_inset(ui, |ui| self.editor.recovery_panel(ui));
            }
        });
    }

    pub(super) fn develop_footer(&mut self, ui: &mut egui::Ui, station: Station) {
        match station {
            Station::Develop if self.editor.loaded.is_some() => self.show_develop_footer(ui),
            Station::Develop => {
                ui.add(w::Button::primary("Export…").wide().enabled(false));
            }
            _ if self.editor.loaded.is_some() && self.export_pane.station.library.is_some() => {
                self.show_export_footer(ui)
            }
            _ => {
                ui.add(w::Button::primary("Export").wide().enabled(false));
            }
        }
    }
}

/// The inspector's 16 px inset for a short message.
fn padded(ui: &mut egui::Ui, content: impl FnOnce(&mut egui::Ui)) {
    egui::Frame::NONE
        .inner_margin(egui::Margin {
            left: 16,
            right: 16,
            top: 14,
            bottom: 8,
        })
        .show(ui, content);
}

/// Today's controls inside Develop: they paint with the Graphite constants,
/// so on a light theme they sit in a Graphite well with Graphite visuals.
fn legacy_inset<R>(ui: &mut egui::Ui, content: impl FnOnce(&mut egui::Ui) -> R) -> R {
    let light = studio_theme::tokens(ui.ctx()).light;
    ui.scope(|ui| {
        let mut frame = egui::Frame::NONE;
        if light {
            let reduced = studio_theme::reduced_motion(ui.ctx());
            ui.set_style(studio_theme::style(
                ui.ctx(),
                studio_theme::ThemeName::Graphite,
                reduced,
            ));
            frame = frame.fill(studio_theme::GRAPHITE.panel).inner_margin(8);
        }
        ui.spacing_mut().item_spacing.y = 4.0;
        frame.show(ui, content).inner
    })
    .inner
}

#[cfg(test)]
#[path = "app-station-develop-tests.rs"]
mod tests;
