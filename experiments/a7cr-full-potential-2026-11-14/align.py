"""Per-plane similarity alignment from near-span plane pairs.

  python -X utf8 align.py WORK_DIR [REFERENCE_PLANE]

Reads WORK_DIR/q4/pNNN.npy (green, 4x4 box-averaged). Each plane k gets
T_k: x_plane = c + s_k R(theta_k) (x_ref - c) + t_k, c the frame centre, the
reference plane the identity. Pairs at spans 1, 2, 3, 4 (weights 1 / span) are
both warped to the reference geometry with the current estimate and their
residual similarity is measured by one parametric Lucas-Kanade step on
band-passed images (tile normal equations, Huber-reweighted by tile). A global
least-squares solve over all pairs updates every plane; three rounds. Near
spans are used because adjacent planes are focused almost alike, which keeps
defocus from biasing the registration; the cost is a slow random walk of the
far planes, which matters little because fusion only combines neighbours.

Writes WORK_DIR/align.json (full-resolution photosite units) with per-round
residuals: the rms of per-tile shifts left between span-1 and span-4 pairs.
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

work = Path(sys.argv[1])
files = sorted((work / 'q4').glob('p*.npy'))
planes = [int(f.stem[1:]) for f in files]
ref = int(sys.argv[2]) if len(sys.argv) > 2 else planes[len(planes) // 2]
Q = torch.stack([torch.from_numpy(np.load(f).astype(np.float32)) for f in files]).to(fp.DEV)
n, H, W = Q.shape
Q = Q / Q.mean((1, 2), keepdim=True)
B = torch.stack([fp.gauss(q, 1.0) - fp.gauss(q, 4.0) for q in Q])
del Q
cx, cy = (W - 1) / 2, (H - 1) / 2
T = 96
ty, tx = H // T, W // T
yy, xx = torch.meshgrid(torch.arange(H, device=fp.DEV, dtype=torch.float32),
                        torch.arange(W, device=fp.DEV, dtype=torch.float32), indexing='ij')
# Tile-centre design rows: u = [dx, -dy, 1, 0] . m, v = [dy, dx, 0, 1] . m, m = (ds, dtheta, dtx, dty).
tcx = (torch.arange(tx, device=fp.DEV, dtype=torch.float64) + 0.5) * T - 0.5 - cx
tcy = (torch.arange(ty, device=fp.DEV, dtype=torch.float64) + 0.5) * T - 0.5 - cy
TY, TX = torch.meshgrid(tcy, tcx, indexing='ij')
one, zero = torch.ones_like(TX), torch.zeros_like(TX)
P = torch.stack([torch.stack([TX, -TY, one, zero], -1), torch.stack([TY, TX, zero, one], -1)], -2)  # [ty, tx, 2, 4]


def warp(img, p):
    s, th, dx, dy = p
    c, sn = np.cos(th), np.sin(th)
    X = cx + s * (c * (xx - cx) - sn * (yy - cy)) + dx
    Y = cy + s * (sn * (xx - cx) + c * (yy - cy)) + dy
    grid = torch.stack([2 * (X + 0.5) / W - 1, 2 * (Y + 0.5) / H - 1], -1)[None]
    return F.grid_sample(img[None, None], grid, mode='bicubic', padding_mode='border', align_corners=False)[0, 0]


def pool(v):
    return v[:ty * T, :tx * T].reshape(ty, T, tx, T).sum((1, 3)).double()


def measure(wj, wk):
    """Residual similarity m and per-tile shift field between warped images:
    features sit at x in wj and at x + u in wk."""
    g = 0.5 * (wj + wk)
    gx = F.pad((g[:, 2:] - g[:, :-2]) / 2, (1, 1))
    gy = F.pad((g[2:, :] - g[:-2, :]) / 2, (0, 0, 1, 1))
    dt = wk - wj
    A = torch.stack([torch.stack([pool(gx * gx), pool(gx * gy)], -1), torch.stack([pool(gx * gy), pool(gy * gy)], -1)], -2)
    b = -torch.stack([pool(gx * dt), pool(gy * dt)], -1)
    lam = torch.linalg.eigvalsh(A)[..., 0]
    good = lam > 0.05 * lam.max()
    u = torch.linalg.solve(A + 1e-12 * torch.eye(2, device=A.device, dtype=A.dtype), b[..., None])[..., 0]
    w = good.double()
    for _ in range(3):
        M = torch.einsum('yxai,yxab,yxbj,yx->ij', P, A, P, w)
        v = torch.einsum('yxai,yxa,yx->i', P, b, w)
        m = torch.linalg.solve(M, v)
        res = (u - torch.einsum('yxai,i->yxa', P, m)).norm(dim=-1)
        scale = res[good].median() * 1.4826 + 1e-9
        w = good.double() * torch.clamp(2.0 * scale / res.clamp(min=1e-12), max=1.0)
    rms = float((res[good] ** 2).mean().sqrt())
    FIELD.append(((u - torch.einsum('yxai,i->yxa', P, m)) * good[..., None]).cpu().numpy())
    GOOD.append(good.cpu().numpy())
    return m, M, rms, int(good.sum())


FIELD, GOOD = [], []
params = np.zeros((n, 4))
params[:, 0] = 1.0
r0 = planes.index(ref)
history = []
SPANS = [1, 2, 3, 4]
for rnd in range(4):
    warped = [warp(B[i], params[i]) for i in range(n)]
    FIELD.clear()
    GOOD.clear()
    N = np.zeros((4 * n, 4 * n))
    rhs = np.zeros(4 * n)
    stats = {s: [] for s in SPANS}
    for span in SPANS:
        for j in range(n - span):
            k = j + span
            m, M, rms, good = measure(warped[j], warped[k])
            M = (M / M.diagonal().mean()).cpu().numpy() / span
            m = m.cpu().numpy()
            stats[span].append(rms)
            for a, sa in ((j, -1.0), (k, 1.0)):
                rhs[4 * a:4 * a + 4] += sa * (M @ m)
                for b_, sb in ((j, -1.0), (k, 1.0)):
                    N[4 * a:4 * a + 4, 4 * b_:4 * b_ + 4] += sa * sb * M
    del warped
    N[4 * r0:4 * r0 + 4, :] = 0
    N[:, 4 * r0:4 * r0 + 4] = 0
    N[4 * r0:4 * r0 + 4, 4 * r0:4 * r0 + 4] = np.eye(4)
    rhs[4 * r0:4 * r0 + 4] = 0
    history.append({f'span{s}_tile_rms_qpx': float(np.sqrt(np.mean(np.square(v)))) for s, v in stats.items()})
    print('round', rnd, history[-1], flush=True)
    if rnd == 3:
        break  # the last round only measures the residual
    eps = np.linalg.solve(N, rhs).reshape(n, 4)
    params += eps
    print('   max update: scale %.2e theta %.2e shift %.3f qpx' % (np.abs(eps[:, 0]).max(), np.abs(eps[:, 1]).max(), np.abs(eps[:, 2:]).max()), flush=True)

np.save(work / 'align-residual-field.npy', np.stack(FIELD))
np.save(work / 'align-residual-good.npy', np.stack(GOOD))
out = {'reference': ref, 'width': W * 4, 'height': H * 4, 'rounds': history,
       'planes': {str(p): {'scale': params[i, 0], 'theta': params[i, 1], 'tx': 4 * params[i, 2], 'ty': 4 * params[i, 3]}
                  for i, p in enumerate(planes)}}
(work / 'align.json').write_text(json.dumps(out, indent=1) + '\n')
i0, i1 = 0, n - 1
print('first', planes[i0], params[i0], 'last', planes[i1], params[i1])
