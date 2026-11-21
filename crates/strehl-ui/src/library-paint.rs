//! Drawing for the Library and Subject screens in the Studio 2 look: square
//! corners, hairlines, tracked capitals and drawn status marks. Colours come
//! from a `LibraryPalette`, so the shell's theme tokens replace the defaults
//! with one conversion.
#![allow(
    dead_code,
    reason = "the Library and Subject screens are composed into the shell in P4 stage 2"
)]
use crate::workspace_history::StepState;
use eframe::egui::{
    self, Align2, Color32, CornerRadius, FontId, Painter, Pos2, Rect, Response, Sense, Stroke,
    StrokeKind, Ui, Vec2,
    text::{LayoutJob, TextFormat, TextWrapping},
};
use std::sync::Arc;

/// The screens' colours (mockup `base.css`, Graphite). The shell converts its
/// theme tokens into this; nothing here reads the global theme.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct LibraryPalette {
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
    pub ok: Color32,
    pub warn: Color32,
    pub bad: Color32,
    pub info: Color32,
    /// The dark plate under a badge on a picture.
    pub plate: Color32,
    /// Capitals on the plate: light in every theme.
    pub plate_ink: Color32,
}
impl LibraryPalette {
    pub(crate) const fn graphite() -> Self {
        Self {
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
            ok: Color32::from_rgb(0xa9, 0xc7, 0x79),
            warn: Color32::from_rgb(0xf0, 0x8a, 0x4b),
            bad: Color32::from_rgb(0xe5, 0x60, 0x4c),
            info: Color32::from_rgb(0x8a, 0xb4, 0xe8),
            plate: Color32::from_rgba_premultiplied(7, 7, 7, 209),
            plate_ink: Color32::from_rgb(0xe9, 0xe6, 0xde),
        }
    }
}
impl LibraryPalette {
    /// The palette for the theme in effect (Graphite, Instrument, Lightbox).
    /// The picture plate stays a dark veil in every theme: it sits on photographs.
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
            ok: t.ok,
            warn: t.warn,
            bad: t.bad,
            info: t.info,
            plate: Self::graphite().plate,
            plate_ink: Self::graphite().plate_ink,
        }
    }
}
impl Default for LibraryPalette {
    fn default() -> Self {
        Self::graphite()
    }
}

/// The drawn status marks: a lamp, a triangle, a diamond, a ring, a half.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Mark {
    Ok,
    Warn,
    Bad,
    Idle,
    Run,
    Info,
    Plain,
}
impl Mark {
    pub(crate) fn of(step: StepState) -> Self {
        match step {
            StepState::Done => Self::Ok,
            StepState::NeedsLook => Self::Warn,
            StepState::Running => Self::Run,
            StepState::NotYet => Self::Idle,
        }
    }
}
pub(crate) fn mark(painter: &Painter, center: Pos2, kind: Mark, palette: &LibraryPalette) {
    let r = 3.5;
    match kind {
        Mark::Ok | Mark::Info | Mark::Plain => {
            let fill = match kind {
                Mark::Ok => palette.ok,
                Mark::Info => palette.info,
                _ => palette.ink_3,
            };
            painter.circle_filled(center, r, fill);
        }
        Mark::Warn => {
            painter.add(egui::Shape::convex_polygon(
                vec![
                    center + Vec2::new(0.0, -3.8),
                    center + Vec2::new(4.2, 3.4),
                    center + Vec2::new(-4.2, 3.4),
                ],
                palette.warn,
                Stroke::NONE,
            ));
        }
        Mark::Bad => {
            painter.add(egui::Shape::convex_polygon(
                vec![
                    center + Vec2::new(0.0, -4.2),
                    center + Vec2::new(4.2, 0.0),
                    center + Vec2::new(0.0, 4.2),
                    center + Vec2::new(-4.2, 0.0),
                ],
                palette.bad,
                Stroke::NONE,
            ));
        }
        Mark::Idle => {
            painter.circle_stroke(center, r - 0.6, Stroke::new(1.2_f32, palette.ink_3));
        }
        Mark::Run => {
            let points: Vec<Pos2> = (0..=12)
                .map(|i| {
                    let a = std::f32::consts::FRAC_PI_2 + std::f32::consts::PI * i as f32 / 12.0;
                    center + Vec2::new(a.cos(), a.sin()) * r
                })
                .collect();
            painter.add(egui::Shape::convex_polygon(
                points,
                palette.accent,
                Stroke::NONE,
            ));
            painter.circle_stroke(center, r - 0.6, Stroke::new(1.2_f32, palette.accent));
        }
    }
}

pub(crate) fn font(size: f32) -> FontId {
    FontId::proportional(size)
}
/// A single-line galley, cut with an ellipsis at `width` when given.
pub(crate) fn galley(
    painter: &Painter,
    text: &str,
    size: f32,
    color: Color32,
    width: Option<f32>,
) -> Arc<egui::Galley> {
    let mut job = LayoutJob::simple_singleline(text.to_owned(), font(size), color);
    if let Some(width) = width {
        job.wrap = TextWrapping::truncate_at_width(width.max(1.0));
    }
    painter.layout_job(job)
}
/// Draw `text` with its `align` point at `at`; returns its rectangle.
pub(crate) fn text(
    painter: &Painter,
    at: Pos2,
    align: Align2,
    text: &str,
    size: f32,
    color: Color32,
    width: Option<f32>,
) -> Rect {
    let galley = galley(painter, text, size, color, width);
    let rect = align.anchor_size(at, galley.size());
    painter.galley(rect.min, galley, color);
    rect
}
/// Tracked capitals (`letter-spacing: .13em`), the label style of the screens.
pub(crate) fn caps_galley(
    painter: &Painter,
    label: &str,
    size: f32,
    color: Color32,
) -> Arc<egui::Galley> {
    let mut job = LayoutJob::default();
    job.append(
        &label.to_uppercase(),
        0.0,
        TextFormat {
            font_id: font(size),
            color,
            extra_letter_spacing: size * 0.13,
            ..Default::default()
        },
    );
    painter.layout_job(job)
}
pub(crate) fn caps(
    painter: &Painter,
    at: Pos2,
    align: Align2,
    label: &str,
    size: f32,
    color: Color32,
) -> Rect {
    let galley = caps_galley(painter, label, size, color);
    let rect = align.anchor_size(at, galley.size());
    painter.galley(rect.min, galley, color);
    rect
}
/// A wrapped paragraph of at most `rows` lines; returns its height.
pub(crate) fn paragraph(
    painter: &Painter,
    at: Pos2,
    body: &str,
    size: f32,
    color: Color32,
    width: f32,
    rows: usize,
) -> f32 {
    let mut job = LayoutJob::simple(body.to_owned(), font(size), color, width.max(1.0));
    job.wrap.max_rows = rows;
    let galley = painter.layout_job(job);
    let height = galley.size().y;
    painter.galley(at, galley, color);
    height
}

pub(crate) fn hline(painter: &Painter, x: std::ops::RangeInclusive<f32>, y: f32, color: Color32) {
    let y = y.round() + 0.5;
    painter.line_segment(
        [Pos2::new(*x.start(), y), Pos2::new(*x.end(), y)],
        Stroke::new(1.0_f32, color),
    );
}
pub(crate) fn vline(painter: &Painter, x: f32, y: std::ops::RangeInclusive<f32>, color: Color32) {
    let x = x.round() + 0.5;
    painter.line_segment(
        [Pos2::new(x, *y.start()), Pos2::new(x, *y.end())],
        Stroke::new(1.0_f32, color),
    );
}
pub(crate) fn outline(painter: &Painter, rect: Rect, width: f32, color: Color32) {
    painter.rect_stroke(
        rect,
        CornerRadius::ZERO,
        Stroke::new(width, color),
        StrokeKind::Outside,
    );
}
pub(crate) fn inset(painter: &Painter, rect: Rect, color: Color32) {
    painter.rect_stroke(
        rect,
        CornerRadius::ZERO,
        Stroke::new(1.0_f32, color),
        StrokeKind::Inside,
    );
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ButtonStyle {
    /// Accent fill.
    Primary,
    /// Hairline outline.
    Outline,
    /// Text only.
    Quiet,
}
/// A square button with an optional leading icon; under 25 px tall is small.
pub(crate) fn button(
    ui: &mut Ui,
    rect: Rect,
    id: impl std::hash::Hash,
    label: &str,
    icon: Option<crate::workspace_icons::Icon>,
    style: ButtonStyle,
    palette: &LibraryPalette,
) -> Response {
    let response = ui.interact(rect, ui.id().with(("library-button", id)), Sense::click());
    let painter = ui.painter();
    let hovered = response.hovered();
    let (fill, ink) = match style {
        ButtonStyle::Primary => (Some(palette.accent), palette.accent_ink),
        ButtonStyle::Outline => (None, palette.ink),
        ButtonStyle::Quiet => (None, if hovered { palette.ink } else { palette.ink_2 }),
    };
    if let Some(fill) = fill {
        painter.rect_filled(rect, CornerRadius::ZERO, fill);
    } else if style == ButtonStyle::Outline {
        inset(
            painter,
            rect,
            if hovered {
                palette.ink_3
            } else {
                palette.line_2
            },
        );
    }
    let size = if rect.height() < 25.0 { 12.0 } else { 12.5 };
    let label_galley = galley(painter, label, size, ink, None);
    let icon_width = if icon.is_some() { 22.0 } else { 0.0 };
    let total = label_galley.size().x + icon_width;
    let left = rect.center().x - total * 0.5;
    if let Some(icon) = icon {
        crate::workspace_icons::paint(
            painter,
            Pos2::new(left + 7.5, rect.center().y),
            14.0,
            icon,
            ink,
        );
    }
    painter.galley(
        Pos2::new(
            left + icon_width,
            rect.center().y - label_galley.size().y * 0.5,
        ),
        label_galley,
        ink,
    );
    response
}
/// The width a `button` needs for its label.
pub(crate) fn button_width(painter: &Painter, label: &str, icon: bool, small: bool) -> f32 {
    let size = if small { 12.0 } else { 12.5 };
    galley(painter, label, size, Color32::WHITE, None).size().x
        + if icon { 22.0 } else { 0.0 }
        + if small { 16.0 } else { 24.0 }
}
/// A segmented control 24 px tall; returns its rectangle and the index clicked.
pub(crate) fn segments(
    ui: &mut Ui,
    origin: Pos2,
    id: &str,
    labels: &[&str],
    selected: usize,
    palette: &LibraryPalette,
) -> (Rect, Option<usize>) {
    let painter = ui.painter().clone();
    let mut x = origin.x;
    let mut clicked = None;
    let mut cells = Vec::with_capacity(labels.len());
    for label in labels {
        let width = galley(&painter, label, 12.0, Color32::WHITE, None).size().x + 20.0;
        cells.push(Rect::from_min_size(
            Pos2::new(x, origin.y),
            Vec2::new(width, 24.0),
        ));
        x += width;
    }
    let outer = Rect::from_min_max(origin, Pos2::new(x, origin.y + 24.0));
    for (index, (cell, label)) in cells.iter().zip(labels).enumerate() {
        let response = ui.interact(*cell, ui.id().with((id, index)), Sense::click());
        let on = index == selected;
        if on {
            painter.rect_filled(*cell, CornerRadius::ZERO, palette.control);
            painter.rect_filled(
                Rect::from_min_max(Pos2::new(cell.left(), cell.bottom() - 1.5), cell.max),
                CornerRadius::ZERO,
                palette.accent,
            );
        }
        if index > 0 {
            vline(
                &painter,
                cell.left(),
                cell.top()..=cell.bottom(),
                palette.line_2,
            );
        }
        let ink = if on || response.hovered() {
            palette.ink
        } else {
            palette.ink_3
        };
        text(
            &painter,
            cell.center(),
            Align2::CENTER_CENTER,
            label,
            12.0,
            ink,
            None,
        );
        if response.clicked() {
            clicked = Some(index);
        }
    }
    inset(&painter, outer, palette.line_2);
    (outer, clicked)
}

/// A square switch (`.toggle`), 26 x 14; returns its response.
pub(crate) fn toggle(
    ui: &mut Ui,
    at: Pos2,
    id: impl std::hash::Hash,
    on: bool,
    palette: &LibraryPalette,
) -> Response {
    let rect = Rect::from_min_size(at, Vec2::new(26.0, 14.0));
    let response = ui.interact(rect, ui.id().with(("library-toggle", id)), Sense::click());
    let painter = ui.painter();
    inset(
        painter,
        rect,
        if on { palette.accent } else { palette.line_2 },
    );
    let knob = Rect::from_min_size(
        Pos2::new(
            if on {
                rect.left() + 15.0
            } else {
                rect.left() + 3.0
            },
            rect.top() + 3.0,
        ),
        Vec2::splat(8.0),
    );
    painter.rect_filled(
        knob,
        CornerRadius::ZERO,
        if on { palette.accent } else { palette.ink_3 },
    );
    response
}

/// The four lifecycle bars (`.life4 i`); returns their width.
pub(crate) fn life_bars(painter: &Painter, at: Pos2, colors: [Color32; 4]) -> f32 {
    for (index, color) in colors.into_iter().enumerate() {
        let x = at.x + index as f32 * 17.0;
        painter.rect_filled(
            Rect::from_min_size(Pos2::new(x, at.y), Vec2::new(14.0, 3.0)),
            CornerRadius::ZERO,
            color,
        );
    }
    4.0 * 17.0 - 3.0
}
/// An outlined tag in tracked capitals (`.tag`).
pub(crate) fn tag(painter: &Painter, left_center: Pos2, label: &str, color: Color32) -> Rect {
    let galley = caps_galley(painter, label, 9.5, color);
    let rect = Rect::from_min_size(
        Pos2::new(left_center.x, left_center.y - galley.size().y * 0.5 - 2.0),
        galley.size() + Vec2::new(10.0, 3.0),
    );
    inset(painter, rect, color);
    painter.galley(rect.min + Vec2::new(5.0, 2.0), galley, color);
    rect
}
/// A badge on a picture's lower left (`.badge`): plate, optional mark, capitals.
pub(crate) fn badge(
    painter: &Painter,
    bottom_left: Pos2,
    mark_kind: Option<Mark>,
    label: &str,
    accent: bool,
    palette: &LibraryPalette,
) -> Rect {
    let ink = if accent {
        palette.accent_ink
    } else {
        palette.plate_ink
    };
    let galley = caps_galley(painter, label, 9.5, ink);
    let mark_width = if mark_kind.is_some() { 14.0 } else { 0.0 };
    let size = Vec2::new(galley.size().x + 16.0 + mark_width, galley.size().y + 5.0);
    let rect = Rect::from_min_size(bottom_left - Vec2::new(0.0, size.y), size);
    painter.rect_filled(
        rect,
        CornerRadius::ZERO,
        if accent {
            palette.accent
        } else {
            palette.plate
        },
    );
    if let Some(kind) = mark_kind {
        mark(
            painter,
            Pos2::new(rect.left() + 11.0, rect.center().y),
            kind,
            palette,
        );
    }
    painter.galley(
        Pos2::new(rect.left() + 8.0 + mark_width, rect.top() + 3.0),
        galley,
        ink,
    );
    rect
}

/// Small drawn glyphs the shared icon set lacks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Glyph {
    Search,
    Disk,
    Grid,
    List,
    Note,
    Arrow,
    /// Quiet mode: a crescent.
    Moon,
}
pub(crate) fn glyph(painter: &Painter, center: Pos2, kind: Glyph, color: Color32) {
    let stroke = Stroke::new(1.25_f32, color);
    let p = |x: f32, y: f32| center + Vec2::new(x, y);
    match kind {
        Glyph::Search => {
            painter.circle_stroke(p(-1.5, -1.5), 4.5, stroke);
            painter.line_segment([p(1.8, 1.8), p(5.5, 5.5)], stroke);
        }
        Glyph::Disk => {
            let rect = Rect::from_center_size(center, Vec2::new(13.0, 9.0));
            painter.rect_stroke(rect, CornerRadius::ZERO, stroke, StrokeKind::Inside);
            painter.line_segment([p(-6.0, 0.0), p(6.0, 0.0)], stroke);
            painter.circle_filled(p(3.5, 2.3), 0.9, color);
        }
        Glyph::Grid => {
            for (x, y) in [(-3.5, -3.5), (3.5, -3.5), (-3.5, 3.5), (3.5, 3.5)] {
                painter.rect_stroke(
                    Rect::from_center_size(p(x, y), Vec2::splat(5.0)),
                    CornerRadius::ZERO,
                    stroke,
                    StrokeKind::Inside,
                );
            }
        }
        Glyph::List => {
            for y in [-4.0, 0.0, 4.0] {
                painter.line_segment([p(-6.0, y), p(6.0, y)], stroke);
            }
        }
        Glyph::Note => {
            painter.rect_stroke(
                Rect::from_center_size(center, Vec2::new(10.0, 12.0)),
                CornerRadius::ZERO,
                stroke,
                StrokeKind::Inside,
            );
            painter.line_segment([p(-2.5, -1.5), p(2.5, -1.5)], stroke);
            painter.line_segment([p(-2.5, 1.5), p(2.5, 1.5)], stroke);
        }
        Glyph::Moon => {
            // Two arcs: the outer disc's edge and the bite taken from it.
            let arc = |cx: f32, r: f32, from: f32, to: f32| -> Vec<Pos2> {
                (0..=16)
                    .map(|i| {
                        let a = from + (to - from) * i as f32 / 16.0;
                        p(cx + r * a.cos(), r * a.sin())
                    })
                    .collect()
            };
            use std::f32::consts::PI;
            let mut outline = arc(0.0, 6.0, 0.35 * PI, 1.65 * PI);
            outline.extend(arc(2.6, 4.6, 1.45 * PI, 0.55 * PI));
            painter.add(egui::Shape::closed_line(outline, stroke));
        }
        Glyph::Arrow => {
            let thin = Stroke::new(1.0_f32, color);
            painter.line_segment([p(-18.0, 0.0), p(16.0, 0.0)], thin);
            painter.line_segment([p(8.0, -7.0), p(16.0, 0.0)], thin);
            painter.line_segment([p(8.0, 7.0), p(16.0, 0.0)], thin);
        }
    }
}

/// Sizes as the screens print them: "371 GB", "61.4 GB", "1.21 TB".
pub(crate) fn bytes(bytes: u64) -> String {
    let b = bytes as f64;
    if b >= 1.0e12 {
        format!("{:.2} TB", b / 1.0e12)
    } else if b >= 1.0e11 {
        format!("{:.0} GB", b / 1.0e9)
    } else if b >= 1.0e9 {
        format!("{:.1} GB", b / 1.0e9)
    } else if b >= 1.0e6 {
        format!("{:.0} MB", b / 1.0e6)
    } else if bytes > 0 {
        format!("{:.0} KB", (b / 1.0e3).max(1.0))
    } else {
        "0 B".into()
    }
}
/// "today", "12 Nov", or "12 Nov 2025" in local time; empty for no date.
pub(crate) fn day(unix: u64, now: u64) -> String {
    use chrono::{Datelike, Local, TimeZone};
    if unix == 0 {
        return String::new();
    }
    let (Some(at), Some(today)) = (
        Local.timestamp_opt(unix as i64, 0).single(),
        Local.timestamp_opt(now as i64, 0).single(),
    ) else {
        return String::new();
    };
    if at.date_naive() == today.date_naive() {
        "today".into()
    } else if at.year() == today.year() {
        at.format("%-d %b").to_string()
    } else {
        at.format("%-d %b %Y").to_string()
    }
}
/// "Today 21:38" or "9 Nov 21:12" for journal lines.
pub(crate) fn moment(unix: u64, now: u64) -> String {
    use chrono::{Local, TimeZone};
    let time = Local
        .timestamp_opt(unix as i64, 0)
        .single()
        .map(|at| at.format("%H:%M").to_string())
        .unwrap_or_default();
    let day = day(unix, now);
    let day = if day == "today" { "Today".into() } else { day };
    format!("{day} {time}").trim().to_owned()
}
pub(crate) fn plural(count: usize, one: &str, many: &str) -> String {
    format!("{count} {}", if count == 1 { one } else { many })
}
