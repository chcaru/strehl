"""Can this lane's section 13 gate detect a REVERSED CONCLUSION?

Section 13 is more exposed than section 14 was. Section 14 has two
instruments -- `s14_splice.py --check` and `verify_s14.py` -- and the splice
check at least catches a flip made in the report alone. Section 13 has ONE
instrument, `verify_blotch.py`, it re-derives NUMBERS, and there is no splice
guard covering sections 0-13 at all. A reversed verdict in section 13 changes
no number, so before the CONCLUSIONS table it was caught by nothing.

That is not a suspicion. It was observed without planting anything: the 13.6
scope correction rewrote a conclusion outright -- withdrawing the unrestricted
claim "the gate never fires where the mottle is" -- and `verify_blotch.py`
returned 53/0/0 GREEN across the change.

Each flip is therefore run TWICE:

  BG_NO_CONCLUSIONS=1   the pre-fix verifier, numbers only. Establishes that
                        the defect really is invisible to what was there
                        before, so the fix is measured rather than asserted.
  (unset)               the shipping verifier. Must catch every flip.

A control with identical text runs in both modes and must stay GREEN in both,
so a harness that simply failed everything could not be read as a success.

Every mutation is anchored on a unique string and hard-errors if it does not
land, because a negative control that silently fails to plant its defect
reports the instrument as healthy -- the exact failure it exists to prevent.

Runtime is ~3 min per verifier run (the blotch row cache is warm), so this
takes roughly 25 minutes.
"""
import os
import re
import shutil
from reportlock import ReportLock
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))
TMP = os.environ["TEMP"]

# (name, anchor, replacement, which conclusion it reverses)
#
# Anchors are whitespace-exact against the file, so any phrase that wraps in
# the source is anchored on a single line of it.
FLIPS = [
    ("control-identical",
     "## 13. Does the admission gate fix the mid-scale mottle? No.",
     "## 13. Does the admission gate fix the mid-scale mottle? No.",
     "control: identical text, must stay GREEN in both modes"),
    ("headline-answer",
     "## 13. Does the admission gate fix the mid-scale mottle? No.",
     "## 13. Does the admission gate fix the mid-scale mottle? Yes.",
     "reverses the section's entire headline answer"),
    ("knob-fixes-mottle",
     "knob cannot fix the mottle.** Two subjects have no knee at all: on",
     "knob fixes the mottle.** Two subjects have no knee at all: on",
     "reverses the elimination in 13.5"),
    ("control-identical-2",
     "`bee-1-cpl` against 0.976-0.999 on the other four -- the only subject "
     "where the",
     "`bee-1-cpl` against 0.976-0.999 on the other four -- the only subject "
     "where the",
     "control 2: identical text in a different section, must stay GREEN"),
    ("scope-correction-undone",
     "floor and across the whole scalar range this section swept, the gate "
     "does not",
     "floor and across the whole scalar range this section swept, the gate "
     "never",
     "THE ONE THAT MATTERS: reinstates ORCH's withdrawn fact 1807 by "
     "breaking the scope qualifier"),
    ("knob-shape-reversed",
     "band 0 is where the sharpness lives. The failure is in the shape of "
     "the knob,",
     "band 0 is where the sharpness lives. The failure is in the reach of "
     "the gate,",
     "reverses the mechanism 13.6 now attributes the failure to"),
]


def read(p):
    return open(p, encoding="utf-8", errors="strict").read()


def write(p, t):
    open(p, "w", encoding="utf-8", newline="").write(t)


def plant(path, old, new):
    t = read(path)
    n = t.count(old)
    if n != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND (%d occurrences) in %s:\n"
                         "  %r" % (n, os.path.basename(path), old[:70]))
    write(path, t.replace(old, new, 1))


def gate(pre_fix):
    """verify_blotch.py. Returns True when GREEN."""
    env = dict(os.environ)
    if pre_fix:
        env["BG_NO_CONCLUSIONS"] = "1"
    else:
        env.pop("BG_NO_CONCLUSIONS", None)
    r = subprocess.run([sys.executable, os.path.join(HERE, "verify_blotch.py")],
                       capture_output=True, cwd=HERE, env=env)
    return r.returncode == 0


def main():
    bak = os.path.join(TMP, "negctl_s13_report.md")
    shutil.copy2(REPORT, bak)
    print("backed up the report to %s" % bak)

    t0 = time.time()
    base_new, base_old = gate(False), gate(True)
    print("baseline: shipping=%s pre-fix=%s  (%.0fs)\n"
          % ("GREEN" if base_new else "RED", "GREEN" if base_old else "RED",
             time.time() - t0))
    if not (base_new and base_old):
        print("baseline is not green in both modes; aborting so a "
              "pre-existing failure is not read as a caught defect.")
        shutil.copy2(bak, REPORT)
        return 1

    caught = missed = 0
    ctl_bad = 0
    pre_missed = 0
    rows = []
    try:
        for name, old, new, what in FLIPS:
            control = (old == new)
            plant(REPORT, old, new)
            new_ok, old_ok = gate(False), gate(True)
            shutil.copy2(bak, REPORT)

            if control:
                good = new_ok and old_ok
                verdict = "GREEN both (correct)" if good else "CONTROL FAILED"
                if not good:
                    ctl_bad += 1
            else:
                if not old_ok:
                    pre = "caught"
                else:
                    pre = "MISSED"
                    pre_missed += 1
                if new_ok:
                    verdict = "**MISSED** (pre-fix %s)" % pre
                    missed += 1
                else:
                    verdict = "caught (pre-fix %s)" % pre
                    caught += 1
            rows.append((name, what, verdict))
            print("%-24s %s" % (name, verdict))
    finally:
        shutil.copy2(bak, REPORT)

    same = read(REPORT) == read(bak)
    post = gate(False)
    print("\nrestored byte-identical: %s   post-restore gate: %s"
          % (same, "GREEN" if post else "RED"))

    real = [f for f in FLIPS if f[2] != f[1]]
    print("\n%d caught / %d MISSED of %d conclusion flips  "
          "(%d controls, %d control failures)"
          % (caught, missed, len(real), len(FLIPS) - len(real), ctl_bad))
    print("pre-fix verifier missed %d of %d -- that is what the CONCLUSIONS "
          "table is worth." % (pre_missed, len(real)))
    print("\ndetail:")
    for name, what, verdict in rows:
        print("  %-24s %-62s %s" % (name, what[:62], verdict))

    ok = (missed == 0 and ctl_bad == 0 and same and post)
    print("\nVERDICT: %s" % ("every conclusion flip was caught."
                             if ok else
                             "the section 13 gate is BLIND to a reversed "
                             "conclusion, or the harness itself failed."))
    return 0 if ok else 1


if __name__ == "__main__":
    with ReportLock("negctl_s13.py"):
        sys.exit(main())
