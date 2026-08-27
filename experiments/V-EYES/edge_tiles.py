"""Find the edges most likely to show a halo, and cut them at 1:1.

The owner's specific complaint was the "cut-out sticker" look: a bright or dark
rim following the subject's silhouette against the background. That artifact
lives at high-contrast subject/background boundaries, so this picks tiles by
edge strength AND tonal range, not by detail alone -- the delivery's own crop
chooser ranks by mean |Laplacian| of luma, which favours busy texture and can
skip a clean silhouette entirely.

Tiles are 400 px because viewer_target.py showed the path to my eye is 1:1 at
400 and resampled at 600 and above. They are cut from the delivered JPEGs
rather than the masters on purpose: the JPEG is the artifact under audit, and
if the encode itself introduced something the master comparison would hide it.

Also reports, per tile, the overshoot statistic that a halo would produce:
the 99.9th percentile of luma within 12 px of a strong edge, minus the 99.9th
percentile of luma in the flat background away from edges. A genuine rim shows
as a positive excursion that exists ONLY near edges. This number is here to
localise what the eye finds, not to replace it -- the tiles are for looking at.

Usage: python edge_tiles.py <outdir> <fulljpeg> [more jpegs...] [--per N]
"""

import sys
import pathlib
import numpy as np
import cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TILE = 400
DS = 8


def main():
    args = [a for a in sys.argv[1:]]
    per = 2
    if "--per" in args:
        i = args.index("--per")
        per = int(args[i + 1])
        del args[i : i + 2]
    outdir = pathlib.Path(args[0])
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"{'tile':<52} {'x':>6} {'y':>6} {'rng':>5} {'grad':>7} {'rimDN':>7}")
    print("-" * 92)
    for src in args[1:]:
        p = pathlib.Path(src)
        a = np.asarray(Image.open(p).convert("RGB"))
        lum = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(
            np.float32
        )
        small = cv2.resize(lum, (lum.shape[1] // DS, lum.shape[0] // DS), cv2.INTER_AREA)
        gx = cv2.Sobel(small, cv2.CV_32F, 1, 0, 3)
        gy = cv2.Sobel(small, cv2.CV_32F, 0, 1, 3)
        gm = np.sqrt(gx * gx + gy * gy)
        t = TILE // DS
        score = cv2.boxFilter(gm, -1, (t, t))
        mx = cv2.dilate(small, np.ones((t, t), np.uint8))
        mn = cv2.erode(small, np.ones((t, t), np.uint8))
        rng = mx - mn
        combined = score * np.clip(rng - 60, 0, None)

        picks = []
        c = combined.copy()
        for _ in range(per):
            idx = int(np.argmax(c))
            cy, cx = divmod(idx, c.shape[1])
            if c[cy, cx] <= 0:
                break
            picks.append((cx * DS - TILE // 2, cy * DS - TILE // 2))
            y0, y1 = max(0, cy - t), min(c.shape[0], cy + t)
            x0, x1 = max(0, cx - t), min(c.shape[1], cx + t)
            c[y0:y1, x0:x1] = 0

        for i, (x, y) in enumerate(picks, 1):
            x = int(max(0, min(x, a.shape[1] - TILE)))
            y = int(max(0, min(y, a.shape[0] - TILE)))
            tl = a[y : y + TILE, x : x + TILE]
            tlum = lum[y : y + TILE, x : x + TILE]
            e = cv2.Canny(
                cv2.GaussianBlur(tlum, (0, 0), 1.5).astype(np.uint8), 40, 120
            )
            near = cv2.dilate(e, np.ones((25, 25), np.uint8)) > 0
            far = ~cv2.dilate(e, np.ones((81, 81), np.uint8)).astype(bool)
            rim = (
                float(np.percentile(tlum[near], 99.9) - np.percentile(tlum[far], 99.9))
                if near.sum() > 100 and far.sum() > 100
                else float("nan")
            )
            name = f"{p.stem.replace('--DELIVER-V4', '')}-E{i}-{x}-{y}.png"
            Image.fromarray(tl).save(outdir / name)
            print(
                f"{name:<52} {x:>6} {y:>6} {np.ptp(tlum):>5.0f} "
                f"{float(cv2.Laplacian(tlum, cv2.CV_32F).std()):>7.2f} {rim:>7.1f}"
            )


if __name__ == "__main__":
    main()
