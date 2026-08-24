"""Report the current max fact and discipline numbers in SYNTHESIS.md."""
import re
import pathlib

p = pathlib.Path(__file__).resolve().parents[2] / "docs" / "research" / "SYNTHESIS.md"
raw = p.read_text(encoding="utf-8")

facts = [int(m) for m in re.findall(r"^\|\s*(\d+)\s*\|", raw, re.M)]
disc = [int(m) for m in re.findall(r"^\|\s*D?(\d+)\s*\|", raw, re.M)]

print("path:", p)
print("bytes:", len(raw.encode("utf-8")))
print("max numbered row:", max(facts) if facts else None)
print("row count:", len(facts))

for label in ("## Facts", "## Disciplines", "# Disciplines", "Disciplines"):
    i = raw.find(label)
    if i >= 0:
        print(f"section {label!r} at char {i}")
