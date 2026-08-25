"""V-M116 probe 6: is the arm that produced the headline the DEFAULT path?

The headline sentence says "the default merge". The arm measured is B1u, which
is rendered with STREHL_ALIGN=0. The binary itself prints, on that arm:
  "alignment : OFF -- frames are combined unregistered. M86 measured 232.7 px of
   drift on bee-3-cpl; expect softness that grows with radius."

A0 (the actual default) and B1u do not share a grid, so no pixel-wise comparison
is possible. Two grid-independent, gain-independent statistics are computed
instead:

  ACUT = sd(g - box5(g)) / sd(g - box17(g))   over the whole plane
         a band RATIO, so a gain, a level or an exposure cancels exactly.
  RAPS = radially averaged power spectrum of the high-pass, on a 2048x2048
         central window, normalised to unit total power -- so it reports WHERE
         the energy is, not how much.

fit_to_cover rescales A0 by k=0.9634 on bee, so A0's spectrum is stretched by
~3.8% in frequency relative to B1u's. Any difference smaller than that is not
interpretable; the point of the probe is whether the difference is much larger.
"""
from pathlib import Path
import numpy as np
import tifffile

M = Path(r"C:\dev\strehl-out\M116\measure")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
ARMS = ["B0", "B1u", "M0u", "A0", "M0"]


def load_green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16"
    return a[:, :, 1].astype(np.float64)


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def acut(g):
    return float((g - box(g, 5)).std() / (g - box(g, 17)).std())


def raps(g, n=2048):
    h, w = g.shape
    y, x = (h - n) // 2, (w - n) // 2
    c = g[y:y + n, x:x + n]
    c = c - c.mean()
    win = np.hanning(n)
    c = c * win[:, None] * win[None, :]
    P = np.abs(np.fft.rfft2(c)) ** 2
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    nb = 64
    idx = np.clip((r / 0.7071 * nb).astype(int), 0, nb - 1)
    tot = np.bincount(idx.ravel(), P.ravel(), minlength=nb)
    cnt = np.bincount(idx.ravel(), minlength=nb)
    prof = tot / np.maximum(cnt, 1)
    prof = prof / prof.sum()
    return prof


for s in SUBJECTS:
    print(f"\n=== {s} ===")
    profs = {}
    for arm in ARMS:
        g = load_green(M / f"{s}__{arm}.tif")
        a = acut(g)
        profs[arm] = raps(g)
        hi = float(profs[arm][32:].sum())   # power above half Nyquist
        print(f"  {arm:4s}  ACUT {a:.5f}   log10 ACUT {np.log10(a):+.5f}   "
              f"frac power > 0.25 cyc/px {hi:.5f}")
    print(f"  d log10 ACUT  B1u - B0 = {np.log10(acut(load_green(M/f'{s}__B1u.tif')))-np.log10(acut(load_green(M/f'{s}__B0.tif'))):+.5f} dex")
    print(f"  d log10 ACUT  A0  - B1u = {np.log10(acut(load_green(M/f'{s}__A0.tif')))-np.log10(acut(load_green(M/f'{s}__B1u.tif'))):+.5f} dex "
          f"(alignment on vs off, same 100 frames, same gate)")
