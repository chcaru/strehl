"""Verify docs/research/V-LINEAR-BANDS.md against the JSON it claims to quote.

WHY THE FIRST VERSION OF THIS FILE WAS WORTHLESS, RECORDED BECAUSE THE FAILURE
IS THE INSTRUCTIVE PART.  It tested `f"{R:.3f}" in whole_document`.  That reads
GREEN for 40/40 claims and STAYS GREEN when a number is corrupted, because each
R appears in up to three tables (sec.3 verdicts, sec.3 CIs, sec.4 ladder) and any
surviving copy satisfies the check.  Measured: mutating the sec.3 cell
`**4.874** PASS` to `**4.875**` left the verifier reading "40 claims verified, 0
missing", exit 0.  Its own docstring claimed it anchored on the subject row; the
code computed that anchor into a variable and then never used it.

So every check below is bound to ONE table row, located by its leading
`| \\`subject\\` |` cell, and a value must appear in THAT row.  A row that cannot
be found is counted as UNRESOLVED and fails the run -- a check that silently
matches nothing must not be readable as a check that passed, so the printed
summary partitions every claim into located-and-correct, located-and-wrong, and
unresolved, which sum to the number attempted.

    python verify_bands_doc.py     # exit 0 = every claim located in its own row
"""
import json
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _HERE)
import bandsweep                                                 # noqa: E402

DOC = os.path.join(_ROOT, "docs", "research", "V-LINEAR-BANDS.md")
BANDS = ["0.17-0.20", "0.20-0.25", "0.25-0.30", "0.30-0.40", "0.40-0.48"]
BAND0 = ["0.25-0.30", "0.30-0.40", "0.40-0.48"]

# Round 2 (sec.9) is stored one file per subject rather than one file for the
# sweep, because those subjects were developed and swept one at a time under a
# disk constraint.  Every `bandsweep-far20*.json` beside this script is loaded,
# so a subject added later is verified without editing this list -- the failure
# mode being avoided is a new table row that no check ever looks at, which is
# the same "silently matches nothing" defect this file was rewritten for.
#
# Two kinds of file are NOT canonical subject records:
#   `simdecim`                     -- the decimation commissioning arm (sec.9.5)
#   `bandsweep-far20-leaf-2-cpl`   -- the sec.6.1 reproduction control, which
#                                     sweeps a subject ALONE to show that
#                                     `bandsignal.py`'s module-level RNG makes
#                                     the CI call-order dependent.  It disagrees
#                                     with the canonical row BY DESIGN.
# Loading that control shadowed the canonical `leaf-2-cpl` record on the first
# run of the glob and reported the document WRONG at 2 checks.  The document was
# right and the loader was wrong.
#
# The collision rule is NOT "first file wins" and NOT "declared controls only".
# It is: AGREEMENT IS NOT AMBIGUITY, DISAGREEMENT IS.  A key in two files whose
# measured values match is harmless and is accepted silently -- that is how
# `bandsweep-far20-noPF.json` is handled, a round-1 robustness arm that repeats
# all five subjects and was MEASURED here to agree to 1e-9 on all 60 of its
# R values.  A key in two files whose values differ is a real ambiguity about
# what the document quotes and is a hard error.  Written this way, a future
# control that happens to disagree cannot slip through by being added to a list.
CONTROLS = ("simdecim", "bandsweep-far20-leaf-2-cpl")


def _payload(r):
    return (r["n_real"], r["step"], r["kept"],
            {b: (v["R"], v["lo"], v["hi"]) for b, v in r["bands"].items()})


def load(pattern, controls):
    recs, src = {}, {}
    for path in sorted(glob.glob(os.path.join(_HERE, pattern))):
        base = os.path.basename(path)
        if any(c in base for c in controls):
            continue
        with open(path) as fh:
            for r in json.load(fh):
                k = r["key"]
                if k in recs:
                    if _payload(recs[k]) != _payload(r):
                        raise SystemExit(
                            f"AMBIGUOUS: subject {k!r} has DIFFERENT values in "
                            f"{src[k]} and {base}; the verifier cannot know "
                            f"which the document quotes. Declare one a control.")
                    continue
                recs[k], src[k] = r, base
    return recs


def rows_for(lines, key):
    """Every table row whose FIRST cell is `key`, in document order."""
    pat = re.compile(r"^\|\s*`" + re.escape(key) + r"`\s*\|")
    return [ln.strip() for ln in lines if pat.match(ln.strip())]


def split_cells(row):
    return [c.strip() for c in row.strip("|").split("|")]


# The document's shorthand for the instrument's verdict strings.
TOKEN = {"PASS": "PASS", "MARGINAL": "MARG", "FAIL(noise)": "FAIL"}


def band0_verdict(rec):
    """sec.10's band-0 conclusion, DERIVED from the three slice verdicts.

    The document states the rule in prose: NOISE means every FINE slice of
    band 0 FAILs; SIGNAL means they all PASS; anything else is mixed.  Deriving
    it here rather than reading it means the CONCLUSION is certified against the
    measurement, not against itself.
    """
    vs = [rec["bands"][b]["verdict"] for b in BAND0]
    if all(v.startswith("FAIL") for v in vs):
        return "NOISE"
    if all(v == "PASS" for v in vs):
        return "SIGNAL"
    return "mixed"


def locate(lines, key):
    """The verdict row and the CI row for `key`, found by SHAPE not by ordinal.

    SECOND DEFECT IN THIS FILE, FOUND THE SAME WAY AS THE FIRST -- BY RUNNING IT.
    The previous version took `rows[0]` and `rows[1]` of every row whose first
    cell is the subject.  That is positional, and it was only ever correct while
    the document had exactly three subject-keyed tables in a fixed order.
    Section 9.1 (a prose "why this subject is here" table) and section 10
    (band-0 verdicts) each add another row keyed by the same subject, so
    `rows[0]` silently became the PROSE row and all 50 checks for round-2
    subjects reported WRONG against a row that was never meant to carry numbers.

    Anchoring on the row's SHAPE fixes the class rather than the instance:

      verdict row : 10 cells, carries a PASS/MARG/FAIL token
      CI row      :  3 cells, carries exactly two `[`
      band-0 row  :  5 cells, carries a NOISE/mixed/SIGNAL token  (sec.10)
      ladder row  :  4 cells, carries a same/MOVED token          (sec.9.4)

    and each must match EXACTLY ONCE.  A shape that matches twice is ambiguous
    and is reported as unresolved rather than resolved to whichever came first,
    because "resolved to the first of several" is how the first defect survived.
    """
    verdict, ci, band0, ladder = [], [], [], []
    for s in rows_for(lines, key):
        cells = split_cells(s)
        if len(cells) == 10 and any(t in s for t in ("PASS", "MARG", "FAIL")):
            verdict.append(cells)
        elif len(cells) == 3 and s.count("[") == 2:
            ci.append(cells)
        elif len(cells) == 5 and any(t in s for t in ("NOISE", "mixed", "SIGNAL")):
            band0.append(cells)
        elif len(cells) == 4 and any(t in s for t in ("same", "MOVED")):
            ladder.append(cells)
    return verdict, ci, band0, ladder


def main():
    lines = open(DOC, encoding="utf-8").read().splitlines()
    recs = load("bandsweep-far20*.json", CONTROLS)
    far8 = load("bandsweep-far8*.json", CONTROLS)

    ok = bad = unresolved = 0
    ladder_rows = band0_rows = ladder_same = 0

    def check(desc, cell, needle):
        """`needle` must be in THIS CELL, not merely somewhere in the row.

        Row-wide `in` was the surviving remnant of the presence-test defect:
        an R quoted in the wrong band's cell, or a verdict token belonging to a
        neighbouring band, satisfied it.  A cell is the smallest unit that
        carries one claim, so it is the unit a check is pinned to.
        """
        nonlocal ok, bad
        if needle in cell:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      {desc}: expected {needle!r}, cell reads {cell!r}")

    for key, r in sorted(recs.items()):
        vrows, crows, brows, lrows = locate(lines, key)
        if len(vrows) != 1 or len(crows) != 1:
            unresolved += 11
            print(f"  UNRESOLVED {key}: need exactly 1 verdict row and 1 CI row, "
                  f"found {len(vrows)} and {len(crows)}")
            continue
        v, c = vrows[0], crows[0]

        check(f"{key} n_real", v[1], str(r["n_real"]))
        check(f"{key} step", v[2], str(r["step"]))
        check(f"{key} kept", v[3], str(r["kept"]))

        for j, b in enumerate(BANDS):
            cell, rec_b = v[4 + j], r["bands"][b]
            check(f"{key} {b} R", cell, f"{rec_b['R']:.3f}")
            # THE CONCLUSION, not the evidence.  A flipped verdict with an
            # intact number is the mutation that passed 712 green checks in
            # another lane; it is caught here because the token is derived
            # from the instrument's own verdict string.
            check(f"{key} {b} verdict", cell, TOKEN[rec_b["verdict"]])

        # THE HEADLINE.  The boundary is the single value other lanes act on,
        # and it is recomputed by the instrument that produced the record
        # rather than read back out of the document.
        check(f"{key} BOUNDARY", v[9], f"{bandsweep.boundary(r):.2f}")

        for j, b in enumerate(("0.17-0.20", "0.20-0.25")):
            rec_b = r["bands"][b]
            check(f"{key} {b} R+CI", c[1 + j],
                  f"{rec_b['R']:.3f} [{rec_b['lo']:.3f}, {rec_b['hi']:.3f}]")

        # sec.10 band-0 verdict (all eleven subjects).
        if len(brows) == 1:
            band0_rows += 1
            b0 = brows[0]
            for j, b in enumerate(BAND0):
                check(f"{key} band0 {b} R", b0[1 + j],
                      f"{r['bands'][b]['R']:.3f}")
            check(f"{key} BAND-0 VERDICT", b0[4], band0_verdict(r))
        elif len(brows) > 1:
            unresolved += 1
            print(f"  UNRESOLVED {key}: {len(brows)} band-0 rows")

        # sec.9.4 far ladder (round-2 subjects only; round 1's ladder is a
        # differently-shaped table in sec.4 and is NOT re-checked here -- that
        # is declared, not silent, and is asserted by the count below).
        if len(lrows) == 1:
            ladder_rows += 1
            L, r8 = lrows[0], far8.get(key)
            if r8 is None:
                unresolved += 1
                print(f"  UNRESOLVED {key}: ladder row with no far=8 record")
            else:
                b20, b8 = bandsweep.boundary(r), bandsweep.boundary(r8)
                check(f"{key} ladder far20", L[1], f"{b20:.2f}")
                check(f"{key} ladder far8", L[2], f"{b8:.2f}")
                check(f"{key} LADDER VERDICT", L[3],
                      "same" if b20 == b8 else "MOVED")
                if L[3] == "same":
                    ladder_same += 1
        elif len(lrows) > 1:
            unresolved += 1
            print(f"  UNRESOLVED {key}: {len(lrows)} ladder rows")

    # A check that matches nothing prints the same green as one that matches.
    # These counts are what make the derived tables non-vacuous.
    #
    # The ladder count is pinned to the DOCUMENT'S OWN SUMMARY CLAIM ("6/6
    # unchanged") rather than to a magic number or to len(far8).  len(far8) is
    # 11 because round 1 also has far=8 records, but round 1's ladder lives in
    # sec.4 in a differently-shaped six-cell table and is NOT re-checked here.
    # Pinning to the claim means the summary line cannot drift away from the
    # rows it summarises, which is the same failure the conclusion checks above
    # exist for.
    # The claim is now quoted in more than one place (sec.9.4 states it, sec.12
    # discusses it), so taking the FIRST match would be the same positional
    # mistake that produced defect 2. Every occurrence is collected and they
    # must AGREE -- the same rule the loader uses for duplicate records.
    claims = set(re.findall(r"\*\*(\d+)/(\d+) unchanged\*\*", "\n".join(lines)))
    if len(claims) != 1:
        bad += 1
        print(f"  WRONG      sec.9.4 summary claim: found {len(claims)} "
              f"distinct '**N/N unchanged**' claims {sorted(claims)}; "
              "they must agree or the document contradicts itself")
    else:
        n_same, n_tot = (int(x) for x in claims.pop())
        for label, got, want in (("ladder rows vs claimed denominator",
                                  ladder_rows, n_tot),
                                 ("ladder rows reading 'same' vs claimed",
                                  ladder_same, n_same)):
            if got == want:
                ok += 1
            else:
                bad += 1
                print(f"  WRONG      {label}: found {got}, claimed {want}")

    if band0_rows == len(recs):
        ok += 1
    else:
        bad += 1
        print(f"  WRONG      band-0 rows: found {band0_rows}, "
              f"expected {len(recs)}")

    attempted = ok + bad + unresolved
    print(f"\n  located-and-correct : {ok}")
    print(f"  located-and-WRONG   : {bad}")
    print(f"  unresolved          : {unresolved}")
    print(f"  ------------------------------")
    print(f"  attempted           : {attempted}   over {len(recs)} subjects "
          f"({band0_rows} band-0 rows, {ladder_rows} ladder rows)")
    return 1 if (bad or unresolved) else 0


if __name__ == "__main__":
    sys.exit(main())
