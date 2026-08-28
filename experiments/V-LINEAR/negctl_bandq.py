"""Negative control on commission_bandq.py itself.

A harness that reads 16/16 on a working tool and 16/16 on a broken one is not
a harness.  This sabotages `bandq.py` in two specific ways and requires the
harness to go RED for each.

Sabotage 2 is the one that matters: it is ORCH's named failure mode -- a typo
silently reported as UNQUALIFIED, so a misspelled subject looks exactly like a
working licence refusal.  If the harness cannot see that, the harness is
certifying the wrong thing.

Restores from a $env:TEMP copy, never `git checkout --`.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
BANDQ = os.path.join(HERE, "bandq.py")
HARNESS = os.path.join(HERE, "commission_bandq.py")

SABOTAGE = [
    ("always-licence",
     "make every query exit 0. A gate that licenses everything is the most "
     "dangerous possible defect and the easiest to ship by accident.",
     lambda s: s.replace(
         "    return sys.exit(main(sys.argv[1:]))", "    sys.exit(0)")
     if "return sys.exit" in s else
     s.replace("    sys.exit(main(sys.argv[1:]))", "    main(sys.argv[1:]); sys.exit(0)")),

    ("typo-becomes-unqualified",
     "ORCH's named failure mode: report a nonexistent subject as UNQUALIFIED "
     "instead of UNKNOWN, so a typo reads like a working refusal.",
     lambda s: s.replace("        return UNKNOWN\n",
                         "        return UNQUALIFIED\n")),

    ("marginal-counts-as-licensed",
     "silently treat MARGINAL as a licence. Every PASS and FAIL arm still "
     "passes; only the marginal arms move.",
     lambda s: s.replace("        return PASS if allow_marginal else MARGINAL",
                         "        return PASS")),
]


def main():
    backup = tempfile.mktemp(suffix=".py.bak")
    shutil.copy2(BANDQ, backup)
    original = open(backup, "rb").read()
    reds = 0
    try:
        for name, why, mutate in SABOTAGE:
            src = open(BANDQ, encoding="utf-8").read()
            new = mutate(src)
            if new == src:
                print("[SABOTAGE FAILED TO APPLY] %s -- anchor not found. "
                      "A control that does not land reads as a pass." % name)
                return 1
            open(BANDQ, "w", encoding="utf-8", newline="").write(new)
            p = subprocess.run([sys.executable, HARNESS], cwd=HERE,
                               capture_output=True)
            rc = p.returncode
            out = p.stdout.decode("utf-8", "replace")
            wrong = [l for l in out.splitlines() if l.startswith("[WRONG")
                     or l.startswith("[FALSE ALARM")]
            ok = rc != 0
            print("[%-4s] harness exit=%d  %d arm(s) moved  %s"
                  % ("RED" if ok else "GREEN", rc, len(wrong), name))
            print("        why: %s" % why)
            for l in wrong[:4]:
                print("        %s" % l.strip())
            if ok:
                reds += 1
            else:
                print("        THE HARNESS DID NOT NOTICE. It certifies "
                      "nothing about this behaviour.")
            shutil.copy2(backup, BANDQ)
    finally:
        shutil.copy2(backup, BANDQ)
        restored = open(BANDQ, "rb").read() == original
        os.remove(backup)

    print()
    print("bandq.py restored byte-identical: %s" % ("yes" if restored else "NO"))
    print("%d/%d sabotages caught" % (reds, len(SABOTAGE)))
    return 0 if (reds == len(SABOTAGE) and restored) else 1


if __name__ == "__main__":
    sys.exit(main())
