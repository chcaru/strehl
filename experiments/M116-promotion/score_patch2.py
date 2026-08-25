"""score_patch2.py — campaign 5, replacement instrument.

Contract: experiments/M116-promotion/prereg-patchwork2.txt @ 9253125,
committed before any number here existed.

The first instrument (excess Laplacian kurtosis) failed its own registered
plant G1 and is reported as a failure in the report, not repaired. This is a
separate instrument with separate bars H1-H9.

F4 = fraction of coarse-scale gradient pixels above 4x the ROI's own median
gradient. It is a ratio of the ROI's gradient distribution to itself, so a
uniform rescaling -- which is what denoising approximately is -- leaves it
unchanged. Its residual bias runs AGAINST the soft gate and that is registered.

Run:  python experiments/M116-promotion/score_patch2.py
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
MEAS, MAPS = ROOT / "measure", ROOT / "maps"
OUT = ROOT / "patch"
OUT.mkdir(parents=True, exist_ok=True)

PIN = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
PREREG = "prereg-patchwork2.txt @ 9253125"
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
ARMS = ["A0", "A1", "A2", "A3", "A4", "M0", "N1", "P1", "T2"]

BIN = 4        # coarse scale: kills per-pixel noise, keeps contours
MULT = 4.0     # F4 threshold, as a multiple of the ROI's own median gradient
TILE = 256
NEFF_MAX = 10.0

# Named ROIs, fixed in the prereg section 2 with their disclosure.
NAMED = {"bee-3-cpl": {"ROI-W": (256, 768, 384), "ROI-N": (1024, 2560, 256)}}


def luma(a):
    return a if a.ndim == 2 else (0.2126 * a[..., 0] + 0.7152 * a[..., 1]
                                  + 0.0722 * a[..., 2])


def binned(x, f=BIN):
    h, w = x.shape
    h2, w2 = (h // f) * f, (w // f) * f
    return x[:h2, :w2].reshape(h2 // f, f, w2 // f, f).mean(axis=(1, 3))


def f4(roi):
    """The registered metric. Returns (F4, median gradient)."""
    t = binned(roi.astype(np.float64))
    gy, gx = np.gradient(t)
    e = np.hypot(gy, gx).ravel()
    med = float(np.median(e))
    if med <= 0:
        return 0.0, 0.0
    return float((e > MULT * med).mean()), med


def l995(roi):
    """Secondary, magnitude-based and confounded BY CONSTRUCTION. Reported
    only so the size of the denoising confound can be seen."""
    return float(np.percentile(np.abs(ndimage.laplace(roi.astype(np.float64))),
                               99.5))


def blur_matched(roi_a0, target_l995):
    """H5. Bisect sigma so blurred A0 matches A2's L995 to within 1 %.

    Blur creates no contours and corrects no election, so whatever F4 gain it
    shows is the confound, priced. Same construction M87 used to refute its own
    halo blur hypothesis, which is the strongest form of this control we have.
    """
    base = l995(roi_a0)
    if target_l995 >= base:
        return None, None, "target L995 not below A0's; no blur can match"
    lo, hi = 0.0, 8.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        v = l995(ndimage.gaussian_filter(roi_a0.astype(np.float64), mid))
        if v > target_l995:
            lo = mid
        else:
            hi = mid
    sig = 0.5 * (lo + hi)
    b = ndimage.gaussian_filter(roi_a0.astype(np.float64), sig)
    got = l995(b)
    rel = abs(got - target_l995) / max(target_l995, 1e-12)
    if rel > 0.01:
        return sig, b, f"match failed: rel {rel:.4f} > 0.01"
    return sig, b, None


def oriented_mask(a, coh_min=0.6):
    """H7's instrument. IDENTICAL to campaigns 1 and 4 (CB6/CD7)."""
    g = luma(a)
    gy, gx = np.gradient(g)
    jxx = ndimage.gaussian_filter(gx * gx, 2.0)
    jyy = ndimage.gaussian_filter(gy * gy, 2.0)
    jxy = ndimage.gaussian_filter(gx * gy, 2.0)
    tr, det = jxx + jyy, jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr - 4 * det, 0.0))
    coh = np.where(tr > 0, disc / np.maximum(tr, 1e-12), 0.0)
    return coh >= coh_min


def hp_amp(ch, mask):
    hp = ch.astype(np.float64) - ndimage.gaussian_filter(ch.astype(np.float64), 1.5)
    return float(np.sqrt(np.mean(hp[mask] ** 2))) if mask.any() else 0.0


def election_components(idx):
    total = 0
    for v in np.unique(idx):
        _, n = ndimage.label(idx == v)
        total += int(n)
    return total


def auto_rois(gA0, neff):
    """ROI-AUTO. Selection depends only on the UNTREATED arm and on the n_eff
    map, so it cannot favour the treatment."""
    H, W = gA0.shape
    tiles, contrasts = [], []
    for y in range(0, H - TILE + 1, TILE):
        for x in range(0, W - TILE + 1, TILE):
            t = binned(gA0[y:y + TILE, x:x + TILE])
            contrasts.append(float(t.std() / max(t.mean(), 1e-9)))
            tiles.append((y, x))
    cmed = float(np.median(contrasts))
    out = []
    for (y, x), c in zip(tiles, contrasts):
        if c >= cmed:
            continue
        if neff is not None and float(np.median(neff[y:y + TILE,
                                                    x:x + TILE])) >= NEFF_MAX:
            continue
        out.append((y, x, TILE))
    return out, cmed


def main():
    res = {"pinned_sha": PIN, "prereg": PREREG,
           "metric": f"F4 = frac(coarse grad > {MULT}x own median), bin {BIN}",
           "subjects": {}}

    for S in SUBJECTS:
        paths = {a: MEAS / f"{S}__{a}.tif" for a in ARMS}
        if any(not p.exists() for p in paths.values()):
            print(f"{S}: SKIP")
            continue
        print(f"\n=== {S} ===")
        imgs = {a: tifffile.imread(p).astype(np.float32) for a, p in paths.items()}
        lums = {a: luma(v) for a, v in imgs.items()}

        nf = MAPS / f"{S}__T1-neff.tif"
        neff = None
        if nf.exists():
            n = tifffile.imread(nf)
            neff = (n[..., 0] if n.ndim == 3 else n).astype(np.float32)

        rois = dict(NAMED.get(S, {}))
        auto, cmed = auto_rois(lums["A0"], neff)
        print(f"  ROI-AUTO: {len(auto)} tiles "
              f"(contrast < {cmed:.4f} and median n_eff < {NEFF_MAX:.0f})")

        sub = {"named": {}, "auto": {"n_tiles": len(auto),
                                     "contrast_median": cmed}}

        # ---------- named ROIs, case studies ----------
        for name, (y, x, r) in rois.items():
            print(f"\n  --- {name}  y={y} x={x} r={r} ---")
            rec = {"y": y, "x": x, "r": r, "arms": {}}
            for a in ARMS:
                roi = lums[a][y:y + r, x:x + r]
                v, med = f4(roi)
                rec["arms"][a] = {"F4": v, "grad_median": med,
                                  "L995": l995(roi)}
                print(f"    {a:3}  F4 = {v:.5f}   L995 = "
                      f"{rec['arms'][a]['L995']:9.2f}")
            a0, a2 = rec["arms"]["A0"], rec["arms"]["A2"]
            sig, b, err = blur_matched(lums["A0"][y:y + r, x:x + r], a2["L995"])
            if err:
                rec["blur"] = {"error": err, "sigma": sig}
                print(f"    BLUR CONTROL: {err}")
            else:
                bv, _ = f4(b)
                gain_soft = a0["F4"] - a2["F4"]
                gain_blur = a0["F4"] - bv
                ratio = (gain_soft / gain_blur) if gain_blur > 0 else float("inf")
                rec["blur"] = {"sigma": sig, "F4": bv,
                               "gain_soft": gain_soft, "gain_blur": gain_blur,
                               "ratio": ratio}
                print(f"    BLUR CONTROL: sigma = {sig:.4f} px  F4 = {bv:.5f}")
                print(f"      gain soft = {gain_soft:+.5f}   "
                      f"gain blur = {gain_blur:+.5f}   ratio = {ratio:.3f}")
            sub["named"][name] = rec

        # ---------- ROI-AUTO ----------
        if auto:
            per = {a: [] for a in ARMS}
            for (y, x, r) in auto:
                for a in ARMS:
                    per[a].append(f4(lums[a][y:y + r, x:x + r])[0])
            sub["auto"]["median_F4"] = {a: float(np.median(per[a])) for a in ARMS}
            sub["auto"]["per_tile"] = {a: [float(v) for v in per[a]] for a in ARMS}
            print("\n  ROI-AUTO median F4:")
            for a in ARMS:
                print(f"    {a:3}  {np.median(per[a]):.5f}")

        # ---------- H7 cost ----------
        mask = oriented_mask(imgs["A0"])
        sub["oriented_px"] = int(mask.sum())
        for a in ["A1", "A2", "A3", "A4"]:
            ds = [np.log10(hp_amp(imgs[a][..., c], mask) /
                           max(hp_amp(imgs["A0"][..., c], mask), 1e-12))
                  for c in range(3)]
            dl = np.log10(hp_amp(luma(imgs[a]), mask) /
                          max(hp_amp(luma(imgs["A0"]), mask), 1e-12))
            w = float(min(ds[0], ds[2], dl))
            sub.setdefault("D", {})[a] = w
            print(f"  D_worst({a}) = {w:+.5f} dex")

        # ---------- H9 election invariance ----------
        ip = MAPS / f"{S}__A0-index.tif"
        if ip.exists() and rois:
            idx = tifffile.imread(ip)
            idx = idx[..., 0] if idx.ndim == 3 else idx
            for name, (y, x, r) in rois.items():
                c = election_components(idx[y:y + r, x:x + r])
                sub["named"][name]["election_components_A0"] = c
                print(f"  election components in {name} (A0) = {c}")

        res["subjects"][S] = sub

    (OUT / "scores-patch2.json").write_text(json.dumps(res, indent=2),
                                            encoding="utf-8")
    print(f"\nwrote {OUT / 'scores-patch2.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
