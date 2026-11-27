//! The subject's in-focus range from contrast ([`strehl_core::focus_contrast`]),
//! for `strehl survey` and `strehl subject` (capture calibration spec 5.2
//! and C2, ledger row `cpf-f2-bounds`).
//!
//! The engine's earlier depth (each subject cell's plane of largest energy)
//! stays in the JSON under its own names for comparison; what is offered as
//! bounds comes from here.

use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use strehl_core::CfaPlane;
use strehl_core::focus_contrast::{self, Tiles};
use strehl_core::pixel_shift::cfa_colour;

/// Sensor pixels per contrast tile.
pub const TILE_PX: usize = 2 * focus_contrast::BLOCK * focus_contrast::TILE_BLOCKS;

/// The first green site plane of a decoded exposure's active area, above
/// black (the plane `strehl focus-step` reads): samples, width, height.
pub fn green_plane(f: &strehl_raw::Frame) -> (Vec<f32>, usize, usize) {
    let (ax, ay) = (f.active.x, f.active.y);
    let (w, h) = (f.active.width / 2, f.active.height / 2);
    let (gx, gy) = if cfa_colour(1, 0) == 1 {
        (1, 0)
    } else {
        (0, 1)
    };
    let black = f.levels.black;
    let mut plane = vec![0.0f32; w * h];
    plane
        .par_chunks_mut(w.max(1))
        .enumerate()
        .for_each(|(j, row)| {
            let src = &f.data[(ay + 2 * j + gy) * f.stride + ax + gx..];
            for (i, v) in row.iter_mut().enumerate() {
                *v = f32::from(src[2 * i]) - black;
            }
        });
    (plane, w, h)
}

/// Contrast tiles of one exposure, with the injected noise model.
pub fn frame_tiles(f: &strehl_raw::Frame) -> Tiles {
    let noise = strehl_core::profile::noise_model_for(&f.camera, f.iso, f.levels);
    let (plane, w, h) = green_plane(f);
    focus_contrast::tiles(&plane, w, h, &|s| noise.variance(CfaPlane::G1, s))
}

/// Per contrast tile (64 sensor px from the active area's corner, the grid
/// of [`frame_tiles`]): the mean green level and the largest sample of any
/// colour, both above black as shares of black to white.
pub fn tile_levels(f: &strehl_raw::Frame) -> (Vec<f32>, Vec<f32>) {
    let (ax, ay) = (f.active.x, f.active.y);
    let (cols, rows) = (f.active.width / TILE_PX, f.active.height / TILE_PX);
    let black = f.levels.black;
    let range = (f.levels.white - black).max(1.0);
    let per: Vec<(f32, f32)> = (0..cols * rows)
        .into_par_iter()
        .map(|t| {
            let (tx, ty) = (t % cols, t / cols);
            let (mut sum, mut n, mut top) = (0.0f64, 0u32, 0u16);
            for y in ty * TILE_PX..(ty + 1) * TILE_PX {
                let row = &f.data[(ay + y) * f.stride + ax + tx * TILE_PX..][..TILE_PX];
                for (x, &v) in row.iter().enumerate() {
                    top = top.max(v);
                    if cfa_colour((tx * TILE_PX + x) as isize, y as isize) == 1 {
                        sum += f64::from(v);
                        n += 1;
                    }
                }
            }
            let mean = (sum / f64::from(n.max(1))) as f32;
            (
                ((mean - black) / range).max(0.0),
                ((f32::from(top) - black) / range).max(0.0),
            )
        })
        .collect();
    per.into_iter().unzip()
}

/// The tiles at least half inside `rings` (normalised to the active area of
/// `active` sensor pixels); every tile without rings.
pub fn subject_tiles(rings: Option<&[Vec<[f32; 2]>]>, t: &Tiles, active: [usize; 2]) -> Vec<bool> {
    let Some(rings) = rings.filter(|r| !r.is_empty()) else {
        return vec![true; t.cols * t.rows];
    };
    // Eight sub-cells a side per tile, counted.
    const SUB: usize = 8;
    let (cw, ch) = (t.cols * SUB, t.rows * SUB);
    let cell = [
        (TILE_PX / SUB) as f64 / active[0].max(1) as f64,
        (TILE_PX / SUB) as f64 / active[1].max(1) as f64,
    ];
    let fine = strehl_core::subject::rasterize(rings, cw, ch, cell);
    (0..t.cols * t.rows)
        .map(|i| {
            let (tx, ty) = (i % t.cols, i / t.cols);
            let inside = (0..SUB)
                .flat_map(|j| (0..SUB).map(move |k| (ty * SUB + j) * cw + tx * SUB + k))
                .filter(|&c| fine[c])
                .count();
            2 * inside >= SUB * SUB
        })
        .collect()
}

/// The in-focus range, as `depth` reports it.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct InFocus {
    /// The focus of the first and last frame holding the subject in focus
    /// (spec 5.2); `null` when no frame does.
    pub in_focus_first: Option<f64>,
    pub in_focus_last: Option<f64>,
    /// The first (last) frame measured holds the subject: it may go on past
    /// what was taken, and that side has no suggestion.
    pub reaches_first: bool,
    pub reaches_last: bool,
    /// `in_focus_first` less the larger of half the sharp width and half the
    /// frames' spacing there; `in_focus_last` plus the same. `null` where the
    /// subject reaches that end or nothing is in focus.
    pub suggested_start: Option<f64>,
    pub suggested_end: Option<f64>,
    /// Subject tiles in focus at each frame: `[focus, tiles]`, in focus order.
    pub per_position: Vec<[f64; 2]>,
    /// The subject's reference contrast, the tiles it is read over, and the
    /// tiles a frame needs to hold the subject.
    pub contrast_reference: f32,
    pub subject_tiles: usize,
    pub tiles_needed: usize,
    /// The sharp width the suggestion used (`null`: none known).
    pub width: Option<f64>,
}

/// Per-tile figures for the desktop's lenses (spec C2 `maps`).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Maps {
    pub cols: usize,
    pub rows: usize,
    /// Sensor pixels per tile; the grid starts at the active area's corner.
    pub tile_px: usize,
    /// Per tile, row-major: the focus of its largest contrast among the
    /// frames where it is in focus; `null` where it is in focus nowhere.
    pub focus: Vec<Option<f64>>,
    /// Per tile: whether it is the subject's.
    pub subject: Vec<bool>,
    /// Per tile (`strehl survey` only): the body's mean green level in the
    /// brightest long frame, as a share of full scale at the long shutter
    /// (the Light lens); and the brightest sample any short frame holds,
    /// scaled to the long shutter (the Glints lens: over 1 pins there).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub level: Option<Vec<f32>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub glint: Option<Vec<f32>>,
    /// The long shutter both are at, effective seconds.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub long_s: Option<f64>,
}

/// The range and maps from frames at `positions` (any order) with their
/// tiles, over the subject's tiles; `width` the sharp width, if known.
pub fn in_focus(
    positions: &[f64],
    tiles: &[Tiles],
    subject: &[bool],
    width: Option<f64>,
) -> Option<(InFocus, Maps)> {
    assert_eq!(positions.len(), tiles.len());
    let first = tiles.first()?;
    if tiles
        .iter()
        .any(|t| (t.cols, t.rows) != (first.cols, first.rows))
    {
        return None;
    }
    let mut order: Vec<usize> = (0..positions.len()).collect();
    order.sort_by(|&a, &b| positions[a].total_cmp(&positions[b]));
    let pos: Vec<f64> = order.iter().map(|&i| positions[i]).collect();
    let frames: Vec<&[f32]> = order
        .iter()
        .map(|&i| tiles[i].contrast.as_slice())
        .collect();
    let r = focus_contrast::range(&frames, subject);
    let gap = |i: usize| -> f64 {
        let before = i.checked_sub(1).map_or(0.0, |j| pos[i] - pos[j]);
        let after = pos.get(i + 1).map_or(0.0, |p| p - pos[i]);
        before.max(after)
    };
    let w = width.unwrap_or(0.0);
    let focus = focus_contrast::tile_focus(&frames, &pos, r.reference);
    let n_subject = subject.iter().filter(|&&s| s).count();
    let out = InFocus {
        in_focus_first: r.first.map(|i| pos[i]),
        in_focus_last: r.last.map(|i| pos[i]),
        reaches_first: r.reaches_first,
        reaches_last: r.reaches_last,
        suggested_start: r
            .first
            .filter(|_| !r.reaches_first)
            .map(|i| focus_contrast::widen(pos[i], w, gap(i), -1.0).floor()),
        suggested_end: r
            .last
            .filter(|_| !r.reaches_last)
            .map(|i| focus_contrast::widen(pos[i], w, gap(i), 1.0).ceil()),
        per_position: pos
            .iter()
            .zip(&r.in_focus)
            .map(|(p, n)| [*p, *n as f64])
            .collect(),
        contrast_reference: r.reference,
        subject_tiles: if subject.is_empty() {
            frames[0].len()
        } else {
            n_subject
        },
        tiles_needed: r.needed,
        width,
    };
    let maps = Maps {
        cols: first.cols,
        rows: first.rows,
        tile_px: TILE_PX,
        focus: focus
            .into_iter()
            .enumerate()
            .map(|(t, f)| f.filter(|_| subject.is_empty() || subject[t]))
            .collect(),
        subject: if subject.is_empty() {
            vec![true; first.cols * first.rows]
        } else {
            subject.to_vec()
        },
        level: None,
        glint: None,
        long_s: None,
    };
    Some((out, maps))
}

/// One line for a report: "in focus from A to B" with what is not known.
pub fn describe(r: &InFocus) -> String {
    match (r.in_focus_first, r.in_focus_last) {
        (Some(a), Some(b)) => {
            let mut s = format!("in focus from {a:.0} to {b:.0}");
            if r.reaches_first {
                s += &format!("; still in focus at the first frame, {a:.0}: the subject may go on");
            }
            if r.reaches_last {
                s += &format!("; still in focus at the last frame, {b:.0}: the subject may go on");
            }
            s
        }
        _ => "nothing in focus".into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tiles_of(v: Vec<f32>) -> Tiles {
        Tiles {
            cols: v.len(),
            rows: 1,
            contrast: v,
        }
    }

    #[test]
    fn a_range_inside_the_frames_has_both_suggestions() {
        // Five frames 100 apart; ten tiles in focus at 200 and 300.
        let positions = [400.0, 0.0, 200.0, 100.0, 300.0];
        let tiles: Vec<Tiles> = positions
            .iter()
            .map(|&p| tiles_of(vec![if p == 200.0 || p == 300.0 { 1.0 } else { 0.0 }; 10]))
            .collect();
        let (r, maps) = in_focus(&positions, &tiles, &[], Some(40.0)).unwrap();
        assert_eq!(
            (r.in_focus_first, r.in_focus_last),
            (Some(200.0), Some(300.0))
        );
        assert!(!r.reaches_first && !r.reaches_last);
        // Half the spacing (50) is more than half the width (20).
        assert_eq!(
            (r.suggested_start, r.suggested_end),
            (Some(150.0), Some(350.0))
        );
        assert_eq!(r.per_position[2], [200.0, 10.0]);
        assert_eq!(maps.focus[0], Some(200.0));
    }

    #[test]
    fn a_subject_running_past_the_end_has_no_suggestion_there() {
        let positions = [0.0, 100.0, 200.0];
        let tiles: Vec<Tiles> = positions
            .iter()
            .map(|&p| tiles_of(vec![if p >= 100.0 { 1.0 } else { 0.0 }; 10]))
            .collect();
        let (r, _) = in_focus(&positions, &tiles, &[], None).unwrap();
        assert!(r.reaches_last && !r.reaches_first);
        assert_eq!(r.suggested_end, None);
        assert_eq!(r.suggested_start, Some(50.0));
        assert!(describe(&r).contains("still in focus at the last frame, 200"));
    }
}
