//! Explicit, frozen SDR scene development. This is a separate contract from
//! `learned_profile`: gain-query scale never scales the RGB being developed.
//! No inference, asset loading, default profile, recipe, or UI is installed here.
//!
//! `strehl.scene-sdr-linear.v1` performs, in order:
//! supplied BT.709-to-working transform -> clamp negative working channels ->
//! query spatial/brightness gain at separately scaled RGB -> apply gain to the
//! unscaled working RGB -> apply exposure scale -> cap RGB extrema at one while
//! preserving the middle channel's relative position -> supplied color table ->
//! supplied working-to-BT.709 transform. The LUT retains its explicit encoding,
//! interpolation and gamut-extension policy from `learned_profile::ColorLut`.
//!
//! This contract intentionally discards negative working values and SDR highlight
//! headroom. A float result is not an HDR treatment. It is also not a complete
//! application development branch: manual edits, baseline placement, display
//! contrast and final presentation remain the caller's explicit responsibility.

use crate::learned_profile::{
    ColorLut, GainMap, IDENTITY_MATRIX, Matrix3, ProfileRegion, matrix_rgb, validate_matrix,
};
use anyhow::{Result, ensure};
use rayon::prelude::*;
use std::sync::atomic::{AtomicBool, Ordering};

/// Versioned operation order and numeric policy, not a model or asset identifier.
pub const SCENE_SDR_LINEAR_V1: &str = "strehl.scene-sdr-linear.v1";
const MAX_IMAGE_DIMENSION: u32 = 1 << 20;

#[derive(Clone, Copy, Debug)]
pub struct SceneSdrParameters {
    pub linear_709_to_working: Matrix3,
    /// Explicitly supplied to preserve a previously validated pair's FP32 values.
    /// The pair must be nonsingular and approximately inverse (absolute 0.001).
    pub working_to_linear_709: Matrix3,
    /// Positive linear multiplier in (0, 256], used ONLY to index the gain map.
    pub gain_query_scale: f32,
    /// Positive linear multiplier in (0, 256], applied AFTER the sampled gain.
    /// No model exposure units, camera compensation or allocation are inferred.
    pub exposure_scale: f32,
}

/// Immutable shared fields; clones share the existing gain and color-table data.
/// No per-pixel allocation and no semantic-mask substitution or regional analysis.
#[derive(Clone, Debug)]
pub struct PreparedSceneSdrProfile {
    gain: GainMap,
    table: ColorLut,
    parameters: SceneSdrParameters,
}

/// Validate serialized parameters before allocating numeric field payloads.
pub(crate) fn validate_scene_parameters(parameters: SceneSdrParameters) -> Result<()> {
    for scale in [parameters.gain_query_scale, parameters.exposure_scale] {
        ensure!(
            scale.is_finite() && scale > 0. && scale <= 256.,
            "SDR scene scales must be finite in (0, 256]"
        );
    }
    validate_matrix(parameters.linear_709_to_working)?;
    validate_matrix(parameters.working_to_linear_709)?;
    for (a, b) in [
        (
            parameters.linear_709_to_working,
            parameters.working_to_linear_709,
        ),
        (
            parameters.working_to_linear_709,
            parameters.linear_709_to_working,
        ),
    ] {
        for r in 0..3 {
            for c in 0..3 {
                let value = (0..3)
                    .map(|k| f64::from(a[r][k]) * f64::from(b[k][c]))
                    .sum::<f64>();
                ensure!(
                    (value - f64::from(IDENTITY_MATRIX[r][c])).abs() <= 0.001,
                    "SDR scene transforms are not an inverse pair"
                );
            }
        }
    }
    Ok(())
}

impl PreparedSceneSdrProfile {
    pub fn new(gain: GainMap, table: ColorLut, parameters: SceneSdrParameters) -> Result<Self> {
        validate_scene_parameters(parameters)?;
        Ok(Self {
            gain,
            table,
            parameters,
        })
    }

    pub fn contract_id(&self) -> &'static str {
        SCENE_SDR_LINEAR_V1
    }

    pub fn parameters(&self) -> SceneSdrParameters {
        self.parameters
    }

    /// Full-strength scene branch in linear BT.709. `uv` is the center of the
    /// source footprint in the FULL photograph in [0, 1], never crop-local UV.
    /// For an Amount control, finish both branches in the same linear domain
    /// before using `blend_sdr_scene_pixel`; do not blend against the raw source.
    pub fn develop_pixel(&self, linear_709: [f32; 3], uv: [f32; 2]) -> Result<[f32; 3]> {
        ensure!(
            linear_709.iter().all(|v| v.is_finite()),
            "Nonfinite SDR scene input"
        );
        ensure!(
            uv.iter().all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
            "SDR scene coordinates must refer to the full image in 0..1"
        );
        self.develop_inner(linear_709, uv)
    }

    #[inline]
    fn develop_inner(&self, source: [f32; 3], uv: [f32; 2]) -> Result<[f32; 3]> {
        let working = matrix_rgb(&self.parameters.linear_709_to_working, source);
        // Check BEFORE max/min: floating point clamp can otherwise hide NaNs or
        // overflow and turn an invalid input into a plausible black/white pixel.
        ensure!(
            working.iter().all(|v| v.is_finite()),
            "SDR scene transform overflow"
        );
        let working = working.map(|v| v.max(0.));
        let query = working.map(|v| v * self.parameters.gain_query_scale);
        ensure!(
            query.iter().all(|v| v.is_finite()),
            "SDR scene gain-query overflow"
        );
        let gain = self.gain.sample_inner(query, uv);
        ensure!(gain.is_finite(), "Nonfinite SDR scene gain");
        let exposed = working.map(|v| (v * gain) * self.parameters.exposure_scale);
        ensure!(
            exposed.iter().all(|v| v.is_finite()),
            "SDR scene exposure overflow"
        );
        let mapped = self.table.apply_inner(cap_sdr_rgb(exposed));
        let result = matrix_rgb(&self.parameters.working_to_linear_709, mapped);
        ensure!(
            result.iter().all(|v| v.is_finite()),
            "Nonfinite SDR scene output"
        );
        Ok(result)
    }

    /// Develop a native crop into caller-owned storage, preserving whole-image
    /// gain coordinates. Rows run in parallel; no extra full-resolution buffer.
    /// Cancellation is checked at row starts and every 64 pixels. An error can
    /// leave a partial destination: publish it only after this returns `Ok`.
    /// Resampled previews instead call `develop_pixel` at source-footprint UVs;
    /// developing an averaged source is a coarse approximation, not the average
    /// of fully developed pixels under these nonlinear operations.
    pub fn render_region(
        &self,
        input: &[f32],
        output: &mut [f32],
        region: ProfileRegion,
        cancelled: &AtomicBool,
    ) -> Result<()> {
        ensure!(
            region
                .full_size
                .iter()
                .all(|v| (1..=MAX_IMAGE_DIMENSION).contains(v)),
            "Invalid full photograph dimensions"
        );
        for axis in 0..2 {
            ensure!(
                region.size[axis] > 0
                    && u64::from(region.origin[axis]) + u64::from(region.size[axis])
                        <= u64::from(region.full_size[axis]),
                "SDR scene crop exceeds full photograph"
            );
        }
        let samples = (region.size[0] as usize)
            .checked_mul(region.size[1] as usize)
            .and_then(|v| v.checked_mul(3))
            .ok_or_else(|| anyhow::anyhow!("SDR scene crop overflows address space"))?;
        ensure!(
            input.len() == samples && output.len() == samples,
            "Incorrect SDR scene buffer extent"
        );
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "SDR scene rendering cancelled"
        );
        let width = region.size[0] as usize;
        output
            .par_chunks_mut(width * 3)
            .zip(input.par_chunks(width * 3))
            .enumerate()
            .try_for_each(|(y, (dst, src))| -> Result<()> {
                let v = (region.origin[1] as f32 + y as f32 + 0.5) / region.full_size[1] as f32;
                for x in 0..width {
                    if x % 64 == 0 {
                        ensure!(
                            !cancelled.load(Ordering::Relaxed),
                            "SDR scene rendering cancelled"
                        );
                    }
                    let p = [src[3 * x], src[3 * x + 1], src[3 * x + 2]];
                    ensure!(p.iter().all(|v| v.is_finite()), "Nonfinite SDR scene input");
                    let u = (region.origin[0] as f32 + x as f32 + 0.5) / region.full_size[0] as f32;
                    dst[3 * x..3 * x + 3].copy_from_slice(&self.develop_inner(p, [u, v])?);
                }
                Ok(())
            })
    }
}

/// Blend two COMPLETE development branches in the same caller-declared linear
/// presentation domain. `baseline` is the existing developed view, not raw RGB.
/// Amount zero returns its exact bits without evaluating `candidate`, allowing
/// the caller to bypass unresolved assets, field loading and inference entirely.
/// Amount one returns exact candidate bits. Intermediate values perform only
/// this linear blend; analysis and field construction belong outside pixel work.
/// This boundary is not evidence that the app currently uses this path.
pub fn blend_sdr_scene_pixel(
    baseline: [f32; 3],
    amount: f32,
    candidate: impl FnOnce() -> Result<[f32; 3]>,
) -> Result<[f32; 3]> {
    ensure!(
        amount.is_finite() && (0.0..=1.0).contains(&amount),
        "SDR scene Amount must be in 0..1"
    );
    ensure!(
        baseline.iter().all(|v| v.is_finite()),
        "Nonfinite SDR scene baseline"
    );
    if amount == 0. {
        return Ok(baseline);
    }
    let candidate = candidate()?;
    ensure!(
        candidate.iter().all(|v| v.is_finite()),
        "Nonfinite SDR scene candidate"
    );
    if amount == 1. {
        return Ok(candidate);
    }
    let blended = std::array::from_fn(|c| baseline[c] * (1. - amount) + candidate[c] * amount);
    ensure!(
        blended.iter().all(|v| v.is_finite()),
        "Nonfinite SDR scene blend"
    );
    Ok(blended)
}

#[inline]
fn cap_sdr_rgb(p: [f32; 3]) -> [f32; 3] {
    let mut order = [0usize, 1, 2];
    order.sort_by(|a, b| p[*a].total_cmp(&p[*b]));
    let [low, middle, high] = order.map(|i| p[i]);
    let a = low.min(1.);
    let b = high.min(1.);
    let center = if high <= 1. {
        middle
    } else if middle == low {
        a
    } else if middle == high {
        b
    } else {
        a + (middle - low) / (high - low).max(1e-8) * (b - a)
    };
    let mut out = p;
    out[order[0]] = a;
    out[order[1]] = center;
    out[order[2]] = b;
    out
}
