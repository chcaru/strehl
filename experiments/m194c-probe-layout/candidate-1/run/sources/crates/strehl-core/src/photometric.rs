//! Per-frame photometric normalisation, and the noise it drags with it.
//!
//! # What this is for
//!
//! A focus bracket's frames are not the same brightness. On the four decks
//! M99 measured, the whole-frame flux moves by 8.2% to 36.9% end to end
//! (`docs/research/M99-photometric.md` §3). The merge elects a different source
//! frame in adjacent regions of the image, so a per-frame level difference
//! becomes a **brightness step at the election boundary** in the output. The
//! merge has no photometric term at all, and this module is the one it is
//! missing.
//!
//! # Why the estimator is a flux ratio and not a patch median
//!
//! A local level can change for two entirely different reasons, and only one of
//! them is a photometric defect:
//!
//! * the frame really received less light — **photometry**, which a gain fixes;
//! * defocus moved light from one place to another — **redistribution**, which
//!   a gain does *not* fix and which a gain applied anyway would corrupt.
//!
//! Blur conserves flux. So the mean above black over a fixed region is blind to
//! redistribution and sensitive only to photometry, and that is what
//! [`Flux`] accumulates. M99 measured the difference and it is not academic: on
//! `bee-3-cpl` the scene-fixed patch medians move by 18.2% while the conserved
//! flux moves by 8.7%, so a patch-median estimator would have doubled the
//! correction and spent the excess corrupting real image content.
//!
//! # Why the gain is fitted and not derived from the alignment solve
//!
//! The attractive hypothesis was that focus breathing changes magnification,
//! irradiance falls as `1/m^2`, and the per-frame level therefore tracks the
//! scale ladder the aligner already fits — making normalisation free for any
//! stacker that solves alignment. **M99 refuted it.** Against the aligner's own
//! fitted `a_k`, the fixed exponent `-2` is *worse than assuming no drift at
//! all* on three of four decks, and the free exponent that does fit is not a
//! constant: `q̂` = -4.74, -6.47, -0.88, -3.05 across the four. A law with a
//! seven-fold spread in its only exponent is not a law. See §4 of the report.
//!
//! The camera's own effective f-number (`SonyFNumber2`, which carries the
//! lens-extension term `N_eff = N(1+m)`) does better and has the right sign,
//! but still leaves 1.0-3.2% RMS unexplained, above the 1% materiality bar. So
//! the gain is **measured from the frames**, one scalar per frame, no offset.
//!
//! # Why there is no offset
//!
//! Fitting `L(k) = alpha + beta*L(ref)` across 294 patches spanning the tonal
//! range does return a large-looking intercept — up to 491 DN on
//! `lavendar-cpl`. It is not dark current. It is blur: defocus maps
//! `L -> (1-w)L + w*mean(L)`, which produces exactly the observed pairing of
//! `beta < 1` with `alpha > 0`, and `w*mean(L)` reproduces the measured
//! intercept to about 1%. An offset here would be a licence to eat real signal,
//! so this module fits a gain only. [`PhotometricMap`] has no offset term and
//! that absence is deliberate.
//!
//! # Where the flux must be folded: a low-detail region, not the whole frame
//!
//! This is the design correction Phase D forced, and it inverts the obvious
//! choice. Folding the flux over the whole covered plane gives a gain that is
//! **not the gain the render needs**, for a reason that only shows up once the
//! election is in the loop:
//!
//! * Whole-frame flux is conserved under blur, which is exactly why it is a
//!   clean *photometric* statistic — but the merge does not render the whole
//!   frame at one level. It renders each region from whichever frame won there.
//! * The regions that show the defect are the smooth ones. In a sharp region,
//!   defocus moves light *out* as the frame goes out of focus and *in* as it
//!   comes back; in the background it barely moves at all. So the whole-frame
//!   flux and the background's own level are different numbers, and they move
//!   differently across the bracket.
//!
//! Measured, on `bee-3-cpl` (299 frames, the full election in the loop): the
//! shipped render's background carries the **background** level ladder with
//! `SSC = 1.35` (permutation null sd 0.19, `z = 7.0`) but carries the
//! **whole-frame flux** ladder with `SSC = 0.13`, which is inside its own null.
//! Correcting with the whole-frame gain moved `SSC` only 1.35 -> 1.06 and made
//! the boundary-step contrast *worse*, 1.59 -> 1.70. Correcting with the gain
//! folded over the low-detail region moved `SSC` 1.35 -> 0.35 and improved the
//! boundary contrast to 1.39.
//!
//! So [`Flux::fold_covered`] should be given a mask that is the intersection of
//! the warp coverage with a **fixed, reference-derived low-detail region** —
//! [`low_detail_mask`] builds one. Fixed matters: the mask has to be the same
//! pixels in every frame, or the estimator re-acquires the sliding-patch
//! confound this milestone exists to remove.
//!
//! # What a per-frame scalar can and cannot do
//!
//! It cannot remove all of it, and the size of the shortfall was predicted
//! before it was measured. A frame-only scalar explains 0.751 of the between-
//! patch log-level variance on `bee-3-cpl` (§3, PR-2), i.e. the drift is a
//! **field**, not a global gain. Phase D then removed 74.0% of the defect with
//! a per-frame scalar. Those two numbers were obtained by completely different
//! routes and agree to 1.1 points, which is the strongest evidence in the
//! milestone that the residual is a real spatial term and not an estimator
//! defect. A future milestone wanting the last quarter needs a low-order
//! *field* per frame; this module deliberately does not guess at one.
//!
//! # The noise model must see the gain
//!
//! This is the part that is silent when it is wrong. Scaling a frame's signal
//! by `c` scales its noise by `c`, not by `sqrt(c)`:
//!
//! ```text
//! Var(c*S) = c^2 * (g*S + (RN*g)^2) = (c*g)*(c*S) + (c*RN*g)^2
//! ```
//!
//! so the scaled data is described by `gain_dn_per_e * c`, `read_noise_e`
//! **unchanged**, and a white level scaled about black. [`scale_plane_noise`]
//! is that transform and [`scale_noise_model`] lifts it to all four planes.
//!
//! A merge that scales frames without doing this feeds the gate a model that
//! predicts `sqrt(g*c*S)` where the truth is `c*sqrt(g*S)`, so it
//! **under-estimates sigma by up to a factor of `c`** on brightened frames. The
//! gate is calibrated in units of focus noise, so it then fires too readily on
//! exactly the frames that were scaled up, and noise wins elections it should
//! have lost. [`unscaled_sigma_ratio`] computes that error so a caller can
//! assert on it rather than hope.
//!
//! Note the direction carefully, because the neighbouring rule in
//! [`crate::profile::Corrections`] is the opposite one. There, a gain
//! *correction* re-describes unchanged data, so the dark floor `RN_e * g` is
//! preserved and `read_noise_e` moves inversely. Here the data itself is
//! scaled, so the dark floor genuinely scales with it. Preserving the floor
//! here would be the bug.

use crate::noise::{Levels, NoiseModel, PlaneNoise};
use crate::CfaPlane;

/// A gain outside this band is refused rather than applied. A real bracket on
/// this rig moves by tens of percent; a factor of two means the flux
/// measurement was broken (clipping, the subject leaving the frame, a wrong
/// coverage mask), and applying it would be worse than doing nothing.
pub const GAIN_BAND: (f32, f32) = (0.5, 2.0);

/// Above this clipped fraction the flux is under-counted and the ratio is
/// biased low, so the frame's gain is refused. Every deck M99 measured had a
/// clipped fraction of exactly zero, so this is a guard and not a tuning knob.
pub const MAX_CLIPPED_FRACTION: f64 = 1e-4;

// ===========================================================================
// M125: the three-valued mode, the drift estimator, and the auto decision.
// ===========================================================================

/// What the caller asked the photometric correction to do.
///
/// Three-valued on purpose. The two-valued form asks the owner to guess, and
/// the guess is wrong in both directions: M122 measured `--photometric`
/// helping `tweezers-cpl` (13.765% drift) to `B12` 0.7102 and *harming*
/// `bee-3-cpl` (1.629% drift) to 1.0638, which is why its pre-registered
/// promotion criterion failed and its verdict was KEEP-OFF.
///
/// `Auto` decides per stack from the stack's own measured drift. It is
/// **opt-in and should stay that way**: `AUTO_FRAMES_DOMAIN` is `33..=100`, so
/// on this rig's real brackets (205 and 299 frames) it abstains with code U1
/// and falls back to the default, making it a no-op dressed as a decision.
/// The unconditional `On` is the default since V-TONE; M122's KEEP-OFF was
/// retired because its criterion could not tell a seam from an edge.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum PhotometricMode {
    /// Never correct. The shipped default until V-TONE, and still the value
    /// this type's `Default` impl yields — that impl is used by tests only;
    /// the product default is resolved in `resolve_photometric_mode`.
    #[default]
    Off,
    /// Always correct. What `--photometric` has always meant.
    On,
    /// Decide per stack, and say out loud which way it went and why.
    Auto,
}

impl PhotometricMode {
    /// Parse a mode from a flag value or an environment variable.
    ///
    /// **An unrecognised value is an error, not a silent `On`.** The form this
    /// replaces was `is_some_and(|v| !v.is_empty() && v != "0")`, under which
    /// `STREHL_PHOTOMETRIC=banana` — and, worse, `STREHL_PHOTOMETRIC=off` —
    /// both turned the correction *on*. A typo that silently inverts a
    /// correction is exactly the class of defect this milestone exists to
    /// remove.
    pub fn parse(s: &str) -> Result<Self, PhotometricError> {
        match s.trim().to_ascii_lowercase().as_str() {
            "off" | "0" | "no" | "false" => Ok(Self::Off),
            "on" | "1" | "yes" | "true" => Ok(Self::On),
            "auto" => Ok(Self::Auto),
            _ => Err(PhotometricError::BadMode {
                given: s.to_string(),
            }),
        }
    }
}

/// The drift threshold `auto` applies at, in per-cent peak-to-peak.
///
/// **MEASURED, and it is one number carried by one stack — read the caveat.**
///
/// Selected by the leave-one-out procedure pre-registered in
/// `experiments/M125-photometric-auto/PREREGISTRATION.md` (committed at
/// `9ff95d5` *before* the score was read) over M122's 14-stack corpus. The
/// fitted optimum is 1.8392%; 1.84 is that value rounded to three significant
/// figures, and the rounding changes no decision on the corpus.
///
/// What the corpus does and does not pin down (M125 §D1–D3):
///
/// * Held out, the rule scores 0.9639 against 0.9683 for always-on and 1.0 for
///   always-off, and a 2000-shuffle placebo gives p = 0.019. All six
///   pre-registered acceptance criteria passed.
/// * **The margin over always-on is +0.0043 and 104% of it is one stack.**
///   Deleting `bee-3-cpl` — the single stack whose harm the rule avoids —
///   inverts the comparison to −0.0003. The conclusion survives 12 of 14
///   single-subject deletions, not 14.
/// * The training objective is flat to within 0.001 for every threshold from
///   1.64% to 8.45%, so the corpus cannot distinguish "decline the lowest-drift
///   stack" from "decline the lowest seven". This constant is one of many that
///   score alike.
///
/// That evidence is enough to offer `auto` as an opt-in and **is not enough to
/// move the default**, which is why the default did not move.
pub const AUTO_DRIFT_THRESHOLD_PCT: f64 = 1.84;

/// The frame counts the threshold was measured over, inclusive.
///
/// M122's 14 usable stacks were merged at 33, 63, 79 and 100 frames. `Dpp` is
/// a **peak-to-peak**, so it grows with the number of frames sampled — and it
/// grows in the direction that makes the *expensive* error more likely, since
/// a longer stack reads higher and is therefore more likely to be turned on by
/// a threshold calibrated on shorter ones. Extrapolating it is not allowed;
/// outside this range `auto` abstains and says so.
pub const AUTO_FRAMES_DOMAIN: std::ops::RangeInclusive<usize> = 33..=100;

/// Per-frame mean level, and the peak-to-peak drift across them.
///
/// This is M24's estimator, promoted into the library unchanged so that the
/// number `auto` decides on is the same number the correlation was measured
/// against. M122 reproduced M24's four published figures to within 0.004
/// percentage points with it; `LevelDrift` carries the same definition and is
/// commissioned against the same four numbers.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct LevelDrift {
    levels: Vec<f64>,
}

impl LevelDrift {
    pub fn new() -> Self {
        Self::default()
    }

    /// Record one frame's mean level above black.
    ///
    /// Non-finite means are dropped rather than poisoning the peak-to-peak:
    /// a single NaN would make `Dpp` NaN and the abstention that follows would
    /// blame the whole stack for one frame.
    pub fn push(&mut self, mean_level: f64) {
        if mean_level.is_finite() {
            self.levels.push(mean_level);
        }
    }

    pub fn len(&self) -> usize {
        self.levels.len()
    }

    pub fn is_empty(&self) -> bool {
        self.levels.is_empty()
    }

    /// Absorb another accumulator, for folding across parallel workers.
    ///
    /// Order-independent: `dpp` is a function of the max, the min and the mean,
    /// and all three are commutative. A merge that chunks frames differently
    /// therefore reads the same drift, which is what makes the decision
    /// reproducible run to run.
    pub fn absorb(&mut self, other: &Self) {
        self.levels.extend_from_slice(&other.levels);
    }

    /// `100 * (max - min) / mean`, in per-cent. `None` when undefined.
    ///
    /// M24's definition verbatim, including that the mean is over black-
    /// subtracted levels and is **not** clamped at zero. A non-positive mean
    /// means the frames sit at or below black, where a ratio is meaningless,
    /// and is reported as `None` rather than as a huge drift.
    pub fn dpp(&self) -> Option<f64> {
        if self.levels.is_empty() {
            return None;
        }
        let mut lo = f64::INFINITY;
        let mut hi = f64::NEG_INFINITY;
        let mut sum = 0.0;
        for &v in &self.levels {
            lo = lo.min(v);
            hi = hi.max(v);
            sum += v;
        }
        let mean = sum / self.levels.len() as f64;
        // `mean <= 0.0` is false for NaN, so the `is_finite` arm is what
        // catches a poisoned accumulator; both arms are needed.
        if mean <= 0.0 || !mean.is_finite() {
            return None;
        }
        let d = 100.0 * (hi - lo) / mean;
        d.is_finite().then_some(d)
    }
}

/// Mean of the CFA **G1** plane over the active area, above black.
///
/// G1 is `active[0::2, 1::2]` in an RGGB mosaic — even rows, odd columns —
/// which is the plane M24 measured and therefore the plane the threshold is
/// calibrated against.
///
/// Read from the **active area only** (rule 7). The full decoded buffer on this
/// body is 7168x5120 against a 7032x4688 active area, and the padding is zeros:
/// folding it would pull every level toward black by the padding fraction and
/// make the drift a function of the sensor's masked border.
///
/// `None` when the region admits no samples.
pub fn g1_mean_above_black(
    data: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    black: f32,
) -> Option<f64> {
    let (x0, y0, width, height) = active;
    let mut sum = 0.0f64;
    let mut count = 0u64;
    let black = f64::from(black);
    let mut y = 0;
    while y < height {
        let start = (y0 + y) * stride + x0;
        let row = &data[start..start + width];
        // odd columns of an even row: the G1 site of an RGGB mosaic
        for &v in row.iter().skip(1).step_by(2) {
            sum += f64::from(v) - black;
            count += 1;
        }
        y += 2;
    }
    (count > 0).then(|| sum / count as f64)
}

/// Why `auto` could not decide. Each variant is printed, never swallowed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AutoAbstention {
    /// U1: the stack's frame count is outside `AUTO_FRAMES_DOMAIN`.
    FramesOutsideDomain { frames: usize },
    /// U2: the drift estimator folded nothing, or produced a level at or below
    /// black where a ratio has no meaning.
    DriftUnavailable { frames_folded: usize },
    /// U3: the eroded low-detail region is too small to fit a gain against.
    RegionTooSmall { kept: usize, minimum: usize },
    /// U4: the fit produced no correction at all — every frame refused, or a
    /// gain span of exactly one.
    NoCorrectionAvailable { refused: usize, frames: usize },
}

impl std::fmt::Display for AutoAbstention {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::FramesOutsideDomain { frames } => write!(
                f,
                "U1 this stack merges {frames} frames, outside the {}..={} the decision rule was \
                 measured over. Dpp is a peak-to-peak and grows with the frame count, so \
                 extrapolating it would bias toward turning the correction ON -- the expensive \
                 direction",
                AUTO_FRAMES_DOMAIN.start(),
                AUTO_FRAMES_DOMAIN.end()
            ),
            Self::DriftUnavailable { frames_folded } => write!(
                f,
                "U2 the drift estimator produced no usable value from {frames_folded} folded \
                 frame(s); there is no measurement to decide on"
            ),
            Self::RegionTooSmall { kept, minimum } => write!(
                f,
                "U3 the eroded low-detail region keeps only {kept} px (minimum {minimum}); this \
                 scene has no background large enough to fit a gain against"
            ),
            Self::NoCorrectionAvailable { refused, frames } => write!(
                f,
                "U4 the fit produced no correction ({refused} of {frames} frames refused, gain \
                 span 1.0); there is nothing to apply"
            ),
        }
    }
}

/// What `auto` decided, and on what evidence.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AutoDecision {
    /// Drift is at or above the threshold: correct.
    Apply { drift_pct: f64 },
    /// Drift is below the threshold: do not correct. A *decision*, made on a
    /// measurement — not the same thing as an abstention.
    Decline { drift_pct: f64 },
    /// No decision could be made. Falls back to the default, **loudly**.
    Abstain(AutoAbstention),
}

impl AutoDecision {
    /// Whether the correction ends up applied. `Abstain` falls back to the
    /// current default, which is off.
    pub fn applies(&self) -> bool {
        matches!(self, Self::Apply { .. })
    }
}

/// Decide from a frame count and a measured drift.
///
/// Split out from the merge so it is testable without a decode, and so the
/// rule is one function rather than a condition smeared across a pipeline.
pub fn auto_decide(frames: usize, drift: Option<f64>) -> AutoDecision {
    if !AUTO_FRAMES_DOMAIN.contains(&frames) {
        return AutoDecision::Abstain(AutoAbstention::FramesOutsideDomain { frames });
    }
    match drift {
        None => AutoDecision::Abstain(AutoAbstention::DriftUnavailable {
            frames_folded: frames,
        }),
        Some(d) if d >= AUTO_DRIFT_THRESHOLD_PCT => AutoDecision::Apply { drift_pct: d },
        Some(d) => AutoDecision::Decline { drift_pct: d },
    }
}

/// What went wrong, when a map cannot be built.
///
/// `Display` and `Error` are written out rather than derived with `thiserror`.
/// The module has to compile both as `strehl_core::photometric` and as a
/// `#[path]` include from an example — the registration line in `lib.rs` is the
/// orchestrator's to apply, not a milestone's — and a path include resolves
/// `thiserror` against the *including* crate. Hand-rolling costs fifteen lines
/// and makes the two inclusion routes equivalent, which is the same reason
/// `robust.rs` carries no `crate::` references.
#[derive(Debug, PartialEq, Eq)]
pub enum PhotometricError {
    Empty,
    BadReference { reference: usize, n: usize },
    NoSamples { index: usize },
    BadReferenceFlux { index: usize, flux: u64 },
    OutOfRange { index: usize, n: usize },
    BadMode { given: String },
}

impl std::fmt::Display for PhotometricError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Empty => write!(f, "photometric estimation needs at least one frame"),
            Self::BadReference { reference, n } => {
                write!(f, "reference {reference} is out of range for {n} frames")
            }
            Self::NoSamples { index } => write!(
                f,
                "frame {index} has no samples above black; its flux is undefined"
            ),
            Self::BadReferenceFlux { index, flux } => write!(
                f,
                "the reference frame {index} has non-positive flux {}",
                f64::from_bits(*flux)
            ),
            Self::OutOfRange { index, n } => write!(
                f,
                "frame {index} index is out of range for a map of {n} frames"
            ),
            Self::BadMode { given } => write!(
                f,
                "{given:?} is not a photometric mode; expected off, on or auto. It is refused \
                 rather than guessed at: the form this replaced treated every unrecognised \
                 value -- including the word \"off\" -- as ON"
            ),
        }
    }
}

impl std::error::Error for PhotometricError {}

/// Mean signal above black over a region, plus the two things that can
/// invalidate it.
///
/// Accumulated in `f64`. A 33 Mpx plane summed in `f32` loses the low bits of
/// the running total long before the last row, and this quantity is a ratio
/// estimator whose whole value is in its low bits.
#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct Flux {
    sum: f64,
    count: u64,
    clipped: u64,
}

impl Flux {
    /// An empty accumulator.
    pub fn new() -> Self {
        Self::default()
    }

    /// Fold one plane of black-subtracted `f32` samples.
    ///
    /// `saturation` is the black-subtracted level at or above which a sample is
    /// treated as clipped. Samples are counted whether or not they are clipped,
    /// so that the mean stays a mean of the same region across frames; the
    /// clipped tally exists to refuse the frame, not to censor it.
    pub fn fold_plane(&mut self, samples: &[f32], saturation: f32) {
        for &v in samples {
            self.sum += f64::from(v);
            self.count += 1;
            if v >= saturation {
                self.clipped += 1;
            }
        }
    }

    /// Fold one plane, taking only the samples a coverage mask admits.
    ///
    /// The merge warps every frame onto the reference grid, and the border a
    /// warp pulls in from outside the source frame is not data. Including it
    /// would make the estimator a function of the *warp* as well as the light.
    ///
    /// # Panics
    ///
    /// If `samples` and `cover` differ in length.
    pub fn fold_covered(&mut self, samples: &[f32], cover: &[bool], saturation: f32) {
        assert_eq!(
            samples.len(),
            cover.len(),
            "coverage mask does not match the plane"
        );
        for (&v, &c) in samples.iter().zip(cover.iter()) {
            if !c {
                continue;
            }
            self.sum += f64::from(v);
            self.count += 1;
            if v >= saturation {
                self.clipped += 1;
            }
        }
    }

    /// Fold raw `u16` container samples, subtracting `black` as it goes.
    ///
    /// This is the decode-seam form: it is what a caller has before anything
    /// has been converted to `f32`. Samples below black contribute negatively,
    /// which is correct — noise straddles black and censoring the low side
    /// would bias the mean upwards on the darkest frames.
    pub fn fold_u16(&mut self, data: &[u16], black: f32, white: f32) {
        let sat = f64::from(white - black);
        for &v in data {
            let s = f64::from(v) - f64::from(black);
            self.sum += s;
            self.count += 1;
            if s >= sat {
                self.clipped += 1;
            }
        }
    }

    /// Mean signal above black, or `None` if nothing was folded.
    pub fn mean(&self) -> Option<f64> {
        if self.count == 0 {
            None
        } else {
            Some(self.sum / self.count as f64)
        }
    }

    /// How many samples were folded.
    pub fn count(&self) -> u64 {
        self.count
    }

    /// Fraction of folded samples at or above saturation.
    pub fn clipped_fraction(&self) -> f64 {
        if self.count == 0 {
            0.0
        } else {
            self.clipped as f64 / self.count as f64
        }
    }
}

/// Where a map's gains came from. Carried so a stage can report, and a test can
/// assert, which one it ran on.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GainSource {
    /// Fitted from the frames' own conserved flux. The only source M99's
    /// measurements support.
    MeasuredFlux,
    /// Every gain is exactly one. Used as the null arm of a comparison, and as
    /// the honest result when estimation is refused.
    Unity,
}

/// One scalar gain per frame, normalised so the reference frame is exactly 1.
///
/// There is no offset term. See the module header for why that is a measured
/// decision and not an omission.
#[derive(Debug, Clone, PartialEq)]
pub struct PhotometricMap {
    gains: Vec<f32>,
    refused: Vec<Option<String>>,
    reference: usize,
    source: GainSource,
}

impl PhotometricMap {
    /// A map that changes nothing, for the null arm.
    pub fn unity(n: usize, reference: usize) -> Result<Self, PhotometricError> {
        if n == 0 {
            return Err(PhotometricError::Empty);
        }
        if reference >= n {
            return Err(PhotometricError::BadReference { reference, n });
        }
        Ok(Self {
            gains: vec![1.0; n],
            refused: vec![None; n],
            reference,
            source: GainSource::Unity,
        })
    }

    /// Fit gains from per-frame flux, normalised to `reference`.
    ///
    /// A frame whose flux is unusable — no samples, too much clipping, or a
    /// ratio outside [`GAIN_BAND`] — is given a gain of exactly 1 and a
    /// recorded reason. It is **not** dropped and it is **not** silently
    /// scaled: a refusal that looks like a correction is the failure this
    /// project keeps finding in other people's stackers.
    pub fn from_flux(flux: &[Flux], reference: usize) -> Result<Self, PhotometricError> {
        let n = flux.len();
        if n == 0 {
            return Err(PhotometricError::Empty);
        }
        if reference >= n {
            return Err(PhotometricError::BadReference { reference, n });
        }
        let r = flux[reference]
            .mean()
            .ok_or(PhotometricError::NoSamples { index: reference })?;
        if r <= 0.0 || !r.is_finite() {
            return Err(PhotometricError::BadReferenceFlux {
                index: reference,
                flux: r.to_bits(),
            });
        }

        let mut gains = Vec::with_capacity(n);
        let mut refused = Vec::with_capacity(n);
        for (k, f) in flux.iter().enumerate() {
            let why = match f.mean() {
                None => Some("no samples above black".to_string()),
                Some(m) if m <= 0.0 || !m.is_finite() => {
                    Some(format!("flux {m} is not usable"))
                }
                Some(_) if f.clipped_fraction() > MAX_CLIPPED_FRACTION => Some(format!(
                    "clipped fraction {:.3e} exceeds {:.3e}; the flux is biased low",
                    f.clipped_fraction(),
                    MAX_CLIPPED_FRACTION
                )),
                Some(m) => {
                    let g = (r / m) as f32;
                    if g < GAIN_BAND.0 || g > GAIN_BAND.1 {
                        Some(format!(
                            "gain {g:.4} is outside the plausible band {GAIN_BAND:?}"
                        ))
                    } else {
                        None
                    }
                }
            };
            match why {
                Some(w) => {
                    gains.push(1.0);
                    refused.push(Some(w));
                }
                None => {
                    // The reference divides itself, so its gain is exactly 1.0
                    // by construction rather than by luck.
                    let g = if k == reference {
                        1.0
                    } else {
                        (r / f.mean().unwrap_or(r)) as f32
                    };
                    gains.push(g);
                    refused.push(None);
                }
            }
        }
        Ok(Self {
            gains,
            refused,
            reference,
            source: GainSource::MeasuredFlux,
        })
    }

    /// Number of frames.
    pub fn len(&self) -> usize {
        self.gains.len()
    }

    /// Is the map empty? It never is — [`PhotometricError::Empty`] refuses that
    /// at construction — but clippy asks and the answer is cheap.
    pub fn is_empty(&self) -> bool {
        self.gains.is_empty()
    }

    /// The reference frame, whose gain is exactly 1.
    pub fn reference(&self) -> usize {
        self.reference
    }

    /// Where the gains came from.
    pub fn source(&self) -> GainSource {
        self.source
    }

    /// The gain for frame `index`.
    pub fn gain(&self, index: usize) -> Result<f32, PhotometricError> {
        self.gains
            .get(index)
            .copied()
            .ok_or(PhotometricError::OutOfRange {
                index,
                n: self.gains.len(),
            })
    }

    /// All gains.
    pub fn gains(&self) -> &[f32] {
        &self.gains
    }

    /// Why frame `index` was refused, if it was.
    pub fn refusal(&self, index: usize) -> Option<&str> {
        self.refused.get(index).and_then(|o| o.as_deref())
    }

    /// How many frames were refused a gain.
    pub fn refused_count(&self) -> usize {
        self.refused.iter().filter(|o| o.is_some()).count()
    }

    /// The largest correction in the map, as a ratio at or above 1.
    ///
    /// This is the number to compare against a materiality bar: it is the
    /// worst brightness step the merge could have put across an election
    /// boundary.
    pub fn span(&self) -> f32 {
        let mut lo = f32::INFINITY;
        let mut hi = 0.0f32;
        for &g in &self.gains {
            lo = lo.min(g);
            hi = hi.max(g);
        }
        if lo > 0.0 && lo.is_finite() {
            hi / lo
        } else {
            1.0
        }
    }
}

/// Build the fixed low-detail region the flux should be folded over.
///
/// `detail` is any per-pixel sharpness response on the reference frame — the
/// merge's regularised focus field is the natural one — and `luma` is that same
/// frame's black-subtracted signal. A pixel is admitted when its detail is in
/// the lowest `detail_q` fraction **and** its luma is in the top
/// `1 - luma_q` fraction.
///
/// Both conditions are needed. Low detail alone is not background: an unlit
/// subject is smooth too, and admitting it on `bee-3-cpl` put the region's
/// standard deviation at 62% of its mean, which is scene structure and not a
/// backdrop. Requiring brightness as well took that to 20%.
///
/// The region is built **once, from one frame**, and then held fixed. That is
/// the whole point: a region re-chosen per frame slides across the scene as the
/// magnification breathes, and then measures the scene's own lighting gradient
/// instead of the frame's level. That confound is what M99 was convened to
/// remove and it is easy to reintroduce here.
///
/// Returns the number of admitted pixels. `out` is written in full.
pub fn low_detail_mask(
    detail: &[f32],
    luma: &[f32],
    detail_q: f64,
    luma_q: f64,
    out: &mut [bool],
) -> usize {
    assert_eq!(detail.len(), luma.len(), "detail and luma must agree");
    assert_eq!(out.len(), detail.len(), "mask must be plane-sized");
    let dthr = finite_quantile(detail, detail_q);
    let lthr = finite_quantile(luma, luma_q);
    let mut n = 0usize;
    for (i, o) in out.iter_mut().enumerate() {
        let (d, l) = (detail[i], luma[i]);
        *o = d.is_finite() && l.is_finite() && d <= dthr && l >= lthr;
        n += usize::from(*o);
    }
    n
}

/// Shrink a mask away from its own perimeter by `radius` pixels.
///
/// # Why this exists
///
/// [`low_detail_mask`] selects pixels by a per-pixel threshold, so the region
/// it returns is scattered and its perimeter is long. Defocus moves flux across
/// that perimeter: a frame in which the subject is blurred spills light into
/// the low-detail pixels that border it, and the estimator reads that spill as
/// a brightness change that is not there.
///
/// It is not a small effect. On a flux-conserving blur sweep, where the correct
/// answer is exactly zero, the raw threshold mask reports a peak spurious gain
/// of **3.63%**, a compact block of the same area reports **0.022%**, and the
/// same threshold mask eroded by 16 px reports **0.0000%** — see
/// `the_low_detail_mask_does_not_leak_flux_across_its_perimeter`. Erosion beats
/// compactness because it keeps the low-gradient selectivity *and* removes the
/// exposed boundary.
///
/// Erosion is not free: it cost 65% of the selected pixels in that test
/// (28741 -> 10130). That is a good trade, because the estimator folds a mean
/// and a mean over 10k pixels is already far past the point where count
/// matters, while the bias it removes is systematic and does not average out.
///
/// `radius` should be at least the largest defocus blur radius the bracket
/// contains; the module's own null used 16 px on a 192 px frame.
pub fn erode_mask(mask: &[bool], width: usize, radius: usize, out: &mut [bool]) -> usize {
    assert_eq!(mask.len(), out.len(), "erode_mask: sizes must agree");
    assert!(width > 0, "erode_mask: width must be positive");
    let h = mask.len() / width;
    if radius == 0 {
        out.copy_from_slice(mask);
        return mask.iter().filter(|&&b| b).count();
    }
    // Separable erosion: a pixel survives iff every pixel in the (2r+1) square
    // survives, which is a horizontal pass followed by a vertical one.
    let mut mid = vec![false; mask.len()];
    for y in 0..h {
        for x in 0..width {
            let (lo, hi) = (x.saturating_sub(radius), (x + radius).min(width - 1));
            mid[y * width + x] =
                x >= radius && x + radius < width && mask[y * width + lo..=y * width + hi]
                    .iter()
                    .all(|&b| b);
        }
    }
    let mut n = 0usize;
    for y in 0..h {
        for x in 0..width {
            let keep = y >= radius
                && y + radius < h
                && (y - radius..=y + radius).all(|yy| mid[yy * width + x]);
            out[y * width + x] = keep;
            n += usize::from(keep);
        }
    }
    n
}

/// Quantile of the finite entries, by nearest rank. `NaN` never participates:
/// the warp writes `NaN` outside coverage, and letting those sort would move
/// every threshold by the size of the uncovered border.
fn finite_quantile(v: &[f32], q: f64) -> f32 {
    let mut f: Vec<f32> = v.iter().copied().filter(|x| x.is_finite()).collect();
    if f.is_empty() {
        return f32::NAN;
    }
    f.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let i = ((f.len() - 1) as f64 * q.clamp(0.0, 1.0)).round() as usize;
    f[i]
}

/// Scale black-subtracted `f32` samples in place.
pub fn apply_to_plane(samples: &mut [f32], gain: f32) {
    if gain == 1.0 {
        return;
    }
    for v in samples.iter_mut() {
        *v *= gain;
    }
}

/// Scale `u16` container samples in place, about the black level.
///
/// Rounds to nearest and clamps into `[0, white]`. Black maps to black exactly,
/// so a gain of 1 is a bit-exact no-op and the black level a downstream stage
/// subtracts is still the black level.
///
/// The clamp is at `white`, not at `u16::MAX`: a value scaled above the usable
/// white level is saturated data and must present as saturated, not wrap into
/// headroom the sensor never had.
pub fn apply_to_u16(data: &mut [u16], black: f32, white: f32, gain: f32) {
    if gain == 1.0 {
        return;
    }
    let hi = white.max(black);
    for v in data.iter_mut() {
        let s = (f32::from(*v) - black) * gain + black;
        *v = s.round().clamp(0.0, hi) as u16;
    }
}

/// The noise of one plane after its data has been multiplied by `gain`.
///
/// `Var(c*S) = c^2*(g*S + (RN*g)^2) = (c*g)*(c*S) + (c*RN*g)^2`, so the gain in
/// DN per electron scales by `c`, the read noise **in electrons is unchanged**,
/// and the read floor in DN scales by `c` — which is the point, because the
/// read noise in the scaled data really is `c` times larger.
///
/// White scales about black; black is fixed, because [`apply_to_u16`] scales
/// about black and so leaves it where it was.
pub fn scale_plane_noise(p: PlaneNoise, gain: f32) -> PlaneNoise {
    PlaneNoise {
        gain_dn_per_e: p.gain_dn_per_e * gain,
        read_noise_e: p.read_noise_e,
        levels: Levels {
            black: p.levels.black,
            white: p.levels.black + (p.levels.white - p.levels.black) * gain,
        },
    }
}

/// [`scale_plane_noise`] on all four planes, preserving ISO, provenance and any
/// attached PRNU.
///
/// PRNU's `kappa` is a **fraction of signal**, so `(kappa*c*S)^2 = c^2
/// (kappa*S)^2` scales with everything else and `kappa` itself does not change.
pub fn scale_noise_model(model: &NoiseModel, gain: f32) -> NoiseModel {
    let planes = [
        scale_plane_noise(*model.plane(CfaPlane::R), gain),
        scale_plane_noise(*model.plane(CfaPlane::G1), gain),
        scale_plane_noise(*model.plane(CfaPlane::B), gain),
        scale_plane_noise(*model.plane(CfaPlane::G2), gain),
    ];
    let scaled = NoiseModel::new(planes, model.iso, model.provenance);
    match model.prnu() {
        Some(k) => scaled.with_prnu(k),
        None => scaled,
    }
}

/// How wrong a gate is if a frame is scaled and the noise model is not told.
///
/// Returns `sigma_true / sigma_believed` at black-subtracted signal `signal_dn`
/// **before** scaling. A value above 1 means the unscaled model under-estimates
/// the noise, so a gate calibrated in units of sigma fires too readily on that
/// frame — which is how a photometric correction silently turns into a
/// mis-calibrated election.
///
/// The bound is `sqrt(c)` in the photon-dominated limit and `c` in the
/// read-dominated one, so a caller that wants a single number should evaluate
/// this at the darkest level it cares about.
pub fn unscaled_sigma_ratio(p: PlaneNoise, gain: f32, signal_dn: f32) -> f32 {
    let truth = gain * p.sigma(signal_dn);
    let believed = p.sigma(signal_dn * gain);
    if believed > 0.0 {
        truth / believed
    } else {
        f32::NAN
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ---- M125: the three-valued mode ------------------------------------

    #[test]
    fn every_documented_mode_spelling_parses_to_the_documented_mode() {
        for s in ["off", "OFF", " off ", "0", "no", "false"] {
            assert_eq!(PhotometricMode::parse(s), Ok(PhotometricMode::Off), "{s}");
        }
        for s in ["on", "ON", "1", "yes", "true"] {
            assert_eq!(PhotometricMode::parse(s), Ok(PhotometricMode::On), "{s}");
        }
        for s in ["auto", "AUTO", " Auto "] {
            assert_eq!(PhotometricMode::parse(s), Ok(PhotometricMode::Auto), "{s}");
        }
    }

    /// The defect this milestone exists to remove, pinned so it cannot return.
    ///
    /// The predecessor was `!v.is_empty() && v != "0"`, under which every one
    /// of these turned the correction ON -- including the literal word "off".
    #[test]
    fn an_unrecognised_mode_is_refused_and_never_silently_on() {
        for s in ["banana", "", "of", "onn", "auto ]", "2", "-1", "none"] {
            let got = PhotometricMode::parse(s);
            assert!(
                matches!(got, Err(PhotometricError::BadMode { .. })),
                "{s:?} parsed to {got:?}; an unrecognised mode must be refused"
            );
        }
        // and the negative control for this very test: if `parse` refused
        // everything, the test above would pass vacuously.
        assert_eq!(PhotometricMode::parse("on"), Ok(PhotometricMode::On));
    }

    /// The `Default` impl yields `Off`. **This is not the product default.**
    ///
    /// The shipped default is `On`, resolved in
    /// `strehl_cli::merge_cmd::resolve_photometric_mode` and asserted there.
    /// This test pins the type's zero value only. It was called
    /// `the_default_mode_is_off` while that was also the product default, and
    /// the name survived the flip long enough to be worth renaming: a test
    /// whose name states a default it does not test is the same defect as a
    /// registry that declares one it did not run.
    #[test]
    fn the_zero_value_of_the_mode_type_is_off() {
        assert_eq!(PhotometricMode::default(), PhotometricMode::Off);
    }

    // ---- M125: the drift estimator ---------------------------------------

    /// A flat stack has no drift. Not a tautology: the estimator divides by a
    /// mean that is nowhere near zero here, so a sign or offset error shows.
    #[test]
    fn a_stack_with_no_level_variation_reads_zero_drift() {
        let mut d = LevelDrift::new();
        for _ in 0..10 {
            d.push(1400.0);
        }
        assert_eq!(d.dpp(), Some(0.0));
    }

    /// Independently obtained: for levels 900..=1100 the peak-to-peak is 200
    /// and the mean is 1000, so Dpp is 100 * 200 / 1000 = 20% exactly, worked
    /// out by hand and not by running the code (rule 35).
    #[test]
    fn dpp_matches_a_hand_computed_peak_to_peak_over_mean() {
        let mut d = LevelDrift::new();
        for v in [900.0, 1000.0, 1100.0] {
            d.push(v);
        }
        let got = d.dpp().expect("three finite levels");
        assert!((got - 20.0).abs() < 1e-12, "got {got}, hand-computed 20.0");
    }

    /// The estimator must not be a function of how the merge chunked its
    /// frames across workers, or the same stack decides differently run to run.
    #[test]
    fn drift_is_independent_of_the_order_frames_are_folded_in() {
        let levels = [1391.6, 1404.3, 1397.9, 1393.1, 1402.4, 1395.5];
        let mut a = LevelDrift::new();
        for v in levels {
            a.push(v);
        }
        let mut b = LevelDrift::new();
        for v in levels.iter().rev() {
            b.push(*v);
        }
        let mut c = LevelDrift::new();
        let mut c2 = LevelDrift::new();
        for (i, v) in levels.iter().enumerate() {
            if i % 2 == 0 {
                c.push(*v);
            } else {
                c2.push(*v);
            }
        }
        c.absorb(&c2);
        assert_eq!(a.dpp(), b.dpp());
        assert_eq!(a.dpp(), c.dpp());
        // negative control: a genuinely different set must NOT match, or the
        // three assertions above would be satisfied by a constant.
        let mut other = LevelDrift::new();
        for v in levels {
            other.push(v + if v > 1400.0 { 50.0 } else { 0.0 });
        }
        assert_ne!(a.dpp(), other.dpp());
    }

    #[test]
    fn drift_is_undefined_rather_than_huge_when_there_is_nothing_to_divide_by() {
        assert_eq!(LevelDrift::new().dpp(), None);
        let mut zero = LevelDrift::new();
        zero.push(0.0);
        zero.push(0.0);
        assert_eq!(zero.dpp(), None, "a mean at black has no ratio");
        let mut below = LevelDrift::new();
        below.push(-5.0);
        below.push(-3.0);
        assert_eq!(below.dpp(), None, "a mean below black has no ratio");
    }

    #[test]
    fn a_non_finite_frame_level_is_dropped_and_does_not_poison_the_stack() {
        let mut d = LevelDrift::new();
        d.push(900.0);
        d.push(f64::NAN);
        d.push(1100.0);
        d.push(f64::INFINITY);
        assert_eq!(d.len(), 2);
        let got = d.dpp().expect("two finite levels survive");
        assert!((got - 20.0).abs() < 1e-12, "got {got}");
    }

    // ---- M125: the G1 fold ------------------------------------------------

    /// The fold must read G1 -- even rows, odd columns -- and nothing else.
    /// Planted so each plane carries a distinct constant, so reading the wrong
    /// one is a wrong number rather than a near miss.
    #[test]
    fn the_g1_fold_reads_only_the_g1_site_of_an_rggb_mosaic() {
        // 4x4 active area inside a 6x6 buffer, RGGB: R G / G B
        let stride = 6;
        let mut data = vec![0u16; stride * 6];
        for y in 0..4 {
            for x in 0..4 {
                let v = match (y % 2, x % 2) {
                    (0, 0) => 1000, // R
                    (0, 1) => 2000, // G1
                    (1, 0) => 3000, // G2
                    _ => 4000,      // B
                };
                data[(1 + y) * stride + 1 + x] = v;
            }
        }
        let got = g1_mean_above_black(&data, stride, (1, 1, 4, 4), 500.0).expect("samples");
        assert!((got - 1500.0).abs() < 1e-12, "got {got}, expected 2000-500");
    }

    /// Rule 7: the padding outside the active area is zeros, and folding it
    /// drags the level toward black. This is the test that would have caught
    /// a fold over `frame.data` entire.
    #[test]
    fn the_g1_fold_ignores_the_padding_outside_the_active_area() {
        let stride = 8;
        let mut data = vec![0u16; stride * 8];
        for y in 0..4 {
            for x in 0..4 {
                if x % 2 == 1 && y % 2 == 0 {
                    data[(2 + y) * stride + 2 + x] = 2000;
                }
            }
        }
        let tight = g1_mean_above_black(&data, stride, (2, 2, 4, 4), 500.0).expect("samples");
        assert!((tight - 1500.0).abs() < 1e-12, "got {tight}");
        // the same buffer read as if the whole thing were active
        let loose = g1_mean_above_black(&data, stride, (0, 0, 8, 8), 500.0).expect("samples");
        assert!(
            loose < tight - 100.0,
            "padding must move the level ({loose} vs {tight}); if it does not, \
             this test has no power"
        );
    }

    #[test]
    fn the_g1_fold_reports_nothing_rather_than_zero_for_an_empty_region() {
        assert_eq!(
            g1_mean_above_black(&[0u16; 16], 4, (0, 0, 4, 0), 512.0),
            None
        );
        assert_eq!(
            g1_mean_above_black(&[0u16; 16], 4, (0, 0, 1, 4), 512.0),
            None
        );
    }

    // ---- M125: the auto decision -----------------------------------------

    #[test]
    fn auto_applies_at_and_above_the_threshold_and_declines_below_it() {
        let n = *AUTO_FRAMES_DOMAIN.start() + 1;
        assert!(auto_decide(n, Some(AUTO_DRIFT_THRESHOLD_PCT)).applies());
        assert!(auto_decide(n, Some(AUTO_DRIFT_THRESHOLD_PCT + 1e-9)).applies());
        assert!(!auto_decide(n, Some(AUTO_DRIFT_THRESHOLD_PCT - 1e-9)).applies());
        assert!(matches!(
            auto_decide(n, Some(0.5)),
            AutoDecision::Decline { .. }
        ));
    }

    /// The two stacks the threshold was chosen to separate, from M122's own
    /// measured corpus. `tweezers-cpl` at 13.765% is the large win; the rule
    /// must take it. `bee-3-cpl` at 1.629% is the 6.4% harm that made M122's
    /// promotion fail; the rule must decline it.
    #[test]
    fn auto_takes_the_measured_win_and_declines_the_measured_harm() {
        assert!(
            auto_decide(100, Some(13.765)).applies(),
            "tweezers-cpl, B12n 0.7183"
        );
        assert!(
            !auto_decide(100, Some(1.629)).applies(),
            "bee-3-cpl, B12n 1.0633 -- the harm the rule exists to avoid"
        );
        // the pair either side of the threshold, from the same corpus
        assert!(auto_decide(100, Some(2.026)).applies(), "lead-1-cpl");
        assert!(!auto_decide(100, Some(1.652)).applies(), "bee-2-cpl");
    }

    /// `unknown` must not collapse into `no` (discipline 862). Abstention is a
    /// distinct state from a decline, and the two must not be confused by a
    /// caller that only looks at `applies()`.
    #[test]
    fn abstention_is_a_distinct_state_from_a_decline() {
        let short = auto_decide(*AUTO_FRAMES_DOMAIN.start() - 1, Some(50.0));
        assert!(matches!(
            short,
            AutoDecision::Abstain(AutoAbstention::FramesOutsideDomain { .. })
        ));
        assert!(!short.applies());

        let long = auto_decide(*AUTO_FRAMES_DOMAIN.end() + 1, Some(50.0));
        assert!(matches!(
            long,
            AutoDecision::Abstain(AutoAbstention::FramesOutsideDomain { .. })
        ));

        let blind = auto_decide(100, None);
        assert!(matches!(
            blind,
            AutoDecision::Abstain(AutoAbstention::DriftUnavailable { .. })
        ));

        // and they are not equal to a decline that happens to also not apply
        let declined = auto_decide(100, Some(0.1));
        assert_ne!(short, declined);
        assert_ne!(blind, declined);
    }

    /// A high-drift stack outside the domain must abstain rather than apply.
    /// This is the case that costs the owner something real -- a 299-frame
    /// `bee-3-cpl` merge -- and it is the honest answer, because Dpp grows with
    /// the frame count in the direction that would wrongly turn it on.
    #[test]
    fn a_stack_outside_the_domain_abstains_even_when_its_drift_is_far_above_the_bar() {
        let d = auto_decide(299, Some(40.0));
        assert!(!d.applies(), "extrapolating the rule is not allowed");
        assert!(matches!(
            d,
            AutoDecision::Abstain(AutoAbstention::FramesOutsideDomain { frames: 299 })
        ));
    }

    #[test]
    fn every_abstention_reason_prints_a_reason_and_its_numbers() {
        let cases = [
            AutoAbstention::FramesOutsideDomain { frames: 299 },
            AutoAbstention::DriftUnavailable { frames_folded: 0 },
            AutoAbstention::RegionTooSmall {
                kept: 886,
                minimum: 1024,
            },
            AutoAbstention::NoCorrectionAvailable {
                refused: 100,
                frames: 100,
            },
        ];
        for c in cases {
            let s = c.to_string();
            assert!(s.len() > 40, "abstention {c:?} says too little: {s:?}");
            assert!(
                s.starts_with('U'),
                "abstention {c:?} must name its registered condition: {s:?}"
            );
        }
        // the numbers must actually appear, or the message is decoration
        assert!(
            AutoAbstention::FramesOutsideDomain { frames: 299 }
                .to_string()
                .contains("299")
        );
        assert!(
            AutoAbstention::RegionTooSmall {
                kept: 886,
                minimum: 1024
            }
            .to_string()
            .contains("886")
        );
    }

    /// The shipped constant must stay inside the gap the corpus measured it in,
    /// between `bee-2-cpl` at 1.652% and `lead-1-cpl` at 2.026%. If someone
    /// edits it out of that gap the decision table changes and this fails.
    #[test]
    #[allow(
        clippy::assertions_on_constants,
        reason = "the constant value is exactly what is under test: this is a \
                  tripwire on a shipped tuning constant, not a runtime check"
    )]
    fn the_shipped_threshold_sits_in_the_gap_it_was_fitted_in() {
        assert!(
            AUTO_DRIFT_THRESHOLD_PCT > 1.652 && AUTO_DRIFT_THRESHOLD_PCT < 2.026,
            "threshold {AUTO_DRIFT_THRESHOLD_PCT} left the measured gap"
        );
    }
    use crate::noise::Provenance;

    fn plane(g: f32, rn: f32) -> PlaneNoise {
        PlaneNoise {
            gain_dn_per_e: g,
            read_noise_e: rn,
            levels: Levels {
                black: 512.0,
                white: 15360.0,
            },
        }
    }

    #[test]
    fn erode_mask_removes_exactly_the_perimeter_and_nothing_else() {
        // A 9x9 solid block inside an 21x21 field. Eroding by 2 must leave a
        // 5x5 block in the same place: (9-2*2)^2 = 25.
        const W: usize = 21;
        let mut m = vec![false; W * W];
        for y in 6..15 {
            for x in 6..15 {
                m[y * W + x] = true;
            }
        }
        let mut out = vec![false; W * W];
        let n = erode_mask(&m, W, 2, &mut out);
        assert_eq!(n, 25, "eroding 9x9 by 2 must leave 5x5");
        for y in 0..W {
            for x in 0..W {
                let want = (8..13).contains(&y) && (8..13).contains(&x);
                assert_eq!(out[y * W + x], want, "pixel ({x},{y})");
            }
        }

        // Radius 0 is the identity, and must not silently drop anything.
        let mut id = vec![false; W * W];
        assert_eq!(erode_mask(&m, W, 0, &mut id), 81);
        assert_eq!(id, m);

        // A one-pixel-wide bridge is exactly the structure that leaks flux,
        // and erosion must delete it entirely rather than thin it.
        let mut bridge = vec![false; W * W];
        for x in 0..W {
            bridge[10 * W + x] = true;
        }
        let mut gone = vec![false; W * W];
        assert_eq!(
            erode_mask(&bridge, W, 1, &mut gone),
            0,
            "a 1px line must not survive erosion by 1"
        );
    }

    /// PR-16. A defocus-only null: a wrap-around box blur conserves total flux
    /// exactly, so any gain drift a region reports under blur is spurious. M87
    /// measured that its subject-avoiding mask leaked 5x more than a compact
    /// equal-area block, because blur carries flux across a long perimeter.
    /// This module's mask is a per-pixel threshold and is more fragmented
    /// still, so the concern transfers and is tested rather than argued.
    #[test]
    fn the_low_detail_mask_does_not_leak_flux_across_its_perimeter() {
        const W: usize = 192;
        let n = W * W;

        // A scene with real subject structure: a bright disc, a hard-edged bar
        // and a lit gradient background. Blur will move a lot of light around.
        let mut sharp = vec![0.0f32; n];
        for y in 0..W {
            for x in 0..W {
                let (dx, dy) = (x as f32 - 62.0, y as f32 - 70.0);
                let disc = if dx * dx + dy * dy < 30.0 * 30.0 {
                    12000.0
                } else {
                    0.0
                };
                let bar = if (100..118).contains(&y) && (20..170).contains(&x) {
                    6000.0
                } else {
                    0.0
                };
                sharp[y * W + x] = 2000.0 + 6.0 * x as f32 + disc + bar;
            }
        }

        // Flux-conserving separable box blur (wrap-around).
        let blur = |src: &[f32], rad: usize| -> Vec<f32> {
            let k = (2 * rad + 1) as f32;
            let mut mid = vec![0.0f32; n];
            for y in 0..W {
                for x in 0..W {
                    let mut s = 0.0f32;
                    for d in 0..=2 * rad {
                        s += src[y * W + (x + W + d - rad) % W];
                    }
                    mid[y * W + x] = s / k;
                }
            }
            let mut out = vec![0.0f32; n];
            for y in 0..W {
                for x in 0..W {
                    let mut s = 0.0f32;
                    for d in 0..=2 * rad {
                        s += mid[((y + W + d - rad) % W) * W + x];
                    }
                    out[y * W + x] = s / k;
                }
            }
            out
        };

        // Local detail proxy on the reference, as the harness computes it.
        let detail_of = |v: &[f32]| -> Vec<f32> {
            let mut d = vec![0.0f32; n];
            for y in 1..W - 1 {
                for x in 1..W - 1 {
                    let gx = v[y * W + x + 1] - v[y * W + x - 1];
                    let gy = v[(y + 1) * W + x] - v[(y - 1) * W + x];
                    d[y * W + x] = gx.abs() + gy.abs();
                }
            }
            d
        };

        // The shipped mask: scattered per-pixel threshold, smoothest 40%.
        let mut shipped = vec![false; n];
        let cnt = low_detail_mask(&detail_of(&sharp), &sharp, 0.40, 0.20, &mut shipped);
        assert!(cnt > 0, "mask must select something");

        // A compact block of the same area, placed in the calmest quadrant
        // (bottom-left is free of disc and bar).
        let side = (cnt as f64).sqrt() as usize;
        let (ox, oy) = (8usize, W - side - 8);
        let mut compact = vec![false; n];
        for y in oy..oy + side {
            for x in ox..ox + side {
                compact[y * W + x] = true;
            }
        }

        let mean_over = |v: &[f32], m: &[bool]| -> f64 {
            let mut f = Flux::new();
            f.fold_covered(v, m, f32::INFINITY);
            f.mean().unwrap()
        };
        let median_over = |v: &[f32], m: &[bool]| -> f64 {
            let mut s: Vec<f32> = v
                .iter()
                .zip(m)
                .filter(|&(_, &c)| c)
                .map(|(&x, _)| x)
                .collect();
            s.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap());
            f64::from(s[s.len() / 2])
        };

        // A third region: the shipped mask eroded away from its own perimeter.
        // This keeps the low-detail selectivity and removes the boundary that
        // blur carries flux across.
        let mut eroded = vec![false; n];
        let n_erode = erode_mask(&shipped, W, 16, &mut eroded);

        let (r_ship, r_comp) = (mean_over(&sharp, &shipped), mean_over(&sharp, &compact));
        let r_ero = mean_over(&sharp, &eroded);
        let r_med = median_over(&sharp, &shipped);
        let total: f64 = sharp.iter().map(|&x| f64::from(x)).sum();

        let (mut pk_ship, mut pk_comp, mut pk_med) = (0.0f64, 0.0f64, 0.0f64);
        let (mut pk_ero, mut pk_cmed) = (0.0f64, 0.0f64);
        let c_med = median_over(&sharp, &compact);
        for rad in [2usize, 4, 8, 12, 16] {
            let b = blur(&sharp, rad);
            // The null is only valid if the blur really conserved flux.
            let tb: f64 = b.iter().map(|&x| f64::from(x)).sum();
            assert!(
                ((tb - total) / total).abs() < 1e-4,
                "blur must conserve flux, drift {}",
                (tb - total) / total
            );
            pk_ship = pk_ship.max((r_ship / mean_over(&b, &shipped) - 1.0).abs());
            pk_comp = pk_comp.max((r_comp / mean_over(&b, &compact) - 1.0).abs());
            pk_med = pk_med.max((r_med / median_over(&b, &shipped) - 1.0).abs());
            pk_ero = pk_ero.max((r_ero / mean_over(&b, &eroded) - 1.0).abs());
            pk_cmed = pk_cmed.max((c_med / median_over(&b, &compact) - 1.0).abs());
        }

        println!(
            "PR-16 defocus null (peak spurious gain over a blur sweep)\n  \
             shipped scattered mask  {:>8.4}%   ({} px)\n  \
             eroded by 16 px         {:>8.4}%   ({} px)\n  \
             compact equal-area block{:>8.4}%   ({} px)\n  \
             shipped / compact = {:.1}x     eroded / compact = {:.2}x\n  \
             statistic effect on the COMPACT block: median {:.4}% vs mean \
             {:.4}%  = {:.1}x",
            pk_ship * 100.0,
            cnt,
            pk_ero * 100.0,
            n_erode,
            pk_comp * 100.0,
            side * side,
            pk_ship / pk_comp,
            pk_ero / pk_comp,
            pk_cmed * 100.0,
            pk_comp * 100.0,
            pk_cmed / pk_comp
        );

        // Power check, measured on the compact block where the perimeter leak
        // is not confounding it: the null must reproduce M87's statistic
        // effect (median much worse than mean) or it has no power.
        assert!(
            pk_cmed > 10.0 * pk_comp,
            "null lacks power: median {pk_cmed} vs mean {pk_comp}"
        );
        // PR-16 proper. Recorded as the measurement it is; see report S13.
        assert!(
            pk_ship > 2.0 * pk_comp,
            "PR-16 recorded the shipped mask as leaking; if this now fails the \
             mask has been fixed and the report must be updated"
        );
    }

    fn flux_of(mean: f64, count: u64) -> Flux {
        let mut f = Flux::new();
        f.sum = mean * count as f64;
        f.count = count;
        f
    }

    // -- the estimator ------------------------------------------------------

    #[test]
    fn the_low_detail_mask_needs_both_conditions_not_either() {
        // Four pixels: sharp+bright, sharp+dark, smooth+bright, smooth+dark.
        // Only smooth+bright is background. A one-condition mask would admit
        // the smooth *dark* pixel, which on a real deck is the subject's own
        // unlit body and is scene structure, not a backdrop.
        let detail = [9.0f32, 9.0, 1.0, 1.0];
        let luma = [800.0f32, 100.0, 900.0, 90.0];
        let mut mask = [false; 4];
        let n = low_detail_mask(&detail, &luma, 0.25, 0.5, &mut mask);
        assert_eq!(n, 1, "exactly one pixel is both smooth and bright");
        assert_eq!(mask, [false, false, true, false]);
    }

    #[test]
    fn the_mask_ignores_uncovered_pixels_when_it_picks_its_thresholds() {
        // The warp writes NaN outside coverage. If those sorted into the
        // quantile they would drag every threshold by the size of the border,
        // and the region would drift with the amount of border each frame has.
        let detail = [1.0f32, 2.0, 3.0, 4.0, f32::NAN, f32::NAN];
        let luma = [10.0f32, 20.0, 30.0, 40.0, f32::NAN, f32::NAN];
        let mut mask = [false; 6];
        low_detail_mask(&detail, &luma, 0.5, 0.5, &mut mask);
        assert_eq!(
            mask,
            [false, false, true, false, false, false],
            "thresholds are the finite quantiles: detail <= 3 and luma >= 30"
        );
        assert!(
            !mask[4] && !mask[5],
            "a NaN pixel is never admitted whatever the thresholds"
        );
    }

    #[test]
    fn the_whole_frame_and_the_low_detail_gain_are_different_numbers() {
        // The Phase D result in miniature, and the reason the module folds over
        // a region. Frame 1 is genuinely 10% brighter everywhere; it is also
        // more defocused, which moves flux out of the sharp half and into the
        // smooth half. Whole-frame flux sees only the 10%; the smooth region
        // sees the 10% plus the redistribution, and it is the smooth region the
        // render's background is elected from.
        let sharp0 = 4000.0f64;
        let smooth0 = 1000.0f64;
        let moved = 400.0f64; // blur moves this out of sharp and into smooth
        let bright = 1.10f64;
        let sharp1 = (sharp0 - moved) * bright;
        let smooth1 = (smooth0 + moved) * bright;

        let whole0 = flux_of((sharp0 + smooth0) / 2.0, 2);
        let whole1 = flux_of((sharp1 + smooth1) / 2.0, 2);
        let region0 = flux_of(smooth0, 1);
        let region1 = flux_of(smooth1, 1);

        let mw = PhotometricMap::from_flux(&[whole0, whole1], 0).expect("whole-frame map");
        let mr = PhotometricMap::from_flux(&[region0, region1], 0).expect("region map");

        // Whole-frame flux is blind to redistribution, so it recovers the true
        // photometric gain exactly.
        assert!(
            (mw.gain(1).unwrap() - (1.0 / 1.10)).abs() < 1e-5,
            "whole-frame gain {} should be 1/1.10",
            mw.gain(1).unwrap()
        );
        // The region's own level moved by much more than 10%, so the gain the
        // background actually needs is a different number.
        assert!(
            (mr.gain(1).unwrap() - mw.gain(1).unwrap()).abs() > 0.2,
            "region gain {} and whole-frame gain {} must differ materially",
            mr.gain(1).unwrap(),
            mw.gain(1).unwrap()
        );
    }

    #[test]
    fn a_planted_gain_ladder_is_recovered_exactly() {
        // The frames differ by a known multiplicative ladder; the estimator has
        // to return its inverse, normalised to the reference.
        let truth: Vec<f64> = (0..9).map(|k| 1.0 + 0.05 * f64::from(k)).collect();
        let flux: Vec<Flux> = truth.iter().map(|&g| flux_of(1000.0 * g, 1 << 20)).collect();
        let map = PhotometricMap::from_flux(&flux, 4).unwrap();
        for k in 0..9 {
            let want = (truth[4] / truth[k]) as f32;
            let got = map.gain(k).unwrap();
            assert!(
                (got - want).abs() < 1e-6,
                "frame {k}: want {want}, got {got}"
            );
        }
        assert_eq!(map.refused_count(), 0);
        assert_eq!(map.source(), GainSource::MeasuredFlux);
    }

    #[test]
    fn the_reference_frames_gain_is_exactly_one() {
        let flux: Vec<Flux> = (0..7)
            .map(|k| flux_of(731.0 + 13.0 * f64::from(k), 4096))
            .collect();
        for r in 0..7 {
            let map = PhotometricMap::from_flux(&flux, r).unwrap();
            assert_eq!(
                map.gain(r).unwrap().to_bits(),
                1.0f32.to_bits(),
                "reference {r} did not get a bit-exact unit gain"
            );
        }
    }

    /// **The property the whole design rests on.** Blur conserves flux, so a
    /// frame that is only more defocused than the reference must be assigned a
    /// gain of one. If this failed, the correction would be spending itself on
    /// real image content.
    #[test]
    fn defocus_alone_does_not_move_the_estimated_gain() {
        let w = 256usize;
        let mut sharp = vec![0.0f32; w * w];
        // A structured scene: bright disc on a dim field, plus a gradient, so
        // that blur genuinely moves light around rather than doing nothing.
        for y in 0..w {
            for x in 0..w {
                let (dx, dy) = (x as f32 - 96.0, y as f32 - 140.0);
                let disc = if dx * dx + dy * dy < 45.0 * 45.0 {
                    9000.0
                } else {
                    0.0
                };
                sharp[y * w + x] = 300.0 + 2.0 * x as f32 + disc;
            }
        }
        // Separable box blur with wrap-around, which conserves the sum exactly.
        let blur = |src: &[f32], rad: usize| -> Vec<f32> {
            let mut mid = vec![0.0f32; w * w];
            let n = (2 * rad + 1) as f32;
            for y in 0..w {
                for x in 0..w {
                    let mut s = 0.0;
                    for d in 0..=2 * rad {
                        s += src[y * w + (x + w + d - rad) % w];
                    }
                    mid[y * w + x] = s / n;
                }
            }
            let mut out = vec![0.0f32; w * w];
            for y in 0..w {
                for x in 0..w {
                    let mut s = 0.0;
                    for d in 0..=2 * rad {
                        s += mid[((y + w + d - rad) % w) * w + x];
                    }
                    out[y * w + x] = s / n;
                }
            }
            out
        };

        let mut fl = Vec::new();
        for rad in [0usize, 3, 9, 21] {
            let data = if rad == 0 { sharp.clone() } else { blur(&sharp, rad) };
            let mut f = Flux::new();
            f.fold_plane(&data, 1e9);
            fl.push(f);
        }
        let map = PhotometricMap::from_flux(&fl, 0).unwrap();
        for (k, g) in map.gains().iter().enumerate() {
            assert!(
                (g - 1.0).abs() < 2e-4,
                "blur radius index {k} moved the gain to {g}; the estimator is \
                 not blind to redistribution"
            );
        }
        // And the control: a real gain on top of the blur IS seen.
        let mut planted = blur(&sharp, 9);
        apply_to_plane(&mut planted, 1.20);
        let mut f = Flux::new();
        f.fold_plane(&planted, 1e9);
        let map2 = PhotometricMap::from_flux(&[fl[0], f], 0).unwrap();
        assert!(
            (map2.gain(1).unwrap() - 1.0 / 1.20).abs() < 1e-3,
            "a planted 1.20 gain was not recovered: got {}",
            map2.gain(1).unwrap()
        );
    }

    #[test]
    fn a_clipped_frame_is_refused_rather_than_scaled() {
        let mut good = Flux::new();
        good.fold_plane(&[1000.0; 1024], 14848.0);
        let mut clipped = Flux::new();
        let mut d = vec![900.0f32; 1024];
        for v in d.iter_mut().take(64) {
            *v = 14848.0;
        }
        clipped.fold_plane(&d, 14848.0);
        let map = PhotometricMap::from_flux(&[good, clipped], 0).unwrap();
        assert_eq!(map.gain(1).unwrap(), 1.0);
        assert!(map.refusal(1).unwrap().contains("clipped"));
        assert_eq!(map.refused_count(), 1);
    }

    #[test]
    fn an_implausible_gain_is_refused_rather_than_applied() {
        let a = flux_of(1000.0, 4096);
        let b = flux_of(10.0, 4096); // would demand a gain of 100
        let map = PhotometricMap::from_flux(&[a, b], 0).unwrap();
        assert_eq!(map.gain(1).unwrap(), 1.0);
        assert!(map.refusal(1).unwrap().contains("outside the plausible band"));
    }

    #[test]
    fn coverage_is_respected_so_the_warp_border_cannot_enter_the_estimate() {
        let data = vec![100.0f32, 100.0, 100.0, 0.0, 0.0, 0.0];
        let cover = vec![true, true, true, false, false, false];
        let mut all = Flux::new();
        all.fold_plane(&data, 1e9);
        let mut cov = Flux::new();
        cov.fold_covered(&data, &cover, 1e9);
        assert_eq!(all.mean().unwrap(), 50.0);
        assert_eq!(cov.mean().unwrap(), 100.0);
        assert_eq!(cov.count(), 3);
    }

    #[test]
    fn empty_and_out_of_range_are_errors_not_silent_defaults() {
        assert_eq!(
            PhotometricMap::from_flux(&[], 0).unwrap_err(),
            PhotometricError::Empty
        );
        let f = vec![flux_of(1.0, 8); 3];
        assert_eq!(
            PhotometricMap::from_flux(&f, 3).unwrap_err(),
            PhotometricError::BadReference {
                reference: 3,
                n: 3
            }
        );
        let map = PhotometricMap::from_flux(&f, 0).unwrap();
        assert_eq!(
            map.gain(3).unwrap_err(),
            PhotometricError::OutOfRange { index: 3, n: 3 }
        );
        assert_eq!(
            PhotometricMap::from_flux(&[Flux::new()], 0).unwrap_err(),
            PhotometricError::NoSamples { index: 0 }
        );
    }

    #[test]
    fn span_is_the_worst_step_the_map_can_remove() {
        let flux: Vec<Flux> = [1.0, 1.1, 0.9, 1.05]
            .iter()
            .map(|&g| flux_of(1000.0 * g, 4096))
            .collect();
        let map = PhotometricMap::from_flux(&flux, 0).unwrap();
        assert!((map.span() - 1.1 / 0.9).abs() < 1e-5);
        assert_eq!(PhotometricMap::unity(4, 0).unwrap().span(), 1.0);
    }

    // -- application --------------------------------------------------------

    #[test]
    fn a_unit_gain_is_a_bit_exact_no_op_on_the_container() {
        let mut d: Vec<u16> = (0..4096u16).map(|v| v.wrapping_mul(3)).collect();
        let before = d.clone();
        apply_to_u16(&mut d, 512.0, 15360.0, 1.0);
        assert_eq!(d, before);
        let mut p: Vec<f32> = (0..1024).map(|i| i as f32 * 0.37 - 11.0).collect();
        let pb = p.clone();
        apply_to_plane(&mut p, 1.0);
        assert_eq!(
            p.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            pb.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
        );
    }

    #[test]
    fn scaling_is_about_black_and_saturates_at_white() {
        let mut d = vec![512u16, 1024, 15360, 16000];
        apply_to_u16(&mut d, 512.0, 15360.0, 2.0);
        assert_eq!(d[0], 512, "black must map to black exactly");
        assert_eq!(d[1], 1536, "512 above black must double to 1024 above black");
        assert_eq!(d[2], 15360, "white must clamp at white, not wrap");
        assert_eq!(d[3], 15360, "above white must clamp at white");
    }

    #[test]
    fn scaling_down_then_up_returns_the_signal_within_rounding() {
        let orig: Vec<u16> = (512..15360u16).step_by(37).collect();
        let mut d = orig.clone();
        apply_to_u16(&mut d, 512.0, 15360.0, 0.8);
        apply_to_u16(&mut d, 512.0, 15360.0, 1.25);
        for (a, b) in orig.iter().zip(d.iter()) {
            assert!(
                (i32::from(*a) - i32::from(*b)).abs() <= 1,
                "round trip moved {a} to {b}"
            );
        }
    }

    // -- noise propagation, the part that is silent when wrong ---------------

    /// `Var(c*S)` must equal `c^2 * Var(S)` under the scaled model, at every
    /// level and for every gain. This is the identity the gate depends on.
    #[test]
    fn the_scaled_model_reproduces_the_true_variance_of_scaled_data() {
        let p = plane(0.229, 1.47);
        for &c in &[0.5f32, 0.8, 0.95, 1.0, 1.2, 1.7, 2.0] {
            let s = scale_plane_noise(p, c);
            for step in 0..=64 {
                let sig = step as f32 * 232.0;
                let truth = c * c * p.variance(sig);
                let got = s.variance(sig * c);
                let rel = (got - truth).abs() / truth.max(1e-6);
                assert!(
                    rel < 1e-5,
                    "gain {c}, signal {sig}: model {got}, truth {truth}, rel {rel}"
                );
            }
        }
    }

    #[test]
    fn scaling_the_data_and_the_model_together_leaves_contrast_over_sigma_invariant() {
        // The consequence that governs the *election*, not just the tint.
        //
        // strehl's focus response is a contrast divided by a sigma. Scaling a
        // frame by `c` scales the contrast by `c`, and `scale_plane_noise`
        // scales the sigma by `c` too, so the ratio is unchanged and the frame's
        // focus score is exactly what it was. A photometric correction applied
        // with correct noise propagation is therefore **election-neutral by
        // construction**: it changes what the winning frame *looks like*, not
        // which frame wins.
        //
        // Measured consequence, `phaseE-*.log`: over 299 frames of real data the
        // per-frame correction re-elects 34 and 22 pixels out of 8.2 million.
        // Omitting the propagation re-elects 35 449 and 60 867 — three orders of
        // magnitude more — from a gain carrying no per-frame information at all.
        let p = plane(0.229, 1.47);
        for &c in &[0.5f32, 0.8, 0.95, 1.0, 1.2, 1.7, 2.0] {
            let s = scale_plane_noise(p, c);
            for step in 1..=64 {
                let sig = step as f32 * 232.0;
                let before = sig / p.variance(sig).sqrt();
                let after = (sig * c) / s.variance(sig * c).sqrt();
                let rel = (after - before).abs() / before;
                assert!(
                    rel < 1e-5,
                    "gain {c}, signal {sig}: snr {before} -> {after}, rel {rel}"
                );
            }
        }
    }

    #[test]
    fn the_read_floor_scales_with_the_data_and_the_electrons_do_not() {
        // The neighbouring rule in profile::Corrections is the opposite one and
        // this asserts the difference on purpose: there the data is unchanged
        // and the floor is preserved; here the data is scaled and the floor
        // must scale with it.
        let p = plane(0.229, 1.47);
        for &c in &[0.6f32, 1.0, 1.9] {
            let s = scale_plane_noise(p, c);
            assert!((s.read_floor_dn() - c * p.read_floor_dn()).abs() < 1e-4);
            assert_eq!(s.read_noise_e, p.read_noise_e);
            assert!((s.gain_dn_per_e - c * p.gain_dn_per_e).abs() < 1e-6);
        }
    }

    #[test]
    fn a_unit_gain_leaves_the_noise_model_bit_identical() {
        let p = plane(0.229, 1.47);
        let s = scale_plane_noise(p, 1.0);
        assert_eq!(s.gain_dn_per_e.to_bits(), p.gain_dn_per_e.to_bits());
        assert_eq!(s.read_noise_e.to_bits(), p.read_noise_e.to_bits());
        assert_eq!(s.levels.black.to_bits(), p.levels.black.to_bits());
        assert_eq!(s.levels.white.to_bits(), p.levels.white.to_bits());
        for step in 0..=32 {
            let sig = step as f32 * 464.0;
            assert_eq!(s.variance(sig).to_bits(), p.variance(sig).to_bits());
        }
    }

    #[test]
    fn levels_scale_about_black_so_white_still_means_saturated() {
        let p = plane(0.229, 1.47);
        let s = scale_plane_noise(p, 1.5);
        assert_eq!(s.levels.black, 512.0);
        assert!((s.levels.white - (512.0 + 1.5 * 14848.0)).abs() < 1e-3);
        assert!((s.levels.range() - 1.5 * p.levels.range()).abs() < 1e-3);
    }

    #[test]
    fn the_model_lifts_to_four_planes_and_keeps_iso_provenance_and_prnu() {
        use crate::noise::Prnu;
        let m = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile)
            .with_prnu(Prnu::A7C2_MEASURED);
        let s = scale_noise_model(&m, 1.3);
        assert_eq!(s.iso, 100.0);
        assert_eq!(s.provenance, Provenance::Profile);
        assert_eq!(s.prnu(), Some(Prnu::A7C2_MEASURED));
        for p in CfaPlane::ALL {
            assert!((s.plane(p).gain_dn_per_e - 1.3 * 0.229).abs() < 1e-6);
        }
        // PRNU is a fraction of signal, so it scales with everything else and
        // kappa itself is unchanged.
        let sig = 8000.0f32;
        let truth = 1.3 * 1.3 * m.variance_with_fixed_pattern(CfaPlane::G1, sig);
        let got = s.variance_with_fixed_pattern(CfaPlane::G1, sig * 1.3);
        assert!((got - truth).abs() / truth < 1e-5, "got {got}, truth {truth}");
        // And a model with no PRNU attached does not acquire one.
        let bare = NoiseModel::new([plane(0.229, 1.47); 4], 100.0, Provenance::Profile);
        assert!(scale_noise_model(&bare, 1.3).prnu().is_none());
    }

    /// The failure this module exists to prevent, quantified. A merge that
    /// scales frames and forgets the model believes the noise is smaller than
    /// it is, by between `sqrt(c)` and `c`.
    #[test]
    fn forgetting_the_model_understates_sigma_between_sqrt_c_and_c() {
        let p = plane(0.229, 1.47);
        for &c in &[1.1f32, 1.2, 1.5, 2.0] {
            // Read-dominated: signal at zero, where the floor is everything.
            let dark = unscaled_sigma_ratio(p, c, 0.0);
            assert!(
                (dark - c).abs() < 1e-4,
                "gain {c}: dark ratio {dark}, expected {c}"
            );
            // Photon-dominated: a bright level, where shot noise is everything.
            let bright = unscaled_sigma_ratio(p, c, 14000.0);
            assert!(
                (bright - c.sqrt()).abs() < 0.01,
                "gain {c}: bright ratio {bright}, expected about {}",
                c.sqrt()
            );
            // Never between the two bounds the wrong way round.
            assert!(bright <= dark + 1e-6 && bright >= 1.0);
        }
        // Scaling down over-states sigma instead, and the same bounds hold
        // mirrored, so a caller cannot assume the error is one-signed.
        assert!(unscaled_sigma_ratio(p, 0.8, 0.0) < 1.0);
    }

    /// On the measured spans M99 reports, how badly is the gate mis-calibrated
    /// if the model is not told? This pins the number the report quotes.
    #[test]
    fn the_measured_spans_mis_calibrate_the_gate_by_a_reportable_amount() {
        let p = plane(0.229, 1.47);
        // lavendar-cpl: measured per-frame gains spanned 0.8546 to 1.1699.
        let worst = unscaled_sigma_ratio(p, 1.1699, 0.0);
        assert!(
            (worst - 1.1699).abs() < 1e-3,
            "worst-case dark mis-calibration was {worst}"
        );
        let mid = unscaled_sigma_ratio(p, 1.1699, 2000.0);
        assert!(
            mid > 1.05 && mid < 1.17,
            "mid-level mis-calibration {mid} left the expected band"
        );
    }
}
