#!/usr/bin/env python3
"""Commission the STATUS 2.9.82 pins added to v2954.py.

WHAT IS BEING GUARDED. Section 2.9.82 records two corrections to the program
board and one derivation, all resting on lane M136's committed execution
assessment (`docs/research/M136-m8-v15-execution-assessment.md`, commit
`c0244711`):

  * M8's scorecard readiness code `(e)` -- "scientifically measurable now" -- is
    wrong. M136: "There is no scoreable M8-O movement executable now."
  * M8 is NOT transitively blocked by blocker (a) for its own verdict, but a
    pass licenses only the internal no-invention invariant while M1 is absent.
  * The M8 population ruling belongs to the scorecard owner and must be made
    BEFORE any render, which is what makes it a preregistration and not tuning.
  * M12's bar 3 (`peak_N299/peak_N33`) old value is VOID rather than merely
    under-sampled, because it was measured on the pre-repair memory model. The
    hypothesis that M182's bounded recycling also repairs bar 3 is PLAUSIBLE AND
    UNMEASURED, and 2.9.82 must keep saying so until M192 measures it.
  * M12 is consequently the only axis with a route to a first passing score that
    depends on nothing external.

WHY THE CROSS-DOCUMENT PINS EXIST. Three arms re-read M136's artifact rather
than STATUS. M136 is a LIVE lane that still owns that file. A quote goes stale
silently when its source lane revises the passage, and a STATUS-side presence
check cannot see that happen -- it keeps passing while the attribution becomes
false. Only re-reading the source catches it. This program has already been bitten
by exactly that: a doc quoted a live lane's file verbatim, the lane rewrote both
passages while still running, and the drift was caught only because a verifier
re-read the source.

THE MOST IMPORTANT ARM IS 5. `s82 bar3 unmeasured` guards a hedge, not a claim.
Its mutation deletes the words that keep the bar-3 hypothesis honest, turning
"plausible and unmeasured" into an established result. That is the single defect
in this section most likely to be introduced by accident and least likely to be
noticed, because it makes the program look closer to a passing axis than it is.

PRE-FLIGHT IS PART OF THE HARNESS. A mutation is a literal replace on raw bytes
while a check reads collapsed text, so an anchor can be findable by the check and
unreachable by the mutation. Every arm target must occur EXACTLY ONCE in the raw
file before any arm runs; missing or duplicated is a hard error, not a pass.

Note that two arm strings appear in BOTH files by design (STATUS quotes M136).
Uniqueness is therefore asserted per-file, which is the correct scope: mutating
one file's copy must redden that file's pin and no other.

v2954 pins GIT_ROOT to the real repository independently of ROOT, and every arm
here mutates a DOCUMENT rather than the verifier, so this must invoke the REAL
v2954.py with a TEMP root -- never a TEMP copy of it, whose HEAD: blob reads
would all fail.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
V = REAL / "experiments" / "ORCH-verify" / "v2954.py"

STATUS_REL = "docs/STATUS.md"
M136_REL = "docs/research/M136-m8-v15-execution-assessment.md"

# (pin label, relative path, exact raw text, replacement)
ARMS = [
    # ---- correction 1: M8 is not measurable now ----
    ("s82 m8 not measurable", STATUS_REL,
     "There is no scoreable M8-O movement executable now.",
     "There is a scoreable M8-O movement executable now."),
    ("s82 m8 not (a) blocked", STATUS_REL,
     "internal no-invention invariant, not a detail",
     "internal no-invention invariant, and also a detail"),

    # ---- correction 2: the prospective ruling is mine ----
    ("s82 ruling is mine", STATUS_REL,
     "Before a score run, the scorecard owner must make one",
     "After a score run, the scorecard owner may make one"),

    # ---- derivation: bar 3 is void, and the repair claim is UNMEASURED ----
    ("s82 bar3 void", STATUS_REL,
     "**The reading that matters is on bar 3.**",
     "**The reading that matters is on bar 4.**"),
    # The highest-value arm in this file: it deletes the hedge and promotes an
    # unmeasured hypothesis to an established result.
    ("s82 bar3 unmeasured", STATUS_REL,
     "not be cited as established until M192 measures it",
     "be cited as established without waiting for M192"),

    ("s82 m12 only reachable", STATUS_REL,
     "as the only axis with a route to a first passing score that depends on nothing",
     "as one of several axes with a route to a first passing score that depends on little"),
    ("s82 m179 drift", STATUS_REL,
     "a lane's stated intent is a",
     "a lane's stated intent is not a"),

    # ---- cross-document: 2.9.82 attributes all of this to M136 ----
    ("s82 artifact no movement", M136_REL,
     "does not license an owner-free scored render. There is no scoreable M8-O",
     "does not license an owner-free scored render. There is a scoreable M8-O"),
    ("s82 artifact m1 bound", M136_REL,
     "complete M8 pass licenses only the internal no-invention invariant, not a",
     "complete M8 pass licenses more than the internal no-invention invariant, and a"),
    ("s82 artifact prospective", M136_REL,
     "Before a score run, the scorecard owner must make one prospective, explicit",
     "After a score run, the scorecard owner may make one retrospective, implicit"),
]

# Must change nothing. Without it, a harness that reddened on every input would
# score a perfect 10/10 and look identical to a working one.
INERT = (STATUS_REL,
         "A protocol does not become a score merely because it",
         "A protocol does not turn into a score merely because it")


def run(root):
    """Return (s82 reds, green, all reds) from the REAL v2954 under `root`.

    Labels are matched against the KNOWN arm set rather than parsed out of the
    line by a whitespace heuristic. v2954 formats failures as `XFAIL %-24s  %s`,
    so a label of exactly 24 characters gets no padding from the field itself;
    an earlier version of this parser delimited on a run of >=2 spaces and
    therefore could not see those lines at all, and reported two genuine
    catches as decorative pins. Matching known labels exactly is immune to the
    field width, and to any future change in it.
    """
    p = subprocess.run([sys.executable, str(V), str(root)],
                       capture_output=True, text=True)
    known = [a[0] for a in ARMS]
    reds, all_reds = set(), set()
    for line in p.stdout.splitlines():
        m = re.match(r"^(?:XFAIL|RED)\s+(.+?)(?:\s{2,}|$)", line)
        if m:
            all_reds.add(m.group(1).strip())
        for lab in known:
            if re.match(r"^(?:XFAIL|RED)\s+" + re.escape(lab) + r"(?:\s|$)",
                        line):
                reds.add(lab)
                all_reds.add(lab)
    return reds, "VERDICT: GREEN" in p.stdout, all_reds


def apply_mutation(path, old, new):
    body = path.read_text(encoding="utf-8", errors="replace")
    if old not in body:
        raise SystemExit(
            "FATAL: mutation target not found in %s\n  looking for: %r\n"
            "A mutation that does not land is a harness failure, not a pass."
            % (path, old))
    if old == new:
        raise SystemExit("FATAL: no-op mutation for %s" % path)
    mutated = body.replace(old, new, 1)
    if mutated == body:
        raise SystemExit("FATAL: replace() changed nothing in %s" % path)
    path.write_text(mutated, encoding="utf-8")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="orch-s82-"))
    try:
        shutil.copytree(REAL / "docs", tmp / "docs")
        (tmp / "experiments").mkdir(parents=True, exist_ok=True)
        for sub in ("M-PHASE0-PHASE", "M134-kernel-frontier",
                    "M152-site-census", "M175-fork-arm", "M172-worker-memory",
                    "M136-m8o-bar", "M163-m10-uncertainty", "ORCH-verify"):
            shutil.copytree(REAL / "experiments" / sub,
                            tmp / "experiments" / sub)
        for rel in ("crates/strehl-cli/src/align_cmd.rs",
                    "crates/strehl-core/src/restore.rs"):
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, dst)

        # Per-file uniqueness. Two strings appear in both files by design,
        # because STATUS quotes M136; the arm must be unique in the file it
        # mutates, not across the tree.
        bad = []
        for label, rel, old, _new in ARMS + [("INERT", INERT[0], INERT[1], "")]:
            n = (tmp / rel).read_text(encoding="utf-8",
                                      errors="replace").count(old)
            if n != 1:
                bad.append("%-26s occurs %d times in %s: %r"
                           % (label, n, rel, old))
        if bad:
            print("FATAL: arm targets are not raw-unique within their own "
                  "file. A missing target cannot mutate; a duplicated one "
                  "leaves a copy that satisfies the pin.")
            for b in bad:
                print("  " + b)
            raise SystemExit(2)
        print("pre-flight: all %d arm targets are raw-unique in-file"
              % (len(ARMS) + 1))

        reds, green, all_reds = run(tmp)
        if not green or reds:
            raise SystemExit(
                "FATAL: TEMP baseline is not GREEN.\n  s82 reds: %s\n"
                "  all reds: %s" % (sorted(reds), sorted(all_reds)))
        print("TEMP baseline VERDICT: GREEN, no s82 reds")

        caught = missed = dup = 0
        for label, rel, old, new in ARMS:
            target = tmp / rel
            original = target.read_text(encoding="utf-8", errors="replace")
            apply_mutation(target, old, new)
            reds, _green, _all = run(tmp)
            target.write_text(original, encoding="utf-8")

            if reds == {label}:
                print("CAUGHT    %s" % label)
                caught += 1
            elif not reds:
                print("MISSED    %s  <-- DECORATIVE: defect planted, pin silent"
                      % label)
                missed += 1
            else:
                print("DUPLICATE %s  <-- reddened %s" % (label, sorted(reds)))
                dup += 1

        rel, old, new = INERT
        target = tmp / rel
        original = target.read_text(encoding="utf-8", errors="replace")
        apply_mutation(target, old, new)
        inert_reds, _g, _a = run(tmp)
        target.write_text(original, encoding="utf-8")
        inert_ok = not inert_reds
        print("INERT     %s" % ("held (no pin reddened)" if inert_ok
                                else "FAILED, reddened %s" % sorted(inert_reds)))

        post_reds, post_green, _ = run(tmp)
        restored = post_green and not post_reds
        print("post-restore TEMP: %s" % ("GREEN" if restored else "RED"))

        live_reds, live_green, _ = run(REAL)
        live_ok = live_green and not live_reds
        print("live tree: %s" % ("GREEN" if live_ok else "RED"))

        print()
        print("ARMS %d / CAUGHT %d / MISSED %d / DUPLICATE %d"
              % (len(ARMS), caught, missed, dup))
        ok = (missed == 0 and dup == 0 and inert_ok and restored and live_ok)
        print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
        sys.exit(0 if ok else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
