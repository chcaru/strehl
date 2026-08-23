"""Second measurement pass, driven by what M58c H2 actually recorded.

M58c's three consequences of the discipline-170 slip:
  1. discipline 170's subject was corrupted   -- not machine-checkable
  2. its headline stopped rendering           -- invariant B catches this
  3. fact 771 asserted "Question 170 is MOOT" while SYNTHESIS 10's question 170
     carried no MOOT marker                   -- an EXISTENCE check does not
     catch this, because question 170 exists. A STATUS check does.

So this measures:
  A. naive `**` per ITEM (not per line) -- to reconcile with the "about eighty"
     the orchestrator measured, since per-line I get 320.
  B. numbered items per section, to find which sections are genuinely empty and
     can therefore carry a zero-base-rate placement check.
  C. the base rate of "Question N is <MARKER>" claims whose SYNTHESIS 10 item
     does not carry that marker. If this is noisy it cannot be a failing check.

Read-only. Run: python experiments/M59-corpus-linter/inv_probe2.py
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
CODE_SPAN = re.compile(r"`+[^`]*`+")
MARKERS = ["MOOT", "ANSWERED", "CLOSED", "RESOLVED", "REOPENED", "WITHDRAWN",
           "SUPERSEDED", "REFUTED"]
CLAIM = re.compile(
    r"\b(question|discipline)\s+(\d{1,4})\b(?![\w.])(?P<mid>[^.;|]{0,60}?)\b(?P<mk>%s)\b"
    % "|".join(MARKERS), re.I)


def main():
    lines = io.open(SYN, encoding="utf-8", newline="").read() \
        .replace("\r\n", "\n").split("\n")
    sec, cur = {}, 0
    for i, l in enumerate(lines):
        m = SECTION.match(l)
        if m:
            cur = int(m.group(1))
        sec[i] = cur

    def item_spans():
        n, i = len(lines), 0
        while i < n:
            m = ITEM.match(lines[i])
            if not m:
                i += 1
                continue
            j = i + 1
            while j < n and lines[j].strip() and not ITEM.match(lines[j]) \
                    and not lines[j].startswith("## "):
                j += 1
            yield int(m.group(1)), i, j, sec[i]
            i = j

    spans = list(item_spans())

    # --- A: naive per-ITEM (any constituent line odd) vs per-LINE ---
    per_line = per_item = 0
    for num, a, b, s in spans:
        if s not in (5, 10):
            continue
        odd_lines = sum(1 for k in range(a, b) if lines[k].count("**") % 2)
        per_line += odd_lines
        if odd_lines:
            per_item += 1
    print("A  naive `**` counting, SYNTHESIS 5 + 10 only")
    print("     odd LINES                       : %d" % per_line)
    print("     ITEMS with >=1 odd line         : %d" % per_item)
    # naive per item, joined but NOT code-stripped
    joined_no_strip = 0
    for num, a, b, s in spans:
        if s in (5, 10) and "\n".join(lines[a:b]).count("**") % 2:
            joined_no_strip += 1
    print("     ITEMS unbalanced when joined but code spans NOT stripped: %d"
          % joined_no_strip)
    print("     -> the code-span strip is worth %d false positive(s)" % joined_no_strip)

    # --- B: numbered items per section ---
    print("")
    print("B  numbered items per section")
    by_sec = Counter(s for _, _, _, s in spans)
    all_secs = sorted(set(sec.values()) - {0})
    for s in all_secs:
        print("     section %-3d %s" % (s, by_sec.get(s, 0)))
    empty = [s for s in all_secs if by_sec.get(s, 0) == 0]
    print("     sections with ZERO numbered items: %s" % empty)

    # --- C: status-claim coherence ---
    print("")
    print("C  `<kind> N ... <MARKER>` claims vs the item's own text")
    body = {}
    for num, a, b, s in spans:
        if s in (5, 10):
            body.setdefault((s, num), "\n".join(lines[a:b]))
    kind_sec = {"question": 10, "discipline": 5}
    total = agree = disagree = 0
    rows = []
    for i, line in enumerate(lines):
        stripped = CODE_SPAN.sub("", line)
        for m in CLAIM.finditer(stripped):
            kind = m.group(1).lower()
            n = int(m.group(2))
            mk = m.group("mk").upper()
            s = kind_sec[kind]
            txt = body.get((s, n))
            if txt is None:
                continue
            total += 1
            if re.search(r"\b%s\b" % mk, txt):
                agree += 1
            else:
                disagree += 1
                rows.append((i + 1, sec[i], kind, n, mk, m.group(0)[:78]))
    print("     claims examined      : %d" % total)
    print("     item carries marker  : %d" % agree)
    print("     item does NOT        : %d" % disagree)
    for line, s, kind, n, mk, raw in rows[:25]:
        print("       L%-6d (section %-2d) %s %d -> %-9s | %s" % (line, s, kind, n, mk, raw))

    # --- D: does the existing C1 tokenizer see capitalised "Question N"? ---
    print("")
    print("D  tokenizer check on capitalised references")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import corpus_lint as CL

    class FakeDoc(object):
        def __init__(self, text):
            self.text = text
            self.lines = text.split("\n")

    sample = "Question 170 is **MOOT**, and Discipline 170 is unrelated."
    for kind, num, off, raw, klass in CL.iter_citations(FakeDoc(sample)):
        print("     %-10s %-5d %-16r class=%s" % (kind, num, raw, klass))


if __name__ == "__main__":
    main()
