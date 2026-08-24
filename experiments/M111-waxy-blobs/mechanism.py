"""M111 -- the mechanism, conditioned.

quantify.py showed the whole-image flat population is *not* where the defect
lives: there the gate admits a median 151 frames of 299 and the luma step across
election boundaries is 1.06x the off-boundary step against a translated null of
1.00 +- 0.07, i.e. nothing. Yet the blobB ROI has median n_eff 2. So the flat
population is two populations, and pooling them hides the defect.

This script splits them on the merge's own admission count and asks, for each
regulariser radius:

  A  mean/median n_eff as a function of best_focus. The gate tolerance is an
     ABSOLUTE constant (threshold * sqrt(2) * FOCUS_NOISE_SD = 0.086063) but the
     focus response is a contrast-scaled quantity, so admission should fall as
     the response rises. If it does, the gate's unit is wrong.
  B  the luma step across election boundaries, restricted to flat AND
     low-admission pixels, against the translated-election null (NC5).
  C  plateau geometry in that same population, as a function of the radius.
     This is the causal test of H1: a box-smoothed argmax has a plateau scale
     set by the box.
  D  the same numbers in a region with genuine texture (NC1) and in the
     high-admission flat population, either of which firing would mean the
     detector is measuring something else.

Usage:  python mechanism.py
"""

import json
import os

import numpy as np
import tifffile
from scipy import ndimage

ROOT = r"C:\dev\strehl-out\M111"
RENDER = os.path.join(ROOT, "render")
RADII = [0, 2, 4, 8, 16, 32]
FLAT_SD = 300.0
LOW_N = 8  # "the merge elected rather than averaged here"
HIGH_N = 64
SHIFTS = [(137, 211), (-263, 89), (451, -337)]
NOISE_CEILING = 0.4330 + 2.94 * 0.015214
MARGIN = 64


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def plane_luma(path):
    y = luma(tifffile.imread(path))
    return 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndimage.uniform_filter(y, k, mode="nearest")
    m2 = ndimage.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def edge_step(idx, y, mask):
    dh = idx[:, 1:].astype(np.int32) != idx[:, :-1].astype(np.int32)
    dv = idx[1:, :].astype(np.int32) != idx[:-1, :].astype(np.int32)
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    step = np.concatenate([np.abs(y[:, 1:] - y[:, :-1])[mh], np.abs(y[1:, :] - y[:-1, :])[mv]])
    on = np.concatenate([dh[mh], dv[mv]])
    if step.size < 5000 or on.sum() < 500 or (~on).sum() < 500:
        return None
    a, b = float(np.median(step[on])), float(np.median(step[~on]))
    return {
        "pairs": int(step.size),
        "boundary_density": float(on.mean()),
        "on": a,
        "off": b,
        "ratio": a / max(b, 1e-9),
        "on_p90": float(np.percentile(step[on], 90)),
        "off_p90": float(np.percentile(step[~on], 90)),
    }


def plateau(idx, mask):
    b = np.zeros(idx.shape, bool)
    b[:, 1:] |= idx[:, 1:] != idx[:, :-1]
    b[1:, :] |= idx[1:, :] != idx[:-1, :]
    lab, n = ndimage.label(mask & ~b, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    if n == 0:
        return {"components": 0}
    s = np.bincount(lab.ravel())[1:].astype(np.float64)
    return {
        "components": int(n),
        "median_px": float(np.median(s)),
        "area_weighted_mean_px": float((s * s).sum() / s.sum()),
        "equiv_diameter_px": float(np.sqrt(4 / np.pi * (s * s).sum() / s.sum())),
    }


def arm(radius, base_flat, base_low, base_high, base_rough, y):
    """Score radius `radius` on masks fixed by the r8 baseline where possible."""
    st = os.path.join(RENDER, f"state-r{radius}")
    tif = os.path.join(RENDER, "marker-dump.tif" if radius == 8 else f"marker-r{radius}.tif")
    idx = np.load(os.path.join(st, "best_index.npy"))
    ne = np.load(os.path.join(st, f"n_eff_gate4.00.npy"))
    bf = np.load(os.path.join(st, "best_focus.npy"))
    yr = plane_luma(tif)
    inner = np.zeros(idx.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    sd = local_sd(yr)
    flat = (sd < FLAT_SD) & inner
    low = flat & (ne <= LOW_N)
    high = flat & (ne >= HIGH_N)
    rough = (sd >= FLAT_SD * 4) & inner

    out = {
        "radius": radius,
        "n_eff_mean_whole": float(ne[inner].mean()),
        "flat_frac": float(flat.mean()),
        "low_frac_of_flat": float(low.sum() / max(flat.sum(), 1)),
        "best_focus_low_median": float(np.median(bf[low])) if low.any() else None,
        "best_focus_high_median": float(np.median(bf[high])) if high.any() else None,
        # B -- own-mask arms (the mask moves with the arm, which is what a user
        # of that radius would see)
        "edge_low": edge_step(idx, yr, low),
        "edge_high": edge_step(idx, yr, high),
        "edge_rough": edge_step(idx, yr, rough),
        # C
        "plateau_low": plateau(idx, low),
        "plateau_high": plateau(idx, high),
        # B on the r8 baseline mask, so the population is IDENTICAL across arms
        "edge_low_fixedmask": edge_step(idx, yr, base_low),
        "plateau_low_fixedmask": plateau(idx, base_low),
    }
    nulls = [edge_step(np.roll(idx, s, (0, 1)), yr, low) for s in SHIFTS]
    nulls = [n for n in nulls if n]
    if nulls:
        out["edge_low_null_ratio_mean"] = float(np.mean([n["ratio"] for n in nulls]))
        out["edge_low_null_ratio_sd"] = float(np.std([n["ratio"] for n in nulls], ddof=1))
        out["edge_low_null_density_mean"] = float(np.mean([n["boundary_density"] for n in nulls]))
    nf = [edge_step(np.roll(idx, s, (0, 1)), yr, base_low) for s in SHIFTS]
    nf = [n for n in nf if n]
    if nf:
        out["edge_low_fixedmask_null_ratio_mean"] = float(np.mean([n["ratio"] for n in nf]))
        out["edge_low_fixedmask_null_ratio_sd"] = float(np.std([n["ratio"] for n in nf], ddof=1))
    return out


def gate_curve(radius=8):
    """A -- admission as a function of the focus response."""
    st = os.path.join(RENDER, f"state-r{radius}")
    ne = np.load(os.path.join(st, "n_eff_gate4.00.npy")).astype(np.float64)
    bf = np.load(os.path.join(st, "best_focus.npy")).astype(np.float64)
    inner = np.zeros(ne.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    b, n = bf[inner], ne[inner]
    edges = [0.0, 0.55, 0.60, 0.65, 0.7, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 1e9]
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (b >= lo) & (b < hi)
        if m.sum() < 1000:
            continue
        rows.append(
            {
                "best_focus_lo": lo,
                "best_focus_hi": hi,
                "px_pct": float(100 * m.mean()),
                "n_eff_mean": float(n[m].mean()),
                "n_eff_median": float(np.median(n[m])),
                "n_eff_le8_pct": float(100 * (n[m] <= 8).mean()),
            }
        )
    return rows


def main():
    st8 = os.path.join(RENDER, "state-r8")
    y8 = plane_luma(os.path.join(RENDER, "marker-dump.tif"))
    ne8 = np.load(os.path.join(st8, "n_eff_gate4.00.npy"))
    inner = np.zeros(ne8.shape, bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True
    sd8 = local_sd(y8)
    flat8 = (sd8 < FLAT_SD) & inner
    low8 = flat8 & (ne8 <= LOW_N)
    high8 = flat8 & (ne8 >= HIGH_N)
    rough8 = (sd8 >= FLAT_SD * 4) & inner
    del ne8, sd8

    res = {"gate_curve_r8": gate_curve(8), "arms": []}
    for r in RADII:
        res["arms"].append(arm(r, flat8, low8, high8, rough8, y8))
        print(f"  arm r{r} done", flush=True)

    dst = os.path.join(ROOT, "mechanism.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    print("\n--- A. admission vs focus response (r8, gate 4.00) ---")
    print(f"{'best_focus band':>18} {'%px':>7} {'n_eff mean':>11} {'median':>8} {'<=8 %':>8}")
    for row in res["gate_curve_r8"]:
        print(
            f"{row['best_focus_lo']:8.2f}..{row['best_focus_hi']:<8.2f} {row['px_pct']:7.2f}"
            f" {row['n_eff_mean']:11.1f} {row['n_eff_median']:8.0f} {row['n_eff_le8_pct']:8.2f}"
        )
    print("\n--- C. plateau scale vs regulariser radius (flat & n_eff<=8) ---")
    print(
        f"{'r':>3} {'n_eff':>7} {'lowfrac':>8} {'equivD own':>11} {'equivD fixed':>13}"
        f" {'edge on/off':>12} {'null':>14} {'bdens':>7}"
    )
    for a in res["arms"]:
        e = a["edge_low_fixedmask"]
        print(
            f"{a['radius']:3d} {a['n_eff_mean_whole']:7.1f} {a['low_frac_of_flat']:8.4f}"
            f" {a['plateau_low']['equiv_diameter_px']:11.1f}"
            f" {a['plateau_low_fixedmask']['equiv_diameter_px']:13.1f}"
            f" {e['ratio']:12.3f}"
            f" {a['edge_low_fixedmask_null_ratio_mean']:8.3f}"
            f"+-{a['edge_low_fixedmask_null_ratio_sd']:.3f} {e['boundary_density']:7.4f}"
        )
    print("\n--- D. controls at r8 ---")
    a8 = [a for a in res["arms"] if a["radius"] == 8][0]
    for k in ("edge_low", "edge_high", "edge_rough"):
        e = a8[k]
        print(
            f"{k:>12}: on {e['on']:8.2f}  off {e['off']:8.2f}  ratio {e['ratio']:6.3f}"
            f"  bdens {e['boundary_density']:.4f}  pairs {e['pairs']}"
        )
    print(
        f"  own-mask null ratio {a8['edge_low_null_ratio_mean']:.3f}"
        f" +- {a8['edge_low_null_ratio_sd']:.3f}"
    )
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
