"""Probe: the edge-amplitude distribution, to set a `min_amplitude` floor.

N4 (flat ROI, rule 9) fired: 113 of 334 forced profiles in featureless
background were ACCEPTED and read -0.30 on both sides.  That is the classic
failure the rule exists to catch -- with no step present, `A` is pure noise,
the recentring locks onto the largest noise gradient, and every statistic is
then divided by that noise.

The fix has to be a floor on `A` that admits real steps and rejects noise
steps.  This probe measures both distributions so the floor is CHOSEN FROM
DATA rather than picked to make a number come out.

Run:  python experiments/M121-halo-polarity/amp_probe.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from halo_lib import DMAX, measure_edge  # noqa: E402
from m121_io import FRAMES, arm_path, load_u16, luma  # noqa: E402
from runner import scan  # noqa: E402

FLAT_TOL = 0.10


def flat_amplitudes(img, n=4000, seed=99):
    rng = np.random.default_rng(seed)
    h, w = img.shape
    g = uniform_filter(np.abs(np.diff(img, axis=1, prepend=img[:, :1])), size=33)
    ys = rng.integers(int(DMAX) + 8, h - int(DMAX) - 8, size=n)
    xs = rng.integers(int(DMAX) + 8, w - int(DMAX) - 8, size=n)
    keep = g[ys, xs] < np.percentile(g, 10)
    ys, xs = ys[keep], xs[keep]
    ang = rng.uniform(0, 2 * np.pi, size=ys.size)
    out = []
    for y, x, a in zip(ys, xs, ang):
        e = measure_edge(img, float(y), float(x), float(np.cos(a)), float(np.sin(a)),
                         flat_tol=FLAT_TOL)
        if e is not None:
            out.append(e["A"])
    return np.array(out)


def main():
    merged = luma(load_u16(arm_path("armM4-gate4-binlin")))
    print(f"merged luma range {merged.min():.4f} .. {merged.max():.4f}")

    r = scan(merged, label="amp probe", grad_percentile=95.0, max_edges=60000,
             isolation_frac=0.40, flat_tol=FLAT_TOL, max_rise=6.5, verbose=False)
    A = np.asarray(r["bright"]["amps"]) if "amps" in r.get("bright", {}) else r["amplitudes"]
    A = np.asarray(A)
    print(f"\nREAL accepted edges: n={A.size}")
    for p in (0, 1, 5, 10, 25, 50, 75, 100):
        print(f"  A p{p:<3d} = {np.percentile(A, p):.5f}")

    F = flat_amplitudes(merged)
    print(f"\nFLAT-ROI forced profiles that passed measure_edge: n={F.size}")
    for p in (50, 75, 90, 95, 99, 100):
        print(f"  A p{p:<3d} = {np.percentile(F, p):.5f}")

    for floor in (0.005, 0.01, 0.02, 0.03, 0.05, 0.08):
        print(f"  floor {floor:.3f}: real keeps {100*np.mean(A >= floor):5.1f}% "
              f"({int(np.sum(A >= floor))})   flat keeps {100*np.mean(F >= floor):5.1f}% "
              f"({int(np.sum(F >= floor))})")

    for name in FRAMES:
        img = luma(load_u16(arm_path(name)))
        Ff = flat_amplitudes(img)
        print(f"  {name}: flat p99 A = {np.percentile(Ff, 99):.5f}  n={Ff.size}")


if __name__ == "__main__":
    main()
