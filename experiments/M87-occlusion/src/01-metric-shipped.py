"""M87 step 1 -- the frozen metric on the SHIPPED merged output.

Order is the one PREREGISTRATION registers: the flat-ROI control (C3) runs
FIRST (rule 9: "Run it *first*, not as a closing check"), then the real ROIs,
then the gate comparison.

Reads only `C:\\dev\\strehl-out\\bee3-*.tif`, which the owner delivered. Writes
nothing there.
"""

import json
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

SHIPPED = {
    "bee3-full": r"C:\dev\strehl-out\bee3-full.tif",
    "bee3-g0": r"C:\dev\strehl-out\bee3-g0.tif",
    "bee3-g1": r"C:\dev\strehl-out\bee3-g1.tif",
}


def planted_disc(shape, centre, radius):
    y, x = np.ogrid[: shape[0], : shape[1]]
    return ((y - centre[0]) ** 2 + (x - centre[1]) ** 2) <= radius * radius


def report(r, name):
    if r is None:
        print(f"  {name:<34} INSUFFICIENT DATA")
        return None
    print(
        f"  {name:<34} H={r['H']:9.1f} DN  ({r['H_pct']:+6.3f}% of base)  "
        f"signed={r['H_signed']:+9.1f}  d*={r['d_star']:3d}  W={r['W']}"
    )
    return r


def main():
    results = {}
    for tag, path in SHIPPED.items():
        img = tifffile.imread(path).astype(np.float32)
        g = img[..., 1]
        print(f"\n=== {tag}  {img.shape} ===", flush=True)
        mask, tau = L.foreground_mask(g, hist_roi=L.ROIS["ROI_LEG"])
        print(f"  mask tau={tau:.1f}  foreground fraction={mask.mean():.4f}")
        sm = L.shifted_mask(mask)

        res = {"tau": float(tau), "fg_frac": float(mask.mean())}

        # ---- C3 FIRST: flat ROI with a planted disc, rule 9 --------------
        fy0, fy1, fx0, fx1 = L.ROIS["ROI_FLAT"]
        inside = mask[fy0:fy1, fx0:fx1].mean()
        print(f"  ROI_FLAT foreground fraction = {inside:.5f} (registered: must be ~0)")
        disc = planted_disc(g.shape, ((fy0 + fy1) // 2, (fx0 + fx1) // 2), 120)
        wide = (fy0, fy1, max(0, fx0), min(g.shape[1], fx1 + 300))
        c3 = report(L.measure(g, disc, wide), "C3 flat ROI, planted disc")
        c3s = report(L.measure(g, L.shifted_mask(disc, (0, 600)), wide), "C3 shift placebo")
        res["C3"] = {k: c3[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if c3 else None
        res["C3_shift"] = (
            {k: c3s[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if c3s else None
        )

        # ---- the registered ROIs -----------------------------------------
        for roi_name in ("ROI_LEG", "ROI_BODY"):
            roi = L.ROIS[roi_name]
            r = report(L.measure(g, mask, roi), f"{roi_name} real mask")
            rs = report(L.measure(g, sm, roi), f"{roi_name} SHIFT placebo")
            res[roi_name] = {k: r[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if r else None
            res[roi_name + "_shift"] = (
                {k: rs[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if rs else None
            )
            if r and rs:
                ratio = r["H"] / max(rs["H"], 1e-9)
                print(f"  {roi_name:<34} H / H_shift = {ratio:8.2f}x   (bar G1: >= 4)")
                res[roi_name + "_ratio"] = float(ratio)
                np.save(OUT / f"01-{tag}-{roi_name}-E.npy", r["E"])
                np.save(OUT / f"01-{tag}-{roi_name}-P.npy", r["P"])
                np.save(OUT / f"01-{tag}-{roi_name}-Eshift.npy", rs["E"])
        results[tag] = res

    (DATA / "01-shipped-metric.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8"
    )
    print("\nwrote data/01-shipped-metric.json")

    print("\n=== G3: gate comparison on the shipped renders ===")
    for roi_name in ("ROI_LEG", "ROI_BODY"):
        hs = {t: results[t].get(roi_name, {}) for t in SHIPPED}
        vals = {t: (hs[t] or {}).get("H") for t in SHIPPED}
        print(f"  {roi_name}: " + "  ".join(f"{t}={v:.1f}" for t, v in vals.items() if v))


if __name__ == "__main__":
    sys.exit(main())
