"""M120 step 4 — the background ROI, defined from INPUT FRAMES ONLY (prereg §4).

Rule 17 / M111 P13+P28: the mask may not be a percentile of any arm under test.
Every mask here is built from the 299-frame luma cube and never from a merge.

Outputs the ROI rectangles used by every later step, plus arm E (is any input
frame carrying the polygons?) which is the R3 falsifier.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
OUT.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).resolve().parent

TIGHT = (330, 610, 150, 570)  # box-relative, the crop ORCH looked at
PAD = 40
WIN = (TIGHT[0] - PAD, TIGHT[1] + PAD, TIGHT[2] - PAD, TIGHT[3] + PAD)


def local_sd(a, k=9):
    a = a.astype(np.float32)
    m = ndi.uniform_filter(a, k)
    m2 = ndi.uniform_filter(a * a, k)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def largest_square(mask, lo, hi):
    """Largest axis-aligned square of True, restricted to rows/cols in the crop."""
    h, w = mask.shape
    dp = np.zeros((h, w), np.int32)
    best = (0, 0, 0)
    for y in range(h):
        for x in range(w):
            if mask[y, x]:
                if y == 0 or x == 0:
                    dp[y, x] = 1
                else:
                    dp[y, x] = 1 + min(dp[y - 1, x], dp[y, x - 1], dp[y - 1, x - 1])
                if dp[y, x] > best[0] and lo <= y - dp[y, x] + 1 and y < hi:
                    best = (dp[y, x], y, x)
    s, y, x = best
    return (y - s + 1, y + 1, x - s + 1, x + 1), s


def main() -> int:
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]
    print(f"luma cube {cube.shape} {cube.dtype}  ({n} frames)")

    y0, y1, x0, x1 = WIN
    h, w = y1 - y0, x1 - x0
    maxsd = np.zeros((h, w), np.float32)
    minlvl = np.full((h, w), np.inf, np.float32)
    maxlvl = np.zeros((h, w), np.float32)
    lvl = np.zeros(n, np.float64)
    for k in range(n):
        f = np.array(cube[k, y0:y1, x0:x1], dtype=np.float32)
        np.maximum(maxsd, local_sd(f), out=maxsd)
        np.minimum(minlvl, f, out=minlvl)
        np.maximum(maxlvl, f, out=maxlvl)
        lvl[k] = f.mean()
    print(f"per-frame window mean level: min={lvl.min():.1f} max={lvl.max():.1f} "
          f"ratio={lvl.max() / lvl.min():.4f}  first={lvl[0]:.1f} last={lvl[-1]:.1f}")

    thr = float(np.percentile(maxsd, 20.0))
    smooth = maxsd <= thr
    print(f"'smooth in EVERY frame' threshold = 20th pct of max-over-frames 9x9 sd "
          f"= {thr:.2f} DN;  {100 * smooth.mean():.2f}% of the window")

    er = ndi.binary_erosion(smooth, np.ones((31, 31), bool))
    (by0, by1, bx0, bx1), side = largest_square(er, 0, h)
    print(f"largest all-frames-smooth square inside the window: "
          f"{side} px at window coords rows {by0}:{by1} cols {bx0}:{bx1}")
    if side < 128:
        print("REFUSE: no >=128 px all-smooth square; item 4's invariant is N/A here")
        return 3

    # box-relative absolute coordinates
    BG = (y0 + by0, y0 + by1, x0 + bx0, x0 + bx1)
    print(f"BACKGROUND ROI (box-relative) = {BG}")

    # NC1 textured control: the sharpest square of the same size, chosen on the
    # cube's max-over-frames local sd, again never on a merge.
    ksz = side
    box = ndi.uniform_filter(maxsd, ksz)
    box[: ksz // 2 + 1] = 0
    box[-(ksz // 2 + 1) :] = 0
    box[:, : ksz // 2 + 1] = 0
    box[:, -(ksz // 2 + 1) :] = 0
    cy, cx = np.unravel_index(int(box.argmax()), box.shape)
    TX = (y0 + cy - ksz // 2, y0 + cy - ksz // 2 + ksz,
          x0 + cx - ksz // 2, x0 + cx - ksz // 2 + ksz)
    print(f"TEXTURED ROI (NC1, box-relative) = {TX}")

    meta = {
        "window_box_relative": list(WIN),
        "bg_roi_box_relative": list(BG),
        "tx_roi_box_relative": list(TX),
        "side": int(side),
        "smooth_thr_dn": thr,
        "frame_mean_level": lvl.tolist(),
    }
    (HERE / "roi.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    np.save(OUT / "maxsd_window.npy", maxsd)
    print(f"\nwrote {HERE / 'roi.json'}")

    # ---- arm E: is any single input frame carrying the polygons? ----------
    print("\n--- arm E: per-frame local structure inside the background ROI ---")
    gy0, gy1, gx0, gx1 = BG
    sds = []
    for k in range(n):
        f = np.array(cube[k, gy0:gy1, gx0:gx1], dtype=np.float32)
        sds.append(float(local_sd(f).mean()))
    sds = np.array(sds)
    print(f"mean 9x9 local sd inside BG ROI over frames: "
          f"min={sds.min():.3f} median={np.median(sds):.3f} max={sds.max():.3f} DN")
    print(f"  argmax frame = {int(sds.argmax())}, argmin frame = {int(sds.argmin())}")
    np.save(OUT / "armE_frame_localsd.npy", sds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
