"""Crop a master at 1:1 and write PNGs, so a human (or I) can actually look.

Usage: python peek.py <tiff> <outdir> [n]

Sites are chosen where the local gradient is strongest -- that is where a rim
artefact lives -- with an exclusion radius so that n crops are not n views of
one edge. Prints the clip fraction beside every crop, because fact 1817: a
verdict on a saturated crop is uninterpretable.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

SIZE = 384
EXCL = 900


def main() -> int:
    src = sys.argv[1]
    out = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    os.makedirs(out, exist_ok=True)

    a = tifffile.imread(src)
    if a.ndim == 3 and a.shape[2] > 3:
        a = a[:, :, :3]
    h, w = a.shape[:2]
    print("%s  %dx%d  clip=%.2f%%  median=%.0f" % (
        os.path.basename(src), w, h,
        float((a.max(axis=2) >= 65535).mean()) * 100.0,
        float(np.median(a)),
    ))

    lum = a.astype(np.float32).mean(axis=2)
    # Coarse energy map on a 64-px grid: cheap, and rim artefacts are a
    # neighbourhood property rather than a single-pixel one.
    step = 64
    gh = (h - SIZE) // step
    gw = (w - SIZE) // step
    score = np.zeros((gh, gw), np.float32)
    gy, gx = np.gradient(lum)
    g = np.abs(gy) + np.abs(gx)
    # MODE MATTERS MORE THAN THE CROP SIZE. Picking sites by peak gradient
    # samples the sharpest parts of the frame, which is exactly where a stacker
    # looks best -- so the default mode is a good-news generator and must not be
    # used to conclude anything about defects. `flat` targets low-gradient
    # regions carrying low-frequency variance, which is where blotch/mottle
    # lives; `edge` targets the largest luminance steps, which is where rim
    # lives.
    mode = os.environ.get("PEEK_MODE", "hi")
    for j in range(gh):
        for i in range(gw):
            y = j * step
            x = i * step
            tg = g[y:y + SIZE, x:x + SIZE]
            tl = lum[y:y + SIZE, x:x + SIZE]
            if mode == "flat":
                # Low-frequency variance measured on a 16x-decimated tile, so
                # per-pixel grain does not enter it, divided by local gradient
                # so that busy regions are not selected.
                d = tl[::16, ::16]
                score[j, i] = float(d.std()) / (float(tg.mean()) + 1.0)
            elif mode == "edge":
                score[j, i] = float(tl.max() - tl.min()) * float(tg.mean())
            else:
                score[j, i] = float(tg.mean())

    picked = []
    s = score.copy()
    for _ in range(n):
        j, i = np.unravel_index(int(np.argmax(s)), s.shape)
        if s[j, i] <= 0:
            break
        y, x = j * step, i * step
        picked.append((y, x))
        r = EXCL // step
        s[max(0, j - r):j + r, max(0, i - r):i + r] = 0

    for k, (y, x) in enumerate(picked):
        tile = a[y:y + SIZE, x:x + SIZE]
        clip = float((tile.max(axis=2) >= 65535).mean()) * 100.0
        img = Image.fromarray((tile >> 8).astype(np.uint8))
        img = img.resize((SIZE * 2, SIZE * 2), Image.NEAREST)
        p = os.path.join(out, "crop%d_y%d_x%d.png" % (k, y, x))
        img.save(p)
        print("  crop%d at (%d,%d)  clip=%5.2f%%  -> %s" % (k, y, x, clip, p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
