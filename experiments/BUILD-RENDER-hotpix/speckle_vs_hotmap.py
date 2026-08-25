"""Are the coloured speckles in the gallery hot pixels?

The gallery JPEG of `foam` shows isolated magenta/orange/cyan dots on a subject
that is physically monochrome black foam. Two explanations are available and
they have different fixes:

  - chroma noise amplified by the develop path
  - hot sensor sites surviving the merge

This decides between them by colocation against the persistent-hot map derived
from D:\\macro-dark-frames, and it does NOT accept colocation on its own. A hot
map covering 8685 sites will collect some speckles by chance. So the same test
is run against random positions with the identical detector and the identical
tolerance, and the finding is the RATIO. If speckles hit the hot map at the same
rate as random points do, they are not hot pixels and this script should say so.

Measured on the CAMERA-LINEAR render, never on --srgb.

usage:  python speckle_vs_hotmap.py <linear.tif> [--hot <hot-persistent-xy.npy>]
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import tifffile


def neighbour_max(a):
    """Max over the 8 neighbours of each pixel, centre excluded."""
    p = np.pad(a, 1, mode="edge")
    out = np.full(a.shape, -np.inf, dtype=np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            sl = p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]
            np.maximum(out, sl, out=out)
    return out


def detect(img, excess_dn):
    """Isolated bright outliers: brighter than every neighbour by excess_dn.

    A defocused optical point cannot do this. The system PSF is several pixels
    across at every focus setting, so any real feature is shared with at least
    one neighbour. A site that beats all eight by a wide margin is not optics.
    """
    hits = np.zeros(img.shape[:2], dtype=bool)
    per_channel = []
    for c in range(3):
        a = img[:, :, c].astype(np.float32)
        h = (a - neighbour_max(a)) >= excess_dn
        per_channel.append(int(h.sum()))
        hits |= h
    return hits, per_channel


def hit_rate(ys, xs, hotset, tol):
    """Fraction of the given points within Chebyshev tol of a hot site."""
    if len(ys) == 0:
        return 0.0, 0
    n = 0
    offsets = [(dy, dx)
               for dy in range(-tol, tol + 1)
               for dx in range(-tol, tol + 1)]
    for y, x in zip(ys, xs):
        for dy, dx in offsets:
            if (y + dy, x + dx) in hotset:
                n += 1
                break
    return n / len(ys), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tif")
    ap.add_argument("--hot", default=r"C:\dev\strehl-out\hotpixels\hot-persistent-xy.npy")
    ap.add_argument("--excess", type=float, default=250.0)
    ap.add_argument("--tol", type=int, default=2)
    ap.add_argument("--max-points", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20260825)
    args = ap.parse_args()

    img = tifffile.imread(args.tif)
    assert img.dtype == np.uint16, f"expected uint16, got {img.dtype}"
    assert img.ndim == 3 and img.shape[2] == 3, f"expected RGB, got {img.shape}"
    print(f"image      : {args.tif}")
    print(f"shape      : {img.shape}  dtype {img.dtype}")

    hits, per_channel = detect(img, args.excess)
    ys, xs = np.nonzero(hits)
    total = len(ys)
    ppm = 1e6 * total / (img.shape[0] * img.shape[1])
    print(f"detector   : brighter than all 8 neighbours by >= {args.excess:.0f} DN")
    print(f"speckles   : {total}  ({ppm:.2f} ppm)   per-channel R/G/B "
          f"{per_channel[0]}/{per_channel[1]}/{per_channel[2]}")

    if total:
        v = img[ys, xs, :].astype(np.float32)
        mx = v.max(axis=1)
        mn = v.min(axis=1)
        frac_coloured = float(((mx - mn) / np.maximum(mx, 1.0) > 0.35).mean())
        print(f"coloured   : {100 * frac_coloured:.1f}% have (max-min)/max > 0.35 "
              f"-- i.e. a single channel is the outlier")

    hot = np.load(args.hot)
    print(f"hot map    : {args.hot}  {hot.shape}")
    if hot.ndim == 2 and hot.shape[1] == 2:
        pairs = hot
    else:
        pairs = hot.T
    h0, h1 = pairs[:, 0], pairs[:, 1]
    H, W = img.shape[:2]
    if h0.max() < H and h1.max() < W:
        hy, hx = h0, h1
    elif h1.max() < H and h0.max() < W:
        hy, hx = h1, h0
    else:
        print("!! hot map does not fit the image; cannot colocate")
        return 2
    hotset = set(zip(hy.tolist(), hx.tolist()))
    print(f"hot sites  : {len(hotset)} unique, fitted as (y,x) in {H}x{W}")

    rng = np.random.default_rng(args.seed)
    if total > args.max_points:
        sel = rng.choice(total, args.max_points, replace=False)
        sy, sx = ys[sel], xs[sel]
    else:
        sy, sx = ys, xs

    rate, n = hit_rate(sy, sx, hotset, args.tol)
    ry = rng.integers(0, H, size=len(sy))
    rx = rng.integers(0, W, size=len(sx))
    nrate, nn = hit_rate(ry, rx, hotset, args.tol)

    print()
    print(f"tested     : {len(sy)} speckles, tolerance +/-{args.tol} px")
    print(f"  speckles within tol of a persistent-hot site : {n:6d}  ({100*rate:.2f}%)")
    print(f"  NULL: random positions, same count           : {nn:6d}  ({100*nrate:.2f}%)")
    if nrate > 0:
        print(f"  enrichment over chance                       : {rate / nrate:.2f}x")
    else:
        print(f"  enrichment over chance                       : null found none")

    print()
    if nrate > 0 and rate / nrate >= 3.0:
        print("VERDICT: the speckles ARE hot pixels. They land on known-hot sensor")
        print("         sites far above chance. Repair belongs in the decode path.")
    elif nrate == 0 and rate > 0.05:
        print("VERDICT: the speckles ARE hot pixels -- the null found nothing at all.")
    elif rate > 0.5:
        print("VERDICT: strong colocation but the null is also high -- the hot map is")
        print("         too dense for this test to discriminate. Tighten it.")
    else:
        print("VERDICT: NOT explained by the persistent-hot map. Look elsewhere")
        print("         (chroma noise, demosaic, or non-persistent hot sites).")

    out = pathlib.Path(args.tif).with_suffix(".speckle.json")
    out.write_text(json.dumps({
        "tif": args.tif,
        "excess_dn": args.excess,
        "speckles": total,
        "ppm": ppm,
        "per_channel": per_channel,
        "tested": len(sy),
        "hot_hits": n,
        "hot_rate": rate,
        "null_hits": nn,
        "null_rate": nrate,
        "enrichment": (rate / nrate) if nrate > 0 else None,
    }, indent=2))
    print(f"wrote      : {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
