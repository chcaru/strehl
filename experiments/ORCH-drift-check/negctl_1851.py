"""Negative control for the fact-bank lint.

A lint that passes proves nothing unless it can fail. This plants two defects of
the exact classes the insert script guards against -- an odd asterisk count and a
raw pipe -- inside a row I just added, and requires the linter to FAIL on each.

Safety: the file is copied to %TEMP% first and restored from that copy. Never
`git checkout --`, which reverts to HEAD and would destroy the 14 uncommitted
rows plus anything else uncommitted in the file.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
PATH = os.path.join(ROOT, "docs", "research", "SYNTHESIS.md")
LINT = os.path.join(ROOT, "scripts", "corpus_lint.py")

# Anchored on a unique full substring of a row inserted this session. An anchor
# that fails to land makes a mutation silently absent, and the resulting GREEN
# reads exactly like a linter that works.
ARMS = [
    ("odd asterisk", "**COMMISSIONING PROVED SENSITIVITY", "***COMMISSIONING PROVED SENSITIVITY", "S5"),
    ("raw pipe", "with run-start phase near-uniform mod 2/4/8/16/32", "with run-start phase near-uniform mod 2|4|8|16|32", "S1"),
]


def read():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write(text):
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def run_lint():
    proc = subprocess.run(
        [sys.executable, LINT, "--root", "."],
        cwd=ROOT, capture_output=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).decode("utf-8", "replace")


def main():
    original = read()
    backup = os.path.join(tempfile.gettempdir(), "SYNTHESIS.negctl.bak.md")
    shutil.copy2(PATH, backup)
    print("backup -> %s (%d bytes)" % (backup, os.path.getsize(backup)))

    # Baseline: the linter must be quiet on SYNTHESIS.md specifically. Another
    # lane's file is currently failing S3, so key on our own path, not exit code.
    rc0, out0 = run_lint()
    syn0 = [ln for ln in out0.splitlines() if "SYNTHESIS.md" in ln]
    print("BASELINE rc=%d  SYNTHESIS.md violations=%d" % (rc0, len(syn0)))
    for ln in syn0:
        print("   " + ln)

    results = []
    try:
        for name, old, new, expect in ARMS:
            if original.count(old) != 1:
                raise SystemExit(
                    "MUTATION TARGET NOT FOUND: %r occurs %d times, need exactly 1"
                    % (old, original.count(old))
                )
            write(original.replace(old, new, 1))
            rc, out = run_lint()
            syn = [ln for ln in out.splitlines() if "SYNTHESIS.md" in ln]
            caught = any(("[%s]" % expect) in ln for ln in syn)
            results.append((name, expect, caught, len(syn)))
            print("ARM %-14s expect %s -> rc=%d  SYNTHESIS violations=%d  CAUGHT=%s"
                  % (name, expect, rc, len(syn), caught))
            for ln in syn[:3]:
                print("   " + ln)
            write(original)
    finally:
        write(original)
        restored = read()
        ok = restored == original
        print("RESTORED byte-identical: %s" % ok)
        if not ok:
            shutil.copy2(backup, PATH)
            print("restored from %TEMP% copy instead")

    missed = [r for r in results if not r[2]]
    print()
    if len(syn0) != 0:
        print("VERDICT: INVALID -- baseline was not clean on SYNTHESIS.md")
        return 1
    if missed:
        print("VERDICT: RED -- linter blind to %d of %d planted defects: %s"
              % (len(missed), len(ARMS), [m[0] for m in missed]))
        return 1
    print("VERDICT: GREEN -- %d of %d planted defects caught, baseline clean"
          % (len(ARMS), len(ARMS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
