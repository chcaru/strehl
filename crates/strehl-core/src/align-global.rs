//! Wide-baseline global similarity proposals between two planes.
//!
//! The ordinary coarse ladder in [`crate::align`] searches a few pixels about
//! identity, which suits focus breathing inside one sweep. Separate passes of
//! the same subject can differ by tens of percent of the frame in translation
//! and by several times in magnification (a close-up pass beside a whole-body
//! pass). This module searches scale, rotation and **all** translations at low
//! resolution with masked normalized cross-correlation (gain/offset invariant,
//! overlap-aware), in both magnification directions, and returns a few diverse
//! candidates.
//!
//! A candidate is only a **search proposal**. It never enters a placement on its
//! own: callers must refine it with the ordinary direct fine stage
//! ([`crate::align::refine_pair_observed`]) and accept only what that measures.
//! Low-resolution NCC can prefer a wrong but plausible overlap; returning
//! several candidates and letting the direct measurement arbitrate is the
//! defence, not a higher NCC bar.
use crate::align::{Cx, PlaneRef, Similarity, downsample, lift_box_decimated_similarity};
use rayon::prelude::*;

/// Explicit search bounds. Defaults cover 4x magnification either way and
/// +-12 degrees of rotation; translation is unrestricted.
#[derive(Clone, Debug, PartialEq)]
pub struct GlobalSearchConfig {
    /// Long side of the coarse search plane, px.
    pub side: usize,
    /// Long side of the local refinement plane, px. Zero disables refinement.
    pub refine_side: usize,
    /// Largest magnification ratio searched in either direction.
    pub max_scale: f64,
    /// Natural-log scale step of the coarse grid.
    pub log_scale_step: f64,
    /// Largest absolute rotation, radians.
    pub max_rotation: f64,
    /// Rotation step of the coarse grid, radians.
    pub rotation_step: f64,
    /// Minimum overlap as a fraction of the smaller footprint (in fixed px).
    pub min_overlap_fraction: f64,
    /// Number of diverse candidates returned.
    pub candidates: usize,
}

impl Default for GlobalSearchConfig {
    fn default() -> Self {
        Self {
            side: 128,
            refine_side: 256,
            max_scale: 4.0,
            log_scale_step: 0.04,
            max_rotation: 12f64.to_radians(),
            rotation_step: 3f64.to_radians(),
            min_overlap_fraction: 0.3,
            candidates: 4,
        }
    }
}

impl GlobalSearchConfig {
    fn valid(&self) -> bool {
        (32..=512).contains(&self.side)
            && (self.refine_side == 0 || (self.side..=1024).contains(&self.refine_side))
            && self.max_scale.is_finite()
            && (1.0..=8.0).contains(&self.max_scale)
            && self.log_scale_step.is_finite()
            && self.log_scale_step > 0.0
            && self.max_rotation.is_finite()
            && (0.0..=std::f64::consts::FRAC_PI_2).contains(&self.max_rotation)
            && self.rotation_step.is_finite()
            && self.rotation_step > 0.0
            && self.min_overlap_fraction.is_finite()
            && (0.01..=1.0).contains(&self.min_overlap_fraction)
            && (1..=32).contains(&self.candidates)
    }
}

/// One proposal: `transform` maps reference-centred to moving-centred
/// coordinates of the input planes, as every [`Similarity`] in this crate.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct GlobalCandidate {
    pub transform: Similarity,
    /// Masked NCC at the proposal on the finest searched plane.
    pub ncc: f64,
    /// Overlap in finest-search pixels of the fixed plane.
    pub overlap: f64,
}

// ---------------------------------------------------------------------------
// FFT (iterative radix-2, f64). Small and local: the crate carries no FFT
// dependency and these sizes are powers of two at most 2048.
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, Default)]
struct C {
    re: f64,
    im: f64,
}

impl C {
    #[inline]
    fn mul(self, o: C) -> C {
        C {
            re: self.re * o.re - self.im * o.im,
            im: self.re * o.im + self.im * o.re,
        }
    }
    #[inline]
    fn conj(self) -> C {
        C {
            re: self.re,
            im: -self.im,
        }
    }
}

struct Fft1 {
    n: usize,
    rev: Vec<usize>,
    twiddle: Vec<C>,
}

impl Fft1 {
    fn new(n: usize) -> Self {
        assert!(n.is_power_of_two() && n >= 2);
        let bits = n.trailing_zeros();
        let rev = (0..n)
            .map(|i| i.reverse_bits() >> (usize::BITS - bits))
            .collect();
        let twiddle = (0..n / 2)
            .map(|k| {
                let angle = -2.0 * std::f64::consts::PI * k as f64 / n as f64;
                C {
                    re: angle.cos(),
                    im: angle.sin(),
                }
            })
            .collect();
        Self { n, rev, twiddle }
    }

    /// In-place forward transform; the inverse is conj-forward-conj / n.
    fn forward(&self, data: &mut [C]) {
        let n = self.n;
        for i in 0..n {
            let j = self.rev[i];
            if i < j {
                data.swap(i, j);
            }
        }
        let mut len = 2;
        while len <= n {
            let step = n / len;
            for start in (0..n).step_by(len) {
                for k in 0..len / 2 {
                    let w = self.twiddle[k * step];
                    let u = data[start + k];
                    let v = data[start + k + len / 2].mul(w);
                    data[start + k] = C {
                        re: u.re + v.re,
                        im: u.im + v.im,
                    };
                    data[start + k + len / 2] = C {
                        re: u.re - v.re,
                        im: u.im - v.im,
                    };
                }
            }
            len <<= 1;
        }
    }
}

struct Fft2 {
    width: usize,
    height: usize,
    rows: Fft1,
    cols: Fft1,
}

impl Fft2 {
    fn new(width: usize, height: usize) -> Self {
        Self {
            width,
            height,
            rows: Fft1::new(width),
            cols: Fft1::new(height),
        }
    }

    fn forward(&self, data: &mut [C]) {
        for row in data.chunks_mut(self.width) {
            self.rows.forward(row);
        }
        let mut column = vec![C::default(); self.height];
        for x in 0..self.width {
            for (y, value) in column.iter_mut().enumerate() {
                *value = data[y * self.width + x];
            }
            self.cols.forward(&mut column);
            for (y, value) in column.iter().enumerate() {
                data[y * self.width + x] = *value;
            }
        }
    }

    fn inverse(&self, data: &mut [C]) {
        for value in data.iter_mut() {
            *value = value.conj();
        }
        self.forward(data);
        let scale = 1.0 / (self.width * self.height) as f64;
        for value in data.iter_mut() {
            *value = C {
                re: value.re * scale,
                im: -value.im * scale,
            };
        }
    }
}

// ---------------------------------------------------------------------------
// Low-resolution planes
// ---------------------------------------------------------------------------

#[derive(Clone)]
struct Low {
    data: Vec<f64>,
    width: usize,
    height: usize,
}

impl Low {
    fn centre(&self) -> Cx {
        Cx::new(self.width as f64 * 0.5, self.height as f64 * 0.5)
    }
}

/// Box-decimate by `factor`, compress dynamic range (macro subjects on dark
/// backgrounds) and remove the mean to limit cancellation in the NCC sums.
fn low(plane: PlaneRef<'_>, factor: usize) -> Option<Low> {
    let decimated = downsample(plane, factor)?;
    let mut data: Vec<f64> = decimated
        .data
        .iter()
        .map(|&v| f64::from(v.max(0.0)).sqrt())
        .collect();
    if data.iter().any(|v| !v.is_finite()) {
        return None;
    }
    let mean = data.iter().sum::<f64>() / data.len() as f64;
    for value in &mut data {
        *value -= mean;
    }
    Some(Low {
        data,
        width: decimated.width,
        height: decimated.height,
    })
}

/// Factor-2 box pyramid of a low plane for anti-aliased minification.
fn pyramid(base: &Low) -> Vec<Low> {
    let mut levels = vec![base.clone()];
    while levels.len() < 4 {
        let last = levels.last().expect("level");
        let (w, h) = (last.width / 2, last.height / 2);
        if w < 4 || h < 4 {
            break;
        }
        let mut data = vec![0.0; w * h];
        for y in 0..h {
            for x in 0..w {
                let i = 2 * y * last.width + 2 * x;
                data[y * w + x] = 0.25
                    * (last.data[i]
                        + last.data[i + 1]
                        + last.data[i + last.width]
                        + last.data[i + last.width + 1]);
            }
        }
        levels.push(Low {
            data,
            width: w,
            height: h,
        });
    }
    levels
}

/// Bilinear sample of the level-0 coordinate `(x, y)` from a factor-2 pyramid
/// level `level`; `None` outside the plane.
fn sample(levels: &[Low], level: usize, x: f64, y: f64) -> Option<f64> {
    let plane = &levels[level];
    let s = (1usize << level) as f64;
    let (u, v) = ((x - (s - 1.0) * 0.5) / s, (y - (s - 1.0) * 0.5) / s);
    if !(u >= 0.0 && v >= 0.0) {
        return None;
    }
    let (x0, y0) = (u.floor() as usize, v.floor() as usize);
    if x0 + 1 >= plane.width || y0 + 1 >= plane.height {
        return None;
    }
    let (fx, fy) = (u - x0 as f64, v - y0 as f64);
    let i = y0 * plane.width + x0;
    let top = plane.data[i] * (1.0 - fx) + plane.data[i + 1] * fx;
    let bottom = plane.data[i + plane.width] * (1.0 - fx) + plane.data[i + plane.width + 1] * fx;
    Some(top * (1.0 - fy) + bottom * fy)
}

/// Fixed-plane spectra, reused by every hypothesis in one direction.
struct Fixed {
    plane: Low,
    fft: Fft2,
    mask: Vec<C>,
    value: Vec<C>,
    square: Vec<C>,
}

fn spectrum(fft: &Fft2, plane_width: usize, values: impl Fn(usize) -> Option<f64>) -> Vec<C> {
    let mut buffer = vec![C::default(); fft.width * fft.height];
    for (index, slot) in buffer.iter_mut().enumerate() {
        let (x, y) = (index % fft.width, index / fft.width);
        if x < plane_width
            && let Some(v) = values(y * plane_width + x)
        {
            *slot = C { re: v, im: 0.0 };
        }
    }
    fft.forward(&mut buffer);
    buffer
}

impl Fixed {
    fn new(plane: Low, fft: Fft2) -> Self {
        let n = plane.data.len();
        let get = |f: fn(f64) -> f64| {
            let data = &plane.data;
            move |i: usize| (i < n).then(|| f(data[i]))
        };
        let mask = spectrum(&fft, plane.width, get(|_| 1.0));
        let value = spectrum(&fft, plane.width, get(|v| v));
        let square = spectrum(&fft, plane.width, get(|v| v * v));
        Self {
            plane,
            fft,
            mask,
            value,
            square,
        }
    }
}

/// One hypothesis outcome on a given grid.
#[derive(Clone, Copy, Debug)]
struct Peak {
    /// Moving plane more magnified than fixed: `swapped` is false when the
    /// fixed plane is the caller's reference.
    swapped: bool,
    a: Cx,
    /// Translation in fixed-centred px: fixed point x maps to moving a*(x+t).
    t: Cx,
    ncc: f64,
    overlap: f64,
}

/// Moving plane resampled onto a grid in fixed-centred coordinates.
struct Warped {
    /// Fixed-centred coordinate of grid pixel (0, 0).
    origin: Cx,
    width: usize,
    height: usize,
    values: Vec<f64>,
    mask: Vec<bool>,
}

/// Resample the moving plane through `a` onto a fixed-centred grid.
fn warped(moving: &[Low], a: Cx) -> Option<Warped> {
    let base = &moving[0];
    let inv = a.recip()?;
    let cm = base.centre();
    let corners = [
        Cx::new(0.0, 0.0),
        Cx::new(base.width as f64, 0.0),
        Cx::new(0.0, base.height as f64),
        Cx::new(base.width as f64, base.height as f64),
    ]
    .map(|p| inv * (p - cm));
    let (mut lo, mut hi) = (corners[0], corners[0]);
    for c in corners {
        lo = Cx::new(lo.re.min(c.re), lo.im.min(c.im));
        hi = Cx::new(hi.re.max(c.re), hi.im.max(c.im));
    }
    let origin = Cx::new(lo.re.floor(), lo.im.floor());
    let width = (hi.re.ceil() - origin.re) as usize + 1;
    let height = (hi.im.ceil() - origin.im) as usize + 1;
    let level = (a.abs().log2().floor().max(0.0) as usize).min(moving.len() - 1);
    let mut values = vec![0.0; width * height];
    let mut mask = vec![false; width * height];
    for q in 0..height {
        for p in 0..width {
            let y = origin + Cx::new(p as f64, q as f64);
            let z = a * y + cm;
            if let Some(v) = sample(moving, level, z.re, z.im) {
                values[q * width + p] = v;
                mask[q * width + p] = true;
            }
        }
    }
    Some(Warped {
        origin,
        width,
        height,
        values,
        mask,
    })
}

/// Masked NCC of the fixed plane against the warped moving plane for every
/// translation (Padfield's FFT formulation). `window` optionally restricts the
/// searched translations to a disc about a predicted fixed-centred `t`.
fn correlate(
    fixed: &Fixed,
    moving: &[Low],
    a: Cx,
    swapped: bool,
    min_overlap_fraction: f64,
    window: Option<(Cx, f64)>,
) -> Option<Peak> {
    let Warped {
        origin,
        width: gw,
        height: gh,
        values,
        mask,
    } = warped(moving, a)?;
    let fft = &fixed.fft;
    if gw + fixed.plane.width > fft.width || gh + fixed.plane.height > fft.height {
        return None;
    }
    let footprint = mask.iter().filter(|&&m| m).count() as f64;
    let minimum = (min_overlap_fraction * footprint.min(fixed.plane.data.len() as f64)).max(64.0);
    let spectra = [0, 1, 2].map(|kind| {
        let mut buffer = vec![C::default(); fft.width * fft.height];
        for q in 0..gh {
            for p in 0..gw {
                let i = q * gw + p;
                if mask[i] {
                    let v = values[i];
                    buffer[q * fft.width + p].re = match kind {
                        0 => 1.0,
                        1 => v,
                        _ => v * v,
                    };
                }
            }
        }
        fft.forward(&mut buffer);
        buffer
    });
    // corr(A, B)(d) = sum_p A(p) B(p + d)  <->  conj(A^) . B^
    let product = |a: &[C], b: &[C]| -> Vec<C> {
        let mut out: Vec<C> = a.iter().zip(b).map(|(x, y)| x.conj().mul(*y)).collect();
        fft.inverse(&mut out);
        out
    };
    let n = product(&fixed.mask, &spectra[0]);
    let sf = product(&fixed.value, &spectra[0]);
    let sff = product(&fixed.square, &spectra[0]);
    let sg = product(&fixed.mask, &spectra[1]);
    let sgg = product(&fixed.mask, &spectra[2]);
    let sfg = product(&fixed.value, &spectra[1]);
    drop(spectra);
    let cf = fixed.plane.centre();
    let mut best: Option<Peak> = None;
    for k in 0..fft.height {
        let dy = if k < gh {
            k as isize
        } else if k > fft.height - fixed.plane.height {
            k as isize - fft.height as isize
        } else {
            continue;
        };
        for j in 0..fft.width {
            let dx = if j < gw {
                j as isize
            } else if j > fft.width - fixed.plane.width {
                j as isize - fft.width as isize
            } else {
                continue;
            };
            // Fixed pixel p <-> x = p - cf; grid pixel q <-> y = q + origin.
            // q = p + d and y = x + t give t = d + origin + cf.
            let t = Cx::new(dx as f64, dy as f64) + origin + cf;
            if let Some((centre, radius)) = window
                && (t - centre).abs() > radius
            {
                continue;
            }
            let i = k * fft.width + j;
            let count = n[i].re;
            if count < minimum {
                continue;
            }
            let vf = sff[i].re - sf[i].re * sf[i].re / count;
            let vg = sgg[i].re - sg[i].re * sg[i].re / count;
            if vf <= 1e-9 * count || vg <= 1e-9 * count {
                continue;
            }
            let ncc = (sfg[i].re - sf[i].re * sg[i].re / count) / (vf * vg).sqrt();
            if ncc.is_finite() && best.is_none_or(|b| ncc > b.ncc) {
                best = Some(Peak {
                    swapped,
                    a,
                    t,
                    ncc,
                    overlap: count,
                });
            }
        }
    }
    best
}

fn fft_for(fixed: &Low, max_scale: f64) -> Fft2 {
    // Rotated grids can exceed the fixed extent by up to sqrt(2) when a is
    // near 1; size for that so every hypothesis fits without wrap-around.
    let grow = |n: usize| {
        let worst = n as f64 + (n as f64 * std::f64::consts::SQRT_2 / max_scale.min(1.0)) + 4.0;
        (worst.ceil() as usize).next_power_of_two()
    };
    let side = grow(fixed.width).max(grow(fixed.height));
    Fft2::new(side, side)
}

fn hypotheses(cfg: &GlobalSearchConfig) -> Vec<Cx> {
    let steps = (cfg.max_scale.ln() / cfg.log_scale_step).floor() as usize;
    let rotations = (cfg.max_rotation / cfg.rotation_step).floor() as isize;
    let mut out = Vec::new();
    for s in 0..=steps {
        let scale = (s as f64 * cfg.log_scale_step).exp();
        for r in -rotations..=rotations {
            let theta = r as f64 * cfg.rotation_step;
            out.push(Cx::new(scale * theta.cos(), scale * theta.sin()));
        }
    }
    out
}

/// Distinct within the coarse search's resolving power.
fn same(a: &Peak, b: &Peak, cfg: &GlobalSearchConfig) -> bool {
    a.swapped == b.swapped
        && (a.a.abs().ln() - b.a.abs().ln()).abs() < 2.5 * cfg.log_scale_step
        && (a.a.im.atan2(a.a.re) - b.a.im.atan2(b.a.re)).abs() < 2.5 * cfg.rotation_step
        && (a.t - b.t).abs() < 6.0
}

/// Low-resolution similarity in caller orientation (reference -> moving),
/// lifted back to the input plane coordinates.
fn lift(
    peak: &Peak,
    factor: usize,
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
) -> Option<Similarity> {
    // Fixed -> warped-moving similarity on the low planes: z = a (x + t).
    let low = Similarity {
        a: peak.a,
        b: peak.a * peak.t,
    };
    let (fixed_geom, moving_geom) = if peak.swapped {
        (moving.geometry(), reference.geometry())
    } else {
        (reference.geometry(), moving.geometry())
    };
    let lifted = lift_box_decimated_similarity(low, fixed_geom, moving_geom, factor)?;
    if peak.swapped {
        lifted.invert()
    } else {
        Some(lifted)
    }
}

/// Propose up to `cfg.candidates` diverse reference->moving similarities, best
/// first. Returns an empty list when the planes are too small or flat.
pub fn global_similarity_candidates(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    cfg: &GlobalSearchConfig,
) -> Vec<GlobalCandidate> {
    if !cfg.valid() {
        return Vec::new();
    }
    let long = reference
        .width()
        .max(reference.height())
        .max(moving.width())
        .max(moving.height());
    let factor = long.div_ceil(cfg.side).max(1);
    let (Some(r), Some(m)) = (low(reference, factor), low(moving, factor)) else {
        return Vec::new();
    };
    let directions = [
        (
            false,
            Fixed::new(r.clone(), fft_for(&r, cfg.max_scale)),
            pyramid(&m),
        ),
        (
            true,
            Fixed::new(m.clone(), fft_for(&m, cfg.max_scale)),
            pyramid(&r),
        ),
    ];
    let grid = hypotheses(cfg);
    let mut peaks: Vec<Peak> = directions
        .par_iter()
        .flat_map(|(swapped, fixed, moving)| {
            grid.par_iter()
                .filter(move |a| !*swapped || a.abs() > 1.0 + 1e-9)
                .filter_map(move |&a| {
                    correlate(fixed, moving, a, *swapped, cfg.min_overlap_fraction, None)
                })
        })
        .collect();
    peaks.sort_by(|a, b| b.ncc.total_cmp(&a.ncc));
    let mut chosen: Vec<Peak> = Vec::new();
    for peak in peaks {
        if chosen.len() >= cfg.candidates.max(1) * 2 {
            break;
        }
        if !chosen.iter().any(|c| same(c, &peak, cfg)) {
            chosen.push(peak);
        }
    }
    // Local refinement on a finer plane; translation re-searched in a disc.
    let (chosen, final_factor) = if cfg.refine_side > cfg.side {
        let fine_factor = long.div_ceil(cfg.refine_side).max(1);
        match (low(reference, fine_factor), low(moving, fine_factor)) {
            (Some(rf), Some(mf)) if fine_factor < factor => {
                let ratio = factor as f64 / fine_factor as f64;
                let fixed = [
                    Fixed::new(rf.clone(), fft_for(&rf, cfg.max_scale)),
                    Fixed::new(mf.clone(), fft_for(&mf, cfg.max_scale)),
                ];
                let pyramids = [pyramid(&mf), pyramid(&rf)];
                let refined: Vec<Peak> = chosen
                    .par_iter()
                    .filter_map(|peak| {
                        let side = usize::from(peak.swapped);
                        let (scale, theta) = (peak.a.abs(), peak.a.im.atan2(peak.a.re));
                        let mut local = Vec::new();
                        for ds in [-0.5, 0.0, 0.5] {
                            for dr in [-0.5, 0.0, 0.5] {
                                let s = scale * (ds * cfg.log_scale_step).exp();
                                let r = theta + dr * cfg.rotation_step;
                                local.push(Cx::new(s * r.cos(), s * r.sin()));
                            }
                        }
                        local
                            .into_iter()
                            .filter_map(|a| {
                                correlate(
                                    &fixed[side],
                                    &pyramids[side],
                                    a,
                                    peak.swapped,
                                    cfg.min_overlap_fraction,
                                    Some((peak.t.scale(ratio), 2.0 * ratio + 3.0)),
                                )
                            })
                            .max_by(|a, b| a.ncc.total_cmp(&b.ncc))
                    })
                    .collect();
                (refined, fine_factor)
            }
            _ => (chosen, factor),
        }
    } else {
        (chosen, factor)
    };
    let mut sorted = chosen;
    sorted.sort_by(|a, b| b.ncc.total_cmp(&a.ncc));
    let mut out: Vec<GlobalCandidate> = Vec::new();
    for peak in sorted {
        if out.len() >= cfg.candidates {
            break;
        }
        if let Some(transform) = lift(&peak, final_factor, reference, moving) {
            out.push(GlobalCandidate {
                transform,
                ncc: peak.ncc,
                overlap: peak.overlap,
            });
        }
    }
    out
}

#[cfg(test)]
#[path = "align-global-tests.rs"]
mod tests;
