#!/usr/bin/env python3
"""Does a sub-pixel Catmull-Rom shift explain the CA census placebo excursion?

The census placebo (§45.6, §46) compares the chroma std of a FLAT region before
and after lateral-CA correction.  It is supposed to read 1.0: a radial warp that
removes fringes should do nothing where there are no edges.  It does not read
1.0.  It reads as low as 0.80, and -- the part that killed the obvious
explanation -- it reads LOWEST on the subjects whose flat set is most genuinely
flat.  109MSDCF's flat set carries more chroma than its own edge set and its
placebo is 0.9999; foam's flat set carries 3% of its edge set's chroma and its
placebo is 0.8026.

The surviving mechanism is that a flat set is noise, and interpolation is a
low-pass filter.  Correcting CA resamples R and B (G is the reference and is
untouched), so the corrected arm's R and B noise is SMALLER than the source
arm's by the kernel's noise gain, and a std ratio reads that as improvement even
though not one fringe was removed.

This script tests that mechanism on synthetic noise with NO project code: build
white noise with per-channel variance matching a Bayer CFA (R and B quarter
sampled, G half sampled, so R/B carry ~2x the variance of G after demosaic),
shift R and B by the measured CA displacements with the same Catmull-Rom kernel
the pipeline uses, and report the resulting chroma std ratios.

If the predicted ratios bracket the observed placebo values, the excursion is
explained and the census edge numbers must be read against a noise-smoothing
floor rather than against 1.0.

Usage:
    python noisegain.py                    # default sweep
    python noisegain.py --dx-r 0.5 --dx-b 0.2
"""
from __future__ import annotations

import argparse

import numpy as np


def cr_taps(phi: float, a: float = -0.5) -> np.ndarray:
    """Catmull-Rom taps for fractional offset phi in [0,1), 4-tap support.

    Written from the basis polynomials, not from the project's code, so this is
    an independent evaluation of the same kernel.
    """
    x = phi
    # distances from the four sample centres at -1, 0, 1, 2
    d = np.array([x + 1.0, x, 1.0 - x, 2.0 - x])
    w = np.empty(4)
    for i, t in enumerate(d):
        if t <= 1.0:
            w[i] = (a + 2.0) * t**3 - (a + 3.0) * t**2 + 1.0
        else:
            w[i] = a * t**3 - 5.0 * a * t**2 + 8.0 * a * t - 4.0 * a
    return w


def noise_gain_1d(phi: float) -> float:
    """RMS gain a Catmull-Rom resample applies to white noise."""
    w = cr_taps(phi)
    return float(np.sqrt((w**2).sum()))


def shift2d(img: np.ndarray, dy: float, dx: float) -> np.ndarray:
    """Separable Catmull-Rom sub-pixel shift, wrap boundary."""
    out = img
    for axis, d in ((0, dy), (1, dx)):
        if d == 0.0:
            continue
        i0 = int(np.floor(d))
        phi = d - i0
        w = cr_taps(phi)
        acc = np.zeros_like(out)
        for k in range(4):
            acc += w[k] * np.roll(out, -(i0 + k - 1), axis=axis)
        out = acc
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--var-rb", type=float, default=2.0,
                    help="R/B noise variance relative to G (CFA sampling)")
    ap.add_argument("--seed", type=int, default=20260824)
    args = ap.parse_args()

    print("Catmull-Rom 1-D noise gain sqrt(sum tap^2) by phase")
    print(f"  {'phi':>6s} {'gain':>8s}")
    for phi in (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
        print(f"  {phi:6.2f} {noise_gain_1d(phi):8.4f}")

    rng = np.random.default_rng(args.seed)
    n = args.n
    sg = 1.0
    srb = float(np.sqrt(args.var_rb))
    G = rng.normal(0.0, sg, (n, n))
    R = rng.normal(0.0, srb, (n, n))
    B = rng.normal(0.0, srb, (n, n))

    print(f"\nsynthetic flat field {n}x{n}, sigma_G={sg:.3f}, sigma_R=sigma_B="
          f"{srb:.3f}  (R/B variance {args.var_rb:g}x G, CFA sampling)")
    print("G is the CA reference channel and is never resampled.\n")
    hdr = (f"{'dR (px)':>8s} {'dB (px)':>8s} | {'R-G':>8s} {'R-B':>8s} "
           f"{'B-G':>8s}")
    print(hdr)
    print("-" * len(hdr))

    for dr, db in ((0.05, 0.02), (0.1, 0.04), (0.2, 0.08), (0.3, 0.12),
                   (0.4, 0.16), (0.5, 0.2), (0.7, 0.28), (1.0, 0.4)):
        Rw = shift2d(R, 0.0, dr)
        Bw = shift2d(B, 0.0, db)
        row = []
        for a1, a2, b1, b2 in ((R, G, Rw, G), (R, B, Rw, Bw), (B, G, Bw, G)):
            row.append(float((b1 - b2).std() / (a1 - a2).std()))
        print(f"{dr:8.2f} {db:8.2f} | {row[0]:8.4f} {row[1]:8.4f} "
              f"{row[2]:8.4f}")

    print("\nobserved census placebos, worst rows:")
    print(f"  {'foam':<20s}   0.8026   0.8261   0.9766")
    print(f"  {'113MSDCF':<20s}   0.8530   0.9341   0.9948")
    print(f"  {'112MSDCF':<20s}   0.8809   0.9401   0.9906")
    print(f"  {'couch-fibers-cpl':<20s}   0.8983   0.9663   0.9961")
    print("\nIf the synthetic table brackets those triples -- same ordering, "
          "R-G lowest and B-G nearest 1 -- the placebo excursion is a noise\n"
          "gain artefact of the resample, not a failure of the comparison.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
