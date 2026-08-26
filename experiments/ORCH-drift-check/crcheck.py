#!/usr/bin/env python3
"""Is Catmull-Rom at zero phase the exact identity?

BUILD-SHARP refuted my blue-channel "free blur" hypothesis by asserting that
Catmull-Rom is an INTERPOLATING kernel whose taps at phase 0 are exactly
[0, 1, 0, 0], so there is no fixed interpolation cost that a skip-guard could
avoid -- the cost is a function of phase that vanishes at 0.

That refutation kills a code change I asked for, so I check it myself rather
than take it. Analytic derivation and numeric evaluation, no project code.

Catmull-Rom basis:
  p(t) = 0.5 * [ (-t^3 + 2t^2 - t) P0
               + ( 3t^3 - 5t^2 + 2) P1
               + (-3t^3 + 4t^2 + t) P2
               + (   t^3 -  t^2   ) P3 ]

At t=0 that is 0.5 * [0, 2, 0, 0] = P1 exactly.
"""
from __future__ import annotations

import numpy as np


def catmull_rom_taps(t: float) -> np.ndarray:
    return 0.5 * np.array([
        -t ** 3 + 2 * t ** 2 - t,
        3 * t ** 3 - 5 * t ** 2 + 2,
        -3 * t ** 3 + 4 * t ** 2 + t,
        t ** 3 - t ** 2,
    ])


def response(t: float, f: float) -> float:
    """Magnitude response at normalised frequency f (cycles/sample) for phase t."""
    w = catmull_rom_taps(t)
    n = np.array([-1.0, 0.0, 1.0, 2.0])
    # Shift-compensated: divide out the intended linear phase so what is left
    # is amplitude error, not the shift itself.
    h = np.sum(w * np.exp(-2j * np.pi * f * (n - t)))
    return float(np.abs(h))


def main() -> int:
    print("taps at phase 0 :", catmull_rom_taps(0.0))
    print("taps at phase 0.5:", catmull_rom_taps(0.5))
    print("sum of taps, phase 0..1 in 0.1 steps:",
          [round(float(catmull_rom_taps(t).sum()), 12) for t in np.arange(0, 1.01, 0.1)])
    print()

    print(f"{'phase px':>10s} {'f=0.25':>10s} {'f=0.35':>10s} {'f=0.50':>10s}")
    print("-" * 44)
    for t in (0.0, 0.039, 0.152, 0.25, 0.5):
        print(f"{t:10.3f} {response(t, 0.25):10.6f} "
              f"{response(t, 0.35):10.6f} {response(t, 0.50):10.6f}")

    print()
    ident = catmull_rom_taps(0.0)
    exact = np.array_equal(ident, np.array([0.0, 1.0, 0.0, 0.0]))
    print(f"phase-0 taps are EXACTLY [0,1,0,0]: {exact}")

    # What phase would be needed to lose 9.36% amplitude at f=0.35?
    ts = np.linspace(0, 0.5, 20001)
    r = np.array([response(t, 0.35) for t in ts])
    need = ts[np.argmin(np.abs(r - (1 - 0.0936)))]
    print(f"phase needed for a 9.36% amplitude loss at f=0.35: {need:.4f} px")
    print(f"blue's measured radial displacement:                0.0390 px")
    print(f"ratio: {need / 0.039:.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
