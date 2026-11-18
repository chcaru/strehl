"""Compare shipped-stacker renders arm against arm, per channel, from two
independent captures of the same subject.

  python -X utf8 compare-colour.py OUT_DIR BASE=single.tif,member1.tif ARM=a.tif,b.tif [...]

Each arm is two full-resolution `strehl stack --demosaic` renders, one per
capture (single-shot run, four-shot run as member 1). Tiles: 256 px where the
base arm's green high-pass energy is in the top 30 % (in focus) and under
1 % of pixels are near clipping in any arm. For each tile and channel, the two captures' tiles
form an independent pair; with a Hann window and their relative shift removed
as a phase ramp (evaluate.py's `pair_spectra`):

  signal = Re(A conj(B))  (common content; noise cancels)
  noise  = (|A|^2 + |B|^2) / 2 - signal

Reported per arm and channel, as ratios to the first (base) arm: signal
amplitude in 0.25-0.40 and 0.10-0.25 cycles/px, high-pass noise (value minus
5x5 box mean, in the Fourier domain), the noise inside each signal band, and
the R-G and B-G high-pass chroma
coherence: sqrt(signal power of the chroma difference) over the edge band
0.05-0.25 cycles/px, which lateral or axial misregistration inflates (a
colour fringe is common to both captures, so it is signal, not noise).
Fooled by: anything common to both captures that is not scene; colour
fringes count as chroma signal by design.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).parent))
import fp
import evaluate as ev

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
arms = []
for a in sys.argv[2:]:
    name, files = a.split('=', 1)
    arms.append((name, files.split(',')))
T = ev.T
dev = fp.DEV
win = ev.hann2(T, dev)
fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
fr = torch.sqrt(fx * fx + fy * fy)


def d5(f):
    return torch.where(f.abs() < 1e-9, torch.ones_like(f), torch.sin(5 * np.pi * f) / (5 * torch.sin(np.pi * f)))


hp = (1 - d5(fx) * d5(fy)) ** 2
band_hi = ((fr >= 0.25) & (fr <= 0.40)).double()
band_lo = ((fr >= 0.10) & (fr < 0.25)).double()
band_edge = ((fr >= 0.05) & (fr < 0.25)).double()


def load(f):
    return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)


base = [load(f) for f in arms[0][1]]
_, H, W = base[0].shape
g = base[0][1]
hpe = (g - fp.gauss(g, 2.0)) ** 2
ty, tx = H // T, W // T
e = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
m = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
fg = m > np.percentile(m, 15)
sel = (e >= np.percentile(e[fg], 70)) & fg
sel[:1], sel[-1:], sel[:, :1], sel[:, -1:] = False, False, False, False
loaded = {arms[0][0]: base}
for name, files in arms[1:]:
    loaded[name] = [load(f) for f in files]
clip = torch.zeros(H, W, dtype=torch.bool, device=dev)
for pair in loaded.values():
    for im in pair:
        clip |= im.max(0).values > 60000
# A specular subject glints nearly everywhere; a tile is kept when under
# 1 % of its pixels are near clipping in any arm (clipped glints sit at the
# same places in both captures, so they count as common content in every arm).
clipt = torch.nn.functional.avg_pool2d(clip.float()[None, None], T, T)[0, 0].cpu().numpy() > 0.01
sel &= ~clipt[:ty, :tx]
tiles = [(int(x) * T, int(y) * T) for y, x in np.argwhere(sel)]
print('tiles', len(tiles))


def spectra(a, b):
    s, n, _ = ev.pair_spectra(a, b, win)
    return s, n


report = {'tiles': tiles, 'arms': {}}
for name, pair in loaded.items():
    A, B = pair
    res = {}
    for c in range(3):
        S = torch.zeros(T, T, dtype=torch.float64, device=dev)
        N = torch.zeros_like(S)
        for x0, y0 in tiles:
            s, n = spectra(A[c, y0:y0 + T, x0:x0 + T], B[c, y0:y0 + T, x0:x0 + T])
            S += s
            N += n
        res['RGB'[c]] = {'hi': float((S * band_hi).sum()), 'lo': float((S * band_lo).sum()), 'noise_hp': float((N * hp).sum()),
                         'hi_noise': float((N * band_hi).sum()), 'lo_noise': float((N * band_lo).sum())}
    for c, label in ((0, 'R-G'), (2, 'B-G')):
        S = torch.zeros(T, T, dtype=torch.float64, device=dev)
        for x0, y0 in tiles:
            s, _ = spectra(A[c, y0:y0 + T, x0:x0 + T] - A[1, y0:y0 + T, x0:x0 + T], B[c, y0:y0 + T, x0:x0 + T] - B[1, y0:y0 + T, x0:x0 + T])
            S += s
        res[label] = float((S * band_edge).sum())
    report['arms'][name] = res
b0 = report['arms'][arms[0][0]]
print(f'ratios to {arms[0][0]} (amplitude; chroma = coherent R-G / B-G edge-band amplitude):')
for name, r in report['arms'].items():
    parts = []
    for c in 'RGB':
        parts.append(f'{c}: hi {np.sqrt(max(r[c]["hi"], 0) / b0[c]["hi"]):.3f} lo {np.sqrt(max(r[c]["lo"], 0) / b0[c]["lo"]):.3f} '
                     f'noise {np.sqrt(r[c]["noise_hp"] / b0[c]["noise_hp"]):.3f}')
    parts.append(f'chroma R-G {np.sqrt(max(r["R-G"], 0) / b0["R-G"]):.3f} B-G {np.sqrt(max(r["B-G"], 0) / b0["B-G"]):.3f}')
    print(f'{name:10s} ' + '  '.join(parts))
print('in-band noise amplitude (whatever the two captures do not share), ratios to the base arm, hi / lo:')
for name, r in report['arms'].items():
    print(f'{name:10s} ' + '  '.join(f'{c}: {np.sqrt(r[c]["hi_noise"] / b0[c]["hi_noise"]):.3f} / {np.sqrt(r[c]["lo_noise"] / b0[c]["lo_noise"]):.3f}' for c in 'RGB')
          + '   signal-to-noise power in hi: ' + ' '.join(f'{r[c]["hi"] / r[c]["hi_noise"]:.2f}' for c in 'RGB'))
(out / 'compare-colour.json').write_text(json.dumps(report, indent=1) + '\n')
