"""M77 arm B0 -- ROI selection on wrapped-text-2, by the section 4 rule, unchanged.

PREREGISTRATION-B.md B.3. This stack is declared BLIND in B.2: M77 had never run
it, no ROI existed for it, and this script chooses one by the same rule, from
input frames only, before any gate ladder is computed on it.

The rule is not reimplemented here. `01-rois.py` is imported and its `scan` and
`pick` are called, so a divergence between the two stacks' ROI rules is not
available as a defect.
"""

import importlib.util
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m77  # noqa: E402

_spec = importlib.util.spec_from_file_location("g0", HERE / "01-rois.py")
g0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g0)

STACK = "wrapped-text-2"


def main():
    m77.banner("M77 arm B0 -- ROI selection, wrapped-text-2 (BLIND, declared B.2)")
    print(f"  rule: imported verbatim from 01-rois.py "
          f"(tile {g0.TILE}, stride {g0.STRIDE}, edge {g0.EDGE})")
    tl, idx, contam, cg, iso, shape = g0.scan(STACK, None)
    fi, di, fs, ds = g0.pick(tl, contam, cg)
    flat_roi, detail_roi = tl[fi], tl[di]

    ev_cols = [k for k in range(len(idx)) if k % 2 == 0]
    od_cols = [k for k in range(len(idx)) if k % 2 == 1]
    fe, de, _, _ = g0.pick(tl, contam[:, ev_cols], cg[:, ev_cols])
    fo, do, _, _ = g0.pick(tl, contam[:, od_cols], cg[:, od_cols])
    k5_flat = g0.adjacent(tl[fe], tl[fo])
    k5_det = g0.adjacent(tl[de], tl[do])

    best_col = int(np.argmax(cg[di]))
    k2 = cg[di, best_col] / cg[fi, best_col] if cg[fi, best_col] > 0 else np.inf

    print(f"\n  --- {STACK}  ISO {iso:g}  plane {shape[1]}x{shape[0]}  "
          f"{len(tl)} tiles x {len(idx)} frames")
    print(f"      FLAT   x{flat_roi[0]},y{flat_roi[1]}  contam(max over frames) "
          f"= {fs[fi]:.4f}   [K1 bar < 1.10 -> "
          f"{'MET' if fs[fi] < 1.10 else 'NOT MET'}]")
    print(f"      DETAIL x{detail_roi[0]},y{detail_roi[1]}  cg(max over frames)  "
          f"= {ds[di]:.4f}")
    print(f"      K2 detail/flat cg = {k2:.2f}x  [bar >= 3x -> "
          f"{'MET' if k2 >= 3.0 else 'NOT MET'}]")
    print(f"      K5 even/odd: flat {'MET' if k5_flat else 'NOT MET'}"
          f"   detail {'MET' if k5_det else 'NOT MET'}")
    print(f"      contam over all {len(tl)} tiles: "
          f"{fs.min():.4f} .. {fs.max():.4f}")

    out = {
        STACK: {
            "iso": iso, "plane": list(shape), "n_tiles": len(tl), "frames": idx,
            "flat_roi": {"x": flat_roi[0], "y": flat_roi[1], "w": g0.TILE,
                         "h": g0.TILE, "contam_max": float(fs[fi])},
            "detail_roi": {"x": detail_roi[0], "y": detail_roi[1], "w": g0.TILE,
                           "h": g0.TILE, "cg_max": float(ds[di])},
            "k1_met": bool(fs[fi] < 1.10),
            "k2_ratio": float(k2), "k2_met": bool(k2 >= 3.0),
            "k5_flat_met": bool(k5_flat), "k5_detail_met": bool(k5_det),
            "contam_range": [float(fs.min()), float(fs.max())],
        }
    }
    (m77.OUT / "06-roi-wt2.json").write_text(json.dumps(out, indent=2),
                                             encoding="utf-8")
    print("\n  wrote out/06-roi-wt2.json")


if __name__ == "__main__":
    main()
