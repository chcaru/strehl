"""Audit 82-verify-s22.py for the conclusion-flip blind spot ORCH described.

Not an assertion that the verifier is blind -- a measurement of it. Each probe
flips a CONCLUSION in section 22 while leaving every number intact, then asks the
verifier for a verdict. A probe that passes is a conclusion the verifier cannot
defend, which is exactly the shape that let another lane's report survive
'refuted' -> 'confirmed' across 712 green checks.
"""
import importlib.util
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, "..", "out")
log = []


def emit(s=""):
    print(s)
    log.append(s)


spec = importlib.util.spec_from_file_location(
    "v82", os.path.join(HERE, "82-verify-s22.py"))
v82 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v82)

PROBES = [
    ("22.1 heading conclusion",
     "The negative control did not fire",
     "The negative control fired exactly as expected"),
    # The phrase wraps across a line in the source; a probe written as it READS
    # rather than as it is STORED does not land, and an unanchored probe is not
    # a pass. Anchored on the stored form.
    ("22.1 headline characterisation",
     "**accidentally\ncorrect**", "**actively\ndestructive**"),
    ("22.4 negative-control verdicts (RED/GREEN swapped)",
     "| pre-fix blob at `81ee69fa` | **RED**",
     "| pre-fix blob at `81ee69fa` | **GREEN**"),
    ("22.4 fixed-arm verdict",
     "| fixed working copy | **GREEN**", "| fixed working copy | **RED**"),
    ("22.1 pin row conclusion",
     "| pin `44C2F2CD2E5B2894` | `--srgb --exposure +2.61 --limit 8` (substituted) | 0 DN",
     "| pin `44C2F2CD2E5B2894` | `--srgb --exposure +2.61 --limit 8` (substituted) | 65,535 DN"),
    ("22.1 HEAD row substitution status",
     "(verbatim)", "(substituted)"),
    ("22.6 delivered conclusion sentence",
     "disturbed none of them", "disturbed several of them"),
    ("22.3 improvement direction",
     "the substitution destroys it", "the substitution preserves it"),
]


def main():
    base = v82.section22()
    emit("=== auditing the section-22 verifier for conclusion blindness ===")
    emit()
    ck0 = v82.verify(base, quiet=True)
    emit("  clean : %d matched + %d mismatched + %d unresolved"
         % (ck0.m, ck0.mm, ck0.un))
    if ck0.mm or ck0.un:
        raise SystemExit("clean section does not verify; audit is unreadable")
    emit()
    caught = blind = unanchored = ambiguous = 0
    for label, old, new in PROBES:
        n = base.count(old)
        if n == 0:
            unanchored += 1
            emit("  UNANCHORED %-46s %r absent" % (label, old[:40]))
            continue
        if n > 1:
            # A probe that lands on whichever copy comes first is not testing
            # the site it names. Require one site.
            ambiguous += 1
            emit("  AMBIGUOUS  %-46s anchor occurs %d times" % (label, n))
            continue
        ck = v82.verify(base.replace(old, new, 1), quiet=True)
        if ck.mm + ck.un > 0:
            caught += 1
            emit("  CAUGHT     %-46s" % label)
        else:
            blind += 1
            emit("  BLIND      %-46s conclusion flipped, verifier still PASSES"
                 % label)
    emit("  %d probes = %d caught + %d blind + %d unanchored + %d ambiguous"
         % (len(PROBES), caught, blind, unanchored, ambiguous))
    if caught + blind + unanchored + ambiguous != len(PROBES):
        raise SystemExit("partition does not sum")
    emit()
    # A probe that did not land is not a probe that passed. Reporting
    # NO-BLIND-SPOT while two probes never landed is the same defect this
    # script exists to find: a check that did not run reading as one that
    # succeeded.
    if blind:
        v = "BLIND ON %d CONCLUSION(S)" % blind
    elif unanchored or ambiguous:
        v = ("INCONCLUSIVE -- %d probe(s) never landed, so the verifier was "
             "not tested on them" % (unanchored + ambiguous))
    else:
        v = "NO-BLIND-SPOT"
    emit("VERDICT: %s" % v)
    with io.open(os.path.join(OUTD, "83-audit.log"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(log) + "\n")
    if blind or unanchored or ambiguous:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
