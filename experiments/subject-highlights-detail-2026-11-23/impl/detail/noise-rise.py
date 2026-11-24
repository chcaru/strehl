"""Plan D2's gate: a flat tile's noise rise against the Detail budget (shd-d-detail).

  python noise-rise.py <out root> <unrestored arm> <capture name> <arm> [<arm> ...]

On the linear masters (one alignment, one merge; the arms differ only in the restoration):
256 px tiles of the unrestored master that hold noise, not scene: the mean power per
frequency at 0.10-0.20 cycles/px at most 5 times that at 0.30-0.50 (MEASURED with
tiles.py-style statistics on the weevil and scarab: backdrop tiles of pure noise read 3 to 4,
the gather and the chroma smoothing shape the noise; tiles with scene structure read 7 to 100),
at most 5 % of samples at or below zero (the merge clamps negative values, which rectifies a
dark backdrop's noise and makes the restoration non-linear there), and no sample above 0.5
(away from highlights and the guard). For each arm: per tile, the power at
0.30-0.50 cycles/px of the arm over the unrestored, green channel of the master (the write's
chroma smoothing hands red and blue green's finest bands) and BT.709 luminance; the median
and quartiles over the flat tiles. Compared with the budget and the designed and delivered
rise the render's log reports for green ("detail" lines).
"""
import pathlib
import re
import sys

import numpy as np
import tifffile

root, off, name, arms = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4:]
T = 256
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]
FINE = (FR >= 0.30) & (FR < 0.50)
LOW = (FR >= 0.10) & (FR < 0.20)


def planes(path):
    a = tifffile.imread(path).astype(np.float64)
    return {'green': a[..., 1], 'luma': 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]}


def power(t):
    return np.abs(np.fft.rfft2((t - t.mean()) * WIN)) ** 2


base = planes(root / off / name / 'master.tiff')
g = base['green']
h, w = g.shape
flat = []
for y in range(T, h - 2 * T, T):
    for x in range(T, w - 2 * T, T):
        t = g[y:y + T, x:x + T]
        if (t <= 0).mean() > 0.05 or t.max() > 0.5:
            continue
        p = power(t)
        if p[LOW].mean() <= 5.0 * p[FINE].mean():
            flat.append((y, x))
print('%s: %d noise tiles of %d px (unrestored master, green: 0.10-0.20 power per frequency <= 5 x '
      'the 0.30-0.50 power, <= 5 %% of samples at or below zero, max < 0.5)' % (name, len(flat), T))
if not flat:
    raise SystemExit('no flat tile')
for arm in arms:
    log = (root / arm / name / 'render.log').read_text(encoding='utf-8', errors='replace')
    m = re.search(r'detail\s+: (.*)', log)
    gl = re.search(r'\n\s+G: noise power in 0\.30-0\.50 cycles/px x([0-9.]+) designed, x([0-9.]+) delivered', log)
    budget = re.search(r'at most ([0-9.]+) x the unrestored', log)
    sigma = re.search(r'target ([0-9.]+) px chosen', log) or re.search(r'target Gaussian sigma ([0-9.]+) px', log)
    print('  %s: %s' % (arm, m.group(1)[:160] if m else '(no detail line)'))
    arm_planes = planes(root / arm / name / 'master.tiff')
    for ch in ('green', 'luma'):
        r = np.array([power(arm_planes[ch][y:y + T, x:x + T])[FINE].sum() /
                      power(base[ch][y:y + T, x:x + T])[FINE].sum() for y, x in flat])
        q1, med, q3 = np.percentile(r, [25, 50, 75])
        line = '    %-5s flat-tile noise rise 0.30-0.50: median %.3f (quartiles %.3f-%.3f)' % (ch, med, q1, q3)
        if ch == 'green' and gl:
            designed, delivered = float(gl.group(1)), float(gl.group(2))
            line += '; log: designed %.2f, delivered %.2f' % (designed, delivered)
            if budget:
                b = float(budget.group(1))
                line += '; budget %.2f: median / budget %.3f (%s within 10 %%)' % (
                    b, med / b, 'IS' if abs(med / b - 1) <= 0.10 else 'NOT')
            line += '; median / delivered %.3f' % (med / delivered)
        print(line)
    if sigma:
        print('    target sigma %s px' % sigma.group(1))
