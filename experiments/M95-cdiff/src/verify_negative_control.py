"""Negative control for verify_report.py.

A verifier that has only ever been seen passing is not evidence. This plants a
known defect on each side of the comparison, requires the verifier to go RED,
restores, and requires GREEN again.

Two disciplines from earlier arms are enforced here:

- **Anchors are exact full-line strings and a miss is a hard error.** Arm 5's F5
  was a mutation that silently landed 0 times because the anchor was spelled with
  ASCII 'x' where the report uses U+00D7. A mutation that does not land makes the
  control report GREEN for the wrong reason.
- **Restore from a byte copy in TEMP, never from git.** Reverting to HEAD would
  discard uncommitted work in a tree with other agents live in it.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
REPORT = ROOT / "docs" / "research" / "M95-cdiff.md"
LADDER = HERE.parents[1] / "out" / "c1_ladder.json"
VERIFY = HERE.parent / "verify_report.py"


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       text=True, env=env, cwd=str(HERE.parent))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def mutate(path, old, new):
    """Replace `old` with `new` exactly once, or fail loudly."""
    txt = path.read_text(encoding="utf-8")
    n = txt.count(old)
    if n != 1:
        raise SystemExit(
            f"ANCHOR DID NOT LAND: {old!r} occurs {n} times in {path.name}. "
            "A mutation that does not land makes this control green for the "
            "wrong reason -- see arm 5 F5.")
    path.write_text(txt.replace(old, new, 1), encoding="utf-8")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="m95cdiff-"))
    bak_r, bak_l = tmp / "report.md", tmp / "ladder.json"
    shutil.copy2(REPORT, bak_r)
    shutil.copy2(LADDER, bak_l)
    print(f"backups in {tmp}")

    failures = []
    try:
        rc, _ = run()
        print(f"\n[1] baseline, unmodified            rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("baseline was not green")

        # -- defect A: change a number in the REPORT only.
        # Anchored on a full table row, glyph-free apart from the minus sign
        # that the report actually uses.
        old = "| CDIFF | Y | +0.0110 | \u22120.1462 | \u22120.5064 | 0.3038 |"
        mutate(REPORT, old,
               "| CDIFF | Y | +0.0110 | \u22120.1999 | \u22120.5064 | 0.3038 |")
        rc, out = run()
        print(f"[2] report number altered           rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc == 0:
            failures.append("verifier stayed green with a wrong report number")
        shutil.copy2(bak_r, REPORT)

        # -- defect B: change the SOURCE json the report is checked against.
        old = '"signal": -0.14622'
        txt = LADDER.read_text(encoding="utf-8")
        m = re.search(r'"signal": -0\.14\d+', txt)
        if not m:
            raise SystemExit("ANCHOR DID NOT LAND: no CDIFF luma signal in json")
        LADDER.write_text(txt.replace(m.group(0), '"signal": -0.19999', 1),
                          encoding="utf-8")
        rc, out = run()
        print(f"[3] source json altered             rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc == 0:
            failures.append("verifier stayed green with a wrong source value")
        shutil.copy2(bak_l, LADDER)

        # -- defect C: remove a fact label, so facts != labels.
        txt = REPORT.read_text(encoding="utf-8")
        if txt.count("`MEASURED`") < 1:
            raise SystemExit("ANCHOR DID NOT LAND: no MEASURED label")
        REPORT.write_text(txt.replace("`MEASURED`", "", 1), encoding="utf-8")
        rc, out = run()
        print(f"[4] one fact label removed          rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc == 0:
            failures.append("verifier stayed green with an unlabelled fact")
        shutil.copy2(bak_r, REPORT)

        rc, _ = run()
        print(f"[5] restored                        rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("restore did not return to green")
    finally:
        shutil.copy2(bak_r, REPORT)
        shutil.copy2(bak_l, LADDER)

    print()
    if failures:
        for f in failures:
            print(f"  FAILURE: {f}")
        print("NEGATIVE CONTROL FAILED")
        return 1
    print("NEGATIVE CONTROL PASSED  green -> red, red, red -> green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
