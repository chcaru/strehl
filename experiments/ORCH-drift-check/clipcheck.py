"""How much of each master is clipped to pure white, or crushed to black.

Written after a 1:1 crop of `leaf-2-cpl` showed paper-white across most of the
frame. A defect this size is invisible to every axis the campaign has been
scoring -- blotch, rim, sharpness and dust all measure *structure*, and there
is no structure in a saturated region to measure. A master can therefore read
clean on all four axes while being mostly white.

Reports the fraction of pixels at the top of the range in every channel, which
is the only value that cannot be recovered.
"""
import os
import sys

import numpy as np
import tifffile


def main():
    root = sys.argv[1]
    tiffs = sorted(f for f in os.listdir(root) if f.lower().endswith(".tiff"))
    if not tiffs:
        raise SystemExit("no .tiff in %s" % root)
    print("%-40s %8s %8s %8s %10s" % ("subject", "clip%", "black%", "median", "verdict"))
    rows = []
    for f in tiffs:
        a = tifffile.imread(os.path.join(root, f))
        if a.ndim == 2:
            a = np.dstack([a] * 3)
        a = a[:, :, :3]
        top = 65535 if a.dtype == np.uint16 else 255
        mx = a.max(axis=2)
        mn = a.min(axis=2)
        clip = float((mx >= top).mean()) * 100.0
        black = float((mn <= 0).mean()) * 100.0
        med = float(np.median(a))
        v = "BLOWN" if clip > 25.0 else ("high" if clip > 5.0 else "ok")
        rows.append((f[: -len(".tiff")], clip, black, med, v))
        print("%-40s %7.2f%% %7.2f%% %8.0f %10s" % rows[-1], flush=True)
    blown = [r for r in rows if r[4] == "BLOWN"]
    print("\n%d/%d BLOWN (>25%% clipped), %d high, %d ok"
          % (len(blown), len(rows), sum(1 for r in rows if r[4] == "high"),
             sum(1 for r in rows if r[4] == "ok")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
