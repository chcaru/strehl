"""Scratch survey: what shapes actually exist in SYNTHESIS.md and the corpus.

Read-only. Informs the design of scripts/corpus_lint.py.
"""
import io
import re
from collections import Counter

SYN = "docs/research/SYNTHESIS.md"


def load(path):
    return io.open(path, encoding="utf-8", newline="").read().split("\n")


def unescaped_pipes(line):
    return line.replace("\\|", "").count("|")


def main():
    lines = load(SYN)

    # --- every table-ish line, grouped into contiguous blocks ---
    print("### TABLE BLOCKS (contiguous lines starting with '|')")
    i = 0
    blocks = []
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            blocks.append((i, j))
            i = j
        else:
            i += 1
    for (a, b) in blocks:
        counts = Counter(unescaped_pipes(lines[k]) for k in range(a, b))
        print("  lines %d-%d  n=%d  pipe-counts=%s  header=%s" %
              (a + 1, b, b - a, dict(counts), lines[a][:80]))

    # --- numbered list items per section ---
    print()
    print("### NUMBERED LIST ITEMS BY SECTION")
    sec_marks = [(int(m.group(1)), i) for i, l in enumerate(lines)
                 for m in [re.match(r"^## (\d+)\. ", l)] if m]
    for k, (num, start) in enumerate(sec_marks):
        end = sec_marks[k + 1][1] if k + 1 < len(sec_marks) else len(lines)
        items = [(i + 1, int(m.group(1))) for i in range(start, end)
                 for m in [re.match(r"^(\d+)\. ", lines[i])] if m]
        if items:
            nums = [n for _, n in items]
            print("  §%-3d lines %d-%d  items=%d  min=%d max=%d  dups=%s" %
                  (num, start + 1, end, len(items), min(nums), max(nums),
                   [n for n, c in Counter(nums).items() if c > 1]))

    # --- citation token survey across the corpus ---
    print()
    print("### CITATION TOKEN FORMS in SYNTHESIS")
    text = "\n".join(lines)
    for pat in [r"\bfacts?\s+\d+[a-z]", r"\bfacts?\s+\d+", r"\bdisciplines?\s+\d+",
                r"\bquestions?\s+\d+", r"\brisks?\s+\d+", r"\brules?\s+\d+",
                r"\bfacts?\s+\d+\s*[-\u2013]\s*\d+", r"\bfacts?\s+\d+(,\s*\d+)+",
                r"\bfacts?\s+\d+\s+and\s+\d+"]:
        print("  %-40s %d" % (pat, len(re.findall(pat, text, re.I))))

    # sample the letter-suffixed ones
    print()
    print("### LETTER-SUFFIXED fact refs in SYNTHESIS (sample)")
    for m in list(re.finditer(r"\bfacts?\s+\d+[a-z]\b", text, re.I))[:20]:
        ln = text[:m.start()].count("\n") + 1
        print("  line %d: %s" % (ln, text[max(0, m.start() - 60):m.end() + 20].replace("\n", " ")))


if __name__ == "__main__":
    main()
