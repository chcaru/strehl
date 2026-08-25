"""Generalised photometric A/B look: any subject, windows chosen symmetrically.

photometric_look.py hand-picked windows on tweezers-cpl. Hand-picking is how
fact 1629 happened. This version selects windows the same way photometric_ab.py
does -- brightness bar then smoothness, both computed on the SYMMETRIC MEAN of
the two arms -- so neither arm chooses the pixels it is judged on, and the
panels correspond to the rows of the numeric table.

    python photometric_look2.py <subject> [test-arm]

Shared stretch from the base arm. Reads only.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

ROOT = r"C:\dev\strehl-out\M116\measure"
OUT = r"C:\dev\strehl-out\ORCH-morning"
SUBJ = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
ARM = sys.argv[2] if len(sys.argv) > 2 else "A1"
S, BORDER, STRIDE = 256, 400, 128
os.makedirs(OUT, exist_ok=True)


def load(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s read as %s, expected uint16" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hf(w):
    lap = -4 * w[1:-1, 1:-1] + w[:-2, 1:-1] + w[2:, 1:-1] + w[1:-1, :-2] + w[1:-1, 2:]
    return float(np.sqrt((lap ** 2).mean()))


A0 = load(os.path.join(ROOT, "%s__A0.tif" % SUBJ))
A1 = load(os.path.join(ROOT, "%s__%s.tif" % (SUBJ, ARM)))
assert A0.shape == A1.shape
M = (A0 + A1) * 0.5
H, W = A0.shape

allw = []
for y in range(BORDER, H - S - BORDER, STRIDE):
    for x in range(BORDER, W - S - BORDER, STRIDE):
        w = M[y : y + S, x : x + S]
        allw.append((float(w.mean()), float(w[::8, ::8].std()), x, y))
bar = float(np.percentile([a[0] for a in allw], 80))
pool = sorted([a for a in allw if a[0] >= bar], key=lambda t: t[1])

picks = [("smooth%d" % i, pool[i][2], pool[i][3]) for i in range(3)]
picks.append(("textured", pool[-1][2], pool[-1][3]))

print("%s: A0 vs %s, %d windows, brightness bar %.0f" % (SUBJ, ARM, len(allw), bar))
rows = []
for tag, x, y in picks:
    w0, w1 = A0[y : y + S, x : x + S], A1[y : y + S, x : x + S]
    lo, hi = np.percentile(w0, [0.5, 99.5])
    span = max(hi - lo, 1e-9)
    panels = []
    for lum in (w0, w1):
        st = np.clip((lum - lo) / span, 0, 1) * 255.0
        panels.append(np.repeat(np.repeat(st.astype(np.uint8), 2, 0), 2, 1))
    gap = np.full((panels[0].shape[0], 12), 255, np.uint8)
    rows.append(np.concatenate([panels[0], gap, panels[1]], axis=1))
    print("  %-9s x=%-5d y=%-5d hf %8.1f -> %8.1f  ratio %.4f   lvl %.5f"
          % (tag, x, y, hf(w0), hf(w1), hf(w1) / hf(w0), w1.mean() / w0.mean()))

vgap = np.full((12, rows[0].shape[1]), 255, np.uint8)
sheet = rows[0]
for r in rows[1:]:
    sheet = np.concatenate([sheet, vgap, r], axis=0)
p = os.path.join(OUT, "PHOTOMETRIC-SHEET-%s-%s.png" % (SUBJ, ARM))
Image.fromarray(sheet).save(p)
print("wrote %s   (left A0, right %s, shared stretch; rows: 3 smoothest then most textured)"
      % (os.path.basename(p), ARM))
