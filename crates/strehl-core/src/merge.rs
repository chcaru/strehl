//! The estimation merge — **the thing `strehl` exists to build.**
//!
//! [`stack::Selection`](crate::stack) is the named baseline: per-pixel argmax,
//! measured at 1.253x the noise of a single unstacked frame (SYNTHESIS fact 19).
//! This module is its replacement, and it is built out of two measured findings
//! that were priced long before any of this was written:
//!
//! - **Regularise the focus field before choosing a winner.** A 17x17 box mean
//!   over the focus field drops winner-index speckle from 34.4% to 0.868% and
//!   merged noise from 1.253x to 1.075x (fact 23), and cuts absolute
//!   reconstruction error at occluding edges by 35%, 24.79 -> 15.99 DN
//!   (fact 84). That was the single largest measured quality win still unbuilt.
//!
//! - **Regularisation alone is not enough.** 1.075x is still worse than one
//!   frame. *Only averaging goes below one* (fact 23). A plain mean reaches
//!   0.534x (fact 19) but collapses detail by more than half (fact 24), so the
//!   average has to be taken over exactly those frames that genuinely agree.
//!
//! So the merge is: regularise, elect a winner, admit every frame whose focus
//! response is statistically indistinguishable from the winner's, and average
//! them. Where one frame stands far above the rest the acceptance set collapses
//! to that frame and the estimator degenerates to a selector — which is the
//! correct behaviour, and is what facts 263 and 264 say actually happens at a
//! resolved edge, where the peak stands 10^2-10^3 sigma clear.
//!
//! # Why this is two passes and not one
//!
//! The gate needs each frame's focus response *relative to the winner*, and the
//! winner is not known until every frame has been seen. A single bounded fold
//! would have to carry per-pixel through-focus state whose size grows with the
//! acceptance set. Two passes carry O(1) state per pixel instead, and decode is
//! 0.91 s warm (fact 33), so the second pass is cheap. Both passes are
//! order-independent and associative, so both parallelise by partitioning the
//! frame list — see the tests, which pin that property rather than assume it.
//!
//! # What is measured here and what is not
//!
//! [`FOCUS_NOISE_SD`] is measured by [`tests::the_focus_noise_constant_is_the
//! _measured_one`], in this crate, from a pure-noise plane pushed through the
//! real operator. It is not a literature value and not a guess.
//!
//! [`Gate::threshold`] is **not** measured. It is the one free parameter in this
//! module and it is deliberately left explicit at the API boundary rather than
//! buried in a default, because M27 measured the acceptance-set width it
//! controls (`nwide = 3`, fact 212) and that number is the calibration target.
//! [`Estimator::n_eff`] is an output for exactly this reason.

use crate::boxfilter::box_mean;
use crate::noise::NoiseModel;
use crate::plane::{PlaneGeometry, QuadSource};
use crate::{CfaPlane, Error, Result};

/// Radius of the merge regulariser: 8, giving the measured 17x17 box.
///
/// Fact 84 priced width 17 at -35% absolute reconstruction error. Fact 86 is the
/// reason this is not a tuning knob reaching down to 1: at width 3 the
/// regulariser is *worse than none at all* (merged noise rises 1.2773 -> 1.3856),
/// because a narrow box correlates neighbouring selections without averaging
/// enough of them to pay for it.
///
/// Fact 36 is the reason it is not tuned upward either: the flat-ROI noise ratio
/// is monotone-decreasing in width with no interior optimum, so anything that
/// minimises noise alone runs to the widest width offered and destroys focus
/// selectivity. Fact 42 supplies the interior optimum only under a *joint*
/// selectivity/noise objective, and only on tilted depth — which is where 17
/// came from.
pub const REGULARISER_RADIUS: usize = 8;

/// Width of the merge regulariser box, in plane pixels.
pub const REGULARISER_WIDTH: usize = 2 * REGULARISER_RADIUS + 1;

/// Standard deviation of the regularised focus response under pure sensor noise.
///
/// **Measured, not assumed** — see `the_focus_noise_constant_is_the_measured_one`.
/// A pure-noise luma plane is pushed through the real
/// [`FocusField`](crate::focus::FocusField) and this regulariser, and the
/// standard deviation of the interior response is read off.
///
/// The units work out to a pure number because
/// [`FocusField::compute`](crate::focus::FocusField::compute) already divides the
/// windowed gradient mean by the noise model's sigma at that pixel. That is what
/// makes a *single* threshold valid across the whole frame and across stacks
/// shot at different ISOs: the response is already in units of its own noise.
/// Without that normalisation this constant would have to be a per-pixel field.
///
/// # What the number says
///
/// A single sample of the sigma-normalised gradient magnitude is Rayleigh with
/// scale `0.125 * sqrt(12) = 0.4330`, so its own standard deviation is
/// `0.4330 * sqrt(2 - pi/2) = 0.2837`. The measured response is 18.6x quieter
/// than that, implying about **348 effective independent samples**. The nominal
/// combined support of a 27-box followed by a 17-box is `43 x 43 = 1849`, so the
/// overlapping Sobel stencils and the triangular box-of-box weighting cost a
/// factor of 5.3 against naive independence. **That factor is exactly why this
/// is measured rather than derived** — a closed form would have had to assume it
/// away, and would have made the gate 2.3x too tight.
///
/// It is a function of [`WINDOW_RADIUS`](crate::focus::WINDOW_RADIUS) and
/// [`REGULARISER_RADIUS`], and it is wrong if either changes. The test asserts
/// against the operator as configured, so changing either breaks it loudly.
pub const FOCUS_NOISE_SD: f32 = 0.015_214;

/// Apply the merge regulariser to one frame's focus field.
///
/// `scratch` and `dst` must be `geom.pixels()` long; `scratch` is overwritten.
/// Separable running sums, so the cost does not depend on the radius.
pub fn regularise(focus: &[f32], geom: PlaneGeometry, scratch: &mut [f32], dst: &mut [f32]) {
    box_mean(focus, geom, REGULARISER_RADIUS, scratch, dst);
}

/// The rule admitting a frame to the average at a pixel.
///
/// A frame is admitted when its regularised focus response is within
/// `threshold` standard deviations of the winner's. Both responses are already
/// noise-normalised, and the two frames' sensor noise is independent, so the
/// standard deviation of the *difference* is `sqrt(2) * FOCUS_NOISE_SD`.
///
/// # The winner's curse, and why the regulariser is the defence
///
/// The reference is a maximum over N frames, so it is biased upward by
/// selection, which makes every gap look larger than it is and shrinks the
/// acceptance set. The regulariser is what contains this: averaging the focus
/// field over 289 pixels before electing a winner is what takes speckle from
/// 34.4% to 0.868% (fact 23), and speckle *is* the winner's curse made visible.
/// Electing on the regularised field rather than the raw one is therefore
/// load-bearing for the gate, not just for the winner map.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Gate {
    /// Admission half-width, in standard deviations of the response difference.
    pub threshold: f32,
}

impl Gate {
    pub fn new(threshold: f32) -> Self {
        assert!(
            threshold >= 0.0 && threshold.is_finite(),
            "gate threshold must be finite and non-negative, got {threshold}"
        );
        Self { threshold }
    }

    /// The admission half-width in response units.
    #[inline]
    pub fn tolerance(&self) -> f32 {
        self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
    }

    /// Is a frame with response `focus` admitted against a winner at `best`?
    ///
    /// A non-finite response is never admitted, because every comparison
    /// against NaN is false.
    #[inline]
    pub fn admits(&self, focus: f32, best: f32) -> bool {
        best - focus <= self.tolerance()
    }
}

/// Pass one: the regularised winner field.
///
/// Carries O(1) state per pixel and is a commutative, associative fold, so the
/// frame list can be partitioned across workers arbitrarily and reduced with
/// [`FocusStats::absorb`] for bit-identical output.
#[derive(Debug, Clone)]
pub struct FocusStats {
    geom: PlaneGeometry,
    best_focus: Vec<f32>,
    best_index: Vec<u16>,
    frames: u32,
    max_index: u16,
}

/// Sentinel for "no frame has been folded at this pixel yet".
const NO_FRAME: u16 = u16::MAX;

impl FocusStats {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            best_focus: vec![f32::NEG_INFINITY; geom.pixels()],
            best_index: vec![NO_FRAME; geom.pixels()],
            frames: 0,
            max_index: 0,
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    pub fn best_focus(&self) -> &[f32] {
        &self.best_focus
    }
    pub fn best_index(&self) -> &[u16] {
        &self.best_index
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    /// Highest frame index folded, for the boundary flag.
    pub fn max_index(&self) -> u16 {
        self.max_index
    }
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * (size_of::<f32>() + size_of::<u16>())
    }

    /// Ties go to the lower frame index, stated rather than left to visitation
    /// order, so the fold is order-independent.
    #[inline]
    fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16) -> bool {
        focus > cur_focus || (focus == cur_focus && index < cur_index)
    }

    /// Fold one frame's **regularised** focus field in.
    pub fn fold(&mut self, frame_index: u16, regularised: &[f32]) -> Result<()> {
        if regularised.len() != self.geom.pixels() {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (regularised.len(), 1),
                want: (self.geom.pixels(), 1),
            });
        }
        assert_ne!(frame_index, NO_FRAME, "frame index {NO_FRAME} is reserved");
        for ((best_f, best_i), &f) in self
            .best_focus
            .iter_mut()
            .zip(self.best_index.iter_mut())
            .zip(regularised)
        {
            if Self::beats(f, frame_index, *best_f, *best_i) {
                *best_f = f;
                *best_i = frame_index;
            }
        }
        self.frames += 1;
        self.max_index = self.max_index.max(frame_index);
        Ok(())
    }

    /// Reduce another worker's partial pass-one state into this one.
    pub fn absorb(&mut self, other: &FocusStats) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: usize::MAX,
                got: (other.geom.width, other.geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        for i in 0..self.geom.pixels() {
            if Self::beats(
                other.best_focus[i],
                other.best_index[i],
                self.best_focus[i],
                self.best_index[i],
            ) {
                self.best_focus[i] = other.best_focus[i];
                self.best_index[i] = other.best_index[i];
            }
        }
        self.frames += other.frames;
        self.max_index = self.max_index.max(other.max_index);
        Ok(())
    }
}

/// Pass two: the noise-gated average.
///
/// Accumulates in `f32` per CFA plane, in **native raw DN** — M26's ruling. No
/// white balance, no colour transform and no black subtraction happens before
/// the gate, because the noise model is calibrated in raw DN and any of those
/// would put the gate and the model in different spaces.
#[derive(Debug, Clone)]
pub struct Estimator {
    geom: PlaneGeometry,
    gate: Gate,
    best_focus: Vec<f32>,
    best_index: Vec<u16>,
    max_index: u16,
    sum: [Vec<f32>; 4],
    /// Number of frames admitted at each pixel. This is `n_eff` for a plain
    /// mean, and it is an output, not a diagnostic — see fact 212.
    n: Vec<u16>,
    frames: u32,
}

impl Estimator {
    /// Begin pass two against a completed pass one.
    pub fn new(stats: &FocusStats, gate: Gate) -> Self {
        let n = stats.geom.pixels();
        Self {
            geom: stats.geom,
            gate,
            best_focus: stats.best_focus.clone(),
            best_index: stats.best_index.clone(),
            max_index: stats.max_index,
            sum: [vec![0.0; n], vec![0.0; n], vec![0.0; n], vec![0.0; n]],
            n: vec![0; n],
            frames: 0,
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    pub fn gate(&self) -> Gate {
        self.gate
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    /// Frames admitted per pixel. Compare against fact 212's `nwide = 3`.
    pub fn n_eff(&self) -> &[u16] {
        &self.n
    }
    pub fn best_index(&self) -> &[u16] {
        &self.best_index
    }
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * (4 * size_of::<f32>() + 2 * size_of::<u16>() + size_of::<f32>())
    }

    #[inline]
    fn slot(p: CfaPlane) -> usize {
        match p {
            CfaPlane::R => 0,
            CfaPlane::G1 => 1,
            CfaPlane::B => 2,
            CfaPlane::G2 => 3,
        }
    }

    /// Fold one frame's samples in, admitting it where the gate allows.
    ///
    /// `regularised` must be the same field that was folded into pass one for
    /// this `frame_index`, recomputed or cached.
    ///
    /// The winning frame is admitted **unconditionally** at its own pixels. That
    /// is not a convenience: it is what makes `n_eff >= 1` a structural
    /// guarantee rather than a numerical hope, and `n_eff >= 1` is in turn what
    /// makes "never noisier than one frame" provable instead of measured. It
    /// also makes the merge immune to any drift between the two passes'
    /// arithmetic.
    pub fn fold<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        src: &S,
        regularised: &[f32],
    ) -> Result<()> {
        let geom = src.geometry();
        if geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (geom.width, geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        if regularised.len() != self.geom.pixels() {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (regularised.len(), 1),
                want: (self.geom.pixels(), 1),
            });
        }

        let off = [
            CfaPlane::R.rggb_offset(),
            CfaPlane::G1.rggb_offset(),
            CfaPlane::B.rggb_offset(),
            CfaPlane::G2.rggb_offset(),
        ];
        let w = self.geom.width;

        for py in 0..self.geom.height {
            let (row0, row1) = src.quad_rows(py);
            let base = py * w;
            for px in 0..w {
                let i = base + px;
                let admitted = self.best_index[i] == frame_index
                    || self.gate.admits(regularised[i], self.best_focus[i]);
                if !admitted {
                    continue;
                }
                for (s, (ox, oy)) in off.iter().enumerate() {
                    let row = if *oy == 0 { row0 } else { row1 };
                    self.sum[s][i] += row[2 * px + ox] as f32;
                }
                self.n[i] += 1;
            }
        }
        self.frames += 1;
        Ok(())
    }

    /// Reduce another worker's partial pass-two state into this one.
    ///
    /// Both must have been built from the same pass one, which is checked: the
    /// winner fields must be identical, otherwise the two halves gated against
    /// different references and the sums are not commensurable.
    pub fn absorb(&mut self, other: &Estimator) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: usize::MAX,
                got: (other.geom.width, other.geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        assert_eq!(
            self.best_index, other.best_index,
            "estimators gated against different winner fields cannot be reduced"
        );
        assert_eq!(self.gate, other.gate, "estimators used different gates");
        for i in 0..self.geom.pixels() {
            for s in 0..4 {
                self.sum[s][i] += other.sum[s][i];
            }
            self.n[i] += other.n[i];
        }
        self.frames += other.frames;
        Ok(())
    }

    /// The merged estimate for one plane at one pixel, in raw DN.
    #[inline]
    pub fn value(&self, p: CfaPlane, i: usize) -> f32 {
        let n = self.n[i];
        debug_assert!(n > 0, "pixel {i} admitted no frame");
        self.sum[Self::slot(p)][i] / n as f32
    }

    /// Green as the output uses it, `(G1 + G2) / 2`, still in raw DN.
    #[inline]
    pub fn green_mean(&self, i: usize) -> f32 {
        0.5 * (self.value(CfaPlane::G1, i) + self.value(CfaPlane::G2, i))
    }

    /// Predicted standard deviation of the merged green luma at a pixel, in DN.
    ///
    /// This is confidence channel C1 of M34's vector. It is a *prediction from
    /// the calibrated model*, not a measurement of the output, which is what
    /// makes it available per pixel with no second capture.
    ///
    /// Averaging `n` independent frames divides the standard deviation by
    /// `sqrt(n)`. The frames are independent in their sensor noise; they are
    /// not independent in their fixed-pattern noise, so this is a floor rather
    /// than a complete account.
    pub fn predicted_sigma(&self, noise: &NoiseModel, i: usize, black_dn: f32) -> f32 {
        let luma = self.green_mean(i) - black_dn;
        noise.green_luma_sigma(luma) / (self.n[i] as f32).sqrt()
    }

    /// Did this pixel's winner land on the first or last frame of the stack?
    ///
    /// Confidence channel C4. Mass at the bracket boundary means the true peak
    /// is plausibly outside the capture, so no frame here is in focus and the
    /// merge cannot know it. M35 fact 300 measured 7.38% of `119MSDCF` in this
    /// state — a bracket that never covered the subject.
    #[inline]
    pub fn at_bracket_boundary(&self, i: usize) -> bool {
        let k = self.best_index[i];
        k == 0 || k == self.max_index
    }

    /// Every pixel admitted at least one frame.
    ///
    /// Structurally guaranteed by the unconditional admission of the winner, so
    /// a false here is a bug in this module and not a property of the data.
    pub fn every_pixel_is_decided(&self) -> bool {
        self.n.iter().all(|n| *n > 0)
    }

    /// Mean frames admitted per pixel, the stack-level `n_eff`.
    pub fn mean_n_eff(&self) -> f64 {
        if self.geom.pixels() == 0 {
            return 0.0;
        }
        self.n.iter().map(|n| *n as f64).sum::<f64>() / self.geom.pixels() as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::focus::FocusField;
    use crate::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
    use crate::plane::testing::QuadGrid;

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// A noise model whose green-luma sigma is 1.0 DN and is effectively flat in
    /// signal, so the focus normalisation divides by a known constant.
    ///
    /// The gain must be non-zero. `PlaneNoise` derives its read noise in DN as
    /// `read_noise_e * gain_dn_per_e`, so a zero gain gives a zero sigma, which
    /// `FocusField::compute` then clamps to `SIGMA_EPS` and the whole response
    /// is scaled by 1000. That is exactly the trap this comment exists to stop
    /// the next person falling into: it does not error, it silently rescales.
    fn unit_sigma_model() -> NoiseModel {
        // Var(L) = (Var(G1) + Var(G2)) / 4 = read_dn^2 / 2 for equal planes, so
        // read_dn = sqrt(2) gives sigma_L = 1. Gain is small enough that the
        // shot term is negligible over the signal range these tests use.
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

    /// Deterministic standard normals. **SplitMix64** feeding Box-Muller: the
    /// tests must not depend on the host's RNG or on a crate.
    ///
    /// The generator choice is load-bearing and was arrived at the hard way. A
    /// plain LCG here made [`FOCUS_NOISE_SD`] vary by **1.30x across seeds**
    /// (0.01172 / 0.01371 / 0.01522) when sampling error on ~19,000 interior
    /// pixels should be well under 1%. Consecutive LCG outputs lie on lattice
    /// planes, Box-Muller consumes them in pairs, and filling a raster grid with
    /// the result lays that lattice out *spatially* — where a 27-box followed by
    /// a 17-box aliases against it differently for every seed. A single-seed
    /// measurement would have silently baked a 30% error into the gate.
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
            // In (0, 1], never 0, so ln() is finite.
            ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
        }
        fn normal(&mut self) -> f32 {
            let (u1, u2) = (self.uniform(), self.uniform());
            ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
        }
    }

    /// **The measurement behind [`FOCUS_NOISE_SD`].**
    ///
    /// A pure-noise plane carries no focus signal, so every bit of spread in the
    /// regularised response is the operator's own noise. That spread is exactly
    /// the scale the gate needs, and measuring it here rather than deriving it
    /// analytically means the answer includes the correlation between
    /// overlapping Sobel stencils inside the box, which a closed form would have
    /// had to assume away — a factor of 3.2, see [`FOCUS_NOISE_SD`].
    ///
    /// # Why the tolerance is derived and not chosen
    ///
    /// The interior holds ~219,000 pixels but they are **not** 219,000
    /// measurements: each response averages a `43 x 43` support, so neighbouring
    /// responses are nearly the same number and only about `(468/43)^2 = 118`
    /// are independent per seed. An estimated standard deviation from `n`
    /// samples has a relative error near `1/sqrt(2(n-1))`, so one seed is worth
    /// about 6.5%. Picking a round tolerance here would have been picking
    /// whether the test passes: an earlier draft asserted 5% seed-to-seed
    /// stability, which no honest version of this measurement could ever have
    /// met. So the test computes the standard error of its own mean across seeds
    /// and requires the declared constant to sit inside four of them — and
    /// separately requires that standard error to be small, otherwise the band
    /// is wide enough to admit anything and the test has no power.
    ///
    /// # Why the plane is this large
    ///
    /// A sample standard deviation taken over a region only a few supports
    /// across is biased **low**, because the mean it subtracts is itself
    /// correlated with the samples. At `192 x 192` this measured 0.01366 — 10%
    /// under the truth — and it drifted with plane size, which is a falsifiable
    /// signature rather than a mystery. `384` gives `0.015277 +/- 0.000223` and
    /// `512` gives `0.015214 +/- 0.000075`: a difference of 0.27 standard
    /// errors, so the bias is spent by `384` and the number has converged. The
    /// larger plane is kept for the tighter interval.
    ///
    /// The **mean** is checked against closed form as well, and that check is
    /// the one that would catch the operator chain being wrong rather than just
    /// noisy. Under unit luma noise the gradient magnitude is Rayleigh with
    /// scale `0.125 * sqrt(12)`, whose mean is `0.4330 * sqrt(pi/2) = 0.5427`;
    /// neither box mean changes a mean. A silent rescale — the zero-gain trap
    /// documented on `unit_sigma_model` — moves this by three orders of
    /// magnitude while leaving the standard deviation looking plausible.
    #[test]
    fn the_focus_noise_constant_is_the_measured_one() {
        let g = geom(512, 512);
        let noise = unit_sigma_model();
        let margin = crate::focus::SUPPORT_RADIUS + REGULARISER_RADIUS;
        let seeds: [u64; 12] = [
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

        let mut sds = Vec::new();
        let mut means = Vec::new();
        let mut field = FocusField::new(g);
        let mut scratch = vec![0.0; g.pixels()];
        let mut reg = vec![0.0; g.pixels()];
        for seed in seeds {
            let mut rng = Rng::new(seed);
            let luma: Vec<f32> = (0..g.pixels()).map(|_| rng.normal()).collect();
            field.compute(&luma, &noise);
            regularise(field.values(), g, &mut scratch, &mut reg);

            let mut vals = Vec::new();
            for y in margin..g.height - margin {
                for x in margin..g.width - margin {
                    vals.push(reg[y * g.width + x] as f64);
                }
            }
            assert!(vals.len() > 10_000, "not enough interior samples");
            let mean = vals.iter().sum::<f64>() / vals.len() as f64;
            let var =
                vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (vals.len() - 1) as f64;
            means.push(mean);
            sds.push(var.sqrt());
        }

        // Closed form: Rayleigh(0.125 * sqrt(12)) has mean 0.5427, and a box
        // mean does not move it. This is the structural check.
        let rayleigh_mean = 0.125 * 12f64.sqrt() * (std::f64::consts::PI / 2.0).sqrt();
        for m in &means {
            let r = m / rayleigh_mean;
            assert!(
                (0.97..1.03).contains(&r),
                "pure-noise response mean {m:.4} is {r:.3}x the closed-form \
                 Rayleigh mean {rayleigh_mean:.4}; the operator chain is not \
                 doing what this test assumes"
            );
        }

        let n = sds.len() as f64;
        let mean_sd = sds.iter().sum::<f64>() / n;
        let spread = sds.iter().map(|s| (s - mean_sd).powi(2)).sum::<f64>() / (n - 1.0);
        let sem = (spread / n).sqrt();
        let rel_sem = sem / mean_sd;

        // The test must be able to fail. If the seeds happened to agree to
        // within nothing, the band below would admit any constant at all.
        assert!(
            rel_sem < 0.05,
            "standard error {rel_sem:.4} is too large for this test to have \
             power; add seeds or enlarge the plane. sds = {sds:?}"
        );

        let deviation = ((mean_sd - FOCUS_NOISE_SD as f64) / sem).abs();
        assert!(
            deviation < 4.0,
            "measured focus noise SD {mean_sd:e} +/- {sem:e} is {deviation:.1} \
             standard errors from the declared FOCUS_NOISE_SD \
             {FOCUS_NOISE_SD:e} (relative SEM {rel_sem:.4}); if the operator or \
             either radius changed, re-measure and update the constant"
        );
    }

    /// The constant is only meaningful if it is small against real focus
    /// contrast. If a real through-focus swing were the same size as the noise
    /// SD, the gate would admit everything and the merge would be a plain mean —
    /// which fact 24 says destroys detail.
    #[test]
    fn real_focus_contrast_is_far_larger_than_the_noise_scale() {
        let g = geom(192, 192);
        let noise = unit_sigma_model();
        let mut rng = Rng::new(7);

        // Same texture at two blur levels: a sharp checker versus a 2x2 mean of
        // it, both with the same noise added.
        let sharp: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = (i % g.width, i / g.width);
                let s = if (x / 2 + y / 2) % 2 == 0 { 60.0 } else { 20.0 };
                s + rng.normal()
            })
            .collect();
        let blurred: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = (i % g.width, i / g.width);
                let s = if (x / 4 + y / 4) % 2 == 0 { 45.0 } else { 35.0 };
                s + rng.normal()
            })
            .collect();

        let mut field = FocusField::new(g);
        let mut scratch = vec![0.0; g.pixels()];
        let (mut a, mut b) = (vec![0.0; g.pixels()], vec![0.0; g.pixels()]);
        field.compute(&sharp, &noise);
        regularise(field.values(), g, &mut scratch, &mut a);
        field.compute(&blurred, &noise);
        regularise(field.values(), g, &mut scratch, &mut b);

        let m = crate::focus::SUPPORT_RADIUS + REGULARISER_RADIUS;
        let c = m * g.width + m;
        let contrast = a[c] - b[c];
        assert!(
            contrast > 20.0 * FOCUS_NOISE_SD,
            "focus contrast {contrast:e} is not clear of the noise scale \
             {FOCUS_NOISE_SD:e}; the gate cannot discriminate"
        );
    }

    // ---- gate ----

    #[test]
    fn a_zero_threshold_admits_only_the_winner() {
        let gate = Gate::new(0.0);
        assert!(gate.admits(1.0, 1.0));
        assert!(!gate.admits(1.0 - 1e-6, 1.0));
    }

    #[test]
    fn the_gate_admits_within_its_tolerance_and_not_beyond() {
        let gate = Gate::new(2.0);
        let t = gate.tolerance();
        // Bracketed either side of the boundary rather than exactly on it. The
        // tolerance is ~1e-2 against a reference of 10, so `10.0 - t` is not
        // exactly representable and testing the boundary itself would be
        // testing f32 cancellation rather than the gate.
        assert!(gate.admits(10.0 - 0.5 * t, 10.0));
        assert!(gate.admits(10.0 - 0.99 * t, 10.0));
        assert!(!gate.admits(10.0 - 1.01 * t, 10.0));
        assert!(!gate.admits(10.0 - 2.0 * t, 10.0));
    }

    #[test]
    fn a_non_finite_response_is_never_admitted() {
        let gate = Gate::new(3.0);
        assert!(!gate.admits(f32::NAN, 1.0));
        assert!(!gate.admits(f32::NEG_INFINITY, 1.0));
    }

    #[test]
    #[should_panic(expected = "non-negative")]
    fn a_negative_threshold_is_rejected_rather_than_silently_inverting_the_gate() {
        Gate::new(-1.0);
    }

    // ---- pass one ----

    fn stats_over(order: &[u16], g: PlaneGeometry, f: impl Fn(u16, usize) -> f32) -> FocusStats {
        let mut s = FocusStats::new(g);
        for k in order {
            let field: Vec<f32> = (0..g.pixels()).map(|i| f(*k, i)).collect();
            s.fold(*k, &field).unwrap();
        }
        s
    }

    #[test]
    fn pass_one_elects_the_highest_response_and_is_order_independent() {
        let g = geom(9, 7);
        let f = |k: u16, i: usize| ((i * 37 + k as usize * 11) % 23) as f32;
        let a = stats_over(&[0, 1, 2, 3, 4], g, f);
        let b = stats_over(&[4, 3, 2, 1, 0], g, f);
        let c = stats_over(&[2, 0, 4, 1, 3], g, f);
        assert_eq!(a.best_index(), b.best_index());
        assert_eq!(a.best_index(), c.best_index());
        assert_eq!(a.best_focus(), b.best_focus());
        assert_eq!(a.frames_folded(), 5);
    }

    #[test]
    fn pass_one_absorb_matches_a_single_sequential_fold() {
        let g = geom(9, 7);
        let f = |k: u16, i: usize| ((i * 37 + k as usize * 11) % 23) as f32;
        let whole = stats_over(&[0, 1, 2, 3, 4, 5], g, f);
        for cut in 1..6usize {
            let all: Vec<u16> = (0..6).collect();
            let mut left = stats_over(&all[..cut], g, f);
            let right = stats_over(&all[cut..], g, f);
            left.absorb(&right).unwrap();
            assert_eq!(left.best_index(), whole.best_index(), "cut {cut}");
            assert_eq!(left.best_focus(), whole.best_focus(), "cut {cut}");
            assert_eq!(left.frames_folded(), whole.frames_folded());
            assert_eq!(left.max_index(), whole.max_index());
        }
    }

    #[test]
    fn pass_one_rejects_a_mismatched_field() {
        let mut s = FocusStats::new(geom(4, 4));
        assert!(matches!(
            s.fold(0, &[0.0; 9]),
            Err(Error::DimensionMismatch { .. })
        ));
    }

    // ---- pass two ----

    /// Frame `k` of a synthetic stack: a constant value per frame so the mean
    /// over an acceptance set is exactly predictable.
    fn flat_frame(k: u16, g: PlaneGeometry) -> QuadGrid {
        QuadGrid::new(g.width, g.height, |_, _| {
            let v = 100 + 10 * k;
            [v, v + 1, v + 2, v + 3]
        })
    }

    fn run(
        g: PlaneGeometry,
        n_frames: u16,
        gate: Gate,
        focus: impl Fn(u16, usize) -> f32,
    ) -> Estimator {
        let mut stats = FocusStats::new(g);
        for k in 0..n_frames {
            let field: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            stats.fold(k, &field).unwrap();
        }
        let mut est = Estimator::new(&stats, gate);
        for k in 0..n_frames {
            let field: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            est.fold(k, &flat_frame(k, g), &field).unwrap();
        }
        est
    }

    #[test]
    fn with_one_frame_clearly_sharpest_the_estimator_degenerates_to_a_selector() {
        // Frame 3 stands far above everything: exactly facts 263/264's resolved
        // edge, where the peak is 10^2-10^3 sigma clear and there is nothing
        // for an average to harvest.
        let g = geom(4, 4);
        let est = run(g, 6, Gate::new(3.0), |k, _| if k == 3 { 1.0 } else { 0.0 });
        assert!(est.n_eff().iter().all(|n| *n == 1));
        // Frame 3 carries the quad [130, 131, 132, 133] in QuadGrid's order,
        // which is R, G1, G2, B -- not R, G1, B, G2. The green mean is the two
        // greens, 131 and 132.
        assert_eq!(est.value(CfaPlane::R, 0), 130.0);
        assert_eq!(est.value(CfaPlane::G1, 0), 131.0);
        assert_eq!(est.value(CfaPlane::G2, 0), 132.0);
        assert_eq!(est.value(CfaPlane::B, 0), 133.0);
        assert_eq!(est.green_mean(0), 131.5);
        assert!(est.every_pixel_is_decided());
    }

    #[test]
    fn with_frames_that_agree_the_estimator_averages_them() {
        // Three frames tied at the top, three far below. The gate must take the
        // mean of exactly the three, which is fact 23's "only averaging goes
        // below one frame" and fact 212's nwide = 3.
        let g = geom(4, 4);
        let est = run(g, 6, Gate::new(3.0), |k, _| if k < 3 { 5.0 } else { 0.0 });
        assert!(est.n_eff().iter().all(|n| *n == 3));
        // Frames 0,1,2 carry R = 100, 110, 120.
        assert_eq!(est.value(CfaPlane::R, 0), 110.0);
        assert_eq!(est.mean_n_eff(), 3.0);
    }

    /// **The acceptance invariant: never noisier than one frame.**
    ///
    /// Fact 19 measured the baseline at 1.253x a single frame; this is the
    /// property that makes that impossible here. It is proved rather than
    /// sampled: averaging `n` independent samples scales sigma by
    /// `1/sqrt(n)`, and `n >= 1` is structural, so the merged sigma can never
    /// exceed the single-frame sigma at any pixel under any gate.
    #[test]
    fn the_merged_estimate_is_never_noisier_than_a_single_frame() {
        let g = geom(8, 8);
        let noise = unit_sigma_model();
        for threshold in [0.0f32, 0.5, 1.0, 3.0, 100.0] {
            let est = run(g, 7, Gate::new(threshold), |k, i| {
                ((i * 13 + k as usize * 5) % 11) as f32 * 1e-4
            });
            assert!(est.every_pixel_is_decided(), "t={threshold}");
            for i in 0..g.pixels() {
                let n = est.n_eff()[i];
                assert!(n >= 1, "t={threshold} pixel {i} admitted nothing");
                let merged = est.predicted_sigma(&noise, i, 0.0);
                let single = noise.green_luma_sigma(est.green_mean(i));
                assert!(
                    merged <= single + 1e-6,
                    "t={threshold} pixel {i}: merged {merged} > single {single}"
                );
                // And the improvement is exactly 1/sqrt(n), not approximately.
                assert!((merged * (n as f32).sqrt() - single).abs() < 1e-4);
            }
        }
    }

    #[test]
    fn a_wide_gate_admits_every_frame_and_a_zero_gate_admits_only_the_winner() {
        let g = geom(4, 4);
        // Responses one tolerance-unit apart so the threshold actually bites.
        let focus = |k: u16, _: usize| k as f32 * FOCUS_NOISE_SD;
        let wide = run(g, 5, Gate::new(1e6), focus);
        assert!(wide.n_eff().iter().all(|n| *n == 5));
        let none = run(g, 5, Gate::new(0.0), focus);
        assert!(none.n_eff().iter().all(|n| *n == 1));
    }

    #[test]
    fn the_acceptance_set_widens_monotonically_with_the_threshold() {
        let g = geom(4, 4);
        let focus = |k: u16, _: usize| -(k as f32) * FOCUS_NOISE_SD;
        let mut last = 0.0;
        for t in [0.0f32, 0.5, 1.0, 2.0, 4.0, 8.0] {
            let n = run(g, 8, Gate::new(t), focus).mean_n_eff();
            assert!(n >= last, "n_eff fell from {last} to {n} at threshold {t}");
            last = n;
        }
        assert_eq!(last, 8.0);
    }

    #[test]
    fn pass_two_is_order_independent_and_absorb_matches_a_sequential_fold() {
        let g = geom(6, 5);
        let focus = |k: u16, i: usize| (((i * 7 + k as usize * 3) % 5) as f32) * FOCUS_NOISE_SD;
        let gate = Gate::new(1.5);

        let mut stats = FocusStats::new(g);
        for k in 0..6u16 {
            let f: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let fold_set = |ks: &[u16]| {
            let mut e = Estimator::new(&stats, gate);
            for k in ks {
                let f: Vec<f32> = (0..g.pixels()).map(|i| focus(*k, i)).collect();
                e.fold(*k, &flat_frame(*k, g), &f).unwrap();
            }
            e
        };
        let whole = fold_set(&[0, 1, 2, 3, 4, 5]);
        let shuffled = fold_set(&[4, 1, 5, 0, 3, 2]);
        assert_eq!(whole.n_eff(), shuffled.n_eff());
        for i in 0..g.pixels() {
            assert_eq!(whole.value(CfaPlane::R, i), shuffled.value(CfaPlane::R, i));
        }
        for cut in 1..6usize {
            let all: Vec<u16> = (0..6).collect();
            let mut left = fold_set(&all[..cut]);
            left.absorb(&fold_set(&all[cut..])).unwrap();
            assert_eq!(left.n_eff(), whole.n_eff(), "cut {cut}");
            assert_eq!(left.frames_folded(), 6);
            for i in 0..g.pixels() {
                assert!((left.value(CfaPlane::B, i) - whole.value(CfaPlane::B, i)).abs() < 1e-3);
            }
        }
    }

    #[test]
    fn reducing_estimators_from_different_winner_fields_is_refused() {
        let g = geom(4, 4);
        let a = run(g, 3, Gate::new(1.0), |k, _| if k == 0 { 1.0 } else { 0.0 });
        let mut b = run(g, 3, Gate::new(1.0), |k, _| if k == 2 { 1.0 } else { 0.0 });
        assert!(std::panic::catch_unwind(move || b.absorb(&a)).is_err());
    }

    #[test]
    fn a_mismatched_frame_is_rejected_rather_than_silently_cropped() {
        let g = geom(4, 4);
        let stats = FocusStats::new(g);
        let mut est = Estimator::new(&stats, Gate::new(1.0));
        let small = QuadGrid::new(3, 4, |_, _| [1, 1, 1, 1]);
        assert!(matches!(
            est.fold(0, &small, &[0.0; 12]),
            Err(Error::DimensionMismatch { .. })
        ));
    }

    #[test]
    fn the_bracket_boundary_flag_fires_only_at_the_ends_of_the_stack() {
        let g = geom(3, 1);
        // Pixel 0 peaks at frame 0, pixel 1 mid-stack, pixel 2 at the last.
        let est = run(g, 5, Gate::new(0.0), |k, i| {
            let want = [0u16, 2, 4][i];
            if k == want { 1.0 } else { 0.0 }
        });
        assert!(est.at_bracket_boundary(0));
        assert!(!est.at_bracket_boundary(1));
        assert!(est.at_bracket_boundary(2));
    }

    /// The regulariser is what makes the winner field usable, and this is the
    /// mechanism fact 23 measured: a lone noise spike in one frame's focus field
    /// steals the pixel under a raw argmax and does not under a regularised one.
    ///
    /// It also pins the **limit**, because the regulariser is dilution and not
    /// magic. A `W x W` box divides a spike's excess by `W^2`, so it beats a
    /// deficit `d` in the surrounding response only while
    /// `excess < d * W^2`. At `d = 0.1` and `W = 17` the break-even spike is
    /// `0.9 + 0.1 * 289 = 29.8`, so 20 loses and 50 wins. Both are asserted:
    /// a test that only showed the spike being killed would not distinguish
    /// this regulariser from an arbitrarily strong one.
    #[test]
    fn the_regulariser_dilutes_a_focus_spike_by_its_area_and_no_more() {
        let g = geom(64, 64);
        let c = 32 * 64 + 32;
        let truth: Vec<f32> = vec![1.0; g.pixels()];
        let area = (REGULARISER_WIDTH * REGULARISER_WIDTH) as f32;
        let break_even = 0.9 + 0.1 * area;

        let winner_after_regularising = |spike: f32| {
            let mut spiked = vec![0.9f32; g.pixels()];
            spiked[c] = spike;

            // Raw argmax: any spike above 1.0 steals the pixel outright.
            let mut raw = FocusStats::new(g);
            raw.fold(0, &truth).unwrap();
            raw.fold(1, &spiked).unwrap();
            assert_eq!(raw.best_index()[c], 1, "raw argmax should elect the spike");

            let mut scratch = vec![0.0; g.pixels()];
            let (mut a, mut b) = (vec![0.0; g.pixels()], vec![0.0; g.pixels()]);
            regularise(&truth, g, &mut scratch, &mut a);
            regularise(&spiked, g, &mut scratch, &mut b);
            let mut reg = FocusStats::new(g);
            reg.fold(0, &a).unwrap();
            reg.fold(1, &b).unwrap();
            reg.best_index()[c]
        };

        assert!(break_even > 20.0 && break_even < 50.0, "{break_even}");
        assert_eq!(
            winner_after_regularising(20.0),
            0,
            "a 20x spike should not survive a {REGULARISER_WIDTH}x{REGULARISER_WIDTH} box"
        );
        assert_eq!(
            winner_after_regularising(50.0),
            1,
            "a 50x spike is above the {break_even:.1} break-even and must still win; \
             the regulariser is dilution, not a robust estimator"
        );
    }

    /// The regulariser must not be so strong that it erases a real depth edge —
    /// the other half of fact 82, which found no window/regulariser substitution
    /// at a depth discontinuity.
    #[test]
    fn the_regulariser_preserves_a_real_depth_edge() {
        let g = geom(64, 64);
        let left: Vec<f32> = (0..g.pixels())
            .map(|i| if i % 64 < 32 { 2.0 } else { 0.0 })
            .collect();
        let right: Vec<f32> = (0..g.pixels())
            .map(|i| if i % 64 < 32 { 0.0 } else { 2.0 })
            .collect();
        let mut scratch = vec![0.0; g.pixels()];
        let (mut a, mut b) = (vec![0.0; g.pixels()], vec![0.0; g.pixels()]);
        regularise(&left, g, &mut scratch, &mut a);
        regularise(&right, g, &mut scratch, &mut b);
        let mut s = FocusStats::new(g);
        s.fold(0, &a).unwrap();
        s.fold(1, &b).unwrap();
        // Well clear of the boundary on both sides, the correct frame wins.
        assert_eq!(s.best_index()[32 * 64 + 4], 0);
        assert_eq!(s.best_index()[32 * 64 + 60], 1);
    }

    #[test]
    fn memory_is_bounded_and_independent_of_the_frame_count() {
        let g = geom(100, 100);
        let a = run(g, 3, Gate::new(1.0), |_, _| 1.0);
        let b = run(g, 90, Gate::new(1.0), |_, _| 1.0);
        assert_eq!(a.allocated_bytes(), b.allocated_bytes());
    }
}
