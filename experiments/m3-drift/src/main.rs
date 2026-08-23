// Scratch benchmark: measure inter-frame drift on a real in-camera focus bracket.
//
// Two questions:
//   1. Is the drift across a stack LINEAR in frame index, or does it need a
//      QUADRATIC term? Focus breathing scales magnification as 1/(u - d - f),
//      which is hyperbolic in focus distance, so a straight line may not fit.
//   2. What does a two-phase (coarse global, then per-frame independent)
//      aligner actually cost? That is the largest unpinned term in the budget.
//
// The estimator is validated against a synthetic warp with known parameters
// before it is trusted on real data. Run `--synthetic` first.
//
// M6 EXTENSION. The crate originally aggregated per-tile displacements into one
// RMS number and threw the tiles away. `--m6` and `--m6-control` keep them:
// every tile's residual, correlation peak, contrast and rejection reason is
// written to CSV, together with a per-tile focus profile over the whole stack,
// so that the 0.6-1.3 px residual (SYNTHESIS fact 18) can be regressed against
// depth. Nothing in the original two modes changed behaviour: `fit_stage` now
// delegates to `fit_stage_at`, which is the single code path both use, so
// `--synthetic` still validates the code that produces the M6 numbers.

use rayon::prelude::*;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

struct Plane {
    d: Vec<f32>,
    w: usize,
    h: usize,
}

/// Black-subtracted green luma at CFA plane resolution (active/2).
///
/// RGGB: within each 2x2 quad, G1 is at (1,0) and G2 at (0,1).
fn green_plane(path: &Path) -> Result<Plane, String> {
    let img = rawler::decode_file(path).map_err(|e| format!("{e:?}"))?;
    let data = match img.data {
        rawler::RawImageData::Integer(d) => d,
        rawler::RawImageData::Float(_) => return Err("float raw".into()),
    };
    let stride = img.width;
    let (ax, ay, aw, ah) = img
        .active_area
        .map(|r| (r.p.x, r.p.y, r.d.w, r.d.h))
        .unwrap_or((0, 0, img.width, img.height));
    let black = img
        .blacklevel
        .levels
        .first()
        .map(|r| r.n as f32 / r.d as f32)
        .unwrap_or(0.0);

    let (pw, ph) = (aw / 2, ah / 2);
    let mut out = vec![0f32; pw * ph];
    for py in 0..ph {
        let r0 = (ay + 2 * py) * stride + ax;
        let r1 = (ay + 2 * py + 1) * stride + ax;
        for px in 0..pw {
            let g1 = data[r0 + 2 * px + 1] as f32 - black;
            let g2 = data[r1 + 2 * px] as f32 - black;
            out[py * pw + px] = 0.5 * (g1 + g2);
        }
    }
    Ok(Plane {
        d: out,
        w: pw,
        h: ph,
    })
}

fn downsample(p: &Plane, f: usize) -> Plane {
    let (w, h) = (p.w / f, p.h / f);
    let mut out = vec![0f32; w * h];
    let inv = 1.0 / (f * f) as f32;
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for dy in 0..f {
                let base = (y * f + dy) * p.w + x * f;
                for dx in 0..f {
                    s += p.d[base + dx];
                }
            }
            *o = s * inv;
        }
    });
    Plane { d: out, w, h }
}

fn bilinear(p: &Plane, x: f32, y: f32) -> f32 {
    let x = x.clamp(0.0, (p.w - 2) as f32);
    let y = y.clamp(0.0, (p.h - 2) as f32);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let (fx, fy) = (x - x0 as f32, y - y0 as f32);
    let i = y0 * p.w + x0;
    let a = p.d[i] * (1.0 - fx) + p.d[i + 1] * fx;
    let b = p.d[i + p.w] * (1.0 - fx) + p.d[i + p.w + 1] * fx;
    a * (1.0 - fy) + b * fy
}

#[derive(Clone, Copy, Debug, Default)]
struct Fit {
    ax: f32,
    ay: f32,
    g: f32,
    r: f32,
}

impl Fit {
    /// Displacement predicted at plane point `(x, y)`, relative to plane centre.
    fn at(&self, x: f32, y: f32, cx: f32, cy: f32) -> (f32, f32) {
        let (ux, uy) = (x - cx, y - cy);
        (
            self.ax + self.g * ux - self.r * uy,
            self.ay + self.r * ux + self.g * uy,
        )
    }
}

fn parabola(l: f32, c: f32, r: f32) -> f32 {
    if !l.is_finite() || !r.is_finite() {
        return 0.0;
    }
    let d = l - 2.0 * c + r;
    if d.abs() < 1e-12 {
        return 0.0;
    }
    let o = 0.5 * (l - r) / d;
    if o.abs() > 1.0 {
        0.0
    } else {
        o
    }
}

/// Why a tile produced no usable displacement. M6 needs these: silently
/// dropping low-contrast tiles censors exactly the defocused tiles that the
/// blur-bias hypothesis predicts, so the rejections are recorded, not hidden.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum TileStatus {
    Ok,
    /// Tile variance below the contrast floor — no displacement information.
    LowContrast,
    /// Best correlation below 0.5.
    LowPeak,
    /// Peak sat on the edge of the search window.
    Border,
    /// Search window fell outside the moving plane everywhere.
    Oob,
}

impl TileStatus {
    fn as_str(self) -> &'static str {
        match self {
            TileStatus::Ok => "ok",
            TileStatus::LowContrast => "lowcontrast",
            TileStatus::LowPeak => "lowpeak",
            TileStatus::Border => "border",
            TileStatus::Oob => "oob",
        }
    }
}

struct TileMeas {
    status: TileStatus,
    /// Mean square of the zero-mean reference tile, in DN^2.
    contrast: f32,
    dx: f32,
    dy: f32,
    peak: f32,
}

/// Zero-mean normalised cross-correlation of one reference tile against the
/// moving plane, searching a square window around `(px, py)`.
///
/// Returns the displacement that carries the reference tile onto the moving
/// plane, with parabolic sub-pixel refinement, plus the peak correlation, plus
/// why it failed when it did.
fn ncc_tile_full(
    rf: &Plane,
    mv: &Plane,
    tx: usize,
    ty: usize,
    ts: usize,
    px: f32,
    py: f32,
    radius: i32,
) -> TileMeas {
    let fail = |status, contrast| TileMeas {
        status,
        contrast,
        dx: f32::NAN,
        dy: f32::NAN,
        peak: f32::NAN,
    };
    let mut a = vec![0f32; ts * ts];
    let mut mean = 0f32;
    for y in 0..ts {
        let row = (ty + y) * rf.w + tx;
        for x in 0..ts {
            let v = rf.d[row + x];
            a[y * ts + x] = v;
            mean += v;
        }
    }
    mean /= (ts * ts) as f32;
    let mut sa = 0f32;
    for v in a.iter_mut() {
        *v -= mean;
        sa += *v * *v;
    }
    let contrast = sa / (ts * ts) as f32;
    // Contrast floor: a featureless tile has no displacement information and
    // will happily report a confident answer built out of noise.
    if contrast <= 4.0 {
        return fail(TileStatus::LowContrast, contrast);
    }

    let (bx, by) = (px.round() as i32, py.round() as i32);
    let n = (2 * radius + 1) as usize;
    let mut scores = vec![f32::NEG_INFINITY; n * n];
    let (mut best, mut bi, mut bj) = (f32::NEG_INFINITY, 0usize, 0usize);

    for j in -radius..=radius {
        for i in -radius..=radius {
            let ox = tx as i32 + bx + i;
            let oy = ty as i32 + by + j;
            if ox < 0 || oy < 0 || ox as usize + ts > mv.w || oy as usize + ts > mv.h {
                continue;
            }
            let (ox, oy) = (ox as usize, oy as usize);
            let mut mb = 0f32;
            for y in 0..ts {
                let row = (oy + y) * mv.w + ox;
                for x in 0..ts {
                    mb += mv.d[row + x];
                }
            }
            mb /= (ts * ts) as f32;
            let (mut num, mut sb) = (0f32, 0f32);
            for y in 0..ts {
                let row = (oy + y) * mv.w + ox;
                for x in 0..ts {
                    let bv = mv.d[row + x] - mb;
                    num += a[y * ts + x] * bv;
                    sb += bv * bv;
                }
            }
            if sb <= 1e-6 {
                continue;
            }
            let s = num / (sa * sb).sqrt();
            let (ii, jj) = ((i + radius) as usize, (j + radius) as usize);
            scores[jj * n + ii] = s;
            if s > best {
                best = s;
                bi = ii;
                bj = jj;
            }
        }
    }

    if !best.is_finite() {
        return fail(TileStatus::Oob, contrast);
    }
    if best < 0.5 {
        let mut m = fail(TileStatus::LowPeak, contrast);
        m.peak = best;
        return m;
    }
    // A peak on the search border means the true optimum is outside the window.
    if bi == 0 || bj == 0 || bi == n - 1 || bj == n - 1 {
        let mut m = fail(TileStatus::Border, contrast);
        m.peak = best;
        return m;
    }
    let sc = |i: usize, j: usize| scores[j * n + i];
    let ox = parabola(sc(bi - 1, bj), sc(bi, bj), sc(bi + 1, bj));
    let oy = parabola(sc(bi, bj - 1), sc(bi, bj), sc(bi, bj + 1));
    TileMeas {
        status: TileStatus::Ok,
        contrast,
        dx: (bx + bi as i32 - radius) as f32 + ox,
        dy: (by + bj as i32 - radius) as f32 + oy,
        peak: best,
    }
}

fn solve4(mut m: [[f64; 5]; 4]) -> Option<[f64; 4]> {
    for c in 0..4 {
        let mut p = c;
        for r in c + 1..4 {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c].abs() < 1e-12 {
            return None;
        }
        m.swap(c, p);
        let d = m[c][c];
        for v in m[c].iter_mut() {
            *v /= d;
        }
        for r in 0..4 {
            if r != c {
                let f = m[r][c];
                for k in c..5 {
                    m[r][k] -= f * m[c][k];
                }
            }
        }
    }
    Some([m[0][4], m[1][4], m[2][4], m[3][4]])
}

/// Least squares for an arbitrary basis, solved by Gauss-Jordan on the normal
/// equations. Returns the RMS residual only — the coefficients are not needed.
fn lsq_rms(rows: &[(Vec<f64>, f64)]) -> Option<f64> {
    let n = rows.first()?.0.len();
    if rows.len() < n {
        return None;
    }
    let mut m = vec![vec![0f64; n + 1]; n];
    for (basis, b) in rows {
        for i in 0..n {
            for j in 0..n {
                m[i][j] += basis[i] * basis[j];
            }
            m[i][n] += basis[i] * b;
        }
    }
    for c in 0..n {
        let mut p = c;
        for r in c + 1..n {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c].abs() < 1e-12 {
            return None;
        }
        m.swap(c, p);
        let d = m[c][c];
        for v in m[c].iter_mut() {
            *v /= d;
        }
        for r in 0..n {
            if r != c {
                let f = m[r][c];
                for k in c..=n {
                    m[r][k] -= f * m[c][k];
                }
            }
        }
    }
    let coef: Vec<f64> = (0..n).map(|i| m[i][n]).collect();
    let ss: f64 = rows
        .iter()
        .map(|(basis, b)| {
            let pred: f64 = basis.iter().zip(&coef).map(|(x, c)| x * c).sum();
            (b - pred).powi(2)
        })
        .sum();
    Some((ss / rows.len() as f64).sqrt())
}

/// How much of the similarity residual is model error rather than tile noise?
///
/// Fits progressively richer motion models to the same observations. If a
/// richer model does not reduce the residual, the residual is measurement
/// noise and a richer model would only fit that noise.
///
/// x and y get independent coefficient vectors — sharing one is a 3-parameter
/// model that is not affine at all, and it does not contain the similarity.
fn model_ladder(obs: &[Obs]) -> (f64, f64) {
    let build = |quad: bool, want_y: bool| -> Vec<(Vec<f64>, f64)> {
        obs.iter()
            .map(|o| {
                // Scaled to keep the normal equations well conditioned. A
                // linear reparametrisation cannot change the residual.
                let (ux, uy) = (o.ux as f64 / 1000.0, o.uy as f64 / 1000.0);
                let mut b = vec![1.0, ux, uy];
                if quad {
                    b.extend([ux * ux, ux * uy, uy * uy]);
                }
                (b, if want_y { o.dy as f64 } else { o.dx as f64 })
            })
            .collect()
    };
    let combined = |quad: bool| match (
        lsq_rms(&build(quad, false)),
        lsq_rms(&build(quad, true)),
    ) {
        // sqrt(mean(ex^2) + mean(ey^2)) == sqrt(mean(ex^2 + ey^2)), which is
        // the same Euclidean RMS that `residuals` reports for the similarity.
        (Some(x), Some(y)) => (x * x + y * y).sqrt(),
        _ => f64::NAN,
    };
    (combined(false), combined(true))
}

#[derive(Clone, Copy)]
struct Obs {
    ux: f32,
    uy: f32,
    dx: f32,
    dy: f32,
}

fn fit_similarity(obs: &[Obs]) -> Option<Fit> {
    // Rows: dx -> [1, 0, ux, -uy], dy -> [0, 1, uy, ux].
    let mut ata = [[0f64; 5]; 4];
    let add = |ata: &mut [[f64; 5]; 4], row: [f64; 4], b: f64| {
        for i in 0..4 {
            for j in 0..4 {
                ata[i][j] += row[i] * row[j];
            }
            ata[i][4] += row[i] * b;
        }
    };
    for o in obs {
        let (ux, uy) = (o.ux as f64, o.uy as f64);
        add(&mut ata, [1.0, 0.0, ux, -uy], o.dx as f64);
        add(&mut ata, [0.0, 1.0, uy, ux], o.dy as f64);
    }
    let s = solve4(ata)?;
    Some(Fit {
        ax: s[0] as f32,
        ay: s[1] as f32,
        g: s[2] as f32,
        r: s[3] as f32,
    })
}

fn residuals(obs: &[Obs], f: &Fit) -> Vec<f32> {
    obs.iter()
        .map(|o| {
            let ex = o.dx - (f.ax + f.g * o.ux - f.r * o.uy);
            let ey = o.dy - (f.ay + f.r * o.ux + f.g * o.uy);
            (ex * ex + ey * ey).sqrt()
        })
        .collect()
}

/// One tile's contribution to a stage fit, kept rather than aggregated away.
struct TileRec {
    id: usize,
    tx: usize,
    ty: usize,
    /// Tile centre relative to the reference plane centre.
    ux: f32,
    uy: f32,
    dx: f32,
    dy: f32,
    /// Residual after the final similarity fit for this pair.
    ex: f32,
    ey: f32,
    peak: f32,
    contrast: f32,
    status: TileStatus,
    /// Survived the MAD outlier pass and so contributed to the final fit.
    kept: bool,
}

struct Stage {
    fit: Fit,
    used: usize,
    total: usize,
    rms: f32,
    rms_affine: f64,
    rms_quad: f64,
    /// Ladder on every tile that correlated, before outlier rejection. The
    /// rejection uses similarity residuals, so judging the ladder only on
    /// survivors would be circular — it discards exactly the tiles a richer
    /// model might explain.
    raw_sim: f32,
    raw_affine: f64,
    raw_quad: f64,
    raw_n: usize,
    /// M6: one entry per anchor, including the ones that produced nothing.
    tiles: Vec<TileRec>,
}

fn fit_stage(
    rf: &Plane,
    mv: &Plane,
    tile: usize,
    gx: usize,
    gy: usize,
    radius: i32,
    seed: Option<Fit>,
) -> Option<Stage> {
    let spots = tile_grid(rf, tile, gx, gy, radius)?;
    fit_stage_at(rf, mv, tile, &spots, radius, seed)
}

/// The fixed anchor grid a stage uses, in reference-plane coordinates.
///
/// Split out of `fit_stage` so that M6 can build the *same* grid once in
/// frame-0 coordinates and then carry it into other reference frames.
fn tile_grid(rf: &Plane, tile: usize, gx: usize, gy: usize, radius: i32) -> Option<Vec<(usize, usize)>> {
    tile_grid_m(rf, tile, gx, gy, radius as usize + 4)
}

fn tile_grid_m(
    rf: &Plane,
    tile: usize,
    gx: usize,
    gy: usize,
    margin: usize,
) -> Option<Vec<(usize, usize)>> {
    if rf.w < tile + 2 * margin || rf.h < tile + 2 * margin {
        return None;
    }
    let span_x = rf.w - tile - 2 * margin;
    let span_y = rf.h - tile - 2 * margin;
    let mut spots = Vec::with_capacity(gx * gy);
    for j in 0..gy {
        for i in 0..gx {
            let tx = margin + span_x * i / (gx - 1).max(1);
            let ty = margin + span_y * j / (gy - 1).max(1);
            spots.push((tx, ty));
        }
    }
    Some(spots)
}

fn fit_stage_at(
    rf: &Plane,
    mv: &Plane,
    tile: usize,
    spots: &[(usize, usize)],
    radius: i32,
    seed: Option<Fit>,
) -> Option<Stage> {
    let (cx, cy) = (rf.w as f32 * 0.5, rf.h as f32 * 0.5);

    let meas: Vec<(usize, f32, f32, TileMeas)> = spots
        .par_iter()
        .enumerate()
        .map(|(id, &(tx, ty))| {
            let (mx, my) = (tx as f32 + tile as f32 * 0.5, ty as f32 + tile as f32 * 0.5);
            let (px, py) = seed.map(|s| s.at(mx, my, cx, cy)).unwrap_or((0.0, 0.0));
            let m = if tx + tile <= rf.w && ty + tile <= rf.h {
                ncc_tile_full(rf, mv, tx, ty, tile, px, py, radius)
            } else {
                TileMeas {
                    status: TileStatus::Oob,
                    contrast: f32::NAN,
                    dx: f32::NAN,
                    dy: f32::NAN,
                    peak: f32::NAN,
                }
            };
            (id, mx - cx, my - cy, m)
        })
        .collect();

    let mut tiles: Vec<TileRec> = meas
        .iter()
        .map(|(id, ux, uy, m)| TileRec {
            id: *id,
            tx: spots[*id].0,
            ty: spots[*id].1,
            ux: *ux,
            uy: *uy,
            dx: m.dx,
            dy: m.dy,
            ex: f32::NAN,
            ey: f32::NAN,
            peak: m.peak,
            contrast: m.contrast,
            status: m.status,
            kept: false,
        })
        .collect();

    let mut obs: Vec<Obs> = Vec::new();
    let mut obs_of: Vec<usize> = Vec::new();
    for (id, ux, uy, m) in &meas {
        if m.status == TileStatus::Ok {
            obs.push(Obs {
                ux: *ux,
                uy: *uy,
                dx: m.dx,
                dy: m.dy,
            });
            obs_of.push(*id);
        }
    }

    let total = spots.len();
    if obs.len() < 8 {
        return None;
    }

    // One robust pass: fit, drop anything beyond 3 scaled MADs, refit.
    let f0 = fit_similarity(&obs)?;
    let res = residuals(&obs, &f0);
    let raw_sim = (res.iter().map(|r| r * r).sum::<f32>() / res.len() as f32).sqrt();
    let (raw_affine, raw_quad) = model_ladder(&obs);
    let raw_n = obs.len();

    let mut sorted = res.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let med = sorted[sorted.len() / 2];
    let mut devs: Vec<f32> = res.iter().map(|r| (r - med).abs()).collect();
    devs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let mad = devs[devs.len() / 2].max(1e-3);
    let cut = med + 3.0 * 1.4826 * mad;

    let keep_mask: Vec<bool> = res.iter().map(|r| *r <= cut).collect();
    let kept: Vec<Obs> = obs
        .iter()
        .zip(&keep_mask)
        .filter(|(_, k)| **k)
        .map(|(o, _)| *o)
        .collect();
    if kept.len() < 8 {
        return None;
    }
    let fit = fit_similarity(&kept)?;
    let kres = residuals(&kept, &fit);
    let rms = (kres.iter().map(|r| r * r).sum::<f32>() / kres.len() as f32).sqrt();
    let (rms_affine, rms_quad) = model_ladder(&kept);

    // Residuals for EVERY correlated tile against the FINAL fit, so the M6
    // analysis is not restricted to the survivors of a similarity-based cut.
    for (i, o) in obs.iter().enumerate() {
        let t = &mut tiles[obs_of[i]];
        t.ex = o.dx - (fit.ax + fit.g * o.ux - fit.r * o.uy);
        t.ey = o.dy - (fit.ay + fit.r * o.ux + fit.g * o.uy);
        t.kept = keep_mask[i];
    }

    Some(Stage {
        fit,
        used: kept.len(),
        total,
        rms,
        rms_affine,
        rms_quad,
        raw_sim,
        raw_affine,
        raw_quad,
        raw_n,
        tiles,
    })
}

/// Coarse global fit on an 8x-decimated plane, then an independent fine fit at
/// plane resolution seeded from it. No chaining between frames.
fn align(rf: &Plane, mv: &Plane) -> Option<Stage> {
    const CF: usize = 8;
    let rc = downsample(rf, CF);
    let mc = downsample(mv, CF);
    let spots = tile_grid(rf, 128, 12, 8, 6)?;
    align_at(&rc, &mc, rf, mv, &spots)
}

/// The same two-phase fit, with the decimated planes supplied and the fine
/// anchors chosen by the caller.
///
/// The coarse stage exists only to bring the fine search into capture range;
/// all accuracy comes from the fine stage, which correlates `rf` against `mv`
/// **directly**. Nothing here composes one pair's fit into another's, so
/// AGENTS.md rule 6 is not touched.
fn align_at(
    rc: &Plane,
    mc: &Plane,
    rf: &Plane,
    mv: &Plane,
    spots: &[(usize, usize)],
) -> Option<Stage> {
    const CF: usize = 8;
    let coarse = fit_stage(rc, mc, 32, 8, 6, 10, None)?;
    let seed = Fit {
        ax: coarse.fit.ax * CF as f32,
        ay: coarse.fit.ay * CF as f32,
        g: coarse.fit.g,
        r: coarse.fit.r,
    };
    fit_stage_at(rf, mv, 128, spots, 6, Some(seed))
}

fn synthetic(rf: &Plane, truth: Fit) -> Plane {
    let (cx, cy) = (rf.w as f32 * 0.5, rf.h as f32 * 0.5);
    let mut out = vec![0f32; rf.w * rf.h];
    let w = rf.w;
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let (dx, dy) = truth.at(x as f32, y as f32, cx, cy);
            *o = bilinear(rf, x as f32 - dx, y as f32 - dy);
        }
    });
    Plane {
        d: out,
        w: rf.w,
        h: rf.h,
    }
}

/// Least squares through the origin: y = a*k, and y = a*k + b*k^2.
fn trend(k: &[f64], y: &[f64]) -> (f64, f64, f64, f64) {
    let (mut s2, mut sy) = (0.0, 0.0);
    for (ki, yi) in k.iter().zip(y) {
        s2 += ki * ki;
        sy += ki * yi;
    }
    let a1 = sy / s2;
    let rms1 =
        (k.iter().zip(y).map(|(ki, yi)| (yi - a1 * ki).powi(2)).sum::<f64>() / k.len() as f64).sqrt();

    let (mut m11, mut m12, mut m22, mut b1, mut b2) = (0.0, 0.0, 0.0, 0.0, 0.0);
    for (ki, yi) in k.iter().zip(y) {
        let (p1, p2) = (*ki, ki * ki);
        m11 += p1 * p1;
        m12 += p1 * p2;
        m22 += p2 * p2;
        b1 += p1 * yi;
        b2 += p2 * yi;
    }
    let det = m11 * m22 - m12 * m12;
    if det.abs() < 1e-30 {
        return (a1, 0.0, rms1, rms1);
    }
    let a2 = (b1 * m22 - b2 * m12) / det;
    let c2 = (m11 * b2 - m12 * b1) / det;
    let rms2 = (k
        .iter()
        .zip(y)
        .map(|(ki, yi)| (yi - a2 * ki - c2 * ki * ki).powi(2))
        .sum::<f64>()
        / k.len() as f64)
        .sqrt();
    (a2, c2, rms1, rms2)
}

/// Compose a run of adjacent similarity fits into one transform.
///
/// A displacement field `d(p) = a + s*(p - c)` is the map `u' = T*u + a` with
/// `T = 1 + s`, taking coordinates relative to the plane centre. Writing scale
/// and rotation as one complex number makes composition a multiplication:
/// applying step 1 then step 2 gives `T = T1*T2`, `a = T2*a1 + a2`.
fn compose(steps: &[Fit]) -> Fit {
    let (mut tr, mut ti) = (1.0f64, 0.0f64);
    let (mut ar, mut ai) = (0.0f64, 0.0f64);
    for f in steps {
        let (sr, si) = (1.0 + f.g as f64, f.r as f64);
        let (nr, ni) = (tr * sr - ti * si, tr * si + ti * sr);
        let (par, pai) = (sr * ar - si * ai + f.ax as f64, sr * ai + si * ar + f.ay as f64);
        tr = nr;
        ti = ni;
        ar = par;
        ai = pai;
    }
    Fit {
        ax: ar as f32,
        ay: ai as f32,
        g: (tr - 1.0) as f32,
        r: ti as f32,
    }
}

/// Weighted least squares for an arbitrary basis. Returns the coefficients.
fn wls(rows: &[(Vec<f64>, f64, f64)]) -> Option<Vec<f64>> {
    let n = rows.first()?.0.len();
    if rows.len() < n {
        return None;
    }
    let mut m = vec![vec![0f64; n + 1]; n];
    for (basis, b, w) in rows {
        for i in 0..n {
            for j in 0..n {
                m[i][j] += w * basis[i] * basis[j];
            }
            m[i][n] += w * basis[i] * b;
        }
    }
    for c in 0..n {
        let mut p = c;
        for r in c + 1..n {
            if m[r][c].abs() > m[p][c].abs() {
                p = r;
            }
        }
        if m[p][c].abs() < 1e-30 {
            return None;
        }
        m.swap(c, p);
        let d = m[c][c];
        for v in m[c].iter_mut() {
            *v /= d;
        }
        for r in 0..n {
            if r != c {
                let f = m[r][c];
                for k in c..=n {
                    m[r][k] -= f * m[c][k];
                }
            }
        }
    }
    Some((0..n).map(|i| m[i][n]).collect())
}

/// A smooth model of the direct-fit parameters against frame index.
///
/// **Used only to place tile anchors, never to measure anything.** On a
/// 105-frame stack the direct fit of frame 0 against frame 90 degrades badly
/// (fact 4: correlation tracks the migrating in-focus band), so some frames have
/// no usable direct fit at all and others have one built from nine tiles. A tile
/// anchor only needs to be right to a few pixels, so it is placed from a robust
/// smooth model instead. Every displacement, residual and fit reported by this
/// experiment is measured **directly** between the two frames of its own pair;
/// nothing is composed, so AGENTS.md rule 6 is untouched.
///
/// `g`, `rot`, `ax` and `ay` are all zero at k=0 by construction, so the bases
/// have no constant term.
fn smooth_anchor_model(fits: &[(usize, Fit, usize, f32)], n: usize) -> Vec<Fit> {
    let basis = |k: f64, deg: usize| -> Vec<f64> {
        (1..=deg).map(|p| (k / 100.0).powi(p as i32)).collect()
    };
    let deg = 3usize;
    let solve = |pick: &dyn Fn(&Fit) -> f64| -> Vec<f64> {
        let mut rows: Vec<(Vec<f64>, f64, f64)> = fits
            .iter()
            .map(|(k, f, used, rms)| {
                // Weight by how much evidence the fit rests on, damped by its
                // own residual. A nine-tile fit with a 5 px residual should not
                // outvote a seventy-tile fit with a 1 px one.
                let w = *used as f64 / (1.0 + (*rms as f64).powi(2));
                (basis(*k as f64, deg), pick(f), w)
            })
            .collect();
        let Some(c0) = wls(&rows) else {
            return vec![0.0; deg];
        };
        let res: Vec<f64> = rows
            .iter()
            .map(|(b, y, _)| (y - b.iter().zip(&c0).map(|(x, c)| x * c).sum::<f64>()).abs())
            .collect();
        let mut s = res.clone();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let med = s[s.len() / 2];
        let mut dev: Vec<f64> = res.iter().map(|r| (r - med).abs()).collect();
        dev.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let cut = med + 3.0 * 1.4826 * dev[dev.len() / 2].max(1e-12);
        for (i, r) in res.iter().enumerate() {
            if *r > cut {
                rows[i].2 = 0.0;
            }
        }
        wls(&rows).unwrap_or(c0)
    };
    let cg = solve(&|f: &Fit| f.g as f64);
    let cr = solve(&|f: &Fit| f.r as f64);
    let cx = solve(&|f: &Fit| f.ax as f64);
    let cy = solve(&|f: &Fit| f.ay as f64);
    let ev = |c: &[f64], k: usize| -> f32 {
        basis(k as f64, deg).iter().zip(c).map(|(x, cc)| x * cc).sum::<f64>() as f32
    };
    (0..n)
        .map(|k| Fit {
            ax: ev(&cx, k),
            ay: ev(&cy, k),
            g: ev(&cg, k),
            r: ev(&cr, k),
        })
        .collect()
}

// ---------------------------------------------------------------------------
// M6 — per-tile residuals, per-tile focus profile, and planted-cause controls
// ---------------------------------------------------------------------------

/// Inner box radius, mirroring `strehl-core::focus::INNER_RADIUS` (a 3x3 mean).
const FOCUS_INNER: usize = 1;
/// Outer box radius, mirroring `strehl-core::focus::OUTER_RADIUS` (a 7x7 mean).
const FOCUS_OUTER: usize = 3;

/// Ring-difference focus, aggregated over one tile.
///
/// Returns `(mean |box3x3 - box7x7| / sigma, RMS of box3x3 - box7x7)`. The first
/// mirrors `strehl-core`'s measure, which divides by the injected noise model's
/// green-luma sigma; the second is the same high-pass with no noise
/// normalisation at all. They are reported separately so that the winner index
/// can be checked for dependence on the normalisation.
///
/// `gain` is DN per electron and `rn_e` is read noise in electrons. Both are
/// arguments, never derived here — AGENTS.md rule 3.
fn tile_focus(p: &Plane, tx: usize, ty: usize, ts: usize, gain: f32, rn_e: f32) -> Option<(f32, f32)> {
    let m = FOCUS_OUTER;
    if tx < m || ty < m || tx + ts + m > p.w || ty + ts + m > p.h {
        return None;
    }
    let (x0, y0) = (tx - m, ty - m);
    let rw = ts + 2 * m;
    let rh = ts + 2 * m;
    let stride = rw + 1;
    let mut ii = vec![0f64; stride * (rh + 1)];
    for y in 0..rh {
        let mut row_sum = 0f64;
        for x in 0..rw {
            row_sum += p.d[(y0 + y) * p.w + x0 + x] as f64;
            ii[(y + 1) * stride + x + 1] = ii[y * stride + x + 1] + row_sum;
        }
    }
    let box_mean = |cx: usize, cy: usize, r: usize| -> f64 {
        let (xa, ya) = (cx - r, cy - r);
        let (xb, yb) = (cx + r + 1, cy + r + 1);
        let s = ii[yb * stride + xb] - ii[ya * stride + xb] - ii[yb * stride + xa] + ii[ya * stride + xa];
        s / ((2 * r + 1) * (2 * r + 1)) as f64
    };
    let read_dn = (rn_e * gain) as f64;
    let mut sum_ring = 0f64;
    let mut sum_hp2 = 0f64;
    for y in 0..ts {
        for x in 0..ts {
            let (cx, cy) = (x + m, y + m);
            let hp = box_mean(cx, cy, FOCUS_INNER) - box_mean(cx, cy, FOCUS_OUTER);
            let l = p.d[(y0 + cy) * p.w + x0 + cx].max(0.0) as f64;
            // Green luma sigma for L = (G1+G2)/2 with independent reads:
            // Var(L) = (Var(G1) + Var(G2))/4 = (g*L + read_dn^2)/2.
            let sigma = (0.5 * (gain as f64 * l + read_dn * read_dn)).sqrt().max(1e-3);
            sum_ring += hp.abs() / sigma;
            sum_hp2 += hp * hp;
        }
    }
    let n = (ts * ts) as f64;
    Some(((sum_ring / n) as f32, (sum_hp2 / n).sqrt() as f32))
}

/// xorshift64*, so the synthetic controls are bit-reproducible from a seed.
struct Rng(u64);

impl Rng {
    fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.0 = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
    fn unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / 9007199254740992.0)
    }
    /// Box-Muller, one value per call (the second is discarded on purpose —
    /// simplicity beats speed here).
    fn normal(&mut self) -> f32 {
        let u1 = self.unit().max(1e-12);
        let u2 = self.unit();
        ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
    }
}

fn gauss_blur(p: &Plane, sigma: f32) -> Plane {
    if sigma <= 1e-3 {
        return Plane {
            d: p.d.clone(),
            w: p.w,
            h: p.h,
        };
    }
    let r = (3.0 * sigma).ceil() as isize;
    let k: Vec<f32> = (-r..=r)
        .map(|i| (-0.5 * (i as f32 / sigma).powi(2)).exp())
        .collect();
    let ks: f32 = k.iter().sum();
    let k: Vec<f32> = k.iter().map(|v| v / ks).collect();

    let (w, h) = (p.w, p.h);
    let mut tmp = vec![0f32; w * h];
    tmp.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for (t, kv) in k.iter().enumerate() {
                let xx = (x as isize + t as isize - r).clamp(0, w as isize - 1) as usize;
                s += *kv * p.d[y * w + xx];
            }
            *o = s;
        }
    });
    let mut out = vec![0f32; w * h];
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for (t, kv) in k.iter().enumerate() {
                let yy = (y as isize + t as isize - r).clamp(0, h as isize - 1) as usize;
                s += *kv * tmp[yy * w + x];
            }
            *o = s;
        }
    });
    Plane { d: out, w, h }
}

/// Blur levels the spatially-varying blur interpolates between.
const BLUR_LEVELS: [f32; 4] = [0.0, 1.0, 2.2, 4.0];

/// A smooth depth field in `[0, n-1]`: a diagonal ramp plus three Gaussian
/// blobs, so that depth is deliberately **not** an affine function of position.
/// If it were, a depth-dependent magnification would be exactly absorbable by
/// the affine model, and the control would test nothing.
fn depth_field(w: usize, h: usize, n: usize) -> Vec<f32> {
    let blobs = [
        (0.25f32, 0.30f32, 0.22f32, 0.85f32),
        (0.72, 0.62, 0.18, -0.75),
        (0.45, 0.85, 0.26, 0.55),
    ];
    let mut d = vec![0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let (u, v) = (x as f32 / w as f32, y as f32 / h as f32);
            let mut t = 0.30 * u + 0.18 * v;
            for (bx, by, br, ba) in blobs {
                let r2 = ((u - bx).powi(2) + (v - by).powi(2)) / (br * br);
                t += ba * (-r2).exp();
            }
            d[y * w + x] = t;
        }
    }
    let (mut lo, mut hi) = (f32::INFINITY, f32::NEG_INFINITY);
    for v in &d {
        lo = lo.min(*v);
        hi = hi.max(*v);
    }
    let span = (hi - lo).max(1e-6);
    for v in d.iter_mut() {
        *v = (*v - lo) / span * (n - 1) as f32;
    }
    d
}

struct SynthSpec {
    /// Scale change per frame index, applied as `g_k = gstep * k`.
    gstep: f32,
    /// Fractional spread of the scale factor across the depth range. 0 means a
    /// single global similarity; 0.2 means the near and far depths scale 20%
    /// differently from each other.
    kappa: f32,
    /// Defocus sigma in plane px per frame of separation from best focus.
    blur_per_frame: f32,
    gain: f32,
    rn_e: f32,
    seed: u64,
    /// Move every frame by a whole number of pixels instead of warping it.
    ///
    /// Bilinear resampling attenuates high spatial frequencies by an amount that
    /// depends on the sub-pixel phase, so a scaled synthetic frame has a
    /// per-tile, per-frame *sharpness* modulation that nobody planted. That is
    /// enough to give the tiles a spurious focus peak and to bias the
    /// correlation the same way defocus does. An integer shift touches no
    /// interpolator, so this is the null that is actually free of the effect
    /// being looked for.
    integer_shift: bool,
    /// Plant a **field-dependent asymmetric** defocus PSF: as a tile defocuses,
    /// its PSF centroid walks radially outward by `asym_gain * sigma * r/r_max`
    /// plane px. This is the mechanism SYNTHESIS §3.4.2 hypothesises would make
    /// a lens plugin genuine computation, so S6 needs it as an end-to-end
    /// positive control rather than only a planted-statistic one.
    ///
    /// The walk is deliberately **unsigned in defocus** (always outward, growing
    /// with the amount of blur) rather than signed. A signed-linear walk
    /// `c*(k - w)*r` displaces tile `i` in pair `(j, j+D)` by
    /// `c*((j+D-w) - (j-w))*r = c*D*r`, which is a pure scale change: constant
    /// per pair, linear in radius, and therefore absorbed exactly by the
    /// similarity fit. Such a PSF leaves **no residual at all** and is
    /// unobservable here by construction. The unsigned walk gives
    /// `c*(|j+D-w| - |j-w|)*r`, which depends on the tile's own depth `w` and
    /// so cannot be absorbed. That difference is why S6 regresses on
    /// `|mov-w| - |ref-w|` and not on `mov - ref`.
    asym_gain: f32,
}

/// Build a synthetic focus bracket from one real frame with a known cause
/// planted in it.
fn synth_stack(base: &Plane, n: usize, depth: &[f32], s: &SynthSpec) -> Vec<Plane> {
    let (w, h) = (base.w, base.h);
    let (cx, cy) = (w as f32 * 0.5, h as f32 * 0.5);
    (0..n)
        .map(|k| {
            let gk = s.gstep * k as f32;
            let mut warped = vec![0f32; w * h];
            if s.integer_shift {
                // Whole-pixel translation: a copy, not a resample.
                let sx = (gk * cx).round() as i64;
                let sy = (gk * cy).round() as i64;
                warped.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                    let src_y = (y as i64 + sy).clamp(0, h as i64 - 1) as usize;
                    for (x, o) in row.iter_mut().enumerate() {
                        let src_x = (x as i64 + sx).clamp(0, w as i64 - 1) as usize;
                        *o = base.d[src_y * w + src_x];
                    }
                });
            } else {
                warped.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                    for (x, o) in row.iter_mut().enumerate() {
                        let dz = depth[y * w + x] / (n - 1).max(1) as f32 - 0.5;
                        let g_eff = gk * (1.0 + 2.0 * s.kappa * dz);
                        let (dx, dy) = (g_eff * (x as f32 - cx), g_eff * (y as f32 - cy));
                        *o = bilinear(base, x as f32 - dx, y as f32 - dy);
                    }
                });
            }
            let warped = Plane { d: warped, w, h };

            let mut out = if s.blur_per_frame <= 0.0 {
                warped
            } else {
                let levels: Vec<Plane> = BLUR_LEVELS.iter().map(|s| gauss_blur(&warped, *s)).collect();
                let mut mixed = vec![0f32; w * h];
                let rmax = (cx * cx + cy * cy).sqrt();
                let asym = s.asym_gain;
                mixed.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
                    for (x, o) in row.iter_mut().enumerate() {
                        let i = y * w + x;
                        let sig = (s.blur_per_frame * (k as f32 - depth[i]).abs())
                            .min(BLUR_LEVELS[BLUR_LEVELS.len() - 1]);
                        let mut lo = 0;
                        while lo + 2 < BLUR_LEVELS.len() && BLUR_LEVELS[lo + 1] < sig {
                            lo += 1;
                        }
                        let (a, b) = (BLUR_LEVELS[lo], BLUR_LEVELS[lo + 1]);
                        let t = ((sig - a) / (b - a)).clamp(0.0, 1.0);
                        if asym > 0.0 {
                            let (rx, ry) = (x as f32 - cx, y as f32 - cy);
                            let rn = (rx * rx + ry * ry).sqrt().max(1.0);
                            let amt = asym * sig * (rn / rmax);
                            let (px, py) = (x as f32 + amt * rx / rn, y as f32 + amt * ry / rn);
                            *o = bilinear(&levels[lo], px, py) * (1.0 - t)
                                + bilinear(&levels[lo + 1], px, py) * t;
                        } else {
                            *o = levels[lo].d[i] * (1.0 - t) + levels[lo + 1].d[i] * t;
                        }
                    }
                });
                Plane { d: mixed, w, h }
            };

            // Fresh sensor noise on every frame. Without it the blurred cases
            // would also be quieter than the sharp ones, and the estimator
            // would see a noise difference where the experiment intends a
            // resolution difference.
            let mut rng = Rng(s.seed ^ (0x9E37_79B9_7F4A_7C15u64.wrapping_mul(k as u64 + 1)));
            let read_dn = s.rn_e * s.gain;
            for v in out.d.iter_mut() {
                let sigma = (0.5 * (s.gain * v.max(0.0) + read_dn * read_dn)).sqrt();
                *v += sigma * rng.normal();
            }
            out
        })
        .collect()
}

struct M6Writers {
    fits: std::io::BufWriter<std::fs::File>,
    tiles: std::io::BufWriter<std::fs::File>,
    focus: std::io::BufWriter<std::fs::File>,
    truth: std::io::BufWriter<std::fs::File>,
}

impl M6Writers {
    fn create(prefix: &str) -> std::io::Result<Self> {
        let mk = |suffix: &str, header: &str| -> std::io::Result<std::io::BufWriter<std::fs::File>> {
            let mut f = std::io::BufWriter::new(std::fs::File::create(format!("{prefix}-{suffix}.csv"))?);
            writeln!(f, "{header}")?;
            Ok(f)
        };
        Ok(Self {
            fits: mk(
                "fits",
                "case,grid,ref,mov,delta,g,rot,ax,ay,rms,used,raw_n,total,plane_w,plane_h",
            )?,
            tiles: mk(
                "tiles",
                "case,ref,mov,delta,tile_id,tx,ty,ux,uy,dx,dy,ex,ey,peak,contrast,status,kept",
            )?,
            focus: mk("focus", "case,tile_id,frame,tx,ty,ring,hp")?,
            truth: mk("truth", "case,tile_id,depth_truth")?,
        })
    }

    fn write_stage(&mut self, case: &str, grid: &str, rf: usize, mv: usize, st: &Stage, pw: usize, ph: usize) {
        let _ = writeln!(
            self.fits,
            "{case},{grid},{rf},{mv},{},{:.9},{:.9},{:.6},{:.6},{:.6},{},{},{},{pw},{ph}",
            mv as i64 - rf as i64,
            st.fit.g,
            st.fit.r,
            st.fit.ax,
            st.fit.ay,
            st.rms,
            st.used,
            st.raw_n,
            st.total
        );
        if grid != "m6" {
            return;
        }
        for t in &st.tiles {
            let _ = writeln!(
                self.tiles,
                "{case},{rf},{mv},{},{},{},{},{:.2},{:.2},{},{},{},{},{},{},{},{}",
                mv as i64 - rf as i64,
                t.id,
                t.tx,
                t.ty,
                t.ux,
                t.uy,
                fnum(t.dx),
                fnum(t.dy),
                fnum(t.ex),
                fnum(t.ey),
                fnum(t.peak),
                fnum(t.contrast),
                t.status.as_str(),
                if t.kept { 1 } else { 0 }
            );
        }
    }
}

fn fnum(v: f32) -> String {
    if v.is_finite() {
        format!("{v:.6}")
    } else {
        "".to_string()
    }
}

/// Everything M6 needs from one stack of planes: direct fits, warped anchors,
/// the per-tile focus profile, and the sliding-baseline sweep.
#[allow(clippy::too_many_arguments)]
fn run_m6_case(
    case: &str,
    planes: &[Plane],
    deltas: &[usize],
    gain: f32,
    rn_e: f32,
    truth_depth: Option<&[f32]>,
    w: &mut M6Writers,
) {
    const CF: usize = 8;
    const TILE: usize = 128;
    // The canonical grid is inset far enough that warping it into any frame of
    // the stack stays inside the plane: 10 px of NCC margin plus 46 px of slack,
    // against a worst-case measured drift of 39 px at the plane corner.
    const CANON_MARGIN: usize = 56;

    let n = planes.len();
    let (pw, ph) = (planes[0].w, planes[0].h);

    eprintln!("[{case}] decimating {n} planes 8x");
    let coarse: Vec<Plane> = planes.par_iter().map(|p| downsample(p, CF)).collect();

    let spots0 = match tile_grid_m(&planes[0], TILE, 12, 8, CANON_MARGIN) {
        Some(s) => s,
        None => {
            eprintln!("[{case}] plane too small for the canonical grid");
            return;
        }
    };
    let centres: Vec<(f32, f32)> = spots0
        .iter()
        .map(|&(tx, ty)| (tx as f32 + TILE as f32 * 0.5, ty as f32 + TILE as f32 * 0.5))
        .collect();

    if let Some(d) = truth_depth {
        for (id, &(tx, ty)) in spots0.iter().enumerate() {
            let mut s = 0f64;
            for y in ty..ty + TILE {
                for x in tx..tx + TILE {
                    s += d[y * pw + x] as f64;
                }
            }
            let _ = writeln!(w.truth, "{case},{id},{:.4}", s / (TILE * TILE) as f64);
        }
    }

    // 1. Direct fits, frame 0 against every other frame. Two grids: `m3` is the
    //    exact grid M3 published from, `m6` is the inset canonical grid used for
    //    everything else here. Publishing both makes the inset visible rather
    //    than an unstated difference.
    eprintln!("[{case}] direct fits, frame 0 -> k, both grids");
    let t0 = Instant::now();
    let m3_grid = tile_grid(&planes[0], TILE, 12, 8, 6);
    let direct: Vec<(Option<Stage>, Option<Stage>)> = (1..n)
        .into_par_iter()
        .map(|k| {
            let a = m3_grid
                .as_ref()
                .and_then(|g| align_at(&coarse[0], &coarse[k], &planes[0], &planes[k], g));
            let b = align_at(&coarse[0], &coarse[k], &planes[0], &planes[k], &spots0);
            (a, b)
        })
        .collect();
    eprintln!("[{case}] direct fits took {:.2} s", t0.elapsed().as_secs_f64());

    let mut fit_of: Vec<Option<Fit>> = vec![Some(Fit::default()); n];
    let mut direct_ok: Vec<(usize, Fit, usize, f32)> = Vec::new();
    let mut n_failed = 0usize;
    for (i, (a, b)) in direct.iter().enumerate() {
        let k = i + 1;
        if let Some(st) = a {
            w.write_stage(case, "m3", 0, k, st, pw, ph);
        }
        match b {
            Some(st) => {
                w.write_stage(case, "m6", 0, k, st, pw, ph);
                fit_of[k] = Some(st.fit);
                direct_ok.push((k, st.fit, st.used, st.rms));
            }
            None => {
                n_failed += 1;
                fit_of[k] = None;
            }
        }
    }

    // 2. Anchors: the canonical grid carried into every frame, so tile `i`
    //    covers the same scene content in every frame. Only the anchor position
    //    uses a fit; every displacement is still measured directly between the
    //    two frames of the pair.
    //
    //    The anchor transform is the *smooth model* of the direct fits, not the
    //    raw per-frame fit. On the 105-frame stack the direct fit of frame 0
    //    against a late frame degrades to a handful of tiles or fails outright,
    //    and a missing anchor would silently censor whole reference frames from
    //    the sweep — exactly the frames that carry the most depth information.
    //    Smoothing costs a few pixels of anchor accuracy and buys back the
    //    frames. The raw fits are still written to the fits CSV under grid=m6,
    //    and the smooth model under grid=anchor, so the difference is auditable.
    eprintln!(
        "[{case}] direct fits: {} ok, {n_failed} failed; smoothing anchor model",
        direct_ok.len()
    );
    let smooth = smooth_anchor_model(&direct_ok, n);
    for (k, f) in smooth.iter().enumerate() {
        let dev = fit_of[k]
            .map(|r| {
                let (rx, ry) = r.at(pw as f32, ph as f32, pw as f32 * 0.5, ph as f32 * 0.5);
                let (sx, sy) = f.at(pw as f32, ph as f32, pw as f32 * 0.5, ph as f32 * 0.5);
                ((rx - sx).powi(2) + (ry - sy).powi(2)).sqrt()
            })
            .unwrap_or(f32::NAN);
        let _ = writeln!(
            w.fits,
            "{case},anchor,0,{k},{k},{:.9},{:.9},{:.6},{:.6},{:.6},0,0,0,{pw},{ph}",
            f.g, f.r, f.ax, f.ay, dev
        );
    }
    let fit_of: Vec<Option<Fit>> = smooth.iter().map(|f| Some(*f)).collect();

    let (ccx, ccy) = (pw as f32 * 0.5, ph as f32 * 0.5);
    let anchors: Vec<Option<Vec<(usize, usize)>>> = fit_of
        .iter()
        .map(|f| {
            let f = (*f)?;
            let mut v = Vec::with_capacity(centres.len());
            for &(mx, my) in &centres {
                let (dx, dy) = f.at(mx, my, ccx, ccy);
                let tx = (mx + dx - TILE as f32 * 0.5).round();
                let ty = (my + dy - TILE as f32 * 0.5).round();
                if tx < FOCUS_OUTER as f32
                    || ty < FOCUS_OUTER as f32
                    || tx as usize + TILE + FOCUS_OUTER > pw
                    || ty as usize + TILE + FOCUS_OUTER > ph
                {
                    return None;
                }
                v.push((tx as usize, ty as usize));
            }
            Some(v)
        })
        .collect();

    // 3. Per-tile focus profile over the whole stack, on the registered anchors.
    eprintln!("[{case}] focus profile, {} tiles x {n} frames", spots0.len());
    let t1 = Instant::now();
    let profile: Vec<Vec<(f32, f32)>> = (0..n)
        .into_par_iter()
        .map(|k| match &anchors[k] {
            None => vec![(f32::NAN, f32::NAN); spots0.len()],
            Some(a) => a
                .iter()
                .map(|&(tx, ty)| {
                    tile_focus(&planes[k], tx, ty, TILE, gain, rn_e).unwrap_or((f32::NAN, f32::NAN))
                })
                .collect(),
        })
        .collect();
    eprintln!("[{case}] focus profile took {:.2} s", t1.elapsed().as_secs_f64());
    for (k, row) in profile.iter().enumerate() {
        let a = anchors[k].clone().unwrap_or_else(|| vec![(0, 0); spots0.len()]);
        for (id, (ring, hp)) in row.iter().enumerate() {
            let _ = writeln!(
                w.focus,
                "{case},{id},{k},{},{},{},{}",
                a[id].0,
                a[id].1,
                fnum(*ring),
                fnum(*hp)
            );
        }
    }

    // 4. The sliding-baseline sweep. For each baseline `delta`, align (j, j+delta)
    //    for every j. This is the axis on which the two candidate causes differ:
    //    at fixed delta the geometry is nearly the same for every j, but the
    //    defocus configuration of a tile is not.
    for &delta in deltas {
        if delta >= n {
            continue;
        }
        let t2 = Instant::now();
        let pairs: Vec<usize> = (0..n - delta).collect();
        let out: Vec<(usize, Option<Stage>)> = pairs
            .par_iter()
            .map(|&j| {
                let st = anchors[j]
                    .as_ref()
                    .and_then(|a| align_at(&coarse[j], &coarse[j + delta], &planes[j], &planes[j + delta], a));
                (j, st)
            })
            .collect();
        let ok = out.iter().filter(|(_, s)| s.is_some()).count();
        eprintln!(
            "[{case}] delta={delta}: {ok}/{} pairs in {:.2} s",
            out.len(),
            t2.elapsed().as_secs_f64()
        );
        for (j, st) in out {
            if let Some(st) = st {
                w.write_stage(case, "m6", j, j + delta, &st, pw, ph);
            }
        }
    }
}

fn parse_deltas(s: &str) -> Vec<usize> {
    s.split(',')
        .filter_map(|t| t.trim().parse::<usize>().ok())
        .filter(|d| *d > 0)
        .collect()
}

fn arg_val(args: &[String], key: &str) -> Option<String> {
    args.iter().position(|a| a == key).and_then(|i| args.get(i + 1)).cloned()
}

fn load_planes(dir: &str, limit: usize) -> Vec<Plane> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .expect("read_dir")
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    paths.truncate(limit);
    assert!(!paths.is_empty(), "no ARW files in {dir}");
    let t0 = Instant::now();
    let planes: Vec<Plane> = paths
        .par_iter()
        .map(|p| green_plane(p).unwrap_or_else(|e| panic!("{}: {e}", p.display())))
        .collect();
    eprintln!(
        "decoded {} frames to {}x{} green planes in {:.2} s",
        planes.len(),
        planes[0].w,
        planes[0].h,
        t0.elapsed().as_secs_f64()
    );
    planes
}

fn run_m6(args: &[String]) {
    let dir = args[2].clone();
    let prefix = args[3].clone();
    let limit: usize = arg_val(args, "--limit").and_then(|v| v.parse().ok()).unwrap_or(999);
    let iso: f32 = arg_val(args, "--iso").and_then(|v| v.parse().ok()).unwrap_or(160.0);
    let deltas = parse_deltas(&arg_val(args, "--deltas").unwrap_or_else(|| "1,2,4,8".into()));
    let case = arg_val(args, "--case").unwrap_or_else(|| {
        Path::new(&dir)
            .file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_else(|| "stack".into())
    });
    // Camera profile constants, DERIVED (SYNTHESIS §4.1): g = ISO/436.8 DN/e-,
    // read noise 4.20 e- below the ISO 400 second base, 1.47 e- at and above it.
    let gain = iso / 436.8;
    let rn_e = if iso < 400.0 { 4.20 } else { 1.47 };
    eprintln!("m6: dir={dir} case={case} iso={iso} gain={gain:.4} rn={rn_e} deltas={deltas:?}");

    let planes = load_planes(&dir, limit);
    let mut w = M6Writers::create(&prefix).expect("create csv");
    run_m6_case(&case, &planes, &deltas, gain, rn_e, None, &mut w);
    eprintln!("m6: wrote {prefix}-fits.csv, {prefix}-tiles.csv, {prefix}-focus.csv");
}

fn run_m6_control(args: &[String]) {
    let dir = args[2].clone();
    let prefix = args[3].clone();
    let iso: f32 = arg_val(args, "--iso").and_then(|v| v.parse().ok()).unwrap_or(160.0);
    let n: usize = arg_val(args, "--n").and_then(|v| v.parse().ok()).unwrap_or(12);
    let deltas = parse_deltas(&arg_val(args, "--deltas").unwrap_or_else(|| "1,2,4".into()));
    let gain = iso / 436.8;
    let rn_e = if iso < 400.0 { 4.20 } else { 1.47 };

    // Drift and defocus scaled to the real 22-frame stack: -1.835% of scale
    // over 21 frames is -8.74e-4 per frame (M3 §4).
    let gstep = -8.74e-4f32;
    let blur = 0.35f32;
    let kappa = 0.20f32;

    let base = load_planes(&dir, 1).into_iter().next().expect("one frame");
    let depth = depth_field(base.w, base.h, n);
    eprintln!(
        "m6-control: n={n} gstep={gstep:.3e} kappa={kappa} blur={blur} px/frame deltas={deltas:?}"
    );

    let mut w = M6Writers::create(&prefix).expect("create csv");
    let cases: [(&str, f32, f32, bool, f32); 6] = [
        // N0: whole-pixel translation only. No interpolator runs, so there is no
        // resampling-phase sharpness modulation and no depth signal of any kind.
        // This is the cleanest null available on real texture.
        ("N0-integer", 0.0, 0.0, true, 0.0),
        // N1: one global similarity, no defocus at all. Real texture, real
        // noise, but bilinear resampling — which turns out to matter.
        ("N1-null", 0.0, 0.0, false, 0.0),
        // P0: depth-dependent magnification, no defocus. Cause (a) alone.
        ("P0-depth-only", kappa, 0.0, false, 0.0),
        // P2: one global similarity plus depth-dependent defocus. Cause (b)
        // alone, with a strictly SYMMETRIC Gaussian PSF: it destroys high
        // frequencies but does not move the peak. S1 must fire here and S6 must
        // stay quiet — that pairing is what licenses reading S6 on real data.
        ("P2-blur-only", 0.0, blur, false, 0.0),
        // P1: both.
        ("P1-both", kappa, blur, false, 0.0),
        // P3: symmetric defocus PLUS a field-dependent asymmetric PSF whose
        // centroid walks radially outward with the amount of blur. This is the
        // end-to-end positive control for S6 and the direct emulation of the
        // mechanism §3.4.2 says would justify a real lens plugin.
        ("P3-asym-psf", 0.0, blur, false, 0.35),
    ];
    for (name, k, b, int_shift, asym) in cases {
        eprintln!(
            "\n=== control case {name}: kappa={k} blur={b} integer_shift={int_shift} asym={asym} ==="
        );
        let spec = SynthSpec {
            gstep,
            kappa: k,
            blur_per_frame: b,
            gain,
            rn_e,
            seed: 0x5EED_1234_ABCD_0001,
            integer_shift: int_shift,
            asym_gain: asym,
        };
        let planes = synth_stack(&base, n, &depth, &spec);
        run_m6_case(name, &planes, &deltas, gain, rn_e, Some(&depth), &mut w);
    }
    eprintln!("m6-control: wrote {prefix}-*.csv");
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage:");
        eprintln!("  drift-bench <dir> [limit]");
        eprintln!("  drift-bench --synthetic <dir>");
        eprintln!("  drift-bench --m6 <dir> <out-prefix> [--limit N] [--iso F] [--deltas 1,2,4,8] [--case NAME]");
        eprintln!("  drift-bench --m6-control <dir> <out-prefix> [--iso F] [--n N] [--deltas 1,2,4]");
        std::process::exit(2);
    }
    if args[1] == "--m6" {
        assert!(args.len() >= 4, "--m6 needs <dir> <out-prefix>");
        run_m6(&args);
        return;
    }
    if args[1] == "--m6-control" {
        assert!(args.len() >= 4, "--m6-control needs <dir> <out-prefix>");
        run_m6_control(&args);
        return;
    }
    let syn = args[1] == "--synthetic";
    let dir = if syn { &args[2] } else { &args[1] };
    let limit: usize = if syn {
        1
    } else {
        args.get(2).and_then(|s| s.parse().ok()).unwrap_or(999)
    };

    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .expect("read_dir")
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    paths.truncate(limit);
    if paths.is_empty() {
        eprintln!("no ARW files in {dir}");
        std::process::exit(1);
    }

    let t0 = Instant::now();
    let planes: Vec<Plane> = paths
        .par_iter()
        .map(|p| green_plane(p).unwrap_or_else(|e| panic!("{}: {e}", p.display())))
        .collect();
    let decode_ms = t0.elapsed().as_secs_f64() * 1e3;
    eprintln!(
        "decoded {} frames to {}x{} green planes in {:.0} ms ({:.1} ms/frame)",
        planes.len(),
        planes[0].w,
        planes[0].h,
        decode_ms,
        decode_ms / planes.len() as f64
    );

    if syn {
        // compose() is load-bearing for the chain-vs-direct comparison, so
        // check it against a case with a closed form: N identical pure-scale
        // steps must compose to (1+g)^N - 1.
        let step = Fit { ax: 0.0, ay: 0.0, g: -0.001, r: 0.0 };
        let n = 21;
        let got = compose(&vec![step; n]).g as f64;
        let want = (1.0f64 - 0.001).powi(n as i32) - 1.0;
        eprintln!(
            "compose() self-check: {got:.9} vs closed form {want:.9} (err {:.2e})",
            (got - want).abs()
        );

        eprintln!("\n=== synthetic control: known warp, must be recovered ===");
        let cases = [
            ("pure translation", Fit { ax: 3.7, ay: -2.4, g: 0.0, r: 0.0 }),
            ("scale only -1.0%", Fit { ax: 0.0, ay: 0.0, g: -0.0100, r: 0.0 }),
            ("scale+trans+rot", Fit { ax: -5.25, ay: 1.75, g: -0.00512, r: 0.00031 }),
            ("tiny scale -0.05%", Fit { ax: 0.0, ay: 0.0, g: -0.0005, r: 0.0 }),
        ];
        let mut worst_g = 0f64;
        for (name, truth) in cases {
            let m = synthetic(&planes[0], truth);
            match align(&planes[0], &m) {
                Some(s) => {
                    let f = s.fit;
                    let eg = (f.g - truth.g) as f64;
                    worst_g = worst_g.max(eg.abs());
                    eprintln!(
                        "{name:>18}: ax {:+8.3} (err {:+.3})  ay {:+8.3} (err {:+.3})  \
                         g {:+.6} (err {:+.6})  r {:+.6} (err {:+.6})  \
                         sim {:.3} affine {:.3} quad {:.3} px  {}/{} tiles (all: {:.3}/{:.3}/{:.3})",
                        f.ax, f.ax - truth.ax, f.ay, f.ay - truth.ay,
                        f.g, eg, f.r, f.r - truth.r,
                        s.rms, s.rms_affine, s.rms_quad, s.used, s.total,
                        s.raw_sim, s.raw_affine, s.raw_quad
                    );
                }
                None => eprintln!("{name:>18}: FAILED"),
            }
        }
        // The quadratic term the review predicted is ~0.4 px at the frame edge.
        // Express the estimator's scale error in the same units so the two are
        // directly comparable.
        let radius = (planes[0].w.pow(2) as f64 + planes[0].h.pow(2) as f64).sqrt() * 0.5;
        eprintln!(
            "\nworst scale error {:.2e} = {:.3} px at the plane corner (radius {:.0} px)",
            worst_g,
            worst_g * radius,
            radius
        );
        eprintln!("the quadratic term to be detected is ~0.2 px at plane resolution");
        return;
    }

    eprintln!("\n=== drift vs frame index (each frame aligned to frame 0, independently) ===");
    let t1 = Instant::now();
    let fits: Vec<Option<Stage>> = (1..planes.len())
        .into_par_iter()
        .map(|k| align(&planes[0], &planes[k]))
        .collect();
    let align_ms = t1.elapsed().as_secs_f64() * 1e3;

    println!(
        "k  scale_g      rot_r        tx        ty   | kept: sim affine quad | all: sim affine quad  n"
    );
    let (mut ks, mut gs, mut txs, mut tys) = (vec![], vec![], vec![], vec![]);
    for (i, f) in fits.iter().enumerate() {
        let k = (i + 1) as f64;
        match f {
            Some(s) => {
                println!(
                    "{:<2} {:+.6}   {:+.6}   {:+7.3} {:+7.3} | {:5.3} {:5.3} {:5.3} | \
                     {:5.3} {:5.3} {:5.3}  {}/{}/{}",
                    k,
                    s.fit.g,
                    s.fit.r,
                    s.fit.ax,
                    s.fit.ay,
                    s.rms,
                    s.rms_affine,
                    s.rms_quad,
                    s.raw_sim,
                    s.raw_affine,
                    s.raw_quad,
                    s.used,
                    s.raw_n,
                    s.total
                );
                ks.push(k);
                gs.push(s.fit.g as f64);
                txs.push(s.fit.ax as f64);
                tys.push(s.fit.ay as f64);
            }
            None => println!("{k:<2} FAILED"),
        }
    }
    eprintln!("sim/affine/quad = RMS residual of a 4-, 6- and 12-parameter motion model on the");
    eprintln!("same tiles. `all` includes the outliers that similarity-based rejection removes,");
    eprintln!("so it is the honest test of whether richer geometry explains anything.");

    let radius = ((planes[0].w * planes[0].w + planes[0].h * planes[0].h) as f64).sqrt() * 0.5;
    eprintln!("\n=== linear vs quadratic in frame index ===");
    for (name, y, scale) in [
        ("scale g", &gs, radius),
        ("tx", &txs, 1.0),
        ("ty", &tys, 1.0),
    ] {
        let (a, b, rms1, rms2) = trend(&ks, y);
        let kmax = ks.last().copied().unwrap_or(1.0);
        eprintln!(
            "{name:>8}: linear a={a:+.6e} rms={rms1:.4e} | +quadratic b={b:+.6e} rms={rms2:.4e} \
             | quad term at k={kmax:.0} = {:.3} px",
            (b * kmax * kmax * scale).abs()
        );
    }
    let lin_px = {
        let (a, _, rms1, _) = trend(&ks, &gs);
        let _ = a;
        rms1 * radius
    };
    eprintln!(
        "a straight line in frame index leaves {lin_px:.2} px RMS of scale error at the plane corner"
    );

    // The scale centre is where the magnification change has no effect. A
    // constant offset o from the plane centre shows up as translation -g*o, so
    // regress the fitted translation against the fitted scale.
    let (mut nx, mut ny, mut den) = (0.0, 0.0, 0.0);
    for i in 0..ks.len() {
        nx += txs[i] * gs[i];
        ny += tys[i] * gs[i];
        den += gs[i] * gs[i];
    }
    let (ox, oy) = (-nx / den, -ny / den);
    eprintln!(
        "\nscale centre: {:+.0}, {:+.0} px from the plane centre \
         ({:+.0}, {:+.0} px at sensor resolution)",
        ox,
        oy,
        ox * 2.0,
        oy * 2.0
    );

    eprintln!(
        "\nalign: {:.0} ms for {} pairs = {:.1} ms/frame (all pairs independent, {} threads)",
        align_ms,
        fits.len(),
        align_ms / fits.len() as f64,
        rayon::current_num_threads()
    );
    eprintln!(
        "extrapolated to a 60-frame stack: {:.2} s",
        align_ms / fits.len() as f64 * 59.0 / 1e3
    );

    // Chaining adjacent pairs is the obvious alternative to aligning every
    // frame against a fixed reference. Compose the chain and compare it with
    // the direct fit, which is ground truth for this purpose.
    eprintln!("\n=== chained adjacent alignment vs direct alignment ===");
    let adj: Vec<Option<Stage>> = (0..planes.len() - 1)
        .into_par_iter()
        .map(|k| align(&planes[k], &planes[k + 1]))
        .collect();
    if adj.iter().all(|a| a.is_some()) {
        let steps: Vec<Fit> = adj.iter().map(|a| a.as_ref().unwrap().fit).collect();
        let adj_rms: f32 =
            adj.iter().map(|a| a.as_ref().unwrap().rms).sum::<f32>() / steps.len() as f32;
        let chained = compose(&steps);
        if let Some(direct) = fits.last().and_then(|f| f.as_ref()) {
            let dg = (chained.g - direct.fit.g) as f64;
            let dx = (chained.ax - direct.fit.ax) as f64;
            let dy = (chained.ay - direct.fit.ay) as f64;
            eprintln!(
                "adjacent-pair fits: mean residual {adj_rms:.3} px ({} pairs)",
                steps.len()
            );
            eprintln!(
                "chained: g {:+.6}  r {:+.6}  tx {:+.3}  ty {:+.3}",
                chained.g, chained.r, chained.ax, chained.ay
            );
            eprintln!(
                " direct: g {:+.6}  r {:+.6}  tx {:+.3}  ty {:+.3}",
                direct.fit.g, direct.fit.r, direct.fit.ax, direct.fit.ay
            );
            eprintln!(
                "chaining error: {:.3} px at the plane corner from scale, {:.3} px from translation",
                dg.abs() * radius,
                (dx * dx + dy * dy).sqrt()
            );
        }
    } else {
        eprintln!("some adjacent pairs failed to align");
    }
}
