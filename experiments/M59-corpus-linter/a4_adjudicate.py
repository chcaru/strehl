"""M59 pass 7: adjudicate A4's six residual claims by hand, printing the fact
row and the §10 item side by side.

The orchestrator asks whether A4 should be promoted from advisory to a failing
check, on the grounds that the inconsistency class now has at least three real
instances. A rate cannot answer that. Each residual has to be read.

Read-only. Run: python experiments/M59-corpus-linter/a4_adjudicate.py
"""
import os
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import corpus_lint as cl                                    # noqa: E402


def wrap(label, text, width=104):
    body = re.sub(r"\s+", " ", text).strip()
    out = textwrap.wrap(body, width - 6) or [""]
    print("   %-6s %s" % (label, out[0]))
    for line in out[1:6]:
        print("          %s" % line)
    if len(out) > 6:
        print("          ... (%d more lines)" % (len(out) - 6))


def main():
    syn = cl.Doc(ROOT, cl.SYNTHESIS)
    index = cl.Index(syn, cl.Doc(ROOT, cl.AGENTS))
    for v in cl.advisory_a4_status_coherence(index):
        m = re.search(r"says (question|discipline) (\d+) is (\w+)", v.message)
        kind, num, marker = m.group(1), int(m.group(2)), m.group(3)
        sec = 10 if kind == "question" else 5
        print("=" * 110)
        print("CLAIM at line %d: %r  -> asserts %s %d is %s"
              % (v.line, v.text, kind, num, marker))
        print("=" * 110)
        wrap("row", syn.lines[v.line - 1])
        body = index.item_body(sec, num)
        wrap("§%d" % sec, body)
        markers = sorted(set(w for w in cl.STATUS_MARKERS
                             if re.search(r"\b%s\b" % w, body, re.I)))
        amend = sorted(set(w for w in cl.AMENDMENT_MARKERS
                           if re.search(r"\b%s\b" % w, body, re.I)))
        print("   status words present in the item : %s" % (markers or "NONE"))
        print("   amendment words present          : %s" % (amend or "NONE"))
        print("")


if __name__ == "__main__":
    main()
