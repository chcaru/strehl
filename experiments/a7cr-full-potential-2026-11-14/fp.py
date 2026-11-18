"""Shared pieces of the A7CR full-potential prototype (see brief.md).

GPU (torch) throughout; float32 arithmetic on u16 samples. Coordinates are
photosites of member 1's active area, x right, y down, RGGB with red at (0, 0).
"""
import json
import math
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

DEV = torch.device('cuda')


class Run:
    """An exported run (export-members.rs): member mosaics per plane."""

    def __init__(self, cache):
        self.cache = Path(cache)
        self.meta = {}
        for line in (self.cache / 'members.jsonl').read_text().splitlines():
            m = json.loads(line)
            self.meta[m['plane']] = m
        self.planes = sorted(p for p in self.meta if (self.cache / f'p{p:03d}.u16').exists())
        m0 = self.meta[self.planes[0]]
        self.W, self.H, self.P = m0['width'], m0['height'], m0['pad']
        self.black, self.white = m0['black'], m0['white']

    def members(self, plane):
        """[members, H + 2P, W + 2P] float32 on the GPU, black-subtracted."""
        m = self.meta[plane]
        a = np.fromfile(self.cache / f'p{plane:03d}.u16', dtype='<u2')
        a = a.reshape(m['members'], self.H + 2 * self.P, self.W + 2 * self.P)
        return torch.from_numpy(a.view(np.int16)).to(DEV).float() - self.black


def cfa(x, y):
    """0 red, 1 green, 2 blue at RGGB parity (x, y)."""
    return 0 if (x % 2, y % 2) == (0, 0) else 2 if (x % 2, y % 2) == (1, 1) else 1


def assemble(mem, offsets, gains, pad):
    """Nominal assembly: [3, H, W] measured R, G (mean of two), B.

    Also returns `src[c][py][px]`: the members supplying channel c at output
    parity (px, py) (one for red and blue, two for green), and for green the
    difference of its two samples (first minus second member) as [H, W].
    """
    H, W = mem.shape[1] - 2 * pad, mem.shape[2] - 2 * pad
    out = torch.zeros(3, H, W, device=mem.device)
    gdiff = torch.zeros(H, W, device=mem.device)
    src = [[[[] for _ in range(2)] for _ in range(2)] for _ in range(3)]
    for k, (ox, oy) in enumerate(offsets):
        v = mem[k, pad + oy:pad + oy + H, pad + ox:pad + ox + W] / gains[k]
        for py in (0, 1):
            for px in (0, 1):
                c = cfa(px + ox, py + oy)
                first = not src[c][py][px]
                src[c][py][px].append(k)
                if c == 1:
                    out[1, py::2, px::2] += 0.5 * v[py::2, px::2]
                    gdiff[py::2, px::2] += v[py::2, px::2] if first else -v[py::2, px::2]
                else:
                    out[c, py::2, px::2] = v[py::2, px::2]
    return out, src, gdiff


def conv_sep(x, k, axis):
    """Convolve [.., H, W] with 1-D kernel k along axis (-1 x, -2 y), reflect."""
    k = torch.as_tensor(k, dtype=x.dtype, device=x.device)
    r = len(k) // 2
    shape = x.shape
    x = x.reshape(-1, 1, shape[-2], shape[-1])
    if axis == -1:
        x = F.conv2d(F.pad(x, (r, r, 0, 0), mode='reflect'), k.view(1, 1, 1, -1))
    else:
        x = F.conv2d(F.pad(x, (0, 0, r, r), mode='reflect'), k.view(1, 1, -1, 1))
    return x.reshape(shape)


TENT = [0.25, 0.5, 0.25]
# Sixth-order central difference: antisymmetric, so a parity-class error that
# is common to a tap pair cancels.
DERIV = [-1 / 60, 3 / 20, -3 / 4, 0.0, 3 / 4, -3 / 20, 1 / 60]


def tent(x):
    return conv_sep(conv_sep(x, TENT, -1), TENT, -2)


def grad(x):
    # conv2d correlates: DERIV as written gives d/dx with x increasing right.
    return conv_sep(x, DERIV, -1), conv_sep(x, DERIV, -2)


def gauss(x, sigma):
    r = max(1, int(math.ceil(3.5 * sigma)))
    t = torch.arange(-r, r + 1, dtype=torch.float32)
    k = torch.exp(-0.5 * (t / sigma) ** 2)
    k = (k / k.sum()).tolist()
    return conv_sep(conv_sep(x, k, -1), k, -2)


GAIN_DN_PER_E = 0.4040   # measured, capture 1 (ISO 100)
READ_NOISE_DN = 1.334    # measured dark floor, ISO 100
D2 = [-1 / 12, 4 / 3, -5 / 2, 4 / 3, -1 / 12]
DERIV_NOISE = sum(c * c for c in DERIV)
D2_NOISE = sum(c * c for c in D2)
PARAMS = ['ex', 'ey', 'gain', 'pedestal', 'bxx', 'byy', 'bxy']


def regressors(x):
    """[gx, gy, level, 1, hxx, hyy, hxy] of a plane."""
    gx, gy = grad(x)
    return [gx, gy, tent(x), torch.ones_like(x), conv_sep(x, D2, -1), conv_sep(x, D2, -2), conv_sep(gx, DERIV, -2)]


def member_motion(rgb, src, gdiff, tiles=None, clip=None):
    """Per-member differences that leave a 2-photosite-period trace in an
    assembled group, fitted jointly from all three channels.

    At a site supplied by member k, value = truth + theta_k . phi with phi =
    [gx, gy, level, 1, hxx, hyy, hxy]: a sub-photosite offset (ex, ey), a gain
    and a pedestal error, and a blur difference (bxx, byy, bxy; motion during
    one member's exposure, or second-order offset terms). The 3x3 tent of a
    plane carries the member mean (each parity class has weight 1/4), so with
    n = plane - tent(plane):
      red, blue:   n = (theta_k - mean) . phi        (k supplies the site)
      green mean:  n = ((theta_a + theta_b) / 2 - mean) . phi
      green diff:  G_a - G_b = (theta_a - theta_b) . phi
    One weighted least-squares solve for all four members; the common term is
    unobservable and set to zero. Derivative regressors are noisy, which would
    attenuate the fit; their known noise power (the injected sensor noise
    model through the filters) is subtracted from the normal matrix. Returns
    [4, 7] in PARAMS order, or per-tile [ty, tx, 4, 7] when `tiles` is
    (ty, tx). `clip` [3]: ignore sites near clipped samples.
    """
    ty, tx = tiles or (1, 1)
    dev = rgb.device
    K = len(PARAMS)
    N = torch.zeros(ty, tx, 4 * K, 4 * K, device=dev, dtype=torch.float64)
    r = torch.zeros(ty, tx, 4 * K, device=dev, dtype=torch.float64)
    # Noise covariance of the regressors per unit sample variance.
    C = torch.zeros(K, K, dtype=torch.float64, device=dev)
    C[0, 0] = C[1, 1] = DERIV_NOISE
    C[4, 4] = C[5, 5] = D2_NOISE
    C[4, 5] = C[5, 4] = D2[2] * D2[2]
    C[6, 6] = DERIV_NOISE ** 2

    def pool(v):  # [h, w] -> [ty, tx] sums
        h, w = v.shape
        v = v[:h // ty * ty, :w // tx * tx].double()
        return v.reshape(ty, h // ty, tx, w // tx).sum((1, 3))

    def add(coef, phi, y, w, weight, var):
        coef = torch.tensor(coef, dtype=torch.float64, device=dev)
        A = torch.zeros(ty, tx, K, K, device=dev, dtype=torch.float64)
        v = torch.zeros(ty, tx, K, device=dev, dtype=torch.float64)
        for i in range(K):
            v[..., i] = pool(phi[i] * y * w)
            for j in range(i, K):
                A[..., i, j] = A[..., j, i] = pool(phi[i] * phi[j] * w)
        A -= pool(var * w)[..., None, None] * C
        N.add_(weight * torch.einsum('a,b,yxij->yxaibj', coef, coef, A).reshape(ty, tx, 4 * K, 4 * K))
        r.add_(weight * torch.einsum('a,yxi->yxai', coef, v).reshape(ty, tx, 4 * K))

    for c in range(3):
        x = rgb[c]
        phi_full = regressors(x)
        n = x - phi_full[2]
        var = (GAIN_DN_PER_E * phi_full[2].clamp(min=0) + READ_NOISE_DN ** 2) * (0.5 if c == 1 else 1.0)
        ok = torch.ones_like(x)
        if clip is not None:
            ok = ok * (F.max_pool2d(x[None, None], 9, 1, 4)[0, 0] < clip[c]).float()
        for py in (0, 1):
            for px in (0, 1):
                ks = src[c][py][px]
                sl = (slice(py, None, 2), slice(px, None, 2))
                phi = [f[sl] for f in phi_full]
                coef = [(sum(1.0 for k in ks if k == j) / len(ks)) - 0.25 for j in range(4)]
                add(coef, phi, n[sl], ok[sl], 1.0, var[sl])
                if c == 1:
                    add([float(j == ks[0]) - float(j == ks[1]) for j in range(4)], phi, gdiff[sl], ok[sl], 0.25, var[sl])
        del phi_full
    scale = N.diagonal(dim1=-2, dim2=-1).mean(-1)[..., None, None] + 1e-30
    sol = torch.linalg.solve(N + 1e-9 * scale * torch.eye(4 * K, device=dev, dtype=N.dtype), r[..., None])[..., 0]
    sol = sol.reshape(ty, tx, 4, K)
    sol = sol - sol.mean(-2, keepdim=True)
    return sol[0, 0] if tiles is None else sol


APPLY = [0, 1, 4, 5, 6]  # offsets and blur differences; gain and pedestal are nuisance terms


def compensate(rgb, src, motion, iterations=3):
    """Bring every member's samples to the group mean position and blur
    (first order in the fitted terms, fixed-point on the derivatives):
    [3, H, W]."""
    e = motion.float()
    obs = rgb
    x = rgb.clone()
    for _ in range(iterations):
        nxt = obs.clone()
        for c in range(3):
            phi = regressors(x[c])
            for py in (0, 1):
                for px in (0, 1):
                    ks = src[c][py][px]
                    m = sum(e[k] for k in ks) / len(ks)
                    sl = (slice(py, None, 2), slice(px, None, 2))
                    for i in APPLY:
                        nxt[c][sl] -= m[i] * phi[i][sl]
            del phi
        x = nxt
    return x


def nyquist_energy(x, sigma=12.0, step=16):
    """Local amplitude of the three 2-photosite-period patterns (alternating
    in x, in y, checkerboard): [3, h / step, w / step]. Taken on x - tent(x),
    which keeps those patterns whole and removes smooth content exactly, then
    demodulated and Gaussian-windowed."""
    H, W = x.shape
    n = x - tent(x)
    yy = torch.arange(H, device=x.device).view(-1, 1)
    xx = torch.arange(W, device=x.device).view(1, -1)
    out = []
    for sign in ((-1.0) ** xx, (-1.0) ** yy, (-1.0) ** (xx + yy)):
        out.append(gauss(n * sign, sigma)[::step, ::step])
    return torch.stack(out)


def lanczos_weights(frac, a=4):
    """Weights for taps at offsets -(a-1)..a from floor: frac [N] -> [N, 2a]."""
    t = torch.arange(-(a - 1), a + 1, device=frac.device, dtype=torch.float64).view(1, -1) - frac.view(-1, 1)
    w = torch.sinc(t) * torch.sinc(t / a)
    w = torch.where(t.abs() < a, w, torch.zeros_like(w))
    return (w / w.sum(1, keepdim=True)).float()


def resample_axis(x, coords, axis, a=4):
    """Resample [.., H, W] along `axis` (-1 or -2) at source coordinates
    `coords` [N] (float64 tensor), Lanczos-a, edge clamped."""
    n_src = x.shape[axis]
    base = torch.floor(coords)
    w = lanczos_weights(coords - base, a)
    base = base.long()
    out = None
    for t in range(2 * a):
        idx = (base + t - (a - 1)).clamp(0, n_src - 1)
        term = x.index_select(axis, idx) * (w[:, t].view(1, -1) if axis == -1 else w[:, t].view(-1, 1))
        out = term if out is None else out + term
    return out


def warp_scale_shift(x, scale, tx, ty, out_hw=None, centre=None):
    """out(u, v) = x(cx + scale * (u - cx) + tx, cy + scale * (v - cy) + ty)."""
    H, W = x.shape[-2:]
    oh, ow = out_hw or (H, W)
    cx, cy = centre or ((W - 1) / 2, (H - 1) / 2)
    u = torch.arange(ow, device=x.device, dtype=torch.float64)
    v = torch.arange(oh, device=x.device, dtype=torch.float64)
    x = resample_axis(x, cx + scale * (u - cx) + tx, -1)
    return resample_axis(x, cy + scale * (v - cy) + ty, -2)


def lanczos(t, a=4):
    w = torch.sinc(t) * torch.sinc(t / a)
    return torch.where(t.abs() < a, w, torch.zeros_like(w))


def shear(x, shift, axis, a=4):
    """out(line, i) = x(line, i + shift[line]) along `axis` (-1: lines are
    rows, shift [H]; -2: lines are columns, shift [W]); Lanczos-a, edge
    clamped. Small shifts only (a few photosites): each integer offset is one
    shifted copy of the image times a per-line weight, so no index tensors."""
    shift = shift.double()
    lo = int(math.floor(float(shift.min()))) - (a - 1)
    hi = int(math.floor(float(shift.max()))) + a
    js = list(range(lo, hi + 1))
    wts = torch.stack([lanczos(j - shift, a) for j in js])          # [J, lines]
    wts = (wts / wts.sum(0, keepdim=True)).float()
    n = x.shape[axis]
    pad = max(abs(lo), abs(hi))
    out = torch.zeros_like(x)
    if axis == -1:
        xp = F.pad(x[None, None], (pad, pad, 0, 0), mode='replicate')[0, 0]
        for j, w in zip(js, wts):
            if float(w.abs().max()) > 0:
                out += w.view(-1, 1) * xp[:, pad + j:pad + j + n]
    else:
        xp = F.pad(x[None, None], (0, 0, pad, pad), mode='replicate')[0, 0]
        for j, w in zip(js, wts):
            if float(w.abs().max()) > 0:
                out += w.view(1, -1) * xp[pad + j:pad + j + n, :]
    return out


def warp_similarity(x, scale, theta, tx, ty):
    """out(u) = x(c + scale * R(theta) (u - c) + t), c the frame centre, for a
    small theta: two shears (first order in theta; the neglected term is
    theta^2 times the radius) and one scale-and-shift resampling."""
    H, W = x.shape[-2:]
    cx, cy = (W - 1) / 2, (H - 1) / 2
    if abs(theta) * math.hypot(cx, cy) > 0.005:
        rows = torch.arange(H, device=x.device, dtype=torch.float64) - cy
        cols = torch.arange(W, device=x.device, dtype=torch.float64) - cx
        x = shear(x, -theta * rows, -1)       # g(a, b) = x(a - theta b, b)
        x = shear(x, theta * cols, -2)        # r(a, b) = g(a, b + theta a)
        tx, ty = tx + theta * ty, ty - theta * tx   # R(-theta) t
    return warp_scale_shift(x, scale, tx, ty)


def resample_dense_axis(x, shift, axis, a=4):
    """out = x sampled at its own position plus `shift` ([H, W], photosites)
    along `axis` (-1 x, -2 y); Lanczos-a, edge clamped. Any shift size."""
    H, W = x.shape
    n = W if axis == -1 else H
    grid = torch.arange(n, device=x.device, dtype=torch.float32)
    pos = shift + (grid.view(1, -1) if axis == -1 else grid.view(-1, 1))
    base = torch.floor(pos)
    frac = pos - base
    base = base.long()
    out = torch.zeros_like(x)
    norm = torch.zeros_like(x)
    dim = 1 if axis == -1 else 0
    for t in range(-(a - 1), a + 1):
        w = lanczos(t - frac, a)
        out += w * torch.gather(x, dim, (base + t).clamp(0, n - 1))
        norm += w
    return out / norm


def warp_dense(x, dx, dy):
    """out(u, v) = x(u + dx(u, v), v + dy(u, v)) for a smooth displacement:
    one pass along x, one along y (the neglected term is dy times the
    gradient of dx)."""
    return resample_dense_axis(resample_dense_axis(x, dx, -1), dy, -2)


def to_png(path, rgb, gain, gamma=2.2):
    """[3, h, w] linear tensor -> 8-bit PNG with one gain and power."""
    from PIL import Image
    v = (rgb * gain).clamp(0, 1) ** (1 / gamma)
    Image.fromarray((v.permute(1, 2, 0).cpu().numpy() * 255 + 0.5).astype(np.uint8)).save(path)
