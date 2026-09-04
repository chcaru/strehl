"""Commission the cross-document derived checks in v2954.py.

A check that has never been shown to fail is not evidence. These three read the
scorecard -- a document another lane edits -- and re-derive what STATUS 2.9.61
and 2.9.65 assert about it. Each mutation below plants the exact defect one
check exists to catch.

The scorecard is backed up to TEMP and restored from that copy, never from git.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "experiments" / "ORCH-verify" / "v2954.py"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
BACKUP = Path(tempfile.gettempdir()) / "xdoc-scorecard-backup.md"

# (check label that must flip to XFAIL, unique anchor, replacement)
MUTATIONS = [
    # Drop M7 from the (d) set: the recomputed axis list must stop matching.
    ("blocker (d) axis set",
     "| M7 | **(b)(c)(d)** | No traceable colour target exists. |",
     "| M7 | **(b)(c)** | No traceable colour target exists. |"),
    # Add M10 to the (d) set: the exact error I made when briefing M175.
    ("blocker (d) axis set",
     "| M10 | **DEFINITION BLOCKED beyond M163; (b)(c)**",
     "| M10 | **DEFINITION BLOCKED beyond M163; (b)(c)(d)**"),
    # Remove M3's (a)/(d) codes: STATUS 2.9.61's correction would be unsourced.
    ("m3 carries (a)(b)(d)",
     "| M3 | **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`; (a)(b)(d)** |",
     "| M3 | **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`; (b)** |"),
    # Weaken all-arms-required to any-arm-suffices: the load-bearing quote for
    # STATUS 2.9.65's claim that a free fork rebuild cannot clear (d) alone.
    ("all-arms-required rule",
     "the named-comparator requirement is unmet and the dependent comparative",
     "the named-comparator requirement is satisfied and the dependent comparative"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def run() -> tuple[int, str]:
    r = subprocess.run([sys.executable, "-B", str(VERIFIER)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return r.returncode, r.stdout + r.stderr


def main() -> int:
    original = sha(SCORECARD)
    shutil.copy2(SCORECARD, BACKUP)
    print("backup        : %s" % BACKUP)
    print("scorecard sha : %s" % original)

    rc, out = run()
    if rc != 0 or "VERDICT: GREEN" not in out:
        print("PRECONDITION FAILED: verifier is not GREEN before commissioning.")
        print(out[-1500:])
        return 1
    print("precondition  : GREEN\n")

    caught, missed = 0, []
    try:
        for label, anchor, replacement in MUTATIONS:
            text = BACKUP.read_text(encoding="utf-8")
            if anchor not in text:
                raise SystemExit(
                    "MUTATION TARGET NOT FOUND for %r: %r" % (label, anchor))
            if text.count(anchor) != 1:
                raise SystemExit(
                    "MUTATION ANCHOR NOT UNIQUE for %r (%d hits)"
                    % (label, text.count(anchor)))
            SCORECARD.write_text(text.replace(anchor, replacement, 1),
                                 encoding="utf-8", newline="")
            rc, out = run()
            fired = ("XFAIL %-24s" % label).rstrip() in out or (
                "XFAIL " + label) in out
            if rc != 0 and fired:
                print("  RED   %-24s control PASSED" % label)
                caught += 1
            else:
                print("  %-5s %-24s *** CONTROL FAILED -- CHECK IS A NO-OP ***"
                      % ("GREEN" if rc == 0 else "RED", label))
                missed.append(label)
    finally:
        shutil.copy2(BACKUP, SCORECARD)

    restored = sha(SCORECARD)
    print("\nrestored sha  : %s" % restored)
    print("restore       : %s" % ("byte-identical to backup"
                                  if restored == original else "*** MISMATCH ***"))
    rc, out = run()
    print("final run     : %s" % ("GREEN" if rc == 0 else "RED"))

    total = len(MUTATIONS)
    print("\ncontrols      : %d caught + %d missed = %d of %d"
          % (caught, len(missed), caught + len(missed), total))
    if missed:
        print("MISSED        : %s" % missed)
    ok = (caught == total and restored == original and rc == 0)
    print("\nVERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
