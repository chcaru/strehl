"""score_patch.py — campaign 5. Does the soft gate remove the background
patchwork, and what does it cost?

Contract: experiments/M116-promotion/prereg-patchwork.txt @ 5aa8fc7, committed
before any number here existed.

PRIMARY METRIC.  K = excess kurtosis of the Laplacian over a fixed background
ROI, on LINEAR renders.

The reason it is kurtosis and not a magnitude is registered in the prereg and
repeated here because it is the whole design: the soft gate averages more
frames, so it reduces noise by roughly sqrt(n_eff), so ANY metric that is a
magnitude of local difference falls under the treatment whether or not a single
polygon is removed. Excess kurtosis is scale-invariant -- multiply the field by
any constant and it does not move -- so uniform denoising reads zero and only a
change in the SHAPE of the distribution registers. Gaussian noise gives ~0;
piecewise-constant regions give near-zero Laplacian inside each patch and
spikes at the boundaries, i.e. heavy tails, i.e. K >> 0.

Run:  python experiments/M116-promotion/score_patch.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(r"C:\dev\strehl-out\M116")
MEAS = ROOT / "measure"
MAPS = ROOT / "maps"
OUT = ROOT / "patch"
OUT.mkdir(parents=True, exist_ok=True)

PIN = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]

# The compared arms. M0 is the PLANT (gate 0, patchwork known maximal, P18),
# not a treatment under test.
ARMS = ["A0", "A1", "A2", "A3", "A4", "M0", "N1", "P1", "T2"]

MARGIN = 64          # frame margin excluded from ROI search
ROI_MIN = 256        # minimum ROI side
COARSE_SIGMA = 32.0  # "is this defocused" scale -- deliberately far coarser
                     # than the patchwork, so selection is arm-invariant


def load(p: Path) -> np.ndarray:
    return tifffile.imread(p).astype(np.float32)


def luma(a: np.ndarray) -> np.ndarray:
    """Linear luminance. Kept simple and documented: these are linear renders,
    so this is a plain Rec.709 weighting with no transfer function."""
    if a.ndim == 2:
        return a
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])


def coarse_gradient(g: np.ndarray) -> np.ndarray:
    gx = ndimage.gaussian_filter(g, COARSE_SIGMA, order=(0, 1))
    gy = ndimage.gaussian_filter(g, COARSE_SIGMA, order=(1, 0))
    return np.hypot(gx, gy)


def pick_background_roi(g: np.ndarray):
    """Largest square-ish window in the lowest decile of COARSE gradient.

    Selection uses only the coarse (sigma=32) field, which measures whether a
    region is defocused -- a property of the scene, not of an arm. The prereg
    requires this to return the SAME rectangle for every compared arm, and
    verify below checks it rather than assuming it.
    """
    h, w = g.shape
    cg = coarse_gradient(g)
    inner = cg[MARGIN:h - MARGIN, MARGIN:w - MARGIN]
    thr = np.percentile(inner, 10.0)
    flat = np.zeros_like(cg, dtype=bool)
    flat[MARGIN:h - MARGIN, MARGIN:w - MARGIN] = inner <= thr

    # Integral image -> the ROI_MIN window with the most flat pixels. Integer
    # coordinates only; nothing here resamples.
    ii = np.cumsum(np.cumsum(flat.astype(np.int32), axis=0), axis=1)
    r = ROI_MIN

    def win_sum(y, x):
        y0, x0, y1, x1 = y - 1, x - 1, y + r - 1, x + r - 1
        tot = ii[y1, x1]
        if y0 >= 0:
            tot -= ii[y0, x1]
        if x0 >= 0:
            tot -= ii[y1, x0]
        if y0 >= 0 and x0 >= 0:
            tot += ii[y0, x0]
        return tot

    step = 16
    best, best_yx = -1, (MARGIN, MARGIN)
    for y in range(MARGIN, h - MARGIN - r, step):
        for x in range(MARGIN, w - MARGIN - r, step):
            s = win_sum(y, x)
            if s > best:
                best, best_yx = s, (y, x)
    y, x = best_yx
    return (int(y), int(x), r, float(best) / (r * r))


def laplacian_kurtosis(g: np.ndarray):
    """Excess kurtosis of the Laplacian. Scale-invariant by construction."""
    lap = ndimage.laplace(g.astype(np.float64))
    v = lap.ravel()
    v = v - v.mean()
    sd = v.std()
    if sd <= 0:
        return 0.0, 0.0
    k = float(np.mean((v / sd) ** 4) - 3.0)
    return k, float(sd)


def hf_energy(g: np.ndarray) -> float:
    """RMS of the Laplacian -- a MAGNITUDE, deliberately, and only used for the
    manufacturing control G7 where absolute structure is the question."""
    return float(np.sqrt(np.mean(ndimage.laplace(g.astype(np.float64)) ** 2)))


def oriented_highpass(a: np.ndarray, coh_min=0.6):
    """D's instrument: highpass amplitude on oriented content. IDENTICAL to
    campaigns 1 and 4 (CB6/CD7) so the cost is comparable across M116."""
    g = luma(a)
    gy, gx = np.gradient(g)
    jxx = ndimage.gaussian_filter(gx * gx, 2.0)
    jyy = ndimage.gaussian_filter(gy * gy, 2.0)
    jxy = ndimage.gaussian_filter(gx * gy, 2.0)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr - 4 * det, 0.0))
    coh = np.where(tr > 0, disc / np.maximum(tr, 1e-12), 0.0)
    return coh >= coh_min


def hp_amp(ch: np.ndarray, mask: np.ndarray) -> float:
    hp = ch.astype(np.float64) - ndimage.gaussian_filter(ch.astype(np.float64), 1.5)
    return float(np.sqrt(np.mean(hp[mask] ** 2))) if mask.any() else 0.0


def sha_of(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def main():
    results = {"pinned_sha": PIN,
               "prereg": "prereg-patchwork.txt @ 5aa8fc7",
               "metric": "excess kurtosis of Laplacian over background ROI, linear",
               "subjects": {}}

    for S in SUBJECTS:
        paths = {a: MEAS / f"{S}__{a}.tif" for a in ARMS}
        missing = [a for a, p in paths.items() if not p.exists()]
        if missing:
            print(f"{S}: SKIP, missing arms {missing}")
            continue
        print(f"\n=== {S} ===")

        imgs = {a: load(p) for a, p in paths.items()}
        lums = {a: luma(v) for a, v in imgs.items()}

        # ---- ROI selection, computed independently per arm ----------------
        rois = {a: pick_background_roi(lums[a]) for a in
                ["A0", "A1", "A2", "A3", "A4", "M0"]}
        uniq = sorted({(r[0], r[1], r[2]) for r in rois.values()})
        roi_invariant = (len(uniq) == 1)
        if roi_invariant:
            y, x, r = uniq[0]
            print(f"  ROI selection is ARM-INVARIANT: y={y} x={x} r={r}")
        else:
            # Registered fallback, named in the prereg in advance.
            y, x, r, _ = rois["M0"]
            print(f"  ROI selection is ARM-DEPENDENT ({len(uniq)} distinct). "
                  f"Falling back to the M0 ROI as registered: y={y} x={x} r={r}")
            for a, rr in rois.items():
                print(f"      {a}: y={rr[0]} x={rr[1]} flat_frac={rr[3]:.3f}")

        sub = {"roi": {"y": int(y), "x": int(x), "r": int(r),
                       "arm_invariant": bool(roi_invariant),
                       "per_arm": {a: [int(v[0]), int(v[1]), int(v[2]), v[3]]
                                   for a, v in rois.items()}},
               "arms": {}}

        # ---- primary metric per arm ---------------------------------------
        for a in ARMS:
            roi = lums[a][y:y + r, x:x + r]
            K, sd = laplacian_kurtosis(roi)
            sub["arms"][a] = {
                "K": K,
                "lap_sd": sd,
                "hf": hf_energy(roi),
                "roi_mean": float(roi.mean()),
                "sha256": sha_of(paths[a]),
            }
            print(f"  {a:3}  K = {K:9.3f}   lap_sd = {sd:10.2f}   "
                  f"mean = {roi.mean():9.1f}")

        # ---- detail cost D, vs A0 -----------------------------------------
        mask = oriented_highpass(imgs["A0"])
        sub["oriented_px"] = int(mask.sum())
        for a in ["A1", "A2", "A3", "A4"]:
            ds = []
            for ci, cname in enumerate("RGB"):
                off = hp_amp(imgs["A0"][..., ci], mask)
                on = hp_amp(imgs[a][..., ci], mask)
                ds.append(np.log10(on / off) if off > 0 else 0.0)
            dl = np.log10(hp_amp(luma(imgs[a]), mask) /
                          max(hp_amp(luma(imgs["A0"]), mask), 1e-12))
            sub["arms"][a]["D_R"] = float(ds[0])
            sub["arms"][a]["D_B"] = float(ds[2])
            sub["arms"][a]["D_L"] = float(dl)
            sub["arms"][a]["D_worst"] = float(min(ds[0], ds[2], dl))
            print(f"  {a:3}  D_worst = {min(ds[0], ds[2], dl):+.5f} dex")

        # ---- election polygons over the same ROI (G9) ----------------------
        idxp = MAPS / f"{S}__A0-index.tif"
        if idxp.exists():
            idx = tifffile.imread(idxp)
            if idx.ndim == 3:
                idx = idx[..., 0]
            sub["election"] = election_stats(idx[y:y + r, x:x + r])
            print(f"  election polygons in ROI (A0): "
                  f"{sub['election']['components']}  "
                  f"distinct frames = {sub['election']['distinct']}")

        neffp = MAPS / f"{S}__T1-neff.tif"
        if neffp.exists():
            ne = tifffile.imread(neffp)
            if ne.ndim == 3:
                ne = ne[..., 0]
            sub["neff_A0"] = {
                "bg_median": float(np.median(ne[y:y + r, x:x + r])),
                "detail_median": float(np.median(ne[mask])),
            }
            print(f"  n_eff(A0)  background = "
                  f"{sub['neff_A0']['bg_median']:.2f}   detail = "
                  f"{sub['neff_A0']['detail_median']:.2f}")

        results["subjects"][S] = sub

    (OUT / "scores-patch.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT / 'scores-patch.json'}")
    return 0


def election_stats(idx: np.ndarray):
    """Connected components of constant elected frame index."""
    total = 0
    vals = np.unique(idx)
    for v in vals:
        _, n = ndimage.label(idx == v)
        total += int(n)
    return {"components": total, "distinct": int(vals.size),
            "px": int(idx.size)}


if __name__ == "__main__":
    sys.exit(main())
