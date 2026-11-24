//! Outline geometry (plan S1/S2). The JSON contract with the host and the
//! desktop is written by `strehl subject` (`crates/strehl-cli/src/subject-cmd.rs`).
//!
//! Pure data: rings of points normalised to the sensor's active area (0..1 on
//! both axes, x to the right, y down), filled even-odd, at most
//! [`MAX_RING_POINTS`] points a ring so one ring can become a Develop
//! `RegionShape::Polygon`. The raster every calibration reads is derived from
//! the rings with [`rasterize`].

/// Points a ring may hold; `strehl_edit::RegionShape::Polygon` accepts 3..=256.
pub const MAX_RING_POINTS: usize = 256;

/// One closed ring, normalised to the active area. The last point joins the
/// first; it is not repeated.
pub type Ring = Vec<[f32; 2]>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Source {
    /// One green site plane of RAW exposures, normalised by the injected
    /// noise model: the precise outline.
    Raw,
    /// Live-view JPEG frames: a loose first outline.
    LiveView,
}

/// How the focus threshold was set.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThresholdKind {
    /// Against the frame's own quiet population.
    Relative,
    /// No quiet population (the subject fills the frame): a fixed multiple
    /// of the noise floor.
    Absolute,
}

/// Even-odd fill of `rings` sampled at the centres of a `cols` x `rows` grid
/// whose cells measure `cell_norm` (normalised units) and start at the active
/// area's origin. Row-major.
pub fn rasterize(rings: &[Ring], cols: usize, rows: usize, cell_norm: [f64; 2]) -> Vec<bool> {
    let mut out = vec![false; cols * rows];
    let mut xs: Vec<f64> = Vec::new();
    for (j, row) in out.chunks_mut(cols.max(1)).enumerate().take(rows) {
        let yc = (j as f64 + 0.5) * cell_norm[1];
        xs.clear();
        for ring in rings {
            let n = ring.len();
            for k in 0..n {
                let p = ring[k];
                let q = ring[(k + 1) % n];
                let (py, qy) = (f64::from(p[1]), f64::from(q[1]));
                if (py > yc) != (qy > yc) {
                    let (px, qx) = (f64::from(p[0]), f64::from(q[0]));
                    xs.push(px + (yc - py) * (qx - px) / (qy - py));
                }
            }
        }
        xs.sort_by(f64::total_cmp);
        for &[a, b] in xs.as_chunks::<2>().0 {
            // Cells whose centre lies in [a, b).
            let first = (a / cell_norm[0] - 0.5).ceil().max(0.0) as usize;
            let end = ((b / cell_norm[0] - 0.5).ceil().max(0.0) as usize).min(cols);
            for cell in row.iter_mut().take(end).skip(first) {
                *cell = true;
            }
        }
    }
    out
}

/// Area enclosed by one ring (shoelace, absolute), in normalised units.
pub fn ring_area(ring: &[[f32; 2]]) -> f64 {
    let n = ring.len();
    let mut a = 0.0f64;
    for k in 0..n {
        let p = ring[k];
        let q = ring[(k + 1) % n];
        a += f64::from(p[0]) * f64::from(q[1]) - f64::from(q[0]) * f64::from(p[1]);
    }
    (0.5 * a).abs()
}
