//! Contrast: fine detail against its own brightness, the focus measure of a
//! capture's calibration (capture calibration spec 5.1 and 5.2, ledger row
//! `cpf-f2-bounds`).
//!
//! The engine's earlier depth rule ranked a cell by its fine energy above
//! noise. On a subject with bright out-of-focus highlights that ranks blur
//! above detail: on the dragonfly of 2026-11-26 the in-focus wing sat at
//! about 148 DN and the blur that scored as sharp at about 2,056 DN, so the
//! rule called the subject sharp from the first plane to the last (MEASURED,
//! `experiments/capture-planning-flow-2026-11-26/grounding/results.md` R1).
//! Dividing the energy by the square of the local level removes that: on
//! eight stacks this measure gives the in-focus range within one sharp
//! depth and says when a subject runs past its capture (R2.3).
//!
//! On one green site plane above black:
//!
//! 1. per block of [`BLOCK`] x [`BLOCK`] samples (16 sensor pixels), `l` =
//!    the mean squared 4-neighbour Laplacian;
//! 2. its noise `n` = [`LAPLACIAN_NOISE`] x the injected model's variance at
//!    the block's mean (four neighbours and four times the centre);
//! 3. detail `e = l - n` where `l >= DETAIL_OVER_NOISE n`, else 0;
//! 4. the level `L` = the largest block mean within [`REACH`] blocks, and
//!    the floor `L0` = [`DARK_FLOOR_SIGMAS`] read-noise deviations;
//! 5. block contrast `c = e / (L^2 + L0^2)`;
//! 6. a tile of [`TILE_BLOCKS`] x [`TILE_BLOCKS`] blocks (64 sensor pixels)
//!    has the [`TILE_PERCENTILE`] of its blocks.
//!
//! Each part removed a measured failure: brightness as divisor (bright blur
//! outranks dim detail by energy), the neighbourhood's level rather than the
//! block's own (a blurred bright edge spills gradient into the dark blocks
//! beside it: 56 false tiles on the weevil), the injected noise and `L0`
//! (with a wrong dark-level noise black backdrop reads as detail), the
//! percentile of blocks (one hot pixel or glint rim does not make a tile).
//!
//! [`range`] turns tile contrasts of frames at known positions into the
//! subject's in-focus range. The reference implementation is
//! `block_contrast` and `contrast_range` in the grounding's
//! `scripts/general.py`.

// `!(x >= limit)` is deliberate: it also rejects NaN.
#![allow(clippy::neg_cmp_op_on_partial_ord)]

use rayon::prelude::*;

/// Block side, green-site samples (16 sensor pixels).
pub const BLOCK: usize = 8;
/// Tile side, blocks (64 sensor pixels).
pub const TILE_BLOCKS: usize = 4;
/// The level is the largest block mean within this many blocks (a 7 x 7
/// window).
pub const REACH: usize = 3;
/// Variance of the 4-neighbour Laplacian of white noise, in sample
/// variances: four neighbours and four times the centre (4 + 16).
pub const LAPLACIAN_NOISE: f32 = 20.0;
/// Energy under this multiple of its noise is no detail.
pub const DETAIL_OVER_NOISE: f32 = 3.0;
/// The level's floor, read-noise deviations.
pub const DARK_FLOOR_SIGMAS: f32 = 8.0;
/// A tile's contrast: this quantile of its blocks.
pub const TILE_PERCENTILE: f32 = 0.75;
/// [`range`]: the subject's reference is this quantile of its tiles' best.
pub const REFERENCE_PERCENTILE: f32 = 0.90;
/// A tile is in focus in a frame at this share of the reference.
pub const IN_FOCUS_SHARE: f32 = 0.2;
/// A frame holds the subject with this many tiles in focus, and this share
/// of the subject's tiles.
pub const MIN_TILES: usize = 3;
pub const MIN_SHARE: f64 = 0.0005;

/// One exposure's contrast per tile, row-major.
#[derive(Clone, Debug, PartialEq)]
pub struct Tiles {
    pub cols: usize,
    pub rows: usize,
    pub contrast: Vec<f32>,
}

/// Quantile `q` (0..1) of `v` with linear interpolation, as numpy's default.
fn quantile(v: &mut [f32], q: f32) -> f32 {
    if v.is_empty() {
        return f32::NAN;
    }
    v.sort_by(f32::total_cmp);
    let pos = q * (v.len() - 1) as f32;
    let k = pos.floor() as usize;
    let frac = pos - k as f32;
    match v.get(k + 1) {
        Some(&hi) if frac > 0.0 => v[k] + (hi - v[k]) * frac,
        _ => v[k],
    }
}

/// Tile contrast of one green site plane: `plane` holds `w x h` samples
/// above black, row-major; `variance(level)` is the injected noise model's
/// variance of one sample at `level` above black (its value at 0 is the
/// read noise). Blocks and tiles that do not fit whole are left out.
pub fn tiles(plane: &[f32], w: usize, h: usize, variance: &(dyn Fn(f32) -> f32 + Sync)) -> Tiles {
    assert!(
        plane.len() >= w * h,
        "plane of {} samples, not {w} x {h}",
        plane.len()
    );
    let (bw, bh) = (w / BLOCK, h / BLOCK);
    let at = |x: usize, y: usize| plane[y * w + x];
    // Per block: the mean squared Laplacian and the mean level.
    let blocks: Vec<(f32, f32)> = (0..bh)
        .into_par_iter()
        .flat_map_iter(|by| {
            (0..bw).map(move |bx| {
                let (mut lap, mut sum) = (0.0f64, 0.0f64);
                for y in by * BLOCK..(by + 1) * BLOCK {
                    for x in bx * BLOCK..(bx + 1) * BLOCK {
                        let c = at(x, y);
                        sum += f64::from(c);
                        // The plane's own border has no Laplacian.
                        if x > 0 && y > 0 && x + 1 < w && y + 1 < h {
                            let l =
                                at(x - 1, y) + at(x + 1, y) + at(x, y - 1) + at(x, y + 1) - 4.0 * c;
                            lap += f64::from(l * l);
                        }
                    }
                }
                let n = (BLOCK * BLOCK) as f64;
                ((lap / n) as f32, ((sum / n) as f32).max(0.0))
            })
        })
        .collect();
    let floor = DARK_FLOOR_SIGMAS * variance(0.0).max(0.0).sqrt();
    let floor2 = floor * floor;
    let contrast: Vec<f32> = (0..bh)
        .into_par_iter()
        .flat_map_iter(|by| {
            let blocks = &blocks;
            (0..bw).map(move |bx| {
                let (l, m) = blocks[by * bw + bx];
                let n = LAPLACIAN_NOISE * variance(m);
                if !(l >= DETAIL_OVER_NOISE * n) {
                    return 0.0;
                }
                let mut level = 0.0f32;
                for y in by.saturating_sub(REACH)..(by + REACH + 1).min(bh) {
                    for x in bx.saturating_sub(REACH)..(bx + REACH + 1).min(bw) {
                        level = level.max(blocks[y * bw + x].1);
                    }
                }
                (l - n).max(0.0) / (level * level + floor2)
            })
        })
        .collect();
    let (cols, rows) = (bw / TILE_BLOCKS, bh / TILE_BLOCKS);
    let tiles: Vec<f32> = (0..cols * rows)
        .into_par_iter()
        .map(|t| {
            let (tx, ty) = (t % cols, t / cols);
            let mut v = [0.0f32; TILE_BLOCKS * TILE_BLOCKS];
            for j in 0..TILE_BLOCKS {
                for i in 0..TILE_BLOCKS {
                    v[j * TILE_BLOCKS + i] =
                        contrast[(ty * TILE_BLOCKS + j) * bw + tx * TILE_BLOCKS + i];
                }
            }
            quantile(&mut v, TILE_PERCENTILE)
        })
        .collect();
    Tiles {
        cols,
        rows,
        contrast: tiles,
    }
}

/// What a set of frames says about the subject's depth.
#[derive(Clone, Debug, PartialEq)]
pub struct Range {
    /// The subject's reference contrast: [`REFERENCE_PERCENTILE`] over its
    /// tiles of each tile's best.
    pub reference: f32,
    /// Subject tiles in focus, per frame.
    pub in_focus: Vec<usize>,
    /// Tiles a frame needs to hold the subject.
    pub needed: usize,
    /// The first and last frame that hold the subject (indices into the
    /// frames given); `None` when none does.
    pub first: Option<usize>,
    pub last: Option<usize>,
    /// The first (or last) frame given holds the subject: it may go on past
    /// what was taken.
    pub reaches_first: bool,
    pub reaches_last: bool,
}

/// The in-focus range over `frames` (tile contrasts, in focus order), on the
/// tiles where `subject` is true (all tiles when it is empty).
pub fn range(frames: &[&[f32]], subject: &[bool]) -> Range {
    let n = frames.first().map_or(0, |f| f.len());
    assert!(
        frames.iter().all(|f| f.len() == n),
        "frames of different tile grids"
    );
    let chosen: Vec<usize> = if subject.is_empty() {
        (0..n).collect()
    } else {
        assert_eq!(subject.len(), n, "a subject mask of another grid");
        (0..n).filter(|&t| subject[t]).collect()
    };
    let mut best: Vec<f32> = chosen
        .iter()
        .map(|&t| frames.iter().map(|f| f[t]).fold(0.0f32, f32::max))
        .collect();
    let reference = quantile(&mut best, REFERENCE_PERCENTILE);
    let needed = MIN_TILES.max((MIN_SHARE * chosen.len() as f64).ceil() as usize);
    let cut = IN_FOCUS_SHARE * reference;
    let in_focus: Vec<usize> = frames
        .iter()
        .map(|f| {
            if !(reference > 0.0) {
                return 0;
            }
            chosen.iter().filter(|&&t| f[t] >= cut).count()
        })
        .collect();
    let holds = |i: usize| in_focus[i] >= needed;
    let first = (0..frames.len()).find(|&i| holds(i));
    let last = (0..frames.len()).rev().find(|&i| holds(i));
    Range {
        reference,
        needed,
        reaches_first: !frames.is_empty() && holds(0),
        reaches_last: !frames.is_empty() && holds(frames.len() - 1),
        in_focus,
        first,
        last,
    }
}

/// Per tile, the position of its largest contrast among the frames where it
/// is in focus (at least [`IN_FOCUS_SHARE`] of `reference`); `None` where it
/// is in focus nowhere.
pub fn tile_focus(frames: &[&[f32]], positions: &[f64], reference: f32) -> Vec<Option<f64>> {
    assert_eq!(frames.len(), positions.len());
    let n = frames.first().map_or(0, |f| f.len());
    let cut = IN_FOCUS_SHARE * reference;
    (0..n)
        .map(|t| {
            // The first of equal maxima.
            let (i, v) = frames.iter().enumerate().map(|(i, f)| (i, f[t])).fold(
                None,
                |best: Option<(usize, f32)>, (i, v)| match best {
                    Some((_, b)) if !(v > b) => best,
                    _ => Some((i, v)),
                },
            )?;
            (reference > 0.0 && v >= cut).then(|| positions[i])
        })
        .collect()
}

/// The suggested start or end for a range end (spec 5.2 point 6): `end`
/// widened by the larger of half the sharp depth `width` and half the
/// frames' spacing near that end, away from the range (`toward` is -1 for a
/// start, +1 for an end in increasing focus).
pub fn widen(end: f64, width: f64, spacing: f64, toward: f64) -> f64 {
    end + toward * (0.5 * width.max(0.0)).max(0.5 * spacing.max(0.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The model of a sensor: gain 0.4 DN/e-, read noise 3 DN.
    fn variance(level: f32) -> f32 {
        0.4 * level.max(0.0) + 9.0
    }

    /// A deterministic noise field of unit variance (a hash, not a RNG).
    fn unit_noise(x: usize, y: usize, seed: u64) -> f32 {
        let mut z = (x as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15)
            ^ (y as u64).wrapping_mul(0xc2b2_ae3d_27d4_eb4f)
            ^ seed.wrapping_mul(0x1656_67b1_9e37_79f9);
        let mut sum = 0.0f32;
        for _ in 0..4 {
            z ^= z >> 33;
            z = z.wrapping_mul(0xff51_afd7_ed55_8ccd);
            z ^= z >> 29;
            sum += (z >> 40) as f32 / (1u64 << 24) as f32 - 0.5;
        }
        // Four uniforms of variance 1/12: variance 1/3.
        sum * 3f32.sqrt()
    }

    /// A plane with `level(x, y)` plus noise of the model.
    fn plane(w: usize, h: usize, seed: u64, level: impl Fn(usize, usize) -> f32) -> Vec<f32> {
        (0..w * h)
            .map(|i| {
                let (x, y) = (i % w, i / w);
                let l = level(x, y);
                l + variance(l).sqrt() * unit_noise(x, y, seed)
            })
            .collect()
    }

    fn mean_over(t: &Tiles, keep: impl Fn(usize, usize) -> bool) -> f32 {
        let v: Vec<f32> = (0..t.cols * t.rows)
            .filter(|&i| keep(i % t.cols, i / t.cols))
            .map(|i| t.contrast[i])
            .collect();
        v.iter().sum::<f32>() / v.len() as f32
    }

    const FULL: f32 = 15_000.0;

    #[test]
    fn dim_texture_outranks_a_bright_blurred_disc() {
        // Left half: fine texture at 1 % of full scale. Right half: a disc
        // at 30 %, blurred (a smooth ramp at its edge) on black.
        let (w, h) = (512, 256);
        let p = plane(w, h, 1, |x, y| {
            if x < w / 2 {
                let base = 0.01 * FULL;
                base * (1.0 + 0.5 * if (x + y) % 2 == 0 { 1.0 } else { -1.0 })
            } else {
                let (dx, dy) = (x as f32 - 384.0, y as f32 - 128.0);
                let r = (dx * dx + dy * dy).sqrt();
                0.3 * FULL * (1.0 - ((r - 60.0) / 40.0).clamp(0.0, 1.0))
            }
        });
        let t = tiles(&p, w, h, &variance);
        let texture = mean_over(&t, |x, _| x < t.cols / 2);
        let disc = mean_over(&t, |x, _| x >= t.cols / 2);
        assert!(texture > 0.0);
        assert!(
            disc < 0.2 * texture,
            "disc {disc} against texture {texture}"
        );
    }

    #[test]
    fn a_blurred_bright_edge_on_black_makes_no_tile() {
        let (w, h) = (512, 256);
        let p = plane(w, h, 2, |x, _| {
            0.5 * FULL * ((x as f32 - 256.0) / 24.0).clamp(0.0, 1.0)
        });
        let t = tiles(&p, w, h, &variance);
        // Against a reference of real detail (1 % texture), nothing passes.
        let q = plane(w, h, 3, |x, y| {
            0.01 * FULL * (1.0 + 0.5 * if (x + y) % 2 == 0 { 1.0 } else { -1.0 })
        });
        let reference = tiles(&q, w, h, &variance);
        let mut best = reference.contrast.clone();
        let r = quantile(&mut best, REFERENCE_PERCENTILE);
        let passing = t
            .contrast
            .iter()
            .filter(|&&c| c >= IN_FOCUS_SHARE * r)
            .count();
        assert_eq!(passing, 0, "{:?}", t.contrast);
    }

    #[test]
    fn a_flat_frame_has_no_contrast() {
        let (w, h) = (256, 256);
        for level in [0.0, 0.02 * FULL, 0.6 * FULL] {
            let p = plane(w, h, 4, |_, _| level);
            let t = tiles(&p, w, h, &variance);
            let high = t.contrast.iter().filter(|&&c| c > 0.0).count();
            assert!(
                high <= 1,
                "level {level}: {high} of {} tiles",
                t.contrast.len()
            );
        }
    }

    #[test]
    fn contrast_does_not_change_with_gain() {
        // The same scene 1.25 times brighter, its noise by the model: the
        // contrast is the same within the noise.
        let (w, h) = (256, 256);
        let scene = |g: f32| {
            move |x: usize, y: usize| {
                g * 0.05 * FULL * (1.0 + 0.4 * ((x as f32 * 0.9).sin() * (y as f32 * 1.1).cos()))
            }
        };
        let a = tiles(&plane(w, h, 5, scene(1.0)), w, h, &variance);
        let b = tiles(&plane(w, h, 6, scene(1.25)), w, h, &variance);
        let (ma, mb) = (mean_over(&a, |_, _| true), mean_over(&b, |_, _| true));
        assert!(
            ma > 0.0 && (mb / ma - 1.0).abs() < 0.05,
            "{ma} against {mb}"
        );
    }

    #[test]
    fn the_range_is_where_frames_hold_the_subject() {
        // Ten frames; tiles 0..50 in focus at frames 3..6, the rest never.
        let frames: Vec<Vec<f32>> = (0..10)
            .map(|i| {
                (0..100)
                    .map(|t| {
                        if t < 50 && (3..=6).contains(&i) {
                            1.0
                        } else {
                            0.01
                        }
                    })
                    .collect()
            })
            .collect();
        let refs: Vec<&[f32]> = frames.iter().map(Vec::as_slice).collect();
        let subject: Vec<bool> = (0..100).map(|t| t < 80).collect();
        let r = range(&refs, &subject);
        assert_eq!((r.first, r.last), (Some(3), Some(6)));
        assert!(!r.reaches_first && !r.reaches_last);
        assert_eq!(r.in_focus[4], 50);
        // Run past the end: the last frame holds it.
        let r = range(&refs[..5], &subject);
        assert_eq!((r.first, r.last), (Some(3), Some(4)));
        assert!(r.reaches_last);
        let positions: Vec<f64> = (0..10).map(|i| 100.0 * i as f64).collect();
        let focus = tile_focus(&refs, &positions, r.reference);
        assert_eq!(focus[0], Some(300.0));
        assert_eq!(focus[60], None);
    }

    #[test]
    fn bounds_widen_by_half_a_depth_or_half_a_gap() {
        assert_eq!(widen(1000.0, 40.0, 10.0, -1.0), 980.0);
        assert_eq!(widen(1000.0, 40.0, 100.0, 1.0), 1050.0);
    }
}
