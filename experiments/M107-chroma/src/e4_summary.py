"""E4 summary -- attribute the OUTPUT fringe across the three render arms.

The arms differ only in how RGB is constructed from the same elected merge:

  linear    binned, camera-native linear, NO demosaic, NO matrix, NO curve,
            NO cosite correction    -- the byte-frozen default path
  binned    --srgb --binned         -- adds matrix, sRGB curve, and M95's
                                       COSITE_SHIFT = 0.25 correction
  demosaic  --srgb (shipped)        -- Malvar-He-Cutler, the path under
                                       investigation

Displacements are converted to SOURCE SENSEL so the arms are comparable:
one output px = cov source px, and the binned arms carry 2 sensel per px while
the demosaic arm carries 1.

Registered hazard (fact 1378): the `binned` arm is NOT a clean control for
co-siting, because COSITE_SHIFT is applied inside it.  Bar B4 therefore checks
the SIGN of the binned-vs-linear difference rather than assuming the arm is
neutral: if co-siting were driving the output fringe, the corrected arm must
move TOWARD zero relative to `linear`.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump

COV = {"tweezers-cpl": 0.9726, "leaf-2-cpl": 0.9344, "bee-3-cpl": 0.9315}
SENSEL_PER_PX = {"linear": 2.0, "binned": 2.0, "demosaic": 1.0}


def rows_of(d):
    if isinstance(d, dict) and "rows" in d:
        return d["rows"]
    if isinstance(d, dict):
        out = []
        for stack, arms in d.items():
            if not isinstance(arms, dict):
                continue
            for arm, rs in arms.items():
                out.extend(rs)
        return out
    return d


if __name__ == "__main__":
    d = json.load(open(os.path.join(OUT, "json", "e4_render_arms.json")))
    rows = rows_of(d)
    print(f"{len(rows)} rows\n")
    print(f"{'stack':>14s} {'arm':>9s} {'n':>3s} "
          f"{'|dR| px':>9s} {'|dB| px':>9s} {'|dR| sensel':>12s} "
          f"{'|dB| sensel':>12s}")
    tab = {}
    for st in sorted({r["stack"] for r in rows}):
        for arm in ("linear", "binned", "demosaic"):
            sel = [r for r in rows if r["stack"] == st and r["arm"] == arm]
            if not sel:
                continue
            k = COV[st] * SENSEL_PER_PX[arm]
            dR = np.median([abs(r["dR"]) for r in sel])
            dB = np.median([abs(r["dB"]) for r in sel])
            tab[(st, arm)] = (dR * k, dB * k)
            print(f"{st:>14s} {arm:>9s} {len(sel):>3d} {dR:>9.4f} {dB:>9.4f} "
                  f"{dR*k:>12.4f} {dB*k:>12.4f}")
    print("\nB4 -- does the co-siting-corrected arm move toward zero?")
    out = []
    for st in sorted({s for (s, a) in tab}):
        if (st, "linear") not in tab or (st, "binned") not in tab:
            continue
        lR, lB = tab[(st, "linear")]
        bR, bB = tab[(st, "binned")]
        dm = tab.get((st, "demosaic"), (float("nan"),) * 2)
        movR, movB = bR - lR, bB - lB
        print(f"  {st}: |dR| linear {lR:.4f} -> binned+COSITE {bR:.4f} "
              f"({movR:+.4f} sensel, {'toward 0' if movR < 0 else 'AWAY from 0'})")
        print(f"  {st}: |dB| linear {lB:.4f} -> binned+COSITE {bB:.4f} "
              f"({movB:+.4f} sensel, {'toward 0' if movB < 0 else 'AWAY from 0'})")
        print(f"  {st}: shipped demosaic arm |dR| {dm[0]:.4f}  |dB| {dm[1]:.4f} sensel")
        out.append({"stack": st, "linear_sensel": [lR, lB],
                    "binned_cosite_sensel": [bR, bB],
                    "demosaic_sensel": list(dm),
                    "cosite_move_sensel": [movR, movB]})
    dump("e4_summary", out)
