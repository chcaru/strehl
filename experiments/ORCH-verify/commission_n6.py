#!/usr/bin/env python3
"""Commission the six N6 / Amendment 1 checks added to vclamp.py.

Two kinds of arm, deliberately labelled differently rather than blurred:

  WIRING   -- mutates docs/research/ORCH-clamp-default-decision.md, which the
              orchestrator owns, and runs vclamp.py end to end. This proves the
              check is wired to the real file and really fails.

  PREDICATE-- evaluates the exact predicate vclamp.py uses against good and bad
              strings held in memory. The three code-fact checks read shared
              Rust source under crates/, and ~25 agents share this working
              tree; mutating align.rs or restore.rs could be consumed by
              another agent's cargo build. A PREDICATE arm is weaker evidence
              than a WIRING arm -- it does not prove the path is right -- and
              saying so is the point of the label.

Every WIRING mutation is anchored on a unique full string and hard-errors if it
does not match exactly once, so a silent no-match can never be reported as a
caught defect.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs" / "research" / "ORCH-clamp-default-decision.md"
VCLAMP = Path(__file__).resolve().parent / "vclamp.py"


def collapse(s):
    return re.sub(r"\s+", " ", s)


def run():
    p = subprocess.run([sys.executable, str(VCLAMP)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode


WIRING = [
    ("N6 prohibition deleted",
     "> **N6 (generalises N5, which stands as a special case).** **No configuration",
     "> **N6 (advisory).** It would be preferable if no configuration",
     True),
    ("M8/(a) coupling softened",
     "**M8\ncannot be honestly passed before `(a)` closes.**",
     "M8 may well be passable before `(a)` closes.",
     True),
    ("N6's own falsifier removed",
     "and measurable, N6 is too strong, and it must be **qualified rather than\nfootnoted**",
     "and measurable, N6 is too strong, and it may be footnoted",
     True),
    ("INERT cosmetic edit in the amended section",
     "**What is measured and what is assumed.**",
     "**What is measured, and what is assumed.**",
     False),
]

# The exact predicates vclamp.py applies to the Rust sources.
PREDICATE = [
    ("six-variant enum",
     lambda t: all(collapse("Resampler::%s" % v) in collapse(t)
                   for v in ("Nearest", "Bilinear", "CatmullRom",
                             "ClampedCatmullRom", "Lanczos2", "Lanczos3")),
     "enum Resampler { Nearest, Bilinear, CatmullRom, ClampedCatmullRom, "
     "Lanczos2, Lanczos3 } Resampler::Nearest Resampler::Bilinear "
     "Resampler::CatmullRom Resampler::ClampedCatmullRom Resampler::Lanczos2 "
     "Resampler::Lanczos3",
     "enum Resampler { CatmullRom, ClampedCatmullRom } Resampler::CatmullRom "
     "Resampler::ClampedCatmullRom"),
    ("bilinear tap non-negative",
     lambda t: collapse("Resampler::Bilinear => (1.0 - a).max(0.0),") in collapse(t),
     "Resampler::Bilinear => (1.0 - a).max(0.0),",
     "Resampler::Bilinear => 1.5 * a * a * a - 2.5 * a * a + 1.0,"),
    ("restoration refuses only the clamp",
     lambda t: collapse("!matches!(r, Resampler::ClampedCatmullRom)") in collapse(t),
     "pub const fn restoration_supported(r: Resampler) -> bool { "
     "!matches!(r, Resampler::ClampedCatmullRom) }",
     "pub const fn restoration_supported(r: Resampler) -> bool { "
     "matches!(r, Resampler::CatmullRom) }"),
]


def main():
    original = DECISION.read_text(encoding="utf-8")
    if run() != 0:
        print("FATAL: baseline vclamp is not GREEN; commissioning is meaningless.")
        return 2
    print("baseline            : GREEN")
    print()

    caught = missed = inert_green = inert_red = 0
    try:
        for label, find, repl, expect_red in WIRING:
            n = original.count(find)
            if n != 1:
                raise SystemExit(
                    "MUTATION TARGET NOT FOUND: %r matched %d times (need exactly 1)."
                    % (label, n))
            DECISION.write_text(original.replace(find, repl, 1), encoding="utf-8")
            red = (run() != 0)
            if expect_red:
                if red:
                    caught += 1
                    v = "CAUGHT"
                else:
                    missed += 1
                    v = "MISSED  <-- no-op"
            else:
                if red:
                    inert_red += 1
                    v = "INERT-RED  <-- over-sensitive"
                else:
                    inert_green += 1
                    v = "INERT-GREEN"
            print("WIRING    %-42s %s" % (label, v))
    finally:
        DECISION.write_text(original, encoding="utf-8")

    pred_ok = pred_bad = 0
    for label, pred, good, bad in PREDICATE:
        g, b = pred(good), pred(bad)
        if g and not b:
            pred_ok += 1
            v = "DISCRIMINATES"
        else:
            pred_bad += 1
            v = "DOES NOT DISCRIMINATE (good=%s bad=%s)" % (g, b)
        print("PREDICATE %-42s %s" % (label, v))

    restored = "GREEN" if run() == 0 else "RED"
    print()
    print("restored baseline   : %s" % restored)
    print("wiring caught       : %d" % caught)
    print("wiring missed       : %d" % missed)
    print("wiring inert green  : %d" % inert_green)
    print("wiring inert red    : %d" % inert_red)
    print("wiring accounted    : %d of %d" %
          (caught + missed + inert_green + inert_red, len(WIRING)))
    print("predicates discrim. : %d of %d" % (pred_ok, len(PREDICATE)))
    ok = (missed == 0 and inert_red == 0 and pred_bad == 0
          and restored == "GREEN"
          and caught == sum(1 for a in WIRING if a[3]))
    print()
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
