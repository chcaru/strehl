//! Separable box means by running sum.
//!
//! The focus measure needs a 3x3 and a 7x7 mean of every pixel of an 8.2 MP
//! plane, once per frame. A naive gather is 9 + 49 taps per pixel; the running
//! sum is 4 adds per pixel per axis regardless of radius.
//!
//! # Border policy: clamp the box, divide by the clamped count
//!
//! The window is intersected with the plane and the mean is taken over what
//! survives, so no read leaves the buffer and no border pixel gets a mean that
//! was diluted by invented zeros — which would manufacture a bright ring one
//! radius in from the edge and hand it to the focus measure as detail.
//!
//! The support therefore differs near the border. That is acceptable *here*
//! because the only thing consumed downstream is the ranking of the focus value
//! across frames at a fixed pixel, and every frame sees the identical clamped
//! support at that pixel.

use crate::plane::PlaneGeometry;

/// Mean of `src` over a `(2*radius+1)^2` window centred on each pixel, with the
/// window clamped to the plane.
///
/// `scratch` and `dst` must both be `geom.pixels()` long. `scratch` is
/// overwritten.
pub fn box_mean(
    src: &[f32],
    geom: PlaneGeometry,
    radius: usize,
    scratch: &mut [f32],
    dst: &mut [f32],
) {
    let (w, h) = (geom.width, geom.height);
    assert_eq!(src.len(), geom.pixels());
    assert_eq!(scratch.len(), geom.pixels());
    assert_eq!(dst.len(), geom.pixels());
    if w == 0 || h == 0 {
        return;
    }

    horizontal_sums(src, w, h, radius, scratch);
    vertical_means(scratch, w, h, radius, dst);
}

/// `scratch[y][x]` becomes the sum of `src[y][x-r ..= x+r]`, clamped.
fn horizontal_sums(src: &[f32], w: usize, h: usize, radius: usize, scratch: &mut [f32]) {
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        let out = &mut scratch[y * w..(y + 1) * w];
        // f64 accumulator: a sliding sum adds and subtracts once per pixel
        // across a 3516-wide row, so f32 rounding would random-walk into the
        // low DN differences the ring filter is trying to resolve.
        let mut sum: f64 = row[..(radius + 1).min(w)].iter().map(|v| *v as f64).sum();
        for x in 0..w {
            out[x] = sum as f32;
            let entering = x + 1 + radius;
            if entering < w {
                sum += row[entering] as f64;
            }
            if x >= radius {
                sum -= row[x - radius] as f64;
            }
        }
    }
}

/// `dst[y][x]` becomes the clamped-window mean, given horizontal sums in `sums`.
fn vertical_means(sums: &[f32], w: usize, h: usize, radius: usize, dst: &mut [f32]) {
    // Horizontal sample count per column, which depends only on x.
    let counts: Vec<f64> = (0..w)
        .map(|x| {
            let x0 = x.saturating_sub(radius);
            let x1 = (x + radius).min(w - 1);
            (x1 - x0 + 1) as f64
        })
        .collect();

    let mut column = vec![0.0f64; w];
    for y in 0..(radius + 1).min(h) {
        for (x, c) in column.iter_mut().enumerate() {
            *c += sums[y * w + x] as f64;
        }
    }

    for y in 0..h {
        let y0 = y.saturating_sub(radius);
        let y1 = (y + radius).min(h - 1);
        let ny = (y1 - y0 + 1) as f64;
        let out = &mut dst[y * w..(y + 1) * w];
        for (x, o) in out.iter_mut().enumerate() {
            *o = (column[x] / (counts[x] * ny)) as f32;
        }

        let entering = y + 1 + radius;
        if entering < h {
            for (x, c) in column.iter_mut().enumerate() {
                *c += sums[entering * w + x] as f64;
            }
        }
        if y >= radius {
            let leaving = y - radius;
            for (x, c) in column.iter_mut().enumerate() {
                *c -= sums[leaving * w + x] as f64;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Direct 2D gather with the same clamped-window rule. Deliberately naive.
    fn reference(src: &[f32], geom: PlaneGeometry, radius: usize) -> Vec<f32> {
        let (w, h) = (geom.width, geom.height);
        let mut out = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                let x0 = x.saturating_sub(radius);
                let x1 = (x + radius).min(w - 1);
                let y0 = y.saturating_sub(radius);
                let y1 = (y + radius).min(h - 1);
                let mut sum = 0.0f64;
                let mut n = 0u32;
                for yy in y0..=y1 {
                    for xx in x0..=x1 {
                        sum += src[yy * w + xx] as f64;
                        n += 1;
                    }
                }
                out[y * w + x] = (sum / n as f64) as f32;
            }
        }
        out
    }

    fn run(w: usize, h: usize, radius: usize, sample: impl Fn(usize, usize) -> f32) {
        let geom = PlaneGeometry {
            width: w,
            height: h,
        };
        let src: Vec<f32> = (0..h)
            .flat_map(|y| (0..w).map(move |x| (x, y)))
            .map(|(x, y)| sample(x, y))
            .collect();
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut got = vec![0.0f32; geom.pixels()];
        box_mean(&src, geom, radius, &mut scratch, &mut got);
        let want = reference(&src, geom, radius);
        for i in 0..geom.pixels() {
            let tol = 1e-3 * want[i].abs().max(1.0);
            assert!(
                (got[i] - want[i]).abs() <= tol,
                "w={w} h={h} r={radius} at {i}: got {} want {}",
                got[i],
                want[i]
            );
        }
    }

    #[test]
    fn running_sums_match_the_naive_gather() {
        for radius in [1usize, 3, 5] {
            for (w, h) in [(1, 1), (1, 9), (9, 1), (8, 5), (17, 13), (32, 4)] {
                run(w, h, radius, |x, y| {
                    ((x * 7 + y * 13) % 19) as f32 * 3.5 - 11.0
                });
            }
        }
    }

    #[test]
    fn window_wider_than_the_plane_degenerates_to_the_global_mean() {
        // radius 5 over a 3x3 plane clamps to the whole plane everywhere.
        run(3, 3, 5, |x, y| (x + 10 * y) as f32);
        let geom = PlaneGeometry {
            width: 3,
            height: 3,
        };
        let src: Vec<f32> = (0..9).map(|i| i as f32).collect();
        let mut scratch = vec![0.0f32; 9];
        let mut got = vec![0.0f32; 9];
        box_mean(&src, geom, 5, &mut scratch, &mut got);
        assert!(got.iter().all(|v| (v - 4.0).abs() < 1e-4));
    }

    #[test]
    fn a_constant_plane_stays_constant_including_at_the_border() {
        // Zero-padding instead of clamping would show up here as a dark rim.
        let geom = PlaneGeometry {
            width: 11,
            height: 7,
        };
        let src = vec![1234.5f32; geom.pixels()];
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut got = vec![0.0f32; geom.pixels()];
        box_mean(&src, geom, 3, &mut scratch, &mut got);
        assert!(got.iter().all(|v| (v - 1234.5).abs() < 1e-2), "{got:?}");
    }

    #[test]
    fn radius_zero_is_the_identity() {
        let geom = PlaneGeometry {
            width: 4,
            height: 3,
        };
        let src: Vec<f32> = (0..12).map(|i| i as f32 * 2.0).collect();
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut got = vec![0.0f32; geom.pixels()];
        box_mean(&src, geom, 0, &mut scratch, &mut got);
        assert_eq!(got, src);
    }
}
