"""Scratch: measure hit rates for candidate C2d (item shape) and C5a/C5c/C5d
(amendment consistency) before committing them to the linter."""
import io
import re
from collections import Counter

SYN = "docs/research/SYNTHESIS.md"
MARKERS = r"(AMENDED|REFUTED|PARTLY REFUTED|SCOPED|RESCOPED|MOOT|WITHDRAWN|SUPERSEDED|NOT ADMISSIBLE|RETRACTED)"


def cells(row):
    out, buf, i = [], "", 0
    while i < len(row):
        if row[i] == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if row[i] == "|":
            out.append(buf)
            buf = ""
            i += 1
            continue
        buf += row[i]
        i += 1
    out.append(buf)
    if out and not out[0].strip():
        out = out[1:]
    if out and not out[-1].strip():
        out = out[:-1]
    return out


def main():
    lines = io.open(SYN, encoding="utf-8", newline="").read().split("\n")
    marks = [(int(m.group(1)), i) for i, l in enumerate(lines)
             for m in [re.match(r"^## (\d+)\. ", l)] if m]
    spans = {n: (s, marks[k + 1][1] if k + 1 < len(marks) else len(lines))
             for k, (n, s) in enumerate(marks)}

    # ---- C2d: does an item's shape distinguish §5 from §10? ----
    for sec in (5, 10):
        a, b = spans[sec]
        qmark = 0
        tot = 0
        i = a
        while i < b:
            if re.match(r"^\d+\. ", lines[i]):
                j = i + 1
                buf = [lines[i]]
                while j < b and not re.match(r"^\d+\. ", lines[j]) and not lines[j].startswith("#"):
                    buf.append(lines[j])
                    j += 1
                tot += 1
                head = " ".join(buf)
                # the bolded lead sentence
                m = re.match(r"^\d+\. \*\*(.+?)\*\*", head, re.S)
                lead = m.group(1) if m else head[:200]
                if "?" in lead:
                    qmark += 1
                i = j
            else:
                i += 1
        print("§%d items=%d  bolded-lead contains '?': %d (%.0f%%)" % (sec, tot, qmark, 100.0 * qmark / tot))

    # ---- fact rows ----
    a, b = spans[4]
    rows = [(i + 1, lines[i]) for i in range(a, b) if re.match(r"^\|\s*\d+\s*\|", lines[i])]

    # C5a: refutation marker anywhere + "confirmed" in Source cell
    print("\n--- C5a: marker in row + 'confirm' in Source cell ---")
    n = 0
    for ln, r in rows:
        c = cells(r)
        if len(c) < 4:
            continue
        if re.search(MARKERS, r) and re.search(r"\bconfirm", c[3], re.I):
            n += 1
            print("  line %s  num=%s  SOURCE=[%s]" % (ln, c[0].strip(), c[3].strip()[:110]))
    print("  hits: %d" % n)

    # C5d: marker present but NOT in the Fact cell (headline unamended)
    print("\n--- C5d: amendment marker present in Consequence/Source but not in Fact cell ---")
    n = 0
    for ln, r in rows:
        c = cells(r)
        if len(c) < 4:
            continue
        infact = bool(re.search(MARKERS, c[1]))
        elsewhere = bool(re.search(MARKERS, c[2] + " " + c[3]))
        if elsewhere and not infact:
            n += 1
            if n <= 12:
                print("  line %s num=%s" % (ln, c[0].strip()))
    print("  hits: %d" % n)

    # C5c: question status vs facts claiming to close it
    print("\n--- C5c: question status vs 'closes question N' claims ---")
    a10, b10 = spans[10]
    qstat = {}
    i = a10
    while i < b10:
        m = re.match(r"^(\d+)\. ", lines[i])
        if m:
            num = int(m.group(1))
            j = i + 1
            buf = [lines[i]]
            while j < b10 and not re.match(r"^\d+\. ", lines[j]) and not lines[j].startswith("#"):
                buf.append(lines[j])
                j += 1
            body = " ".join(buf)
            st = set(re.findall(r"\b(REOPENED|CLOSED|ANSWERED|MOOT|WITHDRAWN)\b", body))
            if st:
                qstat[num] = (i + 1, st)
            i = j
        else:
            i += 1
    print("  questions carrying a status marker: %s" % {k: sorted(v[1]) for k, v in qstat.items()})
    closes = re.compile(r"(closes?|closed|answers?|answered)\s+question\s+(\d+)", re.I)
    for ln, r in rows:
        for m in closes.finditer(r):
            q = int(m.group(2))
            st = qstat.get(q, (None, set()))[1]
            if "REOPENED" in st:
                print("  CONFLICT line %d: '%s' but question %d is REOPENED" % (ln, m.group(0), q))

    # also: reopen+close inside one row
    print("\n--- C5b: same row says a question is both closed and reopened ---")
    for ln, r in rows:
        qs_close = {int(m.group(2)) for m in closes.finditer(r)}
        qs_open = {int(m.group(1)) for m in re.finditer(r"question\s+(\d+)[^.|]{0,60}REOPEN", r, re.I)}
        qs_open |= {int(m.group(1)) for m in re.finditer(r"REOPEN\w*[^.|]{0,60}question\s+(\d+)", r, re.I)}
        both = qs_close & qs_open
        if both:
            print("  line %d  questions %s both closed and reopened in one row" % (ln, sorted(both)))


if __name__ == "__main__":
    main()
