//! Optical restoration of the finished stack (`STREHL_OPTICAL_RESTORE`): on by
//! default for pixel-shift stacks with colour carry, off otherwise, `off` or
//! `on` to override (owner's call of 2026-11-16 on one subject; to be measured
//! on a second). Defaulted, a stack it cannot measure is written unrestored
//! with a warning; asked for, that is an error. The filter is
//! `strehl_core::optical_restore`'s; this module gathers what it measures and
//! applies it at the write.
//!
//! # Why
//!
//! On the A7CR scarab (2026-11-15) the prototype's restoration lifted the
//! blended stack's fine detail by 1.25-1.4x at modest noise, and depth-guided
//! fusion (`STREHL_FUSION=depth`) trades about a fifth of the finest detail for
//! half the noise: the blend of neighbouring planes softens what restoration
//! can put back, given a measurement of what it cost.
//!
//! # What is measured, and where
//!
//! * In-focus tiles of 256 px, from the depth measurement
//!   (`depth_guide`, run for this even when the fusion is off): half the
//!   tile's cells must show a confident focus peak, and two folded frames
//!   must lie at its focus plane (finest band, median).
//! * Those two frames' prepared planes on each tile ([`observe`]) -- the
//!   reference, two single frames at focus: kept as the fold passes when
//!   the depth pre-pass ran, or, when depth was measured during the fold
//!   (`STREHL_DEPTH_PASS=fused`, the default), prepared again after it over
//!   only the tiles' rows (`gather_restoration_references`).
//! * The fold keeps alternate folded frames in separate accumulators
//!   (`BandWorker::alt`, or the GPU fold's second accumulator); their sum is
//!   the full stack, and each half is finished on its own ([`stash_halves`]).
//! * At the write ([`restore`]): every tile developed to linear RGB exactly as
//!   the output is (normalisation, then Malvar or the carried colour), the
//!   halves' and the reference's spectra, the cutoff fitted on the reference,
//!   the blend transfer, the filter, applied in the square-root domain
//!   (`sqrt(v + 25 DN)`, as the prototype's arm `f5`: a highlight fifty times
//!   its surround cannot drive its surround below zero), and kept off within
//!   about ten photosites of a sample at the raw pin (plan D3).
//! * The target's strength (plan D2): the sharpest Gaussian target, 0.70 to
//!   0.35 px, whose restored noise power in 0.30-0.50 cycles/px stays within
//!   the Detail budget (`stack --detail`, [`DETAIL_ENV`]) times the
//!   unrestored, on green's measured noise.
//!
//! # Limits
//!
//! The depth measurement (during the fold by default, else an extra gather
//! of every frame), the reference tiles' frames gathered again, twice the
//! merge's accumulator memory, and two finished halves. `--demosaic` output
//! only. The model is diffraction, photosite aperture and the blend; any
//! other blur is left in.
use super::*;
use std::sync::Mutex;
use strehl_core::optical_restore as core;

#[path = "optical-cutoffs.rs"]
mod cutoffs;

pub(super) const ENV: &str = "STREHL_OPTICAL_RESTORE";
/// Target Gaussian sigma, output px (experiment control): when set, this
/// target is used as given and the Detail budget ([`DETAIL_ENV`]) is not
/// consulted.
pub(super) const SIGMA_ENV: &str = "STREHL_OPTICAL_RESTORE_SIGMA";
/// Plan D2's strength, published by `stack --detail`: `natural`, `safe`
/// (the default), `crisp`, or a noise budget `B` in 1.0-6.0.
pub(crate) const DETAIL_ENV: &str = "STREHL_DETAIL";

/// The owner's Detail control (plan D2): how far the restoration may lift
/// the finest bands' noise for crispness.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Detail {
    /// The shipped target, 0.70 px, never below the system (plan Q2): no
    /// budget.
    Natural,
    /// The sharpest target whose restored noise power in 0.30-0.50
    /// cycles/px is at most `B` times the unrestored.
    Budget { name: &'static str, budget: f64 },
}

/// Detail anchors, measured on the weevil (results note Q8, noise power at
/// 0.3-0.4 / 0.4-0.5 cycles/px against the unrestored half-stack): 0.50 px
/// cost 1.74 / 1.63, 0.40 px 2.67 / 3.27.
pub(crate) const SAFE_BUDGET: f64 = 1.7;
pub(crate) const CRISP_BUDGET: f64 = 3.3;

impl Detail {
    pub(crate) fn parse(v: &str) -> Result<Self> {
        Ok(match v.trim() {
            "natural" => Self::Natural,
            "" | "safe" => Self::Budget {
                name: "safe",
                budget: SAFE_BUDGET,
            },
            "crisp" => Self::Budget {
                name: "crisp",
                budget: CRISP_BUDGET,
            },
            other => {
                let b: f64 = other.parse().map_err(|_| {
                    anyhow::anyhow!(
                        "Detail {other:?} is not natural, safe, crisp or a budget number"
                    )
                })?;
                ensure!(
                    b.is_finite() && (1.0..=6.0).contains(&b),
                    "a Detail budget lies in 1.0-6.0 (times the unrestored noise power), not {b}"
                );
                Self::Budget {
                    name: "given",
                    budget: b,
                }
            }
        })
    }

    fn from_env() -> Result<Self> {
        match std::env::var(DETAIL_ENV) {
            Err(std::env::VarError::NotPresent) => Self::parse("safe"),
            Err(e) => Err(e).context(DETAIL_ENV),
            Ok(v) => Self::parse(&v).with_context(|| format!("{DETAIL_ENV}={v:?}")),
        }
    }
}

/// The prototype's arm `f5` and the Natural target: lifted detail without
/// visible grain on the scarab; 0.60 added grain.
const SIGMA_T: f64 = core::SIGMA_WIDEST;
/// The diffraction cutoffs R, G, B in cycles/px, when this stack cannot
/// measure them (a single-shot stack): measured on a four-shot run of the
/// same lens, aperture and magnification.
pub(super) const CUTOFF_ENV: &str = "STREHL_OPTICAL_RESTORE_CUTOFF";
/// A joint green cutoff at or above this is the fit's ceiling: no roll-off.
const JOINT_CEILING: f64 = 0.88;
/// Experiment hook: write the measured spectra here as JSON.
pub(super) const DUMP_ENV: &str = "STREHL_OPTICAL_RESTORE_DUMP";
/// `on` puts the gather's interpolation kernel into the system model
/// (proposal item 5): the phase-averaged Catmull-Rom response multiplies the
/// system transfer on each axis, and the reference spectra are divided by its
/// power before the cutoff fit (the reference frames were gathered too).
/// Default off. MEASURED by the proposal: without it the restoration falls
/// short of its own target by 3 / 11 / 26 % at 0.2 / 0.3 / 0.4 cycles/px on
/// an axis.
pub(super) const GATHER_ENV: &str = "STREHL_OPTICAL_RESTORE_GATHER";
/// `measured` replaces the colour carry's fixed chroma smoothing by a
/// Wiener filter of each colour difference designed from the halves' spectra
/// (proposal item 3); `smooth` (default) keeps the 1 px smoothing.
pub(super) const CHROMA_ENV: &str = "STREHL_CHROMA_FILTER";
const MAX_GAIN: f64 = 8.0;
/// Added before the square root, DN.
const ROOT_OFFSET_DN: f32 = 25.0;
/// Samples above this fraction of the black-to-white range count as clipped
/// for the spectrum tiles (the measurement's choice of tiles; unchanged by
/// plan D3).
const CLIP_FRACTION: f32 = 0.80;
/// Plan D3: the highlight guard keeps restoration off around merged samples
/// at or above this fraction of the raw pin (`Norm::pin`). Inside a pinned
/// plateau the merge reproduces the pin; the dilation covers its edges.
/// Before D3 the guard used [`CLIP_FRACTION`] of the white level (0.75 of
/// the pin on the A7CR), which also held back unpinned, real highlights and
/// the scales around them.
const PIN_FRACTION: f32 = 0.95;
/// Spectrum tile in plane px, and the margin each crop keeps for Malvar.
const TP: usize = core::TILE / 2;
const MARGIN: usize = 4;
const SIDE: usize = TP + 2 * MARGIN;
const MAX_TILES: usize = 200;
const MIN_TILES: usize = 8;
/// Kernel radius cap and truncation tolerance (gain units).
const MAX_RADIUS: usize = 32;
const TOLERANCE: f64 = 0.02;

/// `Some(true)` explicitly on, `Some(false)` explicitly off, `None` unset.
fn setting() -> Result<Option<bool>> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(None),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" => Ok(None),
            "0" | "off" => Ok(Some(false)),
            "on" | "1" => Ok(Some(true)),
            other => anyhow::bail!("{ENV}={other:?} is not off or on"),
        },
    }
}

/// Whether the operator explicitly asked for optical restoration.
pub(super) fn requested() -> Result<bool> {
    Ok(setting()? == Some(true))
}

/// Set while this render restores by default rather than on request: a
/// failure to measure then leaves the image unrestored, with a warning,
/// instead of failing the render.
static DEFAULTED: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);

/// Whether this render restores by default (not on request).
pub(super) fn defaulted() -> bool {
    DEFAULTED.load(std::sync::atomic::Ordering::Relaxed)
}

/// Set while a render runs again because its defaulted restoration found no
/// usable depth after a fold that measured depth as it went
/// (`depth_guide::Unmeasured`): why, for [`abandon`] at the point where the
/// pre-pass would have failed. The restoration is activated as before (the
/// fold's chunks are planned with it on) and abandoned there, so the second
/// render is exactly the render the pre-pass route gives such a stack.
static WITHOUT: Mutex<Option<String>> = Mutex::new(None);

/// Keeps a defaulted restoration abandoned while it lives.
pub(super) struct Without;

impl Without {
    pub(super) fn new(why: String) -> Self {
        *WITHOUT.lock().unwrap_or_else(|e| e.into_inner()) = Some(why);
        Self
    }
}

impl Drop for Without {
    fn drop(&mut self) {
        *WITHOUT.lock().unwrap_or_else(|e| e.into_inner()) = None;
    }
}

/// Why this render (run again) must abandon its defaulted restoration
/// before the fold, if it must.
pub(super) fn abandoned_before() -> Option<String> {
    WITHOUT.lock().unwrap_or_else(|e| e.into_inner()).clone()
}

/// Stop restoring this render (a defaulted restoration whose measurement
/// cannot run), saying why.
pub(super) fn abandon(why: &str) {
    *state() = None;
    eprintln!(
        "optical restore : off for this render -- on by default for pixel-shift stacks, but {why}"
    );
    crate::ui_progress::optical_restore("state=off", Some(why));
}

fn cutoff_override() -> Result<Option<[f64; 3]>> {
    let v = match std::env::var(CUTOFF_ENV) {
        Err(std::env::VarError::NotPresent) => return Ok(None),
        Err(e) => return Err(e).context(CUTOFF_ENV),
        Ok(v) => v,
    };
    let parts: Vec<f64> = v
        .split(',')
        .map(|p| p.trim().parse::<f64>())
        .collect::<std::result::Result<_, _>>()
        .with_context(|| format!("{CUTOFF_ENV}={v:?} is not three numbers"))?;
    ensure!(
        parts.len() == 3
            && parts
                .iter()
                .all(|c| c.is_finite() && (0.2..=1.0).contains(c)),
        "{CUTOFF_ENV}={v:?}: expected r,g,b cutoffs in 0.2-1.0 cycles/px"
    );
    Ok(Some([parts[0], parts[1], parts[2]]))
}

fn gather_in_model() -> Result<bool> {
    match std::env::var(GATHER_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Err(e) => Err(e).context(GATHER_ENV),
        Ok(v) => match v.trim() {
            "" | "0" | "off" => Ok(false),
            "1" | "on" => Ok(true),
            other => anyhow::bail!("{GATHER_ENV}={other:?} is not off or on"),
        },
    }
}

/// Whether the write's chroma filter is measured (`STREHL_CHROMA_FILTER`).
pub(super) fn chroma_measured() -> Result<bool> {
    match std::env::var(CHROMA_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(false),
        Err(e) => Err(e).context(CHROMA_ENV),
        Ok(v) => match v.trim() {
            "" | "smooth" => Ok(false),
            "measured" => Ok(true),
            other => anyhow::bail!("{CHROMA_ENV}={other:?} is not smooth or measured"),
        },
    }
}

/// The target given by [`SIGMA_ENV`], if any (then the Detail budget is not
/// consulted).
fn sigma_t() -> Result<Option<f64>> {
    match std::env::var(SIGMA_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(None),
        Err(e) => Err(e).context(SIGMA_ENV),
        Ok(v) => {
            let s: f64 = v
                .trim()
                .parse()
                .with_context(|| format!("{SIGMA_ENV}={v:?}"))?;
            ensure!(
                s.is_finite() && (0.3..=3.0).contains(&s),
                "{SIGMA_ENV} must lie in 0.3-3.0 px"
            );
            Ok(Some(s))
        }
    }
}

/// A tile the spectra use, with its two reference crops.
type UsableTile<'a> = (&'a Tile, &'a Vec<Vec<f32>>, &'a Vec<Vec<f32>>);

struct Tile {
    /// Top-left of the core, analysis-plane px.
    x0: usize,
    y0: usize,
    /// The folded frame nearest the tile's focus, and the next nearest.
    frames: [usize; 2],
    /// Those frames' planes, `SIDE x SIDE` about the core.
    reference: [Option<Vec<Vec<f32>>>; 2],
}

#[derive(Default)]
struct State {
    width: usize,
    tiles: Vec<Tile>,
    halves: Option<[Vec<Vec<f32>>; 2]>,
    /// Crops captured during the fold ([`capture`]), by frame and tile core.
    captured: Captured,
    /// The capture's gear and focus, for the stored cutoff fits
    /// ([`set_capture`]).
    source: Option<Source>,
}

/// What a stored cutoff fit is keyed on, read when the render starts.
#[derive(Clone, Debug, Default)]
struct Source {
    /// The capture folder's name.
    name: String,
    camera: Option<String>,
    lens_type3: Option<u16>,
    lens_model: Option<String>,
    f_number: Option<f32>,
    /// Median planned focus position (`manifest.json`).
    focus: Option<f64>,
}

impl Source {
    /// The gear key under system model `model`, or what is missing.
    fn gear(&self, model: &str) -> std::result::Result<cutoffs::Gear, String> {
        let mut missing = Vec::new();
        if self.camera.is_none() {
            missing.push("the camera model");
        }
        if self.lens_type3.is_none() {
            missing.push("the lens (LensType3)");
        }
        if self.f_number.is_none() {
            missing.push("the f-number");
        }
        if !missing.is_empty() {
            return Err(format!(
                "the first frame does not report {}",
                missing.join(", ")
            ));
        }
        Ok(cutoffs::Gear {
            camera: self.camera.clone().unwrap_or_default(),
            lens_type3: self.lens_type3.unwrap_or_default(),
            lens_model: self.lens_model.clone(),
            f_number: self.f_number.unwrap_or_default(),
            model: model.into(),
        })
    }
}

/// Record the capture this render restores (its folder `dir` and first
/// frame), for storing a measured cutoff and finding a stored one. Nothing
/// unless restoration is on.
pub(super) fn set_capture(dir: &Path, first: Option<&Path>) {
    let mut guard = state();
    let Some(st) = guard.as_mut() else { return };
    let id = first.map(strehl_raw::identity_cached).unwrap_or_default();
    st.source = Some(Source {
        name: dir
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default(),
        camera: id.model,
        lens_type3: id.lens_type3,
        lens_model: id.lens_model,
        f_number: id.f_number,
        focus: cutoffs::manifest_focus(dir),
    });
}

/// One crop per plane, by (frame, tile core).
type Captured = std::collections::HashMap<(usize, (usize, usize)), Vec<Vec<f32>>>;

static STATE: Mutex<Option<State>> = Mutex::new(None);

fn state() -> std::sync::MutexGuard<'static, Option<State>> {
    STATE.lock().unwrap_or_else(|e| e.into_inner())
}

/// Whether this render restores.
pub(super) fn active() -> bool {
    state().is_some()
}

/// Clears the restoration's state when the render ends, however it ends.
pub(super) struct Active;

impl Drop for Active {
    fn drop(&mut self) {
        *state() = None;
        clear_prediction();
        DEFAULTED.store(false, std::sync::atomic::Ordering::Relaxed);
    }
}

/// Switch restoration on for this render: when asked, or by default on a
/// pixel-shift stack with colour carry on (the one kind of stack whose
/// diffraction cutoff is measurable; activate the carry first). Never for a
/// lateral-CA preview. Asked for, an unsupported combination is an error; by
/// default, restoration stays off and says why.
pub(super) fn activate_if_requested(
    opts: &MergeOptions,
    temporal_active: bool,
) -> Result<Option<Active>> {
    if ca_refine::preview_active() {
        return Ok(None);
    }
    match setting()? {
        Some(true) => {}
        Some(false) => return Ok(None),
        None if crate::pixel_shift_cmd::assembly_requested() => {
            let blockers = [
                (
                    !colour_carry::active(),
                    "colour carry is off (single-shot colour cannot show the lens's cutoff)",
                ),
                (!opts.demosaic, "the output is not --demosaic"),
                (opts.region_recipe.is_some(), "region repair is on"),
                (
                    strehl_core::restore::gain_cap_from_env().is_some(),
                    "STREHL_RESTORE is on",
                ),
                (temporal_active, "temporal energy is on"),
            ];
            if let Some((_, why)) = blockers.iter().find(|(b, _)| *b) {
                eprintln!(
                    "optical restore : off for this render -- on by default for pixel-shift stacks, \
                     but {why} ({ENV}=on makes that an error)"
                );
                crate::ui_progress::optical_restore("state=off", Some(why));
                return Ok(None);
            }
            sigma_t()?;
            Detail::from_env()?;
            cutoff_override()?;
            DEFAULTED.store(true, std::sync::atomic::Ordering::Relaxed);
            *state() = Some(State::default());
            eprintln!(
                "optical restore : ON by default for pixel-shift stacks with colour carry (to be \
                 confirmed on a second subject; {ENV}=off disables it)"
            );
            return Ok(Some(Active));
        }
        None => return Ok(None),
    }
    sigma_t()?;
    Detail::from_env()?;
    cutoff_override()?;
    ensure!(opts.demosaic, "{ENV}=on needs --demosaic");
    ensure!(
        strehl_core::restore::gain_cap_from_env().is_none(),
        "{ENV}=on cannot combine with STREHL_RESTORE (the gather-kernel restoration)"
    );
    ensure!(
        opts.region_recipe.is_none(),
        "{ENV}=on cannot combine with region repair (the repair rewrites the full stack but not \
         its halves)"
    );
    *state() = Some(State::default());
    Ok(Some(Active))
}

/// Whether the render after the lateral-colour preview will restore, as
/// [`activate_if_requested`] decides it there (without its messages): for
/// predicting its reference crops in the preview. The colour carry is not
/// asked: the preview runs before it is switched on. A wrong answer costs
/// only a prediction nobody uses.
pub(super) fn would_activate(opts: &MergeOptions, temporal_active: bool) -> bool {
    match setting() {
        Ok(Some(true)) => true,
        Ok(None) => {
            crate::pixel_shift_cmd::assembly_requested()
                && opts.demosaic
                && opts.region_recipe.is_none()
                && strehl_core::restore::gain_cap_from_env().is_none()
                && !temporal_active
        }
        _ => false,
    }
}

/// Choose the spectrum tiles from the depth measurement: `depth` is the
/// finest band's focus plane per cell, `confident` whether the cell showed a
/// confident peak, on a `cw x ch` grid of `cell` plane px over a `w x h`
/// plane; `folded` marks the frames the fold will take (placed by the
/// alignment and kept by `STREHL_FRAME_PARITY`).
pub(super) fn plan_tiles(
    w: usize,
    h: usize,
    cw: usize,
    cell: usize,
    depth: &[f32],
    confident: &[bool],
    folded: &[bool],
) {
    let mut guard = state();
    let Some(st) = guard.as_mut() else { return };
    let per = TP / cell;
    let mut found: Vec<(f64, Tile)> = Vec::new();
    for ty in 1..(h / TP).saturating_sub(1) {
        for tx in 1..(w / TP).saturating_sub(1) {
            let (x0, y0) = (tx * TP, ty * TP);
            let mut d = Vec::with_capacity(per * per);
            let mut good = 0usize;
            for cy in y0 / cell..y0 / cell + per {
                for cx in x0 / cell..x0 / cell + per {
                    if confident[cy * cw + cx] {
                        good += 1;
                        d.push(depth[cy * cw + cx]);
                    }
                }
            }
            if good * 2 < per * per {
                continue;
            }
            d.sort_by(f32::total_cmp);
            let focus = d[d.len() / 2];
            // The nearest folded frame, then the next nearest.
            let nearest = |exclude: Option<usize>| {
                (0..folded.len())
                    .filter(|&k| folded[k] && Some(k) != exclude)
                    .min_by(|&a, &b| {
                        (a as f32 - focus)
                            .abs()
                            .total_cmp(&(b as f32 - focus).abs())
                    })
            };
            let Some(a) = nearest(None) else { continue };
            let Some(b) = nearest(Some(a)) else { continue };
            // Too far from focus to stand for the in-focus image.
            if (a as f32 - focus).abs() > 2.0 || (b as f32 - focus).abs() > 3.0 {
                continue;
            }
            found.push((
                good as f64 / (per * per) as f64,
                Tile {
                    x0,
                    y0,
                    frames: [a, b],
                    reference: [None, None],
                },
            ));
        }
    }
    found.sort_by(|a, b| b.0.total_cmp(&a.0));
    found.truncate(MAX_TILES);
    st.width = w;
    st.tiles = found.into_iter().map(|(_, t)| t).collect();
}

/// `STREHL_REFERENCE_CAPTURE=off`: no reference crops captured during the
/// fold; every planned tile's frames are gathered again after it (Q2).
pub(super) const CAPTURE_ENV: &str = "STREHL_REFERENCE_CAPTURE";
/// `STREHL_CAPTURE_CHECK=1`: capture, gather every planned tile again as
/// well, and fail the render unless each captured crop it uses equals the
/// gathered one bit for bit.
pub(super) const CAPTURE_CHECK_ENV: &str = "STREHL_CAPTURE_CHECK";
/// Frames captured either side of a tile's predicted focus. MEASURED on the
/// scarab stack (`experiments/a7cr-stacking-performance-2026-11-18/evidence/
/// q18-hit-rate.txt`): the preview's prediction is within 2.6 frames of the
/// plan's focus for every tile it predicts; three frames either side held
/// both reference frames for 186 of the 200 planned tiles.
const CAPTURE_RADIUS: f32 = 3.0;

/// Round-2 performance plan stage Q18. The tiles' reference frames are known
/// only after the fold (from its depth energies), and gathering them again
/// then cost about 3 s of every render (153 frames read and decoded over the
/// tiles' rows). The preview, folded first from every eighth plane, measures
/// a coarse depth map of its own: each candidate tile's focus to about a
/// frame, though not which tiles the plan will rank highest. So every
/// candidate is cropped from the frames near its predicted focus as the
/// fold gathers them (`GpuFold::add_staged_keeping_luma_cropped`, copies of
/// the gathered planes), and the plan takes what was captured; a tile whose
/// frame was not captured is gathered again as before. The crops are the
/// fold's own planes, which the gather after the fold reproduces bit for bit
/// (`STREHL_CAPTURE_CHECK`), so the photograph cannot change.
static PREDICTION: Mutex<Vec<((usize, usize), f32)>> = Mutex::new(Vec::new());

pub(super) fn capture_enabled() -> Result<bool> {
    match std::env::var(CAPTURE_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(true),
        Err(e) => Err(e).context(CAPTURE_ENV),
        Ok(v) => match v.trim() {
            "" | "on" | "1" => Ok(true),
            "off" | "0" => Ok(false),
            other => anyhow::bail!("{CAPTURE_ENV}={other:?} is not on or off"),
        },
    }
}

fn capture_check() -> bool {
    std::env::var(CAPTURE_CHECK_ENV).is_ok_and(|v| v.trim() == "1")
}

pub(super) fn clear_prediction() {
    PREDICTION.lock().unwrap_or_else(|e| e.into_inner()).clear();
}

/// Keep the preview's candidate tiles and their focus (frame units of the
/// whole stack): every tile [`plan_tiles`] could choose from this depth
/// map. Returns how many.
pub(super) fn predict(
    w: usize,
    h: usize,
    cw: usize,
    cell: usize,
    depth: &[f32],
    confident: &[bool],
) -> usize {
    let per = TP / cell;
    let mut found = Vec::new();
    for ty in 1..(h / TP).saturating_sub(1) {
        for tx in 1..(w / TP).saturating_sub(1) {
            let (x0, y0) = (tx * TP, ty * TP);
            let mut d = Vec::with_capacity(per * per);
            for cy in y0 / cell..y0 / cell + per {
                for cx in x0 / cell..x0 / cell + per {
                    if confident[cy * cw + cx] {
                        d.push(depth[cy * cw + cx]);
                    }
                }
            }
            if d.len() * 2 < per * per {
                continue;
            }
            d.sort_by(f32::total_cmp);
            found.push(((x0, y0), d[d.len() / 2]));
        }
    }
    let n = found.len();
    *PREDICTION.lock().unwrap_or_else(|e| e.into_inner()) = found;
    n
}

/// The crops' side and the tile cores frame `index` is captured for: the
/// predicted tiles whose focus is within [`CAPTURE_RADIUS`] of it. Empty
/// unless this render restores and capture is on.
pub(super) fn capture_windows(index: usize) -> Vec<(usize, usize)> {
    if !active() {
        return Vec::new();
    }
    PREDICTION
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .iter()
        .filter(|(_, focus)| (index as f32 - focus.round()).abs() <= CAPTURE_RADIUS)
        .map(|&(at, _)| at)
        .collect()
}

/// A crop's corner for the tile core at `at`, and its side.
pub(super) fn crop_window(at: (usize, usize)) -> (usize, usize, usize) {
    (at.0 - MARGIN, at.1 - MARGIN, SIDE)
}

/// Keep frame `index`'s crops for `tiles` (cores, in the order captured):
/// `data` holds them window by window, plane by plane, rows of `SIDE`.
pub(super) fn capture(
    index: usize,
    tiles: &[(usize, usize)],
    data: &[f32],
    planes: usize,
) -> Result<()> {
    let per = SIDE * SIDE;
    ensure!(
        data.len() == tiles.len() * planes * per,
        "captured crops for frame {index}: {} values for {} windows",
        data.len(),
        tiles.len()
    );
    let mut guard = state();
    let Some(st) = guard.as_mut() else {
        return Ok(());
    };
    for (k, &at) in tiles.iter().enumerate() {
        let crop: Vec<Vec<f32>> = (0..planes)
            .map(|c| data[(k * planes + c) * per..(k * planes + c + 1) * per].to_vec())
            .collect();
        st.captured.insert((index, at), crop);
    }
    Ok(())
}

/// After [`plan_tiles`]: give each planned tile the crops captured for its
/// frames, and drop the rest. Returns (reference crops taken, crops
/// captured). Under [`CAPTURE_CHECK_ENV`] nothing is taken: the crops are
/// kept for [`observe`] to compare with the gathered ones.
pub(super) fn use_captured() -> (usize, usize) {
    let mut guard = state();
    let Some(st) = guard.as_mut() else {
        return (0, 0);
    };
    let captured = st.captured.len();
    if capture_check() {
        return (0, captured);
    }
    let mut taken = 0;
    for t in &mut st.tiles {
        for slot in 0..2 {
            if let Some(crop) = st.captured.remove(&(t.frames[slot], (t.x0, t.y0))) {
                t.reference[slot] = Some(crop);
                taken += 1;
            }
        }
    }
    st.captured.clear();
    (taken, captured)
}

/// Under [`CAPTURE_CHECK_ENV`]: how many captured crops [`observe`] found
/// equal to the gathered ones (any difference fails the render there).
static CHECKED: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

pub(super) fn take_checked() -> usize {
    CHECKED.swap(0, std::sync::atomic::Ordering::Relaxed)
}

/// The frames the planned tiles take their reference planes from, each once
/// in index order, with the analysis-plane rows and columns [`observe`]
/// crops from that frame for them (one pair per tile).
pub(super) fn reference_windows() -> Vec<(usize, Vec<Window>)> {
    let guard = state();
    let Some(st) = guard.as_ref() else {
        return Vec::new();
    };
    let mut by_frame: std::collections::BTreeMap<usize, Vec<Window>> = Default::default();
    for t in &st.tiles {
        // A crop captured during the fold ([`use_captured`]) is not gathered.
        for (&k, _) in t
            .frames
            .iter()
            .zip(&t.reference)
            .filter(|(_, r)| r.is_none())
        {
            by_frame.entry(k).or_default().push(Window {
                rows: t.y0 - MARGIN..t.y0 + TP + MARGIN,
                cols: t.x0 - MARGIN..t.x0 + TP + MARGIN,
            });
        }
    }
    by_frame.into_iter().collect()
}

/// One tile's crop, analysis-plane rows and columns.
pub(super) struct Window {
    pub rows: std::ops::Range<usize>,
    pub cols: std::ops::Range<usize>,
}

/// The crops [`observe`] would keep from frame `index`'s planes, in tile
/// order (for checking a cheaper preparation against a full one).
pub(super) fn crops_of(index: usize, planes: &[Vec<f32>]) -> Vec<Vec<Vec<f32>>> {
    let guard = state();
    let Some(st) = guard.as_ref() else {
        return Vec::new();
    };
    // A slot a capture filled was not gathered: its window may not be.
    st.tiles
        .iter()
        .filter(|t| {
            t.frames
                .iter()
                .zip(&t.reference)
                .any(|(&k, r)| k == index && r.is_none())
        })
        .map(|t| crop(planes, st.width, t.x0, t.y0))
        .collect()
}

/// Keep frame `index`'s prepared planes on the tiles whose reference it is.
pub(super) fn observe(index: usize, planes: &[Vec<f32>]) {
    let mut guard = state();
    let Some(st) = guard.as_mut() else { return };
    let w = st.width;
    let check = capture_check();
    for t in st.tiles.iter_mut() {
        let Some(slot) = t.frames.iter().position(|&k| k == index) else {
            continue;
        };
        // Filled from a crop captured during the fold (`use_captured`):
        // this frame was gathered for other tiles, and only over theirs.
        if t.reference[slot].is_some() {
            continue;
        }
        let gathered = crop(planes, w, t.x0, t.y0);
        if check && let Some(captured) = st.captured.get(&(index, (t.x0, t.y0))) {
            let same = captured.len() == gathered.len()
                && captured
                    .iter()
                    .flatten()
                    .zip(gathered.iter().flatten())
                    .all(|(a, b)| a.to_bits() == b.to_bits())
                && captured
                    .iter()
                    .map(Vec::len)
                    .eq(gathered.iter().map(Vec::len));
            if same {
                CHECKED.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            } else {
                CHECK_FAILED
                    .lock()
                    .unwrap_or_else(|e| e.into_inner())
                    .get_or_insert(format!(
                        "{CAPTURE_CHECK_ENV}: frame {index}'s crop captured for the tile at {:?} \
                         differs from the gathered one",
                        (t.x0, t.y0)
                    ));
            }
        }
        t.reference[slot] = Some(gathered);
    }
}

static CHECK_FAILED: Mutex<Option<String>> = Mutex::new(None);

/// Under [`CAPTURE_CHECK_ENV`]: fail if any captured crop differed, else
/// drop the captured crops (the gathered ones are in use).
pub(super) fn capture_verdict() -> Result<()> {
    if let Some(why) = CHECK_FAILED
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .take()
    {
        anyhow::bail!(why);
    }
    if let Some(st) = state().as_mut() {
        st.captured.clear();
    }
    Ok(())
}

fn crop(planes: &[Vec<f32>], w: usize, x0: usize, y0: usize) -> Vec<Vec<f32>> {
    planes
        .iter()
        .map(|p| {
            let mut out = Vec::with_capacity(SIDE * SIDE);
            for y in y0 - MARGIN..y0 + TP + MARGIN {
                out.extend_from_slice(&p[y * w + x0 - MARGIN..y * w + x0 + TP + MARGIN]);
            }
            out
        })
        .collect()
}

/// `STREHL_RESTORE_DEVICE=off`: the restoration's convolutions on the CPU
/// (`core::convolve`) rather than the device (`strehl_gpu::convolve`, the
/// same operations in the same order; round-2 plan stage Q8).
pub(super) const RESTORE_DEVICE_ENV: &str = "STREHL_RESTORE_DEVICE";

/// `STREHL_RESTORE_CHECK=1`: every device convolution is also run on the
/// CPU and the render fails unless the two are bit-identical.
pub(super) const RESTORE_CHECK_ENV: &str = "STREHL_RESTORE_CHECK";

/// `core::convolve`, on the device when there is one (and it has not been
/// switched off), else on the CPU; the same bits either way (with
/// [`RESTORE_CHECK_ENV`], checked).
fn convolve(src: &[f32], w: usize, h: usize, k: &core::Kernel) -> Result<Vec<f32>> {
    #[cfg(feature = "gpu")]
    if !std::env::var(RESTORE_DEVICE_ENV).is_ok_and(|v| v.trim() == "off")
        && std::env::var(super::GPU_FOLD_ENV).map_or(true, |v| v.trim() != "off")
        && let Ok(out) = strehl_gpu::convolve(src, w, h, k.radius, &k.taps)
    {
        if std::env::var(RESTORE_CHECK_ENV).is_ok_and(|v| v.trim() == "1") {
            let cpu = core::convolve(src, w, h, k);
            ensure!(
                cpu.iter()
                    .zip(&out)
                    .all(|(a, b)| a.to_bits() == b.to_bits()),
                "{RESTORE_CHECK_ENV}: the device convolution differs from the CPU's"
            );
            eprintln!(
                "optical restore : device convolution checked bit for bit ({RESTORE_CHECK_ENV})"
            );
        }
        return Ok(out);
    }
    Ok(core::convolve(src, w, h, k))
}

/// Keep the two finished half-stacks (odd and even frames).
pub(super) fn stash_halves(a: Vec<Vec<f32>>, b: Vec<Vec<f32>>) {
    if let Some(st) = state().as_mut() {
        st.halves = Some([a, b]);
    }
}

/// How the write normalises a black-subtracted plane value: per channel
/// white balance, exposure gain and range.
#[derive(Clone, Copy)]
pub(super) struct Norm {
    pub gains: [f32; 3],
    pub exposure: f32,
    pub range: f32,
    /// The raw container maximum, black-subtracted DN: where a sample is
    /// pinned (16383 - black on the A7CR; not the white level, which bounds
    /// the noise model's calibrated range).
    pub pin: f32,
}

impl Norm {
    fn scale(&self, c: usize) -> f32 {
        self.gains[c] * self.exposure / self.range
    }
}

fn channel_of(p: usize, planes: usize) -> usize {
    if planes == BAND_PLANES {
        [0, 1, 1, 2][p]
    } else {
        colour_carry::plane_channel(p)
    }
}

/// A crop (`SIDE x SIDE` plane px, every plane) developed to linear RGB as
/// the output is, its `TILE x TILE` core returned per channel.
fn tile_rgb(crop: &[Vec<f32>], norm: Norm) -> [Vec<f32>; 3] {
    let n = crop.len();
    let planes: Vec<Vec<f32>> = crop
        .iter()
        .enumerate()
        .map(|(p, v)| {
            let s = norm.scale(channel_of(p, n));
            v.iter().map(|x| x.max(0.0) * s).collect()
        })
        .collect();
    let full = 2 * SIDE;
    let mut rgb = [
        vec![0f32; full * full],
        vec![0f32; full * full],
        vec![0f32; full * full],
    ];
    if n == BAND_PLANES {
        let mut mosaic = vec![0f32; full * full];
        for py in 0..SIDE {
            for px in 0..SIDE {
                let i = py * SIDE + px;
                for (p, (dx, dy)) in BAND_PLANE_OFFSETS.iter().enumerate() {
                    mosaic[(2 * py + dy) * full + 2 * px + dx] = planes[p][i];
                }
            }
        }
        let m = strehl_core::demosaic::Mosaic {
            data: &mosaic,
            width: full,
            height: full,
        };
        let [r, g, b] = &mut rgb;
        for (y, ((rr, gg), bb)) in r
            .chunks_mut(full)
            .zip(g.chunks_mut(full))
            .zip(b.chunks_mut(full))
            .enumerate()
        {
            strehl_core::demosaic::demosaic_row_planar(&m, y, rr, gg, bb);
        }
    } else {
        // As carried: the restoration runs before the chroma smoothing.
        let inter = colour_carry::interleave(&planes, SIDE, SIDE);
        for (i, px) in inter.as_chunks::<3>().0.iter().enumerate() {
            for (c, v) in px.iter().enumerate() {
                rgb[c][i] = *v;
            }
        }
    }
    let o = 2 * MARGIN;
    rgb.map(|plane| {
        let mut core_px = Vec::with_capacity(core::TILE * core::TILE);
        for y in o..o + core::TILE {
            core_px.extend_from_slice(&plane[y * full + o..y * full + o + core::TILE]);
        }
        core_px
    })
}

fn max_filter(v: &[f32], w: usize, h: usize, r: usize) -> Vec<f32> {
    let rows: Vec<f32> = (0..h)
        .into_par_iter()
        .flat_map_iter(|y| {
            let row = &v[y * w..(y + 1) * w];
            (0..w).map(move |x| {
                row[x.saturating_sub(r)..(x + r + 1).min(w)]
                    .iter()
                    .copied()
                    .fold(f32::MIN, f32::max)
            })
        })
        .collect();
    let mut out = vec![0f32; w * h];
    out.par_chunks_mut(w).enumerate().for_each(|(y, o)| {
        for (x, o) in o.iter_mut().enumerate() {
            *o = (y.saturating_sub(r)..(y + r + 1).min(h))
                .map(|yy| rows[yy * w + x])
                .fold(f32::MIN, f32::max);
        }
    });
    out
}

/// The experiment record of each tile (`STREHL_OPTICAL_RESTORE_DUMP`): its
/// place, reference frames, whether the clipping test kept it out, the
/// brightest sample of the merged planes and of each reference crop over the
/// black-to-white range (per plane), and its own radial spectra per channel
/// (halves and reference, signal and noise). Nothing here reaches the image.
fn tile_records(
    tiles: &[(UsableTile<'_>, bool)],
    ha: &[Vec<f32>],
    hb: &[Vec<f32>],
    merged: &[Vec<f32>],
    gw: usize,
    norm: Norm,
) -> Vec<serde_json::Value> {
    let binner = core::SpectrumSum::new();
    let peak = |planes: &[Vec<f32>]| -> Vec<f32> {
        planes
            .iter()
            .map(|p| p.iter().copied().fold(f32::MIN, f32::max) / norm.range)
            .collect()
    };
    let over = |planes: &[Vec<f32>], f: f32| -> usize {
        planes
            .iter()
            .map(|p| p.iter().filter(|v| **v > f * norm.range).count())
            .sum()
    };
    tiles
        .par_iter()
        .map(|((t, r0, r1), is_hot)| {
            let a = tile_rgb(&crop(ha, gw, t.x0, t.y0), norm);
            let b = tile_rgb(&crop(hb, gw, t.x0, t.y0), norm);
            let ra = tile_rgb(r0, norm);
            let rb = tile_rgb(r1, norm);
            let channels: Vec<serde_json::Value> = (0..3)
                .map(|c| {
                    let own = binner.radial_terms(&binner.pair_terms(&a[c], &b[c]));
                    let reference = binner.radial_terms(&binner.pair_terms(&ra[c], &rb[c]));
                    serde_json::json!({
                        "out_signal": own.signal, "out_noise": own.noise,
                        "ref_signal": reference.signal, "ref_noise": reference.noise,
                    })
                })
                .collect();
            let m = crop(merged, gw, t.x0, t.y0);
            serde_json::json!({
                "x0": t.x0, "y0": t.y0, "frames": t.frames, "hot": is_hot,
                "merged_peak": peak(&m), "ref_peak": [peak(r0), peak(r1)],
                "ref_over_half": over(r0, 0.5) + over(r1, 0.5),
                "ref_over_clip": over(r0, CLIP_FRACTION) + over(r1, CLIP_FRACTION),
                "channels": channels,
            })
        })
        .collect()
}

/// Restore `rgb` (interleaved linear camera RGB, `mw x mh`, normalised by
/// `norm`) in place. `merged` is the full stack's planes (black-subtracted
/// DN) on the `mw / 2 x mh / 2` quad grid, for the clipping guard. Returns
/// whether the measured chroma filter (`STREHL_CHROMA_FILTER=measured`) was
/// applied, in which case the write must not smooth the chroma again.
pub(super) fn restore(
    rgb: &mut [f32],
    mw: usize,
    mh: usize,
    merged: &[Vec<f32>],
    norm: Norm,
) -> Result<bool> {
    let started = Instant::now();
    // `STREHL_FOLD_TRACE=1`: the restoration's phases, timed.
    let trace = std::env::var(super::fold_trace::ENV).is_ok_and(|v| v.trim() == "1");
    let mut last = Instant::now();
    let mut phase = |name: &str| {
        if trace {
            eprintln!(
                "restore trace   : {name} {:.0} ms",
                last.elapsed().as_secs_f64() * 1e3
            );
        }
        last = Instant::now();
    };
    let given_sigma = sigma_t()?;
    let detail = Detail::from_env()?;
    let gather =
        gather_in_model()?.then(|| core::gather_table(strehl_core::align::Resampler::CatmullRom));
    let chroma = chroma_measured()? && merged.len() == colour_carry::PLANES;
    let st = state()
        .take()
        .context("optical restoration has no measurement")?;
    let [ha, hb] = st
        .halves
        .context("optical restoration: the fold kept no half-stacks")?;
    let (gw, gh) = (mw / 2, mh / 2);
    ensure!(
        st.width == gw && merged.iter().all(|p| p.len() == gw * gh),
        "optical restoration: the measured grid does not match the output"
    );
    let clip = CLIP_FRACTION * norm.range;
    let clipped = |planes: &[Vec<f32>], x0: usize, y0: usize| {
        planes.iter().any(|p| {
            (y0 - MARGIN..y0 + TP + MARGIN).any(|y| {
                p[y * gw + x0 - MARGIN..y * gw + x0 + TP + MARGIN]
                    .iter()
                    .any(|v| *v > clip)
            })
        })
    };
    let mut out: [core::SpectrumSum; 3] = std::array::from_fn(|_| core::SpectrumSum::new());
    let mut refs: [core::SpectrumSum; 3] = std::array::from_fn(|_| core::SpectrumSum::new());
    // Red minus green and blue minus green, for the measured chroma filter.
    let mut diffs: [core::SpectrumSum; 2] = std::array::from_fn(|_| core::SpectrumSum::new());
    // The tiles used, decided in order as before; then each tile's spectra
    // transformed in parallel, a batch at a time (about 8 MB of terms per
    // tile), and added in tile order: every sum receives the same values in
    // the same order as adding tile by tile.
    let (mut no_ref, mut hot) = (0usize, 0usize);
    let mut usable: Vec<UsableTile<'_>> = Vec::new();
    // Experiment record (`STREHL_OPTICAL_RESTORE_DUMP`): every tile with its
    // reference frames, near clipping or not, measured on its own.
    let dumping = std::env::var_os(DUMP_ENV).is_some();
    let mut per_tile: Vec<(UsableTile<'_>, bool)> = Vec::new();
    for t in &st.tiles {
        let [Some(r0), Some(r1)] = &t.reference else {
            no_ref += 1;
            continue;
        };
        let is_hot = clipped(merged, t.x0, t.y0);
        if dumping {
            per_tile.push(((t, r0, r1), is_hot));
        }
        if is_hot {
            hot += 1;
            continue;
        }
        usable.push((t, r0, r1));
    }
    let used = usable.len();
    let tile_dump: Vec<serde_json::Value> = if dumping {
        tile_records(&per_tile, &ha, &hb, merged, gw, norm)
    } else {
        Vec::new()
    };
    const BATCH: usize = 32;
    for batch in usable.chunks(BATCH) {
        let terms: Vec<_> = batch
            .par_iter()
            .map(|(t, r0, r1)| {
                let a = tile_rgb(&crop(&ha, gw, t.x0, t.y0), norm);
                let b = tile_rgb(&crop(&hb, gw, t.x0, t.y0), norm);
                let ra = tile_rgb(r0, norm);
                let rb = tile_rgb(r1, norm);
                let own: Vec<_> = (0..3).map(|c| out[c].pair_terms(&a[c], &b[c])).collect();
                let reference: Vec<_> =
                    (0..3).map(|c| refs[c].pair_terms(&ra[c], &rb[c])).collect();
                let diff = |x: &[f32], g: &[f32]| -> Vec<f32> {
                    x.iter().zip(g).map(|(x, g)| x - g).collect()
                };
                let chroma_terms: Vec<_> = if chroma {
                    [0usize, 2]
                        .into_iter()
                        .enumerate()
                        .map(|(k, c)| diffs[k].pair_terms(&diff(&a[c], &a[1]), &diff(&b[c], &b[1])))
                        .collect()
                } else {
                    Vec::new()
                };
                (own, reference, chroma_terms)
            })
            .collect();
        for (own, reference, chroma_terms) in &terms {
            for c in 0..3 {
                out[c].add_terms(&own[c]);
                refs[c].add_terms(&reference[c]);
            }
            for (k, t) in chroma_terms.iter().enumerate() {
                diffs[k].add_terms(t);
            }
        }
    }
    phase("tile spectra");
    ensure!(
        used >= MIN_TILES,
        "optical restoration: {used} usable in-focus tiles ({} planned, {no_ref} missing a reference frame, \
         {hot} near clipping); at least {MIN_TILES} are needed to measure the system",
        st.tiles.len()
    );
    let centres = core::centres();
    let at = |v: &[f64], f: f64| v[((f / core::BIN_WIDTH) as usize).min(v.len() - 1)];
    let mut kernels = Vec::new();
    let mut lines = Vec::new();
    let mut dump = Vec::new();
    let spectra: Vec<(core::Spectrum, core::Spectrum)> = (0..3)
        .map(|c| (out[c].radial(), refs[c].radial()))
        .collect();
    // The reference frames' signal as the cutoff fit sees it: with the
    // gather in the model, its power divided out first.
    let ref_signal: Vec<Vec<f64>> = spectra
        .iter()
        .map(|(_, sr)| match &gather {
            None => sr.signal.clone(),
            Some(g) => sr
                .signal
                .iter()
                .zip(&centres)
                .map(|(s, f)| s / core::gather_annulus_power(g, *f).max(1e-6))
                .collect(),
        })
        .collect();
    let fits: Vec<(f64, f64, Option<f64>)> = ref_signal
        .iter()
        .map(|signal| {
            let (fc, _, rms) = core::fit_cutoff(&centres, signal);
            (fc, rms, core::cube_root_cutoff(&centres, signal, fc))
        })
        .collect();
    for (c, (so, sr)) in spectra.iter().enumerate() {
        dump.push(serde_json::json!({
            "out_signal": so.signal, "out_noise": so.noise,
            "ref_signal": sr.signal, "ref_noise": sr.noise, "count": so.count,
            "fitted_cutoff": fits[c].0, "fit_rms": fits[c].1, "cube_root_cutoff": fits[c].2,
        }));
    }
    // Experiment hook (`STREHL_OPTICAL_RESTORE_DUMP`, declared in
    // check-defaults.py): the measured spectra as JSON, written before any
    // refusal so a refused stack can still be inspected.
    if let Ok(path) = std::env::var(DUMP_ENV) {
        std::fs::write(
            &path,
            serde_json::to_string(&serde_json::json!({
                "centres": centres, "tiles": used, "channels": dump, "tile_records": tile_dump,
            }))?,
        )?;
    }
    let (joint, joint_rms) =
        core::fit_cutoff_joint(&centres, [&ref_signal[0], &ref_signal[1], &ref_signal[2]]);
    let Choice {
        cutoffs,
        source,
        event,
    } = choose_cutoffs(
        Fitted {
            green: joint,
            residual: joint_rms,
            per_channel: [fits[0].0, fits[1].0, fits[2].0],
            tiles: used,
        },
        cutoff_override()?,
        st.source.as_ref(),
        cutoffs::model_name(gather.is_some()),
        &cutoffs::store_path(),
    )?;
    let mut models = Vec::with_capacity(3);
    // Each channel's model: independent, so fitted side by side.
    let fitted_models: Vec<Result<(Vec<f64>, core::ChannelModel)>> = (0..3)
        .into_par_iter()
        .map(|c| {
            let (so, sr) = &spectra[c];
            let m = core::blend_transfer(&centres, so, sr);
            let noise: Vec<f64> = so.noise.iter().map(|n| n / 2.0).collect();
            let model = core::ChannelModel::new_with_gather(
                &centres,
                &so.signal,
                noise,
                cutoffs[c],
                m.clone(),
                gather.clone(),
            )
            .with_context(|| {
                format!("optical restoration: channel {c}'s signal spectrum could not be modelled")
            })?;
            Ok((m, model))
        })
        .collect();
    let fitted_models: Vec<(Vec<f64>, core::ChannelModel)> =
        fitted_models.into_iter().collect::<Result<_>>()?;
    // Plan D2: one target for the three channels, chosen on green against
    // the Detail budget. Green, because the write's chroma smoothing hands
    // red and blue green's finest bands, so green's is the noise the
    // picture's fine grain carries.
    let (sigma, strength) = match (given_sigma, detail) {
        (Some(s), _) => (s, None),
        (None, Detail::Natural) => (SIGMA_T, None),
        (None, Detail::Budget { budget, .. }) => {
            let s = core::choose_sigma(&fitted_models[1].1, 128, budget, MAX_GAIN);
            (s.sigma, Some(s))
        }
    };
    // Each channel's gain grid and kernel, side by side.
    let designs: Vec<(Vec<f64>, core::ChannelModel, core::Kernel)> = fitted_models
        .into_par_iter()
        .map(|(m, model)| {
            let g = core::gain_grid(&model, 128, sigma, MAX_GAIN);
            // Judged where the filter does its work: below the taper.
            let k = core::kernel(&g, 128, MAX_RADIUS, TOLERANCE, (0.25, 0.40));
            (m, model, k)
        })
        .collect();
    // The strength's account, per channel: designed and delivered noise
    // rise in the budget band, and the signal's amplitude gain by band.
    let mut strength_lines = Vec::new();
    for (c, (_, model, k)) in designs.iter().enumerate() {
        let designed = core::gain_grid(model, 128, sigma, MAX_GAIN);
        let delivered = core::kernel_response(k, 128);
        strength_lines.push(format!(
            "{}: noise power in {:.2}-{:.2} cycles/px x{:.2} designed, x{:.2} delivered; signal \
             amplitude at 0.1-0.2/0.2-0.3/0.3-0.4/0.4-0.5 cycles/px {}",
            ["R", "G", "B"][c],
            core::NOISE_BAND.0,
            core::NOISE_BAND.1,
            core::noise_rise(model, &designed, 128, core::NOISE_BAND),
            core::noise_rise(model, &delivered, 128, core::NOISE_BAND),
            [(0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5)]
                .iter()
                .map(|&b| format!("x{:.2}", core::signal_gain(model, &delivered, 128, b)))
                .collect::<Vec<_>>()
                .join("/")
        ));
    }
    for (c, design) in designs.into_iter().enumerate() {
        let fc = cutoffs[c];
        let (fitted, fit_rms, cube) = fits[c];
        let (m, model, k) = design;
        let mtf = |f: f64| core::system_mtf(&model, f, 0.0);
        let gain = |f: f64| core::gain_at(&model, f, 0.0, sigma, MAX_GAIN);
        lines.push(format!(
            "{}: cutoff {fc:.3} cycles/px (fitted {fitted:.3}, cube-root {}, fit rms {fit_rms:.4}); blend transfer at \
             0.2/0.3/0.4 {:.2}/{:.2}/{:.2}; system -> restored (target) MTF at 0.2/0.3/0.4 {}; \
             kernel radius {} delivers {:.3} of the designed gain in 0.25-0.40 cycles/px (worst {:.3} \
             of the peak gain there, {:.3} anywhere)",
            ["R", "G", "B"][c],
            cube.map_or("-".into(), |v| format!("{v:.3}")),
            at(&m, 0.2),
            at(&m, 0.3),
            at(&m, 0.4),
            [0.2, 0.3, 0.4]
                .iter()
                .map(|&f| format!(
                    "{:.2}->{:.2} ({:.2})",
                    mtf(f),
                    gain(f) * mtf(f),
                    core::target(sigma, f)
                ))
                .collect::<Vec<_>>()
                .join(" "),
            k.radius,
            k.delivered,
            k.band_error,
            k.max_error
        ));
        kernels.push(k);
        models.push(model);
    }
    // Experiment hook (`STREHL_OPTICAL_RESTORE_DUMP`, declared in
    // check-defaults.py): the measured spectra as JSON.
    if let Ok(path) = std::env::var(DUMP_ENV) {
        std::fs::write(
            &path,
            serde_json::to_string(&serde_json::json!({
                "centres": centres, "tiles": used, "channels": dump, "tile_records": tile_dump,
            }))?,
        )?;
    }
    phase("fits and kernel design");
    // Highlight guard: keep the unrestored value within about ten photosites
    // of a sample at the raw pin, with a smooth hand-over (quad grid). Plan
    // D3: pinned, not merely bright (`PIN_FRACTION`).
    let pinned = PIN_FRACTION * norm.pin;
    let hotq: Vec<f32> = (0..gw * gh)
        .into_par_iter()
        .map(|i| f32::from(u8::from(merged.iter().any(|p| p[i] >= pinned))))
        .collect();
    let pinned_share = hotq.iter().filter(|v| **v > 0.0).count() as f64 / hotq.len() as f64;
    let near = max_filter(&hotq, gw, gh, 5);
    let soft = axial_colour::blur(&near, gw, gh, 2.0);
    let keep: Vec<f32> = soft.iter().map(|v| 1.0 - v.clamp(0.0, 1.0)).collect();
    let guarded = keep.iter().filter(|v| **v < 0.999).count() as f64 / keep.len() as f64;
    phase("highlight guard");
    for c in 0..3 {
        let off = ROOT_OFFSET_DN * norm.scale(c);
        let x: Vec<f32> = rgb.par_chunks_exact(3).map(|p| p[c]).collect();
        let root: Vec<f32> = x.par_iter().map(|v| (v.max(0.0) + off).sqrt()).collect();
        let y = convolve(&root, mw, mh, &kernels[c])?;
        rgb.par_chunks_exact_mut(3)
            .zip(y.par_iter().zip(x.par_iter()))
            .enumerate()
            .for_each(|(i, (p, (y, x)))| {
                let restored = y.max(0.0).powi(2) - off;
                let k = keep[(i / mw / 2) * gw + (i % mw) / 2];
                p[c] = x + k * (restored - x);
            });
        phase("a channel's restoration");
    }
    // The measured chroma filter, on the restored image: per colour
    // difference, the Wiener filter of the difference the restored halves
    // share against their noise. Where the difference carries detail above
    // noise, red and blue keep their own; where it does not, they take
    // green's (the fixed smoothing's behaviour at every frequency).
    let mut chroma_line = None;
    if chroma {
        let diff_spectra = [diffs[0].radial(), diffs[1].radial()];
        let mut filters = Vec::with_capacity(2);
        for (k, c) in [0usize, 2].into_iter().enumerate() {
            let sd = &diff_spectra[k];
            let raw: Vec<f64> = centres
                .iter()
                .enumerate()
                .map(|(i, &f)| {
                    let gc = core::gain_at(&models[c], f, 0.0, sigma, MAX_GAIN);
                    let gg = core::gain_at(&models[1], f, 0.0, sigma, MAX_GAIN);
                    let (sc, sg) = (spectra[c].0.signal[i], spectra[1].0.signal[i]);
                    let (nc, ng) = (spectra[c].0.noise[i], spectra[1].0.noise[i]);
                    // The channels' shared signal, from the difference's.
                    let scg = 0.5 * (sc + sg - sd.signal[i]);
                    let s = (gc * gc * sc + gg * gg * sg - 2.0 * gc * gg * scg).max(0.0);
                    let n = 0.5 * (gc * gc * nc.max(0.0) + gg * gg * ng.max(0.0));
                    if s + n > 0.0 { s / (s + n) } else { 0.0 }
                })
                .collect();
            // A three-bin running mean: per-bin estimates are noisy.
            let smooth: Vec<f64> = (0..raw.len())
                .map(|i| {
                    let lo = i.saturating_sub(1);
                    let hi = (i + 2).min(raw.len());
                    raw[lo..hi].iter().sum::<f64>() / (hi - lo) as f64
                })
                .collect();
            filters.push(smooth);
        }
        let mut parts = Vec::new();
        for (k, c) in [0usize, 2].into_iter().enumerate() {
            let grid = core::radial_grid(&filters[k], 128);
            let kern = core::kernel(&grid, 128, MAX_RADIUS, TOLERANCE, (0.05, 0.45));
            let d: Vec<f32> = rgb.par_chunks_exact(3).map(|p| p[c] - p[1]).collect();
            let fd = convolve(&d, mw, mh, &kern)?;
            rgb.par_chunks_exact_mut(3)
                .zip(fd.par_iter())
                .for_each(|(p, d)| p[c] = p[1] + d);
            let at_f =
                |f: f64| filters[k][((f / core::BIN_WIDTH) as usize).min(filters[k].len() - 1)];
            parts.push(format!(
                "{} minus green {:.2}/{:.2}/{:.2}/{:.2} (kernel radius {}, delivers {:.3})",
                ["red", "", "blue"][c],
                at_f(0.1),
                at_f(0.2),
                at_f(0.3),
                at_f(0.4),
                kern.radius,
                kern.delivered
            ));
        }
        chroma_line = Some(format!(
            "chroma filter   : MEASURED ({CHROMA_ENV}=measured) in place of the 1 px smoothing -- \
             each colour difference kept where the restored halves share it above their noise; at \
             0.1/0.2/0.3/0.4 cycles/px {}",
            parts.join(", ")
        ));
    }
    let detail_line = match (given_sigma, detail, strength) {
        (Some(_), _, _) => format!(
            "target GIVEN by {SIGMA_ENV}; the Detail budget ({DETAIL_ENV}) is not consulted"
        ),
        (None, Detail::Natural, _) => {
            format!("NATURAL: the shipped target {SIGMA_T:.2} px, no noise budget")
        }
        (None, Detail::Budget { name, budget }, Some(s)) => format!(
            "{} (budget: restored noise power in {:.2}-{:.2} cycles/px at most {budget:.2} x the \
             unrestored, green, on the half-stacks' noise): target {:.2} px chosen of {:.2}-{:.2} \
             in {:.2} px steps, designed rise x{:.2}{}",
            name.to_uppercase(),
            core::NOISE_BAND.0,
            core::NOISE_BAND.1,
            s.sigma,
            core::SIGMA_WIDEST,
            core::SIGMA_SHARPEST,
            core::SIGMA_STEP,
            s.rise,
            if s.within {
                ""
            } else {
                " -- even the widest target exceeds the budget, so it is used"
            }
        ),
        (None, Detail::Budget { .. }, None) => unreachable!("a budget always chooses"),
    };
    eprintln!(
        "optical restore : ON ({}) -- target Gaussian sigma {sigma:.2} px, Wiener against the \
         measured noise, never below the system's response, gain cap {MAX_GAIN}, square-root \
         domain{}",
        if defaulted() {
            "default for pixel-shift stacks".to_string()
        } else {
            format!("{ENV}=on")
        },
        if gather.is_some() {
            format!(
                "; the gather's Catmull-Rom kernel IN THE MODEL ({GATHER_ENV}=on: phase-averaged \
                 response per axis, divided out of the reference before the cutoff fit)"
            )
        } else {
            String::new()
        }
    );
    eprintln!(
        "                  {used} in-focus tiles of {} px ({} planned; {no_ref} missing a reference \
         frame, {hot} near clipping): halves' signal and noise, reference = the two frames at \
         each tile's focus",
        core::TILE,
        st.tiles.len()
    );
    for l in &lines {
        eprintln!("                  {l}");
    }
    eprintln!("detail          : {detail_line}");
    for l in &strength_lines {
        eprintln!("                  {l}");
    }
    eprintln!(
        "                  cutoffs R/G/B {:.3}/{:.3}/{:.3}: {source}; highlight guard covers {:.2}% of \
         the frame (around the {:.4}% of sites with a merged sample at or above {PIN_FRACTION} of \
         the raw pin, {:.0} DN over black); {:.1} s",
        cutoffs[0],
        cutoffs[1],
        cutoffs[2],
        100.0 * guarded,
        100.0 * pinned_share,
        norm.pin,
        started.elapsed().as_secs_f64()
    );
    if let Some(line) = &chroma_line {
        eprintln!("{line}");
    }
    crate::ui_progress::optical_restore(&event, None);
    Ok(chroma_line.is_some())
}

/// This stack's one-aperture fit, as [`choose_cutoffs`] weighs it.
struct Fitted {
    green: f64,
    residual: f64,
    /// Each channel's own fit ([`core::fit_cutoff`]), for the log.
    per_channel: [f64; 3],
    tiles: usize,
}

/// The cutoffs a render restores with, the log's account of them and the
/// desktop's report (`event=optical-restore`).
struct Choice {
    cutoffs: [f64; 3],
    source: String,
    event: String,
}

/// The cutoffs R, G, B to restore with: given by [`CUTOFF_ENV`]; else this
/// stack's joint fit below [`JOINT_CEILING`], which is kept in the store at
/// `store`; else the nearest stored fit for the same gear
/// ([`cutoffs::nearest`]); else an error saying why none could stand in.
fn choose_cutoffs(
    fitted: Fitted,
    given: Option<[f64; 3]>,
    source: Option<&Source>,
    model: &str,
    store: &Path,
) -> Result<Choice> {
    let Fitted {
        green: joint,
        residual: joint_rms,
        per_channel,
        tiles,
    } = fitted;
    let from_green = |g: f64| -> [f64; 3] {
        std::array::from_fn(|c| g * core::WAVELENGTH_UM[1] / core::WAVELENGTH_UM[c])
    };
    if let Some(given) = given {
        return Ok(Choice {
            cutoffs: given,
            source: format!(
                "GIVEN by {CUTOFF_ENV}, not measured on this stack (its own joint fit: green {joint:.3})"
            ),
            event: format!("state=given cutoff={:.3}", given[1]),
        });
    }
    if joint < JOINT_CEILING {
        let stored = store_fit(source, model, joint, joint_rms, tiles, store);
        return Ok(Choice {
            cutoffs: from_green(joint),
            source: format!(
                "one aperture fitted to all three reference channels (relative residual \
                 {joint_rms:.4}; diffraction ratios from nominal wavelengths 600/535/465 nm); {stored}"
            ),
            event: format!("state=measured cutoff={joint:.3}"),
        });
    }
    let unmeasurable = format!(
        "the diffraction cutoff is not measurable on this stack (the one-aperture fit of the \
         reference frames ran to its ceiling: green {joint:.3} cycles/px; per channel \
         {:.3}/{:.3}/{:.3})",
        per_channel[0], per_channel[1], per_channel[2]
    );
    match stand_in(source, model, store) {
        Ok((fit, focus)) => Ok(Choice {
            cutoffs: from_green(fit.green),
            source: format!(
                "STORED fit of {} (focus {:.0}, this stack {focus:.0}; {} tiles, relative \
                 residual {:.4}; {}), because {unmeasurable}",
                fit.capture, fit.focus, fit.tiles, fit.residual, fit.origin
            ),
            event: format!(
                "state=stored cutoff={:.3} from={} from_focus={:.0} focus={focus:.0} fitted={joint:.3}",
                fit.green, fit.capture, fit.focus
            ),
        }),
        Err(why) => anyhow::bail!(
            "optical restoration: {unmeasurable}, and no stored fit can stand in: {why}. A \
             single-shot frame cannot sample the lens's roll-off above its 0.5 cycles/px \
             Nyquist, and its demosaic structure reads as signal there. Measure the cutoff on \
             a four-shot run of the same setup (STREHL_CARRY_RGB=on) and pass it as \
             {CUTOFF_ENV}=r,g,b"
        ),
    }
}

/// Keep a measured joint fit in the store ([`cutoffs`]), and say so for the
/// log. A fit that cannot be keyed or written is not kept; the render goes on.
fn store_fit(
    source: Option<&Source>,
    model: &str,
    green: f64,
    residual: f64,
    tiles: usize,
    path: &Path,
) -> String {
    let Some(source) = source else {
        return "not stored (no capture recorded)".into();
    };
    let gear = match source.gear(model) {
        Ok(g) => g,
        Err(why) => return format!("not stored ({why})"),
    };
    let Some(focus) = source.focus else {
        return "not stored (the capture manifest records no focus positions)".into();
    };
    let fit = cutoffs::Fit {
        gear,
        focus,
        green,
        residual,
        tiles,
        capture: source.name.clone(),
        origin: "measured".into(),
        build: crate::VERSION.into(),
        recorded_unix_ms: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_millis() as u64),
    };
    match cutoffs::record(path, fit) {
        Ok(()) => format!(
            "stored for stacks that cannot measure it ({})",
            path.display()
        ),
        Err(e) => format!("NOT stored: {e:#}"),
    }
}

/// The stored fit to stand in for this stack's cutoff, with this stack's
/// focus position, or why there is none.
fn stand_in(
    source: Option<&Source>,
    model: &str,
    path: &Path,
) -> std::result::Result<(cutoffs::Fit, f64), String> {
    let source = source.ok_or("no capture recorded for this render")?;
    let gear = source.gear(model)?;
    let focus = source
        .focus
        .ok_or("the capture manifest records no focus positions")?;
    let stored = cutoffs::load(path).unwrap_or_else(|e| {
        eprintln!("optical restore : the stored cutoff fits are unreadable ({e:#}); using the built-in ones only");
        Vec::new()
    });
    let all = cutoffs::candidates(stored);
    cutoffs::nearest(&all, &gear, focus, &source.name)
        .map(|f| (f.clone(), focus))
        .ok_or_else(|| {
            format!(
                "none of {} stored fits is for {} / lens {} / f/{:.1} ({}) within {:.0} focus units of {focus:.0}",
                all.len(),
                gear.camera,
                gear.lens_type3,
                gear.f_number,
                gear.model,
                cutoffs::MAX_FOCUS_DISTANCE
            )
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn weevil() -> Source {
        Source {
            name: "stack-weevil".into(),
            camera: Some("ILCE-7CR".into()),
            lens_type3: Some(33094),
            lens_model: None,
            f_number: Some(5.6),
            focus: Some(25_175.0),
        }
    }

    fn store(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "strehl-optical-choice-{name}-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&dir);
        dir.join(cutoffs::STORE_FILE)
    }

    /// `--detail`'s spellings: the three names, a budget number in range,
    /// and refusals for anything else.
    #[test]
    fn detail_names_and_budgets_parse() {
        assert_eq!(Detail::parse("natural").unwrap(), Detail::Natural);
        assert_eq!(
            Detail::parse("safe").unwrap(),
            Detail::Budget {
                name: "safe",
                budget: SAFE_BUDGET
            }
        );
        assert_eq!(
            Detail::parse("crisp").unwrap(),
            Detail::Budget {
                name: "crisp",
                budget: CRISP_BUDGET
            }
        );
        assert_eq!(
            Detail::parse("2.5").unwrap(),
            Detail::Budget {
                name: "given",
                budget: 2.5
            }
        );
        for bad in ["sharp", "0.9", "7", "NaN"] {
            assert!(Detail::parse(bad).is_err(), "{bad}");
        }
    }

    /// The joint fit over planted spectra: three channels with no roll-off.
    fn fitted_on(signals: [Vec<f64>; 3]) -> Fitted {
        let c = core::centres();
        let (green, residual) = core::fit_cutoff_joint(&c, [&signals[0], &signals[1], &signals[2]]);
        Fitted {
            green,
            residual,
            per_channel: [green; 3],
            tiles: 50,
        }
    }

    /// A spectrum with no roll-off runs the fit to its ceiling; the nearest
    /// stored fit for the same gear stands in, and the log and the desktop's
    /// report both name it.
    #[test]
    fn a_spectrum_without_roll_off_takes_the_nearest_stored_fit() {
        let c = core::centres();
        let flat: Vec<f64> = c.iter().map(|f| f.powf(-2.0)).collect();
        let fitted = fitted_on([flat.clone(), flat.clone(), flat]);
        assert!(fitted.green >= JOINT_CEILING, "{}", fitted.green);
        let path = store("fallback");
        let choice = choose_cutoffs(fitted, None, Some(&weevil()), "diffraction", &path).unwrap();
        assert!(
            (choice.cutoffs[1] - 0.776).abs() < 1e-12,
            "{:?}",
            choice.cutoffs
        );
        assert!(
            (choice.cutoffs[0] - 0.776 * 535.0 / 600.0).abs() < 1e-12,
            "the channels keep one aperture"
        );
        assert!(
            choice
                .source
                .starts_with("STORED fit of stack-1795433406862-8651")
        );
        assert!(choice.source.contains("ran to its ceiling"));
        assert_eq!(
            choice.event,
            "state=stored cutoff=0.776 from=stack-1795433406862-8651 from_focus=31239 \
             focus=25175 fitted=0.900"
        );
        // Nothing was stored for a fit that failed.
        assert!(cutoffs::load(&path).unwrap().is_empty());
    }

    /// A measured fit is used and stored; a later stack nearer to it in
    /// focus takes it over the seeds. Unknown gear has no stand-in, and the
    /// error says so.
    #[test]
    fn a_measured_fit_is_stored_and_stands_in_later() {
        let c = core::centres();
        let planted: [Vec<f64>; 3] = std::array::from_fn(|ch| {
            let fc = 0.70 * core::WAVELENGTH_UM[1] / core::WAVELENGTH_UM[ch];
            c.iter()
                .map(|f| f.powf(-1.5) * (core::mtf_diffraction(f / fc) * core::sinc(*f)).powi(2))
                .collect()
        });
        let path = store("measured");
        let mut first = weevil();
        first.name = "stack-measured".into();
        first.focus = Some(24_000.0);
        let choice =
            choose_cutoffs(fitted_on(planted), None, Some(&first), "diffraction", &path).unwrap();
        assert!(
            (choice.cutoffs[1] - 0.70).abs() < 0.0081,
            "{:?}",
            choice.cutoffs
        );
        assert!(choice.event.starts_with("state=measured cutoff="));
        assert!(
            choice
                .source
                .contains("stored for stacks that cannot measure it")
        );
        let stored = cutoffs::load(&path).unwrap();
        assert_eq!(stored.len(), 1);
        assert_eq!(stored[0].capture, "stack-measured");
        let flat: Vec<f64> = c.iter().map(|f| f.powf(-2.0)).collect();
        let later = choose_cutoffs(
            fitted_on([flat.clone(), flat.clone(), flat.clone()]),
            None,
            Some(&weevil()),
            "diffraction",
            &path,
        )
        .unwrap();
        assert!(
            later.source.starts_with("STORED fit of stack-measured"),
            "{}",
            later.source
        );
        let mut other = weevil();
        other.lens_type3 = Some(1);
        let err = choose_cutoffs(
            fitted_on([flat.clone(), flat.clone(), flat]),
            None,
            Some(&other),
            "diffraction",
            &path,
        )
        .err()
        .unwrap()
        .to_string();
        assert!(err.contains("no stored fit can stand in"), "{err}");
        let _ = std::fs::remove_dir_all(path.parent().unwrap());
    }
}
