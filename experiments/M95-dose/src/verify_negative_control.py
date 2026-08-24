"""Negative control for arm 8's verify_report.py.

A verifier only ever seen passing is not evidence. This plants three known
defects, requires RED each time, restores from byte copies in TEMP, and requires
GREEN again.

Every mutation is anchored on an exact full-line string and a miss is a hard
error, not a pass -- arm 5's F5 reported green for the wrong reason because its
anchor was spelled with ASCII where the report uses U+2212.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
REPORT = ROOT / "docs" / "research" / "M95-dose.md"
Y1 = HERE.parents[1] / "out" / "y1_dose.json"
VERIFY = HERE.parent / "verify_report.py"


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       text=True, env=env, cwd=str(HERE.parent))
    return p.returncode


def mutate(path, old, new):
    txt = path.read_text(encoding="utf-8")
    n = txt.count(old)
    if n != 1:
        raise SystemExit(
            f"ANCHOR DID NOT LAND: {old!r} occurs {n} times in {path.name}. "
            "A mutation that does not land makes this control green for the "
            "wrong reason.")
    path.write_text(txt.replace(old, new, 1), encoding="utf-8")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="m95dose-"))
    bak_r, bak_y = tmp / "report.md", tmp / "y1.json"
    shutil.copy2(REPORT, bak_r)
    shutil.copy2(Y1, bak_y)
    print(f"backups in {tmp}")

    failures = []
    try:
        rc = run()
        print(f"\n[1] baseline, unmodified            rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("baseline was not green")

        # defect A -- a wrong number in a report table row
        mutate(REPORT, "| 0.9800 | +0.1805 | +0.1815 |",
                       "| 0.9800 | +0.1905 | +0.1815 |")
        rc = run()
        print(f"[2] report sweep row altered        rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc == 0:
            failures.append("verifier stayed green with a wrong report number")
        shutil.copy2(bak_r, REPORT)

        # defect B -- a wrong number in the source JSON the report is checked against
        txt = Y1.read_text(encoding="utf-8")
        needle = '"1.02": {'
        if txt.count(needle) != 2:  # once under ISO, once under COMP
            raise SystemExit(
                f"ANCHOR DID NOT LAND: {needle!r} occurs {txt.count(needle)} "
                "times, expected 2")
        i = txt.index(needle)
        j = txt.index('"mean":', i)
        k = txt.index(",", j)
        Y1.write_text(txt[:j] + '"mean": -9.9999' + txt[k:], encoding="utf-8")
        rc = run()
        print(f"[3] source json ISO(1.02) altered   rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc == 0:
            failures.append("verifier stayed green with a wrong source value")
        shutil.copy2(bak_y, Y1)

        # defect C -- strip a fact status label
        txt = REPORT.read_text(encoding="utf-8")
        if txt.count("`MEASURED`") < 1:
            raise SystemExit("ANCHOR DID NOT LAND: no MEASURED label")
        REPORT.write_text(txt.replace("`MEASURED`", "", 1), encoding="utf-8")
        rc = run()
        print(f"[4] one fact label removed          rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc == 0:
            failures.append("verifier stayed green with an unlabelled fact")
        shutil.copy2(bak_r, REPORT)

        rc = run()
        print(f"[5] restored                        rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("restore did not return to green")
    finally:
        shutil.copy2(bak_r, REPORT)
        shutil.copy2(bak_y, Y1)

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
