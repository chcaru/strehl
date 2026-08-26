import re
from pathlib import Path

P = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-RIM-verification.md")
t = P.read_text(encoding="utf-8")

hits = [(t[:m.start()].count("\n") + 1, m.group(0))
        for m in re.finditer(r"\S{0,25}''\S{0,25}", t)]
print("doubled-apostrophe sites:", len(hits))
for ln, s in hits:
    print(f"  {ln}: {s}")

t2 = t.replace("''", "'")
print("after fix, remaining:", len(re.findall(r"''", t2)))

OLDW = """veil nor the ring is in the photographs.** Across sixteen usable single-frame renders
from the two anchors' own brackets — including, on each subject, the frame in
which the silhouette is genuinely in focus — every profile climbs monotonically
from silhouette to far field."""
NEWW = """veil nor the ring is in the photographs.** Across sixteen usable single-frame
renders from the two anchors' own brackets — including, on each subject, the
frame in which the silhouette is genuinely in focus — every profile climbs
monotonically from silhouette to far field."""
assert OLDW in t2, "REFLOW ANCHOR NOT FOUND"
t2 = t2.replace(OLDW, NEWW)

P.write_text(t2.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
print("written")
