#!/usr/bin/env python3
"""M111 -- decompose the headline: real effect diluted, or mask circularity?

`recheck.py` showed the low-n_eff seam excess is +11.6 sd when `flat` is defined
on the gate-4 arm (the arm under test) and null-consistent when `flat` is defined
on either selection-free arm. Two readings survive that:

  (a) CIRCULARITY. The gate-4 mask selects the very pixels selection flattened,
      so the statistic is conditioned on its own outcome.
  (b) DILUTION. The independent masks are twice as large and swamp a real effect
      with pixels that are not blobs.

They are separable. Partition the low-n_eff population three ways:

    BOTH  = flat on gate-4 AND flat on the selection-free arm
    ONLY4 = flat on gate-4 but NOT flat on the selection-free arm
            (pixels selection MADE flat -- the circular set)
    ONLYI = flat on the selection-free arm but NOT on gate-4

If the excess lives in BOTH, it is real and the independent mask merely diluted
it. If it lives in ONLY4, the headline was circular and must be retracted.

Also scores ORCH's two named ROIs directly, and reports the population sizes so
a null result can be told apart from an underpowered one.
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage as ndi

RENDER = r"C:\dev\strehl-out\M111\render"
ORCH = r"C:\dev\strehl-out\ORCH-thennow"
OUT = r"C:\dev\strehl-out\M111"

LOW_N, MARGIN, FLAT_FRAC = 8, 64, 0.40
_OFF = (-419, -337, -263, -157, 157, 263, 337, 419)
SHIFTS = [(dy, dx) for dy in _OFF for dx in _OFF]


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(p):
    y = luma(tifffile.imread(p))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndi.uniform_filter(y, k, mode="nearest")
    m2 = ndi.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def stat(idx, f, mask):
    dh = idx[:, 1:] != idx[:, :-1]
    dv = idx[1:, :] != idx[:-1, :]
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    step = np.concatenate([np.abs(f[:, 1:] - f[:, :-1])[mh],
                           np.abs(f[1:, :] - f[:-1, :])[mv]])
    on = np.concatenate([dh[mh], dv[mv]])
    if step.size < 3000 or on.sum() < 300 or (~on).sum() < 300:
        return None
    return float(np.median(step[on])) / max(float(np.median(step[~on])), 1e-9)


def score(idx, f, mask, tag):
    r = stat(idx, f, mask)
    npx = int(mask.sum())
    if r is None:
        return {"tag": tag, "npx": npx, "verdict": "UNDERPOWERED"}
    v = np.array([x for x in (stat(np.roll(idx, s, (0, 1)), f, mask) for s in SHIFTS) if x], float)
    mu, sd = float(v.mean()), float(v.std(ddof=1))
    p = (int(np.sum(np.abs(v - mu) >= abs(r - mu))) + 1) / (len(v) + 1)
    return {"tag": tag, "npx": npx, "real": r, "null_mean": mu, "null_sd": sd,
            "sigma": (r - mu) / sd if sd else float("nan"), "rank_p": p, "n_nulls": len(v)}


def line(d):
    if "real" not in d:
        return "  %-42s n=%8d  %s" % (d["tag"], d["npx"], d["verdict"])
    return ("  %-42s n=%8d  %6.3f  null %6.3f+-%5.3f  %+7.1f sd  p=%.3f"
            % (d["tag"], d["npx"], d["real"], d["null_mean"], d["null_sd"], d["sigma"], d["rank_p"]))


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

    def flatmask(src):
        sd = local_sd(src)
        return (sd <= float(np.percentile(sd[inner], 100.0 * FLAT_FRAC))) & inner

    f4, fm, fc = flatmask(y4), flatmask(ym), flatmask(yc)
    low = ne <= LOW_N

    print("=" * 104)
    print("M111 -- is the headline CIRCULAR or merely DILUTED?   64 nulls, median statistic")
    print("=" * 104)
    res = []
    for nm, fi in (("gate1e5 mean", fm), ("single frame", fc)):
        print(f"\n--- independent flat mask: {nm} ---")
        for tag, m in ((f"BOTH  flat4 AND flat[{nm}]", f4 & fi & low),
                       (f"ONLY4 flat4 NOT flat[{nm}]", f4 & ~fi & low),
                       (f"ONLYI flat[{nm}] NOT flat4", ~f4 & fi & low)):
            r = score(idx, d, m, tag)
            res.append(r)
            print(line(r))

    print("\n--- ORCH's named ROIs, low-n_eff pixels only (plane coords) ---")
    rois = {"blobB (2048,1300)": (slice(650, 800), slice(1024, 1184)),
            "blobA (4715,1180)": (slice(590, 720), slice(2357, 2507)),
            "matched no-blob": (slice(1984, 2134), slice(424, 584))}
    for nm, sl in rois.items():
        m = np.zeros((h, w), bool)
        m[sl] = True
        r = score(idx, d, m & low, f"{nm} & n_eff<=8")
        res.append(r)
        print(line(r))
        r2 = score(idx, d, m, f"{nm} all pixels")
        res.append(r2)
        print(line(r2))

    print("\n--- what does selection actually do to the ROI, in DN? ---")
    print("  %-20s %10s %10s %10s %10s" % ("region", "gate4 sd", "mean sd", "control sd", "|d| mean"))
    for nm, sl in rois.items():
        print("  %-20s %10.1f %10.1f %10.1f %10.1f"
              % (nm, local_sd(y4)[sl].mean(), local_sd(ym)[sl].mean(),
                 local_sd(yc)[sl].mean(), np.abs(d)[sl].mean()))

    with open(os.path.join(OUT, "decompose.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    print("\nwrote decompose.json")


if __name__ == "__main__":
    main()
