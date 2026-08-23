"""Scratch: measure feasibility of candidate checks C2b/C2c/C5/C7 on HEAD."""
import io
import re
from collections import Counter

SYN = "docs/research/SYNTHESIS.md"


def load():
    lines = io.open(SYN, encoding="utf-8", newline="").read().split("\n")
    marks = [(int(m.group(1)), i) for i, l in enumerate(lines)
             for m in [re.match(r"^## (\d+)\. ", l)] if m]
    spans = {}
    for k, (num, start) in enumerate(marks):
        spans[num] = (start, marks[k + 1][1] if k + 1 < len(marks) else len(lines))
    return lines, spans


def split_cells(row):
    """Split a table row on unescaped pipes, restoring escapes."""
    parts = row.split("|")
    out, buf = [], ""
    for p in parts:
        if buf.endswith("\\"):
            buf = buf[:-1] + "|" + p
        else:
            if buf or out or True:
                out.append(buf)
            buf = p
    out.append(buf)
    return out[1:]  # leading empty from the opening pipe


def main():
    lines, spans = load()

    # --- C2b: ordering of list items in §5 and §10 ---
    for sec in (5, 7, 10):
        a, b = spans[sec]
        items = [(i + 1, int(m.group(1))) for i in range(a, b)
                 for m in [re.match(r"^(\d+)\. ", lines[i])] if m]
        nums = [n for _, n in items]
        desc = [(items[k - 1], items[k]) for k in range(1, len(items)) if nums[k] < nums[k - 1]]
        print("§%d: %d items, ascending=%s, descents=%s" %
              (sec, len(items), not desc, desc[:5]))

    # --- C2c: continuation indentation of list items in §5 / §10 ---
    print("\n--- continuation-line indents (non-blank lines inside an item) ---")
    for sec in (5, 10):
        a, b = spans[sec]
        indents = Counter()
        offenders = []
        i = a
        while i < b:
            if re.match(r"^\d+\. ", lines[i]):
                j = i + 1
                while j < b and not re.match(r"^\d+\. ", lines[j]) and not lines[j].startswith("#"):
                    if lines[j].strip():
                        ind = len(lines[j]) - len(lines[j].lstrip(" "))
                        indents[ind] += 1
                        if ind not in (0, 5):
                            offenders.append((j + 1, ind, lines[j][:70]))
                        elif ind == 0:
                            offenders.append((j + 1, 0, lines[j][:70]))
                    j += 1
                i = j
            else:
                i += 1
        print("§%d indents=%s" % (sec, dict(sorted(indents.items()))))
        for o in offenders[:15]:
            print("   line %d indent=%d  %s" % o)

    # --- C5: status vocabulary in §10 questions ---
    print("\n--- §10 question status markers ---")
    a, b = spans[10]
    vocab = Counter()
    for i in range(a, b):
        for w in re.findall(r"\b(ANSWERED|CLOSED|REOPENED|OPEN|MOOT|WITHDRAWN|SUPERSEDED|PARTLY ANSWERED)\b", lines[i]):
            vocab[w] += 1
    print(dict(vocab))

    # --- amendment markers in fact rows ---
    print("\n--- amendment markers in §4 fact rows ---")
    a, b = spans[4]
    marks = Counter()
    rows_with = 0
    for i in range(a, b):
        if not re.match(r"^\|\s*\d+\s*\|", lines[i]):
            continue
        found = re.findall(r"\b(AMENDED|REFUTED|SCOPED|RESCOPED|MOOT|WITHDRAWN|SUPERSEDED|NOT ADMISSIBLE|DEFECT|PARTLY REFUTED|CORRECTED|RETRACTED)\b", lines[i])
        if found:
            rows_with += 1
            for f in set(found):
                marks[f] += 1
    print("rows with a marker: %d ; marker counts: %s" % (rows_with, dict(marks)))

    # --- C7: Source-cell provenance labels ---
    print("\n--- §4 Source-cell label coverage ---")
    labels = re.compile(r"\b(MEASURED|DERIVED|ARGUED|VERIFIED|UNVERIFIED|REPORTED|ASSUMED)\b")
    missing = []
    n = 0
    for i in range(a, b):
        if not re.match(r"^\|\s*\d+\s*\|", lines[i]):
            continue
        n += 1
        cells = split_cells(lines[i])
        src = cells[3] if len(cells) > 3 else ""
        if not labels.search(src):
            missing.append((i + 1, lines[i][:60], src[:90]))
    print("rows=%d  Source cells with no label: %d" % (n, len(missing)))
    for m in missing[:20]:
        print("   line %d  %s  SOURCE=[%s]" % m)


if __name__ == "__main__":
    main()
