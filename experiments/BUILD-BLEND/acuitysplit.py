"""Does an acuity drop live at the EDGES or in the FLAT?

accept.py's acuity is `mean |Laplacian| of green over pixels above the 20th
luminance percentile`. That population is not "detail". On a subject that is
mostly smooth -- 109MSDCF is marker strokes on white paper, and the paper is
bright enough to be "lit" -- most of those pixels are flat, and in a flat region
|Laplacian| is noise. A mean over them reports the noise level with the edges
as a minority contribution.

So a lower acuity has two completely different causes:

    the EDGES got softer    -> real detail loss, do not ship
    the FLAT got quieter    -> less noise, which is an improvement the metric
                               scores as a regression

A single scalar cannot separate them, and this project has already been misled
twice by exactly this shape of statistic: microC read a 33% "loss" on
coffee-bean where 1:1 inspection showed none, and gradenergy read a backdrop as
10.97x noisier when the real figure was 1.14x once the clipped tiles were
excluded.

METHOD
    Partition the pixels ONCE, on the CONTROL arm, then read both arms through
    that fixed partition. Partitioning per-arm would move the population with
    the treatment, which is the same error as letting each arm pick its own
    subject mask.

        EDGE   top EDGE_PCT of control gradient magnitude, dilated so the
               shoulder of an edge counts as edge rather than as flat
        FLAT   bottom FLAT_PCT of control gradient magnitude, eroded by the
               same amount so no edge shoulder leaks in

    Both restricted to accept.py's own lit population (>20th luminance
    percentile) so the numbers are comparable to its acuity column.

USAGE
    python acuitysplit.py <control.tif> <treatment.tif> [label]
"""
import sys

import numpy as np
import tifffile
from scipy import ndimage

if len(sys.argv) < 3:
    sys.exit(__doc__)

CONTROL, TREAT = sys.argv[1], sys.argv[2]
LABEL = sys.argv[3] if len(sys.argv) > 3 else ""

EDGE_PCT = 98.0   # top 2% of gradient magnitude
FLAT_PCT = 50.0   # bottom 50%
GROW = 3          # px, dilate edges / erode flat


def green(path):
    im = tifffile.imread(path)
    assert im.dtype == np.uint16, f"{path}: expected uint16 linear, got {im.dtype}"
    # accept.py measures the GREEN channel. Match it exactly, or the numbers
    # here cannot be compared with the column they are explaining.
    return im[:, :, 1].astype(np.float32)


def laplacian(g):
    lap = np.zeros_like(g)
    lap[1:-1, 1:-1] = (
        4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    )
    return np.abs(lap)


c, t = green(CONTROL), green(TREAT)
assert c.shape == t.shape, f"different grids: {c.shape} vs {t.shape}"

print(f"=== acuity, split by population {('-- ' + LABEL) if LABEL else ''} ===")
print(f"  control  : {CONTROL}")
print(f"  treatment: {TREAT}")

lit = c > np.percentile(c, 20.0)

gy, gx = np.gradient(c)
gm = np.hypot(gx, gy)
e_thr = np.percentile(gm[lit], EDGE_PCT)
f_thr = np.percentile(gm[lit], FLAT_PCT)

edge = ndimage.binary_dilation(gm >= e_thr, iterations=GROW) & lit
flat = ndimage.binary_erosion(gm <= f_thr, iterations=GROW) & lit

lc, lt = laplacian(c), laplacian(t)

print(f"  lit population    : {lit.mean()*100:.1f}% of frame")
print(f"  EDGE (top {100-EDGE_PCT:.0f}% grad, +{GROW}px) : {edge.mean()*100:.2f}% of frame")
print(f"  FLAT (bot {FLAT_PCT:.0f}% grad, -{GROW}px) : {flat.mean()*100:.2f}% of frame")
print()

print("  population        control   pyramid     ratio")
rows = [("ALL lit (= accept.py acuity)", lit), ("EDGE", edge), ("FLAT", flat)]
out = {}
for name, m in rows:
    if m.sum() < 1000:
        print(f"  {name:<26} -- too few px ({int(m.sum())})")
        continue
    a, b = float(lc[m].mean()), float(lt[m].mean())
    out[name] = b / a if a else float("nan")
    print(f"  {name:<26} {a:9.2f} {b:9.2f}   {b/a:7.1%}")

print()
print("--- reading ------------------------------------------------------")
e = out.get("EDGE")
f = out.get("FLAT")
if e is not None and f is not None:
    if e >= 0.98 and f < 0.98:
        print("  The EDGES are preserved and the FLAT is quieter. The acuity")
        print("  column is reporting REMOVED NOISE as lost detail. Not softening.")
    elif e < 0.98:
        print("  The EDGES themselves lost amplitude. That is REAL SOFTENING and")
        print("  no amount of noise argument excuses it.")
    else:
        print("  Edges preserved and flat unchanged; the acuity column is not")
        print("  explained by either population. Look further before concluding.")
    print(f"  edge ratio {e:.1%}   flat ratio {f:.1%}")
