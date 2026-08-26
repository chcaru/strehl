"""Gamut-ceiling probe on shipped print masters.

A colour outside the sRGB triangle maps to a NEGATIVE component under the
camera matrix; the writer clamps it to 0. So the signature of a clipped
out-of-gamut pixel is one channel pinned at 0 (or 65535) while the others
sit well away from the same rail. A true black has all three at the rail.

COMMISSIONED: a synthetic in-gamut ramp must read ~0, and a synthetic
out-of-gamut image must read high. An uncommissioned counter of zeros is
just a counter of dark pixels.
"""
import sys, os, glob
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

LO, HI = 0, 65535
AWAY = 6553  # 10% of full scale: "well away from the rail"

def probe(a):
    r, g, b = a[..., 0].astype(np.int32), a[..., 1].astype(np.int32), a[..., 2].astype(np.int32)
    n = a.shape[0] * a.shape[1]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    # low-rail clip: some channel at 0 while the brightest channel is well up
    lo_clip = ((mn <= LO) & (mx >= AWAY)).sum()
    # high-rail clip: some channel at max while the darkest is well below
    hi_clip = ((mx >= HI) & (mn <= HI - AWAY)).sum()
    # true black / true white, for contrast
    true_black = (mx <= LO).sum()
    true_white = (mn >= HI).sum()
    return dict(n=n, lo=lo_clip, hi=hi_clip, tb=true_black, tw=true_white,
                lo_pct=100.0*lo_clip/n, hi_pct=100.0*hi_clip/n)

def commission():
    ok = True
    # in-gamut: a neutral + pastel ramp, nothing near a rail asymmetrically
    h = w = 256
    x = np.linspace(0.15, 0.85, w, dtype=np.float64)
    ing = np.zeros((h, w, 3))
    ing[..., 0] = x; ing[..., 1] = x * 0.9 + 0.05; ing[..., 2] = x * 0.8 + 0.1
    ing = (ing * 65535).astype(np.uint16)
    a = probe(ing)
    print(f"  commission in-gamut     : lo={a['lo_pct']:.4f}%  hi={a['hi_pct']:.4f}%")
    if a['lo_pct'] > 0.01 or a['hi_pct'] > 0.01:
        print("  FAIL: in-gamut control tripped the detector"); ok = False
    # out-of-gamut: saturated primaries with a clamped channel
    oog = np.zeros((h, w, 3))
    oog[..., 0] = x; oog[..., 1] = 0.0; oog[..., 2] = x * 0.5
    oog = (oog * 65535).astype(np.uint16)
    b = probe(oog)
    print(f"  commission out-of-gamut : lo={b['lo_pct']:.4f}%  hi={b['hi_pct']:.4f}%")
    if b['lo_pct'] < 50.0:
        print("  FAIL: planted out-of-gamut not detected"); ok = False
    if not ok:
        print("COMMISSIONING FAILED - refusing to report"); sys.exit(2)
    print("  commissioning OK\n")

print("== gamut-ceiling probe ==")
commission()
files = sorted(glob.glob(sys.argv[1]))
rows = []
for f in files:
    im = Image.open(f)
    a = np.asarray(im)
    r = probe(a)
    rows.append((os.path.basename(f).split("--")[0], r))
    print(f"{rows[-1][0]:<28} lo-rail {r['lo_pct']:7.3f}%   hi-rail {r['hi_pct']:7.3f}%   "
          f"true-black {100.0*r['tb']/r['n']:6.3f}%  true-white {100.0*r['tw']/r['n']:6.3f}%")
print()
tot_lo = sum(r['lo'] for _, r in rows); tot_n = sum(r['n'] for _, r in rows)
tot_hi = sum(r['hi'] for _, r in rows)
print(f"CORPUS  lo-rail {100.0*tot_lo/tot_n:.4f}%   hi-rail {100.0*tot_hi/tot_n:.4f}%   over {len(rows)} subjects")
worst = max(rows, key=lambda kv: kv[1]['lo_pct'])
print(f"worst lo-rail: {worst[0]} at {worst[1]['lo_pct']:.3f}%")
worst2 = max(rows, key=lambda kv: kv[1]['hi_pct'])
print(f"worst hi-rail: {worst2[0]} at {worst2[1]['hi_pct']:.3f}%")
