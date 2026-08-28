"""Commission ORCH's pass/fail channel in V-KILLB0's verdict.py.

The channel was added because `verdictaudit.py` proved every designed outcome in
that file exited 0, including a run that printed the word FAIL.  A fix for a
green-when-it-should-be-red defect is worthless until it has been shown to go RED
under a known-potent sabotage, so this plants three and requires a non-zero exit
from each, plus a null that must stay 0.

Method constraints, both earned elsewhere on this project:
  * every mutation is anchored on a UNIQUE FULL LINE and hard-errors if it does
    not land exactly once -- a bare replace() hits the first textual match, which
    is routinely not the site meant, and the run then reads GREEN for the wrong
    reason;
  * the original is restored from a %TEMP% byte copy, never from git, and the
    restoration is verified byte-identical before the script exits.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

TARGET = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-KILLB0\verdict.py"

# (label, class, anchor line, replacement, expected exit, substring that must appear)
ARMS = [
    ("null", "NULL", None, None, 0, "VERDICT BINDING PASSED"),

    ("del_arm", "DELETION",
     'arm("A7 bee flat R stands clear of the permuted null", a7)',
     "",
     1, "ARM SET CHANGED"),

    ("rename_arm", "SUBSTITUTION",
     'arm("A1 loss reduced above the denoise floor", a1)',
     'arm("A1 renamed but still counted", a1)',
     1, "ARM SET CHANGED"),

    ("neuter_arm", "MISS",
     '        f["obs_struct"]["leaf-2-cpl"][b] = 0.995',
     "        pass",
     1, "were MISSED"),
]


def read_bytes(path):
    with io.open(path, "rb") as fh:
        return fh.read()


def run(path):
    p = subprocess.run([sys.executable, path], capture_output=True)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    original = read_bytes(TARGET)
    backup = os.path.join(tempfile.gettempdir(), "verdict_py_commission_backup.py")
    with io.open(backup, "wb") as fh:
        fh.write(original)
    print("backed up %d bytes to %s" % (len(original), backup))

    text = original.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"

    results = []
    try:
        for label, klass, anchor, repl, want_exit, want_sub in ARMS:
            if anchor is None:
                mutated = text
            else:
                lines = text.split(newline)
                hits = [i for i, ln in enumerate(lines) if ln == anchor]
                if len(hits) != 1:
                    raise SystemExit(
                        "MUTATION TARGET NOT FOUND: arm %r anchor matched %d lines, "
                        "expected exactly 1. Anchor was %r" % (label, len(hits), anchor))
                lines[hits[0]] = repl
                mutated = newline.join(lines)
                if mutated == text:
                    raise SystemExit("ARM %r CHANGED NOTHING -- inert plant" % label)

            with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
                fh.write(mutated)
            rc, out = run(TARGET)

            exit_ok = (rc != 0) if want_exit else (rc == 0)
            sub_ok = want_sub in out
            verdict = "GOOD" if (exit_ok and sub_ok) else "**BAD**"
            results.append((label, klass, rc, want_exit, sub_ok, verdict))
            print("  %-11s %-12s exit=%-3d want%s  message=%-5s  %s"
                  % (label, klass, rc, ("!=0" if want_exit else "==0"), sub_ok, verdict))
            if verdict == "**BAD**":
                tail = [ln for ln in out.splitlines() if ln.strip()][-3:]
                for ln in tail:
                    print("        | " + ln)
    finally:
        shutil.copyfile(backup, TARGET)
        restored = read_bytes(TARGET)
        if restored != original:
            raise SystemExit("RESTORE FAILED: %s does not match the backup" % TARGET)
        print("restored byte-identical (%d bytes)" % len(restored))

    bad = [r for r in results if r[-1] == "**BAD**"]
    print("\n%d/%d arms behaved correctly" % (len(results) - len(bad), len(results)))
    if bad:
        print("COMMISSIONING FAILED -- the pass/fail channel is not trustworthy")
        return 1
    print("COMMISSIONING PASSED -- the channel goes RED on deletion, on a silent "
          "rename, and on a missed arm, and stays GREEN on the unmutated file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
