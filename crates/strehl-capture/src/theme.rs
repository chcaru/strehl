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
/// Same native palette, square controls and system face as Strehl's workspace.
pub fn install(ctx: &egui::Context) {
    ctx.set_theme(egui::Theme::Dark);
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
    let mut style = (*ctx.style()).clone();
    style.visuals = egui::Visuals::dark();
    style.visuals.panel_fill = PANEL;
    style.visuals.window_fill = PANEL;
    style.visuals.extreme_bg_color = BG;
    style.visuals.faint_bg_color = RAISED;
    style.visuals.override_text_color = Some(INK);
    style.visuals.selection.bg_fill = Color32::from_rgb(53, 47, 34);
    style.visuals.selection.stroke = Stroke::new(1.0_f32, ACCENT);
    style.visuals.hyperlink_color = ACCENT;
    style.visuals.warn_fg_color = AMBER;
    style.visuals.window_corner_radius = egui::CornerRadius::ZERO;
    style.visuals.window_shadow = egui::epaint::Shadow::NONE;
    for w in [
        &mut style.visuals.widgets.noninteractive,
        &mut style.visuals.widgets.inactive,
        &mut style.visuals.widgets.hovered,
        &mut style.visuals.widgets.active,
        &mut style.visuals.widgets.open,
    ] {
        w.corner_radius = egui::CornerRadius::ZERO;
        w.bg_fill = RAISED;
        w.weak_bg_fill = PANEL;
        w.bg_stroke = Stroke::new(1.0_f32, LINE);
        w.fg_stroke = Stroke::new(1.0_f32, INK);
        w.expansion = 0.0;
    }
    style.visuals.widgets.hovered.fg_stroke = Stroke::new(1.0_f32, ACCENT);
    style.visuals.widgets.active.bg_stroke = Stroke::new(1.0_f32, ACCENT);
    style.spacing.item_spacing = egui::vec2(7.0, 7.0);
    style.spacing.button_padding = egui::vec2(10.0, 6.0);
    style.spacing.interact_size.y = 29.0;
    style.spacing.slider_width = 130.0;
    for (name, size) in [
        (TextStyle::Body, 12.0),
        (TextStyle::Button, 12.0),
        (TextStyle::Small, 11.0),
        (TextStyle::Heading, 16.0),
    ] {
        style.text_styles.insert(name, FontId::proportional(size));
    }
    style
        .text_styles
        .insert(TextStyle::Monospace, FontId::monospace(12.0));
    ctx.set_style(style);
}
