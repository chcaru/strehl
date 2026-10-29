//! Mosaic-only actual affine patch remeasurement. The matrices change where
//! native pixels are gathered, rather than merely refitting old displacements.
//! Each spatial site remains one witness, regardless of its overlapping tiles.
use super::*;
use strehl_core::align::{TileProbe, TileStatus, ncc_tile};

const ITERATIONS: usize = 5;

#[derive(Clone, Copy, Debug)]
struct Affine([f64; 6]);
impl Affine {
    fn from_similarity(t: Similarity, g: PlaneGeometry) -> Self {
        let zero = point(t, [0.0; 2], g);
        Self([t.a.re, -t.a.im, t.a.im, t.a.re, zero[0], zero[1]])
    }
    fn apply(self, p: [f64; 2]) -> [f64; 2] {
        let [a, b, c, d, tx, ty] = self.0;
        [a * p[0] + b * p[1] + tx, c * p[0] + d * p[1] + ty]
    }
    fn inverse(self) -> Option<Self> {
        let [a, b, c, d, tx, ty] = self.0;
        let det = a * d - b * c;
        if !self.valid() {
            return None;
        }
        Some(Self([
            d / det,
            -b / det,
            -c / det,
            a / det,
            (b * ty - d * tx) / det,
            (c * tx - a * ty) / det,
        ]))
    }
    fn valid(self) -> bool {
        let [a, b, c, d, _, _] = self.0;
        let det = a * d - b * c;
        let trace = a * a + b * b + c * c + d * d;
        let root = (trace * trace - 4.0 * det * det).max(0.0).sqrt();
        let min = ((trace - root) * 0.5).sqrt();
        let max = ((trace + root) * 0.5).sqrt();
        self.0.into_iter().all(f64::is_finite) && det > 0.0 && min >= 0.5 && max <= 2.0
    }
}

#[derive(Clone, Copy)]
struct Observation {
    p: [f64; 2],
    q: [f64; 2],
    peak: f32,
    center: bool,
}

fn solve3(mut a: [[f64; 4]; 3]) -> Option<[f64; 3]> {
    for col in 0..3 {
        let pivot = (col..3).max_by(|&i, &j| a[i][col].abs().total_cmp(&a[j][col].abs()))?;
        a.swap(col, pivot);
        let divisor = a[col][col];
        if !divisor.is_finite() || divisor.abs() < 1e-9 {
            return None;
        }
        for value in &mut a[col][col..] {
            *value /= divisor;
        }
        let row = a[col];
        for (i, values) in a.iter_mut().enumerate() {
            if i != col {
                let factor = values[col];
                for (v, p) in values[col..].iter_mut().zip(&row[col..]) {
                    *v -= factor * p;
                }
            }
        }
    }
    Some([a[0][3], a[1][3], a[2][3]])
}

fn fit(observations: &[Observation], omitted: Option<usize>) -> Option<Affine> {
    let n = observations
        .len()
        .checked_sub(usize::from(omitted.is_some()))?;
    if n < 3 {
        return None;
    }
    let mut center = [0.0; 2];
    for (i, o) in observations.iter().enumerate() {
        if Some(i) != omitted {
            for (v, p) in center.iter_mut().zip(o.p) {
                *v += p / n as f64;
            }
        }
    }
    let mut normal = [[0.0; 3]; 3];
    let mut rhs = [[0.0; 3]; 2];
    for (i, o) in observations.iter().enumerate() {
        if Some(i) == omitted {
            continue;
        }
        let p = [o.p[0] - center[0], o.p[1] - center[1], 1.0];
        for (j, row) in normal.iter_mut().enumerate() {
            for (k, value) in row.iter_mut().enumerate() {
                *value += p[j] * p[k];
            }
            for (axis, values) in rhs.iter_mut().enumerate() {
                values[j] += p[j] * o.q[axis];
            }
        }
    }
    let xy: Option<Vec<_>> = rhs
        .into_iter()
        .map(|values| {
            solve3(std::array::from_fn(|i| {
                [normal[i][0], normal[i][1], normal[i][2], values[i]]
            }))
        })
        .collect();
    let xy = xy?;
    let t = Affine([
        xy[0][0],
        xy[0][1],
        xy[1][0],
        xy[1][1],
        xy[0][2] - xy[0][0] * center[0] - xy[0][1] * center[1],
        xy[1][2] - xy[1][0] * center[0] - xy[1][1] * center[1],
    ]);
    t.valid().then_some(t)
}

fn residual(t: Affine, o: Observation) -> f64 {
    let p = t.apply(o.p);
    (p[0] - o.q[0]).hypot(p[1] - o.q[1])
}

fn corners(x: f64, y: f64, last_x: f64, last_y: f64) -> [[f64; 2]; 4] {
    [[x, y], [x, last_y], [last_x, y], [last_x, last_y]]
}

fn coherent_fit(
    observations: &[Observation],
    maximum_residual: f64,
) -> Option<(Affine, Vec<bool>)> {
    let center = observations.iter().position(|o| o.center)?;
    // A nomination cutoff only: final fit and all leave-one-tile-out predictions
    // still use the original stricter residual bar.
    let nomination_cutoff = 2.0 * maximum_residual;
    let mut hypotheses = Vec::new();
    if let Some(model) = fit(observations, None) {
        hypotheses.push(model);
    }
    for i in 0..observations.len() {
        for j in i + 1..observations.len() {
            for k in j + 1..observations.len() {
                if let Some(model) = fit(&[observations[i], observations[j], observations[k]], None)
                {
                    hypotheses.push(model);
                }
            }
        }
    }
    let mut best: Option<(usize, f64, Affine, Vec<bool>)> = None;
    for model in hypotheses {
        let keep: Vec<_> = observations
            .iter()
            .map(|&o| residual(model, o) <= nomination_cutoff)
            .collect();
        let kept: Vec<_> = observations
            .iter()
            .zip(&keep)
            .filter_map(|(&o, &k)| k.then_some(o))
            .collect();
        if !keep[center] || kept.len() < 6 {
            continue;
        }
        let Some(refitted) = fit(&kept, None) else {
            continue;
        };
        let errors: Vec<_> = kept.iter().map(|&o| residual(refitted, o)).collect();
        if errors.iter().any(|&e| e > nomination_cutoff) {
            continue;
        }
        let sum = errors.iter().map(|e| e * e).sum::<f64>();
        if best.as_ref().is_none_or(|(count, score, _, _)| {
            kept.len() > *count || (kept.len() == *count && sum < *score)
        }) {
            best = Some((kept.len(), sum, refitted, keep));
        }
    }
    best.map(|(_, _, model, keep)| (model, keep))
}

fn bilinear(plane: PlaneRef<'_>, p: [f64; 2]) -> Option<f32> {
    let g = plane.geometry();
    if !p.into_iter().all(f64::is_finite)
        || p[0] < 0.0
        || p[1] < 0.0
        || p[0].floor() + 1.0 >= g.width as f64
        || p[1].floor() + 1.0 >= g.height as f64
    {
        return None;
    }
    let x = p[0].floor() as usize;
    let y = p[1].floor() as usize;
    let fx = (p[0] - x as f64) as f32;
    let fy = (p[1] - y as f64) as f32;
    let values = [
        plane.data()[y * g.width + x],
        plane.data()[y * g.width + x + 1],
        plane.data()[(y + 1) * g.width + x],
        plane.data()[(y + 1) * g.width + x + 1],
    ];
    if !values.into_iter().all(f32::is_finite) {
        return None;
    }
    Some(
        (values[0] * (1.0 - fx) + values[1] * fx) * (1.0 - fy)
            + (values[2] * (1.0 - fx) + values[3] * fx) * fy,
    )
}

struct Measured {
    transform: Affine,
    rms: f32,
    peak: f32,
    used: usize,
}

#[allow(clippy::too_many_arguments)]
fn measure(
    a: PlaneRef<'_>,
    b: PlaneRef<'_>,
    p: [f64; 2],
    mut seed: Affine,
    config: &MosaicGeometryConfig,
    roles: Option<&[support::RoleWitness<'_>; 2]>,
    originals: Option<&[support::PixelWitness<'_>; 2]>,
    direction: &str,
    measurements: &mut Vec<NativeMeasurement>,
) -> Result<Measured> {
    ensure!(
        seed.valid(),
        "affine seed folds or exceeds bounded local scale"
    );
    let tile = config.native_tile;
    let radius = config.native_search_radius as usize;
    let positions = spots(p, a.geometry(), tile, config.native_search_radius)
        .context("affine native reference patch leaves source")?;
    let side = tile + 2 * radius;
    let mut cfg = AlignConfig::shallow();
    cfg.min_peak = config.native_minimum_peak;
    let mut result = None;
    for iteration in 0..ITERATIONS {
        let mut trace = NativeMeasurement {
            direction: format!("{direction}-affine"),
            termination: "measuring".into(),
            attempted_passes: iteration + 1,
            selected_pass: Some(iteration),
            seed: None,
            affine_seed: Some(seed.0),
            affine_fit: None,
            leave_one_tile_out_rms_quad: None,
            center_residual_quad: None,
            center_leave_one_out_error_quad: None,
            affine_footprints: Vec::new(),
            sampled_bounds_quad: None,
            plane_center: [0.0; 2],
            sample_step_quad: 1,
            rms_quad: None,
            peak_mean: None,
            used_tiles: 0,
            support_reserved: true,
            support_unclipped: true,
            observations: Vec::new(),
            kept: Vec::new(),
            initial_residuals: Vec::new(),
            final_residuals: Vec::new(),
            probes: Vec::new(),
            statuses: Vec::new(),
        };
        let mut observations = Vec::new();
        for &(x, y) in &positions {
            trace.probes.push([x, y, tile, radius]);
            let reference = corners(
                x as f64,
                y as f64,
                (x + tile - 1) as f64,
                (y + tile - 1) as f64,
            );
            let moving = corners(
                (x - radius) as f64,
                (y - radius) as f64,
                (x + tile + radius - 1) as f64,
                (y + tile + radius - 1) as f64,
            )
            .map(|q| seed.apply(q));
            trace.affine_footprints.push([reference, moving]);
            trace.support_reserved &= roles.is_none_or(|r| {
                r[0].rectangle(&reference, 0.0, 1) && r[1].rectangle(&moving, 1.0, 1)
            });
            trace.support_unclipped &= trace.support_reserved
                && originals.is_none_or(|o| {
                    o[0].rectangle(&reference, 0.0, 1) && o[1].rectangle(&moving, 1.0, 1)
                });
            if !trace.support_reserved || !trace.support_unclipped {
                trace
                    .statuses
                    .push("unsupported actual affine footprint".into());
                trace.termination =
                    "actual affine search footprint leaves reserved or unclipped support".into();
                measurements.push(trace);
                anyhow::bail!(
                    "actual affine search footprint leaves reserved or unclipped support"
                );
            }
            let mut reference_values = Vec::with_capacity(tile * tile);
            for row in y..y + tile {
                reference_values.extend_from_slice(
                    &a.data()[row * a.geometry().width + x..row * a.geometry().width + x + tile],
                );
            }
            let mut moving_values = Vec::with_capacity(side * side);
            for row in 0..side {
                for column in 0..side {
                    let q = seed.apply([(x - radius + column) as f64, (y - radius + row) as f64]);
                    let Some(value) = bilinear(b, q) else {
                        trace.support_unclipped = false;
                        trace
                            .statuses
                            .push("out-of-bounds affine bilinear taps".into());
                        trace.termination = "actual affine image footprint leaves source".into();
                        measurements.push(trace);
                        anyhow::bail!("actual affine image footprint leaves source");
                    };
                    moving_values.push(value);
                }
            }
            let measurement = ncc_tile(
                PlaneRef::from_geometry(
                    &reference_values,
                    PlaneGeometry {
                        width: tile,
                        height: tile,
                    },
                )
                .unwrap(),
                PlaneRef::from_geometry(
                    &moving_values,
                    PlaneGeometry {
                        width: side,
                        height: side,
                    },
                )
                .unwrap(),
                TileProbe {
                    tx: 0,
                    ty: 0,
                    size: tile,
                    predicted: (radius as f32, radius as f32),
                    radius: config.native_search_radius,
                },
                &cfg,
            );
            trace.statuses.push(format!("{:?}", measurement.status));
            if measurement.status == TileStatus::Ok {
                let center = [x as f64 + tile as f64 * 0.5, y as f64 + tile as f64 * 0.5];
                let shifted = [
                    center[0] + f64::from(measurement.dx) - radius as f64,
                    center[1] + f64::from(measurement.dy) - radius as f64,
                ];
                let q = seed.apply(shifted);
                observations.push(Observation {
                    p: center,
                    q,
                    peak: measurement.peak,
                    center: (x, y) == positions[4],
                });
                trace.observations.push([
                    center[0] as f32,
                    center[1] as f32,
                    (q[0] - center[0]) as f32,
                    (q[1] - center[1]) as f32,
                ]);
            }
        }
        trace.used_tiles = observations.len();
        let selected = if config.native_affine_robust {
            coherent_fit(&observations, config.maximum_native_residual)
        } else {
            (observations.len() >= 6)
                .then(|| fit(&observations, None))
                .flatten()
                .map(|f| (f, vec![true; observations.len()]))
        };
        let Some((fitted, keep)) = selected else {
            trace.termination = "insufficient affine tile support or singular/folded fit".into();
            measurements.push(trace);
            anyhow::bail!("insufficient affine tile support or singular/folded fit");
        };
        let errors: Vec<_> = observations.iter().map(|&o| residual(fitted, o)).collect();
        let kept: Vec<_> = observations
            .iter()
            .zip(&keep)
            .filter_map(|(&o, &k)| k.then_some(o))
            .collect();
        let rms = (errors
            .iter()
            .zip(&keep)
            .filter_map(|(&e, &k)| k.then_some(e * e))
            .sum::<f64>()
            / kept.len() as f64)
            .sqrt() as f32;
        let loo: Option<Vec<_>> = kept
            .iter()
            .enumerate()
            .map(|(i, &o)| fit(&kept, Some(i)).map(|t| residual(t, o)))
            .collect();
        let center_index = kept.iter().position(|o| o.center);
        let center_residual = center_index.map(|i| residual(fitted, kept[i]) as f32);
        let center_loo = center_index.and_then(|i| loo.as_ref().map(|e| e[i] as f32));
        let center_supported = center_residual
            .is_some_and(|e| f64::from(e) <= config.maximum_native_residual)
            && center_loo.is_some_and(|e| f64::from(e) <= config.maximum_native_residual);
        let loo_rms =
            loo.map(|e| (e.iter().map(|v| v * v).sum::<f64>() / e.len() as f64).sqrt() as f32);
        let peak = kept.iter().map(|o| o.peak).sum::<f32>() / kept.len() as f32;
        trace.affine_fit = Some(fitted.0);
        trace.rms_quad = Some(rms);
        trace.peak_mean = Some(peak);
        trace.leave_one_tile_out_rms_quad = loo_rms;
        trace.center_residual_quad = center_residual;
        trace.center_leave_one_out_error_quad = center_loo;
        trace.initial_residuals = observations
            .iter()
            .map(|&o| residual(seed, o) as f32)
            .collect();
        trace.final_residuals = errors.iter().map(|&e| e as f32).collect();
        trace.kept = keep;
        trace.used_tiles = kept.len();
        trace.termination = "remeasure fitted affine pixels".into();
        let movement = positions
            .iter()
            .map(|&(x, y)| {
                let q = [x as f64, y as f64];
                let a = seed.apply(q);
                let b = fitted.apply(q);
                (a[0] - b[0]).hypot(a[1] - b[1])
            })
            .fold(0.0_f64, f64::max);
        let finished =
            iteration + 1 == ITERATIONS || movement < strehl_core::align::FINE_CONVERGE_PX;
        if finished {
            trace.termination = "final affine image measurement".into();
        }
        measurements.push(trace);
        result = Some((
            Measured {
                transform: fitted,
                rms,
                peak,
                used: kept.len(),
            },
            loo_rms,
            center_supported,
        ));
        seed = fitted;
        if finished {
            break;
        }
    }
    let (result, loo, center_supported) = result.context("no affine image measurement")?;
    ensure!(
        !config.native_affine_robust || center_supported,
        "robust affine center tile lacks direct residual/leave-one-out support"
    );
    ensure!(
        f64::from(result.rms) <= config.maximum_native_residual,
        "affine native local fit residual exceeds configured bar: {} > {} quad pixels",
        result.rms,
        config.maximum_native_residual
    );
    ensure!(
        loo.is_some_and(|v| f64::from(v) <= config.maximum_native_residual),
        "affine leave-one-tile-out placement residual exceeds configured bar: {loo:?} > {} quad pixels",
        config.maximum_native_residual
    );
    Ok(result)
}

type RefinedMatch = ([f64; 2], f32, f32, f64, f32, usize, usize);

#[allow(clippy::too_many_arguments)]
pub(super) fn refine(
    a: PlaneRef<'_>,
    b: PlaneRef<'_>,
    pa: [f64; 2],
    pb: [f64; 2],
    seed: Similarity,
    config: &MosaicGeometryConfig,
    roles: Option<&[support::RoleWitness<'_>; 2]>,
    originals: Option<&[support::PixelWitness<'_>; 2]>,
    measurements: &mut Vec<NativeMeasurement>,
) -> Result<RefinedMatch> {
    ensure!(
        a.geometry() == b.geometry(),
        "affine native geometry differs"
    );
    let initial = Affine::from_similarity(seed, a.geometry());
    let forward = measure(
        a,
        b,
        pa,
        initial,
        config,
        roles,
        originals,
        "forward",
        measurements,
    )?;
    let reverse_roles = roles.map(|r| [r[1], r[0]]);
    let reverse_originals = originals.map(|o| [o[1], o[0]]);
    // Reverse is independently initialized from the nomination, not the fitted forward map.
    let reverse = measure(
        b,
        a,
        pb,
        initial.inverse().context("singular affine seed")?,
        config,
        reverse_roles.as_ref(),
        reverse_originals.as_ref(),
        "reverse",
        measurements,
    )?;
    let q = forward.transform.apply(pa);
    let back = reverse.transform.apply(q);
    let reciprocal = (back[0] - pa[0]).hypot(back[1] - pa[1]);
    ensure!(
        reciprocal <= config.maximum_reciprocal_error,
        "affine independent forward/reverse loop exceeds configured bar: {reciprocal} > {} quad pixels",
        config.maximum_reciprocal_error
    );
    Ok((
        q,
        forward.rms,
        reverse.rms,
        reciprocal,
        (forward.peak + reverse.peak) * 0.5,
        forward.used,
        reverse.used,
    ))
}

#[cfg(test)]
#[path = "session-mosaic-native-affine-tests.rs"]
mod tests;
