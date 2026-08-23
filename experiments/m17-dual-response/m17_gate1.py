"""Gate 1 — reproduce M13's headline from its COMMITTED data, with code written
here rather than reused from `m13_analyse.py`.

The gate, exactly as briefed:

  * cell = (stack, shape, step); value = mean of `excess_dn` over the 3 noise
    seeds; regret(w, cell) = value(w, cell) - min_w' value(w', cell)
  * over the 30 cells that carry a depth step: argmin of mean regret = w13 at
    3.171 DN, and argmin of worst-case regret = w13 at 12.111 DN
  * over the 6 zero-step cells: the argmin is the w40 ENDPOINT at 0.000 DN

If any of those four fails, nothing downstream in M17 is a valid comparison and
the milestone stops (AGENTS.md "reproduce one published number from the original
data before extending anyone's experiment").

No RAW access, no M13 binary: this reads only the two committed CSVs.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

M13 = Path(__file__).resolve().parents[1] / "m13-window-depth" / "data"
STACKS = ("109MSDCF", "119MSDCF")

# M13's ladder, from run-m13.ps1. Order matters only for the ENDPOINT label.
LADDER = [0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40]

EXPECT = {
    "argmin_mean": 13,
    "mean_regret": 3.171,
    "argmin_worst": 13,
    "worst_regret": 12.111,
    "null_argmin": 40,
    "null_regret": 0.000,
}


def window_of(name: str) -> int:
    """`tenengrad-w13` -> 13. The CSV also carries a `window` column; both are
    read and cross-checked so a rename cannot silently shift the ladder."""
    return int(name.rsplit("-w", 1)[1])


def load_cells() -> dict[tuple[str, str, int], dict[int, float]]:
    """(stack, shape, step) -> window -> seed-averaged excess_dn."""
    acc: dict[tuple[str, str, int], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for stack in STACKS:
        path = M13 / f"edge-{stack}.csv"
        with path.open(newline="") as fh:
            for row in csv.DictReader(fh):
                if int(row["width"]) != 1:  # regulariser off, M13's stratum
                    continue
                w = window_of(row["measure"])
                assert w == int(row["window"]), (row["measure"], row["window"])
                key = (row["stack"], row["shape"], int(row["step"]))
                acc[key][w].append(float(row["excess_dn"]))
    out = {}
    for key, per_w in acc.items():
        out[key] = {w: sum(v) / len(v) for w, v in per_w.items()}
    return out


def regret_table(cells) -> dict[int, tuple[float, float, tuple]]:
    """window -> (mean regret, worst regret, worst cell)."""
    table = {}
    for w in LADDER:
        regs = []
        for key, per_w in cells.items():
            best = min(per_w.values())
            regs.append((per_w[w] - best, key))
        worst = max(regs, key=lambda r: r[0])
        table[w] = (sum(r[0] for r in regs) / len(regs), worst[0], worst[1])
    return table


def label(w: int) -> str:
    return "ENDPOINT" if w in (LADDER[0], LADDER[-1]) else "interior"


def main() -> int:
    cells = load_cells()
    nseeds = 3
    print(f"M13 committed data: {len(cells)} cells, {len(LADDER)} windows, "
          f"{nseeds} seeds, stratum width=1")
    for stack in STACKS:
        n = sum(1 for k in cells if k[0] == stack)
        print(f"  {stack}: {n} cells")

    step_cells = {k: v for k, v in cells.items() if k[2] > 0}
    null_cells = {k: v for k, v in cells.items() if k[2] == 0}
    print(f"  depth-step cells: {len(step_cells)}   zero-step cells: {len(null_cells)}")

    print("\n-- objective: excess_dn, cells WITH a depth step "
          f"({len(step_cells)} cells) --")
    tbl = regret_table(step_cells)
    print(f"  {'window':>7} {'mean regret':>12} {'worst regret':>13} {'worst cell':>30}")
    for w in LADDER:
        m, wo, cell = tbl[w]
        print(f"  {w:>7} {m:>12.3f} {wo:>13.3f} "
              f"{cell[0] + '/' + cell[1] + '/s' + str(cell[2]):>30}")
    bm = min(LADDER, key=lambda w: tbl[w][0])
    bw = min(LADDER, key=lambda w: tbl[w][1])
    print(f"    min mean regret : w{bm} ({tbl[bm][0]:.3f})  [{label(bm)}]")
    print(f"    min worst regret: w{bw} ({tbl[bw][1]:.3f})  [{label(bw)}]")

    print(f"\n-- NULL: zero-step cells only ({len(null_cells)} cells) --")
    ntbl = regret_table(null_cells)
    nbm = min(LADDER, key=lambda w: ntbl[w][0])
    for w in LADDER:
        print(f"  {w:>7} {ntbl[w][0]:>12.4f}")
    print(f"    min mean regret : w{nbm} ({ntbl[nbm][0]:.4f})  [{label(nbm)}]")

    checks = [
        ("argmin mean regret == w13", bm == EXPECT["argmin_mean"], f"w{bm}"),
        ("mean regret == 3.171 DN",
         abs(tbl[bm][0] - EXPECT["mean_regret"]) < 5e-4, f"{tbl[bm][0]:.4f}"),
        ("argmin worst regret == w13", bw == EXPECT["argmin_worst"], f"w{bw}"),
        ("worst regret == 12.111 DN",
         abs(tbl[bw][1] - EXPECT["worst_regret"]) < 5e-4, f"{tbl[bw][1]:.4f}"),
        ("zero-step argmin == w40 ENDPOINT",
         nbm == EXPECT["null_argmin"] and label(nbm) == "ENDPOINT", f"w{nbm}"),
        ("zero-step regret == 0.000 DN",
         abs(ntbl[nbm][0] - EXPECT["null_regret"]) < 5e-4, f"{ntbl[nbm][0]:.4f}"),
    ]
    print("\n-- GATE 1 --")
    ok = True
    for name, passed, got in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:<36} got {got}")
        ok &= passed
    print(f"\nGATE 1: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
