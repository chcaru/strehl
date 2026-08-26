"""Which nonlinearity breaks the commutation? A 2x2, because I have now been
wrong twice about this operator and a single arm cannot separate the causes.

Established so far (restore_placement.py):
  - restore does NOT commute with a fixed-weight mean: 44.08 DN on a 2600 DN
    signal, where float precision would be < 1e-3 DN.
  - it is NOT driven by per-frame noise: dividing the noise by 100 left the
    gap at x0.8923.

Two candidates remain and they are separable:
  A. SPECTRAL FIT. design_fir fits the filter to each plane's own spectrum.
     Frames blurred at DIFFERENT phases have different spectra even when
     noise-free, so each gets a different filter. Isolate by giving every
     frame the SAME phase: then the planes are identical up to noise.
  B. GAIN CAP. gain_cap clips the designed response. Clipping is a
     nonlinearity all by itself, independent of any fit. Isolate by raising
     the cap far above any gain the design will request.

Factorial, so an interaction cannot hide inside either main effect.
"""

from __future__ import annotations

import numpy as np

from restore_placement import gather_blur, restore, scene


def gap(phases, cap, sigma, rng):
    truth = scene(192, 192)
    clean = np.stack([gather_blur(truth, p) for p in phases])
    frames = clean + rng.normal(0.0, sigma, clean.shape)
    fx = np.full(len(phases), 1.0 / len(phases))
    mf = restore((frames * fx[:, None, None]).sum(axis=0), sigma ** 2 if sigma else 144.0, cap)
    ef = (np.stack([restore(f, sigma ** 2 if sigma else 144.0, cap) for f in frames])
          * fx[:, None, None]).sum(axis=0)
    return float(np.abs(mf - ef).max())


def main() -> int:
    K = 8
    varied = np.random.default_rng(11).uniform(0.15, 0.85, K)
    equal = np.full(K, 0.5)
    print("max |R(mean) - mean(R)| in DN, signal range 2600 DN, K=8")
    print("float precision would be < 1e-3\n")
    print(f"{'':24s}{'cap=1.4':>14s}{'cap=1e6 (off)':>16s}")
    for label, ph, sig in (("varied phase, noisy", varied, 12.0),
                           ("varied phase, quiet", varied, 0.12),
                           ("EQUAL phase, noisy", equal, 12.0),
                           ("EQUAL phase, quiet", equal, 0.12)):
        row = [gap(ph, c, sig, np.random.default_rng(7)) for c in (1.4, 1e6)]
        print(f"{label:24s}{row[0]:14.6e}{row[1]:16.6e}")
    print("\nReading: a row that collapses to ~0 names the cause of that row's")
    print("difference. 'EQUAL phase, quiet' is the null -- the planes are then")
    print("identical, so ANY gap there is a harness bug, not a finding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
