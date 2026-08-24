"""M87 step 11 -- the mechanism: what does selection do to a background pixel?

Step 10 established, MEASURED, that every one of the 299 single frames scores
ISO ~ 0 on the same edge geometry where the merge scores 0.068. So merging
manufactures the rim. This script asks HOW.

Hypothesis (two-layer veiling, stated as a selection consequence):

  A background pixel near a dark occluder is veiled: I_k = a_k F + (1-a_k) B
  with a_k the fraction of its blur disc covered by the defocused foreground.
  a_k is SMALLEST when the foreground is in focus, at k = k_F. With F darker
  than B, the pixel is therefore BRIGHTEST at k = k_F.

  The focus field at that pixel is dominated by the foreground's own edge --
  the 13 px gradient window straddles the silhouette -- so it also peaks at
  k_F. Selection therefore elects, at near-edge background pixels, close to the
  value-MAXIMISING frame.

  Far from any edge the focus field is flat and noise-driven, so selection
  elects an essentially arbitrary k and lands near the value-MEDIAN frame.

  Prediction: the percentile rank of the elected value within that pixel's own
  through-focus value distribution is high near the edge and ~0.5 far away.
  The rim is then the difference between a max-like estimate and a median-like
  one -- created entirely by selection, exactly as the single-frame control
  requires.

Measured here: rank(d), and the band profiles of the per-pixel max, median and
min over k, against the merge.
"""

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

MARGIN = 22
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
CHUNK = 48


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    n, h, w = lumas.shape

    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True

    rank = np.zeros((h, w), np.float32)
    vmax = np.full((h, w), -np.inf, np.float32)
    vmin = np.full((h, w), np.inf, np.float32)
    ssum = np.zeros((h, w), np.float64)
    for y0 in range(0, h, CHUNK):
        y1 = min(y0 + CHUNK, h)
        cube = np.asarray(lumas[:, y0:y1, :], np.float32)
        e = sel[y0:y1, :][None, :, :]
        rank[y0:y1] = (cube < e).sum(axis=0) / n
        vmax[y0:y1] = cube.max(axis=0)
        vmin[y0:y1] = cube.min(axis=0)
        ssum[y0:y1] = cube.sum(axis=0)
        np.save(CACHE / f"_med_{y0}.npy", np.median(cube, axis=0).astype(np.float32))
        print(f"  rows {y0}-{y1}", flush=True)
    vmed = np.concatenate([np.load(CACHE / f"_med_{y0}.npy")
                           for y0 in range(0, h, CHUNK)], axis=0)
    for y0 in range(0, h, CHUNK):
        (CACHE / f"_med_{y0}.npy").unlink()
    vmean = (ssum / n).astype(np.float32)
    np.save(CACHE / "11-vmax.npy", vmax)
    np.save(CACHE / "11-vmed.npy", vmed)
    np.save(CACHE / "11-rank.npy", rank)

    bg = inner & (~mask)
    dr = np.rint(dist).astype(np.int32)
    print("\n   d     n_px   rank(elected)   merge     max_k     med_k     min_k"
          "    (merge-med)/(max-med)")
    rows = []
    for d in list(range(1, 41)) + list(range(42, 97, 2)):
        s = bg & (dr == d)
        c = int(s.sum())
        if c < 200:
            continue
        r = float(rank[s].mean())
        me = float(sel[s].mean())
        mx = float(vmax[s].mean())
        md = float(vmed[s].mean())
        mn = float(vmin[s].mean())
        frac = (me - md) / max(mx - md, 1e-6)
        rows.append((d, c, r, me, mx, md, mn, frac))
        print(f"{d:4d} {c:8d}   {r:8.4f}    {me:8.1f}  {mx:8.1f}  {md:8.1f}  "
              f"{mn:8.1f}   {frac:8.3f}")

    far = bg & (dr >= 60)
    near = bg & (dr >= 3) & (dr <= 25)
    print(f"\nrank of elected value:  near band d in [3,25] {rank[near].mean():.4f}"
          f"   far d>=60 {rank[far].mean():.4f}")
    print(f"elected k:              near {np.median(argbest[near]):.0f}"
          f"   far {np.median(argbest[far]):.0f}")
    kF = int(np.bincount(argbest[mask]).argmax())
    print(f"modal elected k inside the subject (k_F) = {kF}")
    print(f"|k_elected - k_F|:      near {np.median(np.abs(argbest[near] - kF)):.0f}"
          f"   far {np.median(np.abs(argbest[far] - kF)):.0f}")

    json.dump({"rank_near": float(rank[near].mean()),
               "rank_far": float(rank[far].mean()),
               "kF": kF,
               "rows": rows}, open(DATA / "11-mechanism.json", "w"), indent=1)
    print("\nwrote data/11-mechanism.json")


if __name__ == "__main__":
    main()
