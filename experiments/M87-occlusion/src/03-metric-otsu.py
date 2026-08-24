"""M87 step 3 -- the frozen metric on the shipped output, with the Otsu mask,
and the full E(d) profile printed so the shape is visible rather than
summarised.

Order per PREREGISTRATION: C3 (flat ROI, planted mask) FIRST.
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

SHIPPED = {
    "bee3-full": r"C:\dev\strehl-out\bee3-full.tif",
    "bee3-g0": r"C:\dev\strehl-out\bee3-g0.tif",
    "bee3-g1": r"C:\dev\strehl-out\bee3-g1.tif",
}


def planted_disc(shape, centre, radius):
    y, x = np.ogrid[: shape[0], : shape[1]]
    return ((y - centre[0]) ** 2 + (x - centre[1]) ** 2) <= radius * radius


def line(r, name):
    if r is None:
        print(f"  {name:<32} INSUFFICIENT DATA")
        return None
    print(
        f"  {name:<32} H={r['H']:8.1f} DN ({r['H_pct']:+6.3f}%)  "
        f"signed={r['H_signed']:+8.1f}  d*={r['d_star']:3d}  W={r['W']}"
    )
    return r


def show_profile(r, name, upto=48):
    print(f"    E(d) for {name}:")
    e = r["E"]
    s = "      "
    for d in range(1, upto + 1):
        s += f"{d}:{e[d]:+.0f} " if np.isfinite(e[d]) else f"{d}:--- "
        if d % 8 == 0:
            print(s)
            s = "      "
    if s.strip():
        print(s)


def main():
    results = {}
    for tag, path in SHIPPED.items():
        img = tifffile.imread(path).astype(np.float32)
        g = img[..., 1]
        print(f"\n=== {tag} ===", flush=True)
        mask, tau = L.foreground_mask(g)
        sm = L.shifted_mask(mask)
        print(f"  Otsu tau={tau:.1f}  foreground fraction={mask.mean():.4f}")
        res = {"tau": float(tau), "fg_frac": float(mask.mean())}

        # ---- C3 FIRST (rule 9) -------------------------------------------
        fy0, fy1, fx0, fx1 = L.ROIS["ROI_FLAT"]
        print(f"  ROI_FLAT foreground fraction = {mask[fy0:fy1, fx0:fx1].mean():.5f}")
        wide = (fy0, fy1, 0, 620)
        cy, cx = (fy0 + fy1) // 2, 150
        c3 = line(L.measure(g, planted_disc(g.shape, (cy, cx), 120), wide), "C3 planted disc, flat")
        c3s = line(
            L.measure(g, planted_disc(g.shape, (cy, cx + 260), 120), wide), "C3 disc moved +260 px"
        )
        res["C3"] = {k: c3[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if c3 else None
        res["C3_moved"] = (
            {k: c3s[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if c3s else None
        )

        # ---- registered ROIs ---------------------------------------------
        for roi_name in ("ROI_LEG", "ROI_BODY"):
            roi = L.ROIS[roi_name]
            r = line(L.measure(g, mask, roi), f"{roi_name} real mask")
            rs = line(L.measure(g, sm, roi), f"{roi_name} SHIFT placebo")
            if r:
                show_profile(r, f"{roi_name} real")
                np.save(OUT / f"03-{tag}-{roi_name}-E.npy", r["E"])
                np.save(OUT / f"03-{tag}-{roi_name}-P.npy", r["P"])
            if rs:
                np.save(OUT / f"03-{tag}-{roi_name}-Eshift.npy", rs["E"])
            res[roi_name] = {k: r[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if r else None
            res[roi_name + "_shift"] = (
                {k: rs[k] for k in ("H", "H_signed", "H_pct", "d_star", "W")} if rs else None
            )
            if r and rs:
                res[roi_name + "_ratio"] = float(r["H"] / max(rs["H"], 1e-9))
                print(
                    f"  {roi_name:<32} H / H_shift = {res[roi_name + '_ratio']:7.2f}x"
                    f"   (bar G1: >= 4)"
                )
        results[tag] = res

    (DATA / "03-shipped-metric.json").write_text(
        json.dumps(results, indent=2, default=float), encoding="utf-8"
    )
    print("\nwrote data/03-shipped-metric.json")


if __name__ == "__main__":
    sys.exit(main())
