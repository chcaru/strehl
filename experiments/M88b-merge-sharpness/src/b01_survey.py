"""M88b b01 — pre-select ROIs on GEOMETRY ALONE.

This runs BEFORE the treatment arm exists and its output is committed with the
pre-registration, so the ROI choice cannot be steered by an aligned result.

THE SELECTION RULE USES NO SHARPNESS QUANTITY.  Rise, MTF, cutoff and every
spectral statistic are deliberately absent from the scoring.  A window is
judged only on:

  * slant angle      -- must be slanted enough to supersample, not so much
                        that the edge runs out of the window
  * contrast         -- a step, in DN
  * straightness     -- residual sd of the fitted line, in pixels
  * wing flatness    -- the two sides must be flat, so the feature is a STEP
                        and not a ridge or a filament.  M88 measured a
                        +5.39 DN/um wing ramp on its own subject and had to
                        deramp it; a flat-winged edge avoids that entirely.

This mirrors M88's s05_find_edges.py, which was described in its report as
"geometric ROI selection, no frequency quantity".

Writes out/b01_survey.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88blib as B  # noqa: E402
import m88lib as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "out"

PREFIX = {"bee-3-cpl": "B3", "bee-2-cpl": "B2", "109MSDCF": "M9",
          "ruler": "RU", "tweezers": "TW", "wtext1": "WT"}

WIN = 96            # merge px; ~983 um across, comfortably > 2 * half-width
STRIDE = 64

# Pre-declared geometric admission thresholds.
ANGLE_LO, ANGLE_HI = 1.2, 9.0      # degrees off axis
MIN_CONTRAST = 400.0               # DN across the step
MAX_RESID_PX = 0.60                # straightness of the fitted line
MAX_WING_SLOPE = 0.35              # wing rise across the half-width, per unit step
SATURATION_DN = 64000.0            # 16-bit clip guard; tweezers reaches 65535


def wing_slopes(plane, roi, axis, line, core_um=24.0):
    """Slope of each wing outside the transition core, in DN/um.

    MUST be computed on the RAW ESF.  An earlier version of this function read
    the ESF returned by sfr_from_sites2, which applies deramp_esf and therefore
    flattens the wings BY CONSTRUCTION -- it reported exactly 0.000 for every
    window and the filter did nothing.  esf_from_sites does no deramping, so
    this sees the real wing.
    """
    r0, c0, h, w = roi
    sub, xs, ys = B.merge_sites(plane, r0, c0, h, w)
    xx, yy = np.meshgrid(xs, ys)
    c, e, cnt = L.esf_from_sites(sub.ravel(), xx.ravel(), yy.ravel(), line,
                                 B.BIN_UM, B.HALF_WIDTH_UM)
    out = []
    for m in (c < -core_um, c > core_um):
        cc, ee = c[m], e[m]
        good = np.isfinite(ee)
        if good.sum() < 8:
            out.append(np.nan)
            continue
        out.append(float(np.polyfit(cc[good], ee[good], 1)[0]))
    return out


def scan(plane, label):
    h, w = plane.shape
    cands = []
    for r0 in range(WIN, h - 2 * WIN, STRIDE):
        for c0 in range(WIN, w - 2 * WIN, STRIDE):
            patch = plane[r0:r0 + WIN, c0:c0 + WIN]
            if not np.isfinite(patch).all():
                continue
            # Saturation: a clipped highlight flattens the top of the ESF and
            # biases the rise low.  tweezers reaches 65535 DN, so this is a
            # real exclusion in this corpus and not a hypothetical one.
            if patch.max() >= SATURATION_DN:
                continue
            rng = float(patch.max() - patch.min())
            if rng < MIN_CONTRAST:
                continue
            for axis in ("vertical", "horizontal"):
                try:
                    m = B.measure_roi(plane, (r0, c0, WIN, WIN), axis)
                except Exception:
                    continue
                # Every comparison below must be guarded: `nan < x` is False,
                # so a NaN contrast SILENTLY PASSES a `<` threshold.  That let
                # a NaN-contrast window through an earlier run of this survey.
                if not (np.isfinite(m["angle_deg"])
                        and np.isfinite(m["contrast"])
                        and np.isfinite(m["resid_sd_px"])
                        and np.isfinite(m["rise_um"])):
                    continue
                ang = abs(m["angle_deg"])
                if not (ANGLE_LO <= ang <= ANGLE_HI):
                    continue
                if m["contrast"] < MIN_CONTRAST:
                    continue
                if m["resid_sd_px"] > MAX_RESID_PX:
                    continue
                if m["n_empty_bins"] > 0:
                    continue
                ws = wing_slopes(plane, (r0, c0, WIN, WIN), axis, m["line"])
                if not np.all(np.isfinite(ws)):
                    continue
                # scale-free: wing rise across the half-width, per unit step
                wmax = max(abs(x) for x in ws) * B.HALF_WIDTH_UM / m["contrast"]
                if wmax > MAX_WING_SLOPE:
                    continue
                cands.append(dict(
                    stack=label, row=r0, col=c0, win=WIN, axis=axis,
                    angle_deg=m["angle_deg"], contrast=m["contrast"],
                    resid_sd_px=m["resid_sd_px"],
                    wing_rise_frac_of_step=wmax,
                    # recorded for the report, NOT used in selection
                    rise_um_NOT_USED_IN_SELECTION=m["rise_um"],
                ))
    return cands


def pick(cands, n=6, min_sep=160):
    """Rank by a geometry-only score and enforce spatial separation."""
    def score(c):
        return (c["contrast"] / 1000.0
                - 2.0 * c["resid_sd_px"]
                - 1.5 * c["wing_rise_frac_of_step"])
    ranked = sorted(cands, key=score, reverse=True)
    chosen = []
    for c in ranked:
        if all(max(abs(c["row"] - k["row"]), abs(c["col"] - k["col"])) >= min_sep
               for k in chosen):
            chosen.append(c)
        if len(chosen) >= n:
            break
    return chosen


def main():
    report = {"win": WIN, "stride": STRIDE,
              "thresholds": dict(angle=[ANGLE_LO, ANGLE_HI],
                                 min_contrast=MIN_CONTRAST,
                                 max_resid_px=MAX_RESID_PX,
                                 max_wing_slope=MAX_WING_SLOPE),
              "stacks": {}}
    for tif, label in ((DATA / "bee3_gate4.tiff", "bee-3-cpl"),
                       (DATA / "bee_2_cpl_gate4.tiff", "bee-2-cpl"),
                       (DATA / "109_gate4.tiff", "109MSDCF"),
                       (DATA / "highly_angled_ruler_mm_cpl_gate4.tiff", "ruler"),
                       (DATA / "tweezers_cpl_gate4.tiff", "tweezers"),
                       (DATA / "wrapped_text_1_gate4.tiff", "wtext1")):
        if not tif.exists():
            print(f"  {label}: MISSING {tif.name}, skipped")
            continue
        plane = B.read_merge_plane(tif, "G")
        print(f"\n{label}: plane {plane.shape}, "
              f"range {plane.min():.0f}-{plane.max():.0f} DN")
        cands = scan(plane, label)
        print(f"  {len(cands)} windows pass every geometric threshold")
        chosen = pick(cands)
        print(f"  {'name':>5} {'row':>5} {'col':>5} {'axis':>10} "
              f"{'angle':>7} {'contrast':>9} {'resid':>6} {'wing':>6}")
        for i, c in enumerate(chosen):
            c["name"] = f"{PREFIX[label]}{i + 1}"
            print(f"  {c['name']:>5} {c['row']:5d} {c['col']:5d} "
                  f"{c['axis']:>10} {c['angle_deg']:7.3f} "
                  f"{c['contrast']:9.0f} {c['resid_sd_px']:6.3f} "
                  f"{c['wing_rise_frac_of_step']:6.3f}")
        report["stacks"][label] = dict(n_candidates=len(cands), chosen=chosen)
    OUT.mkdir(exist_ok=True)
    (OUT / "b01_survey.json").write_text(json.dumps(report, indent=1),
                                         encoding="utf-8")
    print("\nwrote out/b01_survey.json")


if __name__ == "__main__":
    main()
