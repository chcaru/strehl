//! A persistent photographic instrument. Every coloured mark is an observation;
//! animation only reveals delivered pixels, never estimates engine work.
#[path = "process-review-strip.rs"]
mod review_strip;
#[path = "process-source-admission.rs"]
mod source_admission;

use crate::{
    pipeline::{DiagnosticKind, DiagnosticScale, Stage},
    process_space::{Input, Response, SurfaceMeta},
    theme::{ACCENT, GREEN, INK, LINE, MUTED, PANEL},
    viewer::preview_aperture,
    workbench::PhotoSlot,
};
use eframe::egui::{
    self, Align2, Color32, FontId, Painter, Pos2, Rect, Sense, Stroke, TextureHandle, Ui, Vec2,
};
#[cfg(test)]
#[path = "workspace-layout-review-tests.rs"]
mod workspace_layout_review_tests;

#[cfg(test)]
const SIGNALS: [DiagnosticKind; 5] = [
    DiagnosticKind::FocusEnergy,
    DiagnosticKind::GateFloor,
    DiagnosticKind::GateSupport,
    DiagnosticKind::Averaging,
    DiagnosticKind::Coefficient,
];

#[derive(Clone)]
struct Observation {
    texture: TextureHandle,
    meta: SurfaceMeta,
    level: usize,
    frame: Option<usize>,
    // Keep the bounded observer packet with its delivered image. The
    // transport queue may roll over long before the user inspects a result.
    packet: Option<crate::pipeline::DiagnosticSurface>,
}

#[derive(Clone)]
struct Plate {
    texture: TextureHandle,
    extent: Vec2,
    uv: Rect,
    kind: u8, // original camera, accumulated band, green reconstruction, owned TIFF
    sequence: u64,
    level: usize,
    folded: usize,
    tonal: bool,
}
struct Reveal {
    plate: Plate,
    previous: Option<Plate>,
    start: f64,
    alpha: f32,
}

#[derive(Clone, PartialEq)]
struct Exploration {
    source: Option<usize>,
    enlarged: Option<DiagnosticKind>,
    signal: DiagnosticKind,
    level: usize,
    level_touched: bool,
    scales: crate::process_scales::ScaleView,
    zoom: f32,
    pan: Vec2,
    source_zoom: f32,
    source_pan: Vec2,
    selection: crate::process_participation::SelectionState,
    layout: crate::workspace_layout::WorkspaceLayout,
}

pub(crate) struct ProcessTheater {
    pub(crate) layout: crate::workspace_layout::WorkspaceLayout,
    epoch: Option<u64>,
    domain_epoch: u64,
    source_index: Option<usize>,
    inspected_source: Option<usize>,
    // A cursor visit is a modifier of the photograph, never a journal entry.
    hover_source: Option<usize>,
    inspection_mix: f32,
    source_relation_rect: Option<Rect>,
    source_axis_bounds: Option<Rect>,
    review_hover: Option<usize>,
    review_strip_visible: bool,
    source: Option<PhotoSlot>,
    inspection: Option<PhotoSlot>,
    source_zoom: f32,
    source_pan: Vec2,
    source_relation_mix: f32,
    source_relation_axis: Option<SourceRelationAxis>,
    source_admission: source_admission::SourceAdmissionCache,
    dense_admission: crate::process_admission_regions::DenseAdmissionCache,
    source_region_painter: crate::process_admission_regions::DenseRegionPainter,
    source_selection_painter: crate::process_admission_regions::DenseSelectionPainter,
    source_drag: Option<(Pos2, Pos2, f32)>,
    pair: [Option<PhotoSlot>; 2],
    observations: Vec<Observation>,
    hero: Option<Reveal>,
    hero_pending: bool,
    saved_output: Option<TextureHandle>,
    saved_output_size: Option<[u32; 2]>,
    result_photo: crate::process_result::ResultPhoto,
    pub(crate) photo_paint: Option<crate::photo_viewport::PhotoPaint>,
    participation: crate::process_participation::CaptureParticipation,
    participation_frame: Option<usize>,
    participation_held: bool,
    completion_started: Option<f64>,
    completion_mix: f32,
    preview_range: Option<(f32, f32)>,
    preview_tone: Option<(u64, TextureHandle)>,
    scales: crate::process_scales::ProcessScales,
    level: usize,
    level_touched: bool,
    selected_signal: DiagnosticKind,
    enlarged: Option<DiagnosticKind>,
    pin: Pos2,
    zoom: f32,
    pan: Vec2,
    last_stage: Stage,
    visible_contacts: Vec<usize>,
    latest_preview: Option<Plate>,
    preview_generation: Option<u64>,
    contributions: crate::process_contribution::ContributionLenses,
    contribution_hovered: bool,
    retained_admission: Option<(
        crate::process_provenance::AdmissionMeta,
        crate::pipeline::DiagnosticSurface,
    )>,
    navigator: crate::process_navigator::DetailNavigator,
    ledger: crate::process_ledger::ProcessLedger,
    revisions: crate::process_revision::RevisionField,
    revision_view: crate::process_revision_view::RevisionView,
    show_revisions: bool,
    review_network: bool,
    undo: Vec<Exploration>,
    redo: Vec<Exploration>,
    gesture_start: Option<Exploration>,
    wheel_edit: Option<f64>,
    primary_destination: Option<Rect>,
    pub(crate) edit_mapping: Option<(Rect, Rect)>,
    pub(crate) annotation_mode: bool,
    pub(crate) edit_focus: bool,
    pub(crate) requested_view: Option<(Pos2, f32)>,
    history_revision: u64,
    history_commits: u64,
    restored: bool,
}
impl Default for ProcessTheater {
    fn default() -> Self {
        Self {
            layout: Default::default(),
            epoch: None,
            domain_epoch: 0,
            source_index: None,
            inspected_source: None,
            hover_source: None,
            inspection_mix: 0.0,
            source_relation_rect: None,
            source_axis_bounds: None,
            review_hover: None,
            review_strip_visible: false,
            source: None,
            inspection: None,
            source_zoom: 1.0,
            source_pan: Vec2::ZERO,
            source_relation_mix: 0.0,
            source_relation_axis: None,
            source_admission: Default::default(),
            dense_admission: Default::default(),
            source_region_painter: Default::default(),
            source_selection_painter: Default::default(),
            source_drag: None,
            pair: [None, None],
            observations: Vec::new(),
            hero: None,
            hero_pending: false,
            saved_output: None,
            saved_output_size: None,
            result_photo: Default::default(),
            photo_paint: None,
            participation: Default::default(),
            participation_frame: None,
            participation_held: false,
            completion_started: None,
            completion_mix: 0.0,
            preview_range: None,
            preview_tone: None,
            scales: Default::default(),
            level: 0,
            level_touched: false,
            selected_signal: DiagnosticKind::GateSupport,
            enlarged: None,
            pin: egui::pos2(0.5, 0.5),
            zoom: 1.0,
            pan: Vec2::ZERO,
            last_stage: Stage::Preparing,
            visible_contacts: Vec::new(),
            latest_preview: None,
            preview_generation: None,
            contributions: Default::default(),
            contribution_hovered: false,
            retained_admission: None,
            navigator: Default::default(),
            ledger: Default::default(),
            revisions: Default::default(),
            revision_view: Default::default(),
            show_revisions: true,
            review_network: false,
            undo: Vec::new(),
            redo: Vec::new(),
            gesture_start: None,
            wheel_edit: None,
            primary_destination: None,
            edit_mapping: None,
            annotation_mode: false,
            edit_focus: false,
            requested_view: None,
            history_revision: 0,
            history_commits: 0,
            restored: false,
        }
    }
}

#[derive(Clone, Copy)]
struct Layout {
    title: Rect,
    hero: Rect,
    origins: [Rect; 2],
    network: Rect,
    ledger: Rect,
    history: Rect,
    contributions: Rect,
    weave: Rect,
    signals: Rect,
}
impl Layout {
    fn configured(
        rect: Rect,
        complete: bool,
        mut prefs: crate::workspace_layout::WorkspaceLayout,
    ) -> Self {
        prefs.constrain_width(rect.width());
        let mut layout = if complete {
            Self::completed(rect)
        } else {
            Self::new(rect)
        };
        let map_x = |region: &mut Rect, old_a: f32, old_b: f32, new_a: f32, new_b: f32| {
            for x in [&mut region.min.x, &mut region.max.x] {
                *x = new_a + (*x - old_a) / (old_b - old_a) * (new_b - new_a);
            }
        };
        let x = |fraction: f32| rect.left() + rect.width() * fraction;
        if complete {
            for region in [&mut layout.signals, &mut layout.weave] {
                map_x(
                    region,
                    rect.left(),
                    x(0.44),
                    rect.left(),
                    x(prefs.final_detail),
                );
            }
            for region in [&mut layout.title, &mut layout.hero, &mut layout.history] {
                map_x(
                    region,
                    x(0.44) + 24.0,
                    rect.right(),
                    x(prefs.final_detail) + 24.0,
                    rect.right(),
                );
            }
            if rect.height() >= 576.0 {
                map_x(
                    &mut layout.contributions,
                    rect.left(),
                    x(0.44),
                    rect.left(),
                    x(prefs.final_detail),
                );
            } else {
                map_x(
                    &mut layout.contributions,
                    x(0.44) + 24.0,
                    rect.right(),
                    x(prefs.final_detail) + 24.0,
                    rect.right(),
                );
            }
        } else {
            for region in [
                &mut layout.network,
                &mut layout.ledger,
                &mut layout.origins[0],
            ] {
                map_x(region, rect.left(), x(0.20), rect.left(), x(prefs.network));
            }
            map_x(
                &mut layout.origins[1],
                rect.left(),
                x(0.20),
                rect.left(),
                x(prefs.network),
            );
            for region in [&mut layout.signals, &mut layout.weave] {
                map_x(
                    region,
                    x(0.20) + 16.0,
                    x(0.61),
                    x(prefs.network) + 16.0,
                    x(prefs.detail),
                );
            }
            for region in [
                &mut layout.title,
                &mut layout.hero,
                &mut layout.contributions,
                &mut layout.history,
            ] {
                map_x(
                    region,
                    x(0.61) + 24.0,
                    rect.right(),
                    x(prefs.detail) + 24.0,
                    rect.right(),
                );
            }
        }
        let dy = rect.height() * prefs.lower;
        // Enlarge history upward; keep enough photograph to remain useful.
        let shift = dy.clamp(
            48.0 - layout.history.height(),
            (layout.hero.height() - 150.0).max(0.0),
        );
        layout.history.min.y -= shift;
        if complete && rect.height() >= 576.0 {
            layout.hero.max.y -= shift;
        } else {
            layout.contributions = layout.contributions.translate(egui::vec2(0.0, -shift));
            layout.hero.max.y -= shift;
        }
        let tail =
            (rect.height() * prefs.fingerprint).min((layout.signals.height() - 235.0).max(0.0));
        layout.signals.max.y -= tail;
        layout.weave.min.y -= tail;
        layout
    }
    fn compact_instruments(rect: Rect, complete: bool) -> Self {
        let mut layout = Self::new(rect);
        let matrix_top = rect.top() + if complete { 0.0 } else { 326.0 };
        layout.network = Rect::from_min_size(rect.min, egui::vec2(176.0, 226.0));
        layout.ledger = Rect::from_min_max(
            rect.min + egui::vec2(188.0, 0.0),
            egui::pos2(rect.right(), rect.top() + 306.0),
        );
        layout.origins = [0, 1].map(|index| {
            Rect::from_min_size(
                rect.min + egui::vec2(index as f32 * 90.0, 238.0),
                egui::vec2(86.0, 68.0),
            )
        });
        layout.signals = Rect::from_min_max(
            egui::pos2(rect.left(), matrix_top),
            egui::pos2(rect.right(), matrix_top + 426.0),
        );
        layout.weave = Rect::from_min_max(
            egui::pos2(rect.left(), matrix_top + 440.0),
            egui::pos2(rect.right(), matrix_top + 558.0),
        );
        layout.contributions =
            Rect::from_min_max(egui::pos2(rect.left(), matrix_top + 572.0), rect.max);
        layout
    }

    fn reveal(self, target: Self, t: f32) -> Self {
        let between =
            |a: Rect, b: Rect| Rect::from_min_max(a.min.lerp(b.min, t), a.max.lerp(b.max, t));
        Self {
            title: between(self.title, target.title),
            hero: between(self.hero, target.hero),
            signals: between(self.signals, target.signals),
            weave: between(self.weave, target.weave),
            contributions: between(self.contributions, target.contributions),
            history: between(self.history, target.history),
            ..self
        }
    }
    fn completed(rect: Rect) -> Self {
        let mut layout = Self::new(rect);
        let divide = rect.left() + rect.width() * 0.44;
        let right = divide + 24.0;
        layout.signals.min.x = rect.left();
        layout.signals.max.x = divide;
        layout.weave.min.x = rect.left();
        layout.weave.max.x = divide;
        for region in [
            &mut layout.title,
            &mut layout.hero,
            &mut layout.contributions,
            &mut layout.history,
        ] {
            region.min.x = right;
        }
        // A finished photograph owns the right-hand column. On a tall canvas,
        // keep the two spatial witnesses beside their maps instead of consuming
        // the photograph's height. Compact windows retain readable map rows.
        if rect.height() >= 576.0 {
            layout.signals.max.y = rect.bottom() - 238.0;
            layout.weave = Rect::from_min_max(
                egui::pos2(rect.left(), rect.bottom() - 226.0),
                egui::pos2(divide, rect.bottom() - 124.0),
            );
            layout.contributions = Rect::from_min_max(
                egui::pos2(rect.left(), rect.bottom() - 112.0),
                egui::pos2(divide, rect.bottom()),
            );
            layout.history.min.y = rect.bottom() - 54.0;
            layout.hero.max.y = layout.history.top() - 12.0;
        }
        layout
    }
    fn new(rect: Rect) -> Self {
        let network_right = rect.left() + rect.width() * 0.20;
        let signal_left = network_right + 16.0;
        let signal_right = rect.left() + rect.width() * 0.61;
        let right = Rect::from_min_max(egui::pos2(signal_right + 24.0, rect.top()), rect.max);
        let pair_height = 80.0;
        let pair_top = rect.bottom() - pair_height;
        let pair_width = (network_right - rect.left() - 8.0) * 0.5;
        let ledger_bottom = pair_top - 12.0;
        let ledger_top = ledger_bottom - (rect.height() * 0.29).clamp(180.0, 208.0);
        let expanded = ((rect.height() - 470.0) / 190.0).clamp(0.0, 1.0);
        let history_top = rect.bottom() - (54.0 + 16.0 * expanded);
        let contribution_bottom = history_top - 12.0;
        let contribution_top = contribution_bottom - (80.0 + 68.0 * expanded);
        Self {
            title: Rect::from_min_max(right.min, right.min + egui::vec2(right.width(), 35.0)),
            hero: Rect::from_min_max(
                right.min + egui::vec2(0.0, 40.0),
                egui::pos2(right.right(), contribution_top - 12.0),
            ),
            origins: [0, 1].map(|i| {
                Rect::from_min_size(
                    egui::pos2(rect.left() + i as f32 * (pair_width + 8.0), pair_top),
                    egui::vec2(pair_width, pair_height),
                )
            }),
            network: Rect::from_min_max(rect.min, egui::pos2(network_right, ledger_top - 12.0)),
            ledger: Rect::from_min_max(
                egui::pos2(rect.left(), ledger_top),
                egui::pos2(network_right, ledger_bottom),
            ),
            contributions: Rect::from_min_max(
                egui::pos2(right.left(), contribution_top),
                egui::pos2(right.right(), contribution_bottom),
            ),
            history: Rect::from_min_max(egui::pos2(right.left(), history_top), right.max),
            signals: Rect::from_min_max(
                egui::pos2(signal_left, rect.top()),
                egui::pos2(signal_right, rect.bottom() - 122.0),
            ),
            weave: Rect::from_min_max(
                egui::pos2(signal_left, rect.bottom() - 110.0),
                egui::pos2(signal_right, rect.bottom()),
            ),
        }
    }
}

/// Inspection gives almost all available area to the linked photographs.
/// It leaves a small, directly selectable band signature in place of the atlas.
fn inspection_layout(rect: Rect) -> (Rect, Rect, Rect, Rect) {
    let rail_width = (rect.width() * 0.07).clamp(58.0, 82.0);
    let rail = Rect::from_min_max(
        rect.min,
        egui::pos2(rect.left() + rail_width, rect.bottom()),
    );
    let left = rail.right() + 12.0;
    let lenses = (rect.height() * 0.16).clamp(58.0, 100.0);
    let title = Rect::from_min_max(
        egui::pos2(left, rect.top()),
        egui::pos2(rect.right(), rect.top() + 35.0),
    );
    let hero = Rect::from_min_max(
        egui::pos2(left, rect.top() + 40.0),
        egui::pos2(rect.right(), rect.bottom() - lenses - 6.0),
    );
    let contributions = Rect::from_min_max(egui::pos2(left, rect.bottom() - lenses), rect.max);
    (title, hero, contributions, rail)
}

impl ProcessTheater {
    pub(crate) fn set_photo_view(&mut self, center: Pos2, zoom: f32) {
        let before = self.exploration();
        self.resume_live();
        self.scales.set_view(center, zoom.clamp(1.0, 8.0));
        self.pin = self.scales.pin();
        self.requested_view = Some((center, zoom));
        self.remember(before);
    }
    pub(crate) fn set_photo_paint(&mut self, paint: Option<crate::photo_viewport::PhotoPaint>) {
        self.photo_paint = paint.clone();
        self.result_photo.set_photo_paint(paint);
    }
    pub(crate) fn update_balance(
        &mut self,
        ctx: &egui::Context,
        output: Option<&std::path::Path>,
        expected: Option<[usize; 2]>,
    ) {
        self.result_photo.update_balance(ctx, output, expected);
    }
    pub(crate) fn invalidate_balance(&mut self) {
        self.result_photo.invalidate_balance();
    }
    fn exploration(&self) -> Exploration {
        Exploration {
            source: self.inspected_source,
            enlarged: self.enlarged,
            signal: self.selected_signal,
            level: self.level,
            level_touched: self.level_touched,
            scales: self.scales.view(),
            zoom: self.zoom,
            pan: self.pan,
            source_zoom: self.source_zoom,
            source_pan: self.source_pan,
            selection: self.participation.selection(),
            layout: self.layout,
        }
    }
    fn restore(&mut self, view: Exploration) {
        self.requested_view = None;
        self.source_drag = None;
        self.hover_source = None;
        self.inspected_source = view.source;
        self.enlarged = view.enlarged;
        self.selected_signal = view.signal;
        self.level = view.level;
        self.level_touched = view.level_touched;
        self.scales.restore_view(view.scales);
        self.pin = self.scales.pin();
        self.zoom = view.zoom;
        self.pan = view.pan;
        self.source_zoom = view.source_zoom;
        self.source_pan = view.source_pan;
        self.participation.restore_selection(&view.selection);
        self.layout = view.layout;
        self.navigator.clear();
        self.restored = true;
        self.gesture_start = None;
        self.wheel_edit = None;
        self.history_revision = self.history_revision.wrapping_add(1);
    }
    fn remember(&mut self, before: Exploration) {
        if before == self.exploration() {
            return;
        }
        if self.undo.last() != Some(&before) {
            self.undo.push(before);
            self.history_commits = self.history_commits.wrapping_add(1);
            if self.undo.len() > 80 {
                self.undo.remove(0);
            }
        }
        self.redo.clear();
        self.history_revision = self.history_revision.wrapping_add(1);
    }
    pub(crate) fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }
    pub(crate) fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }
    pub(crate) fn history_revision(&self) -> u64 {
        self.history_revision
    }
    pub(crate) fn history_depths(&self) -> (usize, usize) {
        (self.undo.len(), self.redo.len())
    }
    pub(crate) fn history_commits(&self) -> u64 {
        self.history_commits
    }
    pub(crate) fn undo(&mut self) -> bool {
        let Some(before) = self.undo.pop() else {
            return false;
        };
        self.redo.push(self.exploration());
        self.restore(before);
        true
    }
    pub(crate) fn redo(&mut self) -> bool {
        let Some(after) = self.redo.pop() else {
            return false;
        };
        self.undo.push(self.exploration());
        self.restore(after);
        true
    }
    fn fit_views(&mut self) {
        self.result_photo.clear_lenses();
        self.hover_source = None;
        self.result_photo.cancel_gesture();
        self.inspected_source = None;
        self.enlarged = None;
        self.zoom = 1.0;
        self.pan = Vec2::ZERO;
        self.source_zoom = 1.0;
        self.source_pan = Vec2::ZERO;
        self.scales.reset_view();
        self.pin = self.scales.pin();
        self.navigator.clear();
        self.participation.clear();
        self.participation_frame = None;
        self.participation_held = false;
    }
    pub(crate) fn navigation_shortcuts(&mut self, ui: &mut Ui, response: &mut Response) {
        if self.restored {
            crate::image_gesture::clear(ui.ctx());
            response.selected = self.inspected_source;
            response.return_live = self.inspected_source.is_none();
            self.restored = false;
            ui.ctx().request_repaint();
        }
        let allowed = ui.is_enabled() && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()));
        if allowed && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape)) {
            let before = self.exploration();
            self.resume_live();
            self.fit_views();
            self.participation.clear();
            self.remember(before);
            response.return_live = true;
        }
    }
    pub(crate) fn contact_indices(&self) -> Vec<usize> {
        let mut contacts = self.visible_contacts.clone();
        contacts.extend(self.participation.indices());
        contacts
    }
    pub(crate) fn inspection_frame(&self) -> Option<usize> {
        self.hover_source.or(self.inspected_source)
    }
    pub(crate) fn inspecting(&self) -> bool {
        self.inspection_frame().is_some() || self.enlarged.is_some() || self.review_network
    }
    pub(crate) fn resume_live(&mut self) {
        self.result_photo.clear_lenses();
        self.source_drag = None;
        self.hover_source = None;
        self.inspected_source = None;
        self.enlarged = None;
        self.review_network = false;
    }
    pub(crate) fn inspect_frame(&mut self, index: usize) {
        self.hover_source = None;
        self.inspected_source = Some(index);
        self.enlarged = None;
    }

    pub(crate) fn screenshot_ranges(
        &mut self,
        domain: (u64, u64),
        frame_count: usize,
        ranges: &[[usize; 2]],
    ) -> Result<bool, &'static str> {
        if self.epoch != Some(domain.0)
            || self.domain_epoch != domain.1
            || self.saved_output.is_none()
        {
            return Ok(false);
        }
        if !self
            .participation
            .screenshot_ranges(domain, frame_count, ranges)?
        {
            return Ok(false);
        }
        self.resume_live();
        self.participation_frame = ranges.last().map(|range| range[1]);
        self.participation_held = true;
        Ok(true)
    }

    pub(crate) fn review_focus(&mut self, focus: crate::controls::ReviewFocus, selected: usize) {
        self.resume_live();
        match focus {
            crate::controls::ReviewFocus::Captures => {
                self.inspect_frame(selected);
                self.review_network = true;
            }
            crate::controls::ReviewFocus::Coverage => {
                self.scales.reset_view();
                self.pin = self.scales.pin();
                self.zoom = 1.0;
                self.pan = Vec2::ZERO;
            }
            crate::controls::ReviewFocus::Alignment => self.review_network = true,
            crate::controls::ReviewFocus::Blend(level) => {
                self.level = level;
                self.level_touched = true;
                self.scales.select_level(level);
                self.enlarged = Some(DiagnosticKind::Averaging);
            }
        }
    }

    pub(crate) fn transitioning(&self) -> bool {
        self.inspection
            .as_ref()
            .is_some_and(PhotoSlot::needs_repaint)
            || self.source.as_ref().is_some_and(PhotoSlot::needs_repaint)
            || self.pair.iter().flatten().any(PhotoSlot::needs_repaint)
            || self
                .hero
                .as_ref()
                .is_some_and(|hero| hero.previous.is_some())
            || self.hero_pending
            || self.source_relation_mix > 0.0 && self.source_relation_mix < 1.0
            || self.scales.transitioning()
            || self.contributions.transitioning()
            || self.ledger.transitioning()
            || self.completion_started.is_some() && self.completion_mix < 1.0
            || (self.inspection_mix > 0.0 && self.inspection_mix < 1.0)
    }

    #[cfg(test)]
    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        response: &mut Response,
    ) {
        self.show_with_ribbon(ui, rect, input, response, None);
    }

    pub(crate) fn show_with_ribbon(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        response: &mut Response,
        ribbon: Option<Rect>,
    ) {
        let capture_input = input;
        let processing_input = Input {
            frame_count: input.processing_count(),
            ..*input
        };
        let input = &processing_input;
        if self.epoch != Some(input.epoch) {
            let photo_paint = self.photo_paint.clone();
            let requested_view = self.requested_view;
            *self = Self {
                layout: self.layout,
                epoch: Some(input.epoch),
                annotation_mode: self.annotation_mode,
                edit_focus: self.edit_focus,
                ..Default::default()
            };
            self.set_photo_paint(photo_paint);
            if let Some((center, zoom)) = requested_view {
                self.set_photo_view(center, zoom);
            }
        }
        if self.domain_epoch != input.progress.diagnostic_epoch {
            self.domain_epoch = input.progress.diagnostic_epoch;
            self.observations.clear();
            self.hero = None;
            self.hero_pending = false;
            self.preview_range = None;
            self.preview_tone = None;
            self.scales = Default::default();
            self.revisions = Default::default();
            self.revision_view = Default::default();
            self.contributions = Default::default();
            self.retained_admission = None;
            self.latest_preview = None;
            self.preview_generation = None;
            self.pin = egui::pos2(0.5, 0.5);
            self.enlarged = None;
            self.navigator.clear();
            self.level_touched = false;
            self.result_photo = Default::default();
            self.participation.clear();
            self.participation_frame = None;
            self.completion_started = None;
            self.completion_mix = 0.0;
        }
        self.receive(input);
        if let Some(level) = self.result_photo.take_requested_level() {
            self.level = level;
            self.level_touched = true;
            self.scales.select_level(level);
        }
        self.level = self.level.min(self.levels(input) - 1);
        let now = ui.input(|state| state.time);
        self.sync_photos(input, now, ui.ctx());
        self.sync_latest_preview(input, ui.ctx());
        self.sync_hero(input, now, ui.ctx());
        if self.output_space(input).is_some()
            && let Some((center, zoom)) = self.requested_view
        {
            // The first final plate and its diagnostic domain initialize their
            // view clocks above. An explicit incoming crop wins over that
            // automatic Scene placement, before any linked image is painted.
            self.scales.prepare_frame(ui, input);
            self.scales.set_view(center, zoom);
            self.pin = self.scales.pin();
        }
        if input.progress.stage == Stage::Complete && self.last_stage != Stage::Complete {
            self.enlarged = None;
        }
        self.last_stage = input.progress.stage;
        // The same instruments remain beside the photograph after completion.
        // Only the legacy screenshot harness uses the former final-only layout.
        let completed = ribbon.is_none()
            && !self.review_network
            && self.output_space(input).is_some()
            && self
                .hero
                .as_ref()
                .is_some_and(|hero| hero.plate.kind == 3 && hero.previous.is_none());
        let before = self.exploration();
        let pinch = crate::process_region_probe::zoom_delta(ui);
        let (pressed, released, wheel, key) = ui.input(|state| {
            (
                state.pointer.primary_pressed(),
                state.pointer.primary_released(),
                state.raw_scroll_delta != Vec2::ZERO || (pinch - 1.0).abs() > f32::EPSILON,
                state
                    .events
                    .iter()
                    .any(|e| matches!(e, egui::Event::Key { pressed: true, .. })),
            )
        });
        if pressed {
            self.gesture_start = Some(before.clone());
            self.wheel_edit = None;
        }
        self.inspection_mix = ui.ctx().animate_bool_with_time(
            ui.id().with(("inspection-workspace", input.epoch)),
            (self.inspection_frame().is_some() || self.edit_focus)
                && self.output_space(input).is_some(),
            0.24,
        );
        let focused = self.inspection_mix > 0.001;
        let compact = ribbon.is_some() && rect.width() < 1040.0;
        if !compact && !focused {
            self.resize_workspace(ui, rect, completed);
        }
        let mut arrangement = self.layout;
        if ribbon.is_some() {
            arrangement.lower = 0.0;
        }
        let mut layout = if completed {
            let started = *self.completion_started.get_or_insert(now);
            let t = ((now - started) / 0.24).clamp(0.0, 1.0) as f32;
            self.completion_mix = t;
            if t < 1.0 {
                ui.ctx().request_repaint();
            }
            Layout::configured(rect, false, arrangement).reveal(
                Layout::configured(rect, true, arrangement),
                t * t * (3.0 - 2.0 * t),
            )
        } else {
            Layout::configured(rect, false, arrangement)
        };
        if ribbon.is_some() {
            // Reclaim the retired construction rail for the main photograph.
            let reclaimed = rect.bottom() - layout.history.top() + 12.0;
            layout.hero.max.y += reclaimed;
            if !(completed && rect.height() >= 576.0) {
                layout.contributions = layout.contributions.translate(egui::vec2(0.0, reclaimed));
            }
        }
        let instrument_clip = if focused {
            // Inspection suppresses the matrix's drawing, not the shared view
            // clock. Otherwise zoom targets change but neither photo's UV does.
            self.scales.set_pin(self.pin);
            self.scales.prepare_frame(ui, input);
            self.pin = self.scales.pin();
            let mut target = inspection_layout(rect);
            if self.edit_focus {
                // Editing occupies the same continuous photograph and timeline;
                // instruments return when the sidebar focus is released.
                target.0.min.x = rect.left();
                target.1.min.x = rect.left();
                target.1.max.y = rect.bottom();
            }
            let blend = |from: Rect, to: Rect| {
                Rect::from_min_max(
                    from.min.lerp(to.min, self.inspection_mix),
                    from.max.lerp(to.max, self.inspection_mix),
                )
            };
            layout.title = blend(layout.title, target.0);
            layout.hero = blend(layout.hero, target.1);
            layout.contributions = blend(layout.contributions, target.2);
            if !self.edit_focus {
                self.inspection_rail(ui, target.3, input, response);
            }
            None
        } else if compact {
            let split = self.compact_divider(ui, rect);
            let left = Rect::from_min_max(rect.min, egui::pos2(split - 9.0, rect.bottom()));
            layout.title = Rect::from_min_size(
                egui::pos2(split + 10.0, rect.top()),
                egui::vec2(rect.right() - split - 10.0, 35.0),
            );
            layout.hero = Rect::from_min_max(layout.title.min + egui::vec2(0.0, 40.0), rect.max);
            layout.contributions =
                Rect::from_min_max(egui::pos2(split + 10.0, rect.bottom() - 84.0), rect.max);
            ui.scope_builder(egui::UiBuilder::new().max_rect(left), |ui| {
                egui::ScrollArea::both()
                    .id_salt("process-instruments-scroll")
                    .auto_shrink([false, false])
                    .scroll_bar_visibility(egui::scroll_area::ScrollBarVisibility::AlwaysVisible)
                    .show_viewport(ui, |ui, viewport| {
                        let size = egui::vec2(
                            viewport.width().max(382.0),
                            if completed { 684.0 } else { 1010.0 },
                        );
                        let (area, _) = ui.allocate_exact_size(size, Sense::hover());
                        let instruments = Layout::compact_instruments(area, completed);
                        self.instruments(ui, instruments, input, response, completed);
                        self.fingerprint(ui, instruments, input, response);
                        self.contribution(ui, instruments.contributions, input);
                    });
            });
            Some(left)
        } else {
            self.instruments(ui, layout, input, response, completed);
            None
        };
        self.heading(ui, layout.title, input);
        if let Some(ribbon) = ribbon {
            self.timeline_controls(ui, ribbon, capture_input, response);
            let capture = Rect::from_min_max(
                ribbon.min + egui::vec2(0.0, 25.0),
                egui::pos2(
                    ribbon.right(),
                    ribbon
                        .bottom()
                        .max(ribbon.top() + 25.0 + crate::process_participation::HEIGHT),
                ),
            );
            self.participation.set_source_mode(
                input.progress.stage != Stage::Complete
                    && (self.inspected_source.is_some()
                        || (self.hero.is_none() && input.output.is_none())),
            );
            self.participation
                .set_active_source(self.inspection_frame());
            let picked = self.participation.show(
                ui,
                capture,
                capture_input,
                &input.progress.admission_archive,
                self.level,
                self.result_photo
                    .hover_region(ui, self.scales.aperture())
                    .unwrap_or_else(|| self.scales.aperture()),
            );
            self.participation_frame = picked.frame;
            self.participation_held = picked.held;
            if let Some(level) = picked.level {
                self.level = level;
                self.level_touched = true;
                self.scales.select_level(level);
            }
            if !picked.return_photo
                && !picked.reset_view
                && let Some(frame) = picked.hover_source
            {
                self.hover_source = Some(frame);
            }
            if input.progress.stage == Stage::Complete && !picked.return_photo {
                // Once a camera comparison is held, merely crossing another
                // thumbnail cannot silently put a different frame's support
                // over the final while the first camera source remains beside it.
                if let Some(frame) = picked.open_source.or(self.inspection_frame()) {
                    self.participation_frame = Some(frame);
                    self.participation_held = self.hover_source.is_none();
                }
            }
            if let Some(frame) = picked.open_source {
                self.inspect_frame(frame);
                response.selected = Some(frame);
                // Selection may arrive after the normal background sync, but
                // an already cached real source can be shown this same paint.
                self.sync_photos(input, now, ui.ctx());
            }
            if picked.return_photo {
                self.resume_live();
                response.return_live = true;
            }
            if picked.reset_view {
                self.fit_views();
            }
            // Hover requests use inspection_frame() for existing bounded cache
            // warming. They never mutate app selection or the exploration log.
            self.sync_photos(input, now, ui.ctx());
            if self.inspection_frame().is_some() && self.output_space(input).is_some() {
                // A pending request cannot put the next frame's diagnostic
                // labels over the previous frame's still-visible photograph.
                self.participation_frame = self
                    .inspection
                    .as_ref()
                    .map(|slot| slot.current().index)
                    .or_else(|| self.inspection_frame());
            }
        }
        if (!compact || focused) && !self.edit_focus {
            self.contribution(ui, layout.contributions, input);
        }
        self.source_axis_bounds = focused.then_some(layout.hero);
        self.photograph(ui, layout.hero, input, response);
        self.scales.set_pin(self.pin);
        if !compact && !focused {
            self.fingerprint(ui, layout, input, response);
        }
        if !focused {
            self.convergence(ui, layout, input, instrument_clip);
        }
        if !self.restored {
            if released {
                if let Some(start) = self.gesture_start.take() {
                    self.remember(start);
                }
            } else if wheel && self.gesture_start.is_none() && before != self.exploration() {
                if self.wheel_edit.is_none_or(|previous| now - previous > 0.35) {
                    self.remember(before);
                }
                self.wheel_edit = Some(now);
            } else if key && self.gesture_start.is_none() {
                self.remember(before);
            }
        }
    }

    fn inspection_rail(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        response: &mut Response,
    ) {
        let p = ui.painter_at(rect);
        crate::theme::rule(&p, rect.right_top(), rect.right_bottom(), LINE);
        let back = Rect::from_min_size(rect.min, egui::vec2(rect.width() - 8.0, 28.0));
        let hit = ui.interact(
            back,
            ui.id().with("inspection-return-process"),
            Sense::click(),
        );
        p.text(
            back.center(),
            Align2::CENTER_CENTER,
            "Process",
            FontId::proportional(10.0),
            INK,
        );
        if hit.clicked() {
            self.resume_live();
            response.return_live = true;
        }
        hit.on_hover_text(
            "Return to the complete process workspace · Escape also fits the photograph",
        );
        let Some(frame) = self.inspection_frame() else {
            return;
        };
        text(
            &p,
            rect.min + egui::vec2(0.0, 42.0),
            &format!("F{:03}", frame + 1),
            13.0,
            ACCENT,
        );
        text(&p, rect.min + egui::vec2(0.0, 62.0), "ADMITTED", 7.0, MUTED);
        for level in input.progress.admission_archive.levels().take(16) {
            let y = rect.top() + 82.0 + level as f32 * 27.0;
            if y + 25.0 > rect.bottom() {
                break;
            }
            let cell = Rect::from_min_size(
                egui::pos2(rect.left(), y),
                egui::vec2(rect.width() - 10.0, 25.0),
            );
            let hit = ui.interact(
                cell,
                ui.id().with(("inspection-band", level)),
                Sense::click(),
            );
            let color = crate::process_sample_glyphs::level_color(level);
            if level == self.level {
                p.rect_filled(cell, 0.0, PANEL);
            }
            text(
                &p,
                cell.min,
                &crate::process_output_space::detail_label(level, input.progress.output_geometry),
                8.0,
                color,
            );
            if let Some((yes, total)) = input.progress.admission_archive.counts(level, frame) {
                let bar = Rect::from_min_size(
                    cell.min + egui::vec2(0.0, 15.0),
                    egui::vec2(cell.width(), 3.0),
                );
                p.rect_filled(bar, 0.0, LINE);
                p.rect_filled(
                    Rect::from_min_size(
                        bar.min,
                        egui::vec2(bar.width() * yes as f32 / total.max(1) as f32, 3.0),
                    ),
                    0.0,
                    color,
                );
                hit.clone().on_hover_text(format!("Capture {} · {yes}/{total} observed samples admitted at this detail size. Click to inspect this band.", frame + 1));
            }
            if hit.clicked() {
                self.level = level;
                self.level_touched = true;
                self.scales.select_level(level);
            }
        }
    }

    fn contribution(&mut self, ui: &mut Ui, rect: Rect, input: &Input<'_>) {
        let linked_output = self.output_space(input).is_some();
        let admitted = if linked_output && self.participation_frame.is_some() {
            self.participation_frame.and_then(|frame| {
                let archive = &input.progress.admission_archive;
                let Some(meta) = archive.metadata(self.level, frame).filter(|meta| {
                    Some(meta.extent) == input.progress.analysis_size.or(input.progress.plane_size)
                }) else {
                    self.retained_admission = None;
                    return None;
                };
                if self
                    .retained_admission
                    .as_ref()
                    .is_none_or(|(old, packet)| {
                        *old != meta || packet.frame != frame || packet.level != self.level
                    })
                {
                    let (_, cells) = archive.cells(self.level, frame)?;
                    self.retained_admission = Some((
                        meta,
                        crate::pipeline::DiagnosticSurface {
                            sequence: meta.sequence,
                            frame,
                            level: self.level,
                            kind: DiagnosticKind::GateSupport,
                            scope: crate::pipeline::DiagnosticScope::Frame,
                            scale: DiagnosticScale::Linear,
                            width: meta.samples[0],
                            height: meta.samples[1],
                            min: 0.0,
                            max: 1.0,
                            folded: 1,
                            pixels: cells
                                .map(|yes| if yes { 255 } else { 0 })
                                .collect::<Vec<_>>()
                                .into(),
                        },
                    ));
                }
                self.retained_admission
                    .as_ref()
                    .map(|(_, packet)| packet.clone())
            })
        } else {
            self.observation(DiagnosticKind::GateSupport)
                .and_then(|item| item.packet.clone())
        };
        let fallback = self
            .observation(DiagnosticKind::Averaging)
            .and_then(|item| item.packet.clone());
        let contribution = self.contributions.show(
            ui,
            rect,
            crate::process_contribution::Context {
                base: if linked_output {
                    self.saved_output.as_ref()
                } else {
                    self.hero
                        .as_ref()
                        .filter(|hero| hero.plate.tonal)
                        .map(|hero| &hero.plate.texture)
                        .or_else(|| self.preview_tone.as_ref().map(|(_, texture)| texture))
                },
                base_folded: if linked_output {
                    input
                        .progress
                        .frames_accepted
                        .or_else(|| input.progress.folded.map(|(done, _)| done))
                        .unwrap_or(0)
                } else {
                    self.hero
                        .as_ref()
                        .filter(|hero| hero.plate.tonal)
                        .map(|hero| hero.plate.folded)
                        .unwrap_or_else(|| {
                            self.preview_tone
                                .as_ref()
                                .and_then(|(sequence, _)| {
                                    self.observations
                                        .iter()
                                        .find(|item| item.meta.sequence == *sequence)
                                })
                                .map_or(0, |item| item.meta.folded)
                        })
                },
                admitted: admitted.as_ref(),
                fallback: fallback.as_ref(),
                level: self.level,
                pin: self.scales.painted_pin(),
                aperture: self.scales.aperture(),
                extent: input
                    .progress
                    .analysis_size
                    .or(input.progress.plane_size)
                    .map(|size| egui::vec2(size[0] as f32, size[1] as f32)),
            },
        );
        self.contribution_hovered = contribution.hovered;
        if contribution.reset {
            self.fit_views();
        }
        if let Some(pin) = contribution.pin {
            self.pin = pin;
            if contribution.dragging {
                self.scales
                    .set_view(pin, self.scales.aperture().width().recip());
            } else {
                self.scales.set_pin(pin);
                self.scales.focus_pin();
            }
            ui.ctx().request_repaint();
        }
        if let Some(anchor) = contribution.zoom_anchor {
            if linked_output {
                self.scales.zoom_photo_at(contribution.zoom_factor, anchor);
            } else {
                self.scales.zoom_at(contribution.zoom_factor, anchor);
            }
            self.pin = self.scales.pin();
            ui.ctx().request_repaint();
        }
    }

    fn instruments(
        &mut self,
        ui: &mut Ui,
        layout: Layout,
        input: &Input<'_>,
        response: &mut Response,
        completed: bool,
    ) {
        self.visible_contacts =
            crate::process_network::visible_contact_indices(layout.network, input.frame_count);
        self.visible_contacts
            .extend(crate::process_ledger::visible_contact_indices(
                layout.ledger,
                input.frame_count,
            ));
        self.visible_contacts.sort_unstable();
        self.visible_contacts.dedup();
        if !completed {
            self.origins(ui, layout, input, response);
        }
        if !completed && let Some(pick) = crate::process_network::show(ui, layout.network, input) {
            match pick {
                crate::process_network::Pick::Frame(index) => {
                    if input.progress.stage == Stage::Complete {
                        self.participation.select_frame(index);
                        self.inspect_frame(index);
                        response.selected = Some(index);
                    } else {
                        self.inspect_frame(index);
                        response.selected = Some(index);
                    }
                }
                crate::process_network::Pick::Pair(pair) => {
                    response.compare_pair = Some(pair);
                    self.inspected_source = None;
                }
            }
        }
        if !completed
            && let Some(pick) = self
                .ledger
                .show(ui, layout.ledger, input, self.level)
                .clicked
        {
            self.level = pick.level.min(self.levels(input) - 1);
            self.level_touched = true;
            self.scales.select_level(self.level);
            if let Some(frame) = pick.frame {
                self.inspect_frame(frame);
                response.selected = Some(frame);
            }
        }
        self.signals(ui, layout, input);
    }

    fn fingerprint(
        &mut self,
        ui: &mut Ui,
        layout: Layout,
        input: &Input<'_>,
        response: &mut Response,
    ) {
        let fingerprint = crate::process_fingerprint::show(
            ui,
            layout.weave,
            input,
            &input.progress.admission_archive,
            self.scales.painted_pin(),
            self.level,
        );
        if let Some(pick) = fingerprint.clicked {
            self.level = pick.level.min(self.levels(input) - 1);
            self.level_touched = true;
            self.scales.select_level(self.level);
            if let Some(frame) = pick.frame {
                self.inspect_frame(frame);
                response.selected = Some(frame);
            }
        }
    }

    fn compact_divider(&mut self, ui: &mut Ui, rect: Rect) -> f32 {
        // Keep all five measured columns readable beside the photograph. The
        // instrument content is 382 points wide; its solid scrollbar and the
        // divider gap also consume space. Clamp only the painted split, so a
        // smaller window never rewrites the user's saved arrangement.
        let minimum_left = 408.0_f32.min((rect.width() - 230.0).max(rect.width() * 0.52));
        let minimum = minimum_left / rect.width();
        let limits = minimum..=(1.0 - 230.0 / rect.width()).max(minimum);
        let fraction = self
            .layout
            .final_detail
            .clamp(*limits.start(), *limits.end());
        let x = rect.left() + rect.width() * fraction;
        let seam = Rect::from_min_max(
            egui::pos2(x - 4.0, rect.top()),
            egui::pos2(x + 4.0, rect.bottom()),
        );
        let (delta, reset) = crate::workspace_layout::seam(ui, "compact-photo-seam", seam, true);
        if reset {
            self.layout.final_detail = 0.44;
        } else if delta != 0.0 {
            self.layout.final_detail =
                (fraction + delta / rect.width()).clamp(*limits.start(), *limits.end());
        }
        rect.left()
            + rect.width()
                * self
                    .layout
                    .final_detail
                    .clamp(*limits.start(), *limits.end())
    }

    fn resize_workspace(&mut self, ui: &mut Ui, rect: Rect, completed: bool) {
        use crate::workspace_layout::seam;
        self.layout.sanitize();
        let mut effective = self.layout;
        effective.constrain_width(rect.width());
        effective.lower = 0.0;
        let layout = Layout::configured(rect, completed, effective);
        for (id, ratio, painted, default) in if completed {
            vec![(
                "final-photo-seam",
                &mut self.layout.final_detail,
                effective.final_detail,
                0.44,
            )]
        } else {
            vec![
                (
                    "network-seam",
                    &mut self.layout.network,
                    effective.network,
                    0.20,
                ),
                (
                    "photo-seam",
                    &mut self.layout.detail,
                    effective.detail,
                    0.61,
                ),
            ]
        } {
            let at = rect.left() + rect.width() * painted + 8.0;
            let hit = Rect::from_min_max(
                egui::pos2(at - 5.0, rect.top()),
                egui::pos2(at + 5.0, rect.bottom()),
            );
            let (delta, reset) = seam(ui, id, hit, true);
            if reset {
                *ratio = default;
            } else if delta != 0.0 {
                *ratio = painted + delta / rect.width();
            }
        }
        let fingerprint = Rect::from_min_max(
            egui::pos2(layout.weave.left(), layout.weave.top() - 10.0),
            egui::pos2(layout.weave.right(), layout.weave.top() - 2.0),
        );
        let (delta, reset) = seam(ui, "fingerprint-height-seam", fingerprint, false);
        if reset {
            self.layout.fingerprint = 0.0;
        } else {
            self.layout.fingerprint -= delta / rect.height();
        }
        self.layout.sanitize();
    }

    fn receive(&mut self, input: &Input<'_>) {
        if let Some(extent) = input.progress.analysis_size.or(input.progress.plane_size) {
            for packet in &input.progress.diagnostic_surfaces {
                self.revisions.observe(packet, extent);
            }
            // Direct surfaces also support replay and deliberately sparse engines.
            for packet in input
                .surfaces
                .iter()
                .filter(|s| s.epoch == input.epoch)
                .filter_map(|s| s.packet)
            {
                self.revisions.observe(packet, extent);
            }
        }
        for surface in input
            .surfaces
            .iter()
            .filter(|surface| surface.epoch == input.epoch)
        {
            let Some(meta) = surface.meta else { continue };
            let incoming = Observation {
                texture: surface.texture.clone(),
                meta,
                level: surface.level,
                frame: surface.frame,
                packet: surface
                    .packet
                    .filter(|packet| packet.sequence == meta.sequence)
                    .cloned()
                    .or_else(|| {
                        input
                            .progress
                            .diagnostic_surfaces
                            .iter()
                            .find(|packet| packet.sequence == meta.sequence)
                            .cloned()
                    }),
            };
            if let Some(old) = self
                .observations
                .iter_mut()
                .find(|old| old.level == surface.level && old.meta.kind == meta.kind)
            {
                if meta.sequence > old.meta.sequence {
                    *old = incoming;
                }
            } else {
                if self.observations.len() == 384 {
                    let oldest = self
                        .observations
                        .iter()
                        .enumerate()
                        .min_by_key(|(_, item)| item.meta.sequence)
                        .unwrap()
                        .0;
                    self.observations.remove(oldest);
                }
                self.observations.push(incoming);
            }
        }
    }

    fn observation(&self, kind: DiagnosticKind) -> Option<&Observation> {
        self.observations
            .iter()
            .find(|item| item.level == self.level && item.meta.kind == kind)
    }

    fn sync_photos(&mut self, input: &Input<'_>, now: f64, ctx: &egui::Context) {
        let available = |index| {
            input
                .inspection_photos
                .iter()
                .find(|photo| photo.epoch == input.epoch && photo.index == index)
                .cloned()
        };
        // Lock the first available canonical camera image. Live pair activity
        // belongs to the small lenses, and never scrubs the main photograph.
        if self.source_index.is_none() {
            self.source_index = input
                .progress
                .reference_frame
                .filter(|index| available(*index).is_some())
                .or_else(|| available(input.selected).map(|photo| photo.index))
                .or_else(|| {
                    input
                        .inspection_photos
                        .iter()
                        .find(|photo| photo.epoch == input.epoch)
                        .map(|photo| photo.index)
                });
        }
        PhotoSlot::sync(
            &mut self.source,
            self.source_index.and_then(available),
            input.epoch,
        );
        let mut pair = input
            .inspected_pair
            .or(input.progress.alignment_current_pair)
            .or(input.progress.alignment_latest_pair)
            .unwrap_or([input.selected, input.selected]);
        if let Some(index) = self.inspection_frame() {
            pair[0] = index;
        }
        for (slot, index) in self.pair.iter_mut().zip(pair) {
            PhotoSlot::sync(slot, available(index), input.epoch);
        }
        let inspection = self.inspection_frame().and_then(available);
        PhotoSlot::sync(&mut self.inspection, inspection, input.epoch);
        let mut repaint = self.source.as_mut().is_some_and(|slot| slot.advance(now));
        repaint |= self
            .inspection
            .as_mut()
            .is_some_and(|slot| slot.advance(now));
        for slot in self.pair.iter_mut().flatten() {
            repaint |= slot.advance(now);
        }
        if repaint {
            ctx.request_repaint();
        }
    }

    fn sync_latest_preview(&mut self, input: &Input<'_>, ctx: &egui::Context) {
        let retained = &input.progress.live_preview;
        if self.preview_generation != Some(retained.generation) {
            self.preview_generation = Some(retained.generation);
            self.latest_preview = None;
            self.preview_range = retained.tone_range;
            self.preview_tone = None;
        }
        let Some(packet) = retained.latest.as_ref() else {
            return;
        };
        if self
            .latest_preview
            .as_ref()
            .is_some_and(|p| p.sequence == packet.sequence)
        {
            return;
        }
        let range = retained.tone_range.unwrap_or((packet.min, packet.max));
        self.preview_range = Some(range);
        let texture = ctx.load_texture(
            format!("live-reconstruction-{}-{}", input.epoch, packet.sequence),
            preview_tone_image(packet, range),
            egui::TextureOptions::LINEAR,
        );
        self.latest_preview = Some(Plate {
            extent: extent(input, &texture),
            texture,
            uv: full(),
            kind: 1,
            sequence: packet.sequence,
            level: packet.level,
            folded: packet.folded,
            tonal: true,
        });
    }

    fn sync_hero(&mut self, input: &Input<'_>, now: f64, ctx: &egui::Context) {
        // Complete the previous reveal before choosing the newest delivered
        // accumulation. Otherwise a sparse repaint can defer a real update for
        // an extra paint even though its transition already elapsed.
        if let Some(hero) = &mut self.hero
            && hero.previous.is_some()
        {
            let t = ((now - hero.start) / 0.38).clamp(0.0, 1.0) as f32;
            hero.alpha = t * t * (3.0 - 2.0 * t);
            if t >= 1.0 {
                hero.previous = None;
            }
        }
        if let Some(output) = input.output {
            self.saved_output = Some(output.clone());
            self.saved_output_size = input.output_size;
        }
        let coarse = self
            .observations
            .iter()
            .filter(|item| item.meta.kind == DiagnosticKind::Preview)
            .max_by_key(|item| item.meta.sequence)
            .cloned();
        if let Some(item) = &coarse
            && let Some(packet) = &item.packet
            && self
                .preview_tone
                .as_ref()
                .is_none_or(|(sequence, _)| *sequence != item.meta.sequence)
        {
            if self.preview_range.is_none() && packet.max > packet.min {
                self.preview_range = Some((packet.min, packet.max));
            }
            let range = self.preview_range.unwrap_or((packet.min, packet.max));
            self.preview_tone = Some((
                item.meta.sequence,
                ctx.load_texture(
                    format!("stack-preview-{}-{}", input.epoch, item.meta.sequence),
                    preview_tone_image(packet, range),
                    egui::TextureOptions::LINEAR,
                ),
            ));
        }
        let incoming = self
            .saved_output
            .as_ref()
            .map(|texture| Plate {
                texture: texture.clone(),
                extent: self.saved_output_size.map_or_else(
                    || texture.size_vec2(),
                    |size| egui::vec2(size[0] as f32, size[1] as f32),
                ),
                uv: full(),
                kind: 3,
                sequence: u64::MAX,
                level: 0,
                folded: input.frame_count,
                tonal: false,
            })
            .or_else(|| {
                // The diagnostic reconstruction packet is sampled more
                // sparsely. Never downgrade a delivered coarse live image
                // while the developed TIFF is being decoded.
                if coarse.is_some() {
                    return None;
                }
                self.observations
                    .iter()
                    .filter(|item| item.meta.kind == DiagnosticKind::Reconstructed)
                    .max_by_key(|item| item.meta.sequence)
                    .map(|item| Plate {
                        texture: item.texture.clone(),
                        extent: extent(input, &item.texture),
                        uv: full(),
                        kind: 2,
                        sequence: item.meta.sequence,
                        level: item.level,
                        folded: item.meta.folded,
                        tonal: false,
                    })
            })
            .or_else(|| {
                coarse.as_ref().and_then(|item| {
                    self.preview_tone
                        .as_ref()
                        .filter(|(sequence, _)| *sequence == item.meta.sequence)
                        .map(|(_, texture)| Plate {
                            texture: texture.clone(),
                            extent: extent(input, texture),
                            uv: full(),
                            kind: 1,
                            sequence: item.meta.sequence,
                            level: item.level,
                            folded: item.meta.folded,
                            tonal: true,
                        })
                })
            });
        // Keep the newest real reconstruction across sparse paints.
        let retained = self.latest_preview.clone();
        let incoming = match (incoming, retained) {
            (Some(current), Some(retained))
                if current.kind == 1 && retained.sequence > current.sequence =>
            {
                Some(retained)
            }
            (Some(current), _) => Some(current),
            (None, retained) => retained,
        };
        if let Some(plate) = incoming {
            let changed = self.hero.as_ref().is_none_or(|hero| {
                hero.plate.kind < plate.kind
                    || hero.plate.kind == plate.kind
                        && (hero.plate.sequence != plate.sequence
                            || hero.plate.texture.id() != plate.texture.id())
            });
            if changed
                && plate.kind == 3
                && let Some(hero) = self.hero.as_mut().filter(|hero| hero.plate.kind == 3)
            {
                // A developed/Before texture is the same photograph. Replaying
                // completion here would discard the user's crop and selections.
                hero.plate = plate;
                hero.previous = None;
                hero.alpha = 1.0;
                self.hero_pending = false;
                return;
            }
            let revealing = self
                .hero
                .as_ref()
                .is_some_and(|hero| hero.previous.is_some());
            self.hero_pending = changed;
            if changed && !revealing && !self.source.as_ref().is_some_and(PhotoSlot::needs_repaint)
            {
                let previous = self
                    .hero
                    .as_ref()
                    .map(|hero| hero.plate.clone())
                    .or_else(|| {
                        self.source.as_ref().map(|slot| {
                            let photo = slot.current();
                            let (_, uv) =
                                preview_aperture(photo.texture.size_vec2(), photo.aperture, true);
                            Plate {
                                texture: photo.texture.clone(),
                                extent: egui::vec2(
                                    photo.aperture[0] as f32,
                                    photo.aperture[1] as f32,
                                ),
                                uv,
                                kind: 0,
                                sequence: 0,
                                level: 0,
                                folded: 0,
                                tonal: false,
                            }
                        })
                    });
                if plate.kind == 3 {
                    self.enlarged = None;
                    self.inspected_source = None;
                    self.zoom = 1.0;
                    self.pan = Vec2::ZERO;
                    // Completion starts with the entire clean photograph.
                    if self.output_space(input).is_some() {
                        self.scales.set_view(egui::pos2(0.5, 0.5), 1.0);
                        self.pin = egui::pos2(0.5, 0.5);
                        if !self.level_touched
                            && let Some(level) = crate::process_output_space::initial_detail_level(
                                &input.progress.admission_archive,
                                input.progress.bands.unwrap_or(0),
                                input.progress.output_geometry,
                            )
                        {
                            self.level = level;
                            self.scales.select_level(level);
                        }
                    }
                    self.result_photo = Default::default();
                    self.participation.clear();
                    self.participation_frame = None;
                }
                self.revision_view.sync(
                    ctx,
                    input
                        .progress
                        .revisions
                        .latest()
                        .or_else(|| self.revisions.latest())
                        .filter(|revision| plate.tonal && revision.sequence == plate.sequence),
                );
                self.hero = Some(Reveal {
                    plate,
                    alpha: if previous.is_some() { 0.0 } else { 1.0 },
                    previous,
                    start: now,
                });
                self.hero_pending = false;
            }
        }
        if let Some(hero) = &mut self.hero
            && hero.previous.is_some()
        {
            let t = ((now - hero.start) / 0.38).clamp(0.0, 1.0) as f32;
            hero.alpha = t * t * (3.0 - 2.0 * t);
            if t >= 1.0 {
                hero.previous = None;
            }
            ctx.request_repaint();
        }
    }

    fn heading(&self, ui: &mut Ui, rect: Rect, input: &Input<'_>) {
        let p = ui.painter_at(rect);
        let completed = input.progress.stage == Stage::Complete;
        let title = if completed {
            "PHOTOGRAPH COMPLETE"
        } else {
            "PHOTOGRAPH / ACCUMULATING"
        };
        text(
            &p,
            rect.min + egui::vec2(0.0, 6.0),
            title,
            11.0,
            if completed { GREEN } else { INK },
        );
        let subtitle = if completed {
            self.hero
                .as_ref()
                .filter(|hero| hero.plate.kind == 3)
                .map_or_else(
                    || "Saved TIFF · preparing display".into(),
                    |hero| {
                        format!(
                            "{} frames · {} × {} TIFF pixels · saved",
                            input.frame_count,
                            hero.plate.extent.x as u32,
                            hero.plate.extent.y as u32
                        )
                    },
                )
        } else {
            // Kernel activity is already visible in the journey's quiet work
            // lanes. Keep the photograph's heading anchored to its real phase.
            match input.progress.stage {
                Stage::Preparing => "Camera originals → measured detail → photograph",
                Stage::Alignment => "Registering capture geometry",
                Stage::Merge => "Combining accepted frames",
                Stage::Rendering => "Reconstructing + developing",
                Stage::Failed => "Processing stopped with an error",
                Stage::Cancelled => "Processing stopped",
                Stage::Complete => unreachable!(),
            }
            .into()
        };
        text(&p, rect.min + egui::vec2(0.0, 24.0), &subtitle, 8.5, MUTED);
    }

    fn photograph(&mut self, ui: &mut Ui, rect: Rect, input: &Input<'_>, response: &mut Response) {
        let probe_count = if self.output_space(input).is_some() {
            input.frame_count
        } else {
            0
        };
        let fallback = self
            .observation(DiagnosticKind::Averaging)
            .filter(|observation| Some(observation.meta.folded) == input.progress.frames_accepted)
            .and_then(|observation| observation.packet.clone())
            .zip(input.progress.analysis_size.or(input.progress.plane_size));
        self.result_photo.configure_probe(
            probe_count,
            input
                .progress
                .analysis_size
                .or(input.progress.plane_size)
                .filter(|_| probe_count > 0),
            fallback,
        );
        self.primary_destination = None;
        self.edit_mapping = None;
        let p = ui.painter_at(rect);
        p.rect_filled(rect, 0.0, crate::theme::BG);
        let final_owned = input.progress.stage == Stage::Complete
            && self.hero.as_ref().is_some_and(|hero| hero.plate.kind == 3);
        self.source_relation_mix = ui.ctx().animate_bool_with_time(
            ui.id().with(("source-final-companion", input.epoch)),
            final_owned && self.inspection_frame().is_some(),
            0.18,
        );
        let final_extent = self
            .hero
            .as_ref()
            .map_or(egui::vec2(3.0, 2.0), |hero| hero.plate.extent);
        let source_extent = self.inspection.as_ref().map_or(final_extent, |slot| {
            let [w, h] = slot.current().aperture;
            egui::vec2(w as f32, h as f32)
        });
        let axis = source_relation_axis(
            self.source_axis_bounds.unwrap_or(rect),
            [final_extent, source_extent],
            self.source_relation_axis,
        );
        if self.source_relation_mix > 0.001 {
            self.source_relation_axis = Some(axis);
        } else {
            self.source_relation_axis = None;
        }
        let (rect, companion) = source_relation_layout(rect, self.source_relation_mix, axis);
        let footer = photograph_footer(rect);
        self.source_relation_rect = companion;
        let title_rect = Rect::from_min_size(
            rect.min + egui::vec2(10.0, 8.0),
            egui::vec2(rect.width() - 20.0, 21.0),
        );
        // Reuse the existing caption lane. Evidence must never resize the
        // photograph at TIFF arrival or steal room from a compact comparison.
        self.review_strip_visible = final_owned
            && footer >= 53.0
            && rect.width() >= 230.0
            && input.progress.bands.is_some();
        self.review_hover = None;
        if self.review_strip_visible {
            let strip = Rect::from_min_max(
                rect.left_bottom() + egui::vec2(10.0, -29.0),
                rect.right_bottom() - egui::vec2(10.0, 1.0),
            );
            let action = review_strip::show(
                ui,
                strip,
                input.progress,
                self.observations.iter().filter_map(|o| o.packet.as_ref()),
                self.level,
            );
            self.review_hover = action.hovered.filter(|_| final_owned);
            if let Some(level) = action.selected {
                self.level = level;
                self.level_touched = true;
                self.scales.select_level(level);
                if final_owned {
                    self.enlarged = Some(DiagnosticKind::Averaging);
                }
            }
        }
        let image_box = Rect::from_min_max(
            rect.min + egui::vec2(10.0, 36.0),
            // Reserve the diagnostic caption from the first camera frame.
            // Its later contents cannot shrink the live image at TIFF arrival.
            rect.max - egui::vec2(10.0, footer),
        );
        if final_owned && self.output_space(input).is_some() {
            self.requested_view = None;
        }
        if self.output_space(input).is_some()
            && self
                .hero
                .as_ref()
                .is_some_and(|hero| hero.plate.kind == 3 && hero.previous.is_none())
        {
            self.finished_photograph(ui, rect, image_box, input);
            if !self.annotation_mode {
                self.final_modifier(ui, rect, image_box, input);
            }
            self.result_photo.legend(
                ui,
                Rect::from_min_size(
                    rect.left_bottom() + egui::vec2(10.0, 1.0 - footer),
                    egui::vec2((rect.width() - 20.0).max(0.0), 24.0),
                ),
                final_extent,
            );
            if let Some(companion) = companion {
                self.source_relation(ui, companion, input, response);
            }
            return;
        }
        if !final_owned && self.inspected_source.is_some() && self.inspection.is_some() {
            self.source_photograph(ui, rect, image_box, input);
            return;
        }
        let inspect = self
            .enlarged
            .filter(|_| !final_owned)
            .and_then(|kind| self.observation(kind).cloned());
        let title = if let Some(observed) = &inspect {
            format!(
                "{} / {} / ALIGNED MAP",
                signal_name(observed.meta.kind),
                crate::process_output_space::detail_label(
                    self.level,
                    input.progress.output_geometry
                )
            )
        } else if let Some(hero) = &self.hero {
            if hero.plate.kind == 3 {
                self.edit_mapping = Some((
                    zoomed(fit(hero.plate.extent, image_box), self.zoom, self.pan),
                    image_box,
                ));
            }
            match hero.plate.kind {
                3 => "YOUR PHOTOGRAPH / SAVED TIFF".into(),
                2 => "RECONSTRUCTED GREEN / MEASURED DN".into(),
                _ if hero.plate.tonal => format!(
                    "LIVE STACK / {} OF {} FRAMES",
                    hero.plate.folded, input.frame_count
                ),
                _ => format!(
                    "MERGED GREEN / {} / {} ACCEPTED",
                    crate::process_output_space::detail_label(
                        hero.plate.level,
                        input.progress.output_geometry
                    ),
                    hero.plate.folded
                ),
            }
        } else {
            self.source.as_ref().map_or_else(
                || "CAMERA CONTEXT / PREVIEW PENDING".into(),
                |slot| format!("CAMERA CONTEXT / FRAME {:03}", slot.current().index + 1),
            )
        };
        let live_photo = self.enlarged.is_none()
            && self.saved_output.is_none()
            && self.hero.as_ref().is_some_and(|hero| hero.plate.tonal);
        let title_clip = if live_photo {
            Rect::from_min_max(
                title_rect.min,
                egui::pos2(rect.right() - 96.0, title_rect.bottom()),
            )
        } else if self.enlarged.is_some() {
            Rect::from_min_max(
                title_rect.min,
                egui::pos2(rect.right() - 142.0, title_rect.bottom()),
            )
        } else {
            title_rect
        };
        text(
            &p.with_clip_rect(title_clip),
            title_rect.min,
            &title,
            9.0,
            ACCENT,
        );
        if live_photo {
            crate::process_revision_view::toggle(
                ui,
                Rect::from_min_size(
                    egui::pos2(rect.right() - 84.0, rect.top() + 7.0),
                    egui::vec2(74.0, 19.0),
                ),
                &mut self.show_revisions,
            );
        }
        if self.enlarged.is_some() {
            let back = Rect::from_min_size(
                egui::pos2(rect.right() - 134.0, rect.top() + 7.0),
                egui::vec2(124.0, 21.0),
            );
            p.rect_filled(back, 0.0, PANEL);
            p.text(
                back.center(),
                Align2::CENTER_CENTER,
                "Return photograph",
                FontId::proportional(10.0),
                INK,
            );
            if ui
                .interact(back, ui.id().with("theater-photo-return"), Sense::click())
                .clicked()
            {
                self.enlarged = None;
            }
        }
        if let Some((center, zoom)) = self.requested_view {
            self.zoom = zoom.clamp(1.0, 8.0);
            if let Some(hero) = &self.hero {
                let size = fit(hero.plate.extent, image_box).size() * self.zoom;
                self.pan = (egui::vec2(0.5, 0.5) - center.to_vec2()) * size;
                self.pin = center;
                self.scales.set_pin(center);
                if self.saved_output.is_none() || hero.plate.kind == 3 {
                    self.requested_view = None;
                }
            }
        }
        let gesture = ui.interact(
            image_box,
            ui.id().with("theater-photograph"),
            if self.annotation_mode {
                Sense::hover()
            } else {
                Sense::click_and_drag()
            },
        );
        gesture.context_menu(|ui| {
            if ui.button("Fit linked views").clicked() {
                self.fit_views();
                ui.close();
            }
            if ui.button("Return to current photograph").clicked() {
                self.resume_live();
                ui.close();
            }
            ui.separator();
            if ui
                .add_enabled(self.can_undo(), egui::Button::new("Undo exploration"))
                .clicked()
            {
                self.undo();
                ui.close();
            }
            if ui
                .add_enabled(self.can_redo(), egui::Button::new("Redo exploration"))
                .clicked()
            {
                self.redo();
                ui.close();
            }
        });
        let gestures_allowed = !self.annotation_mode
            && ui.is_enabled()
            && ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()));
        let image_gesture = crate::image_gesture::reset(ui, &gesture);
        let detail_pin = self.scales.painted_pin();
        let detail_aperture = self.scales.aperture();
        let navigation = if live_photo
            && !self.annotation_mode
            && let Some(hero) = &self.hero
        {
            self.navigator.interact(
                ui,
                &gesture,
                zoomed(fit(hero.plate.extent, image_box), self.zoom, self.pan),
                image_box,
                detail_aperture,
                false,
            )
        } else {
            self.navigator.clear();
            Default::default()
        };
        if live_photo
            && gesture.hovered()
            && !gesture.dragged()
            && !navigation.owns_click
            && !self.navigator.hovered()
        {
            ui.ctx().set_cursor_icon(egui::CursorIcon::Crosshair);
        }
        if gestures_allowed && image_gesture.reset {
            self.enlarged = None;
            self.zoom = 1.0;
            self.pan = Vec2::ZERO;
            self.scales.reset_view();
            self.pin = self.scales.pin();
            self.navigator.clear();
            ui.ctx().request_repaint();
        }
        if let Some(observed) = &inspect {
            if gestures_allowed
                && !image_gesture.reset
                && !image_gesture.pending
                && (gesture.clicked() || gesture.dragged())
                && let Some(pos) = gesture.interact_pointer_pos()
            {
                let mapped = fit(extent(input, &observed.texture), image_box);
                self.pin = normalized(pos, mapped);
            }
        } else {
            if gestures_allowed
                && !image_gesture.reset
                && !image_gesture.pending
                && gesture.hovered()
                && !navigation.owns_scroll
            {
                let scroll = ui.input(|state| state.raw_scroll_delta.y);
                let pinch = crate::process_region_probe::zoom_delta(ui);
                let factor = if (pinch - 1.0).abs() > f32::EPSILON {
                    pinch
                } else {
                    (scroll * 0.0025).exp()
                };
                if factor.is_finite() && (factor - 1.0).abs() > f32::EPSILON {
                    let next = (self.zoom * factor).clamp(1.0, 8.0);
                    if let Some(pointer) = ui.input(|state| state.pointer.hover_pos()) {
                        let ratio = next / self.zoom;
                        self.pan =
                            self.pan * ratio + (pointer - image_box.center()) * (1.0 - ratio);
                    }
                    self.zoom = next;
                }
            }
            if gestures_allowed
                && !image_gesture.reset
                && !image_gesture.pending
                && gesture.dragged()
                && !navigation.owns_drag
            {
                self.pan += ui.input(|state| state.pointer.delta());
            }
            let extent = self
                .hero
                .as_ref()
                .map(|hero| hero.plate.extent)
                .or_else(|| {
                    self.source.as_ref().map(|source| {
                        let aperture = source.current().aperture;
                        egui::vec2(aperture[0] as f32, aperture[1] as f32)
                    })
                })
                .unwrap_or(image_box.size());
            let limit = ((fit(extent, image_box).size() * self.zoom - image_box.size()) * 0.5)
                .max(Vec2::ZERO);
            self.pan = self.pan.clamp(-limit, limit);
            if live_photo
                && gesture.clicked()
                && !image_gesture.reset
                && !image_gesture.pending
                && !navigation.owns_click
                && let Some(point) = gesture.interact_pointer_pos()
            {
                self.pin = normalized(point, zoomed(fit(extent, image_box), self.zoom, self.pan));
                self.scales.focus_pin();
                ui.ctx().request_repaint();
            }
        }
        let photo_painter = p.with_clip_rect(image_box);
        if let Some(observed) = inspect {
            let destination = fit(extent(input, &observed.texture), image_box);
            self.primary_destination = Some(destination);
            photo_painter.image(observed.texture.id(), destination, full(), Color32::WHITE);
            crosshair(&photo_painter, destination, self.pin);
        } else if let Some(hero) = &self.hero {
            self.primary_destination = Some(
                zoomed(fit(hero.plate.extent, image_box), self.zoom, self.pan).intersect(image_box),
            );
            if let Some(previous) = &hero.previous {
                paint_plate(
                    &photo_painter,
                    previous,
                    image_box,
                    self.zoom,
                    self.pan,
                    255,
                );
            }
            paint_plate(
                &photo_painter,
                &hero.plate,
                image_box,
                self.zoom,
                self.pan,
                (hero.alpha * 255.0).round() as u8,
            );
            if live_photo && self.show_revisions {
                self.revision_view.paint(
                    &photo_painter,
                    zoomed(fit(hero.plate.extent, image_box), self.zoom, self.pan),
                    hero.alpha,
                );
            }
            if live_photo {
                let destination = zoomed(fit(hero.plate.extent, image_box), self.zoom, self.pan);
                self.edit_mapping = Some((destination, image_box));
                self.navigator.paint(
                    &photo_painter,
                    destination,
                    detail_aperture,
                    detail_pin,
                    self.contribution_hovered || self.scales.interaction_hovered(),
                );
            }
        } else if let Some(source) = &self.source {
            let photo = source.current();
            let destination = zoomed(
                fit(
                    egui::vec2(photo.aperture[0] as f32, photo.aperture[1] as f32),
                    image_box,
                ),
                self.zoom,
                self.pan,
            );
            source.paint(&photo_painter, destination, full());
        } else {
            p.text(
                image_box.center(),
                Align2::CENTER_CENTER,
                "The capture will appear here",
                FontId::proportional(13.0),
                MUTED,
            );
        }
        if live_photo {
            // Apply direct manipulation only after painting. The maps, lenses,
            // locator and fingerprint all use the same frame's sampled aperture.
            if !image_gesture.reset && !image_gesture.pending {
                if let Some((pin, zoom)) = navigation.view {
                    self.scales.set_view(pin, zoom);
                    self.pin = self.scales.pin();
                }
                if let Some((factor, anchor)) = navigation.zoom {
                    self.scales.zoom_at(factor, anchor);
                    self.pin = self.scales.pin();
                }
            }
            gesture.on_hover_text("Drag box · corner or wheel adjusts detail\nClick to relocate · double-click restores scene");
            if !self.review_strip_visible {
                self.revision_view.footer(
                    ui,
                    Rect::from_min_max(
                        rect.left_bottom() + egui::vec2(10.0, -23.0),
                        rect.right_bottom() - egui::vec2(10.0, 3.0),
                    ),
                    if input.progress.revisions.history().is_empty() {
                        &self.revisions
                    } else {
                        &input.progress.revisions
                    },
                    input.frame_count,
                );
            }
        } else if !self.review_strip_visible {
            text(
                &p,
                rect.left_bottom() + egui::vec2(10.0, -19.0),
                if self.enlarged.is_some() {
                    "Shared pin / aligned sample coordinates"
                } else if self.hero.as_ref().is_some_and(|hero| hero.plate.tonal) {
                    "Live coarse green · colour and final detail follow"
                } else if self.hero.as_ref().is_some_and(|hero| hero.plate.kind == 1) {
                    "Actual accumulated detail scale · colour encodes signed coefficients"
                } else if self.hero.as_ref().is_some_and(|hero| hero.plate.kind == 2) {
                    "Green sensor reconstruction · colour development follows"
                } else {
                    "Scroll to explore · drag to move · double-click to fit"
                },
                9.0,
                MUTED,
            );
        }
        if final_owned {
            self.final_modifier(ui, rect, image_box, input);
        }
        if let Some(companion) = companion {
            self.source_relation(ui, companion, input, response);
        }
    }

    fn output_space(&self, input: &Input<'_>) -> Option<crate::process_output_space::OutputSpace> {
        self.saved_output.as_ref()?;
        crate::process_output_space::OutputSpace::from_progress(
            input.progress,
            self.saved_output_size?,
        )
    }

    fn dense_current_frame(&self) -> Option<usize> {
        if self.inspection_frame().is_some() {
            self.inspection
                .as_ref()
                .map(|slot| slot.current().index)
                .or(self.participation_frame)
        } else {
            self.participation_frame
        }
    }

    fn finished_photograph(&mut self, ui: &mut Ui, rect: Rect, image_box: Rect, input: &Input<'_>) {
        self.result_photo
            .suppress_diagnostics(input.progress.source_repair.is_some());
        let p = ui.painter_at(rect);
        let multiple = self.participation.has_ranges();
        // Use the capture actually on screen while a newly requested preview
        // is pending. The final and approximate source then share one footprint.
        let current = self.dense_current_frame();
        let label = if multiple {
            format!(
                "{} SELECTED RANGES{} / {} ADMISSION",
                self.participation.spans().len(),
                current.map_or(String::new(), |frame| format!(
                    " · CURRENT {:03}",
                    frame + 1
                )),
                crate::process_output_space::detail_label(
                    self.level,
                    input.progress.output_geometry
                ),
            )
        } else {
            match self.participation_frame {
                Some(frame) => format!(
                    "CAPTURE {:03} / {} ADMISSION",
                    frame + 1,
                    crate::process_output_space::detail_label(
                        self.level,
                        input.progress.output_geometry
                    )
                ),
                None => "YOUR PHOTOGRAPH / LINKED INSPECTION".into(),
            }
        };
        text(
            &p.with_clip_rect(Rect::from_min_max(
                rect.min,
                egui::pos2(rect.right() - 88.0, rect.top() + 28.0),
            )),
            rect.min + egui::vec2(10.0, 8.0),
            &label,
            9.0,
            if self.participation_frame.is_some() {
                GREEN
            } else {
                ACCENT
            },
        );
        let fit_button = Rect::from_min_size(
            egui::pos2(rect.right() - 78.0, rect.top() + 7.0),
            egui::vec2(68.0, 19.0),
        );
        let fit_hit = ui.interact(fit_button, ui.id().with("result-scene"), Sense::click());
        p.text(
            fit_button.center(),
            Align2::CENTER_CENTER,
            format!("{:.1}× · Scene", self.scales.aperture().width().recip()),
            FontId::monospace(8.0),
            if fit_hit.hovered() { INK } else { MUTED },
        );
        if self.annotation_mode && fit_hit.clicked() {
            if self.source_relation_rect.is_some() {
                self.scales.reset_view();
                self.source_drag = None;
                self.navigator.clear();
            } else {
                self.fit_views();
            }
            // Scales animate the reset from the aperture painted this frame;
            // drawing and photograph geometry advance together next frame.
            ui.ctx().request_repaint();
        }
        let photo = self.hero.as_ref().unwrap();
        let image = fit(photo.plate.extent, image_box);
        let aperture = self.scales.aperture();
        let full_size = image.size() / aperture.size();
        self.edit_mapping = Some((
            Rect::from_min_size(image.min - aperture.min.to_vec2() * full_size, full_size),
            image,
        ));
        self.primary_destination = Some(image);
        if self.annotation_mode {
            // A drawing gesture has a single owner. Keep the exact photo crop,
            // but do not register a competing pan/zoom/probe widget beneath it.
            self.result_photo.cancel_gesture();
            if let Some(paint) = &self.photo_paint {
                paint.paint(&p, image, aperture);
            } else {
                p.image(photo.plate.texture.id(), image, aperture, Color32::WHITE);
            }
            return;
        }
        if multiple {
            let selection = input
                .progress
                .analysis_size
                .or(input.progress.plane_size)
                .and_then(|extent| {
                    self.dense_admission.selection_with_current(
                        &input.progress.admission_archive,
                        [input.epoch, input.progress.diagnostic_epoch],
                        self.participation.spans(),
                        current,
                        self.level,
                        extent,
                        crate::process_admission_regions::RegionSettings::read(ui.ctx()),
                    )
                });
            self.result_photo.configure_dense_selection(selection);
        } else {
            let dense = self
                .participation_frame
                .zip(input.progress.analysis_size.or(input.progress.plane_size))
                .and_then(|(frame, extent)| {
                    self.dense_admission.region(
                        &input.progress.admission_archive,
                        [input.epoch, input.progress.diagnostic_epoch],
                        frame,
                        self.level,
                        extent,
                        crate::process_admission_regions::RegionSettings::read(ui.ctx()),
                    )
                });
            self.result_photo.configure_dense_region(dense);
        }
        let action = self.result_photo.show(
            ui,
            image_box,
            crate::process_result::Context {
                texture: &photo.plate.texture,
                extent: photo.plate.extent,
                aperture: self.scales.aperture(),
                pin: self.scales.painted_pin(),
                archive: &input.progress.admission_archive,
                level: self.level,
                frame: if multiple {
                    current
                } else {
                    self.participation_frame
                },
                spans: self.participation.spans(),
                linked_hover: self.contribution_hovered || self.scales.interaction_hovered(),
            },
        );
        if action.reset || fit_hit.clicked() {
            if self.source_relation_rect.is_some() {
                self.scales.reset_view();
                self.source_drag = None;
                self.navigator.clear();
            } else {
                self.fit_views();
            }
        } else {
            if let Some((pin, zoom)) = action.view {
                self.scales.set_view(pin, zoom);
            }
            if let Some(region) = action.region {
                self.scales.focus_region(region);
            }
            if let Some((factor, anchor)) = action.zoom {
                self.scales.zoom_photo_at(factor, anchor);
            }
            if let Some(pin) = action.focus {
                self.scales.set_pin(pin);
                self.scales.focus_pin();
            }
        }
        self.pin = self.scales.pin();
        let caption = if input.progress.source_repair.is_some() {
            "Locally rebuilt photograph · matrix and timeline retain original-merge evidence"
        } else if ui.input(|state| state.key_down(egui::Key::Space)) {
            "Clean photograph · release Space to restore inspection"
        } else if let Some(frame) = self.participation_frame {
            if input
                .progress
                .admission_archive
                .metadata(self.level, frame)
                .is_some()
            {
                if self.participation_held {
                    "Held footprint · Space: clean view · Escape: release"
                } else {
                    "Sampled footprint · click strip to hold · Space: clean view"
                }
            } else {
                "No retained admission samples for this capture + detail size"
            }
        } else {
            if self.scales.aperture().width() > 0.99 {
                "Drag: select a region · wheel: zoom · double-click: scene"
            } else {
                "Drag: pan · Shift-drag: select a region · double-click: scene"
            }
        };
        if !self.review_strip_visible && photograph_footer(rect) >= 53.0 {
            text(
                &p,
                rect.left_bottom() + egui::vec2(10.0, -19.0),
                caption,
                8.5,
                MUTED,
            );
        }
    }

    fn final_modifier(&self, ui: &mut Ui, rect: Rect, _image_box: Rect, input: &Input<'_>) {
        if input.progress.source_repair.is_some() || ui.input(|i| i.key_down(egui::Key::Space)) {
            return;
        }
        let Some(destination) = self.primary_destination else {
            return;
        };
        let p = ui.painter_at(rect);
        if self.output_space(input).is_none() {
            return;
        }
        if let Some(kind) = self
            .review_hover
            .map(|_| DiagnosticKind::Averaging)
            .or(self.enlarged)
            && let Some(map) = self
                .observations
                .iter()
                .find(|m| m.meta.kind == kind && m.level == self.review_hover.unwrap_or(self.level))
        {
            let geometry = map.packet.as_ref().and_then(|packet| {
                crate::process_sample_glyphs::SampleGeometry::new(
                    map.level,
                    crate::process_provenance::AdmissionMeta {
                        sequence: packet.sequence,
                        samples: [packet.width, packet.height],
                        extent: input.progress.analysis_size.or(input.progress.plane_size)?,
                    },
                )
            });
            if let (Some(geometry), Some(packet)) = (geometry, map.packet.as_ref()) {
                let colors = crate::app::diagnostic_image(packet);
                for (index, &value) in packet.pixels.iter().enumerate() {
                    // A binary admission packet only asserts its observed
                    // positive samples. Scalar packets retain their palette,
                    // but never inflate a sparse observation into a region.
                    if matches!(
                        kind,
                        DiagnosticKind::GateSupport | DiagnosticKind::Averaging
                    ) && value == 0
                    {
                        continue;
                    }
                    if let (Some(glyph), Some(&color)) =
                        (geometry.at(index), colors.pixels.get(index))
                    {
                        crate::process_sample_glyphs::paint_glyph(
                            &p,
                            destination,
                            self.scales.aperture(),
                            glyph,
                            color,
                            true,
                        );
                    }
                }
            } else {
                // An image without a valid sampling lattice is still a real
                // diagnostic, but cannot certify positions on the photograph.
                let inset = fit(
                    map.texture.size_vec2(),
                    Rect::from_min_size(
                        destination.right_top() + egui::vec2(-176.0, 28.0),
                        egui::vec2(168.0, 108.0),
                    )
                    .intersect(destination),
                );
                p.rect_filled(inset.expand(4.0), 0.0, crate::theme::BG);
                p.image(map.texture.id(), inset, full(), Color32::WHITE);
                text(
                    &p,
                    inset.left_bottom() + egui::vec2(0.0, 4.0),
                    "SAMPLE POSITIONS UNAVAILABLE",
                    7.0,
                    MUTED,
                );
            }
            text(
                &p,
                destination.left_top() + egui::vec2(6.0, 6.0),
                &format!(
                    "{} · SAMPLES / {} FOLDED{}",
                    signal_name(kind),
                    map.meta.folded,
                    if self.review_hover.is_some() {
                        ""
                    } else {
                        " · Fit to clear"
                    }
                ),
                8.0,
                ACCENT,
            );
        }
    }

    fn source_relation(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        response: &mut Response,
    ) {
        if rect.height() < 100.0 || rect.width() < 180.0 {
            return;
        }
        let p = ui.painter_at(rect);
        p.rect_filled(rect, 0.0, crate::theme::BG);
        p.line_segment(
            [
                rect.left_top(),
                if self.source_relation_axis == Some(SourceRelationAxis::Columns) {
                    rect.left_bottom()
                } else {
                    rect.right_top()
                },
            ],
            Stroke::new(ui.ctx().pixels_per_point().recip(), LINE),
        );
        let close = Rect::from_min_size(
            rect.right_top() + egui::vec2(-48.0, 4.0),
            egui::vec2(44.0, 22.0),
        );
        let image_box = Rect::from_min_max(
            rect.min + egui::vec2(10.0, 36.0),
            rect.max - egui::vec2(10.0, photograph_footer(rect)),
        );
        if self.inspection.is_some() {
            self.source_photograph(ui, rect, image_box, input);
        } else {
            text(
                &p,
                rect.min + egui::vec2(10.0, 8.0),
                "SOURCE / CAMERA SPACE",
                9.0,
                ACCENT,
            );
            p.text(
                image_box.center(),
                Align2::CENTER_CENTER,
                "Fetching the selected camera preview",
                FontId::proportional(10.0),
                MUTED,
            );
        }
        self.source_admission_strip(ui, rect, input);
        let close_hit = ui.interact(close, ui.id().with("source-relation-close"), Sense::click());
        p.rect_filled(close, 0.0, crate::theme::BG);
        p.text(
            close.center(),
            Align2::CENTER_CENTER,
            "Close",
            FontId::proportional(9.0),
            if close_hit.hovered() { INK } else { MUTED },
        );
        if close_hit.clicked() {
            self.resume_live();
            self.participation.clear();
            self.participation_frame = None;
            self.participation_held = false;
            response.return_live = true;
        }
        close_hit.on_hover_text(
            "Close source comparison · Escape or Photograph also returns to the clean final",
        );
    }

    /// These small maps use the final photograph's certified analysis domain.
    /// The camera preview above shares only normalized navigation, not registration.
    fn source_admission_strip(&mut self, ui: &mut Ui, rect: Rect, input: &Input<'_>) {
        let footer = Rect::from_min_max(
            rect.left_bottom() + egui::vec2(10.0, 3.0 - photograph_footer(rect)),
            rect.max - egui::vec2(10.0, 1.0),
        );
        let p = ui.painter_at(footer);
        p.rect_filled(footer, 0.0, crate::theme::BG);
        let Some(frame) = self.inspection.as_ref().map(|slot| slot.current().index) else {
            return;
        };
        let Some(_) = self.output_space(input) else {
            text(
                &p,
                footer.min + egui::vec2(0.0, 15.0),
                "CAMERA SPACE · correspondence unavailable",
                8.0,
                MUTED,
            );
            return;
        };
        let Some(hero) = self.hero.as_ref().filter(|hero| hero.plate.kind == 3) else {
            return;
        };
        let levels = input
            .progress
            .bands
            .map(|bands| bands.saturating_add(1))
            .unwrap_or_else(|| {
                input
                    .progress
                    .admission_archive
                    .levels()
                    .max()
                    .map_or(0, |level| level + 1)
            })
            .min(16);
        if levels == 0 {
            return;
        }
        let title = Rect::from_min_size(footer.min, egui::vec2(46.0, footer.height()));
        text(&p, title.min + egui::vec2(0.0, 3.0), "FINAL", 8.0, MUTED);
        text(
            &p,
            title.min + egui::vec2(0.0, 14.0),
            "admit / px",
            7.0,
            MUTED,
        );
        let lane = Rect::from_min_max(footer.min + egui::vec2(48.0, 0.0), footer.max);
        let cell_width = lane.width() / levels as f32;
        let aperture = self.scales.aperture();
        let analysis_extent = input
            .progress
            .analysis_size
            .or(input.progress.plane_size)
            .unwrap();
        let bands = self.source_admission.bands(
            &input.progress.admission_archive,
            [input.epoch, input.progress.diagnostic_epoch],
            frame,
            analysis_extent,
            levels,
        );
        for (level, band) in bands.iter().enumerate() {
            let cell = Rect::from_min_size(
                lane.min + egui::vec2(level as f32 * cell_width, 0.0),
                egui::vec2(cell_width, lane.height()),
            );
            let canvas = Rect::from_min_max(
                cell.min + egui::vec2(2.0, 1.0),
                cell.max - egui::vec2(2.0, 15.0),
            );
            let destination = fit(hero.plate.extent, canvas);
            p.image(
                hero.plate.texture.id(),
                destination,
                full(),
                Color32::from_white_alpha(115),
            );
            let color = crate::process_sample_glyphs::level_color(level);
            let counts = band.counts;
            for point in &band.points {
                p.circle_filled(
                    destination.min + point.to_vec2() * destination.size(),
                    0.7,
                    color,
                );
            }
            if counts.is_none() {
                p.line_segment(
                    [destination.left_bottom(), destination.right_top()],
                    Stroke::new(0.6_f32, MUTED),
                );
            }
            if aperture.width() < 0.99 {
                let view = Rect::from_min_max(
                    destination.min + aperture.min.to_vec2() * destination.size(),
                    destination.min + aperture.max.to_vec2() * destination.size(),
                );
                p.rect_stroke(
                    view,
                    0.0,
                    Stroke::new(0.8_f32, Color32::WHITE),
                    egui::StrokeKind::Inside,
                );
            }
            let spacing = (1u64 << level) as f32 * hero.plate.extent.x / analysis_extent[0] as f32;
            let label = p.layout_no_wrap(format!("{spacing:.0}"), FontId::monospace(7.0), color);
            if label.size().x <= cell.width() - 2.0 {
                p.galley(
                    egui::pos2(
                        cell.center().x - label.size().x * 0.5,
                        cell.bottom() - 3.0 - label.size().y,
                    ),
                    label,
                    color,
                );
            }
            if level == self.level {
                p.line_segment(
                    [cell.left_bottom(), cell.right_bottom()],
                    Stroke::new(1.0_f32, color),
                );
            }
            let hit = ui.interact(
                cell,
                ui.id().with(("source-final-admission", level)),
                Sense::click(),
            );
            if hit.clicked() {
                self.level = level;
                self.level_touched = true;
                self.scales.select_level(level);
            }
            hit.on_hover_text(match counts {
                Some((admitted, total)) => format!("Capture {:03} · {spacing:.0} output-pixel coefficient spacing\n{admitted}/{total} observed samples admitted (positive merge weight). These maps are in final-image coordinates. White box: linked region. Camera correspondence above is approximate; no measured contribution fraction is implied.", frame + 1),
                None => format!("Capture {:03} · no retained admission samples at this detail size", frame + 1),
            });
        }
    }

    fn origins(&mut self, ui: &mut Ui, layout: Layout, input: &Input<'_>, response: &mut Response) {
        for (index, rect) in layout.origins.into_iter().enumerate() {
            let p = ui.painter_at(rect);
            let has_pair = input
                .inspected_pair
                .or(input.progress.alignment_current_pair)
                .or(input.progress.alignment_latest_pair)
                .is_some();
            text(
                &p,
                rect.min,
                if self.inspected_source.is_some() {
                    if index == 0 {
                        "INSPECTED SOURCE"
                    } else {
                        "CONTEXT / SOURCE"
                    }
                } else {
                    match (has_pair, index) {
                        (true, 0) => "PAIR / A",
                        (true, _) => "PAIR / B",
                        (false, 0) => "CAMERA ORIGINAL",
                        (false, _) => "CAMERA CONTEXT",
                    }
                },
                8.0,
                MUTED,
            );
            let frame = Rect::from_min_max(
                rect.min + egui::vec2(0.0, 16.0),
                rect.max - egui::vec2(0.0, 17.0),
            );
            p.rect_filled(frame, 0.0, PANEL);
            if let Some(slot) = &self.pair[index] {
                let photo = slot.current();
                let destination = fit(
                    egui::vec2(photo.aperture[0] as f32, photo.aperture[1] as f32),
                    frame,
                );
                slot.paint(&p, destination, full());
                text(
                    &p,
                    rect.left_bottom() - egui::vec2(0.0, 13.0),
                    &format!("{:03} / ORIGINAL", photo.index + 1),
                    8.0,
                    ACCENT,
                );
                if ui
                    .interact(
                        rect,
                        ui.id().with(("theater-origin", index)),
                        Sense::click(),
                    )
                    .clicked()
                {
                    let selected = photo.index;
                    if input.progress.stage == Stage::Complete {
                        self.participation.select_frame(selected);
                        self.inspect_frame(selected);
                        response.selected = Some(selected);
                    } else {
                        response.selected = Some(selected);
                        self.inspected_source = Some(selected);
                    }
                }
            }
        }
    }

    fn source_photograph(&mut self, ui: &mut Ui, rect: Rect, image_box: Rect, input: &Input<'_>) {
        let linked = self.output_space(input).is_some()
            && self.hero.as_ref().is_some_and(|hero| hero.plate.kind == 3);
        let Some(slot) = &self.inspection else { return };
        let photo = slot.current();
        let extent = egui::vec2(photo.aperture[0] as f32, photo.aperture[1] as f32);
        let base = fit(extent, image_box);
        let painter = ui.painter_at(rect);
        let requested = self.inspection_frame().unwrap_or(photo.index);
        let capture_color = self
            .participation
            .spans()
            .iter()
            .find(|span| span.contains(photo.index))
            .map_or(ACCENT, |span| span.color());
        let title = Rect::from_min_max(
            rect.min + egui::vec2(10.0, 7.0),
            egui::pos2(rect.right() - 52.0, rect.top() + 34.0),
        );
        text(
            &painter.with_clip_rect(title),
            title.min,
            &format!(
                "SOURCE {:03} / CAMERA{}",
                photo.index + 1,
                if requested != photo.index {
                    format!(" · {:03} pending", requested + 1)
                } else {
                    String::new()
                }
            ),
            9.0,
            capture_color,
        );
        text(
            &painter.with_clip_rect(title),
            title.min + egui::vec2(0.0, 13.0),
            &if linked && self.participation.has_ranges() {
                format!(
                    "SELECTED REGIONS · APPROXIMATE · CURRENT {:03}",
                    photo.index + 1
                )
            } else if linked {
                "LINKED REGION · APPROXIMATE".to_owned()
            } else {
                "CAMERA SPACE".to_owned()
            },
            7.5,
            MUTED,
        );
        let hit = ui.interact(
            image_box,
            ui.id().with("primary-source-photo"),
            Sense::click_and_drag(),
        );
        let allowed = ui.is_enabled()
            && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
            && !egui::Popup::is_any_open(ui.ctx())
            && ui.input(|i| {
                i.focused
                    && i.viewport().focused != Some(false)
                    && i.viewport().minimized != Some(true)
            });
        let gesture = crate::image_gesture::reset(ui, &hit);
        // Both photographs paint the same frame-stable aperture. Mutations below
        // are committed together on the next paint, including an easing zoom.
        let shared_aperture = self.scales.aperture();
        if allowed
            && ui.input(|i| i.pointer.primary_pressed())
            && hit.contains_pointer()
            && let Some(at) = ui.input(|i| i.pointer.press_origin())
        {
            self.source_drag = Some((
                at,
                shared_aperture.center(),
                shared_aperture.width().recip(),
            ));
        }
        if allowed && gesture.reset {
            self.source_drag = None;
            if linked {
                self.scales.reset_view();
                self.navigator.clear();
            } else {
                self.source_zoom = 1.0;
                self.source_pan = Vec2::ZERO;
            }
        } else if allowed && !gesture.pending {
            if hit.hovered() {
                let wheel = ui.input(|i| i.raw_scroll_delta.y);
                let pinch = crate::process_region_probe::zoom_delta(ui);
                let factor = if (pinch - 1.0).abs() > f32::EPSILON {
                    pinch
                } else {
                    (wheel * 0.004).exp()
                };
                if factor.is_finite() && (factor - 1.0).abs() > f32::EPSILON {
                    if linked {
                        self.scales.zoom_photo_at(
                            factor,
                            normalized(hit.hover_pos().unwrap_or(base.center()), base),
                        );
                    } else {
                        let next = (self.source_zoom * factor).clamp(1.0, 16.0);
                        if let Some(at) = hit.hover_pos() {
                            let ratio = next / self.source_zoom;
                            self.source_pan =
                                self.source_pan * ratio + (at - image_box.center()) * (1.0 - ratio);
                        }
                        self.source_zoom = next;
                    }
                    self.source_drag = None;
                    ui.ctx().request_repaint();
                }
            }
            if hit.dragged() {
                if linked {
                    if let Some((origin, pin, zoom)) = self.source_drag
                        && let Some(at) = ui.input(|i| i.pointer.interact_pos())
                    {
                        self.scales
                            .set_view(pin - (at - origin) / base.size() / zoom, zoom);
                    }
                } else {
                    self.source_pan += ui.input(|i| i.pointer.delta());
                }
                ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
            } else if hit.hovered() {
                ui.ctx().set_cursor_icon(egui::CursorIcon::Grab);
            }
        }
        if !allowed
            || ui.input(|i| {
                !i.pointer.primary_down() || i.key_pressed(egui::Key::Escape) || !i.focused
            })
        {
            self.source_drag = None;
        }
        let (destination, uv, zoom) = if linked {
            self.pin = self.scales.pin();
            (base, shared_aperture, shared_aperture.width().recip())
        } else {
            let limit = ((base.size() * self.source_zoom - image_box.size()) * 0.5).max(Vec2::ZERO);
            let pan = self.source_pan.clamp(-limit, limit);
            if self.hover_source.is_none() && self.inspected_source.is_some() {
                self.source_pan = pan;
            }
            (
                zoomed(base, self.source_zoom, pan),
                full(),
                self.source_zoom,
            )
        };
        slot.paint(&painter.with_clip_rect(image_box), destination, uv);
        // The source JPEG has no saved registration/crop certificate. Show
        // this deliberately as a dashed normalized-location estimate; the
        // solid region on the final photograph remains the measured domain.
        if linked
            && crate::process_result::ResultPhoto::admission_visible(ui.ctx())
            && !ui.input(|i| i.key_down(egui::Key::Space))
            && let Some(analysis) = input.progress.analysis_size.or(input.progress.plane_size)
        {
            let settings = crate::process_admission_regions::RegionSettings::read(ui.ctx());
            if self.participation.has_ranges() {
                if let Some(selection) = self.dense_admission.selection_with_current(
                    &input.progress.admission_archive,
                    [input.epoch, input.progress.diagnostic_epoch],
                    self.participation.spans(),
                    Some(photo.index),
                    self.level,
                    analysis,
                    settings,
                ) {
                    self.source_selection_painter.paint_approximate(
                        &painter.with_clip_rect(image_box),
                        &selection,
                        destination,
                        uv,
                    );
                }
            } else if let Some(region) = self.dense_admission.region(
                &input.progress.admission_archive,
                [input.epoch, input.progress.diagnostic_epoch],
                photo.index,
                self.level,
                analysis,
                settings,
            ) {
                self.source_region_painter.paint_approximate(
                    &painter.with_clip_rect(image_box),
                    &region,
                    destination,
                    uv,
                    crate::process_sample_glyphs::level_color(self.level),
                );
            }
        }
        if zoom > 1.01 {
            let overview_box = if linked {
                let size = egui::vec2(112.0, 78.0).min(base.size() * 0.34);
                Rect::from_min_size(base.max - size - Vec2::splat(9.0), size)
            } else {
                Rect::from_min_size(
                    image_box.right_bottom() - egui::vec2(122.0, 88.0),
                    egui::vec2(112.0, 78.0),
                )
            };
            let overview = fit(extent, overview_box);
            painter.rect_filled(overview.expand(4.0), 0.0, crate::theme::BG);
            slot.paint(&painter, overview, full());
            let region = if linked {
                uv
            } else {
                Rect::from_min_max(
                    normalized(image_box.min, destination),
                    normalized(image_box.max, destination),
                )
            };
            let viewport = Rect::from_min_max(
                overview.min + region.min.to_vec2() * overview.size(),
                overview.min + region.max.to_vec2() * overview.size(),
            );
            painter.rect_stroke(
                viewport,
                0.0,
                Stroke::new(1.0_f32, ACCENT),
                egui::StrokeKind::Inside,
            );
        }
        if !linked {
            text(
                &painter,
                rect.left_bottom() + egui::vec2(10.0, -19.0),
                &format!(
                    "{zoom:.1}× · {} · wheel zoom / drag pan",
                    if photo.index >= input.processing_count() {
                        "outside rendered prefix"
                    } else {
                        "camera coordinates"
                    }
                ),
                8.0,
                MUTED,
            );
        }
        hit.on_hover_text(if linked {
            "Solid shading on the final photograph estimates dense admission. Dashed shading here shows its approximate normalized location: this camera JPEG has no saved registration or sensor-crop certificate. Zoom and pan both together; double-click resets."
        } else { "Camera preview · wheel to zoom · drag to pan · double-click to fit" });
    }

    fn timeline_controls(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        input: &Input<'_>,
        response: &mut Response,
    ) {
        let photo_label = if input.progress.stage == Stage::Complete {
            "Photograph"
        } else {
            "Live"
        };
        let complete = input.progress.stage == Stage::Complete;
        let controls = [
            (photo_label, 83.0),
            (
                if complete {
                    "Source + final"
                } else {
                    "Sources"
                },
                if complete { 96.0 } else { 68.0 },
            ),
            ("Fit", 42.0),
            ("Undo", 48.0),
            ("Redo", 48.0),
        ];
        let mut x = rect.left();
        for (index, (label, width)) in controls.into_iter().enumerate() {
            let cell = Rect::from_min_size(egui::pos2(x, rect.top()), egui::vec2(width, 22.0));
            x += width;
            let enabled = match index {
                1 => input.frame_count > 0,
                3 => self.can_undo(),
                4 => self.can_redo(),
                _ => true,
            };
            let hit = ui.interact(
                cell,
                ui.id().with(("timeline-control", index)),
                Sense::click(),
            );
            let active = match index {
                0 => !self.inspecting(),
                1 => self.inspection_frame().is_some(),
                _ => false,
            };
            let p = ui.painter_at(cell);
            p.text(
                cell.center(),
                Align2::CENTER_CENTER,
                label,
                FontId::proportional(10.0),
                if !enabled {
                    MUTED.gamma_multiply(0.45)
                } else if active || hit.hovered() {
                    INK
                } else {
                    MUTED
                },
            );
            if active {
                p.line_segment(
                    [cell.left_bottom(), cell.right_bottom()],
                    Stroke::new(ui.ctx().pixels_per_point().recip(), ACCENT),
                );
            }
            if enabled && hit.clicked() {
                match index {
                    0 => {
                        self.resume_live();
                        self.participation.clear();
                        self.participation_frame = None;
                        self.participation_held = false;
                        response.return_live = true;
                    }
                    1 => {
                        let index = input.selected.min(input.frame_count - 1);
                        self.inspect_frame(index);
                        if complete {
                            self.participation.select_frame(index);
                        }
                        response.selected = Some(index);
                    }
                    2 => self.fit_views(),
                    3 => {
                        self.undo();
                    }
                    4 => {
                        self.redo();
                    }
                    _ => {}
                }
            }
            hit.on_hover_cursor(egui::CursorIcon::PointingHand)
                .on_hover_text(match index {
                    0 => "Return to the current photograph · Escape also fits the view",
                    1 if complete => "Compare the selected camera source beside the final photograph. Its observed admission is marked on the final; camera pixels stay unregistered. Escape closes the comparison.",
                    1 => "Click or drag the capture thumbnails to sweep sources in the main viewer",
                    2 => "Reset image and linked detail magnification · double-click also resets",
                    3 => "Undo the last exploration gesture · Ctrl+Z",
                    _ => "Redo exploration · Ctrl+Shift+Z or Ctrl+Y",
                });
        }
        let p = ui.painter_at(Rect::from_min_max(
            egui::pos2(x + 14.0, rect.top()),
            rect.right_top() + egui::vec2(0.0, 22.0),
        ));
        let caption: String = if self.enlarged.is_some() {
            "MAP INSPECTION · Fit or Escape to return".into()
        } else if complete {
            "Hover: explore · wheel: step · Photograph / Esc: return · Shift: span".into()
        } else {
            "Thumbnails: sweep sources · lanes: select contributions".into()
        };
        text(
            &p,
            egui::pos2(x + 14.0, rect.top() + 6.0),
            &caption,
            8.0,
            MUTED,
        );
    }

    fn signals(&mut self, ui: &mut Ui, layout: Layout, input: &Input<'_>) {
        self.scales.set_pin(self.pin);
        if let Some(pick) = self.scales.show(ui, layout.signals, input) {
            self.level = pick.level;
            self.level_touched = true;
            self.selected_signal = pick.kind;
            self.pin = self.scales.pin();
            if pick.reset {
                self.fit_views();
            } else if pick.enlarge || self.enlarged.is_some() {
                self.enlarged = Some(pick.kind);
            }
        }
        self.pin = self.scales.pin();
        // Inspection and the physical readout must use the same generation as
        // the visible tile, including while a newer delivery is deferred.
        for surface in self.scales.presented_surfaces() {
            let Some(meta) = surface.meta else { continue };
            if let Some(item) = self
                .observations
                .iter_mut()
                .find(|item| item.level == surface.level && item.meta.kind == meta.kind)
            {
                item.texture = surface.texture.clone();
                item.meta = meta;
                item.frame = surface.frame;
                item.packet = surface.packet.cloned();
            }
        }
    }

    fn convergence(
        &self,
        ui: &mut Ui,
        _layout: Layout,
        input: &Input<'_>,
        instruments: Option<Rect>,
    ) {
        let Some(destination) = self.primary_destination else {
            return;
        };
        let p = ui.painter().with_clip_rect(Rect::from_min_max(
            ui.clip_rect().min,
            egui::pos2(destination.left(), ui.clip_rect().bottom()),
        ));
        let end = destination.left_center();
        for port in self.scales.output_ports() {
            if instruments.is_some_and(|clip| !clip.contains(port.position)) {
                continue;
            }
            let done = input
                .progress
                .merge_bands
                .get(&port.level)
                .map_or(0, |work| work.completed);
            let from = port.position;
            let color = if port.observed && port.folded > 0 {
                GREEN.gamma_multiply(0.52)
            } else if done > 0 {
                ACCENT.gamma_multiply(0.34)
            } else {
                LINE.gamma_multiply(0.4)
            };
            p.add(egui::epaint::CubicBezierShape::from_points_stroke(
                [
                    from,
                    from + egui::vec2(14.0, 0.0),
                    end - egui::vec2(14.0, 0.0),
                    end,
                ],
                false,
                Color32::TRANSPARENT,
                Stroke::new(1.0_f32, color),
            ));
        }
    }

    fn levels(&self, input: &Input<'_>) -> usize {
        input
            .progress
            .bands
            .map_or(0, |bands| bands.saturating_add(1))
            .max(
                self.observations
                    .iter()
                    .map(|item| item.level + 1)
                    .max()
                    .unwrap_or(1),
            )
            .max(
                input
                    .progress
                    .merge_bands
                    .keys()
                    .next_back()
                    .map_or(1, |level| level + 1),
            )
            .clamp(1, 64)
    }
}

fn signal_name(kind: DiagnosticKind) -> &'static str {
    match kind {
        DiagnosticKind::FocusEnergy => "01 / DETAIL ENERGY",
        DiagnosticKind::GateFloor => "02 / NOISE FLOOR",
        DiagnosticKind::GateSupport => "03 / POSITIVE WEIGHT",
        DiagnosticKind::Averaging => "04 / FALLBACK",
        DiagnosticKind::Coefficient => "05 / MERGED BAND",
        DiagnosticKind::Preview => "LIVE COARSE GREEN",
        DiagnosticKind::Reconstructed => "GREEN RECONSTRUCTION",
    }
}
fn full() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}
fn extent(input: &Input<'_>, texture: &TextureHandle) -> Vec2 {
    input
        .progress
        .analysis_size
        .or(input.progress.plane_size)
        .filter(|size| !size.contains(&0))
        .map_or_else(
            || texture.size_vec2(),
            |size| egui::vec2(size[0] as f32, size[1] as f32),
        )
}
fn fit(size: Vec2, rect: Rect) -> Rect {
    let scale = (rect.width() / size.x).min(rect.height() / size.y).max(0.0);
    Rect::from_center_size(rect.center(), size * scale)
}
fn zoomed(rect: Rect, zoom: f32, pan: Vec2) -> Rect {
    Rect::from_center_size(rect.center() + pan, rect.size() * zoom)
}
fn normalized(point: Pos2, rect: Rect) -> Pos2 {
    let uv = (point - rect.min) / rect.size();
    egui::pos2(uv.x.clamp(0.0, 1.0), uv.y.clamp(0.0, 1.0))
}
fn paint_plate(p: &Painter, plate: &Plate, rect: Rect, zoom: f32, pan: Vec2, alpha: u8) {
    p.image(
        plate.texture.id(),
        zoomed(fit(plate.extent, rect), zoom, pan),
        plate.uv,
        Color32::from_white_alpha(alpha),
    );
}
/// Caption capacity is a property of the container, never the processing
/// phase or arriving data. Compact photos keep one lane; taller ones gain a
/// second lane smoothly as the user enlarges the workspace.
fn photograph_footer(rect: Rect) -> f32 {
    30.0 + ((rect.height() - 340.0) / 80.0).clamp(0.0, 1.0) * 24.0
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum SourceRelationAxis {
    Columns,
    Rows,
}

fn source_relation_axis(
    rect: Rect,
    extents: [Vec2; 2],
    previous: Option<SourceRelationAxis>,
) -> SourceRelationAxis {
    let score = |axis| {
        let (left, right) = source_relation_layout(rect, 1.0, axis);
        [left, right.unwrap()]
            .into_iter()
            .zip(extents)
            .map(|(panel, extent)| {
                let available = (panel.size() - egui::vec2(20.0, 36.0 + photograph_footer(panel)))
                    .max(Vec2::ZERO);
                fit(
                    extent.max(Vec2::splat(1.0)),
                    Rect::from_min_size(Pos2::ZERO, available),
                )
                .area()
            })
            .sum::<f32>()
    };
    let columns = score(SourceRelationAxis::Columns);
    let rows = score(SourceRelationAxis::Rows);
    // Small resizes near the crossover cannot repeatedly flip the comparison.
    match previous {
        Some(SourceRelationAxis::Columns) if rows <= columns * 1.08 => SourceRelationAxis::Columns,
        Some(SourceRelationAxis::Rows) if columns <= rows * 1.08 => SourceRelationAxis::Rows,
        _ if columns >= rows => SourceRelationAxis::Columns,
        _ => SourceRelationAxis::Rows,
    }
}
fn source_relation_layout(rect: Rect, mix: f32, axis: SourceRelationAxis) -> (Rect, Option<Rect>) {
    let mix = mix.clamp(0.0, 1.0);
    if mix <= 0.001 {
        return (rect, None);
    }
    if axis == SourceRelationAxis::Columns {
        let width = ((rect.width() - 8.0).max(0.0) * 0.5) * mix;
        let source = Rect::from_min_max(egui::pos2(rect.right() - width, rect.top()), rect.max);
        let final_rect = Rect::from_min_max(
            rect.min,
            egui::pos2(source.left() - 8.0 * mix, rect.bottom()),
        );
        (final_rect, Some(source))
    } else {
        let height = ((rect.height() - 8.0).max(0.0) * 0.5) * mix;
        let source = Rect::from_min_max(egui::pos2(rect.left(), rect.bottom() - height), rect.max);
        let final_rect =
            Rect::from_min_max(rect.min, egui::pos2(rect.right(), source.top() - 8.0 * mix));
        (final_rect, Some(source))
    }
}

fn text(p: &Painter, at: Pos2, value: &str, size: f32, color: Color32) {
    p.text(
        at,
        Align2::LEFT_TOP,
        value,
        FontId::proportional(size),
        color,
    );
}
fn crosshair(p: &Painter, rect: Rect, uv: Pos2) {
    let point = rect.min + uv.to_vec2() * rect.size();
    let p = p.with_clip_rect(rect);
    p.circle_stroke(point, 4.0, Stroke::new(1.0_f32, Color32::WHITE));
    for (a, b) in [
        (egui::vec2(-10.0, 0.0), egui::vec2(-5.0, 0.0)),
        (egui::vec2(5.0, 0.0), egui::vec2(10.0, 0.0)),
        (egui::vec2(0.0, -10.0), egui::vec2(0.0, -5.0)),
        (egui::vec2(0.0, 5.0), egui::vec2(0.0, 10.0)),
    ] {
        p.line_segment([point + a, point + b], Stroke::new(1.0_f32, ACCENT));
    }
}

fn sample_value(surface: &crate::pipeline::DiagnosticSurface, pin: Pos2) -> Option<f32> {
    let x = ((pin.x * surface.width as f32) as usize).min(surface.width.checked_sub(1)?);
    let y = ((pin.y * surface.height as f32) as usize).min(surface.height.checked_sub(1)?);
    let t = *surface.pixels.get(y * surface.width + x)? as f32 / 255.0;
    Some(match surface.scale {
        DiagnosticScale::Linear => surface.min + t * (surface.max - surface.min),
        DiagnosticScale::Log => (surface.min.max(0.0).ln_1p()
            + t * (surface.max.max(0.0).ln_1p() - surface.min.max(0.0).ln_1p()))
        .exp_m1(),
        DiagnosticScale::Symmetric => {
            let span = surface.min.abs().max(surface.max.abs()).ln_1p();
            let value = (2.0 * t - 1.0) * span;
            value.signum() * value.abs().exp_m1()
        }
    })
}

/// Fixed display exposure for the whole run. Later accumulated snapshots cannot
/// pump the preview contrast merely because their local extrema changed.
fn preview_tone_image(
    surface: &crate::pipeline::DiagnosticSurface,
    range: (f32, f32),
) -> egui::ColorImage {
    let span = range.1 - range.0;
    let pixels = (0..surface.height)
        .flat_map(|y| {
            (0..surface.width).map(move |x| {
                let pin = egui::pos2(
                    (x as f32 + 0.5) / surface.width as f32,
                    (y as f32 + 0.5) / surface.height as f32,
                );
                let value = sample_value(surface, pin).unwrap_or(range.0);
                let linear = if span > 0.0 {
                    ((value - range.0) / span).clamp(0.0, 1.0)
                } else {
                    0.5
                };
                Color32::from_gray((linear.powf(1.0 / 2.2) * 255.0).round() as u8)
            })
        })
        .collect();
    egui::ColorImage::new([surface.width, surface.height], pixels)
}

#[cfg(test)]
#[path = "process-theater-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "process-immersion-tests.rs"]
mod immersion_tests;

#[cfg(test)]
#[path = "process-inspection-tests.rs"]
mod inspection_tests;

#[cfg(test)]
#[path = "process-navigation-tests.rs"]
mod navigation_tests;

#[cfg(test)]
#[path = "process-result-tests.rs"]
mod result_tests;

#[cfg(test)]
#[path = "process-theater-v22-hover-tests.rs"]
mod v22_hover_tests;

#[cfg(test)]
#[path = "process-live-preview-tests.rs"]
mod live_preview_tests;

#[cfg(test)]
#[path = "process-theater-v24-review-tests.rs"]
mod v24_review_tests;

#[cfg(test)]
#[path = "process-theater-v26-perf-tests.rs"]
mod v26_perf_tests;
