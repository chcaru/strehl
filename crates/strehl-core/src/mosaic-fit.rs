//! Sparse joint displacement fit. The zero-displacement prior fixes the local
//! deformation gauge symmetrically; no pass is a preferred appearance source.

use super::{
    Correspondence, ForwardMesh, MosaicError, ObservationRole, Result, checked, norm, sub,
    validate_correspondence,
};

#[derive(Clone, Copy, Debug)]
pub struct MeshFitOptions {
    pub smoothness: f64,
    pub tether: f64,
    pub focus_width_floor: f64,
    pub huber_delta: f64,
    pub irls_iterations: usize,
    pub cg_iterations: usize,
    pub relative_tolerance: f64,
    pub maximum_displacement: f64,
    pub max_vertices: usize,
    pub max_observations: usize,
    /// Additional workspace, excluding caller-owned seeds/observations.
    pub max_work_bytes: usize,
}
impl Default for MeshFitOptions {
    fn default() -> Self {
        Self {
            smoothness: 2.0,
            tether: 0.01,
            focus_width_floor: 0.5,
            huber_delta: 0.5,
            irls_iterations: 6,
            cg_iterations: 512,
            relative_tolerance: 1e-8,
            maximum_displacement: 256.0,
            max_vertices: 100_000,
            max_observations: 1_000_000,
            max_work_bytes: 512 * 1024 * 1024,
        }
    }
}
#[derive(Clone, Debug, Default)]
pub struct MeshFitReport {
    pub fitted_observations: usize,
    pub heldout_observations: usize,
    pub distinct_pass_edges: usize,
    pub pass_cycle_rank: usize,
    pub reserved_work_bytes: usize,
    pub cg_iterations: usize,
    pub maximum_displacement: f64,
    pub fit_rms: f64,
}
#[derive(Clone, Debug)]
struct Row {
    ids: [usize; 6],
    factors: [f64; 6],
    rhs: [f64; 2],
    weight: f64,
}
impl Row {
    fn dot(&self, values: &[f64]) -> f64 {
        self.ids
            .iter()
            .zip(&self.factors)
            .map(|(&id, &factor)| values[id] * factor)
            .sum()
    }
}
#[derive(Clone, Copy)]
struct Edge {
    a: usize,
    b: usize,
    weight: f64,
}

fn apply(
    rows: &[Row],
    weights: &[f64],
    edges: &[Edge],
    tether: f64,
    values: &[f64],
    output: &mut [f64],
) {
    for (dst, &value) in output.iter_mut().zip(values) {
        *dst = tether * value;
    }
    for (row, &weight) in rows.iter().zip(weights) {
        let value = row.dot(values) * weight;
        for (&id, &factor) in row.ids.iter().zip(&row.factors) {
            output[id] += factor * value;
        }
    }
    for edge in edges {
        let value = (values[edge.a] - values[edge.b]) * edge.weight;
        output[edge.a] += value;
        output[edge.b] -= value;
    }
}
fn dot(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b).map(|(a, b)| a * b).sum()
}

fn solve(
    rows: &[Row],
    weights: &[f64],
    edges: &[Edge],
    options: MeshFitOptions,
    axis: usize,
    values: &mut [f64],
) -> Result<usize> {
    let n = values.len();
    let mut rhs = vec![0.0; n];
    let mut diagonal = vec![options.tether; n];
    for (row, &weight) in rows.iter().zip(weights) {
        for (&id, &factor) in row.ids.iter().zip(&row.factors) {
            rhs[id] += factor * row.rhs[axis] * weight;
            diagonal[id] += factor * factor * weight;
        }
    }
    for edge in edges {
        diagonal[edge.a] += edge.weight;
        diagonal[edge.b] += edge.weight;
    }
    let threshold = options.relative_tolerance * dot(&rhs, &rhs).sqrt().max(1.0);
    let mut product = vec![0.0; n];
    apply(rows, weights, edges, options.tether, values, &mut product);
    let mut residual: Vec<f64> = rhs.iter().zip(&product).map(|(b, a)| b - a).collect();
    let mut z: Vec<f64> = residual.iter().zip(&diagonal).map(|(r, d)| r / d).collect();
    let mut direction = z.clone();
    let mut rz = dot(&residual, &z);
    for iteration in 0..options.cg_iterations {
        if dot(&residual, &residual).sqrt() <= threshold {
            return Ok(iteration);
        }
        apply(
            rows,
            weights,
            edges,
            options.tether,
            &direction,
            &mut product,
        );
        let denominator = dot(&direction, &product);
        checked(
            denominator.is_finite() && denominator > 0.0 && rz.is_finite(),
            "mosaic fit lost positive definite normal operator",
        )?;
        let alpha = rz / denominator;
        for i in 0..n {
            values[i] += alpha * direction[i];
            residual[i] -= alpha * product[i];
            z[i] = residual[i] / diagonal[i];
        }
        let next = dot(&residual, &z);
        let beta = next / rz;
        for i in 0..n {
            direction[i] = z[i] + beta * direction[i];
        }
        rz = next;
    }
    checked(
        dot(&residual, &residual).sqrt() <= threshold,
        "mosaic fit did not converge within iteration budget",
    )?;
    Ok(options.cg_iterations)
}

/// Fits all pass deformations jointly from direct correspondences. Held-out
/// observations are validated structurally but never enter the normal operator.
/// These meshes still require native held-out/loop and visibility qualification.
pub fn fit_meshes(
    seeds: &[ForwardMesh],
    observations: &[Correspondence],
    options: MeshFitOptions,
) -> Result<(Vec<ForwardMesh>, MeshFitReport)> {
    checked(seeds.len() >= 2, "mosaic fit requires at least two passes")?;
    checked(
        [
            options.smoothness,
            options.tether,
            options.focus_width_floor,
            options.huber_delta,
            options.relative_tolerance,
            options.maximum_displacement,
        ]
        .into_iter()
        .all(|x| x.is_finite() && x > 0.0)
            && options.irls_iterations > 0
            && options.cg_iterations > 0,
        "invalid mosaic fit options",
    )?;
    let mut offsets = Vec::with_capacity(seeds.len());
    let mut vertices = 0usize;
    let mut cells = 0usize;
    for seed in seeds {
        seed.validate()?;
        offsets.push(vertices);
        vertices = vertices
            .checked_add(seed.vertices.len())
            .ok_or(MosaicError("mesh vertex count overflow"))?;
        cells = cells
            .checked_add(seed.visibility.len())
            .ok_or(MosaicError("mesh cell count overflow"))?;
    }
    checked(
        vertices <= options.max_vertices && observations.len() <= options.max_observations,
        "mosaic fit exceeds geometry limits",
    )?;
    // n: x,y + six PCG vectors + output vertices/focus/visibility + sparse
    // grid edges. m: fixed sparse rows, IRLS weights, pass-pair receipts. This
    // deliberately over-reserves headers and clone storage as well.
    let reserved = vertices
        .checked_mul(256)
        .and_then(|n| {
            observations
                .len()
                .checked_mul(256)
                .and_then(|m| n.checked_add(m))
        })
        .and_then(|n| cells.checked_mul(8).and_then(|c| n.checked_add(c)))
        .ok_or(MosaicError("mosaic fit reservation overflow"))?;
    checked(
        reserved <= options.max_work_bytes,
        "mosaic fit exceeds workspace byte budget",
    )?;
    let mut rows = Vec::new();
    let mut links = std::collections::BTreeSet::new();
    let mut heldout = 0usize;
    for observation in observations {
        validate_correspondence(seeds, observation)?;
        if observation.role == ObservationRole::Heldout {
            heldout += 1;
            continue;
        }
        let a = observation.pass_a;
        let b = observation.pass_b;
        links.insert((a.min(b), a.max(b)));
        let (ia, wa, _) = seeds[a]
            .weights(observation.point_a)
            .ok_or(MosaicError("fit point outside source"))?;
        let (ib, wb, _) = seeds[b]
            .weights(observation.point_b)
            .ok_or(MosaicError("fit point outside source"))?;
        let pa = seeds[a]
            .map_source(observation.point_a)
            .ok_or(MosaicError("fit point outside source"))?;
        let pb = seeds[b]
            .map_source(observation.point_b)
            .ok_or(MosaicError("fit point outside source"))?;
        rows.push(Row {
            ids: [
                ia[0] + offsets[a],
                ia[1] + offsets[a],
                ia[2] + offsets[a],
                ib[0] + offsets[b],
                ib[1] + offsets[b],
                ib[2] + offsets[b],
            ],
            factors: [wa[0], wa[1], wa[2], -wb[0], -wb[1], -wb[2]],
            rhs: sub(pb, pa),
            weight: observation.weight,
        });
    }
    checked(!rows.is_empty(), "no measured mosaic fit constraints")?;
    let mut connected = vec![false; seeds.len()];
    connected[0] = true;
    loop {
        let mut changed = false;
        for &(a, b) in &links {
            if connected[a] != connected[b] {
                connected[a] = true;
                connected[b] = true;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    checked(
        connected.into_iter().all(|x| x),
        "disconnected measured mosaic pass graph",
    )?;
    let mut edges = Vec::with_capacity(vertices * 2);
    for (pass, seed) in seeds.iter().enumerate() {
        for y in 0..seed.rows {
            for x in 0..seed.columns {
                let a = y * seed.columns + x;
                for neighbor in [
                    if x + 1 < seed.columns {
                        Some(a + 1)
                    } else {
                        None
                    },
                    if y + 1 < seed.rows {
                        Some(a + seed.columns)
                    } else {
                        None
                    },
                ]
                .into_iter()
                .flatten()
                {
                    let fa = seed.focus[a];
                    let fb = seed.focus[neighbor];
                    let scale = if fa.usable && fb.usable {
                        let distance = f64::from((fa.ordinal - fb.ordinal).abs());
                        let width = f64::from(fa.width + fb.width).max(options.focus_width_floor);
                        1.0 / (1.0 + (distance / width).powi(2))
                    } else {
                        1.0
                    };
                    edges.push(Edge {
                        a: a + offsets[pass],
                        b: neighbor + offsets[pass],
                        weight: options.smoothness * scale,
                    });
                }
            }
        }
    }
    let mut weights: Vec<f64> = rows.iter().map(|r| r.weight).collect();
    let mut values = [vec![0.0; vertices], vec![0.0; vertices]];
    let mut report = MeshFitReport {
        fitted_observations: rows.len(),
        heldout_observations: heldout,
        distinct_pass_edges: links.len(),
        pass_cycle_rank: links.len() + 1 - seeds.len(),
        reserved_work_bytes: reserved,
        ..MeshFitReport::default()
    };
    for _ in 0..options.irls_iterations {
        for (axis, axis_values) in values.iter_mut().enumerate() {
            report.cg_iterations += solve(&rows, &weights, &edges, options, axis, axis_values)?;
        }
        for (row, weight) in rows.iter().zip(&mut weights) {
            let error = norm([
                row.dot(&values[0]) - row.rhs[0],
                row.dot(&values[1]) - row.rhs[1],
            ]);
            *weight = row.weight * (options.huber_delta / error.max(options.huber_delta));
        }
    }
    let mut output = seeds.to_vec();
    for (pass, mesh) in output.iter_mut().enumerate() {
        // A new fit has not been independently revalidated. Old witness hulls
        // must not survive a changed placement as cross-view certificates.
        mesh.join_hulls.iter_mut().for_each(Vec::clear);
        for visibility in &mut mesh.visibility {
            if *visibility == super::Visibility::ValidatedOverlap {
                *visibility = super::Visibility::SingleView;
            }
        }
        for (index, point) in mesh.vertices.iter_mut().enumerate() {
            let displacement = [
                values[0][index + offsets[pass]],
                values[1][index + offsets[pass]],
            ];
            let distance = norm(displacement);
            checked(
                distance.is_finite() && distance <= options.maximum_displacement,
                "mosaic displacement exceeds configured bound",
            )?;
            report.maximum_displacement = report.maximum_displacement.max(distance);
            point[0] += displacement[0];
            point[1] += displacement[1];
        }
    }
    report.fit_rms = (rows
        .iter()
        .map(|row| {
            let x = row.dot(&values[0]) - row.rhs[0];
            let y = row.dot(&values[1]) - row.rhs[1];
            x * x + y * y
        })
        .sum::<f64>()
        / rows.len() as f64)
        .sqrt();
    Ok((output, report))
}
