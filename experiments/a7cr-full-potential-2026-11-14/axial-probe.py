"""Frame-level probe of the axial-colour frame offset: where do red and blue
from frame k + j land relative to green in frame k, on the merge's own
aligned planes?

  python -X utf8 axial-probe.py PLANES_DIR OUT.npz

PLANES_DIR: `STREHL_AXIAL_DUMP` output of a `strehl stack --refine-ca=off`
run (fNNN.f32 = [3, h, w] f32, red / green site 1 / blue CFA planes on the
reference grid, after the alignment warp and the lateral profile; geom.txt).

Per 64-px tile (plane px; 1 plane px = 2 sensor px):
- through-focus band energy per channel (difference of Gaussians, sigma 1 and
  2) and its peak index kg, kr, kb (log-parabola about the smoothed maximum);
- for the tile's green focus frame k = round(kg) and each offset j: the
  displacement of X(k + j) from G(k), X in red, blue, and of G(k + j) from
  G(k) and R(k + j) from R(k). Instrument: band-passed (sigma 1 - 3) channel
  regressed on the reference and its gradient, C = a G - a d . grad(G), the
  one lateral-profile.py uses; photosites near a clipped sample are left out.

Fooled by: a blur difference between the pair scales d (the gradient term is
attenuated more than the level term), so compare arms at like blur; glints
whose defocused image moves; a tile mixing two depths.
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
JS = [-6, -3, 0, 1, 2, 3, 4, 5, 6, 7, 9]


def load(i):
    a = np.fromfile(files[i], dtype='<f4').reshape(3, H, W)
    return torch.from_numpy(a).to(dev)


def pool(v):
    return v[:ty * T, :tx * T].reshape(ty, T, tx, T).sum((1, 3)).double()


# Pass 1: through-focus energy and clipping.
energy = np.zeros((N, 3, ty, tx))
# The planes are black-subtracted DN, not white-balanced: the A7CR clips at
# 16383 - 512 = 15871 in every channel (resampling overshoots above it, so
# the plane maximum is not the clip level).
CLIP = 0.9 * 15871.0
clipfrac = np.zeros((ty, tx))
for i in range(N):
    p = load(i)
    clipfrac = np.maximum(clipfrac, (pool((p >= CLIP).any(0).float()) / (T * T)).cpu().numpy())
    for c in range(3):
        l1 = fp.gauss(p[c], 1.0)
        b = l1 - fp.gauss(l1, 3 ** 0.5)
        energy[i, c] = (pool(b * b) / (T * T)).cpu().numpy()


def peak(curve):
    s = curve.copy()
    for _ in range(2):
        s = 0.25 * np.concatenate([s[:1], s[:-1]]) + 0.5 * s + 0.25 * np.concatenate([s[1:], s[-1:]])
    k = int(s.argmax())
    floor = s.min()
    amp = s[k] - floor
    if k < 3 or k > N - 4 or amp < floor or amp <= 0:
        return np.nan, 0.0
    t = np.arange(-3, 4)
    y = np.log(np.maximum(s[k - 3:k + 4] - floor, 1e-9 * amp))
    w = (s[k - 3:k + 4] - floor) ** 2
    c = np.polyfit(t, y, 2, w=np.sqrt(w))
    if c[0] >= -1e-6:
        return np.nan, 0.0
    off = -c[1] / (2 * c[0])
    return (k + off, amp / max(floor, 1e-12)) if abs(off) < 2.5 else (np.nan, 0.0)


pk = np.full((3, ty, tx), np.nan)
contrast = np.zeros((3, ty, tx))
for c in range(3):
    for y in range(ty):
        for x in range(tx):
            pk[c, y, x], contrast[c, y, x] = peak(energy[:, c, y, x])
kg = pk[1]
print('tiles with a green peak', int(np.isfinite(kg).sum()), 'of', ty * tx, '| tiles with a clipped sample', int((clipfrac > 0).sum()),
      '| red - green median', np.nanmedian(pk[0] - kg), '| blue - green', np.nanmedian(pk[2] - kg), flush=True)

# Pass 2: displacements.
cache = {}


def bands(i):
    """Band-passed planes, gradients of each, and the unclipped mask."""
    if i not in cache:
        for old in [k for k in cache if k < i - 16]:
            del cache[old]
        p = load(i)
        clipped = (p >= CLIP).any(0).float()
        mask = 1.0 - (F.max_pool2d(clipped[None, None], 13, 1, 6)[0, 0] > 0).float()
        b = torch.stack([fp.gauss(p[c], 1.0) - fp.gauss(p[c], 3.0) for c in range(3)])
        cache[i] = (b, mask)
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
    return (torch.cat([d, a[..., None], resid[..., None], used[..., None]], -1)).cpu().numpy()


# pairs[name][j] = [ty, tx, 5]: dx, dy, a, resid, used  (NaN where no frame)
PAIRS = {'rg': (0, 1), 'bg': (2, 1), 'gg': (1, 1), 'rr': (0, 0), 'bb': (2, 2)}
res = {n: np.full((len(JS), ty, tx, 5), np.nan) for n in PAIRS}
kint = np.where(np.isfinite(kg), np.round(kg), -1).astype(int)
for k in range(N):
    sel = kint == k
    if not sel.any():
        continue
    bk, mk = bands(k)
    for ji, j in enumerate(JS):
        if not 0 <= k + j < N:
            continue
        bj, mj = bands(k + j)
        m = mk * mj
        for n, (c, r) in PAIRS.items():
            if j == 0 and c == r:
                continue
            res[n][ji][sel] = tile_shift(bj[c], bk[r], m)[sel]
    print('frame', k, int(sel.sum()), 'tiles', flush=True)
np.savez(out, js=np.array(JS), clipfrac=clipfrac, energy=energy, peak=pk, contrast=contrast, tile=T, w=W, h=H, **res)
print('wrote', out)
