"""Test the orchestrator's radial hypothesis for the M93/M95 ROI drift spread.

The orchestrator observed that four ROIs of the *same* bee-3-cpl stack show
brightness drifts of 1.0523x, 1.0776x, 1.1865x and 1.4585x, and offered as a
hypothesis that this is consistent with 1/m^2 focus breathing, under which drift
should grow with radius from the zoom centre. It explicitly asked that the ROI
coordinates be determined before interpreting.

They are in M95's `s2_rois.json` (M93 was renumbered to M95 in 45ba18b).

Two things make this testable without assuming where the optical axis sits:

  * `drift_per_step_px` is M95's own *measured* per-ROI alignment drift. Under a
    pure scale about any centre, displacement is proportional to radius from
    that centre. So `drift_per_step_px` is a direct empirical radius proxy and
    needs no assumption about the centre's location.
  * `score` is M95's detail measure. It separates the one low-detail ROI, which
    is the only one plausibly measuring background, from the three high-detail
    ROIs, where "brightness drift" is contaminated by subject structure sweeping
    through focus.

Plane order in `m93_crops.npy` is the insertion order of `chosen`, which
`s6_spectral.py:132` relies on via `list(rois).index("ROI-FLAT")`.
"""

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ROIS = os.path.join(ROOT, "experiments", "M95-merge-vs-frame", "out", "s2_rois.json")

# MEASURED by the orchestrator, experiments/ORCH-drift-check/decide.py, in the
# plane order of m93_crops.npy.
ORCH_DRIFT = [1.0776, 1.1865, 1.4585, 1.0523]
ORCH_REELECT_PCT = [1.40, 6.87, 5.77, 3.18]
ORCH_MARGIN_LT = [85.74, 87.82, 88.23, 92.97]


def main():
    with open(ROIS, "r", encoding="utf-8") as fh:
        rois = json.load(fh)
    chosen = rois["chosen"]
    h, w = rois["plane_shape"]
    ccx, ccy = w / 2.0, h / 2.0
    names = list(chosen)

    print(f"plane shape {w}x{h}, geometric centre ({ccx:.0f}, {ccy:.0f})")
    print(f"plane order in m93_crops.npy: {names}")
    print()
    hdr = ("plane", "ROI", "cx", "cy", "r_geom", "drift/step", "detail", "bright drift")
    print("{:>5} {:<14} {:>6} {:>6} {:>8} {:>11} {:>8} {:>13}".format(*hdr))
    rows = []
    for k, nm in enumerate(names):
        r = chosen[nm]
        rg = math.hypot(r["cx"] - ccx, r["cy"] - ccy)
        rows.append((k, nm, r["cx"], r["cy"], rg, r["drift_per_step_px"],
                     r["score"], ORCH_DRIFT[k]))
        print("{:>5} {:<14} {:>6.0f} {:>6.0f} {:>8.1f} {:>11.4f} {:>8.0f} {:>13.4f}".format(
            k, nm, r["cx"], r["cy"], rg, r["drift_per_step_px"], r["score"],
            ORCH_DRIFT[k]))

    print()
    print("--- test 1: equal radius must imply equal drift ---")
    # Use the measured drift-per-step as the radius proxy: under a pure scale
    # about ANY centre, displacement is proportional to radius from it.
    worst = None
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            dr = abs(a[5] - b[5]) / max(a[5], b[5])
            db = abs(a[7] - b[7]) / min(a[7], b[7])
            if dr < 0.05:
                print(f"  {a[1]:<14} vs {b[1]:<14}: radius proxy {dr*100:5.2f}% apart, "
                      f"brightness drift {db*100:6.2f}% apart")
                if worst is None or db > worst[0]:
                    worst = (db, a[1], b[1], dr)
    if worst is not None:
        print(f"  -> worst pair {worst[1]} / {worst[2]}: {worst[3]*100:.2f}% in radius, "
              f"{worst[0]*100:.2f}% in brightness")

    print()
    print("--- test 2: drift must be monotone in radius ---")
    by_r = sorted(rows, key=lambda r: r[5])
    print("  ordered by measured drift/step (radius proxy):")
    for r in by_r:
        print(f"    {r[1]:<14} drift/step {r[5]:.4f}  ->  brightness {r[7]:.4f}")
    mono = all(by_r[i][7] <= by_r[i + 1][7] for i in range(len(by_r) - 1))
    print(f"  monotone increasing? {mono}")
    largest_r = by_r[-1]
    smallest_b = min(rows, key=lambda r: r[7])
    print(f"  largest radius proxy is {largest_r[1]} ({largest_r[5]:.4f})")
    print(f"  smallest brightness drift is {smallest_b[1]} ({smallest_b[7]:.4f})")
    if largest_r[1] == smallest_b[1]:
        print("  -> the outermost ROI has the SMALLEST drift: anti-monotone, refuted")

    print()
    print("--- test 3: which ROI is actually background? ---")
    det = sorted(rows, key=lambda r: r[6])
    lo, hi = det[0], det[-1]
    print(f"  lowest detail : {lo[1]:<14} score {lo[6]:8.0f}  brightness drift {lo[7]:.4f}")
    print(f"  highest detail: {hi[1]:<14} score {hi[6]:8.0f}  brightness drift {hi[7]:.4f}")
    print(f"  detail ratio  : {hi[6] / lo[6]:.1f}x")
    print("  Only the low-detail ROI plausibly measures background rather than")
    print("  subject sweeping through focus. It has the smallest drift of the four.")

    print()
    print("--- the focus advantage, re-derived from M99's scene-coordinate levels ---")
    # MEASURED by M99: scene-fixed background level ratios, and the low-detail
    # region flux spans from the Phase D run. focus.rs asserts a per-frame gain
    # g moves the normalised response by sqrt(g).
    for label, r in [
        ("orchestrator's sensor-coordinate bee-3", 1.1091),
        ("M99 scene-fixed bee-3-cpl", 1.1818),
        ("M99 low-detail flux span bee-3-cpl", 1.1848),
        ("M99 low-detail flux span bee-2-cpl", 1.1815),
        ("M99 low-detail flux span lavendar-cpl", 1.3617),
    ]:
        print(f"  {label:<40} R = {r:.4f}  ->  sqrt(R) - 1 = {100*(math.sqrt(r)-1):5.2f}%")


if __name__ == "__main__":
    main()
