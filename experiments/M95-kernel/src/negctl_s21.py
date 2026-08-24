"""Negative control for verify_s21.py.

Section 21 is about a gate that reported nothing and was read as reporting
success, so a verifier for it that has only ever been shown passing would be
the same mistake one level up. This plants seven defects, one at a time, and
requires a RED on each.

Every mutation is anchored on a string that lies WITHIN A SINGLE LINE and is
UNIQUE in the file, both hard-checked before anything is written, because this
milestone has already paid for a control that silently mutated the wrong
occurrence and for one whose anchor spanned a line break in wrapped prose.

CAUGHT requires `rc == 1 and bad > 0`: the exact exit code the verifier uses
for a subject failure, plus a positive signal parsed from its stdout. A crash
exits 2 and prints no BAD line, so it cannot be counted as a catch. The final
arm proves that rather than asserting it.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
VERIFY = Path(__file__).resolve().parent / "verify_s21.py"
PREFIX = ROOT / "experiments" / "M95-kernel" / "out" / "k18_gate702_PREFIX.txt"

MUTATIONS = [
    ("cp1252 arm char count",
     "| `PYTHONIOENCODING=cp1252` | 1 | 1937 | 35 | none |",
     "| `PYTHONIOENCODING=cp1252` | 1 | 1938 | 35 | none |"),
    ("the check it died at",
     "**B1 = EXPOSED.** It died at check 36 of 40, lost 363 characters of its own",
     "**B1 = EXPOSED.** It died at check 37 of 40, lost 363 characters of its own"),
    ("fleet exposure count",
     "**2 of 10 exposed, 3409 characters of verification output lost.**",
     "**3 of 10 exposed, 3409 characters of verification output lost.**"),
    ("post-fix fleet claim",
     "| fleet | **0 of 10 exposed**, `verify_s16.py` restored 4 \u2192 49 lines, GREEN |",
     "| fleet | **1 of 10 exposed**, `verify_s16.py` restored 4 \u2192 49 lines, GREEN |"),
    ("tool-failure exit codes",
     "| B4 | **FIXED**, tool-failure codes seen `[0, 2]`, never 1 |",
     "| B4 | **FIXED**, tool-failure codes seen `[0, 3]`, never 1 |"),
    ("the B3 verdict that could withdraw section 20",
     "**B3 = FAILS SAFE. Section 20's 5/5 stands.**",
     "**B3 = UNSOUND. Section 20's 5/5 stands.**"),
    ("mtime span read off the filesystem",
     "records the mtime span, 09:24:21 to 10:33:42, which is the same observation in a",
     "records the mtime span, 09:24:21 to 10:33:41, which is the same observation in a"),
]


def run_verifier():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, cwd=ROOT)
    out = r.stdout.decode("utf-8", "replace")
    bad = sum(1 for ln in out.splitlines() if ln.strip().startswith("BAD"))
    return r.returncode, bad


def main():
    original = REPORT.read_bytes()
    backup = Path(tempfile.gettempdir()) / "M95-kernel.md.s21.bak"
    backup.write_bytes(original)
    print(f"backed up {len(original)} bytes to {backup}\n")

    text = original.decode("utf-8")
    for _, old, _ in MUTATIONS:
        if "\n" in old:
            sys.exit(f"ANCHOR SPANS A LINE BREAK: {old!r}")
        n = text.count(old)
        if n != 1:
            sys.exit(f"MUTATION TARGET NOT UNIQUE ({n} occurrences): {old!r}")

    rc, _ = run_verifier()
    print(f"baseline: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        REPORT.write_bytes(original)
        sys.exit("baseline is not GREEN; refusing to run the control")

    caught = 0
    try:
        for label, old, new in MUTATIONS:
            REPORT.write_text(text.replace(old, new, 1), encoding="utf-8")
            rc, bad = run_verifier()
            if rc == 1 and bad > 0:
                print(f"  CAUGHT  {label:<48} rc={rc}  BAD={bad}")
                caught += 1
            else:
                print(f"  MISSED  {label:<48} rc={rc}  BAD={bad}")
            REPORT.write_bytes(original)
    finally:
        REPORT.write_bytes(original)

    same = REPORT.read_bytes() == original
    print(f"\nrestored byte-identical: {same}")
    rc, _ = run_verifier()
    print(f"post-restore: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    print(f"\nnegative control: {caught}/{len(MUTATIONS)} planted defects caught")

    # The arm this section exists to make standing. Break the verifier as a
    # TOOL, by removing a capture it must read, and require that it says so in
    # its exit code rather than presenting as a subject failure.
    print("\n-- tool-failure arm: a broken verifier must not score as a catch --")
    stash = PREFIX.read_bytes()
    try:
        PREFIX.unlink()
        tf_rc, tf_bad = run_verifier()
    finally:
        PREFIX.write_bytes(stash)
    restored = PREFIX.read_bytes() == stash
    scored = tf_rc == 1 and tf_bad > 0
    print(f"  removed {PREFIX.name} -> rc={tf_rc}  BAD={tf_bad}  "
          f"scored {'CAUGHT' if scored else 'MISSED'}")
    print(f"  capture restored byte-identical: {restored}")
    tool_ok = tf_rc == 2 and not scored and restored
    print(f"  tool failure exits {tf_rc}, subject failure exits 1, distinct: "
          f"{'PASS' if tool_ok else 'FAIL'}")

    # 21.9's ownership check passes trivially when the live capture happens to
    # be clean, which is the state it is in. A null that cannot fail is not a
    # measurement, so plant a violation naming a file I own and require it.
    print("\n-- power control: the ownership check must fail when it should --")
    lint_now = PREFIX.parent / "lint_s21_now.txt"
    lint_stash = lint_now.read_bytes()
    planted = "docs/research/M95-kernel.md:1: [S6] planted by the power control\n"
    try:
        lint_now.write_bytes(lint_stash.decode("utf-8").replace(
            "corpus_lint: checks run:", planted + "corpus_lint: checks run:", 1
        ).encode("utf-8"))
        pw_rc, pw_bad = run_verifier()
    finally:
        lint_now.write_bytes(lint_stash)
    lint_restored = lint_now.read_bytes() == lint_stash
    power_ok = pw_rc == 1 and pw_bad > 0 and lint_restored
    print(f"  planted a violation in a file I own -> rc={pw_rc}  BAD={pw_bad}")
    print(f"  capture restored byte-identical: {lint_restored}")
    print(f"  the ownership check can say otherwise: "
          f"{'PASS' if power_ok else 'FAIL'}")

    if not same:
        shutil.copyfile(backup, REPORT)
        sys.exit("RESTORE FAILED -- report recovered from the backup")
    return 0 if (caught == len(MUTATIONS) and rc == 0 and tool_ok and power_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
