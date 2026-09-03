//! `strehl merge` — the estimation merge on real frames.
//!
//! This is the thing the project exists to build, wired to data. Where
//! `strehl stack` selects one frame per pixel (and is therefore the defect),
//! this regularises the focus field, elects a winner from the regularised
//! field, and then **averages every frame the calibrated noise model cannot
//! distinguish from that winner**.
//!
//! # Why two passes over the frames
//!
//! The gate compares each frame's regularised response against the winner's,
//! and the winner is not known until every frame has been seen. A single-pass
//! fold would have to carry per-pixel state that grows with the acceptance set.
//! Decode is 0.91 s warm (fact 33), so a second pass is the cheaper of the two
//! and it keeps peak memory O(workers). Pass two recomputes each frame's focus
//! field rather than caching it; caching would be O(frames) planes.
//!
//! # Why the whole gate sweep runs in one invocation
//!
//! The gate threshold is the merge's one free parameter and it is deliberately
//! unmeasured (question 90). Its calibration target is fact 212's `nwide = 3`.
//! Decode dominates pass two, so folding the same decoded frame into several
//! `Estimator`s at different thresholds costs almost nothing beyond the extra
//! accumulator memory — one run yields the whole calibration curve instead of
//! one point per decode budget. The worker plan is told about the accumulator
//! count so the budget still binds.
//!
//! # What is measured here
//!
//! Two acceptance invariants, and they are a **pair**. Fact 19 measured a plain
//! mean at 0.534x the single-frame noise; fact 24 measured that the same plain
//! mean collapses detail-region gradient by 58%. Either number alone can be won
//! trivially by a merge that is wrong in the other direction, so the report
//! prints them together and neither is a result on its own.

use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use strehl_core::photometric::{self, Flux, PhotometricMap, PhotometricMode};
use strehl_core::align::Resampler;
use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};
use strehl_core::color::{self, AppliedExposure, Exposure};
use strehl_core::edgeaware::{self, BimodalStats, LayerSupport};
use strehl_core::flat_ratio::{self, FrameFlat};
use strehl_core::focus::FocusField;use strehl_core::merge::{
    Estimator, FOCUS_NOISE_SD, FocusStats, Gate, REGULARISER_RADIUS, REGULARISER_WIDTH, regularise,
    regularise_at, regularise_guided, regularise_layered,
};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;
use strehl_core::pyramid::{
    BandMerge, BaseBand, FrameWorkspace, MergeConfig, SelectMode, Workspace, level_sizes,
    luma_variance,
};
use strehl_core::split::{self, Crossing, SplitAnalysis};
use strehl_core::stack::{DEFAULT_SPECKLE_TOLERANCE as SPECKLE_TOLERANCE, speckle_fraction};
use strehl_core::through_focus::{
    ConfidenceVector, FINE_FOCUS_NOISE_SD, FLAG_BIMODAL, FLAG_BRACKET_BOUNDARY,
    FLAG_SCALE_DISAGREEMENT, PEAK_SEPARATION, STATS_RADIUS, ThroughFocus, do_not_trust_mask,
    shuffled_indices,
};
use strehl_core::warpmap::{FrameWarp, StackIdentity, WarpMap};
use strehl_core::{CfaPlane, Error};
use strehl_raw::Frame;

use crate::align_cmd::{self, WarpScratch};
use crate::image_out;

pub(crate) mod dump;
pub(crate) mod gatefloor;
pub(crate) mod halo;
use crate::stack::{
    MEMORY_BUDGET_BYTES, Roi, flat_roi_stats, mean_and_sigma, provenance_line, report_hp_reference,
    roi_green, srgb_encode,
};

pub struct MergeOptions {
    pub dir: PathBuf,
    pub out: Option<PathBuf>,
    pub limit: Option<usize>,
    /// Apply the sRGB transfer curve **and** the camera's colour matrix.
    /// For looking at, NOT for measuring.
    pub srgb: bool,
    /// Which colour space the output should land in, resolved from `--srgb` /
    /// `--linear-srgb` in `main.rs` so that the two flags cannot disagree.
    ///
    /// **This is the conduit for `--linear-srgb` and nothing reads it yet.**
    /// It is deliberately additive: it exists so the flag is parsed, validated
    /// and carried to this struct without any colour decision being taken
    /// inside the merge code. [`image_out::OutputSpace`] answers the two
    /// questions the write path needs -- `wants_matrix()` and
    /// `applies_curve()` -- which before this were welded together as a bare
    /// `if srgb`, and that weld is why there was no way to ask for a stated
    /// colorimetric space that is still linear.
    ///
    /// `srgb` above is retained and still authoritative for every existing
    /// call site, so this field changes no behaviour until it is read.
    pub space: image_out::OutputSpace,
    /// Emit at full sensor resolution, demosaiced, rather than binned 2x2.
    ///
    /// Interpolated output. Legitimate to look at and to measure *colour* on;
    /// not legitimate to measure *resolution* on, because some of the detail
    /// in it was inferred rather than recorded.
    pub demosaic: bool,
    /// Explicit exposure for the viewing render, in stops. Requires `srgb`.
    ///
    /// `0.0` is **no exposure at all**, not "a gain of one": it resolves to
    /// [`Exposure::None`] and the writer's arithmetic is then exactly what it
    /// was before M100 existed.
    pub exposure: f32,
    /// Choose the exposure from the merged image instead, and print the choice.
    /// Requires `srgb`, and refuses to combine with a non-zero `exposure`.
    pub auto_exposure: bool,
    /// One or more gate thresholds, in units of the combined focus noise. Every
    /// one is folded in the same pass two.
    pub gates: Vec<f32>,
    /// Registered id of the focus operator to elect on, or `None` for the
    /// shipped one.
    ///
    /// `None` and `Some("tenengrad-w13")` are NOT the same run and must not be
    /// collapsed into one. `None` takes `FOCUS_NOISE_SD` -- the compiled-in
    /// 0.015214 the byte-freezes were baselined against -- while any `Some`
    /// takes the scale the host MEASURES at registration, which for that same
    /// operator is 0.0152113. The two differ in the fourth significant figure,
    /// and a gate is a multiplier on exactly that number.
    pub focus: Option<String>,
    pub flat_roi: Option<Roi>,
    pub detail_roi: Option<Roi>,
    /// Also write the **election map**: the per-pixel index of the frame that
    /// won pass one, as a single-channel 16-bit TIFF. Debug output; `None`
    /// costs nothing and never touches the merged image.
    ///
    /// See [`write_election_map`] for the grid and the index convention.
    pub index_map: Option<PathBuf>,
    /// Also write the **n_eff map**: the per-pixel count of frames averaged
    /// into that pixel, as a single-channel 16-bit TIFF. Debug output; `None`
    /// costs nothing and never touches the merged image.
    ///
    /// See [`write_n_eff_map`] for the grid and the value convention.
    pub n_eff_map: Option<PathBuf>,
    /// Also write the **confidence map**: how far the merged output sits from
    /// the nearest aligned observation, per pixel, in milli-sigma of the
    /// calibrated noise. Debug output; `None` costs nothing and never touches
    /// the merged image, but unlike the two maps above it is not free — it
    /// costs a second decode and warp of every frame.
    ///
    /// PYRAMID BACKEND ONLY, which is the point: `--n-eff-map` and
    /// `--index-map` are both refused there, so before this the default merge
    /// emitted an image and no per-pixel evidence of any kind.
    ///
    /// See [`write_confidence_map`] for the grid, the value convention and the
    /// polarity, which is the opposite of `n_eff`'s.
    pub confidence_map: Option<PathBuf>,
    /// Off-by-default same-pass odd/even diagnostic product directory.
    ///
    /// The main accumulator remains first and unchanged; each half gets a
    /// separate green-luma `BandMerge`, so its data-dependent weights are
    /// re-derived rather than inherited from the full stack.
    pub split_out: Option<PathBuf>,
    /// Fit and apply a per-frame affine photometric gain. **Default on**
    /// since V-TONE; it was opt-in from M99 until then.
    ///
    /// M24 measured real per-frame drift that EXIF does not predict — 0.91%
    /// peak-to-peak on `109MSDCF`, 11.70% on `coffee-bean` — so a gated
    /// average without this term is reading an exposure change as a signal
    /// change.
    ///
    /// Three-valued since M125. [`PhotometricMode::Auto`] decides per stack
    /// from that same measured drift. It is **not** the default and should not
    /// be made one: `AUTO_FRAMES_DOMAIN` is `33..=100`, so `auto` abstains
    /// with code U1 on every stack this rig actually shoots (205 and 299
    /// frames), which makes it identical to `Off` in practice.
    ///
    /// M122's KEEP-OFF no longer stands: see [`resolve_photometric_mode`] for
    /// the partition that retired it, and for the two caveats that travel with
    /// it. Also settable via `STREHL_PHOTOMETRIC=off|on|auto`.
    pub photometric: PhotometricMode,
    /// Which channel supplied [`MergeOptions::photometric`] -- flag, env, or the
    /// compiled-in default -- so the run banner can report the mode without
    /// claiming a request that nobody made.
    pub photometric_source: SettingSource,
    /// Solve the ladder for the gate that achieves this mean `n_eff`.
    ///
    /// **This, not `gates`, is the parameter the project intends to ship.**
    /// A fixed threshold is not a calibration. M52 re-measured this across all
    /// seven stacks against the current pipeline: at gate 2.0 mean `n_eff` runs
    /// **1.177 (`foam`) to 14.386 (`coffee-bean`), a 12.22x spread**, and the
    /// gate needed to reach `n_eff = 3` runs **0.7618 to 21.9934, a factor of
    /// 28.9**. `foam` cannot reach `n_eff = 3` anywhere on the shipped 0.5-4.0
    /// ladder. A target `n_eff` transfers where a gate does not, and it is the
    /// quantity fact 212 calibrated.
    ///
    /// Fact 324 published "2.26 to 7.42" and "1.1 to 2.9" from a five-stack
    /// sweep taken before commit `2a4f5c5` corrected the ISO-50 gain floor. Its
    /// conclusion held and its magnitude was understated by 3.7x. The numbers
    /// above are M52's (`docs/research/M52-gate-cluster-verified.md`), whose
    /// independent Python merge agrees with the shipped binary to <= 0.09% on
    /// all seven stacks.
    pub target_n_eff: Option<f64>,
    /// Gather per-pixel through-focus sufficient statistics during pass two.
    ///
    /// Opt-in because it is not free, and **two different per-worker figures
    /// are in circulation for it**, so this says which is which:
    ///
    /// * **60 B/px = 494 MB** is [`ThroughFocus`] *alone*, the payload of the
    ///   struct itself. It is the right number for "what does the gathered
    ///   statistic cost", and the wrong one for "what does this flag cost".
    /// * **64 B/px = 527 MB** is what setting this field actually costs, and
    ///   is what a run reports, because it also forces a `FINE_FIELD_PER_PX`
    ///   4 B/px fine focus plane into every pass-two worker. This is the
    ///   number a user deciding whether to pass `--stats` wants.
    ///
    /// Neither is stale; they are two quantities under one label, which is the
    /// failure mode section 5 of `SYNTHESIS.md` calls the corpus's worst. The
    /// 527 figure is `px * (FINE_FIELD_PER_PX + gathers * bytes_per_pixel())`
    /// at `gathers = 1`; `stats_placebo` raises `gathers` to 2 and the total
    /// to 124 B/px, so 527 MB is the floor for this flag, not a constant.
    ///
    /// Either way it reduces the worker count the memory budget licenses. With
    /// it off, the merge path's memory is exactly what M37/M38 measured.
    pub stats: bool,
    /// Also gather a frame-permutation placebo alongside the statistics.
    ///
    /// Doubles the statistics memory. Without it the bimodality channel has no
    /// null on this stack and its absolute value means nothing.
    pub stats_placebo: bool,
    /// Tail fraction per channel for the "do not trust" union mask. M34 used
    /// 0.05 and measured a 14.278% union.
    pub confidence_tail: f64,
    /// Interpolator each frame is gathered with when the merge registers.
    ///
    /// **Default [`align_cmd::DEFAULT_RESAMPLER_NAME`], which is the literal
    /// `merge_config` used to return**, so a merge that does not pass
    /// `--resampler` is byte-identical to every merge rendered before this
    /// field existed. Whether the default should move is pre-registered in
    /// `docs/research/ORCH-kernel-decision.md` and is not this field's decision.
    ///
    /// It reaches pixels only through the **solve** path: with
    /// [`WARPMAP_ENV`] set the named sidecar carries its own resampler and wins,
    /// which [`alignment_for`] says out loud rather than silently ignoring the
    /// flag.
    pub resampler: Resampler,
    /// Which merge actually produces the pixels.
    ///
    /// Resolved in `main.rs` from `--merge` / [`MERGE_BACKEND_ENV`] so that an
    /// unrecognised spelling is one error in one place, exactly as
    /// [`resolve_photometric_mode`] does it.
    pub backend: MergeBackend,
    /// What to do about the region only *some* frames cover: shrink the field
    /// of view and upsample (the default), or emit the covered rectangle at
    /// unity scale. See [`align_cmd::CoverMode`].
    ///
    /// Resolved in `main.rs` from `--cover` / [`align_cmd::COVER_ENV`] so that
    /// an unrecognised spelling is one error in one place, and carried here
    /// rather than read from the environment at each of the two call sites --
    /// which is what keeps **both** backends on the same decision. A previous
    /// fix in this file reached one backend and shipped broken in the other.
    pub cover: align_cmd::CoverMode,
    /// Which channel chose [`MergeOptions::cover`], for the banner.
    pub cover_source: SettingSource,
    /// Configuration for [`MergeBackend::Pyramid`]. Ignored, and REFUSED by
    /// `main.rs` rather than ignored silently, under the other backend.
    pub pyramid: MergeConfig,
}

/// Which merge produces the merged pixels.
///
/// Two merges exist in this tree and until now only one of them was reachable
/// from the binary. The Laplacian multi-band merge lived in
/// `crates/strehl-cli/examples/blend-render.rs`, which ships nothing, and is
/// what every good render in the research corpus was made with. This enum is
/// what connects it to `strehl stack`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MergeBackend {
    /// [`strehl_core::pyramid`]: a Laplacian multi-band merge.
    ///
    /// Selection happens per band and per coefficient rather than per pixel, so
    /// a depth boundary is a transition in each band's own frequency rather
    /// than a step in the image, and the coarse bands -- where the eye reads
    /// the "cut-out sticker" rim -- stay gently blended while the fine bands,
    /// where acuity lives, run near winner-take-all.
    ///
    /// Reachable, and **the default**. See [`DEFAULT_MERGE_BACKEND`].
    Pyramid,
    /// [`strehl_core::merge`]: the regularised-winner, noise-gated estimator.
    ///
    /// **What shipped before this flag existed**, and what the older quality
    /// numbers in the corpus were measured on. `--merge estimator` is
    /// byte-identical to what `strehl stack` did before the backend switch
    /// existed, which is why every row in `tests/byte-freeze.rs` names it.
    Estimator,
}

/// The backend `strehl stack` runs when neither `--merge` nor `STREHL_MERGE`
/// names one.
///
/// # This constant is the flip
///
/// Changing it to [`MergeBackend::Pyramid`] moves the shipped merge. It is a
/// named constant rather than a `#[default]` attribute precisely so that the
/// decision has one address and a reviewer can see the whole of it at once.
///
/// It is one line in the source and it is not one line in effect, and the
/// difference is worth stating before someone flips it in a hurry. Both arms
/// are wired, both are reachable, both share one develop path, and the flag,
/// its env twin and the cross-backend refusals are all written against
/// whichever value sits here, so no shipped test breaks -- `tests/byte-freeze.rs`
/// is immune because `Freeze::argv` passes `--merge estimator` explicitly.
/// But eight flags are estimator-only and `main.rs` REFUSES them under
/// `--merge pyramid` rather than ignoring them, so every invocation that
/// passes one without also naming the backend starts failing. Swept over this
/// repository that is 338 call sites in 185 files, of which 189 are executable
/// (144 `.ps1`, 42 `.py`, 3 `.rs`); `--gate` alone accounts for 275. Those
/// failures are loud rather than silent, which is the design, but they are not
/// nothing, and a harness that dies is a measurement that does not happen.
///
/// Prose that moves with this line: the `(DEFAULT)` marker and the "NOT the
/// default yet" paragraph in `main.rs`'s `Stack` help, `--merge`'s own "(the
/// default)", the variant docs above, the two runtime banners at the head of
/// each merge (via [`merge_banner`]), and `scripts/check-defaults.py`'s
/// `STREHL_MERGE` registry entry. All but the last are covered by tests that
/// compare the rendered string against this constant, so flipping the value
/// fails the suite until the words follow. That coupling is deliberate: this
/// project has already shipped a subject line asserting a default that the code
/// did not have, and a stale `(DEFAULT)` in `--help` is the same defect where
/// more people would read it.
///
/// The banners were missing from that list until a binary built with this
/// constant flipped was actually run. It printed `(--merge pyramid; reachable,
/// NOT the default)` while running as the default. Reading the enumeration back
/// would not have caught it, because the enumeration was the thing that was
/// wrong; only executing the flipped build did.
///
/// # Why it is the pyramid
///
/// Because the criterion this line was written against was met, and then the
/// picture agreed with it.
///
/// The condition recorded here was: *"This line moves when a pyramid arm
/// measured at its own default gate passes the acceptance gate -- not on the
/// halo alone, and not on numbers borrowed from a gate the default does not
/// use."* Both halves of that are now satisfied, and the table below is the
/// arm a flip actually ships: stock `MergeConfig::default()`, band gate 2.00,
/// no `--pyramid-gate` anywhere. Measured through ONE binary, both arms
/// camera-linear with `--demosaic`, `STREHL_FIX_CA` and `STREHL_PHOTOMETRIC`
/// explicitly unset, so the arms differ in the merge and nothing else:
///
/// | subject | arm | clip% | acuity | microC | p1 |
/// | --- | --- | --- | --- | --- | --- |
/// | couch-fibers | estimator | 0.0000 | 334.1 | 289.88 | 3068 |
/// | | pyramid | 0.0000 | **373.2** | **339.73** | 3232 |
/// | flower-bud-alone | estimator | 0.0001 | 126.9 | 54.21 | 1028 |
/// | | pyramid | **0.0000** | **223.4** | **117.55** | **1042** |
/// | lavendar | estimator | 0.0000 | 165.9 | 42.83 | 1939 |
/// | | pyramid | 0.0000 | **330.4** | **161.58** | 2462 |
///
/// Those are this render's own numbers, not the ones this doc block used to
/// carry. The earlier table quoted couch-fibers at 290.3/274.76 for the
/// estimator; that was a different render at a band gate this command does not
/// ship, and the reference arm moved with it. Comparing a new treatment against
/// an old control is how a corpus drifts without anyone deciding to move it.
///
/// The clip that blocked this line is gone: **1.4043% -> 0.0000%**, and `p1`
/// no longer collapses (1042 against the estimator's 1028, where it used to
/// read 334). Both were one finding about the black point rather than two --
/// `accept.py`'s clip predicate is `np.any(im == 0, axis=2)`, black only -- and
/// `Hull::InputRange` in `pyramid.rs` addressed it at the source by confining
/// the reconstruction to the hull of its own inputs.
///
/// The second blocker recorded here was that every number on this page had
/// been taken at `--pyramid-gate 4`, a configuration `strehl stack` does not
/// ship. That is no longer true of anything above.
///
/// # The halo, in absolute DN rather than in a ratio
///
/// The owner's standing complaint is a hard white halo tracing the silhouette
/// on dark-subject, bright-ground stacks, and a broad dark aura outside it.
/// Scored through ONE mask and ONE distance transform taken from the estimator
/// arm, so both columns read an identical pixel population
/// (`experiments/BUILD-BLEND/dnlevel.py`):
///
/// | subject | zone | estimator | pyramid |
/// | --- | --- | --- | --- |
/// | flower-bud-alone | aura d=80-200 px, vs own far field | -4739 DN | **-166 DN** |
/// | coffee-bean | aura d=80-200 px, vs own far field | -5629 DN | **-1765 DN** |
///
/// Levels, not errors, and deliberately so. An upper-envelope estimator was
/// measured on this project to carry a **+0.845 sigma bias, upward**, against a
/// defect that is a *darkening*; at sigma_frame ~ 200 DN that is +169 DN, and
/// an estimator with it nulls a veiling error metric arithmetically without
/// improving the photograph. The discriminator is the far field, where no aura
/// reaches: the pyramid's far field is **-113 DN** on flower-bud and **-317
/// DN** on coffee-bean, i.e. very slightly DARKER, while the near-silhouette
/// rows move **+4452 DN** and **+6965 DN**. A bias faking the fix moves both
/// the same way; this moves them in opposite directions, with the local change
/// 14-22x the global one.
///
/// The placebo agrees. `109MSDCF` has no depth separation and therefore no
/// silhouette to blend across, so a merge change should do nothing to it. It
/// does nothing to it: median **+0 DN**, mean **+5 DN**, worst 6x6 tile
/// **32 DN**, against the +4452 DN it moves on a subject that does have a
/// boundary.
///
/// # What is NOT fixed, recorded here because it ships too
///
/// `accept.py` still reads FAIL on `coffee-bean`, on micro-contrast, at 67.2%
/// of the estimator. Two things are true about that number and neither is an
/// excuse. It is inflated: `microC` is a median local standard deviation, the
/// estimator's dark regions carry a blotchy mottle the pyramid does not, and
/// at 1:1 there is no visible detail loss. It is also not empty: `coffee-bean`
/// is the only subject whose interior standard deviation falls, and the only
/// one where the pyramid more than doubles white-rail clipping, 1.17% ->
/// 2.86%. That is the highlight-side twin of the black-point collapse fixed
/// above -- where the inputs reach the rail, the hull permits the rail -- and
/// it is BUILD-BLEND's to fix in `pyramid.rs`.
///
/// The band gate is also not gating where it claims to. `pyramid.rs`'s own
/// `averaged` diagnostic reads `49.1% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0%`: it gates
/// at level 0 and not at all at levels 1-6, because the per-band floor is
/// derived by pushing WHITE noise through the operators while real
/// post-demosaic noise is spatially correlated and carries more coarse-scale
/// energy than that predicts. Backdrop noise is up 1.14-3.87x as a result.
///
/// The flip happens anyway, and the reason is a judgement about which defect
/// disqualifies a print. A merge that renders a subject's edge properly and
/// clips 1.4% of the frame is not better than one that smears the edge; that
/// was the old reasoning and it was right, which is why this line did not move
/// until the clip was fixed. A merge that renders the edge properly and is
/// noisier in one subject's backdrop IS better than one that draws a cut-out
/// sticker rim around every subject with an occlusion boundary, because the
/// rim disqualifies the frame and the noise does not.
pub const DEFAULT_MERGE_BACKEND: MergeBackend = MergeBackend::Pyramid;

impl Default for MergeBackend {
    fn default() -> Self {
        DEFAULT_MERGE_BACKEND
    }
}

impl MergeBackend {
    /// Parse a backend name. **An unrecognised value is an error**, in either
    /// channel, for the same reason `--photometric` refuses one: a merge that
    /// silently fell back to the other merge is indistinguishable, from the
    /// terminal, from one that did what was asked.
    pub fn parse(v: &str) -> Result<Self> {
        match v.trim().to_ascii_lowercase().as_str() {
            "pyramid" | "bands" | "blend" => Ok(Self::Pyramid),
            "estimator" | "merge" | "legacy" => Ok(Self::Estimator),
            other => bail!(
                "unknown merge backend {other:?}; valid values are `estimator` (the default, the \
                 regularised-winner noise-gated merge) and `pyramid` (the Laplacian multi-band \
                 merge)"
            ),
        }
    }

    /// The spelling `--merge` accepts for this backend, and the one the
    /// refusal messages quote back, so a message can never name a value the
    /// parser would reject.
    pub fn name(self) -> &'static str {
        match self {
            Self::Pyramid => "pyramid",
            Self::Estimator => "estimator",
        }
    }

    /// The other backend. Used to name the one a refused flag belongs to.
    pub fn other(self) -> Self {
        match self {
            Self::Pyramid => Self::Estimator,
            Self::Estimator => Self::Pyramid,
        }
    }
}

/// The banner line a merge prints before it runs, with the default claim
/// supplied rather than assumed.
///
/// Split from [`merge_banner`] so that all four strings are reachable from a
/// test without mutating [`DEFAULT_MERGE_BACKEND`]. A test that skipped the
/// branch the constant does not currently select would report a pass for a
/// string nobody had looked at.
fn merge_banner_for(backend: MergeBackend, is_default: bool) -> &'static str {
    match (backend, is_default) {
        (MergeBackend::Estimator, true) => {
            "strehl stack -- regularised winner + noise-gated average (THE DEFAULT PATH, an estimator)"
        }
        (MergeBackend::Estimator, false) => {
            "strehl stack -- regularised winner + noise-gated average (--merge estimator; reachable, NOT the default)"
        }
        (MergeBackend::Pyramid, true) => {
            "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)"
        }
        (MergeBackend::Pyramid, false) => {
            "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; reachable, NOT the default)"
        }
    }
}

/// The banner line for `backend`, with its default claim derived from
/// [`DEFAULT_MERGE_BACKEND`].
///
/// Both banners used to state their role as a literal. That was measured to be
/// wrong: a binary built with the constant flipped to `Pyramid` printed
/// `(--merge pyramid; reachable, NOT the default)` while running as the
/// default, and the estimator's line went on claiming `THE DEFAULT PATH` after
/// it had stopped being one. The `--help` strings are covered by tests in
/// `main.rs`; these two were not, and they are the copy a user actually sees
/// on every run, so they were the worst of the set to leave hardcoded.
pub fn merge_banner(backend: MergeBackend) -> &'static str {
    merge_banner_for(backend, backend == DEFAULT_MERGE_BACKEND)
}

/// Env-var twin of `--merge`, for A/B harnesses that cannot edit argv.
pub const MERGE_BACKEND_ENV: &str = "STREHL_MERGE";

/// Where the merge backend came from, for the run log and for tests.
///
/// The distinction that matters is `Flag`/`Env` (the user STATED a backend)
/// against `Inferred`/`Default` (they did not). Contradicting flags are refused
/// only in the first case, because only there is there a contradiction: if the
/// user never named a backend, a lone `--gate` is not a disagreement with
/// anything, it is the only thing they said about which merge they want.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum MergeSource {
    /// `--merge` on the command line.
    Flag,
    /// [`MERGE_BACKEND_ENV`].
    Env,
    /// Deduced from the flag family the caller used.
    Inferred,
    /// Nobody said anything: [`DEFAULT_MERGE_BACKEND`].
    Default,
}

/// The backend the user STATED and where they stated it, or `None` for neither.
///
/// Split out of the choice so that inference can ask "did they say?" without
/// having to ask "what is the default?" in the same breath -- those are
/// different questions, and conflating them is what made a lone
/// `--pyramid-gate` fail against a backend the caller never chose.
///
/// Precedence: `--merge` wins, then [`MERGE_BACKEND_ENV`]. **Neither channel
/// may mean a backend by accident** -- an unrecognised spelling is an error and
/// not a silent fall back, because the whole point of this switch is that which
/// merge ran must be knowable.
///
/// The environment is parsed on EVERY call, including the calls the flag wins.
/// The obvious implementation returns on the flag before it ever looks at the
/// environment, and then `STREHL_MERGE=banana` is ignored for exactly as long
/// as argv happens to carry `--merge` -- so the same environment is an error on
/// one command line and silent on the next, and which one you get depends on an
/// unrelated argument. VERIFY-WIRE found that as F5 and measured it:
/// `STREHL_MERGE=banana --merge estimator` exited 0. The flag still WINS. It
/// just no longer excuses a malformed environment.
///
/// Empty, whitespace-only and non-UTF-8 values are NOT errors: they mean the
/// variable carries no opinion, which is what an exported-but-cleared variable
/// means in every shell. That asymmetry is this function's, not the parser's --
/// `MergeBackend::parse` refuses those spellings, and a test pins which of the
/// two owns the decision.
///
/// NOTE: [`resolve_photometric_mode`] still has the F5 hole this function no
/// longer has. It is deliberately not fixed in the same change:
/// `STREHL_PHOTOMETRIC` is in live use by another agent's measurements tonight,
/// and widening its error surface mid-run would invalidate them. The divergence
/// is recorded here so it is not mistaken for an oversight.
pub fn stated_merge_backend(flag: Option<&str>) -> Result<Option<(MergeBackend, MergeSource)>> {
    let from_env = match std::env::var(MERGE_BACKEND_ENV) {
        Ok(v) if !v.trim().is_empty() => Some(
            MergeBackend::parse(&v)
                .with_context(|| format!("reading {MERGE_BACKEND_ENV}={v:?}"))?,
        ),
        _ => None,
    };
    if let Some(v) = flag {
        let backend = MergeBackend::parse(v).with_context(|| format!("reading --merge {v:?}"))?;
        return Ok(Some((backend, MergeSource::Flag)));
    }
    Ok(from_env.map(|b| (b, MergeSource::Env)))
}

/// A resolved backend, with the sentence the run log prints to say why.
#[derive(Debug)]
pub struct MergeChoice {
    pub backend: MergeBackend,
    pub source: MergeSource,
    /// Ready to print, e.g. `estimator (inferred from --gate; pass --merge
    /// pyramid to override)`.
    pub why: String,
}

/// Choose the merge backend, inferring it from the flag families when -- and
/// only when -- the caller did not state one.
///
/// This is the single entry point `strehl stack` uses. There is deliberately no
/// no-inference twin: a second public resolver that nothing calls would be an
/// unreachable function in the one file whose entire subject is reachability.
/// Callers wanting the stated-only answer ask [`stated_merge_backend`], which
/// this is built from and which returns `None` rather than inventing a default.
///
/// The rules, in order:
///
/// * stated (`--merge`, then [`MERGE_BACKEND_ENV`]) wins outright, and the
///   caller's contradicting flags are refused exactly as before;
/// * otherwise one family given, that family's backend;
/// * otherwise both families given, a hard error -- genuinely ambiguous, and
///   guessing here would be the silent choice this whole switch exists to
///   prevent;
/// * otherwise [`DEFAULT_MERGE_BACKEND`].
///
/// **This does not weaken the refusal.** The refusal exists so that a flag
/// which parses, prints nothing and does nothing cannot be mistaken for one
/// that works. Under inference the flag does precisely what it always did, on
/// the backend that implements it, and whenever the user names a backend a
/// contradicting flag is still refused with the same message. What changes is
/// the false-positive rate: a lone `--pyramid-gate` used to fail against a
/// default the caller never asked for.
///
/// `STREHL_MERGE` counts as STATED, deliberately. Were it not to count, then
/// `STREHL_MERGE=pyramid` alongside `--gate` would infer the estimator and
/// ignore the variable entirely -- an environment setting that parses, prints
/// nothing and does nothing, which is the exact failure this module refuses to
/// ship. Setting it is a deliberate act and it is treated as one.
pub fn choose_merge_backend(
    flag: Option<&str>,
    estimator_flags: &[&str],
    pyramid_flags: &[&str],
) -> Result<MergeChoice> {
    if let Some((backend, source)) = stated_merge_backend(flag)? {
        let why = match source {
            MergeSource::Flag => format!("{} (--merge)", backend.name()),
            _ => format!("{} ({MERGE_BACKEND_ENV})", backend.name()),
        };
        return Ok(MergeChoice {
            backend,
            source,
            why,
        });
    }
    let infer = |backend: MergeBackend, from: &[&str]| MergeChoice {
        backend,
        source: MergeSource::Inferred,
        why: format!(
            "{} (inferred from {}; pass --merge {} to override)",
            backend.name(),
            from.join(", "),
            backend.other().name()
        ),
    };
    match (estimator_flags.is_empty(), pyramid_flags.is_empty()) {
        (true, true) => Ok(MergeChoice {
            backend: DEFAULT_MERGE_BACKEND,
            source: MergeSource::Default,
            why: format!("{} (default)", DEFAULT_MERGE_BACKEND.name()),
        }),
        (false, true) => Ok(infer(MergeBackend::Estimator, estimator_flags)),
        (true, false) => Ok(infer(MergeBackend::Pyramid, pyramid_flags)),
        (false, false) => bail!(
            "{} names the estimator merge and {} names the pyramid, but no --merge was given, \
             so there is nothing to arbitrate between them. Pass --merge estimator or \
             --merge pyramid to say which you meant. This is refused rather than guessed \
             because a merge chosen by tie-break is a merge nobody chose.",
            estimator_flags.join(", "),
            pyramid_flags.join(", "),
        ),
    }
}

/// Parse `--pyramid-select`. Unknown spellings are errors, not defaults.
pub fn parse_select_mode(v: &str) -> Result<SelectMode> {
    match v.trim().to_ascii_lowercase().as_str() {
        "soft" | "soft-power" | "softpower" => Ok(SelectMode::SoftPower),
        "hard" | "hard-max" | "hardmax" | "pmax" => Ok(SelectMode::HardMax),
        other => bail!("unknown --pyramid-select {other:?}; valid values are `soft` and `hard-max`"),
    }
}

/// Parse `--pyramid-base`. Unknown spellings are errors, not defaults.
pub fn parse_base_band(v: &str) -> Result<BaseBand> {
    match v.trim().to_ascii_lowercase().as_str() {
        "mean" => Ok(BaseBand::Mean),
        "weighted" | "weighted-from-coarsest" => Ok(BaseBand::WeightedFromCoarsest),
        other => bail!("unknown --pyramid-base {other:?}; valid values are `mean` and `weighted`"),
    }
}

/// The outcome of solving a measured gate ladder for a target mean `n_eff`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Solve {
    /// The target lies inside the ladder; this gate reaches it.
    Gate(f64),
    /// The target is below everything the ladder measured. The reported gate is
    /// the ladder's lowest, and it already averages more than asked.
    BelowLadder { lowest_gate: f64, lowest: f64 },
    /// The target is above everything the ladder measured. Extrapolating a gate
    /// from a ladder that never reached the target would be inventing a number.
    AboveLadder { highest_gate: f64, highest: f64 },
    /// The ladder is not usable — fewer than two points, or not monotone.
    Unusable(&'static str),
}

/// Solve a measured `(gate, mean n_eff)` ladder for the gate hitting `target`.
///
/// # Why interpolation and not bisection
///
/// Pass two folds every gate in the ladder into its own accumulator for the
/// price of one decode, so a ladder is nearly free while each bisection step
/// costs a whole pass. One sweep therefore *is* the solve.
///
/// # Why log-log
///
/// The ladder is geometric in the gate and `n_eff` grows superlinearly in it
/// (109MSDCF: 1.414, 1.884, 2.891, 4.987 at gates 0.5, 1, 2, 4). Linear
/// interpolation on those points would systematically overestimate the gate.
/// In log-log the same ladder is close to straight, so the residual curvature
/// between adjacent rungs is small.
///
/// # Monotonicity is checked, not assumed
///
/// Admission is a threshold on a field fixed before the gate is applied, so a
/// larger gate admits a superset and `n_eff` cannot fall. That makes
/// non-monotonicity a bug rather than a property of the data, and it is
/// reported as `Unusable` rather than silently interpolated across.
pub(crate) fn solve_gate_for_n_eff(ladder: &[(f64, f64)], target: f64) -> Solve {
    if ladder.len() < 2 {
        return Solve::Unusable("a ladder needs at least two rungs to interpolate");
    }
    if target.is_nan() || target <= 1.0 {
        return Solve::Unusable("a target n_eff must exceed 1.0; the winner is always admitted");
    }
    let mut v: Vec<(f64, f64)> = ladder.to_vec();
    v.sort_by(|a, b| {
        a.0.partial_cmp(&b.0)
            .expect("gate ladder must not hold NaN")
    });
    if v.windows(2).any(|w| w[1].1 < w[0].1) {
        return Solve::Unusable("n_eff fell as the gate rose, which is a bug, not a measurement");
    }
    if v.iter().any(|r| r.0 <= 0.0 || r.1 <= 0.0) {
        return Solve::Unusable("log-log interpolation needs strictly positive rungs");
    }

    let (lo, hi) = (v[0], v[v.len() - 1]);
    if target < lo.1 {
        return Solve::BelowLadder {
            lowest_gate: lo.0,
            lowest: lo.1,
        };
    }
    if target > hi.1 {
        return Solve::AboveLadder {
            highest_gate: hi.0,
            highest: hi.1,
        };
    }
    for w in v.windows(2) {
        let ((g0, n0), (g1, n1)) = (w[0], w[1]);
        if target >= n0 && target <= n1 {
            if (n1 - n0).abs() < f64::EPSILON {
                return Solve::Gate(g0);
            }
            let f = (target.ln() - n0.ln()) / (n1.ln() - n0.ln());
            return Solve::Gate((g0.ln() + f * (g1.ln() - g0.ln())).exp());
        }
    }
    Solve::Unusable("the target fell between no pair of rungs, which cannot happen")
}

/// Report the solve, or explain why the sweep did not answer the question.
fn report_target_solve(est: &[Estimator], target: Option<f64>) {
    let Some(target) = target else {
        eprintln!(
            "gate solve      : not requested. Pass --target-n-eff 3 to solve the ladder for a\n\
             \x20                 gate, which is what fact 324 says you should be setting."
        );
        eprintln!();
        return;
    };
    let ladder: Vec<(f64, f64)> = est
        .iter()
        .map(|e| (e.gate().threshold as f64, e.mean_n_eff()))
        .filter(|r| r.0 > 0.0)
        .collect();

    eprintln!("--- gate solved for a target n_eff (MEASURED ladder, INTERPOLATED gate) ---");
    match solve_gate_for_n_eff(&ladder, target) {
        Solve::Gate(g) => {
            eprintln!("target n_eff    : {target:.3}");
            eprintln!("gate            : {g:.4}   (log-log interpolation between measured rungs)");
            eprintln!(
                "                  Re-run with --gate {g:.4} to confirm; interpolation is not\n\
                 \x20                 a measurement, and the rungs bracketing it are."
            );
        }
        Solve::BelowLadder {
            lowest_gate,
            lowest,
        } => eprintln!(
            "target n_eff {target:.3} is below the ladder: gate {lowest_gate:.4} already \
             averages {lowest:.3}.\n                  Extend the ladder downward to solve it."
        ),
        Solve::AboveLadder {
            highest_gate,
            highest,
        } => eprintln!(
            "target n_eff {target:.3} is above the ladder: gate {highest_gate:.4} reaches only \
             {highest:.3}.\n                  Extend the ladder upward; extrapolating would be \
             inventing a number."
        ),
        Solve::Unusable(why) => eprintln!("cannot solve    : {why}"),
    }
    eprintln!();
}

///
/// # Why more than one number
///
/// **`m2_pooled_abs` is fact 24's convention**, identified by measurement, not
/// by assumption: M2's harness is not preserved in the repository, so M38 §1
/// computed seven candidate conventions with an independent numpy
/// implementation and asked which reproduced the published 11.89 and 18.58.
/// `mean(0.5*(|dx| + |dy|))` hits both to **0.01% and 0.02%**. The pre-registered
/// guess — single-axis `|dx|`, predicted from the pi/2 ratio between an
/// isotropic magnitude and one component — matched one ROI and missed the other
/// by 17.5%, because ROI `64,800` is **1.43x anisotropic** (`|dy|` 21.84 against
/// `|dx|` 15.32). Reporting this column is what makes any comparison against
/// fact 24 legitimate; the two harnesses differ by 1.55x and 1.60x, an
/// ROI-dependent factor, so the conversion cannot be a constant.
///
/// # Why the correction exists
///
/// **Mean |grad| is confounded by noise, and the confound has the same sign as
/// the effect the metric is used to detect.** Noise contributes gradient. A
/// merge that reduces sigma therefore reduces mean |grad| *even with zero
/// blur*, so an uncorrected reading charges the merge for the very thing it is
/// supposed to do. This is not hypothetical here: M2 measured that argmax
/// *raises* gradient (fact 24), and argmax also raises noise (fact 19) — the
/// same confound, read as a virtue.
///
/// The squared form is additively decomposable where the absolute form is not:
/// `E[dx^2] = E[dx_signal^2] + E[dx_noise^2]`. With forward differences and
/// per-pixel `sigma`, the noise contribution at pixel `i` is exactly
/// `2*sigma_i^2 + sigma_{i+1}^2 + sigma_{i+w}^2`, so
/// `corrected_rms = sqrt(max(0, raw_rms^2 - noise_rms^2))` removes it using the
/// calibrated model rather than an assumption. M77 showed why that subtraction
/// is insufficient after selection: model sigma does not include max-over-N
/// inflation. Invariant 2 now uses [`cross_fitted_detail`]; this field remains
/// for component tests and historical columns only.
#[cfg_attr(not(test), allow(dead_code))]
struct DetailMetrics {
    /// `mean(0.5*(|dx| + |dy|))` — fact 24's convention, for comparability.
    m2_pooled_abs: f64,
    /// `mean(hypot(dx, dy))` — isotropic, rotation-invariant.
    iso_mean: f64,
    /// `sqrt(mean(dx^2 + dy^2))` — signal and noise together.
    raw_rms: f64,
    /// The model's prediction for what the noise alone contributes to it.
    noise_rms: f64,
    /// Model-only correction, not the post-selection acceptance headline.
    corrected_rms: f64,
}

/// Compute [`DetailMetrics`] from co-located values and per-pixel predicted
/// sigmas.
///
/// `sigma[i]` must be the predicted standard deviation of `v[i]` in the same
/// units, which for the merged image means it already carries the `1/sqrt(n)`
/// from averaging.
fn detail_metrics(v: &[f32], sigma: &[f32], w: usize, h: usize) -> DetailMetrics {
    if w < 2 || h < 2 {
        return DetailMetrics {
            m2_pooled_abs: 0.0,
            iso_mean: 0.0,
            raw_rms: 0.0,
            noise_rms: 0.0,
            corrected_rms: 0.0,
        };
    }
    let (mut pooled, mut iso, mut sq, mut nsq) = (0.0f64, 0.0f64, 0.0f64, 0.0f64);
    let mut n = 0usize;
    for y in 0..h - 1 {
        for x in 0..w - 1 {
            let i = y * w + x;
            let dx = (v[i + 1] - v[i]) as f64;
            let dy = (v[i + w] - v[i]) as f64;
            pooled += 0.5 * (dx.abs() + dy.abs());
            iso += (dx * dx + dy * dy).sqrt();
            sq += dx * dx + dy * dy;
            let (s0, s1, sw) = (sigma[i] as f64, sigma[i + 1] as f64, sigma[i + w] as f64);
            nsq += 2.0 * s0 * s0 + s1 * s1 + sw * sw;
            n += 1;
        }
    }
    let n = n as f64;
    let raw_rms = (sq / n).sqrt();
    let noise_rms = (nsq / n).sqrt();
    DetailMetrics {
        m2_pooled_abs: pooled / n,
        iso_mean: iso / n,
        raw_rms,
        noise_rms,
        corrected_rms: (raw_rms * raw_rms - noise_rms * noise_rms).max(0.0).sqrt(),
    }
}

#[derive(Clone, Copy, Debug)]
struct GradientPower {
    raw_sum: f64,
    noise_sum: f64,
    noise_covariance_square_sum: f64,
    samples: usize,
}

#[derive(Clone, Copy)]
struct GradientRoi<'a> {
    values: &'a [f32],
    sigma: &'a [f32],
    width: usize,
    height: usize,
}

impl<'a> GradientRoi<'a> {
    fn new(values: &'a [f32], sigma: &'a [f32], width: usize, height: usize) -> Self {
        Self {
            values,
            sigma,
            width,
            height,
        }
    }
}

fn gradient_power_columns(
    v: &[f32],
    sigma: &[f32],
    w: usize,
    h: usize,
    x0: usize,
    x1: usize,
) -> GradientPower {
    assert_eq!(v.len(), w * h);
    assert_eq!(sigma.len(), w * h);
    assert!(x0 < x1 && x1 <= w);
    let (mut raw_sum, mut noise_sum, mut noise_covariance_square_sum, mut samples) =
        (0.0f64, 0.0f64, 0.0f64, 0usize);
    if h < 2 || x1 - x0 < 2 {
        return GradientPower {
            raw_sum,
            noise_sum,
            noise_covariance_square_sum,
            samples,
        };
    }
    let mut gradient_degree = vec![0u8; w * h];
    for y in 0..h - 1 {
        for x in x0..x1 - 1 {
            let i = y * w + x;
            let dx = f64::from(v[i + 1] - v[i]);
            let dy = f64::from(v[i + w] - v[i]);
            raw_sum += dx * dx + dy * dy;
            let (v0, v1, vw) = (
                f64::from(sigma[i]).powi(2),
                f64::from(sigma[i + 1]).powi(2),
                f64::from(sigma[i + w]).powi(2),
            );
            let (dx_variance, dy_variance) = (v0 + v1, v0 + vw);
            noise_sum += dx_variance + dy_variance;
            noise_covariance_square_sum += dx_variance.powi(2) + dy_variance.powi(2);
            gradient_degree[i] += 2;
            gradient_degree[i + 1] += 1;
            gradient_degree[i + w] += 1;
            samples += 1;
        }
    }
    for y in 0..h {
        for x in x0..x1 {
            let i = y * w + x;
            let degree = f64::from(gradient_degree[i]);
            if degree >= 2.0 {
                let variance = f64::from(sigma[i]).powi(2);
                noise_covariance_square_sum += degree * (degree - 1.0) * variance.powi(2);
            }
        }
    }
    GradientPower {
        raw_sum,
        noise_sum,
        noise_covariance_square_sum,
        samples,
    }
}

#[derive(Clone, Copy, Debug)]
struct ControlledDetail {
    raw_power: f64,
    controlled_noise_power: f64,
    signal_power: f64,
    signal_standard_error: f64,
    structure: f64,
    inflation_left: f64,
    inflation_right: f64,
}

/// Remove selection-conditioned gradient noise with a contemporaneous flat
/// control rather than a constant transferred between stack lengths.
///
/// The flat and detail regions are split into disjoint left/right sets of
/// gradient anchors. Each detail half is corrected with the scale fitted on the
/// opposite flat half. When the detail ROI is the flat ROI, as in M77's null,
/// no sample is used both to fit and to evaluate its own scale.
fn cross_fitted_detail(detail: GradientRoi<'_>, flat: GradientRoi<'_>) -> Result<ControlledDetail> {
    ensure!(
        detail.width >= 4 && detail.height >= 2 && flat.width >= 4 && flat.height >= 2,
        "the repaired detail invariant needs flat and detail ROIs at least 4x2"
    );
    let flat_mid = flat.width / 2;
    let detail_mid = detail.width / 2;
    let flat_left = gradient_power_columns(
        flat.values,
        flat.sigma,
        flat.width,
        flat.height,
        0,
        flat_mid,
    );
    let flat_right = gradient_power_columns(
        flat.values,
        flat.sigma,
        flat.width,
        flat.height,
        flat_mid,
        flat.width,
    );
    let detail_left = gradient_power_columns(
        detail.values,
        detail.sigma,
        detail.width,
        detail.height,
        0,
        detail_mid,
    );
    let detail_right = gradient_power_columns(
        detail.values,
        detail.sigma,
        detail.width,
        detail.height,
        detail_mid,
        detail.width,
    );
    ensure!(
        flat_left.samples > 0
            && flat_right.samples > 0
            && detail_left.samples > 0
            && detail_right.samples > 0,
        "the repaired detail invariant has no gradient samples in one ROI half"
    );
    ensure!(
        flat_left.noise_sum > 0.0
            && flat_right.noise_sum > 0.0
            && detail_left.noise_sum > 0.0
            && detail_right.noise_sum > 0.0,
        "the calibrated noise model returned zero gradient power"
    );

    let scale_left = flat_left.raw_sum / flat_left.noise_sum;
    let scale_right = flat_right.raw_sum / flat_right.noise_sum;
    let (scale_for_detail_left, scale_for_detail_right) = (scale_right, scale_left); // M80_CROSS_FITTED_SCALES
    let samples = detail_left.samples + detail_right.samples;
    let raw_sum = detail_left.raw_sum + detail_right.raw_sum;
    let controlled_noise_sum = scale_for_detail_left * detail_left.noise_sum
        + scale_for_detail_right * detail_right.noise_sum;
    let signal_variance_sum = 2.0
        * scale_for_detail_left.powi(2)
        * (detail_left.noise_covariance_square_sum
            + detail_left.noise_sum.powi(2) * flat_right.noise_covariance_square_sum
                / flat_right.noise_sum.powi(2))
        + 2.0
            * scale_for_detail_right.powi(2)
            * (detail_right.noise_covariance_square_sum
                + detail_right.noise_sum.powi(2) * flat_left.noise_covariance_square_sum
                    / flat_left.noise_sum.powi(2));
    ensure!(
        scale_left.is_finite()
            && scale_right.is_finite()
            && controlled_noise_sum.is_finite()
            && controlled_noise_sum > 0.0,
        "the flat-control selection-noise scale is not finite and positive"
    );
    ensure!(
        signal_variance_sum.is_finite() && signal_variance_sum > 0.0,
        "the calibrated noise model returned no finite detail-power variance"
    );
    let raw_power = raw_sum / samples as f64;
    let controlled_noise_power = controlled_noise_sum / samples as f64;
    Ok(ControlledDetail {
        raw_power,
        controlled_noise_power,
        signal_power: raw_power - controlled_noise_power,
        signal_standard_error: signal_variance_sum.sqrt() / samples as f64,
        structure: (raw_power / controlled_noise_power).sqrt(),
        inflation_left: scale_left.sqrt(),
        inflation_right: scale_right.sqrt(),
    })
}

const DETAIL_FALSE_ANSWER_RATE: f64 = 0.01;
const DETAIL_DETECTION_Z: f64 = 2.326_347_874;

#[derive(Clone, Copy, Debug, PartialEq)]
enum DetailRetention {
    NotMeasurable,
    Measured(f64),
}

fn detail_target_is_measurable(detail: ControlledDetail) -> bool {
    detail.signal_power > DETAIL_DETECTION_Z * detail.signal_standard_error
}

fn equal_noise_retention(
    candidate: ControlledDetail,
    selector: ControlledDetail,
) -> DetailRetention {
    if !detail_target_is_measurable(selector) {
        return DetailRetention::NotMeasurable;
    }
    if selector.raw_power <= 0.0 {
        return DetailRetention::Measured(f64::NAN);
    }
    DetailRetention::Measured(
        ((candidate.signal_power + selector.controlled_noise_power).max(0.0) / selector.raw_power)
            .sqrt(),
    )
}

/// Merged green over an ROI, black-subtracted, in plane coordinates.
///
/// Deliberately the same shape as [`roi_green`] so the two sides of the detail
/// ratio are gathered the same way.
fn roi_green_merged(est: &Estimator, roi: Roi, geom: PlaneGeometry, black: f32) -> Vec<f32> {
    let mut out = Vec::with_capacity(roi.width * roi.height);
    for py in roi.y..roi.y + roi.height {
        for px in roi.x..roi.x + roi.width {
            out.push(est.green_mean(geom.index(px, py)) - black);
        }
    }
    out
}

struct SelectedRoi {
    roi: Roi,
    values: Vec<f32>,
    seen: Vec<bool>,
}

impl SelectedRoi {
    fn new(roi: Roi) -> Self {
        Self {
            roi,
            values: vec![0.0; roi.width * roi.height],
            seen: vec![false; roi.width * roi.height],
        }
    }

    fn fold(
        &mut self,
        frame: &Frame,
        frame_index: u16,
        best_index: &[u16],
        geom: PlaneGeometry,
        black: f32,
    ) {
        let values = roi_green(frame, self.roi, black);
        for y in 0..self.roi.height {
            for x in 0..self.roi.width {
                let local = y * self.roi.width + x;
                let global = geom.index(self.roi.x + x, self.roi.y + y);
                if best_index[global] == frame_index {
                    assert!(
                        !self.seen[local],
                        "selector ROI pixel {local} was supplied by two frames"
                    );
                    self.values[local] = values[local];
                    self.seen[local] = true;
                }
            }
        }
    }

    fn absorb(&mut self, other: &Self) {
        assert_eq!(self.roi, other.roi);
        for i in 0..self.values.len() {
            if other.seen[i] {
                assert!(
                    !self.seen[i],
                    "selector ROI pixel {i} occurred in two worker chunks"
                );
                self.values[i] = other.values[i];
                self.seen[i] = true;
            }
        }
    }

    fn is_complete(&self) -> bool {
        self.seen.iter().all(|v| *v)
    }
}

struct SelectorRois {
    flat: SelectedRoi,
    detail: SelectedRoi,
}

impl SelectorRois {
    fn new(flat: Roi, detail: Roi) -> Self {
        Self {
            flat: SelectedRoi::new(flat),
            detail: SelectedRoi::new(detail),
        }
    }

    fn fold(
        &mut self,
        frame: &Frame,
        frame_index: u16,
        best_index: &[u16],
        geom: PlaneGeometry,
        black: f32,
    ) {
        self.flat.fold(frame, frame_index, best_index, geom, black);
        self.detail
            .fold(frame, frame_index, best_index, geom, black);
    }

    fn absorb(&mut self, other: &Self) {
        self.flat.absorb(&other.flat);
        self.detail.absorb(&other.detail);
    }

    fn is_complete(&self) -> bool {
        self.flat.is_complete() && self.detail.is_complete()
    }
}

struct Plan {
    workers: usize,
    chunks: usize,
    chunk_len: usize,
    pass1_bytes: usize,
    pass2_bytes: usize,
    stats_bytes: usize,
    roi_bytes: usize,
}

/// Per-worker bytes in pass one: `FocusStats` (f32 focus + u16 index) plus the
/// four scratch planes the fold walks through.
const PASS1_PER_PX: usize = 6 + 4 + 12 + 4 + 4;
/// Per-worker scratch in pass two, excluding the accumulators.
const PASS2_SCRATCH_PER_PX: usize = 4 + 12 + 4 + 4;
/// One `Estimator`: four f32 sums, a u16 count, and the winner field it was
/// built from (f32 + u16).
const ESTIMATOR_PER_PX: usize = 4 * 4 + 2 + 4 + 2;
/// The extra fine focus plane `--stats` needs in every pass-two worker's
/// scratch. `ThroughFocus`'s own footprint is priced separately because it is
/// per gather rather than per frame.
const FINE_FIELD_PER_PX: usize = 4;

impl Plan {
    fn new(
        frames: usize,
        geom: PlaneGeometry,
        frame_bytes: usize,
        gates: usize,
        gathers: usize,
        roi_bytes: usize,
    ) -> Self {
        let px = geom.pixels();
        let pass1_bytes = px * PASS1_PER_PX + frame_bytes;
        // The statistics ride pass two, so they are priced into pass two and
        // therefore into the worker count. This is the honest place for them:
        // pricing them outside the per-worker term would license more workers
        // than the budget pays for, which is exactly the defect M8 measured in
        // the pre-M8 `buffers` model.
        let stats_bytes = if gathers > 0 {
            px * (FINE_FIELD_PER_PX + gathers * ThroughFocus::bytes_per_pixel())
        } else {
            0
        };
        let pass2_bytes = px * (PASS2_SCRATCH_PER_PX + gates * ESTIMATOR_PER_PX)
            + stats_bytes
            + roi_bytes
            + frame_bytes;
        // The binding pass is whichever needs more per worker, so that one
        // worker count is safe for both and the two passes chunk identically.
        let per_worker = pass1_bytes.max(pass2_bytes);
        let by_memory = (MEMORY_BUDGET_BYTES / per_worker).max(1);
        let by_cpu = std::thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(1);
        let workers = by_memory.min(by_cpu).min(frames.max(1));
        let chunk_len = frames.div_ceil(workers);
        Self {
            workers,
            chunks: frames.div_ceil(chunk_len),
            chunk_len,
            pass1_bytes,
            pass2_bytes,
            stats_bytes,
            roi_bytes,
        }
    }

    fn describe(&self) -> String {
        let mut s = format!(
            "workers         : {} chunks of <= {} frames ({} allowed by the {} MB budget, {} by CPU)\n\
             working set     : {:.0} MB/worker pass 1, {:.0} MB/worker pass 2 (buffers only, a \
             LOWER BOUND)",
            self.chunks,
            self.chunk_len,
            self.workers,
            MEMORY_BUDGET_BYTES / (1 << 20),
            std::thread::available_parallelism()
                .map(|v| v.get())
                .unwrap_or(1),
            self.pass1_bytes as f64 / 1e6,
            self.pass2_bytes as f64 / 1e6,
        );
        if self.stats_bytes > 0 {
            s.push_str(&format!(
                "\n  of which stats: {:.0} MB/worker of through-focus sufficient statistics, \
                 CONSTANT in the frame count",
                self.stats_bytes as f64 / 1e6
            ));
        }
        if self.roi_bytes > 0 {
            s.push_str(&format!(
                "\n  of which detail control: {:.1} MB/worker, CONSTANT in the frame count",
                self.roi_bytes as f64 / 1e6
            ));
        }
        s
    }
}

/// Everything a worker needs that is identical across both passes.
struct Ctx<'a> {
    geom: PlaneGeometry,
    levels: Levels,
    noise: &'a NoiseModel,
    live: &'a AtomicUsize,
    peak_live: &'a AtomicUsize,
    /// Per-frame photometric gains, or `None` to merge without a photometric
    /// term. Built between the two passes from flux accumulated in pass one.
    ///
    /// M24 measured real per-frame drift across most of the corpus — 0.91%
    /// peak-to-peak on `109MSDCF`, **11.70% on `coffee-bean`** — which EXIF
    /// does not predict, so it must be fitted from the data. A gated average
    /// that has not corrected an 11.70% gain drift is reading an exposure
    /// change as a signal change.
    photometric: Option<&'a PhotometricMap>,
    /// The bracket's solved geometry, or `None` when merging unregistered.
    ///
    /// M86 measured that these stacks drift 232.7 px (bee-3-cpl) and 299.2 px
    /// (bee-2-cpl) corner-to-corner, so an unregistered merge is combining
    /// frames that do not describe the same scene points. When this is `Some`,
    /// every frame is resampled onto the reference grid before anything reads
    /// it.
    warps: Option<&'a WarpMap>,
    /// Whether [`Ctx::field_for`] should read each frame's mean level for the
    /// `auto` decision. False on every other path, so the cost — one pass over
    /// the G1 sites of the active area — is paid only by the mode that needs
    /// it, and the `off` and `on` paths are untouched.
    measure_drift: bool,
    /// Depth-layer masked selection support, or `None` for the shipped
    /// full-window operator.
    ///
    /// When this is `Some`, [`Ctx::field_for`] elects on
    /// [`FocusField::compute_layered`] and [`regularise_layered`] instead of the
    /// plain pair. Both compute the shipped box mean first and overwrite only
    /// the treated pixels, so a support that treats nothing is byte-identical
    /// to `None`; the distinction here is about **cost**, not behaviour.
    support: Option<&'a LayerSupport>,
    /// Per-pixel selection radius solved from the calibrated noise model
    /// ([`SelectionScale::from_silhouettes`]), or `None` for a fixed window.
    ///
    /// This is the shipping path. When it is `Some`, [`Ctx::field_for`] elects
    /// on [`FocusField::compute_scaled`] and regularises with
    /// [`regularise_guided`] — both cascades of the election adapt, which is
    /// the only configuration that removes the rim rather than relocating it.
    scale: Option<&'a edgeaware::SelectionScale>,
    /// Elect at this radius with the plain shipped operator, ignoring
    /// `support`. Set only by the depth-guide pass, which needs a narrow
    /// window; `None` everywhere else.
    guide_radius: Option<usize>,
    /// The contributed focus operator `--focus` selected, already calibrated by
    /// the host, or `None` for the shipped path.
    ///
    /// It is a `&Registered` and not an `&dyn FocusMeasure` on purpose. A
    /// `Registered` cannot be obtained without the registry having MEASURED the
    /// operator's response SD -- `Calibration` has no public constructor -- so
    /// there is no way to reach this field holding an operator whose gate has
    /// not been calibrated. That is the plugin crate's whole design, carried
    /// intact across the crate boundary rather than re-stated as a convention.
    focus_op: Option<&'a strehl_plugin::registry::Registered>,
}

/// Per-worker scratch, allocated once per chunk and reused across frames.
///
/// Bundled rather than passed loose because both passes need exactly this set
/// and the memory plan prices it as one unit.
struct Scratch {
    luma: Vec<f32>,
    field: FocusField,
    box_scratch: Vec<f32>,
    reg: Vec<f32>,
    /// The fine focus field, allocated only when `--stats` asked for it.
    fine: Vec<f32>,
    /// Per-pixel clip flags for the frame currently in `luma`.
    clipped: Vec<bool>,
    /// Buffers for resampling a frame onto the reference grid. Allocated only
    /// when the merge is registering.
    warp: Option<WarpScratch>,
    /// The mean G1 level of the frame most recently decoded into this scratch,
    /// read from the raw mosaic **before** registration and before any
    /// photometric gain. `None` unless the merge is measuring drift.
    ///
    /// Before the warp on purpose: the drift the decision rule was calibrated
    /// against is a property of the *light*, and reading it after resampling
    /// would make it a property of the alignment solve as well. M103 measured
    /// that the alignment solve already recovers about half of the level
    /// change, so a post-warp reading would systematically under-report.
    drift_level: Option<f64>,
    /// Two planes of working space for [`regularise_layered`]. Empty unless the
    /// merge is electing edge-aware.
    lay_scratch: Vec<f32>,
}

impl Scratch {
    fn new_with_warp(geom: PlaneGeometry, fine: bool, warp: bool) -> Self {
        let px = geom.pixels();
        Self {
            luma: vec![0.0; px],
            field: FocusField::new(geom),
            box_scratch: vec![0.0; px],
            reg: vec![0.0; px],
            fine: if fine { vec![0.0; px] } else { Vec::new() },
            clipped: vec![false; px],
            warp: warp.then(|| WarpScratch::new(geom)),
            drift_level: None,
            lay_scratch: Vec::new(),
        }
    }
}

#[derive(Default, Clone, Copy)]
struct Timings {
    decode: f64,
    work: f64,
}

impl Timings {
    fn add(&mut self, other: Timings) {
        self.decode += other.decode;
        self.work += other.work;
    }
}

impl Ctx<'_> {
    /// Did the alignment solve refuse to place this frame?
    ///
    /// A refused frame is **not** a frame with an identity warp. The solve
    /// could not connect it to the rest of the bracket, so its geometry is
    /// unknown; folding it unregistered would put a mis-registered frame into
    /// the election, which is the defect alignment exists to remove.
    ///
    /// Every pass must ask this and skip identically, or pass two would gate
    /// against a winner field pass one built from a different set of frames.
    fn is_refused(&self, index: u16) -> bool {
        self.warps.is_some_and(|m| {
            m.warps()
                .get(index as usize)
                .is_some_and(|w| w.is_refused())
        })
    }

    /// Decode one frame and produce its regularised focus field into
    /// `scratch.reg`.
    ///
    /// Both passes go through here, which is the point: pass two's gate is only
    /// meaningful if the field it compares was produced by the same arithmetic
    /// that elected the winner in pass one.
    fn field_for(
        &self,
        path: &Path,
        index: u16,
        scratch: &mut Scratch,
        t: &mut Timings,
    ) -> Result<Frame> {
        let t0 = Instant::now();
        let in_flight = self.live.fetch_add(1, Ordering::Relaxed) + 1;
        self.peak_live.fetch_max(in_flight, Ordering::Relaxed);
        let frame = match strehl_raw::decode(path) {
            Ok(f) => f,
            Err(e) => {
                self.live.fetch_sub(1, Ordering::Relaxed);
                return Err(e).with_context(|| format!("frame {index}"));
            }
        };
        t.decode += t0.elapsed().as_secs_f64();

        let t0 = Instant::now();
        if frame.levels != self.levels {
            self.live.fetch_sub(1, Ordering::Relaxed);
            bail!(
                "frame {index} ({}) has levels black {} white {}, but the stack was calibrated at \
                 black {} white {}",
                frame.path.display(),
                frame.levels.black,
                frame.levels.white,
                self.levels.black,
                self.levels.white
            );
        }
        // M125: the drift reading, taken HERE -- after decode, before
        // registration, before any photometric gain -- because that is where
        // M24 took the numbers the decision threshold was calibrated against.
        //
        // Reading it after the warp would make it a function of the alignment
        // solve: M103 measured the solve already recovering about half the
        // level change, so a post-warp reading under-reports drift and would
        // push `auto` toward declining stacks it should take. Reading it after
        // the gain would be circular -- the gain exists to remove exactly this.
        //
        // Costs one pass over the G1 sites of the active area, once per frame,
        // and only when `auto` asked for it.
        scratch.drift_level = if self.measure_drift {
            photometric::g1_mean_above_black(
                &frame.data,
                frame.stride,
                (
                    frame.active.x,
                    frame.active.y,
                    frame.active.width,
                    frame.active.height,
                ),
                self.levels.black,
            )
        } else {
            None
        };
        // Registration happens here, before anything reads a pixel, so that
        // every downstream stage -- focus field, gate, estimator, output --
        // sees frames that describe the same scene points. Doing it here also
        // means the two passes cannot disagree about geometry.
        let mut frame = frame;
        if let Some(map) = self.warps {
            match map.warp(index as usize) {
                Ok(FrameWarp::Placed(t)) => {
                    let scratch_warp = scratch
                        .warp
                        .as_mut()
                        .expect("warp scratch is allocated whenever the merge is registering");
                    if let Err(e) = align_cmd::warp_frame_in_place(
                        &mut frame,
                        *t,
                        self.geom,
                        map.resampler(),
                        scratch_warp,
                    ) {
                        self.live.fetch_sub(1, Ordering::Relaxed);
                        return Err(e);
                    }
                }
                Ok(FrameWarp::Refused(why)) => {
                    self.live.fetch_sub(1, Ordering::Relaxed);
                    // Unreachable: every caller skips refused frames via
                    // `is_refused`. Kept so a new pass that forgets to skip
                    // fails loudly instead of merging unknown geometry.
                    bail!(
                        "frame {index} was refused by the alignment solve ({why}) but \
                         reached field_for; a merge pass is missing its is_refused skip"
                    );
                }
                Err(e) => {
                    self.live.fetch_sub(1, Ordering::Relaxed);
                    return Err(e.into());
                }
            }
        }
        // Photometric normalisation, at the seam, AFTER registration so the
        // gain and the geometry describe the same frame, and BEFORE the focus
        // measure so the field, the gate and the estimator all see normalised
        // data (M99 §13.2).
        //
        // The frame is scaled and the noise model is scaled with it. That
        // second half is not optional: the model is
        // `sigma^2(S) = g*S + (RN*g)^2`, so scaling data by `c` without
        // scaling the model under-estimates sigma by between sqrt(c) and c --
        // up to 17% on the measured lavendar-cpl gain span -- and the gate,
        // which is calibrated in units of focus noise, then fires too readily
        // on exactly the frames that were brightened. M99 calls this "the
        // single most important sentence in this patch".
        //
        // Because focus is `contrast / sigma`, scaling both leaves the focus
        // response EXACTLY invariant, which is why this is election-neutral by
        // construction: M99 measured 34 re-elected pixels of 8.25M. A
        // mis-propagated variant re-elects 40.13%.
        let scaled_noise;
        let mut noise = self.noise;
        if let Some(map) = self.photometric {
            match map.gain(index as usize) {
                Ok(g) if g != 1.0 => {
                    photometric::apply_to_u16(
                        &mut frame.data,
                        self.levels.black,
                        self.levels.white,
                        g,
                    );
                    scaled_noise = photometric::scale_noise_model(self.noise, g);
                    noise = &scaled_noise;
                }
                // A frame the fit refused (clipped, or no usable flux) is
                // merged UNCORRECTED rather than dropped: its geometry is
                // still good, and gain 1.0 is exactly the status quo for it.
                // The refusal is reported once, before the passes run.
                _ => {}
            }
        }
        let frame = frame;
        green_luma_with_clip(
            &frame,
            self.levels.black,
            CONTAINER_MAX_DN,
            &mut scratch.luma,
            &mut scratch.clipped,
        );
        if scratch.fine.is_empty() {
            match (self.guide_radius, self.scale, self.support) {
                (Some(r), _, _) => scratch.field.compute_at_radius(&scratch.luma, noise, r),
                (None, Some(s), _) => match self.focus_op {
                    // The DEFAULT estimator arm (acuity is on unless
                    // STREHL_EDGE_AWARE=0), so this is the one that has to
                    // carry --focus for the flag to mean anything in the
                    // shipping configuration.
                    Some(op) => {
                        scratch
                            .field
                            .compute_scaled_with_measure(op.measure(), &scratch.luma, noise, s);
                    }
                    None => scratch.field.compute_scaled(&scratch.luma, noise, s),
                },
                // The plugin seam, and the ONLY arm that has one. The other
                // three reach Tenengrad-specific entry points -- a scaled
                // window, a layered support, a fixed guide radius -- that take
                // no operator, so `run_estimator` refuses `--focus` in
                // combination with them rather than accepting the flag and
                // electing on the shipped operator anyway.
                //
                // `compute_with_measure` is the same `run_measure` the shipped
                // path goes through: `compute` -> `compute_at_radius` ->
                // `compute_with_measure(&Tenengrad::at_radius(r))`. There is
                // one pipeline, not two that agree.
                (None, None, None) => match self.focus_op {
                    Some(op) => {
                        scratch
                            .field
                            .compute_with_measure(op.measure(), &scratch.luma, noise);
                    }
                    None => scratch.field.compute(&scratch.luma, noise),
                },
                (None, None, Some(s)) => scratch.field.compute_layered(&scratch.luma, noise, s),
            }
        } else {
            // One shared gradient pass produces both scales. The selection field
            // is bit-identical either way — pinned by
            // `through_focus::tests::gathering_statistics_cannot_move_the_selection_field`
            // — so turning statistics on cannot move the merge.
            scratch.field.compute_with_fine(
                &scratch.luma,
                noise,
                STATS_RADIUS,
                &mut scratch.fine,
            );
        }
        match self.support.filter(|_| self.guide_radius.is_none()) {
            None if self.scale.is_some() && self.guide_radius.is_none() => {
                // The guided regulariser, at the SAME nominal scale as the
                // shipped box. Away from a luma step this is the shipped
                // operator; at an occluding silhouette it stops instead of
                // averaging across, which is what stops the narrow selection
                // window's win being undone by the second cascade.
                let px = self.geom.pixels();
                if scratch.lay_scratch.len() != 3 * px {
                    scratch.lay_scratch = vec![0.0; 3 * px];
                }
                let (tmp, rest) = scratch.lay_scratch.split_at_mut(px);
                let (dom, extra) = rest.split_at_mut(px);
                regularise_guided(
                    scratch.field.values(),
                    &scratch.luma,
                    self.geom,
                    extra,
                    tmp,
                    dom,
                    &mut scratch.reg,
                );
            }
            None => match self.guide_radius {
                // The guide's regulariser is capped to the guide's own window,
                // or the radius-8 box would displace the step it is looking for.
                Some(r) => regularise_at(
                    scratch.field.values(),
                    self.geom,
                    r,
                    &mut scratch.box_scratch,
                    &mut scratch.reg,
                ),
                None => regularise(
                    scratch.field.values(),
                    self.geom,
                    &mut scratch.box_scratch,
                    &mut scratch.reg,
                ),
            },
            // Both ends of the election's box cascade have to be told about the
            // depth step. An edge-aware focus window under a radius-8
            // regulariser just re-manufactures the rim at the regulariser's own
            // scale.
            Some(s) => {
                let px = self.geom.pixels();
                if scratch.lay_scratch.len() != 2 * px {
                    scratch.lay_scratch = vec![0.0; 2 * px];
                }
                let (tmp, acc) = scratch.lay_scratch.split_at_mut(px);
                regularise_layered(
                    scratch.field.values(),
                    self.geom,
                    s,
                    &mut scratch.box_scratch,
                    tmp,
                    acc,
                    &mut scratch.reg,
                );
            }
        }
        t.work += t0.elapsed().as_secs_f64();
        Ok(frame)
    }
    fn release(&self, frame: Frame) {
        drop(frame);
        self.live.fetch_sub(1, Ordering::Relaxed);
    }
}

/// Environment switch for the edge-aware election (BUILD-HALO).
///
/// An environment variable rather than a flag for the same reason
/// `STREHL_ALIGN` and `STREHL_FIX_HALO` are: the subcommand definition in
/// `main.rs` is owned by another agent tonight. The flag is the better
/// long-term home.
pub const EDGE_AWARE_ENV: &str = "STREHL_EDGE_AWARE";
/// Override for the depth-step tolerance, in frames. See [`edge_tau`].
pub const EDGE_TAU_ENV: &str = "STREHL_EDGE_TAU";
/// Override for the confidence veto, in multiples of the plane's own
/// low-percentile guide response. Default 2.0.
pub const EDGE_CONF_ENV: &str = "STREHL_EDGE_CONF";

/// Radius the depth guide elects at.
///
/// Narrow on purpose. The shipped merge's own winner field has its depth step
/// displaced outward by exactly one window radius — that displacement IS the
/// halo — so a guide elected at 13 px cannot locate the silhouette the support
/// has to avoid. 4 px carries a ~5 px step of its own, well inside the 13 px
/// the masking has to reach.
const GUIDE_RADIUS: usize = 4;

/// Render exactly one frame of the bracket, by index, with no election at all.
pub const ONLY_FRAME_ENV: &str = "STREHL_ONLY_FRAME";

/// Restrict the bracket to a single frame, for diagnosis only.
///
/// # Why this exists
///
/// Every halo argument this build has made compares one *merge* against
/// another, and every such comparison can only see what the **election** does.
/// That is structurally unable to answer the question that decides the whole
/// plan: is the bright aura around a subject something we *chose*, or something
/// the *lens* did?
///
/// A single frame has no election — one frame is trivially its own winner at
/// every pixel — so whatever aura survives here is optical, and no selection
/// strategy whatsoever can remove it. Conversely an aura that is present in the
/// merge and absent from every single frame is entirely ours.
///
/// This is a diagnostic, not a feature: it is an environment variable rather
/// than a flag precisely because it produces a deliberately wrong picture, and
/// the number it takes is a raw bracket index whose meaning depends on the
/// capture order of the directory being read.
fn only_frame(paths: Vec<std::path::PathBuf>) -> Vec<std::path::PathBuf> {
    let Ok(raw) = std::env::var(ONLY_FRAME_ENV) else {
        return paths;
    };
    let k: usize = raw
        .trim()
        .parse()
        .unwrap_or_else(|_| panic!("{ONLY_FRAME_ENV}={raw:?} is not a frame index"));
    assert!(
        k < paths.len(),
        "{ONLY_FRAME_ENV}={k} but the bracket has {} frames",
        paths.len()
    );
    eprintln!(
        "{ONLY_FRAME_ENV}={k}: rendering 1 of {} frames, NO election -- diagnostic only",
        paths.len()
    );
    vec![paths[k].clone()]
}

fn edge_conf() -> f32 {
    env_num(EDGE_CONF_ENV, 2.0)
}

fn env_num(key: &str, default: f32) -> f32 {
    match std::env::var(key) {
        Err(_) => default,
        Ok(raw) => raw
            .trim()
            .parse()
            .unwrap_or_else(|_| panic!("{key}={raw:?} is not a number")),
    }
}

/// Which edge-aware election is in force.
#[derive(Copy, Clone, PartialEq, Eq, Debug)]
enum EdgeArm {
    /// The shipped fixed-window operator. An A/B baseline, not a default.
    Off,
    /// Per-pixel radius solved from the noise model, plus the luma-guided
    /// regulariser. **The default.**
    Acuity,
    /// The depth-layer masked support. Superseded — kept switchable because it
    /// is the arm every earlier measurement in this build was taken against,
    /// and those comparisons have to stay reproducible.
    Layer,
}

/// The edge-aware election is **ON by default**.
///
/// It was behind an opt-in env var while it was being built, and the direct
/// consequence was that every render the owner actually looked at still had the
/// halo in it — the fix was measured, committed, reported, and never once
/// applied to a picture anybody saw. An environment variable is an A/B
/// mechanism. It is not a shipping mechanism, and treating it as one cost this
/// build a full cycle of "why does the render still look like that".
///
/// So the default is on, and the variable now selects an *arm*:
///
/// | `STREHL_EDGE_AWARE` | arm |
/// | --- | --- |
/// | unset, `1`, `on`, `true`, `acuity` | adaptive radius (shipping) |
/// | `0`, `off`, `false` | shipped fixed window |
/// | `layer` | the superseded masked-support arm |
/// Which election arm ships.
///
/// # This shipped ON and is back OFF, on a do-no-harm rejection
///
/// The adaptive-radius arm reduces the halo -- the broad aura on `bee-2-cpl` is
/// gone with it and the `off` arm's rim on
/// `flower-bud-with-background-fern-cpl` is both thicker and carries a dark band
/// the `on` arm removes. It ships **off** anyway, because it fails the texture
/// guard.
///
/// `couch-fibers-cpl` is dense fibre filling the frame with **no depth
/// silhouettes anywhere**, and it renders well on the shipped path. Rendered
/// `off` and `on` from one pinned binary and judged at 100% -- same crop origin,
/// same display gain, arms sharing a pixel grid -- the `on` arm is visibly
/// **softer**: adjacent filaments less separated, specular glints along the
/// fibres duller, micro-contrast down. The standing rule is that a change which
/// degrades a good subject is rejected regardless of what it does to the halo,
/// and this one does.
///
/// It is invisible at the 1400 px full frame, because downsampling is a low-pass
/// filter and the loss is high-frequency. It has to be judged at 1:1.
///
/// # The cause, which is also section 16's cause
///
/// [`SelectionScale::from_silhouettes`](strehl_core::edgeaware::SelectionScale::from_silhouettes)
/// collapses the radius where the guide varies locally. On this subject every
/// pixel is a depth step -- fibres at many depths interleaved at pixel scale --
/// so it collapses nearly everywhere, and a 1 px focus measure on a noisy
/// texture is a bad estimator.
///
/// **SUPERSEDED BY MEASUREMENT — that is no longer what happens.** The veto
/// added afterwards fixed it, and fixed it so thoroughly that the rule now has
/// the opposite problem. Measured on this subject from one binary:
///
/// ```text
/// collapse veto : 86101 px admitted (1.04% of plane)
/// by radius     : r1 0.00%  r2 0.00%  r4 0.02%  r8 0.05%  r13 99.93%
/// ```
///
/// The geometric rule is now very nearly **inert** here -- 99.93% of the frame
/// elects at the shipped 13 px, because the veto refuses the collapse wherever
/// no second layer is resolvable, which on a single-depth texture is almost
/// everywhere. So the softening this section describes is real but its cause is
/// the reverse of what is written above: not a 1 px window on noisy texture, but
/// a 13 px window on ALL texture.
///
/// That is why deleting the noise-driven shrink cost the library 6.6% gradient
/// RMS. With it gone there was nothing left to adapt the window on a subject
/// without silhouettes. Restoring it moves this subject to r1 45.86% / r2 25.30%
/// / r4 17.93% and recovers **+6.56%** at viewing scale, visibly at 1:1.
/// See `experiments/BUILD-HALO/acuity_measure.py`.
///
/// The paragraph is kept rather than rewritten because the reasoning that
/// follows it -- "collapse only where collapsing buys something" -- is what
/// produced the veto and is still correct. Only its factual premise expired.
///
/// That is the same defect as the dead-ground over-collapse, from the other
/// side. Over dead ground the guide is noise; over dense texture the steps are
/// real. In both cases collapsing **buys nothing** and costs the estimator. The
/// rule needs to be "collapse only where collapsing buys something" -- at a
/// genuine occluding boundary, where a large window would straddle two depths
/// that are actually separated. Local guide variation cannot tell that from
/// either failure, and every veto tried so far has been an attempt to patch that
/// one deficiency from outside.
///
/// Turn it back on here, not by changing a default elsewhere, once the rule
/// distinguishes those cases and `couch-fibers-cpl` is no worse at 100%.
fn edge_aware_arm() -> EdgeArm {
    match std::env::var(EDGE_AWARE_ENV).ok().as_deref().map(str::trim) {
        None | Some("") | Some("1") | Some("on") | Some("true") | Some("acuity") => EdgeArm::Acuity,
        Some("0") | Some("off") | Some("false") => EdgeArm::Off,
        Some("layer") => EdgeArm::Layer,
        Some(other) => panic!(
            "{EDGE_AWARE_ENV}={other:?} is not a known arm; expected one of \
             on/off/acuity/layer"
        ),
    }
}


/// Confidence the acuity term demands before it hands a pixel a smaller
/// window, in standard deviations of a difference of two responses.
///
/// **Deliberately the same number as [`Gate::DEFAULT_GATE`], and for the same
/// reason.** The gate asks "are these two frames distinguishable at this
/// pixel?"; the radius rule asks "is this pixel's peak distinguishable from its
/// own baseline at this radius?". Both are the same question about the same
/// noise model, so a second, independently-tuned constant here would be a
/// second calibration of one physical quantity — exactly the failure mode this
/// project exists to avoid. It is not a free parameter and it should not be
/// swept.
const ACUITY_MARGIN: f32 = strehl_core::merge::DEFAULT_GATE;

/// Whether the noise-driven window shrink runs on top of the geometric cap.
///
/// `STREHL_ACUITY=0` disables it, which is the ONLY reason this switch exists:
/// `57e4554` deleted the term after measuring one subject's background noise,
/// and a 26-subject gallery delta then charged the deletion **-6.6% gradient
/// RMS**. Both arms have to be renderable **from one binary** or the comparison
/// re-acquires the build-drift confound that made the original deletion look
/// free. Default ON.
const ACUITY_ENV: &str = "STREHL_ACUITY";

fn acuity_shrink() -> bool {
    !matches!(
        std::env::var(ACUITY_ENV).ok().as_deref().map(str::trim),
        Some("0" | "off" | "no" | "false")
    )
}

/// How many frames of guide variation a support box may span before it is
/// judged to cross a depth discontinuity.
///
/// **Scaled from the bracket, not carried across stacks** (AGENTS.md: never
/// carry a threshold across stacks). The default is an eighth of the guide
/// winner field's own robust span, floored at 4 frames. A tilted subject sweeps
/// the winner field smoothly and must not read as a step: at the shipped radius
/// a box spans 27 px, so a tilt of one frame per pixel spans 26 frames, and an
/// eighth of a full 299-frame bracket clears that comfortably. A genuine
/// occluding silhouette jumps most of the bracket in a pixel or two.
fn edge_tau(guide: &[u16]) -> f32 {
    if let Ok(raw) = std::env::var(EDGE_TAU_ENV) {
        let v: f32 = raw
            .trim()
            .parse()
            .unwrap_or_else(|_| panic!("{EDGE_TAU_ENV}={raw:?} is not a number"));
        assert!(v > 0.0, "{EDGE_TAU_ENV} must be positive");
        return v;
    }
    let mut v: Vec<u16> = guide.iter().copied().filter(|&k| k != u16::MAX).collect();
    if v.is_empty() {
        return 4.0;
    }
    v.sort_unstable();
    let q = |f: f64| f32::from(v[((v.len() - 1) as f64 * f) as usize]);
    // Robust span, not max - min: a handful of pixels electing frame 0 or
    // frame N-1 out of noise would otherwise set the tolerance for the plane.
    ((q(0.99) - q(0.01)) / 8.0).max(4.0)
}

/// Elect a winner field at [`edgeaware::GUIDE_LEVEL`] to locate depth steps.
///
/// This is a **third pass over the frames** and it is the price of the fix.
/// It exists because the shipped winner field cannot locate its own silhouettes:
/// it is haloed by exactly one window radius, so its depth steps sit 13 px into
/// the background and a support truncated at them still swallows the foreground
/// (see `edgeaware`'s module header, and the BUILD-HALO ladder that measured the
/// displacement).
///
/// It folds nothing but [`FocusStats`] — no flat ROI, no flux, no drift, no
/// clip census — because the only thing read off it is `best_index`.
/// Directory to write the bimodality diagnostic into, if asked.
///
/// The detector costs a `frames`-independent 12 B/px riding the guide's decode,
/// but it is still work nobody needs on a normal render, so it is off unless
/// this names somewhere to put the answer.
pub const BIMODAL_DUMP_ENV: &str = "STREHL_BIMODAL_DUMP";

fn bimodal_dump() -> Option<std::path::PathBuf> {
    std::env::var_os(BIMODAL_DUMP_ENV).map(std::path::PathBuf::from)
}

/// Answer one question: **does the through-focus response go bimodal on the
/// pixels the masked-support fix still fails?**
///
/// The two survivors are the tight bright rim at the silhouette and the blobs
/// at the fix's coverage boundary, and §10.3 argued both are the same wall —
/// a 13 px window near a silhouette does not *contain* enough background to
/// reconstruct background from. If that is right, those pixels are exactly the
/// ones whose through-focus curve has two peaks: one where the foreground came
/// sharp, one where the background did. So this cross-tabulates prominence
/// against `blend`, which is where the fix reaches.
///
/// A detector that fires everywhere is useless and a detector that fires
/// nowhere kills the forward model, so both are reported rather than
/// summarised into a single number.
/// Mandate (B)'s first deliverable: **where does the detector fire?**
///
/// Writes full-plane maps of the mode statistics and the selection radius, so
/// the answer can be looked at as a picture over the whole subject rather than
/// inferred from a table at frozen ROIs. Judging on crops is how the severity
/// of the halo itself stayed hidden for a week, and the same mistake is
/// available here.
///
/// Reports the firing rate against the **adaptive radius**, which is the
/// question that decides mandate (B). If bimodality concentrates where the
/// radius rule had to collapse the window, those pixels are exactly the ones
/// with no clean background sample in any frame, and unmixing is the only thing
/// left that can help them. If it fires everywhere, or nowhere in particular,
/// the two-layer model is wrong for this data and must not be forced.
fn report_bimodality_scaled(
    modes: &BimodalStats,
    scale: &edgeaware::SelectionScale,
    guide: &[u16],
    geom: PlaneGeometry,
    dir: &Path,
) -> Result<()> {
    let prom = modes.second_mode_z();
    let first = modes.first_mode_z();
    let levels = scale.levels();
    std::fs::create_dir_all(dir).with_context(|| format!("creating {}", dir.display()))?;

    const FIRES: f32 = 1.5;
    // Bucket by how far the radius rule had to collapse the window: the small
    // radii are hard against a silhouette, the full radius is untouched ground.
    let mut buckets = vec![(0usize, 0.0f64, 0usize); edgeaware::LEVEL_RADII.len()];
    for i in 0..geom.pixels() {
        let b = levels[i] as usize;
        buckets[b].0 += 1;
        buckets[b].1 += f64::from(prom[i]);
        // BOTH modes must clear the baseline. Requiring only the second is the
        // defect that made the first detector fire on 54.2% of clean ground:
        // where neither peak is real the ratio tends to 1 by noise alone.
        if prom[i] >= FIRES && first[i] >= FIRES {
            buckets[b].2 += 1;
        }
    }
    eprintln!("--- where the bimodality detector fires, by selection radius (MEASURED) ---");
    for (b, &(n, sum, hits)) in buckets.iter().enumerate() {
        if n == 0 {
            continue;
        }
        eprintln!(
            "r{:<3} : {:>7.3}% of plane   mean z2 {:.3}   fires {:.2}%",
            edgeaware::LEVEL_RADII[b],
            100.0 * n as f64 / geom.pixels() as f64,
            sum / n as f64,
            100.0 * hits as f64 / n as f64
        );
    }
    eprintln!();

    // Full-plane maps, so a full-frame overlay can be built. Raw u16 LE with
    // the scaling stated in the log rather than baked into a picture.
    let dump = |name: &str, v: &[f32], full: f32| -> Result<()> {
        let p = dir.join(name);
        let mut raw = Vec::with_capacity(v.len() * 2);
        for &x in v {
            let q = ((x / full).clamp(0.0, 1.0) * 65535.0) as u16;
            raw.extend_from_slice(&q.to_le_bytes());
        }
        std::fs::write(&p, &raw).with_context(|| format!("writing {}", p.display()))?;
        eprintln!(
            "wrote {}  ({}x{} u16 LE raw, full scale = {full})",
            p.display(),
            geom.width,
            geom.height
        );
        Ok(())
    };
    dump("second_mode_z.raw", &prom, 6.0)?;
    dump("first_mode_z.raw", &first, 6.0)?;
    let lv: Vec<f32> = levels
        .iter()
        .map(|&l| edgeaware::LEVEL_RADII[l as usize] as f32)
        .collect();
    dump("radius.raw", &lv, strehl_core::focus::WINDOW_RADIUS as f32)?;
    let g: Vec<f32> = guide
        .iter()
        .map(|&k| if k == u16::MAX { 0.0 } else { f32::from(k) })
        .collect();
    let gmax = g.iter().copied().fold(1.0f32, f32::max);
    dump("guide.raw", &g, gmax)?;
    eprintln!();
    Ok(())
}

fn report_bimodality(
    modes: &BimodalStats,
    support: &LayerSupport,
    guide: &[u16],
    geom: PlaneGeometry,
    dir: &Path,
) -> Result<()> {
    let prom = modes.second_mode_z();
    let first = modes.first_mode_z();
    let sep = modes.separation();
    let blend = support.blend();
    std::fs::create_dir_all(dir)
        .with_context(|| format!("creating {}", dir.display()))?;

    // Three populations, by how far the fix reaches. "Boundary" is the blob
    // population: guards wanted it, the layer floor took it back.
    let mut buckets = [(0usize, 0.0f64, 0usize); 3];
    const FIRES: f32 = 1.5;
    for i in 0..geom.pixels() {
        let b = match blend[i] {
            x if x <= 0.001 => 0,
            x if x >= 0.999 => 2,
            _ => 1,
        };
        buckets[b].0 += 1;
        buckets[b].1 += f64::from(prom[i]);
        if prom[i] >= FIRES {
            buckets[b].2 += 1;
        }
    }

    eprintln!("--- bimodality of the through-focus response (MEASURED) ---");
    eprintln!(
        "detector        : two strongest peaks >= {} frames apart in the NARROW (r={GUIDE_RADIUS}) \
         response; significance of the SECOND peak in SDs of the pixel's own through-focus curve",
        edgeaware::MODE_SEPARATION
    );
    eprintln!(
        "cost            : {:.1} MB, constant in the {} frames folded",
        modes.allocated_bytes() as f64 / 1e6,
        modes.frames_folded()
    );
    for (b, name) in ["untreated", "boundary", "treated"].iter().enumerate() {
        let (n, sum, fired) = buckets[b];
        if n == 0 {
            eprintln!("{name:<16}: none");
            continue;
        }
        eprintln!(
            "{name:<16}: {:>7.3}% of plane   mean second-mode z {:.3}   fires (>={FIRES}) on {:.2}% \
             of them",
            100.0 * n as f64 / geom.pixels() as f64,
            sum / n as f64,
            100.0 * fired as f64 / n as f64
        );
    }
    eprintln!(
        "  READ          : if the boundary and treated rows fire far above the untreated row, \
         the two-layer model holds where the fix fails and unmixing is worth building. If every \
         row is alike, the detector cannot discriminate and the model is wrong too."
    );

    // 16-bit, because the whole point is to look at it and an 8-bit
    // prominence map would quantise the very gradient being judged.
    let quant = |v: &[f32], scale: f32| -> Vec<u16> {
        v.iter()
            .map(|&x| (x * scale).clamp(0.0, 65535.0) as u16)
            .collect()
    };
    let (w, h) = (geom.width as u32, geom.height as u32);
    for (name, data) in [
        ("bimodal-second-mode-z.tif", quant(&prom, 6553.5)),
        ("bimodal-first-mode-z.tif", quant(&first, 6553.5)),
        ("bimodal-mode-balance.tif", quant(&modes.mode_balance(), 65535.0)),
        (
            "bimodal-separation.tif",
            sep.iter().map(|&s| s.saturating_mul(256)).collect(),
        ),
        ("edge-aware-blend.tif", quant(blend, 65535.0)),
        // The depth map the whole argument is about. Without it "distance from
        // the silhouette" has to be guessed from the render, and the halo is
        // precisely the thing that makes the render an unreliable guide to
        // where the silhouette is.
        (
            "guide-winner.tif",
            guide.iter().map(|&k| k.saturating_mul(64)).collect(),
        ),
    ] {
        let path = dir.join(name);
        image_out::write_gray16(&path, w, h, &data)?;
        eprintln!("wrote           : {}", path.display());
    }
    eprintln!();
    Ok(())
}

fn guide_winner_field(
    paths: &[std::path::PathBuf],
    plan: &Plan,
    ctx: &Ctx<'_>,
    geom: PlaneGeometry,
    bimodal: bool,
) -> Result<(Vec<u16>, Vec<f32>, Option<BimodalStats>, Timings)> {
    let out = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(ci, chunk)| -> Result<(FocusStats, Option<BimodalStats>, Timings)> {
            let first_index = (ci * plan.chunk_len) as u16;
            let mut stats = FocusStats::new(geom);
            // Rides the guide's decode. The detector needs the NARROW field
            // for the same reason the guide does: a 13 px window smears the
            // foreground and background modes into a single peak, which is
            // precisely the confusion under investigation.
            let mut modes = bimodal.then(|| BimodalStats::new(geom));
            let mut scratch = Scratch::new_with_warp(geom, false, ctx.warps.is_some());
            let mut t = Timings::default();
            for (offset, path) in chunk.iter().enumerate() {
                let index = first_index + offset as u16;
                // The guide must skip exactly the frames the merge skips, or it
                // would locate silhouettes in a bracket the election never sees.
                if ctx.is_refused(index) {
                    continue;
                }
                let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                ctx.release(frame);
                stats
                    .fold(index, &scratch.reg)
                    .map_err(|e| map_dim_err(index, e))?;
                if let Some(m) = modes.as_mut() {
                    m.fold(index, &scratch.reg)
                        .map_err(|e| anyhow::anyhow!("frame {index}: {e}"))?;
                }
            }
            Ok((stats, modes, t))
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok((mut sa, mut ma, mut ta)), Ok((sb, mb, tb))) => {
                sa.absorb(&sb).map_err(|e| map_dim_err(0, e))?;
                if let (Some(x), Some(y)) = (ma.as_mut(), mb.as_ref()) {
                    x.absorb(y)
                        .map_err(|e| anyhow::anyhow!("bimodality merge: {e}"))?;
                }
                ta.add(tb);
                Ok((sa, ma, ta))
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    Ok((
        out.0.best_index().to_vec(),
        out.0.best_focus().to_vec(),
        out.1,
        out.2,
    ))
}

struct Pass1 {
    stats: FocusStats,
    /// Per-frame flux over the fixed low-detail region, for the photometric    /// fit. Empty unless the photometric term was asked for. One `Flux` per
    /// frame decoded by this worker, so it is constant in the region size.
    flux: Vec<(u16, Flux)>,
    /// Census of samples pinned at the container maximum. Two bytes per pixel,
    /// constant in the frame count, so the ratchet is untouched.
    clip: ClipCensus,
    /// The middle frame's flat and detail ROIs, kept by whichever worker
    /// decoded it. `flat` now feeds the LEGACY raw ratio only; the noise
    /// invariant references `flat_frames` instead.
    flat: Option<Vec<f32>>,
    /// `(frame index, flat-ROI moments)` for **every** frame. Three `f64` per
    /// frame, so it is constant in the ROI size and irrelevant to the ratchet.
    /// Fact 441: one privileged denominator moves the published ratio 1.60x, so
    /// there is no longer a privileged denominator to move.
    flat_frames: Vec<(u16, FrameFlat)>,
    /// Per-frame mean levels for the `auto` decision. One `f64` per frame, so
    /// it is constant in the frame size. Empty unless the mode is `auto`.
    drift: photometric::LevelDrift,
    t: Timings,
}

struct Pass2 {
    est: Vec<Estimator>,
    /// A compact gate-zero reference over only the two requested ROIs. It is
    /// read from the completed pass-one winner map and never touches `est`.
    selector: Option<SelectorRois>,
    /// The through-focus sufficient statistics, and their permutation placebo.
    /// Both `None` unless `--stats` was passed.
    tf: Option<ThroughFocus>,
    placebo: Option<ThroughFocus>,
    t: Timings,
}

fn map_dim_err(index: u16, e: Error) -> anyhow::Error {
    match e {
        Error::DimensionMismatch { got, want, .. } => {
            anyhow::anyhow!("frame {index} has plane geometry {got:?}, expected {want:?}")
        }
        other => anyhow::anyhow!(other),
    }
}

/// Environment override naming the warp sidecar the merge must consume.
///
/// [`align_cmd::load_or_solve`] discovers a sidecar *beside the capture* and
/// caches a fresh solve there on a miss. That is the right behaviour for a
/// cache, but it cannot serve three things M97 needs:
///
///   1. **A sidecar that is not the one the solver would produce.** Every
///      planted control here — jittered placements, an identity map, a map
///      belonging to a different bracket — is a file, and the merge has to be
///      pointable at it.
///   2. **A read-only corpus.** The caching write lands inside the capture
///      directory, so merely *rendering* a bracket mutates it. Measured: it
///      created `warpmap.txt` under two of the owner's captures. When this
///      variable is set nothing is written anywhere.
///   3. **Refusal instead of recovery.** `load_or_solve` answers a bad sidecar
///      by re-solving, which is correct for a cache and wrong for a file the
///      operator named: silently rendering a *different* registration than the
///      one requested would make every control here unfalsifiable. Every
///      failure below is therefore hard.
pub const WARPMAP_ENV: &str = "STREHL_WARPMAP";

/// Resolve the bracket's registration: an explicitly named sidecar if
/// [`WARPMAP_ENV`] is set, otherwise the normal discover-or-solve path.
///
/// `resampler` is what `--resampler` asked for. It reaches the gather only
/// through the solve path, because a named sidecar already records the kernel it
/// was solved with and that record wins — the merge gathers with
/// `map.resampler()`. That is deliberate (it is the method M118's D4 depends
/// on), so the disagreement is **reported** rather than either silently
/// dropped or turned into a refusal that would break an existing measurement
/// route.
/// Say which channel chose the coverage mode, but **only when one did**.
///
/// Silent on [`SettingSource::Default`], which is every run that does not
/// mention `--cover` or `STREHL_COVER`, so the default banner is exactly the
/// banner it was before this mode existed. When somebody does ask, the run's
/// own record has to name the channel: an argv records what the caller said and
/// only the run can record what it resolved, and those differ exactly when a
/// default is doing the work.
fn cover_mode_line(opts: &MergeOptions) {
    if !opts.cover_source.asked() {
        return;
    }
    eprintln!(
        "coverage mode   : {} -- {}",
        opts.cover.name(),
        opts.cover_source
            .describe(align_cmd::COVER_FLAG, align_cmd::COVER_ENV)
    );
}

fn alignment_for(
    dir: &Path,
    paths: &[PathBuf],
    resampler: Resampler,
) -> Result<Option<(WarpMap, &'static str)>> {
    let Some(explicit) = std::env::var_os(WARPMAP_ENV) else {
        return align_cmd::load_or_solve(dir, paths, 0, resampler);
    };
    // `STREHL_ALIGN=0` still wins, so an unregistered baseline can be rendered
    // without first unsetting the override.
    if !align_cmd::align_enabled() {
        return Ok(None);
    }
    let path = PathBuf::from(explicit);
    let map = WarpMap::load(&path).with_context(|| {
        format!(
            "loading the warp sidecar named by {WARPMAP_ENV}: {}",
            path.display()
        )
    })?;
    let name = dir
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let identity = StackIdentity::from_paths(&name, paths)?;
    map.check_stack(&identity).with_context(|| {
        format!(
            "the sidecar named by {WARPMAP_ENV} ({}) was not fitted on this bracket",
            path.display()
        )
    })?;
    ensure!(
        map.len() == paths.len(),
        "the sidecar named by {WARPMAP_ENV} ({}) has {} frames but the bracket has {}",
        path.display(),
        map.len(),
        paths.len()
    );
    // Never silently. The sidecar's kernel is the one that gathers, so if it is
    // not the one asked for, say which won: a flag that parses and is then
    // ignored is indistinguishable from a flag that works, and this project has
    // shipped that failure before.
    if map.resampler() != resampler {
        eprintln!(
            "alignment      : --resampler asked for {resampler:?} but the sidecar named by \
             {WARPMAP_ENV} was solved with {:?}; THE SIDECAR WINS. Unset {WARPMAP_ENV} to \
             let --resampler choose.",
            map.resampler()
        );
    }
    Ok(Some((map, "sidecar-override")))
}

/// The environment variable that asks for an election map without a flag.
const ELECTION_ENV: &str = "STREHL_DUMP_ELECTION";

/// Where to write the election map, if anywhere: `--index-map` wins, then
/// [`ELECTION_ENV`].
///
/// Two mechanisms because they serve two callers. The flag mirrors
/// `argmax-baseline --index-map`, and those two subcommands exist to be
/// compared against each other, so an asymmetry between them is a thumb on the
/// scale — the same reasoning M104c applied to resolution and M109 to exposure.
/// The variable is for a harness that drives an already-fixed command line.
///
/// Whichever is used, the resolved path is **printed**. Rule 47 binds
/// environment variables into a hash record precisely because they are
/// invisible in the invocation, and an unprinted one is the input that makes a
/// frozen hash unreproducible later.
fn election_map_path(opts: &MergeOptions) -> Option<PathBuf> {
    if let Some(p) = &opts.index_map {
        return Some(p.clone());
    }
    let raw = std::env::var(ELECTION_ENV).ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        eprintln!("{ELECTION_ENV} is set but empty; not writing an election map");
        return None;
    }
    Some(PathBuf::from(trimmed))
}

/// Write the pass-one winner field as a single-channel 16-bit TIFF.
///
/// **Grid.** The **plane** grid, which is *half* sensor resolution in each axis
/// ([`PlaneGeometry::from_active`] divides by two): one election per 2x2 CFA
/// quad, because the focus field the election is computed on lives there. It is
/// therefore the same size as a binned render and half the size of a
/// `--demosaic`/`--srgb` one — to overlay it on the latter, scale by two.
///
/// **Values.** The literal 0-based frame index into the input order, which
/// `raw_paths` sorts by filename, so it is capture order and `--limit N` keeps
/// `0..N-1`. The range is `0..frames-1`, far below the 16-bit ceiling, so
/// autoscale before looking at it. `u16::MAX` is the never-decided sentinel and
/// is refused here rather than written, since a map containing it would be
/// silently misread as a frame index near 65535.
///
/// **This is debug output and it does not touch the merged image.** It is a
/// read of state pass one has already finished computing, taken before pass two
/// starts, so the byte-frozen path is unaffected whether or not it runs.
///
/// What it is for: a blob in the render is not distinguishable from real scene
/// content by appearance, but it should be distinguishable by *provenance*.
/// Adjacent pixels electing different frames inherit placements that differ by
/// the alignment track's frame-to-frame jitter, so election boundaries are
/// where local geometric incoherence is predicted. Correlating this map's
/// discontinuities against blob boundaries is a joint statistic between the
/// output and the merge's internal state — which a single unstacked frame
/// cannot score at all, because it has no election map.
fn write_election_map(path: &Path, best: &[u16], geom: PlaneGeometry) -> Result<()> {
    ensure!(
        best.len() == geom.pixels(),
        "winner field is {} long but the plane grid is {}x{}",
        best.len(),
        geom.width,
        geom.height
    );
    ensure!(
        best.iter().all(|&i| i != u16::MAX),
        "some pixels were never decided; the election map would be meaningless"
    );
    image_out::write_gray16(path, geom.width as u32, geom.height as u32, best)?;
    let hi = best.iter().copied().max().unwrap_or(0);
    eprintln!(
        "election map    : wrote {} ({}x{} u16 plane grid, indices 0..{hi})",
        path.display(),
        geom.width,
        geom.height
    );
    eprintln!();
    Ok(())
}

/// The environment variable that asks for an n_eff map without a flag.
const NEFF_ENV: &str = "STREHL_DUMP_NEFF";

/// Env-var twin of `--photometric`, for A/B harnesses that cannot edit argv.
const PHOTOMETRIC_ENV: &str = "STREHL_PHOTOMETRIC";

/// What `strehl stack` does when nobody says. **`On` since V-TONE.**
///
/// Named, rather than left as a literal in the match arm of
/// [`resolve_photometric_mode`], for the reason [`DEFAULT_MERGE_BACKEND`] is
/// named: the previous arrangement is what let the switch registry declare
/// this default `auto` while the code returned `Off`, a disagreement that hid
/// a measured +1415 DN of recoverable background artifact for as long as it
/// took someone to read the resolving line rather than the documentation.
/// A default that has one greppable site can be checked by grepping it.
pub const DEFAULT_PHOTOMETRIC_MODE: PhotometricMode = PhotometricMode::On;

/// Where a resolved setting actually came from, so a banner can distinguish a
/// value the caller ASKED for from one they merely GOT.
///
/// This exists because the photometric banner printed `on (unconditional, as
/// asked)` on the branch where nothing asked: no flag, no environment variable,
/// just the compiled-in default. "As asked" is a claim about the CALLER, and
/// emitting it unconditionally makes the run's own record of itself false.
///
/// That matters more here than the wording suggests. A banner is the only
/// durable record of what produced an artifact, and this project has already
/// lost the provenance of a shipped gallery by trusting a log that recorded a
/// setting without recording who chose it. An argv records what the caller
/// SAID; only the run's own report can record what the program RESOLVED. The
/// two differ exactly when a default is doing the work, which is the case a
/// reader is least able to reconstruct later and most likely to get wrong --
/// the `--fix-ca` banner says `(gear matched; default on)` for this reason and
/// this type is that habit made reusable.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingSource {
    /// A command-line flag named it. The caller asked, in the loudest channel.
    Flag,
    /// The environment twin named it and no flag was given. Setting an
    /// environment variable is still ASKING -- it is a quieter channel, not an
    /// absent one -- so this counts as asked, and is named so the reader knows
    /// which channel to look in when the command line does not explain the run.
    Env,
    /// Nothing named it. This is the compiled-in product default, and it is the
    /// one branch on which "as asked" is a lie.
    Default,
}

impl SettingSource {
    /// Did the caller actually ask, in either channel?
    ///
    /// Sole purpose: gate the phrase "as asked" so it cannot be printed on
    /// [`SettingSource::Default`].
    pub fn asked(self) -> bool {
        !matches!(self, Self::Default)
    }

    /// How to say the provenance out loud, given the flag and environment
    /// variable that carry this setting.
    ///
    /// Routed through [`SettingSource::asked`] deliberately, so that the phrase
    /// "as asked" has exactly one guard in the codebase and cannot be restored
    /// to the default branch by editing a match arm.
    pub fn describe(self, flag: &str, env: &str) -> String {
        if !self.asked() {
            return "THE DEFAULT -- nothing asked for it".to_string();
        }
        match self {
            Self::Flag => format!("as asked, {flag}"),
            Self::Env => format!("as asked, {env}"),
            Self::Default => unreachable!("the default is not asked, and returned above"),
        }
    }
}

/// Fraction of the reference frame admitted as "low detail".
const PHOTOMETRIC_DETAIL_Q: f64 = 0.40;

/// Luma quantile a pixel must EXCEED to be admitted. Low detail alone is not
/// background — an unlit subject is smooth too, and admitting it put the
/// region's spread at 62% of its mean on `bee-3-cpl`; requiring brightness as
/// well took that to 20%.
const PHOTOMETRIC_LUMA_Q: f64 = 0.60;

/// Erosion radius, in plane pixels, applied to the low-detail region.
///
/// Defocus spills light across a scattered mask's long perimeter and the fit
/// reads the spill as a brightness change that is not there. On a
/// flux-conserving blur sweep whose true answer is exactly zero, M99 measured
/// 3.63% spurious gain raw against a registered 2x bar — 168x over — and
/// 0.0000% after eroding. The radius should exceed the largest defocus blur
/// the bracket contains.
const PHOTOMETRIC_ERODE_PX: usize = 16;

/// Below this many surviving pixels the fit is refused rather than attempted.
const PHOTOMETRIC_MIN_PX: usize = 1024;

/// Resolve the photometric mode from the flag and the environment.
///
/// Precedence: `--photometric MODE` wins, then [`PHOTOMETRIC_ENV`], then the
/// default — which is **`On`**. It was `Off` until V-TONE.
///
/// M122 returned KEEP-OFF on K2, its no-harm criterion. K2 is a
/// high-frequency energy ratio over whole windows: it has no spatial argument,
/// so it cannot tell an artifact edge from a subject edge. V-TONE partitioned
/// that same statistic by distance to the election-map discontinuities, with
/// thresholds and reading rule registered before the slopes were computed, and
/// the loss is not in the picture:
///
/// | partition | k | 95% CI |
/// | --- | --- | --- |
/// | SUBJECT, no seam | 0.9957 | [0.9888, 1.0022] |
/// | SEAM, far background | 0.6647 | [0.5431, 0.7899] |
///
/// Subject texture away from seams is the *most* textured partition in the
/// frame (hf0 280.8 DN against 127.3 at seams) and it loses 0.4%, with a CI
/// spanning 1.00. 85.7% of the removed laplacian energy lies in the seam set,
/// and the removed-energy map forms closed loops that are pixel-for-pixel the
/// election patch boundaries. What the correction deletes is level speckle,
/// written by an election that picks a near-random frame per pixel out of
/// frames whose levels span 23.5%.
///
/// **Two caveats travel with this and must not be dropped.** V-TONE's
/// rule-verbatim verdict is MIXED, not CONFIRMED: its gradient-matched placebo
/// read k = 0.9886 against a registered bar of 0.99, missing by 0.0014, so the
/// discriminator keeps ~1.1% residual sensitivity to gradient magnitude
/// against a 33% seam effect. The substance holds; the margin was not earned.
/// And `k_background` = 1.0287 [1.0021, 1.0622] is **unexplained** — the
/// correction *raises* high-frequency energy away from both subject and seams.
/// Nothing should be built on that region until it is understood.
///
/// **An unrecognised spelling is an error in either channel.** The form this
/// replaces read the environment as `!v.is_empty() && v != "0"`, so
/// `STREHL_PHOTOMETRIC=off` turned the correction ON — a value whose plain
/// meaning is the exact opposite of its effect. That mattered less while the
/// default was off; with the default on, `off` is the only way to ask for the
/// old pipeline, and it has to mean it.
/// It also reports WHICH CHANNEL supplied the value -- flag, environment, or
/// the compiled-in default -- because the banner has to be able to say whether
/// anybody actually asked. Returning the two together, from one read, is what
/// keeps the reported provenance honest: a second, independent read could
/// disagree with the value in use, and a provenance line that disagrees with
/// its own run is worse than none.
pub fn resolve_photometric_mode(
    flag: Option<&str>,
) -> Result<(PhotometricMode, SettingSource)> {
    if let Some(v) = flag {
        let mode =
            PhotometricMode::parse(v).with_context(|| format!("reading --photometric {v:?}"))?;
        return Ok((mode, SettingSource::Flag));
    }
    match std::env::var(PHOTOMETRIC_ENV) {
        Ok(v) if !v.trim().is_empty() => {
            let mode = PhotometricMode::parse(&v)
                .with_context(|| format!("reading {PHOTOMETRIC_ENV}={v:?}"))?;
            Ok((mode, SettingSource::Env))
        }
        // Unset, empty, or not valid UTF-8: the default, and nobody asked.
        _ => Ok((DEFAULT_PHOTOMETRIC_MODE, SettingSource::Default)),
    }
}

/// Resolve the coverage mode from the flag and the environment.
///
/// Precedence, and it is the same one `--photometric` uses: the flag wins, then
/// [`align_cmd::COVER_ENV`], then [`align_cmd::DEFAULT_COVER_MODE`]. The source
/// comes back with the value from the same read, so a banner cannot report a
/// channel that did not supply the mode in use.
///
/// The flag cannot spell the measurement control `0`/`off` even though the
/// environment can. That asymmetry is deliberate: leaving the plane uncovered
/// produces an image with invented edges, which is a thing to measure and not a
/// thing to render, and a command line is the channel a caller reaches for when
/// they want output they intend to keep.
pub fn resolve_cover_mode(flag: Option<&str>) -> Result<(align_cmd::CoverMode, SettingSource)> {
    if let Some(v) = flag {
        let mode = align_cmd::CoverMode::parse(v)
            .with_context(|| format!("reading {} {v:?}", align_cmd::COVER_FLAG))?;
        return Ok((mode, SettingSource::Flag));
    }
    if let Some(mode) = align_cmd::cover_mode_from_env()? {
        return Ok((mode, SettingSource::Env));
    }
    Ok((align_cmd::DEFAULT_COVER_MODE, SettingSource::Default))
}

/// Where to write the n_eff map, if anywhere: `--n-eff-map` wins, then
/// [`NEFF_ENV`]. Same precedence and same printing rule as
/// [`election_map_path`], so the two maps behave identically.
/// Default state of the veil envelope: off.
///
/// It stays off until the flatness gate has a 26-subject gallery sharpness
/// delta behind it. A merge-path change that alters which samples enter the
/// average is exactly the kind that looks like a win on the subject it was
/// aimed at and softens the library — which is how `57e4554` cost 6.6%.
const DEFAULT_VEIL_ON: bool = false;

/// Whether the veil envelope runs, from `STREHL_VEIL`. `0` or `off` disables it.
///
/// This used to carry the winner-focus ceiling as its magnitude. It no longer
/// does: eligibility is now the debiased peak prominence against the merge's
/// own significance gate (see [`Estimator::veil_w`]), which takes its cut from
/// `--gate` and has no free parameter for this variable to set. A leftover
/// numeric value is therefore accepted as "on" and **said so out loud**, rather
/// than being silently ignored — a run whose command line still names a ceiling
/// that no longer exists would otherwise be attributed to the wrong
/// configuration later.
fn veil_enabled() -> bool {
    match std::env::var("STREHL_VEIL") {
        Err(_) => DEFAULT_VEIL_ON,
        Ok(v) if v.trim().eq_ignore_ascii_case("off") => false,
        Ok(v) => match v.trim().parse::<f32>() {
            Ok(x) if x.is_finite() && x == 0.0 => false,
            Ok(x) if x.is_finite() && x > 0.0 => {
                if (x - 1.0).abs() > f32::EPSILON {
                    eprintln!(
                        "veil: STREHL_VEIL={x} is read as ON. The magnitude is no \
                         longer a focus ceiling -- eligibility is the peak \
                         prominence against the --gate cut -- so this number \
                         selects nothing."
                    );
                }
                true
            }
            _ => {
                eprintln!(
                    "STREHL_VEIL={v:?} is not a non-negative number; \
                     leaving the veil off"
                );
                DEFAULT_VEIL_ON
            }
        },
    }
}

/// Default significance margin for the veil envelope, in single-frame sigmas.
const DEFAULT_VEIL_MARGIN: f32 = 3.0;

/// How far above the gated mean the envelope must sit before it is believed,
/// from `STREHL_VEIL_MARGIN`, in units of the single-frame noise sigma.
fn veil_margin() -> f32 {
    match std::env::var("STREHL_VEIL_MARGIN") {
        Err(_) => DEFAULT_VEIL_MARGIN,
        Ok(v) => match v.trim().parse::<f32>() {
            Ok(x) if x.is_finite() && x >= 0.0 => x,
            _ => {
                eprintln!(
                    "STREHL_VEIL_MARGIN={v:?} is not a non-negative number; \
                     using the default {DEFAULT_VEIL_MARGIN}"
                );
                DEFAULT_VEIL_MARGIN
            }
        },
    }
}

/// Default luminance floor, as a fraction of the estimated backdrop level.
const DEFAULT_VEIL_LUMA_FLOOR: f32 = 0.5;

/// Fraction of the backdrop below which no pixel may be raised, from
/// `STREHL_VEIL_FLOOR`.
fn veil_luma_floor() -> f32 {
    match std::env::var("STREHL_VEIL_FLOOR") {
        Err(_) => DEFAULT_VEIL_LUMA_FLOOR,
        Ok(v) => match v.trim().parse::<f32>() {
            Ok(x) if x.is_finite() && (0.0..=1.0).contains(&x) => x,
            _ => {
                eprintln!(
                    "STREHL_VEIL_FLOOR={v:?} is not a fraction in [0,1]; \
                     using the default {DEFAULT_VEIL_LUMA_FLOOR}"
                );
                DEFAULT_VEIL_LUMA_FLOOR
            }
        },
    }
}

fn n_eff_map_path(opts: &MergeOptions) -> Option<PathBuf> {
    if let Some(p) = &opts.n_eff_map {
        return Some(p.clone());
    }
    let raw = std::env::var(NEFF_ENV).ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        eprintln!("{NEFF_ENV} is set but empty; not writing an n_eff map");
        return None;
    }
    Some(PathBuf::from(trimmed))
}

/// Write the per-pixel `n_eff` field as a single-channel 16-bit TIFF.
///
/// **Grid.** The **plane** grid, identical to [`write_election_map`]'s: half
/// sensor resolution, one value per 2x2 CFA quad. The two maps are therefore
/// the same size and overlay pixel-for-pixel with no resampling, which is the
/// point — one says *which* frame won, this says *how many* frames the noise
/// gate could not separate from it.
///
/// **Values.** A literal frame count, starting at **1**: the winner is always
/// within tolerance of itself, so no decided pixel can read 0. The ceiling is
/// the u16 one, **65535**, which this refuses to saturate against — a value
/// outside `1..=frames` is rejected rather than written, because a clamped
/// count read as a real one would understate averaging exactly where averaging
/// was heaviest. In practice the range is `1..=frames_folded` and far below the
/// ceiling, so autoscale before looking at it.
///
/// **This is debug output and it does not touch the merged image.** It reads
/// state pass two has already finished computing.
///
/// What it is for: `n_eff` is the project's headline quality number and is
/// reported only as a scalar mean, yet the gate that reaches `n_eff = 3` spans
/// 0.7618 to 21.9934 across the corpus — a factor of 28.9 — so that mean is
/// averaging over structure nobody can currently see. It also tests a specific
/// hypothesis about the "waxy blob" artefact: that the gate admits frames on a
/// focus-measure test while validity actually requires PSF similarity, so in
/// smooth defocused regions it averages frames whose PSFs differ and produces
/// extra blur. That predicts n_eff high and near-constant inside a blob with a
/// jump at its boundary, which this map either shows or refutes.
fn write_n_eff_map(path: &Path, n_eff: &[u16], frames: u32, geom: PlaneGeometry) -> Result<()> {
    ensure!(
        n_eff.len() == geom.pixels(),
        "n_eff field is {} long but the plane grid is {}x{}",
        n_eff.len(),
        geom.width,
        geom.height
    );
    let hi = n_eff.iter().copied().max().unwrap_or(0);
    let lo = n_eff.iter().copied().min().unwrap_or(0);
    ensure!(
        lo >= 1,
        "some pixels averaged 0 frames; the n_eff map would be meaningless"
    );
    ensure!(
        u32::from(hi) <= frames,
        "n_eff reaches {hi} but only {frames} frames were folded; the field is not a frame count"
    );
    image_out::write_gray16(path, geom.width as u32, geom.height as u32, n_eff)?;
    let mean = n_eff.iter().map(|&v| f64::from(v)).sum::<f64>() / n_eff.len() as f64;
    eprintln!(
        "n_eff map       : wrote {} ({}x{} u16 plane grid, counts {lo}..{hi}, mean {mean:.3})",
        path.display(),
        geom.width,
        geom.height
    );
    eprintln!();
    Ok(())
}

/// Resolve [`strehl_core::merge::SOFT_GATE_ENV`] once, **before any frame is
/// decoded**, on whichever backend is about to run.
///
/// **SCOPE, because this is a reachability claim and those have cost this
/// project whole investigations** (`optics.rs:317` documented `compose` as
/// uncalled while two live call sites existed). This function makes the pyramid
/// backend **validate** the kernel name. It does **not** make the pyramid
/// backend *apply* the kernel: that is `BandMerge::enable_soft`, which is not
/// landed at the time of writing. So on the pyramid backend a correctly-spelled
/// `gaussian` currently exits 0 and renders the shipped selection, unchanged.
/// Grep `enable_soft` before believing otherwise -- if it has no call site in
/// `merge_cmd.rs`, this paragraph is still current.
///
/// This closes an asymmetry, not a parse bug. The kernel name was validated on
/// exactly one path -- `Estimator::new`, which `panic!`s -- and the pyramid
/// backend, which is the shipped default, never read the variable at all.
/// MEASURED on `coffee-bubbles -l 3 --srgb` against a binary built and pinned
/// from a `git archive` of pristine `ec96973d`. It must be a private pristine
/// build: this tree is shared by roughly a dozen lanes, and the same table run
/// against a binary built from the *working* tree reads `742A6331..` where
/// pristine `ec96973d` reads `C9A93201..`, so an arm compared against anything
/// but its own matched build measures other lanes' drift.
///
/// ```text
/// STREHL_SOFT_GATE   pyramid (SHIPS)            estimator --photometric off
/// unset              rc=0  C9A93201..           rc=0  BBF38DD4..
/// gaussian           rc=0  C9A93201..  SAME     rc=0  00D8BFE3..  differs
/// exponential        rc=0  C9A93201..  SAME     rc=0  F496B5A7..  differs
/// zzznope            rc=0  C9A93201..  SAME     rc=101 panic in 3.4 s
/// ```
///
/// The estimator column is the control: it moves, so the harness could see a
/// change if there were one, and the pyramid column's single hash is a real
/// zero rather than a blind comparator. A typo exited 0 and rendered normally
/// on the backend that ships -- the same failure `MergeBackend::parse` refuses
/// for the flag channel, because a flag that parses and does nothing is
/// indistinguishable from one that works.
///
/// Placed on the shared dispatch so **both** backends refuse the same value.
/// On the estimator that also converts an rc=101 panic into the ordinary rc=1
/// `anyhow` error every other bad setting produces, by arriving first; the
/// `panic!` stays where it is as a library-level invariant for direct API
/// callers who bypass the CLI. Like [`align_cmd::preflight_ca_profile`] this
/// asks the question once and throws the answer away, so the per-use re-read
/// contract on [`strehl_core::merge::active_kernel`] is untouched.
pub fn preflight_soft_kernel() -> Result<()> {
    strehl_core::merge::active_kernel()?;
    Ok(())
}

/// Run the merge the options selected.
///
/// **The dispatch is the point.** Both merges are compiled and both are
/// reachable; which one ran is decided here, printed on stderr by the arm that
/// runs, and settable from one flag. Before this existed, `pyramid` was 1898
/// lines of compiled, tested, unreachable code and `blend-render` -- an example
/// binary that ships nothing -- was the only way to run it.
pub fn run(opts: &MergeOptions) -> Result<()> {
    preflight_soft_kernel()?;
    ensure!(
        opts.split_out.is_none() || opts.backend == MergeBackend::Pyramid,
        "--split-out is available only with --merge pyramid"
    );
    match opts.backend {
        MergeBackend::Pyramid => run_pyramid(opts),
        MergeBackend::Estimator => run_estimator(opts),
    }
}

/// Refuse to run a backend that would silently drop a configured defect
/// correction.
///
/// # The seam this guards
///
/// `strehl-cli` has **two independent frame loaders**: [`load_frame`], which
/// the pyramid merge uses, and `field_for`/`Scratch`, which the estimator uses.
/// The defect correction was added to the first. It is therefore *absent* from
/// the second, and absent silently — the estimator would print the same
/// "defect map" banner, decode the same frames, and produce an uncorrected
/// render.
///
/// **This is a guard over the seam, not a fix of it.** The seam is
/// architectural and the next per-frame correction anyone adds will hit it too;
/// it is recorded as a finding in its own right in
/// `docs/research/BUILD-DEFECT.md` §6.2.2. What this function buys is that the
/// failure is loud.
///
/// # Why here
///
/// A configured-but-unapplied correction is the precise failure this project
/// exists to catch, so it must not be reachable, and the refusal must not be
/// mistakable for a warning: it returns `Err` and the process exits non-zero.
/// It fires **before any frame is decoded**, because a refusal that surfaced
/// after 53.4 s of decoding reads as a slow arm in a matrix rather than as a
/// configuration error.
///
/// # Why it takes the backend rather than the options
///
/// So that the *supporting* backend is inside the function's domain and can be
/// asserted on. A refusal tested only in the arm where it fires is a refusal
/// with no negative control: it cannot distinguish "refuses when the correction
/// would be dropped" from "refuses always". Passing `Pyramid` here must return
/// `Ok` with a map configured, and that is a `#[test]`.
fn preflight_defect_backend_support(backend: MergeBackend) -> Result<()> {
    if backend != MergeBackend::Estimator {
        return Ok(());
    }
    let req = crate::stack::defect_request_from_env()?;
    if !req.wants_correction() {
        return Ok(());
    }
    let (correction, _) = crate::stack::defect_arms_from_env()?;
    if correction.is_noop() {
        return Ok(());
    }
    let source = match &req {
        crate::stack::DefectRequest::Sidecar(p) => format!("STREHL_DEFECT_MAP={}", p.display()),
        _ => "the map embedded in this build".to_string(),
    };
    bail!(
        "REFUSING TO RENDER: the sensor defect correction was NOT applied.\n\
         \n\
         A correction is configured ({source}, arms `{correction}`), but the \
         `estimator` merge backend does not apply it. The estimator loads frames \
         through a different path from the one the correction is wired into, so \
         this render would silently contain the uncorrected dust.\n\
         \n\
         This is an error, not a warning; nothing was rendered. Either:\n\
         \x20 - run the `pyramid` backend, which applies the correction, or\n\
         \x20 - set STREHL_DEFECT=off to render without it deliberately."
    )
}

fn run_estimator(opts: &MergeOptions) -> Result<()> {
    // Same reason as the --n-eff-map refusal below: fail on configuration
    // before a frame is read. An invalid STREHL_FIX_CA otherwise surfaces only
    // after the first decode (53.4 s), which reads as a slow arm in a matrix.
    align_cmd::preflight_ca_profile()?;
    preflight_defect_backend_support(opts.backend)?;
    ensure!(!opts.gates.is_empty(), "at least one --gate is required");
    ensure!(
        opts.gates.iter().all(|g| g.is_finite() && *g >= 0.0),
        "gate thresholds must be finite and non-negative"
    );
    // n_eff is per-gate, so with several gates the map would silently be
    // gate[0]'s. Refused here, before a frame is read, for the same reason
    // --out refuses: a debug map labelled with the wrong gate is worse than no
    // map, because it looks like evidence.
    if n_eff_map_path(opts).is_some() {
        ensure!(
            opts.gates.len() == 1,
            "--n-eff-map writes one map but {} gates were given; n_eff is per-gate, so pick one",
            opts.gates.len()
        );
    }
    if opts.out.is_some() {
        ensure!(
            opts.gates.len() == 1,
            "--out writes one image, but {} gates were given; pick one",
            opts.gates.len()
        );
    }
    // Exposure is validated *here*, before a frame is read, because a refusal
    // must cost nothing. It is a viewing control and the linear output is the
    // measurement output, so asking for it without --srgb is an error and not
    // something to quietly drop: a user who believes they brightened the
    // measurement file and did not has no way to find out.
    let exposure = Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?;

    // ---- the plugin seam ---------------------------------------------------
    //
    // Resolved here: after the cheap validations, before a frame is read.
    // Registration CALIBRATES -- twelve 512x512 noise planes per operator --
    // so it is a measurement and costs about half a second for the reference
    // set. That is why it is behind `is_some()`: the default path never
    // constructs a registry, never draws a seed, and pays nothing. It is also
    // why the byte-freezes are safe. The default keeps the compiled-in
    // FOCUS_NOISE_SD, which is what they were baselined against.
    //
    // --stats is refused rather than ignored: `compute_with_fine` computes the
    // selection field and a second fine-radius field from ONE gradient pass,
    // and that pass is Tenengrad's. Running it under --focus would elect on
    // the shipped operator while the banner named a different one, which is
    // precisely the "flag accepted and silently ignored" failure this seam
    // exists to remove.
    let focus_registry = match &opts.focus {
        Some(_) => Some(crate::focus_plugin::reference_registry()?),
        None => None,
    };
    let focus_op = match (&opts.focus, &focus_registry) {
        (Some(name), Some(reg)) => {
            ensure!(
                !opts.stats,
                "--focus {name} cannot be combined with --stats: through-focus statistics share \
                 one gradient pass with the selection field, and that pass is the shipped \
                 operator's. Refused rather than ignored -- the alternative is a run that \
                 reports one operator and elects with another."
            );
            ensure!(
                edge_aware_arm() != EdgeArm::Layer,
                "--focus {name} cannot be combined with {EDGE_AWARE_ENV}=layer: the layered \
                 support path elects through a Tenengrad-specific entry point that takes no \
                 operator. Use the default acuity arm or {EDGE_AWARE_ENV}=0."
            );
            let entry = crate::focus_plugin::resolve(reg, name)?;
            let cal = entry.calibration();
            eprintln!(
                "focus operator  : {} (contributed, via strehl-plugin)",
                entry.id()
            );
            eprintln!(
                "  noise sd      : {:.7e} MEASURED by the host at registration \
                 ({} seeds, rel sem {:.3}%), k = {:.4} vs the compiled-in {:.6}",
                cal.response_sd(),
                cal.seeds(),
                100.0 * cal.relative_sem(),
                cal.k_against_host_constant(),
                strehl_core::merge::FOCUS_NOISE_SD,
            );
            eprintln!(
                "  gate           : --gate T means T*sqrt(2)*{:.7e} in THIS operator's response \
                 units, not the shipped one's. Fact 631: the two are not related by rescaling \
                 -- operators disagree about the winner on up to 71.5% of pixels at a matched \
                 gate, so a k-corrected gate does NOT reproduce the other operator's decisions.",
                cal.response_sd()
            );
            Some(entry)
        }
        _ => None,
    };

    let paths = crate::raw_paths(&opts.dir, opts.limit)?;
    let paths = only_frame(paths);
    ensure!(
        paths.len() < u16::MAX as usize,
        "{} frames exceeds the u16 winner-index range",
        paths.len()
    );
    let input_bytes: u64 = paths
        .iter()
        .filter_map(|p| std::fs::metadata(p).ok().map(|m| m.len()))
        .sum();

    let t_prologue = Instant::now();
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let prologue_secs = t_prologue.elapsed().as_secs_f64();
    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let wb = first.wb_gains();
    // The camera's own characterisation, carried through the merge unused and
    // consumed only by the output path. `None` for a body `rawler` has no
    // entry for, which the writer reports rather than papers over.
    let xyz_to_cam = first.xyz_to_cam_rgb_with_source();
    let frame_bytes = first.allocated_bytes();
    drop(first);

    let noise = profile::noise_model_for(&camera, iso, levels);
    let middle = (paths.len() / 2) as u16;

    for (label, roi) in [
        ("--flat-roi", opts.flat_roi),
        ("--detail-roi", opts.detail_roi),
    ] {
        if let Some(roi) = roi {
            ensure!(
                roi.x + roi.width <= geom.width && roi.y + roi.height <= geom.height,
                "{label} {},{},{},{} does not fit inside the {}x{} plane",
                roi.x,
                roi.y,
                roi.width,
                roi.height,
                geom.width,
                geom.height
            );
        }
    }

    let roi_bytes = match (opts.flat_roi, opts.detail_roi) {
        (Some(flat), Some(detail)) => {
            let flat_px = flat.width * flat.height;
            let detail_px = detail.width * detail.height;
            // One f32 value plus a conservative byte for `Vec<bool>` per
            // captured pixel, and one temporary f32 extraction buffer.
            5 * (flat_px + detail_px) + 4 * flat_px.max(detail_px)
        }
        _ => 0,
    };
    let plan = Plan::new(
        paths.len(),
        geom,
        frame_bytes,
        opts.gates.len(),
        if opts.stats {
            1 + usize::from(opts.stats_placebo)
        } else {
            0
        },
        roi_bytes,
    );

    // The placebo permutation. Fixed, auditable and reproducible.
    //
    // NOT a rotation. `k -> (k + n/3) mod n` was the first draft and it is an
    // isometry of the index line, so adjacency survives and the placebo returned
    // exactly 1.0000x of the real reading -- a null that had silently become a
    // copy of its own subject. A seeded shuffle is the fix; the core test
    // `shuffle_destroys_adjacency_which_a_rotation_does_not` holds the line.
    let perm: Vec<u16> = shuffled_indices(paths.len(), PLACEBO_SEED);

    eprintln!("{}", merge_banner(MergeBackend::Estimator));
    eprintln!("camera          : {camera}");
    eprintln!("lateral CA      : {}", ca_status_line(&paths[0]));
    eprintln!(
        "iso             : {}",
        iso.map(|v| format!("{v:.0}")).unwrap_or("UNKNOWN".into())
    );
    eprintln!(
        "levels          : black {}, white {}",
        levels.black, levels.white
    );
    eprintln!("{}", provenance_line(&noise));

    eprintln!(
        "regulariser     : {REGULARISER_WIDTH}x{REGULARISER_WIDTH} box on the focus field \
         (fact 84: -35% absolute error; fact 86: width 3 is WORSE than none)"
    );
    // The scale the gate is ACTUALLY denominated in on this run. Printing the
    // compiled-in constant unconditionally would have been a provenance line
    // that disagrees with the run, which this file elsewhere calls worse than
    // no provenance line at all -- and under --focus it would be wrong by up
    // to 6.6x.
    match focus_op {
        None => eprintln!(
            "focus noise sd  : {FOCUS_NOISE_SD:.6} on the regularised field, MEASURED in-crate \
             (facts 310-313)"
        ),
        Some(op) => eprintln!(
            "focus noise sd  : {:.6} on the regularised field, MEASURED by the host for \
             `{}` at registration (NOT the compiled-in {FOCUS_NOISE_SD:.6})",
            op.calibration().response_sd(),
            op.id()
        ),
    }
    eprintln!(
        "gates           : {}  (UNCALIBRATED -- question 90; target is fact 212's nwide = 3)",
        opts.gates
            .iter()
            .map(|g| format!("{g:.2}"))
            .collect::<Vec<_>>()
            .join(", ")
    );
    eprintln!(
        "planes          : {} x {} per CFA plane",
        geom.width, geom.height
    );
    eprintln!(
        "frames          : {} from {}",
        paths.len(),
        opts.dir.display()
    );
    eprintln!("{}", plan.describe());

    // ---- alignment --------------------------------------------------------
    //
    // Solved (or loaded) before either pass, because both passes must see the
    // same geometry. M86 fact: every bracket in this corpus drifts far past
    // T_usable, so this is on by default; `STREHL_ALIGN=0` turns it off.
    cover_mode_line(opts);
    let t_align = Instant::now();
    let alignment = alignment_for(&opts.dir, &paths, opts.resampler)?;
    let alignment = alignment.map(|(m, how)| {
        let (m, fit) = align_cmd::cover_or_explain(m, opts.cover);
        (m, how, fit)
    });
    match &alignment {
        Some((map, how, fit)) => {
            let p = map.provenance();
            eprintln!(
                "alignment      : ON ({how}), reference frame {}, {} placed / {} refused",
                p.reference,
                map.placed_count(),
                map.refused_count()
            );
            if p.strategy.contains("zoom-only null") {
                eprintln!(
                    "  *** ZOOM-ONLY NULL CONTROL: relative registration has been DISCARDED. \
                     This render pays the resampling cost and has the aligned field of view \
                     but is NOT aligned. It exists to be compared against. ***"
                );
            }
            eprintln!(
                "  held-out err  : {}   cycle floor: {}",
                p.heldout_px
                    .map(|e| format!("{e:.3} px"))
                    .unwrap_or("NOT MEASURED".into()),
                p.cycle_floor_px
                    .map(|f| format!("{f:.3} px"))
                    .unwrap_or("NOT MEASURED".into()),
            );
            eprintln!(
                "  resampler     : {:?}   solve took {:.1} s",
                map.resampler(),
                t_align.elapsed().as_secs_f64()
            );
            match fit {
                // The crop arm deliberately shares no phrase with the scale
                // arm below. Around thirty harnesses in `experiments/` regex
                // `field of view scaled to ([0-9.]+)` out of this line and
                // divide by it to compare spectra at matched sensor bandwidth;
                // a crop render has no such factor, and a line they could
                // half-match would feed them a correction that does not apply.
                align_cmd::CoverFit::Cropped { k, rect } => {
                    eprintln!("{}", align_cmd::crop_banner(*k, *rect, map.geometry()))
                }
                align_cmd::CoverFit::Scaled(k) if *k >= 0.999_999 => {
                    eprintln!("  coverage      : every frame covers the whole grid; no crop needed")
                }
                align_cmd::CoverFit::Scaled(k) => eprintln!(
                    "  coverage      : field of view scaled to {:.4} so that EVERY frame covers \
                     every pixel ({:.1}% of width dropped, then upsampled to keep the output \
                     dimensions). Without this the render is part black.",
                    k,
                    100.0 * (1.0 - k)
                ),
                align_cmd::CoverFit::Uncovered => eprintln!(
                    "  coverage      : WARNING -- could not fit a fully covered grid; the render \
                     may contain black regions where no frame reaches."
                ),
            }
            if p.heldout_px.is_none() {
                eprintln!(
                    "  WARNING       : this solve could not certify itself. The held-out \
                     protocol needs long-span edges (M10: span >= 40, >= 12 surviving) and \
                     this stack's edge set did not supply them, so the registration below \
                     is UNVERIFIED. Run `strehl align` with a richer span set to get a \
                     sidecar that carries an error bar."
                );
            }
            if let Some(e) = p.heldout_px
                && e > 4.0
            {
                eprintln!(
                    "  NOTE          : {e:.3} px is above M86's T_usable of 4.0 px -- a large \
                     improvement on no registration, but not a precise solve."
                );
            }
            if p.heldout_px.is_some() {
                // Printed whenever a solve certifies itself, INCLUDING when the
                // number looks good. M97 fact 1295: the held-out score is a
                // *pairwise* residual, so it is blind to a gain shared by every
                // edge -- an 11.56 px E* coexisted with only 54.3% of the drift
                // being applied. A small E* is the case where this caveat
                // matters most, because it is the one that reads as success.
                eprintln!(
                    "  CAVEAT        : the held-out score is a pairwise residual and cannot \
                     detect a scale error common to every edge, so it bounds relative \
                     placement, not absolute magnification (M97, fact 1295)."
                );
            }
        }
        None => eprintln!(
            "alignment      : OFF -- frames are combined unregistered. M86 measured \
             232.7 px of drift on bee-3-cpl; expect softness that grows with radius."
        ),
    }
    eprintln!();

    let live = AtomicUsize::new(0);
    let peak_live = AtomicUsize::new(0);
    let warps = alignment.as_ref().map(|(m, _, _)| m);
    let ctx = Ctx {
        geom,
        levels,
        noise: &noise,
        live: &live,
        peak_live: &peak_live,
        warps,
        // Pass one runs UNCORRECTED: the gains are fitted from flux this pass
        // accumulates, so they cannot exist yet. That costs nothing, because
        // the correction is election-neutral by construction (M99 §13.2) --
        // the focus response is exactly invariant under it -- so a winner
        // elected on uncorrected data is the same winner.
        photometric: None,
        // Only `auto` needs a drift reading, and it needs it from every frame
        // pass one decodes. Pass two re-uses this Ctx with the field left as
        // it is, but pass two never reads `scratch.drift_level`, so the
        // reading is taken once per frame and not twice.
        measure_drift: opts.photometric == PhotometricMode::Auto,
        support: None,
        scale: None,
        guide_radius: None,
        // Pass zero -- the depth guide -- deliberately keeps the SHIPPED
        // operator even under --focus. The guide is not the election: it
        // solves a per-pixel selection RADIUS from a deliberately narrow
        // window, and that solve was calibrated against Tenengrad's response.
        // Substituting an operator whose scale is 6.6x different would move
        // the radius map for reasons that have nothing to do with the
        // contributed measure. `ctx_guide` below therefore inherits this
        // `None` and cannot pick the operator up by accident.
        focus_op: None,
    };

    // ---- pass zero: the depth guide, and the adaptive radius it solves -----
    //
    // Skipped only when explicitly switched off for an A/B arm.
    let mut acuity: Option<edgeaware::SelectionScale> = None;
    // The veil USED to gate on the veto's prominence field. It no longer does:
    // that gate was borrowed from `--gate`, which states when averaging is safe
    // and carries no information about veiling, and it inverted on the first
    // out-of-sample subject it met (BUILD-HALO.md sec 32). The veil now gates on
    // election incoherence, which is derived from the image's own distribution.
    // The prominence field survives here only as a printed diagnostic.
    let layer_support: Option<LayerSupport> = if edge_aware_arm() != EdgeArm::Off {
        let t0 = Instant::now();
        let ctx_guide = Ctx {
            guide_radius: Some(GUIDE_RADIUS),
            measure_drift: false,
            ..ctx
        };
        // Mode statistics are folded unconditionally now: the same accumulator
        // that answers "is this pixel bimodal" is the one mandate (B) gates on,
        // and folding it only when a dump was requested made the detector
        // something you had to opt into to find out whether you needed it.
        let (guide, guide_resp, modes, gt) =
            guide_winner_field(&paths, &plan, &ctx_guide, geom, true)?;
        let tau = edge_tau(&guide);
        eprintln!("--- pass zero: depth guide for the edge-aware election (MEASURED) ---");
        eprintln!(
            "guide radius    : {GUIDE_RADIUS} px box on |grad|, elected NARROW on purpose"
        );
        eprintln!(
            "depth tolerance : tau = {tau:.1} frames{}",
            if std::env::var(EDGE_TAU_ENV).is_ok() {
                "  (from the environment)"
            } else {
                "  (an eighth of this bracket's own robust winner span)"
            }
        );

        if edge_aware_arm() != EdgeArm::Off {
            // The veto. `peak_excess` is the prominence of a separated secondary
            // peak in the pixel's own through-focus curve, already folded on the
            // NARROW guide field during the pass above at no extra decode, and
            // already debiased: the maximum of n noisy responses stands above
            // the truth by ~sd*sqrt(2 ln n) even with no peak at all, which at
            // 299 frames is 3.4 sd of pure artefact. Subtracting that makes zero
            // mean "no resolvable peak".
            //
            // Consumed as proof of ABSENCE, which is the only direction a
            // prominence upper bound supports. Gating *on* it read 45.62% of the
            // plane including empty sky; refusing to collapse where it proves
            // there is no second layer is the same statistic used the way it can
            // be trusted.
            //
            // The cut is the merge's own significance gate rather than a new
            // constant: a secondary peak counts as resolvable at exactly the
            // confidence every other noise-model decision in this engine
            // requires.
            let excess = modes
                .as_ref()
                .map(edgeaware::BimodalStats::peak_excess)
                .unwrap_or_else(|| vec![f32::INFINITY; geom.pixels()]);
            let cut = opts.gates.iter().copied().fold(f32::INFINITY, f32::min);
            {
                // Retained as a DIAGNOSTIC, not as a gate. This distribution is
                // the evidence for BUILD-HALO.md sec 32: `first_mode_z`'s median
                // is 2.97 on `flower-bud` but exactly 4.00 on `coffee-bean`, so
                // a fixed 4.0 cut admits most of one image and the COMPLEMENT of
                // the target population in the other. Printing the quantiles is
                // what made that visible; a single "admitted %" could not have,
                // and reasoning about the scale of a quantity instead of
                // measuring it is how a gate ends up either inert or universal.
                let mut v = modes
                    .as_ref()
                    .map(edgeaware::BimodalStats::first_mode_z)
                    .unwrap_or_default();
                v.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
                let q = |f: f64| v[(((v.len() - 1) as f64) * f).round() as usize];
                eprintln!(
                    "peak significance: p10 {:.2} p25 {:.2} p50 {:.2} p75 {:.2} p90 {:.2} \
                     p99 {:.2} max {:.2} sigma  (diagnostic; the veil does NOT gate on this)",
                    q(0.10), q(0.25), q(0.50), q(0.75), q(0.90), q(0.99), q(1.0)
                );
            }
            let may: Vec<bool> = excess.iter().map(|&e| e > cut).collect();
            let admitted = may.iter().filter(|&&m| m).count();
            eprintln!(
                "collapse veto   : a resolvable second layer at gate {cut:.1} sigma. \
                 {admitted} px admitted ({:.2}% of plane); the rest keep the shipped window \
                 because there is provably nothing there for a narrow window to separate",
                100.0 * admitted as f64 / geom.pixels() as f64
            );
            let mut scale = edgeaware::SelectionScale::from_silhouettes(&guide, &may, geom, tau);
            let shrink = acuity_shrink();
            if shrink {
                scale.tighten_by_acuity(&excess, ACUITY_MARGIN);
            }
            let hist = scale.histogram();
            if shrink {
                eprintln!(
                    "radius rule     : min(r_noise, r_geom). r_geom is distance to the nearest \
                     depth step; r_noise is the smallest radius whose noise floor still resolves \
                     this pixel's own peak, margin {ACUITY_MARGIN:.1} sigma against \
                     FOCUS_NOISE_SD scaled from radius {}",
                    strehl_core::focus::WINDOW_RADIUS
                );
            } else {
                eprintln!(
                    "radius rule     : distance to the nearest depth step, capped at the shipped \
                     {} px. NO noise-driven shrink ({ACUITY_ENV}=0)",
                    strehl_core::focus::WINDOW_RADIUS
                );
            }
            eprintln!(
                "  by radius     : {}",
                hist.iter()
                    .enumerate()
                    .map(|(l, n)| format!(
                        "r{} {:.2}%",
                        edgeaware::LEVEL_RADII[l],
                        100.0 * *n as f64 / geom.pixels() as f64
                    ))
                    .collect::<Vec<_>>()
                    .join("  ")
            );
            eprintln!(
                "  mean radius   : {:.2} px  (shipped is a flat {} px)",
                scale
                    .levels()
                    .iter()
                    .map(|&l| edgeaware::LEVEL_RADII[l as usize] as f64)
                    .sum::<f64>()
                    / geom.pixels() as f64,
                strehl_core::focus::WINDOW_RADIUS
            );
            eprintln!(
                "regulariser     : guided by each frame's OWN luma at sigma_s = {REGULARISER_RADIUS} \
                 px, replacing the radius-{REGULARISER_RADIUS} box"
            );
            eprintln!(
                "wall clock      : {:.3} s  (decode {:.1} s, work {:.1} s summed across workers)",
                t0.elapsed().as_secs_f64(),
                gt.decode,
                gt.work
            );
            eprintln!();
            if let Some(dir) = bimodal_dump() {
                if let Some(m) = modes.as_ref() {
                    report_bimodality_scaled(m, &scale, &guide, geom, &dir)?;
                }
            }
            acuity = Some(scale);
            None
        } else {
            let conf = edge_conf();
            let radii = [strehl_core::focus::WINDOW_RADIUS, REGULARISER_RADIUS];
            let support = LayerSupport::from_guide(&guide, &guide_resp, geom, tau, conf, &radii);
            let hist = support.histogram();
            eprintln!(
                "confidence veto : {conf:.1}x the {:.0}th-percentile guide response, so ground with \
                 no sharp content in reach is left alone",
                100.0 * f64::from(edgeaware::FLOOR_Q)
            );
            eprintln!(
                "support masked  : {} of the plane elects on its own depth layer only, at the \
                 UNCHANGED {} px radius",
                format_args!("{:.2}%", 100.0 * support.treated_fraction()),
                strehl_core::focus::WINDOW_RADIUS
            );
            eprintln!(
                "  by layer      : {}",
                hist.iter()
                    .enumerate()
                    .map(|(l, n)| format!(
                        "L{l} {:.2}%",
                        100.0 * *n as f64 / geom.pixels() as f64
                    ))
                    .collect::<Vec<_>>()
                    .join("  ")
            );
            eprintln!(
                "wall clock      : {:.3} s  (decode {:.1} s, work {:.1} s summed across workers)",
                t0.elapsed().as_secs_f64(),
                gt.decode,
                gt.work
            );
            eprintln!();
            if let (Some(m), Some(dir)) = (modes.as_ref(), bimodal_dump()) {
                report_bimodality(m, &support, &guide, geom, &dir)?;
            }
            (!support.is_empty()).then_some(support)
        }
    } else {
        None
    };
    // Pass two is the election, and this is where the contributed operator
    // enters. Both `compute` and `compute_scaled` have a `_with_measure`
    // sibling that `Ctx::field_for` dispatches to when this is `Some`.
    let ctx = Ctx {
        support: layer_support.as_ref(),
        scale: acuity.as_ref(),
        focus_op,
        ..ctx
    };

    // A refused frame is dropped, not merged unregistered. Counted once here so
    // every pass agrees on the denominator; skipping is done per pass via
    // `Ctx::is_refused`.
    let refused: Vec<u16> = (0..paths.len() as u16).filter(|i| ctx.is_refused(*i)).collect();
    let expected = paths.len() - refused.len();
    if !refused.is_empty() {
        let shown: Vec<String> = refused.iter().take(8).map(|i| i.to_string()).collect();
        eprintln!(
            "alignment      : DROPPING {} of {} frames the solve could not place: {}{}",
            refused.len(),
            paths.len(),
            shown.join(", "),
            if refused.len() > shown.len() {
                format!(", +{} more", refused.len() - shown.len())
            } else {
                String::new()
            }
        );
        eprintln!(
            "                 Their geometry is unknown, so merging them would put \
             mis-registered frames into the election."
        );
        eprintln!();
    }
    ensure!(
        expected > 0,
        "the alignment solve refused all {} frames; there is nothing to merge",
        paths.len()
    );

    // ---- the fixed photometric region -------------------------------------
    //
    // Built ONCE, from the reference frame, and then held fixed. A region
    // re-chosen per frame slides across the scene as magnification breathes
    // and re-acquires the exact confound the correction exists to remove.
    //
    // Whole-frame flux is the wrong corrector. M99 §7.3 measured whole-frame
    // and background ladders 7.1% and 5.5% apart on the two auto-exposure
    // decks -- the AE meter holds TOTAL flux roughly constant while defocus
    // moves light between the sharp core and the smooth surround -- and
    // correcting with the whole-frame ladder left 44% and 42% of the defect
    // standing. M28 §6's "mean over all pixels" rule is right about the
    // STATISTIC (a mean, never a median: M99 measured 368x between them) and
    // wrong about the region on an AE deck. Its real warning was against a
    // *subject-centred* region; this one is deliberately subject-avoiding.
    //
    // Then eroded, because the threshold mask is scattered and its perimeter
    // is long: defocus spills light across that perimeter and the estimator
    // reads the spill as a brightness change that is not there. M99 measured
    // 3.63% spurious gain on a flux-conserving blur sweep whose true answer is
    // zero, against a 2x bar -- 168x over. Erosion takes it to 0.0000%.
    let photometric_mode = opts.photometric;
    let photometric_source = opts.photometric_source;
    // `auto` has to build the region and fold the flux as if the correction
    // were on, because the drift it decides on cannot be known until pass one
    // has read every frame. If it then declines, the map is dropped and pass
    // two runs the uncorrected path -- byte-identically, which M125 proves by
    // hash rather than by argument.
    let photometric_wanted = matches!(
        photometric_mode,
        PhotometricMode::On | PhotometricMode::Auto
    );
    let mut auto_abstention: Option<photometric::AutoAbstention> = None;
    let photometric_region = if photometric_wanted {
        let mut t = Timings::default();
        let mut scratch = Scratch::new_with_warp(geom, false, warps.is_some());
        let frame = ctx.field_for(&paths[middle as usize], middle, &mut scratch, &mut t)?;
        ctx.release(frame);
        let mut raw = vec![false; geom.pixels()];
        let picked = photometric::low_detail_mask(
            &scratch.reg,
            &scratch.luma,
            PHOTOMETRIC_DETAIL_Q,
            PHOTOMETRIC_LUMA_Q,
            &mut raw,
        );
        let mut mask = vec![false; geom.pixels()];
        let kept = photometric::erode_mask(&raw, geom.width, PHOTOMETRIC_ERODE_PX, &mut mask);
        eprintln!("--- photometric normalisation (M99, ON BY DEFAULT since V-TONE) ---");
        eprintln!(
            "mode            : {} ({})",
            match photometric_mode {
                PhotometricMode::On => "on, unconditional",
                PhotometricMode::Auto =>
                    "auto, decides after pass one from this stack's drift",
                PhotometricMode::Off => unreachable!("off does not build a region"),
            },
            photometric_source.describe("--photometric", PHOTOMETRIC_ENV),
        );
        eprintln!(
            "region          : {picked} px low-detail on frame {middle}, {kept} px after \
             eroding {PHOTOMETRIC_ERODE_PX} px ({:.1}% kept)",
            100.0 * kept as f64 / picked.max(1) as f64
        );
        if kept < PHOTOMETRIC_MIN_PX {
            // U3. Under an explicit `on` this stays a hard error: the caller
            // asked for a correction that cannot be fitted, and quietly not
            // doing it would be the silent no-op this milestone exists to
            // remove. Under `auto` the caller asked for a DECISION, and "this
            // scene has no background" is a legitimate answer to that question
            // -- so it abstains, says why, and still renders. M122 measured
            // this hard exit on 112MSDCF (886 px) and coffee-bubbles (442 px).
            let why = photometric::AutoAbstention::RegionTooSmall {
                kept,
                minimum: PHOTOMETRIC_MIN_PX,
            };
            ensure!(
                photometric_mode != PhotometricMode::On,
                "{why}. Re-run without --photometric, or with --photometric auto, rather than \
                 fitting on a sliver."
            );
            eprintln!("AUTO: ABSTAINED  {why}");
            eprintln!(
                "                  falling back to the default (off) LOUDLY, not silently. \
                 The render continues and is byte-identical to --photometric off."
            );
            eprintln!();
            auto_abstention = Some(why);
            None
        } else {
            Some(mask)
        }
    } else {
        None
    };

    // ---- pass one: regularised winner field -------------------------------
    let t1 = Instant::now();
    let p1 = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(ci, chunk)| -> Result<Pass1> {
            let first_index = (ci * plan.chunk_len) as u16;
            let mut stats = FocusStats::new(geom);
            let mut clip = ClipCensus::new(geom);
            let mut scratch = Scratch::new_with_warp(geom, false, warps.is_some());
            let mut flat = None;
            let mut flat_frames: Vec<(u16, FrameFlat)> = Vec::with_capacity(chunk.len());
            let mut flux: Vec<(u16, Flux)> = Vec::new();
            let mut drift = photometric::LevelDrift::new();
            let mut t = Timings::default();

            for (offset, path) in chunk.iter().enumerate() {
                let index = first_index + offset as u16;
                if ctx.is_refused(index) {
                    continue;
                }
                let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                // Read before `release`, and only ever `Some` under `auto`.
                // A frame whose level could not be read is simply not pushed:
                // `LevelDrift` then folds a smaller stack, and if that leaves
                // nothing the decision abstains rather than guessing.
                if let Some(level) = scratch.drift_level {
                    drift.push(level);
                }
                if let Some(r) = opts.flat_roi {
                    // Every frame, not only the middle one. The denominator of
                    // the noise invariant is the whole distribution (fact 441).
                    let g = roi_green(&frame, r, levels.black);
                    flat_frames.push((index, flat_ratio::frame_flat(&g, r.width, r.height)));
                    if index == middle {
                        flat = Some(g);
                    }
                }
                ctx.release(frame);
                if let Some(region) = photometric_region.as_deref() {
                    // Folded from the SAME luma the focus field was computed
                    // from, so the gain and the election describe one frame.
                    // No further intersection with warp coverage is needed:
                    // the merge fits the output grid so that every frame
                    // covers every pixel (the `fit_to_cover` enlargement), and
                    // an unregistered merge does not resample at all.
                    let mut f = Flux::new();
                    f.fold_covered(
                        &scratch.luma,
                        region,
                        f32::from(CONTAINER_MAX_DN) - levels.black,
                    );
                    flux.push((index, f));
                }
                stats
                    .fold(index, &scratch.reg)
                    .map_err(|e| map_dim_err(index, e))?;
                clip.fold(&scratch.clipped)
                    .map_err(|e| map_dim_err(index, e))?;
            }
            Ok(Pass1 {
                stats,
                clip,
                flat,
                flat_frames,
                flux,
                drift,
                t,
            })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                a.stats.absorb(&b.stats).map_err(|e| map_dim_err(0, e))?;
                a.clip.absorb(&b.clip).map_err(|e| map_dim_err(0, e))?;
                a.flat = a.flat.or(b.flat);
                a.flat_frames.extend(b.flat_frames);
                a.flux.extend(b.flux);
                a.drift.absorb(&b.drift);
                a.t.add(b.t);
                Ok(a)
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    let pass1_secs = t1.elapsed().as_secs_f64();

    ensure!(
        p1.stats.frames_folded() as usize == expected,
        "pass one folded {} frames, expected {}",
        p1.stats.frames_folded(),
        expected
    );

    if let Some(path) = election_map_path(opts) {
        write_election_map(&path, p1.stats.best_index(), geom)?;
    }
    if let Some(dir) = dump::dump_dir() {
        dump::write_u16(
            &dir.join("best_index.npy"),
            geom.width,
            geom.height,
            p1.stats.best_index(),
        )?;
        dump::write_f32(
            &dir.join("best_focus.npy"),
            geom.width,
            geom.height,
            p1.stats.best_focus(),
        )?;
        eprintln!(
            "merge state     : wrote best_index.npy + best_focus.npy to {} ({}x{} plane grid)",
            dir.display(),
            geom.width,
            geom.height
        );
        eprintln!();
    }

    let n = paths.len() as f64;
    eprintln!("--- pass one: regularised winner field (MEASURED) ---");
    eprintln!(
        "wall clock      : {pass1_secs:.3} s  ({:.1} ms/frame)",
        1000.0 * pass1_secs / n
    );
    eprintln!(
        "  decode        : {:.3} s summed across workers ({:.1} ms/frame)",
        p1.t.decode,
        1000.0 * p1.t.decode / n
    );
    eprintln!(
        "  focus + reg   : {:.3} s summed across workers ({:.1} ms/frame)",
        p1.t.work,
        1000.0 * p1.t.work / n
    );
    eprintln!();

    // ---- the auto decision ------------------------------------------------
    //
    // Made here, between the passes, because the drift cannot be known until
    // pass one has read every frame. `auto` therefore builds the region and
    // folds the flux as if the correction were on, and then either keeps the
    // map or drops it. Dropping it makes pass two byte-identical to `off`;
    // that is proved by SHA-256 in M125, not argued from this comment.
    //
    // Discipline 862: `unknown` must not collapse into `no`. Every path out of
    // here prints which of the three states it reached -- APPLIED, DECLINED, or
    // ABSTAINED with a numbered reason -- and an abstention falls back to the
    // default loudly. The precedent not to repeat is STREHL_FIX_CA, a
    // byte-identical no-op under STREHL_ALIGN=0 that says nothing at all.
    let auto_decision = if photometric_mode == PhotometricMode::Auto {
        let d = auto_abstention.map_or_else(
            || photometric::auto_decide(expected, p1.drift.dpp()),
            photometric::AutoDecision::Abstain,
        );
        eprintln!("--- photometric auto decision (M125) ---");
        eprintln!(
            "drift estimator : mean CFA G1 level over the active area, per frame, read before \
             registration and before any gain (M24's estimator, promoted)"
        );
        match p1.drift.dpp() {
            Some(dpp) => eprintln!(
                "measured drift  : {dpp:.4}% peak-to-peak over {} frame(s)",
                p1.drift.len()
            ),
            None => eprintln!(
                "measured drift  : UNAVAILABLE from {} folded frame(s)",
                p1.drift.len()
            ),
        }
        eprintln!(
            "threshold       : {:.2}% (leave-one-out over M122's 14-stack corpus; \
             pre-registered before scoring)",
            photometric::AUTO_DRIFT_THRESHOLD_PCT
        );
        match d {
            photometric::AutoDecision::Apply { drift_pct } => eprintln!(
                "AUTO: APPLIED    drift {drift_pct:.3}% is at or above the {:.2}% threshold",
                photometric::AUTO_DRIFT_THRESHOLD_PCT
            ),
            photometric::AutoDecision::Decline { drift_pct } => {
                eprintln!(
                    "AUTO: DECLINED   drift {drift_pct:.3}% is below the {:.2}% threshold",
                    photometric::AUTO_DRIFT_THRESHOLD_PCT
                );
                eprintln!(
                    "                  This is a DECISION on a measurement, not a failure to \
                     decide. The render is byte-identical to --photometric off."
                );
            }
            photometric::AutoDecision::Abstain(why) => {
                eprintln!("AUTO: ABSTAINED  {why}");
                eprintln!(
                    "                  falling back to the default (off) LOUDLY, not silently. \
                     The render is byte-identical to --photometric off."
                );
            }
        }
        eprintln!(
            "  CAVEAT        : the threshold's held-out margin over always-on is +0.0043 on \
             M122's B12n, and 104% of that margin is a single stack (bee-3-cpl). The rule \
             survives 12 of 14 single-subject deletions, and the training objective is flat \
             from 1.64% to 8.45%. This is enough to offer auto as opt-in and NOT enough to \
             move the default, which is why the default did not move."
        );
        eprintln!();
        Some(d)
    } else {
        None
    };

    // ---- the photometric fit ----------------------------------------------
    //
    // Fitted here, between the passes, because the gains cannot be known until
    // pass one has read every frame. Pass two then merges corrected data while
    // the gate compares against pass one's uncorrected winner field -- which is
    // legitimate precisely because the correction is election-neutral: the
    // corrected regularised response is the uncorrected one.
    let fit_region = match auto_decision {
        // `auto` declined or abstained: drop the region, and with it the map.
        Some(d) if !d.applies() => None,
        _ => photometric_region,
    };
    let photometric_map = match fit_region {
        None => None,
        Some(_) => {
            let mut per_frame: Vec<Flux> = (0..paths.len()).map(|_| Flux::new()).collect();
            let mut folded = 0usize;
            for (index, f) in &p1.flux {
                per_frame[*index as usize] = *f;
                folded += 1;
            }
            ensure!(
                folded == expected,
                "photometric flux was folded for {folded} frames but {expected} were merged"
            );
            let map = PhotometricMap::from_flux(&per_frame, middle as usize)
                .context("fitting the photometric gains")?;
            eprintln!("--- photometric fit (MEASURED) ---");
            eprintln!(
                "statistic       : MEAN over the region, never a median. M28 §6 and M99 both \
                 measured the statistic dominating the region -- 368x between them -- because a \
                 median over a subject-weighted area absorbs focus signal and calls it gain."
            );
            eprintln!(
                "reference       : frame {middle} (gain 1.0 by definition)\n\
                 gain span       : {:.4} (max/min across {} frames)",
                map.span(),
                map.len()
            );
            if map.refused_count() > 0 {
                eprintln!(
                    "  REFUSED       : {} frame(s) could not be fitted and are merged \
                     UNCORRECTED at gain 1.0, not dropped -- their geometry is still good. \
                     {}",
                    map.refused_count(),
                    (0..map.len())
                        .filter_map(|i| map.refusal(i).map(|why| format!("[{i}: {why}]")))
                        .take(4)
                        .collect::<Vec<_>>()
                        .join(" ")
                );
            }
            eprintln!(
                "  CAVEAT        : this corrects frame LEVEL. It is not a quality claim. M99's \
                 headline +6.88% early-decile figure was fitted over an UN-eroded region that \
                 leaks 3.63% of flux across its own perimeter, so that number is an inflated \
                 upper bound of unmeasured size and is not reproduced here."
            );
            // U4. The fit ran and produced nothing to apply. This is already a
            // byte-identical no-op -- every gain is exactly 1.0, and
            // `field_for` skips the scaling at gain 1.0 -- so nothing about the
            // render changes here. What changes is that it is now SAID. M122
            // measured this on `dry-erase-marker-head-cpl`, where all 100
            // frames were refused and the A0/A1 arms came out byte-identical,
            // and the previous code reported that as a successful correction.
            if photometric_mode == PhotometricMode::Auto
                && (map.span() == 1.0 || map.refused_count() == map.len())
            {
                let why = photometric::AutoAbstention::NoCorrectionAvailable {
                    refused: map.refused_count(),
                    frames: map.len(),
                };
                eprintln!("AUTO: ABSTAINED  {why}");
                eprintln!(
                    "                  the map is a no-op, so this render is byte-identical to \
                     --photometric off. Reported rather than passed off as a correction."
                );
            }
            eprintln!();
            Some(map)
        }
    };

    let ctx = Ctx {
        photometric: photometric_map.as_ref(),
        // Pass one has already read every level; re-reading them in pass two
        // would pay the fold twice for one answer that is already decided.
        measure_drift: false,
        ..ctx
    };

    // ---- pass two: gated average ------------------------------------------
    let t2 = Instant::now();
    let veil_on = veil_enabled();
    let veil_margin = veil_margin();
    let veil_floor = veil_luma_floor();
    // Diagnostic arm. See `Estimator::veil_dispersion`: debiasing by the
    // OBSERVED spread is the right diagnosis of the far-field lift and the
    // wrong operator at a veiled pixel, because the observed spread there is
    // mostly the veil signal itself. Off unless asked for.
    let veil_dispersion = std::env::var("STREHL_VEIL_DISPERSION")
        .map(|v| v != "0" && !v.is_empty())
        .unwrap_or(false);
    // The gate is built in two stages, and the split between them is the point.
    //
    // Stage one asks the per-pixel question -- *is this pixel's election
    // chasing noise* -- against a cut taken from QUANTILES OF THIS IMAGE'S OWN
    // incoherence distribution, never from a constant. A fixed number is a
    // different test on every subject depending on where that subject's
    // distribution falls relative to it, which is exactly how the previous gate
    // failed: it borrowed the merge's `--gate` significance cut, that cut landed
    // at `coffee-bean`'s median, and the gate kept the featureless far
    // background while excluding the rim. See `BUILD-HALO.md` section 32.
    //
    // 0.55 is the split the out-of-crate mask used to trace the silhouette on
    // `lavendar` and `flower-bud` (`experiments/BUILD-HALO/depth_profile.py`),
    // where two luminance-threshold silhouettes had failed.
    //
    // Stage two is what the veil actually ramps on: the FRACTION of each
    // neighbourhood that answered yes. Gating on stage one directly wrote a
    // lacework -- the correction toggling at the scale of paper fibres, because
    // whether one fibre was resolved somewhere in the bracket is a true but
    // invisible per-pixel fact. Section 33. A veil has the scale of the object
    // casting it, so the gate is given that scale too.
    //
    // The stage-two thresholds are constants and are allowed to be, because a
    // fraction carries no scene units: "a quarter of this neighbourhood" means
    // the same thing on every subject, which is precisely what the borrowed
    // absolute cut of section 32 did not.
    const VEIL_SUPPORT_LO: f32 = 0.25;
    const VEIL_SUPPORT_HI: f32 = 0.75;
    let veil_incoherence: Option<Vec<f32>> = veil_on.then(|| {
        let sd = strehl_core::election_coherence::incoherence(p1.stats.best_index(), geom);
        let cut = strehl_core::election_coherence::quantile(&sd, 0.55);
        let support = strehl_core::election_coherence::incoherent_fraction(&sd, geom, cut);
        // Stage three: how much of the correction this pixel is owed.
        //
        // Stages one and two say the envelope is SAFE here. They do not say it
        // is NEEDED here, and on `coffee-bean` those differ over most of the
        // frame: dead ground 900 px from the bean is maximally safe and carries
        // no veil, because a veil is cast by an occluder and there is no
        // occluder within reach of it. Treating it anyway lifted the clean far
        // field 6.04% and turned a shape correction into a gain change.
        //
        // Scaling by proximity to resolved content restores the fall-off the
        // physical term actually has. The normaliser is this image's own p99
        // rather than a constant, for the same reason the stage-one cut is:
        // proximity is measured in "fraction of a window that is occluder", and
        // how much of a window a subject fills is a property of the subject.
        let prox = strehl_core::election_coherence::occluder_proximity(&sd, geom, cut);
        let full = strehl_core::election_coherence::quantile(&prox, 0.99).max(1e-6);
        // Referring this product to its own p99 as well was built and measured
        // and is REFUTED, on the criterion that was specified. It flattens the
        // middle of the profile harder (band 16-30 px reaches 0.7676 of the far
        // field against 0.7111) but it does so by opening the gate from 16.56%
        // to 50.74% of the plane, and it pays for the middle with the two things
        // that were actually asked for: the silhouette band 1-4 px goes back to
        // worsening, 0.3220 -> 0.3158, and the clean far field lifts +2.82%
        // instead of +0.30%. See BUILD-HALO.md section 33.6.
        support
            .iter()
            .zip(prox.iter())
            .map(|(&s, &p)| s * (p / full).clamp(0.0, 1.0))
            .collect()
    });
    let (veil_lo, veil_hi) = (VEIL_SUPPORT_LO, VEIL_SUPPORT_HI);
    // Refused, not silently disabled. Where no neighbourhood anywhere in the
    // frame reads as dead ground there is nothing for the envelope to claim,
    // and applying it anyway would put it on resolved depth -- the one place
    // the specification forbids. Read at p99.9 rather than the max so a handful
    // of hot pixels cannot answer for the frame.
    let veil_reach = veil_incoherence
        .as_deref()
        .map(|s| strehl_core::election_coherence::quantile(s, 0.999))
        .unwrap_or(0.0);
    ensure!(
        !veil_on || veil_reach > VEIL_SUPPORT_LO,
        "STREHL_VEIL cannot separate dead ground from resolved depth on this \
         stack: the most incoherent neighbourhood in the frame is only \
         {veil_reach:.3} incoherent against a {VEIL_SUPPORT_LO:.2} floor, so \
         there is no silhouette to gate on"
    );
    // Refused, not silently accepted. The envelope is a per-pixel maximum over
    // the bracket, so on a bracket whose level drifts it returns the
    // highest-EXPOSURE frame rather than the least-VEILED one, and reports a
    // confident correction that is really a measurement of the drift. This was
    // observed directly: flower-bud drifts 18.3% and the uncorrected envelope
    // raised the far field by 1520 DN, which is the drift, not the veil.
    ensure!(
        !veil_on || photometric_map.is_some(),
        "STREHL_VEIL needs --photometric on (or auto): the veil envelope is a \
         maximum across frames, and without level normalisation it selects the \
         brightest exposure rather than the least veiled sample"
    );
    let mut p2 = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(ci, chunk)| -> Result<Pass2> {
            let first_index = (ci * plan.chunk_len) as u16;
            let mut est: Vec<Estimator> = opts
                .gates
                .iter()
                .map(|g| {
                    // THE CRUX. `Gate::new` denominates the threshold in the
                    // compiled-in FOCUS_NOISE_SD; under --focus it must be
                    // denominated in the scale the host MEASURED for the
                    // operator that actually produced this field. The default
                    // arm is `Gate::new` verbatim, so the byte-freezes see the
                    // same constant they were baselined against.
                    //
                    // Fact 631 is why this is a substitution and not a
                    // correction: t/k prices a miscalibration, it does not undo
                    // one. The number below comes from calibrating the real
                    // operator, never from scaling the shipped constant.
                    let gate = match ctx.focus_op {
                        Some(op) => Gate::with_noise_sd(*g, op.calibration().response_sd()),
                        None => Gate::new(*g),
                    };
                    let mut e = Estimator::new(&p1.stats, gate);
                    if veil_on {
                        e.enable_veil_from_incoherence(
                            veil_incoherence.as_deref().expect("refused above if absent"),
                            veil_lo,
                            veil_hi,
                            veil_margin,
                            veil_floor,
                        );
                        e.set_veil_dispersion(veil_dispersion);
                    }
                    e
                })
                .collect();
            let mut selector = match (opts.flat_roi, opts.detail_roi) {
                (Some(flat), Some(detail)) => Some(SelectorRois::new(flat, detail)),
                _ => None,
            };
            let mut tf = opts.stats.then(|| ThroughFocus::new(&p1.stats));
            let mut placebo = (opts.stats && opts.stats_placebo)
                .then(|| ThroughFocus::new_permuted(&p1.stats, &perm));
            let mut scratch = Scratch::new_with_warp(geom, opts.stats, warps.is_some());
            let mut t = Timings::default();

            for (offset, path) in chunk.iter().enumerate() {
                let index = first_index + offset as u16;
                if ctx.is_refused(index) {
                    continue;
                }
                let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                let t0 = Instant::now();
                let mut err = None;
                for e in est.iter_mut() {
                    if let Err(e) = e.fold_censored(index, &frame, &scratch.reg, CONTAINER_MAX_DN) {
                        err = Some(map_dim_err(index, e));
                        break;
                    }
                }
                if err.is_none()
                    && let Some(selector) = selector.as_mut()
                {
                    selector.fold(&frame, index, p1.stats.best_index(), geom, levels.black);
                }
                ctx.release(frame);
                if let Some(e) = err {
                    return Err(e);
                }
                if let Some(tf) = tf.as_mut() {
                    tf.fold(index, &scratch.fine, &scratch.reg)
                        .map_err(|e| map_dim_err(index, e))?;
                }
                if let Some(p) = placebo.as_mut() {
                    p.fold(perm[index as usize], &scratch.fine, &scratch.reg)
                        .map_err(|e| map_dim_err(index, e))?;
                }
                t.work += t0.elapsed().as_secs_f64();
            }
            Ok(Pass2 {
                est,
                selector,
                tf,
                placebo,
                t,
            })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                for (x, y) in a.est.iter_mut().zip(b.est.iter()) {
                    x.absorb(y).map_err(|e| map_dim_err(0, e))?;
                }
                if let (Some(x), Some(y)) = (a.selector.as_mut(), b.selector.as_ref()) {
                    x.absorb(y);
                }
                if let (Some(x), Some(y)) = (a.tf.as_mut(), b.tf.as_ref()) {
                    x.absorb(y).map_err(|e| map_dim_err(0, e))?;
                }
                if let (Some(x), Some(y)) = (a.placebo.as_mut(), b.placebo.as_ref()) {
                    x.absorb(y).map_err(|e| map_dim_err(0, e))?;
                }
                a.t.add(b.t);
                Ok(a)
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    let pass2_secs = t2.elapsed().as_secs_f64();

    // The veil envelope is applied once, after every chunk has been reduced in,
    // because a maximum over a subset is not a maximum over the bracket.
    if veil_on {
        for (g, e) in opts.gates.iter().zip(p2.est.iter_mut()) {
            let d = e.focus_deciles();
            eprintln!(
                "veil: best_focus deciles p10..p90 = [{}]",
                d.iter()
                    .map(|x| format!("{x:.4}"))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            let r = e.apply_veil(&noise, levels.black);
            if r.declined {
                // A decline and a no-op produce the same picture, and only this
                // line tells them apart.
                eprintln!(
                    "veil: gate {g} DECLINED -- backdrop {:.0} DN is not brighter than \
                     foreground {:.0} DN (polarity {:+.0} DN). Veiling runs toward the \
                     occluder's own level, so an upper envelope here would select the \
                     most-veiled sample at every background pixel. Nothing was touched.",
                    r.backdrop_dn, r.foreground_dn, r.polarity_dn
                );
                continue;
            }
            eprintln!(
                "veil: gate {g} dead-ground support {veil_lo:.2}..{veil_hi:.2} \
                 (reach {veil_reach:.3}) \
                 margin {veil_margin} sigma \
                 floor {veil_floor} x backdrop {:.0} DN = {:.0} DN \
                 (foreground {:.0} DN, polarity {:+.0} DN) \
                 -> eligible {:.2}% applied {:.2}% mean lift {:+.1} DN debias {:.2} sigma \
                 (dispersion {:.2}x modelled)",
                r.backdrop_dn,
                r.luma_floor_dn,
                r.foreground_dn,
                r.polarity_dn,
                100.0 * r.eligible as f64 / r.pixels as f64,
                100.0 * r.applied as f64 / r.pixels as f64,
                r.mean_lift_dn,
                r.debias_sigmas,
                r.dispersion_ratio
            );
        }
    }

    for e in &p2.est {
        ensure!(
            e.frames_folded() as usize == expected,
            "pass two folded {} frames, expected {}",
            e.frames_folded(),
            expected
        );
        ensure!(
            e.every_pixel_is_decided(),
            "some pixel admitted no frame at all; the winner is supposed to be unconditional"
        );
    }
    if let Some(path) = n_eff_map_path(opts) {
        // gates.len() == 1 was enforced before any frame was read, so est[0]
        // is unambiguously the gate this map belongs to.
        let est = &p2.est[0];
        write_n_eff_map(&path, est.n_eff(), est.frames_folded(), geom)?;
    }
    if let Some(selector) = &p2.selector {
        ensure!(
            selector.is_complete(),
            "the gate-zero selector reference did not capture every requested ROI pixel"
        );
    }

    if let Some(dir) = dump::dump_dir() {
        for e in &p2.est {
            let name = format!("n_eff_gate{:.2}.npy", e.gate().threshold);
            dump::write_u16(&dir.join(&name), geom.width, geom.height, e.n_eff())?;
            eprintln!("merge state     : wrote {} to {}", name, dir.display());
        }
        eprintln!();
    }

    eprintln!("--- pass two: gated average (MEASURED) ---");
    eprintln!(
        "wall clock      : {pass2_secs:.3} s  ({:.1} ms/frame, {} accumulators)",
        1000.0 * pass2_secs / n,
        opts.gates.len()
    );
    eprintln!(
        "  decode        : {:.3} s summed across workers ({:.1} ms/frame)",
        p2.t.decode,
        1000.0 * p2.t.decode / n
    );
    eprintln!(
        "  field + gate  : {:.3} s summed across workers ({:.1} ms/frame)",
        p2.t.work,
        1000.0 * p2.t.work / n
    );
    eprintln!(
        "total           : {:.3} s  (+{prologue_secs:.3} s prologue), {:.1} MB/s over {:.1} MB",
        pass1_secs + pass2_secs,
        input_bytes as f64 / 1e6 / (pass1_secs + pass2_secs),
        input_bytes as f64 / 1e6
    );
    eprintln!(
        "in-flight frames: {} peak, bound {} (never O(N))",
        peak_live.load(Ordering::Relaxed),
        plan.chunks
    );
    eprintln!();

    report(
        opts,
        &p2,
        &p1,
        geom,
        levels,
        &noise,
        middle,
        ctx.focus_op
            .map_or(FOCUS_NOISE_SD, |op| op.calibration().response_sd()),
    )?;
    if opts.stats {
        report_statistics(opts, &p2, &p1.clip, geom, levels, &noise, &perm)?;
    }

    // ---- pass three: the M87 occlusion-halo correction --------------------
    //
    // A THIRD pass, and only when asked for. Passes one and two are untouched,
    // so with the correction off the merge is byte-for-byte what it was and the
    // corpus's frozen numbers cannot move. See `halo` for why it is off by
    // default: it is cosmetic, and against ground truth it makes the image
    // measurably more wrong.
    //
    // EVERY STATISTIC THIS COMMAND PRINTS HAS ALREADY BEEN PRINTED BY HERE.
    // `report` and `report_statistics` ran above, so no number in the output
    // above reflects this correction. That is not merely an ordering accident
    // that could be repaired by moving this block earlier -- MOVING IT WOULD
    // CHANGE NOTHING. The correction never touches `p2.est`; it is carried to
    // `write_merged` in the `halo` side-channel and applied as the pixels are
    // written. The reported statistics describe the accumulators, the gate and
    // the election, not the pixels on disk.
    //
    // The same is true of the veil, which *does* mutate the estimator: it moved
    // 18.57% of flower-bud's pixels and changed zero reported statistics
    // (measured, section 31). So the rule generalises to every post-merge
    // correction, present and future:
    //
    //     A/B-ING A POST-MERGE CORRECTION ON STREHL'S PRINTED NUMBERS RETURNS A
    //     NULL WHETHER OR NOT IT WORKS. RE-READ THE OUTPUT TIFF INSTEAD.
    if halo::enabled() && opts.out.is_none() {
        eprintln!(
            "halo fix        : REQUESTED ({}=1) BUT SKIPPED -- there is no --out, so there is no \
             image to correct and nothing above or below reflects it.",
            halo::FIX_ENV
        );
        eprintln!();
    }
    let halo_fix = if halo::enabled() && opts.out.is_some() {
        let est = &p2.est[0];
        let t3 = Instant::now();
        let luma: Vec<f32> = (0..geom.pixels())
            .map(|i| (est.green_mean(i) - levels.black).max(0.0))
            .collect();
        let hplan = halo::Plan::build(&luma, p1.stats.best_index(), geom, halo::delta_in_use());
        drop(luma);
        eprintln!("--- pass three: occlusion-halo correction (M87, COSMETIC) ---");
        eprintln!(
            "halo fix        : ON ({}=1). delta {} frames, yoke {:.0} px.",
            halo::FIX_ENV,
            hplan.delta,
            halo::YOKE
        );
        eprintln!(
            "                  subject {:.2}% of pixels at Otsu tau {:.0} DN; {} treated ({:.3}%).",
            100.0 * hplan.foreground_px as f64 / geom.pixels() as f64,
            hplan.tau,
            hplan.treated_len(),
            100.0 * hplan.treated_len() as f64 / geom.pixels() as f64
        );
        let pass = paths
            .par_chunks(plan.chunk_len)
            .enumerate()
            .map(|(ci, chunk)| -> Result<halo::Pass> {
                let first_index = (ci * plan.chunk_len) as u16;
                let mut acc = halo::Pass::new(&hplan);
                let mut scratch = Scratch::new_with_warp(geom, false, warps.is_some());
                let mut t = Timings::default();
                for (offset, path) in chunk.iter().enumerate() {
                    let index = first_index + offset as u16;
                    if ctx.is_refused(index) {
                        continue;
                    }
                    let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                    acc.fold(&hplan, index, &frame, &scratch.reg);
                    ctx.release(frame);
                }
                Ok(acc)
            })
            .reduce_with(|a, b| match (a, b) {
                (Ok(mut a), Ok(b)) => {
                    a.absorb(&b);
                    Ok(a)
                }
                (Err(e), _) | (Ok(_), Err(e)) => Err(e),
            })
            .expect("at least one chunk")?;
        let fix = pass.finish(&hplan);
        eprintln!(
            "                  {} of {} treated pixels re-elected; {} kept their original value \
             because every frame was inside the forbidden band.",
            fix.treated - fix.undecided,
            fix.treated,
            fix.undecided
        );
        if fix.treated > 0 && fix.undecided == fix.treated {
            // Measured on a 22-frame stack: 793,776 pixels treated, 0 re-elected.
            // `|k - k_F| >= delta` is unsatisfiable when the stack is no deeper
            // than `delta`, so the pass is a guaranteed no-op and the banner
            // above would otherwise be the only thing the user reads.
            eprintln!(
                "halo fix        : WARNING -- ON but a COMPLETE NO-OP. No treated pixel had any \
                 frame at least {} from k_F. A stack of {} frames cannot satisfy that; the output \
                 is identical to the uncorrected merge.",
                hplan.delta,
                paths.len()
            );
        }
        eprintln!(
            "                  This is NOT a fidelity improvement. On a synthetic scene with known \
             truth it cuts the halo metric 79.8% and raises RMSE against truth 254.6%."
        );
        eprintln!("wall clock      : {:.3} s", t3.elapsed().as_secs_f64());
        eprintln!();
        Some(fix)
    } else {
        None
    };

    if let Some(path) = &opts.out {
        write_merged(
            Merged::Estimated {
                est: &p2.est[0],
                halo: halo_fix.as_ref(),
            },
            levels,
            wb,
            xyz_to_cam.as_ref(),
            opts.space,
            opts.demosaic,
            exposure,
            strehl_core::restore::gain_cap_from_env().and_then(|cap| {
                alignment
                    .as_ref()
                    .map(|(m, _, _)| strehl_core::restore::RestorePlan {
                        resampler: m.resampler(),
                        gain_cap: cap,
                        noise: &noise,
                    })
            }),
            // ESTIMATOR BACKEND. The pyramid backend's call carries the
            // identical expression; both read the one `CoverFit` their own
            // `cover_or_explain` returned, so neither can honour `--cover crop`
            // while the other quietly does not.
            alignment.as_ref().and_then(|(_, _, fit)| fit.rect()),
            path,
        )?;
    }
    Ok(())
}

/// The number of CFA planes the band merge carries, and the order it carries
/// them in: `R`, `G1`, `G2`, `B` -- RGGB, matching `CfaPlane::rggb_at`.
///
/// Deliberately NOT `CfaPlane::ALL`, which is `[R, G1, B, G2]`. Both orders are
/// self-consistent; what matters is that the order the planes are folded in is
/// the order [`band_slot`] reads them back out in, and stating it once here is
/// what makes that checkable.
const BAND_PLANES: usize = 4;

/// `(dx, dy)` of each plane inside the 2x2 quad, in [`BAND_PLANES`] order.
const BAND_PLANE_OFFSETS: [(usize, usize); BAND_PLANES] = [(0, 0), (1, 0), (0, 1), (1, 1)];

/// Which slot of a [`BandMerge`] output holds a given CFA site.
const fn band_slot(p: CfaPlane) -> usize {
    match p {
        CfaPlane::R => 0,
        CfaPlane::G1 => 1,
        CfaPlane::G2 => 2,
        CfaPlane::B => 3,
    }
}

/// A merged image ready to be developed, whichever backend produced it.
///
/// **Both variants answer in black-subtracted, non-negative DN.** That is the
/// one convention the write path needs and the one place the two backends
/// disagreed: the estimator accumulates raw sensor DN and the black level comes
/// off at the write, while the band merge folds planes that were
/// black-subtracted at decode and has nothing left to subtract. Pushing the
/// subtraction behind this enum is what lets **one** develop path -- one
/// exposure rule, one colour matrix, one set of caveats -- serve both, instead
/// of a second copy of the arithmetic that can drift from the first. The
/// example this merge came from carries exactly such a copy, with a comment
/// saying it "must stay that way".
///
/// The estimator's arithmetic is unchanged: `(raw - black).max(0.0)` happens
/// here rather than three lines later, in the same order, so the byte-frozen
/// measurement branch below still emits the bytes M85 proved.
enum Merged<'a> {
    /// [`MergeBackend::Estimator`] output, with its optional halo correction.
    Estimated {
        est: &'a Estimator,
        halo: Option<&'a halo::Fix>,
    },
    /// [`MergeBackend::Pyramid`] output: four collapsed planes in
    /// [`BAND_PLANES`] order on the quad grid.
    Bands {
        geom: PlaneGeometry,
        planes: &'a [Vec<f32>],
    },
}

impl Merged<'_> {
    fn geometry(&self) -> PlaneGeometry {
        match self {
            Self::Estimated { est, .. } => est.geometry(),
            Self::Bands { geom, .. } => *geom,
        }
    }

    /// Black-subtracted, non-negative value at CFA site `p` of quad `i`.
    fn value(&self, p: CfaPlane, i: usize, black: f32) -> f32 {
        match self {
            Self::Estimated { est, halo } => {
                let raw = match halo {
                    Some(h) => h.value(est, p, i),
                    None => est.value(p, i),
                };
                (raw - black).max(0.0)
            }
            Self::Bands { planes, .. } => planes[band_slot(p)][i].max(0.0),
        }
    }

    /// Black-subtracted, non-negative mean of the quad's two green sites.
    ///
    /// The clamp is applied to the *mean*, not to each site, on both arms: that
    /// is what the estimator has always done and the two must agree, or the
    /// binned render and the demosaiced render of one image would disagree
    /// about green in the shadows.
    fn green_mean(&self, i: usize, black: f32) -> f32 {
        match self {
            Self::Estimated { est, halo } => {
                let raw = match halo {
                    Some(h) => h.green_mean(est, i),
                    None => est.green_mean(i),
                };
                (raw - black).max(0.0)
            }
            Self::Bands { planes, .. } => {
                (0.5 * (planes[band_slot(CfaPlane::G1)][i] + planes[band_slot(CfaPlane::G2)][i]))
                    .max(0.0)
            }
        }
    }
}

/// One worker's per-frame buffers for the band merge, allocated once per chunk.
/// One chunk's contribution to the fold: its partial merge, how many frames it
/// actually folded, and the running sum of the per-frame MEASURED noise floors
/// so the banner can report the floor the gate really used.
///
/// A struct rather than a tuple because the floor accumulator made the tuple
/// four-wide and unreadable, and because a caller that swapped `folded` and
/// `beta_n` -- both `usize` -- would compile and silently report a wrong frame
/// count beside a wrong floor.
struct FoldPart {
    merge: BandMerge,
    folded: usize,
    beta_sum: Vec<f64>,
    beta_n: usize,
    split: Option<SplitPart>,
}

struct SplitPart {
    even: BandMerge,
    odd: BandMerge,
    even_frames: usize,
    odd_frames: usize,
}

impl SplitPart {
    fn absorb(&mut self, other: &Self) {
        self.even.absorb(&other.even);
        self.odd.absorb(&other.odd);
        self.even_frames += other.even_frames;
        self.odd_frames += other.odd_frames;
    }
}

struct SplitWorker {
    even: BandMerge,
    odd: BandMerge,
    even_ws: FrameWorkspace,
    odd_ws: FrameWorkspace,
    even_frames: usize,
    odd_frames: usize,
}

impl SplitWorker {
    fn new(
        geom: PlaneGeometry,
        cfg: MergeConfig,
        sizes: &[strehl_core::pyramid::LevelSize],
    ) -> Self {
        Self {
            even: BandMerge::new(geom.width, geom.height, 1, cfg),
            odd: BandMerge::new(geom.width, geom.height, 1, cfg),
            even_ws: FrameWorkspace::new(sizes, 1),
            odd_ws: FrameWorkspace::new(sizes, 1),
            even_frames: 0,
            odd_frames: 0,
        }
    }

    fn add_frame(
        &mut self,
        index: usize,
        luma: &[f32],
        variance: &[f32],
        beta: Option<&[f32]>,
    ) {
        let plane = [luma];
        if index.is_multiple_of(2) {
            self.even_ws.next_frame();
            self.even
                .add_frame_with_gain(&plane, luma, variance, beta, &mut self.even_ws);
            self.even_frames += 1;
        } else {
            self.odd_ws.next_frame();
            self.odd
                .add_frame_with_gain(&plane, luma, variance, beta, &mut self.odd_ws);
            self.odd_frames += 1;
        }
    }

    fn into_part(self) -> SplitPart {
        SplitPart {
            even: self.even,
            odd: self.odd,
            even_frames: self.even_frames,
            odd_frames: self.odd_frames,
        }
    }
}

struct BandWorker {
    merge: BandMerge,
    fws: FrameWorkspace,
    warp: WarpScratch,
    planes: Vec<Vec<f32>>,
    luma: Vec<f32>,
    var: Vec<f32>,
    /// `None` when the measured floor is switched off, restoring the shipping
    /// white-noise gate exactly.
    floor: Option<gatefloor::Probe>,
    /// This frame's measured floor, filtered to the bands that are usable.
    beta: Vec<f32>,
    /// Running sum of the per-frame measured floors, so the banner can report
    /// the floor the merge ACTUALLY used rather than the compile-time constant
    /// it used to print. A banner that reports a number the code did not use is
    /// the failure mode this project exists to catch.
    beta_sum: Vec<f64>,
    beta_n: usize,
    split: Option<SplitWorker>,
}

impl BandWorker {
    fn new(geom: PlaneGeometry, cfg: MergeConfig, split: bool) -> Self {
        let sizes = level_sizes(geom.width, geom.height, cfg.bands);
        let px = geom.pixels();
        Self {
            merge: BandMerge::new(geom.width, geom.height, BAND_PLANES, cfg),
            fws: FrameWorkspace::new(&sizes, BAND_PLANES),
            warp: WarpScratch::new(geom),
            planes: (0..BAND_PLANES).map(|_| vec![0.0; px]).collect(),
            luma: vec![0.0; px],
            var: vec![0.0; px],
            floor: gatefloor::enabled().then(|| gatefloor::Probe::new(geom, cfg.bands)),
            beta: Vec::new(),
            beta_sum: Vec::new(),
            beta_n: 0,
            split: split.then(|| SplitWorker::new(geom, cfg, &sizes)),
        }
    }

    /// Decode, register and fold one frame. `false` means the alignment solve
    /// refused this frame, so it was skipped rather than merged unregistered.
    fn fold(
        &mut self,
        path: &Path,
        index: usize,
        geom: PlaneGeometry,
        levels: Levels,
        noise: &NoiseModel,
        warps: Option<&WarpMap>,
        defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,
    ) -> Result<bool> {
        self.beta.clear();
        if let Some(p) = self.floor.as_mut() {
            p.invalidate();
        }
        if !load_frame(
            path,
            index,
            geom,
            levels,
            warps,
            defect,
            &mut self.warp,
            self.floor.as_mut(),
            &mut self.planes,
            &mut self.luma,
        )? {
            return Ok(false);
        }
        luma_variance(&self.luma, noise, &mut self.var);

        // The measured floor, truncated at the first band the probe could not
        // speak for rather than skipping past it. `add_frame_with_gain` falls
        // back to the white value beyond the slice's end, so truncating is how
        // a partial measurement is expressed; substituting white *inside* the
        // slice and continuing would silently mix two noise models across
        // adjacent bands.
        if let Some(p) = self.floor.as_ref() {
            self.beta
                .extend(p.last().iter().copied().take_while(|b| b.is_finite()));
        }
        let frame_beta = (!self.beta.is_empty()).then_some(self.beta.as_slice());
        if let Some(b) = frame_beta {
            if self.beta_sum.len() < b.len() {
                self.beta_sum.resize(b.len(), 0.0);
            }
            for (acc, v) in self.beta_sum.iter_mut().zip(b) {
                *acc += f64::from(*v);
            }
            self.beta_n += 1;
        }

        let refs: Vec<&[f32]> = self.planes.iter().map(|v| v.as_slice()).collect();
        self.fws.next_frame();
        self.merge
            .add_frame_with_gain(&refs, &self.luma, &self.var, frame_beta, &mut self.fws);
        if let Some(split) = self.split.as_mut() {
            split.add_frame(index, &self.luma, &self.var, frame_beta);
        }
        Ok(true)
    }

    fn into_part(self, folded: usize) -> FoldPart {
        FoldPart {
            merge: self.merge,
            folded,
            beta_sum: self.beta_sum,
            beta_n: self.beta_n,
            split: self.split.map(SplitWorker::into_part),
        }
    }
}

/// Decode, register and deinterleave one frame into its four CFA planes and
/// green luma. `false` means the alignment solve refused it.
///
/// **Shared by the fold and by the confidence pass, deliberately.** A
/// confidence map computed against frames registered even slightly differently
/// from the ones that were merged would be measuring the registration rather
/// than the merge, and would do it invisibly -- the map would simply read
/// "unsupported" along every edge and look like a plausible result. One copy of
/// this code is the only thing that makes the second pass comparable to the
/// first.
#[allow(clippy::too_many_arguments)]
fn load_frame(
    path: &Path,
    index: usize,
    geom: PlaneGeometry,
    levels: Levels,
    warps: Option<&WarpMap>,
    defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,
    scratch: &mut WarpScratch,
    floor: Option<&mut gatefloor::Probe>,
    planes: &mut [Vec<f32>],
    luma: &mut [f32],
) -> Result<bool> {
    {
        let mut frame = strehl_raw::decode(path).with_context(|| format!("frame {index}"))?;
        ensure!(
            frame.levels == levels,
            "frame {index} has levels black {} white {}, but the stack was calibrated at \
             black {} white {}",
            frame.levels.black,
            frame.levels.white,
            levels.black,
            levels.white
        );
        // ---- sensor defect correction, BEFORE THE WARP -------------------
        //
        // This ordering is the whole point of the feature and it is why these
        // four lines sit above the `warps` block rather than below it. The
        // map's coordinates name photosites. After `warp_frame_in_place` the
        // sample at (x, y) is a resampled combination of several photosites
        // from somewhere else, so the map no longer addresses anything: the
        // correction would land beside the defect and brighten clean pixels,
        // which is strictly worse than leaving it alone.
        //
        // Note that the justification is *mis-addressing*, not smearing. M101
        // measured the elected trail at 0.931 px against a 0.937 px shift
        // null, so on this body the stack does NOT spread a defect into an arc
        // -- see BUILD-DEFECT.md P2b, which refutes that premise. The ordering
        // requirement survives the refutation unchanged, because a map indexed
        // by photosite cannot address a resampled buffer however far the
        // defect did or did not travel.
        //
        // `strehl_core::defect_map`'s
        // `dust_correction_must_precede_the_warp_to_land_on_the_defect` plants
        // a mote and fails if these lines are moved below the warp;
        // `with_an_identity_warp_the_two_orderings_are_bit_identical` proves
        // that test is measuring the ordering and not the resampler.
        if let Some((plan, tally)) = defect {
            crate::stack::apply_defects(plan, &mut frame, tally, index)?;
        }
        if let Some(map) = warps {
            match map.warp(index)? {
                FrameWarp::Placed(t) => {
                    align_cmd::warp_frame_in_place(&mut frame, *t, geom, map.resampler(), scratch)?;
                    // This frame's own band-noise floor, at this frame's own
                    // sub-pixel phase, measured here because this is the only
                    // place the decoded frame and the transform that was
                    // actually applied to it are both in scope. See
                    // `gatefloor` for why neither a constant nor a formula can
                    // stand in for it.
                    //
                    // An unwarped frame -- `warps` is `None`, or the solve
                    // refused this one -- never reaches this line, so it keeps
                    // the shipping white-noise floor and its output is
                    // bit-identical. That is a property of the control flow,
                    // not of a tolerance.
                    if let Some(p) = floor {
                        p.measure(&frame, index, *t, geom, map.resampler(), scratch)?;
                    }
                }
                // The solve could not connect this frame to the bracket, so its
                // geometry is unknown and folding it would put mis-registered
                // data into the merge.
                FrameWarp::Refused(_) => return Ok(false),
            }
        }

        let black = levels.black;
        let (stride, ax, ay) = (frame.stride, frame.active.x, frame.active.y);
        let (gw, gh) = (geom.width, geom.height);
        for (p, (dx, dy)) in BAND_PLANE_OFFSETS.iter().enumerate() {
            let out = &mut planes[p];
            for py in 0..gh {
                let row = (ay + 2 * py + dy) * stride + ax + dx;
                let dst = &mut out[py * gw..py * gw + gw];
                for (px, o) in dst.iter_mut().enumerate() {
                    *o = (f32::from(frame.data[row + 2 * px]) - black).max(0.0);
                }
            }
        }
    }

    // Green luma, `L = (G1 + G2) / 2`, exactly as `plane::green_luma`
    // computes it -- the same plane the estimator's election runs on.
    // Selecting on green only is what keeps chroma noise out of the
    // decision.
    for i in 0..luma.len() {
        luma[i] = 0.5 * (planes[1][i] + planes[2][i]);
    }
    Ok(true)
}

/// Env twin of `--pyramid-workers`, and the only way to raise the fold's
/// parallelism on a machine with more RAM than the budget assumes.
const BAND_WORKERS_ENV: &str = "STREHL_PYRAMID_WORKERS";

/// Env twin of `--confidence-map`, for a harness that cannot edit the command
/// line. The flag wins, exactly as `--n-eff-map` beats [`NEFF_ENV`].
const CONFIDENCE_ENV: &str = "STREHL_CONFIDENCE_MAP";

/// Where to write the confidence map, or `None`.
fn confidence_map_path(opts: &MergeOptions) -> Option<PathBuf> {
    if let Some(p) = &opts.confidence_map {
        return Some(p.clone());
    }
    let raw = std::env::var(CONFIDENCE_ENV).ok()?;
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        eprintln!("{CONFIDENCE_ENV} is set but empty; not writing a confidence map");
        return None;
    }
    Some(PathBuf::from(trimmed))
}

/// Where the merged output sits INSIDE the cloud of aligned observations at
/// each pixel: 0 when it sits at an extreme of that cloud, 1 when it sits dead
/// centre.
///
/// **What this is a statement about.** The pyramid elects per band coefficient,
/// so no single frame owns an output pixel and there is no frame count to
/// report -- which is why `--n-eff-map` is refused on this backend. But there
/// is a question about the merge's own behaviour that still has a per-pixel
/// answer: *did this merge commit to something, or did it hedge?* Electing a
/// frame puts the output at an extremity of the observations, because the frame
/// that is in focus is the one that departs furthest from the defocused
/// majority. Averaging puts it in the middle. So a value near 1 says the merge
/// declined to choose and emitted the consensus of frames that disagreed --
/// which is the veiling failure stated as a measurement.
///
/// **Why the obvious quantity is not this one, and lost.** The first design
/// here was `d_min`, the distance from the output to the *nearest* observation,
/// on the reasoning that a value nobody photographed is a value nobody can
/// vouch for. Measured against a known veiled tarsus in `bee-3-cpl` it ran
/// BACKWARDS: at matched local contrast the veiled region scored 0.848, i.e.
/// more confident than crisp neighbouring structure. The reason is that veiling
/// is averaging, and an average of frames that agree sits *close* to every one
/// of them. Distance-to-observation cannot see the failure because the failure
/// does not move the output away from the data; it moves it to the middle of
/// the data. `d_sharp` (0.909) and `spread` (0.911) failed the same way.
///
/// **Why it is not a contrast map.** It is a rank, not a magnitude: the only
/// thing each observation contributes is which side of the output it fell on,
/// so scaling the subject's contrast by any positive factor leaves every
/// comparison and therefore the whole statistic unchanged. Measured on
/// `flowers-cpl`, the corpus contrast minimum, the within-subject Spearman
/// against local contrast is 0.0566 and the decile table is flat.
///
/// **Cost.** One extra decode and warp per frame. Nothing is cached from the
/// fold because nothing can be: the frames are streamed and dropped, and the
/// merged image the observations must be compared against does not exist until
/// every one of them has already been folded.
struct Centrality {
    /// How many observations fell below the merged value at this pixel.
    below: Vec<u32>,
    /// How many observations reached this pixel at all. Kept separately rather
    /// than assumed equal to the frame count, because a warp can leave a pixel
    /// outside every frame's support and a rank out of zero is not zero.
    seen: Vec<u32>,
}

fn confidence_pass(
    paths: &[PathBuf],
    geom: PlaneGeometry,
    levels: Levels,
    warps: Option<&WarpMap>,
    defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,
    merged_luma: &[f32],
    per_chunk: usize,
) -> Result<Centrality> {
    let indexed: Vec<(usize, PathBuf)> = paths.iter().cloned().enumerate().collect();
    let parts: Vec<Result<Centrality>> = indexed
        .par_chunks(per_chunk.max(1))
        .map(|chunk| {
            let px = geom.pixels();
            let mut scratch = WarpScratch::new(geom);
            let mut planes: Vec<Vec<f32>> = (0..BAND_PLANES).map(|_| vec![0.0; px]).collect();
            let mut luma = vec![0.0f32; px];
            let mut c = Centrality {
                below: vec![0; px],
                seen: vec![0; px],
            };
            for (i, p) in chunk {
                if !load_frame(
                    p, *i, geom, levels, warps, defect, &mut scratch, None, &mut planes,
                    &mut luma,
                )? {
                    continue;
                }
                for ((b, s), (l, m)) in c
                    .below
                    .iter_mut()
                    .zip(c.seen.iter_mut())
                    .zip(luma.iter().zip(merged_luma))
                {
                    if l < m {
                        *b += 1;
                    }
                    *s += 1;
                }
            }
            Ok(c)
        })
        .collect();

    let mut out: Option<Centrality> = None;
    for part in parts {
        let c = part?;
        match &mut out {
            // Addition is associative and commutative, so how the frames were
            // chunked cannot change the answer and this stays exact however
            // the workers split.
            Some(a) => {
                for i in 0..a.below.len() {
                    a.below[i] += c.below[i];
                    a.seen[i] += c.seen[i];
                }
            }
            None => out = Some(c),
        }
    }
    out.context("no frames were available for the confidence pass")
}

/// MEASUREMENT SCAFFOLDING, gated on `STREHL_CONFIDENCE_DEBUG=<dir>`.
///
/// `d_min` is one candidate for the per-pixel confidence quantity among
/// several, and which of them deserves to ship is an empirical question, not
/// an arguable one. Every candidate is a function of the same loaded frames,
/// so one traversal can compute all of them and they can then be scored
/// against the same controls at the cost of a single render. Nothing on the
/// default path calls this.
#[derive(Clone)]
struct Candidates {
    /// `min |L - M|` -- distance to the nearest observation.
    dmin: Vec<f32>,
    /// `min L` and `max L` -- the observation cloud's extent.
    lo: Vec<f32>,
    hi: Vec<f32>,
    /// How many observations fall below the merged value. With `seen` this
    /// gives the output's rank inside the cloud, and a rank near the middle
    /// is the signature of a merge that averaged instead of electing.
    below: Vec<u32>,
    /// How many observations sit within one sigma of the merged value.
    within: Vec<u32>,
    seen: Vec<u32>,
    /// The largest local Laplacian magnitude any frame showed here, and the
    /// luma of the frame that showed it. The distance from the output to that
    /// value asks the pointed question: *there was a sharper observation
    /// available -- did the merge deliver it?*
    best_sharp: Vec<f32>,
    l_at_sharp: Vec<f32>,
}

impl Candidates {
    fn new(px: usize) -> Self {
        Self {
            dmin: vec![f32::INFINITY; px],
            lo: vec![f32::INFINITY; px],
            hi: vec![f32::NEG_INFINITY; px],
            below: vec![0; px],
            within: vec![0; px],
            seen: vec![0; px],
            best_sharp: vec![-1.0; px],
            l_at_sharp: vec![0.0; px],
        }
    }

    /// Every reduction here is associative and commutative, so how the frames
    /// were chunked cannot change the result.
    fn absorb(&mut self, o: &Candidates) {
        for i in 0..self.dmin.len() {
            if o.dmin[i] < self.dmin[i] {
                self.dmin[i] = o.dmin[i];
            }
            if o.lo[i] < self.lo[i] {
                self.lo[i] = o.lo[i];
            }
            if o.hi[i] > self.hi[i] {
                self.hi[i] = o.hi[i];
            }
            self.below[i] += o.below[i];
            self.within[i] += o.within[i];
            self.seen[i] += o.seen[i];
            if o.best_sharp[i] > self.best_sharp[i] {
                self.best_sharp[i] = o.best_sharp[i];
                self.l_at_sharp[i] = o.l_at_sharp[i];
            }
        }
    }
}

/// Local detail energy, as the magnitude of the 4-neighbour Laplacian. The
/// border is left at zero rather than extrapolated, because a manufactured
/// edge value would be indistinguishable from a real one.
fn laplacian_abs(luma: &[f32], w: usize, h: usize, out: &mut [f32]) {
    out.fill(0.0);
    if w < 3 || h < 3 {
        return;
    }
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let i = y * w + x;
            out[i] = 4.0f32.mul_add(luma[i], -(luma[i - 1] + luma[i + 1] + luma[i - w] + luma[i + w]))
                .abs();
        }
    }
}

fn confidence_debug_pass(
    paths: &[PathBuf],
    geom: PlaneGeometry,
    levels: Levels,
    warps: Option<&WarpMap>,
    defect: Option<(&crate::stack::DefectPlan, &crate::stack::DefectTally)>,
    merged_luma: &[f32],
    sigma: &[f32],
    per_chunk: usize,
) -> Result<Candidates> {
    let indexed: Vec<(usize, PathBuf)> = paths.iter().cloned().enumerate().collect();
    let parts: Vec<Result<Candidates>> = indexed
        .par_chunks(per_chunk.max(1))
        .map(|chunk| {
            let px = geom.pixels();
            let (gw, gh) = (geom.width, geom.height);
            let mut scratch = WarpScratch::new(geom);
            let mut planes: Vec<Vec<f32>> = (0..BAND_PLANES).map(|_| vec![0.0; px]).collect();
            let mut luma = vec![0.0f32; px];
            let mut sharp = vec![0.0f32; px];
            let mut c = Candidates::new(px);
            for (i, p) in chunk {
                if !load_frame(
                    p, *i, geom, levels, warps, defect, &mut scratch, None, &mut planes,
                    &mut luma,
                )? {
                    continue;
                }
                laplacian_abs(&luma, gw, gh, &mut sharp);
                for i in 0..px {
                    let (l, m) = (luma[i], merged_luma[i]);
                    let e = (l - m).abs();
                    if e < c.dmin[i] {
                        c.dmin[i] = e;
                    }
                    if l < c.lo[i] {
                        c.lo[i] = l;
                    }
                    if l > c.hi[i] {
                        c.hi[i] = l;
                    }
                    if l < m {
                        c.below[i] += 1;
                    }
                    if e <= sigma[i] {
                        c.within[i] += 1;
                    }
                    c.seen[i] += 1;
                    if sharp[i] > c.best_sharp[i] {
                        c.best_sharp[i] = sharp[i];
                        c.l_at_sharp[i] = l;
                    }
                }
            }
            Ok(c)
        })
        .collect();

    let mut out: Option<Candidates> = None;
    for part in parts {
        let c = part?;
        match &mut out {
            Some(a) => a.absorb(&c),
            None => out = Some(c),
        }
    }
    out.context("no frames were available for the confidence debug pass")
}

/// Write every candidate as its own milli-unit map so one render decides which
/// statistic ships. Quantities that are fractions are stored in milli-units
/// too, so a single reader handles all of them.
fn write_confidence_debug(
    dir: &Path,
    c: &Candidates,
    merged_luma: &[f32],
    sigma: &[f32],
    geom: PlaneGeometry,
) -> Result<()> {
    std::fs::create_dir_all(dir)?;
    let px = geom.pixels();
    let quantise = |v: f64| -> u16 {
        let s = (v * 1000.0).round();
        if !s.is_finite() || s >= f64::from(u16::MAX) {
            u16::MAX
        } else if s <= 0.0 {
            0
        } else {
            s as u16
        }
    };
    let mut maps: Vec<(&str, Vec<u16>)> = Vec::new();
    let mut push = |name: &'static str, f: &dyn Fn(usize) -> f64| {
        maps.push((name, (0..px).map(|i| quantise(f(i))).collect()));
    };
    let s = |i: usize| f64::from(sigma[i].max(1.0));
    push("dmin", &|i| f64::from(c.dmin[i]) / s(i));
    push("dsharp", &|i| {
        f64::from((merged_luma[i] - c.l_at_sharp[i]).abs()) / s(i)
    });
    push("spread", &|i| f64::from(c.hi[i] - c.lo[i]) / s(i));
    // 1.0 when the output sits dead centre in the observation cloud, which is
    // what averaging produces; 0.0 when it sits at an extreme, which is what
    // electing a single frame produces.
    push("centrality", &|i| {
        let n = f64::from(c.seen[i].max(1));
        1.0 - 2.0 * (f64::from(c.below[i]) / n - 0.5).abs()
    });
    push("withinfrac", &|i| {
        f64::from(c.within[i]) / f64::from(c.seen[i].max(1))
    });
    for (name, q) in &maps {
        let p = dir.join(format!("{name}.tiff"));
        image_out::write_gray16(&p, geom.width as u32, geom.height as u32, q)?;
        eprintln!("confidence debug: wrote {}", p.display());
    }
    Ok(())
}

/// Write the confidence field as a single-channel 16-bit TIFF.
///
/// **Grid.** The plane grid, identical to [`write_n_eff_map`]'s and to
/// [`write_election_map`]'s: half sensor resolution, one value per 2x2 CFA
/// quad. The three maps overlay pixel-for-pixel with no resampling.
///
/// **Values, and how they differ from `n_eff`'s.** `n_eff` is a literal frame
/// count starting at 1. This is NOT a count -- it is a bounded fraction, in
/// **milli-units**: the stored integer divided by 1000 is how centrally the
/// merged output sits inside the cloud of observations, 0.0 at an extreme of
/// that cloud and 1.0 dead centre. **Low is good.** That is the opposite
/// polarity to `n_eff`, and it is stated here rather than fixed by inverting,
/// because inverting would make the number's name disagree with its arithmetic.
///
/// Milli-units, not the full 16-bit range, because with `frames` observations
/// the rank can only resolve `1/frames` and a finer quantisation would invent
/// precision the data does not have; 1000 steps is already finer than any stack
/// this tool has been run on.
///
/// **Saturation is impossible by construction** -- the field is bounded above
/// by 1.0, which encodes to 1000 -- so the partition below is graded against
/// unreached only. A pixel no frame reached is reported at the ceiling and
/// counted separately, because "no observation" and "perfectly confident" must
/// not encode to the same value.
fn write_confidence_map(path: &Path, c: &Centrality, geom: PlaneGeometry) -> Result<()> {
    ensure!(
        c.below.len() == geom.pixels() && c.seen.len() == geom.pixels(),
        "confidence field is {}/{} long but the plane grid is {}x{}",
        c.below.len(),
        c.seen.len(),
        geom.width,
        geom.height
    );
    let mut q = vec![0u16; c.below.len()];
    // Every pixel lands in exactly one of these, and they sum to the total, so
    // a pixel that was never reached cannot be read as one that scored zero.
    let (mut unreached, mut graded) = (0usize, 0usize);
    let mut sum = 0.0f64;
    for ((o, &b), &s) in q.iter_mut().zip(&c.below).zip(&c.seen) {
        if s == 0 {
            *o = u16::MAX;
            unreached += 1;
            continue;
        }
        let v = 1.0 - 2.0 * (f64::from(b) / f64::from(s) - 0.5).abs();
        *o = (v * 1000.0).round() as u16;
        graded += 1;
        sum += v;
    }
    let n = q.len().max(1);
    image_out::write_gray16(path, geom.width as u32, geom.height as u32, &q)?;
    eprintln!(
        "confidence map  : wrote {} ({}x{} u16 plane grid, milli-units, LOW IS GOOD)",
        path.display(),
        geom.width,
        geom.height
    );
    eprintln!(
        "                  graded {graded} + unreached {unreached} = {} of {n} pixels",
        graded + unreached
    );
    eprintln!(
        "                  mean {:.4} over the {graded} pixels a frame reached",
        sum / graded.max(1) as f64
    );
    eprintln!(
        "                  where the merged output sits inside the cloud of aligned \
         observations.\n                  Zero means the merge committed to an extreme -- it \
         elected a frame. One\n                  means it sat dead centre -- it averaged frames \
         that disagreed and chose\n                  none of them, which is what veiled detail \
         looks like from the inside."
    );
    eprintln!();
    Ok(())
}

/// How many workers the band merge's fold gets.
///
/// Each worker holds a whole accumulator plus one frame's working set, which is
/// hundreds of megabytes, so defaulting to the core count would ask for tens of
/// gigabytes. Solved against the same [`MEMORY_BUDGET_BYTES`] the estimator's
/// plan uses rather than against a hardcoded 3, which is what the example did.
///
/// # Why the core count is deliberately not an input
///
/// This started as `by_memory.min(available_parallelism()).min(frames)`, and
/// that was wrong for a reason worth writing down, because it was measured
/// rather than reasoned about.
///
/// The worker count sets how the fold is partitioned, and `BandMerge::absorb`
/// sums the per-worker accumulators. Float addition is not associative, so a
/// different worker count is a different reduction order and a different image.
/// Measured on flower-bud-alone-cpl, 205 frames: 2 workers against 7 differ on
/// 0.2573% of pixels, `max |delta| = 1 DN`, and *zero* pixels differ by more
/// than 1 DN. So the effect is last-bit rounding and nothing a viewer could
/// ever see -- but it is not nothing, because this repository's regression net
/// is a byte-freeze, and because the same measurement on the two backends
/// returns 99.9895% of pixels and a mean of 1820 DN, which is what a difference
/// that matters actually looks like.
///
/// `available_parallelism()` varies by machine. Leaving it in the default would
/// have meant the shipped default merge produced different bytes on a laptop
/// and a workstation, which is a bad property to hand a user and a worse one to
/// hand a byte-freeze. Every remaining input -- the budget constant, the
/// per-worker size implied by the plane geometry, the frame count -- is a
/// property of the build and the stack, not of the host.
///
/// Nothing is lost on a machine with fewer cores than workers: the workers are
/// rayon tasks, so a core-poor host simply runs them in more passes, and peak
/// memory is bounded by however many are genuinely in flight, which is at most
/// this many and possibly fewer.
fn band_workers(per_worker_bytes: usize, frames: usize) -> Result<usize> {
    if let Ok(v) = std::env::var(BAND_WORKERS_ENV)
        && !v.trim().is_empty()
    {
        let n: usize = v
            .trim()
            .parse()
            .with_context(|| format!("reading {BAND_WORKERS_ENV}={v:?}"))?;
        ensure!(n >= 1, "{BAND_WORKERS_ENV} must be at least 1");
        return Ok(n.min(frames.max(1)));
    }
    let by_memory = (MEMORY_BUDGET_BYTES / per_worker_bytes.max(1)).max(1);
    Ok(by_memory.min(frames.max(1)))
}

const SPLIT_TILE_SIZE: usize = 256;

fn quantise_linear_dn(v: f32) -> u16 {
    if v.is_finite() {
        v.round().clamp(0.0, f32::from(u16::MAX)) as u16
    } else {
        0
    }
}

fn write_split_frc(path: &Path, analysis: &SplitAnalysis) -> Result<()> {
    let file = std::fs::File::create(path)
        .with_context(|| format!("creating split product {}", path.display()))?;
    let mut out = BufWriter::new(file);
    writeln!(out, "radius,frequency,count,cross,power_even,power_odd,frc")?;
    for ring in analysis.aggregate.iter().skip(1) {
        let frc = ring.frc().map(|v| format!("{v:.12}")).unwrap_or_default();
        writeln!(
            out,
            "{},{:.12},{},{:.17e},{:.17e},{:.17e},{}",
            ring.radius,
            ring.frequency,
            ring.count,
            ring.cross,
            ring.power_a,
            ring.power_b,
            frc
        )?;
    }
    Ok(())
}

fn write_split_tile_spectra(path: &Path, analysis: &SplitAnalysis) -> Result<()> {
    let file = std::fs::File::create(path)
        .with_context(|| format!("creating split product {}", path.display()))?;
    let mut out = BufWriter::new(file);
    writeln!(
        out,
        "tile_x,tile_y,origin_x,origin_y,radius,frequency,count,cross,power_even,power_odd,frc"
    )?;
    for tile in &analysis.tiles {
        for ring in tile.rings.iter().skip(1) {
            let frc = ring.frc().map(|v| format!("{v:.12}")).unwrap_or_default();
            writeln!(
                out,
                "{},{},{},{},{},{:.12},{},{:.17e},{:.17e},{:.17e},{}",
                tile.tile_x,
                tile.tile_y,
                tile.origin_x,
                tile.origin_y,
                ring.radius,
                ring.frequency,
                ring.count,
                ring.cross,
                ring.power_a,
                ring.power_b,
                frc
            )?;
        }
    }
    Ok(())
}

fn write_split_acuity(path: &Path, analysis: &SplitAnalysis) -> Result<()> {
    let file = std::fs::File::create(path)
        .with_context(|| format!("creating split product {}", path.display()))?;
    let mut out = BufWriter::new(file);
    writeln!(
        out,
        "tile_x,tile_y,origin_x,origin_y,outcome,frequency_or_bound"
    )?;
    for tile in &analysis.tiles {
        let value = tile
            .crossing
            .frequency()
            .map(|v| format!("{v:.12}"))
            .unwrap_or_default();
        writeln!(
            out,
            "{},{},{},{},{},{}",
            tile.tile_x,
            tile.tile_y,
            tile.origin_x,
            tile.origin_y,
            tile.crossing.label(),
            value
        )?;
    }
    Ok(())
}

/// Collapse and emit the off-by-default split products.
///
/// Both analyses happen before TIFF quantisation. M115 measured shared
/// quantisation error making a difference image under-report by 16x, so moving
/// `analyse_pair` below the `u16` conversion is a correctness bug, not a
/// harmless refactor.
fn write_split_products(
    dir: &Path,
    split: SplitPart,
    geom: PlaneGeometry,
    sizes: &[strehl_core::pyramid::LevelSize],
) -> Result<Crossing> {
    std::fs::create_dir_all(dir)
        .with_context(|| format!("creating split product directory {}", dir.display()))?;
    let SplitPart {
        even,
        odd,
        even_frames,
        odd_frames,
    } = split;
    ensure!(
        even_frames > 0 && odd_frames > 0,
        "cannot finish empty split halves"
    );

    let mut ws = Workspace::new(sizes);
    let mut even_planes = even.finish(&mut ws);
    ensure!(
        even_planes.len() == 1,
        "even split returned {} planes, not 1",
        even_planes.len()
    );
    let even_plane = even_planes.pop().expect("checked one plane");
    drop(even);

    let mut odd_planes = odd.finish(&mut ws);
    ensure!(
        odd_planes.len() == 1,
        "odd split returned {} planes, not 1",
        odd_planes.len()
    );
    let odd_plane = odd_planes.pop().expect("checked one plane");
    drop(odd);
    drop(ws);

    // The correlation and null statistics see f32. Only the display products
    // below quantise, after every decision has been taken.
    let analysis = split::analyse_pair(
        &even_plane,
        &odd_plane,
        geom.width,
        geom.height,
        SPLIT_TILE_SIZE,
    )?;

    let even_path = dir.join("half-even.tiff");
    let odd_path = dir.join("half-odd.tiff");
    let null_path = dir.join("null-signed.tiff");
    let q_even: Vec<u16> = even_plane.iter().copied().map(quantise_linear_dn).collect();
    image_out::write_gray16(
        &even_path,
        geom.width as u32,
        geom.height as u32,
        &q_even,
    )?;
    drop(q_even);
    let q_odd: Vec<u16> = odd_plane.iter().copied().map(quantise_linear_dn).collect();
    image_out::write_gray16(
        &odd_path,
        geom.width as u32,
        geom.height as u32,
        &q_odd,
    )?;
    drop(q_odd);
    let q_null: Vec<u16> = even_plane
        .iter()
        .zip(&odd_plane)
        .map(|(&a, &b)| {
            let v = if a.is_finite() && b.is_finite() {
                (a - b).round() + 32768.0
            } else {
                32768.0
            };
            v.clamp(0.0, f32::from(u16::MAX)) as u16
        })
        .collect();
    image_out::write_gray16(
        &null_path,
        geom.width as u32,
        geom.height as u32,
        &q_null,
    )?;

    write_split_frc(&dir.join("frc.csv"), &analysis)?;
    write_split_tile_spectra(&dir.join("frc-tiles.csv"), &analysis)?;
    write_split_acuity(&dir.join("acuity.csv"), &analysis)?;

    let mut acuity_map = Vec::with_capacity(analysis.tiles.len());
    let mut class_map = Vec::with_capacity(analysis.tiles.len());
    for tile in &analysis.tiles {
        let q = tile
            .crossing
            .frequency()
            .map(|f| (f.clamp(0.0, 0.5) * 131_070.0).round() as u16)
            .unwrap_or(0);
        acuity_map.push(q);
        class_map.push(match tile.crossing {
            Crossing::Insufficient => 0,
            Crossing::Measured(_) => 1,
            Crossing::CensoredAbove { .. } => 2,
            Crossing::CensoredBelow { .. } => 3,
        });
    }
    image_out::write_gray16(
        &dir.join("acuity.tiff"),
        analysis.tiles_x as u32,
        analysis.tiles_y as u32,
        &acuity_map,
    )?;
    image_out::write_gray16(
        &dir.join("acuity-class.tiff"),
        analysis.tiles_x as u32,
        analysis.tiles_y as u32,
        &class_map,
    )?;

    let manifest_path = dir.join("README.txt");
    let file = std::fs::File::create(&manifest_path)
        .with_context(|| format!("creating split product {}", manifest_path.display()))?;
    let mut manifest = BufWriter::new(file);
    writeln!(manifest, "EXPERIMENTAL SPLIT-STACK DIAGNOSTIC; NOT A RESOLUTION CERTIFICATE")?;
    writeln!(manifest, "plane={}x{} native quad pixels", geom.width, geom.height)?;
    writeln!(
        manifest,
        "halves=global filename index parity; even={even_frames}; odd={odd_frames}"
    )?;
    writeln!(
        manifest,
        "tiles={}x{} of {}x{}; centred origin={},{}",
        analysis.tiles_x,
        analysis.tiles_y,
        analysis.tile_size,
        analysis.tile_size,
        analysis.start_x,
        analysis.start_y
    )?;
    writeln!(manifest, "window=mean removal then separable Hann")?;
    writeln!(manifest, "threshold=1/7; three consecutive below-threshold rings required")?;
    writeln!(
        manifest,
        "global_outcome={}; frequency_or_bound={}",
        analysis.crossing.label(),
        analysis
            .crossing
            .frequency()
            .map(|v| format!("{v:.12} cycles/quad-pixel"))
            .unwrap_or_else(|| "none".to_string())
    )?;
    writeln!(manifest, "half TIFFs=above-black camera-linear green DN")?;
    writeln!(manifest, "null-signed.tiff=even-odd DN; zero is code 32768")?;
    writeln!(manifest, "acuity.tiff=0..0.5 cycles/quad-pixel mapped to 0..65535")?;
    writeln!(
        manifest,
        "acuity-class.tiff=0 insufficient, 1 measured, 2 censored above, 3 censored below"
    )?;
    writeln!(
        manifest,
        "WARNING=common sensor structure and shared registration error can raise FRC"
    )?;

    eprintln!(
        "split FRC       : {} {}",
        analysis.crossing.label(),
        analysis
            .crossing
            .frequency()
            .map(|v| format!("{v:.6} cycles/quad-pixel"))
            .unwrap_or_else(|| "without a usable bound".into())
    );
    eprintln!(
        "                  experimental diagnostic only; common-mode sensor structure can \
         correlate both halves."
    );
    Ok(analysis.crossing)
}

/// The `lateral CA` prologue line, reporting the **resolved decision** rather
/// than the switch.
///
/// Those used to be the same thing. They stopped being so when the correction
/// was defaulted on: [`profile_for_capture_env`] returns a profile when the
/// operator is silent and the gear matches, and returns `None` for `off` --
/// which is non-empty and not `"0"`, so the previous check on the raw variable
/// printed `CORRECTING` for a render that was not correcting, and `off` for one
/// that was. **Wrong in both directions, on the one switch the default flip
/// makes load-bearing.** Found by V-CA, who also noted that the recommendation
/// to flip the default had cited this very line as evidence -- it happened to
/// be true there only because the operator had set the variable explicitly.
///
/// Resolved through exactly the call the render makes, from the same first
/// frame, so the line cannot drift from the behaviour it describes without the
/// render drifting too. `optics.rs` calls a silent disagreement between switch
/// and behaviour "the exact failure mode this whole milestone is trying to
/// escape"; this line was an instance of it.
///
/// Shared by both merge prologues on purpose. The estimator -- the default path
/// -- printed no CA line at all, so on the backend most renders actually use, a
/// correction that is now always on was reported nowhere. Two copies of this
/// logic would be free to disagree; one cannot.
fn ca_status_line(first_frame: &Path) -> String {
    let ident = strehl_raw::identity(first_frame);
    let set = std::env::var(strehl_core::optics::CA_ENV).ok();
    let asked = set.as_deref().filter(|k| !k.trim().is_empty());
    match strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3) {
        Ok(Some(p)) => match asked {
            Some(k) => format!("CORRECTING, profile {:?} (operator asked for {k:?})", p.key),
            None => format!("CORRECTING, profile {:?} (gear matched; default on)", p.key),
        },
        Ok(None) => match asked {
            Some(k) => format!("off (operator asked for {k:?})"),
            None => format!(
                "off (no profile for body {:?} / lens {:?})",
                ident.model.as_deref().unwrap_or("UNKNOWN"),
                ident.lens_type3
            ),
        },
        // Unreachable in practice -- an unparseable key fails argument handling
        // long before a render starts -- but stated as `off` because that is
        // what the render would do, and this line's whole purpose is to not
        // guess.
        Err(e) => format!("off (unusable setting: {e})"),
    }
}

/// `strehl stack --merge pyramid`: the Laplacian multi-band merge, on the
/// shipped path.
///
/// This is the merge every good render in this project's corpus came from. It
/// was reachable only from `crates/strehl-cli/examples/blend-render.rs` -- an
/// example, which ships nothing -- and this function is that example's fold
/// wired to the real command, the real registration and the real develop path.
///
/// # What it does that the estimator does not
///
/// Selection is per band and per coefficient rather than per pixel. A depth
/// boundary therefore becomes a transition inside each band's own frequency
/// range instead of a step in the image, and the exponent ramps with scale, so
/// the fine bands run near winner-take-all (all the acuity, and a wrong pick
/// there is one invisible high-frequency coefficient) while the coarse bands
/// stay gently blended (a wrong pick there IS the "cut-out sticker" rim).
///
/// # What it does NOT do, stated because it is a real difference
///
/// * **No photometric normalisation.** `--photometric` is the estimator's, and
///   `main.rs` refuses the pair rather than accepting a flag it would ignore.
/// * **No clip census, no outlier rejection, no halo correction, and no
///   through-focus statistics.** Those are stages of the estimator path and
///   none of them is what this arm is.
/// * **No gate ladder.** Its gate is a band-power threshold, not the
///   estimator's focus-noise gate, and the two are not the same number.
fn run_pyramid(opts: &MergeOptions) -> Result<()> {
    // Ask once, up front, and throw the answer away. `warp_frame_in_place`
    // re-reads the profile per frame, so a typo'd STREHL_FIX_CA would otherwise
    // surface only after a full decode.
    align_cmd::preflight_ca_profile()?;
    let cfg = opts.pyramid;
    ensure!(cfg.bands >= 1, "--pyramid-bands must be at least 1");
    ensure!(
        cfg.gate.is_finite() && cfg.gate >= 0.0,
        "--pyramid-gate must be finite and non-negative"
    );
    ensure!(
        cfg.exponent.is_finite() && cfg.exponent > 0.0,
        "--pyramid-exponent must be finite and positive"
    );
    ensure!(
        cfg.sharpen_per_octave.is_finite() && cfg.sharpen_per_octave >= 1.0,
        "--pyramid-sharpen must be finite and at least 1.0 (1.0 disables the ramp)"
    );
    // Same rule and same reason as the estimator arm: a viewing control asked
    // for without --srgb is an error, refused before a frame is read, because a
    // user who believes they brightened the measurement file and did not has no
    // way to find out.
    let exposure = Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?;

    let t_start = Instant::now();
    let paths = crate::raw_paths(&opts.dir, opts.limit)?;
    let paths = only_frame(paths);
    if opts.split_out.is_some() {
        ensure!(
            paths.len() >= 2,
            "--split-out needs at least two frames, one for each disjoint half"
        );
    }
    ensure!(
        paths.len() < u16::MAX as usize,
        "{} frames exceeds the u16 frame-index range",
        paths.len()
    );

    let t_prologue = Instant::now();
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let prologue_secs = t_prologue.elapsed().as_secs_f64();
    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let wb = first.wb_gains();
    let xyz_to_cam = first.xyz_to_cam_rgb_with_source();
    let frame_bytes = first.allocated_bytes();
    drop(first);

    let noise = profile::noise_model_for(&camera, iso, levels);
    let sizes = level_sizes(geom.width, geom.height, cfg.bands);

    eprintln!("{}", merge_banner(MergeBackend::Pyramid));
    eprintln!("camera          : {camera}");
    eprintln!("lateral CA      : {}", ca_status_line(&paths[0]));
    eprintln!(
        "iso             : {}",
        iso.map(|v| format!("{v:.0}")).unwrap_or("UNKNOWN".into())
    );
    eprintln!(
        "levels          : black {}, white {}",
        levels.black, levels.white
    );
    eprintln!("{}", provenance_line(&noise));

    // ---- sensor defect correction ----------------------------------------
    //
    // Built once here and borrowed by the fold and by both confidence passes,
    // so all three see the identical frames. **Off by default** --
    // `defect_request_from_env` returns `Off` when `STREHL_DEFECT` is unset --
    // because two lanes hunting the same mote disagree by 17x and the
    // contradiction is unadjudicated; see `stack::defect_request_from_env`,
    // which carries that argument in full. When it IS switched on,
    // `defect_preflight` still requires the frames themselves to show the
    // darkening before any site is corrected, which is the staleness argument
    // this answers. This comment read "**On by default**, and safe to be on by
    // default", contradicting the function it cites.
    let defect_request = crate::stack::defect_request_from_env()?;
    let defect_plan = crate::stack::defect_preflight(&defect_request, &noise, &paths)?;
    let defect_tally = crate::stack::DefectTally::default();
    let defect = defect_plan
        .as_ref()
        .map(|p| (p, &defect_tally));
    if let Some(p) = &defect_plan {
        eprintln!("{}", p.describe());
    }
    eprintln!(
        "frames          : {} from {}  (first decode {prologue_secs:.2} s)",
        paths.len(),
        opts.dir.display()
    );
    eprintln!(
        "planes          : {} x {} per CFA plane",
        geom.width, geom.height
    );
    eprintln!("--- the merge ---");
    eprintln!(
        "bands           : {} Laplacian levels + 1 base, coarsest {} x {}",
        sizes.len() - 1,
        sizes[sizes.len() - 1].width,
        sizes[sizes.len() - 1].height
    );
    eprintln!(
        "selection       : {}",
        match cfg.select {
            SelectMode::SoftPower =>
                "SOFT -- weight = (band power above the noise floor)^exponent, a convex \
                 combination.\n                  Sign coherence is free: a convex combination \
                 cannot take adjacent\n                  coefficients from opposite-signed \
                 frames, which is the ringing a\n                  coefficient-wise argmax \
                 produces.",
            SelectMode::HardMax =>
                "HARD -- argmax of band power. THE CONTROL ARM, the textbook PMax rule.",
        }
    );
    eprintln!(
        "noise gate      : {:.2} x the modelled band-noise power. Below it, NO frame may win \
         and the\n                  merge averages -- which is the correct estimator when there \
         is no\n                  information, and the only operation that gets below \
         single-frame noise.",
        cfg.gate
    );
    eprintln!("exponent        : {:.2}", cfg.exponent);
    eprintln!(
        "per-band exp    : {}   (coarsest -> finest)",
        (0..sizes.len() - 1)
            .rev()
            .map(|k| format!("{:.0}", cfg.exponent_at(k, sizes.len() - 1)))
            .collect::<Vec<_>>()
            .join(" ")
    );
    eprintln!(
        "                  sharpness ramps {:.1}x per octave toward the fine bands. A wrong \
         pick in a\n                  fine band is one high-frequency coefficient nobody can \
         see; a wrong pick\n                  in a coarse band IS the rim.",
        cfg.sharpen_per_octave
    );
    eprintln!(
        "base band       : {}",
        match cfg.base {
            BaseBand::Mean => "plain mean across frames",
            BaseBand::WeightedFromCoarsest =>
                "weighted by the coarsest band's weight, reduced once onto the base grid",
        }
    );
    eprintln!(
        "not applied     : photometric gain, clip census, outlier rejection, halo correction, \
         through-focus\n                  statistics. Those are the --merge estimator path's \
         stages; this arm is the merge only."
    );

    // ---- registration -----------------------------------------------------
    //
    // The same resolver the estimator uses, so STREHL_WARPMAP, STREHL_ALIGN and
    // --resampler behave identically on both arms and a sidecar solved for one
    // is the sidecar the other gathers through.
    cover_mode_line(opts);
    let t_align = Instant::now();
    let alignment = alignment_for(&opts.dir, &paths, opts.resampler)?;
    let alignment = alignment.map(|(m, how)| {
        let (m, fit) = align_cmd::cover_or_explain(m, opts.cover);
        (m, how, fit)
    });
    match &alignment {
        Some((map, how, fit)) => {
            let p = map.provenance();
            eprintln!(
                "alignment       : ON ({how}), reference frame {}, {} placed / {} refused, \
                 {:.1} s",
                p.reference,
                map.placed_count(),
                map.refused_count(),
                t_align.elapsed().as_secs_f64()
            );
            eprintln!(
                "  held-out err  : {}   resampler: {:?}",
                p.heldout_px
                    .map(|e| format!("{e:.3} px"))
                    .unwrap_or("NOT MEASURED".into()),
                map.resampler()
            );
            match fit {
                // Same wording, from the same function, as the estimator arm.
                // The two backends resolving one mode from one field and
                // printing it through one function is deliberate: the failure
                // this file has actually shipped is a fix that reached one
                // backend and not the other.
                align_cmd::CoverFit::Cropped { k, rect } => {
                    eprintln!("{}", align_cmd::crop_banner(*k, *rect, map.geometry()))
                }
                align_cmd::CoverFit::Scaled(k) if *k >= 0.999_999 => {
                    eprintln!("  coverage      : every frame covers the whole grid; no crop needed")
                }
                align_cmd::CoverFit::Scaled(k) => eprintln!(
                    "  coverage      : field of view scaled to {k:.4} so that EVERY frame covers \
                     every pixel ({:.1}% of width dropped, then upsampled to keep the output \
                     dimensions).",
                    100.0 * (1.0 - k)
                ),
                align_cmd::CoverFit::Uncovered => eprintln!(
                    "  coverage      : WARNING -- could not fit a fully covered grid; the render \
                     may contain black regions where no frame reaches."
                ),
            }
        }
        None => eprintln!(
            "alignment       : OFF -- frames are combined unregistered. M86 measured 232.7 px of \
             drift on bee-3-cpl."
        ),
    }

    // ---- the fold ---------------------------------------------------------
    let acc_floats = BandMerge::new(geom.width, geom.height, BAND_PLANES, cfg).accumulator_floats();
    let ws_floats = FrameWorkspace::new(&sizes, BAND_PLANES).floats();
    // The plane extraction buffers, the luma and the variance field, and one
    // decoded frame, all of which are live at once inside `fold`.
    let per_worker_bytes =
        4 * (acc_floats + ws_floats + (BAND_PLANES + 2) * geom.pixels()) + frame_bytes;
    let workers = band_workers(per_worker_bytes, paths.len())?;
    // Deliberately do NOT feed the diagnostic memory into `band_workers`.
    // Worker count fixes the ordinary merge's chunk boundaries and therefore
    // its floating-point reduction order. Enabling diagnostics must not change
    // the primary image. Report the real extra allocation instead of hiding it.
    let split_extra_per_worker = if opts.split_out.is_some() {
        let half_acc = BandMerge::new(geom.width, geom.height, 1, cfg).accumulator_floats();
        let half_ws = FrameWorkspace::new(&sizes, 1).floats();
        4 * 2 * (half_acc + half_ws)
    } else {
        0
    };
    let per_chunk = paths.len().div_ceil(workers);
    eprintln!(
        "memory plan     : {workers} workers x {:.0} MB = {:.1} GB against a {} MB budget, \
         CONSTANT in\n                  the frame count. The merge is a fold: every accumulator \
         is a sum, so a\n                  frame is built, added and dropped. \
         {BAND_WORKERS_ENV}=N overrides.",
        per_worker_bytes as f64 / (1 << 20) as f64,
        workers as f64 * per_worker_bytes as f64 / (1 << 30) as f64,
        MEMORY_BUDGET_BYTES / (1 << 20),
    );
    if split_extra_per_worker > 0 {
        eprintln!(
            "split diagnostic : ON, +{:.0} MB per worker ({:.1} GB total live estimate). \
             Worker count is\n                  frozen to the ordinary merge so its reduction \
             order and output bytes cannot move.",
            split_extra_per_worker as f64 / (1 << 20) as f64,
            workers as f64 * (per_worker_bytes + split_extra_per_worker) as f64
                / (1 << 30) as f64,
        );
    }

    let warps = alignment.as_ref().map(|(m, _, _)| m);
    let t_fold = Instant::now();
    let indexed: Vec<(usize, PathBuf)> = paths.iter().cloned().enumerate().collect();
    let parts: Vec<Result<FoldPart>> = indexed
        .par_chunks(per_chunk)
        .map(|chunk| {
            let mut w = BandWorker::new(geom, cfg, opts.split_out.is_some());
            let mut folded = 0usize;
            for (i, p) in chunk {
                if w.fold(p, *i, geom, levels, &noise, warps, defect)? {
                    folded += 1;
                }
            }
            Ok(w.into_part(folded))
        })
        .collect();

    let mut merged: Option<BandMerge> = None;
    let mut split_merged: Option<SplitPart> = None;
    let mut folded_total = 0usize;
    let mut beta_sum: Vec<f64> = Vec::new();
    let mut beta_n = 0usize;
    for part in parts {
        let FoldPart {
            merge: m,
            folded: n,
            beta_sum: bs,
            beta_n: bn,
            split,
        } = part?;
        folded_total += n;
        if beta_sum.len() < bs.len() {
            beta_sum.resize(bs.len(), 0.0);
        }
        for (acc, v) in beta_sum.iter_mut().zip(&bs) {
            *acc += v;
        }
        beta_n += bn;
        match &mut merged {
            Some(a) => a.absorb(&m),
            None => merged = Some(m),
        }
        if let Some(split) = split {
            match &mut split_merged {
                Some(a) => a.absorb(&split),
                None => split_merged = Some(split),
            }
        }
    }
    let merge = merged.context("no frames were folded")?;
    ensure!(
        folded_total > 0,
        "every frame was refused by the alignment solve"
    );
    let fold_secs = t_fold.elapsed().as_secs_f64();
    eprintln!();
    if defect_plan.is_some() {
        crate::stack::print_and_check_defects(&defect_tally)?;
    }
    eprintln!(
        "folded          : {folded_total} / {} frames in {fold_secs:.1} s ({:.2} s per frame, \
         {workers} workers)",
        paths.len(),
        fold_secs / folded_total as f64
    );
    eprintln!(
        "band noise gain : {}",
        merge
            .band_gain()
            .all()
            .iter()
            .map(|b| format!("{b:.4}"))
            .collect::<Vec<_>>()
            .join(" ")
    );
    eprintln!(
        "                  (E[L_k^2] / sigma_0^2, MEASURED on these operators, not derived.)"    );
    if beta_n > 0 {
        let white = merge.band_gain().all();
        let gate_floor_env = gatefloor::GATE_FLOOR_ENV;
        eprintln!(
            "measured floor  : {}",
            beta_sum
                .iter()
                .map(|s| format!("{:.4}", s / beta_n as f64))
                .collect::<Vec<_>>()
                .join(" ")
        );
        eprintln!(
            "                  x white       : {}",
            beta_sum
                .iter()
                .zip(white)
                .map(|(s, w)| format!("{:.4}", (s / beta_n as f64) / f64::from(*w)))
                .collect::<Vec<_>>()
                .join(" ")
        );
        eprintln!(
            "                  THE FLOOR THE GATE ACTUALLY USED, averaged over {beta_n} warped\n  \
                                frames. The line above it is the white-noise constant, which is\n  \
                                exact only for an UNWARPED frame; resampling correlates \
             neighbours\n                  and moves the per-band split. Bands past this list \
             kept the constant.\n                  {gate_floor_env}=white restores it everywhere."
        );
    }
    eprintln!(
        "averaged        : {}",
        merge
            .averaged_fraction()
            .iter()
            .map(|f| format!("{:.1}%", 100.0 * f))
            .collect::<Vec<_>>()
            .join(" ")
    );
    eprintln!(
        "                  per level, the fraction of coefficients where NO frame cleared the \
         noise\n                  floor and the merge therefore averaged instead of selecting. \
         Near 0%\n                  everywhere would mean the gate is not gating and this is a \
         naive\n                  pyramid stacker."
    );
    eprintln!();

    // ---- collapse and write ----------------------------------------------
    if let Some(dir) = &opts.split_out {
        let split = split_merged.context("split diagnostics were requested but not accumulated")?;
        ensure!(
            split.even_frames > 0 && split.odd_frames > 0,
            "alignment left an empty split half (even {}, odd {} frames)",
            split.even_frames,
            split.odd_frames
        );
        let even_frames = split.even_frames;
        let odd_frames = split.odd_frames;
        let t_split = Instant::now();
        write_split_products(dir, split, geom, &sizes)?;
        eprintln!(
            "split products  : {} (even {} / odd {} frames, {:.1} s)",
            dir.display(),
            even_frames,
            odd_frames,
            t_split.elapsed().as_secs_f64()
        );
    }
    let Some(path) = &opts.out else {
        eprintln!(
            "no --out        : no primary image written{}.",
            if opts.split_out.is_some() {
                "; split diagnostic products were written above"
            } else {
                "; the run only proves the fold completes"
            }
        );
        eprintln!("total           : {:.1} s", t_start.elapsed().as_secs_f64());
        return Ok(());
    };
    let t_out = Instant::now();
    let mut ws = Workspace::new(&sizes);
    let planes = merge.finish(&mut ws);
    drop(ws);
    drop(merge);
    ensure!(
        planes.len() == BAND_PLANES,
        "the band merge returned {} planes, not {BAND_PLANES}",
        planes.len()
    );

    // The confidence map, if asked for. Deliberately AFTER `finish` and before
    // the write: the question it answers is about the merged output, so the
    // merged output has to exist first, and reporting it before the image is
    // written means a run that fails to write still leaves the evidence.
    if let Some(cpath) = confidence_map_path(opts) {
        let t_conf = Instant::now();
        let px = geom.pixels();
        let mut merged_luma = vec![0.0f32; px];
        for i in 0..px {
            merged_luma[i] = 0.5 * (planes[1][i] + planes[2][i]);
        }
        let debug_dir = std::env::var("STREHL_CONFIDENCE_DEBUG").ok();
        let conf = if let Some(dir) = &debug_dir {
            // One traversal, not two: the debug pass computes the shipped
            // statistic alongside every rival candidate, so the map still
            // comes from the same observations it would otherwise have come
            // from. The rivals need a noise yardstick; the shipped statistic
            // is a rank and does not.
            let mut var = vec![0.0f32; px];
            luma_variance(&merged_luma, &noise, &mut var);
            let sigma: Vec<f32> = var.iter().map(|v| v.max(1.0).sqrt()).collect();
            let c = confidence_debug_pass(
                &paths,
                geom,
                levels,
                warps,
                defect,
                &merged_luma,
                &sigma,
                per_chunk,
            )?;
            write_confidence_debug(Path::new(dir), &c, &merged_luma, &sigma, geom)?;
            Centrality {
                below: c.below,
                seen: c.seen,
            }
        } else {
            confidence_pass(
                &paths,
                geom,
                levels,
                warps,
                defect,
                &merged_luma,
                per_chunk,
            )?
        };
        if let Some(parent) = cpath.parent() {
            std::fs::create_dir_all(parent).ok();
        }
        write_confidence_map(&cpath, &conf, geom)?;
        eprintln!(
            "                  second pass over {} frames in {:.1} s",
            paths.len(),
            t_conf.elapsed().as_secs_f64()
        );
        eprintln!();
    }

    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    write_merged(
        Merged::Bands {
            geom,
            planes: &planes,
        },
        levels,
        wb,
        xyz_to_cam.as_ref(),
        opts.space,
        opts.demosaic,
        exposure,
        strehl_core::restore::gain_cap_from_env().and_then(|cap| {
            alignment
                .as_ref()
                .map(|(m, _, _)| strehl_core::restore::RestorePlan {
                    resampler: m.resampler(),
                    gain_cap: cap,
                    noise: &noise,
                })
        }),
        // PYRAMID BACKEND -- the default one. Textually identical to the
        // estimator's argument, and it must stay that way.
        alignment.as_ref().and_then(|(_, _, fit)| fit.rect()),
        path,
    )?;
    eprintln!("collapse+write  : {:.1} s", t_out.elapsed().as_secs_f64());
    eprintln!("total           : {:.1} s", t_start.elapsed().as_secs_f64());
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn report(
    opts: &MergeOptions,
    p2: &Pass2,
    p1: &Pass1,
    geom: PlaneGeometry,
    levels: Levels,
    noise: &NoiseModel,
    middle: u16,
    // The response noise scale the gate was actually denominated in on this
    // run: the compiled-in constant by default, the host-measured scale of the
    // contributed operator under `--focus`.
    focus_noise_sd: f32,
) -> Result<()> {
    eprintln!("--- gate calibration (MEASURED) ---");
    eprintln!(
        "                  n_eff is frames averaged per pixel. Fact 212 measured nwide = 3 at full"
    );
    eprintln!(
        "                  sampling density -- frames within 50% of PEAK HEIGHT, which is a \
         different"
    );
    eprintln!(
        "                  rule from this NOISE gate, so 3 is a target to land near, not to match."
    );
    eprintln!(
        "  gate   tol(DN-norm)     mean n_eff   n_eff=1 %   boundary %   pred sigma gain (model)"
    );
    for e in &p2.est {
        let n_eff = e.n_eff();
        let px = n_eff.len();
        let alone = n_eff.iter().filter(|v| **v <= 1).count() as f64 / px as f64;
        let boundary = (0..px).filter(|i| e.at_bracket_boundary(*i)).count() as f64 / px as f64;
        let mean = e.mean_n_eff();
        eprintln!(
            "  {:5.2}  {:12.6}   {:10.3}   {:8.2}%   {:9.2}%   {:>12.4}x",
            e.gate().threshold,
            e.gate().tolerance(),
            mean,
            100.0 * alone,
            100.0 * boundary,
            e.mean_predicted_sigma_gain(noise, levels.black)
        );
    }
    eprintln!();
    report_target_solve(&p2.est, opts.target_n_eff);

    // The clip census and the photometric bound are correctness statements about
    // the stack, not diagnostics about an ROI, so they must not be gated behind
    // an ROI flag. Reported before the early return for exactly that reason.
    eprintln!();
    report_clip_census(&p1.clip);
    eprintln!();
    report_photometric_sensitivity(
        p1.stats.best_focus(),
        // The gate unit belongs to the operator that produced this field, not
        // to the shipped constant. Under --focus sml-w13 the two differ by
        // 6.6x, and a sensitivity quoted in the wrong unit is a number that
        // reads as evidence and is not.
        focus_noise_sd,
    );
    eprintln!();

    let Some(roi) = opts.flat_roi else {
        eprintln!(
            "flat ROI        : not requested. Pass --flat-roi X,Y,W,H for the noise invariant."
        );
        return Ok(());
    };
    let single = p1
        .flat
        .as_ref()
        .context("the middle frame's flat ROI was never captured")?;

    eprintln!("--- ACCEPTANCE INVARIANT 1 of 2: flat-ROI noise (MEASURED) ---");
    eprintln!(
        "roi             : x {} y {} w {} h {} in plane coordinates",
        roi.x, roi.y, roi.width, roi.height
    );
    let (single_mean, single_sigma) = mean_and_sigma(single);
    let model_sigma = f64::from(noise.green_luma_sigma(single_mean as f32));
    eprintln!(
        "single frame {middle:<3}: raw sd {single_sigma:8.3} DN   mean {single_mean:9.2} DN   \
         (no stacking at all)"
    );
    eprintln!(
        "model predicts  : sigma {model_sigma:8.3} DN for one green-luma sample at that level, \
         so this"
    );
    eprintln!(
        "                  ROI's RAW sd is {:.2}x the noise in it -- that excess is scene, and \
         it is",
        single_sigma / model_sigma
    );
    eprintln!("                  why the raw ratio below is a LEGACY column and not the verdict.");

    // ---- the noise statistic ----------------------------------------------
    let per_frame: Vec<(u16, f64)> = p1
        .flat_frames
        .iter()
        .filter_map(|(i, f)| f.hp_sd.map(|v| (*i, v)))
        .collect();
    let reference = flat_ratio::FlatReference::new(&per_frame);
    match &reference {
        Some(reference) => {
            eprintln!();
            report_hp_reference(reference, model_sigma, "                  ");
            eprintln!(
                "  gate       hp sd DN     HP RATIO   over every frame     n frames   \
                 vs frame {middle} alone"
            );
            for e in &p2.est {
                let s = flat_roi_stats(e, single, roi, geom, levels.black);
                match s.stacked_hp_sd {
                    Some(hp) => {
                        let r = reference.ratio(hp);
                        // The last column is exactly the number the old
                        // convention would have printed: one privileged frame in
                        // the denominator. It is here so fact 441's spread is
                        // visible as a difference, not only as an interval.
                        let privileged = s
                            .single_hp_sd
                            .map(|d| format!("{:.3}x", hp / d))
                            .unwrap_or_else(|| "n/a".into());
                        eprintln!(
                            "  {:5.2}   {:10.3}   {:9.3}x   [{:6.3}x .. {:6.3}x]   {:>8}   \
                             {:>14}",
                            e.gate().threshold,
                            hp,
                            r.median,
                            r.lo,
                            r.hi,
                            reference.frames(),
                            privileged
                        );
                    }
                    None => eprintln!(
                        "  {:5.2}   ROI is smaller than one {}x{} high-pass box",
                        e.gate().threshold,
                        flat_ratio::HP_BOX_SIDE,
                        flat_ratio::HP_BOX_SIDE
                    ),
                }
            }
            eprintln!(
                "                  PASS is <= 1.000x against the SAME-OPERATOR baseline: \
                 regularised argmax."
            );
            eprintln!(
                "                  Fact 19's 1.253x was a DIFFERENT focus operator and does \
                 not reproduce"
            );
            eprintln!(
                "                  here; it is not this pipeline's baseline and must not be \
                 quoted as one."
            );
            eprintln!(
                "                  A plain unweighted mean measured 0.534x on the LEGACY \
                 statistic, which"
            );
            eprintln!(
                "                  is a floor and not a target, because of invariant 2. \
                 THE BASELINE FOR"
            );
            eprintln!(
                "                  THIS COLUMN HAS NOT BEEN RE-MEASURED: fact 343's 1.0739x is \
                 a RAW-sd"
            );
            eprintln!(
                "                  number and cannot be carried across to a high-pass sd. Run \
                 `strehl stack`"
            );
            eprintln!(
                "                  on the same frames and ROI for the same-operator argmax \
                 figure."
            );
        }
        None => {
            eprintln!();
            eprintln!(
                "HP RATIO        : NOT AVAILABLE -- no frame's flat ROI holds a whole {}x{} \
                 high-pass box.",
                flat_ratio::HP_BOX_SIDE,
                flat_ratio::HP_BOX_SIDE
            );
        }
    }

    // ---- the number this replaced, kept readable ---------------------------
    eprintln!();
    eprintln!("  gate    LEGACY raw sd    mean DN   LEGACY RATIO   winners in roi");
    for e in &p2.est {
        let s = flat_roi_stats(e, single, roi, geom, levels.black);
        eprintln!(
            "  {:5.2}   {:9.3}   {:11.2}   {:8.3}x   {} distinct, median {}",
            e.gate().threshold,
            s.stacked_sigma,
            s.stacked_mean,
            s.legacy_raw_ratio,
            s.distinct_winners,
            s.median_winner
        );
    }
    eprintln!(
        "                  DO NOT READ THE LEGACY COLUMN AS NOISE (facts 469/441/442/455, \
         597). It"
    );
    eprintln!("                  is a ratio of two RAW SPATIAL sds against ONE arbitrary frame.");
    eprintln!(
        "                  It is structure-dominated -- the corpus's flat reference frames are \
         50.9-80.0%"
    );
    eprintln!(
        "                  scene by variance and this ROI's own excess is printed above -- it \
         moves"
    );
    eprintln!(
        "                  over a 1.60x range with the free choice of denominator frame, and on \
         a"
    );
    eprintln!(
        "                  planted noise explosion it under-reported by 6.3x. It is printed \
         only so"
    );
    eprintln!("                  that reports written before this change stay comparable.");
    eprintln!();

    let Some(droi) = opts.detail_roi else {
        eprintln!(
            "detail ROI      : NOT REQUESTED. Invariant 1 ALONE IS NOT A RESULT -- a plain mean \
             wins it"
        );
        eprintln!(
            "                  at 0.534x while collapsing detail 58% (fact 24). Pass \
             --detail-roi X,Y,W,H."
        );
        return Ok(());
    };
    let selector = p2
        .selector
        .as_ref()
        .context("the gate-zero selector ROIs were not captured")?;
    let selector_flat_sigma: Vec<f32> = selector
        .flat
        .values
        .iter()
        .map(|v| noise.green_luma_sigma(*v))
        .collect();
    let selector_detail_sigma: Vec<f32> = selector
        .detail
        .values
        .iter()
        .map(|v| noise.green_luma_sigma(*v))
        .collect();
    let selector_controlled = cross_fitted_detail(
        GradientRoi::new(
            &selector.detail.values,
            &selector_detail_sigma,
            droi.width,
            droi.height,
        ),
        GradientRoi::new(
            &selector.flat.values,
            &selector_flat_sigma,
            roi.width,
            roi.height,
        ),
    )
    .context("building the gate-zero detail reference")?;
    let selector_metrics = detail_metrics(
        &selector.detail.values,
        &selector_detail_sigma,
        droi.width,
        droi.height,
    );
    let selector_z = selector_controlled.signal_power / selector_controlled.signal_standard_error;
    let selector_target = if detail_target_is_measurable(selector_controlled) {
        "MEASURABLE"
    } else {
        "NOT-MEASURABLE"
    };

    eprintln!("--- ACCEPTANCE INVARIANT 2 of 2: detail retention (MEASURED) ---");
    eprintln!(
        "roi             : x {} y {} w {} h {} in plane coordinates",
        droi.x, droi.y, droi.width, droi.height
    );
    eprintln!(
        "                  THIS IS A ONE-SIDED TEST. It is valid against COLLAPSE and against"
    );
    eprintln!(
        "                  nothing else. mean|grad| can be RAISED by ringing, by amplified noise"
    );
    eprintln!(
        "                  and by manufactured edges, so an INCREASE is never evidence of quality."
    );
    eprintln!(
        "                  MEASURED in the orchestrator's calibrated 1-D optics simulation (25"
    );
    eprintln!(
        "                  frames, oracle depth, latent mean|grad| 0.0392): at sigma 0.010 a Wiener"
    );
    eprintln!(
        "                  merge reads 0.0367 against selection's 0.0296 -- 24% MORE gradient --"
    );
    eprintln!(
        "                  while its gradient CORRELATION with truth is 0.7538 against 0.8595, i.e."
    );
    eprintln!(
        "                  12% LESS faithful. At sigma 0.050 argmax reads 0.0455, ABOVE the ground"
    );
    eprintln!(
        "                  truth. A mean-gradient test scores both of those as wins. It must not."
    );
    eprintln!(
        "                  MEAN |GRAD| IS ALSO CONFOUNDED BY NOISE and selection conditions that"
    );
    eprintln!(
        "                  noise on a max over N. A model sigma knows neither the max nor N."
    );
    eprintln!(
        "                  Each row therefore MEASURES its inflation on the flat ROI, separately"
    );
    eprintln!(
        "                  in the left/right halves, and applies the OPPOSITE half's scale to detail."
    );
    eprintln!(
        "                  STRUCTURE = raw / controlled-noise: pure noise reads 1.0x; real detail"
    );
    eprintln!(
        "                  reads above it. RETENTION is N/A unless the SELECTOR'S resolved detail"
    );
    eprintln!(
        "                  clears a one-sided model-derived 99% bound (alpha {:.2}). If it does,",
        DETAIL_FALSE_ANSWER_RATE
    );
    eprintln!(
        "                  retention compares resolved signal at the SAME selector noise floor,"
    );
    eprintln!(
        "                  against the full-stack gate-zero selector -- never one arbitrary frame."
    );
    eprintln!("                  The flat scale is re-measured per gate, so its N and");
    eprintln!(
        "                  admission dependence come from this run rather than a transferred bar."
    );
    eprintln!(
        "selector gate 0 : q {:+10.3} +/- {:8.3} DN^2   z {:+7.3}   target {:14}   \
         STRUCTURE {:7.3}x   raw {:9.4}   ctrl noise {:9.4}   k(L/R) {:6.3}/{:6.3}   \
         m2 {:8.4}   iso {:8.4}",
        selector_controlled.signal_power,
        selector_controlled.signal_standard_error,
        selector_z,
        selector_target,
        selector_controlled.structure,
        selector_controlled.raw_power.sqrt(),
        selector_controlled.controlled_noise_power.sqrt(),
        selector_controlled.inflation_left,
        selector_controlled.inflation_right,
        selector_metrics.m2_pooled_abs,
        selector_metrics.iso_mean
    );
    eprintln!(
        "  gate     q signal    RETENTION   VERDICT    STRUCTURE     raw rms  ctrl noise   \
         k left  k right         m2        iso"
    );
    for e in &p2.est {
        let merged_detail = roi_green_merged(e, droi, geom, levels.black);
        let detail_sig: Vec<f32> = (droi.y..droi.y + droi.height)
            .flat_map(|py| (droi.x..droi.x + droi.width).map(move |px| (px, py)))
            .map(|(px, py)| e.predicted_sigma(noise, geom.index(px, py), levels.black))
            .collect();
        let merged_flat = roi_green_merged(e, roi, geom, levels.black);
        let flat_sig: Vec<f32> = (roi.y..roi.y + roi.height)
            .flat_map(|py| (roi.x..roi.x + roi.width).map(move |px| (px, py)))
            .map(|(px, py)| e.predicted_sigma(noise, geom.index(px, py), levels.black))
            .collect();
        let controlled = cross_fitted_detail(
            GradientRoi::new(&merged_detail, &detail_sig, droi.width, droi.height),
            GradientRoi::new(&merged_flat, &flat_sig, roi.width, roi.height),
        )
        .with_context(|| format!("gate {} detail control", e.gate().threshold))?;
        let m = detail_metrics(&merged_detail, &detail_sig, droi.width, droi.height);
        let retention = equal_noise_retention(controlled, selector_controlled);
        match retention {
            DetailRetention::Measured(retention) => eprintln!(
                "  {:5.2}   {:+10.3}   {:9.3}x   {:9}   {:9.3}x   {:9.4}   {:9.4}   \
                 {:7.3}  {:7.3}   {:8.4}   {:8.4}",
                e.gate().threshold,
                controlled.signal_power,
                retention,
                detail_verdict(retention),
                controlled.structure,
                controlled.raw_power.sqrt(),
                controlled.controlled_noise_power.sqrt(),
                controlled.inflation_left,
                controlled.inflation_right,
                m.m2_pooled_abs,
                m.iso_mean
            ),
            DetailRetention::NotMeasurable => eprintln!(
                "  {:5.2}   {:+10.3}         N/A   NO TARGET   {:9.3}x   {:9.4}   {:9.4}   \
                 {:7.3}  {:7.3}   {:8.4}   {:8.4}",
                e.gate().threshold,
                controlled.signal_power,
                controlled.structure,
                controlled.raw_power.sqrt(),
                controlled.controlled_noise_power.sqrt(),
                controlled.inflation_left,
                controlled.inflation_right,
                m.m2_pooled_abs,
                m.iso_mean
            ),
        }
    }
    eprintln!(
        "                  q is SIGNED resolved gradient power. A negative q means the ROI has no"
    );
    eprintln!(
        "                  resolved detail above the cross-fitted flat control; it is not clamped"
    );
    eprintln!(
        "                  before retention. At high STRUCTURE, RETENTION approaches resolved"
    );
    eprintln!(
        "                  signal amplitude. NO TARGET is not a pass: the ratio is not identified."
    );
    eprintln!(
        "                  A rise is INVESTIGATE, not PASS: see the speckle companion below, which"
    );
    eprintln!("                  is two-sided and shares a cause with manufactured detail.");
    eprintln!();

    // The two-sided companion. mean|grad| cannot tell manufactured detail from
    // real detail; a winner-index map can, because ringing and amplified noise
    // both decorrelate the winner from its neighbours and speckle is exactly
    // that decorrelation. This is the SAME `speckle_fraction` the argmax
    // baseline is quoted against (`strehl stack`), on the merge's own
    // regularised winner, so the two numbers are directly comparable.
    let speckle = speckle_fraction(p1.stats.best_index(), geom, SPECKLE_TOLERANCE);
    eprintln!("--- COMPANION (two-sided): winner-index speckle (MEASURED) ---");
    eprintln!(
        "index speckle   : {:.3}% of pixels differ by more than {SPECKLE_TOLERANCE} from their \
         3x3 median index",
        100.0 * speckle
    );
    eprintln!(
        "                  On the REGULARISED winner, the same statistic and tolerance `strehl \
         stack`"
    );
    eprintln!(
        "                  reports for argmax. Unlike mean|grad| this is two-sided: a real scene \
         gives"
    );
    eprintln!(
        "                  smooth depth with sharp edges, and BOTH over-smoothing and \
         manufactured"
    );
    eprintln!("                  detail move it away from that.");
    eprintln!(
        "                  Fact 23's 34.4% -> 0.868% pair is BOTH the retired ring operator, \
         unregularised"
    );
    eprintln!(
        "                  then 17x17-regularised (M2-verification section 4; :205 states the \
         measure"
    );
    eprintln!(
        "                  was the ring difference, and Tenengrad did not exist until M14). \
         NEITHER is a"
    );
    eprintln!(
        "                  Tenengrad number, and no section-4 row publishes a \
         regularised-Tenengrad"
    );
    eprintln!(
        "                  speckle at all, so there is no cross-operator reference to quote \
         here. The"
    );
    eprintln!(
        "                  operator-matched figure is fact 71's 1.010% for UNREGULARISED \
         Tenengrad on"
    );
    eprintln!(
        "                  this ROI; the regularised comparable is this run's own value, above."
    );
    Ok(())
}

/// Samples pinned at the raw container maximum, and what they do to confidence.
///
/// Always reported, not hidden behind `--stats`, because a clipped pixel is a
/// correctness question rather than a diagnostic one. On a clean stack this
/// costs one comparison per sample and prints zeros — M26 measured that four of
/// six stacks in this corpus have no saturated pixels at all.
fn report_clip_census(clip: &ClipCensus) {
    let ever = clip.ever_clipped_fraction();
    let always = clip.always_clipped_fraction();
    let total = clip.geometry().pixels();
    eprintln!("--- CLIPPING CENSUS (MEASURED) ---");
    eprintln!(
        "container max   : {CONTAINER_MAX_DN} DN. NOT the usable white level (15360) -- these are"
    );
    eprintln!(
        "                  two different numbers for two different purposes and both are right:"
    );
    eprintln!("                  15360 bounds the noise model's calibrated range, 16383 is what");
    eprintln!("                  \"this sample is pinned\" means. Do not unify them.");
    eprintln!(
        "ever clipped    : {:.4}% of pixels ({} of {}) clipped in at least one frame",
        100.0 * ever,
        (ever * total as f64).round() as u64,
        total
    );
    eprintln!(
        "always clipped  : {:.4}% of pixels ({} of {}) pinned in EVERY frame",
        100.0 * always,
        (always * total as f64).round() as u64,
        total
    );
    if always > 0.0 {
        eprintln!(
            "                  ^ these carry ZERO focus information. M26 measured 616 such px on"
        );
        eprintln!(
            "                  coffee-bubbles reading cross-frame focus contrast 1.0000, the"
        );
        eprintln!(
            "                  metric's MAXIMUM, against 0.5398 median on never-clipped px --"
        );
        eprintln!(
            "                  because 85.9% of them have f_min exactly 0 (inside a uniformly"
        );
        eprintln!(
            "                  clipped blob the gradient is identically zero) while f_max is 52x"
        );
        eprintln!(
            "                  typical (the blob edge crosses them in another frame). Discipline"
        );
        eprintln!("                  29 does NOT protect against this: it preferred cross-frame");
        eprintln!("                  contrast to focus magnitude, but on a pinned pixel BOTH read");
        eprintln!("                  their maximum, so they fail in the same direction.");
    } else {
        eprintln!(
            "                  No pixel is pinned in every frame, so the maximum-severity case"
        );
        eprintln!("                  M26 measured on coffee-bubbles does not arise on this stack.");
    }
    eprintln!("                  NOTE 109MSDCF and 119MSDCF are two of the four stacks with NO");
    eprintln!("                  saturation, and 109 is also the quietest photometrically (M24).");
    eprintln!("                  A clean result on them is systematically weaker evidence than it");
    eprintln!("                  looks.");
}

/// How far a per-frame photometric gain drift moves the gate, in gate units.
///
/// # Why this exists, and what it does NOT do
///
/// There is **no per-frame gain term in this merge** (see the module note on
/// `Estimator`). M24 measured that this corpus really does drift: 0.91% peak to
/// peak on `109MSDCF`, 2.88% on `119MSDCF`, and **11.70% on `coffee-bean`**. So
/// the omission has a price, and this prints it rather than leaving it implicit.
///
/// # The conversion, and its one assumption
///
/// The focus response is `box_mean(|grad L|) / sigma(L)`, so scaling a frame's
/// signal by `g` scales the numerator by exactly `g`. In the shot-noise-limited
/// regime `sigma ~ sqrt(S)`, so the denominator scales by `sqrt(g)` and the
/// normalised response scales by **`sqrt(g)`**. A fractional level drift `d`
/// therefore moves the response by `d/2` of itself. That is DERIVED, and it is
/// an UPPER BOUND on the read-noise-dominated end, where sigma is flat in signal
/// and the response scales by the full `g` instead — in deep shadow the
/// sensitivity is twice what is printed here.
///
/// Expressed in gate units, because that is the only scale on which "does this
/// matter" has an answer: one gate unit is `sqrt(2) * FOCUS_NOISE_SD`, the SD of
/// a *difference* of two regularised responses.
fn report_photometric_sensitivity(best_focus: &[f32], noise_sd: f32) {
    let mut f: Vec<f32> = best_focus
        .iter()
        .copied()
        .filter(|v| v.is_finite())
        .collect();
    if f.is_empty() {
        return;
    }
    f.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let q = |p: f64| -> f64 { f[((p * (f.len() - 1) as f64) as usize).min(f.len() - 1)] as f64 };
    let (med, p10, p90) = (q(0.5), q(0.10), q(0.90));
    let unit = (2.0f64).sqrt() * noise_sd as f64;
    // Gate units moved per 1% of level drift: (d/2) * F / unit, with d = 0.01.
    let per_pct = |focus: f64| 0.5 * 0.01 * focus / unit;
    eprintln!("--- PHOTOMETRIC DRIFT SENSITIVITY (DERIVED from a MEASURED response) ---");
    eprintln!(
        "winner response : median {med:.4}, p10 {p10:.4}, p90 {p90:.4}  (regularised, \
         DN-normalised)"
    );
    eprintln!(
        "gate unit       : {unit:.6}  = sqrt(2) * the focus noise sd IN FORCE, the SD of a \
         difference"
    );
    eprintln!(
        "sensitivity     : {:.3} gate units per 1% of per-frame level drift (median pixel),",
        per_pct(med)
    );
    eprintln!(
        "                  {:.3} at p10 and {:.3} at p90. Shot-limited; in read-noise-",
        per_pct(p10),
        per_pct(p90)
    );
    eprintln!("                  dominated shadow it is 2x this.");
    eprintln!(
        "corpus (M24)    : 109MSDCF drifts 0.91% -> {:.2} gate units. 119MSDCF 2.88% -> {:.2}.",
        per_pct(med) * 0.91,
        per_pct(med) * 2.88
    );
    eprintln!(
        "                  coffee-bean 11.70% -> {:.2}. coffee-bubbles 8.93% -> {:.2}.",
        per_pct(med) * 11.70,
        per_pct(med) * 8.93
    );
    eprintln!("                  109MSDCF is the QUIETEST stack in the corpus and is the one most");
    eprintln!(
        "                  of this project's numbers were measured on, so a clean 109 result"
    );
    eprintln!("                  is NOT evidence that photometric variation is handled.");
    eprintln!("STATUS          : NO per-frame gain term is fitted or applied. This merge assumes");
    eprintln!(
        "                  constant photometry across the stack. The number above is the size"
    );
    eprintln!(
        "                  of that assumption, not a correction for it. Do NOT read gain from"
    );
    eprintln!("                  EXIF to fix it: M24 measured two stacks drifting 6.84% and 8.93%");
    eprintln!("                  with CONSTANT EXIF, and coffee-bean moving only 16% of what its");
    eprintln!("                  EXIF change predicts (1.0443 measured vs 1.2800). Fit it.");
}

/// One-sided reading of an equal-noise retention ratio.
///
/// **Deliberately never returns "PASS" for a value above 1.** The orchestrator
/// MEASURED (calibrated 1-D optics simulation, 25 frames, oracle depth, 2026-08)
/// that a Wiener merge can carry **24% more** mean|grad| than selection while
/// having **12% less** gradient correlation with the truth, and that at sigma
/// 0.050 argmax selection reads mean|grad| *above the ground truth's*. Every one
/// of those is a merge inventing detail, and every one of them would be scored a
/// win by a two-sided reading of this number.
///
/// This merge is a regulariser plus a noise gate, not a deconvolution, so it is
/// not itself at risk of manufacturing detail. The verdict exists so the TEST
/// cannot be gamed by a later merge that is.
fn detail_verdict(retention: f64) -> &'static str {
    if retention < DETAIL_COLLAPSE_FLOOR {
        "COLLAPSE"
    } else if retention > DETAIL_RISE_FLAG {
        "INVESTIG."
    } else {
        "ok"
    }
}

/// Equal-noise retention below this is fact 24's collapse.
///
/// The reference is now the full-stack gate-zero selector, with candidate and
/// reference compared at the same measured noise floor. At high structure,
/// 0.90 therefore means a 10% resolved-gradient amplitude loss instead of a
/// ratio to an arbitrarily defocused middle frame. The value is deliberately
/// not tuned here: it still sits well above fact 24's measured 53-58% collapse
/// and the simulated plain mean's 49-51%, but whether 10% is the right product
/// tolerance is a separate decision.
const DETAIL_COLLAPSE_FLOOR: f64 = 0.90;

/// Equal-noise retention above this is a flag to investigate, never a pass.
///
/// The selector reference has already searched the full bracket for focus. A
/// merge carrying 50% more resolved gradient than that reference is therefore
/// a reason to inspect ringing or manufactured texture, never evidence of
/// quality from this one-sided statistic.
const DETAIL_RISE_FLAG: f64 = 1.50;

// Pinned at compile time rather than in a test, because these are relationships
// between constants and a build that violates one should not link.
//
// The rise flag sits above identity so small measurement scatter is not itself
// labelled as manufactured detail.
const _: () = assert!(DETAIL_RISE_FLAG > 1.0);
// The collapse floor must sit above the -49% a plain mean produces in the
// orchestrator's simulation and the -58%/-53% fact 24 measured, or it cannot
// catch the failure it exists for.
const _: () = assert!(DETAIL_COLLAPSE_FLOOR > 0.51);
// And the band must be non-empty, or every reading is a verdict.
const _: () = assert!(DETAIL_COLLAPSE_FLOOR < DETAIL_RISE_FLAG);

/// Report the through-focus sufficient statistics, with their null.
///
/// Every channel here is reported next to the placebo that says what it would
/// read on the same frames with the focus ordering destroyed. That is the only
/// way any of these numbers means anything: the bimodality screen in particular
/// is a max-minus-min and is **large by construction** even on pure noise.
fn report_statistics(
    opts: &MergeOptions,
    p2: &Pass2,
    clip: &ClipCensus,
    geom: PlaneGeometry,
    levels: Levels,
    noise: &NoiseModel,
    perm: &[u16],
) -> Result<()> {
    let Some(tf) = p2.tf.as_ref() else {
        return Ok(());
    };
    let px = geom.pixels();
    let frames = tf.frames_folded() as usize;

    eprintln!();
    eprintln!("--- through-focus sufficient statistics (MEASURED) ---");
    eprintln!(
        "                  Gathered in PASS TWO, anchored on pass one's regularised winner, so"
    );
    eprintln!(
        "                  no third pass over the frames is needed to compute a sub-frame peak,"
    );
    eprintln!("                  a top-k list or a bimodality statistic from them.");
    eprintln!(
        "scale           : {}x{} box on the focus field (fact 152: bimodality is DEPLETED, 0.36x,",
        2 * STATS_RADIUS + 1,
        2 * STATS_RADIUS + 1
    );
    eprintln!(
        "                  at the {REGULARISER_WIDTH}x{REGULARISER_WIDTH} selection scale and only \
         appears at radius {STATS_RADIUS})"
    );
    eprintln!(
        "fine noise sd   : {FINE_FOCUS_NOISE_SD:.6}, MEASURED in-crate. The selection field's is \
         {FOCUS_NOISE_SD:.6},"
    );
    eprintln!(
        "                  but THESE TWO DO NOT DIVIDE. The fine sd is measured with NO \
         regulariser and"
    );
    eprintln!(
        "                  the selection sd with the \
         {REGULARISER_WIDTH}x{REGULARISER_WIDTH} box, so their ratio mixes a window-radius"
    );
    eprintln!(
        "                  change with the presence of a regulariser. Put both at the same \
         regularisation"
    );
    eprintln!(
        "                  and let only the operator window differ and k = 1.815 (fact 500, \
         verified"
    );
    eprintln!(
        "                  independently by M52 at 1.8145). The printed pair's ratio is 5.94 and \
         is NOT"
    );
    eprintln!(
        "                  a k: it overstates the seam by 3.27x. Both constants are correct as \
         consumed."
    );
    eprintln!(
        "memory          : {} B/px = {:.0} MB per gather, CONSTANT in the frame count.",
        ThroughFocus::bytes_per_pixel(),
        tf.allocated_bytes() as f64 / 1e6
    );
    eprintln!(
        "                  A fine focus VOLUME for these {frames} frames would be {} B/px = \
         {:.0} MB and is O(frames).",
        4 * frames,
        (px * 4 * frames) as f64 / 1e6
    );
    eprintln!(
        "                  Break-even is {} frames; the ratchet holds from there up without bound.",
        ThroughFocus::bytes_per_pixel().div_ceil(4)
    );
    eprintln!();

    // (a) sub-frame peak
    let offsets: Vec<f32> = (0..px).filter_map(|i| tf.subframe_offset(i)).collect();
    let deficits: Vec<f32> = (0..px).filter_map(|i| tf.subframe_deficit(i)).collect();
    eprintln!("(a) SUB-FRAME PEAK, by parabola on the fine triple");
    eprintln!(
        "  fitted        : {:.3}% of pixels have a complete concave triple",
        100.0 * offsets.len() as f64 / px as f64
    );
    if !offsets.is_empty() {
        let mean_abs = offsets.iter().map(|v| v.abs() as f64).sum::<f64>() / offsets.len() as f64;
        let near_half = offsets.iter().filter(|v| v.abs() > 0.4).count() as f64;
        eprintln!("  mean |offset| : {mean_abs:.4} frames");
        eprintln!(
            "  |offset|>0.4  : {:.3}% of fitted pixels are nearly half a frame from their peak",
            100.0 * near_half / offsets.len() as f64
        );
    }
    if !deficits.is_empty() {
        let mut d = deficits.clone();
        d.sort_by(|a, b| a.partial_cmp(b).unwrap());
        eprintln!(
            "  deficit (C3)  : median {:.4}, p90 {:.4}, p99 {:.4}   (log fit with baseline \
             subtraction, facts 272/304)",
            d[d.len() / 2],
            d[d.len() * 9 / 10],
            d[d.len() * 99 / 100]
        );
    }
    let disagree = (0..px).filter(|i| !tf.anchor_is_fine_argmax(*i)).count();
    let outside = (0..px).filter(|i| tf.fine_peak_outside_triple(*i)).count();
    eprintln!(
        "  scale disagree: {:.3}% of pixels have a fine argmax different from the regularised \
         winner",
        100.0 * disagree as f64 / px as f64
    );
    eprintln!(
        "  outside triple: {:.3}% have it further than {PEAK_SEPARATION} frames away -- the \
         SCREENING form",
        100.0 * outside as f64 / px as f64
    );
    eprintln!(
        "                  The first is a diagnostic and is expected to be large. The fine field \
         differs"
    );
    eprintln!(
        "                  from the selection field in TWO ways -- a smaller operator window AND \
         no"
    );
    eprintln!(
        "                  regulariser -- so its argmax moves for both reasons. At matched \
         regularisation"
    );
    eprintln!(
        "                  it is noisier by k = 1.815 (fact 500), not the 5.94 the ratio of the \
         two"
    );
    eprintln!(
        "                  published constants suggests. The second is the actionable one, \
         because"
    );
    eprintln!("                  off-by-one is still bracketed by the parabola.");
    eprintln!();

    // (b) top-k
    let full = (0..px)
        .filter(|i| tf.top_indices(*i).iter().all(|k| *k != u16::MAX))
        .count();
    let spread: Vec<f32> = (0..px)
        .map(|i| {
            let t = tf.top_values(i);
            t[0] - t[TOP_K_LAST]
        })
        .filter(|v| v.is_finite())
        .collect();
    eprintln!("(b) TOP-K, k = 4 on the fine field");
    eprintln!(
        "  complete      : {:.3}% of pixels have all four slots filled",
        100.0 * full as f64 / px as f64
    );
    if !spread.is_empty() {
        let mean = spread.iter().map(|v| *v as f64).sum::<f64>() / spread.len() as f64;
        eprintln!(
            "  top1 - top4   : mean {mean:.4} = {:.2} fine sigma",
            mean / (std::f64::consts::SQRT_2 * FINE_FOCUS_NOISE_SD as f64)
        );
    }
    eprintln!();

    // (c) bimodality, against the placebo
    let bimodal: Vec<f32> = (0..px).filter_map(|i| tf.bimodality_sigma(i)).collect();
    eprintln!("(c) BIMODALITY -- an UPPER BOUND on the prominence of a separated second peak");
    // Sort ONCE. An earlier draft passed an unsorted slice to a closure that
    // sorted a copy per call, and one of those calls was inside a per-pixel
    // loop: 8.2 million sorts of an 8.2 million element vector. It did not
    // finish. Sorting up front is the whole fix.
    let mut bimodal_sorted = bimodal.clone();
    bimodal_sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let quant = |s: &[f32], q: f64| -> f32 {
        if s.is_empty() {
            return 0.0;
        }
        s[((q * (s.len() - 1) as f64) as usize).min(s.len() - 1)]
    };
    let real_mean = if bimodal.is_empty() {
        0.0
    } else {
        bimodal.iter().map(|v| *v as f64).sum::<f64>() / bimodal.len() as f64
    };
    eprintln!(
        "  real          : mean {real_mean:.3} sigma, median {:.3}, p99 {:.3}",
        quant(&bimodal_sorted, 0.5),
        quant(&bimodal_sorted, 0.99)
    );
    // Set by the placebo arm below when there is one to set it from.
    let mut bimodal_cut = if bimodal_sorted.is_empty() {
        f32::INFINITY
    } else {
        quant(&bimodal_sorted, 0.99)
    };
    let mut cut_is_circular = true;
    match p2.placebo.as_ref() {
        Some(pl) => {
            let mut fake: Vec<f32> = (0..px).filter_map(|i| pl.bimodality_sigma(i)).collect();
            let fake_mean = if fake.is_empty() {
                0.0
            } else {
                fake.iter().map(|v| *v as f64).sum::<f64>() / fake.len() as f64
            };
            fake.sort_by(|a, b| a.partial_cmp(b).unwrap());
            eprintln!(
                "  placebo       : mean {fake_mean:.3} sigma, median {:.3}, p99 {:.3}   \
                 (seeded shuffle, mean step {:.1} frames, NOT a rotation)",
                quant(&fake, 0.5),
                quant(&fake, 0.99),
                if perm.len() > 1 {
                    (0..perm.len() - 1)
                        .map(|k| perm[k].abs_diff(perm[k + 1]) as f64)
                        .sum::<f64>()
                        / (perm.len() - 1) as f64
                } else {
                    0.0
                }
            );
            eprintln!(
                "  ratio         : {:.4}x  -- BELOW 1 means the through-focus curve is genuinely",
                real_mean / fake_mean
            );
            eprintln!(
                "                  focus-ordered at this scale; AT 1 means the stack carries no"
            );
            eprintln!(
                "                  ordering information here and the screen is reading noise."
            );
            eprintln!(
                "                  The placebo reads HIGH by construction (M21: permutation is a"
            );
            eprintln!("                  null for ENRICHMENT, never for a raw rate).");
            eprintln!(
                "                  THIS RATIO IS NOT AN OCCLUSION TEST AND A READING BELOW 1 IS"
            );
            eprintln!("                  NOT EVIDENCE OF NO OCCLUSION. Occlusion enrichment is a");
            eprintln!(
                "                  CONDITIONAL quantity -- the multi-peak rate at depth steps"
            );
            eprintln!(
                "                  against the rate on smooth depth, binned on an INDEPENDENT"
            );
            eprintln!(
                "                  depth-step map. This is a GLOBAL ratio and it is saturated by"
            );
            eprintln!(
                "                  the fact that permutation manufactures multi-peakedness, so it"
            );
            eprintln!(
                "                  cannot see the effect at all. M21 measures 4.38x on coffee-bean"
            );
            eprintln!(
                "                  conditioned properly, against a null of 1.01x, where this"
            );
            eprintln!(
                "                  global ratio reads 0.86x. Both are correct; only one is an"
            );
            eprintln!(
                "                  answer to the occlusion question. The per-pixel statistic"
            );
            eprintln!(
                "                  supports the conditional test; this summary line does not."
            );
            // The cut for the C4 bimodality flag. Taken from the PLACEBO's p99,
            // never from the real distribution's own p99: the latter flags
            // exactly 1% of pixels by construction and reports the definition
            // of the quantile back as if it were a measurement. An earlier draft
            // did that and printed 82417 px -- 1.0000% -- on both stacks.
            //
            // Against the null's p99, the flagged fraction is a real number: a
            // reading BELOW 1% means the real curve has FEWER prominent far
            // peaks than chance, which is what a focus-ordered stack should do.
            bimodal_cut = quant(&fake, 0.99);
            cut_is_circular = false;
        }
        None => eprintln!(
            "  placebo       : NOT MEASURED. Pass --stats-placebo. Without it the number above \
             is uninterpretable."
        ),
    }
    eprintln!();

    // Confidence vector.
    let est = &p2.est[0];
    let vectors: Vec<ConfidenceVector> = (0..px)
        .map(|i| {
            tf.confidence(
                est.n_eff()[i],
                est.green_mean(i) - levels.black,
                noise,
                i,
                bimodal_cut,
            )
        })
        .collect();
    let (mask, b) = do_not_trust_mask(&vectors, opts.confidence_tail);
    let clip_union = (0..px.min(vectors.len()))
        .filter(|&i| mask[i] || clip.always_clipped(i))
        .count();
    let clip_only = (0..px.min(vectors.len()))
        .filter(|&i| !mask[i] && clip.always_clipped(i))
        .count();
    eprintln!(
        "(d) CONFIDENCE VECTOR at gate {:.2} -- four channels, NOT a score",
        est.gate().threshold
    );
    eprintln!(
        "                  Facts 280-282: C1 is ANTI-correlated with C3's target (0.89x lift), so"
    );
    eprintln!(
        "                  no monotone scalar summary is faithful. The honest answer is the UNION."
    );
    eprintln!(
        "  C1 sigma      : worst {:.1}% at >= {:.3} DN -> {} px",
        100.0 * opts.confidence_tail,
        b.sigma_cut,
        b.by_sigma
    );
    eprintln!(
        "  C2 perplexity : worst {:.1}% at >= {:.3} -> {} px",
        100.0 * opts.confidence_tail,
        b.perplexity_cut,
        b.by_perplexity
    );
    eprintln!(
        "  C3 deficit    : worst {:.1}% at >= {:.4} -> {} px",
        100.0 * opts.confidence_tail,
        b.deficit_cut,
        b.by_deficit
    );
    let flag_count = |f: u8| vectors.iter().filter(|v| v.has(f)).count();
    eprintln!(
        "  C4 flags      : {} px  (boundary {}, bimodal {}, peak outside triple {})",
        b.by_flags,
        flag_count(FLAG_BRACKET_BOUNDARY),
        flag_count(FLAG_BIMODAL),
        flag_count(FLAG_SCALE_DISAGREEMENT)
    );
    eprintln!(
        "                  bimodal cut {bimodal_cut:.3} sigma, from the {}. {:.4}% of pixels \
         clear it;",
        if cut_is_circular {
            "REAL distribution's own p99 -- CIRCULAR, it flags 1% by definition"
        } else {
            "PLACEBO's p99"
        },
        100.0 * flag_count(FLAG_BIMODAL) as f64 / px as f64
    );
    eprintln!(
        "                  1% is the no-effect reading, below 1% means FEWER prominent far peaks"
    );
    eprintln!("                  than chance -- which is what a focus-ordered stack should give.");
    eprintln!(
        "  UNION         : {:.3}% of pixels ({} of {})   -- M34 measured 14.278% at a 5% tail",
        100.0 * b.union as f64 / b.total as f64,
        b.union,
        b.total
    );
    let always_n = (0..px.min(vectors.len()))
        .filter(|&i| clip.always_clipped(i))
        .count();
    eprintln!(
        "  C5 clipped    : {always_n} px pinned in EVERY frame carry no focus information at all."
    );
    eprintln!(
        "                  {clip_only} of them are NOT caught by C1-C4, because a pinned pixel"
    );
    eprintln!(
        "                  reads the confidence metric's MAXIMUM rather than its minimum (M26)."
    );
    eprintln!(
        "  UNION + C5    : {:.3}% of pixels ({} of {})   -- the mask a consumer should use",
        100.0 * clip_union as f64 / b.total as f64,
        clip_union,
        b.total
    );
    // The scale-disagreement channel is new here, so report the union without it
    // too. Comparing a four-channel union against M34's three-channel one and
    // calling the difference a finding would be a reporting defect.
    let m34_like: Vec<ConfidenceVector> = vectors
        .iter()
        .map(|v| {
            let mut c = *v;
            c.flags &= !FLAG_SCALE_DISAGREEMENT;
            c
        })
        .collect();
    let (_, b3) = do_not_trust_mask(&m34_like, opts.confidence_tail);
    eprintln!(
        "  UNION w/o C4' : {:.3}% ({} px) with the NEW scale-disagreement flag removed -- this is",
        100.0 * b3.union as f64 / b3.total as f64,
        b3.union
    );
    eprintln!(
        "                  the channel set M34's 14.278% was measured over, and the only one \
         comparable."
    );
    let mean_pp = (0..px)
        .map(|i| tf.posterior_perplexity(i) as f64)
        .sum::<f64>()
        / px as f64;
    eprintln!(
        "  mean C2       : {mean_pp:.4} against mean n_eff {:.4} at this gate -- the soft and hard",
        est.mean_n_eff()
    );
    eprintln!(
        "                  readings of the same acceptance set, on the same calibrated scale."
    );
    Ok(())
}

/// Index of the last top-k slot. Named so the report cannot silently drift from
/// `strehl_core::through_focus::TOP_K`.
const TOP_K_LAST: usize = strehl_core::through_focus::TOP_K - 1;

/// Seed for the placebo frame permutation. Fixed so a placebo reading is
/// reproducible from the command line alone.
const PLACEBO_SEED: u64 = 0x4D31_385E;

#[allow(clippy::too_many_arguments)]
fn write_merged(
    merged: Merged<'_>,
    levels: Levels,
    wb: Option<[f32; 3]>,
    xyz_to_cam: Option<&([[f32; 3]; 3], String)>,
    space: image_out::OutputSpace,
    demosaic: bool,
    exposure: Exposure,
    // `Some` only when the restoration flag is set AND alignment actually ran:
    // with no gather there is no resampling loss, so there is nothing to undo.
    // `None` leaves every arithmetic expression below textually and
    // numerically identical to what it was before this was wired.
    restore: Option<strehl_core::restore::RestorePlan<'_>>,
    // `Some` only under `--cover crop`. The window every frame covered, in
    // plane px, emitted at unity scale instead of being stretched back to the
    // full plane. `None` -- every other run -- takes `CropRect::whole`, whose
    // index map is the identity, so the byte-frozen branch below reads exactly
    // the values it always read, in exactly the order it always read them.
    crop: Option<align_cmd::CropRect>,
    path: &Path,
) -> Result<()> {
    // The transfer curve, and *only* the transfer curve. Bound here so the
    // byte-frozen arithmetic further down stays textually identical to what
    // M85 proved: it reads `srgb` exactly as it always did, and the meaning of
    // that name has not changed -- what changed is that the matrix no longer
    // rides on it.
    let srgb = space.applies_curve();
    // THE ONE PLACE THE CROP IS APPLIED, and it is applied by *addressing*, not
    // by copying: every expression below asks `merged` for quad `i` of the grid
    // it is writing, and `at` turns that into the quad of the merged grid it
    // came from. Everything downstream -- the exposure statistic, the four
    // restored planes, the demosaic interleave, the binned write and the
    // byte-frozen encode -- is therefore cropped by construction rather than by
    // four separate crops that could disagree.
    //
    // The offsets are whole PLANE pixels, so a `--demosaic`/`--srgb` render is
    // cropped on an EVEN full-resolution boundary and keeps the CFA phase the
    // merge produced.
    let full = merged.geometry();
    let rect = crop.unwrap_or(align_cmd::CropRect::whole(full));
    let geom = rect.geometry();
    let at = move |i: usize| -> usize {
        if rect.x == 0 && rect.y == 0 && rect.width == full.width {
            return i;
        }
        (i / rect.width + rect.y) * full.width + (i % rect.width) + rect.x
    };
    let n = geom.pixels();
    let range = levels.range();
    ensure!(range > 0.0, "white level is not above black level");
    let black = levels.black;
    // The only place the halo correction can reach, and the only place the two
    // backends' conventions are reconciled. Both return BLACK-SUBTRACTED,
    // non-negative DN, so every `norm` below is one multiply and neither arm's
    // convention leaks into it. For the estimator that is `(raw - black).max(0)`
    // computed here instead of three lines later -- the same operations in the
    // same order, which is what keeps the measurement branch byte-frozen.
    // Untreated pixels fall straight through to the estimator, so `halo = None`
    // and "treated nothing" produce the identical file.
    let val = |p: CfaPlane, i: usize| merged.value(p, at(i), black);
    let gmean = |i: usize| merged.green_mean(at(i), black);
    let gains = wb.unwrap_or([1.0, 1.0, 1.0]);

    // The colour matrix rides with `--srgb`, and only with `--srgb`. Both are
    // rendering decisions -- "for looking at, NOT for measuring" -- and keeping
    // them on one switch is what leaves the default linear path byte-frozen for
    // the corpus (M85). Without a characterisation there is no matrix and the
    // output stays camera-native, which the report line below says out loud.
    // The colour matrix rides with **either** colorimetric space, and the
    // transfer curve rides only with `--srgb`. Those were one switch until
    // `OutputSpace` broke the weld, and the weld was why there was no way to
    // ask for the one mode measurement actually needs: stated primaries,
    // still linear. Without a characterisation there is no matrix and the
    // output stays camera-native, which the report line below says out loud.
    let matrix = if space.wants_matrix() {
        xyz_to_cam.and_then(|(m, _)| strehl_core::color::camera_to_srgb(*m))
    } else {
        None
    };
    if space.wants_matrix() {
        match (matrix, xyz_to_cam) {
            (Some(_), Some((m, src))) => {
                let neutral = strehl_core::color::neutral_response(*m);
                eprintln!(
                    "colour          : camera RGB -> {} (BT.709 primaries, D65 white)",
                    if space.applies_curve() { "sRGB" } else { "LINEAR sRGB" }
                );
                eprintln!("                  characterisation: {src}");
                eprintln!(
                    "                  XYZ->cam rows: [{:.4} {:.4} {:.4}] [{:.4} {:.4} {:.4}] [{:.4} {:.4} {:.4}]",
                    m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2], m[2][0], m[2][1], m[2][2]
                );
                eprintln!(
                    "                  implied daylight WB R {:.4} B {:.4}, against as-shot R {:.4} B {:.4}",
                    neutral[1] / neutral[0],
                    neutral[1] / neutral[2],
                    gains[0],
                    gains[2]
                );
                eprintln!(
                    "                  Order: black, as-shot WB, {}, matrix, clamp{}.",
                    if demosaic { "demosaic" } else { "2x2 bin" },
                    if space.applies_curve() {
                        ", sRGB curve"
                    } else {
                        " -- NO transfer curve, safe to measure on"
                    }
                );
            }
            _ => {
                eprintln!(
                    "colour          : no usable camera characterisation; emitting CAMERA-NATIVE RGB."
                );
                eprintln!(
                    "                  Expect a colour cast. This is not a render of what the sensor saw."
                );
            }
        }
    }

    // ---- exposure ---------------------------------------------------------
    //
    // The statistic is ALWAYS taken on the binned quad grid, even under
    // --demosaic. The demosaic is an interpolation and must not be able to
    // move the exposure, and MEASURED (docs/research/M100-exposure.md 3) it
    // does not want to: the binned and demosaiced grids of the same stack put
    // the luminance percentile at 0.322559 and 0.322549, the same answer to
    // 1/100 stop. Computing it here is also 4x cheaper and needs no second
    // full-resolution buffer.
    //
    // It reads through `val`/`gmean`, so with the halo correction on it
    // measures the pixels it is about to write, not a different image.
    let choose = || {
        let norm = |v: f32, gain: f32| v * gain / range;
        let mut luma: Vec<f32> = (0..n)
            .map(|i| {
                color::display_luminance(
                    [
                        norm(val(CfaPlane::R, i), gains[0]),
                        norm(gmean(i), gains[1]),
                        norm(val(CfaPlane::B, i), gains[2]),
                    ],
                    matrix.as_ref(),
                )
            })
            .collect();
        color::choose_exposure(&mut luma)
    };
    let applied = match exposure {
        Exposure::None => AppliedExposure::IDENTITY,
        Exposure::Stops(stops) => AppliedExposure {
            stops,
            automatic: false,
        },
        Exposure::Auto => choose().unwrap_or_else(|| {
            eprintln!(
                "exposure        : --auto-exposure found no positive luminance; leaving it alone."
            );
            AppliedExposure::IDENTITY
        }),
    };
    // M100/M109 REGRESSION GUARD, ported from the identical argument already
    // written out in `stack.rs`. THE TONE STAGE SUPERSEDES `--auto-exposure` on
    // the `--srgb` path, so the gain is computed, reported and NOT applied.
    // This is a declared no-op, not a silent one.
    //
    // The two are the SAME RULE written twice: `color::AUTO_EXPOSURE_PERCENTILE`
    // is 99.9 and `image_out::TONE_WHITE_PCT` is 99.9;
    // `color::AUTO_EXPOSURE_TARGET` is 0.90 and `image_out::TONE_WHITE_TARGET`
    // is 0.90. `stack.rs` carries the full derivation. This path -- the one the
    // `stack` subcommand actually runs -- was simply never given the same guard,
    // so the tone stage landed here without it.
    //
    // MEASURED on `stack D:\personal\macro\109MSDCF --srgb`, 22 frames:
    //   with    --auto-exposure : 92.03% of pixels clipped at 65535, median 65535
    //   without --auto-exposure :  0.00% clipped,                    median 61063
    // and the acceptance pin 9b05d0b7, which predates the tone stage, renders
    // the same recipe at 0.00% clipped / median 60918. The pin's auto-exposure
    // and HEAD's tone stage therefore land in the SAME place, and applying both
    // multiplies an already-normalised image by its own chosen gain a second
    // time. Across the corpus that blew 11 of 18 masters to a white median.
    //
    // Without `--srgb` there is no tone placement, so the flag stays
    // load-bearing there; that is the one case this guard must not steal.
    let superseded = (srgb && applied.automatic).then_some(applied);
    let applied = if superseded.is_some() {
        AppliedExposure::IDENTITY
    } else {
        applied
    };
    if let Some(auto) = superseded {
        eprintln!("exposure        : --auto-exposure is SUPERSEDED and applies NOTHING.");
        eprintln!(
            "                  It would have chosen {auto}, but --srgb's tone rendering\n\
             \x20                 already places luminance p{} at {:.2} -- the identical rule.\n\
             \x20                 Applying both double-normalises and blows the highlights\n\
             \x20                 (measured: 92% of pixels clipped). This render is\n\
             \x20                 byte-for-byte a plain --srgb render.",
            color::AUTO_EXPOSURE_PERCENTILE,
            color::AUTO_EXPOSURE_TARGET
        );
        eprintln!(
            "                  To deviate deliberately from that rendering, use --exposure."
        );
    }
    if !applied.is_identity() || applied.automatic {
        eprintln!(
            "exposure        : {applied}, {}",
            if applied.automatic {
                "chosen from the image"
            } else {
                "as asked"
            }
        );
        if applied.automatic {
            eprintln!(
                "                  rule: linear-sRGB luma p{} -> {:.2} on the binned grid (M100).",
                color::AUTO_EXPOSURE_PERCENTILE,
                color::AUTO_EXPOSURE_TARGET
            );
            eprintln!(
                "                  reproduce this exact file with {}",
                applied.reproduce_flag()
            );
        }
        eprintln!(
            "                  ONE multiply in linear light, before the curve. No tone curve, no"
        );
        eprintln!("                  saturation, no roll-off: every unclipped ratio is unchanged.");
    } else if srgb && superseded.is_none() {
        // ADVISORY ONLY. Nothing is applied and no byte moves; this exists so
        // that "--srgb looks grey" is answered by the tool rather than by a
        // bug report. M100 recommends against making --auto-exposure the
        // default precisely because a silent, scene-dependent gain makes two
        // renders incomparable -- so the number is offered, not taken.
        if let Some(would) = choose()
            && would.stops.abs() >= 0.05
        {
            eprintln!(
                "exposure        : none -- this is a FAITHFUL render of the capture, which is \
                 not the same",
            );
            eprintln!(
                "                  thing as a flattering one. --auto-exposure would choose {}.",
                would
            );
            eprintln!(
                "                  Nothing was applied. Pass {} to apply it. (--auto-exposure is\n\
                 \x20                 superseded by the tone rendering on this path and applies\n\
                 \x20                 nothing -- see the M100/M109 guard above.)",
                would.reproduce_flag()
            );
        }
    }

    // M109: the matrix must not be handed a triple in which one channel is
    // pinned at the container maximum while white balance has carried the
    // others past it -- that is what renders blown neutral white magenta.
    // See `docs/research/M109-highlights.md`. `with_saturation` additionally
    // states where usable white sits, which is what the chroma roll-off in
    // `strehl_core::highlight` needs; see `docs/research/BUILD-HIGHLIGHT.md`.
    // `.with_exposure_gain` is what carries the commanded exposure past the
    // tone normalisation. Without it the gain folded into `norm` below is
    // divided straight back out by `--srgb`'s auto-tone, because both tone
    // anchors are linear in the data (measured: a commanded 64x span
    // delivered 1.0000000, bit-identical across 98,898,048 samples).
    // See `Develop::exposure_gain` and docs/research/BUILD-DEFECT.md S14.
    let dev = space
        .develop(matrix.map(|r| r.with_saturation(levels, gains, applied.gain())))
        .with_exposure_gain(applied.gain());

    if demosaic {
        // Full resolution. The merge already estimates all four CFA sites of
        // every quad independently -- `Estimator` carries four accumulators and
        // reuses one focus decision across them -- so this is pure interleaving
        // of data that was already there, not an inference. Nothing about the
        // gate, the fold or the election changes.
        let (mw, mh) = (geom.width * 2, geom.height * 2);
        let mut mosaic = vec![0.0f32; mw * mh];
        // Normalised but deliberately NOT clamped above: the demosaic and the
        // matrix both need the headroom, and the clamp happens once, after the
        // matrix, in `image_out`. The exposure gain rides in the same multiply
        // -- see the binned branch below for why that is exact and not merely
        // convenient.
        let eg = applied.gain();
        let norm = |v: f32, gain: f32| v * gain * eg / range;
        // The four CFA planes, materialised BEFORE interleaving so that the
        // restoration runs on the grid the gather actually resampled: one
        // sample per quad per plane. Restoring after the interleave would hand
        // the filter a mosaic, in which neighbouring samples are different
        // colours, and the correction would be nonsense.
        //
        // With `restore` None each value is the same expression, evaluated in
        // the same order, as before this branch was wired.
        let spec = [
            (CfaPlane::R, gains[0]),
            (CfaPlane::G1, gains[1]),
            (CfaPlane::G2, gains[1]),
            (CfaPlane::B, gains[2]),
        ];
        let mut planes: Vec<Vec<f32>> = Vec::with_capacity(4);
        for (p, gain) in spec {
            let mut v: Vec<f32> = (0..n).map(|i| norm(val(p, i), gain)).collect();
            if let Some(plan) = restore.as_ref() {
                // The plane's own mean, black-subtracted, is where the
                // calibrated model is evaluated -- shot noise is signal
                // dependent, so a single global level would misprice three of
                // the four planes.
                let mean_dn = if n == 0 {
                    0.0
                } else {
                    ((0..n).map(|i| val(p, i) as f64).sum::<f64>() / n as f64) as f32
                };
                let scale = (gain * eg / range) as f64;
                let cfg = plan.config(plan.sigma2(p, mean_dn, scale));
                let rep = strehl_core::restore::restore_plane(&mut v, geom.width, geom.height, &cfg);
                // `max_gain` is the ONE-dimensional response, and this report
                // used to stop there. `restore_plane` convolves x and then y
                // with the same taps, so the picture receives `G(fx) * G(fy)`
                // and on the diagonal that is the square -- a filter reported
                // at 1.43 delivers 2.05, and a `gain_cap` of 1.7 delivers 2.89.
                // Both numbers are printed because the cap is expressed in the
                // 1-D units the caller sets and the pixels are in the other.
                //
                // sigma^2 is reported in DN^2, NOT in the normalised units the
                // filter runs in. Those units carry `scale^2` ~ 2.3e-10, so the
                // working value prints as 0.0 at any sane precision and says
                // nothing. DN^2 is also the unit every other noise number in
                // this project is quoted in, so it is the one that can be
                // compared against the calibration. The ratio sigma^2/S is
                // scale-invariant, so this is a change of display only.
                //
                // It is printed at all because it, not `cap`, decides the
                // strength: the cap is measured never to bind (see the module
                // header), so a log showing only the cap shows only the guard
                // that did not fire.
                eprintln!(
                    "restore {p:?}       : cap {:.3}, max gain {:.4} (2-D {:.4}), at Nyquist \
                     {:.4}, recovered {:.4}, mean {mean_dn:.1} DN, sigma2 {:.1} DN^2",
                    cfg.gain_cap,
                    rep.max_gain,
                    rep.max_gain * rep.max_gain,
                    rep.gain_at_nyquist,
                    rep.recovered_fraction,
                    plan.sigma2(p, mean_dn, 1.0)
                );
                // The cost column. A sharpening number without this beside it
                // is exactly the evidence this project does not accept: the
                // whole risk of a Wiener restoration is overshoot at an edge,
                // and overshoot at a silhouette is the halo the pyramid merge
                // was built to remove. `worst` is converted back to DN so it
                // can be read against the step it sits on.
                eprintln!(
                    "                  overshoot {:.4}% of px outside their own support, \
                     worst {:.1} DN",
                    rep.outside_support * 100.0,
                    if scale > 0.0 {
                        rep.worst_excursion / scale
                    } else {
                        rep.worst_excursion
                    }
                );
            }
            planes.push(v);
        }
        for py in 0..geom.height {
            let (top, bot) = mosaic[py * 2 * mw..].split_at_mut(mw);
            for px in 0..geom.width {
                let i = py * geom.width + px;
                // RGGB, matching `CfaPlane::rggb_at`: R G1 on the even row,
                // G2 B on the odd one.
                top[px * 2] = planes[0][i];
                top[px * 2 + 1] = planes[1][i];
                bot[px * 2] = planes[2][i];
                bot[px * 2 + 1] = planes[3][i];
            }
        }
        image_out::write_demosaiced(path, mw, mh, &mosaic, &dev)?;
        eprintln!();
        eprintln!(
            "wrote           : {} ({mw} x {mh}, 16-bit RGB, {}, Malvar-He-Cutler demosaic)",
            path.display(),
            dev.caveat()
        );
        eprintln!("                  Full sensor resolution: every CFA site estimated, one focus");
        eprintln!(
            "                  decision per quad. Interpolated -- do not measure resolution on it."
        );
        return Ok(());
    }

    if matrix.is_some() || !applied.is_identity() {
        // Binned, with colour and/or exposure. Same 2x2 binning as below; the
        // matrix and the gain are the only differences, and the values are left
        // unclamped until after both.
        //
        // **The exposure rides in the normalisation multiply, and that is exact
        // rather than convenient.** The colour matrix and the demosaic are both
        // LINEAR operators, so `M(g*v) = g*M(v)`: multiplying here and
        // multiplying between the matrix and the clamp are the same transform
        // (`strehl_core::color::tests::the_gain_commutes_with_the_colour_matrix`).
        // What is *not* free is that it must land before the clamp, so a
        // negative exposure can pull a value back down from above 1.0 instead
        // of scaling one already flattened to it. Folding it here is also what
        // lets the byte-frozen branch below stay textually untouched.
        let eg = applied.gain();
        let norm = |v: f32, gain: f32| v * gain * eg / range;
        let mut lin = vec![0.0f32; n * 3];
        let (pixels, _) = lin.as_chunks_mut::<3>();
        for (i, px) in pixels.iter_mut().enumerate() {
            px[0] = norm(val(CfaPlane::R, i), gains[0]);
            px[1] = norm(gmean(i), gains[1]);
            px[2] = norm(val(CfaPlane::B, i), gains[2]);
        }
        // Same reason as the demosaic branch above: the gain in `norm` is
        // cancelled by the tone stage, so it must also be applied on the far
        // side of that normalisation. This is the identity when no exposure
        // was asked for -- `exp2(0)` is exactly 1.0 and `x * 1.0` is `x`
        // bit-for-bit -- so the byte-frozen linear renders cannot move.
        let dev = space
            .develop(matrix.map(|r| r.with_saturation(levels, gains, eg)))
            .with_exposure_gain(eg);
        image_out::write_binned(path, geom.width, geom.height, &lin, &dev)?;
        eprintln!();
        eprintln!(
            "wrote           : {} ({} x {}, 16-bit RGB, {}, binned from one 2x2 quad per pixel)",
            path.display(),
            geom.width,
            geom.height,
            dev.caveat()
        );
        return Ok(());
    }

    // ------------------------------------------------------------------
    // The measurement path. **Byte-frozen.**
    //
    // Exposure cannot reach here: the branch above claims every case where the
    // gain is not the identity, precisely so that this arithmetic stays
    // textually untouched. See docs/research/M100-exposure.md section 4.
    //
    // Every quality number in the corpus was measured on the file this branch
    // writes. The arithmetic below is exactly what shipped before M85 --
    // clamp before the curve, no matrix, no demosaic -- and
    // `docs/research/M85-output-correctness.md` carries the SHA-256 proof that
    // it still emits the identical bytes. Do not refactor it into the helpers
    // above for tidiness; the tidiness is not worth re-measuring the corpus.
    //
    // The one thing that moved is that `(raw - levels.black).max(0.0)` now
    // happens inside `val`/`gmean` rather than inside `encode`. Same operations,
    // same order, same operands; it moved because the band merge folds planes
    // that are already black-subtracted and one develop path serving both
    // backends beats a second copy of this arithmetic that can drift from it.
    // ------------------------------------------------------------------
    let encode = |v: f32, gain: f32| -> u16 {
        let v = (v * gain / range).min(1.0);
        let v = if srgb { srgb_encode(v) } else { v };
        (v * u16::MAX as f32 + 0.5) as u16
    };

    let mut rgb = vec![0u16; n * 3];
    let (pixels, _) = rgb.as_chunks_mut::<3>();
    for (i, px) in pixels.iter_mut().enumerate() {
        px[0] = encode(val(CfaPlane::R, i), gains[0]);
        px[1] = encode(gmean(i), gains[1]);
        px[2] = encode(val(CfaPlane::B, i), gains[2]);
    }
    // Describing the bytes is not the same as changing them. `Develop` here is
    // a *statement* of what this branch did -- camera-native primaries, no
    // matrix, curve only if asked -- and the arithmetic above deliberately does
    // not route through `image_out::develop_pixel`. The file gains an
    // ImageDescription tag and its pixels are untouched, which is why the
    // byte-freeze rows move for a reason that has to be written down.
    let dev = image_out::Develop::measurement(srgb);
    if !space.is_measurement() {
        // A colorimetric space was asked for and we are in the branch that
        // cannot deliver one: the body has no characterisation, so there is no
        // matrix to apply and `--linear-srgb` has just become a no-op. The
        // caveat below states the space correctly, but a caveat is easy to
        // scroll past, and the file that results is byte-identical to a default
        // render while carrying a name that says otherwise. Say it loudly --
        // this is the one path on which the flag still silently does nothing,
        // and it is the reason the interim guard in `main.rs` existed.
        eprintln!();
        eprintln!(
            "WARNING         : no colour characterisation for this body, so the requested"
        );
        eprintln!(
            "                  colorimetric space could not be reached. Emitting camera-native"
        );
        eprintln!(
            "                  primaries instead of inventing a matrix. Do NOT treat this file"
        );
        eprintln!("                  as being in a stated colour space.");
    }
    image_out::write_rgb16_described(path, geom.width as u32, geom.height as u32, &rgb, &dev)?;
    eprintln!();
    eprintln!(
        "wrote           : {} ({} x {}, 16-bit RGB, {}, binned from one 2x2 quad per pixel)",
        path.display(),
        geom.width,
        geom.height,
        // One source of truth for the caveat, so the terminal line and the
        // ImageDescription tag written above can never disagree.
        dev.caveat()
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Ladder **shapes** for exercising the solver, generated rather than
    /// measured, and that is deliberate.
    ///
    /// Every property the solver has — a rung round-trips to its own gate, a
    /// solved gate inverts back to its target, a target outside the ladder is
    /// refused — holds for **any** monotone ladder. Asserting them against
    /// generated ladders therefore tests strictly *more* than asserting them
    /// against five frozen measurements, and cannot go stale when the pipeline
    /// is recalibrated. The generated family spans `n_eff(2.0)` from 1.07 to
    /// 23.6, which brackets the real corpus's measured 1.177 to 14.386.
    fn generated_ladders() -> Vec<(String, [(f64, f64); 4])> {
        let mut out = Vec::new();
        for p in [0.5_f64, 1.0, 1.5, 2.0, 2.5] {
            for a in [0.1_f64, 0.5, 1.5, 4.0] {
                let rung = |g: f64| (g, 1.0 + a * g.powf(p));
                out.push((
                    format!("a={a} p={p}"),
                    [rung(0.5), rung(1.0), rung(2.0), rung(4.0)],
                ));
            }
        }
        out
    }

    /// The one real ladder still defensible as current, kept so the solver sees
    /// a measured shape and not only analytic ones.
    ///
    /// `109MSDCF` is ISO 160, which puts it outside **both** of the day's
    /// calibration changes: `2a4f5c5` moved only ISO 50, and `f95f6f4` moved
    /// only ISO >= 400. M52 re-measured its gate-2.0 rung against the current
    /// pipeline and got 2.891 against fact 324's 2.891 — the only one of the
    /// five that reproduced exactly. The other four rungs are M38's and are not
    /// independently re-confirmed, so nothing below asserts their values.
    const LADDER_109MSDCF: [(f64, f64); 4] =
        [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891), (4.0, 4.987)];

    /// M52's solved gates for `n_eff = 3`, all seven stacks, measured against
    /// the current pipeline and cross-checked by an independent Python merge
    /// agreeing with the shipped binary to <= 0.09%.
    /// `docs/research/M52-gate-cluster-verified.md` section 4.3, commit `f094c37`.
    ///
    /// **This is a dated snapshot and it will be wrong again.** It was wrong
    /// within one day twice already: `2a4f5c5` (09:41) moved the ISO-50 stacks
    /// and `f95f6f4` (11:17) moved every ISO >= 400 stack. What is asserted
    /// against it below is deliberately **one-sided**, so that the next
    /// calibration change makes these assertions *more* true rather than
    /// quietly false. See `no_single_gate_calibrates_across_the_corpus`.
    const SOLVED_GATES_M52: [(&str, f64); 7] = [
        ("coffee-bean", 0.7618),
        ("112MSDCF", 1.1323),
        ("113MSDCF", 1.3231),
        ("109MSDCF", 2.0964),
        ("119MSDCF", 2.1485),
        ("coffee-bubbles", 3.2144),
        ("foam", 21.9934),
    ];

    fn gate_of(s: Solve) -> f64 {
        match s {
            Solve::Gate(g) => g,
            other => panic!("expected a solved gate, got {other:?}"),
        }
    }

    #[test]
    fn log_log_interpolation_is_exact_on_a_power_law() {
        // n = g^2. The gate for n = 2 is sqrt(2), exactly, and log-log
        // recovers it because a power law is a straight line in log-log.
        // This is the whole reason the solve is not linear: linear
        // interpolation on the same rungs returns 1.3333, which is n = 1.78 —
        // 11% short of the target, biased the same way on every stack.
        let g = gate_of(solve_gate_for_n_eff(
            &[(1.0, 1.0), (2.0, 4.0), (4.0, 16.0)],
            2.0,
        ));
        assert!(
            (g - std::f64::consts::SQRT_2).abs() < 1e-12,
            "log-log gave {g}"
        );

        let linear = 1.0 + (2.0 - 1.0) / (4.0 - 1.0) * (2.0 - 1.0);
        assert!(
            (linear * linear - 2.0f64).abs() > 0.2,
            "linear interpolation must be visibly wrong here, or this test proves nothing"
        );
    }

    #[test]
    fn solving_at_a_rungs_own_value_returns_that_rungs_gate() {
        for (name, l) in generated_ladders() {
            for (gate, n) in l {
                let g = gate_of(solve_gate_for_n_eff(&l, n));
                assert!(
                    (g - gate).abs() < 1e-9,
                    "{name}: rung {gate} round-tripped to {g}"
                );
            }
        }
        for (gate, n) in LADDER_109MSDCF {
            let g = gate_of(solve_gate_for_n_eff(&LADDER_109MSDCF, n));
            assert!(
                (g - gate).abs() < 1e-9,
                "109MSDCF: rung {gate} round-tripped to {g}"
            );
        }
    }

    #[test]
    fn a_solved_gate_reproduces_its_target_when_fed_back() {
        // Interpolation is only honest if it inverts the ladder it came from.
        // Rebuild n_eff at the solved gate by interpolating the ladder the
        // other way, and require the target back. True of any monotone ladder,
        // so it is asserted over the generated family and not over a snapshot.
        let invert = |l: &[(f64, f64); 4], g: f64| {
            let w = l
                .windows(2)
                .find(|w| g >= w[0].0 && g <= w[1].0)
                .expect("gate in ladder");
            let f = (g.ln() - w[0].0.ln()) / (w[1].0.ln() - w[0].0.ln());
            (w[0].1.ln() + f * (w[1].1.ln() - w[0].1.ln())).exp()
        };
        let mut exercised = 0;
        for (name, l) in generated_ladders() {
            // Only ladders that actually bracket the target can be solved; the
            // rest are the refusal path and are covered separately.
            let (lo, hi) = (l[0].1, l[3].1);
            for target in [1.5, 2.0, 3.0, 5.0, 11.0] {
                if target <= lo || target >= hi {
                    continue;
                }
                let g = gate_of(solve_gate_for_n_eff(&l, target));
                let n = invert(&l, g);
                assert!(
                    (n - target).abs() < 1e-9,
                    "{name}: gate {g} inverted to n_eff {n}, wanted {target}"
                );
                exercised += 1;
            }
        }
        // Rule 36: a loop that skipped every case would pass silently.
        assert!(
            exercised > 40,
            "only {exercised} solves were actually exercised; this test would \
             pass vacuously if the generated family stopped bracketing the targets"
        );

        let g = gate_of(solve_gate_for_n_eff(&LADDER_109MSDCF, 3.0));
        let n = invert(&LADDER_109MSDCF, g);
        assert!(
            (n - 3.0).abs() < 1e-9,
            "109MSDCF: gate {g} inverted to n_eff {n}"
        );
    }

    /// **The claim, asserted one-sidedly — and that is the entire design.**
    ///
    /// This test replaces `the_solved_gate_spans_the_range_fact_324_claims`,
    /// which was green while two of its three assertions were false of the
    /// pipeline. It solved a frozen `LADDERS` fixture and compared the result
    /// against bands derived from *that same frozen measurement*, so subject
    /// and object were two copies of one stale snapshot. It could not fail when
    /// the pipeline moved, which is the only thing it existed to detect.
    ///
    /// The rule that generalises out of it: **a claim of the form "X is large"
    /// must be asserted as a one-sided bound, and the bound must be set from
    /// the threshold at which the claim stops meaning anything — never from the
    /// current measurement.** A two-sided band does not encode a claim, it
    /// encodes a measurement, and a measurement expires.
    ///
    /// The old test is the proof of its own rule. Its one-sided `hi / lo > 2.4`
    /// was *correctly calibrated all along*: the spread was 2.7215x before the
    /// ISO-50 gain fix and is 28.8703x after, and that assertion is true of
    /// both. Its two-sided companions — `lo` in `1.0..1.2`, `hi` in `2.7..3.1`
    /// — were false the moment the pipeline moved (`lo` is now 0.7618 and `hi`
    /// 21.9934) and had no way to say so. **The surviving assertion and the
    /// broken ones were in the same function; the difference was one-sidedness.**
    ///
    /// So the floors below are the ones that hold against **both** the pre-fix
    /// five-stack measurement and M52's post-fix seven-stack measurement. That
    /// is the only check available that distinguishes a floor encoding the
    /// claim from a floor encoding today's data, and it is how these two were
    /// chosen: 5.0 and 2.0 were tried first and rejected because they passed
    /// only the newer snapshot.
    ///
    /// A recalibration that ever made the corpus agree would fail this test.
    /// That is correct: it would be the discovery that the gate had become a
    /// calibration after all, and it should stop the build.
    #[test]
    fn no_single_gate_calibrates_across_the_corpus() {
        let gates: Vec<f64> = SOLVED_GATES_M52.iter().map(|(_, g)| *g).collect();
        let lo = gates.iter().copied().fold(f64::INFINITY, f64::min);
        let hi = gates.iter().copied().fold(f64::NEG_INFINITY, f64::max);

        // 2.7215x pre-fix, 28.8703x post-fix. A gate whose required value moves
        // 2.4x across subjects is already not a calibration.
        assert!(
            hi / lo > 2.4,
            "solved gates spanned only {:.4}x ({lo:.4} to {hi:.4}). The claim is \
             that no fixed gate is a calibration; a spread this small would mean \
             it had become one. That is a finding to investigate, not a bound to \
             relax",
            hi / lo
        );

        // The claim is about the corpus, not about its two extremes: a single
        // outlier stack would produce a wide spread while the gate still
        // transferred among the rest. 1.8580x pre-fix, 2.8388x post-fix.
        let mut sorted = gates.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).expect("no NaN"));
        let q1 = sorted[1];
        let q3 = sorted[sorted.len() - 2];
        assert!(
            q3 / q1 > 1.5,
            "discarding the extremes, the gates spanned only {:.4}x ({q1:.4} to \
             {q3:.4}); the spread would then be one outlier rather than a \
             property of the corpus",
            q3 / q1
        );

        // A cross-implementation check, and the one assertion here with a
        // subject distinct from its object. M52 solved 109MSDCF's gate with an
        // independent Python merge and got 2.0964; this crate's own solver, on
        // its own copy of that ladder, must agree. 109MSDCF is the control
        // stack precisely because ISO 160 is untouched by both of the day's
        // calibration commits, and indeed its solved gate is 2.0963 pre-fix
        // against 2.0964 post-fix while the ISO-50 stacks moved by 26% and 94%.
        let ours = gate_of(solve_gate_for_n_eff(&LADDER_109MSDCF, 3.0));
        let theirs = SOLVED_GATES_M52
            .iter()
            .find(|(n, _)| *n == "109MSDCF")
            .expect("109MSDCF is in the snapshot")
            .1;
        assert!(
            (ours - theirs).abs() < 1e-3,
            "this crate solved 109MSDCF to {ours:.4} where M52's independent \
             implementation got {theirs:.4}"
        );
    }

    /// `foam` cannot reach `n_eff = 3` anywhere on the shipped 0.5-4.0 ladder,
    /// so the solver must refuse rather than extrapolate a gate from a ladder
    /// that never got there.
    ///
    /// This one is behavioural rather than a snapshot: it asserts a *code path*
    /// against real measured rungs, and `foam` would have to more than double
    /// its `n_eff` before the assertion changed meaning. Both rungs are M52's,
    /// section 4.3, and M52 quotes the shipped solver's own reply verbatim —
    /// *"target n_eff 3.000 is above the ladder: gate 4.0000 reaches only
    /// 1.361"* — so this is a cross-check against an independent run, not
    /// against itself.
    #[test]
    fn a_stack_the_shipped_ladder_cannot_reach_is_refused_not_extrapolated() {
        let foam = [(2.0, 1.177), (4.0, 1.361)];
        match solve_gate_for_n_eff(&foam, 3.0) {
            Solve::AboveLadder {
                highest_gate,
                highest,
            } => {
                assert!((highest_gate - 4.0).abs() < 1e-12, "got {highest_gate}");
                assert!((highest - 1.361).abs() < 1e-12, "got {highest}");
            }
            other => panic!(
                "foam reaches only n_eff 1.361 at the top of the shipped ladder, so \
                 solving it for 3.0 must refuse; got {other:?}. Extrapolating here \
                 would invent a gate no measurement supports"
            ),
        }
    }

    #[test]
    fn a_target_outside_the_ladder_is_refused_rather_than_extrapolated() {
        let l = [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891)];
        assert!(matches!(
            solve_gate_for_n_eff(&l, 1.1),
            Solve::BelowLadder { .. }
        ));
        assert!(matches!(
            solve_gate_for_n_eff(&l, 9.0),
            Solve::AboveLadder { .. }
        ));
        // And the boundary rungs themselves still solve.
        assert!((gate_of(solve_gate_for_n_eff(&l, 1.414)) - 0.5).abs() < 1e-9);
        assert!((gate_of(solve_gate_for_n_eff(&l, 2.891)) - 2.0).abs() < 1e-9);
    }

    #[test]
    fn a_non_monotone_ladder_is_a_bug_and_is_reported_as_one() {
        // Admission is a threshold on a field fixed before the gate applies, so
        // a larger gate admits a superset. n_eff falling is impossible, and
        // interpolating across it would launder a bug into a number.
        let bad = [(0.5, 1.414), (1.0, 2.500), (2.0, 2.100)];
        assert!(matches!(
            solve_gate_for_n_eff(&bad, 2.2),
            Solve::Unusable(_)
        ));
    }

    #[test]
    fn degenerate_ladders_and_targets_are_refused() {
        assert!(matches!(
            solve_gate_for_n_eff(&[(1.0, 2.0)], 1.5),
            Solve::Unusable(_)
        ));
        assert!(matches!(solve_gate_for_n_eff(&[], 1.5), Solve::Unusable(_)));
        // n_eff cannot go below 1: the winner is admitted unconditionally.
        let l = [(0.5, 1.414), (2.0, 2.891)];
        assert!(matches!(solve_gate_for_n_eff(&l, 1.0), Solve::Unusable(_)));
        assert!(matches!(
            solve_gate_for_n_eff(&l, f64::NAN),
            Solve::Unusable(_)
        ));
        // Gate 0 is a valid measurement but not a valid log-log rung; the
        // caller filters it, and the solve refuses it if the filter is removed.
        assert!(matches!(
            solve_gate_for_n_eff(&[(0.0, 1.0), (2.0, 2.9)], 2.0),
            Solve::Unusable(_)
        ));
    }

    #[test]
    fn an_unsorted_ladder_solves_the_same_as_a_sorted_one() {
        let sorted = [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891), (4.0, 4.987)];
        let shuffled = [(2.0, 2.891), (0.5, 1.414), (4.0, 4.987), (1.0, 1.884)];
        let a = gate_of(solve_gate_for_n_eff(&sorted, 3.0));
        let b = gate_of(solve_gate_for_n_eff(&shuffled, 3.0));
        assert!((a - b).abs() < 1e-12, "{a} != {b}");
    }

    fn gaussian_noise(len: usize, sd: f32, mut state: u64) -> Vec<f32> {
        let mut uniform = || {
            state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = state;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64
        };
        (0..len)
            .map(|_| {
                let (u1, u2) = (uniform().max(1e-12), uniform());
                (f64::from(sd) * (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos())
                    as f32
            })
            .collect()
    }

    fn checker_signal_at(w: usize, h: usize, amplitude: f32) -> Vec<f32> {
        (0..w * h)
            .map(|i| {
                let (x, y) = (i % w, i / w);
                if ((x / 3) + (y / 3)) % 2 == 0 {
                    amplitude
                } else {
                    -amplitude
                }
            })
            .collect()
    }

    fn checker_signal(w: usize, h: usize) -> Vec<f32> {
        checker_signal_at(w, h, 200.0)
    }

    fn box_blur_3x3(v: &[f32], w: usize, h: usize) -> Vec<f32> {
        let mut out = vec![0.0; v.len()];
        for y in 0..h {
            for x in 0..w {
                let mut sum = 0.0;
                for dy in [h - 1, 0, 1] {
                    for dx in [w - 1, 0, 1] {
                        sum += v[((y + dy) % h) * w + (x + dx) % w];
                    }
                }
                out[y * w + x] = sum / 9.0;
            }
        }
        out
    }

    fn synthetic_controlled(
        signal: &[f32],
        w: usize,
        h: usize,
        model_sd: f32,
        inflation: f32,
        seed: u64,
    ) -> ControlledDetail {
        let actual_sd = model_sd * inflation;
        let flat = gaussian_noise(w * h, actual_sd, seed);
        let detail_noise = gaussian_noise(w * h, actual_sd, seed ^ 0xD1B5_4A32_D192_ED03);
        let detail: Vec<f32> = signal
            .iter()
            .zip(detail_noise)
            .map(|(s, n)| *s + n)
            .collect();
        let sigma = vec![model_sd; w * h];
        cross_fitted_detail(
            GradientRoi::new(&detail, &sigma, w, h),
            GradientRoi::new(&flat, &sigma, w, h),
        )
        .expect("synthetic ROIs are valid")
    }

    fn harmonic(n: usize) -> f64 {
        (1..=n).map(|k| 1.0 / k as f64).sum()
    }

    fn measured_retention(retention: DetailRetention, context: &str) -> f64 {
        match retention {
            DetailRetention::Measured(value) => value,
            DetailRetention::NotMeasurable => {
                panic!("{context}: selector target unexpectedly NOT-MEASURABLE")
            }
        }
    }

    #[test]
    fn gradient_noise_moments_match_a_dense_covariance_calculation() {
        let (w, h, x0, x1) = (6usize, 5usize, 1usize, 5usize);
        let sigma: Vec<f32> = (0..w * h).map(|i| 0.75 + (i % 7) as f32 * 0.2).collect();
        let power = gradient_power_columns(&vec![0.0; w * h], &sigma, w, h, x0, x1);
        let mut edges = Vec::new();
        for y in 0..h - 1 {
            for x in x0..x1 - 1 {
                let i = y * w + x;
                edges.push([(i, -1.0f64), (i + 1, 1.0)]);
                edges.push([(i, -1.0f64), (i + w, 1.0)]);
            }
        }
        let covariance = |a: &[(usize, f64); 2], b: &[(usize, f64); 2]| {
            let mut value = 0.0;
            for (ia, ca) in a {
                for (ib, cb) in b {
                    if ia == ib {
                        value += ca * cb * f64::from(sigma[*ia]).powi(2);
                    }
                }
            }
            value
        };
        let expected_noise = edges.iter().map(|edge| covariance(edge, edge)).sum::<f64>();
        let expected_covariance_square = edges
            .iter()
            .flat_map(|a| edges.iter().map(move |b| covariance(a, b).powi(2)))
            .sum::<f64>();
        assert!((power.noise_sum - expected_noise).abs() < 1e-10);
        assert!(
            (power.noise_covariance_square_sum - expected_covariance_square).abs() < 1e-9,
            "{} != {}",
            power.noise_covariance_square_sum,
            expected_covariance_square
        );
    }

    #[test]
    fn selection_noise_null_is_not_a_retention_target_across_frame_counts() {
        let (w, h, sd) = (512usize, 512usize, 20.0f32);
        let no_signal = vec![0.0; w * h];
        for (j, n) in [22usize, 130, 299].into_iter().enumerate() {
            let max_scale = harmonic(n).sqrt() as f32;
            let averaged_scale = (1.0 + 0.35 * (harmonic(n) - 1.0)).sqrt() as f32;
            let selector = synthetic_controlled(&no_signal, w, h, sd, max_scale, 0x1000 + j as u64);
            let candidate =
                synthetic_controlled(&no_signal, w, h, sd, averaged_scale, 0x2000 + j as u64);
            let retention = equal_noise_retention(candidate, selector);
            eprintln!(
                "M80 N={n} noise: selector_structure={:.6} candidate_structure={:.6} \
                 selector_q={:+.6} selector_se={:.6} selector_z={:+.6} \
                 retention={retention:?} fitted_k={:.6}/{:.6}",
                selector.structure,
                candidate.structure,
                selector.signal_power,
                selector.signal_standard_error,
                selector.signal_power / selector.signal_standard_error,
                candidate.inflation_left,
                candidate.inflation_right
            );
            assert!(
                matches!(retention, DetailRetention::NotMeasurable),
                "noise null N={n}: selector target must be NOT-MEASURABLE, got \
                 q={:+.6}, se={:.6}, z={:+.6}, retention={retention:?}",
                selector.signal_power,
                selector.signal_standard_error,
                selector.signal_power / selector.signal_standard_error
            );
            assert!(
                (0.90..=1.10).contains(&candidate.structure),
                "noise null N={n}: STRUCTURE must read 1, got {:.6}; fitted k={:.4}/{:.4}, \
                 planted inflation={averaged_scale:.4}",
                candidate.structure,
                candidate.inflation_left,
                candidate.inflation_right
            );
        }
    }

    #[test]
    fn selector_detectability_false_answers_match_the_registered_noise_model() {
        let (w, h, sd) = (64usize, 64usize, 20.0f32);
        let no_signal = vec![0.0; w * h];
        for (j, n) in [22usize, 130, 299].into_iter().enumerate() {
            let inflation = harmonic(n).sqrt() as f32;
            let false_answers = (0..1_000usize)
                .filter(|trial| {
                    let seed = 0xD37E_C700_0000_0000u64 ^ ((j as u64) << 32) ^ (*trial as u64);
                    detail_target_is_measurable(synthetic_controlled(
                        &no_signal, w, h, sd, inflation, seed,
                    ))
                })
                .count();
            eprintln!(
                "M80 detectability null N={n}: false_answers={false_answers}/1000 \
                 nominal_alpha={DETAIL_FALSE_ANSWER_RATE:.3} registered_max=18"
            );
            assert!(
                false_answers <= 18,
                "detectability null N={n}: {false_answers}/1000 false measurable targets \
                 exceeds the registered binomial limit 18"
            );
        }
    }

    #[test]
    fn selector_detectability_has_a_noise_derived_contrast_transition() {
        const AMPLITUDES: [f32; 11] =
            [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 200.0];
        let (w, h, sd) = (512usize, 512usize, 20.0f32);
        let unit_signal = checker_signal_at(w, h, 1.0);
        let zero_sigma = vec![0.0; w * h];
        let unit_left = gradient_power_columns(&unit_signal, &zero_sigma, w, h, 0, w / 2);
        let unit_right = gradient_power_columns(&unit_signal, &zero_sigma, w, h, w / 2, w);
        let unit_gradient_power = (unit_left.raw_sum + unit_right.raw_sum)
            / (unit_left.samples + unit_right.samples) as f64;

        for (j, n) in [22usize, 130, 299].into_iter().enumerate() {
            let inflation = harmonic(n).sqrt() as f32;
            let seed = 0xC017_A570_0000_0000u64 ^ j as u64;
            let mut states = Vec::new();
            let mut predicted_transition = None;
            for amplitude in AMPLITUDES {
                let signal = checker_signal_at(w, h, amplitude);
                let selector = synthetic_controlled(&signal, w, h, sd, inflation, seed);
                let measurable = detail_target_is_measurable(selector);
                let predicted = (DETAIL_DETECTION_Z * selector.signal_standard_error
                    / unit_gradient_power)
                    .sqrt();
                predicted_transition.get_or_insert(predicted);
                states.push((amplitude, measurable));
                eprintln!(
                    "M80 contrast N={n}: amplitude={amplitude:7.1} q={:+10.4} \
                     se={:8.4} z={:+8.3} target={}",
                    selector.signal_power,
                    selector.signal_standard_error,
                    selector.signal_power / selector.signal_standard_error,
                    if measurable {
                        "MEASURABLE"
                    } else {
                        "NOT-MEASURABLE"
                    }
                );
            }
            assert!(
                !states[0].1,
                "contrast N={n}: zero amplitude was measurable"
            );
            assert!(
                states.last().is_some_and(|(_, measurable)| *measurable),
                "contrast N={n}: amplitude 200 was not measurable"
            );
            let first = states
                .iter()
                .position(|(_, measurable)| *measurable)
                .expect("amplitude 200 must be measurable");
            assert!(
                states[first..].iter().all(|(_, measurable)| *measurable),
                "contrast N={n}: detectability returned to N/A after first answer: {states:?}"
            );
            let observed = f64::from(states[first].0);
            let predicted = predicted_transition.expect("the contrast ladder is non-empty");
            let ratio = observed / predicted;
            eprintln!(
                "M80 contrast transition N={n}: predicted={predicted:.6} DN \
                 first_measurable={observed:.6} DN ratio={ratio:.6}"
            );
            assert!(
                (0.5..=2.0).contains(&ratio),
                "contrast N={n}: first measurable {observed:.6} DN is not within one \
                 factor-two rung of predicted {predicted:.6} DN (ratio {ratio:.6})"
            );
        }
    }

    #[test]
    fn cross_fitted_metric_keeps_detail_and_detects_blur_across_frame_counts() {
        let (w, h, sd) = (512usize, 512usize, 20.0f32);
        let signal = checker_signal(w, h);
        let blurred = box_blur_3x3(&signal, w, h);
        let zero = vec![0.0; w * h];
        let clean_metric = detail_metrics(&signal, &zero, w, h);
        let blur_metric = detail_metrics(&blurred, &zero, w, h);
        let planted_retention = blur_metric.raw_rms / clean_metric.raw_rms;
        eprintln!("M80 positive plant: clean-to-blur gradient retention={planted_retention:.6}");
        assert!(
            planted_retention <= 0.75,
            "positive control cannot express failure: 3x3 blur retained \
             {planted_retention:.6} of gradient amplitude"
        );

        let mut clean_retentions = Vec::new();
        for (j, n) in [22usize, 130, 299].into_iter().enumerate() {
            let max_scale = harmonic(n).sqrt() as f32;
            let averaged_scale = (1.0 + 0.35 * (harmonic(n) - 1.0)).sqrt() as f32;
            let selector = synthetic_controlled(&signal, w, h, sd, max_scale, 0x3000 + j as u64);
            let clean = synthetic_controlled(&signal, w, h, sd, averaged_scale, 0x4000 + j as u64);
            let blur = synthetic_controlled(&blurred, w, h, sd, averaged_scale, 0x5000 + j as u64);
            let clean_retention =
                measured_retention(equal_noise_retention(clean, selector), "clean detail");
            let blur_retention =
                measured_retention(equal_noise_retention(blur, selector), "blurred detail");
            eprintln!(
                "M80 N={n} detail: structure={:.6} clean_retention={clean_retention:.6} \
                 blur_retention={blur_retention:.6}",
                clean.structure
            );
            assert!(
                clean.structure >= 3.0,
                "detail control N={n}: STRUCTURE was {:.6}",
                clean.structure
            );
            assert!(
                (0.95..=1.05).contains(&clean_retention),
                "detail control N={n}: unchanged signal retained {clean_retention:.6}"
            );
            assert!(
                blur_retention <= 0.80,
                "detail control N={n}: planted blur retained {blur_retention:.6}"
            );
            clean_retentions.push(clean_retention);
        }
        let lo = clean_retentions
            .iter()
            .copied()
            .fold(f64::INFINITY, f64::min);
        let hi = clean_retentions
            .iter()
            .copied()
            .fold(f64::NEG_INFINITY, f64::max);
        assert!(
            hi - lo <= 0.05,
            "unchanged detail moved {:.6} across N: {clean_retentions:?}",
            hi - lo
        );
    }

    #[test]
    fn the_isotropic_column_is_the_analytic_value_on_a_linear_ramp() {
        // A ramp of slope s in x and t in y has |grad| = sqrt(s^2 + t^2)
        // everywhere, so this pins both the differences and the normalisation.
        let (w, h) = (16usize, 12usize);
        let (s, t) = (3.0f32, 4.0f32);
        let v: Vec<f32> = (0..w * h)
            .map(|i| s * (i % w) as f32 + t * (i / w) as f32)
            .collect();
        let m = detail_metrics(&v, &vec![0.0; w * h], w, h);
        assert!(
            (m.iso_mean - 5.0).abs() < 1e-6,
            "ramp gradient should be exactly 5, got {}",
            m.iso_mean
        );
        assert!(
            (m.m2_pooled_abs - 3.5).abs() < 1e-6,
            "pooled should be 0.5*(3+4), got {}",
            m.m2_pooled_abs
        );
    }

    #[test]
    fn the_corrected_column_falls_under_blur_which_is_the_property_it_is_used_for() {
        // The model-only component still has to detect the collapse fact 24
        // measured. The shipping invariant wraps this power in a cross-fitted
        // selection correction; noise is zero here so both forms reduce to the
        // same optical fall.
        let (w, h) = (64usize, 64usize);
        let sharp: Vec<f32> = (0..w * h)
            .map(|i| {
                if ((i % w) / 4 + (i / w) / 4) % 2 == 0 {
                    1000.0
                } else {
                    0.0
                }
            })
            .collect();
        let mut blurred = vec![0.0f32; w * h];
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let mut acc = 0.0;
                for dy in 0..3 {
                    for dx in 0..3 {
                        acc += sharp[(y + dy - 1) * w + (x + dx - 1)];
                    }
                }
                blurred[y * w + x] = acc / 9.0;
            }
        }
        let zero = vec![0.0f32; w * h];
        let a = detail_metrics(&sharp, &zero, w, h);
        let b = detail_metrics(&blurred, &zero, w, h);
        assert!(a.corrected_rms > 0.0 && b.corrected_rms > 0.0);
        assert!(
            b.corrected_rms < 0.75 * a.corrected_rms,
            "blur must cut the corrected metric substantially: sharp {}, blurred {}",
            a.corrected_rms,
            b.corrected_rms
        );
    }

    #[test]
    fn the_m2_convention_column_reproduces_the_independently_identified_definition() {
        // M38 §1 identified fact 24's convention as mean(0.5*(|dx|+|dy|)) by
        // measurement, against an independent numpy implementation. This pins
        // the Rust column to that definition on a field where it is hand
        // computable: a pure x-ramp of slope 3 has |dx| = 3, |dy| = 0, so the
        // pooled value is 1.5 while the isotropic value is 3.
        let (w, h) = (8usize, 8usize);
        let v: Vec<f32> = (0..w * h).map(|i| 3.0 * (i % w) as f32).collect();
        let s = vec![0.0f32; w * h];
        let m = detail_metrics(&v, &s, w, h);
        assert!((m.m2_pooled_abs - 1.5).abs() < 1e-9, "{}", m.m2_pooled_abs);
        assert!((m.iso_mean - 3.0).abs() < 1e-9, "{}", m.iso_mean);
        // With zero noise the correction must be inert, not merely small.
        assert_eq!(m.noise_rms, 0.0);
        assert!((m.corrected_rms - m.raw_rms).abs() < 1e-9);
    }

    #[test]
    fn the_noise_correction_removes_pure_noise_down_to_sampling_error() {
        // This pins ordinary, unselected noise subtraction only. M77 showed
        // that it says nothing about selected noise; the cross-fitted tests
        // above cover that separate term.
        let (w, h) = (256usize, 256usize);
        let sd = 20.0f32;
        let mut rng = 0x2545_F491_4F6C_DD1Du64;
        let mut next = || {
            rng = rng.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = rng;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64
        };
        let v: Vec<f32> = (0..w * h)
            .map(|_| {
                let (u1, u2) = (next().max(1e-12), next());
                (sd as f64 * (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
            })
            .collect();
        let s = vec![sd; w * h];
        let m = detail_metrics(&v, &s, w, h);
        // Raw rms of pure noise is ~2*sd; the model predicts exactly that.
        assert!(
            (m.raw_rms / m.noise_rms - 1.0).abs() < 0.02,
            "model must predict pure noise: raw {} vs model {}",
            m.raw_rms,
            m.noise_rms
        );
        assert!(
            m.corrected_rms < 0.2 * m.raw_rms,
            "corrected should collapse on pure noise: {} vs raw {}",
            m.corrected_rms,
            m.raw_rms
        );
    }

    #[test]
    fn the_correction_leaves_signal_alone_while_removing_added_noise() {
        // The same unselected signal measured clean and with noise added must
        // give the same model-corrected value. Selection is deliberately absent
        // here and covered by the M80 controls above.
        let (w, h) = (256usize, 256usize);
        let signal: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                400.0 * (x * 0.11).sin() * (y * 0.07).cos()
            })
            .collect();
        let sd = 30.0f32;
        let mut rng = 0x1234_5678_9ABC_DEF0u64;
        let mut next = || {
            rng = rng.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = rng;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64
        };
        let noisy: Vec<f32> = signal
            .iter()
            .map(|v| {
                let (u1, u2) = (next().max(1e-12), next());
                v + (sd as f64 * (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos())
                    as f32
            })
            .collect();
        let clean = detail_metrics(&signal, &vec![0.0; w * h], w, h);
        let dirty = detail_metrics(&noisy, &vec![sd; w * h], w, h);
        assert!(
            dirty.raw_rms > 1.05 * clean.raw_rms,
            "noise must raise the uncorrected metric, else the test proves nothing: {} vs {}",
            dirty.raw_rms,
            clean.raw_rms
        );
        let rel = (dirty.corrected_rms / clean.corrected_rms - 1.0).abs();
        assert!(
            rel < 0.03,
            "corrected must be blind to added noise: clean {} vs noisy {} ({:.1}%)",
            clean.corrected_rms,
            dirty.corrected_rms,
            100.0 * rel
        );
    }

    #[test]
    fn degenerate_rois_do_not_panic() {
        assert_eq!(detail_metrics(&[1.0], &[1.0], 1, 1).corrected_rms, 0.0);
        assert_eq!(detail_metrics(&[1.0, 2.0], &[1.0, 1.0], 2, 1).iso_mean, 0.0);
    }

    /// **The detail invariant is ONE-SIDED and this test is what says so.**
    ///
    /// The orchestrator MEASURED, in a 1-D optics simulation calibrated to
    /// reproduce facts 12/27/28 to 3-4 digits (25 frames, oracle depth, latent
    /// mean|grad| 0.0392):
    ///
    /// | sigma | mean\|grad\| sel | wiener | grad corr sel | grad corr wiener |
    /// |---|---|---|---|---|
    /// | 0.010 | 0.0296 | 0.0367 | 0.8595 | 0.7538 |
    /// | 0.050 | 0.0455 | 0.0293 | 0.5592 | 0.6629 |
    ///
    /// At sigma 0.010 the Wiener merge has **24% more** gradient magnitude and
    /// **12% less** gradient correlation with the truth — the extra magnitude is
    /// ringing sitting where no edge exists. At sigma 0.050 argmax selection
    /// reads 0.0455, **above the ground truth's 0.0392**: pure noise inflating
    /// the metric past the true value.
    ///
    /// A two-sided reading scores both of those as wins. So `detail_verdict`
    /// must never return a passing string for a large increase, and this test
    /// fails if someone later "simplifies" it into `retention >= floor`.
    #[test]
    fn a_gradient_increase_is_never_scored_as_a_pass() {
        // Fact 24's collapse: -58% and -53%.
        assert_eq!(detail_verdict(0.42), "COLLAPSE");
        assert_eq!(detail_verdict(0.47), "COLLAPSE");
        // The orchestrator's plain-mean reproduction: -49% to -51%.
        assert_eq!(detail_verdict(0.51), "COLLAPSE");
        assert_eq!(detail_verdict(0.49), "COLLAPSE");

        // Identity and small measurement scatter are not verdicts.
        for r in [1.0, 1.02, 1.10] {
            assert_eq!(detail_verdict(r), "ok", "near-identity reading {r} flagged");
        }

        // And the direction that matters: a large rise is NOT a pass.
        for r in [1.6, 2.0, 5.0] {
            let v = detail_verdict(r);
            assert_ne!(v, "ok", "retention {r} was scored as acceptable");
            assert_eq!(v, "INVESTIG.");
        }
    }

    /// The merge's speckle companion has to be quoted at the same tolerance as
    /// `strehl stack`'s, or the two numbers are not comparable and the companion
    /// is worthless. One constant, in core, imported by both.
    #[test]
    fn the_speckle_companion_uses_the_same_tolerance_as_the_argmax_baseline() {
        assert_eq!(
            SPECKLE_TOLERANCE,
            strehl_core::stack::DEFAULT_SPECKLE_TOLERANCE
        );
        assert_eq!(SPECKLE_TOLERANCE, crate::stack::speckle_tolerance_in_use());
    }

    #[test]
    fn the_plan_is_bounded_by_memory_and_scales_down_as_accumulators_are_added() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        let frame_bytes = 66_000_000;
        let one = Plan::new(105, geom, frame_bytes, 1, 0, 0);
        let eight = Plan::new(105, geom, frame_bytes, 8, 0, 0);
        let roi_bytes = 3_000_000;
        let with_detail_control = Plan::new(105, geom, frame_bytes, 1, 0, roi_bytes);
        assert!(
            eight.workers <= one.workers,
            "more accumulators must not license more workers: {} vs {}",
            eight.workers,
            one.workers
        );
        assert!(eight.workers >= 1);
        assert_eq!(with_detail_control.roi_bytes, roi_bytes);
        assert_eq!(
            with_detail_control.pass2_bytes - one.pass2_bytes,
            roi_bytes,
            "the compact selector ROIs must be priced into pass two"
        );
        assert!(with_detail_control.workers <= one.workers);
        // The budget is the thing that has to hold, in both passes.
        for p in [&one, &eight] {
            assert!(
                p.chunks * p.pass1_bytes.max(p.pass2_bytes) <= MEMORY_BUDGET_BYTES
                    || p.workers == 1,
                "plan exceeds the budget without being cornered at one worker"
            );
        }
    }

    /// The memory ratchet, extended for `--stats`. Two things have to hold and
    /// they pull in opposite directions: turning the statistics on must be
    /// **priced** (so it cannot license more workers than the budget pays for),
    /// and its price must be **constant in the frame count** (so the ratchet in
    /// SYNTHESIS §3.2.1 is not quietly broken by an O(frames) object).
    #[test]
    fn the_statistics_are_priced_into_the_plan_and_do_not_grow_with_the_stack() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        let frame_bytes = 66_000_000;
        let off = Plan::new(105, geom, frame_bytes, 1, 0, 0);
        let on = Plan::new(105, geom, frame_bytes, 1, 1, 0);
        let with_placebo = Plan::new(105, geom, frame_bytes, 1, 2, 0);

        assert_eq!(off.stats_bytes, 0, "off must cost nothing");
        assert!(
            on.pass2_bytes > off.pass2_bytes,
            "the gather must be priced into pass two, not hidden outside it"
        );
        assert!(
            on.workers <= off.workers,
            "a bigger working set must not license more workers: {} vs {}",
            on.workers,
            off.workers
        );
        assert!(
            with_placebo.stats_bytes > on.stats_bytes,
            "the placebo is a second gather and must be paid for"
        );

        // Constant in the frame count: the whole point of the seam decision.
        for frames in [22usize, 33, 105, 400] {
            let p = Plan::new(frames, geom, frame_bytes, 1, 1, 0);
            assert_eq!(
                p.stats_bytes, on.stats_bytes,
                "{frames} frames changed the statistics footprint; it is supposed \
                 to be O(1) in the stack depth"
            );
        }

        // And it must genuinely beat the object it replaces at corpus depth.
        let px = geom.pixels();
        let volume_22 = px * 4 * 22;
        assert!(
            on.stats_bytes < volume_22,
            "{} B of statistics is not cheaper than a 22-frame fine focus volume \
             at {} B; the seam decision was wrong",
            on.stats_bytes,
            volume_22
        );
        assert!(on.workers >= 1);
        assert!(
            on.chunks * on.pass1_bytes.max(on.pass2_bytes) <= MEMORY_BUDGET_BYTES
                || on.workers == 1,
            "the statistics plan exceeds the budget without being cornered at one worker"
        );
    }

    #[test]
    fn every_frame_is_covered_exactly_once_by_the_chunking() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        for frames in [1usize, 2, 7, 22, 33, 63, 79, 105] {
            let plan = Plan::new(frames, geom, 66_000_000, 3, 0, 0);
            let mut seen = vec![0u32; frames];
            for ci in 0..plan.chunks {
                let start = ci * plan.chunk_len;
                let end = (start + plan.chunk_len).min(frames);
                for s in seen.iter_mut().take(end).skip(start) {
                    *s += 1;
                }
            }
            assert!(
                seen.iter().all(|c| *c == 1),
                "{frames} frames: coverage was {seen:?}"
            );
        }
    }

    /// Both merge banners state which backend is the default, and both used to
    /// state it as a literal.
    ///
    /// Measured rather than supposed: a release binary built from this tree
    /// with `DEFAULT_MERGE_BACKEND` flipped to `Pyramid` printed `(--merge
    /// pyramid; reachable, NOT the default)` on a run where the pyramid *was*
    /// the default. The `--help` seam in `main.rs` did not catch it, because a
    /// banner is not help text -- it is the line every run prints, which makes
    /// it the copy a user is most likely to read and believe.
    #[test]
    fn both_merge_banners_state_the_role_the_constant_gives_them() {
        for backend in [MergeBackend::Estimator, MergeBackend::Pyramid] {
            let line = merge_banner(backend);
            let claims_default = line.contains("THE DEFAULT PATH");
            let claims_not = line.contains("NOT the default");
            assert_ne!(
                claims_default, claims_not,
                "`{}`'s banner must make exactly one claim about its role: {line:?}",
                backend.name()
            );
            assert_eq!(
                claims_default,
                backend == DEFAULT_MERGE_BACKEND,
                "`{}`'s banner and DEFAULT_MERGE_BACKEND (`{}`) disagree: {line:?}",
                backend.name(),
                DEFAULT_MERGE_BACKEND.name()
            );
        }
    }

    /// Every branch of [`merge_banner_for`], including the two the constant
    /// does not currently select.
    ///
    /// Exercising only the live branch would report a pass for two strings
    /// nobody had read -- and those two are exactly the ones that go live on
    /// the day the default moves, which is the day nobody wants to discover
    /// them.
    #[test]
    fn all_four_banner_strings_are_distinct_and_self_consistent() {
        let mut seen = Vec::new();
        for backend in [MergeBackend::Estimator, MergeBackend::Pyramid] {
            for is_default in [true, false] {
                let line = merge_banner_for(backend, is_default);
                assert_eq!(
                    line.contains("THE DEFAULT PATH"),
                    is_default,
                    "`{}` is_default={is_default}: {line:?}",
                    backend.name()
                );
                assert_eq!(
                    line.contains("NOT the default"),
                    !is_default,
                    "`{}` is_default={is_default}: {line:?}",
                    backend.name()
                );
                assert!(
                    line.contains(backend.name()),
                    "`{}` is_default={is_default} does not name its backend: {line:?}",
                    backend.name()
                );
                seen.push(line);
            }
        }
        seen.sort_unstable();
        let before = seen.len();
        seen.dedup();
        assert_eq!(before, seen.len(), "two banner branches share one string");
    }

    /// The two lines this build actually prints, pinned.
    ///
    /// Deriving the role from the constant rewrote copy that a large body of
    /// logs and harness output already contains, so it had to change no bytes
    /// on the path that ships. Pinned against an explicit `is_default` rather
    /// than against the constant, so it stays a statement about the strings
    /// instead of quietly becoming vacuous the day the default moves.
    #[test]
    fn the_shipping_banner_bytes_are_unchanged_by_deriving_the_role() {
        assert_eq!(
            merge_banner_for(MergeBackend::Estimator, true),
            "strehl stack -- regularised winner + noise-gated average (THE DEFAULT PATH, an estimator)"
        );
        assert_eq!(
            merge_banner_for(MergeBackend::Pyramid, false),
            "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; reachable, NOT the default)"
        );
    }

    /// `MergeBackend::parse` decides which merge a user gets, and had no test
    /// of any kind -- nothing in CI would have caught a regression in it.
    #[test]
    fn merge_backend_parse_accepts_every_documented_spelling() {
        for v in ["pyramid", "bands", "blend", "PYRAMID", "  Pyramid  "] {
            assert_eq!(
                MergeBackend::parse(v).unwrap(),
                MergeBackend::Pyramid,
                "{v:?}"
            );
        }
        for v in ["estimator", "merge", "legacy", "ESTIMATOR", "  Legacy  "] {
            assert_eq!(
                MergeBackend::parse(v).unwrap(),
                MergeBackend::Estimator,
                "{v:?}"
            );
        }
    }

    /// An unrecognised spelling is an error and never a backend by accident --
    /// the rule `--photometric` follows, for the same reason: a merge that
    /// silently fell back is indistinguishable, from the terminal, from one
    /// that did what was asked.
    ///
    /// The empty and whitespace cases are here deliberately. `parse` refuses
    /// them; `stated_merge_backend` never asks it about them, because its
    /// `!v.trim().is_empty()` guard routes them to "no opinion" first. That
    /// asymmetry is a property of the resolver, not of the parser, and this
    /// test pins which of the two owns it.
    #[test]
    fn merge_backend_parse_refuses_unknown_spellings() {
        for v in ["banana", "", "   ", "pyramidal", "est", "0", "1", "on", "off"] {
            let err = MergeBackend::parse(v).unwrap_err().to_string();
            assert!(
                err.contains("unknown merge backend"),
                "{v:?} was not refused as unknown: {err}"
            );
            assert!(
                err.contains("estimator") && err.contains("pyramid"),
                "{v:?}'s refusal does not name both valid values: {err}"
            );
        }
    }

    /// `--pyramid-select`, which had no test.
    #[test]
    fn parse_select_mode_accepts_its_spellings_and_refuses_the_rest() {
        for v in ["soft", "soft-power", "softpower", "SOFT", " Soft "] {
            assert_eq!(parse_select_mode(v).unwrap(), SelectMode::SoftPower, "{v:?}");
        }
        for v in ["hard", "hard-max", "hardmax", "pmax", "HARD"] {
            assert_eq!(parse_select_mode(v).unwrap(), SelectMode::HardMax, "{v:?}");
        }
        for v in ["", "  ", "softest", "max", "hard_max"] {
            let err = parse_select_mode(v).unwrap_err().to_string();
            assert!(
                err.contains("unknown --pyramid-select"),
                "{v:?} was not refused: {err}"
            );
        }
    }

    /// `--pyramid-base`, which had no test.
    #[test]
    fn parse_base_band_accepts_its_spellings_and_refuses_the_rest() {
        for v in ["mean", "MEAN", " Mean "] {
            assert_eq!(parse_base_band(v).unwrap(), BaseBand::Mean, "{v:?}");
        }
        for v in ["weighted", "weighted-from-coarsest", "WEIGHTED"] {
            assert_eq!(
                parse_base_band(v).unwrap(),
                BaseBand::WeightedFromCoarsest,
                "{v:?}"
            );
        }
        for v in ["", "  ", "average", "coarsest", "weight"] {
            let err = parse_base_band(v).unwrap_err().to_string();
            assert!(
                err.contains("unknown --pyramid-base"),
                "{v:?} was not refused: {err}"
            );
        }
    }

    /// What [`choose_merge_backend`] answers when no backend-family flag was
    /// given: the stated backend, or the default. This is the shape the old
    /// `resolve_merge_backend` had, kept as a test helper rather than as a
    /// public function so that the binary has exactly one entry point and this
    /// file gains no unreachable code while removing some.
    fn resolved(flag: Option<&str>) -> Result<MergeBackend> {
        choose_merge_backend(flag, &[], &[]).map(|c| c.backend)
    }

    /// Everything in this module that reads the environment, in one `#[test]`.
    ///
    /// Rust runs tests as threads sharing one process environment, so these
    /// cannot be separate `#[test]`s without becoming order-dependent.
    /// `align_cmd.rs`'s `the_solve_environment_keys_the_cache` serialises its
    /// env-reading assertions the same way and for the same reason.
    ///
    /// Each half ends by clearing its variable and re-asserting the unset
    /// result, so a leaked variable fails here rather than in whichever test
    /// happens to run next.
    #[test]
    fn the_merge_environment_channels_behave() {
        // SAFETY: single-threaded within this test; see the doc comment.
        unsafe { std::env::remove_var(MERGE_BACKEND_ENV) };
        unsafe { std::env::remove_var(BAND_WORKERS_ENV) };

        assert_eq!(
            resolved(None).unwrap(),
            DEFAULT_MERGE_BACKEND,
            "an unset {MERGE_BACKEND_ENV} did not give the default"
        );
        for (v, want) in [
            ("pyramid", MergeBackend::Pyramid),
            ("legacy", MergeBackend::Estimator),
        ] {
            unsafe { std::env::set_var(MERGE_BACKEND_ENV, v) };
            assert_eq!(
                resolved(None).unwrap(),
                want,
                "{MERGE_BACKEND_ENV}={v}"
            );
        }
        unsafe { std::env::set_var(MERGE_BACKEND_ENV, "banana") };
        assert!(
            resolved(None).is_err(),
            "an unrecognised {MERGE_BACKEND_ENV} was not an error"
        );
        unsafe { std::env::set_var(MERGE_BACKEND_ENV, "estimator") };
        assert_eq!(
            resolved(Some("pyramid")).unwrap(),
            MergeBackend::Pyramid,
            "--merge did not outrank {MERGE_BACKEND_ENV}"
        );
        // F5. The flag WINNING must not mean the environment goes unread. A
        // malformed STREHL_MERGE is a mistake in the caller's harness whether
        // or not this particular run also passed --merge, and reporting it only
        // when the flag is absent makes the error blink in and out with an
        // unrelated argument. Measured before the fix: this combination exited
        // 0 and ran the estimator without a word about `banana`.
        unsafe { std::env::set_var(MERGE_BACKEND_ENV, "banana") };
        let err = resolved(Some("estimator"))
            .expect_err("a malformed STREHL_MERGE was excused because --merge was present")
            .to_string();
        assert!(
            err.contains("banana"),
            "the refusal does not name the offending environment value: {err}"
        );
        unsafe { std::env::remove_var(MERGE_BACKEND_ENV) };

        // Both spellings of the flag, through the resolver rather than through
        // `parse`, because the resolver is what main.rs actually calls.
        for (v, want) in [
            ("pyramid", MergeBackend::Pyramid),
            ("estimator", MergeBackend::Estimator),
            ("legacy", MergeBackend::Estimator),
        ] {
            assert_eq!(
                resolved(Some(v)).unwrap(),
                want,
                "--merge {v} did not resolve to {want:?}"
            );
        }
        assert!(
            resolved(Some("banana")).is_err(),
            "an unrecognised --merge value was not an error"
        );
        // Empty and whitespace-only are errors in the FLAG channel, where they
        // can only be a typo, and the default in the ENV channel, where they
        // mean an exported-but-cleared variable. Pinned because the two
        // channels genuinely differ and that is easy to "tidy" into a bug.
        for v in ["", "   "] {
            assert!(
                resolved(Some(v)).is_err(),
                "--merge {v:?} was not an error"
            );
            unsafe { std::env::set_var(MERGE_BACKEND_ENV, v) };
            assert_eq!(
                resolved(None).unwrap(),
                DEFAULT_MERGE_BACKEND,
                "{MERGE_BACKEND_ENV}={v:?} did not mean `no opinion`"
            );
        }
        unsafe { std::env::remove_var(MERGE_BACKEND_ENV) };
        assert_eq!(
            resolved(None).unwrap(),
            DEFAULT_MERGE_BACKEND,
            "the resolver did not return to its unset value"
        );

        // ---- inference, when and only when the caller stated nothing -------
        let est = ["--gate"];
        let pyr = ["--pyramid-gate"];
        let none: [&str; 0] = [];

        let c = choose_merge_backend(None, &none, &none).unwrap();
        assert_eq!(c.backend, DEFAULT_MERGE_BACKEND, "neither family");
        assert_eq!(c.source, MergeSource::Default);
        assert!(c.why.contains("default"), "{}", c.why);

        let c = choose_merge_backend(None, &est, &none).unwrap();
        assert_eq!(c.backend, MergeBackend::Estimator, "estimator-only family");
        assert_eq!(c.source, MergeSource::Inferred);
        assert!(
            c.why.contains("--gate") && c.why.contains("--merge pyramid"),
            "the inference does not say what decided it or how to override: {}",
            c.why
        );

        let c = choose_merge_backend(None, &none, &pyr).unwrap();
        assert_eq!(c.backend, MergeBackend::Pyramid, "pyramid-only family");
        assert_eq!(c.source, MergeSource::Inferred);
        assert!(
            c.why.contains("--pyramid-gate") && c.why.contains("--merge estimator"),
            "{}",
            c.why
        );

        // Both families and no --merge is genuinely ambiguous. A merge chosen
        // by tie-break is a merge nobody chose.
        let err = choose_merge_backend(None, &est, &pyr)
            .expect_err("both families with no --merge was not refused")
            .to_string();
        assert!(
            err.contains("--gate") && err.contains("--pyramid-gate"),
            "the ambiguity error does not name both offending flags: {err}"
        );

        // A STATED backend outranks inference in both channels. Stating it does
        // NOT suppress the refusal: that is main.rs's table, which sees the
        // same `given` booleans either way.
        let c = choose_merge_backend(Some("pyramid"), &est, &none).unwrap();
        assert_eq!(
            c.backend,
            MergeBackend::Pyramid,
            "--merge did not outrank inference"
        );
        assert_eq!(c.source, MergeSource::Flag);

        unsafe { std::env::set_var(MERGE_BACKEND_ENV, "pyramid") };
        let c = choose_merge_backend(None, &est, &none).unwrap();
        assert_eq!(
            c.backend,
            MergeBackend::Pyramid,
            "{MERGE_BACKEND_ENV} did not outrank inference -- an env var that parses, prints \
             nothing and does nothing is the failure this module refuses to ship"
        );
        assert_eq!(c.source, MergeSource::Env);
        unsafe { std::env::remove_var(MERGE_BACKEND_ENV) };

        let third = MEMORY_BUDGET_BYTES / 3;
        assert_eq!(
            band_workers(third, 64).unwrap(),
            3,
            "the memory budget did not bound the worker count"
        );
        assert_eq!(
            band_workers(third, 2).unwrap(),
            2,
            "the frame count did not bound the worker count"
        );
        assert_eq!(
            band_workers(usize::MAX, 8).unwrap(),
            1,
            "a worker too large to fit must still leave one"
        );
        assert_eq!(
            band_workers(1, 0).unwrap(),
            1,
            "zero frames must not give zero workers"
        );
        unsafe { std::env::set_var(BAND_WORKERS_ENV, "2") };
        assert_eq!(
            band_workers(third, 64).unwrap(),
            2,
            "{BAND_WORKERS_ENV} did not override the solved count"
        );
        unsafe { std::env::set_var(BAND_WORKERS_ENV, "999") };
        assert_eq!(
            band_workers(third, 5).unwrap(),
            5,
            "{BAND_WORKERS_ENV} was not clamped to the frame count"
        );
        for bad in ["0", "abc", "-1", "2.5"] {
            unsafe { std::env::set_var(BAND_WORKERS_ENV, bad) };
            assert!(
                band_workers(third, 64).is_err(),
                "{BAND_WORKERS_ENV}={bad} was not refused"
            );
        }
        unsafe { std::env::remove_var(BAND_WORKERS_ENV) };
        assert_eq!(
            band_workers(third, 64).unwrap(),
            3,
            "band_workers did not return to its unset value"
        );

        // The photometric channel, added when its default flipped from `Off`
        // to `On`. What this resolver returns unset IS the product default,
        // and the reason it is asserted by execution rather than by reading is
        // that reading is what failed: the switch registry declared this
        // default `auto` while the code returned `Off`, and nothing caught the
        // disagreement because nothing ran the line.
        unsafe { std::env::remove_var(PHOTOMETRIC_ENV) };
        assert_eq!(
            resolve_photometric_mode(None).unwrap().0,
            DEFAULT_PHOTOMETRIC_MODE,
            "an unset {PHOTOMETRIC_ENV} did not give the default"
        );
        // Deliberately a change-detector, in the spirit of the byte freezes:
        // the default is a shipped product decision backed by a corpus run, so
        // moving it should require editing a test that says so out loud.
        assert_eq!(
            DEFAULT_PHOTOMETRIC_MODE,
            PhotometricMode::On,
            "the shipped photometric default moved; if that was deliberate, the byte-freeze rows \
             and scripts/check-defaults.py both describe it and both must move with it"
        );
        for (v, want) in [
            ("off", PhotometricMode::Off),
            ("on", PhotometricMode::On),
            ("auto", PhotometricMode::Auto),
        ] {
            unsafe { std::env::set_var(PHOTOMETRIC_ENV, v) };
            assert_eq!(
                resolve_photometric_mode(None).unwrap().0,
                want,
                "{PHOTOMETRIC_ENV}={v}"
            );
        }
        unsafe { std::env::set_var(PHOTOMETRIC_ENV, "banana") };
        assert!(
            resolve_photometric_mode(None).is_err(),
            "an unrecognised {PHOTOMETRIC_ENV} was not an error"
        );
        unsafe { std::env::set_var(PHOTOMETRIC_ENV, "on") };
        assert_eq!(
            resolve_photometric_mode(Some("off")).unwrap().0,
            PhotometricMode::Off,
            "--photometric did not outrank {PHOTOMETRIC_ENV}"
        );
        unsafe { std::env::remove_var(PHOTOMETRIC_ENV) };
        assert_eq!(
            resolve_photometric_mode(None).unwrap().0,
            DEFAULT_PHOTOMETRIC_MODE,
            "the resolver did not return to its unset value"
        );

        // PROVENANCE. The banner printed `on (unconditional, as asked)` on
        // THIS branch -- no flag, no environment variable, nothing but the
        // compiled-in default. "As asked" is a claim about the CALLER, and a
        // run banner is the only durable record of what produced an artifact,
        // so emitting it unconditionally makes that record false in exactly
        // the case a later reader cannot reconstruct: when a default did the
        // work. These assertions live inside this test rather than in one of
        // their own because they share `PHOTOMETRIC_ENV` with the block above,
        // and two tests mutating one process-wide variable race.
        unsafe { std::env::remove_var(PHOTOMETRIC_ENV) };
        let (mode, source) = resolve_photometric_mode(None).unwrap();
        assert_eq!(
            mode, DEFAULT_PHOTOMETRIC_MODE,
            "the source-reporting resolver disagreed with the mode-only one \
             about the unset default"
        );
        assert_eq!(
            source,
            SettingSource::Default,
            "nothing named a photometric mode, so the source must be the default"
        );
        assert!(
            !source.asked(),
            "the default branch reported that somebody asked"
        );
        let said = source.describe("--photometric", PHOTOMETRIC_ENV);
        assert!(
            !said.contains("as asked"),
            "the photometric banner still claims consent it never got: {said:?}"
        );

        // The other direction, which is what stops the degenerate "fix" of
        // deleting the phrase everywhere: when somebody DID ask, in either
        // channel, the banner must still say so and must name the channel. A
        // provenance line that reports every run identically has not recorded
        // provenance, it has stopped recording anything.
        unsafe { std::env::set_var(PHOTOMETRIC_ENV, "off") };
        let (_, source) = resolve_photometric_mode(None).unwrap();
        assert_eq!(
            source,
            SettingSource::Env,
            "{PHOTOMETRIC_ENV} carried the mode but was not credited with it"
        );
        let said = source.describe("--photometric", PHOTOMETRIC_ENV);
        assert!(
            source.asked() && said.contains("as asked") && said.contains(PHOTOMETRIC_ENV),
            "an environment-supplied mode must be reported as asked, and must \
             name the variable a reader has to inspect: {said:?}"
        );

        let (_, source) = resolve_photometric_mode(Some("on")).unwrap();
        assert_eq!(
            source,
            SettingSource::Flag,
            "--photometric carried the mode but was not credited with it"
        );
        let said = source.describe("--photometric", PHOTOMETRIC_ENV);
        assert!(
            source.asked() && said.contains("as asked") && said.contains("--photometric"),
            "a flag-supplied mode must be reported as asked, and must name the \
             flag: {said:?}"
        );
        unsafe { std::env::remove_var(PHOTOMETRIC_ENV) };
    }

    /// The estimator refusal, both arms.
    ///
    /// # Why this is one `#[test]` with four assertions rather than four tests
    ///
    /// The same reason as `the_merge_environment_channels_behave`: these read
    /// and write the process environment, which Rust's test harness shares
    /// across threads. Split, they would pass or fail depending on scheduling.
    ///
    /// # What each arm is for
    ///
    /// The project's standing rule is that a metric — or here, a refusal —
    /// shown only inputs it is supposed to reject cannot be distinguished from
    /// one that rejects everything. So:
    ///
    /// 1. **Fires**: estimator + correction configured → `Err`, and the text
    ///    must name the backend that cannot apply it, the backend that can, and
    ///    must say the correction was *not applied*. A user must not be able to
    ///    read it as a warning.
    /// 2. **Negative control, across the backend axis**: pyramid + the *same*
    ///    correction configured → `Ok`. Pyramid is the backend the correction
    ///    is wired into; refusing there would be the refusal firing on a
    ///    correctly-configured render.
    /// 3. **Negative control, across the configuration axis**: estimator +
    ///    `STREHL_DEFECT=off` → `Ok`. This is the arm the brief asked for: the
    ///    estimator still runs normally when no correction is configured.
    /// 4. **Negative control, across the arm axis**: estimator +
    ///    `STREHL_DEFECT_ARM=none` → `Ok`. A map that is loaded but corrects
    ///    nothing drops nothing, so there is nothing to refuse. This arm exists
    ///    because it is the one place the refusal could plausibly be too eager,
    ///    and "configured" is easy to conflate with "would change pixels".
    #[test]
    fn the_estimator_refuses_a_configured_defect_correction_it_cannot_apply() {
        // SAFETY: single-threaded within this test; see the doc comment.
        unsafe { std::env::remove_var("STREHL_DEFECT") };
        unsafe { std::env::remove_var("STREHL_DEFECT_ARM") };
        unsafe { std::env::remove_var("STREHL_DEFECT_MAP") };

        // 1. Fires. The correction is OFF by default, so the firing arm has to
        //    configure one -- and the two ways of configuring one are `on` and
        //    naming a map, so both are exercised. A refusal that only caught
        //    `STREHL_DEFECT=on` would miss the more likely invocation.
        for (k, v) in [("STREHL_DEFECT", "on"), ("STREHL_DEFECT_MAP", "some-map.txt")] {
            unsafe { std::env::remove_var("STREHL_DEFECT") };
            unsafe { std::env::remove_var("STREHL_DEFECT_MAP") };
            unsafe { std::env::set_var(k, v) };
            let err = preflight_defect_backend_support(MergeBackend::Estimator)
                .expect_err(&format!(
                    "the estimator accepted a correction configured by {k}={v}"
                ))
                .to_string();
            let lower = err.to_ascii_lowercase();
            for needle in ["estimator", "pyramid", "not applied"] {
                assert!(
                    lower.contains(needle),
                    "the refusal for {k}={v} does not contain {needle:?}, so a reader \
                     cannot tell what was dropped or what to run instead: {err}"
                );
            }
            assert!(
                lower.contains("refusing") && lower.contains("not a warning"),
                "the refusal does not say it refused, so it is readable as advice \
                 about a render that nevertheless happened: {err}"
            );
        }
        unsafe { std::env::remove_var("STREHL_DEFECT_MAP") };
        unsafe { std::env::set_var("STREHL_DEFECT", "on") };

        // 2. Negative control across the backend axis.
        preflight_defect_backend_support(MergeBackend::Pyramid).expect(
            "the refusal fired on `pyramid`, which is the backend that DOES apply \
             the correction -- it is refusing a correct configuration",
        );

        // 3. Negative control across the configuration axis. This is also the
        //    DEFAULT, so it is the arm that says an ordinary render is not
        //    disturbed by a feature nobody asked for.
        unsafe { std::env::set_var("STREHL_DEFECT", "off") };
        preflight_defect_backend_support(MergeBackend::Estimator)
            .expect("the estimator was refused with the correction explicitly off");
        unsafe { std::env::remove_var("STREHL_DEFECT") };
        preflight_defect_backend_support(MergeBackend::Estimator)
            .expect("the estimator was refused with NOTHING configured, i.e. by default");

        // 4. Negative control across the arm axis.
        unsafe { std::env::set_var("STREHL_DEFECT", "on") };
        unsafe { std::env::set_var("STREHL_DEFECT_ARM", "none") };
        preflight_defect_backend_support(MergeBackend::Estimator).expect(
            "the estimator was refused for a correction with no arms selected, \
             which would not have changed a pixel",
        );

        // A malformed value must reach the caller as the parse error it is,
        // rather than being swallowed into either verdict. This is the
        // `a_typod_override_errors_rather_than_falling_back_to_the_default`
        // shape, applied at the point the refusal reads the environment.
        unsafe { std::env::set_var("STREHL_DEFECT", "1") };
        let err = preflight_defect_backend_support(MergeBackend::Estimator)
            .expect_err("STREHL_DEFECT=1 was accepted as a setting")
            .to_string();
        assert!(
            err.contains("STREHL_DEFECT") && err.contains("\"1\""),
            "the parse error does not name the variable and the offending value: {err}"
        );

        unsafe { std::env::remove_var("STREHL_DEFECT") };
        unsafe { std::env::remove_var("STREHL_DEFECT_ARM") };
        preflight_defect_backend_support(MergeBackend::Estimator).expect(
            "the environment leaked out of this test: with nothing set the \
             estimator must run",
        );
    }
    /// Every `Develop` handed to a writer must carry the exposure gain.
    ///
    /// This is a WIRING guard, and it exists because the wiring is exactly what
    /// failed. The behavioural claim -- that a commanded exposure reaches the
    /// pixels -- is asserted by
    /// `image_out::tests::an_exposure_request_changes_the_pixels_and_not_only_the_banner`,
    /// which regresses the LSQ slope against the unexposed arm and was
    /// commissioned RED by planting the original defect. That test passes
    /// happily while this file forgets to pass the gain in, because it never
    /// sees this file.
    ///
    /// The defect being guarded: `--exposure` was applied upstream in `norm`
    /// and then divided straight back out by `--srgb`'s auto-tone, whose two
    /// anchors are both linear in the data. MEASURED before the fix: a
    /// commanded 64x span between `--exposure 3` and `--exposure -3` delivered
    /// a regression slope of 1.0000000 with all 98,898,048 samples
    /// bit-identical. The only bytes that moved were the banner inside
    /// `ImageDescription`, which is why a whole-file hash read it as working.
    ///
    /// This COUNTS and PARTITIONS rather than searching. A substring check is
    /// satisfied by any one occurrence, so it would still pass on the day a
    /// third writer is added without the builder -- the same class of blind
    /// spot that let the original defect ship. Requiring the two counts to be
    /// equal makes an unchained site fail loudly.
    #[test]
    fn every_writer_develop_carries_the_exposure_gain() {
        let src = include_str!("merge_cmd.rs");
        // The needles are assembled at runtime so that this test cannot match
        // its OWN source text. Spelled as literals, each needle would occur
        // inside this function and inflate the count it is used to take -- the
        // guard would then pass or fail for reasons having nothing to do with
        // the writers it is watching. A self-counting check is not a check.
        let needle_dev = [".", "develop("].concat();
        let needle_gain = [".", "with_exposure_gain("].concat();
        let developed = src.matches(needle_dev.as_str()).count();
        let carried = src.matches(needle_gain.as_str()).count();
        assert!(
            developed > 0,
            "no develop site was found at all -- this guard has lost its \
             target and is asserting nothing"
        );
        assert_eq!(
            developed, carried,
            "{developed} writer develop site(s) but only {carried} carry the \
             exposure gain builder. An unchained writer silently cancels the \
             commanded exposure -- see docs/research/BUILD-DEFECT.md S14."
        );
    }
}
