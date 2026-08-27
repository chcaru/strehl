"""Reproduction attempt: orch_halo's dissent, 0.1281/0.1403 -> 0.1793 on wrapped-text-1.

Same subject, same frame count (130), same render mode (--srgb, CA at default),
same instrument configuration (BT.709 luma, DS=2, HALF=100, BAND=(8,90)).
Three readings per file:
  own-sites   exactly as orch_halo does it: each arm picks its own edge points
  matched     both arms profiled at points chosen once on the MEAN of the arms
  seed spread 4 seeds, so the instrument's own resolution is stated
"""
import sys, os
import numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import step_overshoot, luma, boxblur, downsample, B_stat

OUT = r"C:\dev\strehl-out\V-GATHER"
FILES = [("g0 auto +2.28", "wt1-srgb-auto-g0.tiff"),
         ("g1 auto +2.27", "wt1-srgb-auto-g1.tiff"),
         ("g1 pinned +2.28", "wt1-srgb-pin-g1.tiff")]

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

ys = {}
for lab, f in FILES:
    a = tifffile.imread(os.path.join(OUT, f))[:, :, :3].astype(np.float64)
    ys[lab] = luma(a); del a

mean = 0.5 * (ys["g0 auto +2.28"] + ys["g1 auto +2.27"])
pts = epts(mean, 100, 9, 99.5, 4000, 0, 2)

print("orch_halo config: DS=2 HALF=100 BAND=(8,90) EDGE_PCT=99.5 MIN_STEP_FRAC=0.08 PLATEAU_FRAC=0.18")
print("target to reproduce: 0.1281 / 0.1403 (gather OFF) -> 0.1793 (gather ON)")
print()
print(f"{'file':18s} {'own-sites (4 seeds)':>34s} {'spread':>9s} {'matched':>10s} {'n':>7s} {'B ring%':>9s}")
for lab, f in FILES:
    y = ys[lab]
    v = [step_overshoot(y, half=100, band=(8, 90), ds=2, seed=s)["over"] for s in range(4)]
    m = step_overshoot(y, half=100, band=(8, 90), ds=2, pts_override=pts)
    print(f"{lab:18s} " + " ".join(f"{x:7.4f}" for x in v)
          + f" {max(v)-min(v):9.4f} {m['over']:10.4f} {m['n']:7d} {100*B_stat(y):8.3f}%")

print()
d = ys["g1 auto +2.27"] - ys["g1 pinned +2.28"]
print("exposure confound size: g1@2.27 vs g1@2.28, same pixels otherwise")
print(f"   mean |delta| = {np.abs(d).mean():.3f} DN of 65535, max = {np.abs(d).max():.1f} DN")
