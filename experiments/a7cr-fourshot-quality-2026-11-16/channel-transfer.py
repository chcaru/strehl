"""R10 follow-up: red's and blue's transfer relative to green's, measured on
a neutral target (the black-on-clear slide of the calibration captures).

  python -X utf8 channel-transfer.py OUT.json A.tif B.tif [--top 0.3]

A and B are two renders of the same static target with independent noise
(the 1.6 s and the 0.6 s series). On a neutral target every channel images
the same structure, so for in-focus tiles (top share of green high-pass
energy) the ratio

    T_c(f) = Re S_cG(f) / S_GG(f)        (cross-render spectra: noise cancels)

normalised to its value at 0.02-0.05 cycles/px is channel c's transfer
relative to green's, registration error included (use renders whose channel
registration has been repaired: leak-fix.py --write). Also printed: the
magnitude version sqrt(S_cc / S_GG), which ignores registration.

Compared with what the restoration assumes: diffraction at the channel's
nominal wavelength over diffraction at green's, with the cutoffs it fitted
on the scarab (0.546 / 0.612 / 0.704 cycles/px).

Fooled by: a target that is not neutral at fine scale (chrome edges are);
tiles out of focus for one channel only (axial colour: that is part of what
is being measured); the illuminant differs from the stack's.
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
EDGES = [0.02, 0.05, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
CUT = {'R': 0.546, 'G': 0.612, 'B': 0.704}


def diffraction(f, fc):
    v = np.clip(np.asarray(f) / fc, 0, 1)
    return (2 / np.pi) * (np.arccos(v) - v * np.sqrt(1 - v * v))


def main():
    out, fa, fb = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    top = float(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 0.3
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
    rel = e / np.maximum(m, 1) ** 2
    sel = rel >= np.quantile(rel, 1 - top)
    sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
    clip = (A.max(0).values > 60000) | (B.max(0).values > 60000)
    clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
    sel &= ~clipt[:ty, :tx]
    tiles = [(int(x), int(y)) for y, x in np.argwhere(sel)]
    win = ev.hann2(T, dev)
    fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
    fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
    fr = torch.sqrt(fx * fx + fy * fy)
    masks = [((fr >= lo) & (fr < hi)).double() for lo, hi in zip(EDGES[:-1], EDGES[1:])]
    acc = {k: np.zeros(len(masks)) for k in ('gg', 'rg', 'bg', 'rr', 'bb')}
    for x, y in tiles:
        a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        a = a - a.mean((1, 2), keepdim=True)
        b = b - b.mean((1, 2), keepdim=True)
        FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
        _, _, (sx, sy) = ev.pair_spectra(a[1], b[1], win)
        FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
        # per-tile level normalisation so bright tiles do not dominate
        nrm = float((FA[1] * FB[1].conj()).real.sum().abs()) + 1e-30
        for i, mk in enumerate(masks):
            acc['gg'][i] += float(((FA[1] * FB[1].conj()).real * mk).sum()) / nrm
            acc['rg'][i] += float((0.5 * (FA[0] * FB[1].conj() + FB[0] * FA[1].conj()).real * mk).sum()) / nrm
            acc['bg'][i] += float((0.5 * (FA[2] * FB[1].conj() + FB[2] * FA[1].conj()).real * mk).sum()) / nrm
            acc['rr'][i] += float(((FA[0] * FB[0].conj()).real * mk).sum()) / nrm
            acc['bb'][i] += float(((FA[2] * FB[2].conj()).real * mk).sum()) / nrm
    centres = [0.5 * (lo + hi) for lo, hi in zip(EDGES[:-1], EDGES[1:])]
    report = {'tiles': len(tiles), 'centres': centres, 'channels': {}}
    print(f'{len(tiles)} tiles; cycles/px: ' + ' '.join(f'{c:.3f}' for c in centres))
    for name, key, own in (('R', 'rg', 'rr'), ('B', 'bg', 'bb')):
        t = acc[key] / acc['gg']
        mag = np.sqrt(np.clip(acc[own] / acc['gg'], 0, None))
        model = diffraction(centres, CUT[name]) / diffraction(centres, CUT['G'])
        report['channels'][name] = {'transfer_vs_green': (t / t[0]).tolist(), 'magnitude_vs_green': (mag / mag[0]).tolist(), 'restoration_model': (model / model[0]).tolist()}
        print(f'{name} transfer relative to green (cross, registration included): ' + ' '.join(f'{v:.3f}' for v in t / t[0]))
        print(f'{name} amplitude relative to green (magnitude only):               ' + ' '.join(f'{v:.3f}' for v in mag / mag[0]))
        print(f'{name} what diffraction at the fitted cutoffs predicts:            ' + ' '.join(f'{v:.3f}' for v in model / model[0]))
    out.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
