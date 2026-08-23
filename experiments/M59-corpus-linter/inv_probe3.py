"""Third pass: separate the three causes tangled in inv_probe2's result C, and
reconcile the naive-`**` count with the orchestrator's "about eighty".

Result C reported 11 of 19 status claims disagreeing. Inspecting the four
flagged questions by hand shows three different causes:

  - question 20  -- SYNTHESIS 10 DOES carry "**CLOSED by facts 90-92**", but in a
    continuation PARAGRAPH after a blank line. My walker stopped at the blank
    line, so the marker was invisible to it. My bug, not a corpus defect.
  - question 70  -- the claim is "Question 70 cannot be answered", which is
    prose, not a status assertion. Irreducible false positive.
  - questions 120, 161 -- no marker anywhere in the item. Possibly real.

So this re-measures with two body extents (blank-line-terminated, which is what
invariant B needs, and next-item-terminated, which is what a status check
needs) and with negation filtered, to find the true rate.

Read-only. Run: python experiments/M59-corpus-linter/inv_probe3.py
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SYN = os.path.join(ROOT, "docs", "research", "SYNTHESIS.md")

SECTION = re.compile(r"^## (\d+)\. ")
ITEM = re.compile(r"^(\d+)\. ")
CODE_SPAN = re.compile(r"`+[^`]*`+")
MARKERS = ["MOOT", "ANSWERED", "CLOSED", "RESOLVED", "REOPENED", "WITHDRAWN",
           "SUPERSEDED", "REFUTED"]
CLAIM = re.compile(
    r"\b(question|discipline)\s+(\d{1,4})\b(?![\w.])(?P<mid>[^.;|]{0,60}?)\b(?P<mk>%s)\b"
    % "|".join(MARKERS), re.I)
NEGATION = re.compile(r"\b(cannot|can't|not|never|no longer|still|un)\b", re.I)


def load():
    return io.open(SYN, encoding="utf-8", newline="").read() \
        .replace("\r\n", "\n").split("\n")


def sections(lines):
    out, cur = {}, 0
    for i, l in enumerate(lines):
        m = SECTION.match(l)
        if m:
            cur = int(m.group(1))
        out[i] = cur
    return out


def spans(lines, sec, stop_at_blank):
    """stop_at_blank=True  -> invariant B's rule (blank line ends the item)
       stop_at_blank=False -> semantic rule (next numbered item ends the item)"""
    n, i = len(lines), 0
    while i < n:
        m = ITEM.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n:
            if lines[j].startswith("## "):
                break
            if ITEM.match(lines[j]):
                break
            if stop_at_blank and not lines[j].strip():
                break
            j += 1
        yield int(m.group(1)), i, j, sec[i]
        i = max(j, i + 1)


def main():
    lines = load()
    sec = sections(lines)
    b_spans = list(spans(lines, sec, True))
    s_spans = list(spans(lines, sec, False))

    # --- reconcile the naive number ---
    print("naive `**` counting, several units")
    for label, secs in (("SYNTHESIS 5 only", (5,)), ("SYNTHESIS 10 only", (10,)),
                        ("5 + 10", (5, 10))):
        lines_odd = items_odd = 0
        for num, a, b, s in b_spans:
            if s not in secs:
                continue
            o = sum(1 for k in range(a, b) if lines[k].count("**") % 2)
            lines_odd += o
            items_odd += 1 if o else 0
        print("   %-18s odd lines=%-5d items with an odd line=%d"
              % (label, lines_odd, items_odd))
    print("   -> the orchestrator's 'about eighty' is closest to "
          "SYNTHESIS 5, items-with-an-odd-line")

    # --- invariant B under its own rule ---
    print("")
    print("invariant B, item-grouped (blank-terminated), code spans stripped")
    for label, secs in (("SYNTHESIS 5", (5,)), ("SYNTHESIS 10", (10,))):
        bad = [(n, a + 1) for n, a, b, s in b_spans if s in secs
               and CODE_SPAN.sub("", "\n".join(lines[a:b])).count("**") % 2]
        print("   %-14s unbalanced: %d %s" % (label, len(bad), bad[:6]))

    # --- how many items have blank-line-separated continuation paragraphs? ---
    orphan = 0
    for idx, (n, a, b, s) in enumerate(b_spans):
        if s not in (5, 10):
            continue
        nxt = b
        while nxt < len(lines) and not lines[nxt].strip():
            nxt += 1
        if nxt < len(lines) and lines[nxt].startswith(("    ", "\t")) \
                and not ITEM.match(lines[nxt]):
            orphan += 1
    print("")
    print("items whose text continues after a blank line: %d" % orphan)
    print("   (invariant B does not see those trailing paragraphs at all)")

    # --- status claims, corrected body extent ---
    body = {}
    for num, a, b, s in s_spans:
        if s in (5, 10):
            body.setdefault((s, num), "\n".join(lines[a:b]))
    kind_sec = {"question": 10, "discipline": 5}
    tot = agree = 0
    neg = []
    real = []
    for i, line in enumerate(lines):
        for m in CLAIM.finditer(CODE_SPAN.sub("", line)):
            kind, n = m.group(1).lower(), int(m.group(2))
            mk = m.group("mk").upper()
            txt = body.get((kind_sec[kind], n))
            if txt is None:
                continue
            tot += 1
            if re.search(r"\b%s\b" % mk, txt, re.I):
                agree += 1
            elif NEGATION.search(m.group("mid")) or NEGATION.search(
                    line[max(0, m.start() - 40):m.start()]):
                neg.append((i + 1, kind, n, mk, m.group(0)[:70]))
            else:
                real.append((i + 1, kind, n, mk, m.group(0)[:70]))
    print("")
    print("status claims, body extended through blank-line paragraphs")
    print("   examined                     : %d" % tot)
    print("   item carries the marker      : %d" % agree)
    print("   negated / hedged prose       : %d" % len(neg))
    print("   marker genuinely absent      : %d" % len(real))
    for line, kind, n, mk, raw in neg:
        print("     NEG  L%-6d %s %-4d %-9s %s" % (line, kind, n, mk, raw))
    for line, kind, n, mk, raw in real:
        print("     ABS  L%-6d %s %-4d %-9s %s" % (line, kind, n, mk, raw))


if __name__ == "__main__":
    main()
