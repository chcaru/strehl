"""M78 held-out gate for separately repaired Arm A and Arm B short edges.

This reuses M10's train sets, strategies, solver implementations, and score
function. The fixed test set contains only untouched inherited long edges.
"""

from __future__ import annotations

import csv
import os
import sys
import time

import numpy as np

M10 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m10-deep-align")
sys.path.insert(0, M10)

from m10_lib import graph_stats, read_edges  # noqa: E402
from m10_measure import score, strategies, train_sets  # noqa: E402

BASE_PATH = "data/m10-coffee-bean-edges.csv"
N = 105
CFG = "m10"
MIN_SPAN = 40
MIN_USED = 12
SHIP_GATE = 6.758
HISTORICAL_MARGIN_GATE = 6.358


def replacement_rows(path: str):
    base = read_edges(BASE_PATH, cfg=CFG)
    replacements = {
        (edge.i, edge.j): edge
        for edge in read_edges(path, cfg=CFG)
        if edge.ok and edge.span <= 2
    }
    expected = sum(1 for edge in base if edge.ok and edge.span <= 2)
    if len(replacements) != expected:
        raise RuntimeError(f"{path}: {len(replacements)} replacements, expected {expected}")
    return [
        replacements[(edge.i, edge.j)]
        if edge.ok and edge.span <= 2
        else edge
        for edge in base
    ], set(replacements)


def evaluate(rows, test, test_keys, replacement_keys, arm):
    spans = np.asarray([edge.span for edge in test])
    qcut = float(np.percentile(spans, 75))
    candidates = []
    for train_name, train in train_sets(rows, test_keys, N).items():
        stats = graph_stats(train, N)
        treated = sum((edge.i, edge.j) in replacement_keys for edge in train)
        for strategy, global_fits in strategies(train, N).items():
            if global_fits is None:
                continue
            errors, scale, translation, test_spans = score(global_fits, test)
            coverage = sum(value is not None for value in global_fits)
            if errors.size == 0:
                continue
            robust = errors[test_spans >= qcut]
            candidates.append(
                {
                    "arm": arm,
                    "train": train_name,
                    "strategy": strategy,
                    "edges": len(train),
                    "treated": treated,
                    "cycle_rank": stats["cycle_rank"],
                    "components": stats["components"],
                    "coverage": coverage,
                    "n_test": int(errors.size),
                    "n_robust": int(robust.size),
                    "e_star": float(np.median(robust)) if robust.size else float("nan"),
                    "median": float(np.median(errors)),
                    "p90": float(np.percentile(errors, 90)),
                    "maximum": float(errors.max()),
                    "scale": float(np.median(scale)),
                    "translation": float(np.median(translation)),
                }
            )
    return candidates


def admissible(row) -> bool:
    return (
        row["treated"] > 0
        and row["cycle_rank"] > 0
        and row["coverage"] == N
    )


def show_best(label, candidates, baseline_map):
    valid = [row for row in candidates if admissible(row)]
    winner = min(valid, key=lambda row: row["e_star"])
    paired = baseline_map[(winner["train"], winner["strategy"])]
    print(f"\n{label}")
    print(
        f"  admissible rows={len(valid)}; best E*={winner['e_star']:.6f} px "
        f"({winner['strategy']} / {winner['train']})"
    )
    print(
        f"  train edges={winner['edges']}, treated={winner['treated']}, "
        f"cycle rank={winner['cycle_rank']}, coverage={winner['coverage']}/{N}"
    )
    print(
        f"  fixed test n={winner['n_test']}, robust tail n={winner['n_robust']}; "
        f"median={winner['median']:.6f}, p90={winner['p90']:.6f}, "
        f"max={winner['maximum']:.6f}"
    )
    print(
        f"  paired untreated E*={paired['e_star']:.6f}; "
        f"delta={winner['e_star'] - paired['e_star']:+.6f}"
    )
    print(
        f"  strict <{SHIP_GATE:.3f}: "
        f"{'PASS' if winner['e_star'] < SHIP_GATE else 'FAIL'}; "
        f"historical <= {HISTORICAL_MARGIN_GATE:.3f}: "
        f"{'PASS' if winner['e_star'] <= HISTORICAL_MARGIN_GATE else 'FAIL'}"
    )
    print("  top six admissible rows:")
    for row in sorted(valid, key=lambda value: value["e_star"])[:6]:
        print(
            f"    {row['e_star']:>9.6f}  {row['strategy']:<14} "
            f"{row['train']:<18} treated={row['treated']:>3} "
            f"cycle={row['cycle_rank']:>3}"
        )
    return winner, paired


def main() -> int:
    started = time.time()
    baseline = read_edges(BASE_PATH, cfg=CFG)
    test = [
        edge
        for edge in baseline
        if edge.ok and edge.span >= MIN_SPAN and edge.used >= MIN_USED
    ]
    test_keys = {(edge.i, edge.j) for edge in test}
    if any(edge.span <= 2 for edge in test):
        raise RuntimeError("short edge leaked into held-out test")

    base_candidates = evaluate(baseline, test, test_keys, set(), "baseline")
    base_map = {
        (row["train"], row["strategy"]): row
        for row in base_candidates
    }
    unrestricted = min(
        (
            row
            for row in base_candidates
            if row["cycle_rank"] > 0
            and row["coverage"] == N
        ),
        key=lambda row: row["e_star"],
    )

    print("M78 FIXED HELD-OUT GATE — coffee-bean")
    print(
        f"  test={len(test)} inherited direct edges, span >= {MIN_SPAN}, "
        f"used >= {MIN_USED}, spans {min(edge.span for edge in test)}.."
        f"{max(edge.span for edge in test)}"
    )
    print("  repaired edges in test=0")
    print(
        f"  unrestricted baseline best E*={unrestricted['e_star']:.6f} px "
        f"({unrestricted['strategy']} / {unrestricted['train']})"
    )
    print(
        f"  reproduction versus 6.758: "
        f"{'PASS' if abs(unrestricted['e_star'] - SHIP_GATE) < 0.01 else 'FAIL'}"
    )

    all_candidates = list(base_candidates)
    outcomes = []
    for label, path in [
        ("ARM A — blur-equalised span-1/2", "data/a-primary-edges.csv"),
        ("ARM B — half-shift span-1/2", "data/b-primary-edges.csv"),
    ]:
        rows, keys = replacement_rows(path)
        candidates = evaluate(rows, test, test_keys, keys, label)
        winner, paired = show_best(label, candidates, base_map)
        outcomes.append((label, winner, paired))
        all_candidates.extend(candidates)

    with open("data/heldout-candidates.csv", "w", newline="") as handle:
        fieldnames = list(all_candidates[0])
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_candidates)
    print(f"\n  wrote data/heldout-candidates.csv ({len(all_candidates)} rows)")
    print(f"  wall clock={time.time() - started:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
