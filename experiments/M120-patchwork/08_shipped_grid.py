"""M120 step 8 — the pipeline-matched test, on the SHIPPED grid.

Step 7's shipped arm compared a warped+demosaiced+binned strehl render against
a denominator built from unwarped raw green luma. That mixes pipelines and its
Q is not trustworthy. M93 left the matched artifacts behind:

  armF-f*.tif            22 SINGLE-FRAME renders, shipped pipeline, shipped grid
  armM-gate0-binlin.tif  gate 0, shipped pipeline, shipped grid
  armM4-gate4-binlin.tif gate 4 (the shipped default), same
  armM-gate0-binlin-REPEAT.tif   a repeat -> the instrument's own noise floor

Everything on one grid, one demosaic, one alignment. No registration guesswork
and no cross-pipeline confound. This is the version of the invariant that can
be believed, and the gate 0 -> gate 4 dose-response comes free.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage as ndi

M93 = Path(r"C:\dev\strehl-out\M93-out")
M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
SO = Path(r"C:\dev\strehl-out")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent

WIN = (1400, 2100, 400, 1100)             # generous window on the shipped grid
MAPPED = (1687, 1815, 691, 819)           # M87 ROI mapped by (dy=+33, dx=-29)
SIDE = 128
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]
ROI_BAND = (2.0, 8.0)


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def boxsum(e, side):
    ii = np.zeros((e.shape[0] + 1, e.shape[1] + 1), np.float64)
    np.cumsum(np.cumsum(e, 0), 1, out=ii[1:, 1:])
    return ii[side:, side:] - ii[:-side, side:] - ii[side:, :-side] + ii[:-side, :-side]


def green(p):
    return tifffile.imread(p)[WIN[0]:WIN[1], WIN[2]:WIN[3], 1].astype(np.float32)


def main() -> int:
    # ---- provenance (rule 47): what IS ship-before-linear.tif? -----------
    sbl = tifffile.imread(M87 / "ship-before-linear.tif")
    for cand in ("armM4-gate4-binlin.tif", "armM-gate0-binlin.tif", "armC-aligned-gate0.tif"):
        a = tifffile.imread(M93 / cand)
        same = a.shape == sbl.shape and bool(np.array_equal(a, sbl))
        print(f"ship-before-linear.tif == M93-out/{cand} ? {same}")
        if same:
            print(f"   -> PROVENANCE RESOLVED: the M87 'shipped' reference is {cand}")
    del sbl

    fr_paths = sorted(M93.glob("armF-f*.tif"))
    fr_paths = [p for p in fr_paths if "demo" not in p.name]
    print(f"\n{len(fr_paths)} single-frame shipped-pipeline renders: "
          f"{[p.stem.split('-')[1] for p in fr_paths]}")
    frames = np.stack([green(p) for p in fr_paths])
    n, h, w = frames.shape

    # ---- ROI, chosen on the SINGLE-FRAME renders alone -------------------
    worst = None
    for f in frames:
        s = boxsum(bp(f, ROI_BAND) ** 2, SIDE)
        worst = s if worst is None else np.maximum(worst, s)
    cy, cx = np.unravel_index(int(worst.argmin()), worst.shape)
    R = (cy, cy + SIDE, cx, cx + SIDE)
    Rabs = (WIN[0] + R[0], WIN[0] + R[1], WIN[2] + R[2], WIN[2] + R[3])
    Rmap = (MAPPED[0] - WIN[0], MAPPED[1] - WIN[0], MAPPED[2] - WIN[2], MAPPED[3] - WIN[2])
    print(f"ROI-A (independent, cleanest {SIDE}x{SIDE} over the 22 frames): abs {Rabs}")
    print(f"ROI-B (M87 ROI mapped by dy=+33 dx=-29):                        abs {MAPPED}")

    merges = {
        "SHIPPED gate 4 (armM4-gate4-binlin)": M93 / "armM4-gate4-binlin.tif",
        "gate 0    (armM-gate0-binlin)": M93 / "armM-gate0-binlin.tif",
        "gate 0 REPEAT (determinism)": M93 / "armM-gate0-binlin-REPEAT.tif",
        "gate 0 aligned (armC-aligned-gate0)": M93 / "armC-aligned-gate0.tif",
        "bee3-full.tif": SO / "bee3-full.tif",
        "bee3-g0.tif": SO / "bee3-g0.tif",
        "bee3-g1.tif": SO / "bee3-g1.tif",
    }
    imgs = {}
    for k, p in merges.items():
        if p.exists():
            imgs[k] = green(p)
        else:
            print(f"  MISSING: {p}")
    imgs["NULL-1 mean of the 22 frames"] = frames.mean(0)

    res = {}
    for tag, roi_box in (("ROI-A independent", R), ("ROI-B mapped from M87", Rmap)):
        m = np.zeros((h, w), bool)
        m[roi_box[0]:roi_box[1], roi_box[2]:roi_box[3]] = True
        dens = {b: max(float(np.sqrt((bp(f, b)[m] ** 2).mean())) for f in frames) for b in BANDS}
        med = {b: float(np.median([np.sqrt((bp(f, b)[m] ** 2).mean()) for f in frames])) for b in BANDS}
        lev = frames.reshape(n, -1)[:, m.ravel()].mean(1)
        print(f"\n=== {tag}  abs rows {WIN[0]+roi_box[0]}:{WIN[0]+roi_box[1]} "
              f"cols {WIN[2]+roi_box[2]}:{WIN[2]+roi_box[3]} ===")
        print(f"  per-frame ROI level {lev.min():.0f}..{lev.max():.0f} DN, "
              f"sd {lev.std():.0f} DN ({100*lev.std()/lev.mean():.2f}%)")
        print(f"{'arm':40s}" + "".join(f"{b[0]:g}-{b[1]:g}".rjust(11) for b in BANDS))
        row = {}
        for k, im in imgs.items():
            q = [float(np.sqrt((bp(im, b)[m] ** 2).mean())) / dens[b] for b in BANDS]
            row[k] = {f"{b[0]:g}-{b[1]:g}": round(v, 4) for b, v in zip(BANDS, q)}
            print(f"{k:40s}" + "".join(f"{v:11.3f}" for v in q))
        print(f"{'  single frames: median Q':40s}"
              + "".join(f"{med[b]/dens[b]:11.3f}" for b in BANDS))
        print(f"{'  denominator max_k ||B f_k|| (DN)':40s}" + "".join(f"{dens[b]:11.2f}" for b in BANDS))
        res[tag] = {"roi_abs": [int(WIN[0] + roi_box[0]), int(WIN[0] + roi_box[1]),
                                int(WIN[2] + roi_box[2]), int(WIN[2] + roi_box[3])],
                    "Q": row,
                    "denominator_dn": {f"{b[0]:g}-{b[1]:g}": round(dens[b], 3) for b in BANDS},
                    "frame_level_sd_pct": float(100 * lev.std() / lev.mean())}

    # crops for the eye
    lo, hi = np.percentile(frames[len(frames) // 2][R[0]:R[1], R[2]:R[3]], (0.5, 99.5))
    for k, im in list(imgs.items()) + [("single frame", frames[len(frames) // 2])]:
        a = im[R[0]:R[1], R[2]:R[3]]
        v = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 2.2)
        name = "SHIP-" + "".join(c if c.isalnum() else "-" for c in k)[:34] + ".png"
        Image.fromarray(np.kron((255 * v + .5).astype(np.uint8), np.ones((4, 4), np.uint8))).save(OUT / name)
    print(f"\nwrote crops to {OUT}")
    (HERE / "shipped_grid.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"wrote {HERE / 'shipped_grid.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
