"""Append facts 1945-1948 to the SYNTHESIS fact table.

1945-1947 fold BUILD-GATE-PRINT's local F6/F7, F19 and F13 (report at
docs/research/BUILD-GATE-PRINT.md, committed 952115c4). 1948 is the
orchestrator's own measurement of the print gate over the full 33.
"""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1944

ROWS = [
    (1945, "BUILD-GATE-PRINT", "MEASURED", (
        "The red byte-freeze row was one constant, `eps_r`, and nothing else -- attributed "
        "bit-exactly in both directions. Reverting that single constant reproduces the "
        "superseded hash bit-for-bit, and restoring it reproduces the new one, while the "
        "paired control row `coffee-bean-20-gate2-unaligned` is invariant under both values. "
        "Both directions matter: reproducing the old hash shows the constant is sufficient to "
        "explain the change, and the invariant control shows it is not merely correlated with "
        "it. The row was re-baselined with its `why` column rewritten rather than silently "
        "re-frozen. Note the commission's premise was wrong on the way in -- it stated "
        "`OpticalProfile::compose` has exactly two live call sites; a `git grep` census found "
        "three, the third being a cargo example target not linked into `strehl`. The "
        "conclusion survived; the census did not."
    )),
    (1946, "BUILD-GATE-PRINT", "MEASURED", (
        "A commissioning plant large enough to move one statistic decisively may also move a "
        "second, and then `the verdict did not move` proves nothing about whether the second "
        "statistic is gated. The check that survives the confound is which statistic the gate "
        "NAMES when it speaks -- the verdict-bearing text, not the whole detail line. The trap "
        "is concrete: grepping the full line for `crush` fires on every arm because the gate "
        "reports `crush N%` by design, so only the segment after the verdict marker is "
        "evidence. This lane's first version of the check made exactly that mistake and "
        "reported a false alarm before catching itself."
    )),
    (1947, "BUILD-GATE-PRINT", "MEASURED", (
        "The corrected print gate issues zero FAIL on the 26 masters it was built against, so "
        "on this corpus it is evidenced ONLY by plants -- and that caveat must travel with any "
        "print-readiness claim made from it. The strongest supporting line is the one with no "
        "plant and therefore no confounder: real masters carry heavy crush and pass, "
        "`109MSDCF` at 2.470% and `119MSDCF` at 3.261%, corpus maximum 3.639%. Any crush "
        "threshold below 2.470% must fail a good master and any threshold above 3.639% is "
        "inert, which is the operational form of `there is no threshold to set here`."
    )),
    (1948, "ORCH", "MEASURED", (
        "Fourth occurrence of `an instrument's input path is part of its calibration`, and the "
        "first where the orchestrator was the one calibrated wrongly. The print gate run over "
        "`DELIVER-V6\\masters` returned a partition that summed correctly -- 17 PASS, 0 FAIL, "
        "3 ACQUITTED, 6 ACQUITTAL EXPIRED, 0 REVIEW, 7 NOT EXAMINED, 33 total (found 33) -- "
        "while reporting `FileNotFoundError` for exactly the 7 subjects added last. The "
        "product had been split across two sibling directories: a concurrently running lane "
        "moved those 7 masters into `DELIVER-V6\\orch-rendered-7` at 03:38, after an earlier "
        "orchestrator count of 33 in `masters` at 02:47 had already been used to certify "
        "coverage. Both readings were correct when taken; the tree moved between them. "
        "Re-running the gate against the second directory scored all 7 as REVIEW, giving a "
        "true 33-subject partition of 17 PASS, 0 FAIL, 3 ACQUITTED, 6 ACQUITTAL EXPIRED, 7 "
        "REVIEW, 0 NOT EXAMINED. Two lessons. First, the gate's insistence that every input "
        "land in a counted outcome is what surfaced this at all -- a gate that silently "
        "globbed would have reported 26 clean masters and no gap. Second, in a tree shared "
        "with concurrent agents, a directory listing is a measurement with a timestamp, not a "
        "standing fact, and coverage certified from an earlier listing must be re-measured "
        "rather than carried forward."
    )),
]


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()

    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    if max(ids) != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (max(ids), EXPECTED_TAIL))

    n_before = len(ids)
    cur_tail = EXPECTED_TAIL

    for new_id, lane, kind, body in ROWS:
        if new_id in ids:
            raise SystemExit("FATAL: fact %d already present" % new_id)
        if body.count("*") % 2 != 0:
            raise SystemExit("FATAL: odd '*' count in fact %d" % new_id)
        if "|" in body:
            raise SystemExit("FATAL: '|' in body of fact %d" % new_id)

        anchor = None
        for m in re.finditer(r"^\| %d \|.*$" % cur_tail, src, re.M):
            anchor = m
        if anchor is None:
            raise SystemExit("FATAL: could not locate row %d" % cur_tail)

        row = "| %d | %s | %s | %s |" % (new_id, lane, kind, body)
        src = src[: anchor.end()] + "\n" + row + src[anchor.end() :]
        cur_tail = new_id

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != ROWS[-1][0]:
        raise SystemExit("FATAL: post-write tail is %d, expected %d" % (max(ids2), ROWS[-1][0]))
    if len(ids2) != n_before + len(ROWS):
        raise SystemExit("FATAL: row count went %d -> %d, expected +%d"
                         % (n_before, len(ids2), len(ROWS)))
    for new_id, _l, _k, _b in ROWS:
        if new_id not in ids2:
            raise SystemExit("FATAL: fact %d missing after write" % new_id)
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
