"""R7: is the fine detail that red and blue share with green a green-band
component of those channels (spectral overlap of the colour filters), which
the lateral-colour correction moves with the rest of the channel?

  python -X utf8 leak-fix.py OUT.json ODD.tif EVEN.tif [--eps-r 428e-6] [--eps-b -172e-6]
        [--a-r LIST] [--a-b LIST] [--delta-r LIST] [--delta-b LIST] [--t-r X,Y] [--t-b X,Y] [--write PREFIX]

--t-r / --t-b: a translation of the own band (px, as measured against
green), applied with delta. The own band can sit off green by a uniform
offset as well as a scale (blue does, by a quarter of a pixel in y on the
scarab); the green-band share does not.

Model: a carried channel is its own band plus a share `a` of the green
band, C_raw = C_own + a G. The gather resamples the whole channel by the
lens profile's scale. That displaces the a G part, which in the merged image
sits at G(c + (q - c)(1 - eps)), eps being the fine-band displacement
measured by channel-shift.py --band 0.24,0.42; and it may be the wrong scale
for C_own, since the profile was fitted to the mixture. The merge applies
one set of weights to every plane, so the repair commutes with it and can be
made on the finished image:

    C_fixed = warp(C - a warp(G, 1 - eps), 1 + delta) + a G

delta is the extra radial scale the own band needs (0 keeps the profile's).
LISTs are comma-separated; every combination of a and delta is scored
(default: delta 0 and a sweep of a). Per arm, from cross-half spectra (noise
is independent between halves and cancels):
  - the radial displacement of C_fixed against G fitted per band (offset +
    radial over in-focus tiles), and the rms displacement over tiles; the
    right a nulls it in the fine band, the right delta in the coarse band;
  - coherence of C_fixed with G by band;
  - power of the colour difference C_fixed - G that the halves share, and of
    C_fixed itself, by band, relative to the unrepaired image.

Placebo: the same repair with eps reversed (the share moved the wrong way)
must make the fine-band displacement larger, not smaller.

Fooled by: C_own's fine detail, if any is shared with green at another
displacement, biases the nulling a; a blur difference between channels does
not move a phase ramp; the second warp (delta) costs the own band a little
fine detail (Lanczos-4), visible in the channel-power column.
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
BANDS = [(0.03, 0.08), (0.11, 0.18), (0.24, 0.42)]
PBANDS = [(0.05, 0.10), (0.10, 0.25), (0.25, 0.40)]


def arg(name, default=None):
    for i, tok in enumerate(sys.argv):
        if tok == name:
            return sys.argv[i + 1]
        if tok.startswith(name + '='):
            return tok.split('=', 1)[1]
    return default


def floats(text):
    return [float(v) for v in text.split(',')]


def repair(img, c, a, eps, delta, t=(0.0, 0.0)):
    """C_fixed for channel c of [3, H, W]. `t` is an own-band translation
    (px, the measured offset of the own band against green; read at p + t)."""
    own = img[c] - a * fp.warp_scale_shift(img[1], 1.0 - eps, 0.0, 0.0)
    if delta != 0.0 or t[0] != 0.0 or t[1] != 0.0:
        own = fp.warp_scale_shift(own, 1.0 + delta, t[0], t[1])
    return own + a * img[1]


def main():
    out, fa, fb = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    eps = {0: float(arg('--eps-r', '428e-6')), 2: float(arg('--eps-b', '-172e-6'))}
    shares = {0: floats(arg('--a-r', '0,0.1,0.2,0.3,0.4,0.5,0.6')), 2: floats(arg('--a-b', '0,0.1,0.2,0.3,0.4,0.5,0.6'))}
    deltas = {0: floats(arg('--delta-r', '0')), 2: floats(arg('--delta-b', '0'))}
    trans = {0: tuple(floats(arg('--t-r', '0,0'))), 2: tuple(floats(arg('--t-b', '0,0')))}
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
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    cx, cy = (W - 1) / 2, (H - 1) / 2
    pos = np.array([[x * T + T / 2 - cx, y * T + T / 2 - cy] for x, y in tiles])

    def tile_fft(img):
        res = []
        for x, y in tiles:
            a = img[y * T:(y + 1) * T, x * T:(x + 1) * T].double()
            res.append(torch.fft.fft2((a - a.mean()) * win))
        return torch.stack(res)

    def shift_of(X, fit):
        r = torch.fft.ifft2(X * fit / (X.abs() + 1e-12 * X.abs().mean())).real
        idx = int(r.argmax())
        py, px = idx // T, idx % T
        s = torch.tensor([float(px - T if px > T / 2 else px), float(py - T if py > T / 2 else py)],
                         dtype=torch.float64, device=dev)
        for _ in range(5):
            Y = X * torch.exp(2j * np.pi * (fx * s[0] + fy * s[1]))
            w = Y.abs() * fit
            ph = torch.angle(Y)
            a = torch.stack([(w * fx * fx).sum(), (w * fx * fy).sum(), (w * fy * fy).sum()])
            b = torch.stack([(w * fx * ph).sum(), (w * fy * ph).sum()])
            det = a[0] * a[2] - a[1] * a[1]
            s = s + torch.stack([-(a[2] * b[0] - a[1] * b[1]) / det, -(a[0] * b[1] - a[1] * b[0]) / det]) / (2 * np.pi)
        return s.cpu().numpy()

    def radial_eps(S):
        Am = np.zeros((2 * len(tiles), 3))
        Am[0::2, 0] = 1
        Am[1::2, 1] = 1
        Am[0::2, 2] = pos[:, 0]
        Am[1::2, 2] = pos[:, 1]
        sol, *_ = np.linalg.lstsq(Am, S.reshape(-1), rcond=None)
        return sol

    # the halves' registration to each other, from green (as evaluate.py does)
    GA, GB = tile_fft(A[1]), tile_fft(B[1])
    reg = []
    for x, y in tiles:
        a = A[1, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[1, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        _, _, (sx, sy) = ev.pair_spectra(a - a.mean(), b - b.mean(), win)
        reg.append(torch.exp(2j * np.pi * (fx * sx + fy * sy)))
    reg = torch.stack(reg)
    GB = GB * reg
    Sgg = (GA * GB.conj()).real
    report = {'tiles': len(tiles), 'eps': {'R': eps[0], 'B': eps[2]}, 'channels': {}}

    def score(CA, CB, base):
        X = 0.5 * (CA * GB.conj() + CB * GA.conj())
        Scc = (CA * CB.conj()).real
        Sdd = ((CA - GA) * (CB - GB).conj()).real
        row = {}
        for lo, hi in BANDS:
            fit = ((fr >= lo) & (fr <= hi)).double()
            S = np.array([shift_of(X[i], fit) for i in range(len(tiles))])
            sol = radial_eps(S)
            row[f'eps {lo}-{hi}'] = float(sol[2] * 1e6)
            row[f't {lo}-{hi}'] = [float(sol[0]), float(sol[1])]
            row[f'rms {lo}-{hi}'] = float(np.sqrt((S ** 2).sum(1).mean()))
        for lo, hi in PBANDS:
            mk = ((fr >= lo) & (fr < hi)).double()
            row[f'coh {lo}-{hi}'] = float((X.real * mk).sum() / torch.sqrt((Scc * mk).sum() * (Sgg * mk).sum()))
            row[f'diff {lo}-{hi}'] = float((Sdd * mk).sum())
            row[f'own {lo}-{hi}'] = float((Scc * mk).sum())
        b = base or row
        text = ('eps coarse/mid/fine ' + ' / '.join(f"{row[f'eps {lo}-{hi}']:+5.0f}" for lo, hi in BANDS) + ' ppm; rms px '
                + ' / '.join(f"{row[f'rms {lo}-{hi}']:.2f}" for lo, hi in BANDS) + '; coherence '
                + ' / '.join(f"{row[f'coh {lo}-{hi}']:.3f}" for lo, hi in PBANDS) + '; colour-difference power x'
                + ' / '.join(f"{row[f'diff {lo}-{hi}'] / b[f'diff {lo}-{hi}']:.3f}" for lo, hi in PBANDS)
                + '; channel power x' + ' / '.join(f"{row[f'own {lo}-{hi}'] / b[f'own {lo}-{hi}']:.3f}" for lo, hi in PBANDS))
        return row, text

    for c, label in ((0, 'R'), (2, 'B')):
        base, text = score(tile_fft(A[c]), tile_fft(B[c]) * reg, None)
        print(f'{label} as rendered           : {text}')
        print(f'          offsets coarse / mid / fine, px: ' + ' / '.join(f"({base[f't {lo}-{hi}'][0]:+.3f}, {base[f't {lo}-{hi}'][1]:+.3f})" for lo, hi in BANDS))
        rows = [dict(base, a=0.0, delta=0.0, arm='as rendered')]
        arms = [('model', a, d, 1.0) for d in deltas[c] for a in shares[c] if not (a == 0.0 and d == 0.0)]
        arms.append(('placebo (eps reversed)', 0.3, 0.0, -1.0))
        for name, a, d, sgn in arms:
            tt = trans[c] if sgn > 0 else (0.0, 0.0)
            row, text = score(tile_fft(repair(A, c, a, sgn * eps[c], d, tt)), tile_fft(repair(B, c, a, sgn * eps[c], d, tt)) * reg, base)
            rows.append(dict(row, a=a, delta=d, arm=name))
            print(f'{label} {name[:7]:7s} a={a:.2f} d={d * 1e6:+5.0f}: {text}')
            print(f'          offsets coarse / mid / fine, px: ' + ' / '.join(f"({row[f't {lo}-{hi}'][0]:+.3f}, {row[f't {lo}-{hi}'][1]:+.3f})" for lo, hi in BANDS))
        report['channels'][label] = rows
    out.write_text(json.dumps(report, indent=1) + '\n')
    prefix = arg('--write')
    if prefix:
        for tag, img in (('odd', A), ('even', B)):
            res = img.clone()
            for c in (0, 2):
                res[c] = repair(img, c, shares[c][-1], eps[c], deltas[c][-1], trans[c])
            tifffile.imwrite(f'{prefix}-{tag}.tif', res.clamp(0, 65535).round().permute(1, 2, 0).cpu().numpy().astype(np.uint16))
            print('wrote', f'{prefix}-{tag}.tif', 'a', shares[0][-1], shares[2][-1], 'delta', deltas[0][-1], deltas[2][-1])


if __name__ == '__main__':
    with torch.no_grad():
        main()
