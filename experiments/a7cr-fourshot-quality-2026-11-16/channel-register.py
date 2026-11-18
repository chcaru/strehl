"""R7: channel displacement left in one render (no half-stacks needed).

  python -X utf8 channel-register.py OUT.json IMG.tif [--apply OUT.tif] [--sign -1] [--tile 256] [--band LO,HI]

Use on renders whose channels carry independent noise (colour carried raw:
the chroma smoothing copies green's fine noise into red and blue and would
pull the estimate toward zero).

Per in-focus tile (top 30 % of green high-pass energy among tiles above the
15th percentile of level, clipped tiles dropped) and channel pair, the
displacement of channel c against green is the weighted least-squares phase
ramp of the cross-spectrum F_c conj(F_g) over 0.03-0.30 cycles/px (weights
|X|; --band changes the range, to ask whether the displacement is the same
at every scale), started from the phase-correlation peak (channel-shift.py's
estimator).

Model: displacement = t + eps * (position - centre), fitted on the tiles of
one checkerboard colour and scored on the other (rms of the residual
displacement; a model that only fits noise does not transfer).

--apply resamples red and blue by the fitted model (Lanczos-4, scale and
shift about the image centre) and writes the corrected image; --sign -1
applies the reversed model (placebo: must be worse).

Convention: shift s means channel c's content sits at position p + s where
green's sits at p. Correcting reads channel c at p + s.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def tile_select(g, T):
    H, W = g.shape
    hpe = (g - fp.gauss(g, 2.0)) ** 2
    ty, tx = H // T, W // T
    e = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    m = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    fg = m > np.percentile(m, 15)
    sel = (e >= np.percentile(e[fg], 70)) & fg
    sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
    return sel


def make_shift_of(T, dev, lo=0.03, hi=0.30):
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    fit = ((fr >= lo) & (fr <= hi)).double()

    def shift_of(X):
        """(sx, sy) with X ~ |X| exp(-2 pi i (fx sx + fy sy)); and the
        fraction of |X| that is coherent with that ramp."""
        r = torch.fft.ifft2(X * fit / (X.abs() + 1e-12 * X.abs().mean())).real
        idx = int(r.argmax())
        py, px = idx // T, idx % T
        sy0 = py - T if py > T / 2 else py
        sx0 = px - T if px > T / 2 else px
        s = torch.tensor([float(sx0), float(sy0)], dtype=torch.float64, device=dev)
        for _ in range(5):
            Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
            w = Y.abs() * fit
            ph = torch.angle(Y)
            a = torch.stack([(w * fx * fx).sum(), (w * fx * fy).sum(), (w * fy * fy).sum()])
            b = torch.stack([(w * fx * ph).sum(), (w * fy * ph).sum()])
            det = a[0] * a[2] - a[1] * a[1]
            dx = -(a[2] * b[0] - a[1] * b[1]) / det / (2 * np.pi)
            dy = -(a[0] * b[1] - a[1] * b[0]) / det / (2 * np.pi)
            s = s + torch.stack([dx, dy])
        Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
        coh = float((Y.real * fit).sum() / ((Y.abs() * fit).sum() + 1e-300))
        return s, coh

    return shift_of


def main():
    out, f = Path(sys.argv[1]), sys.argv[2]
    T = int(arg('--tile', '256'))
    sign = float(arg('--sign', '1'))
    dev = fp.DEV
    img = torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)
    _, H, W = img.shape
    sel = tile_select(img[1], T)
    clip = img.max(0).values > 60000
    clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
    sel &= ~clipt[:sel.shape[0], :sel.shape[1]]
    tiles = [(int(x), int(y)) for y, x in np.argwhere(sel)]
    win = ev.hann2(T, dev)
    lo, hi = (float(v) for v in arg('--band', '0.03,0.30').split(','))
    shift_of = make_shift_of(T, dev, lo, hi)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    pos = np.array([[x * T + T / 2 - cx, y * T + T / 2 - cy] for x, y in tiles])
    design = np.array([(x + y) % 2 == 0 for x, y in tiles])
    report = {'image': f, 'tiles': len(tiles), 'tile': T, 'pairs': {}}
    model = {}
    for c, label in ((0, 'R-G'), (2, 'B-G')):
        S, C = [], []
        for x, y in tiles:
            a = img[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
            a = a - a.mean((1, 2), keepdim=True)
            Fc, Fg = torch.fft.fft2(a[c] * win), torch.fft.fft2(a[1] * win)
            # F_c = F_g exp(-2 pi i f.s) when c sits at p + s
            s, coh = shift_of(Fc * Fg.conj())
            S.append(s.cpu().numpy())
            C.append(coh)
        S, C = np.array(S), np.array(C)

        def fit(mask):
            A = np.zeros((2 * mask.sum(), 3))
            A[0::2, 0] = 1
            A[1::2, 1] = 1
            A[0::2, 2] = pos[mask, 0]
            A[1::2, 2] = pos[mask, 1]
            w = np.repeat(C[mask].clip(0.05), 2)
            sol, *_ = np.linalg.lstsq(A * w[:, None], S[mask].reshape(-1) * w, rcond=None)
            return sol

        def resid(sol, mask):
            pred = np.stack([sol[0] + sol[2] * pos[mask, 0], sol[1] + sol[2] * pos[mask, 1]], 1)
            return S[mask] - pred

        sol_d = fit(design)
        sol_all = fit(np.ones(len(tiles), bool))
        r_val = resid(sol_d, ~design)
        rms = lambda v: float(np.sqrt((v ** 2).sum(1).mean()))
        med = lambda v: float(np.median(np.hypot(v[:, 0], v[:, 1])))
        report['pairs'][label] = {
            'mean': S.mean(0).tolist(), 'rms': rms(S), 'median': med(S),
            'fit_design': sol_d.tolist(), 'fit_all': sol_all.tolist(),
            'validation_rms_before': rms(S[~design]), 'validation_rms_after': rms(r_val),
            'validation_median_before': med(S[~design]), 'validation_median_after': med(r_val),
            'coherence_median': float(np.median(C)), 'shifts': S.tolist()}
        model[c] = sol_all
        print(f'{label}: {len(tiles)} tiles, displacement mean ({S[:, 0].mean():+.3f}, {S[:, 1].mean():+.3f}) px, '
              f'rms {rms(S):.3f}, median {med(S):.3f}; fit t=({sol_all[0]:+.3f}, {sol_all[1]:+.3f}) eps={sol_all[2] * 1e6:+.1f} ppm; '
              f'validation rms {rms(S[~design]):.3f} -> {rms(r_val):.3f}, median {med(S[~design]):.3f} -> {med(r_val):.3f} '
              f'(design-half fit t=({sol_d[0]:+.3f}, {sol_d[1]:+.3f}) eps={sol_d[2] * 1e6:+.1f}); phase coherence median {np.median(C):.2f}')
    report['positions'] = pos.tolist()
    out.write_text(json.dumps(report) + '\n')
    dst = arg('--apply')
    if dst:
        res = img.clone()
        for c, sol in model.items():
            tx, ty, eps = sign * sol[0], sign * sol[1], sign * sol[2]
            res[c] = fp.warp_scale_shift(img[c], 1.0 + eps, tx, ty)
        tifffile.imwrite(dst, res.clamp(0, 65535).round().permute(1, 2, 0).cpu().numpy().astype(np.uint16))
        print('wrote', dst, 'sign', sign)


if __name__ == '__main__':
    with torch.no_grad():
        main()
