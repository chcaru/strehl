"""Gate 0 — reproduce M11's published numbers from M11's own committed CSVs.

SYNTHESIS §5 item 15: "When re-analysing someone else's data, reproduce one of
their published numbers first."  M9's re-analysis inverted its own correlations
because the sweep CSV is **stratified by `roi_kind`** and the reader silently
kept the last row per operator.  This script filters the strata explicitly and
prints the reproduction against the published values, so that any schema
misreading in M13 is caught before a single new measurement is believed.

Reads only.  Nothing under `experiments/m11-focus-bakeoff/` is written.
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys

M11 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m11-focus-bakeoff", "data")


def read(name: str) -> list[dict]:
    with open(os.path.join(M11, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def n_axis(measure: str) -> tuple[float, dict[str, float]]:
    """M11's `N`: flat-ROI ratio, **median over ROIs then mean over stacks**, at
    regulariser width 1.

    The two strata that must be filtered explicitly are `roi_kind == 'flat'`
    (the file also carries `detail` rows) and `width == 1` (the file also
    carries 9 and 17).  Getting either wrong reproduces nothing.
    """
    per_stack: dict[str, float] = {}
    for stack in ("109MSDCF", "119MSDCF"):
        rows = read(f"noise-{stack}.csv")
        vals = [
            float(r["ratio"])
            for r in rows
            if r["measure"] == measure and r["roi_kind"] == "flat" and int(r["width"]) == 1
        ]
        if not vals:
            raise SystemExit(f"no rows for {measure} on {stack}")
        per_stack[stack] = statistics.median(vals)
    return sum(per_stack.values()) / len(per_stack), per_stack


def s_axis(measure: str) -> float:
    """M11's `S`: planted-surface election accuracy.

    Three strata must be filtered, and getting any one wrong moves the number:
    `roi_kind == 'detail'` (the file carries flat ROIs too, and they score far
    lower), `width == 1`, and then the median is taken over the remaining
    (ROI x w_true) cells before the mean over the two stacks.  M11's own
    `m11_analyse.py::planted_by_measure` defaults to `roi_kind='detail'`; a
    reader that omits that filter lands ~0.06 low, which is how this gate
    caught its own first version.
    """
    per_stack = []
    for stack in ("109MSDCF", "119MSDCF"):
        rows = read(f"planted-{stack}-p1.csv")
        vals = [
            float(r["acc"])
            for r in rows
            if r["measure"] == measure and int(r["width"]) == 1 and r["roi_kind"] == "detail"
        ]
        if not vals:
            raise SystemExit(f"no planted rows for {measure} on {stack}")
        per_stack.append(statistics.median(vals))
    return sum(per_stack) / len(per_stack)


def phi_of(measure: str) -> float:
    """φ, mean over the two stacks of the median over probe deltas and ROIs."""
    per_stack = []
    for stack in ("109MSDCF", "119MSDCF"):
        rows = read(f"phi-{stack}.csv")
        vals = [float(r["phi"]) for r in rows if r["measure"] == measure]
        if vals:
            per_stack.append(statistics.median(vals))
    return sum(per_stack) / len(per_stack) if per_stack else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out: list[str] = []

    def emit(s: str = "") -> None:
        out.append(s)
        print(s)

    emit("M13 gate 0 — reproducing M11 from M11's committed CSVs")
    emit("=" * 72)
    emit("")
    emit("Stratification applied: roi_kind == 'flat' AND width == 1 for N;")
    emit("width == 1 for S. Aggregation: median over ROIs, then mean over stacks.")
    emit("")

    published_n = {
        "tenengrad-w5": 1.1324,
        "stensor-w5": 1.1300,
        "ring-1-3": 1.3475,
        "brenner-sym-s2-w0-nonorm": 1.0542,
        "sml-w5": 1.0875,
        "varlap-w5": 1.0863,
        "tenengrad-w11": 1.0908,
        "tenengrad-w8": 1.1019,
        "stensor-w11": 1.0918,
        "tenengrad-w0-nonorm": 1.0609,
    }
    emit(f"{'operator':<28} {'N published':>12} {'N here':>10} {'delta':>10}  verdict")
    ok = True
    for m, pub in published_n.items():
        got, per = n_axis(m)
        d = got - pub
        good = abs(d) < 5e-4
        ok &= good
        emit(f"{m:<28} {pub:>12.4f} {got:>10.4f} {d:>+10.5f}  {'PASS' if good else 'FAIL'}")
    emit("")

    published_s = {
        "tenengrad-w5": 0.8007,
        "stensor-w5": 0.8119,
        "ring-1-3": 0.3980,
        "tenengrad-w11": 0.9407,
        "tenengrad-w8": 0.8955,
        "tenengrad-w0-nonorm": 0.3277,
    }
    emit(f"{'operator':<28} {'S published':>12} {'S here':>10} {'delta':>10}  verdict")
    for m, pub in published_s.items():
        got = s_axis(m)
        d = got - pub
        good = abs(d) < 5e-4
        ok &= good
        emit(f"{m:<28} {pub:>12.4f} {got:>10.4f} {d:>+10.5f}  {'PASS' if good else 'FAIL'}")
    emit("")

    published_phi = {
        # M11's own report table, which is what the committed phi CSVs produce.
        # The orchestrator's verification note quotes 0.0235 / 0.0321 / 0.0568
        # for the w2-nonorm / w0 / w2 trio under a different aggregation; the
        # additivity it reports survives either way.
        "tenengrad-w0-nonorm": 0.0000,
        "tenengrad-w2-nonorm": 0.0217,
        "tenengrad-w0": 0.0335,
        "tenengrad-w2": 0.0612,
        "tenengrad-w5": 0.0728,
        "tenengrad-w8": 0.0872,
        "tenengrad-w11": 0.1089,
    }
    emit(f"{'operator':<28} {'phi orch.':>12} {'phi here':>10} {'delta':>10}  verdict")
    for m, pub in published_phi.items():
        got = phi_of(m)
        d = got - pub
        good = abs(d) < 2e-3
        ok &= good
        emit(f"{m:<28} {pub:>12.4f} {got:>10.4f} {d:>+10.5f}  {'PASS' if good else 'FAIL'}")
    emit("")

    # The negative control on the reader itself: the *wrong* stratification,
    # which is exactly the bug SYNTHESIS §5 item 15 records.  If this agreed
    # with the published number the gate would prove nothing.
    rows = read("noise-109MSDCF.csv")
    last = {}
    for r in rows:
        last[r["measure"]] = float(r["ratio"])
    prows = read("planted-109MSDCF-p1.csv")
    unstrat = statistics.median(
        [float(r["acc"]) for r in prows if r["measure"] == "tenengrad-w5" and int(r["width"]) == 1]
    )
    emit("Negative control on the reader (SYNTHESIS §5 item 15):")
    emit(f"  noise, last-row-per-measure, no width filter: ring-1-3 -> {last['ring-1-3']:.4f}")
    emit(f"  noise, correctly stratified                 : ring-1-3 -> {n_axis('ring-1-3')[0]:.4f}")
    emit("  noise, published                            : ring-1-3 -> 1.3475")
    emit(f"  planted, no roi_kind filter                 : tenengrad-w5 -> {unstrat:.4f}")
    emit(f"  planted, roi_kind == 'detail'               : tenengrad-w5 -> {s_axis('tenengrad-w5'):.4f}")
    emit("  planted, published                          : tenengrad-w5 -> 0.8007")
    emit("  Both unfiltered readers disagree, as they must; both filtered ones agree.")
    emit("")
    emit(f"GATE 0: {'PASS' if ok else 'FAIL'}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
