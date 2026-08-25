"""M114 r26 -- quantisation DOSE-RESPONSE for M114's only narrowed estimator.

ORCH has withdrawn the form-based triage rule ("is it absolute? is it
small-over-large?") after three refutations. Its replacement instruction is to
expand the statistic algebraically or measure it with a dose-response control.
M114's r24 clearance used neither: it was a single-dose re-run (8-bit vs 16-bit)
with a roll control. Single-dose is a weak clearance -- it cannot show WHERE the
estimator breaks, only that it had not broken at that one point.

This sweeps quantisation depth on the NCC localisation used by r10a and finds
the breaking point, and in doing so independently tests V-M113's threshold
("immunity ends near 12 distinct levels per fitted window, inverts at 2") on a
DIFFERENT estimator and DIFFERENT data than V-M113 used.

Ground truth is external: the M110 contact-sheet filenames encode each crop's
origin, and r24d confirmed the full-depth estimator recovers them exactly.

Quantisation models the real hazard: floor to N uniform levels across the
container range, which is what `>> 8` does, NOT rounding and NOT dither.

REGISTERED PREDICTION (written before running):
  P1  position error is exactly 0 at high dose and grows abruptly below some
      realised-level count; a graceful linear degradation would refute the
      "immunity then collapse" picture.
  P2  if V-M113's threshold transfers, the last clean dose sits near 12
      REALISED distinct levels inside the matched window -- not 12 nominal
      quantisation levels, which are different numbers.
  P3  r10a's operating point (nominal 256) sits far above the break, with
      margin quantified in realised levels rather than asserted.
COMMISSIONING: the estimator must recover a planted +3 px roll at full depth.
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
OUT = r"C:\dev\strehl-out\M114-ca-verify\r26.json"
HALF = 320
DOSES = [65536, 4096, 1024, 256, 64, 32, 16, 12, 8, 6, 4, 3, 2]


def bands(mask, axis, frac):
    occ = mask.mean(axis=axis); on = occ > frac
    out, s = [], None
    for i, v in enumerate(on):
        if v and s is None: s = i
        elif not v and s is not None: out.append((s, i)); s = None
    if s is not None: out.append((s, len(on)))
    return [b for b in out if b[1] - b[0] > 40]


def tile_of(path):
    sheet = np.asarray(Image.open(path).convert("RGB"))
    nb = np.any(sheet != np.array([16, 16, 16], np.uint8), axis=2)
    y0, y1 = bands(nb, 1, 0.5)[0]
    x0, x1 = bands(nb[y0:y1], 0, 0.5)[0]
    t = sheet[y0:y1, x0:x1]
    same = np.all(t[:, 1:] == t[:, :-1], axis=(0, 2))
    runs, cur = [], 1
    for s in same:
        if s: cur += 1
        else: runs.append(cur); cur = 1
    runs.append(cur)
    v, c = np.unique(runs, return_counts=True)
    z = int(v[np.argmax(c)])
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
    den = np.sqrt(np.maximum(s2 - s1 * s1 / n, 1e-9)) * np.sqrt(np.sum(t0 * t0))
    ncc = num / den
    y, x = np.unravel_index(np.argmax(ncc), ncc.shape)
    return float(ncc[y, x]), int(x), int(y)


def quantise(a, n):
    if n >= 65536:
        return a
    step = 65536.0 / n
    return (np.floor(a.astype(np.float64) / step) * step).astype(np.float64)


raw = tifffile.imread(REND)
assert raw.dtype == np.uint16
print("haystack %s uint16, %d distinct levels" % (str(raw.shape), np.unique(raw).size))

# commissioning: can the estimator go red?
t0 = tile_of(sorted(glob.glob(PAT))[0])
sub = raw[0:HALF * 2, 1400 - HALF:1400 + HALF]
_, xa, _ = ncc_locate(t0, sub)
_, xb, _ = ncc_locate(t0, np.roll(sub, 3, axis=1))
comm = (xb - xa) == 3
print("commissioning: planted +3 px roll recovered as %+d px  %s"
      % (xb - xa, "OK" if comm else "FAILED"))
assert comm, "estimator not commissioned"

rows = []
for p in sorted(glob.glob(PAT)):
    base = os.path.basename(p)
    gx, gy = base.rsplit("-", 1)[1].split(".")[0].split("x")
    gx, gy = int(gx), int(gy)
    tile = tile_of(p)
    th, tw = tile.shape[:2]
    oy = max(0, gy - HALF); ox = max(0, gx - HALF)
    sub = raw[oy:gy + HALF, ox:gx + HALF]
    ex, ey = gx - ox, gy - oy
    print()
    print("%s  tile %dx%d  truth in crop=(%d,%d)" % (base, tw, th, ex, ey))
    for n in DOSES:
        q = quantise(sub, n)
        win = q[ey:ey + th, ex:ex + tw]
        realised = int(np.unique(win).size)
        ncc, x, y = ncc_locate(tile, q)
        err = float(np.hypot(x - ex, y - ey))
        rows.append(dict(needle=base, nominal=n, realised=realised,
                         err=err, ncc=ncc, exact=bool(err == 0.0)))
        print("   nominal %6d  realised %6d  err %8.2f px  ncc %.4f  %s"
              % (n, realised, err, ncc, "exact" if err == 0 else ""))

json.dump(dict(rows=rows, commissioned=bool(comm)), open(OUT, "w"), indent=1)
print()
print("wrote", OUT)
