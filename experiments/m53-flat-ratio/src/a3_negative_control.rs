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
//! # Fooling direction (rule 18)
//!
//! The control is one-sided in `p`: it plants ADDED white noise. It does not
//! plant correlated noise, fixed-pattern noise, or a noise REDUCTION, and a
//! high-pass box is by construction least sensitive to noise whose power sits
//! below its cutoff. A 9x9 box high-pass would under-report a very-low-spatial-
//! frequency explosion, and this control would not notice.

use std::path::PathBuf;

use strehl_core::flat_ratio::{self, FlatReference};

/// From `out/a3_rois_109.json`: plane ROI (1356, 32, 512, 512).
const W: usize = 512;
const H: usize = 512;

/// From the shipped CLI's own line for this stack and ROI:
/// `model predicts  : sigma    8.770 DN for one green-luma sample at that level`
/// (`out/a4_after.log`). The calibrated noise model, not either statistic.
const MODEL_SIGMA: f64 = 8.770;

/// True noise multipliers to plant, against ONE unstacked frame.
/// 22.767x is the number fact 469's arm E actually showed the OLD statistic;
/// 144.391x is what the high-pass showed on the same arm.
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

fn main() {
    let out: PathBuf = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("out");
    let blob = out.join("a3_rois_109.f32");
    let bytes = std::fs::read(&blob)
        .unwrap_or_else(|e| panic!("{}: {e}\nrun src/a3_dump_rois.py first", blob.display()));

    let per_frame_floats = W * H;
    assert_eq!(
        bytes.len() % (per_frame_floats * 4),
        0,
        "blob is not a whole number of {W}x{H} f32 frames"
    );
    let n = bytes.len() / (per_frame_floats * 4);

    let frames: Vec<Vec<f32>> = (0..n)
        .map(|i| {
            bytes[i * per_frame_floats * 4..(i + 1) * per_frame_floats * 4]
                .chunks_exact(4)
                .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
                .collect()
        })
        .collect();

    println!("M53 a3 -- NEGATIVE CONTROL for the flat-ROI acceptance statistic");
    println!("input      : {}", blob.display());
    println!("frames     : {n}   roi {W}x{H} plane px (109MSDCF, plane 1356,32 -- fact 469's ROI)");
    println!("model sigma: {MODEL_SIGMA:.3} DN per green-luma sample (calibrated model)");
    println!();

    // ---- the two references -------------------------------------------------
    let mid = n / 2; // exactly the frame the old convention privileged
    let (_, mid_raw_sd) = flat_ratio::mean_and_sd(&frames[mid]);

    let per_frame_hp: Vec<(u16, f64)> = frames
        .iter()
        .enumerate()
        .filter_map(|(i, f)| flat_ratio::highpass_sd(f, W, H).map(|v| (i as u16, v)))
        .collect();
    let reference = FlatReference::new(&per_frame_hp).expect("22 frames of 512x512");

    let old_floor = mid_raw_sd / MODEL_SIGMA;
    let new_floor = flat_ratio::structure_contamination(reference.median(), MODEL_SIGMA);

    println!("OLD denominator : ONE frame, index {mid}. raw spatial sd {mid_raw_sd:.3} DN");
    println!(
        "NEW denominator : {} frames. hp sd median {:.3} DN  min {:.3} (frame {})  max {:.3} \
         (frame {})",
        reference.frames(),
        reference.median(),
        reference.min(),
        reference.min_frame(),
        reference.max(),
        reference.max_frame()
    );
    println!(
        "                  spread {:.4}x -- fact 441 measured 1.60x on 119MSDCF; this is the \
         same defect",
        reference.spread()
    );
    println!("                  measured on this ROI, and it is why no single frame is used.");
    println!();
    println!("DERIVED asymptotic under-report factors (the prediction this run tests):");
    println!("  OLD : rawsd(frame {mid}) / sigma          = {old_floor:.4}x");
    println!("  NEW : median hp sd / (gain * sigma)      = {new_floor:.4}x");
    println!(
        "  gain = {:.9} = sqrt(1 - 1/{})",
        flat_ratio::HP_NOISE_GAIN,
        flat_ratio::HP_BOX_SIDE * flat_ratio::HP_BOX_SIDE
    );
    println!();

    // ---- the merge surrogate ------------------------------------------------
    // A plain unweighted mean of the 22 REAL frames. It is a real merge output
    // on a real structured ROI: the corpus's own 0.534x legacy floor is this
    // operator. Its noise sd is sigma/sqrt(n), which is what makes K solvable.
    let merged: Vec<f32> = (0..per_frame_floats)
        .map(|i| (frames.iter().map(|f| f64::from(f[i])).sum::<f64>() / n as f64) as f32)
        .collect();
    let (merged_mean, merged_raw_sd) = flat_ratio::mean_and_sd(&merged);
    let merged_hp = flat_ratio::highpass_sd(&merged, W, H).expect("512x512 holds a 9x9 box");
    println!(
        "merge surrogate : unweighted mean of all {n}. mean {merged_mean:.2} DN   raw sd \
         {merged_raw_sd:.3} DN   hp sd {merged_hp:.3} DN"
    );
    println!(
        "                  the SHIPPED argmax merge on this same ROI reads raw sd 76.052 DN and \
         hp sd 9.455 DN"
    );
    println!(
        "                  (out/a4_after.log), so the surrogate sits in the same place as the \
         real thing."
    );
    println!();

    // ---- the plant ----------------------------------------------------------
    println!("planted explosion, {} seeds each:", SEEDS.len());
    println!();
    println!(
        "  K true    plant p DN |  OLD ratio  OLD under-reports |  NEW ratio  [lo .. hi]        \
          NEW under-reports"
    );
    for k in PLANTED_K {
        // p solves K = sqrt(sigma^2/n + p^2) / sigma.
        let p = MODEL_SIGMA * (k * k - 1.0 / n as f64).sqrt();

        let mut olds = Vec::with_capacity(SEEDS.len());
        let mut news = Vec::with_capacity(SEEDS.len());
        let mut los = Vec::with_capacity(SEEDS.len());
        let mut his = Vec::with_capacity(SEEDS.len());
        for seed in SEEDS {
            let mut rng = Rng(seed);
            let planted: Vec<f32> = merged
                .iter()
                .map(|&x| (f64::from(x) + p * rng.normal()) as f32)
                .collect();

            let (_, raw) = flat_ratio::mean_and_sd(&planted);
            olds.push(raw / mid_raw_sd);

            let hp = flat_ratio::highpass_sd(&planted, W, H).expect("512x512 holds a 9x9 box");
            let r = reference.ratio(hp);
            news.push(r.median);
            los.push(r.lo);
            his.push(r.hi);
        }
        let (old_m, old_s) = mean_sd(&olds);
        let (new_m, new_s) = mean_sd(&news);
        let (lo_m, _) = mean_sd(&los);
        let (hi_m, _) = mean_sd(&his);
        println!(
            "  {k:8.3}  {p:10.3} | {old_m:9.3}x {:15.3}x | {new_m:9.3}x  [{lo_m:6.3}x .. \
             {hi_m:6.3}x] {:15.3}x",
            k / old_m,
            k / new_m
        );
        if k == PLANTED_K[PLANTED_K.len() - 1] {
            println!(
                "            seed spread: OLD sd {old_s:.5}x   NEW sd {new_s:.5}x over the \
                 {} seeds",
                SEEDS.len()
            );
        }
    }
    println!();
    println!("READING: 'under-reports' is K true / reported. 1.000x would be perfect.");
    println!(
        "The DERIVED prediction above is that these columns settle at {old_floor:.4}x and \
         {new_floor:.4}x."
    );
}
