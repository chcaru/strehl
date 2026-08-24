"""Controls for the C1 blank-line fix. A gate change needs plants, not a green run.

The fix narrows KIND_TOKEN so a citation may wrap one line but not cross a blank
line. The risk is that it also stops catching REAL dangling citations that happen
to sit across a line break -- 172 legitimate citations live there.

Four bars, all pre-registered here before running:

  R1 (RED)   a dangling `fact 99999` on ONE line          -> must still be caught
  R2 (RED)   a dangling `fact 99998` across ONE newline   -> must still be caught
  G1 (GREEN) `## Questions` + blank + `1. text`           -> must NOT be caught
  G2 (GREEN) the real corpus, M87's phantom `question 49` -> must be gone, and no
             other violation count may change

Plants go in a scratch .md file inside the repo tree (the linter walks the tree),
removed in a finally block. Nothing under D:\\ is touched. No git checkout is used.
"""
import io
import os
import re
import subprocess
import sys

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
LINT = os.path.join(ROOT, "scripts", "corpus_lint.py")
PLANT = os.path.join(ROOT, "docs", "research", "ZZZ-c1-control.md")


def run_lint():
    p = subprocess.run([sys.executable, LINT], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def c1_lines(out):
    """Split the linter's output into violation RECORDS, not lines.

    A violation message quotes the raw citation, and a wrapped citation CONTAINS
    a newline -- so a C1 record can span two output lines. Splitting on "\\n" and
    testing `"99998" in line` reported a FAIL for R2 on a fix that was correct:
    the record was present, the number just sat on the record's second line.
    Records are delimited by the `path:line: [CODE]` prefix instead.
    """
    recs, cur = [], None
    for l in out.split("\n"):
        if re.match(r"^\S+:\d+: \[[A-Z]\d\] ", l):
            if cur is not None:
                recs.append(cur)
            cur = l
        elif cur is not None:
            if l.startswith("corpus_lint:") or not l.strip():
                recs.append(cur)
                cur = None
            else:
                cur += " " + l.strip()
    if cur is not None:
        recs.append(cur)
    return [r for r in recs if "[C1]" in r]


BODY = """# ZZZ C1 control

Status: scratch control file, deleted by c1_controls.py.

R1 same-line dangling citation: see fact 99999 for the detail.

R2 dangling citation across one wrapped line, which is where the corpus really
lives, as recorded in fact
99998 and nowhere else.

## Questions

1. Does the heading above get read as a citation to question 1?
"""


def main():
    assert not os.path.exists(PLANT), "control file already exists; refusing to clobber"

    # --- G2 first: the real corpus, unplanted -----------------------------
    rc0, out0 = run_lint()
    base = c1_lines(out0)
    m87 = [l for l in base if "M87-occlusion" in l and "question" in l]
    print("=== G2  real corpus, no plant ===")
    print(f"  C1 violations now                  : {len(base)}")
    print(f"  M87 phantom `question 49` present  : {len(m87)}   (want 0)")
    for l in base:
        print("    " + l.strip())
    g2 = (len(m87) == 0)

    try:
        with io.open(PLANT, "w", encoding="utf-8", newline="\n") as f:
            f.write(BODY)
        rc1, out1 = run_lint()
        planted = c1_lines(out1)
        mine = [l for l in planted if "ZZZ-c1-control" in l]
        others = [l for l in planted if "ZZZ-c1-control" not in l]

        print()
        print("=== plants ===")
        for l in mine:
            print("    " + l.strip())

        r1 = any("99999" in l for l in mine)
        r2 = any("99998" in l for l in mine)
        g1 = not any(re.search(r"`[Qq]uestions?\s+1`", l) for l in mine)
        g3 = (len(others) == len(base))
    finally:
        if os.path.exists(PLANT):
            os.remove(PLANT)

    print()
    print("=== bars ===")
    bars = [
        ("R1 same-line dangling fact 99999 caught", r1),
        ("R2 wrapped dangling fact 99998 caught", r2),
        ("G1 heading `## Questions` + `1.` NOT caught", g1),
        ("G2 M87 phantom `question 49` gone", g2),
        ("G3 no other violation count changed", g3),
    ]
    for name, ok in bars:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    ok = all(b for _, b in bars)
    print()
    print("ALL BARS PASS" if ok else "*** BARS FAILED ***")
    # verify the plant file is gone
    assert not os.path.exists(PLANT), "control file left behind"
    print("control file removed:", not os.path.exists(PLANT))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
