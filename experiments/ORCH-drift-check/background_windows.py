"""What does the shipped render's background ACTUALLY look like?

Two window-selection rules gave two different stories (median kurtosis 2.48 vs
23.50) because one of them ranked windows by the smoothness of the very arm
under test, which selects away from the defect. Rather than argue from a
statistic, this lays out all twelve unbiased windows and labels each with its
number, so the picture and the number are next to each other.

The single input frame is tiled the same way underneath for comparison.

Reads only. Writes to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
OUT = r"C:\dev\strehl-out\ORCH-morning"
S = 256


def lum(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s is %s, expected uint16" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def excess_kurtosis(win):
    lap = (-4 * win[1:-1, 1:-1] + win[:-2, 1:-1] + win[2:, 1:-1]
           + win[1:-1, :-2] + win[1:-1, 2:])
    f = lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    return (((f - mu) ** 4).mean() / v**2 - 3.0) if v > 0 else float("nan")


def windows(L):
    H, W = L.shape
    border, stride = max(200, min(H, W) // 8), max(128, min(H, W) // 16)
    c = []
    for y in range(border, H - S - border, stride):
        for x in range(border, W - S - border, stride):
            c.append((float(L[y : y + S, x : x + S].mean()), x, y))
    bright = float(np.percentile([t[0] for t in c], 80))
    return sorted([t for t in c if t[0] >= bright], key=lambda t: (-t[0], t[2], t[1]))[:12]


def strip(path, label):
    L = lum(path)
    ws = windows(L)
    out = []
    for _, x, y in ws:
        w = L[y : y + S, x : x + S]
        out.append((excess_kurtosis(w), x, y, w))
    print("%s: kurtosis %s" % (label, " ".join("%.1f" % t[0] for t in out)))
    print("   median %.2f" % np.median([t[0] for t in out]))
    return out


rows = [
    ("SHIPPED RENDER (bee-3)", strip(r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif",
                                    "shipped render")),
    ("SINGLE INPUT FRAME (no merge in its history)",
     strip(r"C:\dev\strehl-out\M93-out\armF-f173.tif", "single frame")),
]

pad, lab, hdr = 6, 18, 26
cols = 12
sheet = Image.new("L", (cols * (S + pad) - pad, len(rows) * (S + lab + hdr)), 255)
d = ImageDraw.Draw(sheet)
for r, (title, items) in enumerate(rows):
    top = r * (S + lab + hdr)
    d.text((4, top + 5), title, fill=0)
    for i, (k, x, y, w) in enumerate(items):
        lo, hi = np.percentile(w, [0.5, 99.5])
        st = np.clip((w - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
        sheet.paste(Image.fromarray(st.astype(np.uint8)), (i * (S + pad), top + hdr))
        d.text((i * (S + pad) + 3, top + hdr + S + 2), "k=%.1f" % k, fill=0)
p = os.path.join(OUT, "BACKGROUND-12-WINDOWS.png")
sheet.save(p)
print("wrote %s" % p)
