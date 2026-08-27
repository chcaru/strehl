"""Where in the band does A's excursion sit, and what is A's matched-site resolution?

orch_halo's BAND is (8,90) at DS=2, i.e. 16..180 FULL-RES px from the edge centre.
A Catmull-Rom or Malvar negative lobe lands at 1-4 px. If the excursion peaks far
out, A is reading the wide composite halo, not the gather.
"""
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
    ysx = np.nonzero((mag >= thr) & m)
    rng = np.random.default_rng(seed)
    ys, xs = ysx
    if ys.size > maxp:
        k = rng.choice(ys.size, maxp, replace=False); ys, xs = ys[k], xs[k]
    return ys, xs

y = {}
for lab, f in (("g0", "wt1-srgb-auto-g0.tiff"), ("g1", "wt1-srgb-auto-g1.tiff")):
    a = tifffile.imread(os.path.join(OUT, f))[:, :, :3].astype(np.float64)
    y[lab] = luma(a); del a
mean = 0.5 * (y["g0"] + y["g1"])

print("MATCHED-SITE RESOLUTION: 6 independent 4000-point subsamples of the SAME")
print("edge set, chosen on the mean image. Both arms read at each.")
print(f"{'seed':>5s} {'A g0':>9s} {'A g1':>9s} {'delta':>9s}")
d = []
for s in range(6):
    pts = epts(mean, 100, 9, 99.5, 4000, s, 2)
    a0 = step_overshoot(y["g0"], half=100, band=(8, 90), ds=2, pts_override=pts)
    a1 = step_overshoot(y["g1"], half=100, band=(8, 90), ds=2, pts_override=pts)
    d.append(a1["over"] - a0["over"])
    print(f"{s:5d} {a0['over']:9.4f} {a1['over']:9.4f} {a1['over']-a0['over']:+9.4f}")
print(f"delta: mean {np.mean(d):+.4f}  sd {np.std(d, ddof=1):.4f}  range {max(d)-min(d):.4f}")

pts = epts(mean, 100, 9, 99.5, 4000, 0, 2)
p0 = step_overshoot(y["g0"], half=100, band=(8, 90), ds=2, pts_override=pts)["prof"]
p1 = step_overshoot(y["g1"], half=100, band=(8, 90), ds=2, pts_override=pts)["prof"]
print()
print("MEDIAN STEP PROFILE, bright side. offset in DS=2 px (x2 for full-res px).")
print(f"{'off(DS)':>8s} {'full-res':>9s} {'g0':>9s} {'g1':>9s} {'g1-g0':>9s}")
for off in [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 80, 90, 100]:
    print(f"{off:8d} {2*off:9d} {p0[100+off]:9.4f} {p1[100+off]:9.4f} {p1[100+off]-p0[100+off]:+9.4f}")
print()
b = slice(108, 191)
print(f"peak of g0 in BAND at offset {int(np.argmax(p0[b]))+8} DS px ({2*(int(np.argmax(p0[b]))+8)} full-res px), value {p0[b].max():.4f}")
print(f"peak of g1 in BAND at offset {int(np.argmax(p1[b]))+8} DS px ({2*(int(np.argmax(p1[b]))+8)} full-res px), value {p1[b].max():.4f}")
print(f"peak of g0 INSIDE 1..4 DS px: {p0[101:105].max():.4f}   g1: {p1[101:105].max():.4f}")
