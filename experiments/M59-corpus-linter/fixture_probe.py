"""M59 fixture probe: prove invariants A and B have power, on SYNTHETIC documents.

`power_probe.py` proves the original ten checks by planting violations into a
copy of the real SYNTHESIS.md. The orchestrator asked for these two invariants
to be proven differently -- each fixture is a small document built from nothing,
so the fixture states exactly the property under test and nothing else.

Every fixture asserts three things, not one (AGENTS rule 36, SYNTHESIS
discipline 351: a red exit code is not evidence of the red you wanted):

  1. the exit code is what the fixture expects,
  2. the output contains a needle specific to THIS fixture,
  3. the output contains no `Traceback` -- a crash also exits non-zero.

Run:  python experiments/M59-corpus-linter/fixture_probe.py
Exit: 0 if every fixture behaved as declared, 1 otherwise.
"""
import io
import os
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROBE = os.path.join(HERE, ".fixtures")
LINT = os.path.join("scripts", "corpus_lint.py")
SYN_REL = os.path.join("docs", "research", "SYNTHESIS.md")

HEAD = """# Strehl — synthetic fixture

## 4. Measured facts that constrain the design

| # | Fact | Consequence | Source |
|---|------|-------------|--------|
"""


def doc(facts="", s5="", s6="", s10=""):
    """A minimal SYNTHESIS-shaped document. §4, §5 and §10 are mandatory: the
    linter's Index resolves fact rows against §4's span."""
    return (HEAD + facts
            + "\n## 5. Engineering discipline\n\n" + s5
            + "\n## 6. Novelty — verified gaps, labelled as bets\n\n" + s6
            + "\n## 10. Open questions\n\n" + s10)


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


def write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def run(text, only, advisory=False):
    rmtree(PROBE)
    write(os.path.join(PROBE, SYN_REL), text)
    cmd = [sys.executable, LINT, "--root", os.path.relpath(PROBE, ROOT)]
    for o in only:
        cmd += ["--only", o]
    if advisory:
        cmd += ["--advisory"]
    p = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# --------------------------------------------------------------------------
# fixtures: (name, expectation, checks, needle, document)
# --------------------------------------------------------------------------

CLEAN_5 = "170. **A discipline that closes its bold span.** Body text.\n"
CLEAN_10 = "170. **A question that closes its bold span.** Body text.\n"

FIXTURES = [

    # ---- negative control -------------------------------------------------
    ("control: a well-formed document", "silent",
     ["S5", "N5", "C1", "N1", "N2"], None,
     doc(facts="| 1 | **A fact.** | None. | M1 |\n",
         s5=CLEAN_5, s10=CLEAN_10)),

    # ---- invariant B, must fire ------------------------------------------
    ("B1: opening `**` consumed by a prepended clause", "fire",
     ["S5"], "discipline 170",
     doc(s5="170. Superseded by M58c, A discipline whose opening marker was "
            "eaten.** Body text.\n",
         s10=CLEAN_10)),

    ("B2: item ending `.****` (over-closed)", "fire",
     ["S5"], "discipline 221",
     doc(s5="221. **A discipline that over-closes its span.****\n",
         s10=CLEAN_10)),

    # ---- invariant B, must NOT fire --------------------------------------
    ("B3: a bold span spanning three continuation lines", "silent",
     ["S5"], None,
     doc(s5="9. **A headline.** The span below opens here and does not close\n"
            "   until the third continuation line, which is **legitimate\n"
            "   markdown: emphasis may cross a soft line break inside one\n"
            "   list item** and does close.\n",
         s10=CLEAN_10)),

    ("B4: a literal `**` inside a code span", "silent",
     ["S5"], None,
     doc(facts="| 7 | **A fact naming the `**` token.** | None. | M1 |\n",
         s5="9. **A discipline about markup.** Write `**` when you mean bold;\n"
            "   a bare `**` in a code span is not markup.\n",
         s10=CLEAN_10)),

    # ---- invariant A, must fire ------------------------------------------
    ("A1: `Question N` where N exists only in §5", "fire",
     ["C1"], "no question 170",
     doc(facts="| 3 | **Question 170 is MOOT.** | None. | M58 |\n",
         s5="170. **A discipline.** M58c: the verdict landed here by mistake, "
            "`MOOT`.\n",
         s10="171. **An unrelated question.** Body.\n")),

    ("A2: a numbered item in §6, which holds no namespace", "fire",
     ["N5"], "§6",
     doc(s5=CLEAN_5, s6="170. **A discipline filed under Novelty.** Body.\n",
         s10=CLEAN_10)),

    # ---- invariant A, must NOT fire --------------------------------------
    ("A3: N present in BOTH §5 and §10 as unrelated items", "silent",
     ["C1", "N1", "N5", "S5"], None,
     doc(facts="| 3 | **See discipline 12 and question 12.** | None. | M1 |\n",
         s5="12. **A discipline numbered 12.** Body.\n",
         s10="12. **An unrelated question also numbered 12.** Body.\n")),

    # ---- the advisory must be able to fire, and must not fail the run ----
    ("A4: status claim uncorroborated by §10 (ADVISORY: exit stays 0)",
     "advisory", ["C1"], "does not carry that word",
     doc(facts="| 3 | **Question 170 is MOOT.** | None. | M58 |\n",
         s5=CLEAN_5,
         s10="170. **A question still open.** Nothing has settled it.\n")),
]


def main():
    if not os.path.isfile(os.path.join(ROOT, LINT)):
        sys.stderr.write("fixture_probe: %s not found\n" % LINT)
        return 2
    width = max(len(f[0]) for f in FIXTURES)
    failures = []
    print("fixture            expectation  exit  verdict  fixture")
    print("-" * (width + 42))
    for name, expect, only, needle, text in FIXTURES:
        code, out = run(text, only, advisory=(expect == "advisory"))
        problems = []
        if "Traceback" in out:
            problems.append("CRASHED, not a check firing")
        if expect == "fire" and code != 1:
            problems.append("expected exit 1, got %d" % code)
        if expect == "silent" and code != 0:
            problems.append("expected exit 0, got %d" % code)
        if expect == "advisory" and code != 0:
            problems.append("advisory must not affect the exit code, got %d" % code)
        if needle and needle not in out:
            problems.append("output never mentions %r" % needle)
        if expect == "silent" and needle is None and "FAIL" in out:
            problems.append("fired on legitimate content")
        if expect == "fire":
            ids = [c for c in only if "[%s]" % c in out]
            if not ids:
                problems.append("no %s violation in the output" % "/".join(only))
        verdict = "ok" if not problems else "BAD"
        if problems:
            failures.append((name, problems, out))
        print("%-*s  %-11s  %-4d  %-7s" % (width, name, expect, code, verdict))
    print("")
    for name, problems, out in failures:
        print("=" * 78)
        print("FIXTURE FAILED: %s" % name)
        for p in problems:
            print("  - %s" % p)
        print("--- unfiltered output ---")
        print(out)
    rmtree(PROBE)
    print("fixture_probe: %d of %d fixtures behaved as declared"
          % (len(FIXTURES) - len(failures), len(FIXTURES)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
