//! Per-pixel argmax selection — **the naive baseline, on purpose.**
//!
//! This is the thing `strehl` exists to replace. `AGENTS.md` rule 4 forbids a
//! raw per-band argmax from ever being a merge *reference*; this module is not
//! that. It is the named baseline artifact SYNTHESIS §5.1 requires and §8 step 0
//! schedules, so that every later quality claim is a measured delta against a
//! stacker that exists.
//!
//! It must therefore stay exactly as bad as the tools it stands in for: no
//! smoothing of the winner map, no top-k, no regularisation, no blending. The
//! defect it produces — argmax over N noisy frames systematically electing noise
//! spikes — is the measurement. See [`speckle_fraction`], which quantifies it.

use crate::plane::{PlaneGeometry, QuadSource};
use crate::{CfaPlane, Error, Result};

/// Running per-pixel winner over however many frames have been folded in.
#[derive(Debug, Clone)]
pub struct Selection {
    geom: PlaneGeometry,
    focus: Vec<f32>,
    index: Vec<u16>,
    r: Vec<u16>,
    g1: Vec<u16>,
    g2: Vec<u16>,
    b: Vec<u16>,
    frames: u32,
}

/// Sentinel for "no frame has won this pixel yet".
const NO_FRAME: u16 = u16::MAX;

impl Selection {
    pub fn new(geom: PlaneGeometry) -> Self {
        let n = geom.pixels();
        Self {
            geom,
            focus: vec![f32::NEG_INFINITY; n],
            index: vec![NO_FRAME; n],
            r: vec![0; n],
            g1: vec![0; n],
            g2: vec![0; n],
            b: vec![0; n],
            frames: 0,
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    pub fn focus(&self) -> &[f32] {
        &self.focus
    }
    pub fn index(&self) -> &[u16] {
        &self.index
    }
    pub fn plane(&self, p: CfaPlane) -> &[u16] {
        match p {
            CfaPlane::R => &self.r,
            CfaPlane::G1 => &self.g1,
            CfaPlane::G2 => &self.g2,
            CfaPlane::B => &self.b,
        }
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * (size_of::<f32>() + 5 * size_of::<u16>())
    }

    /// True where a frame has won. False only if every frame produced a
    /// non-finite focus value at that pixel, which cannot happen for finite
    /// input but is cheap to be able to assert.
    pub fn is_decided(&self, i: usize) -> bool {
        self.index[i] != NO_FRAME
    }

    /// Does candidate `(focus, index)` beat incumbent `(cur_focus, cur_index)`?
    ///
    /// Ties go to the lower frame index. Stating the tie-break explicitly rather
    /// than relying on visitation order is what makes [`Selection::absorb`]
    /// associative and commutative, so the streaming fold gives bit-identical
    /// output regardless of how the file list was partitioned across workers.
    /// A NaN candidate never wins, because every comparison against NaN is
    /// false.
    #[inline]
    fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16) -> bool {
        focus > cur_focus || (focus == cur_focus && index < cur_index)
    }

    /// Fold one frame in. `focus` is that frame's focus field at plane
    /// resolution.
    pub fn fold<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        src: &S,
        focus: &[f32],
    ) -> Result<()> {
        let geom = src.geometry();
        if geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (geom.width, geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        assert_eq!(focus.len(), self.geom.pixels());
        assert_ne!(frame_index, NO_FRAME, "frame index {NO_FRAME} is reserved");

        let (rx, ry) = CfaPlane::R.rggb_offset();
        let (g1x, g1y) = CfaPlane::G1.rggb_offset();
        let (g2x, g2y) = CfaPlane::G2.rggb_offset();
        let (bx, by) = CfaPlane::B.rggb_offset();
        let w = self.geom.width;

        for py in 0..self.geom.height {
            let (row0, row1) = src.quad_rows(py);
            let pick = |dy: usize| if dy == 0 { row0 } else { row1 };
            let (r_row, g1_row, g2_row, b_row) = (pick(ry), pick(g1y), pick(g2y), pick(by));
            let base = py * w;
            for px in 0..w {
                let i = base + px;
                let f = focus[i];
                if Self::beats(f, frame_index, self.focus[i], self.index[i]) {
                    self.focus[i] = f;
                    self.index[i] = frame_index;
                    self.r[i] = r_row[2 * px + rx];
                    self.g1[i] = g1_row[2 * px + g1x];
                    self.g2[i] = g2_row[2 * px + g2x];
                    self.b[i] = b_row[2 * px + bx];
                }
            }
        }
        self.frames += 1;
        Ok(())
    }

    /// Merge another worker's partial selection into this one.
    pub fn absorb(&mut self, other: &Selection) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: usize::MAX,
                got: (other.geom.width, other.geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        for i in 0..self.geom.pixels() {
            if Self::beats(other.focus[i], other.index[i], self.focus[i], self.index[i]) {
                self.focus[i] = other.focus[i];
                self.index[i] = other.index[i];
                self.r[i] = other.r[i];
                self.g1[i] = other.g1[i];
                self.g2[i] = other.g2[i];
                self.b[i] = other.b[i];
            }
        }
        self.frames += other.frames;
        Ok(())
    }

    /// Green as the output uses it: `(G1 + G2) / 2`, still in raw DN.
    pub fn green_mean(&self, i: usize) -> f32 {
        0.5 * (self.g1[i] as f32 + self.g2[i] as f32)
    }
}

/// Fraction of plane pixels whose winning frame index differs by more than
/// `tolerance` from the median index of its 3x3 neighbourhood.
///
/// Physical depth is piecewise smooth, so on a real scene the winner map should
/// be smooth bands with discontinuities only at depth edges. What is left after
/// allowing `tolerance` frames of slack is argmax electing a noise spike instead
/// of the in-focus frame. The neighbourhood is clamped at the border and
/// includes the centre pixel.
pub fn speckle_fraction(index: &[u16], geom: PlaneGeometry, tolerance: u16) -> f64 {
    let (w, h) = (geom.width, geom.height);
    assert_eq!(index.len(), geom.pixels());
    if w == 0 || h == 0 {
        return 0.0;
    }
    let mut speckled = 0u64;
    let mut window = [0u16; 9];
    for y in 0..h {
        for x in 0..w {
            let mut n = 0usize;
            for yy in y.saturating_sub(1)..=(y + 1).min(h - 1) {
                for xx in x.saturating_sub(1)..=(x + 1).min(w - 1) {
                    window[n] = index[yy * w + xx];
                    n += 1;
                }
            }
            let w_slice = &mut window[..n];
            w_slice.sort_unstable();
            let median = w_slice[n / 2];
            if index[y * w + x].abs_diff(median) > tolerance {
                speckled += 1;
            }
        }
    }
    speckled as f64 / geom.pixels() as f64
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::plane::testing::QuadGrid;

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// Frame `k` of a deterministic pseudo-stack, plus its focus field.
    fn frame(k: u16, w: usize, h: usize) -> (QuadGrid, Vec<f32>) {
        let grid = QuadGrid::new(w, h, |px, py| {
            let s = (k as usize * 1000 + px * 31 + py * 17) as u16;
            [s, s + 1, s + 2, s + 3]
        });
        let focus = (0..w * h)
            .map(|i| (((i * 2654435761) ^ (k as usize * 40503)) % 997) as f32)
            .collect();
        (grid, focus)
    }

    fn fold_order(order: &[u16], w: usize, h: usize) -> Selection {
        let mut sel = Selection::new(geom(w, h));
        for k in order {
            let (grid, focus) = frame(*k, w, h);
            sel.fold(*k, &grid, &focus).unwrap();
        }
        sel
    }

    fn same(a: &Selection, b: &Selection) {
        assert_eq!(a.index(), b.index());
        assert_eq!(a.focus(), b.focus());
        for p in CfaPlane::ALL {
            assert_eq!(a.plane(p), b.plane(p), "plane {p:?}");
        }
        assert_eq!(a.frames_folded(), b.frames_folded());
    }

    #[test]
    fn the_winner_is_the_frame_with_the_highest_focus() {
        let mut sel = Selection::new(geom(2, 1));
        let a = QuadGrid::new(2, 1, |px, _| [px as u16, 10, 20, 30]);
        let b = QuadGrid::new(2, 1, |px, _| [100 + px as u16, 11, 21, 31]);
        sel.fold(0, &a, &[5.0, 1.0]).unwrap();
        sel.fold(1, &b, &[4.0, 2.0]).unwrap();
        assert_eq!(sel.index(), &[0, 1]);
        assert_eq!(sel.plane(CfaPlane::R), &[0, 101]);
        assert_eq!(sel.plane(CfaPlane::G1), &[10, 11]);
    }

    #[test]
    fn ties_go_to_the_first_frame_in_either_fold_direction() {
        let a = QuadGrid::new(1, 1, |_, _| [7, 7, 7, 7]);
        let b = QuadGrid::new(1, 1, |_, _| [9, 9, 9, 9]);
        let mut forward = Selection::new(geom(1, 1));
        forward.fold(0, &a, &[3.0]).unwrap();
        forward.fold(1, &b, &[3.0]).unwrap();
        let mut backward = Selection::new(geom(1, 1));
        backward.fold(1, &b, &[3.0]).unwrap();
        backward.fold(0, &a, &[3.0]).unwrap();
        assert_eq!(forward.index(), &[0]);
        assert_eq!(backward.index(), &[0]);
        assert_eq!(backward.plane(CfaPlane::R), &[7]);
    }

    #[test]
    fn the_fold_is_order_independent() {
        let (w, h) = (13usize, 7usize);
        let a = fold_order(&[0, 1, 2, 3, 4, 5, 6], w, h);
        let b = fold_order(&[6, 5, 4, 3, 2, 1, 0], w, h);
        let c = fold_order(&[3, 0, 6, 1, 5, 2, 4], w, h);
        same(&a, &b);
        same(&a, &c);
    }

    #[test]
    fn absorb_is_associative_over_every_contiguous_partition() {
        let (w, h) = (13usize, 7usize);
        let whole = fold_order(&[0, 1, 2, 3, 4, 5, 6], w, h);

        // Every contiguous split point, reduced left-to-right and
        // right-to-left, must give the same answer as one sequential fold.
        for cut in 1..7usize {
            let all: Vec<u16> = (0..7).collect();
            let mut left = fold_order(&all[..cut], w, h);
            let right = fold_order(&all[cut..], w, h);
            left.absorb(&right).unwrap();
            same(&whole, &left);

            let mut right = fold_order(&all[cut..], w, h);
            let left = fold_order(&all[..cut], w, h);
            right.absorb(&left).unwrap();
            same(&whole, &right);
        }

        // And a three-way split reduced both ways round.
        let mut lr = fold_order(&[0, 1], w, h);
        lr.absorb(&fold_order(&[2, 3, 4], w, h)).unwrap();
        lr.absorb(&fold_order(&[5, 6], w, h)).unwrap();
        let mut rl = fold_order(&[5, 6], w, h);
        let mut mid = fold_order(&[2, 3, 4], w, h);
        mid.absorb(&rl.clone()).unwrap();
        rl = fold_order(&[0, 1], w, h);
        rl.absorb(&mid).unwrap();
        same(&whole, &lr);
        same(&whole, &rl);
    }

    #[test]
    fn absorbing_an_empty_selection_changes_nothing() {
        let (w, h) = (5usize, 5usize);
        let mut a = fold_order(&[0, 1, 2], w, h);
        let before = a.clone();
        a.absorb(&Selection::new(geom(w, h))).unwrap();
        assert_eq!(a.index(), before.index());
        assert_eq!(a.plane(CfaPlane::B), before.plane(CfaPlane::B));
    }

    #[test]
    fn a_mismatched_frame_is_rejected_rather_than_silently_cropped() {
        let mut sel = Selection::new(geom(4, 4));
        let small = QuadGrid::new(3, 4, |_, _| [1, 1, 1, 1]);
        let focus = vec![0.0; 12];
        assert!(matches!(
            sel.fold(0, &small, &focus),
            Err(Error::DimensionMismatch { .. })
        ));
        assert!(sel.absorb(&Selection::new(geom(3, 4))).is_err());
    }

    #[test]
    fn every_pixel_is_decided_after_one_frame() {
        let (grid, focus) = frame(0, 6, 6);
        let mut sel = Selection::new(geom(6, 6));
        sel.fold(0, &grid, &focus).unwrap();
        assert!((0..36).all(|i| sel.is_decided(i)));
    }

    #[test]
    fn a_smooth_index_map_has_no_speckle() {
        let g = geom(16, 16);
        // Depth-ordered bands, exactly what a physical scene should give.
        let idx: Vec<u16> = (0..g.pixels()).map(|i| ((i / 16) / 2) as u16).collect();
        assert_eq!(speckle_fraction(&idx, g, 2), 0.0);
    }

    #[test]
    fn an_isolated_wrong_winner_counts_as_speckle() {
        let g = geom(8, 8);
        let mut idx = vec![4u16; g.pixels()];
        idx[g.index(3, 3)] = 20;
        idx[g.index(5, 6)] = 0;
        // 20 vs median 4 and 0 vs median 4 both exceed a tolerance of 2.
        assert!((speckle_fraction(&idx, g, 2) - 2.0 / 64.0).abs() < 1e-12);
        // Slack of 4 forgives the second but not the first.
        assert!((speckle_fraction(&idx, g, 4) - 1.0 / 64.0).abs() < 1e-12);
    }

    #[test]
    fn a_depth_edge_is_not_counted_as_speckle() {
        // A hard step in depth: half the frame at index 2, half at 30. The
        // median is on one side or the other, never between, so a clean edge
        // must not register.
        let g = geom(16, 16);
        let idx: Vec<u16> = (0..g.pixels())
            .map(|i| if i % 16 < 8 { 2 } else { 30 })
            .collect();
        assert_eq!(speckle_fraction(&idx, g, 2), 0.0);
    }

    /// The border convention, pinned to exact counts.
    ///
    /// The window is clamped, not reflected and not skipped, so an edge pixel
    /// sees 6 neighbours and a corner pixel 4. With an even count `w[n / 2]` is
    /// the **upper** median, which is what makes the border asymmetric: the
    /// same pattern can speckle on one edge and not on the opposite one. The
    /// exact fractions below encode that choice, so changing it breaks these
    /// tests loudly rather than silently moving the headline percentage.
    ///
    /// The tool's reported 34.381% includes borders. On a 3516 x 2344 plane the
    /// border is 0.07% of pixels, which is why an independent re-derivation
    /// that excluded them landed at 34.385%.
    #[test]
    fn the_border_convention_is_clamped_with_an_upper_median() {
        let g = geom(16, 16);

        // A ramp of 4 per column. Every interior pixel equals its own
        // neighbourhood median, so nothing there can speckle. Column 0 sees
        // only columns 0 and 1; the upper median of {0,0,0,4,4,4} is 4, and
        // 4 - 0 exceeds the tolerance of 2. Column 15 sees columns 14 and 15,
        // whose upper median is column 15's own value, so it stays clean.
        let ramp: Vec<u16> = (0..g.pixels()).map(|i| 4 * (i % 16) as u16).collect();
        assert_eq!(speckle_fraction(&ramp, g, 2), 16.0 / 256.0);

        // The same ramp at a step of 1 is inside the tolerance everywhere.
        let gentle: Vec<u16> = (0..g.pixels()).map(|i| (i % 16) as u16).collect();
        assert_eq!(speckle_fraction(&gentle, g, 2), 0.0);

        // A constant map is the trivial floor.
        assert_eq!(speckle_fraction(&vec![9u16; g.pixels()], g, 2), 0.0);

        // The ramp above fixes how *many* border pixels speckle but not which,
        // because flipping to the lower median moves the effect from column 0
        // to column 15 and leaves the count identical. This pair is asymmetric
        // and fixes the side: with the upper median a **dark** edge column
        // against a bright field speckles, and a **bright** edge column against
        // a dark field does not. Only `w[n / 2]` satisfies both.
        let e = geom(4, 4);
        let dark_edge: Vec<u16> = (0..e.pixels())
            .map(|i| if i % 4 == 0 { 0 } else { 20 })
            .collect();
        let bright_edge: Vec<u16> = (0..e.pixels())
            .map(|i| if i % 4 == 0 { 20 } else { 0 })
            .collect();
        assert_eq!(speckle_fraction(&dark_edge, e, 2), 4.0 / 16.0);
        assert_eq!(speckle_fraction(&bright_edge, e, 2), 0.0);
    }

    /// The worst case the metric can see, and the one it cannot.
    ///
    /// This is the null the 34.381% figure needs at the top end. Alternating
    /// **columns** saturate the metric: a centre pixel is outnumbered 6 to 3 in
    /// its own neighbourhood, so every interior pixel speckles.
    ///
    /// A **checkerboard** is the higher-frequency pattern and yet is invisible
    /// to the metric, because the centre's own value occupies the four
    /// diagonals plus the centre — 5 of 9 — and therefore *is* the median.
    ///
    /// Both are proved by how the count scales rather than by one number: the
    /// stripe count grows with **area** (`w * h - h`, every pixel but the last
    /// column) and the checkerboard count grows with **perimeter**
    /// (`w + h - 2`, exactly half the border), which is only possible if the
    /// checkerboard's interior contributes nothing at any size.
    ///
    /// Recorded because it is a real limitation of the statistic, not a bug in
    /// this function: 34.381% is blind to the highest-frequency winner map
    /// possible, so it understates instability in that specific mode.
    #[test]
    fn alternating_columns_saturate_the_metric_but_a_checkerboard_hides_from_it() {
        for (w, h) in [(16usize, 16usize), (24, 24), (32, 32)] {
            let g = geom(w, h);
            let px = g.pixels() as f64;

            let stripes: Vec<u16> = (0..g.pixels())
                .map(|i| if (i % w) % 2 == 0 { 0 } else { 10 })
                .collect();
            let want = (w * h - h) as f64 / px;
            assert!(
                (speckle_fraction(&stripes, g, 2) - want).abs() < 1e-12,
                "stripes at {w}x{h}"
            );

            let checker: Vec<u16> = (0..g.pixels())
                .map(|i| if ((i % w) + (i / w)) % 2 == 0 { 0 } else { 10 })
                .collect();
            let want = (w + h - 2) as f64 / px;
            assert!(
                (speckle_fraction(&checker, g, 2) - want).abs() < 1e-12,
                "checkerboard at {w}x{h}"
            );
        }
    }
}
