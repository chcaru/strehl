// Experimental interpolation of existing NCC scores only. No image resampling.
use super::{AlignConfig, PlaneRef, SimilarityParams, TileMeasurement, TileProbe};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode { Parabolic, Lanczos }
#[derive(Clone, Copy, Debug)]
pub struct Outcome {
    pub offset: Option<(f32, f32)>,
    pub evaluations: usize,
    pub reason: &'static str,
    pub integer_peak: (usize, usize),
}
fn refused(reason: &'static str, evaluations: usize) -> Outcome {
    Outcome { offset: None, evaluations, reason, integer_peak: (0,0) }
}
pub fn parabolic(scores: &[f32], side: usize, x: usize, y: usize) -> (f32, f32) {
    let sc = |i: usize, j: usize| scores[j * side + i];
    (super::parabola(sc(x-1,y),sc(x,y),sc(x+1,y)),
     super::parabola(sc(x,y-1),sc(x,y),sc(x,y+1)))
}

// sinc(pi*x), its first derivative and second derivative. The Taylor branch
// avoids subtractive loss near zero; exact integers retain cardinal values.
fn sinc(x: f32) -> [f32; 3] {
    let p2 = std::f32::consts::PI * std::f32::consts::PI;
    if x.abs() < 0.1 {
        let x2 = x*x;
        return [1.0-p2*x2/6.0+p2*p2*x2*x2/120.0-p2*p2*p2*x2*x2*x2/5040.0,
            -p2*x/3.0+p2*p2*x*x2/30.0-p2*p2*p2*x*x2*x2/840.0,
            -p2/3.0+p2*p2*x2/10.0-p2*p2*p2*x2*x2/168.0];
    }
    let (v, c) = if x.fract() == 0.0 {
        (0.0, if (x as i32).rem_euclid(2) == 0 { 1.0 } else { -1.0 })
    } else {
        let t = std::f32::consts::PI*x;
        (t.sin()/t, t.cos())
    };
    let d = (c-v)/x;
    [v, d, -p2*v-2.0*d/x]
}
fn weights(offset: f32) -> [[f32; 3]; 9] {
    let mut w = [[0.0; 3]; 9];
    let mut sum = [0.0; 3];
    for (i, wi) in w.iter_mut().enumerate() {
        let x = offset-(i as f32-4.0);
        if x.abs() >= 4.0 { continue; }
        let a = sinc(x);
        let b = sinc(x/4.0);
        *wi = [a[0]*b[0], a[1]*b[0]+a[0]*b[1]/4.0,
            a[2]*b[0]+a[1]*b[1]/2.0+a[0]*b[2]/16.0];
        for k in 0..3 { sum[k] += wi[k]; }
    }
    for wi in &mut w {
        let [v, d, dd] = *wi;
        *wi = [v/sum[0], (d-v*sum[1]/sum[0])/sum[0],
            (dd-2.0*d*sum[1]/sum[0]-v*sum[2]/sum[0]
                +2.0*v*sum[1]*sum[1]/(sum[0]*sum[0]))/sum[0]];
    }
    w
}
// [value, dx, dy, dxx, dxy, dyy]. Subtract the integer peak from the
// scores before summing: normalized interpolation preserves that constant,
// and the offset/derivatives do not need it.
fn evaluate(local: &[f32; 81], x: f32, y: f32) -> Option<[f32; 6]> {
    let wx = weights(x);
    let wy = weights(y);
    let mut out = [0.0; 6];
    for j in 0..9 {
        for i in 0..9 {
            let v = local[j*9+i];
            out[0] += v*wx[i][0]*wy[j][0];
            out[1] += v*wx[i][1]*wy[j][0];
            out[2] += v*wx[i][0]*wy[j][1];
            out[3] += v*wx[i][2]*wy[j][0];
            out[4] += v*wx[i][1]*wy[j][1];
            out[5] += v*wx[i][0]*wy[j][2];
        }
    }
    out.iter().all(|v| v.is_finite()).then_some(out)
}

/// Fixed bounded Newton maximization of normalized radius-4 Lanczos scores.
/// Nine-by-nine finite union support covers both sides of the peak cell;
/// each noninteger point uses at most eight nonzero taps on each axis.
/// At most 80 full value/gradient/Hessian evaluations, no score extrapolation.
/// Newton steps use backtracking, with a maximum of eight trials per step.
/// A negative-definite Hessian and a <=1e-4-pixel Newton step establish local
/// convergence; a maximum on the original cell boundary is never accepted.
/// This does not certify absence of every possible interpolation-induced peak.
pub fn refine(scores: &[f32], side: usize, peak_x: usize, peak_y: usize) -> Outcome {
    let mut result = refine_inner(scores,side,peak_x,peak_y);
    result.integer_peak = (peak_x,peak_y);
    result
}
fn refine_inner(scores: &[f32], side: usize, peak_x: usize, peak_y: usize) -> Outcome {
    if side.checked_mul(side) != Some(scores.len()) || side < 9
        || peak_x < 4 || peak_y < 4 || peak_x >= side-4 || peak_y >= side-4 {
        return refused("support", 0);
    }
    if scores.iter().any(|v| !v.is_finite()) { return refused("nonfinite", 0); }
    let best = scores[peak_y*side+peak_x];
    for (i, &s) in scores.iter().enumerate() {
        if s > best { return refused("integer-peak", 0); }
        if s == best && i != peak_y*side+peak_x { return refused("ambiguous", 0); }
    }
    let mut local = [0.0; 81];
    for j in 0..9 { for i in 0..9 {
        local[j*9+i] = scores[(peak_y+j-4)*side+peak_x+i-4]-best;
    }}
    let (mut x, mut y) = parabolic(scores, side, peak_x, peak_y);
    if !x.is_finite() || !y.is_finite() || x.abs() >= 0.5 || y.abs() >= 0.5 {
        return refused("boundary", 0);
    }
    let mut evaluations = 1;
    let Some(mut current) = evaluate(&local,x,y) else { return refused("nonfinite", evaluations); };
    loop {
        let [_, gx, gy, hxx, hxy, hyy] = current;
        let determinant = hxx*hyy-hxy*hxy;
        if hxx >= 0.0 || hyy >= 0.0 || determinant <= 0.0 || !determinant.is_finite() {
            return refused("curvature", evaluations);
        }
        let sx = (hxy*gy-hyy*gx)/determinant;
        let sy = (hxy*gx-hxx*gy)/determinant;
        if !sx.is_finite() || !sy.is_finite() { return refused("nonfinite", evaluations); }
        if sx.abs().max(sy.abs()) <= 1e-4 {
            if x.abs() >= 0.5-1e-4 || y.abs() >= 0.5-1e-4 {
                return refused("boundary", evaluations);
            }
            return Outcome { offset: Some((x,y)), evaluations, reason: "accepted", integer_peak: (peak_x,peak_y) };
        }
        let mut fraction = 1.0;
        let mut next = None;
        for _ in 0..8 {
            let nx = x+fraction*sx;
            let ny = y+fraction*sy;
            if nx.abs() < 0.5 && ny.abs() < 0.5 {
                if evaluations == 80 { return refused("budget", evaluations); }
                evaluations += 1;
                let Some(trial) = evaluate(&local,nx,ny) else { return refused("nonfinite", evaluations); };
                // Armijo ascent. Equality may occur at f32 resolution, while
                // the independently evaluated derivatives continue to converge.
                if trial[0] >= current[0]+1e-4*fraction*(gx*sx+gy*sy) {
                    next = Some((nx,ny,trial));
                    break;
                }
            }
            fraction *= 0.5;
        }
        let Some((nx,ny,trial)) = next else { return refused("line-search", evaluations); };
        if nx == x && ny == y { return refused("stalled", evaluations); }
        (x,y,current) = (nx,ny,trial);
    }
}

pub fn ncc_tile_with_mode(
    reference: PlaneRef<'_>, moving: PlaneRef<'_>, probe: TileProbe,
    cfg: &AlignConfig, mode: Mode, diagnostic: &mut Option<Outcome>,
) -> TileMeasurement {
    *diagnostic = None;
    match mode {
        Mode::Parabolic => super::ncc_tile_impl::<false>(reference,moving,probe,cfg,Some(diagnostic)),
        Mode::Lanczos => super::ncc_tile_impl::<true>(reference,moving,probe,cfg,Some(diagnostic)),
    }
}
pub fn ncc_tile_warped_with_mode(
    reference: PlaneRef<'_>, moving: PlaneRef<'_>, probe: TileProbe,
    warp: SimilarityParams, cfg: &AlignConfig, mode: Mode, diagnostic: &mut Option<Outcome>,
) -> TileMeasurement {
    *diagnostic = None;
    match mode {
        Mode::Parabolic => super::ncc_tile_warped_impl::<false>(reference,moving,probe,warp,cfg,Some(diagnostic)),
        Mode::Lanczos => super::ncc_tile_warped_impl::<true>(reference,moving,probe,warp,cfg,Some(diagnostic)),
    }
}

#[cfg(test)]
mod tests {
    mod independent {
        include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/alignment-sinc-peak/independent-controls.rs"));
    }
    #[test]
    #[ignore = "root executes fixed independent controls with an explicit fresh output"]
    fn sinc_peak_literal_controls() {
        let receipt = independent::literal_controls(|scores,side,x,y| {
            let result = super::refine(scores,side,x,y);
            (result.offset,result.evaluations,result.reason)
        });
        let out = std::env::var_os("STREHL_SINC_PEAK_OUT").expect("explicit fresh receipt path");
        let file = std::fs::OpenOptions::new().write(true).create_new(true).open(out).unwrap();
        serde_json::to_writer_pretty(file,&receipt).unwrap();
        println!("SINC_PEAK_LITERAL_CONTROLS_PASS");
    }
}

#[cfg(test)]
mod consumer_tests {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/alignment-sinc-peak/consumer-tests.rs"));
}
