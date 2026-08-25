//! Undo the resampling kernel — a single-image Wiener restoration whose `H` is
//! **our own interpolator**, not a model of a lens.
//!
//! # Status: BUILT, MEASURED, and NOT WIRED IN. Read §"The verdict" first.
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
    /// The gain applied at one frequency, given the local signal power.
    ///
    /// `signal_power` is `S(f)`: the image's own power at this frequency, which
    /// is why this is self-calibrating and needs no lens model and no scene
    /// prior. Where the image has no signal left, `sigma^2/S` explodes and the
    /// gain returns to 1 — the estimator declining, on its own evidence, to
    /// amplify a frequency that is only noise.
    pub fn gain(&self, f: f64, signal_power: f64) -> f64 {
        if !(signal_power > 0.0) || !self.gain_cap.is_finite() {
            return 1.0;
        }
        let h = gather_mtf(self.resampler, f * self.grid_factor);
        if h <= 1e-6 {
            return 1.0;
        }
        let g = h / (h * h + self.sigma2 / signal_power);
        g.clamp(1.0, self.gain_cap.max(1.0))
    }

    /// Separable 2-D gain. The gather is separable, so its correction is too.
    pub fn gain_2d(&self, fx: f64, fy: f64, signal_power: f64) -> f64 {
        if !(signal_power > 0.0) {
            return 1.0;
        }
        let h = gather_mtf(self.resampler, fx.abs() * self.grid_factor)
            * gather_mtf(self.resampler, fy.abs() * self.grid_factor);
        if h <= 1e-6 {
            return 1.0;
        }
        (h / (h * h + self.sigma2 / signal_power)).clamp(1.0, self.gain_cap.max(1.0))
    }
}

/// The two facts that hold for **any** interpolating kernel, checked rather
/// than assumed. Exposed so a caller can run it, not only the test harness.
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

    #[test]
    fn kernels_are_interpolating_and_preserve_dc() {
        selftest().unwrap();
    }

    #[test]
    fn catmull_rom_matches_the_measured_mtf() {
        // The values BUILD-SHARP's diagnosis is quoted against. If a kernel
        // ever changes, this fails and the report's numbers are stale.
        for (f, want) in [(0.25, 0.9402), (0.40, 0.7425), (0.50, 0.6251)] {
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
}
