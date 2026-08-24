#!/usr/bin/env python3
"""M111 -- ORCH's H7 (PSF-heterogeneity averaging), plus a self-audit of M111's
own mask.

TWO JOBS, and the first one is against myself.

JOB A -- MASK INDEPENDENCE (self-audit).
========================================
M111 told ORCH that fact 1444's boundary number is mask-circular because the
mask is a percentile of the arm under test. M111's own `flat` mask is
`local_sd(luma(gate 4)) < 300` -- also the arm under test. The null cancels
mask *shape* artefacts because it reuses the identical mask, but it does not
answer "did selection help decide which pixels are called flat?".

So the headline is re-scored with `flat` defined on two arms that contain no
selection at all:

    gate-1e5   the plain mean of all 299 frames, same alignment/colour/exposure
    control    the single decoded middle frame ORCH built

If +12.00 DN / 1.248 / 97 sigma survives on an independent mask, the finding is
robust. If it collapses, M111 must retract. This is run FIRST and reported
whichever way it goes.

JOB B -- ORCH's H7.
===================
H7: in a smoothly defocused region every frame scores near-zero focus, so the
gate admits nearly the whole bracket, and averaging frames with DIFFERENT PSFs
is an extra blur rather than a denoise. Predictions, in ORCH's numbering:

  P1  elected index locally constant over a LARGE area inside a blob, changing
      discontinuously at its boundary; cells markedly larger than in a matched
      no-blob region.
  P2  the index jump ACROSS a blob boundary is LARGE (many frames), not the
      median 1-frame step. "If blob boundaries are ordinary 1-frame steps, P2
      is dead."
  P3  n_eff HIGH and near-constant inside the blob, dropping or jumping at the
      boundary.
  P4  tightening the gate SHRINKS or KILLS the blobs. "A monotone shrink with
      detail preserved is strong support. No change is a kill."

ORCH believes P3 needs an instrument that does not exist. It exists: M111
shipped per-pixel n_eff at fc4cbf6 behind STREHL_DUMP_MERGE_STATE, so P3 is
answered here rather than deferred.

THE REGION-SELECTION CONTROL ORCH ASKED FOR.
============================================
The matched no-blob region is chosen on the SINGLE-FRAME CONTROL ONLY, by mean
luma and local gradient, never by where the blob is in the merged render. The
search excludes the two ROIs ORCH named and ranks candidates purely on distance
in (luma, gradient) from the blob ROI measured on that same control arm. The
merged render, the election map and n_eff are not read until the region is
fixed, and the chosen coordinates are printed before any of them is opened.

Grid: ORCH's coordinates are full-resolution render space; the planes are the
plane grid at half that. Measured 3520x2344 here, not 3516x2344 -- both
solvers' sidecar headers say 3520 for this bracket.
"""

import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage as ndi

RENDER = r"C:\dev\strehl-out\M111\render"
ORCH = r"C:\dev\strehl-out\ORCH-thennow"
OUT = r"C:\dev\strehl-out\M111"

# ORCH's ROIs, full-resolution render space: (x, y, w, h).
ROI_FULL = {"blobB": (2048, 1300, 320, 300), "blobA": (4715, 1180, 300, 260)}

FLAT_SD = 300.0
LOW_N, HIGH_N, MARGIN = 8, 64, 64
SHIFTS = [(dy, dx) for dy in (-97, -53, 53, 97) for dx in (-89, -61, 61, 89)]


def plane_luma(path):
    """Rec.709 luma on the PLANE grid: the render halved, matching the maps."""
    a = tifffile.imread(path)
    if a.ndim == 3 and a.shape[2] >= 3:
        y = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])
    else:
        y = a.astype(np.float64)
    return y[::2, ::2].astype(np.float32)


def local_sd(y, r=4):
    m = ndi.uniform_filter(y, 2 * r + 1)
    m2 = ndi.uniform_filter(y * y, 2 * r + 1)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def grad_energy(y):
    gx = ndi.sobel(y, axis=1)
    gy = ndi.sobel(y, axis=0)
    return np.hypot(gx, gy)


def roi_plane(name):
    x, y, w, h = ROI_FULL[name]
    return slice(y // 2, y // 2 + h // 2), slice(x // 2, x // 2 + w // 2)


# --------------------------------------------------------------------------
# JOB A: is the headline mask-independent?
# --------------------------------------------------------------------------
def step_on_off(idx, f, mask):
    """Mean |step| in f on vs off election seams, within mask."""
    bh = idx[:, 1:] != idx[:, :-1]
    bv = idx[1:, :] != idx[:-1, :]
    mh = mask[:, 1:] & mask[:, :-1]
    mv = mask[1:, :] & mask[:-1, :]
    dh = np.abs(f[:, 1:] - f[:, :-1])
    dv = np.abs(f[1:, :] - f[:-1, :])
    on = np.concatenate([dh[bh & mh], dv[bv & mv]])
    off = np.concatenate([dh[~bh & mh], dv[~bv & mv]])
    if on.size < 500 or off.size < 500:
        return None
    return {"n_on": int(on.size), "on": float(np.mean(on)), "off": float(np.mean(off))}


def scored(idx, f, mask, tag):
    real = step_on_off(idx, f, mask)
    if real is None:
        return {"tag": tag, "verdict": "TOO FEW PIXELS"}
    ratio = real["on"] / real["off"]
    nulls = []
    for s in SHIFTS:
        r = step_on_off(np.roll(idx, s, (0, 1)), f, mask)
        if r:
            nulls.append(r["on"] / r["off"])
    nm, ns = float(np.mean(nulls)), float(np.std(nulls))
    return {"tag": tag, "n_on": real["n_on"], "on_dn": real["on"], "off_dn": real["off"],
            "excess_dn": real["on"] - real["off"], "ratio": ratio,
            "null": nm, "null_sd": ns,
            "sigma": (ratio - nm) / ns if ns > 0 else float("nan")}


def job_a():
    print("=" * 78)
    print("JOB A -- is M111's headline mask-INDEPENDENT? (self-audit)")
    print("=" * 78)
    y4 = plane_luma(os.path.join(RENDER, "marker-dump.tif"))
    ym = plane_luma(os.path.join(RENDER, "marker-g100000.tif"))
    yc = plane_luma(os.path.join(ORCH, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif"))
    st = os.path.join(RENDER, "state-r8")
    idx = np.load(os.path.join(st, "best_index.npy"))
    ne = np.load(os.path.join(st, "n_eff_gate4.00.npy"))

    # The control arm is a different render size (no common crop); align shapes
    # by cropping all to the smallest common extent. This is a crop, never a
    # resample -- a resample would add blur to the quantity being measured.
    h = min(y4.shape[0], ym.shape[0], yc.shape[0], idx.shape[0])
    w = min(y4.shape[1], ym.shape[1], yc.shape[1], idx.shape[1])
    y4, ym, yc = y4[:h, :w], ym[:h, :w], yc[:h, :w]
    idx, ne = idx[:h, :w], ne[:h, :w]
    print(f"common plane extent: {w}x{h}")

    d = y4 - ym
    inner = np.zeros((h, w), bool)
    inner[MARGIN:-MARGIN, MARGIN:-MARGIN] = True

    rows = []
    for src_name, src in (("gate 4  (ARM UNDER TEST, as reported)", y4),
                          ("gate 1e5 (mean, NO selection)", ym),
                          ("single frame (ORCH control)", yc)):
        flat = (local_sd(src) < FLAT_SD) & inner
        low = flat & (ne <= LOW_N)
        high = flat & (ne >= HIGH_N)
        r_low = scored(idx, d, low, f"low  | flat from {src_name}")
        r_high = scored(idx, d, high, f"high | flat from {src_name}")
        r_low["flat_pct"] = 100.0 * float(np.mean(flat))
        r_low["low_pct"] = 100.0 * float(np.mean(low))
        rows += [r_low, r_high]
        print(f"\n  flat mask from: {src_name}")
        print(f"    flat {r_low['flat_pct']:.2f}% of plane, low population {r_low['low_pct']:.2f}%")
        for r in (r_low, r_high):
            if "ratio" in r:
                print("    %-6s excess %+7.2f DN  ratio %.3f  null %.3f+-%.3f  %+.1f sigma  (n=%d)"
                      % (r["tag"].split("|")[0].strip(), r["excess_dn"], r["ratio"],
                         r["null"], r["null_sd"], r["sigma"], r["n_on"]))
    return rows


# --------------------------------------------------------------------------
# JOB B: ORCH's H7
# --------------------------------------------------------------------------
def pick_matched_region(yc, blob_slices, exclude):
    """Choose a no-blob region using the SINGLE-FRAME CONTROL ONLY.

    Ranked purely on distance in (mean luma, mean |grad|) from the blob ROI as
    measured on this same control arm. The merged render, the election map and
    n_eff are not consulted. Returns (sy, sx) slices.
    """
    ry, rx = blob_slices
    bh, bw = ry.stop - ry.start, rx.stop - rx.start
    g = grad_energy(yc)
    want_l = float(np.mean(yc[ry, rx]))
    want_g = float(np.mean(g[ry, rx]))
    print(f"    target from control: luma {want_l:.1f}  |grad| {want_g:.2f}")

    best, bestd = None, None
    step = 40
    for y0 in range(MARGIN, yc.shape[0] - bh - MARGIN, step):
        for x0 in range(MARGIN, yc.shape[1] - bw - MARGIN, step):
            skip = False
            for ey, ex in exclude:
                if not (x0 + bw < ex.start or x0 > ex.stop or
                        y0 + bh < ey.start or y0 > ey.stop):
                    skip = True
                    break
            if skip:
                continue
            sy, sx = slice(y0, y0 + bh), slice(x0, x0 + bw)
            l = float(np.mean(yc[sy, sx]))
            gg = float(np.mean(g[sy, sx]))
            # Relative distance so neither term dominates by units.
            dd = ((l - want_l) / max(want_l, 1.0)) ** 2 + ((gg - want_g) / max(want_g, 1e-3)) ** 2
            if bestd is None or dd < bestd:
                bestd, best = dd, (sy, sx)
    sy, sx = best
    print(f"    MATCHED no-blob region chosen at plane (x={sx.start}, y={sy.start}) "
          f"{sx.stop - sx.start}x{sy.stop - sy.start}, luma {np.mean(yc[sy, sx]):.1f}, "
          f"|grad| {np.mean(grad_energy(yc)[sy, sx]):.2f}")
    return sy, sx


def cell_stats(idx, ne, sl, tag):
    """P1 and P3: cell size and n_eff inside a region, plus seam jump (P2)."""
    sy, sx = sl
    a = np.asarray(idx[sy, sx]).astype(np.int32)
    n = np.asarray(ne[sy, sx]).astype(np.float64)

    lab, k = ndi.label(np.ones_like(a), structure=np.ones((3, 3)))
    # Connected components of constant index: label each distinct value.
    sizes = []
    for v in np.unique(a):
        m = a == v
        l2, k2 = ndi.label(m)
        if k2:
            sizes += list(np.bincount(l2.ravel())[1:])
    sizes = np.array(sizes, float)
    equiv = 2.0 * np.sqrt(np.median(sizes) / np.pi) if sizes.size else float("nan")

    jh = np.abs(a[:, 1:] - a[:, :-1])
    jv = np.abs(a[1:, :] - a[:-1, :])
    j = np.concatenate([jh[jh > 0], jv[jv > 0]])

    bh = a[:, 1:] != a[:, :-1]
    bv = a[1:, :] != a[:-1, :]
    bdens = float((bh.sum() + bv.sum()) / (bh.size + bv.size))

    # n_eff on seam pixels vs interior pixels, for P3.
    seam = np.zeros_like(a, bool)
    seam[:, 1:] |= bh
    seam[:, :-1] |= bh
    seam[1:, :] |= bv
    seam[:-1, :] |= bv

    return {"tag": tag, "distinct": int(np.unique(a).size),
            "idx_min": int(a.min()), "idx_max": int(a.max()),
            "cell_equiv_px": float(equiv), "boundary_density": bdens,
            "jump_median": float(np.median(j)) if j.size else float("nan"),
            "jump_ge10_pct": 100.0 * float(np.mean(j >= 10)) if j.size else float("nan"),
            "jump_eq1_pct": 100.0 * float(np.mean(j == 1)) if j.size else float("nan"),
            "n_eff_mean": float(n.mean()), "n_eff_median": float(np.median(n)),
            "n_eff_interior_med": float(np.median(n[~seam])) if (~seam).any() else float("nan"),
            "n_eff_seam_med": float(np.median(n[seam])) if seam.any() else float("nan")}


def job_b():
    print()
    print("=" * 78)
    print("JOB B -- ORCH's H7: predictions P1, P2, P3, P4")
    print("=" * 78)
    yc = plane_luma(os.path.join(ORCH, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif"))
    st = os.path.join(RENDER, "state-r8")
    idx = np.load(os.path.join(st, "best_index.npy"))
    ne = np.load(os.path.join(st, "n_eff_gate4.00.npy"))
    h = min(yc.shape[0], idx.shape[0])
    w = min(yc.shape[1], idx.shape[1])
    yc, idx, ne = yc[:h, :w], idx[:h, :w], ne[:h, :w]

    bB, bA = roi_plane("blobB"), roi_plane("blobA")
    print("\n  region selection -- SINGLE-FRAME CONTROL ONLY, before any map is read")
    matched = pick_matched_region(yc, bB, exclude=[bB, bA])

    rows = [cell_stats(idx, ne, bB, "blobB (ORCH's strong case)"),
            cell_stats(idx, ne, bA, "blobA (boundary-only case)"),
            cell_stats(idx, ne, matched, "MATCHED no-blob control")]

    print("\n  P1 cell size / P2 seam jump / P3 n_eff")
    print("  %-28s %7s %7s %8s %8s %8s %9s %9s" %
          ("region", "cells", "equivPx", "jumpMed", ">=10f%", "==1f%", "nEffMed", "nEffSeam"))
    for r in rows:
        print("  %-28s %7d %7.1f %8.1f %8.1f %8.1f %9.1f %9.1f" %
              (r["tag"], r["distinct"], r["cell_equiv_px"], r["jump_median"],
               r["jump_ge10_pct"], r["jump_eq1_pct"], r["n_eff_median"], r["n_eff_seam_med"]))
    return rows, {"matched_x": int(matched[1].start), "matched_y": int(matched[0].start)}


if __name__ == "__main__":
    a = job_a()
    b, sel = job_b()
    with open(os.path.join(OUT, "h7_orch.json"), "w") as fh:
        json.dump({"job_a_mask_independence": a, "job_b_h7": b, "selection": sel}, fh, indent=1)
    print("\nwrote h7_orch.json")
