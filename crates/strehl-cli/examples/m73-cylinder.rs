//! M73 — dump the per-pixel election and admitted-set fields for the cylinder
//! invariant test.
//!
//! # What this is for
//!
//! M67 measured admission correctness (`H`) against a **simulated** stack, where
//! the per-pixel true best-focus index `k*(x, y)` is known by construction. No
//! stack in the corpus carries a `k*`, so `H` cannot be reproduced on real
//! frames — with one exception, which M67 found and designed and this milestone
//! runs.
//!
//! The `wrapped-text` brackets photograph text wrapped around a bottle. A
//! bottle's label region is a **right circular cylinder**, and for a cylinder
//! with its axis along one image direction, `k*` is a function of the *across*
//! coordinate alone:
//!
//! ```text
//!     k*(x, y) = k*(x)            for all y
//! ```
//!
//! That is an invariant of the geometry, not a fitted model. It needs no radius,
//! no distance and no profile. Nothing on that axis can be tuned into agreement,
//! which is what makes it stronger than fitting a geometry and scoring residuals
//! against one's own fit.
//!
//! # What this binary does and does not decide
//!
//! It decides nothing. It is a **dumper**. Every threshold, every residual and
//! every verdict lives in `experiments/M73-cylinder/src/*.py`, scored against
//! criteria committed before this ran. The split is deliberate: the scoring
//! layer changed several times while the field definitions did not, and a
//! harness that also scores invites the scoring to drift toward the answer.
//!
//! It reproduces `merge_cmd.rs`'s two-pass structure exactly — the same decode,
//! the same `green_luma_with_clip`, the same `FocusField::compute`, the same
//! `regularise`, the same `FocusStats` tie-break and the same `Gate::admits`.
//! `m65-election.rs` established that path on real stacks; this is that path
//! with per-pixel witnesses written to disk instead of summarised to stdout.
//!
//! # Arms
//!
//! * **E** — the shipped estimating merge: election on the **regularised**
//!   field, gate on the regularised field at `DEFAULT_GATE`.
//! * **A** — `ArgmaxBaseline`: election on the **raw** field. This is the arm
//!   M67's transferred prediction is about (its `A`, mean `|win - k*| =
//!   0.81473` against `E`'s `0.71747`).
//! * **A'** — arm A's election with a gate on the raw field, scaled by
//!   `k_sd = sd(raw) / sd(reg)` so the two gates are the same number of noise
//!   SDs. `strehl stack` itself admits a singleton, so this arm is a
//!   *construction*, not a shipped path, and the report says so.
//!
//! # Controls that run here rather than in Python
//!
//! * **K1** re-runs the crate's own `FOCUS_NOISE_SD` procedure and refuses to
//!   continue if the measured constant has moved. It also yields `k_sd`.
//! * **K2** checks this harness's admitted-frame counter against the shipped
//!   `Estimator::mean_n_eff()` at `f64` equality. A counter that disagrees with
//!   the merge is not measuring the merge.
//! * **K3** checks the tracked admitted-set bounds bracket the winner, which
//!   `Gate::admits` guarantees and a dumping bug would break.
//!
//! # Usage
//!
//! ```text
//! cargo run --release --example m73-cylinder -- --dir <stack> --out <prefix> [--limit N]
//! ```
//!
//! Writes `<prefix>.json` (header) and `<prefix>.<field>.bin` (native-endian
//! per-pixel arrays, row-major, plane geometry from the header).

use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::{FocusField, SUPPORT_RADIUS};
use strehl_core::merge::{
    DEFAULT_GATE, Estimator, FOCUS_NOISE_SD, FocusStats, Gate, REGULARISER_RADIUS, regularise,
};
use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Sentinel for "no frame has won here yet". `u16::MAX` is unreachable as a
/// frame index for any stack this project can hold in memory.
const NO_FRAME: u16 = u16::MAX;

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

/// Plane side for the pure-noise measurement, matching `m65-election.rs`: 512 is
/// where the crate's own test converged and smaller planes bias the SD low.
const NOISE_PLANE: usize = 512;

/// SplitMix64 feeding Box-Muller, byte-for-byte the generator in `merge.rs`'s
/// test module. Copied rather than substituted because `m65-election.rs`
/// measured a 1.30x spread across generators.
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

/// `Var(L) = read_dn^2 / 2`, so `read_dn = sqrt(2)` gives `sigma_L = 1`.
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

fn mean_and_sem(v: &[f64]) -> (f64, f64) {
    let n = v.len() as f64;
    let mean = v.iter().sum::<f64>() / n;
    let var = v.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (n - 1.0);
    (mean, (var / n).sqrt())
}

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

struct NoiseSd {
    reg_mean: f64,
    reg_sem: f64,
    raw_mean: f64,
    raw_sem: f64,
}

/// Re-run the crate's own `FOCUS_NOISE_SD` procedure on both fields, off the
/// same noise realisations so the ratio is paired.
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
    /// Decode one frame; leave the unregularised focus field in `self.raw` and
    /// the regularised one in `self.reg`.
    ///
    /// Both passes go through here for `merge_cmd.rs`'s own reason: pass two's
    /// gate is only meaningful if the field it compares was produced by the same
    /// arithmetic that elected the winner in pass one.
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

/// Gate ladder for arm E. `DEFAULT_GATE` is the shipped value and the only one
/// any registered decision reads; the rest exist so the report can show what the
/// gate does as it opens, rather than assert it. `m65-election.rs` swept a
/// ladder for the same reason.
const GATE_LADDER: [f32; 7] = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0];

/// Per-pixel admitted-set witnesses for one arm.
///
/// `lo`/`hi` are the extreme admitted frame indices and `sum` their total, so
/// Python can form both the *span* (M67's `devmax` analogue) and the *centre*
/// (where the merge's weight actually sits) without a third pass.
struct Admitted {
    n: Vec<u16>,
    lo: Vec<u16>,
    hi: Vec<u16>,
    sum: Vec<u32>,
}

impl Admitted {
    fn new(px: usize) -> Self {
        Admitted {
            n: vec![0; px],
            lo: vec![NO_FRAME; px],
            hi: vec![0; px],
            sum: vec![0; px],
        }
    }

    fn fold(&mut self, k: u16, win: &[u16], reference: &[f32], field: &[f32], gate: Gate) {
        let it = self
            .n
            .iter_mut()
            .zip(self.lo.iter_mut())
            .zip(self.hi.iter_mut())
            .zip(self.sum.iter_mut())
            .zip(win.iter())
            .zip(reference.iter())
            .zip(field.iter());
        for ((((((n, lo), hi), sum), &w), &r), &f) in it {
            // `merge_cmd.rs`: the winner is admitted unconditionally, everything
            // else on the gate.
            if w == k || gate.admits(f, r) {
                *n += 1;
                *sum += u32::from(k);
                if k < *lo {
                    *lo = k;
                }
                if k > *hi {
                    *hi = k;
                }
            }
        }
    }
}

fn dump_u16(prefix: &Path, name: &str, v: &[u16]) -> Result<()> {
    let path = prefix.with_extension(format!("{name}.bin"));
    let mut w = BufWriter::new(File::create(&path).with_context(|| format!("{}", path.display()))?);
    for x in v {
        w.write_all(&x.to_ne_bytes())?;
    }
    w.flush()?;
    Ok(())
}

fn dump_u32(prefix: &Path, name: &str, v: &[u32]) -> Result<()> {
    let path = prefix.with_extension(format!("{name}.bin"));
    let mut w = BufWriter::new(File::create(&path).with_context(|| format!("{}", path.display()))?);
    for x in v {
        w.write_all(&x.to_ne_bytes())?;
    }
    w.flush()?;
    Ok(())
}

fn dump_f32(prefix: &Path, name: &str, v: &[f32]) -> Result<()> {
    let path = prefix.with_extension(format!("{name}.bin"));
    let mut w = BufWriter::new(File::create(&path).with_context(|| format!("{}", path.display()))?);
    for x in v {
        w.write_all(&x.to_ne_bytes())?;
    }
    w.flush()?;
    Ok(())
}

fn mean_n(n: &[u16]) -> f64 {
    n.iter().map(|v| f64::from(*v)).sum::<f64>() / n.len() as f64
}

fn parse_args() -> Result<(PathBuf, PathBuf, Option<usize>)> {
    let mut args = std::env::args().skip(1);
    let (mut dir, mut out, mut limit) = (None, None, None);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--dir" => dir = args.next().map(PathBuf::from),
            "--out" => out = args.next().map(PathBuf::from),
            "--limit" => {
                limit = Some(
                    args.next()
                        .context("--limit needs a value")?
                        .parse::<usize>()
                        .context("--limit must be an integer")?,
                )
            }
            other => bail!("unknown argument {other}"),
        }
    }
    Ok((
        dir.context("--dir <stack directory> is required")?,
        out.context("--out <prefix> is required")?,
        limit,
    ))
}

fn main() -> Result<()> {
    let (dir, out, limit) = parse_args()?;

    // ---- K1: the crate's own noise constant, and the raw/reg unit ratio ----
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
    println!("k_sd            : {k_sd:.5}  (raw / reg; arm A' scales its gate by this)");
    println!(
        "K1              : {}",
        if deviation < 4.0 { "PASS" } else { "FAIL" }
    );
    if deviation >= 4.0 {
        bail!("K1 failed; no number below it is believable");
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
    let camera = first.camera.clone();
    let iso = first.iso;
    let black = levels.black;
    drop(first);
    let px = geom.pixels();
    let nframes = paths.len();

    println!();
    println!("stack           : {}", dir.display());
    println!("frames          : {nframes}");
    println!("plane           : {} x {}", geom.width, geom.height);
    println!("camera / iso    : {camera} / {iso:?}");
    println!("black / white   : {} / {}", levels.black, levels.white);
    println!("gate E          : {DEFAULT_GATE}  (the shipped default)");
    println!(
        "gate A'         : {:.5}  (= {DEFAULT_GATE} * k_sd)",
        DEFAULT_GATE * k_sd as f32
    );
    println!(
        "margin          : {}  (SUPPORT_RADIUS + REGULARISER_RADIUS)",
        SUPPORT_RADIUS + REGULARISER_RADIUS
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

    // ---- pass one: both elections off the same decoded bytes ---------------
    let t1 = Instant::now();
    let mut stats_reg = FocusStats::new(geom);
    let mut stats_raw = FocusStats::new(geom);
    let mut mean_luma = vec![0.0f64; px];
    for (index, path) in paths.iter().enumerate() {
        let k = index as u16;
        let frame = pipe.field_for(path)?;
        stats_reg.fold(k, &pipe.reg)?;
        stats_raw.fold(k, &pipe.raw)?;
        for (acc, &l) in mean_luma.iter_mut().zip(pipe.luma.iter()) {
            *acc += f64::from(l);
        }
        drop(frame);
        if index % 20 == 0 {
            eprintln!("  pass 1: {index}/{nframes}");
        }
    }
    let pass1 = t1.elapsed().as_secs_f64();
    println!();
    println!("--- pass one (MEASURED) ---");
    println!(
        "wall clock      : {pass1:.3} s  ({:.1} ms/frame)",
        1000.0 * pass1 / nframes as f64
    );

    let win_e = stats_reg.best_index().to_vec();
    let win_a = stats_raw.best_index().to_vec();
    let ref_e = stats_reg.best_focus().to_vec();
    let ref_a = stats_raw.best_focus().to_vec();

    let disagree = win_e
        .iter()
        .zip(win_a.iter())
        .filter(|(a, b)| a != b)
        .count();
    println!(
        "win_E != win_A  : {:.4}% of the plane ({disagree} of {px})",
        100.0 * disagree as f64 / px as f64
    );

    // ---- pass two: admitted sets for E and A' ------------------------------
    let gate_e = Gate::new(DEFAULT_GATE);
    let gate_a = Gate::new(DEFAULT_GATE * k_sd as f32);
    let mut adm_e = Admitted::new(px);
    let mut adm_a = Admitted::new(px);
    let mut ladder: Vec<Admitted> = GATE_LADDER.iter().map(|_| Admitted::new(px)).collect();
    let mut est_e = Estimator::new(&stats_reg, gate_e);
    let t2 = Instant::now();
    for (index, path) in paths.iter().enumerate() {
        let k = index as u16;
        let frame = pipe.field_for(path)?;
        adm_e.fold(k, &win_e, &ref_e, &pipe.reg, gate_e);
        adm_a.fold(k, &win_a, &ref_a, &pipe.raw, gate_a);
        for (slot, &t) in ladder.iter_mut().zip(GATE_LADDER.iter()) {
            slot.fold(k, &win_e, &ref_e, &pipe.reg, Gate::new(t));
        }
        est_e.fold(k, &frame, &pipe.reg)?;
        drop(frame);
        if index % 20 == 0 {
            eprintln!("  pass 2: {index}/{nframes}");
        }
    }
    let pass2 = t2.elapsed().as_secs_f64();
    println!("--- pass two (MEASURED) ---");
    println!(
        "wall clock      : {pass2:.3} s  ({:.1} ms/frame)",
        1000.0 * pass2 / nframes as f64
    );

    // ---- K2: this harness against the shipped Estimator --------------------
    let harness = mean_n(&adm_e.n);
    let shipped = est_e.mean_n_eff();
    println!();
    println!("--- K2: harness admitted-frame counter vs the shipped Estimator ---");
    println!("arm E           : harness {harness:.9}  Estimator {shipped:.9}");
    let k2 = harness == shipped;
    println!("K2              : {}", if k2 { "PASS" } else { "FAIL" });
    if !k2 {
        bail!("K2 failed; the harness is not counting what the merge counts");
    }

    // ---- K3: the tracked bounds bracket the winner -------------------------
    let k3_bad = (0..px)
        .filter(|&i| {
            adm_e.n[i] == 0
                || adm_e.lo[i] > win_e[i]
                || adm_e.hi[i] < win_e[i]
                || adm_a.n[i] == 0
                || adm_a.lo[i] > win_a[i]
                || adm_a.hi[i] < win_a[i]
        })
        .count();
    println!();
    println!("--- K3: admitted-set bounds bracket the elected winner ---");
    println!(
        "violations      : {k3_bad} of {px}  {}",
        if k3_bad == 0 { "PASS" } else { "FAIL" }
    );
    if k3_bad != 0 {
        bail!("K3 failed; the dumped bounds are not the admitted set");
    }

    println!();
    println!("mean n_eff E    : {harness:.5} of {nframes} frames");
    println!(
        "mean n_eff A'   : {:.5} of {nframes} frames",
        mean_n(&adm_a.n)
    );

    // ---- dump --------------------------------------------------------------
    let inv = 1.0 / nframes as f64;
    let mean_luma: Vec<f32> = mean_luma.iter().map(|v| (v * inv) as f32).collect();
    dump_u16(&out, "win_E", &win_e)?;
    dump_u16(&out, "win_A", &win_a)?;
    dump_u16(&out, "nadm_E", &adm_e.n)?;
    dump_u16(&out, "lo_E", &adm_e.lo)?;
    dump_u16(&out, "hi_E", &adm_e.hi)?;
    dump_u32(&out, "sum_E", &adm_e.sum)?;
    dump_u16(&out, "nadm_A", &adm_a.n)?;
    dump_u16(&out, "lo_A", &adm_a.lo)?;
    dump_u16(&out, "hi_A", &adm_a.hi)?;
    dump_u32(&out, "sum_A", &adm_a.sum)?;
    dump_f32(&out, "meanluma", &mean_luma)?;
    for (slot, t) in ladder.iter().zip(GATE_LADDER.iter()) {
        let tag = format!("g{}", *t as u32);
        dump_u16(&out, &format!("lo_{tag}"), &slot.lo)?;
        dump_u16(&out, &format!("hi_{tag}"), &slot.hi)?;
        dump_u16(&out, &format!("nadm_{tag}"), &slot.n)?;
    }

    // The ladder is a POST-HOC exploratory diagnostic added after the
    // pre-registration was committed. It reports what the gate does as it opens;
    // no registered decision reads any gate but `DEFAULT_GATE`.
    println!();
    println!("--- gate ladder for arm E (EXPLORATORY, not pre-registered) ---");
    for (slot, t) in ladder.iter().zip(GATE_LADDER.iter()) {
        let ne = mean_n(&slot.n);
        println!(
            "gate {t:>5}      : n_eff {ne:9.5}   n_eff/N {:.5}",
            ne / nframes as f64
        );
    }

    let iso_json = iso.map_or_else(|| "null".to_string(), |v| format!("{v}"));
    let header = format!(
        "{{\n  \"stack\": {:?},\n  \"frames\": {nframes},\n  \"width\": {},\n  \"height\": {},\n  \
         \"camera\": {camera:?},\n  \"iso\": {iso_json},\n  \"black\": {},\n  \"white\": {},\n  \
         \"gate_E\": {DEFAULT_GATE},\n  \"gate_A\": {},\n  \"k_sd\": {k_sd},\n  \
         \"focus_noise_sd_measured\": {},\n  \"focus_noise_sd_declared\": {},\n  \
         \"margin\": {},\n  \"mean_n_eff_E\": {harness},\n  \"mean_n_eff_A\": {},\n  \
         \"gate_ladder\": [{}],\n  \"gate_ladder_n_eff\": [{}],\n  \
         \"win_disagree_frac\": {},\n  \"pass1_s\": {pass1},\n  \"pass2_s\": {pass2}\n}}\n",
        dir.display().to_string(),
        geom.width,
        geom.height,
        levels.black,
        levels.white,
        DEFAULT_GATE * k_sd as f32,
        sd.reg_mean,
        FOCUS_NOISE_SD,
        SUPPORT_RADIUS + REGULARISER_RADIUS,
        mean_n(&adm_a.n),
        GATE_LADDER
            .iter()
            .map(|t| format!("{t}"))
            .collect::<Vec<_>>()
            .join(", "),
        ladder
            .iter()
            .map(|s| format!("{}", mean_n(&s.n)))
            .collect::<Vec<_>>()
            .join(", "),
        disagree as f64 / px as f64,
    );
    let hpath = out.with_extension("json");
    std::fs::write(&hpath, header).with_context(|| format!("{}", hpath.display()))?;
    println!();
    println!(
        "wrote           : {}.*.bin and {}",
        out.display(),
        hpath.display()
    );
    Ok(())
}
