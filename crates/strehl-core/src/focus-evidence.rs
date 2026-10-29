//! Bounded, per-pass focus evidence for optional reconstruction and mosaics.
//!
//! Coordinates are acquisition ordinals, never physical depth. The regularized
//! anchor chooses a diagnostic neighbourhood; it does not select output pixels.
//! Every reconstruction consumer must retain its own noise/visibility admission.
use crate::merge::FocusStats;
use crate::plane::PlaneGeometry;
use crate::through_focus::{FINE_FOCUS_NOISE_SD, ThroughFocus};
use sha2::{Digest, Sha256};
use std::mem::size_of;

pub const BOUNDARY: u8 = 1;
pub const SCALE_DISAGREEMENT: u8 = 2;
pub const COMPETING_MODE: u8 = 4;
pub const WEAK_RESPONSE: u8 = 8;
pub const NO_LOCAL_FIT: u8 = 16;
pub const MISSING_COVERAGE: u8 = 32;
/// A significant observed mode could not be resolved or retained.
pub const UNRESOLVED_MODE: u8 = 64;
pub const MODE_CAPACITY: usize = 8;
const RECEIPT_CHUNK_BYTES: usize = 64 * 1024;
const INVALID_REGULARIZED: f32 = -1.0e6;

/// A measured local maximum, sorted by response height. A flat-topped maximum
/// is one mode at its plateau midpoint. Empty slots have a NaN ordinal.
#[derive(Clone, Copy, Debug)]
pub struct FocusMode {
    pub ordinal: f32,
    /// Height above the sweep minimum, in nominal fine-operator noise units.
    /// This is not valley prominence, a probability, or depth uncertainty.
    pub prominence_sigma: f32,
    pub boundary: bool,
}

impl Default for FocusMode {
    fn default() -> Self {
        Self {
            ordinal: f32::NAN,
            prominence_sigma: 0.0,
            boundary: false,
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct ModePeak {
    value: f32,
    first: u16,
    last: u16,
    boundary: bool,
}

impl Default for ModePeak {
    fn default() -> Self {
        Self {
            value: f32::NEG_INFINITY,
            first: u16::MAX,
            last: u16::MAX,
            boundary: false,
        }
    }
}

/// Ordered streaming plateau census. Unlike a far-sample maximum, a retained
/// mode must exceed both observed neighbours, or meet a physical sweep edge.
/// Missing neighbours never become zero-valued observations.
#[derive(Clone, Copy, Debug)]
struct ModeCensus {
    peaks: [ModePeak; MODE_CAPACITY],
    dropped_max: f32,
    uncertain_max: f32,
    active: ModePeak,
    left: f32,
}

impl Default for ModeCensus {
    fn default() -> Self {
        Self {
            peaks: [ModePeak::default(); MODE_CAPACITY],
            dropped_max: f32::NEG_INFINITY,
            uncertain_max: f32::NEG_INFINITY,
            active: ModePeak::default(),
            left: f32::NAN,
        }
    }
}

impl ModeCensus {
    fn retain(&mut self, peak: ModePeak) {
        let slot = self
            .peaks
            .iter()
            .position(|p| peak.value > p.value || (peak.value == p.value && peak.first < p.first));
        if let Some(slot) = slot {
            self.dropped_max = self.dropped_max.max(self.peaks[MODE_CAPACITY - 1].value);
            self.peaks.copy_within(slot..MODE_CAPACITY - 1, slot + 1);
            self.peaks[slot] = peak;
        } else {
            self.dropped_max = self.dropped_max.max(peak.value);
        }
    }

    fn close_plateau(&mut self, right: Option<f32>, right_boundary: bool) {
        if !self.active.value.is_finite() {
            return;
        }
        let left_boundary = self.active.first == 0;
        let left_lower = self.left.is_finite() && self.left < self.active.value;
        let right_lower = right.is_some_and(|v| v < self.active.value);
        if (left_lower || left_boundary) && (right_lower || right_boundary) {
            self.retain(ModePeak {
                boundary: left_boundary || right_boundary,
                ..self.active
            });
        } else if (left_lower || left_boundary || !self.left.is_finite())
            && (right_lower || right_boundary || right.is_none())
        {
            // Observed height, but at least one neighbour is missing. The full
            // missing-coverage flag separately protects entirely unseen modes.
            self.uncertain_max = self.uncertain_max.max(self.active.value);
        }
    }

    fn observe(&mut self, ordinal: u16, value: Option<f32>) {
        let Some(value) = value else {
            self.close_plateau(None, false);
            self.active = ModePeak::default();
            self.left = f32::NAN;
            return;
        };
        if !self.active.value.is_finite() {
            self.active = ModePeak {
                value,
                first: ordinal,
                last: ordinal,
                boundary: false,
            };
        } else if value == self.active.value {
            self.active.last = ordinal;
        } else {
            let left = self.active.value;
            self.close_plateau(Some(value), false);
            self.left = left;
            self.active = ModePeak {
                value,
                first: ordinal,
                last: ordinal,
                boundary: false,
            };
        }
    }

    fn finish(&mut self) {
        self.close_plateau(None, true);
        self.active = ModePeak::default();
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FocusFrame {
    pub acquisition: u64,
    pub global_index: usize,
}

#[derive(Clone, Copy, Debug)]
pub struct FocusEvidencePolicy {
    /// A policy cut in the existing fine operator's nominal noise units.
    /// This is not a probability or a new sensor-noise estimate.
    pub minimum_prominence_sigma: f32,
    pub maximum_perplexity_fraction: f32,
    pub competing_peak_ratio: f32,
}

impl Default for FocusEvidencePolicy {
    fn default() -> Self {
        Self {
            minimum_prominence_sigma: 8.0,
            maximum_perplexity_fraction: 0.25,
            competing_peak_ratio: 0.8,
        }
    }
}

#[derive(Debug, thiserror::Error)]
pub enum FocusEvidenceError {
    #[error("invalid focus evidence: {0}")]
    Invalid(&'static str),
    #[error("focus evidence reservation exceeds its byte budget")]
    Budget,
    #[error(transparent)]
    Core(#[from] crate::Error),
}

type Result<T> = std::result::Result<T, FocusEvidenceError>;

/// Full raster in one pass's anchor green-quad gauge. Its caller separately
/// records the raster origin and lattice spacing. NaN denotes no measured fit.
#[derive(Debug)]
pub struct FocusEvidence {
    pub geometry: PlaneGeometry,
    pub frames: Vec<FocusFrame>,
    pub ordinal: Vec<f32>,
    /// Local log-Gaussian shape width in frames, not a confidence interval.
    pub width_frames: Vec<f32>,
    pub prominence_sigma: Vec<f32>,
    pub perplexity: Vec<f32>,
    pub top_global_indices: Vec<[usize; 4]>,
    pub flags: Vec<u8>,
    /// At least one acquisition has a valid complete focus-filter footprint.
    /// This is not raw-CFA coverage; the caller must export that separately.
    pub covered: Vec<bool>,
    pub supported_frames: Vec<u16>,
    pub modes: Vec<[FocusMode; MODE_CAPACITY]>,
    /// Largest observed unresolved/dropped height above the sweep minimum.
    /// Missing intervals can contain an unobserved mode of any height.
    pub unresolved_mode_prominence_sigma: Vec<f32>,
    /// Conservative evidence eligibility, not calibrated focus confidence.
    /// Any missing sweep observation refuses eligibility but preserves diagnostics.
    pub usable: Vec<bool>,
}

impl FocusEvidence {
    /// Adjacent original acquisitions for a measured fractional ordinal.
    /// No extrapolation or assumption about filename/global-index order.
    pub fn bracket(&self, ordinal: f32) -> Option<(FocusFrame, FocusFrame, f32)> {
        if self.frames.is_empty()
            || !ordinal.is_finite()
            || ordinal < 0.0
            || ordinal > (self.frames.len() - 1) as f32
        {
            return None;
        }
        let lo = ordinal.floor() as usize;
        let hi = (lo + 1).min(self.frames.len() - 1);
        Some((self.frames[lo], self.frames[hi], ordinal - lo as f32))
    }
}

/// Two streaming passes, fixed storage per pixel. The caller supplies actual
/// focus responses with their complete filter-footprint validity masks.
pub struct FocusEvidenceBuilder {
    geometry: PlaneGeometry,
    frames: Vec<FocusFrame>,
    policy: FocusEvidencePolicy,
    stats: FocusStats,
    through: Option<ThroughFocus>,
    seen: Vec<bool>,
    anchor_receipts: Vec<[u8; 32]>,
    support_count: Vec<u16>,
    mask_regularized: Vec<f32>,
    mask_fine: Vec<f32>,
    modes: Vec<ModeCensus>,
    next_ordinal: usize,
}

impl FocusEvidenceBuilder {
    pub fn reservation_bytes(geometry: PlaneGeometry, frames: usize) -> Result<usize> {
        if geometry.width == 0
            || geometry.height == 0
            || !(3..usize::from(u16::MAX)).contains(&frames)
        {
            return Err(FocusEvidenceError::Invalid("dimensions or frame count"));
        }
        // Logical live payload, including builder + returned evidence, sorted
        // identity checks, SHA scratch and generous fixed object/header allowance.
        // Caller input rasters and excess capacity in the supplied frame Vec are
        // caller-reserved; allocator metadata is not a sensor/frame-volume term.
        geometry
            .width
            .checked_mul(geometry.height)
            .and_then(|n| n.checked_mul(Self::bytes_per_pixel()))
            .and_then(|n| frames.checked_mul(128).and_then(|f| n.checked_add(f)))
            .and_then(|n| n.checked_add(RECEIPT_CHUNK_BYTES + 4096))
            .filter(|&n| n <= isize::MAX as usize)
            .ok_or(FocusEvidenceError::Budget)
    }

    fn bytes_per_pixel() -> usize {
        // FocusStats (non-robust), ThroughFocus, support count, two scratch planes,
        // census, then all simultaneously live output planes.
        size_of::<f32>()
            + size_of::<u16>()
            + ThroughFocus::bytes_per_pixel()
            + size_of::<u16>()
            + 2 * size_of::<f32>()
            + size_of::<ModeCensus>()
            + 4 * size_of::<f32>()
            + size_of::<[usize; 4]>()
            + 3 * size_of::<u8>()
            + size_of::<u16>()
            + size_of::<[FocusMode; MODE_CAPACITY]>()
            + size_of::<f32>()
    }

    pub fn new(
        geometry: PlaneGeometry,
        frames: Vec<FocusFrame>,
        policy: FocusEvidencePolicy,
        budget: usize,
    ) -> Result<Self> {
        if Self::reservation_bytes(geometry, frames.len())? > budget {
            return Err(FocusEvidenceError::Budget);
        }
        if !policy.minimum_prominence_sigma.is_finite()
            || policy.minimum_prominence_sigma <= 0.0
            || !policy.maximum_perplexity_fraction.is_finite()
            || !(0.0..=1.0).contains(&policy.maximum_perplexity_fraction)
            || policy.maximum_perplexity_fraction == 0.0
            || !policy.competing_peak_ratio.is_finite()
            || !(0.0..=1.0).contains(&policy.competing_peak_ratio)
        {
            return Err(FocusEvidenceError::Invalid("policy"));
        }
        let mut acquisitions: Vec<_> = frames.iter().map(|f| f.acquisition).collect();
        let mut indices: Vec<_> = frames.iter().map(|f| f.global_index).collect();
        acquisitions.sort_unstable();
        indices.sort_unstable();
        if acquisitions.windows(2).any(|w| w[0] == w[1]) || indices.windows(2).any(|w| w[0] == w[1])
        {
            return Err(FocusEvidenceError::Invalid(
                "duplicate acquisition or global index",
            ));
        }
        drop(acquisitions);
        drop(indices);
        let n = geometry.pixels();
        Ok(Self {
            geometry,
            policy,
            stats: FocusStats::new(geometry),
            through: None,
            seen: vec![false; frames.len()],
            anchor_receipts: vec![[0; 32]; frames.len()],
            frames,
            support_count: vec![0; n],
            mask_regularized: vec![0.0; n],
            mask_fine: vec![0.0; n],
            modes: vec![ModeCensus::default(); n],
            next_ordinal: 0,
        })
    }

    fn validate(
        &self,
        ordinal: usize,
        frame: FocusFrame,
        values: &[f32],
        valid: &[bool],
    ) -> Result<()> {
        if ordinal != self.next_ordinal
            || self.frames.get(ordinal) != Some(&frame)
            || self.seen.get(ordinal) != Some(&false)
        {
            return Err(FocusEvidenceError::Invalid(
                "frame identity/order or repeated fold",
            ));
        }
        if values.len() != self.geometry.pixels() || valid.len() != values.len() {
            return Err(FocusEvidenceError::Invalid("response dimensions"));
        }
        if values
            .iter()
            .zip(valid)
            .any(|(&v, &ok)| ok && (!v.is_finite() || v < 0.0))
        {
            return Err(FocusEvidenceError::Invalid(
                "nonfinite or negative supported response",
            ));
        }
        Ok(())
    }

    fn validate_regularized_range(&self, values: &[f32], valid: &[bool]) -> Result<()> {
        // Preserve finite posterior u and u*exp(u), even for adversarial finite
        // inputs. This bounds arithmetic, not any empirically plausible signal.
        if values.iter().zip(valid).any(|(&v, &ok)| {
            ok && !((v - INVALID_REGULARIZED) / ThroughFocus::temperature()).is_finite()
        }) {
            return Err(FocusEvidenceError::Invalid("posterior numerical range"));
        }
        Ok(())
    }

    pub fn observe_anchor(
        &mut self,
        ordinal: usize,
        frame: FocusFrame,
        regularized: &[f32],
        valid: &[bool],
    ) -> Result<()> {
        if self.through.is_some() {
            return Err(FocusEvidenceError::Invalid("anchor pass already finished"));
        }
        self.validate(ordinal, frame, regularized, valid)?;
        self.validate_regularized_range(regularized, valid)?;
        for (i, &ok) in valid.iter().enumerate() {
            self.mask_regularized[i] = if ok {
                regularized[i]
            } else {
                INVALID_REGULARIZED
            };
            self.support_count[i] += u16::from(ok);
        }
        self.stats.fold(ordinal as u16, &self.mask_regularized)?;
        self.anchor_receipts[ordinal] = response_receipt(regularized, valid);
        self.seen[ordinal] = true;
        self.next_ordinal += 1;
        Ok(())
    }

    pub fn begin_shape_pass(&mut self) -> Result<()> {
        if self.through.is_some() || self.seen.iter().any(|&seen| !seen) {
            return Err(FocusEvidenceError::Invalid(
                "incomplete or repeated anchor pass",
            ));
        }
        self.through = Some(ThroughFocus::new(&self.stats));
        self.seen.fill(false);
        self.next_ordinal = 0;
        Ok(())
    }

    pub fn observe_shape(
        &mut self,
        ordinal: usize,
        frame: FocusFrame,
        fine: &[f32],
        regularized: &[f32],
        valid: &[bool],
    ) -> Result<()> {
        if self.through.is_none() {
            return Err(FocusEvidenceError::Invalid("anchor pass not finished"));
        }
        self.validate(ordinal, frame, fine, valid)?;
        self.validate(ordinal, frame, regularized, valid)?;
        if self.anchor_receipts[ordinal] != response_receipt(regularized, valid) {
            return Err(FocusEvidenceError::Invalid(
                "shape pass changed anchor response or validity",
            ));
        }
        for (i, &ok) in valid.iter().enumerate() {
            // A finite negative sentinel avoids (-inf)*exp(-inf) in the existing
            // posterior sums. Fine NaNs cannot enter its comparisons or fits.
            self.mask_regularized[i] = if ok {
                regularized[i]
            } else {
                INVALID_REGULARIZED
            };
            self.mask_fine[i] = if ok { fine[i] } else { f32::NAN };
        }
        self.through.as_mut().expect("phase checked").fold(
            ordinal as u16,
            &self.mask_fine,
            &self.mask_regularized,
        )?;
        for (i, &ok) in valid.iter().enumerate() {
            self.modes[i].observe(ordinal as u16, ok.then_some(fine[i]));
        }
        self.seen[ordinal] = true;
        self.next_ordinal += 1;
        Ok(())
    }

    pub fn finish(mut self) -> Result<FocusEvidence> {
        if self.seen.iter().any(|&seen| !seen) {
            return Err(FocusEvidenceError::Invalid("incomplete shape pass"));
        }
        let through = self
            .through
            .as_ref()
            .ok_or(FocusEvidenceError::Invalid("missing shape pass"))?;
        let n = self.geometry.pixels();
        let mut out = FocusEvidence {
            geometry: self.geometry,
            frames: self.frames.clone(),
            ordinal: vec![f32::NAN; n],
            width_frames: vec![f32::NAN; n],
            prominence_sigma: vec![0.0; n],
            perplexity: vec![0.0; n],
            top_global_indices: vec![[usize::MAX; 4]; n],
            flags: vec![0; n],
            covered: vec![false; n],
            supported_frames: self.support_count.clone(),
            modes: vec![[FocusMode::default(); MODE_CAPACITY]; n],
            unresolved_mode_prominence_sigma: vec![0.0; n],
            usable: vec![false; n],
        };
        for i in 0..n {
            out.covered[i] = self.support_count[i] > 0;
            if usize::from(self.support_count[i]) != self.frames.len() {
                out.flags[i] |= MISSING_COVERAGE;
            }
            if through.at_bracket_boundary(i) {
                out.flags[i] |= BOUNDARY;
            }
            if through.fine_peak_outside_triple(i) {
                out.flags[i] |= SCALE_DISAGREEMENT;
            }
            let peak = through.top_values(i)[0];
            let floor = through.floor(i);
            let prominence = (peak - floor).max(0.0);
            out.prominence_sigma[i] = prominence / (std::f32::consts::SQRT_2 * FINE_FOCUS_NOISE_SD);
            out.perplexity[i] = through.posterior_perplexity(i);
            if !out.prominence_sigma[i].is_finite()
                || out.prominence_sigma[i] < self.policy.minimum_prominence_sigma
                || !out.perplexity[i].is_finite()
                || out.perplexity[i]
                    > self.frames.len() as f32 * self.policy.maximum_perplexity_fraction
            {
                out.flags[i] |= WEAK_RESPONSE;
            }
            match (through.subframe_peak(i), through.local_peak_width(i)) {
                (Some(position), Some(width)) => {
                    out.ordinal[i] = position;
                    out.width_frames[i] = width;
                }
                _ => out.flags[i] |= NO_LOCAL_FIT,
            }
            self.modes[i].finish();
            let census = &self.modes[i];
            let primary = through.top_indices(i)[0];
            let significant = self.policy.competing_peak_ratio * prominence;
            let nominal_sd = std::f32::consts::SQRT_2 * FINE_FOCUS_NOISE_SD;
            for (slot, mode) in out.modes[i].iter_mut().zip(census.peaks) {
                if !mode.value.is_finite() {
                    break;
                }
                let height = (mode.value - floor).max(0.0);
                *slot = FocusMode {
                    ordinal: 0.5 * (f32::from(mode.first) + f32::from(mode.last)),
                    prominence_sigma: height / nominal_sd,
                    boundary: mode.boundary,
                };
                let is_primary = (mode.first..=mode.last).contains(&primary);
                if is_primary && mode.boundary {
                    out.flags[i] |= BOUNDARY;
                } else if !is_primary && height > 0.0 && height >= significant {
                    // Do not exclude a genuine nearby maximum using the fitted
                    // primary width: broad shoulders can hide a distant mode.
                    out.flags[i] |= COMPETING_MODE;
                }
            }
            let unresolved = (census.dropped_max.max(census.uncertain_max) - floor).max(0.0);
            out.unresolved_mode_prominence_sigma[i] = unresolved / nominal_sd;
            if unresolved > 0.0 && unresolved >= significant {
                out.flags[i] |= UNRESOLVED_MODE;
            }
            for (slot, &ordinal) in out.top_global_indices[i]
                .iter_mut()
                .zip(through.top_indices(i))
            {
                if let Some(frame) = self.frames.get(usize::from(ordinal)) {
                    *slot = frame.global_index;
                }
            }
            out.usable[i] = out.covered[i] && out.flags[i] == 0;
        }
        Ok(out)
    }
}

/// Same-process immutable binding, including the original validity mask. Invalid
/// response bits are omitted because they are never observations in either pass.
fn response_receipt(values: &[f32], valid: &[bool]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update((values.len() as u64).to_le_bytes());
    let mut bytes = [0u8; RECEIPT_CHUNK_BYTES];
    let mut used = 0;
    for (&v, &ok) in values.iter().zip(valid) {
        let needed = if ok { 5 } else { 1 };
        if used + needed > bytes.len() {
            hash.update(&bytes[..used]);
            used = 0;
        }
        bytes[used] = u8::from(ok);
        used += 1;
        if ok {
            bytes[used..used + 4].copy_from_slice(&v.to_bits().to_le_bytes());
            used += 4;
        }
    }
    hash.update(&bytes[..used]);
    hash.finalize().into()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn frames(n: usize) -> Vec<FocusFrame> {
        (0..n)
            .map(|i| FocusFrame {
                acquisition: i as u64 + 100,
                global_index: 2 * (n - i),
            })
            .collect()
    }
    fn curve(values: &[f32], masks: &[bool]) -> FocusEvidence {
        let f = frames(values.len());
        let mut b = FocusEvidenceBuilder::new(
            PlaneGeometry {
                width: 1,
                height: 1,
            },
            f.clone(),
            FocusEvidencePolicy::default(),
            1 << 20,
        )
        .unwrap();
        for (i, &v) in values.iter().enumerate() {
            b.observe_anchor(i, f[i], &[v], &[masks[i]]).unwrap();
        }
        b.begin_shape_pass().unwrap();
        for (i, &v) in values.iter().enumerate() {
            b.observe_shape(i, f[i], &[v], &[v], &[masks[i]]).unwrap();
        }
        b.finish().unwrap()
    }
    #[test]
    fn a_flat_has_coverage_but_no_focus_evidence() {
        let result = curve(&[0.54; 17], &[true; 17]);
        assert!(result.covered[0]);
        assert!(!result.usable[0]);
        assert!(result.flags[0] & WEAK_RESPONSE != 0);
    }
    #[test]
    fn b_gaussian_position_width_and_original_track_mapping() {
        let values: Vec<_> = (0..25)
            .map(|i| 0.54 + 12.0 * (-0.5 * ((i as f32 - 11.25) / 1.4).powi(2)).exp())
            .collect();
        let r = curve(&values, &[true; 25]);
        assert!(r.usable[0], "flags {}", r.flags[0]);
        assert!((r.ordinal[0] - 11.25).abs() < 0.04);
        assert!((r.width_frames[0] - 1.4).abs() < 0.001);
        let (a, b, t) = r.bracket(r.ordinal[0]).unwrap();
        assert_eq!((a.global_index, b.global_index), (28, 26));
        assert!((t - 0.25).abs() < 0.04);
        assert!(r.bracket(-1.0).is_none());
        assert!(r.bracket(25.0).is_none());
    }
    #[test]
    fn c_boundary_competing_peak_and_missing_triple_refuse() {
        let single: Vec<_> = (0..31)
            .map(|i| 0.54 + 12.0 * (-0.5 * ((i as f32 - 8.0) / 1.2).powi(2)).exp())
            .collect();
        let double: Vec<_> = single
            .iter()
            .enumerate()
            .map(|(i, &v)| v + 11.0 * (-0.5 * ((i as f32 - 23.0) / 1.2).powi(2)).exp())
            .collect();
        let r = curve(&double, &[true; 31]);
        assert!(!r.usable[0]);
        assert!(r.flags[0] & COMPETING_MODE != 0);
        let boundary: Vec<_> = (0..31)
            .map(|i| 0.54 + 12.0 * (-0.5 * (i as f32 / 1.2).powi(2)).exp())
            .collect();
        assert!(curve(&boundary, &[true; 31]).flags[0] & BOUNDARY != 0);
        let mut mask = [true; 31];
        mask[9] = false;
        assert!(curve(&single, &mask).flags[0] & NO_LOCAL_FIT != 0);
        assert!(!curve(&single, &[false; 31]).covered[0]);
    }
    #[test]
    fn d_budget_and_two_pass_identity_are_checked() {
        let g = PlaneGeometry {
            width: 4,
            height: 3,
        };
        let f = frames(3);
        assert!(
            FocusEvidenceBuilder::new(g, f.clone(), FocusEvidencePolicy::default(), 1).is_err()
        );
        let mut dup = f.clone();
        dup[1] = dup[0];
        assert!(
            FocusEvidenceBuilder::new(g, dup, FocusEvidencePolicy::default(), 1 << 20).is_err()
        );
        let mut b =
            FocusEvidenceBuilder::new(g, f.clone(), FocusEvidencePolicy::default(), 1 << 20)
                .unwrap();
        assert!(b.begin_shape_pass().is_err());
        b.observe_anchor(0, f[0], &[1.0; 12], &[true; 12]).unwrap();
        assert!(b.observe_anchor(0, f[0], &[1.0; 12], &[true; 12]).is_err());
        assert!(b.observe_anchor(1, f[2], &[1.0; 12], &[true; 12]).is_err());
    }

    #[test]
    fn e_shape_pass_must_reproduce_anchor_values_and_validity() {
        let f = frames(3);
        let mut b = FocusEvidenceBuilder::new(
            PlaneGeometry {
                width: 1,
                height: 1,
            },
            f.clone(),
            FocusEvidencePolicy::default(),
            1 << 20,
        )
        .unwrap();
        for (i, &frame) in f.iter().enumerate() {
            b.observe_anchor(i, frame, &[1.0], &[true]).unwrap();
        }
        b.begin_shape_pass().unwrap();
        assert!(
            b.observe_shape(0, f[0], &[1.0], &[1000.0], &[true])
                .is_err()
        );
        assert!(b.observe_shape(0, f[0], &[1.0], &[1.0], &[false]).is_err());
        b.observe_shape(0, f[0], &[1.0], &[1.0], &[true]).unwrap();
    }

    #[test]
    fn f_broad_primary_cannot_hide_a_distant_competing_mode() {
        let single: Vec<_> = (0..65)
            .map(|i| 0.54 + 12.0 * (-0.5 * ((i as f32 - 20.0) / 4.0).powi(2)).exp())
            .collect();
        let positive = curve(&single, &[true; 65]);
        assert!(positive.usable[0], "flags {}", positive.flags[0]);
        assert!((positive.width_frames[0] - 4.0).abs() < 0.001);
        let double: Vec<_> = single
            .iter()
            .enumerate()
            .map(|(i, &v)| v + 10.0 * (-0.5 * ((i as f32 - 48.0) / 1.4).powi(2)).exp())
            .collect();
        let r = curve(&double, &[true; 65]);
        assert!(!r.usable[0]);
        assert_ne!(r.flags[0] & COMPETING_MODE, 0);
        assert_eq!(r.modes[0][0].ordinal, 20.0);
        assert_eq!(r.modes[0][1].ordinal, 48.0);
    }

    #[test]
    fn g_near_maxima_are_not_discarded_by_primary_width() {
        let mut values = [0.54; 33];
        values[14..19].copy_from_slice(&[3.0, 12.0, 9.0, 10.0, 3.0]);
        let r = curve(&values, &[true; 33]);
        assert_ne!(r.flags[0] & COMPETING_MODE, 0);
        assert_eq!(r.modes[0][0].ordinal, 15.0);
        assert_eq!(r.modes[0][1].ordinal, 17.0);
    }

    #[test]
    fn h_plateaus_are_one_mode_and_rising_shoulders_are_not_modes() {
        let mut values = [0.54; 31];
        values[13..17].copy_from_slice(&[7.0, 12.0, 12.0, 7.0]);
        let r = curve(&values, &[true; 31]);
        assert!(r.usable[0], "flags {}", r.flags[0]);
        assert_eq!(r.modes[0][0].ordinal, 14.5);
        assert!(r.modes[0][1].ordinal.is_nan());
        let mut census = ModeCensus::default();
        for (i, v) in [1.0, 3.0, 3.0, 4.0, 2.0].into_iter().enumerate() {
            census.observe(i as u16, Some(v));
        }
        census.finish();
        assert_eq!(census.peaks[0].first, 3);
        assert!(!census.peaks[1].value.is_finite());
    }

    #[test]
    fn i_boundary_modes_remain_visible_beside_an_interior_primary() {
        let values: Vec<_> = (0..65)
            .map(|i| {
                0.54 + 12.0 * (-0.5 * ((i as f32 - 20.0) / 2.0).powi(2)).exp()
                    + 11.0 * (-0.5 * ((i as f32 - 64.0) / 1.4).powi(2)).exp()
            })
            .collect();
        let r = curve(&values, &[true; 65]);
        assert_ne!(r.flags[0] & COMPETING_MODE, 0);
        assert_eq!(r.modes[0][1].ordinal, 64.0);
        assert!(r.modes[0][1].boundary);
        let reversed: Vec<_> = values.into_iter().rev().collect();
        let r = curve(&reversed, &[true; 65]);
        assert_ne!(r.flags[0] & COMPETING_MODE, 0);
        assert_eq!(r.modes[0][1].ordinal, 0.0);
        assert!(r.modes[0][1].boundary);
    }

    #[test]
    fn j_missing_intervals_and_neighbours_are_not_unique_focus_evidence() {
        let values: Vec<_> = (0..65)
            .map(|i| 0.54 + 12.0 * (-0.5 * ((i as f32 - 20.0) / 2.0).powi(2)).exp())
            .collect();
        let mut valid = [true; 65];
        valid[40] = false; // Far from an otherwise valid fitted triple.
        let r = curve(&values, &valid);
        assert!(r.covered[0]);
        assert_eq!(r.supported_frames[0], 64);
        assert_ne!(r.flags[0] & MISSING_COVERAGE, 0);
        assert!(!r.usable[0]);
        assert!(r.ordinal[0].is_finite());
        let mut census = ModeCensus::default();
        for (i, v) in [Some(0.0), Some(10.0), None, Some(8.0), Some(0.0)]
            .into_iter()
            .enumerate()
        {
            census.observe(i as u16, v);
        }
        census.finish();
        assert_eq!(census.uncertain_max, 10.0);
        assert!(!census.peaks[0].value.is_finite());
    }

    #[test]
    fn k_significant_census_overflow_is_flagged_but_tiny_modes_are_not() {
        let mut values = [0.54; 65];
        for j in 0..9 {
            let k = 3 + 6 * j;
            values[k - 1] = 2.54;
            values[k] = 12.54 - j as f32 * 0.1;
            values[k + 1] = 2.54;
        }
        let r = curve(&values, &[true; 65]);
        assert!(r.modes[0].iter().all(|m| m.ordinal.is_finite()));
        assert_ne!(r.flags[0] & UNRESOLVED_MODE, 0);
        assert!(r.unresolved_mode_prominence_sigma[0] > 80.0);
        for j in 1..9 {
            let k = 3 + 6 * j;
            values[k - 1] = 0.55;
            values[k] = 0.74 - j as f32 * 0.01;
            values[k + 1] = 0.55;
        }
        let r = curve(&values, &[true; 65]);
        assert!(r.usable[0], "flags {}", r.flags[0]);
        assert!(r.unresolved_mode_prominence_sigma[0] > 0.0);
        assert_eq!(r.flags[0] & UNRESOLVED_MODE, 0);
    }

    #[test]
    fn l_both_passes_require_ordinal_order_and_failed_folds_are_retryable() {
        let f = frames(3);
        let mut b = FocusEvidenceBuilder::new(
            PlaneGeometry {
                width: 1,
                height: 1,
            },
            f.clone(),
            FocusEvidencePolicy::default(),
            1 << 20,
        )
        .unwrap();
        assert!(b.observe_anchor(1, f[1], &[1.0], &[true]).is_err());
        assert!(b.observe_anchor(0, f[0], &[f32::MAX], &[true]).is_err());
        for (i, &frame) in f.iter().enumerate() {
            b.observe_anchor(i, frame, &[1.0], &[true]).unwrap();
        }
        b.begin_shape_pass().unwrap();
        assert!(b.observe_shape(1, f[1], &[1.0], &[1.0], &[true]).is_err());
        assert!(
            b.observe_shape(0, f[0], &[f32::NAN], &[1.0], &[true])
                .is_err()
        );
        for (i, &frame) in f.iter().enumerate() {
            b.observe_shape(i, frame, &[1.0], &[1.0], &[true]).unwrap();
        }
        assert!(b.finish().is_ok());
    }

    #[test]
    fn m_batched_receipt_is_exact_and_invalid_bits_are_not_observations() {
        let values: Vec<_> = (0..50_000).map(|i| i as f32 * 0.125).collect();
        let valid: Vec<_> = (0usize..50_000).map(|i| !i.is_multiple_of(3)).collect();
        let mut reference = Sha256::new();
        reference.update((values.len() as u64).to_le_bytes());
        for (&v, &ok) in values.iter().zip(&valid) {
            reference.update([u8::from(ok)]);
            if ok {
                reference.update(v.to_bits().to_le_bytes());
            }
        }
        let expected: [u8; 32] = reference.finalize().into();
        assert_eq!(response_receipt(&values, &valid), expected);
        let mut invalid_poison = values.clone();
        for (v, &ok) in invalid_poison.iter_mut().zip(&valid) {
            if !ok {
                *v = f32::NAN;
            }
        }
        assert_eq!(response_receipt(&invalid_poison, &valid), expected);
        invalid_poison[1] += 1.0;
        assert_ne!(response_receipt(&invalid_poison, &valid), expected);
    }

    #[test]
    fn n_reservation_covers_census_and_simultaneously_live_evidence() {
        let g = PlaneGeometry {
            width: 4,
            height: 3,
        };
        let required = FocusEvidenceBuilder::reservation_bytes(g, 17).unwrap();
        assert!(required > g.pixels() * 256 + 17 * 128);
        assert!(
            FocusEvidenceBuilder::new(g, frames(17), FocusEvidencePolicy::default(), required - 1)
                .is_err()
        );
        let mut b =
            FocusEvidenceBuilder::new(g, frames(17), FocusEvidencePolicy::default(), required)
                .unwrap();
        for (i, frame) in frames(17).into_iter().enumerate() {
            b.observe_anchor(i, frame, &[1.0; 12], &[true; 12]).unwrap();
        }
        b.begin_shape_pass().unwrap();
        let builder_payload = g.pixels() * (size_of::<f32>() + size_of::<u16>())
            + b.through.as_ref().unwrap().allocated_bytes()
            + b.support_count.len() * size_of::<u16>()
            + (b.mask_fine.len() + b.mask_regularized.len()) * size_of::<f32>()
            + b.modes.len() * size_of::<ModeCensus>()
            + b.seen.len() * size_of::<bool>()
            + b.anchor_receipts.len() * size_of::<[u8; 32]>()
            + b.frames.len() * size_of::<FocusFrame>();
        for (i, frame) in frames(17).into_iter().enumerate() {
            b.observe_shape(i, frame, &[1.0; 12], &[1.0; 12], &[true; 12])
                .unwrap();
        }
        let out = b.finish().unwrap();
        let returned_payload = (out.ordinal.len()
            + out.width_frames.len()
            + out.prominence_sigma.len()
            + out.perplexity.len()
            + out.unresolved_mode_prominence_sigma.len())
            * size_of::<f32>()
            + out.top_global_indices.len() * size_of::<[usize; 4]>()
            + out.flags.len()
            + out.covered.len()
            + out.usable.len()
            + out.supported_frames.len() * size_of::<u16>()
            + out.modes.len() * size_of::<[FocusMode; MODE_CAPACITY]>()
            + out.frames.len() * size_of::<FocusFrame>();
        assert!(builder_payload + returned_payload + RECEIPT_CHUNK_BYTES <= required);
        assert!(
            FocusEvidenceBuilder::reservation_bytes(
                PlaneGeometry {
                    width: usize::MAX,
                    height: 2
                },
                3
            )
            .is_err()
        );
        assert!(FocusEvidenceBuilder::reservation_bytes(g, u16::MAX as usize).is_err());
    }
}
