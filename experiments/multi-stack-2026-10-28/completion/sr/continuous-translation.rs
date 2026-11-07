//! Experimental continuous same-patch translation refinement for low-DN geometry.
//! Fixed photometric support; no residual pruning, sensor model fitting or new
//! acceptance threshold. Broad NCC supplies a seed and the caller keeps all
//! independent holdout/admission controls.
use strehl_core::align::{PlaneRef, Resampler, Similarity};

#[derive(Clone, Copy, Debug)]
pub struct Refined {
    pub displacement: [f64; 2],
    pub gain: f64,
    pub offset: f64,
    pub residual_mean_square: f64,
    pub iterations: usize,
}
#[derive(Clone, Copy)]
struct Pixel {
    a: f64,
    b: f64,
    gx: f64,
    gy: f64,
}
/// Coordinates and returned displacement are in the two equal-sized native
/// plane crops. `linear_pull` is their centered similarity; only translation is
/// refined, with the source scale/rotation frozen from independent train tiles.
pub fn refine(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    moving_valid: &[bool],
    spot: (usize, usize),
    size: usize,
    linear_pull: Similarity,
    initial_displacement: [f64; 2],
) -> Option<Refined> {
    if size < 8
        || size > 48
        || reference.width() != moving.width()
        || reference.height() != moving.height()
        || moving_valid.len() != moving.width() * moving.height()
        || spot.0.checked_add(size)? > reference.width()
        || spot.1.checked_add(size)? > reference.height()
        || !initial_displacement.iter().all(|v| v.is_finite())
    {
        return None;
    }
    let center = (
        reference.width() as f64 * 0.5,
        reference.height() as f64 * 0.5,
    );
    let tile_center = (
        spot.0 as f64 + size as f64 * 0.5,
        spot.1 as f64 + size as f64 * 0.5,
    );
    let mapped = linear_pull.apply_at(tile_center.0, tile_center.1, center.0, center.1);
    let seed = [
        tile_center.0 + initial_displacement[0] - mapped.0,
        tile_center.1 + initial_displacement[1] - mapped.1,
    ];
    let mut shift = seed;
    let mut pixels = Vec::with_capacity(size * size);
    let mut result = None;
    for iteration in 0..12 {
        pixels.clear();
        for y in spot.1..spot.1 + size {
            for x in spot.0..spot.0 + size {
                let p = linear_pull.apply_at(x as f64, y as f64, center.0, center.1);
                let (sx, sy) = (p.0 + shift[0], p.1 + shift[1]);
                let sample = |xx: f64, yy: f64| {
                    let v = Resampler::CatmullRom.sample_checked(moving, xx, yy)?;
                    let x0 = xx.floor() as usize;
                    let y0 = yy.floor() as usize;
                    if (y0 - 1..=y0 + 2)
                        .any(|y| (x0 - 1..=x0 + 2).any(|x| !moving_valid[y * moving.width() + x]))
                    {
                        return None;
                    }
                    Some(f64::from(v))
                };
                let b = sample(sx, sy)?;
                let epsilon = 0.01;
                let gx = (sample(sx + epsilon, sy)? - sample(sx - epsilon, sy)?) / (2. * epsilon);
                let gy = (sample(sx, sy + epsilon)? - sample(sx, sy - epsilon)?) / (2. * epsilon);
                let a = f64::from(reference.data()[y * reference.width() + x]);
                if ![a, b, gx, gy].into_iter().all(f64::is_finite) {
                    return None;
                }
                pixels.push(Pixel { a, b, gx, gy });
            }
        }
        let n = pixels.len() as f64;
        let means = pixels
            .iter()
            .fold([0.; 4], |mut v, p| {
                v[0] += p.a;
                v[1] += p.b;
                v[2] += p.gx;
                v[3] += p.gy;
                v
            })
            .map(|v| v / n);
        let mut bb = 0.;
        let mut ab = 0.;
        let mut bx = 0.;
        let mut by = 0.;
        for p in &pixels {
            let b = p.b - means[1];
            bb += b * b;
            ab += (p.a - means[0]) * b;
            bx += b * (p.gx - means[2]);
            by += b * (p.gy - means[3]);
        }
        if bb <= 1e-12 {
            return None;
        }
        let gain = ab / bb;
        if !gain.is_finite() || gain <= 0. {
            return None;
        }
        let offset = means[0] - gain * means[1];
        let mut h = [0.; 3];
        let mut rhs = [0.; 2];
        let mut residual = 0.;
        for p in &pixels {
            let b = p.b - means[1];
            let e = p.a - (gain * p.b + offset);
            // Eliminate constant offset and brightness gain from the Jacobian,
            // so gradients cannot turn a local brightness mismatch into motion.
            let gx = gain * (p.gx - means[2] - b * bx / bb);
            let gy = gain * (p.gy - means[3] - b * by / bb);
            h[0] += gx * gx;
            h[1] += gx * gy;
            h[2] += gy * gy;
            rhs[0] += gx * e;
            rhs[1] += gy * e;
            residual += e * e;
        }
        let trace = h[0] + h[2];
        let det = h[0] * h[2] - h[1] * h[1];
        if !trace.is_finite() || !det.is_finite() || trace <= 1e-12 || det <= trace * trace * 1e-5 {
            return None;
        }
        result = Some(Refined {
            displacement: [
                mapped.0 + shift[0] - tile_center.0,
                mapped.1 + shift[1] - tile_center.1,
            ],
            gain,
            offset,
            residual_mean_square: residual / n,
            iterations: iteration + 1,
        });
        let step = [
            (h[2] * rhs[0] - h[1] * rhs[1]) / det,
            (h[0] * rhs[1] - h[1] * rhs[0]) / det,
        ];
        let length = step[0].hypot(step[1]);
        if !length.is_finite() {
            return None;
        }
        if length < 1e-5 {
            break;
        }
        let scale = if length > 0.5 { 0.5 / length } else { 1. };
        shift[0] += step[0] * scale;
        shift[1] += step[1] * scale;
        if (shift[0] - seed[0]).hypot(shift[1] - seed[1]) > 1. {
            return None;
        }
    }
    result
}
