"""Append facts 1971-1972 to the SYNTHESIS fact table (lane V-NEVERWORSE)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1970

ROWS = [
    (1971, "V-NEVERWORSE", "MEASURED", (
        "A second lane independently caught the orchestrator's stale-broadcast failure, and it "
        "supplied the sharper diagnostic: A NUMBER THAT DOES NOT MOVE WHEN THE THING IT "
        "MEASURES PROVABLY SHRANK IS A FROZEN PROBE, because a live scan would have moved and a "
        "cached one reads identically to a live one. The orchestrator had reported 8.66 GB for "
        "this lane across three consecutive messages spanning an interval in which the lane "
        "deleted 0.640 GB and removed its entire D-drive subtree. The lane's own figures were "
        "then verified by the orchestrator rather than accepted: 123 files, 24844047 bytes, "
        "zero access errors, D-side absent -- matching the lane's three independent "
        "measurements by Get-ChildItem with errors CAPTURED rather than suppressed, by `cmd dir "
        "/s /a`, and by `robocopy /L /S /BYTES`. The lane re-ran with errors captured "
        "specifically because `-ErrorAction SilentlyContinue` would have hidden ACL-denied "
        "subtrees, which is the failure mode that would have made it wrong. Its 8 headline "
        "values also re-certified 8-of-8 BANKED under the patched verifier with controls clean. "
        "The asymmetric cost the lane named is the reason this matters: a frozen probe pressures "
        "lanes to delete evidence that is already gone."
    )),
    (1972, "V-NEVERWORSE", "MEASURED", (
        "Seven of this lane's nine verifiers have `conclusion_checks=0`, so their greens are NOT "
        "polarity-audited -- the instruments confirm that values are present without "
        "establishing that a reversed conclusion would have been caught. The lane published this "
        "as a named NOT MEASURED gap rather than leaving it to be discovered, and noted that "
        "closing it needs no scratch, only editing time. This is the same hole found "
        "independently in at least four other lanes tonight and in the orchestrator's own "
        "banking verifier, which makes it a corpus-wide pattern rather than one lane's "
        "oversight: a check that only asserts presence is satisfied by any text containing the "
        "value, and only a conclusion-flip mutation that leaves every number intact "
        "distinguishes a guarded claim from a decorative one. Two further gaps were named in "
        "the same reply: the L0/plateau family was stopped at wind-down rather than for disk, "
        "and the resampling hypothesis (1.542 unregistered against 1.1628 registered on the "
        "same band and subject) is explicitly NOT MEASURED because it would have required "
        "re-materialising develop bundles there was no disk for."
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
        src = src[: anchor.end()] + "\n" + ("| %d | %s | %s | %s |" % (new_id, lane, kind, body)) + src[anchor.end():]
        cur_tail = new_id

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(src)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != ROWS[-1][0]:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != n_before + len(ROWS):
        raise SystemExit("FATAL: row count went %d -> %d" % (n_before, len(ids2)))
    for new_id, _l, _k, _b in ROWS:
        if new_id not in ids2:
            raise SystemExit("FATAL: fact %d missing after write" % new_id)
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
