//! Deterministic unit-variance noise planes, and the unit-sigma noise model
//! the calibration runs under.
//!
//! # The generator is load-bearing, and that is measured
//!
//! `merge.rs` records what happened when this was a plain LCG:
//! `FOCUS_NOISE_SD` varied by **1.30x across seeds** (0.01172 / 0.01371 /
//! 0.01522) when sampling error should have been well under 1%. Consecutive LCG
//! outputs lie on lattice planes, Box-Muller consumes them in pairs, and
//! filling a raster grid lays that lattice out *spatially* — where a 27-box
//! followed by a 17-box aliases against it differently for every seed. A
//! single-seed measurement would have baked a 30% error into the gate.
//!
//! So the generator is a **named choice**, not a detail, and this module offers
//! three so that rule 24 can be discharged by re-choosing rather than
//! re-computing: two different generators behind the same transform, and two
//! different transforms behind the same generator.

use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};

/// Which pseudo-random source fills a calibration plane.
///
/// All three produce mean-0, variance-1 samples. They differ in the two places
/// a noise generator can go wrong for this measurement: the **generator's**
/// spatial lattice structure, and the **transform's** tail shape.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NoiseSource {
    /// SplitMix64 into Box-Muller. Exactly what `merge.rs`'s in-crate
    /// measurement of `FOCUS_NOISE_SD` uses, and therefore the default.
    SplitMixBoxMuller,
    /// PCG-XSH-RR 64/32 into Box-Muller. A **different generator**, the same
    /// transform.
    PcgBoxMuller,
    /// SplitMix64 into Irwin-Hall(12) - 6. The **same generator**, a different
    /// transform, with visibly non-Gaussian tails (bounded at +/-6 sigma).
    /// `focus.rs`'s own test plants use this one.
    SplitMixIrwinHall,
}

impl NoiseSource {
    /// Fill `out` with unit-variance, zero-mean samples.
    pub fn fill(self, seed: u64, out: &mut [f32]) {
        match self {
            NoiseSource::SplitMixBoxMuller => {
                let mut r = SplitMix::new(seed);
                for v in out.iter_mut() {
                    *v = box_muller(r.uniform(), r.uniform());
                }
            }
            NoiseSource::PcgBoxMuller => {
                let mut r = Pcg32::new(seed);
                for v in out.iter_mut() {
                    *v = box_muller(r.uniform(), r.uniform());
                }
            }
            NoiseSource::SplitMixIrwinHall => {
                let mut r = SplitMix::new(seed);
                for v in out.iter_mut() {
                    let s: f64 = (0..12).map(|_| r.uniform()).sum();
                    *v = (s - 6.0) as f32;
                }
            }
        }
    }

    /// A short label for reports.
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            NoiseSource::SplitMixBoxMuller => "splitmix64+box-muller",
            NoiseSource::PcgBoxMuller => "pcg32+box-muller",
            NoiseSource::SplitMixIrwinHall => "splitmix64+irwin-hall(12)",
        }
    }
}

#[inline]
fn box_muller(u1: f64, u2: f64) -> f32 {
    ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
}

struct SplitMix(u64);

impl SplitMix {
    const fn new(seed: u64) -> Self {
        SplitMix(seed)
    }

    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// In `(0, 1]`, never 0, so `ln()` is finite.
    fn uniform(&mut self) -> f64 {
        ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
    }
}

/// PCG-XSH-RR 64/32, from O'Neill's reference construction. A genuinely
/// different generator family from SplitMix64: an LCG state with an
/// output permutation, rather than a mixing function over a Weyl sequence.
struct Pcg32 {
    state: u64,
    inc: u64,
}

impl Pcg32 {
    fn new(seed: u64) -> Self {
        let mut p = Pcg32 {
            state: 0,
            inc: (seed << 1) | 1,
        };
        p.next_u32();
        p.state = p.state.wrapping_add(seed);
        p.next_u32();
        p
    }

    fn next_u32(&mut self) -> u32 {
        let old = self.state;
        self.state = old
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(self.inc);
        let xorshifted = (((old >> 18) ^ old) >> 27) as u32;
        let rot = (old >> 59) as u32;
        xorshifted.rotate_right(rot)
    }

    /// In `(0, 1]`, never 0, so `ln()` is finite. 53 bits from two draws, the
    /// standard `(27, 26)` split.
    fn uniform(&mut self) -> f64 {
        let a = u64::from(self.next_u32() >> 5);
        let b = u64::from(self.next_u32() >> 6);
        (((a << 26) | b) as f64 + 1.0) / (1u64 << 53) as f64
    }
}

/// The noise model under which a unit-variance luma plane normalises to a
/// unit-scale response.
///
/// A verbatim reconstruction of `merge.rs`'s private `unit_sigma_model`.
/// `Var(L) = (Var(G1) + Var(G2)) / 4 = read_dn^2 / 2` for equal planes, so
/// `read_dn = sqrt(2)` gives `sigma_L = 1`, and the gain is small enough that
/// the shot term is negligible over the range a standard normal covers.
///
/// **The zero-gain trap this avoids is real and documented in-crate:** a gain of
/// exactly 0 makes `green_luma_sigma` return 0, `SIGMA_EPS` clamps it to 1e-3,
/// and the whole response is silently scaled by 1000. It does not error.
#[must_use]
pub fn unit_sigma_model() -> NoiseModel {
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

/// The twelve seeds `merge.rs` and `through_focus.rs` both measure over.
pub const CRATE_SEEDS: [u64; 12] = [
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

#[cfg(test)]
mod tests {
    use super::*;

    fn moments(v: &[f32]) -> (f64, f64) {
        let n = v.len() as f64;
        let mean = v.iter().map(|x| f64::from(*x)).sum::<f64>() / n;
        let var = v
            .iter()
            .map(|x| (f64::from(*x) - mean).powi(2))
            .sum::<f64>()
            / (n - 1.0);
        (mean, var.sqrt())
    }

    #[test]
    fn every_source_is_zero_mean_and_unit_variance() {
        // Rule 20: a source whose variance were 2 would move every calibrated
        // constant by sqrt(2) and nothing downstream would say so. The bands
        // are 4 standard errors of the mean and of the sd at n = 262144.
        for src in [
            NoiseSource::SplitMixBoxMuller,
            NoiseSource::PcgBoxMuller,
            NoiseSource::SplitMixIrwinHall,
        ] {
            let mut v = vec![0.0f32; 512 * 512];
            src.fill(0xC0FFEE, &mut v);
            let (mean, sd) = moments(&v);
            let sem = 1.0 / (v.len() as f64).sqrt();
            assert!(
                mean.abs() < 4.0 * sem,
                "{}: mean {mean:.5} exceeds 4 sem {:.5}",
                src.label(),
                4.0 * sem
            );
            assert!(
                (sd - 1.0).abs() < 4.0 * sem,
                "{}: sd {sd:.5} is not 1 within 4 sem",
                src.label()
            );
            assert!(v.iter().all(|x| x.is_finite()));
        }
    }

    #[test]
    fn the_sources_are_deterministic_and_seed_dependent() {
        let mut a = vec![0.0f32; 4096];
        let mut b = vec![0.0f32; 4096];
        NoiseSource::SplitMixBoxMuller.fill(42, &mut a);
        NoiseSource::SplitMixBoxMuller.fill(42, &mut b);
        assert_eq!(a, b, "same seed must give the same plane");
        NoiseSource::SplitMixBoxMuller.fill(43, &mut b);
        assert_ne!(a, b, "a different seed must give a different plane");
        NoiseSource::PcgBoxMuller.fill(42, &mut b);
        assert_ne!(a, b, "a different generator must give a different plane");
    }

    #[test]
    fn the_unit_sigma_model_really_has_unit_luma_sigma() {
        // The zero-gain trap, asserted rather than described: if this model
        // ever returned something other than ~1, every constant this crate
        // measures would be scaled by its reciprocal and the two-target check
        // would be the only thing that noticed.
        let m = unit_sigma_model();
        for level in [-3.0f32, 0.0, 1.0, 3.0, 6.0] {
            let s = m.green_luma_sigma(level);
            assert!(
                (s - 1.0).abs() < 1e-3,
                "sigma at {level} is {s}, not 1; the calibration scale is wrong"
            );
        }
        assert!(m.is_trustworthy());
    }

    #[test]
    fn the_seed_list_is_the_one_the_core_crate_measures_over() {
        assert_eq!(CRATE_SEEDS.len(), 12);
        assert_eq!(CRATE_SEEDS[0], 0xC0FFEE);
        let mut sorted = CRATE_SEEDS.to_vec();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(sorted.len(), 12, "seeds must be distinct");
    }
}
