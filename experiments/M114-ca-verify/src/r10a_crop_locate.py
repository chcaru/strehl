"""M114 R10a -- WHERE are M110's crops, really?  (FFT matcher, band-segmented)

ORCH's lead depends on the crop coordinates.  Its script's line 16 calls the
filename token the crop CENTRE; zoom.py:83 shows `img[y:y+w, x:x+w]`, so it is
the top-left CORNER of a w-px window, and w is unknown because the shipped
sheets do not reconstruct from zoom.py's current geometry.

Do not trust the filename.  Recover each crop's true position from its PIXELS.
Segment the sheet into tile rectangles by row/column occupancy (text rows are
sparse, tile rows are dense), detect the nearest-neighbour zoom factor from the
column run-length INSIDE a tile, decimate, then locate by FFT normalised
cross-correlation.

Bars, registered before running:
  A1  every crop localises with peak NCC > 0.99.
  A2  CONTROL: the same tile matched against a DIFFERENT subject's render must
      NOT reach that bar.  A matcher that always finds something has found
      nothing.
"""
import glob
import os

import numpy as np
import tifffile
from PIL import Image
from scipy import signal

REND = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif"
OTHER = r"C:\dev\strehl-out\M114-ca-verify\r9\off.tif"
PAT = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\ZOOM-*.png"
BAR = 0.99

img8 = (tifffile.imread(REND) >> 8).astype(np.uint8)
H, W, _ = img8.shape
RC = np.hypot(W / 2.0, H / 2.0)
print("render %d x %d   half-diagonal %.1f px" % (W, H, RC))


def bands(mask, axis, frac):
    """Maximal contiguous runs where occupancy along `axis` exceeds `frac`."""
    occ = mask.mean(axis=axis)
    on = occ > frac
    out, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i))
            s = None
    if s is not None:
        out.append((s, len(on)))
    return [b for b in out if b[1] - b[0] > 40]


def zoom_factor(t):
    same = np.all(t[:, 1:] == t[:, :-1], axis=(0, 2))
    runs, cur = [], 1
    for s in same:
        if s:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    v, c = np.unique(runs, return_counts=True)
    return int(v[np.argmax(c)])


def tile_of(path):
    sheet = np.asarray(Image.open(path).convert("RGB"))
    nb = np.any(sheet != np.array([16, 16, 16], np.uint8), axis=2)
    rb = bands(nb, 1, 0.5)          # dense rows = tile bands
    y0, y1 = rb[0]
    cb = bands(nb[y0:y1], 0, 0.5)   # dense cols within that band = tiles
    x0, x1 = cb[0]
    t = sheet[y0:y1, x0:x1]
    z = zoom_factor(t)
    d = t[z // 2::z, z // 2::z]
    return d, z, (y1 - y0), (x1 - x0)


def ncc_locate(tile, hay):
    t = tile.astype(np.float64) @ [0.2126, 0.7152, 0.0722]
    h = hay.astype(np.float64) @ [0.2126, 0.7152, 0.0722]
    th, tw = t.shape
    t0 = t - t.mean()
    num = signal.fftconvolve(h, t0[::-1, ::-1], mode="valid")
    ones = np.ones((th, tw))
    s1 = signal.fftconvolve(h, ones, mode="valid")
    s2 = signal.fftconvolve(h * h, ones, mode="valid")
    n = th * tw
    denom = np.sqrt(np.maximum(s2 - s1 * s1 / n, 1e-9)) * np.sqrt(np.sum(t0 * t0))
    ncc = num / denom
    y, x = np.unravel_index(np.argmax(ncc), ncc.shape)
    return float(ncc[y, x]), int(x), int(y)


print()
print("%-9s %9s %2s %4s %6s %7s %7s  %8s %8s %8s  %s"
      % ("crop", "label", "z", "w", "ncc", "true x", "true y",
         "r_centre", "r_min", "r_max", "vs 0.788"))
first = None
for p in sorted(glob.glob(PAT)):
    base = os.path.basename(p)
    tag = base.split("-")[4]
    lab = base.rsplit("-", 1)[1].replace(".png", "")
    tile, z, bh, bw = tile_of(p)
    if first is None:
        first = tile
    w = tile.shape[0]
    ncc, fx, fy = ncc_locate(tile, img8)
    lx, ly = (int(v) for v in lab.split("x"))
    if ncc < BAR:
        print("%-9s %9s %2d %4d %6.4f   UNLOCALISED" % (tag, lab, z, w, ncc))
        continue
    ccx, ccy = fx + tile.shape[1] / 2.0, fy + w / 2.0
    rc = np.hypot(ccx - W / 2.0, ccy - H / 2.0) / RC
    rr = [np.hypot(a - W / 2.0, b - H / 2.0) / RC
          for a, b in [(fx, fy), (fx + tile.shape[1], fy),
                       (fx, fy + w), (fx + tile.shape[1], fy + w)]]
    print("%-9s %9s %2d %4d %6.4f %7d %7d  %8.4f %8.4f %8.4f  %s   [label offset %+d,%+d]"
          % (tag, lab, z, w, ncc, fx, fy, rc, min(rr), max(rr),
             "*** OUTSIDE ***" if rc > 0.788 else "inside", fx - lx, fy - ly))

oth = (tifffile.imread(OTHER) >> 8).astype(np.uint8)
ncc, fx, fy = ncc_locate(first, oth)
print()
print("A2 CONTROL: first tile vs a DIFFERENT subject's render -> ncc %.4f (bar %.2f) -> %s"
      % (ncc, BAR, "PASS (refuses)" if ncc < BAR else "FAIL (matches anything)"))
