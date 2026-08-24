"""M87 / 53 -- gain ladder: is there ANY normalisation strength that helps?

52 applied a full (lambda = 1) per-frame gain correction and the halo got
WORSE, -8.4%. That single point cannot exclude a small positive photometric
share reachable by a gentler correction, so this sweeps the strength:

    luma_k  ->  luma_k * gain_k**lambda,   lambda in {0, 0.25, 0.5, 0.75, 1}

lambda = 0 is the shipped election (the null arm) and lambda = 1 is 52's arm.
If ISO is monotone increasing in lambda, no correction strength helps and the
photometric share is <= 0 at every strength -- which is a far stronger negative
than a single point.

Also reports the LOW-FREQUENCY trend in the illumination probe separately from
its total spread, because the orchestrator's 5.31% is an early-frame bias while
my probe's 17.83% is a total peak-to-peak that includes the sweep's own
structure.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

CACHE = pathlib.Path("cache")
DATA = pathlib.Path("data")
ISO = 100.0
MARGIN = 22
LAMBDAS = [0.0, 0.25, 0.5, 0.75, 1.0]


def main():
    luma = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    n = luma.shape[0]

    probe = distance_transform_edt(~mask) > 60.0
    lev = np.array([float(np.asarray(luma[k], np.float32)[probe].mean())
                    for k in range(n)], np.float64)
    ref = float(np.median(lev))
    gain = (ref / lev).astype(np.float64)

    pp = 100 * (lev.max() - lev.min()) / ref
    # low-frequency trend: first decile of frames against the median level
    early = float(lev[: n // 10].mean())
    trend = 100 * (early - ref) / ref
    # smooth trend p-p, 31-frame moving average, to strip per-frame noise
    ker = np.ones(31) / 31.0
    sm = np.convolve(lev, ker, mode="valid")
    pp_sm = 100 * (sm.max() - sm.min()) / ref
    print(f"probe level: ref {ref:.1f} DN")
    print(f"  total p-p            {pp:.2f}%")
    print(f"  smoothed p-p (31-fr) {pp_sm:.2f}%")
    print(f"  early-decile bias    {trend:+.2f}%   (ORCH reported +5.31%)")

    R = L.ROIS["ROI_LEG"]
    INNER = (MARGIN, MARGIN + (R[1] - R[0]), MARGIN, MARGIN + (R[3] - R[2]))
    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]

    rows = []
    for lam in LAMBDAS:
        g = gain ** lam
        best = np.full(mask.shape, -np.inf, np.float32)
        arg = np.zeros(mask.shape, np.int32)
        for k in range(n):
            lk = np.asarray(luma[k], np.float32) * np.float32(g[k])
            f = L.regularised_field(lk, ISO)
            m = f > best
            best[m] = f[m]
            arg[m] = k
        sel = np.zeros(mask.shape, np.float32)
        for k in range(n):
            m = arg == k
            if m.any():
                sel[m] = (np.asarray(luma[k], np.float32) * np.float32(g[k]))[m]
        r = M2.score_iso(sel, p, nv, boot=500)
        assert r is not None, f"metric returned None at lambda={lam}"
        rows.append({"lambda": lam, "ISO": r["ISO"], "ci": r["ISO_ci"]})
        print(f"  lambda {lam:4.2f}   ISO {r['ISO']:.5f} "
              f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]", flush=True)

    iso = [r["ISO"] for r in rows]
    base = iso[0]
    best_i = int(np.argmin(iso))
    print(f"\nbest lambda = {LAMBDAS[best_i]} at ISO {iso[best_i]:.5f} "
          f"vs shipped {base:.5f}")
    mono = all(iso[i] <= iso[i + 1] + 1e-9 for i in range(len(iso) - 1))
    print("MONOTONE INCREASING -- no correction strength helps" if mono
          else "NOT monotone -- some strength may help; see table")
    print(f"photometric share at best lambda = {100*(1-iso[best_i]/base):+.1f}%")

    json.dump({"probe_pp_pct": pp, "probe_pp_smoothed_pct": pp_sm,
               "early_decile_bias_pct": trend, "rows": rows,
               "monotone_increasing": bool(mono),
               "best_lambda": LAMBDAS[best_i],
               "share_at_best_pct": 100 * (1 - iso[best_i] / base)},
              open(DATA / "53-gain-ladder.json", "w"), indent=1)


if __name__ == "__main__":
    main()
