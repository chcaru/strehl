"""Append fact 1973 to the SYNTHESIS fact table (ORCH: silent-zero glob filter)."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1972

ROWS = [
    (1973, "ORCH-drift-check", "MEASURED", (
        "AN EXTENSION FILTER THAT IS A PROPER PREFIX OF THE REAL EXTENSION RETURNS A SILENT "
        "ZERO, and it fired on the final verification of the deliverable itself. The "
        "orchestrator's product check used `Get-ChildItem -File -Filter '*.tif'` against the "
        "master directory and printed `masters: 0 TIFFs` while 33 masters totalling 6.08 GB were "
        "present, because the files are named `.tiff`. Measured directly on the same directory "
        "in the same shell: `-Filter '*.tif'` gives 0, `-Filter '*.tiff'` gives 33, `-Filter "
        "'*.tif*'` gives 33, `-Include '*.tif'` gives 0, and a Where-Object test on `.Extension "
        "-in '.tif','.tiff'` gives 33. PowerShell's `-Filter` is passed to the filesystem "
        "wildcard engine and does NOT extend a trailing extension the way an eye does. The "
        "product was then re-verified the correct way and is intact: 33 of 33 SHA256 hashes "
        "match the banked table, 0 mismatches, 0 not-in-bank. The generalisable rule is the same "
        "one the corpus has now hit from four directions: A ZERO IS THE SAME GLYPH WHETHER THE "
        "SET IS EMPTY OR THE QUERY NEVER MATCHED, so any probe whose passing state is a count "
        "must be shown to produce a non-zero on a case known to exist before its zero is "
        "believed. Enumerate by attribute, not by a hand-typed wildcard, whenever the answer is "
        "load-bearing."
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
    print("OK facts %s appended  rows %d -> %d"
          % (", ".join(str(r[0]) for r in ROWS), n_before, len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
