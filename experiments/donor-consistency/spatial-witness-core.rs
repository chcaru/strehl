// Optional immutable witnesses for the fixed spatial donor consumer.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SpatialWitnessField {
    SourceKnown4, SourceAc, SourceBase,
    BaselineAc, BaselineBase, BaselinePre, BaselinePost, BaselineHull,
    Lo, Hi, Mask(usize), Coverage, DonorSum, RetainedAc,
    PreHull, PostHull, HullCorrection,
}

#[derive(Clone, Debug, Default)]
pub struct SpatialWitnessSummary {
    pub baseline_sum_max_abs: [f64; 4],
    pub mixed_sum_max_abs: [f64; 4],
    pub baseline_hull_sum_max_abs: [f64; 4],
    pub mixed_hull_sum_max_abs: [f64; 4],
}

fn spatial_witness_emit(full: LevelSize, windows: &[AttributionWindow],
    field: SpatialWitnessField, plane: usize, values: &[f32],
    visit: &mut impl FnMut(SpatialWitnessField, usize, usize, &[f32])) {
    assert_eq!(values.len(), full.pixels());
    assert!(values.iter().all(|v| v.is_finite()));
    for (index, w) in windows.iter().enumerate() {
        assert!(w.width > 0 && w.height > 0
            && w.x.checked_add(w.width).is_some_and(|x| x <= full.width)
            && w.y.checked_add(w.height).is_some_and(|y| y <= full.height));
        let mut patch = Vec::with_capacity(w.width * w.height);
        for y in w.y..w.y + w.height {
            patch.extend_from_slice(&values[y * full.width + w.x..y * full.width + w.x + w.width]);
        }
        visit(field, plane, index, &patch);
    }
}

/// Borrow the actual currently consumed known-four planes. No gather or decode.
pub fn observe_spatial_source(sizes: &[LevelSize], planes: &[Vec<f32>],
    windows: &[AttributionWindow], ws: &mut Workspace,
    mut visit: impl FnMut(SpatialWitnessField, usize, usize, &[f32])) -> [f64; 4] {
    assert!(sizes.len() >= 2 && planes.len() == 4 && !windows.is_empty());
    let last = sizes.len() - 1;
    let mut errors = [0.0f64; 4];
    for (c, source) in planes.iter().enumerate() {
        assert_eq!(source.len(), sizes[0].pixels());
        assert!(source.iter().all(|v| v.is_finite()));
        let mut p = Pyramid::zeros(sizes);
        p.build(source, ws);
        let mut terminal = Pyramid::zeros(sizes);
        terminal.level_mut(last).copy_from_slice(p.level(last));
        p.level_mut(last).fill(0.0);
        let ac = p.collapse(ws);
        let base = terminal.collapse(ws);
        errors[c] = source.iter().zip(&ac).zip(&base)
            .map(|((&s, &a), &b)| (s as f64 - a as f64 - b as f64).abs()).fold(0.0, f64::max);
        for (field, values) in [(SpatialWitnessField::SourceKnown4, source.as_slice()),
            (SpatialWitnessField::SourceAc, &ac), (SpatialWitnessField::SourceBase, &base)] {
            spatial_witness_emit(sizes[0], windows, field, c, values, &mut visit);
        }
    }
    errors
}

/// Observe actual coefficients and fixed spatial sums after all sources finished.
pub fn observe_spatial_finish(merge: &BandMerge, donor: &SpatialDonor,
    windows: &[AttributionWindow], ws: &mut Workspace,
    mut visit: impl FnMut(SpatialWitnessField, usize, usize, &[f32])) -> SpatialWitnessSummary {
    supported(merge);
    assert_eq!(merge.sizes, donor.sizes);
    assert_eq!(merge.planes, donor.planes);
    assert!(!windows.is_empty());
    for (r, mask) in donor.masks.iter().enumerate() {
        assert!(donor.seen[r] || mask.iter().all(|&m| m == 0.0));
    }
    let sizes = &merge.sizes;
    let last = sizes.len() - 1;
    let mut summary = SpatialWitnessSummary::default();
    for (c, mut p) in resolved_coefficients(merge).into_iter().enumerate() {
        let baseline_pre = p.collapse(ws);
        let mut terminal = Pyramid::zeros(sizes);
        terminal.level_mut(last).copy_from_slice(p.level(last));
        let baseline_base = terminal.collapse(ws);
        p.level_mut(last).fill(0.0);
        let baseline_ac = p.collapse(ws);
        let retained = baseline_ac.iter().zip(&donor.coverage)
            .map(|(&v, &m)| if m == 0.0 { v } else if m == 1.0 { 0.0 } else { (1.0 - m) * v })
            .collect::<Vec<_>>();
        let mut pre = baseline_pre.clone();
        for j in 0..pre.len() {
            if donor.coverage[j] != 0.0 {
                pre[j] = pre[j] + (donor.sums[c][j] - donor.coverage[j] * baseline_ac[j]);
            }
        }
        let bound = |values: &[f32]| values.iter().zip(&merge.lo[c]).zip(&merge.hi[c])
            .map(|((&v, &lo), &hi)| v.clamp(lo, hi)).collect::<Vec<_>>();
        let baseline_post = bound(&baseline_pre);
        let post = bound(&pre);
        let baseline_hull = baseline_post.iter().zip(&baseline_pre).map(|(&a, &b)| a-b).collect::<Vec<_>>();
        let hull = post.iter().zip(&pre).map(|(&a, &b)| a-b).collect::<Vec<_>>();
        for j in 0..pre.len() {
            summary.baseline_sum_max_abs[c] = summary.baseline_sum_max_abs[c].max(
                (baseline_pre[j] as f64 - baseline_ac[j] as f64 - baseline_base[j] as f64).abs());
            summary.mixed_sum_max_abs[c] = summary.mixed_sum_max_abs[c].max(
                (pre[j] as f64 - retained[j] as f64 - donor.sums[c][j] as f64 - baseline_base[j] as f64).abs());
            summary.baseline_hull_sum_max_abs[c] = summary.baseline_hull_sum_max_abs[c].max(
                (baseline_pre[j] as f64 + baseline_hull[j] as f64 - baseline_post[j] as f64).abs());
            summary.mixed_hull_sum_max_abs[c] = summary.mixed_hull_sum_max_abs[c].max(
                (pre[j] as f64 + hull[j] as f64 - post[j] as f64).abs());
        }
        for (field, values) in [
            (SpatialWitnessField::BaselineAc, baseline_ac.as_slice()),
            (SpatialWitnessField::BaselineBase, &baseline_base),
            (SpatialWitnessField::BaselinePre, &baseline_pre),
            (SpatialWitnessField::BaselinePost, &baseline_post),
            (SpatialWitnessField::BaselineHull, &baseline_hull),
            (SpatialWitnessField::Lo, &merge.lo[c]), (SpatialWitnessField::Hi, &merge.hi[c]),
            (SpatialWitnessField::Coverage, &donor.coverage), (SpatialWitnessField::DonorSum, &donor.sums[c]),
            (SpatialWitnessField::RetainedAc, &retained), (SpatialWitnessField::PreHull, &pre),
            (SpatialWitnessField::PostHull, &post), (SpatialWitnessField::HullCorrection, &hull),
        ] { spatial_witness_emit(sizes[0], windows, field, c, values, &mut visit); }
        for (r, mask) in donor.masks.iter().enumerate() {
            spatial_witness_emit(sizes[0], windows, SpatialWitnessField::Mask(r), c, mask, &mut visit);
        }
    }
    summary
}
