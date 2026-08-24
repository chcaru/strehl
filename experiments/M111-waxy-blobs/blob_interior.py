#!/usr/bin/env python3
"""M111 -- blob INTERIORS, with the interior mask defined on the control only.

`decompose.py` produced two results that have to be reconciled:

  * Over the whole plane, in pixels flat in BOTH the render and the single-frame
    control, election seams carry 1.428x the null luma step (+10.4 sd).
  * Inside ORCH's named blobB box the same statistic is 0.634 -- BELOW null.

The boxes are the likely reason: ORCH's 320x300 box contains the blob AND its
surround, so a box statistic mixes the two populations. This script defines the
blob interior the way the defect is defined -- a region the SUBJECT has no
texture in -- using the single-frame control alone, and never the render. Then
it asks, separately for interior and surround:

    does selection (gate 4 minus gate 1e5) ADD local structure there,
    and do the edges of what it adds sit on election seams?

`sd_add` is the diagnostic for the visible defect; the seam ratio is the
diagnostic for the proposed mechanism. They can disagree, and if they do, that
is the finding.
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage as ndi

RENDER = r"C:\dev\strehl-out\M111\render"
ORCH = r"C:\dev\strehl-out\ORCH-thennow"
OUT = r"C:\dev\strehl-out\M111"
_OFF = (-419, -337, -263, -157, 157, 263, 337, 419)
SHIFTS = [(dy, dx) for dy in _OFF for dx in _OFF]

# ORCH's ROIs, full-res render coords -> plane coords (//2), plus a matched
# no-blob region picked by h7_orch.py from the control alone.
ROIS = {"blobB": (1024, 650, 160, 150), "blobA": (2357, 590, 150, 130),
        "matched-noblob": (424, 1984, 160, 150)}


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
    if step.size < 2000 or on.sum() < 200 or (~on).sum() < 200:
        return None
    return float(np.median(step[on])) / max(float(np.median(step[~on])), 1e-9)


def score(idx, f, mask, tag):
    r = stat(idx, f, mask)
    if r is None:
        return {"tag": tag, "npx": int(mask.sum()), "verdict": "UNDERPOWERED"}
    v = np.array([x for x in (stat(np.roll(idx, s, (0, 1)), f, mask) for s in SHIFTS) if x], float)
    mu, sd = float(v.mean()), float(v.std(ddof=1))
    return {"tag": tag, "npx": int(mask.sum()), "real": r, "null_mean": mu, "null_sd": sd,
            "sigma": (r - mu) / sd if sd else float("nan"),
            "rank_p": (int(np.sum(np.abs(v - mu) >= abs(r - mu))) + 1) / (len(v) + 1)}


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

    sd4, sdm, sdc = local_sd(y4), local_sd(ym), local_sd(yc)
    inner = np.zeros((h, w), bool)
    inner[64:-64, 64:-64] = True
    # "The subject has no texture here" -- judged on the control, never the render.
    thr = float(np.percentile(sdc[inner], 40.0))
    smooth = (sdc <= thr) & inner

    print("=" * 108)
    print("M111 -- blob interiors.  'smooth' = flattest 40%% of the SINGLE-FRAME CONTROL (thr %.1f DN)" % thr)
    print("=" * 108)
    print("\nDoes selection ADD local structure where the subject has none?")
    print("  %-16s %7s %9s %9s %9s %9s %9s" %
          ("region", "cover%", "sd ctrl", "sd mean", "sd gate4", "add x", "nEff med"))
    rows = {}
    for nm, (x, y, bw, bh) in ROIS.items():
        box = np.zeros((h, w), bool)
        box[y:y + bh, x:x + bw] = True
        for part, m in (("interior", box & smooth), ("surround", box & ~smooth)):
            if m.sum() < 500:
                print("  %-16s %7.1f  (too few pixels)" % (f"{nm}/{part}", 100 * m.sum() / box.sum()))
                continue
            a, b, c = float(sdc[m].mean()), float(sdm[m].mean()), float(sd4[m].mean())
            rows[f"{nm}/{part}"] = {"cover": float(m.sum() / box.sum()), "sd_ctrl": a,
                                    "sd_mean": b, "sd_gate4": c, "add": c / max(b, 1e-9),
                                    "n_eff_med": float(np.median(ne[m]))}
            print("  %-16s %7.1f %9.1f %9.1f %9.1f %9.2f %9.1f"
                  % (f"{nm}/{part}", 100 * m.sum() / box.sum(), a, b, c, c / max(b, 1e-9),
                     np.median(ne[m])))

    print("\nWhole plane, same 'smooth' definition:")
    for nm, m in (("smooth", smooth), ("textured", ~smooth & inner)):
        print("  %-16s %7.1f %9.1f %9.1f %9.1f %9.2f %9.1f"
              % (nm, 100 * m.sum() / inner.sum(), sdc[m].mean(), sdm[m].mean(), sd4[m].mean(),
                 sd4[m].mean() / max(sdm[m].mean(), 1e-9), np.median(ne[m])))

    print("\nAre the edges of what selection added ON election seams?  (64 nulls)")
    res = []
    for nm, (x, y, bw, bh) in ROIS.items():
        box = np.zeros((h, w), bool)
        box[y:y + bh, x:x + bw] = True
        r = score(idx, d, box & smooth, f"{nm} interior (control-smooth)")
        res.append(r)
        print("  %-38s n=%7d  %s" % (r["tag"], r["npx"],
              "UNDERPOWERED" if "real" not in r else
              "%6.3f  null %6.3f+-%5.3f  %+6.1f sd  p=%.3f"
              % (r["real"], r["null_mean"], r["null_sd"], r["sigma"], r["rank_p"])))
    r = score(idx, d, smooth, "WHOLE PLANE smooth (control)")
    res.append(r)
    print("  %-38s n=%7d  %6.3f  null %6.3f+-%5.3f  %+6.1f sd  p=%.3f"
          % (r["tag"], r["npx"], r["real"], r["null_mean"], r["null_sd"], r["sigma"], r["rank_p"]))
    r = score(idx, d, smooth & (sd4 >= np.percentile(sd4[smooth], 90)),
              "smooth(control) BUT rough in render")
    res.append(r)
    print("  %-38s n=%7d  %6.3f  null %6.3f+-%5.3f  %+6.1f sd  p=%.3f"
          % (r["tag"], r["npx"], r["real"], r["null_mean"], r["null_sd"], r["sigma"], r["rank_p"]))

    with open(os.path.join(OUT, "blob_interior.json"), "w") as fh:
        json.dump({"rows": rows, "seam": res, "thr_dn": thr}, fh, indent=1)
    print("\nwrote blob_interior.json")


if __name__ == "__main__":
    main()
