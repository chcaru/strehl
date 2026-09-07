//! Undo the resampling kernel — a single-image Wiener restoration whose `H` is
//! **our own interpolator**, not a model of a lens.
//!
//! # Status: BUILT, MEASURED, and OPT-IN. Read §"The verdict" first.
//!
//! Reachable on **both** merge backends through `STREHL_RESTORE`, which carries
//! the gain cap: the estimator reads it at `merge_cmd.rs:4452` and the default
//! pyramid path at `merge_cmd.rs:5765`. Unset means off, so no shipped byte
//! moves without it. This line read "NOT WIRED IN" after both call sites
//! existed; the verdict below is unaffected, because being reachable is not the
//! same as being recommended.
//!
//! # What this is for
//!
//! The merge gathers every frame through one resampling pass
//! ([`crate::warpmap::gather_checked`]). That pass attenuates the passband: the
//! phase-averaged MTF of the shipped Catmull-Rom kernel is 0.940 at 0.25
//! cycles/sample and 0.625 at Nyquist. BUILD-SHARP measured the cost with
//! M88b's paired 10-90 ESF rise (instrument floor 0.6699 um) and attributed
//! **18.6% of the shipped merge's blur variance** to it — the second largest
//! term after the optics themselves.
//!
//! The obvious repair — a better kernel — was tried and **fails**. Pooled over
//! the three admitted ROIs, a Lanczos-3 gather scores `-0.045 +/- 0.67 um`
//! against Catmull-Rom: a null. This module explains why, in closed form: the
//! two kernels' phase-averaged MTFs never differ by more than 13.3% (peak, at
//! 0.35 cycles/sample) and differ by only 2.1% at Nyquist — 0.6251 against
//! 0.6383. There is no compact interpolator that does not pay this, so the only
//! remaining move is to *correct* for it.
//!
//! # The estimator
//!
//! ```text
//! G(f) = conj(H(f)) / ( |H(f)|^2 + sigma^2 / S(f) )
//! ```
//!
//! the brief's multi-frame Wiener at `K = 1`, which is what the multi-frame
//! case collapses to anyway: M70 measured the through-focus band matrix as
//! rank-1 to 0.9959, so the frames carry one common signal and stacking `K` of
//! them adds no independent observation of it to invert.
//!
//! `H` is real and non-negative, so `conj(H) = H` and **the filter is
//! zero-phase**: it can change an edge's contrast but cannot move it. That is
//! deliberate. Moving geometry is alignment's job and a restoration that
//! displaces pixels would corrupt the registration this project spends its
//! whole budget on.
//!
//! # Why `H` is trustworthy here and was not in M115 / M20
//!
//! | | M115, M20 | this module |
//! | --- | --- | --- |
//! | `H` is | a model of defocus (x) diffraction | [`Resampler`]'s own kernel |
//! | known to | a fitted magnification and an assumed pupil | machine precision |
//! | recovers | information no frame contains | attenuation we applied ourselves |
//!
//! If `H` is wrong here, the *code* is wrong, and [`gather_mtf`] is checked
//! against two facts that hold for any interpolating kernel: `M(0) == 1`
//! exactly, and at phase 0 the taps are a Kronecker delta.
//!
//! # The one approximation, stated
//!
//! A gather samples each output pixel at its own sub-pixel phase, so the
//! operation is **not shift-invariant and has no single OTF**. What it has is
//! an expected attenuation, averaged over phase, and correcting by that is the
//! best linear correction available without per-pixel phase. The residual is a
//! phase-dependent term this filter does not touch. The recovery is therefore
//! partial *by construction*, not by tuning.
//!
//! # The verdict — MEASURED, and it is a negative
//!
//! The guard the brief asked for (fall back where `sum|H|^2` is small) turns
//! out never to bind, because the **noise term gets there first**. On real
//! merges the achievable gain is:
//!
//! | subject | sigma^2 (from the merge's own spectrum) | max gain | gain @0.25 c/px |
//! | --- | --- | --- | --- |
//! | `109MSDCF` | 691.6 | **1.096** | 1.021 |
//! | `tweezers-cpl` | 4983.0 | **1.298** | 1.059 |
//!
//! against the `1 / 0.625 = 1.60` an ideal inverse would apply at Nyquist. A
//! gain cap of 1.4, 1.7 or 2.5 produces **byte-identical output**: the cap is
//! never reached. The calibrated noise, not a safety limit, is what stops this.
//!
//! Scored on the paired ESF rise, gain cap 1.7, against the shipped arm:
//!
//! | ROI | floor | delta rise |
//! | --- | --- | --- |
//! | `M94` | 0.356 um | **+0.688 um** |
//! | `TW1` | 0.250 um | +0.019 um (null) |
//! | `TW5` | 0.305 um | +0.111 um (null) |
//!
//! One ROI marginally above its floor, two nulls. Checked on the picture for
//! the failure mode that matters: on a real hard edge with a flat approach the
//! largest profile change anywhere is **0.0035 of the step**, and there is no
//! ringing to see. It does not ring because it is too weak to ring.
//!
//! **So this does not ship on by default.** It is committed because the
//! measurement is the deliverable: it says, with a runnable number, that
//! deconvolution cannot recover even *our own known kernel* on this rig's data,
//! which is the same wall M115 (`R_SNR = 1.0014 +/- 0.0184`) and M20 (wins on
//! 15.1% of pixels) hit from two other directions. Three independent routes,
//! one answer.
//!
//! It is worth keeping switchable because the limit is **SNR, not physics**.
//! M20's aperture result says moving from marked f/11 to f/5.6 multiplies
//! best-frame contrast at 4-px detail by 9.6x. On captures with that much more
//! signal, `sigma^2/S` falls and this filter starts to bite. The right fix for
//! the resampling loss is still to not incur it — see
//! `docs/research/BUILD-SHARP.md` §"routed to other lanes" for the gather-order
//! change that would remove it outright.

use crate::align::Resampler;

/// Number of sub-pixel phases [`gather_mtf`] averages over.
///
/// 64 is not tuning: the phase average converges monotonically and 64 agrees
/// with 256 to better than 1e-4 at every frequency, which is two orders below
/// the smallest effect this module can produce.
const PHASE_SAMPLES: usize = 64;

/// Whether the gather has a linear, shift-invariant kernel restoration can
/// model.
///
/// Clamped Catmull-Rom depends on the values under each individual gather, so
/// it has no single tap response or MTF to invert. Treating it as ordinary
/// Catmull-Rom would silently restore a kernel that did not produce the image.
pub const fn restoration_supported(r: Resampler) -> bool {
    !matches!(r, Resampler::ClampedCatmullRom)
}

fn assert_restoration_supported(r: Resampler) {
    assert!(
        restoration_supported(r),
        "restoration refuses ClampedCatmullRom: clamping is nonlinear and has no \
         shift-invariant tap response to invert"
    );
}

/// One interpolation weight, for the kernel a [`Resampler`] uses.
///
/// This **must** agree with `align.rs`'s samplers. It is written separately
/// rather than factored out of them because those are 2-D, hot, and specialised
/// on integer strides; a shared abstraction would put a branch in the merge's
/// innermost loop to serve an analysis path that runs once per image.
/// [`selftest`] pins the agreement instead.
fn tap(r: Resampler, t: f64) -> f64 {
    let a = t.abs();
    match r {
        Resampler::Nearest => {
            if a < 0.5 {
                1.0
            } else {
                0.0
            }
        }
        Resampler::Bilinear => (1.0 - a).max(0.0),
        Resampler::CatmullRom => {
            if a < 1.0 {
                1.5 * a * a * a - 2.5 * a * a + 1.0
            } else if a < 2.0 {
                -0.5 * a * a * a + 2.5 * a * a - 4.0 * a + 2.0
            } else {
                0.0
            }
        }
        Resampler::ClampedCatmullRom => {
            unreachable!("nonlinear kernels must be refused before tap evaluation")
        }
        Resampler::Lanczos2 | Resampler::Lanczos3 => {
            let n = if matches!(r, Resampler::Lanczos2) { 2.0 } else { 3.0 };
            if a >= n {
                0.0
            } else if a < 1e-12 {
                1.0
            } else {
                let pt = std::f64::consts::PI * t;
                (pt.sin() / pt) * ((pt / n).sin() / (pt / n))
            }
        }
    }
}

fn support(r: Resampler) -> i32 {
    match r {
        Resampler::Nearest => 1,
        Resampler::Bilinear => 1,
        Resampler::CatmullRom | Resampler::Lanczos2 => 2,
        Resampler::ClampedCatmullRom => {
            unreachable!("nonlinear kernels must be refused before support evaluation")
        }
        Resampler::Lanczos3 => 3,
    }
}

/// Phase-averaged MTF of one gather, at `f` cycles per **sample of the plane
/// the gather ran on**.
///
/// Not cycles per output pixel. The merge gathers on the CFA quad plane and the
/// demosaic then doubles the grid, so a cycle per output pixel is *half* a
/// cycle per sample here. Callers working in output pixels must double `f`, and
/// [`RestoreConfig::grid_factor`] exists so that conversion is a named value
/// rather than a `2.0` somebody has to notice.
pub fn gather_mtf(r: Resampler, f: f64) -> f64 {
    assert_restoration_supported(r);
    let sup = support(r);
    let mut acc = 0.0;
    for p in 0..PHASE_SAMPLES {
        let phi = (p as f64 + 0.5) / PHASE_SAMPLES as f64;
        let mut w = Vec::with_capacity(2 * sup as usize);
        let mut sum = 0.0;
        for n in (-sup + 1)..=sup {
            let v = tap(r, n as f64 - phi);
            w.push((n as f64 - phi, v));
            sum += v;
        }
        if sum.abs() < 1e-12 {
            continue;
        }
        let (mut re, mut im) = (0.0, 0.0);
        for (d, v) in &w {
            let th = 2.0 * std::f64::consts::PI * f * d;
            re += v / sum * th.cos();
            im += v / sum * th.sin();
        }
        acc += re.hypot(im);
    }
    acc / PHASE_SAMPLES as f64
}

/// How aggressively to restore, and on which grid.
#[derive(Clone, Copy, Debug)]
pub struct RestoreConfig {
    /// The kernel the merge gathered with. Read it off the sidecar
    /// ([`crate::warpmap::WarpMap::resampler`]); do not assume the default,
    /// which is exactly the mistake `solve_config_key` exists to prevent.
    pub resampler: Resampler,
    /// Cycles per gather-plane sample, per cycle per pixel of the image being
    /// restored. `1.0` for a binned merge (the gather grid itself), `2.0` for a
    /// demosaiced one. Getting this backwards halves or doubles the correction.
    pub grid_factor: f64,
    /// Noise variance per pixel, in the image's own units, squared. The whole
    /// point of the Wiener form: this is what makes the filter exactly as
    /// aggressive as the calibrated noise permits and no more.
    pub sigma2: f64,
    /// Hard ceiling on the gain, the brief's guard in its bluntest form.
    /// **Measured never to bind on this rig** (see the module docs) — it is
    /// kept because a guard that has been shown to be slack is worth more than
    /// one that has never been tested. At `1.0` this whole module is a no-op,
    /// which is the fallback "never worse than the input" reduces to for a
    /// restoration.
    pub gain_cap: f64,
}

impl RestoreConfig {
    /// The highest image frequency at which the gather is still the limiter,
    /// in the restored image's own units.
    ///
    /// The gather runs on half-resolution CFA planes -- `align_cmd.rs`
    /// deinterleaves with stride 2 before gathering, so its taps are two output
    /// pixels apart, and BUILD-SHARP's warpmap is 3516 x 2344 against the
    /// 7032 x 4688 the gallery writes. `grid_factor` maps output frequency to
    /// plane frequency, so the plane's Nyquist of 0.5 sits at `0.5 /
    /// grid_factor` in output units: **0.25** for a demosaiced merge.
    ///
    /// Above it two separate things go wrong. Arithmetically, `f *
    /// grid_factor` exceeds 0.5 and [`gather_mtf`] is read past the plane's
    /// Nyquist, where its DTFT aliases and folds back **up** toward 1.0 --
    /// measured to peak at 0.25 and return to 1.026 at Nyquist, moving the
    /// dominant outer tap to `k = 2` and putting a 4-px-period ring into the
    /// picture. Physically the statement is simpler: the gather plane cannot
    /// represent that detail at all, so whatever is up there was manufactured
    /// by the demosaic interpolator rather than attenuated by the resampler,
    /// and correcting it corrects a loss that did not happen there.
    ///
    /// For a binned merge (`grid_factor <= 1.0`) the gather grid IS the output
    /// grid, nothing folds, and this returns Nyquist so no taper applies.
    fn knee(&self) -> f64 {
        if !(self.grid_factor > 1.0) {
            return 0.5;
        }
        0.5 / self.grid_factor
    }

    /// The gain applied at one frequency, given the local signal power.
    ///
    /// `signal_power` is `S(f)`: the image's own power at this frequency, which
    /// is why this is self-calibrating and needs no lens model and no scene
    /// prior. Where the image has no signal left, `sigma^2/S` explodes and the
    /// gain returns to 1 — the estimator declining, on its own evidence, to
    /// amplify a frequency that is only noise.
    ///
    /// Above [`Self::knee`] the correction is rolled off rather than evaluated:
    /// see [`roll_off`] for why a smooth taper and not a hard shelf.
    pub fn gain(&self, f: f64, signal_power: f64) -> f64 {
        if !(signal_power > 0.0) || !self.gain_cap.is_finite() {
            return 1.0;
        }
        let knee = self.knee();
        let a = f.abs();
        // Evaluated AT the knee, never past it: this is the clamp.
        let h = gather_mtf(self.resampler, a.min(knee) * self.grid_factor);
        if h <= 1e-6 {
            return 1.0;
        }
        let g = (h / (h * h + self.sigma2 / signal_power)).clamp(1.0, self.gain_cap.max(1.0));
        1.0 + (g - 1.0) * roll_off(a, knee)
    }

    /// Separable 2-D gain. The gather is separable, so its correction is too.
    pub fn gain_2d(&self, fx: f64, fy: f64, signal_power: f64) -> f64 {
        if !(signal_power > 0.0) {
            return 1.0;
        }
        let knee = self.knee();
        let (ax, ay) = (fx.abs(), fy.abs());
        let h = gather_mtf(self.resampler, ax.min(knee) * self.grid_factor)
            * gather_mtf(self.resampler, ay.min(knee) * self.grid_factor);
        if h <= 1e-6 {
            return 1.0;
        }
        let g = (h / (h * h + self.sigma2 / signal_power)).clamp(1.0, self.gain_cap.max(1.0));
        1.0 + (g - 1.0) * roll_off(ax, knee) * roll_off(ay, knee)
    }
}

/// Raised-cosine taper of the EXCESS gain from the knee to Nyquist.
///
/// `1` at and below the knee, `0` at Nyquist, monotone non-increasing between,
/// with zero slope at both ends so the target curve has no corner for the
/// least-squares fit to ring on.
///
/// A hard shelf at the knee would be the obvious alternative and it is worse
/// twice over: a step in the target is itself a filter with its own ringing,
/// and holding the knee's boost flat to Nyquist would amplify demosaic
/// interpolation artefacts exactly as hard as it amplifies real detail --
/// which, above the knee, is all there is to amplify.
///
/// Because the excess is non-negative (`gain` clamps to `[1, cap]`), scaling it
/// by a monotone non-increasing weight cannot make the response rise, which is
/// the anti-folding property `the_response_never_rises_above_the_knee` pins.
fn roll_off(f: f64, knee: f64) -> f64 {
    if knee >= 0.5 || f <= knee {
        return 1.0;
    }
    if f >= 0.5 {
        return 0.0;
    }
    let t = (f - knee) / (0.5 - knee);
    0.5 * (1.0 + (std::f64::consts::PI * t).cos())
}

/// What [`restore_plane`] actually did.
///
/// Returned rather than logged, in the idiom of [`crate::merge::VeilReport`]: a
/// correction that is a no-op and one that reshapes every edge both produce a
/// picture, and only this tells them apart.
#[derive(Clone, Debug, Default)]
pub struct RestoreReport {
    /// Half of the symmetric FIR, centre tap first. The full filter is
    /// `[..taps[1..].rev(), taps[0], ..taps[1..]]`.
    pub taps: Vec<f64>,
    /// Response at DC. **Must be exactly 1.** The filter is a sharpener, not an
    /// exposure change, and a DC gain of anything else is an additive level
    /// shift wearing a restoration's clothes -- the same failure section 18 of
    /// `docs/research/BUILD-SHARP.md` caught in the veil envelope.
    pub dc_gain: f64,
    /// Largest realised gain anywhere in `[0, 0.5]` cycles per pixel.
    pub max_gain: f64,
    /// Realised gain at Nyquist.
    pub gain_at_nyquist: f64,
    /// Fraction of the gather's own MTF loss the filter buys back, integrated
    /// over frequency. `1.0` would be a perfect inverse; the noise term is what
    /// stops it.
    pub recovered_fraction: f64,
    /// Fraction of pixels the filter drove outside the min/max of their own
    /// 9x9 input support.
    ///
    /// This is the halo detector, and it is here rather than in a test because
    /// it needs no reference image, no clean arm and no visual judgement: a
    /// zero-phase sharpener may change an edge's contrast, but a pixel that
    /// ends up outside the range of every input pixel that could reach it is
    /// overshoot by definition, and overshoot at a silhouette is a rim.
    ///
    /// Reported rather than merely bounded because the useful strength and the
    /// ringing strength are the same knob: the caller has to see the cost to
    /// price it. `0.0` is the only value that means "no ringing anywhere".
    pub outside_support: f64,
    /// The largest such excursion, in the plane's own units. Pairs with
    /// [`Self::outside_support`] for the reason this project requires a cost
    /// column beside every quality number: a vanishing fraction of pixels each
    /// blowing out by thousands of DN is not the same picture as a vanishing
    /// fraction each off by one.
    pub worst_excursion: f64,
    /// The noise variance the filter was given, in the plane's own units.
    pub sigma2: f64,
}

/// Autocorrelation of a plane out to `max_lag`, averaged over both axes.
///
/// The signal power `S(f)` the Wiener form needs is the image's own, and this
/// is how it is obtained without a Fourier transform: Wiener-Khinchin says the
/// power spectrum is the transform of the autocorrelation, and an
/// autocorrelation to a short lag is a few passes over the data with no
/// dependency. `strehl-core` has exactly two dependencies and neither is an FFT.
///
/// Averaged over rows and columns because the gather is separable and is
/// corrected separably; a single one-dimensional spectrum is the matching
/// estimate.
pub fn autocorrelation(plane: &[f32], w: usize, h: usize, max_lag: usize) -> Vec<f64> {
    let mut r = vec![0.0f64; max_lag + 1];
    let mut n = vec![0.0f64; max_lag + 1];
    let mean = {
        let s: f64 = plane.iter().map(|&v| f64::from(v)).sum();
        s / (plane.len().max(1) as f64)
    };
    for y in 0..h {
        let row = &plane[y * w..y * w + w];
        for k in 0..=max_lag {
            if k >= w {
                break;
            }
            let mut acc = 0.0;
            for x in 0..(w - k) {
                acc += (f64::from(row[x]) - mean) * (f64::from(row[x + k]) - mean);
            }
            r[k] += acc;
            n[k] += (w - k) as f64;
        }
    }
    for x in 0..w {
        for k in 0..=max_lag {
            if k >= h {
                break;
            }
            let mut acc = 0.0;
            for y in 0..(h - k) {
                acc += (f64::from(plane[y * w + x]) - mean)
                    * (f64::from(plane[(y + k) * w + x]) - mean);
            }
            r[k] += acc;
            n[k] += (h - k) as f64;
        }
    }
    for k in 0..=max_lag {
        if n[k] > 0.0 {
            r[k] /= n[k];
        }
    }
    r
}

/// Power at `f` cycles per pixel, from an autocorrelation.
///
/// A Hann lag window is applied. Without it the truncation at `max_lag` rings
/// and the estimate goes negative at some frequencies, which would make
/// `sigma^2 / S` negative and the gain unbounded -- an inverse filter with no
/// noise term at all, which is precisely the runaway this project already
/// destroyed one picture with.
fn power_at(r: &[f64], f: f64) -> f64 {
    let m = r.len() - 1;
    let mut p = r[0];
    for (k, &rk) in r.iter().enumerate().skip(1) {
        let win = 0.5 * (1.0 + (std::f64::consts::PI * k as f64 / (m as f64 + 1.0)).cos());
        p += 2.0 * win * rk * (2.0 * std::f64::consts::PI * f * k as f64).cos();
    }
    p.max(0.0)
}

/// Solve a small symmetric positive-definite system by Gaussian elimination.
fn solve(mut a: Vec<Vec<f64>>, mut b: Vec<f64>) -> Option<Vec<f64>> {
    let n = b.len();
    for i in 0..n {
        let mut piv = i;
        for j in (i + 1)..n {
            if a[j][i].abs() > a[piv][i].abs() {
                piv = j;
            }
        }
        if a[piv][i].abs() < 1e-12 {
            return None;
        }
        a.swap(i, piv);
        b.swap(i, piv);
        for j in (i + 1)..n {
            let f = a[j][i] / a[i][i];
            for k in i..n {
                a[j][k] -= f * a[i][k];
            }
            b[j] -= f * b[i];
        }
    }
    let mut x = vec![0.0; n];
    for i in (0..n).rev() {
        let mut s = b[i];
        for k in (i + 1)..n {
            s -= a[i][k] * x[k];
        }
        x[i] = s / a[i][i];
    }
    Some(x)
}

/// Design the zero-phase FIR that realises this configuration's gain.
///
/// A symmetric filter `g[-m..m]` has the purely real response
/// `G(f) = g0 + 2 * sum_k g[k] cos(2 pi f k)`, so it is **zero-phase by
/// construction**: it cannot move an edge, only change its contrast. That is
/// the property the module header calls non-negotiable, and building it into
/// the filter's algebra is stronger than testing for it afterwards.
///
/// The DC constraint is likewise structural rather than fitted. Substituting
/// `g0 = 1 - 2 sum_k g[k]` gives
///
/// ```text
/// G(f) = 1 + 2 * sum_k g[k] * (cos(2 pi f k) - 1)
/// ```
///
/// which is exactly 1 at `f = 0` for **any** `g[k]`. The least-squares fit
/// therefore cannot trade DC accuracy for passband accuracy, and the filter
/// cannot become an exposure change.
pub fn design_fir(cfg: &RestoreConfig, r: &[f64], half_taps: usize) -> Vec<f64> {
    const FIT_POINTS: usize = 128;
    let m = half_taps.max(1);
    let mut ata = vec![vec![0.0f64; m]; m];
    let mut atb = vec![0.0f64; m];
    for i in 0..FIT_POINTS {
        let f = 0.5 * (i as f64 + 0.5) / FIT_POINTS as f64;
        let s = (power_at(r, f) - cfg.sigma2).max(1e-12);
        let target = cfg.gain(f, s) - 1.0;
        let basis: Vec<f64> = (1..=m)
            .map(|k| 2.0 * ((2.0 * std::f64::consts::PI * f * k as f64).cos() - 1.0))
            .collect();
        for a in 0..m {
            for b in 0..m {
                ata[a][b] += basis[a] * basis[b];
            }
            atb[a] += basis[a] * target;
        }
    }
    let outer = solve(ata, atb).unwrap_or_else(|| vec![0.0; m]);
    // The least-squares fit tracks the target at the fit points and may
    // overshoot BETWEEN them, so the cap must be enforced on the REALISED
    // response rather than on the target that was fitted. Measured: a cap of
    // 1.1 was fitted and the designed filter realised 1.1107.
    //
    // Scaling every outer tap by lambda scales `G(f) - 1` by exactly lambda,
    // because `G(f) - 1 = 2 sum_k g[k] (cos(2 pi f k) - 1)` is linear in them,
    // and recomputing the centre tap restores `G(0) = 1` exactly. So the cap is
    // enforced without disturbing either structural property.
    let mut taps = vec![1.0 - 2.0 * outer.iter().sum::<f64>()];
    taps.extend(outer);
    let cap = cfg.gain_cap.max(1.0);
    let mut realised: f64 = 1.0;
    for i in 0..2048 {
        let f = 0.5 * (i as f64 + 0.5) / 2048.0;
        realised = realised.max(fir_response(&taps, f));
    }
    if realised > cap && realised > 1.0 {
        let lambda = (cap - 1.0) / (realised - 1.0);
        for t in taps.iter_mut().skip(1) {
            *t *= lambda;
        }
        let s: f64 = taps.iter().skip(1).sum();
        taps[0] = 1.0 - 2.0 * s;
    }
    taps
}

/// Response of a half-filter at `f` cycles per pixel.
fn fir_response(taps: &[f64], f: f64) -> f64 {
    let mut g = taps[0];
    for (k, &t) in taps.iter().enumerate().skip(1) {
        g += 2.0 * t * (2.0 * std::f64::consts::PI * f * k as f64).cos();
    }
    g
}

/// Apply the restoration to one plane, in place, separably.
///
/// Returns what it did. A `gain_cap` of `1.0` makes this **byte-identical to the
/// input**, which is the "never worse than the input" fallback in its exact
/// form: not a small change, no change.
///
/// Borders replicate. A restoration is a contrast change and replicating is the
/// only border rule that cannot invent a step at the frame edge.
pub fn restore_plane(plane: &mut [f32], w: usize, h: usize, cfg: &RestoreConfig) -> RestoreReport {
    const MAX_LAG: usize = 24;
    const HALF_TAPS: usize = 4;
    assert_restoration_supported(cfg.resampler);
    let mut report = RestoreReport {
        sigma2: cfg.sigma2,
        dc_gain: 1.0,
        max_gain: 1.0,
        gain_at_nyquist: 1.0,
        ..RestoreReport::default()
    };
    if plane.len() != w * h || w < 2 * HALF_TAPS + 1 || h < 2 * HALF_TAPS + 1 {
        return report;
    }
    if !(cfg.gain_cap > 1.0) {
        report.taps = vec![1.0];
        return report;
    }
    let r = autocorrelation(plane, w, h, MAX_LAG.min(w.min(h) / 2));
    let taps = design_fir(cfg, &r, HALF_TAPS);

    report.dc_gain = fir_response(&taps, 0.0);
    report.gain_at_nyquist = fir_response(&taps, 0.5);
    let mut num = 0.0;
    let mut den = 0.0;
    for i in 0..256 {
        let f = 0.5 * (i as f64 + 0.5) / 256.0;
        let g = fir_response(&taps, f);
        report.max_gain = report.max_gain.max(g);
        let hh = gather_mtf(cfg.resampler, f * cfg.grid_factor);
        num += hh * g - hh;
        den += 1.0 - hh;
    }
    report.recovered_fraction = if den > 0.0 { num / den } else { 0.0 };
    report.taps = taps.clone();

    // Kept so the overshoot guard can compare each output against the inputs
    // that could actually reach it. One extra plane, once per plane, is a cheap
    // price for the only number here that detects a halo.
    let input = plane.to_vec();
    let mut tmp = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut acc = f64::from(plane[y * w + x]) * taps[0];
            for (k, &t) in taps.iter().enumerate().skip(1) {
                let xl = x.saturating_sub(k);
                let xr = (x + k).min(w - 1);
                acc += t * (f64::from(plane[y * w + xl]) + f64::from(plane[y * w + xr]));
            }
            tmp[y * w + x] = acc as f32;
        }
    }
    for y in 0..h {
        for x in 0..w {
            let mut acc = f64::from(tmp[y * w + x]) * taps[0];
            for (k, &t) in taps.iter().enumerate().skip(1) {
                let yu = y.saturating_sub(k);
                let yd = (y + k).min(h - 1);
                acc += t * (f64::from(tmp[yu * w + x]) + f64::from(tmp[yd * w + x]));
            }
            plane[y * w + x] = acc as f32;
        }
    }

    // The overshoot guard. The filter's support is `taps.len() - 1` either side
    // on each axis, applied separably, so the set of inputs that can reach one
    // output is a square of that radius. A min/max over a square is separable
    // the same way the filter is, so this costs two passes rather than r^2.
    //
    // Replicating borders are used here too, matching the convolution exactly:
    // a guard that assumed a different border rule would report violations at
    // the frame edge that the filter never committed.
    let r = taps.len().saturating_sub(1);
    if r > 0 {
        let (mut lo, mut hi) = (vec![0.0f32; w * h], vec![0.0f32; w * h]);
        for y in 0..h {
            for x in 0..w {
                let (mut a, mut b) = (f32::INFINITY, f32::NEG_INFINITY);
                for k in x.saturating_sub(r)..=(x + r).min(w - 1) {
                    a = a.min(input[y * w + k]);
                    b = b.max(input[y * w + k]);
                }
                lo[y * w + x] = a;
                hi[y * w + x] = b;
            }
        }
        let (mut worst, mut n_out) = (0.0f64, 0usize);
        for y in 0..h {
            for x in 0..w {
                let (mut a, mut b) = (f32::INFINITY, f32::NEG_INFINITY);
                for k in y.saturating_sub(r)..=(y + r).min(h - 1) {
                    a = a.min(lo[k * w + x]);
                    b = b.max(hi[k * w + x]);
                }
                let v = plane[y * w + x];
                let over = if v > b {
                    f64::from(v) - f64::from(b)
                } else if v < a {
                    f64::from(a) - f64::from(v)
                } else {
                    0.0
                };
                if over > 0.0 {
                    n_out += 1;
                    worst = worst.max(over);
                }
            }
        }
        report.outside_support = n_out as f64 / (w * h) as f64;
        report.worst_excursion = worst;
    }
    report
}

/// The two facts that hold for every supported linear interpolating kernel,
/// checked rather than assumed. Exposed so a caller can run it, not only the
/// test harness. Nonlinear kernels are deliberately absent.
pub fn selftest() -> Result<(), String> {
    for r in [
        Resampler::Nearest,
        Resampler::Bilinear,
        Resampler::CatmullRom,
        Resampler::Lanczos2,
        Resampler::Lanczos3,
    ] {
        let m0 = gather_mtf(r, 0.0);
        if (m0 - 1.0).abs() > 1e-9 {
            return Err(format!("{r:?}: M(0) = {m0}, must be 1 (a gather preserves DC)"));
        }
        // At phase 0 an interpolating kernel is the Kronecker delta, so a
        // gather at integer offsets is the identity and cannot attenuate.
        let sup = support(r);
        for n in (-sup + 1)..=sup {
            let want = if n == 0 { 1.0 } else { 0.0 };
            let got = tap(r, n as f64);
            if (got - want).abs() > 1e-9 {
                return Err(format!("{r:?}: tap({n}) = {got}, must be {want}"));
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A hard step, the shape a silhouette presents to the filter.
    fn step_plane(w: usize, h: usize, lo: f32, hi: f32) -> Vec<f32> {
        (0..w * h)
            .map(|i| if i % w < w / 2 { lo } else { hi })
            .collect()
    }

    /// Commissioning the overshoot guard: it must read zero when nothing
    /// overshoots AND non-zero when something does.
    ///
    /// Both halves are required. A guard that is stuck at zero passes the null
    /// and would have reported a clean picture for every strength ever tried,
    /// which is precisely the "check that cannot fail" this project treats as
    /// worse than no check. The positive arm is what proves the instrument can
    /// respond at all.
    #[test]
    fn the_overshoot_guard_reads_zero_only_when_there_is_no_overshoot() {
        let (w, h) = (64, 64);
        let base = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 1.0,
            gain_cap: 4.0,
        };

        // NULL: a cap of 1.0 is the documented no-op. Nothing may move, so
        // nothing can leave its own support.
        let mut p = step_plane(w, h, 100.0, 1000.0);
        let off = restore_plane(
            &mut p,
            w,
            h,
            &RestoreConfig {
                gain_cap: 1.0,
                ..base
            },
        );
        assert_eq!(
            off.outside_support, 0.0,
            "a no-op restoration reported {:.6} of pixels outside their own support",
            off.outside_support
        );

        // POSITIVE: a near-zero noise floor is the regime D2 measured, where
        // the Wiener form approaches a pure inverse and the FIR rings.
        let mut p = step_plane(w, h, 100.0, 1000.0);
        let on = restore_plane(
            &mut p,
            w,
            h,
            &RestoreConfig {
                sigma2: 1e-6,
                ..base
            },
        );
        assert!(
            on.outside_support > 0.0 && on.worst_excursion > 0.0,
            "an aggressive restoration on a hard step reported NO overshoot \
             ({:.6} of px, worst {:.3}); the guard cannot detect a halo and \
             every clean reading it has ever given is worthless",
            on.outside_support,
            on.worst_excursion
        );
    }

    /// The reported gain is one-dimensional; the picture gets two passes.
    ///
    /// V-RESTORE measured a filter reported at 1.4305 delivering 2.0465 on a
    /// checkerboard, matching the square to five places. This pins the relation
    /// so that a caller reading `max_gain` cannot keep believing it is what the
    /// pixels receive.
    #[test]
    fn the_realised_two_dimensional_gain_is_the_square_of_the_reported_one() {
        let (w, h) = (48, 48);
        // Exactly fx = fy = 0.5: the frequency where a separable filter's two
        // passes both act at their Nyquist response.
        let mid = 500.0f32;
        let amp = 200.0f32;
        let mut p: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = (i % w, i / w);
                if (x + y) % 2 == 0 { mid + amp } else { mid - amp }
            })
            .collect();
        let cfg = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 1e-6,
            gain_cap: 4.0,
        };
        let rep = restore_plane(&mut p, w, h, &cfg);
        // Read the realised amplitude in the interior, away from the borders.
        let c = (h / 2) * w + w / 2;
        let realised = (f64::from(p[c]) - f64::from(mid)).abs() / f64::from(amp);
        let predicted = rep.gain_at_nyquist * rep.gain_at_nyquist;
        assert!(
            (realised - predicted).abs() < 1e-3,
            "checkerboard realised {realised:.6} but the Nyquist response squared \
             is {predicted:.6}; the 2-D gain is no longer the square of the 1-D one \
             and the cap no longer bounds what the picture receives"
        );
    }

    #[test]
    fn supported_linear_kernels_are_interpolating_and_preserve_dc() {
        selftest().unwrap();
    }

    #[test]
    fn restoration_refuses_the_nonlinear_clamped_kernel_before_mutating_pixels() {
        assert!(!restoration_supported(Resampler::ClampedCatmullRom));
        assert!(restoration_supported(Resampler::CatmullRom));

        let (w, h) = (16, 16);
        let mut plane = step_plane(w, h, -100.0, 100.0);
        let before = plane.clone();
        let cfg = RestoreConfig {
            resampler: Resampler::ClampedCatmullRom,
            grid_factor: 1.0,
            sigma2: 1.0,
            gain_cap: 2.0,
        };
        let refused = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            restore_plane(&mut plane, w, h, &cfg)
        }));
        assert!(refused.is_err(), "nonlinear restoration was accepted");
        assert_eq!(
            plane, before,
            "restoration touched pixels before refusing the nonlinear kernel"
        );
    }

    /// ORCH's acceptance criterion for the fold, with a positive control that
    /// the fold it guards against is real. Nothing tested this before.
    ///
    /// The gather runs on half-resolution CFA planes, so for a demosaiced merge
    /// the gather plane's Nyquist sits at `f = 0.25` in output units. Above it
    /// [`gather_mtf`] was being read past its own Nyquist, where the DTFT is
    /// periodic and folds back **up** toward 1.0. A target that rises with
    /// frequency is an unsharp mask, and an unsharp mask at a silhouette is the
    /// halo this project has just finished removing.
    #[test]
    fn the_response_never_rises_above_the_knee() {
        let cfg = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 2.0,
            // The MERGED high-frequency noise floor measured on a real render,
            // not the far larger single-frame figure the module docs were
            // written against. The fold is worst where the filter is strongest.
            sigma2: 82.15,
            gain_cap: 4.0,
        };
        let knee = cfg.knee();
        assert!(
            (knee - 0.25).abs() < 1e-12,
            "a demosaiced merge gathers on half-resolution planes, so the knee \
             must be 0.25 in output units; got {knee}"
        );

        // POSITIVE CONTROL. If `gather_mtf` did not fold back up past the
        // plane's Nyquist there would be nothing here to guard and every
        // assertion below would pass vacuously.
        let at_knee = gather_mtf(cfg.resampler, knee * cfg.grid_factor);
        let folded = gather_mtf(cfg.resampler, 0.5 * cfg.grid_factor);
        assert!(
            folded > at_knee + 0.05,
            "the fold this test guards against is absent: the gather MTF reads \
             {at_knee:.6} at the knee and {folded:.6} an octave past it, so the \
             clamp is guarding nothing"
        );

        // THE TARGET. Monotone non-increasing above the knee, never exceeding
        // its value there, and all the way back to unity at Nyquist.
        let s = 5.0e5;
        let g_knee = cfg.gain(knee, s);
        assert!(
            g_knee > 1.001,
            "this test needs an active correction to be meaningful; got {g_knee}"
        );
        let mut prev = g_knee;
        for i in 0..=100 {
            let f = knee + (0.5 - knee) * f64::from(i) / 100.0;
            let g = cfg.gain(f, s);
            assert!(
                g <= g_knee + 1e-12 && g <= prev + 1e-12,
                "target gain rose to {g:.6} at f={f:.4}; knee {g_knee:.6}, \
                 previous {prev:.6}. The fold is back."
            );
            prev = g;
        }
        assert!(
            (cfg.gain(0.5, s) - 1.0).abs() < 1e-9,
            "above the knee the gather is not the limiter, so the correction \
             must roll all the way back to 1 at Nyquist; got {}",
            cfg.gain(0.5, s)
        );

        // THE DESIGNED RESPONSE, which is what the pixels actually receive.
        //
        // The target has a slope discontinuity at the knee -- rising steeply
        // below it, flat at it -- and a four-tap least-squares fit cannot turn
        // that corner, so it rounds it: measured, the designed peak is 1.4868
        // at f = 0.28 against 1.4574 at the knee, 2.0% high and 0.03 wide.
        // Demanding strict monotonicity from the knee itself would be demanding
        // something no FIR of this length can do, so the property pinned here
        // is the FOLD -- the response must come DOWN toward Nyquist and stay
        // down, which is what it did not do before the clamp: V-RESTORE
        // measured it peaking at 0.25 and returning to 1.026 at Nyquist.
        let (w, h) = (96usize, 96usize);
        let plane: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f64, (i / w) as f64);
                (2000.0
                    + 400.0 * (x / 3.0).sin() * (y / 5.0).cos()
                    + 150.0 * ((x * 7.0 + y * 3.0) % 11.0)) as f32
            })
            .collect();
        let r = autocorrelation(&plane, w, h, 24);
        let taps = design_fir(&cfg, &r, 4);
        let r_knee = fir_response(&taps, knee);
        let r_nyq = fir_response(&taps, 0.5);
        assert!(
            r_nyq < r_knee,
            "the designed response is {r_nyq:.6} at Nyquist against {r_knee:.6} \
             at the knee: it folds back up, which is the defect this clamp exists \
             to remove"
        );
        assert!(
            r_nyq < 1.02,
            "above the knee there is nothing the gather attenuated, so the \
             designed response must be back at unity by Nyquist; got {r_nyq:.6}"
        );
        // Allowance for the fit rounding the corner, and no more.
        const FIT_ROUNDING: f64 = 1.05;
        let mut prev = f64::INFINITY;
        for i in 0..=100 {
            let f = knee + (0.5 - knee) * f64::from(i) / 100.0;
            let resp = fir_response(&taps, f);
            assert!(
                resp <= r_knee * FIT_ROUNDING,
                "designed response {resp:.6} at f={f:.4} exceeds the knee value \
                 {r_knee:.6} by more than the {:.0}% allowed for the fit rounding \
                 the corner",
                (FIT_ROUNDING - 1.0) * 100.0
            );
            // Past the rounded shoulder the decay must be strict.
            if f >= knee + 0.2 * (0.5 - knee) {
                assert!(
                    resp <= prev + 1e-9,
                    "designed response rose from {prev:.6} to {resp:.6} at \
                     f={f:.4}, past the shoulder: the fold is back"
                );
                prev = resp;
            }
        }
    }

    #[test]
    fn catmull_rom_matches_the_measured_mtf() {
        // The values BUILD-SHARP's diagnosis is quoted against. If a kernel
        // ever changes, this fails and the report's numbers are stale.
        //
        // THESE ABSCISSAE ARE CORRECT AND HAVE BEEN CHALLENGED THREE TIMES.
        // The recurring report is that these constants are "documented at
        // f = 0.35 but are actually at f = 0.40". They are not. The confusion
        // is a conflation of two different claims in this file, both true:
        //
        //   * the MODULE HEADER's 0.35 is where the Lanczos-3 / Catmull-Rom
        //     RATIO peaks (1.1300). That is a statement about two kernels.
        //   * this test's 0.40 is a point on the Catmull-Rom MTF itself.
        //
        // 0.35 is carried below as well, so the two can no longer be swapped
        // by eye. Phase-averaged Catmull-Rom, re-derived from the basis
        // polynomials independently of this module and corroborated by
        // `docs/research/V-chroma2.md:388-404`:
        //
        //   0.25 -> 0.94024   0.35 -> 0.82113   0.40 -> 0.74255   0.50 -> 0.62500
        for (f, want) in [
            (0.25, 0.9402),
            (0.35, 0.8211),
            (0.40, 0.7425),
            (0.50, 0.6251),
        ] {
            let got = gather_mtf(Resampler::CatmullRom, f);
            assert!(
                (got - want).abs() < 5e-4,
                "MTF({f}) = {got}, expected {want}"
            );
        }
    }

    #[test]
    fn lanczos3_is_not_meaningfully_sharper() {
        // The closed-form reason the paired ESF rise measured a null for a
        // Lanczos-3 gather. If this ever stops holding, the kernel-default
        // question genuinely reopens.
        for f in [0.1, 0.2, 0.3, 0.4, 0.5] {
            let cr = gather_mtf(Resampler::CatmullRom, f);
            let l3 = gather_mtf(Resampler::Lanczos3, f);
            assert!(
                l3 / cr < 1.15,
                "Lanczos-3 is {:.3}x Catmull-Rom at {f} cyc/sample; the measured \
                 peak ratio of 1.133 at 0.35, which BUILD-SHARP's kernel null \
                 rests on, has moved",
                l3 / cr
            );
        }
    }

    #[test]
    fn the_gain_is_never_below_one_and_never_above_the_cap() {
        let c = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 700.0,
            gain_cap: 1.7,
        };
        for f in [0.0, 0.1, 0.25, 0.4, 0.5] {
            for s in [1e-3, 1.0, 1e3, 1e9] {
                let g = c.gain(f, s);
                assert!((1.0..=1.7).contains(&g), "gain({f}, {s}) = {g}");
            }
        }
        // A cap of 1.0 must make the module a no-op, exactly.
        let off = RestoreConfig { gain_cap: 1.0, ..c };
        for f in [0.0, 0.25, 0.5] {
            assert_eq!(off.gain(f, 1e9), 1.0);
        }
    }

    #[test]
    fn no_signal_means_no_gain() {
        // The guard that matters: where the image has nothing left at this
        // frequency, the filter must decline to amplify it.
        let c = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 1e6,
            gain_cap: 4.0,
        };
        assert!(c.gain(0.5, 1e-6) < 1.0 + 1e-9);
    }

    /// Build a plane, gather it through a real Catmull-Rom resample at a fixed
    /// sub-pixel phase, and hand back both. The attenuation the filter is meant
    /// to undo is thereby real rather than modelled.
    fn gathered_step(w: usize, h: usize, phi: f64) -> (Vec<f32>, Vec<f32>) {
        let mut truth = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                truth[y * w + x] = if x >= w / 2 { 1000.0 } else { 100.0 };
            }
        }
        let mut got = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                let mut acc = 0.0;
                let mut sum = 0.0;
                for n in -1i32..3 {
                    let wt = super::tap(Resampler::CatmullRom, n as f64 - phi);
                    let xs = (x as i32 + n).clamp(0, w as i32 - 1) as usize;
                    acc += wt * f64::from(truth[y * w + xs]);
                    sum += wt;
                }
                got[y * w + x] = (acc / sum) as f32;
            }
        }
        (truth, got)
    }

    #[test]
    fn the_dc_gain_is_exactly_one_so_this_cannot_become_an_exposure_change() {
        // Section 18 of BUILD-SHARP.md caught a correction whose whole effect
        // could have been an additive level shift. This filter is structurally
        // incapable of that, and here is the check across a wide range of
        // aggressiveness rather than at one setting.
        let (_, mut img) = gathered_step(96, 96, 0.5);
        for cap in [1.1, 1.4, 1.7, 2.5, 4.0] {
            for sigma2 in [1.0, 100.0, 1e4, 1e6] {
                let cfg = RestoreConfig {
                    resampler: Resampler::CatmullRom,
                    grid_factor: 1.0,
                    sigma2,
                    gain_cap: cap,
                };
                let mut plane = img.clone();
                let rep = restore_plane(&mut plane, 96, 96, &cfg);
                assert!(
                    (rep.dc_gain - 1.0).abs() < 1e-12,
                    "cap {cap} sigma2 {sigma2}: DC gain {} is not 1",
                    rep.dc_gain
                );
                assert!(
                    rep.max_gain <= cap + 1e-6,
                    "cap {cap}: realised gain {} exceeds it",
                    rep.max_gain
                );
            }
        }
        // And a flat plane must come back flat, to the last bit.
        img.iter_mut().for_each(|v| *v = 4321.0);
        let cfg = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 100.0,
            gain_cap: 1.7,
        };
        restore_plane(&mut img, 96, 96, &cfg);
        for v in &img {
            assert!((v - 4321.0).abs() < 1e-2, "flat plane moved to {v}");
        }
    }

    #[test]
    fn a_gain_cap_of_one_is_byte_identical() {
        let (_, img) = gathered_step(64, 64, 0.25);
        let cfg = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 50.0,
            gain_cap: 1.0,
        };
        let mut out = img.clone();
        restore_plane(&mut out, 64, 64, &cfg);
        assert_eq!(out, img, "gain_cap 1.0 must be the identity, not merely close");
    }

    #[test]
    fn the_filter_sharpens_the_edge_without_moving_it() {
        // The property the module header calls non-negotiable. The edge
        // position is measured as the 50% crossing of the profile, to
        // sub-pixel precision by linear interpolation, and it must not move.
        let (_, img) = gathered_step(128, 128, 0.5);
        let cfg = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 1.0,
            gain_cap: 1.7,
        };
        let mut out = img.clone();
        let rep = restore_plane(&mut out, 128, 128, &cfg);

        let row = 64usize;
        let crossing = |p: &[f32]| -> f64 {
            let (lo, hi) = (100.0f64, 1000.0f64);
            let half = 0.5 * (lo + hi);
            for x in 1..128 {
                let (a, b) = (f64::from(p[row * 128 + x - 1]), f64::from(p[row * 128 + x]));
                if (a - half) * (b - half) <= 0.0 && (b - a).abs() > 1e-9 {
                    return (x - 1) as f64 + (half - a) / (b - a);
                }
            }
            f64::NAN
        };
        let before = crossing(&img);
        let after = crossing(&out);
        assert!(
            (after - before).abs() < 1e-4,
            "the edge moved {} px, from {before} to {after}; a zero-phase filter cannot do that",
            after - before
        );

        // Potency: it must actually have done something, or "did not move" is
        // the trivially true statement about an identity filter.
        let slope = |p: &[f32]| {
            (0..127)
                .map(|x| (f64::from(p[row * 128 + x + 1]) - f64::from(p[row * 128 + x])).abs())
                .fold(0.0f64, f64::max)
        };
        assert!(
            slope(&out) > slope(&img) * 1.02,
            "peak slope went {} -> {}, so the filter is inert and this test proves nothing",
            slope(&img),
            slope(&out)
        );
        assert!(rep.recovered_fraction > 0.0);
    }

    #[test]
    fn a_real_gather_loss_is_partly_recovered_measured_as_10_90_edge_width() {
        // End to end on the quantity the ESF instrument actually reports.
        //
        // Note what this test does NOT do: it does not compare against the
        // un-gathered truth. A gather at phase 0.5 genuinely translates the
        // image by half a pixel, and a zero-phase filter cannot undo a
        // translation, so a distance-to-truth metric charges the restoration
        // for a registration offset it is forbidden to touch. The first
        // version of this test did exactly that and reported a regression.
        // Edge WIDTH is the blur, is shift-invariant, and is the number the
        // rest of this project is measured in.
        let (truth, img) = gathered_step(128, 128, 0.5);
        let cfg = RestoreConfig {
            resampler: Resampler::CatmullRom,
            grid_factor: 1.0,
            sigma2: 1.0,
            gain_cap: 1.7,
        };
        let mut out = img.clone();
        restore_plane(&mut out, 128, 128, &cfg);

        let row = 128usize * 64;
        let width_10_90 = |p: &[f32]| -> f64 {
            let (lo, hi) = (100.0f64, 1000.0f64);
            let at = |frac: f64| -> f64 {
                let level = lo + frac * (hi - lo);
                for x in 1..128 {
                    let (a, b) = (f64::from(p[row + x - 1]), f64::from(p[row + x]));
                    if (a - level) * (b - level) <= 0.0 && (b - a).abs() > 1e-9 {
                        return (x - 1) as f64 + (level - a) / (b - a);
                    }
                }
                f64::NAN
            };
            at(0.9) - at(0.1)
        };

        let (w_truth, w_gathered, w_restored) =
            (width_10_90(&truth), width_10_90(&img), width_10_90(&out));

        // Potency of the apparatus: the gather must have actually blurred the
        // edge, or "the filter narrowed it" is a claim about nothing.
        assert!(
            w_gathered > w_truth + 0.1,
            "the gather did not blur the edge ({w_truth} -> {w_gathered}), so this test is vacuous"
        );
        assert!(
            w_restored < w_gathered - 0.01,
            "10-90 width {w_gathered} -> {w_restored}: the restoration did not narrow the edge"
        );
        // And it must not overshoot into being sharper than the signal that
        // was gathered, which would mean it invented detail.
        assert!(
            w_restored >= w_truth - 1e-9,
            "restored width {w_restored} is below the un-gathered truth {w_truth}"
        );
    }
}

// ---------------------------------------------------------------------------
// Wiring. Added when this module was connected to the product for the first
// time; everything above predates it and is unchanged.
// ---------------------------------------------------------------------------

/// Opt-in flag for the restoration, read from the environment.
///
/// An environment variable rather than a CLI argument, following
/// `crate::optics`'s `STREHL_FIX_CA`: the argument parser is shared surface
/// with several agents in it, and this flag is meant to be temporary -- it
/// exists to carry a measured trade curve to whoever sets the default.
///
/// The value IS the strength: it is [`RestoreConfig::gain_cap`]. `1.0` is a
/// documented no-op, so the sweep runs from off to full through a single knob
/// and "off" is not a second code path that could drift from "on at zero".
pub const RESTORE_ENV: &str = "STREHL_RESTORE";

/// `None` when the flag is unset, empty, `0` or `off`, and also when the cap is
/// not above `1.0` -- that is the no-op, and declining to run reaches the
/// identical picture by a cheaper route.
///
/// The `1.0` case is announced rather than silent. `STREHL_RESTORE=1` reads to
/// a human as "enable" -- that is the idiom for every boolean flag -- but this
/// value IS the gain cap, and a cap of 1.0 is the identity. An orchestrator
/// commissioning this flag set it to `1`, observed byte-identical output, and
/// concluded the stage was unreachable on the render path; it is reachable, and
/// `1` had merely selected the documented no-op. Silence is what made that
/// conclusion available, so the no-op now says so on the same stream the
/// restore banner uses.
pub fn gain_cap_from_env() -> Option<f64> {
    let raw = std::env::var(RESTORE_ENV).ok()?;
    let raw = raw.trim().to_string();
    if raw.is_empty() || raw == "0" || raw.eq_ignore_ascii_case("off") {
        return None;
    }
    let Ok(cap) = raw.parse::<f64>() else {
        eprintln!(
            "restore        : {RESTORE_ENV}={raw:?} is not a number -- the value is a gain \
             cap, not a boolean. The restoration will NOT run. Pass a cap above 1.0 (e.g. 4.0)."
        );
        return None;
    };
    if cap.is_finite() && cap > 1.0 {
        Some(cap)
    } else {
        eprintln!(
            "restore        : {RESTORE_ENV}={raw} is the documented NO-OP (the value is a \
             gain cap and {cap:.4} is not above 1.0), so the restoration will NOT run and \
             the output will be byte-identical to leaving it unset. Pass a cap above 1.0 \
             (e.g. 4.0) to enable it."
        );
        None
    }
}

/// Multiplier on the calibrated `sigma^2`, for **measurement only**.
///
/// This is not a quality knob and must not become one. [`RESTORE_ENV`]'s cap is
/// measured never to bind, so `sigma^2` is the only variable that actually
/// changes this filter's strength, and a trade curve therefore has to be swept
/// along it. The calibrated value stays the default at `1.0`; this exists so
/// the curve can be produced without editing the noise model, and so that the
/// number which decides the behaviour is set in one obvious place rather than
/// by a constant someone guessed.
///
/// Deliberately NOT a silent fallback on a bad value. A measurement instrument
/// that quietly substitutes 1.0 when it is misconfigured produces a curve that
/// is wrong in a way nobody can see, which is worse than no curve.
pub const RESTORE_SIGMA_ENV: &str = "STREHL_RESTORE_SIGMA";

/// The `sigma^2` multiplier from [`RESTORE_SIGMA_ENV`]; `1.0` when unset.
///
/// # Panics
/// If the variable is set to something that is not a finite positive number.
pub fn sigma_scale_from_env() -> f64 {
    let Ok(raw) = std::env::var(RESTORE_SIGMA_ENV) else {
        return 1.0;
    };
    let raw = raw.trim();
    if raw.is_empty() {
        return 1.0;
    }
    match raw.parse::<f64>() {
        Ok(v) if v.is_finite() && v > 0.0 => v,
        _ => panic!(
            "{RESTORE_SIGMA_ENV}={raw:?} is not a finite positive number. It scales the \
             calibrated noise variance and so decides how hard the restoration sharpens; \
             refusing rather than assuming 1.0, because a mis-set instrument that reads \
             plausibly is worse than one that stops."
        ),
    }
}

/// Everything the writer needs, bundled so that wiring costs the shared file
/// exactly one parameter.
///
/// Carries the noise model rather than a number because the brief is explicit
/// that sigma^2 comes from the calibration and is never chosen to make a
/// result land.
pub struct RestorePlan<'a> {
    /// The resampler the gather ACTUALLY used -- the sidecar's, not
    /// `--resampler`'s. Handing it the wrong one restores the wrong MTF, which
    /// is the mistake this field's doc on [`RestoreConfig`] already warns about.
    pub resampler: Resampler,
    pub gain_cap: f64,
    pub noise: &'a crate::noise::NoiseModel,
}

impl RestorePlan<'_> {
    /// The Wiener regulariser for one plane, in the units the writer holds.
    ///
    /// `mean_dn` is the plane's own black-subtracted mean and `scale` is the
    /// factor the writer already applied to reach those units, so the variance
    /// carries across by `scale^2`.
    ///
    /// This is the SINGLE-FRAME variance. The merge has already reduced the
    /// noise, so it OVERSTATES what is actually present and the filter is more
    /// conservative than the calibration strictly permits. That direction is
    /// deliberate: the failure mode under guard is overshoot at an edge, and
    /// over-regularising cannot cause overshoot.
    pub fn sigma2(&self, p: crate::CfaPlane, mean_dn: f32, scale: f64) -> f64 {
        self.noise.variance(p, mean_dn.max(0.0)) as f64 * scale * scale * sigma_scale_from_env()
    }

    /// `grid_factor` is 1.0 because the CFA planes ARE the gather grid: one
    /// sample per quad per plane, which is the grid the loss happened on.
    pub fn config(&self, sigma2: f64) -> RestoreConfig {
        RestoreConfig {
            resampler: self.resampler,
            grid_factor: 1.0,
            sigma2,
            gain_cap: self.gain_cap,
        }
    }
}
