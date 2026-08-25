"""BUILD-SHARP: undo the resampling kernel, not the optics.

Prototype for `crates/strehl-core/src/restore.rs`. Python first, deliberately,
because the failure mode of every deconvolution is RINGING and ringing is
graded by eye, not by a statistic (brief rule: the pictures are right).

# What is being deconvolved, and why this is not M115 or M20 again

M115 measured a multi-frame Wiener against the shipped gate and got
`R_SNR = 1.0014 +/- 0.0184` -- nothing. M20 measured it winning on 15.1% of
pixels and concluded the prize is noise, not detail. Both asked: *does
combining K frames beat selecting the best one?* M70 answered why not -- the
through-focus band matrix is rank-1 to 0.9959, so the frames are redundant and
there is no extra information to harvest.

This asks a different and much smaller question: **the merge applied one
resampling gather with a kernel we wrote ourselves; can we undo it?**

That difference matters because it changes what `H` is:

| | M115 / M20 | here |
| --- | --- | --- |
| `H` | a MODEL of the optics (defocus (x) diffraction) | the interpolation kernel, in closed form |
| known to | a fitted magnification and an assumed pupil | exactly, it is our own code |
| what is recovered | information no frame contains | attenuation we ourselves applied |

There is no model risk. `H` here is not a hypothesis about a lens; it is
`sample_catmull_rom` written in the Fourier domain. If the estimate is wrong,
the code is wrong, and a planted round-trip catches it.

# Size of the prize, measured before building anything

BUILD-SHARP's paired ESF rise (M88b's instrument, floor 0.6699 um), pooled over
the three admitted ROIs, reference = gate-0 catmull-rom:

    nearest-neighbour gather   +2.333 um   (sharper, but aliased)
    lanczos-3 gather           -0.045 um   (NOTHING)

Lanczos-3 recovers none of it, which is the whole reason a *filter* is the
answer rather than a better *kernel*: what catmull-rom costs is passband
attenuation, and no interpolator with a compact support avoids it. Under
`rise^2 = shared^2 + a^2` the nearest-vs-catmull gap is `a = 14.97 um`, which is
18.6% of the shipped merge's blur variance.

# The estimator

    G(f) = conj(H(f)) / ( |H(f)|^2 + sigma^2 / S(f) )

the brief's formula with `K = 1`, which is what the rank-1 result says the
multi-frame case collapses to anyway. `sigma^2/S(f)` is the inverse SNR: it
makes the gain exactly as aggressive as the noise permits, and it is what stops
this being a naive `1/H` that amplifies the noise floor by 3x at Nyquist.

# `H`, and the one place this is an approximation

A gather samples each output pixel at its OWN sub-pixel phase `phi`, so the
operation is NOT shift-invariant and has no single OTF. What it has is an
expected attenuation:

    M(f) = mean over phi in [0,1) of | sum_n k(n - phi) exp(2 pi i f (n - phi)) |

and correcting by `M` is the minimum-mean-square LINEAR correction available
without knowing each pixel's phase. This is stated rather than hidden: the
residual is a phase-dependent term this filter does not touch, and it is the
reason the recovery is partial by construction.

The gather runs on the CFA QUAD plane and the demosaic then doubles the grid
(M95 P56), so a cycle-per-pixel in the output is half a cycle-per-pixel to the
kernel. `--grid demosaic` applies that factor of two. Getting it backwards
doubles the correction and is the most likely way to make this ring, so it is
a flag with a stated default rather than an inline constant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))


# ---------------------------------------------------------------------------
# the kernels, in closed form
# ---------------------------------------------------------------------------

def k_catmull_rom(t):
    """Catmull-Rom (cubic, a = -0.5). Must match `align.rs::sample_catmull_rom`."""
    t = np.abs(np.asarray(t, float))
    out = np.zeros_like(t)
    m1 = t < 1.0
    m2 = (t >= 1.0) & (t < 2.0)
    out[m1] = 1.5 * t[m1] ** 3 - 2.5 * t[m1] ** 2 + 1.0
    out[m2] = -0.5 * t[m2] ** 3 + 2.5 * t[m2] ** 2 - 4.0 * t[m2] + 2.0
    return out


def k_lanczos3(t):
    t = np.asarray(t, float)
    out = np.sinc(t) * np.sinc(t / 3.0)
    return np.where(np.abs(t) < 3.0, out, 0.0)


KERNELS = {"catmull-rom": (k_catmull_rom, 2), "lanczos3": (k_lanczos3, 3)}


def gather_mtf(f, kernel="catmull-rom", n_phase=64):
    """Phase-averaged MTF of one gather, at normalised frequency `f` cyc/sample.

    `f` may be any shape; the return has the same shape. Validated against the
    two values that must hold for ANY interpolating kernel:
      M(0) = 1 exactly (a gather preserves DC), and
      at phi = 0 the kernel is the Kronecker delta, so M is 1 at every f.
    `--selftest` asserts both.
    """
    k, sup = KERNELS[kernel]
    f = np.asarray(f, float)
    phis = (np.arange(n_phase) + 0.5) / n_phase
    taps = np.arange(-sup + 1, sup + 1, dtype=float)
    acc = np.zeros(f.shape, dtype=float)
    for phi in phis:
        w = k(taps - phi)
        w = w / w.sum()
        # sum_n w_n exp(2 pi i f (n - phi)); the exp(-2 pi i f phi) common
        # factor is a pure shift and drops out of the magnitude.
        h = np.tensordot(w, np.exp(2j * np.pi * np.multiply.outer(taps, f)), axes=(0, 0))
        acc += np.abs(h)
    return acc / n_phase


# ---------------------------------------------------------------------------
# the restoration filter
# ---------------------------------------------------------------------------

def radial_psd(img):
    """Radially averaged power spectrum, as a function of |f| in cyc/px."""
    F = np.fft.fftshift(np.fft.fft2(img - img.mean()))
    P = (F.real ** 2 + F.imag ** 2) / img.size
    h, w = img.shape
    fy = np.fft.fftshift(np.fft.fftfreq(h))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(w))[None, :]
    r = np.hypot(fy, fx)
    nb = 256
    idx = np.clip((r / 0.7072 * nb).astype(int), 0, nb - 1)
    num = np.bincount(idx.ravel(), P.ravel(), minlength=nb)
    den = np.bincount(idx.ravel(), minlength=nb).astype(float)
    prof = num / np.maximum(den, 1)
    centres = (np.arange(nb) + 0.5) / nb * 0.7072
    return centres, prof


def wiener_gain(fy, fx, kernel, grid_factor, sigma2, S_of_r, gain_cap):
    """G(f) = conj(H)/(|H|^2 + sigma^2/S), separable H, with a hard gain cap.

    `H` is real and non-negative here (a phase-averaged magnitude), so
    `conj(H) = H` and the filter is zero-phase: it cannot displace an edge, only
    change its contrast. That is a deliberate property -- a filter with phase
    could move geometry, and geometry is what alignment is for.

    `gain_cap` is the guard the brief requires, in its bluntest form. Where the
    Wiener gain would exceed it, the filter is clamped, so a frequency the
    gather nearly annihilated cannot be resurrected out of the noise floor. The
    fallback is the IDENTITY, which is what "never worse than the input" means
    for a restoration: at cap = 1.0 this function is a no-op by construction.
    """
    Hy = gather_mtf(np.abs(fy) * grid_factor, kernel)
    Hx = gather_mtf(np.abs(fx) * grid_factor, kernel)
    H = Hy * Hx
    r = np.hypot(fy, fx)
    S = np.interp(r, S_of_r[0], np.maximum(S_of_r[1], 1e-12))
    G = H / (H * H + sigma2 / S)
    return np.clip(G, 1.0, gain_cap)


def restore(img, kernel="catmull-rom", grid_factor=2.0, noise_sd=None,
            gain_cap=2.0):
    """Apply the restoration to one linear plane. Returns (out, diagnostics)."""
    img = np.asarray(img, float)
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]

    cen, prof = radial_psd(img)
    if noise_sd is None:
        # The noise floor read off the image's own spectrum: the top decile of
        # frequency, where a macro subject at this rig's measured MTF has no
        # signal left (M88: MTF at Nyquist is 0.036 at f/5.6). Reported, so a
        # caller can see what was assumed rather than inherit it silently.
        tail = prof[int(0.9 * len(prof)):]
        sigma2 = float(np.median(tail))
    else:
        sigma2 = float(noise_sd) ** 2 / img.size * (h * w)
    G = wiener_gain(fy, fx, kernel, grid_factor, sigma2, (cen, prof), gain_cap)
    out = np.fft.ifft2(np.fft.fft2(img) * G).real
    # Gain on the frequency axis, read straight off the assembled 2-D filter
    # along fx (fy = 0), so the number reported is the number applied.
    row = G[0, : w // 2]
    ax = np.fft.fftfreq(w)[: w // 2]
    diag = {
        "sigma2": sigma2,
        "gain_max": float(G.max()),
        "gain_at_0.10": float(np.interp(0.10, ax, row)),
        "gain_at_0.25": float(np.interp(0.25, ax, row)),
        "gain_at_0.45": float(np.interp(0.45, ax, row)),
        "mtf_at_0.25": float(gather_mtf(np.array([0.25 * grid_factor]), kernel)[0]),
        "mtf_at_0.5": float(gather_mtf(np.array([0.5 * grid_factor]), kernel)[0]),
    }
    return out, diag


def selftest():
    ok = True
    for name in KERNELS:
        m0 = gather_mtf(np.array([0.0]), name)[0]
        print(f"{name:14} M(0) = {m0:.10f}  (must be 1)")
        ok &= abs(m0 - 1.0) < 1e-9
        for f in (0.1, 0.2, 0.25, 0.3, 0.4, 0.5):
            print(f"{'':14} M({f:.2f}) = {gather_mtf(np.array([f]), name)[0]:.4f}")
    # A gather at phase 0 is the identity, so its MTF must be 1 everywhere.
    k, sup = KERNELS["catmull-rom"]
    taps = np.arange(-sup + 1, sup + 1, dtype=float)
    w = k(taps - 0.0)
    print(f"\nphase-0 taps  = {np.round(w, 6)}  (must be a Kronecker delta)")
    ok &= np.allclose(w, (taps == 0.0).astype(float))
    # Round trip: blur a plant by the modelled MTF, restore, recover.
    rng = np.random.default_rng(0)
    n = 512
    img = rng.normal(0, 1, (n, n))
    img = np.cumsum(np.cumsum(img, 0), 1)          # 1/f^2-ish, like a photo
    img = (img - img.mean()) / img.std() * 1000 + 8000
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    H = gather_mtf(np.abs(fy) * 1.0) * gather_mtf(np.abs(fx) * 1.0)
    blurred = np.fft.ifft2(np.fft.fft2(img) * H).real
    got, _ = restore(blurred, grid_factor=1.0, gain_cap=100.0)
    e0 = np.std(blurred - img) / np.std(img)
    e1 = np.std(got - img) / np.std(img)
    print(f"\nround trip: rel err before {e0:.5f} -> after {e1:.5f} "
          f"(recovery {1 - e1 / e0:.1%})")
    ok &= e1 < 0.25 * e0
    print("\nSELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--mtf-table", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.mtf_table:
        fs = np.array([0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5])
        print(f"{'f cyc/px':>9} " + " ".join(f"{k:>12}" for k in KERNELS))
        for f in fs:
            row = " ".join(f"{gather_mtf(np.array([f]), k)[0]:12.4f}" for k in KERNELS)
            print(f"{f:9.2f} {row}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
