"""56-shipped-estar-ladder.py -- does the SHIPPED solver read the bias the same way?

54 established, on an independently re-derived numpy solve, that E* FALLS as a
scale-attenuation bias is planted while the true error explodes. This runs the
same ladder through `m86-align solve-csv` -- the shipped weighting, the shipped
IRLS, the shipped robust reduction, the shipped decision rule, none of which the
numpy solve reproduces -- and reads its printed statistics back.

If the shipped numbers track mine, the finding is about the product's own gate
rather than about my arithmetic. If they diverge, my re-derivation is wrong
about something and I report that instead.

The parse is anchored, not positional: each value is taken from a line matched
by a literal that names it. A positional parse would silently re-point at a
different column if the tool's table ever changed, and would report the new
column with the old label.
"""

import pathlib
import re
import subprocess
import sys

EXE = pathlib.Path(r".cargo-target-defect\release\examples\m86-align.exe")
OUT = pathlib.Path(r"experiments\BUILD-DEFECT\out")
RHOS = (1.000, 0.800, 0.526, 0.300)

# From 54, the numpy re-derivation, for the same rho values.
NUMPY = {1.000: 0.5987, 0.800: 0.5151, 0.526: 0.3837, 0.300: 0.2757}


def run(path):
    r = subprocess.run(
        [str(EXE), "solve-csv", str(path), "--n", "105", "--cfg", "m10"],
        capture_output=True,
    )
    if r.returncode != 0:
        sys.exit(f"solver failed on {path}: {r.stderr.decode('utf-8', 'replace')[:400]}")
    return r.stdout.decode("utf-8", "replace")


def parse(txt, path):
    """Pull the S3-ba-unit row from the 'all measurable' block, plus the ruling."""
    block = txt.split("train = all measurable")
    if len(block) != 2:
        sys.exit(f"{path}: expected exactly one 'all measurable' block, got {len(block) - 1}")
    row = None
    for line in block[1].splitlines():
        if "S3-ba-unit" in line:
            row = line
            break
    if row is None:
        sys.exit(f"{path}: no S3-ba-unit row in the all-measurable block")
    nums = [float(x) for x in re.findall(r"-?\d+\.\d+", row)]
    if len(nums) < 5:
        sys.exit(f"{path}: S3-ba-unit row has {len(nums)} floats, expected >= 5: {row!r}")
    median, p90, mx, scale, trans = nums[:5]
    m = re.search(r"E\* robust \(span >= \d+\)\s*:\s*(\d+\.\d+) px", txt)
    if not m:
        sys.exit(f"{path}: could not find the 'E* robust' ruling line")
    return median, scale, trans, float(m.group(1))


def main():
    if not EXE.exists():
        sys.exit(f"missing {EXE}; build with --example m86-align first")
    print("=" * 78)
    print("56 -- the SHIPPED solver on the same biased ladder")
    print("=" * 78)
    print(
        f"  {'rho':>6} {'E*_med':>9} {'E*_scale':>10} {'E*_trans':>10} "
        f"{'E*_robust':>10} {'numpy':>9} {'|d|':>8}"
    )
    meds, worst = [], 0.0
    for rho in RHOS:
        p = OUT / f"p4-bias-{int(round(rho * 1000)):04d}.csv"
        if not p.exists():
            sys.exit(f"missing {p}; run 55-emit-biased-edges.py first")
        med, scale, trans, robust = parse(run(p), p)
        d = abs(med - NUMPY[rho])
        worst = max(worst, d)
        meds.append((rho, med, robust))
        print(
            f"  {rho:>6.3f} {med:>9.3f} {scale:>10.3f} {trans:>10.3f} "
            f"{robust:>10.3f} {NUMPY[rho]:>9.4f} {d:>8.4f}"
        )

    print(f"\n  worst |shipped - numpy| = {worst:.4f} px")
    if worst > 0.01:
        print("  DIVERGENT: my re-derivation does not reproduce the shipped statistic;")
        print("  54's ladder describes my solver, not the product's gate.")
        return 1
    print("  AGREES (bar 0.01 px): 54's ladder describes the SHIPPED gate.")

    med_mono = all(meds[k][1] > meds[k + 1][1] for k in range(len(meds) - 1))
    rob_mono = all(meds[k][2] > meds[k + 1][2] for k in range(len(meds) - 1))
    print(f"\n  shipped E* median falls monotonically with the bias : {med_mono}")
    print(f"  shipped E* robust falls monotonically with the bias : {rob_mono}")
    if med_mono and rob_mono:
        print("\n  The shipped gate rewards a scale-attenuation defect, on both the")
        print("  median it reports and the robust figure its decision rule uses.")
        return 0
    print("\n  The shipped gate does NOT move monotonically; 54's mechanism does")
    print("  not transfer to the product and the finding is limited to numpy.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
