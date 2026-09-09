//! Per-frame measurement of the pyramid's band-noise floor.
//!
//! # What this replaces and why
//!
//! [`strehl_core::pyramid::BandGain`] measures `beta[k] = E[L_k^2] / sigma_0^2`
//! by pushing **white** noise through the pyramid. That is the noise transfer of
//! a frame whose samples are independent, which describes an *unwarped* frame
//! and nothing else. Every frame the merge actually folds has been resampled
//! onto the reference grid first, so its noise is correlated by the
//! interpolation kernel and its band-0 power is lower than white.
//!
//! BUILD-GATE measured the resulting over-statement at band 0 as
//! `beta_actual / beta_white` in **0.3432 .. 0.9981** across eight
//! representative warps, in **both** gather arms, with every entry below 1.0.
//! At `gate = 2.0` that sets the bar at up to **3.7x** the true noise power
//! instead of the intended 2.0x, so the merge averages pixels that carry real
//! signal.
//!
//! # Why a probe and not a formula
//!
//! The transfer is a *function of sub-pixel warp phase*, not a constant. The
//! plane gather's band-0 floor traces a curve of period one plane-pixel with a
//! minimum of 0.3432; the full-res gather's has period one **full-res** pixel
//! because it is an exact no-op at integer full-res shifts, with minima of
//! 0.5784 -- and **the two curves cross**. A scalar fitted at one phase is
//! wrong by up to 2.91x at another, which is why this module measures rather
//! than corrects.
//!
//! # Why the probe clones the real frame
//!
//! [`Probe::measure`] takes the decoded frame as a *template* and copies
//! everything except its samples: geometry, stride, active window, black and
//! white levels, **white-balance coefficients** and **path**. All four matter.
//!
//! - `wb_coeffs`: [`align_cmd::warp_frame_in_place_fullres`] balances the
//!   mosaic, demosaics it, samples, then un-balances by the *site's own* gain.
//!   Malvar's green at a red site mixes red and green neighbours, so unequal
//!   gains change how much of each channel's noise lands in green.
//! - `path`: the CA profile is resolved from the camera identity and composed
//!   into the transform **per channel**, so the four CFA sites are warped at
//!   four slightly different phases. A probe with a synthetic path would get an
//!   identity profile and the wrong phases.
//!
//! Copying the template rather than reconstructing it means there is no list of
//! fields to keep in step, which is the failure mode a hand-built probe has.

use anyhow::{Context, Result};
use rayon::prelude::*;
use strehl_core::align::{Resampler, Similarity};
use strehl_core::plane::PlaneGeometry;
use strehl_core::pyramid::{LevelSize, Pyramid, Workspace, level_sizes};
use strehl_raw::Frame;

use super::{BAND_PLANE_OFFSETS, PyramidDomain, extract_planes};
use crate::align_cmd::{self, WarpScratch};

/// Probe level above black, in DN. Far enough above the pedestal that the
/// `(data - black).max(0.0)` clamp in `load_frame` never fires -- it is a
/// nonlinearity, and a probe that trips it would measure the clamp.
const PROBE_LEVEL: f64 = 2000.0;

/// Probe photosite noise sigma, in DN. `beta` is a ratio, so the value is
/// arbitrary; BUILD-GATE's C2 control measured it invariant to 0.046% under a
/// 2x amplitude change. 40 DN sits well inside the `PROBE_LEVEL` headroom.
const PROBE_SIGMA: f64 = 40.0;

/// Fraction of each pyramid level trimmed from every side before pooling.
///
/// **Not defensive.** `warp_frame_in_place_*` leaves samples that map outside
/// the source at black, a pedestal-height ring around the frame. BUILD-GATE
/// measured that ring inflating whole-plane variance by **39x** and driving
/// band ratios to a physically impossible 14.19 before it was cropped out. A
/// *fraction* rather than a pixel count because the ring's influence spreads by
/// a few pixels per pyramid level, so a fixed count shrinks faster than the
/// contamination does.
const MARGIN_FRACTION: usize = 8;

/// Minimum pooled samples for a band to be trusted. Below this the estimate is
/// sampling noise and the band falls back to the white value rather than
/// carrying a number nobody measured.
const MIN_SAMPLES: usize = 256;

/// Environment switch. `STREHL_GATE_FLOOR=white` restores the shipping
/// white-noise floor exactly; anything else, including unset, uses the measured
/// per-frame floor.
///
/// The default is the measured floor because the white one is **wrong for every
/// warped frame** -- see the module docs. `white` exists so the two can be run
/// head to head on the same pixels, which is how the movement in the byte
/// freezes was attributed.
pub const GATE_FLOOR_ENV: &str = "STREHL_GATE_FLOOR";

/// Whether the measured per-frame floor is in use.
pub fn enabled() -> bool {
    static CHOICE: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *CHOICE.get_or_init(|| {
        std::env::var(GATE_FLOOR_ENV)
            .map(|v| !v.eq_ignore_ascii_case("white"))
            .unwrap_or(true)
    })
}

/// Synthetic-probe output work: `rgb` retains the original four-site warp;
/// `green` (default) omits only unused full-resolution R/B outputs.
pub const PROBE_GATHER_ENV: &str = "STREHL_PROBE_GATHER";

pub(super) fn probe_gather_uses_green() -> Result<bool> {
    static CHOICE: std::sync::OnceLock<std::result::Result<bool, String>> =
        std::sync::OnceLock::new();
    match CHOICE.get_or_init(|| match std::env::var(PROBE_GATHER_ENV) {
        Err(std::env::VarError::NotPresent) => Ok(true),
        Ok(v) if v.eq_ignore_ascii_case("green") => Ok(true),
        Ok(v) if v.eq_ignore_ascii_case("rgb") => Ok(false),
        other => Err(format!(
            "{PROBE_GATHER_ENV}: expected green or rgb, got {other:?}"
        )),
    }) {
        Ok(value) => Ok(*value),
        Err(message) => anyhow::bail!("{message}"),
    }
}

/// Per-band multiplier on the floor, comma separated, e.g.
/// `STREHL_GATE_FLOOR_SCALE=1,4,4,4,4,4,4`. Unset means no scaling and is a
/// byte-exact no-op.
///
/// This exists because `--pyramid-gate` is a single number by construction and
/// the measurement that motivated the knob wants opposite moves at opposite
/// ends of the pyramid: at band 0 the gate already averages 54.4% of the finest
/// band, while bands 1..6 average 0.0% at the shipping `k` and only reach
/// 8.1/4.7/3.1/1.3/0.0/0.0% at `k=8` -- by which point band 0 is at 97.2% and
/// the fine detail is gone. Scaling `k` per band and scaling the floor per band
/// are the same operation, so this is the cheaper seam: it needs no change to
/// the merge, and the merge's own `is_finite` fallback keeps a shorter list
/// valid.
///
/// Above the certified range the floor is extended with the white value before
/// scaling, because the merge would otherwise fall back to white and the knob
/// would have no authority at exactly the coarse bands it is aimed at. Passing
/// all ones therefore reproduces the unset render exactly, which is the
/// negative control this knob is commissioned with.
pub const GATE_FLOOR_SCALE_ENV: &str = "STREHL_GATE_FLOOR_SCALE";

/// The parsed per-band scale, empty when unset.
fn scale() -> &'static [f32] {
    static CHOICE: std::sync::OnceLock<Vec<f32>> = std::sync::OnceLock::new();
    CHOICE.get_or_init(|| {
        let Ok(raw) = std::env::var(GATE_FLOOR_SCALE_ENV) else {
            return Vec::new();
        };
        let parsed: Vec<f32> = raw
            .split(',')
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(|s| {
                s.parse::<f32>()
                    .unwrap_or_else(|_| panic!("{GATE_FLOOR_SCALE_ENV}: {s:?} is not a number"))
            })
            .collect();
        assert!(
            parsed.iter().all(|v| v.is_finite() && *v > 0.0),
            "{GATE_FLOOR_SCALE_ENV}: every entry must be finite and positive, got {parsed:?}"
        );
        parsed
    })
}

/// `STREHL_GATE_FLOOR=debug` additionally reports every frame's measured floor
/// against the white model it replaces.
///
/// Deliberately a value of the *same* variable rather than a second one: a
/// separate debug switch can be set while the feature is off, and would then
/// print a floor the merge is not using.
fn debug() -> bool {
    static CHOICE: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *CHOICE.get_or_init(|| {
        std::env::var(GATE_FLOOR_ENV)
            .map(|v| v.eq_ignore_ascii_case("debug"))
            .unwrap_or(false)
    })
}

/// Reusable buffers for [`Probe::measure`].
pub(super) struct Probe {
    domain: PyramidDomain,
    planes: Vec<Vec<f32>>,
    luma: Vec<f32>,
    ws: Workspace,
    pyr: Pyramid,
    sizes: Vec<LevelSize>,
    beta: Vec<f32>,
}

impl Probe {
    pub(super) fn new(domain: PyramidDomain, bands: usize) -> Self {
        let geom = domain.analysis();
        let sizes = level_sizes(geom.width, geom.height, bands);
        let px = geom.pixels();
        Self {
            domain,
            planes: (0..2).map(|_| vec![0.0f32; px]).collect(),
            luma: vec![0.0f32; px],
            ws: Workspace::new(&sizes),
            pyr: Pyramid::zeros(&sizes),
            beta: Vec::new(),
            sizes,
        }
    }

    /// Discard the last measurement.
    ///
    /// **Load-bearing.** A frame that is not warped never calls
    /// [`measure`](Self::measure), so without this the probe would still be
    /// holding the *previous* frame's floor and the merge would gate an
    /// unwarped frame at some other frame's phase. Called unconditionally
    /// before each fold, so the invariant is "a floor is only ever this frame's
    /// floor" rather than "every caller remembers".
    pub(super) fn invalidate(&mut self) {
        self.beta.clear();
    }

    /// Measure this frame's band-noise floor: `beta[k]` for the warp `t`, on the
    /// same grid and through the same operators the merge itself uses.
    ///
    /// `template` supplies every frame parameter except the samples -- see the
    /// module docs for why each one matters. `index` seeds the noise, so the
    /// result is a deterministic function of the inputs and the render stays
    /// byte-reproducible.
    ///
    /// Returns the Laplacian bands only. The base band is never gated.
    pub(super) fn measure(
        &mut self,
        template: &Frame,
        index: usize,
        t: Similarity,
        resampler: Resampler,
        scratch: &mut WarpScratch,
    ) -> Result<&[f32]> {
        self.run(template, index, t, resampler, scratch)?;
        if debug() {
            // The commissioning null, run on the REAL frame with its real white
            // balance and its real CA profile, because those are exactly the
            // parameters a synthetic probe gets wrong.
            //
            // At the identity the full-res gather samples
            // `2*T(px + dx*0.5, py + dy*0.5) = 2px + dx`, an integer;
            // Catmull-Rom is interpolating and Malvar returns `known` at a
            // site's own channel, so the warp is an exact no-op and the floor
            // must come back at the white value. Any drift is the probe's, not
            // the warp's, and it is measured here rather than assumed.
            let got = self.beta.clone();
            self.run(template, index, Similarity::IDENTITY, resampler, scratch)?;
            let white = strehl_core::pyramid::BandGain::measure(self.sizes.len() - 1);
            let worst = self
                .beta
                .iter()
                .enumerate()
                .map(|(k, b)| (b / white.beta(k) - 1.0).abs())
                .fold(0.0f32, f32::max);
            eprintln!(
                "  gate floor: NULL frame {index:>3} identity warp  b0={:.4} ({:.4}x white)  \
                 worst band {:+.3}%  {}",
                self.beta[0],
                self.beta[0] / white.beta(0),
                100.0 * worst,
                if worst < 0.02 { "PASS" } else { "FAIL" }
            );
            self.beta = got;
        }
        self.apply_scale();
        Ok(&self.beta)
    }

    fn run(
        &mut self,
        template: &Frame,
        index: usize,
        t: Similarity,
        resampler: Resampler,
        scratch: &mut WarpScratch,
    ) -> Result<()> {
        // Refuse an unknown arm before cloning or generating a synthetic frame.
        let greens_only = probe_gather_uses_green()?;
        #[cfg(feature = "native-direct-planes")]
        let direct_mode = align_cmd::direct_plane_mode()?;
        #[cfg(feature = "native-direct-planes")]
        let direct_consumed = direct_mode != align_cmd::DirectPlaneMode::Off && align_cmd::fullres_gather_enabled();
        #[cfg(not(feature = "native-direct-planes"))]
        let direct_consumed = false;
        let mut probe = template.clone();
        let black = f64::from(template.levels.black);
        fill_probe_noise(
            &mut probe,
            self.domain.full,
            black + PROBE_LEVEL,
            PROBE_SIGMA,
            index,
        )?;

        #[cfg(feature = "native-direct-planes")]
        if direct_consumed {
            if greens_only {
                align_cmd::warp_frame_fullres_into_planes::<true>(
                    &mut probe,t,self.domain.full,resampler,scratch,self.domain.rect,
                    &BAND_PLANE_OFFSETS[1..3],&mut self.planes,direct_mode)
            } else {
                align_cmd::warp_frame_fullres_into_planes::<false>(
                    &mut probe,t,self.domain.full,resampler,scratch,self.domain.rect,
                    &BAND_PLANE_OFFSETS[1..3],&mut self.planes,direct_mode)
            }.context("gathering the direct noise-probe planes")?;
            #[cfg(test)]
            align_cmd::direct_plane_probe_hit();
        }
        if !direct_consumed {
            if greens_only {
                align_cmd::warp_probe_greens_in_place(&mut probe, t, self.domain.full, resampler, scratch)
            } else {
                align_cmd::warp_frame_in_place(&mut probe, t, self.domain.full, resampler, scratch)
                    .map(|_| ())
            }
            .context("warping the noise probe for the band-noise floor")?;
        }

        // Deinterleave the two green phases exactly as `load_frame` does, and
        // form the same `L = (G1 + G2) / 2`. Only the greens: the selection
        // runs on green luma, so that is the plane whose noise the gate models.
        let blackf = template.levels.black;
        if !direct_consumed {
            extract_planes(
                &probe.data,
                probe.stride,
                probe.active.x,
                probe.active.y,
                blackf,
                self.domain,
                &BAND_PLANE_OFFSETS[1..3],
                &mut self.planes,
            )
            .context("extracting the compact gate-floor luma domain")?;
        }
        for i in 0..self.luma.len() {
            self.luma[i] = 0.5 * (self.planes[0][i] + self.planes[1][i]);
        }

        // Zero-mean the field before the pyramid.
        //
        // `BandGain::measure` builds its white probe zero-mean, so a probe
        // carrying the pedestal is not measuring the same thing. A constant is
        // invisible to a Laplacian band *in the interior* but not at the
        // boundary, where the pyramid's edge handling turns it into real band
        // power -- and at the coarsest levels the boundary is most of the
        // image. Measured, before this line existed: the identity null returned
        // 0.9998x white at band 0 and **12.6x** at band 6, on a warp that is an
        // exact no-op. The floor is a statement about fluctuations; the
        // pedestal is not one of them.
        let mean =
            (self.luma.iter().map(|v| f64::from(*v)).sum::<f64>() / self.luma.len() as f64) as f32;
        for v in self.luma.iter_mut() {
            *v -= mean;
        }

        // The denominator. Green luma is the mean of two independent greens, so
        // its pre-warp variance is `sigma^2 / 2` exactly. Taken analytically and
        // not measured, because a measured denominator would carry the same
        // black-border contamination the numerator is cropped to avoid.
        let sigma0_sq = PROBE_SIGMA * PROBE_SIGMA * 0.5;

        self.pyr.build(&self.luma, &mut self.ws);
        self.beta.clear();
        // Correct only the bands this probe can certify, and only where the
        // effect is bigger than the probe's own error.
        //
        // Two measurements set this bound, both from the identity null on real
        // frames -- a warp that is an exact no-op, so every band must come back
        // at the white value:
        //
        //   band          0       1       2       3   |     4       5       6
        //   null      1.0000  0.999   0.995   1.003   | 1.031   1.021   12.6
        //   warped    1.149   0.944   1.002   1.028   | 1.022   1.037    ~1.0
        //
        // Bands 0..3 are certified to within 0.5% and carry a real effect at
        // band 0 (+14.9%) and band 1 (-5.6%). At bands 4 and 5 the null's own
        // error (+3.1%, +2.1%) is the same size as the difference the warp
        // makes there, so a correction would be reporting the instrument. Band
        // 6 is the truncation seam described above.
        //
        // Expressed as a count rather than a hard index so a sensor whose
        // pyramid is shallower keeps a valid slice; `add_frame_with_gain` falls
        // back to white beyond the end.
        const CERTIFIED_BANDS: usize = 4;
        let measurable = CERTIFIED_BANDS.min(self.sizes.len().saturating_sub(2));
        for k in 0..measurable {
            let sz = self.sizes[k];
            match pooled_mean_square(self.pyr.level(k), sz) {
                Some(e) => self.beta.push((e / sigma0_sq) as f32),
                // Too few interior samples at this level to say anything. Left
                // as NaN so the caller's `is_finite` filter drops it back to the
                // white value instead of gating on a number nobody measured.
                None => self.beta.push(f32::NAN),
            }
        }
        if debug() {
            self.report(index, t);
        }
        Ok(())
    }

    /// Apply [`GATE_FLOOR_SCALE_ENV`], extending to every Laplacian band first.
    ///
    /// Called from `measure` rather than `run`, and after the debug block, so
    /// that neither the per-frame `report` nor the identity-warp commissioning
    /// null ever sees a scaled floor. Both of those compare the measured floor
    /// against white to detect *probe* error; a knob applied before them would
    /// be reported as exactly the instrument fault they exist to catch.
    ///
    /// It extends before it scales, so a band above the certified range is
    /// scaled relative to white instead of being left to the merge's white
    /// fallback, where the multiplier would silently do nothing.
    fn apply_scale(&mut self) {
        let s = scale();
        if s.is_empty() {
            return;
        }
        let white = strehl_core::pyramid::BandGain::measure(self.sizes.len() - 1);
        let bands = self.sizes.len().saturating_sub(1);
        while self.beta.len() < bands {
            let k = self.beta.len();
            self.beta.push(white.beta(k));
        }
        for (k, b) in self.beta.iter_mut().enumerate() {
            // A band the probe could not certify stays NaN: the merge drops it
            // back to white, and scaling a number nobody measured would be
            // inventing one.
            if b.is_finite() {
                *b *= s.get(k).copied().unwrap_or(1.0);
            }
        }
    }

    /// Report this frame's measured floor beside the white model it replaces.
    fn report(&self, index: usize, t: Similarity) {
        let white = strehl_core::pyramid::BandGain::measure(self.sizes.len() - 1);
        let p = t.to_params();
        let mut line = format!(
            "  gate floor: frame {index:>3}  d=({:+.4},{:+.4}) g={:+.6} rot={:+.6}  ",
            p.ax, p.ay, p.g, p.rot
        );
        for (k, b) in self.beta.iter().enumerate() {
            let w = white.beta(k);
            line.push_str(&format!("b{k}={:.4}({:.3}x) ", b, b / w));
        }
        eprintln!("{line}");
    }

    /// The floor measured by the last [`measure`](Self::measure) call, Laplacian
    /// bands only. Empty before the first call; `NaN` at a band the probe could
    /// not speak for.
    pub(super) fn last(&self) -> &[f32] {
        &self.beta
    }
}

/// Mean square of a band's interior, or `None` if the crop leaves too little.
fn pooled_mean_square(level: &[f32], sz: LevelSize) -> Option<f64> {
    let mx = (sz.width / MARGIN_FRACTION).max(3);
    let my = (sz.height / MARGIN_FRACTION).max(3);
    if sz.width <= 2 * mx || sz.height <= 2 * my {
        return None;
    }
    let (iw, ih) = (sz.width - 2 * mx, sz.height - 2 * my);
    if iw * ih < MIN_SAMPLES {
        return None;
    }
    let mut acc = 0.0f64;
    for y in my..sz.height - my {
        let row = &level[y * sz.width + mx..y * sz.width + sz.width - mx];
        for v in row {
            acc += f64::from(*v) * f64::from(*v);
        }
    }
    Some(acc / (iw * ih) as f64)
}

/// Select the deterministic execution schedule, never a different noise law.
pub const PROBE_FILL_ENV: &str = "STREHL_PROBE_FILL";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum FillMode {
    Serial,
    Parallel,
}

fn parse_fill_mode(raw: Option<&str>) -> Result<FillMode> {
    match raw {
        None | Some("parallel") => Ok(FillMode::Parallel),
        Some("serial") => Ok(FillMode::Serial),
        _ => anyhow::bail!("{PROBE_FILL_ENV} must be unset, serial, or parallel"),
    }
}

/// Fill only the complete quads that both gather implementations consume.
/// The RNG advances in active-relative row order, never through unused storage.
/// Using the full geometry (not the analysis Crop) also keeps the probe at a
/// photosite unchanged when only the output domain changes. Odd trailing active
/// sensels are outside the consumer's complete-quad extent and remain untouched.
fn fill_probe_noise(
    frame: &mut Frame,
    full: PlaneGeometry,
    level: f64,
    sigma: f64,
    index: usize,
) -> Result<()> {
    // Resolve once per full fill, before writing; no environment access per row.
    let mode = match std::env::var(PROBE_FILL_ENV) {
        Ok(raw) => parse_fill_mode(Some(&raw))?,
        Err(std::env::VarError::NotPresent) => parse_fill_mode(None)?,
        Err(error) => return Err(error).context(PROBE_FILL_ENV),
    };
    fill_probe_noise_mode(frame, full, level, sigma, index, mode)
}

fn fill_probe_noise_mode(
    frame: &mut Frame,
    full: PlaneGeometry,
    level: f64,
    sigma: f64,
    index: usize,
    mode: FillMode,
) -> Result<()> {
    super::validate_pyramid_frame(frame, full, index)?;
    let (ax, ay) = (frame.active.x, frame.active.y);
    let width = 2 * full.width;
    match mode {
        FillMode::Serial => {
            let sites = frame
                .data
                .chunks_exact_mut(frame.stride)
                .skip(ay)
                .take(2 * full.height)
                .flat_map(|row| row[ax..ax + width].iter_mut());
            fill_noise(sites, level, sigma, index);
        }
        FillMode::Parallel => {
            let seed = noise_seed(index);
            frame
                .data
                .par_chunks_exact_mut(frame.stride)
                .skip(ay)
                .take(2 * full.height)
                .enumerate()
                .for_each(|(row_index, row)| {
                    // A complete-quad row is even: each Box-Muller pair uses
                    // two RNG draws for two sites, with no spare across rows.
                    let draws = (row_index as u64).wrapping_mul(width as u64);
                    let state = seed.wrapping_add(0x9E37_79B9_7F4A_7C15u64.wrapping_mul(draws));
                    fill_noise_from_state(row[ax..ax + width].iter_mut(), level, sigma, state);
                });
        }
    }
    Ok(())
}

/// Fill the destination sequence with `level + N(0, sigma^2)`, quantised to u16
/// as a real frame is.
///
/// Deterministic in `index` alone. A probe seeded from a clock or from thread
/// scheduling would make the gate -- and therefore the merge -- irreproducible,
/// and the byte-freezes would fail for a reason that is not a bug in the merge.
fn fill_noise<'a>(data: impl Iterator<Item = &'a mut u16>, level: f64, sigma: f64, index: usize) {
    fill_noise_from_state(data, level, sigma, noise_seed(index));
}

fn noise_seed(index: usize) -> u64 {
    0x9E37_79B9_7F4A_7C15u64.wrapping_mul(index as u64 + 1) ^ 0x2545_F491_4F6C_DD1D
}

fn fill_noise_from_state<'a>(
    data: impl Iterator<Item = &'a mut u16>,
    level: f64,
    sigma: f64,
    mut s: u64,
) {
    // SplitMix64. Self-contained on purpose: the probe's determinism is a
    // property of this file and should not move if a shared RNG is retuned.
    let mut next = || {
        s = s.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = s;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        f64::from(((z ^ (z >> 31)) >> 40) as u32) / f64::from(1u32 << 24)
    };
    let mut spare: Option<f64> = None;
    for d in data {
        // Box-Muller, both draws used.
        let g = match spare.take() {
            Some(g) => g,
            None => {
                let (u1, u2) = (next().max(1e-12), next());
                let r = (-2.0 * u1.ln()).sqrt();
                let th = std::f64::consts::TAU * u2;
                spare = Some(r * th.sin());
                r * th.cos()
            }
        };
        *d = (level + sigma * g).round().clamp(0.0, f64::from(u16::MAX)) as u16;
    }
}

#[cfg(test)]
mod m194c_author_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194c-probe-layout/author-tests.rs"
    ));
}

#[cfg(test)]
mod m194c_independent_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194c-probe-layout/independent-tests.rs"
    ));

    pub(super) fn green_fixture(w: usize, h: usize, layout: usize, k: usize) -> Frame {
        make_frame(w, h, layout, k)
    }

    pub(super) fn variance_warp() -> Similarity { warp(1) }
    pub(super) fn variance_crop() -> align_cmd::CropRect { crop() }

    pub(super) fn green_render(
        frames: Vec<Frame>,
        dir: &std::path::Path,
        label: &str,
        cropped: bool,
    ) -> Vec<u8> {
        render(frames, dir, label, cropped, false, false, 0)
    }
}

#[cfg(test)]
mod native_probe_fill_independent_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/native-probe-fill/independent-tests.rs"
    ));
}

#[cfg(test)]
mod native_green_probe_independent_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/native-green-probe/independent-tests.rs"
    ));

    pub(super) fn run_for_writeback_controls() {
        independent_green_probe_controls();
    }
}

#[cfg(test)]
mod native_parallel_writeback_independent_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/native-parallel-writeback/independent-tests.rs"
    ));
}

#[cfg(all(test, feature = "native-direct-planes"))]
mod native_direct_planes_independent_tests {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-direct-planes/independent-tests.rs"));
}

#[cfg(all(test, feature = "native-correction-variance"))]
mod native_correction_variance {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-correction-variance/implementation.rs"));
}
