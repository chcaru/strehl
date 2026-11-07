//! Per-pixel through-focus **sufficient statistics** — the fold seam.
//!
//! # What this is for
//!
//! The merge in [`crate::merge`] is two passes: pass one elects a regularised
//! winner, pass two averages the frames the calibrated noise model cannot
//! separate from it. Both carry O(1) state per pixel, which is what keeps memory
//! O(workers) rather than O(frames).
//!
//! Everything the project wants *next* needs more than that. A per-pixel
//! posterior over frame-of-best-focus, from which confidence (posterior
//! entropy), occlusion (bimodality) and "no frame in focus" (mass at the bracket
//! boundary) all fall out of one object, needs the **through-focus
//! neighbourhood** at each pixel: where the peak really sits between frames, how
//! much response the sampling gave away, and whether there is a second peak
//! somewhere else in the stack.
//!
//! The naive way to have that is a focus volume. On the A7C II's 3516x2344 CFA
//! plane that is `4 * N` bytes per pixel: **725 MB at 22 frames, 1.09 GB at 33,
//! 3.46 GB at 105**. It is O(frames) and it is forbidden by the memory ratchet
//! (SYNTHESIS §3.2.1, M8).
//!
//! This module is the alternative: a **fixed 60 bytes per pixel**, gathered
//! during the existing second pass, from which all three of those quantities are
//! computable **with no third pass over the frames**.
//!
//! # The seam decision, stated once
//!
//! *Gather the statistics in pass two, anchored on pass one's winner.*
//!
//! That is what makes an exactly-mergeable fold possible. The parabola triple
//! needs the two frames on either side of the peak; a fold that does not yet
//! know where the peak is cannot know which two frames those are, so a pass-one
//! gather would have to keep a sliding window and would break at worker chunk
//! boundaries — the neighbour of a chunk-first argmax is in a different worker's
//! chunk and was never folded there. By pass two the anchor `k*` is a *constant*,
//! so each pixel's `left`/`peak`/`right` slot is written by exactly one frame and
//! the fold is trivially commutative and associative. Every other channel here is
//! a min, a max, a top-k select or a sum, all of which are as well.
//!
//! The cost of the decision is that the statistics are anchored on the
//! **selection-scale** winner while being measured on the **fine** scale, so a
//! pixel whose fine-scale argmax disagrees with its regularised winner gets a
//! triple that is not centred on its own fine peak. That disagreement is not
//! hidden: [`ThroughFocus::top_indices`] carries the fine argmax, so
//! `top_indices(i)[0] != anchor(i)` is a directly measurable flag, and
//! [`ThroughFocus::anchor_is_fine_argmax`] reports it.
//!
//! # Why the fine scale
//!
//! Because M21 measured that the thing this is for is **invisible at the
//! selection scale**. See [`crate::focus::FINE_WINDOW_RADIUS`]: multi-peak
//! enrichment at depth steps is 4.38x at radius 2 and 0.36x — *depleted* — at
//! radius 13, because a 54-sensor-pixel window averages the foreground and
//! background layers together. Sufficient statistics gathered at the selection
//! scale would be sufficient for nothing.
//!
//! # What is NOT here
//!
//! The posterior itself. This module carries the statistics a posterior would be
//! built from and the two exactly-mergeable sums that make one of its summaries
//! ([`ThroughFocus::posterior_perplexity`]) available now; it does not decide the
//! posterior's form, its prior, or what is done with it. That is deliberately the
//! next milestone's decision and this module is built so that it does not have to
//! be made tonight.

use std::cmp::Ordering;
use std::mem::size_of;

use crate::focus::FINE_WINDOW_RADIUS;
use crate::merge::{FOCUS_NOISE_SD, FocusStats};
use crate::plane::PlaneGeometry;
use crate::{Error, Result};

/// How many `(value, index)` pairs of the through-focus curve are retained.
///
/// Four. The brief's own ratchet arithmetic prices `k = 4` at ~206 MB of the
/// budget and that is the size that was agreed.
///
/// **The truncation is real and it binds in exactly the place confidence lives.**
/// M34 measured the posterior to be a delta at 76.5% of pixels, with p99
/// perplexity 4.74 and a maximum of 39.05 (facts 261, 283). A top-4 list can
/// represent a perplexity of at most 4, so the p99 pixel is *at the cap*. The
/// consequence is stated rather than papered over: quantities derived from
/// [`ThroughFocus::top_values`] are trustworthy as values in the body of the
/// distribution and only as a **saturation flag** in the tail. The perplexity
/// channel that does not have this problem,
/// [`ThroughFocus::posterior_perplexity`], is carried separately as two
/// untruncated sums for precisely this reason.
pub const TOP_K: usize = 4;

/// Minimum frame-index separation for a peak to count as a *different* peak.
///
/// Two. The parabola triple occupies `k* - 1 ..= k* + 1`, so 2 is the first
/// separation at which a sample is not part of the primary peak's own fit. Any
/// smaller value would report the primary peak's shoulders as a second mode.
///
/// It is a floor, not a calibration. A real through-focus peak is broader than
/// three frames — M33 fitted a Gaussian of sigma 1.68 frames at full sampling
/// density — so at separation 2 the "second peak" can still be the primary
/// peak's skirt. That is why [`ThroughFocus::bimodality`] is documented as an
/// **upper bound** and gated against a measured noise scale before it is
/// believed.
pub const PEAK_SEPARATION: u16 = 2;

/// Standard deviation of the **fine** focus response under pure sensor noise.
///
/// The [`FOCUS_NOISE_SD`] of the statistics scale. Measured the same way, by
/// `the_fine_focus_noise_constant_is_the_measured_one`, from a pure-noise luma
/// plane pushed through the real operator at [`FINE_WINDOW_RADIUS`] with **no**
/// regulariser — the fine field is consumed raw, because regularising it would
/// destroy the very thing M21 says only exists at this scale.
///
/// # What the number says
///
/// A single sample of the sigma-normalised gradient magnitude has standard
/// deviation `0.4330 * sqrt(2 - pi/2) = 0.2837`. The measured fine response is
/// 3.14x quieter than that, implying **9.85 effective independent samples**
/// against a nominal `5 x 5 = 25` — so overlapping Sobel stencils cost a factor
/// of 2.5 against naive independence here, where they cost 5.3 at the selection
/// scale. The two are not the same penalty and neither is derivable from the
/// other, which is why both are measured.
///
/// It is **5.94x larger than [`FOCUS_NOISE_SD`] as the two fields are actually
/// consumed**, and that is the trade: the fine field can see a second layer and
/// cannot see a small difference. Every statistic derived from it is therefore
/// reported in units of this constant and never in bare response units.
///
/// **That 5.94 is a product of two things, and fact 437 charged the whole of it
/// to the window.** Fact 500 unpicked it and this crate's sibling
/// `strehl-plugin` re-measures the decomposition on the same pipeline
/// (`calibrate::tests::the_fine_constant_factors_into_a_window_term_and_a_regulariser_term`):
///
/// ```text
/// 5.943  =  1.811  x  3.281
///           ^^^^^     ^^^^^
///           w13 -> w2 at the SAME r8 regulariser   (fact 500: 1.815)
///                     the r8 regulariser being ABSENT here and present there
/// ```
///
/// So the honest answer to "how much noisier is a five-pixel window than a
/// twenty-seven-pixel one" is **1.815**, not 5.94; the remaining 3.27x is the
/// price of consuming this field raw, which M21 says is mandatory. Both numbers
/// are needed and they answer different questions. **Never quote 5.94 as an
/// operator `k`** — that is fact 437's retired error, and fact 500 records it
/// because the failure mode is general: a ratio of two constants means nothing
/// unless both were measured in the same configuration.
///
/// It is a function of [`FINE_WINDOW_RADIUS`] alone and is wrong if that
/// changes. The 3.281 term above is a function of
/// [`crate::merge::REGULARISER_RADIUS`] and is wrong if *that* changes — which
/// is why it is stated as a decomposition rather than folded into one number.
pub const FINE_FOCUS_NOISE_SD: f32 = 0.090_400;

/// Sentinel for "no frame has been folded into this slot yet".
const NO_FRAME: u16 = u16::MAX;

/// Per-pixel through-focus sufficient statistics, gathered during pass two.
///
/// Fixed size per pixel, **independent of the frame count**. See the module
/// documentation for the seam decision and [`ThroughFocus::allocated_bytes`] for
/// the accounting.
///
/// # What it is sufficient for
///
/// | want | from | method |
/// |---|---|---|
/// | sub-frame peak position | the triple | [`subframe_offset`](Self::subframe_offset) |
/// | response given up by sampling | the triple + the floor | [`subframe_deficit`](Self::subframe_deficit) |
/// | top-k frames and values | the top-k lists | [`top_values`](Self::top_values), [`top_indices`](Self::top_indices) |
/// | bimodality / second layer | the far peak + the floor | [`bimodality`](Self::bimodality) |
/// | posterior spread | the two exponential sums | [`posterior_perplexity`](Self::posterior_perplexity) |
/// | "no frame in focus" | the anchor | [`at_bracket_boundary`](Self::at_bracket_boundary) |
#[derive(Debug, Clone)]
pub struct ThroughFocus {
    geom: PlaneGeometry,
    /// Pass one's regularised winner, `k*`. The anchor everything hangs off.
    anchor: Vec<u16>,
    /// Pass one's regularised response at `k*`. Carried so that the posterior
    /// sums have a fixed, pre-fold offset — which is what makes them summable
    /// across workers — and so that [`absorb`](Self::absorb) can refuse two
    /// halves that came from different pass ones.
    anchor_focus: Vec<f32>,
    /// Fine response at `k* - 1`, `k*`, `k* + 1`. [`f32::NAN`] where the slot is
    /// off the end of the stack or has not been folded.
    triple: Vec<[f32; 3]>,
    /// Minimum fine response over every frame. The fit baseline (fact 272).
    floor: Vec<f32>,
    /// The `TOP_K` largest fine responses, descending.
    top_val: Vec<[f32; TOP_K]>,
    /// Their frame indices, ties to the lower index.
    top_idx: Vec<[u16; TOP_K]>,
    /// Largest fine response at least [`PEAK_SEPARATION`] frames from `k*`.
    far_val: Vec<f32>,
    far_idx: Vec<u16>,
    /// `sum_k exp(u_k)` where `u_k = (reg_k - reg_{k*}) / (sqrt(2) * FOCUS_NOISE_SD)`.
    z: Vec<f32>,
    /// `sum_k u_k exp(u_k)`, the other statistic entropy needs.
    w: Vec<f32>,
    frames: u32,
    max_index: u16,
}

impl ThroughFocus {
    /// Begin gathering against a completed pass one.
    pub fn new(stats: &FocusStats) -> Self {
        let n = stats.geometry().pixels();
        Self {
            geom: stats.geometry(),
            anchor: stats.best_index().to_vec(),
            anchor_focus: stats.best_focus().to_vec(),
            triple: vec![[f32::NAN; 3]; n],
            floor: vec![f32::INFINITY; n],
            top_val: vec![[f32::NEG_INFINITY; TOP_K]; n],
            top_idx: vec![[NO_FRAME; TOP_K]; n],
            far_val: vec![f32::NEG_INFINITY; n],
            far_idx: vec![NO_FRAME; n],
            z: vec![0.0; n],
            w: vec![0.0; n],
            frames: 0,
            max_index: stats.max_index(),
        }
    }

    /// Begin gathering with the frame axis **permuted** — the placebo.
    ///
    /// `perm[k]` is the index frame `k` will be folded under; the anchor becomes
    /// `perm[k*]`. Every pixel therefore sees exactly the same *multiset* of
    /// responses and exactly the same winning value, and only the mapping from
    /// response to focus position is destroyed. Fact 19's placebo — same winner
    /// histogram, decorrelated from the pixel's own noise, reading 0.981x — is
    /// the model this follows.
    ///
    /// # What it is a null for, and what it is not
    ///
    /// It is a null for **adjacency**: any statistic that reads the same under
    /// permutation is not using the frame ordering and is measuring noise.
    ///
    /// M21 is explicit that the permutation is a null for *enrichment* and never
    /// for a raw rate — under permutation the raw multi-peak rate goes **up**,
    /// to 86-98%. The same warning applies here with a known sign:
    /// [`bimodality`](Self::bimodality) reads **higher** under permutation, not
    /// lower, because "at least [`PEAK_SEPARATION`] frames from the anchor"
    /// becomes a random subset that usually contains the true runner-up, whereas
    /// on an ordered curve the runner-up is a neighbour and is excluded. So the
    /// placebo is the *maximum-bimodality* reference and the quantity to read is
    /// the ratio: well below 1 means the curve is focus-ordered, at 1 means the
    /// stack carries no ordering information at this scale at all.
    ///
    /// The caller supplies the permutation so that it is reproducible and
    /// auditable. A permutation with a fixed point at some `k` leaves that
    /// frame's contribution unchanged, which is correct and not a defect.
    ///
    /// Use [`shuffled_indices`] to build it. **A rotation is not admissible**:
    /// `k -> (k + s) mod n` is an isometry of the index line, so `|perm[a] -
    /// perm[b]| = |a - b|` away from the wrap point and adjacency survives
    /// almost everywhere. A first draft of this milestone used one, and the
    /// placebo came back at exactly **1.0000x** of the real reading — a null
    /// that is silently a copy of the thing it is supposed to falsify.
    pub fn new_permuted(stats: &FocusStats, perm: &[u16]) -> Self {
        let mut tf = Self::new(stats);
        for a in tf.anchor.iter_mut() {
            if *a != NO_FRAME {
                *a = perm[*a as usize];
            }
        }
        tf
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    pub fn anchor(&self) -> &[u16] {
        &self.anchor
    }

    /// Bytes held, and the whole point of the design.
    ///
    /// Constant in the frame count. The volume this replaces is
    /// `4 * frames` bytes per pixel, so the break-even is at 15 frames: below
    /// that a volume would genuinely be cheaper, and above it this wins by a
    /// factor that grows without bound. **The corpus starts at 22.**
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * Self::bytes_per_pixel()
    }

    /// Per-pixel footprint, for the CLI's memory plan.
    pub const fn bytes_per_pixel() -> usize {
        size_of::<u16>()                    // anchor
            + size_of::<f32>()              // anchor_focus
            + 3 * size_of::<f32>()          // triple
            + size_of::<f32>()              // floor
            + TOP_K * size_of::<f32>()      // top_val
            + TOP_K * size_of::<u16>()      // top_idx
            + size_of::<f32>()              // far_val
            + size_of::<u16>()              // far_idx
            + 2 * size_of::<f32>() // z, w
    }

    /// Temperature of the posterior sums, in regularised response units.
    ///
    /// The **calibrated** scale, from the injected noise model by way of
    /// [`FOCUS_NOISE_SD`] — never `std_k(f_k)`. M32 measured the self-normalised
    /// alternative to be blind and non-monotone (fact 260) and SYNTHESIS
    /// discipline 120 forbids shipping it. It is the standard deviation of a
    /// *difference* of two responses, matching
    /// [`Gate::tolerance`](crate::merge::Gate::tolerance) at threshold 1, so the
    /// soft posterior and the hard gate are on one scale by construction.
    #[inline]
    pub fn temperature() -> f32 {
        std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
    }

    /// Fold one frame in.
    ///
    /// `fine` is that frame's field from
    /// [`FocusField::compute_with_fine`](crate::focus::FocusField::compute_with_fine);
    /// `regularised` is the *same* field that was folded into pass one for this
    /// frame index. Both are required because the two scales answer different
    /// questions and neither substitutes for the other.
    pub fn fold(&mut self, frame_index: u16, fine: &[f32], regularised: &[f32]) -> Result<()> {
        let px = self.geom.pixels();
        if fine.len() != px {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (fine.len(), 1),
                want: (px, 1),
            });
        }
        if regularised.len() != px {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (regularised.len(), 1),
                want: (px, 1),
            });
        }
        assert_ne!(frame_index, NO_FRAME, "frame index {NO_FRAME} is reserved");
        let t = Self::temperature();

        for i in 0..px {
            let f = fine[i];
            let a = self.anchor[i];

            if a != NO_FRAME {
                if frame_index == a {
                    self.triple[i][1] = f;
                } else if frame_index + 1 == a {
                    self.triple[i][0] = f;
                } else if a + 1 == frame_index {
                    self.triple[i][2] = f;
                }
                let sep = frame_index.abs_diff(a);
                if sep >= PEAK_SEPARATION && beats(f, frame_index, self.far_val[i], self.far_idx[i])
                {
                    self.far_val[i] = f;
                    self.far_idx[i] = frame_index;
                }
            }

            if f < self.floor[i] {
                self.floor[i] = f;
            }
            insert_top(&mut self.top_val[i], &mut self.top_idx[i], f, frame_index);

            // u <= 0 by construction: anchor_focus is the max of the regularised
            // field over every frame, so exp(u) is in (0, 1] and no term can
            // overflow however far out of focus the frame is.
            let u = (regularised[i] - self.anchor_focus[i]) / t;
            let e = u.exp();
            self.z[i] += e;
            self.w[i] += u * e;
        }

        self.frames += 1;
        self.max_index = self.max_index.max(frame_index);
        Ok(())
    }

    /// Reduce another worker's partial gather into this one.
    ///
    /// Refuses two halves built from different pass ones, exactly as
    /// [`Estimator::absorb`](crate::merge::Estimator::absorb) does: statistics
    /// anchored on different winners are not commensurable and silently reducing
    /// them would produce a triple centred on nothing.
    pub fn absorb(&mut self, other: &ThroughFocus) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: usize::MAX,
                got: (other.geom.width, other.geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        assert_eq!(
            self.anchor, other.anchor,
            "through-focus gathers anchored on different winner fields cannot be reduced"
        );

        for i in 0..self.geom.pixels() {
            for s in 0..3 {
                // Each slot is written by exactly one frame index, so at most
                // one side can hold it and the merge is a pick, not a choice.
                if self.triple[i][s].is_nan() {
                    self.triple[i][s] = other.triple[i][s];
                }
            }
            if other.floor[i] < self.floor[i] {
                self.floor[i] = other.floor[i];
            }
            for k in 0..TOP_K {
                if other.top_idx[i][k] == NO_FRAME {
                    break;
                }
                insert_top(
                    &mut self.top_val[i],
                    &mut self.top_idx[i],
                    other.top_val[i][k],
                    other.top_idx[i][k],
                );
            }
            if beats(
                other.far_val[i],
                other.far_idx[i],
                self.far_val[i],
                self.far_idx[i],
            ) {
                self.far_val[i] = other.far_val[i];
                self.far_idx[i] = other.far_idx[i];
            }
            self.z[i] += other.z[i];
            self.w[i] += other.w[i];
        }
        self.frames += other.frames;
        self.max_index = self.max_index.max(other.max_index);
        Ok(())
    }

    // ---- (a) sub-frame peak, by parabola fit ----

    /// Sub-frame offset of the peak from the anchor, in frames.
    ///
    /// Three-point parabola through the fine responses at `k* - 1, k*, k* + 1`.
    /// M33 measured the parabola to be 4.03x better than argmax at recovering
    /// peak **position** and only 9.4% worse than a log-domain fit (fact 273), so
    /// for position it is the right instrument and the extra logarithms are not
    /// worth it. **It is disqualifying for peak HEIGHT** — that is the same
    /// fact — which is why [`subframe_deficit`](Self::subframe_deficit) does not
    /// use it.
    ///
    /// `None` where the triple is incomplete (an anchor at the bracket boundary)
    /// or where the fitted quadratic is not concave, which means the three
    /// samples do not bracket a maximum at all.
    pub fn subframe_offset(&self, i: usize) -> Option<f32> {
        let [l, c, r] = self.triple[i];
        parabola_vertex(l, c, r).map(|(d, _)| d)
    }

    /// Absolute sub-frame peak position, `k* + offset`.
    pub fn subframe_peak(&self, i: usize) -> Option<f32> {
        self.subframe_offset(i).map(|d| self.anchor[i] as f32 + d)
    }

    /// Local baseline-subtracted log-Gaussian width in acquisition frames.
    /// This describes the three-sample curve, not calibrated depth uncertainty.
    /// Missing, nonpositive or nonconcave triples have no measured width.
    pub fn local_peak_width(&self, i: usize) -> Option<f32> {
        let [l, c, r] = self.triple[i];
        let floor = self.floor[i];
        let [l, c, r] = [l - floor, c - floor, r - floor];
        if ![l, c, r].into_iter().all(|v| v.is_finite() && v > 0.0) {
            return None;
        }
        let curvature = 0.5 * (l.ln() + r.ln()) - c.ln();
        if !curvature.is_finite() || curvature >= 0.0 {
            return None;
        }
        let width = (-0.5 / curvature).sqrt();
        width.is_finite().then_some(width)
    }

    /// Fraction of the true peak response given up by landing between frames.
    ///
    /// Confidence channel **C3** of M34's vector, and the reason the log domain
    /// is not optional. M33/M35 measured a **log-domain fit with the baseline
    /// subtracted** to beat the linear parabola on peak height on all three
    /// stacks tested (2.05x / 1.53x / 1.79x), with 91% of the margin coming from
    /// the log domain and 9% from the baseline (facts 272, 302, 304). The
    /// baseline used here is [`floor`](Self::floor), the curve's own minimum over
    /// the whole stack, which is why the floor is carried at all.
    ///
    /// The value is `1 - f(k*) / f(peak)` on baseline-subtracted responses, so it
    /// is in `[0, 1)`. It reduces to `1 - exp(b^2 / (4a))` in the fitted
    /// log-quadratic's coefficients and is evaluated that way, which keeps it
    /// bounded without ever exponentiating a large number.
    ///
    /// `None` where the triple is incomplete, where any baseline-subtracted
    /// sample is non-positive (the logarithm does not exist), or where the fit is
    /// not concave.
    pub fn subframe_deficit(&self, i: usize) -> Option<f32> {
        let [l, c, r] = self.triple[i];
        let b = self.floor[i];
        if !b.is_finite() {
            return None;
        }
        let (l, c, r) = (l - b, c - b, r - b);
        if !(l > 0.0 && c > 0.0 && r > 0.0) {
            return None;
        }
        let (ll, lc, lr) = (l.ln(), c.ln(), r.ln());
        // q(x) = a x^2 + bq x + lc through (-1, ll), (0, lc), (1, lr).
        let a = 0.5 * (ll + lr) - lc;
        // Strictly concave, and NaN is not concave. `matches!` on `partial_cmp`
        // rather than `!(a < 0.0)` so the NaN branch is visible rather than
        // implied by operator negation.
        if !matches!(a.partial_cmp(&0.0), Some(Ordering::Less)) {
            return None;
        }
        let bq = 0.5 * (lr - ll);
        // q(x*) - q(0) = -bq^2 / (4a) >= 0, so the ratio is exp of a
        // non-positive number and the deficit lands in [0, 1).
        Some(1.0 - (bq * bq / (4.0 * a)).exp())
    }

    // ---- (b) top-k ----

    /// The `TOP_K` largest fine responses at a pixel, descending. Unfolded slots
    /// are [`f32::NEG_INFINITY`].
    pub fn top_values(&self, i: usize) -> &[f32; TOP_K] {
        &self.top_val[i]
    }

    /// Their frame indices, in the same order. Unfolded slots are `u16::MAX`.
    pub fn top_indices(&self, i: usize) -> &[u16; TOP_K] {
        &self.top_idx[i]
    }

    /// Minimum fine response over the stack — the fit baseline.
    pub fn floor(&self, i: usize) -> f32 {
        self.floor[i]
    }

    /// Does the selection scale agree with the statistics scale about which
    /// frame is sharpest here?
    ///
    /// The honest exposure of the seam's one cost. A `false` does not mean the
    /// merge chose wrongly — the 27x27 window is the scale the project ruled on
    /// and a 5x5 window is much noisier — it means the triple at this pixel is
    /// not centred on the fine curve's own maximum, so
    /// [`subframe_offset`](Self::subframe_offset) is measuring the shape of the
    /// selection winner's neighbourhood rather than of the fine peak.
    ///
    /// **This is a diagnostic, not a screen.** MEASURED on 109MSDCF it is false
    /// at 78% of pixels, which is what a 5.94x noisier field should do and not
    /// a defect. **The 5.94 here is the right number**, and deliberately not
    /// fact 500's 1.815: both fields enter this comparison exactly as the merge
    /// consumes them — the selection field regularised, the fine field raw — and
    /// 5.94 is the ratio of their noise *in that state*. 1.815 answers a
    /// different question (the same operator at two windows under the same
    /// regulariser) and would understate this disagreement rate by 3.27x. See
    /// [`crate::through_focus::FINE_FOCUS_NOISE_SD`] for the decomposition.
    /// Use [`fine_peak_outside_triple`](Self::fine_peak_outside_triple)
    /// for anything that has to gate a pixel.
    pub fn anchor_is_fine_argmax(&self, i: usize) -> bool {
        self.top_idx[i][0] == self.anchor[i]
    }

    /// Is the fine argmax outside the retained triple entirely?
    ///
    /// The screening form of the scale disagreement, and the one that is
    /// actionable. Off-by-one disagreement is expected and harmless: the fine
    /// peak is still inside `[anchor-1, anchor+1]`, so the parabola fit is
    /// bracketing it and [`subframe_offset`](Self::subframe_offset) can still
    /// reach it. Off-by-two or more means the retained neighbourhood does not
    /// contain the fine peak at all and no refinement of the triple can recover
    /// it.
    ///
    /// Uses [`PEAK_SEPARATION`], so it is the same "outside the triple" rule the
    /// bimodality screen uses and the two cannot drift apart.
    pub fn fine_peak_outside_triple(&self, i: usize) -> bool {
        let (a, t) = (self.anchor[i], self.top_idx[i][0]);
        if a == NO_FRAME || t == NO_FRAME {
            return false;
        }
        a.abs_diff(t) >= PEAK_SEPARATION
    }

    // ---- (c) bimodality ----

    /// Prominence of the best peak at least [`PEAK_SEPARATION`] frames from the
    /// anchor, in fine-response units. **An upper bound, not an estimate.**
    ///
    /// `far_max - floor`. True topographic prominence would subtract the minimum
    /// of the curve *between* the two peaks, which is at least the global floor,
    /// so this can only read high. Its complement is what is trustworthy: a small
    /// value **proves** there is no separated secondary peak of that size, which
    /// is the direction an occlusion screen needs.
    ///
    /// `None` where no frame was at least [`PEAK_SEPARATION`] away, i.e. a stack
    /// of fewer than three frames or an anchor with no far side.
    pub fn bimodality(&self, i: usize) -> Option<f32> {
        let far = self.far_val[i];
        let b = self.floor[i];
        if !far.is_finite() || !b.is_finite() {
            return None;
        }
        Some(far - b)
    }

    /// [`bimodality`](Self::bimodality) in units of the fine field's own noise.
    ///
    /// Divided by `sqrt(2) * FINE_FOCUS_NOISE_SD` — the standard deviation of a
    /// *difference* of two fine responses, because the statistic is a difference.
    /// **This is the only form that may be thresholded.** M21's lesson
    /// (SYNTHESIS discipline 120) is that a curve-shape statistic gated on shape
    /// rather than on a calibrated noise scale measures the noise, not the scene.
    ///
    /// # This is a per-pixel value, and it must be consumed conditionally
    ///
    /// Occlusion enrichment is a **conditional** quantity: the multi-peak rate at
    /// depth steps against the rate on smooth depth, binned on an *independent*
    /// depth-step map. A **global** mean of this statistic against a
    /// frame-permutation null cannot detect occlusion, because permutation
    /// manufactures multi-peakedness and saturates the comparison — the null
    /// reads *higher* than the real stack everywhere, so the global ratio is
    /// pinned below 1 whatever the scene does. M18's `--stats` summary made
    /// exactly that mistake and concluded "no bimodality enrichment" from a
    /// 0.86x global ratio on `coffee-bean`, where M21 measures **4.38x**
    /// conditioned properly against a null of 1.01x. Bin this before you
    /// summarise it.
    pub fn bimodality_sigma(&self, i: usize) -> Option<f32> {
        self.bimodality(i)
            .map(|v| v / (std::f32::consts::SQRT_2 * FINE_FOCUS_NOISE_SD))
    }

    /// Frame index of the separated secondary peak, if there is one.
    ///
    /// The channel a later occlusion stage needs: not just *that* a second layer
    /// is present, but *which frame* it is in focus in.
    pub fn far_index(&self, i: usize) -> Option<u16> {
        (self.far_idx[i] != NO_FRAME).then_some(self.far_idx[i])
    }

    // ---- posterior summaries ----

    /// Perplexity of the softmax posterior over frame-of-best-focus.
    ///
    /// Confidence channel **C2**. `exp(H)` for `p_k ∝ exp(u_k)` with `u_k` the
    /// regularised response relative to the winner's, divided by
    /// [`temperature`](Self::temperature). It reads 1 where one frame is
    /// unambiguously sharpest and rises toward the frame count where the stack
    /// cannot tell.
    ///
    /// **Untruncated.** It is computed from the two exact sums `Z` and `W`, not
    /// from the top-k list, so it is not capped at [`TOP_K`] and it is the
    /// channel to use where fact 283's tail matters. The identity is
    /// `H = ln Z - W / Z`, which needs no per-frame revisit.
    ///
    /// It is measured on the **regularised** field, deliberately: this is the
    /// posterior over the quantity the merge actually decides on, so it is
    /// commensurable with [`Estimator::n_eff`](crate::merge::Estimator::n_eff)
    /// rather than being a second opinion on a different scale.
    ///
    /// M32's warning applies to any *threshold* placed on it: the no-information
    /// fixed point of a softmax posterior is not `H / ln n = 1` and drifts with
    /// `n` (fact 262), so a normalised-entropy cut must be simulated per frame
    /// count and never reasoned about.
    pub fn posterior_perplexity(&self, i: usize) -> f32 {
        let z = self.z[i] as f64;
        // A pixel that folded no frame, or folded NaN, has a degenerate
        // posterior; perplexity 1 is "certain", which is the conservative
        // reading for a pixel that will be caught by the flags anyway.
        if !matches!(z.partial_cmp(&0.0), Some(Ordering::Greater)) {
            return 1.0;
        }
        let h = z.ln() - self.w[i] as f64 / z;
        h.max(0.0).exp() as f32
    }

    /// Did the winner land on the first or last frame of the stack?
    ///
    /// Confidence channel **C4**, and the same definition as
    /// [`Estimator::at_bracket_boundary`](crate::merge::Estimator::at_bracket_boundary):
    /// one frame deep, on the regularised winner. Not fact 300's quantity — see
    /// that method for why the two must never be quoted as one number.
    pub fn at_bracket_boundary(&self, i: usize) -> bool {
        let k = self.anchor[i];
        k == 0 || k == self.max_index
    }
}

/// Ties to the lower frame index, stated rather than left to visitation order.
#[inline]
fn beats(val: f32, idx: u16, cur_val: f32, cur_idx: u16) -> bool {
    val > cur_val || (val == cur_val && idx < cur_idx)
}
/// The winner's anchor landed on the first or last frame of the bracket.
pub const FLAG_BRACKET_BOUNDARY: u8 = 1 << 0;
/// A separated secondary peak cleared the noise cut — possible occlusion.
pub const FLAG_BIMODAL: u8 = 1 << 1;
/// The fine scale puts the sharpest frame OUTSIDE the retained triple, so the
/// parabola cannot reach it. Off-by-one disagreement does not set this.
pub const FLAG_SCALE_DISAGREEMENT: u8 = 1 << 2;

/// M34's confidence **vector** at one pixel.
///
/// A vector, not a score, and that is a measured finding rather than a taste:
/// M34 found C1 to be *anti*-correlated with C3's target — selecting the worst
/// 5% by predicted sigma gives only a **0.89x** lift on sub-frame deficit — so
/// **no monotone scalar summary of these channels is faithful** (facts 280-282).
/// The honest "do not trust this pixel" answer is the *union* of the channels'
/// tails, which M34 measured at 14.278% of pixels, not a weighted sum.
///
/// Publishing a single number here would be the defect, so this type
/// deliberately does not offer one.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ConfidenceVector {
    /// **C1** — predicted standard deviation of the merged green luma, in DN,
    /// from the calibrated model and the admitted count. Underestimates at large
    /// `n` because fixed-pattern noise does not divide by `sqrt(n)`.
    pub predicted_sigma: f32,
    /// **C2** — perplexity of the posterior over frame-of-best-focus. 1 where
    /// decided, up to the frame count where not.
    pub perplexity: f32,
    /// **C3** — fraction of peak focus response given up to sampling.
    /// `None` where no concave log fit exists.
    pub subframe_deficit: Option<f32>,
    /// **C4** — the flag bits above.
    pub flags: u8,
}

impl ConfidenceVector {
    pub fn has(&self, flag: u8) -> bool {
        self.flags & flag != 0
    }
}

impl ThroughFocus {
    /// Assemble M34's confidence vector at one pixel.
    ///
    /// `bimodality_sigma_cut` is in units of a *difference* of fine responses and
    /// has **no default in this crate on purpose**. The distribution of
    /// [`bimodality_sigma`](Self::bimodality_sigma) depends on the frame count
    /// through an order statistic — it is a max over `n - 3` frames minus a min
    /// over `n` — so a cut transferred between stacks of different depth is not
    /// the same cut. Calibrate it against the permutation placebo
    /// ([`new_permuted`](Self::new_permuted)) on the stack in hand.
    pub fn confidence(
        &self,
        n_admitted: u16,
        merged_luma_dn: f32,
        noise: &crate::noise::NoiseModel,
        i: usize,
        bimodality_sigma_cut: f32,
    ) -> ConfidenceVector {
        let mut flags = 0u8;
        if self.at_bracket_boundary(i) {
            flags |= FLAG_BRACKET_BOUNDARY;
        }
        if self
            .bimodality_sigma(i)
            .is_some_and(|b| b >= bimodality_sigma_cut)
        {
            flags |= FLAG_BIMODAL;
        }
        if self.fine_peak_outside_triple(i) {
            flags |= FLAG_SCALE_DISAGREEMENT;
        }
        ConfidenceVector {
            predicted_sigma: noise.green_luma_sigma(merged_luma_dn)
                * crate::merge::selection_inflation(n_admitted)
                / (n_admitted.max(1) as f32).sqrt(),
            perplexity: self.posterior_perplexity(i),
            subframe_deficit: self.subframe_deficit(i),
            flags,
        }
    }
}

/// How a [`do_not_trust_mask`] was arrived at, so the union can be audited
/// channel by channel instead of taken on faith.
#[derive(Debug, Clone, Copy, Default)]
pub struct MaskBreakdown {
    pub by_sigma: usize,
    pub by_perplexity: usize,
    pub by_deficit: usize,
    pub by_flags: usize,
    pub union: usize,
    pub total: usize,
    /// The value each numeric channel's tail cut landed on, for the report.
    pub sigma_cut: f32,
    pub perplexity_cut: f32,
    pub deficit_cut: f32,
}

/// The union "do not trust" mask over a whole plane.
///
/// Takes the worst `tail` fraction of each numeric channel independently and
/// ORs them with the flag bits. This is M34's construction and its 14.278%
/// figure is what a `tail` of 0.05 produced there.
///
/// The union is deliberately not a vote or a weighted sum. Facts 280-282 measured
/// the channels to disagree about which pixels are bad — which is what makes each
/// one worth carrying and what makes any scalar collapse of them a lie.
pub fn do_not_trust_mask(vectors: &[ConfidenceVector], tail: f64) -> (Vec<bool>, MaskBreakdown) {
    let mut b = MaskBreakdown {
        total: vectors.len(),
        ..Default::default()
    };
    let mut mask = vec![false; vectors.len()];
    if vectors.is_empty() {
        return (mask, b);
    }

    // A pixel with no fit is not "good"; it is unmeasured, and it is caught by
    // the flags or by the tail of whichever channel does exist.
    b.sigma_cut = upper_tail_cut(vectors.iter().map(|v| v.predicted_sigma), tail);
    b.perplexity_cut = upper_tail_cut(vectors.iter().map(|v| v.perplexity), tail);
    b.deficit_cut = upper_tail_cut(
        vectors.iter().map(|v| v.subframe_deficit.unwrap_or(0.0)),
        tail,
    );

    for (i, v) in vectors.iter().enumerate() {
        let mut bad = false;
        if v.predicted_sigma >= b.sigma_cut {
            b.by_sigma += 1;
            bad = true;
        }
        if v.perplexity >= b.perplexity_cut {
            b.by_perplexity += 1;
            bad = true;
        }
        if v.subframe_deficit.unwrap_or(0.0) >= b.deficit_cut {
            b.by_deficit += 1;
            bad = true;
        }
        if v.flags != 0 {
            b.by_flags += 1;
            bad = true;
        }
        mask[i] = bad;
        if bad {
            b.union += 1;
        }
    }
    (mask, b)
}

/// Value at the `1 - tail` quantile, by linear-time selection.
fn upper_tail_cut(vals: impl Iterator<Item = f32>, tail: f64) -> f32 {
    let mut v: Vec<f32> = vals.filter(|x| x.is_finite()).collect();
    if v.is_empty() {
        return f32::INFINITY;
    }
    let k = (((1.0 - tail) * v.len() as f64).floor() as usize).min(v.len() - 1);
    let (_, nth, _) = v.select_nth_unstable_by(k, |a, b| a.partial_cmp(b).unwrap());
    *nth
}

/// A deterministic frame permutation for [`ThroughFocus::new_permuted`].
///
/// Seeded Fisher-Yates over SplitMix64, so it is reproducible from the seed
/// alone and needs no dependency.
///
/// # Why not a rotation
///
/// Because a rotation does not work, and the failure is silent. `k -> (k + s)
/// mod n` preserves `|a - b|` everywhere except across one wrap point, so a
/// statistic screened on "at least `PEAK_SEPARATION` frames from the anchor"
/// sees an almost identical set and the placebo returns the real answer. This
/// milestone shipped a rotation first and measured a placebo ratio of exactly
/// **1.0000x** — indistinguishable from "the statistic is pure noise", which is
/// the very reading the null exists to rule out. A null must be checked for
/// being a null; the test `shuffle_destroys_adjacency_which_a_rotation_does_not`
/// in this module is that check.
pub fn shuffled_indices(n: usize, seed: u64) -> Vec<u16> {
    let mut v: Vec<u16> = (0..n as u16).collect();
    let mut s = seed;
    let mut next = move || {
        s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = s;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    };
    for i in (1..n).rev() {
        let j = (next() % (i as u64 + 1)) as usize;
        v.swap(i, j);
    }
    v
}

/// Insert `(val, idx)` into a descending top-k list, ignoring a repeat of an
/// index already present.
///
/// The idempotence matters: [`ThroughFocus::absorb`] replays the other side's
/// list into this one, and without it a reduce would be able to enter the same
/// frame twice and inflate a spread statistic.
#[inline]
fn insert_top(vals: &mut [f32; TOP_K], idxs: &mut [u16; TOP_K], val: f32, idx: u16) {
    if idxs.contains(&idx) {
        return;
    }
    let mut pos = TOP_K;
    for k in 0..TOP_K {
        if beats(val, idx, vals[k], idxs[k]) {
            pos = k;
            break;
        }
    }
    if pos == TOP_K {
        return;
    }
    for k in (pos + 1..TOP_K).rev() {
        vals[k] = vals[k - 1];
        idxs[k] = idxs[k - 1];
    }
    vals[pos] = val;
    idxs[pos] = idx;
}

/// Vertex of the parabola through `(-1, l), (0, c), (1, r)`.
///
/// Returns `(offset, peak_value)`, or `None` when the fit is not concave or a
/// sample is missing. The offset is clamped to `[-1, 1]`: outside that the three
/// samples do not bracket the peak and the extrapolation is not evidence.
#[inline]
fn parabola_vertex(l: f32, c: f32, r: f32) -> Option<(f32, f32)> {
    if !(l.is_finite() && c.is_finite() && r.is_finite()) {
        return None;
    }
    let denom = l - 2.0 * c + r;
    if !matches!(denom.partial_cmp(&0.0), Some(Ordering::Less)) {
        return None;
    }
    let d = 0.5 * (l - r) / denom;
    if !(-1.0..=1.0).contains(&d) {
        return None;
    }
    let peak = c - 0.25 * (l - r) * d;
    Some((d, peak))
}

/// The window radius the statistics are gathered at. Re-exported so a caller
/// cannot pick a different one by accident.
pub const STATS_RADIUS: usize = FINE_WINDOW_RADIUS;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::focus::{FocusField, SOBEL_RADIUS};
    use crate::noise::{Levels, NoiseModel, PlaneNoise, Provenance};

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// A noise model whose green-luma sigma is 1.0 DN and is effectively **flat
    /// in signal**, so the focus normalisation divides by a known constant.
    ///
    /// Copied deliberately from `merge::tests::unit_sigma_model` rather than
    /// re-derived, and the flatness is the load-bearing part: a model with a
    /// real gain makes the divisor a function of the luma at that pixel, and the
    /// measured mean response then comes out **0.929x** the closed-form Rayleigh
    /// mean — not because the operator is wrong but because `E[1/sigma(L)]` is
    /// not `1/sigma(E[L])`. That is a 7% silent error in a constant every
    /// threshold in this module is quoted against.
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

    /// SplitMix64. Discipline 221: a plain LCG's lattice aliases against the box
    /// filters and made the sibling constant vary 1.30x across seeds. Identical
    /// to `merge::tests::Rng` so that the two constants are measured by the same
    /// instrument and their ratio means something.
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

    /// Build a synthetic stack whose fine focus field at pixel `i` for frame `k`
    /// is exactly `curve(k, i)`, and gather statistics over it. The regularised
    /// field is taken to be the same curve, so the anchor is the curve's argmax.
    fn gather(
        g: PlaneGeometry,
        frames: u16,
        order: &[u16],
        curve: impl Fn(u16, usize) -> f32,
    ) -> ThroughFocus {
        let mut stats = FocusStats::new(g);
        for k in 0..frames {
            let f: Vec<f32> = (0..g.pixels()).map(|i| curve(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let mut tf = ThroughFocus::new(&stats);
        for k in order {
            let f: Vec<f32> = (0..g.pixels()).map(|i| curve(*k, i)).collect();
            tf.fold(*k, &f, &f).unwrap();
        }
        tf
    }

    // ---- the fine scale ----

    /// The sibling of `merge::the_focus_noise_constant_is_the_measured_one`, and
    /// it exists for the same reason: every threshold on a fine-field statistic
    /// is quoted in units of this constant, so if it is wrong the bimodality
    /// screen is silently mis-gated and nothing errors.
    ///
    /// Discipline 220/221 in force: SplitMix64, twelve seeds, a 512x512 plane
    /// (192x192 reads ~10% low from finite-region SD bias), and a tolerance
    /// derived from the measured standard error rather than picked.
    #[test]
    fn the_fine_focus_noise_constant_is_the_measured_one() {
        let g = geom(512, 512);
        let noise = unit_sigma_model();
        let margin = SOBEL_RADIUS + FINE_WINDOW_RADIUS + 1;
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
        let mut fine = vec![0.0f32; g.pixels()];
        for seed in seeds {
            let mut rng = Rng::new(seed);
            let luma: Vec<f32> = (0..g.pixels()).map(|_| rng.normal()).collect();
            field.compute_with_fine(&luma, &noise, FINE_WINDOW_RADIUS, &mut fine);

            let mut vals = Vec::new();
            for y in margin..g.height - margin {
                for x in margin..g.width - margin {
                    vals.push(fine[y * g.width + x] as f64);
                }
            }
            let mean = vals.iter().sum::<f64>() / vals.len() as f64;
            let var =
                vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (vals.len() - 1) as f64;
            means.push(mean);
            sds.push(var.sqrt());
        }

        // Structural anchor: a box mean does not move a mean, so the fine field
        // under unit-sigma noise must still average the Rayleigh mean.
        let rayleigh_mean = 0.125 * 12f64.sqrt() * (std::f64::consts::PI / 2.0).sqrt();
        for m in &means {
            let r = m / rayleigh_mean;
            assert!(
                (0.97..1.03).contains(&r),
                "fine-field response mean {m:.4} is {r:.3}x the closed-form \
                 Rayleigh mean {rayleigh_mean:.4}; the operator chain is not \
                 doing what this test assumes"
            );
        }

        let n = sds.len() as f64;
        let mean_sd = sds.iter().sum::<f64>() / n;
        let spread = sds.iter().map(|s| (s - mean_sd).powi(2)).sum::<f64>() / (n - 1.0);
        let sem = (spread / n).sqrt();
        let rel_sem = sem / mean_sd;
        assert!(
            rel_sem < 0.05,
            "standard error {rel_sem:.4} is too large for this test to have \
             power; add seeds or enlarge the plane. sds = {sds:?}"
        );

        let deviation = ((mean_sd - FINE_FOCUS_NOISE_SD as f64) / sem).abs();
        assert!(
            deviation < 4.0,
            "measured fine focus noise SD {mean_sd:e} +/- {sem:e} is \
             {deviation:.1} standard errors from the declared \
             FINE_FOCUS_NOISE_SD {FINE_FOCUS_NOISE_SD:e} (relative SEM \
             {rel_sem:.4}); if the operator or FINE_WINDOW_RADIUS changed, \
             re-measure and update the constant"
        );
    }

    /// **The two scales are not interchangeable, and this measures the trade
    /// rather than restating it.**
    ///
    /// This test used to read `assert!((5.0..7.0).contains(&(FINE_FOCUS_NOISE_SD
    /// / FOCUS_NOISE_SD)))`. That is rule 35 exactly: both terms are compile-time
    /// constants in this crate, so the assertion's subject and object are the
    /// same two values and it had **no power to fail** against anything but an
    /// edit to the constants it was made of. M52 flagged it as "the framing fact
    /// 500 retired" and asked the fold to carry it; M58 found the framing is
    /// defensible and the *power* was the real defect.
    ///
    /// What it does now: measures all three SDs on one set of twelve 512x512
    /// noise planes, through the real operator and the real regulariser, on an
    /// identical interior so the ratios compare the same pixels, and asserts the
    /// **decomposition** against fact 500's published numbers.
    ///
    /// ```text
    /// fine_bare / sel  = 5.94   the two fields AS CONSUMED -- what this test's name claims
    /// fine_reg  / sel  = 1.815  fact 500: the same operator, two windows, ONE regulariser
    /// fine_bare / fine_reg = 3.273  the price of consuming the fine field raw
    /// ```
    ///
    /// Rule 20 — inputs that make this fail: regularising the fine arm (then
    /// 5.94 collapses to 1.8 and the first assertion fires); dropping the
    /// regulariser from the selection arm (fact 501's +24%, and all three
    /// ratios move); a changed `FINE_WINDOW_RADIUS` or `REGULARISER_RADIUS`;
    /// and a normalisation that is not flat in signal, which the module's own
    /// notes measure at 0.929x.
    ///
    /// Rule 34 — the plant supplies unit-variance Gaussian luma and
    /// [`unit_sigma_model`] makes the divisor exactly 1.0, so this test shares
    /// the *normalisation* constant with the code under test and can prove
    /// nothing about it. It is a test of the operator chain and of the two
    /// window radii, which is all it claims. The absolute calibration is
    /// falsifiable only against real data.
    #[test]
    fn the_fine_scale_is_much_noisier_than_the_selection_scale() {
        let g = geom(512, 512);
        let noise = unit_sigma_model();
        // One margin for all three arms, taken as the widest any of them needs
        // (Sobel + selection window + regulariser), so the three SDs are over
        // an identical pixel set and their ratios are exact comparisons.
        let margin =
            SOBEL_RADIUS + 1 + crate::focus::WINDOW_RADIUS + crate::merge::REGULARISER_RADIUS;
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

        let interior_sd = |f: &[f32]| -> f64 {
            let mut vals = Vec::new();
            for y in margin..g.height - margin {
                for x in margin..g.width - margin {
                    vals.push(f64::from(f[y * g.width + x]));
                }
            }
            let mean = vals.iter().sum::<f64>() / vals.len() as f64;
            (vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (vals.len() - 1) as f64).sqrt()
        };

        let mut field = FocusField::new(g);
        let mut fine = vec![0.0f32; g.pixels()];
        let mut scratch = vec![0.0f32; g.pixels()];
        let mut reg = vec![0.0f32; g.pixels()];
        let (mut sels, mut bares, mut regs) = (Vec::new(), Vec::new(), Vec::new());
        for seed in seeds {
            let mut rng = Rng::new(seed);
            let luma: Vec<f32> = (0..g.pixels()).map(|_| rng.normal()).collect();
            field.compute_with_fine(&luma, &noise, FINE_WINDOW_RADIUS, &mut fine);

            bares.push(interior_sd(&fine));
            crate::merge::regularise(field.values(), g, &mut scratch, &mut reg);
            sels.push(interior_sd(&reg));
            crate::merge::regularise(&fine, g, &mut scratch, &mut reg);
            regs.push(interior_sd(&reg));
        }

        let avg = |v: &[f64]| v.iter().sum::<f64>() / v.len() as f64;
        let rel_sem = |v: &[f64]| {
            let m = avg(v);
            let n = v.len() as f64;
            let var = v.iter().map(|s| (s - m).powi(2)).sum::<f64>() / (n - 1.0);
            (var / n).sqrt() / m
        };
        let (sel, bare, regd) = (avg(&sels), avg(&bares), avg(&regs));
        let as_consumed = bare / sel;
        let same_config = regd / sel;
        let regulariser_term = bare / regd;

        println!(
            "selection w13+r8 {sel:e}  fine w2 bare {bare:e}  fine w2+r8 {regd:e}\n\
             as consumed {as_consumed:.4} (published pair 5.942)  \
             same-config {same_config:.4} (fact 500: 1.815)  \
             regulariser {regulariser_term:.4} (fact 500: 3.273)"
        );

        // Rule 36: the instrument must be tight enough for the bands below to
        // reject anything. At ~0.5% relative sem a +/-3% band rejects fact
        // 501's +24%, fact 509's +52.8% and fact 510's +12.5% alike.
        for (label, v) in [
            ("selection", &sels),
            ("fine bare", &bares),
            ("fine reg", &regs),
        ] {
            assert!(
                rel_sem(v) < 0.01,
                "{label} relative sem {:.4} is too large for this test to have power",
                rel_sem(v)
            );
        }

        // Anchors, so a failure localises to one arm rather than to a ratio.
        assert!(
            (sel - f64::from(FOCUS_NOISE_SD)).abs() / f64::from(FOCUS_NOISE_SD) < 0.02,
            "the selection arm must reproduce FOCUS_NOISE_SD; got {sel:e}"
        );
        assert!(
            (bare - f64::from(FINE_FOCUS_NOISE_SD)).abs() / f64::from(FINE_FOCUS_NOISE_SD) < 0.02,
            "the fine arm must reproduce FINE_FOCUS_NOISE_SD; got {bare:e}"
        );

        assert!(
            (as_consumed - 5.942).abs() / 5.942 < 0.03,
            "the fine field is supposed to be materially noisier AS CONSUMED, by \
             the ratio of the two published constants; got {as_consumed:.4}x"
        );
        assert!(
            (same_config - 1.815).abs() / 1.815 < 0.03,
            "fact 500's same-configuration quantity is 1.815 (M52 measured 1.8145, \
             M58 1.8114); got {same_config:.4}x"
        );
        assert!(
            (regulariser_term - 3.273).abs() / 3.273 < 0.03,
            "fact 500's overstatement factor is 3.273x; got {regulariser_term:.4}x"
        );
    }

    /// `compute_with_fine` must not perturb the selection field. If it did, the
    /// statistics gather would be changing the merge, which is exactly what it
    /// is forbidden to do.
    #[test]
    fn gathering_statistics_cannot_move_the_selection_field() {
        let g = geom(96, 72);
        let noise = unit_sigma_model();
        let mut rng = Rng::new(0xABCD);
        let luma: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = (i % g.width, i / g.width);
                (if (x / 3 + y / 5) % 2 == 0 {
                    900.0
                } else {
                    300.0
                }) + 20.0 * rng.normal()
            })
            .collect();

        let mut a = FocusField::new(g);
        a.compute(&luma, &noise);
        let plain = a.values().to_vec();

        let mut b = FocusField::new(g);
        let mut fine = vec![0.0f32; g.pixels()];
        b.compute_with_fine(&luma, &noise, FINE_WINDOW_RADIUS, &mut fine);

        assert_eq!(plain, b.values(), "the selection field moved");
        assert_ne!(plain, fine, "the fine field is not actually a second scale");
    }

    // ---- the fold is exactly mergeable ----

    #[test]
    fn the_gather_is_order_independent_and_absorb_matches_a_sequential_fold() {
        let g = geom(7, 5);
        let n = 9u16;
        // A distinct peak per pixel plus a reproducible wobble, so no two pixels
        // share an anchor and the top-k lists differ across the plane.
        let curve = |k: u16, i: usize| {
            let peak = (i % 7) as f32 + 1.0;
            let d = k as f32 - peak;
            10.0 - d * d + ((i * 13 + k as usize * 5) % 3) as f32 * 0.01
        };
        let all: Vec<u16> = (0..n).collect();
        let whole = gather(g, n, &all, curve);
        let shuffled = gather(g, n, &[4, 1, 8, 0, 7, 3, 6, 2, 5], curve);

        for i in 0..g.pixels() {
            assert_eq!(whole.top_val[i], shuffled.top_val[i], "top values at {i}");
            assert_eq!(whole.top_idx[i], shuffled.top_idx[i], "top indices at {i}");
            assert_eq!(whole.floor[i], shuffled.floor[i], "floor at {i}");
            assert_eq!(whole.far_idx[i], shuffled.far_idx[i], "far index at {i}");
            assert_eq!(whole.triple[i][1], shuffled.triple[i][1], "peak at {i}");
            assert!(
                (whole.posterior_perplexity(i) - shuffled.posterior_perplexity(i)).abs() < 1e-4,
                "perplexity at {i}"
            );
        }

        for cut in 1..n as usize {
            let mut stats = FocusStats::new(g);
            for k in 0..n {
                let f: Vec<f32> = (0..g.pixels()).map(|i| curve(k, i)).collect();
                stats.fold(k, &f).unwrap();
            }
            let part = |ks: &[u16]| {
                let mut tf = ThroughFocus::new(&stats);
                for k in ks {
                    let f: Vec<f32> = (0..g.pixels()).map(|i| curve(*k, i)).collect();
                    tf.fold(*k, &f, &f).unwrap();
                }
                tf
            };
            let mut left = part(&all[..cut]);
            left.absorb(&part(&all[cut..])).unwrap();
            assert_eq!(left.frames_folded(), n as u32, "cut {cut}");
            for i in 0..g.pixels() {
                assert_eq!(left.top_idx[i], whole.top_idx[i], "cut {cut} top at {i}");
                assert_eq!(left.top_val[i], whole.top_val[i], "cut {cut} vals at {i}");
                assert_eq!(left.floor[i], whole.floor[i], "cut {cut} floor at {i}");
                assert_eq!(left.triple[i], whole.triple[i], "cut {cut} triple at {i}");
                assert_eq!(left.far_idx[i], whole.far_idx[i], "cut {cut} far at {i}");
                assert!(
                    (left.posterior_perplexity(i) - whole.posterior_perplexity(i)).abs() < 1e-3,
                    "cut {cut} perplexity at {i}"
                );
            }
        }
    }

    /// The whole claim of the module in one assertion: what pass two retains is
    /// enough to reproduce, exactly, what a third pass over the frames would
    /// compute. The reference here is a **full focus volume** — the O(frames)
    /// object the design exists to avoid — recomputed independently.
    #[test]
    fn the_statistics_match_a_full_focus_volume_with_no_third_pass() {
        let g = geom(11, 9);
        let n = 13u16;
        let curve = |k: u16, i: usize| {
            let peak = (i % 9) as f32 + 2.0;
            let d = k as f32 - peak;
            5.0 - 0.3 * d * d + ((i * 31 + k as usize * 17) % 11) as f32 * 0.05
        };
        let all: Vec<u16> = (0..n).collect();
        let tf = gather(g, n, &all, curve);

        // The forbidden object, built only to check the permitted one.
        let volume: Vec<Vec<f32>> = (0..n)
            .map(|k| (0..g.pixels()).map(|i| curve(k, i)).collect())
            .collect();

        for i in 0..g.pixels() {
            let col: Vec<f32> = volume.iter().map(|plane| plane[i]).collect();

            let mut want: Vec<(f32, u16)> = col
                .iter()
                .enumerate()
                .map(|(k, v)| (*v, k as u16))
                .collect();
            want.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap().then(a.1.cmp(&b.1)));
            for (k, w) in want.iter().enumerate().take(TOP_K) {
                assert_eq!(tf.top_val[i][k], w.0, "top {k} value at {i}");
                assert_eq!(tf.top_idx[i][k], w.1, "top {k} index at {i}");
            }

            let anchor = want[0].1;
            assert_eq!(tf.anchor[i], anchor);
            assert_eq!(
                tf.floor[i],
                col.iter().cloned().fold(f32::INFINITY, f32::min)
            );
            assert_eq!(tf.triple[i][1], col[anchor as usize]);
            if anchor > 0 {
                assert_eq!(tf.triple[i][0], col[anchor as usize - 1]);
            }
            if (anchor as usize) + 1 < col.len() {
                assert_eq!(tf.triple[i][2], col[anchor as usize + 1]);
            }

            let (mut fv, mut fi) = (f32::NEG_INFINITY, NO_FRAME);
            for (k, v) in col.iter().enumerate() {
                let k = k as u16;
                if k.abs_diff(anchor) >= PEAK_SEPARATION && beats(*v, k, fv, fi) {
                    fv = *v;
                    fi = k;
                }
            }
            assert_eq!(tf.far_idx[i], fi, "far index at {i}");
            assert_eq!(tf.far_val[i], fv, "far value at {i}");

            // And the posterior, from the volume, in f64.
            let t = ThroughFocus::temperature() as f64;
            let m = col[anchor as usize] as f64;
            let us: Vec<f64> = col.iter().map(|v| (*v as f64 - m) / t).collect();
            let z: f64 = us.iter().map(|u| u.exp()).sum();
            let w: f64 = us.iter().map(|u| u * u.exp()).sum();
            let want_pp = (z.ln() - w / z).max(0.0).exp();
            let got = tf.posterior_perplexity(i) as f64;
            assert!(
                (got - want_pp).abs() <= 1e-3 * want_pp.max(1.0),
                "perplexity at {i}: got {got} want {want_pp}"
            );
        }
    }

    // ---- (a) sub-frame position ----

    /// Positive control with a known answer: a parabola sampled off-centre by a
    /// known amount must return that amount. Null: sampled exactly on the peak,
    /// the offset is zero and the deficit is zero.
    #[test]
    fn the_parabola_recovers_a_planted_sub_frame_offset() {
        for &want in &[-0.4f32, -0.25, 0.0, 0.25, 0.4] {
            let g = geom(1, 1);
            let n = 7u16;
            let peak = 3.0 + want;
            let tf = gather(g, n, &(0..n).collect::<Vec<_>>(), |k, _| {
                let d = k as f32 - peak;
                4.0 - 0.5 * d * d
            });
            let got = tf.subframe_offset(0).expect("triple should be complete");
            assert!((got - want).abs() < 1e-3, "planted {want}, recovered {got}");
            if want == 0.0 {
                assert!(tf.subframe_deficit(0).unwrap() < 1e-4, "null must be flat");
            }
        }
    }

    /// The deficit must rise with the offset and vanish at zero, and it must be
    /// a fraction. A metric that could exceed 1 or go negative would not be a
    /// "fraction of response given up" at all.
    #[test]
    fn the_sub_frame_deficit_is_a_bounded_fraction_that_rises_with_the_offset() {
        let n = 9u16;
        let mut last = -1.0f32;
        for &off in &[0.0f32, 0.1, 0.2, 0.3, 0.4, 0.5] {
            let peak = 4.0 + off;
            let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
                let d = k as f32 - peak;
                1.0 + 8.0 * (-0.5 * d * d).exp()
            });
            let d = tf.subframe_deficit(0).expect("fit should exist");
            assert!((0.0..1.0).contains(&d), "deficit {d} out of range at {off}");
            assert!(d >= last - 1e-6, "deficit fell from {last} to {d} at {off}");
            last = d;
        }
        assert!(
            last > 0.02,
            "a half-frame miss on a sigma-1 Gaussian should give up a percent \
             or two of response, got {last}"
        );
    }

    /// A Gaussian peak's log is exactly a parabola, so the log fit must recover
    /// its height exactly where the linear fit cannot. This is fact 272/304's
    /// margin, reproduced as a unit test rather than cited.
    #[test]
    fn the_log_fit_beats_a_linear_fit_on_peak_height() {
        let n = 9u16;
        let (peak_k, amp, base, sigma) = (4.35f32, 8.0f32, 1.0f32, 1.0f32);
        let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
            let d = (k as f32 - peak_k) / sigma;
            base + amp * (-0.5 * d * d).exp()
        });
        let anchor = tf.anchor[0] as f32;
        let sampled = tf.triple[0][1] - base;
        let truth_deficit = 1.0 - sampled / amp;

        let log = tf.subframe_deficit(0).unwrap();
        let [l, c, r] = tf.triple[0];
        let (_, lin_peak) = parabola_vertex(l, c, r).unwrap();
        let lin = 1.0 - (c - base) / (lin_peak - base);

        assert!((anchor - 4.0).abs() < 1e-6, "anchor should be frame 4");
        assert!(
            (log - truth_deficit).abs() < 1e-4,
            "log fit should be exact on a Gaussian: got {log}, truth {truth_deficit}"
        );
        assert!(
            (lin - truth_deficit).abs() > 3.0 * (log - truth_deficit).abs(),
            "the linear fit is supposed to be materially worse here: \
             linear {lin}, log {log}, truth {truth_deficit}"
        );
    }

    #[test]
    fn a_peak_at_the_bracket_boundary_has_no_triple_and_says_so() {
        let n = 6u16;
        let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
            5.0 - k as f32
        });
        assert!(tf.at_bracket_boundary(0));
        assert_eq!(tf.subframe_offset(0), None);
        assert_eq!(tf.subframe_deficit(0), None);
    }

    #[test]
    fn a_flat_curve_has_no_concave_fit_rather_than_a_fabricated_peak() {
        let n = 5u16;
        let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |_, _| 3.0);
        assert_eq!(tf.subframe_offset(0), None);
        assert_eq!(tf.subframe_deficit(0), None);
    }

    // ---- (c) bimodality: null and positive control ----

    /// Positive control: a genuinely two-layer curve, with a second peak far
    /// from the anchor, must read large. Null: the same curve with the second
    /// peak removed must read at the shoulder level, which is much smaller.
    #[test]
    fn bimodality_fires_on_two_layers_and_not_on_one() {
        let n = 15u16;
        let bump = |k: u16, at: f32, amp: f32| {
            let d = k as f32 - at;
            amp * (-0.5 * d * d).exp()
        };
        let two = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
            1.0 + bump(k, 4.0, 6.0) + bump(k, 11.0, 4.0)
        });
        let one = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
            1.0 + bump(k, 4.0, 6.0)
        });

        let b2 = two.bimodality(0).unwrap();
        let b1 = one.bimodality(0).unwrap();
        assert_eq!(
            two.far_index(0),
            Some(11),
            "should point at the second layer"
        );
        assert!(
            b2 > 3.0,
            "a 4.0-amplitude second peak should show up whole, got {b2}"
        );
        // The unimodal arm does NOT read zero, and that is the documented
        // over-reporting, not a bug: at PEAK_SEPARATION = 2 the "far" sample can
        // still be the primary peak's own skirt, which for this sigma-1 Gaussian
        // is 6 * exp(-2) = 0.812 above the floor. The screen is an upper bound
        // and this is the size of the bound's slack on a clean curve.
        let skirt = 6.0 * (-2.0f32).exp();
        assert!(
            (b1 - skirt).abs() < 0.05,
            "the unimodal reading should be exactly the primary peak's skirt \
             {skirt:.3}, got {b1}"
        );
        assert!(
            b1 < 0.25 * b2,
            "and it must stay well clear of a real second layer: {b1} vs {b2}"
        );
        assert!(
            two.bimodality_sigma(0).unwrap() > 10.0,
            "and it must clear the fine field's noise scale by a wide margin"
        );
    }

    /// The bound is a bound. Its complement is what may be believed, so the test
    /// that matters is that it never reads *below* the true prominence.
    #[test]
    fn bimodality_is_an_upper_bound_on_true_prominence() {
        let n = 15u16;
        fn curve(k: u16) -> f32 {
            let d1 = k as f32 - 3.0;
            let d2 = k as f32 - 10.0;
            2.0 + 6.0 * (-0.5 * d1 * d1).exp() + 3.0 * (-0.5 * d2 * d2).exp()
        }
        let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| curve(k));
        let far = tf.far_idx[0];
        let anchor = tf.anchor[0];
        let (lo, hi) = (anchor.min(far), anchor.max(far));
        let saddle = (lo..=hi).map(curve).fold(f32::INFINITY, f32::min);
        let truth = tf.far_val[0] - saddle;
        let bound = tf.bimodality(0).unwrap();
        assert!(
            bound >= truth - 1e-5,
            "bound {bound} is below the true prominence {truth}"
        );
    }

    /// The honest null for the screen: pure noise, no scene. The statistic is a
    /// max over frames minus a min over frames, so it is **large by
    /// construction** even with nothing there — which is exactly why it is
    /// quoted in sigma and why a threshold has to be set against this, not
    /// against zero.
    ///
    /// The expected value is not the plain range of 12 normals (3.26 sd). The
    /// far-peak channel excludes the argmax **and both its neighbours**, so it is
    /// the maximum of the remaining nine, and the null lands near 2.7 rather than
    /// 3.3. Getting the exclusion wrong would move this, which is the point.
    #[test]
    fn the_bimodality_screen_has_a_measured_noise_floor_that_is_not_zero() {
        let n = 12u16;
        let g = geom(64, 64);
        let mut rng = Rng::new(0x51DE);
        let noiseless: Vec<Vec<f32>> = (0..n)
            .map(|_| (0..g.pixels()).map(|_| rng.normal()).collect())
            .collect();
        let mut stats = FocusStats::new(g);
        for (k, f) in noiseless.iter().enumerate() {
            stats.fold(k as u16, f).unwrap();
        }
        let mut tf = ThroughFocus::new(&stats);
        for (k, f) in noiseless.iter().enumerate() {
            tf.fold(k as u16, f, f).unwrap();
        }
        let vals: Vec<f32> = (0..g.pixels()).filter_map(|i| tf.bimodality(i)).collect();
        let mean = vals.iter().sum::<f32>() / vals.len() as f32;
        assert!(
            (2.4..3.1).contains(&mean),
            "pure-noise bimodality mean {mean} is not the expected \
             max-of-nine-minus-min-of-twelve statistic; the screen's null is \
             mis-specified"
        );
        assert!(
            mean < 3.26,
            "the null must sit BELOW the plain range of 12 normals, or the \
             far-peak exclusion is not excluding the peak"
        );
    }

    // ---- posterior ----

    /// Null and positive control for C2 in one test: a stack where one frame is
    /// unambiguously sharpest must read perplexity 1, and a stack where every
    /// frame is identical must read the frame count.
    #[test]
    fn perplexity_is_one_when_decided_and_the_frame_count_when_it_is_not() {
        let n = 8u16;
        let decided = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
            if k == 3 { 1.0 } else { 0.0 }
        });
        assert!(
            (decided.posterior_perplexity(0) - 1.0).abs() < 1e-3,
            "got {}",
            decided.posterior_perplexity(0)
        );

        let undecided = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |_, _| 1.0);
        assert!(
            (undecided.posterior_perplexity(0) - n as f32).abs() < 1e-2,
            "got {}",
            undecided.posterior_perplexity(0)
        );
    }

    /// It must be monotone in the thing it claims to measure. Widening the
    /// through-focus curve — the same scene sampled more densely — must raise
    /// the perplexity, and it must never exceed the frame count.
    ///
    /// The amplitude is fixed at `20 * FOCUS_NOISE_SD`, the scale
    /// `merge::real_focus_contrast_is_far_larger_than_the_noise_scale` measured
    /// real focus contrast to clear. Nothing here looks at the curve's own
    /// spread: the calibration is doing the work.
    #[test]
    fn perplexity_rises_with_the_width_of_the_acceptance_set() {
        const AMPLITUDE: f32 = 20.0 * FOCUS_NOISE_SD;
        let n = 12u16;
        let mut last = 0.0f32;
        for &width in &[0.2f32, 0.5, 1.0, 2.0, 4.0] {
            let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
                let d = (k as f32 - 6.0) / width;
                AMPLITUDE * (-0.5 * d * d).exp()
            });
            let p = tf.posterior_perplexity(0);
            assert!(
                p >= last - 1e-4,
                "perplexity fell: {last} -> {p} at {width}"
            );
            assert!(
                p <= n as f32 + 1e-3,
                "perplexity {p} exceeds the frame count"
            );
            last = p;
        }
        assert!(last > 2.0, "the widest curve should be genuinely undecided");
    }

    // ---- memory ----

    /// The ratchet. Constant in the frame count, and materially smaller than the
    /// focus volume it replaces at every stack size in the corpus.
    #[test]
    fn statistics_memory_is_constant_in_the_frame_count() {
        let g = geom(100, 100);
        let short = gather(g, 4, &[0, 1, 2, 3], |k, _| k as f32);
        let long = gather(g, 90, &(0..90).collect::<Vec<_>>(), |k, _| k as f32);
        assert_eq!(short.allocated_bytes(), long.allocated_bytes());
        assert_eq!(
            ThroughFocus::bytes_per_pixel(),
            60,
            "the per-pixel footprint is a published number; changing it changes \
             the CLI's memory plan and the ratchet in SYNTHESIS §3.2.1"
        );
        // The object this replaces, at the smallest stack in the corpus.
        let volume = 22 * size_of::<f32>();
        assert!(
            ThroughFocus::bytes_per_pixel() < volume,
            "a 22-frame fine focus volume is {volume} B/px; the statistics must \
             be cheaper than that or the seam decision was wrong"
        );
    }

    // ---- refusals ----

    #[test]
    fn a_mismatched_field_is_rejected_rather_than_silently_cropped() {
        let g = geom(4, 4);
        let stats = FocusStats::new(g);
        let mut tf = ThroughFocus::new(&stats);
        assert!(matches!(
            tf.fold(0, &[0.0; 12], &[0.0; 16]),
            Err(Error::DimensionMismatch { .. })
        ));
        assert!(matches!(
            tf.fold(0, &[0.0; 16], &[0.0; 12]),
            Err(Error::DimensionMismatch { .. })
        ));
    }

    #[test]
    fn reducing_gathers_from_different_winner_fields_is_refused() {
        let g = geom(4, 4);
        let a = gather(g, 3, &[0, 1, 2], |k, _| if k == 0 { 1.0 } else { 0.0 });
        let mut b = gather(g, 3, &[0, 1, 2], |k, _| if k == 2 { 1.0 } else { 0.0 });
        assert!(std::panic::catch_unwind(move || b.absorb(&a)).is_err());
    }

    /// A repeated frame index must not enter the top-k twice. Without the
    /// idempotence in `insert_top`, `absorb` would double-count the frames both
    /// sides happened to see and inflate every spread statistic.
    #[test]
    fn the_top_k_list_cannot_contain_a_frame_twice() {
        let mut vals = [f32::NEG_INFINITY; TOP_K];
        let mut idxs = [NO_FRAME; TOP_K];
        insert_top(&mut vals, &mut idxs, 5.0, 2);
        insert_top(&mut vals, &mut idxs, 5.0, 2);
        insert_top(&mut vals, &mut idxs, 9.0, 2);
        assert_eq!(idxs[0], 2);
        assert_eq!(vals[0], 5.0);
        assert_eq!(idxs[1], NO_FRAME);
    }

    /// The seam's cost, made visible. A pixel whose fine argmax disagrees with
    /// the regularised winner is reported, not hidden.
    #[test]
    fn a_scale_disagreement_between_the_two_fields_is_reported() {
        let g = geom(2, 1);
        let mut stats = FocusStats::new(g);
        // Selection scale: pixel 0 peaks at 1, pixel 1 at 3.
        for k in 0..5u16 {
            let reg: Vec<f32> = (0..2)
                .map(|i| {
                    let want = if i == 0 { 1.0f32 } else { 3.0 };
                    -(k as f32 - want).abs()
                })
                .collect();
            stats.fold(k, &reg).unwrap();
        }
        let mut tf = ThroughFocus::new(&stats);
        for k in 0..5u16 {
            // Fine scale agrees at pixel 0 and disagrees at pixel 1.
            let fine: Vec<f32> = (0..2)
                .map(|i| {
                    let want = if i == 0 { 1.0f32 } else { 0.0 };
                    -(k as f32 - want).abs()
                })
                .collect();
            let reg: Vec<f32> = (0..2)
                .map(|i| {
                    let want = if i == 0 { 1.0f32 } else { 3.0 };
                    -(k as f32 - want).abs()
                })
                .collect();
            tf.fold(k, &fine, &reg).unwrap();
        }
        assert!(tf.anchor_is_fine_argmax(0));
        assert!(!tf.anchor_is_fine_argmax(1));
    }

    #[test]
    fn the_stats_radius_is_the_fine_window_radius() {
        assert_eq!(STATS_RADIUS, FINE_WINDOW_RADIUS);
        assert_eq!(STATS_RADIUS, 2);
    }

    // ---- the placebo ----

    /// The placebo must preserve exactly what fact 19's placebo preserved — the
    /// multiset of responses and the winning value — and destroy only adjacency.
    /// A permutation that changed the floor or the top-k would be measuring
    /// something other than ordering.
    #[test]
    fn the_permutation_placebo_preserves_the_response_multiset() {
        let g = geom(8, 6);
        let n = 11u16;
        let curve = |k: u16, i: usize| {
            let peak = (i % 6) as f32 + 2.0;
            let d = k as f32 - peak;
            6.0 - 0.4 * d * d + ((i * 19 + k as usize * 7) % 5) as f32 * 0.02
        };
        let mut stats = FocusStats::new(g);
        for k in 0..n {
            let f: Vec<f32> = (0..g.pixels()).map(|i| curve(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        // A fixed, auditable permutation with no fixed points.
        let perm: Vec<u16> = (0..n).map(|k| (k + 5) % n).collect();

        let real = gather(g, n, &(0..n).collect::<Vec<_>>(), curve);
        let mut fake = ThroughFocus::new_permuted(&stats, &perm);
        for k in 0..n {
            let f: Vec<f32> = (0..g.pixels()).map(|i| curve(k, i)).collect();
            fake.fold(perm[k as usize], &f, &f).unwrap();
        }

        for i in 0..g.pixels() {
            assert_eq!(real.floor[i], fake.floor[i], "floor moved at {i}");
            let mut a = real.top_val[i];
            let mut b = fake.top_val[i];
            a.sort_by(|x, y| x.partial_cmp(y).unwrap());
            b.sort_by(|x, y| x.partial_cmp(y).unwrap());
            assert_eq!(a, b, "top-k values moved at {i}");
            assert_eq!(
                real.triple[i][1], fake.triple[i][1],
                "the winning value moved at {i}"
            );
            assert!(
                (real.posterior_perplexity(i) - fake.posterior_perplexity(i)).abs() < 1e-4,
                "perplexity is not an adjacency statistic and must not move at {i}"
            );
        }
    }

    /// And the sign of the placebo's effect on the bimodality screen, which the
    /// documentation makes a claim about and which is the opposite of the naive
    /// expectation. On an ordered unimodal curve the runner-up is a neighbour and
    /// is excluded; under permutation it is not, so the null reads HIGH.
    #[test]
    fn the_placebo_reads_higher_than_the_real_curve_on_a_unimodal_stack() {
        let g = geom(6, 6);
        let n = 13u16;
        let curve = |k: u16, i: usize| {
            let peak = (i % 7) as f32 + 3.0;
            let d = k as f32 - peak;
            1.0 + 8.0 * (-0.5 * d * d).exp() + ((i * 11 + k as usize * 3) % 4) as f32 * 0.001
        };
        let mut stats = FocusStats::new(g);
        for k in 0..n {
            let f: Vec<f32> = (0..g.pixels()).map(|i| curve(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let perm: Vec<u16> = (0..n).map(|k| (k * 5 + 3) % n).collect();
        let real = gather(g, n, &(0..n).collect::<Vec<_>>(), curve);
        let mut fake = ThroughFocus::new_permuted(&stats, &perm);
        for k in 0..n {
            let f: Vec<f32> = (0..g.pixels()).map(|i| curve(k, i)).collect();
            fake.fold(perm[k as usize], &f, &f).unwrap();
        }
        let mean = |t: &ThroughFocus| {
            let v: Vec<f32> = (0..g.pixels()).filter_map(|i| t.bimodality(i)).collect();
            v.iter().sum::<f32>() / v.len() as f32
        };
        let (r, f) = (mean(&real), mean(&fake));
        assert!(
            f > 1.5 * r,
            "the placebo is supposed to be the MAXIMUM-bimodality reference: \
             real {r:.3}, placebo {f:.3}"
        );
    }

    /// **The test that catches the defect this milestone actually shipped.**
    ///
    /// The first `--stats-placebo` run returned a ratio of exactly 1.0000x,
    /// which reads as "the statistic carries no ordering information" — the very
    /// conclusion the null exists to exclude. The cause was not the statistic;
    /// it was that the permutation was a rotation, and a rotation is an isometry
    /// of the index line, so the "at least PEAK_SEPARATION frames away" screen
    /// saw an identical set. A null has to be tested for actually being a null.
    #[test]
    fn shuffle_destroys_adjacency_which_a_rotation_does_not() {
        for n in [7usize, 11, 22, 33, 105] {
            let p = shuffled_indices(n, 0x4D31_385Eu64);
            // It is a permutation at all.
            let mut seen = vec![false; n];
            for v in &p {
                assert!(!seen[*v as usize], "n={n}: {v} appeared twice");
                seen[*v as usize] = true;
            }
            assert!(seen.iter().all(|s| *s), "n={n}: not surjective");
            // It is deterministic.
            assert_eq!(p, shuffled_indices(n, 0x4D31_385Eu64));

            // And the property that matters. Mean step between the images of
            // adjacent frames: 1 for a rotation, ~n/3 for a shuffle.
            let step = |q: &[u16]| {
                (0..n - 1)
                    .map(|k| q[k].abs_diff(q[k + 1]) as f64)
                    .sum::<f64>()
                    / (n - 1) as f64
            };
            let rotation: Vec<u16> = (0..n as u16)
                .map(|k| (k + n as u16 / 3) % n as u16)
                .collect();
            assert!(
                step(&rotation) < 2.0,
                "n={n}: the rotation control is supposed to preserve adjacency, read {:.3}",
                step(&rotation)
            );
            if n >= 11 {
                assert!(
                    step(&p) > 0.15 * n as f64,
                    "n={n}: shuffle left adjacency largely intact, mean step {:.3}",
                    step(&p)
                );
            }
        }
    }

    /// The screening form of the scale disagreement has to be strictly weaker
    /// than the diagnostic form, or it is not screening anything. Off-by-one is
    /// harmless because the parabola still brackets the fine peak; off-by-two is
    /// not, because no refinement of the retained triple can reach it.
    #[test]
    fn the_scale_disagreement_screen_ignores_off_by_one_and_catches_off_by_two() {
        let g = geom(4, 1);
        let n = 9u16;
        // Pixel 0: fine peak == anchor. 1: off by one. 2: off by two. 3: far.
        let offsets = [0i32, 1, 2, 5];
        let mut stats = FocusStats::new(g);
        let sel = |k: u16, i: usize| {
            let d = k as f32 - 4.0;
            10.0 - d * d + i as f32 * 1e-3
        };
        for k in 0..n {
            let f: Vec<f32> = (0..g.pixels()).map(|i| sel(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let mut tf = ThroughFocus::new(&stats);
        for k in 0..n {
            let coarse: Vec<f32> = (0..g.pixels()).map(|i| sel(k, i)).collect();
            let fine: Vec<f32> = (0..g.pixels())
                .map(|i| {
                    let d = k as i32 - (4 + offsets[i]);
                    10.0 - (d * d) as f32
                })
                .collect();
            tf.fold(k, &fine, &coarse).unwrap();
        }
        assert_eq!(tf.anchor[0], 4, "the selection winner should be frame 4");
        assert!(tf.anchor_is_fine_argmax(0));
        assert!(!tf.fine_peak_outside_triple(0));
        for i in 1..4 {
            assert!(!tf.anchor_is_fine_argmax(i), "pixel {i} should disagree");
        }
        assert!(
            !tf.fine_peak_outside_triple(1),
            "off-by-one is inside the triple and must not be flagged"
        );
        assert!(tf.fine_peak_outside_triple(2), "off-by-two must be flagged");
        assert!(
            tf.fine_peak_outside_triple(3),
            "off-by-five must be flagged"
        );
    }

    // ---- the confidence vector ----

    /// The vector must not be collapsible, and the test that says so is that the
    /// channels select different pixels. If the union equalled any single
    /// channel's tail, carrying four would be pointless and M34's 14.278% would
    /// be a rounding error rather than a finding.
    #[test]
    fn the_confidence_channels_disagree_about_which_pixels_are_bad() {
        let g = geom(20, 20);
        let n = 11u16;
        let noise = unit_sigma_model();
        let mut rng = Rng::new(0xC1DE);
        // Peaks scattered across the stack, widths varying, so C2 and C4 pick
        // out different pixels from each other.
        let peaks: Vec<f32> = (0..g.pixels())
            .map(|i| (i % 11) as f32 + 0.37 * ((i % 3) as f32))
            .collect();
        let widths: Vec<f32> = (0..g.pixels())
            .map(|i| 0.4 + 1.6 * ((i / 20) % 5) as f32)
            .collect();
        let curve = |k: u16, i: usize| {
            let d = (k as f32 - peaks[i]) / widths[i];
            20.0 * FOCUS_NOISE_SD * (-0.5 * d * d).exp()
        };
        let tf = gather(g, n, &(0..n).collect::<Vec<_>>(), curve);

        let vectors: Vec<ConfidenceVector> = (0..g.pixels())
            .map(|i| {
                let admitted = 1 + (rng.next_u64() % 5) as u16;
                tf.confidence(admitted, 3000.0, &noise, i, 1e9)
            })
            .collect();
        let (mask, b) = do_not_trust_mask(&vectors, 0.05);

        assert_eq!(b.total, g.pixels());
        assert_eq!(mask.iter().filter(|m| **m).count(), b.union);
        assert!(
            b.union > b.by_sigma.max(b.by_perplexity).max(b.by_deficit),
            "the union should be strictly larger than any one channel: {b:?}"
        );
        assert!(b.by_flags > 0, "the boundary flag should fire somewhere");
        assert!(
            b.union < b.total,
            "a mask that condemns everything is not a mask"
        );
    }

    /// C1 is the channel most likely to be misread as "the" confidence, so its
    /// contract is pinned: it falls as `1/sqrt(n)`, and `n = 1` carries
    /// whatever selection penalty has been measured — **currently none**.
    ///
    /// This test used to assert `one > model`, pricing selection at M40-refuted
    /// 1.074x. That constant is gone (see [`crate::merge::SELECTION_INFLATION`])
    /// and with it the guarantee. **Fact 341 is open again and this test now
    /// pins the gap rather than papering over it**: at `n = 1` the model reports
    /// exactly the single-frame sigma, which is known to be optimistic because
    /// the argmax prefers frames whose noise pointed upward.
    ///
    /// The `n = 4` arm is unaffected and is the real regression guard here —
    /// `1/sqrt(n)` never depended on the penalty.
    #[test]
    fn predicted_sigma_is_the_calibrated_model_with_no_selection_penalty_yet() {
        let noise = unit_sigma_model();
        let tf = gather(geom(1, 1), 5, &(0..5).collect::<Vec<_>>(), |k, _| {
            -(k as f32 - 2.0).abs()
        });
        let one = tf.confidence(1, 3000.0, &noise, 0, 1e9).predicted_sigma;
        let four = tf.confidence(4, 3000.0, &noise, 0, 1e9).predicted_sigma;
        let model = noise.green_luma_sigma(3000.0);
        assert!(
            (one - model * crate::merge::SELECTION_INFLATION).abs() < 1e-6,
            "n = 1 must track SELECTION_INFLATION exactly: expected {} got {one}",
            model * crate::merge::SELECTION_INFLATION
        );
        assert!(
            (one - model).abs() < 1e-6,
            "KNOWN GAP, not a passing property: with no measured penalty, n = 1 \
             reports the bare single-frame sigma ({one} vs {model}). This is \
             fact 341. When a penalty is measured this assertion is the one to \
             delete, and the `one > model` guarantee returns with it"
        );
        assert!(
            (four - model / 2.0).abs() < 1e-6,
            "n = 4 must halve it with no penalty, got {four}"
        );
    }

    /// The bimodality flag has to actually depend on the cut, or the cut is
    /// decorative and the flag is a constant.
    #[test]
    fn the_bimodality_flag_follows_its_cut() {
        let n = 15u16;
        let tf = gather(geom(1, 1), n, &(0..n).collect::<Vec<_>>(), |k, _| {
            let bump = |at: f32, amp: f32| {
                let d = k as f32 - at;
                amp * (-0.5 * d * d).exp()
            };
            1.0 + bump(4.0, 6.0) + bump(11.0, 4.0)
        });
        let noise = unit_sigma_model();
        let b = tf.bimodality_sigma(0).unwrap();
        assert!(
            tf.confidence(1, 3000.0, &noise, 0, b * 0.5)
                .has(FLAG_BIMODAL)
        );
        assert!(
            !tf.confidence(1, 3000.0, &noise, 0, b * 2.0)
                .has(FLAG_BIMODAL)
        );
    }
}
