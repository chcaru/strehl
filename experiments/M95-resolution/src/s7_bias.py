"""V4 read the G1->G2 offset as +0.40 to +0.45 against a predicted +0.50.

Two explanations: the geometry is not what the RGGB quad says, or the estimator
is biased low at realistic SNR. This decides between them by planting a KNOWN
+0.50 offset and sweeping the noise level down to what the real frames have.

If the recovered value falls toward 0.40 as SNR falls, the shortfall is
attenuation bias -- the classical regression-dilution result, noise in the
signal pulls a recovered slope toward zero -- and V4 is consistent with a true
+0.50. If it stays at 0.50 regardless of noise, the geometry claim is wrong.
"""

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6_signal import geometry_scan, grids  # noqa: E402


def main():
    rng = np.random.default_rng(31337)
    n = 384
    # A scene with a realistic falling spectrum, not flat band-limited noise:
    # the bias depends on SNR *per frequency*, so the spectral shape matters.
    fu, fv = grids(n)
    r = np.hypot(fu, fv)
    F = np.fft.fft2(rng.standard_normal((n, n)))
    F *= 1.0 / (1.0 + (r / 0.03) ** 1.6)
    scene = np.real(np.fft.ifft2(F))
    scene = 500 * scene / scene.std()

    fy, fx = np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :]
    S = np.fft.fft2(scene)
    planted = 0.50
    shifted = np.real(np.fft.ifft2(S * np.exp(-2j * np.pi * (fy * -planted + fx * planted))))

    print("planted offset = %+.2f binned px in every row below" % planted)
    print("%10s %12s %12s" % ("noise sd", "hf SNR", "recovered"))
    rows = []
    for sd in (2.0, 10.0, 25.0, 50.0, 100.0, 200.0):
        a = scene + rng.standard_normal((n, n)) * sd
        b = shifted + rng.standard_normal((n, n)) * sd
        # high-frequency SNR of the scene against this noise level
        P = np.abs(np.fft.fft2(scene)) ** 2
        hf = float(P[r >= 0.25].mean()) / (sd * sd * n * n)
        got = geometry_scan(a, b)
        rows.append({"noise_sd": sd, "hf_snr": hf, "recovered": got})
        print("%10.1f %12.3f %12.2f" % (sd, hf, got))

    lo = [x["recovered"] for x in rows if x["hf_snr"] < 0.5]
    hi = [x["recovered"] for x in rows if x["hf_snr"] > 5]
    print("\n   high-SNR rows recover %s" % hi)
    print("   low-SNR  rows recover %s" % lo)
    verdict = bool(hi and lo and min(hi) >= 0.49 and max(lo) <= 0.46)
    print("   attenuation bias reproduced: %s" % verdict)
    print("   -> V4's +0.40..+0.45 is %s"
          % ("consistent with a true +0.50" if verdict else "NOT explained by bias"))

    with open(os.path.join(OUT, "s7_bias.json"), "w", encoding="utf-8") as f:
        json.dump({"planted": planted, "rows": rows, "bias_reproduced": verdict}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
