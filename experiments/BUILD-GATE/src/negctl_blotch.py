"""Negative control for verify_blotch.py.

A green verifier is a claim about the instrument, not about the report, until
the instrument has been shown to go red on a defect it should catch. Each
defect below is anchored on a UNIQUE FULL LINE and the script hard-errors if
the anchor does not land -- a bare replace(x, y, 1) that silently hits the
wrong occurrence produces a green that means nothing.

The report is restored from a copy in TEMP. `git checkout -- <path>` is never
used: it reverts to HEAD and has destroyed uncommitted work on this machine.
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "..", "..", "..", "docs", "research",
                      "BUILD-GATE-4.md")
BACKUP = os.path.join(os.environ["TEMP"], "negctl_blotch_BG4.md")
BT = chr(96)

DEFECTS = [
    ("D1 blotch point estimate",
     "| | | G400 | 4.0 | **0.9643 [0.9298, 0.9866]** * | -0.84% | **0.0842** |",
     "| | | G400 | 4.0 | **0.9648 [0.9298, 0.9866]** * | -0.84% | **0.0842** |"),
    ("D2 bootstrap CI bound",
     "| | | G300 | 3.0 | 0.8980 [0.8618, 0.9262] * | -79.98% * | 0.3105 |",
     "| | | G300 | 3.0 | 0.8980 [0.8518, 0.9262] * | -79.98% * | 0.3105 |"),
    ("D3 sharpness delta",
     "| | | G200 | 2.0 | 0.9836 [0.9803, 0.9867] * | -39.93% * | 0.6159 |",
     "| | | G200 | 2.0 | 0.9836 [0.9803, 0.9867] * | -35.93% * | 0.6159 |"),
    ("D4 grain column",
     "| | | G300 | 3.0 | 0.9882 [0.9854, 0.9908] * | -55.52% * | 0.4009 |",
     "| | | G300 | 3.0 | 0.9882 [0.9854, 0.9908] * | -55.52% * | 0.4509 |"),
    ("D5 knee arm",
     "| %sbee-1-cpl%s | 299 | G400 | **-3.57%%** [-7.02, -1.34] | -0.84%% null "
     "| **6.1%%** |" % (BT, BT),
     "| %sbee-1-cpl%s | 299 | G300 | **-3.57%%** [-7.02, -1.34] | -0.84%% null "
     "| **6.1%%** |" % (BT, BT)),
    ("D6 degeneracy correlation",
     "| %sbee-1-cpl%s | 0.9922 | **0.6011** |" % (BT, BT),
     "| %sbee-1-cpl%s | 0.9922 | **0.7011** |" % (BT, BT)),
    ("D7 gate authority",
     "| %sflower-bud-alone-cpl%s | 205 | 89.12%% | G140 |" % (BT, BT),
     "| %sflower-bud-alone-cpl%s | 205 | 79.12%% | G140 |" % (BT, BT)),
    ("D8 Spearman",
     "`Spearman(N, sharpness authority) = -0.30` over five subjects.",
     "`Spearman(N, sharpness authority) = -0.70` over five subjects."),
]


def verify():
    r = subprocess.run([sys.executable,
                        os.path.join(HERE, "verify_blotch.py")],
                       capture_output=True, cwd=HERE)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def main():
    shutil.copyfile(REPORT, BACKUP)
    try:
        rc, _ = verify()
        print("BASELINE: verify_blotch.py rc=%d  %s"
              % (rc, "GREEN" if rc == 0 else "RED"))
        if rc != 0:
            print("baseline is not green; the control cannot be interpreted")
            return 1

        caught = missed = 0
        for name, old, new in DEFECTS:
            d = io.open(BACKUP, "rb").read().decode("utf-8")
            n = d.count(old)
            if n != 1:
                raise SystemExit(
                    "MUTATION TARGET NOT FOUND OR NOT UNIQUE for %s: %d "
                    "occurrences. A control that cannot plant its defect is "
                    "not a control." % (name, n))
            io.open(REPORT, "wb").write(d.replace(old, new, 1).encode("utf-8"))
            rc, out = verify()
            if rc != 0:
                caught += 1
                line = [x for x in out.split("\n") if x.strip().startswith("FAIL")]
                print("  %-28s RED   caught -- %s"
                      % (name, line[0].strip()[:90] if line else "(no FAIL line)"))
            else:
                missed += 1
                print("  %-28s GREEN MISSED -- the verifier does not check this"
                      % name)
            shutil.copyfile(BACKUP, REPORT)

        rc, _ = verify()
        print("\nRESTORED: verify_blotch.py rc=%d  %s"
              % (rc, "GREEN" if rc == 0 else "RED"))
        print("NEGATIVE CONTROL: %d/%d caught, %d missed"
              % (caught, len(DEFECTS), missed))
        return 0 if (missed == 0 and rc == 0) else 1
    finally:
        if os.path.exists(BACKUP):
            shutil.copyfile(BACKUP, REPORT)


if __name__ == "__main__":
    sys.exit(main())
