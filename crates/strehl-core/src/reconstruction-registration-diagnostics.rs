//! Diagnostic-only census of every predefined registration patch.
//!
//! The ordinary estimator finishes first. Additional probes below do not enter
//! its training, eligibility, original-footprint witness or returned certificate.
//! They can explain an early refusal without presenting unconsumed observations
//! as independent held-out evidence for that fit.
use super::*;
use crate::align::TileMeasurement;

#[derive(Clone, Copy, Debug)]
pub struct Information {
    pub minimum_eigenvalue: f32,
    pub maximum_eigenvalue: f32,
    pub minimum_eigenvalue_required: f32,
    pub ratio: f32,
    pub minimum_ratio: f32,
    pub accepted: bool,
}
#[derive(Clone, Copy, Debug)]
pub struct Probe {
    pub reference_derivatives_supported: bool,
    pub original_search_supported: bool,
    pub information: Option<Information>,
    /// Evaluated whenever the full original search footprint is supported,
    /// even if the information gate failed. Diagnostic only in that case.
    pub ncc: Option<TileMeasurement>,
}
#[derive(Clone, Debug)]
pub struct Tile {
    pub index: usize,
    pub training: bool,
    pub reference_origin_crop_quad: [usize; 2],
    pub seed: Probe,
    pub fitted: Option<Probe>,
    /// An exact match to the ordinary estimator's retained held-out list.
    pub retained_heldout: bool,
}
pub struct DiagnosedPair {
    pub witnessed: WitnessedPair,
    pub tiles: Vec<Tile>,
}

fn information_values(p: &Patch, spot: (usize, usize), policy: Policy) -> Option<Information> {
    let (x, y) = spot;
    let tile = policy.tile_quad;
    if !supported(
        p,
        x as isize - 1,
        y as isize - 1,
        (x + tile) as isize,
        (y + tile) as isize,
    ) {
        return None;
    }
    // Keep the exact f32 order of the production information calculation. Tests
    // compare its decision/ratio directly; this duplicate is descriptive only.
    let w = p.geometry.width;
    let (mut xx, mut xy, mut yy) = (0., 0., 0.);
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
    let required = 2. * policy.minimum_gradient_variances * p.gradient_variance;
    Some(Information {
        minimum_eigenvalue: lo,
        maximum_eigenvalue: hi,
        minimum_eigenvalue_required: required,
        ratio,
        minimum_ratio: policy.minimum_information_ratio,
        accepted: lo > required && ratio >= policy.minimum_information_ratio,
    })
}
fn probe(
    reference: &Patch,
    moving: &Patch,
    spot: (usize, usize),
    t: Similarity,
    policy: Policy,
    cfg: &AlignConfig,
) -> Probe {
    let information = information_values(reference, spot, policy);
    let tile = footprint::probe(spot, t, reference.geometry.width, policy);
    let original_search_supported = footprint::visit(reference, moving, tile, t.to_params(), None);
    let ncc = original_search_supported.then(|| {
        let a = PlaneRef::from_geometry(&reference.values, reference.geometry).unwrap();
        let b = PlaneRef::from_geometry(&moving.values, moving.geometry).unwrap();
        ncc_tile_warped(a, b, tile, t.to_params(), cfg)
    });
    Probe {
        reference_derivatives_supported: information.is_some(),
        original_search_supported,
        information,
        ncc,
    }
}

/// Run the unchanged witnessed estimator, then inspect seed/fitted probes for
/// every predefined patch, including patches behind early-refusal boundaries.
/// Additional observations are not certified and must not be fed back as fits.
pub fn measure_pair(
    first: &OriginalView<'_>,
    second: &OriginalView<'_>,
    window: Window,
    kind: PlaneKind,
    policy: Policy,
) -> Result<DiagnosedPair> {
    let witnessed = super::measure_pair_with_footprints(first, second, window, kind, policy)?;
    let mut first = build(first, window, kind)?;
    let mut second = build(second, window, kind)?;
    let kernel = geometry_kernel(policy.geometry_lowpass_sigma_quad)?;
    geometry_lowpass(&mut first, &kernel);
    geometry_lowpass(&mut second, &kernel);
    let origins = [first.origin, second.origin];
    let global = Similarity::relative(first.pull, second.pull).ok_or("singular pair pull")?;
    let seed = crop_pull(global, window.full, window.side_quad, origins);
    let fitted = witnessed
        .evidence
        .fitted_pair_global
        .map(|t| crop_pull(t, window.full, window.side_quad, origins));
    let margin = policy.radius_quad as usize + 3 + kernel.len() / 2;
    let a = PlaneRef::from_geometry(&first.values, first.geometry).ok_or("reference shape")?;
    let spots = tile_grid(
        a,
        policy.tile_quad,
        policy.grid_axis,
        policy.grid_axis,
        margin,
    )
    .ok_or("local tile grid does not fit")?;
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
    let tiles = spots
        .into_iter()
        .enumerate()
        .map(|(index, spot)| {
            let q = [
                spot.0 as f64 + policy.tile_quad as f64 * 0.5 + origins[0][0] as f64,
                spot.1 as f64 + policy.tile_quad as f64 * 0.5 + origins[0][1] as f64,
            ];
            Tile {
                index,
                training: (index % policy.grid_axis + index / policy.grid_axis).is_multiple_of(2),
                reference_origin_crop_quad: [spot.0, spot.1],
                seed: probe(&first, &second, spot, seed, policy, &cfg),
                fitted: fitted.map(|t| probe(&first, &second, spot, t, policy, &cfg)),
                retained_heldout: witnessed
                    .evidence
                    .heldout_tiles
                    .iter()
                    .any(|h| h.reference_quad_global.map(f64::to_bits) == q.map(f64::to_bits)),
            }
        })
        .collect();
    Ok(DiagnosedPair { witnessed, tiles })
}
