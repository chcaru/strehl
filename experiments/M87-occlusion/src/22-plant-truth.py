"""M87 step 22 -- judge the arms by GROUND TRUTH, not by the halo metric.

Addendum 2 D8 records the most uncomfortable measurement in this milestone:
three of four deliberately broken reconstructions still improved ISO on the
plant, one of them with a ground-truth RMSE six orders of magnitude wrong.  A
halo metric measures whether the halo is gone, not whether the answer is right.
So no arm may be certified on ISO alone.

This step re-runs the winning arm -- the per-pixel mode partition of step 20 --
on the plant, where the correct answer is known, and scores it by RMSE against
the all-in-focus composite in the treated band.  Three outcomes are meaningful:

  * RMSE falls    -> the fix is reconstructing, not just flattening.
  * RMSE flat     -> it is cosmetic: it removes the halo by discarding the
                     information that produced it, which for a background whose
                     own focus peak lies outside the forbidden band costs
                     nothing visible but earns no accuracy either.
  * RMSE rises    -> it is doing damage the halo metric cannot see.

It also builds the control that MUST fail and checks that it does: the SAME
plant with the background moved to the SAME depth as the foreground (KB = KF).
That is a non-occluding edge with ground truth.  There is then no second depth
to fall back on, the forbidden band contains the background's own focus peak,
and the partition must wreck it.  If RMSE does not rise there, the remedy is not
doing what this report claims and the claim must be withdrawn.
"""

import importlib.util
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

spec = importlib.util.spec_from_file_location("plant", HERE / "16-plant.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

OUT = HERE.parents[0] / "out"
DATA = HERE.parents[0] / "data"
SHIP = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")

YOKE = 40
KF_MEDIAN = 15
DELTAS = (10, 20, 40)


def build(kb):
    """P.build() with the background depth made a parameter."""
    old = P.KB
    P.KB = kb
    try:
        return P.build()
    finally:
        P.KB = old


def fields(frames):
    return np.stack([L.regularised_field(frames[k], 100.0)
                     for k in range(len(frames))])


def partition(field, frames, treat, kf, delta):
    n, h, w = field.shape
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int32)
    for k in range(n):
        better = (field[k] > best) & ~(treat & (np.abs(kf - k) < delta))
        best[better] = field[k][better]
        arg[better] = k
    sel = np.empty((h, w), np.float32)
    for k in range(n):
        s = arg == k
        if s.any():
            sel[s] = frames[k][s]
    return sel, arg


def run(tag, kb, res):
    frames, alphas, m, f, b, truth, unveiled = build(kb)
    mask = m > 0.5
    sel, argbest = P.merge(frames)
    inside = ndi.median_filter(argbest.astype(np.float32), size=KF_MEDIAN)
    _, (iy, ix) = ndi.distance_transform_edt(~mask, return_indices=True)
    kf = inside[iy, ix]
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    roi = np.zeros(mask.shape, bool)
    roi[P.ROI[0]:P.ROI[1], P.ROI[2]:P.ROI[3]] = True
    treat = roi & (~mask) & (dist <= YOKE)
    band = treat & (dist >= 2)
    far = roi & (~mask) & (dist >= 60)

    pts, nrm = M2.boundary_normals(mask, roi=P.ROI)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]

    def rmse(img, sel_set):
        e = img[sel_set] - truth[sel_set]
        return float(np.sqrt(np.mean(e.astype(np.float64) ** 2)) / P.LEVEL)

    base_iso = M2.score_iso(sel, p, nv, boot=500)
    row = {"kb": kb, "kF_global": int(np.bincount(argbest[mask]).argmax()),
           "F0_ISO": base_iso["ISO"], "F0_ci": base_iso["ISO_ci"],
           "F0_rmse_band": rmse(sel, band), "F0_rmse_far": rmse(sel, far)}
    print(f"\n[{tag}]  KB={kb}  KF={P.KF}")
    print(f"  F0            ISO={row['F0_ISO']:.5f}  "
          f"RMSE band={row['F0_rmse_band']:.4f}  far={row['F0_rmse_far']:.4f}",
          flush=True)

    fld = fields(frames)
    for D in DELTAS:
        s, arg = partition(fld, frames, treat, kf, D)
        r = M2.score_iso(s, p, nv, boot=500)
        rb, rf = rmse(s, band), rmse(s, far)
        row[f"local-d{D}"] = {
            "ISO": r["ISO"], "ISO_ci": r["ISO_ci"],
            "iso_delta_pct": float(100 * (1 - r["ISO"] / max(row["F0_ISO"], 1e-12))),
            "rmse_band": rb, "rmse_far": rf,
            "rmse_band_delta_pct": float(100 * (rb / row["F0_rmse_band"] - 1)),
            "moved_frac": float((treat & (arg != argbest)).sum() / max(treat.sum(), 1)),
        }
        print(f"  F1-local d={D:<3} ISO={r['ISO']:.5f} "
              f"({row[f'local-d{D}']['iso_delta_pct']:+.1f}%)  "
              f"RMSE band={rb:.4f} ({row[f'local-d{D}']['rmse_band_delta_pct']:+.1f}%)"
              f"  far={rf:.4f}  moved={row[f'local-d{D}']['moved_frac']:.3f}",
              flush=True)
        if D == 40 and kb == P.KB:
            P.png(s, OUT / "22-plant-F1-local-d40.png", 0, P.LEVEL)

    # arm F2 for reference, on the same plant, judged the same way
    a = P.alpha_model(m, P.KF, P.SCALE, len(frames))
    est, r2 = P.unmix(frames, a)
    fixed = sel.copy()
    good = (~mask) & np.isfinite(est) & np.isfinite(r2) & (r2 >= 0.5)
    fixed[good] = est[good]
    r = M2.score_iso(fixed, p, nv, boot=500)
    row["F2-unmix"] = {"ISO": r["ISO"], "rmse_band": rmse(fixed, band),
                       "rmse_far": rmse(fixed, far),
                       "coverage_band": float(good[band].mean())}
    print(f"  F2-unmix      ISO={r['ISO']:.5f}  "
          f"RMSE band={row['F2-unmix']['rmse_band']:.4f}  "
          f"far={row['F2-unmix']['rmse_far']:.4f}  "
          f"cover band={row['F2-unmix']['coverage_band']:.3f}", flush=True)
    res[tag] = row
    return sel, truth


def main():
    res = {}
    sel, truth = run("occluding (KB=90, two depths)", P.KB, res)
    run("CONTROL non-occluding (KB=KF=40, one depth)", P.KF, res)

    o = res["occluding (KB=90, two depths)"]["local-d40"]["rmse_band_delta_pct"]
    c = res["CONTROL non-occluding (KB=KF=40, one depth)"]["local-d40"]["rmse_band_delta_pct"]
    print(f"\nRMSE(band) change at d=40:  occluding {o:+.1f}%   "
          f"non-occluding control {c:+.1f}%")
    print("control fails as designed" if c > o + 5 else
          "CONTROL DID NOT FAIL -- the remedy is not depth-selective")
    res["control_fails_as_designed"] = bool(c > o + 5)
    json.dump(res, open(DATA / "22-plant-truth.json", "w"), indent=1)
    P.png(truth, OUT / "22-plant-truth.png", 0, P.LEVEL)
    for f in OUT.glob("22-plant-*.png"):
        Image.open(f).save(SHIP / f"11-PLANT-{f.name[9:]}")
    print("\nwrote data/22-plant-truth.json")


if __name__ == "__main__":
    main()
