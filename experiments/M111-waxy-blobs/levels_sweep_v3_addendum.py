"""Addendum to levels_sweep_v3: is the family ordering an artefact of my units,
and does the bias statistic mask per-window scatter?

v3 returned N_L = 12 and N_A = 4, i.e. location broke at MORE levels than
dispersion, reversing ORCH's ordering. Before reporting that I have to test my
own gate, because R4 compares 0.2 px against 20% -- two thresholds in two
incommensurable units. The ordering is only a finding if it survives the
choice. Three tests, all pre-registered before the numbers exist.

T1 THRESHOLD SENSITIVITY. Sweep the location tolerance over 0.05..0.50 px and
   the dispersion tolerance over 5..40%, and report the FRACTION of the
   threshold grid on which the ordering reverses. If reversal holds on most of
   the grid it is a property of the data; if it holds only near my chosen pair
   it is a property of my gate and I withdraw it.

T2 UNIT-FREE COMPARISON. Express both families as a percentage of the quantity
   each is measuring: location error over the planted displacement magnitude
   (0.4356 px), dispersion error over the full-depth gradient energy. This
   removes the threshold entirely. PREDICTION if the reversal is real:
   normalised location error exceeds normalised dispersion error at EVERY
   level, not merely at the crossing.

T3 BIAS MASKS SCATTER -- the consequential one. My own levels_sweep v1 reported
   a median SIGNED difference and I cited it as support for immunity; signed
   medians cancel symmetric scatter. ORCH reports M113's location immunity as a
   BIAS (+2.1% at a step of 8192 DN). If bias and per-window absolute deviation
   diverge sharply on this data, then a bias-validated immunity claim does not
   license per-window use, and that qualification transfers to any milestone
   measuring a displacement window by window. PREDICTION if the masking is
   real: median|dev| exceeds |median signed| by a growing factor as N falls.

T4 THE TRANSFER. The project's own lateral-CA displacement is 0.155 px (M107,
   re-measured by M113). Report the largest N at which per-window location
   scatter already exceeds that signal. If scatter exceeds 0.155 px at a level
   count the fleet would consider safe, "location statistics are largely
   immune" is actively misleading for the project's actual location
   measurement, whatever it is true of in general.

Writes: C:\\dev\\strehl-out\\M111-pil-audit\\levels_sweep_v3_addendum.json
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M111-pil-audit"
MERGED = os.path.join(r"C:\dev\strehl-out\ORCH-thennow", "marker-HEAD-8f46f04.tif")
TILE, STRIDE = 256, 384
LEVELS = [256, 128, 64, 48, 32, 24, 16, 12, 8, 6, 4, 3, 2]
PLANT_DY, PLANT_DX = 0.37, -0.23
PLANT_MAG = float(np.hypot(PLANT_DY, PLANT_DX))
CA_SIGNAL_PX = 0.155

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from levels_sweep_v3 import fshift, gradmag, luma, narrow, offset  # noqa: E402


def main():
    os.makedirs(OUT, exist_ok=True)
    mt = tifffile.imread(MERGED)
    assert mt.dtype == np.uint16, mt.dtype
    tiles = []
    for y0 in range(200, mt.shape[0] - TILE - 200, STRIDE):
        for x0 in range(200, mt.shape[1] - TILE - 200, STRIDE):
            y = luma(mt[y0:y0 + TILE, x0:x0 + TILE])
            if y.std() < 5.0:
                continue
            tiles.append(y)
    base = []
    for y in tiles:
        s = fshift(y, PLANT_DY, PLANT_DX)
        dy, dx, _ = offset(s, y)
        base.append({"A": float(gradmag(y).mean()), "dy": dy, "dx": dx, "s": s, "y": y})
    print("tiles %d   plant magnitude %.4f px   CA signal %.3f px"
          % (len(tiles), PLANT_MAG, CA_SIGNAL_PX))

    rows = []
    print("\n%5s %8s %9s %10s %11s %10s %9s"
          % ("N", "A abs%", "L|dev|px", "L signed", "L norm%", "mask x", "frac>CA"))
    print("-" * 72)
    for n in LEVELS:
        A, dev, signed = [], [], []
        for b in base:
            qy, qs = narrow(b["y"], n), narrow(b["s"], n)
            A.append(abs(100.0 * (float(gradmag(qy).mean()) - b["A"]) / max(b["A"], 1e-9)))
            dy, dx, _ = offset(qs, qy)
            dev.append(float(np.hypot(dy - b["dy"], dx - b["dx"])))
            signed.append(dy - b["dy"])
        a = float(np.median(A))
        d = float(np.median(dev))
        sg = float(np.median(signed))
        r = {"N": n, "A_pct": a, "L_abs_px": d, "L_signed_px": sg,
             "L_norm_pct": 100.0 * d / PLANT_MAG,
             "mask_factor": d / max(abs(sg), 1e-9),
             "frac_windows_over_CA": float(np.mean(np.asarray(dev) > CA_SIGNAL_PX)),
             "n": len(dev)}
        rows.append(r)
        print("%5d %8.2f %9.4f %10.4f %11.2f %10.1f %9.3f"
              % (n, a, d, sg, r["L_norm_pct"], r["mask_factor"],
                 r["frac_windows_over_CA"]))

    # T1 threshold sensitivity
    rev = tot = 0
    for lt in np.arange(0.05, 0.501, 0.025):
        for at in np.arange(5.0, 40.1, 2.5):
            nl = next((r["N"] for r in rows if r["L_abs_px"] > lt), None)
            na = next((r["N"] for r in rows if r["A_pct"] > at), None)
            if nl is None or na is None:
                continue
            tot += 1
            if nl > na:
                rev += 1
    frac_rev = rev / max(tot, 1)

    # T2 unit-free
    worse = [r for r in rows if r["L_norm_pct"] > r["A_pct"]]
    t2 = len(worse) == len(rows)

    # T3 masking
    t3 = rows[-1]["mask_factor"] > rows[0]["mask_factor"]
    mask_max = max(r["mask_factor"] for r in rows)

    # T4 transfer
    n_ca = next((r["N"] for r in rows if r["L_abs_px"] > CA_SIGNAL_PX), None)

    print("\n[pre-registered gates]")
    print("  T1 reversal holds across threshold grid : %s  (%.1f%% of %d pairs)"
          % ("PASS" if frac_rev > 0.5 else "FAIL", 100.0 * frac_rev, tot))
    print("  T2 location worse at EVERY level        : %s  (%d of %d levels)"
          % ("PASS" if t2 else "FAIL", len(worse), len(rows)))
    print("  T3 bias masks scatter, growing          : %s  (max factor %.1fx)"
          % ("PASS" if t3 else "FAIL", mask_max))
    print("  T4 scatter exceeds the 0.155 px CA signal at N = %s" % n_ca)
    doc = {"plant_mag_px": PLANT_MAG, "ca_signal_px": CA_SIGNAL_PX, "rows": rows,
           "T1_frac_reversed": frac_rev, "T1_pairs": tot, "T2_all_levels": bool(t2),
           "T3_mask_growing": bool(t3), "T3_max_mask_factor": mask_max,
           "T4_N_at_CA_signal": n_ca}
    dst = os.path.join(OUT, "levels_sweep_v3_addendum.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
