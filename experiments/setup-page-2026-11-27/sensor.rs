//! Prototype of the Setup page's sensor measurement from lit bursts
//! (spec section 6.2): gain by photon transfer, the code the data clip at,
//! and the level the response stays linear to. Read-only over the folders.
//!
//! `cargo run --release -p strehl-raw --example setup-sensor -- OUT.json DIR=SECONDS...`
//!
//! Each DIR is one burst: fixed focus (far out of focus), fixed ISO, one
//! shutter time. Per burst and CFA position:
//!
//! - every photosite's temporal mean and unbiased variance, with the light's
//!   frame-to-frame drift removed (the drift is read from photosites between
//!   100 DN above black and 50 % of the 14-bit range, so clipped ones cannot bias it);
//! - mean and variance in 128 DN bins of signal above black, with no
//!   exclusion near white: the fall of variance toward the top is the
//!   measurement;
//! - the histogram's top: the highest code present and how many samples sit
//!   on it and just under it.
//!
//! Across bursts, for each pair of consecutive shutter times: the ratio of
//! the longer burst's mean to the shorter's, per photosite, binned by the
//! longer burst's level. It is flat while the sensor is linear and falls
//! where it stops; the light's drift between bursts moves the flat value
//! only.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};

const BIN: f64 = 128.0;
const BINS: usize = 512;
const NAMES: [&str; 4] = ["R", "G1", "G2", "B"];

fn raws(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)?
        .flatten()
        .map(|e| e.path())
        .filter(|p| strehl_raw::is_raw_path(p))
        .collect();
    v.sort();
    Ok(v)
}

struct Series {
    name: String,
    seconds: f64,
    frames: usize,
    iso: Option<f32>,
    black: f64,
    declared_white: f64,
    width: usize,
    /// Temporal mean per photosite, raw codes.
    mean: Vec<f32>,
    /// `[channel][bin] = (sum S, sum var, count)`.
    bins: Vec<Vec<[f64; 3]>>,
    drift_sd: [f64; 4],
    frame_means: Vec<[f64; 4]>,
    /// `[channel] = (top code, samples on it, samples within 16 under it, samples)`.
    top: [(usize, u64, u64, u64); 4],
}

fn series(dir: &Path, seconds: f64) -> Result<Series> {
    let files = raws(dir)?;
    ensure!(
        files.len() >= 4,
        "{}: need at least 4 frames",
        dir.display()
    );
    let first = strehl_raw::decode(&files[0])?;
    let a = first.active;
    let black = f64::from(first.levels.black);
    let n = a.width * a.height;
    let reference: Vec<u16> = (0..a.height)
        .flat_map(|y| first.data[(a.y + y) * first.stride + a.x..][..a.width].to_vec())
        .collect();
    // Mid-tone photosites carry the drift estimate.
    let (lo, hi) = (black + 100.0, black + 0.5 * 16383.0);
    let mut sum = vec![0f32; n];
    let mut sq = vec![0f32; n];
    let mut means: Vec<[f64; 4]> = Vec::new();
    let mut hist = vec![vec![0u64; 65536]; 4];
    for batch in files.chunks(4) {
        let frames: Vec<strehl_raw::Frame> = batch
            .par_iter()
            .map(|p| strehl_raw::decode(p).with_context(|| p.display().to_string()))
            .collect::<Result<_>>()?;
        for f in &frames {
            ensure!(
                f.active == a && f.stride == first.stride,
                "geometry changed"
            );
            let rows: Vec<([f64; 8], Vec<Vec<u32>>)> = sum
                .par_chunks_mut(a.width)
                .zip(sq.par_chunks_mut(a.width))
                .zip(reference.par_chunks(a.width))
                .enumerate()
                .map(|(y, ((s, q), r))| {
                    let row = &f.data[(a.y + y) * f.stride + a.x..][..a.width];
                    let mut cm = [0f64; 8];
                    // The top 512 codes under 65536 would be too wide a
                    // table per row: count codes in a sparse per-row list.
                    let mut top: Vec<Vec<u32>> = vec![Vec::new(); 2];
                    for x in 0..a.width {
                        let v = row[x];
                        let d = f32::from(v) - f32::from(r[x]);
                        s[x] += d;
                        q[x] += d * d;
                        let c = 2 * (y % 2) + x % 2;
                        let rv = f64::from(r[x]);
                        if rv > lo && rv < hi {
                            cm[c] += f64::from(v) - black;
                            cm[4 + c] += 1.0;
                        }
                        top[x % 2].push(u32::from(v));
                    }
                    (cm, top)
                })
                .collect();
            let mut fm = [0f64; 8];
            for (y, (r, top)) in rows.iter().enumerate() {
                for c in 0..8 {
                    fm[c] += r[c];
                }
                for (px, list) in top.iter().enumerate() {
                    let h = &mut hist[2 * (y % 2) + px];
                    for &v in list {
                        h[v as usize] += 1;
                    }
                }
            }
            means.push([0, 1, 2, 3].map(|c| fm[c] / fm[4 + c].max(1.0)));
        }
    }
    let k = means.len() as f64;
    let mut drift = [0f64; 4];
    for c in 0..4 {
        let m = means.iter().map(|v| v[c]).sum::<f64>() / k;
        drift[c] = means.iter().map(|v| (v[c] / m - 1.0).powi(2)).sum::<f64>() / (k - 1.0);
    }
    // A colour with no mid-tone photosites takes green's drift: the light's
    // level is common to the colours.
    let green = 0.5 * (drift[1] + drift[2]);
    for d in &mut drift {
        if !d.is_finite() {
            *d = green;
        }
    }
    let mut mean = vec![0f32; n];
    mean.par_iter_mut().enumerate().for_each(|(i, m)| {
        *m = f32::from(reference[i]) + sum[i] / k as f32;
    });
    let bins = (0..a.height)
        .into_par_iter()
        .fold(
            || vec![vec![[0f64; 3]; BINS]; 4],
            |mut acc, y| {
                for x in 0..a.width {
                    let i = y * a.width + x;
                    let c = 2 * (y % 2) + x % 2;
                    let mean_d = f64::from(sum[i]) / k;
                    let var = (f64::from(sq[i]) - k * mean_d * mean_d) / (k - 1.0);
                    let s = f64::from(reference[i]) + mean_d - black;
                    if s <= 0.0 {
                        continue;
                    }
                    let var = var - s * s * drift[c];
                    let b = ((s / BIN) as usize).min(BINS - 1);
                    acc[c][b][0] += s;
                    acc[c][b][1] += var;
                    acc[c][b][2] += 1.0;
                }
                acc
            },
        )
        .reduce(
            || vec![vec![[0f64; 3]; BINS]; 4],
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
    let mut top = [(0usize, 0u64, 0u64, 0u64); 4];
    for c in 0..4 {
        let h = &hist[c];
        let t = h.iter().rposition(|&v| v > 0).unwrap_or(0);
        let under: u64 = h[t.saturating_sub(16)..t].iter().sum();
        top[c] = (t, h[t], under, h.iter().sum());
    }
    Ok(Series {
        name: dir.file_name().unwrap().to_string_lossy().to_string(),
        seconds,
        frames: files.len(),
        iso: first.iso,
        black,
        declared_white: f64::from(first.levels.white),
        width: a.width,
        mean,
        bins,
        drift_sd: drift.map(f64::sqrt),
        frame_means: means,
        top,
    })
}

/// Weighted fit of var = r2 + g S; returns (g, r2).
fn fit(points: &[(f64, f64, f64)]) -> (f64, f64) {
    let (mut g, mut r2) = (0.4, 1.8);
    for _ in 0..8 {
        let (mut sw, mut sx, mut sy, mut sxx, mut sxy) = (0f64, 0f64, 0f64, 0f64, 0f64);
        for &(s, v, n) in points {
            let pred = (r2 + g * s).max(1e-3);
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
    }
    (g, r2)
}

/// The longer burst's mean over the shorter's, per channel, by the longer's
/// level: `[channel][bin] = (level, ratio, count)`.
fn ratios(short: &Series, long: &Series) -> Vec<Vec<[f64; 3]>> {
    let w = short.width;
    let acc = (0..short.mean.len() / w)
        .into_par_iter()
        .fold(
            || vec![vec![[0f64; 3]; BINS]; 4],
            |mut acc, y| {
                for x in 0..w {
                    let i = y * w + x;
                    let c = 2 * (y % 2) + x % 2;
                    let (a, b) = (
                        f64::from(short.mean[i]) - short.black,
                        f64::from(long.mean[i]) - long.black,
                    );
                    if a < 64.0 {
                        continue;
                    }
                    let bin = ((b / BIN).max(0.0) as usize).min(BINS - 1);
                    acc[c][bin][0] += b;
                    acc[c][bin][1] += a;
                    acc[c][bin][2] += 1.0;
                }
                acc
            },
        )
        .reduce(
            || vec![vec![[0f64; 3]; BINS]; 4],
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
    acc.into_iter()
        .map(|ch| {
            ch.into_iter()
                .filter(|b| b[2] >= 2000.0)
                .map(|b| [b[0] / b[2], b[0] / b[1], b[2]])
                .collect()
        })
        .collect()
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    ensure!(args.len() >= 2, "usage: OUT.json DIR=SECONDS...");
    let mut all = Vec::new();
    for a in &args[1..] {
        let (dir, seconds) = a.rsplit_once('=').context("DIR=SECONDS")?;
        let began = std::time::Instant::now();
        let s = series(Path::new(dir), seconds.parse()?)?;
        eprintln!(
            "{} {} s: {} frames, drift G1 {:.4}, top G1 {:?} ({:.1} s)",
            s.name,
            s.seconds,
            s.frames,
            s.drift_sd[1],
            s.top[1],
            began.elapsed().as_secs_f64()
        );
        all.push(s);
    }
    all.sort_by(|a, b| a.seconds.total_cmp(&b.seconds));
    let mut out_series = Vec::new();
    for s in &all {
        out_series.push(json!({
            "name": s.name, "seconds": s.seconds, "frames": s.frames, "iso": s.iso,
            "black": s.black, "declared_white": s.declared_white,
            "drift_rel_sd": s.drift_sd, "frame_means": s.frame_means,
            "top": (0..4).map(|c| json!({"channel": NAMES[c], "code": s.top[c].0, "on_it": s.top[c].1,
                                         "within_16_under": s.top[c].2, "samples": s.top[c].3})).collect::<Vec<_>>(),
            "bins": (0..4).map(|c| s.bins[c].iter().filter(|b| b[2] >= 500.0)
                .map(|b| [b[0] / b[2], b[1] / b[2], b[2]]).collect::<Vec<_>>()).collect::<Vec<_>>(),
        }));
    }
    // One fit per channel over every burst's bins from 30 DN to `limit`.
    let mut fits = Vec::new();
    for limit in [4000.0, 8000.0, 12000.0] {
        let mut row = serde_json::Map::new();
        for (c, name) in NAMES.iter().enumerate() {
            let mut p = Vec::new();
            for s in &all {
                for b in &s.bins[c] {
                    if b[2] >= 500.0 {
                        let m = b[0] / b[2];
                        if (30.0..=limit).contains(&m) {
                            p.push((m, b[1] / b[2], b[2]));
                        }
                    }
                }
            }
            if p.len() >= 3 {
                let (g, r2) = fit(&p);
                row.insert(
                    (*name).into(),
                    json!({"gain": g, "intercept": r2, "points": p.len()}),
                );
            }
        }
        fits.push(json!({"to_dn": limit, "fit": row}));
    }
    let mut pairs = Vec::new();
    for w in all.windows(2) {
        if w[1].seconds > w[0].seconds * 1.2 && w[0].mean.len() == w[1].mean.len() {
            pairs.push(json!({
                "short": w[0].seconds, "long": w[1].seconds, "times": w[1].seconds / w[0].seconds,
                "ratio": ratios(&w[0], &w[1]),
            }));
        }
    }
    let out: Value = json!({"series": out_series, "fits": fits, "pairs": pairs});
    std::fs::write(&args[0], serde_json::to_string(&out)?)?;
    println!("wrote {}", args[0]);
    Ok(())
}
