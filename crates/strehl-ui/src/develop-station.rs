//! The Develop station (implementation plan 7.5; mockup `screens/develop.html`)
//! as self-contained parts for the Studio 2 shell: the tools strip, the
//! control strip for the active tool, the inspector (Adjust, Layers,
//! Versions) and the canvas overlays (crop, scale bar, depth brush, picker,
//! heal, note, split view). Each part takes its inputs as parameters and
//! returns intents; `EditorState::apply_develop` and the app apply them.
//!
//! Performance (5.2/5.4): nothing here reads files, decodes or scans pixels.
//! The histogram arrives from the preview worker; the split view's "before"
//! is one overview per photograph, developed and uploaded on a worker, so
//! dragging a slider never pays for a second settle or reveal.
#![allow(
    dead_code,
    reason = "the Studio 2 shell (P1) composes these parts; tests and the editor use them until then"
)]
#[path = "develop-layers.rs"]
pub(crate) mod layers;
#[path = "develop-style.rs"]
pub(crate) mod style;

use eframe::egui::{
    self, Align2, Color32, CornerRadius, Pos2, Rect, Response, Sense, Stroke, StrokeKind, Ui,
};
use layers::{LayerIntent, LayerRow};
use strehl_edit::{
    AdaptiveParameters, AdaptiveToneRange, Adjustments, Backdrop, BackdropKey, Crop,
    DevelopmentRecipe, Heal, ScaleBar, ScaleBarCorner, ScaleBarStyle,
};
use style::{ButtonKind, Icon, Number, StudioPalette};

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub(crate) enum DevelopTool {
    #[default]
    Move,
    Crop,
    WhiteBalance,
    DepthBrush,
    Heal,
    Backdrop,
    Region,
    ScaleBar,
    Note,
}

impl DevelopTool {
    /// Strip order; groups are separated by a hairline after 3 and 6.
    pub(crate) const ALL: [Self; 9] = [
        Self::Move,
        Self::Crop,
        Self::WhiteBalance,
        Self::DepthBrush,
        Self::Heal,
        Self::Backdrop,
        Self::Region,
        Self::ScaleBar,
        Self::Note,
    ];

    pub(crate) fn caption(self) -> &'static str {
        match self {
            Self::Move => "Move",
            Self::Crop => "Crop and straighten",
            Self::WhiteBalance => "White balance",
            Self::DepthBrush => "Depth brush",
            Self::Heal => "Heal",
            Self::Backdrop => "Backdrop",
            Self::Region => "Region",
            Self::ScaleBar => "Scale bar",
            Self::Note => "Note",
        }
    }

    pub(crate) fn hint(self) -> &'static str {
        match self {
            Self::Move => "Move and zoom",
            Self::Crop => "Crop and straighten",
            Self::WhiteBalance => "White balance picker",
            Self::DepthBrush => "Depth brush: take an area from other planes",
            Self::Heal => "Heal dust and fibres",
            Self::Backdrop => "Backdrop: clean the background",
            Self::Region => "Region: ellipse, rectangle, polygon, lasso, magic lasso",
            Self::ScaleBar => "Scale bar and labels",
            Self::Note => "Note for yourself or an agent",
        }
    }

    pub(crate) fn icon(self) -> Icon {
        match self {
            Self::Move => Icon::Move,
            Self::Crop => Icon::Crop,
            Self::WhiteBalance => Icon::Picker,
            Self::DepthBrush => Icon::Brush,
            Self::Heal => Icon::Heal,
            Self::Backdrop => Icon::Backdrop,
            Self::Region => Icon::Shape,
            Self::ScaleBar => Icon::Ruler,
            Self::Note => Icon::Note,
        }
    }

    pub(crate) fn key(self) -> egui::Key {
        match self {
            Self::Move => egui::Key::V,
            Self::Crop => egui::Key::C,
            Self::WhiteBalance => egui::Key::I,
            Self::DepthBrush => egui::Key::B,
            Self::Heal => egui::Key::J,
            Self::Backdrop => egui::Key::K,
            Self::Region => egui::Key::R,
            Self::ScaleBar => egui::Key::L,
            Self::Note => egui::Key::N,
        }
    }

    /// Tools whose pointer gestures belong to this module, not to panning or
    /// to the region editor.
    pub(crate) fn owns_canvas(self) -> bool {
        matches!(
            self,
            Self::Crop | Self::WhiteBalance | Self::DepthBrush | Self::Heal | Self::Note
        )
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum InspectorTab {
    #[default]
    Adjust,
    Layers,
    Versions,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Compare {
    #[default]
    After,
    Before,
    Split,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Surround {
    Black,
    #[default]
    Dark,
    Grey,
    White,
}

impl Surround {
    pub(crate) const ALL: [Self; 4] = [Self::Black, Self::Dark, Self::Grey, Self::White];

    pub(crate) fn colour(self) -> Color32 {
        match self {
            Self::Black => Color32::BLACK,
            Self::Dark => Color32::from_rgb(0x1c, 0x1c, 0x1c),
            Self::Grey => Color32::from_rgb(0x77, 0x77, 0x77),
            Self::White => Color32::WHITE,
        }
    }
}

/// A named Adaptive profile with its one-line description.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Look {
    pub name: &'static str,
    pub line: &'static str,
    pub parameters: AdaptiveParameters,
}

/// Today's Adaptive profiles as named looks, in the mockup's order.
pub(crate) fn looks() -> [Look; 6] {
    [
        Look {
            name: "Natural",
            line: "Natural: gentle local light and colour, close to the render.",
            parameters: AdaptiveParameters::default(),
        },
        Look {
            name: "Signature",
            line: "Signature: stronger local contrast and colour, shadows protected.",
            parameters: AdaptiveParameters::signature(),
        },
        Look {
            name: "Deep background",
            line: "Deep background: keeps a dark ground dark while the subject opens up.",
            parameters: AdaptiveParameters {
                balance: 0.35,
                shadow_protection: 0.85,
                ..Default::default()
            },
        },
        Look {
            name: "Texture",
            line: "Texture: separates midtone detail without sharpening pixels.",
            parameters: AdaptiveParameters {
                balance: 0.2,
                local_contrast: 0.8,
                color: 0.15,
                tone_range: AdaptiveToneRange::Midtones,
                shadow_protection: 0.6,
                ..Default::default()
            },
        },
        Look {
            name: "Gentle highlights",
            line: "Gentle highlights: compresses bright light; clipped detail stays clipped.",
            parameters: AdaptiveParameters {
                balance: 0.0,
                local_contrast: 0.25,
                color: 0.15,
                tone_range: AdaptiveToneRange::Highlights,
                shadow_protection: 1.0,
                highlight_compression: 0.65,
                ..Default::default()
            },
        },
        Look {
            name: "Gems and glints",
            line: "Gems and glints: tames small specular highlights, leaves large bright areas.",
            parameters: AdaptiveParameters {
                balance: 0.3,
                local_contrast: 0.4,
                color: 0.35,
                shadow_protection: 0.85,
                highlight_compression: 0.2,
                glint_compression: 0.85,
                ..Default::default()
            },
        },
    ]
}

/// The tone and colour controls of the Adjust tab.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum AdjustmentField {
    Exposure,
    Contrast,
    Highlights,
    Shadows,
    Whites,
    Blacks,
    Warmth,
    Tint,
    Vibrance,
    Saturation,
}

impl AdjustmentField {
    pub(crate) const LIGHT: [Self; 6] = [
        Self::Exposure,
        Self::Contrast,
        Self::Highlights,
        Self::Shadows,
        Self::Whites,
        Self::Blacks,
    ];
    pub(crate) const COLOUR: [Self; 4] =
        [Self::Warmth, Self::Tint, Self::Vibrance, Self::Saturation];

    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Exposure => "Exposure",
            Self::Contrast => "Contrast",
            Self::Highlights => "Highlights",
            Self::Shadows => "Shadows",
            Self::Whites => "Whites",
            Self::Blacks => "Blacks",
            Self::Warmth => "Warmth",
            Self::Tint => "Tint",
            Self::Vibrance => "Vibrance",
            Self::Saturation => "Saturation",
        }
    }

    pub(crate) fn range(self) -> std::ops::RangeInclusive<f32> {
        if self == Self::Exposure {
            -4.0..=4.0
        } else {
            -100.0..=100.0
        }
    }

    pub(crate) fn number(self) -> Number {
        if self == Self::Exposure {
            Number::Fixed2
        } else {
            Number::Signed
        }
    }

    pub(crate) fn get(self, a: &Adjustments) -> f32 {
        match self {
            Self::Exposure => a.exposure,
            Self::Contrast => a.contrast,
            Self::Highlights => a.highlights,
            Self::Shadows => a.shadows,
            Self::Whites => a.whites,
            Self::Blacks => a.blacks,
            Self::Warmth => a.temperature,
            Self::Tint => a.tint,
            Self::Vibrance => a.vibrance,
            Self::Saturation => a.saturation,
        }
    }

    pub(crate) fn set(self, a: &mut Adjustments, value: f32) {
        let (lo, hi) = if self == Self::Exposure {
            (-8.0, 8.0)
        } else {
            (-100.0, 100.0)
        };
        let value = if value.is_finite() {
            value.clamp(lo, hi)
        } else {
            0.0
        };
        match self {
            Self::Exposure => a.exposure = value,
            Self::Contrast => a.contrast = value,
            Self::Highlights => a.highlights = value,
            Self::Shadows => a.shadows = value,
            Self::Whites => a.whites = value,
            Self::Blacks => a.blacks = value,
            Self::Warmth => a.temperature = value,
            Self::Tint => a.tint = value,
            Self::Vibrance => a.vibrance = value,
            Self::Saturation => a.saturation = value,
        }
    }
}

/// Luminance histogram of the developed overview, computed on the preview
/// worker from a small SDR rendering. 64 bins of coded display luminance.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Histogram {
    pub bins: Vec<u32>,
    pub peak: u32,
    /// Fraction of samples below 1 % of white.
    pub shadows: f32,
    /// Fraction of samples at or above 99 % of white.
    pub highlights: f32,
}

impl Histogram {
    pub(crate) const BINS: usize = 64;

    pub(crate) fn from_rgb8(rgb: &[u8]) -> Self {
        let mut bins = vec![0u32; Self::BINS];
        let (mut dark, mut bright, mut count) = (0u64, 0u64, 0u64);
        for p in rgb.as_chunks::<3>().0 {
            let y = 0.2126 * f32::from(p[0]) + 0.7152 * f32::from(p[1]) + 0.0722 * f32::from(p[2]);
            let bin =
                ((y / 255.0) * Self::BINS as f32).clamp(0.0, Self::BINS as f32 - 1.0) as usize;
            bins[bin] += 1;
            dark += u64::from(y < 2.55);
            bright += u64::from(y >= 252.45);
            count += 1;
        }
        let n = count.max(1) as f32;
        Self {
            peak: bins.iter().copied().max().unwrap_or(0),
            bins,
            shadows: dark as f32 / n,
            highlights: bright as f32 / n,
        }
    }

    /// The mockup's caption, for example `shadows 38 % below 1 %`.
    pub(crate) fn caption(&self) -> String {
        if self.highlights >= 0.001 {
            format!("highlights {:.1} % at white", self.highlights * 100.0)
        } else {
            format!("shadows {:.0} % below 1 %", self.shadows * 100.0)
        }
    }
}

/// A saved version, as the Versions tab lists it.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct VersionRow {
    pub id: String,
    pub name: String,
    pub detail: String,
    pub current: bool,
}

/// What the station shows about a depth repair.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct RepairView {
    /// Repairs in the recipe that the master does not hold.
    pub pending: bool,
    /// The background re-stack, for example `Rebuilding · 12 s`.
    pub running: Option<String>,
}

/// Everything the Develop parts read. Built by the caller each frame from
/// state it already holds; nothing here is computed.
pub(crate) struct DevelopView<'a> {
    pub palette: &'a StudioPalette,
    pub recipe: &'a DevelopmentRecipe,
    /// The selected region; `None` adjusts the whole photograph.
    pub scope: Option<&'a str>,
    pub histogram: Option<&'a Histogram>,
    /// The look applied to the current scope, if it is one of `looks()`.
    pub look: Option<usize>,
    /// Amount of the scope's Adaptive field, if it has one.
    pub look_amount: Option<f32>,
    pub look_busy: bool,
    pub versions: &'a [VersionRow],
    pub render: &'a str,
    pub repair: RepairView,
    /// Planes in the stack, for the depth brush's range.
    pub planes: Option<usize>,
    /// The subject's scale calibration, micrometres per source pixel.
    pub um_per_px: Option<f64>,
    pub image_size: [u32; 2],
    pub hdr_photo: bool,
    /// The display can show HDR now (the presenter is active).
    pub hdr_available: bool,
    /// The photograph is presented in HDR (not switched to SDR).
    pub hdr_display: bool,
    /// What the display reports: state, monitor, reason, luminance.
    pub display: Vec<String>,
    pub can_export: bool,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum DevelopIntent {
    SelectTool(DevelopTool),
    SetCompare(Compare),
    SetSurround(Surround),
    SetHdr(bool),
    /// The HDR photograph's peak and reference white, in nits.
    SetHdrLuminance {
        peak_nits: f32,
        reference_white_nits: f32,
    },
    ToggleClipping,
    SetBrush {
        size_px: f32,
        feather: f32,
    },
    /// The Region tool's shape: 0 select, 1 ellipse, 2 rectangle, 3 polygon,
    /// 4 lasso, 5 magic lasso.
    RegionDrawing(usize),
    SetScope(Option<String>),
    Adjust(AdjustmentField, f32),
    PickLook(usize),
    /// Double-click on the chosen look: back to that look's parameters.
    ResetToLook(usize),
    Recalculate,
    SetLookAmount(f32),
    /// Arm the white-balance picker.
    PickNeutral,
    /// The picker clicked here (normalized photograph coordinates).
    SampleNeutral([f32; 2]),
    SetCrop(Option<Crop>),
    SetScaleBar(Option<ScaleBar>),
    PaintStroke {
        points: Vec<[f32; 2]>,
        radius: [f32; 2],
        feather: f32,
    },
    /// Planes (zero-based, inclusive) the depth brush takes from.
    SetRepairRange(usize, usize),
    StartRepair,
    AddHeal(Heal),
    SetBackdrop(Option<Backdrop>),
    AddNote([f32; 2]),
    Layer(LayerIntent),
    OpenVersion(String),
    CarryVersion(String),
    SaveVersion,
    Export,
}

/// The depth rail. The Stack station provides the real one (P3); until
/// then `RangeFallback` offers two plane fields.
pub(crate) trait DepthRail {
    /// Show the rail for the painted area and return a new range, if chosen.
    fn show(
        &mut self,
        ui: &mut Ui,
        palette: &StudioPalette,
        range: (usize, usize),
        planes: usize,
    ) -> Option<(usize, usize)>;
}

/// Two plane fields, counted from 1 as on screen.
pub(crate) struct RangeFallback;

impl DepthRail for RangeFallback {
    fn show(
        &mut self,
        ui: &mut Ui,
        palette: &StudioPalette,
        range: (usize, usize),
        planes: usize,
    ) -> Option<(usize, usize)> {
        let planes = planes.max(1);
        let (mut first, mut last) = (range.0 + 1, range.1 + 1);
        style::text(ui, "Take from", style::BODY, palette.ink_2);
        let a = ui.add(
            egui::DragValue::new(&mut first)
                .range(1..=planes)
                .prefix("planes "),
        );
        style::text(ui, "\u{2013}", style::BODY, palette.ink_2);
        let b = ui.add(egui::DragValue::new(&mut last).range(1..=planes));
        if a.changed() || b.changed() {
            let (lo, hi) = (first.min(last), first.max(last));
            return Some((lo - 1, hi - 1));
        }
        None
    }
}

/// Default planes for a new repair: the middle fifth of the stack.
pub(crate) fn default_range(planes: usize) -> (usize, usize) {
    let planes = planes.max(1);
    let span = (planes / 5).max(1);
    let first = (planes - span) / 2;
    (first, (first + span - 1).min(planes - 1))
}

// ---------------------------------------------------------------- tools strip

/// The tools column (44 px). The shell fills and rules the panel.
pub(crate) fn tools_strip(
    ui: &mut Ui,
    palette: &StudioPalette,
    active: DevelopTool,
) -> Option<DevelopTool> {
    let mut chosen = None;
    let rect = ui.available_rect_before_wrap();
    let mut y = rect.top() + 8.0;
    for (i, tool) in DevelopTool::ALL.into_iter().enumerate() {
        if i == 3 || i == 6 {
            style::hairline(
                ui.painter(),
                egui::pos2(rect.center().x - 9.0, y + 6.0),
                egui::pos2(rect.center().x + 9.0, y + 6.0),
                palette.line,
            );
            y += 13.0;
        }
        let cell = Rect::from_center_size(
            egui::pos2(rect.center().x, y + 16.0),
            egui::vec2(32.0, 32.0),
        );
        let response = ui
            .interact(cell, ui.id().with(("develop-tool", tool)), Sense::click())
            .on_hover_text(format!("{} · {:?}", tool.hint(), tool.key()));
        let on = tool == active;
        if on {
            ui.painter()
                .rect_filled(cell, CornerRadius::ZERO, palette.accent_soft);
            ui.painter().rect_filled(
                Rect::from_min_max(
                    egui::pos2(cell.left() - 6.0, cell.top() + 6.0),
                    egui::pos2(cell.left() - 4.0, cell.bottom() - 6.0),
                ),
                CornerRadius::ZERO,
                palette.accent,
            );
        }
        let colour = if on {
            palette.accent
        } else if response.hovered() {
            palette.ink
        } else {
            palette.ink_3
        };
        style::icon(ui.painter(), cell.shrink(7.5), tool.icon(), colour);
        if response.clicked() {
            chosen = Some(tool);
        }
        y += 34.0;
    }
    chosen
}

/// Tool keys, honoured only when no text field has focus.
pub(crate) fn tool_shortcut(ctx: &egui::Context) -> Option<DevelopTool> {
    if ctx.wants_keyboard_input() {
        return None;
    }
    ctx.input(|i| {
        if i.modifiers.any() {
            return None;
        }
        DevelopTool::ALL
            .into_iter()
            .find(|tool| i.key_pressed(tool.key()))
    })
}

/// The other Develop keys: `[` and `]` size the brush, `\` toggles before
/// and after.
pub(crate) fn view_shortcuts(ctx: &egui::Context, canvas: &DevelopCanvas) -> Vec<DevelopIntent> {
    if ctx.wants_keyboard_input() {
        return Vec::new();
    }
    ctx.input(|i| {
        let mut out = Vec::new();
        if i.modifiers.any() {
            return out;
        }
        let size = if canvas.tool == DevelopTool::Heal {
            canvas.heal_px
        } else {
            canvas.brush_px
        };
        for (key, factor) in [
            (egui::Key::OpenBracket, 0.8),
            (egui::Key::CloseBracket, 1.25),
        ] {
            if i.key_pressed(key) {
                out.push(DevelopIntent::SetBrush {
                    size_px: (size * factor).round().clamp(4.0, 240.0),
                    feather: canvas.brush_feather,
                });
            }
        }
        if i.key_pressed(egui::Key::Backslash) {
            out.push(DevelopIntent::SetCompare(
                if canvas.compare == Compare::Before {
                    Compare::After
                } else {
                    Compare::Before
                },
            ));
        }
        out
    })
}

// -------------------------------------------------------------- control strip

/// The 36 px strip above the canvas, drawn into the shell's row (a
/// left-to-right layout already inset): the tool's options at the left, the
/// view controls (compare, surround, HDR, clipping) at the right.
pub(crate) fn control_strip(
    ui: &mut Ui,
    view: &DevelopView<'_>,
    canvas: &DevelopCanvas,
) -> Vec<DevelopIntent> {
    let pal = view.palette;
    let mut intents = Vec::new();
    ui.spacing_mut().item_spacing.x = 14.0;
    style::caps(ui, canvas.tool.caption(), style::CAPS, pal.accent);
    vr(ui, pal);
    ui.spacing_mut().item_spacing.x = 10.0;
    match canvas.tool {
        DevelopTool::DepthBrush => {
            style::text(ui, "Size", 12.5, pal.ink_2);
            let size = style::inline_slider(ui, pal, canvas.brush_px, 4.0..=240.0, 80.0);
            style::text(ui, "Feather", 12.5, pal.ink_2);
            let feather = style::inline_slider(ui, pal, canvas.brush_feather, 0.0..=1.0, 80.0);
            if size.value.is_some() || feather.value.is_some() {
                intents.push(DevelopIntent::SetBrush {
                    size_px: size.value.map_or(canvas.brush_px, f32::round),
                    feather: feather.value.unwrap_or(canvas.brush_feather),
                });
            }
            if let Some(planes) = view.planes {
                let (first, last) = canvas.repair_range.unwrap_or_else(|| default_range(planes));
                style::text(ui, "Take from", 12.5, pal.ink_2);
                style::strong(ui, &layers::plane_range(first, last), 12.5, pal.accent);
                style::text(ui, "drag on the rail to change", 12.5, pal.ink_3);
            } else {
                style::text(
                    ui,
                    "Open the stack's planes to choose where to take from",
                    12.5,
                    pal.ink_3,
                );
            }
            if let Some(running) = &view.repair.running {
                style::text(ui, running, 12.5, pal.ink_2);
            } else if view.repair.pending
                && style::button(
                    ui,
                    pal,
                    "Rebuild now",
                    ButtonKind::Plain,
                    egui::vec2(92.0, 22.0),
                    true,
                )
                .on_hover_text("Re-stack the painted areas from their planes in the background")
                .clicked()
            {
                intents.push(DevelopIntent::StartRepair);
            }
        }
        DevelopTool::Crop => {
            let angle = view.recipe.crop.map_or(0.0, |c| c.angle_deg);
            style::text(ui, "Straighten", 12.5, pal.ink_2);
            let out = style::inline_slider(ui, pal, angle, -45.0..=45.0, 160.0);
            style::text(ui, &format!("{angle:+.1}°"), 12.5, pal.ink);
            if let Some(value) = out.value {
                let crop = view.recipe.crop.unwrap_or(Crop {
                    min: [0.0, 0.0],
                    max: [1.0, 1.0],
                    angle_deg: 0.0,
                });
                let turned = Crop {
                    angle_deg: (value * 10.0).round() / 10.0,
                    ..crop
                };
                intents.push(DevelopIntent::SetCrop(Some(
                    turned.fit_inside(view.image_size[0].max(1), view.image_size[1].max(1)),
                )));
            }
            if let Some(crop) = view.recipe.crop {
                let [w, h] = crop.output_size(view.image_size[0].max(1), view.image_size[1].max(1));
                style::text(ui, &format!("{w} × {h}"), 12.5, pal.ink_3);
                if style::link(ui, pal, "Reset", false).clicked() {
                    intents.push(DevelopIntent::SetCrop(None));
                }
            } else {
                style::text(
                    ui,
                    "drag the frame's edges on the photograph",
                    12.5,
                    pal.ink_3,
                );
            }
        }
        DevelopTool::WhiteBalance => {
            style::text(
                ui,
                "Click something neutral · warmth and tint stop at a factor of 2",
                12.5,
                pal.ink_2,
            );
        }
        DevelopTool::Heal => {
            style::text(ui, "Size", 12.5, pal.ink_2);
            let size = style::inline_slider(ui, pal, canvas.heal_px, 4.0..=200.0, 80.0);
            if let Some(value) = size.value {
                intents.push(DevelopIntent::SetBrush {
                    size_px: value.round(),
                    feather: canvas.brush_feather,
                });
            }
            style::text(
                ui,
                "click a spot · its source is taken beside it",
                12.5,
                pal.ink_3,
            );
        }
        DevelopTool::Backdrop => {
            let current = view.recipe.backdrop.unwrap_or(Backdrop {
                threshold: 0.012,
                softness: 1.0,
                key: BackdropKey::Dark,
                enabled: true,
            });
            let key = style::seg(
                ui,
                pal,
                &["Dark ground", "Light ground"],
                Some(usize::from(current.key == BackdropKey::Light)),
            );
            style::text(ui, "Level", 12.5, pal.ink_2);
            // Logarithmic: 0.1 % to 100 % of white.
            let level = style::inline_slider(
                ui,
                pal,
                (current.threshold * 1000.0).log10(),
                0.0..=3.0,
                100.0,
            );
            style::text(
                ui,
                &format!("{:.1} %", current.threshold * 100.0),
                12.5,
                pal.ink,
            );
            style::text(ui, "Soft edge", 12.5, pal.ink_2);
            let soft = style::inline_slider(ui, pal, current.softness, 0.0..=4.0, 80.0);
            let mut next = current;
            if let Some(k) = key {
                next.key = if k == 0 {
                    BackdropKey::Dark
                } else {
                    BackdropKey::Light
                };
            }
            if let Some(v) = level.value {
                next.threshold = (10f32.powf(v) / 1000.0).clamp(0.001, 1.0);
            }
            if let Some(v) = soft.value {
                next.softness = (v * 10.0).round() / 10.0;
            }
            if next != current || (view.recipe.backdrop.is_none() && key.is_some()) {
                intents.push(DevelopIntent::SetBackdrop(Some(next)));
            }
            if view.recipe.backdrop.is_some() && style::link(ui, pal, "Remove", false).clicked() {
                intents.push(DevelopIntent::SetBackdrop(None));
            }
        }
        DevelopTool::ScaleBar => {
            let bar = view.recipe.scale_bar.unwrap_or(ScaleBar {
                length_um: view.um_per_px.map_or(1000.0, |um| {
                    ScaleBar::suggested_length_um(um, view.image_size[0])
                }),
                corner: ScaleBarCorner::BottomRight,
                style: ScaleBarStyle::Light,
                enabled: true,
            });
            let mut next = bar;
            let mut length = bar.length_um;
            style::text(ui, "Length", 12.5, pal.ink_2);
            if ui
                .add(
                    egui::DragValue::new(&mut length)
                        .range(0.1..=100_000.0)
                        .suffix(" µm"),
                )
                .changed()
            {
                next.length_um = length;
            }
            let corners = [
                ScaleBarCorner::TopLeft,
                ScaleBarCorner::TopRight,
                ScaleBarCorner::BottomLeft,
                ScaleBarCorner::BottomRight,
            ];
            if let Some(i) = style::seg(
                ui,
                pal,
                &["Top left", "Top right", "Bottom left", "Bottom right"],
                corners.iter().position(|c| *c == bar.corner),
            ) {
                next.corner = corners[i];
            }
            if let Some(i) = style::seg(
                ui,
                pal,
                &["Light", "Dark"],
                Some(usize::from(bar.style == ScaleBarStyle::Dark)),
            ) {
                next.style = if i == 0 {
                    ScaleBarStyle::Light
                } else {
                    ScaleBarStyle::Dark
                };
            }
            if next != bar || view.recipe.scale_bar.is_none() {
                intents.push(DevelopIntent::SetScaleBar(Some(next)));
            }
            style::text(
                ui,
                &match view.um_per_px {
                    Some(um) => format!("{um:.3} µm per pixel from the subject"),
                    None => "No scale calibration for this subject".into(),
                },
                12.5,
                if view.um_per_px.is_some() {
                    pal.ink_3
                } else {
                    pal.warn
                },
            );
        }
        DevelopTool::Note => {
            style::text(
                ui,
                "Click to pin a note; edit its text in Layers",
                12.5,
                pal.ink_2,
            );
        }
        DevelopTool::Region => {
            if let Some(i) = style::seg(
                ui,
                pal,
                &[
                    "Select",
                    "Ellipse",
                    "Rectangle",
                    "Polygon",
                    "Lasso",
                    "Magic lasso",
                ],
                Some(canvas.region_drawing),
            ) {
                intents.push(DevelopIntent::RegionDrawing(i));
            }
        }
        DevelopTool::Move => {
            style::text(
                ui,
                "Drag to move · scroll to zoom · double-click to fit",
                12.5,
                pal.ink_3,
            );
        }
    }
    // View controls, right-aligned; the order on screen is left to right.
    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
        ui.spacing_mut().item_spacing.x = 14.0;
        if style::toggle_button(ui, pal, "Clipping", canvas.clipping)
            .on_hover_text("Mark the developed photograph's pure black and pure white")
            .clicked()
        {
            intents.push(DevelopIntent::ToggleClipping);
        }
        // Shown only where it changes something: an HDR photograph on an
        // HDR display.
        if view.hdr_photo
            && view.hdr_available
            && let Some(i) = style::seg(
                ui,
                pal,
                &["HDR", "SDR"],
                Some(usize::from(!view.hdr_display)),
            )
        {
            intents.push(DevelopIntent::SetHdr(i == 0));
        }
        if let Some(s) = swatches(ui, pal, canvas.surround) {
            intents.push(DevelopIntent::SetSurround(s));
        }
        let compare = [Compare::After, Compare::Before, Compare::Split];
        // Right to left: the segments are listed in reverse.
        if let Some(i) = style::seg(
            ui,
            pal,
            &["After", "Before", "Split"],
            compare.iter().position(|c| *c == canvas.compare),
        ) {
            intents.push(DevelopIntent::SetCompare(compare[i]));
        }
    });
    intents
}

fn vr(ui: &mut Ui, pal: &StudioPalette) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(1.0, 20.0), Sense::hover());
    style::hairline(
        ui.painter(),
        rect.center_top(),
        rect.center_bottom(),
        pal.line,
    );
}

fn swatches(ui: &mut Ui, pal: &StudioPalette, current: Surround) -> Option<Surround> {
    let mut chosen = None;
    let (rect, _) =
        ui.allocate_exact_size(egui::vec2(4.0 * 14.0 + 3.0 * 3.0, 14.0), Sense::hover());
    for (i, surround) in Surround::ALL.into_iter().enumerate() {
        let cell = Rect::from_min_size(
            egui::pos2(rect.left() + i as f32 * 17.0, rect.top()),
            egui::vec2(14.0, 14.0),
        );
        let response = ui
            .interact(cell, ui.id().with(("surround", i)), Sense::click())
            .on_hover_text(match surround {
                Surround::Black => "Black surround",
                Surround::Dark => "Dark surround",
                Surround::Grey => "Mid-grey surround",
                Surround::White => "White surround",
            });
        ui.painter()
            .rect_filled(cell, CornerRadius::ZERO, surround.colour());
        if surround == current {
            ui.painter().rect_stroke(
                cell,
                CornerRadius::ZERO,
                Stroke::new(1.5_f32, pal.accent),
                StrokeKind::Outside,
            );
        } else {
            ui.painter().rect_stroke(
                cell,
                CornerRadius::ZERO,
                Stroke::new(1.0_f32, pal.line_2),
                StrokeKind::Inside,
            );
        }
        if response.clicked() {
            chosen = Some(surround);
        }
    }
    chosen
}

// ----------------------------------------------------------------------- rail

/// The rail slot while the depth brush is out: its head and the planes the
/// painted area takes from. The Stack station's depth rail (P3) replaces
/// `RangeFallback` through `DepthRail`; this head and the range stay.
pub(crate) fn depth_rail(
    ui: &mut Ui,
    view: &DevelopView<'_>,
    canvas: &DevelopCanvas,
    rail: &mut dyn DepthRail,
) -> Vec<DevelopIntent> {
    let pal = view.palette;
    let mut intents = Vec::new();
    let rect = ui.max_rect();
    let head = Rect::from_min_size(rect.min, egui::vec2(rect.width(), 30.0));
    let mut head_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(head.shrink2(egui::vec2(14.0, 0.0)))
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
    );
    head_ui.spacing_mut().item_spacing.x = 16.0;
    style::caps(&mut head_ui, "Depth rail", style::CAPS, pal.ink);
    style::text(
        &mut head_ui,
        "planes the painted area takes from",
        style::SMALL,
        pal.ink_3,
    );
    head_ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
        style::text(
            ui,
            "the sharpness trace arrives with the Stack station's rail",
            style::SMALL,
            pal.ink_3,
        );
    });
    let body = Rect::from_min_max(egui::pos2(rect.left() + 14.0, head.bottom()), rect.max);
    let mut body_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(body)
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
    );
    body_ui.spacing_mut().item_spacing.x = 8.0;
    match view.planes {
        Some(planes) => {
            let range = canvas.repair_range.unwrap_or_else(|| default_range(planes));
            if let Some((first, last)) = rail.show(&mut body_ui, pal, range, planes) {
                intents.push(DevelopIntent::SetRepairRange(first, last));
            }
            style::text(
                &mut body_ui,
                &format!("of {planes}"),
                style::SMALL,
                pal.ink_3,
            );
        }
        None => {
            style::text(
                &mut body_ui,
                "Open this photograph's stack to choose its planes.",
                style::SMALL,
                pal.ink_3,
            );
        }
    }
    intents
}

// ------------------------------------------------------------------ inspector

/// Inspector state that belongs to the panel, not the photograph.
#[derive(Clone, Debug, Default)]
pub(crate) struct DevelopPanel {
    pub tab: InspectorTab,
    /// Detail, Crop and straighten, Display; then the app's Saved looks and
    /// Source evidence groups.
    pub groups: [bool; 6],
}

/// The tabs' captions: Adjust, Layers · n, Versions · n.
pub(crate) fn tab_labels(
    view: &DevelopView<'_>,
    layer_rows: &[LayerRow],
) -> [(InspectorTab, String); 3] {
    [
        (InspectorTab::Adjust, "Adjust".to_owned()),
        (
            InspectorTab::Layers,
            format!("Layers · {}", layer_rows.len()),
        ),
        (
            InspectorTab::Versions,
            format!("Versions · {}", view.versions.len()),
        ),
    ]
}

/// A foldable group's head in the Adjust tab: chevron, title, summary, rule.
pub(crate) fn group_header(
    ui: &mut Ui,
    pal: &StudioPalette,
    title: &str,
    summary: &str,
    open: bool,
) -> egui::Response {
    let width = ui.available_width();
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 34.0), Sense::click());
    let painter = ui.painter();
    style::hairline(painter, rect.left_bottom(), rect.right_bottom(), pal.line);
    let chevron = Rect::from_center_size(
        egui::pos2(rect.left() + 5.0, rect.center().y),
        egui::vec2(11.0, 11.0),
    );
    style::icon(
        painter,
        chevron,
        Icon::Chevron,
        if open { pal.accent } else { pal.ink_3 },
    );
    style::paint_strong(
        painter,
        egui::pos2(rect.left() + 19.0, rect.center().y),
        Align2::LEFT_CENTER,
        title,
        style::BODY,
        if response.hovered() {
            pal.accent
        } else {
            pal.ink
        },
    );
    style::paint_text(
        painter,
        rect.right_center(),
        Align2::RIGHT_CENTER,
        summary,
        style::SMALL,
        pal.ink_3,
    );
    response
}

/// Display: what the screen reports, and an HDR photograph's luminance.
fn display_group(ui: &mut Ui, view: &DevelopView<'_>, intents: &mut Vec<DevelopIntent>) {
    let pal = view.palette;
    for (i, line) in view.display.iter().enumerate() {
        style::text(
            ui,
            line,
            style::SMALL,
            if i == 0 { pal.ink } else { pal.ink_3 },
        );
    }
    if !view.hdr_photo {
        style::text(
            ui,
            "This saved image has no HDR highlight data. A new stack keeps the RAW-derived HDR master.",
            style::SMALL,
            pal.ink_2,
        );
        return;
    }
    let hdr = view.recipe.hdr;
    let width = ui.available_width();
    let peak = style::slider(
        ui,
        pal,
        "Peak brightness",
        hdr.peak_nits,
        hdr.reference_white_nits..=10_000.0,
        1000.0,
        style::Number::Whole,
        width,
    );
    let max_white = hdr.peak_nits.min(500.0);
    let white = style::slider(
        ui,
        pal,
        "Reference white",
        hdr.reference_white_nits,
        80.0..=max_white,
        203.0_f32.min(max_white),
        style::Number::Whole,
        width,
    );
    if peak.value.is_some() || white.value.is_some() {
        intents.push(DevelopIntent::SetHdrLuminance {
            peak_nits: peak.value.unwrap_or(hdr.peak_nits).round(),
            reference_white_nits: white.value.unwrap_or(hdr.reference_white_nits).round(),
        });
    }
}

/// The open tab's contents, for a caller that pads and scrolls them.
pub(crate) fn tab_contents(
    ui: &mut Ui,
    panel: &mut DevelopPanel,
    view: &DevelopView<'_>,
    layer_rows: &[LayerRow],
) -> Vec<DevelopIntent> {
    let mut intents = Vec::new();
    match panel.tab {
        InspectorTab::Adjust => adjust_tab(ui, panel, view, layer_rows, &mut intents),
        InspectorTab::Layers => {
            let status = view.repair.running.as_deref();
            intents.extend(
                layers::layers_panel(ui, view.palette, layer_rows, view.scope, status)
                    .into_iter()
                    .map(DevelopIntent::Layer),
            );
        }
        InspectorTab::Versions => versions_tab(ui, view, &mut intents),
    }
    intents
}

/// The tab's body, padded and scrolling, for the shell's inspector body.
pub(crate) fn inspector_body(
    ui: &mut Ui,
    panel: &mut DevelopPanel,
    view: &DevelopView<'_>,
    layer_rows: &[LayerRow],
) -> Vec<DevelopIntent> {
    let mut intents = Vec::new();
    let rect = ui.max_rect();
    let body = Rect::from_min_max(
        egui::pos2(rect.left() + 16.0, rect.top() + 14.0),
        egui::pos2(rect.right() - 16.0, rect.bottom() - 8.0),
    );
    let mut body_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(body)
            .layout(egui::Layout::top_down(egui::Align::Min)),
    );
    egui::ScrollArea::vertical()
        .id_salt("develop-inspector")
        .auto_shrink([false, false])
        .show(&mut body_ui, |ui| {
            ui.spacing_mut().item_spacing.y = 9.0;
            intents = tab_contents(ui, panel, view, layer_rows);
        });
    intents
}

/// The foot: Export… and Save version, into the shell's footer row.
pub(crate) fn inspector_footer(ui: &mut Ui, view: &DevelopView<'_>) -> Vec<DevelopIntent> {
    let pal = view.palette;
    let mut intents = Vec::new();
    let save_width = 92.0;
    let export_width = (ui.available_width() - save_width - 8.0).max(80.0);
    let export = style::button(
        ui,
        pal,
        "Export…",
        ButtonKind::Primary,
        egui::vec2(export_width, 28.0),
        view.can_export,
    );
    // The mockup's chevron: Export is the next station.
    style::icon(
        ui.painter(),
        Rect::from_center_size(
            egui::pos2(export.rect.right() - 16.0, export.rect.center().y),
            egui::vec2(12.0, 12.0),
        ),
        Icon::Chevron,
        if view.can_export {
            pal.accent_ink
        } else {
            pal.ink_3
        },
    );
    if export.clicked() {
        intents.push(DevelopIntent::Export);
    }
    if style::button(
        ui,
        pal,
        "Save version",
        ButtonKind::Plain,
        egui::vec2(save_width, 28.0),
        true,
    )
    .clicked()
    {
        intents.push(DevelopIntent::SaveVersion);
    }
    intents
}

/// Tabs, body and foot together: the whole 348 px inspector, for callers
/// without the shell (tests, a floating panel).
pub(crate) fn inspector(
    ui: &mut Ui,
    panel: &mut DevelopPanel,
    view: &DevelopView<'_>,
    layer_rows: &[LayerRow],
) -> Vec<DevelopIntent> {
    let pal = view.palette;
    let full = ui.available_rect_before_wrap();
    ui.painter()
        .rect_filled(full, CornerRadius::ZERO, pal.panel);
    let labels = tab_labels(view, layer_rows);
    let names: Vec<String> = labels.iter().map(|(_, l)| l.clone()).collect();
    let tab = labels
        .iter()
        .position(|(t, _)| *t == panel.tab)
        .unwrap_or(0);
    if let Some(i) = style::tabs(ui, pal, &names, tab) {
        panel.tab = labels[i].0;
    }
    let foot_height = 53.0;
    let body = Rect::from_min_max(
        egui::pos2(full.left(), full.top() + 36.0),
        egui::pos2(full.right(), full.bottom() - foot_height),
    );
    let mut body_ui = ui.new_child(egui::UiBuilder::new().max_rect(body));
    let mut intents = inspector_body(&mut body_ui, panel, view, layer_rows);
    let foot = Rect::from_min_max(
        egui::pos2(full.left(), full.bottom() - foot_height),
        full.max,
    );
    style::hairline(ui.painter(), foot.left_top(), foot.right_top(), pal.line);
    let mut foot_ui = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(foot.shrink2(egui::vec2(16.0, 12.0)))
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
    );
    foot_ui.spacing_mut().item_spacing.x = 8.0;
    intents.extend(inspector_footer(&mut foot_ui, view));
    ui.advance_cursor_after_rect(full);
    intents
}

fn adjust_tab(
    ui: &mut Ui,
    panel: &mut DevelopPanel,
    view: &DevelopView<'_>,
    layer_rows: &[LayerRow],
    intents: &mut Vec<DevelopIntent>,
) {
    let pal = view.palette;
    // Scope: Whole photograph or a named layer.
    ui.horizontal(|ui| {
        style::caps(ui, "Adjusting", style::CAPS, pal.ink_3);
        let mut names = vec!["Whole photograph"];
        let mut ids: Vec<Option<&str>> = vec![None];
        for row in layer_rows {
            if let layers::LayerId::Region(id) = &row.id
                && row.kind == layers::LayerKind::Region
            {
                names.push(&row.title);
                ids.push(Some(id));
            }
        }
        let selected = ids.iter().position(|id| *id == view.scope);
        if let Some(i) = style::seg(ui, pal, &names, selected) {
            intents.push(DevelopIntent::SetScope(ids[i].map(str::to_owned)));
        }
    });
    if view
        .scope
        .is_some_and(|id| !view.recipe.regions.iter().any(|r| r.id == id))
    {
        intents.push(DevelopIntent::SetScope(None));
    }
    histogram(ui, pal, view.histogram);
    style::sect(ui, pal, "Look", Some("measured from this photograph"));
    let all = looks();
    if let Some(event) = look_grid(ui, pal, &all, view.look, !view.look_busy) {
        intents.push(event);
    }
    let line = view
        .look
        .map(|i| all[i].line)
        .unwrap_or("Choose a look to measure this photograph and apply it.");
    style::text(ui, line, style::SMALL, pal.ink_2);
    if let Some(amount) = view.look_amount {
        let width = ui.available_width();
        let out = style::slider(
            ui,
            pal,
            "Amount",
            amount,
            0.0..=1.0,
            1.0,
            Number::Fixed2,
            width,
        );
        if let Some(value) = out.value {
            intents.push(DevelopIntent::SetLookAmount(value));
        }
        if style::link(ui, pal, "Recalculate", false).clicked() {
            intents.push(DevelopIntent::Recalculate);
        }
    }
    let adjustments = view
        .scope
        .and_then(|id| view.recipe.regions.iter().find(|r| r.id == id))
        .map_or(view.recipe.global, |r| r.adjustments);
    style::sect(ui, pal, "Light", None);
    two_columns(ui, pal, &AdjustmentField::LIGHT, &adjustments, intents);
    ui.horizontal(|ui| {
        style::caps(ui, "Colour", style::CAPS, pal.ink_3);
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if style::button(
                ui,
                pal,
                "Pick neutral",
                ButtonKind::Quiet,
                egui::vec2(92.0, 22.0),
                true,
            )
            .on_hover_text(
                "Click something neutral in the photograph. Warmth and tint stop at a factor of 2.",
            )
            .clicked()
            {
                intents.push(DevelopIntent::PickNeutral);
            }
        });
    });
    style::hairline(
        ui.painter(),
        ui.cursor().left_top(),
        egui::pos2(ui.max_rect().right(), ui.cursor().top()),
        pal.line,
    );
    two_columns(ui, pal, &AdjustmentField::COLOUR, &adjustments, intents);
    let crop = view.recipe.crop;
    let groups = [
        ("Detail", "sharpening on export".to_owned()),
        (
            "Crop and straighten",
            crop.map_or("whole photograph · 0.0°".into(), |c| {
                let [w, h] = c.output_size(view.image_size[0].max(1), view.image_size[1].max(1));
                format!("{w} × {h} · {:.1}°", c.angle_deg)
            }),
        ),
        (
            "Display",
            if view.hdr_photo {
                format!("HDR · peak {:.0} nits", view.recipe.hdr.peak_nits)
            } else {
                "SDR photograph".into()
            },
        ),
    ];
    for (i, (title, summary)) in groups.iter().enumerate() {
        if group_header(ui, pal, title, summary, panel.groups[i]).clicked() {
            panel.groups[i] = !panel.groups[i];
        }
        if panel.groups[i] && i == 2 {
            display_group(ui, view, intents);
        }
        if panel.groups[i] && i == 1 {
            if style::link(ui, pal, "Choose the crop tool", false).clicked() {
                intents.push(DevelopIntent::SelectTool(DevelopTool::Crop));
            }
            if crop.is_some() && style::link(ui, pal, "Reset crop", false).clicked() {
                intents.push(DevelopIntent::SetCrop(None));
            }
        }
        if panel.groups[i] && i == 0 {
            style::text(
                ui,
                "Output sharpening belongs to each export preset, judged at its size.",
                style::SMALL,
                pal.ink_2,
            );
        }
    }
}

fn two_columns(
    ui: &mut Ui,
    pal: &StudioPalette,
    fields: &[AdjustmentField],
    adjustments: &Adjustments,
    intents: &mut Vec<DevelopIntent>,
) {
    let gap = 18.0;
    let width = ((ui.available_width() - gap) * 0.5).floor();
    for pair in fields.chunks(2) {
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = gap;
            for field in pair {
                let out = style::slider(
                    ui,
                    pal,
                    field.label(),
                    field.get(adjustments),
                    field.range(),
                    0.0,
                    field.number(),
                    width,
                );
                if let Some(value) = out.value {
                    intents.push(DevelopIntent::Adjust(*field, value));
                }
            }
        });
    }
}

fn histogram(ui: &mut Ui, pal: &StudioPalette, histogram: Option<&Histogram>) {
    let width = ui.available_width();
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 54.0), Sense::hover());
    let painter = ui.painter();
    painter.rect_filled(rect, CornerRadius::ZERO, pal.bg);
    painter.rect_stroke(
        rect,
        CornerRadius::ZERO,
        Stroke::new(1.0_f32, pal.line),
        StrokeKind::Inside,
    );
    let Some(h) = histogram else {
        return;
    };
    let peak = (h.peak.max(1) as f32).sqrt();
    let n = h.bins.len().max(1) as f32;
    let mut points = vec![rect.left_bottom()];
    for (i, count) in h.bins.iter().enumerate() {
        let x = rect.left() + (i as f32 + 0.5) / n * rect.width();
        let y = rect.bottom() - (*count as f32).sqrt() / peak * (rect.height() - 8.0);
        points.push(egui::pos2(x, y));
    }
    points.push(rect.right_bottom());
    // Columns as one mesh of quads: 64 bins, no per-pixel work.
    let mut mesh = egui::Mesh::default();
    for pair in points.windows(2) {
        let (a, b) = (pair[0], pair[1]);
        let i = mesh.vertices.len() as u32;
        let fill = pal.ink_3.gamma_multiply(0.8);
        mesh.colored_vertex(a, fill);
        mesh.colored_vertex(b, fill);
        mesh.colored_vertex(egui::pos2(b.x, rect.bottom()), fill);
        mesh.colored_vertex(egui::pos2(a.x, rect.bottom()), fill);
        mesh.add_triangle(i, i + 1, i + 2);
        mesh.add_triangle(i, i + 2, i + 3);
    }
    painter.add(egui::Shape::mesh(mesh));
    painter.galley(
        rect.left_top() + egui::vec2(8.0, 5.0),
        painter.layout_job(style::caps_job(&h.caption(), 10.0, pal.ink_3)),
        pal.ink_3,
    );
}

/// The looks as a 2 x 3 grid. Click applies; double-click on the chosen look
/// resets its parameters to the look.
fn look_grid(
    ui: &mut Ui,
    pal: &StudioPalette,
    all: &[Look],
    chosen: Option<usize>,
    enabled: bool,
) -> Option<DevelopIntent> {
    let width = ui.available_width();
    let cell_w = (width / 2.0).floor();
    let rows = all.len().div_ceil(2);
    let (rect, _) = ui.allocate_exact_size(egui::vec2(width, rows as f32 * 29.0), Sense::hover());
    let mut out = None;
    for (i, look) in all.iter().enumerate() {
        let cell = Rect::from_min_size(
            rect.min + egui::vec2((i % 2) as f32 * cell_w, (i / 2) as f32 * 29.0),
            egui::vec2(cell_w, 29.0),
        );
        let response = ui.interact(
            cell,
            ui.id().with(("look", i)),
            if enabled {
                Sense::click()
            } else {
                Sense::hover()
            },
        );
        let on = chosen == Some(i);
        let painter = ui.painter();
        if on {
            painter.rect_filled(cell, CornerRadius::ZERO, pal.control);
        }
        painter.rect_stroke(
            cell,
            CornerRadius::ZERO,
            Stroke::new(1.0_f32, if on { pal.accent } else { pal.line_2 }),
            StrokeKind::Inside,
        );
        style::paint_text(
            painter,
            cell.center(),
            Align2::CENTER_CENTER,
            look.name,
            style::SMALL,
            if on || response.hovered() {
                pal.ink
            } else {
                pal.ink_2
            },
        );
        if response.double_clicked() && on {
            out = Some(DevelopIntent::ResetToLook(i));
        } else if response.clicked() && !on {
            out = Some(DevelopIntent::PickLook(i));
        }
    }
    out
}

fn versions_tab(ui: &mut Ui, view: &DevelopView<'_>, intents: &mut Vec<DevelopIntent>) {
    let pal = view.palette;
    style::sect(ui, pal, &format!("Versions of {}", view.render), None);
    if view.versions.is_empty() {
        style::text(
            ui,
            "No saved versions yet. Save version keeps this edit.",
            style::SMALL,
            pal.ink_2,
        );
    }
    for version in view.versions {
        let width = ui.available_width();
        let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 52.0), Sense::click());
        let painter = ui.painter();
        if version.current {
            painter.rect_filled(
                Rect::from_min_size(rect.min, egui::vec2(2.0, rect.height())),
                CornerRadius::ZERO,
                pal.accent,
            );
        } else if response.hovered() {
            painter.rect_filled(rect, CornerRadius::ZERO, pal.raised);
        }
        style::hairline(painter, rect.left_bottom(), rect.right_bottom(), pal.line);
        let left = rect.left() + if version.current { 10.0 } else { 0.0 };
        style::paint_text(
            painter,
            egui::pos2(left, rect.center().y - 9.0),
            Align2::LEFT_CENTER,
            &version.name,
            style::BODY,
            pal.ink,
        );
        style::paint_text(
            painter,
            egui::pos2(left, rect.center().y + 9.0),
            Align2::LEFT_CENTER,
            &version.detail,
            style::SMALL,
            pal.ink_2,
        );
        if version.current {
            painter.text(
                rect.right_center(),
                Align2::RIGHT_CENTER,
                "OPEN",
                egui::FontId::proportional(9.5),
                pal.accent,
            );
        } else if response.double_clicked() {
            intents.push(DevelopIntent::OpenVersion(version.id.clone()));
        }
        response.context_menu(|ui| {
            if ui.button("Open this version").clicked() {
                intents.push(DevelopIntent::OpenVersion(version.id.clone()));
                ui.close();
            }
            if ui.button("Carry to the new render").clicked() {
                intents.push(DevelopIntent::CarryVersion(version.id.clone()));
                ui.close();
            }
        });
    }
    egui::Frame::NONE
        .fill(pal.raised)
        .stroke(Stroke::new(1.0_f32, pal.line))
        .inner_margin(egui::Margin::symmetric(14, 12))
        .show(ui, |ui| {
            ui.label(
                egui::RichText::new("Versions follow you to a new render.")
                    .size(12.5)
                    .strong()
                    .color(pal.ink),
            );
            style::text(
                ui,
                "After \u{201c}Render again\u{201d}, a version can be carried over to the new render in one step.",
                12.5,
                pal.ink_2,
            );
        });
}

// --------------------------------------------------------------------- canvas

/// A crop handle: sides of the crop frame it moves, or the whole frame.
#[derive(Clone, Copy, Debug, PartialEq)]
enum CropGrip {
    Sides(i8, i8),
    Body,
}

#[derive(Clone, Copy, Debug)]
struct CropDrag {
    grip: CropGrip,
    start: Crop,
    origin: [f64; 2],
}

/// Canvas state of the Develop tools. Kept by the editor across documents;
/// the per-photograph parts reset with `reset_document`.
#[derive(Debug)]
pub(crate) struct DevelopCanvas {
    pub tool: DevelopTool,
    pub compare: Compare,
    /// Split position as a fraction of the photograph's width.
    pub split: f32,
    pub surround: Surround,
    /// The surround is painted only once chosen, so today's canvas is unchanged.
    pub surround_chosen: bool,
    pub clipping: bool,
    /// Brush diameter in screen points.
    pub brush_px: f32,
    pub brush_feather: f32,
    pub heal_px: f32,
    /// Planes for the next depth repair, zero-based inclusive.
    pub repair_range: Option<(usize, usize)>,
    /// The Region tool's current shape (see `DevelopIntent::RegionDrawing`).
    pub region_drawing: usize,
    stroke: Vec<[f32; 2]>,
    crop_drag: Option<CropDrag>,
    crop_draft: Option<Crop>,
    split_drag: bool,
    /// Intents raised by pointer gestures on the photograph.
    pub outbox: Vec<DevelopIntent>,
}

impl Default for DevelopCanvas {
    fn default() -> Self {
        Self {
            tool: DevelopTool::Move,
            compare: Compare::After,
            split: 0.5,
            surround: Surround::Dark,
            surround_chosen: false,
            clipping: false,
            brush_px: 40.0,
            brush_feather: 0.5,
            heal_px: 24.0,
            repair_range: None,
            region_drawing: 1,
            stroke: Vec::new(),
            crop_drag: None,
            crop_draft: None,
            split_drag: false,
            outbox: Vec::new(),
        }
    }
}

/// What the canvas overlay reads.
pub(crate) struct CanvasView<'a> {
    pub palette: &'a StudioPalette,
    pub recipe: &'a DevelopmentRecipe,
    pub image_size: [u32; 2],
    pub um_per_px: Option<f64>,
    /// The split view's "before" overview, when it is ready.
    pub before: Option<(&'a egui::TextureHandle, [[f32; 2]; 2])>,
    /// Pure black and pure white of the development, when Clipping is on.
    pub clipping: Option<&'a egui::TextureHandle>,
}

fn uv_of(image: Rect, at: Pos2) -> [f32; 2] {
    [
        ((at.x - image.left()) / image.width()).clamp(0.0, 1.0),
        ((at.y - image.top()) / image.height()).clamp(0.0, 1.0),
    ]
}

fn screen_of(image: Rect, uv: [f64; 2], size: [u32; 2]) -> Pos2 {
    egui::pos2(
        image.left() + (uv[0] / f64::from(size[0].max(1))) as f32 * image.width(),
        image.top() + (uv[1] / f64::from(size[1].max(1))) as f32 * image.height(),
    )
}

impl DevelopCanvas {
    /// Per-photograph state goes; the tool and view choices stay.
    pub(crate) fn reset_document(&mut self) {
        self.stroke.clear();
        self.crop_drag = None;
        self.crop_draft = None;
        self.split_drag = false;
        self.outbox.clear();
        self.repair_range = None;
    }

    /// True while a Develop tool takes the pointer from panning and regions.
    pub(crate) fn owns_pointer(&self) -> bool {
        self.tool.owns_canvas() || self.split_drag
    }

    pub(crate) fn take_intents(&mut self) -> Vec<DevelopIntent> {
        std::mem::take(&mut self.outbox)
    }

    /// Paint and handle the overlays on the photograph at `image` (screen
    /// rectangle of the whole photograph), clipped to `clip`.
    pub(crate) fn overlay(&mut self, ui: &mut Ui, image: Rect, clip: Rect, view: &CanvasView<'_>) {
        let visible = image.intersect(clip);
        if !visible.is_positive() {
            return;
        }
        let painter = ui.painter().with_clip_rect(visible);
        if let Some(texture) = view.clipping.filter(|_| self.clipping) {
            painter.image(
                texture.id(),
                image,
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                Color32::WHITE,
            );
        }
        if self.compare == Compare::Split {
            self.split_view(ui, &painter, image, visible, view);
        }
        if let Some(crop) = self.crop_draft.or(view.recipe.crop)
            && (self.tool == DevelopTool::Crop || self.crop_draft.is_some())
        {
            paint_crop(&painter, image, crop, view.image_size, view.palette);
        }
        if let Some(bar) = view.recipe.scale_bar.filter(|b| b.enabled)
            && let Some(um) = view.um_per_px
        {
            paint_scale_bar(&painter, image, &bar, um, view.image_size, view.palette);
        }
        if !self.tool.owns_canvas() {
            return;
        }
        let response = ui.interact(
            visible,
            ui.id().with("develop-canvas"),
            Sense::click_and_drag(),
        );
        match self.tool {
            DevelopTool::Crop => self.crop_gesture(&response, image, view),
            DevelopTool::WhiteBalance => {
                if response.clicked()
                    && let Some(at) = response.interact_pointer_pos()
                {
                    self.outbox
                        .push(DevelopIntent::SampleNeutral(uv_of(image, at)));
                }
                if response.hovered() {
                    ui.ctx().set_cursor_icon(egui::CursorIcon::Crosshair);
                }
            }
            DevelopTool::DepthBrush => self.brush_gesture(ui, &painter, &response, image, view),
            DevelopTool::Heal => {
                if let Some(at) = response.hover_pos() {
                    painter.circle_stroke(
                        at,
                        self.heal_px * 0.5,
                        Stroke::new(1.0_f32, Color32::WHITE),
                    );
                }
                if response.clicked()
                    && let Some(at) = response.interact_pointer_pos()
                {
                    self.outbox.push(DevelopIntent::AddHeal(auto_heal(
                        uv_of(image, at),
                        [
                            self.heal_px * 0.5 / image.width(),
                            self.heal_px * 0.5 / image.height(),
                        ],
                    )));
                }
            }
            DevelopTool::Note => {
                if response.clicked()
                    && let Some(at) = response.interact_pointer_pos()
                {
                    self.outbox.push(DevelopIntent::AddNote(uv_of(image, at)));
                }
            }
            _ => {}
        }
    }

    fn brush_gesture(
        &mut self,
        ui: &mut Ui,
        painter: &egui::Painter,
        response: &Response,
        image: Rect,
        view: &CanvasView<'_>,
    ) {
        let radius_screen = self.brush_px * 0.5;
        if let Some(at) = response.hover_pos().or(response.interact_pointer_pos()) {
            painter.circle_stroke(
                at,
                radius_screen,
                Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.85)),
            );
            ui.ctx().set_cursor_icon(egui::CursorIcon::None);
        }
        if response.dragged()
            && let Some(at) = response.interact_pointer_pos()
        {
            let uv = uv_of(image, at);
            if self.stroke.last() != Some(&uv) {
                self.stroke.push(uv);
            }
        }
        if self.stroke.len() > 1 {
            let points: Vec<Pos2> = self
                .stroke
                .iter()
                .map(|p| {
                    egui::pos2(
                        image.left() + p[0] * image.width(),
                        image.top() + p[1] * image.height(),
                    )
                })
                .collect();
            painter.add(egui::Shape::line(
                points,
                Stroke::new(
                    radius_screen * 2.0,
                    view.palette.accent.gamma_multiply(0.14),
                ),
            ));
        }
        if response.drag_stopped() || (response.clicked() && self.stroke.is_empty()) {
            if self.stroke.is_empty()
                && let Some(at) = response.interact_pointer_pos()
            {
                self.stroke.push(uv_of(image, at));
            }
            let points = std::mem::take(&mut self.stroke);
            if !points.is_empty() {
                self.outbox.push(DevelopIntent::PaintStroke {
                    points,
                    radius: [
                        radius_screen / image.width(),
                        radius_screen / image.height(),
                    ],
                    feather: self.brush_feather,
                });
            }
        }
        // Outline every depth repair, dashed in accent.
        for region in &view.recipe.regions {
            if let strehl_edit::RegionShape::Stroke { points, .. } = &region.shape
                && region.source_range.is_some()
            {
                let line: Vec<Pos2> = points
                    .iter()
                    .map(|p| {
                        egui::pos2(
                            image.left() + p[0] * image.width(),
                            image.top() + p[1] * image.height(),
                        )
                    })
                    .collect();
                if line.len() > 1 {
                    style::dashed(
                        painter,
                        &line,
                        Stroke::new(1.2_f32, view.palette.accent),
                        5.0,
                        4.0,
                    );
                }
            }
        }
    }

    fn crop_gesture(&mut self, response: &Response, image: Rect, view: &CanvasView<'_>) {
        let size = view.image_size.map(|v| v.max(1));
        let current = self.crop_draft.or(view.recipe.crop).unwrap_or(Crop {
            min: [0.0, 0.0],
            max: [1.0, 1.0],
            angle_deg: 0.0,
        });
        let to_px = |at: Pos2| {
            [
                f64::from((at.x - image.left()) / image.width()) * f64::from(size[0]),
                f64::from((at.y - image.top()) / image.height()) * f64::from(size[1]),
            ]
        };
        if response.drag_started()
            && let Some(at) = response.interact_pointer_pos()
        {
            let grip = crop_grip(current, size, image, at);
            self.crop_drag = Some(CropDrag {
                grip,
                start: current,
                origin: to_px(at),
            });
        }
        if let Some(drag) = self.crop_drag
            && let Some(at) = response.interact_pointer_pos()
        {
            self.crop_draft = Some(drag_crop(drag, to_px(at), size));
        }
        if response.drag_stopped() {
            self.crop_drag = None;
            if let Some(crop) = self.crop_draft.take() {
                self.outbox.push(DevelopIntent::SetCrop(Some(crop)));
            }
        }
    }

    fn split_view(
        &mut self,
        ui: &mut Ui,
        painter: &egui::Painter,
        image: Rect,
        visible: Rect,
        view: &CanvasView<'_>,
    ) {
        let x = image.left() + self.split.clamp(0.0, 1.0) * image.width();
        if let Some((texture, uv)) = view.before {
            let left =
                Rect::from_min_max(image.min, egui::pos2(x, image.bottom())).intersect(visible);
            if left.is_positive() {
                // The before overview covers the whole photograph; map the
                // visible left part into its UV rectangle.
                let u = |sx: f32| {
                    uv[0][0] + (sx - image.left()) / image.width() * (uv[1][0] - uv[0][0])
                };
                let v = |sy: f32| {
                    uv[0][1] + (sy - image.top()) / image.height() * (uv[1][1] - uv[0][1])
                };
                painter.image(
                    texture.id(),
                    left,
                    Rect::from_min_max(
                        egui::pos2(u(left.left()), v(left.top())),
                        egui::pos2(u(left.right()), v(left.bottom())),
                    ),
                    Color32::WHITE,
                );
            }
        }
        painter.line_segment(
            [
                egui::pos2(x, visible.top()),
                egui::pos2(x, visible.bottom()),
            ],
            Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.8)),
        );
        let label = |text: &str, at: Pos2, align: Align2| {
            painter.galley(
                align
                    .anchor_size(
                        at,
                        painter
                            .layout_job(style::caps_job(text, 10.0, Color32::WHITE))
                            .size(),
                    )
                    .min,
                painter.layout_job(style::caps_job(text, 10.0, Color32::WHITE)),
                Color32::WHITE,
            );
        };
        label(
            if view.before.is_some() {
                "Before"
            } else {
                "Before · developing"
            },
            egui::pos2(x - 8.0, visible.top() + 8.0),
            Align2::RIGHT_TOP,
        );
        label(
            "After",
            egui::pos2(x + 8.0, visible.top() + 8.0),
            Align2::LEFT_TOP,
        );
        let grip =
            Rect::from_center_size(egui::pos2(x, visible.center().y), egui::vec2(12.0, 40.0));
        let response = ui.interact(grip, ui.id().with("develop-split"), Sense::drag());
        if response.hovered() || response.dragged() {
            ui.ctx().set_cursor_icon(egui::CursorIcon::ResizeHorizontal);
        }
        self.split_drag = response.dragged();
        if response.dragged()
            && let Some(at) = response.interact_pointer_pos()
        {
            self.split = ((at.x - image.left()) / image.width()).clamp(0.02, 0.98);
        }
    }
}

/// A heal at `center` whose source sits beside it, on the side with room.
pub(crate) fn auto_heal(center: [f32; 2], radius: [f32; 2]) -> Heal {
    let r = [radius[0].clamp(0.0001, 0.25), radius[1].clamp(0.0001, 0.25)];
    let reach = 2.5;
    let offset = if center[0] + r[0] * (reach + 1.0) <= 1.0 {
        [r[0] * reach, 0.0]
    } else if center[0] - r[0] * (reach + 1.0) >= 0.0 {
        [-r[0] * reach, 0.0]
    } else if center[1] + r[1] * (reach + 1.0) <= 1.0 {
        [0.0, r[1] * reach]
    } else {
        [0.0, -r[1] * reach]
    };
    Heal {
        center,
        radius: r,
        source_offset: offset,
        enabled: true,
    }
}

fn crop_grip(crop: Crop, size: [u32; 2], image: Rect, at: Pos2) -> CropGrip {
    let corners = crop
        .corners_px(size[0], size[1])
        .map(|c| screen_of(image, c, size));
    // Corners clockwise from top left; edge midpoints between them.
    let grips = [
        (corners[0], (-1, -1)),
        (corners[1], (1, -1)),
        (corners[2], (1, 1)),
        (corners[3], (-1, 1)),
        (corners[0].lerp(corners[1], 0.5), (0, -1)),
        (corners[1].lerp(corners[2], 0.5), (1, 0)),
        (corners[2].lerp(corners[3], 0.5), (0, 1)),
        (corners[3].lerp(corners[0], 0.5), (-1, 0)),
    ];
    grips
        .iter()
        .filter(|(p, _)| p.distance(at) <= 12.0)
        .min_by(|a, b| a.0.distance(at).total_cmp(&b.0.distance(at)))
        .map_or(CropGrip::Body, |(_, (x, y))| CropGrip::Sides(*x, *y))
}

/// Move a crop edge or the whole crop. Edges move in the crop's own turned
/// frame, so straightening and cropping compose.
fn drag_crop(drag: CropDrag, at: [f64; 2], size: [u32; 2]) -> Crop {
    let start = drag.start;
    let w = f64::from(size[0]);
    let h = f64::from(size[1]);
    let centre = [
        (f64::from(start.min[0]) + f64::from(start.max[0])) * 0.5 * w,
        (f64::from(start.min[1]) + f64::from(start.max[1])) * 0.5 * h,
    ];
    let half = [
        (f64::from(start.max[0]) - f64::from(start.min[0])) * 0.5 * w,
        (f64::from(start.max[1]) - f64::from(start.min[1])) * 0.5 * h,
    ];
    let (sin, cos) = f64::from(start.angle_deg).to_radians().sin_cos();
    let crop = match drag.grip {
        CropGrip::Body => {
            let d = [at[0] - drag.origin[0], at[1] - drag.origin[1]];
            let c = [
                (centre[0] + d[0]).clamp(half[0].min(w * 0.5), (w - half[0]).max(w * 0.5)),
                (centre[1] + d[1]).clamp(half[1].min(h * 0.5), (h - half[1]).max(h * 0.5)),
            ];
            Crop {
                min: [((c[0] - half[0]) / w) as f32, ((c[1] - half[1]) / h) as f32],
                max: [((c[0] + half[0]) / w) as f32, ((c[1] + half[1]) / h) as f32],
                angle_deg: start.angle_deg,
            }
        }
        CropGrip::Sides(sx, sy) => {
            let p = [at[0] - centre[0], at[1] - centre[1]];
            let local = [cos * p[0] + sin * p[1], -sin * p[0] + cos * p[1]];
            let minimum = 8.0;
            let (mut left, mut right) = (-half[0], half[0]);
            let (mut top, mut bottom) = (-half[1], half[1]);
            match sx {
                -1 => left = local[0].min(right - minimum),
                1 => right = local[0].max(left + minimum),
                _ => {}
            }
            match sy {
                -1 => top = local[1].min(bottom - minimum),
                1 => bottom = local[1].max(top + minimum),
                _ => {}
            }
            let mid = [(left + right) * 0.5, (top + bottom) * 0.5];
            let c = [
                centre[0] + cos * mid[0] - sin * mid[1],
                centre[1] + sin * mid[0] + cos * mid[1],
            ];
            let hh = [(right - left) * 0.5, (bottom - top) * 0.5];
            Crop {
                min: [((c[0] - hh[0]) / w) as f32, ((c[1] - hh[1]) / h) as f32],
                max: [((c[0] + hh[0]) / w) as f32, ((c[1] + hh[1]) / h) as f32],
                angle_deg: start.angle_deg,
            }
        }
    };
    let clamped = Crop {
        min: crop.min.map(|v| v.clamp(0.0, 1.0)),
        max: crop.max.map(|v| v.clamp(0.0, 1.0)),
        ..crop
    };
    clamped.fit_inside(size[0], size[1])
}

/// The crop frame: the outside dimmed, a hairline frame, thirds and grips.
pub(crate) fn paint_crop(
    painter: &egui::Painter,
    image: Rect,
    crop: Crop,
    size: [u32; 2],
    pal: &StudioPalette,
) {
    let size = size.map(|v| v.max(1));
    let corners = crop
        .corners_px(size[0], size[1])
        .map(|c| screen_of(image, c, size));
    // Dim outside: the photograph minus the frame, as a mesh with a hole.
    let outer = [
        image.left_top(),
        image.right_top(),
        image.right_bottom(),
        image.left_bottom(),
    ];
    let mut mesh = egui::Mesh::default();
    let shade = Color32::from_black_alpha(140);
    for p in outer.iter().chain(corners.iter()) {
        mesh.colored_vertex(*p, shade);
    }
    for i in 0..4u32 {
        let j = (i + 1) % 4;
        mesh.add_triangle(i, j, 4 + i);
        mesh.add_triangle(j, 4 + j, 4 + i);
    }
    painter.add(egui::Shape::mesh(mesh));
    let frame: Vec<Pos2> = corners
        .iter()
        .copied()
        .chain(std::iter::once(corners[0]))
        .collect();
    painter.add(egui::Shape::line(
        frame,
        Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.7)),
    ));
    for t in [1.0 / 3.0, 2.0 / 3.0] {
        let a = corners[0].lerp(corners[1], t);
        let b = corners[3].lerp(corners[2], t);
        let c = corners[0].lerp(corners[3], t);
        let d = corners[1].lerp(corners[2], t);
        painter.line_segment(
            [a, b],
            Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.2)),
        );
        painter.line_segment(
            [c, d],
            Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.2)),
        );
    }
    for (i, corner) in corners.iter().enumerate() {
        painter.rect_filled(
            Rect::from_center_size(*corner, egui::vec2(7.0, 7.0)),
            CornerRadius::ZERO,
            pal.accent,
        );
        let mid = corner.lerp(corners[(i + 1) % 4], 0.5);
        painter.rect_filled(
            Rect::from_center_size(mid, egui::vec2(5.0, 5.0)),
            CornerRadius::ZERO,
            pal.accent,
        );
    }
}

/// The crop as Export shows it: the outside dimmed and a hairline frame.
pub(crate) fn paint_crop_outline(painter: &egui::Painter, image: Rect, crop: Crop, size: [u32; 2]) {
    let size = size.map(|v| v.max(1));
    let corners = crop
        .corners_px(size[0], size[1])
        .map(|c| screen_of(image, c, size));
    let outer = [
        image.left_top(),
        image.right_top(),
        image.right_bottom(),
        image.left_bottom(),
    ];
    let mut mesh = egui::Mesh::default();
    let shade = Color32::from_black_alpha(150);
    for p in outer.iter().chain(corners.iter()) {
        mesh.colored_vertex(*p, shade);
    }
    for i in 0..4u32 {
        let j = (i + 1) % 4;
        mesh.add_triangle(i, j, 4 + i);
        mesh.add_triangle(j, 4 + j, 4 + i);
    }
    painter.add(egui::Shape::mesh(mesh));
    let frame: Vec<Pos2> = corners
        .iter()
        .copied()
        .chain(std::iter::once(corners[0]))
        .collect();
    painter.add(egui::Shape::line(
        frame,
        Stroke::new(1.0_f32, Color32::WHITE.gamma_multiply(0.4)),
    ));
}

/// The scale bar as it will be burned in, scaled to the photograph on screen.
/// Its length in screen points follows the calibration exactly.
pub(crate) fn paint_scale_bar(
    painter: &egui::Painter,
    image: Rect,
    bar: &ScaleBar,
    um_per_px: f64,
    size: [u32; 2],
    pal: &StudioPalette,
) {
    let _ = pal;
    let width_px = f64::from(size[0].max(1));
    let length = (f64::from(bar.length_um) / um_per_px / width_px) as f32 * image.width();
    if !(length.is_finite() && length > 1.0) {
        return;
    }
    let margin = image.width().min(image.height()) * 0.04;
    let right = matches!(
        bar.corner,
        ScaleBarCorner::TopRight | ScaleBarCorner::BottomRight
    );
    let bottom = matches!(
        bar.corner,
        ScaleBarCorner::BottomLeft | ScaleBarCorner::BottomRight
    );
    let x0 = if right {
        image.right() - margin - length
    } else {
        image.left() + margin
    };
    let colour = if bar.style == ScaleBarStyle::Light {
        Color32::WHITE
    } else {
        Color32::BLACK
    };
    let y = if bottom {
        image.bottom() - margin - 16.0
    } else {
        image.top() + margin
    };
    painter.rect_filled(
        Rect::from_min_size(egui::pos2(x0, y), egui::vec2(length, 2.0)),
        CornerRadius::ZERO,
        colour,
    );
    painter.text(
        egui::pos2(x0 + length * 0.5, y + 6.0),
        Align2::CENTER_TOP,
        bar.label(),
        egui::FontId::proportional(11.0),
        colour,
    );
}

#[cfg(test)]
#[path = "develop-station-tests.rs"]
mod tests;
