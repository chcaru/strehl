"""M87 addendum 4 / R2-ladder -- ISO as a function of planted drift.

R2 (step 37) measured that 30 px p-p of drift on a single-depth, no-occlusion
plant produces ISO = 0.0645, which is 95% of the real bee-3 leg halo. R1
(step 35/36) measured that correcting registration on the real stack removes
only ~7%. Those two results are in tension and this ladder is the instrument
that resolves the tension rather than picking a side.

It measures the SHAPE of ISO(drift). That shape decides the question:

  - If ISO(drift) rises steeply from 0 and is roughly linear, then cutting the
    real 63 px p-p in-ROI drift down to M86's 11.56 px held-out residual should
    have removed most of the halo. It removed 7%. Something is then wrong with
    either the aligner's in-ROI performance or the drift hypothesis.

  - If ISO(drift) SATURATES -- flat above some small drift -- then 63 px and
    11.56 px sit on the same plateau, a 7% drop is exactly what the drift
    hypothesis predicts, and R1's null does NOT discriminate. That would make
    R1 uninformative on its own and would be a self-correction to my step-35
    reading.

I do not know which it is. Both are recorded here before the run.

The plant is step 37's: single depth, painted step edge, no occluder, no second
layer, integer shifts only.
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
import m87metric2 as M2                                   # noqa: E402
from importlib import import_module                       # noqa: E402

plant = import_module("37-plant-drift")
DATA = HERE / "data"

PP = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 30, 45, 60, 90]


def main():
    rows = []
    for pp in PP:
        frames, truth, ref, dx, _ = plant.build(pp / 2.0)
        sel, _ = plant.merge_argmax(frames)
        r = plant.score(sel, ref, f"drift {pp:3d} px p-p")
        rows.append({"pp": pp, "n_positions": int(len(np.unique(dx))),
                     "ISO": None if r is None else r["ISO"],
                     "ISO_ci": None if r is None else r["ISO_ci"],
                     "d_star": None if r is None else r["d_star"]})

    v = [x["ISO"] for x in rows]
    v0, vmax = v[0], max(v)
    print("\n  pp   ISO       fraction of the 90 px value   d*")
    for row, val in zip(rows, v):
        print(f"  {row['pp']:3d}  {val:.5f}   {val / v[-1]:6.3f}"
              f"                   {row['d_star']:.0f}")

    half = next((r["pp"] for r, val in zip(rows, v)
                 if val >= 0.5 * (v0 + vmax)), None)
    print(f"\n  ISO(0) = {v0:.5f}   ISO(90) = {v[-1]:.5f}")
    print(f"  drift reaching half the full response: {half} px p-p")

    i63 = min(range(len(PP)), key=lambda i: abs(PP[i] - 63))
    i12 = min(range(len(PP)), key=lambda i: abs(PP[i] - 12))
    ratio = v[i12] / v[i63]
    print(f"\n  ISO at ~63 px p-p (real unaligned in-ROI drift) = {v[i63]:.5f}")
    print(f"  ISO at ~12 px p-p (M86 E* = 11.56 px residual)   = {v[i12]:.5f}")
    print(f"  predicted retention if the halo were pure drift  = {ratio:.3f} "
          f"({100 * (1 - ratio):+.0f}% removal)")
    print(f"  R1 MEASURED removal on the real stack            = 6.6%")
    verdict = ("SATURATES -- R1's null does not discriminate"
               if ratio > 0.85 else
               "STEEP -- drift predicts a large removal that R1 did not see")
    print(f"  ladder shape: {verdict}")

    out = {"rows": rows, "half_response_pp": half,
           "ISO_63": v[i63], "ISO_12": v[i12],
           "predicted_retention": ratio,
           "predicted_removal_pct": 100 * (1 - ratio),
           "R1_measured_removal_pct": 6.6, "verdict": verdict}
    (DATA / "38-drift-ladder.json").write_text(json.dumps(out, indent=2),
                                               encoding="utf-8")
    print("wrote data/38-drift-ladder.json")


if __name__ == "__main__":
    main()
