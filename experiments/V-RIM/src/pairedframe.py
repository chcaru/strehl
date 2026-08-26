"""Pixel-paired merge-versus-single-frame test (memory-lean).

Ray set built ONCE from the merge's mask. Both images sampled along identical
rays, so segmentation, ray choice and sampling are held exactly constant and
only the source file differs.

Prints the 10-90 edge width of every image, because a defocused single frame
cannot resolve a 34 px feature and would fake a clean negative. The frames span
the bracket so the scene is interrogated at several focus positions.
"""
import gc, glob, sys
from pathlib import Path
import numpy as np
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment
from vrim_rays import fringe_index

T0, T1, DT = -80.0, 320.0, 0.5
TS = np.arange(T0, T1 + 1e-9, DT, dtype=np.float32)
GRID = np.arange(-40.0, 300.0 + 1e-9, 1.0, dtype=np.float32)
MERGE = r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"
NRAY = 2500
CHUNK = 250


def sample_rays(lum, yy, xx):
    out = np.empty(yy.shape, np.float32)
    for i in range(0, yy.shape[0], CHUNK):
        ys = yy[i:i + CHUNK]; xs = xx[i:i + CHUNK]
        out[i:i + CHUNK] = ndimage.map_coordinates(
            lum, [ys.ravel(), xs.ravel()], order=1,
            mode="nearest").reshape(ys.shape).astype(np.float32)
    return out


def ray_geometry(lum, seed, straight_only):
    subject, backdrop, diag = segment(lum)
    h, w = subject.shape
    fi, bnd = fringe_index(subject)
    sd = (ndimage.distance_transform_edt(~subject)
          - ndimage.distance_transform_edt(subject)).astype(np.float32)
    sm = ndimage.gaussian_filter(sd, 4.0)
    gy, gx = np.gradient(sm)
    del sm; gc.collect()
    n = np.sqrt(gy * gy + gx * gx) + 1e-6
    gy = (gy / n).astype(np.float32); gx = (gx / n).astype(np.float32)
    del n; gc.collect()
    ys, xs = np.nonzero(bnd)
    keep = (ys > 350) & (ys < h - 350) & (xs > 350) & (xs < w - 350)
    ys, xs = ys[keep], xs[keep]
    fv = fi[ys, xs].astype(np.float32)
    del fi, bnd; gc.collect()
    q25 = float(np.percentile(fv, 25))
    sel = np.nonzero(fv <= q25)[0] if straight_only else np.arange(fv.size)
    rng = np.random.default_rng(seed)
    if sel.size > NRAY:
        sel = rng.choice(sel, NRAY, replace=False)
    yy = ys[sel][:, None].astype(np.float32) + gy[ys[sel], xs[sel]][:, None] * TS[None, :]
    xx = xs[sel][:, None].astype(np.float32) + gx[ys[sel], xs[sel]][:, None] * TS[None, :]
    del gy, gx; gc.collect()
    ok = ((yy > 1) & (yy < h - 2) & (xx > 1) & (xx < w - 2)).all(axis=1)
    yy, xx = yy[ok], xx[ok]
    s = sample_rays(sd, yy, xx)
    del sd; gc.collect()
    keep2 = ~((s[:, TS > 5] < 0).any(axis=1))
    del s; gc.collect()
    return yy[keep2], xx[keep2], diag, q25


def crossings(v):
    inner = np.median(v[:, (TS >= -80) & (TS <= -55)], axis=1)
    outer = np.median(v[:, (TS >= 260) & (TS <= 320)], axis=1)
    half = 0.5 * (inner + outer)
    cross = np.full(v.shape[0], np.nan, np.float32)
    for i in range(v.shape[0]):
        row = v[i]
        g = row > half[i] if outer[i] > inner[i] else row < half[i]
        j = int(np.argmax(g)) if g.any() else -1
        if j <= 0:
            continue
        a, b = row[j - 1], row[j]
        f = 0.0 if b == a else (half[i] - a) / (b - a)
        cross[i] = TS[j - 1] + f * DT
    return inner, outer, cross


def register(v, cross):
    reg = np.empty((v.shape[0], GRID.size), np.float32)
    for i in range(v.shape[0]):
        reg[i] = np.interp(GRID + cross[i], TS, v[i])
    return np.median(reg, axis=0)


def ring_of(med, far, tmax=120.0):
    i0 = int(np.searchsorted(GRID, 0.0))
    seg, g2 = med[i0:], GRID[i0:]
    best = None
    for i in range(1, len(seg) - 1):
        if seg[i] >= seg[i - 1] and seg[i] > seg[i + 1] and g2[i] <= tmax:
            p = float(seg[i] - seg[i + 1:].min())
            if best is None or p > best[2]:
                best = (float(g2[i]), float(seg[i]), p)
    return None if best is None else dict(t=best[0], prom=best[2], frac=best[2] / far)


def edge_width(med, inner, far):
    def firstx(thr):
        g = med > thr
        j = int(np.argmax(g)) if g.any() else -1
        if j <= 0:
            return np.nan
        a, b = med[j - 1], med[j]
        return float(GRID[j - 1] + (0.0 if b == a else (thr - a) / (b - a)))
    return firstx(inner + 0.9 * (far - inner)) - firstx(inner + 0.1 * (far - inner))


def main():
    shape, lum_m = load_lum(Path(MERGE), "G")
    cands = [("MERGE", MERGE)]
    for p in sorted(glob.glob(r"C:\dev\strehl-out\V-RIM\cb-frame*-lin.tif")):
        if Path(p).stat().st_size > 1_000_000:
            cands.append((Path(p).stem.replace("cb-", "").replace("-lin", "").upper(), p))
    print(f"images under test: {[c[0] for c in cands]}")

    for straight_only in (True, False):
        tag = "STRAIGHTEST QUARTILE" if straight_only else "ALL RAYS"
        yy, xx, diag, q25 = ray_geometry(lum_m, 7, straight_only)
        print(f"\n### pixel-paired, ray set from the MERGE mask, {tag}")
        print(f"    rays={yy.shape[0]}  merge subj={diag['subject_frac']*100:.2f}%  fi_p25={q25:.3f}")
        print("\n  image        far DN   inner DN  10-90 edge   ring t   ring %   t=+1 %far")
        for lab, path in cands:
            _, lum = load_lum(Path(path), "G")
            v = sample_rays(lum, yy, xx)
            del lum; gc.collect()
            inner, outer, cross = crossings(v)
            ok = np.isfinite(cross) & (np.abs(cross) < 40)
            med = register(v[ok], cross[ok])
            del v; gc.collect()
            far = float(np.median(outer[ok])); inn = float(np.median(inner[ok]))
            r = ring_of(med, far); ew = edge_width(med, inn, far)
            k1 = int(np.searchsorted(GRID, 1.0))
            print(f"  {lab:11s} {far:8.0f} {inn:10.0f} {ew:11.1f} "
                  f"{(r['t'] if r else float('nan')):8.0f} {(r['frac']*100 if r else float('nan')):+8.2f} "
                  f"{(med[k1]-far)/far*100:+11.2f}")
            print("        profile:", " ".join(
                f"{int(t)}:{med[int(np.searchsorted(GRID,t))]:.0f}"
                for t in (0, 5, 10, 20, 30, 34, 40, 50, 70, 100, 150, 200, 280)))
        del yy, xx; gc.collect()


main()
