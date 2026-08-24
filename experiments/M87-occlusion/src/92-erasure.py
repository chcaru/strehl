"""M87 s31h -- quantify the erasure the rendered gate caught and my scalars missed.

WHAT HAPPENED.  91-gate.py scored the correction as leakage 0.000 into the
subject and a 96.3% reduction of the veil, and the rendered 100% crop of the
hair mass then showed the hair TIPS truncated against a hard stair-stepped
edge, the wispy isolated hairs over the pale background faded out, and a
hard-edged rim with blocky terracing where a soft veil used to be.

WHY THE SCALAR WAS BLIND, AND IT IS THE SAME HOLE AS LAST TIME.  B12
partitions by the SEGMENTED subject mask, which is a threshold on darkness.
A fine hair tip is one or two pixels wide and sits mostly above that
threshold, so it is classified as BACKGROUND.  The correction is licensed to
act on background.  A correction that erases every hair tip in the frame
therefore scores leakage = 0.000, which is exactly what it scored.  This is
the same failure as the +72.9% episode: a metric that rewards removing
background brightness near an edge also rewards removing the hairs, because
near an edge THE HAIRS ARE THE BACKGROUND PIXELS.

THE REPAIR IS TO DEFINE THE POPULATION FROM THE REFERENCE RENDER, not from a
mask.  Hair tips are thin DARK structures on a bright field, so measure their
depth below their own local surround:

    depth(x) = greyscale_dilation(g, 9)(x) - g(x)

and select the population where depth is large IN THE BEFORE RENDER.  Then
ask what happened to those same pixels in AFTER.  This is referenced -- it is
a ratio between two renders of the same pixels on a population fixed by the
reference -- so discipline 674 is satisfied: no gradient or Laplacian energy
is scored anywhere, and nothing is called "sharper".

  BAR B14, three branches, on median depth_after / depth_before over
  near-background hair-tip pixels:
      >= 0.90 -> thin structure preserved
      <= 0.70 -> thin structure erased
      otherwise -> PARTIAL

  CONTROL C-INT.  The same statistic on hair pixels INSIDE the subject, which
  91 measured the correction leaves untouched (median |delta| 0.0, p99 0.0).
  It must return 1.00.  If it does not, the estimator is not measuring what
  it claims and B14 means nothing.

  CONTROL C-NULL.  The same statistic with AFTER replaced by BEFORE.  Must
  return exactly 1.00 by construction; it catches a bug in the population
  selection or the ratio.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
X0, Y0, W, H = 700, 3150, 1100, 900
ZOOM = (150, 375, 250, 525)      # y0,y1,x0,x1: the hair tips, for a 2x figure
DEPTH_MIN = 3000.0               # DN below local surround to be a hair tip
B14_KEEP, B14_ERASE = 0.90, 0.70


def depth(g, k=9):
    return ndimage.grey_dilation(g, size=k) - g


def main():
    out = {}
    b = tifffile.imread(SCRATCH / "s31-bee3.tif")[Y0:Y0 + H, X0:X0 + W].astype(np.float32)
    a = tifffile.imread(SCRATCH / "s31-bee3-FIX.tif")[Y0:Y0 + H, X0:X0 + W].astype(np.float32)
    gb, ga = b[:, :, 1], a[:, :, 1]
    lo, hi = float(np.percentile(gb, 1)), float(np.percentile(gb, 99))
    med, span = float(np.median(gb)), (hi - lo) * 0.35
    subj = ndimage.binary_opening(
        ndimage.binary_closing(gb < med - span, np.ones((5, 5))), np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)

    db, da = depth(gb), depth(ga)
    near_bg = ~subj & (dist <= 40)
    tips = near_bg & (db > DEPTH_MIN)
    inside = subj & (ndimage.distance_transform_edt(subj) > 10) & (db > DEPTH_MIN)
    print("=== the population, defined from the BEFORE render ===")
    print(f"  near background (<=40 px, not subject) {int(near_bg.sum())} px")
    print(f"  of which thin dark structure (depth > {DEPTH_MIN:.0f} DN):"
          f" {int(tips.sum())} px ({100*tips.sum()/max(near_bg.sum(),1):.2f}%)")
    print(f"  subject-interior hair pixels (the control): {int(inside.sum())} px")

    def ratio(pop, after_depth, tag):
        r = float(np.median(after_depth[pop]) / np.median(db[pop]))
        print(f"  {tag:<44} median depth {np.median(db[pop]):7.0f} ->"
              f" {np.median(after_depth[pop]):7.0f} DN   ratio {r:.4f}")
        return r

    print("\n=== B14  what happened to the thin structure? ===")
    r14 = ratio(tips, da, "near-background hair tips (B14)")
    r_int = ratio(inside, da, "subject-interior hairs (C-INT, must be 1.00)")
    r_nul = ratio(tips, db, "AFTER replaced by BEFORE (C-NULL, must be 1.00)")

    gone = float((da[tips] <= DEPTH_MIN * 0.5).mean())
    print(f"  hair-tip pixels whose depth fell below half the selection"
          f" threshold: {100*gone:.1f}%")
    b14 = ("thin structure preserved" if r14 >= B14_KEEP
           else "thin structure ERASED" if r14 <= B14_ERASE else "PARTIAL")
    print(f"  B14: {b14}")
    ok_int = abs(r_int - 1.0) <= 0.02
    ok_nul = abs(r_nul - 1.0) <= 1e-9
    print(f"  C-INT {'PASS' if ok_int else 'FAIL'}   C-NULL"
          f" {'PASS' if ok_nul else 'FAIL'}")
    out.update({"tips_px": int(tips.sum()), "near_bg_px": int(near_bg.sum()),
                "inside_px": int(inside.sum()), "B14_ratio": r14,
                "C_INT": r_int, "C_NULL": r_nul, "gone_frac": gone,
                "B14": b14, "C_INT_pass": bool(ok_int),
                "C_NULL_pass": bool(ok_nul)})

    print("\n=== why B12 read 0.000 while this reads erasure ===")
    in_mask = float(tips[subj].sum()) if subj.sum() else 0.0
    print(f"  hair-tip pixels classified as SUBJECT by the mask: {int(in_mask)}")
    print(f"  hair-tip pixels classified as BACKGROUND: {int(tips.sum())}")
    print(f"  so 100% of the population B14 measures is INVISIBLE to B12,")
    print(f"  which only looks for leakage INTO the subject mask.")
    out["tips_in_mask"] = int(in_mask)

    def view(x):
        return np.clip(x / 257.0, 0, 255).astype(np.uint8)

    zy0, zy1, zx0, zx1 = ZOOM
    vb, va = view(b[zy0:zy1, zx0:zx1]), view(a[zy0:zy1, zx0:zx1])
    hh, ww = vb.shape[:2]
    pan = np.full((hh, 2 * ww + 8, 3), 30, np.uint8)
    pan[:, 0:ww] = vb
    pan[:, ww + 8:] = va
    Image.fromarray(pan).resize((pan.shape[1] * 2, pan.shape[0] * 2),
                                Image.NEAREST).save(SCRATCH / "HAIR-TIPS-2X.png")
    print(f"\n  wrote {SCRATCH / 'HAIR-TIPS-2X.png'}"
          f"  BEFORE | AFTER at 2x, crop y {zy0}:{zy1} x {zx0}:{zx1}")
    out["zoom"] = list(ZOOM)

    DATA.mkdir(exist_ok=True)
    (DATA / "92-erasure.json").write_text(json.dumps(out, indent=1, default=float),
                                          encoding="utf-8")
    print(f"wrote {DATA / '92-erasure.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
