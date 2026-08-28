"""Append facts 1960-1961 to the SYNTHESIS fact table (lanes BUILD-DEFECT, ORCH)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1959

ROWS = [
    (1960, "BUILD-DEFECT", "MEASURED", (
        "Banking a hash preserves a derived image's IDENTITY but not its REPRODUCIBILITY, which "
        "refines the corpus's own purge doctrine rather than restating it. The doctrine `a "
        "byte-freeze result IS a SHA256, the TIFFs were only its carrier` holds for a FREEZE, "
        "where identity is the whole result. It fails for a VISUALISATION, where the result is "
        "what the picture shows. Priced concretely: a 459736-byte, 512x410 exhibit was banked "
        "with its full 64-character SHA256 and its crop geometry was later recovered and "
        "confirmed against the artifact (two 256-px crops, row 1 clipped to 205, predicting "
        "512x410, which the file measures). The 8-bit stretch endpoints could NOT be recovered: "
        "they were per-crop percentile(1)/percentile(99.5) computed over arrays inside a TIFF "
        "pair that was since deleted, and were never printed. The stretch is precisely what the "
        "8-bit conversion discarded. Discipline: print the normalisation parameters of any "
        "derived visualisation AT RENDER TIME, in text, beside the hash. The lane recorded this "
        "as its own local gap rather than listing the recovered geometry and letting the entry "
        "read as complete."
    )),
    (1961, "ORCH", "MEASURED", (
        "In PowerShell, `-match` against an ARRAY is a filter, not a containment test, and "
        "silently converts a boolean probe into one that can report a string present when it is "
        "absent. Caught live while verifying a lane's commit: a loop printing "
        "`$blob -match [regex]::Escape($s)` where `$blob` came from `git show` (an array of "
        "lines) printed `System.Object[]` for every term, including `459,736` -- and the "
        "re-run, joining the lines into one string and calling `.Contains()`, returned False "
        "for `459,736` and True for `459736`. The comma-formatted variant was never in the "
        "file. Both a hit and a miss render as non-empty-looking output, so the probe's "
        "`nothing` and its `something` are indistinguishable at a glance. Discipline: join "
        "multi-line command output with `-join` and use `.Contains()` or an explicit "
        "`[bool]`, and require every containment probe to print True or False and nothing else. "
        "Same family as the whitespace-collapse rule for quotes spanning line breaks."
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
