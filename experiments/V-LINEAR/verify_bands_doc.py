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
DOC = os.path.join(_ROOT, "docs", "research", "V-LINEAR-BANDS.md")
JSON = os.path.join(_HERE, "bandsweep-far20.json")
BANDS = ["0.17-0.20", "0.20-0.25", "0.25-0.30", "0.30-0.40", "0.40-0.48"]

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


def load_all():
    recs, src = {}, {}
    for path in sorted(glob.glob(os.path.join(_HERE, "bandsweep-far20*.json"))):
        base = os.path.basename(path)
        if any(c in base for c in CONTROLS):
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

    and each must match EXACTLY ONCE.  A shape that matches twice is ambiguous
    and is reported as unresolved rather than resolved to whichever came first,
    because "resolved to the first of several" is how the first defect survived.
    """
    verdict, ci = [], []
    for s in rows_for(lines, key):
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) == 10 and any(t in s for t in ("PASS", "MARG", "FAIL")):
            verdict.append(s)
        elif len(cells) == 3 and s.count("[") == 2:
            ci.append(s)
    return verdict, ci


def main():
    lines = open(DOC, encoding="utf-8").read().splitlines()
    recs = load_all()

    ok = bad = unresolved = 0

    def check(desc, hay, needle):
        nonlocal ok, bad
        if needle in hay:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      {desc}: expected {needle!r} in its own row")

    for key, r in sorted(recs.items()):
        verdict_rows, ci_rows = locate(lines, key)
        if len(verdict_rows) != 1 or len(ci_rows) != 1:
            unresolved += 8
            print(f"  UNRESOLVED {key}: need exactly 1 verdict row and 1 CI row, "
                  f"found {len(verdict_rows)} and {len(ci_rows)}")
            continue
        verdict_row, ci_row = verdict_rows[0], ci_rows[0]

        check(f"{key} N/step/kept", verdict_row,
              f"| {r['n_real']} | {r['step']} | {r['kept']} |")
        for b in BANDS:
            check(f"{key} {b} R", verdict_row, f"{r['bands'][b]['R']:.3f}")
        for b in ("0.17-0.20", "0.20-0.25"):
            v = r["bands"][b]
            check(f"{key} {b} R+CI", ci_row,
                  f"{v['R']:.3f} [{v['lo']:.3f}, {v['hi']:.3f}]")

    attempted = ok + bad + unresolved
    print(f"\n  located-and-correct : {ok}")
    print(f"  located-and-WRONG   : {bad}")
    print(f"  unresolved          : {unresolved}")
    print(f"  ------------------------------")
    print(f"  attempted           : {attempted}   over {len(recs)} subjects")
    return 1 if (bad or unresolved) else 0


if __name__ == "__main__":
    sys.exit(main())
