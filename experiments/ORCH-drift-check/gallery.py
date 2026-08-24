"""Build the gallery: what strehl actually produces, exposed correctly.

The owner's verdict was that the stacks do not look good yet.  Fact 1253
established the render is tonally faithful and fact 1257 that 19 of 23
captures are under-exposed, median +2.01 stops.  So the fix for what he is
looking at is exposure, and the honest way to show it is to apply exposure
ONLY -- the operation a raw converter's slider performs.

NOT DONE HERE, deliberately, because any of them would flatter the output:
no contrast curve, no saturation, no sharpening, no local adjustment, no
noise reduction, no lens correction.  A single global gain in linear light,
then the sRGB transfer curve.  Every gain is reported.

READ-ONLY on D:\\.  All output goes to C:\\dev\\strehl-out\\ORCH-gallery.
"""
import os
import subprocess
import sys
import time
import glob
import numpy as np
import tifffile
from PIL import Image

ROOT = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\ORCH-gallery"
EXE = r".cargo-target-orch\release\strehl.exe"
os.makedirs(OUT, exist_ok=True)

STACKS = [
    "bee-3-cpl",
    "lavendar-cpl",
    "flowers-cpl",
    "leaf-2-cpl",
    "flower-bud-alone-cpl",
    "tweezers-cpl",
    "coffee-bean",
]

TARGET = 0.92          # where p99.9 lands in linear light after the gain
CLIP_BUDGET = 0.005    # refuse a gain that clips more than 0.5% of pixels


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def stack_one(name):
    src = os.path.join(ROOT, name)
    dst = os.path.join(OUT, "%s-srgb.tif" % name)
    if os.path.exists(dst):
        print("  [skip] %s already stacked" % name)
        return dst
    n = len(glob.glob(os.path.join(src, "*.ARW")))
    print("  [stack] %s (%d frames) ..." % (name, n), flush=True)
    t0 = time.time()
    r = subprocess.run(
        [EXE, "stack", src, "--out", dst, "--srgb", "--demosaic"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] %s rc=%d" % (name, r.returncode))
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        return None
    print("  [ok] %s in %.1f s" % (name, time.time() - t0), flush=True)
    return dst


def detail_peak(gray, box=900):
    """Coordinates of the most-detailed box, found on a downsampled copy."""
    s = 8
    g = gray[::s, ::s].astype(np.float32)
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    e = gx * gx + gy * gy
    r = max(box // (2 * s), 1)
    c = np.zeros((e.shape[0] + 1, e.shape[1] + 1))
    np.cumsum(np.cumsum(e.astype(np.float64), 0), 1, out=c[1:, 1:])
    H, W = e.shape
    y0 = np.clip(np.arange(H) - r, 0, H)
    y1 = np.clip(np.arange(H) + r, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W)
    x1 = np.clip(np.arange(W) + r, 0, W)
    tot = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
           - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
    iy, ix = np.unravel_index(int(np.argmax(tot)), tot.shape)
    return iy * s, ix * s


print("=" * 74)
print("STACKING")
print("=" * 74)
paths = {}
for n in STACKS:
    p = stack_one(n)
    if p:
        paths[n] = p

print()
print("=" * 74)
print("EXPOSURE (global gain in linear light, nothing else)")
print("=" * 74)
print("%-30s %8s %9s %9s" % ("stack", "gain", "stops", "clipped"))
print("-" * 74)
thumbs = []
for n, p in paths.items():
    a = tifffile.imread(p).astype(np.float32) / 65535.0
    lin = srgb_to_linear(a)
    p999 = float(np.percentile(lin, 99.9))
    gain = min(TARGET / max(p999, 1e-6), 64.0)
    boosted = lin * gain
    clip = float((boosted.max(axis=2) > 1.0).mean())
    if clip > CLIP_BUDGET:
        lo, hi = 1.0, gain
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if float(((lin * mid).max(axis=2) > 1.0).mean()) > CLIP_BUDGET:
                hi = mid
            else:
                lo = mid
        gain = lo
        boosted = lin * gain
        clip = float((boosted.max(axis=2) > 1.0).mean())
    out = linear_to_srgb(boosted)
    print("%-30s %7.3fx %+8.2f %8.4f%%"
          % (n, gain, np.log2(gain), 100 * clip))

    tifffile.imwrite(os.path.join(OUT, "%s-exposed.tif" % n),
                     (out * 65535.0).astype(np.uint16))
    prev = (out[::6, ::6] * 255).astype(np.uint8)
    Image.fromarray(prev).save(os.path.join(OUT, "%s-preview.png" % n))
    thumbs.append((n, prev))

    gray = out.mean(axis=2)
    cy, cx = detail_peak(gray)
    N = 900
    y = int(np.clip(cy - N // 2, 0, out.shape[0] - N))
    x = int(np.clip(cx - N // 2, 0, out.shape[1] - N))
    Image.fromarray((out[y:y + N, x:x + N] * 255).astype(np.uint8)).save(
        os.path.join(OUT, "%s-100pct.png" % n))

    sbs = np.concatenate([(a[::6, ::6] * 255).astype(np.uint8), prev], axis=1)
    Image.fromarray(sbs).save(os.path.join(OUT, "%s-before-after.png" % n))

if thumbs:
    tw = min(t.shape[1] for _, t in thumbs)
    th = min(t.shape[0] for _, t in thumbs)
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    sheet = np.full((rows * th + (rows + 1) * 8, cols * tw + (cols + 1) * 8, 3),
                    18, np.uint8)
    for i, (n, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        y = 8 + r * (th + 8)
        x = 8 + c * (tw + 8)
        sheet[y:y + th, x:x + tw] = t[:th, :tw]
    Image.fromarray(sheet).save(os.path.join(OUT, "CONTACT-SHEET.png"))
    print()
    print("wrote CONTACT-SHEET.png (%d stacks)" % len(thumbs))
print("gallery in %s" % OUT)
