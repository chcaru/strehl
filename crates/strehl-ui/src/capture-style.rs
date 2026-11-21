//! The Capture station's look (Studio 2): square corners, hairlines, tracked
//! capitals and drawn status marks, in one small palette.
//!
//! The screens take a [`CapturePalette`] rather than reading theme constants,
//! so wiring the shell's tokens (`studio-theme.rs`, P1) is one conversion.
//! Its default is the graphite theme of the locked mockups (`base.css`).
use eframe::egui::{
    self, Align2, Color32, FontFamily, FontId, Painter, Pos2, Rect, Response, Sense, Stroke,
    StrokeKind, Ui, Vec2, text::LayoutJob,
};

/// The colours the Capture screens draw with.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct CapturePalette {
    pub bg: Color32,
    pub panel: Color32,
    pub raised: Color32,
    pub control: Color32,
    pub line: Color32,
    pub line2: Color32,
    pub ink: Color32,
    pub ink2: Color32,
    pub ink3: Color32,
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

const fn hex(rgb: u32) -> Color32 {
    Color32::from_rgb((rgb >> 16) as u8, (rgb >> 8) as u8, rgb as u8)
}

impl Default for CapturePalette {
    /// Graphite, the default theme (D2).
    fn default() -> Self {
        Self {
            bg: hex(0x0b0b0c),
            panel: hex(0x111112),
            raised: hex(0x171718),
            control: hex(0x1e1e20),
            line: hex(0x232326),
            line2: hex(0x37373c),
            ink: hex(0xe9e6de),
            ink2: hex(0xa19f98),
            ink3: hex(0x807e77),
            accent: hex(0xe6b450),
            accent_ink: hex(0x171204),
            accent_soft: Color32::from_rgba_unmultiplied(230, 180, 80, 31),
            ok: hex(0xa9c779),
            warn: hex(0xf08a4b),
            bad: hex(0xe5604c),
            info: hex(0x8ab4e8),
            plane: hex(0x55d6c4),
            surround: hex(0x0e0e0f),
        }
    }
}

/// A drawn status mark: a lamp (ok, info, accent), a triangle (warn), a
/// diamond (bad), a ring (idle) or a half lamp (running).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[allow(dead_code)]
pub(crate) enum Mark {
    Ok,
    Info,
    Accent,
    Warn,
    Bad,
    Idle,
    Run,
    Neutral,
}

impl CapturePalette {
    pub fn mark_color(&self, mark: Mark) -> Color32 {
        match mark {
            Mark::Ok => self.ok,
            Mark::Info => self.info,
            Mark::Accent | Mark::Run => self.accent,
            Mark::Warn => self.warn,
            Mark::Bad => self.bad,
            Mark::Idle | Mark::Neutral => self.ink3,
        }
    }
}

/// Draws `mark` centred on `center`, `size` points across (7 in the mockups).
pub(crate) fn mark(
    painter: &Painter,
    center: Pos2,
    mark: Mark,
    size: f32,
    palette: &CapturePalette,
) {
    let color = palette.mark_color(mark);
    let r = size / 2.0;
    match mark {
        Mark::Ok | Mark::Info | Mark::Accent | Mark::Neutral => {
            painter.circle_filled(center, r, color);
        }
        Mark::Warn => {
            let h = size * 0.9;
            painter.add(egui::Shape::convex_polygon(
                vec![
                    center + egui::vec2(0.0, -h / 2.0),
                    center + egui::vec2(r + 0.5, h / 2.0),
                    center + egui::vec2(-r - 0.5, h / 2.0),
                ],
                color,
                Stroke::NONE,
            ));
        }
        Mark::Bad => {
            let d = r * 0.95;
            painter.add(egui::Shape::convex_polygon(
                vec![
                    center + egui::vec2(0.0, -d),
                    center + egui::vec2(d, 0.0),
                    center + egui::vec2(0.0, d),
                    center + egui::vec2(-d, 0.0),
                ],
                color,
                Stroke::NONE,
            ));
        }
        Mark::Idle => {
            painter.circle_stroke(center, r - 0.6, Stroke::new(1.2_f32, color));
        }
        Mark::Run => {
            painter.circle_stroke(center, r - 0.6, Stroke::new(1.2_f32, color));
            let mut points = vec![center];
            for i in 0..=12 {
                let a = std::f32::consts::FRAC_PI_2 + std::f32::consts::PI * i as f32 / 12.0;
                points.push(center + egui::vec2(a.cos(), -a.sin()) * r);
            }
            painter.add(egui::Shape::convex_polygon(points, color, Stroke::NONE));
        }
    }
}

/// A one-section layout in the UI face, with tracking.
pub(crate) fn job(text: &str, size: f32, color: Color32, tracking: f32) -> LayoutJob {
    let mut job = LayoutJob::single_section(
        text.to_owned(),
        egui::TextFormat {
            font_id: FontId::new(size, FontFamily::Proportional),
            color,
            extra_letter_spacing: tracking,
            ..Default::default()
        },
    );
    job.wrap.max_width = f32::INFINITY;
    job
}

/// Tracked capitals, the mockups' `.cap` (10.5 px, 0.13 em).
pub(crate) fn caps_job(text: &str, size: f32, color: Color32) -> LayoutJob {
    job(&text.to_uppercase(), size, color, size * 0.13)
}

/// Paints `layout` with its anchor at `pos`; returns its rectangle.
pub(crate) fn paint_job(painter: &Painter, pos: Pos2, anchor: Align2, layout: LayoutJob) -> Rect {
    let galley = painter.layout_job(layout);
    let rect = anchor.anchor_size(pos, galley.size());
    let color = galley
        .job
        .sections
        .first()
        .map_or(Color32::WHITE, |s| s.format.color);
    painter.galley(rect.min, galley, color);
    rect
}

/// A tracked-capitals caption as a widget.
pub(crate) fn caps(ui: &mut Ui, text: &str, palette: &CapturePalette) -> Response {
    ui.label(caps_job(text, 10.5, palette.ink3))
}

/// Plain text of a size and colour as a widget.
pub(crate) fn text(ui: &mut Ui, text: &str, size: f32, color: Color32) -> Response {
    ui.label(job(text, size, color, 0.0))
}

/// A hairline between two points, one physical pixel wide.
pub(crate) fn hairline(painter: &Painter, a: Pos2, b: Pos2, color: Color32) {
    crate::theme::rule(painter, a, b, color);
}

/// How a button looks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ButtonKind {
    /// A hairline box.
    Plain,
    /// Filled with the accent (Start stack).
    Primary,
    /// Red text in a hairline box (Stop…).
    Danger,
    /// No box; the text only.
    Quiet,
    /// Quiet, marked on with an accent underline (Peaking, Fit).
    On,
}

/// A square button of `size`, drawn as the mockups' `.btn`.
pub(crate) fn button_sized(
    ui: &mut Ui,
    label: &str,
    kind: ButtonKind,
    size: Vec2,
    enabled: bool,
    palette: &CapturePalette,
) -> Response {
    let sense = if enabled {
        Sense::click()
    } else {
        Sense::hover()
    };
    let (rect, response) = ui.allocate_exact_size(size, sense);
    if ui.is_rect_visible(rect) {
        let p = ui.painter();
        let hovered = enabled && response.hovered();
        let alpha = if enabled { 1.0 } else { 0.4 };
        let (fill, ink, stroke) = match kind {
            ButtonKind::Primary => (Some(palette.accent), palette.accent_ink, None),
            ButtonKind::Plain => (
                None,
                palette.ink,
                Some(if hovered { palette.ink3 } else { palette.line2 }),
            ),
            ButtonKind::Danger => (
                None,
                palette.bad,
                Some(if hovered { palette.ink3 } else { palette.line2 }),
            ),
            ButtonKind::Quiet => (None, if hovered { palette.ink } else { palette.ink2 }, None),
            ButtonKind::On => (None, palette.ink, None),
        };
        if let Some(fill) = fill {
            p.rect_filled(rect, 1.0, fill.gamma_multiply(alpha));
        }
        if let Some(stroke) = stroke {
            p.rect_stroke(
                rect,
                1.0,
                Stroke::new(1.0_f32, stroke.gamma_multiply(alpha)),
                StrokeKind::Inside,
            );
        }
        if kind == ButtonKind::On {
            p.rect_filled(
                Rect::from_min_max(
                    egui::pos2(rect.left(), rect.bottom() - 1.5),
                    rect.right_bottom(),
                ),
                0.0,
                palette.accent,
            );
        }
        let size_pt = if size.y >= 34.0 {
            13.5
        } else if size.y <= 22.0 {
            12.0
        } else {
            12.5
        };
        let weight = if kind == ButtonKind::Primary {
            0.2
        } else {
            0.0
        };
        paint_job(
            p,
            rect.center(),
            Align2::CENTER_CENTER,
            job(label, size_pt, ink.gamma_multiply(alpha), weight),
        );
    }
    if enabled {
        response.on_hover_cursor(egui::CursorIcon::PointingHand)
    } else {
        response
    }
}

/// A button sized to its label.
pub(crate) fn button(
    ui: &mut Ui,
    label: &str,
    kind: ButtonKind,
    height: f32,
    enabled: bool,
    palette: &CapturePalette,
) -> Response {
    let size_pt = if height <= 22.0 { 12.0 } else { 12.5 };
    let galley = ui
        .painter()
        .layout_job(job(label, size_pt, palette.ink, 0.0));
    let pad = if height <= 22.0 { 16.0 } else { 24.0 };
    let width = galley.size().x + if kind == ButtonKind::Quiet { 12.0 } else { pad };
    button_sized(ui, label, kind, egui::vec2(width, height), enabled, palette)
}

/// A tracked-capitals link (`.link`).
pub(crate) fn link(ui: &mut Ui, label: &str, enabled: bool, palette: &CapturePalette) -> Response {
    let layout = caps_job(label, 10.5, palette.ink2);
    let galley = ui.painter().layout_job(layout);
    let sense = if enabled {
        Sense::click()
    } else {
        Sense::hover()
    };
    let (rect, response) = ui.allocate_exact_size(galley.size(), sense);
    let color = if !enabled {
        palette.ink3.gamma_multiply(0.6)
    } else if response.hovered() {
        palette.ink
    } else {
        palette.ink2
    };
    ui.painter().galley(rect.min, galley, color);
    if enabled && response.hovered() {
        ui.painter().line_segment(
            [rect.left_bottom(), rect.right_bottom()],
            Stroke::new(1.0_f32, palette.ink3),
        );
    }
    response
}

/// The square on/off switch (`.toggle`, 26 x 14).
pub(crate) fn toggle(ui: &mut Ui, on: bool, enabled: bool, palette: &CapturePalette) -> Response {
    let sense = if enabled {
        Sense::click()
    } else {
        Sense::hover()
    };
    let (rect, response) = ui.allocate_exact_size(egui::vec2(26.0, 14.0), sense);
    let alpha = if enabled { 1.0 } else { 0.45 };
    let p = ui.painter();
    p.rect_stroke(
        rect,
        0.0,
        Stroke::new(
            1.0_f32,
            if on { palette.accent } else { palette.line2 }.gamma_multiply(alpha),
        ),
        StrokeKind::Inside,
    );
    let knob = Rect::from_min_size(
        rect.min + egui::vec2(if on { 15.0 } else { 3.0 }, 3.0),
        egui::vec2(8.0, 8.0),
    );
    p.rect_filled(
        knob,
        0.0,
        if on { palette.accent } else { palette.ink3 }.gamma_multiply(alpha),
    );
    response
}

/// A toggle with its label; clicking either flips it. Returns whether it was
/// clicked.
pub(crate) fn option(
    ui: &mut Ui,
    on: bool,
    label: &str,
    note: Option<&str>,
    enabled: bool,
    palette: &CapturePalette,
) -> bool {
    ui.horizontal(|ui| {
        ui.spacing_mut().item_spacing.x = 10.0;
        ui.set_min_height(26.0);
        let mut clicked = toggle(ui, on, enabled, palette).clicked();
        let mut job = job(label, 13.0, palette.ink, 0.0);
        if let Some(note) = note {
            job.append(
                &format!(" {note}"),
                0.0,
                egui::TextFormat {
                    font_id: FontId::new(13.0, FontFamily::Proportional),
                    color: palette.ink3,
                    ..Default::default()
                },
            );
        }
        job.wrap.max_width = ui.available_width();
        let sense = if enabled {
            Sense::click()
        } else {
            Sense::hover()
        };
        clicked |= ui
            .add(
                egui::Label::new(job)
                    .sense(sense)
                    .wrap_mode(egui::TextWrapMode::Wrap),
            )
            .clicked();
        clicked && enabled
    })
    .inner
}

/// A status chip: a mark and a label (`.chip`).
pub(crate) fn chip(
    ui: &mut Ui,
    mark_kind: Mark,
    label: &str,
    color: Color32,
    palette: &CapturePalette,
) -> Response {
    let layout = job(label, 12.0, color, 0.0);
    let galley = ui.painter().layout_job(layout);
    let size = egui::vec2(galley.size().x + 13.0, galley.size().y.max(14.0));
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
    mark(
        ui.painter(),
        egui::pos2(rect.left() + 3.5, rect.center().y),
        mark_kind,
        7.0,
        palette,
    );
    ui.painter().galley(
        egui::pos2(rect.left() + 13.0, rect.center().y - galley.size().y / 2.0),
        galley,
        color,
    );
    response
}

/// A thin progress bar (`.bar`): `fraction` of `rect` filled with `fill`.
pub(crate) fn bar(
    painter: &Painter,
    rect: Rect,
    fraction: f32,
    fill: Color32,
    palette: &CapturePalette,
) {
    painter.rect_filled(rect, 0.0, palette.line2);
    let w = rect.width() * fraction.clamp(0.0, 1.0);
    if w > 0.0 {
        painter.rect_filled(
            Rect::from_min_size(rect.min, egui::vec2(w, rect.height())),
            0.0,
            fill,
        );
    }
}

/// The input box (`.inp`): a dim label at the left, the value at the right.
/// Clickable when `sense` asks.
pub(crate) fn field(
    ui: &mut Ui,
    width: f32,
    label: Option<&str>,
    value: &str,
    chevron: bool,
    sense: Sense,
    palette: &CapturePalette,
) -> Response {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 28.0), sense);
    let p = ui.painter();
    p.rect_filled(rect, 0.0, palette.bg);
    p.rect_stroke(
        rect,
        0.0,
        Stroke::new(
            1.0_f32,
            if response.hovered() && sense.senses_click() {
                palette.ink3
            } else {
                palette.line2
            },
        ),
        StrokeKind::Inside,
    );
    let inner = rect.shrink2(egui::vec2(9.0, 0.0));
    if let Some(label) = label {
        paint_job(
            p,
            inner.left_center(),
            Align2::LEFT_CENTER,
            job(label, 13.0, palette.ink3, 0.0),
        );
        paint_job(
            p,
            inner.right_center() - egui::vec2(if chevron { 16.0 } else { 0.0 }, 0.0),
            Align2::RIGHT_CENTER,
            job(value, 13.0, palette.ink, 0.2),
        );
    } else {
        paint_job(
            p,
            inner.left_center(),
            Align2::LEFT_CENTER,
            job(value, 13.0, palette.ink, 0.2),
        );
    }
    if chevron {
        let c = egui::pos2(inner.right() - 4.0, inner.center().y);
        p.line_segment(
            [c + egui::vec2(-3.5, -1.5), c + egui::vec2(0.0, 2.0)],
            Stroke::new(1.0_f32, palette.ink3),
        );
        p.line_segment(
            [c + egui::vec2(0.0, 2.0), c + egui::vec2(3.5, -1.5)],
            Stroke::new(1.0_f32, palette.ink3),
        );
    }
    response
}

/// Sony's ISO code as shown: `ISO 100`, or `ISO AUTO`.
pub(crate) fn iso_label(code: u64) -> String {
    match code & 0x00ff_ffff {
        0x00ff_ffff => "ISO AUTO".into(),
        iso => format!("ISO {iso}"),
    }
}

/// Sony's shutter code (`numerator << 16 | denominator`) as shown: `1/8 s`,
/// `1/2.5 s`, `0.6 s`, `2 s`, or `Bulb`.
pub(crate) fn shutter_label(code: u64) -> String {
    let (num, den) = (code >> 16, code & 0xffff);
    if code == 0 || num == 0 || den == 0 {
        return "Bulb".into();
    }
    if num < den {
        if num == 1 {
            return format!("1/{den} s");
        }
        let inverse = den as f64 / num as f64;
        if (inverse - inverse.round()).abs() < 1e-9 {
            return format!("1/{} s", inverse.round());
        }
        if num == 10 {
            return format!("1/{:.1} s", inverse);
        }
        return format!("{} s", trim(num as f64 / den as f64));
    }
    format!("{} s", trim(num as f64 / den as f64))
}

fn trim(v: f64) -> String {
    let s = format!("{v:.1}");
    s.strip_suffix(".0").map(str::to_owned).unwrap_or(s)
}

/// Gigabytes with one decimal (`25.0 GB`).
pub(crate) fn gigabytes(bytes: u64) -> String {
    format!("{:.1} GB", bytes as f64 / 1e9)
}

/// A duration as the screens say it: `9.0 min`, `45 s`, `2.1 h`.
pub(crate) fn minutes(seconds: f64) -> String {
    if seconds < 90.0 {
        format!("{:.0} s", seconds.max(0.0))
    } else if seconds < 5400.0 {
        format!("{:.1} min", seconds / 60.0)
    } else {
        format!("{:.1} h", seconds / 3600.0)
    }
}

/// A count of time left: `3:18`, `1:02:05`.
pub(crate) fn clock(seconds: f64) -> String {
    let n = seconds.max(0.0).round() as u64;
    if n >= 3600 {
        format!("{}:{:02}:{:02}", n / 3600, n / 60 % 60, n % 60)
    } else {
        format!("{}:{:02}", n / 60, n % 60)
    }
}

/// A focus position with a thousands separator (`37,556`).
pub(crate) fn focus_units(position: u16) -> String {
    let s = position.to_string();
    if s.len() > 3 {
        format!("{},{}", &s[..s.len() - 3], &s[s.len() - 3..])
    } else {
        s
    }
}

/// The local time `seconds` from now, as `21:47`.
pub(crate) fn local_time_in(seconds: f64) -> String {
    let at =
        chrono::Local::now() + chrono::Duration::milliseconds((seconds.max(0.0) * 1000.0) as i64);
    at.format("%H:%M").to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sony_codes_read_as_the_camera_shows_them() {
        assert_eq!(iso_label(100), "ISO 100");
        assert_eq!(iso_label(0x01ff_ffff), "ISO AUTO");
        assert_eq!(iso_label(0x1000_0c80), "ISO 3200");
        assert_eq!(shutter_label((1 << 16) | 8), "1/8 s");
        assert_eq!(shutter_label((1 << 16) | 125), "1/125 s");
        assert_eq!(shutter_label((10 << 16) | 25), "1/2.5 s");
        assert_eq!(shutter_label((6 << 16) | 10), "0.6 s");
        assert_eq!(shutter_label((2 << 16) | 1), "2 s");
        assert_eq!(shutter_label((13 << 16) | 10), "1.3 s");
        assert_eq!(shutter_label(0), "Bulb");
        assert_eq!(shutter_label((1 << 16) | 5), "1/5 s");
    }

    #[test]
    fn units_and_times_read_as_the_mockups_write_them() {
        assert_eq!(focus_units(37556), "37,556");
        assert_eq!(focus_units(512), "512");
        assert_eq!(clock(198.0), "3:18");
        assert_eq!(clock(3725.0), "1:02:05");
        assert_eq!(minutes(540.0), "9.0 min");
        assert_eq!(minutes(45.0), "45 s");
        assert_eq!(gigabytes(25_000_000_000), "25.0 GB");
    }
}
