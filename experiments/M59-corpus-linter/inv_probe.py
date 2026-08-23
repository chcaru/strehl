"""Measure before implementing invariants A and B.

Three questions the implementation depends on, none of which I can answer by
reading the spec:

  1. Which sections actually contain `^N. **` items? The spec says assert
     "section 5 or section 10", but SYNTHESIS 7 holds risks and 3/8 hold
     ordinary numbered lists. If any of those use a bold lead, a naive
     placement check fires on them and gets turned off.
  2. What is the naive per-line `**` false-positive rate? The orchestrator
     measured "about eighty". Reproducing that is the positive control for the
     item-grouping method: if the naive count is quiet here, my line-grouping
     differs from theirs and the whole comparison is void.
  3. Does the item-grouped, code-span-stripped count come out clean at HEAD?

Read-only. Run: python experiments/M59-corpus-linter/inv_probe.py
"""
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SYN = os.path.join(ROOT, "docs", "research", "SYNTHESIS.md")

SECTION = re.compile(r"^## (\d+)\. ")
ITEM = re.compile(r"^(\d+)\. ")
BOLD_ITEM = re.compile(r"^(\d+)\. \*\*")
CODE_SPAN = re.compile(r"`+[^`]*`+")


def load():
    text = io.open(SYN, encoding="utf-8", newline="").read()
    return text.replace("\r\n", "\n").split("\n")


def section_of(lines):
    """1-based line index -> section number."""
    out = {}
    cur = 0
    for i, l in enumerate(lines):
        m = SECTION.match(l)
        if m:
            cur = int(m.group(1))
        out[i] = cur
    return out


def items(lines, sec):
    """Yield (number, start_index, end_index_exclusive, section)."""
    n = len(lines)
    i = 0
    while i < n:
        m = ITEM.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n and lines[j].strip() and not ITEM.match(lines[j]) \
                and not SECTION.match(lines[j]) and not lines[j].startswith("## "):
            j += 1
        yield int(m.group(1)), i, j, sec[i]
        i = j


def main():
    lines = load()
    sec = section_of(lines)

    # --- Q1: where do bold-lead numbered items live? ---
    bold_by_sec = Counter()
    plain_by_sec = Counter()
    for num, a, b, s in items(lines, sec):
        if BOLD_ITEM.match(lines[a]):
            bold_by_sec[s] += 1
        else:
            plain_by_sec[s] += 1
    print("Q1  numbered items by section (bold lead `N. **` vs plain `N. `)")
    for s in sorted(set(list(bold_by_sec) + list(plain_by_sec))):
        print("    §%-3s bold=%-5d plain=%d" % (s, bold_by_sec[s], plain_by_sec[s]))
    outside = {s: c for s, c in bold_by_sec.items() if s not in (5, 10)}
    print("    bold-lead items OUTSIDE §5/§10: %s" % (outside or "none"))

    # --- Q2: naive per-line ** count, over §5 and §10 item regions ---
    naive_hits = []
    for num, a, b, s in items(lines, sec):
        if s not in (5, 10):
            continue
        for k in range(a, b):
            if lines[k].count("**") % 2:
                naive_hits.append((k + 1, s, num))
    print("")
    print("Q2  naive per-line odd-`**` lines inside §5/§10 items: %d" % len(naive_hits))
    print("    first 5: %s" % naive_hits[:5])

    # naive over the whole file, for scale
    whole = sum(1 for l in lines if l.count("**") % 2)
    print("    naive odd-`**` lines in the WHOLE file: %d" % whole)

    # --- Q3: item-grouped, code-spans stripped ---
    print("")
    print("Q3  item-grouped, code-spans stripped, §5/§10")
    bad = []
    literal_bold_in_code = 0
    for num, a, b, s in items(lines, sec):
        if s not in (5, 10):
            continue
        body = "\n".join(lines[a:b])
        if "`" in body:
            for m in CODE_SPAN.finditer(body):
                if "**" in m.group(0):
                    literal_bold_in_code += 1
        stripped = CODE_SPAN.sub("", body)
        c = stripped.count("**")
        if c % 2:
            bad.append((num, s, a + 1, c, lines[a][:110]))
    print("    unbalanced items: %d" % len(bad))
    for num, s, line, c, head in bad:
        print("      §%d item %d at L%d: %d `**` -> %s" % (s, num, line, c, head))
    print("    code spans containing a literal `**`: %d" % literal_bold_in_code)

    # --- same, over §4 fact rows ---
    print("")
    print("Q3b §4 fact rows, code-spans stripped")
    rows = bad_rows = 0
    for i, l in enumerate(lines):
        if sec[i] == 4 and re.match(r"^\|\s*\d+\s*\|", l):
            rows += 1
            if CODE_SPAN.sub("", l).count("**") % 2:
                bad_rows += 1
                print("      L%d: %s" % (i + 1, l[:110]))
    print("    %d rows, %d unbalanced" % (rows, bad_rows))

    # --- the four the orchestrator repaired: are they balanced now? ---
    print("")
    print("Q4  disciplines 170, 181, 211, 221 (repaired in 82f13b0)")
    for num, a, b, s in items(lines, sec):
        if s == 5 and num in (170, 181, 211, 221):
            body = "\n".join(lines[a:b])
            st = CODE_SPAN.sub("", body)
            print("    discipline %-4d L%-6d lines=%-3d `**`=%-3d %s"
                  % (num, a + 1, b - a, st.count("**"),
                     "balanced" if st.count("**") % 2 == 0 else "UNBALANCED"))

    # --- invariant A second half: do Question/Discipline refs resolve by section? ---
    print("")
    print("Q5  cross-references `Question N` / `Discipline N`")
    in_sec = {5: set(), 10: set()}
    for num, a, b, s in items(lines, sec):
        if s in (5, 10):
            in_sec[s].add(num)
    print("    §5 numbers: %d   §10 numbers: %d   shared: %d"
          % (len(in_sec[5]), len(in_sec[10]),
             len(in_sec[5] & in_sec[10])))
    shared = sorted(in_sec[5] & in_sec[10])
    print("    shared examples: %s" % shared[:14])
    print("    question 170 in §10? %s   discipline 170 in §5? %s"
          % (170 in in_sec[10], 170 in in_sec[5]))


if __name__ == "__main__":
    main()
