//! M53 step 3b -- **the negative control**: plant a noise explosion of KNOWN
//! size on a REAL, STRUCTURED ROI and ask both statistics what they see.
//!
//! This is the point of the exercise. Fact 469 says the flat-ROI raw spatial sd
//! ratio under-reported a real 6.3x noise explosion. A replacement is only a
//! replacement if it can be shown, with numbers, to catch what the old one
//! missed -- and if it cannot, that is the finding and the statistic does not
//! ship.
//!
//! # What is planted, and why the truth is independent of both statistics
//!
//! Input is the 22 REAL 109MSDCF flat ROIs at plane (1356, 32, 512, 512) --
//! the exact ROI behind fact 469 -- dumped by `a3_dump_rois.py`. That ROI is
//! **not** detail-free (fact 455) and its raw sd is 8.70x the modelled noise,
//! so it is exactly the structured case the old statistic fails on.
//!
//! The merge surrogate `A` is the plain unweighted mean of the 22 frames. Its
//! noise sd is therefore `sigma / sqrt(n)`. Adding iid Gaussian noise of sd `p`
//! gives a planted output whose NOISE sd is `sqrt(sigma^2/n + p^2)`, so the
//! true noise multiplier against ONE unstacked frame is
//!
//! ```text
//! K = sqrt(sigma^2 / n + p^2) / sigma          ->   p = sigma * sqrt(K^2 - 1/n)
//! ```
//!
//! `sigma` comes from the CALIBRATED NOISE MODEL (the shipped CLI prints
//! 8.770 DN for this stack and ROI), and `p` is a number this program chooses.
//! Neither comes from the raw sd ratio or from the high-pass sd, so the truth
//! the two statistics are scored against is not derived from either of them
//! (rule 35).
//!
//! # What each statistic can do at best
//!
//! Both statistics measure a SPATIAL sd of noise **plus surviving structure**,
//! so neither can report `K` exactly. As `p` grows the reported ratio tends to
//!
//! ```text
//! OLD -> p / rawsd(F_mid)      so under-report -> rawsd(F_mid) / sigma
//! NEW -> g*p / median_i hp(F_i) so under-report -> median_i hp(F_i) / (g*sigma)
//! ```
//!
//! i.e. each statistic's asymptotic under-report factor is exactly its own
//! structure floor. Those two floors are printed, and the measured under-report
//! is checked against them. This is a DERIVED prediction made before the run,
//! which is what makes the run a test rather than a description.
//!
//! # The trap this control was rebuilt to avoid (SYNTHESIS fact 599)
//!
//! M40's null plant and M41's `noise_constant_check` each drew their noise from
//! the gain constant `g` and then normalised by a sigma computed from the *same*
//! `g`. Both were therefore scale-invariant in `g` to ~0.05 %, and both passed
//! confidently through the twelve milestones during which that constant was a
//! factor of two wrong. **A plant that supplies its own noise constant is
//! structurally blind to that constant being wrong.**
//!
//! This control is run in two arms, and the split is the whole point:
//!
//! * **SIGMA-FREE arm.** The plant is a size in DN that this program chooses.
//!   The predictions are `hp(A + p·n) = sqrt(hp(A)^2 + (g·p)^2)` and
//!   `raw(A + p·n) = sqrt(raw(A)^2 + p^2)` from the **measured** `hp(A)` and
//!   `raw(A)`, and the separation `R_new / R_old -> g · raw_mid / hp_med`. No
//!   calibrated constant appears anywhere in either side. These are falsifiable
//!   claims about the operator and they carry the milestone.
//! * **SIGMA-SCALED arm.** Labels the same plants with a true noise multiplier
//!   `K` against one unstacked frame, which needs the calibrated `sigma`. It is
//!   what a reader actually wants to know, and it is reported — but its
//!   "under-report" columns are an ALGEBRAIC IDENTITY of the construction, not
//!   a test, and they are printed saying so. See the note the program prints.
//!
//! What saves this from being M40's mistake is that **the statistic under test
//! is itself sigma-free**: `hp(merged) / median_i hp(F_i)` contains no
//! calibrated constant. Only the *labelling* of the plant needs sigma.
//!
//! # Why two stacks
//!
//! `109MSDCF` is ISO 160 — a true gain step, untouched by fact 550.
//! `119MSDCF` is ISO 50 — an extended ISO whose gain that fact doubled. A
//! quantity that behaves the same on both is not resting on the constant; one
//! that does not, is. M47 used this pairing to save facts 461/479.
//!
//! # Fooling direction (rule 18)
//!
//! The control is one-sided in `p`: it plants ADDED WHITE noise. It does not
//! plant correlated noise, fixed-pattern noise, or a noise REDUCTION, and a
//! high-pass box is by construction least sensitive to noise whose power sits
//! below its cutoff. A 9x9 box high-pass would under-report a very-low-spatial-
//! frequency explosion, and this control would not notice.

use std::path::PathBuf;

use strehl_core::flat_ratio::{self, FlatReference};

/// One corpus stack, as `a3_dump_rois.py` wrote it.
struct Stack {
    tag: &'static str,
    iso: u32,
    /// `true` when SYNTHESIS fact 550's ISO-50 gain correction moves this
    /// stack's noise model. The sigma-free arm must not care; the sigma-scaled
    /// arm does.
    gain_fix_applies: bool,
    w: usize,
    h: usize,
    /// From the calibrated noise model, via the JSON header. Used ONLY by the
    /// sigma-scaled arm.
    model_sigma: f64,
    /// `measured g / modelled g` from M25 fact 200's photon-transfer table, for
    /// THIS stack. Sigma goes as sqrt(g) once shot noise dominates, so this is
    /// how far arm 2's labels could move on independent evidence. Per stack,
    /// because the PTC disagrees in different directions at the two ISOs and
    /// carrying the ISO-160 figure across to ISO 50 would be a false claim.
    ptc_g_ratio: f64,
    /// Human-readable source for [`Self::ptc_g_ratio`].
    ptc_note: &'static str,
}

const STACKS: [Stack; 2] = [
    Stack {
        tag: "109",
        iso: 160,
        gain_fix_applies: false,
        w: 512,
        h: 512,
        model_sigma: 8.770,
        // M25 fact 200: 0.3273 measured against the relation's 0.3663.
        ptc_g_ratio: 0.3273 / 0.3663,
        ptc_note:
            "M25 fact 200's ISO-160 control: g measures 0.3273 vs the relation's 0.3663, 10.7% LOW",
    },
    Stack {
        tag: "119",
        iso: 50,
        gain_fix_applies: true,
        w: 512,
        h: 512,
        model_sigma: 9.774,
        // M25 fact 200: 0.2342 measured on THIS stack against the shipped
        // post-fact-550 base-ISO gain max(50,100)/436.8 = 0.228938.
        ptc_g_ratio: 0.2342 / 0.228938,
        ptc_note: "M25 fact 200 on THIS stack: g measures 0.2342 vs the shipped 0.22894, 2.3% HIGH",
    },
];

/// Plant sizes in DN, chosen directly rather than derived from any constant.
const PLANTS_DN: [f64; 7] = [0.0, 5.0, 20.0, 80.0, 200.0, 640.0, 2560.0];

/// True noise multipliers for the sigma-scaled arm.
/// 22.767x is what fact 469's arm E showed the OLD statistic; 144.391x is what
/// the high-pass showed on the same arm.
const PLANTED_K: [f64; 6] = [1.0, 2.0, 5.0, 10.0, 22.767, 144.391];

/// Several seeds, because `merge.rs`'s own tests record that a single-seed
/// noise fixture aliases against a box filter and is worth 30% there.
const SEEDS: [u64; 8] = [
    0x5307_0001,
    0x5307_0002,
    0x5307_0003,
    0x5307_0004,
    0x5307_0005,
    0x5307_0006,
    0x5307_0007,
    0x5307_0008,
];

/// splitmix64 + Box-Muller, the fixture RNG this repo already uses
/// (`crates/strehl-core/src/merge.rs`, `crates/strehl-core/src/focus.rs`).
struct Rng(u64);

impl Rng {
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    fn unit(&mut self) -> f64 {
        // (0, 1], never 0, so ln() is finite.
        ((self.next_u64() >> 11) as f64 + 1.0) / (9_007_199_254_740_992.0 + 1.0)
    }

    fn normal(&mut self) -> f64 {
        let (u, v) = (self.unit(), self.unit());
        (-2.0 * u.ln()).sqrt() * (std::f64::consts::TAU * v).cos()
    }
}

fn mean_sd(v: &[f64]) -> (f64, f64) {
    let n = v.len() as f64;
    let m = v.iter().sum::<f64>() / n;
    let var = v.iter().map(|x| (x - m) * (x - m)).sum::<f64>() / n;
    (m, var.sqrt())
}

/// Load one stack's dumped ROIs.
fn load(out: &std::path::Path, s: &Stack) -> Vec<Vec<f32>> {
    let blob = out.join(format!("a3_rois_{}.f32", s.tag));
    let bytes = std::fs::read(&blob)
        .unwrap_or_else(|e| panic!("{}: {e}\nrun src/a3_dump_rois.py first", blob.display()));
    let px = s.w * s.h;
    assert_eq!(
        bytes.len() % (px * 4),
        0,
        "{} is not a whole number of {}x{} f32 frames",
        blob.display(),
        s.w,
        s.h
    );
    (0..bytes.len() / (px * 4))
        .map(|i| {
            bytes[i * px * 4..(i + 1) * px * 4]
                .chunks_exact(4)
                .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
                .collect()
        })
        .collect()
}

/// Plant `p` DN of white noise on `base` and return `(raw sd, hp sd)`, averaged
/// over the seeds.
fn plant(base: &[f32], w: usize, h: usize, p: f64) -> (f64, f64) {
    let mut raws = Vec::with_capacity(SEEDS.len());
    let mut hps = Vec::with_capacity(SEEDS.len());
    for seed in SEEDS {
        let mut rng = Rng(seed);
        let v: Vec<f32> = base
            .iter()
            .map(|&x| (f64::from(x) + p * rng.normal()) as f32)
            .collect();
        raws.push(flat_ratio::mean_and_sd(&v).1);
        hps.push(flat_ratio::highpass_sd(&v, w, h).expect("ROI holds a 9x9 box"));
    }
    (mean_sd(&raws).0, mean_sd(&hps).0)
}

fn main() {
    let out: PathBuf = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("out");
    let g = flat_ratio::HP_NOISE_GAIN;

    println!("M53 a3 -- NEGATIVE CONTROL for the flat-ROI acceptance statistic");
    println!("Two arms, because of SYNTHESIS fact 599: a plant that supplies its own noise");
    println!("constant is structurally blind to that constant being wrong. Arm 1 uses no");
    println!("calibrated constant at all. Arm 2 does, and says where.");
    println!("Two stacks, because ISO 160 is untouched by fact 550's gain fix and ISO 50 is not.");
    println!(
        "kernel gain g = {g:.9} (DERIVED, sqrt(1 - 1/81)); {} seeds per plant.",
        SEEDS.len()
    );

    for s in &STACKS {
        let frames = load(&out, s);
        let n = frames.len();
        let mid = n / 2; // exactly the frame the old convention privileged
        let (_, raw_mid) = flat_ratio::mean_and_sd(&frames[mid]);
        let per_frame_hp: Vec<(u16, f64)> = frames
            .iter()
            .enumerate()
            .filter_map(|(i, f)| flat_ratio::highpass_sd(f, s.w, s.h).map(|v| (i as u16, v)))
            .collect();
        let reference = FlatReference::new(&per_frame_hp).expect("frames exist");
        let hp_med = reference.median();

        // The merge surrogate: a plain unweighted mean of the real frames. Its
        // noise sd is sigma/sqrt(n), which is what makes K solvable in arm 2.
        let px = s.w * s.h;
        let merged: Vec<f32> = (0..px)
            .map(|i| (frames.iter().map(|f| f64::from(f[i])).sum::<f64>() / n as f64) as f32)
            .collect();
        let (merged_mean, raw_a) = flat_ratio::mean_and_sd(&merged);
        let hp_a = flat_ratio::highpass_sd(&merged, s.w, s.h).expect("ROI holds a 9x9 box");

        println!();
        println!("================================================================");
        println!(
            "{}MSDCF  ISO {}  {} frames  {}x{}   fact 550's gain fix applies: {}",
            s.tag,
            s.iso,
            n,
            s.w,
            s.h,
            if s.gain_fix_applies { "YES" } else { "no" }
        );
        println!("================================================================");
        println!("OLD denominator : ONE frame, index {mid}. raw spatial sd {raw_mid:.3} DN");
        println!(
            "NEW denominator : {} frames. hp sd median {hp_med:.3} DN  min {:.3} (frame {})  \
             max {:.3} (frame {})",
            reference.frames(),
            reference.min(),
            reference.min_frame(),
            reference.max(),
            reference.max_frame()
        );
        println!(
            "                  spread {:.4}x over the choice of denominator -- fact 441's defect,",
            reference.spread()
        );
        println!("                  measured here, and why no single frame is used.");
        println!(
            "merge surrogate : unweighted mean of all {n}. mean {merged_mean:.2} DN   \
             raw sd {raw_a:.3} DN   hp sd {hp_a:.3} DN"
        );

        // ---- ARM 1: no calibrated constant anywhere -----------------------
        println!();
        println!("--- ARM 1: SIGMA-FREE. No calibrated constant on either side. ---");
        println!(
            "Predictions are quadrature from the MEASURED hp sd {hp_a:.3} and raw sd {raw_a:.3}"
        );
        println!("of the un-planted merge, plus the DERIVED kernel gain. Nothing else.");
        println!();
        println!(
            "   plant p DN |   hp measured   hp predicted    err |  raw measured  raw predicted \
               err"
        );
        for p in PLANTS_DN {
            let (raw_m, hp_m) = plant(&merged, s.w, s.h, p);
            let hp_pred = (hp_a * hp_a + (g * p) * (g * p)).sqrt();
            let raw_pred = (raw_a * raw_a + p * p).sqrt();
            println!(
                "  {p:11.1} | {hp_m:13.4} {hp_pred:14.4} {:6.2}% | {raw_m:13.4} {raw_pred:14.4} \
                 {:6.2}%",
                100.0 * (hp_m / hp_pred - 1.0),
                100.0 * (raw_m / raw_pred - 1.0)
            );
        }
        // The one number that carries the milestone, and it has no sigma in it.
        let (raw_big, hp_big) = plant(&merged, s.w, s.h, *PLANTS_DN.last().unwrap());
        let sep_pred = g * raw_mid / hp_med;
        let sep_meas = (hp_big / hp_med) / (raw_big / raw_mid);
        println!();
        println!("SEPARATION -- how many times more explosion NEW reports than OLD, at the");
        println!("largest plant. This is the milestone's claim and it contains NO sigma:");
        println!(
            "   predicted g * raw_mid / hp_med = {:.6} * {raw_mid:.3} / {hp_med:.3} = {sep_pred:.4}x",
            g
        );
        println!("   measured  (hp/hp_med) / (raw/raw_mid)                      = {sep_meas:.4}x");
        println!(
            "   apart {:.3}%. The content is that hp(planted)/raw(planted) -> g on a REAL",
            100.0 * (sep_meas / sep_pred - 1.0)
        );
        println!(
            "   structured ROI: measured {:.6} against the derived {g:.6}.",
            hp_big / raw_big
        );

        // ---- ARM 2: needs the calibrated sigma ----------------------------
        let sigma = s.model_sigma;
        println!();
        println!("--- ARM 2: SIGMA-SCALED. Uses the calibrated sigma = {sigma:.3} DN. ---");
        println!("K is the true noise multiplier against ONE unstacked frame, so the plant is");
        println!("p = sigma*sqrt(K^2 - 1/n) and sigma enters. READ THE WARNING BELOW THE TABLE.");
        println!();
        println!(
            "   K true    plant p DN |  OLD reports  under |  NEW reports  [lo .. hi]        under"
        );
        for k in PLANTED_K {
            let p = sigma * (k * k - 1.0 / n as f64).sqrt();
            let (raw_m, hp_m) = plant(&merged, s.w, s.h, p);
            let r_old = raw_m / raw_mid;
            let r = reference.ratio(hp_m);
            println!(
                "  {k:8.3}  {p:10.3} | {r_old:11.3}x {:6.3}x | {:11.3}x  [{:6.3}x .. {:6.3}x] \
                 {:6.3}x",
                k / r_old,
                r.median,
                r.lo,
                r.hi,
                k / r.median
            );
        }
        println!();
        println!("  !! THE TWO 'under' COLUMNS ARE ALGEBRAIC IDENTITIES, NOT TESTS (fact 599).");
        println!("  !! p is proportional to sigma, so as K grows");
        println!(
            "  !!     K / OLD -> raw_mid / sigma     = {:.4}x",
            raw_mid / sigma
        );
        println!(
            "  !!     K / NEW -> hp_med / (g*sigma)  = {:.4}x",
            hp_med / (g * sigma)
        );
        println!("  !! which is the same expression the 'prediction' is computed from. Their");
        println!("  !! agreement is arithmetic. What is NOT an identity is arm 1, and the ratio");
        println!(
            "  !! of these two columns, {:.4}x, which is arm 1's separation with sigma",
            (raw_mid / sigma) / (hp_med / (g * sigma))
        );
        println!("  !! cancelled out of it.");
        // Sensitivity: what a wrong sigma would do to arm 2 and not to arm 1.
        let alt = sigma * s.ptc_g_ratio.sqrt();
        println!("  !! SENSITIVITY, on this stack's OWN photon-transfer measurement:");
        println!("  !!   {}", s.ptc_note);
        println!("  !! so sigma could be {alt:.3} rather than {sigma:.3} DN. That moves K/NEW to");
        println!(
            "  !! {:.4}x and K/OLD to {:.4}x -- and moves arm 1 not at all.",
            hp_med / (g * alt),
            raw_mid / alt
        );
    }

    println!();
    println!("================================================================");
    println!("VERDICT: read arm 1. Arm 2 is the reader-facing labelling and is disclosed as");
    println!("partly self-referential. The statistic under test is itself sigma-free --");
    println!("hp(merged) / median_i hp(frame_i) -- so unlike M40's null plant it is not");
    println!("blind to a wrong noise constant; only the plant's LABEL needs one.");
}
