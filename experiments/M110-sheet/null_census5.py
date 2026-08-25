"""Census stage 5: the adjudication sheet.

Four instruments were built for this census. THREE FAILED, each differently, and
the failures are the most useful output of the exercise:

  stage 1  regex: a draw landing IN image data.  Pinned the known member at
           exactly ca_overshoot.py:162.                             SOUND.
  stage 2  name screen (enclosing def / nearby comment says "null").
           FALSE-CLEARED the known member: its `# Inert null:` comment is at
           line 157 and the context window began at 158.  One line.  DEAD.
  stage 3  dataflow, tainted and clean value reaching the same callee/argpos.
           Reported the seed via `abs()`, `float()`, `str()`, `print()` --
           never via overshoot_by_radius.                            DEAD.
  stage 4  stage 3 + output differencing.  Taint SATURATED (22 of 22 names in
           main(), including `real` and `d_on`), so the true site at line 186
           read tainted-vs-tainted and was skipped.                  DEAD.

Stages 3 and 4 both printed "known member detected = True" because the
commissioning check asked whether the FILE appeared. A file-level presence check
is satisfied by any line in the file. Site-granular commissioning is mandatory.

So this stage does not classify. It prints the material -- injection site,
enclosing def, and the nearest preceding comment within a WIDE window -- and the
classification is made by reading. grep is the census, not the verdict.

Read-only. Names files and owners; changes nothing.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments"
RESEARCH = ROOT / "docs" / "research"
SELF = re.compile(r"null_census\d*\.py|_diag\.py")

INJECT = re.compile(
    r"(?:\+\s*(?:rng|np\.random|random)\.)"
    r"|(?:\+=\s*(?:rng|np\.random|random)\.)"
    r"|(?:\[[^\]]*\]\s*=\s*[^=]*(?:rng|np\.random|random)\.)")

COMMENT_WINDOW = 14          # stage 2 died at 4; widen and say so


def folded():
    out = {}
    for p in RESEARCH.glob("*.md"):
        m = re.match(r"(M\d+|m\d+)", p.stem)
        if m:
            out.setdefault(m.group(1).upper(), []).append(p.stem)
    return out


def enclosing_def(lines, i):
    for j in range(i, -1, -1):
        m = re.match(r"\s*def\s+(\w+)", lines[j])
        if m:
            return m.group(1)
    return "<module>"


def nearest_comment(lines, i):
    for j in range(i, max(-1, i - COMMENT_WINDOW), -1):
        s = lines[j].strip()
        if s.startswith("#") and len(s) > 4:
            return s.lstrip("# ").strip()
        if s.startswith(('"""', "'''")) and len(s) > 6:
            return s.strip("\"' ").strip()
    return ""


def main():
    want = sys.argv[1:] or None
    fold = folded()
    rows = []
    for p in sorted(EXP.rglob("*.py")):
        if SELF.match(p.name):
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        m = re.match(r"(M\d+|m\d+)", p.relative_to(EXP).parts[0])
        ms = m.group(1).upper() if m else "?"
        for i, line in enumerate(lines):
            if INJECT.search(line):
                rows.append((ms, p, i + 1, line.strip(),
                             enclosing_def(lines, i), nearest_comment(lines, i)))

    inf = [r for r in rows if r[0] in fold]
    print(f"stage-1 injection sites total          : {len(rows)} in "
          f"{len({r[1] for r in rows})} file(s)")
    print(f"  in milestones with a FOLDED report   : {len(inf)} in "
          f"{len({r[1] for r in inf})} file(s)   <- ORCH's cap")
    print(f"  in unfolded milestones (deferred)    : {len(rows) - len(inf)}\n")

    by_ms = {}
    for r in inf:
        by_ms.setdefault(r[0], []).append(r)
    print("folded milestones carrying injection sites "
          f"({len(by_ms)}), by site count:")
    for ms, rs in sorted(by_ms.items(), key=lambda x: -len(x[1])):
        print(f"  {ms:<7} {len(rs):>3} site(s)  "
              f"{len({r[1] for r in rs})} file(s)  "
              f"[{', '.join(sorted(fold[ms])[:2])}]")

    if not want:
        print("\npass milestone ids as argv to print the adjudication sheet")
        return 0

    print("\n" + "=" * 78)
    for ms in want:
        for r in sorted(by_ms.get(ms.upper(), []), key=lambda x: (x[1], x[2])):
            _, p, ln, line, fn, com = r
            print(f"\n{ms.upper()}  {p.relative_to(ROOT).as_posix()}:{ln}"
                  f"  def {fn}()")
            if com:
                print(f"     comment: {com[:96]}")
            print(f"     code   : {line[:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
