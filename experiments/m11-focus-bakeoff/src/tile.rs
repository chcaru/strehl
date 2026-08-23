//! Tiles: the whole measurement, cut down to what it actually depends on.
//!
//! Adapted from `experiments/m9-support/src/tile.rs` (same author project,
//! MIT OR Apache-2.0), which M9 verified against the shipped CLI. This is M11's
//! own copy — M9's tree is read-only for this milestone — with one addition:
//! both green planes are extracted over the **padded** tile, not just G1, so a
//! focus field can be computed on each of them independently.
//!
//! # Why tiles are exact here, and not an approximation
//!
//! The flat-ROI ratio depends only on the merged output inside the ROI. The
//! winner at an ROI pixel is a per-pixel argmax over the **regularised** focus
//! fields, so it depends on the unregularised focus field within `reg_radius`
//! of that pixel, which depends on the luma within `reg_radius +
//! support_radius`. So a tile that extends `margin = max(reg_radius) +
//! max(support_radius)` beyond the ROI on every side reproduces the full-plane
//! answer **bit for bit** for every pixel the ROI reads.
//!
//! That is asserted, not assumed: `selftest` group T compares a tile run
//! against a wider-margin run of the same measure and width and requires exact
//! equality of the winner map, and `xcheck` reproduces M2's published 1.253x.
//!
//! # Rule 7
//!
//! Every read goes through `Frame::quad_rows`, which is defined on the
//! **active area**. Nothing here can touch `rawler`'s zero padding.

use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::CfaPlane;
use strehl_raw::Frame;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Roi {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

impl Roi {
    pub fn pixels(&self) -> usize {
        self.width * self.height
    }

    pub fn parse(s: &str) -> Result<Roi, String> {
        let p: Vec<&str> = s.split(',').map(str::trim).collect();
        if p.len() != 4 {
            return Err(format!("expected X,Y,W,H, got {s:?}"));
        }
        let v: Result<Vec<usize>, _> = p.iter().map(|q| q.parse::<usize>()).collect();
        let v = v.map_err(|e| format!("{s:?}: {e}"))?;
        if v[2] == 0 || v[3] == 0 {
            return Err(format!("{s:?}: width and height must be non-zero"));
        }
        Ok(Roi {
            x: v[0],
            y: v[1],
            width: v[2],
            height: v[3],
        })
    }
}

impl std::fmt::Display for Roi {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{},{},{},{}", self.x, self.y, self.width, self.height)
    }
}

/// One frame's contribution to one ROI.
pub struct FrameTile {
    /// Black-subtracted `(G1+G2)/2`, clamped at zero, over the padded tile.
    /// This is exactly `strehl_core::plane::green_luma` restricted to the tile.
    pub luma: Vec<f32>,
    /// The same quantity **without** the clamp, over the ROI only. This is what
    /// `strehl-cli`'s `roi_green` produces and what the published 1.253x is
    /// computed from, so the ratio here is the same quantity as M2's.
    pub green: Vec<f32>,
    /// `G1 - black` over the padded tile.
    pub g1: Option<Vec<f32>>,
    /// `G2 - black` over the padded tile.
    pub g2: Option<Vec<f32>>,
    /// `G2 - black` over the ROI only, unclamped, for the decoupled placebo.
    pub g2_roi: Option<Vec<f32>>,
}

/// Geometry of a padded tile around an ROI.
#[derive(Clone, Copy, Debug)]
pub struct TileGeom {
    pub roi: Roi,
    pub margin: usize,
    pub geom: PlaneGeometry,
    pub x0: usize,
    pub y0: usize,
}

impl TileGeom {
    pub fn new(roi: Roi, margin: usize, plane: PlaneGeometry) -> Result<Self, String> {
        if roi.x < margin || roi.y < margin {
            return Err(format!(
                "ROI {roi} is closer than the {margin} px margin to the top-left of the plane"
            ));
        }
        if roi.x + roi.width + margin > plane.width || roi.y + roi.height + margin > plane.height {
            return Err(format!(
                "ROI {roi} plus a {margin} px margin does not fit inside the {}x{} plane",
                plane.width, plane.height
            ));
        }
        Ok(Self {
            roi,
            margin,
            geom: PlaneGeometry {
                width: roi.width + 2 * margin,
                height: roi.height + 2 * margin,
            },
            x0: roi.x - margin,
            y0: roi.y - margin,
        })
    }

    /// Index into the tile of ROI pixel `(i, j)`.
    #[inline]
    pub fn roi_index(&self, i: usize, j: usize) -> usize {
        (j + self.margin) * self.geom.width + (i + self.margin)
    }

    pub fn roi_geom(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.roi.width,
            height: self.roi.height,
        }
    }

    pub fn extract(&self, frame: &Frame, black: f32, with_planes: bool) -> FrameTile {
        let (g1x, g1y) = CfaPlane::G1.rggb_offset();
        let (g2x, g2y) = CfaPlane::G2.rggb_offset();
        let n = self.geom.pixels();
        let mut luma = Vec::with_capacity(n);
        let mut g1 = with_planes.then(|| Vec::with_capacity(n));
        let mut g2 = with_planes.then(|| Vec::with_capacity(n));

        for ty in 0..self.geom.height {
            let (row0, row1) = frame.quad_rows(self.y0 + ty);
            let g1_row = if g1y == 0 { row0 } else { row1 };
            let g2_row = if g2y == 0 { row0 } else { row1 };
            for tx in 0..self.geom.width {
                let px = self.x0 + tx;
                let a = (g1_row[2 * px + g1x] as f32 - black).max(0.0);
                let b = (g2_row[2 * px + g2x] as f32 - black).max(0.0);
                luma.push(0.5 * (a + b));
                if let Some(v) = g1.as_mut() {
                    v.push(a);
                }
                if let Some(v) = g2.as_mut() {
                    v.push(b);
                }
            }
        }

        let mut green = Vec::with_capacity(self.roi.pixels());
        let mut g2_roi = with_planes.then(|| Vec::with_capacity(self.roi.pixels()));
        for py in self.roi.y..self.roi.y + self.roi.height {
            let (row0, row1) = frame.quad_rows(py);
            let g1_row = if g1y == 0 { row0 } else { row1 };
            let g2_row = if g2y == 0 { row0 } else { row1 };
            for px in self.roi.x..self.roi.x + self.roi.width {
                let a = g1_row[2 * px + g1x] as f32 - black;
                let b = g2_row[2 * px + g2x] as f32 - black;
                green.push(0.5 * (a + b));
                if let Some(v) = g2_roi.as_mut() {
                    v.push(b);
                }
            }
        }

        FrameTile {
            luma,
            green,
            g1,
            g2,
            g2_roi,
        }
    }
}

/// Population mean and standard deviation, in f64, of an f32 slice.
///
/// Identical to `strehl-cli`'s `mean_and_sigma`, including the `/n` (not
/// `/(n-1)`) convention, so the numbers are the same quantity M2 published.
pub fn mean_and_sigma(v: &[f32]) -> (f64, f64) {
    if v.is_empty() {
        return (0.0, 0.0);
    }
    let n = v.len() as f64;
    let mean = v.iter().map(|x| *x as f64).sum::<f64>() / n;
    let var = v.iter().map(|x| (*x as f64 - mean).powi(2)).sum::<f64>() / n;
    (mean, var.sqrt())
}

/// The shipped argmax tie-break, copied verbatim from
/// `strehl_core::stack::Selection::beats` (which is private).
///
/// Ties go to the lower frame index; a NaN candidate never wins.
#[inline]
pub fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16) -> bool {
    focus > cur_focus || (focus == cur_focus && index < cur_index)
}

/// Mean central-difference gradient magnitude over the interior.
///
/// `AGENTS.md` rule 9: a sharpness metric never travels alone. This is the
/// detail-side control for the flat-ROI ratio, and it is the same quantity
/// SYNTHESIS fact 24 used to show that a mean's sigma looks harmless while its
/// gradient collapses.
pub fn mean_gradient(v: &[f32], geom: PlaneGeometry) -> f64 {
    let (w, h) = (geom.width, geom.height);
    if w < 3 || h < 3 {
        return 0.0;
    }
    let mut sum = 0.0f64;
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let dx = 0.5 * (v[y * w + x + 1] - v[y * w + x - 1]) as f64;
            let dy = 0.5 * (v[(y + 1) * w + x] - v[(y - 1) * w + x]) as f64;
            sum += (dx * dx + dy * dy).sqrt();
        }
    }
    sum / ((w - 2) * (h - 2)) as f64
}
