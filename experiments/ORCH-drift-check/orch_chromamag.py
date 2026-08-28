"""Hue-neutral chroma error at edges: does turning the CA correction off help?

BUILD-CROP measured the shipping default at 1.82x worse than `--fix-ca off`
using an edge-MAGENTA count. That statistic is specific to one artifact shape.
The over-correction produces magenta because it drives R and B to the SAME side
of an edge; switching the correction off restores the lens's natural artifact,
which drives them to OPPOSITE sides and reads as separated orange and cyan. A
magenta counter is blind to the second shape by construction, so it can score
the alternative as better while the alternative is merely differently wrong.

Looking at four sites in `orch_abdiff.py`'s montage of the two renders, CA OFF
appeared MORE saturated, not less. This measures it rather than asserting it.

The metric is the magnitude of the chroma vector about neutral,

    c = sqrt( (R-G)^2 + (B-G)^2 ) / max(G, floor)

which is invariant to the SIGN and the DIRECTION of the displacement and so
scores magenta and orange/cyan on the same footing. It is evaluated in a thin
annulus about high-contrast luma edges, where displacement lives, with flat
regions as the control: a colour CAST would move both, a displacement moves
only the edge population.

Commissioning is the point of this file, not an afterthought. The metric is
planted with BOTH artifact shapes -- same-direction (magenta) and
opposite-direction (lens-like) -- and must respond to both. A metric that
responds only to the shape its author was looking at is exactly the defect
being corrected here.
"""
import argparse
import sys

import numpy as np
import tifffile


def load(path):
    a = tifffile.imread(path)
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit("REFUSED: %s is %r, expected (H, W, >=3)" % (path, a.shape))
    return a[:, :, :3].astype(np.float64)


def chroma_mag(img, floor=256.0):
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    denom = np.maximum(g, floor)
    return np.sqrt(((r - g) / denom) ** 2 + ((b - g) / denom) ** 2)


def luma_grad(img):
    g = img[:, :, 1]
    gy = np.zeros_like(g)
    gx = np.zeros_like(g)
    gy[1:-1, :] = (g[2:, :] - g[:-2, :]) * 0.5
    gx[:, 1:-1] = (g[:, 2:] - g[:, :-2]) * 0.5
    return np.hypot(gy, gx)


def populations(img, edge_pct=99.0, flat_pct=40.0):
    """Split into an edge population and a flat control population."""
    grad = luma_grad(img)
    hi = np.percentile(grad, edge_pct)
    lo = np.percentile(grad, flat_pct)
    return grad >= hi, grad <= lo


def score(img, edge_mask, flat_mask):
    c = chroma_mag(img)
    return {
        "edge_mean": float(c[edge_mask].mean()),
        "edge_p99": float(np.percentile(c[edge_mask], 99.0)),
        "flat_mean": float(c[flat_mask].mean()),
        "ratio": float(c[edge_mask].mean() / max(c[flat_mask].mean(), 1e-9)),
    }


def shift_channel(img, ch, dy, dx):
    out = img.copy()
    out[:, :, ch] = np.roll(np.roll(img[:, :, ch], dy, axis=0), dx, axis=1)
    return out


def commission(img, edge_mask, flat_mask):
    """Both artifact shapes must move the metric. Sensitivity AND specificity."""
    base = score(img, edge_mask, flat_mask)
    print("=== COMMISSIONING ===")
    print("baseline                          edge_mean %.5f" % base["edge_mean"])

    arms = []

    same = shift_channel(shift_channel(img, 0, 0, 1), 2, 0, 1)
    s = score(same, edge_mask, flat_mask)
    arms.append(("same-direction (magenta shape): R+1px, B+1px", s, base))

    opp = shift_channel(shift_channel(img, 0, 0, 1), 2, 0, -1)
    s = score(opp, edge_mask, flat_mask)
    arms.append(("opposite-direction (lens shape): R+1px, B-1px", s, base))

    null = img.copy()
    s = score(null, edge_mask, flat_mask)
    arms.append(("NULL: unmodified copy", s, base))

    ok = True
    for name, s, b in arms:
        delta = s["edge_mean"] - b["edge_mean"]
        rel = 100.0 * delta / max(b["edge_mean"], 1e-9)
        is_null = name.startswith("NULL")
        good = (abs(delta) < 1e-12) if is_null else (delta > 0 and rel > 5.0)
        ok = ok and good
        print("  %-46s edge_mean %.5f  delta %+.5f (%+.1f%%)  %s"
              % (name, s["edge_mean"], delta, rel, "OK" if good else "**FAIL**"))
    print("COMMISSION: %s" % ("GREEN -- responds to BOTH shapes, silent on the null"
                              if ok else "RED"))
    print()
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    args = ap.parse_args()

    a = load(args.a)
    b = load(args.b)
    if a.shape != b.shape:
        raise SystemExit("REFUSED: geometry differs %r vs %r" % (a.shape, b.shape))

    # ONE population, derived from A, applied to both. Deriving the edge mask
    # separately per image would compare different pixel sets and the numbers
    # would not be commensurable.
    edge_mask, flat_mask = populations(a)
    print("edge population: %d px   flat control: %d px   (masks from A, applied to both)"
          % (int(edge_mask.sum()), int(flat_mask.sum())))
    print()

    if not commission(a, edge_mask, flat_mask):
        raise SystemExit("REFUSED: metric failed commissioning; its verdict on "
                         "the real pair would mean nothing")

    sa = score(a, edge_mask, flat_mask)
    sb = score(b, edge_mask, flat_mask)
    print("=== VERDICT ===")
    print("%-34s edge_mean  edge_p99   flat_mean  edge/flat" % "")
    for nm, s in ((args.label_a, sa), (args.label_b, sb)):
        print("%-34s %9.5f %9.5f %11.5f %10.1f"
              % (nm, s["edge_mean"], s["edge_p99"], s["flat_mean"], s["ratio"]))
    print()
    d = 100.0 * (sb["edge_mean"] - sa["edge_mean"]) / max(sa["edge_mean"], 1e-9)
    print("B vs A at edges: %+.1f%%" % d)
    if d < -2.0:
        print("=> %s has LESS total chroma error at edges." % args.label_b)
    elif d > 2.0:
        print("=> %s has MORE total chroma error at edges. A hue-specific "
              "statistic that preferred it was measuring the artifact it was "
              "written for, not the artifact a viewer meets." % args.label_b)
    else:
        print("=> indistinguishable at edges (within 2%). The two are "
              "differently wrong by the same amount.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
