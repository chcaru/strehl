//! Per-capture refinement of the lateral-CA correction.
//!
//! The shipped profile (`crate::optics`) carries one radial coefficient per
//! channel, and SYNTHESIS fact 1570 measured why no constant can be right: a
//! channel's effective wavelength is weighted by the scene's own spectrum, so
//! red's native scale ran from -258 to -611 ppm across seven captures against
//! the profile's -508. The same captures also carry a red/blue *translation*
//! of up to 0.3 px that the profile does not apply.
//!
//! This module measures what a correction **leaves**: given a demosaiced RGB
//! image rendered with the current correction (a cheap preview merge of a
//! subset of frames), it fits, per channel, the displacement of red and of
//! blue relative to green as `translation + scale x (position - centre)`.
//! Adding that to the correction and rendering again is the refinement
//! measured in `experiments/image-quality-2026-11-02/results.md` section 3c.
//!
//! Method -- a port of the instrument whose corrections measured best there
//! (`ca-residual.py`), chosen over three alternatives by rendering each
//! one's correction and scoring edge fringing on two neutral targets: per
//! 256 px tile with enough green structure, the shift of the channel's Sobel
//! gradient magnitude against green's by cross-correlation, refined to 1/20 px
//! by an upsampled DFT around the peak (Guizar-Sicairos et al., 2008, the
//! method of scikit-image's `phase_cross_correlation`); then a least-squares
//! fit of the tile shifts, each tile weighted by green's structure tensor so
//! a tile of parallel edges counts only across them, trimmed of outliers. Gradient magnitude rather than
//! intensity, so a hue difference does not read as a shift; the alternatives
//! (intensity matching with a per-tile gain, gradient energy with an
//! iterative solve) gave corrections that fringed more.

use rayon::prelude::*;

/// Tile side, in pixels (a power of two, for the FFT).
const TILE: usize = 256;
const LOG2_TILE: u32 = 8;
/// First sub-pixel refinement factor (the second is 20x finer).
const UPSAMPLE: f64 = 20.0;
/// A tile shift at or beyond this (px) is not a lateral-CA displacement.
const MAX_SHIFT: f64 = 3.0;
/// Fewest tiles a fit may rest on.
pub const MIN_TILES: usize = 12;

/// One channel's measured displacement relative to green, in pixels of the
/// image measured: `d(p) = translation + scale * (p - centre)`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ChannelFit {
    pub translation: (f64, f64),
    /// Scale minus one (the same convention as the profile's `eps`).
    pub scale: f64,
    /// Tiles kept by the trimmed fit, and tiles measured.
    pub kept: usize,
    pub measured: usize,
    /// Root-mean-square residual of the kept tiles (px).
    pub rms: f64,
}

/// Red's and blue's residual displacement.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Residual {
    pub red: ChannelFit,
    pub blue: ChannelFit,
}

/// A tile's centre-relative position, its structure weight, and red's and
/// blue's displacement where measured.
type TileMeasure = ((f64, f64), [f64; 3], Option<(f64, f64)>, Option<(f64, f64)>);
/// Position, structure weight, displacement.
type TileShift = ((f64, f64), [f64; 3], (f64, f64));

/// Measure red's and blue's displacement relative to green on an interleaved
/// RGB image (`width * height * 3`, linear). `None` when too few tiles carry
/// structure for either channel.
pub fn measure(width: usize, height: usize, rgb: &[f32]) -> Option<Residual> {
    assert_eq!(
        rgb.len(),
        width * height * 3,
        "rgb is not width x height x 3"
    );
    if width <= TILE || height <= TILE {
        return None;
    }
    let tiles: Vec<(usize, usize)> = (0..height - TILE)
        .step_by(TILE)
        .flat_map(|y| (0..width - TILE).step_by(TILE).map(move |x| (x, y)))
        .collect();
    // Gate, as in `ca-residual.py`: a tile's mean green gradient must reach
    // half the image's 80th-percentile pixel.
    let threshold = f64::from(0.5 * green_gradient_quantile(width, height, rgb, 0.8));
    let (cx, cy) = (width as f64 * 0.5, height as f64 * 0.5);
    let per_tile: Vec<TileMeasure> = tiles
        .par_iter()
        .filter_map(|&(x, y)| {
            let g = magnitude_tile(width, height, rgb, x, y, 1);
            let mean = g.iter().map(|v| f64::from(*v)).sum::<f64>() / g.len() as f64;
            if mean.is_nan() || mean < threshold || mean <= 0.0 {
                return None;
            }
            let g_freq = fft2(&g);
            let shift = |c: usize| {
                let m = magnitude_tile(width, height, rgb, x, y, c);
                let (sy, sx) = cross_correlation_shift(&g_freq, &fft2(&m));
                // The shift that registers the channel onto green, negated:
                // the channel's displacement relative to green.
                let d = (-sx, -sy);
                (d.0.abs() < MAX_SHIFT && d.1.abs() < MAX_SHIFT).then_some(d)
            };
            let pos = (
                x as f64 + TILE as f64 * 0.5 - cx,
                y as f64 + TILE as f64 * 0.5 - cy,
            );
            Some((pos, structure(width, height, rgb, x, y), shift(0), shift(2)))
        })
        .collect();
    let channel = |pick: fn(&TileMeasure) -> Option<(f64, f64)>| {
        let v: Vec<TileShift> = per_tile
            .iter()
            .filter_map(|t| Some((t.0, t.1, pick(t)?)))
            .collect();
        trimmed_fit(&v)
    };
    Some(Residual {
        red: channel(|t| t.2)?,
        blue: channel(|t| t.3)?,
    })
}

/// Measure on an RGGB mosaic (`width x height`, even dimensions; R at even
/// row and column, G at the two mixed sites, B at odd row and column).
///
/// Each colour is interpolated **only from its own sites** (normalised
/// `[1 2 1]` convolution), so every sample stays where it was taken. A
/// demosaic that borrows green's detail to rebuild red and blue (MHC) pulls
/// their edges toward green's and under-reads the very displacement being
/// measured: on bug-4 a correction measured on the MHC image removed about
/// half of the residual the output then still showed.
pub fn measure_mosaic(width: usize, height: usize, mosaic: &[f32]) -> Option<Residual> {
    assert_eq!(mosaic.len(), width * height, "mosaic is not width x height");
    measure(width, height, &separate_bilinear(width, height, mosaic))
}

/// RGGB colour of the site at `(x, y)`: 0 red, 1 green, 2 blue.
#[inline]
fn site(x: usize, y: usize) -> usize {
    match (y % 2, x % 2) {
        (0, 0) => 0,
        (1, 1) => 2,
        _ => 1,
    }
}

/// Interleaved RGB from an RGGB mosaic, each colour from its own sites only.
fn separate_bilinear(width: usize, height: usize, mosaic: &[f32]) -> Vec<f32> {
    let mut rgb = vec![0.0f32; width * height * 3];
    rgb.par_chunks_mut(width * 3)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                let mut sum = [0.0f32; 3];
                let mut weight = [0.0f32; 3];
                for dy in -1isize..=1 {
                    let yy = y as isize + dy;
                    if yy < 0 || yy >= height as isize {
                        continue;
                    }
                    for dx in -1isize..=1 {
                        let xx = x as isize + dx;
                        if xx < 0 || xx >= width as isize {
                            continue;
                        }
                        let w =
                            [1.0, 2.0, 1.0][(dx + 1) as usize] * [1.0, 2.0, 1.0][(dy + 1) as usize];
                        let (xx, yy) = (xx as usize, yy as usize);
                        let c = site(xx, yy);
                        sum[c] += w * mosaic[yy * width + xx];
                        weight[c] += w;
                    }
                }
                for c in 0..3 {
                    row[x * 3 + c] = if weight[c] > 0.0 {
                        sum[c] / weight[c]
                    } else {
                        0.0
                    };
                }
            }
        });
    rgb
}

/// Sobel gradient magnitude of channel `c` at `(x, y)`, reflecting at the
/// image border (scipy's `sobel` default, which the Python instrument used).
#[inline]
fn gradient(width: usize, height: usize, rgb: &[f32], x: usize, y: usize, c: usize) -> f32 {
    let (gx, gy) = sobel(width, height, rgb, x, y, c);
    (gx * gx + gy * gy).sqrt()
}

/// Sobel gradient components of channel `c` at `(x, y)`, reflecting at the
/// image border.
#[inline]
fn sobel(width: usize, height: usize, rgb: &[f32], x: usize, y: usize, c: usize) -> (f32, f32) {
    let reflect = |v: isize, n: usize| -> usize {
        if v < 0 {
            (-v - 1) as usize
        } else if v as usize >= n {
            2 * n - 1 - v as usize
        } else {
            v as usize
        }
    };
    let at = |dx: isize, dy: isize| {
        let xx = reflect(x as isize + dx, width);
        let yy = reflect(y as isize + dy, height);
        rgb[(yy * width + xx) * 3 + c]
    };
    let gx = (at(1, -1) + 2.0 * at(1, 0) + at(1, 1)) - (at(-1, -1) + 2.0 * at(-1, 0) + at(-1, 1));
    let gy = (at(-1, 1) + 2.0 * at(0, 1) + at(1, 1)) - (at(-1, -1) + 2.0 * at(0, -1) + at(1, -1));
    (gx, gy)
}

/// Green's unit-trace structure tensor over a tile, `[xx, xy, yy]`: how well
/// the tile's edges constrain a shift in each direction. A tile of parallel
/// edges cannot measure a shift along them -- its cross-correlation has a
/// ridge, not a peak, there -- and this weight keeps that component out of
/// the fit.
fn structure(width: usize, height: usize, rgb: &[f32], x0: usize, y0: usize) -> [f64; 3] {
    let (mut xx, mut xy, mut yy) = (0.0f64, 0.0f64, 0.0f64);
    for i in 0..TILE * TILE {
        let (gx, gy) = sobel(width, height, rgb, x0 + i % TILE, y0 + i / TILE, 1);
        let (gx, gy) = (f64::from(gx), f64::from(gy));
        xx += gx * gx;
        xy += gx * gy;
        yy += gy * gy;
    }
    let t = xx + yy;
    if t > 0.0 {
        [xx / t, xy / t, yy / t]
    } else {
        [0.5, 0.0, 0.5]
    }
}

/// A quantile of green's gradient magnitude, sampled on a sparse lattice.
fn green_gradient_quantile(width: usize, height: usize, rgb: &[f32], q: f64) -> f32 {
    let mut v: Vec<f32> = (0..height)
        .step_by(4)
        .flat_map(|y| (0..width).step_by(4).map(move |x| (x, y)))
        .map(|(x, y)| gradient(width, height, rgb, x, y, 1))
        .filter(|g| g.is_finite())
        .collect();
    if v.is_empty() {
        return f32::INFINITY;
    }
    let k = ((v.len() - 1) as f64 * q) as usize;
    *v.select_nth_unstable_by(k, f32::total_cmp).1
}

fn magnitude_tile(
    width: usize,
    height: usize,
    rgb: &[f32],
    x0: usize,
    y0: usize,
    c: usize,
) -> Vec<f32> {
    (0..TILE * TILE)
        .map(|i| gradient(width, height, rgb, x0 + i % TILE, y0 + i / TILE, c))
        .collect()
}

#[derive(Debug, Clone, Copy, Default)]
struct Cx {
    re: f64,
    im: f64,
}

impl Cx {
    #[inline]
    fn mul(self, o: Self) -> Self {
        Self {
            re: self.re * o.re - self.im * o.im,
            im: self.re * o.im + self.im * o.re,
        }
    }
    #[inline]
    fn conj(self) -> Self {
        Self {
            re: self.re,
            im: -self.im,
        }
    }
    #[inline]
    fn norm2(self) -> f64 {
        self.re * self.re + self.im * self.im
    }
    #[inline]
    fn expi(theta: f64) -> Self {
        Self {
            re: theta.cos(),
            im: theta.sin(),
        }
    }
}

/// In-place radix-2 FFT of a `TILE`-long run with stride; `inverse` flips the
/// exponent sign (no 1/n scaling: only argmax positions are used).
fn fft1(data: &mut [Cx], start: usize, stride: usize, inverse: bool) {
    let n = TILE;
    let idx = |i: usize| start + i * stride;
    for i in 0..n {
        let j = ((i as u32).reverse_bits() >> (32 - LOG2_TILE)) as usize;
        if j > i {
            data.swap(idx(i), idx(j));
        }
    }
    let sign = if inverse { 1.0 } else { -1.0 };
    let mut len = 2;
    while len <= n {
        for s in (0..n).step_by(len) {
            for k in 0..len / 2 {
                let w = Cx::expi(sign * std::f64::consts::TAU * k as f64 / len as f64);
                let (a, b) = (idx(s + k), idx(s + k + len / 2));
                let t = w.mul(data[b]);
                let u = data[a];
                data[a] = Cx {
                    re: u.re + t.re,
                    im: u.im + t.im,
                };
                data[b] = Cx {
                    re: u.re - t.re,
                    im: u.im - t.im,
                };
            }
        }
        len <<= 1;
    }
}

fn fft2_in_place(data: &mut [Cx], inverse: bool) {
    for r in 0..TILE {
        fft1(data, r * TILE, 1, inverse);
    }
    for c in 0..TILE {
        fft1(data, c, TILE, inverse);
    }
}

/// Spectrum of a tile after removing its mean and applying a Hann window.
/// Unwindowed, the circular correlation compares wrapped-around content at
/// any non-zero shift and so favours zero: planted shifts read ~10% short
/// (0.25 -> 0.219); windowed, ~5% (0.25 -> 0.234; 400 ppm -> 399).
fn fft2(v: &[f32]) -> Vec<Cx> {
    let mean = v.iter().map(|x| f64::from(*x)).sum::<f64>() / v.len() as f64;
    let hann =
        |i: usize| 0.5 - 0.5 * (std::f64::consts::TAU * (i as f64 + 0.5) / TILE as f64).cos();
    let mut d: Vec<Cx> = v
        .iter()
        .enumerate()
        .map(|(i, x)| Cx {
            re: (f64::from(*x) - mean) * hann(i % TILE) * hann(i / TILE),
            im: 0.0,
        })
        .collect();
    fft2_in_place(&mut d, false);
    d
}

/// numpy's `fftfreq(TILE, d)` at index `k`.
#[inline]
fn fftfreq(k: usize, d: f64) -> f64 {
    let n = TILE;
    let signed = if k < n.div_ceil(2) {
        k as f64
    } else {
        k as f64 - n as f64
    };
    signed / (n as f64 * d)
}

/// The (row, column) shift that registers `moving` onto `reference`, from
/// their spectra: cross-correlation peak, then two upsampled-DFT refinements.
fn cross_correlation_shift(reference: &[Cx], moving: &[Cx]) -> (f64, f64) {
    let n = TILE;
    let product: Vec<Cx> = reference
        .iter()
        .zip(moving)
        .map(|(a, b)| a.mul(b.conj()))
        .collect();
    let mut cc = product.clone();
    fft2_in_place(&mut cc, true);
    let (mut best, mut at) = (-1.0, 0usize);
    for (i, v) in cc.iter().enumerate() {
        let m = v.norm2();
        if m > best {
            best = m;
            at = i;
        }
    }
    let wrap = |k: usize| {
        if k > n / 2 {
            k as f64 - n as f64
        } else {
            k as f64
        }
    };
    let (mut sy, mut sx) = (wrap(at / n), wrap(at % n));
    // Two upsampled-DFT stages of conj(product), each on a `REGION x REGION`
    // grid centred on the current peak: 1/20 px over +-0.75 px, then
    // 1/400 px over +-0.04 px. One stage at 1/20 quantizes a uniform shift
    // (a planted (0.12, 0.07) read (0.10, 0.10)).
    for factor in [UPSAMPLE, UPSAMPLE * 20.0] {
        let (py, px) = refine_peak(&product, sy, sx, factor);
        sy = py;
        sx = px;
    }
    (sy, sx)
}

/// Side of each refinement grid.
const REGION: usize = 30;

/// The cross-correlation peak near `(sy, sx)` on a grid of `1/factor` px.
fn refine_peak(product: &[Cx], sy: f64, sx: f64, factor: f64) -> (f64, f64) {
    let n = TILE;
    let (sy, sx) = (
        (sy * factor).round() / factor,
        (sx * factor).round() / factor,
    );
    let dftshift = (REGION as f64 / 2.0).trunc();
    let (oy, ox) = (dftshift - sy * factor, dftshift - sx * factor);
    let kernel = |offset: f64| -> Vec<Cx> {
        (0..REGION)
            .flat_map(|u| {
                (0..n).map(move |k| {
                    Cx::expi(-std::f64::consts::TAU * (u as f64 - offset) * fftfreq(k, factor))
                })
            })
            .collect()
    };
    let (kx, ky) = (kernel(ox), kernel(oy));
    // Contract the column axis first: `half[y][u]`.
    let mut half = vec![Cx::default(); n * REGION];
    for y in 0..n {
        for u in 0..REGION {
            let mut acc = Cx::default();
            for k in 0..n {
                let t = kx[u * n + k].mul(product[y * n + k].conj());
                acc.re += t.re;
                acc.im += t.im;
            }
            half[y * REGION + u] = acc;
        }
    }
    let (mut best, mut peak) = (-1.0, (0usize, 0usize));
    for v in 0..REGION {
        for u in 0..REGION {
            let mut acc = Cx::default();
            for y in 0..n {
                let t = ky[v * n + y].mul(half[y * REGION + u]);
                acc.re += t.re;
                acc.im += t.im;
            }
            let m = acc.norm2();
            if m > best {
                best = m;
                peak = (v, u);
            }
        }
    }
    (
        sy + (peak.0 as f64 - dftshift) / factor,
        sx + (peak.1 as f64 - dftshift) / factor,
    )
}

/// Structure-weighted least squares of `d = t + scale * pos`, iteratively
/// trimmed: tiles whose weighted residual exceeds `max(3 x MAD, 0.15 px)` are
/// dropped (the rule of `ca-raw-shift.py`).
fn trimmed_fit(tiles: &[TileShift]) -> Option<ChannelFit> {
    if tiles.len() < MIN_TILES {
        return None;
    }
    // Positions in units of 1000 px keep the normal equations well scaled.
    const U: f64 = 1000.0;
    let mut keep = vec![true; tiles.len()];
    let mut theta = [0.0f64; 3];
    let mut rr = vec![0.0f64; tiles.len()];
    for _ in 0..5 {
        let mut n = [[0.0f64; 3]; 3];
        let mut rhs = [0.0f64; 3];
        for ((pos, w, d), _) in tiles.iter().zip(&keep).filter(|(_, k)| **k) {
            let (px, py) = (pos.0 / U, pos.1 / U);
            let rows = [[1.0, 0.0, px], [0.0, 1.0, py]];
            let [wxx, wxy, wyy] = *w;
            // Accumulate J^T W J and J^T W d with J = rows.
            for i in 0..3 {
                let wj = (
                    wxx * rows[0][i] + wxy * rows[1][i],
                    wxy * rows[0][i] + wyy * rows[1][i],
                );
                for j in 0..3 {
                    n[i][j] += rows[0][j] * wj.0 + rows[1][j] * wj.1;
                }
                rhs[i] += wj.0 * d.0 + wj.1 * d.1;
            }
        }
        // A direction no tile constrains resolves to zero, not to a
        // singular solve.
        let ridge = 1e-6 * (n[0][0] + n[1][1] + n[2][2]);
        for (i, row) in n.iter_mut().enumerate() {
            row[i] += ridge;
        }
        theta = solve3(n, rhs)?;
        for (r, (pos, w, d)) in rr.iter_mut().zip(tiles) {
            let (px, py) = (pos.0 / U, pos.1 / U);
            let (rx, ry) = (
                d.0 - (theta[0] + theta[2] * px),
                d.1 - (theta[1] + theta[2] * py),
            );
            let [wxx, wxy, wyy] = *w;
            // Unit-trace W, doubled: an isotropic tile's residual is its
            // Euclidean length; an edge tile's along-edge error counts nothing.
            *r = (2.0 * (rx * (wxx * rx + wxy * ry) + ry * (wxy * rx + wyy * ry)))
                .max(0.0)
                .sqrt();
        }
        let mut kept: Vec<f64> = rr
            .iter()
            .zip(&keep)
            .filter(|(_, k)| **k)
            .map(|(r, _)| *r)
            .collect();
        kept.sort_by(f64::total_cmp);
        let mad = 1.4826 * kept[kept.len() / 2];
        let cut = (3.0 * mad).max(0.15);
        for (k, r) in keep.iter_mut().zip(&rr) {
            *k = *r < cut;
        }
        if keep.iter().filter(|k| **k).count() < MIN_TILES {
            return None;
        }
    }
    let kept: Vec<f64> = rr
        .iter()
        .zip(&keep)
        .filter(|(_, k)| **k)
        .map(|(r, _)| *r)
        .collect();
    Some(ChannelFit {
        translation: (theta[0], theta[1]),
        scale: theta[2] / U,
        kept: kept.len(),
        measured: tiles.len(),
        rms: (kept.iter().map(|r| r * r).sum::<f64>() / kept.len() as f64).sqrt(),
    })
}

/// Solve a symmetric 3x3 system by Cramer's rule; `None` when singular.
fn solve3(a: [[f64; 3]; 3], b: [f64; 3]) -> Option<[f64; 3]> {
    let det = |m: [[f64; 3]; 3]| {
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    };
    let d = det(a);
    if d.is_nan() || d.abs() <= 1e-12 {
        return None;
    }
    let mut out = [0.0; 3];
    for (i, o) in out.iter_mut().enumerate() {
        let mut m = a;
        for r in 0..3 {
            m[r][i] = b[r];
        }
        *o = det(m) / d;
    }
    Some(out)
}

#[cfg(test)]
#[path = "ca-refine-tests.rs"]
mod tests;
