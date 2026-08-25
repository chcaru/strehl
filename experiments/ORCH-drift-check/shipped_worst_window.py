"""Show the worst patchwork window of the SHIPPED render, next to a calibrated plant.

The number the shipped render produces (worst window 89.94 against a synthetic
Voronoi plant of 41.81) is only meaningful if the window looks like what the
plant looks like. This crops both and puts them side by side.

Reads only. Writes to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
OUT = r"C:\dev\strehl-out\ORCH-morning"
S = 256
BAR = 10.0


def excess_kurtosis(win):
    lap = (-4 * win[1:-1, 1:-1] + win[:-2, 1:-1] + win[2:, 1:-1]
           + win[1:-1, :-2] + win[1:-1, 2:])
    f = lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    return (((f - mu) ** 4).mean() / v**2 - 3.0) if v > 0 else float("nan")


a = tifffile.imread(SRC)
if a.dtype != np.uint16:
    raise SystemExit("%s is %s, expected uint16" % (SRC, a.dtype))
L = a[..., :3].astype(np.float64).mean(axis=2)
H, W = L.shape
print("%s  %dx%d %s" % (os.path.basename(SRC), W, H, a.dtype))

border, stride = max(200, min(H, W) // 8), max(128, min(H, W) // 16)
cands = []
for y in range(border, H - S - border, stride):
    for x in range(border, W - S - border, stride):
        w = L[y : y + S, x : x + S]
        cands.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
bright = float(np.percentile([c[0] for c in cands], 80))
pool = sorted([c for c in cands if c[0] >= bright], key=lambda t: t[1])[:12]

scored = sorted(((excess_kurtosis(L[y : y + S, x : x + S]), x, y) for _, _, x, y in pool),
                reverse=True)
for k, x, y in scored:
    print("  kurt %8.2f at x=%d y=%d %s" % (k, x, y, "<-- worst" if (k, x, y) == scored[0] else ""))

kw, xw, yw = scored[0]
kb, xb, yb = scored[-1]
worst = L[yw : yw + S, xw : xw + S]
best = L[yb : yb + S, xb : xb + S]

rng = np.random.default_rng(7)
sd = float(worst.std())
yy, xx = np.mgrid[0:S, 0:S]
pts = rng.integers(0, S, (60, 2))
lv = rng.normal(0, sd, 60)
d2 = (yy[..., None] - pts[:, 0]) ** 2 + (xx[..., None] - pts[:, 1]) ** 2
plant = lv[np.argmin(d2, axis=2)] + worst.mean()
kp = excess_kurtosis(plant)

panels = [
    ("SHIPPED render, worst window  kurt %.1f" % kw, worst),
    ("SHIPPED render, cleanest window  kurt %.1f" % kb, best),
    ("synthetic Voronoi plant  kurt %.1f" % kp, plant),
]
Z, pad, lab = 3, 12, 30
sheet = Image.new("L", ((S * Z + pad) * len(panels) - pad, S * Z + lab), 255)
d = ImageDraw.Draw(sheet)
for i, (t, w) in enumerate(panels):
    lo, hi = np.percentile(w, [0.5, 99.5])
    st = np.clip((w - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
    sheet.paste(Image.fromarray(st.astype(np.uint8)).resize((S * Z, S * Z), Image.NEAREST),
                (i * (S * Z + pad), lab))
    d.text((i * (S * Z + pad) + 8, 9), t, fill=0)
    print("%-46s sd=%8.1f  stretch span=%.0f" % (t, w.std(), hi - lo))

p = os.path.join(OUT, "SHIPPED-worst-vs-plant.png")
sheet.save(p)
print("wrote %s" % p)
