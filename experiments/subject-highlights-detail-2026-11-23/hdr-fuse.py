"""Fuse a long and a short four-shot group of one plane per photosite (brief Q4).

Linear RAW units, no interpolation of colour (both groups are assembled four-shot planes):
  1. shift of the short group against the long one (phase correlation on unclipped mid-tones);
  2. the exposure ratio measured where both are well exposed (never the nominal shutter ratio:
     the light moves a few per cent between groups);
  3. a site takes the short group, scaled, where any colour of the long group is near its pin or
     has a pinned neighbour; a smooth ramp in between;
  4. checks: the two groups must agree in the hand-over band, and fusing a group with a scaled
     copy of itself must return it.

  python hdr-fuse.py <long folder> <short folder> <out prefix> <y0> <x0> [h w]
"""
import pathlib
import sys

import numpy as np
from scipy import ndimage

import rigdata

long_dir, short_dir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
y0, x0 = int(sys.argv[4]), int(sys.argv[5])
h, w = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (1024, 1536)
FULL = 16383.0 - 512.0
LO, HI = 0.75, 0.90       # hand-over band as a share of the pin
crop = (y0, y0 + h, x0, x0 + w)
L, Lpin, _ = rigdata.assemble(rigdata.members(long_dir), crop=crop)
S, Spin, _ = rigdata.assemble(rigdata.members(short_dir), crop=crop)


def register(a, b):
    """shift (dx, dy) to apply to b so that it lies on a."""
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    fa, fb = np.fft.rfft2((a - a.mean()) * win), np.fft.rfft2((b - b.mean()) * win)
    cross = fa * np.conj(fb)
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-((fy ** 2 + fx ** 2) / 0.2 ** 2)), s=a.shape)
    py, px = np.unravel_index(corr.argmax(), corr.shape)

    def sub(m, c, p):
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    H, W = a.shape
    dy = (py + H // 2) % H - H // 2 + sub(corr[(py - 1) % H, px], corr[py, px], corr[(py + 1) % H, px])
    dx = (px + W // 2) % W - W // 2 + sub(corr[py, (px - 1) % W], corr[py, px], corr[py, (px + 1) % W])
    return dx, dy


def fuse(L, Lpin, S, label):
    g_l = np.minimum(L[..., 1], 0.6 * FULL)        # clipped areas must not steer the registration
    dx, dy = register(g_l, np.minimum(S[..., 1] * (np.median(L[..., 1]) / max(np.median(S[..., 1]), 1e-6)), 0.6 * FULL))
    Sr = np.stack([ndimage.shift(S[..., c], (dy, dx), order=3, mode='nearest') for c in range(3)], -1)
    ok = (L > 0.05 * FULL) & (L < 0.6 * FULL) & (Sr > 30)
    k = np.array([np.median(L[..., c][ok[..., c]] / Sr[..., c][ok[..., c]]) for c in range(3)])
    kk = float(np.median(k))
    near = ndimage.maximum_filter((L.max(-1) / FULL), 5)                       # a site and its neighbours
    wgt = np.clip((near - LO) / (HI - LO), 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    wgt = np.maximum(wgt, ndimage.maximum_filter(Lpin.any(-1).astype(np.float32), 5))
    fused = L * (1 - wgt[..., None]) + kk * Sr * wgt[..., None]
    band = (L.max(-1) > 0.5 * FULL) & (L.max(-1) < LO * FULL) & ~ndimage.maximum_filter(Lpin.any(-1), 9)
    ratio = (kk * Sr[..., 1][band]) / L[..., 1][band]
    print('%s: shift %+.3f, %+.3f px; exposure ratio R %.4f G %.4f B %.4f (one value used: %.4f)' % (label, dx, dy, *k, kk))
    print('   sites taken from the short group (weight > 0.5): %d of %d (%.4f %%); pinned in the long group: %d; still pinned in the short: %d' % (
        int((wgt > 0.5).sum()), wgt.size, 100 * (wgt > 0.5).mean(), int(Lpin.any(-1).sum()), int(Spin.any(-1).sum())))
    if band.sum() > 50:
        print('   hand-over check, green at 50-75 %% of the pin in the long group: scaled short / long = %.4f median, %.4f spread (1 sigma, %d sites)' % (
            np.median(ratio), 0.7413 * (np.percentile(ratio, 75) - np.percentile(ratio, 25)), band.sum()))
    print('   fused peak %.2f x the long group\'s pin' % (fused.max() / FULL))
    return fused, wgt, kk


fused, wgt, k = fuse(L, Lpin, S, 'long + short')
# control: a group fused with a scaled copy of itself must come back unchanged
ctl, _, _ = fuse(L, Lpin, L / 16.0, 'control (long + long/16)')
unp = ~ndimage.maximum_filter(Lpin.any(-1), 5)
print('   control residual where the long group is not pinned: max |fused - long| = %.3f DN' % np.abs(ctl - L)[unp].max())
np.savez_compressed(prefix + '.npz', long=L, short=S, fused=fused, weight=wgt, ratio=k)

# pictures: one display transform for all (white balance, exposure, a shoulder that keeps hue, sRGB)
WB = np.array([1.7842, 1.0, 2.5732], np.float32)


def show(img, gain, shoulder=True):
    x = np.maximum(img, 0) / FULL * WB * gain
    if shoulder:
        lum = x.max(-1, keepdims=True)
        knee = 0.7
        out = np.where(lum > knee, knee + (1 - knee) * (1 - np.exp(-(lum - knee) / (1 - knee) / 2.5)), lum)
        x = x * (out / np.maximum(lum, 1e-6))
    x = np.clip(x, 0, 1)
    return (np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055) * 255 + 0.5).astype(np.uint8)


try:
    from PIL import Image
    gain = 0.5 / max(np.percentile((L / FULL * WB).max(-1), 99), 1e-6)     # the body's bright end at mid-scale
    pin_l = np.minimum(L, FULL)                                            # what a clipped file holds
    Image.fromarray(show(pin_l, gain, shoulder=False)).save(prefix + '-long.png')
    Image.fromarray(show(fused, gain)).save(prefix + '-fused.png')
    print('pictures: display gain %.2f on the long group\'s scale' % gain)
except ImportError:
    pass
