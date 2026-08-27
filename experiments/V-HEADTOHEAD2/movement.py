"""movement.py -- which PUBLISHED numbers move under the sign repair?

Deliverable 3 of the mask audit: "If published numbers move, say which and by
how much, and mark them at the source."  Doing that by eye over eight log
diffs is how a number gets missed, so this does it mechanically:

  1. diff each published log against its post-repair re-run
  2. pull every numeric token that changed
  3. grep README.md and docs/research/V-HEADTOHEAD2.md for that token

Anything that survives all three steps is a number a reader can see today and
which is now wrong.  Anything that changes but is not cited anywhere is noted
as internal.

Usage:  python movement.py
"""
import os
import re
import sys

LOGS = "logs"
DOCS = [r"..\..\README.md", r"..\..\docs\research\V-HEADTOHEAD2.md"]
PAIRS = [("h2h2-113", "resign-h2h2-113"), ("h2h2-cb", "resign-h2h2-cb"),
         ("h2h2b-113", "resign-h2h2b-113"), ("h2h2b-cb", "resign-h2h2b-cb"),
         ("toneparity-113", "resign-toneparity-113"),
         ("toneparity-cb", "resign-toneparity-cb"),
         ("grade-113", "resign-grade-113"), ("grade-cb", "resign-grade-cb")]

NUM = re.compile(r"\d+\.\d+(?:e[-+]\d+)?")


def toks(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return NUM.findall(f.read())


def vals(path):
    """Numeric VALUES, not text.  The first version of this compared literal
    tokens and would have missed the single most important number in the
    audit: the log prints `3.7147e-02` and README.md prints `0.037147`, which
    are the same number and share no substring.  Matching text where you mean
    to match quantity is the same defect as grepping for a claim and finding
    its retraction."""
    out = {}
    for t in toks(path):
        try:
            out.setdefault(float(t), set()).add(t)
        except ValueError:
            pass
    return out


def main():
    doc_vals = {}
    for d in DOCS:
        p = os.path.abspath(d)
        doc_vals[os.path.basename(p)] = vals(p)

    cited_moved = []
    internal = 0
    for old, new in PAIRS:
        po = os.path.join(LOGS, old + ".txt")
        pn = os.path.join(LOGS, new + ".txt")
        if not (os.path.exists(po) and os.path.exists(pn)):
            print("  MISSING %s / %s" % (po, pn))
            continue
        a, b = vals(po), vals(pn)
        gone = set(a) - set(b)
        for v in sorted(gone):
            # 4+ significant digits, so 1.0 / 100.0 / 2.4 cannot collide by
            # accident with unrelated prose
            digits = len(("%r" % v).replace("-", "").replace(".", "")
                         .split("e")[0].lstrip("0"))
            if digits < 4:
                continue
            hits = [n for n, dv in doc_vals.items() if v in dv]
            if hits:
                forms = sorted(set().union(*[doc_vals[n][v] for n in hits]))
                cited_moved.append((old, v, sorted(a[v])[0], forms,
                                    ",".join(hits)))
            else:
                internal += 1

    print("=" * 78)
    print("PUBLISHED NUMBERS THAT MOVE UNDER THE SIGN REPAIR")
    print("=" * 78)
    if not cited_moved:
        print("  none -- no changed value appears in README.md or "
              "V-HEADTOHEAD2.md")
    for log, v, logform, forms, where in cited_moved:
        print("  %-16s %-12s printed as %-22s in %s"
              % (log, logform, "/".join(forms), where))
    print("\n  %d further values changed but are cited in neither document "
          "(internal to the logs)" % internal)
    print("  partition: %d cited + %d internal = %d changed values"
          % (len(cited_moved), internal, len(cited_moved) + internal))
    return 0


if __name__ == "__main__":
    sys.exit(main())
