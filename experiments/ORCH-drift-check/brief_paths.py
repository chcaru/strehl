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

sys.exit(1 if missing_c else 0)
