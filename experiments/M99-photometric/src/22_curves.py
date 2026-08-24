"""Look at the curves, not the summary. Print the per-frame level, the step at
the shutter change, and the per-patch disagreement, so the shape of the effect
is on the record rather than a single ratio.
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module  # noqa: E402

A = import_module("21_phaseA")


def main(stack):
    z = A.load(stack)
    scene, smad, sensor = z["scene"], z["scene_mad"], z["sensor"]
    centres, a, files = z["centres"], z["a"], [str(x) for x in z["files"]]
    ref = int(z["ref"])
    ok = (np.isfinite(scene).all(axis=0) & np.isfinite(smad).all(axis=0)
          & (scene > A.LEVEL_MIN).all(axis=0) & (scene < A.LEVEL_MAX).all(axis=0)
          & (smad < A.SMOOTH_MAX).all(axis=0))
    chosen = A.farthest_point(centres, ok, A.N_PATCH)
    t = A.shutter(stack, files)
    S = scene[:, chosen]
    Sn = sensor[:, chosen]
    g = np.median(S, axis=1)
    gn = np.median(Sn, axis=1)
    n = len(g)

    # Shutter runs.
    runs = []
    cur, start = t[0], 0
    for i in range(1, n):
        if t[i] != cur:
            runs.append((start, i - 1, cur))
            cur, start = t[i], i
    runs.append((start, n - 1, cur))

    print("=" * 74)
    print("%s   n=%d  ref=%d  patches=%s" % (stack, n, ref, chosen))
    print("shutter runs: %s" % [(r[0], r[1], round(r[2], 5)) for r in runs])
    print()
    print(" idx   a_k     t_s     scene    sensor   scene/t   a-ratio")
    step = max(1, n // 30)
    for k in list(range(0, n, step)) + [n - 1]:
        print("%4d  %.5f  %.5f  %.5f  %.5f  %8.4f  %.5f"
              % (k, a[k], t[k], g[k], gn[k], g[k] / t[k], a[k] / a[ref]))

    # The step at each shutter change, measured on the scene-fixed level with a
    # 20-frame median either side. A camera exposure step should show up here at
    # exactly the shutter ratio if the scene is otherwise static.
    print()
    for (s0, e0, t0), (s1, e1, t1) in zip(runs, runs[1:]):
        w = 20
        before = np.median(g[max(0, s1 - w):s1])
        after = np.median(g[s1:s1 + w])
        print("shutter change at frame %d: %.5f s -> %.5f s (EXIF ratio %.4f)"
              % (s1, t0, t1, t0 / t1))
        print("  measured level step (median of %d frames either side): "
              "%.5f -> %.5f  ratio %.4f" % (w, before, after, before / after))
        print("  1/3-stop ladder would give %.4f; the rounded EXIF pair gives "
              "%.4f" % (2 ** (1 / 3), t0 / t1))

    # Per-patch curves, normalised to their own frame-0 value.
    print()
    print("per-patch level relative to frame 0 (scene-fixed, no exposure norm):")
    rel = S / S[0:1, :]
    hdr = "".join("  p%-5d" % c for c in chosen)
    print("  idx" + hdr)
    for k in list(range(0, n, step)) + [n - 1]:
        print("  %3d" % k + "".join("  %6.4f" % v for v in rel[k]))
    print()
    print("patch centres (plane px) and their frame-0 level:")
    for c in chosen:
        print("  p%-4d  (%7.1f,%7.1f)  L0=%.4f  maxrelMAD=%.4f"
              % (c, centres[c][0], centres[c][1], scene[0, c],
                 smad[:, c].max()))


if __name__ == "__main__":
    for s in sys.argv[1:] or ["bee-3-cpl"]:
        main(s)
