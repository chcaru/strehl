//! The live view in the Capture canvas (Studio 2; mockup `capture-plan.html`):
//! the camera's JPEG preview fitted or at 100 %, focus peaking with its
//! threshold, the clipping overlay, a thirds grid, the subject box with its
//! corner marks, the camera magnifier, and the estimate panel with the
//! preview's histogram, labelled "estimate, not the RAW".
//!
//! Textures are uploaded only when the preview's generation (or the peaking
//! threshold) changes; the histogram is one cached mesh per generation.
use std::sync::Arc;

use eframe::egui::{
    self, Align2, Color32, Mesh, Rect, Sense, Shape, Stroke, StrokeKind, TextureHandle,
    TextureOptions, Ui,
};
use strehl_capture::model::Roi;

use super::style::{self, ButtonKind, CapturePalette, Mark};
use crate::capture_aids::PreviewLevels;
use crate::capture_client::Snapshot;

/// What the user asked of the live view.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum LiveIntent {
    /// A new subject box, normalised to the preview.
    SetRoi(Roi),
    /// The camera magnifier at `ratio` (0 off) centred at `x`, `y` of 639 x 479.
    Magnify { ratio: u32, x: u16, y: u16 },
}

/// The histogram's mesh, keyed by the preview's generation and rectangle.
type HistogramCache = Option<((u64, [u32; 4]), Arc<Mesh>)>;

/// The live view's switches and textures.
pub(crate) struct LiveView {
    pub actual_size: bool,
    pub peaking: bool,
    pub threshold: u8,
    pub clipping: bool,
    pub grid: bool,
    pub subject_box: bool,
    drag_from: Option<egui::Pos2>,
    preview: Option<(u64, TextureHandle)>,
    peaks: Option<(u64, u8, TextureHandle)>,
    clip: Option<(u64, TextureHandle)>,
    histogram: HistogramCache,
    /// Texture uploads (tests and performance checks).
    pub uploads: u64,
}

impl Default for LiveView {
    fn default() -> Self {
        Self {
            actual_size: false,
            peaking: true,
            threshold: 18,
            clipping: true,
            grid: false,
            subject_box: true,
            drag_from: None,
            preview: None,
            peaks: None,
            clip: None,
            histogram: None,
            uploads: 0,
        }
    }
}

/// The preview's rectangle in a canvas: its aspect, the canvas height less
/// 38 px, centred with 10 px below (the mockup's `.canvas.center > .photo`).
pub(crate) fn photo_rect(canvas: Rect, aspect: f32) -> Rect {
    let h = (canvas.height() - 38.0).max(40.0);
    let w = (h * aspect).min(canvas.width() - 24.0).max(40.0);
    let h = w / aspect;
    Rect::from_center_size(
        egui::pos2(canvas.center().x, canvas.center().y - 5.0),
        egui::vec2(w, h),
    )
}

impl LiveView {
    /// The live preview's texture, once uploaded.
    pub(crate) fn preview_handle(&self) -> Option<&TextureHandle> {
        self.preview.as_ref().map(|(_, t)| t)
    }
    /// Uploads the preview (and its overlays) when its generation changed.
    pub(crate) fn sync_textures(
        &mut self,
        ctx: &egui::Context,
        s: &Snapshot,
        palette: &CapturePalette,
    ) {
        if let Some((generation, image)) = &s.preview
            && self.preview.as_ref().is_none_or(|(g, _)| g != generation)
        {
            let image = image.as_ref().clone();
            match &mut self.preview {
                Some((g, t)) => {
                    t.set(image, TextureOptions::LINEAR);
                    *g = *generation;
                }
                None => {
                    self.preview = Some((
                        *generation,
                        ctx.load_texture("capture-live", image, TextureOptions::LINEAR),
                    ))
                }
            }
            self.uploads += 1;
        }
        if self.peaking
            && let Some((generation, peaks)) = &s.peaking
            && self
                .peaks
                .as_ref()
                .is_none_or(|(g, t, _)| g != generation || *t != self.threshold)
        {
            let image = peaks.overlay(self.threshold);
            match &mut self.peaks {
                Some((g, t, tex)) => {
                    tex.set(image, TextureOptions::NEAREST);
                    *g = *generation;
                    *t = self.threshold;
                }
                None => {
                    self.peaks = Some((
                        *generation,
                        self.threshold,
                        ctx.load_texture("capture-live-peaking", image, TextureOptions::NEAREST),
                    ))
                }
            }
            self.uploads += 1;
        }
        if self.clipping
            && let Some((generation, levels)) = &s.levels
            && self.clip.as_ref().is_none_or(|(g, _)| g != generation)
        {
            let image = levels.clip_overlay(palette.warn.gamma_multiply(0.85));
            match &mut self.clip {
                Some((g, tex)) => {
                    tex.set(image, TextureOptions::NEAREST);
                    *g = *generation;
                }
                None => {
                    self.clip = Some((
                        *generation,
                        ctx.load_texture("capture-live-clip", image, TextureOptions::NEAREST),
                    ))
                }
            }
            self.uploads += 1;
        }
    }

    /// Draws the live view into the canvas `ui` gives it.
    pub fn show(&mut self, ui: &mut Ui, s: &Snapshot, palette: &CapturePalette) -> Vec<LiveIntent> {
        let mut out = Vec::new();
        let canvas = ui.max_rect();
        ui.painter().rect_filled(canvas, 0.0, palette.surround);
        self.sync_textures(ui.ctx(), s, palette);
        let host = &s.host;
        let aspect = self
            .preview
            .as_ref()
            .map(|(_, t)| t.size_vec2())
            .filter(|v| v.y > 0.0)
            .map_or(1.5, |v| v.x / v.y);
        let photo = photo_rect(canvas, aspect);
        let p = ui.painter_at(canvas);
        p.rect_filled(photo, 0.0, Color32::BLACK);
        let roi = host.roi.unwrap_or_else(Roi::subject);
        // 100 %: one preview pixel a point, around the subject box.
        let uv = match (&self.preview, self.actual_size) {
            (Some((_, t)), true) => {
                let size = t.size_vec2();
                let w = (photo.width() / size.x).min(1.0);
                let h = (photo.height() / size.y).min(1.0);
                let cx = (roi.x + roi.width / 2.0).clamp(w / 2.0, 1.0 - w / 2.0);
                let cy = (roi.y + roi.height / 2.0).clamp(h / 2.0, 1.0 - h / 2.0);
                Rect::from_center_size(egui::pos2(cx, cy), egui::vec2(w, h))
            }
            _ => Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
        };
        let fresh = host.preview.fresh;
        if let Some((generation, t)) = &self.preview {
            p.image(t.id(), photo, uv, Color32::WHITE);
            if self.peaking
                && fresh
                && let Some((g, _, peaks)) = &self.peaks
                && g == generation
            {
                p.image(peaks.id(), photo, uv, Color32::WHITE);
            }
            if self.clipping
                && let Some((g, clip)) = &self.clip
                && g == generation
            {
                p.image(clip.id(), photo, uv, Color32::WHITE);
            }
        } else {
            style::paint_job(
                &p,
                photo.center(),
                Align2::CENTER_CENTER,
                style::job("The live view appears here", 13.0, palette.ink3, 0.0),
            );
        }
        p.rect_stroke(
            photo,
            0.0,
            Stroke::new(1.0_f32, Color32::from_white_alpha(13)),
            StrokeKind::Outside,
        );
        if self.grid {
            for i in 1..3 {
                let f = i as f32 / 3.0;
                let x = photo.left() + photo.width() * f;
                let y = photo.top() + photo.height() * f;
                p.line_segment(
                    [egui::pos2(x, photo.top()), egui::pos2(x, photo.bottom())],
                    Stroke::new(1.0_f32, Color32::from_white_alpha(40)),
                );
                p.line_segment(
                    [egui::pos2(photo.left(), y), egui::pos2(photo.right(), y)],
                    Stroke::new(1.0_f32, Color32::from_white_alpha(40)),
                );
            }
        }
        // The subject box: drawn, and redrawn by dragging on the picture.
        let response = ui.interact(
            photo,
            ui.id().with("capture-live-photo"),
            Sense::click_and_drag(),
        );
        let editable = s.fresh() && host.editable && !s.pending;
        let to_uv = |pos: egui::Pos2| {
            let fx = ((pos.x - photo.left()) / photo.width()).clamp(0.0, 1.0);
            let fy = ((pos.y - photo.top()) / photo.height()).clamp(0.0, 1.0);
            egui::pos2(uv.left() + fx * uv.width(), uv.top() + fy * uv.height())
        };
        let to_screen = |u: egui::Pos2| {
            egui::pos2(
                photo.left() + (u.x - uv.left()) / uv.width() * photo.width(),
                photo.top() + (u.y - uv.top()) / uv.height() * photo.height(),
            )
        };
        if self.subject_box && editable {
            if response.drag_started() {
                self.drag_from = ui.input(|i| i.pointer.press_origin()).map(to_uv);
            }
            if response.drag_stopped()
                && let (Some(a), Some(b)) = (
                    self.drag_from.take(),
                    response.interact_pointer_pos().map(to_uv),
                )
            {
                let r = Rect::from_two_pos(a, b);
                let roi = Roi {
                    x: r.left(),
                    y: r.top(),
                    width: r.width(),
                    height: r.height(),
                };
                if roi.width >= 0.05 && roi.height >= 0.05 && roi.valid() {
                    out.push(LiveIntent::SetRoi(roi));
                }
            }
        } else {
            self.drag_from = None;
        }
        if self.subject_box {
            let shown = match (self.drag_from, response.interact_pointer_pos()) {
                (Some(a), Some(b)) => Rect::from_two_pos(to_screen(a), b),
                _ => Rect::from_min_max(
                    to_screen(egui::pos2(roi.x, roi.y)),
                    to_screen(egui::pos2(roi.x + roi.width, roi.y + roi.height)),
                ),
            };
            subject_box(&p, shown, palette);
        }
        // The state at the top left.
        let state = match host.preview.age_seconds {
            Some(age) if fresh => format!("Live · preview {age:.1} s old"),
            Some(age) => format!("Last preview · {age:.0} s old"),
            None => "No preview".into(),
        };
        let galley = p.layout_job(style::job(&state, 11.5, palette.ink2, 0.0));
        let tag = Rect::from_min_size(
            photo.left_top() + egui::vec2(10.0, 10.0),
            egui::vec2(galley.size().x + 35.0, 26.0),
        );
        glass(&p, tag, palette);
        style::mark(
            &p,
            egui::pos2(tag.left() + 13.5, tag.center().y),
            if fresh { Mark::Ok } else { Mark::Idle },
            7.0,
            palette,
        );
        p.galley(
            egui::pos2(tag.left() + 25.0, tag.center().y - galley.size().y / 2.0),
            galley,
            palette.ink2,
        );
        self.bar(ui, photo, s, roi, palette, &mut out);
        self.estimate(ui, photo, s, palette);
        out
    }

    /// The tool bar at the bottom left (`.lvbar`).
    fn bar(
        &mut self,
        ui: &mut Ui,
        photo: Rect,
        s: &Snapshot,
        roi: Roi,
        palette: &CapturePalette,
        out: &mut Vec<LiveIntent>,
    ) {
        let at = photo.left_bottom() + egui::vec2(10.0, -10.0);
        let rect = Rect::from_min_size(egui::pos2(at.x, at.y - 34.0), egui::vec2(520.0, 34.0));
        glass(ui.painter(), rect, palette);
        ui.scope_builder(
            egui::UiBuilder::new()
                .max_rect(rect.shrink2(egui::vec2(8.0, 5.0)))
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
            |ui| {
                ui.spacing_mut().item_spacing.x = 4.0;
                for (label, actual) in [("Fit", false), ("100%", true)] {
                    let kind = if self.actual_size == actual { ButtonKind::On } else { ButtonKind::Quiet };
                    if style::button(ui, label, kind, 24.0, true, palette).clicked() {
                        self.actual_size = actual;
                    }
                }
                ui.add_space(6.0);
                if style::button(ui, "Peaking", if self.peaking { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette).clicked() {
                    self.peaking = !self.peaking;
                }
                let mut t = f32::from(self.threshold);
                ui.scope(|ui| {
                    ui.spacing_mut().slider_width = 70.0;
                    if ui
                        .add_enabled(self.peaking, egui::Slider::new(&mut t, 6.0..=40.0).show_value(false))
                        .on_hover_text("Peaking threshold: higher marks fewer, stronger edges")
                        .changed()
                    {
                        self.threshold = t.round() as u8;
                    }
                });
                for (label, flag) in [("Clipping", 0), ("Grid", 1), ("Subject box", 2)] {
                    let on = match flag {
                        0 => self.clipping,
                        1 => self.grid,
                        _ => self.subject_box,
                    };
                    if style::button(ui, label, if on { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette).clicked() {
                        match flag {
                            0 => self.clipping = !on,
                            1 => self.grid = !on,
                            _ => self.subject_box = !on,
                        }
                    }
                }
                let ratios = &s.host.magnifier_ratios;
                if !ratios.is_empty() {
                    let current = s.host.magnifier_current.unwrap_or(0) as u32;
                    let label = if current == 0 {
                        "Magnifier".to_owned()
                    } else {
                        format!("Magnifier {}×", trim(current as f32 / 10.0))
                    };
                    let editable = s.fresh() && s.host.editable && !s.pending;
                    if style::button(ui, &label, if current == 0 { ButtonKind::Quiet } else { ButtonKind::On }, 22.0, editable, palette)
                        .on_hover_text("The camera's magnifier, centred on the subject box; click for the next ratio")
                        .clicked()
                    {
                        let next = ratios.iter().copied().find(|r| *r > current).unwrap_or(0);
                        out.push(LiveIntent::Magnify {
                            ratio: next,
                            x: ((roi.x + roi.width / 2.0) * 639.0).round() as u16,
                            y: ((roi.y + roi.height / 2.0) * 479.0).round() as u16,
                        });
                    }
                }
            },
        );
    }

    /// The estimate panel at the bottom right (`.expo`): the preview's
    /// histogram with its clipped share, and the exposure.
    fn estimate(&mut self, ui: &mut Ui, photo: Rect, s: &Snapshot, palette: &CapturePalette) {
        let rect = Rect::from_min_size(
            photo.right_bottom() + egui::vec2(-254.0, -10.0 - 106.0),
            egui::vec2(244.0, 106.0),
        );
        let p = ui.painter();
        glass(p, rect, palette);
        let inner = rect.shrink2(egui::vec2(12.0, 10.0));
        style::paint_job(
            p,
            inner.left_top(),
            Align2::LEFT_TOP,
            style::caps_job("Live view", 10.5, palette.ink3),
        );
        style::paint_job(
            p,
            inner.right_top(),
            Align2::RIGHT_TOP,
            style::job(PreviewLevels::CAUTION_SHORT, 12.0, palette.ink3, 0.0),
        );
        let hist = Rect::from_min_size(
            egui::pos2(inner.left(), inner.top() + 21.0),
            egui::vec2(inner.width(), 52.0),
        );
        if let Some((generation, levels)) = &s.levels {
            let key = (
                *generation,
                [
                    hist.left().to_bits(),
                    hist.top().to_bits(),
                    hist.width().to_bits(),
                    hist.height().to_bits(),
                ],
            );
            if self.histogram.as_ref().is_none_or(|(k, _)| *k != key) {
                self.histogram = Some((key, Arc::new(histogram_mesh(levels, hist, palette))));
            }
            if let Some((_, mesh)) = &self.histogram {
                p.add(Shape::mesh(mesh.clone()));
            }
        }
        let y = inner.bottom();
        let e = s.host.exposure.as_ref();
        let mut x = inner.left();
        for text in [
            e.and_then(|e| e.iso).map(style::iso_label),
            e.and_then(|e| e.shutter).map(style::shutter_label),
            e.and_then(|e| e.f_number)
                .filter(|f| *f > 0)
                .map(|f| format!("f/{}", trim(f as f32 / 100.0))),
        ]
        .into_iter()
        .flatten()
        {
            x = style::paint_job(
                p,
                egui::pos2(x, y),
                Align2::LEFT_BOTTOM,
                style::job(&text, 12.5, palette.ink, 0.2),
            )
            .right()
                + 6.0;
        }
        if let Some((_, levels)) = &s.levels {
            let share = 100.0 * levels.clipped_share;
            style::paint_job(
                p,
                egui::pos2(inner.right(), y),
                Align2::RIGHT_BOTTOM,
                style::job(
                    &format!("{share:.1} % clipped"),
                    12.5,
                    if share > 0.05 {
                        palette.warn
                    } else {
                        palette.ok
                    },
                    0.0,
                ),
            );
        }
    }
}

/// Bars of the preview's 256-bin luma histogram (square-root scale) and the
/// clipped band at the right.
pub(crate) fn histogram_mesh(levels: &PreviewLevels, rect: Rect, palette: &CapturePalette) -> Mesh {
    let mut mesh = Mesh::default();
    let peak = levels.histogram.iter().copied().max().unwrap_or(0).max(1) as f32;
    let columns = rect.width().max(1.0) as usize;
    for c in 0..columns {
        let a = c * 256 / columns;
        let b = ((c + 1) * 256 / columns).max(a + 1).min(256);
        let n = levels.histogram[a..b].iter().copied().max().unwrap_or(0) as f32;
        let h = (n / peak).sqrt() * rect.height();
        if h > 0.0 {
            mesh.add_colored_rect(
                Rect::from_min_max(
                    egui::pos2(rect.left() + c as f32, rect.bottom() - h),
                    egui::pos2(rect.left() + c as f32 + 1.0, rect.bottom()),
                ),
                palette.ink3.gamma_multiply(0.7),
            );
        }
    }
    mesh.add_colored_rect(
        Rect::from_min_max(egui::pos2(rect.right() - 8.0, rect.top()), rect.max),
        palette.warn.gamma_multiply(0.25),
    );
    mesh
}

fn trim(v: f32) -> String {
    let s = format!("{v:.1}");
    s.strip_suffix(".0").map(str::to_owned).unwrap_or(s)
}

/// A floating panel (`.glass`).
fn glass(p: &egui::Painter, rect: Rect, palette: &CapturePalette) {
    p.rect_filled(rect.expand(1.0), 0.0, palette.line2);
    p.rect_filled(rect, 0.0, palette.panel);
}

/// The subject box: a faint frame, white corner marks and its caption.
fn subject_box(p: &egui::Painter, r: Rect, palette: &CapturePalette) {
    let _ = palette;
    p.rect_stroke(
        r,
        0.0,
        Stroke::new(1.0_f32, Color32::from_white_alpha(71)),
        StrokeKind::Middle,
    );
    let l = 14.0f32.min(r.width() / 3.0).min(r.height() / 3.0);
    let stroke = Stroke::new(1.5_f32, Color32::WHITE);
    for (c, dx, dy) in [
        (r.left_top(), 1.0, 1.0),
        (r.right_top(), -1.0, 1.0),
        (r.left_bottom(), 1.0, -1.0),
        (r.right_bottom(), -1.0, -1.0),
    ] {
        p.line_segment([c, c + egui::vec2(l * dx, 0.0)], stroke);
        p.line_segment([c, c + egui::vec2(0.0, l * dy)], stroke);
    }
    style::paint_job(
        p,
        r.left_top() - egui::vec2(0.0, 8.0),
        Align2::LEFT_BOTTOM,
        style::caps_job(
            "Subject box · used by the survey and the magnifier",
            10.0,
            Color32::from_white_alpha(153),
        ),
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use eframe::egui::ColorImage;
    use serde_json::json;
    use std::time::Instant;

    fn snapshot(generation: u64) -> Snapshot {
        let mut image = ColorImage::filled([120, 80], Color32::from_gray(100));
        image.pixels[0] = Color32::WHITE;
        let image = Arc::new(image);
        let mut s = Snapshot {
            online: true,
            observed: Some(Instant::now()),
            preview: Some((generation, image.clone())),
            peaking: Some((
                generation,
                Arc::new(crate::capture_aids::Peaking::analyze(&image)),
            )),
            levels: Some((generation, Arc::new(PreviewLevels::analyze(&image)))),
            ..Default::default()
        };
        s.set_state(json!({"camera_revision":1,"plan_revision":1,"sequence_id":1,"phase":"ready","connected":true,
            "editable":true,"busy":false,"roi":{"x":0.1,"y":0.1,"width":0.8,"height":0.8},
            "preview":{"available":true,"fresh":true,"generation":generation,"age_seconds":0.2},
            "magnifier_ratios":[0,59,117],"magnifier_current":0,
            "exposure":{"iso":100,"shutter":65544,"f_number":560}}));
        s
    }

    fn frame(
        ctx: &egui::Context,
        view: &mut LiveView,
        s: &Snapshot,
        time: f64,
        events: Vec<egui::Event>,
    ) -> (egui::FullOutput, Vec<LiveIntent>) {
        let palette = CapturePalette::default();
        let mut intents = Vec::new();
        let out = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1332.0, 811.0),
                )),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| intents = view.show(ui, s, &palette));
            },
        );
        (out, intents)
    }

    /// Textures are uploaded when the preview changes, never on pointer
    /// motion; the estimate panel says what it is.
    #[test]
    fn uploads_follow_the_preview_not_the_pointer() {
        let ctx = egui::Context::default();
        let mut view = LiveView::default();
        let s = snapshot(1);
        let (out, _) = frame(&ctx, &mut view, &s, 0.0, vec![]);
        assert_eq!(view.uploads, 3, "picture, peaking and clipping");
        for i in 0..5 {
            frame(
                &ctx,
                &mut view,
                &s,
                0.1 * (i + 1) as f64,
                vec![egui::Event::PointerMoved(egui::pos2(
                    300.0 + 50.0 * i as f32,
                    300.0,
                ))],
            );
        }
        assert_eq!(view.uploads, 3);
        frame(&ctx, &mut view, &snapshot(2), 1.0, vec![]);
        assert_eq!(view.uploads, 6);
        let texts: Vec<String> = out
            .shapes
            .iter()
            .filter_map(|s| match &s.shape {
                Shape::Text(t) => Some(t.galley.text().to_owned()),
                _ => None,
            })
            .collect();
        for want in [
            "estimate, not the RAW",
            "ISO 100",
            "1/8 s",
            "f/5.6",
            "LIVE VIEW",
        ] {
            assert!(texts.iter().any(|t| t == want), "{want}: {texts:?}");
        }
    }

    /// Dragging on the picture draws a new subject box.
    #[test]
    fn dragging_draws_a_subject_box() {
        let ctx = egui::Context::default();
        let mut view = LiveView::default();
        let s = snapshot(1);
        frame(&ctx, &mut view, &s, 0.0, vec![]);
        let photo = photo_rect(
            Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1332.0, 811.0)),
            1.5,
        );
        let a = photo.lerp_inside(egui::vec2(0.25, 0.25));
        let b = photo.lerp_inside(egui::vec2(0.75, 0.6));
        let button = |pos, pressed| egui::Event::PointerButton {
            pos,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: Default::default(),
        };
        let mut all = Vec::new();
        for (i, events) in [
            vec![egui::Event::PointerMoved(a), button(a, true)],
            vec![egui::Event::PointerMoved(a + egui::vec2(20.0, 20.0))],
            vec![egui::Event::PointerMoved(b)],
            vec![button(b, false)],
        ]
        .into_iter()
        .enumerate()
        {
            all.extend(frame(&ctx, &mut view, &s, 0.1 * (i + 1) as f64, events).1);
        }
        match all.as_slice() {
            [LiveIntent::SetRoi(roi)] => {
                assert!(
                    (roi.x - 0.25).abs() < 0.01 && (roi.y - 0.25).abs() < 0.01,
                    "{roi:?}"
                );
                assert!(
                    (roi.width - 0.5).abs() < 0.01 && (roi.height - 0.35).abs() < 0.01,
                    "{roi:?}"
                );
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn the_preview_fits_its_canvas() {
        let canvas = Rect::from_min_size(egui::pos2(0.0, 80.0), egui::vec2(1332.0, 811.0));
        let r = photo_rect(canvas, 1.5);
        assert!((r.height() - 773.0).abs() < 0.5, "the mockup's 1160 x 773");
        assert!((r.width() - 1159.5).abs() < 1.0);
    }
}
