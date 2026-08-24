"""Is the figure honest? The one control that could invalidate it.

The BEFORE panel is upscaled 2x with Lanczos, and Lanczos itself attenuates high
frequencies. So a sceptic can say: what the eye sees is the resampler, not the
binning. And separately, if the two output branches differ in tone curve, white
balance or matrix, the figure is comparing two things at once.

Both objections die if one thing is true: the binned branch must be, to within
rounding, an exact 2x2 box average of the demosaic branch. If it is, then every
difference in the figure is attributable to that box average and to nothing else,
and the Lanczos upscale is simply the fairest available way to show an 8.2 MP
image at 32.9 MP size.

POSITIVE CONTROL: the same comparison against a deliberately mismatched
reference (a gamma-shifted copy) must FAIL, or the test cannot discriminate.
"""

import json
import os
import sys

import numpy as np
import tifffile

REN = r"C:\dev\strehl-out\M95-resolution"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def box2(a):
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    b = a[:h, :w].astype(np.float64)
    return (b[0::2, 0::2] + b[0::2, 1::2] + b[1::2, 0::2] + b[1::2, 1::2]) / 4.0


def agree(binned, ref):
    d = binned.astype(np.float64) - ref
    return {"median_abs": float(np.median(np.abs(d))),
            "p99_abs": float(np.percentile(np.abs(d), 99)),
            "max_abs": float(np.abs(d).max()),
            "corr": float(np.corrcoef(binned.ravel(), ref.ravel())[0, 1])}


def main():
    binned = tifffile.imread(os.path.join(REN, "ship-binned.tif")).astype(np.float64)
    demo = tifffile.imread(os.path.join(REN, "ship-demosaic.tif")).astype(np.float64)
    ref = np.stack([box2(demo[:, :, c]) for c in range(3)], axis=2)
    n = min(binned.shape[0], ref.shape[0]), min(binned.shape[1], ref.shape[1])
    b, r = binned[:n[0], :n[1]], ref[:n[0], :n[1]]

    a = agree(b, r)
    print("binned  vs  box2(demosaic)      full frame, 16-bit DN out of 65535")
    print("   median |diff| %10.2f DN   (%.4f %% of full scale)"
          % (a["median_abs"], 100 * a["median_abs"] / 65535))
    print("   p99    |diff| %10.2f DN" % a["p99_abs"])
    print("   max    |diff| %10.2f DN" % a["max_abs"])
    print("   correlation   %10.6f" % a["corr"])

    bad = r * 0
    for c in range(3):
        bad[:, :, c] = 65535.0 * np.clip(r[:, :, c] / 65535.0, 0, 1) ** 1.1
    p = agree(b, bad)
    print("\n   POSITIVE CONTROL vs a gamma-1.1 mismatched reference")
    print("   median |diff| %10.2f DN   correlation %.6f" % (p["median_abs"], p["corr"]))

    sep = p["median_abs"] / max(a["median_abs"], 1e-9)
    passed = a["median_abs"] < 0.005 * 65535 and sep > 10
    print("\n   control discriminates (separation %.1fx): %s" % (sep, sep > 10))
    print("   binned branch IS a box average of the demosaic branch: %s" % passed)
    print("   -> the figure's difference is attributable to binning alone: %s" % passed)

    with open(os.path.join(OUT, "f2_boxcontrol.json"), "w", encoding="utf-8") as f:
        json.dump({"agree": a, "positive_control": p, "separation": sep,
                   "passed": bool(passed)}, f, indent=1)
    return 0 if passed else 2


if __name__ == "__main__":
    sys.exit(main())
