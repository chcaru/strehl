"""Pictures for the calibration mockups, drawn from the measurements of 2026-11-27 (the grounding
experiment's scratch). They are the owner's subject: written to outputs/assets, which Git ignores.
Without them the build draws placeholders.

    python assets.py [scratch folder of the dragonfly, default C:/strehl-scratch/plan-flow/dragonfly]

  cpf-live          the subject as the stage shows it
  cpf-depth-sweep   Depth lens from the 36 s live sweep (preview tiles)
  cpf-depth         Depth lens from RAW (64 px tiles)
  cpf-depth-at      the same with only the tiles in focus at one lens position kept
  cpf-cover         Cover lens for a Start held too late
  cpf-glints        Glints lens
  cpf-core-a/b/c    a core sample: one tile from three frames around its focus
  rail.json         tiles in focus by position, for the rail
"""
import json
import pathlib
import sys

import cv2
import matplotlib
import numpy as np
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('C:/strehl-scratch/plan-flow/dragonfly')
OUT = HERE / 'outputs' / 'assets'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = (1140, 760)
RAMP = matplotlib.colormaps['turbo']
LO, HI = 32300.0, 33200.0
WIDTH = 45.0

base = cv2.cvtColor(cv2.imread(str(ROOT / 'result-overview.jpg')), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
base = cv2.resize(base, SIZE, interpolation=cv2.INTER_AREA)
H, W = base.shape[:2]
photo = np.clip(base * 2.2, 0, 1) ** 0.9
g = np.load(ROOT / 'general.npz')
focus, coherent, inside, pos = g['focus'], g['coherent'], g['inside'], g['pos']
cb = g['contrast'].astype(np.float32)


def overlay(rgba, alpha=0.62, gap=1, under=None):
    img = (photo if under is None else under).copy()
    th, tw = rgba.shape[:2]
    ys = np.linspace(0, H, th + 1).round().astype(int)
    xs = np.linspace(0, W, tw + 1).round().astype(int)
    for i in range(th):
        for j in range(tw):
            a = rgba[i, j, 3] * alpha
            if a > 0:
                sl = (slice(ys[i] + gap, ys[i + 1]), slice(xs[j] + gap, xs[j + 1]))
                img[sl] = img[sl] * (1 - a) + rgba[i, j, :3] * a
    return img


def write(img, name, quality=86):
    cv2.imwrite(str(OUT / (name + '.jpg')), cv2.cvtColor((np.clip(img, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, quality])


def ramp(values):
    return RAMP(np.clip((values - LO) / (HI - LO), 0, 1))[:, :3]


write(photo, 'cpf-live')
t = np.zeros(focus.shape + (4,), np.float32)
t[coherent, :3] = ramp(focus[coherent]); t[coherent, 3] = 1
write(overlay(t, gap=0 if W / focus.shape[1] < 9 else 1), 'cpf-depth')
# only the tiles in focus at one position
AT = 32742.0
near = coherent & (np.abs(focus - AT) <= WIDTH / 2)
t2 = np.zeros_like(t)
t2[near, :3] = ramp(focus[near]); t2[near, 3] = 1.25
t2[coherent & ~near, :3] = 0.5; t2[coherent & ~near, 3] = 0.16
write(overlay(t2, gap=0), 'cpf-depth-at')
# the sweep's coarse map
est = np.load(ROOT / 'rig/series-1/live-wide-own-est.npy') + 27.0
neigh = ndimage.generic_filter(est, np.nanmedian, size=3, mode='constant', cval=np.nan)
ok = np.isfinite(est) & (np.abs(est - neigh) <= 2 * WIDTH)
ts = np.zeros(est.shape + (4,), np.float32)
ts[ok, :3] = ramp(est[ok]); ts[ok, 3] = 1
write(overlay(ts, gap=2), 'cpf-depth-sweep')
# Cover: a Start held at 32,480 loses what is in focus before it
START = 32480.0
lost = coherent & (focus < START - WIDTH / 2)
tc = np.zeros_like(t)
tc[coherent & ~lost, :3] = (0.36, 0.90, 0.78); tc[coherent & ~lost, 3] = 0.45
tc[lost, :3] = (0.95, 0.70, 0.29); tc[lost, 3] = 1.3
write(overlay(tc, gap=0), 'cpf-cover')
# Glints: highlights over the base exposure's pin, in stops
rows = json.loads((ROOT / 'highlights.json').read_text())
top = np.zeros(focus.shape, np.float32)
for r in rows:
    hp = ROOT / 'planes' / ('highlight-%04d.npz' % r['plane'])
    if hp.exists():
        mx = (np.load(hp)['max8'].astype(np.float32) - 512.0).max(0) / 15871.0 * r['nominal_ratio']
        mx = mx[:mx.shape[0] // 8 * 8, :mx.shape[1] // 8 * 8].reshape(mx.shape[0] // 8, 8, mx.shape[1] // 8, 8).max(axis=(1, 3))
        top = np.maximum(top, mx[:focus.shape[0], :focus.shape[1]])
m = (top > 1.0) & inside
tg = np.zeros_like(t)
tg[m, :3] = matplotlib.colormaps['inferno'](np.clip(0.4 + np.log2(top[m]) / 5.6 * 0.6, 0, 1))[:, :3]; tg[m, 3] = 1.3
write(overlay(tg, gap=0), 'cpf-glints')
# a core sample: a tile on the lower wing, from the frames nearest its focus and one survey spacing either side
ty, tx = 90, 61
f = float(focus[ty, tx])
files = sorted((ROOT / 'planes').glob('base-*.npz'))
crops = []
for name, d in (('a', -48), ('b', 0), ('c', 48)):
    i = int(np.argmin(np.abs(pos - (f + d))))
    gplane = np.load(files[g['order'][i]])['g'].astype(np.float32) - 512.0
    c = gplane[ty * 32 - 40:ty * 32 + 72, tx * 32 - 40:tx * 32 + 72]
    crops.append((name, int(pos[i]), c))
hi = max(np.percentile(c, 99.7) for _, _, c in crops)
for name, p, c in crops:
    v = np.clip(c / hi, 0, 1) ** (1 / 2.2)
    cv2.imwrite(str(OUT / ('cpf-core-%s.jpg' % name)), (cv2.resize(v, (224, 224), interpolation=cv2.INTER_NEAREST) * 255).astype(np.uint8),
                [cv2.IMWRITE_JPEG_QUALITY, 90])
ref = float(np.percentile(cb[:, inside].max(0), 90))
counts = ((cb >= 0.2 * ref) & inside[None]).sum(axis=(1, 2))
curve = cb[:, ty, tx]
hist, edges = np.histogram(est[ok], bins=np.arange(31900, 33500, 40))
rail = {'from': int(pos[0]), 'step': int(pos[1] - pos[0]), 'counts': counts.tolist(),
        'sweep': {'from': int(edges[0]), 'step': 40, 'counts': hist.tolist()},
        'core': {'tile': [ty, tx], 'focus': round(f), 'frames': [p for _, p, _ in crops],
                 'curve': [round(float(v), 3) for v in curve[::3]], 'curve_from': int(pos[0]), 'curve_step': int(3 * (pos[1] - pos[0]))},
        'glint_tiles_share': round(float(m.sum() / inside.sum()), 4), 'glint_stops': round(float(np.log2(top[m].max())), 1),
        'lost_tiles': int(lost.sum()), 'lost_share': round(float(lost.sum() / coherent.sum()), 4),
        'tiles_at': int(near.sum())}
(OUT / 'rail.json').write_text(json.dumps(rail))
print('written to', OUT, '| lost before a Start of %d: %d tiles (%.1f %%) | in focus at %d: %d tiles | core tile focus %d, frames %s'
      % (START, lost.sum(), 100 * rail['lost_share'], AT, near.sum(), f, rail['core']['frames']))
