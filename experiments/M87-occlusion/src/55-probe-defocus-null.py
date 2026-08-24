"""M87 step 55 -- which probe REGION is right, by a defocus-only null.

Step 54 showed every probe region recovers a planted global gain with slope
1.000000: a global multiply scales every region alike, so that test proves
sign and linearity and cannot discriminate regions. This one can.

THE PROPERTY. Blur conserves flux. A probe that measures ILLUMINATION must be
unmoved when the only thing that changes is focus; a probe that has scene
content in it will drift, because defocus redistributes that content. This is
the same property M99 asserts in `photometric.rs`
(`defocus_alone_does_not_move_the_estimated_gain`) and the same reason its
header rejects patch medians for flux. Here it is applied to the three regions
of step 54 on a real frame.

PREDICTION, REGISTERED BEFORE RUNNING:
  FAR   drift smallest -- homogeneous defocused background, little to redistribute
  CROP  drift middling -- contains the subject boundary
  SUBJ  drift largest  -- the subject is the structure being redistributed
If FAR is not the smallest, my region choice is wrong and I have to say so.

WHY IT CAN FAIL, AND THE ONE HONEST CAVEAT. Flux is conserved globally, but
over a SUBREGION it leaks across the region's own boundary. So none of these
will read exactly zero, and a region that is merely large would score well for
the wrong reason. The control for that is `BLOCK`: a CONTIGUOUS rectangle with
FAR's exact pixel count placed over the middle of the crop, which has FAR's
size and locality but not its avoidance of the subject.

A MIS-SPECIFIED CONTROL, DISCLOSED. The first version used `SHUF`, FAR's pixel
count scattered uniformly at random. It read 0.042% and BEAT FAR's 0.206%,
which looked like a failure of my region choice and is not: a uniform random
scatter over the whole crop is an estimator of the GLOBAL MEAN, and blur
conserves the global mean, so SHUF is the most blur-invariant statistic
available rather than a same-area-wrong-place control. It is kept in the table
because it is informative, but `BLOCK` is the control the claim needs.

THE UNINTENDED FINDING THIS EXPOSED. `CROP` is a whole-crop MEDIAN and reads
2.942%; `SHUF`, a mean over a random 29% of the same crop, reads 0.042%. Same
pixels, 70x apart. So the estimator's STATISTIC dominates its REGION here, and
`GMEAN` -- the whole-crop mean -- is included to state that comparison against
`CROP` directly, holding the region fixed and changing only mean vs median.
"""

import json
import pathlib

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

SIGMAS = [0.0, 1.0, 2.0, 4.0, 8.0, 16.0]
DIST_PX = 60.0
SEED = 20260824


def main():
    luma = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    n, h, w = luma.shape
    kref = n // 2
    base = np.asarray(luma[kref], np.float32)
    print(f"cube {luma.shape}; defocus null on real frame k={kref}")

    far = distance_transform_edt(~mask) > DIST_PX
    subj = mask.copy()

    # SHUF: a random region with exactly FAR's pixel count, placed without
    # regard to the subject. NOTE: this turns out to estimate the global mean
    # (see the docstring); BLOCK is the control the region claim rests on.
    rng = np.random.default_rng(SEED)
    flat = rng.permutation(h * w)[: int(far.sum())]
    shuf = np.zeros(h * w, bool)
    shuf[flat] = True
    shuf = shuf.reshape(h, w)

    # BLOCK: a contiguous rectangle of FAR's exact area, centred on the crop,
    # so it has FAR's size and locality but overlaps the subject.
    side = int(np.sqrt(far.sum()))
    bh = min(side, h)
    bw = int(round(far.sum() / bh))
    bw = min(bw, w)
    y0 = (h - bh) // 2
    x0 = (w - bw) // 2
    block = np.zeros((h, w), bool)
    block[y0:y0 + bh, x0:x0 + bw] = True

    regions = {"FAR": far, "CROP": None, "GMEAN": np.ones((h, w), bool),
               "SUBJ": subj, "BLOCK": block, "SHUF": shuf}
    for a, m in regions.items():
        frac = 100.0 if m is None else 100.0 * m.mean()
        stat = "median" if m is None else "mean"
        print(f"  {a:<6} {frac:6.2f}% of pixels  ({stat})")

    lev = {a: [] for a in regions}
    for s in SIGMAS:
        f = base if s == 0.0 else gaussian_filter(base, s, mode="nearest")
        for a, m in regions.items():
            lev[a].append(float(np.median(f)) if m is None else float(f[m].mean()))
        print(f"  sigma {s:5.1f} done", flush=True)

    out = {"kref": kref, "sigmas": SIGMAS, "dist_px": DIST_PX, "seed": SEED,
           "regions": {}}
    print("\n=== DEFOCUS-ONLY NULL: drift from sigma=0, percent ===")
    hdr = "".join(f"{s:>9.0f}" for s in SIGMAS)
    print(f"{'arm':<6}{hdr}{'  max|drift|%':>14}")
    for a in regions:
        v = np.array(lev[a])
        d = 100.0 * (v / v[0] - 1.0)
        mx = float(np.abs(d).max())
        out["regions"][a] = {"levels": v.tolist(), "drift_pct": d.tolist(),
                             "max_abs_drift_pct": mx}
        print(f"{a:<6}" + "".join(f"{x:>9.3f}" for x in d) + f"{mx:>14.3f}")

    fa = out["regions"]["FAR"]["max_abs_drift_pct"]
    bl = out["regions"]["BLOCK"]["max_abs_drift_pct"]
    cr = out["regions"]["CROP"]["max_abs_drift_pct"]
    gm = out["regions"]["GMEAN"]["max_abs_drift_pct"]
    su = out["regions"]["SUBJ"]["max_abs_drift_pct"]
    order_ok = fa < cr and fa < su
    beats_area = fa < bl
    out["prediction_order_ok"] = bool(order_ok)
    out["far_beats_block_control"] = bool(beats_area)
    out["median_over_mean_same_region"] = cr / gm if gm > 0 else None
    print(f"\nFAR smallest of the three real regions   : "
          f"{'PASS' if order_ok else 'FAIL'}  ({fa:.3f} vs CROP {cr:.3f}, SUBJ {su:.3f})")
    print(f"FAR beats the same-area BLOCK control    : "
          f"{'PASS' if beats_area else 'FAIL'}  ({fa:.3f} vs {bl:.3f})")
    print(f"same region, median vs mean (CROP/GMEAN) : "
          f"{cr:.3f} vs {gm:.3f} = {cr / gm:.1f}x")
    json.dump(out, open(DATA / "55-probe-defocus-null.json", "w"), indent=1)
    print(f"\nwrote {DATA / '55-probe-defocus-null.json'}")


if __name__ == "__main__":
    main()
