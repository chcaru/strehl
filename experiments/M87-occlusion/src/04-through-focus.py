"""M87 step 4 -- the through-focus volume on ROI_LEG, my own merge, and C2.

C2 is the PREREGISTRATION's *primary falsifier*: if the bright band is already
present in a single unmerged frame at comparable amplitude, the halo is scene
content and not a merge artifact.

Produces, for the registered ROI_LEG box:
  * my independent Python merge at gate 0 (pure selector) and gate 2
  * the argmax frame-index map
  * the frame that maximises the focus field inside the subject   (k_F)
  * the frame that maximises it in the near background band       (k_B)
  * 16-bit PNG crops of each, on a common stretch, for direct comparison
  * the per-frame band profile P_k(d), so the band can be tracked through focus
"""

import json
import pathlib
import sys
import time

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
for p in (OUT, DATA, CACHE):
    p.mkdir(parents=True, exist_ok=True)

STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100.0
MARGIN = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1  # 22 binned px
ROI = L.ROIS["ROI_LEG"]
BOX = (ROI[0] - MARGIN, ROI[1] + MARGIN, ROI[2] - MARGIN, ROI[3] + MARGIN)


def to_png(a, path, lo=None, hi=None, gamma=2.2):
    lo = np.percentile(a, 0.5) if lo is None else lo
    hi = np.percentile(a, 99.7) if hi is None else hi
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)
    return float(lo), float(hi)


def main():
    files = L.frames(STACK)
    n = len(files)
    h = BOX[1] - BOX[0]
    w = BOX[3] - BOX[2]
    print(f"stack {STACK}: {n} frames, box {BOX} -> {h}x{w}", flush=True)

    lum_p = CACHE / "bee3-leg-luma.npy"
    fld_p = CACHE / "bee3-leg-field.npy"
    if lum_p.exists() and fld_p.exists():
        lumas = np.load(lum_p, mmap_mode="r")
        fields = np.load(fld_p, mmap_mode="r")
        print("loaded cached cubes", lumas.shape, fields.shape, flush=True)
    else:
        lumas = np.empty((n, h, w), np.float32)
        fields = np.empty((n, h, w), np.float32)
        t0 = time.time()
        for k, p in enumerate(files):
            _, g1, g2, _ = L.read_planes(p, BOX)
            lm = 0.5 * (np.maximum(g1 - L.BLACK, 0.0) + np.maximum(g2 - L.BLACK, 0.0))
            lumas[k] = lm
            fields[k] = L.regularised_field(lm.astype(np.float64), ISO)
            if k % 50 == 0:
                print(f"  {k}/{n}  {time.time() - t0:.0f}s", flush=True)
        np.save(lum_p, lumas)
        np.save(fld_p, fields)
        print(f"  decoded+filtered in {time.time() - t0:.0f}s", flush=True)

    best = np.asarray(fields).max(axis=0)
    argbest = np.asarray(fields).argmax(axis=0).astype(np.int32)

    # ---- merges ---------------------------------------------------------
    sel = np.take_along_axis(np.asarray(lumas), argbest[None], 0)[0].astype(np.float32)
    tol = np.float32(2.0) * np.float32(L.SQRT2) * np.float32(L.FOCUS_NOISE_SD)
    acc = np.zeros((h, w), np.float64)
    cnt = np.zeros((h, w), np.float64)
    for k in range(n):
        a = (best - np.asarray(fields[k])) <= tol
        acc += np.where(a, np.asarray(lumas[k]), 0.0)
        cnt += a
    g2m = (acc / np.maximum(cnt, 1)).astype(np.float32)
    print(f"gate2: mean n_eff = {cnt.mean():.3f}   frac n_eff==1 = {(cnt == 1).mean():.4%}")

    # ---- mask, from MY merge, and the near band -------------------------
    mask, tau = L.foreground_mask(sel)
    dist = distance_transform_edt(~mask)
    print(f"my-merge Otsu tau = {tau:.1f}   fg frac = {mask.mean():.4f}")

    # k_F: frame maximising the field inside the subject
    inside = mask.copy()
    band = (~mask) & (dist >= 2) & (dist <= 24)
    far = (~mask) & (dist >= 60)
    fmean_in = np.array([np.asarray(fields[k])[inside].mean() for k in range(n)])
    fmean_band = np.array([np.asarray(fields[k])[band].mean() for k in range(n)])
    fmean_far = np.array([np.asarray(fields[k])[far].mean() for k in range(n)]) if far.any() else None
    kF = int(fmean_in.argmax())
    kBand = int(fmean_band.argmax())
    kFar = int(fmean_far.argmax()) if fmean_far is not None else None
    print(f"k_F (subject)   = {kF}")
    print(f"k_band (d 2-24) = {kBand}")
    print(f"k_far (d>=60)   = {kFar}   far pixels = {int(far.sum())}")

    # ---- C2: band profile of merged vs single frames --------------------
    inner = (MARGIN, MARGIN + (ROI[1] - ROI[0]), MARGIN, MARGIN + (ROI[3] - ROI[2]))
    rows = {}
    for tag, img in (
        ("merge-gate0", sel),
        ("merge-gate2", g2m),
        (f"frame-kF-{kF}", np.asarray(lumas[kF]).astype(np.float32)),
        (f"frame-kBand-{kBand}", np.asarray(lumas[kBand]).astype(np.float32)),
        (f"frame-kFar-{kFar}", np.asarray(lumas[kFar]).astype(np.float32)),
        ("frame-0", np.asarray(lumas[0]).astype(np.float32)),
        (f"frame-{n - 1}", np.asarray(lumas[n - 1]).astype(np.float32)),
    ):
        r = L.measure(img, mask, inner, tag)
        rs = L.measure(img, L.shifted_mask(mask, (300, 300)), inner, tag + "-shift")
        rows[tag] = {
            "H": r["H"], "H_signed": r["H_signed"], "d_star": r["d_star"], "W": r["W"],
            "H_shift": rs["H"] if rs else None,
            "E": r["E"].tolist(),
        }
        print(
            f"  {tag:<22} H={r['H']:8.1f}  signed={r['H_signed']:+8.1f}  "
            f"d*={r['d_star']:3d}  H_shift={rs['H'] if rs else float('nan'):8.1f}"
        )

    # ---- crops for the eye ---------------------------------------------
    sub = (300, 800, 100, 800)  # inside the box: a leg edge against background
    ref = sel[sub[0]:sub[1], sub[2]:sub[3]]
    lo, hi = np.percentile(ref, 0.5), np.percentile(ref, 99.7)
    for tag, img in (
        ("merge-gate0", sel),
        ("merge-gate2", g2m),
        (f"frame-kF-{kF}", np.asarray(lumas[kF])),
        (f"frame-kBand-{kBand}", np.asarray(lumas[kBand])),
        (f"frame-kFar-{kFar}", np.asarray(lumas[kFar])),
        ("frame-0", np.asarray(lumas[0])),
    ):
        to_png(np.asarray(img)[sub[0]:sub[1], sub[2]:sub[3]], OUT / f"04-{tag}.png", lo, hi)
    am = argbest[sub[0]:sub[1], sub[2]:sub[3]].astype(np.float32)
    to_png(am, OUT / "04-argmax.png", 0, n - 1, gamma=1.0)
    to_png(mask[sub[0]:sub[1], sub[2]:sub[3]].astype(np.float32), OUT / "04-mask.png", 0, 1, 1.0)

    np.save(CACHE / "bee3-leg-mask.npy", mask)
    np.save(CACHE / "bee3-leg-argbest.npy", argbest)
    np.save(CACHE / "bee3-leg-best.npy", best)
    np.save(CACHE / "bee3-leg-sel.npy", sel)
    np.save(CACHE / "bee3-leg-g2.npy", g2m)
    (DATA / "04-c2.json").write_text(
        json.dumps(
            {
                "box": list(BOX), "roi": list(ROI), "n": n, "kF": kF, "kBand": kBand,
                "kFar": kFar, "tau": float(tau), "mean_n_eff": float(cnt.mean()),
                "frac_n1": float((cnt == 1).mean()),
                "fmean_in": fmean_in.tolist(), "fmean_band": fmean_band.tolist(),
                "fmean_far": fmean_far.tolist() if fmean_far is not None else None,
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("wrote data/04-c2.json")


if __name__ == "__main__":
    sys.exit(main())
