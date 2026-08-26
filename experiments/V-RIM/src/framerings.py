"""Does any SINGLE frame carry the ring, or does the merge create it?

Each image is segmented and registered on its OWN terms, so focus breathing and
mask size differences cannot leak in. The 10-90 edge width is printed for every
image ABOVE the ring verdict, because a frame whose silhouette is defocused
cannot resolve a 34 px feature and would read as a clean negative for a reason
that has nothing to do with the merge.

Ring search is capped at t<=120 px to exclude coffee-bean's cast-shadow
boundary near t=159, which is not the feature under test.
"""
import gc, glob, sys
from pathlib import Path
import numpy as np
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment
from vrim_rays import fringe_index

TS = np.arange(-80.0, 320.0 + 1e-9, 0.5, dtype=np.float32)
GRID = np.arange(-40.0, 300.0 + 1e-9, 1.0, dtype=np.float32)
DT = 0.5
NRAY = 2500
CHUNK = 250


def sample(lum, yy, xx):
    out = np.empty(yy.shape, np.float32)
    for i in range(0, yy.shape[0], CHUNK):
        a, b = yy[i:i + CHUNK], xx[i:i + CHUNK]
        out[i:i + CHUNK] = ndimage.map_coordinates(
            lum, [a.ravel(), b.ravel()], order=1, mode="nearest").reshape(a.shape)
    return out


def profile(path, straight_only, seed=7):
    shape, lum = load_lum(Path(path), "G")
    subject, backdrop, diag = segment(lum)
    h, w = subject.shape
    fi, bnd = fringe_index(subject)
    sd = (ndimage.distance_transform_edt(~subject)
          - ndimage.distance_transform_edt(subject)).astype(np.float32)
    sm = ndimage.gaussian_filter(sd, 4.0)
    gy, gx = np.gradient(sm); del sm; gc.collect()
    n = np.sqrt(gy * gy + gx * gx) + 1e-6
    gy = (gy / n).astype(np.float32); gx = (gx / n).astype(np.float32); del n
    ys, xs = np.nonzero(bnd)
    keep = (ys > 350) & (ys < h - 350) & (xs > 350) & (xs < w - 350)
    ys, xs = ys[keep], xs[keep]
    fv = fi[ys, xs].astype(np.float32); del fi, bnd; gc.collect()
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
    s = sample(sd, yy, xx); del sd; gc.collect()
    k2 = ~((s[:, TS > 5] < 0).any(axis=1)); del s; gc.collect()
    yy, xx = yy[k2], xx[k2]
    v = sample(lum, yy, xx); del lum, subject, backdrop; gc.collect()
    inner = np.median(v[:, (TS >= -80) & (TS <= -55)], axis=1)
    outer = np.median(v[:, (TS >= 260) & (TS <= 320)], axis=1)
    half = 0.5 * (inner + outer)
    cross = np.full(v.shape[0], np.nan, np.float32)
    for i in range(v.shape[0]):
        row = v[i]
        g = row > half[i] if outer[i] > inner[i] else row < half[i]
        j = int(np.argmax(g)) if g.any() else -1
        if j > 0:
            a, b = row[j - 1], row[j]
            cross[i] = TS[j - 1] + (0.0 if b == a else (half[i] - a) / (b - a)) * DT
    okc = np.isfinite(cross) & (np.abs(cross) < 40)
    v, inner, outer, cross = v[okc], inner[okc], outer[okc], cross[okc]
    reg = np.empty((v.shape[0], GRID.size), np.float32)
    for i in range(v.shape[0]):
        reg[i] = np.interp(GRID + cross[i], TS, v[i])
    med = np.median(reg, axis=0)
    return med, float(np.median(inner)), float(np.median(outer)), v.shape[0], diag


def ring(med, far, tmax=120.0):
    i0 = int(np.searchsorted(GRID, 0.0)); seg, g2 = med[i0:], GRID[i0:]
    best = None
    for i in range(1, len(seg) - 1):
        if seg[i] >= seg[i - 1] and seg[i] > seg[i + 1] and g2[i] <= tmax:
            p = float(seg[i] - seg[i + 1:].min())
            if best is None or p > best[2]:
                best = (float(g2[i]), float(seg[i]), p)
    return best


def ew(med, inner, far):
    def fx(thr):
        g = med > thr
        j = int(np.argmax(g)) if g.any() else -1
        if j <= 0:
            return np.nan
        a, b = med[j - 1], med[j]
        return float(GRID[j - 1] + (0.0 if b == a else (thr - a) / (b - a)))
    return fx(inner + 0.9 * (far - inner)) - fx(inner + 0.1 * (far - inner))


# argv: [merge.tif] [frame-glob] [prefix].  Defaults reproduce the coffee-bean run.
MERGE = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"
PAT = sys.argv[2] if len(sys.argv) > 2 else r"C:\dev\strehl-out\V-RIM\cb-frame*-lin.tif"
PFX = sys.argv[3] if len(sys.argv) > 3 else "cb-"

files = [("MERGE", MERGE)]
for p in sorted(glob.glob(PAT), key=lambda q: int("".join(c for c in Path(q).stem if c.isdigit()))):
    if Path(p).stat().st_size > 1_000_000:
        files.append((Path(p).stem.replace(PFX, "").replace("-lin", "").upper(), p))
print(f"# merge: {MERGE}")
print(f"# frames: {len(files)-1} matching {PAT}")

for straight_only in (True, False):
    print(f"\n### per-image mask and registration, "
          f"{'STRAIGHTEST QUARTILE' if straight_only else 'ALL RAYS'}, "
          f"ring window t<=120 px")
    print("  image      rays   subj%   inner    far   10-90 edge   ring t   ring %")
    for lab, path in files:
        med, inn, far, n, diag = profile(path, straight_only)
        r = ring(med, far); e = ew(med, inn, far)
        print(f"  {lab:9s} {n:6d} {diag['subject_frac']*100:7.2f} {inn:7.0f} {far:6.0f} "
              f"{e:11.1f} {(r[0] if r else float('nan')):8.0f} "
              f"{(r[2]/far*100 if r else float('nan')):+8.2f}")
        print("      profile:", " ".join(
            f"{int(t)}:{med[int(np.searchsorted(GRID,t))]:.0f}"
            for t in (0, 5, 10, 20, 30, 34, 40, 50, 60, 70, 85, 100, 120, 150, 200, 280)))
        gc.collect()
