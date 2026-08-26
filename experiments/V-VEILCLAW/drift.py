"""How much does the bracket move? Measure it, do not assume it.

For a handful of (frame, master-window) pairs where that window's content is at
or near its own focus peak -- so NCC has something to lock onto -- report the
translation that best registers the frame to the master. Three windows at
different image positions distinguish rigid drift (same shift everywhere) from
focus breathing (shift growing with radius from the optical centre).
"""
import argparse
import pathlib

import cv2
import numpy as np
import rawpy
import tifffile

RAWDIR = pathlib.Path(r"D:\personal\macro\bee-3-cpl")
MASTER = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff")


def green_full(path):
    with rawpy.imread(str(path)) as r:
        v = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    v = v - black
    g = np.zeros_like(v)
    m = np.zeros(v.shape, np.float32)
    g[0::2, 1::2] = v[0::2, 1::2]
    m[0::2, 1::2] = 1
    g[1::2, 0::2] = v[1::2, 0::2]
    m[1::2, 0::2] = 1
    k = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.float32)
    s = cv2.filter2D(g, -1, k, borderType=cv2.BORDER_REFLECT)
    c = cv2.filter2D(m, -1, k, borderType=cv2.BORDER_REFLECT)
    return np.where(m > 0, g, s / np.maximum(c, 1e-6))


def n01(z):
    lo, hi = np.percentile(z, [0.5, 99.5])
    return np.clip((z - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True,
                    help="frame:y0:y1:x0:x1;frame:y0:... one per window")
    ap.add_argument("--pad", type=int, default=420)
    a = ap.parse_args()
    files = sorted(RAWDIR.glob("*.ARW"))
    M = tifffile.imread(str(MASTER))[:, :, 1].astype(np.float32)

    print(f"{'frame':>6}{'cy':>7}{'cx':>7}{'ncc':>8}{'dy':>7}{'dx':>7}")
    for spec in a.pairs.split(";"):
        k, y0, y1, x0, x1 = (int(v) for v in spec.split(":"))
        G = green_full(files[k])
        p = a.pad
        sy0, sx0 = max(0, y0 - p), max(0, x0 - p)
        sy1, sx1 = min(G.shape[0], y1 + p), min(G.shape[1], x1 + p)
        src = n01(G[sy0:sy1, sx0:sx1])
        tpl = n01(M[y0:y1, x0:x1])
        r = cv2.matchTemplate(cv2.GaussianBlur(src, (0, 0), 4),
                              cv2.GaussianBlur(tpl, (0, 0), 4), cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        dy, dx = loc[1] - (y0 - sy0), loc[0] - (x0 - sx0)
        print(f"{k:>6}{(y0 + y1) // 2:>7}{(x0 + x1) // 2:>7}{mx:8.3f}{dy:>7}{dx:>7}")


if __name__ == "__main__":
    main()
