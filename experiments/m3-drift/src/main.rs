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

use rayon::prelude::*;
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

/// Zero-mean normalised cross-correlation of one reference tile against the
/// moving plane, searching a square window around `(px, py)`.
///
/// Returns the displacement that carries the reference tile onto the moving
/// plane, with parabolic sub-pixel refinement, plus the peak correlation.
fn ncc_tile(
    rf: &Plane,
    mv: &Plane,
    tx: usize,
    ty: usize,
    ts: usize,
    px: f32,
    py: f32,
    radius: i32,
) -> Option<(f32, f32, f32)> {
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
    // Contrast floor: a featureless tile has no displacement information and
    // will happily report a confident answer built out of noise.
    if sa / (ts * ts) as f32 <= 4.0 {
        return None;
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

    if !best.is_finite() || best < 0.5 {
        return None;
    }
    // A peak on the search border means the true optimum is outside the window.
    if bi == 0 || bj == 0 || bi == n - 1 || bj == n - 1 {
        return None;
    }
    let sc = |i: usize, j: usize| scores[j * n + i];
    let ox = parabola(sc(bi - 1, bj), sc(bi, bj), sc(bi + 1, bj));
    let oy = parabola(sc(bi, bj - 1), sc(bi, bj), sc(bi, bj + 1));
    Some((
        (bx + bi as i32 - radius) as f32 + ox,
        (by + bj as i32 - radius) as f32 + oy,
        best,
    ))
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
    let (cx, cy) = (rf.w as f32 * 0.5, rf.h as f32 * 0.5);
    let margin = radius as usize + 4;
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

    let obs: Vec<Obs> = spots
        .par_iter()
        .filter_map(|&(tx, ty)| {
            let (mx, my) = (tx as f32 + tile as f32 * 0.5, ty as f32 + tile as f32 * 0.5);
            let (px, py) = seed.map(|s| s.at(mx, my, cx, cy)).unwrap_or((0.0, 0.0));
            let (dx, dy, _) = ncc_tile(rf, mv, tx, ty, tile, px, py, radius)?;
            Some(Obs {
                ux: mx - cx,
                uy: my - cy,
                dx,
                dy,
            })
        })
        .collect();

    let total = spots.len();
    if obs.len() < 8 {
        return None;
    }

    // One robust pass: fit, drop anything beyond 3 scaled MADs, refit.
    let f0 = fit_similarity(&obs)?;
    let mut res = residuals(&obs, &f0);
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

    let kept: Vec<Obs> = obs
        .into_iter()
        .zip(res.iter())
        .filter(|(_, r)| **r <= cut)
        .map(|(o, _)| o)
        .collect();
    if kept.len() < 8 {
        return None;
    }
    let fit = fit_similarity(&kept)?;
    res = residuals(&kept, &fit);
    let rms = (res.iter().map(|r| r * r).sum::<f32>() / res.len() as f32).sqrt();
    let (rms_affine, rms_quad) = model_ladder(&kept);
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
    })
}

/// Coarse global fit on an 8x-decimated plane, then an independent fine fit at
/// plane resolution seeded from it. No chaining between frames.
fn align(rf: &Plane, mv: &Plane) -> Option<Stage> {
    const CF: usize = 8;
    let rc = downsample(rf, CF);
    let mc = downsample(mv, CF);
    let coarse = fit_stage(&rc, &mc, 32, 8, 6, 10, None)?;
    let seed = Fit {
        ax: coarse.fit.ax * CF as f32,
        ay: coarse.fit.ay * CF as f32,
        g: coarse.fit.g,
        r: coarse.fit.r,
    };
    fit_stage(rf, mv, 128, 12, 8, 6, Some(seed))
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

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: drift-bench <dir> [limit] | drift-bench --synthetic <dir>");
        std::process::exit(2);
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
