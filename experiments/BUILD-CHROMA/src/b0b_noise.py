"""B0b -- photon-transfer estimate of sensor gain and read noise.

The V3 planted-offset arm has to run at the SNR of the real data or it proves
nothing. Guessing the noise model was the first attempt and it was wrong by a
factor of ~6 in variance, which destroyed every synthetic focus curve. This
measures the noise instead.

Method: on a real, heavily-defocused frame (a smooth scene is what photon
transfer wants), take small patches, and regress local variance on local mean
across patches. For a sensor with `g` electrons per ADU and read noise `r` ADU:

    var_ADU(S) = S / g + r^2

so the slope is 1/g and the intercept is r^2. Patches are taken from a single
frame, and the local mean is removed with a plane fit first so that real scene
gradient does not inflate the variance.

Only the two GREEN lattices are used, and they are estimated separately: if the
two agree, the estimate is not a lattice artefact.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import frames, read_cfa, planes_of, dump


def patch_stats(pl, size=16, stride=64):
    """Local (mean, variance) after removing a first-order plane per patch."""
    h, w = pl.shape
    ys = np.arange(0, h - size, stride)
    xs = np.arange(0, w - size, stride)
    yy, xx = np.mgrid[0:size, 0:size]
    A = np.stack([np.ones(size * size), yy.ravel(), xx.ravel()], 1)
    pinv = np.linalg.pinv(A)
    means, vars_ = [], []
    for y in ys:
        for x in xs:
            p = pl[y:y + size, x:x + size].astype(np.float64).ravel()
            coef = pinv @ p
            resid = p - A @ coef
            means.append(coef[0] + coef[1] * (size - 1) / 2 + coef[2] * (size - 1) / 2)
            # 3 dof consumed by the plane fit
            vars_.append(resid @ resid / (p.size - 3))
    return np.array(means), np.array(vars_)


def fit(means, vars_, nbin=24):
    """Bin by mean and fit a straight line to the binned medians."""
    ok = (means > 5) & (means < 12000)
    m, v = means[ok], vars_[ok]
    edges = np.quantile(m, np.linspace(0, 1, nbin + 1))
    bm, bv = [], []
    for i in range(nbin):
        s = (m >= edges[i]) & (m < edges[i + 1])
        if s.sum() >= 8:
            bm.append(np.median(m[s]))
            bv.append(np.median(v[s]))
    bm, bv = np.array(bm), np.array(bv)
    A = np.stack([bm, np.ones_like(bm)], 1)
    sol, *_ = np.linalg.lstsq(A, bv, rcond=None)
    slope, intercept = float(sol[0]), float(sol[1])
    pred = A @ sol
    ss = 1.0 - np.sum((bv - pred) ** 2) / max(np.sum((bv - bv.mean()) ** 2), 1e-9)
    return {"slope": slope, "intercept": intercept,
            "gain_e_per_adu": 1.0 / slope if slope > 0 else None,
            "read_adu": float(np.sqrt(max(intercept, 0.0))),
            "r2": float(ss), "nbin": int(len(bm)),
            "bin_mean": bm.tolist(), "bin_var": bv.tolist()}


if __name__ == "__main__":
    stack = sys.argv[1] if len(sys.argv) > 1 else "lavendar-cpl"
    fs = frames(stack)
    out = {"stack": stack, "frames_used": [], "planes": {}}
    # first and last frames are the most defocused, hence the smoothest
    for label, k in (("first", 0), ("last", len(fs) - 1)):
        pl = planes_of(read_cfa(fs[k]))
        out["frames_used"].append({label: os.path.basename(fs[k])})
        for c in ("G1", "G2"):
            m, v = patch_stats(pl[c])
            r = fit(m, v)
            out["planes"][f"{label}_{c}"] = r
            print(f"  {label:5s} {c}: gain {r['gain_e_per_adu']:.3f} e-/ADU   "
                  f"read {r['read_adu']:.2f} ADU   R2 {r['r2']:.4f}  "
                  f"({r['nbin']} bins)")
    gs = [v["gain_e_per_adu"] for v in out["planes"].values() if v["gain_e_per_adu"]]
    rs = [v["read_adu"] for v in out["planes"].values()]
    out["gain_median"] = float(np.median(gs))
    out["read_median"] = float(np.median(rs))
    print(f"  ADOPTED: gain {out['gain_median']:.3f} e-/ADU, "
          f"read {out['read_median']:.2f} ADU")
    dump("b0b_noise", out)
