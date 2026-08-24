"""Measure how citations sit relative to line breaks before changing C1.

C1's KIND_TOKEN is `(facts?|...|questions?)\\s+(?=\\d)`. `\\s+` crosses newlines
AND blank lines, so a heading ending in the word "question" followed by a
paragraph starting with a digit is read as a citation. That is how
M87-occlusion.md:3738 produced `question 49`.

Before tightening it I need to know what I would break: how many citations in
the corpus legitimately span a line break, and how many span a blank line.
"""
import io
import os
import re
import sys

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
sys.path.insert(0, os.path.join(ROOT, "scripts"))

KIND = re.compile(r"(?<![-\w])(facts?|disciplines?|questions?|risks?|rules?)(\s+)(?=\d)", re.I)


def main():
    same = span1 = spanblank = 0
    ex1, exb = [], []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in
                       (".git", "target", "node_modules", ".cargo-target-orch")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            try:
                with io.open(p, encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            for m in KIND.finditer(text):
                gap = m.group(2)
                nl = gap.count("\n")
                line = text.count("\n", 0, m.start()) + 1
                nm = re.compile(r"\d+").match(text, m.end())
                snippet = re.sub(r"\s+", " ", text[m.start():m.end() + 12])
                if nl == 0:
                    same += 1
                elif nl == 1:
                    span1 += 1
                    if len(ex1) < 12:
                        ex1.append(f"{rel}:{line}  {snippet!r}")
                else:
                    spanblank += 1
                    if len(exb) < 12:
                        exb.append(f"{rel}:{line}  {snippet!r}")

    print(f"citations on ONE line              : {same}")
    print(f"citations spanning ONE newline     : {span1}")
    print(f"citations spanning a BLANK line    : {spanblank}")
    print()
    print("--- examples spanning one newline (these must keep working) ---")
    for e in ex1:
        print("  " + e)
    print()
    print("--- examples spanning a blank line (candidates for the false positive) ---")
    for e in exb:
        print("  " + e)


if __name__ == "__main__":
    main()
