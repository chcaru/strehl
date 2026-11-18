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
//!   about ten photosites of a near-clipped sample.
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

pub(super) const ENV: &str = "STREHL_OPTICAL_RESTORE";
/// Target Gaussian sigma, output px (experiment control; default
/// [`SIGMA_T`]).
pub(super) const SIGMA_ENV: &str = "STREHL_OPTICAL_RESTORE_SIGMA";
/// The prototype's arm `f5`: lifted detail without visible grain on the
/// scarab; 0.60 added grain.
const SIGMA_T: f64 = 0.70;
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
/// Samples above this fraction of the black-to-white range count as clipped.
const CLIP_FRACTION: f32 = 0.80;
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

fn sigma_t() -> Result<f64> {
    match std::env::var(SIGMA_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(SIGMA_T),
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
            Ok(s)
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
}

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
                return Ok(None);
            }
            sigma_t()?;
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
        for &k in &t.frames {
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
    st.tiles
        .iter()
        .filter(|t| t.frames.contains(&index))
        .map(|t| crop(planes, st.width, t.x0, t.y0))
        .collect()
}

/// Keep frame `index`'s prepared planes on the tiles whose reference it is.
pub(super) fn observe(index: usize, planes: &[Vec<f32>]) {
    let mut guard = state();
    let Some(st) = guard.as_mut() else { return };
    let w = st.width;
    for t in st.tiles.iter_mut() {
        let Some(slot) = t.frames.iter().position(|&k| k == index) else {
            continue;
        };
        t.reference[slot] = Some(crop(planes, w, t.x0, t.y0));
    }
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
    let sigma = sigma_t()?;
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
    for t in &st.tiles {
        let [Some(r0), Some(r1)] = &t.reference else {
            no_ref += 1;
            continue;
        };
        if clipped(merged, t.x0, t.y0) {
            hot += 1;
            continue;
        }
        usable.push((t, r0, r1));
    }
    let used = usable.len();
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
                "centres": centres, "tiles": used, "channels": dump,
            }))?,
        )?;
    }
    let (joint, joint_rms) =
        core::fit_cutoff_joint(&centres, [&ref_signal[0], &ref_signal[1], &ref_signal[2]]);
    let measured: [f64; 3] =
        std::array::from_fn(|c| joint * core::WAVELENGTH_UM[1] / core::WAVELENGTH_UM[c]);
    let (cutoffs, source) = match cutoff_override()? {
        Some(given) => (
            given,
            format!(
                "GIVEN by {CUTOFF_ENV}, not measured on this stack (its own joint fit: green {joint:.3})"
            ),
        ),
        None => {
            ensure!(
                joint < JOINT_CEILING,
                "optical restoration: the diffraction cutoff is not measurable on this stack (the one-aperture fit \
                 of the reference frames ran to its ceiling: green {joint:.3} cycles/px; per channel \
                 {:.3}/{:.3}/{:.3}). A single-shot frame cannot sample the lens's roll-off above its 0.5 \
                 cycles/px Nyquist, and its demosaic structure reads as signal there. Measure the cutoff \
                 on a four-shot run of the same setup (STREHL_CARRY_RGB=on) and pass it as \
                 {CUTOFF_ENV}=r,g,b",
                fits[0].0,
                fits[1].0,
                fits[2].0
            );
            (
                measured,
                format!(
                    "one aperture fitted to all three reference channels (relative residual \
                     {joint_rms:.4}; diffraction ratios from nominal wavelengths 600/535/465 nm)"
                ),
            )
        }
    };
    let mut models = Vec::with_capacity(3);
    // Each channel's model, gain grid and kernel: independent, so designed
    // side by side, then reported in channel order.
    let designs: Vec<Result<(Vec<f64>, core::ChannelModel, core::Kernel)>> = (0..3)
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
            let g = core::gain_grid(&model, 128, sigma, MAX_GAIN);
            // Judged where the filter does its work: below the taper.
            let k = core::kernel(&g, 128, MAX_RADIUS, TOLERANCE, (0.25, 0.40));
            Ok((m, model, k))
        })
        .collect();
    for (c, design) in designs.into_iter().enumerate() {
        let fc = cutoffs[c];
        let (fitted, fit_rms, cube) = fits[c];
        let (m, model, k) = design?;
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
                "centres": centres, "tiles": used, "channels": dump,
            }))?,
        )?;
    }
    // Highlight guard: keep the unrestored value within about ten photosites
    // of a near-clipped sample, with a smooth hand-over (quad grid).
    let hotq: Vec<f32> = (0..gw * gh)
        .into_par_iter()
        .map(|i| f32::from(u8::from(merged.iter().any(|p| p[i] > clip))))
        .collect();
    let near = max_filter(&hotq, gw, gh, 5);
    let soft = axial_colour::blur(&near, gw, gh, 2.0);
    let keep: Vec<f32> = soft.iter().map(|v| 1.0 - v.clamp(0.0, 1.0)).collect();
    let guarded = keep.iter().filter(|v| **v < 0.999).count() as f64 / keep.len() as f64;
    for c in 0..3 {
        let off = ROOT_OFFSET_DN * norm.scale(c);
        let x: Vec<f32> = rgb.par_chunks_exact(3).map(|p| p[c]).collect();
        let root: Vec<f32> = x.par_iter().map(|v| (v.max(0.0) + off).sqrt()).collect();
        let y = core::convolve(&root, mw, mh, &kernels[c]);
        rgb.par_chunks_exact_mut(3)
            .zip(y.par_iter().zip(x.par_iter()))
            .enumerate()
            .for_each(|(i, (p, (y, x)))| {
                let restored = y.max(0.0).powi(2) - off;
                let k = keep[(i / mw / 2) * gw + (i % mw) / 2];
                p[c] = x + k * (restored - x);
            });
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
            let fd = core::convolve(&d, mw, mh, &kern);
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
    eprintln!(
        "optical restore : ON ({}) -- target Gaussian sigma {sigma:.2} px, Wiener against the \
         measured noise, gain cap {MAX_GAIN}, square-root domain{}",
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
    eprintln!(
        "                  cutoffs R/G/B {:.3}/{:.3}/{:.3}: {source}; highlight guard covers {:.2}% of \
         the frame; {:.1} s",
        cutoffs[0],
        cutoffs[1],
        cutoffs[2],
        100.0 * guarded,
        started.elapsed().as_secs_f64()
    );
    if let Some(line) = &chroma_line {
        eprintln!("{line}");
    }
    Ok(chroma_line.is_some())
}
