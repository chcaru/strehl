"""M116-promotion -- commission verify_ladder.py by planting defects it must catch.

A green from an uncommissioned verifier is not evidence. This plants one defect
at a time into a COPY of the report and requires verify_ladder.py to go RED on
every one.

Safety, per this project's rules:
  * The real report is never mutated. Each arm copies it to a scratch file and
    points the verifier at the copy through M116_REPORT. There is no restore
    step to get wrong, and no `git checkout --` anywhere.
  * Every plant is anchored on a UNIQUE FULL-LINE string and hard-errors if the
    anchor is not found or is not unique. A plant that silently fails to land
    produces a green that means nothing -- the exact failure this script exists
    to rule out.

Run: python negctl_ladder.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research"
              r"\M116-promotion.md")

# (name, exact full line to find, replacement line, what it simulates)
PLANTS = [
    ("D1 last digit of the deciding blur number",
     "| fern | H1 | 40 | `+123.79` | `-0.30177` | `-0.22916` | 573588 |",
     "| fern | H1 | 40 | `+123.79` | `-0.30176` | `-0.22916` | 573588 |",
     "a one-digit typo in D at the shipped dose on the damage subject"),
    ("D2 sign-carrying number on the refuting subject",
     "| bee-3-cpl | L1 | 1 | `-2.18` | `+0.14468` | `+0.14505` | 585886 |",
     "| bee-3-cpl | L1 | 1 | `-2.18` | `+0.14568` | `+0.14505` | 585886 |",
     "an inflated D on the stack that refutes the blur confound"),
    ("D3 oriented-content number",
     "| fern | L20 | 20 | `+64.00` | `-0.29321` | `-0.19099` | 573588 |",
     "| fern | L20 | 20 | `+64.00` | `-0.29321` | `-0.19199` | 573588 |",
     "a drifted D_or, the hairs-and-claws statistic"),
    ("D4 a count taken from the tool's own log",
     "| bee-3-cpl | H2 | 80 | `+21.27` | `+0.11914` | `+0.09706` | 519621 |",
     "| bee-3-cpl | H2 | 80 | `+21.27` | `+0.11914` | `+0.09706` | 519620 |",
     "a re-elected count that no longer matches the tool"),
    ("D5 a delta label",
     "| bee-3-cpl | L10 | 10 | `+6.44` | `+0.03344` | `+0.01474` | 585886 |",
     "| bee-3-cpl | L10 | 11 | `+6.44` | `+0.03344` | `+0.01474` | 585886 |",
     "a mislabelled rung"),
    ("D6 a DELETED row",
     "| bee-3-cpl | L160 | 160 | `-0.00` | `+0.00000` | `+0.00000` | 0 |",
     "",
     "the dead rung quietly dropped from the table -- the plant that a "
     "presence-only verifier misses"),
    ("D7 the halo index that carries the dose-response claim",
     "| fern | L10 | 10 | `+26.46` | `-0.26812` | `-0.15270` | 573588 |",
     "| fern | L10 | 10 | `+16.46` | `-0.26812` | `-0.15270` | 573588 |",
     "a dHALO% that breaks monotonicity"),
]


def run(path: Path):
    env = dict(os.environ, M116_REPORT=str(path))
    p = subprocess.run([sys.executable, str(HERE / "verify_ladder.py")],
                       capture_output=True, text=True, env=env, cwd=str(HERE))
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    src = REPORT.read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="m116-negctl-"))

    # ---- arm 0: the unmutated copy must be GREEN ------------------------
    clean = tmp / "clean.md"
    shutil.copy2(REPORT, clean)
    rc, out = run(clean)
    print(f"[baseline] unmutated copy -> rc={rc}")
    print(f"           {out.splitlines()[-1] if out else ''}")
    if rc != 0:
        print("ABORT - the verifier does not pass on an unmutated report, so "
              "nothing below would be interpretable.")
        return 1

    caught, missed = 0, []
    for name, anchor, repl, sim in PLANTS:
        n = src.count(anchor)
        if n != 1:
            raise SystemExit(
                f"PLANT ANCHOR NOT UNIQUE: {name!r} matched {n} times. "
                "A plant that does not land where intended produces a "
                "meaningless result; fix the anchor before trusting any arm.")
        mutated = src.replace(anchor, repl, 1)
        if mutated == src:
            raise SystemExit(f"PLANT DID NOT LAND: {name!r}")
        f = tmp / f"{name.split()[0]}.md"
        f.write_text(mutated, encoding="utf-8")
        rc, out = run(f)
        tail = out.splitlines()[0] if out else ""
        status = "CAUGHT" if rc != 0 else "MISSED"
        if rc != 0:
            caught += 1
        else:
            missed.append(name)
        print(f"[{status:>6}] {name}")
        print(f"           simulates: {sim}")
        print(f"           rc={rc}  {tail}")

    print(f"\n{caught}/{len(PLANTS)} planted defects caught.")
    if missed:
        print("MISSED:")
        for m in missed:
            print(f"  {m}")
        print("RED - verify_ladder.py is not commissioned; its green is not "
              "evidence.")
        return 1
    print("GREEN - verify_ladder.py catches every planted defect, including a "
          "deleted row. Its PASS on the real report is now worth something.")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
