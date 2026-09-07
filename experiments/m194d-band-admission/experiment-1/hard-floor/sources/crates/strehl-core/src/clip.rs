//! Detection of samples pinned at the raw container maximum.
//!
//! # Why this exists
//!
//! A sample sitting at the container maximum is not a measurement. It is the
//! statement "at least this bright", and every frame that clips the same pixel
//! reports the same value regardless of focus. M26 measured the consequence on
//! `coffee-bubbles`: of 8,236,816 pixels, **616 are clipped in every frame**,
//! and the cross-frame focus contrast on those reads **1.0000 — the metric's
//! maximum** — against a median of 0.5398 on never-clipped pixels.
//!
//! The mechanism is measured, not assumed. **85.9% of always-clipped pixels
//! have `f_min` exactly 0.0**, against **0.0000%** of never-clipped pixels,
//! while their median `f_max` is **7598 against 145.6** — 52x typical. In one
//! frame the pixel sits inside a uniformly clipped blob where the gradient is
//! identically zero; in another the blob's edge crosses it. `(f_max - f_min) /
//! f_max` is then 1.0 by construction.
//!
//! This is the failure discipline 29 does **not** protect against. Discipline 29
//! chose cross-frame contrast over focus magnitude because magnitude fails on
//! fact 73's monotone edge — but on a pinned pixel *both* candidates read their
//! maximum, so they fail in the same direction and the choice buys nothing.
//!
//! # The two white levels, and why both are right
//!
//! `rawpy` reports two different numbers for these files and the project uses
//! both, for different purposes:
//!
//! - [`Levels::white`](crate::noise::Levels::white) is **15360**, the camera's
//!   declared per-channel white level. It bounds the range over which the noise
//!   model `sigma^2(S) = g*S + (RN*g)^2` was calibrated. It is pinned by
//!   `usable_white_level_is_not_the_container_maximum` in `noise.rs`.
//! - [`CONTAINER_MAX_DN`] is **16383**, the 14-bit container maximum. It is what
//!   "this sample is pinned" means.
//!
//! Real data *exceeds* the declared 15360, so these are genuinely different
//! numbers and neither is a bug. **Do not unify them.**
//!
//! # Saturation is per-stack, so detect it
//!
//! M26 measured that **four of six stacks contain zero pixels at or above
//! 15360**, their maxima sitting at 39-61% of it, while `coffee-bean` has 1.26%
//! at or above it and `coffee-bubbles` has pixels pinned at the container max.
//! So this census reports what it finds rather than assuming either way, and on
//! a clean stack it costs one comparison per sample and reports zero.
//!
//! Note that `109MSDCF` and `119MSDCF` — the stacks most of this project's
//! numbers come from — are two of the four with no saturation at all. Combined
//! with M24's finding that 109 is also the quietest photometrically, a clean
//! result on 109/119 is systematically weaker evidence than it looks.

use crate::plane::PlaneGeometry;
use crate::{Error, Result};

/// The 14-bit raw container maximum for the A7C II.
///
/// **This is not [`Levels::white`](crate::noise::Levels::white).** See the
/// module documentation: 15360 is the calibrated model's range, 16383 is the
/// container. Both are correct and they are not interchangeable.
pub const CONTAINER_MAX_DN: u16 = 16383;

/// Per-pixel count of how many frames clipped it.
///
/// `u16` per pixel — 2 bytes, **O(1) in the frame count**, so the memory ratchet
/// is untouched. The count saturates rather than wrapping, which matters only
/// for stacks beyond 65535 frames and is the safe direction anyway.
#[derive(Debug, Clone)]
pub struct ClipCensus {
    geom: PlaneGeometry,
    count: Vec<u16>,
    frames: u32,
}

impl ClipCensus {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            count: vec![0; geom.pixels()],
            frames: 0,
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    pub fn frames_folded(&self) -> u32 {
        self.frames
    }

    /// Bytes held, for the memory ratchet. Two per pixel, constant in frames.
    pub fn allocated_bytes(&self) -> usize {
        self.count.len() * size_of::<u16>()
    }

    /// Fold one frame's clip mask in.
    pub fn fold(&mut self, clipped: &[bool]) -> Result<()> {
        if clipped.len() != self.geom.pixels() {
            return Err(Error::DimensionMismatch {
                index: self.frames as usize,
                got: (clipped.len(), 1),
                want: (self.geom.pixels(), 1),
            });
        }
        for (c, &hit) in self.count.iter_mut().zip(clipped) {
            if hit {
                *c = c.saturating_add(1);
            }
        }
        self.frames += 1;
        Ok(())
    }

    /// Merge another worker's census. Exactly commutative and associative.
    pub fn absorb(&mut self, other: &ClipCensus) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: 0,
                got: (other.geom.pixels(), 1),
                want: (self.geom.pixels(), 1),
            });
        }
        for (c, &o) in self.count.iter_mut().zip(&other.count) {
            *c = c.saturating_add(o);
        }
        self.frames += other.frames;
        Ok(())
    }

    pub fn clipped_frames(&self, i: usize) -> u16 {
        self.count[i]
    }

    /// True where at least one frame clipped this pixel.
    pub fn ever_clipped(&self, i: usize) -> bool {
        self.count[i] > 0
    }

    /// True where **every** folded frame clipped this pixel.
    ///
    /// This is the maximum-severity case: the pixel is pinned in all frames, so
    /// it carries zero focus information and any peak-shape statistic computed
    /// on it is reading the clip, not the scene. M26 measured 616 such pixels on
    /// `coffee-bubbles`, all reading the confidence metric's maximum.
    ///
    /// Returns `false` when nothing has been folded, so an empty census makes no
    /// claims.
    pub fn always_clipped(&self, i: usize) -> bool {
        self.frames > 0 && self.count[i] as u32 == self.frames
    }

    /// Fraction of pixels clipped in at least one frame.
    pub fn ever_clipped_fraction(&self) -> f64 {
        if self.count.is_empty() {
            return 0.0;
        }
        self.count.iter().filter(|c| **c > 0).count() as f64 / self.count.len() as f64
    }

    /// Fraction of pixels clipped in every frame.
    pub fn always_clipped_fraction(&self) -> f64 {
        if self.count.is_empty() || self.frames == 0 {
            return 0.0;
        }
        let n = self
            .count
            .iter()
            .filter(|c| **c as u32 == self.frames)
            .count();
        n as f64 / self.count.len() as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    #[test]
    fn the_container_maximum_is_not_the_usable_white_level() {
        // The whole point of this module's two-white-levels note. If these ever
        // become equal, either the noise model's range has been widened past
        // its calibration or the clip test has been narrowed to a level real
        // data legitimately reaches.
        let usable = crate::noise::Levels {
            black: 512.0,
            white: 15360.0,
        };
        assert!(
            (CONTAINER_MAX_DN as f32) > usable.white,
            "the container max {CONTAINER_MAX_DN} must sit ABOVE the usable white {}",
            usable.white
        );
        assert_eq!(CONTAINER_MAX_DN, (1u16 << 14) - 1, "14-bit container");
    }

    #[test]
    fn a_pixel_clipped_in_every_frame_is_always_clipped() {
        let mut c = ClipCensus::new(geom(2, 1));
        c.fold(&[true, false]).unwrap();
        c.fold(&[true, true]).unwrap();
        assert!(c.always_clipped(0));
        assert!(
            !c.always_clipped(1),
            "clipped in 1 of 2 frames is not always"
        );
        assert!(c.ever_clipped(1));
        assert_eq!(c.clipped_frames(0), 2);
    }

    #[test]
    fn an_empty_census_makes_no_claims() {
        // Guards the degenerate reading of `count == frames` when both are 0,
        // which would declare every pixel always-clipped before anything is
        // folded — and this census is consulted to build a trust mask.
        let c = ClipCensus::new(geom(4, 4));
        for i in 0..16 {
            assert!(!c.always_clipped(i), "pixel {i} claimed before any fold");
            assert!(!c.ever_clipped(i));
        }
        assert_eq!(c.always_clipped_fraction(), 0.0);
    }

    #[test]
    fn absorb_matches_folding_the_same_frames_in_one_census() {
        let masks = [
            vec![true, false, true, false],
            vec![true, true, false, false],
            vec![true, false, false, true],
        ];
        let mut single = ClipCensus::new(geom(4, 1));
        for m in &masks {
            single.fold(m).unwrap();
        }
        let mut a = ClipCensus::new(geom(4, 1));
        a.fold(&masks[0]).unwrap();
        let mut b = ClipCensus::new(geom(4, 1));
        b.fold(&masks[1]).unwrap();
        b.fold(&masks[2]).unwrap();
        a.absorb(&b).unwrap();
        assert_eq!(a.frames_folded(), single.frames_folded());
        for i in 0..4 {
            assert_eq!(a.clipped_frames(i), single.clipped_frames(i), "pixel {i}");
            assert_eq!(a.always_clipped(i), single.always_clipped(i));
        }
        assert!(a.always_clipped(0), "pixel 0 is clipped in all three");
    }

    #[test]
    fn the_census_memory_is_two_bytes_per_pixel_and_constant_in_frames() {
        let mut c = ClipCensus::new(geom(1000, 1000));
        let before = c.allocated_bytes();
        assert_eq!(before, 2_000_000);
        for _ in 0..50 {
            c.fold(&vec![false; 1_000_000]).unwrap();
        }
        assert_eq!(
            c.allocated_bytes(),
            before,
            "the census must not grow with the frame count"
        );
    }

    #[test]
    fn a_dimension_mismatch_is_an_error_not_a_panic() {
        let mut c = ClipCensus::new(geom(2, 2));
        assert!(c.fold(&[true, false]).is_err());
        assert_eq!(c.frames_folded(), 0, "a rejected fold must not count");
    }
}
