"""foam: are the coloured highlight rims lateral CA, or thin-film iridescence?

THE QUESTION
------------
`foam` is dark cellular plastic with blown specular highlights -- maximum
contrast at a hard edge, which is the worst case for lateral chromatic
aberration. Its highlight rims carry visible orange, cyan and magenta. Foam
has thin films and thin-film iridescence is a real optical effect, so the
colour alone proves nothing.

THE DISCRIMINATOR
-----------------
Lateral CA is a RADIAL magnification difference between channels: zero on axis
by construction, growing with distance from the centre. Iridescence has no such
geometry -- it sits wherever the film is, centre included. So:

  * whatever the CA correction REMOVES was aberration;
  * whatever SURVIVES it is something else, and iridescence is the candidate;
  * and the centre is the built-in null -- a correction that moved the centre
    would be doing something other than what it claims.

Both arms come from ONE binary on ONE subject with one flag changed, so the
comparison is not across builds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

D = Path(r"C:\dev\strehl-out\ORCH-CADEF")
ON = D / "foam-caon.tif"
OFF = D / "foam-caoff.tif"


def edge_colour_by_radius(img: np.ndarray, nbands: int = 6):
    """Mean |R-G| and |B-G| at strong edges, normalised by local green,
    in `nbands` radial bands from centre to corner."""
    f = img.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]

    # Strong edges, found on GREEN so the mask cannot be created by the very
    # colour difference being measured.
    gy, gx = np.gradient(g)
    grad = np.hypot(gx, gy)
    thr = np.percentile(grad, 99.0)
    strong = grad >= thr

    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rad = np.hypot(yy - cy, xx - cx)
    rmax = rad.max()

    denom = np.maximum(g, 1.0)
    rg = np.abs(r - g) / denom
    bg = np.abs(b - g) / denom

    out = []
    for i in range(nbands):
        lo, hi = i / nbands * rmax, (i + 1) / nbands * rmax
        m = strong & (rad >= lo) & (rad < hi)
        n = int(m.sum())
        out.append((i, n, float(rg[m].mean()) if n else float("nan"),
                    float(bg[m].mean()) if n else float("nan")))
    return out


def main() -> int:
    for p in (ON, OFF):
        if not p.exists():
            print(f"MISSING {p}")
            return 2

    a = tifffile.imread(ON)
    b = tifffile.imread(OFF)
    print(f"on  {a.shape} {a.dtype}")
    print(f"off {b.shape} {b.dtype}")
    if a.shape != b.shape:
        print("SHAPE MISMATCH -- not comparable")
        return 2

    same = np.array_equal(a, b)
    print(f"\narms byte-identical: {same}")
    if same:
        print("  THE ARMS DID NOT DIFFER. The flag did nothing; every number")
        print("  below would be a comparison of a file with itself.")
        return 2
    d = np.abs(a.astype(np.int32) - b.astype(np.int32))
    print(f"  max|delta| {d.max()}   changed pixels {int((d.max(axis=2) > 0).sum()):,}"
          f" / {a.shape[0] * a.shape[1]:,}")

    print("\n            band 0 = CENTRE (the null)  ->  band 5 = CORNER")
    print(f"  {'band':>4} {'edges':>9} {'|R-G|/G on':>11} {'off':>9} {'change':>8}"
          f" {'|B-G|/G on':>11} {'off':>9} {'change':>8}")
    ra, rb = edge_colour_by_radius(a), edge_colour_by_radius(b)
    for (i, na, rga, bga), (_, nb, rgb_, bgb) in zip(ra, rb):
        cr = rga / rgb_ if rgb_ else float("nan")
        cb = bga / bgb if bgb else float("nan")
        print(f"  {i:>4} {na:>9,} {rga:>11.4f} {rgb_:>9.4f} {cr:>7.3f}x"
              f" {bga:>11.4f} {bgb:>9.4f} {cb:>7.3f}x")

    print("\n  READ IT AS GEOMETRY, NOT AS A LEVEL: the claim is not that the")
    print("  numbers fall. It is that the RADIAL GROWTH flattens and the centre")
    print("  is left alone. A ratio near 1.000 in band 0 with ratios well below")
    print("  1 at band 5 is the signature of a real lateral-CA correction.")
    print("  Whatever colour SURVIVES at the corner is not lateral CA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
