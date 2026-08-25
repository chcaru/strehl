"""M120 step 6 — the instrument.

Two jobs:
  (A) define the background ROI from the INPUT CUBE ALONE, at a band that
      excludes the defocus gradient seen in step 5 (which is smooth but steep,
      and which contaminated the 3-24 px band used in 04b);
  (B) build and validate the metric

          Q(I) = ||B I||_ROI / max_k ||B f_k||_ROI

      B linear => for SPATIALLY CONSTANT convex weights w,
          ||B (sum_k w_k f_k)|| <= sum_k w_k ||B f_k|| <= max_k ||B f_k||
      so Q > 1 is a PROOF that the merge weights varied spatially, i.e. that
      the merge manufactured structure the inputs do not contain. No aesthetic
      judgement is involved.

Controls, pre-registered direction BEFORE running (prereg 5, rule 6):
  NULL-1  plain unweighted mean of all frames.  Constant weights.
          PREDICT Q <= 1.00 exactly. A value above 1 means my code is wrong.
  NULL-2  DECOUPLED-ELECTION control (answers M111 P8 directly): take the
          gate-0 elected-index field UNCHANGED and gather from a cube in which
          every frame is a copy of one real frame. The polygons are still in
          the index map; the inter-frame differences are gone.
          PREDICT Q == 1.00 exactly. If the metric fires here it is responding
          to the index map, not to manufactured structure.
  POS     a planted patchwork: random Voronoi cells over the ROI of a single
          real frame, each offset by a draw matched to the OBSERVED inter-frame
          ROI-mean spread. PREDICT Q >= 1.5. If it does not fire the instrument
          is dead and no negative result from it may be believed.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\src")))
import m87lib as L  # noqa: E402

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
HERE = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

TIGHT = (330, 610, 150, 570)
BANDS = [(1.0, 4.0), (2.0, 8.0), (4.0, 16.0), (8.0, 32.0)]
ROI_BAND = (2.0, 8.0)
ISO = 100.0
RMS_K = 17


def bp(a, s):
    a = np.asarray(a, np.float32)
    return ndi.gaussian_filter(a, s[0]) - ndi.gaussian_filter(a, s[1])


def lrms(a):
    return np.sqrt(np.maximum(ndi.uniform_filter(a * a, RMS_K), 0.0))


def largest_square(mask):
    h, w = mask.shape
    dp = np.zeros((h, w), np.int32)
    best = (0, 0, 0)
    m = mask.astype(np.int32)
    for y in range(h):
        row, prev = dp[y], (dp[y - 1] if y else None)
        for x in range(w):
            if m[y, x]:
                row[x] = 1 if (y == 0 or x == 0) else 1 + min(prev[x], row[x - 1], prev[x - 1])
                if row[x] > best[0]:
                    best = (row[x], y, x)
    s, y, x = best
    return (y - s + 1, y + 1, x - s + 1, x + 1), s


def main() -> int:
    y0, y1, x0, x1 = TIGHT
    h, w = y1 - y0, x1 - x0
    cube = np.load(M87 / "bee3-leg-luma.npy", mmap_mode="r")
    n = cube.shape[0]

    # ---------- (A) ROI from the input cube alone ------------------------
    lvl = float(np.array(cube[n // 2, y0:y1, x0:x1]).mean())
    sig = float(L.green_luma_sigma(np.array([[lvl]]), ISO)[0, 0])
    rng = np.random.default_rng(20250120)
    nullmax = np.zeros((h, w), np.float32)
    for _ in range(n):
        np.maximum(nullmax, lrms(bp(rng.normal(0, sig, (h, w)), ROI_BAND)), out=nullmax)
    floor = float(np.median(nullmax))

    maxbp = np.zeros((h, w), np.float32)
    frames = np.empty((n, h, w), np.float32)
    for k in range(n):
        f = np.array(cube[k, y0:y1, x0:x1], np.float32)
        frames[k] = f
        np.maximum(maxbp, lrms(bp(f, ROI_BAND)), out=maxbp)

    thr = 2.0 * floor
    smooth = maxbp <= thr
    er = ndi.binary_erosion(smooth, np.ones((21, 21), bool))
    (ay0, ay1, ax0, ax1), side = largest_square(er)
    print(f"[A] ROI band {ROI_BAND}: model sigma {sig:.2f} DN, "
          f"max-over-{n} null floor {floor:.3f} DN, threshold {thr:.3f} DN")
    print(f"    maxbp percentiles: " + "  ".join(
        f"p{q}={np.percentile(maxbp, q):.2f}" for q in (1, 5, 10, 25, 50, 90)))
    print(f"    smooth-in-every-frame: {100 * smooth.mean():.2f}% of crop; "
          f"largest square {side} px at crop coords ({ay0},{ay1},{ax0},{ax1})")
    if side < 96:
        print("    !! square < 96 px -- falling back to the eroded MASK as ROI")
    roi = np.zeros((h, w), bool)
    roi[ay0:ay1, ax0:ax1] = True
    mask_roi = er.copy()
    print(f"    eroded mask ROI: {int(mask_roi.sum())} px")

    lev = frames.reshape(n, -1)[:, mask_roi.ravel()].mean(1) if mask_roi.any() else frames.reshape(n, -1).mean(1)
    print(f"    per-frame ROI mean level: min {lev.min():.1f} max {lev.max():.1f} "
          f"sd {lev.std():.1f} DN  (this is the size of the step a frame swap can make)")

    # ---------- (B) arms -------------------------------------------------
    arg = np.load(M87 / "bee3-leg-argbest.npy")[y0:y1, x0:x1]
    sel = np.load(M87 / "bee3-leg-sel.npy")[y0:y1, x0:x1].astype(np.float32)
    g2 = np.load(M87 / "bee3-leg-g2.npy")[y0:y1, x0:x1].astype(np.float32)
    mean = frames.mean(0)

    # NULL-2: same index field, zero inter-frame difference
    ref = frames[n // 2]
    null2 = ref.copy()

    # POS: planted patchwork on one real frame, cells ~ observed plateau size,
    # offsets ~ observed inter-frame ROI-mean spread
    pr = np.random.default_rng(7)
    ncell = 40
    sy = pr.integers(0, h, ncell)
    sx = pr.integers(0, w, ncell)
    yy, xx = np.mgrid[0:h, 0:w]
    d = (yy[None] - sy[:, None, None]) ** 2 + (xx[None] - sx[:, None, None]) ** 2
    cell = d.argmin(0)
    off = pr.normal(0.0, float(lev.std()), ncell).astype(np.float32)
    pos = ref + off[cell]

    def q(img, where):
        out = {}
        for b in BANDS:
            num = float(np.sqrt((bp(img, b)[where] ** 2).mean()))
            den = max(float(np.sqrt((bp(f, b)[where] ** 2).mean())) for f in frames)
            out[f"{b[0]:g}-{b[1]:g}"] = (num, den, num / den)
        return out

    arms = {
        "gate0-argmax (the brief's image)": sel,
        "gate2": g2,
        "NULL-1 plain mean": mean,
        "NULL-2 decoupled election": null2,
        "POS planted patchwork": pos,
    }
    where = mask_roi if mask_roi.sum() > 4000 else roi
    print(f"\n[B] Q = ||B merge|| / max_k ||B frame_k||   over {int(where.sum())} ROI px")
    print(f"{'arm':36s}" + "".join(f"{b[0]:g}-{b[1]:g}".rjust(12) for b in BANDS))
    res = {}
    for name, img in arms.items():
        r = q(img, where)
        res[name] = r
        print(f"{name:36s}" + "".join(f"{r[k][2]:12.3f}" for k in r))

    dens = {k: res["gate0-argmax (the brief's image)"][k][1] for k in res["gate0-argmax (the brief's image)"]}
    print("\nmax_k ||B frame_k|| (DN, the denominator):", {k: round(v, 3) for k, v in dens.items()})

    np.save(OUT / "roi_mask.npy", where)
    np.save(OUT / "roi_frames_level.npy", lev)
    (HERE / "roi_final.json").write_text(json.dumps({
        "crop_tight": [int(v) for v in TIGHT],
        "roi_band": list(ROI_BAND),
        "model_sigma_dn": sig,
        "null_floor_dn": floor,
        "threshold_dn": thr,
        "smooth_fraction": float(smooth.mean()),
        "largest_square_crop_coords": [int(ay0), int(ay1), int(ax0), int(ax1)],
        "largest_square_side": int(side),
        "mask_px": int(where.sum()),
        "frame_level_sd_dn": float(lev.std()),
        "Q": {k: {b: [round(x, 4) for x in v] for b, v in r.items()} for k, r in res.items()},
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {HERE / 'roi_final.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
