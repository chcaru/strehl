"""M40 verification, script 06 -- RE-CHOOSING THE REFERENCE FRAME for the flat-ROI ratio.

`flat_roi_stats` (crates/strehl-cli/src/stack.rs:653) computes

    ratio = spatial_sd(merged over ROI) / spatial_sd(MIDDLE FRAME over ROI)

and fact 320 reads 1.074x off that column at gate 0.  SELECTION_INFLATION = 1.074 is that
number, moved into `predicted_sigma` as if it were a NOISE inflation.

The denominator is one frame, chosen as `frames.len()/2` -- by POSITION IN THE FILE LIST.
On a through-focus stack, position in the list is depth.  So the denominator is "the frame
that happens to sit at the middle of the focus sweep", which on any given ROI is some
arbitrary defocus.  Script 04 measured that on 109MSDCF's flat ROI the middle frame is only
the 5th sharpest of 22 and the argmax's modal winner carries 1.267x its corrected detail.

RULE 20 -- WHAT WOULD MAKE THIS FAIL.  If 1.074x is a NOISE fact, it is a property of the
merge and must be roughly invariant to which frame sits in the denominator: every frame
carries the same read noise and (at these levels) nearly the same shot noise.  A sweep of
the reference over all N frames should then give a flat line near 1.074.  If instead the
ratio tracks the reference frame's SHARPNESS -- high against blurred frames, ~1.0 against
the frames the argmax elects -- then 1.074 is a FOCUS fact wearing a noise fact's clothes,
and it is not a constant of the merge at all.  A flat line refutes me.

Also reported: the structure/noise decomposition the shipped banner invites.  The banner
prints "model predicts sigma 19.267 DN" beside "single frame 11: sigma 28.201 DN", so it
already knows the denominator is roughly half structure by variance.  Two inversions are
DERIVED from that: what noise inflation the 1.074 implies if structure is assumed EQUAL
between merge and reference, and what it implies once the measured structure difference is
priced in.

Outputs: out/06-reference-sweep.txt, out/06-reference-sweep.json
"""

import glob
import json
import os
import sys

import numpy as np
import rawpy

BLACK = 512.0
GAIN_DIV = 436.8
RN_E_LOW = 4.20
SIGMA_EPS = 1e-3
WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24
FOCUS_NOISE_SD = 0.015214

STACKS = {
    "109MSDCF": dict(
        path=r"C:\dev\macro\test\109MSDCF",
        iso=160.0,
        rois={
            "flat-M2 2272,1344": (2272, 1344, 256, 256),
            "flat-M11 2352,1408": (2352, 1408, 256, 256),
        },
    ),
    "119MSDCF": dict(
        path=r"C:\dev\macro\test\119MSDCF",
        iso=50.0,
        rois={
            "flat-M11 2896,1968": (2896, 1968, 256, 256),
            "flat-M11 3056,416": (3056, 416, 256, 256),
        },
    ),
}


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


def main():
    os.makedirs("out", exist_ok=True)
    out = open("out/06-reference-sweep.txt", "w", encoding="utf-8")

    def emit(s=""):
        print(s, flush=True)
        out.write(s + "\n")

    emit("=" * 100)
    emit("M40 script 06 -- the flat-ROI ratio as a function of WHICH FRAME is the reference")
    emit("=" * 100)
    emit("")
    results = {}
    for stack, cfg in STACKS.items():
        frames = sorted(glob.glob(os.path.join(cfg["path"], "*.ARW")))
        N = len(frames)
        middle = N // 2
        g = cfg["iso"] / GAIN_DIV
        read_dn = RN_E_LOW * g
        acc = {k: dict(L=[], reg=[]) for k in cfg["rois"]}
        for p in frames:
            r = rawpy.imread(p)
            a = r.raw_image_visible
            for k, (x, y, w, h) in cfg["rois"].items():
                cx, cy = x - MARGIN, y - MARGIN
                cw, ch = w + 2 * MARGIN, h + 2 * MARGIN
                sub = a[2 * cy : 2 * (cy + ch), 2 * cx : 2 * (cx + cw)].astype(np.float64)
                g1, g2 = sub[0::2, 1::2], sub[1::2, 0::2]
                lf = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
                focus = box_mean(sobel_mag(lf), WINDOW_RADIUS) / np.maximum(
                    sigma_luma(lf, g, read_dn), SIGMA_EPS
                )
                acc[k]["reg"].append(box_mean(focus, REG_RADIUS).astype(np.float32))
                acc[k]["L"].append((0.5 * (g1 + g2) - BLACK).astype(np.float32))
            del r, a
        sl = (slice(MARGIN, MARGIN + 256), slice(MARGIN, MARGIN + 256))
        emit(f"### stack {stack}  iso {cfg['iso']:.0f}  N={N}  middle frame = f{middle}")
        for k in cfg["rois"]:
            L = np.stack(acc[k]["L"])[:, sl[0], sl[1]].astype(np.float64)
            R = np.stack(acc[k]["reg"])[:, sl[0], sl[1]]
            win = R.argmax(axis=0)
            merged = np.take_along_axis(L, win[None], 0)[0]
            sd_merged = float(merged.std(ddof=0))
            sd = L.std(axis=(1, 2), ddof=0)
            lvl = L.mean(axis=(1, 2))
            # per-frame model sigma for one green-luma sample at that frame's mean level
            mdl = np.sqrt(0.5 * (g * np.maximum(lvl, 0.0) + read_dn * read_dn))
            struct = np.sqrt(np.maximum(sd**2 - mdl**2, 0.0))
            counts = np.bincount(win.ravel(), minlength=N)
            modal = int(np.argmax(counts))
            mdl_m = float(
                np.sqrt(0.5 * (g * max(merged.mean(), 0.0) + read_dn * read_dn))
            )
            struct_m = float(np.sqrt(max(sd_merged**2 - mdl_m**2, 0.0)))

            emit(f"  --- ROI {k} ---")
            emit(f"    merged (gate 0, argmax): spatial sd {sd_merged:.4f} DN   "
                 f"model sigma {mdl_m:.4f}   implied structure {struct_m:.4f}")
            emit("    per-frame reference sweep -- ratio = sd(merged)/sd(frame j):")
            emit("      frame   sd(DN)  structure   ratio   winner%")
            for j in range(N):
                mark = ""
                if j == middle:
                    mark = "  <- SHIPPED REFERENCE (frames.len()/2)"
                if j == modal:
                    mark += "  <- MODAL WINNER"
                emit(
                    f"      f{j:<4d} {sd[j]:8.3f} {struct[j]:10.3f}  "
                    f"{sd_merged / sd[j]:6.4f}x {100 * counts[j] / counts.sum():7.2f}%{mark}"
                )
            ratios = sd_merged / sd
            wsel = counts / counts.sum()
            emit("")
            emit(f"    ratio vs SHIPPED middle f{middle}      : {ratios[middle]:.4f}x")
            emit(f"    ratio vs MODAL WINNER f{modal}        : {ratios[modal]:.4f}x")
            emit(f"    ratio vs winner-WEIGHTED mean sd  : {sd_merged / (wsel * sd).sum():.4f}x")
            emit(f"    ratio vs MEAN of all frames' sd   : {sd_merged / sd.mean():.4f}x")
            emit(f"    ratio vs SHARPEST-sd frame f{int(np.argmax(sd))}     : {ratios.max():.4f}x"
                 f"   (min over references)")
            emit(f"    ratio vs FLATTEST-sd frame f{int(np.argmin(sd))}     : {ratios.min():.4f}x"
                 f"   (max over references)")
            emit(f"    SPREAD over the N choices of reference: "
                 f"{ratios.min():.4f}x .. {ratios.max():.4f}x")
            # DERIVED inversions
            s2n_ref = mdl[middle] ** 2
            inv_equal = float(
                np.sqrt(max(sd_merged**2 - struct[middle] ** 2, 0.0) / s2n_ref)
            )
            inv_true = float(
                np.sqrt(max(sd_merged**2 - struct_m**2, 0.0) / s2n_ref)
            ) if struct_m < sd_merged else float("nan")
            emit("")
            emit("    DERIVED inversions of the same ratio into a NOISE inflation:")
            emit(f"      reference frame f{middle} is {100 * mdl[middle] ** 2 / sd[middle] ** 2:.1f}% "
                 f"noise by variance, {100 * struct[middle] ** 2 / sd[middle] ** 2:.1f}% structure")
            emit(f"      if structure were IDENTICAL in the merge : implied noise inflation "
                 f"{inv_equal:.4f}x")
            emit(f"      with the merge's OWN implied structure    : implied noise inflation "
                 f"{inv_true:.4f}x")
            emit("")
            results[f"{stack} | {k}"] = dict(
                N=N, middle=middle, modal=modal,
                sd_merged=sd_merged, sd=[float(v) for v in sd],
                structure=[float(v) for v in struct], struct_merged=struct_m,
                ratio_mid=float(ratios[middle]), ratio_modal=float(ratios[modal]),
                ratio_weighted=float(sd_merged / (wsel * sd).sum()),
                ratio_min=float(ratios.min()), ratio_max=float(ratios.max()),
                implied_infl_equal_structure=inv_equal,
                implied_infl_measured_structure=inv_true,
                winner_share=[float(v) for v in wsel],
            )
        del acc
        emit("")
    json.dump(results, open("out/06-reference-sweep.json", "w"), indent=1)
    emit("=" * 100)
    emit("SUMMARY")
    emit("=" * 100)
    emit(f"  {'ROI':34s} {'vs middle':>10s} {'vs modal':>10s} {'vs wtd':>9s} "
         f"{'min..max over reference':>26s}")
    for name, r in results.items():
        emit(f"  {name:34s} {r['ratio_mid']:9.4f}x {r['ratio_modal']:9.4f}x "
             f"{r['ratio_weighted']:8.4f}x   {r['ratio_min']:.4f}x .. {r['ratio_max']:.4f}x")
    out.close()


if __name__ == "__main__":
    sys.exit(main())
