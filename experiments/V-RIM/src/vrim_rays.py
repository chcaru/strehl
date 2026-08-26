"""Assumption-free edge profile: perpendicular rays, each registered on its own
edge crossing.

Every criticism of the annulus method dies here. There is no mask placement to
get wrong, because each ray finds its own 50 percent crossing and is shifted so
that crossing sits at t=0. There is no mixing of high-curvature and low-curvature
perimeter, because rays are selected by measured local straightness. There is no
azimuthal reweighting with distance, because a ray is one direction.

Rays are also split by the local fringe density of the boundary point they start
from, which is the within-subject test of C2 with scene, exposure, magnification
and frame count all held exactly constant.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment

R_FRINGE = 20
T0, T1, DT = -80.0, 320.0, 0.5
NRAY = 4000


def fringe_index(subject):
    er = ndimage.binary_erosion(subject, iterations=1, border_value=1)
    bnd = subject & ~er
    dens = ndimage.uniform_filter(bnd.astype(np.float32),
                                  size=2 * R_FRINGE + 1, mode="nearest")
    return dens * (2 * R_FRINGE + 1) ** 2 / (2.0 * R_FRINGE + 1.0), bnd


def run(src, label, outdir, channel="G", seed=7):
    shape, lum = load_lum(src, channel)
    subject, backdrop, diag = segment(lum)
    h, w = subject.shape
    print(f"== rays {label} {shape} ch={channel} subj={diag['subject_frac']*100:.2f}%")

    fi, bnd = fringe_index(subject)
    sd = (ndimage.distance_transform_edt(~subject)
          - ndimage.distance_transform_edt(subject)).astype(np.float32)
    sm = ndimage.gaussian_filter(sd, 4.0)
    gy, gx = np.gradient(sm)
    n = np.sqrt(gy * gy + gx * gx) + 1e-6
    gy /= n
    gx /= n

    ys, xs = np.nonzero(bnd)
    keep = ((ys > 350) & (ys < h - 350) & (xs > 350) & (xs < w - 350))
    ys, xs = ys[keep], xs[keep]
    fv = fi[ys, xs]
    print(f"   boundary points usable: {ys.size}   fringe index "
          f"p10={np.percentile(fv,10):.3f} p50={np.percentile(fv,50):.3f} "
          f"p90={np.percentile(fv,90):.3f} max={fv.max():.3f}")

    ts = np.arange(T0, T1 + 1e-9, DT)
    rng = np.random.default_rng(seed)

    def sample(sel, name):
        idx = np.nonzero(sel)[0]
        if idx.size == 0:
            print(f"   {name}: no rays"); return None
        if idx.size > NRAY:
            idx = rng.choice(idx, NRAY, replace=False)
        y0 = ys[idx].astype(np.float32)
        x0 = xs[idx].astype(np.float32)
        ny = gy[ys[idx], xs[idx]]
        nx = gx[ys[idx], xs[idx]]
        yy = y0[:, None] + ny[:, None] * ts[None, :]
        xx = x0[:, None] + nx[:, None] * ts[None, :]
        ok = (yy > 1) & (yy < h - 2) & (xx > 1) & (xx < w - 2)
        good = ok.all(axis=1)
        yy, xx = yy[good], xx[good]
        if yy.shape[0] < 30:
            print(f"   {name}: only {yy.shape[0]} in-frame rays"); return None
        v = ndimage.map_coordinates(lum, [yy.ravel(), xx.ravel()], order=1,
                                    mode="nearest").reshape(yy.shape)
        s = ndimage.map_coordinates(sd, [yy.ravel(), xx.ravel()], order=1,
                                    mode="nearest").reshape(yy.shape)
        # geometric rejection only: the ray must not re-enter the subject
        outward = ts > 5
        reenter = (s[:, outward] < 0).any(axis=1)
        v, s = v[~reenter], s[~reenter]
        if v.shape[0] < 30:
            print(f"   {name}: only {v.shape[0]} rays survive re-entry test")
            return None
        inner = np.median(v[:, (ts >= -80) & (ts <= -55)], axis=1)
        outer = np.median(v[:, (ts >= 260) & (ts <= 320)], axis=1)
        half = 0.5 * (inner + outer)
        # register each ray on its own 50 percent crossing
        cross = np.full(v.shape[0], np.nan)
        for i in range(v.shape[0]):
            row = v[i]
            up = outer[i] > inner[i]
            g = row > half[i] if up else row < half[i]
            j = int(np.argmax(g)) if g.any() else -1
            if j <= 0:
                continue
            a, b = row[j - 1], row[j]
            f = 0.0 if b == a else (half[i] - a) / (b - a)
            cross[i] = ts[j - 1] + f * DT
        okc = np.isfinite(cross) & (np.abs(cross) < 40)
        v, cross, inner, outer = v[okc], cross[okc], inner[okc], outer[okc]
        if v.shape[0] < 30:
            print(f"   {name}: only {v.shape[0]} rays register"); return None
        grid = np.arange(-40.0, 300.0 + 1e-9, 1.0)
        reg = np.empty((v.shape[0], grid.size), np.float32)
        for i in range(v.shape[0]):
            reg[i] = np.interp(grid + cross[i], ts, v[i])
        med = np.median(reg, axis=0)
        far = float(np.median(outer))
        print(f"   {name}: {v.shape[0]} rays, inner={np.median(inner):.0f} "
              f"far={far:.0f} contrast={far-np.median(inner):.0f}")
        print("      t(px)      med DN     vs far      frac        n")
        for t in list(range(-40, 0, 10)) + list(range(0, 61, 2)) + \
                 list(range(65, 121, 5)) + list(range(130, 301, 10)):
            k = int(np.searchsorted(grid, t))
            if k >= grid.size:
                continue
            print(f"    {grid[k]:8.0f} {med[k]:11.1f} {med[k]-far:+10.1f} "
                  f"{(med[k]-far)/far*100:+8.2f}%  {v.shape[0]:8d}")
        i0 = int(np.searchsorted(grid, 0.0))
        seg = med[i0:]
        g2 = grid[i0:]
        best = None
        for i in range(1, len(seg) - 1):
            if seg[i] >= seg[i - 1] and seg[i] > seg[i + 1] and g2[i] <= 200:
                p = float(seg[i] - seg[i + 1:].min())
                if best is None or p > best[2]:
                    best = (float(g2[i]), float(seg[i]), p)
        prom = None if best is None else dict(t=best[0], val=best[1],
                                              prom=best[2], frac=best[2] / far)
        k1 = int(np.searchsorted(grid, 1.0))
        res = dict(n=int(v.shape[0]), far=far,
                   inner=float(np.median(inner)),
                   at1=float(med[k1]), frac1=float((med[k1] - far) / far),
                   frac1_contrast=float((med[k1] - far) /
                                        (far - np.median(inner))),
                   ring=prom,
                   grid=[float(x) for x in grid],
                   med=[float(x) for x in med])
        print(f"      -> at t=+1: {(med[k1]-far)/far*100:+.2f}% of far, "
              f"{(med[k1]-far)/(far-np.median(inner))*100:+.2f}% of contrast")
        print(f"      -> ring: {prom}")
        return res

    q = np.percentile(fv, [25, 75])
    out = dict(label=label, channel=channel, seg=diag,
               fringe_q=[float(q[0]), float(q[1])])
    out["all"] = sample(np.ones(fv.shape, bool), "ALL rays")
    out["straight"] = sample(fv <= q[0], f"STRAIGHTEST quartile (fi<={q[0]:.3f})")
    out["fringed"] = sample(fv >= q[1], f"MOST FRINGED quartile (fi>={q[1]:.3f})")
    Path(outdir).mkdir(parents=True, exist_ok=True)
    Path(outdir, f"{label}-rays.json").write_text(json.dumps(out))
    return out


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2], sys.argv[3],
        sys.argv[4] if len(sys.argv) > 4 else "G")
