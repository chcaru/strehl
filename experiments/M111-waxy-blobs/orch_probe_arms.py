"""M111 -- answer ORCH's probe in ORCH's own coordinates and statistic.

`experiments/ORCH-drift-check/blob_probe.py` reports, at blobB, a merged
inside/outside gradient-energy ratio of 0.094 against a control's 0.761, and
reads it as "the merge flattened the blob interior 10.6x beyond the optics".

Two things are wrong with that reading and one thing is right.

  * The mask is `merged >= percentile(merged, 75)` -- defined ON the arm under
    test. In this ROI the merged image's bright quartile is the pale defocused
    field and everything outside it is the sharp marker texture, so the ratio is
    guaranteed small for any working stacker. The control has no sharp texture
    anywhere, so its ratio is guaranteed near 1. The statistic separates the
    arms by construction (rule 17).
  * The comparison is cross-arm and was never registration-checked; the two arms
    also sit on a tone curve whose local slope varies 0.512..1.252 across luma
    bands (see `audit_probe.py`).
  * What is right is the eye: there ARE pale patches with hard scalloped edges
    that no input frame contains.

This script re-runs ORCH's exact statistic with two changes that cost nothing
and settle it: a third arm that is the plain mean of all 299 frames (same
frames, same alignment, same colour, same exposure -- so no registration or tone
confound at all), and the same numbers under a mask defined on the MEAN arm
instead of the arm under test.

Usage:  python orch_probe_arms.py
"""

import os

import numpy as np
import tifffile
from scipy import ndimage

RENDER = r"C:\dev\strehl-out\M111\render"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
ARMS = {
    "gate4 (shipped)": os.path.join(RENDER, "marker-dump.tif"),
    "gate1e5 (mean299)": os.path.join(RENDER, "marker-g100000.tif"),
    "gate0.25 (argmax)": os.path.join(RENDER, "marker-g0p25.tif"),
    "single frame (LibRaw)": os.path.join(ORCHDIR,
                                          "CONTROL-singleframe-dry-erase-marker-head-cpl.tif"),
}
ZOOMS = [("blobA-row4", 4715, 1180, 300, 260), ("blobB-row2", 2048, 1300, 320, 300)]


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def grad_energy(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def score(y, mask):
    ge = grad_energy(y)
    i, o = float(ge[mask].mean()), float(ge[~mask].mean())
    edge = ndimage.binary_dilation(mask, iterations=2) & ~ndimage.binary_erosion(
        mask, iterations=2
    )
    p90 = float(np.percentile(ge[edge], 90)) if edge.sum() > 20 else float("nan")
    return i, o, i / max(o, 1e-9), p90


def main():
    crops = {}
    for name, path in ARMS.items():
        if not os.path.exists(path):
            print(f"MISSING {name}: {path}")
            continue
        crops[name] = tifffile.imread(path)

    for nm, x, y, w, h in ZOOMS:
        print(f"\n=== {nm} @({x},{y}) {w}x{h} ===")
        sub = {k: luma(v[y:y + h, x:x + w]) for k, v in crops.items()}
        for mask_from in ("gate4 (shipped)", "gate1e5 (mean299)"):
            if mask_from not in sub:
                continue
            m = sub[mask_from] >= np.percentile(sub[mask_from], 75)
            print(f"  -- mask = bright quartile of [{mask_from}] --")
            print(f"     {'arm':>24} {'inside':>9} {'outside':>9} {'ratio':>8} {'bdy p90':>9}"
                  f" {'luma':>9}")
            for k, v in sub.items():
                i, o, r, p = score(v, m)
                print(f"     {k:>24} {i:9.2f} {o:9.2f} {r:8.3f} {p:9.2f} {v.mean():9.1f}")


if __name__ == "__main__":
    main()
