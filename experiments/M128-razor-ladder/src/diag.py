"""M-PHASE0-EDGE / diag — show the raw edge locus and the averaged ESF.

Diagnostic for the geometry census: prints the 50%-crossing locus against its
cubic fit, and the binned ESF, so that a bad residual or a bad rise can be
attributed to the subject or to the estimator rather than guessed at.
"""

import argparse

import numpy as np

import geom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--orient", choices=["h", "v"], default="h")
    ap.add_argument("--bright-first", action="store_true")
    ap.add_argument("--x0", type=int, default=0)
    ap.add_argument("--x1", type=int, default=3514)
    ap.add_argument("--band", nargs=2, type=int, default=None)
    ap.add_argument("--half", type=int, default=32)
    args = ap.parse_args()

    g1, _g2, black = geom.read_greens(args.frame)
    a = geom.orient(g1, args.orient)
    if args.band:
        b0, b1 = args.band
    else:
        b0, b1, row = geom.find_band(a)
        print(f"auto band {b0}..{b1} (step row {row})")
    sl = np.ascontiguousarray(a[:, args.x0:args.x1])
    x, y, hi, lo = geom.crossings(sl, b0, b1, args.bright_first)
    print(f"columns {args.x1 - args.x0}, clean crossings {len(x)}, "
          f"hi {np.median(hi):.0f} lo {np.median(lo):.0f}")

    p3, xn, r3, keep = geom.fit_poly(x, y, 3)
    fit = np.polyval(p3, xn)
    res = y - fit
    print(f"cubic residual RMS {r3:.4f} px over {keep.sum()} kept")
    print("\nlocus, 64-column blocks: x, y_median, fit, resid_median, resid_IQR")
    step = max(1, len(x) // 40)
    for i in range(0, len(x) - step, step):
        sx = x[i:i + step]
        sy = y[i:i + step]
        sr = res[i:i + step]
        q = np.percentile(sr, [25, 75])
        print(f"  x {sx.mean():7.0f}  y {np.median(sy):9.3f}  "
              f"fit {np.median(fit[i:i + step]):9.3f}  "
              f"res {np.median(sr):+7.3f}  IQR {q[1] - q[0]:6.3f}")

    e = geom.esf(sl, x, fit, keep, args.bright_first, half=args.half)
    if not e:
        print("no ESF")
        return
    cc, ee, nl = e
    print(f"\nESF from {nl} scanlines, {len(cc)} bins")
    top = float(np.max(ee))
    for i in range(0, len(cc), 2):
        bar = "#" * int(60 * max(ee[i], 0) / max(top, 1))
        print(f"  {cc[i]:+7.3f} {ee[i]:9.1f} {bar}")


if __name__ == "__main__":
    main()
