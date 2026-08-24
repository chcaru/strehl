"""M88 s13 — robustness and reference scales cited in the report.

Three things, all of which the report quotes and none of which existed as
committed code until now:

  1. The diffraction-limited reference rise distances, measured through this
     same instrument, so the real 10-90% rises of s12 have a scale to sit
     against.
  2. The diffraction-limited reference MTF(40 cy/mm) at f/5.6 and f/11, at the
     exploratory 64 um half-width, so the shortfall factor is a matched
     comparison rather than a cross-setting one. This is also what shows
     MTF(40) has no discriminating power at f/11.
  3. A best-focus plateau sweep on the sharpest real ROI, which shows the
     verdict does not depend on the frame-selection rule.

Writes out/s13_robustness.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m88lib as L
from s12_closing import rise_1090

GAIN_DN_PER_E = 0.75
READ_NOISE_E = 3.0
BIN_UM = 0.64
TAPER = 0.10
CORE_UM = 24.0
PLANT_ANGLE_DEG = 2.0
N_SEED = 5

# ROI A1 of 119MSDCF, exactly as frozen in s06_measure.py
A1_ROW0, A1_COL0, A1_NROW, A1_NCOL = 1280, 0, 160, 400
PLATEAU = range(3, 10)


def _measure_plant(fc, lo_dn, hi_dn, half_um, seed, noisy=True):
    """One synthetic diffraction-limited edge through the real instrument."""
    img = L.synth_edge_frame2(300, 1400, fc, PLANT_ANGLE_DEG, lo_dn, hi_dn, sub=8)
    if noisy:
        rng = np.random.default_rng(1000 + seed)
        img = L.add_sensor_noise(img, GAIN_DN_PER_E, READ_NOISE_E, rng)
    sub, xs, ys = L.green_sites(img, "G1")
    line = L.fit_edge_line(sub, xs, ys, axis="horizontal")
    xx, yy = np.meshgrid(xs, ys)
    return L.sfr_from_sites2(
        sub.ravel().astype(float), xx.ravel(), yy.ravel(),
        line, BIN_UM, half_um, TAPER, core_um=CORE_UM,
    )


def reference_rises():
    """Rise distance of a diffraction-limited edge, noise free, per cutoff."""
    out = []
    for fc in (43.9, 53.9, 86.3, 106.0):
        res = _measure_plant(fc, 1000.0, 3600.0, 96.0, 0, noisy=False)
        rise = rise_1090(res["centres_um"], res["esf"])
        out.append(dict(fc_cymm=fc, rise_um=float(rise)))
        print(f"  fc={fc:6.1f} cy/mm -> 10-90 rise {rise:6.2f} um")
    return out


def reference_mtf40():
    """MTF(40) of a diffraction-limited edge at each aperture's own cutoff.

    Contrast is matched to the real stack it stands in for, because the noise
    floor at 40 cy/mm is a meaningful part of the answer at f/11.
    """
    out = []
    for label, fc, lo, hi in (("f/5.6", 86.3, 1000.0, 3600.0),
                              ("f/11", 43.9, 1000.0, 2500.0)):
        vals = []
        for seed in range(N_SEED):
            res = _measure_plant(fc, lo, hi, 64.0, seed)
            i = int(np.argmin(np.abs(res["freq_cymm"] - 40.0)))
            vals.append(float(res["mtf"][i]))
        m, s = float(np.mean(vals)), float(np.std(vals))
        out.append(dict(aperture=label, fc_cymm=fc, contrast_dn=hi - lo,
                        mtf40_mean=m, mtf40_sd=s))
        print(f"  {label:5s} diffraction-limited fc={fc:5.1f} -> "
              f"MTF(40) = {m:.4f} +/- {s:.4f}")
    return out


def plateau_sweep():
    """Rise distance across the best-focus plateau of the sharpest real ROI."""
    files = sorted(Path("D:/personal/macro/119MSDCF").glob("*.ARW"))
    out = []
    for k in PLATEAU:
        active = L.load_active(files[k])
        sub, xs, ys = L.green_sites(active, "G1")
        win = sub[A1_ROW0:A1_ROW0 + A1_NROW, A1_COL0:A1_COL0 + A1_NCOL].astype(float)
        cx = xs[A1_COL0:A1_COL0 + A1_NCOL]
        cy = ys[A1_ROW0:A1_ROW0 + A1_NROW]
        line = L.fit_edge_line(win, cx, cy, axis="horizontal")
        xx, yy = np.meshgrid(cx, cy)
        res = L.sfr_from_sites2(win.ravel(), xx.ravel(), yy.ravel(),
                                line, BIN_UM, 96.0, TAPER, core_um=CORE_UM)
        rise = rise_1090(res["centres_um"], res["esf"])
        out.append(dict(frame=k, file=files[k].name, rise_um=float(rise),
                        angle_deg=float(line["angle_deg"])))
        print(f"  frame {k:2d}: rise {rise:6.2f} um   angle {line['angle_deg']:7.3f}")
        del active, sub
    return out


def main():
    print("=" * 78)
    print("1. REFERENCE RISE OF A DIFFRACTION-LIMITED EDGE (noise free)")
    print("=" * 78)
    rises = reference_rises()

    print()
    print("=" * 78)
    print("2. REFERENCE MTF(40 cy/mm), half-width 64 um, matched contrast")
    print("=" * 78)
    mtf40 = reference_mtf40()
    f56 = next(r for r in mtf40 if r["aperture"] == "f/5.6")
    f11 = next(r for r in mtf40 if r["aperture"] == "f/11")
    print()
    print(f"  measured f/5.6 median MTF(40) = 0.1232 -> shortfall "
          f"{f56['mtf40_mean'] / 0.1232:.2f}x")
    print(f"  measured f/11  median MTF(40) = 0.0481 vs a diffraction-limited "
          f"{f11['mtf40_mean']:.4f} +/- {f11['mtf40_sd']:.4f}")
    print("  -> at f/11 this statistic cannot discriminate; 40 cy/mm is 91% of "
          "the cutoff")

    print()
    print("=" * 78)
    print("3. BEST-FOCUS PLATEAU SWEEP, 119MSDCF ROI A1, G1")
    print("=" * 78)
    plateau = plateau_sweep()
    best = min(p["rise_um"] for p in plateau)
    worst = max(p["rise_um"] for p in plateau)
    ref = next(r["rise_um"] for r in rises if r["fc_cymm"] == 86.3)
    print()
    print(f"  plateau min {best:.2f} um, max {worst:.2f} um")
    print(f"  diffraction-limited fc=86.3 through this instrument: {ref:.2f} um")
    print(f"  the sharpest frame in the plateau is still {best / ref:.2f}x too wide")
    print("  -> the verdict does not depend on the frame-selection rule")

    report = dict(
        reference_rises=rises,
        reference_mtf40=mtf40,
        plateau=plateau,
        plateau_min_um=best,
        plateau_max_um=worst,
        reference_rise_86p3_um=ref,
        plateau_best_over_diffraction=best / ref,
    )
    out = Path(__file__).resolve().parents[1] / "out" / "s13_robustness.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\nwrote {out.relative_to(out.parents[1])}")


if __name__ == "__main__":
    main()
