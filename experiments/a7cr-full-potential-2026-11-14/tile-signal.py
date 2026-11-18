"""Per-tile coherent signal and noise of render pairs (the per-tile form of
compare-colour.py), for oracle and per-depth comparisons.

  python -X utf8 tile-signal.py OUT.npz NAME=A.tif,B.tif [NAME=A.tif,B.tif ...]

All renders share one geometry (the same run under the same warp sidecar, or
odd/even halves). Tiles: 256 px on the full grid, none dropped here; per tile
it records the green high-pass energy and clipped fraction of the first arm's
first render, so the analysis can choose tiles. Per arm, tile and channel,
from the pair's Hann-windowed spectra with their relative shift removed
(evaluate.py's pair_spectra): signal and noise summed over 0.25-0.40
cycles/px ('hi') and 0.10-0.25 ('lo'). out: names, energy [ty, tx],
clip [ty, tx], sig [arm, ty, tx, channel, band], noi likewise.
Fooled by: content common to both renders that is not scene.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).parent))
import fp
import evaluate as ev

out = Path(sys.argv[1])
arms = [(a.split('=', 1)[0], a.split('=', 1)[1].split(',')) for a in sys.argv[2:]]
T = ev.T
dev = fp.DEV
win = ev.hann2(T, dev)
fy = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[:, None]
fx = torch.fft.fftfreq(T, device=dev, dtype=torch.float64)[None, :]
fr = torch.sqrt(fx * fx + fy * fy)
bands = [((fr >= 0.25) & (fr <= 0.40)).double(), ((fr >= 0.10) & (fr < 0.25)).double()]


def load(f):
    return torch.from_numpy(tifffile.imread(f).astype(np.float32)).to(dev).permute(2, 0, 1)


first = load(arms[0][1][0])
_, H, W = first.shape
ty, tx = H // T, W // T
g = first[1]
hpe = (g - fp.gauss(g, 2.0)) ** 2
energy = hpe[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
clip = (first.max(0).values > 60000).float()[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
mean_g = g[:ty * T, :tx * T].reshape(ty, T, tx, T).mean((1, 3)).cpu().numpy()
del first
sig = np.zeros((len(arms), ty, tx, 3, 2))
noi = np.zeros_like(sig)
for ai, (name, files) in enumerate(arms):
    A, B = load(files[0]), load(files[1])
    for y in range(ty):
        for x in range(tx):
            for c in range(3):
                s, n, _ = ev.pair_spectra(A[c, y * T:(y + 1) * T, x * T:(x + 1) * T], B[c, y * T:(y + 1) * T, x * T:(x + 1) * T], win)
                for b, m in enumerate(bands):
                    sig[ai, y, x, c, b] = float((s * m).sum())
                    noi[ai, y, x, c, b] = float((n * m).sum())
    print(name, flush=True)
    del A, B
np.savez(out, names=np.array([a[0] for a in arms]), energy=energy, clip=clip, mean_g=mean_g, sig=sig, noi=noi)
print('wrote', out)
