r"""Is my independent rim instrument admissible at all?

A rim instrument must read ~0 on a SHARP edge that has no ringing. If it reads
high there, it is measuring sharpness rather than ringing, and its readings on
real pictures cannot be attributed to halos.

Three synthetic images, all with identical geometry:
  SHARP-CLEAN  ideal step, slightly softened, NO overshoot  -> must read ~0
  RINGING      the same step with a real Gibbs-like rim      -> must read high
  BLURRED      the same step, heavily softened               -> must read ~0
"""
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rimindep as R


def base(seed=0):
    rng = np.random.default_rng(seed)
    h, w = 1400, 1400
    img = np.zeros((h, w))
    xs = np.arange(60, w - 60, 40)
    lvl = rng.uniform(0.15, 0.85, size=xs.size)
    for i, x in enumerate(xs):
        img[:, x:] = lvl[i]
    return img, rng


def sharp_clean(seed=0):
    img, rng = base(seed)
    img = gaussian_filter(img, 0.8)
    return np.clip(img + rng.normal(0, 0.002, img.shape), 0, 1)


def ringing(seed=0):
    img, rng = base(seed)
    img = gaussian_filter(img, 0.8)
    img = img + 0.9 * (img - gaussian_filter(img, 1.6))
    return np.clip(img + rng.normal(0, 0.002, img.shape), 0, 1)


def blurred(seed=0):
    img, rng = base(seed)
    return np.clip(gaussian_filter(img, 2.5) + rng.normal(0, 0.002, img.shape),
                   0, 1)


def main():
    print("commissioning the independent rim instrument on synthetic edges\n")
    rows = []
    for name, fn in (("SHARP-CLEAN", sharp_clean), ("RINGING", ringing),
                     ("BLURRED", blurred)):
        g = fn()
        sites = R.select(gaussian_filter(g, 2.0))
        v, n = R.overshoot(R.profiles(g, sites))
        rows.append((name, v, n))
        print("  %-12s reads %+7.2f%%  over n=%d sites" % (name, 100 * v, n))

    d = dict((r[0], r[1]) for r in rows)
    print()
    clean_ok = abs(d["SHARP-CLEAN"]) < 0.02
    ring_ok = d["RINGING"] > 0.05
    sep = d["RINGING"] - d["SHARP-CLEAN"]
    print("  SHARP-CLEAN within +/-2%% of zero : %s" % ("YES" if clean_ok else
                                                        "NO"))
    print("  RINGING above +5%%                : %s" % ("YES" if ring_ok else "NO"))
    print("  separation ringing - clean       : %+.2f points" % (100 * sep))
    if clean_ok and ring_ok:
        print("\nADMISSIBLE: it is quiet on a sharp rim-free edge and loud on a "
              "ringing one.")
        return 0
    print("\nINADMISSIBLE: this instrument reads %+.2f%% on an edge that is sharp "
          "and provably\nrim-free, so its readings on real pictures carry "
          "sharpness, not ringing.\nIt may not be used to corroborate or refute "
          "the rim axis." % (100 * d["SHARP-CLEAN"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
