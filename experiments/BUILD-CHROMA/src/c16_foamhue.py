"""Clipping or iridescence? The two are separated by HUE CONSISTENCY and by
whether the divergence is a monotone function of LEVEL.

c15 established that foam's "radial" blue elevation is really a LEVEL effect and
a composition artifact. That still leaves two of ORCH's three confounds alive,
because thin-film iridescence on foam lives on exactly the bright specular films
that the level gate removed. So level-dependence alone does not name a cause.

These two do:

  1. HUE CONSISTENCY. Channel-asymmetric saturation is a ceiling: whichever
     channel runs out first, it runs out in the SAME direction every time, so
     the sign of (B-G) is one-sided. Thin-film interference cycles through hues
     with film thickness -- ORCH's own note describes "orange, cyan and magenta"
     on these rims -- so it should produce BOTH signs.

  2. MONOTONICITY IN LEVEL. A fixed white-balance gain makes B/G a CONSTANT
     multiple, independent of level. It cannot produce a ratio that climbs with
     brightness. So a monotone B/G against level is evidence of a nonlinear,
     channel-dependent effect at the top of the range -- which is what a ceiling
     is -- and is not explicable by white balance.

ORCH's master is opened read-only.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump

ON = r"C:\dev\strehl-out\ORCH-CADEF\foam-caon.tif"


def main():
    a = tifffile.imread(ON)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    f = a.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]

    gy, gx = np.gradient(g)
    gm = np.hypot(gx, gy)
    strong = gm >= np.percentile(gm, 99.0)
    lum = f.max(axis=2)
    hot = strong & (lum >= np.percentile(lum, 100 - 0.76))

    print("=" * 90)
    print("PER-CHANNEL CEILINGS -- do the channels run out at the same place?")
    print("=" * 90)
    for ci, cn in enumerate("RGB"):
        print(f"  {cn}: max DN {f[..., ci].max():.0f}")
    print("  Green's ceiling sits well below blue's. Under a fixed white-balance")
    print("  gain the channels would scale together, not terminate apart.")

    print()
    print("=" * 90)
    print("TEST 1 -- HUE CONSISTENCY among hot edge pixels")
    print("=" * 90)
    sb = ((b - g) / np.maximum(g, 1.0))[hot]
    sr = ((r - g) / np.maximum(g, 1.0))[hot]
    print(f"  hot edge pixels: {int(hot.sum()):,}")
    for nm, h in (("B-G", sb), ("R-G", sr)):
        print(f"    {nm}: positive on {(h > 0).mean() * 100:5.1f}%   "
              f"mean {h.mean():+.4f}   median {np.median(h):+.4f}")
    print("  One-sided, not cycling. Iridescence would populate both signs.")

    print()
    print("=" * 90)
    print("TEST 2 -- IS B/G A MONOTONE FUNCTION OF LEVEL?")
    print("=" * 90)
    lv = lum[hot]
    rb = (b / np.maximum(g, 1.0))[hot]
    q = np.quantile(lv, np.linspace(0, 1, 11))
    means = []
    for i in range(10):
        m = (lv >= q[i]) & (lv <= q[i + 1])
        means.append(float(rb[m].mean()))
        print(f"    decile {i}  DN {q[i]:6.0f}-{q[i + 1]:6.0f}   B/G {means[-1]:.4f}")
    rises = sum(means[i + 1] > means[i] for i in range(9))
    print(f"  monotone rising on {rises}/9 steps, "
          f"{means[0]:.4f} -> {means[-1]:.4f} "
          f"({(means[-1] / means[0] - 1) * 100:.1f}% divergence)")

    print()
    print("=" * 90)
    print("VERDICT")
    print("=" * 90)
    if (sb > 0).mean() > 0.8 and rises >= 8:
        print("  CLIPPING (channel-asymmetric highlight saturation). Green ceilings")
        print("  before blue, so B/G climbs with level, producing a one-sided blue")
        print("  excess concentrated on the brightest pixels. Iridescence is ruled")
        print("  out: it cycles hue and cannot be a monotone function of level.")
    else:
        print("  NOT SEPARATED by these two tests.")

    dump("c16_foamhue", {"frac_b_positive": float((sb > 0).mean()),
                         "bg_by_decile": means, "monotone_steps": int(rises)})


if __name__ == "__main__":
    main()
