"""M87 step 6 -- validate metric v2 (addendum D2 bars V1, V2, V3, V6).

Runs on the SHIPPED renders, which is where the owner sees the artifact:
  V1 sensitivity : O on ROI_LEG must be >= +0.02, CI excluding 0
  V2 placebo C1  : mask translated (+512,+512) into empty background -> |O| <= 0.005
  V3 placebo C3  : a disc planted in ROI_FLAT                        -> |O| <= 0.005
  V6 gate inv.   : gate 0 vs gate 2 agree within their CIs
"""

import json
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

SHIPPED = {
    "bee3-g0": r"C:\dev\strehl-out\bee3-g0.tif",
    "bee3-g1": r"C:\dev\strehl-out\bee3-g1.tif",
    "bee3-full": r"C:\dev\strehl-out\bee3-full.tif",
}


def planted_disc(shape, centre, radius):
    y, x = np.ogrid[: shape[0], : shape[1]]
    return ((y - centre[0]) ** 2 + (x - centre[1]) ** 2) <= radius * radius


def report(tag, r):
    if r is None:
        print(f"  {tag:<34} INSUFFICIENT PROFILES")
        return
    print(f"  {tag:<34} O={r['O']:+8.5f}  CI[{r['O_ci'][0]:+.5f},{r['O_ci'][1]:+.5f}]"
          f"  n={r['n']:6d} ({r['n_tiles']:4d} tiles)  d*={r['d_star']:3d}")


def run(name, path):
    img = tifffile.imread(path)
    g = img[..., 1].astype(np.float32) if img.ndim == 3 else img.astype(np.float32)
    mask, tau = L.foreground_mask(g, hist_roi=None)
    print(f"\n=== {name}  {g.shape}  tau {tau:.0f}  fg frac {mask.mean():.4f} ===",
          flush=True)

    res = {}
    for roi_name in ("ROI_LEG", "ROI_BODY"):
        roi = L.ROIS[roi_name]
        pts, nrm = M2.boundary_normals(mask, roi=roi)
        val = M2.valid_profiles(mask, pts, nrm)
        r = M2.score2(g, mask, pts, nrm, val)
        report(f"{roi_name} (V1)", r)
        if r:
            res[roi_name] = {k: v for k, v in r.items() if k not in ("qbar", "o", "pts")}
            np.save(OUT / f"06-{name}-{roi_name}-q.npy", r["q_mean"])

    # ---- V2 placebo: the same mask translated into empty background --------
    sm = L.shifted_mask(mask)
    roi = L.ROIS["ROI_LEG"]
    sroi = (roi[0] + L.SHIFT_OFFSET[0], roi[1] + L.SHIFT_OFFSET[0],
            roi[2] + L.SHIFT_OFFSET[1], roi[3] + L.SHIFT_OFFSET[1])
    sroi = (min(sroi[0], g.shape[0] - 1), min(sroi[1], g.shape[0]),
            min(sroi[2], g.shape[1] - 1), min(sroi[3], g.shape[1]))
    pts, nrm = M2.boundary_normals(sm, roi=sroi)
    val = M2.valid_profiles(sm, pts, nrm)
    r = M2.score2(g, sm, pts, nrm, val)
    report("C1 shifted mask (V2)", r)
    if r:
        res["C1_shift"] = {k: v for k, v in r.items() if k not in ("qbar", "o", "pts")}

    # ---- V3 placebo: a disc planted in the flat ROI ------------------------
    f = L.ROIS["ROI_FLAT"]
    cy, cx = (f[0] + f[1]) // 2, (f[2] + f[3]) // 2
    disc = planted_disc(g.shape, (cy, cx), 120)
    droi = (max(cy - 300, 0), min(cy + 300, g.shape[0]),
            max(cx - 170, 0), min(cx + 170, g.shape[1]))
    pts, nrm = M2.boundary_normals(disc, roi=droi)
    val = M2.valid_profiles(disc, pts, nrm)
    r = M2.score2(g, disc, pts, nrm, val)
    report("C3 planted disc in ROI_FLAT (V3)", r)
    if r:
        res["C3_disc"] = {k: v for k, v in r.items() if k not in ("qbar", "o", "pts")}
    return res


def main():
    all_res = {}
    for name, path in SHIPPED.items():
        if not pathlib.Path(path).exists():
            print(f"missing {path}")
            continue
        all_res[name] = run(name, path)

    print("\n--- V6 gate invariance (ROI_LEG) ---")
    for name in all_res:
        r = all_res[name].get("ROI_LEG")
        if r:
            print(f"  {name:<12} O={r['O']:+.5f}  CI[{r['O_ci'][0]:+.5f},"
                  f"{r['O_ci'][1]:+.5f}]")

    json.dump(all_res, open(DATA / "06-metric-v2.json", "w"), indent=1)
    print("\nwrote data/06-metric-v2.json")


if __name__ == "__main__":
    main()
