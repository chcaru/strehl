"""Is fine detail weaker along one axis? Signal power (cross-spectrum of the odd and even
half-stacks, so noise drops out) in a 45-degree cone about the horizontal frequency axis and
about the vertical one, by band. A sway along y blurs detail that varies along y, which lives
near the vertical frequency axis.

  python aniso.py <label> <odd master> <even master> <cx> <cy> <half> [...]
"""
import sys

import numpy as np
import tifffile

T = 512
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
ANG = np.degrees(np.arctan2(np.abs(fy), np.abs(fx) + 1e-12))     # 0 = horizontal frequency (detail varying along x)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]
BANDS = [(0.05, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40)]


def luma(path):
    a = tifffile.imread(path)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


args = sys.argv[1:]
for i in range(0, len(args), 6):
    label, odd, even, cx, cy, half = args[i], args[i + 1], args[i + 2], int(args[i + 3]), int(args[i + 4]), int(args[i + 5])
    a, b = luma(odd), luma(even)
    rows = []
    for y in range(cy - half, cy + half - T + 1, T // 2):
        for x in range(cx - half, cx + half - T + 1, T // 2):
            ta, tb = a[y:y + T, x:x + T], b[y:y + T, x:x + T]
            if ta.mean() <= 0:
                continue
            fa = np.fft.rfft2((ta / ta.mean() - 1) * WIN)
            fb = np.fft.rfft2((tb / tb.mean() - 1) * WIN)
            cross = (fa * np.conj(fb)).real
            hx = [cross[(FR >= lo) & (FR < hi) & (ANG < 22.5)].mean() for lo, hi in BANDS]
            hy = [cross[(FR >= lo) & (FR < hi) & (ANG > 67.5)].mean() for lo, hi in BANDS]
            rows.append((sum(hx[1:3]) + sum(hy[1:3]), hx, hy))
    rows.sort(key=lambda r: -r[0])
    keep = rows[:max(4, len(rows) // 3)]
    hx = np.median([r[1] for r in keep], 0)
    hy = np.median([r[2] for r in keep], 0)
    print('%s (%d tiles): detail varying along y over detail varying along x, signal power by band:' % (label, len(keep)))
    print('   ' + '  '.join('%.2f-%.2f: %.2f' % (lo, hi, hy[k] / hx[k]) for k, (lo, hi) in enumerate(BANDS)))
