//! M67 — does the shipped merge admit the frames that are actually **in
//! focus** at each pixel, and by what margin?
//!
//! Every prior measurement of the merge in this project scores **how many**
//! frames it averages (`n_eff`, the sqrt-N battery, the degeneracy guard).
//! None scores **which** frames. A merge that admits a fixed wrong set scores
//! identically to one that admits the right set. This instrument closes that,
//! on plants where the correct frame per pixel is known **by construction**
//! rather than estimated by the operator under test.
//!
//! Not a product path. Additive: it modifies no shared crate code and no
//! shipped behaviour, and it never writes to any capture directory.
//!
//! It mirrors `merge_cmd.rs`'s two passes exactly — same `green_luma_with_clip`,
//! same `FocusField::compute`, same `regularise`, same `FocusStats`, same
//! `Gate` — with one substitution: the frames come from a rendered plant on
//! disk instead of `strehl_raw::decode`, because a real capture has no
//! ground-truth focus map and that is the whole reason this had never been
//! measured. Serial, for `m65-election.rs`'s reason: the worker plan is the
//! part of `merge_cmd.rs` most likely to move underneath an example, and a
//! measurement is worth more correct than fast.
//!
//! Arms, all over the same rendered bytes:
//!
//! | arm | admitted set at pixel `i` |
//! | --- | --- |
//! | `E(T)` | the shipped estimating merge: `{k : win_reg == k or Gate(T).admits(reg_k, best_reg)}` |
//! | `A` | `argmax-baseline`: `{argmax_k raw_k}`, one frame, the retained selector |
//! | `Su(T)` | null: `n_eff(T)` indices drawn uniformly without replacement from `0..K` |
//! | `Sb(T)` | null: a contiguous run of `n_eff(T)` frames at a uniform random offset |
//!
//! ```text
//! cargo run --release -p strehl-cli --example m67-focus-correctness -- <PLANT_PREFIX> [--gate G]... [--null-seed S]
//! ```
//!
//! `<PLANT_PREFIX>` names three files written by
//! `experiments/M67-focus-correctness/src/10-render-plants.py`:
//! `<prefix>.meta.txt`, `<prefix>.frames.u16`, `<prefix>.truth.f32`.

use std::io::Read;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::{FocusField, SUPPORT_RADIUS};
use strehl_core::merge::{
    DEFAULT_GATE, Estimator, FocusStats, Gate, REGULARISER_RADIUS, regularise,
};
use strehl_core::noise::Levels;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Statistics are pooled over the interior only. `SUPPORT_RADIUS` is the
/// furthest luma sample the focus value reads and `REGULARISER_RADIUS` the box
/// mean on top of it, so a pixel nearer the edge than their sum has a focus
/// response contaminated by the replicate-clamped border.
const MARGIN: usize = SUPPORT_RADIUS + REGULARISER_RADIUS;

/// One rendered frame's CFA samples, in active-area coordinates. `2*w x 2*h`
/// u16 with no padding, exactly the layout `QuadGrid` uses in the crate's own
/// tests.
struct SimFrame<'a> {
    geom: PlaneGeometry,
    data: &'a [u16],
}

impl QuadSource for SimFrame<'_> {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        let stride = 2 * self.geom.width;
        let a = &self.data[2 * py * stride..(2 * py + 1) * stride];
        let b = &self.data[(2 * py + 1) * stride..(2 * py + 2) * stride];
        (a, b)
    }
}

/// The plant's declared parameters. A flat `key value` text file rather than
/// JSON, because `strehl-cli` has no serde dependency and adding one to ship a
/// research example would be the wrong trade.
struct Meta {
    plane_w: usize,
    plane_h: usize,
    frames: usize,
    iso: f32,
    black: f32,
    white: f32,
    camera: String,
    fields: Vec<(String, String)>,
}

fn read_meta(p: &Path) -> Result<Meta> {
    let text = std::fs::read_to_string(p).with_context(|| format!("reading {}", p.display()))?;
    let mut fields: Vec<(String, String)> = Vec::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (k, v) = line
            .split_once(char::is_whitespace)
            .with_context(|| format!("malformed meta line {line:?}"))?;
        fields.push((k.to_string(), v.trim().to_string()));
    }
    let get = |k: &str| -> Result<&str> {
        fields
            .iter()
            .find(|(a, _)| a == k)
            .map(|(_, b)| b.as_str())
            .with_context(|| format!("meta is missing {k}"))
    };
    Ok(Meta {
        plane_w: get("plane_w")?.parse()?,
        plane_h: get("plane_h")?.parse()?,
        frames: get("frames")?.parse()?,
        iso: get("iso")?.parse()?,
        black: get("black")?.parse()?,
        white: get("white")?.parse()?,
        camera: get("camera")?.to_string(),
        fields,
    })
}

fn read_u16(p: &Path, n: usize) -> Result<Vec<u16>> {
    let mut f = std::fs::File::open(p).with_context(|| format!("opening {}", p.display()))?;
    let mut bytes = Vec::with_capacity(2 * n);
    f.read_to_end(&mut bytes)?;
    if bytes.len() != 2 * n {
        bail!(
            "{} holds {} bytes, expected {}",
            p.display(),
            bytes.len(),
            2 * n
        );
    }
    Ok(bytes
        .as_chunks::<2>()
        .0
        .iter()
        .map(|c| u16::from_le_bytes([c[0], c[1]]))
        .collect())
}

fn read_f32(p: &Path, n: usize) -> Result<Vec<f32>> {
    let mut f = std::fs::File::open(p).with_context(|| format!("opening {}", p.display()))?;
    let mut bytes = Vec::with_capacity(4 * n);
    f.read_to_end(&mut bytes)?;
    if bytes.len() != 4 * n {
        bail!(
            "{} holds {} bytes, expected {}",
            p.display(),
            bytes.len(),
            4 * n
        );
    }
    Ok(bytes
        .as_chunks::<4>()
        .0
        .iter()
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect())
}

/// SplitMix64. Copied from `merge.rs`'s test generator rather than reached for
/// from a crate, so the null arms are reproducible from the seed alone.
struct Rng(u64);

impl Rng {
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    /// Uniform on `0..n`, by rejection, so the null has no modulo bias.
    fn below(&mut self, n: u64) -> u64 {
        assert!(n > 0);
        let zone = u64::MAX - (u64::MAX % n);
        loop {
            let x = self.next_u64();
            if x < zone {
                return x % n;
            }
        }
    }
}

/// Per-arm accumulators over the interior, in one place so every arm is scored
/// by the same arithmetic.
#[derive(Clone)]
struct Score {
    px: u64,
    /// Pixels where the truly-best frame index was admitted.
    hit: u64,
    /// Sum over pixels of `min |k - k*|` over the admitted set.
    miss: f64,
    /// Sum over pixels of `mean_{k admitted} |k - f*|`, `f*` continuous.
    defocus: f64,
    /// Sum over pixels of the admitted-set size.
    n: f64,
}

impl Score {
    fn new() -> Self {
        Score {
            px: 0,
            hit: 0,
            miss: 0.0,
            defocus: 0.0,
            n: 0.0,
        }
    }
    fn h(&self) -> f64 {
        self.hit as f64 / self.px as f64
    }
    fn d(&self) -> f64 {
        self.defocus / self.px as f64
    }
    fn m(&self) -> f64 {
        self.miss / self.px as f64
    }
    fn mean_n(&self) -> f64 {
        self.n / self.px as f64
    }
}

fn spearman(a: &[f64], b: &[f64]) -> f64 {
    fn ranks(v: &[f64]) -> Vec<f64> {
        let mut idx: Vec<usize> = (0..v.len()).collect();
        idx.sort_by(|&i, &j| v[i].partial_cmp(&v[j]).unwrap());
        let mut r = vec![0.0; v.len()];
        let mut i = 0;
        while i < idx.len() {
            let mut j = i;
            while j + 1 < idx.len() && v[idx[j + 1]] == v[idx[i]] {
                j += 1;
            }
            let avg = ((i + j) as f64) / 2.0 + 1.0;
            for &k in &idx[i..=j] {
                r[k] = avg;
            }
            i = j + 1;
        }
        r
    }
    let (ra, rb) = (ranks(a), ranks(b));
    let n = ra.len() as f64;
    let (ma, mb) = (ra.iter().sum::<f64>() / n, rb.iter().sum::<f64>() / n);
    let mut num = 0.0;
    let (mut da, mut db) = (0.0, 0.0);
    for (x, y) in ra.iter().zip(&rb) {
        num += (x - ma) * (y - mb);
        da += (x - ma) * (x - ma);
        db += (y - mb) * (y - mb);
    }
    num / (da.sqrt() * db.sqrt()).max(1e-12)
}

fn parse_args() -> Result<(PathBuf, Vec<f32>, u64, bool)> {
    let mut args = std::env::args().skip(1);
    let mut prefix: Option<PathBuf> = None;
    let mut gates: Vec<f32> = Vec::new();
    let mut seed: u64 = 0x4D36_37AA;
    let mut mirror = false;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--gate" => gates.push(
                args.next()
                    .context("--gate needs a value")?
                    .parse()
                    .context("--gate value")?,
            ),
            "--null-seed" => {
                seed = args
                    .next()
                    .context("--null-seed needs a value")?
                    .parse()
                    .context("--null-seed value")?
            }
            // The instrument's own negative control: mirror the truth map in
            // the ramp axis. On a monotone plant that makes the truth
            // anti-correlated with reality, so a metric that is really reading
            // the truth must collapse. If it does not, the metric is measuring
            // something other than focus correctness and every arm above it is
            // void.
            "--truth-mirror" => mirror = true,
            other => prefix = Some(PathBuf::from(other)),
        }
    }
    let prefix = prefix.context(
        "usage: m67-focus-correctness <PLANT_PREFIX> [--gate G].. [--null-seed S] [--truth-mirror]",
    )?;
    if gates.is_empty() {
        gates = vec![0.5, 1.0, 2.0, DEFAULT_GATE];
    }
    Ok((prefix, gates, seed, mirror))
}

fn main() -> Result<()> {
    let (prefix, gates, seed, mirror) = parse_args()?;
    let sib = |suffix: &str| PathBuf::from(format!("{}{suffix}", prefix.display()));
    let meta = read_meta(&sib(".meta.txt"))?;
    let geom = PlaneGeometry {
        width: meta.plane_w,
        height: meta.plane_h,
    };
    let px = geom.pixels();
    let k_frames = meta.frames;
    let frames = read_u16(&sib(".frames.u16"), 4 * px * k_frames)?;
    let mut truth = read_f32(&sib(".truth.f32"), px)?;
    if mirror {
        for y in 0..geom.height {
            truth[y * geom.width..(y + 1) * geom.width].reverse();
        }
    }
    let truth = truth;

    let levels = Levels {
        black: meta.black,
        white: meta.white,
    };
    let noise = profile::noise_model_for(&meta.camera, Some(meta.iso), levels);
    let black = meta.black;

    println!("=== M67 focus-admission correctness ===");
    println!("plant           : {}", prefix.display());
    for (k, v) in &meta.fields {
        println!("  {k:<16}: {v}");
    }
    println!(
        "plane           : {} x {} = {px} px",
        geom.width, geom.height
    );
    println!("noise model     : {:?}", noise.provenance);
    println!("interior margin : {MARGIN} plane px");
    println!("null seed       : {seed}");
    println!(
        "truth control   : {}",
        if mirror {
            "MIRRORED in x (negative control; the metric must collapse)"
        } else {
            "none"
        }
    );

    // Truth, discretised the only way the question admits: the correct frame at
    // a pixel is the frame whose focus plane is nearest the pixel's own visible
    // focus. `truth` carries the continuous value so the defocus statistic does
    // not inherit the rounding.
    let kstar: Vec<u16> = truth
        .iter()
        .map(|f| f.round().clamp(0.0, (k_frames - 1) as f32) as u16)
        .collect();

    let interior: Vec<usize> = (MARGIN..geom.height - MARGIN)
        .flat_map(|y| (MARGIN..geom.width - MARGIN).map(move |x| y * geom.width + x))
        .collect();
    println!("interior px     : {}", interior.len());
    {
        let mut lo = u16::MAX;
        let mut hi = 0u16;
        for &i in &interior {
            lo = lo.min(kstar[i]);
            hi = hi.max(kstar[i]);
        }
        println!("truth k* range  : {lo} .. {hi} over the interior");
    }

    // ---- pass one: the two winner fields, off the same rendered bytes ------
    let mut field = FocusField::new(geom);
    let mut luma = vec![0.0f32; px];
    let mut clipped = vec![false; px];
    let mut scratch = vec![0.0f32; px];
    let mut raw = vec![0.0f32; px];
    let mut reg = vec![0.0f32; px];
    let mut stats_reg = FocusStats::new(geom);
    let mut stats_raw = FocusStats::new(geom);

    let frame_at = |k: usize| SimFrame {
        geom,
        data: &frames[k * 4 * px..(k + 1) * 4 * px],
    };

    for k in 0..k_frames {
        let src = frame_at(k);
        green_luma_with_clip(&src, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, &noise);
        raw.copy_from_slice(field.values());
        regularise(field.values(), geom, &mut scratch, &mut reg);
        stats_reg.fold(k as u16, &reg)?;
        stats_raw.fold(k as u16, &raw)?;
    }

    // ---- pass two: the shipped gate, per pixel, plus the selector ----------
    let mut n_eff: Vec<Vec<u16>> = gates.iter().map(|_| vec![0u16; px]).collect();
    let mut e_score: Vec<Score> = gates.iter().map(|_| Score::new()).collect();
    let mut hit: Vec<Vec<bool>> = gates.iter().map(|_| vec![false; px]).collect();
    let mut miss: Vec<Vec<f32>> = gates.iter().map(|_| vec![f32::INFINITY; px]).collect();
    let mut defo: Vec<Vec<f32>> = gates.iter().map(|_| vec![0.0f32; px]).collect();
    // Per-pixel mean admitted index, for the monotonicity check.
    let mut idxsum: Vec<Vec<f32>> = gates.iter().map(|_| vec![0.0f32; px]).collect();

    let mut est = Estimator::new(&stats_reg, Gate::new(DEFAULT_GATE));

    for k in 0..k_frames {
        let src = frame_at(k);
        green_luma_with_clip(&src, black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
        field.compute(&luma, &noise);
        raw.copy_from_slice(field.values());
        regularise(field.values(), geom, &mut scratch, &mut reg);
        let ku = k as u16;
        for (g, &t) in gates.iter().enumerate() {
            let gate = Gate::new(t);
            for i in 0..px {
                let admitted = stats_reg.best_index()[i] == ku
                    || gate.admits(reg[i], stats_reg.best_focus()[i]);
                if admitted {
                    n_eff[g][i] += 1;
                    if kstar[i] == ku {
                        hit[g][i] = true;
                    }
                    let d = (i32::from(ku) - i32::from(kstar[i])).unsigned_abs() as f32;
                    miss[g][i] = miss[g][i].min(d);
                    defo[g][i] += (k as f32 - truth[i]).abs();
                    idxsum[g][i] += k as f32;
                }
            }
        }
        est.fold(ku, &src, &reg)?;
    }

    // ---- control: my counter is the shipped one ---------------------------
    let g_default = gates
        .iter()
        .position(|&t| t == DEFAULT_GATE)
        .context("the gate ladder must include DEFAULT_GATE")?;
    let harness_mean = n_eff[g_default].iter().map(|v| f64::from(*v)).sum::<f64>() / px as f64;
    let shipped_mean = est.mean_n_eff();
    println!();
    println!("--- C0: the harness's admitted-set counter is the shipped Estimator's ---");
    println!("harness mean n_eff (whole plane) : {harness_mean:.9}");
    println!("Estimator::mean_n_eff()          : {shipped_mean:.9}");
    let c0 = (harness_mean - shipped_mean).abs() < 1e-9;
    println!(
        "C0                               : {}",
        if c0 { "PASS" } else { "FAIL" }
    );
    if !c0 {
        bail!("C0 failed; the arms below are not scoring the shipped merge");
    }

    // ---- score every arm --------------------------------------------------
    for (g, _) in gates.iter().enumerate() {
        let s = &mut e_score[g];
        for &i in &interior {
            s.px += 1;
            s.hit += u64::from(hit[g][i]);
            s.miss += f64::from(miss[g][i]);
            s.defocus += f64::from(defo[g][i]) / f64::from(n_eff[g][i]);
            s.n += f64::from(n_eff[g][i]);
        }
    }

    // Arm A: the retained selector, one frame, elected on the RAW field —
    // which is what `Command::ArgmaxBaseline` does (`stack.rs` never calls
    // `regularise`). This is the control that must be separable from `E`.
    let mut a = Score::new();
    for &i in &interior {
        let w = stats_raw.best_index()[i];
        a.px += 1;
        a.hit += u64::from(w == kstar[i]);
        let d = f64::from((i32::from(w) - i32::from(kstar[i])).unsigned_abs());
        a.miss += d;
        a.defocus += f64::from((f32::from(w) - truth[i]).abs());
        a.n += 1.0;
    }

    // `E`'s *election* — the winner index map — reported next to its
    // *admitted set*, never instead of it. M65 measured that the two are
    // different objects (56.70 % of pixels elect a different winner while the
    // acceptance set moves 0.44 %), so this milestone keeps them apart.
    let mut e_win_hit = 0u64;
    let mut e_win_miss = 0.0f64;
    for &i in &interior {
        let w = stats_reg.best_index()[i];
        e_win_hit += u64::from(w == kstar[i]);
        e_win_miss += f64::from((i32::from(w) - i32::from(kstar[i])).unsigned_abs());
    }
    println!();
    println!("--- the election (an INDEX-map quantity), reported separately ---");
    println!(
        "E winner == k*   : {:.5}   mean |win - k*| = {:.4} frames (regularised field)",
        e_win_hit as f64 / interior.len() as f64,
        e_win_miss / interior.len() as f64
    );
    println!(
        "A winner == k*   : {:.5}   mean |win - k*| = {:.4} frames (raw field)",
        a.h(),
        a.m()
    );

    // Nulls, matched pixel-by-pixel to `E(T)`'s own `n_eff`.
    //
    // `Su` draws `n` distinct indices uniformly; its hit probability is exactly
    // `n/K`, so that column is computed in closed form and the sampled draw is
    // used only for the distance statistics. `Sb` places a contiguous run of
    // length `n` at a uniform offset; its hit probability is also closed form.
    let mut rng = Rng(seed);
    let mut su: Vec<Score> = gates.iter().map(|_| Score::new()).collect();
    let mut sb: Vec<Score> = gates.iter().map(|_| Score::new()).collect();
    let mut su_exact = vec![0.0f64; gates.len()];
    let mut sb_exact = vec![0.0f64; gates.len()];
    let mut pool: Vec<u16> = (0..k_frames as u16).collect();
    for (g, _) in gates.iter().enumerate() {
        for &i in &interior {
            let n = n_eff[g][i] as usize;
            let ks = i32::from(kstar[i]);
            // closed forms
            su_exact[g] += n as f64 / k_frames as f64;
            let last_start = (k_frames - n) as i32;
            let lo = (ks - n as i32 + 1).max(0);
            let hi = ks.min(last_start);
            sb_exact[g] += ((hi - lo + 1).max(0) as f64) / ((last_start + 1) as f64);

            // Su: partial Fisher-Yates over a fresh index pool.
            pool.iter_mut().enumerate().for_each(|(j, v)| *v = j as u16);
            let (mut h, mut mn, mut df, mut _sum) = (false, f32::INFINITY, 0.0f32, 0.0f32);
            for j in 0..n {
                let r = j + rng.below((k_frames - j) as u64) as usize;
                pool.swap(j, r);
                let kk = pool[j];
                if kk == kstar[i] {
                    h = true;
                }
                mn = mn.min((i32::from(kk) - ks).unsigned_abs() as f32);
                df += (f32::from(kk) - truth[i]).abs();
            }
            su[g].px += 1;
            su[g].hit += u64::from(h);
            su[g].miss += f64::from(mn);
            su[g].defocus += f64::from(df) / n as f64;
            su[g].n += n as f64;

            // Sb: one contiguous run at a uniform start.
            let s0 = rng.below((last_start + 1) as u64) as i32;
            let (mut h, mut mn, mut df) = (false, f32::INFINITY, 0.0f32);
            for j in 0..n as i32 {
                let kk = s0 + j;
                if kk == ks {
                    h = true;
                }
                mn = mn.min((kk - ks).unsigned_abs() as f32);
                df += (kk as f32 - truth[i]).abs();
            }
            sb[g].px += 1;
            sb[g].hit += u64::from(h);
            sb[g].miss += f64::from(mn);
            sb[g].defocus += f64::from(df) / n as f64;
            sb[g].n += n as f64;
        }
    }
    let npx = interior.len() as f64;

    println!();
    println!("--- the arms, interior only ---");
    println!(
        "{:<10} {:>7} {:>9} {:>9} {:>9}   H(closed form)",
        "arm", "n_eff", "H", "miss", "defocus"
    );
    println!(
        "{:<10} {:>7.3} {:>9.5} {:>9.4} {:>9.4}",
        "A(argmax)",
        a.mean_n(),
        a.h(),
        a.m(),
        a.d()
    );
    for (g, &t) in gates.iter().enumerate() {
        println!(
            "{:<10} {:>7.3} {:>9.5} {:>9.4} {:>9.4}",
            format!("E({t})"),
            e_score[g].mean_n(),
            e_score[g].h(),
            e_score[g].m(),
            e_score[g].d()
        );
        println!(
            "{:<10} {:>7.3} {:>9.5} {:>9.4} {:>9.4}   {:.5}",
            format!("Su({t})"),
            su[g].mean_n(),
            su[g].h(),
            su[g].m(),
            su[g].d(),
            su_exact[g] / npx
        );
        println!(
            "{:<10} {:>7.3} {:>9.5} {:>9.4} {:>9.4}   {:.5}",
            format!("Sb({t})"),
            sb[g].mean_n(),
            sb[g].h(),
            sb[g].m(),
            sb[g].d(),
            sb_exact[g] / npx
        );
    }

    println!();
    println!("--- margins at the shipped default gate {DEFAULT_GATE} ---");
    let e = &e_score[g_default];
    println!("H(E)  - H(Su)   : {:+.5}", e.h() - su[g_default].h());
    println!("H(E)  - H(Sb)   : {:+.5}", e.h() - sb[g_default].h());
    println!("H(E)  - H(A)    : {:+.5}", e.h() - a.h());
    println!(
        "D(Su) / D(E)    : {:.4}",
        su[g_default].d() / e.d().max(1e-12)
    );
    println!(
        "D(Sb) / D(E)    : {:.4}",
        sb[g_default].d() / e.d().max(1e-12)
    );
    println!("D(A)  / D(E)    : {:.4}", a.d() / e.d().max(1e-12));

    println!();
    println!("--- miss-distance CDF at the shipped default gate {DEFAULT_GATE} ---");
    println!(
        "{:<10} {:>9} {:>9} {:>9} {:>9}",
        "arm", "miss=0", "<=1", "<=2", "<=3"
    );
    {
        let mut cdf = [0u64; 4];
        for &i in &interior {
            let m = miss[g_default][i] as usize;
            for (j, c) in cdf.iter_mut().enumerate() {
                if m <= j {
                    *c += 1;
                }
            }
        }
        let n = interior.len() as f64;
        println!(
            "{:<10} {:>9.5} {:>9.5} {:>9.5} {:>9.5}",
            format!("E({DEFAULT_GATE})"),
            cdf[0] as f64 / n,
            cdf[1] as f64 / n,
            cdf[2] as f64 / n,
            cdf[3] as f64 / n
        );
        let mut cdf = [0u64; 4];
        for &i in &interior {
            let w = stats_raw.best_index()[i];
            let m = (i32::from(w) - i32::from(kstar[i])).unsigned_abs() as usize;
            for (j, c) in cdf.iter_mut().enumerate() {
                if m <= j {
                    *c += 1;
                }
            }
        }
        println!(
            "{:<10} {:>9.5} {:>9.5} {:>9.5} {:>9.5}",
            "A(argmax)",
            cdf[0] as f64 / n,
            cdf[1] as f64 / n,
            cdf[2] as f64 / n,
            cdf[3] as f64 / n
        );
    }

    // ---- the structural check: on a monotone depth ramp, the admitted set's
    // centre must be monotone across the field ------------------------------
    println!();
    println!("--- structural: is the admitted set's centre monotone in the ramp axis? ---");
    let mut rho_by_gate = vec![0.0f64; gates.len()];
    let mut dev_by_gate = vec![0.0f64; gates.len()];
    for (g, &t) in gates.iter().enumerate() {
        let mut cols: Vec<f64> = Vec::new();
        let mut mean_idx: Vec<f64> = Vec::new();
        let mut mean_truth: Vec<f64> = Vec::new();
        for x in MARGIN..geom.width - MARGIN {
            let mut s = 0.0f64;
            let mut st = 0.0f64;
            let mut c = 0.0f64;
            for y in MARGIN..geom.height - MARGIN {
                let i = y * geom.width + x;
                s += f64::from(idxsum[g][i]) / f64::from(n_eff[g][i]);
                st += f64::from(truth[i]);
                c += 1.0;
            }
            cols.push(x as f64);
            mean_idx.push(s / c);
            mean_truth.push(st / c);
        }
        let rho = spearman(&cols, &mean_idx);
        let rho_t = spearman(&cols, &mean_truth);
        let mut worst = 0.0f64;
        for (a, b) in mean_idx.iter().zip(&mean_truth) {
            worst = worst.max((a - b).abs());
        }
        rho_by_gate[g] = rho;
        dev_by_gate[g] = worst;
        println!(
            "E({t:<4}) spearman(col, mean admitted idx) = {rho:+.5}   \
             spearman(col, mean truth) = {rho_t:+.5}   max |col mean - truth| = {worst:.4} frames"
        );
    }

    // ---- one machine-readable line, so the aggregator never re-parses prose -
    print!(
        "SUMMARY plant={}",
        prefix.file_name().unwrap().to_string_lossy()
    );
    print!(" truth_mirror={mirror}");
    for (k, v) in &meta.fields {
        print!(" {k}={v}");
    }
    print!(
        " interior_px={} H_A={:.6} M_A={:.6} D_A={:.6} winH_E={:.6} winM_E={:.6}",
        interior.len(),
        a.h(),
        a.m(),
        a.d(),
        e_win_hit as f64 / interior.len() as f64,
        e_win_miss / interior.len() as f64
    );
    for (g, &t) in gates.iter().enumerate() {
        let tag = format!("{t}").replace('.', "p");
        print!(
            " n_{tag}={:.6} H_E_{tag}={:.6} M_E_{tag}={:.6} D_E_{tag}={:.6}",
            e_score[g].mean_n(),
            e_score[g].h(),
            e_score[g].m(),
            e_score[g].d()
        );
        print!(
            " H_Su_{tag}={:.6} D_Su_{tag}={:.6} M_Su_{tag}={:.6} H_Su_exact_{tag}={:.6}",
            su[g].h(),
            su[g].d(),
            su[g].m(),
            su_exact[g] / npx
        );
        print!(
            " H_Sb_{tag}={:.6} D_Sb_{tag}={:.6} M_Sb_{tag}={:.6} H_Sb_exact_{tag}={:.6}",
            sb[g].h(),
            sb[g].d(),
            sb[g].m(),
            sb_exact[g] / npx
        );
        print!(
            " rho_{tag}={:.6} devmax_{tag}={:.6}",
            rho_by_gate[g], dev_by_gate[g]
        );
    }
    println!();

    Ok(())
}
