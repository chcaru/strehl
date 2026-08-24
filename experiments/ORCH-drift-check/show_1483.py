"""Print the exact current text of facts 1483-1487 and discipline 759 before amending."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
with io.open(P, "r", encoding="utf-8") as fh:
    raw = fh.read()

for fid in range(1483, 1488):
    m = re.search(r"^\| %d \|.*$" % fid, raw, re.M)
    print("--- FACT %d ---" % fid)
    print(m.group(0) if m else "NOT FOUND")
    print()

for did in (759, 760):
    m = re.search(r"^%d\. .*$" % did, raw, re.M)
    print("--- DISCIPLINE %d ---" % did)
    print(m.group(0) if m else "NOT FOUND")
    print()
