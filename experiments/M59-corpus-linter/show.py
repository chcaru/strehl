"""Scratch helper: print SYNTHESIS.md items by namespace and number.

Usage: python show.py fact 694 725 759
       python show.py question 178
       python show.py discipline 351
"""
import io
import re
import sys

SYN = "docs/research/SYNTHESIS.md"

SECTION_RE = re.compile(r"^## (\d+)\. ")


def sections(lines):
    """Return {section_number: (start_idx, end_idx)} over 0-based line indices."""
    marks = []
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if m:
            marks.append((int(m.group(1)), i))
    out = {}
    for k, (num, start) in enumerate(marks):
        end = marks[k + 1][1] if k + 1 < len(marks) else len(lines)
        out[num] = (start, end)
    return out


def fact_rows(lines, span):
    """Yield (lineno_1based, number, raw_line) for §4 table rows."""
    start, end = span
    for i in range(start, end):
        line = lines[i]
        m = re.match(r"^\|\s*(\d+)\s*\|", line)
        if m:
            yield i + 1, int(m.group(1)), line


def list_items(lines, span):
    """Yield (lineno_1based, number, text) for numbered list items, item text joined."""
    start, end = span
    i = start
    while i < end:
        m = re.match(r"^(\d+)\. ", lines[i])
        if m:
            num = int(m.group(1))
            j = i + 1
            buf = [lines[i]]
            while j < end and not re.match(r"^\d+\. ", lines[j]) and not lines[j].startswith("## "):
                buf.append(lines[j])
                j += 1
            yield i + 1, num, "\n".join(buf).rstrip()
            i = j
        else:
            i += 1


def main():
    kind = sys.argv[1]
    wanted = {int(x) for x in sys.argv[2:]}
    text = io.open(SYN, encoding="utf-8", newline="").read()
    lines = text.split("\n")
    secs = sections(lines)
    if kind == "fact":
        for ln, num, raw in fact_rows(lines, secs[4]):
            if num in wanted:
                print("=" * 100)
                print("FACT %d  (line %d)" % (num, ln))
                print(raw)
    else:
        sec = 5 if kind == "discipline" else 10
        for ln, num, txt in list_items(lines, secs[sec]):
            if num in wanted:
                print("=" * 100)
                print("%s %d  (line %d)" % (kind.upper(), num, ln))
                print(txt)


if __name__ == "__main__":
    main()
