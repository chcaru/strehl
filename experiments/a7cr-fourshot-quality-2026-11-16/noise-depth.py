"""Q2: how many groups' worth of noise averaging does a merge reach on the
smooth bright tiles where the sensor pattern was measured?

  python -X utf8 noise-depth.py SINGLE_A.tif SINGLE_B.tif NAME=ODD.tif,EVEN.tif [...]

Tiles: fpn-pairs.py's --flat selection on SINGLE_A (bright, least fine
energy). Band 0.08-0.30 cycles/px. Noise of a pair = (|A|^2 + |B|^2) / 2 -
Re(A conj B) with the pair's relative shift removed on green (what the two
do not share: for two single frames that includes the sensor pattern's
displacement between them and one focus step, so it overstates one frame's
random noise a little). Printed: each merge's noise power relative to the
single-frame pair's, per channel, and its inverse (the effective number of
groups averaged, per half-stack; the full stack is twice that).
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp
import evaluate as ev

T = 256
dev = fp.DEV


def load(f):
    return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)


A = load(sys.argv[1])
_, H, W = A.shape
ty, tx = H // T, W // T
lvl = A[1][:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
keep = lvl > np.percentile(lvl, 40)
g = A[1]
hp = ((g - fp.gauss(g, 2.0)) ** 2)[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy() / np.maximum(lvl, 1.0)
keep &= hp <= np.percentile(hp[keep], 35)
keep[:1], keep[-1:], keep[:, :1], keep[:, -1:] = False, False, False, False
tiles = [(int(x), int(y)) for y, x in np.argwhere(keep)]
win = ev.hann2(T, dev)
norm = T * T * float((win * win).sum())
fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
fr = torch.sqrt(fx * fx + fy * fy)
band = ((fr >= 0.08) & (fr < 0.30)).double()


def noise(a, b):
    out = torch.zeros(3, dtype=torch.float64, device=dev)
    sig = torch.zeros(3, dtype=torch.float64, device=dev)
    for x, y in tiles:
        p = a[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        q = b[:, y * T:(y + 1) * T, x * T:(x + 1) * T].double()
        p = p - p.mean((1, 2), keepdim=True)
        q = q - q.mean((1, 2), keepdim=True)
        FA, FB = torch.fft.fft2(p * win), torch.fft.fft2(q * win)
        _, _, (sx, sy) = ev.pair_spectra(p[1], q[1], win)
        FB = FB * torch.exp(2j * np.pi * (fx * sx + fy * sy))
        s = (FA * FB.conj()).real / norm
        n = (FA.abs() ** 2 + FB.abs() ** 2) / (2 * norm) - s
        out += (n * band).sum((1, 2))
        sig += (s * band).sum((1, 2))
    return (out / len(tiles)).cpu().numpy(), (sig / len(tiles)).cpu().numpy()


n0, s0 = noise(A, load(sys.argv[2]))
print(f'{len(tiles)} tiles; single-frame pair: noise R/G/B {n0[0]:.3e} {n0[1]:.3e} {n0[2]:.3e}, shared/noise ' + ' '.join(f'{v:.2f}' for v in s0 / n0))
del A
for arg in sys.argv[3:]:
    name, files = arg.split('=', 1)
    fa, fb = files.split(',')
    n, s = noise(load(fa), load(fb))
    print(f'{name:16s} noise / single ' + ' '.join(f'{v:.3f}' for v in n / n0) + '   groups averaged per half ' + ' '.join(f'{v:.1f}' for v in n0 / n)
          + '   shared/noise ' + ' '.join(f'{v:.1f}' for v in s / n))
