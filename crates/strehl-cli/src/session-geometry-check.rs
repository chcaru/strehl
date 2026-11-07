//! Direct post-placement geometric consistency between two frames.
//!
//! A tile-support ratio is only a proxy: changed lighting lowers correlation
//! even when the geometry is right, while a pose change leaves systematic local
//! displacement that no single similarity removes. This check warps one guide
//! into the other through the solved placement and measures the remaining
//! local displacement directly with zero-mean NCC on textured tiles.
use strehl_core::align::{Cx, PlaneRef, Similarity};

pub const TILE: usize = 48;
pub const RADIUS: i32 = 10;
pub const MIN_PEAK: f64 = 0.6;
pub const MIN_TILES: usize = 10;

#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct GeometricResidual {
    pub tiles: usize,
    /// Median remaining displacement, measurement-plane px.
    pub median: f64,
    pub p90: f64,
}

fn bilinear(plane: PlaneRef<'_>, x: f64, y: f64) -> Option<f64> {
    if !(x >= 0.0 && y >= 0.0) {
        return None;
    }
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    if x0 + 1 >= plane.width() || y0 + 1 >= plane.height() {
        return None;
    }
    let (fx, fy) = (x - x0 as f64, y - y0 as f64);
    let at = |x: usize, y: usize| f64::from(plane.at(x, y));
    let top = at(x0, y0) * (1.0 - fx) + at(x0 + 1, y0) * fx;
    let bottom = at(x0, y0 + 1) * (1.0 - fx) + at(x0 + 1, y0 + 1) * fx;
    Some(top * (1.0 - fy) + bottom * fy)
}

fn percentile(values: &mut [f64], q: f64) -> f64 {
    values.sort_by(f64::total_cmp);
    values[((values.len() - 1) as f64 * q).round() as usize]
}

/// Remaining displacement of `moving` against `reference` after `t`
/// (reference-centred to moving-centred). `None` with too few usable tiles.
pub fn measure(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    t: Similarity,
) -> Option<GeometricResidual> {
    let cr = Cx::new(
        reference.width() as f64 * 0.5,
        reference.height() as f64 * 0.5,
    );
    let cm = Cx::new(moving.width() as f64 * 0.5, moving.height() as f64 * 0.5);
    let r = RADIUS as usize;
    let window = TILE + 2 * r;
    let mut shifts = Vec::new();
    let margin = r + 2;
    let mut ty = margin;
    while ty + TILE + margin <= reference.height() {
        let mut tx = margin;
        'tile: while tx + TILE + margin <= reference.width() {
            let x0 = tx;
            tx += TILE;
            // Reference tile statistics.
            let mut tile = Vec::with_capacity(TILE * TILE);
            for y in ty..ty + TILE {
                for x in x0..x0 + TILE {
                    tile.push(f64::from(reference.at(x, y)));
                }
            }
            let mean = tile.iter().sum::<f64>() / tile.len() as f64;
            let var = tile.iter().map(|v| (v - mean) * (v - mean)).sum::<f64>();
            if var <= 1e-6 * tile.len() as f64 * mean.abs().max(1.0) {
                continue;
            }
            // Moving window warped into reference coordinates.
            let mut warped = vec![0.0; window * window];
            for wy in 0..window {
                for wx in 0..window {
                    let p = Cx::new((x0 + wx) as f64 - r as f64, (ty + wy) as f64 - r as f64);
                    let q = t.apply(p - cr) + cm;
                    let Some(v) = bilinear(moving, q.re, q.im) else {
                        continue 'tile;
                    };
                    warped[wy * window + wx] = v;
                }
            }
            let mut best = (f64::NEG_INFINITY, 0i32, 0i32);
            let mut second = f64::NEG_INFINITY;
            for dy in -RADIUS..=RADIUS {
                for dx in -RADIUS..=RADIUS {
                    let (ox, oy) = ((dx + RADIUS) as usize, (dy + RADIUS) as usize);
                    let mut s = 0.0;
                    let mut ss = 0.0;
                    let mut sx = 0.0;
                    for y in 0..TILE {
                        let row = (oy + y) * window + ox;
                        for x in 0..TILE {
                            let m = warped[row + x];
                            s += m;
                            ss += m * m;
                            sx += (tile[y * TILE + x] - mean) * m;
                        }
                    }
                    let n = (TILE * TILE) as f64;
                    let mvar = ss - s * s / n;
                    if mvar <= 0.0 {
                        continue;
                    }
                    let ncc = sx / (var * mvar).sqrt();
                    if ncc > best.0 {
                        if (dx - best.1).abs() > 2 || (dy - best.2).abs() > 2 {
                            second = second.max(best.0);
                        }
                        best = (ncc, dx, dy);
                    } else if (dx - best.1).abs() > 2 || (dy - best.2).abs() > 2 {
                        second = second.max(ncc);
                    }
                }
            }
            let on_edge = best.1.abs() == RADIUS || best.2.abs() == RADIUS;
            if best.0 >= MIN_PEAK && best.0 - second.max(0.0) > 0.05 && !on_edge {
                shifts.push(f64::from(best.1).hypot(f64::from(best.2)));
            }
        }
        ty += TILE;
    }
    if shifts.len() < MIN_TILES {
        return None;
    }
    let tiles = shifts.len();
    Some(GeometricResidual {
        tiles,
        median: percentile(&mut shifts, 0.5),
        p90: percentile(&mut shifts, 0.9),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scene(x: f64, y: f64) -> f32 {
        (500.0
            + 200.0 * ((x * 0.21).sin() * (y * 0.17).cos())
            + 150.0 * ((x * 0.07 + y * 0.11).sin())
            + 80.0 * ((x * 0.45).cos() * (y * 0.39).sin())) as f32
    }

    fn render(w: usize, h: usize, warp: impl Fn(f64, f64) -> (f64, f64), gain: f32) -> Vec<f32> {
        let mut d = vec![0.0; w * h];
        for y in 0..h {
            for x in 0..w {
                let (u, v) = warp(x as f64, y as f64);
                // Lighting change: a gain plus a horizontal shading ramp.
                d[y * w + x] = gain * (1.0 + 0.3 * x as f32 / w as f32) * scene(u, v);
            }
        }
        d
    }

    #[test]
    fn consistent_geometry_under_changed_lighting_has_small_residual() {
        let (w, h) = (400, 300);
        let reference = render(w, h, |x, y| (x, y), 1.0);
        let moving = render(w, h, |x, y| (x, y), 0.6);
        let r = PlaneRef::new(&reference, w, h).unwrap();
        let m = PlaneRef::new(&moving, w, h).unwrap();
        let out = measure(r, m, Similarity::IDENTITY).unwrap();
        assert!(out.median < 0.5, "{out:?}");
    }

    #[test]
    fn local_non_rigid_displacement_is_reported() {
        let (w, h) = (400, 300);
        let reference = render(w, h, |x, y| (x, y), 1.0);
        // A pose change: displacement grows across the frame (bend), up to 8 px.
        let moving = render(
            w,
            h,
            |x, y| (x + 8.0 * (y / 300.0).powi(2), y + 6.0 * (x / 400.0)),
            1.0,
        );
        let r = PlaneRef::new(&reference, w, h).unwrap();
        let m = PlaneRef::new(&moving, w, h).unwrap();
        let out = measure(r, m, Similarity::IDENTITY).unwrap();
        assert!(out.median > 2.0 && out.p90 > 4.0, "{out:?}");
        // A flat moving frame cannot be measured.
        let flat = vec![100.0; w * h];
        assert!(measure(r, PlaneRef::new(&flat, w, h).unwrap(), Similarity::IDENTITY).is_none());
    }
}
