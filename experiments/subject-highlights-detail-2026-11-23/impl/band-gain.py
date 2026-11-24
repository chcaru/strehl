"""The restoration's delivered amplitude gain by band, measured on the written linear masters
(shd-q-restore, plan Q2).

  python band-gain.py <out root> <unrestored arm> <capture name> <arm> [<arm> ...]

For each arm: sqrt(sum P_arm / sum P_unrestored) per band, P the windowed power spectrum of each
256 px luminance tile (BT.709 weights on the linear master), summed over the tiles in the
brightest half by mean level (the subject, not the dark background) and over the frequencies in
the band. The masters come from one alignment and one merge, so their ratio is the filter as
delivered (kernel, square-root domain, highlight guard), signal and noise alike; it is not a
signal-only measure. Bands in cycles/px.
"""
import pathlib
import sys

import numpy as np
import tifffile

root, off, name, arms = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4:]
T = 256
BANDS = [(0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50)]
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]


def luma(path):
    a = tifffile.imread(path)
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float64)


def band_power(img, tiles):
    out = np.zeros(len(BANDS))
    for y, x in tiles:
        t = img[y:y + T, x:x + T]
        p = np.abs(np.fft.rfft2((t - t.mean()) * WIN)) ** 2
        out += [p[(FR >= lo) & (FR < hi)].sum() for lo, hi in BANDS]
    return out


base = luma(root / off / name / 'master.tiff')
h, w = base.shape
grid = [(y, x) for y in range(T, h - 2 * T, T) for x in range(T, w - 2 * T, T)]
level = np.array([base[y:y + T, x:x + T].mean() for y, x in grid])
tiles = [g for g, l in zip(grid, level) if l >= np.median(level)]
p0 = band_power(base, tiles)
print('%s: %d tiles of %d px (brightest half of %d); bands %s' % (name, len(tiles), T, len(grid), BANDS))
for arm in arms:
    p = band_power(luma(root / arm / name / 'master.tiff'), tiles)
    print('  %-6s amplitude over unrestored: %s' % (arm, ' / '.join('%.3f' % v for v in np.sqrt(p / p0))))
