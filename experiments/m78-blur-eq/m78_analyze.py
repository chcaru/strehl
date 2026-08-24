"""M78 controls and conservation statistics.

All inputs are committed inherited edge tables or M78 measurement CSVs. This
script never reads a capture directory.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict

import numpy as np

from m78_lib import IDENT, corner_err, read_edges

W = 48


def edge_map(path: str) -> dict[tuple[int, int], object]:
    result = {}
    for edge in read_edges(path, cfg="m10"):
        if not edge.ok:
            continue
        key = (edge.i, edge.j)
        if key not in result or edge.used > result[key].used:
            result[key] = edge
    return result


def log_scale(edge) -> float:
    return math.log(abs(edge.a))


def conservation(
    short: dict[tuple[int, int], object],
    anchors: dict[tuple[int, int], object],
    start: int = 0,
    width: int = W,
) -> float:
    denominator = sum(log_scale(short[(index, index + 1)]) for index in range(start, start + width))
    return log_scale(anchors[(start, start + width)]) / denominator


def all_windows(short, anchors, n: int, width: int = W) -> np.ndarray:
    values = []
    for start in range(n - width):
        if (start, start + width) not in anchors:
            continue
        if not all((index, index + 1) in short for index in range(start, start + width)):
            continue
        values.append(conservation(short, anchors, start, width))
    return np.asarray(values)


def local_telescoping(edges: dict[tuple[int, int], object], n: int) -> np.ndarray:
    values = []
    for index in range(n - 2):
        keys = ((index, index + 1), (index + 1, index + 2), (index, index + 2))
        if not all(key in edges for key in keys):
            continue
        denominator = log_scale(edges[keys[0]]) + log_scale(edges[keys[1]])
        if abs(denominator) > 1e-12:
            values.append(log_scale(edges[keys[2]]) / denominator)
    return np.asarray(values)


def percentile_summary(values: np.ndarray) -> str:
    return (
        f"n={values.size}, median={np.median(values):.6f}, "
        f"p95={np.percentile(values, 95):.6f}, max={values.max():.6f}"
    )


def show_self(label: str, path: str) -> None:
    values = np.asarray(
        [corner_err(edge.t(), IDENT) for edge in read_edges(path, cfg="m10") if edge.ok]
    )
    passed = np.median(values) <= 0.05 and np.percentile(values, 95) <= 0.19
    print(f"  {label:<12} {percentile_summary(values)} -> {'PASS' if passed else 'FAIL'}")


def read_field(path: str) -> list[dict[str, str]]:
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def show_field(label: str, path: str) -> None:
    rows = read_field(path)
    grouped: dict[tuple[str, float], list[float]] = defaultdict(list)
    for row in rows:
        if row["q"]:
            grouped[(row["case"], float(row["g_true"]))].append(float(row["q"]))
    medians: dict[tuple[str, float], float] = {}
    print(f"\n  {label}:")
    print(f"    {'case':<8} {'g':>9} {'n':>3} {'median Q':>10} {'p25':>10} {'p75':>10}")
    for (case, scale), values in sorted(grouped.items()):
        array = np.asarray(values)
        median = float(np.median(array))
        medians[(case, scale)] = median
        print(
            f"    {case:<8} {scale:>9.1e} {array.size:>3} {median:>10.6f} "
            f"{np.percentile(array, 25):>10.6f} {np.percentile(array, 75):>10.6f}"
        )
    treated = [value for (case, _), value in medians.items() if case == "treated"]
    accuracy = all(0.90 <= value <= 1.10 for value in treated)
    spread = max(treated) - min(treated)
    scales = sorted(scale for case, scale in medians if case == "treated")
    treatment_deltas = [
        medians[("treated", scale)] - medians[("raw", scale)] for scale in scales
    ]
    print(
        f"    treated range={spread:.6f}; accuracy={'PASS' if accuracy else 'FAIL'}, "
        f"flatness={'PASS' if spread <= 0.15 else 'FAIL'}"
    )
    print(
        f"    treated-minus-raw median-Q range "
        f"[{min(treatment_deltas):+.6f},{max(treatment_deltas):+.6f}]"
    )
    raw_small = medians[("raw", min(scale for _, scale in medians))]
    print(
        f"    raw smallest-probe |Q-1|={abs(raw_small - 1):.6f}; "
        f"positive mechanism {'FIRES' if abs(raw_small - 1) >= 0.10 else 'DOES NOT FIRE'}"
    )


def show_conservation() -> None:
    base = edge_map("data/m10-coffee-bean-edges.csv")
    base_c = conservation(base, base)
    base_windows = all_windows(base, base, 105)
    base_local = local_telescoping(base, 105)
    print("\nCONSERVATION — coffee-bean")
    print(f"  baseline fixed C_0={base_c:.6f}")
    print(
        f"  baseline windows n={base_windows.size}, median={np.median(base_windows):.6f}, "
        f"min={base_windows.min():.6f}, max={base_windows.max():.6f}; "
        f"local median={np.median(base_local):.6f}"
    )
    cases = [
        ("A q=1/12", "data/a-q0833333-edges.csv"),
        ("A q=1/6 primary", "data/a-primary-edges.csv"),
        ("A q=1/3", "data/a-q3333333-edges.csv"),
        ("A q=2/3", "data/a-q6666667-edges.csv"),
        ("B half primary", "data/b-primary-edges.csv"),
        ("B half mirror", "data/b-mirror-edges.csv"),
        ("B integer", "data/b-integer-edges.csv"),
    ]
    print(
        f"  {'case':<18} {'ok/need':>9} {'C(0..48)':>11} {'delta C':>10} "
        f"{'denom x':>9} {'|C-1| improve':>14} {'windows med':>12} {'local med':>11}"
    )
    fixed_results = {}
    for label, path in cases:
        treatment = edge_map(path)
        required = 104 if label == "B integer" else 207
        fixed = conservation(treatment, base)
        fixed_results[label] = fixed
        windows = all_windows(treatment, base, 105)
        local = local_telescoping(treatment, 105)
        improvement = abs(base_c - 1.0) - abs(fixed - 1.0)
        print(
            f"  {label:<18} {len(treatment):>3}/{required:<5} {fixed:>11.6f} "
            f"{fixed - base_c:>+10.6f} {base_c / fixed:>9.6f} {improvement:>+14.6f} "
            f"{np.median(windows):>12.6f} "
            f"{np.median(local) if local.size else float('nan'):>11.6f}"
        )
    a_primary = fixed_results["A q=1/6 primary"]
    a_s1 = (
        abs(a_primary - base_c) >= 0.15
        and abs(a_primary - 1.0) <= abs(base_c - 1.0) - 0.15
        and a_primary >= 0.85
    )
    b_primary = fixed_results["B half primary"]
    b_mirror = fixed_results["B half mirror"]
    b_movements = (b_primary - base_c, b_mirror - base_c)
    b_s1 = (
        abs(b_movements[0]) >= 0.15
        and abs(b_movements[1]) >= 0.15
        and np.sign(b_movements[0]) == np.sign(b_movements[1])
        and abs(b_primary - 1.0) <= abs(base_c - 1.0) - 0.15
        and abs(b_mirror - 1.0) <= abs(base_c - 1.0) - 0.15
        and b_primary >= 0.85
        and b_mirror >= 0.85
    )
    print(
        f"  registered A-S1={'PASS' if a_s1 else 'FAIL'}; "
        f"B-S1={'PASS' if b_s1 else 'FAIL'}"
    )

    primary = edge_map("data/b-primary-edges.csv")
    mirror = edge_map("data/b-mirror-edges.csv")
    integer = edge_map("data/b-integer-edges.csv")
    half_parity = np.asarray(
        [
            corner_err(primary[key].t(), mirror[key].t())
            for key in primary.keys() & mirror.keys()
        ]
    )
    integer_delta = np.asarray(
        [corner_err(integer[key].t(), base[key].t()) for key in integer.keys() & base.keys()]
    )
    print("\nPHASE-ARM TRANSFORM COMPARISONS (plane-corner px)")
    print(
        f"  primary versus mirror: n={half_parity.size}, "
        f"median={np.median(half_parity):.9f}, "
        f"p95={np.percentile(half_parity, 95):.9f}, max={half_parity.max():.9f}"
    )
    print(
        f"  integer placebo versus inherited: n={integer_delta.size}, "
        f"median={np.median(integer_delta):.9f}, max={integer_delta.max():.9f}"
    )

    base112 = edge_map("data/m12-stack-112-edges.csv")
    phase112 = edge_map("data/b-112-edges.csv")
    raw112 = conservation(base112, base112)
    treated112 = conservation(phase112, base112)
    print("\nCONSERVATION — 112MSDCF placebo")
    print(
        f"  raw={raw112:.6f}, half-shift={treated112:.6f}, "
        f"movement={treated112 - raw112:+.6f}, "
        f"B-C2={'PASS' if abs(treated112 - raw112) < 0.10 else 'FAIL'}"
    )

    print("\nSHORT-EDGE FIT OBSERVABLES")
    print(f"  {'case':<18} {'n':>4} {'used med':>9} {'rms med':>10} {'peak med':>10}")
    for label, path in [
        ("inherited", "data/m10-coffee-bean-edges.csv"),
        ("A q=1/6 primary", "data/a-primary-edges.csv"),
        ("B half primary", "data/b-primary-edges.csv"),
    ]:
        edges = [
            edge
            for edge in read_edges(path, cfg="m10")
            if edge.ok and edge.span <= 2
        ]
        print(
            f"  {label:<18} {len(edges):>4} "
            f"{np.median([edge.used for edge in edges]):>9.1f} "
            f"{np.median([edge.rms for edge in edges]):>10.6f} "
            f"{np.median([edge.peak for edge in edges]):>10.6f}"
        )


def main() -> int:
    print("M78 CONTROL AND CONSERVATION ANALYSIS")
    print("\nSELF-PAIR CORNER ERROR (plane px)")
    show_self("A-C0", "data/a-self-edges.csv")
    show_self("B-C0", "data/b-self-edges.csv")

    print("\nINTERPOLATOR-FREE FIELD Q(g)")
    show_field("A-C1 native sigmas 0.5/1.5", "data/a-mismatch-field.csv")
    show_field("A-C1p native sigmas 1.0/1.0", "data/a-equal-field.csv")
    show_field("B-C3 exact composed render", "data/b-phase-field.csv")
    show_conservation()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
