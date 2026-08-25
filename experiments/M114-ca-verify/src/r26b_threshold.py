"""M114 r26b -- what actually determines quantisation failure in localisation.

r26 produced a result that does not fit the level-count picture. On the
`specular` needle:

    nominal 4 levels -> realised 2 -> error   0.00 px   (exact)
    nominal 3 levels -> realised 2 -> error 165.34 px   (failed)

SAME needle, SAME realised distinct-level count, OPPOSITE outcome. A level count
therefore cannot be the controlling variable. The candidate mechanism is that
what matters is WHERE the quantisation decision boundary falls relative to the
image content, not how many boundaries there are.

This tests that directly: hold the level count fixed at 2 -- a pure binary
image, the most degraded case possible -- and sweep only the THRESHOLD. If the
level-count picture were right, every threshold should fail alike. If the
placement picture is right, some thresholds localise exactly and others fail
catastrophically, at constant level count.
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
OUT = r"C:\dev\strehl-out\M114-ca-verify\r26b.json"
HALF = 320


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


raw = tifffile.imread(REND)
res = {}
for want in ("specular", "wing"):
    p = [q for q in sorted(glob.glob(PAT)) if want in q][0]
    base = os.path.basename(p)
    gx, gy = base.rsplit("-", 1)[1].split(".")[0].split("x")
    gx, gy = int(gx), int(gy)
    tile = tile_of(p)
    th, tw = tile.shape[:2]
    oy, ox = max(0, gy - HALF), max(0, gx - HALF)
    sub = raw[oy:gy + HALF, ox:gx + HALF].astype(np.float64)
    ex, ey = gx - ox, gy - oy
    lum = sub @ [0.2126, 0.7152, 0.0722]
    lo, hi = float(lum.min()), float(lum.max())
    print()
    print("%s   luminance range %.0f .. %.0f   truth=(%d,%d)" % (base, lo, hi, ex, ey))
    rows = []
    for f in np.linspace(0.05, 0.95, 19):
        t = lo + f * (hi - lo)
        binary = np.where(sub > t, 1.0, 0.0)
        win = binary[ey:ey + th, ex:ex + tw]
        realised = int(np.unique(win).size)
        ncc, x, y = ncc_locate(tile, binary)
        err = float(np.hypot(x - ex, y - ey))
        rows.append(dict(frac=float(f), thresh=float(t), realised=realised,
                         err=err, ncc=ncc, exact=bool(err == 0.0)))
        print("   thresh %5.2f of range (%8.0f)  realised %d  err %8.2f px  %s"
              % (f, t, realised, err, "exact" if err == 0 else "FAIL"))
    ok = sum(r["exact"] for r in rows)
    two = [r for r in rows if r["realised"] == 2]
    two_ok = sum(r["exact"] for r in two)
    print("   -> %d/%d thresholds localise exactly" % (ok, len(rows)))
    print("   -> at realised==2 levels: %d/%d exact, %d/%d fail"
          % (two_ok, len(two), len(two) - two_ok, len(two)))
    res[base] = dict(rows=rows, exact=ok, n=len(rows), two_ok=two_ok, two_n=len(two))

print()
print("At a FIXED level count of 2, outcome varies with threshold placement:")
for k, v in res.items():
    print("   %-42s %d/%d exact at realised==2" % (k[:42], v["two_ok"], v["two_n"]))
json.dump(res, open(OUT, "w"), indent=1)
print("wrote", OUT)
