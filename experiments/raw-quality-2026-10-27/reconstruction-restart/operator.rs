// Fixed one-restart unweighted least-squares synthesis. Historical source preserved.
// Only the CG recurrence resets once after iteration 8 if admission has failed.
// A is the ACTUAL public Pyramid::build; S is the ACTUAL public collapse.
// Transposes below scatter the finite, border-replicated operators, including
// repeated edge taps. They are not an infinite-grid filter approximation.
use anyhow::{ensure, Result};
use strehl_core::pyramid::{LevelSize, Pyramid, Workspace, KERNEL};

pub const MAX_ITERATIONS: usize = 32;
pub const RESTART_ITERATION: usize = 8;
pub const ERROR_RMS_LIMIT: f64 = 0.02; // camera DN; fixed before measurements

#[derive(Debug, Clone, serde::Serialize)]
pub struct ResidualObservation {
    pub iteration: usize,
    pub actual_residual_norm: f64,
    pub recursive_residual_norm: f64,
    pub residual_gap_norm: f64,
    pub error_bound_rms: f64,
    pub objective: f64,
    pub restart_applied: bool,
}

#[derive(Debug, Clone)]
pub struct Solve {
    pub restart_applied: bool,
    pub residual_trace: Vec<ResidualObservation>,
    // The last iterate is retained on refusal for diagnosis. Callers MUST NOT
    // apply it unless converged is true.
    pub image: Vec<f32>,
    pub iterations: usize,
    pub converged: bool,
    pub relative_residual: f64,
    pub error_bound_rms: f64,
    pub correction_rhs_norm: f64,
    pub correction_residual_norm: f64,
    pub correction_objective: f64,
    pub final_rounding_bound: f64, // RMS DN from the last x0+delta addition
    pub initial_objective: f64,
    pub objective: f64,
    pub refusal: Option<&'static str>,
}

fn check_sizes(sizes: &[LevelSize]) {
    assert!(!sizes.is_empty());
    assert!(sizes.iter().all(|s| s.width > 0 && s.height > 0));
    assert!(sizes.windows(2).all(|p| p[0].reduced() == p[1]));
}

fn check_bands(sizes: &[LevelSize], bands: &[Vec<f32>]) {
    check_sizes(sizes);
    assert_eq!(sizes.len(), bands.len());
    assert!(sizes.iter().zip(bands).all(|(s, b)| s.pixels() == b.len()));
}

pub fn analysis(sizes: &[LevelSize], image: &[f32]) -> Vec<Vec<f32>> {
    check_sizes(sizes);
    let mut p = Pyramid::zeros(sizes);
    p.build(image, &mut Workspace::new(sizes));
    (0..p.levels()).map(|k| p.level(k).to_vec()).collect()
}

pub fn synthesis(sizes: &[LevelSize], bands: &[Vec<f32>]) -> Vec<f32> {
    check_bands(sizes, bands);
    let mut p = Pyramid::zeros(sizes);
    for (k, b) in bands.iter().enumerate() { p.level_mut(k).copy_from_slice(b); }
    p.collapse(&mut Workspace::new(sizes))
}

fn clamp(i: isize, n: usize) -> usize { i.clamp(0, n as isize - 1) as usize }

// Exact transpose of reduce's horizontal-then-vertical finite matrix.
pub fn reduce_transpose(coarse: &[f32], fine_size: LevelSize) -> Vec<f32> {
    let c = fine_size.reduced();
    assert_eq!(coarse.len(), c.pixels());
    let mut middle = vec![0.0; c.width * fine_size.height];
    for y in 0..c.height {
        for (t, &w) in KERNEL.iter().enumerate() {
            let sy = clamp(2 * y as isize + t as isize - 2, fine_size.height);
            for x in 0..c.width { middle[sy * c.width + x] += w * coarse[y * c.width + x]; }
        }
    }
    let mut out = vec![0.0; fine_size.pixels()];
    for y in 0..fine_size.height {
        for x in 0..c.width {
            let value = middle[y * c.width + x];
            for (t, &w) in KERNEL.iter().enumerate() {
                let sx = clamp(2 * x as isize + t as isize - 2, fine_size.width);
                out[y * fine_size.width + sx] += w * value;
            }
        }
    }
    out
}

fn expansion_taps(x: usize, n: usize) -> [(usize, f32); 3] {
    let c = x / 2;
    if x % 2 == 0 {
        [(clamp(c as isize - 1, n), 0.125), (c, 0.75),
         (clamp(c as isize + 1, n), 0.125)]
    } else {
        [(c, 0.5), (clamp(c as isize + 1, n), 0.5), (c, 0.0)]
    }
}

// Exact transpose of expand's two-phase finite matrix, reverse separable order.
pub fn expand_transpose(fine: &[f32], fine_size: LevelSize) -> Vec<f32> {
    assert_eq!(fine.len(), fine_size.pixels());
    let c = fine_size.reduced();
    let mut middle = vec![0.0; fine_size.width * c.height];
    for y in 0..fine_size.height {
        for (sy, w) in expansion_taps(y, c.height) {
            if w == 0.0 { continue; }
            for x in 0..fine_size.width {
                middle[sy * fine_size.width + x] += w * fine[y * fine_size.width + x];
            }
        }
    }
    let mut out = vec![0.0; c.pixels()];
    for y in 0..c.height {
        for x in 0..fine_size.width {
            let value = middle[y * fine_size.width + x];
            for (sx, w) in expansion_taps(x, c.width) {
                if w != 0.0 { out[y * c.width + sx] += w * value; }
            }
        }
    }
    out
}

pub fn adjoint(sizes: &[LevelSize], bands: &[Vec<f32>]) -> Vec<f32> {
    check_bands(sizes, bands);
    let mut acc = bands.last().unwrap().clone();
    for k in (0..sizes.len() - 1).rev() {
        // Reverse C_k=G_k-E_k G_(k+1), then G_(k+1)=R_k G_k.
        let et = expand_transpose(&bands[k], sizes[k]);
        for (a, e) in acc.iter_mut().zip(et) { *a -= e; }
        let rt = reduce_transpose(&acc, sizes[k]);
        acc = bands[k].iter().zip(rt).map(|(c, r)| c + r).collect();
    }
    acc
}

pub fn synthesis_adjoint(sizes: &[LevelSize], image: &[f32]) -> Vec<Vec<f32>> {
    check_sizes(sizes);
    assert_eq!(image.len(), sizes[0].pixels());
    let mut out = vec![image.to_vec()];
    for k in 0..sizes.len() - 1 {
        out.push(expand_transpose(&out[k], sizes[k]));
    }
    out
}

// Only scalar reductions use f64; image, coefficient and iterative arithmetic
// remain f32. No private noise model or coefficient scaling is introduced.
fn dot(a: &[f32], b: &[f32]) -> f64 {
    assert_eq!(a.len(), b.len());
    a.iter().zip(b).map(|(&x, &y)| f64::from(x) * f64::from(y)).sum()
}

fn precondition(sizes: &[LevelSize], image: &[f32]) -> Vec<f32> {
    synthesis(sizes, &synthesis_adjoint(sizes, image))
}

fn coefficient_residual(sizes: &[LevelSize], targets: &[Vec<f32>], image: &[f32]) -> Vec<Vec<f32>> {
    let mut delta = analysis(sizes, image);
    for (d, c) in delta.iter_mut().zip(targets) {
        for (d, c) in d.iter_mut().zip(c) { *d = *c - *d; }
    }
    delta
}

fn residual(sizes: &[LevelSize], targets: &[Vec<f32>], image: &[f32]) -> (Vec<f32>, f64) {
    let delta = coefficient_residual(sizes, targets, image);
    (adjoint(sizes, &delta), delta.iter().map(|d| dot(d, d)).sum())
}

// SA=I, S has nonnegative entries and each row sums to #levels. Thus
// B=#levels*max(S^T 1) >= ||S||_2^2. In exact linear arithmetic, with H=A^T A,
// P=SS^T=H^-1+ZZ^T gives BOTH ||e|| <= B||r|| and
// ||e|| <= sqrt(B)*||S^T r||. Neither formula encloses f32 roundoff: independent
// dense-oracle and realizable-pyramid controls must qualify this implementation.
fn error_bound(sizes: &[LevelSize], r: &[f32], b: f64) -> f64 {
    let rt = synthesis_adjoint(sizes, r);
    let r2 = dot(r, r);
    let pr = rt.iter().map(|v| dot(v, v)).sum::<f64>();
    (b * r2.sqrt()).min((b * pr).sqrt()) / (r.len() as f64).sqrt()
}

pub fn reconstruct(sizes: &[LevelSize], targets: &[Vec<f32>], initial: &[f32]) -> Result<Solve> {
    reconstruct_inner(sizes, targets, initial, MAX_ITERATIONS)
}

// Refusal foil only. All real/cached/generated arms call reconstruct's fixed32.
#[cfg(test)]
pub(crate) fn reconstruct_with_cap(sizes: &[LevelSize], targets: &[Vec<f32>], initial: &[f32], cap: usize) -> Result<Solve> {
    ensure!(cap <= MAX_ITERATIONS, "test cap may only reduce the fixed maximum");
    reconstruct_inner(sizes, targets, initial, cap)
}

fn reconstruct_inner(sizes: &[LevelSize], targets: &[Vec<f32>], initial: &[f32], iteration_cap: usize) -> Result<Solve> {
    ensure!(!sizes.is_empty() && sizes.iter().all(|s| s.width > 0 && s.height > 0), "invalid level sizes");
    ensure!(sizes.windows(2).all(|p| p[0].reduced() == p[1]), "inconsistent level sizes");
    ensure!(targets.len() == sizes.len()
        && targets.iter().zip(sizes).all(|(v, s)| v.len() == s.pixels()), "target shape mismatch");
    ensure!(initial.len() == sizes[0].pixels(), "initial shape mismatch");
    ensure!(initial.iter().chain(targets.iter().flatten()).all(|v| v.is_finite()), "nonfinite solver input");
    let ones = vec![1.0; initial.len()];
    let max_column = synthesis_adjoint(sizes, &ones).iter().flatten()
        .copied().fold(0.0f32, f32::max);
    let b = sizes.len() as f64 * f64::from(max_column);
    // Solve the correction about the canonical collapse. In ideal linear
    // arithmetic this is the SAME objective. The explicitly retained f32
    // correction targets avoid repeated cancellation of high-DN A*x values.
    // Independent high-DN dense controls qualify this finite implementation.
    let correction_targets = coefficient_residual(sizes, targets, initial);
    let initial_objective = correction_targets.iter().map(|d| dot(d, d)).sum::<f64>();
    let rhs = adjoint(sizes, &correction_targets);
    let rhs_norm = dot(&rhs, &rhs).sqrt();
    let mut recursive_r = rhs;
    let mut delta = vec![0.0f32; initial.len()];
    let mut z = precondition(sizes, &recursive_r);
    let mut direction = z.clone();
    let mut rho = dot(&recursive_r, &z);
    let mut iterations = 0;
    let mut restart_applied = false;
    let mut residual_trace = Vec::new();
    let mut reason = "iteration-cap";
    loop {
        // Admission ALWAYS uses a newly evaluated actual correction residual;
        // recursive CG residuals alone never admit an iterate.
        let (actual_r, correction_objective) = residual(sizes, &correction_targets, &delta);
        let image: Vec<f32> = initial.iter().zip(&delta).map(|(x, d)| x + d).collect();
        let final_rounding_bound = (initial.iter().zip(&delta).zip(&image).map(|((&x, &d), &y)|
            (f64::from(x) + f64::from(d) - f64::from(y)).powi(2)).sum::<f64>()
            / initial.len() as f64).sqrt();
        let objective = coefficient_residual(sizes, targets, &image).iter().map(|d| dot(d, d)).sum::<f64>();
        let normal_norm = dot(&actual_r, &actual_r).sqrt();
        let relative_residual = if rhs_norm > 0.0 { normal_norm / rhs_norm }
            else if normal_norm == 0.0 { 0.0 } else { f64::INFINITY };
        let error_bound_rms = error_bound(sizes, &actual_r, b) + final_rounding_bound;
        let finite = image.iter().all(|v| v.is_finite()) && objective.is_finite()
            && normal_norm.is_finite() && error_bound_rms.is_finite();
        // Objective cannot increase. Equality permits an already-solved warm
        // start, including the literal constant/identity controls.
        let converged = finite && error_bound_rms <= ERROR_RMS_LIMIT
            && objective <= initial_objective;
        let restart_now = !converged && finite && reason == "iteration-cap"
            && iterations == RESTART_ITERATION && iterations < iteration_cap && !restart_applied;
        residual_trace.push(ResidualObservation {
            iteration: iterations,
            actual_residual_norm: normal_norm,
            recursive_residual_norm: dot(&recursive_r, &recursive_r).sqrt(),
            residual_gap_norm: actual_r.iter().zip(&recursive_r)
                .map(|(&a, &r)| (f64::from(a) - f64::from(r)).powi(2)).sum::<f64>().sqrt(),
            error_bound_rms,
            objective,
            restart_applied: restart_now,
        });
        if converged || iterations == iteration_cap || reason != "iteration-cap" || !finite {
            return Ok(Solve { restart_applied, residual_trace, image, iterations, converged, relative_residual,
                error_bound_rms, initial_objective, objective,
                correction_rhs_norm: rhs_norm, correction_residual_norm: normal_norm,
                correction_objective, final_rounding_bound,
                refusal: if converged { None } else if !finite { Some("nonfinite-iterate") }
                    else { Some(reason) } });
        }
        if restart_now {
            // The independently recomputed residual replaces the recursive one;
            // discard the old conjugate direction rather than mixing recurrences.
            // Same delta, targets, objective and preconditioner; no extra step.
            recursive_r.copy_from_slice(&actual_r);
            z = precondition(sizes, &recursive_r);
            direction.clone_from(&z);
            rho = dot(&recursive_r, &z);
            restart_applied = true;
        }
        let hd = adjoint(sizes, &analysis(sizes, &direction));
        let denominator = dot(&direction, &hd);
        if !(rho > 0.0 && rho.is_finite() && denominator > 0.0 && denominator.is_finite()) {
            reason = "nonpositive-or-nonfinite-curvature";
            continue;
        }
        let alpha = (rho / denominator) as f32;
        if !alpha.is_finite() { reason = "nonfinite-step"; continue; }
        for ((x, r), (p, hp)) in delta.iter_mut().zip(&mut recursive_r).zip(direction.iter().zip(hd)) {
            *x += alpha * p;
            *r -= alpha * hp;
        }
        iterations += 1;
        z = precondition(sizes, &recursive_r);
        let next_rho = dot(&recursive_r, &z);
        let beta = (next_rho / rho) as f32;
        if !(next_rho >= 0.0 && next_rho.is_finite() && beta.is_finite()) {
            reason = "nonfinite-recurrence";
            continue;
        }
        for (p, z) in direction.iter_mut().zip(&z) { *p = z + beta * *p; }
        rho = next_rho;
    }
}
