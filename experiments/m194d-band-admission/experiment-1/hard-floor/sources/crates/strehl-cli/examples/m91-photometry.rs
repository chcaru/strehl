//! M91 -- per-frame photometric normalisation: fit it, price it, and apply it
//! only if the measurement earns it.
//!
//! Pre-registered in `experiments/M91-photometry/PREREGISTRATION.md`, committed
//! at `065ab3b` with the C9 addendum at `cb706c9`, both **before** any arm here
//! produced a number. Every bar this example prints a verdict against is fixed
//! in that file; nothing is chosen after seeing data.
//!
//! # What this is, and what it deliberately is not
//!
//! It is a **second implementation of the merge's averaging stage**, not an edit
//! to it. `crates/strehl-core/src/merge.rs` is contended by five other live
//! milestones, so the correction is applied here, in this example's own
//! accumulators, against the shipped `FocusStats` / `Gate` / `Estimator`. That
//! costs a control: criterion C8 requires the identity case (`c = 1, o = 0`) to
//! reproduce `Estimator::green_mean` **bit-identically in f32**, including the
//! censoring rule, or every image number below is void.
//!
//! # The two orderings, and why one of them is a bug
//!
//! Fact 608: the photon-transfer model must be evaluated on each capture's own
//! **unscaled** DN, with variance carried through the photometric scale as
//! `c^2 * var`. [`fact608_weight`] is the only place a variance is formed and it
//! takes the unscaled luma; [`correct_dn`] is the only place a sample is scaled
//! and it never touches the noise model. The `naive` arm exists to price the
//! inversion, and it is the *only* place the scaled DN reaches a noise model.
//!
//! # The pedestal
//!
//! `Estimator::fold_inner` reads `row[2 * px + ox]`, the raw **black-inclusive**
//! sensor sample, and `Estimator::disagreement` subtracts black only at read
//! time. A gain fitted on black-subtracted signal must therefore be applied
//! about the pedestal, `black + c * (L - black)`, not about zero. Passing
//! `luma_offset = 0` scales the 512 DN pedestal too and over-corrects by
//! `1 + black / mean_signal`. Arm `chi2` runs both and that is criterion C9.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::CfaPlane;
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{DEFAULT_GATE, Estimator, FocusStats, Gate, regularise};
use strehl_core::noise::NoiseModel;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

// ---------------------------------------------------------------------------
// The correction. Two functions, deliberately tiny, because criterion C5
// breaks exactly one of them on purpose and the break has to be visible.
// ---------------------------------------------------------------------------

/// Apply the photometric correction to one **black-inclusive** raw DN sample.
///
/// Pivoted at the pedestal: a gain fitted on signal above black is a statement
/// about photons, and the pedestal is not photons. `black + c*(L - black) + o`.
///
/// This function never sees the noise model. That is fact 608's ordering, made
/// structural rather than remembered.
#[inline]
fn correct_dn(raw: f64, black: f64, c: f64, o: f64) -> f64 {
    black + c * (raw - black) + o
}

/// Inverse-variance weight for a corrected sample, per fact 608.
///
/// The model is evaluated on the frame's **own unscaled** signal, and the
/// variance is carried through the scale as `c^2 * var`. Feeding it the scaled
/// DN instead charges a frame's shot noise for photons it never collected.
///
/// `unscaled_signal_dn` is the frame's *expected* signal above black at this
/// pixel, not the sample itself. Using the sample makes the weight a function
/// of that sample's own noise, which biases the weighted mean downward
/// independently of anything photometric; the `W1s` accumulator exists to
/// price that mistake rather than to commit it.
#[inline]
fn fact608_weight(noise: &NoiseModel, unscaled_signal_dn: f64, c: f64) -> f64 {
    let s = f64::from(noise.green_luma_sigma(unscaled_signal_dn as f32));
    let v = c * c * s * s;
    if v > 0.0 { 1.0 / v } else { 0.0 }
}

// ---------------------------------------------------------------------------
// Small statistics helpers.
// ---------------------------------------------------------------------------

fn median(v: &mut [f64]) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    }
}

fn mean(v: &[f64]) -> f64 {
    if v.is_empty() {
        return f64::NAN;
    }
    v.iter().sum::<f64>() / v.len() as f64
}

fn sd(v: &[f64]) -> f64 {
    if v.len() < 2 {
        return 0.0;
    }
    let m = mean(v);
    (v.iter().map(|x| (x - m) * (x - m)).sum::<f64>() / (v.len() - 1) as f64).sqrt()
}

fn ptp(v: &[f64]) -> f64 {
    let lo = v.iter().cloned().fold(f64::INFINITY, f64::min);
    let hi = v.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    hi - lo
}

/// Deterministic pseudo-random ladder, seeded before the run.
///
/// SplitMix64. The values are affinely mapped so the min lands exactly on
/// `1 - ptp` and the max exactly on `1`, which makes the planted peak-to-peak
/// *exact* rather than approximately the requested value -- criterion C3a
/// compares a recovery against a known ladder and a sloppy ladder would blur it.
fn plant_ladder(n: usize, ptp_frac: f64, seed: u64) -> Vec<f64> {
    let mut s = seed.wrapping_add(0x9E37_79B9_7F4A_7C15);
    let mut raw = Vec::with_capacity(n);
    for _ in 0..n {
        s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = s;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^= z >> 31;
        raw.push((z >> 11) as f64 / (1u64 << 53) as f64);
    }
    if ptp_frac <= 0.0 {
        return vec![1.0; n];
    }
    let lo = raw.iter().cloned().fold(f64::INFINITY, f64::min);
    let hi = raw.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let span = (hi - lo).max(1e-12);
    raw.iter()
        .map(|r| 1.0 - ptp_frac * (hi - r) / span)
        .collect()
}

// ---------------------------------------------------------------------------
// Pass one pipeline, mirroring `merge_cmd.rs` exactly as `m60-disagreement.rs`
// does: same `green_luma_with_clip`, same `FocusField`, same `regularise`.
// ---------------------------------------------------------------------------

struct Pipeline {
    geom: PlaneGeometry,
    noise: NoiseModel,
    black: f32,
    field: FocusField,
    luma: Vec<f32>,
    clipped: Vec<bool>,
    box_scratch: Vec<f32>,
    reg: Vec<f32>,
}

impl Pipeline {
    fn field_for(&mut self, path: &Path) -> Result<strehl_raw::Frame> {
        let frame =
            strehl_raw::decode(path).with_context(|| format!("decoding {}", path.display()))?;
        if frame.geometry() != self.geom {
            bail!("{} has a different plane geometry", path.display());
        }
        green_luma_with_clip(
            &frame,
            self.black,
            CONTAINER_MAX_DN,
            &mut self.luma,
            &mut self.clipped,
        );
        self.field.compute(&self.luma, &self.noise);
        regularise(
            self.field.values(),
            self.geom,
            &mut self.box_scratch,
            &mut self.reg,
        );
        Ok(frame)
    }

    /// The ordering fact 608 forbids: scale the DN, *then* run the noise model
    /// on the scaled DN. Used only by the `naive` arm, to price the inversion.
    fn field_for_naive(&mut self, path: &Path, c: f32) -> Result<()> {
        let frame =
            strehl_raw::decode(path).with_context(|| format!("decoding {}", path.display()))?;
        green_luma_with_clip(
            &frame,
            self.black,
            CONTAINER_MAX_DN,
            &mut self.luma,
            &mut self.clipped,
        );
        for l in &mut self.luma {
            *l *= c;
        }
        self.field.compute(&self.luma, &self.noise);
        regularise(
            self.field.values(),
            self.geom,
            &mut self.box_scratch,
            &mut self.reg,
        );
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Block grid.
// ---------------------------------------------------------------------------

struct Blocks {
    bx: usize,
    by: usize,
    /// Block index for each plane pixel row (`py -> by`), precomputed.
    map: Vec<u32>,
    counts: Vec<f64>,
}

impl Blocks {
    fn new(geom: PlaneGeometry, size: usize) -> Self {
        let bx = geom.width.div_ceil(size);
        let by = geom.height.div_ceil(size);
        let mut map = vec![0u32; geom.pixels()];
        let mut counts = vec![0.0f64; bx * by];
        for py in 0..geom.height {
            for px in 0..geom.width {
                let b = (py / size) * bx + (px / size);
                map[py * geom.width + px] = b as u32;
                counts[b] += 1.0;
            }
        }
        Self {
            bx,
            by,
            map,
            counts,
        }
    }

    fn n(&self) -> usize {
        self.bx * self.by
    }

    /// Checkerboard parity of a block, for the held-out split of criterion C1.
    fn is_even(&self, b: usize) -> bool {
        let bxi = b % self.bx;
        let byi = b / self.bx;
        (bxi + byi).is_multiple_of(2)
    }

    fn means(&self, luma: &[f32]) -> Vec<f64> {
        let mut sums = vec![0.0f64; self.n()];
        for (i, &v) in luma.iter().enumerate() {
            sums[self.map[i] as usize] += f64::from(v);
        }
        for (s, c) in sums.iter_mut().zip(&self.counts) {
            *s /= *c;
        }
        sums
    }

    /// Per-block mean of `x * L`, the second moment C3a-hard's spatial ramp
    /// needs: the ramp is affine in `x`, so a planted block mean is an exact
    /// linear combination of this and [`Blocks::means`] and needs no re-decode.
    fn means_x(&self, luma: &[f32], width: usize) -> Vec<f64> {
        let mut sums = vec![0.0f64; self.n()];
        for (i, &v) in luma.iter().enumerate() {
            sums[self.map[i] as usize] += f64::from(v) * (i % width) as f64;
        }
        for (s, c) in sums.iter_mut().zip(&self.counts) {
            *s /= *c;
        }
        sums
    }
}

// ---------------------------------------------------------------------------
// Fitting forms F1..F6.
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq)]
enum Form {
    F1MeanRatio,
    F2LsOrigin,
    F3AffineLs,
    F4OffsetOnly,
    F5BlockMedian,
    F6BlockAffine,
}

impl Form {
    fn id(self) -> &'static str {
        match self {
            Form::F1MeanRatio => "F1-gain-mean-ratio",
            Form::F2LsOrigin => "F2-gain-ls-origin",
            Form::F3AffineLs => "F3-affine-ls",
            Form::F4OffsetOnly => "F4-offset-only",
            Form::F5BlockMedian => "F5-gain-block-median",
            Form::F6BlockAffine => "F6-affine-block-ls",
        }
    }
}

/// `(c_k, o_k)` for one frame, in the **signal** (black-subtracted) domain.
///
/// `sel` selects the blocks the parameters are fitted on: criterion C1's
/// held-out design fits on even-parity blocks only and scores on odd ones.
fn fit_one(
    form: Form,
    lk: &[f64],
    rb: &[f64],
    sel: &dyn Fn(usize) -> bool,
    grand: f64,
    counts: &[f64],
) -> (f64, f64) {
    let mut sl = 0.0;
    let mut sr = 0.0;
    let mut sll = 0.0;
    let mut slr = 0.0;
    let mut w = 0.0;
    let mut ratios = Vec::with_capacity(lk.len());
    for b in 0..lk.len() {
        if !sel(b) {
            continue;
        }
        let (l, r, cw) = (lk[b], rb[b], counts[b]);
        sl += l * cw;
        sr += r * cw;
        sll += l * l * cw;
        slr += l * r * cw;
        w += cw;
        if l > 1.0 {
            ratios.push(r / l);
        }
    }
    match form {
        // fact 225 / M28 s6: the mean over all pixels. The pixel-weighted block
        // mean *is* the whole-image mean, so this is that prescription exactly.
        Form::F1MeanRatio => ((sr / w) / (sl / w), 0.0),
        Form::F2LsOrigin => (slr / sll, 0.0),
        Form::F3AffineLs | Form::F6BlockAffine => {
            let n = w;
            let den = n * sll - sl * sl;
            if den.abs() < 1e-9 {
                return (1.0, 0.0);
            }
            let c = (n * slr - sl * sr) / den;
            let o = (sr - c * sl) / n;
            (c, o)
        }
        Form::F4OffsetOnly => (1.0, grand - sl / w),
        Form::F5BlockMedian => (median(&mut ratios), 0.0),
    }
}

/// Held-out residual RMS on the odd-parity blocks.
fn heldout_rms(
    fits: &[(f64, f64)],
    lkb: &[Vec<f64>],
    rb: &[f64],
    blocks: &Blocks,
    counts: &[f64],
) -> f64 {
    let mut se = 0.0;
    let mut w = 0.0;
    for (k, &(c, o)) in fits.iter().enumerate() {
        for b in 0..rb.len() {
            if blocks.is_even(b) {
                continue;
            }
            let pred = c * lkb[k][b] + o;
            let e = rb[b] - pred;
            se += e * e * counts[b];
            w += counts[b];
        }
    }
    (se / w).sqrt()
}

// ---------------------------------------------------------------------------
// My own averaging stage: the shipped one, mirrored, plus a corrected variant.
// ---------------------------------------------------------------------------

/// Bit-exact f32 mirror of `Estimator`'s sums for G1 and G2, so criterion C8
/// can be an *identity* and not an approximation.
struct Mirror {
    g1: Vec<f32>,
    g2: Vec<f32>,
    n: Vec<u16>,
    censor: Vec<u8>,
}

impl Mirror {
    fn new(px: usize) -> Self {
        Self {
            g1: vec![0.0; px],
            g2: vec![0.0; px],
            n: vec![0; px],
            censor: vec![0; px],
        }
    }
    /// Mirrors `Estimator::value` including the censoring override, then
    /// `Estimator::green_mean`'s `(G1 + G2) / 2`.
    #[inline]
    fn green(&self, i: usize) -> f32 {
        let lvl = f32::from(CONTAINER_MAX_DN);
        let v1 = if self.censor[i] & (1 << 1) != 0 {
            lvl
        } else {
            self.g1[i] / f32::from(self.n[i])
        };
        let v2 = if self.censor[i] & (1 << 3) != 0 {
            lvl
        } else {
            self.g2[i] / f32::from(self.n[i])
        };
        0.5 * (v1 + v2)
    }
}

/// A photometrically corrected accumulator, in f64.
///
/// f64 deliberately: the *deltas* criterion C3 measures are far below an f32
/// ULP at 3000 DN, and an f32 accumulator would confound the correction with
/// rounding. The identity control C8 is run against [`Mirror`], which is f32,
/// so the split is disclosed rather than silent.
struct Corrected {
    g1: Vec<f64>,
    g2: Vec<f64>,
    w: Vec<f64>,
}

impl Corrected {
    fn new(px: usize) -> Self {
        Self {
            g1: vec![0.0; px],
            g2: vec![0.0; px],
            w: vec![0.0; px],
        }
    }
    #[inline]
    fn green(&self, i: usize) -> f64 {
        if self.w[i] <= 0.0 {
            return f64::NAN;
        }
        0.5 * (self.g1[i] / self.w[i] + self.g2[i] / self.w[i])
    }
}

/// Everything the image arm accumulates in its single pass two.
struct ImageAccum {
    m0: Mirror,
    /// Corrected, equal weights (`W0`) -- the shipped merge's weighting.
    cw0: Corrected,
    /// Corrected, fact-608 inverse-variance weights (`W1`).
    cw1: Corrected,
    /// Corrected, fact-608 weights formed from the **sample** rather than the
    /// expected signal -- the self-weighting mistake, priced.
    cw1s: Corrected,
    /// Planted, uncorrected.
    pu: Option<Corrected>,
    /// Planted, corrected with the fit re-derived from the planted data.
    pc: Option<Corrected>,
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

#[allow(clippy::too_many_lines)]
fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let mut dir: Option<PathBuf> = None;
    let mut gate = DEFAULT_GATE;
    let mut limit: Option<usize> = None;
    let mut block = 32usize;
    let mut arms = String::from("fit");
    let mut plant_ptp = 0.117f64;
    let mut plant_ramp = 0.0f64;
    let mut seed = 91u64;
    let mut form_for_image = Form::F1MeanRatio;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--gate" => gate = args.next().context("--gate")?.parse()?,
            "--limit" => limit = Some(args.next().context("--limit")?.parse()?),
            "--block" => block = args.next().context("--block")?.parse()?,
            "--arms" => arms = args.next().context("--arms")?,
            "--plant" => plant_ptp = args.next().context("--plant")?.parse()?,
            "--ramp" => plant_ramp = args.next().context("--ramp")?.parse()?,
            "--seed" => seed = args.next().context("--seed")?.parse()?,
            "--image-form" => {
                let s = args.next().context("--image-form")?;
                form_for_image = match s.as_str() {
                    "F1" => Form::F1MeanRatio,
                    "F5" => Form::F5BlockMedian,
                    "F6" => Form::F6BlockAffine,
                    other => bail!("--image-form: F1, F5 or F6, not {other}"),
                };
            }
            other => dir = Some(PathBuf::from(other)),
        }
    }
    let dir = dir.context("usage: m91-photometry <DIR> [--gate G] [--limit N] [--arms ...]")?;
    let want = |a: &str| arms.split(',').any(|x| x.trim() == a);

    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    if paths.len() < 2 {
        bail!(
            "{} holds {} ARW files; need >= 2",
            dir.display(),
            paths.len()
        );
    }

    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom = first.geometry();
    let levels = first.levels;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let black = levels.black;
    let iso = first.iso;
    drop(first);
    let npx = geom.pixels();
    let nfr = paths.len();

    println!("== M91 photometry ==");
    println!("stack        : {}", dir.display());
    println!("frames       : {nfr}");
    println!("plane        : {} x {}", geom.width, geom.height);
    println!("iso / black  : {iso:?} / {black}");
    println!("gate         : {gate}");
    println!("block        : {block}");
    println!("arms         : {arms}");

    let mut pipe = Pipeline {
        geom,
        noise: noise.clone(),
        black,
        field: FocusField::new(geom),
        luma: vec![0.0; npx],
        clipped: vec![false; npx],
        box_scratch: vec![0.0; npx],
        reg: vec![0.0; npx],
    };
    let blocks = Blocks::new(geom, block);

    // ---------------- pass one -------------------------------------------
    let t0 = std::time::Instant::now();
    let mut stats = FocusStats::new(geom);
    let mut frame_mean = vec![0.0f64; nfr];
    let mut lkb: Vec<Vec<f64>> = Vec::with_capacity(nfr);
    let mut xlkb: Vec<Vec<f64>> = Vec::with_capacity(nfr);
    let mut frame_meanx = vec![0.0f64; nfr];
    let mut ref_sum = vec![0.0f64; npx];
    let mut reg_mean = vec![0.0f64; nfr];
    for (index, path) in paths.iter().enumerate() {
        let frame = pipe.field_for(path)?;
        stats.fold(index as u16, &pipe.reg)?;
        let mut acc = 0.0f64;
        for (r, &v) in ref_sum.iter_mut().zip(&pipe.luma) {
            acc += f64::from(v);
            *r += f64::from(v);
        }
        frame_mean[index] = acc / npx as f64;
        reg_mean[index] = pipe.reg.iter().map(|&v| f64::from(v)).sum::<f64>() / npx as f64;
        lkb.push(blocks.means(&pipe.luma));
        xlkb.push(blocks.means_x(&pipe.luma, geom.width));
        frame_meanx[index] = pipe
            .luma
            .iter()
            .enumerate()
            .map(|(i, &v)| f64::from(v) * (i % geom.width) as f64)
            .sum::<f64>()
            / npx as f64;
        drop(frame);
    }
    let inv_n = 1.0 / nfr as f64;
    for r in &mut ref_sum {
        *r *= inv_n;
    }
    let rb: Vec<f64> = (0..blocks.n())
        .map(|b| lkb.iter().map(|l| l[b]).sum::<f64>() * inv_n)
        .collect();
    let grand = mean(&frame_mean);
    let drift = 100.0 * ptp(&frame_mean) / grand;
    println!(
        "\n-- pass one -- {:.1}s   grand mean signal {grand:.2} DN   ptp {drift:.3}%",
        t0.elapsed().as_secs_f64()
    );
    println!(
        "blocks       : {} x {} = {} ({} even / {} odd)",
        blocks.bx,
        blocks.by,
        blocks.n(),
        (0..blocks.n()).filter(|&b| blocks.is_even(b)).count(),
        (0..blocks.n()).filter(|&b| !blocks.is_even(b)).count()
    );

    // ---------------- arm: fit  (C1, C1b, C2) -----------------------------
    let all = |_b: usize| true;
    let even = |b: usize| blocks.is_even(b);
    let forms = [
        Form::F1MeanRatio,
        Form::F2LsOrigin,
        Form::F3AffineLs,
        Form::F4OffsetOnly,
        Form::F5BlockMedian,
        Form::F6BlockAffine,
    ];
    // Full-data fits, used by every downstream arm.
    let mut full_fits: Vec<Vec<(f64, f64)>> = Vec::new();
    for f in forms {
        full_fits.push(
            (0..nfr)
                .map(|k| fit_one(f, &lkb[k], &rb, &all, grand, &blocks.counts))
                .collect(),
        );
    }

    if want("fit") {
        println!("\n== C1 / C1b : functional form, held-out on odd-parity blocks ==");
        println!(
            "{:<22} {:>10} {:>10} {:>10} {:>10} {:>8}",
            "form", "heldRMS", "c min", "c max", "|o| max", "C1b"
        );
        let mut heldout: Vec<(Form, f64)> = Vec::new();
        for f in forms {
            let fits: Vec<(f64, f64)> = (0..nfr)
                .map(|k| fit_one(f, &lkb[k], &rb, &even, grand, &blocks.counts))
                .collect();
            let rms = heldout_rms(&fits, &lkb, &rb, &blocks, &blocks.counts);
            let cmin = fits.iter().map(|x| x.0).fold(f64::INFINITY, f64::min);
            let cmax = fits.iter().map(|x| x.0).fold(f64::NEG_INFINITY, f64::max);
            let omax = fits.iter().map(|x| x.1.abs()).fold(0.0, f64::max);
            // C1b, verbatim from the pre-registration: |c-1| > 3*ptp, or
            // |o| > 0.02*grandmean, makes the fit VOID.
            let cbad = fits
                .iter()
                .any(|x| (x.0 - 1.0).abs() > 3.0 * (drift / 100.0));
            let obad = omax > 0.02 * grand;
            let verdict = match (cbad, obad) {
                (false, false) => "ok",
                (true, false) => "VOID-c",
                (false, true) => "VOID-o",
                (true, true) => "VOID-co",
            };
            println!(
                "{:<22} {rms:>10.4} {cmin:>10.5} {cmax:>10.5} {omax:>10.4} {verdict:>8}",
                f.id()
            );
            heldout.push((f, rms));
        }
        let r5 = heldout
            .iter()
            .find(|(f, _)| *f == Form::F5BlockMedian)
            .unwrap()
            .1;
        let r6 = heldout
            .iter()
            .find(|(f, _)| *f == Form::F6BlockAffine)
            .unwrap()
            .1;
        let gain = 100.0 * (1.0 - r6 / r5);
        println!("C1: F6 vs F5 held-out RMS reduction = {gain:.4}%  (bar: >= 5.0%)");
        println!("C1: {}", if gain >= 5.0 { "MET" } else { "FAILS" });
        // Also the pixel-domain pair, so the answer is not an artefact of the
        // block grid: F2 (gain, LS through origin) vs F3 (affine LS).
        let r2 = heldout
            .iter()
            .find(|(f, _)| *f == Form::F2LsOrigin)
            .unwrap()
            .1;
        let r3 = heldout
            .iter()
            .find(|(f, _)| *f == Form::F3AffineLs)
            .unwrap()
            .1;
        println!(
            "C1-aux: F3 vs F2 held-out RMS reduction = {:.4}%",
            100.0 * (1.0 - r3 / r2)
        );
        let r1 = heldout
            .iter()
            .find(|(f, _)| *f == Form::F1MeanRatio)
            .unwrap()
            .1;
        let r4 = heldout
            .iter()
            .find(|(f, _)| *f == Form::F4OffsetOnly)
            .unwrap()
            .1;
        println!("C1-aux: F1 held-out RMS {r1:.4}   F4 held-out RMS {r4:.4}");

        // -------- C2: spatial uniformity ---------------------------------
        let uniformity = |ladder: &[f64]| -> (f64, f64, f64) {
            let mut med_per_frame = Vec::with_capacity(nfr);
            let mut sd_per_frame = Vec::with_capacity(nfr);
            for (k, lk) in lkb.iter().enumerate() {
                let g = ladder[k];
                let mut r = Vec::with_capacity(blocks.n());
                for b in 0..blocks.n() {
                    let l = lk[b] * g;
                    if l > 1.0 {
                        // Reference must be planted too, or the ratio measures
                        // the plant against an unplanted world.
                        let rr: f64 = (0..nfr).map(|j| lkb[j][b] * ladder[j]).sum::<f64>() * inv_n;
                        r.push(rr / l);
                    }
                }
                med_per_frame.push(median(&mut r.clone()));
                sd_per_frame.push(sd(&r));
            }
            let between = sd(&med_per_frame);
            let within = median(&mut sd_per_frame.clone());
            (between / within, between, within)
        };
        let flat = vec![1.0; nfr];
        let (u, b_sd, w_sd) = uniformity(&flat);
        println!("\n== C2 : spatial uniformity ==");
        println!("U = sd_k(median_b r) / median_k(sd_b r) = {u:.4}   ({b_sd:.6} / {w_sd:.6})");
        let verdict = if u >= 3.0 {
            "GLOBAL (>= 3.0)"
        } else if u < 1.5 {
            "NOT SPATIALLY COHERENT (< 1.5)"
        } else {
            "EQUIVOCAL [1.5, 3.0) -- reported as equivocal, not rounded"
        };
        println!("C2: {verdict}");
        // C2-power (mandatory): a statistic that cannot be made to read
        // "uniform" has not measured non-uniformity.
        let ladder = plant_ladder(nfr, 0.117, seed);
        let (up, _, _) = uniformity(&ladder);
        println!(
            "C2-power: planted uniform ladder ptp 11.7% -> U = {up:.4}  (bar: >= 3.0)  {}",
            if up >= 3.0 { "PASS" } else { "FAIL" }
        );

        // -------- C10: how much of the drift is a single global gain? ----
        // `y_{k,b} = R_b / L_{k,b}` normalised so mean_k y = 1 per block, then
        // the fraction of its variance explained by one ladder shared by every
        // block. `mult` is an optional per-frame factor applied to the data
        // before the decomposition, which is how the power and null arms are
        // built out of the same code path.
        // `b` indexes the inner dimension of `lkb[k][b]`, not `lkb` itself.
        #[allow(clippy::needless_range_loop)]
        let explained = |mult: &[f64]| -> f64 {
            let mut num = 0.0f64;
            let mut den = 0.0f64;
            let mut y: Vec<Vec<f64>> = Vec::with_capacity(blocks.n());
            let mut keep: Vec<usize> = Vec::new();
            for b in 0..blocks.n() {
                let col: Vec<f64> = (0..nfr).map(|k| lkb[k][b] * mult[k]).collect();
                if col.iter().any(|v| *v <= 1.0) {
                    continue;
                }
                let m = mean(&col);
                y.push(col.iter().map(|v| m / v).collect());
                keep.push(b);
            }
            if y.is_empty() {
                return f64::NAN;
            }
            // The single global ladder: the mean over blocks, per frame.
            let g: Vec<f64> = (0..nfr)
                .map(|k| y.iter().map(|c| c[k]).sum::<f64>() / y.len() as f64)
                .collect();
            for col in &y {
                for (k, v) in col.iter().enumerate() {
                    num += (v - g[k]) * (v - g[k]);
                    den += (v - 1.0) * (v - 1.0);
                }
            }
            1.0 - num / den
        };
        let ones = vec![1.0; nfr];
        let ev = explained(&ones);
        // Power: a ladder that is uniform by construction, planted on top.
        let ev_planted = explained(&ladder);
        // Null: the real drift divided out, leaving only spatial structure.
        let flat_mult: Vec<f64> = (0..nfr).map(|k| grand / frame_mean[k]).collect();
        let ev_null = explained(&flat_mult);
        println!("\n== C10 : is the drift a single global gain? ==");
        println!("EV = {ev:.4}   (>= 0.50 global, < 0.20 spatial, between = mixed)");
        println!(
            "C10: {}",
            if ev >= 0.50 {
                "PREDOMINANTLY GLOBAL"
            } else if ev < 0.20 {
                "PREDOMINANTLY SPATIAL -- a per-frame scalar is the wrong form"
            } else {
                "MIXED -- reported as mixed, not rounded"
            }
        );
        println!(
            "C10-power: planted uniform ptp 11.7% -> EV = {ev_planted:.4}  (bar: > 0.90)  {}   \
             deflation floor 1-EV = {:.4}",
            if ev_planted > 0.90 { "PASS" } else { "FAIL" },
            1.0 - ev_planted
        );
        println!("C10-null: real drift divided out -> EV = {ev_null:.4}  (must fall toward 0)");
    }

    // ---------------- arm: naive  (C7 / P-b) ------------------------------
    if want("naive") {
        println!("\n== C7 : the price of inverting fact 608's ordering ==");
        let base_best = stats.best_index().to_vec();
        let c1 = &full_fits[0];
        let mut naive_stats = FocusStats::new(geom);
        let mut ratios = Vec::with_capacity(nfr);
        for (index, path) in paths.iter().enumerate() {
            pipe.field_for_naive(path, c1[index].0 as f32)?;
            let m = pipe.reg.iter().map(|&v| f64::from(v)).sum::<f64>() / npx as f64;
            ratios.push(m / reg_mean[index]);
            naive_stats.fold(index as u16, &pipe.reg)?;
        }
        let pred: Vec<f64> = c1.iter().map(|x| x.0.sqrt()).collect();
        let err: Vec<f64> = ratios
            .iter()
            .zip(&pred)
            .map(|(r, p)| (r / p - 1.0).abs())
            .collect();
        let worst = err.iter().cloned().fold(0.0, f64::max);
        println!(
            "response ratio vs sqrt(c): mean measured {:.6}, mean predicted {:.6}, worst frame error {:.4}%",
            mean(&ratios),
            mean(&pred),
            100.0 * worst
        );
        println!(
            "P-b (bar 10%): {}",
            if worst <= 0.10 { "MET" } else { "FAILS" }
        );
        let changed = base_best
            .iter()
            .zip(naive_stats.best_index())
            .filter(|(a, b)| a != b)
            .count();
        println!(
            "winner changes under the naive ordering: {} / {} = {:.4}%",
            changed,
            npx,
            100.0 * changed as f64 / npx as f64
        );
        let mut e_base = Estimator::new(&stats, Gate::new(gate));
        let mut e_naive = Estimator::new(&naive_stats, Gate::new(gate));
        for (index, path) in paths.iter().enumerate() {
            let frame = pipe.field_for(path)?;
            e_base.fold_censored(index as u16, &frame, &pipe.reg, CONTAINER_MAX_DN)?;
            pipe.field_for_naive(path, c1[index].0 as f32)?;
            e_naive.fold_censored(index as u16, &frame, &pipe.reg, CONTAINER_MAX_DN)?;
        }
        println!(
            "mean n_eff: fact-608 ordering {:.4}   naive ordering {:.4}   delta {:+.4}",
            e_base.mean_n_eff(),
            e_naive.mean_n_eff(),
            e_naive.mean_n_eff() - e_base.mean_n_eff()
        );
    }

    // ---------------- arm: chi2  (C6, C9) ---------------------------------
    if want("chi2") {
        println!("\n== C6 / C9 : merge-time disagreement, six photometric arms ==");
        let names = [
            "A0-raw",
            "A1b-m60-gain-zero-pivot",
            "C9-gain-black-pivot",
            "C9-blockmedian-black-pivot",
            "A4-affine-ls-black-pivot",
            "A4b-offset-only",
        ];
        let mut ests: Vec<Estimator> = (0..names.len())
            .map(|_| {
                let mut e = Estimator::new(&stats, Gate::new(gate));
                e.track_disagreement();
                e
            })
            .collect();
        println!(
            "estimator memory: {:.2} GB total",
            ests.iter().map(Estimator::allocated_bytes).sum::<usize>() as f64 / 1e9
        );
        let t = std::time::Instant::now();
        let mut a4_slope: Vec<f64> = Vec::with_capacity(nfr);
        let mut a4_off: Vec<f64> = Vec::with_capacity(nfr);
        for (index, path) in paths.iter().enumerate() {
            let frame = pipe.field_for(path)?;
            // M60's A4: per-pixel LS of the all-frame mean on this frame, in
            // the signal domain, fitted on the fly exactly as it does.
            let (mut sl, mut sr, mut sll, mut slr) = (0.0f64, 0.0f64, 0.0f64, 0.0f64);
            for (&l, &r) in pipe.luma.iter().zip(&ref_sum) {
                let l = f64::from(l);
                sl += l;
                sr += r;
                sll += l * l;
                slr += l * r;
            }
            let n = npx as f64;
            let den = n * sll - sl * sl;
            let (a_s, a_o) = if den.abs() < 1e-9 {
                (1.0, 0.0)
            } else {
                let s = (n * slr - sl * sr) / den;
                (s, (sr - s * sl) / n)
            };
            let bk = f64::from(black);
            a4_slope.push(a_s);
            a4_off.push(a_o);
            let c1 = full_fits[0][index].0;
            let c5 = full_fits[4][index].0;
            let off4 = full_fits[3][index].1;
            let params: [(f32, f32); 6] = [
                (1.0, 0.0),
                (c1 as f32, 0.0),
                (c1 as f32, (bk * (1.0 - c1)) as f32),
                (c5 as f32, (bk * (1.0 - c5)) as f32),
                (a_s as f32, (a_o + bk * (1.0 - a_s)) as f32),
                (1.0, off4 as f32),
            ];
            for (e, (s, o)) in ests.iter_mut().zip(params) {
                e.fold_censored_probing_photometry(
                    index as u16,
                    &frame,
                    &pipe.reg,
                    CONTAINER_MAX_DN,
                    s,
                    o,
                )?;
            }
        }
        println!("pass two: {:.1}s", t.elapsed().as_secs_f64());
        let exposure = ests[0].disagreement_exposure();
        let mut means = Vec::new();
        for (name, e) in names.iter().zip(&ests) {
            let mut acc = 0.0f64;
            let mut cnt = 0usize;
            for i in 0..npx {
                if let Some(d) = e.disagreement(&noise, i, black) {
                    acc += d;
                    cnt += 1;
                }
            }
            let m = acc / cnt as f64;
            means.push(m);
            let base = means[0];
            println!(
                "{name:<28} mean chi2 {m:>9.4}   reduction {:>8.2}%   excess reduction {:>8.2}%",
                100.0 * (1.0 - m / base),
                100.0 * (1.0 - (m - 1.0) / (base - 1.0))
            );
        }
        println!(
            "disagreement exposure (n_eff >= 2): {:.2}% of pixels",
            100.0 * exposure
        );
        let over = 1.0 + f64::from(black) / grand;
        println!(
            "C9: predicted over-correction factor 1 + black/signal = {over:.3}x;  \
             zero-pivot {:.2}% vs black-pivot {:.2}% reduction, gap {:.2} pp",
            100.0 * (1.0 - means[1] / means[0]),
            100.0 * (1.0 - means[2] / means[0]),
            100.0 * (means[1] - means[2]) / means[0]
        );
        // C1b applied to the on-the-fly per-pixel affine fit, which the `fit`
        // arm never sees. M60b G6 killed exactly this arm on `foam` and the
        // guard has to be run here or the trap is repeated.
        let smin = a4_slope.iter().cloned().fold(f64::INFINITY, f64::min);
        let smax = a4_slope.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let omax = a4_off.iter().map(|o| o.abs()).fold(0.0, f64::max);
        let cbad = (smin - 1.0).abs().max((smax - 1.0).abs()) > 3.0 * (drift / 100.0);
        let obad = omax > 0.02 * grand;
        let ratio = means[4] / means[0];
        println!(
            "A4 fit: slope {smin:.5}..{smax:.5}, |o| max {omax:.4} (2% of grand = {:.4});  \
             C1b -> {}",
            0.02 * grand,
            if cbad || obad { "VOID" } else { "admissible" }
        );
        println!(
            "A4 G6 degeneracy check: chi2 ratio {ratio:.5}, sqrt {:.5}; inside fitted slope range? {} / {}",
            ratio.sqrt(),
            if ratio >= smin && ratio <= smax {
                "yes"
            } else {
                "no"
            },
            if ratio.sqrt() >= smin && ratio.sqrt() <= smax {
                "yes"
            } else {
                "no"
            }
        );
        println!(
            "A4 rule 35: its (s,o) minimise sum_i (R_i - s*L_i - o)^2, and mean chi2 is the \
             variance of exactly that residual. Subject and object are the same quantity."
        );
    }

    // ---------------- arms: image / plant  (C3a, C3b, C4, C8) -------------
    if want("image") || want("plant") {
        let planting = want("plant");
        println!("\n== C3 / C8 : the merged image ==");
        let ladder = if planting {
            plant_ladder(nfr, plant_ptp, seed)
        } else {
            vec![1.0; nfr]
        };
        if planting {
            println!(
                "plant ladder : ptp {:.4}%  min {:.6} max {:.6} seed {seed}  ramp a = {plant_ramp}",
                100.0 * ptp(&ladder),
                ladder.iter().cloned().fold(f64::INFINITY, f64::min),
                ladder.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
            );
        }
        // C3a-hard's ramp `g_k(x) = 1 + (gamma_k - 1) * (1 + a*(2x/W - 1))` is
        // affine in x, so `A_k * L + B_k * (x*L)` is the exact planted mean of
        // any pixel set: the fit on planted data needs no second decode.
        let wf = geom.width as f64;
        let ramp_a: Vec<f64> = ladder
            .iter()
            .map(|g| 1.0 + (g - 1.0) * (1.0 - plant_ramp))
            .collect();
        let ramp_b: Vec<f64> = ladder
            .iter()
            .map(|g| (g - 1.0) * plant_ramp * 2.0 / wf)
            .collect();
        let planted_lkb: Vec<Vec<f64>> = (0..nfr)
            .map(|k| {
                (0..blocks.n())
                    .map(|b| ramp_a[k] * lkb[k][b] + ramp_b[k] * xlkb[k][b])
                    .collect()
            })
            .collect();
        let planted_rb: Vec<f64> = (0..blocks.n())
            .map(|b| (0..nfr).map(|k| planted_lkb[k][b]).sum::<f64>() * inv_n)
            .collect();
        let planted_grand = mean(
            &(0..nfr)
                .map(|k| ramp_a[k] * frame_mean[k] + ramp_b[k] * frame_meanx[k])
                .collect::<Vec<_>>(),
        );
        let planted_fit: Vec<(f64, f64)> = (0..nfr)
            .map(|k| {
                fit_one(
                    form_for_image,
                    &planted_lkb[k],
                    &planted_rb,
                    &all,
                    planted_grand,
                    &blocks.counts,
                )
            })
            .collect();
        let form_index = forms.iter().position(|f| *f == form_for_image).unwrap();
        let clean_fit = &full_fits[form_index];
        println!("image form   : {}", form_for_image.id());
        if planting {
            // Recovery ratio of the fit itself. For F1 with `--ramp 0` this is
            // arithmetically forced (addendum 5c) and is reported as a plumbing
            // control, never as evidence. `g_eff` is the whole-image-mean gain
            // the plant actually applied, which equals gamma exactly at a = 0.
            let g_eff: Vec<f64> = (0..nfr)
                .map(|k| (ramp_a[k] * frame_mean[k] + ramp_b[k] * frame_meanx[k]) / frame_mean[k])
                .collect();
            let prod: Vec<f64> = (0..nfr).map(|k| planted_fit[k].0 * g_eff[k]).collect();
            let m = mean(&prod);
            let norm: Vec<f64> = prod.iter().map(|p| p / m).collect();
            println!(
                "fit recovery : mean(c_hat*g_eff)/mean = 1.000000, sd {:.3e}, ptp {:.3e}",
                sd(&norm),
                ptp(&norm)
            );
        }

        let mut acc = ImageAccum {
            m0: Mirror::new(npx),
            cw0: Corrected::new(npx),
            cw1: Corrected::new(npx),
            cw1s: Corrected::new(npx),
            pu: planting.then(|| Corrected::new(npx)),
            pc: planting.then(|| Corrected::new(npx)),
        };
        let mut e_ref = Estimator::new(&stats, Gate::new(gate));
        let gate_obj = Gate::new(gate);
        let bk = f64::from(black);
        let (g1x, g1y) = CfaPlane::G1.rggb_offset();
        let (g2x, g2y) = CfaPlane::G2.rggb_offset();
        let best_focus = stats.best_focus().to_vec();
        let best_index = stats.best_index().to_vec();

        let t = std::time::Instant::now();
        for (index, path) in paths.iter().enumerate() {
            let frame = pipe.field_for(path)?;
            e_ref.fold_censored(index as u16, &frame, &pipe.reg, CONTAINER_MAX_DN)?;
            let (c, o) = clean_fit[index];
            let (pc_c, pc_o) = planted_fit[index];
            for py in 0..geom.height {
                let (row0, row1) = frame.quad_rows(py);
                let r1 = if g1y == 0 { row0 } else { row1 };
                let r2 = if g2y == 0 { row0 } else { row1 };
                let base = py * geom.width;
                for px in 0..geom.width {
                    let i = base + px;
                    let winner = best_index[i] == index as u16;
                    if !(winner || gate_obj.admits(pipe.reg[i], best_focus[i])) {
                        continue;
                    }
                    let v1 = r1[2 * px + g1x];
                    let v2 = r2[2 * px + g2x];
                    if winner {
                        if v1 >= CONTAINER_MAX_DN {
                            acc.m0.censor[i] |= 1 << 1;
                        }
                        if v2 >= CONTAINER_MAX_DN {
                            acc.m0.censor[i] |= 1 << 3;
                        }
                    }
                    // Exactly `Estimator::fold_inner`: f32, frame order.
                    acc.m0.g1[i] += f32::from(v1);
                    acc.m0.g2[i] += f32::from(v2);
                    acc.m0.n[i] += 1;

                    let d1 = f64::from(v1);
                    let d2 = f64::from(v2);
                    acc.cw0.g1[i] += correct_dn(d1, bk, c, o);
                    acc.cw0.g2[i] += correct_dn(d2, bk, c, o);
                    acc.cw0.w[i] += 1.0;
                    // fact 608: the model sees the frame's own UNSCALED signal.
                    // `ref_sum[i] / c` is this frame's expected unscaled signal
                    // at this pixel; the sample itself is used only by `cw1s`,
                    // which exists to show what that costs.
                    let w = fact608_weight(&noise, ref_sum[i] / c, c);
                    acc.cw1.g1[i] += w * correct_dn(d1, bk, c, o);
                    acc.cw1.g2[i] += w * correct_dn(d2, bk, c, o);
                    acc.cw1.w[i] += w;
                    let ws = fact608_weight(&noise, 0.5 * (d1 + d2) - bk, c);
                    acc.cw1s.g1[i] += ws * correct_dn(d1, bk, c, o);
                    acc.cw1s.g2[i] += ws * correct_dn(d2, bk, c, o);
                    acc.cw1s.w[i] += ws;

                    if let (Some(pu), Some(pcx)) = (acc.pu.as_mut(), acc.pc.as_mut()) {
                        // The plant is applied to signal above black, in f64,
                        // so it adds no quantisation noise of its own. With
                        // `--ramp a` the gain varies across x, which is the
                        // disturbance a single global gain cannot absorb.
                        let g = ramp_a[index] + ramp_b[index] * px as f64;
                        let p1 = bk + (d1 - bk) * g;
                        let p2 = bk + (d2 - bk) * g;
                        pu.g1[i] += p1;
                        pu.g2[i] += p2;
                        pu.w[i] += 1.0;
                        pcx.g1[i] += correct_dn(p1, bk, pc_c, pc_o);
                        pcx.g2[i] += correct_dn(p2, bk, pc_c, pc_o);
                        pcx.w[i] += 1.0;
                    }
                }
            }
        }
        println!("pass two: {:.1}s", t.elapsed().as_secs_f64());

        // -------- C8: the identity control -------------------------------
        let mut mismatch = 0usize;
        let mut worst = 0.0f32;
        for i in 0..npx {
            let a = acc.m0.green(i);
            let b = e_ref.green_mean(i);
            if a.to_bits() != b.to_bits() {
                mismatch += 1;
                worst = worst.max((a - b).abs());
            }
        }
        println!(
            "C8 identity vs Estimator::green_mean: {mismatch} / {npx} bits differ (worst {worst:.6} DN) -> {}",
            if mismatch == 0 {
                "PASS"
            } else {
                "FAIL -- every image number below is VOID"
            }
        );
        let censored = (0..npx).filter(|&i| acc.m0.censor[i] != 0).count();
        println!(
            "censored pixels excluded from image statistics: {censored} ({:.4}%)",
            100.0 * censored as f64 / npx as f64
        );

        // -------- delta statistics, global scale removed -----------------
        let valid: Vec<usize> = (0..npx).filter(|&i| acc.m0.censor[i] == 0).collect();
        let m0sig: Vec<f64> = valid
            .iter()
            .map(|&i| f64::from(acc.m0.green(i)) - bk)
            .collect();
        let mu0 = mean(&m0sig);
        let sig_pred: Vec<f64> = valid
            .iter()
            .map(|&i| f64::from(e_ref.predicted_sigma(&noise, i, black)))
            .collect();
        println!(
            "reference merge: mean signal {mu0:.2} DN, mean predicted sigma {:.4} DN, mean n_eff {:.4}",
            mean(&sig_pred),
            e_ref.mean_n_eff()
        );
        let sig_of =
            |c: &Corrected| -> Vec<f64> { valid.iter().map(|&i| c.green(i) - bk).collect() };
        // Global scale removed before anything is counted: a uniform gain on
        // the output is a re-exposure, not a picture defect. What survives is
        // the winner-index map printed into the image as brightness mottling.
        let delta_stats = |other: &[f64], reference: &[f64], label: &str| -> (f64, f64) {
            let mu_r = mean(reference);
            let k = mu_r / mean(other);
            let mut se = 0.0;
            let mut over = 0usize;
            let mut amax = 0.0f64;
            for j in 0..valid.len() {
                let d = other[j] * k - reference[j];
                se += d * d;
                amax = amax.max(d.abs());
                if d.abs() > sig_pred[j] {
                    over += 1;
                }
            }
            let rms = (se / valid.len() as f64).sqrt();
            let f1 = 100.0 * over as f64 / valid.len() as f64;
            println!(
                "{label:<30} global scale {k:.6}   residual RMS {rms:.5} DN   max |d| {amax:.4}   f1sig {f1:.4}%"
            );
            (rms, f1)
        };
        println!("\n-- C3b : corrected minus uncorrected, real data --");
        let mc_sig = sig_of(&acc.cw0);
        let (_, f1_w0) = delta_stats(&mc_sig, &m0sig, "corrected W0 (equal)");
        delta_stats(&sig_of(&acc.cw1), &m0sig, "corrected W1 (fact 608)");
        delta_stats(&sig_of(&acc.cw1s), &m0sig, "corrected W1s (self-weighted)");
        println!(
            "C3b: f1sig(W0) = {f1_w0:.4}%  (bar: >= 1.0% on >= 2 of 6 stacks) -> {}",
            if f1_w0 >= 1.0 {
                "meets bar here"
            } else {
                "below bar here"
            }
        );

        if planting {
            let hard = plant_ramp != 0.0;
            println!(
                "\n-- {} --",
                if hard {
                    "C3a-hard : planted recovery, spatially non-uniform ramp"
                } else {
                    "C3a : planted recovery, spatially uniform (plumbing control, see addendum 5c)"
                }
            );
            // The reference for the *corrected* planted merge is the corrected
            // *unplanted* merge, not M0. The placebo run found this: with
            // gamma == 1 the old comparison reported the native correction as
            // if it were plant damage, reproducing C3b's number exactly.
            let pu = sig_of(acc.pu.as_ref().unwrap());
            let pc = sig_of(acc.pc.as_ref().unwrap());
            let (e_unc, f1_unc) = delta_stats(&pu, &m0sig, "planted uncorrected vs M0");
            let (e_cor, _) = delta_stats(&pc, &mc_sig, "planted corrected vs corrected");
            let r = 1.0 - e_cor / e_unc;
            let label = if hard { "C3a-hard" } else { "C3a" };
            println!("{label}: recovery R = 1 - E_corr/E_uncorr = {r:.6}   (bar: >= 0.50)");
            println!(
                "{label}: {}",
                if r >= 0.50 {
                    "MET"
                } else if r > 0.0 {
                    "FAILS (positive but under bar)"
                } else {
                    "FAILS (correction makes it worse)"
                }
            );
            println!(
                "{label}: f1sig of the UNCORRECTED plant = {f1_unc:.4}%  \
                 -- the materiality of a {:.2}% drift with ramp a = {plant_ramp}",
                100.0 * ptp(&ladder)
            );
            if !hard {
                println!("{label}: R = 1 here is algebra, not evidence (rule 35). Its job is C5.");
            }
            if plant_ptp == 0.0 {
                println!(
                    "C3a-placebo (gamma == 1): plant machinery no-op E_uncorr {e_unc:.8} DN (bar < 0.01) -> {};  \
                     corrected-arm cross-check E_corr {e_cor:.8} DN (bar < 0.01) -> {}",
                    if e_unc < 0.01 { "PASS" } else { "FAIL" },
                    if e_cor < 0.01 { "PASS" } else { "FAIL" }
                );
            }
        }
    }

    Ok(())
}
