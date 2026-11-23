//! The focus rail (Studio 2, 7.4): the lens travel in the camera's focus
//! units, the bounds survey's sharpness profile as bars, every planned plane
//! as a tick, the Start and End handles and the lens.
//!
//! The rail has a scale. The wheel over it zooms around the pointer; Shift
//! and the wheel, or a drag on the empty rail, pans; the head's scale slider
//! sets it, and Fit (or a double click on the slider) returns to the bounds
//! and the survey. The view eases to where it is asked to be (about 150 ms;
//! at once with reduced motion) and stays inside the lens's travel. A click
//! or a drag lands on the resolution the scale shows ([`quantum`]): coarse
//! zoomed out, single units zoomed in. A lens moved out of a zoomed view
//! brings the view along.
//!
//! Spec 5.4: the bars and ticks are one cached `Arc<Mesh>`, rebuilt only when
//! the survey, the plan, the flight's plane states, the rectangle, the
//! display scale or the view change (its buffers reused); ticks are pooled to
//! at most one per 2 px column, anchored to focus units so panning does not
//! make them swim. The hover line, the handles' labels and the lens are
//! separate cheap shapes, so pointer motion rebuilds nothing.
use std::sync::Arc;

use eframe::egui::{
    self, Align2, Color32, Event, Key, Mesh, MouseWheelUnit, Pos2, Rect, Response, Sense, Shape,
    Stroke, Ui,
};

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
    /// Move the lens to a position (a click on the rail, or the lens
    /// dragged and let go).
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

/// The lens's travel in focus units: the host accepts 0 to 65,535.
pub(crate) const TRAVEL: f64 = 65_535.0;
/// The finest scale: this many focus units across the rail.
pub(crate) const MIN_SPAN: f64 = 32.0;
/// One wheel notch scales the visible span by this (two notches double it).
pub(crate) const NOTCH: f64 = std::f64::consts::SQRT_2;
/// Shift and one wheel notch pan this share of the visible span.
pub(crate) const PAN_NOTCH: f64 = 0.12;
/// How long a change of view eases (an ease-out cubic), in seconds.
pub(crate) const EASE_SECONDS: f64 = 0.14;

/// The rail's visible focus range: `lo` at the chart's left end, `span`
/// focus units across it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct RailView {
    pub lo: f64,
    pub span: f64,
}

impl RailView {
    /// The view of a domain, kept inside the travel and the finest scale.
    pub fn of(domain: (u16, u16)) -> Self {
        let lo = f64::from(domain.0.min(domain.1));
        let span = f64::from(domain.0.abs_diff(domain.1).max(1));
        Self { lo, span }.clamped()
    }
    pub fn hi(self) -> f64 {
        self.lo + self.span
    }
    /// The span within [`MIN_SPAN`] and the travel, and the view inside the
    /// travel (a too-fine view widens about its centre).
    pub fn clamped(self) -> Self {
        let span = if self.span.is_finite() {
            self.span.clamp(MIN_SPAN, TRAVEL)
        } else {
            TRAVEL
        };
        let lo = if !self.lo.is_finite() {
            0.0
        } else if self.span.is_finite() && self.span < MIN_SPAN {
            self.lo + self.span / 2.0 - span / 2.0
        } else {
            self.lo
        };
        Self {
            lo: lo.clamp(0.0, TRAVEL - span),
            span,
        }
    }
    /// A view `span` across with focus position `at` at chart fraction
    /// `anchor` (0 the left end, 1 the right), within the travel.
    pub fn around(at: f64, anchor: f64, span: f64) -> Self {
        let span = span.clamp(MIN_SPAN, TRAVEL);
        Self {
            lo: at - anchor * span,
            span,
        }
        .clamped()
    }
    /// The focus position at chart fraction `anchor`.
    pub fn at(self, anchor: f64) -> f64 {
        self.lo + anchor * self.span
    }
    /// The chart fraction of focus position `p`.
    pub fn fraction(self, p: f64) -> f64 {
        (p - self.lo) / self.span
    }
    /// Panned by `units` (positive towards Far), within the travel.
    pub fn panned(self, units: f64) -> Self {
        Self {
            lo: self.lo + units,
            ..self
        }
        .clamped()
    }
    pub fn contains(self, p: f64) -> bool {
        p >= self.lo && p <= self.hi()
    }
}

/// The view after `notches` of the wheel (positive: away from the user,
/// finer) at chart fraction `anchor` of `shown`, starting from the view
/// asked for (`target`): the position under the pointer stays under it.
pub(crate) fn wheel_zoom(shown: RailView, target: RailView, notches: f64, anchor: f64) -> RailView {
    RailView::around(shown.at(anchor), anchor, target.span * NOTCH.powf(-notches))
}

/// The view `k` of the way (0-1) from `from` to `goal`: the span on a log
/// scale, the position at chart fraction `anchor` linearly, so a zoom about
/// the pointer keeps the pointer's position still all the way.
pub(crate) fn between(from: RailView, goal: RailView, anchor: f64, k: f64) -> RailView {
    if k >= 1.0 {
        return goal;
    }
    let k = k.max(0.0);
    let (lf, lg) = (from.span.ln(), goal.span.ln());
    let (a_f, a_g) = (from.at(anchor), goal.at(anchor));
    let span = (lf + (lg - lf) * k).exp();
    RailView {
        lo: a_f + (a_g - a_f) * k - anchor * span,
        span,
    }
}

/// The ease-out cubic at `t` (0-1) of [`EASE_SECONDS`].
pub(crate) fn ease_out(t: f64) -> f64 {
    let t = t.clamp(0.0, 1.0);
    1.0 - (1.0 - t).powi(3)
}

/// The resolution a click or a drag lands on at `units_per_px`: the
/// smallest of 1, 2, 5, 10, 20, 50 ... focus units not finer than a pixel.
pub(crate) fn quantum(units_per_px: f64) -> u16 {
    nice_at_least(units_per_px).min(10_000) as u16
}

/// The smallest of 1, 2, 5, 10, 20, 50 ... at least `want` (and at least 1).
fn nice_at_least(want: f64) -> u32 {
    let mut unit = 1u32;
    loop {
        for m in [1, 2, 5] {
            if f64::from(unit * m) >= want {
                return unit * m;
            }
        }
        if unit >= 100_000 {
            return unit * 10;
        }
        unit *= 10;
    }
}

/// `p` rounded to a multiple of `q`, within the travel.
pub(crate) fn snap(p: f64, q: u16) -> u16 {
    let q = f64::from(q.max(1));
    ((p / q).round() * q).clamp(0.0, TRAVEL) as u16
}

/// What a press on the chart took hold of.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Grip {
    Start,
    End,
    Lens,
}

/// The rail's scale: the view asked for, the view drawn and a pan.
#[derive(Default)]
struct Zoom {
    /// The user's view; `None` follows the fit (bounds, survey and lens).
    target: Option<RailView>,
    /// What the last frame drew, easing towards the target.
    shown: Option<RailView>,
    /// The chart fraction held still while easing (the pointer's, for the
    /// wheel; the lens's, for the slider).
    anchor: f64,
    /// The lens seen last frame: a lens that moved out of a zoomed view
    /// brings the view along.
    lens: Option<u16>,
    /// A pan by dragging the empty rail: the view and the pointer's x when
    /// it began.
    pan: Option<(RailView, f32)>,
    /// The ease under way: the view it began from, when (the input's
    /// time), and the view it runs to.
    tween: Option<(RailView, f64, RailView)>,
    /// The rail showed a capture in flight last frame: entering or leaving
    /// flight fits the view again, so a capture opens fitted to its stack.
    flight: bool,
}

/// The rail's cached geometry and drag state.
#[derive(Default)]
pub(crate) struct FocusRail {
    cache: Option<(RailKey, Arc<Mesh>)>,
    /// How many times the mesh was built (tests and performance checks).
    pub rebuilds: u64,
    drag: Option<(Grip, u16)>,
    zoom: Zoom,
    /// The survey's profile by position, and the samples' hash it is of.
    profile: Option<(u64, Vec<(u16, f32)>)>,
    /// The planned positions and the (start, end, step) they are of.
    planned: Option<((u16, u16, u16), Vec<u16>)>,
    /// The head's right-hand controls' width last frame, so the survey's
    /// legend can shorten before it reaches them.
    head_right: f32,
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct RailKey {
    samples: u64,
    view: [u64; 2],
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
/// How near (points) a press must be to a handle or the lens to take it.
const GRIP: f32 = 6.0;

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

/// The survey's profile interpolated at `p`; 0 outside the survey.
fn profile_at(sorted: &[(u16, f32)], p: f64) -> f32 {
    let i = sorted.partition_point(|v| f64::from(v.0) < p);
    match (i.checked_sub(1).map(|j| sorted[j]), sorted.get(i)) {
        (_, Some(b)) if f64::from(b.0) == p => b.1,
        (Some(a), Some(b)) if b.0 > a.0 => {
            let f = ((p - f64::from(a.0)) / f64::from(b.0 - a.0)) as f32;
            a.1 + (b.1 - a.1) * f
        }
        _ => 0.0,
    }
}

/// The profile's highest point over `a..=b`: a bar keeps the peaks of the
/// focus range it stands for, however coarse the scale.
pub(crate) fn profile_max(sorted: &[(u16, f32)], a: f64, b: f64) -> f32 {
    let mut m = profile_at(sorted, a).max(profile_at(sorted, b));
    let i = sorted.partition_point(|v| f64::from(v.0) < a);
    let j = sorted.partition_point(|v| f64::from(v.0) <= b);
    for v in sorted.get(i..j).unwrap_or(&[]) {
        m = m.max(v.1);
    }
    m
}

/// The focus range the rail fits, padded by a tenth (at least 32 units)
/// each side: while planning, the survey, the bounds and the lens; in
/// flight, the stack being captured (its planned planes and bounds) alone,
/// so the fit does not move as the lens goes back for a retake.
pub(crate) fn domain(inputs: &RailInputs<'_>) -> (u16, u16) {
    let mut lo = u16::MAX;
    let mut hi = 0u16;
    let mut take = |p: u16| {
        lo = lo.min(p);
        hi = hi.max(p);
    };
    let flight = inputs.flight.filter(|f| !f.positions.is_empty());
    if flight.is_none() {
        for s in inputs.samples {
            take(s.position);
        }
        if let Some(p) = inputs.lens {
            take(p);
        }
    }
    for p in [inputs.start, inputs.end].into_iter().flatten() {
        take(p);
    }
    if let Some(f) = flight
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

/// The tick columns to draw: the positions inside `view`, pooled to one per
/// `units_per_column` (columns counted from focus position 0, so they stay
/// put as the view pans), keeping the most notable state in each.
pub(crate) fn pooled<T: Copy>(
    items: impl IntoIterator<Item = (u16, T)>,
    view: RailView,
    units_per_column: f64,
    rank: impl Fn(T) -> u8,
) -> Vec<(u16, T)> {
    let per = units_per_column.max(1e-6);
    let mut out: Vec<(i64, u16, T)> = Vec::new();
    for (p, s) in items {
        let at = f64::from(p);
        if !view.contains(at) {
            continue;
        }
        let col = (at / per).floor() as i64;
        match out.last_mut() {
            Some((c, _, prev)) if *c == col => {
                if rank(s) > rank(*prev) {
                    *prev = s;
                }
            }
            _ => out.push((col, p, s)),
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
    view: RailView,
}

impl Axis {
    fn new(chart: Rect, view: RailView) -> Self {
        Self {
            left: chart.left() + PAD,
            width: axis_width(chart),
            view,
        }
    }
    fn right(&self) -> f32 {
        self.left + self.width
    }
    fn xf(&self, p: f64) -> f32 {
        self.left + (self.view.fraction(p) * f64::from(self.width)) as f32
    }
    fn x(&self, p: u16) -> f32 {
        self.xf(f64::from(p))
    }
    fn units_per_px(&self) -> f64 {
        self.view.span / f64::from(self.width)
    }
    fn fraction(&self, x: f32) -> f64 {
        f64::from((x - self.left) / self.width)
    }
    /// The position under `x` on the resolution the scale shows.
    fn snap(&self, x: f32) -> u16 {
        snap(self.view.at(self.fraction(x)), quantum(self.units_per_px()))
    }
}

fn axis_width(chart: Rect) -> f32 {
    (chart.width() - 2.0 * PAD).max(1.0)
}

/// A rectangle in `mesh`.
fn rect(mesh: &mut Mesh, r: Rect, color: Color32) {
    if r.width() > 0.0 && r.height() > 0.0 {
        mesh.add_colored_rect(r, color);
    }
}

/// `x` on the nearest physical pixel.
fn on_pixel(x: f32, ppp: f32) -> f32 {
    (x * ppp).round() / ppp
}

/// A nice spacing of focus-unit labels: about one per 110 px.
fn label_spacing(span: f64, width: f32) -> u32 {
    nice_at_least(span / f64::from((width / 110.0).max(1.0)))
}

/// The minor tick spacing under `major`: the finest of 1, 2, 5, 10 ...
/// units that divides it and leaves at least 9 px between ticks (single
/// units when zoomed in far enough).
fn minor_spacing(major: u32, units_per_px: f64) -> u32 {
    let mut q = nice_at_least(9.0 * units_per_px);
    while q < major && !major.is_multiple_of(q) {
        q = nice_at_least(f64::from(q) + 0.5);
    }
    q.min(major).max(1)
}

/// "0.51/px": the focus units a pixel of the rail stands for.
fn per_pixel(units_per_px: f64) -> String {
    if units_per_px < 1.0 {
        format!("{units_per_px:.2}/px")
    } else if units_per_px < 10.0 {
        format!("{units_per_px:.1}/px")
    } else {
        format!("{units_per_px:.0}/px")
    }
}

impl FocusRail {
    /// The view drawn last frame (`None` before the first).
    #[allow(dead_code)]
    pub fn view(&self) -> Option<RailView> {
        self.zoom.shown
    }

    /// Shows `view` from the next frame (`None`: fit the bounds and the
    /// survey), without easing.
    pub fn set_view(&mut self, view: Option<RailView>) {
        self.zoom.target = view.map(RailView::clamped);
        self.zoom.shown = None;
        self.zoom.tween = None;
    }

    /// Back to the bounds and the survey (eased).
    pub fn fit(&mut self) {
        self.zoom.target = None;
        self.zoom.pan = None;
        self.zoom.anchor = 0.5;
    }

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
        let chart = Rect::from_min_max(egui::pos2(slot.left(), head.bottom()), slot.max);
        let fit = RailView::of(domain(inputs));
        // A capture starts (and ends) fitted to its stack: a view the user
        // zoomed while planning is let go. A wheel or a pan in flight holds
        // the user's view until Fit.
        let flight = inputs.flight.is_some();
        if flight != self.zoom.flight {
            self.zoom.flight = flight;
            self.fit();
        }
        self.wheel(ui, slot, chart, fit, inputs.lens);
        self.follow_lens(inputs.lens);
        self.ease(ui, fit);
        self.head(ui, head, chart, inputs, palette, fit, &mut intents);
        self.chart(ui, chart, inputs, palette, fit, &mut intents);
        intents
    }

    /// The wheel over the rail: it zooms around the pointer (over the head
    /// row, around the lens while it is in view); Shift and the wheel, or a
    /// sideways wheel, pans. The scroll is consumed, so nothing under the
    /// rail scrolls with it.
    fn wheel(&mut self, ui: &Ui, slot: Rect, chart: Rect, fit: RailView, lens: Option<u16>) {
        if !ui.rect_contains_pointer(slot) {
            return;
        }
        let (zoom, pan, pointer) = ui.input(|i| {
            let (mut zoom, mut pan) = (0.0f64, 0.0f64);
            for e in &i.events {
                if let Event::MouseWheel {
                    unit,
                    delta,
                    modifiers,
                } = e
                {
                    // Notches: a line is one; 50 points (a touchpad) are one.
                    let scale = match unit {
                        MouseWheelUnit::Line => 1.0,
                        MouseWheelUnit::Point => 1.0 / 50.0,
                        MouseWheelUnit::Page => 4.0,
                    };
                    let (x, y) = (f64::from(delta.x) * scale, f64::from(delta.y) * scale);
                    if modifiers.shift {
                        pan += x + y;
                    } else {
                        zoom += y;
                        pan += x;
                    }
                }
            }
            (zoom, pan, i.pointer.hover_pos())
        });
        if zoom == 0.0 && pan == 0.0 {
            return;
        }
        let axis = Axis::new(chart, self.zoom.shown.unwrap_or(fit));
        let shown = axis.view;
        let mut target = self.zoom.target.unwrap_or(shown);
        if zoom != 0.0 {
            let anchor = match pointer {
                Some(p) if p.y >= chart.top() => axis.fraction(p.x).clamp(0.0, 1.0),
                _ => lens
                    .map(|l| shown.fraction(f64::from(l)))
                    .filter(|f| (0.0..=1.0).contains(f))
                    .unwrap_or(0.5),
            };
            target = wheel_zoom(shown, target, zoom, anchor);
            self.zoom.anchor = anchor;
        }
        if pan != 0.0 {
            // The wheel turned away from you pans towards Near.
            target = target.panned(-pan * PAN_NOTCH * target.span);
        }
        self.zoom.target = Some(target);
        ui.ctx().input_mut(|i| {
            i.raw_scroll_delta = egui::Vec2::ZERO;
            i.smooth_scroll_delta = egui::Vec2::ZERO;
        });
    }

    /// A lens that moved out of a zoomed view brings the view along: to the
    /// margin it left by after a short move, centred after a long one.
    fn follow_lens(&mut self, lens: Option<u16>) {
        if lens == self.zoom.lens {
            return;
        }
        let before = std::mem::replace(&mut self.zoom.lens, lens);
        let (Some(_), Some(lens), Some(v)) = (before, lens, self.zoom.target) else {
            return;
        };
        if self.zoom.pan.is_some() {
            return;
        }
        let p = f64::from(lens);
        let margin = 0.08 * v.span;
        let target = if p < v.lo - v.span || p > v.hi() + v.span {
            RailView::around(p, 0.5, v.span)
        } else if p < v.lo + margin {
            RailView::around(p, 0.08, v.span)
        } else if p > v.hi() - margin {
            RailView::around(p, 0.92, v.span)
        } else {
            return;
        };
        self.zoom.target = Some(target);
    }

    /// Eases the drawn view to the one asked for over [`EASE_SECONDS`]; a
    /// new goal mid-way starts again from where the view is.
    fn ease(&mut self, ui: &Ui, fit: RailView) {
        let goal = self.zoom.target.unwrap_or(fit);
        let shown = match self.zoom.shown {
            Some(shown) if !crate::studio_theme::reduced_motion(ui.ctx()) => shown,
            _ => goal,
        };
        if shown == goal {
            self.zoom.shown = Some(goal);
            self.zoom.tween = None;
            return;
        }
        let (now, dt) = ui.input(|i| (i.time, f64::from(i.stable_dt.clamp(0.0, 0.1))));
        let (from, since) = match self.zoom.tween {
            Some((from, since, to)) if to == goal => (from, since),
            _ => {
                // Started a frame ago, so this frame already moves.
                self.zoom.tween = Some((shown, now - dt, goal));
                (shown, now - dt)
            }
        };
        let t = (now - since) / EASE_SECONDS;
        if t >= 1.0 {
            self.zoom.shown = Some(goal);
            self.zoom.tween = None;
        } else {
            self.zoom.shown = Some(between(from, goal, self.zoom.anchor, ease_out(t)));
            ui.ctx().request_repaint();
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn head(
        &mut self,
        ui: &mut Ui,
        head: Rect,
        chart: Rect,
        inputs: &RailInputs<'_>,
        palette: &CapturePalette,
        fit: RailView,
        intents: &mut Vec<RailIntent>,
    ) {
        ui.scope_builder(
            egui::UiBuilder::new()
                .max_rect(head.shrink2(egui::vec2(14.0, 0.0)))
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
            |ui| {
                ui.spacing_mut().item_spacing.x = 16.0;
                ui.label(style::caps_job("Depth rail", 10.5, palette.ink))
                    .on_hover_text("Lens travel, in the camera's focus units");
                if inputs.flight.is_some() {
                    // A narrow rail (a 1280 px window) keeps the legend
                    // short, clear of the scale at the right.
                    let roomy = head.width() >= 1200.0;
                    if roomy {
                        style::text(ui, "each tick is a plane", 12.0, palette.ink3);
                    }
                    for (color, label) in [
                        (palette.ok, "checked"),
                        (palette.warn, "retaken"),
                        (
                            palette.info,
                            if roomy {
                                "on the camera host, not yet here"
                            } else {
                                "on the host"
                            },
                        ),
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
                } else {
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
                        // The legend shortens to what fits before the scale
                        // at the right (its width measured last frame): the
                        // words, then "survey", then the swatch alone.
                        let right = if self.head_right > 0.0 {
                            self.head_right
                        } else {
                            640.0
                        };
                        let room = head.right() - 14.0 - right - 24.0 - ui.cursor().left() - 21.0;
                        let width = |text: &str| {
                            ui.painter()
                                .layout_job(style::job(text, 12.0, palette.ink3, 0.0))
                                .size()
                                .x
                        };
                        let label = [survey.as_str(), "survey"]
                            .into_iter()
                            .find(|text| width(text) <= room)
                            .unwrap_or("");
                        ui.horizontal(|ui| {
                            ui.spacing_mut().item_spacing.x = 7.0;
                            let (r, _) =
                                ui.allocate_exact_size(egui::vec2(14.0, 7.0), Sense::hover());
                            for i in 0..4 {
                                let x = r.left() + i as f32 * 4.0;
                                ui.painter().rect_filled(
                                    Rect::from_min_size(
                                        egui::pos2(x, r.top()),
                                        egui::vec2(3.0, 7.0),
                                    ),
                                    0.0,
                                    palette.ok.gamma_multiply(0.75),
                                );
                            }
                            if !label.is_empty() {
                                style::text(ui, label, 12.0, palette.ink3);
                            }
                        })
                        .response
                        .on_hover_text(survey.as_str());
                    }
                }
                let right =
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.spacing_mut().item_spacing.x = 16.0;
                        if inputs.flight.is_none() {
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
                            ui.add_space(10.0);
                        }
                        // A narrow head (a 1280 px window) folds the span readout into
                        // the slider's hover, clear of the jog buttons.
                        let compact = head.width() < 1040.0;
                        self.scale_controls(ui, chart, inputs.lens, palette, fit, compact);
                        ui.min_rect().width()
                    });
                self.head_right = right.inner;
            },
        );
    }

    /// The head's scale, laid out right to left: Fit, the visible span and
    /// the units a pixel stands for, the slider, its caption.
    fn scale_controls(
        &mut self,
        ui: &mut Ui,
        chart: Rect,
        lens: Option<u16>,
        palette: &CapturePalette,
        fit: RailView,
        compact: bool,
    ) {
        ui.spacing_mut().item_spacing.x = 9.0;
        let width = f64::from(axis_width(chart));
        let shown = self.zoom.shown.unwrap_or(fit);
        if style::link(ui, "Fit", self.zoom.target.is_some(), palette)
            .on_hover_text("Back to the bounds and the survey")
            .clicked()
        {
            self.fit();
        }
        let readout = format!(
            "{} units · {}",
            style::focus_units(shown.span.round().clamp(0.0, TRAVEL) as u16),
            per_pixel(shown.span / width)
        );
        if !compact {
            let (r, _) = ui.allocate_exact_size(egui::vec2(124.0, 16.0), Sense::hover());
            style::paint_job(
                ui.painter(),
                r.left_center(),
                Align2::LEFT_CENTER,
                style::job(&readout, 12.0, palette.ink2, 0.0),
            );
        }
        let (response, span) = scale_slider(ui, shown.span, fit.span, palette);
        let help = "The rail's scale. The wheel over the rail zooms around the pointer; Shift and \
             the wheel, or a drag on the empty rail, pans; double-click or Fit returns to \
             the bounds";
        let response = if compact {
            response.on_hover_text(format!("{readout}. {help}"))
        } else {
            response.on_hover_text(help)
        };
        if response.double_clicked() {
            self.fit();
        } else if let Some(span) = span {
            // About the lens while it is in view, else about the centre.
            let anchor = lens
                .map(|l| shown.fraction(f64::from(l)))
                .filter(|f| (0.0..=1.0).contains(f))
                .unwrap_or(0.5);
            self.zoom.target = Some(RailView::around(shown.at(anchor), anchor, span));
            self.zoom.anchor = anchor;
        }
        ui.label(style::caps_job("Scale", 10.5, palette.ink3));
    }

    fn key(
        &self,
        chart: Rect,
        ppp: f32,
        inputs: &RailInputs<'_>,
        samples: u64,
        view: RailView,
    ) -> RailKey {
        RailKey {
            samples,
            view: [view.lo.to_bits(), view.span.to_bits()],
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

    /// The bars, ticks, baseline and scale into `mesh` (cleared first, its
    /// buffers reused).
    fn build(
        &self,
        mesh: &mut Mesh,
        chart: Rect,
        ppp: f32,
        inputs: &RailInputs<'_>,
        view: RailView,
        palette: &CapturePalette,
    ) {
        mesh.clear();
        let px = 1.0 / ppp;
        let axis = Axis::new(chart, view);
        let upx = axis.units_per_px();
        let base = chart.bottom() - 19.0;
        let top_gap = 22.0;
        let hgt = (base - (chart.top() + top_gap)).max(1.0);
        // Grid at half and full height.
        for g in [0.5, 1.0] {
            let y = (base - hgt * g).round();
            rect(
                mesh,
                Rect::from_min_max(egui::pos2(axis.left, y), egui::pos2(axis.right(), y + px)),
                palette.line,
            );
        }
        // The survey's profile: one bar a plane (whole plan steps, at least
        // 3 px), on the plan's grid so the bars stay put as the view pans;
        // its height the profile's highest point over the bar's focus range.
        let profile = self.profile.as_ref().map_or(&[][..], |(_, p)| p.as_slice());
        let peak = profile.iter().map(|v| v.1).fold(0.0f32, f32::max);
        if peak > 0.0 {
            let step = f64::from(inputs.step.max(1));
            let per = (3.0 * upx / step).ceil().max(1.0) * step;
            let origin = f64::from(inputs.start.unwrap_or(0));
            let column = (per / upx) as f32;
            let gap = (column * 0.12).clamp(1.0, 4.0);
            let half = ((column - gap) / 2.0).max(0.5);
            let (a, b) = match (inputs.start, inputs.end) {
                (Some(s), Some(e)) => (f64::from(s.min(e)), f64::from(s.max(e))),
                _ => (0.0, TRAVEL),
            };
            let first = ((view.lo - origin) / per).floor() as i64 - 1;
            let last = ((view.hi() - origin) / per).ceil() as i64 + 1;
            for k in first..=last {
                let c = origin + k as f64 * per;
                let x = axis.xf(c);
                if x + half < axis.left || x - half > axis.right() {
                    continue;
                }
                let v = profile_max(profile, c - per / 2.0, c + per / 2.0);
                if v <= 0.0 {
                    continue;
                }
                let h = v / peak * hgt;
                let inside = (a..=b).contains(&c);
                let done = match (inputs.flight, inputs.lens) {
                    (Some(_), Some(lens)) => match (inputs.start, inputs.end) {
                        (Some(s), Some(e)) if e < s => c >= f64::from(lens),
                        _ => c <= f64::from(lens),
                    },
                    _ => true,
                };
                let color = if done {
                    palette.ok.gamma_multiply(if inside { 0.6 } else { 0.28 })
                } else {
                    palette.ink3.gamma_multiply(0.3)
                };
                let left = on_pixel(x - half, ppp);
                let right = on_pixel(x + half, ppp).max(left + px);
                rect(
                    mesh,
                    Rect::from_min_max(egui::pos2(left, base - h.max(px)), egui::pos2(right, base)),
                    color,
                );
            }
        }
        // Planes: the plan's ticks, or the flight's states, pooled to 2 px.
        let per_column = 2.0 * upx;
        let ticks: Vec<(u16, TickState)> = match inputs.flight {
            Some(f) => pooled(
                f.positions.iter().copied().zip(f.states.iter().copied()),
                view,
                per_column,
                tick_rank,
            ),
            None => match &self.planned {
                Some((_, positions)) => pooled(
                    positions.iter().map(|p| (*p, TickState::ToCome)),
                    view,
                    per_column,
                    tick_rank,
                ),
                None => Vec::new(),
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
                mesh,
                Rect::from_min_max(
                    egui::pos2(x - 0.75, tick_top - th),
                    egui::pos2(x + 0.75, tick_top),
                ),
                color,
            );
        }
        // Baseline and scale: nice steps re-picked at every scale.
        rect(
            mesh,
            Rect::from_min_max(
                egui::pos2(axis.left, base),
                egui::pos2(axis.right(), base + px),
            ),
            palette.line2,
        );
        let major = label_spacing(view.span, axis.width);
        let minor = f64::from(minor_spacing(major, upx));
        let mut p = (view.lo / minor).ceil() * minor;
        while p <= view.hi() {
            let is_major = (p as u64).is_multiple_of(u64::from(major));
            let x = on_pixel(axis.xf(p), ppp);
            rect(
                mesh,
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
            p += minor;
        }
    }

    fn chart(
        &mut self,
        ui: &mut Ui,
        chart: Rect,
        inputs: &RailInputs<'_>,
        palette: &CapturePalette,
        fit: RailView,
        intents: &mut Vec<RailIntent>,
    ) {
        let ppp = ui.ctx().pixels_per_point();
        let response = ui.interact(
            chart,
            ui.id().with("focus-rail-chart"),
            Sense::click_and_drag(),
        );
        let mut view = self.zoom.shown.unwrap_or(fit);
        let base = chart.bottom() - 19.0;
        let editable = inputs.editable && inputs.flight.is_none();
        // What a press at `pos` takes: the nearest handle or the lens within
        // reach; the lens wins a tie in the lower half, where its mark is.
        let grip_at = |axis: &Axis, pos: Pos2| -> Option<Grip> {
            if !editable {
                return None;
            }
            let lower = pos.y > chart.center().y;
            [
                (Grip::Start, inputs.start),
                (Grip::End, inputs.end),
                (Grip::Lens, inputs.lens),
            ]
            .into_iter()
            .filter_map(|(g, p)| {
                let d = (axis.x(p?) - pos.x).abs();
                let bias = match (g, lower) {
                    (Grip::Lens, true) => -0.5,
                    (Grip::Lens, false) => 0.5,
                    _ => 0.0,
                };
                (d <= GRIP).then_some((g, d + bias))
            })
            .min_by(|a, b| a.1.total_cmp(&b.1))
            .map(|(g, _)| g)
        };
        let axis = Axis::new(chart, view);
        if response.drag_started()
            && let Some(pos) = ui.input(|i| i.pointer.press_origin())
        {
            match grip_at(&axis, pos) {
                Some(grip) => self.drag = Some((grip, axis.snap(pos.x))),
                None => self.zoom.pan = Some((view, pos.x)),
            }
        }
        if let Some(pos) = response.interact_pointer_pos() {
            if let Some((grip, _)) = self.drag {
                self.drag = Some((grip, axis.snap(pos.x)));
            }
            if let Some((from, x0)) = self.zoom.pan {
                let moved = from.panned(-f64::from(pos.x - x0) * from.span / f64::from(axis.width));
                self.zoom.target = Some(moved);
                self.zoom.shown = Some(moved);
                self.zoom.tween = None;
                view = moved;
            }
        }
        if response.drag_stopped() {
            self.zoom.pan = None;
            if let Some((grip, to)) = self.drag.take() {
                intents.push(match grip {
                    Grip::Start => RailIntent::MoveBound { start: true, to },
                    Grip::End => RailIntent::MoveBound { start: false, to },
                    Grip::Lens => RailIntent::Focus(to),
                });
            }
        }
        if !editable {
            self.drag = None;
        }
        let axis = Axis::new(chart, view);
        if editable
            && response.clicked()
            && self.drag.is_none()
            && let Some(pos) = response.interact_pointer_pos()
            && grip_at(&axis, pos).is_none()
        {
            intents.push(RailIntent::Focus(axis.snap(pos.x)));
        }
        let pointer = response.interact_pointer_pos().or(response.hover_pos());
        if self.zoom.pan.is_some() {
            ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
        } else if self.drag.is_some() || pointer.is_some_and(|p| grip_at(&axis, p).is_some()) {
            ui.ctx().set_cursor_icon(egui::CursorIcon::ResizeHorizontal);
        }

        // The cached mesh: rebuilt when its inputs or the view changed.
        let samples = hash_samples(inputs.samples);
        if self.profile.as_ref().is_none_or(|(h, _)| *h != samples) {
            let mut values: Vec<(u16, f32)> = inputs
                .samples
                .iter()
                .filter_map(|s| profile_value(s).map(|v| (s.position, v)))
                .collect();
            values.sort_by_key(|v| v.0);
            self.profile = Some((samples, values));
        }
        match (inputs.flight, inputs.start, inputs.end) {
            (None, Some(start), Some(end)) => {
                let plan = (start, end, inputs.step);
                if self.planned.as_ref().is_none_or(|(k, _)| *k != plan) {
                    self.planned = Some((plan, planned(start, end, inputs.step)));
                }
            }
            _ => self.planned = None,
        }
        let key = self.key(chart, ppp, inputs, samples, view);
        if self.cache.as_ref().is_none_or(|(k, _)| *k != key) {
            // The last frame's mesh is free again once it was painted: its
            // buffers are refilled rather than allocated anew.
            let mut arc = self.cache.take().map(|(_, a)| a).unwrap_or_default();
            if Arc::get_mut(&mut arc).is_none() {
                arc = Arc::new(Mesh::default());
            }
            if let Some(mesh) = Arc::get_mut(&mut arc) {
                self.build(mesh, chart, ppp, inputs, view, palette);
            }
            self.cache = Some((key, arc));
            self.rebuilds += 1;
        }
        if let Some((_, mesh)) = &self.cache {
            ui.painter_at(Rect::from_x_y_ranges(
                axis.left..=axis.right(),
                chart.y_range(),
            ))
            .add(Shape::mesh(mesh.clone()));
        }
        let painter = ui.painter_at(chart);
        let top_gap = chart.top() + 22.0;
        let label = |pos: Pos2, anchor: Align2, text: &str, color: Color32| {
            style::paint_job(&painter, pos, anchor, style::caps_job(text, 10.0, color));
        };
        // Scale labels (cheap text, a handful).
        let major = f64::from(label_spacing(view.span, axis.width));
        let mut p = (view.lo / major).ceil() * major;
        while p <= view.hi() {
            let x = axis.xf(p);
            if x > axis.left + 40.0 && x < axis.right() - 40.0 {
                label(
                    egui::pos2(x, chart.bottom() - 3.0),
                    Align2::CENTER_BOTTOM,
                    &style::focus_units(p as u16),
                    palette.ink3,
                );
            }
            p += major;
        }
        label(
            egui::pos2(axis.left, chart.bottom() - 3.0),
            Align2::LEFT_BOTTOM,
            "Near",
            palette.ink3,
        );
        label(
            egui::pos2(axis.right(), chart.bottom() - 3.0),
            Align2::RIGHT_BOTTOM,
            "Far",
            palette.ink3,
        );
        let in_view = |x: f32| x >= axis.left - 0.5 && x <= axis.right() + 0.5;
        // Handles (a dragged one where it is being taken).
        for (grip, bound, name) in [
            (Grip::Start, inputs.start, "Start"),
            (Grip::End, inputs.end, "End"),
        ] {
            let shown = match self.drag {
                Some((g, to)) if g == grip => Some(to),
                _ => bound,
            };
            let Some(b) = shown else { continue };
            let text = format!("{name} {}", style::focus_units(b));
            let x = axis.x(b);
            if !in_view(x) {
                edge_marker(
                    &painter,
                    &axis,
                    x < axis.left,
                    chart.top() + 7.0,
                    &text,
                    palette.accent,
                );
                continue;
            }
            let dir = if grip == Grip::Start { -1.0 } else { 1.0 };
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
                if grip == Grip::Start {
                    Align2::RIGHT_BOTTOM
                } else {
                    Align2::LEFT_BOTTOM
                },
                &text,
                palette.accent,
            );
        }
        // The lens, and where it is being dragged to.
        let dragged_lens = match self.drag {
            Some((Grip::Lens, to)) => Some(to),
            _ => None,
        };
        for (lens, color, caption) in [
            (inputs.lens, palette.ink, "Lens"),
            (dragged_lens, palette.plane, "Focus to"),
        ] {
            let Some(lens) = lens else { continue };
            let text = format!("{caption} {}", style::focus_units(lens));
            let x = axis.x(lens);
            if !in_view(x) {
                edge_marker(&painter, &axis, x < axis.left, top_gap + 4.0, &text, color);
                continue;
            }
            painter.line_segment(
                [egui::pos2(x, top_gap), egui::pos2(x, base)],
                Stroke::new(1.0_f32, color),
            );
            painter.add(Shape::convex_polygon(
                vec![
                    egui::pos2(x - 5.0, base + 7.0),
                    egui::pos2(x + 5.0, base + 7.0),
                    egui::pos2(x, base),
                ],
                color,
                Stroke::NONE,
            ));
            label(
                egui::pos2(x + 7.0, top_gap + 9.0),
                Align2::LEFT_BOTTOM,
                &text,
                color,
            );
        }
        // Hover: the position under the pointer, on the scale's resolution.
        if self.drag.is_none()
            && self.zoom.pan.is_none()
            && let Some(pos) = response.hover_pos()
        {
            let at = axis.snap(pos.x);
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

/// A mark at the chart's end for something out of view: a small triangle
/// pointing the way, and its caption.
fn edge_marker(
    painter: &egui::Painter,
    axis: &Axis,
    left: bool,
    y: f32,
    text: &str,
    color: Color32,
) {
    let (tip, back, anchor, at) = if left {
        (
            axis.left - 14.0,
            axis.left - 8.0,
            Align2::LEFT_CENTER,
            axis.left - 4.0,
        )
    } else {
        (
            axis.right() + 14.0,
            axis.right() + 8.0,
            Align2::RIGHT_CENTER,
            axis.right() + 4.0,
        )
    };
    painter.add(Shape::convex_polygon(
        vec![
            egui::pos2(tip, y),
            egui::pos2(back, y - 4.0),
            egui::pos2(back, y + 4.0),
        ],
        color,
        Stroke::NONE,
    ));
    style::paint_job(
        painter,
        egui::pos2(at, y),
        anchor,
        style::caps_job(text, 10.0, color),
    );
}

/// The scale slider: the visible span on a log scale, the whole travel at
/// the left and the finest scale at the right; decade ticks, a mark where
/// Fit is, and a square thumb. Returns the span asked for, if any.
fn scale_slider(
    ui: &mut Ui,
    span: f64,
    fit: f64,
    palette: &CapturePalette,
) -> (Response, Option<f64>) {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(116.0, 16.0), Sense::click_and_drag());
    let (l_max, l_min) = (TRAVEL.ln(), MIN_SPAN.ln());
    let x_of = |s: f64| {
        let t = ((l_max - s.clamp(MIN_SPAN, TRAVEL).ln()) / (l_max - l_min)) as f32;
        rect.left() + 3.0 + t * (rect.width() - 6.0)
    };
    let p = ui.painter();
    let ppp = ui.ctx().pixels_per_point();
    let y = on_pixel(rect.center().y, ppp);
    let active = response.hovered() || response.dragged();
    p.rect_filled(
        Rect::from_min_max(
            egui::pos2(rect.left(), y),
            egui::pos2(rect.right(), y + 1.0 / ppp),
        ),
        0.0,
        if active { palette.ink3 } else { palette.line2 },
    );
    for decade in [100.0, 1_000.0, 10_000.0] {
        let x = on_pixel(x_of(decade), ppp);
        p.rect_filled(
            Rect::from_min_max(egui::pos2(x, y - 3.0), egui::pos2(x + 1.0 / ppp, y)),
            0.0,
            palette.line2,
        );
    }
    let fx = on_pixel(x_of(fit), ppp);
    p.rect_filled(
        Rect::from_min_max(egui::pos2(fx - 1.0, y + 2.0), egui::pos2(fx + 1.0, y + 6.0)),
        0.0,
        palette.accent.gamma_multiply(0.8),
    );
    let tx = on_pixel(x_of(span), ppp);
    p.rect_filled(
        Rect::from_center_size(egui::pos2(tx, y), egui::vec2(5.0, 12.0)),
        0.0,
        if response.dragged() {
            palette.accent
        } else if active {
            palette.ink
        } else {
            palette.ink2
        },
    );
    let asked = if response.dragged() || response.clicked() {
        response.interact_pointer_pos().map(|pos| {
            let t = f64::from(((pos.x - rect.left() - 3.0) / (rect.width() - 6.0)).clamp(0.0, 1.0));
            (l_max - t * (l_max - l_min)).exp()
        })
    } else {
        None
    };
    let response = if active {
        response.on_hover_cursor(egui::CursorIcon::ResizeHorizontal)
    } else {
        response
    };
    (response, asked)
}

/// A jog button: "-128" ... "+128". ASCII minus: the UI face draws U+2212
/// on the baseline, where it read as "_128".
fn jog(ui: &mut Ui, delta: i32, enabled: bool, palette: &CapturePalette) -> bool {
    let label = if delta < 0 {
        format!("-{}", -delta)
    } else {
        format!("+{delta}")
    };
    style::button(ui, &label, ButtonKind::Plain, 20.0, enabled, palette).clicked()
}

#[cfg(test)]
#[path = "capture-rail-tests.rs"]
mod tests;
