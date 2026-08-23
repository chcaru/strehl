"""M40 verification, script 01 -- RE-CHOOSING the estimator behind SELECTION_INFLATION.

Commit 253e56f multiplies `predicted_sigma` by SELECTION_INFLATION = 1.074 at n = 1,
citing fact 320 (gate-0 flat-ROI ratio on 109MSDCF) and fact 23/321 (M2-verification's
1.075x).  Both of those numbers are produced by ONE estimator:

    ratio = spatial_sd(selected image over the ROI) / spatial_sd(one frame over the ROI)

(`crates/strehl-cli/src/stack.rs::flat_roi_stats`, whose own banner says the two
quantities are "SPATIAL sds of noise plus whatever scene structure the ROI still has").
The constant is then consumed as a multiplier on a TEMPORAL per-sample sigma
(`NoiseModel::green_luma_sigma`).  That is a different physical quantity -- AGENTS.md
rule 10.  Scene structure is common to numerator and denominator, so the spatial-sd
ratio is COMPRESSED TOWARD 1: it under-states the temporal inflation whenever the ROI
carries structure, and by construction it can never be read as a per-pixel noise ratio.

This script re-chooses the estimator.  Everything is measured against a per-pixel
across-frame mean `mu`, which carries the scene structure exactly, so the structure
cancels instead of diluting.

    d = selected - mu          (pure noise + selection bias + residual scene change)

Arms (this is the re-choice of the NULL as well as of the estimator):
  true    the real regularised-argmax winner map
  shift   the same winner map rolled by (+37,+53) plane px.  Preserves the winner
          histogram AND the spatial coherence of the map; destroys the correspondence
          between a pixel's own noise and the frame elected there.  AGENTS.md rule 17's
          shift control.
  shuffle the winner map fully permuted.  Preserves the histogram only.
  fixed   every pixel takes the stack's median winner frame.  No selection at all.

Reported per ROI:
  E1  the author's estimator, spatial_sd(sel)/spatial_sd(middle frame)   [reproduction]
  E2  pixel-domain temporal inflation   sqrt( mean(d^2)_true / mean(d^2)_shift )
  E3  model-referenced                  sqrt( mean(d^2)_true / ((1-1/N)*mean(sigma^2)) )
  E4  GRADIENT-domain inflation         sqrt( grad_energy(d)_true / grad_energy(d)_shift )

E4 is the quantity the detail metric actually needs: `detail_metrics` consumes
`predicted_sigma` inside `2*s_i^2 + s_{i+1}^2 + s_{i+w}^2`, which is a forward-difference
(high-pass) noise power.  E2 is the quantity C1 needs.  If E2 != E4 then ONE scalar
cannot serve both consumers and the repair's LOCATION is wrong.

PRE-REGISTERED PREDICTIONS (AGENTS.md rule 20 -- inputs that would make this fail):
  P1  E2 > 1.074 on the flat ROIs, because the spatial-sd ratio is structure-diluted.
      FAILS IF E2 lands at or below 1.074.
  P2  E4 < E2, because a 27x27-window + 17x17-regularised argmax elects a frame from a
      wide neighbourhood, so the induced excess is spatially correlated and a high-pass
      statistic sees less of it.  FAILS IF E4 >= E2.
  P3  E1 is stack- and ROI-dependent well beyond the 0.6% of fact 320.
      FAILS IF all four flat ROIs land within +-1% of 1.074.
  P4  shift ~= shuffle ~= 1.0 by E2's definition (they are the null).  If the shift arm
      is itself far from the fixed-frame arm, the winner's-curse story is wrong and the
      excess is frame-composition, not per-pixel selection.

Outputs: out/01-inflation-estimators.txt (also stdout) and out/01-inflation.json
"""

import glob
import json
import os
import sys
import time

import numpy as np
import rawpy

BLACK = 512.0
GAIN_DIV = 436.8
RN_E_LOW = 4.20
SIGMA_EPS = 1e-3
WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24

STACKS = {
    "109MSDCF": dict(
        path=r"C:\dev\macro\test\109MSDCF",
        iso=160.0,
        rois={
            # M2 / M38 / M39's flat ROI -- the one fact 320 and fact 428 are measured on.
            "flat-M2 2272,1344": (2272, 1344, 256, 256),
            # M11's independently chosen flattest block on this stack.
            "flat-M11 2352,1408": (2352, 1408, 256, 256),
            # M11's most-detailed block: an ROI where selection is decided by SIGNAL.
            "detail-M11 2080,1056": (2080, 1056, 256, 256),
        },
    ),
    "119MSDCF": dict(
        path=r"C:\dev\macro\test\119MSDCF",
        iso=50.0,
        rois={
            "flat-M11 2896,1968": (2896, 1968, 256, 256),
            "flat-M11 3056,416": (3056, 416, 256, 256),
            "detail-M11 2016,1152": (2016, 1152, 256, 256),
        },
    ),
}

SHIFT = (37, 53)
RNG_SEED = 4041


def sigma_luma(S, g, read_dn):
    return np.sqrt(0.5 * (g * np.maximum(S, 0.0) + read_dn * read_dn))


def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a, 0), 1), ((1, 0), (1, 0)))
    y0 = np.maximum(np.arange(H) - r, 0)
    y1 = np.minimum(np.arange(H) + r, H - 1)
    x0 = np.maximum(np.arange(W) - r, 0)
    x1 = np.minimum(np.arange(W) + r, W - 1)
    s = (
        c[np.ix_(y1 + 1, x1 + 1)]
        - c[np.ix_(y0, x1 + 1)]
        - c[np.ix_(y1 + 1, x0)]
        + c[np.ix_(y0, x0)]
    )
    return s / np.outer(y1 - y0 + 1, x1 - x0 + 1)


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (
        p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]
    ) * 0.125
    gy = (
        p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]
    ) * 0.125
    return np.hypot(gx, gy)


def grad_energy(v):
    """mean(dx^2 + dy^2) over forward differences -- the detail metric's raw_rms^2."""
    dx = v[:-1, 1:] - v[:-1, :-1]
    dy = v[1:, :-1] - v[:-1, :-1]
    return float((dx * dx + dy * dy).mean())


def load_stack(path, iso, rois):
    frames = sorted(glob.glob(os.path.join(path, "*.ARW")))
    assert frames, path
    g = iso / GAIN_DIV
    read_dn = RN_E_LOW * g
    acc = {k: dict(L=[], reg=[]) for k in rois}
    t0 = time.time()
    for fi, p in enumerate(frames):
        r = rawpy.imread(p)
        a = r.raw_image_visible
        for k, (x, y, w, h) in rois.items():
            cx, cy, cw, ch = x - MARGIN, y - MARGIN, w + 2 * MARGIN, h + 2 * MARGIN
            sub = a[2 * cy : 2 * (cy + ch), 2 * cx : 2 * (cx + cw)].astype(np.float64)
            g1 = sub[0::2, 1::2]
            g2 = sub[1::2, 0::2]
            luma_f = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
            focus = box_mean(sobel_mag(luma_f), WINDOW_RADIUS) / np.maximum(
                sigma_luma(luma_f, g, read_dn), SIGMA_EPS
            )
            acc[k]["reg"].append(box_mean(focus, REG_RADIUS).astype(np.float32))
            acc[k]["L"].append(0.5 * (g1 + g2) - BLACK)
        del r, a
        print(f"    frame {fi:2d}  {time.time() - t0:6.1f}s", flush=True)
    return frames, g, read_dn, acc


def main():
    out = open("out/01-inflation-estimators.txt", "w", encoding="utf-8")

    def emit(s=""):
        print(s, flush=True)
        out.write(s + "\n")

    emit("=" * 96)
    emit("M40 script 01 -- four estimators of the gate-0 selection inflation")
    emit("=" * 96)
    emit(f"shift control = roll(win, {SHIFT}) ; shuffle seed = {RNG_SEED}")
    emit("")

    results = {}
    for stack, cfg in STACKS.items():
        emit(f"### stack {stack}   iso {cfg['iso']:.0f}")
        frames, g, read_dn, acc = load_stack(cfg["path"], cfg["iso"], cfg["rois"])
        N = len(frames)
        middle = N // 2
        emit(f"    {N} frames, middle = {middle}, gain {g:.6f} DN/e-, read {read_dn:.4f} DN")
        emit("")
        rng = np.random.default_rng(RNG_SEED)
        sl = (slice(MARGIN, MARGIN + 256), slice(MARGIN, MARGIN + 256))
        for k, (x, y, w, h) in cfg["rois"].items():
            L = np.stack(acc[k]["L"])[:, sl[0], sl[1]]
            R = np.stack(acc[k]["reg"])[:, sl[0], sl[1]]
            win = R.argmax(axis=0)
            mu = L.mean(axis=0)
            sig = sigma_luma(mu, g, read_dn)
            median_win = int(np.median(win))

            yy, xx = np.mgrid[0:h, 0:w]
            arms = {
                "true": win,
                "shift": np.roll(win, SHIFT, axis=(0, 1)),
                "shuffle": rng.permutation(win.ravel()).reshape(win.shape),
                "fixed": np.full_like(win, median_win),
            }
            single = L[middle]
            row = dict(
                mean_dn=float(mu.mean()),
                model_sigma=float(sig.mean()),
                single_spatial_sd=float(single.std(ddof=0)),
                struct_sd=float(np.sqrt(max(0.0, single.var() - float((sig**2).mean())))),
                distinct_winners=int(len(np.unique(win))),
                median_winner=median_win,
                N=N,
                arms={},
            )
            for name, wmap in arms.items():
                sel = L[wmap, yy, xx]
                d = sel - mu
                row["arms"][name] = dict(
                    spatial_sd=float(sel.std(ddof=0)),
                    E1=float(sel.std(ddof=0) / single.std(ddof=0)),
                    pix_var=float((d * d).mean()),
                    grad_energy=grad_energy(d),
                )
            a_t, a_s, a_h, a_f = (row["arms"][n] for n in ("true", "shift", "shuffle", "fixed"))
            null_pix = (1.0 - 1.0 / N) * float((sig**2).mean())
            row["E2_shift"] = float(np.sqrt(a_t["pix_var"] / a_s["pix_var"]))
            row["E2_shuffle"] = float(np.sqrt(a_t["pix_var"] / a_h["pix_var"]))
            row["E2_fixed"] = float(np.sqrt(a_t["pix_var"] / a_f["pix_var"]))
            row["E3_model"] = float(np.sqrt(a_t["pix_var"] / null_pix))
            row["E3_model_shift"] = float(np.sqrt(a_s["pix_var"] / null_pix))
            row["E4_shift"] = float(np.sqrt(a_t["grad_energy"] / a_s["grad_energy"]))
            row["E4_shuffle"] = float(np.sqrt(a_t["grad_energy"] / a_h["grad_energy"]))
            results[f"{stack} | {k}"] = row

            emit(f"  --- ROI {k} ---")
            emit(
                f"    mean {row['mean_dn']:9.2f} DN   model sigma {row['model_sigma']:7.3f} DN   "
                f"spatial sd(1 frame) {row['single_spatial_sd']:8.3f} DN   "
                f"implied structure sd {row['struct_sd']:8.3f} DN"
            )
            emit(
                f"    winners: {row['distinct_winners']} distinct, median {median_win}"
            )
            emit(
                "      arm        E1 spatial-sd    mean(d^2)      grad energy(d)"
            )
            for name in ("true", "shift", "shuffle", "fixed"):
                a = row["arms"][name]
                emit(
                    f"      {name:8s}   {a['E1']:10.4f}x   {a['pix_var']:12.3f}   {a['grad_energy']:14.3f}"
                )
            emit(
                f"    E1 (author's, spatial sd ratio)          = {a_t['E1']:.4f}x   "
                f"[SELECTION_INFLATION is 1.0740x]"
            )
            emit(
                f"    E2 pixel-domain vs shift control         = {row['E2_shift']:.4f}x"
                f"   (vs shuffle {row['E2_shuffle']:.4f}x, vs fixed {row['E2_fixed']:.4f}x)"
            )
            emit(
                f"    E3 pixel-domain vs calibrated model      = {row['E3_model']:.4f}x"
                f"   (shift arm on the same reference {row['E3_model_shift']:.4f}x)"
            )
            emit(
                f"    E4 GRADIENT-domain vs shift control      = {row['E4_shift']:.4f}x"
                f"   (vs shuffle {row['E4_shuffle']:.4f}x)"
            )
            emit("")
        del acc
        emit("")

    json.dump(results, open("out/01-inflation.json", "w"), indent=1)

    emit("=" * 96)
    emit("SUMMARY -- every ROI, side by side")
    emit("=" * 96)
    emit(f"  {'ROI':34s} {'E1':>9s} {'E2 pix':>9s} {'E3 model':>9s} {'E4 grad':>9s}")
    for name, r in results.items():
        emit(
            f"  {name:34s} {r['arms']['true']['E1']:8.4f}x {r['E2_shift']:8.4f}x "
            f"{r['E3_model']:8.4f}x {r['E4_shift']:8.4f}x"
        )
    out.close()


if __name__ == "__main__":
    sys.exit(main())
