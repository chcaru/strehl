"""B1 + B3, corrected: the scale must be applied about the FIELD centre.

DEFECT IN x7_scale.py, found by its own ladder disagreeing with the end-to-end
measurement by 8x. x7 gathers each tile about that tile's own centre, so every
tile sits at zero base phase and only sweeps +-(TILE/2)*(1-k) cycles about it.
For k near 1 that keeps every sample close to integer phase, where Catmull-Rom
is nearly exact, and the arm reads far too low: k=0.997 read +0.0340 dex while
the shipped binary at k=0.9974 costs -0.2851 dex.

The real pipeline scales about the FIELD centre. An output tile starting at
integer output row o0 reads the source at fy + (o0 - fy)*k, whose fractional
part is arbitrary and varies from tile to tile. That base phase is the whole
cost. This script models it exactly: o0 is forced to an integer, as an output
pixel grid requires, and the resulting sub-pixel phase is whatever it is.

Bars unchanged from ../PRE-REGISTRATION.md.
"""
import json
import sys
from pathlib import Path

import numpy as np

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "x7b_scale_field.json"

LADDER = [1.0, 0.9999, 0.9995, 0.999, 0.997, 0.9974, 0.99, 0.97, 0.9315, 0.85, 0.70]


def field_arm(img, tiles, k, kernel="catmull-rom", extra_off=0.0):
    """Gather each tile as the pipeline would: scale k about the field centre.

    The output tile origin o0 is an integer output pixel, so the source position
    it reads, fy + (o0 - fy)*k, carries an arbitrary fractional phase.
    """
    h, w = img.shape
    fy, fx = (h - 1) / 2.0, (w - 1) / 2.0
    out, phases = [], []
    for ty, tx in tiles:
        o0y = round(fy + (ty - fy) / k)
        o0x = round(fx + (tx - fx) / k)
        sy = fy + (o0y - fy) * k + extra_off
        sx = fx + (o0x - fx) * k + extra_off
        phases.append((sy - np.floor(sy), sx - np.floor(sx)))
        cy_i = int(np.floor(sy + (M.TILE - 1) * k / 2.0))
        cx_i = int(np.floor(sx + (M.TILE - 1) * k / 2.0))
        y0, x0 = cy_i - M.PAD // 2, cx_i - M.PAD // 2
        if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
            continue
        reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
        i = np.arange(M.TILE, dtype=np.float64)
        vy = (sy - y0) + i * k
        vx = (sx - x0) + i * k
        t = M.gather_1d(reg, vy, 0, kernel)
        out.append(M.gather_1d(t, vx, 1, kernel))
    return out, phases


def base_for(img, tiles, k):
    """The unresampled tile covering the SAME scene span as `field_arm`'s tile.

    Comparing spectra requires the same scene. The arm reads source span
    [sy, sy + 256k); the base is the integer-aligned 256-px window centred on it,
    taken straight from the source with no interpolation at all.
    """
    h, w = img.shape
    fy, fx = (h - 1) / 2.0, (w - 1) / 2.0
    out = []
    for ty, tx in tiles:
        o0y = round(fy + (ty - fy) / k)
        o0x = round(fx + (tx - fx) / k)
        sy = fy + (o0y - fy) * k
        sx = fx + (o0x - fx) * k
        cy_i = int(np.floor(sy + (M.TILE - 1) * k / 2.0))
        cx_i = int(np.floor(sx + (M.TILE - 1) * k / 2.0))
        if (cy_i - M.PAD // 2 < 0 or cx_i - M.PAD // 2 < 0
                or cy_i + M.PAD // 2 > h or cx_i + M.PAD // 2 > w):
            continue
        out.append(img[cy_i - M.TILE // 2 : cy_i + M.TILE // 2,
                       cx_i - M.TILE // 2 : cx_i + M.TILE // 2])
    return out


def main():
    if not B0.exists():
        sys.exit(f"missing {B0}")
    print(f"source: {B0.name}  (strehl decode, STREHL_ALIGN=0, no resample)")
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    print(f"tiles : {len(tiles)} sharpest {M.TILE}px\n")
    res = {"n_tiles": len(tiles)}

    def cost_at(k, kernel="catmull-rom", extra_off=0.0):
        arm, ph = field_arm(img, tiles, k, kernel, extra_off)
        base = base_for(img, tiles, k)
        n = min(len(arm), len(base))
        Lb, _ = M.mean_sd([M.band_ratio(t, 1.0) for t in base[:n]])
        La, _ = M.mean_sd([M.band_ratio(t, k) for t in arm[:n]])
        return Lb - La, n, ph

    print("--- CONTROLS ---")
    ok = {}
    c1, n1, _ = cost_at(1.0)
    ok["K1"] = abs(c1) < 0.005
    print(f"K1 NULL          k=1.0 about field centre  {c1:+.6f} dex  "
          f"{'PASS' if ok['K1'] else 'FAIL'}   ({n1} tiles)")
    res["K1_null"] = c1

    c4, _, _ = cost_at(1.0, extra_off=1.0)
    ok["K4"] = abs(c4) < 0.005
    print(f"K4 INTEGER SHIFT k=1.0, +1.0 px           {c4:+.6f} dex  "
          f"{'PASS' if ok['K4'] else 'FAIL'}")
    res["K4_integer_shift"] = c4

    c5, _, _ = cost_at(0.9315, kernel="lanczos8")
    ok["K5"] = abs(c5) < 0.05
    print(f"K5 BAND-MATCH    lanczos8 at k=0.9315     {c5:+.4f} dex  "
          f"{'PASS' if ok['K5'] else 'FAIL'}")
    res["K5_bandmatch_lanczos8"] = c5

    base10 = base_for(img, tiles, 1.0)
    Lb, _ = M.mean_sd([M.band_ratio(t, 1.0) for t in base10])
    Lp, _ = M.mean_sd([M.band_ratio(M.fourier_blur(t, 0.30), 1.0) for t in base10])
    c3 = Lb - Lp
    ok["K3"] = c3 >= 0.15
    print(f"K3 POSITIVE      planted Gaussian s=0.30  {c3:+.4f} dex  "
          f"{'PASS' if ok['K3'] else 'FAIL'}")
    res["K3_planted_sigma0p30"] = c3

    res["controls"] = ok
    if not all(ok.values()):
        print("\nCONTROLS FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print("\n--- B1 (corrected): pure scale about the field centre ---")
    print(f"{'k':>8} {'enlargement':>12} {'mean phase':>11} {'cost (dex)':>12}")
    lad = {}
    for k in LADDER:
        c, n, ph = cost_at(k)
        d = np.array([max(min(a, 1 - a), min(b, 1 - b)) for a, b in ph])
        lad[k] = c
        print(f"{k:>8.4f} {100 * (1 / k - 1):>11.2f}% {d.mean():>11.3f} {c:>+12.4f}")
    res["B1_ladder"] = {str(k): v for k, v in lad.items()}

    sweep = [k for k in LADDER if k <= 0.999]
    vals = [lad[k] for k in sweep]
    spread = max(vals) - min(vals)
    print(f"\n  cost spread over k = {min(sweep):g}..{max(sweep):g} "
          f"({100 * (1 / min(sweep) - 1):.1f}% to {100 * (1 / max(sweep) - 1):.2f}% "
          f"enlargement): {spread:.4f} dex")
    print(f"  min {min(vals):+.4f}  max {max(vals):+.4f}")
    third = lad[0.9315] / 3.0
    print(f"\n  pre-registered MAGNITUDE reading: cost(0.997) < {third:.4f}? "
          f"actual {lad[0.997]:+.4f} -> "
          f"{'MAGNITUDE' if lad[0.997] < third else 'NOT magnitude'}")
    print(f"  pre-registered PHASE reading: spread < 0.04? "
          f"actual {spread:.4f} -> {'PHASE' if spread < 0.04 else 'NOT phase'}")
    res["B1_spread_dex"] = spread
    res["B1_verdict_magnitude"] = bool(lad[0.997] < third)
    res["B1_verdict_phase"] = bool(spread < 0.04)

    print("\n--- B3: fixed band vs band-matched, same k=0.9315 arm ---")
    arm, _ = field_arm(img, tiles, 0.9315)
    base = base_for(img, tiles, 0.9315)
    n = min(len(arm), len(base))
    Lb, _ = M.mean_sd([M.band_ratio(t, 1.0) for t in base[:n]])
    Lf, _ = M.mean_sd([M.band_ratio_fixed(t) for t in arm[:n]])
    Lm, _ = M.mean_sd([M.band_ratio(t, 0.9315) for t in arm[:n]])
    print(f"  fixed 0.30-0.48 band : {Lb - Lf:+.4f} dex")
    print(f"  band-matched         : {Lb - Lm:+.4f} dex")
    print(f"  bias from fixed band : {(Lb - Lf) - (Lb - Lm):+.4f} dex")
    res["B3_fixed_band_cost"] = Lb - Lf
    res["B3_matched_band_cost"] = Lb - Lm
    res["B3_bias_dex"] = (Lb - Lf) - (Lb - Lm)

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
