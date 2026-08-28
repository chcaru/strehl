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
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
DOC = os.path.join(_ROOT, "docs", "research", "V-LINEAR-BANDS.md")
JSON = os.path.join(_HERE, "bandsweep-far20.json")
BANDS = ["0.17-0.20", "0.20-0.25", "0.25-0.30", "0.30-0.40", "0.40-0.48"]


def rows_for(lines, key):
    """Every table row whose FIRST cell is `key`, in document order."""
    pat = re.compile(r"^\|\s*`" + re.escape(key) + r"`\s*\|")
    return [ln for ln in lines if pat.match(ln.strip())]


def main():
    lines = open(DOC, encoding="utf-8").read().splitlines()
    with open(JSON) as fh:
        recs = {r["key"]: r for r in json.load(fh)}

    ok = bad = unresolved = 0

    def check(desc, hay, needle):
        nonlocal ok, bad
        if needle in hay:
            ok += 1
        else:
            bad += 1
            print(f"  WRONG      {desc}: expected {needle!r} in its own row")

    for key, r in recs.items():
        rows = rows_for(lines, key)
        if len(rows) < 3:
            unresolved += 8
            print(f"  UNRESOLVED {key}: expected 3 table rows "
                  f"(verdicts, CIs, ladder), found {len(rows)}")
            continue
        verdict_row, ci_row = rows[0], rows[1]

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
