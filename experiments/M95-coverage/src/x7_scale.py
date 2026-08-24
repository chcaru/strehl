"""B1 + B3 + controls K1-K5: is the gather's cost set by the SCALE MAGNITUDE or
by the PHASE it sweeps?

Runs on strehl's own unresampled decode (`single-noalign.tif`, B0 from arm 4),
so the source has been through no interpolation at all.

Bars are pre-registered in ../PRE-REGISTRATION.md. Controls K1-K5 gate the arms:
if any fails, no arm number is reported.
"""
import json
import sys
from pathlib import Path

import numpy as np

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "x7_scale.json"

LADDER = [1.0, 0.9999, 0.9995, 0.999, 0.997, 0.99, 0.97, 0.9315, 0.85, 0.70]


def main():
    if not B0.exists():
        sys.exit(f"missing {B0} (arm 4 render)")
    print(f"source: {B0.name}  (strehl decode, STREHL_ALIGN=0, no resample)")
    img = M.load_luma(B0)
    print(f"        {img.shape[1]}x{img.shape[0]} luma")

    tiles = M.pick_tiles(img)
    print(f"tiles : {len(tiles)} sharpest {M.TILE}px, >= {M.PAD}px from any border\n")

    regions = [img[y + M.TILE // 2 - M.PAD // 2 : y + M.TILE // 2 + M.PAD // 2,
                   x + M.TILE // 2 - M.PAD // 2 : x + M.TILE // 2 + M.PAD // 2]
               for y, x in tiles]

    base = [M.centre_crop(r) for r in regions]
    L_base, e_base = M.mean_sd([M.band_ratio(t, 1.0) for t in base])
    print(f"BASE  unresampled                     level {L_base:+.4f} +- {e_base:.4f}\n")

    def cost(arm_tiles, k):
        L, e = M.mean_sd([M.band_ratio(t, k) for t in arm_tiles])
        return L_base - L, L, e

    res = {"base_level": L_base, "base_sem": e_base, "n_tiles": len(tiles)}

    # ------------------------------------------------------------ controls
    print("--- CONTROLS (all must pass or no arm is reported) ---")
    ok = {}

    c, _, _ = cost([M.gather(r, 1.0, 0.0, 0.0) for r in regions], 1.0)
    ok["K1"] = abs(c) < 0.005
    print(f"K1 NULL          step 1.0, offset 0        {c:+.6f} dex   "
          f"{'PASS' if ok['K1'] else 'FAIL'}  (bar |c| < 0.005)")
    res["K1_null"] = c

    ladder_off = []
    for off in (0.0, 0.125, 0.25, 0.5):
        cc, _, _ = cost([M.gather(r, 1.0, off, off) for r in regions], 1.0)
        ladder_off.append(cc)
    ok["K2"] = all(ladder_off[i] < ladder_off[i + 1] - 1e-9 for i in range(3))
    print("K2 DOSE          offset 0/.125/.25/.5      " +
          " ".join(f"{d:+.4f}" for d in ladder_off) +
          f"   {'PASS' if ok['K2'] else 'FAIL'}  (bar: strictly monotone)")
    res["K2_offset_ladder"] = ladder_off

    c3, _, _ = cost([M.fourier_blur(t, 0.30) for t in base], 1.0)
    ok["K3"] = c3 >= 0.15
    print(f"K3 POSITIVE      planted Gaussian s=0.30  {c3:+.4f} dex   "
          f"{'PASS' if ok['K3'] else 'FAIL'}  (bar >= 0.15)")
    res["K3_planted_sigma0p30"] = c3

    c4, _, _ = cost([M.gather(r, 1.0, 1.0, 1.0) for r in regions], 1.0)
    ok["K4"] = abs(c4) < 0.005
    print(f"K4 INTEGER SHIFT step 1.0, offset 1.0 px  {c4:+.6f} dex   "
          f"{'PASS' if ok['K4'] else 'FAIL'}  (bar |c| < 0.005)")
    res["K4_integer_shift"] = c4

    c5, _, _ = cost([M.gather(r, 0.9315, 0.0, 0.0, kernel="lanczos8")
                     for r in regions], 0.9315)
    ok["K5"] = abs(c5) < 0.05
    print(f"K5 BAND-MATCH    lanczos8 at k=0.9315     {c5:+.4f} dex   "
          f"{'PASS' if ok['K5'] else 'FAIL'}  (bar |c| < 0.05)")
    res["K5_bandmatch_lanczos8"] = c5

    res["controls"] = ok
    if not all(ok.values()):
        print("\nCONTROLS FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    # -------------------------------------------------------------- B1
    print("\n--- B1: the discriminating ladder (pure scale, no translation) ---")
    print(f"{'k':>8} {'enlargement':>12} {'phase cyc/tile':>15} {'cost (dex)':>12}")
    lad = {}
    for k in LADDER:
        c, _, _ = cost([M.gather(r, k, 0.0, 0.0) for r in regions], k)
        cyc = M.TILE * abs(1.0 - k)
        lad[k] = c
        print(f"{k:>8.4f} {100 * (1 / k - 1):>11.2f}% {cyc:>15.2f} {c:>+12.4f}")
    res["B1_ladder"] = {str(k): v for k, v in lad.items()}

    sweeping = [k for k in LADDER if M.TILE * abs(1.0 - k) >= 1.0]
    vals = [lad[k] for k in sweeping]
    spread = max(vals) - min(vals)
    print(f"\n  k values sweeping >= 1 full phase cycle per tile: "
          f"{', '.join(f'{k:g}' for k in sweeping)}")
    print(f"  cost spread across them: {spread:.4f} dex "
          f"(min {min(vals):+.4f}, max {max(vals):+.4f})")
    print(f"  enlargement range across them: "
          f"{100 * (1 / max(sweeping) - 1):.2f}% to {100 * (1 / min(sweeping) - 1):.2f}%")
    res["B1_spread_dex"] = spread
    res["B1_sweeping_k"] = sweeping

    third = lad[0.9315] / 3.0
    b1_magnitude = lad[0.997] < third
    b1_phase = spread < 0.04
    print(f"\n  pre-registered: MAGNITUDE model if cost(0.997) < {third:.4f}; "
          f"actual cost(0.997) = {lad[0.997]:+.4f}  -> "
          f"{'MAGNITUDE' if b1_magnitude else 'not magnitude'}")
    print(f"  pre-registered: PHASE model if spread < 0.04; "
          f"actual spread = {spread:.4f}  -> "
          f"{'PHASE' if b1_phase else 'not phase'}")
    res["B1_verdict_magnitude"] = bool(b1_magnitude)
    res["B1_verdict_phase"] = bool(b1_phase)

    # phase-average of the offset curve, for comparison with the flat ladder
    off_costs = []
    for off in np.arange(0.0, 1.0, 0.0625):
        cc, _, _ = cost([M.gather(r, 1.0, off, off) for r in regions], 1.0)
        off_costs.append(cc)
    pavg = float(np.mean(off_costs))
    print(f"\n  phase-average of the pure-offset cost over 16 phases in [0,1): "
          f"{pavg:+.4f} dex")
    print(f"  flat scale-ladder plateau (mean over sweeping k):     "
          f"{np.mean(vals):+.4f} dex")
    res["phase_average_offset_cost"] = pavg
    res["B1_plateau_mean"] = float(np.mean(vals))

    # -------------------------------------------------------------- B3
    print("\n--- B3: how much of the orchestrator's +0.2392 is a units artifact ---")
    arm = [M.gather(r, 0.9315, 0.0, 0.0) for r in regions]
    L_fix, _ = M.mean_sd([M.band_ratio_fixed(t) for t in arm])
    L_mat, _ = M.mean_sd([M.band_ratio(t, 0.9315) for t in arm])
    c_fixed, c_matched = L_base - L_fix, L_base - L_mat
    print(f"  same k=0.9315 catmull-rom arm, fixed 0.30-0.48 band : {c_fixed:+.4f} dex")
    print(f"  same arm, band-matched to 0.2794-0.4471             : {c_matched:+.4f} dex")
    print(f"  the fixed band overstates the cost by                {c_fixed - c_matched:+.4f} dex")
    print(f"  (an arm magnified by 1/0.9315 is empty above "
          f"{0.5 * 0.9315:.4f} cyc/px by construction, so 0.4657-0.48 of")
    print(f"   the fixed band compares real content against a hole)")
    res["B3_fixed_band_cost"] = c_fixed
    res["B3_matched_band_cost"] = c_matched
    res["B3_bias_dex"] = c_fixed - c_matched

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
