"""Commission the Amendment 8 pins in v2954.py.

A green verifier is a claim about the verifier, not about the document. Every
pin added for Amendment 8 is proven here by planting the exact defect it is
supposed to catch and requiring that specific label to XFAIL.

Two classes of arm, and they are NOT equally strong:

  WIRING   -- the real file on disk is mutated, v2954.py is re-run as a
              subprocess, and the named check must fail. This proves the whole
              path: read, collapse, compare, report.

  PREDICATE-- the needle is corrupted in memory and required to vanish from the
              real source. This proves the needle discriminates on its exact
              string rather than matching something loose. It does NOT prove
              the check is wired. It is used only for the eight source-side
              QUOTES pins, whose sources are lane-owned files that ~25
              concurrent agents may be reading; mutating those on disk to
              commission my own check would be reckless.

An INERT arm changes text no check reads and requires the verifier to stay
GREEN, so that "everything fails" cannot masquerade as "everything is caught".

Mutations are anchored on unique full strings and HARD-ERROR if the anchor does
not land. A mutation that silently fails to apply produces a green that means
nothing. The plan file is backed up to %TEMP% and restored in a finally block;
`git checkout --` is never used, because it would discard concurrent work.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLAN = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
VERIF = HERE / "v2954.py"
BACKUP = Path(tempfile.gettempdir()) / "commission_a8_plan_backup.md"


def run_verifier():
    r = subprocess.run([sys.executable, str(VERIF)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def failed(out, label):
    return ("XFAIL %s" % label) in out


def mutate(anchor, replacement):
    """Replace `anchor` exactly once. Hard-error if it is not uniquely present."""
    text = PLAN.read_text(encoding="utf-8")
    n = text.count(anchor)
    if n != 1:
        raise SystemExit(
            "MUTATION TARGET NOT FOUND: %r matched %d times (need exactly 1)"
            % (anchor[:70], n))
    PLAN.write_text(text.replace(anchor, replacement), encoding="utf-8")


def restore():
    shutil.copyfile(BACKUP, PLAN)


# (label, anchor, replacement, what defect this simulates)
WIRING = [
    ("a8 section present",
     "## 18. Amendment 8 — the phase-0 audit lands",
     "## 18. Amendment Eight — the phase-0 audit lands",
     "the amendment is renamed / silently unregistered"),
    ("a8 cites split2",
     "> **Final verdict: NOT ROBUST / NO BUILD.**",
     "> **Final verdict: NOT-ROBUST / NO BUILD.**",
     "SPLIT2's verdict is misquoted by one character"),
    ("a8 cites phase",
     "> **Filed verdict: KILL at the measured rho, NOT ROBUST across the rho census.**",
     "> **Filed verdict: NARROWED at the measured rho, NOT ROBUST across the rho census.**",
     "C1's filed verdict is softened from KILL to NARROWED"),
    ("a8 cites rho ci",
     "> interval (0.00185-0.01078), and to SURVIVE at the top of the design census.",
     "> interval (0.00185-0.00900), and to SURVIVE at the top of the design census.",
     "the rho interval is narrowed so 0.01 falls outside it"),
    ("a8 cites rho 30x",
     "**`30.49x`**",
     "**`30.50x`**",
     "the RHO grid-refinement factor drifts from its source value"),
    ("a8 c1 ruling intact",
     "It may not be scheduled as build-ready phase-3 work",
     "It may now be scheduled as build-ready phase-3 work",
     "C1 is quietly made schedulable again"),
    # Two arms, one per conjunct of `a8 c1 correction recorded`. The check
    # requires BOTH that M183's falsification is recorded AND that the
    # superseded wording survives verbatim; a single arm would leave half the
    # conjunction unexercised and I would not know which half works.
    ("a8 c1 correction recorded",
     "**Both statements were wrong, and the lane falsified them by doing exactly what",
     "**Both statements were arguable, and the lane broadly agreed by doing exactly what",
     "M183's falsification of my own amendment is softened away"),
    ("a8 c1 correction recorded",
     "C1 *\"may not be struck, because that same interval contains SURVIVE\"*, and that",
     "C1 something to that general effect, and that",
     "the superseded wording is tidied away instead of preserved"),
]

INERT = ("uncommitted on disk", "uncommitted on the disk",
         "prose no check reads is reworded")

# (label, source-relative path, needle) -- corrupt the needle, require absence.
PREDICATE = [
    ("a8 split2 verdict", "docs/research/M-PHASE0-SPLIT2.md",
     "Final verdict: NOT ROBUST / NO BUILD."),
    ("a8 split2 fail rms", "docs/research/M-PHASE0-SPLIT2.md", "0.107703"),
    ("a8 split2 spatial", "docs/research/M-PHASE0-SPLIT2.md", "0.105202"),
    ("a8 phase filed verdict", "experiments/M-PHASE0-PHASE/PREREGISTRATION.md",
     "Filed verdict: KILL at the measured rho, NOT ROBUST across the rho census."),
    ("a8 phase rho ci", "experiments/M-PHASE0-PHASE/PREREGISTRATION.md",
     "(0.00185-0.01078)"),
    ("a8 phase rho 30x", "experiments/M-PHASE0-PHASE/PREREGISTRATION.md", "30.49x"),
    ("a8 status phase closed", "docs/STATUS.md",
     "CLOSED. C1 is KILL at the measured"),
    ("a8 m133 phase not absent", "docs/research/M133-blocker-audit.md",
     "is false. Its result is filed in the"),
    # M183's artifacts. These are predicate arms rather than wiring arms
    # deliberately: M183-rho-convention.md belongs to that lane and I must not
    # mutate another lane's file to commission my own checks. What these prove
    # is that each needle is present AND that a one-character corruption of it
    # is absent -- i.e. the pin cannot be satisfied by a near-miss.
    ("m183 rho pinned", "docs/research/M183-rho-convention.md",
     "rho = 0.00551650"),
    ("m183 rho interval", "docs/research/M183-rho-convention.md",
     "0.00184706--0.01077932"),
    ("m183 verdict line", "docs/research/M183-rho-convention.md",
     "KILL at the median, but NARROWED at field centre at the upper endpoint"),
    ("m183 transition", "docs/research/M183-rho-convention.md",
     "rho = 0.00633340"),
    ("m183 30x diagnosis", "docs/research/M183-rho-convention.md",
     "0.0055165 / 0.0001809 = 30.49x"),
    ("m183 falsifies a8 survive", "docs/research/M183-rho-convention.md",
     "It says the measured interval contains **SURVIVE**"),
]


def corrupt(s):
    """Change exactly one character in a way that cannot coincide with truth."""
    digits = [i for i, c in enumerate(s) if c.isdigit()]
    if digits:
        i = digits[-1]
        return s[:i] + ("0" if s[i] != "0" else "1") + s[i + 1:]
    return s[:-1] + "Q"


def main():
    caught = missed = inert_green = 0
    notes = []

    shutil.copyfile(PLAN, BACKUP)
    try:
        base = run_verifier()
        if "VERDICT: GREEN" not in base:
            raise SystemExit("BASELINE IS NOT GREEN -- commission nothing until it is:\n"
                             + base[-1500:])
        print("baseline: GREEN\n")

        for label, anchor, repl, why in WIRING:
            mutate(anchor, repl)
            try:
                out = run_verifier()
            finally:
                restore()
            if failed(out, label):
                caught += 1
                print("CAUGHT   %-26s %s" % (label, why))
            else:
                missed += 1
                print("MISSED   %-26s %s  <-- CHECK IS A NO-OP" % (label, why))
                notes.append(label)

        # INERT: prove the suite is not simply failing on any edit at all.
        mutate(INERT[0], INERT[1])
        try:
            out = run_verifier()
        finally:
            restore()
        if "VERDICT: GREEN" in out:
            inert_green += 1
            print("INERT-OK %-26s %s" % ("(no check reads this)", INERT[2]))
        else:
            missed += 1
            print("INERT-BAD%-26s suite fails on unrelated prose" % "")
            notes.append("INERT")

        print()
        # The absence pin needs a different kind of plant: not a text edit, but
        # the thing whose non-existence it asserts. If either gate ever produces
        # a tracked artifact, section 18.3 is false and this must notice.
        probe = ROOT / "experiments" / "M-PHASE0-TETHER-commission-probe"
        probe.mkdir(exist_ok=True)
        try:
            out = run_verifier()
        finally:
            shutil.rmtree(probe, ignore_errors=True)
        if failed(out, "a8 makernote/tether unrun"):
            caught += 1
            print("CAUGHT   %-26s a tracked TETHER artifact appears on disk"
                  % "a8 makernote/tether unrun")
        else:
            missed += 1
            print("MISSED   %-26s <-- ABSENCE CLAIM IS UNGUARDED"
                  % "a8 makernote/tether unrun")
            notes.append("a8 makernote/tether unrun")
        if probe.exists():
            raise SystemExit("PROBE NOT CLEANED UP: %s" % probe)

        print()
        pred_ok = pred_bad = 0
        for label, rel, needle in PREDICATE:
            p = ROOT / rel
            if not p.exists():
                pred_bad += 1
                print("PRED-BAD %-26s SOURCE MISSING %s" % (label, rel))
                continue
            raw = p.read_text(encoding="utf-8", errors="replace")
            flat = re.sub(r"\s+", " ", raw)
            here = re.sub(r"\s+", " ", needle) in flat
            gone = re.sub(r"\s+", " ", corrupt(needle)) not in flat
            if here and gone:
                pred_ok += 1
                print("PRED-OK  %-26s exact needle present; corrupted needle absent" % label)
            else:
                pred_bad += 1
                print("PRED-BAD %-26s present=%s corrupted-absent=%s" % (label, here, gone))
                notes.append(label)
    finally:
        restore()
        if BACKUP.exists():
            os.remove(BACKUP)

    final = run_verifier()
    print("\nrestored plan, verifier re-run: %s"
          % ("GREEN" if "VERDICT: GREEN" in final else "NOT GREEN -- RESTORE FAILED"))

    total = len(WIRING) + 1 + 1 + len(PREDICATE)
    print("\nwiring caught     : %d of %d" % (caught, len(WIRING) + 1))
    print("inert green       : %d of 1" % inert_green)
    print("predicate ok      : %d of %d" % (pred_ok, len(PREDICATE)))
    print("missed            : %d" % missed)
    print("accounted         : %d of %d arms"
          % (caught + missed + inert_green + pred_ok + pred_bad, total))
    ok = (missed == 0 and pred_bad == 0 and inert_green == 1
          and "VERDICT: GREEN" in final)
    print("\n%s" % ("COMMISSIONED" if ok else "NOT COMMISSIONED: %s" % notes))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
