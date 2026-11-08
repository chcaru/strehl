//! A preview-only focusing aid. These scores do not measure RAW image quality,
//! sensor noise, physical depth, or proof that every subject feature is covered.
use crate::model::Roi;
use anyhow::{Result, ensure};
use image::RgbImage;
use serde::{Deserialize, Serialize};

pub const TILES: usize = 24;
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Sample {
    pub position: u16,
    pub scores: Vec<f32>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Suggestion {
    pub start: u16,
    pub end: u16,
    pub supported_tiles: usize,
    pub clipped: bool,
    pub explanation: String,
}

pub fn scores(image: &RgbImage, roi: Roi) -> Result<Vec<f32>> {
    ensure!(
        roi.valid(),
        "Choose a nonempty subject region inside the preview"
    );
    ensure!(
        image.width() >= 96 && image.height() >= 64,
        "Preview too small for a focus survey"
    );
    let w = image.width();
    let h = image.height();
    let luma = |x: u32, y: u32| {
        let p = image.get_pixel(x, y);
        (f32::from(p[0]) * 0.2126 + f32::from(p[1]) * 0.7152 + f32::from(p[2]) * 0.0722) / 255.0
    };
    let smooth = |x: u32, y: u32| {
        (luma(x, y) * 4.0 + luma(x - 1, y) + luma(x + 1, y) + luma(x, y - 1) + luma(x, y + 1)) / 8.0
    };
    let mut values = Vec::with_capacity(TILES);
    for ty in 0..4 {
        for tx in 0..6 {
            let left = ((roi.x + roi.width * tx as f32 / 6.0) * w as f32) as u32;
            let right = ((roi.x + roi.width * (tx + 1) as f32 / 6.0) * w as f32) as u32;
            let top = ((roi.y + roi.height * ty as f32 / 4.0) * h as f32) as u32;
            let bottom = ((roi.y + roi.height * (ty + 1) as f32 / 4.0) * h as f32) as u32;
            let mut energy = 0.0;
            let mut mean = 0.0;
            let mut n = 0u32;
            for y in (top.max(3)..bottom.min(h - 4)).step_by(3) {
                for x in (left.max(3)..right.min(w - 4)).step_by(3) {
                    let c = smooth(x, y);
                    if !(0.02..0.97).contains(&c) {
                        continue;
                    }
                    let gx = smooth(x + 2, y) - smooth(x - 2, y);
                    let gy = smooth(x, y + 2) - smooth(x, y - 2);
                    energy += gx * gx + gy * gy;
                    mean += c;
                    n += 1;
                }
            }
            values.push(if n < 16 {
                0.0
            } else {
                energy / n as f32 / (mean / n as f32).powi(2).max(0.01)
            });
        }
    }
    Ok(values)
}

pub fn suggest(samples: &[Sample]) -> Result<Suggestion> {
    ensure!(
        samples.len() >= 9,
        "A focus survey needs at least nine positions"
    );
    ensure!(samples.iter().all(|s|s.scores.len()==TILES && s.scores.iter().all(|v|v.is_finite() && *v>=0.0)),"Invalid focus survey samples");
    let ascending = samples[1].position > samples[0].position;
    ensure!(
        samples.windows(2).all(|p| if ascending {
            p[1].position > p[0].position
        } else {
            p[1].position < p[0].position
        }),
        "Survey positions must be distinct and directional"
    );
    let mut first = samples.len() - 1;
    let mut last = 0;
    let mut support = 0;
    let mut clipped = false;
    for tile in 0..TILES {
        let curve: Vec<f32> = samples.iter().map(|s| s.scores[tile]).collect();
        let mut sorted = curve.clone();
        sorted.sort_by(f32::total_cmp);
        let floor = sorted[sorted.len() / 4];
        let (peak, high) = curve
            .iter()
            .copied()
            .enumerate()
            .max_by(|a, b| a.1.total_cmp(&b.1))
            .unwrap();
        // Broad prominence, not raw argmax. A random isolated spike is refused.
        let prominence = high - floor;
        if prominence < 0.00003 || prominence < floor.max(0.00001) * 0.6 {
            continue;
        }
        let threshold = floor + prominence * 0.5;
        let mut a = peak;
        let mut b = peak;
        while a > 0 && curve[a - 1] >= threshold {
            a -= 1;
        }
        while b + 1 < curve.len() && curve[b + 1] >= threshold {
            b += 1;
        }
        if b - a < 2 {
            continue;
        }
        support += 1;
        clipped |= a == 0 || b == curve.len() - 1;
        // Two survey intervals guard the half-height crossings.
        first = first.min(a.saturating_sub(2));
        last = last.max((b + 2).min(curve.len() - 1));
    }
    ensure!(
        support >= 2,
        "No reliable focus bounds in this preview. Keep manual marks; choose a textured subject region or wider search limits."
    );
    if clipped {
        first = 0;
        last = samples.len() - 1;
    }
    Ok(Suggestion { start:samples[first].position,end:samples[last].position,supported_tiles:support,clipped,
        explanation:if clipped {"Focus support reaches a search limit. The full search range is retained; extend the rough bounds and sweep again."}else{"Preview estimate with two survey intervals of margin. Inspect both ends before applying; fine or low-contrast features may be missed."}.into() })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn survey(curve: impl Fn(usize, usize) -> f32) -> Vec<Sample> {
        (0..25)
            .map(|i| Sample {
                position: 500 + i as u16 * 10,
                scores: (0..TILES).map(|t| curve(i, t)).collect(),
            })
            .collect()
    }
    #[test]
    fn flat_controls_before_focus_positive() {
        let flat = RgbImage::from_pixel(192, 128, image::Rgb([100, 100, 100]));
        assert!(
            scores(&flat, Roi::subject())
                .unwrap()
                .iter()
                .all(|&v| v == 0.0)
        );
        assert!(suggest(&survey(|_, _| 0.01)).is_err());
        // Isolated noise peaks, and a flat exposure/gain sequence, must not trim.
        assert!(suggest(&survey(|i, t| if i == (t % 20) + 2 { 0.03 } else { 0.01 })).is_err());
        let positive =
            survey(|i, t| 0.001 + 0.03 * (-((i as f32 - (9 + t % 7) as f32) / 2.5).powi(2)).exp());
        let s = suggest(&positive).unwrap();
        assert!(!s.clipped);
        assert_eq!(s.supported_tiles, TILES);
        assert!(s.start <= 570 && s.end >= 670);
    }
    #[test]
    fn edge_peak_preserves_full_bounds_and_invalid_samples_fail() {
        let s = suggest(&survey(|i, _| {
            0.001 + 0.03 * (-(i as f32 / 3.0).powi(2)).exp()
        }))
        .unwrap();
        assert!(s.clipped);
        assert_eq!((s.start, s.end), (500, 740));
        let mut bad = survey(|_, _| 0.0);
        bad[0].scores[0] = f32::NAN;
        assert!(suggest(&bad).is_err());
    }
    #[test]
    fn gain_placebo_and_blur_positive_on_actual_score_path() {
        let texture = RgbImage::from_fn(240, 180, |x, y| {
            let v = 100.0 + 28.0 * (x as f32 * 0.45).sin() * (y as f32 * 0.37).cos();
            image::Rgb([v as u8; 3])
        });
        let gain = image::imageops::brighten(&texture, 0); // identity control
        assert_eq!(
            scores(&texture, Roi::subject()).unwrap(),
            scores(&gain, Roi::subject()).unwrap()
        );
        let mut scaled = texture.clone();
        for p in scaled.pixels_mut() {
            for c in &mut p.0 {
                *c = (*c as f32 * 1.25).round() as u8;
            }
        }
        let a = scores(&texture, Roi::subject()).unwrap();
        let b = scores(&scaled, Roi::subject()).unwrap();
        assert!(a.iter().zip(b).all(|(x, y)| (x - y).abs() < x * 0.03));
        let samples: Vec<_> = (0..25)
            .map(|i| {
                let blurred = image::imageops::blur(&texture, (i as f32 - 12.0).abs() * 0.6 + 0.1);
                Sample {
                    position: 1000 + i * 10,
                    scores: scores(&blurred, Roi::subject()).unwrap(),
                }
            })
            .collect();
        let suggestion = suggest(&samples).unwrap();
        assert!(!suggestion.clipped);
        assert!(suggestion.start < 1120 && suggestion.end > 1120);
    }
}
