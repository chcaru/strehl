"""M114 r24d -- DECISIVE part of the PIL-narrowing audit.

r10a_crop_locate.py is the only M114 probe that narrowed its own data: line 33
does `(tifffile.imread(REND) >> 8).astype(np.uint8)`, discarding the low byte of
a genuine uint16 render before locating M110's crops by normalised
cross-correlation.

That was a deliberate choice, not the PIL accident -- the needle is an 8-bit PNG
contact-sheet tile, so the haystack was matched at the needle's depth. But
"deliberate" is not "harmless", and ORCH's rule is re-run rather than reason.

This re-runs the identical localisation with a FULL-DEPTH uint16 haystack and
compares the located position and the NCC peak against the 8-bit haystack.

Registered bar D1: the located (x, y) is IDENTICAL for every needle at both
depths. r10a reported positions, not photometry; if the position is unchanged
the narrowing cost r10a nothing. Any disagreement refutes r10a's localisation
and every support-split statistic that inherited it.
"""
import glob
import json
import os

import numpy as np
import tifffile
from PIL import Image
from scipy import signal

REND = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.tif"
PAT = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl\ZOOM-*.png"
OUT = r"C:\dev\strehl-out\M114-ca-verify\r24d.json"


def bands(mask, axis, frac):
    occ = mask.mean(axis=axis)
    on = occ > frac
    out, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i)); s = None
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
            runs.append(cur); cur = 1
    runs.append(cur)
    v, c = np.unique(runs, return_counts=True)
    return int(v[np.argmax(c)])


def tile_of(path):
    sheet = np.asarray(Image.open(path).convert("RGB"))
    nb = np.any(sheet != np.array([16, 16, 16], np.uint8), axis=2)
    rb = bands(nb, 1, 0.5)
    y0, y1 = rb[0]
    cb = bands(nb[y0:y1], 0, 0.5)
    x0, x1 = cb[0]
    t = sheet[y0:y1, x0:x1]
    z = zoom_factor(t)
    return t[z // 2::z, z // 2::z]


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


raw = tifffile.imread(REND)
assert raw.dtype == np.uint16, "haystack is not uint16: %s" % raw.dtype
hay8 = (raw >> 8).astype(np.uint8)          # exactly what r10a used
hay16 = raw                                  # full depth
print("haystack %s  levels: 16-bit=%d  8-bit=%d"
      % (str(raw.shape), np.unique(raw).size, np.unique(hay8).size))

rows, agree = [], True
for p in sorted(glob.glob(PAT)):
    tile = tile_of(p)
    n8, x8, y8 = ncc_locate(tile, hay8)
    n16, x16, y16 = ncc_locate(tile, hay16)
    same = (x8, y8) == (x16, y16)
    agree &= same
    rows.append(dict(needle=os.path.basename(p), tile=list(tile.shape),
                     ncc8=n8, x8=x8, y8=y8, ncc16=n16, x16=x16, y16=y16,
                     dx=x16 - x8, dy=y16 - y8, identical=same))
    print("%-42s 8bit=(%5d,%5d) ncc=%.4f | 16bit=(%5d,%5d) ncc=%.4f | d=(%d,%d) %s"
          % (os.path.basename(p)[:42], x8, y8, n8, x16, y16, n16,
             x16 - x8, y16 - y8, "SAME" if same else "*** DIFFERS ***"))

# Negative control: the bar must be able to go red. Shift the haystack by a
# known 3 px and require the recovered position to move by exactly 3.
tile = tile_of(sorted(glob.glob(PAT))[0])
_, xr, yr = ncc_locate(tile, np.roll(hay16, 3, axis=1))
_, x0, y0 = ncc_locate(tile, hay16)
ctrl = (xr - x0) == 3 and (yr - y0) == 0
print()
print("negative control: haystack rolled +3 px in x -> recovered shift (%d,%d)  %s"
      % (xr - x0, yr - y0, "CONTROL OK" if ctrl else "CONTROL FAILED"))

verdict = "D1 PASS" if (agree and ctrl) else ("D1 FAIL" if not agree else "CONTROL FAILED")
print()
print("%s  -- r10a's 8-bit narrowing changed no located position (n=%d needles)"
      % (verdict, len(rows)))
json.dump(dict(rows=rows, all_identical=bool(agree), control_ok=bool(ctrl),
               verdict=verdict), open(OUT, "w"), indent=1)
print("wrote", OUT)
