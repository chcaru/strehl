"""Lateral colour, measured and corrected on a fused arm.

  python -X utf8 ca.py WORK_DIR ARM OUT_ARM [--model-only] [--placebo]

Measured on the fused image, not per plane: red focuses about five planes
from green on this lens, and on a specular subject a defocused highlight is
displaced in proportion to its defocus, so an in-plane red-versus-green
comparison reads axial colour times that walk as lateral displacement. In the
fused image each channel is at its own focus.

Per 128-px tile, band-passed red (blue) is regressed on band-passed green and
its gradient: C = a G - a d . grad(G), so d is where the channel's features
sit relative to green's. Photosites near a clipped sample in any channel are
left out (a highlight clipped in green but not in red has a different shape in
each, which reads as displacement), and tile weights are capped at the median
so that a few bright tiles cannot steer the fit.

Stage 1, model: d = eps * (x - c) + d0 per channel (a magnification error
about the frame centre plus an offset), Huber-fitted; coarse band first
(shifts of several photosites), then a fine band after resampling.
Stage 2, field (skipped with --model-only): what the model leaves is a
repeatable, spatially smooth displacement (the two independent halves agree
to a few hundredths of a photosite), so it is fitted as a free-form field:
tile residuals smoothed by normalised convolution (sigma 1.5 tiles). Its
honesty check is held-out: the field is built from one checkerboard half of
the tiles and the residual is scored on the other half.

Null: red against red shifted by a known 0.30 px.

Writes WORK_DIR/fused/OUT_ARM-{all,odd,even}.npy with red and blue resampled
once (dense Lanczos warp) and WORK_DIR/ca-ARM.json. --placebo applies red's
correction to blue and blue's to red.
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
import fp

work, arm, out_arm = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
placebo, model_only = '--placebo' in sys.argv, '--model-only' in sys.argv
H, W = 6336, 9504
T = 128
ty, tx = H // T, W // T
cx, cy = (W - 1) / 2, (H - 1) / 2
tcx = (np.arange(tx) + 0.5) * T - 0.5 - cx
tcy = (np.arange(ty) + 0.5) * T - 0.5 - cy
TX, TY = np.meshgrid(tcx, tcy)
CLIP = 0.80 * (15360.0 - 512.0)


def pool(v):
    return v[:ty * T, :tx * T].reshape(ty, T, tx, T).sum((1, 3)).double()


def tile_shift(c, g, lo, hi, mask):
    """Per-tile displacement of c's features relative to g's."""
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
    return d.cpu().numpy(), a.cpu().numpy(), lam.cpu().numpy(), resid.cpu().numpy(), used.cpu().numpy()


def valid(d, a, lam, resid, used, limit):
    return (a > 0.2) & (a < 5) & (lam > 0.05 * np.median(lam)) & (resid < 0.5) & (used > 0.5) & (np.abs(d).max(-1) < limit)


def fit(x, y, dx, dy):
    """Huber fit of d = eps (x, y) + d0. Returns params and residual vectors."""
    A = np.stack([np.concatenate([x, y]), np.concatenate([np.ones_like(x), np.zeros_like(x)]), np.concatenate([np.zeros_like(x), np.ones_like(x)])], 1)
    t = np.concatenate([dx, dy])
    hw = np.ones_like(t)
    for _ in range(10):
        sw = np.sqrt(hw)
        p = np.linalg.lstsq(A * sw[:, None], t * sw, rcond=None)[0]
        res = t - A @ p
        s = 1.4826 * np.median(np.abs(res)) + 1e-9
        hw = np.minimum(1.0, 2.0 * s / np.maximum(np.abs(res), 1e-12))
    return p


def smooth_field(d, ok, sigma=1.5):
    """Normalised convolution of tile vectors over valid tiles: [ty, tx, 2]."""
    w = torch.from_numpy(ok.astype(np.float32)).to(fp.DEV)
    out = []
    for i in range(2):
        v = torch.from_numpy(np.where(ok, d[..., i], 0.0).astype(np.float32)).to(fp.DEV)
        num, den = fp.gauss(v, sigma), fp.gauss(w, sigma)
        wide = fp.gauss(v, 6.0) / fp.gauss(w, 6.0).clamp(min=1e-6)
        t = den / (den + 0.05)
        out.append((t * num / den.clamp(min=1e-6) + (1 - t) * wide).cpu().numpy())
    return np.stack(out, -1)


def dense(field_tiles, p):
    """Full-resolution displacement (dx, dy) = model p + tile field."""
    f = torch.from_numpy(field_tiles.astype(np.float32)).to(fp.DEV).permute(2, 0, 1)[None]
    f = F.interpolate(F.pad(f, (1, 1, 1, 1), mode='replicate'), size=((ty + 2) * T, (tx + 2) * T), mode='bicubic', align_corners=False)[0]
    f = f[:, T:T + H, T:T + W]
    if f.shape[1] < H or f.shape[2] < W:
        f = F.pad(f[None], (0, W - f.shape[2], 0, H - f.shape[1]), mode='replicate')[0]
    xx = torch.arange(W, device=fp.DEV, dtype=torch.float32).view(1, -1) - cx
    yy = torch.arange(H, device=fp.DEV, dtype=torch.float32).view(-1, 1) - cy
    return f[0] + p[0] * xx + p[1], f[1] + p[0] * yy + p[2]


def rms(v):
    return float(np.sqrt((v ** 2).sum(-1).mean()))


x = torch.from_numpy(np.load(work / 'fused' / f'{arm}-all.npy')).to(fp.DEV)
g = x[1]
clipped = (x.max(0).values > CLIP).float()
mask = 1.0 - (F.max_pool2d(clipped[None, None], 25, 1, 12)[0, 0] > 0).float()
print('photosites kept after the clipping mask: %.1f%%' % (100 * float(mask.mean())))
report = {'arm': arm, 'tile_px': T}
models, fields = {}, {}
for c, name in ((0, 'red'), (2, 'blue')):
    rep = {}
    d, a, lam, resid, used = tile_shift(x[c], g, 4.0, 12.0, mask)
    ok = valid(d, a, lam, resid, used, 6.0)
    rep['uncorrected'] = {'tiles': int(ok.sum()), 'rms_px': rms(d[ok]), 'median_px': float(np.median(np.hypot(d[ok][:, 0], d[ok][:, 1])))}
    p = fit(TX[ok], TY[ok], d[ok][:, 0], d[ok][:, 1])
    zero = np.zeros((ty, tx, 2))
    for _ in range(3):
        ddx, ddy = dense(zero, p)
        ch = fp.warp_dense(x[c], ddx, ddy)
        d, a, lam, resid, used = tile_shift(ch, g, 1.5, 4.0, mask)
        ok = valid(d, a, lam, resid, used, 1.5)
        p = p + fit(TX[ok], TY[ok], d[ok][:, 0], d[ok][:, 1])
    ddx, ddy = dense(zero, p)
    ch = fp.warp_dense(x[c], ddx, ddy)
    d, a, lam, resid, used = tile_shift(ch, g, 1.5, 4.0, mask)
    ok = valid(d, a, lam, resid, used, 1.5)
    rep['model'] = {'eps_ppm': p[0] * 1e6, 'd0_px': [p[1], p[2]], 'corner_px': p[0] * 5711.0}
    rep['after_model'] = {'tiles': int(ok.sum()), 'rms_px': rms(d[ok]), 'median_px': float(np.median(np.hypot(d[ok][:, 0], d[ok][:, 1])))}
    print(f'{name}: uncorrected displacement rms {rep["uncorrected"]["rms_px"]:.3f} px over {rep["uncorrected"]["tiles"]} tiles; model eps {p[0] * 1e6:+.1f} ppm '
          f'({p[0] * 5711:+.2f} px at the corner), offset ({p[1]:+.3f}, {p[2]:+.3f}); after the model: rms {rep["after_model"]["rms_px"]:.3f} px', flush=True)
    field = zero
    if not model_only:
        # held-out score: field from one checkerboard half of the tiles, scored on the other
        iy, ix = np.indices(ok.shape)
        held = []
        for parity in (0, 1):
            build = ok & ((iy + ix) % 2 == parity)
            score = ok & ((iy + ix) % 2 != parity)
            f = smooth_field(d, build)
            held.append((d - f)[score])
        rep['field_held_out_rms_px'] = rms(np.concatenate(held))
        field = smooth_field(d, ok)
        ddx, ddy = dense(field, p)
        ch = fp.warp_dense(x[c], ddx, ddy)
        d2, a, lam, resid, used = tile_shift(ch, g, 1.5, 4.0, mask)
        ok2 = valid(d2, a, lam, resid, used, 1.5)
        rep['after_field'] = {'tiles': int(ok2.sum()), 'rms_px': rms(d2[ok2]), 'field_rms_px': rms(field[ok])}
        print(f'   free-form field: rms {rep["after_field"]["field_rms_px"]:.3f} px; held-out residual rms {rep["field_held_out_rms_px"]:.3f} px; '
              f'residual after applying it (same tiles, optimistic) {rep["after_field"]["rms_px"]:.3f} px', flush=True)
    models[c], fields[c] = p, field
    report[name] = rep
sh = fp.warp_scale_shift(x[0], 1.0, 0.30, 0.0)
d, a, lam, resid, used = tile_shift(sh, x[0], 1.5, 4.0, mask)
ok = (lam > 0.05 * np.median(lam)) & (used > 0.5)
report['null_shift_px'] = [float(np.median(d[ok][:, 0])), float(np.median(d[ok][:, 1]))]
print('null (red against red resampled 0.30 px in x; expect -0.30, 0):', [round(v, 4) for v in report['null_shift_px']])
(work / f'ca-{arm}.json').write_text(json.dumps(report, indent=1) + '\n')
del x, g
order = {0: 2, 2: 0} if placebo else {0: 0, 2: 2}
for name in ('all', 'odd', 'even'):
    y = torch.from_numpy(np.load(work / 'fused' / f'{arm}-{name}.npy')).to(fp.DEV)
    for c in (0, 2):
        ddx, ddy = dense(fields[order[c]], models[order[c]])
        y[c] = fp.warp_dense(y[c], ddx, ddy)
        del ddx, ddy
    np.save(work / 'fused' / f'{out_arm}-{name}.npy', y.cpu().numpy())
    del y
