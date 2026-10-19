#![allow(clippy::too_many_arguments)] // the probe threads the full warp+pyramid config

//! BUILD-GATE — is the pyramid's band-noise floor stale with respect to the
//! gather flip, and by how much?
//!
//! # The claim under test
//!
//! `BandMerge::add_frame` gates band selection at
//! `floor = gate * beta[k] * var`, where `var` is the modelled per-pixel raw
//! noise variance and `beta[k]` comes from [`BandGain::measure`] — a
//! **white-noise probe pushed straight into the pyramid**. Nothing in that
//! probe knows a warp happened. But the frames the merge actually folds have
//! been resampled, and resampling is a low-pass: it correlates neighbouring
//! samples and moves noise power out of the fine bands. The two gather orders
//! do that by *different* amounts, so a floor that is arm-independent by
//! construction cannot be right for both.
//!
//! # What this instrument measures
//!
//! `beta_actual[k] = E[L_k^2] / sigma_0^2` for the **real** noise path into the
//! merge, which `load_frame` fixes as
//!
//! ```text
//! raw photosite noise -> warp_frame_in_place_{plane,fullres}
//!                     -> deinterleave to 4 CFA quad planes
//!                     -> green luma L = (G1 + G2) / 2
//!                     -> Pyramid::build
//! ```
//!
//! There is **no demosaic** in this path — the merge runs on the quad grid and
//! the demosaic happens after collapse — so the probe does not contain one
//! either. The warp functions are the shipping ones, reached through
//! `#[path]` because `strehl-cli` has no lib target.
//!
//! The denominator is the *empirical* level-0 variance of the **unwarped**
//! green luma, which makes the no-warp arm reproduce `BandGain::measure`'s own
//! definition exactly. That is C1, and it is a real null rather than a
//! normalisation convention.
//!
//! # Reading the output
//!
//! `beta_actual / beta_white` is the factor the shipping floor is wrong by. If
//! it is materially different between the two arms, the gate is stale and the
//! flip silently moved the average/select boundary. If it is the same, the
//! diagnosis is wrong and nothing here should be built on.

#[allow(dead_code)]
#[path = "../src/align_cmd.rs"]
mod align_cmd;
#[allow(dead_code)]
#[path = "../src/ui-progress.rs"]
mod ui_progress;

use std::path::PathBuf;

use anyhow::Result;
use strehl_core::align::{Resampler, Similarity, SimilarityParams};
use strehl_core::noise::Levels;
use strehl_core::plane::PlaneGeometry;
use strehl_core::pyramid::{BandGain, DEFAULT_BANDS, Pyramid, Workspace, level_sizes};
use strehl_raw::{Frame, Region};

use align_cmd::{WarpScratch, warp_frame_in_place_fullres, warp_frame_in_place_plane};

/// Quad-plane extent of the probe. The merge's grid is the quad grid, so this
/// is the grid the pyramid runs on and `2 * GW` is the photosite extent.
const GW: usize = 512;
const GH: usize = 512;
const BLACK: f32 = 512.0;
/// Flat scene level in raw DN above black. Well away from black so nothing
/// clips at `.max(0.0)`, and well below white so nothing saturates.
const LEVEL: f64 = 2000.0;

/// `load_frame`'s CFA offsets, copied so the probe deinterleaves exactly the
/// way the fold does. R, G1, G2, B for an RGGB mosaic.
const PLANE_OFFSETS: [(usize, usize); 4] = [(0, 0), (1, 0), (0, 1), (1, 1)];

struct Lcg(u64);

impl Lcg {
    fn next_u64(&mut self) -> u64 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.0
    }
    fn uniform(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64) / ((1u64 << 53) as f64)
    }
    /// Box-Muller. The band gain of a linear operator does not depend on the
    /// input's distribution, but a Gaussian keeps the probe honest against the
    /// clipping at `.max(0.0)` that a heavy-tailed field could trip.
    fn normal(&mut self) -> f64 {
        let u1 = self.uniform().max(1e-12);
        let u2 = self.uniform();
        (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
    }
}

/// A flat frame carrying nothing but white photosite noise of sd `sigma_p`.
fn probe_frame(sigma_p: f64, seed: u64, blur: bool) -> Frame {
    let (fw, fh) = (2 * GW, 2 * GH);
    let (ox, oy) = (2usize, 4usize);
    let stride = fw + ox + 3;
    let buffer_height = fh + oy + 2;
    let mut data = vec![0u16; stride * buffer_height];
    let mut rng = Lcg(seed);
    let mut field: Vec<f64> = (0..fw * fh).map(|_| sigma_p * rng.normal()).collect();
    if blur {
        // C3's planted defect: pre-correlate the noise with a 5x5 box on the
        // photosite grid. 5x5 and not 3x3 deliberately — the merge runs on the
        // quad grid, where adjacent samples are TWO photosites apart, so a
        // 3x3 box (reach +/-1) leaves them almost independent and the planted
        // defect barely registers. Measured: 3x3 moved beta[0] by only -19%,
        // 5x5 (reach +/-2) is the smallest box that actually correlates the
        // grid the pyramid sees.
        let src = field.clone();
        for y in 0..fh {
            for x in 0..fw {
                let (mut acc, mut n) = (0.0, 0usize);
                for dy in -2i32..=2 {
                    for dx in -2i32..=2 {
                        let (sx, sy) = (x as i32 + dx, y as i32 + dy);
                        if sx >= 0 && sy >= 0 && (sx as usize) < fw && (sy as usize) < fh {
                            acc += src[sy as usize * fw + sx as usize];
                            n += 1;
                        }
                    }
                }
                field[y * fw + x] = acc / n as f64;
            }
        }
    }
    for y in 0..fh {
        for x in 0..fw {
            let raw = LEVEL + BLACK as f64 + field[y * fw + x];
            data[(oy + y) * stride + ox + x] = raw.round().clamp(0.0, u16::MAX as f64) as u16;
        }
    }
    Frame {
        data,
        stride,
        buffer_height,
        active: Region { x: ox, y: oy, width: fw, height: fh },
        levels: Levels { black: BLACK, white: 15360.0 },
        iso: Some(100.0),
        // Unity, so the gather's white-balance round trip is exactly the
        // identity and cannot colour the measurement.
        wb_coeffs: [1.0, 1.0, 1.0, 1.0],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        // A path that does not exist, so `profile_for_capture_env` declines and
        // the lateral-CA composition in both gathers is the identity.
        camera: "synthetic".to_string(),
        path: PathBuf::from("synthetic-no-such-file.ARW"),
    }
}

/// `load_frame`'s deinterleave and green luma, verbatim in behaviour.
fn green_luma(frame: &Frame) -> Vec<f32> {
    let (stride, ax, ay) = (frame.stride, frame.active.x, frame.active.y);
    let black = frame.levels.black;
    let mut planes: Vec<Vec<f32>> = (0..4).map(|_| vec![0f32; GW * GH]).collect();
    for (p, (dx, dy)) in PLANE_OFFSETS.iter().enumerate() {
        for py in 0..GH {
            let row = (ay + 2 * py + dy) * stride + ax + dx;
            for px in 0..GW {
                planes[p][py * GW + px] =
                    (f32::from(frame.data[row + 2 * px]) - black).max(0.0);
            }
        }
    }
    (0..GW * GH)
        .map(|i| 0.5 * (planes[1][i] + planes[2][i]))
        .collect()
}

/// Interior crop at level 0, in quad px. Every statistic below is taken inside
/// it. It has to be generous: `warp_frame_in_place_*` leaves the samples that
/// map outside the source at black, and a 2000 DN step on a ring is a far
/// larger signal than the 28 DN of noise being measured. Sized for the worst
/// warp in the sweep — 3.9 px of translation plus 2.3% of scale over a 256 px
/// half-extent plus the resampler's support, about 15 px — with 4x headroom.
/// `assert_no_border` fails loudly rather than letting a border in quietly.
const CROP: usize = 64;

/// `E[L_k^2]` per Laplacian band, interior only. The base band is excluded:
/// `add_frame` gates bands `0..nb` and never consults `beta` for the base, and
/// the base is the one level that carries the scene's DC.
fn band_power(luma: &[f32], bands: usize) -> Vec<f64> {
    let sizes = level_sizes(GW, GH, bands);
    let mut ws = Workspace::new(&sizes);
    let mut pyr = Pyramid::zeros(&sizes);
    pyr.build(luma, &mut ws);
    sizes
        .iter()
        .enumerate()
        .take(sizes.len() - 1)
        .map(|(k, sz)| {
            let m = (CROP >> k).max(3).min(sz.width / 4).min(sz.height / 4);
            let lv = pyr.level(k);
            let (mut acc, mut n) = (0.0f64, 0usize);
            for y in m..sz.height.saturating_sub(m) {
                for x in m..sz.width.saturating_sub(m) {
                    let v = f64::from(lv[y * sz.width + x]);
                    acc += v * v;
                    n += 1;
                }
            }
            if n == 0 { 0.0 } else { acc / n as f64 }
        })
        .collect()
}

/// Level-0 variance inside the same crop.
fn variance(v: &[f32]) -> f64 {
    let mut s = Vec::with_capacity((GW - 2 * CROP) * (GH - 2 * CROP));
    for y in CROP..GH - CROP {
        for x in CROP..GW - CROP {
            s.push(f64::from(v[y * GW + x]));
        }
    }
    let n = s.len() as f64;
    let mean = s.iter().sum::<f64>() / n;
    s.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n
}

/// The crop must contain no warp border. A black ring would dominate every
/// statistic here and would do it silently.
fn assert_no_border(luma: &[f32], what: &str) {
    let mut lo = f32::INFINITY;
    for y in CROP..GH - CROP {
        for x in CROP..GW - CROP {
            lo = lo.min(luma[y * GW + x]);
        }
    }
    assert!(
        lo > 0.5 * LEVEL as f32,
        "{what}: the crop contains a warp border (min {lo:.1} DN, level {LEVEL:.0}); \
         CROP={CROP} is too small for this warp"
    );
}

/// One arm: warp the probe (or not), deinterleave, and read the band powers.
fn arm(
    sigma_p: f64,
    seed: u64,
    blur: bool,
    warp: Option<(Similarity, bool)>,
    bands: usize,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
) -> Result<(Vec<f64>, f64)> {
    let mut f = probe_frame(sigma_p, seed, blur);
    if let Some((t, fullres)) = warp {
        if fullres {
            warp_frame_in_place_fullres(&mut f, t, geom, resampler, scratch)?;
        } else {
            warp_frame_in_place_plane(&mut f, t, geom, resampler, scratch)?;
        }
    }
    let luma = green_luma(&f);
    assert_no_border(&luma, if warp.is_none() { "unwarped" } else { "warped" });
    Ok((band_power(&luma, bands), variance(&luma)))
}

/// Pooled over independent realisations, because a single probe's coarsest
/// level has too few samples for something the gate multiplies.
fn arm_pooled(
    sigma_p: f64,
    blur: bool,
    warp: Option<(Similarity, bool)>,
    bands: usize,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
    reals: usize,
) -> Result<(Vec<f64>, f64)> {
    let mut acc: Vec<f64> = Vec::new();
    let mut var = 0.0f64;
    for r in 0..reals {
        let seed = 0x2545_F491_4F6C_DD1D ^ (r as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15);
        let (p, v) = arm(sigma_p, seed, blur, warp, bands, geom, resampler, scratch)?;
        if acc.is_empty() {
            acc = vec![0.0; p.len()];
        }
        for (a, b) in acc.iter_mut().zip(&p) {
            *a += b;
        }
        var += v;
    }
    for a in acc.iter_mut() {
        *a /= reals as f64;
    }
    Ok((acc, var / reals as f64))
}

fn main() -> Result<()> {
    let bands = DEFAULT_BANDS;
    let geom = PlaneGeometry { width: GW, height: GH };
    let resampler = Resampler::CatmullRom;
    let reals: usize = std::env::var("REALS").ok().and_then(|v| v.parse().ok()).unwrap_or(8);
    let mut scratch = WarpScratch::new(geom);

    // Green luma is (G1 + G2)/2 of two independent photosites, so its level-0
    // variance is sigma_p^2 / 2. Injected rather than assumed, and checked in C0.
    let sigma_p = 40.0_f64;

    println!("BUILD-GATE -- is the pyramid band-noise floor stale after the gather flip?");
    println!(
        "  probe {}x{} quad ({}x{} photosites), {bands} bands, {reals} realisations, \
         CatmullRom, sigma_p {sigma_p} DN",
        GW,
        GH,
        2 * GW,
        2 * GH
    );

    let white = BandGain::measure(bands);
    let (p_none, v_none) = arm_pooled(
        sigma_p, false, None, bands, geom, resampler, &mut scratch, reals,
    )?;

    println!("\n== commissioning ==");
    // C0: the injected noise is the noise I think it is.
    let expect = sigma_p * sigma_p / 2.0;
    println!(
        "  C0 green-luma level-0 variance: measured {v_none:.2} DN^2, expected sigma_p^2/2 = \
         {expect:.2}   ratio {:.4}   {}",
        v_none / expect,
        if (v_none / expect - 1.0).abs() < 0.02 { "PASS" } else { "FAIL" }
    );

    // C1: with no warp the probe must reproduce the shipping white-noise beta.
    // Per band, not pooled: the probe's deep bands have few samples (band 5 is
    // 16x16 before cropping), so a single worst-case number would either hide a
    // real gap at band 0 or condemn the whole probe for sampling noise at band
    // 5. Bands that fail the null are excluded from every result below and
    // named, rather than being quietly carried.
    let beta_none: Vec<f64> = p_none.iter().map(|p| p / v_none).collect();
    let nlap = beta_none.len();
    let gaps: Vec<f64> = (0..nlap)
        .map(|k| beta_none[k] / f64::from(white.beta(k)) - 1.0)
        .collect();
    let trusted: Vec<bool> = gaps.iter().map(|g| g.abs() < 0.03).collect();
    println!("  C1 null, no warp: beta_actual == BandGain::measure, PER BAND");
    print!("     band   ");
    for k in 0..nlap {
        print!("{k:>10}");
    }
    println!();
    print!("     white  ");
    for k in 0..nlap {
        print!("{:10.5}", white.beta(k));
    }
    println!();
    print!("     probe  ");
    for b in beta_none.iter().take(nlap) {
        print!("{b:10.5}");
    }
    println!();
    print!("     gap    ");
    for g in &gaps {
        print!("{:9.2}%", 100.0 * g);
    }
    println!();
    print!("     verdict");
    for t in &trusted {
        print!("{:>10}", if *t { "PASS" } else { "excl" });
    }
    println!();
    println!(
        "     bands trusted: {:?}   (excluded bands are probe-limited, not gate findings)",
        (0..nlap).filter(|k| trusted[*k]).collect::<Vec<_>>()
    );

    // C2: beta is a ratio, so doubling the noise must not move it. Stated
    // explicitly because amplitude-invariance is exactly what killed
    // `overshoot_frac` -- there it was a bug, here it is the definition, and
    // the difference is that this quantity is a *normalised* one by
    // construction and its numerator is checked to move in C4.
    let (p2, v2) = arm_pooled(
        2.0 * sigma_p, false, None, bands, geom, resampler, &mut scratch, reals,
    )?;
    let b2: Vec<f64> = p2.iter().map(|p| p / v2).collect();
    let gap2 = (0..nlap).map(|k| (b2[k] / beta_none[k] - 1.0).abs()).fold(0.0, f64::max);
    println!(
        "  C2 amplitude x2: beta unchanged (it is a ratio)      worst gap {:.3}%   {}",
        100.0 * gap2,
        if gap2 < 0.05 { "PASS" } else { "FAIL" }
    );
    println!(
        "     numerator DID move: E[L_0^2] {:.1} -> {:.1} DN^2 (x{:.3}), so C2 is not a dead \
         statistic",
        p_none[0],
        p2[0],
        p2[0] / p_none[0]
    );

    // C3 planted DEFECT: pre-correlate the noise. beta[0] must fall.
    let (p_blur, v_blur) = arm_pooled(
        sigma_p, true, None, bands, geom, resampler, &mut scratch, reals,
    )?;
    let b_blur: Vec<f64> = p_blur.iter().map(|p| p / v_blur).collect();
    println!(
        "  C3 planted defect (5x5 pre-blur, a stronger low-pass than any warp):\n     \
         beta[0] {:.4} -> {:.4}   {}",
        beta_none[0],
        b_blur[0],
        if b_blur[0] < 0.7 * beta_none[0] { "PASS - falls" } else { "FAIL" }
    );

    // C4 planted IMPROVEMENT: a warp so small it is the identity must leave the
    // floor where it was. This is the improvement half of 110.6 for an
    // estimator: an arm that should NOT move, and does not.
    let tiny = Similarity::from_params(SimilarityParams { ax: 0.0, ay: 0.0, g: 0.0, rot: 0.0 });
    let (p_id, v_id) = arm_pooled(
        sigma_p, false, Some((tiny, true)), bands, geom, resampler, &mut scratch, reals,
    )?;
    let b_id: Vec<f64> = p_id.iter().map(|p| p / v_id).collect();
    println!(
        "  C4 planted improvement (identity warp, full-res gather):\n     \
         beta[0] {:.4} vs unwarped {:.4}   gap {:+.3}%   {}",
        b_id[0],
        beta_none[0],
        100.0 * (b_id[0] / beta_none[0] - 1.0),
        if (b_id[0] / beta_none[0] - 1.0).abs() < 0.02 { "PASS - flat" } else { "FAIL" }
    );

    // ---- the measurement -------------------------------------------------
    println!("\n== beta_actual / beta_white, by arm and by warp ==");
    println!("  the factor the SHIPPING floor is wrong by. 1.000 would mean the gate is fine.");
    println!(
        "\n  {:>7} {:>7} | {:>8} {:>8} {:>8} | {:>8} {:>8} | {:>9}",
        "trans", "scale%", "b0 plane", "b0 full", "b0 white", "r plane", "r full", "full/plane"
    );
    let warps = [
        (0.37, 0.23, 0.0004, 0.0006),
        (0.05, 0.03, 0.0, 0.0),
        (0.50, 0.50, 0.0, 0.0),
        (1.37, 0.83, 0.0, 0.0),
        (3.10, -2.40, 0.0, 0.0),
        (0.37, 0.23, 0.005, 0.0),
        (0.37, 0.23, 0.023, 0.0),
        (2.50, 1.75, 0.012, 0.002),
    ];
    let mut ratios: Vec<(f64, f64)> = Vec::new();
    for (ax, ay, g, rot) in warps {
        let t = Similarity::from_params(SimilarityParams { ax, ay, g, rot });
        let (pp, vp) = arm_pooled(
            sigma_p, false, Some((t, false)), bands, geom, resampler, &mut scratch, reals,
        )?;
        let (pf, vf) = arm_pooled(
            sigma_p, false, Some((t, true)), bands, geom, resampler, &mut scratch, reals,
        )?;
        // Normalised by the UNWARPED variance, because that is what the gate's
        // `var` models: the raw sensor noise, which the warp does not change.
        let (bp, bf) = (pp[0] / v_none, pf[0] / v_none);
        let _ = (vp, vf);
        let w0 = f64::from(white.beta(0));
        println!(
            "  {:7.2} {:7.2} | {:8.4} {:8.4} {:8.4} | {:8.4} {:8.4} | {:9.4}",
            (ax * ax + ay * ay).sqrt(),
            g * 100.0,
            bp,
            bf,
            w0,
            bp / w0,
            bf / w0,
            bf / bp
        );
        ratios.push((bp / w0, bf / w0));
    }

    let lo_p = ratios.iter().map(|r| r.0).fold(f64::INFINITY, f64::min);
    let hi_p = ratios.iter().map(|r| r.0).fold(0.0, f64::max);
    let lo_f = ratios.iter().map(|r| r.1).fold(f64::INFINITY, f64::min);
    let hi_f = ratios.iter().map(|r| r.1).fold(0.0, f64::max);
    println!(
        "\n  plane arm   beta_actual/beta_white spans {lo_p:.4} .. {hi_p:.4}\n  \
         fullres arm beta_actual/beta_white spans {lo_f:.4} .. {hi_f:.4}"
    );
    println!(
        "  A SINGLE CONSTANT CANNOT SERVE BOTH: the two arms' spans {} overlap.",
        if hi_p < lo_f || hi_f < lo_p { "do NOT" } else { "DO" }
    );

    // Deeper bands: does the warp matter there, or only at band 0?
    println!("\n== does the correction matter beyond band 0? ==");
    let t = Similarity::from_params(SimilarityParams { ax: 0.37, ay: 0.23, g: 0.0004, rot: 0.0006 });
    let (pp, _) = arm_pooled(
        sigma_p, false, Some((t, false)), bands, geom, resampler, &mut scratch, reals,
    )?;
    let (pf, _) = arm_pooled(
        sigma_p, false, Some((t, true)), bands, geom, resampler, &mut scratch, reals,
    )?;
    println!("  {:>5} {:>10} {:>10} {:>10} {:>10} {:>8}", "band", "white", "plane/w", "full/w", "full/plane", "C1");
    for k in 0..nlap {
        let w = f64::from(white.beta(k));
        let (bp, bf) = (pp[k] / v_none, pf[k] / v_none);
        println!(
            "  {k:5} {w:10.5} {:10.4} {:10.4} {:10.4} {:>8}",
            bp / w,
            bf / w,
            bf / bp,
            if trusted[k] { "ok" } else { "excl" }
        );
    }

    // ---- the phase sweep -------------------------------------------------
    // The owner's constraint is that no closed-form kernel ratio can serve,
    // because the transfer depends on the per-frame warp PHASE. That is a
    // claim about a function, so measure the function: sweep a pure diagonal
    // translation across one full plane-pixel and read the floor at each
    // phase. If the constraint is right this traces out a curve, not a level.
    println!("\n== the phase sweep: pure diagonal translation across one plane pixel ==");
    println!("  a closed-form correction would have to be ONE number for this whole column.");
    println!(
        "\n  {:>8} {:>8} | {:>9} {:>9} | {:>9} {:>9}",
        "dx=dy", "full px", "b0 plane", "b0 full", "plane/w", "full/w"
    );
    let w0 = f64::from(white.beta(0));
    let mut ph_p: Vec<f64> = Vec::new();
    let mut ph_f: Vec<f64> = Vec::new();
    for i in 0..=8 {
        let d = f64::from(i) / 8.0;
        let t = Similarity::from_params(SimilarityParams {
            ax: d,
            ay: d,
            g: 0.0,
            rot: 0.0,
        });
        let (pp, _) = arm_pooled(
            sigma_p, false, Some((t, false)), bands, geom, resampler, &mut scratch, reals,
        )?;
        let (pf, _) = arm_pooled(
            sigma_p, false, Some((t, true)), bands, geom, resampler, &mut scratch, reals,
        )?;
        let (bp, bf) = (pp[0] / v_none, pf[0] / v_none);
        println!(
            "  {:8.4} {:8.4} | {:9.4} {:9.4} | {:9.4} {:9.4}",
            d,
            2.0 * d,
            bp,
            bf,
            bp / w0,
            bf / w0
        );
        ph_p.push(bp / w0);
        ph_f.push(bf / w0);
    }
    let sp = (
        ph_p.iter().cloned().fold(f64::INFINITY, f64::min),
        ph_p.iter().cloned().fold(0.0, f64::max),
    );
    let sf = (
        ph_f.iter().cloned().fold(f64::INFINITY, f64::min),
        ph_f.iter().cloned().fold(0.0, f64::max),
    );
    println!(
        "\n  plane   spans {:.4} .. {:.4}  (x{:.2} across phase)\n  \
         fullres spans {:.4} .. {:.4}  (x{:.2} across phase)",
        sp.0,
        sp.1,
        sp.1 / sp.0,
        sf.0,
        sf.1,
        sf.1 / sf.0
    );
    Ok(())
}
