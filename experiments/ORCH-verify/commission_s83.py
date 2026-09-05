#!/usr/bin/env python3
"""Commission the STATUS 2.9.82-correction and 2.9.83 pins added to v2954.py.

WHAT IS BEING GUARDED.

(1) The 2.9.82 correction. I published "M8's `(e)` coding is wrong". That
    overstated lane M136. The scorecard's code is scoped -- `(e) for M8-R` --
    and M8-R WAS measured, at 1.030569%; `:834` defines the class as
    "scientifically measurable now" and adds "An (e) does not mean a result has
    been run." The claim is WITHDRAWN VISIBLY, per this file's rule at
    STATUS:5301-5303, because a silently removed false claim leaves no trace
    that anyone was misled by it. What survives is narrower and still decisive:
    the M8 axis cannot reach a pass now because the M8-O half has no executable
    route to a score.

(2) The 2.9.83 M10 definition freeze. Lane M190 closed the four gaps M186
    localised and M10 moved from `PARTIALLY DEFINED; DEFINITION BLOCKED` to
    `DEFINED; UNMEASURED`. Three properties of that freeze are load-bearing and
    each is pinned:

      * ORDERING. The algorithm precommit `1fb63317` (00:44:24) lands BEFORE the
        normative freeze `a9753219` (00:48:50). Reverse that and the freeze stops
        being a preregistration and becomes tuning. Arm 5 plants exactly that.
      * NO RE-ROLL. A leaked or re-drawn scored seed makes the arm
        `UNMEASURED_SYNTHETIC_TRUTH` and "does not license another seed". A
        design permitting a re-draw after a leak hands back the whole degree of
        freedom the commitment removes. Arm 6 plants the permissive version.
      * NO THRESHOLD MOVED. A definition freeze that also moves a bar is tuning
        wearing a freeze's clothes. Arm 7 plants the admission that one moved.

(3) The scoreboard arithmetic. Removing M10 from the DEFINITION BLOCKED count
    exposed that the FAIL count was ALREADY wrong -- M12 is read-and-admitted
    FAIL at `:2122`. The partition is now two FAIL / one BLOCKED / nine
    UNMEASURED = twelve. Arm 8 breaks the sum; arm 12 restores the old
    undercount.

WHY THE PAIRED PIN ON THE CORRECTION. Arm 1 mutates the corrected statement and
arm 2 UN-STRIKES the withdrawn one. A pin on the correction alone stays GREEN if
someone removes the strikethrough and leaves both standing, which makes the file
assert a claim and its own correction simultaneously -- the exact defect that
produced 2.9.80.

WHY THE CROSS-DOCUMENT ARMS. Arms 10-14 re-read the live scorecard and M190's
artifact rather than STATUS. 2.9.83 asserts that replacements were APPLIED and
quotes a live lane; a STATUS-side presence check cannot see the scorecard being
reverted or M190 revising its own escrow clause, and would keep passing while
the attribution became false.

PRE-FLIGHT IS PART OF THE HARNESS. A mutation is a literal replace on raw bytes
while a check reads collapsed text, so an anchor can be findable by the check and
unreachable by the mutation. Every arm target must occur EXACTLY ONCE in the raw
file before any arm runs.

v2954 pins GIT_ROOT to the real repository independently of ROOT, and every arm
mutates a DOCUMENT rather than the verifier, so this invokes the REAL v2954.py
with a TEMP root -- never a TEMP copy of it, whose HEAD: blob reads would fail.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
V = REAL / "experiments" / "ORCH-verify" / "v2954.py"

ST = "docs/STATUS.md"
SC = "docs/proposals/2026-09-sota-scorecard.md"
M190 = "docs/research/M190-m10-definition-freeze.md"

# (pin label, relative path, exact raw text, replacement)
ARMS = [
    # ---- 2.9.82 correction, pinned as a pair ----
    ("s82c coding is correct", ST,
     "**M8 cannot reach a pass now, though its `(e)` coding is",
     "**M8 can reach a pass now, though its `(e)` coding is"),
    ("s82c overclaim struck", ST,
     "~~**M8's `(e)` coding is wrong.**",
     "**M8's `(e)` coding is wrong.**"),
    ("s82c e definition", ST,
     "immediately by *\"An **(e)** does not mean a result has been run.\"*",
     "immediately by *\"An **(e)** does mean a result has been run.\"*"),

    # ---- 2.9.83 ----
    ("s83 heading", ST,
     "### 2.9.83 M10's definition is closed, frozen before any product existed",
     "### 2.9.83 M10's definition is open, frozen before any product existed"),
    # Reversing the precommit ordering turns a preregistration into tuning.
    ("s83 precommit ordering", ST,
     "**before** the normative freeze `a9753219` at `00:48:50`",
     "**after** the normative freeze `a9753219` at `00:48:50`"),
    # Permitting a re-draw after a leak restores the degree of freedom.
    ("s83 no reroll", ST,
     "license another seed.\"** A naive design would permit a re-draw after a leak,",
     "license another seed.\"** A sound design would permit a re-draw after a leak,"),
    ("s83 no threshold moved", ST,
     "**Nothing here changed a threshold**, which is the line between a freeze and",
     "**One threshold moved here**, which is the line between a freeze and"),
    ("s83 partition sums", ST,
     "`DEFINITION BLOCKED` (M9), nine `UNMEASURED`**, summing to twelve.",
     "`DEFINITION BLOCKED` (M9), eight `UNMEASURED`**, summing to twelve."),
    ("s83 supersedes label", ST,
     "**This section supersedes their label only.**",
     "**This section supersedes their reasoning only.**"),

    # ---- cross-document: the live scorecard must actually carry the rows ----
    ("s83 scorecard 815", SC,
     "**DEFINED; UNMEASURED \u2014 MISSING PRODUCT, CHECKER, AND SCORED TRUTH.**",
     "**DEFINED; MEASURED \u2014 MISSING PRODUCT, CHECKER, AND SCORED TRUTH.**"),
    ("s83 scorecard 849", SC,
     "| M10 | **DEFINED; UNMEASURED; (b)(c)** |",
     "| M10 | **DEFINED; UNMEASURED; (b)(c)(d)** |"),
    # Restores the stale undercount this section repaired.
    ("s83 scoreboard fixed", SC,
     "**two owner gates have an admitted `FAIL` (M8 and M12),",
     "**one owner gate has an admitted `FAIL` (M8),"),

    # ---- cross-document: M190 is a live lane owning this artifact ----
    ("s83 artifact no reroll", M190,
     "`UNMEASURED_SYNTHETIC_TRUTH`; it does not license another seed.",
     "`UNMEASURED_SYNTHETIC_TRUTH`; it licenses another seed."),
    ("s83 artifact verdict", M190,
     "**Verdict: DEFINED; UNMEASURED.**",
     "**Verdict: PARTIALLY DEFINED.**"),
]

# Must change nothing. Without it, a harness that reddened on every input would
# score a perfect 14/14 and look identical to a working one.
INERT = (ST,
         "move the scoreboard; it removes a class of blocker.",
         "move the scoreboard; it removes one class of blocker.")


def run(root):
    """Return (arm reds, green, all reds) from the REAL v2954 under `root`.

    Labels are matched against the KNOWN arm set rather than parsed out by a
    whitespace heuristic. v2954 formats failures as `XFAIL %-24s  %s`, so a label
    of exactly 24 characters gets no padding from the field itself; an earlier
    parser delimited on a run of >=2 spaces and could not see those lines at all,
    reporting two genuine catches as decorative pins.
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
    tmp = Path(tempfile.mkdtemp(prefix="orch-s83-"))
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

        bad = []
        for label, rel, old, _new in ARMS + [("INERT", INERT[0], INERT[1], "")]:
            n = (tmp / rel).read_text(encoding="utf-8",
                                      errors="replace").count(old)
            if n != 1:
                bad.append("%-26s occurs %d times in %s: %r"
                           % (label, n, rel, old))
        if bad:
            print("FATAL: arm targets are not raw-unique within their own file.")
            for b in bad:
                print("  " + b)
            raise SystemExit(2)
        print("pre-flight: all %d arm targets are raw-unique in-file"
              % (len(ARMS) + 1))

        reds, green, all_reds = run(tmp)
        if not green or reds:
            raise SystemExit(
                "FATAL: TEMP baseline is not GREEN.\n  arm reds: %s\n"
                "  all reds: %s" % (sorted(reds), sorted(all_reds)))
        print("TEMP baseline VERDICT: GREEN, no arm reds")

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
