"""Two captures of the same tile at different shutter times, compared at the tiles where the
shorter (partial) stack is in focus. Signal = cross-spectrum of odd and even half-stacks;
noise = auto-spectrum minus that; linear masters, restoration off, luminance.

  python exposure-compare.py <labelA> <oddA> <evenA> <labelB> <oddB> <evenB>
     A is the partial stack that chooses the tiles.
"""
import sys

import numpy as np
import tifffile

T = 256
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]
BANDS = [(0.03, 0.06), (0.06, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.35), (0.35, 0.40), (0.40, 0.50)]


def luma(path):
    a = tifffile.imread(path)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def spectra(a, b, y, x):
    ta, tb = a[y:y + T, x:x + T], b[y:y + T, x:x + T]
    fa = np.fft.rfft2((ta / max(ta.mean(), 1e-9) - 1) * WIN)
    fb = np.fft.rfft2((tb / max(tb.mean(), 1e-9) - 1) * WIN)
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-(FR / 0.2) ** 2), s=(T, T))
    py, px = np.unravel_index(corr.argmax(), corr.shape)
    dy, dx = (py + T // 2) % T - T // 2, (px + T // 2) % T - T // 2
    cross = (cross * np.exp(2j * np.pi * (fy * dy + fx * dx))).real
    auto = 0.5 * (np.abs(fa) ** 2 + np.abs(fb) ** 2)
    s = np.array([cross[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])
    n = np.array([(auto - cross)[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])
    return s, n, float(ta.mean())


la, oa, ea, lb, ob, eb = sys.argv[1:7]
A1, A2, B1, B2 = luma(oa), luma(ea), luma(ob), luma(eb)
h, w = A1.shape
cands = []
for y in range(600, h - 600 - T, T):
    for x in range(600, w - 600 - T, T):
        s, n, m = spectra(A1, A2, y, x)
        if m > 0.005:
            cands.append((s[3:7].sum(), y, x))
cands.sort(reverse=True)
tiles = [(y, x) for _, y, x in cands[:40]]
print('%d tiles of %d px: the most detailed in %s (where its 24 planes are in focus)' % (len(tiles), T, la))


def shift(a, b, y, x):
    ta, tb = a[y:y + T, x:x + T], b[y:y + T, x:x + T]
    fa = np.fft.rfft2((ta / max(ta.mean(), 1e-9) - 1) * WIN)
    fb = np.fft.rfft2((tb / max(tb.mean(), 1e-9) - 1) * WIN)
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-(FR / 0.1) ** 2), s=(T, T))
    py, px = np.unravel_index(corr.argmax(), corr.shape)
    return (px + T // 2) % T - T // 2, (py + T // 2) % T - T // 2, float(corr.max())


sh = [shift(A1, B1, y, x) for y, x in tiles]
dx, dy = int(np.median([s[0] for s in sh])), int(np.median([s[1] for s in sh]))
print('offset between the two renders at these tiles: %d, %d px (median); correlation peak median %.2f' % (dx, dy, np.median([s[2] for s in sh])))
SA, NA, SB, NB, MA, MB = [], [], [], [], [], []
for y, x in tiles:
    s, n, m = spectra(A1, A2, y, x)
    yb, xb = y - dy, x - dx
    if yb < 0 or xb < 0 or yb + T > h or xb + T > w:
        continue
    s2, n2, m2 = spectra(B1, B2, yb, xb)
    SA.append(s); NA.append(n); SB.append(s2); NB.append(n2); MA.append(m); MB.append(m2)
SA, NA, SB, NB = map(np.array, (SA, NA, SB, NB))
print('mean level of the tiles: %s %.4f, %s %.4f (ratio %.2f)' % (la, np.median(MA), lb, np.median(MB), np.median(np.array(MA) / np.array(MB))))
print('band cycles/px | signal power %s / %s | noise power %s / %s | signal/noise: %s, %s (ratio)' % (la, lb, la, lb, la, lb))
for i, (lo, hi) in enumerate(BANDS):
    ra, rb = np.median(SA[:, i] / NA[:, i]), np.median(SB[:, i] / NB[:, i])
    print('%.2f-%.2f      | %.2f | %.2f | %.1f, %.1f (%.2f)' % (lo, hi, np.median(SA[:, i] / SB[:, i]), np.median(NA[:, i] / NB[:, i]), ra, rb, ra / rb))
