"""Does ORCH's "quantisation is not noise" mechanism transfer to a SPATIAL
gradient statistic -- and is M111's headline window above its own level bound?

ORCH's finding is temporal: rounding is a deterministic function of pixel value,
so the same value rounds the same way in every frame, the error is correlated
ACROSS FRAMES, and split-half / frame-difference estimators book the correlated
half as signal. Measured 3.937x against 63.311x for equal-power random dither,
a 16x gap at matched injected power.

M111's headline statistic is gradient energy, which is a SPATIAL difference.
The same argument should apply one axis over: neighbouring pixels holding
similar values round to the SAME level, so the rounding error is correlated
BETWEEN NEIGHBOURS and largely cancels in a first difference, while equal-
variance white dither does not cancel at all. If that holds, then anyone who
modelled quantisation damage on a sharpness, gradient or acutance statistic by
ADDING RANDOM NOISE overstated it -- the mirror image of ORCH's warning, and it
points the other way: their control was too harsh, not too kind, so it would
have condemned work that was fine rather than clearing work that was not.

This also settles a debt to my own discipline P65. That discipline says to
count levels in the window the statistic actually integrates over, not in the
file. M111 verified 62152 levels in the merged FILE and a median 138 per 256 px
tile, but never counted them in the blob interiors specifically -- and a
featureless blob interior is exactly the low-contrast case P65 warns about.

PRE-REGISTERED, before these numbers exist:

  F1 LEVEL COUNT IN THE HEADLINE WINDOW. blobB's merged interior holds >= 12
     distinct levels, my own stated bound. Reported either way. If it holds
     fewer, M111's headline flatness number sits in the regime P65 says fails
     quietly, and I flag it against myself rather than defending it.
  F2 THE TRANSFER. Across tiles, equal-variance white dither inflates gradient
     energy at least 3x more than deterministic rounding of the same step does
     (median ratio >= 3.0). This is ORCH's mechanism in the spatial domain.
  F3 SELF-REFUTATION, registered so the favourable half cannot be banked alone.
     If the median ratio is < 1.5, the mechanism does NOT transfer to spatial
     gradient statistics, ORCH's result is domain-specific rather than general,
     and I report that instead.
  F4 DIRECTION IN FLAT REGIONS. Rounding should REMOVE gradient energy where a
     window is flat enough that neighbours collapse onto one level, while
     dither can only ADD it. Report the fraction of tiles where rounding gives
     a NEGATIVE change. If it is non-zero, a dither-based control cannot even
     reproduce the SIGN of quantisation damage on this statistic.

Reads only from C:\\dev\\strehl-out\\. Writes only
C:\\dev\\strehl-out\\M111-pil-audit\\quant_is_not_noise.json.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M111-pil-audit"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(ORCHDIR, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(ORCHDIR, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")
BLOBS = [("blobA-row4", 4715, 1180, 300, 260), ("blobB-row2", 2048, 1300, 320, 300)]
STEP = 256.0
TILE, STRIDE = 256, 256
SEED = 20260824


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float64)
            + 0.7152 * a[..., 1].astype(np.float64)
            + 0.0722 * a[..., 2].astype(np.float64))


def ge(y):
    gy, gx = np.gradient(y)
    return float(np.sqrt(gx * gx + gy * gy).mean())


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    assert mt.dtype == np.uint16 and ct.dtype == np.uint16

    # --- F1: levels in the headline windows -----------------------------
    print("[F1] distinct levels in the blob windows the statistic integrates over")
    f1 = {}
    for name, x, y, w, h in BLOBS:
        cy, cx = y + h // 2, x + w // 2
        ry, rx = int(h * 0.30), int(w * 0.30)
        for arm, img in (("merged", mt), ("control", ct)):
            win = luma(img[cy - ry:cy + ry, cx - rx:cx + rx])
            n = int(np.unique(np.round(win)).size)
            rngdn = float(win.max() - win.min())
            f1["%s/%s" % (name, arm)] = {"levels": n, "range_dn": rngdn,
                                         "grad_energy": ge(win)}
            print("   %-12s %-8s levels %6d   range %8.1f DN   grad %8.2f"
                  % (name, arm, n, rngdn, ge(win)))
    key = "blobB-row2/merged"
    f1_pass = f1[key]["levels"] >= 12

    # --- F2/F4: rounding against equal-variance dither ------------------
    # Quantisation to step q has error variance q^2/12. Matched exactly.
    sigma = STEP / np.sqrt(12.0)
    rows = []
    for y0 in range(200, mt.shape[0] - TILE - 200, STRIDE * 4):
        for x0 in range(200, mt.shape[1] - TILE - 200, STRIDE * 4):
            win = luma(mt[y0:y0 + TILE, x0:x0 + TILE])
            base = ge(win)
            if base < 1.0:
                continue
            rounded = np.round(win / STEP) * STEP
            dithered = win + rng.normal(0.0, sigma, win.shape)
            d_round = 100.0 * (ge(rounded) - base) / base
            d_dith = 100.0 * (ge(dithered) - base) / base
            rows.append((int(np.unique(np.round(win)).size), base, d_round, d_dith))
    arr = np.asarray(rows, dtype=float)
    print("\n[F2/F4] %d tiles, step %.0f DN, dither sigma %.2f DN (matched variance)"
          % (len(arr), STEP, sigma))

    ratios = np.abs(arr[:, 3]) / np.maximum(np.abs(arr[:, 2]), 1e-9)
    med_ratio = float(np.median(ratios))
    med_round = float(np.median(arr[:, 2]))
    med_dith = float(np.median(arr[:, 3]))
    frac_neg = float(np.mean(arr[:, 2] < 0.0))

    print("   median grad-energy change, deterministic rounding : %+8.2f %%" % med_round)
    print("   median grad-energy change, equal-variance dither  : %+8.2f %%" % med_dith)
    print("   median |dither| / |rounding|                      : %8.2f x" % med_ratio)
    print("   tiles where rounding REMOVES gradient energy      : %8.1f %%"
          % (100.0 * frac_neg))

    print("\n   by level count in the tile")
    bands = [(0, 32), (32, 64), (64, 128), (128, 256), (256, 10 ** 9)]
    byband = []
    for lo, hi in bands:
        m = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
        if not m.sum():
            continue
        r = {"levels_lo": lo, "levels_hi": None if hi > 10 ** 8 else hi,
             "n": int(m.sum()), "median_round_pct": float(np.median(arr[m, 2])),
             "median_dither_pct": float(np.median(arr[m, 3])),
             "median_ratio": float(np.median(ratios[m]))}
        byband.append(r)
        print("     levels [%4d,%-6s) n=%4d   round %+7.2f %%   dither %+7.2f %%   %6.2fx"
              % (lo, "inf" if hi > 10 ** 8 else str(hi), m.sum(),
                 r["median_round_pct"], r["median_dither_pct"], r["median_ratio"]))

    f2 = med_ratio >= 3.0
    f3 = med_ratio < 1.5
    print("\n[pre-registered gates]")
    print("  F1 blobB merged interior >= 12 levels : %s  (%d levels, %.0f DN range)"
          % ("PASS" if f1_pass else "FAIL", f1[key]["levels"], f1[key]["range_dn"]))
    print("  F2 dither >= 3x rounding (transfer)   : %s  (%.2fx)"
          % ("PASS" if f2 else "FAIL", med_ratio))
    print("  F3 self-refutation (<1.5x, no transfer): %s"
          % ("FIRED" if f3 else "not fired"))
    print("  F4 rounding removes energy on %.1f %% of tiles" % (100.0 * frac_neg))
    verdict = ("MECHANISM TRANSFERS: a dither-based quantisation control overstates "
               "damage to gradient statistics" if f2 else
               ("MECHANISM DOES NOT TRANSFER: ORCH's result is domain-specific"
                if f3 else "PARTIAL: transfer present but under the registered 3x bar"))
    print("\nVERDICT: %s" % verdict)

    doc = {"step_dn": STEP, "dither_sigma_dn": sigma, "seed": SEED, "n_tiles": len(arr),
           "F1_blob_windows": f1, "F1_pass": bool(f1_pass),
           "median_round_pct": med_round, "median_dither_pct": med_dith,
           "median_ratio_dither_over_round": med_ratio,
           "frac_tiles_rounding_negative": frac_neg, "by_level_band": byband,
           "gates": {"F2": bool(f2), "F3_fired": bool(f3)}, "verdict": verdict}
    dst = os.path.join(OUT, "quant_is_not_noise.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
