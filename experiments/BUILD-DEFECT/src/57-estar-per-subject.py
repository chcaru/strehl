"""57-estar-per-subject.py -- E* per subject, and the bias response on REAL edges.

TWO QUESTIONS
=============
1. E* is quoted as a single number -- "6.76 px held-out" -- and used as a gate.
   It is a per-subject quantity. This reports it per subject, and counts the
   subjects for which it CANNOT BE COMPUTED AT ALL, which is a distinct outcome
   from "computed and small" and must not be allowed to look like one.

2. 54 and 56 planted the scale-attenuation bias on the SYNTHETIC P4 case,
   because only there is truth known. A reader may reasonably object that the
   perversity is an artefact of a synthesised stack. So the same bias is
   planted here on REAL measured edges from real subjects. Truth is unknown
   there, so this cannot show E_true rising -- the algebra and P4 do that --
   but it can show whether the shipped gate still moves the WRONG WAY on real
   data, which is the part that decides whether the gate is safe to use.

PARTITION
---------
Every subject is placed in exactly one counted outcome and the outcomes sum to
the number of subjects examined. A subject whose E* is undefined is reported as
UNDEFINED, never as a blank or a zero.
"""

import csv
import pathlib
import re
import subprocess
import sys

import numpy as np

EXE = pathlib.Path(r".cargo-target-defect\release\examples\m86-align.exe")
OUT = pathlib.Path(r"experiments\BUILD-DEFECT\out")
D10 = pathlib.Path(r"experiments\m10-deep-align\data")
D23 = pathlib.Path(r"experiments\m23-metacal\data")

MIN_SPAN, MIN_USED = 40, 12

SUBJECTS = [
    ("coffee-bean", D10 / "coffee-bean-edges.csv", "m10"),
    ("stack-112", D23 / "m12-stack-112-edges.csv", "m10"),
    ("p4-warp (synthetic)", D10 / "p4-warp-edges.csv", "m10"),
    ("coffee-bean-m6", D10 / "coffee-bean-m6-edges.csv", "m3"),
    ("shallow-119", D10 / "shallow-119-edges.csv", "m10"),
    ("shallow-109", D10 / "shallow-109-edges.csv", "m10"),
]

RHOS = (1.000, 0.526)


def read(path, cfg):
    rows = [r for r in csv.DictReader(open(path, newline="")) if r["cfg"] == cfg]
    return rows


def stats(rows):
    ok = [r for r in rows if r["status"] == "ok"]
    n = max(int(r["mov"]) for r in rows) + 1
    test = [r for r in ok if int(r["span"]) >= MIN_SPAN and int(r["used"]) >= MIN_USED]
    return n, len(rows), len(ok), len(test)


def biased_copy(rows, rho, path):
    """Attenuate the log-scale increment on every row that carries one.

    Rows with `status != ok` carry empty numeric fields -- they are refusals,
    not measurements -- so they are passed through untouched. They are COUNTED
    rather than silently skipped: a table where the transform reached nothing
    must not look like one where it reached everything.
    """
    touched = passed = 0
    for r in rows:
        if r["status"] != "ok" or r["g"] == "" or r["rot"] == "":
            passed += 1
            continue
        a = complex(1.0 + float(r["g"]), float(r["rot"]))
        b = complex(np.exp(rho * np.log(a)))
        r["g"] = f"{b.real - 1.0:.9f}"
        r["rot"] = f"{b.imag:.9f}"
        touched += 1
    if touched + passed != len(rows):
        sys.exit("row partition does not sum to the table size")
    if touched == 0:
        sys.exit(f"{path}: the bias reached no row; the arm would be a silent no-op")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path, touched, passed


def run_estar(path, n, cfg):
    r = subprocess.run(
        [str(EXE), "solve-csv", str(path), "--n", str(n), "--cfg", cfg],
        capture_output=True,
    )
    txt = r.stdout.decode("utf-8", "replace")
    if r.returncode != 0:
        return None, r.stderr.decode("utf-8", "replace").strip().splitlines()[-1:]
    m = re.search(r"E\* robust \(span >= \d+\)\s*:\s*(\d+\.\d+) px", txt)
    if not m:
        return None, ["no E* robust line in output"]
    return float(m.group(1)), []


def main():
    if not EXE.exists():
        sys.exit(f"missing {EXE}")
    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 84)
    print("57 -- E* PER SUBJECT (it is quoted as one number; it is not one number)")
    print("=" * 84)
    print(f"  {'subject':<22} {'frames':>7} {'ok':>6} {'test':>6} {'E* robust':>12}")

    counted = {"computed": 0, "undefined_no_test": 0, "solver_refused": 0}
    vals = []
    for name, path, cfg in SUBJECTS:
        rows = read(path, cfg)
        if not rows:
            counted["solver_refused"] += 1
            print(f"  {name:<22} {'-':>7} {'-':>6} {'-':>6} {'NO ROWS':>12}")
            continue
        n, tot, ok, ntest = stats(rows)
        if ntest == 0:
            counted["undefined_no_test"] += 1
            print(
                f"  {name:<22} {n:>7} {ok:>6} {ntest:>6} {'UNDEFINED':>12}"
                f"   <- no edge reaches span {MIN_SPAN}"
            )
            continue
        es, why = run_estar(path, n, cfg)
        if es is None:
            counted["solver_refused"] += 1
            print(f"  {name:<22} {n:>7} {ok:>6} {ntest:>6} {'REFUSED':>12}  {why}")
            continue
        counted["computed"] += 1
        vals.append((name, n, es))
        print(f"  {name:<22} {n:>7} {ok:>6} {ntest:>6} {es:>12.3f}")

    tot = sum(counted.values())
    print(f"\n  partition: {tot} subjects examined = ", end="")
    print(" + ".join(f"{v} {k}" for k, v in counted.items()))
    assert tot == len(SUBJECTS), "partition does not account for every subject"

    if len(vals) >= 2:
        lo = min(vals, key=lambda v: v[2])
        hi = max(vals, key=lambda v: v[2])
        print(f"\n  spread: {lo[2]:.3f} px ({lo[0]}) .. {hi[2]:.3f} px ({hi[0]})")
        print(f"          = {hi[2] / lo[2]:.2f}x across subjects")
        dep = np.array([v[1] for v in vals], dtype=float)
        ev = np.array([v[2] for v in vals], dtype=float)
        if len(set(dep)) > 1:
            r = float(np.corrcoef(dep, ev)[0, 1])
            print(f"  correlation of E* with stack depth: r = {r:+.3f}")
            print(
                "  -> depth "
                + ("does NOT explain" if abs(r) < 0.7 else "largely explains")
                + " the spread; a pooled number hides subject-to-subject variation"
            )

    print("\n" + "=" * 84)
    print("THE BIAS RESPONSE ON REAL EDGES (not synthesised)")
    print("=" * 84)
    print("  Truth is unknown on real subjects, so this shows only the direction")
    print("  E* moves. P4 and the algebra supply the true error.")
    print(f"  {'subject':<22} {'E* rho=1.000':>14} {'E* rho=0.526':>14} {'move':>10} {'rows biased':>13}")
    worse_reads_better = 0
    tested = 0
    for name, path, cfg in SUBJECTS:
        rows = read(path, cfg)
        if not rows:
            continue
        n, _, _, ntest = stats(rows)
        if ntest == 0:
            continue
        got, nb = {}, 0
        for rho in RHOS:
            tag = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            p, nb, npass = biased_copy(
                read(path, cfg), rho, OUT / f"sub-{tag}-{int(rho * 1000):04d}.csv"
            )
            es, _ = run_estar(p, n, cfg)
            got[rho] = es
        if got[1.0] is None or got[0.526] is None:
            continue
        tested += 1
        mv = 100 * (got[0.526] / got[1.0] - 1)
        if mv < 0:
            worse_reads_better += 1
        print(
            f"  {name:<22} {got[1.0]:>14.3f} {got[0.526]:>14.3f} {mv:>9.1f}% {nb:>13}"
        )

    print(f"\n  subjects where a WORSE estimator read BETTER: {worse_reads_better} of {tested}")
    if tested and worse_reads_better == tested:
        print("\n  The perversity is not an artefact of the synthetic case. On every")
        print("  real subject with a computable E*, attenuating the scale response")
        print("  by M23's own measured factor makes the gate read BETTER.")
        return 0
    if tested == 0:
        print("\n  No subject had a computable E*; nothing was established here.")
        return 1
    print("\n  Mixed result: the direction is not universal. Reporting as such.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
