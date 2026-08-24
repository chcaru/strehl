r"""Verify table-row integrity for the rows touched by folds 112-114.

Written as a FILE, not `python -c`, because a one-liner passed through a PowerShell
double-quoted string mangles the backslash in the `\|` escape pattern and reports
false pipe counts -- which is exactly what happened when this was first checked inline.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
ROWS = [1500, 1501, 1507, 1511, 1512, 1513, 1514, 1515, 1516,
        1517, 1518, 1519, 1520, 1521, 1522, 1523]

raw = io.open(PATH, encoding="utf-8").read()
lines = raw.split("\n")

bad = 0
for fid in ROWS:
    hits = [l for l in lines if l.startswith("| %d |" % fid)]
    if len(hits) != 1:
        print("FAIL  fact %d: %d rows found, expected 1" % (fid, len(hits)))
        bad += 1
        continue
    line = hits[0]
    stripped = line.replace("\\|", "")       # 2-char sequence: backslash, pipe
    n = stripped.count("|")
    esc = line.count("\\|")
    status = "ok " if n == 5 else "FAIL"
    if n != 5:
        bad += 1
    print("%s fact %-5d unescaped=%d escaped=%d len=%d" % (status, fid, n, esc, len(line)))

print()
print("rows checked: %d   failures: %d" % (len(ROWS), bad))

# Every row must also end cleanly, i.e. no graft left a dangling fragment past the
# closing pipe (discipline 768's failure mode is silent and lint-clean).
for fid in ROWS:
    hits = [l for l in lines if l.startswith("| %d |" % fid)]
    if hits and not hits[0].rstrip().endswith("|"):
        print("FAIL fact %d does not end with a closing pipe" % fid)
        bad += 1

print("VERDICT:", "ALL ROWS WELL FORMED" if bad == 0 else "%d PROBLEM(S)" % bad)
