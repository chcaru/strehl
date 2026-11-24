//! Raster to rings: every boundary between a set and an unset cell becomes a
//! directed edge along the cell corners (set cell on the right, image
//! coordinates, y down), the edges are linked into closed loops, and each
//! loop is simplified (Douglas-Peucker) to at most [`MAX_RING_POINTS`].
//!
//! Any decomposition of the boundary edges into loops fills back to the
//! raster exactly under the even-odd rule, so outer rings and holes need no
//! bookkeeping. At a corner where two set cells touch only diagonally the
//! walk turns right, keeping them apart, which matches 4-connected parts.

use super::morph::Grid;
use super::outline::{MAX_RING_POINTS, Ring};

const STEP: [(i64, i64); 4] = [(1, 0), (0, 1), (-1, 0), (0, -1)];

/// Closed loops of corner coordinates (in cells), collinear points removed.
pub(crate) fn loops(m: &[bool], g: Grid) -> Vec<Vec<[i64; 2]>> {
    let (w, h) = (g.cols, g.rows);
    let vw = w + 1;
    // Outgoing edge directions per corner, as a bit set over STEP.
    let mut out = vec![0u8; vw * (h + 1)];
    let set = |x: i64, y: i64| -> bool {
        x >= 0 && y >= 0 && (x as usize) < w && (y as usize) < h && m[y as usize * w + x as usize]
    };
    let v = |x: usize, y: usize| y * vw + x;
    for y in 0..h {
        for x in 0..w {
            if !m[y * w + x] {
                continue;
            }
            let (xi, yi) = (x as i64, y as i64);
            if !set(xi, yi - 1) {
                out[v(x, y)] |= 1 << 0; // top edge, left to right
            }
            if !set(xi + 1, yi) {
                out[v(x + 1, y)] |= 1 << 1; // right edge, downwards
            }
            if !set(xi, yi + 1) {
                out[v(x + 1, y + 1)] |= 1 << 2; // bottom edge, right to left
            }
            if !set(xi - 1, yi) {
                out[v(x, y + 1)] |= 1 << 3; // left edge, upwards
            }
        }
    }
    let mut result = Vec::new();
    for start in 0..out.len() {
        while out[start] != 0 {
            let d0 = out[start].trailing_zeros() as usize;
            out[start] &= !(1 << d0);
            let (sx, sy) = ((start % vw) as i64, (start / vw) as i64);
            let mut pts = vec![[sx, sy]];
            let (mut x, mut y, mut d) = (sx + STEP[d0].0, sy + STEP[d0].1, d0);
            while (x, y) != (sx, sy) {
                let at = y as usize * vw + x as usize;
                // Prefer a right turn, then straight on, then left.
                let next = [(d + 1) % 4, d, (d + 3) % 4]
                    .into_iter()
                    .find(|&n| out[at] & (1 << n) != 0)
                    .expect("boundary edges balance at every corner");
                out[at] &= !(1 << next);
                if next != d {
                    pts.push([x, y]);
                }
                d = next;
                x += STEP[d].0;
                y += STEP[d].1;
            }
            // The start is a corner unless the walk leaves it straight on.
            if d == d0 && pts.len() > 1 {
                pts.remove(0);
            }
            result.push(pts);
        }
    }
    result
}

/// Douglas-Peucker on an open chain, keeping both ends.
fn simplify_chain(p: &[[f64; 2]], eps: f64, keep: &mut [bool]) {
    let mut stack = vec![(0usize, p.len() - 1)];
    while let Some((a, b)) = stack.pop() {
        if b <= a + 1 {
            continue;
        }
        let (ax, ay) = (p[a][0], p[a][1]);
        let (dx, dy) = (p[b][0] - ax, p[b][1] - ay);
        let len = dx.hypot(dy);
        let mut best = (0.0f64, a);
        for (k, q) in p.iter().enumerate().take(b).skip(a + 1) {
            let dist = if len > 1e-12 {
                (dx * (q[1] - ay) - dy * (q[0] - ax)).abs() / len
            } else {
                (q[0] - ax).hypot(q[1] - ay)
            };
            if dist > best.0 {
                best = (dist, k);
            }
        }
        if best.0 > eps {
            keep[best.1] = true;
            stack.push((a, best.1));
            stack.push((best.1, b));
        }
    }
}

/// Simplifies a closed loop with tolerance `eps` (cells).
fn simplify_loop(p: &[[f64; 2]], eps: f64) -> Vec<[f64; 2]> {
    let n = p.len();
    if n <= 4 {
        return p.to_vec();
    }
    // Split at the point farthest from the first, then simplify both halves.
    let far = (1..n)
        .max_by(|&i, &j| {
            let di = (p[i][0] - p[0][0]).hypot(p[i][1] - p[0][1]);
            let dj = (p[j][0] - p[0][0]).hypot(p[j][1] - p[0][1]);
            di.total_cmp(&dj)
        })
        .unwrap_or(n / 2);
    let mut closed: Vec<[f64; 2]> = p.to_vec();
    closed.push(p[0]);
    let mut keep = vec![false; n + 1];
    keep[0] = true;
    keep[far] = true;
    keep[n] = true;
    simplify_chain(&closed[..=far], eps, &mut keep[..=far]);
    simplify_chain(&closed[far..], eps, &mut keep[far..]);
    (0..n).filter(|&k| keep[k]).map(|k| p[k]).collect()
}

/// Rings for a raster, normalised by `cell_norm`, each with at most
/// [`MAX_RING_POINTS`] points. The tolerance starts at `eps` cells and grows
/// until a ring fits. Rings that collapse below three points are dropped.
pub(crate) fn rings(m: &[bool], g: Grid, cell_norm: [f64; 2], eps: f64) -> Vec<Ring> {
    loops(m, g)
        .into_iter()
        .filter_map(|l| {
            let p: Vec<[f64; 2]> = l.iter().map(|q| [q[0] as f64, q[1] as f64]).collect();
            let mut tol = eps;
            let mut s = simplify_loop(&p, tol);
            while s.len() > MAX_RING_POINTS {
                tol *= 1.25;
                s = simplify_loop(&p, tol);
            }
            (s.len() >= 3).then(|| {
                s.iter()
                    .map(|q| {
                        [
                            (q[0] * cell_norm[0]).clamp(0.0, 1.0) as f32,
                            (q[1] * cell_norm[1]).clamp(0.0, 1.0) as f32,
                        ]
                    })
                    .collect()
            })
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::subject::outline::rasterize;

    /// Unsimplified loops fill back to the raster exactly, holes, diagonal
    /// touches and frame-edge parts included.
    #[test]
    fn loops_fill_back_exactly() {
        let (w, h) = (37usize, 23usize);
        let mut m = vec![false; w * h];
        for y in 0..h {
            for x in 0..w {
                let (fx, fy) = (x as f64 - 15.0, y as f64 - 11.0);
                let ring = (fx * fx + fy * fy).sqrt();
                m[y * w + x] = (ring < 9.0 && ring > 3.5) || (x + y) % 7 == 0 || (x > 30 && y < 4);
            }
        }
        let g = Grid { cols: w, rows: h };
        let cell = [1.0 / w as f64, 1.0 / h as f64];
        let rings: Vec<Ring> = loops(&m, g)
            .into_iter()
            .map(|l| {
                l.iter()
                    .map(|q| {
                        [
                            (q[0] as f64 * cell[0]) as f32,
                            (q[1] as f64 * cell[1]) as f32,
                        ]
                    })
                    .collect()
            })
            .collect();
        assert_eq!(rasterize(&rings, w, h, cell), m);
    }

    #[test]
    fn rings_respect_the_point_limit() {
        let (w, h) = (400usize, 300usize);
        let mut m = vec![false; w * h];
        for y in 0..h {
            for x in 0..w {
                let a = (y as f64 - 150.0).atan2(x as f64 - 200.0);
                let r = 100.0 + 30.0 * (17.0 * a).sin();
                m[y * w + x] = (x as f64 - 200.0).hypot(y as f64 - 150.0) < r;
            }
        }
        let g = Grid { cols: w, rows: h };
        let cell = [1.0 / w as f64, 1.0 / h as f64];
        let r = rings(&m, g, cell, 1.0);
        assert_eq!(r.len(), 1);
        assert!(r[0].len() <= MAX_RING_POINTS && r[0].len() >= 34);
        let back = rasterize(&r, w, h, cell);
        let inter = back.iter().zip(&m).filter(|(a, b)| **a && **b).count();
        let union = back.iter().zip(&m).filter(|(a, b)| **a || **b).count();
        assert!(inter as f64 / union as f64 > 0.97);
    }
}
