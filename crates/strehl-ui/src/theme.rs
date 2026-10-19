use eframe::egui::{self, Color32, FontFamily, FontId, Stroke, TextStyle};
pub const BG: Color32 = Color32::from_rgb(16, 20, 28);
pub const PANEL: Color32 = Color32::from_rgb(20, 24, 33);
pub const RAISED: Color32 = Color32::from_rgb(27, 32, 42);
pub const LINE: Color32 = Color32::from_rgb(44, 51, 64);
pub const INK: Color32 = Color32::from_rgb(200, 198, 190);
pub const MUTED: Color32 = Color32::from_rgb(141, 150, 162);
pub const ACCENT: Color32 = Color32::from_rgb(230, 180, 80);
pub const GREEN: Color32 = Color32::from_rgb(169, 199, 121);
pub const AMBER: Color32 = Color32::from_rgb(223, 156, 99);
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
    // Read an installed system face; font files are never redistributed.
    #[cfg(windows)]
    if let Ok(bytes) = std::fs::read("C:/Windows/Fonts/segoeui.ttf") {
        let mut fonts = egui::FontDefinitions::default();
        fonts
            .font_data
            .insert("system-ui".into(), egui::FontData::from_owned(bytes).into());
        fonts
            .families
            .entry(FontFamily::Proportional)
            .or_default()
            .insert(0, "system-ui".into());
        ctx.set_fonts(fonts);
    }
    let hairline = 1.0 / ctx.pixels_per_point();
    let mut style = (*ctx.style()).clone();
    style.visuals = egui::Visuals::dark();
    style.visuals.panel_fill = PANEL;
    style.visuals.window_fill = PANEL;
    style.visuals.extreme_bg_color = BG;
    style.visuals.faint_bg_color = RAISED;
    style.visuals.override_text_color = Some(INK);
    style.visuals.selection.bg_fill = Color32::from_rgb(53, 47, 34);
    style.visuals.selection.stroke = Stroke::new(hairline, ACCENT);
    style.visuals.window_corner_radius = egui::CornerRadius::ZERO;
    style.visuals.menu_corner_radius = egui::CornerRadius::ZERO;
    style.visuals.window_shadow = egui::epaint::Shadow::NONE;
    style.visuals.popup_shadow = egui::epaint::Shadow::NONE;
    style.visuals.window_stroke = Stroke::new(hairline, LINE);
    style.visuals.hyperlink_color = ACCENT;
    style.visuals.warn_fg_color = AMBER;
    style.visuals.code_bg_color = BG;
    style.visuals.widgets.noninteractive.bg_fill = PANEL;
    style.visuals.widgets.noninteractive.bg_stroke = Stroke::new(hairline, LINE);
    style.visuals.widgets.noninteractive.fg_stroke = Stroke::new(hairline, MUTED);
    style.visuals.widgets.inactive.weak_bg_fill = PANEL;
    style.visuals.widgets.inactive.bg_fill = RAISED;
    style.visuals.widgets.inactive.bg_stroke = Stroke::new(hairline, LINE);
    style.visuals.widgets.inactive.fg_stroke = Stroke::new(hairline, INK);
    style.visuals.widgets.hovered.weak_bg_fill = RAISED;
    style.visuals.widgets.hovered.bg_fill = RAISED;
    style.visuals.widgets.hovered.bg_stroke = Stroke::new(hairline, LINE);
    style.visuals.widgets.hovered.fg_stroke = Stroke::new(hairline, ACCENT);
    style.visuals.widgets.active.weak_bg_fill = Color32::from_rgb(45, 42, 34);
    style.visuals.widgets.active.bg_fill = Color32::from_rgb(45, 42, 34);
    style.visuals.widgets.active.bg_stroke = Stroke::new(hairline, ACCENT);
    style.visuals.widgets.active.fg_stroke = Stroke::new(hairline, ACCENT);
    style.visuals.widgets.open = style.visuals.widgets.active;
    for widget in [
        &mut style.visuals.widgets.noninteractive,
        &mut style.visuals.widgets.inactive,
        &mut style.visuals.widgets.hovered,
        &mut style.visuals.widgets.active,
        &mut style.visuals.widgets.open,
    ] {
        widget.corner_radius = egui::CornerRadius::ZERO;
        widget.expansion = 0.0;
    }
    style.spacing.item_spacing = egui::vec2(6.0, 3.0);
    style.spacing.button_padding = egui::vec2(7.0, 3.0);
    style.spacing.interact_size.y = 23.0;
    style.spacing.slider_width = 125.0;
    style.spacing.scroll = egui::style::ScrollStyle::solid();
    style.spacing.scroll.bar_width = 5.0;
    style.spacing.scroll.bar_inner_margin = 6.0;
    style.spacing.scroll.bar_outer_margin = 1.0;
    style.visuals.handle_shape = egui::style::HandleShape::Rect { aspect_ratio: 0.5 };
    for (name, size) in [
        (TextStyle::Body, 11.0),
        (TextStyle::Button, 11.0),
        (TextStyle::Small, 10.0),
        (TextStyle::Heading, 14.0),
    ] {
        style
            .text_styles
            .insert(name, FontId::new(size, FontFamily::Proportional));
    }
    style
        .text_styles
        .insert(TextStyle::Monospace, FontId::monospace(11.0));
    ctx.set_style(style);
}
pub fn caption(ui: &mut egui::Ui, text: &str) {
    ui.label(egui::RichText::new(text).size(11.0).color(MUTED));
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
