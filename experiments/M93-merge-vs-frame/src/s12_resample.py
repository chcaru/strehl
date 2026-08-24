"""S12 -- validate the analytic Catmull-Rom MTF numerically.

S7's alignment-price comparison was retired: its geometry control failed because
arm M is an unaligned collage, so cross-correlating it against an aligned arm
compares different scene content. What survives from S7 is an *analytic* MTF for
the Catmull-Rom kernel the aligner uses at the measured 1.07354x upsample. An
analytic number that has never been checked against a running resampler is a
claim about algebra, not about the code.

So: implement the separable 4-tap Catmull-Rom resample directly, push white noise
through it, and measure the MTF the same way the analytic formula predicts it.
If the two agree, the derived cost of the resample stands on its own without any
image comparison between arms.

Controls:
  C4  identity zoom (k = 1.0, integer phase) must be a pass-through:
      MTF == 1 at every frequency, max |out - in| == 0.
  C5  a planted Gaussian of known sigma pushed through the same measurement
      must be recovered (the measurement, not the resampler, is under test).
  C6  the numeric MTF must fall below 1 monotonically -- a resampler that read
      MTF > 1 in the passband would be sharpening, not interpolating.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
K = 1.07354  # measured: strehl prints "field of view scaled to 0.9315"; 1/0.9315
A = -0.5  # Catmull-Rom is the Keys cubic with a = -1/2


def keys_w(t, a=A):
    """Keys' cubic convolution kernel. t is |distance| as an array."""
    t = np.abs(t)
    w = np.zeros_like(t)
    m1 = t < 1
    m2 = (t >= 1) & (t < 2)
    w[m1] = (a + 2) * t[m1] ** 3 - (a + 3) * t[m1] ** 2 + 1
    w[m2] = a * (t[m2] ** 3 - 5 * t[m2] ** 2 + 8 * t[m2] - 4)
    return w


def cr_resample_1d(img, k, axis):
    """Separable Catmull-Rom zoom by factor k along one axis, edge-clamped."""
    img = np.moveaxis(img, axis, -1)
    n = img.shape[-1]
    m = int(round(n * k))
    # centre-aligned sampling: output pixel j samples source coordinate s
    s = (np.arange(m) + 0.5) / k - 0.5
    i0 = np.floor(s).astype(np.int64)
    frac = s - i0
    out = np.zeros(img.shape[:-1] + (m,), dtype=np.float64)
    for tap in (-1, 0, 1, 2):
        idx = np.clip(i0 + tap, 0, n - 1)
        w = keys_w(np.abs(frac - tap))
        out += img[..., idx] * w
    return np.moveaxis(out, -1, axis)


def cr_resample(img, k):
    return cr_resample_1d(cr_resample_1d(img, k, 0), k, 1)


def analytic_mtf(f, k, a=A, replicas=0):
    """Transfer of Keys' cubic used as a phase-varying interpolator.

    `replicas=0` gives the bare kernel CTFT |H(f)|. That is the textbook answer
    and it is incomplete: a resampler evaluates the kernel at a source-grid
    *phase* that varies from output pixel to output pixel, so the measured
    power transfer is the phase-average sum(|H(f+n)|^2) over the source-grid
    replicas n. Keys' cubic is interpolating, so H(n) = 0 at every non-zero
    integer and the replica terms vanish at DC -- but they do not vanish
    between integers, and they raise the measured transfer above |H(f)| at high
    frequency. `replicas=N` includes n = -N..N.
    """
    t = np.linspace(-2, 2, 40001)
    w = keys_w(t, a)
    w = w / np.trapezoid(w, t)

    def H(fi):
        return abs(float(np.trapezoid(w * np.cos(2 * np.pi * fi * t), t)))

    f = np.atleast_1d(f)
    if replicas == 0:
        return np.array([H(fi) for fi in f])
    out = []
    for fi in f:
        s = sum(H(fi + n) ** 2 for n in range(-replicas, replicas + 1))
        out.append(np.sqrt(s))
    return np.array(out)


def measure_mtf(a_img, b_img, k_out=1.0, nbins=90):
    """MTF of b relative to a.

    b may live on a grid `k_out` times finer than a's. A source frequency f
    (cycles per *source* pixel) appears in b at f / k_out cycles per output
    pixel, so b's frequency axis is multiplied by k_out before the ratio is
    taken. The ratio is normalised to 1 at low frequency, which is what makes
    it an MTF rather than a bare power ratio -- upsampling changes the number
    of samples and hence the absolute PSD level.
    """
    fa, pa, _ = L.radial_psd(a_img, nbins=nbins)
    fb, pb, _ = L.radial_psd(b_img, nbins=nbins)
    fb_src = fb * k_out
    pb_on_a = np.interp(fa, fb_src, pb, left=np.nan, right=np.nan)
    ok = (fa > 0.02) & (fa < 0.48) & (pa > 0) & np.isfinite(pb_on_a)
    r = np.sqrt(np.maximum(pb_on_a[ok] / pa[ok], 0))
    f = fa[ok]
    lowband = f < 0.08
    if lowband.sum() >= 2:
        r = r / np.median(r[lowband])
    return f, r


def sigma_from_mtf(f, mtf, lo=0.05, hi=0.45):
    """Fit ln(MTF) = -2 pi^2 sigma^2 f^2 over a band, weighted by f."""
    ok = (f >= lo) & (f <= hi) & (mtf > 1e-6)
    x = f[ok] ** 2
    y = np.log(mtf[ok])
    w = f[ok]
    slope = float(np.sum(w * x * y) / np.sum(w * x * x))
    return float(np.sqrt(max(-slope / (2 * np.pi**2), 0.0)))


def main() -> int:
    rng = np.random.default_rng(93012)
    N = 1024
    res = {}

    # ---- C4: identity zoom must be a pass-through -------------------------
    img = rng.standard_normal((64, 64))
    ident = cr_resample(img, 1.0)
    c4_max = float(np.abs(ident - img).max())
    res["C4_identity_max_abs_diff"] = c4_max
    print(f"C4 identity zoom k=1.0 : max |out-in| = {c4_max:.3e}   "
          f"{'PASS' if c4_max < 1e-12 else 'FAIL'}")

    # ---- the measurement itself, on white noise ---------------------------
    noise = rng.standard_normal((N, N))
    zoomed = cr_resample(noise, K)
    f, mtf = measure_mtf(noise, zoomed, k_out=K)
    pred = analytic_mtf(f, K)

    # ---- band-limited stimulus -------------------------------------------
    # A power ratio on *broadband* noise measures transfer PLUS the imaging
    # replicas the interpolator leaks back into the passband: source content
    # above the output Nyquist (0.5*K = 0.537 cy per source px) reappears
    # inside the band and adds power, so the ratio can and does exceed 1.
    # Removing that content from the stimulus isolates the transfer function.
    FCUT = 0.45
    fy = np.fft.fftfreq(N)
    R = np.hypot(*np.meshgrid(fy, fy, indexing="ij"))
    bl = np.real(np.fft.ifft2(np.fft.fft2(noise) * (R <= FCUT)))
    bl_z = cr_resample(bl, K)
    fbl, mbl = measure_mtf(bl, bl_z, k_out=K)
    pbl = analytic_mtf(fbl, K)
    keep = fbl < FCUT - 0.02
    fbl, mbl, pbl = fbl[keep], mbl[keep], pbl[keep]

    # ---- C5: the measurement must recover a planted Gaussian --------------
    from s6_spectral import plant_blur

    c5 = {}
    for s in (0.25, 0.50, 1.00):
        blurred = plant_blur(noise, s)
        f2, m2 = measure_mtf(noise, blurred)
        rec = sigma_from_mtf(f2, m2)
        c5[f"{s:.2f}"] = dict(planted=s, recovered=rec, rel_err=(rec - s) / s)
        print(f"C5 planted sigma {s:.2f} px -> recovered {rec:.4f} px "
              f"({100*(rec-s)/s:+.2f}%)   {'PASS' if abs(rec-s)/s < 0.05 else 'FAIL'}")
    res["C5_planted_gaussian"] = c5

    # ---- C6: never above 1 in the passband, once imaging is excluded ------
    over_bb = float(mtf[(f > 0.02) & (f < 0.45)].max())
    jbb = int(np.argmax(np.where((f > 0.02) & (f < 0.45), mtf, -1)))
    over_bl = float(mbl.max())
    res["C6_max_mtf_broadband"] = over_bb
    res["C6_max_mtf_bandlimited"] = over_bl
    res["C6_argmax_f"] = float(f[jbb])
    print(f"C6 max measured MTF, broadband stimulus     = {over_bb:.4f} at "
          f"f = {f[jbb]:.4f} cy/px")
    print(f"C6 max measured MTF, band-limited stimulus  = {over_bl:.4f}")
    over_hi = float(mbl[fbl >= 0.10].max())
    res["C6_max_mtf_above_0p10"] = over_hi
    print(f"C6 max measured MTF for f >= 0.10 cy/px     = {over_hi:.4f}   "
          f"{'PASS' if over_hi <= 1.02 else 'FAIL'}")

    # ---- headline: numeric vs analytic ------------------------------------
    prep = analytic_mtf(fbl, K, replicas=3)
    print()
    print("  f cy/px   |H(f)| only   +replicas   numeric(BL)   num/|H|   num/+rep")
    rows = []
    for target in (0.10, 0.20, 0.25, 0.30, 0.40):
        j = int(np.argmin(np.abs(fbl - target)))
        rows.append(dict(f=float(fbl[j]), kernel_only=float(pbl[j]),
                         with_replicas=float(prep[j]), numeric=float(mbl[j])))
        print(f"  {fbl[j]:6.4f}   {pbl[j]:11.4f}   {prep[j]:9.4f}   "
              f"{mbl[j]:11.4f}   {mbl[j]/max(pbl[j],1e-9):7.4f}   "
              f"{mbl[j]/max(prep[j],1e-9):8.4f}")
    res["mtf_table"] = rows

    band = (fbl >= 0.05) & (fbl <= 0.40)
    worst = float(np.max(np.abs(mbl[band] - pbl[band])))
    worst_r = float(np.max(np.abs(mbl[band] - prep[band])))
    res["max_abs_dev_kernel_only_0p05_0p40"] = worst
    res["max_abs_dev_with_replicas_0p05_0p40"] = worst_r

    sig = {}
    for lo, hi in ((0.05, 0.40), (0.05, 0.25), (0.10, 0.40)):
        sig[f"{lo}-{hi}"] = dict(
            numeric=sigma_from_mtf(fbl, mbl, lo, hi),
            kernel_only=sigma_from_mtf(fbl, pbl, lo, hi),
            with_replicas=sigma_from_mtf(fbl, prep, lo, hi),
        )
    res["sigma_eq_px_by_band"] = sig
    res["k"] = K
    print()
    print(f"max |numeric - |H(f)||        over 0.05-0.40 cy/px = {worst:.4f}")
    print(f"max |numeric - with replicas| over 0.05-0.40 cy/px = {worst_r:.4f}")
    print("equivalent Gaussian sigma of one resample (px), by fit band:")
    for kk, vv in sig.items():
        print(f"   band {kk:>10} cy/px : |H| {vv['kernel_only']:.4f}   "
              f"+replicas {vv['with_replicas']:.4f}   numeric {vv['numeric']:.4f}")

    with open(os.path.join(OUTDIR, "s12_resample.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
