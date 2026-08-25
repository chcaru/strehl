"""Commission halfspec.py on synthetic data where the answer is known.

An instrument that has not been shown to respond to the thing it claims to measure,
AND to stay quiet when that thing is absent, is not an instrument.  Five checks:

  1. SIGNAL REJECTION  a strong structured scene common to both arms must cancel;
                       the difference must look like the pure-noise case.
  2. LEVEL LINEARITY   doubling the noise sd must quadruple the measured power.
  3. FLATNESS          white noise must measure flat across frequency.
  4. CORRELATION       blurred (correlated) noise must measure as falling with f.
                       This is the capability the whole exercise depends on -- the
                       real merged noise IS correlated and the previous calibration
                       failed precisely by mismodelling that.
  5. OFFSET GUARD      a planted 3 px shift must be detected, not silently
                       differenced into a huge fake "noise" spectrum.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from halfspec import integer_offset, radial_power, structure_score  # noqa: E402

RNG = np.random.default_rng(20260825)
N = 1024
TILE = 256


def scene() -> np.ndarray:
    """A structured 'scene': bars, a disc and a gradient. Strong, and identical in
    both arms, so a working instrument must cancel it entirely."""
    y, x = np.mgrid[0:N, 0:N]
    s = 8000.0 + 3000.0 * np.sign(np.sin(x / 11.0))
    s += 6000.0 * ((y - 400) ** 2 + (x - 600) ** 2 < 150 ** 2)
    s += 12.0 * y
    return np.repeat(s[:, :, None], 3, axis=2)


def white(sd: float) -> np.ndarray:
    return RNG.normal(0.0, sd, (N, N, 3))


def blurred(sd: float, k: int = 4) -> np.ndarray:
    """Correlated noise: white noise box-averaged, which is what averaging many
    frames through a resampling kernel does to it."""
    n = RNG.normal(0.0, sd, (N + k, N + k, 3))
    acc = np.zeros((N, N, 3))
    for dy in range(k):
        for dx in range(k):
            acc += n[dy:dy + N, dx:dx + N]
    return acc / k


def flat_power(d: np.ndarray) -> tuple[float, float]:
    f, p, _ = radial_power(d[:, :, 1], tile=TILE)
    m = (f > 0.05) & (f < 0.45)
    return float(np.mean(p[m])), float(np.max(p[m]) / max(np.min(p[m]), 1e-30))


def slope(d: np.ndarray) -> float:
    f, p, _ = radial_power(d[:, :, 1], tile=TILE)
    m = (f > 0.06) & (f < 0.45) & (p > 0)
    return float(np.polyfit(np.log(f[m]), np.log(p[m]), 1)[0])


def main() -> int:
    fails = []
    S = scene()

    # 1. signal rejection ----------------------------------------------------
    a, b = S + white(50.0), S + white(50.0)
    p_scene, _ = flat_power(a - b)
    p_bare, _ = flat_power(white(50.0) - white(50.0))
    ratio = p_scene / p_bare
    ok = 0.95 < ratio < 1.05
    print(f"1 signal rejection   with-scene/bare power = {ratio:.4f}   "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("signal rejection")
    ss_scene = structure_score(a - b)
    ss_bare = structure_score(white(50.0) - white(50.0))
    print(f"    structure score   {ss_scene:.4f} vs bare {ss_bare:.4f} "
          f"(white-noise ref {1/64:.4f})")

    # 2. level linearity -----------------------------------------------------
    p1, _ = flat_power(white(50.0) - white(50.0))
    p2, _ = flat_power(white(100.0) - white(100.0))
    r = p2 / p1
    ok = 3.8 < r < 4.2
    print(f"2 level linearity    P(2sd)/P(sd) = {r:.4f} (expect 4.0)   "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("level linearity")

    # 3. flatness ------------------------------------------------------------
    _, spread = flat_power(white(50.0) - white(50.0))
    ok = spread < 1.25
    print(f"3 flatness           max/min bin = {spread:.4f} (expect ~1)   "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("flatness")

    # 4. correlation detection ----------------------------------------------
    s_white = slope(white(50.0) - white(50.0))
    s_corr = slope(blurred(50.0) - blurred(50.0))
    ok = abs(s_white) < 0.15 and s_corr < -1.0
    print(f"4 correlation        slope white = {s_white:+.3f}, "
          f"blurred = {s_corr:+.3f}   {'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("correlation detection")

    # 5. offset guard --------------------------------------------------------
    a = S + white(50.0)
    b = np.roll(np.roll(S + white(50.0), 3, axis=0), -2, axis=1)
    dy, dx, _ = integer_offset(a, b)
    ok = (dy, dx) == (3, -2)
    print(f"5 offset guard       detected dy={dy} dx={dx} (planted 3,-2)   "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("offset guard")

    print()
    if fails:
        print("COMMISSIONING FAILED: " + ", ".join(fails))
        return 1
    print("COMMISSIONING PASSED: 5/5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
