"""Append facts 1969-1970 to the SYNTHESIS fact table (lane V-SOFTCHECK)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1968

ROWS = [
    (1969, "V-SOFTCHECK", "MEASURED", (
        "The merge-versus-best-frame question has no single answer because THE SIGN FLIPS WITH "
        "FREQUENCY, and that reframing is the result. On `113MSDCF` the master reads 1.0997, "
        "1.1936 and 1.1345 of the per-site ceiling across 0.05-0.20 cyc per output px, i.e. "
        "SHARPER than the best single source frame, and 0.9426, 0.7314, 0.6063, 0.5942 across "
        "0.20-0.40, i.e. softer. The merge is therefore softer only above roughly 0.20 cyc per "
        "output px. In the highest band that actually qualifies on that subject, 0.20-0.25 at "
        "R = 3.32, the shortfall is 0.9426, about 5.7%. Relative to the originating claim, the "
        "SIGN survives qualification and the MAGNITUDE does not. Two limits are stated in the "
        "report rather than buried: the deciding figure 0.9426 carries NO confidence interval "
        "and is marked NOT MEASURED for its interval, because the only interval this lane holds "
        "(+0.0656 dex per doubling, +0.0495 to +0.0950, at R = 2.32) answers bracket depth and "
        "not master-versus-frame, so quoting it alongside would be quoting the wrong "
        "measurement; and the ceiling ratio rests on ONE subject of 63 frames while the "
        "originating claim spanned four, the other three never having been re-derived in a "
        "qualified band."
    )),
    (1970, "V-SOFTCHECK", "MEASURED", (
        "A lane's self-reported inventory of its own outputs was wrong, and the deciding numbers "
        "were in the file it failed to enumerate. It reported three committed documents; it has "
        "six, and the ceiling ratios the orchestrator had asked for lived in the unenumerated "
        "`-nyquist.md`. Nothing was lost, but a self-reported inventory is not an enumeration "
        "and must not be accepted as one -- list the artifacts with a command. The same lane "
        "flagged a second trap it created: `-ninvariance` and `-N-invariance` differ only by "
        "case and a hyphen, are separate files, and will mislead the next reader on a "
        "case-insensitive filesystem. Related and worth carrying: this lane wrote a VERDICT "
        "section that its own 25-claim harness did not cover, noticed that the new text could "
        "therefore be reversed silently, and closed the hole itself by adding three claims each "
        "with a conclusion-flip mutation that leaves every number intact, reaching 28 of 28 "
        "claims with 24 caught, 0 mis-attributed, 0 silent and 0 vacuous. Adding prose to a "
        "report does not extend the harness that guards it."
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
