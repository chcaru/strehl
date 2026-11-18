"""Lateral colour of a full-resolution render, with a permutation null: the
evidence block for an `OpticalProfile`.

  python -X utf8 lateral-profile.py RENDER.tif [--permutations 2000]

RENDER.tif: a `strehl stack --demosaic` output (H x W x 3, 16-bit, linear
camera-native), rendered WITHOUT lateral-CA correction. Per 128-px tile,
band-passed red (blue) is regressed on band-passed green and its gradient
(the same instrument as ca.py): C = a G - a d . grad(G), d the channel's
displacement from green. Photosites near a clipped sample are left out. Model
per channel: d = eps * (x - c) + t, Huber-fitted; coarse band (sigma 4-12)
first, then the channel is resampled with the fit and a fine band (1.5-4)
refines it, twice.

Reports eps in ppm, translation in sensor px and in plane px (half), the
fraction of displacement power the radial model explains (`1 - rms_after^2 /
rms_before^2`), residual rms in plane px (the profile's `sensel` unit is the
CFA plane), the tile count, the largest normalised field height a used tile
reached (support_r_max, 1 = corner), and a permutation p for eps: tile
displacement vectors are shuffled across tile positions and refitted; p is
the fraction of shuffles whose |eps| reaches the observed one (+1 smoothing).
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

path = Path(sys.argv[1])
perms = int(sys.argv[sys.argv.index('--permutations') + 1]) if '--permutations' in sys.argv else 2000
img = torch.from_numpy(tifffile.imread(path).astype(np.float32)).to(fp.DEV).permute(2, 0, 1)
_, H, W = img.shape
T = 128
ty, tx = H // T, W // T
cx, cy = (W - 1) / 2, (H - 1) / 2
half_diag = float(np.hypot(cx, cy))
TX, TY = np.meshgrid((np.arange(tx) + 0.5) * T - 0.5 - cx, (np.arange(ty) + 0.5) * T - 0.5 - cy)
clipped = (img.max(0).values > 0.95 * 65535).float()
mask = 1.0 - (F.max_pool2d(clipped[None, None], 25, 1, 12)[0, 0] > 0).float()


def pool(v):
    return v[:ty * T, :tx * T].reshape(ty, T, tx, T).sum((1, 3)).double()


def tile_shift(c, g, lo, hi):
    cb = fp.gauss(c, lo) - fp.gauss(c, hi)
    gb = fp.gauss(g, lo) - fp.gauss(g, hi)
    gx, gy = fp.grad(gb)
    phi = [gb, gx, gy]
    A = torch.zeros(ty, tx, 3, 3, dtype=torch.float64, device=fp.DEV)
    b = torch.zeros(ty, tx, 3, dtype=torch.float64, device=fp.DEV)
    for i in range(3):
        b[..., i] = pool(phi[i] * cb * mask)
        for j in range(i, 3):
            A[..., i, j] = A[..., j, i] = pool(phi[i] * phi[j] * mask)
    ridge = (1e-9 * A.diagonal(dim1=-2, dim2=-1).mean(-1) + 1e-12)[..., None, None] * torch.eye(3, device=fp.DEV, dtype=torch.float64)
    sol = torch.linalg.solve(A + ridge, b[..., None])[..., 0]
    a = sol[..., 0]
    d = -sol[..., 1:] / a.clamp(min=1e-3)[..., None]
    lam = torch.linalg.eigvalsh(A[..., 1:, 1:])[..., 0]
    resid = (pool(cb * cb * mask) - (sol * b).sum(-1)) / pool(cb * cb * mask).clamp(min=1e-9)
    used = pool(mask) / (T * T)
    a, d, lam, resid, used = (v.cpu().numpy() for v in (a, d, lam, resid, used))
    return d, (a > 0.2) & (a < 5) & (lam > 0.05 * np.median(lam)) & (resid < 0.5) & (used > 0.5)


def fit(x, y, dx, dy):
    A = np.stack([np.concatenate([x, y]), np.concatenate([np.ones_like(x), np.zeros_like(x)]),
                  np.concatenate([np.zeros_like(x), np.ones_like(x)])], 1)
    t = np.concatenate([dx, dy])
    hw = np.ones_like(t)
    for _ in range(10):
        sw = np.sqrt(hw)
        p = np.linalg.lstsq(A * sw[:, None], t * sw, rcond=None)[0]
        res = t - A @ p
        s = 1.4826 * np.median(np.abs(res)) + 1e-9
        hw = np.minimum(1.0, 2.0 * s / np.maximum(np.abs(res), 1e-12))
    return p


def rms(v):
    return float(np.sqrt((v ** 2).sum(-1).mean()))


report = {'render': str(path), 'tile_px': T, 'permutations': perms}
g = img[1]
for c, name in ((0, 'red'), (2, 'blue')):
    d0, ok0 = tile_shift(img[c], g, 4.0, 12.0)
    ok0 &= np.abs(d0).max(-1) < 8
    p = fit(TX[ok0], TY[ok0], d0[ok0][:, 0], d0[ok0][:, 1])
    raw_rms = rms(d0[ok0])
    for _ in range(3):
        xx = torch.arange(W, device=fp.DEV, dtype=torch.float32).view(1, -1) - cx
        yy = torch.arange(H, device=fp.DEV, dtype=torch.float32).view(-1, 1) - cy
        ch = fp.warp_dense(img[c], (p[0] * xx + p[1]).expand(H, W).contiguous(), (p[0] * yy + p[2]).expand(H, W).contiguous())
        d, ok = tile_shift(ch, g, 1.5, 4.0)
        ok &= np.abs(d).max(-1) < 1.5
        p = p + fit(TX[ok], TY[ok], d[ok][:, 0], d[ok][:, 1])
    ch = fp.warp_dense(img[c], (p[0] * xx + p[1]).expand(H, W).contiguous(), (p[0] * yy + p[2]).expand(H, W).contiguous())
    d, ok = tile_shift(ch, g, 1.5, 4.0)
    ok &= np.abs(d).max(-1) < 1.5
    after = rms(d[ok])
    # Uncorrected displacement of the same tiles, in the fine band: the
    # corrected residual plus the applied model.
    full = d + np.stack([p[0] * TX + p[1], p[0] * TY + p[2]], -1)
    before = rms(full[ok])
    x, y, dx, dy = TX[ok], TY[ok], full[ok][:, 0], full[ok][:, 1]
    rng = np.random.default_rng(1)
    hits = 0
    for _ in range(perms):
        k = rng.permutation(len(x))
        if abs(fit(x, y, dx[k], dy[k])[0]) >= abs(p[0]):
            hits += 1
    r_max = float((np.hypot(x, y) / half_diag).max())
    report[name] = {
        'eps_ppm': p[0] * 1e6, 'translation_sensor_px': [p[1], p[2]], 'translation_plane_px': [p[1] / 2, p[2] / 2],
        'tiles': int(ok.sum()), 'rms_before_sensor_px': before, 'rms_after_sensor_px': after,
        'rms_after_plane_px': after / 2, 'r_squared': 1 - (after / before) ** 2,
        'permutation_p': (hits + 1) / (perms + 1), 'support_r_max': r_max, 'coarse_rms_sensor_px': raw_rms,
    }
    print(f'{name}: eps {p[0] * 1e6:+.1f} ppm ({p[0] * half_diag:+.2f} sensor px at the corner), translation ({p[1]:+.3f}, {p[2]:+.3f}) sensor px; '
          f'{int(ok.sum())} tiles; rms {before:.3f} -> {after:.3f} sensor px (R^2 {1 - (after / before) ** 2:.3f}); '
          f'permutation p {(hits + 1) / (perms + 1):.4f}; support r_max {r_max:.3f}', flush=True)
out = path.with_suffix('.lateral.json')
out.write_text(json.dumps(report, indent=1) + '\n')
print('wrote', out)
