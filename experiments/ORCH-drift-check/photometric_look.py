"""Look at the pixels behind the tweezers-cpl photometric result.

photometric_ab.py measured a 29-37% drop in laplacian RMS in the six smoothest
background windows of tweezers-cpl, converging to a floor near 45-53 counts.
Three things could do that:
  (a) removing manufactured mosaic   -- the claim
  (b) blurring                       -- would also destroy real detail
  (c) a different, smoother election -- neither of the above

Numbers cannot separate these; pixels can. Both panels get the SAME stretch
bounds, taken from the base arm, because independent per-panel stretching makes
a visual A/B meaningless (fact 1630 / discipline 832).

A detail window over real subject structure is rendered alongside, because (b)
predicts visible softening there and (a) predicts none.
"""
import os

import numpy as np
import tifffile
from PIL import Image

ROOT = r"C:\dev\strehl-out\M116\measure"
OUT = r"C:\dev\strehl-out\ORCH-morning"
SUBJ = "tweezers-cpl"
S = 256

# (tag, x, y) -- the first three are the smooth windows that moved most,
# the last is a textured window that did not move (hf ratio 1.022).
WINDOWS = [
    ("smooth-912x400", 912, 400),
    ("smooth-1040x400", 1040, 400),
    ("textured-400x656", 400, 656),
]

os.makedirs(OUT, exist_ok=True)


def load(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s read as %s, expected uint16" % (p, a.dtype))
    return a


A0 = load(os.path.join(ROOT, "%s__A0.tif" % SUBJ))
A1 = load(os.path.join(ROOT, "%s__A1.tif" % SUBJ))
print("A0 %s %s   A1 %s %s" % (A0.shape, A0.dtype, A1.shape, A1.dtype))

for tag, x, y in WINDOWS:
    w0 = A0[y : y + S, x : x + S]
    w1 = A1[y : y + S, x : x + S]
    l0 = w0[..., :3].astype(np.float64).mean(axis=2)
    l1 = w1[..., :3].astype(np.float64).mean(axis=2)

    # shared stretch, bounds from the BASE arm only
    lo, hi = np.percentile(l0, [0.5, 99.5])
    span = max(hi - lo, 1e-9)

    panels = []
    for lum in (l0, l1):
        st = np.clip((lum - lo) / span, 0, 1) * 255.0
        panels.append(np.repeat(np.repeat(st.astype(np.uint8), 2, axis=0), 2, axis=1))

    gap = np.full((panels[0].shape[0], 12), 255, np.uint8)
    sheet = np.concatenate([panels[0], gap, panels[1]], axis=1)
    p = os.path.join(OUT, "PHOTOMETRIC-%s-%s.png" % (SUBJ, tag))
    Image.fromarray(sheet).save(p)
    print("%-18s A0 mean %8.1f sd %7.2f | A1 mean %8.1f sd %7.2f | stretch span %.0f -> %s"
          % (tag, l0.mean(), l0.std(), l1.mean(), l1.std(), span, os.path.basename(p)))
print()
print("left panel = A0 (default), right panel = A1 (--photometric), identical stretch")
