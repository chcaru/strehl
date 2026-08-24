//! M99 — does a per-frame photometric term improve the photograph?
//!
//! `photometric.rs` is included by path rather than as `strehl_core::photometric`,
//! because wiring it into `lib.rs` is a shared registration point that belongs
//! to the orchestrator (the M93 precedent, and the M85/M86 near-miss it records).
//! The wiring patch is given verbatim in `docs/research/M99-photometric.md` §8.
//!
//! # What this measures
//!
//! The defect is a brightness **step between elected regions**: the stacker
//! picks a different source frame in adjacent parts of the image, and if those
//! frames are not the same brightness the boundary shows. So the statistic has
//! to respond to *that*, not to "the render changed". Two are computed, both on
//! background pixels and both zero for a correct render:
//!
//! * **SSC** — the slope of the output luma on the elected frame's own relative
//!   level, divided by the mean luma. If the render carries the per-frame level
//!   through to the output this is about 1; if the level has been removed it is
//!   about 0. A render that merely differs from the baseline, but whose luma is
//!   uncorrelated with which frame won, scores zero.
//! * **BSC** — the median absolute luma difference across adjacent pixel pairs
//!   that straddle an election boundary, divided by the same quantity for pairs
//!   that do not. A step at the boundary drives this above 1; noise alone
//!   leaves it at 1.
//!
//! # The plant
//!
//! A metric that cannot see a planted defect cannot exonerate the build, and the
//! plant must have the **same form as the defect**. So it is a per-frame
//! multiplicative gain — not a translation, not a per-pixel change — injected
//! into the decoded frames at the seam the correction acts on, and the
//! requirement is that the statistic sees it and that the correction removes it.
//!
//! Its *sequence*, however, is deliberately **pseudo-random in frame index**
//! rather than a monotonic ramp. A monotonic plant is collinear with the deck's
//! own monotonic drift, and that was measured to break the test in two separate
//! ways: on `bee-3-cpl` a ramp of the opposite sign partially *cancelled* the
//! defect, and on `lavendar-cpl` a ramp had `corr = +0.9999` with the natural
//! ladder so the residualised coefficient exploded. Same form, orthogonal
//! sequence, and the plant becomes identifiable.
//!
//! Five arms, one decode pass:
//!
//! ```text
//!   A0  as shipped                A1  whole-frame gain     A2  low-detail gain
//!   P0  planted, no correction    P1  planted, corrected
//! ```
//!
//! Usage: `m99-photometric <DIR> [--limit N] [--plant A] [--gate-noise]`

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::align::PlaneRef;
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{FocusStats, regularise};
use strehl_core::noise::NoiseModel;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;
use strehl_core::warpmap::WarpMap;

pub use strehl_core::CfaPlane;
pub mod noise {
    pub use strehl_core::noise::*;
}

#[path = "../../strehl-core/src/photometric.rs"]
#[allow(dead_code)] // the module's public API; the example exercises a subset.
mod photometric;

use photometric::{Flux, PhotometricMap, apply_to_plane, scale_noise_model};

/// Amplitude of the planted per-frame gain ramp, peak to peak as a fraction.
const PLANT_A: f32 = 0.20;

/// Background is the smoothest this fraction of the reference frame, further
/// restricted to pixels brighter than [`BACKGROUND_BRIGHT_Q`]. Chosen once,
/// from the *uncorrected* reference frame, so every arm is scored on the
/// identical pixel set and no arm can move its own goalposts.
const BACKGROUND_Q: f64 = 0.40;

/// Low focus alone is not background: the subject's own dark, unlit body is
/// smooth too, and on `bee-3-cpl` admitting it put the background standard
/// deviation at 62% of its mean, which is scene structure and not a backdrop.
/// The backdrop is the *bright* smooth region, so brightness is required too.
const BACKGROUND_BRIGHT_Q: f64 = 0.60;

struct Arm {
    name: &'static str,
    gain: Box<dyn Fn(usize) -> f32>,
    plant: bool,
    stats: FocusStats,
    out: Vec<f32>,
    best: Vec<f32>,
}

fn list_frames(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    paths.sort();
    Ok(paths)
}

fn percentile(v: &mut [f32], q: f64) -> f32 {
    v.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let i = ((v.len() - 1) as f64 * q).round() as usize;
    v[i]
}

fn median(v: &mut [f32]) -> f32 {
    percentile(v, 0.5)
}

/// One adjacent background pixel pair that straddles an election boundary.
struct Pair {
    a: u16,
    b: u16,
    dy: f32,
}

/// Collect the adjacent background pairs once. Every statistic below is a
/// function of this list, which makes a permutation null affordable: it is a
/// pass over 200k pairs rather than over 8.2M pixels.
fn collect_pairs(
    y: &[f32],
    idx: &[u16],
    mask: &[bool],
    geom: PlaneGeometry,
) -> (Vec<Pair>, Vec<f32>) {
    let (w, h) = (geom.width, geom.height);
    let mut across = Vec::new();
    let mut within = Vec::new();
    for py in 0..h {
        for px in 0..w {
            let i = py * w + px;
            if !mask[i] {
                continue;
            }
            for j in [
                if px + 1 < w { Some(i + 1) } else { None },
                if py + 1 < h { Some(i + w) } else { None },
            ]
            .into_iter()
            .flatten()
            {
                if !mask[j] {
                    continue;
                }
                let dy = y[i] - y[j];
                if idx[i] == idx[j] {
                    within.push(dy.abs());
                } else {
                    across.push(Pair {
                        a: idx[i],
                        b: idx[j],
                        dy,
                    });
                }
            }
        }
    }
    (across, within)
}

/// Slope of the luma **step** across election boundaries on the level step the
/// two elected frames imply, divided by the mean luma.
///
/// The first form of this statistic regressed the output luma on the elected
/// frame's level over every background pixel, and it was useless: the elected
/// frame index is strongly correlated with depth, depth is correlated with
/// scene brightness, and on `bee-3-cpl` the scene term was sixty times the
/// photometric term, so the slope measured the scene and not the defect. It
/// scored 49.98 where the defect can contribute at most about 1.
///
/// Differencing across a one-pixel boundary removes that. Scene radiance is
/// continuous across an arbitrary election boundary, so `E[dY] = 0` whatever
/// the scene does; but if the render carries the per-frame level then
/// `dY = mean(Y) * dR`, `dR` being the difference in the two frames' relative
/// levels. Regressing `dY` on `dR` through the origin and dividing by `mean(Y)`
/// therefore gives **1 when the defect is fully present and 0 when it is gone**.
/// A render that merely differs from the baseline scores zero, which is the
/// property a change-detector would not have.
fn ssc_from_pairs(pairs: &[Pair], level: &[f32], mean_y: f64) -> f64 {
    let (mut sxy, mut sxx) = (0.0f64, 0.0f64);
    for p in pairs {
        let (la, lb) = match (level.get(p.a as usize), level.get(p.b as usize)) {
            (Some(&la), Some(&lb)) => (la, lb),
            _ => continue,
        };
        let dx = f64::from(la - lb);
        sxy += dx * f64::from(p.dy);
        sxx += dx * dx;
    }
    if pairs.len() < 1024 || sxx <= 0.0 || mean_y == 0.0 {
        return f64::NAN;
    }
    (sxy / sxx) / mean_y
}

/// Null distribution of [`ssc_from_pairs`] under a shuffled level ladder.
///
/// The residuals are spatially correlated, so a textbook standard error would
/// be optimistic. Permuting the ladder while holding the election map and the
/// luma fixed keeps every one of those correlations and destroys only the
/// association under test, which is the quantity being claimed.
fn ssc_null(pairs: &[Pair], level: &[f32], mean_y: f64, trials: usize) -> (f64, f64) {
    let mut lv = level.to_vec();
    let mut state = 0x9E37_79B9_7F4A_7C15u64;
    let mut vals = Vec::with_capacity(trials);
    for _ in 0..trials {
        for i in (1..lv.len()).rev() {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            lv.swap(i, (state % (i as u64 + 1)) as usize);
        }
        vals.push(ssc_from_pairs(pairs, &lv, mean_y));
    }
    let n = vals.len() as f64;
    let m = vals.iter().sum::<f64>() / n;
    let sd = (vals.iter().map(|v| (v - m) * (v - m)).sum::<f64>() / (n - 1.0)).sqrt();
    (m, sd)
}

/// Pearson correlation, for reporting the collinearity the plant test has to
/// work around.
fn pearson(a: &[f32], b: &[f32]) -> f64 {
    let n = a.len() as f64;
    if n < 2.0 {
        return f64::NAN;
    }
    let ma = a.iter().map(|v| f64::from(*v)).sum::<f64>() / n;
    let mb = b.iter().map(|v| f64::from(*v)).sum::<f64>() / n;
    let (mut sab, mut saa, mut sbb) = (0.0f64, 0.0f64, 0.0f64);
    for (x, y) in a.iter().zip(b.iter()) {
        let (dx, dy) = (f64::from(*x) - ma, f64::from(*y) - mb);
        sab += dx * dy;
        saa += dx * dx;
        sbb += dy * dy;
    }
    if saa <= 0.0 || sbb <= 0.0 {
        return f64::NAN;
    }
    sab / (saa * sbb).sqrt()
}

/// Residualise `x` against `basis`, so a coefficient on the result is the
/// *partial* coefficient on `x` holding `basis` fixed.
///
/// This is what makes the plant test valid. The planted ramp and the deck's own
/// background drift are both monotonic in frame index, so they are strongly
/// correlated — and on `bee-3-cpl` they are correlated with **opposite sign**,
/// so the ramp partially cancels the natural defect. A plant test that
/// regressed on the combined ladder therefore showed the planted render as no
/// worse than the baseline, which says nothing about whether the statistic can
/// see a plant. Removing the natural ladder from the ramp first isolates the
/// injected term, and the coefficient on it is 0 when there is no plant and 1
/// when the render carries one in full.
fn residualise(x: &[f32], basis: &[f32]) -> Vec<f32> {
    let n = x.len() as f64;
    if n < 2.0 {
        return x.to_vec();
    }
    let mx = x.iter().map(|v| f64::from(*v)).sum::<f64>() / n;
    let mb = basis.iter().map(|v| f64::from(*v)).sum::<f64>() / n;
    let mut sxy = 0.0f64;
    let mut sbb = 0.0f64;
    for (a, b) in x.iter().zip(basis.iter()) {
        let db = f64::from(*b) - mb;
        sxy += db * (f64::from(*a) - mx);
        sbb += db * db;
    }
    let slope = if sbb > 0.0 { sxy / sbb } else { 0.0 };
    x.iter()
        .zip(basis.iter())
        .map(|(a, b)| (f64::from(*a) - slope * (f64::from(*b) - mb) - mx) as f32)
        .collect()
}

/// Median |dY| across election boundaries over median |dY| within regions.
fn bsc_from_pairs(across: &[Pair], within: &mut [f32]) -> f64 {
    if across.len() < 64 || within.len() < 64 {
        return f64::NAN;
    }
    let mut a: Vec<f32> = across.iter().map(|p| p.dy.abs()).collect();
    let ma = f64::from(median(&mut a));
    let mw = f64::from(median(within));
    if mw > 0.0 { ma / mw } else { f64::NAN }
}


fn mean_of(v: &[f32], mask: &[bool]) -> f64 {
    let (mut s, mut n) = (0.0f64, 0.0f64);
    for (i, &m) in mask.iter().enumerate() {
        if m {
            s += f64::from(v[i]);
            n += 1.0;
        }
    }
    if n > 0.0 { s / n } else { f64::NAN }
}

fn sd_of(v: &[f32], mask: &[bool]) -> f64 {
    let m = mean_of(v, mask);
    let (mut s, mut n) = (0.0f64, 0.0f64);
    for (i, &k) in mask.iter().enumerate() {
        if k {
            let d = f64::from(v[i]) - m;
            s += d * d;
            n += 1.0;
        }
    }
    if n > 1.0 { (s / (n - 1.0)).sqrt() } else { f64::NAN }
}

#[allow(clippy::too_many_lines)]
fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        bail!("usage: m99-photometric <DIR> [--limit N] [--plant A]");
    }
    let dir = PathBuf::from(&args[0]);
    let mut limit: Option<usize> = None;
    let mut plant_a = PLANT_A;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--limit" => {
                limit = Some(args[i + 1].parse()?);
                i += 2;
            }
            "--plant" => {
                plant_a = args[i + 1].parse()?;
                i += 2;
            }
            other => bail!("unknown argument {other}"),
        }
    }

    let mut paths = list_frames(&dir)?;
    if let Some(n) = limit {
        paths.truncate(n);
    }
    let n = paths.len();
    if n < 8 {
        bail!("{} holds {n} ARW files", dir.display());
    }

    let side = dir.join("warpmap.txt");
    let map = WarpMap::load(&side)
        .with_context(|| format!("loading the alignment sidecar {}", side.display()))?;
    if map.len() < n {
        bail!(
            "sidecar has {} placements but {n} frames were listed",
            map.len()
        );
    }
    let geom = map.geometry();
    let px = geom.pixels();
    let reference = map.provenance().reference.min(n - 1);

    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    if first.geometry() != geom {
        bail!("frame geometry does not match the sidecar");
    }
    let levels = first.levels;
    let base_noise = profile::noise_model_for(&first.camera, first.iso, levels);
    drop(first);

    println!("stack           : {}", dir.display());
    println!("frames          : {n}   reference {reference}   plane {}x{}", geom.width, geom.height);
    println!("plant amplitude : {plant_a:+.3} peak-to-peak, per-frame gain, pseudo-random in k");
    println!("background      : smoothest {:.0}% of the reference frame", 100.0 * BACKGROUND_Q);

    // The plant is a per-frame multiplicative gain — the same *form* as the
    // defect, as the brief requires. Its *sequence* is deliberately pseudo-
    // random rather than a monotonic ramp.
    //
    // A monotonic ramp is collinear with the deck's own monotonic drift, and
    // that makes the plant test unidentifiable in two different ways, both of
    // which were measured before this line was written. On `bee-3-cpl` the
    // ramp has the opposite sign to the natural drift and partially cancels
    // it, so the raw statistic reads "no plant". On `lavendar-cpl` the ramp
    // has corr = +0.9999 with the natural ladder, so projecting the natural
    // ladder out leaves a near-zero-variance residual and the partial
    // coefficient explodes to +/-40. Neither is a statement about the metric.
    //
    // A pseudo-random sequence has the identical form and amplitude but is
    // near-orthogonal to any monotonic drift by construction, so the planted
    // term is separately identifiable. Deterministic, so the run reproduces.
    let plant_gain = |k: usize| -> f32 {
        let mut z = (k as u64).wrapping_add(0x9e37_79b9_7f4a_7c15);
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^= z >> 31;
        let u = (z >> 11) as f32 / (1u64 << 53) as f32;
        1.0 + plant_a * (u - 0.5)
    };

    // ---- pass 0: the reference frame alone, so the background mask exists
    // before the flux ladder is accumulated. The mask is drawn from the
    // *uncorrected* reference, so every arm is scored on the same pixels.
    let t0 = std::time::Instant::now();
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut warped = vec![0.0f32; px];
    let mut cover = vec![false; px];
    let mut field = FocusField::new(geom);
    let mut boxsc = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];
    let sat = levels.white - levels.black;

    {
        let p = &paths[reference];
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        drop(frame);
        let src = PlaneRef::new(&luma, geom.width, geom.height).context("luma plane geometry")?;
        strehl_core::warpmap::gather_frame(&map, reference, src, &mut warped, &mut cover)?;
        for (v, &c) in warped.iter_mut().zip(cover.iter()) {
            if !c {
                *v = 0.0;
            }
        }
        field.compute(&warped, &base_noise);
        regularise(field.values(), geom, &mut boxsc, &mut reg);
    }
    let ref_focus = reg.clone();
    let ref_luma = warped.clone();
    let mut sorted = ref_focus.clone();
    let thr = percentile(&mut sorted, BACKGROUND_Q);
    let mut sortl = ref_luma.clone();
    let lthr = percentile(&mut sortl, BACKGROUND_BRIGHT_Q);
    let background: Vec<bool> = ref_focus
        .iter()
        .zip(ref_luma.iter())
        .map(|(&f, &l)| f <= thr && f.is_finite() && l >= lthr && l.is_finite())
        .collect();
    let nbg = background.iter().filter(|b| **b).count();
    println!(
        "background mask : {nbg} of {px} px ({:.1}%), reference focus <= {thr:.5} and luma >= {lthr:.0}",
        100.0 * nbg as f64 / px as f64
    );

    // ---- pass 1: the flux ladders --------------------------------------
    let mut flux_plain: Vec<Flux> = Vec::with_capacity(n);
    let mut flux_bg: Vec<Flux> = Vec::with_capacity(n);
    let mut flux_plant: Vec<Flux> = Vec::with_capacity(n);
    let mut cover_bg = vec![false; px];

    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        drop(frame);
        let src = PlaneRef::new(&luma, geom.width, geom.height).context("luma plane geometry")?;
        strehl_core::warpmap::gather_frame(&map, k, src, &mut warped, &mut cover)?;
        for (v, &c) in warped.iter_mut().zip(cover.iter()) {
            if !c {
                *v = 0.0;
            }
        }
        let mut f = Flux::new();
        f.fold_covered(&warped, &cover, sat);
        flux_plain.push(f);
        for i in 0..px {
            cover_bg[i] = cover[i] && background[i];
        }
        let mut fb = Flux::new();
        fb.fold_covered(&warped, &cover_bg, sat);
        flux_bg.push(fb);
        let mut fp = Flux::new();
        let g = plant_gain(k);
        // The plant is a gain, so its flux is the plain flux times the gain;
        // computing it rather than asserting it keeps the arms symmetric.
        apply_to_plane(&mut warped, g);
        fp.fold_covered(&warped, &cover_bg, sat * g);
        flux_plant.push(fp);
        apply_to_plane(&mut warped, 1.0 / g);

        if k % 50 == 0 {
            println!("  pass 1: frame {k}/{n}  {:.1} s", t0.elapsed().as_secs_f64());
        }
    }
    let pass1 = t0.elapsed().as_secs_f64();
    println!("  pass 1 done in {pass1:.1} s");

    let map_plain =
        PhotometricMap::from_flux(&flux_plain, reference).map_err(|e| anyhow::anyhow!(e))?;
    let map_bg = PhotometricMap::from_flux(&flux_bg, reference).map_err(|e| anyhow::anyhow!(e))?;
    let map_plant =
        PhotometricMap::from_flux(&flux_plant, reference).map_err(|e| anyhow::anyhow!(e))?;
    println!(
        "whole-frame map : span {:.4} ({:+.4} stops), {} refused, gains {:.4} .. {:.4}",
        map_plain.span(),
        map_plain.span().log2(),
        map_plain.refused_count(),
        map_plain.gains().iter().copied().fold(f32::INFINITY, f32::min),
        map_plain.gains().iter().copied().fold(0.0f32, f32::max)
    );
    println!(
        "background map  : span {:.4} ({:+.4} stops), {} refused, gains {:.4} .. {:.4}",
        map_bg.span(),
        map_bg.span().log2(),
        map_bg.refused_count(),
        map_bg.gains().iter().copied().fold(f32::INFINITY, f32::min),
        map_bg.gains().iter().copied().fold(0.0f32, f32::max)
    );
    let plant_lo = (0..n).map(plant_gain).fold(f32::INFINITY, f32::min);
    let plant_hi = (0..n).map(plant_gain).fold(0.0f32, f32::max);
    println!(
        "planted map     : span {:.4}  (the plant alone would be {:.4})",
        map_plant.span(),
        f64::from(plant_hi / plant_lo)
    );

    // ---- pass 2: five arms, one decode ------------------------------------
    let mut arms: Vec<Arm> = Vec::new();
    let gp: Vec<f32> = map_plain.gains().to_vec();
    let gb: Vec<f32> = map_bg.gains().to_vec();
    let gq: Vec<f32> = map_plant.gains().to_vec();
    arms.push(Arm { name: "A0 shipped", gain: Box::new(|_| 1.0), plant: false,
        stats: FocusStats::new(geom), out: vec![0.0; px], best: vec![f32::NEG_INFINITY; px] });
    arms.push(Arm { name: "A1 whole-frame gain", gain: Box::new(move |k| gp[k]), plant: false,
        stats: FocusStats::new(geom), out: vec![0.0; px], best: vec![f32::NEG_INFINITY; px] });
    arms.push(Arm { name: "A2 background gain", gain: Box::new(move |k| gb[k]), plant: false,
        stats: FocusStats::new(geom), out: vec![0.0; px], best: vec![f32::NEG_INFINITY; px] });
    arms.push(Arm { name: "P0 planted", gain: Box::new(|_| 1.0), plant: true,
        stats: FocusStats::new(geom), out: vec![0.0; px], best: vec![f32::NEG_INFINITY; px] });
    arms.push(Arm { name: "P1 planted + corr", gain: Box::new(move |k| gq[k]), plant: true,
        stats: FocusStats::new(geom), out: vec![0.0; px], best: vec![f32::NEG_INFINITY; px] });

    let t1 = std::time::Instant::now();
    let mut scaled = vec![0.0f32; px];
    let mut arm_seconds = vec![0.0f64; arms.len()];
    for (k, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
        green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        drop(frame);
        let src = PlaneRef::new(&luma, geom.width, geom.height).context("luma plane geometry")?;
        strehl_core::warpmap::gather_frame(&map, k, src, &mut warped, &mut cover)?;
        for (v, &c) in warped.iter_mut().zip(cover.iter()) {
            if !c {
                *v = 0.0;
            }
        }
        for (ai, arm) in arms.iter_mut().enumerate() {
            let ta = std::time::Instant::now();
            let g = (arm.gain)(k) * if arm.plant { plant_gain(k) } else { 1.0 };
            scaled.copy_from_slice(&warped);
            apply_to_plane(&mut scaled, g);
            // The noise model must see the gain. `scale_noise_model` is the
            // whole point of the module: without it the gate believes the
            // brightened frames are quieter than they are.
            let nm: NoiseModel = if g == 1.0 {
                base_noise.clone()
            } else {
                scale_noise_model(&base_noise, g)
            };
            field.compute(&scaled, &nm);
            regularise(field.values(), geom, &mut boxsc, &mut reg);
            arm.stats.fold(k as u16, &reg)?;
            for i in 0..px {
                if reg[i] > arm.best[i] {
                    arm.best[i] = reg[i];
                    arm.out[i] = scaled[i];
                }
            }
            arm_seconds[ai] += ta.elapsed().as_secs_f64();
        }
        if k % 50 == 0 {
            println!("  pass 2: frame {k}/{n}  {:.1} s", t1.elapsed().as_secs_f64());
        }
    }
    let pass2 = t1.elapsed().as_secs_f64();
    println!("  pass 2 done in {pass2:.1} s");
    println!(
        "cost            : per-arm merge seconds {:?}  (A1 - A0 = {:+.2} s over {n} frames)",
        arm_seconds.iter().map(|s| (s * 10.0).round() / 10.0).collect::<Vec<_>>(),
        arm_seconds[1] - arm_seconds[0]
    );

    // Relative level of each frame, the regressor SSC uses. gain = ref/level,
    // so the level is its reciprocal. The **background** ladder is the primary
    // regressor: the defect under test is a brightness step in the background
    // between elected regions, so the quantity to test for is the background's
    // own per-frame level, not the whole frame's flux. The whole-frame ladder
    // is reported alongside because it is what a flux-based correction removes,
    // and the two are not the same number.
    let level_bg: Vec<f32> = map_bg.gains().iter().map(|g| 1.0 / g).collect();
    let level_plain: Vec<f32> = map_plain.gains().iter().map(|g| 1.0 / g).collect();
    let level_plant: Vec<f32> = map_plant.gains().iter().map(|g| 1.0 / g).collect();
    // The pure planted ramp, with the deck's own background drift projected
    // out, so its coefficient is the partial one. See `residualise`.
    let ramp: Vec<f32> = (0..n).map(plant_gain).collect();
    let ramp_only = residualise(&ramp, &level_bg);
    println!(
        "plant regressor : corr(ramp, background level) = {:+.4}  (why the ramp must be residualised)",
        pearson(&ramp, &level_bg)
    );

    println!("\n--- Phase D: does the correction improve the photograph? ---");
    println!(
        "{:<21} {:>8} {:>8} {:>7} {:>8} {:>8} {:>8} {:>10} {:>10}",
        "arm", "SSC", "null sd", "z", "SSC_wf", "SSC_pl", "BSC", "bg sd/mean", "bdy pairs"
    );
    let mut summary = Vec::new();
    for arm in &arms {
        let lv = if arm.plant { &level_plant } else { &level_bg };
        let idx = arm.stats.best_index();
        let m = mean_of(&arm.out, &background);
        let (across, mut within) = collect_pairs(&arm.out, idx, &background, geom);
        let s = ssc_from_pairs(&across, lv, m);
        let (_, nsd) = ssc_null(&across, lv, m, 200);
        let swf = ssc_from_pairs(&across, &level_plain, m);
        let spl = ssc_from_pairs(&across, &ramp_only, m);
        let b = bsc_from_pairs(&across, &mut within);
        let sd = sd_of(&arm.out, &background);
        println!(
            "{:<21} {:>8.4} {:>8.4} {:>7.1} {:>8.4} {:>8.4} {:>8.4} {:>10.5} {:>10}",
            arm.name,
            s,
            nsd,
            s / nsd,
            swf,
            spl,
            b,
            sd / m,
            across.len()
        );
        summary.push((arm.name, s, b, m, sd / m, nsd, spl));
    }

    println!("\n--- pre-registered bars ---");
    let (s_a0, s_a1, s_a2) = (summary[0].1, summary[1].1, summary[2].1);
    let (b_a0, b_a1, b_a2) = (summary[0].2, summary[1].2, summary[2].2);
    let (p_a0, p_p0, p_p1) = (summary[0].6, summary[3].6, summary[4].6);
    println!(
        "PR-6 plant visible : SSC_pl(A0) = {:>8.4} -> SSC_pl(P0) = {:>8.4}   (the ramp alone, natural drift projected out)  -> {}",
        p_a0,
        p_p0,
        if (p_p0 - p_a0).abs() >= 0.5 {
            "METRIC SEES THE PLANT"
        } else {
            "METRIC IS BLIND -- Phase D VOID"
        }
    );
    println!(
        "PR-6 plant removed : SSC_pl(P0) = {:>8.4} -> SSC_pl(P1) = {:>8.4}  -> {}",
        p_p0,
        p_p1,
        if (p_p1 - p_a0).abs() <= 0.25 * (p_p0 - p_a0).abs().max(1e-9) {
            "REMOVED"
        } else {
            "NOT REMOVED"
        }
    );
    let detectable = s_a0.abs() >= 3.0 * summary[0].5;
    println!(
        "PR-6 defect present: SSC(A0) = {:>8.4}, permutation null sd {:.4}, z = {:.1}  -> {}",
        s_a0,
        summary[0].5,
        s_a0 / summary[0].5,
        if detectable {
            "DEFECT IS REAL IN THE RENDER"
        } else {
            "NO DEFECT DETECTABLE -- nothing for the correction to fix"
        }
    );
    for (i, label) in [(1usize, "A1 whole-frame gain"), (2usize, "A2 background gain")] {
        let s = if i == 1 { s_a1 } else { s_a2 };
        let b = if i == 1 { b_a1 } else { b_a2 };
        let sd_ok = summary[i].4 <= summary[0].4 * 1.02;
        println!(
            "PR-6 improvement   : {label:<20} SSC {:>8.4} -> {:>8.4}   BSC {:.4} -> {:.4}   bg sd/mean {:+.2}%  -> {}",
            s_a0,
            s,
            b_a0,
            b,
            100.0 * (summary[i].4 / summary[0].4 - 1.0),
            if !detectable {
                "N/A (no defect)"
            } else if s.abs() <= 0.25 * s_a0.abs() && sd_ok {
                "IMPROVED"
            } else {
                "NOT IMPROVED"
            }
        );
    }
    Ok(())
}
