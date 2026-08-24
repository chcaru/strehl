#!/usr/bin/env python3
"""M111 -- CORRECTED re-analysis of the attribution headline.

WHY THIS EXISTS
===============
`attribution.py` reported the M111 headline as

    low (flat, n_eff<=8): +12.00 DN, ratio 1.248, null 1.002 +/- 0.003, +97.4 sigma

The sigma is not defensible. `attribution.py` estimates the null standard
deviation from **three** translations:

    SHIFTS = [(137, 211), (-263, 89), (451, -337)]

and then divides by `np.std(..., ddof=1)` of three numbers. A three-sample sd is
an unstable estimate; here it came out at 0.0025, and dividing a 0.246 ratio
excess by it manufactures 97 sigma. Re-running the identical mask with 16
translations gives a null sd of 0.027 -- an order of magnitude larger -- and the
same effect reads about 2.6 sigma.

This script replaces that analysis with one that does not depend on a small-n sd:

  * 64 translations, not 3.
  * A RANK p-value -- how many nulls equal or exceed the real value -- reported
    alongside sigma, because the rank statistic makes no normality assumption
    and cannot be inflated by an underestimated sd.
  * BOTH the median and the mean of |step|, because attribution.py used the
    median and the cross-check used the mean, and the choice moved the answer.
  * Flat masks PERCENTILE-MATCHED across arms. `attribution.py`'s absolute
    `local_sd < 300 DN` threshold selects 39.9% of the gate-4 arm but 81.5% of
    the softer mean arm, so swapping the mask source silently swapped the
    population as well. Matching on population fraction changes only WHICH arm
    decides a pixel is flat, which is the question.
  * Cell size AREA-WEIGHTED. Counting the median connected component treats a
    one-pixel island the same as a plateau; the honest question is how large a
    plateau the average pixel sits inside.

Every number in the M111 report that came from `attribution.py`'s null is
superseded by whatever this prints.
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage as ndi

RENDER = r"C:\dev\strehl-out\M111\render"
ORCH = r"C:\dev\strehl-out\ORCH-thennow"
OUT = r"C:\dev\strehl-out\M111"

LOW_N, HIGH_N, MARGIN = 8, 64, 64
FLAT_FRAC = 0.40   # population fraction, matched across arms

# 64 translations. Coprime-ish offsets, none a small multiple of the ~60 px
# plateau scale, so no shift can accidentally re-register the map onto itself.
_OFF = (-419, -337, -263, -157, 157, 263, 337, 419)
SHIFTS = [(dy, dx) for dy in _OFF for dx in _OFF]


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(path):
    y = luma(tifffile.imread(path))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndi.uniform_filter(y, k, mode="nearest")
    m2 = ndi.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def step_on_off(idx, f, mask):
    """|step| in f, split by whether the step crosses an election seam."""
    dh = idx[:, 1:] != idx[:, :-1]
    dv = idx[1:, :] != idx[:-1, :]
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    step = np.concatenate([np.abs(f[:, 1:] - f[:, :-1])[mh],
                           np.abs(f[1:, :] - f[:-1, :])[mv]])
    on = np.concatenate([dh[mh], dv[mv]])
    if step.size < 5000 or on.sum() < 500 or (~on).sum() < 500:
        return None
    s_on, s_off = step[on], step[~on]
    return {"n": int(step.size), "bdens": float(on.mean()),
            "med_ratio": float(np.median(s_on)) / max(float(np.median(s_off)), 1e-9),
            "mean_ratio": float(np.mean(s_on)) / max(float(np.mean(s_off)), 1e-9),
            "med_excess": float(np.median(s_on) - np.median(s_off)),
            "mean_excess": float(np.mean(s_on) - np.mean(s_off))}


def scored(idx, f, mask, tag):
    real = step_on_off(idx, f, mask)
    if real is None:
        return {"tag": tag, "verdict": "TOO FEW PIXELS"}
    nulls = [step_on_off(np.roll(idx, s, (0, 1)), f, mask) for s in SHIFTS]
    nulls = [n for n in nulls if n]
    out = {"tag": tag, "n_nulls": len(nulls), "bdens": real["bdens"]}
    for key in ("med_ratio", "mean_ratio", "med_excess", "mean_excess"):
        vals = np.array([n[key] for n in nulls], float)
        mu, sd = float(vals.mean()), float(vals.std(ddof=1))
        r = real[key]
        # Rank p-value: fraction of nulls at least as extreme, two-sided about
        # the null mean. Floor is 1/(n+1) -- it cannot report better than the
        # resolution 64 translations buy.
        n_ge = int(np.sum(np.abs(vals - mu) >= abs(r - mu)))
        out[key] = {"real": r, "null_mean": mu, "null_sd": sd,
                    "sigma": (r - mu) / sd if sd > 0 else float("nan"),
                    "rank_p": (n_ge + 1) / (len(vals) + 1)}
    return out


def show(res, key):
    d = res[key]
    return ("%-30s %8.3f  null %7.3f+-%6.3f  %+7.1f sd  p=%.3f"
            % (res["tag"], d["real"], d["null_mean"], d["null_sd"], d["sigma"], d["rank_p"]))


def area_weighted_cell(idx, sl):
    """Diameter of the plateau the AVERAGE pixel sits in, not the median blob."""
    a = np.asarray(idx[sl]).astype(np.int32)
    areas = np.zeros(a.shape, float)
    for v in np.unique(a):
        m = a == v
        lab, k = ndi.label(m)
        if not k:
            continue
        cnt = np.bincount(lab.ravel())
        areas[m] = cnt[lab[m]]
    return float(2.0 * np.sqrt(np.mean(areas) / np.pi)), float(np.mean(areas))


def main():
    y4 = plane_luma(os.path.join(RENDER, "marker-dump.tif"))
    ym = plane_luma(os.path.join(RENDER, "marker-g100000.tif"))
    yc = plane_luma(os.path.join(ORCH, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif"))
    st = os.path.join(RENDER, "state-r8")
    idx = np.load(os.path.join(st, "best_index.npy"))
    ne = np.load(os.path.join(st, "n_eff_gate4.00.npy"))

    h = min(y4.shape[0], ym.shape[0], yc.shape[0], idx.shape[0])
    w = min(y4.shape[1], ym.shape[1], yc.shape[1], idx.shape[1])
    y4, ym, yc, idx, ne = y4[:h, :w], ym[:h, :w], yc[:h, :w], idx[:h, :w], ne[:h, :w]
    d = y4 - ym
    inner = np.zeros((h, w), bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True

    print("=" * 92)
    print("M111 CORRECTED attribution -- 64 translations, rank p-values, matched masks")
    print("=" * 92)
    print(f"plane {w}x{h}   nulls={len(SHIFTS)}   flat population matched at {FLAT_FRAC:.0%}")

    results = []
    for arm, src in (("gate4 (test arm, as reported)", y4),
                     ("gate1e5 (mean, NO selection)", ym),
                     ("single frame (ORCH control)", yc)):
        sd = local_sd(src)
        thr = float(np.percentile(sd[inner], 100.0 * FLAT_FRAC))
        flat = (sd <= thr) & inner
        low = flat & (ne <= LOW_N)
        high = flat & (ne >= HIGH_N)
        print(f"\n--- flat mask from {arm}   (sd threshold {thr:.1f} DN, "
              f"flat {100*flat.mean():.1f}%, low {100*low.mean():.1f}%) ---")
        for nm, m in (("low  flat & n_eff<=8", low), ("high flat & n_eff>=64", high)):
            r = scored(idx, d, m, f"{nm} [{arm.split()[0]}]")
            if "med_ratio" not in r:
                print(f"  {r['tag']}: {r['verdict']}")
                continue
            print("  MEDIAN " + show(r, "med_ratio"))
            print("  MEAN   " + show(r, "mean_ratio"))
            results.append(r)

    # The textured control, on the arm-independent mask.
    sd = local_sd(ym)
    thr_hi = float(np.percentile(sd[inner], 90.0))
    rough = (sd >= thr_hi) & inner
    r = scored(idx, d, rough, "rough (textured) [gate1e5 mask]")
    print(f"\n--- NC1 textured control (mean-arm mask, top 10% local sd) ---")
    print("  MEDIAN " + show(r, "med_ratio"))
    print("  MEAN   " + show(r, "mean_ratio"))
    results.append(r)

    # Area-weighted plateau size, replacing the median-component figure.
    print("\n--- area-weighted plateau size (diameter the average pixel sits in) ---")
    rois = {"blobB": (slice(650, 800), slice(1024, 1184)),
            "blobA": (slice(590, 720), slice(2357, 2507)),
            "matched no-blob": (slice(1984, 2134), slice(424, 584)),
            "whole plane": (slice(MARGIN, h - MARGIN), slice(MARGIN, w - MARGIN))}
    cells = {}
    for nm, sl in rois.items():
        dia, area = area_weighted_cell(idx, sl)
        cells[nm] = {"equiv_diameter_px": dia, "mean_area_px": area}
        print("  %-18s equivalent diameter %6.1f px   mean plateau area %9.1f px" % (nm, dia, area))

    with open(os.path.join(OUT, "recheck.json"), "w") as fh:
        json.dump({"results": results, "cells": cells, "n_shifts": len(SHIFTS)}, fh, indent=1)
    print("\nwrote recheck.json")


if __name__ == "__main__":
    main()
