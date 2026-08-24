"""Re-run the crop comparison with the 1.25% magnification difference removed.

Nearest-neighbour resampling only: it duplicates and drops pixels but never
blurs, so it cannot hand either arm an advantage in the quantity under test.
"""
import os
import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-look"
D = r"C:\dev\strehl-out\M86-align"
S_REL = 0.9875  # measured: zoomnull -> aligned

a = tifffile.imread(os.path.join(D, "bee-3-ALIGNED.tif"))
z = tifffile.imread(os.path.join(D, "bee3-zoomnull.tif"))
H, W = a.shape[:2]


def rescale_nn(img, s):
    h, w = img.shape[:2]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    sy = np.clip(np.rint((yy - cy) / s + cy).astype(np.int64), 0, h - 1)
    sx = np.clip(np.rint((xx - cx) / s + cx).astype(np.int64), 0, w - 1)
    return img[sy, sx]


zs = rescale_nn(z, S_REL)


def tenengrad(g):
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return float((gx * gx + gy * gy).mean())


def ncc(x, y):
    x = x - x.mean(); y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else 0.0


S = W / 1400.0
CROPS = {
    "wing-venation": (int(300 * S), int(100 * S)),
    "thorax-hair":   (int(800 * S), int(300 * S)),
    "head-eye":      (int(900 * S), int(650 * S)),
}
N = 640

print("%-16s %10s %10s %8s   %s" % ("region", "aligned", "null(sc)", "ratio", "NCC"))
for name, (x, y) in CROPS.items():
    x = max(0, min(W - N, x)); y = max(0, min(H - N, y))
    ca = a[y:y + N, x:x + N].astype(np.float32)
    cz = zs[y:y + N, x:x + N].astype(np.float32)
    ta, tz = tenengrad(ca.mean(axis=2)), tenengrad(cz.mean(axis=2))
    print("%-16s %10.1f %10.1f %8.4f   %.4f" % (
        name, ta, tz, ta / tz, ncc(ca.mean(axis=2), cz.mean(axis=2))))
    bar = 34
    canvas = Image.new("RGB", (N * 2 + 12, N + bar), (18, 18, 18))
    canvas.paste(Image.fromarray(np.clip(ca / 257.0, 0, 255).astype(np.uint8)), (0, bar))
    canvas.paste(Image.fromarray(np.clip(cz / 257.0, 0, 255).astype(np.uint8)), (N + 12, bar))
    dr = ImageDraw.Draw(canvas)
    dr.text((8, 10), "ALIGNED", fill=(120, 255, 120))
    dr.text((N + 20, 10), "null, SCALE-MATCHED to aligned (x0.9875, nearest)", fill=(255, 150, 150))
    canvas.save(os.path.join(OUT, "matched-%s.png" % name))

ga = a.astype(np.float32).mean(axis=2)
gz = zs.astype(np.float32).mean(axis=2)
print()
print("whole-frame tenengrad ratio, scale-matched: %.4f" % (tenengrad(ga) / tenengrad(gz)))
print("(unmatched it was 0.9790 -- see how much of that was pure magnification)")
