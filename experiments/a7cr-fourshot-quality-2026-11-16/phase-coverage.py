"""Q7: do the planes near a point's focus sample it at sub-pixel phases
spread well enough to resolve beyond the pixel grid?

  python -X utf8 phase-coverage.py ALIGN.json [--centre-plane 100]

ALIGN.json: the prototype's per-plane similarity (scale, theta, tx, ty about
the frame centre), fitted on the scarab four-shot run. For a grid of frame
positions and a window of K consecutive planes about --centre-plane, each
plane's sampling phase (fractional photosite position, x and y) at that
point. Doubling the sampling density means separating four aliased
components per frequency (baseband and the x, y and xy aliases); with phases
d_k the system matrix is A[k, m] = exp(2 pi i m . d_k), m in {0,1}^2. The
noise amplification of that separation relative to ideally spread phases is

  NA = sqrt(mean diag(inv(A^H A / K)))      (1 = ideal; large = ill-posed)

Printed: quantiles of NA over the frame for K = 4, 6, 10, 16, and the same
for a control where every plane's phase is random (what a deliberate
sixteen-shot sequence or true dither would give).
"""
import json
import sys

import numpy as np

path = sys.argv[1]
kc = int(sys.argv[sys.argv.index('--centre-plane') + 1]) if '--centre-plane' in sys.argv else 100
a = json.load(open(path))
W, H = a['width'], a['height']
pl = {int(k): v for k, v in a['planes'].items()}
cx, cy = (W - 1) / 2, (H - 1) / 2
xs = np.linspace(200, W - 200, 48)
ys = np.linspace(200, H - 200, 32)
X, Y = np.meshgrid(xs, ys)
M = np.array([[0, 0], [1, 0], [0, 1], [1, 1]])
rng = np.random.default_rng(1)


def amplification(d):
    """d: [K, ny, nx, 2] phases -> NA [ny, nx]."""
    A = np.exp(2j * np.pi * np.einsum('kyxd,md->yxkm', d, M))
    G = np.einsum('yxkm,yxkn->yxmn', A.conj(), A) / d.shape[0]
    G = G + 1e-9 * np.eye(4)
    inv = np.linalg.inv(G)
    return np.sqrt(np.real(np.einsum('yxmm->yx', inv)) / 4)


for K in (4, 6, 10, 16):
    ks = [k for k in range(kc - K // 2, kc - K // 2 + K)]
    d = []
    for k in ks:
        s, th, tx, ty = pl[k]['scale'], pl[k]['theta'], pl[k]['tx'], pl[k]['ty']
        u, v = X - cx, Y - cy
        sx = cx + s * (u - th * v) + tx
        sy = cy + s * (v + th * u) + ty
        d.append(np.stack([sx % 1.0, sy % 1.0], -1))
    d = np.stack(d)
    na = amplification(d)
    ctrl = amplification(rng.random(d.shape))
    q = np.quantile(na, [0.1, 0.5, 0.9])
    qc = np.quantile(ctrl, [0.1, 0.5, 0.9])
    print(f'K = {K:2d} planes about {kc}: noise amplification p10 / median / p90 = {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f}; '
          f'under 2: {100 * (na < 2).mean():.0f} % of the frame, under 4: {100 * (na < 4).mean():.0f} %;   random phases: {qc[0]:.2f} / {qc[1]:.2f} / {qc[2]:.2f}')
