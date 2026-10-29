//! Fixed native-grid antialias diagnostic. No resampling or coordinate change.
//! All supported values require the complete two-quad separable filter halo.
use rayon::prelude::*;
use strehl_core::plane::PlaneGeometry;
pub(super) const HALO: usize = 2;
pub(super) fn apply(values: &mut [f32], g: PlaneGeometry) {
    assert_eq!(values.len(), g.pixels());
    let mut horizontal = vec![f32::NAN; values.len()];
    horizontal
        .par_chunks_mut(g.width)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, value) in row
                .iter_mut()
                .enumerate()
                .take(g.width.saturating_sub(HALO))
                .skip(HALO)
            {
                let p = y * g.width + x;
                *value = (values[p - 2]
                    + 4.0 * values[p - 1]
                    + 6.0 * values[p]
                    + 4.0 * values[p + 1]
                    + values[p + 2])
                    * (1.0 / 16.0);
            }
        });
    values
        .par_chunks_mut(g.width)
        .enumerate()
        .for_each(|(y, row)| {
            if y < HALO || y + HALO >= g.height {
                row.fill(f32::NAN);
                return;
            }
            for (x, value) in row.iter_mut().enumerate() {
                let p = y * g.width + x;
                *value = (horizontal[p - 2 * g.width]
                    + 4.0 * horizontal[p - g.width]
                    + 6.0 * horizontal[p]
                    + 4.0 * horizontal[p + g.width]
                    + horizontal[p + 2 * g.width])
                    * (1.0 / 16.0);
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn native_filter_preserves_grid_and_has_finite_two_quad_dependency() {
        let g = PlaneGeometry {
            width: 32,
            height: 32,
        };
        let mut values = vec![42.0; g.pixels()];
        apply(&mut values, g);
        assert_eq!(values[16 * g.width + 16], 42.0);
        assert!(values[0].is_nan());
        let mut impulse = vec![0.0; g.pixels()];
        impulse[16 * g.width + 16] = 256.0;
        apply(&mut impulse, g);
        assert_eq!(impulse[16 * g.width + 16], 36.0);
        assert_eq!(impulse[14 * g.width + 14], 1.0);
        assert_eq!(impulse[13 * g.width + 16], 0.0);
        let mut checker: Vec<_> = (0..g.pixels())
            .map(|p| {
                if (p / g.width + p % g.width).is_multiple_of(2) {
                    100.0
                } else {
                    300.0
                }
            })
            .collect();
        apply(&mut checker, g);
        assert_eq!(checker[16 * g.width + 16], 200.0);
    }
}
