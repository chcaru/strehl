"""Which arm is more magnified? Measured without any resampling convention.

The orchestrator and I agree on the number and disagree on its direction. They
report "zoomnull -> aligned: 0.9875" and read it as "the aligned render is 1.25%
more magnified than the null". My `orchmag.py` measures 0.986250 for the factor
by which the NULL must be magnified to match the ALIGNED, which says the
opposite: the null is 1/0.98625 = 1.0139x, i.e. 1.39% MORE magnified.

Every scale estimator carries a convention, and a convention is exactly the
thing that flips silently. So this script uses none. It measures a DISTANCE.

Method: take a small template from the aligned arm at a known radius from the
frame centre, find where that same texture sits in the null arm by normalised
cross-correlation over a generous search box, and compare the two radii. If a
feature at radius r in the aligned arm sits at radius > r in the null arm, the
null is the more magnified image. No resampling, no forward/inverse choice, no
scale parameter -- just where the same texture is.

Controls, pre-registered:
  D1 SELF. Template from the aligned arm, searched in the ALIGNED arm, must
     return displacement exactly (0, 0) and a radius ratio of exactly 1.
  D2 PLANT. Search in a copy of the aligned arm that has been deliberately
     magnified by 1.02 about the centre; the measured radius ratio must come
     back at 1.02 +/- 0.002. This proves the probe can see a magnification at
     all and that it reports "more magnified" as a ratio ABOVE one.
  D3 SHRINK PLANT. Same with 0.98; must return 0.98 +/- 0.002. Without both
     signs a probe can be right by accident.
  D4 AGREEMENT. The per-tile ratios must agree with each other; a spread wider
     than 0.5% means the frames differ by more than a global similarity and no
     single number should be quoted.
"""

import json

import numpy as np
import tifffile
from scipy.ndimage import map_coordinates

ALIGNED = r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif"
ZOOMNULL = r"C:\dev\strehl-out\M86-align\bee3-zoomnull.tif"
OUT = r"C:\dev\strehl-out\M97\signcheck.json"

TPL = 192      # template side
SEARCH = 60    # +/- search radius in px


def load(path):
    a = tifffile.imread(path)
    g = a[:, :, 1] if a.ndim == 3 else a
    return g.astype(np.float32)


def rescale(img, s):
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return map_coordinates(img, [cy + (yy - cy) / s, cx + (xx - cx) / s],
                           order=3, mode="nearest").astype(np.float32)


def match(tpl, img, y0, x0):
    """Best (dy, dx) placing `tpl` in `img` near (y0, x0), by NCC, sub-pixel."""
    t = tpl - tpl.mean()
    tn = np.sqrt((t * t).sum())
    best = (-2.0, 0, 0)
    scores = {}
    for dy in range(-SEARCH, SEARCH + 1, 2):
        for dx in range(-SEARCH, SEARCH + 1, 2):
            w = img[y0 + dy:y0 + dy + TPL, x0 + dx:x0 + dx + TPL]
            if w.shape != tpl.shape:
                continue
            wc = w - w.mean()
            d = tn * np.sqrt((wc * wc).sum())
            v = float((t * wc).sum() / d) if d > 0 else -2.0
            scores[(dy, dx)] = v
            if v > best[0]:
                best = (v, dy, dx)
    # parabolic refinement on the 3-point neighbourhood in each axis
    v0, by, bx = best
    ref = []
    for axis in range(2):
        step = (2, 0) if axis == 0 else (0, 2)
        m = scores.get((by - step[0], bx - step[1]))
        p = scores.get((by + step[0], bx + step[1]))
        if m is None or p is None or (m - 2 * v0 + p) == 0:
            ref.append(0.0)
        else:
            ref.append(-0.5 * (p - m) / (m - 2 * v0 + p) * 2.0)
    return v0, by + ref[0], bx + ref[1]


def probe(a, target, tiles, label, results):
    h, w = a.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rows = []
    for (ty, tx) in tiles:
        tpl = a[ty:ty + TPL, tx:tx + TPL]
        if tpl.std() < 50:
            continue
        v, dy, dx = match(tpl, target, ty, tx)
        py, px = ty + TPL / 2.0, tx + TPL / 2.0
        ra = np.hypot(py - cy, px - cx)
        rb = np.hypot(py + dy - cy, px + dx - cx)
        rows.append({"ty": ty, "tx": tx, "ncc": v, "dy": dy, "dx": dx,
                     "r_aligned": ra, "r_target": rb, "ratio": rb / ra})
    rr = [r["ratio"] for r in rows if r["ncc"] > 0.5]
    med = float(np.median(rr)) if rr else float("nan")
    spread = float(np.max(rr) - np.min(rr)) if rr else float("nan")
    results[label] = {"median_radius_ratio": med, "spread": spread,
                      "n": len(rr), "tiles": rows}
    print(f"{label:22s} radius ratio {med:.5f}   spread {spread:.5f}   "
          f"n={len(rr)}", flush=True)
    return med, spread


def main():
    a = load(ALIGNED)
    z = load(ZOOMNULL)
    h, w = a.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0

    # Tiles on a ring far from the centre, where a 1.4% scale is tens of pixels.
    tiles = []
    for ang in np.arange(0, 2 * np.pi, np.pi / 6):
        for rad in (1600, 2100):
            ty = int(cy + rad * np.sin(ang) - TPL / 2)
            tx = int(cx + rad * np.cos(ang) - TPL / 2)
            if (SEARCH + 4 < ty < h - TPL - SEARCH - 4 and
                    SEARCH + 4 < tx < w - TPL - SEARCH - 4):
                tiles.append((ty, tx))
    print(f"{len(tiles)} candidate tiles", flush=True)

    res = {"tpl": TPL, "search": SEARCH, "n_tiles": len(tiles)}
    d1, _ = probe(a, a, tiles, "D1 self", res)
    d2, _ = probe(a, rescale(a, 1.02), tiles, "D2 plant 1.02", res)
    d3, _ = probe(a, rescale(a, 0.98), tiles, "D3 plant 0.98", res)
    tr, sp = probe(a, z, tiles, "TREATMENT null", res)

    res["verdict"] = {
        "D1_pass": abs(d1 - 1.0) < 1e-6,
        "D2_pass": abs(d2 - 1.02) < 0.002,
        "D3_pass": abs(d3 - 0.98) < 0.002,
        "D4_pass": bool(sp < 0.005),
        "null_is_more_magnified": bool(tr > 1.0),
        "null_over_aligned_magnification": tr}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)

    print("\n--- verdict ---")
    for k, v in res["verdict"].items():
        print(f"  {k}: {v}")
    print(f"\nMEASURED: the null arm is {tr:.5f}x the aligned arm's "
          f"magnification.")
    print("  > 1 means the NULL is the more magnified image.")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
