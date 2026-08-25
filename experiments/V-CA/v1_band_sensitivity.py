"""V-CA v1 -- independent re-derivation of M110's 61.0 %/58.7 % edge-chroma figure,
and a sensitivity test of the choice that produced it.

Reads the M110 renders that fact 1589 was measured on.  Shares no code with
`ca_overshoot.py`: edge definition, gradient stencil and band construction are
re-implemented here.  Prints, per subject:

  * the band profile of mean |R-Y| (band 0 = strong edge, band k = k px out)
  * the "edge-localised chroma excess" fall, (b0-bK)_off -> (b0-bK)_on, for
    EVERY choice of baseline band K -- because K is a free parameter of the
    statistic and M110 reported only K = 5
  * the raw fall at band 0 and the WHOLE-FRAME fall, which are the two numbers
    an owner-facing claim has to sit between
  * the green/blue footprint of a correction advertised as red-only
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
DN_PER_LEVEL = 257.0
NBAND = 11


def luma(f):
    return 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]


def ry(f):
    return f[..., 0] - luma(f)


def grad_sobelish(y):
    """Different stencil from ca_overshoot.py's [-1,0,1] sum: 3x3 Sobel magnitude."""
    gy = np.zeros_like(y); gx = np.zeros_like(y)
    gx[1:-1, 1:-1] = (y[:-2, 2:] + 2*y[1:-1, 2:] + y[2:, 2:]
                      - y[:-2, :-2] - 2*y[1:-1, :-2] - y[2:, :-2])
    gy[1:-1, 1:-1] = (y[2:, :-2] + 2*y[2:, 1:-1] + y[2:, 2:]
                      - y[:-2, :-2] - 2*y[:-2, 1:-1] - y[:-2, 2:])
    return np.hypot(gx, gy)


def dilate(m):
    o = m.copy()
    o[1:, :] |= m[:-1, :]; o[:-1, :] |= m[1:, :]
    o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    return o


def run(subject):
    off = tifffile.imread(str(ROOT / subject / "default.tif"))
    on = tifffile.imread(str(ROOT / subject / "ca.tif"))
    assert off.shape == on.shape and off.dtype == np.uint16
    print(f"\n===== {subject}  shape={off.shape} dtype={off.dtype} =====")

    fo = off.astype(np.float32); fn = on.astype(np.float32)
    d_off = ry(fo); d_on = ry(fn)
    yo = luma(fo)

    print(f"  WHOLE FRAME mean|R-Y|  off {np.abs(d_off).mean():9.1f} DN"
          f"   on {np.abs(d_on).mean():9.1f} DN"
          f"   -> {(np.abs(d_on).mean()/np.abs(d_off).mean()-1)*100:+7.2f}%")

    g = grad_sobelish(yo)
    thr = float(np.percentile(g[::7, ::7], 98.0))
    core = g >= thr
    grown = [core]
    for _ in range(1, NBAND):
        grown.append(dilate(grown[-1]))

    prof = []
    for k in range(NBAND):
        band = grown[k] if k == 0 else (grown[k] & ~grown[k-1])
        n = int(band.sum())
        mo = float(np.abs(d_off[band]).mean()); mn = float(np.abs(d_on[band]).mean())
        prof.append((k, n, mo, mn))
        print(f"   band {k:2d}  n={n:9d}  off {mo:8.1f}  on {mn:8.1f}"
              f"   raw {100*(mn-mo)/mo:+7.2f}%")

    b0o, b0n = prof[0][2], prof[0][3]
    print("   'edge-localised chroma excess' fall, by BASELINE BAND choice K:")
    for k in range(1, NBAND):
        exo = b0o - prof[k][2]; exn = b0n - prof[k][3]
        print(f"     K={k:2d}  excess off {exo:8.1f} -> on {exn:8.1f}"
              f"   FALL {100*(1-exn/exo):7.2f}%"
              f"   peak/base {b0o/prof[k][2]:6.3f} -> {b0n/prof[k][3]:6.3f}")

    for ci, nm in ((0, "R"), (1, "G"), (2, "B")):
        d = fn[..., ci] - fo[..., ci]
        chg = float((d != 0).mean() * 100)
        print(f"   plane {nm}: changed {chg:6.2f}% of px   mean|d| {np.abs(d).mean():8.2f} DN"
              f"  ({np.abs(d).mean()/DN_PER_LEVEL:6.3f} lv)   max|d| {np.abs(d).max():8.0f} DN"
              f"  ({np.abs(d).max()/DN_PER_LEVEL:6.2f} lv)")
    dr = np.abs(fn[..., 0] - fo[..., 0]); dg = np.abs(fn[..., 1] - fo[..., 1])
    print(f"   mean|dG| / mean|dR| = {dg.mean()/dr.mean():.4f}")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        run(s)
