"""Render the same background window from several arms on ONE shared stretch.

Independent per-panel stretching makes a visual A/B meaningless: an arm that
genuinely flattened the background gets its remaining noise amplified until it
looks as bad as the arm that did not. Every panel here uses the same lo/hi,
taken from the reference arm, so a flatter panel looks flatter.

Reads only. Writes to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-morning"
M93 = r"C:\dev\strehl-out\M93-out"
ARMS = [
    ("gate0 (shipped default)", "armM-gate0-binlin.tif"),
    ("gate4 (gated merge)", "armM4-gate4-binlin.tif"),
    ("single input frame", "armF-f173.tif"),
]
X, Y, S = 2832, 400, 256
REF = 0  # panel whose percentiles define the shared stretch


def lum(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s is %s, expected uint16" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


wins = [(t, lum(os.path.join(M93, f))[Y : Y + S, X : X + S]) for t, f in ARMS]
lo, hi = np.percentile(wins[REF][1], [0.5, 99.5])
span = hi - lo
print("shared stretch from %s: lo=%.0f hi=%.0f span=%.0f of 65535" % (wins[REF][0], lo, hi, span))

Z = 3
pad, lab = 12, 30
sheet = Image.new("L", ((S * Z + pad) * len(wins) - pad, S * Z + lab), 255)
d = ImageDraw.Draw(sheet)
for i, (t, w) in enumerate(wins):
    st = np.clip((w - lo) / max(span, 1e-9), 0, 1) * 255.0
    sd = float(w.std())
    im = Image.fromarray(st.astype(np.uint8)).resize((S * Z, S * Z), Image.NEAREST)
    sheet.paste(im, (i * (S * Z + pad), lab))
    d.text((i * (S * Z + pad) + 8, 9), "%s   sd=%.0f counts" % (t, sd), fill=0)
    print("%-26s window sd = %8.1f counts   mean = %8.1f" % (t, sd, float(w.mean())))

p = os.path.join(OUT, "AB-SHARED-STRETCH.png")
sheet.save(p)
print("wrote %s" % p)
