//! M54 — what the absent clip mask actually does to the merged output.
//!
//! This harness deliberately **re-implements nothing** of the pipeline. It links
//! `strehl-core` and `strehl-raw` by path and drives the shipped
//! `green_luma_with_clip` -> `FocusField::compute` -> `regularise` ->
//! `FocusStats` -> `Estimator` sequence exactly as `strehl-cli`'s `merge_cmd`
//! does, so that anything it measures is a property of the pipeline and not of
//! this file.
//!
//! The one thing it *does* implement is the **masked winner election** (arm B),
//! because that is the change under test and it does not exist in the crate.
//! Its power check is `election_matches_focus_stats_when_nothing_is_masked`,
//! run on every invocation against the real `FocusStats` on real data: with an
//! all-valid mask the two must agree bit for bit at every pixel.
//!
//! Constants shared with the code under test (rule 34, stated up front):
//! `CONTAINER_MAX_DN`, `Levels::black`/`white` from the decoder, the noise model
//! from `profile::noise_model_for`, `WINDOW_RADIUS`, `REGULARISER_RADIUS`,
//! `FOCUS_NOISE_SD`. Sharing is unavoidable: the question is not whether any of
//! those is right, it is what the pipeline built from them does at a clipped
//! pixel. The falsifiable external term is the **deficit null** — `deficit ~ 0`
//! at an unclipped pixel — evaluated on stacks that contain no clipping at all,
//! where this harness has no way to manufacture a zero.
//!
//! Usage:
//!   m54-clip-mask --dir <stack dir> [--limit N] [--gate T]...

use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result, bail};
use strehl_core::CfaPlane;
use strehl_core::boxfilter::box_mean;
use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};
use strehl_core::focus::{FocusField, SUPPORT_RADIUS};
use strehl_core::merge::{Estimator, FocusStats, Gate, REGULARISER_RADIUS, regularise};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

const NO_FRAME: u16 = u16::MAX;

struct Args {
    dir: PathBuf,
    limit: Option<usize>,
    gates: Vec<f32>,
}

fn parse_args() -> Result<Args> {
    let mut dir = None;
    let mut limit = None;
    let mut gates: Vec<f32> = Vec::new();
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--dir" => dir = Some(PathBuf::from(it.next().context("--dir needs a value")?)),
            "--limit" => limit = Some(it.next().context("--limit needs a value")?.parse()?),
            "--gate" => gates.push(it.next().context("--gate needs a value")?.parse()?),
            other => bail!("unknown argument {other}"),
        }
    }
    if gates.is_empty() {
        gates = vec![0.5, 1.0, 2.0, 4.0]; // the CLI's own default ladder
    }
    Ok(Args {
        dir: dir.context("--dir is required")?,
        limit,
        gates,
    })
}

fn raw_paths(dir: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    v.sort();
    if let Some(n) = limit {
        v.truncate(n);
    }
    if v.is_empty() {
        bail!("no .ARW files under {}", dir.display());
    }
    Ok(v)
}

/// A winner election that can refuse a frame at a pixel.
///
/// Two tiers: a frame whose focus response is *valid* at a pixel always beats
/// one that is not; within a tier the rule is `FocusStats::beats` verbatim —
/// higher response wins, ties to the lower frame index. With every frame valid
/// everywhere the tiering is inert and this must reduce **exactly** to
/// `FocusStats`; that reduction is asserted on real data on every run.
struct MaskedStats {
    best_focus: Vec<f32>,
    best_index: Vec<u16>,
    elected_valid: Vec<bool>,
}

impl MaskedStats {
    fn new(px: usize) -> Self {
        Self {
            best_focus: vec![f32::NEG_INFINITY; px],
            best_index: vec![NO_FRAME; px],
            elected_valid: vec![false; px],
        }
    }

    #[inline]
    fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16) -> bool {
        focus > cur_focus || (focus == cur_focus && index < cur_index)
    }

    /// `valid = None` means "every pixel is valid in this frame".
    fn fold(&mut self, frame_index: u16, regularised: &[f32], valid: Option<&[bool]>) {
        for i in 0..self.best_focus.len() {
            let v = valid.map(|m| m[i]).unwrap_or(true);
            let cur = self.elected_valid[i];
            let take = if v && !cur {
                true
            } else if v == cur {
                Self::beats(
                    regularised[i],
                    frame_index,
                    self.best_focus[i],
                    self.best_index[i],
                )
            } else {
                false
            };
            if take {
                self.best_focus[i] = regularised[i];
                self.best_index[i] = frame_index;
                self.elected_valid[i] = v;
            }
        }
    }
}

fn quantile(v: &mut Vec<f32>, q: f64) -> f32 {
    if v.is_empty() {
        return f32::NAN;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let i = ((v.len() - 1) as f64 * q).round() as usize;
    v[i]
}

fn stats_of(v: &mut Vec<f32>) -> (f64, f32, f32, f32, f32) {
    let mean = v.iter().map(|x| *x as f64).sum::<f64>() / v.len().max(1) as f64;
    (
        mean,
        quantile(v, 0.5),
        quantile(v, 0.9),
        quantile(v, 0.99),
        quantile(v, 1.0),
    )
}

fn main() -> Result<()> {
    let args = parse_args()?;
    let paths = raw_paths(&args.dir, args.limit)?;
    let n = paths.len();

    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom: PlaneGeometry = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    drop(first);
    let noise = profile::noise_model_for(&camera, iso, levels);
    let px = geom.pixels();
    let white_u16 = levels.white as u16;

    println!("=== M54 clip-mask consequence harness (shipped operator, linked by path) ===");
    println!("stack           : {} ({n} frames)", args.dir.display());
    println!("camera          : {camera}   iso {iso:?}");
    println!(
        "levels          : black {} white {}   container max {CONTAINER_MAX_DN}",
        levels.black, levels.white
    );
    println!(
        "noise           : {:?}  sigma(0)={:.4}  sigma(7000)={:.3}  sigma(14848)={:.3} DN",
        noise.provenance,
        noise.green_luma_sigma(0.0),
        noise.green_luma_sigma(7000.0),
        noise.green_luma_sigma(14848.0)
    );
    println!("plane           : {}x{} = {px} px", geom.width, geom.height);
    println!(
        "gates           : {:?}   focus support radius {SUPPORT_RADIUS} + reg radius \
         {REGULARISER_RADIUS} = {}",
        args.gates,
        SUPPORT_RADIUS + REGULARISER_RADIUS
    );
    println!();

    // ---- pass one ----------------------------------------------------------
    let t0 = Instant::now();
    let mut stats = FocusStats::new(geom);
    // Arm B, at a ladder of propagation thresholds. `t = 0.0` is fact 203's
    // literal reading -- one pinned sample anywhere in the read extent condemns
    // the response. Larger `t` demands that a larger *fraction* of the support
    // be pinned. One pinned sample scores exactly `1/841 = 1.189e-3` in this
    // field, so the ladder brackets "one sample" through "half the support".
    let arm_b_thresholds: Vec<f32> = vec![0.0, 0.002, 0.01, 0.05, 0.10, 0.25, 0.50];
    let mut masked: Vec<MaskedStats> = arm_b_thresholds
        .iter()
        .map(|_| MaskedStats::new(px))
        .collect();
    let mut nullmask = MaskedStats::new(px); // power check for MaskedStats
    let mut census = ClipCensus::new(geom);
    let mut census_white = ClipCensus::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut clipped_white = vec![false; px];
    let mut field = FocusField::new(geom);
    let mut boxscratch = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];
    let mut dil_a = vec![0.0f32; px];
    let mut dil_b = vec![0.0f32; px];
    let mut valid = vec![true; px];
    let mut max_luma = vec![f32::NEG_INFINITY; px];
    let mut contaminated = vec![false; px];
    let mut n_invalid = vec![0u16; px];
    // Largest clipped-fraction-of-support any single frame put on this pixel.
    let mut max_frac = vec![0.0f32; px];
    // Per-CFA-plane "ever pinned" maps, so the luma's half-clipped quads cannot
    // be mistaken for a pinned pixel.
    let mut ever_plane = [vec![false; px], vec![false; px], vec![false; px], vec![
        false;
        px
    ]];

    for (i, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("frame {i}"))?;
        if frame.geometry() != geom {
            bail!("frame {i} geometry {:?} != {geom:?}", frame.geometry());
        }
        green_luma_with_clip(
            &frame,
            levels.black,
            CONTAINER_MAX_DN,
            &mut luma,
            &mut clipped,
        );
        // Same call at the usable white level. The luma written is identical --
        // pinned by `the_clip_mask_reports_clipping_without_altering_the_luma`
        // -- so this costs one scan and re-implements nothing.
        green_luma_with_clip(
            &frame,
            levels.black,
            white_u16,
            &mut luma,
            &mut clipped_white,
        );
        for (s, plane) in [CfaPlane::R, CfaPlane::G1, CfaPlane::B, CfaPlane::G2]
            .iter()
            .enumerate()
        {
            let ev = &mut ever_plane[s];
            for pyy in 0..geom.height {
                for pxx in 0..geom.width {
                    let (x, y) = geom.sensor_coord(*plane, pxx, pyy);
                    if frame.sample(x, y) >= CONTAINER_MAX_DN {
                        ev[pyy * geom.width + pxx] = true;
                    }
                }
            }
        }
        field.compute(&luma, &noise);
        regularise(field.values(), geom, &mut boxscratch, &mut reg);
        stats.fold(i as u16, &reg)?;
        census.fold(&clipped)?;
        census_white.fold(&clipped_white)?;
        for (m, l) in max_luma.iter_mut().zip(&luma) {
            if *l > *m {
                *m = *l;
            }
        }
        let any_clip = clipped.iter().any(|c| *c);
        if any_clip {
            // Dilate by the focus read extent, then by the regulariser, using
            // the shipped box filter. The result at a pixel is the **fraction
            // of that pixel's combined support that is pinned** -- exactly
            // `1/841 = 1.189e-3` for a single pinned sample -- so thresholding
            // it at 0 is the maximal ("one sample condemns the response")
            // reading of "propagate the mask", and thresholding it higher is a
            // strictly softer rule.
            for (d, c) in dil_a.iter_mut().zip(&clipped) {
                *d = if *c { 1.0 } else { 0.0 };
            }
            box_mean(&dil_a, geom, SUPPORT_RADIUS, &mut boxscratch, &mut dil_b);
            box_mean(
                &dil_b,
                geom,
                REGULARISER_RADIUS,
                &mut boxscratch,
                &mut dil_a,
            );
            for i2 in 0..px {
                if dil_a[i2] > 0.0 {
                    contaminated[i2] = true;
                    n_invalid[i2] += 1;
                    if dil_a[i2] > max_frac[i2] {
                        max_frac[i2] = dil_a[i2];
                    }
                }
            }
        } else {
            dil_a.iter_mut().for_each(|d| *d = 0.0);
        }
        for (bi, t) in arm_b_thresholds.iter().enumerate() {
            for i2 in 0..px {
                valid[i2] = dil_a[i2] <= *t;
            }
            masked[bi].fold(i as u16, &reg, Some(&valid));
        }
        nullmask.fold(i as u16, &reg, None);
        if i % 10 == 0 {
            eprint!("\rpass1 {i}/{n}   ");
        }
    }
    eprintln!("\rpass1 {n}/{n}  {:.1}s", t0.elapsed().as_secs_f64());

    // Power check for MaskedStats (rule 20): with nothing masked it must be the
    // shipped election, exactly.
    {
        let bad_f = (0..px)
            .filter(|&i| nullmask.best_focus[i] != stats.best_focus()[i])
            .count();
        let bad_i = (0..px)
            .filter(|&i| nullmask.best_index[i] != stats.best_index()[i])
            .count();
        if bad_f != 0 || bad_i != 0 {
            bail!(
                "MaskedStats with an all-valid mask disagrees with FocusStats: {bad_f} focus, \
                 {bad_i} index"
            );
        }
        println!(
            "election power check : MaskedStats(all valid) == FocusStats bit for bit at all {px} px"
        );
    }

    // ---- pass two ----------------------------------------------------------
    let t1 = Instant::now();
    let mut ests: Vec<Estimator> = args
        .gates
        .iter()
        .map(|g| Estimator::new(&stats, Gate::new(*g)))
        .collect();
    // Arm C: the same gate, folded through the winner-keyed censoring path.
    let mut cests: Vec<Estimator> = args
        .gates
        .iter()
        .map(|g| Estimator::new(&stats, Gate::new(*g)))
        .collect();
    let ng = args.gates.len();
    let mut adm_total: Vec<Vec<u16>> = vec![vec![0; px]; ng];
    let mut adm_clip: Vec<Vec<u16>> = vec![vec![0; px]; ng];
    let best_index = stats.best_index().to_vec();
    let best_focus = stats.best_focus().to_vec();
    // Winner records for both arms.
    let mut a_luma = vec![0.0f32; px];
    let mut a_g1 = vec![0.0f32; px];
    let mut a_g2 = vec![0.0f32; px];
    let mut a_clip = vec![false; px];
    let mut b_luma: Vec<Vec<f32>> = arm_b_thresholds.iter().map(|_| vec![0.0f32; px]).collect();
    let mut b_clip: Vec<Vec<bool>> = arm_b_thresholds
        .iter()
        .map(|_| vec![false; px])
        .collect();

    for (i, p) in paths.iter().enumerate() {
        let frame = strehl_raw::decode(p).with_context(|| format!("frame {i}"))?;
        green_luma_with_clip(
            &frame,
            levels.black,
            CONTAINER_MAX_DN,
            &mut luma,
            &mut clipped,
        );
        field.compute(&luma, &noise);
        regularise(field.values(), geom, &mut boxscratch, &mut reg);
        for e in ests.iter_mut() {
            e.fold(i as u16, &frame, &reg)?;
        }
        for e in cests.iter_mut() {
            e.fold_censored(i as u16, &frame, &reg, CONTAINER_MAX_DN)?;
        }
        for (gi, g) in args.gates.iter().enumerate() {
            let gate = Gate::new(*g);
            let (at, ac) = (&mut adm_total[gi], &mut adm_clip[gi]);
            for idx in 0..px {
                if best_index[idx] == i as u16 || gate.admits(reg[idx], best_focus[idx]) {
                    at[idx] += 1;
                    if clipped[idx] {
                        ac[idx] += 1;
                    }
                }
            }
        }
        let k = i as u16;
        for idx in 0..px {
            if best_index[idx] == k {
                let (pxx, pyy) = (idx % geom.width, idx / geom.width);
                let (x1, y1) = geom.sensor_coord(CfaPlane::G1, pxx, pyy);
                let (x2, y2) = geom.sensor_coord(CfaPlane::G2, pxx, pyy);
                a_g1[idx] = frame.sample(x1, y1) as f32;
                a_g2[idx] = frame.sample(x2, y2) as f32;
                a_luma[idx] = luma[idx];
                a_clip[idx] = clipped[idx];
            }
            if masked[0].best_index[idx] == k {
                b_clip[0][idx] = clipped[idx];
            }
        }
        for bi in 0..arm_b_thresholds.len() {
            let (bl, mb) = (&mut b_luma[bi], &masked[bi]);
            for idx in 0..px {
                if mb.best_index[idx] == k {
                    bl[idx] = luma[idx];
                }
            }
        }
        if i % 10 == 0 {
            eprint!("\rpass2 {i}/{n}   ");
        }
    }
    eprintln!("\rpass2 {n}/{n}  {:.1}s", t1.elapsed().as_secs_f64());
    println!();

    for (gi, e) in ests.iter().enumerate() {
        let bad = (0..px).filter(|&i| adm_total[gi][i] != e.n_eff()[i]).count();
        if bad != 0 {
            bail!(
                "gate {}: harness admission disagrees with Estimator::n_eff at {bad} px",
                args.gates[gi]
            );
        }
    }
    println!("admission cross-check: harness == Estimator::n_eff at all {px} px, all gates");
    println!();

    // ---- 1. census ---------------------------------------------------------
    let ever_c: Vec<bool> = (0..px).map(|i| census.ever_clipped(i)).collect();
    let n_ever = ever_c.iter().filter(|b| **b).count();
    let n_always = (0..px).filter(|&i| census.always_clipped(i)).count();
    let n_ever_w = (0..px).filter(|&i| census_white.ever_clipped(i)).count();
    let n_wina = a_clip.iter().filter(|b| **b).count();
    let n_contam = contaminated.iter().filter(|b| **b).count();
    let n_contam_clean = (0..px).filter(|&i| contaminated[i] && !ever_c[i]).count();
    let n_allbad = n_invalid.iter().filter(|c| **c as usize == n).count();
    let pctf = |k: usize| 100.0 * k as f64 / px as f64;

    println!("--- 1. census (MEASURED, all {n} frames) ---");
    println!(
        "ever   >= container {CONTAINER_MAX_DN} : {n_ever:>10} px  {:>8.4}%",
        pctf(n_ever)
    );
    println!(
        "always >= container {CONTAINER_MAX_DN} : {n_always:>10} px  {:>8.4}%",
        pctf(n_always)
    );
    println!(
        "ever   >= white     {white_u16:>5} : {n_ever_w:>10} px  {:>8.4}%",
        pctf(n_ever_w)
    );
    for (s, nm) in ["R", "G1", "B", "G2"].iter().enumerate() {
        let k = ever_plane[s].iter().filter(|b| **b).count();
        println!(
            "  of which plane {nm:<2}          : {k:>10} px  {:>8.4}%",
            pctf(k)
        );
    }
    println!(
        "winner frame clipped        : {n_wina:>10} px  {:>8.4}%",
        pctf(n_wina)
    );
    println!(
        "focus support contaminated  : {n_contam:>10} px  {:>8.4}%   ({n_contam_clean} never \
         clipped themselves, {n_allbad} contaminated in EVERY frame)",
        pctf(n_contam)
    );
    println!(
        "                              contamination / clipped = {:.2}x",
        if n_ever > 0 {
            n_contam as f64 / n_ever as f64
        } else {
            0.0
        }
    );
    println!();

    // ---- 2. does the argmax flee or seek clipped frames? -------------------
    println!("--- 2. the winner's clip rate against its own null (MEASURED) ---");
    println!(
        "    NULL: if clipping did not influence the election, P(winner clips at i) = \
         c(i)/N where"
    );
    println!(
        "    c(i) is the number of frames clipping at i. Summing that over the ever-clipped set \
         gives"
    );
    println!("    the expected count. Below the null = the argmax FLEES clipped frames.");
    let expected: f64 = (0..px)
        .filter(|&i| ever_c[i])
        .map(|i| census.clipped_frames(i) as f64 / n as f64)
        .sum();
    println!(
        "  ever-clipped px {n_ever}, expected winner-clips {expected:.1}, observed {n_wina}, \
         ratio {:.4}x",
        if expected > 0.0 {
            n_wina as f64 / expected
        } else {
            0.0
        }
    );
    println!();

    // ---- 3. the deficit -----------------------------------------------------
    println!("--- 3. deficit = winner green luma - merged green luma, raw DN (MEASURED) ---");
    println!(
        "{:>6} {:>12} {:>9} {:>8} {:>9} {:>9} {:>8} {:>8} {:>8} {:>8}",
        "gate", "population", "n_px", "mean n", "meanAdmC", "mean", "med", "p90", "p99", "sigma"
    );
    let (r_cc, r_ec, r_al, r_ac) = (&contaminated, &ever_c, &a_luma, &a_clip);
    for (gi, e) in ests.iter().enumerate() {
        let g = args.gates[gi];
        let bright = 0.5 * levels.white;
        let groups: Vec<(&str, Box<dyn Fn(usize) -> bool>)> = vec![
            ("WINCLIP", Box::new(move |i: usize| r_ac[i])),
            ("EVERCLIP", Box::new(move |i: usize| r_ec[i])),
            (
                "CONTAM-clean",
                Box::new(move |i: usize| r_cc[i] && !r_ec[i]),
            ),
            (
                "CTRL-bright",
                Box::new(move |i: usize| !r_ec[i] && !r_cc[i] && r_al[i] >= bright),
            ),
            (
                "CTRL-all",
                Box::new(move |i: usize| !r_ec[i] && !r_cc[i]),
            ),
        ];
        for (label, pred) in groups {
            let idxs: Vec<usize> = (0..px).filter(|&i| pred(i)).collect();
            if idxs.is_empty() {
                println!(
                    "{g:>6.2} {label:>12} {:>9} {:>8} {:>9} {:>9} {:>8} {:>8} {:>8} {:>8}",
                    0, "--", "--", "--", "--", "--", "--", "--"
                );
                continue;
            }
            let mut def: Vec<f32> = Vec::with_capacity(idxs.len());
            let (mut sn, mut sa, mut ss) = (0f64, 0f64, 0f64);
            for &i in &idxs {
                let merged = e.green_mean(i);
                def.push(a_luma[i] + levels.black - merged);
                sn += e.n_eff()[i] as f64;
                sa += adm_clip[gi][i] as f64;
                ss += noise.green_luma_sigma(merged - levels.black) as f64;
            }
            let k = idxs.len() as f64;
            let (mean, med, p90, p99, _mx) = stats_of(&mut def);
            println!(
                "{g:>6.2} {label:>12} {:>9} {:>8.3} {:>9.3} {:>9.2} {:>8.2} {:>8.2} {:>8.2} \
                 {:>8.2}",
                idxs.len(),
                sn / k,
                sa / k,
                mean,
                med,
                p90,
                p99,
                ss / k
            );
        }
        println!();
    }

    // ---- 4. per-plane dilution at a pinned sample ---------------------------
    println!("--- 4. per-CFA-plane: does the average dilute a pinned sample? (MEASURED) ---");
    println!(
        "    population: winner's own sample on that plane is pinned at {CONTAINER_MAX_DN}. The \
         merged"
    );
    println!(
        "    value there is {CONTAINER_MAX_DN} exactly iff no unpinned frame was admitted."
    );
    println!(
        "{:>6} {:>6} {:>10} {:>12} {:>10} {:>10} {:>10}",
        "gate", "plane", "n_px", "diluted px", "mean drop", "med drop", "max drop"
    );
    for (gi, e) in ests.iter().enumerate() {
        let g = args.gates[gi];
        for (plane, gwin) in [(CfaPlane::G1, &a_g1), (CfaPlane::G2, &a_g2)] {
            let idxs: Vec<usize> = (0..px)
                .filter(|&i| gwin[i] >= CONTAINER_MAX_DN as f32)
                .collect();
            if idxs.is_empty() {
                println!(
                    "{g:>6.2} {:>6} {:>10} {:>12} {:>10} {:>10} {:>10}",
                    format!("{plane:?}"),
                    0,
                    "--",
                    "--",
                    "--",
                    "--"
                );
                continue;
            }
            let mut drop: Vec<f32> = idxs
                .iter()
                .map(|&i| CONTAINER_MAX_DN as f32 - e.value(plane, i))
                .collect();
            let diluted = drop.iter().filter(|d| **d > 0.0).count();
            let (mean, med, _p90, _p99, mx) = stats_of(&mut drop);
            println!(
                "{g:>6.2} {:>6} {:>10} {:>12} {:>10.3} {:>10.3} {:>10.2}",
                format!("{plane:?}"),
                idxs.len(),
                diluted,
                mean,
                med,
                mx
            );
        }
    }
    println!();

    // ---- 5. arm A vs arm B: the propagated mask, at the election ------------
    println!("--- 5. ARM B: fact 203's propagated mask at the winner election (MEASURED) ---");
    // 5a. How much of a contaminated pixel's support is actually pinned? One
    // pinned sample scores 1/841 = 1.189e-3. If the median contaminated pixel
    // sits at that floor, the binary rule is condemning responses that were
    // perturbed by one sample in 841.
    {
        let mut fr: Vec<f32> = (0..px)
            .filter(|&i| contaminated[i])
            .map(|i| max_frac[i])
            .collect();
        if fr.is_empty() {
            println!("no contaminated pixels: arm B is identical to arm A by construction");
        } else {
            let (m, med, p90, p99, mx) = stats_of(&mut fr);
            println!(
                "clipped fraction of support (worst frame, over {} contaminated px):",
                fr.len()
            );
            println!(
                "  mean {:.5} med {:.5} p90 {:.5} p99 {:.5} max {:.5}   (one pinned sample = \
                 {:.5})",
                m,
                med,
                p90,
                p99,
                mx,
                1.0 / ((2.0 * SUPPORT_RADIUS as f32 + 1.0).powi(2))
            );
        }
    }
    println!();
    println!(
        "{:>7} {:>10} {:>9} {:>10} {:>10} {:>10} {:>10} {:>9} {:>9}",
        "thresh", "moved", "%plane", "mean|dDN|", "med|dDN|", "p90|dDN|", "max|dDN|", "everclip",
        "clean"
    );
    for (bi, t) in arm_b_thresholds.iter().enumerate() {
        let moved: Vec<usize> = (0..px)
            .filter(|&i| masked[bi].best_index[i] != best_index[i])
            .collect();
        if moved.is_empty() {
            println!(
                "{t:>7.3} {:>10} {:>9.4} {:>10} {:>10} {:>10} {:>10} {:>9} {:>9}",
                0, 0.0, "--", "--", "--", "--", 0, 0
            );
            continue;
        }
        let mut abs_dn: Vec<f32> = moved
            .iter()
            .map(|&i| (b_luma[bi][i] - a_luma[i]).abs())
            .collect();
        let (m_a, med_a, p90_a, _p99_a, mx_a) = stats_of(&mut abs_dn);
        let in_clip = moved.iter().filter(|&&i| ever_c[i]).count();
        println!(
            "{t:>7.3} {:>10} {:>9.4} {:>10.2} {:>10.2} {:>10.2} {:>10.2} {:>9} {:>9}",
            moved.len(),
            pctf(moved.len()),
            m_a,
            med_a,
            p90_a,
            mx_a,
            in_clip,
            moved.len() - in_clip
        );
    }
    println!();

    // Detail on the literal reading, t = 0.
    let moved: Vec<usize> = (0..px)
        .filter(|&i| masked[0].best_index[i] != best_index[i])
        .collect();
    println!(
        "detail at t = 0 (fact 203 literal): winner index moved at {} px  {:>8.4}% of the plane",
        moved.len(),
        pctf(moved.len())
    );
    if !moved.is_empty() {
        let mut d_idx: Vec<f32> = moved
            .iter()
            .map(|&i| (masked[0].best_index[i] as i32 - best_index[i] as i32).abs() as f32)
            .collect();
        let (m_i, med_i, p90_i, p99_i, mx_i) = stats_of(&mut d_idx);
        println!(
            "  |delta frame index|       : mean {m_i:.2} med {med_i:.0} p90 {p90_i:.0} p99 \
             {p99_i:.0} max {mx_i:.0}  (of {n} frames)"
        );
        let mut d_dn: Vec<f32> = moved.iter().map(|&i| b_luma[0][i] - a_luma[i]).collect();
        let (m_d, med_d, p90_d, p99_d, mx_d) = stats_of(&mut d_dn);
        println!(
            "  delta winner luma DN      : mean {m_d:+.2} med {med_d:+.2} p90 {p90_d:+.2} p99 \
             {p99_d:+.2} max {mx_d:+.2}"
        );
        let mut abs_dn: Vec<f32> = moved
            .iter()
            .map(|&i| (b_luma[0][i] - a_luma[i]).abs())
            .collect();
        let (m_a, med_a, p90_a, p99_a, mx_a) = stats_of(&mut abs_dn);
        println!(
            "  |delta| winner luma DN    : mean {m_a:.2} med {med_a:.2} p90 {p90_a:.2} p99 \
             {p99_a:.2} max {mx_a:.2}"
        );
        let in_clip = moved.iter().filter(|&&i| ever_c[i]).count();
        let in_contam = moved
            .iter()
            .filter(|&&i| contaminated[i] && !ever_c[i])
            .count();
        println!(
            "  where they moved          : {in_clip} ever-clipped, {in_contam} contaminated-clean, \
             {} elsewhere",
            moved.len() - in_clip - in_contam
        );
        // Split the signed delta by subset: the sign on never-clipped pixels is
        // the one that says whether arm B is systematically re-electing dimmer
        // or brighter frames at pixels that had nothing wrong with them.
        for (label, sel) in [
            ("ever-clipped   ", true),
            ("contam.-clean  ", false),
        ] {
            let mut d: Vec<f32> = moved
                .iter()
                .copied()
                .filter(|&i| ever_c[i] == sel)
                .map(|i| b_luma[0][i] - a_luma[i])
                .collect();
            if d.is_empty() {
                continue;
            }
            let nn = d.len();
            let (m, med, p90, _p99, mx) = stats_of(&mut d);
            println!(
                "  signed dDN, {label}  : n {nn} mean {m:+.2} med {med:+.2} p90 {p90:+.2} max \
                 {mx:+.2}"
            );
        }
        let b_clipped = moved.iter().filter(|&&i| b_clip[0][i]).count();
        let a_clipped = moved.iter().filter(|&&i| a_clip[i]).count();
        println!("  winner clipped, at moved px: arm A {a_clipped}, arm B {b_clipped}");
        // The population where the change is EXACTLY the output change.
        for (gi, e) in ests.iter().enumerate() {
            let alone: Vec<usize> = moved
                .iter()
                .copied()
                .filter(|&i| e.n_eff()[i] <= 1)
                .collect();
            if alone.is_empty() {
                println!("  gate {:.2}: no moved px at n_eff = 1", args.gates[gi]);
                continue;
            }
            let mut d: Vec<f32> = alone
                .iter()
                .map(|&i| (b_luma[0][i] - a_luma[i]).abs())
                .collect();
            let (m, med, p90, _p99, mx) = stats_of(&mut d);
            println!(
                "  gate {:.2}: {} of {} moved px have n_eff = 1, where |delta| IS the output \
                 change: mean {m:.2} med {med:.2} p90 {p90:.2} max {mx:.2} DN",
                args.gates[gi],
                alone.len(),
                moved.len()
            );
        }
    }
    println!();
    println!(
        "--- 6. scale: output is written over [black, white] = [{}, {}], range {} DN ---",
        levels.black,
        levels.white,
        levels.range()
    );
    println!("    1 DN = {:.1} of 65535 output levels", 65535.0 / levels.range());
    println!();

    // ---- 7. arm C: the shipped winner-keyed censoring fix -------------------
    println!("--- 7. ARM C: Estimator::fold_censored vs Estimator::fold (MEASURED) ---");
    println!(
        "{:>6} {:>10} {:>9} {:>11} {:>10} {:>10} {:>10} {:>11}",
        "gate", "changed", "%samples", "mean lift", "med lift", "p99 lift", "max lift", "contribflag"
    );
    for (gi, (e, c)) in ests.iter().zip(&cests).enumerate() {
        let mut lift: Vec<f32> = Vec::new();
        let mut contrib = 0usize;
        for p in [CfaPlane::R, CfaPlane::G1, CfaPlane::B, CfaPlane::G2] {
            for i in 0..px {
                let (a, b) = (e.value(p, i), c.value(p, i));
                if a != b {
                    lift.push(b - a);
                }
                if c.has_censored_contributor(p, i) {
                    contrib += 1;
                }
            }
        }
        if lift.is_empty() {
            println!(
                "{:>6.2} {:>10} {:>9.4} {:>11} {:>10} {:>10} {:>10} {:>11}",
                args.gates[gi], 0, 0.0, "--", "--", "--", "--", contrib
            );
            continue;
        }
        let n_ch = lift.len();
        let neg = lift.iter().filter(|v| **v < 0.0).count();
        assert_eq!(
            neg, 0,
            "censoring must only ever raise a value toward the pin, never lower it"
        );
        let (m, med, _p90, p99, mx) = stats_of(&mut lift);
        println!(
            "{:>6.2} {:>10} {:>9.4} {:>11.2} {:>10.2} {:>10.2} {:>10.2} {:>11}",
            args.gates[gi],
            n_ch,
            100.0 * n_ch as f64 / (4.0 * px as f64),
            m,
            med,
            p99,
            mx,
            contrib
        );
    }
    println!("    (every change is a rise toward the pin; asserted, not hoped)");
    Ok(())
}
