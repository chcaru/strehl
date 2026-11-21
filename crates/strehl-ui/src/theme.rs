use eframe::egui::{self, Color32, FontFamily, FontId, Stroke, TextStyle};
// Legacy palette shim. These names keep compiling everywhere they are used
// today and now hold the Graphite tokens (studio-theme.rs, appendix A), so the
// whole app adopts the new palette at once. A constant cannot follow the
// theme chosen in Preferences: new code reads `crate::studio_theme::tokens(ctx)`
// instead. The shell draws stations that still use these constants in the
// Graphite scope on a light theme so they stay legible, and passes drawers
// (today's panes) through `follow_theme`, which recolours them in the theme in
// effect. Replace call sites module by module and delete a constant when no
// caller remains.
pub const BG: Color32 = crate::studio_theme::GRAPHITE.bg;
pub const PANEL: Color32 = crate::studio_theme::GRAPHITE.panel;
pub const RAISED: Color32 = crate::studio_theme::GRAPHITE.raised;
pub const LINE: Color32 = crate::studio_theme::GRAPHITE.line;
pub const INK: Color32 = crate::studio_theme::GRAPHITE.ink;
pub const MUTED: Color32 = crate::studio_theme::GRAPHITE.ink3;
pub const ACCENT: Color32 = crate::studio_theme::GRAPHITE.accent;
pub const GREEN: Color32 = crate::studio_theme::GRAPHITE.ok;
pub const AMBER: Color32 = crate::studio_theme::GRAPHITE.warn;
/// Failure: a capture fault, a stopped render, a refused file.
#[allow(dead_code)]
pub const RED: Color32 = crate::studio_theme::GRAPHITE.bad;

/// The legacy project tree's selected row (`project-explorer.rs`).
const LEGACY_SELECTED: Color32 = Color32::from_rgb(43, 49, 61);

/// Run `paint`, which draws with the Graphite constants above, so that what
/// it adds to `layer` reads natively in the theme in effect: every shape
/// colour that is a Graphite token becomes that token of the current theme.
/// Derived colours (tints, alpha) and pictures are left alone. Costs one pass
/// over the shapes `paint` added, and nothing in Graphite.
pub(crate) fn follow_theme<R>(
    ctx: &egui::Context,
    layer: egui::LayerId,
    paint: impl FnOnce() -> R,
) -> R {
    use crate::studio_theme::{GRAPHITE as G, ThemeName};
    if crate::studio_theme::theme_name(ctx) == ThemeName::Graphite {
        return paint();
    }
    let from = ctx.graphics_mut(|graphics| graphics.entry(layer).next_idx());
    let result = paint();
    let t = crate::studio_theme::tokens(ctx);
    let pairs = [
        (G.bg, t.bg),
        (G.panel, t.panel),
        (G.raised, t.raised),
        (G.control, t.control),
        (G.line, t.line),
        (G.line2, t.line2),
        (G.ink, t.ink),
        (G.ink2, t.ink2),
        (G.ink3, t.ink3),
        (G.accent, t.accent),
        (G.accent_ink, t.accent_ink),
        (G.ok, t.ok),
        (G.warn, t.warn),
        (G.bad, t.bad),
        (G.info, t.info),
        (LEGACY_SELECTED, t.control),
    ];
    let map = |color: Color32| {
        pairs
            .iter()
            .find(|(graphite, _)| *graphite == color)
            .map_or(color, |(_, current)| *current)
    };
    ctx.graphics_mut(|graphics| {
        let list = graphics.entry(layer);
        for index in from.0..list.next_idx().0 {
            list.mutate_shape(egui::layers::ShapeIdx(index), |clipped| {
                recolor(&mut clipped.shape, &map);
            });
        }
    });
    result
}

fn recolor(shape: &mut egui::Shape, map: &impl Fn(Color32) -> Color32) {
    use egui::{Shape, epaint::ColorMode};
    let stroke = |mode: &mut ColorMode| {
        if let ColorMode::Solid(color) = mode {
            *color = map(*color);
        }
    };
    match shape {
        Shape::Vec(shapes) => shapes.iter_mut().for_each(|s| recolor(s, map)),
        Shape::Circle(circle) => {
            circle.fill = map(circle.fill);
            circle.stroke.color = map(circle.stroke.color);
        }
        Shape::Ellipse(ellipse) => {
            ellipse.fill = map(ellipse.fill);
            ellipse.stroke.color = map(ellipse.stroke.color);
        }
        Shape::LineSegment { stroke, .. } => stroke.color = map(stroke.color),
        Shape::Path(path) => {
            path.fill = map(path.fill);
            stroke(&mut path.stroke.color);
        }
        Shape::Rect(rect) => {
            rect.fill = map(rect.fill);
            rect.stroke.color = map(rect.stroke.color);
        }
        Shape::Text(text) => {
            text.underline.color = map(text.underline.color);
            if let Some(color) = text.override_text_color {
                text.override_text_color = Some(map(color));
            } else {
                let mut colors = text.galley.job.sections.iter().map(|s| s.format.color);
                let first = colors.next();
                if let Some(first) = first
                    && colors.all(|color| color == first)
                {
                    if first == Color32::PLACEHOLDER {
                        text.fallback_color = map(text.fallback_color);
                    } else if map(first) != first {
                        text.override_text_color = Some(map(first));
                    }
                }
            }
        }
        Shape::Mesh(mesh) if mesh.texture_id == egui::TextureId::default() => {
            for vertex in &mut std::sync::Arc::make_mut(mesh).vertices {
                vertex.color = map(vertex.color);
            }
        }
        Shape::QuadraticBezier(curve) => {
            curve.fill = map(curve.fill);
            stroke(&mut curve.stroke.color);
        }
        Shape::CubicBezier(curve) => {
            curve.fill = map(curve.fill);
            stroke(&mut curve.stroke.color);
        }
        _ => {}
    }
}

/// Keep the button and popup tied to the parent control's width. egui's Width
/// option is a minimum, and its popup defaults to Extend; neither bounds long
/// labels or prevents an expanding parent/menu from feeding the next layout.
pub struct Dropdown {
    inner: egui::ComboBox,
    width: Option<f32>,
}
impl Dropdown {
    pub fn from_id_salt(id: impl std::hash::Hash) -> Self {
        Self {
            inner: egui::ComboBox::from_id_salt(id),
            width: None,
        }
    }
    pub fn width(mut self, width: f32) -> Self {
        self.width = Some(width);
        self
    }
    pub fn selected_text(mut self, text: impl Into<egui::WidgetText>) -> Self {
        self.inner = self.inner.selected_text(text);
        self
    }
    pub fn truncate(self) -> Self {
        self
    }
    pub fn show_ui<R>(
        self,
        ui: &mut egui::Ui,
        content: impl FnOnce(&mut egui::Ui) -> R,
    ) -> egui::InnerResponse<Option<R>> {
        let width = self
            .width
            .unwrap_or(ui.spacing().combo_width)
            .min(ui.available_width())
            .max(24.0);
        self.inner.width(width).truncate().show_ui(ui, |menu| {
            let margin = egui::Frame::popup(menu.style()).total_margin().sum().x;
            menu.set_width((width - margin).max(8.0));
            menu.style_mut().wrap_mode = Some(egui::TextWrapMode::Truncate);
            content(menu)
        })
    }
}
/// A single physical pixel at every display scale. Axis-aligned rules sit on
/// pixel centers, so adjacent panels do not make blurred two-pixel boundaries.
pub fn rule(p: &egui::Painter, mut from: egui::Pos2, mut to: egui::Pos2, color: Color32) {
    let scale = p.ctx().pixels_per_point();
    if from.x == to.x {
        let x = if (from.x - p.clip_rect().right()).abs() < 0.01 {
            (from.x * scale).floor() / scale - 0.5 / scale
        } else {
            (from.x * scale).floor() / scale + 0.5 / scale
        };
        from.x = x;
        to.x = x;
    } else if from.y == to.y {
        let y = if (from.y - p.clip_rect().bottom()).abs() < 0.01 {
            (from.y * scale).floor() / scale - 0.5 / scale
        } else {
            (from.y * scale).floor() / scale + 0.5 / scale
        };
        from.y = y;
        to.y = y;
    }
    p.line_segment([from, to], Stroke::new(1.0 / scale, color));
}
pub fn install(ctx: &egui::Context) {
    // Keep native controls on the same palette when the OS reports light mode.
    ctx.set_theme(egui::Theme::Dark);
    // Read installed system faces; font files are never redistributed.
    crate::studio_fonts::install(ctx);
    crate::studio_theme::apply(
        ctx,
        crate::studio_theme::theme_name(ctx),
        crate::studio_theme::surround(ctx),
        crate::studio_theme::reduced_motion(ctx),
    );
}

fn mix(a: Color32, b: Color32, t: f32) -> Color32 {
    let channel = |x: u8, y: u8| (x as f32 + (y as f32 - x as f32) * t).round() as u8;
    Color32::from_rgb(
        channel(a.r(), b.r()),
        channel(a.g(), b.g()),
        channel(a.b(), b.b()),
    )
}

/// egui's style for a set of tokens: square corners, hairline rules, no
/// shadow except under popovers, and the Studio type scale (plan 6.4).
pub(crate) fn studio_style(
    base: &egui::Style,
    t: &crate::studio_theme::Tokens,
    hairline: f32,
    reduced_motion: bool,
    strong: FontFamily,
) -> egui::Style {
    use crate::studio_theme::scale;
    let mut style = base.clone();
    style.visuals = if t.light {
        egui::Visuals::light()
    } else {
        egui::Visuals::dark()
    };
    let visuals = &mut style.visuals;
    visuals.panel_fill = t.panel;
    visuals.window_fill = t.panel;
    visuals.extreme_bg_color = t.bg;
    visuals.faint_bg_color = t.raised;
    visuals.override_text_color = Some(t.ink);
    visuals.selection.bg_fill = mix(t.panel, t.accent, if t.light { 0.24 } else { 0.2 });
    visuals.selection.stroke = Stroke::new(hairline, t.accent);
    visuals.window_corner_radius = egui::CornerRadius::ZERO;
    visuals.menu_corner_radius = egui::CornerRadius::ZERO;
    let shadow = egui::epaint::Shadow {
        offset: [0, 10],
        blur: 30,
        spread: 0,
        color: t.shadow,
    };
    visuals.window_shadow = shadow;
    visuals.popup_shadow = shadow;
    visuals.window_stroke = Stroke::new(hairline, t.line2);
    // Links are neutral; only a check that needs a look takes the accent.
    visuals.hyperlink_color = t.ink2;
    visuals.warn_fg_color = t.warn;
    visuals.error_fg_color = t.bad;
    visuals.code_bg_color = t.bg;
    let widgets = &mut visuals.widgets;
    widgets.noninteractive.bg_fill = t.panel;
    widgets.noninteractive.weak_bg_fill = t.panel;
    widgets.noninteractive.bg_stroke = Stroke::new(hairline, t.line);
    widgets.noninteractive.fg_stroke = Stroke::new(hairline, t.ink2);
    // Buttons read as outlines: their fill is the panel they sit on.
    widgets.inactive.weak_bg_fill = t.panel;
    widgets.inactive.bg_fill = t.control;
    widgets.inactive.bg_stroke = Stroke::new(hairline, t.line2);
    widgets.inactive.fg_stroke = Stroke::new(hairline, t.ink);
    // Hover lightens the outline; amber is kept for selection and the main action.
    widgets.hovered.weak_bg_fill = t.panel;
    widgets.hovered.bg_fill = t.control;
    widgets.hovered.bg_stroke = Stroke::new(hairline, t.ink3);
    widgets.hovered.fg_stroke = Stroke::new(hairline, t.ink);
    widgets.active.weak_bg_fill = t.control;
    widgets.active.bg_fill = t.control;
    widgets.active.bg_stroke = Stroke::new(hairline, t.accent);
    widgets.active.fg_stroke = Stroke::new(hairline, t.ink);
    widgets.open = widgets.active;
    for widget in [
        &mut widgets.noninteractive,
        &mut widgets.inactive,
        &mut widgets.hovered,
        &mut widgets.active,
        &mut widgets.open,
    ] {
        widget.corner_radius = egui::CornerRadius::ZERO;
        widget.expansion = 0.0;
    }
    style.spacing.item_spacing = egui::vec2(6.0, 3.0);
    style.spacing.button_padding = egui::vec2(8.0, 3.0);
    style.spacing.interact_size.y = 24.0;
    style.spacing.slider_width = 125.0;
    style.spacing.scroll = egui::style::ScrollStyle::solid();
    style.spacing.scroll.bar_width = 5.0;
    style.spacing.scroll.bar_inner_margin = 6.0;
    style.spacing.scroll.bar_outer_margin = 1.0;
    style.visuals.handle_shape = egui::style::HandleShape::Rect { aspect_ratio: 0.5 };
    // No animation is longer than 160 ms; reduced motion removes them.
    style.animation_time = if reduced_motion { 0.0 } else { 0.1 };
    // Studio widgets size their own labels. egui's Button style stays at the
    // 11 px the existing panes align their painted labels with (the Develop
    // pane's value fields, for one); every style stays above 10.5 px.
    for (name, size) in [
        (TextStyle::Body, scale::BODY),
        (TextStyle::Button, 11.0),
        (TextStyle::Small, scale::HINT),
    ] {
        style
            .text_styles
            .insert(name, FontId::new(size, FontFamily::Proportional));
    }
    style
        .text_styles
        .insert(TextStyle::Heading, FontId::new(scale::STATEMENT, strong));
    style
        .text_styles
        .insert(TextStyle::Monospace, FontId::monospace(scale::HINT));
    style
}
/// A quiet sentence: the scale's smallest size for one (12 px).
pub fn caption(ui: &mut egui::Ui, text: &str) {
    ui.label(
        egui::RichText::new(text)
            .size(crate::studio_theme::scale::SECONDARY)
            .color(MUTED),
    );
}
/// A full-width command row. Its geometry stays unchanged when disabled or
/// hovered, and the resource line has its own reserved strip.
pub fn stack_action(
    ui: &mut egui::Ui,
    size: egui::Vec2,
    enabled: bool,
    spec: Option<&str>,
) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(
        size,
        if enabled {
            egui::Sense::click()
        } else {
            egui::Sense::hover()
        },
    );
    response.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, enabled, "Stack"));
    let p = ui.painter_at(rect);
    let hover = enabled && response.hovered();
    let active = enabled && (response.has_focus() || response.is_pointer_button_down_on());
    p.rect_filled(rect, 0.0, if hover { RAISED } else { PANEL });
    p.rect_stroke(
        rect,
        0.0,
        Stroke::new(1.0_f32, if active { ACCENT } else { LINE }),
        egui::StrokeKind::Inside,
    );
    let command_height = if spec.is_some() { 34.0 } else { rect.height() };
    let compact = spec.is_none() && rect.width() < 180.0;
    let y = rect.top() + command_height * 0.5;
    let ink = if enabled { INK } else { MUTED };
    p.rect_filled(
        egui::Rect::from_min_size(rect.min, egui::vec2(2.0, command_height)),
        0.0,
        if enabled { ACCENT } else { LINE },
    );
    for layer in 0..3 {
        let plane = egui::Rect::from_min_size(
            egui::pos2(
                rect.left() + 13.0 + layer as f32 * 3.0,
                y - 8.0 + layer as f32 * 3.0,
            ),
            egui::vec2(14.0, 10.0),
        );
        p.rect_filled(plane, 0.0, if hover { RAISED } else { PANEL });
        p.rect_stroke(
            plane,
            0.0,
            Stroke::new(1.0_f32, if layer == 2 && enabled { ACCENT } else { MUTED }),
            egui::StrokeKind::Inside,
        );
    }
    p.text(
        egui::pos2(rect.left() + if compact { 38.0 } else { 46.0 }, y),
        egui::Align2::LEFT_CENTER,
        "Stack",
        FontId::proportional(if spec.is_some() { 16.0 } else { 13.0 }),
        ink,
    );
    let execute = egui::Rect::from_min_max(
        egui::pos2(
            rect.right() - if compact { 28.0 } else { 36.0 },
            rect.top() + 1.0,
        ),
        egui::pos2(rect.right() - 1.0, rect.top() + command_height - 1.0),
    );
    p.line_segment(
        [execute.left_top(), execute.left_bottom()],
        Stroke::new(1.0_f32, LINE),
    );
    let at = execute.center();
    let stroke = Stroke::new(1.2_f32, if enabled { ACCENT } else { MUTED });
    p.line_segment(
        [at - egui::vec2(6.0, 0.0), at + egui::vec2(6.0, 0.0)],
        stroke,
    );
    p.line_segment(
        [at + egui::vec2(1.0, -5.0), at + egui::vec2(6.0, 0.0)],
        stroke,
    );
    p.line_segment(
        [at + egui::vec2(1.0, 5.0), at + egui::vec2(6.0, 0.0)],
        stroke,
    );
    if let Some(spec) = spec {
        let rule_y = rect.top() + command_height;
        p.line_segment(
            [
                egui::pos2(rect.left() + 1.0, rule_y),
                egui::pos2(rect.right() - 1.0, rule_y),
            ],
            Stroke::new(1.0_f32, LINE),
        );
        let details = egui::Rect::from_min_max(
            egui::pos2(rect.left() + 12.0, rule_y + 4.0),
            rect.right_bottom() - egui::vec2(12.0, 3.0),
        );
        let galley = p.layout(
            spec.to_owned(),
            FontId::proportional(8.5),
            MUTED,
            details.width(),
        );
        p.with_clip_rect(details).galley(details.min, galley, MUTED);
    }
    if enabled {
        response.on_hover_cursor(egui::CursorIcon::PointingHand)
    } else {
        response
    }
}
pub fn tab(ui: &mut egui::Ui, text: &str, selected: bool) -> egui::Response {
    let response = ui.add(
        egui::Button::new(egui::RichText::new(text).size(11.5).color(if selected {
            INK
        } else {
            MUTED
        }))
        .frame(false)
        .min_size(egui::vec2(0.0, 26.0)),
    );
    if selected || response.hovered() {
        let inset = (response.rect.width() * 0.12).clamp(2.0, 7.0);
        ui.painter().line_segment(
            [
                response.rect.left_bottom() + egui::vec2(inset, -1.0),
                response.rect.right_bottom() + egui::vec2(-inset, -1.0),
            ],
            Stroke::new(1.0_f32, if selected { ACCENT } else { LINE }),
        );
    }
    response
}
pub fn mark(painter: &egui::Painter, rect: egui::Rect) {
    let scale = rect.width().min(rect.height()) / 20.0;
    for i in 0..3 {
        let r = egui::Rect::from_min_size(
            rect.min + egui::vec2(i as f32 * 3.0, (2 - i) as f32 * 3.0) * scale,
            egui::vec2(14.0, 14.0) * scale,
        );
        painter.rect_filled(r, 0.0, PANEL);
        painter.rect_stroke(
            r,
            0.0,
            Stroke::new(1.2_f32, if i == 2 { ACCENT } else { MUTED }),
            egui::StrokeKind::Inside,
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dropdown_does_not_grow_across_pointer_repaints() {
        let ctx = egui::Context::default();
        ctx.set_pixels_per_point(1.25);
        install(&ctx);
        let mut widths = Vec::new();
        let mut selected = 0;
        for frame in 0..45 {
            let _ = ctx.run(
                egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(
                        egui::Pos2::ZERO,
                        egui::vec2(900.0, 600.0),
                    )),
                    time: Some(frame as f64 / 30.0),
                    events: vec![egui::Event::PointerMoved(egui::pos2(
                        60.0 + (frame % 5) as f32,
                        60.0,
                    ))],
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| {
                        let combo = Dropdown::from_id_salt("regression-dropdown")
                            .width(180.0)
                            .selected_text("Capture mode");
                        let popup = ui
                            .make_persistent_id(egui::Id::new("regression-dropdown"))
                            .with("popup");
                        egui::Popup::open_id(ctx, popup);
                        combo.show_ui(ui, |ui| {
                            for i in 0..45 {
                                ui.selectable_value(
                                    &mut selected,
                                    i,
                                    format!("Capture preset {i} with an intentionally extremely long folder name that must never widen the overlay"),
                                );
                            }
                            if frame >= 10 {
                                widths.push(ui.min_rect().width());
                            }
                        });
                    });
                },
            );
        }
        assert!(widths.len() >= 30, "Must exercise the open popup");
        let first = widths[0];
        assert!(
            first <= 180.0,
            "Long labels must not expand the dropdown: {first}"
        );
        assert!(
            widths.iter().all(|w| (*w - first).abs() <= 1.0),
            "Dropdown grew: {widths:?}"
        );
    }

    fn native_control_colors(
        ctx: &egui::Context,
        system_theme: egui::Theme,
        time: f64,
    ) -> (Color32, Color32, Color32) {
        let mut text = "Strehl project".to_owned();
        let mut edit = egui::Rect::NOTHING;
        let mut separator = egui::Rect::NOTHING;
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(400.0, 200.0),
                )),
                system_theme: Some(system_theme),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    edit = ui.text_edit_singleline(&mut text).rect;
                    separator = ui.separator().rect;
                });
            },
        );
        assert_eq!(ctx.system_theme(), Some(system_theme));
        let (fill, border) = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Rect(rect) if rect.rect == edit => {
                    Some((rect.fill, rect.stroke.color))
                }
                _ => None,
            })
            .expect("the real text editor must paint its background and border");
        let rule = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::LineSegment { points, stroke }
                    if points[0].y == points[1].y
                        && (points[0].y - separator.center().y).abs() < 0.01 =>
                {
                    Some(stroke.color)
                }
                _ => None,
            })
            .expect("the real separator must paint its rule");
        (fill, border, rule)
    }

    #[test]
    fn native_controls_keep_the_app_palette_across_system_theme_changes() {
        for initial_light in [false, true] {
            let ctx = egui::Context::default();
            if initial_light {
                let _ = native_control_colors(&ctx, egui::Theme::Light, 0.0);
            }
            install(&ctx);
            for (frame, system_theme) in [egui::Theme::Light, egui::Theme::Dark, egui::Theme::Light]
                .into_iter()
                .enumerate()
            {
                let colors = native_control_colors(&ctx, system_theme, frame as f64 + 1.0);
                assert_eq!(
                    colors,
                    (BG, crate::studio_theme::GRAPHITE.line2, LINE),
                    "OS theme changes must preserve the actual editor and separator paint"
                );
                assert_eq!(ctx.theme(), egui::Theme::Dark);
                assert_eq!(ctx.style().visuals.panel_fill, PANEL);
                assert_eq!(ctx.style().visuals.override_text_color, Some(INK));
            }
        }

        // Reproduce the retired automatic-theme preference on the same real
        // widgets: a light OS input must expose the white editor/bright rules.
        let control = egui::Context::default();
        install(&control);
        control.set_theme(egui::ThemePreference::System);
        let (fill, border, rule) = native_control_colors(&control, egui::Theme::Light, 0.0);
        assert_eq!(control.theme(), egui::Theme::Light);
        assert_ne!(fill, BG);
        assert_ne!(border, crate::studio_theme::GRAPHITE.line2);
        assert_ne!(rule, LINE);
    }

    fn command_frame(
        ctx: &egui::Context,
        size: egui::Vec2,
        enabled: bool,
        spec: Option<&str>,
        time: f64,
        events: Vec<egui::Event>,
    ) -> (egui::Rect, bool, egui::FullOutput) {
        let mut rect = egui::Rect::NOTHING;
        let mut clicked = false;
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    size + egui::vec2(40.0, 40.0),
                )),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        let response = stack_action(ui, size, enabled, spec);
                        rect = response.rect;
                        clicked = response.clicked();
                    });
            },
        );
        (rect, clicked, output)
    }

    #[test]
    fn stack_command_fits_its_reserved_strip_and_only_enabled_clicks_activate() {
        let spec = "Full resolution · 16-bit RGB · 32/32 CPU threads · 61.6 GiB RAM";
        for width in [112.0, 264.0, 320.0] {
            for spec in [Some(spec), None] {
                if width == 112.0 && spec.is_some() {
                    continue;
                }
                for enabled in [false, true] {
                    let ctx = egui::Context::default();
                    install(&ctx);
                    let size = egui::vec2(
                        width,
                        if width == 112.0 {
                            29.0
                        } else if spec.is_some() {
                            65.0
                        } else {
                            38.0
                        },
                    );
                    let (rect, _, output) = command_frame(&ctx, size, enabled, spec, 0.0, vec![]);
                    let mut saw_label = false;
                    let mut saw_spec = false;
                    for shape in &output.shapes {
                        if let egui::Shape::Text(text) = &shape.shape {
                            saw_label |= text.galley.text() == "Stack";
                            saw_spec |= spec.is_some_and(|value| text.galley.text() == value);
                            if text.galley.text() == "Stack" {
                                let divider = output
                                    .shapes
                                    .iter()
                                    .find_map(|shape| {
                                        if let egui::Shape::LineSegment { points, .. } =
                                            &shape.shape
                                        {
                                            (points[0].x == points[1].x
                                                && points[0].x > rect.center().x
                                                && points[1].y > points[0].y)
                                                .then_some(points[0].x)
                                        } else {
                                            None
                                        }
                                    })
                                    .expect("The execute area must have its real painted divider");
                                assert!(
                                    text.visual_bounding_rect().right() <= divider - 4.0,
                                    "Stack label must leave space before its execute divider at {width}px"
                                );
                            }
                            assert!(
                                rect.contains_rect(text.visual_bounding_rect()),
                                "visible command text must fit the actual action at {width}px: {:?}",
                                text.visual_bounding_rect()
                            );
                            assert!(
                                shape.clip_rect.contains_rect(text.visual_bounding_rect()),
                                "metadata must fit without relying on clipping its last row"
                            );
                        }
                    }
                    assert!(
                        saw_label && (spec.is_none() || saw_spec),
                        "fixture must paint both the command and requested resource text"
                    );
                    let position = rect.center();
                    let button = |pressed| egui::Event::PointerButton {
                        pos: position,
                        button: egui::PointerButton::Primary,
                        pressed,
                        modifiers: egui::Modifiers::NONE,
                    };
                    let (pressed, _, _) = command_frame(
                        &ctx,
                        size,
                        enabled,
                        spec,
                        0.1,
                        vec![egui::Event::PointerMoved(position), button(true)],
                    );
                    let (released, clicked, _) =
                        command_frame(&ctx, size, enabled, spec, 0.2, vec![button(false)]);
                    assert_eq!(rect, pressed);
                    assert_eq!(rect, released);
                    assert_eq!(
                        clicked, enabled,
                        "a disabled command must never launch stacking"
                    );
                }
            }
        }
    }
}
