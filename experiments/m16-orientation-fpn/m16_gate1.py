"""M16 Gate 1 — independently reproduce SYNTHESIS fact 83 from M15's committed data.

Written for M16 from the published description of the statistic, not copied from
`m15_analyse.py`. Reads only
`experiments/m15-regulariser-window/data/edge-{109,119}MSDCF.csv`.

Recipe (M15 Sec.6 / fact 83):
  cell            = (stack, geometry, step),  step > 0
  E_g(cell, w)    = mean over the 5 seeds of `excess_dn` at regulariser width g
  w*(cell, g)     = argmin over the 24-window ladder, ties to the SMALLEST window
  shift(cell)     = w*(cell, 17) - w*(cell, 1)
  report per geometry: median w*(1), median w*(17), median shift, and the
  narrower/wider/same counts.

Targets that must be recovered exactly:
  bar        10 cells  10.5 -> 12.0  +1.0   2/6/2
  horizontal 10 cells   9.0 ->  7.0  -2.5  10/0/0
  vertical   10 cells  17.0 -> 19.0  +1.5   2/6/2
  ALL        30 cells  13.0 -> 12.0   0.0  14/12/4
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
M15_DATA = HERE.parent / "m15-regulariser-window" / "data"

TARGETS = {
    "bar": (10, 10.5, 12.0, 1.0, (2, 6, 2)),
    "horizontal": (10, 9.0, 7.0, -2.5, (10, 0, 0)),
    "vertical": (10, 17.0, 19.0, 1.5, (2, 6, 2)),
    "ALL": (30, 13.0, 12.0, 0.0, (14, 12, 4)),
}


def geometry(shape: str) -> str:
    """`vertical@298` -> `vertical`. The suffix is the tile coordinate."""
    return shape.split("@", 1)[0]


def load(path: Path):
    """(stack, geometry, step, width, window) -> list of excess_dn, one per seed."""
    acc = defaultdict(list)
    order = defaultdict(list)  # (cell, width) -> windows in CSV order
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            step = int(row["step"])
            if step == 0:
                continue
            cell = (row["stack"], geometry(row["shape"]), step)
            width = int(row["width"])
            window = int(row["window"])
            key = (cell, width, window)
            if not acc[key]:
                order[(cell, width)].append(window)
            acc[key].append(float(row["excess_dn"]))
    return acc, order


def argmin_window(acc, order, cell, width):
    """argmin over the ladder of the seed-mean excess, ties to the first-listed
    window. The CSV lists windows in ascending order, so that is the smallest."""
    best_w = None
    best_v = None
    for w in order[(cell, width)]:
        vals = acc[(cell, width, w)]
        v = sum(vals) / len(vals)
        if best_v is None or v < best_v:
            best_v, best_w = v, w
    return best_w, best_v


def main() -> int:
    acc = defaultdict(list)
    order = defaultdict(list)
    files = sorted(M15_DATA.glob("edge-*MSDCF.csv"))
    if not files:
        print(f"FAIL: no M15 edge CSVs under {M15_DATA}")
        return 2
    for path in files:
        a, o = load(path)
        for k, v in a.items():
            acc[k].extend(v)
        for k, v in o.items():
            if not order[k]:
                order[k] = v
    print(f"gate1: read {len(files)} file(s): {', '.join(p.name for p in files)}")

    cells = sorted({k[0] for k in acc})
    nseed = {len(acc[k]) for k in acc}
    print(f"gate1: {len(cells)} cells with step>0, seeds per point {sorted(nseed)}")
    if nseed != {5}:
        print(f"FAIL: expected exactly 5 seeds per point, got {sorted(nseed)}")
        return 2

    per_cell = {}
    for cell in cells:
        w1, _ = argmin_window(acc, order, cell, 1)
        w17, _ = argmin_window(acc, order, cell, 17)
        per_cell[cell] = (w1, w17, w17 - w1)

    groups = defaultdict(list)
    for cell, v in per_cell.items():
        groups[cell[1]].append(v)
        groups["ALL"].append(v)

    print()
    print(f"{'geometry':<12}{'n':>4}{'med w*(1)':>11}{'med w*(17)':>12}"
          f"{'med shift':>11}{'narrower':>10}{'wider':>7}{'same':>6}  verdict")
    ok = True
    for g in ("bar", "horizontal", "vertical", "ALL"):
        vs = groups[g]
        m1 = statistics.median(v[0] for v in vs)
        m17 = statistics.median(v[1] for v in vs)
        ms = statistics.median(v[2] for v in vs)
        nn = sum(1 for v in vs if v[2] < 0)
        nw = sum(1 for v in vs if v[2] > 0)
        ns = sum(1 for v in vs if v[2] == 0)
        want = TARGETS[g]
        got = (len(vs), m1, m17, ms, (nn, nw, ns))
        good = got == want
        ok &= good
        print(f"{g:<12}{len(vs):>4}{m1:>11.1f}{m17:>12.1f}{ms:>11.1f}"
              f"{nn:>10}{nw:>7}{ns:>6}  {'MATCH' if good else 'MISMATCH want=' + str(want)}")

    print()
    print("per-cell shifts (stack, geometry, step): w*(1) -> w*(17) = shift")
    for cell in sorted(cells, key=lambda c: (c[1], c[0], c[2])):
        w1, w17, sh = per_cell[cell]
        print(f"  {cell[0]:<9} {cell[1]:<11} step={cell[2]:<3} {w1:>3} -> {w17:>3} = {sh:+d}")

    print()
    print("GATE 1 PASS" if ok else "GATE 1 FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
