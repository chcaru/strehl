"""M111 -- the closing figures and the per-ROI numbers.

Three jobs:

 1. The comparative population census, marker against lavendar. The mechanism
    predicts the defect needs a population that is BOTH visually flat and in the
    intermediate focus-response band, because that is the band where the gate's
    absolute tolerance closes. A stack without such a population should not show
    the defect however the merge is configured -- so the census is the
    mechanism's own prediction about which stacks are vulnerable, and lavendar
    is the stack that can refute it.

 2. ORCH's two ROIs, scored on the merge's internal state, so the inherited
    numbers can be answered in their own coordinates.

 3. The headline figure: the worst spot the DATA picks, not the one I picked,
    rendered at gate 4 beside the plain mean of all 299 frames.

Usage:  python final_figs.py
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage

ROOT = r"C:\dev\strehl-out\M111"
RENDER = os.path.join(ROOT, "render")
FLAT_SD, LOW_N, HIGH_N, MARGIN = 300.0, 8, 64, 64
STACKS = {
    "marker": ("state-r8", "marker-dump.tif", "marker-g100000.tif"),
    "lavendar": ("state-lav-g4", "lavendar-g4.tif", "lavendar-g100000.tif"),
}
ROIS = {"blobB-row2": (2048, 1300, 320, 300), "blobA-row4": (4715, 1180, 300, 260)}


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(p):
    y = luma(tifffile.imread(p))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndimage.uniform_filter(y, k, mode="nearest")
    m2 = ndimage.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def band(bf, lo, hi):
    return (bf >= lo) & (bf < hi)


def main():
    out = {}
    print(f"{'stack':>9} {'flat%':>7} {'low%pl':>7} {'low%flat':>9} {'bf<0.7%':>8}"
          f" {'bf 0.7-5%':>10} {'bf>5%':>7} {'flat&bf0.7-5%':>14}")
    for name, (st, f4, fm) in STACKS.items():
        stdir = os.path.join(RENDER, st)
        y = plane_luma(os.path.join(RENDER, f4))
        bf = np.load(os.path.join(stdir, "best_focus.npy"))
        nef = sorted(f for f in os.listdir(stdir) if f.startswith("n_eff_gate"))
        ne = np.load(os.path.join(stdir, nef[0]))
        inner = np.zeros(y.shape, bool)
        inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
        flat = (local_sd(y) < FLAT_SD) & inner
        low = flat & (ne <= LOW_N)
        mid = band(bf, 0.7, 5.0) & inner
        out[name] = {
            "flat_pct": 100 * flat.mean(),
            "low_pct_plane": 100 * low.mean(),
            "low_pct_of_flat": 100 * low.sum() / flat.sum(),
            "bf_lo_pct": 100 * (band(bf, 0.0, 0.7) & inner).mean(),
            "bf_mid_pct": 100 * mid.mean(),
            "bf_hi_pct": 100 * (band(bf, 5.0, 1e9) & inner).mean(),
            "flat_and_mid_pct": 100 * (flat & mid).mean(),
            "n_eff_mean": float(ne[inner].mean()),
        }
        r = out[name]
        print(f"{name:>9} {r['flat_pct']:7.2f} {r['low_pct_plane']:7.2f} {r['low_pct_of_flat']:9.2f}"
              f" {r['bf_lo_pct']:8.2f} {r['bf_mid_pct']:10.2f} {r['bf_hi_pct']:7.2f}"
              f" {r['flat_and_mid_pct']:14.2f}")

    # 2 -- ORCH's ROIs on the merge's own state
    print("\n--- ORCH's ROIs, on the merge's internal state (marker) ---")
    stdir = os.path.join(RENDER, "state-r8")
    y4 = plane_luma(os.path.join(RENDER, "marker-dump.tif"))
    ym = plane_luma(os.path.join(RENDER, "marker-g100000.tif"))
    idx = np.load(os.path.join(stdir, "best_index.npy"))
    bf = np.load(os.path.join(stdir, "best_focus.npy"))
    ne = np.load(os.path.join(stdir, "n_eff_gate4.00.npy"))
    d = y4 - ym
    print(f"{'roi':>12} {'n_eff med':>10} {'bf med':>8} {'winners':>8} {'|D| med':>9}"
          f" {'flat%':>7} {'low%':>7}")
    for nm, (ox, oy, ow, oh) in ROIS.items():
        sl = (slice(oy // 2, oy // 2 + oh // 2), slice(ox // 2, ox // 2 + ow // 2))
        sub_sd = local_sd(y4)[sl]
        f = sub_sd < FLAT_SD
        lw = f & (ne[sl] <= LOW_N)
        out[nm] = {
            "n_eff_median": float(np.median(ne[sl])),
            "best_focus_median": float(np.median(bf[sl])),
            "distinct_winners": int(np.unique(idx[sl]).size),
            "abs_D_median": float(np.median(np.abs(d[sl]))),
            "flat_pct": 100 * f.mean(),
            "low_pct": 100 * lw.mean(),
        }
        r = out[nm]
        print(f"{nm:>12} {r['n_eff_median']:10.1f} {r['best_focus_median']:8.3f}"
              f" {r['distinct_winners']:8d} {r['abs_D_median']:9.1f}"
              f" {r['flat_pct']:7.2f} {r['low_pct']:7.2f}")

    # 3 -- let the data pick the worst 160x150 window in the low population
    inner = np.zeros(y4.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    flat = (local_sd(y4) < FLAT_SD) & inner
    low = flat & (ne <= LOW_N)
    b = np.zeros(idx.shape, bool)
    b[:, 1:] |= idx[:, 1:] != idx[:, :-1]
    b[1:, :] |= idx[1:, :] != idx[:-1, :]
    score = ndimage.uniform_filter((low & b).astype(np.float32), 151, mode="constant")
    score *= ndimage.uniform_filter(low.astype(np.float32), 151, mode="constant")
    cy, cx = np.unravel_index(int(np.argmax(score)), score.shape)
    px, py, pw, ph = int(cx) - 80, int(cy) - 75, 160, 150
    out["worst_window_plane"] = [px, py, pw, ph]
    out["worst_window_output"] = [px * 2, py * 2, pw * 2, ph * 2]
    print(f"\nworst low-population window: plane ({px},{py}) {pw}x{ph}"
          f"  = output ({px * 2},{py * 2}) {pw * 2}x{ph * 2}")

    tiles = []
    for lab, arr, lo, hi in (
        ("gate 4 (shipped)", y4, None, None),
        ("gate 1e5 (mean of 299)", ym, None, None),
        ("D = shipped - mean", np.abs(d), 0.0, 4000.0),
    ):
        a = arr[py:py + ph, px:px + pw]
        if lo is None:
            lo, hi = float(np.percentile(a, 1)), float(np.percentile(a, 99))
        t = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
        tiles.append(np.repeat(np.repeat((t * 255).astype(np.uint8), 2, 0), 2, 1))
    e = idx[py:py + ph, px:px + pw]
    e = (e - e.min()) / max(int(e.max() - e.min()), 1)
    tiles.append(np.repeat(np.repeat((e * 255).astype(np.uint8), 2, 0), 2, 1))
    gap = np.zeros((tiles[0].shape[0], 8), np.uint8)
    sheet = tiles[0]
    for t in tiles[1:]:
        sheet = np.concatenate([sheet, gap, t], 1)
    dst = os.path.join(ROOT, "_M111-headline.png")
    try:
        from PIL import Image, ImageDraw

        im = Image.fromarray(sheet).convert("RGB")
        dr = ImageDraw.Draw(im)
        for i, lab in enumerate(["gate 4 (shipped)", "gate 1e5 (mean of 299)",
                                 "|shipped - mean|", "best_index"]):
            dr.text((i * (pw * 2 + 8) + 6, 4), lab, fill=(255, 255, 0))
        im.save(dst)
        print(f"wrote {dst}")
    except Exception as exc:  # pragma: no cover
        print(f"label pass failed: {exc}")

    with open(os.path.join(ROOT, "final_figs.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)


if __name__ == "__main__":
    main()
