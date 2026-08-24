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
        (0..self.pixels).filter(|&i| self.idx[i] == NO_FRAME).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
        assert_eq!(run(Arm::Ungated, 1, &r, &z), vec![1], "shipped elects motion");
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
        let r = vec![vec![4.0], vec![9.0], vec![7.0]];
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
        let r = vec![vec![1.0], vec![100.0], vec![1.0]];
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
        let r = vec![vec![4.0], vec![9.0], vec![7.0]];
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
        assert!(e.fold(NO_FRAME, &[1.0, 2.0, 3.0], &[0.0, 0.0, 0.0]).is_err());
        let other = RobustElection::new(4, Arm::Soft);
        assert!(e.absorb(&other).is_err());
        let wrong_arm = RobustElection::new(3, Arm::Hard);
        assert!(e.absorb(&wrong_arm).is_err());
    }
}
