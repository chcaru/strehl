//! The developed photograph and its sampled diagnostics share a certified UV
//! domain. A single aperture drives the photo, maps, lenses and overview.
use crate::{
    process_navigator::DetailNavigator,
    process_participation::SelectionSpan,
    process_provenance::{AdmissionArchive, AdmissionMeta},
    process_sample_glyphs::{self as sample_glyphs, SampleGeometry, SampleGlyph},
    theme,
};
use eframe::egui::{self, Color32, Pos2, Rect, Sense, Stroke, TextureHandle, Ui, Vec2};
#[path = "process-overlay-mesh.rs"]
mod overlay_mesh;
use overlay_mesh::Mode as OverlayMode;

#[derive(Default)]
pub(crate) struct ResultPhoto {
    diagnostics_suppressed: bool,
    navigator: DetailNavigator,
    drag: Option<Pos2>,
    region: Option<(Pos2, Pos2)>,
    cancelled_press: bool,
    mask_key: Option<MaskKey>,
    samples: Vec<ColoredSample>,
    sample_revision: Option<(u64, Option<[usize; 2]>, OverlayMode)>,
    overlay: overlay_mesh::Overlay,
    requested_level: Option<usize>,
    legend_bands: Vec<(usize, AdmissionMeta)>,
    balance: crate::process_balance::ObservationBalance,
    probe: crate::process_region_probe::RegionProbe,
    probe_count: usize,
    probe_region: Option<Rect>,
    probe_image: Option<Rect>,
    probe_overview: Option<Rect>,
    probe_aperture: Option<Rect>,
    probe_analysis: Option<[usize; 2]>,
    dense_region: Option<std::sync::Arc<crate::process_admission_regions::DenseRegion>>,
    dense_painter: crate::process_admission_regions::DenseRegionPainter,
    dense_selection: Option<std::sync::Arc<crate::process_admission_regions::DenseSelection>>,
    selection_painter: crate::process_admission_regions::DenseSelectionPainter,
}

#[derive(Default)]
pub(crate) struct Action {
    pub view: Option<(Pos2, f32)>,
    pub zoom: Option<(f32, Pos2)>,
    pub focus: Option<Pos2>,
    pub region: Option<Rect>,
    pub reset: bool,
}

pub(crate) struct Context<'a> {
    pub texture: &'a TextureHandle,
    pub extent: Vec2,
    pub aperture: Rect,
    pub pin: Pos2,
    pub archive: &'a AdmissionArchive,
    pub level: usize,
    pub frame: Option<usize>,
    pub spans: &'a [SelectionSpan],
    pub linked_hover: bool,
}

impl ResultPhoto {
    pub(crate) fn suppress_diagnostics(&mut self, suppressed: bool) {
        self.diagnostics_suppressed = suppressed;
        if suppressed {
            self.probe_region = None;
        }
    }
    pub(crate) fn admission_visible(ctx: &egui::Context) -> bool {
        OverlayMode::read(ctx) != OverlayMode::Clean
    }
    pub(crate) fn configure_dense_region(
        &mut self,
        region: Option<std::sync::Arc<crate::process_admission_regions::DenseRegion>>,
    ) {
        self.dense_region = region;
        self.dense_selection = None;
    }
    pub(crate) fn configure_dense_selection(
        &mut self,
        selection: Option<std::sync::Arc<crate::process_admission_regions::DenseSelection>>,
    ) {
        self.dense_selection = selection;
        self.dense_region = None;
    }
    pub(crate) fn configure_probe(
        &mut self,
        frame_count: usize,
        analysis: Option<[usize; 2]>,
        fallback: Option<(crate::pipeline::DiagnosticSurface, [usize; 2])>,
    ) {
        self.probe_count = frame_count;
        self.probe_analysis = analysis;
        self.probe.set_fallback(fallback);
        if frame_count == 0 {
            self.probe_region = None;
        }
    }
    pub(crate) fn hover_region(&self, ui: &Ui, aperture: Rect) -> Option<Rect> {
        let allowed = ui.is_enabled()
            && !self.diagnostics_suppressed
            && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
            && !egui::Popup::is_any_open(ui.ctx())
            && self.probe_count > 0
            && self.probe_analysis.is_some()
            && self.probe_aperture == Some(aperture)
            && ui.input(|state| {
                state.focused
                    && state.viewport().focused != Some(false)
                    && state.viewport().minimized != Some(true)
                    && !state.pointer.any_down()
                    && !state.key_down(egui::Key::Space)
                    && state.raw_scroll_delta == Vec2::ZERO
                    && state.pointer.hover_pos().is_some_and(|at| {
                        self.probe_image.is_some_and(|image| image.contains(at))
                            && !self
                                .probe_overview
                                .is_some_and(|view| view.expand(3.0).contains(at))
                    })
            });
        allowed
            .then(|| self.probe.current_region(ui, self.probe_image?, aperture))
            .flatten()
    }
    pub(crate) fn clear_lenses(&mut self) {
        self.balance.set_enabled(false);
        self.probe_region = None;
    }
    pub(crate) fn take_requested_level(&mut self) -> Option<usize> {
        self.requested_level.take()
    }
    pub(crate) fn update_balance(
        &mut self,
        ctx: &egui::Context,
        output: Option<&std::path::Path>,
        expected: Option<[usize; 2]>,
    ) {
        self.balance.update(ctx, output, expected);
    }
    pub(crate) fn invalidate_balance(&mut self) {
        self.balance.invalidate();
    }
    pub(crate) fn cancel_gesture(&mut self) {
        self.cancelled_press |= self.drag.is_some() || self.region.is_some();
        self.drag = None;
        self.region = None;
        self.navigator.clear();
        self.probe_region = None;
    }
    pub(crate) fn show(&mut self, ui: &mut Ui, rect: Rect, input: Context<'_>) -> Action {
        let mut action = Action::default();
        let allowed = ui.is_enabled()
            && ui.input(|state| {
                state.focused
                    && state.viewport().focused != Some(false)
                    && state.viewport().minimized != Some(true)
            })
            && ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()));
        let peek = allowed && ui.input(|state| state.key_down(egui::Key::Space));
        // Regional reconstruction changes admission provenance. Confidence is
        // recomputed against the repaired result, so it remains valid here.
        let hide_admission = peek || self.diagnostics_suppressed;
        if allowed
            && !egui::Popup::is_any_open(ui.ctx())
            && ui.input(|state| state.key_pressed(egui::Key::Escape))
        {
            self.cancelled_press |= ui.input(|state| state.pointer.primary_down());
            self.cancel_gesture();
        }
        let image = fit(input.extent, rect);
        let painter = ui.painter_at(rect);
        painter.image(input.texture.id(), image, input.aperture, Color32::WHITE);
        let show_samples = self.dense_selection.is_none() || self.range_samples_visible(ui.ctx());
        if show_samples && !hide_admission {
            self.sync_samples(ui.ctx(), &input);
        }
        if !peek {
            self.balance
                .paint(&painter, image, input.aperture, input.pin);
        }
        if !hide_admission {
            if OverlayMode::read(ui.ctx()) != OverlayMode::Clean {
                if let Some(selection) = &self.dense_selection {
                    self.selection_painter
                        .paint(&painter, selection, image, input.aperture);
                } else if let Some(region) = &self.dense_region {
                    self.dense_painter.paint(
                        &painter,
                        region,
                        image,
                        input.aperture,
                        sample_glyphs::level_color(input.level),
                    );
                }
            }
            // A range's coherent footprint is the primary comparison. Dense
            // sample marks can otherwise completely obscure its fill and the
            // shared-region stripes, especially when the photograph is fit.
            if show_samples {
                self.paint_samples(&painter, image, &input);
            }
        }
        let overview = (input.aperture.width() < 0.995 && !peek).then(|| {
            let size = Vec2::new(112.0, 78.0).min(image.size() * 0.34);
            fit(
                input.extent,
                Rect::from_min_size(image.max - size - Vec2::splat(9.0), size),
            )
        });
        let hit = ui.interact(image, ui.id().with("result-photo"), Sense::click_and_drag());
        hit.context_menu(|ui| {
            ui.label("Photograph overlay");
            if self.diagnostics_suppressed {
                ui.label("Regional repairs changed the admitted detail.");
                ui.label("Original admission evidence remains in the matrix.");
            }
            ui.add_enabled_ui(!self.diagnostics_suppressed, |ui| {
                let mut mode = OverlayMode::read(ui.ctx());
                for (value, label) in [
                    (OverlayMode::Detail, "Selected detail size"),
                    (OverlayMode::Scales, "All detail sizes"),
                    (OverlayMode::Clean, "Hide admission marks"),
                ] {
                    if ui.selectable_value(&mut mode, value, label).changed() {
                        mode.write(ui.ctx());
                    }
                }
                ui.separator();
                dense_region_controls(ui);
                self.selection_summary(ui);
                if let Some(region) = &self.dense_region {
                    ui.label(format!(
                        "{} regions · {}/{} recorded samples admitted",
                        region.islands, region.admitted, region.observed
                    ));
                }
            });
            ui.separator();
            if self.balance.ready() {
                let mut enabled = self.balance.enabled();
                if ui.checkbox(&mut enabled, "Observation balance").changed() {
                    self.balance.set_enabled(enabled);
                }
            }
            if ui.button("Fit photograph and linked details").clicked() {
                action.reset = true;
                ui.close();
            }
            ui.separator();
            ui.label("Click: focus · drag at fit: select a region");
            ui.label("Wheel: zoom · zoomed drag: pan · Shift-drag: select");
            ui.label("Ctrl+wheel: resize the regional contribution lens");
            ui.label("Double-click: fit · Space: clean photograph");
        });
        let reset_gesture = crate::image_gesture::reset(ui, &hit);
        if reset_gesture.reset {
            action.reset = true;
            self.cancel_gesture();
        }
        let pointer = ui.input(|state| state.pointer.interact_pos());
        let over_overview =
            overview.is_some_and(|view| pointer.is_some_and(|at| view.expand(3.0).contains(at)));
        let resized_probe = allowed
            && !hide_admission
            && !over_overview
            && self.probe_count > 0
            && self.probe_analysis.is_some()
            && !reset_gesture.pending
            && !action.reset
            && self.probe.resize(ui, image);
        if !allowed {
            self.cancel_gesture();
        }
        // A photograph grab owns the pointer until release, including while
        // crossing the inset. Otherwise crossing it stores a dead-zone delta.
        if allowed
            && !action.reset
            && !self.cancelled_press
            && (!over_overview || self.drag.is_some() || self.region.is_some())
        {
            if hit.is_pointer_button_down_on() && ui.input(|state| state.pointer.primary_pressed())
            {
                if input.aperture.width() >= 0.995 || ui.input(|s| s.modifiers.shift) {
                    self.region = pointer.map(|at| (at, at));
                    self.drag = None;
                } else {
                    self.drag = pointer;
                    self.region = None;
                }
            }
            if let Some((origin, _)) = self.region {
                if !reset_gesture.pending
                    && let Some(at) = pointer
                {
                    self.region = Some((origin, at.clamp(image.min, image.max)));
                }
                ui.ctx().set_cursor_icon(egui::CursorIcon::Crosshair);
            } else if hit.dragged()
                && !reset_gesture.pending
                && let (Some(previous), Some(at)) = (self.drag, pointer)
            {
                if at != previous {
                    let half = input.aperture.size() * 0.5;
                    let center = (input.aperture.center()
                        - (at - previous) / image.size() * input.aperture.size())
                    .clamp(Pos2::ZERO + half, egui::pos2(1.0, 1.0) - half);
                    action.view = Some((center, input.aperture.width().recip()));
                    self.drag = Some(at);
                }
                ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
            } else if hit.hovered() {
                ui.ctx().set_cursor_icon(
                    if input.aperture.width() >= 0.995 || ui.input(|s| s.modifiers.shift) {
                        egui::CursorIcon::Crosshair
                    } else {
                        egui::CursorIcon::Grab
                    },
                );
            }
            if hit.clicked()
                && !reset_gesture.pending
                && let Some(at) = pointer
            {
                let uv = ((at - image.min) / image.size()).clamp(Vec2::ZERO, Vec2::splat(1.0));
                action.focus = Some(input.aperture.min + uv * input.aperture.size());
            }
            if hit.hovered() && self.region.is_none() && !reset_gesture.pending && !resized_probe {
                let wheel = ui.input(|state| state.raw_scroll_delta.y);
                let pinch = crate::process_region_probe::zoom_delta(ui);
                let factor = if (pinch - 1.0).abs() > f32::EPSILON {
                    pinch
                } else {
                    (wheel * 0.004).exp()
                };
                if factor.is_finite()
                    && (factor - 1.0).abs() > f32::EPSILON
                    && let Some(at) = pointer
                {
                    action.zoom = Some((
                        factor,
                        Pos2::ZERO
                            + ((at - image.min) / image.size()).clamp(Vec2::ZERO, Vec2::splat(1.0)),
                    ));
                }
            }
        }
        if !peek
            && self.probe_count == 0
            && hit.hovered()
            && input.aperture.width() >= 0.995
            && self.region.is_none()
            && !ui.input(|s| s.pointer.any_down())
            && let Some(at) = pointer
        {
            let half = image.size() * 0.125;
            let center = at.clamp(image.min + half, image.max - half);
            let focus = Rect::from_center_size(center, half * 2.0);
            let stroke = Stroke::new(0.7_f32, theme::ACCENT.gamma_multiply(0.55));
            for (corner, dir) in [
                (focus.left_top(), Vec2::splat(1.0)),
                (focus.right_top(), egui::vec2(-1.0, 1.0)),
                (focus.right_bottom(), Vec2::splat(-1.0)),
                (focus.left_bottom(), egui::vec2(1.0, -1.0)),
            ] {
                painter.line_segment([corner, corner + egui::vec2(dir.x * 8.0, 0.0)], stroke);
                painter.line_segment([corner, corner + egui::vec2(0.0, dir.y * 8.0)], stroke);
            }
        }
        if !action.reset
            && !reset_gesture.pending
            && let Some((start, end)) = self.region
        {
            let selected = Rect::from_two_pos(start, end).intersect(image);
            if selected.width() >= 4.0 && selected.height() >= 4.0 {
                let selection_painter = painter.with_clip_rect(image);
                selection_painter.rect_filled(selected, 0.0, theme::ACCENT.gamma_multiply(0.09));
                selection_painter.rect_stroke(
                    selected,
                    0.0,
                    Stroke::new(1.0 / ui.ctx().pixels_per_point(), theme::ACCENT),
                    egui::StrokeKind::Inside,
                );
                if hit.drag_stopped() {
                    let uv = |at: Pos2| {
                        input.aperture.min
                            + ((at - image.min) / image.size()) * input.aperture.size()
                    };
                    action.region = Some(Rect::from_min_max(uv(selected.min), uv(selected.max)));
                    action.focus = None;
                }
            }
        }
        if let Some(overview) = overview {
            painter.rect_filled(overview.expand(4.0), 0.0, theme::BG);
            painter.image(input.texture.id(), overview, full(), Color32::WHITE);
            painter.rect_stroke(
                overview,
                0.0,
                Stroke::new(0.7_f32, theme::LINE),
                egui::StrokeKind::Inside,
            );
            let locator_hit = ui.interact(
                overview.expand(3.0),
                ui.id().with("result-overview"),
                Sense::click_and_drag(),
            );
            let navigation =
                self.navigator
                    .interact(ui, &locator_hit, overview, overview, input.aperture, true);
            self.navigator.paint(
                &painter.with_clip_rect(overview),
                overview,
                input.aperture,
                input.pin,
                input.linked_hover,
            );
            if self.cancelled_press {
                self.navigator.clear();
            } else if allowed && navigation.reset {
                action.reset = true;
            } else if let Some(view) = navigation.view {
                action.view = Some(view);
            } else if allowed
                && locator_hit.clicked()
                && !navigation.owns_click
                && let Some(at) = pointer
            {
                action.view = Some((
                    Pos2::ZERO
                        + ((at - overview.min) / overview.size())
                            .clamp(Vec2::ZERO, Vec2::splat(1.0)),
                    input.aperture.width().recip(),
                ));
            }
            if !self.cancelled_press
                && let Some(zoom) = navigation.zoom
            {
                action.zoom = Some(zoom);
            }
        } else {
            self.navigator.clear();
        }
        if !ui.input(|state| state.pointer.primary_down()) {
            self.drag = None;
            self.region = None;
            self.cancelled_press = false;
        }
        self.probe_image = Some(image);
        self.probe_overview = overview;
        self.probe_aperture = Some(input.aperture);
        let probe_pin = ui
            .input(|state| state.pointer.hover_pos())
            .filter(|at| image.contains(*at))
            .map(|at| input.aperture.min + (at - image.min) / image.size() * input.aperture.size());
        self.probe
            .set_balance(probe_pin.and_then(|pin| self.balance.reading_at(pin)));
        self.probe.set_source_frame(input.frame);
        self.probe.set_texture(input.texture.id());
        let previous_probe = self.probe_region;
        self.probe_region = if allowed
            && !hide_admission
            && !over_overview
            && !reset_gesture.pending
            && self.probe_count > 0
            && let Some(analysis) = self.probe_analysis
        {
            self.probe.show(
                ui,
                image,
                input.aperture,
                input.archive,
                input.level,
                analysis,
                [input.extent.x as usize, input.extent.y as usize],
                self.probe_count,
            )
        } else {
            None
        };
        if self.probe_region != previous_probe {
            ui.ctx().request_repaint();
        }
        if action.reset {
            self.cancel_gesture();
            action = Action {
                reset: true,
                ..Default::default()
            };
        }
        if action.reset
            || action.view.is_some()
            || action.zoom.is_some()
            || action.focus.is_some()
            || action.region.is_some()
        {
            ui.ctx().request_repaint();
        }
        action
    }

    fn sync_samples(&mut self, ctx: &egui::Context, input: &Context<'_>) {
        let mode = OverlayMode::read(ctx);
        let spans = effective_spans(input.spans, input.frame);
        let revision = (input.archive.revision(), self.probe_analysis, mode);
        if self.sample_revision == Some(revision)
            && self
                .mask_key
                .as_ref()
                .is_some_and(|key| key.level == input.level && key.spans == spans)
        {
            return;
        }
        let mut evidence = Vec::new();
        self.legend_bands = input
            .archive
            .levels()
            .take(16)
            .filter_map(|level| {
                let frame = input.archive.frames(level).next()?;
                let meta = input.archive.metadata(level, frame)?;
                (!self
                    .probe_analysis
                    .is_some_and(|extent| meta.extent != extent))
                .then_some((level, meta))
            })
            .collect();
        for level in input.archive.levels().take(16).filter(|level| {
            mode == OverlayMode::Scales || mode == OverlayMode::Detail && *level == input.level
        }) {
            for frame in input
                .archive
                .frames(level)
                .filter(|&frame| spans.iter().any(|span| span.contains(frame)))
            {
                if let Some(meta) = input.archive.metadata(level, frame) {
                    if self
                        .probe_analysis
                        .is_some_and(|extent| meta.extent != extent)
                    {
                        continue;
                    }
                    evidence.push((level, frame, meta));
                }
            }
        }
        let key = MaskKey {
            level: input.level,
            spans,
            evidence,
        };
        self.sample_revision = Some(revision);
        if self.mask_key.as_ref() == Some(&key) {
            return;
        }
        self.samples = admission_samples(input.archive, &key);
        self.overlay.invalidate();
        self.mask_key = Some(key);
    }

    fn paint_samples(&mut self, painter: &egui::Painter, image: Rect, input: &Context<'_>) {
        self.overlay.paint(painter, image, input, &self.samples);
    }

    fn selection_summary(&self, ui: &mut Ui) {
        let Some(selection) = &self.dense_selection else {
            return;
        };
        let mut samples = self.range_samples_visible(ui.ctx());
        if ui
            .checkbox(&mut samples, "Sample marks over range regions")
            .changed()
        {
            ui.ctx().data_mut(|data| {
                data.insert_temp(egui::Id::new("range-region-sample-marks"), samples)
            });
            ui.ctx().request_repaint();
        }
        ui.label("Pinned ranges + current capture · stripes mark shared regions");
        for layer in &selection.layers {
            ui.colored_label(
                layer.span.color(),
                format!(
                    "{} · {} regions · {}/{} captures recorded",
                    layer.label(),
                    layer.region.islands,
                    layer.recorded_frames,
                    layer.requested_frames,
                ),
            );
        }
    }

    fn range_samples_visible(&self, ctx: &egui::Context) -> bool {
        ctx.data(|data| data.get_temp(egui::Id::new("range-region-sample-marks")))
            .unwrap_or(false)
    }

    /// A quiet strip outside the photograph. The controls affect all measured
    /// overlay panes, and never alter the data or the finished photograph.
    pub(crate) fn legend(&mut self, ui: &mut Ui, rect: Rect, extent: Vec2) {
        let key = self.mask_key.as_ref();
        if rect.width() < 180.0 {
            return;
        }
        let p = ui.painter_at(rect);
        p.rect_filled(rect, 0.0, theme::BG);
        if self.diagnostics_suppressed || key.is_none() && self.dense_selection.is_none() {
            let balance_width = rect.width().min(280.0);
            if self.diagnostics_suppressed && rect.width() > balance_width + 220.0 {
                p.text(
                    rect.left_center(),
                    egui::Align2::LEFT_CENTER,
                    "Regional repairs applied · original admission in matrix",
                    egui::FontId::proportional(9.0),
                    theme::MUTED,
                );
            }
            self.balance.control(
                ui,
                Rect::from_min_max(
                    egui::pos2(rect.right() - balance_width, rect.top()),
                    rect.max,
                ),
            );
            return;
        }
        let mode_rect = Rect::from_min_size(rect.min, egui::vec2(60.0, rect.height()));
        ui.scope_builder(egui::UiBuilder::new().max_rect(mode_rect), |ui| {
            ui.set_clip_rect(mode_rect);
            ui.style_mut().override_font_id = Some(egui::FontId::proportional(9.0));
            let mut mode = OverlayMode::read(ui.ctx());
            ui.menu_button("Overlay", |ui| {
                ui.label("Marks show admitted samples, not blend percentages.");
                for (value, label) in [
                    (OverlayMode::Detail, "Selected detail size"),
                    (OverlayMode::Scales, "All detail sizes"),
                    (OverlayMode::Clean, "Hide admission marks"),
                ] {
                    if ui.selectable_value(&mut mode, value, label).changed() {
                        mode.write(ui.ctx());
                        ui.close();
                    }
                }
                ui.separator();
                dense_region_controls(ui);
                self.selection_summary(ui);
                if let Some(region) = &self.dense_region {
                    ui.label(format!(
                        "{} regions · {}/{} recorded samples admitted",
                        region.islands, region.admitted, region.observed
                    ));
                }
            });
        });
        if rect.width() < 270.0 {
            self.balance.control(
                ui,
                Rect::from_min_max(egui::pos2(mode_rect.right() + 3.0, rect.top()), rect.max),
            );
            return;
        }
        let y = rect.center().y;
        let density = sample_glyphs::Density::read(ui.ctx());
        let controls = Rect::from_min_max(egui::pos2(rect.right() - 106.0, rect.top()), rect.max);
        p.text(
            controls.left_center(),
            egui::Align2::LEFT_CENTER,
            "Density",
            egui::FontId::proportional(8.0),
            theme::MUTED,
        );
        for (index, (value, name)) in [
            (sample_glyphs::Density::Quiet, "Quiet"),
            (sample_glyphs::Density::Balanced, "Balanced"),
            (sample_glyphs::Density::Full, "All recorded samples"),
        ]
        .into_iter()
        .enumerate()
        {
            let button = Rect::from_min_size(
                egui::pos2(controls.left() + 46.0 + index as f32 * 20.0, rect.top()),
                egui::vec2(20.0, rect.height()),
            );
            let hit = ui.interact(
                button,
                ui.id().with(("overlay-density", index)),
                Sense::click(),
            );
            for bar in 0..=index {
                let x = button.center().x + (bar as f32 - index as f32 * 0.5) * 4.0;
                p.line_segment(
                    [egui::pos2(x, y + 4.0), egui::pos2(x, y - 3.0 - bar as f32)],
                    Stroke::new(
                        1.2_f32,
                        if value == density {
                            theme::ACCENT
                        } else if hit.hovered() {
                            theme::INK
                        } else {
                            theme::MUTED
                        },
                    ),
                );
            }
            if hit.clicked() {
                value.write(ui.ctx());
            }
            hit.on_hover_text(format!("{name} · affects photograph and matrix overlays. Marks are actual retained measurements, not filled ownership pixels. New stacks record up to 128 × 96 per band; existing runs keep their recorded resolution."));
        }
        let bands = &self.legend_bands;
        let balance_width = (rect.width() - 240.0).clamp(90.0, 158.0);
        if balance_width > 0.0 {
            let balance_rect = Rect::from_min_max(
                egui::pos2(controls.left() - balance_width - 5.0, rect.top()),
                egui::pos2(controls.left() - 5.0, rect.bottom()),
            );
            self.balance.control(ui, balance_rect);
        }
        let band_left = mode_rect.right() + 3.0;
        let available = (controls.left() - balance_width - band_left - 10.0).max(0.0);
        if available < 12.0 {
            return;
        }
        let width = (available / bands.len().max(1) as f32).min(50.0);
        let key_painter = p.with_clip_rect(Rect::from_min_max(
            egui::pos2(band_left, rect.top()),
            egui::pos2(controls.left() - balance_width - 9.0, rect.bottom()),
        ));
        if let Some(selection) = &self.dense_selection {
            let width = available / selection.layers.len().max(1) as f32;
            for (index, layer) in selection.layers.iter().enumerate() {
                let cell = Rect::from_min_size(
                    egui::pos2(band_left + index as f32 * width, rect.top()),
                    egui::vec2(width, rect.height()),
                );
                let paint = key_painter.with_clip_rect(cell.intersect(key_painter.clip_rect()));
                let color = layer.span.color();
                paint.line_segment(
                    [
                        cell.left_center() + egui::vec2(1.0, -4.0),
                        cell.left_center() + egui::vec2(1.0, 4.0),
                    ],
                    Stroke::new(2.0_f32, color),
                );
                let label =
                    paint.layout_no_wrap(layer.label(), egui::FontId::monospace(8.0), color);
                if label.size().x + 8.0 <= width {
                    paint.galley(
                        cell.left_center() + egui::vec2(6.0, -label.size().y * 0.5),
                        label,
                        color,
                    );
                }
                ui.interact(cell, ui.id().with(("range-region-key", layer.span.id, layer.span.start, layer.span.end)), Sense::hover())
                    .on_hover_text(if layer.is_current() {
                        format!("{} · current capture's estimated admitted region\nThe quiet outline follows the displayed capture. Mixed stripes mark intersections with pinned ranges; the pins stay unchanged.", layer.label())
                    } else {
                        format!("Captures {} · {}/{} recorded\nThis colour marks the pinned range's estimated admitted region. Mixed stripes mark intersections with other pins or the current capture.", layer.span.label(), layer.recorded_frames, layer.requested_frames)
                    });
            }
            return;
        }
        for (index, (level, meta)) in bands.iter().enumerate() {
            if width < 1.0 {
                break;
            }
            let x = band_left + index as f32 * width;
            let cell =
                Rect::from_min_size(egui::pos2(x, rect.top()), egui::vec2(width, rect.height()));
            let cell_painter = key_painter.with_clip_rect(cell.intersect(key_painter.clip_rect()));
            let color = sample_glyphs::level_color(*level);
            let spacing = SampleGeometry::new(*level, *meta)
                .map_or(1usize << level, |geometry| geometry.spacing());
            let physical = (spacing as f32 * extent.x / meta.extent[0] as f32).max(1.0);
            if width >= 6.0 {
                cell_painter.line_segment(
                    [egui::pos2(x + 1.0, y - 4.0), egui::pos2(x + 5.0, y - 4.0)],
                    Stroke::new(1.0_f32, color),
                );
            }
            cell_painter.line_segment(
                [
                    egui::pos2(x + width.min(2.0) * 0.5, y - 4.0),
                    egui::pos2(x + width.min(2.0) * 0.5, y),
                ],
                Stroke::new(1.0_f32, color),
            );
            let label = format!("{physical:.0}");
            let galley = cell_painter.layout_no_wrap(label, egui::FontId::monospace(8.0), color);
            if galley.size().x + 10.0 <= width {
                cell_painter.galley(
                    egui::pos2(x + 8.0, y - galley.size().y * 0.5),
                    galley,
                    color,
                );
            }
            if key.is_some_and(|key| *level == key.level) {
                cell_painter.line_segment(
                    [
                        egui::pos2(x, y + 7.0),
                        egui::pos2(x + (width - 5.0).max(1.0), y + 7.0),
                    ],
                    Stroke::new(0.7_f32, theme::INK),
                );
            }
            let hit = ui.interact(
                Rect::from_min_size(egui::pos2(x, rect.top()), egui::vec2(width, rect.height())),
                ui.id().with(("overlay-scale-key", level)),
                Sense::click(),
            );
            if hit.clicked() {
                self.requested_level = Some(*level);
                OverlayMode::Detail.write(ui.ctx());
            }
            hit.on_hover_text(format!("{physical:.0}px in the photograph = {spacing}px in the analysis grid · {} × {} recorded observations. This is coefficient spacing, not feature width. Marks show where this capture passed the detail gate, not how much it supplied. Click to link this size across the photograph, timeline and matrix.", meta.samples[0], meta.samples[1]));
        }
    }
}

fn dense_region_controls(ui: &mut Ui) {
    use crate::process_admission_regions::RegionSettings;
    let mut settings = RegionSettings::read(ui.ctx());
    let before = settings;
    ui.checkbox(&mut settings.enabled, "Estimated admission regions");
    ui.add_enabled_ui(settings.enabled, |ui| {
        ui.add(
            egui::Slider::new(&mut settings.threshold, 35..=85)
                .text("Density cutoff")
                .suffix("%"),
        );
    });
    ui.label("Shading estimates dense regions between recorded samples.");
    ui.label("Higher cutoff keeps denser regions; dots remain measured.");
    ui.label("An admission boundary is not a sharpness boundary.");
    if settings != before {
        settings.write(ui.ctx());
    }
}

#[derive(PartialEq, Eq)]
struct MaskKey {
    level: usize,
    spans: Vec<SelectionSpan>,
    evidence: Vec<(usize, usize, AdmissionMeta)>,
}

struct ColoredSample {
    level: usize,
    #[cfg(test)]
    spacing: usize,
    glyph: SampleGlyph,
    colors: SampleColors,
}

// Eight selection colours plus the transient white source trace. Keeping
// these inline avoids one allocation per admitted pixel while scrubbing.
#[derive(Clone, Debug)]
struct SampleColors {
    values: [Color32; 9],
    len: usize,
}
impl Default for SampleColors {
    fn default() -> Self {
        Self {
            values: [Color32::TRANSPARENT; 9],
            len: 0,
        }
    }
}
impl std::ops::Deref for SampleColors {
    type Target = [Color32];
    fn deref(&self) -> &Self::Target {
        &self.values[..self.len]
    }
}
impl SampleColors {
    fn push(&mut self, value: Color32) {
        if !self.contains(&value) && self.len < self.values.len() {
            self.values[self.len] = value;
            self.len += 1;
        }
    }
}
#[cfg(test)]
impl<const N: usize> PartialEq<[Color32; N]> for SampleColors {
    fn eq(&self, other: &[Color32; N]) -> bool {
        self.deref_slice() == other
    }
}
#[cfg(test)]
impl SampleColors {
    fn deref_slice(&self) -> &[Color32] {
        &self.values[..self.len]
    }
}

fn effective_spans(spans: &[SelectionSpan], frame: Option<usize>) -> Vec<SelectionSpan> {
    let multiple = spans.len() > 1 || spans.iter().any(|span| span.len() > 1);
    if !multiple {
        return frame
            .map(|frame| {
                vec![SelectionSpan {
                    start: frame,
                    end: frame,
                    id: spans
                        .iter()
                        .find(|span| span.contains(frame))
                        .map_or(0, |span| span.id),
                }]
            })
            .unwrap_or_default();
    }
    let mut spans = spans.to_vec();
    // Current capture is a separate role even inside a pinned interval, just
    // like its dense footprint. Adding it never changes the saved groups.
    if let Some(frame) = frame {
        spans.push(SelectionSpan {
            start: frame,
            end: frame,
            id: usize::MAX,
        });
    }
    spans
}

/// Union only at matching observed sample locations. Missing samples and
/// observed negatives remain unpainted; no interpolation invents ownership.
fn admission_samples(archive: &AdmissionArchive, key: &MaskKey) -> Vec<ColoredSample> {
    let mut result = Vec::new();
    for level in 0..16 {
        let Some((_, _, meta)) = key.evidence.iter().find(|(band, _, _)| *band == level) else {
            continue;
        };
        let Some(geometry) = SampleGeometry::new(level, *meta) else {
            continue;
        };
        let mut colors = vec![SampleColors::default(); meta.samples[0] * meta.samples[1]];
        for span in &key.spans {
            for &(band, frame, frame_meta) in &key.evidence {
                if band != level
                    || !span.contains(frame)
                    || frame_meta.samples != meta.samples
                    || frame_meta.extent != meta.extent
                {
                    continue;
                }
                if let Some((_, values)) = archive.cells(level, frame) {
                    for (cell, admitted) in values.enumerate() {
                        if admitted && !colors[cell].contains(&span.color()) {
                            colors[cell].push(span.color());
                        }
                    }
                }
            }
        }
        // Retain every measured location. Display thinning happens after the
        // inspection aperture is known, so zooming exposes real extra detail.
        for (cell, colors) in colors.into_iter().enumerate() {
            if colors.is_empty() {
                continue;
            }
            if let Some(glyph) = geometry.at(cell) {
                result.push(ColoredSample {
                    level,
                    #[cfg(test)]
                    spacing: geometry.spacing(),
                    glyph,
                    colors,
                });
            }
        }
    }
    result
}

#[cfg(test)]
#[path = "process-result-density-tests.rs"]
mod density_tests;
#[cfg(test)]
#[path = "process-result-region-tests.rs"]
mod region_tests;
#[cfg(test)]
#[path = "process-result-selection-tests.rs"]
mod selection_tests;
#[cfg(test)]
#[path = "process-overlay-v25-tests.rs"]
mod v25_tests;

fn fit(size: Vec2, rect: Rect) -> Rect {
    Rect::from_center_size(
        rect.center(),
        size * (rect.width() / size.x).min(rect.height() / size.y),
    )
}
fn full() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}

/// Inspect the actual retained draw output in integration tests. A marker is
/// an eight-triangle fan around a measured center, not a filled sample cell.
#[cfg(test)]
pub(crate) fn overlay_marker_centers(output: &egui::FullOutput) -> Vec<Pos2> {
    let mut points = Vec::new();
    for shape in &output.shapes {
        if let egui::Shape::Circle(circle) = &shape.shape
            && (circle.radius - 1.05).abs() < 0.01
            && circle.fill.a() > 0
            && shape.clip_rect.contains(circle.center)
        {
            points.push(circle.center);
        }
        let egui::Shape::Mesh(mesh) = &shape.shape else {
            continue;
        };
        if mesh.texture_id != egui::TextureId::default() {
            continue;
        }
        let mut uses = vec![0usize; mesh.vertices.len()];
        for &index in &mesh.indices {
            uses[index as usize] += 1;
        }
        for (vertex, uses) in mesh.vertices.iter().zip(uses) {
            if uses == 8 && vertex.color.a() > 0 && shape.clip_rect.contains(vertex.pos) {
                points.push(vertex.pos);
            }
        }
    }
    points
}
