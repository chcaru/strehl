"""M84b step 14 - the tick-height hierarchy, which decides the physical pitch.

Pre-registration section 3.2. On a metric rule the longest marks are the
centimetre marks, so the minor pitch is 10 mm / Q_long. This is the only test
that separates a 1 mm rule from a 2 mm rule; the lens's VERIFIED 2.8x ceiling
(F-camera-lens-optics.md:13) separately refutes 0.5 mm.

REGISTERED DEVIATION, disclosed: the pre-registration froze F-TALL as
0,1100,3514,880. That band was chosen from a preview before the tick DIRECTION
was established. The ruler's datum line sits near quad y = 1540 with minor ticks
below it and long ticks rising above it, so the registered band truncates the
tallest ticks' tops. This script reports BOTH the registered band and an
extended band 0,600,3512,940 that contains the whole rise. The hierarchy
decision is read from the extended band and the registered band is reported
alongside it.

Reads READ-ONLY from D:\\personal\\macro.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy
from PIL import Image
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACK = "flat-on-ruler-cpl"

BANDS = {
    "registered_F_TALL": (1100, 1980),
    "extended": (600, 1540),
}


def quad_green(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black


def tick_rise(plane: np.ndarray, xs: np.ndarray, y0: int, y1: int) -> np.ndarray:
    """For each graduation x, how far the dark mark reaches above the datum.

    Measured as the number of rows in [y0, y1) whose local darkness at that
    column exceeds half the darkness measured just below the datum. Rows are
    scanned upward from y1 and the run is required to be contiguous, so a
    speck of dirt higher up cannot extend a short tick."""
    h, w = plane.shape
    rows = plane[y0:y1, :]
    bg = ndimage.median_filter(rows, size=(1, 301), mode="nearest")
    dark = np.maximum(bg - rows, 0.0)
    rise = np.zeros(len(xs))
    for i, x in enumerate(xs):
        xi = int(round(x))
        lo, hi = max(xi - 3, 0), min(xi + 4, w)
        col = dark[:, lo:hi].mean(axis=1)
        ref = float(np.max(col[-40:]))  # darkness just above the datum
        if ref <= 0:
            continue
        thr = 0.5 * ref
        j = len(col) - 1
        while j >= 0 and col[j] >= thr:
            j -= 1
        rise[i] = len(col) - 1 - j
    return rise


def period_of_flagged(flags: np.ndarray) -> dict:
    """Index period of the flagged graduations, and whether it is an integer."""
    idx = np.flatnonzero(flags)
    if len(idx) < 2:
        return {"n": int(len(idx)), "period": None, "gaps": idx.tolist()}
    g = np.diff(idx)
    return {
        "n": int(len(idx)),
        "indices": idx.tolist(),
        "gaps": g.tolist(),
        "period": float(np.median(g)),
        "period_spread": float(np.max(g) - np.min(g)),
    }


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    fit = json.loads((OUT / "13-flat.json").read_text())
    xs = np.array(fit["tick_x"])
    frames = sorted((CORPUS / STACK).glob("*.ARW"))
    # Registered: frames spanning the band where the comb is in focus.
    use = [40, 48, 52, 56, 64]
    res = {"stack": STACK, "frames_used": [frames[i].name for i in use], "bands": {}}

    planes = [quad_green(frames[i]) for i in use]
    for name, (y0, y1) in BANDS.items():
        rises = np.array([tick_rise(p, xs, y0, y1) for p in planes])
        rise = np.median(rises, axis=0)
        spread = float(np.median(np.std(rises, axis=0)))
        band_h = y1 - y0
        # Registered classification: three populations by rise, split at the
        # two largest gaps in the sorted rise distribution.
        order = np.sort(rise)
        med_minor = float(np.median(rise))
        long_flag = rise > 0.6 * band_h
        mid_flag = (rise > 0.25 * band_h) & ~long_flag
        res["bands"][name] = {
            "band": [y0, y1],
            "rise_quadpx": rise.tolist(),
            "rise_frame_scatter": spread,
            "sorted_rise": order.tolist(),
            "median_rise": med_minor,
            "long": period_of_flagged(long_flag),
            "mid_or_long": period_of_flagged(long_flag | mid_flag),
        }
        print(f"[{name}] band y {y0}-{y1} ({band_h} px)")
        print(f"  rise per graduation: {np.round(rise, 0)}")
        print(f"  frame-to-frame scatter (median): {spread:.1f} px")
        print(f"  long  : {res['bands'][name]['long']}")
        print(f"  mid|long: {res['bands'][name]['mid_or_long']}")

    # Save a visual of the extended band for the record.
    y0, y1 = BANDS["extended"]
    vis = planes[2][y0:y1, :]
    p0, p1 = np.percentile(vis, [1, 99])
    Image.fromarray(
        (np.clip((vis - p0) / (p1 - p0), 0, 1) * 255 + 0.5).astype(np.uint8)
    ).save(OUT / "14-tall-band.png")

    (OUT / "14-hierarchy.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
