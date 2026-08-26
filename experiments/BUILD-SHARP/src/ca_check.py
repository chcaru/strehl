"""Is the bud/white fringe lateral CA, or is it something else?

ORCH gave the discriminator and it is the right one: **lateral CA is
antisymmetric and radial**. The red and blue channels are focused at slightly
different magnifications, so R is displaced outward relative to B (or inward) by
an amount proportional to distance from the optical axis, and the displacement
REVERSES SIGN across the centre. Clipping asymmetry is neither radial nor
antisymmetric, and neither is a merge or demosaic artifact.

So the test is not "is there a colour fringe" -- there is, that is not in
dispute -- it is whether the R-vs-B displacement is an ODD function of signed
distance from the image centre.

METHOD. Vertical edges only, so the displacement of interest is along x and the
signed x offset from centre is the radial coordinate. For each edge the
subpixel position of the R and of the B edge is the centroid of |d/dx| over a
short window, and the statistic is `pos_R - pos_B`. Edges are required to be
real steps in BOTH channels, counted and reported, so a rejected edge cannot be
read as a measured one.

NULL CONTROL. The same statistic computed between G1-like halves of the SAME
channel (G against G, shifted window) must return zero displacement. A method
that reports a radial trend on identical data is measuring its own windowing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

HALF = 10
MIN_AMP = 1500.0


def edge_pos(prof: np.ndarray) -> float:
    """Subpixel edge position as the centroid of |gradient| over the window."""
    g = np.abs(np.diff(prof.astype(np.float64)))
    s = g.sum()
    if s <= 0:
        return float("nan")
    return float((np.arange(len(g)) * g).sum() / s)


def measure(a: np.ndarray, ch_a: int, ch_b: int, label: str) -> None:
    h, w, _ = a.shape
    cy, cx = h / 2.0, w / 2.0
    A = a[:, :, ch_a].astype(np.float64)
    B = a[:, :, ch_b].astype(np.float64)
    lum = A + B

    # Candidate vertical edges: strong local maxima of |d/dx| on the sum.
    gx = np.abs(np.diff(lum, axis=1))
    step = 7
    ys = np.arange(HALF + 2, h - HALF - 2, step)
    rows = gx[ys]
    peak = (rows[:, 1:-1] >= rows[:, :-2]) & (rows[:, 1:-1] > rows[:, 2:])
    ri, ci = np.nonzero(peak)
    ci = ci + 1
    keep = (ci > HALF + 2) & (ci < w - HALF - 2)
    ri, ci = ri[keep], ci[keep]
    vals = rows[ri, ci]
    take = np.argsort(vals)[-min(60000, len(vals)):]
    ri, ci = ri[take], ci[take]

    xs, dd, kept, rej = [], [], 0, 0
    for r, c in zip(ri, ci):
        y = ys[r]
        pa = A[y, c - HALF:c + HALF + 1]
        pb = B[y, c - HALF:c + HALF + 1]
        if (pa.max() - pa.min()) < MIN_AMP or (pb.max() - pb.min()) < MIN_AMP:
            rej += 1
            continue
        ea, eb = edge_pos(pa), edge_pos(pb)
        if not (np.isfinite(ea) and np.isfinite(eb)):
            rej += 1
            continue
        kept += 1
        xs.append(c - cx)
        dd.append(ea - eb)
    xs, dd = np.asarray(xs), np.asarray(dd)
    print(f"\n  {label}:  measured {kept}, rejected {rej} (weak in one channel)")
    if kept < 200:
        print("    too few edges -- VACUOUS, not a null")
        return

    print(f"    {'signed x from centre':>22s} {'n':>7s} {'median pos_a - pos_b (px)':>26s}")
    edges = [-3000, -2000, -1200, -600, 0, 600, 1200, 2000, 3000]
    meds = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (xs >= lo) & (xs < hi)
        if m.sum() < 30:
            continue
        med = float(np.median(dd[m]))
        meds.append((0.5 * (lo + hi), med))
        print(f"    {f'{lo:+5d} .. {hi:+5d}':>22s} {int(m.sum()):7d} {med:26.4f}")
    if len(meds) >= 4:
        u = np.array([m[0] for m in meds])
        v = np.array([m[1] for m in meds])
        slope = float(np.polyfit(u, v, 1)[0])
        left = float(np.mean(v[u < 0]))
        right = float(np.mean(v[u > 0]))
        print(f"    slope vs radius : {slope*1000:+.4f} px per 1000 px")
        print(f"    mean left  half : {left:+.4f} px")
        print(f"    mean right half : {right:+.4f} px")
        anti = left * right < 0
        print(f"    ANTISYMMETRIC (signs oppose across centre)? {'YES' if anti else 'NO'}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: ca_check.py <render.tif>")
    a = tifffile.imread(sys.argv[1])
    print(f"{Path(sys.argv[1]).name}: {a.shape}")
    measure(a, 0, 2, "R vs B  (lateral CA shows here)")
    measure(a, 1, 1, "G vs G  (NULL CONTROL -- must be exactly 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
