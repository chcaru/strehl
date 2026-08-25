"""R17 -- D for M107's transfer check, and whether D alone clears it.

ORCH asks for D = max/min of the terms alongside any cancellation claim.
M107's transfer check is applied/eps_r with applied = e_on - e_off, so its two
terms are the OFF-arm and ON-arm radial estimates and it owes a D.

But R15 already holds the data for a sharper question. R15 swept a support
floor and measured the narrowing shift falling 22.9% -> 0.8%. If D barely
moves across that sweep while the shift moves by more than 5x, then D -- like
"is it a ratio" and "is it absolute" before it -- does not on its own decide
exposure, and support is an INDEPENDENT axis that must be reported beside it.

That is not a rebuttal of ORCH's table. It is the same structural point ORCH
has now accepted twice: a single scalar summarising a statistic's shape or
scale cannot decide a question that depends on what the estimator was allowed
to integrate.

BARS -- registered before running.

  D1  ACROSS THE FLOOR SWEEP, D IS NEARLY CONSTANT WHILE THE SHIFT IS NOT.
      Registered: D varies by under 1.5x across floors 0..480 while the
      narrowing shift varies by over 5x.  If both hold, D is insufficient
      on its own and support is independent of it.
      Falsified if D varies by 1.5x or more -- in which case D tracks the
      shift after all and ORCH's scalar is doing the work.

  D2  WHERE SUPPORT IS ADEQUATE, MY DATA SHOULD CORROBORATE ORCH'S TABLE.
      At floor 120 my D lands in some bin of ORCH's table; registered that
      my measured shift there is within 2x of that bin's median |shift|.
      Falsified if it is outside 2x, which would put my data in conflict
      with the table rather than in support of it.

  D3  WHERE SUPPORT IS INADEQUATE, THE TABLE SHOULD UNDER-PREDICT.
      Registered: at floor 0 my shift EXCEEDS the same bin's median by more
      than 2x.  Falsified if floor 0 also lands inside 2x, which would mean
      the table already absorbs the support effect and D1's conclusion is
      unnecessary.

ORCH's bins, transcribed from the broadcast:
    [1.00,1.25) 0.68%  [1.25,1.50) 0.90%  [1.50,2) 3.79%
    [2,3) 6.15%  [3,5) 6.71%  [5,8) 7.58%  [8,inf) 8.04%
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r13_clean_calib import EPS, R13  # noqa: E402
from r15_reconcile import FLOORS, estimate_floored, narrow  # noqa: E402

BINS = [(1.00, 1.25, 0.68), (1.25, 1.50, 0.90), (1.50, 2.0, 3.79),
        (2.0, 3.0, 6.15), (3.0, 5.0, 6.71), (5.0, 8.0, 7.58), (8.0, 1e18, 8.04)]


def orch_bin(d):
    for lo, hi, med in BINS:
        if lo <= d < hi:
            return f"[{lo:g},{hi:g})" if hi < 1e17 else "[8,inf)", med
    return "below table", float("nan")


def main():
    print("=" * 78)
    print("R17 -- D for M107's transfer check, and whether D alone clears it")
    print("=" * 78)
    off = tifffile.imread(os.path.join(R13, "off.tif"))
    on = tifffile.imread(os.path.join(R13, "on.tif"))
    ro, go = off[..., 0].astype(np.float32), off[..., 1].astype(np.float32)
    rn, gn = on[..., 0].astype(np.float32), on[..., 1].astype(np.float32)
    ro8, go8 = narrow(off[..., 0]), narrow(off[..., 1])
    rn8, gn8 = narrow(on[..., 0]), narrow(on[..., 1])

    print(f"\n{'floor':>6s} {'n':>6s} {'e_off':>9s} {'e_on':>9s} {'D':>6s} "
          f"{'ORCH bin':>10s} {'pred':>6s} {'measured':>9s}")
    rows = []
    for f in FLOORS:
        a16, n, _ = estimate_floored(ro, go, f)
        b16, _, _ = estimate_floored(rn, gn, f)
        a8, _, _ = estimate_floored(ro8, go8, f)
        b8, _, _ = estimate_floored(rn8, gn8, f)
        t16, t8 = (b16 - a16) / EPS, (b8 - a8) / EPS
        shift = 100.0 * abs(t8 - t16) / abs(t16)
        d = max(abs(a16), abs(b16)) / max(min(abs(a16), abs(b16)), 1e-18)
        name, pred = orch_bin(d)
        rows.append((f, n, a16, b16, d, name, pred, shift))
        print(f"{f:6.0f} {n:6d} {a16*1e6:+9.1f} {b16*1e6:+9.1f} {d:6.2f} "
              f"{name:>10s} {pred:5.2f}% {shift:8.1f}%")

    ds = [r[4] for r in rows]
    shifts = [r[7] for r in rows]
    d_range = max(ds) / max(min(ds), 1e-18)
    s_range = max(shifts) / max(min(shifts), 1e-18)
    print(f"\nD1  D range {d_range:.2f}x   shift range {s_range:.1f}x")
    d1 = d_range < 1.5 and s_range > 5.0
    print(f"    D1 {'HOLDS -- D is near-constant while the shift is not;' if d1 else 'FALSIFIED -- D tracks the shift'}")
    if d1:
        print("       support is an axis INDEPENDENT of D and must be reported beside it.")

    r120 = next(r for r in rows if r[0] == 120.0)
    r0 = next(r for r in rows if r[0] == 0.0)
    d2 = r120[7] <= 2.0 * r120[6]
    d3 = r0[7] > 2.0 * r0[6]
    print(f"\nD2  floor 120 (adequate support): D {r120[4]:.2f} -> bin {r120[5]} "
          f"pred {r120[6]:.2f}%, measured {r120[7]:.1f}%")
    print(f"    D2 {'HOLDS -- my data CORROBORATES the table' if d2 else 'FALSIFIED -- conflicts with the table'}")
    print(f"\nD3  floor 0 (no support floor):  D {r0[4]:.2f} -> bin {r0[5]} "
          f"pred {r0[6]:.2f}%, measured {r0[7]:.1f}%  ({r0[7]/max(r0[6],1e-9):.1f}x the bin median)")
    print(f"    D3 {'HOLDS -- the table UNDER-predicts when support is inadequate' if d3 else 'FALSIFIED'}")

    print("\n" + "=" * 78)
    print(f"M107's D, as asked: {r120[4]:.2f} at floor 120 ({r120[5]}), "
          f"{r0[4]:.2f} at floor 0.")
    print("Both in the UNPROTECTED regime. M107 never claimed ratio cancellation --")
    print("its stated reason was the reader (tifffile throughout) -- but the D is owed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
