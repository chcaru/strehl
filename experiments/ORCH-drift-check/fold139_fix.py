"""Repair fold139's question insertion.

Two compounding defects, same root:
  1. `full_line(raw, "202. ")` matched DISCIPLINE 202 in section 5, not
     QUESTION 202 in section 10, because section 5 comes first in the file.
  2. Section 5 entries WRAP across physical lines with indented continuations,
     so the insertion landed between discipline 202's first line and its own
     continuation, breaking its bold span.

The fix anchors inside the questions section only, and inserts after the whole
wrapped entry rather than after its first physical line.
"""
import io
import re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    lines = fh.read().split("\n")

BAD = "203. **Does blotch severity track measured level drift"
hits = [i for i, l in enumerate(lines) if l.startswith(BAD)]
assert len(hits) == 1, "expected exactly 1 misplaced line, found %d" % len(hits)
moved = lines.pop(hits[0])
print("removed misplaced entry from line %d" % (hits[0] + 1))

# Locate the questions section, then question 202 within it.
sec = [i for i, l in enumerate(lines) if re.match(r"^#{1,3} .*[Qq]uestion", l)]
assert sec, "could not find a questions section heading"
start = sec[-1]
end = len(lines)
for i in range(start + 1, len(lines)):
    if re.match(r"^#{1,3} ", lines[i]):
        end = i
        break
print("questions section: lines %d-%d (%s)" % (start + 1, end, lines[start].strip()))

q202 = [i for i in range(start, end) if lines[i].startswith("202. ")]
assert len(q202) == 1, "expected 1 question 202 in the section, found %d" % len(q202)
i = q202[0]

# Walk past any indented continuation lines of the wrapped entry.
j = i + 1
while j < end and lines[j].strip() and not re.match(r"^\d+\. ", lines[j]):
    j += 1
print("question 202 occupies lines %d-%d" % (i + 1, j))

lines.insert(j, moved)

txt = "\n".join(lines)
assert txt.count(BAD) == 1, "duplicate after re-insertion"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(txt)
print("re-inserted as question 203 after question 202 at line %d" % (j + 1))
