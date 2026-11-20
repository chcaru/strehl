"""Does a short settle after a focus step hurt the first exposure of a four-shot group?

  python -X faulthandler settle-analyse.py <folder of pNN-sSSSS-M.ARW>

Groups are named by plane and by the settle (ms after the camera's focus-result event) before
the shutter. If the lens or the rig were still moving during exposure 1, that exposure would be
(a) softer than exposures 2-4 of its own group, which start 1.1 s or more later, and
(b) displaced from where the long-settle groups put exposure 1 relative to exposures 2-4.

Per group, on a detailed in-focus window:
  sharp1/sharp234  gradient energy of exposure 1 over the mean of exposures 2-4 (noise energy
                   removed with the flat window's energy scaled by signal level);
  shift residual   phase-correlation shift of exposures 2, 3, 4 against exposure 1, minus the
                   median of the same shift over the 1500 ms groups (the pixel-shift pattern
                   itself and its estimator bias are common to all groups and cancel).
Controls: the same ratio on a defocused flat window (noise only; run first), and a planted
0.25 px blur and 0.2 px shift of exposure 1 that the two measures must report.
"""
import collections
import pathlib
import re
import statistics as st
import sys

import cv2
import numpy as np
import rawpy

folder = pathlib.Path(sys.argv[1])
groups = collections.defaultdict(dict)
for f in sorted(folder.glob('*.ARW')):
    m = re.match(r'p(\d+)-s(\d+)-(\d)\.ARW', f.name)
    groups[(int(m.group(1)), int(m.group(2)))][int(m.group(3))] = f
SIZE = 1536


def cfa(path):
    with rawpy.imread(str(path)) as raw:
        img = raw.raw_image_visible.copy()  # copy inside the context
        black = float(np.mean(raw.black_level_per_channel))
    return img, black


def gray(img, black, y, x, size=SIZE):
    roi = img[y:y + size, x:x + size]
    g = cv2.cvtColor(roi, cv2.COLOR_BAYER_RG2GRAY).astype(np.float32) - black
    return g


def energy(g):
    s = cv2.GaussianBlur(g, (0, 0), 1.0)
    gx = cv2.Sobel(s, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(s, cv2.CV_32F, 0, 1)
    return float(np.mean(gx * gx + gy * gy))


# Windows: chosen once on a 1500 ms group's first exposure.
ref_key = sorted(k for k in groups if k[1] == 1500)[0]
img, black = cfa(groups[ref_key][1])
h, w = img.shape
small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BAYER_RG2GRAY).astype(np.float32) - black, (w // 16, h // 16), interpolation=cv2.INTER_AREA)
gx = cv2.Sobel(small, cv2.CV_32F, 1, 0)
gy = cv2.Sobel(small, cv2.CV_32F, 0, 1)
e = cv2.boxFilter(gx * gx + gy * gy, -1, (SIZE // 16, SIZE // 16), normalize=True, anchor=(0, 0))
level = cv2.boxFilter(small, -1, (SIZE // 16, SIZE // 16), normalize=True, anchor=(0, 0))
valid = np.zeros_like(e, bool)
valid[:(h - SIZE) // 16, :(w - SIZE) // 16] = True
iy, ix = np.unravel_index(np.argmax(np.where(valid, e, -1)), e.shape)
detail = (int(iy) * 16 // 2 * 2, int(ix) * 16 // 2 * 2)
flat_score = np.where(valid & (level > 0.5 * np.median(small)), e, np.inf)
fy, fx = np.unravel_index(np.argmin(flat_score), e.shape)
flat = (int(fy) * 16 // 2 * 2, int(fx) * 16 // 2 * 2)
print('frame %dx%d black %.0f; detail window at y=%d x=%d, flat window at y=%d x=%d (%d px square)' % (w, h, black, *detail, *flat, SIZE))

hann = cv2.createHanningWindow((SIZE, SIZE), cv2.CV_32F)
rows = {}
for key in sorted(groups):
    shots = groups[key]
    if len(shots) != 4:
        print('skip', key, 'has', len(shots))
        continue
    d, f, lv = {}, {}, {}
    for n in (1, 2, 3, 4):
        img, black = cfa(shots[n])
        d[n] = gray(img, black, *detail)
        f[n] = gray(img, black, *flat)
        lv[n] = float(d[n].mean())
    rows[key] = (d, f, lv)

# Control 1 (first): the flat window's ratio is noise only.
print('\ncontrol, flat window: gradient energy of exposure 1 over exposures 2-4 (expect 1 within noise)')
flat_ratio = {}
for key, (d, f, lv) in rows.items():
    ef = {n: energy(f[n]) for n in f}
    flat_ratio[key] = ef[1] / np.mean([ef[2], ef[3], ef[4]])
print('   ', '  '.join('p%02d/%d:%.3f' % (k[0], k[1], v) for k, v in flat_ratio.items()))
print('    spread of the flat ratio: %.4f (std over %d groups)' % (np.std(list(flat_ratio.values())), len(flat_ratio)))


def measures(d, f):
    ef = {n: energy(f[n]) for n in f}
    lf = {n: float(f[n].mean()) for n in f}
    ed = {}
    for n in d:
        # noise energy at the detail window's level, from the flat window (shot noise ~ level)
        noise = ef[n] * float(d[n].mean()) / lf[n]
        ed[n] = energy(d[n]) - noise
    ratio = ed[1] / np.mean([ed[2], ed[3], ed[4]])
    shifts = {}
    for n in (2, 3, 4):
        (sx, sy), _ = cv2.phaseCorrelate(d[1] * 1.0, d[n] * 1.0, hann)
        shifts[n] = (sx, sy)
    return ratio, shifts, ed


res = {key: measures(d, f) for key, (d, f, lv) in rows.items()}
long_keys = [k for k in res if k[1] == 1500]
base = {n: (st.median(res[k][1][n][0] for k in long_keys), st.median(res[k][1][n][1] for k in long_keys)) for n in (2, 3, 4)}
print('\npixel-shift pattern as this estimator sees it (median over the 1500 ms groups): ' + ', '.join('exposure %d at (%+.3f, %+.3f) px' % (n, *base[n]) for n in (2, 3, 4)))


def residual(shifts):
    return max(float(np.hypot(shifts[n][0] - base[n][0], shifts[n][1] - base[n][1])) for n in (2, 3, 4))


# Control 2: a planted fault in exposure 1 of a long-settle group must show.
d, f, lv = rows[long_keys[-1]]
planted = dict(d)
planted[1] = cv2.GaussianBlur(d[1], (0, 0), 0.25 * 2.0)
r_blur, _, _ = measures(planted, f)
m = np.float32([[1, 0, 0.2], [0, 1, 0.0]])
planted = dict(d)
planted[1] = cv2.warpAffine(d[1], m, (SIZE, SIZE), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
_, s_shift, _ = measures(planted, f)
print('control, planted in exposure 1 of p%02d: Gaussian blur sigma 0.5 px -> sharp ratio %.3f (unplanted %.3f); 0.2 px shift -> residual %.3f px (unplanted %.3f)' % (
    long_keys[-1][0], r_blur, res[long_keys[-1]][0], residual(s_shift), residual(res[long_keys[-1]][1])))

print('\nper group: settle ms, plane, level ratio 1/234, sharp1/sharp234, shift residual px, detail energy of exposure 1')
by = collections.defaultdict(list)
for key in sorted(res, key=lambda k: (k[1], k[0])):
    ratio, shifts, ed = res[key]
    d, f, lv = rows[key]
    r = residual(shifts)
    by[key[1]].append((ratio, r))
    print('   %5d  p%02d  %.4f  %.4f  %.3f  %.1f' % (key[1], key[0], lv[1] / np.mean([lv[2], lv[3], lv[4]]), ratio, r, ed[1]))
print('\nsummary by settle after the focus-result event:')
for s in sorted(by):
    ratios = [a for a, _ in by[s]]
    resid = [b for _, b in by[s]]
    print('   %5d ms: sharp1/sharp234 median %.4f (min %.4f, max %.4f); shift residual median %.3f px (max %.3f); n=%d' % (
        s, st.median(ratios), min(ratios), max(ratios), st.median(resid), max(resid), len(ratios)))

# The estimator's bias moves with focus (the planes go through best focus), so the shifts are
# also compared with a quadratic through all sixteen planes; what is left, by settle, is
# the part a settle could explain.
print()
print('shift of exposures 2, 3, 4 against exposure 1 per plane (px), in plane order:')
keys = sorted(res)
planes = np.array([k[0] for k in keys], float)
left = {}
for n in (2, 3, 4):
    for axis, name in ((0, 'x'), (1, 'y')):
        v = np.array([res[k][1][n][axis] for k in keys])
        fit = np.polyval(np.polyfit(planes, v, 2), planes)
        left[(n, axis)] = v - fit
        print('   exposure %d %s: ' % (n, name) + ' '.join('%+.3f' % a for a in v))
print('   departure from a quadratic in plane index, rms over exposures and axes, by settle:')
for s in sorted(by):
    idx = [i for i, k in enumerate(keys) if k[1] == s]
    vals = np.array([left[c][i] for c in left for i in idx])
    worst = max(float(np.hypot(left[(n, 0)][i], left[(n, 1)][i])) for n in (2, 3, 4) for i in idx)
    print('   %5d ms: rms %.3f px, worst %.3f px' % (s, float(np.sqrt(np.mean(vals ** 2))), worst))
