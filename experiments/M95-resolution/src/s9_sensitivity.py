"""Does the headline depend on the unexplained V4 offset shortfall?

V4 recovers d = +0.40..+0.45 from the real frames where the RGGB quad predicts
+0.50. Two explanations were tested and BOTH were falsified: attenuation bias
(s7: recovers +0.50 exactly down to hf SNR 0.45) and aliasing (s8: recovers
+0.50 exactly with content out to 0.50 cyc/full-res px). It is unexplained.

Note it is the same sign and roughly the same size as arm 2's independent
shortfall: the R-B separation measured 0.6637 against a derived 0.7071, 6.1 %
short, on a different channel pair with a different instrument.

This file asks the only question that matters for the report: does the destroyed
fraction move if the geometry is 0.45 or 0.40 rather than 0.50? If it does not,
the headline is robust to the thing I could not explain.

FIRST ATTEMPT WAS A NO-OP AND IS RECORDED AS A FAILED CONTROL. It monkeypatched
the module global `S6.D_G1_TO_G2`, but s6 binds it as a *default argument*
(`def signal_power(g1, g2, d=D_G1_TO_G2)`), which is evaluated once at def time.
The patch therefore changed nothing and the run printed a change of exactly
0.00 percentage points -- a number that looks like a clean pass and is in fact
the instrument reporting that it was never perturbed. The exact zero is what
gave it away. `report` also hard-codes the same 0.5 a second time in its loss
weight, so both call sites are parameterised explicitly below.
"""

import json
import os
import sys

import numpy as np
import tifffile

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
REN = r"C:\dev\strehl-out\M95-resolution"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s6_signal as S6  # noqa: E402


def report_d(g1, g2, d):
    """s6.report, with the geometry threaded through BOTH places it is used:
    the de-ramp that estimates shared power, and the sin^2 binning-loss weight."""
    P, _N, (fu, fv) = S6.signal_power(g1, g2, d=(d, -d))
    t = np.pi * d * (fu - fv)
    lose_w, keep_w = np.sin(t) ** 2, np.cos(t) ** 2
    r = np.hypot(fu, fv)
    m = np.ones_like(P, dtype=bool)
    m[0, 0] = False
    Pc = np.clip(P, 0, None)
    sel = m & (r >= 0.25)
    tot = (Pc[sel] * (lose_w[sel] + keep_w[sel])).sum()
    return float((Pc[sel] * lose_w[sel]).sum() / tot) if tot > 0 else 0.0


def main():
    meta = json.load(open(os.path.join(OUT, "tiles_meta.json"), encoding="utf-8"))
    T = meta["tile"]
    img = tifffile.imread(os.path.join(REN, "demo-align.tif"))
    g1p = img[:, :, 1].astype(np.float64)[0::2, 1::2]
    g2p = img[:, :, 1].astype(np.float64)[1::2, 0::2]

    print("destroyed fraction (%) in the top octave, as the assumed geometry varies")
    print("%8s %10s %10s %10s %10s" % ("d", "T1", "T2", "T3", "T4"))
    rows = []
    for d in (0.50, 0.45, 0.40):
        vals = []
        for _key, (by, bx) in meta["tiles"].items():
            vals.append(100 * report_d(g1p[by:by + T, bx:bx + T],
                                       g2p[by:by + T, bx:bx + T], d))
        rows.append({"d": d, "top_octave_pct": vals})
        print("%8.2f %10.1f %10.1f %10.1f %10.1f" % (d, *vals))

    base = np.array(rows[0]["top_octave_pct"])
    deltas = [float(np.max(np.abs(np.array(r["top_octave_pct"]) - base))) for r in rows[1:]]
    worst = max(deltas)
    print("\n   perturbation landed (non-zero change): %s" % (worst > 0.0))
    print("   largest change across the whole 0.40-0.50 range: %.2f percentage points" % worst)
    print("   every value still exceeds 8 %%: %s"
          % all(v > 8.0 for r in rows for v in r["top_octave_pct"]))
    print("   headline robust to the unexplained shortfall: %s" % (worst > 0.0 and worst < 8.0))
    with open(os.path.join(OUT, "s9_sensitivity.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "worst_pp": worst,
                   "robust": bool(worst > 0.0 and worst < 8.0)}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
