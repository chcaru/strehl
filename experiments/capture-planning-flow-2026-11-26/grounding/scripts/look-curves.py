"""First look at the through-focus measures: depth maps and whole-subject curves by plane.

  python look-curves.py <curves folder> <capture folder> <out png>
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.path import Path as MplPath

src, run, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
T = 4                      # blocks a tile side: 4 x 16 = 64 sensor px
focus = np.load(src / 'focus.npy')
cube = {n: np.load(src / (n + '.npy'), mmap_mode='r') for n in ('lap2', 'mid2', 'low2', 'mean', 'lap2m', 'nm', 'bright', 'pin')}


def tiles(a):
    p, h, w = a.shape
    h, w = h // T * T, w // T * T
    return np.asarray(a[:, :h, :w]).reshape(p, h // T, T, w // T, T).sum(axis=(2, 4))


lap, mid, low = tiles(cube['lap2']), tiles(cube['mid2']), tiles(cube['low2'])
lapm, nm = tiles(cube['lap2m']), tiles(cube['nm'])
mean = tiles(cube['mean']) / T ** 2
bright = tiles(cube['bright'])
P, H, W = lap.shape
rings = json.loads((run / 'manifest.json').read_text())['plan']['subject']['rings']
yy, xx = np.mgrid[0:H, 0:W]
pts = np.column_stack([(xx.ravel() + 0.5) / W, (yy.ravel() + 0.5) / H])
inside = np.zeros(H * W, bool)
for ring in rings:
    inside |= MplPath(np.array(ring)).contains_points(pts)
inside = inside.reshape(H, W)
print('tiles', H, W, 'inside the outline', inside.sum(), 'planes', P, 'focus', focus[0], focus[-1])

# Noise in the Laplacian measure: on the last planes' darkest tiles nothing is in focus.
px = (T * 8) ** 2
far = lap[-5:].mean(0) / px
dark = mean[-5:].mean(0)
print('lap2 per pixel on the five farthest planes: dark-background median %.1f; subject median %.1f' % (np.median(far[~inside]), np.median(far[inside])))

fig, ax = plt.subplots(3, 3, figsize=(19, 13))
peak = lap.argmax(0)
ax[0, 0].imshow(np.where(inside, focus[peak], np.nan), cmap='turbo'); ax[0, 0].set_title('plane of largest lap2 (engine measure), focus units')
ratio = lap.max(0) / np.maximum(np.percentile(lap, 10, axis=0), 1e-6)
ax[0, 1].imshow(np.log10(ratio), cmap='magma', vmin=0, vmax=3); ax[0, 1].set_title('log10 peak / 10th percentile of lap2')
ax[0, 2].imshow(np.log10(np.maximum(lap.max(0) / px, 1)), cmap='gray'); ax[0, 2].set_title('log10 peak lap2 per pixel')
lapm_pp = lapm / np.maximum(nm, 1)
okm = nm > 0.5 * px
peakm = np.where(okm, lapm_pp, 0).argmax(0)
ax[1, 0].imshow(np.where(inside, focus[peakm], np.nan), cmap='turbo'); ax[1, 0].set_title('plane of largest lap2 away from bright samples')
band = lap / np.maximum(mid, 1e-6)
peakb = band.argmax(0)
ax[1, 1].imshow(np.where(inside, focus[peakb], np.nan), cmap='turbo'); ax[1, 1].set_title('plane of largest lap2 / mid2 (band ratio)')
ax[1, 2].imshow(np.log10(np.maximum(bright.max(0), 0.5)), cmap='hot'); ax[1, 2].set_title('log10 most bright samples in any plane')
# whole-subject curves, each normalised to its own maximum
for name, c in (('lap2 (engine)', lap[:, inside].sum(1)), ('lap2 away from bright', lapm[:, inside].sum(1)),
                ('mid band', mid[:, inside].sum(1)), ('low band', low[:, inside].sum(1)),
                ('bright samples', bright[:, inside].sum(1))):
    ax[2, 0].plot(focus, c / c.max(), label=name)
ax[2, 0].legend(); ax[2, 0].set_title('sum over the subject by plane, each over its own maximum'); ax[2, 0].set_xlabel('focus')
# how many subject tiles peak at each plane, by measure
for name, pk in (('lap2', peak), ('away from bright', peakm), ('band ratio', peakb)):
    ax[2, 1].plot(focus, np.bincount(pk[inside], minlength=P), label=name)
ax[2, 1].legend(); ax[2, 1].set_title('subject tiles whose measure peaks at each plane')
# half-height widths of lap2 curves, subject tiles with a real peak
widths = []
for y, x in zip(*np.nonzero(inside)):
    c = lap[:, y, x]
    floor = np.percentile(c, 10); k = c.argmax()
    if c[k] < 6 * floor or k == 0 or k == P - 1:
        continue
    half = floor + (c[k] - floor) / 2
    a = k
    while a > 0 and c[a] > half: a -= 1
    b = k
    while b < P - 1 and c[b] > half: b += 1
    if c[a] > half or c[b] > half:
        continue
    widths.append((b - a) * (focus[1] - focus[0]))
widths = np.array(widths)
ax[2, 2].hist(widths, bins=np.arange(0, 600, 16)); ax[2, 2].set_title('half-height width of lap2, focus units: %d tiles, median %.0f, p10 %.0f, p90 %.0f'
                                                                        % (len(widths), np.median(widths), np.percentile(widths, 10), np.percentile(widths, 90)))
for a in ax[:2].ravel():
    a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig(out, dpi=70)
print('subject tiles with a measurable peak', len(widths), 'of', inside.sum(), 'width median', np.median(widths), 'p10', np.percentile(widths, 10), 'p90', np.percentile(widths, 90))
print('whole-subject lap2 by plane, over its max, every 10th plane:', np.round((lap[:, inside].sum(1) / lap[:, inside].sum(1).max())[::10], 2))
print('same, away from bright:', np.round((lapm[:, inside].sum(1) / lapm[:, inside].sum(1).max())[::10], 2))
