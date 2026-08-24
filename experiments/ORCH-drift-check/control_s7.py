"""Negative control for corpus_lint check S7.

Green means nothing until the check has been shown to fire. Plant one control
character on a uniquely-anchored full line, prove the mutation landed, prove the
linter goes RED and names S7 at the right file and line, then restore from a
TEMP copy (never `git checkout --`) and prove it goes GREEN again.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET = os.path.join(ROOT, "docs", "research", "M105b-exposure-ship.md")
LINT = os.path.join(ROOT, "scripts", "corpus_lint.py")

# A full-line anchor, asserted unique. Anchoring on a short token is how a
# control silently mutates the wrong site (see the fold-control incident).
ANCHOR = "ship.md, experiments/M105b-exposure-verify/"


def run_lint():
    p = subprocess.run([sys.executable, LINT], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def main():
    code, out = run_lint()
    print("baseline lint: exit=%d" % code)
    assert code == 0, "baseline is not green; fix that before trusting a control\n" + out
    assert "OK" in out, "baseline did not report OK"

    with io.open(TARGET, "rb") as fh:
        original = fh.read()

    n = original.count(ANCHOR.encode())
    assert n == 1, "ANCHOR must be unique, found %d occurrence(s) -- MUTATION TARGET AMBIGUOUS" % n

    backup = os.path.join(tempfile.gettempdir(), "s7_control_backup.md")
    shutil.copy2(TARGET, backup)
    print("backed up to %s" % backup)

    try:
        # 'e' of "experiments" -> form feed, exactly the PowerShell `f/`e failure mode
        mutated = original.replace(
            ANCHOR.encode(), ANCHOR.encode().replace(b"experiments", b"\x0cxperiments"), 1)
        assert mutated != original, "MUTATION TARGET NOT FOUND -- control is inert, fix it"
        assert b"\x0c" in mutated, "planted byte absent after mutation"

        with io.open(TARGET, "wb") as fh:
            fh.write(mutated)

        code, out = run_lint()
        print("mutated lint: exit=%d" % code)
        red = code != 0
        named = "S7" in out
        located = "M105b-exposure-ship.md" in out
        print("  RED: %s   names S7: %s   names file: %s" % (red, named, located))
        for line in out.splitlines():
            if "S7" in line:
                print("  > " + line.strip()[:150])
        assert red, "CONTROL FAILED: linter stayed green with a planted control char\n" + out
        assert named, "CONTROL FAILED: linter went red but did not name S7\n" + out
        assert located, "CONTROL FAILED: S7 did not name the mutated file\n" + out
    finally:
        shutil.copy2(backup, TARGET)
        os.remove(backup)
        print("restored from backup")

    with io.open(TARGET, "rb") as fh:
        assert fh.read() == original, "RESTORE FAILED -- file differs from original"
    print("restore verified byte-identical")

    code, out = run_lint()
    print("post-restore lint: exit=%d" % code)
    assert code == 0, "did not return to green after restore\n" + out

    print("\nS7 NEGATIVE CONTROL: PASS (green -> red on plant -> green on restore)")


if __name__ == "__main__":
    main()
