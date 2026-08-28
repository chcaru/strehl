"""Negative control for verify_s14.py.

A verifier that has never gone red on a defect it was built to catch is a
claim about an instrument, not evidence. This plants one defect at a time in
section 14's PROSE, requires verify_s14.py to go RED on each, and restores
the report between arms.

Two disciplines this repository has already paid for:

  * every mutation is anchored on a UNIQUE full-line-fragment string and the
    script hard-errors if the anchor does not land exactly once. A bare
    replace(x, y, 1) silently mutates the first coincidental match and the
    resulting red reads like a caught defect when it is a different edit.

  * the report is copied to %TEMP% first and restored from that copy, never
    via `git checkout --`, which reverts to HEAD and has destroyed
    uncommitted work on this machine.

The final arm is a control on the control: an edit that changes prose without
changing any number must stay GREEN. Without it, a verifier stuck at RED
would score a perfect sweep.
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))
BACKUP = os.path.join(os.environ["TEMP"], "BG4-negctl-s14.md")
VERIFY = os.path.join(HERE, "verify_s14.py")

# (name, unique anchor, replacement, expected verdict)
DEFECTS = [
    ("D1 r upper bound",
     "at **+0.933 to +0.997**",
     "at **+0.933 to +0.998**", "RED"),
    ("D2 grain move max",
     "`k` still moves grain by up to 3.89% and",
     "`k` still moves grain by up to 3.79% and", "RED"),
    ("D3 largest blotch cut",
     "blotch cut anywhere in the sweep is **-8.38%**",
     "blotch cut anywhere in the sweep is **-8.48%**", "RED"),
    ("D4 band 0 worst error",
     "against band 0's worst of **4.3%**",
     "against band 0's worst of **3.4%**", "RED"),
    ("D5 decoy margin",
     "margin, while its own predictions span only 13.2%",
     "margin, while its own predictions span only 14.2%", "GREEN"),
    ("D6 runtime outlier",
     "`coffee-bubbles` at 2.54x is 19 frames",
     "`coffee-bubbles` at 2.45x is 19 frames", "RED"),
    ("D7 bee-1 worst grain",
     "by up to -54.49% -- while its sharpness column",
     "by up to -54.39% -- while its sharpness column", "RED"),
    ("D8 one-in-N",
     "at most 1 in\n2000, and they would have to carry",
     "at most 1 in\n1000, and they would have to carry", "RED"),
    ("D9 prediction accuracy",
     "predicts the measured gating rate to within **4.3%** on",
     "predicts the measured gating rate to within **4.9%** on", "RED"),
    ("D10 share of requirement",
     "so that is **14.3%** of the requirement",
     "so that is **15.3%** of the requirement", "RED"),
    ("D11 k_obs range",
     "compensating `k` is\n   **1.611-1.834** here",
     "compensating `k` is\n   **1.611-1.844** here", "RED"),
    ("CONTROL prose-only edit",
     "Three further results, in descending order",
     "Three further findings, in descending order", "GREEN"),
]


def run_verifier():
    p = subprocess.run([sys.executable, VERIFY], capture_output=True,
                       cwd=HERE)
    return "GREEN" if p.returncode == 0 else "RED", p.stdout.decode(
        "utf-8", "replace")


def main():
    shutil.copyfile(REPORT, BACKUP)
    clean = io.open(REPORT, encoding="utf-8").read()
    print("backed up report to %s (%d bytes)" % (BACKUP, len(clean)))

    verdict, out = run_verifier()
    print("\nBASELINE (unmutated): %s" % verdict)
    if verdict != "GREEN":
        print(out)
        sys.exit("baseline must be GREEN before planting anything")

    caught = missed = wrong_anchor = 0
    try:
        for name, anchor, repl, expect in DEFECTS:
            n = clean.count(anchor)
            if n != 1:
                print("  %-26s MUTATION TARGET NOT FOUND (%d occurrences)"
                      % (name, n))
                wrong_anchor += 1
                continue
            io.open(REPORT, "w", encoding="utf-8", newline="\n").write(
                clean.replace(anchor, repl, 1))
            verdict, _ = run_verifier()
            ok = verdict == expect
            print("  %-26s expected %-5s got %-5s  %s"
                  % (name, expect, verdict, "ok" if ok else "** MISSED **"))
            if ok:
                caught += 1
            else:
                missed += 1
    finally:
        shutil.copyfile(BACKUP, REPORT)

    restored = io.open(REPORT, encoding="utf-8").read()
    same = restored == clean
    print("\nrestored byte-identical: %s" % same)
    verdict, _ = run_verifier()
    print("post-restore verifier: %s" % verdict)

    total = len(DEFECTS)
    print("\n  %d caught / %d missed / %d unanchored = %d of %d"
          % (caught, missed, wrong_anchor, caught + missed + wrong_anchor,
             total))
    bad = missed or wrong_anchor or not same or verdict != "GREEN"
    print("  %s" % ("COMMISSIONED" if not bad else "FAILED"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
