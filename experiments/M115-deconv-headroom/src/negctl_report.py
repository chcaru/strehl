"""Negative control on verify_report.py -- a green is a claim about the verifier.

Copies the report to TEMP first and restores from that copy.  It NEVER uses
`git checkout -- <path>`, which reverts to HEAD and has destroyed uncommitted
work on this machine.

Each planted defect is anchored on a UNIQUE full string and the script
hard-errors if the anchor does not land, because `str.replace(x, y, 1)` on a
non-unique token silently mutates the wrong site and reports a meaningless
green.
"""
import os, shutil, subprocess, sys, tempfile

DOC = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M115-deconv-headroom.md"
VER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_report.py")

DEFECTS = [
    ("D1 headline value",
     "band-SNR ratio of **1.0014 \u00b1 0.0184** against the shipped",
     "band-SNR ratio of **1.2014 \u00b1 0.0184** against the shipped"),
    ("D2 headline error bar",
     "ratio of **1.0014 \u00b1 0.0184** against the shipped",
     "ratio of **1.0014 \u00b1 0.0034** against the shipped"),
    ("D3 ringing halo",
     "to **70.7 %** at 8\u201316 px, falling to",
     "to **20.7 %** at 8\u201316 px, falling to"),
    ("D4 gradient-metric fooling factor",
     "metric was moved **8.25\u00d7** by the same information-free",
     "metric was moved **1.25\u00d7** by the same information-free"),
    ("D5 OTF over-estimate",
     "over-estimates the defocus scale by **1.87\u00d7** and **2.15\u00d7**",
     "over-estimates the defocus scale by **1.07\u00d7** and **2.15\u00d7**"),
    ("D6 injection-channel phantom SNR",
     "reported mid-band SNR of **84.9** for a per-pixel selector",
     "reported mid-band SNR of **8.49** for a per-pixel selector"),
]


def run():
    p = subprocess.run([sys.executable, VER], capture_output=True, text=True)
    return p.returncode


def main():
    tmp = os.path.join(tempfile.gettempdir(), "M115_report_backup.md")
    shutil.copy2(DOC, tmp)
    print(f"backup -> {tmp}")
    orig = open(DOC, encoding="utf-8").read()

    rc = run()
    print(f"\nbaseline (unmutated): rc={rc}  -> "
          f"{'GREEN' if rc == 0 else 'RED (the verifier is broken, not the report)'}")
    if rc != 0:
        shutil.copy2(tmp, DOC)
        sys.exit("baseline is not green; aborting before planting anything")

    caught, missed = 0, []
    try:
        for name, old, new in DEFECTS:
            n = orig.count(old)
            if n != 1:
                raise SystemExit(f"MUTATION TARGET NOT UNIQUE for {name}: "
                                 f"found {n} occurrences of {old!r}")
            open(DOC, "w", encoding="utf-8").write(orig.replace(old, new, 1))
            rc = run()
            ok = rc != 0
            print(f"  {'CAUGHT ' if ok else 'MISSED '} {name:36s} rc={rc}")
            if ok:
                caught += 1
            else:
                missed.append(name)
            open(DOC, "w", encoding="utf-8").write(orig)
    finally:
        shutil.copy2(tmp, DOC)

    rc = run()
    print(f"\nrestored: rc={rc} -> {'GREEN' if rc == 0 else 'RED'}")
    print(f"negative control: {caught}/{len(DEFECTS)} planted defects caught")
    if missed:
        print("  MISSED: " + ", ".join(missed))
        sys.exit(1)


if __name__ == "__main__":
    main()
