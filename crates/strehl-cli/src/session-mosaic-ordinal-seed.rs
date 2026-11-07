//! Focus-ordinal-conditioned search nomination. Acquisition ordinal is a
//! coordinate for proposing original-image searches, never metric depth or an
//! accepted warp. Only FIT descriptors enter this model.
use super::{CoarseCorrespondence, MatchRole};
use serde::{Deserialize, Serialize};
use strehl_core::plane::PlaneGeometry;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrdinalSeed {
    pub linear: [f64; 2],
    pub translation: [f64; 2],
    pub ordinal_translation: [f64; 2],
    pub source_interval: [usize; 2],
    /// Absolute original census IDs in both axes, including pass offsets.
    pub target_source_linear: [f64; 2],
    pub target_source_interval: [usize; 2],
    pub target_source_rms_ordinals: f64,
    pub fit_ids: Vec<String>,
    pub fit_rms_quad: f64,
    pub nomination_envelope_quad: f64,
}
impl OrdinalSeed {
    pub fn target_sources(&self, source: usize) -> Vec<usize> {
        let Some(centre) = self.target_source(source) else {
            return Vec::new();
        };
        let uncertainty = self.target_source_rms_ordinals.ceil().max(1.0) as usize;
        let mut result = Vec::new();
        for candidate in [
            Some(centre),
            centre.checked_sub(uncertainty),
            centre.checked_add(uncertainty),
        ]
        .into_iter()
        .flatten()
        {
            if (self.target_source_interval[0]..=self.target_source_interval[1])
                .contains(&candidate)
                && !result.contains(&candidate)
            {
                result.push(candidate);
            }
        }
        result
    }
    pub fn target_source(&self, source: usize) -> Option<usize> {
        if !self.supports(source) {
            return None;
        }
        let predicted = self.target_source_linear[0] * source as f64 + self.target_source_linear[1];
        if !predicted.is_finite()
            || predicted < self.target_source_interval[0] as f64
            || predicted > self.target_source_interval[1] as f64
        {
            return None;
        }
        Some(predicted.round() as usize)
    }
    pub fn supports(&self, source: usize) -> bool {
        (self.source_interval[0]..=self.source_interval[1]).contains(&source)
    }
    pub fn predict(&self, p: [f64; 2], source: usize) -> [f64; 2] {
        let t = (source as f64 - self.source_interval[0] as f64)
            / (self.source_interval[1] - self.source_interval[0]) as f64;
        [
            self.linear[0] * p[0] - self.linear[1] * p[1]
                + self.translation[0]
                + t * self.ordinal_translation[0],
            self.linear[1] * p[0]
                + self.linear[0] * p[1]
                + self.translation[1]
                + t * self.ordinal_translation[1],
        ]
    }
    pub fn centred(&self, source: usize, g: PlaneGeometry) -> [f64; 4] {
        let centre = [g.width as f64 * 0.5, g.height as f64 * 0.5];
        let p = self.predict(centre, source);
        [
            self.linear[0],
            self.linear[1],
            p[0] - centre[0],
            p[1] - centre[1],
        ]
    }
}
fn fit(points: &[&CoarseCorrespondence], envelope: f64) -> Option<OrdinalSeed> {
    let lo = points.iter().map(|p| p.source_a).min()?;
    let hi = points.iter().map(|p| p.source_a).max()?;
    if hi <= lo {
        return None;
    }
    let coordinate_scale = points
        .iter()
        .flat_map(|p| p.point_a_quad)
        .map(f64::abs)
        .fold(1.0, f64::max);
    let mut system = [[0.0; 7]; 6];
    for p in points {
        let x = p.point_a_quad[0] / coordinate_scale;
        let y = p.point_a_quad[1] / coordinate_scale;
        let t = (p.source_a - lo) as f64 / (hi - lo) as f64;
        for (row, target) in [
            (
                [x, -y, 1.0, 0.0, t, 0.0],
                p.point_b_quad[0] / coordinate_scale,
            ),
            (
                [y, x, 0.0, 1.0, 0.0, t],
                p.point_b_quad[1] / coordinate_scale,
            ),
        ] {
            for i in 0..6 {
                for j in 0..6 {
                    system[i][j] += row[i] * row[j];
                }
                system[i][6] += row[i] * target;
            }
        }
    }
    for column in 0..6 {
        let pivot = (column..6)
            .max_by(|&a, &b| system[a][column].abs().total_cmp(&system[b][column].abs()))?;
        if system[pivot][column].abs() <= 1e-10 {
            return None;
        }
        system.swap(column, pivot);
        let d = system[column][column];
        for value in &mut system[column][column..] {
            *value /= d;
        }
        let pivot_row = system[column];
        for (i, row) in system.iter_mut().enumerate() {
            if i == column {
                continue;
            }
            let d = row[column];
            for (value, pivot) in row[column..].iter_mut().zip(&pivot_row[column..]) {
                *value -= d * pivot;
            }
        }
    }
    let c = system.map(|r| r[6]);
    if !c.into_iter().all(f64::is_finite) || !(0.5..=2.0).contains(&c[0].hypot(c[1])) {
        return None;
    }
    let mean_a = points.iter().map(|p| p.source_a as f64).sum::<f64>() / points.len() as f64;
    let mean_b = points.iter().map(|p| p.source_b as f64).sum::<f64>() / points.len() as f64;
    let variance = points
        .iter()
        .map(|p| (p.source_a as f64 - mean_a).powi(2))
        .sum::<f64>();
    if variance <= 0.0 {
        return None;
    }
    let slope = points
        .iter()
        .map(|p| (p.source_a as f64 - mean_a) * (p.source_b as f64 - mean_b))
        .sum::<f64>()
        / variance;
    let intercept = mean_b - slope * mean_a;
    let source_rms = (points
        .iter()
        .map(|p| (slope * p.source_a as f64 + intercept - p.source_b as f64).powi(2))
        .sum::<f64>()
        / points.len() as f64)
        .sqrt();
    let mut seed = OrdinalSeed {
        linear: [c[0], c[1]],
        translation: [c[2] * coordinate_scale, c[3] * coordinate_scale],
        ordinal_translation: [c[4] * coordinate_scale, c[5] * coordinate_scale],
        source_interval: [lo, hi],
        target_source_linear: [slope, intercept],
        target_source_interval: [
            points.iter().map(|p| p.source_b).min()?,
            points.iter().map(|p| p.source_b).max()?,
        ],
        target_source_rms_ordinals: source_rms,
        fit_ids: points.iter().map(|p| p.id.clone()).collect(),
        fit_rms_quad: 0.0,
        nomination_envelope_quad: envelope,
    };
    seed.fit_rms_quad = (points
        .iter()
        .map(|p| super::distance_sq(seed.predict(p.point_a_quad, p.source_a), p.point_b_quad))
        .sum::<f64>()
        / points.len() as f64)
        .sqrt();
    Some(seed)
}
fn ordered_sources(points: &[&CoarseCorrespondence]) -> bool {
    // Reversed focus sweeps are allowed. Contradictory acquisition order is not
    // evidence for this single ordinal coordinate; it must use another seed.
    let mut direction = 0;
    for (i, a) in points.iter().enumerate() {
        for b in &points[i + 1..] {
            if a.source_a == b.source_a || a.source_b == b.source_b {
                continue;
            }
            let d = if (a.source_a < b.source_a) == (a.source_b < b.source_b) {
                1
            } else {
                -1
            };
            if direction != 0 && d != direction {
                return false;
            }
            direction = d;
        }
    }
    direction != 0
}
pub(super) fn nominate(matches: &[CoarseCorrespondence], envelope: f64) -> Option<OrdinalSeed> {
    let points: Vec<_> = matches
        .iter()
        .filter(|p| p.role == MatchRole::Fit && p.spatial_roles_match)
        .collect();
    if points.len() < 4 || !envelope.is_finite() || envelope <= 0.0 {
        return None;
    }
    let mut state = 0x83a6_1cd4_a9f8_e137_u64;
    let mut best = None;
    for _ in 0..2048 {
        let mut ids = [0; 3];
        for id in &mut ids {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            *id = (state >> 32) as usize % points.len();
        }
        if ids[0] == ids[1] || ids[0] == ids[2] || ids[1] == ids[2] {
            continue;
        }
        let sample = ids.map(|i| points[i]);
        if !ordered_sources(&sample) {
            continue;
        }
        let Some(model) = fit(&sample, envelope) else {
            continue;
        };
        let consensus: Vec<_> = points
            .iter()
            .copied()
            .filter(|p| {
                super::distance_sq(model.predict(p.point_a_quad, p.source_a), p.point_b_quad)
                    <= envelope * envelope
            })
            .collect();
        if consensus.len() < 4 || consensus.len() * 2 < points.len() || !ordered_sources(&consensus)
        {
            continue;
        }
        let Some(model) = fit(&consensus, envelope) else {
            continue;
        };
        if consensus.iter().any(|p| {
            super::distance_sq(model.predict(p.point_a_quad, p.source_a), p.point_b_quad)
                > envelope * envelope
        }) {
            continue;
        }
        if best.as_ref().is_none_or(|prior: &OrdinalSeed| {
            model.fit_ids.len() > prior.fit_ids.len()
                || (model.fit_ids.len() == prior.fit_ids.len()
                    && model.fit_rms_quad < prior.fit_rms_quad)
        }) {
            best = Some(model);
        }
    }
    best
}

#[cfg(test)]
mod tests {
    use super::*;
    fn plant() -> Vec<CoarseCorrespondence> {
        let points = [
            [250.0, 320.0],
            [650.0, 850.0],
            [1300.0, 400.0],
            [1900.0, 1450.0],
            [700.0, 1800.0],
            [2600.0, 680.0],
            [2800.0, 1800.0],
            [1700.0, 2050.0],
        ];
        let ordinals = [10, 70, 30, 110, 50, 150, 90, 130];
        points
            .into_iter()
            .zip(ordinals)
            .enumerate()
            .map(|(i, (p, s))| CoarseCorrespondence {
                id: format!("fit-{i}"),
                pass_a: 0,
                pass_b: 1,
                point_a_quad: p,
                point_b_quad: [
                    0.98 * p[0] - 0.04 * p[1] + 800.0 + 1.1 * s as f64,
                    0.04 * p[0] + 0.98 * p[1] - 500.0 - 2.4 * s as f64,
                ],
                source_a: s,
                source_b: 1000 + 2 * s,
                focus_a: None,
                focus_b: None,
                role: MatchRole::Fit,
                spatial_blocks: [[1, 0]; 2],
                descriptor_distance: 0.1,
                seed_residual_quad: 0.0,
                within_seed_support: false,
                grid_nomination: false,
                spatial_roles_match: true,
            })
            .collect()
    }
    #[test]
    fn ordinal_seed_nominates_parallax_but_shuffled_ordinals_and_wrong_pairs_do_not_certify() {
        let planted = plant();
        let seed = nominate(&planted, 24.0).expect("ordinal parallax must remain searchable");
        assert_eq!(seed.fit_ids.len(), 8);
        assert!(seed.fit_rms_quad < 1e-6);
        assert_eq!(seed.target_source(70), Some(1140));
        assert_eq!(seed.target_sources(70), vec![1140, 1139, 1141]);
        assert!(seed.target_sources(0).is_empty());
        assert_eq!(seed.target_source(0), None);
        assert!(!seed.supports(0) && !seed.supports(151));
        let mut heldout = planted.clone();
        for p in &mut heldout {
            p.role = MatchRole::Heldout;
        }
        assert!(nominate(&heldout, 24.0).is_none());
        let mut shuffled = planted.clone();
        for (p, ordinal) in shuffled.iter_mut().zip([150, 30, 110, 10, 130, 50, 70, 90]) {
            p.source_a = ordinal;
        }
        assert!(
            nominate(&shuffled, 24.0).is_none(),
            "extra parameters must not rescue shuffled acquisition coordinates"
        );
        let mut wrong = planted.clone();
        for (i, p) in wrong.iter_mut().enumerate() {
            p.point_b_quad = planted[(i * 3 + 1) % 8].point_b_quad;
        }
        assert!(
            nominate(&wrong, 24.0).is_none(),
            "wrong image correspondences must not buy consensus"
        );
        let mut reversed = planted.clone();
        for p in &mut reversed {
            p.source_b = 2000 - 2 * p.source_a;
        }
        let reversed = nominate(&reversed, 24.0).expect("reversed focus sweep is valid");
        assert_eq!(reversed.target_source(70), Some(1860));
        assert_eq!(reversed.target_sources(70), vec![1860, 1859, 1861]);
        let mut unrelated = planted;
        for (p, id) in unrelated
            .iter_mut()
            .zip([1000, 1900, 1200, 1100, 1800, 1400, 1700, 1300])
        {
            p.source_b = id;
        }
        assert!(
            nominate(&unrelated, 24.0).is_none(),
            "unrelated source order cannot nominate a focus mapping"
        );
    }
}
