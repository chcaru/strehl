//! M65 — does electing the winner on the **regularised** focus field rather than
//! the **raw** one change what the `Gate` admits?
//!
//! Not a product path. This is the instrument for
//! `docs/research/M65-election-gate-measured.md`, and it runs the measurement
//! M60c named and deliberately did not run: `n_eff` under regularised versus raw
//! election at a matched tolerance, on real frames.
//!
//! It mirrors `merge_cmd.rs`'s two passes exactly — same decode, same
//! `green_luma_with_clip`, same `FocusField::compute`, same `regularise`, same
//! `Gate` — and is deliberately serial, for `m60-disagreement.rs`'s reason: the
//! worker plan is the part of `merge_cmd.rs` most likely to be edited underneath
//! an example, and a measurement is worth more correct than fast.
//!
//! Four arms, all at the same gate ladder, over the same decoded bytes:
//!
//! | arm | winner index | reference value | field the gate reads | tolerance |
//! | --- | --- | --- | --- | --- |
//! | `R` | argmax of `reg` | `max reg` | `reg` | `tau` |
//! | `W` | argmax of `raw` | `reg` at that index | `reg` | `tau` |
//! | `X` | argmax of `raw` | `max raw` | `raw` | `tau` |
//! | `X'` | argmax of `raw` | `max raw` | `raw` | `tau * k_sd` |
//!
//! `W` is the surgical arm: tolerance, units, field and noise scale are all
//! identical to the shipped path and only the elected index differs. `X` turns
//! the regulariser off entirely at a matched *numeric* tolerance, which is
//! confounded because `FOCUS_NOISE_SD` is defined on the regularised field;
//! `X'` rescales the tolerance by the measured ratio of the two fields' own
//! pure-noise SDs to remove that confound.
//!
//! ```text
//! cargo run --release -p strehl-cli --example m65-election -- <DIR> [--gate G]... [--limit N]
//! ```
//!
//! **Reads only.** It never writes to the stack directory.

use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::{FocusField, SUPPORT_RADIUS};
use strehl_core::merge::{
    Estimator, FOCUS_NOISE_SD, FocusStats, Gate, REGULARISER_RADIUS, regularise,
};
use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// The gate the paired per-pixel statistics are reported at. The shipped
/// default, so the headline is the number the product would produce.
const REPORT_GATE: f32 = 4.0;

/// Sentinel matching `FocusStats`'s own "no frame has been folded here yet".
const NO_FRAME: u16 = u16::MAX;

/// The twelve seeds `merge::tests::the_focus_noise_constant_is_the_measured_one`
/// uses. Reproduced rather than re-chosen: `k_sd` is only a matched unit if its
/// numerator and denominator come off the same procedure the crate calibrated
/// `FOCUS_NOISE_SD` with.
const SEEDS: [u64; 12] = [
    0xC0FFEE,
    0x5EED,
    0xBADF00D,
    1,
    2,
    3,
    0xDEADBEEF,
    0x1234_5678,
    99,
    0xFACE,
    0xA5A5_A5A5,
    7,
];

/// Plane side for the pure-noise measurement. 512 is where the crate's own test
/// converged; smaller planes bias the sample SD low.
const NOISE_PLANE: usize = 512;

/// SplitMix64 feeding Box-Muller, byte-for-byte the generator in `merge.rs`'s
/// test module. A plain LCG here moved the measured constant by 1.30x across
/// seeds, which is why the algorithm is copied rather than swapped for whatever
/// is convenient.
struct Rng(u64);

impl Rng {
    fn new(seed: u64) -> Self {
        Rng(seed)
    }
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn uniform(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
    }
    fn normal(&mut self) -> f32 {
        let (u1, u2) = (self.uniform(), self.uniform());
        ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
    }
}

/// `Var(L) = (Var(G1) + Var(G2)) / 4 = read_dn^2 / 2`, so `read_dn = sqrt(2)`
/// gives `sigma_L = 1`. Same construction as `merge::tests::unit_sigma_model`.
fn unit_sigma_model() -> NoiseModel {
    let gain = 1e-4;
    let p = PlaneNoise {
        gain_dn_per_e: gain,
        read_noise_e: std::f32::consts::SQRT_2 / gain,
        levels: Levels {
            black: 0.0,
            white: 16383.0,
        },
    };
    NoiseModel::new([p; 4], 100.0, Provenance::Measured)
}

/// Interior SD of a pure-noise response: mean and standard error over seeds,
/// for the regularised and the unregularised field alike.
struct NoiseSd {
    reg_mean: f64,
    reg_sem: f64,
    raw_mean: f64,
    raw_sem: f64,
}

fn mean_and_sem(v: &[f64]) -> (f64, f64) {
    let n = v.len() as f64;
    let mean = v.iter().sum::<f64>() / n;
    let var = v.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (n - 1.0);
    (mean, (var / n).sqrt())
}

/// Interior sample SD of `field`, over the same margin the crate's test uses.
fn interior_sd(field: &[f32], g: PlaneGeometry, margin: usize) -> f64 {
    let mut vals = Vec::with_capacity((g.height - 2 * margin) * (g.width - 2 * margin));
    for y in margin..g.height - margin {
        vals.extend(
            field[y * g.width + margin..y * g.width + g.width - margin]
                .iter()
                .map(|v| f64::from(*v)),
        );
    }
    let n = vals.len() as f64;
    let mean = vals.iter().sum::<f64>() / n;
    (vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n - 1.0)).sqrt()
}

/// Re-run the crate's own `FOCUS_NOISE_SD` procedure, reading the SD off the
/// unregularised field as well as the regularised one.
///
/// The two numbers come off the *same* noise realisations, so the ratio is
/// paired.
fn measure_noise_sds() -> NoiseSd {
    let g = PlaneGeometry {
        width: NOISE_PLANE,
        height: NOISE_PLANE,
    };
    let noise = unit_sigma_model();
    let margin = SUPPORT_RADIUS + REGULARISER_RADIUS;
    let mut field = FocusField::new(g);
    let mut scratch = vec![0.0; g.pixels()];
    let mut reg = vec![0.0; g.pixels()];
    let (mut regs, mut raws) = (Vec::new(), Vec::new());
    for seed in SEEDS {
        let mut rng = Rng::new(seed);
        let luma: Vec<f32> = (0..g.pixels()).map(|_| rng.normal()).collect();
        field.compute(&luma, &noise);
        raws.push(interior_sd(field.values(), g, margin));
        regularise(field.values(), g, &mut scratch, &mut reg);
        regs.push(interior_sd(&reg, g, margin));
    }
    let (reg_mean, reg_sem) = mean_and_sem(&regs);
    let (raw_mean, raw_sem) = mean_and_sem(&raws);
    NoiseSd {
        reg_mean,
        reg_sem,
        raw_mean,
        raw_sem,
    }
}

/// One election: which frame won at each pixel, the value the gate compares
/// against, and which field it compares. Shared across the gate ladder, because
/// an election does not depend on the gate.
struct Election {
    win: Vec<u16>,
    reference: Vec<f32>,
    reads_reg: bool,
}

/// One arm: an election plus a multiplier on the gate threshold.
struct ArmSpec {
    name: &'static str,
    election: usize,
    gate_scale: f32,
}

struct Pipeline {
    geom: PlaneGeometry,
    noise: NoiseModel,
    black: f32,
    field: FocusField,
    luma: Vec<f32>,
    clipped: Vec<bool>,
    box_scratch: Vec<f32>,
    raw: Vec<f32>,
    reg: Vec<f32>,
}

impl Pipeline {
    /// Decode one frame and leave its unregularised focus field in `self.raw`
    /// and its regularised one in `self.reg`.
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
        self.raw.copy_from_slice(self.field.values());
        regularise(
            self.field.values(),
            self.geom,
            &mut self.box_scratch,
            &mut self.reg,
        );
        Ok(frame)
    }
}

fn mean_n(n: &[u16]) -> f64 {
    n.iter().map(|v| f64::from(*v)).sum::<f64>() / n.len() as f64
}

fn frac_singleton(n: &[u16]) -> f64 {
    n.iter().filter(|v| **v == 1).count() as f64 / n.len() as f64
}

/// Mean, range and non-zero fraction of the signed per-pixel difference `a - b`.
/// Reported as counts rather than interpolated quantiles, because the quantity
/// is discrete.
fn diff_summary(a: &[u16], b: &[u16]) -> (f64, i64, i64, f64) {
    let mut sum = 0i64;
    let (mut lo, mut hi) = (i64::MAX, i64::MIN);
    let mut nonzero = 0u64;
    for (x, y) in a.iter().zip(b) {
        let d = i64::from(*x) - i64::from(*y);
        sum += d;
        lo = lo.min(d);
        hi = hi.max(d);
        if d != 0 {
            nonzero += 1;
        }
    }
    let n = a.len() as f64;
    (sum as f64 / n, lo, hi, nonzero as f64 / n)
}

fn parse_args() -> Result<(PathBuf, Vec<f32>, Option<usize>)> {
    let mut args = std::env::args().skip(1);
    let mut dir: Option<PathBuf> = None;
    let mut gates: Vec<f32> = Vec::new();
    let mut limit: Option<usize> = None;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--gate" => gates.push(
                args.next()
                    .context("--gate needs a value")?
                    .parse()
                    .context("--gate value")?,
            ),
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
    let dir = dir.context("usage: m65-election <DIR> [--gate G].. [--limit N]")?;
    if gates.is_empty() {
        // The shipped ladder, plus the two endpoints the pre-registration's
        // control K5 needs: 0 must collapse every arm to a selector, and a very
        // wide gate must saturate every arm at N.
        gates = vec![0.0, 0.5, 1.0, 2.0, 4.0, 64.0];
    }
    Ok((dir, gates, limit))
}

fn main() -> Result<()> {
    let (dir, gates, limit) = parse_args()?;

    // ---- K1: the unit-matching constant, by the crate's own procedure ------
    let sd = measure_noise_sds();
    let k_sd = sd.raw_mean / sd.reg_mean;
    let deviation = ((sd.reg_mean - f64::from(FOCUS_NOISE_SD)) / sd.reg_sem).abs();
    println!("--- K1: pure-noise response SD, the crate's own procedure ---");
    println!(
        "regularised     : {:.6e} +/- {:.3e}  (declared {:.6e}, {deviation:.2} SEM away)",
        sd.reg_mean, sd.reg_sem, FOCUS_NOISE_SD
    );
    println!(
        "unregularised   : {:.6e} +/- {:.3e}",
        sd.raw_mean, sd.raw_sem
    );
    println!("k_sd            : {k_sd:.5}  (raw / reg; arm X' scales the gate by this)");
    println!(
        "K1              : {}",
        if deviation < 4.0 { "PASS" } else { "FAIL" }
    );
    if deviation >= 4.0 {
        bail!("K1 failed; no arm number below it is believable");
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
    let px = geom.pixels();
    let nframes = paths.len();

    println!();
    println!("stack           : {}", dir.display());
    println!("frames          : {nframes}");
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
        luma: vec![0.0; px],
        clipped: vec![false; px],
        box_scratch: vec![0.0; px],
        raw: vec![0.0; px],
        reg: vec![0.0; px],
    };

    // ---- pass one: three winner fields off the same decoded bytes ----------
    let mut stats_reg = FocusStats::new(geom);
    let mut stats_raw = FocusStats::new(geom);
    // Arm W's reference: the *regularised* response of the frame the *raw*
    // argmax elected. `FocusStats` cannot carry a payload, so it is tracked here
    // with the identical tie-break, and K6 checks the tracking reproduces
    // `FocusStats::best_index` exactly.
    let mut raw_best = vec![f32::NEG_INFINITY; px];
    let mut raw_win = vec![NO_FRAME; px];
    let mut reg_at_raw_win = vec![f32::NEG_INFINITY; px];
    for (index, path) in paths.iter().enumerate() {
        let k = index as u16;
        let frame = pipe.field_for(path)?;
        stats_reg.fold(k, &pipe.reg)?;
        stats_raw.fold(k, &pipe.raw)?;
        let track = raw_best
            .iter_mut()
            .zip(raw_win.iter_mut())
            .zip(reg_at_raw_win.iter_mut())
            .zip(pipe.raw.iter())
            .zip(pipe.reg.iter());
        for ((((best, win), payload), &f), &r) in track {
            // `FocusStats::beats`, restated: ties go to the lower frame index.
            if f > *best || (f == *best && k < *win) {
                *best = f;
                *win = k;
                *payload = r;
            }
        }
        drop(frame);
    }

    // ---- K6 ---------------------------------------------------------------
    let k6_bad = raw_win
        .iter()
        .zip(stats_raw.best_index())
        .filter(|(a, b)| a != b)
        .count();
    println!();
    println!("--- K6: the tracked raw election reproduces FocusStats' tie-break ---");
    println!(
        "mismatched px   : {k6_bad} of {px}  {}",
        if k6_bad == 0 { "PASS" } else { "FAIL" }
    );
    if k6_bad != 0 {
        bail!("K6 failed; arm W's reference is not the shipped election");
    }

    // ---- D4: the index-map quantity, measured next to the value one --------
    let agree: Vec<bool> = raw_win
        .iter()
        .zip(stats_reg.best_index())
        .map(|(a, b)| a == b)
        .collect();
    let disagree = agree.iter().filter(|a| !**a).count();
    println!();
    println!("--- D4: election disagreement rate (an INDEX-map quantity) ---");
    println!(
        "win_R != win_W  : {:.4}% of the plane ({disagree} of {px})",
        100.0 * disagree as f64 / px as f64
    );

    // ---- the arms ---------------------------------------------------------
    let elections = [
        Election {
            win: stats_reg.best_index().to_vec(),
            reference: stats_reg.best_focus().to_vec(),
            reads_reg: true,
        },
        Election {
            win: raw_win.clone(),
            reference: reg_at_raw_win,
            reads_reg: true,
        },
        Election {
            win: raw_win,
            reference: stats_raw.best_focus().to_vec(),
            reads_reg: false,
        },
    ];
    let arms = [
        ArmSpec {
            name: "R",
            election: 0,
            gate_scale: 1.0,
        },
        ArmSpec {
            name: "W",
            election: 1,
            gate_scale: 1.0,
        },
        ArmSpec {
            name: "X",
            election: 2,
            gate_scale: 1.0,
        },
        ArmSpec {
            name: "X'",
            election: 2,
            gate_scale: k_sd as f32,
        },
    ];
    // `counts[a * gates.len() + g]` is arm `a`'s per-pixel n_eff at gate `g`.
    let mut counts: Vec<Vec<u16>> = (0..arms.len() * gates.len())
        .map(|_| vec![0u16; px])
        .collect();

    // ---- pass two: every arm at every gate, one decode budget --------------
    // K2's witnesses: the shipped `Estimator` at the report gate, for the two
    // arms expressible as a `FocusStats` plus a `Gate`.
    let mut est_r = Estimator::new(&stats_reg, Gate::new(REPORT_GATE));
    let mut est_x = Estimator::new(&stats_raw, Gate::new(REPORT_GATE));

    for (index, path) in paths.iter().enumerate() {
        let k = index as u16;
        let frame = pipe.field_for(path)?;
        for (a, arm) in arms.iter().enumerate() {
            let e = &elections[arm.election];
            let field: &[f32] = if e.reads_reg { &pipe.reg } else { &pipe.raw };
            for (g, &t) in gates.iter().enumerate() {
                let gate = Gate::new(t * arm.gate_scale);
                let n = &mut counts[a * gates.len() + g];
                let it = n
                    .iter_mut()
                    .zip(e.win.iter())
                    .zip(e.reference.iter())
                    .zip(field.iter());
                for (((slot, &win), &reference), &f) in it {
                    if win == k || gate.admits(f, reference) {
                        *slot += 1;
                    }
                }
            }
        }
        est_r.fold(k, &frame, &pipe.reg)?;
        est_x.fold(k, &frame, &pipe.raw)?;
        drop(frame);
    }

    let idx = |name: &str, t: f32| -> usize {
        let a = arms.iter().position(|s| s.name == name).expect("arm");
        let g = gates.iter().position(|&x| x == t).expect("gate");
        a * gates.len() + g
    };

    // ---- K2 ---------------------------------------------------------------
    let manual_r = mean_n(&counts[idx("R", REPORT_GATE)]);
    let manual_x = mean_n(&counts[idx("X", REPORT_GATE)]);
    let (ship_r, ship_x) = (est_r.mean_n_eff(), est_x.mean_n_eff());
    println!();
    println!(
        "--- K2: the harness's counter against the shipped Estimator (gate {REPORT_GATE}) ---"
    );
    println!("arm R           : harness {manual_r:.9}  Estimator {ship_r:.9}");
    println!("arm X           : harness {manual_x:.9}  Estimator {ship_x:.9}");
    let k2 = manual_r == ship_r && manual_x == ship_x;
    println!("K2              : {}", if k2 { "PASS" } else { "FAIL" });
    if !k2 {
        bail!("K2 failed; the harness is not counting what the merge counts");
    }

    // ---- K4 ---------------------------------------------------------------
    let mut k4_bad = 0usize;
    for &t in &gates {
        let (r, w) = (&counts[idx("R", t)], &counts[idx("W", t)]);
        k4_bad += r
            .iter()
            .zip(w.iter())
            .zip(agree.iter())
            .filter(|((a, b), same)| **same && a != b)
            .count();
    }
    println!();
    println!("--- K4: where the elections agree, the arms must agree exactly ---");
    println!(
        "violations      : {k4_bad} over {} gates  {}",
        gates.len(),
        if k4_bad == 0 { "PASS" } else { "FAIL" }
    );

    // ---- K5 ---------------------------------------------------------------
    println!();
    println!("--- K5: can the plant express the failure at both ends? ---");
    let ends = gates.contains(&0.0) && gates.contains(&64.0);
    for arm in &arms {
        if !ends {
            println!(
                "arm {:<3}         : SKIPPED, the ladder lacks 0 or 64",
                arm.name
            );
            continue;
        }
        let lo = mean_n(&counts[idx(arm.name, 0.0)]);
        let hi = mean_n(&counts[idx(arm.name, 64.0)]);
        // The pre-registered text is "mean n_eff = 1.000 at gate 0", read at the
        // three decimals it is written to. Exact float ties in the response do
        // admit a second frame at a handful of pixels, which is a property of
        // the data and not of the arm.
        let floor_ok = (lo - 1.0).abs() < 5e-4;
        let ceil_ok = hi >= 0.95 * nframes as f64;
        println!(
            "arm {:<3}         : gate 0 -> {lo:.6} [{}]   gate 64 -> {hi:.4} of {nframes} [{}]  {}",
            arm.name,
            if floor_ok { "ok" } else { "NOT MET" },
            if ceil_ok { "ok" } else { "NOT MET" },
            if floor_ok && ceil_ok { "PASS" } else { "FAIL" }
        );
    }
    println!("(span, post-hoc: the range each arm's ladder actually covers)");
    for arm in &arms {
        let m: Vec<f64> = gates
            .iter()
            .map(|&t| mean_n(&counts[idx(arm.name, t)]))
            .collect();
        let lo = m.iter().cloned().fold(f64::INFINITY, f64::min);
        let hi = m.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        println!(
            "arm {:<3}         : {lo:.4} .. {hi:.4} of {nframes}  ({:.2}x)",
            arm.name,
            hi / lo
        );
    }

    // ---- the measurement --------------------------------------------------
    println!();
    println!("--- MEAN n_eff BY ARM AND GATE (MEASURED) ---");
    println!("  gate         R          W          X         X'  |   rho_W   rho_X  rho_X'");
    for &t in &gates {
        let m: Vec<f64> = arms
            .iter()
            .map(|a| mean_n(&counts[idx(a.name, t)]))
            .collect();
        println!(
            "{t:>6.2}  {:>9.5}  {:>9.5}  {:>9.5}  {:>9.5}  |  {:>6.4}  {:>6.4}  {:>6.4}",
            m[0],
            m[1],
            m[2],
            m[3],
            m[1] / m[0],
            m[2] / m[0],
            m[3] / m[0]
        );
    }

    println!();
    println!("--- n_eff == 1 FRACTION (the plane on which the merge is a selector) ---");
    println!("  gate         R          W          X         X'");
    for &t in &gates {
        let f: Vec<f64> = arms
            .iter()
            .map(|a| 100.0 * frac_singleton(&counts[idx(a.name, t)]))
            .collect();
        println!(
            "{t:>6.2}  {:>8.4}%  {:>8.4}%  {:>8.4}%  {:>8.4}%",
            f[0], f[1], f[2], f[3]
        );
    }

    println!();
    println!("--- PAIRED PER-PIXEL DIFFERENCE AGAINST ARM R, at gate {REPORT_GATE} ---");
    let r = idx("R", REPORT_GATE);
    for name in ["W", "X", "X'"] {
        let (mean, lo, hi, nz) = diff_summary(&counts[idx(name, REPORT_GATE)], &counts[r]);
        println!(
            "{name:<3} - R         : mean {mean:>+9.5}  range [{lo:>+4}, {hi:>+4}]  non-zero on {:.4}% of px",
            100.0 * nz
        );
    }

    Ok(())
}
