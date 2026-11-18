//! Optical restoration of a finished stack: one linear filter per channel that
//! takes the measured system transfer to a ringing-free target, held back by
//! the measured noise (`STREHL_OPTICAL_RESTORE`, wired in
//! `strehl-cli/src/merge_cmd/optical-restore.rs`).
//!
//! Not [`crate::restore`], which undoes the gather's own interpolation kernel.
//! This one models the lens: circular-aperture diffraction at a cutoff fitted
//! to the stack's own signal spectrum, the photosite aperture, and the
//! transfer of the merge's blend measured against single frames. Nothing else
//! is modelled; other blur enters only through the fitted cutoff (see the
//! limit below).
//!
//! Ported from the A7CR full-potential prototype
//! (`experiments/a7cr-full-potential-2026-11-14/restore.py`). Every input is
//! measured on the stack, on in-focus tiles:
//!
//! * `S(f)`, `N(f)`: the cross-spectrum of two independent half-stacks (odd
//!   and even frames) is signal, their mean auto-spectrum minus it is noise
//!   ([`SpectrumSum`]). The full stack's noise is half a half's.
//! * the cutoffs: one aperture for all three channels ([`fit_cutoff_joint`]):
//!   `A f^-alpha [MTF_diff(f / fc) sinc(f)]^2` fitted to the cube root of the
//!   reference signal over 0.20-0.49 cycles/px with the channels' cutoffs tied
//!   by nominal wavelength (red 600, green 535, blue 465 nm). Fitted per
//!   channel ([`fit_cutoff`], the prototype's estimator) they came out
//!   mis-ordered on the A7CR scarab (red 0.572 = green 0.572, blue 0.804);
//!   jointly, green 0.616, matching the prototype's N_eff 11.1-11.8. A
//!   single-shot frame shows no roll-off (its demosaic structure fills the
//!   corners) and the fit runs to its ceiling: the caller must refuse.
//! * the blend transfer `M(f) = sqrt(S_out / S_ref)` ([`blend_transfer`]),
//!   `S_ref` from two single frames at the tile's focus: what the merge's
//!   blend of neighbouring planes cost against the in-focus image, from the
//!   bins where the reference is reliable, made non-increasing.
//!
//! The filter ([`gain_grid`]) is `G = (T / H) S / (S + N)` with
//! `H = MTF_diff(f / fc) sinc(fx) sinc(fy) M(f)`, `S` the fitted signal model,
//! `T` a Gaussian of `sigma_t` px (a positive PSF: no ringing of its own),
//! capped at `max_gain`, tapered to zero at the cutoff. It is applied as a
//! windowed spatial kernel ([`kernel`], [`convolve`]) that reports what
//! fraction of the designed gain it delivers.
//!
//! Limit: blur the model omits (residual misregistration, the gather's
//! interpolation, defocus) steepens the measured roll-off and biases the
//! fitted cutoff low, which over-restores; on planted spectra with 0.4-0.7 px
//! of extra Gaussian blur the joint fit read up to 0.15 cycles/px low.
use rayon::prelude::*;

/// Edge of a spectrum tile, px.
pub const TILE: usize = 256;
/// Radial bins of [`BIN_WIDTH`] cycles/px from zero, covering the corners.
pub const BINS: usize = 72;
pub const BIN_WIDTH: f64 = 0.01;

/// Bin centres, cycles/px.
pub fn centres() -> Vec<f64> {
    (0..BINS).map(|i| (i as f64 + 0.5) * BIN_WIDTH).collect()
}

#[derive(Clone, Copy, Default, Debug)]
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
}

/// Radix-2 complex FFT of a power-of-two length.
struct Fft1 {
    n: usize,
    rev: Vec<usize>,
    twiddle: Vec<C>,
}

impl Fft1 {
    fn new(n: usize) -> Self {
        assert!(n.is_power_of_two() && n >= 2);
        let bits = n.trailing_zeros();
        Self {
            n,
            rev: (0..n)
                .map(|i| i.reverse_bits() >> (usize::BITS - bits))
                .collect(),
            twiddle: (0..n / 2)
                .map(|k| {
                    let a = -std::f64::consts::TAU * k as f64 / n as f64;
                    C {
                        re: a.cos(),
                        im: a.sin(),
                    }
                })
                .collect(),
        }
    }

    fn forward(&self, d: &mut [C]) {
        let n = self.n;
        for i in 0..n {
            let j = self.rev[i];
            if i < j {
                d.swap(i, j);
            }
        }
        let mut len = 2;
        while len <= n {
            let step = n / len;
            for s in (0..n).step_by(len) {
                for k in 0..len / 2 {
                    let w = self.twiddle[k * step];
                    let u = d[s + k];
                    let v = d[s + k + len / 2].mul(w);
                    d[s + k] = C {
                        re: u.re + v.re,
                        im: u.im + v.im,
                    };
                    d[s + k + len / 2] = C {
                        re: u.re - v.re,
                        im: u.im - v.im,
                    };
                }
            }
            len <<= 1;
        }
    }
}

/// Forward 2-D FFT of an `n x n` array in place.
fn fft2(f: &Fft1, d: &mut [C]) {
    let n = f.n;
    for row in d.chunks_mut(n) {
        f.forward(row);
    }
    let mut col = vec![C::default(); n];
    for x in 0..n {
        for (y, v) in col.iter_mut().enumerate() {
            *v = d[y * n + x];
        }
        f.forward(&mut col);
        for (y, v) in col.iter().enumerate() {
            d[y * n + x] = *v;
        }
    }
}

/// `fftfreq(n)[i]`.
fn freq(i: usize, n: usize) -> f64 {
    if i < n.div_ceil(2) {
        i as f64 / n as f64
    } else {
        (i as f64 - n as f64) / n as f64
    }
}

/// Signal and noise spectra summed over tile pairs, radially binned.
pub struct SpectrumSum {
    fft: Fft1,
    win: Vec<f64>,
    bin: Vec<usize>,
    signal: Vec<f64>,
    noise: Vec<f64>,
    tiles: usize,
}

/// One pair's contribution to a [`SpectrumSum`], per 2-D frequency: the
/// cross-spectrum and the mean auto-spectrum minus it.
pub struct PairTerms {
    signal: Vec<f64>,
    noise: Vec<f64>,
}

/// Radial signal and noise spectra, per bin; `count` is the number of 2-D
/// frequencies in each bin.
#[derive(Clone, Debug)]
pub struct Spectrum {
    pub signal: Vec<f64>,
    pub noise: Vec<f64>,
    pub count: Vec<f64>,
    pub tiles: usize,
}

impl Default for SpectrumSum {
    fn default() -> Self {
        Self::new()
    }
}

impl SpectrumSum {
    pub fn new() -> Self {
        let t = TILE;
        let hann: Vec<f64> = (0..t)
            .map(|i| 0.5 - 0.5 * (std::f64::consts::TAU * i as f64 / t as f64).cos())
            .collect();
        let win = (0..t * t).map(|i| hann[i / t] * hann[i % t]).collect();
        let bin = (0..t * t)
            .map(|i| {
                let (fy, fx) = (freq(i / t, t), freq(i % t, t));
                (((fx * fx + fy * fy).sqrt() / BIN_WIDTH) as usize).min(BINS)
            })
            .collect();
        Self {
            fft: Fft1::new(t),
            win,
            bin,
            signal: vec![0.0; t * t],
            noise: vec![0.0; t * t],
            tiles: 0,
        }
    }

    /// One pair of [`TILE`]-square images with independent noise and a
    /// common signal: the cross-spectrum is the signal, the mean
    /// auto-spectrum minus it the noise (per image), both normalised to a
    /// power per pixel.
    pub fn add_pair(&mut self, a: &[f32], b: &[f32]) {
        let terms = self.pair_terms(a, b);
        self.add_terms(&terms);
    }

    /// What [`Self::add_pair`] adds for one pair, computed without touching
    /// the sums: pure, so pairs can be transformed in parallel and then
    /// added in their order with [`Self::add_terms`] (the same additions, in
    /// the same order, as calling `add_pair` on each).
    pub fn pair_terms(&self, a: &[f32], b: &[f32]) -> PairTerms {
        let t = TILE;
        assert!(a.len() == t * t && b.len() == t * t);
        let prep = |v: &[f32]| -> Vec<C> {
            let mean = v.iter().map(|x| f64::from(*x)).sum::<f64>() / (t * t) as f64;
            let mut c: Vec<C> = v
                .iter()
                .zip(&self.win)
                .map(|(x, w)| C {
                    re: (f64::from(*x) - mean) * w,
                    im: 0.0,
                })
                .collect();
            fft2(&self.fft, &mut c);
            c
        };
        let (fa, fb) = (prep(a), prep(b));
        // Power per frequency: white noise of variance v reads v.
        let norm = self.win.iter().map(|w| w * w).sum::<f64>();
        let mut signal = vec![0f64; t * t];
        let mut noise = vec![0f64; t * t];
        for i in 0..t * t {
            let (x, y) = (fa[i], fb[i]);
            let cross = (x.re * y.re + x.im * y.im) / norm;
            let auto = (x.re * x.re + x.im * x.im + y.re * y.re + y.im * y.im) / (2.0 * norm);
            signal[i] = cross;
            noise[i] = auto - cross;
        }
        PairTerms { signal, noise }
    }

    /// Add one pair's [`Self::pair_terms`] and count its tile.
    pub fn add_terms(&mut self, terms: &PairTerms) {
        for (s, v) in self.signal.iter_mut().zip(&terms.signal) {
            *s += v;
        }
        for (n, v) in self.noise.iter_mut().zip(&terms.noise) {
            *n += v;
        }
        self.tiles += 1;
    }

    pub fn radial(&self) -> Spectrum {
        let mut s = vec![0.0; BINS];
        let mut n = vec![0.0; BINS];
        let mut c = vec![0.0; BINS];
        let k = self.tiles.max(1) as f64;
        for i in 0..TILE * TILE {
            let b = self.bin[i];
            if b < BINS {
                s[b] += self.signal[i] / k;
                n[b] += self.noise[i] / k;
                c[b] += 1.0;
            }
        }
        for b in 0..BINS {
            if c[b] > 0.0 {
                s[b] /= c[b];
                n[b] /= c[b];
            }
        }
        Spectrum {
            signal: s,
            noise: n,
            count: c,
            tiles: self.tiles,
        }
    }
}

/// Circular-aperture diffraction MTF at `s = f / fc`.
pub fn mtf_diffraction(s: f64) -> f64 {
    let s = s.clamp(0.0, 1.0);
    (2.0 / std::f64::consts::PI) * (s.acos() - s * (1.0 - s * s).sqrt())
}

/// `sin(pi x) / (pi x)`.
pub fn sinc(x: f64) -> f64 {
    if x.abs() < 1e-12 {
        1.0
    } else {
        let p = std::f64::consts::PI * x;
        p.sin() / p
    }
}

/// The diffraction cutoff fitted to a signal spectrum: the model
/// `A f^-alpha [MTF_diff(f / fc) sinc(f)]^2`, compared in the cube-root domain
/// (which handles the bins where the model is zero) over 0.20-0.49 cycles/px,
/// below the axis Nyquist so nothing folded is fitted. Grid over `fc` in
/// 0.40-0.90 and `alpha` in 0.4-3.2, `A` solved per point. Returns
/// `(fc, alpha, rms residual)`.
pub fn fit_cutoff(centres: &[f64], signal: &[f64]) -> (f64, f64, f64) {
    let fit: Vec<usize> = (0..centres.len())
        .filter(|&i| centres[i] > 0.20 && centres[i] < 0.49)
        .collect();
    let cube: Vec<f64> = fit.iter().map(|&i| signal[i].max(0.0).cbrt()).collect();
    let mut best = (f64::INFINITY, 0.0, 0.0);
    for a in 0..=125 {
        let fc = 0.40 + 0.004 * f64::from(a);
        let base: Vec<f64> = fit
            .iter()
            .map(|&i| (mtf_diffraction(centres[i] / fc) * sinc(centres[i])).powi(2))
            .collect();
        for b in 0..=56 {
            let alpha = 0.4 + 0.05 * f64::from(b);
            let m: Vec<f64> = fit
                .iter()
                .zip(&base)
                .map(|(&i, base)| (centres[i].powf(-alpha) * base).cbrt())
                .collect();
            let mm: f64 = m.iter().map(|v| v * v).sum::<f64>().max(1e-30);
            let k = cube.iter().zip(&m).map(|(c, m)| c * m).sum::<f64>() / mm;
            let res = (cube
                .iter()
                .zip(&m)
                .map(|(c, m)| (c - k * m).powi(2))
                .sum::<f64>()
                / fit.len() as f64)
                .sqrt();
            if res < best.0 {
                best = (res, fc, alpha);
            }
        }
    }
    (best.1, best.2, best.0)
}

/// Nominal channel centroid wavelengths R, G, B, um. Not measured: they set
/// only the RATIO of the channels' cutoffs in [`fit_cutoff_joint`].
pub const WAVELENGTH_UM: [f64; 3] = [0.600, 0.535, 0.465];

/// One aperture for all three channels: diffraction cutoffs scale as
/// 1 / wavelength, so a single green cutoff `fc_g` fixes all three
/// (`fc_c = fc_g * 535 / lambda_c`). The model of [`fit_cutoff`] is fitted to
/// each channel's cube-root signal over 0.20-0.49 cycles/px with its own
/// object slope and amplitude; `fc_g` (0.40-0.90) minimises the sum of the
/// channels' residuals, each relative to its own signal. Returns
/// `(fc_g, summed relative residual)`. The single parameter cannot come out
/// mis-ordered, and uses all three channels' evidence for it.
pub fn fit_cutoff_joint(centres: &[f64], signals: [&[f64]; 3]) -> (f64, f64) {
    let fit: Vec<usize> = (0..centres.len())
        .filter(|&i| centres[i] > 0.20 && centres[i] < 0.49)
        .collect();
    let cubes: Vec<Vec<f64>> = signals
        .iter()
        .map(|s| fit.iter().map(|&i| s[i].max(0.0).cbrt()).collect())
        .collect();
    let mut best = (f64::INFINITY, 0.0);
    for a in 0..=125 {
        let fg = 0.40 + 0.004 * f64::from(a);
        let mut total = 0.0;
        for (c, cube) in cubes.iter().enumerate() {
            let fc = fg * WAVELENGTH_UM[1] / WAVELENGTH_UM[c];
            let base: Vec<f64> = fit
                .iter()
                .map(|&i| (mtf_diffraction(centres[i] / fc) * sinc(centres[i])).powi(2))
                .collect();
            let power: f64 = cube.iter().map(|v| v * v).sum::<f64>().max(1e-300);
            let mut channel = f64::INFINITY;
            for b in 0..=40 {
                let alpha = 0.1 * f64::from(b);
                let m: Vec<f64> = fit
                    .iter()
                    .zip(&base)
                    .map(|(&i, base)| (centres[i].powf(-alpha) * base).cbrt())
                    .collect();
                let mm: f64 = m.iter().map(|v| v * v).sum::<f64>().max(1e-30);
                let k = cube.iter().zip(&m).map(|(c, m)| c * m).sum::<f64>() / mm;
                let r = cube
                    .iter()
                    .zip(&m)
                    .map(|(c, m)| (c - k * m).powi(2))
                    .sum::<f64>()
                    / power;
                channel = channel.min(r);
            }
            total += channel;
        }
        if total < best.0 {
            best = (total, fg);
        }
    }
    (best.1, best.0)
}

/// Least squares polynomial of `degree`, weighted; coefficients lowest first.
fn polyfit(x: &[f64], y: &[f64], w: &[f64], degree: usize) -> Option<Vec<f64>> {
    let m = degree + 1;
    let mut a = vec![0.0; m * m];
    let mut b = vec![0.0; m];
    for ((x, y), w) in x.iter().zip(y).zip(w) {
        let w2 = w * w;
        let p: Vec<f64> = (0..m).map(|k| x.powi(k as i32)).collect();
        for r in 0..m {
            b[r] += w2 * p[r] * y;
            for c in 0..m {
                a[r * m + c] += w2 * p[r] * p[c];
            }
        }
    }
    // Gaussian elimination with partial pivoting.
    for col in 0..m {
        let piv =
            (col..m).max_by(|&i, &j| a[i * m + col].abs().total_cmp(&a[j * m + col].abs()))?;
        if a[piv * m + col].abs() < 1e-300 {
            return None;
        }
        if piv != col {
            for c in 0..m {
                a.swap(piv * m + c, col * m + c);
            }
            b.swap(piv, col);
        }
        for r in col + 1..m {
            let f = a[r * m + col] / a[col * m + col];
            for c in col..m {
                a[r * m + c] -= f * a[col * m + c];
            }
            b[r] -= f * b[col];
        }
    }
    let mut out = vec![0.0; m];
    for r in (0..m).rev() {
        let s: f64 = (r + 1..m).map(|c| a[r * m + c] * out[c]).sum();
        out[r] = (b[r] - s) / a[r * m + r];
    }
    out.iter().all(|v| v.is_finite()).then_some(out)
}

fn polyval(c: &[f64], x: f64) -> f64 {
    c.iter().rev().fold(0.0, |acc, k| acc * x + k)
}

/// The model-free cutoff: where the cube root of the signal, linear in `f`
/// near the cutoff, reaches zero (fitted over 0.75-0.97 of `fc`, below 0.49).
pub fn cube_root_cutoff(centres: &[f64], signal: &[f64], fc: f64) -> Option<f64> {
    let idx: Vec<usize> = (0..centres.len())
        .filter(|&i| {
            centres[i] > 0.75 * fc && centres[i] < (0.97 * fc).min(0.49) && signal[i] > 0.0
        })
        .collect();
    if idx.len() < 4 {
        return None;
    }
    let x: Vec<f64> = idx.iter().map(|&i| centres[i]).collect();
    let y: Vec<f64> = idx.iter().map(|&i| signal[i].cbrt()).collect();
    let k = polyfit(&x, &y, &vec![1.0; x.len()], 1)?;
    (k[1] < 0.0).then(|| -k[0] / k[1])
}

/// Reference signal-to-noise below which a bin does not inform the blend
/// transfer.
pub const MIN_REFERENCE_SNR: f64 = 2.0;

/// The blend's transfer against single frames, per bin: a smooth (weighted
/// cubic) fit of `sqrt(S_out / S_ref)` over the bins in 0.02-0.47 cycles/px
/// where the reference's own signal-to-noise is at least
/// [`MIN_REFERENCE_SNR`], held constant past the last such bin, made
/// non-increasing with frequency, and clipped to 0.3-1.15. All ones when it
/// cannot be fitted (fewer than eight such bins).
///
/// Why the cut and the monotone constraint: the reference is two adjacent
/// frames, which do not overlay perfectly at the finest scale, so their
/// common signal undercounts the in-focus image where it is weak. Measured
/// on the A7CR scarab four-shot run, the raw ratio rises from 0.84-0.89 to
/// 1.2-1.3 exactly where the reference's signal-to-noise falls through one;
/// a cubic through that upturn put a narrow bump into the filter. A blend of
/// frames can only lose amplitude toward fine detail.
pub fn blend_transfer(centres: &[f64], out: &Spectrum, reference: &Spectrum) -> Vec<f64> {
    let ok: Vec<usize> = (0..centres.len())
        .filter(|&i| {
            out.signal[i] > 0.0
                && reference.signal[i] > 0.0
                && reference.signal[i] >= MIN_REFERENCE_SNR * reference.noise[i].max(0.0)
                && centres[i] > 0.02
                && centres[i] < 0.47
        })
        .collect();
    if ok.len() < 8 {
        return vec![1.0; centres.len()];
    }
    let hi = centres[*ok.last().expect("non-empty")];
    let x: Vec<f64> = ok.iter().map(|&i| centres[i]).collect();
    let y: Vec<f64> = ok
        .iter()
        .map(|&i| (out.signal[i] / reference.signal[i]).sqrt())
        .collect();
    let w: Vec<f64> = ok.iter().map(|&i| out.count[i].sqrt()).collect();
    let Some(k) = polyfit(&x, &y, &w, 3) else {
        return vec![1.0; centres.len()];
    };
    let mut running = f64::INFINITY;
    centres
        .iter()
        .map(|&c| {
            running = running.min(polyval(&k, c.clamp(0.02, hi)));
            running.clamp(0.3, 1.15)
        })
        .collect()
}

/// One channel's measured system.
#[derive(Clone, Debug)]
pub struct ChannelModel {
    /// Diffraction cutoff, cycles/px.
    pub cutoff: f64,
    /// Blend transfer per bin.
    pub transfer: Vec<f64>,
    /// Signal model `exp(log_a) f^-alpha H^2`.
    pub log_a: f64,
    pub alpha: f64,
    /// The finished stack's noise per bin.
    pub noise: Vec<f64>,
    /// The gather kernel's phase-averaged response along one axis, per bin
    /// ([`gather_table`]), when the model includes it
    /// (`STREHL_OPTICAL_RESTORE_GATHER`); `None` leaves it out.
    pub gather: Option<Vec<f64>>,
}

/// The gather kernel's phase-averaged response along one axis at each bin
/// centre, in cycles per output pixel. The four-shot gather resamples
/// full-resolution channel rows, so a cycle per output pixel is a cycle per
/// source sample of the kernel.
pub fn gather_table(resampler: crate::align::Resampler) -> Vec<f64> {
    centres()
        .iter()
        .map(|&f| crate::restore::gather_mtf(resampler, f))
        .collect()
}

/// The mean over an annulus of radius `f` of the 2-D gather response
/// squared, `(g(fx) g(fy))^2`: what a radially binned power spectrum of a
/// gathered image carries of it.
pub fn gather_annulus_power(g: &[f64], f: f64) -> f64 {
    const ANGLES: usize = 32;
    (0..ANGLES)
        .map(|k| {
            let t = (k as f64 + 0.5) / ANGLES as f64 * std::f64::consts::FRAC_PI_2;
            (radial_at(g, f * t.cos()) * radial_at(g, f * t.sin())).powi(2)
        })
        .sum::<f64>()
        / ANGLES as f64
}

/// A radial per-bin profile sampled on an `n x n` frequency grid
/// (`fftfreq` order), for [`kernel`].
pub fn radial_grid(profile: &[f64], n: usize) -> Vec<f64> {
    (0..n * n)
        .map(|i| {
            let (fx, fy) = (freq(i % n, n), freq(i / n, n));
            radial_at(profile, (fx * fx + fy * fy).sqrt())
        })
        .collect()
}

impl ChannelModel {
    /// The object model `exp(log_a) f^-alpha`, fitted to `signal / H^2` over
    /// 0.03-0.47 cycles/px.
    pub fn new(
        centres: &[f64],
        signal: &[f64],
        noise: Vec<f64>,
        cutoff: f64,
        transfer: Vec<f64>,
    ) -> Option<Self> {
        Self::new_with_gather(centres, signal, noise, cutoff, transfer, None)
    }

    /// [`Self::new`] with the gather kernel in the system transfer.
    pub fn new_with_gather(
        centres: &[f64],
        signal: &[f64],
        noise: Vec<f64>,
        cutoff: f64,
        transfer: Vec<f64>,
        gather: Option<Vec<f64>>,
    ) -> Option<Self> {
        let h = |i: usize| {
            let base = mtf_diffraction(centres[i] / cutoff) * sinc(centres[i]) * transfer[i];
            match &gather {
                None => base,
                Some(g) => base * gather_annulus_power(g, centres[i]).sqrt(),
            }
        };
        let good: Vec<usize> = (0..centres.len())
            .filter(|&i| centres[i] > 0.03 && centres[i] < 0.47 && signal[i] > 0.0 && h(i) > 1e-3)
            .collect();
        let x: Vec<f64> = good.iter().map(|&i| centres[i].ln()).collect();
        let y: Vec<f64> = good
            .iter()
            .map(|&i| (signal[i] / h(i).powi(2)).ln())
            .collect();
        let k = polyfit(&x, &y, &vec![1.0; x.len()], 1).filter(|_| good.len() >= 4)?;
        Some(Self {
            cutoff,
            transfer,
            log_a: k[0],
            alpha: -k[1],
            noise,
            gather,
        })
    }
}

/// Linear interpolation of a per-bin profile at radius `f`, held at the ends.
fn radial_at(v: &[f64], f: f64) -> f64 {
    let x = f / BIN_WIDTH - 0.5;
    if x <= 0.0 {
        return v[0];
    }
    let i = x as usize;
    if i + 1 >= v.len() {
        return v[v.len() - 1];
    }
    let a = x - i as f64;
    v[i] * (1.0 - a) + v[i + 1] * a
}

/// The system transfer `H` at `(fx, fy)`.
pub fn system_mtf(m: &ChannelModel, fx: f64, fy: f64) -> f64 {
    let f = (fx * fx + fy * fy).sqrt();
    let base = mtf_diffraction(f / m.cutoff) * sinc(fx) * sinc(fy) * radial_at(&m.transfer, f);
    match &m.gather {
        None => base,
        Some(g) => base * radial_at(g, fx.abs()) * radial_at(g, fy.abs()),
    }
}

/// The Gaussian target `T` of `sigma_t` px at radius `f`.
pub fn target(sigma_t: f64, f: f64) -> f64 {
    (-2.0 * std::f64::consts::PI.powi(2) * sigma_t * sigma_t * f * f).exp()
}

/// Fraction of the cutoff from which the gain is tapered to zero at the
/// cutoff (raised cosine). Near the cutoff `T / H` is ill-conditioned and the
/// target there is a few percent; without the taper the gain falls from its
/// cap to zero in one step, and no compact kernel can follow that.
pub const TAPER_FROM: f64 = 0.85;

/// The filter's gain at `(fx, fy)`.
pub fn gain_at(m: &ChannelModel, fx: f64, fy: f64, sigma_t: f64, max_gain: f64) -> f64 {
    let f = (fx * fx + fy * fy).sqrt();
    if f == 0.0 {
        return 1.0;
    }
    let h = system_mtf(m, fx, fy);
    if h <= 1e-4 || f >= m.cutoff {
        return 0.0;
    }
    let s = m.log_a.exp() * f.max(1e-3).powf(-m.alpha) * h * h;
    let n = radial_at(&m.noise, f).max(1e-30);
    let taper = if f <= TAPER_FROM * m.cutoff {
        1.0
    } else {
        let u = (f - TAPER_FROM * m.cutoff) / ((1.0 - TAPER_FROM) * m.cutoff);
        0.5 * (1.0 + (std::f64::consts::PI * u).cos())
    };
    (target(sigma_t, f) / h * s / (s + n)).min(max_gain) * taper
}

/// The filter sampled on an `n x n` frequency grid (`fftfreq` order).
pub fn gain_grid(m: &ChannelModel, n: usize, sigma_t: f64, max_gain: f64) -> Vec<f64> {
    (0..n * n)
        .map(|i| gain_at(m, freq(i % n, n), freq(i / n, n), sigma_t, max_gain))
        .collect()
}

/// A square spatial kernel of radius `r`, row-major `(2r + 1)^2`.
#[derive(Clone, Debug)]
pub struct Kernel {
    pub radius: usize,
    pub taps: Vec<f32>,
    /// Largest absolute difference between the kernel's response and the
    /// design inside the working band, over the design's peak gain (at least
    /// one).
    pub band_error: f64,
    /// The same over every frequency: concentrated where the design is
    /// steepest (its taper below the cutoff), which the window smooths.
    pub max_error: f64,
    /// Mean delivered gain over mean designed gain inside the working band:
    /// below one, the kernel restores less than designed.
    pub delivered: f64,
}

/// The kernel whose response approximates `gain` (an `n x n` grid, `n` a
/// power of two, real and even): the design's inverse transform times a
/// radial Hann window of radius `r`, the smallest `r` in 4..=`max_radius`
/// whose response stays within `tolerance` times the design's peak gain (at
/// least one) of the design over radial frequencies `band`, else
/// `max_radius`. The taps are renormalised to sum to one (the design's DC
/// gain).
///
/// A window, not a plain truncation: cutting the inverse transform off
/// square spreads ripple over every frequency (ringing; the error falls only
/// as `1 / r`), while a window turns the error into a smoothing of the
/// design's steepest part. Measured on a cutoff-0.57 design: rectangular
/// truncation at radius 24 misses by 16 % of the peak gain, the window by
/// 2 % inside 0.15-0.45 cycles/px. The smoothing lowers the design's peak, so
/// the windowed design is pre-corrected three times (`d += g - response`);
/// on the A7CR scarab's measured designs that lifts the delivered fraction in
/// 0.25-0.40 cycles/px from 0.92-0.96 to 0.93-0.98, the remainder an
/// under-restoration.
pub fn kernel(
    gain: &[f64],
    n: usize,
    max_radius: usize,
    tolerance: f64,
    band: (f64, f64),
) -> Kernel {
    assert_eq!(gain.len(), n * n);
    assert!(2 * max_radius < n);
    // The inverse of a real even spectrum is its forward transform / n^2.
    let f = Fft1::new(n);
    let peak = gain.iter().copied().fold(1.0, f64::max);
    let in_band: Vec<bool> = (0..n * n)
        .map(|i| {
            let fr = (freq(i % n, n).powi(2) + freq(i / n, n).powi(2)).sqrt();
            fr >= band.0 && fr <= band.1
        })
        .collect();
    // Windowed taps of radius `r` for design `d`, and their response.
    let windowed = |d: &[f64], r: usize| -> (Vec<f64>, Vec<f64>) {
        let mut c: Vec<C> = d.iter().map(|g| C { re: *g, im: 0.0 }).collect();
        fft2(&f, &mut c);
        let full: Vec<f64> = c.iter().map(|v| v.re / (n * n) as f64).collect();
        let at = |dx: isize, dy: isize| {
            full[(dy.rem_euclid(n as isize) as usize) * n + dx.rem_euclid(n as isize) as usize]
        };
        let ri = r as isize;
        let mut taps: Vec<f64> = (-ri..=ri)
            .flat_map(|dy| (-ri..=ri).map(move |dx| (dx, dy)))
            .map(|(dx, dy)| {
                let rho = ((dx * dx + dy * dy) as f64).sqrt();
                let w = if rho <= r as f64 {
                    0.5 * (1.0 + (std::f64::consts::PI * rho / (r as f64 + 1.0)).cos())
                } else {
                    0.0
                };
                at(dx, dy) * w
            })
            .collect();
        let sum: f64 = taps.iter().sum();
        for t in &mut taps {
            *t /= sum;
        }
        let mut resp = vec![C::default(); n * n];
        for (k, t) in taps.iter().enumerate() {
            let (dx, dy) = (
                (k % (2 * r + 1)) as isize - ri,
                (k / (2 * r + 1)) as isize - ri,
            );
            resp[(dy.rem_euclid(n as isize) as usize) * n + dx.rem_euclid(n as isize) as usize] =
                C { re: *t, im: 0.0 };
        }
        fft2(&f, &mut resp);
        (taps, resp.iter().map(|v| v.re).collect())
    };
    let mut chosen = None;
    for r in 4..=max_radius {
        let mut design = gain.to_vec();
        let (mut taps, mut resp) = windowed(&design, r);
        for _ in 0..3 {
            for i in 0..n * n {
                design[i] += gain[i] - resp[i];
            }
            (taps, resp) = windowed(&design, r);
        }
        let (mut band_error, mut max_error) = (0.0f64, 0.0f64);
        let (mut got, mut want) = (0.0f64, 0.0f64);
        for i in 0..n * n {
            let e = (resp[i] - gain[i]).abs() / peak;
            max_error = max_error.max(e);
            if in_band[i] {
                band_error = band_error.max(e);
                got += resp[i];
                want += gain[i];
            }
        }
        if band_error <= tolerance || r == max_radius {
            chosen = Some(Kernel {
                radius: r,
                taps: taps.iter().map(|t| *t as f32).collect(),
                band_error,
                max_error,
                delivered: if want > 0.0 { got / want } else { 1.0 },
            });
            break;
        }
    }
    chosen.expect("max_radius >= 4")
}

/// `src` (`w x h`) convolved with `k`, mirror-reflected at the borders.
///
/// In tiles of [`CONV_ROWS`] x [`CONV_COLS`] output pixels: each tile's
/// reflected source neighbourhood is copied once into a per-thread buffer
/// (about 220 KB at radius 32, in a core's own cache), and the taps run per
/// block of [`CONV_BLOCK`] pixels. Every output pixel still sums `t * v`
/// from zero over the live taps in `(ky, kx)` order, a multiply then an add
/// each, so the result is bit-identical to sweeping whole rows once per tap
/// (the test keeps that form as the reference). MEASURED on a 9504 x 6336
/// channel at radius 32 (3,209 live taps): 0.48 s against 0.92 s.
pub fn convolve(src: &[f32], w: usize, h: usize, k: &Kernel) -> Vec<f32> {
    assert_eq!(src.len(), w * h);
    let r = k.radius;
    let side = 2 * r + 1;
    assert!(w > r && h > r, "image smaller than the kernel");
    let reflect = |i: isize, n: usize| -> usize {
        let n = n as isize;
        let mut i = i;
        if i < 0 {
            i = -i;
        }
        if i >= n {
            i = 2 * (n - 1) - i;
        }
        i.clamp(0, n - 1) as usize
    };
    // The live taps of each kernel row, in order.
    let live: Vec<Vec<(usize, f32)>> = k
        .taps
        .chunks(side)
        .map(|row| {
            row.iter()
                .enumerate()
                .filter(|(_, t)| **t != 0.0)
                .map(|(kx, t)| (kx, *t))
                .collect()
        })
        .collect();
    const B: usize = CONV_BLOCK;
    let mut out = vec![0f32; w * h];
    out.par_chunks_mut(w * CONV_ROWS).enumerate().for_each_init(
        || vec![0f32; (CONV_ROWS + 2 * r) * (CONV_COLS + 2 * r)],
        |tile, (band, rows)| {
            let y0 = band * CONV_ROWS;
            let nrows = rows.len() / w;
            let mut x0 = 0;
            while x0 < w {
                let nx = CONV_COLS.min(w - x0);
                let tw = nx + 2 * r;
                for ty in 0..nrows + 2 * r {
                    let sy = reflect((y0 + ty) as isize - r as isize, h);
                    let s = &src[sy * w..sy * w + w];
                    let t = &mut tile[ty * tw..(ty + 1) * tw];
                    for (tx, o) in t.iter_mut().enumerate() {
                        *o = s[reflect((x0 + tx) as isize - r as isize, w)];
                    }
                }
                for yy in 0..nrows {
                    let orow = &mut rows[yy * w + x0..yy * w + x0 + nx];
                    let mut xb = 0;
                    while xb + B <= nx {
                        let mut acc = [0f32; B];
                        for (ky, taps) in live.iter().enumerate() {
                            let p = &tile[(yy + ky) * tw + xb..(yy + ky) * tw + xb + B + 2 * r];
                            for &(kx, t) in taps {
                                let v: &[f32; B] = p[kx..kx + B].try_into().expect("block");
                                for i in 0..B {
                                    acc[i] += t * v[i];
                                }
                            }
                        }
                        orow[xb..xb + B].copy_from_slice(&acc);
                        xb += B;
                    }
                    for (x, o) in orow.iter_mut().enumerate().skip(xb) {
                        let mut acc = 0f32;
                        for (ky, taps) in live.iter().enumerate() {
                            let p = &tile[(yy + ky) * tw + x..];
                            for &(kx, t) in taps {
                                acc += t * p[kx];
                            }
                        }
                        *o = acc;
                    }
                }
                x0 += nx;
            }
        },
    );
    out
}

/// Output rows, columns and the pixel block of [`convolve`]'s tiles.
const CONV_ROWS: usize = 32;
const CONV_COLS: usize = 512;
const CONV_BLOCK: usize = 32;

#[cfg(test)]
mod tests {
    use super::*;

    /// `convolve` as it was before tiling: each output row swept once per
    /// tap. The reference the tiled form must equal bit for bit.
    fn convolve_reference(src: &[f32], w: usize, h: usize, k: &Kernel) -> Vec<f32> {
        let r = k.radius;
        let side = 2 * r + 1;
        let reflect = |i: isize, n: usize| -> usize {
            let n = n as isize;
            let mut i = i;
            if i < 0 {
                i = -i;
            }
            if i >= n {
                i = 2 * (n - 1) - i;
            }
            i.clamp(0, n - 1) as usize
        };
        let mut out = vec![0f32; w * h];
        let mut pad = vec![0f32; w + 2 * r];
        for (y, row) in out.chunks_mut(w).enumerate() {
            for (ky, krow) in k.taps.chunks(side).enumerate() {
                let sy = reflect(y as isize + ky as isize - r as isize, h);
                let s = &src[sy * w..sy * w + w];
                pad[r..r + w].copy_from_slice(s);
                for i in 0..r {
                    pad[r - 1 - i] = s[reflect(-(i as isize) - 1, w)];
                    pad[r + w + i] = s[reflect((w + i) as isize, w)];
                }
                for (kx, &t) in krow.iter().enumerate() {
                    if t == 0.0 {
                        continue;
                    }
                    for (o, v) in row.iter_mut().zip(&pad[kx..kx + w]) {
                        *o += t * v;
                    }
                }
            }
        }
        out
    }

    /// The tiled convolution against the row sweep, bit for bit: sizes that
    /// leave partial tiles and blocks, kernels with dead taps, radii 4-32.
    #[test]
    fn tiled_convolution_equals_the_row_sweep() {
        for (w, h, r) in [
            (37usize, 29usize, 4usize),
            (530, 41, 5),
            (1100, 70, 17),
            (600, 100, 32),
        ] {
            let side = 2 * r + 1;
            let taps: Vec<f32> = (0..side * side)
                .map(|i| {
                    if i % 7 == 3 {
                        0.0
                    } else {
                        ((i * 2_654_435_761) % 1999) as f32 / 1999.0 - 0.45
                    }
                })
                .collect();
            let k = Kernel {
                radius: r,
                taps,
                band_error: 0.0,
                max_error: 0.0,
                delivered: 1.0,
            };
            let src: Vec<f32> = (0..w * h)
                .map(|i| ((i * 40_503) % 65_521) as f32 * 0.37 - 900.0)
                .collect();
            let a = convolve(&src, w, h, &k);
            let b = convolve_reference(&src, w, h, &k);
            assert!(
                a.iter().zip(&b).all(|(a, b)| a.to_bits() == b.to_bits()),
                "{w}x{h} radius {r}"
            );
        }
    }

    #[test]
    fn the_fft_matches_a_direct_transform() {
        let n = 8;
        let x: Vec<f64> = (0..n * n).map(|i| ((i * 37 % 11) as f64).sin()).collect();
        let mut c: Vec<C> = x.iter().map(|v| C { re: *v, im: 0.0 }).collect();
        fft2(&Fft1::new(n), &mut c);
        for (ky, kx) in [(0, 0), (1, 3), (5, 2), (7, 7)] {
            let (mut re, mut im) = (0.0, 0.0);
            for y in 0..n {
                for xx in 0..n {
                    let a = -std::f64::consts::TAU * ((kx * xx + ky * y) as f64) / n as f64;
                    re += x[y * n + xx] * a.cos();
                    im += x[y * n + xx] * a.sin();
                }
            }
            let v = c[ky * n + kx];
            assert!((v.re - re).abs() < 1e-9 && (v.im - im).abs() < 1e-9);
        }
    }

    /// A planted model spectrum: the fit must return its cutoff.
    #[test]
    fn a_planted_cutoff_is_recovered() {
        let c = centres();
        for fc in [0.52, 0.61, 0.70] {
            let s: Vec<f64> = c
                .iter()
                .map(|f| 3.0 * f.powf(-1.6) * (mtf_diffraction(f / fc) * sinc(*f)).powi(2))
                .collect();
            let (got, alpha, _) = fit_cutoff(&c, &s);
            assert!((got - fc).abs() < 0.0041, "{fc}: {got}");
            assert!((alpha - 1.6).abs() < 0.051, "{alpha}");
            // The linear part must lie below 0.49 cycles/px to be fitted.
            match cube_root_cutoff(&c, &s, got) {
                Some(cube) => assert!((cube - fc).abs() < 0.03, "{fc}: cube-root {cube}"),
                None => assert!(0.75 * fc > 0.45, "{fc}: no cube-root estimate"),
            }
        }
    }

    /// Two images of one random scene with independent noise: the pair's
    /// signal spectrum is the scene's, its noise spectrum the noise's.
    #[test]
    fn pair_spectra_split_signal_from_noise() {
        let t = TILE;
        let mut seed = 0x2545_F491_4F6C_DD1Du64;
        let mut u = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            ((seed >> 11) as f64 / (1u64 << 53) as f64) - 0.5
        };
        let mut sum = SpectrumSum::new();
        for _ in 0..4 {
            let scene: Vec<f64> = (0..t * t).map(|_| u() * 20.0).collect();
            let a: Vec<f32> = scene.iter().map(|s| (s + u() * 10.0) as f32).collect();
            let b: Vec<f32> = scene.iter().map(|s| (s + u() * 10.0) as f32).collect();
            sum.add_pair(&a, &b);
        }
        let sp = sum.radial();
        // White: per-frequency power is the variance (uniform of width w: w^2 / 12).
        let (vs, vn) = (400.0 / 12.0, 100.0 / 12.0);
        let mid: Vec<usize> = (5..45).collect();
        let s = mid.iter().map(|&i| sp.signal[i]).sum::<f64>() / mid.len() as f64;
        let n = mid.iter().map(|&i| sp.noise[i]).sum::<f64>() / mid.len() as f64;
        assert!((s / vs - 1.0).abs() < 0.05, "signal {s} vs {vs}");
        assert!((n / vn - 1.0).abs() < 0.05, "noise {n} vs {vn}");
    }

    fn model(noise: f64) -> ChannelModel {
        let c = centres();
        ChannelModel {
            cutoff: 0.6,
            transfer: vec![1.0; c.len()],
            log_a: 0.0,
            alpha: 1.5,
            noise: vec![noise; c.len()],
            gather: None,
        }
    }

    /// The table reproduces the phase-averaged Catmull-Rom response measured
    /// by `kernel-table.py` (A7CR four-shot quality, round 1): 0.973 / 0.889 /
    /// 0.821 / 0.743 at 0.20 / 0.30 / 0.35 / 0.40 cycles/px.
    #[test]
    fn the_gather_table_is_the_catmull_rom_response() {
        let g = gather_table(crate::align::Resampler::CatmullRom);
        for (f, want) in [(0.20, 0.973), (0.30, 0.889), (0.35, 0.821), (0.40, 0.743)] {
            let got = radial_at(&g, f);
            assert!((got - want).abs() < 0.006, "{f}: {got} vs {want}");
        }
        // Unity at DC; below one, and above the on-axis g(f)^2, at 0.4 (off
        // the axes both factors are nearer one).
        // (the table's first bin centre is 0.005 cycles/px, not zero)
        assert!((gather_annulus_power(&g, 0.0) - 1.0).abs() < 1e-3);
        let p = gather_annulus_power(&g, 0.4);
        assert!(p < 1.0 && p > radial_at(&g, 0.4).powi(2), "{p}");
    }

    /// A planted spectrum seen through the gather: divided by the gather's
    /// annulus power before the fit, the planted cutoff is recovered; left
    /// in, it reads low (the bias the model change removes).
    #[test]
    fn a_gathered_planted_cutoff_is_recovered_once_the_gather_is_divided_out() {
        let c = centres();
        let g = gather_table(crate::align::Resampler::CatmullRom);
        for fc in [0.56, 0.62] {
            let s: Vec<f64> = c
                .iter()
                .map(|f| {
                    3.0 * f.powf(-1.6)
                        * (mtf_diffraction(f / fc) * sinc(*f)).powi(2)
                        * gather_annulus_power(&g, *f)
                })
                .collect();
            let (raw, _, _) = fit_cutoff(&c, &s);
            let undone: Vec<f64> = s
                .iter()
                .zip(&c)
                .map(|(v, f)| v / gather_annulus_power(&g, *f))
                .collect();
            let (got, _, _) = fit_cutoff(&c, &undone);
            assert!((got - fc).abs() < 0.0041, "{fc}: {got}");
            assert!(
                raw < fc - 0.004,
                "{fc}: the gather left in should bias low, read {raw}"
            );
        }
    }

    /// The gather in the model lowers the system transfer by exactly its
    /// per-axis response, and leaves it alone when absent.
    #[test]
    fn the_gather_multiplies_the_system_transfer() {
        let plain = model(1e-6);
        let mut with = model(1e-6);
        let g = gather_table(crate::align::Resampler::CatmullRom);
        with.gather = Some(g.clone());
        for (fx, fy) in [(0.3, 0.0), (0.2, 0.25), (0.0, 0.4)] {
            let want = system_mtf(&plain, fx, fy) * radial_at(&g, fx) * radial_at(&g, fy);
            assert!((system_mtf(&with, fx, fy) - want).abs() < 1e-12);
        }
    }

    /// With negligible noise the restored transfer `G H` is the target below
    /// the gain cap; with heavy noise the filter backs off.
    #[test]
    fn the_filter_reaches_the_target_where_signal_dominates() {
        let m = model(1e-12);
        for f in [0.1, 0.2, 0.3] {
            let got = gain_at(&m, f, 0.0, 0.7, 50.0) * system_mtf(&m, f, 0.0);
            assert!((got - target(0.7, f)).abs() < 1e-6, "{f}: {got}");
        }
        let noisy = model(1e3);
        assert!(gain_at(&noisy, 0.3, 0.0, 0.7, 50.0) < 0.1);
        assert_eq!(gain_at(&m, 0.65, 0.0, 0.7, 50.0), 0.0, "past the cutoff");
    }

    /// The truncated kernel reproduces the design within its stated error,
    /// and convolving a delta returns the kernel.
    #[test]
    fn the_kernel_realises_the_design() {
        // A realistic case: cutoff 0.57 cycles/px, little noise, so the gain
        // rises to its cap below the cutoff (the taper must bring it down).
        let mut sharp = model(1e-9);
        sharp.cutoff = 0.57;
        let k = kernel(
            &gain_grid(&sharp, 128, 0.7, 8.0),
            128,
            32,
            0.02,
            (0.15, 0.45),
        );
        assert!(
            k.band_error <= 0.02,
            "{} at radius {}",
            k.band_error,
            k.radius
        );
        let m = model(1e-4);
        let n = 128;
        let g = gain_grid(&m, n, 0.7, 8.0);
        let k = kernel(&g, n, 24, 0.02, (0.02, 0.5));
        assert!(k.band_error <= 0.02 || k.radius == 24, "{k:?}");
        assert!((k.taps.iter().map(|t| f64::from(*t)).sum::<f64>() - 1.0).abs() < 1e-5);
        let (w, h) = (64, 64);
        let mut img = vec![0f32; w * h];
        img[32 * w + 32] = 1.0;
        let out = convolve(&img, w, h, &k);
        let r = k.radius;
        for dy in 0..2 * r + 1 {
            for dx in 0..2 * r + 1 {
                let got = out[(32 + dy - r) * w + 32 + dx - r];
                assert!((got - k.taps[dy * (2 * r + 1) + dx]).abs() < 1e-6);
            }
        }
        // A constant image is unchanged, including at the borders.
        let flat = convolve(&vec![5.0; w * h], w, h, &k);
        assert!(flat.iter().all(|v| (v - 5.0).abs() < 1e-3));
    }

    /// Three channels planted with one aperture: the joint fit returns its
    /// green cutoff; a spectrum with no roll-off runs to the ceiling.
    #[test]
    fn the_joint_fit_recovers_one_aperture() {
        let c = centres();
        for fg in [0.55, 0.62, 0.70] {
            let s: Vec<Vec<f64>> = (0..3)
                .map(|ch| {
                    let fc = fg * WAVELENGTH_UM[1] / WAVELENGTH_UM[ch];
                    c.iter()
                        .map(|f| {
                            f.powf(-1.2 - 0.4 * ch as f64)
                                * (mtf_diffraction(f / fc) * sinc(*f)).powi(2)
                        })
                        .collect()
                })
                .collect();
            let (got, _) = fit_cutoff_joint(&c, [&s[0], &s[1], &s[2]]);
            assert!((got - fg).abs() < 0.0081, "{fg}: {got}");
        }
        let flat: Vec<f64> = c.iter().map(|f| f.powf(-2.0)).collect();
        let (got, _) = fit_cutoff_joint(&c, [&flat, &flat, &flat]);
        assert!(got > 0.88, "{got}");
    }

    #[test]
    fn the_blend_transfer_is_the_amplitude_ratio() {
        let c = centres();
        let reference = Spectrum {
            signal: c.iter().map(|f| f.powf(-2.0)).collect(),
            noise: vec![0.0; c.len()],
            count: vec![100.0; c.len()],
            tiles: 1,
        };
        let shrink = |f: f64| 1.0 - 0.8 * f;
        let out = Spectrum {
            signal: c
                .iter()
                .zip(&reference.signal)
                .map(|(f, s)| s * shrink(*f).powi(2))
                .collect(),
            ..reference.clone()
        };
        let m = blend_transfer(&c, &out, &reference);
        for (i, f) in c.iter().enumerate() {
            if *f > 0.03 && *f < 0.46 {
                assert!((m[i] - shrink(*f)).abs() < 1e-3, "{f}: {}", m[i]);
            }
        }
    }
}
