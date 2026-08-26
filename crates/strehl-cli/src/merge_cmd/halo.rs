//! The occlusion-halo correction (M87), **off by default and cosmetic**.
//!
//! # What it is for
//!
//! Every selection stacker puts a bright rim around a dark subject that meets a
//! bright out-of-focus background. M87 measured that rim on `bee-3-cpl` and
//! established three things about it that bound what this module may claim:
//!
//! - It is **not** a gate artifact. It is present at `--gate 0`, where every
//!   output pixel is one frame's pixel and nothing is averaged, and at
//!   `--gate 2` alike (M87 fact 1145).
//! - It is **not** mostly misregistration. Turning the M86 aligner on removes
//!   only `6.6%` of it, against the `91.7%` the drift hypothesis predicts
//!   (M87 P20-P26).
//! - It is **not** two depths at the edge. M63 killed the two-layer model, and
//!   M87's own attempt to unmix two layers reached only `-28.2%` on real data
//!   against a `-50%` bar.
//!
//! # What it does
//!
//! At a background pixel close to the subject silhouette, the elected frame is
//! very often the frame that put the *foreground's* defocus energy over that
//! pixel -- the pixel inherits the foreground's focus decision. This forbids
//! that. Every treated pixel takes the elected frame of its nearest foreground
//! pixel, `k_F`, and then re-elects a winner from only those frames with
//! `|k - k_F| >= delta`.
//!
//! # What it costs, and why it is off by default
//!
//! **This is a cosmetic filter. It makes the image measurably more wrong.**
//! Against a synthetic two-layer scene with known ground truth (M87 section 6.3),
//! at the shipped `delta = 40`:
//!
//! | scene | halo metric ISO | RMSE against truth in the band |
//! | --- | --- | --- |
//! | occluding edge, uncorrected | 0.03060 | 0.03462 |
//! | occluding edge, corrected | 0.00618 (`-79.8%`) | 0.12276 (**`+254.6%`**) |
//! | **no occluding edge**, uncorrected | 0.01367 | 0.01807 |
//! | **no occluding edge**, corrected | 0.00493 (`-63.9%`) | 0.11900 (**`+558.4%`**) |
//!
//! Read the last two rows before enabling this. On a region with **no defect at
//! all** the correction still "improves" the halo metric by `63.9%` while
//! raising the error against truth by `558.4%`. It is not depth-selective: it
//! moves `85.4%` of treated pixels at a *planted, non-occluding* disc in the
//! bee's own background against `82.1%` at the real occluding edge. It fires on
//! silhouettes, not on occlusions, and it cannot tell them apart.
//!
//! It is shipped because the rim is the single most objectionable thing in a
//! rendered stack and removing it is a legitimate thing to *choose*. It is off
//! by default because choosing it should be deliberate.
//!
//! Treated pixels are re-elected, not re-averaged: each takes one frame's
//! sample, so inside the yoke the gate's noise averaging is lost and the band
//! is noisier than its surroundings.
//!
//! M87's **ground-truth** measurements (§6, §16.1-§16.8) were made at gate 0,
//! where that is also true of the uncorrected image, so the numbers above are
//! like for like. It is **not** true that every M87 measurement was made at
//! gate 0 -- an earlier version of this comment said so and it was wrong. The
//! shipped-render arms ran at `--gate 2` (§16.9 and §31; the `72.9%` halo-metric
//! reduction, the zoomnull arm's `82.8%`, and P125's alignment split are all
//! gate-2 numbers). What no gate-2 arm measured is *this* cost specifically:
//! those arms scored the halo metric and hair-tip contrast, not the treated
//! band's noise. Against a gated merge that remains an additional, unmeasured
//! cost.
//!
//! The structural repair is not to measure it but to stop incurring it: an
//! estimator over frames keeps the gate's noise averaging by construction,
//! where a second election cannot. That is what the veil does, and it is why
//! the veil is not built on this module.
//!
//! Set `STREHL_FIX_HALO=1` to enable. It is an environment variable rather than
//! a flag for the same reason `STREHL_ALIGN` is one: the subcommand definition
//! in `main.rs` is owned by another agent tonight. The flag is the better
//! long-term home and the verbatim patch for it is in
//! `docs/research/M87-occlusion.md`.

use strehl_core::CfaPlane;
use strehl_core::merge::Estimator;
use strehl_core::plane::{PlaneGeometry, QuadSource};

/// Environment switch. Off unless explicitly turned on.
pub const FIX_ENV: &str = "STREHL_FIX_HALO";
/// Environment override for the forbidden half-band, in frames.
pub const DELTA_ENV: &str = "STREHL_FIX_HALO_DELTA";

/// How far from the silhouette a background pixel is still treated, in binned
/// pixels. Fixed at the value every M87 measurement used.
pub const YOKE: f32 = 40.0;

/// Half-width of the forbidden band around `k_F`, in frames.
///
/// M87 section 6.1 ran the ladder on both real stacks with one parameter set and
/// no refitting. `delta = 40` removes `87.9%` of the halo on `bee-3-cpl` and
/// `84.6%` on `flower-bud-with-background-fern-cpl`. `delta = 80` reaches
/// `-100.0%` and `-95.9%` but visibly softens hairs and claws, which are
/// narrower than the yoke, so their two flanking bands overlap and the whole
/// neighbourhood is forbidden its own focus frames. `40` is the largest value
/// that did not do that.
pub const DELTA: u16 = 40;

/// Radius of the morphological disc used to close and open the mask.
const DISC_R: i32 = 3;
/// Connected components smaller than this are not subjects.
const MIN_COMPONENT: usize = 2000;
/// Side of the median filter applied to the winner field before propagation.
const KF_MEDIAN: i32 = 15;
/// Histogram resolution of the Otsu threshold.
const OTSU_BINS: usize = 512;

/// Is the correction enabled?
pub fn enabled() -> bool {
    match std::env::var(FIX_ENV) {
        Ok(v) => !matches!(
            v.trim().to_ascii_lowercase().as_str(),
            "" | "0" | "off" | "false" | "no"
        ),
        Err(_) => false,
    }
}

/// The forbidden half-band actually in use.
pub fn delta_in_use() -> u16 {
    std::env::var(DELTA_ENV)
        .ok()
        .and_then(|v| v.trim().parse::<u16>().ok())
        .filter(|d| *d > 0)
        .unwrap_or(DELTA)
}

/// Standard two-class threshold. No peak-finding heuristic, no free knob.
///
/// Deliberately the same rule as the M87 Python instrument, which replaced a
/// registered two-mode-midpoint rule that put `46%` of a background-only ROI
/// inside the mask because this capture's *background* is itself bimodal.
pub fn otsu(a: &[f32]) -> f32 {
    let (mut lo, mut hi) = (f32::INFINITY, f32::NEG_INFINITY);
    for &v in a {
        if v.is_finite() {
            lo = lo.min(v);
            hi = hi.max(v);
        }
    }
    if hi.partial_cmp(&lo) != Some(core::cmp::Ordering::Greater) {
        return lo;
    }
    let scale = OTSU_BINS as f32 / (hi - lo);
    let mut hist = vec![0u64; OTSU_BINS];
    for &v in a {
        if v.is_finite() {
            let b = (((v - lo) * scale) as usize).min(OTSU_BINS - 1);
            hist[b] += 1;
        }
    }
    let centre = |b: usize| lo + (b as f32 + 0.5) / scale;
    let total: u64 = hist.iter().sum();
    let grand: f64 = hist
        .iter()
        .enumerate()
        .map(|(b, &c)| c as f64 * centre(b) as f64)
        .sum();
    let (mut w0, mut cw) = (0u64, 0f64);
    let (mut best, mut best_b) = (f64::NEG_INFINITY, 0usize);
    for (b, &h) in hist.iter().enumerate() {
        w0 += h;
        cw += h as f64 * centre(b) as f64;
        let w1 = total - w0;
        if w0 == 0 || w1 == 0 {
            continue;
        }
        let mu0 = cw / w0 as f64;
        let mu1 = (grand - cw) / w1 as f64;
        let score = w0 as f64 * w1 as f64 * (mu0 - mu1) * (mu0 - mu1);
        if score > best {
            best = score;
            best_b = b;
        }
    }
    centre(best_b)
}

fn disc(r: i32) -> Vec<(i32, i32)> {
    let mut v = Vec::new();
    for dy in -r..=r {
        for dx in -r..=r {
            if dy * dy + dx * dx <= r * r {
                v.push((dy, dx));
            }
        }
    }
    v
}

/// Binary dilation (`grow = true`) or erosion by a disc. Outside the frame
/// counts as background for both, so a closing cannot swallow the frame edge.
fn morph(src: &[bool], w: usize, h: usize, se: &[(i32, i32)], grow: bool) -> Vec<bool> {
    let mut out = vec![false; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut hit = !grow;
            for &(dy, dx) in se {
                let (ny, nx) = (y as i32 + dy, x as i32 + dx);
                let inside = ny >= 0 && nx >= 0 && (ny as usize) < h && (nx as usize) < w;
                let v = inside && src[ny as usize * w + nx as usize];
                if grow && v {
                    hit = true;
                    break;
                }
                if !grow && !v {
                    hit = false;
                    break;
                }
            }
            out[y * w + x] = hit;
        }
    }
    out
}

/// Drop 4-connected components below `MIN_COMPONENT` pixels.
fn drop_small(mask: &mut [bool], w: usize, h: usize) {
    let n = w * h;
    let mut seen = vec![false; n];
    let mut stack: Vec<usize> = Vec::new();
    let mut comp: Vec<usize> = Vec::new();
    for start in 0..n {
        if !mask[start] || seen[start] {
            continue;
        }
        comp.clear();
        stack.push(start);
        seen[start] = true;
        while let Some(i) = stack.pop() {
            comp.push(i);
            let (x, y) = (i % w, i / w);
            let mut nb = [usize::MAX; 4];
            if x > 0 {
                nb[0] = i - 1;
            }
            if x + 1 < w {
                nb[1] = i + 1;
            }
            if y > 0 {
                nb[2] = i - w;
            }
            if y + 1 < h {
                nb[3] = i + w;
            }
            for &j in nb.iter() {
                if j != usize::MAX && mask[j] && !seen[j] {
                    seen[j] = true;
                    stack.push(j);
                }
            }
        }
        if comp.len() < MIN_COMPONENT {
            for &i in &comp {
                mask[i] = false;
            }
        }
    }
}

/// Foreground mask: darker-than-Otsu, closed, opened, de-speckled.
///
/// **Assumes the subject is darker than its background**, which is true of both
/// stacks M87 measured and is the case the halo is worst in. On a bright
/// subject against a dark background this selects the background instead; that
/// limitation is recorded in the report rather than papered over with a
/// heuristic that was never measured.
pub fn foreground_mask(luma: &[f32], w: usize, h: usize) -> (Vec<bool>, f32) {
    let tau = otsu(luma);
    let mut m: Vec<bool> = luma.iter().map(|&v| v < tau).collect();
    let se = disc(DISC_R);
    // closing = dilate then erode; opening = erode then dilate.
    m = morph(&m, w, h, &se, true);
    m = morph(&m, w, h, &se, false);
    m = morph(&m, w, h, &se, false);
    m = morph(&m, w, h, &se, true);
    drop_small(&mut m, w, h);
    (m, tau)
}

/// Exact squared Euclidean distance transform with source indices.
///
/// Felzenszwalb & Huttenlocher's lower-envelope algorithm, run down the columns
/// and then across the rows. Exact, and linear in the pixel count: a chamfer
/// approximation would bias the yoke boundary along the diagonals, and the yoke
/// is the thing that decides which pixels are touched.
///
/// Returns `(squared distance to the nearest set pixel, index of that pixel)`.
pub fn edt(mask: &[bool], w: usize, h: usize) -> (Vec<f32>, Vec<u32>) {
    const INF: f32 = 1e20;
    let mut g = vec![INF; w * h];
    let mut gy = vec![u32::MAX; w * h];
    for x in 0..w {
        let mut last: Option<usize> = None;
        for y in 0..h {
            if mask[y * w + x] {
                last = Some(y);
            }
            if let Some(ly) = last {
                let d = (y - ly) as f32;
                g[y * w + x] = d * d;
                gy[y * w + x] = ly as u32;
            }
        }
        let mut last: Option<usize> = None;
        for y in (0..h).rev() {
            if mask[y * w + x] {
                last = Some(y);
            }
            if let Some(ly) = last {
                let d = (ly - y) as f32;
                if d * d < g[y * w + x] {
                    g[y * w + x] = d * d;
                    gy[y * w + x] = ly as u32;
                }
            }
        }
    }
    let mut dist = vec![INF; w * h];
    let mut src = vec![u32::MAX; w * h];
    if w == 0 || h == 0 {
        return (dist, src);
    }
    let mut v = vec![0usize; w];
    let mut z = vec![0f32; w + 1];
    for y in 0..h {
        let row = &g[y * w..y * w + w];
        // Columns that saw no foreground at all take no part in the envelope.
        let first = match (0..w).find(|&q| row[q] < INF) {
            Some(q) => q,
            None => continue,
        };
        let mut k = 0usize;
        v[0] = first;
        z[0] = -INF;
        z[1] = INF;
        for q in first + 1..w {
            if row[q] >= INF {
                continue;
            }
            loop {
                let p = v[k];
                let s = ((row[q] + (q * q) as f32) - (row[p] + (p * p) as f32))
                    / (2.0 * q as f32 - 2.0 * p as f32);
                if s <= z[k] && k > 0 {
                    k -= 1;
                } else {
                    k += 1;
                    v[k] = q;
                    z[k] = s;
                    z[k + 1] = INF;
                    break;
                }
            }
        }
        let mut k = 0usize;
        for x in 0..w {
            while z[k + 1] < x as f32 {
                k += 1;
            }
            let p = v[k];
            let d = x as f32 - p as f32;
            dist[y * w + x] = row[p] + d * d;
            src[y * w + x] = gy[y * w + p] * w as u32 + p as u32;
        }
    }
    (dist, src)
}

/// Which pixels get treated, and what frame each of them must avoid.
pub struct Plan {
    geom: PlaneGeometry,
    /// Pixel index of each treated pixel.
    pub treated: Vec<u32>,
    /// `k_F` for each treated pixel: the elected frame of its nearest
    /// foreground pixel, median-smoothed.
    pub kf: Vec<u16>,
    /// Pixel index -> slot in `treated`, or `u32::MAX`.
    slot: Vec<u32>,
    pub delta: u16,
    pub tau: f32,
    pub foreground_px: usize,
}

impl Plan {
    /// Build the plan from the completed pass-one winner field.
    ///
    /// `luma` is any per-pixel brightness on the plane grid; the merge passes
    /// the elected winner's green luma.
    pub fn build(luma: &[f32], best_index: &[u16], geom: PlaneGeometry, delta: u16) -> Plan {
        let (w, h) = (geom.width, geom.height);
        let n = w * h;
        assert_eq!(luma.len(), n, "luma is not on the plane grid");
        assert_eq!(best_index.len(), n, "winner field is not on the plane grid");
        let (mask, tau) = foreground_mask(luma, w, h);
        let foreground_px = mask.iter().filter(|m| **m).count();
        let (d2, near) = edt(&mask, w, h);
        let yoke2 = YOKE * YOKE;

        let mut treated = Vec::new();
        let mut slot = vec![u32::MAX; n];
        // Only foreground pixels that are somebody's nearest need a median,
        // which is a thin band rather than the whole subject.
        let mut needed = vec![false; n];
        for i in 0..n {
            if !mask[i] && d2[i] <= yoke2 && near[i] != u32::MAX {
                slot[i] = treated.len() as u32;
                treated.push(i as u32);
                needed[near[i] as usize] = true;
            }
        }

        let r = KF_MEDIAN / 2;
        let mut med = vec![0u16; n];
        let mut buf: Vec<u16> = Vec::with_capacity((KF_MEDIAN * KF_MEDIAN) as usize);
        for i in 0..n {
            if !needed[i] {
                continue;
            }
            let (x, y) = ((i % w) as i32, (i / w) as i32);
            buf.clear();
            for dy in -r..=r {
                for dx in -r..=r {
                    let (ny, nx) = (y + dy, x + dx);
                    if ny >= 0 && nx >= 0 && (ny as usize) < h && (nx as usize) < w {
                        buf.push(best_index[ny as usize * w + nx as usize]);
                    }
                }
            }
            buf.sort_unstable();
            med[i] = buf[buf.len() / 2];
        }

        let kf = treated
            .iter()
            .map(|&p| med[near[p as usize] as usize])
            .collect();
        Plan {
            geom,
            treated,
            kf,
            slot,
            delta,
            tau,
            foreground_px,
        }
    }

    pub fn treated_len(&self) -> usize {
        self.treated.len()
    }

    /// Is frame `k` allowed to win at treated slot `s`?
    #[inline]
    fn allows(&self, s: usize, k: u16) -> bool {
        (k as i32 - self.kf[s] as i32).unsigned_abs() >= self.delta as u32
    }
}

/// Per-chunk accumulator: the best *allowed* frame at each treated pixel.
pub struct Pass {
    best: Vec<f32>,
    val: Vec<[u16; 4]>,
    decided: Vec<bool>,
}

impl Pass {
    pub fn new(plan: &Plan) -> Pass {
        let m = plan.treated.len();
        Pass {
            best: vec![f32::NEG_INFINITY; m],
            val: vec![[0; 4]; m],
            decided: vec![false; m],
        }
    }

    /// Fold one frame's regularised response, considering treated pixels only.
    ///
    /// Uses the same `reg` field that elected the pass-one winner, so the
    /// re-election is the original election restricted to a subset of frames
    /// and nothing else.
    pub fn fold<S: QuadSource + ?Sized>(&mut self, plan: &Plan, index: u16, src: &S, reg: &[f32]) {
        let w = plan.geom.width;
        debug_assert_eq!(reg.len(), w * plan.geom.height);
        for (s, &p) in plan.treated.iter().enumerate() {
            if !plan.allows(s, index) {
                continue;
            }
            let i = p as usize;
            let f = reg[i];
            if !self.decided[s] || f > self.best[s] {
                let (py, px) = (i / w, i % w);
                let (top, bot) = src.quad_rows(py);
                self.best[s] = f;
                self.decided[s] = true;
                self.val[s] = [top[px * 2], top[px * 2 + 1], bot[px * 2], bot[px * 2 + 1]];
            }
        }
    }

    pub fn absorb(&mut self, other: &Pass) {
        for s in 0..self.best.len() {
            if other.decided[s] && (!self.decided[s] || other.best[s] > self.best[s]) {
                self.best[s] = other.best[s];
                self.decided[s] = true;
                self.val[s] = other.val[s];
            }
        }
    }

    /// Freeze into the substitution the writer consults.
    pub fn finish(self, plan: &Plan) -> Fix {
        let undecided = self.decided.iter().filter(|d| !**d).count();
        Fix {
            slot: plan.slot.clone(),
            val: self.val,
            decided: self.decided,
            treated: plan.treated.len(),
            undecided,
        }
    }
}

/// A sparse override of the merged planes at treated pixels.
pub struct Fix {
    slot: Vec<u32>,
    val: Vec<[u16; 4]>,
    decided: Vec<bool>,
    pub treated: usize,
    /// Treated pixels where **every** frame was forbidden. These keep the
    /// uncorrected value rather than inventing one.
    pub undecided: usize,
}

impl Fix {
    #[inline]
    fn at(&self, i: usize) -> Option<&[u16; 4]> {
        let s = *self.slot.get(i)?;
        if s == u32::MAX || !self.decided[s as usize] {
            return None;
        }
        Some(&self.val[s as usize])
    }

    /// The corrected value, or the estimator's own where untreated.
    #[inline]
    pub fn value(&self, est: &Estimator, p: CfaPlane, i: usize) -> f32 {
        match self.at(i) {
            Some(v) => {
                let s = match p {
                    CfaPlane::R => 0,
                    CfaPlane::G1 => 1,
                    CfaPlane::G2 => 2,
                    CfaPlane::B => 3,
                };
                v[s] as f32
            }
            None => est.value(p, i),
        }
    }

    #[inline]
    pub fn green_mean(&self, est: &Estimator, i: usize) -> f32 {
        match self.at(i) {
            Some(v) => 0.5 * (v[1] as f32 + v[2] as f32),
            None => est.green_mean(i),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn otsu_splits_a_clean_two_class_histogram() {
        let mut a = vec![10.0f32; 500];
        a.extend(std::iter::repeat_n(90.0f32, 500));
        let t = otsu(&a);
        assert!(t > 10.0 && t < 90.0, "threshold {t} did not separate");
    }

    #[test]
    fn edt_is_exact_on_a_single_seed() {
        let (w, h) = (9usize, 7usize);
        let mut m = vec![false; w * h];
        m[3 * w + 4] = true;
        let (d2, src) = edt(&m, w, h);
        for y in 0..h {
            for x in 0..w {
                let want = ((x as i32 - 4).pow(2) + (y as i32 - 3).pow(2)) as f32;
                assert_eq!(d2[y * w + x], want, "at ({x},{y})");
                assert_eq!(src[y * w + x], (3 * w + 4) as u32);
            }
        }
    }

    #[test]
    fn edt_matches_brute_force_on_a_scattered_mask() {
        let (w, h) = (23usize, 19usize);
        let mut m = vec![false; w * h];
        for (i, s) in m.iter_mut().enumerate() {
            *s = (i * 7919) % 37 == 0;
        }
        let seeds: Vec<usize> = (0..w * h).filter(|i| m[*i]).collect();
        assert!(seeds.len() > 5, "the plant must actually contain seeds");
        let (d2, _) = edt(&m, w, h);
        for y in 0..h {
            for x in 0..w {
                let want = seeds
                    .iter()
                    .map(|&s| {
                        let (sx, sy) = ((s % w) as i32, (s / w) as i32);
                        ((x as i32 - sx).pow(2) + (y as i32 - sy).pow(2)) as f32
                    })
                    .fold(f32::INFINITY, f32::min);
                assert_eq!(d2[y * w + x], want, "at ({x},{y})");
            }
        }
    }

    #[test]
    fn the_band_is_the_only_thing_that_vetoes_a_frame() {
        let plan = Plan {
            geom: PlaneGeometry {
                width: 4,
                height: 4,
            },
            treated: vec![0],
            kf: vec![100],
            slot: {
                let mut s = vec![u32::MAX; 16];
                s[0] = 0;
                s
            },
            delta: 40,
            tau: 0.0,
            foreground_px: 0,
        };
        assert!(!plan.allows(0, 100), "the foreground's own frame must be out");
        assert!(!plan.allows(0, 139), "39 frames away is inside the band");
        assert!(plan.allows(0, 140), "40 frames away is the first allowed");
        assert!(plan.allows(0, 60), "and symmetrically on the near side");
        assert!(!plan.allows(0, 61));
    }

    #[test]
    fn an_untreated_pixel_is_never_overridden() {
        // A Fix with nothing treated must be a no-op at every pixel, which is
        // what makes "off" and "on, but away from a silhouette" the same image.
        let fix = Fix {
            slot: vec![u32::MAX; 16],
            val: vec![],
            decided: vec![],
            treated: 0,
            undecided: 0,
        };
        for i in 0..16 {
            assert!(fix.at(i).is_none());
        }
    }

    #[test]
    fn a_small_speck_is_not_a_subject() {
        let (w, h) = (60usize, 60usize);
        let mut m = vec![false; w * h];
        for y in 10..14 {
            for x in 10..14 {
                m[y * w + x] = true;
            }
        }
        drop_small(&mut m, w, h);
        assert!(
            m.iter().all(|v| !v),
            "a 16 px blob is not a {MIN_COMPONENT} px subject"
        );
    }
}
