"""Q5: where in frequency does an arm lose or gain signal against a base arm?

  python -X utf8 radial-ratio.py OUT.json BASE=odd.tif,even.tif ARM=odd.tif,even.tif [...]

Tiles as cross-channel.py, selected on the base arm. Per arm and channel the
radial cross-half signal S(f) and noise N(f) in 0.0125 cycles/px bins.
Printed: amplitude ratio sqrt(S_arm / S_base) and noise amplitude ratio by
frequency, green (and all channels in the JSON).

The carried merge works on half-resolution site planes, so a plane-domain
pyramid level k passes output frequencies near every multiple of 0.5
cycles/px: output detail above 0.375 cycles/px sits in plane level 1 and
above 0.4375 in level 2, with their weights. A merge whose weights differ by
level therefore shows steps at 0.375 and 0.4375 in this ratio; a smooth
filter (the restoration control) does not.
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
BIN = 0.0125
NB = int(0.72 / BIN)


def main():
    out = Path(sys.argv[1])
    arms = []
    for a in sys.argv[2:]:
        name, files = a.split('=', 1)
        arms.append((name, files.split(',')))
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)

    A, B = load(arms[0][1][0]), load(arms[0][1][1])
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

    def radial(x):
        acc = torch.zeros(NB, dtype=torch.float64, device=dev)
        acc.scatter_add_(0, bins, x.flatten())
        return acc / count

    def measure(A, B):
        S = torch.zeros(3, NB, dtype=torch.float64, device=dev)
        N = torch.zeros_like(S)
        for x, y in tiles:
            a = A[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
            b = B[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
            a = a - a.mean((1, 2), keepdim=True)
            b = b - b.mean((1, 2), keepdim=True)
            FA, FB = torch.fft.fft2(a * win), torch.fft.fft2(b * win)
            _, _, (sx, sy) = ev.pair_spectra(a[1], b[1], win)
            FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
            for c in range(3):
                s = (FA[c] * FB[c].conj()).real / norm
                S[c] += radial(s)
                N[c] += radial((FA[c].abs() ** 2 + FB[c].abs() ** 2) / (2 * norm) - s)
        return (S / len(tiles)).cpu().numpy(), (N / len(tiles)).cpu().numpy()

    res = {arms[0][0]: measure(A, B)}
    del A, B
    for name, files in arms[1:]:
        a, b = load(files[0]), load(files[1])
        res[name] = measure(a, b)
        del a, b
    centres = (np.arange(NB) + 0.5) * BIN
    report = {'tiles': len(tiles), 'centres': centres.tolist(), 'arms': {k: {'S': v[0].tolist(), 'N': v[1].tolist()} for k, v in res.items()}}
    S0, N0 = res[arms[0][0]]
    show = [i for i in range(NB) if 0.05 <= centres[i] <= 0.50]
    print('f (cycles/px)      ' + ' '.join(f'{centres[i]:.3f}' for i in show))
    for name, (S, N) in res.items():
        if name == arms[0][0]:
            continue
        for c in (1,):
            print(f'{name:14s} {"RGB"[c]} sig ' + ' '.join(f'{np.sqrt(max(S[c][i], 0) / S0[c][i]):.3f}' for i in show))
            print(f'{name:14s} {"RGB"[c]} noi ' + ' '.join(f'{np.sqrt(N[c][i] / N0[c][i]):.3f}' for i in show))
            print(f'{name:14s} {"RGB"[c]} snr ' + ' '.join(f'{(S[c][i] / N[c][i]) / (S0[c][i] / N0[c][i]):.3f}' for i in show))
    out.write_text(json.dumps(report) + '\n')


if __name__ == '__main__':
    with torch.no_grad():
        main()
