#!/usr/bin/env python3
"""Independent check of BUILD-SHARP's co-site prediction, from the kernel alone.

BUILD-SHARP (§20 of docs/research/BUILD-SHARP.md) found that the viewable render
applies a fixed phi=0.25 chroma co-site shift on BOTH axes, SERIALLY after the
alignment gather, and predicted that folding it into the gather instead would
recover 1.128 / 1.438 / 2.004 x amplitude on R/B at f = 0.25 / 0.35 / 0.50.

A code change is about to ship on that number, so it gets checked from the
kernel rather than taken on trust -- the same way the Catmull-Rom "free blur"
hypothesis was killed in section 43.  Nothing here imports project code.

The arithmetic being checked:

  * A separable Catmull-Rom resample at phase phi has 1-D frequency response
    H(f, phi) = sum_k w_k(phi) exp(-2 pi i f (k - 1 + phi_offset)).  Amplitude
    retained is |H|.
  * Applied on both axes, the cost is |H|^2 for an isotropic feature at f.
  * Two SERIAL resamples multiply their responses.  One FOLDED resample pays
    only the composed transform's own response.
  * So the recoverable factor is exactly the co-site's own 2-D amplitude,
    1 / |H(f, 0.25)|^2 ... to the extent that folding a constant 0.25 into a
    near-uniform phase distribution does not itself cost anything, which
    BUILD-SHARP measured separately as 0.6 / 2.0 / 5.3%.

If this reproduces 1.128 / 1.438 / 2.004 the prediction is sound as arithmetic
and the remaining risk is entirely in the implementation, not the theory.
"""
from __future__ import annotations

import numpy as np


def cr_taps(phi: float, a: float = -0.5) -> np.ndarray:
    x = phi
    d = np.array([x + 1.0, x, 1.0 - x, 2.0 - x])
    w = np.empty(4)
    for i, t in enumerate(d):
        if t <= 1.0:
            w[i] = (a + 2.0) * t**3 - (a + 3.0) * t**2 + 1.0
        else:
            w[i] = a * t**3 - 5.0 * a * t**2 + 8.0 * a * t - 4.0 * a
    return w


def amp(f: float, phi: float) -> float:
    """Amplitude retained by a 1-D Catmull-Rom resample at phase phi."""
    w = cr_taps(phi)
    off = np.array([-1.0, 0.0, 1.0, 2.0]) - phi
    return float(abs((w * np.exp(-2j * np.pi * f * off)).sum()))


def main() -> int:
    print("sanity: taps at phi=0 must be the exact identity")
    t0 = cr_taps(0.0)
    print(f"  taps(0)      = {t0}")
    print(f"  exact [0,1,0,0]? {np.array_equal(t0, np.array([0.0, 1.0, 0.0, 0.0]))}")
    print(f"  sum taps(.25) = {cr_taps(0.25).sum():.12f}")
    print(f"  amp(f, phi=0) at .25/.35/.50 = "
          f"{amp(0.25,0):.6f} {amp(0.35,0):.6f} {amp(0.50,0):.6f}\n")

    print("the co-site: phi=0.25 on BOTH axes, applied serially")
    hdr = f"{'f':>6s} {'1-D amp':>9s} {'2-D amp':>9s} {'recover 1/2-D':>14s}"
    print(hdr)
    print("-" * len(hdr))
    pred = {0.25: 1.128, 0.35: 1.438, 0.50: 2.004}
    rows = []
    for f in (0.25, 0.35, 0.50):
        a1 = amp(f, 0.25)
        a2 = a1 * a1
        rec = 1.0 / a2 if a2 else float("inf")
        rows.append((f, a1, a2, rec))
        print(f"{f:6.2f} {a1:9.6f} {a2:9.6f} {rec:14.4f}")

    print(f"\n{'f':>6s} {'mine':>9s} {'BUILD-SHARP':>12s} {'delta':>9s} {'':>8s}")
    ok = 0
    for (f, _, _, rec) in rows:
        p = pred[f]
        d = rec - p
        good = abs(d) / p < 0.05
        ok += good
        print(f"{f:6.2f} {rec:9.4f} {p:12.4f} {d:+9.4f} "
              f"{'MATCH' if good else 'DIVERGES':>8s}")

    print(f"\n{ok}/3 bands agree within 5%.")
    if ok == 3:
        print("The prediction is sound AS ARITHMETIC. Remaining risk is entirely")
        print("in the implementation -- sign of the offset, which planes it is")
        print("applied to, and whether the fold really replaces the serial call")
        print("rather than adding to it.")
    else:
        print("DIVERGENCE. Do not ship the code change on this number until the")
        print("discrepancy is explained -- one of the two derivations is wrong.")

    # The other half of the claim: folding a constant into a near-uniform phase
    # distribution should be nearly free.  BUILD-SHARP measured 0.6/2.0/5.3%.
    print("\ncontrol -- is folding +0.25 into a near-uniform phase free?")
    rng = np.random.default_rng(11)
    ph = rng.uniform(0.0, 1.0, 40000)
    print(f"{'f':>6s} {'plain':>9s} {'folded':>9s} {'cost':>8s}")
    for f in (0.25, 0.35, 0.50):
        base = np.mean([amp(f, p) for p in ph[:4000]])
        fold = np.mean([amp(f, (p + 0.25) % 1.0) for p in ph[:4000]])
        print(f"{f:6.2f} {base:9.6f} {fold:9.6f} {100*(base-fold)/base:7.2f}%")
    print("  (a near-uniform phase is invariant under a constant offset, so a")
    print("   small number here is the expected result and a large one would")
    print("   mean the distribution is NOT uniform and the fold is not free)")
    return 0 if ok == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
