"""Scratch: build the namespace index and measure citation resolution rates.

Dumps every unresolved reference with context so the parser can be judged
against reality before it becomes a linter.
"""
import io
import os
import re
import sys
from collections import Counter

SYN = "docs/research/SYNTHESIS.md"

KIND_RE = re.compile(r"\b(facts?|disciplines?|questions?|risks?|rules?)\s+(?=\d)", re.I)
NUM_RE = re.compile(r"\d+")
CONNECTOR_RE = re.compile(r"\A(\s*(?:,|;|/|and|&|through|to|\u2013|\u2014|-)\s*)(?=\d)")


def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def build_index():
    lines = read(SYN).split("\n")
    marks = [(int(m.group(1)), i) for i, l in enumerate(lines)
             for m in [re.match(r"^## (\d+)\. ", l)] if m]
    spans = {}
    for k, (num, start) in enumerate(marks):
        end = marks[k + 1][1] if k + 1 < len(marks) else len(lines)
        spans[num] = (start, end)
    idx = {}
    a, b = spans[4]
    idx["fact"] = {int(m.group(1)): i + 1 for i in range(a, b)
                   for m in [re.match(r"^\|\s*(\d+)\s*\|", lines[i])] if m}
    for name, sec in (("discipline", 5), ("question", 10), ("risk", 7)):
        a, b = spans[sec]
        idx[name] = {int(m.group(1)): i + 1 for i in range(a, b)
                     for m in [re.match(r"^(\d+)\. ", lines[i])] if m}
    agents = read("AGENTS.md").split("\n")
    idx["rule"] = {int(m.group(1)): i + 1 for i, l in enumerate(agents)
                   for m in [re.match(r"^(\d+)\. \*\*", l)] if m}
    return idx, spans, lines


def parse_refs(text):
    """Yield (kind, number, offset, matched_text, suffixed) citations."""
    for m in KIND_RE.finditer(text):
        kind = m.group(1).lower().rstrip("s")
        if kind == "rule" and m.group(1).lower() == "rules":
            pass
        pos = m.end()
        first = True
        while True:
            nm = NUM_RE.match(text, pos)
            if not nm:
                break
            num = int(nm.group(0))
            after = text[nm.end():nm.end() + 1]
            if after.isalpha():
                # report-local sub-item label (`fact 198c`) — not a corpus ref
                yield (kind, num, nm.start(), text[m.start():nm.end() + 1], True)
                break
            if after == "." and text[nm.end() + 1:nm.end() + 2].isdigit():
                break  # a decimal like 1.253
            if after in ("%", "x", "\u00d7"):
                break  # a quantity like 10x, 42%
            yield (kind, num, nm.start(), text[m.start():nm.end()], False)
            pos = nm.end()
            cm = CONNECTOR_RE.match(text[pos:pos + 12])
            if not cm:
                break
            pos += len(cm.group(1))
            first = False


def line_of(text, off):
    return text.count("\n", 0, off) + 1


def main():
    idx, spans, lines = build_index()
    for k, v in idx.items():
        print("%-11s n=%-4d min=%-4d max=%-4d" % (k, len(v), min(v), max(v)))
    print()

    targets = [SYN]
    targets += sorted(os.path.join("docs/research", f) for f in os.listdir("docs/research")
                      if f.endswith(".md") and f != "SYNTHESIS.md")
    for root, _dirs, files in os.walk("crates"):
        if "target" in root.split(os.sep):
            continue
        for f in files:
            if f.endswith(".rs"):
                targets.append(os.path.join(root, f))

    unresolved = []
    stats = Counter()
    suffixed = []
    for path in targets:
        text = read(path)
        for kind, num, off, raw, suf in parse_refs(text):
            stats[(kind, "suffixed" if suf else "plain")] += 1
            if suf:
                suffixed.append((path, line_of(text, off), raw))
                continue
            if num not in idx.get(kind, {}):
                unresolved.append((path, line_of(text, off), kind, num, raw,
                                   text[max(0, off - 70):off + 40].replace("\n", " ")))
    print("token stats:", dict(stats))
    print()
    print("UNRESOLVED: %d" % len(unresolved))
    for path, ln, kind, num, raw, ctx in unresolved:
        print("  %s:%d  %s %d   ...%s..." % (path, ln, kind, num, ctx))
    print()
    print("LETTER-SUFFIXED (report-local, skipped): %d" % len(suffixed))
    for path, ln, raw in suffixed[:40]:
        print("  %s:%d  %s" % (path, ln, raw))


if __name__ == "__main__":
    main()
