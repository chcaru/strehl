//! M60 — how much do the frames the merge **actually averages** disagree?
//!
//! Not a product path. This is the instrument for
//! `docs/research/M60-robustness-mask-at-merge-time.md` §1, kept beside the
//! shipped code so it goes stale loudly rather than quietly.
//!
//! It mirrors `merge_cmd.rs`'s two passes exactly — same decode, same
//! `green_luma_with_clip`, same `FocusField::compute`, same `regularise`, same
//! `Gate`, same `fold_censored` — and adds one thing the shipped path does not
//! have: `Estimator::track_disagreement`, the admitted-frame green-luma
//! variance. It is deliberately serial. A measurement that has to be argued
//! about is worth more correct than fast, and the worker plan is the part of
//! `merge_cmd.rs` most likely to be edited underneath this file.
//!
//! ```text
//! cargo run --release -p strehl-cli --example m60-disagreement -- <DIR> [--gate G]... [--limit N]
//! ```
//!
//! **Reads only.** It never writes to the stack directory.

use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::FocusField;
use strehl_core::merge::{Estimator, FocusStats, Gate, regularise};
use strehl_core::noise::NoiseModel;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Quantiles reported for every stack, so the tail is visible and not just the
/// mean. The 99th is the one criterion A3 is written against.
const QUANTILES: [f64; 7] = [0.01, 0.25, 0.50, 0.75, 0.95, 0.99, 0.999];

/// Fixed absolute octave edges on the winner's focus response, common to every
/// stack, so criterion A2' compares like with like.
///
/// The decile axis answers "how does chi2 vary *within* a stack"; it cannot
/// answer "does this stack disagree more than that one", because the deciles of
/// two stacks sit at different focus responses. These do not move.
const OCTAVES: [f32; 8] = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0];

/// Minimum pixels a stack must contribute to an octave for that octave to enter
/// the A2' ratio. Below this the per-octave mean is too noisy to divide.
const OCTAVE_MIN: u64 = 10_000;

/// Number of detail buckets, cut at **quantiles of the winner's own focus
/// response** rather than at fixed edges.
///
/// The first cut of this instrument used fixed half-decade edges anchored on
/// `FOCUS_NOISE_SD = 0.0152`, on the assumption that a regularised focus
/// response near the noise floor would read near that value. That was wrong:
/// `regularise` returns an SNR-like quantity, and on `109MSDCF` **every** pixel
/// reads >= 0.32, so four of the six buckets were empty and the flat-field
/// bucket that criterion A1c-i is written against did not exist. A fixture that
/// produces a constant where the test needs a spread ships permanently green
/// and looks like coverage (AGENTS rule 36), so the edges are now taken from
/// the data and every bucket is populated by construction.
const DETAIL_BUCKETS: usize = 10;

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
    /// Decode one frame and leave its regularised focus field in `self.reg`.
    ///
    /// Both passes go through here, for `merge_cmd.rs`'s own reason: pass two's
    /// gate is only meaningful if the field it compares was produced by the same
    /// arithmetic that elected the winner in pass one.
    fn field_for(&mut self, path: &std::path::Path) -> Result<strehl_raw::Frame> {
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
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let mut dir: Option<PathBuf> = None;
    let mut gates: Vec<f32> = Vec::new();
    let mut limit: Option<usize> = None;
    // A3's fixed absolute threshold: 109MSDCF's p99 chi2 at gate 1.0, measured
    // before this arm was written and not re-chosen afterwards.
    let mut threshold = 13.811f64;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--gate" => gates.push(
                args.next()
                    .context("--gate needs a value")?
                    .parse()
                    .context("--gate value")?,
            ),
            "--reach" => {
                threshold = args
                    .next()
                    .context("--reach needs a value")?
                    .parse()
                    .context("--reach value")?;
            }
            "--limit" => {
                limit = Some(
                    args.next()
                        .context("--limit needs a value")?
                        .parse()
                        .context("--limit value")?,
                );
            }
            other => dir = Some(PathBuf::from(other)),
        }
    }
    let dir = dir.context("usage: m60-disagreement <DIR> [--gate G].. [--limit N]")?;
    if gates.is_empty() {
        // The shipped default ladder, so the headline number is the one the
        // product would produce rather than one chosen for this milestone.
        gates = vec![0.5, 1.0, 2.0, 4.0];
    }

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
            "{} holds {} ARW files; need at least 2",
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

    println!("stack           : {}", dir.display());
    println!("frames          : {}", paths.len());
    println!("plane           : {} x {}", geom.width, geom.height);
    println!("iso / black     : {iso:?} / {black}");
    println!(
        "gates           : {}",
        gates
            .iter()
            .map(|g| format!("{g}"))
            .collect::<Vec<_>>()
            .join(" ")
    );

    let mut pipe = Pipeline {
        geom,
        noise,
        black,
        field: FocusField::new(geom),
        luma: vec![0.0; geom.pixels()],
        clipped: vec![false; geom.pixels()],
        box_scratch: vec![0.0; geom.pixels()],
        reg: vec![0.0; geom.pixels()],
    };

    // ---- pass one: the winner field, exactly as merge_cmd builds it --------
    // Also the per-frame mean luma above black, which costs nothing here and is
    // what criterion A1b's scalar gain is estimated from (fact 225: the mean
    // over *all* pixels, never a median over a subject-centred region).
    let mut stats = FocusStats::new(geom);
    let mut frame_mean = vec![0.0f64; paths.len()];
    // Per-pixel mean luma over every frame. A4 regresses each frame against it
    // to fit a two-parameter photometric correction; it is *not* used as a
    // disagreement reference, which is the thing M28 §1 measured to be 10x
    // worse than an adjacent-frame one.
    let mut ref_sum = vec![0.0f64; geom.pixels()];
    for (index, path) in paths.iter().enumerate() {
        let frame = pipe.field_for(path)?;
        stats.fold(index as u16, &pipe.reg)?;
        let mut acc = 0.0f64;
        for (r, &v) in ref_sum.iter_mut().zip(&pipe.luma) {
            acc += f64::from(v);
            *r += f64::from(v);
        }
        // `green_luma_with_clip` has already removed black, so this is signal.
        frame_mean[index] = acc / pipe.luma.len() as f64;
        drop(frame);
    }
    let inv_n = 1.0 / paths.len() as f64;
    for r in &mut ref_sum {
        *r *= inv_n;
    }
    let grand = frame_mean.iter().sum::<f64>() / frame_mean.len() as f64;
    let scale: Vec<f32> = frame_mean.iter().map(|m| (grand / m) as f32).collect();
    let lo = frame_mean.iter().cloned().fold(f64::INFINITY, f64::min);
    let hi = frame_mean.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    println!(
        "photometric ptp : {:.3}%  (per-frame mean signal, {lo:.1}..{hi:.1} DN above black)",
        100.0 * (hi - lo) / grand
    );

    // ---- pass two: two estimators per gate, raw and photometrically --------
    // ---- normalised, so A1b is a paired comparison on the same pixels ------
    let mut ests: Vec<Estimator> = gates
        .iter()
        .map(|g| {
            let mut e = Estimator::new(&stats, Gate::new(*g));
            e.track_disagreement();
            e
        })
        .collect();
    let mut norm: Vec<Estimator> = gates
        .iter()
        .map(|g| {
            let mut e = Estimator::new(&stats, Gate::new(*g));
            e.track_disagreement();
            e
        })
        .collect();
    // A4's arm: the same pixels again, under a *two*-parameter per-frame
    // correction instead of A1b's one.
    let mut affine: Vec<Estimator> = gates
        .iter()
        .map(|g| {
            let mut e = Estimator::new(&stats, Gate::new(*g));
            e.track_disagreement();
            e
        })
        .collect();
    let mut fits: Vec<(f32, f32)> = Vec::with_capacity(paths.len());
    // A4b: the offset analogue of fact 225's gain, `s` pinned to 1 so the fit
    // has exactly one degree of freedom and cannot buy a reduction by
    // collapsing the frame onto the reference. This is the arm that answers
    // M24 §5 as asked; A4's two-parameter fit can pass for reasons that are not
    // photometry, and on one stack it does.
    let mut offs: Vec<Estimator> = gates
        .iter()
        .map(|g| {
            let mut e = Estimator::new(&stats, Gate::new(*g));
            e.track_disagreement();
            e
        })
        .collect();

    for (index, path) in paths.iter().enumerate() {
        let frame = pipe.field_for(path)?;
        // Least squares of the all-frame mean on this frame's luma, over every
        // pixel: `ref ~ s*L + c`. Two parameters against 8.2M samples, so the
        // in-sample bias is 2/8.2e6 and is not the reason for any result below.
        let (mut sl, mut sr, mut sll, mut slr) = (0.0f64, 0.0f64, 0.0f64, 0.0f64);
        for (&l, &r) in pipe.luma.iter().zip(&ref_sum) {
            let l = f64::from(l);
            sl += l;
            sr += r;
            sll += l * l;
            slr += l * r;
        }
        let n = pipe.luma.len() as f64;
        let denom = n * sll - sl * sl;
        let (s, c) = if denom.abs() < 1e-9 {
            (1.0, 0.0)
        } else {
            let s = (n * slr - sl * sr) / denom;
            (s, (sr - s * sl) / n)
        };
        fits.push((s as f32, c as f32));
        for e in &mut ests {
            e.fold_censored(index as u16, &frame, &pipe.reg, CONTAINER_MAX_DN)?;
        }
        for e in &mut norm {
            e.fold_censored_probing_photometry(
                index as u16,
                &frame,
                &pipe.reg,
                CONTAINER_MAX_DN,
                scale[index],
                // `green_luma_with_clip` subtracts black, so the luma the
                // accumulator sees is already signal and the offset is zero.
                0.0,
            )?;
        }
        for e in &mut affine {
            e.fold_censored_probing_photometry(
                index as u16,
                &frame,
                &pipe.reg,
                CONTAINER_MAX_DN,
                s as f32,
                c as f32,
            )?;
        }
        for e in &mut offs {
            e.fold_censored_probing_photometry(
                index as u16,
                &frame,
                &pipe.reg,
                CONTAINER_MAX_DN,
                1.0,
                (grand - frame_mean[index]) as f32,
            )?;
        }
        drop(frame);
    }

    let slo = fits.iter().map(|f| f.0).fold(f32::INFINITY, f32::min);
    let shi = fits.iter().map(|f| f.0).fold(f32::NEG_INFINITY, f32::max);
    let clo = fits.iter().map(|f| f.1).fold(f32::INFINITY, f32::min);
    let chi = fits.iter().map(|f| f.1).fold(f32::NEG_INFINITY, f32::max);
    println!("A4 affine fit   : s in {slo:.4}..{shi:.4}, c in {clo:.2}..{chi:.2} DN");

    println!();
    println!("--- admitted-frame disagreement (MEASURED) ---");
    println!(
        "chi2 = s^2(admitted luma) / sigma_pred^2.  E[chi2] = 1 under \
         'the admitted frames differ only by sensor noise', for every n >= 2."
    );
    println!();
    let cx = Ctx {
        noise: &pipe.noise,
        black,
        geom,
        best_focus: stats.best_focus(),
        threshold,
    };
    for ((((g, e), n), a), o) in gates.iter().zip(&ests).zip(&norm).zip(&affine).zip(&offs) {
        report(*g, e, n, a, o, &cx);
    }
    Ok(())
}

/// Everything the report needs that is the same for every gate.
struct Ctx<'a> {
    noise: &'a NoiseModel,
    black: f32,
    geom: PlaneGeometry,
    best_focus: &'a [f32],
    /// A3's fixed absolute threshold, in chi2 units.
    threshold: f64,
}

fn report(
    gate: f32,
    e: &Estimator,
    norm: &Estimator,
    affine: &Estimator,
    offs: &Estimator,
    cx: &Ctx<'_>,
) {
    let (noise, black, geom, best_focus, threshold) =
        (cx.noise, cx.black, cx.geom, cx.best_focus, cx.threshold);
    let px = geom.pixels();
    // Cut the detail axis at deciles of the winner's focus response over the
    // measurable pixels only, so the buckets are populated by construction and
    // the axis means the same thing on every stack.
    let mut det: Vec<f32> = (0..px)
        .filter(|&i| e.n_eff()[i] >= 2)
        .map(|i| best_focus[i])
        .collect();
    if det.is_empty() {
        println!("gate {gate:>5}   NOTHING TO MEASURE: every pixel admitted exactly one frame.");
        println!();
        return;
    }
    det.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let edges: Vec<f32> = (0..DETAIL_BUCKETS)
        .map(|b| det[(det.len() - 1) * b / DETAIL_BUCKETS])
        .collect();

    let mut chi2: Vec<f64> = Vec::with_capacity(px);
    // Bucketed by n so the report can show that the aggregate is not being
    // carried by one n. `n_eff = 1` contributes to neither, by construction.
    let mut by_n: Vec<(u64, f64)> = vec![(0, 0.0); 8];
    // Bucketed by the winner's own focus response, which is the discriminator
    // between the two rival explanations for any excess: residual defocus among
    // admitted frames must vanish where there is no detail to be defocused,
    // whereas motion and photometric drift need not.
    let mut by_detail: Vec<(u64, f64)> = vec![(0, 0.0); DETAIL_BUCKETS];
    // A2': the same statistic on fixed absolute octaves, so two stacks can be
    // compared at matched detail rather than at matched rank.
    let mut by_octave: Vec<(u64, f64)> = vec![(0, 0.0); OCTAVES.len()];
    // A3: pixels over the fixed threshold, counted exactly.
    let mut over = 0u64;
    let mut norm_sum = 0.0f64;
    let mut norm_cnt = 0u64;
    let mut aff_sum = 0.0f64;
    let mut aff_cnt = 0u64;
    let mut off_sum = 0.0f64;
    let mut off_cnt = 0u64;
    for (i, &focus) in best_focus.iter().enumerate().take(px) {
        if let Some(c) = e.disagreement(noise, i, black) {
            chi2.push(c);
            let b = (e.n_eff()[i] as usize).min(7);
            by_n[b].0 += 1;
            by_n[b].1 += c;
            let d = edges.iter().rposition(|edge| focus >= *edge).unwrap_or(0);
            by_detail[d].0 += 1;
            by_detail[d].1 += c;
            let o = OCTAVES.iter().rposition(|edge| focus >= *edge).unwrap_or(0);
            by_octave[o].0 += 1;
            by_octave[o].1 += c;
            if c > threshold {
                over += 1;
            }
        }
        if let Some(c) = norm.disagreement(noise, i, black) {
            norm_sum += c;
            norm_cnt += 1;
        }
        if let Some(c) = affine.disagreement(noise, i, black) {
            aff_sum += c;
            aff_cnt += 1;
        }
        if let Some(c) = offs.disagreement(noise, i, black) {
            off_sum += c;
            off_cnt += 1;
        }
    }
    let exposure = e.disagreement_exposure();
    println!("gate {gate:>5}   tol {:.6}", e.gate().tolerance());
    println!(
        "  exposure      : {:.2}% of pixels have n_eff >= 2   ({:.2}% are n_eff = 1, where \
         chi2 is undefined and no mask can act)",
        100.0 * exposure,
        100.0 * (1.0 - exposure)
    );
    if chi2.is_empty() {
        println!("  NOTHING TO MEASURE: every pixel admitted exactly one frame.");
        println!();
        return;
    }
    let mean = chi2.iter().sum::<f64>() / chi2.len() as f64;
    chi2.sort_by(|a, b| a.partial_cmp(b).unwrap());
    print!("  mean chi2     : {mean:.4}   quantiles");
    for q in QUANTILES {
        let k = ((chi2.len() - 1) as f64 * q).round() as usize;
        print!("  p{q:<5.3}={:.3}", chi2[k]);
    }
    println!();
    assert_eq!(
        norm_cnt,
        chi2.len() as u64,
        "the photometric arm must cover the same pixels or A1b is not paired"
    );
    let normed = norm_sum / norm_cnt as f64;
    println!(
        "  A1b photometric: mean chi2 {normed:.4} after removing a per-frame scalar gain \
         ({:.1}% of the excess over 1.0 removed)",
        100.0 * (mean - normed) / (mean - 1.0)
    );
    assert_eq!(
        aff_cnt,
        chi2.len() as u64,
        "the affine arm must cover the same pixels or A4 is not paired"
    );
    let affined = aff_sum / aff_cnt as f64;
    println!(
        "  A4  affine     : mean chi2 {affined:.4} after removing a per-frame gain AND offset \
         ({:.1}% of the excess over 1.0 removed)",
        100.0 * (mean - affined) / (mean - 1.0)
    );
    assert_eq!(
        off_cnt,
        chi2.len() as u64,
        "the offset arm must cover the same pixels or A4b is not paired"
    );
    let offset_only = off_sum / off_cnt as f64;
    println!(
        "  A4b offset only: mean chi2 {offset_only:.4} after removing a per-frame offset, s == 1 \
         ({:.1}% of the excess over 1.0 removed)",
        100.0 * (mean - offset_only) / (mean - 1.0)
    );
    print!("  by n_eff      :");
    for (b, (cnt, sum)) in by_n.iter().enumerate().skip(2) {
        if *cnt > 0 {
            let label = if b == 7 {
                "7+".to_string()
            } else {
                b.to_string()
            };
            print!(
                "  n={label} {:.3} ({:.1}%)",
                sum / *cnt as f64,
                100.0 * *cnt as f64 / px as f64
            );
        }
    }
    println!();
    println!(
        "  detail range  : winner focus response {:.3} .. {:.3} (deciles below)",
        det[0],
        det[det.len() - 1]
    );
    print!("  by detail     :");
    for (b, (cnt, sum)) in by_detail.iter().enumerate() {
        if *cnt > 0 {
            print!("  >={:.2} {:.3}", edges[b], sum / *cnt as f64);
        }
    }
    println!();
    println!(
        "  A3 reach      : {:.4}% of ALL pixels are measurable AND chi2 > {threshold} \
         ({:.2}% of measurable)",
        100.0 * over as f64 / px as f64,
        100.0 * over as f64 / chi2.len() as f64
    );
    print!("  by octave     :");
    for (b, (cnt, sum)) in by_octave.iter().enumerate() {
        if *cnt >= OCTAVE_MIN {
            print!("  [{:>4}] {:.3} n={cnt}", OCTAVES[b], sum / *cnt as f64);
        }
    }
    println!();
    println!(
        "  memory        : {:.1} MB for this estimator",
        e.allocated_bytes() as f64 / 1e6
    );
    println!();
}
