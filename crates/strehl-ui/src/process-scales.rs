//! The complete multiscale merge, visible simultaneously. Row sizes describe
//! sample spacing in photograph pixels when the output geometry is known.
use crate::{
    pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticSurface, Stage},
    process_output_space::{detail_label, detail_tooltip},
    process_space::{Input, Surface, SurfaceMeta},
    theme::{ACCENT, AMBER, BG, GREEN, INK, LINE, MUTED, PANEL},
};
use eframe::egui::{
    self, Align2, Color32, FontId, Painter, Pos2, Rect, Sense, Stroke, TextureHandle, Ui,
};
use std::{cell::RefCell, sync::Arc};

const KINDS: [DiagnosticKind; 5] = [
    DiagnosticKind::FocusEnergy,
    DiagnosticKind::GateFloor,
    DiagnosticKind::GateSupport,
    DiagnosticKind::Averaging,
    DiagnosticKind::Coefficient,
];
const MAX_SURFACES: usize = 384;

#[cfg(test)]
#[path = "process-scales-v26-tests.rs"]
mod v26_tests;

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct ScaleInspection {
    pub level: usize,
    pub kind: DiagnosticKind,
    pub uv: Pos2,
    pub enlarge: bool,
    pub reset: bool,
}
/// User intent only: texture deliveries and animation intermediates are never
/// pushed into navigation history.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct ScaleView {
    pin: Pos2,
    zoom: f32,
    selected: Option<(usize, DiagnosticKind)>,
}
#[derive(Clone, Copy)]
pub(crate) struct ScalePort {
    pub level: usize,
    pub position: Pos2,
    pub observed: bool,
    pub folded: usize,
}
struct Snapshot {
    level: usize,
    frame: Option<usize>,
    meta: SurfaceMeta,
    texture: TextureHandle,
    packet: Option<DiagnosticSurface>,
    previous: Option<TextureHandle>,
    previous_packet: Option<DiagnosticSurface>,
    binary: RefCell<BinaryPane>,
    previous_binary: RefCell<BinaryPane>,
    arrived: f64,
    alpha: f32,
    pending: Option<PendingSnapshot>,
}
struct PendingSnapshot {
    frame: Option<usize>,
    meta: SurfaceMeta,
    texture: TextureHandle,
    packet: Option<DiagnosticSurface>,
}
impl Snapshot {
    fn replace(&mut self, next: PendingSnapshot, now: f64) {
        self.previous = Some(std::mem::replace(&mut self.texture, next.texture));
        self.frame = next.frame;
        self.meta = next.meta;
        self.previous_packet = std::mem::replace(&mut self.packet, next.packet);
        self.previous_binary = std::mem::take(&mut self.binary);
        self.arrived = now;
        self.alpha = 0.0;
    }
}
pub(crate) struct ProcessScales {
    epoch: Option<u64>,
    domain_epoch: u64,
    snapshots: Vec<Snapshot>,
    pin: Pos2,
    selected: Option<(usize, DiagnosticKind)>,
    ports: Vec<ScalePort>,
    local: bool,
    magnification: f32,
    zoom_target: f32,
    zoom_from: f32,
    zoom_started: f64,
    now: f64,
    zoom_anchor: Option<(Pos2, Pos2)>,
    reset_origin: Option<Pos2>,
    region_motion: Option<(Pos2, Pos2)>,
    painted_pin: Pos2,
    painted_aperture: Rect,
    drag: Option<((usize, DiagnosticKind), Pos2)>,
    interaction_hovered: bool,
}
impl Default for ProcessScales {
    fn default() -> Self {
        Self {
            epoch: None,
            domain_epoch: 0,
            snapshots: Vec::new(),
            pin: egui::pos2(0.5, 0.5),
            selected: None,
            ports: Vec::new(),
            local: false,
            magnification: 1.0,
            zoom_target: 1.0,
            zoom_from: 1.0,
            zoom_started: 0.0,
            now: 0.0,
            zoom_anchor: None,
            reset_origin: None,
            region_motion: None,
            painted_pin: egui::pos2(0.5, 0.5),
            painted_aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            drag: None,
            interaction_hovered: false,
        }
    }
}

#[derive(Clone, Copy)]
struct Layout {
    rect: Rect,
    top: f32,
    row_height: f32,
    label_width: f32,
    column_width: f32,
}
impl Layout {
    fn new(rect: Rect, count: usize) -> Self {
        let label_width = (rect.width() * 0.14).clamp(70.0, 100.0);
        Self {
            rect,
            top: rect.top() + 62.0,
            row_height: ((rect.height() - 87.0) / count.max(1) as f32).max(1.0),
            label_width,
            column_width: (rect.width() - label_width - 14.0) / 5.0,
        }
    }
    fn row(self, level: usize) -> Rect {
        Rect::from_min_size(
            egui::pos2(self.rect.left(), self.top + level as f32 * self.row_height),
            egui::vec2(self.rect.width(), self.row_height),
        )
    }
    fn cell(self, level: usize, column: usize) -> Rect {
        Rect::from_min_size(
            egui::pos2(
                self.rect.left() + self.label_width + column as f32 * self.column_width,
                self.top + level as f32 * self.row_height,
            ),
            egui::vec2(self.column_width - 8.0, (self.row_height - 5.0).max(2.0)),
        )
    }
}

impl ProcessScales {
    pub(crate) fn view(&self) -> ScaleView {
        let pin = if let Some((_, target)) = self.region_motion {
            target
        } else if self.reset_origin.is_some() {
            egui::pos2(0.5, 0.5)
        } else if let Some((physical, anchor)) = self.zoom_anchor {
            clamp_center(
                physical + (egui::vec2(0.5, 0.5) - anchor.to_vec2()) / self.zoom_target,
                self.zoom_target.recip(),
            )
        } else {
            self.pin
        };
        ScaleView {
            pin,
            zoom: self.zoom_target,
            selected: self.selected,
        }
    }
    pub(crate) fn restore_view(&mut self, view: ScaleView) {
        self.set_view(view.pin, view.zoom);
        self.selected = view.selected;
        self.drag = None;
    }
    pub(crate) fn focus_pin(&mut self) {
        if !self.local {
            self.set_detail_zoom(4.0);
        }
    }
    pub(crate) fn focus_region(&mut self, region: Rect) {
        if !region.is_finite() || region.width() <= 0.0 || region.height() <= 0.0 {
            return;
        }
        let zoom = region.width().max(region.height()).recip().clamp(1.0, 16.0);
        let origin = self.painted_pin;
        self.pin = clamp_center(region.center(), zoom.recip());
        self.retarget(zoom);
        self.region_motion = Some((origin, self.pin));
    }
    pub(crate) fn detail_zoom(&self) -> f32 {
        self.zoom_target
    }
    pub(crate) fn painted_pin(&self) -> Pos2 {
        self.painted_pin
    }
    pub(crate) fn interaction_hovered(&self) -> bool {
        self.interaction_hovered
    }
    pub(crate) fn set_detail_zoom(&mut self, zoom: f32) {
        if zoom.is_finite() {
            self.retarget(zoom.clamp(2.0, 16.0));
        }
    }
    pub(crate) fn reset_view(&mut self) {
        self.retarget(1.0);
        self.reset_origin = Some(self.pin);
        self.drag = None;
    }
    /// Direct manipulation commits geometry without an easing lag. The painted
    /// snapshot stays unchanged until the next show, keeping linked views equal.
    pub(crate) fn set_view(&mut self, pin: Pos2, zoom: f32) {
        if !zoom.is_finite() || !pin.x.is_finite() || !pin.y.is_finite() {
            return;
        }
        let zoom = zoom.clamp(1.0, 16.0);
        self.retarget(zoom);
        self.magnification = zoom;
        self.zoom_from = zoom;
        self.pin = clamp_center(pin, zoom.recip());
    }
    /// `anchor` is the pointer's normalized position within the rendered map.
    /// Hold its physical sample stationary throughout the zoom reveal.
    pub(crate) fn zoom_at(&mut self, factor: f32, anchor: Pos2) {
        self.zoom_at_minimum(factor, anchor, 2.0);
    }
    /// Finished-image navigation uses continuous magnification down to Scene.
    pub(crate) fn zoom_photo_at(&mut self, factor: f32, anchor: Pos2) {
        self.zoom_at_minimum(factor, anchor, 1.0);
    }
    fn zoom_at_minimum(&mut self, factor: f32, anchor: Pos2, minimum: f32) {
        if !factor.is_finite() || factor <= 0.0 || !anchor.x.is_finite() || !anchor.y.is_finite() {
            return;
        }
        let anchor = egui::pos2(anchor.x.clamp(0.0, 1.0), anchor.y.clamp(0.0, 1.0));
        let physical = self.painted_aperture.min + self.painted_aperture.size() * anchor.to_vec2();
        let next = (self.zoom_target * factor).clamp(minimum, 16.0);
        if (!self.local && factor <= 1.0) || next == self.zoom_target {
            return;
        }
        self.retarget(next);
        self.zoom_anchor = Some((physical, anchor));
    }
    fn retarget(&mut self, zoom: f32) {
        self.local = zoom > 1.0;
        self.zoom_target = zoom;
        self.zoom_from = self.magnification;
        self.zoom_started = self.now;
        self.zoom_anchor = None;
        self.reset_origin = None;
        self.region_motion = None;
    }
    fn advance_view(&mut self, now: f64) {
        self.now = now;
        let t = ((now - self.zoom_started) / 0.18).clamp(0.0, 1.0) as f32;
        let eased = t * t * (3.0 - 2.0 * t);
        self.magnification = self.zoom_from + (self.zoom_target - self.zoom_from) * eased;
        if let Some((origin, target)) = self.region_motion {
            self.pin = clamp_center(origin.lerp(target, eased), self.magnification.recip());
        } else if let Some((physical, anchor)) = self.zoom_anchor {
            let center = physical + (egui::vec2(0.5, 0.5) - anchor.to_vec2()) / self.magnification;
            self.pin = clamp_center(center, self.magnification.recip());
        } else if let Some(origin) = self.reset_origin {
            self.pin = origin.lerp(egui::pos2(0.5, 0.5), eased);
        }
        if t >= 1.0 {
            self.zoom_anchor = None;
            self.reset_origin = None;
            self.region_motion = None;
        }
    }
    pub(crate) fn select_level(&mut self, level: usize) {
        self.selected = Some((level, DiagnosticKind::GateSupport));
    }
    pub(crate) fn pin(&self) -> Pos2 {
        self.pin
    }
    pub(crate) fn set_pin(&mut self, pin: Pos2) {
        if pin.x.is_finite() && pin.y.is_finite() && pin != self.pin {
            self.pin = egui::pos2(pin.x.clamp(0.0, 1.0), pin.y.clamp(0.0, 1.0));
            self.zoom_anchor = None;
            self.reset_origin = None;
            self.region_motion = None;
        }
    }
    pub(crate) fn output_ports(&self) -> &[ScalePort] {
        &self.ports
    }
    /// Inspect precisely the generation currently being revealed in this ledger,
    /// even if the transport has already supplied a later deferred generation.
    pub(crate) fn presented_surfaces(&self) -> Vec<Surface<'_>> {
        self.snapshots
            .iter()
            .map(|item| Surface {
                epoch: self.epoch.unwrap_or(0),
                stage: Stage::Merge,
                level: item.level,

                texture: &item.texture,

                frame: item.frame,
                meta: Some(item.meta),
                packet: item.packet.as_ref(),
            })
            .collect()
    }
    pub(crate) fn transitioning(&self) -> bool {
        (self.magnification - self.zoom_target).abs() > 0.0001
            || self.reset_origin.is_some()
            || self.region_motion.is_some()
            || self
                .snapshots
                .iter()
                .any(|snapshot| snapshot.previous.is_some() || snapshot.pending.is_some())
    }

    /// Advance the shared photograph view even when the full matrix is hidden.
    /// Every linked image reads this frame-stable snapshot; image gestures only
    /// change the target that the next frame will publish.
    pub(crate) fn prepare_frame(&mut self, ui: &Ui, input: &Input<'_>) {
        if self.epoch != Some(input.epoch) || self.domain_epoch != input.progress.diagnostic_epoch {
            *self = Self {
                epoch: Some(input.epoch),
                domain_epoch: input.progress.diagnostic_epoch,
                ..Default::default()
            };
        }
        let now = ui.input(|state| state.time);
        self.advance_view(now);
        self.receive(input, now);
        let mut repaint = false;
        for item in &mut self.snapshots {
            if item.previous.is_some() {
                let t = ((now - item.arrived) / 0.2).clamp(0.0, 1.0) as f32;
                item.alpha = t * t * (3.0 - 2.0 * t);
                if t >= 1.0 {
                    item.previous = None;
                    item.previous_packet = None;
                    item.previous_binary = Default::default();
                }
                repaint = true;
            }
            if item.previous.is_none()
                && let Some(next) = item.pending.take()
            {
                item.replace(next, now);
                repaint = true;
            }
        }
        if repaint || self.transitioning() {
            ui.ctx().request_repaint();
        }
        self.painted_pin = self.pin;
        self.painted_aperture = view_aperture(self.pin, self.magnification);
        self.interaction_hovered = false;
        if !ui.input(|state| state.pointer.primary_down()) || !gestures_allowed(ui) {
            self.drag = None;
        }
    }

    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
    ) -> Option<ScaleInspection> {
        self.prepare_frame(ui, input);
        let count = self.row_count(input);
        let layout = Layout::new(rect, count);
        self.ports.clear();
        self.header(ui, layout, input);
        self.painted_pin = self.pin;
        self.painted_aperture = view_aperture(self.pin, self.magnification);
        self.interaction_hovered = false;
        let mut inspection = None;
        for level in 0..count {
            self.row_identity(ui, layout, level, input);
            for (column, kind) in KINDS.into_iter().enumerate() {
                if let Some(pick) = self.map(ui, layout.cell(level, column), level, kind, input) {
                    inspection = Some(pick);
                }
                if matches!(
                    kind,
                    DiagnosticKind::GateSupport | DiagnosticKind::Averaging
                ) {
                    self.mask_trace(ui, layout.cell(level, column), level, kind, input);
                }
            }
            self.connections(ui, layout, level);
            let accumulated = self.get(level, DiagnosticKind::Coefficient);
            self.ports.push(ScalePort {
                level,
                position: accumulated.map_or_else(
                    || layout.cell(level, 4).right_center(),
                    |item| {
                        fit(map_extent(item, input), map_aperture(layout.cell(level, 4)))
                            .right_center()
                    },
                ),
                observed: accumulated.is_some(),
                folded: accumulated.map_or(0, |item| item.meta.folded),
            });
        }
        let p = ui.painter_at(rect);
        label(
            &p,
            egui::pos2(rect.left(), rect.bottom() - 14.0),
            "Whole-field mask area · frame / prefix traces",
            8.0,
            INK,
        );
        p.text(
            egui::pos2(rect.right(), rect.bottom() - 14.0),
            Align2::RIGHT_TOP,
            "Double-click: fit · right-click: actions",
            FontId::proportional(8.0),
            MUTED,
        );
        if let Some(selected) = inspection {
            if selected.reset {
                self.reset_view();
                self.selected = None;
            } else {
                self.set_pin(selected.uv);
                self.selected = Some((selected.level, selected.kind));
                self.focus_pin();
            }
        }
        if !ui.input(|state| state.pointer.primary_down()) || !gestures_allowed(ui) {
            self.drag = None;
        }
        if self.transitioning() || inspection.is_some() {
            ui.ctx().request_repaint();
        }
        inspection
    }

    fn row_count(&self, input: &Input<'_>) -> usize {
        let observed = self
            .snapshots
            .iter()
            .map(|item| item.level + 1)
            .max()
            .unwrap_or(0)
            .max(
                input
                    .progress
                    .merge_bands
                    .keys()
                    .next_back()
                    .map_or(0, |level| level + 1),
            );
        // Until the engine reports its configuration, this is an explicitly
        // labelled default sketch, not observed work or an asserted band count.
        input
            .progress
            .bands
            .map_or(8, |bands| bands.saturating_add(1))
            .max(observed)
            .clamp(1, 64)
    }
    fn get(&self, level: usize, kind: DiagnosticKind) -> Option<&Snapshot> {
        self.snapshots
            .iter()
            .find(|item| item.level == level && item.meta.kind == kind)
    }
    fn receive(&mut self, input: &Input<'_>, now: f64) {
        for surface in input
            .surfaces
            .iter()
            .filter(|surface| surface.epoch == input.epoch && surface.level < 64)
        {
            let Some(meta) = surface.meta.filter(|meta| KINDS.contains(&meta.kind)) else {
                continue;
            };
            let matches = |packet: &&DiagnosticSurface| {
                packet.sequence == meta.sequence
                    && packet.level == surface.level
                    && packet.kind == meta.kind
                    && packet.scale == meta.scale
            };
            let packet = surface
                .packet
                .filter(matches)
                .or_else(|| input.progress.diagnostic_surfaces.iter().find(matches))
                .cloned();
            let incoming = PendingSnapshot {
                frame: surface.frame,
                meta,
                texture: surface.texture.clone(),
                packet,
            };
            if let Some(old) = self
                .snapshots
                .iter_mut()
                .find(|item| item.level == surface.level && item.meta.kind == meta.kind)
            {
                if meta.sequence <= old.meta.sequence
                    || old
                        .pending
                        .as_ref()
                        .is_some_and(|pending| meta.sequence <= pending.meta.sequence)
                {
                    continue;
                }
                if old.previous.is_some() {
                    old.pending = Some(incoming);
                    continue;
                }
                old.replace(incoming, now);
            } else {
                if self.snapshots.len() == MAX_SURFACES {
                    let index = self
                        .snapshots
                        .iter()
                        .enumerate()
                        .min_by_key(|(_, item)| item.meta.sequence)
                        .unwrap()
                        .0;
                    self.snapshots.remove(index);
                }
                self.snapshots.push(Snapshot {
                    level: surface.level,
                    frame: surface.frame,
                    meta,
                    texture: surface.texture.clone(),
                    packet: incoming.packet,
                    previous: None,
                    previous_packet: None,
                    binary: Default::default(),
                    previous_binary: Default::default(),
                    arrived: now,
                    alpha: 1.0,
                    pending: None,
                });
            }
        }
    }

    fn header(&mut self, ui: &mut Ui, layout: Layout, input: &Input<'_>) {
        let p = ui.painter_at(layout.rect);
        let control = Rect::from_min_size(
            egui::pos2(layout.rect.right() - 83.0, layout.rect.top() + 2.0),
            egui::vec2(83.0, 20.0),
        );
        let hit = ui.interact(control, ui.id().with("diagnostic-zoom"), Sense::click());
        if hit.clicked() && gestures_allowed(ui) {
            if self.local {
                self.reset_view();
            } else {
                self.focus_pin();
            }
        }
        p.line_segment(
            [control.left_bottom(), control.right_bottom()],
            Stroke::new(1.0_f32, if self.local { ACCENT } else { LINE }),
        );
        p.text(
            control.center(),
            Align2::CENTER_CENTER,
            if self.local {
                format!("{:.1}× · SCENE", self.detail_zoom())
            } else {
                "SCENE / 1×".into()
            },
            FontId::monospace(8.0),
            if hit.hovered() { INK } else { MUTED },
        );
        hit.on_hover_text("Return to the full scene, or focus the shared pin. Scroll or pinch a map to zoom; drag to move the image. Every map and both photograph lenses use the same region. Double-click any map to reset; right-click to inspect it large.");
        label(
            &p.with_clip_rect(Rect::from_min_max(
                layout.rect.min,
                egui::pos2(control.left() - 6.0, layout.rect.bottom()),
            )),
            layout.rect.min + egui::vec2(0.0, 6.0),
            "HOW DETAIL BECOMES THE PHOTOGRAPH",
            11.0,
            INK,
        );
        let subtitle = input.progress.bands.map_or(
            "Scale plan pending · default layout shown".into(),
            |count| format!("{count} detail sizes + broad tone · every row contributes"),
        );
        label(
            &p,
            layout.rect.min + egui::vec2(0.0, 24.0),
            &subtitle,
            8.5,
            MUTED,
        );
        for (column, title) in [
            "TEXTURE",
            "NOISE LIMIT",
            "ADMITTED",
            "FALLBACK",
            "ACCUMULATED",
        ]
        .into_iter()
        .enumerate()
        {
            let cell = layout.cell(0, column);
            p.text(
                egui::pos2(cell.center().x, layout.rect.top() + 43.0),
                Align2::CENTER_CENTER,
                title,
                FontId::proportional(8.5),
                if column == 2 || column == 4 {
                    GREEN
                } else if column == 1 || column == 3 {
                    AMBER
                } else {
                    INK
                },
            );
        }
        p.line_segment(
            [
                egui::pos2(layout.rect.left(), layout.top - 6.0),
                egui::pos2(layout.rect.right(), layout.top - 6.0),
            ],
            Stroke::new(1.0_f32, LINE),
        );
    }

    fn row_identity(&self, ui: &mut Ui, layout: Layout, level: usize, input: &Input<'_>) {
        let row = layout.row(level);
        let p = ui.painter_at(row);
        let base = input.progress.bands == Some(level);
        let active = input.progress.stage == Stage::Merge
            && input.progress.merge_step_state == Some(crate::pipeline::WorkState::Started)
            && input.progress.merge_step_level == Some(level);
        p.rect_filled(
            row.shrink2(egui::vec2(0.0, 1.0)),
            0.0,
            if self.selected.is_some_and(|(selected, _)| selected == level) {
                crate::theme::RAISED
            } else if level.is_multiple_of(2) {
                PANEL
            } else {
                BG
            },
        );
        let dense = layout.row_height < 40.0;
        if layout.row_height > 12.0 {
            label(
                &p,
                row.min + egui::vec2(4.0, 3.0),
                scale_name(level, base),
                if dense { 8.0 } else { 9.0 },
                if active { ACCENT } else { INK },
            );
        }
        if layout.row_height > 30.0 {
            let spacing = if base {
                "residual".to_owned()
            } else {
                detail_label(level, input.progress.output_geometry)
            };
            let detail = if dense {
                input.progress.merge_bands.get(&level).map_or_else(
                    || spacing.clone(),
                    |work| format!("{spacing} · {}/{}", work.completed, work.total),
                )
            } else {
                spacing
            };
            label(&p, row.min + egui::vec2(4.0, 18.0), &detail, 7.0, MUTED);
        }
        let gauge_y = row.bottom() - 5.0;
        let progress_bar = Rect::from_min_size(
            egui::pos2(row.left() + 4.0, gauge_y),
            egui::vec2(layout.label_width - 17.0, 3.0),
        );
        p.rect_filled(progress_bar, 0.0, LINE);
        if let Some(work) = input.progress.merge_bands.get(&level) {
            let fraction = work.completed as f32 / work.total.max(1) as f32;
            p.rect_filled(
                Rect::from_min_size(
                    progress_bar.min,
                    egui::vec2(progress_bar.width() * fraction.clamp(0.0, 1.0), 3.0),
                ),
                0.0,
                GREEN,
            );
            if !dense {
                label(
                    &p,
                    row.min + egui::vec2(4.0, 29.0),
                    &format!("{}/{} folds", work.completed, work.total),
                    7.0,
                    GREEN,
                );
            }
        } else if !dense {
            label(
                &p,
                row.min + egui::vec2(4.0, 29.0),
                "awaiting work",
                7.0,
                MUTED,
            );
        }
        let info = format!(
            "{}\n{}\n{}",
            scale_name(level, base),
            detail_tooltip(level, input.progress.output_geometry),
            if base {
                "Broad tone is the Gaussian residual; it has no independent focus-energy election."
            } else {
                "This octave is the difference between a blurred level and its expanded next-coarser level."
            }
        );
        ui.interact(
            Rect::from_min_size(row.min, egui::vec2(layout.label_width - 8.0, row.height())),
            ui.id().with(("scale-identity", level)),
            Sense::hover(),
        )
        .on_hover_text(info);
    }

    fn map(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        level: usize,
        kind: DiagnosticKind,
        input: &Input<'_>,
    ) -> Option<ScaleInspection> {
        let p = ui.painter_at(rect);
        let dense = rect.height() < 60.0;
        let image_box = map_aperture(rect);
        let Some(snapshot) = self.get(level, kind) else {
            let base = input.progress.bands == Some(level);
            let no_election = base
                && matches!(
                    kind,
                    DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor
                );
            if no_election && rect.height() > 12.0 {
                p.text(
                    rect.center(),
                    Align2::CENTER_CENTER,
                    "not elected",
                    FontId::proportional(7.0),
                    MUTED,
                );
            } else {
                p.rect_stroke(
                    image_box,
                    0.0,
                    Stroke::new(0.6_f32, LINE),
                    egui::StrokeKind::Inside,
                );
                p.text(
                    image_box.center(),
                    Align2::CENTER_CENTER,
                    "·",
                    FontId::monospace(10.0),
                    MUTED,
                );
            }
            return None;
        };
        let scope = snapshot.frame.map_or_else(
            || format!("{} frames", snapshot.meta.folded),
            |frame| format!("frame {}", frame + 1),
        );
        if rect.height() >= 18.0 && !dense {
            p.text(
                egui::pos2(rect.center().x, rect.top() + 2.0),
                Align2::CENTER_TOP,
                &scope,
                FontId::proportional(7.0),
                MUTED,
            );
        }
        let extent = map_extent(snapshot, input);
        let fitted = fit(extent, image_box);
        let aperture = self.aperture();
        let binary = matches!(
            kind,
            DiagnosticKind::GateSupport | DiagnosticKind::Averaging
        );
        if binary {
            p.rect_filled(fitted, 0.0, BG);
            if let Some(extent) = input.progress.analysis_size.or(input.progress.plane_size) {
                let color = if kind == DiagnosticKind::GateSupport {
                    GREEN
                } else {
                    AMBER
                };
                if let Some(previous) = &snapshot.previous_packet {
                    snapshot.previous_binary.borrow_mut().paint(
                        &p,
                        fitted,
                        aperture,
                        previous,
                        extent,
                        color.gamma_multiply(1.0 - snapshot.alpha),
                    );
                }
                if let Some(packet) = &snapshot.packet {
                    snapshot.binary.borrow_mut().paint(
                        &p,
                        fitted,
                        aperture,
                        packet,
                        extent,
                        color.gamma_multiply(snapshot.alpha),
                    );
                }
            }
        } else {
            if let Some(previous) = &snapshot.previous {
                p.image(previous.id(), fitted, aperture, Color32::WHITE);
            }
            p.image(
                snapshot.texture.id(),
                fitted,
                aperture,
                Color32::from_white_alpha((snapshot.alpha * 255.0).round() as u8),
            );
        }
        if dense && rect.height() >= 18.0 {
            let compact = snapshot.frame.map_or_else(
                || format!("{}Σ", snapshot.meta.folded),
                |frame| format!("F{:03}", frame + 1),
            );
            let caption = p.layout_no_wrap(compact, FontId::monospace(6.5), INK);
            let backing = Rect::from_min_size(fitted.min, caption.size() + egui::vec2(3.0, 2.0));
            p.rect_filled(backing, 0.0, Color32::from_black_alpha(210));
            p.galley(backing.min + egui::vec2(1.5, 0.5), caption, INK);
        }
        let binary_counts = if binary {
            let mut retained = snapshot.binary.borrow_mut();
            retained.prepare(
                snapshot.packet.as_ref(),
                input.progress.analysis_size.or(input.progress.plane_size),
            );
            retained.counts
        } else {
            None
        };
        if let Some((on, samples)) = binary_counts
            && fitted.height() >= 20.0
        {
            let color = if kind == DiagnosticKind::GateSupport {
                GREEN
            } else {
                AMBER
            };
            let badge = p.layout_no_wrap(
                format!("{:.0}%", on as f32 * 100.0 / samples as f32),
                FontId::monospace(6.5),
                color,
            );
            let size = badge.size() + egui::vec2(3.0, 1.0);
            if size.x <= fitted.width() && size.y <= fitted.height() {
                let backing = Rect::from_min_size(fitted.right_bottom() - size, size);
                p.rect_filled(backing, 0.0, Color32::from_black_alpha(220));
                p.galley(backing.min + egui::vec2(1.5, 0.0), badge, color);
            }
        }
        let pin =
            fitted.min + ((self.painted_pin - aperture.min) / aperture.size()) * fitted.size();
        p.circle_stroke(pin, 2.0, Stroke::new(0.7_f32, Color32::WHITE));
        if self.selected == Some((level, kind)) {
            p.rect_stroke(
                fitted.expand(1.0),
                0.0,
                Stroke::new(1.0_f32, ACCENT),
                egui::StrokeKind::Outside,
            );
        }
        if !dense {
            let value = snapshot.packet.as_ref().and_then(|packet| {
                nearest_value_at(
                    packet,
                    self.painted_pin,
                    input.progress.analysis_size.or(input.progress.plane_size),
                )
            });
            let text = match (kind, value) {
                (DiagnosticKind::GateSupport | DiagnosticKind::Averaging, Some(value)) => {
                    if value > 0.5 {
                        "ON".into()
                    } else {
                        "OFF".into()
                    }
                }
                (_, Some(value)) => format!("≈ {value:.1e} {}", kind.units()),
                _ => "sample unavailable".into(),
            };
            p.text(
                egui::pos2(rect.center().x, rect.bottom() - 8.0),
                Align2::CENTER_TOP,
                text,
                FontId::monospace(6.8),
                if kind == DiagnosticKind::Coefficient {
                    GREEN
                } else {
                    MUTED
                },
            );
        }
        let response = ui
            .interact(
                fitted,
                ui.id().with(("scale-map", level, kind as u8)),
                Sense::click_and_drag(),
            )
            .on_hover_cursor(if self.local {
                egui::CursorIcon::Grab
            } else {
                egui::CursorIcon::Crosshair
            });
        let note = if response.hovered() {
            let sampled = binary_counts.map_or_else(String::new, |(on, samples)| format!("\n{on}/{samples} observed samples are ON ({:.0}%). Points mark the observations; corner marks show coefficient spacing. Gaps are unsampled.", on as f32 * 100.0 / samples as f32));
            let point = snapshot
                .packet
                .as_ref()
                .and_then(|packet| {
                    nearest_value_at(
                        packet,
                        self.painted_pin,
                        input.progress.analysis_size.or(input.progress.plane_size),
                    )
                })
                .map_or_else(
                    || "Point value unavailable".to_owned(),
                    |value| format!("Nearest observed sample: ≈ {value:.3e} {}", kind.units()),
                );
            format!(
                "{} · {} · {scope}\n{} × {} nearest samples; physical range {:.2e}…{:.2e} {}.\n{point}\n{}{sampled}\nScroll / pinch to zoom · drag to move · click to pin · double-click to reset · right-click for actions",
                scale_name(level, input.progress.bands == Some(level)),
                kind.title(),
                snapshot.meta.samples[0],
                snapshot.meta.samples[1],
                snapshot.meta.min,
                snapshot.meta.max,
                kind.units(),
                meaning(kind)
            )
        } else {
            String::new()
        };
        let mut selected = None;
        let reset_gesture = crate::image_gesture::reset(ui, &response);
        if reset_gesture.reset {
            self.drag = None;
            return Some(ScaleInspection {
                level,
                kind,
                uv: self.pin,
                enlarge: false,
                reset: true,
            });
        }
        if gestures_allowed(ui) {
            self.interaction_hovered |= response.hovered() || response.dragged();
            if response.hovered()
                && !reset_gesture.pending
                && let Some(at) = response.hover_pos()
            {
                let factor = detail_zoom_factor(ui);
                if factor != 1.0 {
                    let anchor = ((at - fitted.min) / fitted.size()).to_pos2();
                    if input.output.is_some()
                        && input.output_size.is_some_and(|size| {
                            crate::process_output_space::OutputSpace::from_progress(
                                input.progress,
                                size,
                            )
                            .is_some()
                        })
                    {
                        self.zoom_photo_at(factor, anchor);
                    } else {
                        self.zoom_at(factor, anchor);
                    }
                    ui.ctx().request_repaint();
                }
            }
            if response.is_pointer_button_down_on()
                && ui.input(|state| state.pointer.primary_pressed())
                && let Some(at) = response.interact_pointer_pos()
            {
                self.drag = Some(((level, kind), at));
            }
            if response.dragged()
                && !reset_gesture.pending
                && self.local
                && let Some(at) = response.interact_pointer_pos()
                && let Some((key, last)) = self.drag
                && key == (level, kind)
            {
                let delta = at - last;
                self.drag = Some((key, at));
                if delta != egui::Vec2::ZERO {
                    let center = aperture.center() - delta / fitted.size() * aperture.size();
                    self.set_view(
                        clamp_center(center, aperture.width()),
                        aperture.width().recip(),
                    );
                    selected = Some(ScaleInspection {
                        level,
                        kind,
                        uv: self.pin,
                        enlarge: false,
                        reset: false,
                    });
                }
                ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
            } else if response.clicked()
                && !reset_gesture.pending
                && let Some(at) = response.interact_pointer_pos()
            {
                let uv = aperture.min + (at - fitted.min) / fitted.size() * aperture.size();
                selected = Some(ScaleInspection {
                    level,
                    kind,
                    uv: egui::pos2(uv.x.clamp(0.0, 1.0), uv.y.clamp(0.0, 1.0)),
                    enlarge: false,
                    reset: false,
                });
            }
        }
        response.context_menu(|ui| {
            ui.label(format!("{} · {}", scale_name(level, false), kind.title()));
            ui.separator();
            let shared_photograph = input.output.is_some()
                && input.output_size.is_some_and(|size| {
                    crate::process_output_space::OutputSpace::from_progress(input.progress, size)
                        .is_some()
                });
            if ui
                .button(if shared_photograph {
                    "Overlay on photograph"
                } else if input.output.is_some() {
                    "Inspect map alongside photograph"
                } else {
                    "Inspect large"
                })
                .clicked()
            {
                selected = Some(ScaleInspection {
                    level,
                    kind,
                    uv: self.pin,
                    enlarge: true,
                    reset: false,
                });
                ui.close();
            }
            if ui.button("Fit all linked views").clicked() {
                selected = Some(ScaleInspection {
                    level,
                    kind,
                    uv: self.pin,
                    enlarge: false,
                    reset: true,
                });
                ui.close();
            }
            if ui.button("Set linked zoom to 4×").clicked() {
                self.set_detail_zoom(4.0);
                ui.close();
            }
        });
        response.on_hover_text(note);
        selected
    }

    pub(crate) fn aperture(&self) -> Rect {
        self.painted_aperture
    }

    fn mask_trace(
        &self,
        ui: &mut Ui,
        cell: Rect,
        level: usize,
        kind: DiagnosticKind,
        input: &Input<'_>,
    ) {
        let Some(history) = input
            .progress
            .sampled_mask_history
            .iter()
            .find(|history| history.level == level && history.kind == kind)
        else {
            return;
        };
        if cell.height() < 10.0 || cell.width() < 4.0 {
            return;
        }
        let rect = trace_rect(cell);
        let p = ui.painter_at(cell);
        let columns = history
            .bins
            .len()
            .min(rect.width().floor().max(1.0) as usize);
        let color = if kind == DiagnosticKind::GateSupport {
            GREEN
        } else {
            AMBER
        };
        p.rect_filled(rect, 0.0, LINE.gamma_multiply(0.4));
        for column in 0..columns {
            let start = column * history.bins.len() / columns;
            let end = (column + 1) * history.bins.len() / columns;
            let (on, samples) = history.bins[start..end]
                .iter()
                .fold((0u64, 0u64), |(on, samples), bin| {
                    (on + bin.on_samples, samples + bin.samples)
                });
            if samples == 0 {
                continue;
            }
            let alpha = 0.3 + 0.7 * on as f32 / samples as f32;
            let mark = Rect::from_min_max(
                egui::pos2(
                    rect.left() + rect.width() * column as f32 / columns as f32,
                    rect.top(),
                ),
                egui::pos2(
                    rect.left() + rect.width() * (column + 1) as f32 / columns as f32,
                    rect.bottom(),
                ),
            );
            p.rect_filled(mark, 0.0, color.gamma_multiply(alpha));
        }
        if let Some(snapshot) = self.get(level, kind) {
            let index = if kind == DiagnosticKind::GateSupport {
                snapshot.frame
            } else {
                snapshot.meta.folded.checked_sub(1)
            };
            if let Some(index) = index.filter(|&index| index < history.total) {
                let x = rect.left() + rect.width() * (index as f32 + 0.5) / history.total as f32;
                p.line_segment(
                    [egui::pos2(x, rect.top()), egui::pos2(x, rect.bottom())],
                    Stroke::new(1.0_f32, INK),
                );
            }
        }
        let response = ui.interact(
            rect.expand2(egui::vec2(0.0, 1.0)),
            ui.id().with(("sampled-mask-trace", level, kind as u8)),
            Sense::hover(),
        );
        if let Some(pointer) = response.hover_pos() {
            let column = (((pointer.x - rect.left()) / rect.width()).clamp(0.0, 0.999_999)
                * columns as f32) as usize;
            let start = column * history.bins.len() / columns;
            let end = (column + 1) * history.bins.len() / columns;
            let range = history.range(start).start..history.range(end - 1).end;
            let (on, samples, observed) = history.bins[start..end].iter().fold(
                (0u64, 0u64, 0usize),
                |(on, samples, observed), bin| {
                    (
                        on + bin.on_samples,
                        samples + bin.samples,
                        observed + bin.observations(),
                    )
                },
            );
            let axis = if kind == DiagnosticKind::GateSupport {
                "captures"
            } else {
                "accepted prefixes"
            };
            let fraction = if samples == 0 {
                "No sampled mask received".into()
            } else {
                format!(
                    "{on}/{samples} nearest samples ON · {:.0}%",
                    on as f32 * 100.0 / samples as f32
                )
            };
            response.on_hover_text(format!("{} · {axis} {}–{}\n{observed}/{} masks observed here · {}/{} total\n{fraction}\nGaps are unobserved. Marks group at this zoom; the line identifies the displayed map.", kind.title(), range.start + 1, range.end, range.len(), history.observations(), history.total));
        }
    }

    fn connections(&self, ui: &mut Ui, layout: Layout, level: usize) {
        let p = ui.painter_at(layout.row(level));
        let matched = self.frame_inputs_match(level);
        let cells = std::array::from_fn::<_, 5, _>(|column| layout.cell(level, column));
        // Energy and noise are inputs, not a sequential transformation. The
        // observed support and the accumulated fallback are separate branches.
        let comparison = egui::pos2(
            (cells[0].right() + cells[1].left()) * 0.5,
            cells[0].center().y,
        );
        let join = if matched { ACCENT } else { LINE };
        // These are compared, never added. Keep the connector in the gutter.
        p.text(
            comparison,
            Align2::CENTER_CENTER,
            "vs",
            FontId::monospace(6.0),
            join,
        );
        arrow(
            &p,
            cells[1].right_center(),
            cells[2].left_center() - egui::vec2(1.0, 0.0),
            if matched { ACCENT } else { LINE },
        );
        let merge_matches = self
            .get(level, DiagnosticKind::Averaging)
            .zip(self.get(level, DiagnosticKind::Coefficient))
            .is_some_and(|(fallback, band)| fallback.meta.folded == band.meta.folded);
        let gate = egui::pos2(
            (cells[2].right() + cells[3].left()) * 0.5,
            cells[2].center().y,
        );
        // A local gate marks the complementary branches. No long bypass under
        // the fallback map: that suggested data skipped the map entirely.
        let gate_color = if merge_matches { GREEN } else { LINE };
        let r = 3.0;
        p.circle_stroke(gate, r, Stroke::new(0.7_f32, gate_color));
        p.line_segment(
            [gate - egui::vec2(1.4, 0.0), gate + egui::vec2(1.4, 0.0)],
            Stroke::new(0.7_f32, gate_color),
        );
        p.line_segment(
            [gate - egui::vec2(0.0, 1.4), gate + egui::vec2(0.0, 1.4)],
            Stroke::new(0.7_f32, gate_color),
        );
        arrow(
            &p,
            cells[3].right_center(),
            cells[4].left_center() - egui::vec2(1.0, 0.0),
            gate_color,
        );
        ui.interact(
            Rect::from_center_size(gate, egui::vec2(8.0, 14.0)),
            ui.id().with(("fallback-gate", level)),
            Sense::hover(),
        ).on_hover_text("Gated combination: positive-weight detail where supported; the fallback rule supplies samples with no positive-weight denominator. These masks show the branches, not numerical weights to add.");
        // These are operator paths, not an assertion that E > floor is the
        // full admission rule. Positive weight is observed independently.
    }
    fn frame_inputs_match(&self, level: usize) -> bool {
        let frames = [
            DiagnosticKind::FocusEnergy,
            DiagnosticKind::GateFloor,
            DiagnosticKind::GateSupport,
        ]
        .map(|kind| self.get(level, kind).and_then(|item| item.frame));
        frames[0].is_some() && frames.iter().all(|frame| *frame == frames[0])
    }
}

fn scale_name(level: usize, base: bool) -> &'static str {
    if base {
        return "Broad tone";
    }
    match level {
        0 => "Fine texture",
        1 => "Texture",
        2 => "Small edges",
        3 => "Edges",
        4 => "Small forms",
        5 => "Forms",
        _ => "Broad forms",
    }
}
fn meaning(kind: DiagnosticKind) -> &'static str {
    match kind {
        DiagnosticKind::FocusEnergy => {
            "Measured green-band focus energy in one source. Colours use this map's own logarithmic range."
        }
        DiagnosticKind::GateFloor => {
            "Propagated injected noise floor for the same scale. Energy and floor alone do not describe the complete weight rule."
        }
        DiagnosticKind::GateSupport => {
            "Observed binary support: this source's computed weight is positive. It is not weight magnitude or a winning-frame map."
        }
        DiagnosticKind::Averaging => {
            "Observed accumulated fallback mask: no positive-weight denominator at this point. This is not always a simple mean."
        }
        DiagnosticKind::Coefficient => {
            "Accumulated green coefficients at this size. Combining all sizes reconstructs the green plane before colour development."
        }
        DiagnosticKind::Preview => {
            "Live coarse green, before final reconstruction bounds and colour development."
        }
        DiagnosticKind::Reconstructed => "Reconstructed green plane.",
    }
}
#[cfg(test)]
fn value_at(packet: &DiagnosticSurface, pin: Pos2) -> Option<f32> {
    let x = ((pin.x * packet.width as f32) as usize).min(packet.width.checked_sub(1)?);
    let y = ((pin.y * packet.height as f32) as usize).min(packet.height.checked_sub(1)?);
    value_index(packet, y * packet.width + x)
}
fn nearest_value_at(
    packet: &DiagnosticSurface,
    pin: Pos2,
    extent: Option<[usize; 2]>,
) -> Option<f32> {
    let extent = extent?;
    let geometry = crate::process_sample_glyphs::SampleGeometry::new(
        packet.level,
        crate::process_provenance::AdmissionMeta {
            sequence: packet.sequence,
            samples: [packet.width, packet.height],
            extent,
        },
    )?;
    value_index(packet, geometry.nearest_index_at(pin)?)
}
fn value_index(packet: &DiagnosticSurface, index: usize) -> Option<f32> {
    let t = *packet.pixels.get(index)? as f32 / 255.0;
    Some(match packet.scale {
        DiagnosticScale::Linear => packet.min + t * (packet.max - packet.min),
        DiagnosticScale::Log => (packet.min.max(0.0).ln_1p()
            + t * (packet.max.max(0.0).ln_1p() - packet.min.max(0.0).ln_1p()))
        .exp_m1(),
        DiagnosticScale::Symmetric => {
            let value = (2.0 * t - 1.0) * packet.min.abs().max(packet.max.abs()).ln_1p();
            value.signum() * value.abs().exp_m1()
        }
    })
}
fn mask_counts(packet: &DiagnosticSurface) -> Option<(usize, usize)> {
    if !matches!(
        packet.kind,
        DiagnosticKind::GateSupport | DiagnosticKind::Averaging
    ) || packet.scale != DiagnosticScale::Linear
        || packet.min != 0.0
        || packet.max != 1.0
        || packet.pixels.is_empty()
        || packet.pixels.len() != packet.width.checked_mul(packet.height)?
        || packet
            .pixels
            .iter()
            .any(|&value| value != 0 && value != 255)
    {
        return None;
    }
    Some((
        packet.pixels.iter().filter(|&&value| value == 255).count(),
        packet.pixels.len(),
    ))
}

/// Owned by one immutable snapshot generation. A reveal moves this cache with
/// its old packet; a replacement starts a new cache. Pointer motion can then
/// reuse validated observations, geometry, and the actual submitted mesh.
#[derive(Default)]
struct BinaryPane {
    prepared_extent: Option<Option<[usize; 2]>>,
    counts: Option<(usize, usize)>,
    glyphs: Vec<crate::process_sample_glyphs::SampleGlyph>,
    key: Option<BinaryDrawKey>,
    mesh: Arc<egui::Mesh>,
    #[cfg(test)]
    preparations: usize,
    #[cfg(test)]
    builds: usize,
}

#[derive(PartialEq)]
struct BinaryDrawKey {
    image: Rect,
    aperture: Rect,
    density: crate::process_sample_glyphs::Density,
    color: Color32,
    pixels_per_point: f32,
}

impl BinaryPane {
    fn prepare(&mut self, packet: Option<&DiagnosticSurface>, extent: Option<[usize; 2]>) {
        if self.prepared_extent == Some(extent) {
            return;
        }
        self.prepared_extent = Some(extent);
        self.counts = packet.and_then(mask_counts);
        self.glyphs.clear();
        self.key = None;
        self.mesh = Default::default();
        #[cfg(test)]
        {
            self.preparations += 1;
        }
        if self.counts.is_none() {
            return;
        }
        if let (Some(packet), Some(extent)) = (packet, extent)
            && let Some(geometry) = crate::process_sample_glyphs::SampleGeometry::new(
                packet.level,
                crate::process_provenance::AdmissionMeta {
                    sequence: packet.sequence,
                    samples: [packet.width, packet.height],
                    extent,
                },
            )
        {
            self.glyphs.extend(
                packet
                    .pixels
                    .iter()
                    .enumerate()
                    .filter_map(|(index, &value)| {
                        (value == 255).then(|| geometry.at(index)).flatten()
                    }),
            );
        }
    }

    fn paint(
        &mut self,
        painter: &Painter,
        image: Rect,
        aperture: Rect,
        packet: &DiagnosticSurface,
        extent: [usize; 2],
        color: Color32,
    ) {
        self.prepare(Some(packet), Some(extent));
        if !image.is_finite()
            || !image.is_positive()
            || !aperture.is_finite()
            || !aperture.is_positive()
        {
            return;
        }
        let density = crate::process_sample_glyphs::Density::read(painter.ctx());
        let key = BinaryDrawKey {
            image,
            aperture,
            density,
            color,
            pixels_per_point: painter.ctx().pixels_per_point(),
        };
        if self.key.as_ref() != Some(&key) {
            use crate::process_sample_glyphs::Density;
            let mut mesh = egui::Mesh::default();
            let visible = || {
                self.glyphs
                    .iter()
                    .filter(|glyph| glyph.cell.intersects(aperture))
            };
            let (area, maximum) = match density {
                Density::Quiet => (24.0, 512),
                Density::Balanced => (12.0, 2048),
                Density::Full => (4.0, 128 * 96),
            };
            let cap = ((image.area() / area) as usize).clamp(24, maximum);
            let stride = visible().count().div_ceil(cap).max(1);
            for glyph in visible().step_by(stride) {
                append_binary_glyph(
                    &mut mesh,
                    image,
                    aperture,
                    *glyph,
                    color.gamma_multiply(0.88),
                    key.pixels_per_point,
                );
            }
            self.mesh = Arc::new(mesh);
            self.key = Some(key);
            #[cfg(test)]
            {
                self.builds += 1;
            }
        }
        if !self.mesh.is_empty() {
            painter
                .with_clip_rect(painter.clip_rect().intersect(image))
                .add(egui::Shape::Mesh(Arc::clone(&self.mesh)));
        }
    }
}

fn append_binary_glyph(
    mesh: &mut egui::Mesh,
    image: Rect,
    aperture: Rect,
    glyph: crate::process_sample_glyphs::SampleGlyph,
    ink: Color32,
    pixels_per_point: f32,
) {
    let project = |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
    let center = project(glyph.center);
    let cell = Rect::from_min_max(project(glyph.cell.min), project(glyph.cell.max));
    if image.contains(center) {
        const UNIT: [[f32; 2]; 8] = [
            [1.0, 0.0],
            [0.70710677, 0.70710677],
            [0.0, 1.0],
            [-0.70710677, 0.70710677],
            [-1.0, 0.0],
            [-0.70710677, -0.70710677],
            [0.0, -1.0],
            [0.70710677, -0.70710677],
        ];
        let start = mesh.vertices.len() as u32;
        mesh.colored_vertex(center, ink);
        for offset in UNIT {
            mesh.colored_vertex(center + egui::Vec2::from(offset) * 1.05, ink);
        }
        let feather = 0.65 / pixels_per_point.max(0.1);
        for offset in UNIT {
            mesh.colored_vertex(
                center + egui::Vec2::from(offset) * (1.05 + feather),
                Color32::TRANSPARENT,
            );
        }
        for i in 0..8u32 {
            let next = (i + 1) % 8;
            mesh.add_triangle(start, start + 1 + i, start + 1 + next);
            mesh.add_triangle(start + 1 + i, start + 9 + i, start + 9 + next);
            mesh.add_triangle(start + 1 + i, start + 9 + next, start + 1 + next);
        }
    }
    if cell.width().min(cell.height()) >= 2.0 {
        let tick = (cell.width().min(cell.height()) * 0.24).min(7.0);
        for (corner, direction) in [
            (cell.left_top(), egui::Vec2::splat(1.0)),
            (cell.right_top(), egui::vec2(-1.0, 1.0)),
            (cell.right_bottom(), egui::Vec2::splat(-1.0)),
            (cell.left_bottom(), egui::vec2(1.0, -1.0)),
        ] {
            for delta in [
                egui::vec2(direction.x * tick, 0.0),
                egui::vec2(0.0, direction.y * tick),
            ] {
                let normal = delta.normalized().rot90() * 0.5;
                let start = mesh.vertices.len() as u32;
                for at in [
                    corner + normal,
                    corner - normal,
                    corner + delta + normal,
                    corner + delta - normal,
                ] {
                    mesh.colored_vertex(at, ink);
                }
                mesh.add_triangle(start, start + 1, start + 2);
                mesh.add_triangle(start + 1, start + 3, start + 2);
            }
        }
    }
}
fn trace_rect(cell: Rect) -> Rect {
    Rect::from_min_max(
        egui::pos2(cell.left() + 2.0, cell.bottom() - 2.0),
        cell.max - egui::vec2(2.0, 0.0),
    )
}
fn map_aperture(rect: Rect) -> Rect {
    let (header, footer) = if rect.height() >= 60.0 {
        (12.0, 10.0)
    } else if rect.height() >= 6.0 {
        (2.0, 2.0)
    } else {
        (0.0, 0.0)
    };
    Rect::from_min_max(
        rect.min + egui::vec2(2.0, header),
        rect.max - egui::vec2(2.0, footer),
    )
}
fn map_extent(snapshot: &Snapshot, input: &Input<'_>) -> egui::Vec2 {
    input
        .progress
        .analysis_size
        .or(input.progress.plane_size)
        .filter(|size| !size.contains(&0))
        .map_or_else(
            || snapshot.texture.size_vec2(),
            |size| egui::vec2(size[0] as f32, size[1] as f32),
        )
}
fn fit(extent: egui::Vec2, rect: Rect) -> Rect {
    let scale = (rect.width() / extent.x)
        .min(rect.height() / extent.y)
        .max(0.0);
    Rect::from_center_size(rect.center(), extent * scale)
}
fn view_aperture(pin: Pos2, magnification: f32) -> Rect {
    let side = magnification.recip();
    Rect::from_center_size(clamp_center(pin, side), egui::vec2(side, side))
}
pub(crate) fn clamp_center(pin: Pos2, side: f32) -> Pos2 {
    let half = side * 0.5;
    egui::pos2(pin.x.clamp(half, 1.0 - half), pin.y.clamp(half, 1.0 - half))
}
fn gestures_allowed(ui: &Ui) -> bool {
    ui.is_enabled()
        && ui.input(|state| {
            state.focused
                && state.viewport().focused != Some(false)
                && state.viewport().minimized != Some(true)
        })
        && !egui::Popup::is_any_open(ui.ctx())
        && ui
            .ctx()
            .memory(|memory| memory.is_above_modal_layer(ui.layer_id()))
}
/// Raw gestures are consumed once, without egui's scroll-coasting tail or a
/// second ctrl-wheel zoom factor. Both map and lens callers require hover.
pub(crate) fn detail_zoom_factor(ui: &Ui) -> f32 {
    ui.input(|state| {
        if let Some(touch) = state.multi_touch() {
            return touch.zoom_delta;
        }
        state.events.iter().fold(1.0, |factor, event| {
            factor
                * match event {
                    egui::Event::Zoom(value) if value.is_finite() && *value > 0.0 => *value,
                    egui::Event::MouseWheel { unit, delta, .. } => {
                        let speed = match unit {
                            egui::MouseWheelUnit::Point => 0.006,
                            egui::MouseWheelUnit::Line => 0.18,
                            egui::MouseWheelUnit::Page => 0.8,
                        };
                        (delta.y * speed).clamp(-3.0, 3.0).exp()
                    }
                    _ => 1.0,
                }
        })
    })
}
fn label(p: &Painter, at: Pos2, value: &str, size: f32, color: Color32) {
    p.text(
        at,
        Align2::LEFT_TOP,
        value,
        FontId::proportional(size),
        color,
    );
}
fn arrow(p: &Painter, from: Pos2, to: Pos2, color: Color32) {
    p.line_segment([from, to], Stroke::new(0.8_f32, color));
    p.line_segment([to - egui::vec2(3.0, 2.0), to], Stroke::new(0.8_f32, color));
    p.line_segment(
        [to - egui::vec2(3.0, -2.0), to],
        Stroke::new(0.8_f32, color),
    );
}

#[cfg(test)]
#[path = "process-scales-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "process-scales-region-motion-tests.rs"]
mod region_motion_tests;
