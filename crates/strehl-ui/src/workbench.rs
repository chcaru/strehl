//! Direct, interactive inspection of actual camera previews. No registration,
//! focus score or final-render pixels are invented by this view.

use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, TextureHandle, Vec2};

use crate::{theme, viewer::preview_aperture};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WorkbenchMode {
    Probe,
    Compare,
}

#[derive(Clone)]
pub struct SourcePhoto {
    pub epoch: u64,
    pub index: usize,
    pub texture: TextureHandle,
    pub aperture: [u32; 2],
}

pub(crate) struct PhotoSlot {
    current: SourcePhoto,
    previous: Option<SourcePhoto>,
    started: Option<f64>,
    blend: f32,
    pending: bool,
    deferred: bool,
}

impl PhotoSlot {
    pub(crate) fn sync(slot: &mut Option<Self>, incoming: Option<SourcePhoto>, epoch: u64) {
        if let Some(slot) = slot {
            slot.deferred = false;
        }
        let incoming =
            incoming.filter(|photo| photo.epoch == epoch && !photo.aperture.contains(&0));
        let Some(photo) = incoming else {
            if let Some(slot) = slot {
                slot.pending = true;
            }
            return;
        };
        if let Some(slot) = slot {
            slot.pending = false;
            if slot.current.epoch == photo.epoch && slot.current.index == photo.index {
                if slot.current.texture.id() == photo.texture.id() {
                    return;
                }
                let pixels =
                    |photo: &SourcePhoto| photo.texture.size()[0] * photo.texture.size()[1];
                // Cache eviction can expose a smaller fallback. Keep the
                // already displayed texture instead of visibly downgrading it.
                if pixels(&photo) <= pixels(&slot.current) {
                    return;
                }
                if slot.previous.is_some() {
                    // Promoting a partly revealed texture to an opaque base
                    // would flash its pixels. Finish this reveal first; the
                    // browser provides its newest cached tier on the next
                    // paint, so no third texture is retained here.
                    slot.deferred = true;
                    return;
                }
                let same_aperture = slot.current.aperture == photo.aperture;
                slot.previous = same_aperture.then(|| slot.current.clone());
                slot.current = photo;
                slot.started = None;
                slot.blend = if same_aperture { 0.0 } else { 1.0 };
                return;
            }
        }
        *slot = Some(Self {
            current: photo,
            previous: None,
            started: None,
            blend: 1.0,
            pending: false,
            deferred: false,
        });
    }

    pub(crate) fn advance(&mut self, now: f64) -> bool {
        if self.previous.is_none() {
            return false;
        }
        let start = *self.started.get_or_insert(now);
        let elapsed = ((now - start) / 0.22).clamp(0.0, 1.0) as f32;
        self.blend = elapsed * elapsed * (3.0 - 2.0 * elapsed);
        if elapsed >= 1.0 {
            self.previous = None;
        }
        // Also request a paint after completion, so a deferred higher tier
        // can begin without relying on unrelated input to wake the UI.
        true
    }

    pub(crate) fn current(&self) -> &SourcePhoto {
        &self.current
    }
    pub(crate) fn needs_repaint(&self) -> bool {
        self.previous.is_some() || self.deferred
    }
    pub(crate) fn paint(&self, painter: &egui::Painter, destination: Rect, region: Rect) {
        let paint = |photo: &SourcePhoto, alpha: u8| {
            let (_, aperture_uv) =
                preview_aperture(photo.texture.size_vec2(), photo.aperture, true);
            let uv = Rect::from_min_max(
                aperture_uv.min + region.min.to_vec2() * aperture_uv.size(),
                aperture_uv.min + region.max.to_vec2() * aperture_uv.size(),
            );
            painter.image(
                photo.texture.id(),
                destination,
                uv,
                Color32::from_white_alpha(alpha),
            );
        };
        if let Some(previous) = &self.previous {
            paint(previous, 255);
        }
        paint(&self.current, (self.blend * 255.0).round() as u8);
    }

    fn label(&self, role: &str) -> String {
        format!(
            "{role} · frame {} · {}px{}",
            self.current.index + 1,
            self.current.texture.size()[0].max(self.current.texture.size()[1]),
            if self.pending { " · updating" } else { "" }
        )
    }
}

pub struct Workbench {
    epoch: Option<u64>,
    mode: Option<WorkbenchMode>,
    pin: Option<Pos2>,
    wipe: f32,
    zoom_index: usize,
    pair_held: bool,
    a: Option<PhotoSlot>,
    b: Option<PhotoSlot>,
}

impl Default for Workbench {
    fn default() -> Self {
        Self {
            epoch: None,
            mode: None,
            pin: None,
            wipe: 0.5,
            zoom_index: 0,
            pair_held: false,
            a: None,
            b: None,
        }
    }
}

impl Workbench {
    pub fn pin(&self) -> Option<Pos2> {
        self.pin
    }

    pub fn set_pin(&mut self, pin: Pos2) {
        if pin.x.is_finite() && pin.y.is_finite() {
            self.pin = Some(egui::pos2(pin.x.clamp(0.0, 1.0), pin.y.clamp(0.0, 1.0)));
        }
    }

    pub fn transitioning(&self) -> bool {
        [&self.a, &self.b]
            .into_iter()
            .flatten()
            .any(|slot| slot.previous.is_some() || slot.deferred)
    }

    pub fn show(
        &mut self,
        ui: &mut egui::Ui,
        mode: WorkbenchMode,
        a: Option<SourcePhoto>,
        b: Option<SourcePhoto>,
        epoch: u64,
    ) -> Option<[usize; 2]> {
        if self.epoch != Some(epoch) {
            if self.epoch.is_some() {
                crate::image_gesture::clear(ui.ctx());
            }
            // A caller may establish an initial inspection point before the
            // first paint. An actual import must clear the previous bracket's
            // point along with its textures.
            let pin = self.epoch.is_none().then_some(self.pin).flatten();
            *self = Self {
                epoch: Some(epoch),
                pin,
                ..Default::default()
            };
        }
        if self.mode != Some(mode) {
            if self.mode.is_some() {
                // Preserve the stable hit target, but not the previous mode's
                // click history: a probe click cannot reset a new comparison.
                crate::image_gesture::clear(ui.ctx());
            }
            self.mode = Some(mode);
            self.pair_held = false;
        }
        PhotoSlot::sync(&mut self.a, a, epoch);
        PhotoSlot::sync(&mut self.b, b, epoch);
        let now = ui.input(|input| input.time);
        if self.a.as_mut().is_some_and(|slot| slot.advance(now))
            | self.b.as_mut().is_some_and(|slot| slot.advance(now))
        {
            ui.ctx().request_repaint();
        }
        let (viewport, response) =
            ui.allocate_exact_size(ui.available_size(), Sense::click_and_drag());
        let reset_gesture = crate::image_gesture::reset(ui, &response);
        if response.is_pointer_button_down_on() && ui.input(|input| input.pointer.primary_pressed())
        {
            self.pair_held = false;
        }
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
            self.pin = None;
            self.zoom_index = 0;
            self.wipe = 0.5;
        }
        let painter = ui.painter_at(viewport);
        painter.rect_filled(viewport, 0.0, theme::BG);
        let Some(a) = &self.a else {
            note(
                &painter,
                viewport.center(),
                "Waiting for a source preview",
                Align2::CENTER_CENTER,
            );
            return None;
        };
        let image_rect = fit_photo(&a.current, viewport);
        let full = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
        a.paint(&painter, image_rect, full);
        let lenses = lens_rects(viewport, self.pin);
        // Holding the actual displayed pair at the first gesture lets the
        // caller suspend live endpoints before further dragging. Missing
        // requests retain their correctly labelled photos above, so never
        // return a requested identity in place of the pixels on screen.
        let hold_pair = if mode == WorkbenchMode::Compare
            && allowed
            && !reset_gesture.reset
            && !reset_gesture.pending
            && !self.pair_held
            && (response.clicked() || response.dragged())
            && let Some(b) = &self.b
            && a.current.epoch == epoch
            && b.current.epoch == epoch
            && compatible_photos(&a.current, &b.current)
        {
            Some([a.current.index, b.current.index])
        } else {
            None
        };
        self.pair_held |= hold_pair.is_some();
        if let Some(pointer) = response.interact_pointer_pos()
            && allowed
            && !reset_gesture.reset
            && !reset_gesture.pending
            && (response.clicked() || response.dragged())
        {
            match mode {
                WorkbenchMode::Probe
                    if !(self.pin.is_some()
                        && lenses.iter().any(|lens| lens.contains(pointer)))
                        && (image_rect.contains(pointer)
                            || self.pin.is_some() && response.dragged()) =>
                {
                    let uv = (pointer - image_rect.min) / image_rect.size();
                    self.pin = Some(egui::pos2(uv.x.clamp(0.0, 1.0), uv.y.clamp(0.0, 1.0)));
                }
                WorkbenchMode::Compare if self.b.is_some() => {
                    self.wipe =
                        ((pointer.x - image_rect.left()) / image_rect.width()).clamp(0.0, 1.0);
                }
                _ => (),
            }
        }
        if mode == WorkbenchMode::Probe
            && allowed
            && response.hovered()
            && !reset_gesture.reset
            && !reset_gesture.pending
        {
            let scroll = ui.input(|input| input.raw_scroll_delta.y);
            if scroll > 0.0 {
                self.zoom_index = (self.zoom_index + 1).min(2);
            }
            if scroll < 0.0 {
                self.zoom_index = self.zoom_index.saturating_sub(1);
            }
        }
        let header = viewport.left_top() + egui::vec2(14.0, 14.0);
        note(&painter, header, &a.label("A"), Align2::LEFT_TOP);
        match mode {
            WorkbenchMode::Probe => {
                let zoom = [4.0, 8.0, 16.0][self.zoom_index];
                note(
                    &painter,
                    viewport.right_top() + egui::vec2(-14.0, 14.0),
                    &format!("Detail · {zoom:.0}×"),
                    Align2::RIGHT_TOP,
                );
                if let Some(pin) = self.pin {
                    let anchor = image_rect.min + pin.to_vec2() * image_rect.size();
                    let lenses = lens_rects(viewport, Some(pin));
                    let area = detail_rect(lenses[0]);
                    let region = probe_region(pin, area.size() / image_rect.size() / zoom);
                    let footprint = Rect::from_min_max(
                        image_rect.min + region.min.to_vec2() * image_rect.size(),
                        image_rect.min + region.max.to_vec2() * image_rect.size(),
                    );
                    painter.rect_filled(footprint, 0.0, theme::ACCENT.gamma_multiply(0.07));
                    painter.rect_stroke(
                        footprint,
                        1.0,
                        Stroke::new(1.5_f32, theme::ACCENT),
                        egui::StrokeKind::Inside,
                    );
                    reticle(&painter, anchor, 9.0);
                    let identities = self.b.as_ref().map_or_else(
                        || format!("A · frame {}", a.current.index + 1),
                        |b| {
                            format!(
                                "A · frame {}   B · frame {}",
                                a.current.index + 1,
                                b.current.index + 1
                            )
                        },
                    );
                    note_in(
                        &painter,
                        viewport.shrink(8.0),
                        footprint.left_top() - egui::vec2(0.0, 8.0),
                        &identities,
                        Align2::LEFT_BOTTOM,
                    );
                    for (index, slot) in [self.a.as_ref(), self.b.as_ref()].into_iter().enumerate()
                    {
                        let lens = lenses[index];
                        let connector = if lens.center().y < anchor.y {
                            lens.center_bottom()
                        } else {
                            lens.center_top()
                        };
                        painter.line_segment(
                            [footprint.center(), connector],
                            Stroke::new(1.0_f32, theme::ACCENT.gamma_multiply(0.45)),
                        );
                        painter.rect_filled(lens, 0.0, theme::PANEL);
                        painter.rect_stroke(
                            lens,
                            5.0,
                            Stroke::new(1.0_f32, theme::LINE),
                            egui::StrokeKind::Inside,
                        );
                        if let Some(slot) = slot {
                            let detail = detail_rect(lens);
                            let photo_rect = fit_photo(&slot.current, viewport);
                            let region =
                                probe_region(pin, detail.size() / photo_rect.size() / zoom);
                            slot.paint(&painter.with_clip_rect(detail), detail, region);
                            let mark =
                                detail.min + ((pin - region.min) / region.size()) * detail.size();
                            reticle(&painter, mark, 5.0);
                            note_in(
                                &painter.with_clip_rect(lens),
                                lens.shrink(5.0),
                                lens.min + egui::vec2(8.0, 5.0),
                                &slot.label(if index == 0 { "A" } else { "B" }),
                                Align2::LEFT_TOP,
                            );
                        } else {
                            note(
                                &painter,
                                lens.center(),
                                "B · preparing frame",
                                Align2::CENTER_CENTER,
                            );
                        }
                    }
                }
                note(
                    &painter,
                    viewport.center_bottom() - egui::vec2(0.0, 10.0),
                    "Click to sample · drag to move · wheel to magnify",
                    Align2::CENTER_BOTTOM,
                );
            }
            WorkbenchMode::Compare => {
                if let Some(b) = &self.b {
                    if compatible_photos(&a.current, &b.current) {
                        let x = egui::lerp(image_rect.x_range(), self.wipe);
                        let right =
                            Rect::from_min_max(egui::pos2(x, image_rect.top()), image_rect.max);
                        b.paint(
                            &painter.with_clip_rect(right.intersect(viewport)),
                            image_rect,
                            comparison_region(a.current.aperture, b.current.aperture),
                        );
                        painter.line_segment(
                            [
                                egui::pos2(x, image_rect.top()),
                                egui::pos2(x, image_rect.bottom()),
                            ],
                            Stroke::new(1.0_f32, theme::ACCENT),
                        );
                        difference_handle(&painter, egui::pos2(x, image_rect.center().y));
                        note_in(
                            &painter,
                            viewport.shrink(8.0),
                            egui::pos2(x, image_rect.center().y + 35.0),
                            "Slide to compare",
                            Align2::CENTER_TOP,
                        );
                        if response.hovered() {
                            ui.ctx().set_cursor_icon(egui::CursorIcon::ResizeHorizontal);
                        }
                        note(
                            &painter,
                            viewport.right_top() + egui::vec2(-14.0, 14.0),
                            &b.label("B"),
                            Align2::RIGHT_TOP,
                        );
                    } else {
                        note(
                            &painter,
                            viewport.center(),
                            "Different image crops · open Detail",
                            Align2::CENTER_CENTER,
                        );
                    }
                } else {
                    note(
                        &painter,
                        viewport.center(),
                        "Comparison preview is not ready",
                        Align2::CENTER_CENTER,
                    );
                }
                note(
                    &painter,
                    viewport.center_bottom() - egui::vec2(0.0, 10.0),
                    "Frame difference · drag the divider · original positions",
                    Align2::CENTER_BOTTOM,
                );
            }
        }
        hold_pair
    }
}

fn fit_photo(photo: &SourcePhoto, viewport: Rect) -> Rect {
    let (size, _) = preview_aperture(photo.texture.size_vec2(), photo.aperture, true);
    let scale = (viewport.width() / size.x).min(viewport.height() / size.y) * 0.95;
    Rect::from_center_size(viewport.center(), size * scale)
}

fn compatible_photos(a: &SourcePhoto, b: &SourcePhoto) -> bool {
    let aspect = |photo: &SourcePhoto| photo.aperture[0] as f32 / photo.aperture[1] as f32;
    (aspect(a) / aspect(b) - 1.0).abs() <= 0.005
}

fn comparison_region(a: [u32; 2], b: [u32; 2]) -> Rect {
    let a_aspect = a[0] as f32 / a[1] as f32;
    let b_aspect = b[0] as f32 / b[1] as f32;
    let size = if b_aspect > a_aspect {
        egui::vec2(a_aspect / b_aspect, 1.0)
    } else {
        egui::vec2(1.0, b_aspect / a_aspect)
    };
    Rect::from_center_size(egui::pos2(0.5, 0.5), size)
}

fn lens_rects(viewport: Rect, pin: Option<Pos2>) -> [Rect; 2] {
    let width = (viewport.width() * 0.25)
        .clamp(80.0, 224.0)
        .min((viewport.width() - 30.0).max(1.0) / 2.0);
    let height = (width * 0.75).min((viewport.height() - 46.0).max(1.0));
    // Keep the sampled area visible when inspecting the bottom of the photo.
    // Both lenses move together, so A/B never exchange sides.
    let top = if pin.is_some_and(|pin| pin.y > 0.58) {
        viewport.top() + 38.0
    } else {
        viewport.bottom() - height - 32.0
    };
    [
        Rect::from_min_size(
            egui::pos2(viewport.left() + 12.0, top),
            egui::vec2(width, height),
        ),
        Rect::from_min_size(
            egui::pos2(viewport.right() - width - 12.0, top),
            egui::vec2(width, height),
        ),
    ]
}

fn detail_rect(lens: Rect) -> Rect {
    Rect::from_min_max(
        lens.min + egui::vec2(5.0, 25.0),
        lens.max - Vec2::splat(5.0),
    )
}

fn difference_handle(painter: &egui::Painter, center: Pos2) {
    let handle = Rect::from_center_size(center, egui::vec2(34.0, 44.0));
    painter.rect_filled(handle, 0.0, theme::PANEL);
    painter.rect_stroke(
        handle,
        7.0,
        Stroke::new(1.0_f32, theme::ACCENT),
        egui::StrokeKind::Inside,
    );
    for direction in [-1.0, 1.0] {
        let tip = center + egui::vec2(direction * 10.0, 0.0);
        for y in [-4.0, 4.0] {
            painter.line_segment(
                [center + egui::vec2(direction * 5.0, y), tip],
                Stroke::new(1.5_f32, theme::INK),
            );
        }
    }
}

fn probe_region(pin: Pos2, size: Vec2) -> Rect {
    let size = size.clamp(Vec2::splat(0.0001), Vec2::splat(1.0));
    let half = size * 0.5;
    let center = pin.to_vec2().clamp(half, Vec2::splat(1.0) - half);
    Rect::from_center_size(center.to_pos2(), size)
}

fn reticle(painter: &egui::Painter, center: Pos2, radius: f32) {
    painter.circle_stroke(center, radius, Stroke::new(1.0_f32, theme::ACCENT));
    painter.line_segment(
        [
            center - egui::vec2(radius + 4.0, 0.0),
            center + egui::vec2(radius + 4.0, 0.0),
        ],
        Stroke::new(1.0_f32, theme::ACCENT),
    );
    painter.line_segment(
        [
            center - egui::vec2(0.0, radius + 4.0),
            center + egui::vec2(0.0, radius + 4.0),
        ],
        Stroke::new(1.0_f32, theme::ACCENT),
    );
}

fn note(painter: &egui::Painter, point: Pos2, text: &str, align: Align2) {
    let galley = painter.layout_no_wrap(text.to_owned(), FontId::proportional(11.0), theme::INK);
    let rect = align.anchor_size(point, galley.size());
    painter.rect_filled(
        rect.expand2(egui::vec2(4.0, 2.0)),
        0.0,
        Color32::from_black_alpha(200),
    );
    painter.galley(rect.min, galley, theme::INK);
}

fn note_in(painter: &egui::Painter, bounds: Rect, point: Pos2, text: &str, align: Align2) {
    let galley = painter.layout_no_wrap(text.to_owned(), FontId::proportional(11.0), theme::INK);
    let wanted = align.anchor_size(point, galley.size());
    let max = bounds.max - galley.size();
    let min = egui::pos2(
        wanted.min.x.clamp(bounds.left(), max.x.max(bounds.left())),
        wanted.min.y.clamp(bounds.top(), max.y.max(bounds.top())),
    );
    let rect = Rect::from_min_size(min, galley.size());
    let painter = painter.with_clip_rect(bounds);
    painter.rect_filled(
        rect.expand2(egui::vec2(4.0, 2.0)),
        0.0,
        Color32::from_black_alpha(200),
    );
    painter.galley(rect.min, galley, theme::INK);
}

#[cfg(test)]
#[path = "workbench-tests.rs"]
mod tests;
