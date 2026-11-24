"""What exposure and a sharper restoration target do to one in-focus plane (brief Q8).

Two engine-rendered single planes of the same focus position (linear masters, restoration off),
one at the owner's shutter and one about five times longer, get the same linear filter
G = T / H, with H the diffraction x photosite model at the given cutoff and T a Gaussian
target; capped and tapered toward the cutoff. Crops are shown through one display transform,
the short one scaled by the measured exposure ratio.

  python plane-demo.py <mask npz> <plane index> <short master> <long master> <out prefix> [sigma] [cutoff]
"""
import sys

import numpy as np
import tifffile
from PIL import Image

mask = np.load(sys.argv[1])
plane = int(sys.argv[2])
short, long_ = tifffile.imread(sys.argv[3]), tifffile.imread(sys.argv[4])
prefix = sys.argv[5]
sigma = float(sys.argv[6]) if len(sys.argv) > 6 else 0.4
cutoff = float(sys.argv[7]) if len(sys.argv) > 7 else 0.768
H0, W0 = 384, 512


def window():
    depth, m = mask['depth'], mask['mask']
    best = None
    for by in range(0, depth.shape[0] - H0 // 8, 6):
        for bx in range(0, depth.shape[1] - W0 // 8, 6):
            d = depth[by:by + H0 // 8, bx:bx + W0 // 8]
            share = float(((np.abs(d - plane) <= 2) & m[by:by + H0 // 8, bx:bx + W0 // 8]).mean())
            if best is None or share > best[0]:
                best = (share, by * 8 - 20, bx * 8 - 30)
    return best


share, y0, x0 = window()
print('window at', y0, x0, '(%d x %d px); the plane is sharpest (within 2) over %.0f %% of it' % (W0, H0, 100 * share))
a = short[y0:y0 + H0, x0:x0 + W0].astype(np.float64)
b = long_[y0:y0 + H0, x0:x0 + W0].astype(np.float64)
ratio = float(np.median(b[..., 1][(b[..., 1] > 0.02) & (b[..., 1] < 0.5)] / np.maximum(a[..., 1][(b[..., 1] > 0.02) & (b[..., 1] < 0.5)], 1e-9)))
print('measured exposure ratio long / short on green: %.3f' % ratio)

fy = np.fft.fftfreq(H0)[:, None]
fx = np.fft.fftfreq(W0)[None, :]
fr = np.hypot(fy, fx)
x = np.clip(fr / cutoff, 0, 1)
diff = (2 / np.pi) * (np.arccos(x) - x * np.sqrt(1 - x * x))
Hs = diff * np.sinc(fy) * np.sinc(fx)
T = np.exp(-2 * np.pi ** 2 * sigma ** 2 * fr ** 2)
G = np.minimum(T / np.maximum(Hs, 1e-3), 8.0)
taper = np.clip((1 - fr / cutoff) / 0.15, 0, 1)
G = 1 + (G - 1) * taper * taper * (3 - 2 * taper)
print('gain at 0.2 / 0.3 / 0.4 / 0.5 cycles/px (along an axis): %s' % ' / '.join('%.2f' % G[0, int(round(f * W0))] for f in (0.2, 0.3, 0.4, 0.5)))


def restore(img):
    return np.stack([np.fft.ifft2(np.fft.fft2(img[..., c]) * G).real for c in range(3)], -1)


def show(img, gain):
    v = np.clip(img * gain, 0, 1)
    return (np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055) * 255 + 0.5).astype(np.uint8)


gain = 0.6 / np.percentile(b.max(-1), 99.5)
cy, cx = H0 // 2 - 110, W0 // 2 - 150   # the middle 300 x 220 px
panels = [show(a * ratio, gain), show(restore(a) * ratio, gain), show(restore(b), gain)]
crop = [p[cy:cy + 220, cx:cx + 300] for p in panels]
Image.fromarray(np.hstack(crop[:2])).resize((1200, 440), Image.NEAREST).save(prefix + '-a.png')
Image.fromarray(np.hstack([crop[0], crop[2]])).resize((1200, 440), Image.NEAREST).save(prefix + '-b.png')
# noise in a flat-ish patch: local std of the restored images after removing a 5 px mean
def grain(img):
    g = img[..., 1]
    from scipy import ndimage
    hp = g - ndimage.uniform_filter(g, 5)
    return float(np.median(np.abs(hp)) * 1.4826)
print('fine-scale spread (robust, green, scene detail included): short %.5f, short restored %.5f, long restored %.5f (short ones scaled to the long exposure)' % (
    grain(a * ratio), grain(restore(a) * ratio), grain(restore(b))))
