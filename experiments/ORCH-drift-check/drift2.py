"""ORCH drift re-derivation, v2 -- widened, with a rail detector.

v1 confirmed the shape but railed: frames 180-298 all returned exactly
0.936700, which is the bottom of a [0.94, 1.06] search walked down by the
refinement, not a measured optimum.  Seven identical values in a row is the
signature.  v2 widens the range and refuses to report any scale whose coarse
argmax sits on a grid edge.
"""

import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drift import STACK, OUT, DOWN, green_plane, prep, resample_scale, ncc_peak

LO, HI = 0.84, 1.06


def best_scale_railchecked(a, b, lo, hi, n=45, refine=3):
    """Scale of b relative to a.  Reports whether the coarse peak railed."""
    railed = False
    best, bestv = 1.0, -1.0
    for it in range(refine):
        grid = np.linspace(lo, hi, n)
        vals = [ncc_peak(a, prep(resample_scale(b, 1.0 / s))) for s in grid]
        k = int(np.argmax(vals))
        if it == 0 and (k == 0 or k == len(grid) - 1):
            railed = True
        best, bestv = float(grid[k]), float(vals[k])
        step = float(grid[1] - grid[0])
        lo, hi = best - step, best + step
        n = 21
    return best, bestv, railed


def main():
    names = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    ref_raw = green_plane(os.path.join(STACK, names[0]))
    ref = prep(ref_raw)
    full_h = ref_raw.shape[0] * 2 * DOWN
    full_w = ref_raw.shape[1] * 2 * DOWN
    r_corner = 0.5 * float(np.hypot(full_w, full_h))
    print("search [%.2f, %.2f]  corner radius %.1f px" % (LO, HI, r_corner))

    # the plant has to be re-run on the WIDER ladder, because widening the
    # search is itself a change to the instrument.
    for planted in (1.010, 0.900):
        s, v, rail = best_scale_railchecked(
            ref, resample_scale(ref_raw, planted), LO, HI)
        print("PLANT  s=%.4f -> %.6f  (err %+.6f)  ncc %.4f  railed=%s"
              % (planted, s, s - planted, v, rail))
    sys.stdout.flush()

    rows = []
    for k in list(range(20, len(names), 20)) + [len(names) - 1]:
        b = green_plane(os.path.join(STACK, names[k]))
        s, v, rail = best_scale_railchecked(ref, b, LO, HI)
        drift = abs(s - 1.0) * r_corner
        print("FRAME %3d  scale %.6f  ncc %.4f  drift %8.2f px  railed=%s"
              % (k, s, v, drift, rail))
        rows.append(dict(k=k, scale=s, ncc=v, corner_px=drift, railed=rail))
        sys.stdout.flush()

    railed = [r["k"] for r in rows if r["railed"]]
    print("\nrailed frames: %s" % (railed if railed else "none"))
    print("max corner drift: %.2f px at frame %d"
          % (max(r["corner_px"] for r in rows),
             max(rows, key=lambda r: r["corner_px"])["k"]))
    io.open(os.path.join(OUT, "drift-v2.json"), "w", encoding="utf-8").write(
        json.dumps(dict(stack=STACK, lo=LO, hi=HI, r_corner=r_corner,
                        rows=rows), indent=1))


if __name__ == "__main__":
    main()
