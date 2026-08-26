"""BUILD-RESAMP -- commission `band_ratio.py` before any of its answers count.

Three arms, all on real rendered pixels rather than a synthetic plant:

  NULL     the same render against itself. Every band must read exactly 1.0000.
           If it does not, the instrument has a bias and nothing it prints later
           is a measurement.
  POTENCY  a known Gaussian blur against the same render. The ratio must fall,
           and it must fall by the amount the Gaussian's own MTF predicts --
           exp(-2 pi^2 sigma^2 f^2) evaluated at the band's power-weighted
           centre. An instrument that detects "a difference" without landing on
           the right magnitude cannot price one.
  SIGN     the blur in the numerator vs the denominator, to prove the statistic
           is not symmetric by construction.

The Gaussian is applied to the green channel in the frequency domain, which is
exact, so the prediction has no discretisation slack in it.
"""

import sys

import numpy as np
import tifffile

sys.path.insert(0, str(__file__).rsplit("\\", 1)[0])
from band_ratio import BANDS, NORM, TILE, band_masks, green, roi_bands, tiles  # noqa: E402


def blur(img, sigma):
    fy = np.fft.fftfreq(img.shape[0])[:, None]
    fx = np.fft.rfftfreq(img.shape[1])[None, :]
    h = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return np.fft.irfft2(np.fft.rfft2(img) * h, s=img.shape)


def shape_stat(img, pos, masks, win):
    p = roi_bands(img, pos, masks, win)
    ni = [n for n, _, _ in BANDS].index(NORM)
    return p, p / p[:, ni : ni + 1]


def report(name, sa, sb, pred=None):
    ni = [n for n, _, _ in BANDS].index(NORM)
    print(f"  {name}")
    print(f"    {'band':<12}{'ratio':>10}{'predicted':>12}{'|err|':>10}")
    worst = 0.0
    for j, (n, lo, hi) in enumerate(BANDS):
        if j == ni:
            continue
        r = float(np.median(np.sqrt(sa[:, j] / sb[:, j])))
        if pred is None:
            print(f"    {n:<12}{r:>10.6f}{'-':>12}{abs(r - 1.0):>10.2e}")
            worst = max(worst, abs(r - 1.0))
        else:
            p = pred(lo, hi)
            print(f"    {n:<12}{r:>10.6f}{p:>12.6f}{abs(r - p):>10.4f}")
            worst = max(worst, abs(r - p))
    print(f"    worst deviation: {worst:.3e}")
    return worst


def main():
    src = sys.argv[1]
    g = green(src)
    h, w = g.shape
    pos = tiles(h, w)
    masks = band_masks()
    win = np.hanning(TILE)[:, None] * np.hanning(TILE)[None, :]
    print(f"commissioning band_ratio.py on {src}")
    print(f"  {w} x {h}, {len(pos)} ROIs of {TILE} px\n")

    _, s0 = shape_stat(g, pos, masks, win)
    n_worst = report("NULL  (same render both sides)", s0, s0)
    print(f"    NULL {'PASS' if n_worst == 0.0 else 'FAIL'}\n")

    sigma = 0.5
    gb = blur(g, sigma)
    _, sb = shape_stat(gb, pos, masks, win)

    # A Gaussian's MTF is analytic. Predict each band by the mid-frequency of
    # the band, which is where an r^-2-ish natural spectrum puts most of its
    # weight; report the band edges too so the reader can see the spread.
    def pred(lo, hi):
        f = 0.5 * (lo + hi)
        return float(np.exp(-2.0 * np.pi**2 * sigma**2 * f**2))

    p_worst = report(f"POTENCY (sigma = {sigma} px Gaussian in the numerator)", sb, s0, pred)
    print(f"    POTENCY {'PASS' if p_worst < 0.10 else 'FAIL'}  (bar: within 0.10 of the "
          f"Gaussian's own MTF at the band centre)\n")

    report("SIGN  (the same blur in the DENOMINATOR -- must invert)", s0, sb,
           lambda lo, hi: 1.0 / pred(lo, hi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
