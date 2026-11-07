"""Known-answer check with real texture and real breathing geometry.

The scene is a region of a Strehl linear master (real beetle texture, its own
band limit), continuous via Catmull-Rom. Synthetic CFA frames sample it at the
actual warp-map placements of a real focus window (so the sub-pixel phase
diversity is the measured one), with calibrated shot/read noise, Gaussian
defocus growing with distance from the window's peak frame, and registration
error. Arms are scored against the scene itself on every grid pixel and channel,
so errors in directions without phase diversity count.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).parent))
from common import BLACK, GAIN_DN_PER_E, READ_E, cfa_channel, cr_sample, frame_to_ref, load_alignment
import holdout as H

ap = argparse.ArgumentParser()
ap.add_argument("--master", required=True)
ap.add_argument("--alignment", required=True)
ap.add_argument("--window", required=True, help="first,last global frame of a real focus window")
ap.add_argument("--roi", required=True, help="x0,y0,size reference sensor px (geometry)")
ap.add_argument("--texture", required=True, help="tx,ty: master pixel that maps to the roi origin")
ap.add_argument("--defocus-step", type=float, default=0.25, help="blur sigma per frame from the peak, px")
ap.add_argument("--reg-noise", type=float, default=0.1)
ap.add_argument("--peak-dn", type=float, default=4000)
ap.add_argument("--c", action="append", default=["0.02,0.5,0.001"])
ap.add_argument("--save")
args = ap.parse_args()
rng = np.random.default_rng(3)
place, _, (gw, gh) = load_alignment(args.alignment)
centre = complex(gw / 2, gh / 2)
w0, w1 = map(int, args.window.split(","))
x0, y0, s = map(int, args.roi.split(","))
tx, ty = map(int, args.texture.split(","))
pad = 64
m = tifffile.imread(args.master)[ty - pad:ty + s + pad, tx - pad:tx + s + pad].astype(np.float64)
m = np.maximum(m, 0)
m *= args.peak_dn / np.percentile(m, 99.5)
peak = (w0 + w1) // 2
frames = []
blurred = {}
for i in range(w0, w1 + 1):
    sig = args.defocus_step * abs(i - peak)
    if sig not in blurred:
        blurred[sig] = [gaussian_filter(m[..., c], sig) if sig > 0 else m[..., c] for c in range(3)]
    t = place[i]
    true_t = (t[0], t[1] + complex(*rng.normal(0, args.reg_noise / 2, 2)))
    box = H.frame_box(t, (x0, y0, s), centre, 24)
    bx0, by0, bx1, by1 = box
    yy, xx = np.mgrid[by0:by1, bx0:bx1]
    rx, ry = frame_to_ref(true_t, xx.ravel().astype(float), yy.ravel().astype(float), centre)
    c = cfa_channel(xx.ravel(), yy.ravel())
    v = np.zeros(len(c))
    for ch in range(3):
        k = c == ch
        v[k] = cr_sample(blurred[sig][ch], rx[k] - x0 + pad, ry[k] - y0 + pad)
    v = np.nan_to_num(v)
    noise = rng.normal(0, np.sqrt(GAIN_DN_PER_E * np.maximum(v, 0) + (GAIN_DN_PER_E * READ_E) ** 2))
    patch = np.clip(np.round(v + noise + BLACK), 0, 65535).astype(np.uint16).reshape(yy.shape)
    frames.append((patch, (bx0, by0), t, np.ones(3), 1.0))
grid = (x0 - 6, y0 - 6, s + 12, s + 12)
yy, xx = np.mgrid[grid[1]:grid[1] + grid[3], grid[0]:grid[0] + grid[2]].astype(float)
truth = np.stack([cr_sample(m[..., c], xx - x0 + pad, yy - y0 + pad) for c in range(3)])
imgs = {"A": H.arm_a(frames, grid, False, centre), "B": H.arm_b(frames, grid, False, centre, 0.02)}
for spec in args.c:
    ll, lc, ls = map(float, spec.split(","))
    imgs[f"C{spec}"] = H.arm_c(frames, grid, False, centre, imgs["A"], ll, lc, ls)
sl = (slice(None), slice(14, -14), slice(14, -14))
fx = [frame_to_ref(place[i], np.array([x0 + s / 2.0]), np.array([y0 + s / 2.0]), centre) for i in range(w0, w1 + 1)]
print(f"window {w0}..{w1}, phase spread x {np.ptp([f[0][0] for f in fx]):.2f} y {np.ptp([f[1][0] for f in fx]):.2f}")
for n, img in imgs.items():
    e = img[sl] - truth[sl]
    per = [float(np.mean(e[c] ** 2)) for c in range(3)]
    # error split by band: low-pass (sigma 2) vs residual high band
    lo = np.stack([gaussian_filter(e[c], 2) for c in range(3)])
    print(f"{n:>16}: truth mse r/g/b {per[0]:8.1f} {per[1]:8.1f} {per[2]:8.1f}   high-band mse {np.mean((e - lo) ** 2):8.1f}")
if args.save:
    np.save(args.save, np.stack([truth] + list(imgs.values())))
