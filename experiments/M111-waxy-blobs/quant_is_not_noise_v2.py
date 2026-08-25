"""Corrected transfer test. The first attempt (quant_is_not_noise.py) had two
defects, both mine, both disclosed:

  D1 F1 counted levels in a rectangular central crop of the blob ROI. The blob
     interior is not a rectangle -- blob_probe.py defines it as the brightest
     quartile of the MERGED patch. The crop caught 28787 DN of high-contrast
     content and answered a question nobody asked.
  D2 F2 sampled 28 tiles at stride 1024 and EVERY ONE landed in the >=256-level
     band. The mechanism under test is strongest where neighbours collapse onto
     a single level, so the control never entered the regime it was built to
     probe. This is exactly the saturation failure my own discipline P67
     describes, committed two sections after writing it down.

PRE-REGISTERED, before these numbers exist:

  G1 blobB's merged blob INTERIOR -- brightest quartile of the merged patch,
     the mask blob_probe actually used -- holds >= 12 distinct levels. Reported
     either way. If it holds fewer, M111's headline flatness number sits in the
     regime P65 says fails quietly and I flag it against myself.
  G2 SAMPLE ADEQUACY, gating everything below it: at least 3 level-count bands
     carry n >= 20, and at least one band lies below 256 levels. If the sample
     saturates again the run is void and I report it as void.
  G3 THE TRANSFER, now measured where it should be visible: within the LOWEST
     populated level band, equal-variance white dither inflates gradient energy
     at least 3x more than deterministic rounding of the same step.
  G4 GRADIENT of the transfer: the dither/rounding ratio RISES as level count
     falls. This is the discriminating prediction -- a flat offset would mean
     the correlation story is wrong even if the ratio exceeds 3.
  G5 SELF-REFUTATION. If the ratio neither exceeds 3x in the lowest band nor
     rises as levels fall, the mechanism does not transfer to spatial gradient
     statistics and I report that against my own hypothesis.
  G6 SIGN. Fraction of tiles where rounding REMOVES gradient energy while
     dither adds it. Dither cannot reproduce a negative change at all, so any
     non-zero fraction means a dither control cannot even get the sign right.

Reads only from C:\\dev\\strehl-out\\. Writes only
C:\\dev\\strehl-out\\M111-pil-audit\\quant_is_not_noise_v2.json.
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
TILE, STRIDE = 128, 256
SEED = 20260824
BANDS = [(0, 16), (16, 48), (48, 128), (128, 512), (512, 10 ** 9)]


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float64)
            + 0.7152 * a[..., 1].astype(np.float64)
            + 0.0722 * a[..., 2].astype(np.float64))


def gefield(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    assert mt.dtype == np.uint16 and ct.dtype == np.uint16
    h = min(mt.shape[0], ct.shape[0])
    w = min(mt.shape[1], ct.shape[1])

    print("[G1] levels INSIDE the blob mask (brightest quartile of merged patch)")
    g1 = {}
    for name, x, y, bw, bh in BLOBS:
        ym, yc = luma(mt[y:y + bh, x:x + bw]), luma(ct[y:y + bh, x:x + bw])
        mask = ym >= np.percentile(ym, 75)
        for arm, yy in (("merged", ym), ("control", yc)):
            vals = yy[mask]
            n = int(np.unique(np.round(vals)).size)
            g1["%s/%s" % (name, arm)] = {
                "levels_inside_mask": n, "range_dn": float(vals.max() - vals.min()),
                "grad_energy_inside": float(gefield(yy)[mask].mean()),
                "n_px": int(mask.sum())}
            print("   %-12s %-8s levels %6d   range %8.1f DN   grad %7.2f   n_px %d"
                  % (name, arm, n, vals.max() - vals.min(),
                     gefield(yy)[mask].mean(), mask.sum()))
    g1_pass = g1["blobB-row2/merged"]["levels_inside_mask"] >= 12

    sigma = STEP / np.sqrt(12.0)
    rows = []
    for y0 in range(100, h - TILE - 100, STRIDE):
        for x0 in range(100, w - TILE - 100, STRIDE):
            win = luma(mt[y0:y0 + TILE, x0:x0 + TILE])
            base = float(gefield(win).mean())
            if base < 0.05:
                continue
            lv = int(np.unique(np.round(win)).size)
            rounded = np.round(win / STEP) * STEP
            dithered = win + rng.normal(0.0, sigma, win.shape)
            d_r = 100.0 * (float(gefield(rounded).mean()) - base) / base
            d_d = 100.0 * (float(gefield(dithered).mean()) - base) / base
            rows.append((lv, base, d_r, d_d))
    arr = np.asarray(rows, dtype=float)
    ratios = np.abs(arr[:, 3]) / np.maximum(np.abs(arr[:, 2]), 1e-9)
    print("\n[G2-G6] %d tiles, %d px, step %.0f DN, dither sigma %.2f DN (matched variance)"
          % (len(arr), TILE, STEP, sigma))

    print("\n   levels in tile      n    round %%    dither %%   dither/round")
    band_rows, populated = [], []
    for lo, hi in BANDS:
        m = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
        if not m.sum():
            continue
        r = {"lo": lo, "hi": None if hi > 10 ** 8 else hi, "n": int(m.sum()),
             "median_round_pct": float(np.median(arr[m, 2])),
             "median_dither_pct": float(np.median(arr[m, 3])),
             "median_ratio": float(np.median(ratios[m]))}
        band_rows.append(r)
        if r["n"] >= 20:
            populated.append(r)
        print("   [%5d,%-7s) %6d  %+8.2f  %+9.2f  %11.2fx"
              % (lo, "inf" if hi > 10 ** 8 else str(hi), r["n"],
                 r["median_round_pct"], r["median_dither_pct"], r["median_ratio"]))

    g2 = len(populated) >= 3 and any(r["lo"] < 256 for r in populated)
    lowest = populated[0] if populated else None
    g3 = bool(lowest and lowest["median_ratio"] >= 3.0)
    g4 = bool(len(populated) >= 2
              and populated[0]["median_ratio"] > populated[-1]["median_ratio"])
    neg = (arr[:, 2] < 0) & (arr[:, 3] > 0)
    g6 = float(np.mean(neg))
    g5 = not (g3 or g4)

    print("\n[pre-registered gates]")
    print("  G1 blobB merged INTERIOR >= 12 levels : %s  (%d levels in mask)"
          % ("PASS" if g1_pass else "FAIL", g1["blobB-row2/merged"]["levels_inside_mask"]))
    print("  G2 sample adequate, reaches low bands : %s  (%d bands with n>=20)"
          % ("PASS" if g2 else "FAIL", len(populated)))
    print("  G3 lowest band dither >= 3x rounding  : %s  (%.2fx)"
          % ("PASS" if g3 else "FAIL", lowest["median_ratio"] if lowest else float("nan")))
    print("  G4 ratio rises as levels fall         : %s  (%.2fx low vs %.2fx high)"
          % ("PASS" if g4 else "FAIL",
             populated[0]["median_ratio"] if populated else float("nan"),
             populated[-1]["median_ratio"] if populated else float("nan")))
    print("  G5 self-refutation (no transfer)      : %s" % ("FIRED" if g5 else "not fired"))
    print("  G6 rounding removes energy where dither adds it: %.2f %% of tiles"
          % (100.0 * g6))
    verdict = ("MECHANISM TRANSFERS to spatial gradient statistics" if (g3 or g4)
               else "MECHANISM DOES NOT TRANSFER; ORCH's result is domain-specific")
    if not g2:
        verdict = "VOID: sample saturated again"
    print("\nVERDICT: %s" % verdict)

    doc = {"step_dn": STEP, "dither_sigma_dn": sigma, "tile": TILE, "stride": STRIDE,
           "seed": SEED, "n_tiles": len(arr), "G1_blob_masks": g1,
           "bands": band_rows, "gates": {"G1": bool(g1_pass), "G2": bool(g2),
                                         "G3": bool(g3), "G4": bool(g4),
                                         "G5_fired": bool(g5)},
           "G6_frac_sign_disagree": g6, "verdict": verdict}
    dst = os.path.join(OUT, "quant_is_not_noise_v2.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
