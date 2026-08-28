"""Experiment B2 -- does B's claimed effect clear the noise floor of its own design?

B contrasts step-x2/full-range vs step-x1/half-range at equal N and (in its
repaired ROI form) reported 1.125x. That number is only meaningful against a
floor: how far apart do two arms land when they differ in NOTHING that the
hypothesis cares about?

The replicate pair is even-phase (DSC00001,3,..,299; N=150) vs odd-phase
(DSC00002,4,..,298; N=149). Same subject, same focus range, same focus step, so
the same number of frames sit near focus at every pixel -- the quantity the model
actually names. It shares every nuisance of the contrast (independent alignment
solve, its own FOV shrink, its own resample blur) and none of its signal.

Both contrasts run through the same tiles, bands, magnification correction and
bootstrap, so the floor is directly comparable to the claim.
"""
import sys
import numpy as np
import tifffile

HERE = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE"
sys.path.insert(0, HERE)
import vd_metrics as vd

R = r"D:\strehl-out\V-DILUTE\runs"
TILE = vd.TILE
half = TILE // 2

ARMS = {
    "x2":   "B_step2_n150",     # step x2, FULL range,  N=150
    "x1":   "B_first150_n150",  # step x1, HALF range,  N=150
    "odd":  "B_odd149_n149",    # step x2, FULL range,  N=149  <- replicate of x2
}
imgs = {k: vd.green(rf"{R}\{v}.tif") for k, v in ARMS.items()}
scal = {k: vd.fov_scale(rf"{R}\{v}.log") for k, v in ARMS.items()}
print("FOV scales: " + "  ".join(f"{k}={scal[k]:.4f}" for k in ARMS))
print(f"  replicate differential magnification: {scal['x2']/scal['odd']:.4f} "
      f"(two arms differing ONLY in which alternate frame they took)")

idx = tifffile.imread(rf"{R}\ROI_index_n63.tif")
s_i = vd.fov_scale(rf"{R}\ROI_index_n63.log")
near_i = (idx.astype(np.float64) * (298.0 / 62)) < 150.0
H, W = idx.shape
cy, cx = H / 2.0, W / 2.0

smin = min(scal.values())
cands = []
lim_y = (H / 2.0 - half - 2) * smin
lim_x = (W / 2.0 - half - 2) * smin
for u in np.arange(-lim_y, lim_y, TILE):
    for v in np.arange(-lim_x, lim_x, TILE):
        iy, ix = int(round(cy + u / s_i)), int(round(cx + v / s_i))
        if not (half <= iy < H - half and half <= ix < W - half):
            continue
        if near_i[iy - half:iy + half, ix - half:ix + half].mean() < 0.90:
            continue
        cands.append((u, v))

en = np.zeros(len(cands))
for k in ARMS:
    gy, gx = np.gradient(imgs[k])
    e = gy * gy + gx * gx
    for j, (u, v) in enumerate(cands):
        y = int(round(cy + u / scal[k])) - half
        x = int(round(cx + v / scal[k])) - half
        en[j] += e[y:y + TILE, x:x + TILE].mean() / len(ARMS)
order = np.argsort(en)
tex = [cands[i] for i in order[-max(10, len(cands) // 4):]]
print(f"candidates {len(cands)}, textured tiles {len(tex)} (symmetric ranking over all three arms)\n")


def tile_band(arm, band, corrected=True):
    s = scal[arm]
    f1, f2 = (band[0] * s, band[1] * s) if corrected else band
    msk = (vd._R >= f1) & (vd._R < f2)
    vals = []
    for (u, v) in tex:
        y = int(round(cy + u / s)) - half
        x = int(round(cx + v / s)) - half
        P = vd.tile_spectrum(imgs[arm][y:y + TILE, x:x + TILE])
        vals.append(P[msk].mean())
    return np.array(vals)


def pair(a, b, band, label, corrected=True):
    ma, mb = tile_band(a, band, corrected), tile_band(b, band, corrected)
    lr = np.log(ma / mb)
    n = len(lr)
    rng = np.random.default_rng(0)
    boot = np.array([rng.choice(lr, n, replace=True).mean() for _ in range(4000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    sig = "" if (lo < 0 < hi) else "   *** excludes 1.0 ***"
    tag = "" if corrected else " [magnif. corr. OFF]"
    print(f"  {label:<44s}{tag}")
    print(f"    ratio mean {np.exp(lr.mean()):.4f}  median {np.exp(np.median(lr)):.4f}  "
          f"95% CI [{np.exp(lo):.4f}, {np.exp(hi):.4f}]  wins {int((lr>0).sum())}/{n}{sig}")
    return np.exp(lr.mean()), np.exp(lo), np.exp(hi)


for band, bl in (((0.30, 0.35), "DETAIL 0.30-0.35"), ((0.20, 0.25), "DETAIL 0.20-0.25"),
                 ((0.40, 0.50), "NOISE  0.40-0.50")):
    print(f"=== {bl} cyc/px, bee-3-cpl, common-focus ROI, same tiles ===")
    c = pair("x2", "x1", band, "CONTRAST  x2/full-range vs x1/half-range")
    r = pair("x2", "odd", band, "REPLICATE x2-even vs x2-odd (NULL)")
    print(f"    -> claimed effect {c[0]:.4f} vs replicate floor {r[0]:.4f}\n")

print("=== sensitivity: magnification correction OFF ===")
pair("x2", "x1", (0.30, 0.35), "CONTRAST  x2 vs x1", corrected=False)
pair("x2", "odd", (0.30, 0.35), "REPLICATE x2 vs odd", corrected=False)

print("\n=== whole-frame confidence (mean over reached pixels) ===")
for k, v in ARMS.items():
    c = vd.conf_stats(rf"{R}\{v}_conf.tif")
    print(f"  {k:<5s} {v:<20s} mean {c['mean']:8.1f}  p50 {c['p50']:6.0f}  >=900 {c['f900']*100:5.1f}%")
