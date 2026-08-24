"""B14 -- did the ported clip overshoot into GREEN on the `strehl stack` path?

ORCH's caution: M110's readout is one-sided by construction (green has ~0.00034
headroom on blown pixels), so it under-reports green excess. This asks the
mirror question directly on the two `strehl stack` renders M109 already holds,
using the SAME predicate with the channels swapped.

Also answers: can M110's tile selector (R and B >= 99 % full scale) even see the
population this defect lives in?

Read-only. Operates on artefacts under C:\\dev\\strehl-out\\M109.
"""

import sys

import numpy as np
import tifffile

THRESH = 0.06


def load(path):
    a = tifffile.imread(path)
    if a.dtype != np.uint16:
        raise SystemExit(f"expected uint16, got {a.dtype} in {path}")
    return a.astype(np.float32) / 65535.0


def frac(mask):
    return 100.0 * float(mask.sum()) / mask.size


def report(tag, img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    magenta = (r - g > THRESH) & (b - g > THRESH)
    green = (g - r > THRESH) & (g - b > THRESH)
    print(f"  {tag:<7}  magenta {frac(magenta):7.4f} %   green-excess {frac(green):7.4f} %")
    return magenta, green


def main():
    before, after = sys.argv[1], sys.argv[2]
    ib, ia = load(before), load(after)
    if ib.shape != ia.shape:
        raise SystemExit(f"shape mismatch {ib.shape} vs {ia.shape}")

    print(f"frame {ib.shape[1]}x{ib.shape[0]}, predicate |dC| > {THRESH}")
    print("\n=== B14: the mirror predicate, both arms ===")
    mb, gb = report("before", ib)
    ma, ga = report("after", ia)

    dg = frac(ga) - frac(gb)
    print(f"\n  green-excess delta: {dg:+.4f} pp")
    verdict = "OVERSHOOT -- the clip created green pixels" if dg > 0.01 else "NO OVERSHOOT"
    print(f"  B14 VERDICT: {verdict}")

    # Did any pixel that was NOT green-excess before become green-excess after?
    created = ga & ~gb
    print(f"  pixels turned green-excess by the clip: {int(created.sum())} ({frac(created):.4f} %)")

    # How far does green sit from the other two in the affected region?
    print("\n=== green offset in the before-magenta region ===")
    for tag, img in (("before", ib), ("after", ia)):
        r, g, b = img[..., 0], img[..., 1], img[..., 2]
        off = g[mb] - 0.5 * (r[mb] + b[mb])
        print(f"  {tag:<7}  mean {off.mean():+.4f}   min {off.min():+.4f}   max {off.max():+.4f}")

    # Can M110's selector see this population? It requires R AND B near full
    # scale; this defect lives where GREEN is pinned and R/B are not.
    print("\n=== would M110's tile selector (R and B >= 99 % FS) find these pixels? ===")
    r, g, b = ib[..., 0], ib[..., 1], ib[..., 2]
    for pct in (0.99, 0.95, 0.90):
        sel = (r >= pct) & (b >= pct)
        both = sel & mb
        share = 100.0 * float(both.sum()) / max(int(mb.sum()), 1)
        print(f"  R,B >= {pct:.2f}: {frac(sel):7.4f} % of frame; "
              f"covers {share:6.2f} % of the magenta population")

    print("\n  (raw DN from ORCH's own diagnosis of the same blob: R 7673.2, B 14116.0,")
    print("   container max 16383 -> R at 46.8 % FS, B at 86.2 % FS. Neither reaches 99 %.)")


if __name__ == "__main__":
    main()
