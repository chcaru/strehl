"""Attack 7: does demosaic interpolation create the veil or the ring?

The binned render is genuinely un-interpolated -- one RGB sample per 2x2 Bayer
quad, no interpolation kernel anywhere near the silhouette. It is half
resolution, so a distance of d binned px is the SAME PHYSICAL DISTANCE as 2d
demosaiced px. Profiles are therefore compared on a common physical axis in
units of demosaiced pixels.

If demosaic interpolation manufactured the artifacts, the binned profile is
flat where the demosaiced one dips. Full profiles print above every verdict.
"""
import gc, sys
from pathlib import Path
import numpy as np
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment
from vrim_rays import fringe_index

NRAY = 2500
CHUNK = 250


def sample(lum, yy, xx):
    out = np.empty(yy.shape, np.float32)
    for i in range(0, yy.shape[0], CHUNK):
        a, b = yy[i:i + CHUNK], xx[i:i + CHUNK]
        out[i:i + CHUNK] = ndimage.map_coordinates(
            lum, [a.ravel(), b.ravel()], order=1, mode="nearest").reshape(a.shape)
    return out


def profile(path, scale, seed=11):
    """scale: multiply this image's pixel distances by `scale` to get demosaic px."""
    ts = np.arange(-80.0, 320.0 + 1e-9, 0.5, dtype=np.float32) / scale
    grid = np.arange(-40.0, 300.0 + 1e-9, 1.0, dtype=np.float32) / scale
    shape, lum = load_lum(Path(path), "G")
    subject, backdrop, diag = segment(lum)
    h, w = subject.shape
    fi, bnd = fringe_index(subject)
    sd = (ndimage.distance_transform_edt(~subject)
          - ndimage.distance_transform_edt(subject)).astype(np.float32)
    sm = ndimage.gaussian_filter(sd, 4.0 / scale)
    gy, gx = np.gradient(sm); del sm; gc.collect()
    n = np.sqrt(gy * gy + gx * gx) + 1e-6
    gy = (gy / n).astype(np.float32); gx = (gx / n).astype(np.float32); del n
    ys, xs = np.nonzero(bnd)
    m = int(350 / scale)
    keep = (ys > m) & (ys < h - m) & (xs > m) & (xs < w - m)
    ys, xs = ys[keep], xs[keep]
    fv = fi[ys, xs].astype(np.float32); del fi, bnd; gc.collect()
    sel = np.nonzero(fv <= float(np.percentile(fv, 25)))[0]
    rng = np.random.default_rng(seed)
    if sel.size > NRAY:
        sel = rng.choice(sel, NRAY, replace=False)
    yy = ys[sel][:, None].astype(np.float32) + gy[ys[sel], xs[sel]][:, None] * ts[None, :]
    xx = xs[sel][:, None].astype(np.float32) + gx[ys[sel], xs[sel]][:, None] * ts[None, :]
    del gy, gx; gc.collect()
    ok = ((yy > 1) & (yy < h - 2) & (xx > 1) & (xx < w - 2)).all(axis=1)
    yy, xx = yy[ok], xx[ok]
    s = sample(sd, yy, xx); del sd; gc.collect()
    k2 = ~((s[:, ts > 5 / scale] < 0).any(axis=1)); del s; gc.collect()
    yy, xx = yy[k2], xx[k2]
    v = sample(lum, yy, xx); del lum, subject, backdrop; gc.collect()
    inner = np.median(v[:, ts <= -55 / scale], axis=1)
    outer = np.median(v[:, ts >= 260 / scale], axis=1)
    half = 0.5 * (inner + outer)
    cross = np.full(v.shape[0], np.nan, np.float32)
    for i in range(v.shape[0]):
        row = v[i]
        g = row < half[i] if inner[i] < outer[i] else row > half[i]
        g = row > half[i] if outer[i] > inner[i] else row < half[i]
        j = int(np.argmax(g)) if g.any() else -1
        if j > 0:
            a, b = row[j - 1], row[j]
            cross[i] = ts[j - 1] + (0.0 if b == a else (half[i] - a) / (b - a)) * (ts[1] - ts[0])
    okc = np.isfinite(cross) & (np.abs(cross) < 40 / scale)
    v, cross = v[okc], cross[okc]
    reg = np.empty((v.shape[0], grid.size), np.float32)
    for i in range(v.shape[0]):
        reg[i] = np.interp(grid + cross[i], ts, v[i])
    med = np.median(reg, axis=0)
    far = float(np.median(med[grid * scale >= 260]))
    return grid * scale, med, far, v.shape[0], diag


PAIRS = [("coffee-bean",
          r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif",
          r"C:\dev\strehl-out\V-RIM\cb-binned.tif"),
         ("flower-bud-alone-cpl",
          r"C:\dev\strehl-out\ORCH-rim\fb-1cacb61-lin.tif",
          r"C:\dev\strehl-out\V-RIM\fb-binned.tif")]
SHOW = [0, 5, 10, 20, 30, 40, 50, 70, 100, 140, 200, 280]

for name, dem, bin_ in PAIRS:
    print(f"\n=== {name} ===")
    rows = {}
    for lab, path, sc in (("DEMOSAIC", dem, 1.0), ("BINNED", bin_, 2.0)):
        g, med, far, n, diag = profile(path, sc)
        rows[lab] = (g, med, far)
        print(f"  {lab:9s} rays={n:5d} subj={diag['subject_frac']*100:6.2f}% far={far:7.0f}")
        print("     v/far %:", " ".join(
            f"{t}:{med[int(np.searchsorted(g, t))] / far * 100:.1f}" for t in SHOW))
        gc.collect()
    gd, md, fd = rows["DEMOSAIC"]
    gb, mb, fb = rows["BINNED"]
    print("  --- normalised difference, DEMOSAIC minus BINNED, in points of far field ---")
    print("     diff pts:", " ".join(
        f"{t}:{md[int(np.searchsorted(gd, t))] / fd * 100 - mb[int(np.searchsorted(gb, t))] / fb * 100:+.1f}"
        for t in SHOW))
    nd, nb = md / fd * 100, mb / fb * 100
    for lo, hi in ((0, 4), (0, 20), (20, 60), (60, 140)):
        a = float(np.mean(nd[(gd >= lo) & (gd <= hi)]))
        b = float(np.mean(nb[(gb >= lo) & (gb <= hi)]))
        print(f"     band {lo:3d}-{hi:3d} px:  demosaic {a:6.2f}%  binned {b:6.2f}%  "
              f"bias {a - b:+.2f} pts")
    np.savez(rf"C:\dev\strehl-out\V-RIM\attack7-{name}.npz",
             gd=gd, md=md, fd=fd, gb=gb, mb=mb, fb=fb)
