//! Experiment-only direct local registration evidence from original CFA patches.
//! Disjoint spatial training/held-out tiles, full WarpMap gauge, no image volume.
//! Pair disagreement is not an unconditional per-source uncertainty estimate.
use crate::{
    align::{
        AlignConfig, Cx, PairTrace, PlaneRef, Similarity, TileStatus, ncc_tile_warped,
        refine_pair_observed, tile_grid,
    },
    noise::PlaneNoise,
    plane::{PlaneGeometry, QuadSource},
};
/// Optional post-estimator probes; these never change fit or admission.
#[path = "reconstruction-registration-diagnostics.rs"]
pub mod diagnostics;
#[path = "reconstruction-registration-footprint.rs"]
mod footprint;

type Result<T> = std::result::Result<T, String>;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PlaneKind {
    Red,
    GreenLuma,
    Blue,
}
impl PlaneKind {
    fn index(self) -> usize {
        match self {
            Self::Red => 0,
            Self::GreenLuma => 1,
            Self::Blue => 2,
        }
    }
    fn offset(self) -> [f64; 2] {
        match self {
            Self::Red => [0., 0.],
            Self::GreenLuma => [0.5, 0.5],
            Self::Blue => [1., 1.],
        }
    }
}
pub struct OriginalView<'a> {
    pub acquisition_id: u64,
    pub source: &'a dyn QuadSource,
    pub color_pulls: [Similarity; 3],
    pub noise: [PlaneNoise; 4],
    pub gain: f32,
    pub frozen_expected_rgb: [f32; 3],
}
#[derive(Clone, Copy, Debug)]
pub struct Window {
    pub full: PlaneGeometry,
    pub center_sensor: [f64; 2],
    pub side_quad: usize,
}
#[derive(Clone, Copy, Debug)]
pub struct Policy {
    /// Gaussian sigma in original same-color plane pixels, for geometry only.
    /// Zero preserves the unfiltered diagnostic arm.
    pub geometry_lowpass_sigma_quad: f32,
    pub tile_quad: usize,
    pub grid_axis: usize,
    pub radius_quad: i32,
    pub minimum_peak: f32,
    pub minimum_contrast_variances: f32,
    pub minimum_gradient_variances: f32,
    pub minimum_information_ratio: f32,
    pub minimum_train: usize,
    pub minimum_heldout: usize,
    pub maximum_saved_disagreement_sensor: f64,
    pub maximum_refined_disagreement_sensor: f64,
    pub budget_bytes: usize,
}
impl Default for Policy {
    fn default() -> Self {
        Self {
            geometry_lowpass_sigma_quad: 0.,
            tile_quad: 24,
            grid_axis: 4,
            radius_quad: 3,
            minimum_peak: 0.85,
            minimum_contrast_variances: 16.,
            minimum_gradient_variances: 8.,
            minimum_information_ratio: 0.03,
            minimum_train: 4,
            minimum_heldout: 4,
            maximum_saved_disagreement_sensor: 0.15,
            maximum_refined_disagreement_sensor: 0.15,
            budget_bytes: 64 << 20,
        }
    }
}
#[derive(Clone, Debug)]
pub struct HeldOut {
    pub reference_quad_global: [f64; 2],
    pub measured_moving_quad_global: [f64; 2],
    pub saved_error_anchor_sensor: [f64; 2],
    pub refined_error_anchor_sensor: [f64; 2],
    pub peak: f32,
    pub information_ratio: f32,
}
#[derive(Clone, Debug)]
pub struct PairEvidence {
    /// Exact original coordinate/placement binding used to measure this pair.
    pub window: Window,
    pub input_color_pulls: [Similarity; 2],
    pub acquisitions: [u64; 2],
    pub plane: PlaneKind,
    pub original_crop_origins: [[usize; 2]; 2],
    pub trained_tiles: usize,
    pub heldout_tiles: Vec<HeldOut>,
    pub raw_fit_rms_source_quad: f32,
    pub fitted_pair_global: Option<Similarity>,
    pub maximum_saved_disagreement_sensor: f64,
    pub maximum_refined_disagreement_sensor: f64,
    pub saved_map_supported: bool,
    pub refined_map_supported: bool,
    pub refusal: Option<String>,
    pub reservation_bytes: usize,
}
/// Compact original-plane read/support witnesses. Each bit denotes one
/// same-color cell (both original green sites for GreenLuma). Roles/identities,
/// full geometry and crop origins are bound by the accompanying PairEvidence.
/// Caller reserves 4*ceil(side_quad^2/64)*8 bytes per retained witness.
#[derive(Clone, Debug, Default)]
pub struct OriginalFootprints {
    pub side_quad: usize,
    pub training: [Vec<u64>; 2],
    pub heldout: [Vec<u64>; 2],
}
impl OriginalFootprints {
    pub fn reservation_bytes(side_quad: usize) -> Result<usize> {
        side_quad
            .checked_mul(side_quad)
            .and_then(|n| n.checked_add(63))
            .map(|n| n / 64)
            .and_then(|n| n.checked_mul(32))
            .ok_or_else(|| "original footprint reservation overflow".into())
    }
}
pub struct WitnessedPair {
    pub evidence: PairEvidence,
    pub footprints: OriginalFootprints,
}
struct Patch {
    origin: [usize; 2],
    geometry: PlaneGeometry,
    values: Vec<f32>,
    valid: Vec<bool>,
    variance: f32,
    /// Variance of a centered unit-quad derivative after the exact filter.
    gradient_variance: f32,
    pull: Similarity,
}
fn finite_pull(t: Similarity) -> bool {
    [t.a.re, t.a.im, t.b.re, t.b.im]
        .iter()
        .all(|x| x.is_finite())
        && t.invert().is_some()
}
/// Same-color source-plane pull: physical site offset is preserved around the
/// exact stored full-guide fitting centre. Green luma's site offset is zero.
pub fn plane_pull(t: Similarity, kind: PlaneKind) -> Similarity {
    let offset = kind.offset();
    let site = Cx::new(offset[0] * 0.5 - 0.25, offset[1] * 0.5 - 0.25);
    Similarity {
        a: t.a,
        b: t.b + t.a * site - site,
    }
}
/// Convert a full-plane pull to equal-sized native crops, without recentering
/// the actual transform. Inverse conversion is used for returned pair geometry.
pub fn crop_pull(
    t: Similarity,
    full: PlaneGeometry,
    side: usize,
    origins: [[usize; 2]; 2],
) -> Similarity {
    let center = Cx::new(full.width as f64 * 0.5, full.height as f64 * 0.5);
    let half = side as f64 * 0.5;
    let reference = Cx::new(origins[0][0] as f64 + half, origins[0][1] as f64 + half) - center;
    let moving = Cx::new(origins[1][0] as f64 + half, origins[1][1] as f64 + half) - center;
    Similarity {
        a: t.a,
        b: t.a * reference + t.b - moving,
    }
}
pub fn uncrop_pull(
    t: Similarity,
    full: PlaneGeometry,
    side: usize,
    origins: [[usize; 2]; 2],
) -> Similarity {
    let center = Cx::new(full.width as f64 * 0.5, full.height as f64 * 0.5);
    let half = side as f64 * 0.5;
    let reference = Cx::new(origins[0][0] as f64 + half, origins[0][1] as f64 + half) - center;
    let moving = Cx::new(origins[1][0] as f64 + half, origins[1][1] as f64 + half) - center;
    Similarity {
        a: t.a,
        b: t.b - t.a * reference + moving,
    }
}
fn build(source: &OriginalView<'_>, window: Window, kind: PlaneKind) -> Result<Patch> {
    if source.source.geometry() != window.full
        || !source.gain.is_finite()
        || source.gain <= 0.
        || !source.frozen_expected_rgb.iter().all(|x| x.is_finite())
        || !source.color_pulls.iter().all(|t| finite_pull(*t))
    {
        return Err("invalid local original view".into());
    }
    for p in source.noise {
        if !p.gain_dn_per_e.is_finite()
            || p.gain_dn_per_e < 0.
            || !p.read_noise_e.is_finite()
            || p.read_noise_e < 0.
            || !p.levels.black.is_finite()
            || !p.levels.white.is_finite()
            || p.levels.white <= p.levels.black
            || p.levels.white > 65535.
        {
            return Err("invalid injected noise/levels".into());
        }
    }
    let pull = plane_pull(source.color_pulls[kind.index()], kind);
    let offset = kind.offset();
    let target = [
        (window.center_sensor[0] - offset[0]) * 0.5,
        (window.center_sensor[1] - offset[1]) * 0.5,
    ];
    let location = pull.apply_at(
        target[0],
        target[1],
        window.full.width as f64 * 0.5,
        window.full.height as f64 * 0.5,
    );
    let x = (location.0 - window.side_quad as f64 * 0.5).floor();
    let y = (location.1 - window.side_quad as f64 * 0.5).floor();
    if x < 0.
        || y < 0.
        || x + window.side_quad as f64 > window.full.width as f64
        || y + window.side_quad as f64 > window.full.height as f64
    {
        return Err("local original patch leaves active area".into());
    }
    let origin = [x as usize, y as usize];
    let geometry = PlaneGeometry {
        width: window.side_quad,
        height: window.side_quad,
    };
    let mut values = vec![0.; geometry.pixels()];
    let mut valid = vec![false; geometry.pixels()];
    for py in 0..geometry.height {
        let (r0, r1) = source.source.quad_rows(origin[1] + py);
        if r0.len() < 2 * window.full.width || r1.len() < 2 * window.full.width {
            return Err("short original CFA row".into());
        }
        for px in 0..geometry.width {
            let x = 2 * (origin[0] + px);
            let i = py * geometry.width + px;
            let raw = [r0[x], r0[x + 1], r1[x + 1], r1[x]];
            let value = |c: usize| (f32::from(raw[c]) - source.noise[c].levels.black) * source.gain;
            let ok = |c: usize| f32::from(raw[c]) < source.noise[c].levels.white;
            match kind {
                PlaneKind::Red => {
                    values[i] = value(0);
                    valid[i] = ok(0);
                }
                PlaneKind::Blue => {
                    values[i] = value(2);
                    valid[i] = ok(2);
                }
                PlaneKind::GreenLuma => {
                    values[i] = 0.5 * (value(1) + value(3));
                    valid[i] = ok(1) && ok(3);
                }
            }
        }
    }
    let expected = source.frozen_expected_rgb[kind.index()] / source.gain;
    let var = |c: usize| source.noise[c].variance(expected) * source.gain * source.gain;
    let variance = match kind {
        PlaneKind::Red => var(0),
        PlaneKind::Blue => var(2),
        PlaneKind::GreenLuma => 0.25 * (var(1) + var(3)),
    };
    Ok(Patch {
        origin,
        geometry,
        values,
        valid,
        variance,
        gradient_variance: 0.5 * variance,
        pull,
    })
}
/// Explicit finite original-plane Gaussian. It changes only the registration
/// objective, never the reconstruction samples or the delivered image.
fn geometry_kernel(sigma: f32) -> Result<Vec<f32>> {
    if !sigma.is_finite() || !(0. ..=3.).contains(&sigma) {
        return Err("invalid geometry low-pass sigma".into());
    }
    if sigma == 0. {
        return Ok(vec![1.]);
    }
    let radius = (3. * sigma).ceil() as isize;
    let mut kernel: Vec<_> = (-radius..=radius)
        .map(|x| (-0.5 * (x as f32 / sigma).powi(2)).exp())
        .collect();
    let total: f32 = kernel.iter().sum();
    for value in &mut kernel {
        *value /= total;
    }
    Ok(kernel)
}
fn geometry_lowpass(p: &mut Patch, kernel: &[f32]) {
    if kernel.len() == 1 {
        return;
    }
    let radius = kernel.len() / 2;
    let w = p.geometry.width;
    let h = p.geometry.height;
    let mut horizontal = vec![0.; p.values.len()];
    let mut horizontal_valid = vec![false; p.values.len()];
    for y in 0..h {
        for x in radius..w - radius {
            let index = y * w + x;
            if (0..kernel.len()).all(|k| p.valid[index + k - radius]) {
                let mut value = 0.;
                for (k, weight) in kernel.iter().enumerate() {
                    value += *weight * p.values[index + k - radius];
                }
                horizontal[index] = value;
                horizontal_valid[index] = true;
            }
        }
    }
    p.values.fill(0.);
    p.valid.fill(false);
    for y in radius..h - radius {
        for x in radius..w - radius {
            let index = y * w + x;
            if (0..kernel.len()).all(|k| horizontal_valid[(y + k - radius) * w + x]) {
                let mut value = 0.;
                for (k, weight) in kernel.iter().enumerate() {
                    value += *weight * horizontal[(y + k - radius) * w + x];
                }
                p.values[index] = value;
                p.valid[index] = true;
            }
        }
    }
    // Original independent noise is injected, never re-estimated from this
    // textured patch. A finite filter correlates neighbors: central derivative
    // variance is (Var(x+1)+Var(x-1)-2Cov(x+1,x-1))/4.
    let squares: f32 = kernel.iter().map(|v| v * v).sum();
    let lag_two: f32 = kernel
        .iter()
        .zip(kernel.iter().skip(2))
        .map(|(a, b)| a * b)
        .sum();
    let original_variance = p.variance;
    p.variance = original_variance * squares * squares;
    p.gradient_variance = 0.5 * original_variance * squares * (squares - lag_two);
}
fn supported(p: &Patch, x0: isize, y0: isize, x1: isize, y1: isize) -> bool {
    if x0 < 0 || y0 < 0 || x1 >= p.geometry.width as isize || y1 >= p.geometry.height as isize {
        return false;
    }
    (y0..=y1).all(|y| (x0..=x1).all(|x| p.valid[y as usize * p.geometry.width + x as usize]))
}
fn information(p: &Patch, x: usize, y: usize, tile: usize, policy: Policy) -> Option<f32> {
    if !supported(
        p,
        x as isize - 1,
        y as isize - 1,
        (x + tile) as isize,
        (y + tile) as isize,
    ) {
        return None;
    }
    let w = p.geometry.width;
    let mut xx = 0.;
    let mut xy = 0.;
    let mut yy = 0.;
    for y in y..y + tile {
        for x in x..x + tile {
            let i = y * w + x;
            let dx = 0.5 * (p.values[i + 1] - p.values[i - 1]);
            let dy = 0.5 * (p.values[i + w] - p.values[i - w]);
            xx += dx * dx;
            xy += dx * dy;
            yy += dy * dy;
        }
    }
    let n = (tile * tile) as f32;
    xx /= n;
    xy /= n;
    yy /= n;
    let spread = ((xx - yy).powi(2) + 4. * xy * xy).sqrt();
    let lo = 0.5 * (xx + yy - spread) - p.gradient_variance;
    let hi = (0.5 * (xx + yy + spread) - p.gradient_variance).max(0.);
    let ratio = lo / hi.max(f32::MIN_POSITIVE);
    (lo > 2. * policy.minimum_gradient_variances * p.gradient_variance
        && ratio >= policy.minimum_information_ratio)
        .then_some(ratio)
}
fn usable(
    reference: &Patch,
    moving: &Patch,
    t: Similarity,
    spot: (usize, usize),
    policy: Policy,
) -> Option<f32> {
    let (x, y) = spot;
    let information = information(reference, x, y, policy.tile_quad, policy)?;
    let probe = footprint::probe(spot, t, reference.geometry.width, policy);
    if !footprint::visit(reference, moving, probe, t.to_params(), None) {
        return None;
    }
    Some(information)
}
pub fn reservation_bytes(window: Window) -> Result<usize> {
    window
        .side_quad
        .checked_mul(window.side_quad)
        .and_then(|n| n.checked_mul(32))
        .and_then(|n| n.checked_add(1 << 20))
        .ok_or_else(|| "local registration reservation overflow".into())
}
pub fn measure_pair(
    first: &OriginalView<'_>,
    second: &OriginalView<'_>,
    window: Window,
    kind: PlaneKind,
    policy: Policy,
) -> Result<PairEvidence> {
    measure_pair_recorded(first, second, window, kind, policy, None)
}
/// Same numerical estimator with optional retained evidence for graph-wide
/// training/validation independence. No new NCC or fit is evaluated.
pub fn measure_pair_with_footprints(
    first: &OriginalView<'_>,
    second: &OriginalView<'_>,
    window: Window,
    kind: PlaneKind,
    policy: Policy,
) -> Result<WitnessedPair> {
    let mut footprints = OriginalFootprints::default();
    let evidence =
        measure_pair_recorded(first, second, window, kind, policy, Some(&mut footprints))?;
    Ok(WitnessedPair {
        evidence,
        footprints,
    })
}
fn measure_pair_recorded(
    first: &OriginalView<'_>,
    second: &OriginalView<'_>,
    window: Window,
    kind: PlaneKind,
    policy: Policy,
    mut witness: Option<&mut OriginalFootprints>,
) -> Result<PairEvidence> {
    let reserved = reservation_bytes(window)?;
    if window.full.width == 0
        || window.full.height == 0
        || window.side_quad < 64
        || window.side_quad > 384
        || window.center_sensor.iter().any(|x| !x.is_finite())
        || reserved > policy.budget_bytes
        || policy.budget_bytes > 64 << 20
        || first.acquisition_id == second.acquisition_id
    {
        return Err("invalid local window, budget or duplicate acquisition".into());
    }
    if !(8..=48).contains(&policy.tile_quad)
        || !(2..=8).contains(&policy.grid_axis)
        || !(1..=8).contains(&policy.radius_quad)
        || policy.minimum_train < 4
        || policy.minimum_heldout < 4
        || ![
            policy.minimum_peak,
            policy.minimum_contrast_variances,
            policy.minimum_gradient_variances,
            policy.minimum_information_ratio,
        ]
        .iter()
        .all(|x| x.is_finite() && *x > 0.)
        || policy.minimum_peak > 1.
        || policy.minimum_information_ratio > 1.
        || ![
            policy.maximum_saved_disagreement_sensor,
            policy.maximum_refined_disagreement_sensor,
        ]
        .iter()
        .all(|x| x.is_finite() && *x > 0.)
    {
        return Err("invalid local registration policy".into());
    }
    let kernel = geometry_kernel(policy.geometry_lowpass_sigma_quad)?;
    let filter_radius = kernel.len() / 2;
    let acquisitions = [first.acquisition_id, second.acquisition_id];
    let input_color_pulls = [
        first.color_pulls[kind.index()],
        second.color_pulls[kind.index()],
    ];
    let mut first = build(first, window, kind)?;
    let mut second = build(second, window, kind)?;
    geometry_lowpass(&mut first, &kernel);
    geometry_lowpass(&mut second, &kernel);
    let origins = [first.origin, second.origin];
    let global = Similarity::relative(first.pull, second.pull).ok_or("singular pair pull")?;
    let seed = crop_pull(global, window.full, window.side_quad, origins);
    let a = PlaneRef::from_geometry(&first.values, first.geometry).ok_or("reference shape")?;
    let b = PlaneRef::from_geometry(&second.values, second.geometry).ok_or("moving shape")?;
    let margin = policy.radius_quad as usize + 3 + filter_radius;
    let spots = tile_grid(
        a,
        policy.tile_quad,
        policy.grid_axis,
        policy.grid_axis,
        margin,
    )
    .ok_or("local tile grid does not fit")?;
    // Search footprints of neighboring train/held-out tiles must not overlap.
    let step = (window.side_quad - policy.tile_quad - 2 * margin) / (policy.grid_axis - 1);
    if step < policy.tile_quad + 2 * (policy.radius_quad as usize + 1 + filter_radius) {
        return Err("local train/held-out footprints overlap".into());
    }
    let mut train = Vec::new();
    let mut held = Vec::new();
    let mut train_reads = footprint::Footprint::new(window.side_quad);
    let mut held_seed_reads = footprint::Footprint::new(window.side_quad);
    for (i, spot) in spots.into_iter().enumerate() {
        let is_train = (i % policy.grid_axis + i / policy.grid_axis).is_multiple_of(2);
        // Eligibility itself depends on original signal/clipping. Include even
        // rejected candidate tiles; their data determined the admitted subset.
        footprint::visit(
            &first,
            &second,
            footprint::probe(spot, seed, window.side_quad, policy),
            seed.to_params(),
            Some(if is_train {
                &mut train_reads
            } else {
                &mut held_seed_reads
            }),
        );
        if let Some(info) = usable(&first, &second, seed, spot, policy) {
            if is_train {
                train.push(spot);
            } else {
                held.push((spot, info));
            }
        }
    }
    let mut held_original = held_seed_reads.original(filter_radius);
    if let Some(w) = witness.as_deref_mut() {
        w.side_quad = window.side_quad;
        w.training = train_reads.clone().original(filter_radius).packed();
        w.heldout = held_original.packed();
    }
    let mut out = PairEvidence {
        window,
        input_color_pulls,
        acquisitions,
        plane: kind,
        original_crop_origins: origins,
        trained_tiles: train.len(),
        heldout_tiles: Vec::new(),
        raw_fit_rms_source_quad: f32::NAN,
        fitted_pair_global: None,
        maximum_saved_disagreement_sensor: f64::INFINITY,
        maximum_refined_disagreement_sensor: f64::INFINITY,
        saved_map_supported: false,
        refined_map_supported: false,
        refusal: None,
        reservation_bytes: reserved,
    };
    if train.len() < policy.minimum_train {
        out.refusal = Some("insufficient independent, unclipped training structure".into());
        return Ok(out);
    }
    let cfg = AlignConfig {
        fine_tile: policy.tile_quad,
        fine_grid: (policy.grid_axis, policy.grid_axis),
        fine_radius: policy.radius_quad,
        margin,
        min_contrast: policy.minimum_contrast_variances * first.variance.max(second.variance),
        min_peak: policy.minimum_peak,
        min_tiles: policy.minimum_train,
        outlier_mads: 3.5,
        fine_iters: 3,
        warp_tiles: true,
        ..AlignConfig::shallow()
    };
    let mut training_supported = true;
    let mut observer = |trace: &PairTrace| {
        // Every attempted iteration matters, including rejected tiles and a
        // failed later pass whose earlier fit was retained by the aligner.
        for pass in &trace.fine_passes {
            let stage = &pass.stage.measurements;
            let Some(warp) = stage.seed.filter(|_| stage.warped_tiles_used) else {
                training_supported = false;
                continue;
            };
            for tile in &stage.tiles {
                training_supported &=
                    footprint::visit(&first, &second, tile.probe, warp, Some(&mut train_reads));
            }
        }
    };
    let fit_result = refine_pair_observed(a, b, &train, &cfg, seed, Some(&mut observer));
    let train_original = train_reads.original(filter_radius);
    if let Some(w) = witness.as_deref_mut() {
        w.training = train_original.packed();
    }
    let fit = match fit_result {
        Ok(fit) => fit,
        Err(e) => {
            out.refusal = Some(format!("training fit refused: {e:?}"));
            return Ok(out);
        }
    };
    if !training_supported {
        out.refusal = Some("training iteration reached unsupported original taps".into());
        return Ok(out);
    }
    if train_original.overlaps(&held_original) {
        out.refusal = Some("training and held-out original evidence overlap".into());
        return Ok(out);
    }
    let local = fit.similarity();
    let fitted = uncrop_pull(local, window.full, window.side_quad, origins);
    out.raw_fit_rms_source_quad = fit.rms;
    out.fitted_pair_global = Some(fitted);
    // Held-out eligibility may refuse validation, but its photons must never
    // remove or weight the training fit used by a later global training solve.
    if held.len() < policy.minimum_heldout {
        out.refusal = Some("insufficient independent, unclipped held-out structure".into());
        return Ok(out);
    }
    let fullcenter = (
        window.full.width as f64 * 0.5,
        window.full.height as f64 * 0.5,
    );
    let inverse_second = second.pull.invert().ok_or("singular source pull")?;
    for (spot, info) in held {
        let x = spot.0 as f64 + policy.tile_quad as f64 * 0.5;
        let y = spot.1 as f64 + policy.tile_quad as f64 * 0.5;
        let probe = footprint::probe(spot, local, window.side_quad, policy);
        let mut held_reads = footprint::Footprint::new(window.side_quad);
        footprint::visit(
            &first,
            &second,
            probe,
            local.to_params(),
            Some(&mut held_reads),
        );
        held_original.union(&held_reads.original(filter_radius));
        if let Some(w) = witness.as_deref_mut() {
            w.heldout = held_original.packed();
        }
        if train_original.overlaps(&held_original) {
            out.heldout_tiles.clear();
            out.refusal = Some("training and held-out original evidence overlap".into());
            return Ok(out);
        }
        if usable(&first, &second, local, spot, policy).is_none() {
            continue;
        }
        let m = ncc_tile_warped(a, b, probe, local.to_params(), &cfg);
        if m.status != TileStatus::Ok {
            continue;
        }
        let q = [x + first.origin[0] as f64, y + first.origin[1] as f64];
        let measured = [
            x + f64::from(m.dx) + second.origin[0] as f64,
            y + f64::from(m.dy) + second.origin[1] as f64,
        ];
        let saved = global.apply_at(q[0], q[1], fullcenter.0, fullcenter.1);
        let refined = fitted.apply_at(q[0], q[1], fullcenter.0, fullcenter.1);
        let vector = |pred: (f64, f64)| {
            let v = inverse_second.a * Cx::new(measured[0] - pred.0, measured[1] - pred.1);
            [2. * v.re, 2. * v.im]
        };
        out.heldout_tiles.push(HeldOut {
            reference_quad_global: q,
            measured_moving_quad_global: measured,
            saved_error_anchor_sensor: vector(saved),
            refined_error_anchor_sensor: vector(refined),
            peak: m.peak,
            information_ratio: info,
        });
    }
    if out.heldout_tiles.len() < policy.minimum_heldout {
        out.refusal = Some("too few held-out measurements after refinement".into());
        return Ok(out);
    }
    out.maximum_saved_disagreement_sensor = out
        .heldout_tiles
        .iter()
        .map(|h| h.saved_error_anchor_sensor[0].hypot(h.saved_error_anchor_sensor[1]))
        .fold(0., f64::max);
    out.maximum_refined_disagreement_sensor = out
        .heldout_tiles
        .iter()
        .map(|h| h.refined_error_anchor_sensor[0].hypot(h.refined_error_anchor_sensor[1]))
        .fold(0., f64::max);
    out.saved_map_supported =
        out.maximum_saved_disagreement_sensor <= policy.maximum_saved_disagreement_sensor;
    out.refined_map_supported =
        out.maximum_refined_disagreement_sensor <= policy.maximum_refined_disagreement_sensor;
    if !out.saved_map_supported {
        out.refusal = Some("saved placement fails held-out local displacement bound".into());
    }
    Ok(out)
}

#[cfg(test)]
#[path = "reconstruction-registration-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "reconstruction-registration-lowpass-tests.rs"]
mod lowpass_tests;

#[cfg(test)]
#[path = "reconstruction-registration-footprint-tests.rs"]
mod footprint_tests;
