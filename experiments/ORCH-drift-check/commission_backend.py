"""Commission the `backend` field in scripts/check-defaults.py.

WHY THIS EXISTS
---------------
The `backend` field was added to stop the checker reporting estimator-only
stages as dark defaults of the shipping (pyramid) product. That is a correct
fix, but it hands the registry a NEW WAY TO LIE: any genuinely dark switch can
now be excused from the dark check by declaring `backend="estimator"`. A field
that can silence a check must be shown to be load-bearing in BOTH directions
before it is believed --

  * a dark switch that DOES reach the default path must still be caught;
  * a dark switch that does NOT must be reported, counted, and NOT called dark.

An uncommissioned checker and a checker that cannot fail print the same green.

METHOD
------
Two planted arms against the live file, each anchored on a unique full-line
block. The anchor is asserted to occur EXACTLY ONCE and the harness hard-errors
if it does not -- a mutation that silently fails to land produces a green run
that looks exactly like a pass. The file is restored from a $TEMP pin, never
from git, because the working tree holds uncommitted work from other agents.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "scripts" / "check-defaults.py"

ANCHOR = '        kind="quality",\n        default="on (gear-matched)",\n        verified="measured",\n'

ARM_A = '        kind="quality",\n        default="off",\n        verified="measured",\n'

ARM_B = (
    '        kind="quality",\n        default="off",\n'
    '        verified="measured",\n        backend="estimator",\n'
)


def run() -> str:
    p = subprocess.run(
        [sys.executable, str(TARGET)],
        capture_output=True,
        cwd=str(ROOT),
    )
    return p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")


def count(out: str, label: str) -> int:
    m = re.search(rf"^\s*{re.escape(label)}\s+(\d+)", out, re.M)
    if not m:
        raise SystemExit(f"HARNESS BROKEN: no summary line matching {label!r}")
    return int(m.group(1))


def partition_ok(out: str) -> bool:
    a = count(out, "partition sums to")
    b = count(out, "switches found in crates/")
    return a == b


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: anchor occurs {src.count(ANCHOR)} times, "
            "expected exactly 1. Refusing to run -- a mutation that does not land "
            "produces a green that means nothing."
        )

    pin = Path(tempfile.gettempdir()) / "check-defaults.py.pin"
    shutil.copy2(TARGET, pin)
    print(f"pinned to {pin}")

    results: list[tuple[str, bool, str]] = []
    try:
        base = run()
        base_dark = count(base, "quality, dark (DEFECT)")
        base_inap = count(base, "quality, not on default")
        print(f"\nBASELINE   dark={base_dark}  not-on-default={base_inap}  "
              f"partition_ok={partition_ok(base)}")

        # ---- ARM A: a dark switch that DOES reach the default path ---------
        TARGET.write_text(src.replace(ANCHOR, ARM_A), encoding="utf-8")
        a = run()
        a_dark = count(a, "quality, dark (DEFECT)")
        a_has_section = "QUALITY SWITCHES DEFAULTING OFF" in a
        a_names_ca = re.search(r"QUALITY SWITCHES DEFAULTING OFF.*?STREHL_FIX_CA", a, re.S) is not None
        ok_a = a_dark == base_dark + 1 and a_has_section and a_names_ca and partition_ok(a)
        results.append((
            "A  dark + backend=any  -> MUST be caught as dark",
            ok_a,
            f"dark {base_dark}->{a_dark}, section={a_has_section}, names_CA={a_names_ca}",
        ))

        # ---- ARM B: the same dark switch, declared estimator-only ----------
        TARGET.write_text(src.replace(ANCHOR, ARM_B), encoding="utf-8")
        b = run()
        b_dark = count(b, "quality, dark (DEFECT)")
        b_inap = count(b, "quality, not on default")
        b_names_ca = (
            re.search(r"NOT ON THE DEFAULT BACKEND.*?STREHL_FIX_CA", b, re.S) is not None
        )
        ok_b = (
            b_dark == base_dark
            and b_inap == base_inap + 1
            and b_names_ca
            and partition_ok(b)
        )
        results.append((
            "B  dark + backend=estimator -> reported, counted, NOT dark",
            ok_b,
            f"dark {base_dark}->{b_dark}, not-on-default {base_inap}->{b_inap}, "
            f"named={b_names_ca}",
        ))
    finally:
        shutil.copy2(pin, TARGET)
        os.utime(TARGET, None)
        restored = TARGET.read_text(encoding="utf-8")
        print(f"\nrestored from pin: identical={restored == src}")
        if restored != src:
            raise SystemExit("RESTORE FAILED -- the working file is NOT as found.")

    print("\n" + "=" * 70)
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}\n          {detail}")
    caught = sum(1 for _, ok, _ in results if ok)
    print("=" * 70)
    print(f"  {caught}/{len(results)} planted conditions behaved as required")
    return 0 if caught == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
