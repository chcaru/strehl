//! A7CR photon transfer from static, strongly defocused bursts (plan capture 1).
//! Read-only over the capture folders.
//!
//! `cargo run --release -p strehl-raw --example a7cr-ptc-analysis -- OUT.json READ_DN DIR...`
//!
//! Per series (one folder, one shutter time): per-photosite temporal mean and
//! unbiased temporal variance over the declared active area, accumulated
//! against frame 0 as a per-pixel reference so f32 sums keep precision.
//! Photosites whose maximum sample is within 5% of white are excluded.
//! Illumination drift: the relative per-frame mean `m_k / m` of each channel
//! adds `S^2 var(m_k / m)` to a photosite's temporal variance; it is removed
//! analytically and reported. Bins: per CFA position, 64 log-spaced signal
//! bins; each bin's mean signal, mean variance and count.
//!
//! Fit per channel: weighted least squares of `var = r^2 + g S` over every
//! series' bins with 30 <= S <= 0.85 headroom (weights count / predicted
//! variance^2, iterated). Controls: the independent dark read noise
//! READ_DN (lens-capped darks, same ISO) against the fitted intercept; G2/G1
//! and R, B against G gains (the same photosites' conversion gain, so a
//! colour-dependent gain is a defect); and a split-half refit (even and odd
//! frames as separate series) for precision. Accumulation in f64 after the
//! per-photosite f32 stage.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};

const BINS: usize = 64;

fn raws(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)?
        .flatten()
        .map(|e| e.path())
        .filter(|p| strehl_raw::is_raw_path(p))
        .collect();
    v.sort();
    Ok(v)
}

/// One series' bins: `[channel][bin] = (sum S, sum var, count)`.
type Bins = Vec<[[f64; 3]; BINS]>;

struct Series {
    name: String,
    frames: usize,
    shutter_hint: String,
    drift: [f64; 4],
    bins: Bins,
    headroom: f64,
}

fn bin_of(s: f64) -> usize {
    ((s.max(1.0).ln() / 16384f64.ln()) * BINS as f64).min(BINS as f64 - 1.0) as usize
}

fn series(dir: &Path, files: &[PathBuf], name: String) -> Result<Series> {
    ensure!(
        files.len() >= 4,
        "{}: need at least 4 frames",
        dir.display()
    );
    let first = strehl_raw::decode(&files[0])?;
    let a = first.active;
    let (black, white) = (first.levels.black, first.levels.white);
    let near = white - 0.05 * (white - black);
    let n = a.width * a.height;
    let reference: Vec<u16> = (0..a.height)
        .flat_map(|y| first.data[(a.y + y) * first.stride + a.x..][..a.width].to_vec())
        .collect();
    let mut sum = vec![0f32; n];
    let mut sq = vec![0f32; n];
    let mut max = reference.clone();
    let mut means: Vec<[f64; 4]> = Vec::new();
    for batch in files.chunks(6) {
        let frames: Vec<strehl_raw::Frame> = batch
            .par_iter()
            .map(|p| strehl_raw::decode(p).with_context(|| p.display().to_string()))
            .collect::<Result<_>>()?;
        for f in &frames {
            ensure!(
                f.active == a && f.stride == first.stride,
                "geometry changed"
            );
            let rows: Vec<[f64; 5]> = sum
                .par_chunks_mut(a.width)
                .zip(sq.par_chunks_mut(a.width))
                .zip(max.par_chunks_mut(a.width))
                .zip(reference.par_chunks(a.width))
                .enumerate()
                .map(|(y, (((s, q), m), r))| {
                    let row = &f.data[(a.y + y) * f.stride + a.x..][..a.width];
                    let mut cm = [0f64; 5];
                    for x in 0..a.width {
                        let v = row[x];
                        let d = f32::from(v) - f32::from(r[x]);
                        s[x] += d;
                        q[x] += d * d;
                        m[x] = m[x].max(v);
                        cm[2 * (y % 2) + x % 2] += f64::from(v) - f64::from(black);
                    }
                    cm
                })
                .collect();
            let mut fm = [0f64; 4];
            for r in rows {
                for c in 0..4 {
                    fm[c] += r[c];
                }
            }
            means.push(fm.map(|v| v / (n / 4) as f64));
        }
    }
    let k = means.len() as f64;
    let mut drift = [0f64; 4];
    for c in 0..4 {
        let m = means.iter().map(|v| v[c]).sum::<f64>() / k;
        drift[c] = means.iter().map(|v| (v[c] / m - 1.0).powi(2)).sum::<f64>() / (k - 1.0);
    }
    let bins: Bins = (0..a.height)
        .into_par_iter()
        .fold(
            || vec![[[0f64; 3]; BINS]; 4],
            |mut acc, y| {
                for x in 0..a.width {
                    let i = y * a.width + x;
                    if f32::from(max[i]) >= near {
                        continue;
                    }
                    let c = 2 * (y % 2) + x % 2;
                    let mean_d = f64::from(sum[i]) / k;
                    let var = (f64::from(sq[i]) - k * mean_d * mean_d) / (k - 1.0);
                    let s = f64::from(reference[i]) + mean_d - f64::from(black);
                    if s <= 0.0 {
                        continue;
                    }
                    let var = var - s * s * drift[c];
                    let b = &mut acc[c][bin_of(s)];
                    b[0] += s;
                    b[1] += var;
                    b[2] += 1.0;
                }
                acc
            },
        )
        .reduce(
            || vec![[[0f64; 3]; BINS]; 4],
            |mut a, b| {
                for (x, y) in a.iter_mut().zip(b) {
                    for (u, v) in x.iter_mut().zip(y) {
                        for j in 0..3 {
                            u[j] += v[j];
                        }
                    }
                }
                a
            },
        );
    Ok(Series {
        name,
        frames: files.len(),
        shutter_hint: format!("{:?}", first.iso),
        drift,
        bins,
        headroom: f64::from(white - black),
    })
}

/// Weighted fit of var = r2 + g S; returns (g, r2, g standard error).
fn fit(points: &[(f64, f64, f64)]) -> (f64, f64, f64) {
    let (mut g, mut r2) = (0.4, 1.8);
    let mut se = f64::NAN;
    for _ in 0..8 {
        let (mut sw, mut sx, mut sy, mut sxx, mut sxy) = (0f64, 0f64, 0f64, 0f64, 0f64);
        for &(s, v, n) in points {
            let pred = (r2 + g * s).max(1e-3);
            // Variance of a temporal-variance estimate ~ 2 pred^2 / (frames-1)
            // per photosite; bins average `n` photosites.
            let w = n / (pred * pred);
            sw += w;
            sx += w * s;
            sy += w * v;
            sxx += w * s * s;
            sxy += w * s * v;
        }
        let det = sw * sxx - sx * sx;
        g = (sw * sxy - sx * sy) / det;
        r2 = (sxx * sy - sx * sxy) / det;
        // Reduced chi-square scaling of the slope's standard error.
        let chi: f64 = points
            .iter()
            .map(|&(s, v, n)| {
                let pred = (r2 + g * s).max(1e-3);
                n * (v - pred).powi(2) / (pred * pred)
            })
            .sum::<f64>()
            / (points.len() as f64 - 2.0).max(1.0);
        se = (sw / det * chi).sqrt();
    }
    (g, r2, se)
}

fn points(all: &[&Series], c: usize) -> Vec<(f64, f64, f64)> {
    let mut p = Vec::new();
    for s in all {
        for b in &s.bins[c] {
            if b[2] >= 256.0 {
                let mean = b[0] / b[2];
                if (30.0..=0.85 * s.headroom).contains(&mean) {
                    p.push((mean, b[1] / b[2], b[2]));
                }
            }
        }
    }
    p
}

fn report(all: &[&Series], read_dn: f64) -> Value {
    let names = ["R", "G1", "G2", "B"];
    let mut fits = serde_json::Map::new();
    let mut gains = [0f64; 4];
    for c in 0..4 {
        let p = points(all, c);
        let (g, r2, se) = fit(&p);
        gains[c] = g;
        // Residuals per point, relative.
        let worst = p
            .iter()
            .map(|&(s, v, _)| (v / (r2 + g * s) - 1.0).abs())
            .fold(0f64, f64::max);
        fits.insert(
            names[c].into(),
            json!({"gain_dn_per_e": g, "gain_se": se, "intercept_dn2": r2,
                   "read_noise_fit_dn": r2.max(0.0).sqrt(), "points": p.len(),
                   "worst_relative_residual": worst,
                   "full_well_e": all[0].headroom / g}),
        );
    }
    json!({"fits": fits, "dark_read_noise_dn": read_dn,
           "ratios": {"G2/G1": gains[2] / gains[1], "R/G": gains[0] / (0.5 * (gains[1] + gains[2])),
                      "B/G": gains[3] / (0.5 * (gains[1] + gains[2]))}})
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    ensure!(args.len() >= 3, "usage: OUT.json READ_DN DIR...");
    let read_dn: f64 = args[1].parse()?;
    let mut all = Vec::new();
    let mut even = Vec::new();
    let mut odd = Vec::new();
    for d in &args[2..] {
        let dir = PathBuf::from(d);
        let files = raws(&dir)?;
        let name = dir.file_name().unwrap().to_string_lossy().to_string();
        eprintln!("series {name}: {} frames", files.len());
        all.push(series(&dir, &files, name.clone())?);
        let pick = |r: usize| {
            files
                .iter()
                .enumerate()
                .filter(|(i, _)| i % 2 == r)
                .map(|(_, f)| f.clone())
                .collect::<Vec<_>>()
        };
        even.push(series(&dir, &pick(0), format!("{name}-even"))?);
        odd.push(series(&dir, &pick(1), format!("{name}-odd"))?);
    }
    let refs: Vec<&Series> = all.iter().collect();
    let out = json!({
        "series": all.iter().map(|s| json!({
            "name": s.name, "frames": s.frames, "iso": s.shutter_hint,
            "drift_rel_sd": s.drift.map(f64::sqrt),
            "bins": (0..4).map(|c| s.bins[c].iter().filter(|b| b[2] > 0.0)
                .map(|b| [b[0] / b[2], b[1] / b[2], b[2]]).collect::<Vec<_>>()).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
        "all": report(&refs, read_dn),
        "even": report(&even.iter().collect::<Vec<_>>(), read_dn),
        "odd": report(&odd.iter().collect::<Vec<_>>(), read_dn),
        "per_series": all.iter().map(|s| json!({"name": s.name, "fit": report(&[s], read_dn)})).collect::<Vec<_>>(),
    });
    let text = serde_json::to_string_pretty(&out)?;
    std::fs::write(&args[0], &text)?;
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"all": out["all"], "even": out["even"]["fits"]["G1"]["gain_dn_per_e"], "odd": out["odd"]["fits"]["G1"]["gain_dn_per_e"],
        "per_series": out["per_series"].as_array().unwrap().iter().map(|s| json!([s["name"], s["fit"]["fits"]["G1"]["gain_dn_per_e"], s["fit"]["fits"]["G1"]["intercept_dn2"]])).collect::<Vec<_>>(),
        "drift": out["series"].as_array().unwrap().iter().map(|s| s["drift_rel_sd"].clone()).collect::<Vec<_>>()})
        )?
    );
    Ok(())
}
