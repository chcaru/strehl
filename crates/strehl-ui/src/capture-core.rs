//! The core sample (capture calibration spec 6.2, ledger row
//! `cpf-s3-lenses`): a tile pinned under the Depth lens, shown at 100 % from
//! the three survey frames nearest its focus, with its contrast against
//! focus as a small curve and one sentence. Read from the survey's RAWs,
//! which a finished pass keeps until Start, New capture or the next
//! calibration (the owner's decision 2).

use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use eframe::egui::{Color32, ColorImage};
use rayon::prelude::*;

/// Crop side, sensor pixels (shown at 100 %).
pub(crate) const CROP: usize = 160;
/// Survey frames this far from the tile's focus give its curve.
const CURVE_REACH: f64 = 300.0;
/// Frames read for the curve at most.
const CURVE_FRAMES: usize = 16;

/// A pinned tile's sample.
#[derive(Clone, Debug)]
pub(crate) struct CoreSample {
    /// The tile on the survey's 64 px grid, and its focus.
    pub tile: (usize, usize),
    pub focus: f64,
    /// The three frames nearest its focus: position and crop.
    pub crops: Vec<(f64, ColorImage)>,
    /// Its contrast at each frame read, in focus order.
    pub curve: Vec<(f64, f32)>,
    /// "In focus at 32,742, seen in 3 survey frames".
    pub sentence: String,
}

/// Reads a tile's sample from the survey run `run` (worker thread).
pub(crate) fn read(run: &Path, tile: (usize, usize), focus: f64) -> Result<CoreSample> {
    let (shots, _) = strehl_cli::survey_cmd::shots(run)?;
    let plan = strehl_cli::survey_cmd::classify(&shots)?;
    let mut longs: Vec<(f64, PathBuf)> = plan
        .longs
        .iter()
        .map(|s| (s.focus as f64, s.path.clone()))
        .collect();
    longs.sort_by(|a, b| (a.0 - focus).abs().total_cmp(&(b.0 - focus).abs()));
    let near: Vec<(f64, PathBuf)> = longs
        .iter()
        .filter(|(p, _)| (p - focus).abs() <= CURVE_REACH)
        .take(CURVE_FRAMES)
        .cloned()
        .collect();
    anyhow::ensure!(
        !near.is_empty(),
        "No survey frame lies near this tile's focus"
    );
    // Each frame: the tile's contrast, and (for the three nearest) its crop
    // as raw camera RGB above black, normalised to the range.
    type Read = (f64, f32, Option<Vec<[f32; 3]>>);
    let read: Vec<Read> = near
        .par_iter()
        .enumerate()
        .map(|(i, (pos, path))| -> Result<Read> {
            let f = strehl_raw::decode(path).with_context(|| path.display().to_string())?;
            let tiles = strehl_cli::depth_contrast::frame_tiles(&f);
            let c = tiles
                .contrast
                .get(tile.1 * tiles.cols + tile.0)
                .copied()
                .unwrap_or(0.0);
            Ok((*pos, c, (i < 3).then(|| crop(&f, tile))))
        })
        .collect::<Result<_>>()?;
    // One display transform for the three: the brightest crop's 99.5th
    // percentile at 0.9, gamma 2.2.
    let mut all: Vec<f32> = read
        .iter()
        .filter_map(|r| r.2.as_ref())
        .flat_map(|c| c.iter().map(|p| p[0].max(p[1]).max(p[2])))
        .collect();
    all.sort_by(f32::total_cmp);
    let top = all
        .get(((all.len().max(1) - 1) as f32 * 0.995) as usize)
        .copied()
        .unwrap_or(1.0)
        .max(1e-4);
    let gain = 0.9 / top;
    let mut crops: Vec<(f64, ColorImage)> = read
        .iter()
        .filter_map(|(pos, _, c)| {
            let c = c.as_ref()?;
            let u = |v: f32| ((v * gain).clamp(0.0, 1.0).powf(1.0 / 2.2) * 255.0).round() as u8;
            Some((
                *pos,
                ColorImage::new(
                    [CROP, CROP],
                    c.iter()
                        .map(|p| Color32::from_rgb(u(p[0]), u(p[1]), u(p[2])))
                        .collect(),
                ),
            ))
        })
        .collect();
    crops.sort_by(|a, b| a.0.total_cmp(&b.0));
    let mut curve: Vec<(f64, f32)> = read.iter().map(|r| (r.0, r.1)).collect();
    curve.sort_by(|a, b| a.0.total_cmp(&b.0));
    Ok(CoreSample {
        tile,
        focus,
        sentence: format!(
            "In focus at {}, seen in {} survey frames",
            super::style::focus_units(focus.round().clamp(0.0, 65535.0) as u16),
            crops.len()
        ),
        crops,
        curve,
    })
}

/// A [`CROP`]-pixel square around a 64 px tile's centre, each sensor pixel
/// its own colour and its quad's others (white-balanced to green), above
/// black as a share of the range.
fn crop(f: &strehl_raw::Frame, tile: (usize, usize)) -> Vec<[f32; 3]> {
    let (w, h) = (f.active.width, f.active.height);
    let cx = (tile.0 * 64 + 32).min(w.saturating_sub(1));
    let cy = (tile.1 * 64 + 32).min(h.saturating_sub(1));
    let x0 = cx.saturating_sub(CROP / 2).min(w.saturating_sub(CROP)) & !1;
    let y0 = cy.saturating_sub(CROP / 2).min(h.saturating_sub(CROP)) & !1;
    let black = f.levels.black;
    let range = (f.levels.white - black).max(1.0);
    let g = f.wb_coeffs[1].max(1e-6);
    let wb = [f.wb_coeffs[0] / g, 1.0, f.wb_coeffs[2] / g]
        .map(|v| if v.is_finite() && v > 0.0 { v } else { 1.0 });
    let at = |x: usize, y: usize| {
        let x = x.min(w - 1);
        let y = y.min(h - 1);
        (f32::from(f.data[(f.active.y + y) * f.stride + f.active.x + x]) - black).max(0.0) / range
    };
    let mut out = Vec::with_capacity(CROP * CROP);
    for y in y0..y0 + CROP {
        for x in x0..x0 + CROP {
            let (qx, qy) = (x & !1, y & !1);
            let mut rgb = [0.0f32; 3];
            let mut n = [0.0f32; 3];
            for (dx, dy) in [(0, 0), (1, 0), (0, 1), (1, 1)] {
                let c =
                    strehl_core::pixel_shift::cfa_colour((qx + dx) as isize, (qy + dy) as isize);
                rgb[c] += at(qx + dx, qy + dy);
                n[c] += 1.0;
            }
            let own = strehl_core::pixel_shift::cfa_colour(x as isize, y as isize);
            let mut p = [0.0f32; 3];
            for c in 0..3 {
                p[c] = if c == own {
                    at(x, y)
                } else {
                    rgb[c] / n[c].max(1.0)
                } * wb[c];
            }
            out.push(p);
        }
    }
    out
}
