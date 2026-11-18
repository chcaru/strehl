"""Score stack outputs against the synthetic pixel-shift truth (plan gate 3).

Usage: eval-synthetic.py TRUTH.npy ARM.tif [ARM.tif ...]

TRUTH.npy is the generator's all-in-focus scene over the active area (scene
index = truth index + 4, the generator's pad). The stack's cover fit scales
the field slightly about its centre, so a similarity (scale, shift) from
output pixels to truth positions is fitted on green for the FIRST arm and the
same transform is applied to every arm: arms rendered from the same frames
with the same warp map share it exactly, and none is favoured by its own fit.
Truth is sampled at those positions (cubic). Each arm is then mapped by a
per-channel least-squares affine fit over the interior (channel scale and
white-balance convention are not under test). Reported, in truth DN:
  rmse_<c>        interior RMSE per channel
  edge_hf_chroma  RMS of high-passed (R-G, B-G) on the neutral slanted edge,
                  where truth chroma is exactly zero (the rejected RGB-fusion
                  arm's statistic). Blur can lower it; read it beside
                  edge_rmse, which blur raises.
  edge_rmse       luma RMSE on the edge patch
  zone_rmse       RMSE over the colour zone plate (chroma at rising frequency)
"""
import json, sys
import numpy as np
import tifffile
from scipy import ndimage, optimize

truth_full = np.load(sys.argv[1]).astype(np.float32)
EDGE = (1980 + 60, 2580 - 60, 2968 + 60, 3568 - 60)  # truth-array coordinates
ZONE = (3480 + 30, 4080 - 30, 4968 + 30, 5568 - 30)
paths = sys.argv[2:]
first = tifffile.imread(paths[0]).astype(np.float32)
H, W, _ = first.shape
cy, cx = (H - 1) / 2, (W - 1) / 2
rng = np.random.default_rng(1)
py = rng.uniform(300, H - 300, 300000); px = rng.uniform(300, W - 300, 300000)
iy, ix = py.astype(int), px.astype(int)
g = first[iy, ix, 1]


def positions(p, y, x):
    s, ty, tx = p
    return cy + s * (y - cy) + ty, cx + s * (x - cx) + tx


def cost(p):
    ty, tx = positions(p, iy, ix)
    t = ndimage.map_coordinates(truth_full[..., 1], [ty, tx], order=1)
    A = np.stack([g, np.ones_like(g)], 1)
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    return float(np.mean((A @ coef - t) ** 2))


best = min(((cost((s, 4.0, 4.0)), s) for s in np.linspace(0.996, 1.0, 21)))
res = optimize.minimize(cost, (best[1], 4.0, 4.0), method='Nelder-Mead',
                        options={'xatol': 1e-5, 'fatol': 1e-3, 'maxiter': 400})
p = res.x
print('similarity', [round(float(v), 5) for v in p], 'cost', round(res.fun, 2), flush=True)
B = 96
yy, xx = np.mgrid[B:H - B, B:W - B].astype(np.float32)
ty, tx = positions(p, yy, xx)
truth = np.stack([ndimage.map_coordinates(truth_full[..., c], [ty, tx], order=3) for c in range(3)], -1)
del yy, xx


def patch(q):
    # Output-coordinate rectangle covering truth rectangle q (scale ~1).
    y0 = int((q[0] - p[1] - cy) / p[0] + cy) - B
    x0 = int((q[2] - p[2] - cx) / p[0] + cx) - B
    return slice(y0, y0 + q[1] - q[0]), slice(x0, x0 + q[3] - q[2])


out = {'similarity': list(map(float, p))}
for path in paths:
    img = (first if path == paths[0] else tifffile.imread(path).astype(np.float32))[B:H - B, B:W - B]
    fitted = np.empty_like(img)
    for c in range(3):
        A = np.stack([img[..., c].ravel()[::7], np.ones(img[..., c].size, np.float32)[::7]], 1)
        coef, *_ = np.linalg.lstsq(A, truth[..., c].ravel()[::7], rcond=None)
        fitted[..., c] = img[..., c] * coef[0] + coef[1]
    err = fitted - truth
    r = {f'rmse_{"rgb"[c]}': float(np.sqrt(np.mean(err[..., c].astype(np.float64) ** 2))) for c in range(3)}
    e = fitted[patch(EDGE)]
    chroma = np.stack([e[..., 0] - e[..., 1], e[..., 2] - e[..., 1]], -1)
    hp = chroma - np.stack([ndimage.gaussian_filter(chroma[..., k], 3) for k in range(2)], -1)
    r['edge_hf_chroma'] = float(np.sqrt(np.mean(hp ** 2)))
    r['edge_rmse'] = float(np.sqrt(np.mean((e.mean(-1) - truth[patch(EDGE)].mean(-1)) ** 2)))
    r['zone_rmse'] = float(np.sqrt(np.mean(err[patch(ZONE)] ** 2)))
    out[path] = r
    print(path.replace('\\', '/').split('/')[-1], ' '.join(f'{k} {v:.2f}' for k, v in r.items()), flush=True)
print(json.dumps(out))
