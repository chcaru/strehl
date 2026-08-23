//! The alignment estimator: tiled normalised cross-correlation with parabolic
//! sub-pixel refinement, fitting a 4-parameter similarity by least squares over
//! the tile displacement field, with one MAD outlier pass.
//!
//! Behaviour-identical to `experiments/m3-drift`'s estimator, which is what M3
//! §0 validated against known warps and what M6 used. M10 adds only
//! *configuration*: an arbitrary decimation pyramid and an arbitrary anchor
//! margin, so that candidate (d) -- coarse-to-fine rescue -- can be tested
//! against the same code path. The default configuration reproduces M3 exactly.

use crate::plane::{downsample, Plane};
use rayon::prelude::*;

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Fit {
    pub ax: f32,
    pub ay: f32,
    pub g: f32,
    pub r: f32,
}

impl Fit {
    /// Displacement predicted at plane point `(x, y)`, relative to plane centre.
    pub fn at(&self, x: f32, y: f32, cx: f32, cy: f32) -> (f32, f32) {
        let (ux, uy) = (x - cx, y - cy);
        (
            self.ax + self.g * ux - self.r * uy,
            self.ay + self.r * ux + self.g * uy,
        )
    }

    /// Exact inverse map: the plane point that `(x, y)` came from under this
    /// similarity.
    ///
    /// The forward map is `T(p) = a*p + b` with `a = (1+g) + i*rot`, so the
    /// inverse is `(q - b)/a`. Warping by `p - d(p)` instead — the linearised
    /// inverse — is wrong at second order, and the error it plants at the plane
    /// corner is `g^2 * rho`, which for the 4.6% scale drift of a 105-frame
    /// stack is 4.3 px. That is the same size as the effect M10 is trying to
    /// measure, so the control has to use the exact inverse.
    pub fn inv_at(&self, x: f32, y: f32, cx: f32, cy: f32) -> (f32, f32) {
        let (ux, uy) = (x - cx - self.ax, y - cy - self.ay);
        let (ar, ai) = (1.0 + self.g, self.r);
        let den = ar * ar + ai * ai;
        (
            cx + (ux * ar + uy * ai) / den,
            cy + (uy * ar - ux * ai) / den,
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

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TileStatus {
    Ok,
    LowContrast,
    LowPeak,
    Border,
    Oob,
}

pub struct TileMeas {
    pub status: TileStatus,
    /// Mean square of the zero-mean reference tile, in DN^2. Retained because it
    /// is what the contrast floor tests; M10 does not record per-tile rows.
    #[allow(dead_code)]
    pub contrast: f32,
    pub dx: f32,
    pub dy: f32,
    pub peak: f32,
}

/// Zero-mean normalised cross-correlation of one reference tile against the
/// moving plane, searching a square window around `(px, py)`.
#[allow(clippy::too_many_arguments)]
pub fn ncc_tile_full(
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
                let pivot = m[c];
                for (v, p) in m[r].iter_mut().zip(pivot.iter()).skip(c) {
                    *v -= f * p;
                }
            }
        }
    }
    Some([m[0][4], m[1][4], m[2][4], m[3][4]])
}

#[derive(Clone, Copy)]
pub struct Obs {
    pub ux: f32,
    pub uy: f32,
    pub dx: f32,
    pub dy: f32,
}

pub fn fit_similarity(obs: &[Obs]) -> Option<Fit> {
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

pub struct Stage {
    pub fit: Fit,
    pub used: usize,
    pub total: usize,
    pub rms: f32,
    pub raw_n: usize,
    /// RMS radius of the tiles that survived, i.e. the lever arm the scale
    /// estimate actually rests on. Needed to turn a tile rms into a corner-error
    /// standard error without assuming the grid.
    pub lever_rms: f32,
    /// Mean correlation peak over the tiles that survived.
    pub peak_mean: f32,
}

pub fn tile_grid_m(
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

pub fn fit_stage_at(
    rf: &Plane,
    mv: &Plane,
    tile: usize,
    spots: &[(usize, usize)],
    radius: i32,
    seed: Option<Fit>,
) -> Option<Stage> {
    let (cx, cy) = (rf.w as f32 * 0.5, rf.h as f32 * 0.5);

    let meas: Vec<(f32, f32, TileMeas)> = spots
        .par_iter()
        .map(|&(tx, ty)| {
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
            (mx - cx, my - cy, m)
        })
        .collect();

    let mut obs: Vec<Obs> = Vec::new();
    let mut peaks: Vec<f32> = Vec::new();
    for (ux, uy, m) in &meas {
        if m.status == TileStatus::Ok {
            obs.push(Obs {
                ux: *ux,
                uy: *uy,
                dx: m.dx,
                dy: m.dy,
            });
            peaks.push(m.peak);
        }
    }

    let total = spots.len();
    if obs.len() < 8 {
        return None;
    }

    let f0 = fit_similarity(&obs)?;
    let res = residuals(&obs, &f0);
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
    let lever_rms = (kept
        .iter()
        .map(|o| (o.ux * o.ux + o.uy * o.uy) as f64)
        .sum::<f64>()
        / kept.len() as f64)
        .sqrt() as f32;
    let peak_kept: Vec<f32> = peaks
        .iter()
        .zip(&keep_mask)
        .filter(|(_, k)| **k)
        .map(|(p, _)| *p)
        .collect();
    let peak_mean = peak_kept.iter().sum::<f32>() / peak_kept.len() as f32;

    Some(Stage {
        fit,
        used: kept.len(),
        total,
        rms,
        raw_n,
        lever_rms,
        peak_mean,
    })
}

/// Estimator configuration. `AlignCfg::m3()` is exactly M3's estimator.
#[derive(Clone, Debug)]
pub struct AlignCfg {
    /// Decimation factors for the coarse ladder, largest first. `[8]` is M3.
    pub coarse_factors: Vec<usize>,
    pub coarse_tile: usize,
    pub coarse_grid: (usize, usize),
    pub coarse_radius: i32,
    pub fine_tile: usize,
    pub fine_grid: (usize, usize),
    pub fine_radius: i32,
    /// Anchor margin at plane resolution. M3 uses `fine_radius + 4` = 10.
    pub margin: usize,
}

impl AlignCfg {
    /// M3's published estimator, verbatim.
    pub fn m3() -> Self {
        Self {
            coarse_factors: vec![8],
            coarse_tile: 32,
            coarse_grid: (8, 6),
            coarse_radius: 10,
            fine_tile: 128,
            fine_grid: (12, 8),
            fine_radius: 6,
            margin: 10,
        }
    }

    /// M10's default: M3's estimator with the anchor grid inset far enough that
    /// a tile survives the 89 plane px of corner drift the 105-frame stack
    /// carries (M6 fact 32). Insetting censors no tile; leaving it at 10 px
    /// censors exactly the high-lever-arm corner tiles on long-span pairs, which
    /// are the ones the scale estimate rests on.
    pub fn m10() -> Self {
        Self {
            margin: 96,
            ..Self::m3()
        }
    }

    /// Candidate (d): a deeper pyramid and a wider fine search. Tests whether a
    /// no-fit pair is a capture-range failure or a content failure.
    pub fn wide() -> Self {
        Self {
            coarse_factors: vec![32, 16, 8],
            coarse_radius: 12,
            fine_radius: 12,
            margin: 96,
            ..Self::m3()
        }
    }

    /// `wide` with a 64 px correlation template on a denser grid. A rigid
    /// template of side `T` correlated across a scale difference `g` is
    /// internally stretched by `g*T` px, so if the wide-baseline floor is a
    /// template-stretch effect it must halve when `T` halves. If it is a
    /// capture-range effect, `wide` alone already fixes it and this changes
    /// nothing.
    pub fn wide64() -> Self {
        Self {
            fine_tile: 64,
            fine_grid: (16, 11),
            ..Self::wide()
        }
    }
}

/// Decimated copies of one plane, at the factors a configuration asks for.
pub struct Pyramid {
    pub factors: Vec<usize>,
    pub levels: Vec<Plane>,
}

pub fn build_pyramid(p: &Plane, cfg: &AlignCfg) -> Pyramid {
    Pyramid {
        factors: cfg.coarse_factors.clone(),
        levels: cfg
            .coarse_factors
            .iter()
            .map(|f| downsample(p, *f))
            .collect(),
    }
}

/// Coarse-to-fine similarity fit of `mv` against `rf`.
///
/// The coarse ladder exists only to bring the fine search into capture range;
/// all accuracy comes from the fine stage, which correlates `rf` against `mv`
/// **directly**. Nothing composes one pair's fit into another pair's, so
/// AGENTS.md rule 6 is not touched by the estimator itself.
pub fn align_with(
    rp: &Pyramid,
    mp: &Pyramid,
    rf: &Plane,
    mv: &Plane,
    spots: &[(usize, usize)],
    cfg: &AlignCfg,
) -> Option<Stage> {
    let mut seed: Option<Fit> = None;
    for (li, f) in rp.factors.iter().enumerate() {
        let (rc, mc) = (&rp.levels[li], &mp.levels[li]);
        let cspots = tile_grid_m(
            rc,
            cfg.coarse_tile,
            cfg.coarse_grid.0,
            cfg.coarse_grid.1,
            cfg.coarse_radius as usize + 4,
        )?;
        // Carry the previous level's translation down into this level's units.
        let lseed = seed.map(|s| Fit {
            ax: s.ax / *f as f32,
            ay: s.ay / *f as f32,
            g: s.g,
            r: s.r,
        });
        let st = fit_stage_at(rc, mc, cfg.coarse_tile, &cspots, cfg.coarse_radius, lseed)?;
        seed = Some(Fit {
            ax: st.fit.ax * *f as f32,
            ay: st.fit.ay * *f as f32,
            g: st.fit.g,
            r: st.fit.r,
        });
    }
    fit_stage_at(rf, mv, cfg.fine_tile, spots, cfg.fine_radius, seed)
}

/// Corner error between two similarities, in plane px: the largest difference in
/// where they send the four plane corners. This is the unit every M10 figure is
/// quoted in.
pub fn corner_err(a: &Fit, b: &Fit, w: usize, h: usize) -> f32 {
    let (cx, cy) = (w as f32 * 0.5, h as f32 * 0.5);
    let mut worst = 0f32;
    for (x, y) in [
        (0.0, 0.0),
        (w as f32, 0.0),
        (0.0, h as f32),
        (w as f32, h as f32),
    ] {
        let (ax, ay) = a.at(x, y, cx, cy);
        let (bx, by) = b.at(x, y, cx, cy);
        worst = worst.max(((ax - bx).powi(2) + (ay - by).powi(2)).sqrt());
    }
    worst
}

/// Compose a run of similarity fits into one transform.
///
/// A displacement field `d(p) = b + s*p` about the plane centre is the map
/// `p' = a*p + b` with `a = 1 + s`. Applying step 1 then step 2 gives
/// `a = a1*a2`, `b = a2*b1 + b2`.
pub fn compose(steps: &[Fit]) -> Fit {
    let (mut tr, mut ti) = (1.0f64, 0.0f64);
    let (mut ar, mut ai) = (0.0f64, 0.0f64);
    for f in steps {
        let (sr, si) = (1.0 + f.g as f64, f.r as f64);
        let (nr, ni) = (tr * sr - ti * si, tr * si + ti * sr);
        let (par, pai) = (
            sr * ar - si * ai + f.ax as f64,
            sr * ai + si * ar + f.ay as f64,
        );
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
