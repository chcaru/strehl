"""R4: half-stack noise per unit level in smooth and in textured bright
areas, by scale.

  python -X utf8 noise-by-class.py CLASSES.tif ODD.tif EVEN.tif

CLASSES.tif (a render that is not one of the two scored halves; the full
default render was used) defines the classes from its green plane: bright
is above the 40th percentile of the 2 px smoothed level; textured is the top
30 % of bright pixels by local high-pass energy over level squared (4 px
window), smooth the bottom 30 %.

The noise is the odd-minus-even difference of the two half-stack renders,
green, split into bands between Gaussians of sigma 0, 1, 2, 4, 8 px, squared
and divided by the local level (shot noise scales with level). Printed per
band: the textured and the smooth figure and their ratio.

Fooled by: in textured areas the difference also holds what the halves'
elections did differently with real detail, so the textured figure is an
upper bound on noise there; the smooth figure is not exposed to that.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'a7cr-full-potential-2026-11-14'))
import fp


def main():
    dev = fp.DEV

    def load(f):
        return torch.from_numpy(tifffile.imread(f)[..., 1].astype(np.float32)).to(dev)

    cls, odd, even = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
    g = fp.gauss(cls, 2.0)
    hp = fp.gauss((cls - g) ** 2, 4.0) / g.clamp(min=50.0) ** 2
    gl = g.flatten()[::97]
    bright = g > torch.quantile(gl, 0.40)
    hb = hp[bright].flatten()[::97]
    classes = {'textured': bright & (hp >= torch.quantile(hb, 0.70)), 'smooth': bright & (hp <= torch.quantile(hb, 0.30))}
    d = odd - even
    lvl = fp.gauss(0.5 * (odd + even), 3.0).clamp(min=50.0)
    sig = [0.0, 1.0, 2.0, 4.0, 8.0]
    prev = d
    for lo, hi in zip(sig[:-1], sig[1:]):
        nxt = fp.gauss(d, hi)
        band = prev - nxt
        prev = nxt
        t = float(((band ** 2) / lvl)[classes['textured']].mean())
        s = float(((band ** 2) / lvl)[classes['smooth']].mean())
        print(f'half-stack noise per unit level, green, scale {lo:g}-{hi:g} px: textured {t:.4f}, smooth {s:.4f}, smooth / textured {s / t:.2f}')


if __name__ == '__main__':
    with torch.no_grad():
        main()
