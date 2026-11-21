//! White-balance pick: the global temperature and tint that make a sampled
//! neutral come out neutral.
//!
//! `Adjustments::apply` scales red by `2^(0.005 T)`, blue by `2^(-0.005 T)` and
//! green by `2^(-0.005 tint)`. A neutral needs corrected red equal to corrected
//! blue, `T = 100 log2(B / R)`, and corrected green equal to their geometric
//! mean `sqrt(R B)`, `tint = -200 log2(sqrt(R B) / G)`. Exposure is a gain and
//! the tone and saturation controls keep a neutral neutral, so the pick holds
//! under them; an Adaptive colour field applies afterwards and may tint it.
//! Both controls stop at +-100, which limits the correction to a factor of 2
//! between red and blue (and of sqrt 2 for green); `clamped` reports it.
use crate::LinearImage;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct WhiteBalancePick {
    /// Replace the global temperature with this, -100..=100.
    pub temperature: f32,
    /// Replace the global tint with this, -100..=100.
    pub tint: f32,
    /// The neutral needed more than the controls' range; the result is partial.
    pub clamped: bool,
    /// The averaged post-placement linear sample the pick used.
    pub sample: [f32; 3],
}

/// Temperature and tint that neutralize `rgb`, a linear sample taken after the
/// display placement and before the recipe. `None` for a sample with a channel
/// at or below zero, where no gain can make it neutral.
pub fn white_balance_from_neutral(rgb: [f32; 3]) -> Option<WhiteBalancePick> {
    if !rgb.iter().all(|v| v.is_finite() && *v > 1e-9) {
        return None;
    }
    let [r, g, b] = rgb.map(f64::from);
    let temperature = 100.0 * (b / r).log2();
    let tint = -200.0 * ((r * b).sqrt() / g).log2();
    let clamp = |v: f64| v.clamp(-100.0, 100.0) as f32;
    Some(WhiteBalancePick {
        temperature: clamp(temperature),
        tint: clamp(tint),
        clamped: temperature.abs() > 100.0 || tint.abs() > 100.0,
        sample: rgb,
    })
}

impl LinearImage {
    /// Mean post-placement value over the square of side `2 * half + 1` source
    /// pixels centred on `uv`, clipped to the photograph.
    pub fn sample_placed(&self, uv: [f32; 2], half: u32) -> Option<[f32; 3]> {
        if self.validate_extent().is_err() || !uv.iter().all(|v| v.is_finite()) {
            return None;
        }
        let at = |v: f32, n: u32| {
            ((f64::from(v) * f64::from(n)).floor() as i64).clamp(0, i64::from(n) - 1)
        };
        let (cx, cy) = (at(uv[0], self.width), at(uv[1], self.height));
        let half = i64::from(half.min(64));
        let x0 = (cx - half).max(0) as usize;
        let x1 = (cx + half).min(i64::from(self.width) - 1) as usize;
        let y0 = (cy - half).max(0) as usize;
        let y1 = (cy + half).min(i64::from(self.height) - 1) as usize;
        let mut sum = [0.0f64; 3];
        for y in y0..=y1 {
            for x in x0..=x1 {
                let i = (y * self.width as usize + x) * 3;
                let raw = [self.pixels[i], self.pixels[i + 1], self.pixels[i + 2]];
                let placed = self.baseline.map_or(raw, |b| b.place(raw));
                for c in 0..3 {
                    sum[c] += f64::from(placed[c]);
                }
            }
        }
        let n = ((x1 - x0 + 1) * (y1 - y0 + 1)) as f64;
        let mean = sum.map(|s| (s / n) as f32);
        mean.iter().all(|v| v.is_finite()).then_some(mean)
    }

    /// Pick white balance from the neutral at `uv`, averaged over a square.
    pub fn pick_white_balance(&self, uv: [f32; 2], half: u32) -> Option<WhiteBalancePick> {
        white_balance_from_neutral(self.sample_placed(uv, half)?)
    }
}
