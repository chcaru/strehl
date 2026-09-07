//! Robust focus election: an argmax that can decline to elect a frame which
//! disagrees with its temporal neighbours.
//!
//! # Why this exists
//!
//! `merge.rs` pass one elects, per pixel, the frame with the highest regularised
//! focus response. A frame that has *moved* between exposures presents a
//! displaced edge, and a displaced edge is **sharper** than the correctly-focused
//! but stationary alternative. So motion does not merely survive the election —
//! it wins it. M89 measured **4.78% of `foam`'s output pixels** taking their
//! value from a frame more than 8 sigma discrepant at that pixel, and measured
//! that down-weighting those samples in the *average* recovers only 6.0% of the
//! available benefit because the frame has already won. See
//! `docs/research/SYNTHESIS.md` fact 1189.
//!
//! # What it must not do
//!
//! This pipeline exists to elect the sharpest frame. A frame can disagree with
//! its neighbours because it moved **or because it is the only frame that
//! resolves that pixel**. A gate that cannot tell those apart destroys the
//! product. [`Arm::Soft`] exists precisely for that: it *demotes* by the weight
//! rather than excluding, so a frame that is far sharper than any alternative
//! survives a partial penalty while a frame that wins by a hair does not.
//!
//! # Architectural contract
//!
//! [`RobustElection`] is a **commutative, associative, O(1)-per-pixel fold**,
//! exactly like `merge::FocusStats`. The frame list may be partitioned across
//! workers arbitrarily and reduced with [`RobustElection::absorb`] for
//! bit-identical output. This is not incidental: holding the full through-focus
//! curve per pixel would cost ~9.8 GB on a 299-frame stack at this sensor's
//! geometry, and would break worker partitioning.
//!
//! This module deliberately has **no dependencies on the rest of the crate**.
//! It consumes plain slices and scalars so that it is testable in isolation and
//! so that the noise model reaches it as data rather than as a linkage.

/// Sentinel for "no frame has been elected at this pixel yet".
///
/// Matches `merge::NO_FRAME`, which is private to that module.
pub const NO_FRAME: u16 = u16::MAX;

/// Below this normalised disagreement a sample is untouched.
///
/// **Units are sigmas of the calibrated noise model, never DN.** This is M89's
/// weight and carries no constant of its own — see fact 1186.
pub const Z_KNEE_LO: f32 = 4.0;

/// At and above this normalised disagreement a sample is rejected outright.
pub const Z_KNEE_HI: f32 = 8.0;

/// Minimum weight for [`Arm::Hard`] eligibility.
///
/// Derived, not chosen: `w = 0.5` on the ramp corresponds to
/// `|z| = 8 - 4*sqrt(0.5) = 5.172`.
pub const HARD_ELIGIBLE: f32 = 0.5;

/// The robustness weight, in sigmas of the calibrated noise model.
///
/// Continuous everywhere, and `C^1` at the upper knee because the ramp is
/// squared — a binary mask produces spatial discontinuities that show up as
/// blotches.
#[inline]
pub fn weight(z: f32) -> f32 {
    let a = z.abs();
    if a <= Z_KNEE_LO {
        1.0
    } else if a >= Z_KNEE_HI {
        0.0
    } else {
        let t = (Z_KNEE_HI - a) / (Z_KNEE_HI - Z_KNEE_LO);
        t * t
    }
}

/// How the disagreement weight is allowed to affect the election.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Arm {
    /// No gating. Reproduces `merge::FocusStats` exactly and exists so that the
    /// difference made by the other two arms can be measured against the
    /// shipped behaviour rather than against a re-implementation.
    Ungated,
    /// Exclude any frame whose weight is below [`HARD_ELIGIBLE`], then take the
    /// plain argmax of the response over what remains.
    ///
    /// Discards a frame that is 10x sharper than any alternative on the same
    /// evidence that discards one that is 1.01x sharper.
    Hard,
    /// Elect `argmax(weight * response)`.
    ///
    /// Scale-free, because the regularised response is a gradient magnitude and
    /// therefore non-negative. A frame far sharper than its alternatives
    /// survives a partial penalty.
    Soft,
}

impl Arm {
    /// Whether a sample may be considered at all.
    #[inline]
    fn eligible(self, w: f32) -> bool {
        match self {
            Arm::Ungated => true,
            Arm::Hard => w >= HARD_ELIGIBLE,
            Arm::Soft => w > 0.0,
        }
    }

    /// The value the argmax is taken over.
    #[inline]
    fn score(self, response: f32, w: f32) -> f32 {
        match self {
            Arm::Ungated | Arm::Hard => response,
            Arm::Soft => w * response,
        }
    }
}

/// Pass one, with an election that can decline a contaminated frame.
///
/// Carries the ungated winner alongside the gated one so that a pixel at which
/// every frame is ineligible falls back to the shipped behaviour instead of
/// emitting a hole.
#[derive(Debug, Clone)]
pub struct RobustElection {
    arm: Arm,
    pixels: usize,
    /// Best gated score, and the frame that produced it.
    best: Vec<f32>,
    idx: Vec<u16>,
    /// The **raw** response at the elected frame. For [`Arm::Soft`] the score is
    /// `weight * response`, so the score is not the response, and pass two's
    /// admission band `best - focus <= tolerance` must be centred on the
    /// response or the band width silently changes with the weight.
    best_resp: Vec<f32>,
    /// Best ungated response, and the frame that produced it. The fallback.
    fb_best: Vec<f32>,
    fb_idx: Vec<u16>,
    frames: u32,
    max_index: u16,
}

impl RobustElection {
    pub fn new(pixels: usize, arm: Arm) -> Self {
        Self {
            arm,
            pixels,
            best: vec![f32::NEG_INFINITY; pixels],
            idx: vec![NO_FRAME; pixels],
            best_resp: vec![f32::NEG_INFINITY; pixels],
            fb_best: vec![f32::NEG_INFINITY; pixels],
            fb_idx: vec![NO_FRAME; pixels],
            frames: 0,
            max_index: 0,
        }
    }

    pub fn arm(&self) -> Arm {
        self.arm
    }
    pub fn pixels(&self) -> usize {
        self.pixels
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    pub fn max_index(&self) -> u16 {
        self.max_index
    }

    /// Ties go to the lower frame index, stated rather than left to visitation
    /// order, so the fold is order-independent.
    ///
    /// Identical to `merge::FocusStats::beats`; the two must not drift apart or
    /// [`Arm::Ungated`] stops reproducing the shipped election.
    #[inline]
    fn beats(score: f32, index: u16, cur: f32, cur_index: u16) -> bool {
        score > cur || (score == cur && index < cur_index)
    }

    /// Fold one frame's regularised focus field and its normalised
    /// disagreement field.
    ///
    /// `z` is the leave-one-out fourth-difference residual in sigmas of the
    /// calibrated noise model (fact 1186). Pass a `z` of `0.0` for frames where
    /// it is undefined — the first and last `(w-1)/2` of a stack have no centred
    /// temporal window — which leaves them ungated rather than silently
    /// rejecting them.
    pub fn fold(&mut self, frame_index: u16, response: &[f32], z: &[f32]) -> Result<(), String> {
        if response.len() != self.pixels || z.len() != self.pixels {
            return Err(format!(
                "frame {frame_index}: response {} and z {} must both be {} long",
                response.len(),
                z.len(),
                self.pixels
            ));
        }
        if frame_index == NO_FRAME {
            return Err(format!("frame index {NO_FRAME} is reserved"));
        }
        for i in 0..self.pixels {
            let r = response[i];
            if Self::beats(r, frame_index, self.fb_best[i], self.fb_idx[i]) {
                self.fb_best[i] = r;
                self.fb_idx[i] = frame_index;
            }
            let w = weight(z[i]);
            if !self.arm.eligible(w) {
                continue;
            }
            let s = self.arm.score(r, w);
            if Self::beats(s, frame_index, self.best[i], self.idx[i]) {
                self.best[i] = s;
                self.best_resp[i] = r;
                self.idx[i] = frame_index;
            }
        }
        self.frames += 1;
        self.max_index = self.max_index.max(frame_index);
        Ok(())
    }

    /// Reduce another worker's partial state into this one.
    pub fn absorb(&mut self, other: &RobustElection) -> Result<(), String> {
        if other.pixels != self.pixels {
            return Err(format!(
                "cannot absorb {} pixels into {}",
                other.pixels, self.pixels
            ));
        }
        if other.arm != self.arm {
            return Err("cannot absorb a different arm".to_string());
        }
        for i in 0..self.pixels {
            if Self::beats(other.best[i], other.idx[i], self.best[i], self.idx[i]) {
                self.best[i] = other.best[i];
                self.best_resp[i] = other.best_resp[i];
                self.idx[i] = other.idx[i];
            }
            if Self::beats(
                other.fb_best[i],
                other.fb_idx[i],
                self.fb_best[i],
                self.fb_idx[i],
            ) {
                self.fb_best[i] = other.fb_best[i];
                self.fb_idx[i] = other.fb_idx[i];
            }
        }
        self.frames += other.frames;
        self.max_index = self.max_index.max(other.max_index);
        Ok(())
    }

    /// The elected frame per pixel, with the ungated fallback already applied.
    ///
    /// Never returns [`NO_FRAME`] for a pixel at which at least one frame was
    /// folded.
    pub fn winners(&self) -> Vec<u16> {
        (0..self.pixels)
            .map(|i| {
                if self.idx[i] == NO_FRAME {
                    self.fb_idx[i]
                } else {
                    self.idx[i]
                }
            })
            .collect()
    }

    /// The raw focus response at the elected frame, with the ungated fallback
    /// already applied.
    ///
    /// This is the centre of pass two's admission band, and the quantity to
    /// compare against [`RobustElection::ungated_best`] to measure what the gate
    /// costs in sharpness.
    pub fn winner_response(&self) -> Vec<f32> {
        (0..self.pixels)
            .map(|i| {
                if self.idx[i] == NO_FRAME {
                    self.fb_best[i]
                } else {
                    self.best_resp[i]
                }
            })
            .collect()
    }

    /// The election the shipped code would have made, from the same fold.
    pub fn ungated_winners(&self) -> &[u16] {
        &self.fb_idx
    }

    /// Best ungated response per pixel, for measuring what the gate costs in
    /// sharpness.
    pub fn ungated_best(&self) -> &[f32] {
        &self.fb_best
    }

    /// Number of pixels at which every frame was ineligible and the fallback
    /// fired. A large number means the gate is rejecting wholesale and its
    /// output is mostly the ungated election anyway.
    pub fn fallbacks(&self) -> usize {
        (0..self.pixels)
            .filter(|&i| self.idx[i] == NO_FRAME)
            .count()
    }
}

// ---------------------------------------------------------------------------
// The disagreement statistic, `z`
// ---------------------------------------------------------------------------
//
// `RobustElection::fold` consumes a `z` field but has never had a producer in
// the library: `loo_residual_kernel` existed only as two copies inside
// `crates/strehl-cli/examples/`, which is why this module has been dead code
// since it was written. What follows is that producer, ported so the election
// can be reached from the product.
//
// It keeps this module's contract: plain slices and scalars, no dependency on
// the rest of the crate. The noise model arrives as the two coefficients of
// `var(L) = a*L + b` rather than as a linkage.

/// Temporal window for the disagreement statistic. Odd, so it has a centre.
pub const Z_WINDOW: usize = 5;

/// Polynomial order fitted to the window's *other* members.
pub const Z_ORDER: usize = 2;

/// Frames at each end of a stack that have no centred window.
pub const Z_HALF: usize = (Z_WINDOW - 1) / 2;

/// Leave-one-out residual kernel: fit a degree-`p` polynomial to the `w - 1`
/// neighbours of the centre, predict the centre, and return the kernel whose
/// dot product with the window is `centre - prediction`.
///
/// The centre carries `+1` and the neighbours carry `-k_j` with `sum(k) = 1`,
/// so the kernel annihilates any polynomial of degree `<= p`. A frame that
/// merely sits on a smooth through-focus trend therefore scores zero however
/// bright, sharp or steep that trend is, and only a frame that departs from its
/// own neighbours scores at all.
///
/// Ported unchanged from `examples/m93-election.rs`, which took it from M89.
/// The two copies there are left in place deliberately: they are committed
/// instruments behind published numbers and must not start tracking this one.
pub fn loo_residual_kernel(w: usize, p: usize) -> Vec<f64> {
    assert!(w >= 3 && w % 2 == 1, "window must be odd and at least 3");
    let h = (w - 1) / 2;
    assert!(p < w - 1, "order {p} needs {} neighbours", p + 1);
    let xs: Vec<f64> = (0..w)
        .filter(|&j| j != h)
        .map(|j| j as f64 - h as f64)
        .collect();
    let m = p + 1;
    let mut a = vec![vec![0.0f64; m + 1]; m];
    for (row, ar) in a.iter_mut().enumerate() {
        for (col, cell) in ar.iter_mut().enumerate().take(m) {
            *cell = xs.iter().map(|x| x.powi((row + col) as i32)).sum();
        }
        ar[m] = f64::from(u8::from(row == 0));
    }
    for col in 0..m {
        let piv = (col..m)
            .max_by(|&i, &j| {
                a[i][col]
                    .abs()
                    .partial_cmp(&a[j][col].abs())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .expect("non-empty");
        a.swap(col, piv);
        let d = a[col][col];
        assert!(d.abs() > 1e-12, "singular design");
        for v in a[col].iter_mut() {
            *v /= d;
        }
        let pivot = a[col].clone();
        for (row, arow) in a.iter_mut().enumerate() {
            if row != col {
                let f = arow[col];
                if f != 0.0 {
                    for (t, p) in arow.iter_mut().zip(&pivot).skip(col) {
                        *t -= f * p;
                    }
                }
            }
        }
    }
    let v: Vec<f64> = (0..m).map(|i| a[i][m]).collect();
    let mut r = vec![0.0f64; w];
    let mut ksum = 0.0f64;
    let mut n = 0usize;
    for (j, rj) in r.iter_mut().enumerate() {
        if j == h {
            *rj = 1.0;
            continue;
        }
        let x = xs[n];
        n += 1;
        let kj: f64 = (0..m).map(|q| v[q] * x.powi(q as i32)).sum();
        ksum += kj;
        *rj = -kj;
    }
    assert!((ksum - 1.0).abs() < 1e-9, "LOO weights sum to {ksum}, not 1");
    r
}

/// The residual operator and its squares, built once per merge.
#[derive(Debug, Clone)]
pub struct ResidualOp {
    r: Vec<f32>,
    r2: Vec<f32>,
}

impl Default for ResidualOp {
    fn default() -> Self {
        Self::new(Z_WINDOW, Z_ORDER)
    }
}

impl ResidualOp {
    pub fn new(w: usize, p: usize) -> Self {
        let r: Vec<f32> = loo_residual_kernel(w, p)
            .iter()
            .map(|&v| v as f32)
            .collect();
        let r2 = r.iter().map(|v| v * v).collect();
        Self { r, r2 }
    }

    pub fn window(&self) -> usize {
        self.r.len()
    }

    /// `z` for one pixel from `window()` luma samples in temporal order.
    ///
    /// The numerator is the leave-one-out residual; the denominator is the
    /// standard deviation the calibrated model predicts for exactly that linear
    /// combination, `sqrt(sum(r_j^2 * (a*L_j + b)))`. The result is therefore in
    /// sigmas and carries no constant of its own — an absolute DN bar here is
    /// what fact 1470 charges with the waxy-blob artefact.
    ///
    /// Returns `0.0` when the predicted variance is not positive, which leaves
    /// the sample ungated rather than rejecting it on a degenerate denominator.
    #[inline]
    pub fn z(&self, luma: &[f32], a: f32, b: f32) -> f32 {
        debug_assert_eq!(luma.len(), self.r.len());
        let mut num = 0.0f32;
        let mut var = 0.0f32;
        for ((&r, &r2), &l) in self.r.iter().zip(self.r2.iter()).zip(luma.iter()) {
            num += r * l;
            var += r2 * (a * l + b);
        }
        if var > 0.0 { num / var.sqrt() } else { 0.0 }
    }

    /// Fill `out` with `z` for every pixel, from `window()` whole luma planes
    /// given in temporal order.
    pub fn z_field(&self, planes: &[&[f32]], a: f32, b: f32, out: &mut [f32]) {
        assert_eq!(planes.len(), self.r.len(), "wrong window depth");
        let mut buf = vec![0.0f32; self.r.len()];
        for (i, o) in out.iter_mut().enumerate() {
            for (j, p) in planes.iter().enumerate() {
                buf[j] = p[i];
            }
            *o = self.z(&buf, a, b);
        }
    }
}

/// The two coefficients of `var(L) = a*L + b`, extracted from a calibrated
/// noise model by the caller.
///
/// Kept as scalars rather than a `NoiseModel` so this module stays free of
/// crate linkage, per its header.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AffineVar {
    pub a: f32,
    pub b: f32,
}

#[cfg(test)]
mod tests {
    use super::*;

    // ---- the disagreement statistic ------------------------------------

    /// The kernel for the shipped window, worked out by hand from the normal
    /// equations rather than read back out of the code: fitting a quadratic to
    /// x = -2,-1,1,2 and predicting x = 0 gives neighbour weights
    /// k = [-1/6, 2/3, 2/3, -1/6], and the residual kernel is `+1` at the
    /// centre against `-k`.
    #[test]
    fn the_residual_kernel_is_the_hand_computed_one() {
        let r = loo_residual_kernel(Z_WINDOW, Z_ORDER);
        let want = [1.0 / 6.0, -2.0 / 3.0, 1.0, -2.0 / 3.0, 1.0 / 6.0];
        assert_eq!(r.len(), want.len());
        for (got, w) in r.iter().zip(&want) {
            assert!((got - w).abs() < 1e-12, "kernel {r:?} != {want:?}");
        }
    }

    /// **The trap, at the level of the statistic.** The kernel annihilates any
    /// polynomial of degree <= Z_ORDER, so a frame sitting on a smooth
    /// through-focus trend scores exactly zero however steep that trend is.
    /// Without this the gate would fire hardest exactly where focus is changing
    /// fastest, which is the whole useful part of a stack.
    #[test]
    fn the_kernel_annihilates_any_trend_it_is_allowed_to_fit() {
        let r = loo_residual_kernel(Z_WINDOW, Z_ORDER);
        let h = (Z_WINDOW - 1) as f64 / 2.0;
        for deg in 0..=Z_ORDER {
            for scale in [1.0f64, 1e4] {
                let acc: f64 = r
                    .iter()
                    .enumerate()
                    .map(|(j, rj)| rj * scale * (j as f64 - h).powi(deg as i32))
                    .sum();
                assert!(
                    acc.abs() < 1e-9 * scale,
                    "degree {deg} at scale {scale} left residual {acc}"
                );
            }
        }
    }

    /// A frame that departs from its own neighbours scores, and the score is in
    /// sigmas: doubling the noise halves `z` for the same departure.
    #[test]
    fn z_is_a_departure_measured_in_sigmas() {
        let op = ResidualOp::default();
        let flat = [100.0f32; Z_WINDOW];
        assert!(op.z(&flat, 0.0, 1.0).abs() < 1e-5, "a flat window must read 0");

        // Unit variance: b = 1, a = 0. sum(r^2) = 1/36 + 4/9 + 1 + 4/9 + 1/36.
        let r2: f32 = loo_residual_kernel(Z_WINDOW, Z_ORDER)
            .iter()
            .map(|v| (v * v) as f32)
            .sum();
        let mut bumped = flat;
        bumped[Z_HALF] += 10.0;
        let z = op.z(&bumped, 0.0, 1.0);
        assert!(
            (z - 10.0 / r2.sqrt()).abs() < 1e-3,
            "z {z} should be 10/sqrt(sum r^2) = {}",
            10.0 / r2.sqrt()
        );

        // Four times the variance is twice the sigma, so half the z.
        let z4 = op.z(&bumped, 0.0, 4.0);
        assert!((z4 - 0.5 * z).abs() < 1e-3, "z {z} -> {z4} is not sigma-scaled");
    }

    /// A degenerate denominator leaves the sample ungated rather than rejecting
    /// it: `weight(0) == 1`.
    #[test]
    fn a_non_positive_variance_reads_zero_and_so_gates_nothing() {
        let op = ResidualOp::default();
        let mut w = [0.0f32; Z_WINDOW];
        w[Z_HALF] = 500.0;
        assert_eq!(op.z(&w, 0.0, 0.0), 0.0);
        assert_eq!(weight(op.z(&w, 0.0, 0.0)), 1.0);
    }

    #[test]
    fn z_field_agrees_with_z_pixel_by_pixel() {
        let op = ResidualOp::default();
        let planes: Vec<Vec<f32>> = (0..Z_WINDOW)
            .map(|j| (0..7).map(|i| 100.0 + (i * j) as f32 * 3.0).collect())
            .collect();
        let refs: Vec<&[f32]> = planes.iter().map(|p| p.as_slice()).collect();
        let mut out = vec![0.0f32; 7];
        op.z_field(&refs, 0.5, 4.0, &mut out);
        for i in 0..7 {
            let col: Vec<f32> = planes.iter().map(|p| p[i]).collect();
            assert_eq!(out[i], op.z(&col, 0.5, 4.0));
        }
    }

    // ---- the election ---------------------------------------------------

    /// Build a tiny synthetic problem: `pixels` pixels, `frames` frames.
    fn run(arm: Arm, pixels: usize, r: &[Vec<f32>], z: &[Vec<f32>]) -> Vec<u16> {
        let mut e = RobustElection::new(pixels, arm);
        for (f, (rf, zf)) in r.iter().zip(z).enumerate() {
            e.fold(f as u16, rf, zf).unwrap();
        }
        e.winners()
    }

    #[test]
    fn weight_is_one_below_the_lower_knee_and_zero_above_the_upper() {
        assert_eq!(weight(0.0), 1.0);
        assert_eq!(weight(3.9), 1.0);
        assert_eq!(weight(4.0), 1.0);
        assert_eq!(weight(-4.0), 1.0);
        assert_eq!(weight(8.0), 0.0);
        assert_eq!(weight(-8.0), 0.0);
        assert_eq!(weight(1e9), 0.0);
        // and it is continuous and monotone in between
        assert_eq!(weight(6.0), 0.25);
        let mut prev = 1.0;
        for i in 0..=100 {
            let z = 4.0 + 4.0 * (i as f32) / 100.0;
            let w = weight(z);
            assert!(w <= prev + 1e-6, "weight rose at z={z}");
            assert!((0.0..=1.0).contains(&w));
            prev = w;
        }
    }

    #[test]
    fn hard_eligibility_threshold_is_where_the_ramp_crosses_one_half() {
        // Derived, not chosen: 8 - 4*sqrt(0.5).
        let crossing = 8.0 - 4.0 * 0.5f32.sqrt();
        assert!((weight(crossing) - 0.5).abs() < 1e-6);
        assert!(Arm::Hard.eligible(weight(crossing - 0.01)));
        assert!(!Arm::Hard.eligible(weight(crossing + 0.01)));
    }

    #[test]
    fn ungated_arm_is_a_plain_argmax() {
        // Frame 1 is sharpest; z is huge everywhere, and must be ignored.
        let r = vec![vec![1.0, 5.0], vec![9.0, 2.0], vec![3.0, 7.0]];
        let z = vec![vec![99.0, 99.0], vec![99.0, 99.0], vec![99.0, 99.0]];
        assert_eq!(run(Arm::Ungated, 2, &r, &z), vec![1, 2]);
    }

    #[test]
    fn ties_go_to_the_lower_frame_index() {
        let r = vec![vec![5.0], vec![5.0], vec![5.0]];
        let z = vec![vec![0.0], vec![0.0], vec![0.0]];
        assert_eq!(run(Arm::Ungated, 1, &r, &z), vec![0]);
        assert_eq!(run(Arm::Hard, 1, &r, &z), vec![0]);
        assert_eq!(run(Arm::Soft, 1, &r, &z), vec![0]);
    }

    #[test]
    fn the_gate_rejects_a_contaminated_winner_and_elects_the_runner_up() {
        // Frame 1 is sharpest but is 20 sigma discrepant: a moved edge.
        let r = vec![vec![4.0], vec![9.0], vec![7.0]];
        let z = vec![vec![0.0], vec![20.0], vec![0.0]];
        assert_eq!(
            run(Arm::Ungated, 1, &r, &z),
            vec![1],
            "shipped elects motion"
        );
        assert_eq!(run(Arm::Hard, 1, &r, &z), vec![2]);
        assert_eq!(run(Arm::Soft, 1, &r, &z), vec![2]);
    }

    /// **The guard, as a unit test.** A frame that is overwhelmingly sharper
    /// than any alternative is the frame that uniquely resolves the pixel. Soft
    /// must keep it under a partial penalty; Hard cannot tell it apart from a
    /// moved frame.
    #[test]
    fn soft_keeps_a_far_sharper_frame_under_a_partial_penalty_and_hard_does_not() {
        // z = 6 gives w = 0.25, which is below HARD_ELIGIBLE.
        let r = vec![vec![1.0], vec![100.0], vec![1.0]];
        let z = vec![vec![0.0], vec![6.0], vec![0.0]];
        assert_eq!(weight(6.0), 0.25);
        // Soft: 0.25 * 100 = 25, still far above 1.0.
        assert_eq!(run(Arm::Soft, 1, &r, &z), vec![1], "soft must keep it");
        // Hard: excluded outright, elects a frame 100x less sharp.
        assert_eq!(run(Arm::Hard, 1, &r, &z), vec![0], "hard discards it");
    }

    #[test]
    fn soft_still_demotes_a_frame_that_wins_by_a_hair() {
        // Same penalty, but frame 1 is only marginally sharper.
        let r = vec![vec![1.0], vec![1.05], vec![1.0]];
        let z = vec![vec![0.0], vec![6.0], vec![0.0]];
        assert_eq!(run(Arm::Soft, 1, &r, &z), vec![0]);
    }

    #[test]
    fn every_frame_ineligible_falls_back_to_the_ungated_winner() {
        let r = [vec![4.0], vec![9.0], vec![7.0]];
        let z = vec![vec![99.0], vec![99.0], vec![99.0]];
        let mut e = RobustElection::new(1, Arm::Hard);
        for (f, (rf, zf)) in r.iter().zip(&z).enumerate() {
            e.fold(f as u16, rf, zf).unwrap();
        }
        assert_eq!(e.fallbacks(), 1);
        assert_eq!(e.winners(), vec![1], "fallback is the ungated winner");
        assert_eq!(e.ungated_winners(), &[1]);
        // and never a hole
        assert!(!e.winners().contains(&NO_FRAME));
    }

    #[test]
    fn the_fold_is_order_independent() {
        let r = vec![
            vec![1.0, 5.0, 2.0],
            vec![9.0, 2.0, 8.0],
            vec![3.0, 7.0, 8.0],
            vec![6.0, 1.0, 4.0],
        ];
        let z = vec![
            vec![0.0, 9.0, 0.0],
            vec![20.0, 0.0, 0.0],
            vec![0.0, 0.0, 5.0],
            vec![0.0, 0.0, 0.0],
        ];
        for arm in [Arm::Ungated, Arm::Hard, Arm::Soft] {
            let forward = run(arm, 3, &r, &z);
            let mut e = RobustElection::new(3, arm);
            for f in (0..r.len()).rev() {
                e.fold(f as u16, &r[f], &z[f]).unwrap();
            }
            assert_eq!(forward, e.winners(), "{arm:?} depends on visitation order");
        }
    }

    #[test]
    fn winner_response_is_the_raw_response_not_the_soft_score() {
        // Frame 1 wins under Soft with score 0.25 * 100 = 25, but the admission
        // band in pass two must be centred on 100, not 25, or the band width
        // changes with the weight.
        let r = [vec![1.0], vec![100.0], vec![1.0]];
        let z = vec![vec![0.0], vec![6.0], vec![0.0]];
        let mut e = RobustElection::new(1, Arm::Soft);
        for (f, (rf, zf)) in r.iter().zip(&z).enumerate() {
            e.fold(f as u16, rf, zf).unwrap();
        }
        assert_eq!(e.winners(), vec![1]);
        assert_eq!(e.winner_response(), vec![100.0], "must be R, not w*R");
        assert_eq!(e.ungated_best(), &[100.0]);
    }

    #[test]
    fn winner_response_falls_back_with_the_winner() {
        let r = [vec![4.0], vec![9.0], vec![7.0]];
        let z = vec![vec![99.0], vec![99.0], vec![99.0]];
        let mut e = RobustElection::new(1, Arm::Hard);
        for (f, (rf, zf)) in r.iter().zip(&z).enumerate() {
            e.fold(f as u16, rf, zf).unwrap();
        }
        assert_eq!(e.winners(), vec![1]);
        assert_eq!(e.winner_response(), vec![9.0]);
    }

    #[test]
    fn the_fold_is_associative_under_absorb_at_every_cut() {
        let r = vec![
            vec![1.0, 5.0, 2.0],
            vec![9.0, 2.0, 8.0],
            vec![3.0, 7.0, 8.0],
            vec![6.0, 1.0, 4.0],
            vec![2.0, 9.0, 3.0],
        ];
        let z = vec![
            vec![0.0, 9.0, 0.0],
            vec![20.0, 0.0, 0.0],
            vec![0.0, 0.0, 5.0],
            vec![0.0, 0.0, 0.0],
            vec![0.0, 6.0, 0.0],
        ];
        for arm in [Arm::Ungated, Arm::Hard, Arm::Soft] {
            let whole = run(arm, 3, &r, &z);
            let whole_resp = {
                let mut e = RobustElection::new(3, arm);
                for f in 0..r.len() {
                    e.fold(f as u16, &r[f], &z[f]).unwrap();
                }
                e.winner_response()
            };
            for cut in 1..r.len() {
                let mut a = RobustElection::new(3, arm);
                let mut b = RobustElection::new(3, arm);
                for f in 0..cut {
                    a.fold(f as u16, &r[f], &z[f]).unwrap();
                }
                for f in cut..r.len() {
                    b.fold(f as u16, &r[f], &z[f]).unwrap();
                }
                a.absorb(&b).unwrap();
                assert_eq!(whole, a.winners(), "{arm:?} cut {cut}");
                assert_eq!(
                    whole_resp,
                    a.winner_response(),
                    "{arm:?} cut {cut}: best_resp did not survive absorb"
                );
                assert_eq!(a.frames_folded(), r.len() as u32);
            }
        }
    }

    #[test]
    fn undefined_z_leaves_a_frame_ungated_rather_than_rejected() {
        // The window edges have no centred temporal window. A z of 0 must not
        // reject them, or the first and last frames of every stack vanish.
        let r = vec![vec![9.0], vec![1.0]];
        let z = vec![vec![0.0], vec![0.0]];
        assert_eq!(run(Arm::Hard, 1, &r, &z), vec![0]);
        assert_eq!(run(Arm::Soft, 1, &r, &z), vec![0]);
    }

    #[test]
    fn a_length_mismatch_is_an_error_not_a_panic() {
        let mut e = RobustElection::new(3, Arm::Soft);
        assert!(e.fold(0, &[1.0, 2.0], &[0.0, 0.0, 0.0]).is_err());
        assert!(e.fold(0, &[1.0, 2.0, 3.0], &[0.0]).is_err());
        assert!(
            e.fold(NO_FRAME, &[1.0, 2.0, 3.0], &[0.0, 0.0, 0.0])
                .is_err()
        );
        let other = RobustElection::new(4, Arm::Soft);
        assert!(e.absorb(&other).is_err());
        let wrong_arm = RobustElection::new(3, Arm::Hard);
        assert!(e.absorb(&wrong_arm).is_err());
    }
}
