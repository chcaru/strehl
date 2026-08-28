"""V-KILLB0 crop at explicit coordinates (from worst.py), shared stretch from A."""
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import bandprobe as bp

OUT = r"C:\dev\strehl-out\V-KILLB0\crops"


def main():
    A, B, label, y, x = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
    box = int(sys.argv[6]) if len(sys.argv) > 6 else 512
    zoom = int(sys.argv[7]) if len(sys.argv) > 7 else 2
    ia, ib = bp.load(A), bp.load(B)
    ca, cb = ia[y:y+box, x:x+box], ib[y:y+box, x:x+box]
    ga = bp.channels(ia)["L"][y:y+box, x:x+box]
    gb = bp.channels(ib)["L"][y:y+box, x:x+box]
    lo, hi = np.percentile(ca, 0.5), np.percentile(ca, 99.5)
    if hi <= lo:
        hi = lo + 1
    f = lambda c: np.clip((c.astype(np.float64) - lo) / (hi - lo), 0, 1) * 255
    pa, pb = f(ca).astype(np.uint8), f(cb).astype(np.uint8)
    gap = np.full((box, 8, 3), 255, np.uint8)
    im = Image.fromarray(np.concatenate([pa, gap, pb], axis=1))
    im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"{label}-worst.png")
    im.save(p)
    fa = ga - gaussian_filter(ga, 0.6366)
    fb = gb - gaussian_filter(gb, 0.6366)
    print(f"== WORST-TILE CROP {label} y={y} x={x} -> {p}")
    print(f"   A median={np.median(ga):7.0f} clip%={100*(ga>=65000).mean():5.2f} "
          f"black%={100*(ga<=200).mean():5.2f}  p1={np.percentile(ga,1):.0f} p99={np.percentile(ga,99):.0f}")
    print(f"   B median={np.median(gb):7.0f} clip%={100*(gb>=65000).mean():5.2f} "
          f"black%={100*(gb<=200).mean():5.2f}")
    print(f"   fine rms A={np.sqrt((fa**2).mean()):.1f} B={np.sqrt((fb**2).mean()):.1f} "
          f"ratio={np.sqrt((fb**2).mean())/np.sqrt((fa**2).mean()):.4f}")


if __name__ == "__main__":
    main()
