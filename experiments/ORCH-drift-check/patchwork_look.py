"""Make the background patchwork undeniable in one look.

Crops a pure-background region out of the shipped merge, magnifies it with
nearest-neighbour (so no interpolation can be blamed for what you see), and puts
a contrast-stretched copy beside it.

Writes to C:\\dev\\strehl-out\\ORCH-morning only. Never writes to D:\\.
"""
import os

import numpy as np
from PIL import Image

SRC = r"C:\dev\strehl-out\M87-before-after\00-BEFORE-shipped-merge-tight2x.png"
OUT = r"C:\dev\strehl-out\ORCH-morning"
os.makedirs(OUT, exist_ok=True)

im = Image.open(SRC).convert("L")
a = np.asarray(im).astype(np.float64)
print("source %s  %dx%d  range %.1f-%.1f" % (SRC, im.size[0], im.size[1], a.min(), a.max()))

# A window in the lower-right, which is background in every frame: no subject,
# no silhouette edge, so nothing here should carry structure.
X0, Y0, W, H = 470, 300, 240, 180
win = a[Y0 : Y0 + H, X0 : X0 + W]
print(
    "window x=%d..%d y=%d..%d  mean %.2f  sd %.3f  min %.1f max %.1f"
    % (X0, X0 + W, Y0, Y0 + H, win.mean(), win.std(), win.min(), win.max())
)

SCALE = 4
plain = Image.fromarray(win.astype(np.uint8)).resize(
    (W * SCALE, H * SCALE), Image.NEAREST
)

# Stretch to the window's own range so the steps between patches are visible at
# the amplitude they actually have, rather than at the amplitude of the frame.
lo, hi = np.percentile(win, [0.5, 99.5])
st = np.clip((win - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
stretched = Image.fromarray(st.astype(np.uint8)).resize(
    (W * SCALE, H * SCALE), Image.NEAREST
)
print("stretch maps %.2f..%.2f -> 0..255 (span %.2f of 255 levels)" % (lo, hi, hi - lo))

gap = 16
sheet = Image.new("L", (plain.width * 2 + gap, plain.height), 0)
sheet.paste(plain, (0, 0))
sheet.paste(stretched, (plain.width + gap, 0))
dst = os.path.join(OUT, "PATCHWORK-background-4x.png")
sheet.save(dst)
print("wrote %s  (%dx%d)  left=as-rendered  right=contrast-stretched" % (dst, sheet.width, sheet.height))

# How flat is "flat"? A piecewise-constant field has most of its mass at zero
# Laplacian with spikes at the boundaries.
lap = (
    -4 * win[1:-1, 1:-1]
    + win[:-2, 1:-1]
    + win[2:, 1:-1]
    + win[1:-1, :-2]
    + win[1:-1, 2:]
)
lf = lap.ravel()
kurt = ((lf - lf.mean()) ** 4).mean() / max(((lf - lf.mean()) ** 2).mean() ** 2, 1e-30)
print("laplacian sd %.4f  excess kurtosis %.2f  (gaussian = 0)" % (lf.std(), kurt - 3.0))
