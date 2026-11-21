//! Macro finishing in the recipe: crop and straighten, scale bar, heals and
//! backdrop. Every field is optional and omitted when unused, so a recipe that
//! uses none of them serializes exactly as before and older builds read it.
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};

use super::bounded;

/// At most this many heal spots per photograph.
pub const MAX_HEALS: usize = 256;

fn is_zero(value: &f32) -> bool {
    *value == 0.0
}

fn enabled() -> bool {
    true
}

fn is_enabled(value: &bool) -> bool {
    *value
}

/// A crop rectangle in normalized full-photograph coordinates, turned about its
/// own centre by `angle_deg`.
///
/// `min` and `max` bound the rectangle before it is turned, so the output is
/// `(max - min) * [width, height]` source pixels in size at any angle. A
/// positive angle turns the output frame clockwise on screen (y down): it
/// levels a horizon that descends to the right by that many degrees.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Crop {
    pub min: [f32; 2],
    pub max: [f32; 2],
    #[serde(default, skip_serializing_if = "is_zero")]
    pub angle_deg: f32,
}

impl Crop {
    pub const MAX_ANGLE_DEG: f32 = 45.0;

    pub fn validate(&self) -> Result<()> {
        for v in self.min.iter().chain(&self.max) {
            bounded(*v, 0.0, 1.0, "crop coordinate")?;
        }
        ensure!(
            self.max[0] - self.min[0] >= 1e-4 && self.max[1] - self.min[1] >= 1e-4,
            "crop rectangle must have positive area"
        );
        bounded(
            self.angle_deg,
            -Self::MAX_ANGLE_DEG,
            Self::MAX_ANGLE_DEG,
            "straighten angle",
        )
    }

    /// Centre and half extents in source pixels.
    fn frame(&self, width: u32, height: u32) -> ([f64; 2], [f64; 2]) {
        let size = [f64::from(width), f64::from(height)];
        let centre = std::array::from_fn(|i| {
            (f64::from(self.min[i]) + f64::from(self.max[i])) * 0.5 * size[i]
        });
        let half = std::array::from_fn(|i| {
            (f64::from(self.max[i]) - f64::from(self.min[i])) * 0.5 * size[i]
        });
        (centre, half)
    }

    /// Output size in pixels before any export resize.
    pub fn output_size(&self, width: u32, height: u32) -> [u32; 2] {
        if self.angle_deg == 0.0 {
            let [x0, y0, x1, y1] = self.pixel_rect(width, height);
            return [x1 - x0, y1 - y0];
        }
        let (_, half) = self.frame(width, height);
        half.map(|h| ((2.0 * h).round() as u32).max(1))
    }

    /// Integer source rectangle `[x0, y0, x1, y1)` of an unturned crop.
    pub fn pixel_rect(&self, width: u32, height: u32) -> [u32; 4] {
        let edge = |v: f32, n: u32| ((f64::from(v) * f64::from(n)).round() as u32).min(n);
        let x0 = edge(self.min[0], width).min(width - 1);
        let y0 = edge(self.min[1], height).min(height - 1);
        let x1 = edge(self.max[0], width).max(x0 + 1);
        let y1 = edge(self.max[1], height).max(y0 + 1);
        [x0, y0, x1, y1]
    }

    /// Source-pixel corners of the turned rectangle, clockwise from top left.
    pub fn corners_px(&self, width: u32, height: u32) -> [[f64; 2]; 4] {
        let (c, h) = self.frame(width, height);
        let (sin, cos) = f64::from(self.angle_deg).to_radians().sin_cos();
        [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]].map(|[sx, sy]| {
            let d = [sx * h[0], sy * h[1]];
            [
                c[0] + cos * d[0] - sin * d[1],
                c[1] + sin * d[0] + cos * d[1],
            ]
        })
    }

    /// True when the turned rectangle lies inside the photograph.
    pub fn fits(&self, width: u32, height: u32) -> bool {
        let tolerance = 1e-3;
        self.corners_px(width, height).iter().all(|p| {
            (-tolerance..=f64::from(width) + tolerance).contains(&p[0])
                && (-tolerance..=f64::from(height) + tolerance).contains(&p[1])
        })
    }

    /// Shrink about the centre until the turned rectangle fits; for the
    /// straighten tool, which keeps the user's framing while it can.
    pub fn fit_inside(&self, width: u32, height: u32) -> Self {
        let (c, h) = self.frame(width, height);
        let (sin, cos) = f64::from(self.angle_deg).to_radians().sin_cos();
        let extent = [
            h[0] * cos.abs() + h[1] * sin.abs(),
            h[0] * sin.abs() + h[1] * cos.abs(),
        ];
        let size = [f64::from(width), f64::from(height)];
        let mut scale = 1.0f64;
        for i in 0..2 {
            if extent[i] > 0.0 {
                scale = scale.min(c[i].min(size[i] - c[i]).max(0.0) / extent[i]);
            }
        }
        if scale >= 1.0 {
            return *self;
        }
        let scale = scale * (1.0 - 1e-6);
        let mut fitted = *self;
        for i in 0..2 {
            let centre = (f64::from(self.min[i]) + f64::from(self.max[i])) * 0.5;
            let half = (f64::from(self.max[i]) - f64::from(self.min[i])) * 0.5 * scale;
            fitted.min[i] = (centre - half) as f32;
            fitted.max[i] = (centre + half) as f32;
        }
        fitted
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScaleBarCorner {
    TopLeft,
    TopRight,
    BottomLeft,
    #[default]
    BottomRight,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ScaleBarStyle {
    /// White bar and label, for dark backdrops.
    #[default]
    Light,
    /// Black bar and label, for light backdrops.
    Dark,
}

/// A scale bar burned into exports. The calibration (micrometres per source
/// pixel) belongs to the subject's lens calibration, never to the RAW.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ScaleBar {
    pub length_um: f32,
    #[serde(default)]
    pub corner: ScaleBarCorner,
    #[serde(default)]
    pub style: ScaleBarStyle,
    /// Hidden from the layer list and from exports when false.
    #[serde(default = "enabled", skip_serializing_if = "is_enabled")]
    pub enabled: bool,
}

impl ScaleBar {
    pub fn validate(&self) -> Result<()> {
        bounded(self.length_um, 0.1, 1_000_000.0, "scale bar length")
    }

    /// The label as drawn, for example `500 µm` or `1.5 mm`.
    pub fn label(&self) -> String {
        let trim = |v: f64, decimals: usize| {
            let text = format!("{v:.decimals$}");
            if text.contains('.') {
                text.trim_end_matches('0').trim_end_matches('.').to_owned()
            } else {
                text
            }
        };
        let um = f64::from(self.length_um);
        if um >= 1000.0 {
            format!("{} mm", trim(um / 1000.0, 3))
        } else {
            format!("{} µm", trim(um, 1))
        }
    }

    /// A round 1-2-5 length near a fifth of the output width, for a default.
    pub fn suggested_length_um(um_per_output_px: f64, output_width: u32) -> f32 {
        let target = um_per_output_px * f64::from(output_width) * 0.2;
        if !(target.is_finite() && target > 0.0) {
            return 1000.0;
        }
        let decade = 10f64.powf(target.log10().floor());
        let step = [1.0, 2.0, 5.0, 10.0]
            .into_iter()
            .map(|m| m * decade)
            .min_by(|a, b| (a - target).abs().total_cmp(&(b - target).abs()))
            .unwrap_or(decade);
        step.clamp(0.1, 1_000_000.0) as f32
    }
}

/// A clone-and-match heal. The destination disc at `center` takes the source
/// disc at `center + source_offset`, scaled per channel so the ring around the
/// source matches the ring around the destination. Radii are per axis, like an
/// ellipse region: a disc that is round in pixels has `rx * width == ry * height`.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Heal {
    pub center: [f32; 2],
    pub radius: [f32; 2],
    pub source_offset: [f32; 2],
    #[serde(default = "enabled", skip_serializing_if = "is_enabled")]
    pub enabled: bool,
}

impl Heal {
    pub fn validate(&self) -> Result<()> {
        for (i, c) in self.center.iter().enumerate() {
            bounded(*c, 0.0, 1.0, "heal centre")?;
            bounded(self.radius[i], 0.0001, 0.25, "heal radius")?;
            bounded(self.source_offset[i], -1.0, 1.0, "heal source offset")?;
            bounded(c + self.source_offset[i], 0.0, 1.0, "heal source centre")?;
        }
        let reach =
            (self.source_offset[0] / self.radius[0]).hypot(self.source_offset[1] / self.radius[1]);
        ensure!(
            reach >= 1.0,
            "heal source must not lie inside the spot it repairs"
        );
        Ok(())
    }
}

/// Backdrop clean-up: where the local light (post-placement luminance, 5x5
/// mean) reaches `threshold`, the backdrop is replaced by a smoothed backdrop
/// built only from backdrop pixels. `softness` is the width, in stops, of the
/// transition below `threshold`; 0 is a hard key. Pixels below the transition
/// are left bit-identical.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Backdrop {
    pub threshold: f32,
    pub softness: f32,
    #[serde(default = "enabled", skip_serializing_if = "is_enabled")]
    pub enabled: bool,
}

impl Backdrop {
    pub fn validate(&self) -> Result<()> {
        bounded(self.threshold, 0.001, 16.0, "backdrop threshold")?;
        bounded(self.softness, 0.0, 6.0, "backdrop softness")
    }

    /// Backdrop membership of a local light level.
    pub fn membership(&self, light: f32) -> f32 {
        // Also refuses NaN.
        if light.is_nan() || light <= 0.0 {
            return 0.0;
        }
        let stops = (light / self.threshold).log2();
        if self.softness <= 0.0 {
            return if stops >= 0.0 { 1.0 } else { 0.0 };
        }
        let t = ((stops + self.softness) / self.softness).clamp(0.0, 1.0);
        t * t * (3.0 - 2.0 * t)
    }
}
