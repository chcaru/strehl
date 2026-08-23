"""M60 / 23 -- N5 as pre-registered, plus the sep/step ratio table.

The pre-registration defines N5 as "fraction with k1 within 2 frames of either
end".  18-classes.py reported the SOFT version (posterior mass in the outer 5%
of frames), which carries a temperature.  The registered version carries no free
parameter at all, so it is computed here and reported alongside.

Also emits the per-cell ratio |k2-k1| / |k_fg-k_bg| that H2 turns on, because
the class medians hide the spread.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import CELLS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CUR = os.path.join(DATA, "curves")


def main():
    import importlib
    A = importlib.import_module("12-analyse")
    with open(os.path.join(DATA, "20-audit.json"), encoding="utf-8") as fh:
        geo = {g["cell"]: g for g in json.load(fh)["geometry"]}

    print("=" * 78)
    print("N5 as REGISTERED: fraction of band pixels whose k1 is within 2")
    print("frames of either end of the stack -- no temperature, no free parameter")
    print("=" * 78)
    rows = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        p = os.path.join(CUR, "%s__%s.npz" % (stack, name))
        if not os.path.exists(p):
            continue
        d = np.load(p, allow_pickle=True)
        F, lab = d["F"], d["lab"]
        band = lab == 0
        Fb = np.ascontiguousarray(F[:, band])
        n = Fb.shape[0]
        k1 = np.argmax(Fb, axis=0)
        k2 = A.detect(Fb, np.maximum(np.ascontiguousarray(d["S"][:, band]), 1e-6))["k2"]
        b1 = float(np.mean((k1 <= 1) | (k1 >= n - 2)))
        b2 = float(np.mean((k2 <= 1) | (k2 >= n - 2)))
        g = geo.get(name, {})
        sep, step = g.get("sep", float("nan")), g.get("step", float("nan"))
        ratio = sep / step if step and step > 0 else float("nan")
        rows.append(dict(cell=name, cls=cls, n=n, k1_bnd=b1, k2_bnd=b2,
                         sep=sep, step=step, ratio=ratio))
        print("  %-18s %-8s n=%3d  k1 at boundary %5.2f%%  k2 at boundary %5.2f%%"
              "  | sep %5.1f  step %5.1f  sep/step %s"
              % (name, cls, n, 100 * b1, 100 * b2, sep, step,
                 ("%5.2f" % ratio) if np.isfinite(ratio) else " step=0"))
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r for r in rows if r["cls"] == cls]
        rr = [r["ratio"] for r in v if np.isfinite(r["ratio"])]
        print("  %-9s n=%2d  k1 at boundary median %5.2f%% (max %5.2f%%)"
              "  k2 at boundary median %5.2f%%  | sep/step median %s (n=%d finite)"
              % (cls, len(v),
                 100 * np.median([r["k1_bnd"] for r in v]),
                 100 * max(r["k1_bnd"] for r in v),
                 100 * np.median([r["k2_bnd"] for r in v]),
                 ("%5.2f" % np.median(rr)) if rr else " -- ", len(rr)))
    with open(os.path.join(DATA, "23-boundary.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("\nwrote data/23-boundary.json")


if __name__ == "__main__":
    main()
