"""M87 step 14 -- arms F1 and F3, driven by the MEASURED mechanism rather than
by the two-layer reconstruction that arm F2 could not fit.

Step 13 result: the linear-in-alpha two-layer model explains a median R^2 of
only 0.131 of the through-focus variance at halo pixels, admits 12.5% of the
band, and moves ISO by +3.7% -- i.e. slightly WORSE than the untouched merge,
against a bar of -50%. That is an honest negative for reconstruction.

Step 11 measured the defect precisely, though, and it is a RANK DISCONTINUITY:
the percentile rank of the elected value within its own through-focus
distribution is 0.675 in the near band and 0.429 far away. The band is estimated
max-like and the far field median-like, and the rim is the seam between the two.

  F1  (Wang et al. 2015 mode partition, the cheap published remedy that
      SYNTHESIS fact 412 says to try before anything bespoke): forbid near-edge
      background pixels from electing frames in which the FOREGROUND is in
      focus, so they cannot inherit the foreground's focus decision.

      *** READ STEP 22 BEFORE USING ANY NUMBER FROM THIS FILE. ***  F1 wins on
      the halo metric and LOSES on ground truth: on the plant it removes 79.8%
      of the artifact while raising band RMSE from 3.46% to 12.28% of level.
      It is cosmetic.  The global k_F used here also fails to generalise to a
      second scene; step 20 replaces it with a per-pixel map.

  F3  (rank-consistent background): estimate every background pixel at the SAME
      rank of its own through-focus distribution, removing the seam directly.
      F3a applies it to all background; F3b only inside the yoke radius.

Both are pass-through outside the treated set, so the placebo bar is structural
and the number to report is how much of an untreated region each one claims.
"""

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

MARGIN = 22
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
YOKE = 40
CHUNK = 48


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    vmed = np.load(CACHE / "11-vmed.npy")
    n, h, w = lumas.shape
    kF = int(np.bincount(argbest[mask]).argmax())

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True
    bg = ~mask
    band = inner & bg & (dist >= 2) & (dist <= 40)
    far = inner & bg & (dist >= 60)

    base = M2.score_iso(sel, p, nv, boot=500)
    print(f"F0 : ISO={base['ISO']:.5f} "
          f"CI[{base['ISO_ci'][0]:.5f},{base['ISO_ci'][1]:.5f}]", flush=True)
    res = {"kF": kF,
           "F0": {k: v for k, v in base.items() if k not in ("o", "pts", "qt")}}

    def rep(tag, img, treated):
        r = M2.score_iso(img, p, nv, boot=500)
        d = 100 * (1 - r["ISO"] / base["ISO"])
        print(f"{tag:<26} ISO={r['ISO']:.5f} "
              f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  ({d:+.1f}% vs F0)"
              f"  treated band {treated[band].mean():.3f} far {treated[far].mean():.3f}",
              flush=True)
        res[tag] = {"delta_pct": float(d), "treated_band": float(treated[band].mean()),
                    "treated_far": float(treated[far].mean()),
                    **{k: v for k, v in r.items() if k not in ("o", "pts", "qt")}}
        np.save(CACHE / f"14-{tag}.npy", img)
        return r

    # ---- F3a / F3b : rank-consistent background --------------------------
    f3a = sel.copy()
    t = inner & bg
    f3a[t] = vmed[t]
    rep("F3a-median-all-bg", f3a, t)

    f3b = sel.copy()
    t = inner & bg & (dist <= YOKE)
    f3b[t] = vmed[t]
    rep("F3b-median-band-only", f3b, t)

    # ---- F1 : Wang-2015 mode partition ------------------------------------
    # Forbid near-edge background pixels from electing frames in which the
    # foreground is in focus.  DELTA is the half-width of the forbidden band in
    # k, set from the foreground's own focus curve.
    for DELTA in (20, 40, 80):
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)
        treat = inner & bg & (dist <= YOKE)
        # recompute the field per frame (cheap enough) with the shipped radii
        import m87lib as L
        for k in range(n):
            lu = np.asarray(lumas[k], np.float32)
            fld = L.regularised_field(lu, 100.0)
            allowed = np.ones((h, w), bool) if abs(k - kF) >= DELTA else ~treat
            better = (fld > best) & allowed
            best[better] = fld[better]
            arg[better] = k
        f1 = np.empty((h, w), np.float32)
        for k in range(n):
            m = arg == k
            if m.any():
                f1[m] = np.asarray(lumas[k], np.float32)[m]
        rep(f"F1-mode-partition-d{DELTA}", f1, treat)

    json.dump(res, open(DATA / "14-arms.json", "w"), indent=1)
    print("\nwrote data/14-arms.json")


if __name__ == "__main__":
    main()
