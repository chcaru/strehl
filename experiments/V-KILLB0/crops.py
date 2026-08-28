"""Matched 1:1 A/B crops with a SHARED stretch, plus the numbers for the same
crop.  Discipline 1825: a crop is illustration, never evidence, and the
orchestrator has already read one backwards in both level and contrast.  So
this always prints median / clip% / black% / fine-band RMS for the identical
pixels it draws, and both panels ALWAYS share one stretch derived from arm A
only, so a level change shows as a level change instead of being normalised
away.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter

import bandprobe as bp

S = 384


def crop_pair(A, B, y, x, out, tag):
    a = bp.load(A)[y:y + S, x:x + S]
    b = bp.load(B)[y:y + S, x:x + S]
    la = a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    lb = b.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    lo = np.percentile(la, 0.5)
    hi = np.percentile(la, 99.5)
    if hi - lo < 1:
        hi = lo + 1
    fa = la - gaussian_filter(la, 0.6366)
    fb = lb - gaussian_filter(lb, 0.6366)
    print(f"  {tag} @y={y} x={x} {S}x{S}")
    for nm, im, l, f in (("default", a, la, fa), ("arm", b, lb, fb)):
        print(f"     {nm:>8s}  median {np.median(l):8.0f}  mean {l.mean():8.0f}  "
              f"clip% {100*(im.max(axis=2)>=65535).mean():6.3f}  "
              f"black% {100*(im.min(axis=2)<=0).mean():6.3f}  "
              f"fine RMS {np.sqrt((f**2).mean()):8.1f}")
    panels = []
    for im in (a, b):
        v = (im.astype(np.float64) - lo) / (hi - lo)
        panels.append((np.clip(v, 0, 1) * 255).astype(np.uint8))
    gap = np.full((S, 8, 3), 255, np.uint8)
    Image.fromarray(np.hstack([panels[0], gap, panels[1]])).save(out)
    print(f"     -> {out}  (LEFT default, RIGHT arm, shared stretch "
          f"[{lo:.0f},{hi:.0f}] from the default arm)")


def main():
    A, B, outdir, tag = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    os.makedirs(outdir, exist_ok=True)
    la = bp.channels(bp.load(A))["L"]
    h, w = la.shape
    if len(sys.argv) > 5:
        pts = [tuple(int(v) for v in p.split(",")) for p in sys.argv[5:]]
    else:
        # pick automatically: the most structured, and the least structured
        sel = gaussian_filter(np.abs(gaussian_filter(la, 1.5) - gaussian_filter(la, 4.0)), 8.0)
        ny, nx = h // S, w // S
        t = sel[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
        o = np.argsort(t.ravel())
        pts = []
        for f in (o[-1], o[-2], o[0], o[len(o) // 2]):
            ty, tx = divmod(int(f), nx)
            pts.append((ty * S, tx * S))
    for i, (y, x) in enumerate(pts):
        crop_pair(A, B, y, x, os.path.join(outdir, f"{tag}-{i}-y{y}-x{x}.png"),
                  f"{tag}[{i}]")


if __name__ == "__main__":
    main()
