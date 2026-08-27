"""55-emit-biased-edges.py -- write P4 edge CSVs with a known log-scale bias.

WHY THIS EXISTS
===============
`54-estar-tightness.py` shows, on an independently re-derived solver, that E*
FALLS when a scale-attenuation bias is planted while the true error explodes.
That is a statement about my re-derivation. The claim that matters is about the
SHIPPED statistic, computed by the shipped code.

So this writes the biased edge tables to disk in the exact schema
`m86-align solve-csv` reads, and that Rust tool -- with the shipped weighting,
the shipped IRLS, the shipped robust reduction, none of which my numpy solve
reproduces -- is then run on them. If the shipped E* also falls, the finding is
about the product and not about my arithmetic.

Nothing under `crates/` is touched. This only writes CSVs under
`experiments/BUILD-DEFECT/out/`.

THE BIAS
--------
`a -> a**rho` in the complex plane, i.e. the LOG-scale increment is attenuated
by `rho`. M23 defines its response on log-scale, so this is the faithful model
of "the estimator under-reads the increment", not a linear scaling of `g`.
Only the `a` (scale/rotation) part is touched; `ax`/`ay` are copied through
unchanged, which makes the translation columns an internal null: any movement
in the translation part of the result cannot have come from this transform.
"""

import csv
import pathlib
import sys

import numpy as np

SRC = pathlib.Path(r"experiments\m10-deep-align\data\p4-warp-edges.csv")
DST = pathlib.Path(r"experiments\BUILD-DEFECT\out")


def name_for(rho):
    """Build the filename from the rho token alone.

    An earlier version did `f"p4-bias-{rho:.3f}.csv".replace("0.", "0p")`, which
    also rewrote the `0.` inside `.000.csv` and produced `p4-bias-1.000pcsv`.
    Formatting the integer thousandths cannot collide with the extension.
    """
    return f"p4-bias-{int(round(rho * 1000)):04d}.csv"


def emit(rho):
    out = DST / name_for(rho)
    with open(SRC, newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys())
    touched = 0
    for r in rows:
        a = complex(1.0 + float(r["g"]), float(r["rot"]))
        b = complex(np.exp(rho * np.log(a)))
        r["g"] = f"{b.real - 1.0:.9f}"
        r["rot"] = f"{b.imag:.9f}"
        touched += 1
    if touched != len(rows):
        sys.exit("not every row was transformed; refusing to emit a partial table")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"  rho {rho:.3f} -> {out}  ({touched} rows transformed)")
    return out


def main():
    DST.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        sys.exit(f"missing source edge table: {SRC}")
    print("emitting biased P4 edge tables for the SHIPPED solver to read")
    for rho in (1.000, 0.800, 0.526, 0.300):
        emit(rho)
    # rho = 1.000 is the identity arm and must reproduce the source exactly in
    # the columns it claims not to change; if it does not, the harness itself
    # is altering data and no downstream comparison is attributable.
    a = list(csv.DictReader(open(SRC, newline="")))
    b = list(csv.DictReader(open(DST / name_for(1.0), newline="")))
    bad = sum(
        1
        for x, y in zip(a, b)
        if x["ax"] != y["ax"] or x["ay"] != y["ay"] or x["used"] != y["used"]
    )
    drift = max(abs(float(x["g"]) - float(y["g"])) for x, y in zip(a, b))
    print(f"\n  identity check: {bad} untouched-column mismatches (must be 0)")
    print(f"  identity check: max |dg| at rho=1 = {drift:.3e} (must be ~0)")
    if bad or drift > 1e-9:
        sys.exit("the emitter perturbs data it claims to pass through")
    print("  emitter is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
