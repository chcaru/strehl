"""Q1 follow-up: is the low fine-scale coherence between colour channels a
displacement between them?

  python -X utf8 channel-shift.py OUT.json ODD.tif EVEN.tif [--band LO,HI]

--band (round 2) sets the frequency range the phase ramp is fitted over
(default 0.03-0.30, where |X| weights make coarse content dominate).

Per in-focus tile (cross-channel.py's selection) and channel pair, the
cross-half cross-spectrum X = A_c conj(B_d) + B_c conj(A_d) (noise is
independent between halves, so it cancels in the mean). The displacement of
c against d is the weighted least-squares phase ramp of X over 0.03-0.30
cycles/px (weights |X|), started from the phase-correlation peak. Reported:
the displacement field's statistics, and the radial coherence
Re <X ramp> / sqrt(S_cc S_dd) with (a) nothing removed, (b) the mean
displacement removed, (c) an offset-plus-radial model removed, (d) each
tile's own displacement removed, (e) a displacement rolled to another tile
removed (placebo: must not help).

Fooled by: a blur difference between channels changes |X| but not this
coherence; a phase ramp fitted to noise would inflate (d), which the placebo
(e) bounds.
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

T = ev.T
BIN, NB = 0.01, 72


def main():
    out, fa, fb = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    A, B = load(fa), load(fb)
    _, H, W = A.shape
    g = A[1]
    hpe = (g - fp.gauss(g, 2.0)) ** 2
    ty, tx = H // T, W // T
    e = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    m = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
    fg = m > np.percentile(m, 15)
    sel = (e >= np.percentile(e[fg], 70)) & fg
    sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
    clip = (A.max(0).values > 60000) | (B.max(0).values > 60000)
    clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
    sel &= ~clipt[:ty, :tx]
    tiles = [(int(x), int(y)) for y, x in np.argwhere(sel)]
    win = ev.hann2(T, dev)
    norm = T * T * float((win * win).sum())
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    bins = torch.clamp((fr / BIN).long(), max=NB - 1).flatten()
    count = torch.bincount(bins, minlength=NB).double().clamp(min=1)
    lo, hi = (float(v) for v in (sys.argv[sys.argv.index('--band') + 1].split(',') if '--band' in sys.argv else ('0.03', '0.30')))
    fit = ((fr >= lo) & (fr <= hi)).double()

    def radial(x):
        acc = torch.zeros(NB, dtype=x.dtype, device=dev)
        acc.scatter_add_(0, bins, x.flatten())
        return acc / count

    def shift_of(X):
        """Displacement (sx, sy) with X ~ |X| exp(-2 pi i (fx sx + fy sy))."""
        r = torch.fft.ifft2(X * fit / (X.abs() + 1e-12 * X.abs().mean())).real
        idx = int(r.argmax())
        py, px = idx // T, idx % T
        sy0 = py - T if py > T / 2 else py
        sx0 = px - T if px > T / 2 else px
        s = torch.tensor([float(sx0), float(sy0)], dtype=torch.float64, device=dev)
        for _ in range(4):
            Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
            w = Y.abs() * fit
            ph = torch.angle(Y)
            # ph ~ -2 pi (fx dx + fy dy)
            a = torch.stack([(w * fx * fx).sum(), (w * fx * fy).sum(), (w * fy * fy).sum()])
            b = torch.stack([(w * fx * ph).sum(), (w * fy * ph).sum()])
            det = a[0] * a[2] - a[1] * a[1]
            dx = -(a[2] * b[0] - a[1] * b[1]) / det / (2 * np.pi)
            dy = -(a[0] * b[1] - a[1] * b[0]) / det / (2 * np.pi)
            s = s + torch.stack([dx, dy])
        return s

    pairs = ((0, 1, 'R-G'), (2, 1, 'B-G'), (0, 2, 'R-B'))
    X = {p[2]: [] for p in pairs}
    auto = [torch.zeros(NB, dtype=torch.float64, device=dev) for _ in range(3)]
    for x, y in tiles:
        a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        a = a - a.mean((1, 2), keepdim=True)
        b = b - b.mean((1, 2), keepdim=True)
        FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
        _, _, (sx, sy) = ev.pair_spectra(a[1], b[1], win)
        FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
        for c in range(3):
            auto[c] += radial((FA[c] * FB[c].conj()).real) / norm
        for c, d, label in pairs:
            X[label].append(0.5 * (FA[c] * FB[d].conj() + FB[c] * FA[d].conj()) / norm)
    report = {'tiles': tiles, 'pairs': {}}
    q = [int(v / BIN) for v in (0.05, 0.15, 0.25, 0.30, 0.35, 0.40, 0.45)]
    cx, cy = (W - 1) / 2, (H - 1) / 2
    pos = np.array([[x * T + T / 2 - cx, y * T + T / 2 - cy] for x, y in tiles])
    for c, d, label in pairs:
        shifts = torch.stack([shift_of(x) for x in X[label]])
        den = torch.sqrt((auto[c] * auto[d]).clamp(min=1e-300))

        def coh(sh):
            acc = torch.zeros(NB, dtype=torch.float64, device=dev)
            for x, s in zip(X[label], sh):
                acc += radial((x * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))).real)
            return (acc / den).cpu().numpy()

        none = coh(torch.zeros_like(shifts))
        own = coh(shifts)
        placebo = coh(torch.roll(shifts, 7, 0))
        mean_only = coh(shifts.mean(0, keepdim=True).expand_as(shifts))
        s = shifts.cpu().numpy()
        # offset-plus-radial model: shift = t + eps * pos
        Amat = np.zeros((2 * len(tiles), 3))
        Amat[0::2, 0] = 1
        Amat[1::2, 1] = 1
        Amat[0::2, 2] = pos[:, 0]
        Amat[1::2, 2] = pos[:, 1]
        sol, *_ = np.linalg.lstsq(Amat, s.reshape(-1), rcond=None)
        resid = (s.reshape(-1) - Amat @ sol).reshape(-1, 2)
        modelled = coh(torch.tensor((Amat @ sol).reshape(-1, 2), dtype=torch.float64, device=dev))
        report['pairs'][label] = {
            'shifts': s.tolist(), 'mean': s.mean(0).tolist(), 'rms': float(np.sqrt((s ** 2).sum(1).mean())),
            'radial_fit': sol.tolist(), 'residual_rms': float(np.sqrt((resid ** 2).sum(1).mean())),
            'coherence_none': none.tolist(), 'coherence_own': own.tolist(), 'coherence_placebo': placebo.tolist(),
            'coherence_mean_only': mean_only.tolist(), 'coherence_model': modelled.tolist()}
        print(f'{label}: displacement mean ({s[:, 0].mean():+.3f}, {s[:, 1].mean():+.3f}) px, rms {np.sqrt((s ** 2).sum(1).mean()):.3f} px; '
              f'offset + radial fit t=({sol[0]:+.3f}, {sol[1]:+.3f}) eps={sol[2] * 1e6:+.0f} ppm leaves '
              f'{np.sqrt((resid ** 2).sum(1).mean()):.3f} px rms')
        for name, v in (('nothing removed', none), ('mean removed', mean_only), ('offset+radial removed', modelled),
                        ('own removed', own), ('placebo (rolled)', placebo)):
            print(f'   coherence, {name:22s}: ' + ' '.join(f'{v[i]:.3f}' for i in q))
    print('   at 0.05 0.15 0.25 0.30 0.35 0.40 0.45 cycles/px')
    out.write_text(json.dumps(report) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
