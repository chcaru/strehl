//! Core types for `strehl`.
//!
//! Two decisions in here are architecturally irreversible and are documented as
//! such in `docs/research/SYNTHESIS.md` §9:
//!
//! - **Storage is `u16` CFA, arithmetic is `f32`.** `f16` is wrong for linear
//!   14-bit sensor data: a 10-bit mantissa quantises to roughly 8 LSB steps near
//!   white.
//! - **The noise model is injected, never re-derived per stage.** Six of eight
//!   pipeline stages consume it. A private per-stage estimate is the exact
//!   mechanism behind the prior project's measured 2-5x noise defect.

pub mod align;
pub mod boxfilter;
pub mod clip;
pub mod color;
pub mod demosaic;
pub mod flat_ratio;
pub mod focus;
pub mod merge;
pub mod noise;
pub mod plane;
pub mod profile;
pub mod stack;
pub mod through_focus;
pub mod warpmap;

/// Which plane of a 2x2 colour filter array a sample belongs to.
///
/// The two greens are modelled and calibrated **separately**. They sit on
/// different rows, see different crosstalk, and can have genuinely different
/// gain.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CfaPlane {
    R,
    G1,
    B,
    G2,
}

impl CfaPlane {
    /// The four planes in a stable order.
    pub const ALL: [CfaPlane; 4] = [CfaPlane::R, CfaPlane::G1, CfaPlane::B, CfaPlane::G2];

    /// Plane of the sample at `(x, y)` for an RGGB mosaic.
    pub fn rggb_at(x: usize, y: usize) -> CfaPlane {
        match (y % 2, x % 2) {
            (0, 0) => CfaPlane::R,
            (0, _) => CfaPlane::G1,
            (1, 0) => CfaPlane::G2,
            _ => CfaPlane::B,
        }
    }
}

/// How a stack was captured. This changes the alignment prior, and on a rail it
/// changes what is even representable: rail motion produces genuine parallax, so
/// no global 2D transform is correct.
///
/// v1 implements [`CaptureMode::FocusBracket`] only. [`CaptureMode::Rail`] is a
/// deliberate seam, not a supported path — there is no rail hardware to test
/// against, and an untested geometry model is worse than an absent one. Detect
/// the mode and refuse or warn; never silently apply the breathing model to rail
/// data.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CaptureMode {
    /// Camera fixed, focus moves. Frames differ by magnification (breathing).
    /// Every depth scales about one centre and occlusion never changes.
    FocusBracket,
    /// Camera translates, focus fixed. Scale becomes depth-dependent, and
    /// surfaces occlude and disclose at depth discontinuities.
    ///
    /// **Not implemented in v1.**
    Rail,
}

impl CaptureMode {
    /// Whether the pipeline can currently process this capture mode correctly.
    pub fn is_supported(&self) -> bool {
        matches!(self, CaptureMode::FocusBracket)
    }
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("unsupported CFA pattern: {0}")]
    UnsupportedCfa(String),
    #[error("frame {index} has dimensions {got:?}, expected {want:?}")]
    DimensionMismatch {
        index: usize,
        got: (usize, usize),
        want: (usize, usize),
    },
    #[error(transparent)]
    Other(#[from] anyhow::Error),
}

pub type Result<T> = std::result::Result<T, Error>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rggb_plane_assignment_matches_the_mosaic() {
        assert_eq!(CfaPlane::rggb_at(0, 0), CfaPlane::R);
        assert_eq!(CfaPlane::rggb_at(1, 0), CfaPlane::G1);
        assert_eq!(CfaPlane::rggb_at(0, 1), CfaPlane::G2);
        assert_eq!(CfaPlane::rggb_at(1, 1), CfaPlane::B);
        // and it tiles
        assert_eq!(CfaPlane::rggb_at(2, 2), CfaPlane::R);
        assert_eq!(CfaPlane::rggb_at(7033, 4689), CfaPlane::B);
    }

    #[test]
    fn rail_capture_is_not_claimed_as_supported() {
        // Deferred in v1: no rail hardware exists to validate the parallax
        // model against, and an untested geometry model is worse than none.
        assert!(CaptureMode::FocusBracket.is_supported());
        assert!(!CaptureMode::Rail.is_supported());
    }
}
