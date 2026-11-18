//! Two-frame noise structure of a static scene (plan capture 1 control).
//! Read-only over the capture folders.
//!
//! `cargo run --release -p strehl-raw --example a7cr-pair-noise -- RAW_A RAW_B`
//!
//! `D = A - k B` per CFA channel per 32 x 32-site tile, with `k` the tile's
//! own mean ratio (removes illumination drift locally; scene and fixed
//! pattern cancel). Reports per channel:
//! - pair-difference photon transfer: `var(D) / 2` against the tile mean
//!   signal, binned, and the slope over 200..9000 DN;
//! - the correlation of `D` between same-colour neighbours at lags (1,0),
//!   (0,1), (1,1), (2,0) in channel-plane units, and between each channel and
//!   its horizontal/vertical different-colour neighbour. A clean raw has all of
//!   these at about 0; raw-level noise filtering makes them positive.
#![allow(clippy::needless_range_loop)] // four CFA channels indexed in parallel arrays
use anyhow::Result;
use serde_json::json;

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    anyhow::ensure!(args.len() == 2, "usage: RAW_A RAW_B");
    let a = strehl_raw::decode(std::path::Path::new(&args[0]))?;
    let b = strehl_raw::decode(std::path::Path::new(&args[1]))?;
    let r = a.active;
    let black = f64::from(a.levels.black);
    let white = f64::from(a.levels.white);
    let (w2, h2) = (r.width / 2, r.height / 2);
    // Channel planes, black-subtracted.
    let plane = |f: &strehl_raw::Frame, c: usize| -> Vec<f64> {
        let (dy, dx) = (c / 2, c % 2);
        let mut v = Vec::with_capacity(w2 * h2);
        for y in 0..h2 {
            let row = &f.data[(r.y + 2 * y + dy) * f.stride + r.x..][..r.width];
            for x in 0..w2 {
                v.push(f64::from(row[2 * x + dx]) - black);
            }
        }
        v
    };
    const T: usize = 32;
    let names = ["R", "G1", "G2", "B"];
    let mut d_planes: Vec<Vec<f64>> = Vec::new();
    let mut valid: Vec<Vec<bool>> = Vec::new();
    let mut out = serde_json::Map::new();
    for c in 0..4 {
        let (pa, pb) = (plane(&a, c), plane(&b, c));
        let mut d = vec![0f64; w2 * h2];
        let mut ok = vec![false; w2 * h2];
        let mut bins = vec![[0f64; 3]; 48];
        for ty in 0..h2 / T {
            for tx in 0..w2 / T {
                let idx = |i: usize, j: usize| (ty * T + i) * w2 + tx * T + j;
                let (mut sa, mut sb, mut mx) = (0f64, 0f64, 0f64);
                for i in 0..T {
                    for j in 0..T {
                        sa += pa[idx(i, j)];
                        sb += pb[idx(i, j)];
                        mx = mx.max(pa[idx(i, j)]).max(pb[idx(i, j)]);
                    }
                }
                if mx >= 0.95 * (white - black) || sb <= 0.0 {
                    continue;
                }
                let k = sa / sb;
                let n = (T * T) as f64;
                let (mut s1, mut s2) = (0f64, 0f64);
                for i in 0..T {
                    for j in 0..T {
                        let v = pa[idx(i, j)] - k * pb[idx(i, j)];
                        d[idx(i, j)] = v;
                        ok[idx(i, j)] = true;
                        s1 += v;
                        s2 += v * v;
                    }
                }
                // var(D) = var(A) + k^2 var(B) ~ (1 + k^2) var at the tile mean.
                let var = (s2 - s1 * s1 / n) / (n - 1.0) / (1.0 + k * k);
                let s = 0.5 * (sa / n + sb * k / n);
                let bin = ((s.max(1.0).ln() / 16384f64.ln()) * 48.0) as usize;
                let e = &mut bins[bin.min(47)];
                e[0] += s;
                e[1] += var;
                e[2] += 1.0;
            }
        }
        // Slope over 200..9000 DN, ordinary least squares on tile bins.
        let pts: Vec<(f64, f64)> = bins
            .iter()
            .filter(|e| e[2] >= 20.0)
            .map(|e| (e[0] / e[2], e[1] / e[2]))
            .filter(|p| (200.0..9000.0).contains(&p.0))
            .collect();
        let n = pts.len() as f64;
        let (sx, sy) = pts.iter().fold((0., 0.), |a, p| (a.0 + p.0, a.1 + p.1));
        let sxx: f64 = pts.iter().map(|p| p.0 * p.0).sum();
        let sxy: f64 = pts.iter().map(|p| p.0 * p.1).sum();
        let slope = (n * sxy - sx * sy) / (n * sxx - sx * sx);
        let icpt = (sy - slope * sx) / n;
        out.insert(
            names[c].into(),
            json!({"pair_gain_dn_per_e": slope, "intercept_dn2": icpt,
                   "bins": pts.iter().map(|p| [p.0, p.1, p.1 / p.0]).collect::<Vec<_>>()}),
        );
        d_planes.push(d);
        valid.push(ok);
    }
    // Same-colour correlations.
    let corr = |c1: usize, c2: usize, dx: usize, dy: usize| -> f64 {
        let (mut sab, mut saa, mut sbb) = (0f64, 0f64, 0f64);
        for y in 0..h2 - dy {
            for x in 0..w2 - dx {
                let (i, j) = (y * w2 + x, (y + dy) * w2 + x + dx);
                if valid[c1][i] && valid[c2][j] {
                    let (p, q) = (d_planes[c1][i], d_planes[c2][j]);
                    sab += p * q;
                    saa += p * p;
                    sbb += q * q;
                }
            }
        }
        sab / (saa * sbb).sqrt()
    };
    let mut same = serde_json::Map::new();
    for c in 0..4 {
        same.insert(
            names[c].into(),
            json!({"(1,0)": corr(c, c, 1, 0), "(0,1)": corr(c, c, 0, 1),
                   "(1,1)": corr(c, c, 1, 1), "(2,0)": corr(c, c, 2, 0)}),
        );
    }
    // Different-colour neighbours: R-G1 horizontal, R-G2 vertical,
    // G1-B vertical, G2-B horizontal (same 2x2 cell).
    let cross = json!({"R-G1": corr(0, 1, 0, 0), "R-G2": corr(0, 2, 0, 0),
                       "G1-B": corr(1, 3, 0, 0), "G2-B": corr(2, 3, 0, 0), "R-B": corr(0, 3, 0, 0),
                       "G1-G2": corr(1, 2, 0, 0)});
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({"a": args[0], "b": args[1], "transfer": out,
            "same_colour_corr": same, "cross_colour_corr_same_cell": cross}))?
    );
    Ok(())
}
