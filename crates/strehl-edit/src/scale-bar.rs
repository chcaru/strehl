//! Scale bar burn-in: an anti-aliased bar and, when a system font is found,
//! its label. Compositing is in linear light. Font files are read from the
//! system at run time and never redistributed (implementation plan D11).
use crate::{ScaleBar, ScaleBarCorner};
use ab_glyph::{Font, FontArc, PxScale, ScaleFont, point};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScaleBarReport {
    pub length_um: f32,
    /// Micrometres per output pixel after crop and resize.
    pub um_per_px: f64,
    pub length_px: f64,
    /// `None` when no system font was available: the bar was drawn alone.
    pub label: Option<String>,
    pub corner: ScaleBarCorner,
}

/// Bahnschrift, then Segoe UI, then common Linux and macOS faces.
pub fn scale_bar_font() -> Option<FontArc> {
    static FONT: OnceLock<Option<FontArc>> = OnceLock::new();
    FONT.get_or_init(|| {
        let windows = std::env::var_os("WINDIR")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| "C:/Windows".into())
            .join("Fonts");
        [
            windows.join("bahnschrift.ttf"),
            windows.join("segoeui.ttf"),
            "C:/Windows/Fonts/bahnschrift.ttf".into(),
            "C:/Windows/Fonts/segoeui.ttf".into(),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf".into(),
            "/usr/share/fonts/TTF/DejaVuSans.ttf".into(),
            "/System/Library/Fonts/Supplemental/Arial.ttf".into(),
        ]
        .into_iter()
        .find_map(|path| {
            let bytes = std::fs::read(path).ok()?;
            FontArc::try_from_vec(bytes).ok()
        })
    })
    .clone()
}

/// Composite coverage `a` of `colour` over linear RGB.
#[inline]
fn blend(p: &mut [f32], colour: [f32; 3], a: f32) {
    if a <= 0.0 {
        return;
    }
    let a = a.min(1.0);
    for c in 0..3 {
        p[c] += (colour[c] - p[c]) * a;
    }
}

pub(crate) struct Burn<'a> {
    pub pixels: &'a mut [f32],
    pub alpha: Option<&'a mut [u8]>,
    pub size: [u32; 2],
}

impl Burn<'_> {
    fn paint(&mut self, x: i64, y: i64, colour: [f32; 3], a: f32) {
        let [w, h] = self.size.map(i64::from);
        if a <= 0.0 || x < 0 || y < 0 || x >= w || y >= h {
            return;
        }
        let i = (y * w + x) as usize;
        blend(&mut self.pixels[i * 3..i * 3 + 3], colour, a);
        if let Some(alpha) = self.alpha.as_deref_mut() {
            let covered = (a.min(1.0) * 255.0).round() as u8;
            alpha[i] = alpha[i].max(covered);
        }
    }
}

/// Draw `bar` for an output of `um_per_px` micrometres per pixel.
pub(crate) fn burn_scale_bar(
    target: &mut Burn<'_>,
    bar: &ScaleBar,
    um_per_px: f64,
    colour: [f32; 3],
    font: Option<&FontArc>,
) -> Result<ScaleBarReport> {
    bar.validate()?;
    ensure!(
        um_per_px.is_finite() && um_per_px > 0.0,
        "the scale calibration must be a positive number of micrometres per pixel"
    );
    let [w, h] = target.size;
    let length_px = f64::from(bar.length_um) / um_per_px;
    let short = f64::from(w.min(h));
    let margin = (short * 0.04).round().max(2.0);
    ensure!(
        length_px >= 4.0 && length_px <= f64::from(w) - 2.0 * margin,
        "a {} scale bar would be {length_px:.1} px on this {w} px export; choose about {} for this size",
        bar.label(),
        ScaleBar {
            enabled: true,
            length_um: ScaleBar::suggested_length_um(um_per_px, w),
            ..*bar
        }
        .label()
    );
    let thickness = (short / 150.0).round().clamp(2.0, 96.0);
    let font_px = (thickness * 3.0).clamp(10.0, 320.0) as f32;
    let gap = thickness.round();
    let right = matches!(
        bar.corner,
        ScaleBarCorner::TopRight | ScaleBarCorner::BottomRight
    );
    let bottom = matches!(
        bar.corner,
        ScaleBarCorner::BottomLeft | ScaleBarCorner::BottomRight
    );
    let x0 = if right {
        f64::from(w) - margin - length_px
    } else {
        margin
    };
    let x1 = x0 + length_px;
    // Label metrics first: a top bar sits below its label's line.
    let mut text = bar.label();
    let layout = font.map(|font| {
        if font.glyph_id('µ').0 == 0 {
            text = text.replace('µ', "u");
        }
        let scale = PxScale::from(font_px);
        let scaled = font.as_scaled(scale);
        let mut caret = 0.0f32;
        let mut glyphs = Vec::new();
        let mut previous = None;
        for ch in text.chars() {
            let id = scaled.glyph_id(ch);
            if let Some(p) = previous {
                caret += scaled.kern(p, id);
            }
            glyphs.push(id.with_scale_and_position(scale, point(caret, 0.0)));
            caret += scaled.h_advance(id);
            previous = Some(id);
        }
        (glyphs, caret, scaled.ascent(), scaled.descent())
    });
    let label_height = layout
        .as_ref()
        .map_or(0.0, |(_, _, ascent, descent)| f64::from(ascent - descent));
    let (bar_top, baseline) = if bottom {
        let top = f64::from(h) - margin - thickness;
        (
            top,
            top - gap - layout.as_ref().map_or(0.0, |l| f64::from(-l.3)),
        )
    } else {
        let top = margin
            + if layout.is_some() {
                label_height + gap
            } else {
                0.0
            };
        (
            top,
            margin + layout.as_ref().map_or(0.0, |l| f64::from(l.2)),
        )
    };
    ensure!(
        bar_top >= 0.0 && baseline >= 0.0,
        "this export is too small for a labelled scale bar"
    );
    // Bar: whole rows, anti-aliased ends.
    let row0 = bar_top.round() as i64;
    let row1 = (bar_top + thickness).round() as i64;
    for x in x0.floor() as i64..x1.ceil() as i64 {
        let cover = ((x as f64 + 1.0).min(x1) - (x as f64).max(x0)).clamp(0.0, 1.0) as f32;
        for y in row0..row1 {
            target.paint(x, y, colour, cover);
        }
    }
    let mut label = None;
    if let (Some(font), Some((glyphs, width, _, _))) = (font, layout) {
        let left = ((x0 + x1) * 0.5 - f64::from(width) * 0.5).clamp(
            margin,
            (f64::from(w) - margin - f64::from(width)).max(margin),
        );
        for glyph in glyphs {
            let mut glyph = glyph;
            glyph.position = point(
                glyph.position.x + left as f32,
                glyph.position.y + baseline as f32,
            );
            if let Some(outlined) = font.outline_glyph(glyph) {
                let bounds = outlined.px_bounds();
                outlined.draw(|gx, gy, coverage| {
                    target.paint(
                        bounds.min.x as i64 + i64::from(gx),
                        bounds.min.y as i64 + i64::from(gy),
                        colour,
                        coverage,
                    );
                });
            }
        }
        label = Some(text);
    }
    Ok(ScaleBarReport {
        length_um: bar.length_um,
        um_per_px,
        length_px,
        label,
        corner: bar.corner,
    })
}
