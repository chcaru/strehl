"""The pitch of a regular grid in a green plane saved by slide-look.py (results R6).

  python pitch.py <plane.npy> ROW,COL [ROW,COL ...]

For each 768-sample box at the given corner: mean removed, a Hann window, a two-dimensional
Fourier transform; the strongest peaks that are not each other's mirror image, each refined
by the centroid of the power in the 5 x 5 bins around it. Prints the two strongest as a
period in green samples and in sensor pixels (twice that), with the peak's direction.
"""
import sys

import numpy as np

N = 768
g = np.load(sys.argv[1])


def pitch(y0, x0):
    c = g[y0:y0 + N, x0:x0 + N].astype(np.float64)
    c = c - c.mean()
    win = np.hanning(N)[:, None] * np.hanning(N)[None, :]
    power = np.abs(np.fft.fftshift(np.fft.fft2(c * win))) ** 2
    cy = cx = N // 2
    yy, xx = np.mgrid[:N, :N]
    power[np.hypot(yy - cy, xx - cx) < 6] = 0
    out = []
    for _ in range(2):
        i = np.unravel_index(power.argmax(), power.shape)
        ys, xs = slice(i[0] - 2, i[0] + 3), slice(i[1] - 2, i[1] + 3)
        w = power[ys, xs]
        fy = (w * yy[ys, xs]).sum() / w.sum() - cy
        fx = (w * xx[ys, xs]).sum() / w.sum() - cx
        out.append((fx / N, fy / N))
        for j in (i, (2 * cy - i[0], 2 * cx - i[1])):
            power[max(0, j[0] - 6):j[0] + 7, max(0, j[1] - 6):j[1] + 7] = 0
    return out


for corner in sys.argv[2:]:
    y0, x0 = (int(v) for v in corner.split(','))
    parts = []
    for fx, fy in pitch(y0, x0):
        f = np.hypot(fx, fy)
        parts.append('period %.3f green samples (%.3f sensor px) at %.2f degrees' % (1 / f, 2 / f, np.degrees(np.arctan2(fy, fx))))
    print((y0, x0), '; '.join(parts))
