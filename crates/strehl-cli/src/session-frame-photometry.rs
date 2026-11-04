//! Per-frame radiometric normalization measured from alignment overlaps.
//!
//! Shutter metadata states intent, not delivered light. Lamps drift, dim or
//! change between passes, and a per-pass scalar cannot follow that. Every
//! accepted alignment edge already overlaps two frames, and defocus preserves
//! local means, so robust block-mean ratios through the fitted placement give
//! a direct relative-brightness measurement per edge. One global solve (never
//! a chain) then assigns each frame a log gain relative to the reference
//! frame. The spatial spread of block ratios within an edge is kept as
//! evidence: a light that moved changes shading, not just brightness, and no
//! scalar can represent it.
use strehl_core::align::{Cx, PlaneRef, Similarity};

/// Block side on the measurement plane.
pub const BLOCK: usize = 32;
/// Minimum usable blocks for an edge measurement.
pub const MIN_BLOCKS: usize = 6;
/// Blocks dimmer than this fraction of the clipping ceiling carry too little
/// signal; blocks reaching `CLIP_FRACTION` of it may be clipped.
pub const FLOOR_FRACTION: f32 = 0.01;
pub const CLIP_FRACTION: f32 = 0.85;

/// Relative brightness of frame `j` against frame `i` over their overlap.
#[derive(Clone, Copy, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct EdgePhotometry {
    pub i: usize,
    pub j: usize,
    /// `ln(mean_j / mean_i)` over usable blocks (median).
    pub log_ratio: f64,
    /// Robust spread (1.4826 MAD) of block log ratios: shading disagreement.
    pub spread: f64,
    pub blocks: usize,
}

fn bilinear(plane: PlaneRef<'_>, x: f64, y: f64) -> Option<f32> {
    if !(x >= 0.0 && y >= 0.0) {
        return None;
    }
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    if x0 + 1 >= plane.width() || y0 + 1 >= plane.height() {
        return None;
    }
    let (fx, fy) = ((x - x0 as f64) as f32, (y - y0 as f64) as f32);
    let top = plane.at(x0, y0) * (1.0 - fx) + plane.at(x0 + 1, y0) * fx;
    let bottom = plane.at(x0, y0 + 1) * (1.0 - fx) + plane.at(x0 + 1, y0 + 1) * fx;
    Some(top * (1.0 - fy) + bottom * fy)
}

fn median(values: &mut [f64]) -> f64 {
    values.sort_by(f64::total_cmp);
    let mid = values.len() / 2;
    if values.len() % 2 == 1 {
        values[mid]
    } else {
        0.5 * (values[mid - 1] + values[mid])
    }
}

/// Measure `ln(mean_moving / mean_reference)` through `t` (reference-centred to
/// moving-centred, both planes' own centres). `ceiling_*` are clipping levels
/// in plane units. Returns `(log_ratio, spread, blocks)`.
pub fn measure(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    t: Similarity,
    ceiling_reference: f32,
    ceiling_moving: f32,
) -> Option<(f64, f64, usize)> {
    if !(t.a.is_finite() && t.b.is_finite()) || t.a.norm_sq() <= 0.0 {
        return None;
    }
    let cr = Cx::new(
        reference.width() as f64 * 0.5,
        reference.height() as f64 * 0.5,
    );
    let cm = Cx::new(moving.width() as f64 * 0.5, moving.height() as f64 * 0.5);
    let map = |x: usize, y: usize| t.apply(Cx::new(x as f64, y as f64) - cr) + cm;
    let mut logs = Vec::new();
    for by in (BLOCK..reference.height().saturating_sub(2 * BLOCK)).step_by(BLOCK) {
        'block: for bx in (BLOCK..reference.width().saturating_sub(2 * BLOCK)).step_by(BLOCK) {
            let (mut sr, mut sm) = (0f64, 0f64);
            let (mut maxr, mut maxm) = (0f32, 0f32);
            for y in by..by + BLOCK {
                for x in bx..bx + BLOCK {
                    let r = reference.at(x, y);
                    let p = map(x, y);
                    let Some(m) = bilinear(moving, p.re, p.im) else {
                        continue 'block;
                    };
                    sr += f64::from(r);
                    sm += f64::from(m);
                    maxr = maxr.max(r);
                    maxm = maxm.max(m);
                }
            }
            let n = (BLOCK * BLOCK) as f64;
            let (mr, mm) = (sr / n, sm / n);
            if mr < f64::from(FLOOR_FRACTION * ceiling_reference)
                || mm < f64::from(FLOOR_FRACTION * ceiling_moving)
                || maxr >= CLIP_FRACTION * ceiling_reference
                || maxm >= CLIP_FRACTION * ceiling_moving
            {
                continue;
            }
            logs.push((mm / mr).ln());
        }
    }
    if logs.len() < MIN_BLOCKS || logs.iter().any(|v| !v.is_finite()) {
        return None;
    }
    let centre = median(&mut logs.clone());
    let mut deviations: Vec<f64> = logs.iter().map(|v| (v - centre).abs()).collect();
    let spread = 1.4826 * median(&mut deviations);
    Some((centre, spread, logs.len()))
}

/// Global per-frame log brightness relative to `reference`.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct FramePhotometry {
    /// `ln(brightness_k / brightness_reference)`; `None` outside the component.
    pub log_brightness: Vec<Option<f64>>,
    pub edges_used: usize,
    /// Weighted RMS of final edge residuals, natural-log units.
    pub residual_rms: f64,
}

impl FramePhotometry {
    /// Multiplicative gain mapping frame `k` into reference brightness units.
    pub fn gain(&self, k: usize) -> Option<f32> {
        self.log_brightness
            .get(k)
            .copied()
            .flatten()
            .map(|v| (-v).exp() as f32)
    }
}

/// Huber threshold for edge residuals (natural log, about 2%).
pub const HUBER: f64 = 0.02;
const SPREAD_FLOOR: f64 = 0.005;
/// Residuals beyond this many Huber thresholds are rejected outright.
pub const REJECT: f64 = 5.0;

/// Solve `x_j - x_i = r_ij` for frames connected to `reference` through
/// `edges`, with weights `blocks / (spread^2 + floor^2)` and Huber IRLS.
pub fn solve(frames: usize, reference: usize, edges: &[EdgePhotometry]) -> FramePhotometry {
    let mut out = FramePhotometry {
        log_brightness: vec![None; frames],
        edges_used: 0,
        residual_rms: 0.0,
    };
    if reference >= frames {
        return out;
    }
    let valid: Vec<&EdgePhotometry> = edges
        .iter()
        .filter(|e| {
            e.i < frames
                && e.j < frames
                && e.i != e.j
                && e.log_ratio.is_finite()
                && e.spread.is_finite()
                && e.blocks >= MIN_BLOCKS
        })
        .collect();
    // Connected component of the reference.
    let mut adjacency = vec![Vec::new(); frames];
    for (k, e) in valid.iter().enumerate() {
        adjacency[e.i].push(k);
        adjacency[e.j].push(k);
    }
    let mut seen = vec![false; frames];
    let mut stack = vec![reference];
    seen[reference] = true;
    while let Some(v) = stack.pop() {
        for &k in &adjacency[v] {
            let e = valid[k];
            let w = if e.i == v { e.j } else { e.i };
            if !seen[w] {
                seen[w] = true;
                stack.push(w);
            }
        }
    }
    let used: Vec<&EdgePhotometry> = valid
        .into_iter()
        .filter(|e| seen[e.i] && seen[e.j])
        .collect();
    let base: Vec<f64> = used
        .iter()
        .map(|e| e.blocks as f64 / (e.spread * e.spread + SPREAD_FLOOR * SPREAD_FLOOR))
        .collect();
    let mut x = vec![0.0f64; frames];
    let mut robust = vec![1.0f64; used.len()];
    for iteration in 0..6 {
        let w: Vec<f64> = base.iter().zip(&robust).map(|(a, b)| a * b).collect();
        x = conjugate_gradient(frames, reference, &seen, &used, &w, &x);
        for (k, e) in used.iter().enumerate() {
            let r = (x[e.j] - x[e.i] - e.log_ratio).abs();
            // Huber first; once the solution is anchored, redescend so a gross
            // contradiction carries no weight instead of a bounded pull.
            robust[k] = if r <= HUBER {
                1.0
            } else if iteration >= 1 && r > REJECT * HUBER {
                0.0
            } else {
                HUBER / r
            };
        }
    }
    let (mut num, mut den) = (0.0, 0.0);
    for (k, e) in used.iter().enumerate() {
        let r = x[e.j] - x[e.i] - e.log_ratio;
        num += base[k] * robust[k] * r * r;
        den += base[k] * robust[k];
    }
    out.edges_used = used.len();
    out.residual_rms = if den > 0.0 { (num / den).sqrt() } else { 0.0 };
    for k in 0..frames {
        if seen[k] {
            out.log_brightness[k] = Some(x[k]);
        }
    }
    out
}

/// Solve the weighted graph Laplacian with `x[reference] = 0` fixed.
fn conjugate_gradient(
    frames: usize,
    reference: usize,
    active: &[bool],
    edges: &[&EdgePhotometry],
    weights: &[f64],
    start: &[f64],
) -> Vec<f64> {
    let apply = |v: &[f64]| -> Vec<f64> {
        let mut out = vec![0.0; frames];
        for (e, &w) in edges.iter().zip(weights) {
            let d = w * (v[e.j] - v[e.i]);
            out[e.j] += d;
            out[e.i] -= d;
        }
        out[reference] = v[reference];
        for k in 0..frames {
            if !active[k] {
                out[k] = v[k];
            }
        }
        out
    };
    let mut b = vec![0.0; frames];
    for (e, &w) in edges.iter().zip(weights) {
        b[e.j] += w * e.log_ratio;
        b[e.i] -= w * e.log_ratio;
    }
    b[reference] = 0.0;
    for k in 0..frames {
        if !active[k] {
            b[k] = 0.0;
        }
    }
    let mut x = start.to_vec();
    x[reference] = 0.0;
    let ax = apply(&x);
    let mut r: Vec<f64> = b.iter().zip(&ax).map(|(b, a)| b - a).collect();
    let mut p = r.clone();
    let mut rr: f64 = r.iter().map(|v| v * v).sum();
    let scale: f64 = b.iter().map(|v| v * v).sum::<f64>().max(1e-30);
    for _ in 0..(4 * frames).max(50) {
        if rr <= 1e-24 * scale {
            break;
        }
        let ap = apply(&p);
        let pap: f64 = p.iter().zip(&ap).map(|(a, b)| a * b).sum();
        if pap <= 0.0 {
            break;
        }
        let alpha = rr / pap;
        for k in 0..frames {
            x[k] += alpha * p[k];
            r[k] -= alpha * ap[k];
        }
        let next: f64 = r.iter().map(|v| v * v).sum();
        let beta = next / rr;
        rr = next;
        for k in 0..frames {
            p[k] = r[k] + beta * p[k];
        }
    }
    x
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scene(x: f64, y: f64) -> f32 {
        (400.0 + 300.0 * ((x * 0.031).sin() * (y * 0.023).cos()) + 120.0 * ((x + y) * 0.07).sin())
            as f32
    }

    fn plane(w: usize, h: usize, gain: f32, shading: f32, t: Similarity) -> Vec<f32> {
        let inverse = t.invert().unwrap();
        let c = Cx::new(w as f64 * 0.5, h as f64 * 0.5);
        let mut data = vec![0.0; w * h];
        for y in 0..h {
            for x in 0..w {
                let p = inverse.apply(Cx::new(x as f64, y as f64) - c);
                let s = 1.0 + shading * (x as f32 / w as f32 - 0.5);
                data[y * w + x] = gain * s * scene(p.re, p.im);
            }
        }
        data
    }

    #[test]
    fn edge_ratio_recovers_gain_through_placement_and_flags_shading() {
        let (w, h) = (320, 240);
        let t = Similarity {
            a: Cx::new(1.03, 0.01),
            b: Cx::new(6.0, -4.0),
        };
        let reference = plane(w, h, 1.0, 0.0, Similarity::IDENTITY);
        let moving = plane(w, h, 0.8, 0.0, t);
        let r = PlaneRef::new(&reference, w, h).unwrap();
        let m = PlaneRef::new(&moving, w, h).unwrap();
        let (log, spread, blocks) = measure(r, m, t, 4000.0, 4000.0).unwrap();
        assert!((log - 0.8f64.ln()).abs() < 0.01, "log {log}");
        assert!(spread < 0.01 && blocks >= MIN_BLOCKS);
        // A light that moved: a left-right shading ramp is visible as spread.
        let shaded = plane(w, h, 0.8, 0.6, t);
        let s = PlaneRef::new(&shaded, w, h).unwrap();
        let (_, spread, _) = measure(r, s, t, 4000.0, 4000.0).unwrap();
        assert!(spread > 0.05, "spread {spread}");
        // Clipped or too-dark content is not measured.
        assert!(measure(r, m, t, 300.0, 300.0).is_none());
        assert!(measure(r, m, t, 1e6, 1e6).is_none());
    }

    fn edge(i: usize, j: usize, log_ratio: f64) -> EdgePhotometry {
        EdgePhotometry {
            i,
            j,
            log_ratio,
            spread: 0.005,
            blocks: 20,
        }
    }

    #[test]
    fn global_solve_recovers_drift_without_chaining_and_resists_an_outlier() {
        // Truth: brightness falls 2% per frame; frame 5 is unconnected.
        let truth = |k: usize| -0.02 * k as f64;
        let mut edges = Vec::new();
        for i in 0..5 {
            for j in i + 1..5 {
                edges.push(edge(i, j, truth(j) - truth(i)));
            }
        }
        edges.push(edge(1, 3, 0.5)); // gross outlier
        let solved = solve(6, 2, &edges);
        for k in 0..5 {
            let v = solved.log_brightness[k].unwrap();
            assert!((v - (truth(k) - truth(2))).abs() < 0.003, "frame {k}: {v}");
        }
        assert_eq!(solved.log_brightness[5], None);
        assert_eq!(solved.log_brightness[2], Some(0.0));
        assert!((solved.gain(0).unwrap() - (-0.04f32).exp()).abs() < 0.004);
        assert!(
            solve(3, 9, &edges)
                .log_brightness
                .iter()
                .all(Option::is_none)
        );
    }
}
