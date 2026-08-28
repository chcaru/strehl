"""V-MOTE P9 -- MARKED copies of the crops, so a reader can see which coordinate
lands where.  The unmarked originals are kept alongside; nothing below is
evidence, it is annotation of evidence.
"""
import os, sys
import numpy as np
import tifffile
from PIL import Image, ImageDraw

DST = r"C:\dev\strehl-out\V-MOTE\crops"
MAST = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
AB = r"C:\dev\strehl-out\V-MOTE\ab"
CACHE = r"C:\dev\strehl-out\V-MOTE\cache"
SITE_P = (6868, 4610)
SITE_M = (7008, 4450)
CW = 400


def ring(d, x, y, r, col, wide=2):
    d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=wide)


def annotate(img, x0, y0, extra=()):
    im = img.convert("RGB")
    d = ImageDraw.Draw(im)
    ring(d, SITE_P[0] - x0, SITE_P[1] - y0, 45, (255, 60, 60))
    d.text((SITE_P[0] - x0 - 40, SITE_P[1] - y0 + 50), "BUILD-DEFECT 2x(3434,2305)", fill=(255, 60, 60))
    ring(d, SITE_M[0] - x0, SITE_M[1] - y0, 45, (60, 160, 255))
    d.text((SITE_M[0] - x0 - 130, SITE_M[1] - y0 - 60), "V-EYES (7008,4450)", fill=(60, 160, 255))
    for (ex, ey, lab, col) in extra:
        ring(d, ex - x0, ey - y0, 30, col)
        d.text((ex - x0 - 30, ey - y0 + 34), lab, fill=col)
    return im


def main():
    for src, out, sub in (
        ("10-master-flower-bud-alone-cpl-corner400.png",
         "11-MARKED-master-flower-bud-alone-cpl.png", "flower-bud-alone-cpl"),
        ("10-master-highly-angled-ruler-mm-cpl-corner400.png",
         "11-MARKED-master-highly-angled-ruler-mm-cpl.png", "highly-angled-ruler-mm-cpl"),
        ("20-AB-flower-bud-alone-cpl-OFF-corner400.png",
         "22-MARKED-AB-OFF.png", "flower-bud-alone-cpl"),
        ("20-AB-flower-bud-alone-cpl-ON-corner400.png",
         "22-MARKED-AB-ON.png", "flower-bud-alone-cpl"),
    ):
        w = 7040 if sub in ("flower-bud-alone-cpl", "highly-angled-ruler-mm-cpl") else 7032
        x0, y0 = w - CW, 4688 - CW
        im = annotate(Image.open(os.path.join(DST, src)), x0, y0)
        im.save(os.path.join(DST, out))
        print("  %-46s from %s  (crop origin %d,%d)" % (out, src, x0, y0))

    # flats: centred crop, marked with the map coord and the measured centroid
    f = np.load(os.path.join(CACHE, "flat_all.npy")).astype(np.float64)
    QH, QW = f.shape
    cx, cy, R = 3434, 2305, 120
    y0, y1 = cy - R, min(QH, cy + R)
    x0, x1 = cx - R, min(QW, cx + R)
    sub = f[y0:y1, x0:x1]
    dy = (np.arange(y0, y1) - cy)[:, None] * np.ones((1, x1 - x0))
    dx = np.ones((y1 - y0, 1)) * (np.arange(x0, x1) - cx)[None, :]
    r = np.hypot(dx, dy)
    m = (r >= 90) & (r <= 115)
    A = np.stack([np.ones(m.sum()), dx[m], dy[m], dx[m]**2, dx[m]*dy[m], dy[m]**2], 1)
    c, *_ = np.linalg.lstsq(A, sub[m], rcond=None)
    bg = c[0] + c[1]*dx + c[2]*dy + c[3]*dx**2 + c[4]*dx*dy + c[5]*dy**2
    res = sub / bg - 1.0
    up = np.repeat(np.repeat(res, 2, 0), 2, 1)          # quads -> photosites, nearest
    img = Image.fromarray((np.clip((up + 0.05) / 0.10, 0, 1) * 255 + 0.5).astype(np.uint8))
    img.save(os.path.join(DST, "03-flat-mote2-centred-pm5pct.png"))
    im = img.convert("RGB")
    d = ImageDraw.Draw(im)
    px, py = 2 * (cx - x0), 2 * (cy - y0)
    d.line([px - 12, py, px + 12, py], fill=(255, 60, 60), width=1)
    d.line([px, py - 12, px, py + 12], fill=(255, 60, 60), width=1)
    d.text((px + 8, py + 8), "map (3434,2305)", fill=(255, 60, 60))
    gx, gy = 2 * (3432.7 - x0), 2 * (2305.3 - y0)
    ring(d, gx, gy, 41, (60, 255, 120), 1)
    d.text((gx - 60, gy - 56), "measured centroid r=41 photosites", fill=(60, 255, 120))
    im.save(os.path.join(DST, "04-MARKED-flat-mote2-centred.png"))
    print("  03/04 flat crops: %dx%d photosites, quad grid upsampled x2 nearest, stretch [-5%%,+5%%]"
          % up.shape[::-1][0:2][0:1][0] if False else
          "  03/04 flat crops: %d x %d photosites, quads upsampled x2 nearest, stretch [-5%%,+5%%]"
          % (up.shape[1], up.shape[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
