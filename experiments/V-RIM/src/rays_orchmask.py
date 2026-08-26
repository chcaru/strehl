"""Does the coffee-bean ring survive when the rays are anchored on ORCH'S mask?

The mask overlay shows my Otsu segmentation swallows the dim lower-left corner
of the sweep, 7.7 percent of frame at 48061 DN against a 57944 DN far field.
ORCH's mask does not. If my ring at t=34 px were an artifact of my own
segmentation defect, replacing my mask with ORCH's would remove it.

This runs the identical registered-ray pipeline on ORCH's filled mask.
"""
import gc, sys
from pathlib import Path
import numpy as np
from scipy import ndimage
import tifffile

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum
from ringstat import ring_and_null

TS = np.arange(-80.0, 320.0 + 1e-9, 0.5, dtype=np.float32)
GRID = np.arange(-40.0, 300.0 + 1e-9, 1.0, dtype=np.float32)
DT, NRAY, CHUNK, R_FRINGE = 0.5, 2500, 250, 20
SRC = r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"


def orch_mask(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, a.dtype
    mc = a.astype(np.float32).mean(axis=2)
    del a; gc.collect()
    lo, hi = np.percentile(mc, 5), np.percentile(mc, 95)
    d = mc < 0.5 * (lo + hi)
    del mc; gc.collect()
    lab, n = ndimage.label(d)
    sz = ndimage.sum(d, lab, range(1, n + 1))
    m = lab == (int(np.argmax(sz)) + 1)
    del lab, d; gc.collect()
    return ndimage.binary_fill_holes(m)


def take(lum, yy, xx):
    o = np.empty(yy.shape, np.float32)
    for i in range(0, yy.shape[0], CHUNK):
        a, b = yy[i:i+CHUNK], xx[i:i+CHUNK]
        o[i:i+CHUNK] = ndimage.map_coordinates(lum, [a.ravel(), b.ravel()],
                                               order=1, mode="nearest").reshape(a.shape)
    return o


def run(lum, subject, tag):
    h, w = subject.shape
    er = ndimage.binary_erosion(subject, iterations=1, border_value=1)
    bnd = subject & ~er
    dens = ndimage.uniform_filter(bnd.astype(np.float32),
                                  size=2*R_FRINGE+1, mode="nearest")
    fi = dens * (2*R_FRINGE+1)**2 / (2.0*R_FRINGE+1.0)
    sd = (ndimage.distance_transform_edt(~subject)
          - ndimage.distance_transform_edt(subject)).astype(np.float32)
    sm = ndimage.gaussian_filter(sd, 4.0)
    gy, gx = np.gradient(sm); del sm; gc.collect()
    n = np.sqrt(gy*gy + gx*gx) + 1e-6
    gy = (gy/n).astype(np.float32); gx = (gx/n).astype(np.float32); del n
    ys, xs = np.nonzero(bnd)
    keep = (ys > 350) & (ys < h-350) & (xs > 350) & (xs < w-350)
    ys, xs = ys[keep], xs[keep]
    fv = fi[ys, xs].astype(np.float32); del fi, bnd, dens; gc.collect()
    q = np.percentile(fv, [25, 75])
    print(f"  {tag}: boundary pts {ys.size}, fringe p25={q[0]:.3f} p75={q[1]:.3f}")
    for name, sel in (("ALL", np.ones(fv.shape, bool)),
                      ("STRAIGHTEST q", fv <= q[0]),
                      ("MOST FRINGED q", fv >= q[1])):
        idx = np.nonzero(sel)[0]
        rng = np.random.default_rng(7)
        if idx.size > NRAY:
            idx = rng.choice(idx, NRAY, replace=False)
        yy = ys[idx][:, None].astype(np.float32) + gy[ys[idx], xs[idx]][:, None]*TS[None, :]
        xx = xs[idx][:, None].astype(np.float32) + gx[ys[idx], xs[idx]][:, None]*TS[None, :]
        ok = ((yy > 1) & (yy < h-2) & (xx > 1) & (xx < w-2)).all(axis=1)
        yy, xx = yy[ok], xx[ok]
        s = take(sd, yy, xx)
        k2 = ~((s[:, TS > 5] < 0).any(axis=1)); del s
        yy, xx = yy[k2], xx[k2]
        v = take(lum, yy, xx); del yy, xx; gc.collect()
        inner = np.median(v[:, (TS >= -80) & (TS <= -55)], axis=1)
        outer = np.median(v[:, (TS >= 260) & (TS <= 320)], axis=1)
        half = 0.5*(inner+outer)
        cross = np.full(v.shape[0], np.nan, np.float32)
        for i in range(v.shape[0]):
            row = v[i]
            g = row > half[i] if outer[i] > inner[i] else row < half[i]
            j = int(np.argmax(g)) if g.any() else -1
            if j > 0:
                a, b = row[j-1], row[j]
                cross[i] = TS[j-1] + (0.0 if b == a else (half[i]-a)/(b-a))*DT
        okc = np.isfinite(cross) & (np.abs(cross) < 40)
        v, inner, outer, cross = v[okc], inner[okc], outer[okc], cross[okc]
        reg = np.empty((v.shape[0], GRID.size), np.float32)
        for i in range(v.shape[0]):
            reg[i] = np.interp(GRID + cross[i], TS, v[i])
        med = np.median(reg, axis=0)
        far = float(np.median(outer)); inn = float(np.median(inner))
        r, nul = ring_and_null(GRID, med, far)
        k1 = int(np.searchsorted(GRID, 1.0))
        print(f"    {name:15s} rays={v.shape[0]:5d} inner={inn:7.0f} far={far:7.0f} "
              f"edge%far={(med[k1]-far)/far*100:+7.2f} "
              f"RING {r['frac']*100:+6.2f}% @t={r['t_peak']:.0f} "
              f"(null {nul['frac']*100:.2f}%)")
        print("      ", " ".join(f"{int(t)}:{med[int(np.searchsorted(GRID,t))]:.0f}"
                                 for t in (0,10,20,30,34,40,50,60,70,85,100,120,150,200,280)))
        del v, reg; gc.collect()


shape, lum = load_lum(Path(SRC), "G")
print("coffee-bean merged render, registered rays, two different masks\n")
om = orch_mask(SRC)
print(f"ORCH mask (filled) = {om.mean()*100:.2f}% of frame")
run(lum, om, "ORCH mask")
