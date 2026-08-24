"""M87 step 19 -- does the F1 remedy generalise to a SECOND scene?

Everything in steps 10-17 was measured on one ROI of one capture
(bee-3-cpl, ROI_LEG). A remedy tuned on one edge of one stack is not yet a
remedy. Step 18 measured that flower-bud-with-background-fern-cpl carries the
same defect (ISO 0.0815, single frames 0.0000) on a completely different
subject, a different silhouette shape and a different sweep length.

This step re-runs the winning arm -- F1, the Wang-2015 mode partition -- on that
second scene with the SAME DELTA and the SAME yoke radius chosen on the bee, no
refitting. If the reduction transfers, the parameters are scene-independent
enough to hard-code in Rust. If it does not, the Rust recipe must expose them.

It also emits the owner-facing before/after crops for the flower scene, because
that scene shows the artifact far more legibly than the bee's leg does.
"""

import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
SHIP = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

SRC = r"D:\personal\macro\flower-bud-with-background-fern-cpl"
BOX = (700, 1700, 900, 2100)
ISO_GAIN = 100.0
YOKE = 40           # px, chosen on the bee, not refitted here
DELTAS = (40, 80)   # k, chosen on the bee, not refitted here
CROP = (120, 820, 40, 940)   # inside BOX: the right-hand bud and its rim


def stretch(ref):
    lo, hi = np.percentile(ref, (0.5, 99.7))
    return lo, max(hi - lo, 1e-9)


def png(a, path, lo, span, gamma=2.2, zoom=1):
    v = np.clip((a - lo) / span, 0, 1) ** (1.0 / gamma)
    im = Image.fromarray((v * 255).astype(np.uint8))
    if zoom != 1:
        im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
    im.save(path)


def main():
    SHIP.mkdir(parents=True, exist_ok=True)
    files = L.frames(pathlib.Path(SRC))
    n = len(files)
    h, w = BOX[1] - BOX[0], BOX[3] - BOX[2]
    cube = np.empty((n, h, w), np.float32)
    field = np.empty((n, h, w), np.float32)
    for k, f in enumerate(files):
        _, g1, g2, _ = L.read_planes(f, BOX)
        lu = 0.5 * (np.maximum(g1 - L.BLACK, 0) + np.maximum(g2 - L.BLACK, 0))
        cube[k] = lu
        field[k] = L.regularised_field(lu, ISO_GAIN)
        if k % 60 == 0:
            print(f"  decode {k}/{n}", flush=True)

    arg0 = np.argmax(field, axis=0).astype(np.int32)
    sel0 = np.take_along_axis(cube, arg0[None], 0)[0]
    mask, tau = L.foreground_mask(sel0)
    kF = int(np.bincount(arg0[mask]).argmax())
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[30:h - 30, 30:w - 30] = True
    treat = inner & (~mask) & (dist <= YOKE)
    print(f"n={n} kF={kF} fg={mask.mean():.3f} treat={treat.mean():.3f}")

    pts, nrm = M2.boundary_normals(mask, roi=(30, h - 30, 30, w - 30))
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    base = M2.score_iso(sel0, p, nv, boot=500)
    print(f"F0  ISO={base['ISO']:.5f} "
          f"CI[{base['ISO_ci'][0]:.5f},{base['ISO_ci'][1]:.5f}]  n={base['n']}",
          flush=True)
    res = {"n": n, "kF": kF, "tau": float(tau),
           "F0": {k: v for k, v in base.items() if k not in ("o", "pts", "qt")}}

    lo, span = stretch(sel0[CROP[0]:CROP[1], CROP[2]:CROP[3]])
    png(sel0[CROP[0]:CROP[1], CROP[2]:CROP[3]],
        SHIP / "06-FLOWER-BEFORE-shipped-merge.png", lo, span)

    for D in DELTAS:
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)
        for k in range(n):
            fld = field[k]
            better = fld > best
            if abs(k - kF) < D:
                better &= ~treat
            best[better] = fld[better]
            arg[better] = k
        sel = np.take_along_axis(cube, arg[None], 0)[0]
        r = M2.score_iso(sel, p, nv, boot=500)
        d = 100 * (1 - r["ISO"] / base["ISO"])
        print(f"F1 d={D:<3} ISO={r['ISO']:.5f} "
              f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  ({d:+.1f}% vs F0)",
              flush=True)
        res[f"F1-d{D}"] = {"delta_pct": float(d),
                           **{k: v for k, v in r.items()
                              if k not in ("o", "pts", "qt")}}
        png(sel[CROP[0]:CROP[1], CROP[2]:CROP[3]],
            SHIP / f"07-FLOWER-AFTER-F1-mode-partition-d{D}.png", lo, span)
        np.save(CACHE / f"19-flower-F1-d{D}.npy", sel)

    np.save(CACHE / "19-flower-sel0.npy", sel0)
    np.save(CACHE / "19-flower-mask.npy", mask)
    json.dump(res, open(DATA / "19-flower-fix.json", "w"), indent=1)
    for f in SHIP.glob("0[67]-FLOWER-*.png"):
        Image.open(f).save(OUT / f.name)
    print("wrote data/19-flower-fix.json and the flower crops")


if __name__ == "__main__":
    main()
