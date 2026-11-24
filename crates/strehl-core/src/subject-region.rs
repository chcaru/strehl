//! The subject as a region the calibrations and checks read (plan S4,
//! `docs/proposals/2026-11-subject-highlights-and-detail-plan.md`).
//!
//! The outline's rings are rasterised once at [`REGION_CELL_PX`] cells and
//! grown by a margin; a caller then asks whether a rectangle of the active
//! area (a focus-step tile, a witness tile) touches the subject, or for the
//! subject's bounding box, in the geometry of any plane. The outline is drawn
//! in one plane's geometry; a plane whose magnification differs by `scale`
//! (see [`plane_scale`]) sees it scaled about the active area's centre, the
//! same convention as the evidence's registration (`subject::assemble`).

use super::outline::{Ring, rasterize};

/// Sensor pixels per cell of the lookup raster.
pub const REGION_CELL_PX: usize = 8;

/// Magnification of the plane at focus `focus` against the outline's plane
/// at `reference`, for a rate of `rate_ppm` parts per million per focus
/// unit: `exp(rate * (focus - reference))`. 1 when any of them is unknown.
pub fn plane_scale(rate_ppm: Option<f64>, reference: Option<f64>, focus: Option<f64>) -> f64 {
    match (rate_ppm, reference, focus) {
        (Some(r), Some(a), Some(b)) if r.is_finite() && a.is_finite() && b.is_finite() => {
            (r * 1e-6 * (b - a)).exp()
        }
        _ => 1.0,
    }
}

/// An outline rasterised over an active area and grown by a margin.
#[derive(Clone, Debug)]
pub struct SubjectRegion {
    cols: usize,
    rows: usize,
    /// Active area, pixels.
    active: [usize; 2],
    /// Per cell, row-major: inside the outline or within the margin of it.
    inside: Vec<bool>,
    /// Cells inside the outline itself (before the margin).
    outline_cells: usize,
}

impl SubjectRegion {
    /// `rings` (normalised to an active area of `active` pixels, even-odd)
    /// rasterised at cell centres and grown by `margin_px` (a square of that
    /// half-width, rounded up to whole cells).
    pub fn new(rings: &[Ring], active: [usize; 2], margin_px: f64) -> Self {
        let cell = REGION_CELL_PX;
        let (cols, rows) = (active[0].div_ceil(cell), active[1].div_ceil(cell));
        let cell_norm = [
            cell as f64 / active[0].max(1) as f64,
            cell as f64 / active[1].max(1) as f64,
        ];
        let raster = rasterize(rings, cols, rows, cell_norm);
        let outline_cells = raster.iter().filter(|v| **v).count();
        let r = (margin_px.max(0.0) / cell as f64).ceil() as usize;
        let inside = if r == 0 {
            raster
        } else {
            dilate(&raster, cols, rows, r)
        };
        Self {
            cols,
            rows,
            active,
            inside,
            outline_cells,
        }
    }

    /// Whether the outline encloses nothing.
    pub fn is_empty(&self) -> bool {
        self.outline_cells == 0
    }

    /// Share of the active area inside the outline (without the margin).
    pub fn outline_share(&self) -> f64 {
        self.outline_cells as f64 / (self.cols * self.rows).max(1) as f64
    }

    fn centre(&self) -> [f64; 2] {
        [self.active[0] as f64 / 2.0, self.active[1] as f64 / 2.0]
    }

    /// Whether any part of the rectangle `[x0, y0, x1, y1)` (active pixels,
    /// in the geometry of a plane magnified by `scale` against the
    /// outline's) lies in the region.
    pub fn touches(&self, rect: [f64; 4], scale: f64) -> bool {
        let c = self.centre();
        let s = if scale.is_finite() && scale > 0.0 {
            scale
        } else {
            1.0
        };
        let back = |v: f64, k: usize| c[k] + (v - c[k]) / s;
        let cell = REGION_CELL_PX as f64;
        // Cells overlapping `[a, b)`, clipped to the grid (a rectangle
        // mapped past the edge overlaps none there).
        let span = |a: f64, b: f64, n: usize| -> (usize, usize) {
            let lo = ((a / cell).floor().max(0.0) as usize).min(n);
            let hi = ((b / cell).ceil().max(0.0) as usize).clamp(lo, n);
            (lo, hi)
        };
        let (x0, x1) = span(back(rect[0], 0), back(rect[2], 0), self.cols);
        let (y0, y1) = span(back(rect[1], 1), back(rect[3], 1), self.rows);
        (y0..y1).any(|y| self.inside[y * self.cols + x0..y * self.cols + x1].contains(&true))
    }

    /// Per tile of `tile_px` over the active area, `cols` x `rows` tiles
    /// row-major (the last ones may be partial): whether it touches the
    /// region, in the geometry of a plane magnified by `scale`.
    pub fn tiles(&self, tile_px: usize, cols: usize, rows: usize, scale: f64) -> Vec<bool> {
        let t = tile_px as f64;
        let (w, h) = (self.active[0] as f64, self.active[1] as f64);
        (0..rows)
            .flat_map(|ty| {
                (0..cols).map(move |tx| {
                    [
                        tx as f64 * t,
                        ty as f64 * t,
                        ((tx + 1) as f64 * t).min(w),
                        ((ty + 1) as f64 * t).min(h),
                    ]
                })
            })
            .map(|rect| self.touches(rect, scale))
            .collect()
    }

    /// The region's bounding box `[x0, y0, x1, y1)` in active pixels, in the
    /// geometry of a plane magnified by `scale`, clipped to the active area;
    /// `None` when the region is empty.
    pub fn bounds(&self, scale: f64) -> Option<[f64; 4]> {
        let (mut x0, mut y0, mut x1, mut y1) = (usize::MAX, usize::MAX, 0usize, 0usize);
        for (i, _) in self.inside.iter().enumerate().filter(|(_, v)| **v) {
            let (x, y) = (i % self.cols, i / self.cols);
            x0 = x0.min(x);
            y0 = y0.min(y);
            x1 = x1.max(x + 1);
            y1 = y1.max(y + 1);
        }
        if x0 == usize::MAX {
            return None;
        }
        let c = self.centre();
        let cell = REGION_CELL_PX as f64;
        let fwd = |v: f64, k: usize| (c[k] + (v - c[k]) * scale).clamp(0.0, self.active[k] as f64);
        Some([
            fwd(x0 as f64 * cell, 0),
            fwd(y0 as f64 * cell, 1),
            fwd(x1 as f64 * cell, 0),
            fwd(y1 as f64 * cell, 1),
        ])
    }
}

/// Square dilation by `r` cells (separable maximum).
fn dilate(v: &[bool], cols: usize, rows: usize, r: usize) -> Vec<bool> {
    let mut tmp = vec![false; v.len()];
    for y in 0..rows {
        let row = &v[y * cols..(y + 1) * cols];
        for x in 0..cols {
            let (a, b) = (x.saturating_sub(r), (x + r + 1).min(cols));
            tmp[y * cols + x] = row[a..b].contains(&true);
        }
    }
    let mut out = vec![false; v.len()];
    for y in 0..rows {
        let (a, b) = (y.saturating_sub(r), (y + r + 1).min(rows));
        for x in 0..cols {
            out[y * cols + x] = (a..b).any(|k| tmp[k * cols + x]);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn square(x0: f32, y0: f32, x1: f32, y1: f32) -> Ring {
        vec![[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    }

    /// A square in the middle of a 640 x 480 area: tiles touching it, its
    /// bounds, and the margin.
    #[test]
    fn tiles_and_bounds_of_a_square() {
        let ring = square(0.25, 0.25, 0.5, 0.5);
        let r = SubjectRegion::new(std::slice::from_ref(&ring), [640, 480], 0.0);
        assert!(!r.is_empty());
        assert!((r.outline_share() - 0.0625).abs() < 0.01);
        let b = r.bounds(1.0).unwrap();
        assert_eq!(b, [160.0, 120.0, 320.0, 240.0]);
        // 64 px tiles: 10 x 8; the square spans px 160-320 x 120-240.
        let t = r.tiles(64, 10, 8, 1.0);
        let inside: Vec<(usize, usize)> = (0..80)
            .filter(|i| t[*i])
            .map(|i| (i % 10, i / 10))
            .collect();
        assert_eq!(inside.first(), Some(&(2, 1)));
        assert_eq!(inside.last(), Some(&(4, 3)));
        assert_eq!(inside.len(), 9);
        // A 32 px margin reaches one tile further on each side.
        let m = SubjectRegion::new(&[ring], [640, 480], 32.0);
        assert_eq!(m.tiles(64, 10, 8, 1.0).iter().filter(|v| **v).count(), 16);
        assert_eq!(m.bounds(1.0).unwrap(), [128.0, 88.0, 352.0, 272.0]);
    }

    /// A plane magnified 10 % sees the outline 10 % farther from the centre.
    #[test]
    fn scale_maps_about_the_centre() {
        let r = SubjectRegion::new(&[square(0.6, 0.6, 0.704, 0.704)], [1000, 1000], 0.0);
        assert_eq!(r.bounds(1.0).unwrap(), [600.0, 600.0, 704.0, 704.0]);
        let b = r.bounds(1.1).unwrap();
        assert!(
            (b[0] - 610.0).abs() < 1e-6 && (b[2] - 724.4).abs() < 1e-6,
            "{b:?}"
        );
        // Pixel 705 is outside the drawn outline but inside the magnified one.
        assert!(!r.touches([705.0, 650.0, 706.0, 651.0], 1.0));
        assert!(r.touches([705.0, 655.0, 706.0, 656.0], 1.1));
        assert!(
            (plane_scale(Some(-13.0), Some(1000.0), Some(2000.0)) - (-0.013f64).exp()).abs()
                < 1e-12
        );
        assert_eq!(plane_scale(None, Some(1.0), Some(2.0)), 1.0);
        // A corner tile of a shrunk plane maps past the grid: no cells.
        let edge = SubjectRegion::new(&[square(0.5, 0.5, 1.0, 1.0)], [1000, 1000], 32.0);
        assert!(!edge.touches([990.0, 990.0, 1000.0, 1000.0], 0.9));
        assert!(edge.touches([990.0, 990.0, 1000.0, 1000.0], 1.0));
        let t = edge.tiles(64, 16, 16, 0.98);
        assert!(t[255] && !t[0]);
    }

    /// No rings: an empty region that touches nothing.
    #[test]
    fn an_empty_outline_touches_nothing() {
        let r = SubjectRegion::new(&[], [640, 480], 32.0);
        assert!(r.is_empty());
        assert!(r.bounds(1.0).is_none());
        assert!(!r.tiles(64, 10, 8, 1.0).contains(&true));
    }
}
