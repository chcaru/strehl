"""P45 -- verify every number in BUILD-DEFECT.md section 18 against the logs.

The rule this obeys: a checker that compares a document against constants
written in the checker verifies the checker.  Another lane ran 37/37 green and
then caught only 5 of 13 planted defects, because eight of its checks held their
own expected values.  So every pair below is (regex over the DOC, regex over the
LOG) and this file contains no measured value at all.

Each check is anchored on a neighbouring literal rather than on the bare number,
because a short token like `0.052` or `38` occurs by chance and a verifier that
matches the first occurrence is testing coincidence.

Summary partitions: total = agreed + disagreed + doc-not-found + log-not-found.
A check whose anchor fails to land is NOT a pass and is counted separately.

Run with --selftest to plant defects into a scratch copy of the document and
require this verifier to catch each one.  A regression check that has never been
shown to fail is a hypothesis.
"""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "research" / "BUILD-DEFECT.md"
OUT = ROOT / "experiments" / "BUILD-DEFECT" / "out"
LOG43 = OUT / "43-cpl-split.log"
LOG44 = OUT / "44-cpl-label.log"

# (label, doc-regex, which-log, log-regex)
# Both sides are patterns.  Group 1 of each is the value compared as text.
CHECKS = [
    ("mote1 block1 depth", r"   mote 1\s+(-[\d.]+)%\s+-[\d.]+%\s+\+[\d.]+\s+[\d.]+\s+Underpowered",
     43, r"mote 1\s+(-[\d.]+)%\s+-[\d.]+%\s+\+[\d.]+\s+[\d.]+\s+Underpowered"),
    ("mote1 block2 depth", r"   mote 1\s+-[\d.]+%\s+(-[\d.]+)%\s+\+[\d.]+\s+[\d.]+\s+Underpowered",
     43, r"mote 1\s+-[\d.]+%\s+(-[\d.]+)%\s+\+[\d.]+\s+[\d.]+\s+Underpowered"),
    ("mote2 block1 depth", r"   mote 2\s+(-[\d.]+)%\s+-[\d.]+%\s+-[\d.]+\s+[\d.]+\s+Common",
     43, r"mote 2\s+(-[\d.]+)%\s+-[\d.]+%\s+-[\d.]+\s+[\d.]+\s+Common"),
    ("mote2 block2 depth", r"   mote 2\s+-[\d.]+%\s+(-[\d.]+)%\s+-[\d.]+\s+[\d.]+\s+Common",
     43, r"mote 2\s+-[\d.]+%\s+(-[\d.]+)%\s+-[\d.]+\s+[\d.]+\s+Common"),
    ("G0 delta pp", r"`G0` \| nothing; block 1 odd vs even \| not block-specific \| Δ \*\*\+([\d.]+) pp\*\*",
     43, r"G0 placebo.*?DELTA \+([\d.]+) pp"),
    ("G0 p", r"`G0` \|.*?Δ \*\*\+[\d.]+ pp\*\*, p ([\d.]+)",
     43, r"G0 placebo.*?DELTA \+[\d.]+ pp\s+p ([\d.]+)"),
    ("G1 delta pp", r"`G1` \|.*?Δ \*\*−([\d.]+) pp\*\*",
     43, r"G1 planted.*?DELTA -([\d.]+) pp"),
    ("G2 delta pp", r"`G2` \|.*?Δ \*\*−([\d.]+) pp\*\*",
     43, r"G2 common.*?DELTA -([\d.]+) pp"),
    ("G2 p", r"`G2` \|.*?Δ \*\*−[\d.]+ pp\*\*, p ([\d.]+)",
     43, r"G2 common.*?DELTA -[\d.]+ pp\s+p ([\d.]+)"),
    ("G3 delta after", r"`G3` \|.*?Δ −[\d.]+ → \*\*\+([\d.]+) pp\*\*",
     43, r"DELTA -[\d.]+ -> \+([\d.]+) pp"),
    ("median shift", r"`\|median shift\| = ([\d.e-]+)`",
     43, r"plant equivalence: \|median shift\| = ([\d.e-]+)"),
    ("interior null p95", r"interior null\s+p95\s+([\d.]+) pp",
     43, r"DELTA null: n \d+\s+p50 [\d.]+ pp\s+p95 ([\d.]+) pp"),
    ("mote2 matched p95", r"\|\s*mote 2\s*\|\s*\*\*[\d.]+%\*\*\s*\|\s*([\d.]+) pp\s*\|",
     43, r"mote 2   edge-dist\s+\d+\s+matched null n=\d+\s+p95 ([\d.]+) pp"),
    ("mote1 matched p95", r"\|\s*mote 1\s*\|\s*[\d.]+%\s*\|\s*([\d.]+) pp\s*\|",
     43, r"mote 1   edge-dist\s+\d+\s+matched null n=\d+\s+p95 ([\d.]+) pp"),
    ("mote2 filter share", r"\|\s*mote 2\s*\|.*?\*\*≤ ([\d.]+)%\*\*",
     43, r"mote 2   edge-dist.*?bounds the filter-borne share at <= ([\d.]+)%"),
    ("mote1 filter share", r"\|\s*mote 1\s*\|.*?\*\*≤ ([\d.]+)%\*\*",
     43, r"mote 1   edge-dist.*?bounds the filter-borne share at <= ([\d.]+)%"),
    ("mote2 edge dist", r"mote 2 sits \*\*(\d+) quads\*\* from",
     43, r"mote 2   edge-dist\s+(\d+)"),
    ("search border", r"while `SEARCH_BORDER` is \*\*(\d+)\*\*",
     43, r"quads from every edge\n.*?rank|>= (\d+) quads from every edge"),
    ("sites scanned", r"scanned (\d+) sites -> 0 above the bar",
     43, r"scanned (\d+) sites -> 0 above the bar"),
    ("C1 spread", r"but spread \*\*([\d.]+) stops\*\*",
     43, r"C1: 9 of 9 steps finite, same side true, spread ([\d.]+) stops"),
    ("in-window count", r"Only\n\*\*(\d+) of 9\*\* steps have both blocks inside",
     44, r"partition: examined 9 = (\d+) in-window"),
    ("in-window spread", r"and there the spread is\n\*\*([\d.]+) stops\*\*",
     44, r"in-window ratio: mean [+-][\d.]+ stops, spread ([\d.]+) stops"),
    ("in-window stops", r"the in-window measurement is \*\*\+([\d.]+) stops\*\*",
     44, r"in-window ratio: mean \+([\d.]+) stops"),
    ("largest pause", r"\*\*(\d+) s, before `DSC00263`\*\*",
     44, r"largest      :\s+(\d+) s  before DSC00263"),
    ("next pause", r"next largest of the other 358 \| (\d+) s",
     44, r"next largest :\s+(\d+) s"),
    ("pause ratio", r"11 s → \*\*([\d.]+)×\*\*",
     44, r"ratio        : ([\d.]+)x"),
    ("clip level", r"\*\*([\d.]+) of range in block 2\*\*",
     44, r"1/5\s+[\d.]+\s+([\d.]+)\s"),
    ("floor level", r"and 1/250 s reads \*\*([\d.]+) in block 1\*\*",
     44, r"1/250\s+([\d.]+)\s"),
    ("sweep cpl time", r"`WITH cpl` (\d\d:\d\d:\d\d) →",
     44, r"(\d\d:\d\d:\d\d) \.\. \d\d:\d\d:\d\d   subject sweep WITH cpl"),
    ("sweep nocpl time", r"→ `NO cpl` (\d\d:\d\d:\d\d)",
     44, r"(\d\d:\d\d:\d\d) \.\. \d\d:\d\d:\d\d   subject sweep NO cpl"),
    # Section 18.6 restates both p95 values in its own code block. A value with
    # two sites in one document needs two anchors, or a check is satisfied by
    # the copy it is not testing -- which is how the first run of this selftest
    # missed a planted defect in exactly this block.
    ("s18.6 interior p95", r"  interior null           p95  ([\d.]+) pp",
     43, r"DELTA null: n \d+\s+p50 [\d.]+ pp\s+p95 ([\d.]+) pp"),
    ("s18.6 matched p95", r"  edge-matched at 38      p95  ([\d.]+) pp",
     43, r"mote 2   edge-dist\s+\d+\s+matched null n=\d+\s+p95 ([\d.]+) pp"),
]

# Checks whose doc value is DERIVED from two log values rather than copied from
# one. Verified by recomputing, not by matching a string.
DERIVED = [
    ("s18.6 widening ratio",
     r"  edge-matched at 38      p95  [\d.]+ pp     ([\d.]+)x wider",
     43, r"DELTA null: n \d+\s+p50 [\d.]+ pp\s+p95 ([\d.]+) pp",
     43, r"mote 2   edge-dist\s+\d+\s+matched null n=\d+\s+p95 ([\d.]+) pp",
     lambda a, b: round(b / a, 1)),
    ("mote2 filter-borne bound",
     r"\|\s*mote 2\s*\|\s*\*\*([\d.]+)%\*\*\s*\|",
     43, r"mote 2\s+-[\d.]+%\s+(-[\d.]+)%\s+-[\d.]+\s+[\d.]+\s+Common",
     43, r"mote 2\s+-[\d.]+%\s+(-[\d.]+)%\s+-[\d.]+\s+[\d.]+\s+Common",
     lambda a, b: round(abs(a), 3)),
]


# CONCLUSIONS -- what the numbers are HELD TO MEAN.
#
# Everything above compares a number in the report against a number in a log.
# `84-audit-conclusions-all.py` measured what that leaves uncovered: reversing
# "It is not on the filter" to "It is on the filter", flipping the bound from
# the fixed path to the removable filter, and turning "The CPL carries no dust"
# into "The CPL carries dust" each left every number in section 18 correct, and
# this verifier exited 0 on all three. Section 18's entire result is a claim
# about WHICH SIDE OF THE OPTICAL PATH the motes are on; a verifier blind to
# that certifies the arithmetic of a finding it cannot read.
#
# Each entry names the two opposed forms and re-derives which one is true from
# log 43. Stating both, or neither, counts as doc-not-found rather than as
# agreement -- deleting a conclusion must not be cheaper than getting it wrong.
# The doc side is matched against whitespace-normalised text because these
# sentences wrap, and a probe written the way a sentence reads rather than the
# way it is stored reports a false absence.
CONCLUSIONS = [
    ("s18.5 mote 2 not on filter",
     "It is in both. It is not on the filter.",
     "It is on the filter.",
     43, r"mote 2\s+-[\d.]+%\s+-[\d.]+%\s+[-+][\d.]+\s+[\d.]+\s+(\w+)",
     lambda outcome: outcome == "Common"),
    ("s18.5 bound is fixed-path",
     "of mote 2 is in the fixed optical path.",
     "of mote 2 is on the removable filter.",
     43, r"mote 2\s+edge-dist\s+\d+\s+matched null n=\d+\s+p95 ([\d.]+) pp"
         r"\s+DELTA ([-+][\d.]+) pp",
     lambda p95, delta: abs(float(delta)) < float(p95)),
    ("s18.7 CPL carries no dust",
     "carries no dust this instrument can see.",
     "carries dust this instrument can see.",
     43, r"scanned \d+ sites -> (\d+) above the bar",
     lambda n: int(n) == 0),
]


def run(doc_text, log43, log44, verbose=True):
    agreed = disagreed = doc_missing = log_missing = 0
    for label, dre, which, lre in CHECKS:
        text = log43 if which == 43 else log44
        dm = re.search(dre, doc_text, re.S)
        lm = re.search(lre, text, re.S)
        if not dm:
            doc_missing += 1
            if verbose:
                print(f"  DOC-NOT-FOUND  {label}")
            continue
        if not lm:
            log_missing += 1
            if verbose:
                print(f"  LOG-NOT-FOUND  {label}")
            continue
        d, l = dm.group(1), lm.group(1)
        if float(d) == float(l) if _numeric(d) and _numeric(l) else d == l:
            agreed += 1
            if verbose:
                print(f"  ok             {label:<22} {d}")
        else:
            disagreed += 1
            if verbose:
                print(f"  DISAGREE       {label:<22} doc={d}  log={l}")
    total = len(CHECKS) + len(DERIVED) + len(CONCLUSIONS)
    for label, dre, w1, l1re, w2, l2re, fn in DERIVED:
        t1 = log43 if w1 == 43 else log44
        t2 = log43 if w2 == 43 else log44
        dm = re.search(dre, doc_text, re.S)
        m1 = re.search(l1re, t1, re.S)
        m2 = re.search(l2re, t2, re.S)
        if not dm:
            doc_missing += 1
            if verbose:
                print(f"  DOC-NOT-FOUND  {label}")
            continue
        if not (m1 and m2):
            log_missing += 1
            if verbose:
                print(f"  LOG-NOT-FOUND  {label}")
            continue
        want = fn(float(m1.group(1)), float(m2.group(1)))
        if abs(float(dm.group(1)) - want) < 1e-9:
            agreed += 1
            if verbose:
                print(f"  ok (derived)   {label:<22} {dm.group(1)}")
        else:
            disagreed += 1
            if verbose:
                print(f"  DISAGREE       {label:<22} doc={dm.group(1)}  recomputed={want}")

    flat = re.sub(r"\s+", " ", doc_text)
    for label, yes, no, which, lre, fn in CONCLUSIONS:
        text = log43 if which == 43 else log44
        lm = re.search(lre, text, re.S)
        if not lm:
            log_missing += 1
            if verbose:
                print(f"  LOG-NOT-FOUND  {label}")
            continue
        truth = fn(*lm.groups())
        y, n = yes in flat, no in flat
        if y == n:
            doc_missing += 1
            if verbose:
                state = "states both forms" if y else "states neither form"
                print(f"  DOC-NOT-FOUND  {label:<22} {state}")
            continue
        if y == truth:
            agreed += 1
            if verbose:
                print(f"  ok (conclusion){label:<22} {'affirmed' if y else 'denied'}")
        else:
            disagreed += 1
            if verbose:
                print(f"  DISAGREE       {label:<22} doc says "
                      f"{'yes' if y else 'no'}, log 43 says "
                      f"{'yes' if truth else 'no'}")

    print(
        f"\n  partition: {total} checks = {agreed} agreed + {disagreed} disagreed"
        f" + {doc_missing} doc-not-found + {log_missing} log-not-found"
    )
    assert agreed + disagreed + doc_missing + log_missing == total, "partition does not sum"
    return agreed, disagreed, doc_missing, log_missing


def _numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def selftest():
    """Plant defects into a scratch copy and require each to be caught.

    Every mutation is anchored on a UNIQUE full-line string and hard-errors if
    the anchor does not land -- a bare replace() that silently matches nothing
    produces a green run that means nothing.
    """
    doc = DOC.read_text(encoding="utf-8", errors="replace")
    log43 = LOG43.read_text(encoding="utf-8", errors="replace")
    log44 = LOG44.read_text(encoding="utf-8", errors="replace")

    plants = [
        ("mote2 depth flipped",
         "| mote 2 | **3.486%** | 0.052 pp | −0.006 pp | **≤ 1.50%** |",
         "| mote 2 | **3.486%** | 0.052 pp | −0.006 pp | **≤ 9.99%** |"),
        ("G1 magnitude softened",
         "| `G1` | −4% disc in block 2 only | block-specific | Δ **−3.953 pp**, p 0.0000 | **PASS** |",
         "| `G1` | −4% disc in block 2 only | block-specific | Δ **−1.111 pp**, p 0.0000 | **PASS** |"),
        ("pause exaggerated",
         "| largest pause inside the 360 flats | **58 s, before `DSC00263`** |",
         "| largest pause inside the 360 flats | **99 s, before `DSC00263`** |"),
        ("edge null understated",
         "  edge-matched at 38      p95  0.052 pp     2.1x wider",
         "  edge-matched at 38      p95  0.025 pp     2.1x wider"),
        ("scan count inflated",
         "   scanned 469792 sites -> 0 above the bar -> 0 after suppression",
         "   scanned 999999 sites -> 0 above the bar -> 0 after suppression"),
        ("C1 spread hidden",
         "**`C1` FAILED.** Same side at 9 of 9, but spread **2.130 stops**, so per the",
         "**`C1` FAILED.** Same side at 9 of 9, but spread **0.130 stops**, so per the"),
    ]

    caught = missed = 0
    for name, old, new in plants:
        if old not in doc:
            raise SystemExit(
                f"MUTATION TARGET NOT FOUND for '{name}':\n  {old!r}\n"
                "The instrument is not commissioned; fix the anchor before trusting a green run."
            )
        mutated = doc.replace(old, new, 1)
        if mutated == doc:
            raise SystemExit(f"mutation '{name}' was a no-op")
        print(f"\n--- planted: {name} ---")
        a, d, dm, lm = run(mutated, log43, log44, verbose=False)
        if d > 0:
            caught += 1
            print(f"  RED as required ({d} disagreement(s))")
        else:
            missed += 1
            print("  GREEN -- DEFECT MISSED. This verifier is blind to it.")
    print(f"\n  selftest: {len(plants)} plants = {caught} caught + {missed} missed")
    return missed == 0


def main():
    for p in (DOC, LOG43, LOG44):
        if not p.exists():
            raise SystemExit(f"HALT: {p} missing")
    doc = DOC.read_text(encoding="utf-8", errors="replace")
    log43 = LOG43.read_text(encoding="utf-8", errors="replace")
    log44 = LOG44.read_text(encoding="utf-8", errors="replace")

    print("== P45 -- section 18 numbers vs the logs ==")
    print("   no measured value is written in this file; both sides are parsed.\n")
    a, d, dm, lm = run(doc, log43, log44)
    clean = d == 0 and dm == 0 and lm == 0

    if "--selftest" in sys.argv:
        print("\n== commissioning: plant defects, require RED ==")
        ok = selftest()
        print(f"\n== verdict: live {'GREEN' if clean else 'RED'}, "
              f"commissioning {'PASSED' if ok else 'FAILED'} ==")
        sys.exit(0 if (clean and ok) else 1)

    print(f"\n== verdict: {'GREEN' if clean else 'RED'} ==")
    sys.exit(0 if clean else 1)


if __name__ == "__main__":
    main()
