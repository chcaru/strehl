//! Studio 2 theme tokens (implementation plan 6.4 and appendix A).
//!
//! The current tokens live in the egui context, so any code holding a
//! `Context` reads the theme the owner chose in Preferences. `theme.rs`
//! builds egui's own `Style` from them; its legacy constants keep the
//! Graphite values for code that has not moved to `tokens(ctx)` yet.
use eframe::egui::{self, Color32};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

const fn hex(rgb: u32) -> Color32 {
    Color32::from_rgb((rgb >> 16) as u8, (rgb >> 8) as u8, rgb as u8)
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum ThemeName {
    #[default]
    Graphite,
    Instrument,
    Lightbox,
}
impl ThemeName {
    pub(crate) const ALL: [Self; 3] = [Self::Graphite, Self::Instrument, Self::Lightbox];
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Graphite => "Graphite",
            Self::Instrument => "Instrument",
            Self::Lightbox => "Lightbox",
        }
    }
    pub(crate) fn key(self) -> &'static str {
        match self {
            Self::Graphite => "graphite",
            Self::Instrument => "instrument",
            Self::Lightbox => "lightbox",
        }
    }
    pub(crate) fn parse(value: &str) -> Option<Self> {
        Self::ALL
            .into_iter()
            .find(|theme| theme.key().eq_ignore_ascii_case(value.trim()))
    }
    pub(crate) const fn tokens(self) -> Tokens {
        match self {
            Self::Graphite => GRAPHITE,
            Self::Instrument => INSTRUMENT,
            Self::Lightbox => LIGHTBOX,
        }
    }
}

/// What surrounds the photograph on the canvas.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Surround {
    /// The theme's own surround token.
    #[default]
    Theme,
    Black,
    /// A neutral mid-dark grey for judging tone against.
    Grey,
}
impl Surround {
    pub(crate) const ALL: [Self; 3] = [Self::Theme, Self::Black, Self::Grey];
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Theme => "Theme",
            Self::Black => "Black",
            Self::Grey => "Grey",
        }
    }
    pub(crate) fn color(self, theme: Color32) -> Color32 {
        match self {
            Self::Theme => theme,
            Self::Black => Color32::BLACK,
            Self::Grey => hex(0x3a3a3a),
        }
    }
}

/// Every colour a Studio 2 view may use. Detail sizes are coloured by
/// `spectrum` everywhere they appear; text on the dark photograph surround uses
/// `canvas_ink` and `canvas_line`, which differ from the panel inks on Lightbox.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Tokens {
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
    pub spectrum: [Color32; 8],
    pub canvas_ink: [Color32; 3],
    pub canvas_line: [Color32; 2],
    /// Shadow under popovers, the only shadow in the design.
    pub shadow: Color32,
    pub light: bool,
}

/// Detail sizes in pixels, in `Tokens::spectrum` order.
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
pub(crate) const DETAIL_SIZES: [u32; 8] = [2, 4, 8, 16, 32, 64, 128, 256];
pub(crate) const SPECTRUM_DARK: [Color32; 8] = [
    hex(0x5fd9cf),
    hex(0x7fd3ea),
    hex(0xa7c9f2),
    hex(0xc8c0ef),
    hex(0xe2b9dc),
    hex(0xf1b7b4),
    hex(0xf4c18a),
    hex(0xedd06c),
];
pub(crate) const SPECTRUM_LIGHT: [Color32; 8] = [
    hex(0x0f9d92),
    hex(0x1f8fb5),
    hex(0x3f78c9),
    hex(0x6a5fc4),
    hex(0xa2529f),
    hex(0xc2524d),
    hex(0xc47a1c),
    hex(0xa58a00),
];

pub(crate) const GRAPHITE: Tokens = Tokens {
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
    // #e6b450 at 12 %, premultiplied.
    accent_soft: Color32::from_rgba_premultiplied(28, 22, 10, 31),
    ok: hex(0xa9c779),
    warn: hex(0xf08a4b),
    bad: hex(0xe5604c),
    info: hex(0x8ab4e8),
    plane: hex(0x55d6c4),
    surround: hex(0x0e0e0f),
    spectrum: SPECTRUM_DARK,
    canvas_ink: [hex(0xe9e6de), hex(0xa19f98), hex(0x807e77)],
    canvas_line: [hex(0x232326), hex(0x37373c)],
    shadow: Color32::from_black_alpha(140),
    light: false,
};

pub(crate) const INSTRUMENT: Tokens = Tokens {
    bg: hex(0x10141c),
    panel: hex(0x141821),
    raised: hex(0x1a1f29),
    control: hex(0x212835),
    line: hex(0x272e3a),
    line2: hex(0x3a4353),
    ink: hex(0xe2e0d8),
    ink2: hex(0x99a2ae),
    ink3: hex(0x7c8799),
    surround: hex(0x0c0f15),
    canvas_ink: [hex(0xe2e0d8), hex(0x99a2ae), hex(0x7c8799)],
    canvas_line: [hex(0x272e3a), hex(0x3a4353)],
    ..GRAPHITE
};

pub(crate) const LIGHTBOX: Tokens = Tokens {
    bg: hex(0xe7e6e1),
    panel: hex(0xf3f2ee),
    raised: hex(0xfaf9f6),
    control: hex(0xe9e7e1),
    line: hex(0xd8d5cd),
    line2: hex(0xb9b5ab),
    ink: hex(0x19191b),
    ink2: hex(0x55544f),
    ink3: hex(0x6f6d66),
    accent: hex(0xa46300),
    accent_ink: hex(0xffffff),
    // #a46300 at 10 %, premultiplied.
    accent_soft: Color32::from_rgba_premultiplied(17, 10, 0, 26),
    ok: hex(0x4f7d2c),
    warn: hex(0xb9520c),
    bad: hex(0xb83224),
    info: hex(0x2a66ad),
    plane: hex(0x0c8a7c),
    surround: hex(0x2a2a2b),
    spectrum: SPECTRUM_LIGHT,
    canvas_ink: [hex(0xe9e6de), hex(0xa19f98), hex(0x96948d)],
    canvas_line: [hex(0x3a3a3d), hex(0x57575c)],
    shadow: Color32::from_black_alpha(51),
    light: true,
};

/// The type scale, in points at 1.0 pixels per point (appendix A).
pub(crate) mod scale {
    /// Headline figures, light.
    #[allow(dead_code)]
    pub(crate) const HEADLINE: f32 = 64.0;
    /// The glance headline, light.
    #[allow(dead_code)]
    pub(crate) const GLANCE: f32 = 136.0;
    /// Titles, strong.
    #[allow(dead_code)]
    pub(crate) const TITLE: f32 = 24.0;
    /// Statements, strong.
    pub(crate) const STATEMENT: f32 = 15.0;
    /// Body text and controls.
    pub(crate) const BODY: f32 = 13.0;
    /// Button labels (`.btn`, 12.5 px).
    pub(crate) const CONTROL: f32 = 12.5;
    /// Secondary text; the smallest size for a sentence.
    pub(crate) const SECONDARY: f32 = 12.0;
    /// Hint bar and key facts.
    pub(crate) const HINT: f32 = 11.5;
    /// Tracked capitals: labels, stations, links. Never smaller.
    pub(crate) const CAPS: f32 = 10.5;
    /// Station names are tracked capitals at 11 px.
    pub(crate) const STATION: f32 = 11.0;
    /// Letter spacing of tracked capitals, as a fraction of the size.
    pub(crate) const CAPS_TRACKING: f32 = 0.13;
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct Active {
    name: ThemeName,
    surround: Surround,
    reduced_motion: bool,
    tokens: Tokens,
}
impl Active {
    fn new(name: ThemeName, surround: Surround, reduced_motion: bool) -> Self {
        let mut tokens = name.tokens();
        tokens.surround = surround.color(tokens.surround);
        Self {
            name,
            surround,
            reduced_motion,
            tokens,
        }
    }
}
fn active_id() -> egui::Id {
    egui::Id::new("studio-theme-active")
}
fn active(ctx: &egui::Context) -> Active {
    ctx.data(|data| data.get_temp::<Active>(active_id()))
        .unwrap_or_else(|| Active::new(ThemeName::Graphite, Surround::Theme, false))
}

/// The tokens of the theme in effect, including the surround preference.
pub(crate) fn tokens(ctx: &egui::Context) -> Tokens {
    active(ctx).tokens
}
pub(crate) fn theme_name(ctx: &egui::Context) -> ThemeName {
    active(ctx).name
}
pub(crate) fn surround(ctx: &egui::Context) -> Surround {
    active(ctx).surround
}
/// egui 0.33 has no system reduced-motion flag; this is the Preferences switch.
pub(crate) fn reduced_motion(ctx: &egui::Context) -> bool {
    active(ctx).reduced_motion
}

/// Make a theme current: tokens in context data and egui's style.
pub(crate) fn apply(
    ctx: &egui::Context,
    name: ThemeName,
    surround: Surround,
    reduced_motion: bool,
) {
    let next = Active::new(name, surround, reduced_motion);
    ctx.data_mut(|data| data.insert_temp(active_id(), next));
    ctx.set_style(style(ctx, name, reduced_motion));
}

type StyleKey = (ThemeName, bool, u32, egui::FontFamily);
#[derive(Clone, Default)]
struct StyleCache(Vec<(StyleKey, Arc<egui::Style>)>);

/// The egui style for a theme, built once per theme, motion setting and
/// display scale and shared afterwards.
pub(crate) fn style(
    ctx: &egui::Context,
    name: ThemeName,
    reduced_motion: bool,
) -> Arc<egui::Style> {
    let strong = crate::studio_fonts::family(ctx, crate::studio_fonts::Face::Strong);
    let key: StyleKey = (
        name,
        reduced_motion,
        ctx.pixels_per_point().to_bits(),
        strong.clone(),
    );
    let id = egui::Id::new("studio-theme-styles");
    if let Some(style) = ctx.data(|data| {
        data.get_temp::<StyleCache>(id)
            .and_then(|cache| cache.0.into_iter().find(|(k, _)| *k == key))
            .map(|(_, style)| style)
    }) {
        return style;
    }
    let built = Arc::new(crate::theme::studio_style(
        &egui::Style::default(),
        &name.tokens(),
        1.0 / ctx.pixels_per_point(),
        reduced_motion,
        strong,
    ));
    ctx.data_mut(|data| {
        let cache = data.get_temp_mut_or_default::<StyleCache>(id);
        cache.0.retain(|(k, _)| k.2 == key.2 && k.3 == key.3);
        cache.0.push((key, built.clone()));
    });
    built
}

/// Draw `content` in another theme, then restore the current one. Used to
/// keep views that still paint with the Graphite constants legible on a light
/// theme until they read `tokens(ctx)`.
pub(crate) fn scoped<R>(ctx: &egui::Context, name: ThemeName, content: impl FnOnce() -> R) -> R {
    let saved = active(ctx);
    if saved.name == name {
        return content();
    }
    let saved_style = ctx.style();
    let scoped = Active::new(name, saved.surround, saved.reduced_motion);
    ctx.data_mut(|data| data.insert_temp(active_id(), scoped));
    ctx.set_style(style(ctx, name, saved.reduced_motion));
    let result = content();
    ctx.set_style(saved_style);
    ctx.data_mut(|data| data.insert_temp(active_id(), saved));
    result
}

#[cfg(test)]
#[path = "studio-theme-tests.rs"]
mod tests;
