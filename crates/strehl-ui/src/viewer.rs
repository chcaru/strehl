use crate::theme;

#[cfg(test)]
#[path = "viewer-tests.rs"]
mod tests;
use eframe::egui::{self, Color32, Rect, Sense, TextureHandle, Vec2};

const REVEAL_SECONDS: f64 = 0.22;

struct Reveal {
    previous: TextureHandle,
    source_size: [u32; 2],
    overview: bool,
    started: Option<f64>,
}

pub struct Viewer {
    pub texture: Option<TextureHandle>,
    pub source_size: [u32; 2],
    pub overview: bool,
    pub fit: bool,
    pub zoom: f32,
    pan: Vec2,
    drag: Option<egui::Pos2>,
    source_identity: Option<(u64, usize)>,
    reveal: Option<Reveal>,
    photo_paint: Option<crate::photo_viewport::PhotoPaint>,
    pub(crate) display_mapping: Option<(Rect, Rect)>,
}

impl Default for Viewer {
    fn default() -> Self {
        Self {
            texture: None,
            source_size: [0; 2],
            overview: false,
            fit: true,
            zoom: 1.0,
            pan: Vec2::ZERO,
            drag: None,
            source_identity: None,
            reveal: None,
            photo_paint: None,
            display_mapping: None,
        }
    }
}

impl Viewer {
    pub(crate) fn set_photo_paint(&mut self, paint: Option<crate::photo_viewport::PhotoPaint>) {
        let previous = self.aperture_size();
        let changed = self.photo_paint.is_some() != paint.is_some();
        self.photo_paint = paint;
        if changed
            && !self.fit
            && let (Some(old), Some(next)) = (previous, self.aperture_size())
        {
            self.zoom *= old.x / next.x;
        }
    }
    pub(crate) fn native_inspection_available(&self) -> bool {
        self.texture.is_some() && (!self.overview || self.photo_paint.is_some())
    }
    pub(crate) fn install_refinement(
        &mut self,
        texture: &TextureHandle,
        source_size: [u32; 2],
        overview: bool,
    ) {
        let previous = self.aperture_size();
        self.install(texture, source_size, overview);
        if !self.fit
            && let (Some(old), Some(next)) = (previous, self.aperture_size())
        {
            self.zoom *= old.x / next.x;
        }
    }
    /// Instant replacement for a new result/draft. Camera source refinement
    /// uses install_source so only two resolutions of the same capture blend.
    pub fn install(&mut self, texture: &TextureHandle, source_size: [u32; 2], overview: bool) {
        self.reveal = None;
        self.source_identity = None;
        self.texture = Some(texture.clone());
        self.source_size = source_size;
        self.overview = overview;
    }

    pub fn install_source(
        &mut self,
        texture: &TextureHandle,
        source_size: [u32; 2],
        overview: bool,
        identity: (u64, usize),
    ) {
        if self.has_source(texture, identity) {
            return;
        }
        let previous_aperture = self.aperture_size();
        let same_capture = self.source_identity == Some(identity);
        let previous = self.texture.as_ref().filter(|current| {
            let current_size = current.size();
            let next_size = texture.size();
            same_capture
                && self.source_size == source_size
                && next_size[0] * next_size[1] > current_size[0] * current_size[1]
        });
        self.reveal = previous.map(|previous| Reveal {
            previous: previous.clone(),
            source_size: self.source_size,
            overview: self.overview,
            started: None,
        });
        self.texture = Some(texture.clone());
        self.source_size = source_size;
        self.overview = overview;
        self.source_identity = Some(identity);
        if !self.fit
            && let Some(previous) = previous_aperture
            && let Some(next) = self.aperture_size()
            && previous.x > 0.0
            && next.x > 0.0
        {
            self.zoom *= previous.x / next.x;
        }
    }

    pub(crate) fn has_source(&self, texture: &TextureHandle, identity: (u64, usize)) -> bool {
        self.texture
            .as_ref()
            .is_some_and(|current| current.id() == texture.id())
            && self.source_identity == Some(identity)
    }

    pub fn cancel_reveal(&mut self) {
        self.reveal = None;
    }

    pub fn transitioning(&self) -> bool {
        self.reveal.is_some()
    }

    /// Canonical display extent of a reduced image, correcting only integer
    /// resize rounding. Native views always retain their exact pixel geometry.
    pub fn aperture_size(&self) -> Option<Vec2> {
        if self.photo_paint.is_some() && !self.source_size.contains(&0) {
            return Some(egui::vec2(
                self.source_size[0] as f32,
                self.source_size[1] as f32,
            ));
        }
        self.texture
            .as_ref()
            .map(|texture| preview_aperture(texture.size_vec2(), self.source_size, self.overview).0)
    }

    pub fn reset(&mut self, fit: bool) {
        self.fit = fit;
        self.zoom = 1.0;
        self.pan = Vec2::ZERO;
        self.drag = None;
    }

    pub fn show(&mut self, ui: &mut egui::Ui, loading: bool) {
        self.display_mapping = None;
        let (rect, response) = ui.allocate_exact_size(ui.available_size(), Sense::click_and_drag());
        let painter = ui.painter_at(rect);
        painter.rect_filled(rect, 0.0, theme::BG);
        if let Some((texture_id, texture_size)) = self
            .texture
            .as_ref()
            .map(|texture| (texture.id(), texture.size_vec2()))
        {
            let pixels_per_point = ui.ctx().pixels_per_point();
            let (fallback_size, uv) =
                preview_aperture(texture_size, self.source_size, self.overview);
            let aperture_size = self.aperture_size().unwrap_or(fallback_size);
            let native = aperture_size / pixels_per_point;
            let fit_scale = (rect.width() / native.x).min(rect.height() / native.y) * 0.95;
            let reset_gesture = crate::image_gesture::reset(ui, &response);
            let allowed = ui.is_enabled()
                && ui.input(|input| {
                    input.focused
                        && input.viewport().focused != Some(false)
                        && input.viewport().minimized != Some(true)
                })
                && ui
                    .ctx()
                    .memory(|memory| memory.is_above_modal_layer(ui.layer_id()))
                && !egui::Popup::is_any_open(ui.ctx());
            if reset_gesture.reset {
                self.reset(true);
            }
            if !allowed || ui.input(|input| input.key_pressed(egui::Key::Escape)) {
                self.drag = None;
            } else if !reset_gesture.reset
                && response.is_pointer_button_down_on()
                && ui.input(|input| input.pointer.primary_pressed())
            {
                self.drag = response.interact_pointer_pos();
            }
            if self.fit {
                self.zoom = fit_scale;
            }
            if allowed
                && !reset_gesture.reset
                && !reset_gesture.pending
                && response.dragged()
                && let (Some(previous), Some(pointer)) =
                    (self.drag, response.interact_pointer_pos())
            {
                self.pan += pointer - previous;
                self.drag = Some(pointer);
                self.fit = false;
            }
            if allowed && !reset_gesture.reset && !reset_gesture.pending && response.hovered() {
                let scroll = ui.input(|i| i.smooth_scroll_delta.y);
                if scroll != 0.0 {
                    self.fit = false;
                    let previous = self.zoom;
                    self.zoom = (self.zoom * (scroll * 0.002).exp()).clamp(0.01, 16.0);
                    if let Some(pointer) = response.hover_pos() {
                        self.pan = (self.pan - (pointer - rect.center())) * (self.zoom / previous)
                            + (pointer - rect.center());
                    }
                }
            }
            if !ui.input(|input| input.pointer.primary_down()) {
                self.drag = None;
            }
            let size = native * self.zoom;
            // At 100%, one source pixel occupies one physical display pixel, including HiDPI.
            let top_left = ((rect.center() + self.pan - size * 0.5).to_vec2() * pixels_per_point)
                .round()
                / pixels_per_point;
            let image_rect = Rect::from_min_size(top_left.to_pos2(), size);
            let visible = image_rect.intersect(rect);
            self.display_mapping = Some((image_rect, visible));
            if let Some(paint) = &self.photo_paint {
                self.reveal = None;
                if visible.is_positive() {
                    let local =
                        |p: egui::Pos2| egui::Pos2::ZERO + (p - image_rect.min) / image_rect.size();
                    paint.paint(
                        &painter,
                        visible,
                        Rect::from_min_max(local(visible.min), local(visible.max)),
                    );
                }
                return;
            }
            let now = ui.input(|input| input.time);
            let reveal = self.reveal.as_mut().map(|reveal| {
                let started = *reveal.started.get_or_insert(now);
                let elapsed = ((now - started) / REVEAL_SECONDS).clamp(0.0, 1.0) as f32;
                let blend = elapsed * elapsed * (3.0 - 2.0 * elapsed);
                (
                    reveal.previous.clone(),
                    reveal.source_size,
                    reveal.overview,
                    blend,
                )
            });
            if let Some((previous, source_size, overview, blend)) = reveal
                && blend < 1.0
            {
                let (_, previous_uv) =
                    preview_aperture(previous.size_vec2(), source_size, overview);
                painter.image(previous.id(), image_rect, previous_uv, Color32::WHITE);
                painter.image(
                    texture_id,
                    image_rect,
                    uv,
                    Color32::from_white_alpha((blend * 255.0).round() as u8),
                );
                ui.ctx().request_repaint();
            } else {
                self.reveal = None;
                painter.image(texture_id, image_rect, uv, Color32::WHITE);
            }
        } else {
            let center = rect.center() - egui::vec2(0.0, 25.0);
            theme::mark(
                &painter,
                Rect::from_center_size(center, egui::vec2(24.0, 24.0)),
            );
            painter.text(
                center + egui::vec2(0.0, 47.0),
                egui::Align2::CENTER_CENTER,
                if loading {
                    "Loading preview…"
                } else {
                    "Open a focus bracket"
                },
                egui::FontId::proportional(19.0),
                theme::INK,
            );
            painter.text(
                center + egui::vec2(0.0, 77.0),
                egui::Align2::CENTER_CENTER,
                "Drop an ARW folder here to browse its focus planes.",
                egui::FontId::proportional(12.0),
                theme::MUTED,
            );
        }
    }
}

/// Camera previews and display reductions round their dimensions to integer
/// pixels. Their entire content was resampled into that rounded raster: there
/// are no extra border pixels to crop away. Restore the canonical display
/// aspect while preserving full UVs, reversing that tiny resize anisotropy.
/// Substantially different crops retain their own geometry; this is not a
/// general-purpose aspect-ratio override.
pub(crate) fn preview_aperture(texture: Vec2, source: [u32; 2], overview: bool) -> (Vec2, Rect) {
    let full_uv = Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0));
    if !overview || source.contains(&0) || texture.x <= 0.0 || texture.y <= 0.0 {
        return (texture, full_uv);
    }
    let aspect = source[0] as f32 / source[1] as f32;
    let canonical = if texture.x / texture.y > aspect {
        egui::vec2(texture.y * aspect, texture.y)
    } else {
        egui::vec2(texture.x, texture.x / aspect)
    };
    let relative_difference = (texture.x / texture.y / aspect - 1.0).abs();
    let removed = texture - canonical;
    if relative_difference > 0.005 && removed.x.max(removed.y) > 1.001 {
        return (texture, full_uv);
    }
    (canonical, full_uv)
}
