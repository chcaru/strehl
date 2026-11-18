"""Compare capture 3's stacks: single-shot run, and the four-shot run as
member1 (every group demosaiced from its member 1), remosaic (groups passing
the checks assembled) and remosaic-ungated (every group assembled).

  python -X utf8 compare-capture3.py STACK_DIR OUT_DIR

The three four-shot arms share one warp-map cache entry and frame list, so
they are pixel-aligned; the single-shot arm is located against member1 by
phase correlation on a downsampled luma and cropped at the shifted origin
(integer pixels; the arms' focus breathing and cover fit differ slightly, so
the single-shot crops are for eye comparison only and excluded from the
metrics).

Metrics, four-shot arms only, on the in-focus face (tiles whose member1 luma
high-pass energy is in the top 30%, background excluded): RMS of the
high-passed chroma (R-G, B-G; high-pass = value minus its 5x5 box mean) on
edge pixels (luma gradient in the top 20% of the mask) and on flat pixels
(bottom 50%). Edge chroma is false colour plus colour fringes plus noise;
flat chroma is mostly noise. Luma high-pass RMS is detail plus noise; it
cannot separate them and is reported as such. Values are on the TIFF's own
encoding (the binned linear camera-native measurement output), identical
across arms. Crops use one display transform for every arm (a common gain
and a 1/2.2 power); origins and sizes are printed.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import uniform_filter

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
ARMS = ['single', 'four-member1', 'four-remosaic', 'four-remosaic-ungated']
img = {a: tifffile.imread(src / f'{a}.tif') for a in ARMS}
for a, v in img.items():
    print(a, v.shape, v.dtype)
scale = 65535.0 if img['four-member1'].dtype == np.uint16 else 1.0
img = {a: v[..., :3].astype(np.float32) / scale for a, v in img.items()}
H, W = img['four-member1'].shape[:2]
assert all(img[a].shape == (H, W, 3) for a in ARMS[1:]), 'four-shot arms must be aligned'


def luma(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


# Single-shot arm against member1: phase correlation at 1/8 scale.
def small(x, f=8):
    y = luma(x)
    h, w = (y.shape[0] // f) * f, (y.shape[1] // f) * f
    return y[:h, :w].reshape(h // f, f, w // f, f).mean((1, 3))


a, b = small(img['four-member1']), small(img['single'])
h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
a, b = a[:h, :w] - a[:h, :w].mean(), b[:h, :w] - b[:h, :w].mean()
r = np.fft.ifft2(np.fft.fft2(a) * np.conj(np.fft.fft2(b)) / (np.abs(np.fft.fft2(a) * np.fft.fft2(b)) + 1e-9)).real
dy, dx = np.unravel_index(r.argmax(), r.shape)
dy, dx = (dy if dy < h // 2 else dy - h) * 8, (dx if dx < w // 2 else dx - w) * 8
print('single-shot offset vs member1 (px):', -dx, -dy)

# In-focus mask from member1.
L = {k: luma(v) for k, v in img.items()}
T = 128
m1 = L['four-member1']
hp = m1 - uniform_filter(m1, 5)
th, tw = H // T, W // T
energy = (hp[:th * T, :tw * T] ** 2).reshape(th, T, tw, T).mean((1, 3))
mean = m1[:th * T, :tw * T].reshape(th, T, tw, T).mean((1, 3))
fg = mean > np.percentile(mean, 15)  # drop the dark background
sel = (energy >= np.percentile(energy[fg], 70)) & fg
mask = np.kron(sel, np.ones((T, T), bool))
mask = np.pad(mask, ((0, H - mask.shape[0]), (0, W - mask.shape[1])))
gy, gx = np.gradient(uniform_filter(m1, 3))
grad = np.hypot(gx, gy)
gm = grad[mask]
edge = mask & (grad >= np.percentile(gm, 80))
flat = mask & (grad <= np.percentile(gm, 50))

metrics = {}
for k in ARMS[1:]:
    x = img[k]
    cr, cb = x[..., 0] - x[..., 1], x[..., 2] - x[..., 1]
    hcr, hcb = cr - uniform_filter(cr, 5), cb - uniform_filter(cb, 5)
    chroma = np.sqrt(hcr ** 2 + hcb ** 2)
    hl = L[k] - uniform_filter(L[k], 5)
    metrics[k] = {
        'edge_hf_chroma_rms': float(np.sqrt((chroma[edge] ** 2).mean())),
        'flat_hf_chroma_rms': float(np.sqrt((chroma[flat] ** 2).mean())),
        'mask_hf_luma_rms': float(np.sqrt((hl[mask] ** 2).mean())),
        'edge_hf_luma_rms': float(np.sqrt((hl[edge] ** 2).mean())),
    }
metrics['_mask'] = {'tiles': int(sel.sum()), 'pixels': int(mask.sum()), 'edge': int(edge.sum()), 'flat': int(flat.sum())}
(out / 'metrics.json').write_text(json.dumps(metrics, indent=1) + '\n')
print(json.dumps(metrics, indent=1))

# Native crops: the four strongest in-focus tiles spread over the frame, plus
# the centre. Identical display transform: the TIFF's own encoding, 8-bit.
C = 384
cands = np.argwhere(sel)
order = cands[np.argsort(-energy[sel])]
picks = []
for ty, tx in order:
    cy, cx = ty * T + T // 2, tx * T + T // 2
    if all(abs(cy - py) > 2 * C or abs(cx - px) > 2 * C for py, px in picks):
        picks.append((cy, cx))
    if len(picks) == 4:
        break
picks.append((H // 2, W // 2))
# One display transform for every arm: a common gain from member1's luma
# p99.5, then a 1/2.2 power.
gain = 1.0 / max(1e-6, float(np.percentile(L['four-member1'], 99.5)))


def display(x):
    return np.clip(np.clip(x * gain, 0, 1) ** (1 / 2.2) * 255 + 0.5, 0, 255).astype(np.uint8)


rows = []
for i, (cy, cx) in enumerate(picks):
    y0, x0 = max(0, min(H - C, cy - C // 2)), max(0, min(W - C, cx - C // 2))
    tiles = []
    for k in ARMS:
        oy, ox = (y0 - dy, x0 - dx) if k == 'single' else (y0, x0)
        oy, ox = max(0, min(img[k].shape[0] - C, oy)), max(0, min(img[k].shape[1] - C, ox))
        t = display(img[k][oy:oy + C, ox:ox + C])
        tiles.append(np.pad(t, ((4, 4), (4, 4), (0, 0)), constant_values=255))
    rows.append(np.concatenate(tiles, 1))
    print(f'crop {i}: origin ({x0}, {y0}) size {C} (single-shot arm at ({x0 - dx}, {y0 - dy}))')
Image.fromarray(np.concatenate(rows, 0)).save(out / 'crops.png')
ov = display(img['four-remosaic'][::6, ::6])
Image.fromarray(ov).save(out / 'overview-remosaic.png')
print('columns:', ARMS)
