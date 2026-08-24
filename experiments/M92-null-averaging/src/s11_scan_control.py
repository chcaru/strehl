"""M92b S11 -- the falsifying control for the S10 scanner.

A check that has never been made to fail is not a check.  S10 reported ten
per-stack MISMATCHes; before any of them is believed, the scanner has to be
shown to (a) catch a planted defect it has never seen, and (b) NOT fire on a
planted correct file.  Both directions matter: a scanner that flags everything
is as useless as one that flags nothing, and S10's first two revisions did
exactly those two things (0 instances from a wrong root; false MISMATCHes from
counting stack names inside docstrings).

Six fixtures are written to a scratch directory and scanned with the same
`scan_file` / `path_literals` / `classify` the real run uses -- not a
reimplementation, which would prove nothing about the real scanner.

  F1  plain wrong ISO on a named stack          -> must be MISMATCH
  F2  correct ISO on a named stack              -> must be MATCH
  F3  wrong ISO hidden in TUPLE UNPACKING       -> must be MISMATCH
      (this is m57's s7 shape; the pre-fix scanner missed it entirely)
  F4  stack named only in a DOCSTRING           -> must be UNRESOLVED
      (this is m61's shape; the pre-fix scanner called it MISMATCH)
  F5  wrong read noise branch at ISO 100        -> must be MISMATCH
  F6  no sensor constant at all                 -> must yield no hits

Run:
  python experiments/M92-null-averaging/src/s11_scan_control.py
"""
import ast
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402
import s10_const_scan as S10  # noqa: E402

SCRATCH = os.path.join(M92.OUT, "s11_fixtures")

F1 = '''
import os
ISO = 500
p = os.path.join(r"D:\\personal\\macro", "109MSDCF")
'''

F2 = '''
import os
ISO = 160
p = os.path.join(r"D:\\personal\\macro", "109MSDCF")
'''

F3 = '''
import os
PAD, G, RN_E, ISO = 32, 1.14469, 1.47, 500
p = os.path.join(r"D:\\personal\\macro", "109MSDCF")
'''

F4 = '''
"""A synthetic plant emulating the ISO-1000 regime of foam."""
RN_E = 4.20
'''

F5 = '''
import os
RN_E = 1.2392
p = os.path.join(r"D:\\personal\\macro", "bee-3-cpl")
'''

F6 = '''
import os
WINDOW = 512
p = os.path.join(r"D:\\personal\\macro", "109MSDCF")
'''

FIXTURES = [
    ("F1_plain_wrong_iso", F1, "MISMATCH", "ISO"),
    ("F2_plain_right_iso", F2, "MATCH", "ISO"),
    ("F3_tuple_wrong_iso", F3, "MISMATCH", "ISO"),
    ("F4_docstring_only", F4, "UNRESOLVED", "RN_E"),
    ("F5_wrong_rn_branch", F5, "MISMATCH", "RN_E"),
    ("F6_no_constant", F6, None, None),
]


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log("M92b S11 -- falsifying control for the S10 constant scanner")
    log("=" * 78)

    by_name, _ = S10.load_truth()
    names = sorted(by_name, key=len, reverse=True)

    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(SCRATCH)

    rows, ok = [], True
    for nm, body, want, want_const in FIXTURES:
        p = os.path.join(SCRATCH, nm + ".py")
        open(p, "w", encoding="utf-8").write(body.lstrip())
        hits = S10.scan_file(p)
        lits = S10.path_literals(ast.parse(body.lstrip()))
        used = [s for s in names if s in lits]
        used = [s for s in used if not any(s != o and s in o for o in used)]

        if want is None:
            got = None if not hits else "HITS"
            good = not hits
        else:
            sel = [h for h in hits if h["name"] == want_const]
            if not sel:
                got, good = "NO-HIT", False
            else:
                r = dict(file=nm, stacks=used, **sel[0])
                got, _why = S10.classify(r, by_name)
                good = (got == want)
        ok &= good
        rows.append(dict(fixture=nm, want=want, got=got, passed=good))
        log(f"  {'PASS' if good else 'FAIL'}  {nm:22s} "
            f"want={str(want):11s} got={str(got)}")

    log("")
    log("  Interpretation of the two shape fixtures:")
    log("    F3 is m57 s7's literal shape. A scanner that only handles")
    log("       `Name = value` reports 0 hits here and silently under-counts")
    log("       the very defect this audit is about.")
    log("    F4 is m61 03-power-control's shape. A scanner that counts stack")
    log("       names inside docstrings reports MISMATCH on a pure synthetic")
    log("       plant that never opens the stack.")
    log("")
    log(f"  CONTROL {'PASSED' if ok else 'FAILED'} "
        f"({sum(r['passed'] for r in rows)}/{len(rows)} fixtures)")

    M92_json = os.path.join(M92.OUT, "s11_scan_control.json")
    with open(M92_json, "w", encoding="utf-8") as fh:
        json.dump(dict(fixtures=rows, passed=bool(ok)), fh, indent=1)
    with open(os.path.join(M92.OUT, "s11_scan_control.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log("wrote out/s11_scan_control.{json,log}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
