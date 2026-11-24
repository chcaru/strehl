"""Signal and noise of single four-shot groups, from the two green samples each photosite gets
(two different members, same light): cross-spectrum = signal, auto minus cross = noise. The
member-to-member shift is removed as a phase ramp. Compares groups at (nearly) the same focus
position taken at different shutter times, on the tiles sharpest in the first group.

  python group-snr.py <folderA> <planeA> <labelA> <folderB> <planeB> <labelB>
"""
import sys

import numpy as np

import rigdata  # beside this file

T = 256
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]
BANDS = [(0.03, 0.06), (0.06, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.35), (0.35, 0.40), (0.40, 0.50)]


def two_greens(folder, plane):
    names = rigdata.groups(folder)[plane]
    ms = [rigdata.read(folder, n) for n in names]
    img0 = ms[0][0]
    h, w = img0.shape
    yy, xx = np.mgrid[2:h - 2, 2:w - 2]
    vals = []
    for (img, b, wl, cfa), (dx, dy) in zip(ms, rigdata.OFFSETS):
        sy, sx = yy + dy, xx + dx
        vals.append(np.where(cfa[sy % 2, sx % 2] == 'G', img[sy, sx].astype(np.float32) - b, np.nan))
    st = np.stack(vals)
    order = np.argsort(np.isnan(st), axis=0)[:2]
    a = np.take_along_axis(st, order[:1], 0)[0]
    b_ = np.take_along_axis(st, order[1:2], 0)[0]
    return a, b_, float(np.isnan(b_).mean())


def spectra(a, b, y, x):
    ta, tb = a[y:y + T, x:x + T], b[y:y + T, x:x + T]
    m = 0.5 * (ta.mean() + tb.mean())
    fa = np.fft.rfft2((ta / m - 1) * WIN)
    fb = np.fft.rfft2((tb / m - 1) * WIN)
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-(FR / 0.2) ** 2), s=(T, T))
    py, px = np.unravel_index(corr.argmax(), corr.shape)

    def sub(mm, c, p):
        d = mm - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (mm - p) / d
    dy = (py + T // 2) % T - T // 2 + sub(corr[(py - 1) % T, px], corr[py, px], corr[(py + 1) % T, px])
    dx = (px + T // 2) % T - T // 2 + sub(corr[py, (px - 1) % T], corr[py, px], corr[py, (px + 1) % T])
    cross = (cross * np.exp(2j * np.pi * (fy * dy + fx * dx))).real
    auto = 0.5 * (np.abs(fa) ** 2 + np.abs(fb) ** 2)
    s = np.array([cross[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])
    n = np.array([(auto - cross)[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])
    return s, n, m, np.hypot(dx, dy)


fa_, pa, la, fb_, pb, lb = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6]
A1, A2, missA = two_greens(fa_, pa)
B1, B2, missB = two_greens(fb_, pb)
print('sites without two green samples: %s %.3f, %s %.3f (0 means the members cover the four positions)' % (la, missA, lb, missB))
# Glints pinned in the longer exposure lose modulation, which reads as lost signal. With
# "clipmatch" the shorter exposure is clamped at the same radiance, so both are clipped alike.
if len(sys.argv) > 7 and sys.argv[7] == 'clipmatch':
    PIN = 16383.0 - 512.0
    ratio = float(np.nanmedian(A1[1000:-1000:7, 1000:-1000:7]) / np.nanmedian(B1[1000:-1000:7, 1000:-1000:7]))
    if ratio > 1:
        B1, B2 = np.minimum(B1, PIN / ratio), np.minimum(B2, PIN / ratio)
    else:
        A1, A2 = np.minimum(A1, PIN * ratio), np.minimum(A2, PIN * ratio)
    print('clip matched: exposure ratio %.2f; the shorter exposure is clamped at the pin of the longer one' % ratio)
h, w = A1.shape
cands = []
for y in range(800, h - 800 - T, T):
    for x in range(800, w - 800 - T, T):
        if np.isnan(A1[y:y + T, x:x + T]).any() or np.isnan(A2[y:y + T, x:x + T]).any():
            continue
        s, n, m, _ = spectra(A1, A2, y, x)
        if m > 150:
            cands.append((s[3:7].sum(), y, x))
cands.sort(reverse=True)
tiles = [(y, x) for _, y, x in cands[:30]]
SA, NA, SB, NB, MA, MB, DA, DB = [], [], [], [], [], [], [], []
for y, x in tiles:
    if np.isnan(B1[y:y + T, x:x + T]).any() or np.isnan(B2[y:y + T, x:x + T]).any():
        continue
    s, n, m, d = spectra(A1, A2, y, x)
    s2, n2, m2, d2 = spectra(B1, B2, y, x)
    SA.append(s); NA.append(n); SB.append(s2); NB.append(n2); MA.append(m); MB.append(m2); DA.append(d); DB.append(d2)
SA, NA, SB, NB = map(np.array, (SA, NA, SB, NB))
print('%d tiles (sharpest in %s); level DN above black: %s %.0f, %s %.0f (ratio %.2f); green-to-green shift px: %s %.2f, %s %.2f' % (
    len(SA), la, la, np.median(MA), lb, np.median(MB), np.median(np.array(MA) / np.array(MB)), la, np.median(DA), lb, np.median(DB)))
print('band cycles/px | signal power %s over %s | noise power ratio | signal/noise power: %s, %s (ratio)' % (la, lb, la, lb))
for i, (lo, hi) in enumerate(BANDS):
    ra, rb = np.median(SA[:, i] / NA[:, i]), np.median(SB[:, i] / NB[:, i])
    print('%.2f-%.2f      | %.2f | %.2f | %.1f, %.1f (%.2f)' % (lo, hi, np.median(SA[:, i] / SB[:, i]), np.median(NA[:, i] / NB[:, i]), ra, rb, ra / rb))
