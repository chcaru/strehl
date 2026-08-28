"""Locate and characterise the magenta blocks at an ink/white boundary.

Answers four questions about a rect of a delivered master, in one pass:

  1. WHERE are the magenta pixels -- defined as R and B BOTH above G, since that
     is what "magenta" means and a single-channel excess is a different defect.
  2. HOW BIG are the blocks, in native pixels, as a modal run length with its
     distribution -- ORCH's most diagnostic number. Reported for horizontal and
     vertical runs separately, because an anisotropic block implicates a
     different stage than a square one.
  3. Do the blocks COINCIDE WITH CLIPPING? The ground here is blown white. If a
     channel saturates while another does not, the ratio R/G explodes at the
     clip threshold and does so with a hard edge -- which would manufacture
     exactly the blockiness that is being read as a merge defect.
  4. Are the block boundaries GRID-ALIGNED? Start coordinates are histogrammed
     modulo 2, 4, 8, 16 and 32. A 2x2 preference implicates the Bayer cell; a
     larger power of two implicates a pyramid level or a tile.

Usage:
    python chromablock.py <master.tiff> <y> <x> <size> [--thresh 0.25]
"""

import argparse

import numpy as np
import tifffile


def runs(mask_row):
    """Lengths of consecutive True runs, with their start indices."""
    out = []
    n = len(mask_row)
    i = 0
    while i < n:
        if mask_row[i]:
            j = i
            while j < n and mask_row[j]:
                j += 1
            out.append((i, j - i))
            i = j
        else:
            i += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("y", type=int)
    ap.add_argument("x", type=int)
    ap.add_argument("size", type=int)
    ap.add_argument("--thresh", type=float, default=0.25,
                    help="log2 excess of BOTH R and B over G to call magenta")
    args = ap.parse_args()

    a = tifffile.imread(args.master)
    full_max = [float(a[:, :, c].max()) for c in range(3)]
    crop = a[args.y:args.y + args.size, args.x:args.x + args.size].astype(np.float64)
    eps = 1.0
    g = crop[:, :, 1] + eps
    rg = np.log2((crop[:, :, 0] + eps) / g)
    bg = np.log2((crop[:, :, 2] + eps) / g)

    mag = (rg > args.thresh) & (bg > args.thresh)
    cyan = (rg < -args.thresh) & (bg < -args.thresh)
    print(f"rect      : y={args.y} x={args.x} size={args.size}")
    print(f"magenta   : {100.0 * mag.mean():.3f}%  ({int(mag.sum())} px)")
    print(f"cyan      : {100.0 * cyan.mean():.3f}%  ({int(cyan.sum())} px)")
    if mag.sum() == 0:
        print("no magenta pixels at this threshold")
        return 0

    # --- 2. block size -------------------------------------------------------
    hruns = [ln for r in range(args.size) for _, ln in runs(mag[r, :])]
    vruns = [ln for c in range(args.size) for _, ln in runs(mag[:, c])]
    for name, rr in (("horizontal", hruns), ("vertical", vruns)):
        rr = np.array(rr)
        vals, cnts = np.unique(rr, return_counts=True)
        modal = int(vals[np.argmax(cnts)])
        top = ", ".join(f"{int(v)}px x{int(c)}" for v, c in
                        sorted(zip(vals, cnts), key=lambda t: -t[1])[:6])
        print(f"{name:10}: n={len(rr)} modal={modal} mean={rr.mean():.2f} "
              f"max={int(rr.max())}  top: {top}")

    # --- 3. clipping coincidence --------------------------------------------
    # A pixel is "near clip" if any channel is within 1% of that channel's
    # global maximum in the whole master.
    near = np.zeros(mag.shape, bool)
    for c in range(3):
        near |= crop[:, :, c] >= 0.99 * full_max[c]
    print(f"global max per ch : {[int(v) for v in full_max]}")
    print(f"near-clip in rect : {100.0 * near.mean():.3f}%")
    print(f"  of MAGENTA px, near-clip : {100.0 * near[mag].mean():.2f}%")
    if cyan.sum():
        print(f"  of CYAN    px, near-clip : {100.0 * near[cyan].mean():.2f}%")
    print(f"  of ALL     px, near-clip : {100.0 * near.mean():.2f}%")
    # And the converse: how bright are the magenta pixels relative to the rect?
    lum = crop.mean(axis=2)
    print(f"  mean luma  all={lum.mean():9.1f}  magenta={lum[mag].mean():9.1f}"
          f"  cyan={lum[cyan].mean() if cyan.sum() else float('nan'):9.1f}")

    # --- 4. grid alignment ---------------------------------------------------
    starts = np.array([s for r in range(args.size) for s, _ in runs(mag[r, :])])
    print("h-run start phase:")
    for m in (2, 4, 8, 16, 32):
        h = np.bincount(( (starts + args.x) % m), minlength=m)
        frac = h / max(h.sum(), 1)
        print(f"  mod {m:2d}: " + " ".join(f"{f:.3f}" for f in frac) +
              f"   (uniform={1.0 / m:.3f}, peak={frac.max():.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
