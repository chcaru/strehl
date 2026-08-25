"""Check that every absolute path the owner brief points at actually exists.

`captures-needed.md` is the document the owner reads in the morning, and it
tells him to open specific files. A path that was renamed, or that an agent
never wrote, turns the whole section into noise -- and there is no lint for it,
because `corpus_lint` checks the corpus's internal consistency, not the
filesystem.

Reports missing paths grouped by whether they are under D:\\ (the owner's own
captures, which may legitimately be offline) or C:\\ (things this project wrote,
which should be there).

Reads only.
"""
import io
import os
import re
import sys

DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\captures-needed.md"

# Optional override, so the checks can be commissioned against a deliberately
# broken copy in TEMP. A check that has never been seen to fail is not known to
# work -- see the plant/counter-plant discipline used throughout this project.
if len(sys.argv) > 1:
    DOC = sys.argv[1]

with io.open(DOC, "r", encoding="utf-8") as fh:
    text = fh.read()

# Paths appear inside code spans. Take those, so prose mentioning a drive
# letter in passing is not treated as a claim that a file exists.
spans = re.findall(r"`([^`\n]+)`", text)
paths = []
for s in spans:
    s = s.strip().rstrip(".,;:")
    if re.match(r"^[A-Za-z]:\\", s):
        paths.append(s)

seen = {}
for p in paths:
    seen[p] = seen.get(p, 0) + 1

missing_c, missing_d, ok = [], [], []
for p in sorted(seen):
    # A trailing backslash means a directory.
    q = p.rstrip("\\")
    exists = os.path.exists(q)
    if exists:
        ok.append(p)
    elif q[:1].upper() == "D":
        missing_d.append(p)
    else:
        missing_c.append(p)

print("absolute paths cited in captures-needed.md: %d distinct (%d mentions)"
      % (len(seen), len(paths)))
print("  exist        : %d" % len(ok))
print("  missing on C:: %d" % len(missing_c))
print("  missing on D:: %d" % len(missing_d))

if missing_c:
    print()
    print("MISSING, and this project was supposed to have written them:")
    for p in missing_c:
        print("  x%3d  %s" % (seen[p], p))

if missing_d:
    print()
    print("missing under D: (owner's captures -- may be offline or renamed):")
    for p in missing_d:
        print("  x%3d  %s" % (seen[p], p))

# --- Section cross-references -------------------------------------------
#
# The START HERE table -- the first thing the owner reads -- is built almost
# entirely out of "see SS24" style references. A reference to a section that
# does not exist turns his top action item into a dead end, and no existing
# check would notice: `corpus_lint` does not read this file and the path check
# above only looks at code spans.
#
# Added after a real miss of the same shape: a switchboard row said "see
# tonight's near-miss below" when the near-miss had been written into
# SYNTHESIS.md and never into this document.

heads = set(re.findall(r"(?m)^#{2,4}[ \t]*(?:\u00a7[ \t]*)?(\d+)[.)]?[ \t]", text))
refs = {}
for m in re.finditer(r"\u00a7[ \t]*(\d+)", text):
    refs[m.group(1)] = refs.get(m.group(1), 0) + 1

dangling = sorted((r for r in refs if r not in heads), key=int)

print()
print("section refs: %d distinct (%d mentions) against %d numbered headings"
      % (len(refs), sum(refs.values()), len(heads)))
if dangling:
    print()
    print("DANGLING section refs -- these point at nothing:")
    for r in dangling:
        print("  x%3d  \u00a7%s" % (refs[r], r))
else:
    print("  all resolve")

sys.exit(1 if (missing_c or dangling) else 0)
