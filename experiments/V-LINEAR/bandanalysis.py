"""Derived tables for docs/research/V-LINEAR-BANDS.md.

`bandsweep.py` measures; this file only re-derives, from the saved JSON, the
four cross-subject tables the document quotes.  It reads no image data, so it
is cheap to re-run and cannot silently disagree with the measurement.

    python bandanalysis.py

Sections mirror the document:
  sec.4    the far ladder and boundary invariance
  sec.5.1  stack depth
  sec.5.3  fine-structure covariate f2c
  sec.5.4  the two terms of R, normalised
  sec.6.1  reproducibility and RNG call-order dependence
"""
import itertools
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import bandsweep                                                 # noqa: E402

RUNGS = [("far=8", "bandsweep-far8.json"),
         ("far=20", "bandsweep-far20.json"),
         ("far=auto", "bandsweep.json")]
MAIN = "bandsweep-far20.json"
COARSE = "0.05-0.08"          # normaliser: per-subject coarse in-focus power
FINEB = "0.30-0.40"           # the band the covariates are read at


def load(name):
    with open(os.path.join(_HERE, name)) as fh:
        return {r["key"]: r for r in json.load(fh)}


def concordance(rows, idx, bnd):
    """Fraction of subject PAIRS a covariate orders the same way as boundary.

    Reported as pairs rather than as a correlation because five points cannot
    support a correlation coefficient, and because ties on boundary must be
    visible rather than absorbed into a statistic.
    """
    pairs = list(itertools.combinations(rows, 2))
    conc = sum(1 for a, b in pairs if (a[idx] - b[idx]) * (bnd[a[0]] - bnd[b[0]]) > 0)
    tied = sum(1 for a, b in pairs if bnd[a[0]] == bnd[b[0]])
    return conc, len(pairs), tied


def main():
    main_recs = load(MAIN)
    keys = list(main_recs)
    bnd = {k: bandsweep.boundary(main_recs[k]) for k in keys}

    print("=" * 92)
    print("sec.4  FAR LADDER -- is the boundary a property of the subject or of my parameter?")
    print("=" * 92)
    data = {t: load(p) for t, p in RUNGS}
    print(f"{'subject':22} {'R far=8':>10} {'R far=20':>10} {'R auto':>10} "
          f"{'span':>7}   boundary 8/20/auto")
    same = True
    for k in keys:
        rs = [data[t][k]["bands"]["0.17-0.20"]["R"] for t, _ in RUNGS]
        bs = [bandsweep.boundary(data[t][k]) for t, _ in RUNGS]
        same &= len(set(bs)) == 1
        print(f"{k:22} {rs[0]:10.3f} {rs[1]:10.3f} {rs[2]:10.3f} "
              f"{max(rs) / min(rs):6.2f}x   " + " / ".join(f"{b:.2f}" for b in bs))
    print(f"\n  BOUNDARY INVARIANT TO far ON EVERY SUBJECT: {same}")
    print("  -> the spread is the subjects, not the parameter" if same else
          "  -> THE SPREAD IS THE PARAMETER; the table is an artifact")

    print("\n" + "=" * 92)
    print("sec.5.1  STACK DEPTH")
    print("=" * 92)
    for k in sorted(keys, key=lambda k: main_recs[k]["n_real"]):
        print(f"  N={main_recs[k]['n_real']:4d}   boundary={bnd[k]:.2f}   {k}")
    ordered = [bnd[k] for k in sorted(keys, key=lambda k: main_recs[k]["n_real"])]
    mono = all(a <= b for a, b in zip(ordered, ordered[1:])) or \
        all(a >= b for a, b in zip(ordered, ordered[1:]))
    print(f"\n  monotone in depth: {mono}   -> "
          f"{'depth is a candidate' if mono else 'REJECTED as an explanation'}")

    rows_f2c, rows_num, rows_den = [], [], []
    for k in keys:
        c = main_recs[k]["bands"][COARSE]["pf"]
        pf = main_recs[k]["bands"][FINEB]["pf"]
        pd = main_recs[k]["bands"][FINEB]["pd"]
        rows_f2c.append((k, pf / c))
        rows_num.append((k, pf / c))
        rows_den.append((k, pd / c))

    print("\n" + "=" * 92)
    print("sec.5.3 / 5.4  SUBJECT COVARIATES, both normalised by the same")
    print(f"               per-subject coarse in-focus power pf({COARSE}),")
    print("               so exposure and scene brightness divide out.")
    print("=" * 92)
    print(f"{'subject':22} {'boundary':>9} {'num pf/pfc':>12} {'den pd/pfc':>12} "
          f"{'R':>9}")
    for k in sorted(keys, key=lambda k: -bnd[k]):
        c = main_recs[k]["bands"][COARSE]["pf"]
        b = main_recs[k]["bands"][FINEB]
        print(f"{k:22} {bnd[k]:9.2f} {b['pf'] / c:12.5g} {b['pd'] / c:12.5g} "
              f"{b['R']:9.3f}")

    for label, rows in (("fine-structure f2c (sec.5.3)", rows_f2c),
                        ("numerator  pf/pfc (sec.5.4)", rows_num),
                        ("denominator pd/pfc (sec.5.4)", rows_den)):
        conc, tot, tied = concordance(rows, 1, bnd)
        print(f"\n  {label:32} concordant with boundary: {conc}/{tot} "
              f"({tied} pair tied on boundary)")
        print(f"  {'':32} -> "
              + ("ORDERS the boundary" if conc >= tot - tied - 1
                 else "does NOT order the boundary (chance)"))

    srt = sorted(rows_den, key=lambda t: t[1])
    srtn = sorted(rows_num, key=lambda t: t[1])
    print(f"\n  outlier check on {srt[0][0]}:")
    print(f"    numerator   {srtn[0][1]:.5g}  vs next-lowest {srtn[1][1]:.5g}"
          f"   -> {srtn[1][1] / srtn[0][1]:.2f}x")
    print(f"    denominator {srt[0][1]:.5g}  vs next-lowest {srt[1][1]:.5g}"
          f"   -> {srt[1][1] / srt[0][1]:.2f}x")
    print("    -> denominator anomaly is "
          f"{(srt[1][1] / srt[0][1]) / (srtn[1][1] / srtn[0][1]):.2f}x the "
          "numerator anomaly")

    print("\n" + "=" * 92)
    print("sec.6.1  REPRODUCIBILITY.  bandsignal.RNG is module-level, stateful,")
    print("         seeded once -- so R reproduces exactly but a CI depends on")
    print("         how many subjects were swept before it.")
    print("=" * 92)
    solo = os.path.join(_HERE, "bandsweep-far20-leaf-2-cpl.json")
    if not os.path.exists(solo):
        print("  (single-subject control file absent; re-create with")
        print("   `python bandsweep.py --far 20 leaf-2-cpl`)")
        return 0
    with open(solo) as fh:
        s = {r["key"]: r for r in json.load(fh)}["leaf-2-cpl"]
    f = main_recs["leaf-2-cpl"]
    dR = max(abs(s["bands"][b]["R"] - f["bands"][b]["R"]) for b in s["bands"])
    moved = [b for b in s["bands"]
             if abs(s["bands"][b]["lo"] - f["bands"][b]["lo"]) > 1e-12]
    vs = all(s["bands"][b]["verdict"] == f["bands"][b]["verdict"] for b in s["bands"])
    print(f"  leaf-2-cpl swept ALONE vs swept as one of {len(keys)}:")
    print(f"    worst |dR| over {len(s['bands'])} bands : {dR:.3e}   (expect 0)")
    print(f"    bands with a moved CI low  : {len(moved)}/{len(s['bands'])}")
    print(f"    verdicts identical         : {vs}")

    # A WORST-CASE JITTER TAKEN ACROSS ALL BANDS IS THE WRONG STATISTIC AND
    # SAYS THE WRONG THING.  Coarse bands have CI lows of order 10-80, so their
    # absolute jitter is large in absolute terms and irrelevant to a 1.5
    # threshold that only fine bands come near.  Comparing that worst-case
    # against a fine band's margin manufactures a false alarm.  Each band is
    # therefore compared against ITS OWN jitter.
    print("\n    per-band, near-threshold cells only (CI low within 1.0 of the "
          "1.5 bar):")
    print(f"      {'band':>10} {'CI low':>9} {'margin':>9} {'own jitter':>11} "
          f"{'margin/jitter':>14}  safe")
    risk = 0
    for b in sorted(f["bands"], key=lambda b: f["bands"][b]["f_lo"]):
        lo = f["bands"][b]["lo"]
        if abs(lo - 1.5) > 1.0:
            continue
        j = abs(s["bands"][b]["lo"] - lo)
        m = abs(lo - 1.5)
        ok = j == 0 or m / j >= 10
        risk += not ok
        r = f"{m / j:14.1f}" if j else f"{'inf':>14}"
        print(f"      {b:>10} {lo:9.4f} {m:9.4f} {j:11.6f} {r}  "
              f"{'yes' if ok else 'NO'}")
    print(f"\n    cells whose verdict is within 10x the jitter of flipping: "
          f"{risk}")
    return 1 if risk else 0


if __name__ == "__main__":
    sys.exit(main())
