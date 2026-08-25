"""O14 -- is the oracle cube narrowed? Tests SPACING, not level count.

ORCH broadened the quantisation hazard (fact 1765): the vulnerable operation is
AVERAGING, not differencing, because quantisation error is value-deterministic
and so moves a whole sample population together instead of averaging down. That
widens the candidate set from `pick_tiles` to ANY pooled statistic -- which puts
the oracle tree in scope for the first time. It never calls `pick_tiles`, so
o11/o12 did not cover it, and its headline (excess deficit, +0.81 to +2.38 pp)
is exactly the small pooled number ORCH says is most at risk.

WHY NOT LEVEL COUNT. A low-contrast ROI legitimately holds few distinct levels.
ROI-FLAT's contrast is 1.18 BY DESIGN -- it is the flat control. A count-based
bar would convict it for being flat, which is the property it was chosen for,
and would clear a narrowed high-contrast ROI that still spans a wide range.

WHAT DISCRIMINATES. Native RAW arrives as consecutive integers: the gap between
neighbouring distinct values is 1. Data that passed an 8-bit stage and was
rescaled back to 16-bit lands on a lattice with a constant stride > 1. Spacing
separates narrowing from low contrast; count cannot.

BAR, stated before the numbers: an array is NATIVE if the modal gap between
consecutive distinct levels is exactly 1 and at least 90 % of gaps are 1.
NARROWED if the modal gap exceeds 1.

POWER CONTROL (discipline 594/595): a null here is a claim about the world only
if the instrument could have said otherwise, so every ROI is ALSO measured after
a planted 8-bit round trip. The planted arm must read NARROWED with the stride
it was given. If it does not, this script proves nothing and says so.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

CUBE = pathlib.Path(r"C:\dev\strehl-out\M95-oracle")
OUTD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
GAP1_BAR = 0.90


def spacing(a: np.ndarray) -> dict:
    u = np.unique(a)
    if u.size < 2:
        return dict(levels=int(u.size), modal_gap=0, gap1_frac=0.0, native=False)
    g = np.diff(u.astype(np.int64))
    vals, cnts = np.unique(g, return_counts=True)
    modal = int(vals[int(np.argmax(cnts))])
    f1 = float((g == 1).sum() / g.size)
    return dict(levels=int(u.size), lo=int(u[0]), hi=int(u[-1]),
                modal_gap=modal, gap1_frac=f1,
                native=bool(modal == 1 and f1 >= GAP1_BAR))


def plant_8bit(a: np.ndarray) -> np.ndarray:
    """Exactly the loss ORCH described: 16-bit RGB -> uint8 -> back."""
    lo, hi = int(a.min()), int(a.max())
    if hi <= lo:
        return a.copy()
    q = np.round((a.astype(np.float64) - lo) / (hi - lo) * 255.0)
    return (q / 255.0 * (hi - lo) + lo).astype(np.uint16)


def main() -> int:
    rois = ["ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT", "ROI-FLAT"]
    rows, ctrl_ok = [], 0
    print(f"BAR: NATIVE = modal gap 1 AND >= {GAP1_BAR:.0%} of gaps are 1\n")
    print(f"{'ROI':16s} {'arm':9s} {'levels':>8s} {'range':>16s} "
          f"{'modalgap':>9s} {'gap==1':>8s}  verdict")

    for nm in rois:
        p = CUBE / f"{nm}.g1.npy"
        if not p.exists():
            raise SystemExit(f"COVERAGE FAILURE: {p} missing")
        c = np.load(p, mmap_mode="r")
        fr = np.asarray(c[c.shape[0] // 2])  # a mid-stack frame, as pooled

        for arm, a in (("real", fr), ("plant8", plant_8bit(fr))):
            s = spacing(a)
            s.update(roi=nm, arm=arm, dtype=str(a.dtype), frame=int(c.shape[0] // 2))
            rows.append(s)
            print(f"{nm:16s} {arm:9s} {s['levels']:8d} "
                  f"{s.get('lo', 0):7d}..{s.get('hi', 0):<7d} "
                  f"{s['modal_gap']:9d} {s['gap1_frac']:7.1%}  "
                  f"{'NATIVE' if s['native'] else 'NARROWED'}")
            if arm == "plant8" and not s["native"] and s["modal_gap"] > 1:
                ctrl_ok += 1
        print()

    real = [r for r in rows if r["arm"] == "real"]
    print("=" * 78)
    print(f"POWER CONTROL: planted 8-bit arm read NARROWED on {ctrl_ok}/{len(rois)} ROIs")
    if ctrl_ok != len(rois):
        print("INSTRUMENT FAILED -- it could not detect a known narrowing. "
              "The real-arm reading below proves NOTHING.")
        return 1
    nnat = sum(r["native"] for r in real)
    print(f"REAL ARM: NATIVE on {nnat}/{len(real)} ROIs "
          f"(levels {min(r['levels'] for r in real)}..{max(r['levels'] for r in real)})")
    print("VERDICT:", "cube is native precision; no quantisation floor enters "
          "any pooled statistic" if nnat == len(real) else "NARROWING PRESENT")
    with open(os.path.join(OUTD, "o14_cubeprecision.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    return 0 if nnat == len(real) else 1


if __name__ == "__main__":
    raise SystemExit(main())
