"""Chroma smoothing of a colour-carried render, as a probe before building it:
keep green as carried, replace red and blue by green plus a Gaussian-smoothed
colour difference,

  R' = G + blur(R - G, sigma),  B' = G + blur(B - G, sigma)

so fine detail in red and blue comes from (measured) green and only the
colour difference is averaged. Works on linear 16-bit TIFFs; writes
IN-<tag>.tif beside each input.

  python -X utf8 chroma-smooth.py SIGMA TAG A.tif [B.tif ...]

Fooled by: colour detail finer than sigma (a red-on-green texture) is lost
by construction; compare-colour's chroma coherence shows how much.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sigma, tag = float(sys.argv[1]), sys.argv[2]
for p in map(Path, sys.argv[3:]):
    x = tifffile.imread(p).astype(np.float32)
    g = x[..., 1]
    out = x.copy()
    for c in (0, 2):
        out[..., c] = g + gaussian_filter(x[..., c] - g, sigma, mode='reflect')
    dst = p.with_name(f'{p.stem}-{tag}.tif')
    tifffile.imwrite(dst, np.clip(out + 0.5, 0, 65535).astype(np.uint16), photometric='rgb')
    print('wrote', dst)
