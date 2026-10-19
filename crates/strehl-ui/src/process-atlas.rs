//! A photographic volume for exploring observed processing data. X/Y are the
//! aligned image; the third axis is capture order, never recovered scene depth.
//! Detail size and construction time select other observed slices of that same
//! object. A positive sample means admitted support, not ownership or weight.

use crate::{
    pipeline::{DiagnosticKind, DiagnosticSurface, Stage},
    process_output_space::OutputSpace,
    process_space::{Input, Response},
    theme::{ACCENT, AMBER, BG, GREEN, INK, LINE, MUTED, PANEL},
};
use eframe::egui::{
    self, Align2, Color32, FontId, Painter, Pos2, Rect, Sense, Stroke, TextureHandle, Ui, Vec2,
};
use std::collections::VecDeque;

const LAYER_CAP: usize = 18;
const POINT_CAP: usize = 96;
const RAY_CAP: usize = 12;

#[derive(Clone, Copy, Debug, PartialEq)]
struct Camera {
    yaw: f32,
    pitch: f32,
    zoom: f32,
    pan: Vec2,
    spread: f32,
}

#[derive(Clone, Copy)]
struct SpreadGrab {
    pointer: Pos2,
    endpoint: Pos2,
    camera: Camera,
}
impl Default for Camera {
    fn default() -> Self {
        Self {
            yaw: -0.58,
            pitch: 0.23,
            zoom: 1.0,
            pan: Vec2::ZERO,
            spread: 0.88,
        }
    }
}

#[derive(Clone, Copy)]
struct Projection {
    camera: Camera,
    origin: Pos2,
    scale: f32,
    aspect: f32,
}
impl Projection {
    fn new(rect: Rect, camera: Camera, aspect: f32) -> Self {
        let aspect = if aspect.is_finite() && aspect > 0.0 {
            aspect
        } else {
            1.5
        };
        let flat = camera.yaw.abs() < 0.001 && camera.pitch.abs() < 0.001;
        let scale = if flat {
            ((rect.width() - 64.0).max(1.0) / aspect).min(rect.height()) * 0.94
        } else {
            (rect.width() / (aspect + camera.spread + 0.35))
                .min(rect.height() / (1.25 + camera.spread * 0.5))
                .max(1.0)
        } * camera.zoom;
        Self {
            camera,
            origin: rect.center()
                + if flat {
                    Vec2::ZERO
                } else {
                    egui::vec2(-rect.width() * 0.08, -rect.height() * 0.06)
                }
                + camera.pan,
            scale,
            aspect,
        }
    }
    fn at(self, uv: Pos2, depth: f32) -> Pos2 {
        let x = (uv.x - 0.5) * self.aspect;
        let y = uv.y - 0.5;
        let z = -depth * self.camera.spread;
        let (sy, cy) = self.camera.yaw.sin_cos();
        let (sp, cp) = self.camera.pitch.sin_cos();
        let rx = x * cy + z * sy;
        let rz = -x * sy + z * cy;
        self.origin + egui::vec2(rx, y * cp - rz * sp) * self.scale
    }
    fn quad(self, depth: f32) -> [Pos2; 4] {
        [
            egui::pos2(0.0, 0.0),
            egui::pos2(1.0, 0.0),
            egui::pos2(1.0, 1.0),
            egui::pos2(0.0, 1.0),
        ]
        .map(|uv| self.at(uv, depth))
    }
}

#[derive(Clone)]
struct Layer {
    frame: usize,
    sequence: Option<u64>,
    extent: Option<[usize; 2]>,
    points: Vec<Pos2>,
    cells: Vec<Rect>,
    admitted: usize,
    samples: usize,
}

#[derive(Clone)]
struct LivePreview {
    sequence: u64,
    texture: TextureHandle,
}
#[derive(Clone)]
struct FrontCandidate {
    texture: TextureHandle,
    sequence: u64,
    rank: u8,
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum Pick {
    Sample { frame: usize, uv: Pos2 },
    Photograph(Pos2),
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct AtlasView {
    camera: Camera,
    selected: Option<usize>,
    level: usize,
    pin: Option<Pos2>,
    pin_is_aligned: bool,
}

/// All cached payload is bounded by eighteen sparse layers and six retained
/// preview textures. Camera gestures only project that cache, never decode or
/// rescan the archive's image buffers.
pub(crate) struct ProcessAtlas {
    epoch: Option<(u64, u64)>,
    camera: Camera,
    selected: Option<usize>,
    level: usize,
    level_chosen: bool,
    pin: Option<Pos2>,
    pin_is_aligned: bool,
    cache_level: Option<usize>,
    layers: Vec<Layer>,
    live_preview: Option<LivePreview>,
    preview_generation: Option<u64>,
    grab: Option<Pos2>,
    spread_grab: Option<SpreadGrab>,
    front: Option<TextureHandle>,
    front_sequence: u64,
    front_rank: u8,
    pending_front: Option<FrontCandidate>,
    previous_front: Option<TextureHandle>,
    front_started: f64,
    undo: VecDeque<AtlasView>,
    redo: Vec<AtlasView>,
    transaction: Option<AtlasView>,
    history_revision: u64,
    history_commits: u64,
}
impl Default for ProcessAtlas {
    fn default() -> Self {
        Self {
            epoch: None,
            camera: Camera::default(),
            selected: None,
            level: 0,
            level_chosen: false,
            pin: None,
            pin_is_aligned: false,
            cache_level: None,
            layers: Vec::new(),
            live_preview: None,
            preview_generation: None,
            grab: None,
            spread_grab: None,
            front: None,
            front_sequence: 0,
            front_rank: 0,
            pending_front: None,
            previous_front: None,
            front_started: 0.0,
            undo: VecDeque::new(),
            redo: Vec::new(),
            transaction: None,
            history_revision: 0,
            history_commits: 0,
        }
    }
}

impl ProcessAtlas {
    fn view(&self) -> AtlasView {
        AtlasView {
            camera: self.camera,
            selected: self.selected,
            level: self.level,
            pin: self.pin,
            pin_is_aligned: self.pin_is_aligned,
        }
    }
    fn restore(&mut self, view: AtlasView) {
        self.camera = view.camera;
        self.selected = view.selected;
        self.level = view.level;
        self.level_chosen = true;
        self.pin = view.pin;
        self.pin_is_aligned = view.pin_is_aligned;
        self.grab = None;
        self.spread_grab = None;
        self.transaction = None;
    }
    fn commit(&mut self, before: AtlasView) {
        if before == self.view() {
            return;
        }
        if self.undo.len() == 64 {
            self.undo.pop_front();
        }
        self.undo.push_back(before);
        self.redo.clear();
        self.history_revision = self.history_revision.wrapping_add(1);
        self.history_commits = self.history_commits.wrapping_add(1);
    }
    pub(crate) fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }
    pub(crate) fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }
    pub(crate) fn history_depths(&self) -> (usize, usize) {
        (self.undo.len(), self.redo.len())
    }
    pub(crate) fn history_revision(&self) -> u64 {
        self.history_revision
    }
    pub(crate) fn history_commits(&self) -> u64 {
        self.history_commits
    }
    pub(crate) fn undo(&mut self) -> bool {
        let Some(before) = self.undo.pop_back() else {
            return false;
        };
        self.redo.push(self.view());
        self.restore(before);
        self.history_revision = self.history_revision.wrapping_add(1);
        true
    }
    pub(crate) fn redo(&mut self) -> bool {
        let Some(next) = self.redo.pop() else {
            return false;
        };
        self.undo.push_back(self.view());
        self.restore(next);
        self.history_revision = self.history_revision.wrapping_add(1);
        true
    }
    pub(crate) fn reset(&mut self) {
        let before = self.view();
        self.photograph();
        self.transaction = None;
        self.commit(before);
    }
    pub(crate) fn transitioning(&self) -> bool {
        self.previous_front.is_some() || self.pending_front.is_some()
    }
    pub(crate) fn contact_indices(&self) -> Vec<usize> {
        self.layers.iter().map(|layer| layer.frame).collect()
    }
    pub(crate) fn inspection_frame(&self) -> Option<usize> {
        self.selected
    }
    fn photograph(&mut self) {
        self.camera = Camera {
            yaw: 0.0,
            pitch: 0.0,
            ..Default::default()
        };
        self.selected = None;
        self.pin = None;
        self.pin_is_aligned = false;
        self.grab = None;
        self.spread_grab = None;
    }
    fn sync(&mut self, ui: &Ui, input: &Input<'_>) {
        let epoch = (input.epoch, input.progress.diagnostic_epoch);
        if self.epoch != Some(epoch) {
            *self = Self {
                epoch: Some(epoch),
                ..Default::default()
            };
        }
        if !self.level_chosen
            && let Some(level) = crate::process_output_space::initial_detail_level(
                &input.progress.admission_archive,
                input.progress.bands.unwrap_or(8),
                input.progress.output_geometry,
            )
        {
            self.level = level;
            // Adopt one actual observed default; sparse deliveries cannot
            // continually change the meaning of the volume under the pointer.
            self.level_chosen = true;
        }
        let count = input.frame_count;
        if self.selected.is_some_and(|frame| frame >= count) {
            self.selected = None;
        }
        let focus = self.selected.or(input.progress.processing_frame);
        let frames = layer_indices(count, focus);
        if self.cache_level != Some(self.level) {
            self.layers.clear();
            self.cache_level = Some(self.level);
        }
        self.layers.retain(|layer| frames.contains(&layer.frame));
        for frame in frames {
            let meta = input.progress.admission_archive.metadata(self.level, frame);
            let sequence = meta.map(|meta| meta.sequence);
            let old = self.layers.iter().position(|layer| layer.frame == frame);
            if old.is_some_and(|at| self.layers[at].sequence == sequence) {
                continue;
            }
            let layer = layer_from_archive(input, self.level, frame);
            if let Some(at) = old {
                self.layers[at] = layer;
            } else {
                self.layers.push(layer);
            }
        }
        self.layers.sort_by_key(|layer| layer.frame);
        if self.preview_generation != Some(input.progress.live_preview.generation) {
            self.live_preview = None;
            self.preview_generation = Some(input.progress.live_preview.generation);
        }
        if let Some(packet) = &input.progress.live_preview.latest
            && self
                .live_preview
                .as_ref()
                .is_none_or(|old| old.sequence != packet.sequence)
        {
            self.live_preview = Some(LivePreview {
                sequence: packet.sequence,
                texture: ui.ctx().load_texture(
                    format!("atlas-live-{}-{}", input.epoch, packet.sequence),
                    preview_image(packet, input.progress.live_preview.tone_range),
                    egui::TextureOptions::LINEAR,
                ),
            });
        }
        let now = ui.input(|state| state.time);
        if self.previous_front.is_some() && now - self.front_started >= 0.2 {
            self.previous_front = None;
        }
        // Photographic Preview outranks the much smaller Reconstructed map,
        // regardless of sequence. A later diagnostic must never downgrade the
        // photo while the developed TIFF is still arriving.
        let next = input
            .output
            .map(|texture| FrontCandidate {
                texture: texture.clone(),
                sequence: u64::MAX,
                rank: 2,
            })
            .or_else(|| {
                let surface = input
                    .surfaces
                    .iter()
                    .filter(|surface| surface.epoch == input.epoch)
                    .filter_map(|surface| {
                        surface.meta.and_then(|meta| {
                            let rank = match meta.kind {
                                DiagnosticKind::Preview => 1,
                                DiagnosticKind::Reconstructed => 0,
                                _ => return None,
                            };
                            Some(FrontCandidate {
                                texture: surface.texture.clone(),
                                sequence: meta.sequence,
                                rank,
                            })
                        })
                    })
                    .max_by_key(|item| (item.rank, item.sequence));
                let retained = self.live_preview.as_ref().map(|item| FrontCandidate {
                    texture: item.texture.clone(),
                    sequence: item.sequence,
                    rank: 1,
                });
                [surface, retained]
                    .into_iter()
                    .flatten()
                    .max_by_key(|item| (item.rank, item.sequence))
            });
        if let Some(next) = next.filter(|next| {
            (next.rank, next.sequence) > (self.front_rank, self.front_sequence)
                || (next.rank, next.sequence) == (self.front_rank, self.front_sequence)
                    && self
                        .front
                        .as_ref()
                        .is_none_or(|front| front.id() != next.texture.id())
        }) && self
            .pending_front
            .as_ref()
            .is_none_or(|pending| (next.rank, next.sequence) >= (pending.rank, pending.sequence))
        {
            self.pending_front = Some(next);
        }
        // An in-flight reveal finishes before adopting the newest queued image.
        // New deliveries cannot replace a barely-visible image as the old base.
        if self.previous_front.is_none()
            && let Some(next) = self.pending_front.take()
        {
            self.previous_front = self.front.replace(next.texture);
            self.front_rank = next.rank;
            self.front_sequence = next.sequence;
            self.front_started = now;
        }
        if self.transitioning() {
            ui.ctx().request_repaint();
        }
    }

    pub(crate) fn show(&mut self, ui: &mut Ui, input: Input<'_>) -> Response {
        self.sync(ui, &input);
        let before = self.view();
        let mut result = Response::default();
        let (bounds, _) = ui.allocate_exact_size(ui.available_size(), Sense::hover());
        if bounds.width() < 260.0 || bounds.height() < 220.0 {
            return result;
        }
        let p = ui.painter_at(bounds);
        p.rect_filled(bounds, 0.0, BG);
        let scene = object_scene(bounds);
        let gesture = ui.interact(bounds, ui.id().with("atlas-scene"), Sense::click_and_drag());
        let allowed = ui.is_enabled()
            && ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()));
        if allowed && gesture.hovered() {
            let factor = crate::process_scales::detail_zoom_factor(ui);
            if factor.is_finite() && factor > 0.0 {
                self.camera.zoom = (self.camera.zoom * factor).clamp(0.45, 5.0);
            }
        }
        if allowed
            && gesture.is_pointer_button_down_on()
            && ui.input(|state| state.pointer.primary_pressed())
        {
            self.grab = gesture.interact_pointer_pos();
        }
        if allowed
            && gesture.dragged()
            && let Some(at) = gesture.interact_pointer_pos()
            && let Some(previous) = self.grab
        {
            let delta = at - previous;
            self.grab = Some(at);
            if ui.input(|state| state.modifiers.shift) {
                self.camera.pan += delta;
            } else {
                self.camera.yaw = (self.camera.yaw + delta.x * 0.006).clamp(-1.15, 1.15);
                self.camera.pitch = (self.camera.pitch - delta.y * 0.006).clamp(-0.7, 0.7);
            }
            ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
        }
        if !ui.input(|state| state.pointer.primary_down()) {
            self.grab = None;
        }
        if gesture.double_clicked()
            || allowed
                && gesture.has_focus()
                && ui.input_mut(|state| state.consume_key(egui::Modifiers::NONE, egui::Key::Home))
        {
            self.photograph();
            result.return_live = true;
        }
        let mut history_action = false;
        gesture.context_menu(|ui| self.object_menu(ui, &mut result, &mut history_action));

        let aspect = input
            .output_size
            .map(|size| size[0] as f32 / size[1].max(1) as f32)
            .or_else(|| {
                input
                    .progress
                    .analysis_size
                    .or(input.progress.plane_size)
                    .map(|size| size[0] as f32 / size[1].max(1) as f32)
            })
            .or_else(|| {
                self.front
                    .as_ref()
                    .map(|texture| texture.size_vec2().x / texture.size_vec2().y)
            })
            .unwrap_or(1.5);
        let projection = Projection::new(scene, self.camera, aspect);
        let front_quad = projection.quad(0.0);
        let count = input.frame_count;
        let shared =
            shared_domain(&input) && (self.front_sequence != u64::MAX || input.output.is_some());
        let domain = input.progress.analysis_size.or(input.progress.plane_size);
        let painter = ui.painter_at(bounds.shrink(8.0));
        let dock = ObjectDock::new(bounds, projection);
        let selected = self.selected;
        let selected_layer = self
            .layers
            .iter()
            .find(|layer| Some(layer.frame) == selected)
            .cloned();
        let mut samples = Vec::with_capacity(LAYER_CAP * POINT_CAP);
        // Back-to-front painting supplies real occlusion with the photograph.
        // Wire planes are transparent; they do not invent opaque source pixels.
        for layer in self.layers.iter().rev() {
            let depth = capture_depth(layer.frame, count);
            let quad = projection.quad(depth);
            let active = Some(layer.frame) == selected;
            let color = capture_color(layer.frame);
            wire(
                &painter,
                quad,
                if active {
                    color
                } else {
                    LINE.gamma_multiply(0.72)
                },
                if active { 1.0 } else { 0.6 },
            );
            let read = input
                .progress
                .alignment_plane_observations
                .contains(&layer.frame);
            let prepared = input
                .progress
                .alignment_pyramid_observations
                .contains(&layer.frame);
            if read {
                painter.line_segment(
                    [quad[0], quad[0].lerp(quad[3], 0.08)],
                    Stroke::new(1.0_f32, ACCENT),
                );
            }
            if prepared {
                painter.line_segment(
                    [quad[0], quad[0].lerp(quad[1], 0.08)],
                    Stroke::new(1.0_f32, GREEN),
                );
            }
            if let Some(observation) = input.progress.merge_frame_observations.get(&layer.frame) {
                let bands = input.progress.bands.unwrap_or(64).clamp(1, 64);
                let observed =
                    (observation.fold_finished & (u64::MAX >> (64 - bands))).count_ones();
                if observed > 0 {
                    painter.line_segment(
                        [
                            quad[3],
                            quad[3].lerp(quad[2], observed as f32 / bands as f32),
                        ],
                        Stroke::new(1.0_f32, GREEN),
                    );
                }
            }
            if layer.extent == domain && layer.sequence.is_some() {
                for (&uv, &cell) in layer.points.iter().zip(&layer.cells) {
                    let at = projection.at(uv, depth);
                    painter.circle_filled(
                        at,
                        if active { 1.8 } else { 1.15 },
                        color.gamma_multiply(if active { 0.85 } else { 0.38 }),
                    );
                    projected_sample_cell(
                        &painter,
                        projection,
                        cell,
                        depth,
                        crate::process_sample_glyphs::level_color(self.level),
                        active,
                    );
                    samples.push((
                        Pick::Sample {
                            frame: layer.frame,
                            uv,
                        },
                        at,
                    ));
                }
            }
        }
        for corner in [0, 1, 2, 3] {
            painter.line_segment(
                [front_quad[corner], projection.quad(1.0)[corner]],
                Stroke::new(0.6_f32, LINE),
            );
        }
        if let Some(texture) = &self.front {
            let alpha = if let Some(previous) = &self.previous_front {
                image_quad(&painter, previous, front_quad, Color32::WHITE);
                let t = ((ui.input(|state| state.time) - self.front_started) / 0.2).clamp(0.0, 1.0)
                    as f32;
                (t * t * (3.0 - 2.0 * t) * 255.0).round() as u8
            } else {
                255
            };
            image_quad(
                &painter,
                texture,
                front_quad,
                Color32::from_white_alpha(alpha),
            );
        } else {
            painter.add(egui::Shape::convex_polygon(
                front_quad.to_vec(),
                PANEL.gamma_multiply(0.7),
                Stroke::NONE,
            ));
            label(
                &painter,
                projection.at(egui::pos2(0.12, 0.46), 0.0),
                "Waiting for the first aligned preview",
                11.0,
                MUTED,
            );
        }
        wire(&painter, front_quad, LINE, 0.8);
        if shared
            && let Some(layer) = selected_layer
                .as_ref()
                .filter(|layer| layer.extent == domain)
        {
            for (index, &uv) in layer.points.iter().enumerate() {
                let to = projection.at(uv, 0.0);
                painter.circle_stroke(
                    to,
                    2.2,
                    Stroke::new(0.8_f32, capture_color(layer.frame).gamma_multiply(0.75)),
                );
                if let Some(&cell) = layer.cells.get(index) {
                    projected_sample_cell(
                        &painter,
                        projection,
                        cell,
                        0.0,
                        crate::process_sample_glyphs::level_color(self.level),
                        true,
                    );
                }
                if index % layer.points.len().div_ceil(RAY_CAP).max(1) == 0 {
                    let from = projection.at(uv, capture_depth(layer.frame, count));
                    // Selected rays are an explicit x-ray inspection modifier,
                    // not hidden geometry painted as though it were in front.
                    painter.line_segment(
                        [from, to],
                        Stroke::new(0.6_f32, capture_color(layer.frame).gamma_multiply(0.3)),
                    );
                }
            }
        }
        if let Some(pin) = self.pin.filter(|_| !self.pin_is_aligned || shared) {
            let at = projection.at(pin, 0.0);
            painter.circle_stroke(at, 5.0, Stroke::new(1.0_f32, ACCENT));
            if shared {
                for layer in &self.layers {
                    if layer.extent == domain
                        && observed_support(&input, self.level, layer.frame, pin) == Some(true)
                    {
                        let from = projection.at(pin, capture_depth(layer.frame, count));
                        painter.line_segment(
                            [from, at],
                            Stroke::new(0.65_f32, capture_color(layer.frame).gamma_multiply(0.45)),
                        );
                        painter.circle_filled(from, 2.7, capture_color(layer.frame));
                    }
                }
            }
        }
        let hovered = gesture
            .hover_pos()
            .and_then(|pointer| pick_scene(pointer, front_quad, self.front.is_some(), &samples));
        if let Some(Pick::Sample { frame, uv }) = hovered {
            let at = projection.at(uv, capture_depth(frame, count));
            painter.circle_stroke(at, 4.0, Stroke::new(1.0_f32, INK));
            gesture.clone().on_hover_text(format!("Capture {:03} · admitted sample\nClick to connect this sample to the photograph. Positive support is not a blend weight.", frame + 1));
        }
        if allowed && gesture.clicked() && !gesture.double_clicked() {
            gesture.request_focus();
            if let Some(pick) = hovered {
                match pick {
                    Pick::Sample { frame, uv } => {
                        self.selected = Some(frame);
                        self.pin = Some(uv);
                        self.pin_is_aligned = true;
                        result.selected = Some(frame);
                    }
                    Pick::Photograph(uv) => {
                        self.pin = Some(uv);
                        self.pin_is_aligned = false;
                    }
                }
            }
        }
        self.capture_axis(ui, &painter, projection, &input, &mut result);
        self.spread_handle(ui, &painter, scene, projection, allowed);
        {
            let identity = if self.front_rank == 2 {
                "FINAL PHOTOGRAPH"
            } else if self.front.is_none() {
                "WAITING FOR ALIGNED PREVIEW"
            } else {
                "LIVE ALIGNED PREVIEW"
            };
            label(&p, dock.identity, identity, 9.0, MUTED);
        }
        self.object_controls(
            ui,
            &painter,
            &dock,
            &input,
            &mut result,
            &mut history_action,
        );
        self.detail_axis(ui, &painter, dock.details, projection, &input);
        self.camera_card(ui, &painter, &dock, projection, &input);
        let info = if let Some(layer) = selected_layer {
            if layer.sequence.is_some() {
                format!(
                    "Capture {:03} · {}/{} admitted samples shown · {} observed grid cells",
                    layer.frame + 1,
                    layer.points.len(),
                    layer.admitted,
                    layer.samples
                )
            } else {
                format!(
                    "Capture {:03} · admission sample not observed at this detail size",
                    layer.frame + 1
                )
            }
        } else {
            format!(
                "{} / {} capture slices · points: admitted samples · drag to orbit · Shift-drag to pan · wheel to zoom",
                self.layers.len(),
                count
            )
        };
        label(&painter, dock.info, &info, 8.0, MUTED);
        if input.output.is_some() && !shared {
            label(
                &p,
                dock.info + egui::vec2(0.0, 13.0),
                "Image / sample correspondence unavailable · no registered overlay",
                8.0,
                AMBER,
            );
        }
        if history_action {
            self.transaction = None;
        } else if ui.input(|state| state.pointer.primary_down()) {
            self.transaction.get_or_insert(before);
        } else {
            let origin = self.transaction.take().unwrap_or(before);
            self.commit(origin);
        }
        result
    }
}

include!("process-atlas-object.rs");

fn shared_domain(input: &Input<'_>) -> bool {
    if input.output.is_some() {
        input
            .output_size
            .is_some_and(|size| OutputSpace::from_progress(input.progress, size).is_some())
    } else {
        input
            .progress
            .analysis_size
            .or(input.progress.plane_size)
            .is_some()
    }
}

fn phase_receipts(input: &Input<'_>) -> [Option<(usize, usize)>; 4] {
    [
        input.progress.alignment_planes,
        input
            .progress
            .alignment_pairs
            .map(|(done, _, total)| (done, total)),
        input.progress.folded,
        (input.progress.stage == Stage::Complete).then_some((1, 1)),
    ]
}

fn phase_strip(ui: &mut Ui, rect: Rect, input: &Input<'_>) {
    let receipts = phase_receipts(input);
    for (index, (stage, title)) in [
        (Stage::Preparing, "READ"),
        (Stage::Alignment, "ALIGN"),
        (Stage::Merge, "COMBINE"),
        (Stage::Rendering, "SAVE"),
    ]
    .into_iter()
    .enumerate()
    {
        let cell = Rect::from_min_size(
            rect.min + egui::vec2(index as f32 * rect.width() / 4.0, 0.0),
            egui::vec2(rect.width() / 4.0, rect.height()),
        );
        let p = ui.painter_at(cell);
        let active = input.progress.stage == stage;
        let observed = input.progress.observed_stages.contains(&stage) || receipts[index].is_some();
        let color = if active {
            ACCENT
        } else if observed {
            GREEN
        } else {
            MUTED
        };
        let text = match receipts[index] {
            Some((done, total)) if cell.width() >= 72.0 => format!("{title} {done}/{total}"),
            _ => title.to_owned(),
        };
        label(&p, cell.min + egui::vec2(4.0, 5.0), &text, 7.5, color);
        let start = cell.left_bottom() + egui::vec2(4.0, -2.0);
        let end = cell.right_bottom() + egui::vec2(-4.0, -2.0);
        p.line_segment([start, end], Stroke::new(0.6_f32, LINE));
        if let Some((done, total)) = receipts[index].filter(|(_, total)| *total > 0) {
            p.line_segment(
                [
                    start,
                    start.lerp(end, (done as f32 / total as f32).clamp(0.0, 1.0)),
                ],
                Stroke::new(1.0_f32, color),
            );
        } else if active {
            p.circle_filled(start, 1.8, color);
        }
        ui.interact(cell, ui.id().with(("atlas-phase", index)), Sense::hover())
            .on_hover_text(receipts[index].map_or_else(
                || {
                    if active {
                        format!("{} · active; no within-phase count reported", stage.title())
                    } else {
                        format!("{} · no count reported", stage.title())
                    }
                },
                |(done, total)| {
                    format!(
                        "{} · {done}/{total} observed {}",
                        stage.title(),
                        [
                            "alignment input reads",
                            "direct pair attempts",
                            "folded captures",
                            "validated outputs"
                        ][index]
                    )
                },
            ));
    }
}

fn layer_indices(count: usize, selected: Option<usize>) -> Vec<usize> {
    let shown = count.min(LAYER_CAP - 1);
    let mut result: Vec<_> = (0..shown)
        .map(|index| index * count.saturating_sub(1) / shown.saturating_sub(1).max(1))
        .collect();
    if let Some(frame) = selected.filter(|&frame| frame < count) {
        result.push(frame);
    }
    result.sort_unstable();
    result.dedup();
    result
}
fn layer_from_archive(input: &Input<'_>, level: usize, frame: usize) -> Layer {
    let mut layer = Layer {
        frame,
        sequence: None,
        extent: None,
        points: Vec::new(),
        cells: Vec::new(),
        admitted: 0,
        samples: 0,
    };
    let Some((meta, cells)) = input.progress.admission_archive.cells(level, frame) else {
        return layer;
    };
    let positive: Vec<_> = cells
        .enumerate()
        .filter_map(|(index, admitted)| admitted.then_some(index))
        .collect();
    layer.sequence = Some(meta.sequence);
    layer.extent = Some(meta.extent);
    layer.admitted = positive.len();
    layer.samples = meta.samples[0] * meta.samples[1];
    let shown = positive.len().min(POINT_CAP);
    let Some(geometry) = crate::process_sample_glyphs::SampleGeometry::new(level, meta) else {
        return layer;
    };
    for slot in 0..shown {
        if let Some(glyph) = geometry.at(positive[slot * positive.len() / shown]) {
            layer.points.push(glyph.center);
            layer.cells.push(glyph.cell);
        }
    }
    layer
}

fn observed_support(input: &Input<'_>, level: usize, frame: usize, pin: Pos2) -> Option<bool> {
    let (meta, mut cells) = input.progress.admission_archive.cells(level, frame)?;
    let geometry = crate::process_sample_glyphs::SampleGeometry::new(level, meta)?;
    cells.nth(geometry.observed_index_at(pin)?)
}
fn capture_depth(frame: usize, count: usize) -> f32 {
    0.08 + 0.92 * (frame + 1) as f32 / count.max(1) as f32
}
fn capture_color(frame: usize) -> Color32 {
    [
        ACCENT,
        GREEN,
        Color32::from_rgb(123, 170, 222),
        AMBER,
        Color32::from_rgb(178, 150, 218),
        Color32::from_rgb(100, 188, 183),
    ][frame % 6]
}
fn quad_uv(quad: [Pos2; 4], point: Pos2) -> Option<Pos2> {
    let x = quad[1] - quad[0];
    let y = quad[3] - quad[0];
    let at = point - quad[0];
    let det = x.x * y.y - x.y * y.x;
    if det.abs() < 0.0001 {
        return None;
    }
    let uv = egui::pos2(
        (at.x * y.y - at.y * y.x) / det,
        (x.x * at.y - x.y * at.x) / det,
    );
    (uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0).then_some(uv)
}
fn pick_scene(
    pointer: Pos2,
    front: [Pos2; 4],
    photograph: bool,
    samples: &[(Pick, Pos2)],
) -> Option<Pick> {
    if photograph && let Some(uv) = quad_uv(front, pointer) {
        return Some(Pick::Photograph(uv));
    }
    samples
        .iter()
        .rev()
        .filter(|(_, at)| at.distance(pointer) < 5.0)
        .min_by(|(_, a), (_, b)| a.distance(pointer).total_cmp(&b.distance(pointer)))
        .map(|(pick, _)| *pick)
}
fn wire(p: &Painter, quad: [Pos2; 4], color: Color32, width: f32) {
    for index in 0..4 {
        p.line_segment(
            [quad[index], quad[(index + 1) % 4]],
            Stroke::new(width, color),
        );
    }
}
fn image_quad(p: &Painter, texture: &TextureHandle, quad: [Pos2; 4], color: Color32) {
    let mut mesh = egui::Mesh::with_texture(texture.id());
    for (pos, uv) in quad.into_iter().zip([
        egui::pos2(0.0, 0.0),
        egui::pos2(1.0, 0.0),
        egui::pos2(1.0, 1.0),
        egui::pos2(0.0, 1.0),
    ]) {
        mesh.vertices.push(egui::epaint::Vertex { pos, uv, color });
    }
    mesh.indices.extend([0, 1, 2, 0, 2, 3]);
    p.add(egui::Shape::mesh(mesh));
}
fn label(p: &Painter, at: Pos2, text: &str, size: f32, color: Color32) {
    p.text(
        at,
        Align2::LEFT_TOP,
        text,
        FontId::proportional(size),
        color,
    );
}
fn button(ui: &mut Ui, p: &Painter, rect: Rect, id: &str, text: &str, active: bool) -> bool {
    let hit = ui.interact(rect, ui.id().with(id), Sense::click());
    if hit.hovered() {
        p.rect_filled(rect, 0.0, PANEL);
    }
    p.text(
        rect.center(),
        Align2::CENTER_CENTER,
        text,
        FontId::proportional(10.0),
        if active || hit.hovered() { INK } else { MUTED },
    );
    hit.clicked()
}
fn preview_image(packet: &DiagnosticSurface, range: Option<(f32, f32)>) -> egui::ColorImage {
    let (low, high) = range.unwrap_or((packet.min, packet.max));
    let width = (high - low).max(f32::EPSILON);
    let pixels = packet
        .pixels
        .iter()
        .map(|&value| {
            let physical = packet.min + value as f32 / 255.0 * (packet.max - packet.min);
            let normalized = ((physical - low) / width).clamp(0.0, 1.0);
            Color32::from_gray((normalized.sqrt() * 255.0).round() as u8)
        })
        .collect();
    egui::ColorImage::new([packet.width, packet.height], pixels)
}

#[cfg(test)]
#[path = "process-atlas-tests.rs"]
mod tests;
