//! Half-resolution CFA plane geometry, and row-pair access to a mosaiced frame.
//!
//! Every stage that works "per plane" agrees on one mapping: plane pixel
//! `(px, py)` owns the 2x2 sensor quad starting at `(2*px, 2*py)` in
//! **active-area** coordinates. The mapping lives here so that no stage
//! re-derives it, and so that the RGGB offsets are stated exactly once.

use crate::CfaPlane;

impl CfaPlane {
    /// Offset of this plane's sample inside an RGGB 2x2 quad.
    pub const fn rggb_offset(self) -> (usize, usize) {
        match self {
            CfaPlane::R => (0, 0),
            CfaPlane::G1 => (1, 0),
            CfaPlane::G2 => (0, 1),
            CfaPlane::B => (1, 1),
        }
    }
}

/// Dimensions of the four half-resolution planes carved out of an active area.
///
/// A plane pixel exists only where a whole quad does, so an odd active
/// dimension drops its final row or column rather than reading a partial quad.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PlaneGeometry {
    pub width: usize,
    pub height: usize,
}

impl PlaneGeometry {
    pub const fn from_active(active_width: usize, active_height: usize) -> Self {
        Self {
            width: active_width / 2,
            height: active_height / 2,
        }
    }

    pub const fn pixels(&self) -> usize {
        self.width * self.height
    }

    #[inline]
    pub const fn index(&self, px: usize, py: usize) -> usize {
        py * self.width + px
    }

    /// Active-area sensor coordinate of `plane`'s sample in the quad at
    /// `(px, py)`.
    #[inline]
    pub const fn sensor_coord(&self, plane: CfaPlane, px: usize, py: usize) -> (usize, usize) {
        let (dx, dy) = plane.rggb_offset();
        (2 * px + dx, 2 * py + dy)
    }
}

/// Row-pair access to one mosaiced frame, in active-area coordinates.
///
/// Row oriented rather than per pixel so the hot loops see slices and the
/// bounds checks hoist. Implemented by the decoder for a real frame and by
/// tests for synthetic ones.
pub trait QuadSource {
    fn geometry(&self) -> PlaneGeometry;

    /// Active-area sensor rows `2 * py` and `2 * py + 1`. Each must be at least
    /// `2 * self.geometry().width` samples long.
    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]);
}

/// Black-subtracted green luma, `L = (G1 + G2) / 2`, at plane resolution.
///
/// Greens carry most of the luminance and sit on the same lattice pitch as each
/// other, so this is the plane the focus measure runs on. Negative values clamp
/// to zero: read noise straddles the black level, but a negative "signal" has no
/// meaning downstream where it indexes the noise model.
pub fn green_luma<S: QuadSource + ?Sized>(src: &S, black: f32, dst: &mut [f32]) {
    let geom = src.geometry();
    assert_eq!(dst.len(), geom.pixels());

    let (g1x, g1y) = CfaPlane::G1.rggb_offset();
    let (g2x, g2y) = CfaPlane::G2.rggb_offset();

    for py in 0..geom.height {
        let (row0, row1) = src.quad_rows(py);
        let g1_row = if g1y == 0 { row0 } else { row1 };
        let g2_row = if g2y == 0 { row0 } else { row1 };
        let out = &mut dst[py * geom.width..(py + 1) * geom.width];
        for (px, o) in out.iter_mut().enumerate() {
            let g1 = (g1_row[2 * px + g1x] as f32 - black).max(0.0);
            let g2 = (g2_row[2 * px + g2x] as f32 - black).max(0.0);
            *o = 0.5 * (g1 + g2);
        }
    }
}

#[cfg(test)]
pub(crate) mod testing {
    use super::*;

    /// A synthetic mosaiced frame: `2*width x 2*height` samples, no padding.
    pub struct QuadGrid {
        pub geom: PlaneGeometry,
        pub data: Vec<u16>,
    }

    impl QuadGrid {
        /// Build from a per-quad closure returning `[R, G1, G2, B]`.
        pub fn new(width: usize, height: usize, f: impl Fn(usize, usize) -> [u16; 4]) -> Self {
            let geom = PlaneGeometry { width, height };
            let mut data = vec![0u16; 4 * width * height];
            let stride = 2 * width;
            let order = [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B];
            for py in 0..height {
                for px in 0..width {
                    let q = f(px, py);
                    for (plane, v) in order.iter().zip(q) {
                        let (x, y) = geom.sensor_coord(*plane, px, py);
                        data[y * stride + x] = v;
                    }
                }
            }
            Self { geom, data }
        }
    }

    impl QuadSource for QuadGrid {
        fn geometry(&self) -> PlaneGeometry {
            self.geom
        }
        fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
            let stride = 2 * self.geom.width;
            let a = &self.data[2 * py * stride..(2 * py + 1) * stride];
            let b = &self.data[(2 * py + 1) * stride..(2 * py + 2) * stride];
            (a, b)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::testing::QuadGrid;
    use super::*;

    #[test]
    fn rggb_offsets_match_the_mosaic_helper() {
        // The offset table and CfaPlane::rggb_at must not be able to disagree.
        for plane in CfaPlane::ALL {
            let (dx, dy) = plane.rggb_offset();
            assert_eq!(CfaPlane::rggb_at(dx, dy), plane);
        }
    }

    #[test]
    fn plane_geometry_is_the_a7c2_active_area_halved() {
        // Measured, M1: active area 7032 x 4688.
        let g = PlaneGeometry::from_active(7032, 4688);
        assert_eq!((g.width, g.height), (3516, 2344));
        assert_eq!(g.pixels(), 8_241_504);
    }

    #[test]
    fn odd_active_dimensions_drop_the_partial_quad() {
        let g = PlaneGeometry::from_active(7033, 4689);
        assert_eq!((g.width, g.height), (3516, 2344));
    }

    #[test]
    fn sensor_coords_walk_the_quad_at_twice_the_plane_pitch() {
        let g = PlaneGeometry::from_active(8, 8);
        assert_eq!(g.sensor_coord(CfaPlane::R, 0, 0), (0, 0));
        assert_eq!(g.sensor_coord(CfaPlane::G1, 0, 0), (1, 0));
        assert_eq!(g.sensor_coord(CfaPlane::G2, 0, 0), (0, 1));
        assert_eq!(g.sensor_coord(CfaPlane::B, 0, 0), (1, 1));
        assert_eq!(g.sensor_coord(CfaPlane::R, 3, 2), (6, 4));
        assert_eq!(g.sensor_coord(CfaPlane::B, 3, 2), (7, 5));
        // Every sample of the quad lands on the plane that owns it.
        for plane in CfaPlane::ALL {
            let (x, y) = g.sensor_coord(plane, 3, 2);
            assert_eq!(CfaPlane::rggb_at(x, y), plane);
        }
    }

    #[test]
    fn plane_index_is_row_major() {
        let g = PlaneGeometry {
            width: 5,
            height: 3,
        };
        assert_eq!(g.index(0, 0), 0);
        assert_eq!(g.index(4, 0), 4);
        assert_eq!(g.index(0, 1), 5);
        assert_eq!(g.index(4, 2), 14);
    }

    #[test]
    fn green_luma_averages_both_greens_after_black_subtraction() {
        let grid = QuadGrid::new(3, 2, |px, py| {
            let base = (100 * (py * 3 + px)) as u16;
            // R and B are deliberately wrong values; luma must ignore them.
            [9999, 512 + base, 512 + base + 20, 9999]
        });
        let mut luma = vec![0.0f32; grid.geom.pixels()];
        green_luma(&grid, 512.0, &mut luma);
        for py in 0..2 {
            for px in 0..3 {
                let base = (100 * (py * 3 + px)) as f32;
                assert_eq!(luma[grid.geom.index(px, py)], base + 10.0);
            }
        }
    }

    #[test]
    fn green_luma_clamps_below_black_rather_than_going_negative() {
        let grid = QuadGrid::new(1, 1, |_, _| [0, 400, 600, 0]);
        let mut luma = vec![0.0f32; 1];
        green_luma(&grid, 512.0, &mut luma);
        // G1 is 112 DN below black and clamps to 0; G2 is 88 above.
        assert_eq!(luma[0], 44.0);
    }
}
