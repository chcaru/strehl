"""Is the single-frame CA pair a CONTROLLED pair, and where does green move?

A geometric warp cannot change a perfectly flat region: resampling a constant
returns the constant. So if `s1-default` and `s2-caoff` differ ONLY by the CA
flag, the green difference must be concentrated where there is gradient.

    G diff edge >> G diff flat  -> controlled pair; green moves via the
                                   demosaic/gather reacting to shifted R,B sites
    G diff flat ~= G diff edge  -> NOT a controlled pair (different frames,
                                   different exposure, or another difference)

This is the same edge/flat discrimination ORCH used for the chroma result and
that I used for the 157x ratio. It is applied here to green.
"""
import sys
import numpy as np
import tifffile


def main():
    base = r"D:\strehl-out\BUILD-CROP\chroma"
    pairs = [
        ("single-frame", rf"{base}\s1-default.tiff", rf"{base}\s2-caoff.tiff"),
        ("merge",        rf"{base}\m-default.tiff", rf"{base}\m-caoff.tiff"),
    ]
    print("Green movement, split by local gradient. Edge population from image A.\n")
    print(f"{'pair':14s} {'edge G mean':>12s} {'flat G mean':>12s} "
          f"{'edge/flat':>10s} {'flat px':>12s}")
    print("-" * 66)
    for tag, pa, pb in pairs:
        a = tifffile.imread(pa)
        b = tifffile.imread(pb)
        ga = a[..., 1].astype(np.float64)
        gb = b[..., 1].astype(np.float64)
        # gradient magnitude of A's green, on a decimated grid for speed
        s = 2
        g = ga[::s, ::s]
        gy = np.abs(np.diff(g, axis=0, prepend=g[:1]))
        gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
        grad = gy + gx
        d = np.abs(ga - gb)[::s, ::s]
        hi = np.percentile(grad, 99.0)
        lo = np.percentile(grad, 50.0)
        edge = grad >= hi
        flat = grad <= lo
        em = float(d[edge].mean())
        fm = float(d[flat].mean())
        ratio = em / fm if fm > 1e-9 else float("inf")
        print(f"{tag:14s} {em:12.3f} {fm:12.3f} {ratio:10.2f} {int(flat.sum()):12,}")

    print()
    print("Reading: a warp leaves flat regions untouched, so a controlled CA-only")
    print("pair must show flat G ~ 0 and a large edge/flat ratio. A flat G mean of")
    print("order tens of DN means the two renders differ by more than the flag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
