"""M111 -- quantify the mechanism, with the null beside every number.

Runs on one (render, merge-state) pair, so the identical code path scores every
arm of the regulariser sweep.

Statistics, all on the 3520x2344 plane grid (output coordinates halved):

  S0  the FLAT population. Defined from the rendered luma alone -- local sd
      below a stated absolute threshold -- so the bins and the quantity binned
      against them do not share the merge's internal state (rule 17).
  S1  election boundary DENSITY inside the flat population. A box-smoothed
      argmax has a boundary density set by the box; a bare argmax over noise
      has one set by the pixel.
  S2  the luma STEP across election boundaries, inside the flat population,
      against the step across non-boundary edges in the same population.
      This is the "invented structure" claim as a number.
  S3  the same statistic with the election map TRANSLATED (rule 17, NC5).
      Preserves every spatial statistic of the index map and destroys the
      per-pixel correspondence, so it is the null S2 must beat.
  S4  n_eff inside the flat population against outside it (H2 vs H3).
  S5  best_focus inside the flat population against the derived pure-noise
      ceiling (H1's premise).
  S6  plateau geometry: modal share and mean connected-component area of
      best_index inside the flat population.

Usage:  python quantify.py <state-dir> <render.tif> [label]
"""

import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

# A single frame's regularised response under pure sensor noise has mean
# 0.125*sqrt(12) = 0.4330 (Rayleigh) and SD FOCUS_NOISE_SD = 0.015214
# (merge.rs). The winner is a max over N = 299 draws, which sits at
# E[max of 299 standard normals] = 2.94 SD above the mean.
NOISE_FLOOR = 0.4330
FOCUS_NOISE_SD = 0.015214
NOISE_CEILING = NOISE_FLOOR + 2.94 * FOCUS_NOISE_SD

# Absolute 16-bit-luma local-sd threshold for "flat". Stated, not fitted: it is
# ~1.5% of the render's mean luma (31665), i.e. a region whose 9x9 sd is under
# half a percent of full scale carries no visible structure. Reported alongside
# a 2x-looser and 2x-tighter value so the reader can see the dependence.
FLAT_SD = 300.0
SHIFTS = [(137, 211), (-263, 89), (451, -337)]


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def local_sd(y, r=4):
    k = 2 * r + 1
    m = ndimage.uniform_filter(y, k, mode="nearest")
    m2 = ndimage.uniform_filter(y * y, k, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def edge_stats(idx, y, mask):
    """Luma step across index-change edges vs across index-constant edges.

    Horizontal and vertical neighbour pairs are pooled. A pair counts only when
    BOTH of its pixels are in `mask`, so the two populations are drawn from the
    same region and differ only in whether the election changed.
    """
    out = {}
    dh_idx = idx[:, 1:].astype(np.int32) - idx[:, :-1].astype(np.int32)
    dv_idx = idx[1:, :].astype(np.int32) - idx[:-1, :].astype(np.int32)
    dh_y = np.abs(y[:, 1:] - y[:, :-1])
    dv_y = np.abs(y[1:, :] - y[:-1, :])
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]

    step = np.concatenate([dh_y[mh], dv_y[mv]])
    change = np.concatenate([np.abs(dh_idx[mh]), np.abs(dv_idx[mv])])
    n = step.size
    if n < 1000:
        return {"pairs": int(n), "note": "too few pairs"}
    on = change > 0
    out["pairs"] = int(n)
    out["boundary_density"] = float(on.mean())
    out["step_on_boundary_median"] = float(np.median(step[on])) if on.any() else float("nan")
    out["step_off_boundary_median"] = float(np.median(step[~on])) if (~on).any() else float("nan")
    out["step_on_boundary_p90"] = float(np.percentile(step[on], 90)) if on.any() else float("nan")
    out["step_off_boundary_p90"] = (
        float(np.percentile(step[~on], 90)) if (~on).any() else float("nan")
    )
    out["ratio_median"] = out["step_on_boundary_median"] / max(
        out["step_off_boundary_median"], 1e-9
    )
    big = change >= 10
    if big.sum() > 200:
        out["step_bigjump_median"] = float(np.median(step[big]))
        out["bigjump_density"] = float(big.mean())
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    state, render = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(state)

    rgb = tifffile.imread(render)
    y_full = luma(rgb)
    y = 0.25 * (
        y_full[0::2, 0::2] + y_full[1::2, 0::2] + y_full[0::2, 1::2] + y_full[1::2, 1::2]
    )
    idx = np.load(os.path.join(state, "best_index.npy"))
    bf = np.load(os.path.join(state, "best_focus.npy"))
    ne = np.load(os.path.join(state, "n_eff_gate4.00.npy"))
    assert y.shape == idx.shape, (y.shape, idx.shape)

    res = {"label": label, "state": state, "render": render}
    sd = local_sd(y)
    # Trim the regulariser/window margin: the box is clamped at the border, so
    # the field there has a different support and its argmax is not comparable.
    m = 64
    inner = np.zeros(y.shape, bool)
    inner[m:-m, m:-m] = True

    for tag, thr in (("tight", FLAT_SD / 2), ("main", FLAT_SD), ("loose", FLAT_SD * 2)):
        flat = (sd < thr) & inner
        rough = (sd >= thr * 4) & inner
        r = {
            "flat_sd_threshold": thr,
            "flat_fraction": float(flat.mean()),
            "rough_fraction": float(rough.mean()),
        }
        # S4 -- n_eff
        r["n_eff_flat_median"] = float(np.median(ne[flat]))
        r["n_eff_flat_mean"] = float(ne[flat].mean())
        r["n_eff_flat_eq1_pct"] = float(100 * (ne[flat] <= 1).mean())
        r["n_eff_rough_median"] = float(np.median(ne[rough]))
        r["n_eff_rough_mean"] = float(ne[rough].mean())
        r["n_eff_whole_mean"] = float(ne[inner].mean())
        # S5 -- best_focus against the pure-noise ceiling
        r["best_focus_flat_median"] = float(np.median(bf[flat]))
        r["best_focus_flat_p10"] = float(np.percentile(bf[flat], 10))
        r["best_focus_flat_below_ceiling_pct"] = float(100 * (bf[flat] < NOISE_CEILING).mean())
        r["noise_ceiling"] = NOISE_CEILING
        # S1/S2 -- boundary density and the step across it
        r["real"] = edge_stats(idx, y, flat)
        # S3 -- translated-index null
        nulls = []
        for dy, dx in SHIFTS:
            nulls.append(edge_stats(np.roll(idx, (dy, dx), (0, 1)), y, flat))
        r["null_shifted"] = nulls
        r["null_ratio_median_mean"] = float(np.mean([n["ratio_median"] for n in nulls]))
        r["null_ratio_median_sd"] = float(np.std([n["ratio_median"] for n in nulls], ddof=1))
        # S6 -- plateau geometry inside the flat population
        r["plateau"] = plateau_stats(idx, flat)
        res[tag] = r

    print(json.dumps(res, indent=2))
    dst = os.path.join(r"C:\dev\strehl-out\M111", f"quantify-{label}.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"wrote {dst}", file=sys.stderr)
    return 0


def plateau_stats(idx, flat):
    """Connected components of constant `best_index`, restricted to `flat`."""
    out = {}
    vals, counts = np.unique(idx[flat], return_counts=True)
    out["distinct_winners_in_flat"] = int(vals.size)
    out["modal_share_in_flat"] = float(counts.max() / counts.sum())
    # Component labelling over the whole plane is too slow per-index; label the
    # flat mask split by index changes instead, which is the same partition.
    b = np.zeros(idx.shape, bool)
    b[:, 1:] |= idx[:, 1:] != idx[:, :-1]
    b[1:, :] |= idx[1:, :] != idx[:-1, :]
    interior = flat & ~b
    lab, n = ndimage.label(interior, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    if n == 0:
        out["components"] = 0
        return out
    sizes = np.bincount(lab.ravel())[1:]
    out["components"] = int(n)
    out["mean_component_px"] = float(sizes.mean())
    out["median_component_px"] = float(np.median(sizes))
    out["p90_component_px"] = float(np.percentile(sizes, 90))
    out["area_weighted_mean_px"] = float((sizes.astype(float) ** 2).sum() / sizes.sum())
    out["equivalent_diameter_px"] = float(
        np.sqrt(4.0 / np.pi * (sizes.astype(float) ** 2).sum() / sizes.sum())
    )
    return out


if __name__ == "__main__":
    sys.exit(main())
