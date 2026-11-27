"""The calibration's lenses, drawn from real measurements of the dragonfly on the rig: what the
proposal's stage overlays would show. Pictures of the owner's subject: written to scratch only.

  depth-live.png   focus by tile from the 36 s live sweep (33 positions 190 units apart), peaks only
  depth-raw.png    focus by tile from RAW (the stack's planes; a survey would use fewer)
  product.png      what the installed build's rule calls in focus at the stack's FIRST plane
  contrast.png     what the contrast rule calls in focus at that plane, and at a plane inside the range
  glints.png       how far the highlights rise above the base exposure's pin, by tile (stops)
  rail.png         tiles in focus by plane: the product's rule, the contrast rule, the truth; the marks

  python lenses.py <dragonfly scratch folder> <out folder>
"""
import json
import pathlib
import sys

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
base = cv2.cvtColor(cv2.imread(str(root / 'result-overview.jpg')), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
H, W = base.shape[:2]
photo = np.clip(base * 2.2, 0, 1) ** 0.9                       # the stage shows the picture lifted, as live view does
g = np.load(root / 'general.npz')
focus, coherent, inside, pos = g['focus'], g['coherent'], g['inside'], g['pos']
cb = g['contrast'].astype(np.float32)
TURBO = matplotlib.colormaps['turbo']
INK = (0.93, 0.93, 0.90)


def overlay(tiles_rgba, alpha=0.62, gap=1):
    """Square tiles over the photograph, a hairline of picture left between them."""
    th, tw = tiles_rgba.shape[:2]
    img = photo.copy()
    ys = np.linspace(0, H, th + 1).round().astype(int)
    xs = np.linspace(0, W, tw + 1).round().astype(int)
    for i in range(th):
        for j in range(tw):
            a = tiles_rgba[i, j, 3] * alpha
            if a <= 0:
                continue
            sl = (slice(ys[i] + gap, ys[i + 1]), slice(xs[j] + gap, xs[j + 1]))
            img[sl] = img[sl] * (1 - a) + tiles_rgba[i, j, :3] * a
    return img


def save(img, name, legend=None):
    canvas = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    if legend:
        label, lo, hi, ticks = legend
        x0, y0, w, h = 24, H - 40, 300, 8
        bar = (TURBO(np.linspace(0, 1, w))[:, :3] * 255).astype(np.uint8)
        canvas[y0:y0 + h, x0:x0 + w] = bar[None]
        cv2.rectangle(canvas, (x0 - 1, y0 - 1), (x0 + w, y0 + h), (150, 150, 145), 1)
        for v, text in ticks:
            x = int(x0 + (v - lo) / (hi - lo) * w)
            cv2.line(canvas, (x, y0 + h), (x, y0 + h + 4), (230, 230, 225), 1)
            cv2.putText(canvas, text, (x - 16, y0 + h + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (230, 230, 225), 1, cv2.LINE_AA)
        cv2.putText(canvas, label, (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 230, 225), 1, cv2.LINE_AA)
    cv2.imwrite(str(out / name), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))


lo, hi = 32300.0, 33200.0
ticks = [(32355, '32,355'), (32750, '32,750'), (33161, '33,161')]
# depth from RAW
t = np.zeros(focus.shape + (4,), np.float32)
ok = coherent
t[ok, :3] = TURBO(np.clip((focus[ok] - lo) / (hi - lo), 0, 1))[:, :3]
t[ok, 3] = 1
save(overlay(t), 'depth-raw.png', ('DEPTH  where each part is in focus  RAW, 64 px tiles', lo, hi, ticks))
# depth from the live sweep
est = np.load(root / 'rig/series-1/live-wide-own-est.npy') + 27.0
from scipy import ndimage
neigh = ndimage.generic_filter(est, np.nanmedian, size=3, mode='constant', cval=np.nan)
okl = np.isfinite(est) & (np.abs(est - neigh) <= 90)
t = np.zeros(est.shape + (4,), np.float32)
t[okl, :3] = TURBO(np.clip((est[okl] - lo) / (hi - lo), 0, 1))[:, :3]
t[okl, 3] = 1
save(overlay(t, gap=2), 'depth-live.png', ('DEPTH  from the live sweep, 36 s  preview tiles', lo, hi, ticks))
# what counts as in focus at the first plane, and inside the range
ref = float(np.percentile(cb[:, inside].max(0), 90))
for plane, name in ((0, 'first'), (84, 'inside')):
    t = np.zeros(focus.shape + (4,), np.float32)
    m = (cb[plane] >= 0.2 * ref) & inside
    t[m] = (0.36, 0.90, 0.78, 1)
    save(overlay(t, alpha=0.75), 'contrast-%s.png' % name)
    print('contrast rule, plane %d (%d): %d tiles' % (plane + 1, pos[plane], m.sum()))
eng = g['engine_count']
# glints: the highlight frames' brightest sample per tile, over the base exposure's full scale
rows = json.loads((root / 'highlights.json').read_text())
top = np.zeros(focus.shape, np.float32)
pins = np.zeros(focus.shape, np.float32)
for r in rows:
    b = np.load(root / 'planes' / ('base-%04d.npz' % r['plane']))
    pins = np.maximum(pins, b['pin64'].sum(0)[:focus.shape[0], :focus.shape[1]])
    hp = root / 'planes' / ('highlight-%04d.npz' % r['plane'])
    if hp.exists():
        h = np.load(hp)
        mx = (h['max8'].astype(np.float32) - 512.0).max(0) / 15871.0 * r['nominal_ratio']
        mx = mx[:mx.shape[0] // 8 * 8, :mx.shape[1] // 8 * 8].reshape(mx.shape[0] // 8, 8, mx.shape[1] // 8, 8).max(axis=(1, 3))
        top = np.maximum(top, mx[:focus.shape[0], :focus.shape[1]])
stops = np.log2(np.maximum(top, 1e-6))
t = np.zeros(focus.shape + (4,), np.float32)
m = (top > 1.0) & inside
t[m, :3] = matplotlib.colormaps['inferno'](np.clip(0.35 + stops[m] / 5.6 * 0.65, 0, 1))[:, :3]
t[m, 3] = 1
save(overlay(t, alpha=0.8), 'glints.png')
print('tiles whose highlights exceed the base pin: %d of %d subject tiles (%.1f %%); up to %.1f stops; tiles with a pinned sample in any base plane: %d'
      % (m.sum(), inside.sum(), 100 * m.sum() / inside.sum(), stops[m].max(), ((pins > 0) & inside).sum()))
# the rail's evidence
fig, ax = plt.subplots(figsize=(13.3, 2.6), dpi=100, facecolor='#101010')
ax.set_facecolor('#101010')
truth = g['truth_count']
contrast = ((cb >= 0.2 * ref) & inside[None]).sum(axis=(1, 2))
ax.bar(pos, contrast, width=6, color='#5be6c8', alpha=0.85, label='in focus: contrast rule')
ax.step(pos, truth, where='mid', color='#f2f2ec', lw=1, label='in focus: every plane, by eye-checked peaks')
ax.plot(pos, eng, color='#f2b24a', lw=1, ls='--', label='"in focus": energy over 1.75 x noise')
for x, lab in ((32062, 'START 32,062'), (33262, 'END 33,262')):
    ax.axvline(x, color='#f2b24a', lw=1.5); ax.text(x + (8 if x < 33000 else -8), ax.get_ylim()[1] * 0.9, lab, color='#f2b24a', fontsize=8, ha='left' if x < 33000 else 'right')
for x in (32332, 33183):
    ax.axvline(x, color='#5be6c8', lw=1, ls=':')
ax.text(32340, ax.get_ylim()[1] * 0.75, 'subject 32,332', color='#5be6c8', fontsize=8)
ax.text(33175, ax.get_ylim()[1] * 0.75, '33,183', color='#5be6c8', fontsize=8, ha='right')
ax.tick_params(colors='#9a9a94', labelsize=8)
for s in ax.spines.values():
    s.set_color('#3a3a38')
ax.legend(fontsize=8, facecolor='#101010', edgecolor='#3a3a38', labelcolor='#d8d8d2', loc='upper right', bbox_to_anchor=(0.9, 1.0))
ax.set_xlim(pos[0] - 20, pos[-1] + 20); ax.set_ylabel('tiles', color='#9a9a94', fontsize=8)
plt.tight_layout(); plt.savefig(out / 'rail.png'); plt.close()
print('written to', out)
