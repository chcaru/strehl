//! M93 — gating the focus election, and whether the gate eats detail.
//!
//! `robust.rs` is included by path rather than as `strehl_core::robust`, because
//! wiring it into `lib.rs` is a shared registration point that belongs to the
//! orchestrator (discipline 588; M85 committing M86's `pub mod align;` line is
//! the recorded near-miss). The module is written with no `crate::` references
//! so the two inclusion routes are equivalent, and the wiring patch is given
//! verbatim in `docs/research/M93-election-gate.md` §10.
//!
//! Modes:
//!   gate  <DIR>   the real-stack arms: G0, G1, G2, G4a, G4b, G4c, G5
//!   synth <DIR>   the synthetic sharp-frame guard with known ground truth: G3

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::CfaPlane;
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{DEFAULT_GATE, FocusStats, Gate, regularise};
use strehl_core::noise::NoiseModel;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

#[path = "../../strehl-core/src/robust.rs"]
#[allow(dead_code)] // pub API of the module; the example exercises a subset.
mod robust;
use robust::{Arm, RobustElection};

// ---------------------------------------------------------------------------
// Constants. The operator and the weight are fact 1186's and are not re-tuned.
// ---------------------------------------------------------------------------

/// Window and order of the leave-one-out predictor. `(5, 2)` is fact 1186's
/// primary operator: residual kernel `[1, -4, 6, -4, 1] / 6`.
const W: usize = 5;
const P: usize = 2;
const H: usize = (W - 1) / 2;

/// `|z|` above which a sample is called discrepant, for reporting only. This is
/// the upper knee of the weight and introduces no constant of its own.
const HOT_Z: f32 = 8.0;

/// Neighbourhood radius for the local-detail axis, from M89.
const DETAIL_RADIUS: usize = 4;

/// Absolute detail-SNR bin edges, in sigmas. Cross-ISO comparable, which
/// rank-based deciles are not.
const SNR_EDGES: [f32; 10] = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0];

/// Frame-index distance at which a pixel's winner counts as speckle against its
/// 3x3 neighbourhood median.
const SPECKLE_FRAMES: i32 = 5;

/// Arms folded in pass one. Arm 3 is arm S driven by a spatially shuffled `z`:
/// the G5 placebo.
const ARMS: usize = 4;
const ARM_NAMES: [&str; ARMS] = [
    "0 ungated    ",
    "H hard gate  ",
    "S soft demote",
    "G5 shuffled-z",
];
const ARM_KIND: [Arm; ARMS] = [Arm::Ungated, Arm::Hard, Arm::Soft, Arm::Soft];

/// Split-half subsets for the `H` continuity check: evens and odds.
const SUBS: usize = 2;

// ---------------------------------------------------------------------------
// The statistic. Copied from M89 rather than shared, so this milestone cannot
// silently alter M89's committed instrument.
// ---------------------------------------------------------------------------

fn loo_residual_kernel(w: usize, p: usize) -> Vec<f64> {
    assert!(w >= 3 && w % 2 == 1, "window must be odd and at least 3");
    let h = (w - 1) / 2;
    assert!(p < w - 1, "order {p} needs {} neighbours", p + 1);
    let xs: Vec<f64> = (0..w)
        .filter(|&j| j != h)
        .map(|j| j as f64 - h as f64)
        .collect();
    let m = p + 1;
    let mut a = vec![vec![0.0f64; m + 1]; m];
    for (row, ar) in a.iter_mut().enumerate() {
        for (col, cell) in ar.iter_mut().enumerate().take(m) {
            *cell = xs.iter().map(|x| x.powi((row + col) as i32)).sum();
        }
        ar[m] = f64::from(u8::from(row == 0));
    }
    for col in 0..m {
        let piv = (col..m)
            .max_by(|&i, &j| {
                a[i][col]
                    .abs()
                    .partial_cmp(&a[j][col].abs())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .expect("non-empty");
        a.swap(col, piv);
        let d = a[col][col];
        assert!(d.abs() > 1e-12, "singular design");
        for v in a[col].iter_mut() {
            *v /= d;
        }
        let pivot = a[col].clone();
        for (row, arow) in a.iter_mut().enumerate() {
            if row != col {
                let f = arow[col];
                if f != 0.0 {
                    for (t, p) in arow.iter_mut().zip(&pivot).skip(col) {
                        *t -= f * p;
                    }
                }
            }
        }
    }
    let v: Vec<f64> = (0..m).map(|i| a[i][m]).collect();
    let mut r = vec![0.0f64; w];
    let mut ksum = 0.0f64;
    let mut n = 0usize;
    for (j, rj) in r.iter_mut().enumerate() {
        if j == h {
            *rj = 1.0;
            continue;
        }
        let x = xs[n];
        n += 1;
        let kj: f64 = (0..m).map(|q| v[q] * x.powi(q as i32)).sum();
        ksum += kj;
        *rj = -kj;
    }
    assert!((ksum - 1.0).abs() < 1e-9, "LOO weights sum to {ksum}, not 1");
    r
}

struct Op {
    r: Vec<f32>,
    r2: Vec<f32>,
    r2_sum: f32,
}

impl Op {
    fn new() -> Self {
        let r = loo_residual_kernel(W, P);
        let r32: Vec<f32> = r.iter().map(|&v| v as f32).collect();
        let r2: Vec<f32> = r32.iter().map(|v| v * v).collect();
        Self {
            r2_sum: r2.iter().sum(),
            r: r32,
            r2,
        }
    }
}

/// `var(L) = a*L + b`, extracted from the calibrated model and verified affine.
struct AffineVar {
    a: f32,
    b: f32,
}

impl AffineVar {
    fn from(noise: &NoiseModel) -> Self {
        let b = noise.green_luma_sigma(0.0).powi(2);
        let a = noise.green_luma_sigma(1.0).powi(2) - b;
        let v = Self { a, b };
        for probe in [10.0f32, 1000.0, 8000.0] {
            let want = noise.green_luma_sigma(probe).powi(2);
            let got = v.a * probe + v.b;
            assert!(
                (got - want).abs() <= 1e-3 * want.max(1.0),
                "green_luma_sigma is not affine at {probe}: model {want}, affine {got}"
            );
        }
        v
    }
}

/// `z` for pixel `i` from the ring, with an optional per-slot photometric gain.
///
/// `ring` holds luma **already multiplied** by the per-slot gain `cs`. Fact 608
/// binds here: the noise model must see unscaled DN, so the variance carries the
/// scale rather than the level being un-scaled before the lookup. For
/// `L' = c * L`, `var(L') = c^2 (a*L + b) = a*c*L' + b*c^2`, which is what the
/// denominator below evaluates. With every `c = 1` this reduces exactly to
/// `a * sum(r^2 * L) + b * sum(r^2)`.
#[inline]
fn z_at(
    ring: &[Vec<f32>],
    slots: &[usize],
    cs: &[f32],
    op: &Op,
    av: &AffineVar,
    i: usize,
) -> f32 {
    let mut num = 0.0f32;
    let mut vs = 0.0f32;
    for (j, &s) in slots.iter().enumerate() {
        let l = ring[s][i];
        let c = cs[j];
        num += op.r[j] * l;
        vs += op.r2[j] * (av.a * c * l + av.b * c * c);
    }
    num / vs.sqrt()
}

/// The all-ones gain vector: the un-normalised path.
const UNIT_C: [f32; W] = [1.0; W];

/// Slot list for the window centred on frame `c` in a ring of depth `W`.
fn slots_for(c: usize) -> Vec<usize> {
    (0..W).map(|j| (c + j - H) % W).collect()
}

// ---------------------------------------------------------------------------
// Decode plumbing
// ---------------------------------------------------------------------------

struct Loader {
    geom: PlaneGeometry,
    noise: NoiseModel,
    black: f32,
    iso: Option<f32>,
    paths: Vec<PathBuf>,
}

struct Planes {
    luma: Vec<f32>,
    graw: Vec<f32>,
    clipped: Vec<bool>,
}

impl Loader {
    fn open(dir: &Path, limit: Option<usize>) -> Result<Self> {
        let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
            .with_context(|| format!("reading {}", dir.display()))?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
            .collect();
        paths.sort();
        if let Some(n) = limit {
            paths.truncate(n);
        }
        if paths.len() < W + 2 {
            bail!("{} holds {} ARW files", dir.display(), paths.len());
        }
        let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
        let geom = first.geometry();
        let levels = first.levels;
        let noise = profile::noise_model_for(&first.camera, first.iso, levels);
        Ok(Self {
            geom,
            noise,
            black: levels.black,
            iso: first.iso,
            paths,
        })
    }

    fn n(&self) -> usize {
        self.paths.len()
    }

    fn blank(&self) -> Planes {
        Planes {
            luma: vec![0.0; self.geom.pixels()],
            graw: vec![0.0; self.geom.pixels()],
            clipped: vec![false; self.geom.pixels()],
        }
    }

    fn load(&self, f: usize, out: &mut Planes) -> Result<()> {
        let frame = strehl_raw::decode(&self.paths[f])
            .with_context(|| format!("decoding {}", self.paths[f].display()))?;
        if frame.geometry() != self.geom {
            bail!("{} has a different plane geometry", self.paths[f].display());
        }
        green_luma_with_clip(
            &frame,
            self.black,
            CONTAINER_MAX_DN,
            &mut out.luma,
            &mut out.clipped,
        );
        let g1o = CfaPlane::G1.rggb_offset();
        let g2o = CfaPlane::G2.rggb_offset();
        for py in 0..self.geom.height {
            let (row0, row1) = frame.quad_rows(py);
            let r1 = if g1o.1 == 0 { row0 } else { row1 };
            let r2 = if g2o.1 == 0 { row0 } else { row1 };
            let base = py * self.geom.width;
            for px in 0..self.geom.width {
                out.graw[base + px] =
                    0.5 * (f32::from(r1[2 * px + g1o.0]) + f32::from(r2[2 * px + g2o.0]));
            }
        }
        Ok(())
    }
}

/// Separable box mean, radius `rad`, edge-clamped.
fn box_mean(src: &[f32], geom: PlaneGeometry, rad: usize, scratch: &mut [f32], dst: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    let inv = 1.0 / (2 * rad + 1) as f32;
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        let mut acc = row[0] * rad as f32;
        for v in row.iter().take(rad.min(w - 1) + 1) {
            acc += *v;
        }
        for x in 0..w {
            scratch[y * w + x] = acc * inv;
            let add = row[(x + rad + 1).min(w - 1)];
            let sub = row[x.saturating_sub(rad)];
            acc += add - sub;
        }
    }
    for x in 0..w {
        let mut acc = scratch[x] * rad as f32;
        for y in 0..=rad.min(h - 1) {
            acc += scratch[y * w + x];
        }
        for y in 0..h {
            dst[y * w + x] = acc * inv;
            let add = scratch[(y + rad + 1).min(h - 1) * w + x];
            let sub = scratch[y.saturating_sub(rad) * w + x];
            acc += add - sub;
        }
    }
}

/// Local detail and local level, from a strided sample of the stack.
fn detail_axis(ld: &Loader, stride: usize) -> Result<(Vec<f32>, Vec<f32>)> {
    let geom = ld.geom;
    let px = geom.pixels();
    let mut detail = vec![0.0f32; px];
    let mut level = vec![0.0f32; px];
    let mut used = 0usize;
    let mut p = ld.blank();
    let mut g = vec![0.0f32; px];
    let mut sc = vec![0.0f32; px];
    let mut bx = vec![0.0f32; px];
    let mut f = 0usize;
    while f < ld.n() {
        ld.load(f, &mut p)?;
        for y in 0..geom.height {
            for x in 0..geom.width {
                let i = y * geom.width + x;
                let xm = x.saturating_sub(1);
                let xp = (x + 1).min(geom.width - 1);
                let ym = y.saturating_sub(1);
                let yp = (y + 1).min(geom.height - 1);
                let gx = p.luma[y * geom.width + xp] - p.luma[y * geom.width + xm];
                let gy = p.luma[yp * geom.width + x] - p.luma[ym * geom.width + x];
                g[i] = 0.5 * (gx.abs() + gy.abs());
            }
        }
        box_mean(&g, geom, DETAIL_RADIUS, &mut sc, &mut bx);
        for i in 0..px {
            detail[i] = detail[i].max(bx[i]);
        }
        box_mean(&p.luma, geom, DETAIL_RADIUS, &mut sc, &mut bx);
        for i in 0..px {
            level[i] += bx[i];
        }
        used += 1;
        f += stride;
    }
    for v in level.iter_mut() {
        *v /= used as f32;
    }
    Ok((detail, level))
}

fn detail_snr(detail: &[f32], level: &[f32], model: &NoiseModel) -> Vec<f32> {
    detail
        .iter()
        .zip(level)
        .map(|(&d, &l)| d / model.green_luma_sigma(l.max(0.0)).max(1e-6))
        .collect()
}

fn strata_map(values: &[f32], edges: &[f32]) -> Vec<u8> {
    values
        .iter()
        .map(|&v| {
            let mut k = 0u8;
            for (j, &e) in edges.iter().enumerate() {
                if v >= e {
                    k = j as u8;
                }
            }
            k
        })
        .collect()
}

/// A deterministic permutation of `0..n`, for the G5 placebo.
fn shuffle_index(n: usize, seed: u64) -> Vec<u32> {
    let mut v: Vec<u32> = (0..n as u32).collect();
    let mut s = seed | 1;
    for i in (1..n).rev() {
        s = s
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let j = (s >> 33) as usize % (i + 1);
        v.swap(i, j);
    }
    v
}

/// Fraction of pixels whose elected frame differs from the median elected frame
/// of its 3x3 neighbourhood by more than [`SPECKLE_FRAMES`].
///
/// The winner field is a depth map and should be spatially smooth. Motion breaks
/// that; defocus, being monotone in frame index, does not.
fn speckle(win: &[u16], geom: PlaneGeometry) -> f64 {
    let (w, h) = (geom.width, geom.height);
    let mut hits = 0u64;
    let mut n = 0u64;
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let mut nb = [0u16; 9];
            let mut k = 0;
            for dy in 0..3 {
                for dx in 0..3 {
                    nb[k] = win[(y + dy - 1) * w + (x + dx - 1)];
                    k += 1;
                }
            }
            nb.sort_unstable();
            if (win[y * w + x] as i32 - nb[4] as i32).abs() > SPECKLE_FRAMES {
                hits += 1;
            }
            n += 1;
        }
    }
    hits as f64 / n as f64
}

/// One merged image: the shipped noise-gated average around a given winner
/// field. The average is **not** masked — fact 1189 rules out re-specifying the
/// average-side mask, so the election is the only thing that differs by arm.
struct Acc {
    sum: Vec<f32>,
    n: Vec<u32>,
}

impl Acc {
    fn new(px: usize) -> Self {
        Self {
            sum: vec![0.0; px],
            n: vec![0; px],
        }
    }
}

fn percentile(sorted: &[f32], q: f64) -> f32 {
    if sorted.is_empty() {
        return f32::NAN;
    }
    sorted[((sorted.len() - 1) as f64 * q).round() as usize]
}

// ---------------------------------------------------------------------------
// gate: the real-stack measurement
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_lines, clippy::needless_range_loop)]
fn gate_run(dir: &Path, limit: Option<usize>, gate: f32, photonorm: bool) -> Result<()> {
    let ld = Loader::open(dir, limit)?;
    let geom = ld.geom;
    let px = geom.pixels();
    let op = Op::new();
    let av = AffineVar::from(&ld.noise);
    let n = ld.n();

    println!("stack           : {}", dir.display());
    println!("frames          : {n}   gate {gate}   photonorm {photonorm}");
    println!("plane           : {} x {}", geom.width, geom.height);
    println!("iso / black     : {:?} / {}", ld.iso, ld.black as i32);
    println!(
        "green var model : var(L) = {:.6}*L + {:.4}   (extracted from NoiseModel)",
        av.a, av.b
    );
    println!(
        "operator        : w={W} p={P}   6*r = {:?}   sum r^2 = {:.4}",
        op.r.iter().map(|v| (v * 6.0).round()).collect::<Vec<_>>(),
        op.r2_sum
    );

    let (detail, level) = detail_axis(&ld, 8.max(n / 24))?;
    let dsnr = detail_snr(&detail, &level, &ld.noise);
    let sstrat = strata_map(&dsnr, &SNR_EDGES);
    drop(detail);
    drop(level);
    drop(dsnr);

    let perm = shuffle_index(px, 0x9315_2093);

    let mut field = FocusField::new(geom);
    let mut boxsc = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];
    let mut lring: Vec<Vec<f32>> = (0..W).map(|_| vec![0.0f32; px]).collect();
    let mut cring: Vec<f32> = vec![1.0; n];
    let mut ref_level: Option<f64> = None;
    let mut rring: Vec<Vec<f32>> = (0..W).map(|_| vec![0.0f32; px]).collect();
    let mut p = ld.blank();

    let mut whole: Vec<RobustElection> = (0..ARMS)
        .map(|a| RobustElection::new(px, ARM_KIND[a]))
        .collect();
    let mut halves: Vec<Vec<RobustElection>> = (0..ARMS)
        .map(|a| {
            (0..SUBS)
                .map(|_| RobustElection::new(px, ARM_KIND[a]))
                .collect()
        })
        .collect();
    let mut ref_stats = FocusStats::new(geom);

    let mut zbuf = vec![0.0f32; px];
    let mut zshuf = vec![0.0f32; px];
    let zero = vec![0.0f32; px];
    let mut hot_samples = 0u64;
    let mut scored_samples = 0u64;
    let mut folded = vec![false; n];
    let t0 = std::time::Instant::now();

    for f in 0..n {
        ld.load(f, &mut p)?;
        field.compute(&p.luma, &ld.noise);
        regularise(field.values(), geom, &mut boxsc, &mut reg);
        ref_stats.fold(f as u16, &reg)?;
        // Per-frame gain, fitted to the first frame's mean level. This is a
        // deliberately crude stand-in for M91's per-frame photometric fit; it
        // exists only to measure how much of the gate's firing is explained by
        // level drift, not to compete with M91.
        let cf = if photonorm {
            let s: f64 = p.luma.iter().map(|&v| f64::from(v)) .sum::<f64>() / px as f64;
            let r0 = *ref_level.get_or_insert(s);
            if s.abs() < 1e-9 { 1.0 } else { (r0 / s) as f32 }
        } else {
            1.0
        };
        cring[f] = cf;
        if photonorm {
            for (dst, &v) in lring[f % W].iter_mut().zip(p.luma.iter()) {
                *dst = cf * v;
            }
        } else {
            lring[f % W].copy_from_slice(&p.luma);
        }
        rring[f % W].copy_from_slice(&reg);

        // The leading H frames have no centred window. They enter every arm
        // ungated rather than being silently dropped.
        if f == W - 1 {
            for c in 0..H {
                let r = rring[c % W].clone();
                for a in 0..ARMS {
                    whole[a]
                        .fold(c as u16, &r, &zero)
                        .map_err(|e| anyhow::anyhow!(e))?;
                    halves[a][c % SUBS]
                        .fold(c as u16, &r, &zero)
                        .map_err(|e| anyhow::anyhow!(e))?;
                }
                folded[c] = true;
            }
        }
        if f >= W - 1 {
            let c = f - H;
            let slots = slots_for(c);
            let cs: Vec<f32> = (0..W).map(|j| cring[c + j - H]).collect();
            for i in 0..px {
                let z = z_at(&lring, &slots, &cs, &op, &av, i);
                zbuf[i] = z;
                if z.abs() > HOT_Z {
                    hot_samples += 1;
                }
            }
            scored_samples += px as u64;
            for i in 0..px {
                zshuf[i] = zbuf[perm[i] as usize];
            }
            let r = rring[c % W].clone();
            for a in 0..ARMS {
                let zf: &[f32] = if a == 3 { &zshuf } else { &zbuf };
                whole[a]
                    .fold(c as u16, &r, zf)
                    .map_err(|e| anyhow::anyhow!(e))?;
                halves[a][c % SUBS]
                    .fold(c as u16, &r, zf)
                    .map_err(|e| anyhow::anyhow!(e))?;
            }
            folded[c] = true;
        }
        if f % 25 == 0 {
            println!("  pass1 frame {f}/{n} ({:.1}s)", t0.elapsed().as_secs_f32());
        }
    }
    for c in n - H..n {
        let r = rring[c % W].clone();
        for a in 0..ARMS {
            whole[a]
                .fold(c as u16, &r, &zero)
                .map_err(|e| anyhow::anyhow!(e))?;
            halves[a][c % SUBS]
                .fold(c as u16, &r, &zero)
                .map_err(|e| anyhow::anyhow!(e))?;
        }
        folded[c] = true;
    }
    assert!(folded.iter().all(|&b| b), "not every frame was folded");
    drop(rring);

    println!(
        "\ndiscrepant samples: {:.6}% of {} scored (|z| > {HOT_Z})",
        100.0 * hot_samples as f64 / scored_samples as f64,
        scored_samples
    );

    // ---- G0: faithfulness --------------------------------------------------
    let wins: Vec<Vec<u16>> = (0..ARMS).map(|a| whole[a].winners()).collect();
    let wresp: Vec<Vec<f32>> = (0..ARMS).map(|a| whole[a].winner_response()).collect();
    let matched = wins[0]
        .iter()
        .zip(ref_stats.best_index())
        .filter(|(a, b)| a == b)
        .count();
    println!(
        "\n--- G0: faithfulness of arm 0 to the shipped election ---\n\
         G0 election     : {matched}/{px} pixels ({:.6}%) match FocusStats::best_index exactly",
        100.0 * matched as f64 / px as f64
    );

    // ---- G1 / G4b ----------------------------------------------------------
    println!("\n--- G1/G4b: what each arm changes, and what it costs (MEASURED) ---");
    let spk0 = speckle(&wins[0], geom);
    let ung: f64 = wresp[0].iter().map(|&v| v as f64).sum();
    let mut changed = [0u64; ARMS];
    let mut spk = vec![0.0f64; ARMS];
    for a in 0..ARMS {
        changed[a] = wins[a]
            .iter()
            .zip(&wins[0])
            .filter(|(x, y)| x != y)
            .count() as u64;
        spk[a] = speckle(&wins[a], geom);
        let s: f64 = wresp[a].iter().map(|&v| v as f64).sum();
        println!(
            "arm {} changed {:>9.6}%  fallback {:>9.6}%  speckle {:.5e} ({:+7.2}%)  \
             mean response {:.5} ({:+.6}%)",
            ARM_NAMES[a],
            100.0 * changed[a] as f64 / px as f64,
            100.0 * whole[a].fallbacks() as f64 / px as f64,
            spk[a],
            100.0 * (spk[a] / spk0 - 1.0),
            s / px as f64,
            100.0 * (s / ung - 1.0)
        );
    }

    // ---- G2: election change stratified by absolute detail-SNR -------------
    println!("\n--- G2: election-change rate by absolute detail-SNR bin ---");
    let mut binn = vec![0u64; SNR_EDGES.len()];
    for &s in &sstrat {
        binn[s as usize] += 1;
    }
    print!("{:<16}", "SNR bin >=");
    for e in SNR_EDGES {
        print!("{e:>11.1}");
    }
    println!();
    print!("{:<16}", "n");
    for v in &binn {
        print!("{:>11.2e}", *v as f64);
    }
    println!();
    for a in 1..ARMS {
        let mut c = vec![0u64; SNR_EDGES.len()];
        for i in 0..px {
            if wins[a][i] != wins[0][i] {
                c[sstrat[i] as usize] += 1;
            }
        }
        print!("{:<16}", ARM_NAMES[a].trim_end());
        for (j, v) in c.iter().enumerate() {
            if binn[j] == 0 {
                print!("{:>11}", "-");
            } else {
                print!("{:>11.2e}", *v as f64 / binn[j] as f64);
            }
        }
        println!();
    }

    // ---- pass two: hot winners and the split-half average ------------------
    let hwins: Vec<Vec<u16>> = (0..ARMS)
        .map(|a| halves[a][0].winners())
        .chain((0..ARMS).map(|a| halves[a][1].winners()))
        .collect();
    let hresp: Vec<Vec<f32>> = (0..ARMS)
        .map(|a| halves[a][0].winner_response())
        .chain((0..ARMS).map(|a| halves[a][1].winner_response()))
        .collect();
    drop(halves);
    let tol = Gate::new(gate).tolerance();
    println!("\ntolerance       : {tol:.6}   (Gate::new({gate}).tolerance())");
    let mut acc: Vec<Acc> = (0..ARMS * SUBS).map(|_| Acc::new(px)).collect();
    let mut hotwin = vec![0u64; ARMS];
    let t1 = std::time::Instant::now();
    for f in 0..n {
        ld.load(f, &mut p)?;
        field.compute(&p.luma, &ld.noise);
        regularise(field.values(), geom, &mut boxsc, &mut reg);
        if photonorm {
            let cf = cring[f];
            for (dst, &v) in lring[f % W].iter_mut().zip(p.luma.iter()) {
                *dst = cf * v;
            }
        } else {
            lring[f % W].copy_from_slice(&p.luma);
        }
        let s = f % SUBS;
        for a in 0..ARMS {
            let k = s * ARMS + a;
            for i in 0..px {
                if hresp[k][i] - reg[i] <= tol {
                    acc[k].sum[i] += p.graw[i];
                    acc[k].n[i] += 1;
                }
            }
        }
        if f >= W - 1 {
            let c = f - H;
            let slots = slots_for(c);
            let cs: Vec<f32> = (0..W).map(|j| cring[c + j - H]).collect();
            for i in 0..px {
                zbuf[i] = z_at(&lring, &slots, &cs, &op, &av, i);
            }
            for a in 0..ARMS {
                for i in 0..px {
                    if wins[a][i] == c as u16 && zbuf[i].abs() > HOT_Z {
                        hotwin[a] += 1;
                    }
                }
            }
        }
        if f % 25 == 0 {
            println!("  pass2 frame {f}/{n} ({:.1}s)", t1.elapsed().as_secs_f32());
        }
    }
    let _ = &hwins;

    println!("\n--- G4a: hot winners (elected frame's own |z| > {HOT_Z}) ---");
    for a in 0..ARMS {
        println!(
            "arm {} {:>10} pixels ({:.6}%)   {:+.3}% vs arm 0",
            ARM_NAMES[a],
            hotwin[a],
            100.0 * hotwin[a] as f64 / px as f64,
            if hotwin[0] == 0 {
                f64::NAN
            } else {
                100.0 * (hotwin[a] as f64 / hotwin[0] as f64 - 1.0)
            }
        );
    }

    println!("\n--- G4c: split-half disagreement H, in sigmas (MEASURED) ---");
    println!("Pure noise gives E[H] = sqrt(2/pi) = 0.7979.");
    println!(
        "`adm` is the mean number of frames admitted to the average per pixel. It is\n\
         reported because the gate lowers the tolerance band centre, which admits more\n\
         frames, which lowers H by smoothing alone. `dH/dadm` normalises the benefit by\n\
         that increase; compare each arm against the G5 shuffled-z placebo, which raises\n\
         `adm` the same way with no spatial contamination information."
    );
    let mut h0mean = 1.0f64;
    let mut hmeans = vec![0.0f64; ARMS];
    let mut admeans = vec![0.0f64; ARMS];
    let mut h0px: Vec<f32> = vec![f32::NAN; px];
    for a in 0..ARMS {
        let mut hs: Vec<f32> = Vec::with_capacity(px);
        let mut sum = 0.0f64;
        let mut adm = 0.0f64;
        let mut diff_sum = 0.0f64;
        let mut diff_n = 0u64;
        let mut same_n = 0u64;
        let mut violations = 0u64;
        for i in 0..px {
            let (e, o) = (&acc[a], &acc[ARMS + a]);
            if e.n[i] == 0 || o.n[i] == 0 {
                continue;
            }
            let ev = e.sum[i] / e.n[i] as f32;
            let ov = o.sum[i] / o.n[i] as f32;
            let sig = ld
                .noise
                .green_luma_sigma(((ev + ov) * 0.5 - ld.black).max(0.0))
                .max(1e-6);
            let h = (ev - ov).abs() / sig;
            sum += f64::from(h);
            adm += f64::from(e.n[i] + o.n[i]);
            if a == 0 {
                h0px[i] = h;
            } else if hresp[a][i] == hresp[0][i] && hresp[ARMS + a][i] == hresp[ARMS][i] {
                // Both half-election band centres are identical to arm 0's, so
                // the admitted sets are identical and H must be bit-identical.
                same_n += 1;
                if h.to_bits() != h0px[i].to_bits() {
                    violations += 1;
                }
            } else {
                diff_sum += f64::from(h);
                diff_n += 1;
            }
            hs.push(h);
        }
        hs.sort_by(|x, y| x.partial_cmp(y).unwrap_or(std::cmp::Ordering::Equal));
        let mean = sum / hs.len() as f64;
        if a == 0 {
            h0mean = mean;
        }
        hmeans[a] = mean;
        admeans[a] = adm / hs.len() as f64;
        let dh = 100.0 * (mean / h0mean - 1.0);
        let dadm = 100.0 * (admeans[a] / admeans[0] - 1.0);
        println!(
            "arm {} H {:.5} ({:+7.3}%)  med {:.5}  p99 {:>7.4}  p999 {:>7.4}  \
             adm {:>6.2} ({:+6.3}%)  dH/dadm {:>7.3}  H|changed {:.4} ({:>5.2}% px)",
            ARM_NAMES[a],
            mean,
            dh,
            percentile(&hs, 0.5),
            percentile(&hs, 0.99),
            percentile(&hs, 0.999),
            admeans[a],
            dadm,
            if dadm.abs() < 1e-6 { f64::NAN } else { dh / dadm },
            diff_sum / diff_n.max(1) as f64,
            100.0 * diff_n as f64 / hs.len() as f64
        );
        if a > 0 {
            println!(
                "        invariant: H is bit-identical to arm 0 at all {same_n} pixels whose\n\
                 \x20       half-election band centres are unchanged -- {violations} violations ({})",
                if violations == 0 { "PASS" } else { "FAIL - instrument bug" }
            );
            assert_eq!(violations, 0, "H invariant violated on arm {a}");
        }
    }

    println!(
        "\nJSON {{\"stack\":\"{}\",\"n\":{n},\"iso\":{:?},\"g0\":{:.8},\"changed\":{:?},\
         \"speckle\":{:?},\"hotwin\":{:?},\"fallbacks\":{:?},\"hmean\":{:?},\"adm\":{:?},\"resp\":{:?}}}",
        dir.file_name().unwrap_or_default().to_string_lossy(),
        ld.iso,
        matched as f64 / px as f64,
        (0..ARMS)
            .map(|a| changed[a] as f64 / px as f64)
            .collect::<Vec<_>>(),
        spk,
        hotwin,
        (0..ARMS).map(|a| whole[a].fallbacks()).collect::<Vec<_>>(),
        hmeans,
        admeans,
        (0..ARMS)
            .map(|a| wresp[a].iter().map(|&v| v as f64).sum::<f64>() / px as f64)
            .collect::<Vec<_>>()
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// synth: the G3 sharp-frame guard, with known ground truth
// ---------------------------------------------------------------------------

/// Separable Gaussian blur, truncated at 3 sigma, edge-clamped.
fn gaussian(src: &[f32], geom: PlaneGeometry, sigma: f32, scratch: &mut [f32], dst: &mut [f32]) {
    if sigma <= 1e-4 {
        dst.copy_from_slice(src);
        return;
    }
    let rad = (3.0 * sigma).ceil() as isize;
    let k: Vec<f32> = (-rad..=rad)
        .map(|d| (-(d as f32).powi(2) / (2.0 * sigma * sigma)).exp())
        .collect();
    let ks: f32 = k.iter().sum();
    let k: Vec<f32> = k.iter().map(|v| v / ks).collect();
    let (w, h) = (geom.width as isize, geom.height as isize);
    for y in 0..h {
        for x in 0..w {
            let mut a = 0.0f32;
            for (j, &kv) in k.iter().enumerate() {
                let xx = (x + j as isize - rad).clamp(0, w - 1);
                a += kv * src[(y * w + xx) as usize];
            }
            scratch[(y * w + x) as usize] = a;
        }
    }
    for y in 0..h {
        for x in 0..w {
            let mut a = 0.0f32;
            for (j, &kv) in k.iter().enumerate() {
                let yy = (y + j as isize - rad).clamp(0, h - 1);
                a += kv * scratch[(yy * w + x) as usize];
            }
            dst[(y * w + x) as usize] = a;
        }
    }
}

struct Lcg(u64);
impl Lcg {
    fn next_u32(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) as u32
    }
    fn normal(&mut self) -> f32 {
        let u1 = (self.next_u32() as f32 + 1.0) / 4294967296.0;
        let u2 = self.next_u32() as f32 / 4294967296.0;
        (-2.0 * u1.ln()).sqrt() * (std::f32::consts::TAU * u2).cos()
    }
}

/// Build a synthetic through-focus stack from one real frame and measure whether
/// the gate removes the frame that is, by construction, the only one in focus.
///
/// Ground truth: frame `f0` is unblurred, every other frame is blurred by
/// `|f - f0| * step`. `f0` is the correct winner everywhere there is detail.
///
/// **Conservative by construction:** the base frame already carries sensor
/// noise, which blurring attenuates, so `f0` ends up with the *most* total noise
/// of any frame. That inflates `f0`'s `z` and makes the gate *more* likely to
/// remove it, not less.
#[allow(clippy::needless_range_loop)]
fn synth_run(dir: &Path, nframes: usize, crop: usize) -> Result<()> {
    let ld = Loader::open(dir, Some(8))?;
    let full = ld.geom;
    let mut p = ld.blank();
    ld.load(0, &mut p)?;

    let cw = crop.min(full.width);
    let ch = crop.min(full.height);
    let x0 = (full.width - cw) / 2;
    let y0 = (full.height - ch) / 2;
    let geom = PlaneGeometry {
        width: cw,
        height: ch,
    };
    let px = geom.pixels();
    let mut base = vec![0.0f32; px];
    for y in 0..ch {
        for x in 0..cw {
            base[y * cw + x] = p.luma[(y0 + y) * full.width + x0 + x];
        }
    }
    let f0 = nframes / 2;
    let op = Op::new();
    let av = AffineVar::from(&ld.noise);

    println!("base stack      : {}", dir.display());
    println!("crop            : {cw} x {ch} at ({x0},{y0})   frames {nframes}   f0 = {f0}");
    println!("iso             : {:?}", ld.iso);
    println!(
        "green var model : var(L) = {:.6}*L + {:.4}",
        av.a, av.b
    );
    println!(
        "\nGround truth: frame {f0} is the unique correct winner. Any pixel at which the gate\n\
         rules {f0} ineligible is a correctly-elected sharp frame being destroyed.\n\
         A global rate hides the hazard, so f0 gating is also reported inside the top\n\
         detail-SNR bin, which is exactly where electing f0 matters.\n"
    );

    // Detail-SNR axis of the base frame. Fixed across the sweep, so the bins are
    // the same population at every step.
    let mut g = vec![0.0f32; px];
    for y in 0..ch {
        for x in 0..cw {
            let i = y * cw + x;
            let xm = x.saturating_sub(1);
            let xp = (x + 1).min(cw - 1);
            let ym = y.saturating_sub(1);
            let yp = (y + 1).min(ch - 1);
            g[i] = 0.5
                * ((base[y * cw + xp] - base[y * cw + xm]).abs()
                    + (base[yp * cw + x] - base[ym * cw + x]).abs());
        }
    }
    let mut sc0 = vec![0.0f32; px];
    let mut det = vec![0.0f32; px];
    let mut lvl = vec![0.0f32; px];
    box_mean(&g, geom, DETAIL_RADIUS, &mut sc0, &mut det);
    box_mean(&base, geom, DETAIL_RADIUS, &mut sc0, &mut lvl);
    let dsnr = detail_snr(&det, &lvl, &ld.noise);
    let bstrat = strata_map(&dsnr, &SNR_EDGES);
    let mut bn = vec![0u64; SNR_EDGES.len()];
    for &b in &bstrat {
        bn[b as usize] += 1;
    }
    let top = bn
        .iter()
        .enumerate()
        .filter(|(_, c)| **c >= 1000)
        .map(|(j, _)| j)
        .next_back()
        .unwrap_or(0);
    println!("detail-SNR bins (n >= 1000 needed to be usable):");
    for (j, &c) in bn.iter().enumerate() {
        if c > 0 {
            println!(
                "  bin >= {:>6.1} sigma : {:>9} px{}",
                SNR_EDGES[j],
                c,
                if j == top { "   <- top usable" } else { "" }
            );
        }
    }
    println!(
        "\n{:>7} {:>9} {:>11} {:>11} {:>11} {:>10} {:>10} {:>10} {:>10}",
        "step",
        "mean z^2",
        "f0 win a0",
        "f0 win aH",
        "f0 win aS",
        "gated all",
        "gated|a0",
        "gated TOP",
        "respS drop"
    );

    let mut rows: Vec<String> = Vec::new();
    for &step in &[0.05f32, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] {
        let mut sc = vec![0.0f32; px];
        let mut blurred: Vec<Vec<f32>> = Vec::with_capacity(nframes);
        let mut rng = Lcg(0x5EED_0093);
        for f in 0..nframes {
            let mut b = vec![0.0f32; px];
            gaussian(
                &base,
                geom,
                (f as f32 - f0 as f32).abs() * step,
                &mut sc,
                &mut b,
            );
            for v in b.iter_mut() {
                *v += ld.noise.green_luma_sigma((*v).max(0.0)) * rng.normal();
            }
            blurred.push(b);
        }
        let mut field = FocusField::new(geom);
        let mut boxsc = vec![0.0f32; px];
        let mut resp: Vec<Vec<f32>> = Vec::with_capacity(nframes);
        for b in &blurred {
            let mut reg = vec![0.0f32; px];
            field.compute(b, &ld.noise);
            regularise(field.values(), geom, &mut boxsc, &mut reg);
            resp.push(reg);
        }
        let mut arms: Vec<RobustElection> = (0..3)
            .map(|a| RobustElection::new(px, ARM_KIND[a]))
            .collect();
        let zero = vec![0.0f32; px];
        let mut z2sum = 0.0f64;
        let mut z2n = 0u64;
        let mut f0_gated = 0u64;
        let mut f0_gmask: Vec<bool> = Vec::new();
        for c in 0..nframes {
            let zf = if c >= H && c + H < nframes {
                let slots: Vec<usize> = (0..W).map(|j| c + j - H).collect();
                let mut zb = vec![0.0f32; px];
                for i in 0..px {
                    let z = z_at(&blurred, &slots, &UNIT_C, &op, &av, i);
                    zb[i] = z;
                    z2sum += f64::from(z * z);
                    z2n += 1;
                }
                if c == f0 {
                    f0_gmask = zb.iter().map(|z| robust::weight(*z) < 0.5).collect();
                    f0_gated = f0_gmask.iter().filter(|&&b| b).count() as u64;
                }
                zb
            } else {
                zero.clone()
            };
            for a in 0..3 {
                arms[a]
                    .fold(c as u16, &resp[c], &zf)
                    .map_err(|e| anyhow::anyhow!(e))?;
            }
        }
        let wins: Vec<Vec<u16>> = (0..3).map(|a| arms[a].winners()).collect();
        let el: Vec<f64> = (0..3)
            .map(|a| wins[a].iter().filter(|&&v| v == f0 as u16).count() as f64 / px as f64)
            .collect();
        let mut r0 = 0.0f64;
        let mut rs = 0.0f64;
        for i in 0..px {
            r0 += f64::from(resp[wins[0][i] as usize][i]);
            rs += f64::from(resp[wins[2][i] as usize][i]);
        }
        // The two conditional rates. `gated|a0` is the rate among pixels the
        // ungated election already gets right, i.e. the population at risk.
        // `gated TOP` is that same rate inside the highest usable detail bin,
        // which is where losing f0 is most damaging.
        let mut at_risk = 0u64;
        let mut at_risk_gated = 0u64;
        let mut topn = 0u64;
        let mut topg = 0u64;
        for i in 0..px {
            let g = f0_gmask.get(i).copied().unwrap_or(false);
            if wins[0][i] == f0 as u16 {
                at_risk += 1;
                if g {
                    at_risk_gated += 1;
                }
            }
            if bstrat[i] as usize == top {
                topn += 1;
                if g {
                    topg += 1;
                }
            }
        }
        let cond = if at_risk == 0 {
            f64::NAN
        } else {
            at_risk_gated as f64 / at_risk as f64
        };
        let condtop = if topn == 0 {
            f64::NAN
        } else {
            topg as f64 / topn as f64
        };
        println!(
            "{step:>7.2} {:>9.4} {:>10.4}% {:>10.4}% {:>10.4}% {:>9.4}% {:>9.4}% {:>9.4}% {:>9.4}%",
            z2sum / z2n as f64,
            100.0 * el[0],
            100.0 * el[1],
            100.0 * el[2],
            100.0 * f0_gated as f64 / px as f64,
            100.0 * cond,
            100.0 * condtop,
            100.0 * (rs / r0 - 1.0)
        );
        rows.push(format!(
            "{{\"step\":{step},\"z2\":{:.6},\"e0\":{:.8},\"eH\":{:.8},\"eS\":{:.8},\
             \"f0_gated\":{:.8},\"f0_gated_cond\":{:.8},\"f0_gated_top\":{:.8},\
             \"top_bin\":{},\"top_n\":{topn},\"respS\":{:.8}}}",
            z2sum / z2n as f64,
            el[0],
            el[1],
            el[2],
            f0_gated as f64 / px as f64,
            cond,
            condtop,
            SNR_EDGES[top],
            rs / r0 - 1.0
        ));
    }
    println!("\nJSON {{\"synth\":[{}]}}", rows.join(","));
    Ok(())
}

// ---------------------------------------------------------------------------

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!(
            "usage: m93-election gate|synth <DIR> [--limit N] [--gate G] [--frames N] [--crop N]"
        );
        std::process::exit(2);
    }
    let mode = args[0].clone();
    let mut dir = PathBuf::new();
    let mut limit = None;
    let mut gate = DEFAULT_GATE;
    let mut nframes = 41usize;
    let mut crop = 1024usize;
    let mut photonorm = false;
    let mut i = 1usize;
    if i < args.len() && !args[i].starts_with("--") {
        dir = PathBuf::from(&args[i]);
        i += 1;
    }
    while i < args.len() {
        let a = args[i].as_str();
        let mut val = || -> Result<String> {
            i += 1;
            args.get(i).cloned().context("missing flag value")
        };
        match a {
            "--limit" => limit = Some(val()?.parse()?),
            "--gate" => gate = val()?.parse()?,
            "--frames" => nframes = val()?.parse()?,
            "--crop" => crop = val()?.parse()?,
            "--photonorm" => photonorm = true,
            other => bail!("unknown flag {other}"),
        }
        i += 1;
    }
    match mode.as_str() {
        "gate" => gate_run(&dir, limit, gate, photonorm),
        "synth" => synth_run(&dir, nframes, crop),
        _ => {
            eprintln!("unknown mode {mode}");
            std::process::exit(2);
        }
    }
}
