"""Green-against-green displacement between aligned frames k and k + j over
every tile (not only those in focus at k), for j = 1 and j = 5: the
inter-frame residual field of the merge's alignment.

  python -X utf8 axial-probe-pairs.py PLANES_DIR OUT.npz

Same planes and instrument as axial-probe.py (band sigma 1 - 3 plane px,
64-px tiles). out: d1[k] = G(k + 1) from G(k), d5[k] = G(k + 5) from G(k),
each [ty, tx, 5] = dx, dy, a, resid, used (plane px).
"""
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

src, out = Path(sys.argv[1]), Path(sys.argv[2])
W, H, _, _ = (int(v) for v in (src / 'geom.txt').read_text().split())
files = sorted(src.glob('f*.f32'))
N = len(files)
T = 64
ty, tx = H // T, W // T
dev = fp.DEV
CLIP = 0.9 * 15871.0


def pool(v):
    return v[:ty * T, :tx * T].reshape(ty, T, tx, T).sum((1, 3)).double()


cache = {}


def band(i):
    if i not in cache:
        for old in [k for k in cache if k < i - 8]:
            del cache[old]
        a = np.fromfile(files[i], dtype='<f4').reshape(3, H, W)
        p = torch.from_numpy(a).to(dev)
        clipped = (p >= CLIP).any(0).float()
        mask = 1.0 - (F.max_pool2d(clipped[None, None], 13, 1, 6)[0, 0] > 0).float()
        cache[i] = (fp.gauss(p[1], 1.0) - fp.gauss(p[1], 3.0), mask)
    return cache[i]


def tile_shift(cb, gb, mask):
    gx, gy = fp.grad(gb)
    phi = [gb, gx, gy]
    A = torch.zeros(ty, tx, 3, 3, dtype=torch.float64, device=dev)
    b = torch.zeros(ty, tx, 3, dtype=torch.float64, device=dev)
    for i in range(3):
        b[..., i] = pool(phi[i] * cb * mask)
        for j in range(i, 3):
            A[..., i, j] = A[..., j, i] = pool(phi[i] * phi[j] * mask)
    ridge = (1e-9 * A.diagonal(dim1=-2, dim2=-1).mean(-1) + 1e-12)[..., None, None] * torch.eye(3, device=dev, dtype=torch.float64)
    sol = torch.linalg.solve(A + ridge, b[..., None])[..., 0]
    a = sol[..., 0]
    d = -sol[..., 1:] / a.clamp(min=1e-3)[..., None]
    cc = pool(cb * cb * mask).clamp(min=1e-9)
    resid = (cc - (sol * b).sum(-1)) / cc
    used = pool(mask) / (T * T)
    return torch.cat([d, a[..., None], resid[..., None], used[..., None]], -1).cpu().numpy()


d1 = np.full((N, ty, tx, 5), np.nan)
d5 = np.full((N, ty, tx, 5), np.nan)
for k in range(N):
    bk, mk = band(k)
    for j, dst in ((1, d1), (5, d5)):
        if k + j < N:
            bj, mj = band(k + j)
            dst[k] = tile_shift(bj, bk, mk * mj)
    print('frame', k, flush=True)
np.savez(out, d1=d1, d5=d5, tile=T, w=W, h=H)
print('wrote', out)
