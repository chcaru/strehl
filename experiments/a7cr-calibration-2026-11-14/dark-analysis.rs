//! A7CR lens-capped dark series analysis. Read-only over the capture folders.
//!
//! `cargo run --release -p strehl-raw --example a7cr-dark-analysis -- OUT.json DIR...`
//!
//! Per series (one capture folder): per CFA channel over the declared active
//! area, the black level, temporal read noise on three bases (RMS of per-pixel
//! temporal SD = pooled, mean and median per-pixel SD), fixed-pattern DSNU with
//! the temporal share removed, row and column temporal noise (pattern noise),
//! frame-to-frame black drift, and hot pixels from the master dark. The same
//! statistics are reported for the four margins outside the active area, so a
//! masked (optical black) or synthetic margin is visible. Decoding uses
//! `strehl_raw::decode`, whose samples are checked against the linked decoder
//! by `tests/lossless-jpeg.rs`. Accumulation in f64.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::path::{Path, PathBuf};

fn raws(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)?
        .flatten()
        .map(|e| e.path())
        .filter(|p| strehl_raw::is_raw_path(p))
        .collect();
    v.sort();
    Ok(v)
}

#[derive(Clone, Copy)]
struct Rect {
    x: usize,
    y: usize,
    w: usize,
    h: usize,
}

fn quantile(v: &mut [f64], q: f64) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    let k = ((v.len() - 1) as f64 * q).round() as usize;
    *v.select_nth_unstable_by(k, |a, b| a.total_cmp(b)).1
}

fn series(dir: &Path) -> Result<Value> {
    let files = raws(dir)?;
    ensure!(files.len() >= 4, "{}: need at least 4 frames", dir.display());
    let first = strehl_raw::decode(&files[0])?;
    let (stride, bh) = (first.stride, first.buffer_height);
    let a = first.active;
    let n = files.len();
    let iso = first.iso;
    // Per-pixel sums over the whole buffer.
    let mut sum = vec![0f64; stride * bh];
    let mut sq = vec![0f64; stride * bh];
    let mut row_means: Vec<Vec<f64>> = Vec::new();
    let mut col_means: Vec<Vec<f64>> = Vec::new();
    let mut frame_means: Vec<[f64; 4]> = Vec::new();
    for batch in files.chunks(8) {
        let frames: Vec<strehl_raw::Frame> = batch
            .par_iter()
            .map(|p| strehl_raw::decode(p).with_context(|| p.display().to_string()))
            .collect::<Result<_>>()?;
        for f in &frames {
            ensure!(
                f.stride == stride && f.buffer_height == bh && f.active == a,
                "geometry changed within the series"
            );
            sum.par_chunks_mut(stride)
                .zip(sq.par_chunks_mut(stride))
                .zip(f.data.par_chunks(stride))
                .for_each(|((s, q), d)| {
                    for ((s, q), &v) in s.iter_mut().zip(q.iter_mut()).zip(d) {
                        let v = f64::from(v);
                        *s += v;
                        *q += v * v;
                    }
                });
            // Row means per channel-row over active columns, split by parity.
            let mut rm = vec![0f64; 2 * a.height];
            for y in 0..a.height {
                let row = &f.data[(a.y + y) * stride + a.x..(a.y + y) * stride + a.x + a.width];
                let (mut e, mut o) = (0f64, 0f64);
                for (x, &v) in row.iter().enumerate() {
                    if x % 2 == 0 {
                        e += f64::from(v);
                    } else {
                        o += f64::from(v);
                    }
                }
                rm[2 * y] = e / (a.width / 2) as f64;
                rm[2 * y + 1] = o / (a.width / 2) as f64;
            }
            row_means.push(rm);
            let mut cm = vec![0f64; 2 * a.width];
            for y in 0..a.height {
                let row = &f.data[(a.y + y) * stride + a.x..(a.y + y) * stride + a.x + a.width];
                for (x, &v) in row.iter().enumerate() {
                    cm[2 * x + y % 2] += f64::from(v);
                }
            }
            cm.iter_mut().for_each(|c| *c /= (a.height / 2) as f64);
            col_means.push(cm);
            let mut fm = [0f64; 4];
            for y in 0..a.height {
                let row = &f.data[(a.y + y) * stride + a.x..(a.y + y) * stride + a.x + a.width];
                for (x, &v) in row.iter().enumerate() {
                    fm[2 * (y % 2) + x % 2] += f64::from(v);
                }
            }
            fm.iter_mut()
                .for_each(|m| *m /= (a.width * a.height / 4) as f64);
            frame_means.push(fm);
        }
    }
    let nf = n as f64;
    // Region statistics by channel phase (absolute buffer parity: the active
    // origin is even, so phase 0 is R for both active and margin).
    let region = |r: Rect| -> Value {
        let mut out = serde_json::Map::new();
        for (phase, name) in ["R", "G1", "G2", "B"].iter().enumerate() {
            let (py, px) = (phase / 2, phase % 2);
            let mut means = Vec::new();
            let mut sds = Vec::new();
            for y in (r.y..r.y + r.h).filter(|y| y % 2 == py) {
                for x in (r.x..r.x + r.w).filter(|x| x % 2 == px) {
                    let i = y * stride + x;
                    let m = sum[i] / nf;
                    let var = (sq[i] - nf * m * m) / (nf - 1.0);
                    means.push(m);
                    sds.push(var.max(0.0).sqrt());
                }
            }
            if means.is_empty() {
                continue;
            }
            let k = means.len() as f64;
            let mean = means.iter().sum::<f64>() / k;
            let pooled = (sds.iter().map(|s| s * s).sum::<f64>() / k).sqrt();
            let mean_sd = sds.iter().sum::<f64>() / k;
            // Master-dark spatial variance minus the temporal share of the mean.
            let spatial = means.iter().map(|m| (m - mean).powi(2)).sum::<f64>() / (k - 1.0);
            let dsnu = (spatial - pooled * pooled / nf).max(0.0).sqrt();
            let hot = means.iter().filter(|m| **m > mean + 50.0).count();
            let warm = means.iter().filter(|m| **m > mean + 10.0).count();
            let cold = means.iter().filter(|m| **m < mean - 10.0).count();
            let noisy = sds.iter().filter(|s| **s > 5.0 * pooled).count();
            let median_sd = quantile(&mut sds.clone(), 0.5);
            let p99_sd = quantile(&mut sds, 0.99);
            out.insert(
                name.to_string(),
                json!({"pixels":means.len(),"black_mean":mean,"read_noise_pooled_rms":pooled,"read_noise_mean_sd":mean_sd,
                    "read_noise_median_sd":median_sd,"read_noise_p99_sd":p99_sd,"dsnu":dsnu,
                    "hot_gt50":hot,"warm_gt10":warm,"cold_lt10":cold,"noisy_gt5x":noisy}),
            );
        }
        Value::Object(out)
    };
    let active = Rect {
        x: a.x,
        y: a.y,
        w: a.width,
        h: a.height,
    };
    let mut margins = serde_json::Map::new();
    for (name, r) in [
        ("left", Rect { x: 0, y: a.y, w: a.x, h: a.height }),
        ("right", Rect { x: a.x + a.width, y: a.y, w: stride - a.x - a.width, h: a.height }),
        ("top", Rect { x: 0, y: 0, w: stride, h: a.y }),
        ("bottom", Rect { x: 0, y: a.y + a.height, w: stride, h: bh - a.y - a.height }),
    ] {
        if r.w > 0 && r.h > 0 {
            margins.insert(name.into(), region(r));
        }
    }
    // Pattern noise: temporal SD of row (column) means, less the pixel noise
    // share of a mean over W/2 (H/2) samples.
    let temporal_sd = |series: &[Vec<f64>], idx: usize| -> f64 {
        let m = series.iter().map(|v| v[idx]).sum::<f64>() / nf;
        (series.iter().map(|v| (v[idx] - m).powi(2)).sum::<f64>() / (nf - 1.0)).sqrt()
    };
    let rows = row_means[0].len();
    let row_sd: Vec<f64> = (0..rows).map(|i| temporal_sd(&row_means, i)).collect();
    let cols = col_means[0].len();
    let col_sd: Vec<f64> = (0..cols).map(|i| temporal_sd(&col_means, i)).collect();
    let rms = |v: &[f64]| (v.iter().map(|x| x * x).sum::<f64>() / v.len() as f64).sqrt();
    let act = region(active);
    let pixel_rn = act["G1"]["read_noise_pooled_rms"].as_f64().unwrap_or(f64::NAN);
    let row_rms = rms(&row_sd);
    let col_rms = rms(&col_sd);
    let drift: Vec<f64> = frame_means
        .iter()
        .map(|m| m.iter().sum::<f64>() / 4.0)
        .collect();
    let dmean = drift.iter().sum::<f64>() / nf;
    Ok(json!({
        "dir": dir.display().to_string(), "frames": n, "iso": iso, "camera": first.camera,
        "buffer": [stride, bh], "active": [a.x, a.y, a.width, a.height],
        "levels": {"black": first.levels.black, "white": first.levels.white},
        "active_stats": act, "margins": Value::Object(margins),
        "row_noise": {"temporal_sd_rms": row_rms, "pixel_share": pixel_rn / ((a.width / 2) as f64).sqrt(),
            "excess": (row_rms * row_rms - pixel_rn * pixel_rn / (a.width / 2) as f64).max(0.0).sqrt()},
        "column_noise": {"temporal_sd_rms": col_rms, "pixel_share": pixel_rn / ((a.height / 2) as f64).sqrt(),
            "excess": (col_rms * col_rms - pixel_rn * pixel_rn / (a.height / 2) as f64).max(0.0).sqrt()},
        "frame_black_drift": {"min": drift.iter().cloned().fold(f64::INFINITY, f64::min) - dmean,
            "max": drift.iter().cloned().fold(f64::NEG_INFINITY, f64::max) - dmean,
            "first_minus_mean": drift[0] - dmean}
    }))
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    ensure!(args.len() >= 2, "usage: a7cr-dark-analysis OUT.json DIR...");
    let mut all = Vec::new();
    for d in &args[1..] {
        let t = std::time::Instant::now();
        let v = series(Path::new(d))?;
        let g = &v["active_stats"]["G1"];
        eprintln!(
            "{d}: iso {} n {} G1 black {:.2} rn pooled {:.3} median {:.3} dsnu {:.3} hot {} ({:.1} s)",
            v["iso"], v["frames"], g["black_mean"].as_f64().unwrap_or(0.0),
            g["read_noise_pooled_rms"].as_f64().unwrap_or(0.0),
            g["read_noise_median_sd"].as_f64().unwrap_or(0.0),
            g["dsnu"].as_f64().unwrap_or(0.0), g["hot_gt50"], t.elapsed().as_secs_f64()
        );
        all.push(v);
    }
    std::fs::write(&args[0], serde_json::to_string_pretty(&all)? + "\n")?;
    Ok(())
}
