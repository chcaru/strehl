import sys, os
import numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import step_overshoot, luma, boxblur, downsample
OUT = r"C:\dev\strehl-out\V-GATHER"
def epts(img, half, blur, pct, maxp, seed, ds):
    im = downsample(np.asarray(img, np.float64), ds)
    b = boxblur(im, blur)
    gy = np.zeros_like(b); gx = np.zeros_like(b)
    gy[1:-1, :] = (b[2:, :] - b[:-2, :]) * 0.5
    gx[:, 1:-1] = (b[:, 2:] - b[:, :-2]) * 0.5
    mag = np.hypot(gy, gx)
    m = np.zeros(mag.shape, bool); m[half+2:-half-2, half+2:-half-2] = True
    thr = float(np.percentile(mag[m], pct))
    ys, xs = np.nonzero((mag >= thr) & m)
    rng = np.random.default_rng(seed)
    if ys.size > maxp:
        k = rng.choice(ys.size, maxp, replace=False); ys, xs = ys[k], xs[k]
    return ys, xs
y = {}
for lab, f in (("g0", "wt1-srgb-auto-g0.tiff"), ("g1", "wt1-srgb-auto-g1.tiff")):
    a = tifffile.imread(os.path.join(OUT, f))[:, :, :3].astype(np.float64)
    y[lab] = luma(a); del a
pts = epts(0.5*(y["g0"]+y["g1"]), 100, 9, 99.5, 4000, 0, 2)
print("WHICH SIDE is A reading?  over = max(over_hi, over_lo)")
print(f"{'arm':5s} {'over':>9s} {'over_hi':>9s} {'over_lo':>9s}  (hi = BRIGHT side above the bright plateau,")
print(f"{'':5s} {'':>9s} {'':>9s} {'':>9s}   lo = DARK side below the dark plateau)")
for a in ("g0", "g1"):
    r = step_overshoot(y[a], half=100, band=(8, 90), ds=2, pts_override=pts)
    print(f"{a:5s} {r['over']:9.4f} {r['over_hi']:+9.4f} {r['over_lo']:+9.4f}")
