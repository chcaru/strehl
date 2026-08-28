"""Audit every section verifier in this lane for conclusion blindness.

WHY THIS EXISTS
---------------
ORCH circulated an instrument defect found in another lane: a report verifier
that tested for the PRESENCE of the word "refuted" in a section, so reversing
that section's verdict to "confirmed" -- while leaving every number in the
document intact -- passed 712 green checks. A second lane then found four
conclusion-flip arms MISSED at 88/88 green, one of which re-licensed an arm that
lane had just withdrawn.

`83-audit-conclusions.py` ran that probe against the section-22 verifier and
found it blind on five of six conclusions. That repaired one verifier. It said
nothing about the other three, which are older and were written before anybody
in this build knew the defect class existed. This script measures all four.

WHAT MAKES THIS DIFFERENT FROM 83
---------------------------------
83 imports the section-22 verifier and calls `verify()` directly. That is fine
for a verifier whose internals it can reach, but three of the four older
verifiers expose no such function -- they are `main()` and an exit code. So this
script drives the SHIPPED ENTRY POINT: it mutates the real document on disk,
runs `python <verifier>` as a subprocess exactly as a person would, and reads
the exit code. That is a stronger test than 83's, because it exercises the thing
that actually gates the report rather than a function underneath it.

Mutating the real document is the dangerous part, so: the original bytes are
copied to %TEMP% before anything is written, every write is undone in a
`finally`, and the restore is verified byte-identical before the script is
allowed to exit successfully. Never `git checkout --`; that reverts to HEAD and
would silently destroy uncommitted work belonging to this lane or another.

WHY THE DETECTOR IS COMMISSIONED PER VERIFIER, NOT ASSUMED
----------------------------------------------------------
"The verifier caught it" is read off the exit code. An exit code is an
instrument and it gets the same treatment as any other instrument here. If a
verifier's exit code were wired to a constant zero, EVERY probe would read BLIND
-- alarming but harmless, because it errs toward finding fault with myself. The
dangerous direction is the opposite: a verifier that exits non-zero for some
incidental reason would make every probe read CAUGHT and manufacture a clean
bill of health. So each verifier faces a 2x2 before a single conclusion probe is
believed:

    clean document        -> must exit 0      (else the audit is unreadable)
    planted NUMBER defect -> must exit non-0  (the channel can express failure)
    innocuous prose edit  -> must exit 0      (the channel is not merely
                                               "something in the file changed")

A verifier failing any arm is reported UNCOMMISSIONED and its probes are counted
in their own bucket. They are never counted as passes. A probe that did not run
is not a probe that succeeded -- which is the same rule that caught 83 itself
reporting NO-BLIND-SPOT while two of its probes had never landed.

WHAT A PROBE IS ALLOWED TO BE
-----------------------------
A conclusion flip changes what the document CLAIMS while leaving every number it
states intact. "Zero of 98,898,048 samples differ" keeps both numbers; only
"the same image" becomes "different images". If a probe changes a digit it is
testing the numeric checks, which are already commissioned elsewhere, and it
tells us nothing new. Two probes below deliberately flip a verdict TOKEN inside
a quoted log block, which is the boundary case: a token is not a number, and a
doc-vs-log verifier ought to catch it.

Every anchor must occur EXACTLY ONCE in the document. An anchor that matches two
sites silently tests whichever comes first, which is how a negative control ends
up certifying a line nobody meant to examine.
"""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DOC = os.path.join(REPO, "docs", "research", "BUILD-DEFECT.md")
OUTD = os.path.join(HERE, "..", "out")
SRC = os.path.join("experiments", "BUILD-DEFECT", "src")

log = []


def emit(s=""):
    print(s)
    log.append(s)


# name -> (script, positive control, null control)
#
# The positive control mutates a digit the verifier is known to re-derive from
# its logs; the null control edits prose that carries no claim. Both are chosen
# per section because each verifier only reads its own section.
VERIFIERS = [
    ("s18", "45-verify-s18.py",
     ("-3.486%", "-3.487%"),
     ("rather than a shrug", "rather than a wave")),
    ("s20", "63-verify-s20.py",
     ("91.307 DN", "91.308 DN"),
     ("where the truth is genuinely clean", "where the truth is truly clean")),
    # `scanned 110538` was the first choice for the s20 positive control and it
    # read WRONG WAY -- exit 0 with a corrupted digit. That looked like a
    # verifier whose exit code was inert. It was not: 63 exits 1 on any
    # mismatch, but the partition line in 20.2 is prose it never re-derives, so
    # the plant was INERT rather than the instrument blind. An uncommissioned
    # control and a dead instrument produce the same reading, which is why the
    # control gets anchored on a value the verifier demonstrably parses --
    # `91.307 DN` is arm A's residual, extracted by `claim('arm A residual')`.
    ("s21", "73-verify-s21.py",
     ("451,463", "451,464"),
     ("the orchestrator's literal evidence pair",
      "the orchestrator's plain evidence pair")),
    ("s22", "82-verify-s22.py",
     ("31,792 DN", "31,793 DN"),
     ("A verifier can be exhaustive about numbers",
      "A verifier can be thorough about numbers")),
]

# (verifier, label, old, new) -- numbers preserved, claim reversed.
PROBES = [
    # -- section 18: which side of the optical path the motes are on --------
    ("s18", "18.5 mote 2 is on the sensor, not the filter",
     "It is in both.\nIt is not on the filter.**",
     "It is in one block only.\nIt is on the filter.**"),
    ("s18", "18.5 the bound points at the fixed path",
     "of mote 2 is in the fixed optical path.",
     "of mote 2 is on the removable filter."),
    ("s18", "18.5 quoted-log outcome token (Common -> Underpowered)",
     "-0.006   0.4487   Common",
     "-0.006   0.4487   Underpowered"),
    ("s18", "18.7 the open search found nothing",
     "carries no dust this instrument can see.**",
     "carries dust this instrument can see.**"),
    # -- section 20: where the failure was located --------------------------
    ("s20", "20.2 the failure is in the statistic, not the sensor",
     "with it, the failure is clearly in the statistic.",
     "with it, the failure is clearly in the sensor."),
    ("s20", "20.7 arm B is circular",
     "Arm B is circular, which is why arm F exists",
     "Arm B is independent, which is why arm F is redundant"),
    # -- section 21: whether --exposure did anything ------------------------
    ("s21", "21.2 different bytes, same image",
     "different bytes and the same image.",
     "different bytes and two different images."),
    ("s21", "21.2 the 1 DN pair is dither, not a small effect",
     "That is dither, and the",
     "That is a real effect, and the"),
    # -- section 22: re-tested through the shipped entry point --------------
    ("s22", "22.6 no delivered master moved",
     "disturbed none of them", "disturbed several of them"),
    ("s22", "22.3 direction of the improvement",
     "the substitution destroys it", "the substitution preserves it"),
]


def read_doc():
    with io.open(DOC, "rb") as fh:
        return fh.read()


def write_doc(data):
    with io.open(DOC, "wb") as fh:
        fh.write(data)


def run(script):
    """Run a verifier exactly as a person would. Returns its exit code."""
    p = subprocess.run([sys.executable, os.path.join(SRC, script)],
                       cwd=REPO, capture_output=True)
    return p.returncode


def mutate(original, old, new):
    """Apply one anchored substitution, or explain why it could not.

    Returns (bytes, None) or (None, reason). The count is checked before the
    substitution rather than after, because `bytes.replace(a, b, 1)` on a
    two-site anchor succeeds quietly on the wrong site.
    """
    ob, nb = old.encode("utf-8"), new.encode("utf-8")
    n = original.count(ob)
    if n == 0:
        return None, "anchor absent"
    if n > 1:
        return None, "anchor occurs %d times" % n
    return original.replace(ob, nb, 1), None


def commission(original, name, script, pos, null):
    """The 2x2. Returns (ok, list of lines describing each arm)."""
    lines = []
    ok = True

    code = run(script)
    lines.append("      clean                exit=%d  %s"
                 % (code, "ok" if code == 0 else "UNREADABLE"))
    if code != 0:
        return False, lines

    for label, (old, new), want_fail in (("planted number", pos, True),
                                         ("innocuous prose", null, False)):
        data, why = mutate(original, old, new)
        if data is None:
            lines.append("      %-20s SKIPPED (%s)" % (label, why))
            ok = False
            continue
        try:
            write_doc(data)
            code = run(script)
        finally:
            write_doc(original)
        good = (code != 0) if want_fail else (code == 0)
        lines.append("      %-20s exit=%d  %s" % (label, code,
                     "ok" if good else "WRONG WAY"))
        ok = ok and good
    return ok, lines


def main():
    emit("=== auditing every BUILD-DEFECT section verifier for conclusion "
         "blindness ===")
    emit()

    original = read_doc()
    backup = os.path.join(tempfile.gettempdir(), "BUILD-DEFECT.md.audit-bak")
    shutil.copyfile(DOC, backup)
    emit("  document  : %s (%d bytes)" % (os.path.relpath(DOC, REPO),
                                          len(original)))
    emit("  backup    : %s" % backup)
    emit()

    commissioned = {}
    try:
        emit("=== COMMISSIONING THE DETECTOR, PER VERIFIER ===")
        for name, script, pos, null in VERIFIERS:
            emit("  %-4s %s" % (name, script))
            ok, lines = commission(original, name, script, pos, null)
            for ln in lines:
                emit(ln)
            commissioned[name] = ok
            emit("      -> %s" % ("COMMISSIONED" if ok else "UNCOMMISSIONED"))
        emit()

        emit("=== CONCLUSION PROBES ===")
        caught = blind = unanchored = uncommissioned = 0
        for name, label, old, new in PROBES:
            if not commissioned.get(name):
                uncommissioned += 1
                emit("  UNCOMMISSIONED %-52s (%s detector not proven)"
                     % (label, name))
                continue
            data, why = mutate(original, old, new)
            if data is None:
                unanchored += 1
                emit("  UNANCHORED     %-52s %s" % (label, why))
                continue
            script = dict((v[0], v[1]) for v in VERIFIERS)[name]
            try:
                write_doc(data)
                code = run(script)
            finally:
                write_doc(original)
            if code != 0:
                caught += 1
                emit("  CAUGHT         %-52s" % label)
            else:
                blind += 1
                emit("  BLIND          %-52s conclusion reversed, %s still "
                     "exits 0" % (label, script))

        emit()
        emit("=== DELETION PROBES ===")
        # The polarity checks are written so that stating NEITHER form is
        # unresolved rather than a pass. That is a claim about the repair, and
        # it gets measured like any other: excise the conclusion outright and
        # require the verifier to object. If deletion were cheaper than being
        # wrong, the easiest route past a conclusion check would be to delete
        # the conclusion -- and a report that has quietly lost its findings
        # reads just as green as one that never had them.
        dcaught = dblind = dskipped = 0
        for name, label, old, new in PROBES:
            if "quoted-log" in label:
                dskipped += 1
                emit("  N/A            %-52s not a polarity check" % label)
                continue
            data, why = mutate(original, old, "")
            if data is None:
                dskipped += 1
                emit("  UNANCHORED     %-52s %s" % (label, why))
                continue
            script = dict((v[0], v[1]) for v in VERIFIERS)[name]
            try:
                write_doc(data)
                code = run(script)
            finally:
                write_doc(original)
            if code != 0:
                dcaught += 1
                emit("  CAUGHT         %-52s" % label)
            else:
                dblind += 1
                emit("  BLIND          %-52s conclusion DELETED, %s still "
                     "exits 0" % (label, script))
        emit("  %d deletions = %d caught + %d blind + %d n/a"
             % (len(PROBES), dcaught, dblind, dskipped))
        if dcaught + dblind + dskipped != len(PROBES):
            raise SystemExit("deletion partition does not sum")
    finally:
        write_doc(original)
        restored = read_doc()
        same = restored == original
        emit()
        emit("  document restored byte-identical: %s" % same)
        if not same:
            shutil.copyfile(backup, DOC)
            emit("  RESTORED FROM %s" % backup)
            raise SystemExit("document was not restored; recovered from backup")

    emit()
    emit("  %d probes = %d caught + %d blind + %d unanchored + %d "
         "uncommissioned"
         % (len(PROBES), caught, blind, unanchored, uncommissioned))
    if caught + blind + unanchored + uncommissioned != len(PROBES):
        raise SystemExit("partition does not sum")
    emit()

    # A probe that did not run is not a probe that passed.
    if blind or dblind:
        verdict = "BLIND ON %d CONCLUSION(S)" % (blind + dblind)
    elif unanchored or uncommissioned:
        verdict = ("INCONCLUSIVE -- %d probe(s) never ran"
                   % (unanchored + uncommissioned))
    else:
        verdict = "NO-BLIND-SPOT"
    emit("VERDICT: %s" % verdict)

    with io.open(os.path.join(OUTD, "84-audit-all.log"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(log) + "\n")
    return 2 if (blind or dblind or unanchored or uncommissioned) else 0


if __name__ == "__main__":
    sys.exit(main())
