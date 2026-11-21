//! The engraved look of Studio 2 for the Develop and Export stations: square
//! corners, hairlines, tracked capitals and drawn status marks
//! (`experiments/desktop-studio-2026-11-20/mockups/src/base.css`).
//!
//! Every widget takes a `StudioPalette`, so wiring the shell's tokens (P1,
//! `studio-theme.rs`) is one constructor. Widgets draw shapes only; none
//! allocates in proportion to the catalog or keeps state of its own.
use eframe::egui::{
    self, Align2, Color32, CornerRadius, FontId, Pos2, Rect, Response, Sense, Shape, Stroke,
    StrokeKind, Ui, Vec2, text::LayoutJob,
};

/// The colours the stations use. `GRAPHITE` is the locked default theme (D2).
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct StudioPalette {
    pub bg: Color32,
    pub panel: Color32,
    pub raised: Color32,
    pub control: Color32,
    pub line: Color32,
    pub line_2: Color32,
    pub ink: Color32,
    pub ink_2: Color32,
    pub ink_3: Color32,
    pub accent: Color32,
    pub accent_ink: Color32,
    pub accent_soft: Color32,
    pub ok: Color32,
    pub warn: Color32,
    pub bad: Color32,
    pub info: Color32,
    pub plane: Color32,
    pub surround: Color32,
}

impl StudioPalette {
    pub const GRAPHITE: Self = Self {
        bg: Color32::from_rgb(0x0b, 0x0b, 0x0c),
        panel: Color32::from_rgb(0x11, 0x11, 0x12),
        raised: Color32::from_rgb(0x17, 0x17, 0x18),
        control: Color32::from_rgb(0x1e, 0x1e, 0x20),
        line: Color32::from_rgb(0x23, 0x23, 0x26),
        line_2: Color32::from_rgb(0x37, 0x37, 0x3c),
        ink: Color32::from_rgb(0xe9, 0xe6, 0xde),
        ink_2: Color32::from_rgb(0xa1, 0x9f, 0x98),
        ink_3: Color32::from_rgb(0x80, 0x7e, 0x77),
        accent: Color32::from_rgb(0xe6, 0xb4, 0x50),
        accent_ink: Color32::from_rgb(0x17, 0x12, 0x04),
        accent_soft: Color32::from_rgba_premultiplied(28, 22, 10, 31),
        ok: Color32::from_rgb(0xa9, 0xc7, 0x79),
        warn: Color32::from_rgb(0xf0, 0x8a, 0x4b),
        bad: Color32::from_rgb(0xe5, 0x60, 0x4c),
        info: Color32::from_rgb(0x8a, 0xb4, 0xe8),
        plane: Color32::from_rgb(0x55, 0xd6, 0xc4),
        surround: Color32::from_rgb(0x0e, 0x0e, 0x0f),
    };
}

impl StudioPalette {
    /// The palette of the theme chosen in Preferences (Graphite, Instrument
    /// or Lightbox).
    pub(crate) fn from_tokens(t: &crate::studio_theme::Tokens) -> Self {
        Self {
            bg: t.bg,
            panel: t.panel,
            raised: t.raised,
            control: t.control,
            line: t.line,
            line_2: t.line2,
            ink: t.ink,
            ink_2: t.ink2,
            ink_3: t.ink3,
            accent: t.accent,
            accent_ink: t.accent_ink,
            accent_soft: t.accent_soft,
            ok: t.ok,
            warn: t.warn,
            bad: t.bad,
            info: t.info,
            plane: t.plane,
            surround: t.surround,
        }
    }

    pub(crate) fn of(ctx: &egui::Context) -> Self {
        Self::from_tokens(&crate::studio_theme::tokens(ctx))
    }
}

impl Default for StudioPalette {
    fn default() -> Self {
        Self::GRAPHITE
    }
}

/// Body text sizes from the mockup (13 px base, 12-12.5 px secondary).
pub(crate) const BODY: f32 = 13.0;
pub(crate) const SMALL: f32 = 12.0;
pub(crate) const CAPS: f32 = 10.5;

/// Uppercase with the mockup's tracking (0.13 em).
pub(crate) fn caps_job(text: &str, size: f32, color: Color32) -> LayoutJob {
    let mut job = LayoutJob::default();
    job.append(
        &text.to_uppercase(),
        0.0,
        egui::TextFormat {
            font_id: FontId::proportional(size),
            color,
            extra_letter_spacing: size * 0.13,
            ..Default::default()
        },
    );
    job
}

pub(crate) fn caps(ui: &mut Ui, text: &str, size: f32, color: Color32) -> Response {
    ui.label(caps_job(text, size, color))
}

pub(crate) fn text(ui: &mut Ui, text: &str, size: f32, color: Color32) -> Response {
    ui.label(egui::RichText::new(text).size(size).color(color))
}

/// Paint text and return its rectangle.
pub(crate) fn paint_text(
    painter: &egui::Painter,
    at: Pos2,
    align: Align2,
    text: &str,
    size: f32,
    color: Color32,
) -> Rect {
    painter.text(at, align, text, FontId::proportional(size), color)
}

/// Paint text in the strong face (the mockup's `<b>`).
pub(crate) fn paint_strong(
    painter: &egui::Painter,
    at: Pos2,
    align: Align2,
    text: &str,
    size: f32,
    color: Color32,
) -> Rect {
    let font = crate::studio_fonts::font(painter.ctx(), crate::studio_fonts::Face::Strong, size);
    painter.text(at, align, text, font, color)
}

/// A strong label in a layout.
pub(crate) fn strong(ui: &mut Ui, text: &str, size: f32, color: Color32) -> Response {
    let font = crate::studio_fonts::font(ui.ctx(), crate::studio_fonts::Face::Strong, size);
    ui.label(egui::RichText::new(text).font(font).color(color))
}

pub(crate) fn hairline(painter: &egui::Painter, a: Pos2, b: Pos2, color: Color32) {
    painter.line_segment([a, b], Stroke::new(1.0_f32, color));
}

/// A section header: tracked caption, an optional aside, a hairline under.
pub(crate) fn sect(ui: &mut Ui, pal: &StudioPalette, title: &str, aside: Option<&str>) {
    let width = ui.available_width();
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 22.0), Sense::hover());
    let painter = ui.painter();
    painter.galley(
        egui::pos2(rect.left(), rect.top() + 3.0),
        painter.layout_job(caps_job(title, CAPS, pal.ink_3)),
        pal.ink_3,
    );
    if let Some(aside) = aside {
        paint_text(
            painter,
            egui::pos2(rect.right(), rect.top() + 2.0),
            Align2::RIGHT_TOP,
            aside,
            SMALL,
            pal.ink_3,
        );
    }
    hairline(painter, rect.left_bottom(), rect.right_bottom(), pal.line);
}

/// Segmented control: hairline box, the chosen item raised and underlined.
pub(crate) fn seg(
    ui: &mut Ui,
    pal: &StudioPalette,
    items: &[&str],
    selected: Option<usize>,
) -> Option<usize> {
    let font = FontId::proportional(SMALL);
    let widths: Vec<f32> = items
        .iter()
        .map(|item| {
            ui.painter()
                .layout_no_wrap((*item).to_owned(), font.clone(), pal.ink)
                .size()
                .x
                + 20.0
        })
        .collect();
    let total: f32 = widths.iter().sum();
    let (rect, _) = ui.allocate_exact_size(egui::vec2(total, 24.0), Sense::hover());
    let mut clicked = None;
    let mut x = rect.left();
    for (i, (item, width)) in items.iter().zip(&widths).enumerate() {
        let cell = Rect::from_min_size(egui::pos2(x, rect.top()), egui::vec2(*width, 24.0));
        let response = ui.interact(cell, ui.id().with(("seg", i, *item)), Sense::click());
        let on = selected == Some(i);
        let painter = ui.painter();
        if on {
            painter.rect_filled(cell, CornerRadius::ZERO, pal.control);
            painter.rect_filled(
                Rect::from_min_max(egui::pos2(cell.left(), cell.bottom() - 1.5), cell.max),
                CornerRadius::ZERO,
                pal.accent,
            );
        }
        if i > 0 {
            hairline(painter, cell.left_top(), cell.left_bottom(), pal.line_2);
        }
        let color = if on || response.hovered() {
            pal.ink
        } else {
            pal.ink_3
        };
        paint_text(
            painter,
            cell.center(),
            Align2::CENTER_CENTER,
            item,
            SMALL,
            color,
        );
        if response.clicked() {
            clicked = Some(i);
        }
        x += width;
    }
    ui.painter().rect_stroke(
        rect,
        CornerRadius::ZERO,
        Stroke::new(1.0_f32, pal.line_2),
        StrokeKind::Inside,
    );
    clicked
}

/// What a slider did this frame.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct SliderOutput {
    /// The new value, when it changed (including a reset).
    pub value: Option<f32>,
    pub dragging: bool,
    pub released: bool,
}

/// How a slider shows its number.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Number {
    /// Two decimals, for example `0.00` or `1.00`.
    Fixed2,
    /// Whole numbers with a sign when nonzero, for example `+20`.
    Signed,
    /// Whole numbers, for example `40`.
    Whole,
}

pub(crate) fn format_number(value: f32, number: Number) -> String {
    match number {
        Number::Fixed2 => format!("{value:.2}"),
        Number::Signed if value.round() > 0.0 => format!("+{:.0}", value.round()),
        Number::Signed => format!("{:.0}", value.round()),
        Number::Whole => format!("{:.0}", value.round()),
    }
}

/// The mockup's slider: a label and an underlined value, then a hairline
/// track with a tick at the default, an accent run from the default, and a
/// thin handle. Click or drag sets, double-click resets.
#[allow(clippy::too_many_arguments)]
pub(crate) fn slider(
    ui: &mut Ui,
    pal: &StudioPalette,
    label: &str,
    value: f32,
    range: std::ops::RangeInclusive<f32>,
    default: f32,
    number: Number,
    width: f32,
) -> SliderOutput {
    let (lo, hi) = (*range.start(), *range.end());
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 42.0), Sense::hover());
    let field = Rect::from_min_size(rect.min, egui::vec2(width, 24.0));
    let track = Rect::from_min_max(
        egui::pos2(rect.left(), field.bottom()),
        egui::pos2(rect.right(), field.bottom() + 13.0),
    );
    let id = ui.id().with(("slider", label));
    let response = ui.interact(
        Rect::from_min_max(egui::pos2(track.left(), field.top()), track.max),
        id,
        Sense::click_and_drag(),
    );
    let set = (value - default).abs() > 1e-4;
    let painter = ui.painter();
    paint_text(
        painter,
        field.left_center(),
        Align2::LEFT_CENTER,
        label,
        BODY,
        pal.ink_2,
    );
    let shown = format_number(value, number);
    let number_rect = paint_text(
        painter,
        field.right_center(),
        Align2::RIGHT_CENTER,
        &shown,
        12.5,
        if set { pal.accent } else { pal.ink },
    );
    let under = (number_rect.width() + 4.0).max(46.0);
    hairline(
        painter,
        egui::pos2(field.right() - under, field.bottom() - 2.0),
        egui::pos2(field.right(), field.bottom() - 2.0),
        if set { pal.accent } else { pal.line_2 },
    );
    let x_of = |v: f32| track.left() + (v - lo) / (hi - lo).max(1e-9) * track.width();
    let mid = track.top() + 6.5;
    hairline(
        painter,
        egui::pos2(track.left(), mid),
        egui::pos2(track.right(), mid),
        pal.line_2,
    );
    let (dx, vx) = (x_of(default), x_of(value.clamp(lo, hi)));
    hairline(
        painter,
        egui::pos2(dx, track.top() + 3.0),
        egui::pos2(dx, track.top() + 10.0),
        pal.ink_3,
    );
    if set {
        painter.rect_filled(
            Rect::from_min_max(
                egui::pos2(dx.min(vx), mid - 1.0),
                egui::pos2(dx.max(vx), mid + 1.0),
            ),
            CornerRadius::ZERO,
            pal.accent,
        );
    }
    painter.rect_filled(
        Rect::from_min_max(
            egui::pos2(vx - 1.0, track.top()),
            egui::pos2(vx + 1.0, track.bottom()),
        ),
        CornerRadius::ZERO,
        pal.ink,
    );
    let mut out = SliderOutput {
        dragging: response.dragged(),
        released: response.drag_stopped(),
        ..Default::default()
    };
    if response.double_clicked() {
        out.value = Some(default);
    } else if (response.dragged() || response.clicked())
        && let Some(pointer) = response.interact_pointer_pos()
        && pointer.y >= track.top() - 4.0
    {
        let t = ((pointer.x - track.left()) / track.width().max(1.0)).clamp(0.0, 1.0);
        let next = lo + t * (hi - lo);
        let next = match number {
            Number::Fixed2 => (next * 100.0).round() / 100.0,
            _ => next.round(),
        };
        if (next - value).abs() > 1e-6 {
            out.value = Some(next);
        }
    }
    out
}

/// The control strip's compact slider (mockup `.slider` inline): a hairline
/// track, an accent run from the start, a thin handle. Click or drag sets.
pub(crate) fn inline_slider(
    ui: &mut Ui,
    pal: &StudioPalette,
    value: f32,
    range: std::ops::RangeInclusive<f32>,
    width: f32,
) -> SliderOutput {
    let (lo, hi) = (*range.start(), *range.end());
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 13.0), Sense::click_and_drag());
    let painter = ui.painter();
    let mid = rect.center().y;
    hairline(
        painter,
        egui::pos2(rect.left(), mid),
        egui::pos2(rect.right(), mid),
        pal.line_2,
    );
    let t = ((value - lo) / (hi - lo).max(1e-9)).clamp(0.0, 1.0);
    let x = rect.left() + t * rect.width();
    painter.rect_filled(
        Rect::from_min_max(egui::pos2(rect.left(), mid - 1.0), egui::pos2(x, mid + 1.0)),
        CornerRadius::ZERO,
        pal.accent,
    );
    painter.rect_filled(
        Rect::from_min_max(
            egui::pos2(x - 1.0, rect.top()),
            egui::pos2(x + 1.0, rect.bottom()),
        ),
        CornerRadius::ZERO,
        pal.ink,
    );
    let mut out = SliderOutput {
        dragging: response.dragged(),
        released: response.drag_stopped(),
        ..Default::default()
    };
    if (response.dragged() || response.clicked())
        && let Some(pointer) = response.interact_pointer_pos()
    {
        let next =
            lo + ((pointer.x - rect.left()) / rect.width().max(1.0)).clamp(0.0, 1.0) * (hi - lo);
        if (next - value).abs() > 1e-6 {
            out.value = Some(next);
        }
    }
    out
}

/// A quiet button that stays underlined in accent while on.
pub(crate) fn toggle_button(ui: &mut Ui, pal: &StudioPalette, label: &str, on: bool) -> Response {
    let galley =
        ui.painter()
            .layout_no_wrap(label.to_owned(), FontId::proportional(SMALL), pal.ink);
    let (rect, response) =
        ui.allocate_exact_size(egui::vec2(galley.size().x + 12.0, 22.0), Sense::click());
    let colour = if on || response.hovered() {
        pal.ink
    } else {
        pal.ink_2
    };
    ui.painter().galley_with_override_text_color(
        egui::pos2(rect.left() + 6.0, rect.center().y - galley.size().y * 0.5),
        galley,
        colour,
    );
    if on {
        ui.painter().rect_filled(
            Rect::from_min_max(egui::pos2(rect.left(), rect.bottom() - 1.5), rect.max),
            CornerRadius::ZERO,
            pal.accent,
        );
    }
    response
}

/// A square toggle: hairline frame and a square knob, accent when on.
pub(crate) fn toggle(ui: &mut Ui, pal: &StudioPalette, on: bool) -> Response {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(26.0, 14.0), Sense::click());
    let painter = ui.painter();
    painter.rect_stroke(
        rect,
        CornerRadius::ZERO,
        Stroke::new(1.0_f32, if on { pal.accent } else { pal.line_2 }),
        StrokeKind::Inside,
    );
    let knob = if on {
        rect.left() + 15.0
    } else {
        rect.left() + 3.0
    };
    painter.rect_filled(
        Rect::from_min_size(egui::pos2(knob, rect.top() + 3.0), egui::vec2(8.0, 8.0)),
        CornerRadius::ZERO,
        if on { pal.accent } else { pal.ink_3 },
    );
    response
}

/// A square check box with a drawn tick.
pub(crate) fn checkbox(ui: &mut Ui, pal: &StudioPalette, on: bool) -> Response {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(14.0, 14.0), Sense::click());
    paint_checkbox(ui.painter(), rect, pal, on);
    response
}

pub(crate) fn paint_checkbox(painter: &egui::Painter, rect: Rect, pal: &StudioPalette, on: bool) {
    if on {
        painter.rect_filled(rect, CornerRadius::ZERO, pal.accent);
        let s = Stroke::new(1.5_f32, pal.accent_ink);
        let p = |x: f32, y: f32| egui::pos2(rect.left() + x, rect.top() + y);
        painter.line_segment([p(3.5, 7.0), p(6.0, 9.8)], s);
        painter.line_segment([p(6.0, 9.8), p(10.8, 4.0)], s);
    } else {
        painter.rect_stroke(
            rect,
            CornerRadius::ZERO,
            Stroke::new(1.0_f32, pal.line_2),
            StrokeKind::Inside,
        );
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ButtonKind {
    Primary,
    Plain,
    Quiet,
}

pub(crate) fn button(
    ui: &mut Ui,
    pal: &StudioPalette,
    label: &str,
    kind: ButtonKind,
    size: Vec2,
    enabled: bool,
) -> Response {
    let sense = if enabled {
        Sense::click()
    } else {
        Sense::hover()
    };
    let (rect, response) = ui.allocate_exact_size(size, sense);
    let painter = ui.painter();
    let (fill, ink) = match kind {
        ButtonKind::Primary => (Some(pal.accent), pal.accent_ink),
        ButtonKind::Plain => (None, pal.ink),
        ButtonKind::Quiet => (
            None,
            if response.hovered() {
                pal.ink
            } else {
                pal.ink_2
            },
        ),
    };
    let alpha = if enabled { 1.0 } else { 0.4 };
    if let Some(fill) = fill {
        painter.rect_filled(rect, CornerRadius::ZERO, fill.gamma_multiply(alpha));
    } else if kind == ButtonKind::Plain {
        painter.rect_stroke(
            rect,
            CornerRadius::ZERO,
            Stroke::new(
                1.0_f32,
                if response.hovered() {
                    pal.ink_3
                } else {
                    pal.line_2
                },
            ),
            StrokeKind::Inside,
        );
    }
    paint_text(
        painter,
        rect.center(),
        Align2::CENTER_CENTER,
        label,
        if size.y < 24.0 { SMALL } else { 12.5 },
        ink.gamma_multiply(alpha),
    );
    response
}

/// A text link set in tracked capitals.
pub(crate) fn link(ui: &mut Ui, pal: &StudioPalette, label: &str, accent: bool) -> Response {
    let job = caps_job(label, CAPS, pal.ink_2);
    let galley = ui.painter().layout_job(job);
    let (rect, response) = ui.allocate_exact_size(galley.size(), Sense::click());
    let color = if accent {
        pal.accent
    } else if response.hovered() {
        pal.ink
    } else {
        pal.ink_2
    };
    ui.painter()
        .galley_with_override_text_color(rect.min, galley, color);
    if response.hovered() {
        hairline(
            ui.painter(),
            rect.left_bottom(),
            rect.right_bottom(),
            pal.ink_3,
        );
    }
    response
}

/// A small boxed tag; `new` tags are information blue.
pub(crate) fn tag(ui: &mut Ui, pal: &StudioPalette, label: &str, new: bool) {
    let color = if new { pal.info } else { pal.accent };
    let galley = ui.painter().layout_job(caps_job(label, 9.5, color));
    let (rect, _) = ui.allocate_exact_size(galley.size() + egui::vec2(10.0, 3.0), Sense::hover());
    ui.painter().rect_stroke(
        rect,
        CornerRadius::ZERO,
        Stroke::new(1.0_f32, color),
        StrokeKind::Inside,
    );
    ui.painter()
        .galley(rect.min + egui::vec2(5.0, 2.0), galley, color);
}

/// The drawn status marks: a lamp, a triangle, a diamond, a ring, a half.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Mark {
    Ok,
    Info,
    Warn,
    Bad,
    Idle,
    Run,
}

pub(crate) fn mark(painter: &egui::Painter, center: Pos2, kind: Mark, pal: &StudioPalette) {
    match kind {
        Mark::Ok => {
            painter.circle_filled(center, 3.5, pal.ok);
        }
        Mark::Info => {
            painter.circle_filled(center, 3.5, pal.info);
        }
        Mark::Warn => {
            painter.add(Shape::convex_polygon(
                vec![
                    center + egui::vec2(0.0, -4.0),
                    center + egui::vec2(4.0, 3.5),
                    center + egui::vec2(-4.0, 3.5),
                ],
                pal.warn,
                Stroke::NONE,
            ));
        }
        Mark::Bad => {
            painter.add(Shape::convex_polygon(
                vec![
                    center + egui::vec2(0.0, -4.2),
                    center + egui::vec2(4.2, 0.0),
                    center + egui::vec2(0.0, 4.2),
                    center + egui::vec2(-4.2, 0.0),
                ],
                pal.bad,
                Stroke::NONE,
            ));
        }
        Mark::Idle => {
            painter.circle_stroke(center, 3.0_f32, Stroke::new(1.2_f32, pal.ink_3));
        }
        Mark::Run => {
            painter.circle_stroke(center, 3.0_f32, Stroke::new(1.2_f32, pal.accent));
            painter.rect_filled(
                Rect::from_min_max(
                    center + egui::vec2(-3.5, -3.5),
                    center + egui::vec2(0.0, 3.5),
                ),
                CornerRadius::ZERO,
                pal.accent,
            );
        }
    }
}

/// A 36 px tab row: tracked captions, the chosen one underlined in accent.
pub(crate) fn tabs(
    ui: &mut Ui,
    pal: &StudioPalette,
    items: &[String],
    selected: usize,
) -> Option<usize> {
    let width = ui.available_width();
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 36.0), Sense::hover());
    hairline(
        ui.painter(),
        rect.left_bottom(),
        rect.right_bottom(),
        pal.line,
    );
    let mut x = rect.left() + 6.0;
    let mut chosen = None;
    for (i, item) in items.iter().enumerate() {
        let on = i == selected;
        let galley =
            ui.painter()
                .layout_job(caps_job(item, 11.0, if on { pal.ink } else { pal.ink_3 }));
        let cell = Rect::from_min_size(
            egui::pos2(x, rect.top()),
            egui::vec2(galley.size().x + 20.0, 36.0),
        );
        let response = ui.interact(cell, ui.id().with(("tab", i)), Sense::click());
        let color = if on || response.hovered() {
            pal.ink
        } else {
            pal.ink_3
        };
        ui.painter().galley_with_override_text_color(
            egui::pos2(cell.left() + 10.0, cell.center().y - galley.size().y * 0.5),
            galley,
            color,
        );
        if on {
            ui.painter().rect_filled(
                Rect::from_min_max(
                    egui::pos2(cell.left() + 10.0, cell.bottom() - 2.0),
                    egui::pos2(cell.right() - 10.0, cell.bottom()),
                ),
                CornerRadius::ZERO,
                pal.accent,
            );
        }
        if response.clicked() {
            chosen = Some(i);
        }
        x = cell.right();
    }
    chosen
}

/// Line icons drawn on a 16-unit grid, as in the mockup's `icons.svg`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Icon {
    Move,
    Crop,
    Picker,
    Brush,
    Heal,
    Backdrop,
    Shape,
    Ruler,
    Note,
    Eye,
    Chevron,
    Export,
}

pub(crate) fn icon(painter: &egui::Painter, rect: Rect, kind: Icon, color: Color32) {
    let s = rect.width().min(rect.height()) / 16.0;
    let o = rect.center() - egui::vec2(8.0 * s, 8.0 * s);
    let p = |x: f32, y: f32| o + egui::vec2(x * s, y * s);
    let stroke = Stroke::new(1.25_f32, color);
    let line = |points: &[(f32, f32)]| {
        painter.add(Shape::line(
            points.iter().map(|&(x, y)| p(x, y)).collect(),
            stroke,
        ));
    };
    match kind {
        Icon::Move => {
            line(&[(8.0, 2.0), (8.0, 14.0)]);
            line(&[(2.0, 8.0), (14.0, 8.0)]);
            line(&[(6.0, 4.0), (8.0, 2.0), (10.0, 4.0)]);
            line(&[(6.0, 12.0), (8.0, 14.0), (10.0, 12.0)]);
            line(&[(4.0, 6.0), (2.0, 8.0), (4.0, 10.0)]);
            line(&[(12.0, 6.0), (14.0, 8.0), (12.0, 10.0)]);
        }
        Icon::Crop => {
            line(&[(4.0, 1.5), (4.0, 12.0), (14.5, 12.0)]);
            line(&[(1.5, 4.0), (12.0, 4.0), (12.0, 14.5)]);
        }
        Icon::Picker => {
            line(&[(9.0, 4.0), (12.0, 7.0)]);
            line(&[(10.5, 5.5), (4.5, 11.5), (3.0, 13.0)]);
            line(&[
                (8.5, 3.5),
                (10.1, 1.9),
                (14.1, 5.9),
                (12.5, 7.5),
                (8.5, 3.5),
            ]);
        }
        Icon::Brush => {
            line(&[
                (9.5, 2.5),
                (13.5, 6.5),
                (7.0, 13.0),
                (3.0, 13.0),
                (3.0, 9.0),
                (9.5, 2.5),
            ]);
            line(&[(8.0, 4.0), (12.0, 8.0)]);
            line(&[(2.0, 14.5), (14.0, 14.5)]);
        }
        Icon::Heal => {
            line(&[(3.3, 8.7), (8.7, 3.3), (12.7, 7.3), (7.3, 12.7), (3.3, 8.7)]);
            line(&[(6.5, 6.5), (9.5, 9.5)]);
        }
        Icon::Backdrop => {
            line(&[
                (2.0, 2.0),
                (14.0, 2.0),
                (14.0, 14.0),
                (2.0, 14.0),
                (2.0, 2.0),
            ]);
            line(&[
                (5.0, 11.5),
                (6.5, 8.0),
                (8.0, 7.0),
                (9.5, 8.0),
                (11.0, 11.5),
            ]);
        }
        Icon::Shape => {
            painter.circle_stroke(p(6.0, 6.0), 3.5 * s, stroke);
            line(&[
                (7.5, 7.5),
                (13.5, 7.5),
                (13.5, 13.5),
                (7.5, 13.5),
                (7.5, 7.5),
            ]);
        }
        Icon::Ruler => {
            line(&[
                (2.0, 11.0),
                (11.0, 2.0),
                (14.0, 5.0),
                (5.0, 14.0),
                (2.0, 11.0),
            ]);
            line(&[(5.0, 8.0), (6.5, 9.5)]);
            line(&[(7.0, 6.0), (8.5, 7.5)]);
            line(&[(9.0, 4.0), (10.5, 5.5)]);
        }
        Icon::Note => {
            line(&[
                (3.0, 2.5),
                (13.0, 2.5),
                (13.0, 10.5),
                (10.0, 13.5),
                (3.0, 13.5),
                (3.0, 2.5),
            ]);
            line(&[(10.0, 13.5), (10.0, 10.5), (13.0, 10.5)]);
        }
        Icon::Eye => {
            line(&[
                (1.5, 8.0),
                (4.5, 4.8),
                (8.0, 3.5),
                (11.5, 4.8),
                (14.5, 8.0),
                (11.5, 11.2),
                (8.0, 12.5),
                (4.5, 11.2),
                (1.5, 8.0),
            ]);
            painter.circle_stroke(p(8.0, 8.0), 2.0 * s, stroke);
        }
        Icon::Chevron => line(&[(6.0, 4.0), (10.0, 8.0), (6.0, 12.0)]),
        Icon::Export => {
            line(&[(8.0, 10.0), (8.0, 2.0)]);
            line(&[(5.0, 5.0), (8.0, 2.0), (11.0, 5.0)]);
            line(&[(3.0, 9.0), (3.0, 13.0), (13.0, 13.0), (13.0, 9.0)]);
        }
    }
}

/// A dashed polyline (the paint outline of a depth repair).
pub(crate) fn dashed(
    painter: &egui::Painter,
    points: &[Pos2],
    stroke: Stroke,
    dash: f32,
    gap: f32,
) {
    painter.extend(Shape::dashed_line(points, stroke, dash, gap));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn numbers_follow_the_mockup() {
        assert_eq!(format_number(0.0, Number::Fixed2), "0.00");
        assert_eq!(format_number(1.0, Number::Fixed2), "1.00");
        assert_eq!(format_number(20.0, Number::Signed), "+20");
        assert_eq!(format_number(-25.4, Number::Signed), "-25");
        assert_eq!(format_number(0.2, Number::Signed), "0");
        assert_eq!(format_number(90.0, Number::Whole), "90");
    }

    #[test]
    fn caps_are_tracked_uppercase() {
        let job = caps_job("Depth brush", CAPS, Color32::WHITE);
        assert_eq!(job.text, "DEPTH BRUSH");
        assert!((job.sections[0].format.extra_letter_spacing - CAPS * 0.13).abs() < 1e-6);
    }
}
