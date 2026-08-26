"""Why did the silhouette rule decline flower-bud-with-background-fern-cpl?

Instrument, not a fix. Prints the population sizes at each stage of
silhouette_score so the failure is attributed rather than guessed at. Run on a
subject the rule SUCCEEDS on as a control, so a small number is only damning if
the working subject's number is large.
"""

import sys
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi
import tifffile


def read(p):
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p}: {a.dtype}"
    return a


def trace(p: Path) -> None:
    img = read(p)
    lum = img.astype(np.float32).mean(2)
    small = lum[::4, ::4]
    rough = ndi.uniform_filter(small ** 2, 9) - ndi.uniform_filter(small, 9) ** 2
    np.maximum(rough, 0, out=rough)
    rough = np.sqrt(rough)
    smooth = rough < np.percentile(rough, 40)
    vals = small[smooth]
    hist, edges = np.histogram(vals, bins=128)
    level = 0.5 * (edges[hist.argmax()] + edges[hist.argmax() + 1])
    tol = max(float(vals.std()), 1.0) * 2.0
    near = (np.abs(small - level) < tol)
    bg0 = near & smooth
    bgc = ndi.binary_closing(bg0, np.ones((5, 5)))
    bgo = ndi.binary_opening(bgc, np.ones((5, 5)))
    b = ndi.binary_dilation(bgo, np.ones((3, 3))) ^ ndi.binary_erosion(bgo, np.ones((3, 3)))
    textured = rough > np.percentile(rough, 75)
    bt = b & ndi.binary_dilation(textured, np.ones((7, 7)))
    n = small.size
    print(f"\n{p.stem}")
    print(f"  decimated       : {small.shape}  ({n} px)")
    print(f"  level / tol     : {level:.1f} / {tol:.1f}   (lum range {small.min():.0f}-{small.max():.0f})")
    print(f"  smooth          : {smooth.sum()/n:7.3%}")
    print(f"  near level      : {near.sum()/n:7.3%}")
    print(f"  bg = near&smooth: {bg0.sum()/n:7.3%}")
    print(f"  after closing   : {bgc.sum()/n:7.3%}")
    print(f"  after opening   : {bgo.sum()/n:7.3%}   <- 5x5 at 4x decim = 20 px full-res")
    print(f"  boundary        : {b.sum()/n:7.3%}")
    print(f"  & near textured : {bt.sum()/n:7.3%}   <- THE SCORE'S SOURCE")


for arg in sys.argv[1:]:
    trace(Path(arg))
