//! Scene check for owner captures: per-CFA-channel levels over the declared
//! active area and a half-resolution green plane for focus/planarity checks.
//! Read-only over the capture folders.
//!
//! `cargo run --release -p strehl-raw --example a7cr-scene-levels -- OUT_DIR RAW...`
//!
//! Per file: black-subtracted quantiles per CFA position, white headroom
//! (white - black), and the count of photosites within 2% of white. Writes
//! `<stem>.green.pgm`: 16-bit binary PGM, (G1 + G2) / 2 of each 2x2 cell,
//! black-subtracted, active area only. Decoding uses `strehl_raw::decode`
//! (checked against the linked decoder by `tests/lossless-jpeg.rs`).
use anyhow::{Context, Result};
use rayon::prelude::*;
use serde_json::json;
use std::io::Write;
use std::path::PathBuf;

fn quantile(v: &mut [u16], q: f64) -> u16 {
    let k = ((v.len() - 1) as f64 * q).round() as usize;
    *v.select_nth_unstable(k).1
}

fn main() -> Result<()> {
    let args: Vec<PathBuf> = std::env::args_os().skip(1).map(PathBuf::from).collect();
    anyhow::ensure!(args.len() >= 2, "usage: OUT_DIR RAW...");
    let out = &args[0];
    std::fs::create_dir_all(out)?;
    let reports: Vec<_> = args[1..]
        .par_iter()
        .map(|p| -> Result<serde_json::Value> {
            let f = strehl_raw::decode(p).with_context(|| p.display().to_string())?;
            let a = f.active;
            let black = f.levels.black;
            let white = f.levels.white;
            let mut chans: [Vec<u16>; 4] = Default::default();
            for y in 0..a.height {
                let row = &f.data[(a.y + y) * f.stride + a.x..][..a.width];
                for (x, &v) in row.iter().enumerate() {
                    chans[2 * (y % 2) + x % 2].push(v);
                }
            }
            let near = (white - 0.02 * (white - black)) as u16;
            let hist: Vec<Vec<u64>> = chans
                .iter()
                .map(|c| {
                    let mut h = vec![0u64; 65536];
                    c.iter().for_each(|&v| h[usize::from(v)] += 1);
                    h.truncate(16384);
                    h
                })
                .collect();
            let stats: Vec<_> = chans
                .iter_mut()
                .map(|c| {
                    let clipped = c.iter().filter(|&&v| v >= near).count();
                    let q = |c: &mut [u16], q: f64| f64::from(quantile(c, q)) - f64::from(black);
                    json!({"p01": q(c, 0.01), "p50": q(c, 0.5), "p99": q(c, 0.99),
                           "p999": q(c, 0.999), "max": q(c, 1.0), "near_white": clipped})
                })
                .collect();
            let (w2, h2) = (a.width / 2, a.height / 2);
            let mut pgm = Vec::with_capacity(w2 * h2 * 2 + 32);
            write!(pgm, "P5\n{w2} {h2}\n65535\n")?;
            for cy in 0..h2 {
                for cx in 0..w2 {
                    let mut g = 0f32;
                    for (dy, dx) in [(0, 0), (0, 1), (1, 0), (1, 1)] {
                        let (y, x) = (2 * cy + dy, 2 * cx + dx);
                        // RGGB from the even active origin: greens where x + y is odd.
                        if (x + y) % 2 == 1 {
                            g += f32::from(f.data[(a.y + y) * f.stride + a.x + x]) - black;
                        }
                    }
                    let v = (g / 2.0).clamp(0.0, 65535.0) as u16;
                    pgm.extend_from_slice(&v.to_be_bytes());
                }
            }
            let stem = p
                .file_name()
                .unwrap()
                .to_string_lossy()
                .replace(".ARW.straw", "")
                .replace(".ARW", "");
            std::fs::write(out.join(format!("{stem}.green.pgm")), pgm)?;
            Ok(
                json!({"file": p.display().to_string(), "iso": f.iso, "black": black,
                      "white": white, "headroom": white - black,
                      "active": [a.x, a.y, a.width, a.height], "channels": stats, "hist": hist}),
            )
        })
        .collect::<Result<_>>()?;
    std::fs::write(out.join("levels.json"), serde_json::to_string(&reports)?)?;
    let summary: Vec<_> = reports
        .iter()
        .map(|r| {
            let mut r = r.clone();
            r.as_object_mut().unwrap().remove("hist");
            r
        })
        .collect();
    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}
