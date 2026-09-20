// Optional, immutable decomposition observer. No source election or image mutation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AttributionWindow {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AttributionField {
    BaselineAc(usize),
    RetainedAc(usize),
    DonorAc(usize),
    Base,
    BaselinePreHull,
    BaselinePostHull,
    BaselineHullCorrection,
    PreHull,
    PostHull,
    HullCorrection,
}

#[derive(Clone, Debug, Default)]
pub struct AttributionSummary {
    pub baseline_sum_max_abs: [f64; 4],
    pub mixed_sum_max_abs: [f64; 4],
    pub baseline_hull_sum_max_abs: [f64; 4],
    pub mixed_hull_sum_max_abs: [f64; 4],
}

/// Reconstruct each signed contribution on the FULL original pyramid domain,
/// then copy only the requested output-quad windows to the visitor. In particular
/// collapse(mask * coefficient) is not collapse(mask) * collapse(coefficient).
/// The residuals concern arithmetic identities, never photographic quality.
pub fn observe_attribution(
    merge: &BandMerge,
    blend: &DonorBlend,
    windows: &[AttributionWindow],
    ws: &mut Workspace,
    mut visit: impl FnMut(AttributionField, usize, usize, &[f32]),
) -> AttributionSummary {
    blend.check(merge);
    let full = merge.sizes[0];
    assert!(!windows.is_empty());
    for w in windows {
        assert!(w.width > 0 && w.height > 0
            && w.x.checked_add(w.width).is_some_and(|x| x <= full.width)
            && w.y.checked_add(w.height).is_some_and(|y| y <= full.height));
    }
    let mut emit = |field, plane, values: &[f32]| {
        assert_eq!(values.len(), full.pixels());
        assert!(values.iter().all(|v| v.is_finite()));
        for (index, w) in windows.iter().enumerate() {
            let mut patch = Vec::with_capacity(w.width * w.height);
            for y in w.y..w.y + w.height {
                patch.extend_from_slice(&values[y * full.width + w.x..y * full.width + w.x + w.width]);
            }
            visit(field, plane, index, &patch);
        }
    };
    // Fixed four-plane coefficient state, never a per-source volume. These are
    // the existing coefficient consumers, including their exact zero-mask path.
    let baseline = resolved_coefficients(merge);
    let mixed = blend.mixed_coefficients(merge);
    let last = merge.sizes.len() - 1;
    let mut result = AttributionSummary::default();
    for (c, (base_coeff, mixed_coeff)) in baseline.into_iter().zip(mixed).enumerate() {
        assert!(base_coeff.level(last).iter().zip(mixed_coeff.level(last))
            .all(|(a, b)| a.to_bits() == b.to_bits()));
        let mut isolated = Pyramid::zeros(&merge.sizes);
        let mut baseline_sum = vec![0.0f64; full.pixels()];
        let mut mixed_sum = vec![0.0f64; full.pixels()];
        for k in 0..last {
            isolated.level_mut(k).copy_from_slice(base_coeff.level(k));
            let values = isolated.collapse(ws);
            for (sum, &v) in baseline_sum.iter_mut().zip(&values) { *sum += v as f64; }
            emit(AttributionField::BaselineAc(k), c, &values);
            drop(values);
            for ((v, &b), &m) in isolated.level_mut(k).iter_mut()
                .zip(base_coeff.level(k)).zip(blend.coverage.level(k)) {
                *v = if m == 0.0 { b } else if m == 1.0 { 0.0 } else { (1.0 - m) * b };
            }
            let values = isolated.collapse(ws);
            for (sum, &v) in mixed_sum.iter_mut().zip(&values) { *sum += v as f64; }
            emit(AttributionField::RetainedAc(k), c, &values);
            drop(values);
            isolated.level_mut(k).copy_from_slice(blend.sums[c].level(k));
            let values = isolated.collapse(ws);
            for (sum, &v) in mixed_sum.iter_mut().zip(&values) { *sum += v as f64; }
            emit(AttributionField::DonorAc(k), c, &values);
            isolated.level_mut(k).fill(0.0);
        }
        isolated.level_mut(last).copy_from_slice(base_coeff.level(last));
        let values = isolated.collapse(ws);
        for ((base, mixed), &v) in baseline_sum.iter_mut().zip(&mut mixed_sum).zip(&values) {
            *base += v as f64; *mixed += v as f64;
        }
        emit(AttributionField::Base, c, &values);
        drop(values);
        for (is_baseline, coeff, sum) in [(true, &base_coeff, &baseline_sum), (false, &mixed_coeff, &mixed_sum)] {
            let pre = coeff.collapse(ws);
            let sum_error = pre.iter().zip(sum).map(|(&a, &b)| (a as f64 - b).abs())
                .fold(0.0f64, f64::max);
            let post = pre.iter().zip(&merge.lo[c]).zip(&merge.hi[c])
                .map(|((&v, &lo), &hi)| v.clamp(lo, hi)).collect::<Vec<_>>();
            let correction = post.iter().zip(&pre).map(|(&after, &before)| after - before).collect::<Vec<_>>();
            let hull_error = pre.iter().zip(&correction).zip(&post)
                .map(|((&before, &delta), &after)| (before as f64 + delta as f64 - after as f64).abs())
                .fold(0.0f64, f64::max);
            if is_baseline {
                result.baseline_sum_max_abs[c] = sum_error;
                result.baseline_hull_sum_max_abs[c] = hull_error;
                emit(AttributionField::BaselinePreHull, c, &pre);
                emit(AttributionField::BaselinePostHull, c, &post);
                emit(AttributionField::BaselineHullCorrection, c, &correction);
            } else {
                result.mixed_sum_max_abs[c] = sum_error;
                result.mixed_hull_sum_max_abs[c] = hull_error;
                emit(AttributionField::PreHull, c, &pre);
                emit(AttributionField::PostHull, c, &post);
                emit(AttributionField::HullCorrection, c, &correction);
            }
        }
    }
    result
}
