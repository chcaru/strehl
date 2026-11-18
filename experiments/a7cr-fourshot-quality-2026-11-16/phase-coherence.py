"""R4 follow-up: frames on opposite sides of a point's focus do not add
coherently under positive weights (series-focus.py, point-focus.py: the
pair products fall well below the product of the frames' own amplitudes).
Is that a smooth phase difference between their transfers (optics: a
frequency-domain merge with complex weights could undo it), or different
content (nothing linear can)?

  python -X utf8 phase-coherence.py OUT.json SERIES_DIR SERIES_FOCUS.npz [--max-tiles 160] [--cell 8]

Tiles and their focus frames k0 come from series-focus.py's npz (256 px
tiles). Frames are registered to k0 by the green phase ramp, as there. For a
lag L, frames a = k0 - L/2 and b = k0 + L/2, and the neighbouring pair
(a + 1, b + 1), whose noise is independent of the first pair's. The
frequency plane is cut into cells of `cell` x `cell` bins. Per cell:

  C1 = sum F_a conj F_b,   C2 = sum F_{a+1} conj F_{b+1}      (complex)
  Sa = sum Re(F_a conj F_{a+1}),  Sb = sum Re(F_b conj F_{b+1})   (noise-free powers)

Per radial band, summed over its cells and over tiles:

  plain  = sum Re C1 * sum Re C2 / (sum sqrt(Sa Sb))^2
           what a real, positive-weight average of the two frames keeps of
           the product of their amplitudes (squared coherence), cells added
           with their signs
  cells  = sum Re(C1 conj C2) / sum (Sa Sb)
           the same with each cell's own phase removed: 1 if the two frames
           are one image passed through transfers whose phase difference is
           smooth over a cell; unchanged from `plain` if their content
           simply differs

Controls: lag 0 is not defined (same noise); lag 2 must read near 1 in both;
the placebo pairs frame b with frame a of a different tile (must read 0 in
both).

Fooled by: a phase difference that varies inside a cell (reads low in both:
a smaller cell tests it, at more noise); C1 and C2 differ by one frame of
focus, so a transfer that changes quickly from frame to frame reads low.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp

BANDS = [(0.06, 0.10), (0.10, 0.16), (0.16, 0.24), (0.24, 0.32), (0.32, 0.42)]
LAGS = [2, 4, 6, 8, 12]


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
    return default


def main():
    out, sdir, npz = Path(sys.argv[1]), Path(sys.argv[2]), np.load(sys.argv[3])
    max_tiles, cell = int(arg('--max-tiles', '160')), int(arg('--cell', '8'))
    dev = fp.DEV
    T, S, half = 256, 128, 8
    sel, k0 = npz['sel'], npz['k0']
    keep = np.linspace(0, len(sel) - 1, min(max_tiles, len(sel))).astype(int)
    sel, k0 = sel[keep], k0[keep]
    n = len(sel)
    nw = 2 * half + 1
    stack = torch.zeros(n, nw, T, T, dtype=torch.float32)
    for k in range(int(k0.min()) - half, int(k0.max()) + half + 1):
        g = torch.from_numpy(tifffile.imread(sdir / f'one-{k}.tif')[..., 1].astype(np.float32))
        for i, (ty, tx) in enumerate(sel):
            j = k - (int(k0[i]) - half)
            if 0 <= j < nw:
                stack[i, j] = g[ty * S:ty * S + T, tx * S:tx * S + T]
    win = torch.hann_window(T, periodic=True, device=dev)
    win = win[:, None] * win[None, :]
    fy = torch.fft.fftfreq(T, device=dev)[:, None]
    fx = torch.fft.fftfreq(T, device=dev)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    fitm = ((fr >= 0.03) & (fr <= 0.30)).float()
    nc = T // cell
    # cell-pooled radial frequency (cells are blocks of the fftshifted plane)
    frc = torch.fft.fftshift(fr).reshape(nc, cell, nc, cell).mean((1, 3))
    cmask = [((frc >= lo) & (frc < hi)) for lo, hi in BANDS]

    def cells(X):
        return torch.fft.fftshift(X).reshape(nc, cell, nc, cell).sum((1, 3))

    def shift_of(X):
        r = torch.fft.ifft2(X * fitm / (X.abs() + 1e-12 * X.abs().mean())).real
        idx = int(r.argmax())
        py, px = idx // T, idx % T
        s = torch.tensor([float(px - T if px > T / 2 else px), float(py - T if py > T / 2 else py)], device=dev)
        for _ in range(5):
            Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
            wgt = Y.abs() * fitm
            ph = torch.angle(Y)
            a = torch.stack([(wgt * fx * fx).sum(), (wgt * fx * fy).sum(), (wgt * fy * fy).sum()])
            b = torch.stack([(wgt * fx * ph).sum(), (wgt * fy * ph).sum()])
            det = a[0] * a[2] - a[1] * a[1]
            s = s + torch.stack([-(a[2] * b[0] - a[1] * b[1]) / det, -(a[0] * b[1] - a[1] * b[0]) / det]) / (2 * np.pi)
        return s

    Fall = []
    for i in range(n):
        x = stack[i].to(dev)
        Fw = torch.fft.fft2((x - x.mean((-2, -1), keepdim=True)) * win)
        for j in range(nw):
            if j != half:
                s = shift_of(Fw[j] * Fw[half].conj())
                Fw[j] = Fw[j] * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
        Fall.append(Fw.to(torch.complex64).cpu())
    acc = {(arm, L, b): np.zeros(5) for arm in ('real', 'placebo') for L in LAGS for b in range(len(BANDS))}
    for i in range(n):
        Fi = Fall[i].to(dev)
        Fo = Fall[(i + 17) % n].to(dev)
        for L in LAGS:
            a, b = half - L // 2, half + L // 2
            if b + 1 >= nw:
                a, b = a - 1, b - 1
            for arm, Fa in (('real', Fi), ('placebo', Fo)):
                C1 = cells(Fa[a] * Fi[b].conj())
                C2 = cells(Fa[a + 1] * Fi[b + 1].conj())
                Sa = cells((Fa[a] * Fa[a + 1].conj()).real.to(torch.complex64)).real.clamp(min=0)
                Sb = cells((Fi[b] * Fi[b + 1].conj()).real.to(torch.complex64)).real.clamp(min=0)
                for bi, m in enumerate(cmask):
                    v = acc[(arm, L, bi)]
                    v[0] += float(C1.real[m].sum())
                    v[1] += float(C2.real[m].sum())
                    v[2] += float(torch.sqrt(Sa * Sb)[m].sum())
                    v[3] += float((C1 * C2.conj()).real[m].sum())
                    v[4] += float((Sa * Sb)[m].sum())
    report = {'tiles': int(n), 'cell_bins': cell, 'lags': LAGS, 'bands': BANDS, 'results': {}}
    print(f'{n} tiles, cells of {cell} x {cell} bins ({cell / T:.4f} cycles/px)')
    for arm in ('real', 'placebo'):
        for bi, (lo, hi) in enumerate(BANDS):
            row = []
            for L in LAGS:
                v = acc[(arm, L, bi)]
                plain = v[0] * v[1] / max(v[2] ** 2, 1e-30)
                cel = v[3] / max(v[4], 1e-30)
                row.append((plain, cel))
                report['results'][f'{arm} {lo}-{hi} lag {L}'] = {'plain': plain, 'cells': cel}
            print(f'{arm:8s} band {lo:.2f}-{hi:.2f}: ' + '  '.join(f'lag {L}: plain {p:+.2f}, cells {c:+.2f}' for L, (p, c) in zip(LAGS, row)))
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
