"""M95 arm 4 - price the RINGING, not just the sharpness.

M87 shipped a halo correction whose own metric read +72.9% while erasing the bee's
abdomen hairs. A sharpness metric that is blind to overshoot will happily recommend a
kernel that rings, and ringing next to a specular highlight on linear sensor data is
exactly the "cutout halo" defect the owner is already complaining about.

So before recommending Lanczos-3 over Catmull-Rom on the strength of +0.1343 dex, this
measures what each kernel does at a hard edge:

  * OVERSHOOT   max excursion beyond the local [min, max] of the source neighbourhood,
                as a fraction of the local range. Zero for a monotone interpolator.
  * NEGATIVES   fraction of samples driven below the true black floor. On LINEAR sensor
                data a negative is not a cosmetic wobble, it is an impossible radiance
                and the merge's own docs say the caller must clamp it.

Positive control: BILINEAR cannot overshoot at all (its weights are non-negative and sum
to one), so it must read EXACTLY zero overshoot. If it does not, the instrument is broken
and nothing else it says counts.
"""

import json
import os

import numpy as np

import x2_pairs as X
from x3_kernel import KERNELS, PAD, resample, resample_bspline


def w_bilinear(t):
    t = np.asarray(t, dtype=np.float64)
    return np.maximum(0.0, 1.0 - np.abs(t))


# Added here rather than in x3_kernel so that x3's recorded numbers cannot move.
KERNELS.setdefault("bilinear", (w_bilinear, 1))

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
TILE = X.TILE


def local_range(t, r=2):
    """[min, max] over the same neighbourhood the kernels draw from."""
    lo = t.copy()
    hi = t.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            s = np.roll(np.roll(t, dy, axis=0), dx, axis=1)
            lo = np.minimum(lo, s)
            hi = np.maximum(hi, s)
    return lo, hi


def main():
    b0 = X.load_luma(X.IMAGES["B0"]["path"])
    tiles = X.pick_tiles(b0)
    print(f"{len(tiles)} tiles, same selection as x2/x3\n")

    # the phase that maximises interpolation error
    dy = dx = 0.5
    names = ["nearest", "bilinear", "catmullrom", "lanczos3", "bspline"]
    res = {}
    print(f"{'kernel':12s} {'mean overshoot':>15s} {'p99.9 overshoot':>16s} {'% negative':>11s}")
    for name in names:
        ov, p999, neg = [], [], []
        for y, x in tiles:
            t = b0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD].astype(np.float64)
            if name == "bspline":
                r = resample_bspline(t, dy, dx)
            elif name == "nearest":
                r = np.roll(np.roll(t, -1, axis=0), -1, axis=1)
            else:
                r = resample(t, dy, dx, name)
            lo, hi = local_range(t)
            rng = np.maximum(hi - lo, 1e-6)
            over = np.maximum(r - hi, 0.0) + np.maximum(lo - r, 0.0)
            frac = (over / rng)[PAD:-PAD, PAD:-PAD]
            ov.append(float(frac.mean()))
            p999.append(float(np.percentile(frac, 99.9)))
            neg.append(float((r[PAD:-PAD, PAD:-PAD] < 0.0).mean() * 100.0))
        res[name] = dict(mean_overshoot=float(np.mean(ov)), p999=float(np.mean(p999)), pct_negative=float(np.mean(neg)))
        print(f"{name:12s} {np.mean(ov):15.6f} {np.mean(p999):16.6f} {np.mean(neg):10.4f}%")

    print("\n--- positive control ---")
    print("  BILINEAR has non-negative weights summing to 1, so it CANNOT overshoot.")
    b = res["bilinear"]["mean_overshoot"]
    n = res["nearest"]["mean_overshoot"]
    ok_b = b < 1e-9
    ok_n = n < 1e-9
    print(f"  bilinear mean overshoot = {b:.3e}  -> {'PASS' if ok_b else 'FAIL'}")
    print(f"  nearest  mean overshoot = {n:.3e}  -> {'PASS' if ok_n else 'FAIL'} (a permutation cannot overshoot either)")

    print("\n--- ordering control ---")
    ok_o = res["lanczos3"]["mean_overshoot"] > res["catmullrom"]["mean_overshoot"]
    print(
        f"  Lanczos-3 rings MORE than Catmull-Rom (wider support, larger negative lobes): "
        f"{res['lanczos3']['mean_overshoot']:.6f} > {res['catmullrom']['mean_overshoot']:.6f} "
        f"-> {'PASS' if ok_o else 'FAIL'}"
    )

    print("\n--- ringing relative to the incumbent ---")
    cr = res["catmullrom"]["mean_overshoot"]
    for name in ["lanczos3", "bspline"]:
        print(f"  {name:10s} {res[name]['mean_overshoot'] / cr:6.3f}x Catmull-Rom's overshoot")

    json.dump(dict(results=res, checks=dict(bilinear_zero=ok_b, nearest_zero=ok_n, ordering=ok_o)),
              open(os.path.join(OUT, "x5_ringing.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'x5_ringing.json')}")
    return 0 if (ok_b and ok_n and ok_o) else 3


if __name__ == "__main__":
    raise SystemExit(main())
