"""M113 K2 - the END-TO-END arm, and ringing on real occluding edges.

Two full 299-frame renders of `bee-3-cpl` from ONE solve (reference 149,
held-out 13.578 px, cycle floor 2.908 px). The two sidecars differ by exactly
one line, `resampler`, verified by Compare-Object. Plus a `nearest` render as
the MONOTONE REFERENCE: a permutation of samples cannot overshoot, so any
excursion of an arm beyond nearest's local [min,max] is interpolator ringing
and nothing else. That lifts M95's x5 overshoot construction, which ran on a
simulated shift, onto the shipped render.

Because all three arms share one solve and one coverage scale (0.9315), they are
pixel-aligned by construction: NO registration step, so no registration blur
enters the quantity being measured.

ROIs are ORCH's, copied verbatim from `experiments/ORCH-drift-check/kernel_crops.py`
-- chosen from BLOB.png on geometry by a third party before any of this ran.
"""
import json
import os
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
sys.path.insert(0, os.path.join(ROOT, "experiments", "ORCH-drift-check"))
import x2_pairs as X  # noqa: E402
import kernel_crops as KC  # noqa: E402  -- for REGIONS, reused not rewritten

OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render"
ARMS = {"nearest": "lin-nn.tif", "catmull-rom": "lin-cr.tif", "lanczos3": "lin-l3.tif"}
TILE = 256
COVERAGE_K = 0.9315


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def geometric_tiles(shape):
    h, w = shape
    return [(y, x)
            for y in range(h // 4, 3 * h // 4 - TILE, TILE)
            for x in range(w // 4, 3 * w // 4 - TILE, TILE)]


def main():
    imgs = {}
    for k, f in ARMS.items():
        p = os.path.join(R, f)
        if not os.path.exists(p):
            print(f"MISSING {p}")
            return 2
        imgs[k] = luma(p)
        print(f"{k:12s} {imgs[k].shape} from {f}")

    res = {}

    # ------------------------------------------------- B3: end-to-end dex
    tiles = geometric_tiles(imgs["catmull-rom"].shape)
    print(f"\nB3 end-to-end: {len(tiles)} geometric tiles, {TILE}px, centres in the central half")
    print("   (pixel-aligned across arms by construction -- one solve, one coverage scale)")
    print(f"   {'arm':12s} {'band k=1.0':>12s} {'band k=0.9315':>15s}")
    per = {}
    for k in ARMS:
        v1 = [X.band_ratio(imgs[k][y:y + TILE, x:x + TILE], 1.0) for y, x in tiles]
        vk = [X.band_ratio(imgs[k][y:y + TILE, x:x + TILE], COVERAGE_K) for y, x in tiles]
        per[k] = (np.array(v1), np.array(vk))
        print(f"   {k:12s} {np.mean(v1):+12.4f} {np.mean(vk):+15.4f}")
    d1 = per["lanczos3"][0] - per["catmull-rom"][0]
    dk = per["lanczos3"][1] - per["catmull-rom"][1]
    sem1 = float(d1.std(ddof=1) / np.sqrt(d1.size))
    semk = float(dk.std(ddof=1) / np.sqrt(dk.size))
    print(f"\n   catmull-rom -> lanczos3, PAIRED per tile:")
    print(f"     k=1.0000 : {d1.mean():+.4f} dex  sem {sem1:.4f}  n={d1.size}")
    print(f"     k=0.9315 : {dk.mean():+.4f} dex  sem {semk:.4f}  n={dk.size}")
    dn = per["nearest"][0] - per["catmull-rom"][0]
    print(f"     catmull-rom -> nearest (the ceiling M95 used): {dn.mean():+.4f} dex")
    res["B3"] = dict(n=int(d1.size),
                     gain_k1=float(d1.mean()), sem_k1=sem1,
                     gain_kcov=float(dk.mean()), sem_kcov=semk,
                     nearest_gain_k1=float(dn.mean()),
                     per_arm_k1={k: float(v[0].mean()) for k, v in per.items()})

    # ------------------------------------ B4: ringing on real occluding edges
    print("\nB4 ringing at occluding edges. Reference = the NEAREST render, which is a")
    print("   permutation and cannot overshoot. Excursion beyond its local 5x5 [min,max]")
    print("   is interpolator ringing. ROIs are ORCH's from kernel_crops.py.")
    ref = imgs["nearest"]
    b4 = {}
    for name, x, y, rw, rh in KC.REGIONS:
        sub = ref[y:y + rh, x:x + rw]
        lo, hi = sub.copy(), sub.copy()
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                s = np.roll(np.roll(sub, dy, axis=0), dx, axis=1)
                lo = np.minimum(lo, s)
                hi = np.maximum(hi, s)
        rng = np.maximum(hi - lo, 1e-6)
        print(f"\n   ROI '{name}' at ({x},{y}) {rw}x{rh}   local range median {np.median(rng):.0f} DN")
        print(f"     {'arm':12s} {'mean over':>10s} {'p99.9 over':>11s} {'max over':>10s} "
              f"{'p99.9 DN':>10s} {'%px outside':>12s} {'%px at 0':>9s}")
        row = {}
        for k in ("catmull-rom", "lanczos3"):
            a = imgs[k][y:y + rh, x:x + rw]
            over = np.maximum(a - hi, 0.0) + np.maximum(lo - a, 0.0)
            frac = over / rng
            inner = slice(3, -3)
            f_ = frac[inner, inner]
            o_ = over[inner, inner]
            row[k] = dict(mean=float(f_.mean()), p999=float(np.percentile(f_, 99.9)),
                          maxf=float(f_.max()), p999_dn=float(np.percentile(o_, 99.9)),
                          pct_outside=float((f_ > 1e-6).mean() * 100),
                          pct_zero=float((a[inner, inner] <= 0.5).mean() * 100))
            r = row[k]
            print(f"     {k:12s} {r['mean']:10.6f} {r['p999']:11.6f} {r['maxf']:10.4f} "
                  f"{r['p999_dn']:10.1f} {r['pct_outside']:11.3f}% {r['pct_zero']:8.4f}%")
        ratio = row["lanczos3"]["mean"] / max(row["catmull-rom"]["mean"], 1e-12)
        r999 = row["lanczos3"]["p999"] / max(row["catmull-rom"]["p999"], 1e-12)
        print(f"     lanczos3 / catmull-rom : mean {ratio:.3f}x   p99.9 {r999:.3f}x")
        b4[name] = dict(rows=row, mean_ratio=float(ratio), p999_ratio=float(r999),
                        median_local_range_dn=float(np.median(rng)))
    res["B4"] = b4

    # ---- flat-ROI control (rule 9): a region with no detail must not "improve"
    h, w = ref.shape
    flat = None
    best = 1e18
    for yy in range(h // 8, 7 * h // 8 - TILE, TILE):
        for xx in range(w // 8, 7 * w // 8 - TILE, TILE):
            t = ref[yy:yy + TILE, xx:xx + TILE]
            v = float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var())
            if v < best:
                best, flat = v, (yy, xx)
    yy, xx = flat
    fa = X.band_ratio(imgs["catmull-rom"][yy:yy + TILE, xx:xx + TILE], 1.0)
    fb = X.band_ratio(imgs["lanczos3"][yy:yy + TILE, xx:xx + TILE], 1.0)
    print(f"\n   RULE 9 FLAT-ROI CONTROL at ({xx},{yy}), gradient var {best:.4g} "
          f"(flattest tile in the frame)")
    print(f"     catmull-rom {fa:+.4f}   lanczos3 {fb:+.4f}   delta {fb - fa:+.4f} dex")
    res["flat_roi"] = dict(x=int(xx), y=int(yy), grad_var=best, cr=float(fa), l3=float(fb),
                           delta=float(fb - fa))

    json.dump(res, open(os.path.join(OUT, "k2_endtoend.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k2_endtoend.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
