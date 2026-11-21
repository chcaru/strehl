//! The focus rail (Studio 2, 7.4): the lens travel in the camera's focus
//! units, the bounds survey's sharpness profile as bars, every planned plane
//! as a tick, the Start and End handles and the lens.
//!
//! Spec 5.4: the bars and ticks are one cached `Arc<Mesh>`, rebuilt only when
//! the survey, the plan, the flight's plane states, the rectangle or the
//! display scale change; ticks are pooled to at most one per 2 px column.
//! The hover line, the handles' labels and the lens are separate cheap shapes,
//! so pointer motion rebuilds nothing.
use std::sync::Arc;

use eframe::egui::{self, Align2, Color32, Event, Key, Mesh, Pos2, Rect, Sense, Shape, Stroke, Ui};

use super::style::{self, ButtonKind, CapturePalette};
use crate::capture_client::host::SurveySample;

/// What became of a plane in flight, for its tick.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum TickState {
    /// Checked on this PC.
    Checked,
    /// Taken again during the capture.
    Retaken,
    /// The stack will not assemble it as recorded.
    Attention,
    /// Taken, but its RAWs are still on the camera host.
    OnHost,
    /// Not taken yet.
    ToCome,
}

/// The planes of a capture in flight: their positions and states.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct FlightTicks {
    pub positions: Vec<u16>,
    pub states: Vec<TickState>,
    /// Changes whenever the ticks do: the rail's cache key (no per-frame
    /// hashing of thousands of planes).
    pub revision: u64,
}

/// What the rail shows.
pub(crate) struct RailInputs<'a> {
    pub samples: &'a [SurveySample],
    pub start: Option<u16>,
    pub end: Option<u16>,
    /// The plan's step, for the planned ticks (plan mode).
    pub step: u16,
    pub lens: Option<u16>,
    /// The capture's planes (flight mode); `None` draws the plan.
    pub flight: Option<&'a FlightTicks>,
    /// The survey's caption, when there is one ("survey 21:30").
    pub survey: Option<String>,
    /// The survey suggests bounds that can be applied.
    pub can_use_survey: bool,
    /// Jogs, marks and handles may be used.
    pub editable: bool,
    /// The rail's keys are live (the station has the keyboard).
    pub keys: bool,
}

/// What the user asked of the rail.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum RailIntent {
    /// Move focus by a supported increment (±1, ±16, ±128).
    Jog(i32),
    /// Move the lens to a position (a click on the rail).
    Focus(u16),
    MarkStart,
    MarkEnd,
    /// A handle was dragged to `to`: move there, then mark it.
    MoveBound {
        start: bool,
        to: u16,
    },
    UseSurveyBounds,
    SurveyAgain,
}

/// The rail's cached geometry and drag state.
#[derive(Default)]
pub(crate) struct FocusRail {
    cache: Option<(RailKey, Arc<Mesh>)>,
    /// How many times the mesh was built (tests and performance checks).
    pub rebuilds: u64,
    drag: Option<(bool, u16)>,
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct RailKey {
    samples: u64,
    domain: (u16, u16),
    start: Option<u16>,
    end: Option<u16>,
    step: u16,
    flight: u64,
    rect: [u32; 4],
    ppp: u32,
    progress_lens: Option<u16>,
}

/// The rail chart's padding and heights (the mockups' `drawRail`).
const PAD: f32 = 20.0;
const HEAD: f32 = 30.0;
/// The most planned planes the rail lays out ticks for; above it the plan
/// is summarised by its bounds.
const MAX_TICK_PLANES: usize = 65_536;

/// The median of a survey position's tile scores: the bar's height. Scores
/// of `null` (no texture) are left out.
pub(crate) fn profile_value(sample: &SurveySample) -> Option<f32> {
    let mut v: Vec<f32> = sample
        .scores
        .iter()
        .flatten()
        .copied()
        .filter(|s| s.is_finite())
        .collect();
    if v.is_empty() {
        return None;
    }
    v.sort_by(f32::total_cmp);
    let n = v.len();
    Some(if n % 2 == 1 {
        v[n / 2]
    } else {
        (v[n / 2 - 1] + v[n / 2]) / 2.0
    })
}

/// The focus range the rail spans: the survey, the bounds and the lens,
/// padded by a tenth (at least 32 units) each side.
pub(crate) fn domain(inputs: &RailInputs<'_>) -> (u16, u16) {
    let mut lo = u16::MAX;
    let mut hi = 0u16;
    let mut take = |p: u16| {
        lo = lo.min(p);
        hi = hi.max(p);
    };
    for s in inputs.samples {
        take(s.position);
    }
    for p in [inputs.start, inputs.end, inputs.lens]
        .into_iter()
        .flatten()
    {
        take(p);
    }
    if let Some(f) = inputs.flight
        && let (Some(a), Some(b)) = (f.positions.first(), f.positions.last())
    {
        take(*a);
        take(*b);
    }
    if lo > hi {
        return (0, u16::MAX);
    }
    let pad = ((hi - lo) / 10).max(32);
    (lo.saturating_sub(pad), hi.saturating_add(pad).max(lo + 1))
}

/// The planned positions between the bounds at `step`, as the host plans
/// them (`Plan::positions`).
pub(crate) fn planned(start: u16, end: u16, step: u16) -> Vec<u16> {
    let plan = strehl_capture::model::Plan {
        start,
        end,
        step: step.max(1),
        ..Default::default()
    };
    let distance = usize::from(start.abs_diff(end));
    if distance / usize::from(step.max(1)) > MAX_TICK_PLANES {
        return vec![start, end];
    }
    plan.positions().unwrap_or_else(|_| vec![start, end])
}

/// The tick columns to draw: positions pooled to one per `columns` bin,
/// keeping the most notable state in each.
pub(crate) fn pooled<T: Copy>(
    positions: &[u16],
    states: &[T],
    domain: (u16, u16),
    columns: usize,
    rank: impl Fn(T) -> u8,
) -> Vec<(u16, T)> {
    let columns = columns.max(1);
    let span = f64::from(domain.1.saturating_sub(domain.0).max(1));
    let mut out: Vec<(usize, u16, T)> = Vec::new();
    for (p, s) in positions.iter().zip(states) {
        let col = ((f64::from(p.saturating_sub(domain.0)) / span) * columns as f64) as usize;
        match out.last_mut() {
            Some((c, _, prev)) if *c == col => {
                if rank(*s) > rank(*prev) {
                    *prev = *s;
                }
            }
            _ => out.push((col, *p, *s)),
        }
    }
    out.into_iter().map(|(_, p, s)| (p, s)).collect()
}

fn tick_rank(s: TickState) -> u8 {
    match s {
        TickState::ToCome => 0,
        TickState::Checked => 1,
        TickState::OnHost => 2,
        TickState::Retaken => 3,
        TickState::Attention => 4,
    }
}

fn hash_samples(samples: &[SurveySample]) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut h = std::collections::hash_map::DefaultHasher::new();
    samples.len().hash(&mut h);
    for s in samples {
        s.position.hash(&mut h);
        for v in &s.scores {
            v.map(f32::to_bits).hash(&mut h);
        }
    }
    h.finish()
}

fn hash_flight(flight: Option<&FlightTicks>) -> u64 {
    flight.map_or(0, |f| {
        f.revision
            .wrapping_mul(0x9e37_79b9)
            .wrapping_add(f.positions.len() as u64)
    })
}

/// Maps focus positions to x within the chart.
#[derive(Clone, Copy)]
struct Axis {
    left: f32,
    width: f32,
    lo: f32,
    span: f32,
}

impl Axis {
    fn new(chart: Rect, domain: (u16, u16)) -> Self {
        Self {
            left: chart.left() + PAD,
            width: (chart.width() - 2.0 * PAD).max(1.0),
            lo: f32::from(domain.0),
            span: f32::from(domain.1.saturating_sub(domain.0).max(1)),
        }
    }
    fn x(&self, p: u16) -> f32 {
        self.left + (f32::from(p) - self.lo) / self.span * self.width
    }
    fn position(&self, x: f32) -> u16 {
        (self.lo + (x - self.left) / self.width * self.span)
            .round()
            .clamp(0.0, 65535.0) as u16
    }
}

/// A one-physical-pixel-or-wider rectangle in `mesh`.
fn rect(mesh: &mut Mesh, r: Rect, color: Color32) {
    if r.width() > 0.0 && r.height() > 0.0 {
        mesh.add_colored_rect(r, color);
    }
}

/// A nice spacing of focus-unit labels: about one per 110 px.
fn label_spacing(span: f32, width: f32) -> u16 {
    let want = span / (width / 110.0).max(1.0);
    let mut unit = 1.0f32;
    loop {
        for m in [1.0, 2.0, 5.0] {
            if unit * m >= want {
                return (unit * m).min(65535.0) as u16;
            }
        }
        unit *= 10.0;
    }
}

impl FocusRail {
    /// The rail's keys: Left/Right move focus by 1 (Shift by 16), S and E
    /// mark the start and end. Not while a text field has the keyboard.
    pub fn keys(&self, ui: &Ui, inputs: &RailInputs<'_>) -> Vec<RailIntent> {
        if !inputs.keys
            || !inputs.editable
            || inputs.flight.is_some()
            || ui.ctx().wants_keyboard_input()
        {
            return Vec::new();
        }
        ui.input(|i| {
            let mut out = Vec::new();
            for e in &i.events {
                if let Event::Key {
                    key,
                    pressed: true,
                    modifiers,
                    ..
                } = e
                {
                    if modifiers.ctrl || modifiers.alt || modifiers.command {
                        continue;
                    }
                    let by = if modifiers.shift { 16 } else { 1 };
                    match key {
                        Key::ArrowLeft => out.push(RailIntent::Jog(-by)),
                        Key::ArrowRight => out.push(RailIntent::Jog(by)),
                        Key::S if !modifiers.shift => out.push(RailIntent::MarkStart),
                        Key::E if !modifiers.shift => out.push(RailIntent::MarkEnd),
                        _ => {}
                    }
                }
            }
            out
        })
    }

    /// Draws the rail into the slot `ui` gives it (head row and chart) and
    /// returns what the user asked.
    pub fn show(
        &mut self,
        ui: &mut Ui,
        inputs: &RailInputs<'_>,
        palette: &CapturePalette,
    ) -> Vec<RailIntent> {
        let mut intents = self.keys(ui, inputs);
        let slot = ui.max_rect();
        ui.painter().rect_filled(slot, 0.0, palette.panel);
        style::hairline(
            ui.painter(),
            slot.left_top() + egui::vec2(0.0, 0.5),
            slot.right_top() + egui::vec2(0.0, 0.5),
            palette.line,
        );
        let head = Rect::from_min_size(slot.min, egui::vec2(slot.width(), HEAD));
        self.head(ui, head, inputs, palette, &mut intents);
        let chart = Rect::from_min_max(egui::pos2(slot.left(), head.bottom()), slot.max);
        self.chart(ui, chart, inputs, palette, &mut intents);
        intents
    }

    fn head(
        &mut self,
        ui: &mut Ui,
        head: Rect,
        inputs: &RailInputs<'_>,
        palette: &CapturePalette,
        intents: &mut Vec<RailIntent>,
    ) {
        ui.scope_builder(
            egui::UiBuilder::new()
                .max_rect(head.shrink2(egui::vec2(14.0, 0.0)))
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
            |ui| {
                ui.spacing_mut().item_spacing.x = 16.0;
                ui.label(style::caps_job("Depth rail", 10.5, palette.ink));
                if inputs.flight.is_some() {
                    style::text(ui, "each tick is a plane", 12.0, palette.ink3);
                    for (color, label) in [
                        (palette.ok, "checked"),
                        (palette.warn, "retaken"),
                        (palette.info, "on the camera host, not yet here"),
                        (palette.line2, "to come"),
                    ] {
                        ui.horizontal(|ui| {
                            ui.spacing_mut().item_spacing.x = 6.0;
                            let (r, _) =
                                ui.allocate_exact_size(egui::vec2(9.0, 9.0), Sense::hover());
                            ui.painter().rect_filled(r, 0.0, color);
                            style::text(ui, label, 12.0, palette.ink3);
                        });
                    }
                    return;
                }
                style::text(
                    ui,
                    "lens travel, in the camera's focus units",
                    12.0,
                    palette.ink3,
                );
                ui.horizontal(|ui| {
                    ui.spacing_mut().item_spacing.x = 2.0;
                    for delta in [-128, -16, -1] {
                        if jog(ui, delta, inputs.editable, palette) {
                            intents.push(RailIntent::Jog(delta));
                        }
                    }
                    ui.add_space(8.0);
                    style::text(
                        ui,
                        &inputs.lens.map_or("—".into(), style::focus_units),
                        13.0,
                        palette.ink,
                    );
                    ui.add_space(8.0);
                    for delta in [1, 16, 128] {
                        if jog(ui, delta, inputs.editable, palette) {
                            intents.push(RailIntent::Jog(delta));
                        }
                    }
                });
                if let Some(survey) = &inputs.survey {
                    ui.horizontal(|ui| {
                        ui.spacing_mut().item_spacing.x = 7.0;
                        let (r, _) = ui.allocate_exact_size(egui::vec2(14.0, 7.0), Sense::hover());
                        for i in 0..4 {
                            let x = r.left() + i as f32 * 4.0;
                            ui.painter().rect_filled(
                                Rect::from_min_size(egui::pos2(x, r.top()), egui::vec2(3.0, 7.0)),
                                0.0,
                                palette.ok.gamma_multiply(0.75),
                            );
                        }
                        style::text(ui, survey, 12.0, palette.ink3);
                    });
                }
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.spacing_mut().item_spacing.x = 16.0;
                    if style::link(ui, "Survey again", inputs.editable, palette).clicked() {
                        intents.push(RailIntent::SurveyAgain);
                    }
                    if style::link(
                        ui,
                        "Use the survey's bounds",
                        inputs.editable && inputs.can_use_survey,
                        palette,
                    )
                    .clicked()
                    {
                        intents.push(RailIntent::UseSurveyBounds);
                    }
                });
            },
        );
    }

    fn key(&self, chart: Rect, ppp: f32, inputs: &RailInputs<'_>, dom: (u16, u16)) -> RailKey {
        RailKey {
            samples: hash_samples(inputs.samples),
            domain: dom,
            start: inputs.start,
            end: inputs.end,
            step: inputs.step,
            flight: hash_flight(inputs.flight),
            rect: [
                chart.left().to_bits(),
                chart.top().to_bits(),
                chart.width().to_bits(),
                chart.height().to_bits(),
            ],
            ppp: ppp.to_bits(),
            progress_lens: inputs.flight.and(inputs.lens),
        }
    }

    /// Builds the bars, ticks, baseline and scale as one mesh.
    fn build(
        &self,
        chart: Rect,
        ppp: f32,
        inputs: &RailInputs<'_>,
        dom: (u16, u16),
        palette: &CapturePalette,
    ) -> Mesh {
        let px = 1.0 / ppp;
        let axis = Axis::new(chart, dom);
        let base = chart.bottom() - 19.0;
        let top_gap = 22.0;
        let hgt = (base - (chart.top() + top_gap)).max(1.0);
        let mut mesh = Mesh::default();
        // Grid at half and full height.
        for g in [0.5, 1.0] {
            let y = (base - hgt * g).round();
            rect(
                &mut mesh,
                Rect::from_min_max(
                    egui::pos2(axis.left, y),
                    egui::pos2(axis.left + axis.width, y + px),
                ),
                palette.line,
            );
        }
        // The survey's profile.
        let values: Vec<(u16, f32)> = inputs
            .samples
            .iter()
            .filter_map(|s| profile_value(s).map(|v| (s.position, v)))
            .collect();
        let peak = values.iter().map(|v| v.1).fold(0.0f32, f32::max);
        if peak > 0.0 {
            // One bar a column of the plan's step (at least 3 px), its height
            // the survey's profile interpolated there: the mockup's bar per
            // plane, which a 33-position survey alone leaves sparse.
            let mut sorted = values.clone();
            sorted.sort_by_key(|v| v.0);
            let profile_at = |p: f32| -> f32 {
                let i = sorted.partition_point(|v| f32::from(v.0) < p);
                match (i.checked_sub(1).map(|j| sorted[j]), sorted.get(i)) {
                    (Some(a), Some(b)) if b.0 > a.0 => {
                        let f = (p - f32::from(a.0)) / f32::from(b.0 - a.0);
                        a.1 + (b.1 - a.1) * f
                    }
                    (_, Some(b)) if f32::from(b.0) == p => b.1,
                    _ => 0.0,
                }
            };
            let step_px = f32::from(inputs.step.max(1)) / axis.span * axis.width;
            let column = step_px.max(3.0);
            let bw = (column - 1.0).max(1.0);
            let (a, b) = match (inputs.start, inputs.end) {
                (Some(s), Some(e)) => (s.min(e), s.max(e)),
                _ => (0, u16::MAX),
            };
            let n = (axis.width / column) as usize;
            let bars: Vec<(u16, f32)> = (0..=n)
                .map(|i| {
                    let x = axis.left + i as f32 * column;
                    let p = axis.lo + (x - axis.left) / axis.width * axis.span;
                    (p.round().clamp(0.0, 65535.0) as u16, profile_at(p))
                })
                .filter(|(_, v)| *v > 0.0)
                .collect();
            for (p, v) in &bars {
                let x = axis.x(*p);
                let h = v / peak * hgt;
                let inside = (a..=b).contains(p);
                let done = match (inputs.flight, inputs.lens) {
                    (Some(_), Some(lens)) => match (inputs.start, inputs.end) {
                        (Some(s), Some(e)) if e < s => *p >= lens,
                        _ => *p <= lens,
                    },
                    _ => true,
                };
                let color = if done {
                    palette.ok.gamma_multiply(if inside { 0.6 } else { 0.28 })
                } else {
                    palette.ink3.gamma_multiply(0.3)
                };
                rect(
                    &mut mesh,
                    Rect::from_min_max(
                        egui::pos2(x - bw / 2.0, base - h.max(px)),
                        egui::pos2(x + bw / 2.0, base),
                    ),
                    color,
                );
            }
        }
        // Planes: the plan's ticks, or the flight's states, pooled to 2 px.
        let columns = (axis.width / 2.0) as usize;
        let ticks: Vec<(u16, TickState)> = match inputs.flight {
            Some(f) => pooled(&f.positions, &f.states, dom, columns, tick_rank),
            None => match (inputs.start, inputs.end) {
                (Some(s), Some(e)) => {
                    let p = planned(s, e, inputs.step);
                    let states = vec![TickState::ToCome; p.len()];
                    pooled(&p, &states, dom, columns, tick_rank)
                }
                _ => Vec::new(),
            },
        };
        let tick_top = chart.top() + 16.0;
        for (p, s) in ticks {
            let (color, th) = match s {
                TickState::Checked => (palette.ok, 6.0),
                TickState::Retaken => (palette.warn, 10.0),
                TickState::Attention => (palette.bad, 10.0),
                TickState::OnHost => (palette.info, 6.0),
                TickState::ToCome => (
                    if inputs.flight.is_some() {
                        palette.line2
                    } else {
                        palette.ink3
                    },
                    6.0,
                ),
            };
            let x = axis.x(p);
            rect(
                &mut mesh,
                Rect::from_min_max(
                    egui::pos2(x - 0.75, tick_top - th),
                    egui::pos2(x + 0.75, tick_top),
                ),
                color,
            );
        }
        // Baseline and scale.
        rect(
            &mut mesh,
            Rect::from_min_max(
                egui::pos2(axis.left, base),
                egui::pos2(axis.left + axis.width, base + px),
            ),
            palette.line2,
        );
        let major = label_spacing(axis.span, axis.width);
        let minor = (major / 5).max(1);
        let first = dom.0.div_ceil(minor) * minor;
        let mut p = u32::from(first);
        while p <= u32::from(dom.1) {
            let is_major = p % u32::from(major) == 0;
            let x = axis.x(p as u16);
            rect(
                &mut mesh,
                Rect::from_min_max(
                    egui::pos2(x, base),
                    egui::pos2(x + px, base + if is_major { 6.0 } else { 3.0 }),
                ),
                if is_major {
                    palette.ink3
                } else {
                    palette.line2
                },
            );
            p += u32::from(minor);
        }
        mesh
    }

    fn chart(
        &mut self,
        ui: &mut Ui,
        chart: Rect,
        inputs: &RailInputs<'_>,
        palette: &CapturePalette,
        intents: &mut Vec<RailIntent>,
    ) {
        let ppp = ui.ctx().pixels_per_point();
        let dom = domain(inputs);
        let key = self.key(chart, ppp, inputs, dom);
        if self.cache.as_ref().is_none_or(|(k, _)| *k != key) {
            let mesh = self.build(chart, ppp, inputs, dom, palette);
            self.cache = Some((key, Arc::new(mesh)));
            self.rebuilds += 1;
        }
        let response = ui.interact(
            chart,
            ui.id().with("focus-rail-chart"),
            Sense::click_and_drag(),
        );
        let painter = ui.painter_at(chart);
        if let Some((_, mesh)) = &self.cache {
            painter.add(Shape::mesh(mesh.clone()));
        }
        let axis = Axis::new(chart, dom);
        let base = chart.bottom() - 19.0;
        let top_gap = chart.top() + 22.0;
        let label = |pos: Pos2, anchor: Align2, text: &str, color: Color32| {
            style::paint_job(&painter, pos, anchor, style::caps_job(text, 10.0, color));
        };
        // Scale labels (cheap text, a handful).
        let major = label_spacing(axis.span, axis.width);
        let first = dom.0.div_ceil(major) * major;
        let mut p = u32::from(first);
        while p <= u32::from(dom.1) {
            let x = axis.x(p as u16);
            if x > axis.left + 40.0 && x < axis.left + axis.width - 40.0 {
                label(
                    egui::pos2(x, chart.bottom() - 3.0),
                    Align2::CENTER_BOTTOM,
                    &style::focus_units(p as u16),
                    palette.ink3,
                );
            }
            p += u32::from(major);
        }
        label(
            egui::pos2(axis.left, chart.bottom() - 3.0),
            Align2::LEFT_BOTTOM,
            "Near",
            palette.ink3,
        );
        label(
            egui::pos2(axis.left + axis.width, chart.bottom() - 3.0),
            Align2::RIGHT_BOTTOM,
            "Far",
            palette.ink3,
        );
        // Dragging a handle edits a draft bound; release asks for it.
        let pointer = response.interact_pointer_pos().or(response.hover_pos());
        let near_handle = |x: f32| -> Option<bool> {
            let mut best = None;
            for (is_start, b) in [(true, inputs.start), (false, inputs.end)] {
                if let Some(b) = b {
                    let d = (axis.x(b) - x).abs();
                    if d <= 6.0 && best.is_none_or(|(_, bd)| d < bd) {
                        best = Some((is_start, d));
                    }
                }
            }
            best.map(|(s, _)| s)
        };
        if inputs.editable && inputs.flight.is_none() {
            if response.drag_started()
                && let Some(pos) = ui.input(|i| i.pointer.press_origin())
                && let Some(is_start) = near_handle(pos.x)
            {
                self.drag = Some((is_start, axis.position(pos.x)));
            }
            if let Some((is_start, _)) = self.drag
                && let Some(pos) = response.interact_pointer_pos()
            {
                self.drag = Some((is_start, axis.position(pos.x)));
            }
            if response.drag_stopped()
                && let Some((start, to)) = self.drag.take()
            {
                intents.push(RailIntent::MoveBound { start, to });
            }
            if response.clicked()
                && self.drag.is_none()
                && let Some(pos) = response.interact_pointer_pos()
                && near_handle(pos.x).is_none()
            {
                intents.push(RailIntent::Focus(axis.position(pos.x)));
            }
            if pointer.is_some_and(|p| near_handle(p.x).is_some()) || self.drag.is_some() {
                ui.ctx().set_cursor_icon(egui::CursorIcon::ResizeHorizontal);
            }
        } else {
            self.drag = None;
        }
        // Handles.
        for (is_start, bound, name) in [(true, inputs.start, "Start"), (false, inputs.end, "End")] {
            let shown = match self.drag {
                Some((s, to)) if s == is_start => Some(to),
                _ => bound,
            };
            let Some(b) = shown else { continue };
            let x = axis.x(b);
            let dir = if is_start { -1.0 } else { 1.0 };
            painter.line_segment(
                [egui::pos2(x, chart.top() + 2.0), egui::pos2(x, base)],
                Stroke::new(1.5_f32, palette.accent),
            );
            painter.add(Shape::convex_polygon(
                vec![
                    egui::pos2(x, chart.top() + 2.0),
                    egui::pos2(x - 6.0 * dir, chart.top() + 2.0),
                    egui::pos2(x, chart.top() + 9.0),
                ],
                palette.accent,
                Stroke::NONE,
            ));
            label(
                egui::pos2(x + 9.0 * dir, chart.top() + 11.0),
                if is_start {
                    Align2::RIGHT_BOTTOM
                } else {
                    Align2::LEFT_BOTTOM
                },
                &format!("{name} {}", style::focus_units(b)),
                palette.accent,
            );
        }
        // The lens.
        if let Some(lens) = inputs.lens {
            let x = axis.x(lens);
            painter.line_segment(
                [egui::pos2(x, top_gap), egui::pos2(x, base)],
                Stroke::new(1.0_f32, palette.ink),
            );
            painter.add(Shape::convex_polygon(
                vec![
                    egui::pos2(x - 5.0, base + 7.0),
                    egui::pos2(x + 5.0, base + 7.0),
                    egui::pos2(x, base),
                ],
                palette.ink,
                Stroke::NONE,
            ));
            label(
                egui::pos2(x + 7.0, top_gap + 9.0),
                Align2::LEFT_BOTTOM,
                &format!("Lens {}", style::focus_units(lens)),
                palette.ink,
            );
        }
        // Hover: the position under the pointer.
        if self.drag.is_none()
            && let Some(pos) = response.hover_pos()
        {
            let at = axis.position(pos.x);
            painter.line_segment(
                [
                    egui::pos2(pos.x, chart.top() + 2.0),
                    egui::pos2(pos.x, base + 6.0),
                ],
                Stroke::new(1.0_f32, palette.plane),
            );
            let text = style::focus_units(at);
            let r = Rect::from_center_size(
                egui::pos2(
                    pos.x.clamp(chart.left() + 22.0, chart.right() - 22.0),
                    chart.bottom() - 6.5,
                ),
                egui::vec2(44.0, 13.0),
            );
            painter.rect_filled(r, 0.0, palette.plane);
            style::paint_job(
                &painter,
                r.center(),
                Align2::CENTER_CENTER,
                style::job(&text, 10.0, Color32::from_rgb(4, 32, 28), 0.0),
            );
        }
    }
}

fn jog(ui: &mut Ui, delta: i32, enabled: bool, palette: &CapturePalette) -> bool {
    let label = if delta < 0 {
        format!("−{}", -delta)
    } else {
        format!("+{delta}")
    };
    style::button(ui, &label, ButtonKind::Plain, 20.0, enabled, palette).clicked()
}

#[cfg(test)]
#[path = "capture-rail-tests.rs"]
mod tests;
