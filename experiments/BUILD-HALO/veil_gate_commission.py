"""Commission the veil's flatness gate by breaking it four ways.

A test that passes on correct code has proved nothing until it has been shown to
fail on incorrect code. Each sabotage below is anchored on a unique full-line
string and the script HARD-ERRORS if the anchor does not land -- a mutation that
silently fails to apply reports GREEN and looks exactly like a passing test.
"""

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MERGE = ROOT / "crates" / "strehl-core" / "src" / "merge.rs"

SABOTAGES = [
    (
        "unmeasured prominence treated as flat",
        """                if !e.is_finite() {
                    return 0.0;
                }""",
        """                if !e.is_finite() {
                    return 1.0;
                }""",
    ),
    (
        "gate inverted: veil the subject, spare the backdrop",
        """                if e <= knee {
                    1.0
                } else if e >= cut {
                    0.0""",
        """                if e <= knee {
                    0.0
                } else if e >= cut {
                    1.0""",
    ),
    (
        "ramp removed: hard switch at the contour",
        "                    (cut - e) / (cut - knee)",
        "                    1.0",
    ),
    (
        "blend weight ignored at the write site",
        "                    self.sum[s][i] = (w * est + (1.0 - w) * current) * divisor;",
        "                    self.sum[s][i] = est * divisor;",
    ),
]


def run_tests() -> tuple[bool, str]:
    p = subprocess.run(
        ["cargo", "test", "--release", "-p", "strehl-core", "--lib"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = p.stdout + p.stderr
    line = next(
        (l.strip() for l in out.splitlines() if l.startswith("test result:")),
        "<no test result line>",
    )
    return p.returncode == 0, line


def main() -> int:
    original = MERGE.read_text(encoding="utf-8")
    backup = MERGE.with_suffix(".rs.commission-bak")
    shutil.copy(MERGE, backup)

    ok, line = run_tests()
    print(f"baseline            : {'GREEN' if ok else 'RED'}   {line}")
    if not ok:
        print("!! baseline is already red; commissioning is meaningless")
        backup.unlink()
        return 2

    caught = 0
    try:
        for name, old, new in SABOTAGES:
            if original.count(old) != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND (or ambiguous): {name!r} "
                    f"matched {original.count(old)} times -- the anchor is wrong "
                    f"and a green result here would be a lie about the instrument"
                )
            MERGE.write_text(original.replace(old, new), encoding="utf-8")
            MERGE.touch()
            ok, line = run_tests()
            verdict = "CAUGHT" if not ok else "MISSED"
            caught += not ok
            print(f"{name:<52}: {verdict}   {line}")
    finally:
        shutil.copy(backup, MERGE)
        MERGE.touch()
        backup.unlink()

    ok, line = run_tests()
    print(f"restored            : {'GREEN' if ok else 'RED'}   {line}")
    print(f"\n{caught}/{len(SABOTAGES)} sabotages caught")
    return 0 if caught == len(SABOTAGES) and ok else 1


if __name__ == "__main__":
    sys.exit(main())
