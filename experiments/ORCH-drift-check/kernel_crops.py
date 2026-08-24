"""B4: the kernel A/B by eye, at 1:1, no scalar involved.

Three arms rendered from ONE solve (B1 confirmed the catmull-rom arm is
byte-identical to the shipped gallery render, so the kernel is the only
variable). Crops are pixel-for-pixel: no resize, no sharpening, no gamma
adjustment beyond what the renders already carry.

Deliberately NOT computing a sharpness number. Tonight a Laplacian metric
rated a visibly mosaicked render 2.73x sharper than the correct one, and a
metric preferred an image the eye rejects. This figure is the evidence.
"""
import io
import os

import numpy as np
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-kernel"
ARMS = ["catmull-rom", "nearest", "bilinear"]

# Two regions on bee-3-cpl (7032x4688). Chosen from BLOB.png:
# hairs on the thorax edge, and the leg/claw structure lower right.
REGIONS = [
    ("thorax hair, in focus", 760, 3180, 620, 460),
    ("leg + claw", 1500, 3760, 620, 460),
]

SCALE = 2  # nearest-neighbour magnify so the reader sees actual pixels


def load(arm):
    p = os.path.join(OUT, f"bee-3-cpl-{arm}.tif")
    im = Image.open(p)
    a = np.asarray(im)
    print(f"{arm}: {a.shape} {a.dtype}")
    return a


def to8(a):
    if a.dtype == np.uint16:
        return (a.astype(np.float32) / 257.0).clip(0, 255).astype(np.uint8)
    return a.astype(np.uint8)


def main():
    imgs = {a: load(a) for a in ARMS}

    h, w = imgs[ARMS[0]].shape[:2]
    for name, x, y, rw, rh in REGIONS:
        assert 0 <= x and x + rw <= w and 0 <= y and y + rh <= h, f"{name} out of bounds"

    pad = 8
    label_h = 34
    title_h = 46

    cw, ch = REGIONS[0][3] * SCALE, REGIONS[0][4] * SCALE
    W = pad + len(ARMS) * (cw + pad)
    H = title_h + len(REGIONS) * (label_h + ch + pad)

    canvas = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(canvas)
    d.text(
        (pad, 12),
        "bee-3-cpl -- ONE solve, three gather kernels. 1:1 pixels magnified x2 "
        "(nearest, so you are seeing real pixels). No sharpening, no resize, no post.",
        fill=(235, 235, 235),
    )

    yc = title_h
    for name, x, y, rw, rh in REGIONS:
        xc = pad
        for arm in ARMS:
            crop = to8(imgs[arm][y:y + rh, x:x + rw])
            tile = Image.fromarray(crop).resize((rw * SCALE, rh * SCALE), Image.NEAREST)
            canvas.paste(tile, (xc, yc + label_h))
            tag = f"{arm}"
            if arm == "catmull-rom":
                tag += "   <- SHIPPED DEFAULT"
            d.text((xc, yc + 8), f"{name}  |  {tag}", fill=(245, 220, 120))
            d.rectangle(
                [xc - 1, yc + label_h - 1, xc + rw * SCALE, yc + label_h + rh * SCALE],
                outline=(90, 90, 95),
            )
            xc += cw + pad
        yc += label_h + ch + pad

    dst = os.path.join(OUT, "KERNEL-AB.png")
    canvas.save(dst)
    print("wrote", dst, canvas.size)

    # difference magnitude, purely to say WHERE they differ -- not how much
    # better. Rendered as a map, never reported as a scalar alone.
    a = imgs["catmull-rom"].astype(np.int32)
    b = imgs["nearest"].astype(np.int32)
    x, y, rw, rh = REGIONS[0][1], REGIONS[0][2], REGIONS[0][3], REGIONS[0][4]
    da = np.abs(a[y:y + rh, x:x + rw] - b[y:y + rh, x:x + rw]).max(axis=2)
    print(f"|nearest - catmull| in region: median {np.median(da):.0f} DN, "
          f"p99 {np.percentile(da, 99):.0f} DN, max {da.max()} DN of 65535")


if __name__ == "__main__":
    main()
