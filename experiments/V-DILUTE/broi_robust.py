"""Robustness of the Experiment B ROI result.

A single ratio of pooled means can move for one uninteresting reason. This pairs
the two arms TILE BY TILE at matched sensor locations and reports the
distribution of the per-tile log ratio, a sign test, and a bootstrap interval --
plus a sensitivity arm with the magnification correction switched off, so the
correction cannot be quietly carrying the result.
"""
import os
import sys
import numpy as np
import tifffile

HERE = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE"
sys.path.insert(0, HERE)
import vd_metrics as vd

R = r"C:\dev\strehl-out\V-DILUTE\runs"
TILE = vd.TILE
half = TILE // 2

idx = tifffile.imread(rf"{R}\ROI_index_n63.tif")
s_i = vd.fov_scale(rf"{R}\ROI_index_n63.log")
near_i = (idx.astype(np.float64) * (298.0 / 62)) < 150.0
H, W = idx.shape
cy, cx = H / 2.0, W / 2.0

arms = {"x2": "B_step2_n150", "x1": "B_first150_n150"}
imgs = {k: vd.green(rf"{R}\{v}.tif") for k, v in arms.items()}
scal = {k: vd.fov_scale(rf"{R}\{v}.log") for k, v in arms.items()}
print(f"scales: x2={scal['x2']:.4f}  x1={scal['x1']:.4f}  index={s_i:.4f}")

cands = []
lim = (min(H, W) / 2.0 - half - 2) * min(scal.values())
for u in np.arange(-lim, lim, TILE):
    for v in np.arange(-(W / 2.0 - half - 2) * min(scal.values()),
                       (W / 2.0 - half - 2) * min(scal.values()), TILE):
        iy, ix = int(round(cy + u / s_i)), int(round(cx + v / s_i))
        if not (half <= iy < H - half and half <= ix < W - half):
            continue
        if near_i[iy - half:iy + half, ix - half:ix + half].mean() < 0.90:
            continue
        cands.append((u, v))

# symmetric texture ranking
en = np.zeros(len(cands))
for k in arms:
    gy, gx = np.gradient(imgs[k])
    e = gy * gy + gx * gx
    s = scal[k]
    for j, (u, v) in enumerate(cands):
        y, x = int(round(cy + u / s)) - half, int(round(cx + v / s)) - half
        en[j] += e[y:y + TILE, x:x + TILE].mean() / 2.0
order = np.argsort(en)
tex = [cands[i] for i in order[-max(10, len(cands) // 4):]]
print(f"candidates {len(cands)}, textured tiles {len(tex)}")


def per_tile(band, corrected=True):
    out = {}
    m = {}
    for k in arms:
        s = scal[k] if corrected else 1.0
        f1, f2 = band[0] * s, band[1] * s
        msk = (vd._R >= f1) & (vd._R < f2)
        vals = []
        for (u, v) in tex:
            sc = scal[k]
            y, x = int(round(cy + u / sc)) - half, int(round(cx + v / sc)) - half
            P = vd.tile_spectrum(imgs[k][y:y + TILE, x:x + TILE])
            vals.append(P[msk].mean())
        m[k] = np.array(vals)
    return m


def report(band, label, corrected=True):
    m = per_tile(band, corrected)
    lr = np.log(m["x2"] / m["x1"])
    n = len(lr)
    rng = np.random.default_rng(0)
    boot = np.array([np.mean(rng.choice(lr, n, replace=True)) for _ in range(4000)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    wins = int((lr > 0).sum())
    tag = "" if corrected else "  [magnification correction OFF]"
    print(f"\n{label}{tag}")
    print(f"  per-tile x2/x1 ratio: median {np.exp(np.median(lr)):.4f}  "
          f"mean {np.exp(lr.mean()):.4f}  95% CI [{np.exp(lo):.4f}, {np.exp(hi):.4f}]")
    print(f"  tiles where x2 > x1 : {wins} of {n}")
    return np.exp(lr.mean())


report((0.30, 0.35), "DETAIL 0.30-0.35 cyc/px, bee-3-cpl, N=150 both arms, common-focus ROI")
report((0.20, 0.25), "DETAIL 0.20-0.25 cyc/px, bee-3-cpl, N=150 both arms, common-focus ROI")
report((0.40, 0.50), "NOISE  0.40-0.50 cyc/px, SAME TILES (rule 3)")
report((0.30, 0.35), "DETAIL 0.30-0.35 cyc/px", corrected=False)
