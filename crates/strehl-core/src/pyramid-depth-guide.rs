//! Depth-guided fusion weights for the pyramid merge (`STREHL_FUSION=depth`).
//!
//! The default merge elects per coefficient from that coefficient's own
//! smoothed band energy in this frame: a local, noisy statistic. Here the
//! focus plane of every place in the picture is measured once, from the whole
//! stack (a through-focus peak per cell, `merge_cmd/depth-guide.rs`), and each
//! frame's weight at a coefficient is the measured through-focus amplitude
//! transfer of that band at the frame's distance from the place's focus:
//!
//! ```text
//! t_k(j) = exp(-j^2 / (2 s_k^2)),  j = frame - D(x),  0 where t < floor
//! ```
//!
//! On the finest `matched` levels, whose transfer is measured, it is
//! accumulated as `sum(t L) / sum(t^2)` -- the matched filter for coefficients
//! that are `t` times the in-focus one: unbiased for the in-focus coefficient
//! when the model holds, with noise variance `sigma^2 / sum(t^2)`. A plain
//! weighted mean `sum(t L) / sum(t)` would shrink detail by `sum(t^2)/sum(t)`.
//! Coarser levels and the base are a normalised weighted mean
//! `sum(t L) / sum(t)`: brightness and coarse structure barely change through
//! focus, and the matched filter would amplify a band that does not fade by up
//! to `sum(t) / sum(t^2)` (about 1.4 for Gaussian weights).
//! The weights depend on the frame index and the depth map only, never on the
//! frame's own noise, so noise cannot elect itself.
//!
//! Ported from the A7CR full-potential prototype
//! (`experiments/a7cr-full-potential-2026-11-14/fuse.py`, arm f2 with a
//! Gaussian transfer in place of the measured coherent one).
use super::LevelSize;

/// Per pyramid level: the focus plane (fractional frame index) at every
/// coefficient, and the transfer width in frames.
#[derive(Debug, Clone)]
pub struct DepthGuide {
    depth: Vec<Vec<f32>>,
    widths: Vec<f32>,
    floor: f32,
    matched: usize,
    /// Levels below this take the guide's weights; coarser levels take the
    /// merge's own election. `usize::MAX` (the default): every level.
    guided: usize,
}

impl DepthGuide {
    /// From depth maps on a cell grid, one per band: cell `(cx, cy)` covers
    /// level-0 pixels `[cx * cell, (cx + 1) * cell)` horizontally (likewise
    /// vertically), and holds the focus plane there. Level `k` reads map
    /// `depth[k]` (levels past the end read the last): a lens with spherical
    /// aberration focuses fine detail at a different plane from coarse
    /// detail, so each band needs its own. Level `k`'s coefficient `(x, y)` sits at
    /// level-0 position `(x * 2^k, y * 2^k)` (the reduce keeps even samples)
    /// and reads the cell grid bilinearly between cell centres.
    ///
    /// `widths[k]` is band `k`'s transfer width in frames (levels past the end
    /// repeat the last); `floor` zeroes weights below it; levels below
    /// `matched` use the matched filter. Panics on an empty or non-finite
    /// input, which is the caller's to refuse.
    #[allow(clippy::too_many_arguments)]
    pub fn from_cells(
        sizes: &[LevelSize],
        cell: usize,
        cells_w: usize,
        cells_h: usize,
        depth: &[Vec<f32>],
        widths: &[f32],
        floor: f32,
        matched: usize,
    ) -> Self {
        assert!(cell > 0 && cells_w > 0 && cells_h > 0 && !depth.is_empty());
        for d in depth {
            assert_eq!(d.len(), cells_w * cells_h);
            assert!(d.iter().all(|d| d.is_finite()), "depth map has holes");
        }
        assert!(!widths.is_empty() && widths.iter().all(|w| *w > 0.0 && w.is_finite()));
        assert!((0.0..1.0).contains(&floor));
        let at = |depth: &[f32], x: f32, y: f32| -> f32 {
            let fx = (x / cell as f32 - 0.5).clamp(0.0, (cells_w - 1) as f32);
            let fy = (y / cell as f32 - 0.5).clamp(0.0, (cells_h - 1) as f32);
            let (x0, y0) = (fx as usize, fy as usize);
            let (x1, y1) = ((x0 + 1).min(cells_w - 1), (y0 + 1).min(cells_h - 1));
            let (ax, ay) = (fx - x0 as f32, fy - y0 as f32);
            let g = |cx: usize, cy: usize| depth[cy * cells_w + cx];
            (1.0 - ay) * ((1.0 - ax) * g(x0, y0) + ax * g(x1, y0))
                + ay * ((1.0 - ax) * g(x0, y1) + ax * g(x1, y1))
        };
        let depth = sizes
            .iter()
            .enumerate()
            .map(|(k, s)| {
                let step = (1usize << k) as f32;
                let map = &depth[k.min(depth.len() - 1)];
                (0..s.height)
                    .flat_map(|y| (0..s.width).map(move |x| (x, y)))
                    .map(|(x, y)| at(map, x as f32 * step, y as f32 * step))
                    .collect()
            })
            .collect();
        let widths = (0..sizes.len())
            .map(|k| widths[k.min(widths.len() - 1)])
            .collect();
        Self {
            depth,
            widths,
            floor,
            matched,
            guided: usize::MAX,
        }
    }

    /// Guide only the levels below `levels`; coarser levels (and the base)
    /// keep the merge's own soft election.
    pub fn with_guided_levels(mut self, levels: usize) -> Self {
        self.guided = levels;
        self
    }

    /// Whether level `k` takes the guide's weights.
    pub fn guides(&self, k: usize) -> bool {
        k < self.guided
    }

    /// Level `k`'s weights for the frame at stack index `frame`.
    pub fn fill(&self, k: usize, frame: f32, w: &mut [f32]) {
        use rayon::prelude::*;
        let d = &self.depth[k];
        assert_eq!(d.len(), w.len(), "guide level {k} does not match the band");
        let inv = 1.0 / (2.0 * self.widths[k] * self.widths[k]);
        let floor = self.floor;
        w.par_iter_mut().zip(d.par_iter()).for_each(|(w, d)| {
            let j = frame - d;
            let t = (-j * j * inv).exp();
            *w = if t >= floor { t } else { 0.0 };
        });
    }

    /// Whether level `k` is accumulated as the matched filter
    /// (`sum(t L) / sum(t^2)`) rather than the weighted mean.
    pub fn matched(&self, k: usize) -> bool {
        k < self.matched
    }

    /// Transfer width of level `k`, in frames.
    pub fn width(&self, k: usize) -> f32 {
        self.widths[k]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn weights_peak_at_the_focus_plane_and_vanish_beyond_the_floor() {
        let sizes = [LevelSize {
            width: 16,
            height: 8,
        }];
        // Two cells of 8 px: focus at frame 10 on the left, 20 on the right.
        let g = DepthGuide::from_cells(&sizes, 8, 2, 1, &[vec![10.0, 20.0]], &[4.0], 0.3, 1);
        let mut w = vec![0.0; 16 * 8];
        g.fill(0, 10.0, &mut w);
        assert!((w[0] - 1.0).abs() < 1e-6, "in focus at the left: {}", w[0]);
        assert_eq!(w[15], 0.0, "ten frames from focus at the right");
        g.fill(0, 14.0, &mut w);
        let t4 = (-16.0f32 / 32.0).exp();
        assert!((w[0] - t4).abs() < 1e-6);
    }

    #[test]
    fn coarser_levels_read_the_same_map_at_their_own_positions() {
        let sizes = [
            LevelSize {
                width: 16,
                height: 2,
            },
            LevelSize {
                width: 8,
                height: 1,
            },
        ];
        let g = DepthGuide::from_cells(
            &sizes,
            8,
            2,
            1,
            &[vec![10.0, 20.0], vec![12.0, 22.0]],
            &[4.0, 6.0],
            0.0,
            1,
        );
        // Level 1 coefficient 7 sits at level-0 x = 14, inside the right cell,
        // and reads level 1's own map.
        let mut w = vec![0.0; 8];
        g.fill(1, 22.0, &mut w);
        assert!(w[7] > 0.99 && w[0] < 0.5, "{w:?}");
        assert_eq!(g.width(1), 6.0);
    }

    /// The guided merge, end to end: identical frames with independent noise
    /// and a constant focus plane. The output must be the scene, with the
    /// noise variance of `sum(t L) / sum(t^2)`: `sigma^2 / sum(t^2)`.
    #[test]
    fn a_guided_merge_returns_the_scene_with_matched_filter_noise() {
        use super::super::{BandMerge, FrameWorkspace, MergeConfig, Workspace, level_sizes};
        use std::sync::Arc;
        let (w, h) = (96usize, 64usize);
        let cfg = MergeConfig {
            bands: 3,
            ensemble: false,
            ..Default::default()
        };
        let sizes = level_sizes(w, h, cfg.bands);
        // Fine detail on a flat ground: the detail fades with defocus by the
        // transfer, the ground does not.
        let detail: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                200.0 * (2.2 * x).sin() * (1.9 * y).cos()
            })
            .collect();
        let scene: Vec<f32> = detail.iter().map(|d| 1000.0 + d).collect();
        let (frames, focus, width) = (21usize, 10.0f32, 3.0f32);
        let guide = Arc::new(DepthGuide::from_cells(
            &sizes,
            8,
            w / 8,
            h / 8,
            &[vec![focus; (w / 8) * (h / 8)]],
            &[width],
            0.0,
            1,
        ));
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut fws = FrameWorkspace::new(&sizes, 1);
        let var = vec![100.0f32; w * h];
        let mut seed = 0x9E37_79B9_7F4A_7C15u64;
        let mut normal = move || {
            let mut u = || {
                seed ^= seed << 13;
                seed ^= seed >> 7;
                seed ^= seed << 17;
                ((seed >> 11) as f64 + 0.5) / (1u64 << 53) as f64
            };
            let (a, b) = (u(), u());
            ((-2.0 * a.ln()).sqrt() * (std::f64::consts::TAU * b).cos()) as f32
        };
        let sigma = 10.0f32;
        let t = |k: usize| {
            let j = k as f32 - focus;
            (-j * j / (2.0 * width * width)).exp()
        };
        for k in 0..frames {
            let f: Vec<f32> = detail
                .iter()
                .map(|d| 1000.0 + t(k) * d + sigma * normal())
                .collect();
            fws.next_frame();
            merge.set_guide(guide.clone(), k as f32);
            merge.add_frame(&[f.as_slice()], &f, &var, &mut fws);
        }
        let mut ws = Workspace::new(&sizes);
        let out = merge.finish(&mut ws)[0].clone();
        let sum_t2: f32 = (0..frames).map(|k| t(k).powi(2)).sum();
        let inner = |i: usize| (8..w - 8).contains(&(i % w)) && (8..h - 8).contains(&(i / w));
        let (mut bias, mut sq, mut n) = (0f64, 0f64, 0f64);
        for i in (0..w * h).filter(|i| inner(*i)) {
            let e = f64::from(out[i] - scene[i]);
            bias += e;
            sq += e * e;
            n += 1.0;
        }
        let rms = (sq / n).sqrt() as f32;
        let want = sigma / sum_t2.sqrt();
        assert!((bias / n).abs() < 0.5, "bias {}", bias / n);
        assert!(
            rms < 1.25 * want && rms > 0.75 * want,
            "noise {rms}, matched filter predicts {want} (one frame {sigma})"
        );
    }
}
