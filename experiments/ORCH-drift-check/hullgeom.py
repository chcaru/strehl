"""Is BUILD-HULL's clamped/unclamped pair actually on the same grid?

The apparent silhouette offset in the side-by-side crop could be (a) real
geometric drift, which would void every microcontrast number measured from
this pair, or (b) my eyes. A +-6 px correlation search cannot tell the
difference from a 25 px shift, so this widens the search and, independently,
locates the actual edge crossing in each arm.

Green plane, linear DN, one binary, no tone curve anywhere.
"""
import sys
import numpy as np
import tifffile

CL = r"C:\dev\strehl-out\BUILD-HULL\accept\coffee-bean--clamped.tiff"
UN = r"C:\dev\strehl-out\BUILD-HULL\accept\coffee-bean--unclamped.tiff"


def edge_x(row, lo_frac=0.5):
    """x of the first crossing of the midpoint between the row's min and max."""
    lo, hi = float(row.min()), float(row.max())
    if hi - lo < 1000:
        return None
    mid = lo + lo_frac * (hi - lo)
    above = row > mid
    flips = np.where(np.diff(above.astype(np.int8)) != 0)[0]
    return int(flips[0]) if len(flips) else None


def main():
    cl = tifffile.imread(CL)
    un = tifffile.imread(UN)
    assert cl.dtype == np.uint16 and un.dtype == np.uint16
    gc = cl[:, :, 1].astype(np.float64)
    gu = un[:, :, 1].astype(np.float64)
    print(f"shape {gc.shape}")

    # 1. Wide integer correlation on the crop that looked shifted.
    y0, x0, n = 1122, 4834, 700
    a = gc[y0:y0 + n, x0:x0 + n]
    b = gu[y0:y0 + n, x0:x0 + n]
    am = a - a.mean()
    bm = b - b.mean()
    best, bdy, bdx = -np.inf, None, None
    R = 40
    for dy in range(-R, R + 1, 1):
        for dx in range(-R, R + 1, 1):
            ay0, ay1 = max(0, dy), min(n, n + dy)
            ax0, ax1 = max(0, dx), min(n, n + dx)
            by0, by1 = max(0, -dy), min(n, n - dy)
            bx0, bx1 = max(0, -dx), min(n, n - dx)
            ov = (ay1 - ay0) * (ax1 - ax0)
            v = float((am[ay0:ay1, ax0:ax1] * bm[by0:by1, bx0:bx1]).sum()) / ov
            if v > best:
                best, bdy, bdx = v, dy, dx
    print(f"1. WIDE correlation (+-{R}px): peak at dy={bdy} dx={bdx}")

    # POTENCY CONTROL: the same search must FIND a shift I plant myself.
    planted = np.roll(b, (0, 17), axis=(0, 1))
    best2, pdy, pdx = -np.inf, None, None
    for dy in range(-R, R + 1, 1):
        for dx in range(-R, R + 1, 1):
            ay0, ay1 = max(0, dy), min(n, n + dy)
            ax0, ax1 = max(0, dx), min(n, n + dx)
            by0, by1 = max(0, -dy), min(n, n - dy)
            bx0, bx1 = max(0, -dx), min(n, n - dx)
            ov = (ay1 - ay0) * (ax1 - ax0)
            pm = planted - planted.mean()
            v = float((am[ay0:ay1, ax0:ax1] * pm[by0:by1, bx0:bx1]).sum()) / ov
            if v > best2:
                best2, pdy, pdx = v, dy, dx
    ok = (pdx == -17 and pdy == 0)
    print(f"   POTENCY: planted dx=+17 -> search reports dy={pdy} dx={pdx}  "
          f"{'PASS' if ok else 'FAIL -- the search cannot see a shift it is given'}")

    # 2. Independent: where is the silhouette edge in each arm?
    print("2. EDGE CROSSING per row, full-image x (clamped vs unclamped):")
    diffs = []
    for y in (1122, 1300, 1500, 1700, 1900):
        rc = gc[y, 4500:5600]
        ru = gu[y, 4500:5600]
        ec, eu = edge_x(rc), edge_x(ru)
        if ec is None or eu is None:
            print(f"   y={y}: no crossing")
            continue
        diffs.append(ec - eu)
        print(f"   y={y}: clamped x={4500+ec}  unclamped x={4500+eu}  delta={ec-eu:+d} px")
    if diffs:
        print(f"   mean edge delta = {np.mean(diffs):+.2f} px")

    # 3. How much of the frame actually changed, and by how much?
    d = np.abs(gc - gu)
    for t in (0, 1, 10, 100, 1000):
        print(f"3. pixels differing by > {t:5d} DN : {100.0*(d>t).mean():7.4f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
