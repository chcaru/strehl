//! Compact image-dependent tone curves. Coefficients are photographic edits,
//! never image pixels; evaluation retains the original full-resolution detail.
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};

use super::luma;

pub const MAX_SPATIAL_TREATMENTS: usize = 6;

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct AdaptiveParameters {
    pub balance: f32,
    pub local_contrast: f32,
    pub color: f32,
}

impl Default for AdaptiveParameters {
    fn default() -> Self {
        Self {
            balance: 0.5,
            local_contrast: 0.5,
            color: 0.35,
        }
    }
}

impl AdaptiveParameters {
    pub fn validate(&self) -> Result<()> {
        for v in [self.balance, self.local_contrast, self.color] {
            ensure!(
                v.is_finite() && (0.0..=1.0).contains(&v),
                "Adaptive parameters must be finite and in 0..=1"
            );
        }
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SpatialTreatment {
    pub version: u32,
    pub target_region: Option<String>,
    pub parameters: AdaptiveParameters,
    pub amount: f32,
    pub bounds: [[f32; 2]; 2],
    pub width: u32,
    pub height: u32,
    /// Log2 luminance samples, with identical placement in every spatial cell.
    pub levels: u32,
    pub log_min: f32,
    pub log_max: f32,
    /// EV corrections, ordered [y][x][luminance]. Quantized to 1/4096 stop.
    #[serde(with = "compact_f32")]
    pub tone_ev: Vec<f32>,
    /// Modest chroma multipliers at each [y][x] cell.
    #[serde(with = "compact_f32")]
    pub color_gain: Vec<f32>,
    pub delivery_ceiling: f32,
    /// Removes a global light-placement shift from the sampled treatment.
    pub centering_ev: f32,
}

impl SpatialTreatment {
    pub fn validate(&self) -> Result<()> {
        ensure!(self.version == 1, "unsupported spatial treatment version");
        self.parameters.validate()?;
        ensure!(
            self.amount.is_finite() && (0.0..=1.0).contains(&self.amount),
            "invalid spatial amount"
        );
        ensure!(
            (2..=20).contains(&self.width)
                && (2..=20).contains(&self.height)
                && (2..=33).contains(&self.levels),
            "spatial lattice exceeds bounded dimensions"
        );
        ensure!(
            self.log_min.is_finite()
                && self.log_max.is_finite()
                && self.log_min >= -16.0
                && self.log_max <= 10.0
                && self.log_max > self.log_min,
            "invalid spatial luminance domain"
        );
        ensure!(
            self.delivery_ceiling.is_finite() && (1.0..=125.0).contains(&self.delivery_ceiling),
            "invalid spatial delivery ceiling"
        );
        ensure!(
            self.centering_ev.is_finite() && self.centering_ev.abs() <= 0.5,
            "invalid spatial centering"
        );
        for axis in 0..2 {
            ensure!(
                self.bounds[0][axis].is_finite()
                    && self.bounds[1][axis].is_finite()
                    && self.bounds[0][axis] >= 0.0
                    && self.bounds[1][axis] <= 1.0
                    && self.bounds[1][axis] > self.bounds[0][axis],
                "invalid spatial bounds"
            );
        }
        if let Some(id) = &self.target_region {
            ensure!(
                !id.is_empty() && id.len() <= 128,
                "invalid spatial region ID"
            );
        }
        let cells = self.width as usize * self.height as usize;
        ensure!(
            self.tone_ev.len() == cells * self.levels as usize && self.color_gain.len() == cells,
            "spatial lattice sample count mismatch"
        );
        ensure!(
            self.tone_ev.iter().all(|v| v.is_finite() && v.abs() <= 1.0),
            "invalid spatial tone coefficient"
        );
        ensure!(
            self.color_gain
                .iter()
                .all(|v| v.is_finite() && (1.0..=1.2).contains(v)),
            "invalid spatial color coefficient"
        );
        let step = (self.log_max - self.log_min) / (self.levels - 1) as f32;
        ensure!(
            self.tone_ev
                .chunks_exact(self.levels as usize)
                .all(|curve| curve.windows(2).all(|v| v[1] - v[0] > -step * 0.8)),
            "spatial tone curves must preserve luminance order"
        );
        Ok(())
    }

    fn coordinates(&self, uv: [f32; 2]) -> (usize, usize, f32, f32) {
        let x = ((uv[0] - self.bounds[0][0]) / (self.bounds[1][0] - self.bounds[0][0])
            * (self.width - 1) as f32)
            .clamp(0.0, (self.width - 1) as f32);
        let y = ((uv[1] - self.bounds[0][1]) / (self.bounds[1][1] - self.bounds[0][1])
            * (self.height - 1) as f32)
            .clamp(0.0, (self.height - 1) as f32);
        let ix = (x as usize).min(self.width as usize - 2);
        let iy = (y as usize).min(self.height as usize - 2);
        (ix, iy, x - ix as f32, y - iy as f32)
    }

    /// Unmasked EV at this location and input luminance, before Amount and the
    /// final per-pixel highlight/black protection. Useful for an honest change map.
    pub fn gain_ev_at(&self, uv: [f32; 2], luminance: f32) -> f32 {
        let (x, y, tx, ty) = self.coordinates(uv);
        let z = ((luminance.max(1e-12).log2() - self.log_min) / (self.log_max - self.log_min)
            * (self.levels - 1) as f32)
            .clamp(0.0, (self.levels - 1) as f32);
        let iz = (z as usize).min(self.levels as usize - 2);
        let tz = z - iz as f32;
        let at = |xx, yy| {
            let i = (yy * self.width as usize + xx) * self.levels as usize + iz;
            self.tone_ev[i] * (1.0 - tz) + self.tone_ev[i + 1] * tz
        };
        (at(x, y) * (1.0 - tx) + at(x + 1, y) * tx) * (1.0 - ty)
            + (at(x, y + 1) * (1.0 - tx) + at(x + 1, y + 1) * tx) * ty
            + self.centering_ev
    }

    pub(crate) fn color_gain_at(&self, uv: [f32; 2]) -> f32 {
        let (x, y, tx, ty) = self.coordinates(uv);
        let at = |xx, yy| self.color_gain[yy * self.width as usize + xx];
        (at(x, y) * (1.0 - tx) + at(x + 1, y) * tx) * (1.0 - ty)
            + (at(x, y + 1) * (1.0 - tx) + at(x + 1, y + 1) * tx) * ty
    }

    pub(crate) fn apply(&self, rgb: [f32; 3], uv: [f32; 2], scope_weight: f32) -> [f32; 3] {
        let amount = self.amount * scope_weight;
        let y = luma(rgb);
        if amount <= 0.0 || y <= 0.0 {
            return rgb;
        }
        let maximum = rgb.into_iter().fold(0.0, f32::max);
        let floor = smooth((y - 0.002) / 0.025);
        let ev = self.gain_ev_at(uv, y);
        // Only an upward correction approaches the source/delivery white. A
        // stored clipped channel is not a signal to invent recoverable detail.
        let headroom = if ev > 0.0 {
            smooth((self.delivery_ceiling - maximum) / (self.delivery_ceiling * 0.45))
        } else {
            1.0
        };
        let gain = (ev * amount * floor * headroom).exp2();
        let gain = if maximum <= self.delivery_ceiling {
            gain.min(self.delivery_ceiling / maximum.max(1e-12))
        } else {
            gain.min(1.0)
        };
        let toned = rgb.map(|c| c * gain);
        let new_y = y * gain;
        let color = self.color_gain_at(uv);
        let maximum = toned.into_iter().fold(0.0, f32::max);
        let minimum = toned.into_iter().fold(f32::INFINITY, f32::min).max(0.0);
        let saturation = (maximum - minimum) / maximum.max(1e-12);
        let mut increase = (color - 1.0) * amount * floor * (1.0 - saturation).max(0.0);
        let ceiling = self.delivery_ceiling.max(maximum);
        // Increase chroma along the existing hue ray without creating channel
        // clipping or negative light. Luminance is unchanged by this operation.
        for c in toned {
            let d = c - new_y;
            if d > 0.0 {
                increase = increase.min(((ceiling - c) / d).max(0.0));
            }
            if d < 0.0 {
                increase = increase.min((-c / d).max(0.0));
            }
        }
        toned.map(|c| c + (c - new_y) * increase)
    }
}

fn smooth(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

/// Exact bits avoid pretty-JSON whitespace multiplying lattice storage. Unlike
/// quantized integer serialization, this also preserves interpolated Amount
/// coefficients bit-for-bit when a recipe is saved and reopened.
mod compact_f32 {
    use serde::{Deserialize, Deserializer, Serializer, de::Error};
    const PREFIX: &str = "f32hex:";
    pub fn serialize<S: Serializer>(values: &[f32], serializer: S) -> Result<S::Ok, S::Error> {
        const HEX: &[u8] = b"0123456789abcdef";
        let mut text = String::with_capacity(PREFIX.len() + values.len() * 8);
        text.push_str(PREFIX);
        for value in values {
            let bits = value.to_bits();
            for shift in (0..8).rev() {
                text.push(HEX[((bits >> (shift * 4)) & 15) as usize] as char);
            }
        }
        serializer.serialize_str(&text)
    }
    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<Vec<f32>, D::Error> {
        let text = String::deserialize(deserializer)?;
        let Some(body) = text.strip_prefix(PREFIX) else {
            return Err(D::Error::custom("unknown spatial coefficient encoding"));
        };
        if !body.len().is_multiple_of(8) || body.len() > 20 * 20 * 33 * 8 {
            return Err(D::Error::custom("invalid spatial coefficient length"));
        }
        body.as_bytes()
            .as_chunks::<8>()
            .0
            .iter()
            .map(|word| {
                let mut bits = 0u32;
                for &b in word {
                    let digit = match b {
                        b'0'..=b'9' => b - b'0',
                        b'a'..=b'f' => b - b'a' + 10,
                        _ => return Err(D::Error::custom("invalid spatial coefficient hex")),
                    };
                    bits = (bits << 4) | u32::from(digit);
                }
                Ok(f32::from_bits(bits))
            })
            .collect()
    }
}
