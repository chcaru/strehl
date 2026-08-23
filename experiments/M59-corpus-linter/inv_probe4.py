"""Fourth pass, two questions the implementation still depends on.

  1. Invariant B's item rule stops at a blank line, so the 5 items that continue
     in a separate indented paragraph have text B never sees. Are those trailing
     paragraphs balanced? If yes, checking them too is free coverage; if no, I
     have found something.
  2. Two of the 7 residual status-claim hits are inside `~~strikethrough~~`
     (fact 622's repaired consequence cell). Does stripping strikethrough as
     well as code spans clear them? That decides whether the residual is 7 or 5,
     which is the difference between "noisy" and "very noisy" -- neither is
     shippable as a failing check, but the report should state the true number.

Read-only. Run: python experiments/M59-corpus-linter/inv_probe4.py
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
STRIKE = re.compile(r"~~.*?~~", re.S)
MARKERS = ["MOOT", "ANSWERED", "CLOSED", "RESOLVED", "REOPENED", "WITHDRAWN",
           "SUPERSEDED", "REFUTED"]
CLAIM = re.compile(
    r"\b(question|discipline)\s+(\d{1,4})\b(?![\w.])(?P<mid>[^.;|]{0,60}?)\b(?P<mk>%s)\b"
    % "|".join(MARKERS), re.I)
NEGATION = re.compile(r"\b(cannot|can't|not|never|no longer|still|un)\b", re.I)


def main():
    lines = io.open(SYN, encoding="utf-8", newline="").read() \
        .replace("\r\n", "\n").split("\n")
    sec, cur = {}, 0
    for i, l in enumerate(lines):
        m = SECTION.match(l)
        if m:
            cur = int(m.group(1))
        sec[i] = cur

    # --- 1: trailing continuation paragraphs ---
    print("1  paragraphs that belong to a numbered item but sit after a blank line")
    n = len(lines)
    i = 0
    orphans = []
    cur_item = None
    while i < n:
        m = ITEM.match(lines[i])
        if m and sec[i] in (5, 10):
            cur_item = (int(m.group(1)), sec[i])
            j = i + 1
            while j < n and lines[j].strip() and not ITEM.match(lines[j]) \
                    and not lines[j].startswith("## "):
                j += 1
            i = j
            continue
        if cur_item and lines[i].startswith(("    ", "\t")) and lines[i].strip():
            j = i
            while j < n and lines[j].strip():
                j += 1
            orphans.append((cur_item, i + 1, "\n".join(lines[i:j])))
            i = j
            continue
        if lines[i].startswith("## ") or (lines[i].strip() and
                                          not lines[i].startswith((" ", "\t"))):
            cur_item = None
        i += 1
    print("   found: %d" % len(orphans))
    bad = 0
    for (num, s), line, body in orphans:
        c = CODE_SPAN.sub("", body).count("**")
        flag = "UNBALANCED" if c % 2 else "ok"
        if c % 2:
            bad += 1
        print("   section %-2d item %-4d L%-6d lines=%-3d `**`=%-3d %s"
              % (s, num, line, body.count("\n") + 1, c, flag))
    print("   unbalanced trailing paragraphs: %d" % bad)

    # --- 2: status claims with strikethrough stripped too ---
    print("")
    print("2  status claims, code spans AND strikethrough stripped")
    body_of = {}
    i = 0
    while i < n:
        m = ITEM.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n and not lines[j].startswith("## ") and not ITEM.match(lines[j]):
            j += 1
        if sec[i] in (5, 10):
            body_of.setdefault((sec[i], int(m.group(1))), "\n".join(lines[i:j]))
        i = max(j, i + 1)

    kind_sec = {"question": 10, "discipline": 5}
    tot = agree = 0
    residual, dropped_strike, negated = [], [], []
    for k, line in enumerate(lines):
        clean = STRIKE.sub("", CODE_SPAN.sub("", line))
        raw_clean = CODE_SPAN.sub("", line)
        for m in CLAIM.finditer(raw_clean):
            kind, num = m.group(1).lower(), int(m.group(2))
            mk = m.group("mk").upper()
            txt = body_of.get((kind_sec[kind], num))
            if txt is None:
                continue
            tot += 1
            if re.search(r"\b%s\b" % mk, txt, re.I):
                agree += 1
            elif m.group(0) not in clean:
                dropped_strike.append((k + 1, kind, num, mk, m.group(0)[:64]))
            elif NEGATION.search(m.group("mid")) or NEGATION.search(
                    raw_clean[max(0, m.start() - 40):m.start()]):
                negated.append((k + 1, kind, num, mk, m.group(0)[:64]))
            else:
                residual.append((k + 1, kind, num, mk, m.group(0)[:64]))
    print("   examined                       : %d" % tot)
    print("   item carries the marker        : %d" % agree)
    print("   inside ~~strikethrough~~       : %d" % len(dropped_strike))
    print("   negated / hedged prose         : %d" % len(negated))
    print("   RESIDUAL (candidate defects)   : %d" % len(residual))
    for line, kind, num, mk, raw in dropped_strike:
        print("     STRIKE L%-6d %s %-4d %-9s %s" % (line, kind, num, mk, raw))
    for line, kind, num, mk, raw in negated:
        print("     NEG    L%-6d %s %-4d %-9s %s" % (line, kind, num, mk, raw))
    for line, kind, num, mk, raw in residual:
        print("     ABS    L%-6d %s %-4d %-9s %s" % (line, kind, num, mk, raw))
    if tot:
        print("   residual false-positive-or-defect rate: %d/%d = %.0f%%"
              % (len(residual), tot, 100.0 * len(residual) / tot))


if __name__ == "__main__":
    main()
