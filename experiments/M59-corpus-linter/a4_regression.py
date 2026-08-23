"""M59 pass 10: does the out-of-sample-driven A4 fix still catch the four real
defects it was built for?

The equivalence-class corroboration rule makes A4 STRICTLY MORE FORGIVING, which
is exactly the direction that silently kills a check (SYNTHESIS discipline 250,
and A4's own docstring: widening exclusions until the number goes away). So the
fix has to be tested against the state where the four real defects were live --
the SYNTHESIS blob at eceecb5, before the orchestrator repaired them.

This reconstructs a probe root from that blob and runs A4 against it. All four
must still fire. If any is lost, the fix is a regression and must be reverted.

Run: python experiments/M59-corpus-linter/a4_regression.py
Exit: 0 if all four still fire, 1 otherwise.
"""
import io
import os
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROBE = os.path.join(HERE, ".a4regress")
LINT = os.path.join("scripts", "corpus_lint.py")
SYN_REL = os.path.join("docs", "research", "SYNTHESIS.md")

# The blob in which A4 reported 4 violations, before the repair.
PRE_REPAIR = "eceecb5"
EXPECTED = [101, 80, 120, 161]


def rmtree(path):
    def onerror(func, p, exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if os.path.isdir(path):
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=lambda f, p, e: onerror(f, p, e))
        else:
            shutil.rmtree(path, onerror=onerror)


def main():
    p = subprocess.run(["git", "show", "%s:docs/research/SYNTHESIS.md" % PRE_REPAIR],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        sys.stderr.write("a4_regression: cannot read %s: %s\n"
                         % (PRE_REPAIR, p.stderr.decode("utf-8", "replace")))
        return 2
    rmtree(PROBE)
    dest = os.path.join(PROBE, SYN_REL)
    os.makedirs(os.path.dirname(dest))
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(p.stdout.decode("utf-8", "replace").replace("\r\n", "\n"))

    r = subprocess.run([sys.executable, LINT, "--root",
                        os.path.relpath(PROBE, ROOT), "--only", "A4"],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = r.stdout.decode("utf-8", "replace")
    print(out)
    rmtree(PROBE)

    if "Traceback" in out:
        print("a4_regression: CRASHED, not a check firing")
        return 1
    missing = [q for q in EXPECTED if "question %d is" % q not in out]
    print("pre-repair blob: %s" % PRE_REPAIR)
    print("expected still-detected: %s" % EXPECTED)
    if missing:
        print("a4_regression: REGRESSION -- the fix silenced question(s) %s"
              % missing)
        return 1
    print("a4_regression: all %d real defects still detected after the "
          "equivalence-class fix" % len(EXPECTED))
    return 0 if r.returncode == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
