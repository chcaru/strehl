"""Attenuation bias is falsified. The real explanation is ALIASING -- and if it
is, the shortfall is itself evidence for the headline.

s7 planted a shift by resampling one band-limited array, so G1 and G2 were
related by an exact phase ramp and the scan read +0.50 at every SNR down to
hf SNR 0.45. Real photosites are not related that way: each of G1 and G2 samples
a *continuous* scene on its own half-density grid, so each **aliases** whatever
lies above its Nyquist, and aliased energy folds down carrying a phase that does
not obey the ramp. That drags the recovered offset toward zero.

Prediction, made before running: sampling a true quincunx from a scene that has
no content above the binned Nyquist must recover +0.50, and adding above-Nyquist
content must pull the recovered value down toward the +0.40..+0.45 the real
frames give. If that ladder reproduces, the shortfall is aliasing -- which is a
direct, independent demonstration that the capture carries above-Nyquist detail.
"""

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6_signal import geometry_scan  # noqa: E402


def scene_fullres(rng, n2, fmax, slope=1.6, knee=0.03):
    """A scene on the FULL-RES grid, band-limited at `fmax` full-res cyc/px."""
    fy = np.fft.fftfreq(n2)[:, None] * np.ones((1, n2))
    fx = np.fft.fftfreq(n2)[None, :] * np.ones((n2, 1))
    r = np.hypot(fy, fx)
    F = np.fft.fft2(rng.standard_normal((n2, n2)))
    F *= 1.0 / (1.0 + (r / knee) ** slope)
    F[r > fmax] = 0
    s = np.real(np.fft.ifft2(F))
    return 500 * s / (s.std() + 1e-12)


def main():
    rng = np.random.default_rng(818181)
    n2 = 768                     # full-res grid; binned planes are 384
    print("binned Nyquist is 0.25 cyc/full-res px. Sampling a TRUE quincunx.\n")
    print("%14s %10s %14s" % ("scene fmax", "above Nyq", "recovered d"))
    rows = []
    for fmax in (0.12, 0.20, 0.25, 0.30, 0.35, 0.45, 0.50):
        sc = scene_fullres(rng, n2, fmax)
        noisy = sc + rng.standard_normal((n2, n2)) * 25.0
        g1 = noisy[0::2, 1::2]
        g2 = noisy[1::2, 0::2]
        got = geometry_scan(g1, g2)
        rows.append({"fmax": fmax, "above_nyquist": fmax > 0.25, "recovered": got})
        print("%14.2f %10s %14.2f" % (fmax, "yes" if fmax > 0.25 else "no", got))

    below = [r["recovered"] for r in rows if not r["above_nyquist"]]
    above = [r["recovered"] for r in rows if r["above_nyquist"]]
    print("\n   band-limited below Nyquist recovers %s" % sorted(set(below)))
    print("   with above-Nyquist content recovers %s" % sorted(set(above)))
    ok = bool(below and above and min(below) >= 0.49 and max(above) <= 0.46)
    print("   aliasing reproduces the shortfall: %s" % ok)
    print("   -> the real frames' +0.40..+0.45 is %s"
          % ("evidence of above-Nyquist content" if ok else "still unexplained"))

    with open(os.path.join(OUT, "s8_alias.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "explained": ok}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
