//! How finely a capture's focus positions sample its depth of field.
//!
//! For every recorded plane the first exposure is decoded and, per 64 px
//! tile, the energy of the 4-neighbour Laplacian of one green site plane is
//! taken: unblurred, two sensor pixels apart, so it follows the finest detail
//! the lens delivers. A tile's energy against focus position rises to a peak
//! and falls; the width of that peak at half height, in the camera's focus
//! units, is how far a point stays sharp. The median over tiles whose peak
//! lies inside the run, well above their own out-of-focus level, is the
//! run's sharp width.
//!
//! MEASURED (2026-11-20, `experiments/capture-pipeline-2026-11-20`): on the
//! A7CR scarab stack (step 8) the width was 14.3 planes (114 units); renders
//! from every second plane lost nothing measurable where signal dominates and
//! from every fourth 2-3 % of detail amplitude. So a step of width / 7 is
//! taken as safe (it lost nothing) and width / 3.6 as the edge. This is one
//! subject's evidence; the report says so.
//!
//! Read-only over the capture. The measure compares a tile with itself
//! across focus; it says nothing about image quality.

use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde::Serialize;
use serde_json::json;
use std::path::{Path, PathBuf};
use strehl_core::pixel_shift::cfa_colour;

use crate::pixel_shift_cmd::recorded_groups;

#[derive(clap::Args, Debug)]
pub struct FocusStepArgs {
    /// Capture run folder (a stack, or a short survey taken to calibrate).
    pub dir: PathBuf,
    /// Write the result as JSON here.
    #[arg(long)]
    pub json: Option<PathBuf>,
    /// Use at most this many planes, evenly spread (0: all).
    #[arg(long, default_value_t = 0)]
    pub max_planes: usize,
}

/// Tile edge in green-site-plane samples (64 sensor pixels).
const TILE: usize = 32;
/// A tile counts when its peak stands this far above its out-of-focus level.
const PEAK_OVER_FLOOR: f64 = 6.0;
/// Tiles needed for a width to be reported.
const MIN_TILES: usize = 30;
/// Step = width / SAFE lost nothing measurable on the scarab stack.
pub const SAFE: f64 = 7.0;
/// Step = width / EDGE lost 2-3 % of detail amplitude there.
pub const EDGE: f64 = 3.6;

#[derive(Clone, Debug, Serialize)]
pub struct FocusStep {
    /// Planes measured, and their focus positions' typical spacing (units).
    pub planes: usize,
    pub spacing: f64,
    pub tiles: usize,
    pub tiles_measured: usize,
    /// Median width of a tile's sharpness peak at half height (focus units),
    /// with the 10th and 90th percentiles; `None` when too few tiles peak
    /// inside the run.
    pub width: Option<f64>,
    pub width_p10: Option<f64>,
    pub width_p90: Option<f64>,
    /// The step the width supports (units), and the spacing over it.
    pub suggested_step: Option<u32>,
    pub oversampling: Option<f64>,
    /// Plain-language reading of the result.
    pub summary: String,
}

/// Fine-detail energy per tile of one decoded exposure.
fn tile_energy(f: &strehl_raw::Frame) -> (usize, Vec<f64>) {
    let (ax, ay) = (f.active.x, f.active.y);
    let (w, h) = (f.active.width / 2, f.active.height / 2);
    // The first green site of each 2x2 cell, in active coordinates.
    let (gx, gy) = if cfa_colour(1, 0) == 1 {
        (1, 0)
    } else {
        (0, 1)
    };
    let black = f.levels.black;
    let at = |i: usize, j: usize| -> f32 {
        f32::from(f.data[(ay + 2 * j + gy) * f.stride + ax + 2 * i + gx]) - black
    };
    let (tw, th) = (w / TILE, h / TILE);
    let rows: Vec<Vec<f64>> = (0..th)
        .into_par_iter()
        .map(|ty| {
            let mut row = vec![0.0f64; tw];
            for j in ty * TILE..(ty + 1) * TILE {
                if j == 0 || j + 1 >= h {
                    continue;
                }
                for (tx, cell) in row.iter_mut().enumerate() {
                    let mut sum = 0.0f64;
                    for i in tx * TILE..(tx + 1) * TILE {
                        if i == 0 || i + 1 >= w {
                            continue;
                        }
                        let l = at(i - 1, j) + at(i + 1, j) + at(i, j - 1) + at(i, j + 1)
                            - 4.0 * at(i, j);
                        sum += f64::from(l * l);
                    }
                    *cell += sum;
                }
            }
            row
        })
        .collect();
    (tw, rows.into_iter().flatten().collect())
}

fn percentile(sorted: &[f64], q: f64) -> f64 {
    let k = ((sorted.len() - 1) as f64 * q).round() as usize;
    sorted[k]
}

/// Width at half height of one tile's curve, by linear interpolation of the
/// crossing positions; `None` when a crossing lies outside the run.
fn half_width(positions: &[f64], curve: &[f64]) -> Option<(usize, f64)> {
    let n = curve.len();
    let mut sorted = curve.to_vec();
    sorted.sort_by(f64::total_cmp);
    let floor = percentile(&sorted, 0.1);
    let (at, &peak) = curve.iter().enumerate().max_by(|a, b| a.1.total_cmp(b.1))?;
    if !(peak > PEAK_OVER_FLOOR * floor) || at == 0 || at + 1 == n {
        return None;
    }
    let half = floor + (peak - floor) / 2.0;
    let cross = |from: usize, to: usize| -> f64 {
        let (a, b) = (curve[from] - half, curve[to] - half);
        positions[from] + (positions[to] - positions[from]) * a / (a - b)
    };
    let mut lo = at;
    while lo > 0 && curve[lo] > half {
        lo -= 1;
    }
    let mut hi = at;
    while hi + 1 < n && curve[hi] > half {
        hi += 1;
    }
    if curve[lo] > half || curve[hi] > half {
        return None;
    }
    Some((at, (cross(hi - 1, hi) - cross(lo, lo + 1)).abs()))
}

/// Measures a run. Planes are ordered by focus position; repeated positions
/// (retakes, bursts) are measured once.
pub fn measure(dir: &Path, max_planes: usize) -> Result<FocusStep> {
    let mut planes: Vec<(f64, PathBuf)> = Vec::new();
    for g in recorded_groups(dir)? {
        let (Some(target), Some(first)) = (g.target, g.files.iter().find(|f| f.durable)) else {
            continue;
        };
        planes.push((target as f64, first.path.clone()));
    }
    planes.sort_by(|a, b| a.0.total_cmp(&b.0));
    planes.dedup_by(|a, b| a.0 == b.0);
    if max_planes > 0 && planes.len() > max_planes {
        let n = planes.len();
        planes = (0..max_planes)
            .map(|k| planes[k * (n - 1) / (max_planes - 1).max(1)].clone())
            .collect();
    }
    ensure!(
        planes.len() >= 5,
        "{} has {} measurable focus positions; at least 5 are needed",
        dir.display(),
        planes.len()
    );
    // At most eight exposures decoded at once: bounded memory, and room for
    // a capture running beside it.
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(8.min(rayon::current_num_threads()))
        .build()?;
    let energies: Vec<(usize, Vec<f64>)> = pool.install(|| {
        planes
            .par_iter()
            .map(|(_, path)| -> Result<(usize, Vec<f64>)> {
                let frame = strehl_raw::decode(path).with_context(|| path.display().to_string())?;
                Ok(tile_energy(&frame))
            })
            .collect::<Result<_>>()
    })?;
    let tiles = energies[0].1.len();
    ensure!(
        energies.iter().all(|e| e.1.len() == tiles),
        "Exposures of different sizes in one run"
    );
    let positions: Vec<f64> = planes.iter().map(|p| p.0).collect();
    let mut gaps: Vec<f64> = positions.windows(2).map(|w| w[1] - w[0]).collect();
    gaps.sort_by(f64::total_cmp);
    let spacing = gaps[gaps.len() / 2];
    let mut widths: Vec<f64> = (0..tiles)
        .into_par_iter()
        .filter_map(|t| {
            let curve: Vec<f64> = energies.iter().map(|e| e.1[t]).collect();
            half_width(&positions, &curve).map(|(_, w)| w)
        })
        .collect();
    widths.sort_by(f64::total_cmp);
    let measured = widths.len();
    let mut result = FocusStep {
        planes: planes.len(),
        spacing,
        tiles,
        tiles_measured: measured,
        width: None,
        width_p10: None,
        width_p90: None,
        suggested_step: None,
        oversampling: None,
        summary: String::new(),
    };
    if measured < MIN_TILES {
        result.summary = format!(
            "Not measurable: {measured} of {tiles} tiles come into and out of focus inside this run (at least {MIN_TILES} are needed). Survey a range that holds sharp detail with room on both sides."
        );
        return Ok(result);
    }
    let width = percentile(&widths, 0.5);
    result.width = Some(width);
    result.width_p10 = Some(percentile(&widths, 0.1));
    result.width_p90 = Some(percentile(&widths, 0.9));
    let step = (width / SAFE).floor().max(1.0);
    result.suggested_step = Some(step as u32);
    let oversampling = step / spacing;
    result.oversampling = Some(oversampling);
    result.summary = if width < 2.0 * spacing {
        format!(
            "Detail stays sharp over about {width:.0} focus units, under two of this run's steps of {spacing:.0}: the planes are too far apart to measure it well, and fine detail between them may be lost. A step of {step:.0} is suggested."
        )
    } else if oversampling >= 1.4 {
        format!(
            "Detail stays sharp over about {width:.0} focus units. A step of {step:.0} would have been enough here, {oversampling:.1} times this run's {spacing:.0}: about {:.0} % of the planes, the time and the disk. (Width / {SAFE}; measured on one subject so far.)",
            100.0 / oversampling
        )
    } else {
        format!(
            "Detail stays sharp over about {width:.0} focus units; this run's step of {spacing:.0} suits it (suggested {step:.0})."
        )
    };
    Ok(result)
}

pub fn run(args: &FocusStepArgs) -> Result<()> {
    let r = measure(&args.dir, args.max_planes)?;
    println!("run             : {}", args.dir.display());
    println!(
        "planes          : {} measured, spaced {:.1} focus units",
        r.planes, r.spacing
    );
    println!(
        "tiles           : {} of {} peak inside the run",
        r.tiles_measured, r.tiles
    );
    if let (Some(w), Some(lo), Some(hi)) = (r.width, r.width_p10, r.width_p90) {
        println!("sharp width     : {w:.1} focus units (10th-90th percentile {lo:.1}-{hi:.1})");
        println!(
            "suggested step  : {} (width / {SAFE}); the edge is width / {EDGE} = {:.0}",
            r.suggested_step.unwrap_or(0),
            (w / EDGE).floor()
        );
    }
    println!("summary         : {}", r.summary);
    if let Some(path) = &args.json {
        std::fs::write(path, serde_json::to_vec_pretty(&json!(r))?)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A Gaussian sharpness curve of known width sampled at a known step is
    /// measured within a tenth of a step.
    #[test]
    fn half_width_of_a_sampled_peak() {
        for (width, step, centre) in [
            (114.0, 8.0, 403.0),
            (40.0, 16.0, 250.0),
            (300.0, 20.0, 330.0),
        ] {
            let sigma: f64 = width / (2.0 * (2.0f64 * 2f64.ln()).sqrt());
            let positions: Vec<f64> = (0..48).map(|k| 10.0 + k as f64 * step).collect();
            let curve: Vec<f64> = positions
                .iter()
                .map(|&p| 1.0 + 50.0 * (-(p - centre).powi(2) / (2.0 * sigma * sigma)).exp())
                .collect();
            let measured = half_width(&positions, &curve).map(|w| w.1);
            if (centre - 10.0) > width && (10.0 + 47.0 * step - centre) > width {
                let m = measured.unwrap();
                assert!(
                    (m - width).abs() < 0.1 * step + 0.02 * width,
                    "{width} {step}: {m}"
                );
            } else {
                assert!(measured.is_none(), "{width} {step}");
            }
        }
    }

    /// A curve whose peak touches either end of the run, or barely rises
    /// above its floor, is not measured.
    #[test]
    fn edge_and_flat_curves_are_not_measured() {
        let positions: Vec<f64> = (0..20).map(f64::from).collect();
        let rising: Vec<f64> = (0..20).map(|k| 1.0 + f64::from(k)).collect();
        assert!(half_width(&positions, &rising).is_none());
        let flat: Vec<f64> = (0..20).map(|k| 1.0 + 0.1 * f64::from(k % 3)).collect();
        assert!(half_width(&positions, &flat).is_none());
    }
}
