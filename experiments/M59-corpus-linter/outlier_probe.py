"""M59 pass 6: locate the outliers pass 5 found, and re-measure A4 for the
promotion decision the orchestrator asked for.

Pass 5 found:
  - 4 backticks left over by the code-span stripper on non-fenced SYNTHESIS
    lines, but 0 inside any unit S5 checks. Where are they?
  - 1 fact row with an odd single-`*` count.
  - 17 units with an odd single-`_`, as expected from identifiers.

Read-only. Run: python experiments/M59-corpus-linter/outlier_probe.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import corpus_lint as cl                                    # noqa: E402


def main():
    syn = cl.Doc(ROOT, cl.SYNTHESIS)
    agents = cl.Doc(ROOT, cl.AGENTS)
    index = cl.Index(syn, agents)

    print("A  backtick residue on non-fenced SYNTHESIS lines")
    sec_of = {}
    cur = 0
    for i, line in enumerate(syn.lines):
        m = re.match(r"^## (\d+)\. ", line)
        if m:
            cur = int(m.group(1))
        sec_of[i] = cur
    for i, line in enumerate(syn.lines):
        if syn.fenced[i]:
            continue
        left = cl.strip_code_spans(line).count("`")
        if left:
            print("   L%-6d §%-3d residue=%d" % (i + 1, sec_of[i], left))
            print("      %s" % line.strip()[:150])

    print("")
    print("B  the odd single-`*` unit")
    pat = re.compile(r"(?<!\*)\*(?!\*)")
    for num, line in index.fact_rows_all:
        raw = syn.lines[line - 1]
        hits = pat.findall(cl.strip_code_spans(raw))
        if len(hits) % 2:
            print("   fact %d, L%d, %d single-`*`" % (num, line, len(hits)))
            for m in pat.finditer(cl.strip_code_spans(raw)):
                s = cl.strip_code_spans(raw)
                print("      ...%s..." % s[max(0, m.start() - 45):m.start() + 45])

    print("")
    print("C  a sample of the odd single-`_` units, to show why it is unshippable")
    upat = re.compile(r"(?<!_)_(?!_)")
    shown = 0
    for name, line, text in [("fact %d" % n, l, syn.lines[l - 1])
                             for n, l in index.fact_rows_all]:
        hits = upat.findall(cl.strip_code_spans(text))
        if len(hits) % 2 and shown < 4:
            shown += 1
            s = cl.strip_code_spans(text)
            snippets = [s[max(0, m.start() - 30):m.start() + 30]
                        for m in upat.finditer(s)]
            print("   %s L%d: %s" % (name, line, " || ".join(snippets[:3])))

    print("")
    print("D  A4 status coherence, re-measured at this HEAD")
    adv = cl.advisory_a4_status_coherence(index)
    print("   residual claims: %d" % len(adv))
    for v in adv:
        print("     L%-6d %s" % (v.line, v.text))

    pat2 = re.compile(
        r"\b(question|discipline)\s+(\d{1,4})\b(?![\w.])(?P<mid>[^.;|]{0,60}?)"
        r"\b(?P<mk>%s)\b" % "|".join(cl.STATUS_MARKERS), re.I)
    total = corrob = struck = negd = 0
    negation = re.compile(r"\b(cannot|can't|not|never|no longer|still|un)\b", re.I)
    kind_section = {"question": 10, "discipline": 5}
    for i, line in enumerate(syn.lines):
        if syn.fenced[i]:
            continue
        bare = cl.strip_code_spans(line)
        visible = cl.STRIKETHROUGH.sub("", bare)
        for m in pat2.finditer(bare):
            kind = m.group(1).lower()
            body = index.item_body(kind_section[kind], int(m.group(2)))
            if not body:
                continue
            total += 1
            if re.search(r"\b%s\b" % m.group("mk").upper(), body, re.I):
                corrob += 1
            elif m.group(0) not in visible:
                struck += 1
            elif negation.search(m.group("mid")) or \
                    negation.search(bare[max(0, m.start() - 40):m.start()]):
                negd += 1
    print("   claims found %d | corroborated %d | struck %d | negated %d | residual %d"
          % (total, corrob, struck, negd, len(adv)))
    if total:
        print("   residual rate: %d/%d = %.0f%%" % (len(adv), total,
                                                    100.0 * len(adv) / total))


if __name__ == "__main__":
    main()
