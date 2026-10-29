//! Opt-in, bounded coefficient-domain fusion of multiple focus brackets.
//!
//! This is a child of the pyramid module so it shares the ordinary energy and
//! weight operators. The legacy BandMerge entry points do not call this module.
//! Each source is prepared once; groups retain sufficient statistics, never a
//! volume of aligned frames. Noise is injected and propagated, not re-estimated.
//!
//! The preparation helper retains the ordinary per-frame beta approximation.
//! Group variance is a frozen-membership temporal prediction, not confidence in
//! scene truth or in the absence of shared fixed-pattern noise.

use std::collections::{BTreeMap, BTreeSet};
use std::mem::size_of;

use rayon::prelude::*;
use thiserror::Error;

use super::{
    AdmissionMode, BandGain, BaseBand, Fallback, Hull, LevelSize, MergeConfig, Pyramid,
    SOFT_NUMERATOR_SCALE, SelectMode, Workspace, band_energy, level_sizes, select_weight,
    significance_floor, smooth5,
};
use crate::precision_mean::{PrecisionMean, PrecisionResult};
use crate::{CfaPlane, noise::NoiseModel};

#[path = "session-attribution.rs"]
mod attribution;
pub use attribution::{AttributionKind, BandAttribution, CoefficientAttribution};
use attribution::{DualAccumulator, DualSources, SourceMoments};

/// Caller-interned identity of an independent acquisition, not a pathname.
/// Aliases/copies of one RAW must have the same acquisition identity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct SourceKey {
    pub acquisition: u64,
    pub bracket: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GroupMode {
    /// Compatible corresponding observations may form one focus observation.
    Repeat,
    /// Each source enters ordinary noise-gated focus selection independently.
    Combine,
}

/// The observation used for cross-group focus weighting. Delivered coefficients
/// and their propagated noise always retain the requested repeat estimator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GroupFocusReference {
    /// Score the delivered mean using its own propagated temporal variance.
    Delivered,
    /// Freeze the focus score to the equal-observation group mean and its
    /// injected, propagated variance. This separates a precision-mean change
    /// from its feedback into the cross-focus selector. It does not make those
    /// focus decisions independent of the participating measurements.
    EqualObservation,
}

#[derive(Debug, Clone, Copy)]
pub struct GroupPolicy {
    pub mode: GroupMode,
    /// Appearance fallback only. The automatic geometry anchor is not a primary.
    pub primary: Option<usize>,
    /// Local residual RMS in units of propagated temporal standard deviation.
    /// This is an explicit policy threshold, not a calibrated probability.
    pub agreement_sigma: f32,
}

impl Default for GroupPolicy {
    fn default() -> Self {
        Self {
            mode: GroupMode::Repeat,
            primary: None,
            agreement_sigma: 4.0,
        }
    }
}

#[derive(Debug, Error)]
pub enum FusionError {
    #[error("unsupported session-fusion recipe: {0}")]
    UnsupportedRecipe(&'static str),
    #[error("invalid session-fusion input: {0}")]
    InvalidInput(&'static str),
    #[error("source acquisition {0} is duplicated; aliases are not independent noise")]
    DuplicateSource(u64),
    #[error("repeat group contains more than one source from bracket {0}")]
    DuplicateBracket(usize),
    #[error("session fusion has no completed sources")]
    Empty,
    #[error("session fusion contains sources from an unfinished group")]
    UnfinishedGroup,
    #[error("nonfinite arithmetic in session fusion")]
    Nonfinite,
}

type Result<T> = std::result::Result<T, FusionError>;

fn validate_config(width: usize, height: usize, cfg: MergeConfig) -> Result<Vec<LevelSize>> {
    if width == 0 || height == 0 || width.checked_mul(height).is_none() {
        return Err(FusionError::InvalidInput("invalid dimensions"));
    }
    if cfg.bands > 12 {
        return Err(FusionError::UnsupportedRecipe("more than 12 pyramid bands"));
    }
    if cfg.select != SelectMode::SoftPower
        || cfg.admission != AdmissionMode::HardFloor
        || cfg.base != BaseBand::Mean
        || cfg.fallback != Fallback::Mean
        || cfg.hull == Hull::PerLevel
    {
        return Err(FusionError::UnsupportedRecipe(
            "requires soft-power, hard-floor, mean base/fallback, input-range or unclamped hull",
        ));
    }
    if !cfg.gate.is_finite()
        || cfg.gate < 0.0
        || !cfg.exponent.is_finite()
        || cfg.exponent <= 0.0
        || cfg.exponent > super::MAX_EXPONENT
        || !cfg.sharpen_per_octave.is_finite()
        || cfg.sharpen_per_octave < 1.0
        || !cfg.significance_scale.is_finite()
        || cfg.significance_scale < 0.0
    {
        return Err(FusionError::InvalidInput("invalid merge parameters"));
    }
    Ok(level_sizes(width, height, cfg.bands))
}

/// Checked numeric/mask-buffer preflight for one serial session consumer.
///
/// No image buffers are allocated. `peak_bytes` conservatively retains source,
/// group and merge storage while reserving the larger of finish reconstruction
/// (including its returned planes) and an uncached white-noise gain probe.
/// Source-ID/diagnostic collections, allocator/thread overhead, native sampling,
/// decode/cache, demosaic and export buffers remain the caller's responsibility.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MemoryEstimate {
    pub prepared_source_bytes: usize,
    pub group_bytes: usize,
    pub merge_bytes: usize,
    pub finish_additional_bytes: usize,
    pub gain_probe_additional_bytes: usize,
    pub peak_bytes: usize,
}

fn byte_terms(terms: &[(usize, usize)]) -> Result<usize> {
    terms.iter().try_fold(0usize, |sum, &(count, multiplier)| {
        count
            .checked_mul(multiplier)
            .and_then(|term| sum.checked_add(term))
            .ok_or(FusionError::InvalidInput("workspace byte count overflows"))
    })
}

fn validate_policy(policy: GroupPolicy) -> Result<()> {
    if !policy.agreement_sigma.is_finite()
        || policy.agreement_sigma <= 0.0
        || policy.agreement_sigma > 1000.0
    {
        return Err(FusionError::InvalidInput("invalid agreement threshold"));
    }
    Ok(())
}

impl MemoryEstimate {
    pub fn estimate(
        width: usize,
        height: usize,
        cfg: MergeConfig,
        policy: GroupPolicy,
    ) -> Result<Self> {
        let sizes = validate_config(width, height, cfg)?;
        validate_policy(policy)?;
        let n = sizes[0].pixels();
        let p = sizes.iter().try_fold(0usize, |sum, size| {
            sum.checked_add(size.pixels())
                .ok_or(FusionError::InvalidInput("pyramid sample count overflows"))
        })?;
        // Four original planes + seven pyramids + workspace and scalar field.
        let prepared_source_bytes = byte_terms(&[
            (p, 7 * 4 + 5),
            (n, 7 * 4 + 1),
            (width, 4),
            (sizes.len(), 12),
        ])?;
        let group_fields = 21 + usize::from(policy.primary.is_some()) * 10;
        // One extra full f32 field conservatively bounds group working storage.
        let group_bytes = byte_terms(&[(p, group_fields * 4), (n, 6 * 4 + 2), (width, 4)])?;
        let merge_bytes = byte_terms(&[(p, 15 * 4 + 1), (n, 8 * 4 + 1)])?;
        // Reconstruction workspace, one pyramid, four returned color planes,
        // the level-mask pyramid and simultaneously live old/new support masks.
        let finish_additional_bytes = byte_terms(&[(p, 4 + 1), (n, 6 * 4 + 2), (width, 4)])?;
        // BandGain::measure may be uncached. Match its actual-depth probe, not
        // cfg.bands (small images truncate their pyramid before that depth).
        let bands = sizes.len() - 1;
        let side = (super::MIN_LEVEL_EXTENT << bands).max(256);
        let probe_n = side.checked_mul(side).ok_or(FusionError::InvalidInput(
            "gain probe sample count overflows",
        ))?;
        let probe_p = level_sizes(side, side, bands)
            .iter()
            .try_fold(0usize, |sum, size| {
                sum.checked_add(size.pixels())
                    .ok_or(FusionError::InvalidInput("gain probe pyramid overflows"))
            })?;
        let gain_probe_additional_bytes = byte_terms(&[
            (probe_p, 4),
            (probe_n, 3 * 4),
            (side, 4),
            // f64 accumulated energy, usize counts and returned f32 beta.
            (sizes.len(), 8 + std::mem::size_of::<usize>() + 4),
        ])?;
        let peak_bytes = byte_terms(&[
            (prepared_source_bytes, 1),
            (group_bytes, 1),
            (merge_bytes, 1),
            (finish_additional_bytes.max(gain_probe_additional_bytes), 1),
        ])?;
        if peak_bytes > isize::MAX as usize {
            return Err(FusionError::InvalidInput(
                "workspace exceeds addressable allocation size",
            ));
        }
        Ok(Self {
            prepared_source_bytes,
            group_bytes,
            merge_bytes,
            finish_additional_bytes,
            gain_probe_additional_bytes,
            peak_bytes,
        })
    }
}

/// Conservative checked buffer reservation before allocating session workspaces.
pub fn workspace_bytes(
    width: usize,
    height: usize,
    cfg: MergeConfig,
    policy: GroupPolicy,
) -> Result<usize> {
    Ok(MemoryEstimate::estimate(width, height, cfg, policy)?.peak_bytes)
}

/// Additional opt-in storage: predicted noise pyramids/masks and bounded group
/// precision statistics. No source frame volume is retained.
pub fn precision_workspace_bytes(width: usize, height: usize, cfg: MergeConfig) -> Result<usize> {
    let sizes = validate_config(width, height, cfg)?;
    let p = sizes
        .iter()
        .try_fold(0usize, |sum, s| sum.checked_add(s.pixels()))
        .ok_or(FusionError::InvalidInput("precision size overflow"))?;
    byte_terms(&[(p, std::mem::size_of::<PrecisionMean>() + 10)])
}

/// Additional optional payload for group attribution, final-band accumulation
/// and simultaneously returned coefficient maps. Add this to both the baseline
/// and (if used) precision reservations. Caller collection overhead is separate.
pub fn attribution_workspace_bytes(
    width: usize,
    height: usize,
    cfg: MergeConfig,
    policy: GroupPolicy,
) -> Result<usize> {
    validate_policy(policy)?;
    let sizes = validate_config(width, height, cfg)?;
    let p = sizes
        .iter()
        .try_fold(0usize, |sum, s| sum.checked_add(s.pixels()))
        .ok_or(FusionError::InvalidInput("attribution size overflow"))?;
    let group = size_of::<DualSources>() * (1 + usize::from(policy.primary.is_some()));
    let bytes = byte_terms(&[(
        p,
        group + size_of::<DualAccumulator>() + size_of::<CoefficientAttribution>(),
    )])?;
    if bytes > isize::MAX as usize {
        return Err(FusionError::InvalidInput(
            "attribution exceeds addressable allocation size",
        ));
    }
    Ok(bytes)
}

#[derive(Debug)]
struct PreparedModel {
    noise: NoiseModel,
    gain: f32,
    beta: Vec<[f32; 2]>,
}

fn same_noise_model(a: &NoiseModel, b: &NoiseModel) -> bool {
    a.iso.to_bits() == b.iso.to_bits()
        && a.provenance == b.provenance
        && CfaPlane::ALL.iter().all(|&c| {
            let a = a.plane(c);
            let b = b.plane(c);
            a.gain_dn_per_e.to_bits() == b.gain_dn_per_e.to_bits()
                && a.read_noise_e.to_bits() == b.read_noise_e.to_bits()
                && a.levels.black.to_bits() == b.levels.black.to_bits()
                && a.levels.white.to_bits() == b.levels.white.to_bits()
        })
        && match (a.prnu(), b.prnu()) {
            (None, None) => true,
            (Some(a), Some(b)) => CfaPlane::ALL
                .iter()
                .all(|&c| a.kappa(c).to_bits() == b.kappa(c).to_bits()),
            _ => false,
        }
}

#[derive(Debug)]
struct PreparedPrecision {
    guide_acquisition: u64,
    variance: Pyramid,
    color_variance: Pyramid,
    support: Vec<Vec<bool>>,
    gaussian_support: Vec<Vec<bool>>,
}

/// Expected signal in this source's black-subtracted DN, frozen using original
/// acquisitions excluded from this entire repeat group. All guide taps must be
/// supported. A matching shape/visibility check remains the caller's job.
pub struct FrozenPrediction<'a> {
    pub acquisition: u64,
    pub signal: [&'a [f32]; 4],
    pub support: &'a [bool],
}

/// Reusable preparation storage for one source. Planes use [R, G1, B, G2].
#[derive(Debug)]
pub struct PreparedSource {
    key: Option<SourceKey>,
    model: Option<PreparedModel>,
    precision: Option<PreparedPrecision>,
    precision_ready: bool,
    sizes: Vec<LevelSize>,
    pixels: [Vec<f32>; 4],
    planes: [Pyramid; 4],
    green: Pyramid,
    variance: Pyramid,
    color_variance: Pyramid,
    gaussian_support: Vec<Vec<bool>>,
    gaussian_coverage: Vec<Vec<bool>>,
    coverage: Vec<Vec<bool>>,
    support: Vec<Vec<bool>>,
    energy_support: Vec<Vec<bool>>,
    input_support: Vec<bool>,
    gain: BandGain,
    workspace: Workspace,
    scalar: Vec<f32>,
}

impl PreparedSource {
    pub fn new(width: usize, height: usize, cfg: MergeConfig) -> Result<Self> {
        let sizes = validate_config(width, height, cfg)?;
        let n = sizes[0].pixels();
        Ok(Self {
            key: None,
            model: None,
            precision: None,
            precision_ready: false,
            pixels: std::array::from_fn(|_| vec![0.0; n]),
            planes: std::array::from_fn(|_| Pyramid::zeros(&sizes)),
            green: Pyramid::zeros(&sizes),
            variance: Pyramid::zeros(&sizes),
            color_variance: Pyramid::zeros(&sizes),
            gaussian_support: sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
            gaussian_coverage: sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
            coverage: sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
            support: sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
            energy_support: sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
            input_support: vec![false; n],
            gain: BandGain::measure(sizes.len() - 1),
            workspace: Workspace::new(&sizes),
            scalar: vec![0.0; n],
            sizes,
        })
    }

    /// Prepare black-subtracted, already gathered CFA planes.
    ///
    /// The caller supplies coverage AND clipping support for the complete gather
    /// footprint, including demosaic/CA taps where applicable. Unsupported samples
    /// are never trusted, even when their buffers contain plausible values.
    /// Photometric gain scales values by c and variances by c^2. It does not itself
    /// certify exposure equivalence or authorize averaging different lighting.
    #[allow(clippy::too_many_arguments)]
    pub fn prepare(
        &mut self,
        key: SourceKey,
        planes: [&[f32]; 4],
        noise: &NoiseModel,
        frame_beta: Option<&[f32]>,
        support: &[bool],
        photometric_gain: f32,
    ) -> Result<()> {
        self.prepare_with_noise_gains(
            key,
            planes,
            noise,
            frame_beta,
            frame_beta,
            support,
            photometric_gain,
        )
    }

    /// Prepare using distinct absolute band-noise gains for green luma and the
    /// maximum CFA-color variance bound. The ordinary `prepare` wrapper reuses
    /// one gain field, preserving its previous behavior.
    ///
    /// A native CFA gather can have different channel phases, so its green-luma
    /// gain need not bound any individual color. The caller should provide the
    /// largest per-color gain at each band as `color_beta`. Missing entries in
    /// either field independently use the white-noise band gain. These scalar
    /// gains retain the spatial variance approximation; they are not exact
    /// propagated covariance or evidence that the observations are independent.
    #[allow(clippy::too_many_arguments)]
    pub fn prepare_with_noise_gains(
        &mut self,
        key: SourceKey,
        planes: [&[f32]; 4],
        noise: &NoiseModel,
        frame_beta: Option<&[f32]>,
        color_beta: Option<&[f32]>,
        support: &[bool],
        photometric_gain: f32,
    ) -> Result<()> {
        self.prepare_with_masks(
            key,
            planes,
            noise,
            frame_beta,
            color_beta,
            support,
            support,
            photometric_gain,
        )
    }

    /// Separate geometric coverage from uncensored statistical eligibility.
    /// Clipped samples retain their actual values in coverage-valid pyramids,
    /// but never enter repeat means, compatibility evidence or focus weights.
    /// Coverage-only coefficients may fill a final band only if every source
    /// lacks an uncensored contribution there. This preserves saturation as
    /// display content; it does not recover highlights or claim a noise gain.
    #[allow(clippy::too_many_arguments)]
    pub fn prepare_with_masks(
        &mut self,
        key: SourceKey,
        planes: [&[f32]; 4],
        noise: &NoiseModel,
        frame_beta: Option<&[f32]>,
        color_beta: Option<&[f32]>,
        coverage: &[bool],
        uncensored: &[bool],
        photometric_gain: f32,
    ) -> Result<()> {
        self.key = None;
        self.precision_ready = false;
        let n = self.sizes[0].pixels();
        if coverage.len() != n || uncensored.len() != n || planes.iter().any(|p| p.len() != n) {
            return Err(FusionError::InvalidInput("source dimensions differ"));
        }
        if uncensored
            .iter()
            .zip(coverage)
            .any(|(&valid, &covered)| valid && !covered)
        {
            return Err(FusionError::InvalidInput(
                "uncensored sample has no coverage",
            ));
        }
        if !photometric_gain.is_finite() || photometric_gain <= 0.0 {
            return Err(FusionError::InvalidInput(
                "photometric gain must be finite and positive",
            ));
        }
        if [frame_beta, color_beta]
            .into_iter()
            .flatten()
            .any(|b| b.iter().any(|v| !v.is_finite() || *v < 0.0))
        {
            return Err(FusionError::InvalidInput("invalid band-noise gain"));
        }
        for c in CfaPlane::ALL {
            let p = noise.plane(c);
            if !p.gain_dn_per_e.is_finite()
                || p.gain_dn_per_e < 0.0
                || !p.read_noise_e.is_finite()
                || p.read_noise_e < 0.0
            {
                return Err(FusionError::InvalidInput("invalid injected noise model"));
            }
        }
        let gain2 = photometric_gain * photometric_gain;
        if !gain2.is_finite() {
            return Err(FusionError::Nonfinite);
        }
        self.input_support.copy_from_slice(coverage);
        for (c, input) in planes.iter().enumerate() {
            for i in 0..n {
                let value = if coverage[i] {
                    input[i] * photometric_gain
                } else {
                    0.0
                };
                if !value.is_finite() {
                    return Err(FusionError::InvalidInput(
                        "nonfinite supported source sample",
                    ));
                }
                self.pixels[c][i] = value;
            }
            self.planes[c].build(&self.pixels[c], &mut self.workspace);
        }
        for i in 0..n {
            self.scalar[i] = (self.pixels[1][i] + self.pixels[3][i]) * 0.5;
        }
        self.green.build(&self.scalar, &mut self.workspace);
        for i in 0..n {
            self.scalar[i] = if coverage[i] {
                let luma = (planes[1][i] + planes[3][i]) * 0.5;
                let sigma = noise.green_luma_sigma(luma);
                sigma * sigma * gain2
            } else {
                0.0
            };
        }
        self.variance
            .build_gaussian(&self.scalar, &mut self.workspace);
        for i in 0..n {
            self.scalar[i] = if coverage[i] {
                CfaPlane::ALL
                    .iter()
                    .enumerate()
                    .map(|(c, p)| noise.plane(*p).variance(planes[c][i]) * gain2)
                    .fold(0.0_f32, f32::max)
            } else {
                0.0
            };
        }
        self.color_variance
            .build_gaussian(&self.scalar, &mut self.workspace);
        for k in 0..self.sizes.len() {
            let beta = frame_beta
                .and_then(|b| b.get(k))
                .copied()
                .unwrap_or(self.gain.beta(k));
            let color_beta = color_beta
                .and_then(|b| b.get(k))
                .copied()
                .unwrap_or(self.gain.beta(k));
            for (field, gain) in [
                (self.variance.level_mut(k), beta),
                (self.color_variance.level_mut(k), color_beta),
            ] {
                for value in field {
                    *value *= gain;
                    if !value.is_finite() {
                        return Err(FusionError::Nonfinite);
                    }
                }
            }
            if self
                .planes
                .iter()
                .any(|p| p.level(k).iter().any(|v| !v.is_finite()))
                || self.green.level(k).iter().any(|v| !v.is_finite())
            {
                return Err(FusionError::Nonfinite);
            }
        }
        self.gaussian_support[0].copy_from_slice(uncensored);
        self.gaussian_coverage[0].copy_from_slice(coverage);
        for k in 1..self.sizes.len() {
            let (before, after) = self.gaussian_support.split_at_mut(k);
            reduce_support(&before[k - 1], self.sizes[k - 1], &mut after[0]);
            let (before, after) = self.gaussian_coverage.split_at_mut(k);
            reduce_support(&before[k - 1], self.sizes[k - 1], &mut after[0]);
        }
        let last = self.sizes.len() - 1;
        for k in 0..=last {
            if k == last {
                self.support[k].copy_from_slice(&self.gaussian_support[k]);
                self.coverage[k].copy_from_slice(&self.gaussian_coverage[k]);
            } else {
                expand_support(
                    &self.gaussian_support[k + 1],
                    self.sizes[k + 1],
                    &mut self.support[k],
                    self.sizes[k],
                );
                for (v, g) in self.support[k].iter_mut().zip(&self.gaussian_support[k]) {
                    *v &= *g;
                }
                expand_support(
                    &self.gaussian_coverage[k + 1],
                    self.sizes[k + 1],
                    &mut self.coverage[k],
                    self.sizes[k],
                );
                for (v, g) in self.coverage[k].iter_mut().zip(&self.gaussian_coverage[k]) {
                    *v &= *g;
                }
            }
            erode_support(&self.support[k], self.sizes[k], &mut self.energy_support[k]);
        }
        self.model = Some(PreparedModel {
            noise: noise.clone(),
            gain: photometric_gain,
            beta: (0..self.sizes.len())
                .map(|k| {
                    [
                        frame_beta
                            .and_then(|v| v.get(k))
                            .copied()
                            .unwrap_or(self.gain.beta(k)),
                        color_beta
                            .and_then(|v| v.get(k))
                            .copied()
                            .unwrap_or(self.gain.beta(k)),
                    ]
                })
                .collect(),
        });
        self.key = Some(key);
        Ok(())
    }

    pub fn key(&self) -> Option<SourceKey> {
        self.key
    }

    /// Add a separate fixed-guide precision model. Existing focus and residual
    /// admission continue to use their original model; the new variance is used
    /// only for averaging already-compatible observations and its energy floor.
    #[allow(clippy::too_many_arguments)]
    pub fn predict_precision(
        &mut self,
        prediction: FrozenPrediction<'_>,
        noise: &NoiseModel,
        gain: f32,
        frame_beta: Option<&[f32]>,
        color_beta: Option<&[f32]>,
    ) -> Result<()> {
        self.precision_ready = false;
        let key = self.key.ok_or(FusionError::InvalidInput(
            "prediction needs prepared source",
        ))?;
        let n = self.sizes[0].pixels();
        if prediction.acquisition == key.acquisition
            || prediction.signal.iter().any(|p| p.len() != n)
            || prediction.support.len() != n
            || !gain.is_finite()
            || gain <= 0.0
            || !(gain * gain).is_finite()
        {
            return Err(FusionError::InvalidInput(
                "invalid independent precision prediction",
            ));
        }
        for i in 0..n {
            if prediction.support[i] && prediction.signal.iter().any(|p| !p[i].is_finite()) {
                return Err(FusionError::InvalidInput("nonfinite precision guide"));
            }
        }
        if [frame_beta, color_beta]
            .into_iter()
            .flatten()
            .any(|b| b.iter().any(|v| !v.is_finite() || *v < 0.0))
        {
            return Err(FusionError::InvalidInput("invalid precision band gain"));
        }
        let model = self
            .model
            .as_ref()
            .ok_or(FusionError::InvalidInput("missing prepared model"))?;
        let same_beta = model.beta.iter().enumerate().all(|(k, expected)| {
            [frame_beta, color_beta]
                .into_iter()
                .enumerate()
                .all(|(c, supplied)| {
                    supplied
                        .and_then(|v| v.get(k))
                        .copied()
                        .unwrap_or(self.gain.beta(k))
                        .to_bits()
                        == expected[c].to_bits()
                })
        });
        if !same_noise_model(&model.noise, noise)
            || model.gain.to_bits() != gain.to_bits()
            || !same_beta
        {
            return Err(FusionError::InvalidInput(
                "precision model differs from prepared source",
            ));
        }
        let p = self.precision.get_or_insert_with(|| PreparedPrecision {
            guide_acquisition: prediction.acquisition,
            variance: Pyramid::zeros(&self.sizes),
            color_variance: Pyramid::zeros(&self.sizes),
            support: self.sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
            gaussian_support: self.sizes.iter().map(|s| vec![false; s.pixels()]).collect(),
        });
        p.guide_acquisition = prediction.acquisition;
        for i in 0..n {
            let s = (prediction.signal[1][i] + prediction.signal[3][i]) * 0.5;
            let sigma = noise.green_luma_sigma(s);
            self.scalar[i] = if prediction.support[i] {
                sigma * sigma * gain * gain
            } else {
                0.0
            };
        }
        p.variance.build_gaussian(&self.scalar, &mut self.workspace);
        for i in 0..n {
            self.scalar[i] = if prediction.support[i] {
                CfaPlane::ALL
                    .iter()
                    .enumerate()
                    .map(|(c, plane)| {
                        noise.plane(*plane).variance(prediction.signal[c][i]) * gain * gain
                    })
                    .fold(0.0_f32, f32::max)
            } else {
                0.0
            };
        }
        p.color_variance
            .build_gaussian(&self.scalar, &mut self.workspace);
        // Original Gaussian support remains live in SessionMerge's hull logic.
        // Guide support has its own bounded scratch and cannot relabel originals.
        p.gaussian_support[0].copy_from_slice(prediction.support);
        for k in 1..self.sizes.len() {
            let (before, after) = p.gaussian_support.split_at_mut(k);
            reduce_support(&before[k - 1], self.sizes[k - 1], &mut after[0]);
        }
        let last = self.sizes.len() - 1;
        for k in 0..=last {
            if k == last {
                p.support[k].copy_from_slice(&p.gaussian_support[k]);
            } else {
                expand_support(
                    &p.gaussian_support[k + 1],
                    self.sizes[k + 1],
                    &mut p.support[k],
                    self.sizes[k],
                );
                for (v, g) in p.support[k].iter_mut().zip(&p.gaussian_support[k]) {
                    *v &= *g;
                }
            }
            for (field, beta) in [
                (p.variance.level_mut(k), frame_beta),
                (p.color_variance.level_mut(k), color_beta),
            ] {
                let b = beta
                    .and_then(|v| v.get(k))
                    .copied()
                    .unwrap_or(self.gain.beta(k));
                for v in field {
                    *v *= b;
                    if !v.is_finite() || *v < 0.0 {
                        return Err(FusionError::Nonfinite);
                    }
                }
            }
        }
        self.precision_ready = true;
        Ok(())
    }

    pub fn sizes(&self) -> &[LevelSize] {
        &self.sizes
    }

    pub fn band(&self, level: usize) -> PreparedBand<'_> {
        PreparedBand {
            coefficients: std::array::from_fn(|c| self.planes[c].level(level)),
            green: self.green.level(level),
            temporal_variance: self.variance.level(level),
            color_variance_bound: self.color_variance.level(level),
            support: &self.support[level],
            coverage: &self.coverage[level],
        }
    }

    /// Owned numeric/mask buffer bytes, excluding allocator and collection overhead.
    pub fn buffer_bytes(&self) -> usize {
        let p: usize = self.sizes.iter().map(LevelSize::pixels).sum();
        let n = self.sizes[0].pixels();
        (7 * p + 7 * n + self.sizes[0].width) * 4
            + 5 * p
            + n
            + usize::from(self.precision.is_some()) * 10 * p
            + self
                .model
                .as_ref()
                .map_or(0, |m| m.beta.len() * size_of::<[f32; 2]>())
    }
}

/// Borrowed prepared coefficients, useful for diagnostics and independent tests.
pub struct PreparedBand<'a> {
    pub coefficients: [&'a [f32]; 4],
    pub green: &'a [f32],
    pub temporal_variance: &'a [f32],
    pub color_variance_bound: &'a [f32],
    /// Uncensored dependency support for statistical use.
    pub support: &'a [bool],
    /// Genuine dependency coverage, including preserved censored display values.
    pub coverage: &'a [bool],
}

// Parallelism is only across independent coefficients. A source/group call
// joins before the next one, preserving every pixel's accumulation order.
const ACCUMULATION_CHUNK: usize = 4096;

fn channel_chunks_mut<T: Send>(
    values: &mut [Vec<T>; 4],
    chunk: usize,
) -> impl IndexedParallelIterator<Item = [&mut [T]; 4]> {
    let [a, b, c, d] = values;
    a.par_chunks_mut(chunk)
        .zip(b.par_chunks_mut(chunk))
        .zip(c.par_chunks_mut(chunk))
        .zip(d.par_chunks_mut(chunk))
        .map(|(((a, b), c), d)| [a, b, c, d])
}

struct ContributionChunk<'a> {
    numerator: [&'a mut [f32]; 4],
    plain: [&'a mut [f32]; 4],
    denominator: &'a mut [f32],
    count: &'a mut [f32],
}
impl ContributionChunk<'_> {
    fn add(&mut self, i: usize, coefficients: [f32; 4], weight: f32) {
        self.denominator[i] += weight;
        self.count[i] += 1.0;
        for (c, value) in coefficients.iter().enumerate() {
            self.numerator[c][i] += weight * (*value / SOFT_NUMERATOR_SCALE);
            self.plain[c][i] += value;
        }
    }
}

type GroupChunk<'a> = (
    [&'a mut [f32]; 4],
    [&'a mut [f32]; 4],
    &'a mut [f32],
    &'a mut [f32],
    &'a mut [u32],
    ContributionChunk<'a>,
);

#[derive(Debug)]
struct Contributions {
    numerator: [Vec<f32>; 4],
    plain: [Vec<f32>; 4],
    denominator: Vec<f32>,
    count: Vec<f32>,
}

impl Contributions {
    fn zeros(n: usize) -> Self {
        Self {
            numerator: std::array::from_fn(|_| vec![0.0; n]),
            plain: std::array::from_fn(|_| vec![0.0; n]),
            denominator: vec![0.0; n],
            count: vec![0.0; n],
        }
    }

    fn clear(&mut self) {
        for values in self.numerator.iter_mut().chain(&mut self.plain) {
            values.fill(0.0);
        }
        self.denominator.fill(0.0);
        self.count.fill(0.0);
    }

    fn add(&mut self, i: usize, coefficients: [f32; 4], weight: f32) {
        self.denominator[i] += weight;
        self.count[i] += 1.0;
        for (c, value) in coefficients.iter().enumerate() {
            self.numerator[c][i] += weight * (*value / SOFT_NUMERATOR_SCALE);
            self.plain[c][i] += value;
        }
    }

    fn chunks_mut(
        &mut self,
        chunk: usize,
    ) -> impl IndexedParallelIterator<Item = ContributionChunk<'_>> {
        let Self {
            numerator,
            plain,
            denominator,
            count,
        } = self;
        (
            channel_chunks_mut(numerator, chunk),
            channel_chunks_mut(plain, chunk),
            denominator.par_chunks_mut(chunk),
            count.par_chunks_mut(chunk),
        )
            .into_par_iter()
            .map(|(numerator, plain, denominator, count)| ContributionChunk {
                numerator,
                plain,
                denominator,
                count,
            })
    }

    fn absorb_at(&mut self, i: usize, other: &Self) {
        self.denominator[i] += other.denominator[i];
        self.count[i] += other.count[i];
        for c in 0..4 {
            self.numerator[c][i] += other.numerator[c][i];
            self.plain[c][i] += other.plain[c][i];
        }
    }

    fn finite(&self) -> bool {
        self.numerator
            .iter()
            .chain(&self.plain)
            .flatten()
            .chain(&self.denominator)
            .chain(&self.count)
            .all(|v| v.is_finite())
    }
}

#[derive(Debug)]
struct GroupAttribution {
    ordinary: Vec<DualSources>,
    primary: Option<Vec<DualSources>>,
}

impl GroupAttribution {
    fn zeros(n: usize, primary: bool) -> Self {
        Self {
            ordinary: vec![DualSources::default(); n],
            primary: primary.then(|| vec![DualSources::default(); n]),
        }
    }

    fn clear(&mut self) {
        self.ordinary.fill(DualSources::default());
        if let Some(p) = &mut self.primary {
            p.fill(DualSources::default());
        }
    }

    fn buffer_bytes(&self) -> usize {
        (self.ordinary.len() + self.primary.as_ref().map_or(0, Vec::len)) * size_of::<DualSources>()
    }
}

#[derive(Debug)]
struct GroupLevel {
    mean: [Vec<f32>; 4],
    m2: [Vec<f32>; 4],
    variance_sum: Vec<f32>,
    color_variance_sum: Vec<f32>,
    count: Vec<u32>,
    ordinary: Contributions,
    primary: Option<Contributions>,
    precision: Option<Vec<PrecisionMean>>,
    attribution: Option<GroupAttribution>,
}

impl GroupLevel {
    fn precision_at(&self, i: usize) -> Option<PrecisionResult> {
        self.precision
            .as_ref()
            .and_then(|p| p[i].result())
            .filter(|p| p.count == self.count[i])
    }
    fn zeros(n: usize, primary: bool, precision: bool, attribution: bool) -> Self {
        Self {
            mean: std::array::from_fn(|_| vec![0.0; n]),
            m2: std::array::from_fn(|_| vec![0.0; n]),
            variance_sum: vec![0.0; n],
            color_variance_sum: vec![0.0; n],
            count: vec![0; n],
            ordinary: Contributions::zeros(n),
            primary: primary.then(|| Contributions::zeros(n)),
            precision: precision.then(|| vec![PrecisionMean::default(); n]),
            attribution: attribution.then(|| GroupAttribution::zeros(n, primary)),
        }
    }

    fn clear(&mut self) {
        for v in self.mean.iter_mut().chain(&mut self.m2) {
            v.fill(0.0);
        }
        self.variance_sum.fill(0.0);
        self.color_variance_sum.fill(0.0);
        self.count.fill(0);
        self.ordinary.clear();
        if let Some(p) = &mut self.precision {
            p.fill(PrecisionMean::default());
        }
        if let Some(a) = &mut self.attribution {
            a.clear();
        }
        if let Some(p) = &mut self.primary {
            p.clear();
        }
    }
}

/// Reusable sufficient statistics for a focus group. Do not change its policy
/// while a group is in progress. Layer exports use separate SessionMerge values.
#[derive(Debug)]
pub struct GroupWorkspace {
    sizes: Vec<LevelSize>,
    cfg: MergeConfig,
    policy: GroupPolicy,
    levels: Vec<GroupLevel>,
    sources: BTreeSet<SourceKey>,
    guide_ids: BTreeSet<u64>,
    energy: Vec<f32>,
    scratch: Vec<f32>,
    residual: Vec<f32>,
    residual_noise: Vec<f32>,
    grouped_variance: Vec<f32>,
    valid: Vec<bool>,
    guarded: Vec<bool>,
}

impl GroupWorkspace {
    pub fn new(width: usize, height: usize, cfg: MergeConfig, policy: GroupPolicy) -> Result<Self> {
        Self::new_with_precision(width, height, cfg, policy, false)
    }

    pub fn new_with_precision(
        width: usize,
        height: usize,
        cfg: MergeConfig,
        policy: GroupPolicy,
        precision: bool,
    ) -> Result<Self> {
        Self::new_with_options(width, height, cfg, policy, precision, false)
    }

    /// Opt-in coefficient attribution is orthogonal to precision weighting.
    /// Reserve attribution_workspace_bytes before enabling it on a consumer.
    pub fn new_with_options(
        width: usize,
        height: usize,
        cfg: MergeConfig,
        policy: GroupPolicy,
        precision: bool,
        attribution: bool,
    ) -> Result<Self> {
        let sizes = validate_config(width, height, cfg)?;
        validate_policy(policy)?;
        let n = sizes[0].pixels();
        Ok(Self {
            levels: sizes
                .iter()
                .map(|s| {
                    GroupLevel::zeros(s.pixels(), policy.primary.is_some(), precision, attribution)
                })
                .collect(),
            cfg,
            policy,
            sources: BTreeSet::new(),
            guide_ids: BTreeSet::new(),
            energy: vec![0.0; n],
            scratch: vec![0.0; n + sizes[0].width],
            residual: vec![0.0; n],
            residual_noise: vec![0.0; n],
            grouped_variance: vec![0.0; n],
            valid: vec![false; n],
            guarded: vec![false; n],
            sizes,
        })
    }

    pub fn source_count(&self) -> usize {
        self.sources.len()
    }

    fn add(&mut self, source: &PreparedSource) -> Result<()> {
        let key = source
            .key
            .ok_or(FusionError::InvalidInput("source not prepared"))?;
        if self.guide_ids.contains(&key.acquisition) {
            return Err(FusionError::InvalidInput(
                "precision guide is a member of its weighted group",
            ));
        }
        let guide_id = if source.precision_ready && self.levels[0].precision.is_some() {
            let id = source.precision.as_ref().expect("ready").guide_acquisition;
            if self.sources.iter().any(|s| s.acquisition == id) || key.acquisition == id {
                return Err(FusionError::InvalidInput(
                    "precision guide is a member of its weighted group",
                ));
            }
            Some(id)
        } else {
            None
        };
        if self
            .sources
            .iter()
            .any(|s| s.acquisition == key.acquisition)
        {
            return Err(FusionError::DuplicateSource(key.acquisition));
        }
        if self.policy.mode == GroupMode::Repeat
            && self.sources.iter().any(|s| s.bracket == key.bracket)
        {
            return Err(FusionError::DuplicateBracket(key.bracket));
        }
        if self.sources.len() >= u32::MAX as usize {
            return Err(FusionError::InvalidInput("too many group members"));
        }
        if let Some(id) = guide_id {
            self.guide_ids.insert(id);
        }
        self.sources.insert(key);
        let bands = self.sizes.len() - 1;
        for k in 0..self.sizes.len() {
            let sz = self.sizes[k];
            let n = sz.pixels();
            let is_mean = k == bands || k + self.cfg.mean_coarse >= bands;
            if !is_mean {
                band_energy(
                    source.green.level(k),
                    sz,
                    &mut self.energy[..n],
                    &mut self.scratch,
                );
            }
            let GroupLevel {
                mean,
                m2,
                variance_sum,
                color_variance_sum,
                count,
                ordinary,
                primary,
                precision,
                attribution,
            } = &mut self.levels[k];
            let chunks = (
                channel_chunks_mut(mean, ACCUMULATION_CHUNK),
                channel_chunks_mut(m2, ACCUMULATION_CHUNK),
                variance_sum.par_chunks_mut(ACCUMULATION_CHUNK),
                color_variance_sum.par_chunks_mut(ACCUMULATION_CHUNK),
                count.par_chunks_mut(ACCUMULATION_CHUNK),
                ordinary.chunks_mut(ACCUMULATION_CHUNK),
            )
                .into_par_iter();
            let cfg = self.cfg;
            let energy = &self.energy;
            let accumulate =
                |block: usize,
                 fields: GroupChunk<'_>,
                 mut primary: Option<ContributionChunk<'_>>| {
                    let (mean, m2, variance_sum, color_variance_sum, counts, mut ordinary) = fields;
                    let begin = block * ACCUMULATION_CHUNK;
                    for j in 0..counts.len() {
                        let i = begin + j;
                        if !source.support[k][i] {
                            continue;
                        }
                        let coefficients = std::array::from_fn(|c| source.planes[c].level(k)[i]);
                        let weight = if is_mean || !source.energy_support[k][i] {
                            0.0
                        } else {
                            ordinary_weight(cfg, k, bands, energy[i], source.variance.level(k)[i])
                        };
                        ordinary.add(j, coefficients, weight);
                        if let Some(primary) = &mut primary {
                            primary.add(j, coefficients, weight);
                        }
                        counts[j] += 1;
                        let count = counts[j] as f32;
                        for (c, value) in coefficients.iter().enumerate() {
                            let delta = *value - mean[c][j];
                            mean[c][j] += delta / count;
                            m2[c][j] += delta * (*value - mean[c][j]);
                        }
                        variance_sum[j] += source.variance.level(k)[i];
                        color_variance_sum[j] += source.color_variance.level(k)[i];
                    }
                };
            if let Some(primary) = primary
                .as_mut()
                .filter(|_| self.policy.primary == Some(key.bracket))
            {
                chunks
                    .zip(primary.chunks_mut(ACCUMULATION_CHUNK))
                    .enumerate()
                    .for_each(|(block, (fields, primary))| {
                        accumulate(block, fields, Some(primary))
                    });
            } else {
                chunks
                    .enumerate()
                    .for_each(|(block, fields)| accumulate(block, fields, None));
            }
            if let Some(a) = attribution {
                let is_primary = self.policy.primary == Some(key.bracket);
                for i in 0..n {
                    if !source.support[k][i] {
                        continue;
                    }
                    let weight = if is_mean || !source.energy_support[k][i] {
                        0.0
                    } else {
                        ordinary_weight(
                            self.cfg,
                            k,
                            bands,
                            self.energy[i],
                            source.variance.level(k)[i],
                        )
                    };
                    let moment = SourceMoments::single(
                        key.acquisition,
                        [
                            source.variance.level(k)[i],
                            source.color_variance.level(k)[i],
                        ],
                        is_primary,
                    );
                    a.ordinary[i].add_source(moment, weight);
                    if let Some(primary) = a.primary.as_mut().filter(|_| is_primary) {
                        primary[i].add_source(moment, weight);
                    }
                }
            }
            if let Some(values) = precision.as_mut().filter(|_| source.precision_ready) {
                let predicted = source.precision.as_ref().expect("ready");
                let primary = self.policy.primary == Some(key.bracket);
                let source_id = key.acquisition;
                values
                    .par_iter_mut()
                    .enumerate()
                    .try_for_each(|(i, value)| -> Result<()> {
                        if source.support[k][i] && predicted.support[k][i] {
                            value
                                .push(
                                    std::array::from_fn(|c| source.planes[c].level(k)[i]),
                                    predicted.variance.level(k)[i],
                                    [
                                        predicted.variance.level(k)[i],
                                        predicted.color_variance.level(k)[i],
                                    ],
                                    source_id,
                                    primary,
                                )
                                .map_err(FusionError::InvalidInput)?;
                        }
                        Ok(())
                    })?;
            }
        }
        Ok(())
    }

    fn clear(&mut self) {
        self.sources.clear();
        self.guide_ids.clear();
        for level in &mut self.levels {
            level.clear();
        }
    }

    pub fn buffer_bytes(&self) -> usize {
        let p: usize = self.sizes.iter().map(LevelSize::pixels).sum();
        let n = self.sizes[0].pixels();
        let per_level = 21 + usize::from(self.policy.primary.is_some()) * 10;
        (per_level * p + 6 * n + self.sizes[0].width) * 4
            + 2 * n
            + self
                .levels
                .iter()
                .filter_map(|l| l.precision.as_ref())
                .map(|p| p.capacity() * std::mem::size_of::<PrecisionMean>())
                .sum::<usize>()
            + self
                .levels
                .iter()
                .filter_map(|l| l.attribution.as_ref())
                .map(GroupAttribution::buffer_bytes)
                .sum::<usize>()
    }
}

fn ordinary_weight(cfg: MergeConfig, k: usize, bands: usize, energy: f32, variance: f32) -> f32 {
    let floor = cfg.gate * variance;
    select_weight(
        (energy - floor).max(0.0),
        floor,
        cfg.exponent_at(k, bands),
        significance_floor(cfg.gate) * cfg.significance_scale,
    )
}

#[derive(Debug, Clone, Default)]
pub struct LevelDiagnostics {
    pub averaged_coefficients: u64,
    pub precision_averaged_coefficients: u64,
    pub missing_prediction_coefficients: u64,
    pub single_source_coefficients: u64,
    pub primary_fallback_coefficients: u64,
    pub ordinary_fallback_coefficients: u64,
    pub uncovered_coefficients: u64,
    /// Final-band counts, populated by finish, with no precision/noise-gain claim.
    pub saturated_fallback_coefficients: u64,
    pub primary_saturated_fallback_coefficients: u64,
    /// Counts describe accepted group means, not delivered resolution.
    pub averaged_independent_counts: BTreeMap<u32, u64>,
}

impl LevelDiagnostics {
    fn absorb(&mut self, other: &Self) {
        self.averaged_coefficients += other.averaged_coefficients;
        self.precision_averaged_coefficients += other.precision_averaged_coefficients;
        self.missing_prediction_coefficients += other.missing_prediction_coefficients;
        self.single_source_coefficients += other.single_source_coefficients;
        self.primary_fallback_coefficients += other.primary_fallback_coefficients;
        self.ordinary_fallback_coefficients += other.ordinary_fallback_coefficients;
        self.uncovered_coefficients += other.uncovered_coefficients;
        self.saturated_fallback_coefficients += other.saturated_fallback_coefficients;
        self.primary_saturated_fallback_coefficients +=
            other.primary_saturated_fallback_coefficients;
        for (k, v) in &other.averaged_independent_counts {
            *self.averaged_independent_counts.entry(*k).or_default() += v;
        }
    }
}

/// Display-only fallback, completely separate from statistical contributions.
/// A covering explicit primary replaces nonprimary sums; without one, the mean
/// is symmetric over original covering sources. No effective count is reported.
#[derive(Debug)]
struct CoverageFallback {
    sum: [Vec<f32>; 4],
    count: Vec<f32>,
    primary: Vec<bool>,
}
impl CoverageFallback {
    fn zeros(n: usize) -> Self {
        Self {
            sum: std::array::from_fn(|_| vec![0.0; n]),
            count: vec![0.0; n],
            primary: vec![false; n],
        }
    }
}

/// The new path has a denominator at every coefficient for fallback and coverage.
#[derive(Debug)]
pub struct SessionMerge {
    cfg: MergeConfig,
    sizes: Vec<LevelSize>,
    levels: Vec<Contributions>,
    coverage_fallback: Vec<CoverageFallback>,
    fallback_primary: Option<usize>,
    primary_policy_set: bool,
    hull_low: [Vec<f32>; 4],
    hull_high: [Vec<f32>; 4],
    hull_uncensored: Vec<bool>,
    source_ids: BTreeSet<u64>,
    folded_sources: usize,
    groups: usize,
    diagnostics: Vec<LevelDiagnostics>,
    attribution: Option<Vec<Vec<DualAccumulator>>>,
}

impl SessionMerge {
    pub fn new(width: usize, height: usize, cfg: MergeConfig) -> Result<Self> {
        Self::new_with_attribution(width, height, cfg, false)
    }

    pub fn new_with_attribution(
        width: usize,
        height: usize,
        cfg: MergeConfig,
        attribution: bool,
    ) -> Result<Self> {
        let sizes = validate_config(width, height, cfg)?;
        let n = sizes[0].pixels();
        Ok(Self {
            cfg,
            attribution: attribution.then(|| {
                sizes
                    .iter()
                    .map(|s| vec![DualAccumulator::default(); s.pixels()])
                    .collect()
            }),
            levels: sizes
                .iter()
                .map(|s| Contributions::zeros(s.pixels()))
                .collect(),
            coverage_fallback: sizes
                .iter()
                .map(|s| CoverageFallback::zeros(s.pixels()))
                .collect(),
            fallback_primary: None,
            primary_policy_set: false,
            hull_low: std::array::from_fn(|_| vec![f32::INFINITY; n]),
            hull_high: std::array::from_fn(|_| vec![f32::NEG_INFINITY; n]),
            hull_uncensored: vec![false; n],
            source_ids: BTreeSet::new(),
            folded_sources: 0,
            groups: 0,
            diagnostics: vec![LevelDiagnostics::default(); sizes.len()],
            sizes,
        })
    }

    /// Register independent source identity, update the actual pixel hull, and
    /// stream its prepared bands into the group. An error invalidates the run.
    pub fn add_source(
        &mut self,
        group: &mut GroupWorkspace,
        source: &PreparedSource,
    ) -> Result<()> {
        if self.sizes != source.sizes
            || self.sizes != group.sizes
            || !same_recipe(self.cfg, group.cfg)
        {
            return Err(FusionError::InvalidInput(
                "source/group recipe or dimensions differ",
            ));
        }
        if self.attribution.is_some() && group.levels.iter().any(|l| l.attribution.is_none()) {
            return Err(FusionError::InvalidInput(
                "session attribution needs group attribution",
            ));
        }
        let key = source
            .key
            .ok_or(FusionError::InvalidInput("source not prepared"))?;
        if self.source_ids.contains(&key.acquisition) {
            return Err(FusionError::DuplicateSource(key.acquisition));
        }
        if self.primary_policy_set && self.fallback_primary != group.policy.primary {
            return Err(FusionError::InvalidInput(
                "primary policy changed within session",
            ));
        }
        group.add(source)?;
        self.primary_policy_set = true;
        self.fallback_primary = group.policy.primary;
        self.source_ids.insert(key.acquisition);
        let preferred = self.fallback_primary == Some(key.bracket);
        for (k, fallback) in self.coverage_fallback.iter_mut().enumerate() {
            (
                channel_chunks_mut(&mut fallback.sum, ACCUMULATION_CHUNK),
                fallback.count.par_chunks_mut(ACCUMULATION_CHUNK),
                fallback.primary.par_chunks_mut(ACCUMULATION_CHUNK),
            )
                .into_par_iter()
                .enumerate()
                .for_each(|(block, (mut sum, count, primary))| {
                    let begin = block * ACCUMULATION_CHUNK;
                    for j in 0..count.len() {
                        let i = begin + j;
                        if !source.coverage[k][i] || (primary[j] && !preferred) {
                            continue;
                        }
                        if preferred && !primary[j] {
                            for values in &mut sum {
                                values[j] = 0.0;
                            }
                            count[j] = 0.0;
                            primary[j] = true;
                        }
                        for (c, values) in sum.iter_mut().enumerate() {
                            values[j] += source.planes[c].level(k)[i];
                        }
                        count[j] += 1.0;
                    }
                });
        }
        (
            channel_chunks_mut(&mut self.hull_low, ACCUMULATION_CHUNK),
            channel_chunks_mut(&mut self.hull_high, ACCUMULATION_CHUNK),
            self.hull_uncensored.par_chunks_mut(ACCUMULATION_CHUNK),
        )
            .into_par_iter()
            .enumerate()
            .for_each(|(block, (low, high, seen_uncensored))| {
                let begin = block * ACCUMULATION_CHUNK;
                for (j, seen_uncensored) in seen_uncensored.iter_mut().enumerate() {
                    let i = begin + j;
                    if !source.input_support[i] {
                        continue;
                    }
                    // Keep the same preferential hull transition for each source;
                    // parallel pixels cannot change first-uncensored source order.
                    let uncensored = source.gaussian_support[0][i];
                    if *seen_uncensored && !uncensored {
                        continue;
                    }
                    if uncensored && !*seen_uncensored {
                        for c in 0..4 {
                            low[c][j] = f32::INFINITY;
                            high[c][j] = f32::NEG_INFINITY;
                        }
                        *seen_uncensored = true;
                    }
                    for c in 0..4 {
                        low[c][j] = low[c][j].min(source.pixels[c][i]);
                        high[c][j] = high[c][j].max(source.pixels[c][i]);
                    }
                }
            });
        Ok(())
    }

    /// Finish one group and reset its buffers for the next one.
    pub fn fold_group(&mut self, group: &mut GroupWorkspace) -> Result<Vec<LevelDiagnostics>> {
        self.fold_group_with_focus_reference(group, GroupFocusReference::Delivered)
    }

    /// Explicit causal control for separating within-group estimation from
    /// cross-group selection. The ordinary entry point retains its arithmetic.
    pub fn fold_group_with_focus_reference(
        &mut self, group: &mut GroupWorkspace, focus_reference: GroupFocusReference,
    ) -> Result<Vec<LevelDiagnostics>> {
        if self.sizes != group.sizes || !same_recipe(self.cfg, group.cfg) {
            return Err(FusionError::InvalidInput(
                "group recipe or dimensions differ",
            ));
        }
        if group.sources.is_empty() {
            return Err(FusionError::Empty);
        }
        if group
            .sources
            .iter()
            .any(|s| !self.source_ids.contains(&s.acquisition))
        {
            return Err(FusionError::InvalidInput(
                "group has an unregistered source",
            ));
        }
        let mut report = vec![LevelDiagnostics::default(); self.sizes.len()];
        let bands = self.sizes.len() - 1;
        let threshold = group.policy.agreement_sigma * group.policy.agreement_sigma;
        for (k, diag) in report.iter_mut().enumerate() {
            let sz = self.sizes[k];
            let n = sz.pixels();
            let level = &group.levels[k];
            // A singleton cannot produce count >= 2 at any coefficient.
            // Its ordinary fallback is already prepared; no repeat evidence
            // or smoothing is consumed by the unchanged decisions below.
            if group.policy.mode == GroupMode::Repeat && group.sources.len() >= 2 {
                for i in 0..n {
                    let count = level.count[i] as f32;
                    let precision = if focus_reference == GroupFocusReference::Delivered {
                        level.precision_at(i)
                    } else { None };
                    group.energy[i] = precision
                        .map_or((level.mean[1][i] + level.mean[3][i]) * 0.5, |p| {
                            (p.mean[1] + p.mean[3]) * 0.5
                        });
                    group.grouped_variance[i] = if let Some(p) = precision {
                        p.temporal_variance[0]
                    } else if count > 0.0 {
                        level.variance_sum[i] / (count * count)
                    } else {
                        0.0
                    };
                    group.residual[i] = (0..4).map(|c| level.m2[c][i].max(0.0)).fold(0.0, f32::max);
                    group.residual_noise[i] = if count > 1.0 {
                        level.color_variance_sum[i] * ((count - 1.0) / count)
                    } else {
                        0.0
                    };
                    group.valid[i] = level.count[i] >= 2;
                }
                smooth5(&mut group.residual[..n], sz, &mut group.scratch);
                smooth5(&mut group.residual_noise[..n], sz, &mut group.scratch);
                erode_support(&group.valid[..n], sz, &mut group.guarded[..n]);
                // No signal outside supported coefficients can enter this gate.
                for i in 0..n {
                    group.valid[i] = group.guarded[i]
                        && group.residual[i] <= threshold * group.residual_noise[i];
                }
                // Reject the complete 5x5 energy footprint around a disagreement.
                erode_support(&group.valid[..n], sz, &mut group.guarded[..n]);
                for value in &mut group.energy[..n] {
                    *value *= *value;
                }
                smooth5(&mut group.energy[..n], sz, &mut group.scratch);
                smooth5(&mut group.grouped_variance[..n], sz, &mut group.scratch);
            }
            let output = &mut self.levels[k];
            let is_mean = k == bands || k + self.cfg.mean_coarse >= bands;
            for i in 0..n {
                let count = level.count[i];
                if count == 0 {
                    diag.uncovered_coefficients += 1;
                    continue;
                }
                let average =
                    group.policy.mode == GroupMode::Repeat && count >= 2 && group.guarded[i];
                if average {
                    let precision = level.precision_at(i);
                    let coefficients = precision
                        .map_or_else(|| std::array::from_fn(|c| level.mean[c][i]), |p| p.mean);
                    if precision.is_some() {
                        diag.precision_averaged_coefficients += 1;
                    } else if level.precision.is_some() {
                        diag.missing_prediction_coefficients += 1;
                    }
                    let weight = if is_mean {
                        0.0
                    } else {
                        ordinary_weight(
                            self.cfg,
                            k,
                            bands,
                            group.energy[i],
                            group.grouped_variance[i],
                        )
                    };
                    output.add(i, coefficients, weight);
                    if let Some(all) = &mut self.attribution {
                        let source_moments = precision.map_or_else(
                            || {
                                level
                                    .attribution
                                    .as_ref()
                                    .expect("registration checked")
                                    .ordinary[i]
                                    .plain
                            },
                            SourceMoments::precision,
                        );
                        all[k][i].weighted.add_group(
                            source_moments,
                            weight,
                            self.groups as u64,
                            true,
                        );
                        all[k][i]
                            .plain
                            .add_group(source_moments, 1.0, self.groups as u64, true);
                    }
                    diag.averaged_coefficients += 1;
                    *diag.averaged_independent_counts.entry(count).or_default() += 1;
                } else if group.policy.mode == GroupMode::Repeat
                    && count >= 2
                    && level.primary.as_ref().is_some_and(|p| p.count[i] > 0.0)
                {
                    output.absorb_at(i, level.primary.as_ref().expect("primary checked"));
                    if let Some(all) = &mut self.attribution {
                        let a = level
                            .attribution
                            .as_ref()
                            .expect("registration checked")
                            .primary
                            .as_ref()
                            .expect("primary checked")[i];
                        all[k][i].weighted.add_group(
                            a.weighted,
                            a.weighted.weight,
                            self.groups as u64,
                            false,
                        );
                        all[k][i].plain.add_group(
                            a.plain,
                            a.plain.weight,
                            self.groups as u64,
                            false,
                        );
                    }
                    diag.primary_fallback_coefficients += 1;
                } else {
                    output.absorb_at(i, &level.ordinary);
                    if let Some(all) = &mut self.attribution {
                        let a = level
                            .attribution
                            .as_ref()
                            .expect("registration checked")
                            .ordinary[i];
                        all[k][i].weighted.add_group(
                            a.weighted,
                            a.weighted.weight,
                            self.groups as u64,
                            false,
                        );
                        all[k][i].plain.add_group(
                            a.plain,
                            a.plain.weight,
                            self.groups as u64,
                            false,
                        );
                    }
                    if count == 1 {
                        diag.single_source_coefficients += 1;
                    } else {
                        diag.ordinary_fallback_coefficients += 1;
                    }
                }
            }
            if !output.finite() {
                return Err(FusionError::Nonfinite);
            }
        }
        self.folded_sources += group.sources.len();
        self.groups += 1;
        for (total, addition) in self.diagnostics.iter_mut().zip(&report) {
            total.absorb(addition);
        }
        group.clear();
        Ok(report)
    }

    pub fn finish(&self) -> Result<FusionResult> {
        if self.groups == 0 {
            return Err(FusionError::Empty);
        }
        if self.folded_sources != self.source_ids.len() {
            return Err(FusionError::UnfinishedGroup);
        }
        let mut workspace = Workspace::new(&self.sizes);
        let mut pyramid = Pyramid::zeros(&self.sizes);
        let mut planes = std::array::from_fn(|_| Vec::new());
        let mut masks: Vec<Vec<bool>> =
            self.sizes.iter().map(|s| vec![false; s.pixels()]).collect();
        let mut diagnostics = self.diagnostics.clone();
        for (k, level) in self.levels.iter().enumerate() {
            let fallback = &self.coverage_fallback[k];
            for (i, v) in masks[k].iter_mut().enumerate() {
                let strict = level.count[i] > 0.0;
                let preserved = !strict && fallback.count[i] > 0.0;
                *v = strict || preserved;
                if preserved {
                    diagnostics[k].saturated_fallback_coefficients += 1;
                    if fallback.primary[i] {
                        diagnostics[k].primary_saturated_fallback_coefficients += 1;
                    }
                }
            }
        }
        let mut valid = masks.last().expect("one level").clone();
        for k in (0..self.sizes.len() - 1).rev() {
            let mut expanded = vec![false; self.sizes[k].pixels()];
            expand_support(&valid, self.sizes[k + 1], &mut expanded, self.sizes[k]);
            for (v, here) in expanded.iter_mut().zip(&masks[k]) {
                *v &= *here;
            }
            valid = expanded;
        }
        for (c, out) in planes.iter_mut().enumerate() {
            for (k, level) in self.levels.iter().enumerate() {
                for (i, value) in pyramid.level_mut(k).iter_mut().enumerate() {
                    *value = if level.denominator[i] > 0.0 {
                        (level.numerator[c][i] / level.denominator[i]) * SOFT_NUMERATOR_SCALE
                    } else if level.count[i] > 0.0 {
                        level.plain[c][i] / level.count[i]
                    } else if self.coverage_fallback[k].count[i] > 0.0 {
                        self.coverage_fallback[k].sum[c][i] / self.coverage_fallback[k].count[i]
                    } else {
                        0.0
                    };
                }
            }
            *out = pyramid.collapse(&mut workspace);
            for (i, value) in out.iter_mut().enumerate() {
                if !valid[i] {
                    *value = 0.0;
                } else {
                    if !value.is_finite() || !self.hull_low[c][i].is_finite() {
                        return Err(FusionError::Nonfinite);
                    }
                    if self.cfg.hull == Hull::InputRange {
                        *value = value.clamp(self.hull_low[c][i], self.hull_high[c][i]);
                    }
                }
            }
        }
        let attribution = self.attribution.as_ref().map(|all| {
            self.sizes
                .iter()
                .enumerate()
                .map(|(k, size)| BandAttribution {
                    width: size.width,
                    height: size.height,
                    coefficients: (0..size.pixels())
                        .map(|i| {
                            if self.levels[k].denominator[i] > 0.0 {
                                all[k][i].weighted.finish(AttributionKind::Weighted)
                            } else if self.levels[k].count[i] > 0.0 {
                                all[k][i].plain.finish(AttributionKind::PlainMean)
                            } else {
                                let fallback = &self.coverage_fallback[k];
                                let kind = if fallback.count[i] <= 0.0 {
                                    AttributionKind::Uncovered
                                } else if fallback.primary[i] {
                                    AttributionKind::SaturatedPrimary
                                } else {
                                    AttributionKind::SaturatedMean
                                };
                                CoefficientAttribution::unavailable(kind)
                            }
                        })
                        .collect(),
                })
                .collect()
        });
        Ok(FusionResult {
            planes,
            attribution,
            valid,
            diagnostics,
            sources: self.source_ids.len(),
            groups: self.groups,
        })
    }

    pub fn buffer_bytes(&self) -> usize {
        let p: usize = self.sizes.iter().map(LevelSize::pixels).sum();
        (15 * p + 8 * self.sizes[0].pixels()) * 4
            + p
            + self.sizes[0].pixels()
            + self.attribution.as_ref().map_or(0, |levels| {
                levels
                    .iter()
                    .map(|l| l.len() * size_of::<DualAccumulator>())
                    .sum::<usize>()
            })
    }
}

#[derive(Debug)]
pub struct FusionResult {
    pub planes: [Vec<f32>; 4],
    /// Optional fixed-size final-band contribution maps, before collapse and
    /// hull clamping. Not a final-pixel variance or confidence field.
    pub attribution: Option<Vec<BandAttribution>>,
    /// Conservative reconstruction support. Invalid output samples are zero only
    /// as a storage placeholder; consumers must crop/mask/refuse them explicitly.
    pub valid: Vec<bool>,
    pub diagnostics: Vec<LevelDiagnostics>,
    pub sources: usize,
    pub groups: usize,
}

fn same_recipe(a: MergeConfig, b: MergeConfig) -> bool {
    a.bands == b.bands
        && a.gate.to_bits() == b.gate.to_bits()
        && a.exponent.to_bits() == b.exponent.to_bits()
        && a.sharpen_per_octave.to_bits() == b.sharpen_per_octave.to_bits()
        && a.mean_coarse == b.mean_coarse
        && a.hull == b.hull
        && a.significance_scale.to_bits() == b.significance_scale.to_bits()
}

// Boolean support follows every nonzero tap of the actual pyramid operators.
// Replication at the real canvas edge is legal; invented source coverage is not.
fn reduce_support(src: &[bool], size: LevelSize, dst: &mut [bool]) {
    let out = size.reduced();
    for y in 0..out.height {
        for x in 0..out.width {
            dst[y * out.width + x] = (0..5).all(|ty| {
                let sy = super::clamp_tap(2 * y, ty, size.height);
                (0..5).all(|tx| src[sy * size.width + super::clamp_tap(2 * x, tx, size.width)])
            });
        }
    }
}

fn expand_support(src: &[bool], size: LevelSize, dst: &mut [bool], out: LevelSize) {
    for y in 0..out.height {
        for x in 0..out.width {
            let cy = (y / 2) as isize;
            let cx = (x / 2) as isize;
            let ymin = if y % 2 == 0 { cy - 1 } else { cy };
            let xmin = if x % 2 == 0 { cx - 1 } else { cx };
            dst[y * out.width + x] = (ymin..=cy + 1).all(|sy| {
                let sy = super::clamp_idx(sy, size.height);
                (xmin..=cx + 1).all(|sx| src[sy * size.width + super::clamp_idx(sx, size.width)])
            });
        }
    }
}

fn erode_support(src: &[bool], size: LevelSize, dst: &mut [bool]) {
    for y in 0..size.height {
        for x in 0..size.width {
            dst[y * size.width + x] = (0..5).all(|ty| {
                let sy = super::clamp_tap(y, ty, size.height);
                (0..5).all(|tx| src[sy * size.width + super::clamp_tap(x, tx, size.width)])
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::noise::{Levels, PlaneNoise, Provenance};

    #[test]
    fn equal_observation_reference_separates_precision_delivery_from_focus_weights() {
        let (w,h)=(48,40);let config=cfg();let support=vec![true;w*h];
        let run=|precision:bool,reference:GroupFocusReference| {
            let mut merge=SessionMerge::new(w,h,config).unwrap();
            let mut group=GroupWorkspace::new_with_precision(w,h,config,GroupPolicy::default(),precision).unwrap();
            let mut source=PreparedSource::new(w,h,config).unwrap();
            for slice in 0..3 {
                let amplitude=[160.,65.,18.][slice];
                let signal=image(w,h,|c,x,y|2000.+c as f32*100.+amplitude*((x as f32*0.73).sin()+(y as f32*0.41).cos()));
                for bracket in 0..2 {
                    let model=noise(if bracket==0 {20.}else{10.});
                    source.prepare(SourceKey {acquisition:(slice*2+bracket) as u64,bracket},
                        std::array::from_fn(|c|signal[c].as_slice()),&model,None,&support,1.).unwrap();
                    if precision {source.predict_precision(FrozenPrediction {acquisition:(100+slice) as u64,
                        signal:std::array::from_fn(|c|signal[c].as_slice()),support:&support},&model,1.,None,None).unwrap();}
                    merge.add_source(&mut group,&source).unwrap();
                }
                merge.fold_group_with_focus_reference(&mut group,reference).unwrap();
            }
            let weights:Vec<_>=merge.levels.iter().flat_map(|l|l.denominator.iter().copied()).collect();
            (merge.finish().unwrap(),weights)
        };
        let (equal,weights)=run(false,GroupFocusReference::Delivered);
        let (frozen,frozen_weights)=run(true,GroupFocusReference::EqualObservation);
        let (_,delivered_weights)=run(true,GroupFocusReference::Delivered);
        assert_eq!(weights.iter().map(|v|v.to_bits()).collect::<Vec<_>>(),frozen_weights.iter().map(|v|v.to_bits()).collect::<Vec<_>>());
        assert!(weights.iter().zip(&delivered_weights).any(|(a,b)|(a-b).abs()>0.01));
        for (a,b) in equal.planes.iter().flatten().zip(frozen.planes.iter().flatten()) {assert!((a-b).abs()<0.002);}
        assert!(frozen.diagnostics.iter().any(|d|d.precision_averaged_coefficients>0));
    }

    #[test]
    fn a_precision_flat_consumer_matches_fixed_mean_variance_and_missing_guide_fallback() {
        let (w, h) = (256, 256);
        let n = w * h;
        let mut config = cfg();
        config.bands = 0;
        let a = flat(71, w, h, 20.0);
        let b = flat(822, w, h, 10.0);
        let guide = image(w, h, |_, _, _| 2000.0);
        let support = vec![true; n];
        for present in [true, false] {
            let mut source = PreparedSource::new(w, h, config).unwrap();
            let mut group =
                GroupWorkspace::new_with_precision(w, h, config, GroupPolicy::default(), true)
                    .unwrap();
            let mut merge = SessionMerge::new(w, h, config).unwrap();
            for (index, (image, sigma)) in [(&a, 20.0), (&b, 10.0)].into_iter().enumerate() {
                source
                    .prepare(
                        SourceKey {
                            acquisition: index as u64,
                            bracket: index,
                        },
                        std::array::from_fn(|c| image[c].as_slice()),
                        &noise(sigma),
                        None,
                        &support,
                        1.0,
                    )
                    .unwrap();
                if present {
                    source
                        .predict_precision(
                            FrozenPrediction {
                                acquisition: 99,
                                signal: std::array::from_fn(|c| guide[c].as_slice()),
                                support: &support,
                            },
                            &noise(sigma),
                            1.0,
                            None,
                            None,
                        )
                        .unwrap();
                }
                merge.add_source(&mut group, &source).unwrap();
            }
            let base = workspace_bytes(w, h, config, GroupPolicy::default()).unwrap();
            let extra = precision_workspace_bytes(w, h, config).unwrap();
            assert!(
                base + extra >= source.buffer_bytes() + group.buffer_bytes() + merge.buffer_bytes()
            );
            merge.fold_group(&mut group).unwrap();
            let result = merge.finish().unwrap();
            let weight = if present {
                (100.0_f32 + 0.002) / (500.0 + 0.004)
            } else {
                0.5
            };
            let mut sum = 0.0_f64;
            let mut sq = 0.0_f64;
            for i in 0..n {
                let expected = a[0][i] * weight + b[0][i] * (1.0 - weight);
                assert!((result.planes[0][i] - expected).abs() < 0.001);
                let residual = f64::from(result.planes[0][i]) - 2000.0;
                sum += residual;
                sq += residual * residual;
            }
            let mean = sum / n as f64;
            let variance = sq / n as f64 - mean * mean;
            let target = if present { 80.0 } else { 125.0 };
            assert!(mean.abs() < 0.15);
            assert!(
                (variance / target - 1.0).abs() < 0.03,
                "present {present}: {variance}"
            );
            assert_eq!(
                result.diagnostics[0].precision_averaged_coefficients,
                if present { n as u64 } else { 0 }
            );
            assert_eq!(
                result.diagnostics[0].missing_prediction_coefficients,
                if present { 0 } else { n as u64 }
            );
        }
    }

    #[test]
    fn precision_guide_cannot_reenter_its_group_or_admit_invalid_guide_pixels() {
        let (w, h) = (32, 32);
        let n = w * h;
        let mut config = cfg();
        config.bands = 0;
        let planes = image(w, h, |_, _, _| 2000.0);
        let support = vec![true; n];
        let mut missing = support.clone();
        missing[37] = false;
        let mut source = PreparedSource::new(w, h, config).unwrap();
        source
            .prepare(
                SourceKey {
                    acquisition: 0,
                    bracket: 0,
                },
                std::array::from_fn(|c| planes[c].as_slice()),
                &noise(4.0),
                None,
                &support,
                1.0,
            )
            .unwrap();
        assert!(
            source
                .predict_precision(
                    FrozenPrediction {
                        acquisition: 0,
                        signal: std::array::from_fn(|c| planes[c].as_slice()),
                        support: &support
                    },
                    &noise(4.0),
                    1.0,
                    None,
                    None
                )
                .is_err()
        );
        source
            .predict_precision(
                FrozenPrediction {
                    acquisition: 1,
                    signal: std::array::from_fn(|c| planes[c].as_slice()),
                    support: &missing,
                },
                &noise(4.0),
                1.0,
                None,
                None,
            )
            .unwrap();
        let mut group =
            GroupWorkspace::new_with_precision(w, h, config, GroupPolicy::default(), true).unwrap();
        group.add(&source).unwrap();
        assert!(group.levels[0].precision_at(37).is_none());
        assert!(group.levels[0].precision_at(38).is_some());
        source
            .prepare(
                SourceKey {
                    acquisition: 1,
                    bracket: 1,
                },
                std::array::from_fn(|c| planes[c].as_slice()),
                &noise(4.0),
                None,
                &support,
                1.0,
            )
            .unwrap();
        assert!(group.add(&source).is_err());
    }

    #[test]
    fn precision_prediction_preserves_original_clipping_hull_in_both_orders() {
        let (w, h) = (32, 32);
        let n = w * h;
        let mut config = cfg();
        config.bands = 0;
        let supported = vec![true; n];
        let missing = vec![false; n];
        for order in [[false, true], [true, false]] {
            let mut source = PreparedSource::new(w, h, config).unwrap();
            let mut group =
                GroupWorkspace::new_with_precision(w, h, config, GroupPolicy::default(), true)
                    .unwrap();
            let mut merge = SessionMerge::new(w, h, config).unwrap();
            for (index, clean) in order.into_iter().enumerate() {
                let value = if clean { 2000.0 } else { 15000.0 };
                let pixels = image(w, h, |_, _, _| value);
                let original = if clean { &supported } else { &missing };
                let guide = if clean { &missing } else { &supported };
                source
                    .prepare_with_masks(
                        SourceKey {
                            acquisition: index as u64,
                            bracket: index,
                        },
                        std::array::from_fn(|c| pixels[c].as_slice()),
                        &noise(4.0),
                        None,
                        None,
                        &supported,
                        original,
                        1.0,
                    )
                    .unwrap();
                source
                    .predict_precision(
                        FrozenPrediction {
                            acquisition: 99,
                            signal: std::array::from_fn(|c| pixels[c].as_slice()),
                            support: guide,
                        },
                        &noise(4.0),
                        1.0,
                        None,
                        None,
                    )
                    .unwrap();
                assert_eq!(&source.gaussian_support[0], original);
                merge.add_source(&mut group, &source).unwrap();
            }
            assert!(merge.hull_uncensored.iter().all(|&v| v));
            assert!(merge.hull_low.iter().flatten().all(|&v| v == 2000.0));
            assert!(merge.hull_high.iter().flatten().all(|&v| v == 2000.0));
            merge.fold_group(&mut group).unwrap();
            let result = merge.finish().unwrap();
            assert!(result.planes.iter().flatten().all(|&v| v == 2000.0));
        }
    }

    #[test]
    fn precision_model_is_bound_to_prepared_noise_gain_and_resolved_beta() {
        let (w, h) = (32, 32);
        let mut config = cfg();
        config.bands = 0;
        let pixels = image(w, h, |_, _, _| 2000.0);
        let supported = vec![true; w * h];
        let mut source = PreparedSource::new(w, h, config).unwrap();
        source
            .prepare_with_noise_gains(
                SourceKey {
                    acquisition: 0,
                    bracket: 0,
                },
                std::array::from_fn(|c| pixels[c].as_slice()),
                &noise(4.0),
                Some(&[0.5]),
                Some(&[0.75]),
                &supported,
                2.0,
            )
            .unwrap();
        let prediction = || FrozenPrediction {
            acquisition: 99,
            signal: std::array::from_fn(|c| pixels[c].as_slice()),
            support: &supported,
        };
        assert!(
            source
                .predict_precision(prediction(), &noise(4.0), 1.0, Some(&[0.5]), Some(&[0.75]))
                .is_err()
        );
        assert!(
            source
                .predict_precision(prediction(), &noise(5.0), 2.0, Some(&[0.5]), Some(&[0.75]))
                .is_err()
        );
        assert!(
            source
                .predict_precision(prediction(), &noise(4.0), 2.0, Some(&[0.4]), Some(&[0.75]))
                .is_err()
        );
        assert!(
            source
                .predict_precision(prediction(), &noise(4.0), 2.0, Some(&[0.5]), Some(&[0.5]))
                .is_err()
        );
        let mut changed_iso = noise(4.0);
        changed_iso.iso = 200.0;
        assert!(
            source
                .predict_precision(prediction(), &changed_iso, 2.0, Some(&[0.5]), Some(&[0.75]))
                .is_err()
        );
        assert!(!source.precision_ready);
        source
            .predict_precision(prediction(), &noise(4.0), 2.0, Some(&[0.5]), Some(&[0.75]))
            .unwrap();
        assert!(source.precision_ready);
        // The same resolved default is accepted regardless of Option spelling.
        source
            .prepare(
                SourceKey {
                    acquisition: 0,
                    bracket: 0,
                },
                std::array::from_fn(|c| pixels[c].as_slice()),
                &noise(4.0),
                None,
                &supported,
                1.0,
            )
            .unwrap();
        let beta = source.gain.beta(0);
        source
            .predict_precision(prediction(), &noise(4.0), 1.0, Some(&[beta]), Some(&[beta]))
            .unwrap();
    }

    #[test]
    fn rejected_duplicate_does_not_insert_guide_and_u64_sources_remain_valid() {
        let (w, h) = (32, 32);
        let mut config = cfg();
        config.bands = 0;
        let pixels = image(w, h, |_, _, _| 2000.0);
        let supported = vec![true; w * h];
        let id = u64::from(u32::MAX) + 7;
        let mut source = PreparedSource::new(w, h, config).unwrap();
        let mut group =
            GroupWorkspace::new_with_precision(w, h, config, GroupPolicy::default(), true).unwrap();
        for guide in [99, 100] {
            source
                .prepare(
                    SourceKey {
                        acquisition: id,
                        bracket: 0,
                    },
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &noise(4.0),
                    None,
                    &supported,
                    1.0,
                )
                .unwrap();
            source
                .predict_precision(
                    FrozenPrediction {
                        acquisition: guide,
                        signal: std::array::from_fn(|c| pixels[c].as_slice()),
                        support: &supported,
                    },
                    &noise(4.0),
                    1.0,
                    None,
                    None,
                )
                .unwrap();
            if guide == 99 {
                group.add(&source).unwrap();
            } else {
                assert!(group.add(&source).is_err());
            }
        }
        assert!(!group.guide_ids.contains(&100));
        assert_eq!(group.source_count(), 1);
        assert_eq!(group.levels[0].precision_at(0).unwrap().dominant_source, id);
        source
            .prepare(
                SourceKey {
                    acquisition: 100,
                    bracket: 1,
                },
                std::array::from_fn(|c| pixels[c].as_slice()),
                &noise(4.0),
                None,
                &supported,
                1.0,
            )
            .unwrap();
        group.add(&source).unwrap();
        assert_eq!(group.source_count(), 2);
    }

    #[test]
    fn zero_noise_precision_preserves_constant_signal_without_invented_floor() {
        let (w, h) = (32, 32);
        let mut config = cfg();
        config.bands = 0;
        let zero = NoiseModel::new(
            [PlaneNoise {
                gain_dn_per_e: 0.0,
                read_noise_e: 0.0,
                levels: Levels {
                    black: 0.0,
                    white: 16384.0,
                },
            }; 4],
            100.0,
            Provenance::Profile,
        );
        let pixels = image(w, h, |_, _, _| 2000.0);
        let supported = vec![true; w * h];
        let mut source = PreparedSource::new(w, h, config).unwrap();
        let mut group =
            GroupWorkspace::new_with_precision(w, h, config, GroupPolicy::default(), true).unwrap();
        let mut merge = SessionMerge::new(w, h, config).unwrap();
        for i in 0..2 {
            source
                .prepare(
                    SourceKey {
                        acquisition: i as u64,
                        bracket: i,
                    },
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &zero,
                    None,
                    &supported,
                    1.0,
                )
                .unwrap();
            source
                .predict_precision(
                    FrozenPrediction {
                        acquisition: 99,
                        signal: std::array::from_fn(|c| pixels[c].as_slice()),
                        support: &supported,
                    },
                    &zero,
                    1.0,
                    None,
                    None,
                )
                .unwrap();
            merge.add_source(&mut group, &source).unwrap();
        }
        let precision = group.levels[0].precision_at(0).unwrap();
        assert_eq!(precision.temporal_variance, [0.0; 2]);
        assert_eq!(precision.positive_count, 2);
        merge.fold_group(&mut group).unwrap();
        assert!(
            merge
                .finish()
                .unwrap()
                .planes
                .iter()
                .flatten()
                .all(|&v| v == 2000.0)
        );
    }

    #[test]
    fn attribution_retains_final_normalized_source_and_group_weights_without_pixel_changes() {
        let (w, h) = (32, 32);
        let mut config = cfg();
        config.bands = 0;
        let policy = GroupPolicy {
            primary: Some(1),
            ..GroupPolicy::default()
        };
        let pixels = image(w, h, |_, _, _| 2000.0);
        let supported = vec![true; w * h];
        for complete_guide in [true, false] {
            let run = |attribution| {
                let mut source = PreparedSource::new(w, h, config).unwrap();
                let mut group =
                    GroupWorkspace::new_with_options(w, h, config, policy, true, attribution)
                        .unwrap();
                let mut merge =
                    SessionMerge::new_with_attribution(w, h, config, attribution).unwrap();
                let mut pair_variance = [0.0; 2];
                let mut singleton_variance = [0.0; 2];
                for i in 0..3 {
                    let sigma = if i == 0 { 20.0 } else { 10.0 };
                    source
                        .prepare(
                            SourceKey {
                                acquisition: 50 + i as u64,
                                bracket: i % 2,
                            },
                            std::array::from_fn(|c| pixels[c].as_slice()),
                            &noise(sigma),
                            None,
                            &supported,
                            1.0,
                        )
                        .unwrap();
                    if complete_guide || i == 0 {
                        source
                            .predict_precision(
                                FrozenPrediction {
                                    acquisition: 99,
                                    signal: std::array::from_fn(|c| pixels[c].as_slice()),
                                    support: &supported,
                                },
                                &noise(sigma),
                                1.0,
                                None,
                                None,
                            )
                            .unwrap();
                    }
                    merge.add_source(&mut group, &source).unwrap();
                    if i == 1 {
                        pair_variance = if let Some(p) = group.levels[0].precision_at(0) {
                            p.temporal_variance
                        } else {
                            [
                                group.levels[0].variance_sum[0] / 4.0,
                                group.levels[0].color_variance_sum[0] / 4.0,
                            ]
                        };
                        merge.fold_group(&mut group).unwrap();
                    }
                    if i == 2 {
                        singleton_variance = [
                            source.variance.level(0)[0],
                            source.color_variance.level(0)[0],
                        ];
                    }
                }
                let live_bytes =
                    source.buffer_bytes() + group.buffer_bytes() + merge.buffer_bytes();
                merge.fold_group(&mut group).unwrap();
                (
                    merge.finish().unwrap(),
                    live_bytes,
                    pair_variance,
                    singleton_variance,
                )
            };
            let (off, off_bytes, _, _) = run(false);
            let (on, on_bytes, pair_variance, singleton_variance) = run(true);
            assert!(off.attribution.is_none());
            assert_eq!(off.valid, on.valid);
            for c in 0..4 {
                assert!(
                    off.planes[c]
                        .iter()
                        .zip(&on.planes[c])
                        .all(|(a, b)| a.to_bits() == b.to_bits())
                );
            }
            let maps = on.attribution.as_ref().unwrap();
            let map = &maps[0].coefficients[0];
            assert_eq!(map.kind, AttributionKind::PlainMean);
            assert_eq!(map.contributing_sources, 3);
            assert_eq!(map.contributing_groups, 2);
            assert_eq!(map.dominant_source, 52);
            assert_eq!(map.dominant_source_fraction, 0.5);
            assert_eq!(map.dominant_group_fraction, 0.5);
            assert_eq!(map.effective_groups, 2.0);
            assert_eq!(map.accepted_repeat_fraction, 0.5);
            let a = if complete_guide {
                (100.0_f32 + 0.002) / (500.0 + 0.004)
            } else {
                0.5
            };
            let expected_ess = 1.0 / ((0.5 * a).powi(2) + (0.5 * (1.0 - a)).powi(2) + 0.25);
            assert!((map.effective_sources - expected_ess).abs() < 1e-5);
            assert!((map.primary_fraction - 0.5 * (1.0 - a)).abs() < 1e-6);
            assert_eq!(
                map.fixed_guide_fraction,
                if complete_guide { 0.5 } else { 0.0 }
            );
            assert!(map.variance_valid);
            for c in 0..2 {
                let expected = 0.25 * (pair_variance[c] + singleton_variance[c]);
                assert!((map.conditional_variance[c] - expected).abs() < 1e-4);
            }
            let map_bytes: usize = maps
                .iter()
                .map(|m| m.coefficients.len() * size_of::<CoefficientAttribution>())
                .sum();
            let reserved = attribution_workspace_bytes(w, h, config, policy).unwrap();
            assert!(on_bytes - off_bytes + map_bytes <= reserved);
        }
    }

    #[test]
    fn attribution_observes_ordinary_and_primary_fallback_and_censored_display() {
        let (w, h) = (16, 16);
        let mut config = cfg();
        config.bands = 0;
        let supported = vec![true; w * h];
        for primary in [None, Some(0)] {
            let policy = GroupPolicy {
                primary,
                ..GroupPolicy::default()
            };
            let mut source = PreparedSource::new(w, h, config).unwrap();
            let mut group =
                GroupWorkspace::new_with_options(w, h, config, policy, false, true).unwrap();
            let mut merge = SessionMerge::new_with_attribution(w, h, config, true).unwrap();
            for i in 0..2 {
                let pixels = image(w, h, |_, _, _| if i == 0 { 1000.0 } else { 5000.0 });
                source
                    .prepare(
                        SourceKey {
                            acquisition: i as u64,
                            bracket: i,
                        },
                        std::array::from_fn(|c| pixels[c].as_slice()),
                        &noise(1.0),
                        None,
                        &supported,
                        1.0,
                    )
                    .unwrap();
                merge.add_source(&mut group, &source).unwrap();
            }
            merge.fold_group(&mut group).unwrap();
            let out = merge.finish().unwrap();
            let a = &out.attribution.as_ref().unwrap()[0].coefficients[0];
            assert_eq!(a.kind, AttributionKind::PlainMean);
            assert_eq!(a.accepted_repeat_fraction, 0.0);
            assert_eq!(a.fixed_guide_fraction, 0.0);
            assert_eq!(
                a.contributing_sources,
                if primary.is_some() { 1 } else { 2 }
            );
            assert_eq!(
                a.primary_fraction,
                if primary.is_some() { 1.0 } else { 0.0 }
            );
            assert_eq!(
                out.planes[0][0],
                if primary.is_some() { 1000.0 } else { 3000.0 }
            );

            let mut coverage = supported.clone();
            coverage[0] = false;
            let clipped = vec![false; w * h];
            let pixels = image(w, h, |_, _, _| 15000.0);
            let mut group =
                GroupWorkspace::new_with_options(w, h, config, policy, false, true).unwrap();
            let mut merge = SessionMerge::new_with_attribution(w, h, config, true).unwrap();
            source
                .prepare_with_masks(
                    SourceKey {
                        acquisition: 7,
                        bracket: 0,
                    },
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &noise(1.0),
                    None,
                    None,
                    &coverage,
                    &clipped,
                    1.0,
                )
                .unwrap();
            merge.add_source(&mut group, &source).unwrap();
            merge.fold_group(&mut group).unwrap();
            let out = merge.finish().unwrap();
            let maps = out.attribution.as_ref().unwrap();
            assert_eq!(maps[0].coefficients[0].kind, AttributionKind::Uncovered);
            let a = &maps[0].coefficients[1];
            assert_eq!(
                a.kind,
                if primary.is_some() {
                    AttributionKind::SaturatedPrimary
                } else {
                    AttributionKind::SaturatedMean
                }
            );
            assert!(!a.variance_valid);
            assert!(a.conditional_variance[0].is_nan());
            assert!(a.effective_sources.is_nan());
            assert_eq!(a.contributing_sources, 0);
        }
    }

    #[test]
    fn attribution_is_bitwise_nonperturbing_on_textured_multiband_fusion() {
        let (w, h) = (64, 64);
        let config = cfg();
        let support = vec![true; w * h];
        let policy = GroupPolicy {
            agreement_sigma: 1.0,
            ..GroupPolicy::default()
        };
        let run = |attribution| {
            let mut source = PreparedSource::new(w, h, config).unwrap();
            let mut group =
                GroupWorkspace::new_with_options(w, h, config, policy, true, attribution).unwrap();
            let mut merge = SessionMerge::new_with_attribution(w, h, config, attribution).unwrap();
            for i in 0..4 {
                let pixels = image(w, h, |c, x, y| {
                    2000.0
                        + c as f32 * 20.0
                        + 100.0 * (x as f32 * 0.4).sin()
                        + 150.0 * (y as f32 * 0.3).cos()
                        + if x > 32 && i % 2 == 1 {
                            50.0 * ((x + y) % 2) as f32
                        } else {
                            0.0
                        }
                });
                source
                    .prepare(
                        SourceKey {
                            acquisition: i as u64,
                            bracket: i % 2,
                        },
                        std::array::from_fn(|c| pixels[c].as_slice()),
                        &noise(4.0),
                        None,
                        &support,
                        1.0,
                    )
                    .unwrap();
                merge.add_source(&mut group, &source).unwrap();
                if i % 2 == 1 {
                    merge.fold_group(&mut group).unwrap();
                }
            }
            merge.finish().unwrap()
        };
        let off = run(false);
        let on = run(true);
        assert_eq!(off.valid, on.valid);
        for c in 0..4 {
            assert!(
                off.planes[c]
                    .iter()
                    .zip(&on.planes[c])
                    .all(|(a, b)| a.to_bits() == b.to_bits())
            );
        }
        let maps = on.attribution.unwrap();
        assert!(
            maps.iter()
                .flat_map(|m| &m.coefficients)
                .any(|a| a.kind == AttributionKind::Weighted)
        );
        assert!(
            maps.iter()
                .flat_map(|m| &m.coefficients)
                .any(|a| a.kind == AttributionKind::PlainMean)
        );
        let averaged: Vec<_> = maps
            .iter()
            .flat_map(|m| &m.coefficients)
            .filter(|a| a.kind == AttributionKind::Weighted && a.accepted_repeat_fraction == 1.0)
            .collect();
        assert!(!averaged.is_empty());
        for a in averaged {
            assert_eq!(a.contributing_sources, 4);
            assert_eq!(a.contributing_groups, 2);
            assert!((a.effective_sources - 4.0).abs() < 1e-5);
            assert!((a.effective_groups - 2.0).abs() < 1e-6);
            assert!((a.dominant_group_fraction - 0.5).abs() < 1e-6);
        }

        assert_eq!(
            off.diagnostics
                .iter()
                .map(|d| d.averaged_coefficients)
                .collect::<Vec<_>>(),
            on.diagnostics
                .iter()
                .map(|d| d.averaged_coefficients)
                .collect::<Vec<_>>()
        );
    }

    #[test]
    fn attribution_requires_group_tracking_before_any_registration_mutation() {
        let (w, h) = (16, 16);
        let config = cfg();
        let pixels = image(w, h, |_, _, _| 2000.0);
        let support = vec![true; w * h];
        let mut source = PreparedSource::new(w, h, config).unwrap();
        source
            .prepare(
                SourceKey {
                    acquisition: 0,
                    bracket: 0,
                },
                std::array::from_fn(|c| pixels[c].as_slice()),
                &noise(4.0),
                None,
                &support,
                1.0,
            )
            .unwrap();
        let mut group = GroupWorkspace::new(w, h, config, GroupPolicy::default()).unwrap();
        let mut merge = SessionMerge::new_with_attribution(w, h, config, true).unwrap();
        assert!(merge.add_source(&mut group, &source).is_err());
        assert_eq!(group.source_count(), 0);
        assert!(merge.source_ids.is_empty());
        assert!(
            attribution_workspace_bytes(usize::MAX, 2, config, GroupPolicy::default()).is_err()
        );
    }

    fn cfg() -> MergeConfig {
        MergeConfig {
            bands: 2,
            gate: 2.0,
            exponent: 2.0,
            sharpen_per_octave: 1.4,
            select: SelectMode::SoftPower,
            admission: AdmissionMode::HardFloor,
            base: BaseBand::Mean,
            mean_coarse: 0,
            hull: Hull::InputRange,
            hull_lambda: 2.0,
            hull_low_only: false,
            fallback: Fallback::Mean,
            fallback_k: 3,
            fallback_power: 4.0,
            hull_from_level: 1,
            significance_scale: 0.0,
        }
    }

    fn noise(sigma: f32) -> NoiseModel {
        let gain = 1e-6;
        NoiseModel::new(
            [PlaneNoise {
                gain_dn_per_e: gain,
                read_noise_e: sigma / gain,
                levels: Levels {
                    black: 0.0,
                    white: 16384.0,
                },
            }; 4],
            100.0,
            Provenance::Profile,
        )
    }

    fn image(w: usize, h: usize, f: impl Fn(usize, usize, usize) -> f32) -> [Vec<f32>; 4] {
        std::array::from_fn(|c| (0..w * h).map(|i| f(c, i % w, i / w)).collect())
    }

    fn flat(seed: u64, w: usize, h: usize, sigma: f32) -> [Vec<f32>; 4] {
        let mut state = seed;
        std::array::from_fn(|_| {
            (0..w * h)
                .map(|_| {
                    state = state
                        .wrapping_mul(6364136223846793005)
                        .wrapping_add(1442695040888963407);
                    let uniform = ((state >> 40) as f32) / ((1u32 << 24) as f32);
                    2000.0 + (uniform * 2.0 - 1.0) * 3.0_f32.sqrt() * sigma
                })
                .collect()
        })
    }

    fn pair(
        a: &[Vec<f32>; 4],
        b: &[Vec<f32>; 4],
        support_a: &[bool],
        support_b: &[bool],
        policy: GroupPolicy,
        w: usize,
        h: usize,
    ) -> FusionResult {
        let cfg = cfg();
        let model = noise(4.0);
        let mut source = PreparedSource::new(w, h, cfg).unwrap();
        let mut group = GroupWorkspace::new(w, h, cfg, policy).unwrap();
        let mut merge = SessionMerge::new(w, h, cfg).unwrap();
        for (id, (pixels, support)) in [(a, support_a), (b, support_b)].into_iter().enumerate() {
            source
                .prepare(
                    SourceKey {
                        acquisition: id as u64,
                        bracket: id,
                    },
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &model,
                    None,
                    support,
                    1.0,
                )
                .unwrap();
            merge.add_source(&mut group, &source).unwrap();
        }
        merge.fold_group(&mut group).unwrap();
        merge.finish().unwrap()
    }

    // Run this filter first when commissioning the new consumer. It measures
    // known injected temporal errors, not scene-containing spatial SD.
    #[test]
    fn a_flat_independent_noise_is_averaged_before_any_detail_claim() {
        let (w, h) = (64, 64);
        let a = flat(13, w, h, 4.0);
        let b = flat(91, w, h, 4.0);
        let valid = vec![true; w * h];
        let out = pair(&a, &b, &valid, &valid, GroupPolicy::default(), w, h);
        assert!(out.valid.iter().all(|v| *v));
        assert!(
            out.diagnostics
                .iter()
                .all(|d| d.primary_fallback_coefficients == 0)
        );
        assert!(out.diagnostics[0].averaged_coefficients > (w * h) as u64 * 99 / 100);
        let input_error: f32 = a.iter().flatten().map(|v| (v - 2000.0).powi(2)).sum();
        let output_error: f32 = out
            .planes
            .iter()
            .flatten()
            .map(|v| (v - 2000.0).powi(2))
            .sum();
        let ratio = output_error / input_error;
        assert!((ratio - 0.5).abs() < 0.035, "variance ratio {ratio}");
        let mean_error =
            out.planes.iter().flatten().map(|v| v - 2000.0).sum::<f32>() / (4 * w * h) as f32;
        assert!(mean_error.abs() < 0.12, "mean bias {mean_error}");
        for c in 0..4 {
            for i in 0..w * h {
                assert!((out.planes[c][i] - (a[c][i] + b[c][i]) * 0.5).abs() < 0.002);
            }
        }
    }

    #[test]
    fn memory_preflight_bounds_resident_buffers_and_refuses_overflow() {
        fn floats(values: &Vec<f32>) -> usize {
            values.capacity() * 4
        }
        fn pyramid(pyr: &Pyramid) -> usize {
            pyr.data.iter().map(floats).sum()
        }
        fn mask(values: &Vec<bool>) -> usize {
            values.capacity()
        }
        fn workspace(ws: &Workspace) -> usize {
            floats(&ws.scratch) + floats(&ws.expanded)
        }
        fn contribution(c: &Contributions) -> usize {
            c.numerator
                .iter()
                .chain(&c.plain)
                .map(floats)
                .sum::<usize>()
                + floats(&c.denominator)
                + floats(&c.count)
        }
        for (w, h, bands) in [(33, 35, 0), (67, 45, 2), (32, 32, 12)] {
            for primary in [None, Some(0)] {
                let mut recipe = cfg();
                recipe.bands = bands;
                let policy = GroupPolicy {
                    primary,
                    ..GroupPolicy::default()
                };
                let estimate = MemoryEstimate::estimate(w, h, recipe, policy).unwrap();
                let source = PreparedSource::new(w, h, recipe).unwrap();
                let group = GroupWorkspace::new(w, h, recipe, policy).unwrap();
                let merge = SessionMerge::new(w, h, recipe).unwrap();
                // Count capacities of actual owned arrays independently of the
                // planning formulas. Vector headers/collection nodes are excluded
                // by the API contract; all pixel payloads are included here.
                let actual_source = source.pixels.iter().map(floats).sum::<usize>()
                    + source.planes.iter().map(pyramid).sum::<usize>()
                    + pyramid(&source.green)
                    + pyramid(&source.variance)
                    + pyramid(&source.color_variance)
                    + workspace(&source.workspace)
                    + floats(&source.scalar)
                    + floats(&source.gain.beta)
                    + mask(&source.input_support)
                    + source
                        .gaussian_support
                        .iter()
                        .chain(&source.support)
                        .chain(&source.gaussian_coverage)
                        .chain(&source.coverage)
                        .chain(&source.energy_support)
                        .map(mask)
                        .sum::<usize>();
                let actual_group = group
                    .levels
                    .iter()
                    .map(|level| {
                        level
                            .mean
                            .iter()
                            .chain(&level.m2)
                            .map(floats)
                            .sum::<usize>()
                            + floats(&level.variance_sum)
                            + floats(&level.color_variance_sum)
                            + level.count.capacity() * 4
                            + contribution(&level.ordinary)
                            + level.primary.as_ref().map_or(0, contribution)
                    })
                    .sum::<usize>()
                    + [
                        &group.energy,
                        &group.scratch,
                        &group.residual,
                        &group.residual_noise,
                        &group.grouped_variance,
                    ]
                    .into_iter()
                    .map(floats)
                    .sum::<usize>()
                    + mask(&group.valid)
                    + mask(&group.guarded);
                let actual_merge = merge.levels.iter().map(contribution).sum::<usize>()
                    + merge
                        .coverage_fallback
                        .iter()
                        .map(|fallback| {
                            fallback.sum.iter().map(floats).sum::<usize>()
                                + floats(&fallback.count)
                                + mask(&fallback.primary)
                        })
                        .sum::<usize>()
                    + mask(&merge.hull_uncensored)
                    + merge
                        .hull_low
                        .iter()
                        .chain(&merge.hull_high)
                        .map(floats)
                        .sum::<usize>();
                assert!(estimate.prepared_source_bytes >= actual_source);
                assert!(estimate.group_bytes >= actual_group);
                assert!(estimate.merge_bytes >= actual_merge);
                assert!(
                    estimate.peak_bytes
                        >= actual_source
                            + actual_group
                            + actual_merge
                            + estimate.finish_additional_bytes
                );
                assert!(
                    estimate.peak_bytes
                        >= actual_source
                            + actual_group
                            + actual_merge
                            + estimate.gain_probe_additional_bytes
                );
                assert_eq!(
                    workspace_bytes(w, h, recipe, policy).unwrap(),
                    estimate.peak_bytes
                );
            }
        }
        assert!(workspace_bytes(usize::MAX, 2, cfg(), GroupPolicy::default()).is_err());
        assert!(workspace_bytes(usize::MAX / 8, 1, cfg(), GroupPolicy::default()).is_err());
        assert!(
            workspace_bytes(
                32,
                32,
                cfg(),
                GroupPolicy {
                    agreement_sigma: f32::NAN,
                    ..GroupPolicy::default()
                }
            )
            .is_err()
        );
    }

    type MaskedSource<'a> = (SourceKey, &'a [Vec<f32>; 4], &'a [bool], &'a [bool]);

    fn masked_sources(
        w: usize,
        h: usize,
        recipe: MergeConfig,
        policy: GroupPolicy,
        sources: &[MaskedSource<'_>],
        fold_each: bool,
    ) -> FusionResult {
        let mut prepared = PreparedSource::new(w, h, recipe).unwrap();
        let mut group = GroupWorkspace::new(w, h, recipe, policy).unwrap();
        let mut merge = SessionMerge::new(w, h, recipe).unwrap();
        for &(key, pixels, coverage, uncensored) in sources {
            prepared
                .prepare_with_masks(
                    key,
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &noise(4.0),
                    None,
                    None,
                    coverage,
                    uncensored,
                    1.0,
                )
                .unwrap();
            merge.add_source(&mut group, &prepared).unwrap();
            if fold_each {
                merge.fold_group(&mut group).unwrap();
            }
        }
        if !fold_each {
            merge.fold_group(&mut group).unwrap();
        }
        merge.finish().unwrap()
    }

    #[test]
    fn clipping_spot_preserves_original_coefficients_without_pyramid_holes_or_gain_claim() {
        let (w, h) = (128, 128);
        let mut recipe = cfg();
        recipe.bands = 4;
        recipe.hull = Hull::Unclamped;
        let pixels = image(w, h, |c, x, y| {
            if c == 0 && x == 64 && y == 64 {
                16384.0
            } else {
                2000.0
            }
        });
        let coverage = vec![true; w * h];
        let mut uncensored = coverage.clone();
        uncensored[64 * w + 64] = false;
        let out = masked_sources(
            w,
            h,
            recipe,
            GroupPolicy::default(),
            &[
                (
                    SourceKey {
                        acquisition: 0,
                        bracket: 0,
                    },
                    &pixels,
                    &coverage,
                    &uncensored,
                ),
                (
                    SourceKey {
                        acquisition: 1,
                        bracket: 1,
                    },
                    &pixels,
                    &coverage,
                    &uncensored,
                ),
            ],
            false,
        );
        assert!(out.valid.iter().all(|v| *v));
        assert!(
            out.diagnostics
                .iter()
                .all(|d| d.saturated_fallback_coefficients > 0)
        );
        for (actual, expected) in out.planes.iter().zip(&pixels) {
            assert_eq!(actual.len(), w * h);
            assert_eq!(expected.len(), w * h);
            for (&actual, &expected) in actual.iter().zip(expected) {
                assert!((actual - expected).abs() < 0.02);
            }
        }
        // Completely censored input has no statistical observations or gain,
        // but retains its measured display values rather than becoming zeros.
        let censored = vec![false; w * h];
        let preserved = masked_sources(
            w,
            h,
            recipe,
            GroupPolicy::default(),
            &[
                (
                    SourceKey {
                        acquisition: 0,
                        bracket: 0,
                    },
                    &pixels,
                    &coverage,
                    &censored,
                ),
                (
                    SourceKey {
                        acquisition: 1,
                        bracket: 1,
                    },
                    &pixels,
                    &coverage,
                    &censored,
                ),
            ],
            false,
        );
        assert!(preserved.valid.iter().all(|v| *v));
        assert!(
            preserved
                .diagnostics
                .iter()
                .all(|d| d.averaged_coefficients == 0
                    && d.averaged_independent_counts.is_empty()
                    && d.saturated_fallback_coefficients > 0)
        );
    }

    #[test]
    fn strict_other_group_beats_censored_primary_and_censored_fallback_is_symmetric() {
        let (w, h) = (32, 32);
        let bright = image(w, h, |_, _, _| 16000.0);
        let darker = image(w, h, |_, _, _| 14000.0);
        let clear = image(w, h, |_, _, _| 1000.0);
        let covered = vec![true; w * h];
        let censored = vec![false; w * h];
        let first = SourceKey {
            acquisition: 0,
            bracket: 0,
        };
        let second = SourceKey {
            acquisition: 1,
            bracket: 1,
        };
        let preferred = GroupPolicy {
            primary: Some(0),
            ..GroupPolicy::default()
        };
        let strict = masked_sources(
            w,
            h,
            cfg(),
            preferred,
            &[
                (first, &bright, &covered, &censored),
                (second, &clear, &covered, &covered),
            ],
            true,
        );
        assert!(
            strict
                .planes
                .iter()
                .flatten()
                .all(|v| (*v - 1000.0).abs() < 0.002)
        );
        assert!(
            strict
                .diagnostics
                .iter()
                .all(|d| d.saturated_fallback_coefficients == 0)
        );
        let sources = [
            (first, &bright, covered.as_slice(), censored.as_slice()),
            (second, &darker, covered.as_slice(), censored.as_slice()),
        ];
        let symmetric = masked_sources(w, h, cfg(), GroupPolicy::default(), &sources, false);
        let reversed = masked_sources(
            w,
            h,
            cfg(),
            GroupPolicy::default(),
            &[sources[1], sources[0]],
            true,
        );
        assert_eq!(symmetric.planes, reversed.planes);
        assert!(
            symmetric
                .planes
                .iter()
                .flatten()
                .all(|v| (*v - 15000.0).abs() < 0.002)
        );
        let primary = masked_sources(w, h, cfg(), preferred, &[sources[1], sources[0]], false);
        assert!(
            primary
                .planes
                .iter()
                .flatten()
                .all(|v| (*v - 16000.0).abs() < 0.002)
        );
        assert!(
            primary
                .diagnostics
                .iter()
                .all(|d| d.primary_saturated_fallback_coefficients > 0
                    && d.averaged_coefficients == 0)
        );
    }

    #[test]
    fn censored_bright_source_cannot_widen_strict_hull_on_crossing_edge_overshoot() {
        let (w, h) = (96, 96);
        let a = image(w, h, |_, x, _| if x >= 48 { 4000.0 } else { 1000.0 });
        let b = image(w, h, |_, _, y| if y >= 48 { 4000.0 } else { 1000.0 });
        let clipped = image(w, h, |_, _, _| 16384.0);
        let coverage = vec![true; w * h];
        let censored = vec![false; w * h];
        let keys = [
            SourceKey {
                acquisition: 0,
                bracket: 0,
            },
            SourceKey {
                acquisition: 1,
                bracket: 1,
            },
            SourceKey {
                acquisition: 2,
                bracket: 2,
            },
        ];
        let policy = GroupPolicy {
            mode: GroupMode::Combine,
            ..GroupPolicy::default()
        };
        let strict = [
            (keys[0], &a, coverage.as_slice(), coverage.as_slice()),
            (keys[1], &b, coverage.as_slice(), coverage.as_slice()),
        ];
        let bounded = masked_sources(w, h, cfg(), policy, &strict, false);
        let mut unbounded_recipe = cfg();
        unbounded_recipe.hull = Hull::Unclamped;
        let unbounded = masked_sources(w, h, unbounded_recipe, policy, &strict, false);
        // Commission a real clamp-sensitive scene: source values agree in the
        // bright quadrant but selecting different bands overshoots that hull.
        let witnesses = (0..w * h)
            .filter(|&i| {
                let maximum = a[0][i].max(b[0][i]);
                unbounded.planes[0][i] > maximum + 1.0
            })
            .count();
        assert!(
            witnesses > 0,
            "crossing fixture did not expose the old hull leak"
        );
        let extra = (keys[2], &clipped, coverage.as_slice(), censored.as_slice());
        let after = masked_sources(w, h, cfg(), policy, &[strict[0], strict[1], extra], false);
        let before = masked_sources(w, h, cfg(), policy, &[extra, strict[0], strict[1]], true);
        assert_eq!(bounded.planes, after.planes);
        assert_eq!(bounded.planes, before.planes);
        assert!(
            after
                .diagnostics
                .iter()
                .all(|d| d.saturated_fallback_coefficients == 0)
        );
    }

    #[test]
    fn dual_masks_keep_true_coverage_holes_invalid_and_old_wrapper_bits_identical() {
        let (w, h) = (48, 40);
        let a = flat(212, w, h, 4.0);
        let b = flat(721, w, h, 4.0);
        let covered = vec![true; w * h];
        let first = SourceKey {
            acquisition: 0,
            bracket: 0,
        };
        let second = SourceKey {
            acquisition: 1,
            bracket: 1,
        };
        let old = pair(&a, &b, &covered, &covered, GroupPolicy::default(), w, h);
        let new = masked_sources(
            w,
            h,
            cfg(),
            GroupPolicy::default(),
            &[
                (first, &a, &covered, &covered),
                (second, &b, &covered, &covered),
            ],
            false,
        );
        assert_eq!(old.planes, new.planes);
        assert_eq!(old.valid, new.valid);
        let mut missing = covered.clone();
        missing[20 * w + 24] = false;
        let censored = vec![false; w * h];
        let mut poison = a.clone();
        for plane in &mut poison {
            plane[20 * w + 24] = f32::NAN;
        }
        let absent = masked_sources(
            w,
            h,
            cfg(),
            GroupPolicy::default(),
            &[(first, &poison, &missing, &censored)],
            false,
        );
        assert!(!absent.valid[20 * w + 24]);
        assert_eq!(absent.planes[0][20 * w + 24], 0.0);
        assert!(absent.valid.iter().any(|v| *v));
        let mut source = PreparedSource::new(w, h, cfg()).unwrap();
        assert!(
            source
                .prepare_with_masks(
                    first,
                    std::array::from_fn(|c| a[c].as_slice()),
                    &noise(4.0),
                    None,
                    None,
                    &missing,
                    &covered,
                    1.0
                )
                .is_err()
        );
        assert!(source.key().is_none());
    }

    #[test]
    fn independent_pixels_are_bit_identical_with_one_and_sixteen_workers() {
        fn append_diagnostics(signature: &mut Vec<u64>, values: &[LevelDiagnostics]) {
            for value in values {
                signature.extend([
                    value.averaged_coefficients,
                    value.single_source_coefficients,
                    value.primary_fallback_coefficients,
                    value.ordinary_fallback_coefficients,
                    value.uncovered_coefficients,
                    value.saturated_fallback_coefficients,
                    value.primary_saturated_fallback_coefficients,
                    value.averaged_independent_counts.len() as u64,
                ]);
                for (&count, &pixels) in &value.averaged_independent_counts {
                    signature.extend([u64::from(count), pixels]);
                }
            }
        }
        fn signature(workers: usize) -> Vec<u64> {
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(workers)
                .build()
                .unwrap();
            pool.install(|| {
                assert_eq!(rayon::current_num_threads(), workers);
                // Odd sizes exercise partial4096-pixel chunks as well as full
                // chunks at multiple pyramid levels.
                let (w, h) = (193, 177);
                let mut signature = Vec::new();
                for mode in [GroupMode::Combine, GroupMode::Repeat] {
                    for primary in [None, Some(0)] {
                        let recipe = MergeConfig { bands: 3, ..cfg() };
                        let policy = GroupPolicy {
                            mode,
                            primary,
                            ..GroupPolicy::default()
                        };
                        let mut prepared = PreparedSource::new(w, h, recipe).unwrap();
                        let mut group = GroupWorkspace::new(w, h, recipe, policy).unwrap();
                        let mut merge = SessionMerge::new(w, h, recipe).unwrap();
                        // Paired, then singleton, then singleton, then paired
                        // reuses cleared buffers and exercises the singleton
                        // repeat bypass between real repeat groups.
                        let groups: [&[(u64, usize)]; 4] =
                            [&[(0, 1), (1, 0)], &[(2, 1)], &[(3, 0)], &[(4, 0), (5, 1)]];
                        for members in groups {
                            for &(id, bracket) in members {
                                let mut pixels = image(w, h, |c, x, y| {
                                    let detail = ((x * 17 + y * 13 + c * 31) % 73) as f32;
                                    let noise =
                                        ((x * 7 + y * 11 + id as usize * 3) % 5) as f32 - 2.0;
                                    let disagreement = if c == 0 && bracket == 1 && x > w / 2 {
                                        200.0
                                    } else {
                                        0.0
                                    };
                                    1000.0 + c as f32 * 100.0 + detail + noise + disagreement
                                });
                                let mut coverage = vec![true; w * h];
                                let mut uncensored = vec![true; w * h];
                                for y in 0..h {
                                    for x in 0..w {
                                        let i = y * w + x;
                                        if x < 9 && y < 9 {
                                            coverage[i] = false;
                                            uncensored[i] = false;
                                            for plane in &mut pixels {
                                                plane[i] = f32::NAN;
                                            }
                                        } else if id == 2
                                            || ((70..100).contains(&x) && (65..90).contains(&y))
                                        {
                                            // All sources censor one shared patch;
                                            // source2 is a wholly censored singleton.
                                            uncensored[i] = false;
                                            pixels[0][i] = 16000.0;
                                        }
                                    }
                                }
                                prepared
                                    .prepare_with_masks(
                                        SourceKey {
                                            acquisition: id,
                                            bracket,
                                        },
                                        std::array::from_fn(|c| pixels[c].as_slice()),
                                        &noise(6.0),
                                        None,
                                        None,
                                        &coverage,
                                        &uncensored,
                                        1.0,
                                    )
                                    .unwrap();
                                merge.add_source(&mut group, &prepared).unwrap();
                            }
                            let report = merge.fold_group(&mut group).unwrap();
                            append_diagnostics(&mut signature, &report);
                        }
                        let result = merge.finish().unwrap();
                        assert_eq!(result.sources, 6);
                        assert_eq!(result.groups, 4);
                        assert!(result.valid.iter().any(|&v| v));
                        assert!(result.valid.iter().any(|&v| !v));
                        assert!(
                            result
                                .diagnostics
                                .iter()
                                .any(|d| d.saturated_fallback_coefficients > 0)
                        );
                        if mode == GroupMode::Repeat {
                            assert!(
                                result
                                    .diagnostics
                                    .iter()
                                    .any(|d| d.averaged_coefficients > 0)
                            );
                            if primary.is_some() {
                                assert!(
                                    result
                                        .diagnostics
                                        .iter()
                                        .any(|d| d.primary_fallback_coefficients > 0)
                                );
                            }
                        }
                        for plane in &result.planes {
                            signature.extend(plane.iter().map(|v| u64::from(v.to_bits())));
                        }
                        signature.extend(result.valid.iter().map(|&v| u64::from(v)));
                        append_diagnostics(&mut signature, &result.diagnostics);
                    }
                }
                signature
            })
        }
        let one = signature(1);
        let sixteen = signature(16);
        assert_eq!(one.len(), sixteen.len());
        assert!(
            one == sixteen,
            "worker-count output/diagnostic mismatch at {:?}",
            one.iter().zip(&sixteen).position(|(a, b)| a != b)
        );
    }

    #[test]
    fn duplicated_acquisition_is_refused_within_and_across_groups() {
        let (w, h) = (32, 32);
        let pixels = flat(7, w, h, 4.0);
        let valid = vec![true; w * h];
        let mut source = PreparedSource::new(w, h, cfg()).unwrap();
        source
            .prepare(
                SourceKey {
                    acquisition: 8,
                    bracket: 0,
                },
                std::array::from_fn(|c| pixels[c].as_slice()),
                &noise(4.0),
                None,
                &valid,
                1.0,
            )
            .unwrap();
        let mut group = GroupWorkspace::new(w, h, cfg(), GroupPolicy::default()).unwrap();
        let mut merge = SessionMerge::new(w, h, cfg()).unwrap();
        merge.add_source(&mut group, &source).unwrap();
        assert!(matches!(
            merge.add_source(&mut group, &source),
            Err(FusionError::DuplicateSource(8))
        ));
        merge.fold_group(&mut group).unwrap();
        source
            .prepare(
                SourceKey {
                    acquisition: 8,
                    bracket: 1,
                },
                std::array::from_fn(|c| pixels[c].as_slice()),
                &noise(4.0),
                None,
                &valid,
                1.0,
            )
            .unwrap();
        assert!(matches!(
            merge.add_source(&mut group, &source),
            Err(FusionError::DuplicateSource(8))
        ));
    }

    #[test]
    fn one_source_reconstructs_and_unfinished_groups_cannot_export() {
        let (w, h) = (33, 35);
        let pixels = image(w, h, |c, x, y| 400.0 + (c * 11 + x * 3 + y * 2) as f32);
        let valid = vec![true; w * h];
        let mut source = PreparedSource::new(w, h, cfg()).unwrap();
        let mut group = GroupWorkspace::new(w, h, cfg(), GroupPolicy::default()).unwrap();
        let mut merge = SessionMerge::new(w, h, cfg()).unwrap();
        for id in 0..2 {
            source
                .prepare(
                    SourceKey {
                        acquisition: id,
                        bracket: 0,
                    },
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &noise(4.0),
                    None,
                    &valid,
                    1.0,
                )
                .unwrap();
            merge.add_source(&mut group, &source).unwrap();
            if id == 0 {
                merge.fold_group(&mut group).unwrap();
                let out = merge.finish().unwrap();
                for (got, want) in out.planes.iter().flatten().zip(pixels.iter().flatten()) {
                    assert!((got - want).abs() < 0.002);
                }
            }
        }
        assert!(matches!(merge.finish(), Err(FusionError::UnfinishedGroup)));
    }

    #[test]
    fn color_only_lighting_disagreement_uses_explicit_primary() {
        let (w, h) = (48, 48);
        let a = image(w, h, |_, _, _| 1000.0);
        let b = image(w, h, |c, _, _| if c == 0 { 1300.0 } else { 1000.0 });
        let valid = vec![true; w * h];
        let policy = GroupPolicy {
            primary: Some(0),
            ..GroupPolicy::default()
        };
        let out = pair(&a, &b, &valid, &valid, policy, w, h);
        assert!(
            out.diagnostics
                .last()
                .unwrap()
                .primary_fallback_coefficients
                > 0
        );
        for (got, want) in out.planes.iter().flatten().zip(a.iter().flatten()) {
            assert!((got - want).abs() < 0.002);
        }
        let second = pair(
            &a,
            &b,
            &valid,
            &valid,
            GroupPolicy {
                primary: Some(1),
                ..policy
            },
            w,
            h,
        );
        assert!((second.planes[0][w * h / 2] - 1300.0).abs() < 0.002);
    }

    #[test]
    fn no_primary_disagreement_is_symmetric_and_matches_ordinary_combine() {
        let (w, h) = (48, 48);
        let a = image(w, h, |c, x, _| {
            300.0 + c as f32 * 40.0 + if x < 24 { 0.0 } else { 1500.0 }
        });
        let b = image(w, h, |c, x, _| {
            600.0 + c as f32 * 90.0 + if x < 25 { 0.0 } else { 800.0 }
        });
        let valid = vec![true; w * h];
        let ab = pair(&a, &b, &valid, &valid, GroupPolicy::default(), w, h);
        let ba = pair(&b, &a, &valid, &valid, GroupPolicy::default(), w, h);
        assert!(
            ab.diagnostics
                .iter()
                .any(|d| d.ordinary_fallback_coefficients > 0)
        );
        for (x, y) in ab.planes.iter().flatten().zip(ba.planes.iter().flatten()) {
            assert!((x - y).abs() < 0.004, "source-order asymmetry {x} vs {y}");
        }
        let combine = pair(
            &a,
            &b,
            &valid,
            &valid,
            GroupPolicy {
                mode: GroupMode::Combine,
                ..GroupPolicy::default()
            },
            w,
            h,
        );
        // A constant color-only mismatch rejects its sole nonzero base, so the
        // entire reconstruction has exactly the ordinary Combine semantics.
        let ca = image(w, h, |_, _, _| 1000.0);
        let cb = image(w, h, |_, _, _| 1300.0);
        let cr = pair(&ca, &cb, &valid, &valid, GroupPolicy::default(), w, h);
        let cc = pair(
            &ca,
            &cb,
            &valid,
            &valid,
            GroupPolicy {
                mode: GroupMode::Combine,
                ..GroupPolicy::default()
            },
            w,
            h,
        );
        for (x, y) in cr.planes.iter().flatten().zip(cc.planes.iter().flatten()) {
            assert!((x - y).abs() < 0.002);
        }
        assert!(
            combine
                .diagnostics
                .iter()
                .all(|d| d.averaged_coefficients == 0)
        );
    }

    #[test]
    fn known_half_native_pixel_offset_and_blur_decline_repeat_mean_at_edge() {
        let (w, h) = (64, 48);
        let edge = |x: f32| 500.0 + 2000.0 * (x + 0.5 - 31.0).clamp(0.0, 1.0);
        let a = image(w, h, |_, x, _| edge(x as f32));
        // One quad-plane pixel = two native pixels; 0.25 plane = 0.5 native.
        let shifted = image(w, h, |_, x, _| edge(x as f32 - 0.25));
        let blurred = image(w, h, |_, x, _| {
            (edge(x as f32 - 1.0) + 2.0 * edge(x as f32) + edge(x as f32 + 1.0)) * 0.25
        });
        let valid = vec![true; w * h];
        let policy = GroupPolicy {
            primary: Some(0),
            ..GroupPolicy::default()
        };
        for changed in [&shifted, &blurred] {
            let out = pair(&a, changed, &valid, &valid, policy, w, h);
            assert!(out.diagnostics[0].primary_fallback_coefficients >= h as u64);
            // The metric is known-target sample error, not gradient energy.
            let center = h / 2 * w + 31;
            assert!((out.planes[0][center] - a[0][center]).abs() < 2.0);
        }
        let clean = pair(&a, &a, &valid, &valid, policy, w, h);
        assert_eq!(clean.diagnostics[0].primary_fallback_coefficients, 0);
        assert_eq!(clean.diagnostics[0].averaged_coefficients, (w * h) as u64);
    }

    #[test]
    fn poisoned_missing_or_clipped_primary_support_never_enters_output() {
        let (w, h) = (64, 48);
        let b = image(w, h, |_, _, _| 1200.0);
        let mut a = b.clone();
        let mut sa = vec![true; w * h];
        let sb = vec![true; w * h];
        for y in 0..h {
            for x in 0..w {
                if x < 9 || (x == 32 && y == 24) {
                    let i = y * w + x;
                    sa[i] = false;
                    for plane in &mut a {
                        plane[i] = f32::NAN;
                    }
                }
            }
        }
        let out = pair(
            &a,
            &b,
            &sa,
            &sb,
            GroupPolicy {
                primary: Some(0),
                ..GroupPolicy::default()
            },
            w,
            h,
        );
        assert!(out.valid.iter().all(|v| *v));
        assert!(out.diagnostics[0].single_source_coefficients > 0);
        for value in out.planes.iter().flatten() {
            assert!((value - 1200.0).abs() < 0.003);
        }
        let missing_primary = pair(
            &b,
            &b,
            &sb,
            &sb,
            GroupPolicy {
                primary: Some(99),
                ..GroupPolicy::default()
            },
            w,
            h,
        );
        assert_eq!(
            missing_primary.diagnostics[0].averaged_coefficients,
            (w * h) as u64
        );
        let unavailable = pair(&a, &a, &sa, &sa, GroupPolicy::default(), w, h);
        assert!(!unavailable.valid[24 * w + 32]);
        assert_eq!(unavailable.planes[0][24 * w + 32], 0.0);
        assert!(unavailable.valid.iter().any(|v| *v));
    }

    #[test]
    fn gain_and_per_source_beta_reach_absolute_variance_without_double_counting() {
        let (w, h) = (32, 32);
        let pixels = image(w, h, |_, _, _| 800.0);
        let valid = vec![true; w * h];
        let mut source = PreparedSource::new(w, h, cfg()).unwrap();
        let model = noise(4.0);
        let key = SourceKey {
            acquisition: 3,
            bracket: 0,
        };
        source
            .prepare(
                key,
                std::array::from_fn(|c| pixels[c].as_slice()),
                &model,
                Some(&[0.25]),
                &valid,
                1.0,
            )
            .unwrap();
        let variance = source.band(0).temporal_variance[100];
        let expected = model.green_luma_sigma(800.0).powi(2) * 0.25;
        assert!((variance - expected).abs() < 1e-6);
        source
            .prepare(
                key,
                std::array::from_fn(|c| pixels[c].as_slice()),
                &model,
                Some(&[0.25]),
                &valid,
                2.0,
            )
            .unwrap();
        assert!((source.band(0).temporal_variance[100] / variance - 4.0).abs() < 1e-6);
        assert!((source.pixels[0][100] - 1600.0).abs() < 1e-6);
        assert!(
            source
                .prepare(
                    key,
                    std::array::from_fn(|c| pixels[c].as_slice()),
                    &model,
                    Some(&[f32::NAN]),
                    &valid,
                    1.0
                )
                .is_err()
        );
        assert!(source.key().is_none());
    }

    #[test]
    fn unequal_color_beta_changes_only_color_compatibility_not_luma_noise() {
        let (w, h) = (32, 32);
        let mut recipe = cfg();
        recipe.bands = 0;
        let a = image(w, h, |_, _, _| 2000.0);
        let b = image(w, h, |c, _, _| if c == 0 { 2004.0 } else { 2000.0 });
        let support = vec![true; w * h];
        let model = noise(4.0);
        let policy = GroupPolicy {
            primary: Some(0),
            agreement_sigma: 1.0,
            ..GroupPolicy::default()
        };
        // The fixed small color residual commissions routing of two distinct
        // modeled gains. It does not calibrate a physical resampling kernel.
        let run = |color_beta: f32| {
            let mut source = PreparedSource::new(w, h, recipe).unwrap();
            let mut group = GroupWorkspace::new(w, h, recipe, policy).unwrap();
            let mut merge = SessionMerge::new(w, h, recipe).unwrap();
            let mut luma_variance = 0.0;
            for (id, pixels) in [&a, &b].into_iter().enumerate() {
                source
                    .prepare_with_noise_gains(
                        SourceKey {
                            acquisition: id as u64,
                            bracket: id,
                        },
                        std::array::from_fn(|c| pixels[c].as_slice()),
                        &model,
                        Some(&[0.25]),
                        Some(&[color_beta]),
                        &support,
                        1.0,
                    )
                    .unwrap();
                luma_variance = source.band(0).temporal_variance[0];
                merge.add_source(&mut group, &source).unwrap();
            }
            merge.fold_group(&mut group).unwrap();
            (merge.finish().unwrap(), luma_variance)
        };
        let (correct, correct_luma) = run(1.0);
        let (wrong_shared_gain, wrong_luma) = run(0.25);
        assert_eq!(correct_luma.to_bits(), wrong_luma.to_bits());
        assert_eq!(correct.diagnostics[0].averaged_coefficients, (w * h) as u64);
        assert_eq!(wrong_shared_gain.diagnostics[0].averaged_coefficients, 0);
        assert_eq!(
            wrong_shared_gain.diagnostics[0].primary_fallback_coefficients,
            (w * h) as u64
        );
        for i in 0..w * h {
            assert!((correct.planes[0][i] - 2002.0).abs() < 0.001);
            assert!((wrong_shared_gain.planes[0][i] - 2000.0).abs() < 0.001);
            assert_eq!(correct.planes[1][i], wrong_shared_gain.planes[1][i]);
        }
        let mut source = PreparedSource::new(w, h, recipe).unwrap();
        assert!(
            source
                .prepare_with_noise_gains(
                    SourceKey {
                        acquisition: 0,
                        bracket: 0
                    },
                    std::array::from_fn(|c| a[c].as_slice()),
                    &model,
                    Some(&[0.25]),
                    Some(&[f32::NAN]),
                    &support,
                    1.0,
                )
                .is_err()
        );
        assert!(source.key().is_none());
    }

    #[test]
    fn combine_consumer_matches_ordinary_pyramid_for_supported_sources() {
        let (w, h) = (48, 40);
        let a = flat(131, w, h, 4.0);
        let mut b = flat(733, w, h, 4.0);
        for plane in &mut b {
            for y in 0..h {
                for x in 20..w {
                    plane[y * w + x] += 120.0;
                }
            }
        }
        let valid = vec![true; w * h];
        let actual = pair(
            &a,
            &b,
            &valid,
            &valid,
            GroupPolicy {
                mode: GroupMode::Combine,
                ..GroupPolicy::default()
            },
            w,
            h,
        );
        let config = cfg();
        let sizes = level_sizes(w, h, config.bands);
        let mut ordinary = super::super::BandMerge::new(w, h, 4, config);
        let mut fws = super::super::FrameWorkspace::new(&sizes, 4);
        let mut luma = vec![0.0; w * h];
        let mut variance = luma.clone();
        for frame in [&a, &b] {
            for i in 0..w * h {
                luma[i] = (frame[1][i] + frame[3][i]) * 0.5;
            }
            super::super::luma_variance(&luma, &noise(4.0), &mut variance);
            ordinary.add_frame(
                &std::array::from_fn::<_, 4, _>(|c| frame[c].as_slice()),
                &luma,
                &variance,
                &mut fws,
            );
            fws.next_frame();
        }
        let expected = ordinary.finish(&mut Workspace::new(&sizes));
        let max_error = actual
            .planes
            .iter()
            .flatten()
            .zip(expected.iter().flatten())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f32::max);
        assert!(max_error < 0.005, "ordinary fallback drift {max_error}");
    }

    #[test]
    fn actual_source_hull_is_retained_and_unsupported_recipes_are_refused() {
        let mut config = cfg();
        config.select = SelectMode::HardMax;
        assert!(SessionMerge::new(32, 32, config).is_err());
        config = cfg();
        config.base = BaseBand::WeightedFromCoarsest;
        assert!(SessionMerge::new(32, 32, config).is_err());
        config = cfg();
        config.hull = Hull::PerLevel;
        assert!(SessionMerge::new(32, 32, config).is_err());
        let (w, h) = (32, 32);
        let a = image(w, h, |_, x, _| if x < 16 { 100.0 } else { 2000.0 });
        let b = image(w, h, |_, x, _| if x < 17 { 200.0 } else { 1500.0 });
        let valid = vec![true; w * h];
        let out = pair(&a, &b, &valid, &valid, GroupPolicy::default(), w, h);
        for c in 0..4 {
            for i in 0..w * h {
                assert!(out.planes[c][i] >= a[c][i].min(b[c][i]));
                assert!(out.planes[c][i] <= a[c][i].max(b[c][i]));
            }
        }
    }
}
