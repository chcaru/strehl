//! Studio 2 controls (implementation plan 6.4): square corners, hairline
//! outlines, tracked capitals, and amber only for selection and the main
//! action. Status marks are painted shapes, never font glyphs, so they mean
//! the same thing in every face and size.
use crate::studio_fonts::{self, Face};
use crate::studio_theme::{self, Tokens, scale};
use eframe::egui::{
    self, Color32, FontId, Pos2, Rect, Response, Sense, Stroke, Ui, Vec2, WidgetInfo, WidgetType,
    text::LayoutJob,
};
use std::{ops::RangeInclusive, sync::Arc};

pub(crate) const CONTROL_HEIGHT: f32 = 28.0;
pub(crate) const SMALL_HEIGHT: f32 = 22.0;
pub(crate) const LARGE_HEIGHT: f32 = 36.0;
pub(crate) const SEGMENT_HEIGHT: f32 = 24.0;
pub(crate) const TOGGLE_SIZE: Vec2 = Vec2::new(26.0, 14.0);
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
pub(crate) const SLIDER_HEIGHT: f32 = 13.0;
/// Every mark occupies this square, drawn or not, so labels never move.
pub(crate) const MARK_SLOT: f32 = 8.0;

fn tokens(ui: &Ui) -> Tokens {
    studio_theme::tokens(ui.ctx())
}
pub(crate) fn font(ui: &Ui, face: Face, size: f32) -> FontId {
    studio_fonts::font(ui.ctx(), face, size)
}

/// Tracked capitals as a layout job. The colour is left as the placeholder so
/// one cached layout serves every state; pass the ink when painting.
pub(crate) fn caps_job(ui: &Ui, text: &str, size: f32) -> LayoutJob {
    studio_fonts::tracked(
        text,
        font(ui, Face::Regular, size),
        Color32::PLACEHOLDER,
        scale::CAPS_TRACKING,
    )
}
pub(crate) fn caps_galley(ui: &Ui, text: &str, size: f32) -> Arc<egui::Galley> {
    ui.painter().layout_job(caps_job(ui, text, size))
}
/// A single line of text in a face, coloured when painted.
pub(crate) fn text_galley(ui: &Ui, text: &str, face: Face, size: f32) -> Arc<egui::Galley> {
    ui.painter()
        .layout_no_wrap(text.to_owned(), font(ui, face, size), Color32::PLACEHOLDER)
}
/// Paint a galley vertically centred on `y`, starting at `x`, in `color`.
pub(crate) fn paint_galley_at(
    painter: &egui::Painter,
    x: f32,
    y: f32,
    galley: &Arc<egui::Galley>,
    color: Color32,
) {
    painter.galley(
        egui::pos2(x, y - galley.size().y * 0.5),
        galley.clone(),
        color,
    );
}

/// Keyboard focus: a 1 px accent outline offset by 2 px.
pub(crate) fn focus_outline(painter: &egui::Painter, rect: Rect, t: &Tokens) {
    painter.rect_stroke(
        rect.expand(2.0),
        0.0,
        Stroke::new(1.0_f32, t.accent),
        egui::StrokeKind::Inside,
    );
}
fn outline(painter: &egui::Painter, rect: Rect, color: Color32) {
    painter.rect_stroke(
        rect,
        0.0,
        Stroke::new(1.0_f32, color),
        egui::StrokeKind::Inside,
    );
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Kind {
    /// Amber fill: the main action, one per view.
    Primary,
    /// A hairline outline.
    Standard,
    /// Text only.
    Quiet,
    /// An outline with the failure colour: destructive.
    Danger,
}
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Size {
    Small,
    Regular,
    Large,
}
impl Size {
    pub(crate) fn height(self) -> f32 {
        match self {
            Self::Small => SMALL_HEIGHT,
            Self::Regular => CONTROL_HEIGHT,
            Self::Large => LARGE_HEIGHT,
        }
    }
    fn text(self) -> f32 {
        match self {
            Self::Small => scale::SECONDARY,
            Self::Regular => scale::CONTROL,
            Self::Large => 13.5,
        }
    }
    fn padding(self) -> f32 {
        match self {
            Self::Small => 8.0,
            Self::Regular => 12.0,
            Self::Large => 18.0,
        }
    }
}

/// A Studio button. `selected` marks a toggled command with an amber rule
/// under it; `detail` is a dim suffix such as an estimated time.
#[must_use = "add the button with ui.add"]
pub(crate) struct Button<'a> {
    text: &'a str,
    kind: Kind,
    size: Size,
    enabled: bool,
    selected: bool,
    wide: bool,
    detail: Option<&'a str>,
    chevron: bool,
}
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
impl<'a> Button<'a> {
    pub(crate) fn new(text: &'a str) -> Self {
        Self {
            text,
            kind: Kind::Standard,
            size: Size::Regular,
            enabled: true,
            selected: false,
            wide: false,
            detail: None,
            chevron: false,
        }
    }
    pub(crate) fn primary(text: &'a str) -> Self {
        Self::new(text).kind(Kind::Primary)
    }
    pub(crate) fn quiet(text: &'a str) -> Self {
        Self::new(text).kind(Kind::Quiet)
    }
    pub(crate) fn danger(text: &'a str) -> Self {
        Self::new(text).kind(Kind::Danger)
    }
    pub(crate) fn kind(mut self, kind: Kind) -> Self {
        self.kind = kind;
        self
    }
    pub(crate) fn size(mut self, size: Size) -> Self {
        self.size = size;
        self
    }
    pub(crate) fn small(self) -> Self {
        self.size(Size::Small)
    }
    pub(crate) fn large(self) -> Self {
        self.size(Size::Large)
    }
    pub(crate) fn enabled(mut self, enabled: bool) -> Self {
        self.enabled = enabled;
        self
    }
    pub(crate) fn selected(mut self, selected: bool) -> Self {
        self.selected = selected;
        self
    }
    /// Fill the available width, label centred.
    pub(crate) fn wide(mut self) -> Self {
        self.wide = true;
        self
    }
    pub(crate) fn detail(mut self, detail: &'a str) -> Self {
        self.detail = Some(detail);
        self
    }
    pub(crate) fn chevron(mut self) -> Self {
        self.chevron = true;
        self
    }
}
impl egui::Widget for Button<'_> {
    fn ui(self, ui: &mut Ui) -> Response {
        let t = tokens(ui);
        let face = if self.kind == Kind::Primary {
            Face::Strong
        } else {
            Face::Regular
        };
        let ink = match self.kind {
            Kind::Primary => t.accent_ink,
            Kind::Quiet if !self.selected => t.ink2,
            Kind::Danger => t.bad,
            _ => t.ink,
        };
        let label = text_galley(ui, self.text, face, self.size.text());
        let detail = self
            .detail
            .map(|detail| text_galley(ui, detail, Face::Regular, self.size.text()));
        let padding = if self.kind == Kind::Quiet {
            6.0
        } else {
            self.size.padding()
        };
        let gap = 7.0;
        let content = label.size().x
            + detail.as_ref().map_or(0.0, |d| gap + d.size().x)
            + if self.chevron { gap + 5.0 } else { 0.0 };
        let mut width = (content + padding * 2.0).ceil();
        if self.wide {
            width = width.max(ui.available_width());
        }
        let (rect, response) = ui.allocate_exact_size(
            egui::vec2(width, self.size.height()),
            if self.enabled {
                Sense::click()
            } else {
                Sense::hover()
            },
        );
        response.widget_info(|| WidgetInfo::labeled(WidgetType::Button, self.enabled, self.text));
        if !ui.is_rect_visible(rect) {
            return response;
        }
        let mut painter = ui.painter_at(rect.expand(3.0));
        if !self.enabled {
            painter.multiply_opacity(0.4);
        }
        let hovered = self.enabled && response.hovered();
        match self.kind {
            Kind::Primary => {
                let fill = if hovered && !response.is_pointer_button_down_on() {
                    t.accent.gamma_multiply(0.92)
                } else {
                    t.accent
                };
                painter.rect_filled(rect, 0.0, fill);
            }
            Kind::Standard | Kind::Danger => {
                outline(&painter, rect, if hovered { t.ink3 } else { t.line2 })
            }
            Kind::Quiet => {}
        }
        if self.selected {
            painter.rect_filled(
                Rect::from_min_max(egui::pos2(rect.left(), rect.bottom() - 1.5), rect.max),
                0.0,
                t.accent,
            );
        }
        let ink = if hovered && self.kind == Kind::Quiet {
            t.ink
        } else {
            ink
        };
        let mut x = if self.wide {
            rect.center().x - content * 0.5
        } else {
            rect.left() + padding
        };
        let y = rect.center().y;
        painter.galley(egui::pos2(x, y - label.size().y * 0.5), label.clone(), ink);
        x += label.size().x;
        if let Some(detail) = &detail {
            x += gap;
            let dim = if self.kind == Kind::Primary {
                t.accent_ink.gamma_multiply(0.7)
            } else {
                t.ink3
            };
            paint_galley_at(&painter, x, y, detail, dim);
            x += detail.size().x;
        }
        if self.chevron {
            x += gap;
            let stroke = Stroke::new(1.25_f32, ink);
            painter.line_segment([egui::pos2(x, y - 4.0), egui::pos2(x + 4.0, y)], stroke);
            painter.line_segment([egui::pos2(x + 4.0, y), egui::pos2(x, y + 4.0)], stroke);
        }
        if response.has_focus() {
            focus_outline(&painter, rect, &t);
        }
        if self.enabled {
            response.on_hover_cursor(egui::CursorIcon::PointingHand)
        } else {
            response
        }
    }
}

/// A segmented choice, 24 px high: the chosen segment is raised with an
/// amber rule under it.
pub(crate) fn segmented<T: PartialEq + Copy>(
    ui: &mut Ui,
    id_salt: impl std::hash::Hash,
    value: &mut T,
    options: &[(T, &str)],
) -> Response {
    let t = tokens(ui);
    let id = ui.id().with(("studio-segmented", id_salt));
    let labels: Vec<_> = options
        .iter()
        .map(|(_, text)| text_galley(ui, text, Face::Regular, scale::SECONDARY))
        .collect();
    let widths: Vec<f32> = labels.iter().map(|g| (g.size().x + 20.0).ceil()).collect();
    let (rect, mut response) = ui.allocate_exact_size(
        egui::vec2(widths.iter().sum(), SEGMENT_HEIGHT),
        Sense::hover(),
    );
    let mut x = rect.left();
    let mut chosen = None;
    let mut focused = None;
    for (index, ((option, text), galley)) in options.iter().zip(&labels).enumerate() {
        let segment = Rect::from_min_size(
            egui::pos2(x, rect.top()),
            egui::vec2(widths[index], rect.height()),
        );
        x = segment.right();
        let hit = ui.interact(segment, id.with(index), Sense::click());
        hit.widget_info(|| {
            WidgetInfo::selected(WidgetType::SelectableLabel, true, option == value, *text)
        });
        let selected = option == value;
        let painter = ui.painter();
        if selected {
            painter.rect_filled(segment, 0.0, t.control);
            painter.rect_filled(
                Rect::from_min_max(
                    egui::pos2(segment.left(), segment.bottom() - 1.5),
                    segment.max,
                ),
                0.0,
                t.accent,
            );
        }
        if index > 0 {
            painter.line_segment(
                [
                    segment.left_top() + egui::vec2(0.5, 0.0),
                    segment.left_bottom() + egui::vec2(0.5, 0.0),
                ],
                Stroke::new(1.0_f32, t.line2),
            );
        }
        let color = if selected || hit.hovered() {
            t.ink
        } else {
            t.ink3
        };
        painter.galley(
            egui::pos2(
                segment.left() + 10.0,
                segment.center().y - galley.size().y * 0.5,
            ),
            galley.clone(),
            color,
        );
        if hit.has_focus() {
            focused = Some(segment);
        }
        if hit.clicked() && !selected {
            chosen = Some(*option);
        }
        response |= hit;
    }
    outline(ui.painter(), rect, t.line2);
    if let Some(segment) = focused {
        focus_outline(ui.painter(), segment, &t);
    }
    if let Some(option) = chosen {
        *value = option;
        response.mark_changed();
    }
    response
}

/// A 26 x 14 switch with a square knob; amber when on.
pub(crate) fn toggle(ui: &mut Ui, on: &mut bool) -> Response {
    let t = tokens(ui);
    let (rect, mut response) = ui.allocate_exact_size(TOGGLE_SIZE, Sense::click());
    if response.clicked() {
        *on = !*on;
        response.mark_changed();
    }
    response.widget_info(|| WidgetInfo::selected(WidgetType::Checkbox, true, *on, ""));
    let position = ui.ctx().animate_bool_responsive(response.id, *on);
    let painter = ui.painter();
    outline(painter, rect, if *on { t.accent } else { t.line2 });
    let knob = Rect::from_min_size(
        rect.min + egui::vec2(3.0 + 12.0 * position, 3.0),
        egui::vec2(8.0, 8.0),
    );
    painter.rect_filled(knob, 0.0, if *on { t.accent } else { t.ink3 });
    if response.has_focus() {
        focus_outline(painter, rect, &t);
    }
    response.on_hover_cursor(egui::CursorIcon::PointingHand)
}

/// A label on the left and a switch on the right, one row high.
pub(crate) fn toggle_row(ui: &mut Ui, label: &str, on: &mut bool) -> Response {
    let t = tokens(ui);
    ui.horizontal(|ui| {
        ui.set_min_height(SEGMENT_HEIGHT);
        let galley = text_galley(ui, label, Face::Regular, scale::BODY);
        let width = ui.available_width() - TOGGLE_SIZE.x;
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(width.max(0.0), SEGMENT_HEIGHT), Sense::hover());
        paint_galley_at(ui.painter(), rect.left(), rect.center().y, &galley, t.ink2);
        toggle(ui, on)
    })
    .inner
}

/// A slider drawn as a 1 px rule with a 2 px index and a tick at the default.
/// Drag or click to set; double-click restores the default; arrows step.
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
pub(crate) struct Slider<'a> {
    value: &'a mut f32,
    range: RangeInclusive<f32>,
    default: Option<f32>,
    width: Option<f32>,
}
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
impl<'a> Slider<'a> {
    pub(crate) fn new(value: &'a mut f32, range: RangeInclusive<f32>) -> Self {
        Self {
            value,
            range,
            default: None,
            width: None,
        }
    }
    pub(crate) fn default_value(mut self, default: f32) -> Self {
        self.default = Some(default);
        self
    }
    pub(crate) fn width(mut self, width: f32) -> Self {
        self.width = Some(width);
        self
    }
}
impl egui::Widget for Slider<'_> {
    fn ui(self, ui: &mut Ui) -> Response {
        let t = tokens(ui);
        let width = self.width.unwrap_or_else(|| ui.available_width()).max(24.0);
        let (rect, mut response) =
            ui.allocate_exact_size(egui::vec2(width, SLIDER_HEIGHT), Sense::click_and_drag());
        let (low, high) = (*self.range.start(), *self.range.end());
        let span = (high - low).max(f32::EPSILON);
        let x_of = |v: f32| rect.left() + ((v - low) / span).clamp(0.0, 1.0) * rect.width();
        let before = *self.value;
        if let Some(pointer) = response.interact_pointer_pos()
            && (response.dragged() || response.clicked())
        {
            *self.value = low + ((pointer.x - rect.left()) / rect.width()).clamp(0.0, 1.0) * span;
        }
        if response.double_clicked()
            && let Some(default) = self.default
        {
            *self.value = default;
        }
        if response.has_focus() {
            let step = span / 100.0;
            let (left, right) = ui.input(|i| {
                (
                    i.key_pressed(egui::Key::ArrowLeft),
                    i.key_pressed(egui::Key::ArrowRight),
                )
            });
            if left {
                *self.value -= step;
            }
            if right {
                *self.value += step;
            }
        }
        *self.value = self.value.clamp(low, high);
        if *self.value != before {
            response.mark_changed();
        }
        response.widget_info(|| WidgetInfo::slider(true, f64::from(*self.value), ""));
        let painter = ui.painter();
        let rule_y = rect.top() + 6.5;
        painter.line_segment(
            [
                egui::pos2(rect.left(), rule_y),
                egui::pos2(rect.right(), rule_y),
            ],
            Stroke::new(1.0_f32, t.line2),
        );
        let anchor = self.default.unwrap_or(low);
        let (a, b) = (x_of(anchor), x_of(*self.value));
        if (a - b).abs() >= 0.5 {
            painter.rect_filled(
                Rect::from_min_max(
                    egui::pos2(a.min(b), rect.top() + 5.5),
                    egui::pos2(a.max(b), rect.top() + 7.5),
                ),
                0.0,
                t.accent,
            );
        }
        if let Some(default) = self.default {
            let x = x_of(default).round() + 0.5;
            painter.line_segment(
                [
                    egui::pos2(x, rect.top() + 3.0),
                    egui::pos2(x, rect.top() + 10.0),
                ],
                Stroke::new(1.0_f32, t.ink3),
            );
        }
        painter.rect_filled(
            Rect::from_min_size(
                egui::pos2(b - 1.0, rect.top()),
                egui::vec2(2.0, SLIDER_HEIGHT),
            ),
            0.0,
            t.ink,
        );
        if response.has_focus() {
            focus_outline(painter, rect, &t);
        }
        response
    }
}

/// The five status marks of the design, plus an empty reserved slot.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Mark {
    /// Filled circle: fine.
    Fine,
    /// Triangle: needs a look.
    Look,
    /// 45 degree diamond: failed.
    Failed,
    /// Ring: not yet.
    NotYet,
    /// Half-filled ring: running.
    Running,
    /// Nothing drawn; the slot is still reserved.
    Hidden,
}
impl Mark {
    pub(crate) fn color(self, t: &Tokens) -> Color32 {
        match self {
            Self::Fine => t.ok,
            Self::Look => t.warn,
            Self::Failed => t.bad,
            Self::NotYet | Self::Hidden => t.ink3,
            Self::Running => t.accent,
        }
    }
}

/// Paint a status mark centred on `center`, as shapes only.
pub(crate) fn paint_mark(painter: &egui::Painter, center: Pos2, mark: Mark, t: &Tokens) {
    let color = mark.color(t);
    match mark {
        Mark::Fine => {
            painter.circle_filled(center, 3.5, color);
        }
        Mark::Look => {
            painter.add(egui::Shape::convex_polygon(
                vec![
                    center + egui::vec2(0.0, -3.5),
                    center + egui::vec2(4.0, 3.5),
                    center + egui::vec2(-4.0, 3.5),
                ],
                color,
                Stroke::NONE,
            ));
        }
        Mark::Failed => {
            let r = 4.25;
            painter.add(egui::Shape::convex_polygon(
                vec![
                    center + egui::vec2(0.0, -r),
                    center + egui::vec2(r, 0.0),
                    center + egui::vec2(0.0, r),
                    center + egui::vec2(-r, 0.0),
                ],
                color,
                Stroke::NONE,
            ));
        }
        Mark::NotYet => {
            painter.circle_stroke(center, 2.9, Stroke::new(1.2_f32, color));
        }
        Mark::Running => {
            let points: Vec<Pos2> = (0..=12)
                .map(|step| {
                    let angle =
                        std::f32::consts::FRAC_PI_2 + std::f32::consts::PI * step as f32 / 12.0;
                    center + 3.5 * egui::vec2(angle.cos(), angle.sin())
                })
                .collect();
            painter.add(egui::Shape::convex_polygon(points, color, Stroke::NONE));
            painter.circle_stroke(center, 2.9, Stroke::new(1.2_f32, color));
        }
        Mark::Hidden => {}
    }
}

/// Reserve a mark slot in a layout and paint the mark in it.
pub(crate) fn mark(ui: &mut Ui, mark: Mark) -> Response {
    let t = tokens(ui);
    let (rect, response) = ui.allocate_exact_size(egui::vec2(MARK_SLOT, MARK_SLOT), Sense::hover());
    paint_mark(ui.painter(), rect.center(), mark, &t);
    response
}

/// A mark and a short fact; `boxed` draws the 20 px outlined variant.
pub(crate) fn chip(ui: &mut Ui, mark: Option<Mark>, text: &str, boxed: bool) -> Response {
    let t = tokens(ui);
    let galley = text_galley(ui, text, Face::Regular, scale::SECONDARY);
    let padding = if boxed { 7.0 } else { 0.0 };
    let lead = if mark.is_some() { MARK_SLOT + 6.0 } else { 0.0 };
    let size = egui::vec2(
        (padding * 2.0 + lead + galley.size().x).ceil(),
        if boxed {
            20.0
        } else {
            galley.size().y.max(MARK_SLOT)
        },
    );
    let (rect, response) = ui.allocate_exact_size(size, Sense::hover());
    let painter = ui.painter();
    if boxed {
        outline(painter, rect, t.line2);
    }
    let y = rect.center().y;
    if let Some(mark) = mark {
        paint_mark(
            painter,
            egui::pos2(rect.left() + padding + MARK_SLOT * 0.5, y),
            mark,
            &t,
        );
    }
    paint_galley_at(painter, rect.left() + padding + lead, y, &galley, t.ink2);
    response
}

/// A keyboard key, as on the hint bar.
pub(crate) fn key_cap(ui: &mut Ui, key: &str) -> Response {
    let t = tokens(ui);
    let galley = ui.painter().layout_job(studio_fonts::tracked(
        key,
        font(ui, Face::Regular, scale::CAPS),
        Color32::PLACEHOLDER,
        0.08,
    ));
    let size = egui::vec2((galley.size().x + 10.0).ceil(), 16.0);
    let (rect, response) = ui.allocate_exact_size(size, Sense::hover());
    let painter = ui.painter();
    outline(painter, rect, t.line2);
    paint_galley_at(
        painter,
        rect.left() + 5.0,
        rect.center().y + 0.5,
        &galley,
        t.ink3,
    );
    response
}

/// Tracked capitals in the faint ink: section labels and captions.
pub(crate) fn caps(ui: &mut Ui, text: &str) -> Response {
    let color = tokens(ui).ink3;
    caps_colored(ui, text, scale::CAPS, color)
}
pub(crate) fn caps_colored(ui: &mut Ui, text: &str, size: f32, color: Color32) -> Response {
    let galley = caps_galley(ui, text, size);
    let (rect, response) = ui.allocate_exact_size(galley.size(), Sense::hover());
    ui.painter().galley(rect.min, galley, color);
    response
}

/// A link: neutral capitals, amber only on a check that needs a look.
pub(crate) fn link(ui: &mut Ui, text: &str, needs_look: bool) -> Response {
    let t = tokens(ui);
    let galley = caps_galley(ui, text, scale::CAPS);
    let (rect, response) =
        ui.allocate_exact_size(galley.size() + egui::vec2(0.0, 2.0), Sense::click());
    response.widget_info(|| WidgetInfo::labeled(WidgetType::Link, true, text));
    let color = if needs_look {
        t.accent
    } else if response.hovered() {
        t.ink
    } else {
        t.ink2
    };
    let painter = ui.painter();
    painter.galley(rect.min, galley, color);
    if response.hovered() {
        painter.line_segment(
            [
                rect.left_bottom() - egui::vec2(0.0, 0.5),
                rect.right_bottom() - egui::vec2(0.0, 0.5),
            ],
            Stroke::new(1.0_f32, t.ink3),
        );
    }
    if response.has_focus() {
        focus_outline(painter, rect, &t);
    }
    response.on_hover_cursor(egui::CursorIcon::PointingHand)
}

/// An inspector tab: tracked capitals, an amber rule under the open one, and
/// an optional warn-coloured count.
pub(crate) fn tab(ui: &mut Ui, text: &str, selected: bool, badge: Option<&str>) -> Response {
    let t = tokens(ui);
    let height = ui.available_height().max(SEGMENT_HEIGHT);
    let label = caps_galley(ui, text, scale::STATION);
    let badge_galley = badge.map(|b| text_galley(ui, b, Face::Regular, scale::STATION));
    let width = 20.0 + label.size().x + badge_galley.as_ref().map_or(0.0, |b| 6.0 + b.size().x);
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width.ceil(), height), Sense::click());
    response
        .widget_info(|| WidgetInfo::selected(WidgetType::SelectableLabel, true, selected, text));
    let color = if selected || response.hovered() {
        t.ink
    } else {
        t.ink3
    };
    let painter = ui.painter();
    let y = rect.center().y;
    painter.galley(
        egui::pos2(rect.left() + 10.0, y - label.size().y * 0.5),
        label.clone(),
        color,
    );
    if let Some(badge) = &badge_galley {
        paint_galley_at(
            painter,
            rect.left() + 16.0 + label.size().x,
            y,
            badge,
            t.warn,
        );
    }
    if selected {
        painter.rect_filled(
            Rect::from_min_max(
                egui::pos2(rect.left() + 10.0, rect.bottom() - 2.0),
                egui::pos2(rect.right() - 10.0, rect.bottom()),
            ),
            0.0,
            t.accent,
        );
    }
    if response.has_focus() {
        focus_outline(painter, rect.shrink(4.0), &t);
    }
    response.on_hover_cursor(egui::CursorIcon::PointingHand)
}

/// A section heading: capitals on a rule, with room on the right for a link.
pub(crate) fn section<R>(ui: &mut Ui, label: &str, right: impl FnOnce(&mut Ui) -> R) -> R {
    let t = tokens(ui);
    let response = ui.horizontal(|ui| {
        caps(ui, label);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), right)
            .inner
    });
    let rect = response.response.rect;
    let y = rect.bottom() + 3.5;
    ui.painter().line_segment(
        [
            egui::pos2(rect.left(), y),
            egui::pos2(ui.max_rect().right(), y),
        ],
        Stroke::new(1.0_f32, t.line),
    );
    ui.add_space(8.0);
    response.inner
}

#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
pub(crate) struct CheckResponse {
    pub response: Response,
    pub link_clicked: bool,
}
/// A check: its mark, a title, the measured fact, and an optional link.
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
pub(crate) fn check_row(
    ui: &mut Ui,
    mark: Mark,
    title: &str,
    fact: &str,
    link_text: Option<&str>,
) -> CheckResponse {
    let t = tokens(ui);
    let width = ui.available_width();
    let link_galley = link_text.map(|text| caps_galley(ui, text, scale::CAPS));
    let text_width =
        (width - 22.0 - link_galley.as_ref().map_or(0.0, |g| g.size().x + 12.0)).max(40.0);
    let title_galley = ui.painter().layout(
        title.to_owned(),
        font(ui, Face::Strong, scale::BODY),
        t.ink,
        text_width,
    );
    let fact_galley = ui.painter().layout(
        fact.to_owned(),
        font(ui, Face::Regular, 12.5),
        t.ink2,
        text_width,
    );
    let height = 9.0 + title_galley.size().y + 2.0 + fact_galley.size().y + 9.0;
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, height), Sense::hover());
    let painter = ui.painter();
    paint_mark(
        painter,
        egui::pos2(
            rect.left() + 4.0,
            rect.top() + 9.0 + title_galley.size().y * 0.5,
        ),
        mark,
        &t,
    );
    let text_left = rect.left() + 22.0;
    painter.galley(
        egui::pos2(text_left, rect.top() + 9.0),
        title_galley.clone(),
        t.ink,
    );
    painter.galley(
        egui::pos2(text_left, rect.top() + 11.0 + title_galley.size().y),
        fact_galley,
        t.ink2,
    );
    painter.line_segment(
        [
            rect.left_bottom() - egui::vec2(0.0, 0.5),
            rect.right_bottom() - egui::vec2(0.0, 0.5),
        ],
        Stroke::new(1.0_f32, t.line),
    );
    let mut link_clicked = false;
    if let (Some(text), Some(galley)) = (link_text, link_galley) {
        let at = egui::pos2(
            rect.right() - galley.size().x,
            rect.top() + 9.0 + title_galley.size().y * 0.5 - galley.size().y * 0.5,
        );
        let link_rect = Rect::from_min_size(at, galley.size());
        let mut child = ui.new_child(
            egui::UiBuilder::new()
                .max_rect(link_rect.expand(1.0))
                .id_salt(("check-link", title)),
        );
        link_clicked = link(&mut child, text, matches!(mark, Mark::Look | Mark::Failed)).clicked();
    }
    CheckResponse {
        response,
        link_clicked,
    }
}

#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Step {
    Done,
    Current,
    Look,
    Todo,
}
/// The lifecycle line: capture, stack, develop, export, joined by rules.
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
pub(crate) fn lifecycle(ui: &mut Ui, steps: &[(&str, Step)]) -> Response {
    let t = tokens(ui);
    let galleys: Vec<_> = steps
        .iter()
        .map(|(text, _)| text_galley(ui, text, Face::Regular, scale::SECONDARY))
        .collect();
    let joint = 28.0;
    let width: f32 = galleys
        .iter()
        .map(|g| MARK_SLOT + 6.0 + g.size().x)
        .sum::<f32>()
        + joint * steps.len().saturating_sub(1) as f32;
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width.ceil(), 16.0), Sense::hover());
    let painter = ui.painter();
    let y = rect.center().y;
    let mut x = rect.left();
    for (index, ((_, step), galley)) in steps.iter().zip(&galleys).enumerate() {
        if index > 0 {
            painter.line_segment(
                [egui::pos2(x + 7.0, y), egui::pos2(x + joint - 7.0, y)],
                Stroke::new(1.0_f32, t.line2),
            );
            x += joint;
        }
        let mark = match step {
            Step::Done => Mark::Fine,
            Step::Current => Mark::Running,
            Step::Look => Mark::Look,
            Step::Todo => Mark::NotYet,
        };
        paint_mark(painter, egui::pos2(x + MARK_SLOT * 0.5, y), mark, &t);
        x += MARK_SLOT + 6.0;
        let color = match step {
            Step::Done => t.ink2,
            Step::Current => t.ink,
            Step::Look | Step::Todo => t.ink3,
        };
        paint_galley_at(painter, x, y, galley, color);
        x += galley.size().x;
    }
    response
}

/// A 2 px progress rule.
pub(crate) fn progress_bar(
    painter: &egui::Painter,
    rect: Rect,
    fraction: f32,
    color: Color32,
    t: &Tokens,
) {
    painter.rect_filled(rect, 0.0, t.line2);
    let filled = Rect::from_min_size(
        rect.min,
        egui::vec2(rect.width() * fraction.clamp(0.0, 1.0), rect.height()),
    );
    painter.rect_filled(filled, 0.0, color);
}

/// The Strehl mark from `assets/strehl.svg`: a disc cut into planes, the gold
/// plane in focus and the rest thinning and darkening below it. The mark keeps
/// the application icon's colours in every theme. At title-bar size it uses the
/// generator's hand-fitted 20 px rows, with each edge on a physical pixel.
pub(crate) fn brand_mark(painter: &egui::Painter, rect: Rect) {
    const INKS: [[u8; 3]; 5] = [
        [0xe6, 0xb4, 0x50],
        [0xe0, 0x89, 0x3e],
        [0xcc, 0x5a, 0x33],
        [0xa2, 0x3f, 0x2c],
        [0x74, 0x37, 0x2a],
    ];
    const ROWS: [(f32, f32); 5] = [
        (0.0, 9.0),
        (10.0, 12.0),
        (13.0, 14.0),
        (16.0, 17.0),
        (19.0, 20.0),
    ];
    let pixel = 1.0 / painter.pixels_per_point();
    let snap = |y: f32| (y / pixel).round() * pixel;
    let radius = rect.width().min(rect.height()) / 2.0;
    let centre = rect.center();
    let unit = radius / 10.0;
    let top = centre.y - radius;
    let half_width = |y: f32| (radius * radius - (y - centre.y).powi(2)).max(0.0).sqrt();
    for ((first, end), [r, g, b]) in ROWS.into_iter().zip(INKS) {
        let y0 = snap(top + first * unit);
        let y1 = snap(top + end * unit).max(y0 + pixel);
        let steps = 8;
        let rows: Vec<f32> = (0..=steps)
            .map(|step| y0 + (y1 - y0) * step as f32 / steps as f32)
            .collect();
        let mut points: Vec<Pos2> = rows
            .iter()
            .map(|&y| egui::pos2(centre.x + half_width(y), y))
            .collect();
        points.extend(
            rows.iter()
                .rev()
                .map(|&y| egui::pos2(centre.x - half_width(y), y)),
        );
        if points.first() == points.last() {
            points.pop();
        }
        painter.add(egui::Shape::convex_polygon(
            points,
            Color32::from_rgb(r, g, b),
            Stroke::NONE,
        ));
    }
}

#[cfg(test)]
#[path = "studio-widgets-tests.rs"]
mod tests;
