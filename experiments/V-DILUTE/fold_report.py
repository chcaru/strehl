"""Append the Assignment 2 section into the one file this lane owns.

ORCH's rule is "own docs/research/V-DILUTE.md only", so the base-band report is
appended there rather than landing as a second file in docs/research/.
Explicit utf-8 on both ends; no shell redirect, which would re-encode.
"""
import os

DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-DILUTE.md"
SRC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-DILUTE-BASEBAND.md"

with open(SRC, "r", encoding="utf-8") as f:
    add = f.read()
with open(DOC, "r", encoding="utf-8") as f:
    cur = f.read()

if "Assignment 2 — the base-band blur hypothesis" in cur:
    print("already appended; nothing to do")
else:
    with open(DOC, "w", encoding="utf-8") as f:
        f.write(cur.rstrip() + "\n\n---\n\n" + add)
    print(f"appended {len(add)} chars -> {os.path.basename(DOC)}")

os.remove(SRC)
print("removed the stray second file")

with open(DOC, "r", encoding="utf-8") as f:
    print("total lines now:", len(f.read().split("\n")))
