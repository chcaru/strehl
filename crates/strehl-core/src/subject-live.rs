//! The loose first outline from live-view frames alone (plan S2, frames from
//! the bounds survey; prototype `live-mask.py`).
//!
//! Live view is a processed JPEG, so there is no sensor noise model to
//! inject: each frame's energy is normalised by its own quiet level (the
//! median energy of its lowest third), which is what the prototype measured.
//! Growth uses focus evidence only: the defocused glow around a subject
//! differs from the backdrop and would inflate the outline.

use rayon::prelude::*;

use super::evidence::{self, Evidence, FrameCells, Layout, PlaneRef, Registration, gaussian};
use super::outline::Source;
use super::select::{self, Params, Selection, percentile};

/// Live-view pixels per evidence cell.
pub const LIVE_CELL: usize = 4;

/// One decoded live-view frame, RGB8 interleaved, row-major.
#[derive(Clone, Copy, Debug)]
pub struct LiveFrame<'a> {
    pub rgb: &'a [u8],
    pub width: usize,
    pub height: usize,
}

fn linear(c: u8) -> f32 {
    let v = f32::from(c) / 255.0;
    if v <= 0.04045 {
        v / 12.92
    } else {
        ((v + 0.055) / 1.055).powf(2.4)
    }
}

/// Evidence cells of one frame: linear luma, a light blur (sigma 0.7 px, so
/// 8 px JPEG block edges stay out), the 4-neighbour Laplacian squared, mean
/// per 4 x 4 px cell, divided by the frame's quiet level, 3 x 3 cell mean.
pub fn live_frame_cells(f: &LiveFrame<'_>) -> FrameCells {
    let (w, h) = (f.width, f.height);
    assert_eq!(f.rgb.len(), 3 * w * h, "RGB8 frame size");
    let lut: Vec<f32> = (0..=255u8).map(linear).collect();
    let y: Vec<f32> = f
        .rgb
        .par_chunks_exact(3)
        .map(|p| {
            0.2126 * lut[p[0] as usize] + 0.7152 * lut[p[1] as usize] + 0.0722 * lut[p[2] as usize]
        })
        .collect();
    let s = gaussian(&y, w, h, 0.7);
    let (cols, rows) = (w / LIVE_CELL, h / LIVE_CELL);
    let mut energy = vec![0.0f32; cols * rows];
    let mut level = vec![0.0f32; cols * rows];
    energy
        .par_chunks_mut(cols)
        .zip(level.par_chunks_mut(cols))
        .enumerate()
        .for_each(|(cy, (erow, lrow))| {
            for yy in cy * LIVE_CELL..(cy + 1) * LIVE_CELL {
                let (ym, yp) = (yy.saturating_sub(1), (yy + 1).min(h - 1));
                for (cx, (e, l)) in erow.iter_mut().zip(lrow.iter_mut()).enumerate() {
                    for xx in cx * LIVE_CELL..(cx + 1) * LIVE_CELL {
                        let (xm, xp) = (xx.saturating_sub(1), (xx + 1).min(w - 1));
                        let c = s[yy * w + xx];
                        let lap = s[yy * w + xm] + s[yy * w + xp] + s[ym * w + xx] + s[yp * w + xx]
                            - 4.0 * c;
                        *e += lap * lap;
                        *l += y[yy * w + xx];
                    }
                }
            }
            let n = (LIVE_CELL * LIVE_CELL) as f32;
            erow.iter_mut().for_each(|e| *e /= n);
            lrow.iter_mut().for_each(|l| *l /= n);
        });
    let p33 = percentile(energy.clone(), 33.0);
    let low: Vec<f32> = energy.iter().copied().filter(|&e| e <= p33).collect();
    let quiet = percentile(low, 50.0).max(1e-12);
    energy.iter_mut().for_each(|e| *e /= quiet);
    FrameCells {
        cols,
        rows,
        energy: evidence::box3(&energy, cols, rows),
        level,
    }
}

/// Evidence from live-view frames in focus order. `positions` are their
/// focus positions (frame indices when `None`); `active_px` is the sensor's
/// active area, which live view shows whole, so normalised live coordinates
/// are sensor coordinates.
pub fn live_view_evidence(
    frames: &[LiveFrame<'_>],
    positions: Option<&[f64]>,
    active_px: [u32; 2],
) -> Evidence {
    assert!(!frames.is_empty());
    let (w, h) = (frames[0].width, frames[0].height);
    assert!(frames.iter().all(|f| f.width == w && f.height == h));
    let cells: Vec<FrameCells> = frames.par_iter().map(live_frame_cells).collect();
    let planes = (0..frames.len())
        .map(|k| PlaneRef {
            ordinal: k as u64,
            position: positions.map(|p| p[k]),
        })
        .collect();
    let layout = Layout {
        source: Source::LiveView,
        cell_px: LIVE_CELL as f32 * active_px[0] as f32 / w as f32,
        cell_norm: [LIVE_CELL as f64 / w as f64, LIVE_CELL as f64 / h as f64],
        active_px,
    };
    evidence::assemble(cells, planes, layout, Registration::Fit)
}

/// The loose outline from live-view frames: [`live_view_evidence`] then
/// selection with `params` (see [`Params::live`]).
pub fn live_view_subject(
    frames: &[LiveFrame<'_>],
    positions: Option<&[f64]>,
    active_px: [u32; 2],
    params: &Params,
) -> (Evidence, Selection) {
    let e = live_view_evidence(frames, positions, active_px);
    let q = select::quiet(&e);
    let s = select::select(&e, &q, params);
    (e, s)
}
