"""S5b -- prove the election readout before believing it, then measure its roughness.

Three checks, in order:

  1. GRID CONTROL. Take pixels S5 says were won by a frame that was ALSO
     rendered on its own through arm F. The merged value there must equal the
     arm-F TIFF value at the same coordinates, byte for byte. This tests the
     ROI coordinate alignment between the `rawpy` cube and the `strehl` TIFF,
     the DN->u16 arithmetic, and the election readout, all at once. If the
     plane origins disagreed by one pixel this would collapse.

  2. THE MISMATCH. 0.06% of merged pixels match no frame. Characterise them
     rather than wave at them.

  3. ROUGHNESS. A merged pixel electing a distant frame is only a defect if
     its NEIGHBOURS did not. Smoothly varying election is a depth map. Salt
     and pepper is noise. Measured as |elected - local median|, against a
     null built by construction.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.ndimage import median_filter

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
CUBE = os.path.join(L.OUT, "m93_crops_v2.npy")
MERGED = os.path.join(L.OUT, "armM-gate0-binlin.tif")
WIN = 512


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))["res"]
    armf = json.load(open(os.path.join(OUTDIR, "s4_armF.json"), encoding="utf-8"))["binlin"]
    names = list(rois.keys())
    merged = L.read_tif_green(MERGED)
    cube = np.load(CUBE, mmap_mode="r")
    out = {}

    print("=" * 78)
    print("CHECK 1 -- grid control: merged == arm-F render on pixels that frame won")
    print("=" * 78)
    for nm in names:
        if nm == "ROI-FLAT":
            continue
        x, y = rois[nm]["x"], rois[nm]["y"]
        elected = np.load(os.path.join(L.OUT, f"m93_elected_{nm}.npy"))
        m = merged[y : y + WIN, x : x + WIN]
        rec = []
        for idx_s, r in armf.items():
            i = int(idx_s)
            sel = elected == i
            if sel.sum() < 200:
                continue
            f = L.read_tif_green(r["tif"])[y : y + WIN, x : x + WIN]
            d = (f - m)[sel]
            rec.append(
                dict(
                    frame=i,
                    n=int(sel.sum()),
                    frac_exact=float((d == 0).mean()),
                    max_abs=float(np.abs(d).max()),
                )
            )
        rec.sort(key=lambda r: -r["n"])
        worst = min(r["frac_exact"] for r in rec)
        tot = sum(r["n"] for r in rec)
        print(
            f"{nm:<14} {len(rec)} rendered frames tested, {tot} pixels, "
            f"worst frac_exact {100*worst:.4f}%, max |diff| {max(r['max_abs'] for r in rec):.0f} DN"
        )
        for r in rec[:4]:
            print(f"    frame {r['frame']:3d}  {r['n']:6d} px  exact {100*r['frac_exact']:8.4f}%")
        out.setdefault(nm, {})["grid_control"] = rec
        assert worst > 0.999, f"grid control FAILED for {nm}: {worst}"

    print()
    print("=" * 78)
    print("CHECK 2 -- the pixels that match no frame")
    print("=" * 78)
    BLACK, RANGE = 512.0, 14848.0
    for k, nm in enumerate(names):
        x, y = rois[nm]["x"], rois[nm]["y"]
        elected = np.load(os.path.join(L.OUT, f"m93_elected_{nm}.npy"))
        m = merged[y : y + WIN, x : x + WIN]
        bad = elected < 0
        if bad.sum() == 0:
            print(f"{nm:<14} none")
            continue
        pred = np.clip((np.asarray(cube[:, k], dtype=np.float64) - BLACK) / RANGE, 0, 1) * 65535.0
        pred_u = np.floor(pred + 0.5)
        near = np.abs(pred_u - m[None]).min(axis=0)
        print(
            f"{nm:<14} {int(bad.sum()):5d} px ({100*bad.mean():.4f}%)  "
            f"nearest frame differs by median {np.median(near[bad]):.0f} DN, "
            f"max {near[bad].max():.0f} DN;  {100*(near[bad] <= 2).mean():.1f}% within 2 DN"
        )
        out.setdefault(nm, {})["nomatch"] = dict(
            n=int(bad.sum()),
            frac=float(bad.mean()),
            median_nearest_dn=float(np.median(near[bad])),
            max_nearest_dn=float(near[bad].max()),
            frac_within_2=float((near[bad] <= 2).mean()),
        )

    print()
    print("=" * 78)
    print("CHECK 3 -- roughness of the election map")
    print("=" * 78)
    print("null by construction: a synthetic depth ramp of the same range, no noise")
    rng = np.random.default_rng(93)
    for nm in names:
        elected = np.load(os.path.join(L.OUT, f"m93_elected_{nm}.npy")).astype(np.float64)
        valid = elected >= 0
        e = elected.copy()
        e[~valid] = np.nan
        med = median_filter(np.nan_to_num(e, nan=np.nanmedian(e)), size=5)
        dev = np.abs(e - med)
        fw = focus[nm]["fwhm_frames"]
        rough = float(np.nanmedian(dev[valid]))
        p90 = float(np.nanpercentile(dev[valid], 90))
        frac_far = float(np.nanmean(dev[valid] > fw / 2.0))

        # Null: a smooth ramp over the same index range, quantised the same way.
        lo, hi = np.nanpercentile(e, [2, 98])
        yy, xx = np.mgrid[0:WIN, 0:WIN]
        ramp = np.round(lo + (hi - lo) * (xx + yy) / (2 * (WIN - 1)))
        nmed = median_filter(ramp, size=5)
        ndev = np.abs(ramp - nmed)

        print(
            f"{nm:<14} FWHM {fw:3d} fr | median |e-med5| = {rough:6.2f} frames "
            f"(null ramp {np.median(ndev):.2f}) | p90 {p90:6.1f} | "
            f"{100*frac_far:5.1f}% of pixels elect a frame >{fw/2:.0f} frames from their neighbours"
        )
        out.setdefault(nm, {})["roughness"] = dict(
            fwhm=fw, median_dev=rough, p90_dev=p90, frac_beyond_half_fwhm=frac_far,
            null_ramp_median_dev=float(np.median(ndev)),
        )

    dst = os.path.join(OUTDIR, "s5b_election_checks.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
