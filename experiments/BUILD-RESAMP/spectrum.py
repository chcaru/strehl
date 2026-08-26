"""BUILD-RESAMP -- the L3/CR transfer as a fine-grained curve rather than five
wide bands, so the merge plane's Nyquist is visible if it is there.

The merge runs on the CFA quad planes ("planes : 3516 x 2344 per CFA plane"
against a 7032 x 4688 output), so one plane sample is two output pixels and the
plane's Nyquist lands at 0.25 cycles per OUTPUT pixel. Everything the gather
kernel touches is at or below that. Everything above it was put there by the
demosaic.

If that is true, the kernel's transfer curve should look like a kernel below
0.25 and like something else above it. Five wide bands cannot show that; 0.01
wide bins can. Printed as a table because this agent may not write image files
as output.
"""

import sys

import numpy as np

sys.path.insert(0, str(__file__).rsplit("\\", 1)[0])
from band_ratio import TILE, green, tiles  # noqa: E402


def radial(img, pos, win, nb, fmax):
    fy = np.fft.fftfreq(TILE)[:, None]
    fx = np.fft.rfftfreq(TILE)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    idx = np.clip((r / fmax * nb).astype(int), 0, nb - 1)
    acc = np.zeros(nb)
    cnt = np.bincount(idx.ravel(), minlength=nb).astype(float)
    for y, x in pos:
        t = img[y : y + TILE, x : x + TILE]
        t = (t - t.mean()) * win
        p = np.abs(np.fft.rfft2(t)) ** 2
        acc += np.bincount(idx.ravel(), weights=p.ravel(), minlength=nb)
    return acc / np.maximum(cnt, 1) / len(pos)


def main():
    a_path, b_path, label = sys.argv[1], sys.argv[2], sys.argv[3]
    border = int(sys.argv[4]) if len(sys.argv) > 4 else 96
    a = green(a_path)
    b = green(b_path)
    pos = tiles(*a.shape, border)
    win = np.hanning(TILE)[:, None] * np.hanning(TILE)[None, :]
    nb, fmax = 50, 0.5
    pa = radial(a, pos, win, nb, fmax)
    pb = radial(b, pos, win, nb, fmax)
    edges = np.linspace(0, fmax, nb + 1)
    print(f"# {label}")
    print(f"  A={a_path}\n  B={b_path}\n  {len(pos)} ROIs, border {border}")
    print("  merge plane Nyquist = 0.250 cyc/output px  (planes are half the output raster)")
    print(f"\n  {'f (cyc/out px)':<16}{'A/B amplitude':>15}{'B power':>14}")
    for i in range(nb):
        f = 0.5 * (edges[i] + edges[i + 1])
        if f > 0.02:
            mark = "  <== plane Nyquist" if edges[i] <= 0.25 < edges[i + 1] else ""
            print(f"  {f:<16.3f}{np.sqrt(pa[i] / pb[i]):>15.4f}{pb[i]:>14.4g}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
