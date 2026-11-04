//! Fixed-size attribution for the exact per-band session normalization.
//!
//! These maps describe coefficients before pyramid collapse, demosaic, or hull
//! clamping. Their variance is an injected, fixed-weight temporal model. It
//! excludes cross-band/spatial covariance, adaptive selection and shared guide
//! uncertainty; it is never a final-pixel error bar.

use crate::precision_mean::PrecisionResult;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AttributionKind {
    Uncovered,
    Weighted,
    PlainMean,
    SaturatedMean,
    SaturatedPrimary,
}

/// Bounded summaries of normalized original-acquisition and group weights.
/// Missing statistical attribution uses NaNs and zero counts, with an explicit
/// kind. Source and group IDs are meaningful only when contributing counts > 0.
#[derive(Clone, Copy, Debug)]
pub struct CoefficientAttribution {
    pub kind: AttributionKind,
    pub effective_sources: f32,
    pub contributing_sources: u32,
    pub primary_fraction: f32,
    pub dominant_source: u64,
    pub dominant_source_fraction: f32,
    pub effective_groups: f32,
    pub contributing_groups: u32,
    pub dominant_group: u64,
    pub dominant_group_fraction: f32,
    pub accepted_repeat_fraction: f32,
    /// Fraction from accepted means whose variance prediction used guide
    /// acquisitions excluded from that group. Guide reuse elsewhere still
    /// induces dependencies; this does not assert global independence.
    pub fixed_guide_fraction: f32,
    /// Luma model variance and maximum-color model variance bound.
    pub conditional_variance: [f32; 2],
    pub variance_valid: bool,
}

impl CoefficientAttribution {
    pub(crate) fn unavailable(kind: AttributionKind) -> Self {
        Self {
            kind,
            effective_sources: f32::NAN,
            contributing_sources: 0,
            primary_fraction: f32::NAN,
            dominant_source: 0,
            dominant_source_fraction: f32::NAN,
            effective_groups: f32::NAN,
            contributing_groups: 0,
            dominant_group: 0,
            dominant_group_fraction: f32::NAN,
            accepted_repeat_fraction: f32::NAN,
            fixed_guide_fraction: f32::NAN,
            conditional_variance: [f32::NAN; 2],
            variance_valid: false,
        }
    }
}

#[derive(Debug)]
pub struct BandAttribution {
    pub width: usize,
    pub height: usize,
    pub coefficients: Vec<CoefficientAttribution>,
}

/// Normalized moments are mixed with ratios, avoiding overflow from squaring
/// raw focus weights. IDs must be independent across the groups being combined.
#[derive(Clone, Copy, Debug)]
pub(crate) struct SourceMoments {
    pub(crate) weight: f32,
    squared_fraction: f32,
    variance: [f32; 2],
    primary_fraction: f32,
    dominant_fraction: f32,
    dominant_source: u64,
    positive_sources: u32,
    fixed_guide_fraction: f32,
    variance_valid: bool,
}

impl Default for SourceMoments {
    fn default() -> Self {
        Self {
            weight: 0.0,
            squared_fraction: 0.0,
            variance: [0.0; 2],
            primary_fraction: 0.0,
            dominant_fraction: 0.0,
            dominant_source: 0,
            positive_sources: 0,
            fixed_guide_fraction: 0.0,
            variance_valid: true,
        }
    }
}

impl SourceMoments {
    pub(crate) fn single(source: u64, variance: [f32; 2], primary: bool) -> Self {
        Self {
            weight: 1.0,
            squared_fraction: 1.0,
            variance,
            primary_fraction: if primary { 1.0 } else { 0.0 },
            dominant_fraction: 1.0,
            dominant_source: source,
            positive_sources: 1,
            fixed_guide_fraction: 0.0,
            variance_valid: variance.into_iter().all(|v| v.is_finite() && v >= 0.0),
        }
    }

    pub(crate) fn precision(p: PrecisionResult) -> Self {
        Self {
            weight: 1.0,
            squared_fraction: 1.0 / p.effective_sources,
            variance: p.temporal_variance,
            primary_fraction: p.primary_fraction,
            dominant_fraction: p.dominant_fraction,
            dominant_source: p.dominant_source,
            positive_sources: p.positive_count,
            fixed_guide_fraction: 1.0,
            variance_valid: p
                .temporal_variance
                .into_iter()
                .all(|v| v.is_finite() && v >= 0.0),
        }
    }

    /// Treat the incoming normalized distribution as an observation with this
    /// outer weight. Returns the old/new mixture fractions used by group stats.
    pub(crate) fn add(&mut self, other: Self, weight: f32) -> Option<(f32, f32)> {
        if weight <= 0.0 || other.positive_sources == 0 {
            return None;
        }
        if self.weight == 0.0 {
            *self = Self { weight, ..other };
            return Some((0.0, 1.0));
        }
        let total = self.weight + weight;
        let a = self.weight / total;
        let b = weight / total;
        self.weight = total;
        self.squared_fraction = a * a * self.squared_fraction + b * b * other.squared_fraction;
        self.variance =
            std::array::from_fn(|c| a * a * self.variance[c] + b * b * other.variance[c]);
        self.primary_fraction = a * self.primary_fraction + b * other.primary_fraction;
        self.fixed_guide_fraction = a * self.fixed_guide_fraction + b * other.fixed_guide_fraction;
        let incumbent = a * self.dominant_fraction;
        let candidate = b * other.dominant_fraction;
        if candidate > incumbent
            || (candidate == incumbent && other.dominant_source < self.dominant_source)
        {
            self.dominant_fraction = candidate;
            self.dominant_source = other.dominant_source;
        } else {
            self.dominant_fraction = incumbent;
        }
        self.positive_sources += other.positive_sources;
        self.variance_valid &=
            other.variance_valid && self.variance.into_iter().all(|v| v.is_finite() && v >= 0.0);
        Some((a, b))
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct DualSources {
    pub(crate) weighted: SourceMoments,
    pub(crate) plain: SourceMoments,
}

impl DualSources {
    pub(crate) fn add_source(&mut self, source: SourceMoments, focus_weight: f32) {
        self.weighted.add(source, focus_weight);
        self.plain.add(source, 1.0);
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Accumulator {
    sources: SourceMoments,
    squared_group_fraction: f32,
    dominant_group_fraction: f32,
    dominant_group: u64,
    positive_groups: u32,
    accepted_repeat_fraction: f32,
}

impl Accumulator {
    pub(crate) fn add_group(
        &mut self,
        source: SourceMoments,
        outer_weight: f32,
        group: u64,
        accepted_repeat: bool,
    ) {
        let Some((a, b)) = self.sources.add(source, outer_weight) else {
            return;
        };
        self.squared_group_fraction = a * a * self.squared_group_fraction + b * b;
        self.accepted_repeat_fraction =
            a * self.accepted_repeat_fraction + b * (if accepted_repeat { 1.0 } else { 0.0 });
        let incumbent = a * self.dominant_group_fraction;
        if b > incumbent || (b == incumbent && group < self.dominant_group) {
            self.dominant_group = group;
            self.dominant_group_fraction = b;
        } else {
            self.dominant_group_fraction = incumbent;
        }
        self.positive_groups += 1;
    }

    pub(crate) fn finish(self, kind: AttributionKind) -> CoefficientAttribution {
        let s = self.sources;
        if s.weight <= 0.0 {
            return CoefficientAttribution::unavailable(kind);
        }
        CoefficientAttribution {
            kind,
            effective_sources: 1.0 / s.squared_fraction,
            contributing_sources: s.positive_sources,
            primary_fraction: s.primary_fraction,
            dominant_source: s.dominant_source,
            dominant_source_fraction: s.dominant_fraction,
            effective_groups: 1.0 / self.squared_group_fraction,
            contributing_groups: self.positive_groups,
            dominant_group: self.dominant_group,
            dominant_group_fraction: self.dominant_group_fraction,
            accepted_repeat_fraction: self.accepted_repeat_fraction,
            fixed_guide_fraction: s.fixed_guide_fraction,
            conditional_variance: if s.variance_valid {
                s.variance
            } else {
                [f32::NAN; 2]
            },
            variance_valid: s.variance_valid,
        }
    }
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct DualAccumulator {
    pub(crate) weighted: Accumulator,
    pub(crate) plain: Accumulator,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::precision_mean::PrecisionMean;

    #[test]
    fn actual_group_and_source_normalization_survive_aggregation() {
        let mut precision = PrecisionMean::default();
        precision
            .push([0.0; 4], 400.0, [400.0; 2], 11, false)
            .unwrap();
        precision
            .push([0.0; 4], 100.0, [100.0; 2], 29, true)
            .unwrap();
        let mut a = Accumulator::default();
        a.add_group(
            SourceMoments::precision(precision.result().unwrap()),
            3.0,
            7,
            true,
        );
        a.add_group(SourceMoments::single(31, [100.0; 2], false), 1.0, 9, false);
        let r = a.finish(AttributionKind::Weighted);
        assert_eq!(r.contributing_sources, 3);
        assert_eq!(r.contributing_groups, 2);
        assert!(
            (r.effective_sources - 1.0 / (0.15_f32.powi(2) + 0.6_f32.powi(2) + 0.25_f32.powi(2)))
                .abs()
                < 1e-5
        );
        assert!((r.effective_groups - 1.6).abs() < 1e-6);
        assert!((r.primary_fraction - 0.6).abs() < 1e-6);
        assert_eq!(r.dominant_source, 29);
        assert!((r.dominant_source_fraction - 0.6).abs() < 1e-6);
        assert_eq!(r.dominant_group, 7);
        assert_eq!(r.dominant_group_fraction, 0.75);
        assert_eq!(r.accepted_repeat_fraction, 0.75);
        assert_eq!(r.fixed_guide_fraction, 0.75);
        assert!(r.variance_valid);
        assert!((r.conditional_variance[0] - 51.25).abs() < 1e-5);
    }

    #[test]
    fn huge_focus_weights_do_not_square_to_infinity_and_zero_weight_is_absent() {
        let mut a = Accumulator::default();
        a.add_group(SourceMoments::single(10, [4.0; 2], false), 1e30, 1, false);
        a.add_group(SourceMoments::single(20, [4.0; 2], true), 1e30, 2, false);
        a.add_group(SourceMoments::single(30, [4.0; 2], false), 0.0, 3, false);
        let r = a.finish(AttributionKind::Weighted);
        assert_eq!(r.contributing_sources, 2);
        assert_eq!(r.effective_sources, 2.0);
        assert_eq!(r.conditional_variance, [2.0; 2]);
        assert_eq!(r.primary_fraction, 0.5);
    }

    #[test]
    fn display_fallback_is_not_statistical_evidence() {
        for kind in [
            AttributionKind::Uncovered,
            AttributionKind::SaturatedMean,
            AttributionKind::SaturatedPrimary,
        ] {
            let r = CoefficientAttribution::unavailable(kind);
            assert_eq!(r.kind, kind);
            assert!(!r.variance_valid);
            assert!(r.effective_sources.is_nan());
            assert!(r.conditional_variance.iter().all(|v| v.is_nan()));
            assert_eq!(r.contributing_sources, 0);
        }
    }
}
