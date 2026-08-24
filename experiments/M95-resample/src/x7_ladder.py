"""M95 arm 11 - B27 (clean-step ringing) and B28 (flat-region control) for the
four-point kernel ladder.

Bars registered in experiments/M95-kernel/PRE-REGISTRATION.md ADDENDUM 3, commit
42a0c7c, BEFORE lanczos2 was added to any measurement script.

B27  1000 DN ideal step, half-pixel phase, overshoot as % of step height.
     Catmull-Rom is analytically 1/16 = 6.2500%. If this harness does not
     reproduce that, the harness is broken and every other cell is void, so it
     is a hard error rather than a printed warning.

B28  The same kernels on FEATURELESS tiles. A sharper kernel raises high-band
     energy on flat ground too, and that is amplified read and shot noise, not
     detail. Reported beside the detail-region number for every kernel.
     Carries its own power control: a planted blur must move the flat-region
     statistic, or a null there means only that the metric is asleep.
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

from x2_pairs import IMAGES, TILE, band_ratio, fourier_blur, load_luma
from x3_kernel import KERNELS, PAD, bspline_prefilter, resample, resample_bspline, shift1d, w_bspline

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

STEP_DN = 1000.0
NAMES = ["catmullrom", "mitchell", "lanczos2", "lanczos3", "bspline"]


def step_response(name, phase=0.5, n=256):
    """Resample an ideal step by `phase` px and return the profile near the edge."""
    a = np.zeros((n, 4), dtype=np.float64)
    a[n // 2 :, :] = STEP_DN
    if name == "bspline":
        c = bspline_prefilter(a, 0)
        r = shift1d(c, 0, phase, w_bspline, 2)
    else:
        wfun, radius = KERNELS[name]
        r = shift1d(a, 0, phase, wfun, radius)
    # Stay well away from the circular wrap at the array ends.
    return r[n // 2 - 32 : n // 2 + 32, 0]


def ring_stats(name):
    p = step_response(name)
    over = (p.max() - STEP_DN) / STEP_DN * 100.0
    under = (0.0 - p.min()) / STEP_DN * 100.0
    # Ring reach: how many samples past the edge deviate by more than 0.1% of
    # the step. Amplitude and extent are different complaints.
    dev = np.where(np.arange(p.size) >= 32, np.abs(p - STEP_DN), np.abs(p))
    reach = int((dev > 0.001 * STEP_DN).sum())
    return dict(overshoot_pct=float(over), undershoot_pct=float(under), reach_px=reach)


def pick_flat_tiles(img, n=40, tile=TILE):
    """pick_tiles inverted: the LEAST textured tiles, which is where a sharpness
    gain can only be noise."""
    h, w = img.shape
    m = 3 * tile
    scored = []
    for y in range(m, h - m - tile, tile):
        for x in range(m, w - m - tile, tile):
            t = img[y : y + tile, x : x + tile]
            scored.append((float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var()), y, x))
    scored.sort()
    taken = []
    for s, y, x in scored:
        if all(abs(y - ty) >= tile or abs(x - tx) >= tile for _, ty, tx in taken):
            taken.append((s, y, x))
        if len(taken) == n:
            break
    return [(y, x) for _, y, x in taken], float(np.mean([s for s, _, _ in taken]))


def main():
    j = {}

    print("=" * 74)
    print("B27 -- ringing on a clean 1000 DN step, half-pixel phase")
    print("=" * 74)
    rows = {n: ring_stats(n) for n in NAMES}

    cr = rows["catmullrom"]["overshoot_pct"]
    if abs(cr - 6.25) > 1e-6:
        sys.exit(
            f"HARNESS BROKEN: Catmull-Rom half-pixel overshoot is {cr:.6f}%, "
            f"analytically it must be 1/16 = 6.250000%. Every cell in this table is void."
        )
    print(f"  harness check: Catmull-Rom = {cr:.4f}% = 1/16 exactly  OK\n")
    print(f"  {'kernel':12s} {'overshoot %':>12s} {'undershoot %':>13s} {'reach px':>9s} {'vs C-R':>8s}")
    for n in NAMES:
        r = rows[n]
        print(
            f"  {n:12s} {r['overshoot_pct']:>12.4f} {r['undershoot_pct']:>13.4f} "
            f"{r['reach_px']:>9d} {r['overshoot_pct'] / cr:>7.2f}x"
        )
    j["b27_step"] = rows
    j["b27_harness_catmullrom_pct"] = cr

    print()
    print("=" * 74)
    print("B28 -- the flat-region control: is the gain detail or amplified noise?")
    print("=" * 74)
    b0 = load_luma(IMAGES["B0"]["path"])
    flat, flat_score = pick_flat_tiles(b0)
    from x2_pairs import pick_tiles

    sharp = pick_tiles(b0)
    sharp_score = float(
        np.mean(
            [
                np.diff(b0[y : y + TILE, x : x + TILE], axis=0).var()
                + np.diff(b0[y : y + TILE, x : x + TILE], axis=1).var()
                for y, x in sharp
            ]
        )
    )
    print(f"  detail tiles: mean gradient variance {sharp_score:12.2f}")
    print(f"  flat tiles  : mean gradient variance {flat_score:12.2f}")
    print(f"  separation  : {sharp_score / max(flat_score, 1e-9):.1f}x\n")

    phases = [(0.5, 0.0), (0.0, 0.5), (0.5, 0.5), (0.25, 0.25), (0.25, 0.75), (0.75, 0.25), (0.75, 0.75)]

    def ladder(tiles):
        base = float(np.mean([band_ratio(b0[y : y + TILE, x : x + TILE], 1.0) for y, x in tiles]))
        out = {}
        for name in NAMES:
            vals = []
            for dy, dx in phases:
                for y, x in tiles:
                    t = b0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]
                    r = resample_bspline(t, dy, dx) if name == "bspline" else resample(t, dy, dx, name)
                    vals.append(band_ratio(r[PAD:-PAD, PAD:-PAD], 1.0))
            out[name] = float(np.mean(vals) - base)
        return base, out

    d_base, d = ladder(sharp)
    f_base, f = ladder(flat)

    print(f"  {'kernel':12s} {'detail dex':>11s} {'flat dex':>10s} {'gain vs C-R (detail)':>21s} {'(flat)':>9s}")
    for n in NAMES:
        print(
            f"  {n:12s} {d[n]:>+11.4f} {f[n]:>+10.4f} "
            f"{d[n] - d['catmullrom']:>+21.4f} {f[n] - f['catmullrom']:>+9.4f}"
        )
    j["b28_detail"] = d
    j["b28_flat"] = f
    j["b28_detail_baseline"] = d_base
    j["b28_flat_baseline"] = f_base
    j["b28_grad_var_detail"] = sharp_score
    j["b28_grad_var_flat"] = flat_score

    print("\n  -- power control: can the flat-region statistic move at all? --")
    print("     A null on flat tiles is worth nothing unless a planted blur shows there.")
    resp = {}
    for sigma in [0.5, 1.0]:
        vals = []
        for y, x in flat:
            t = b0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]
            vals.append(band_ratio(fourier_blur(t, sigma)[PAD:-PAD, PAD:-PAD], 1.0))
        resp[f"sigma_{sigma}"] = float(np.mean(vals) - f_base)
        print(f"     planted sigma={sigma} px blur on the flat tiles: {resp[f'sigma_{sigma}']:+.4f} dex")
    j["b28_power_control"] = resp
    live = abs(resp["sigma_1.0"]) > 0.05
    print(f"     flat-region metric responds to a planted blur: {'PASS' if live else 'FAIL'}")
    j["b28_power_control_pass"] = bool(live)

    with open(os.path.join(OUT, "x7_ladder.json"), "w", encoding="utf-8") as fh:
        json.dump(j, fh, indent=1)
    print(f"\nwrote {os.path.join(OUT, 'x7_ladder.json')}")
    print("END OF X7 -- reaching this line is part of the contract")


if __name__ == "__main__":
    main()
