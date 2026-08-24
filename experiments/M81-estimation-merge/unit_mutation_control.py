"""Prove M81's unit-direction control fails under the registered byte mutation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "analyse_unit.py"
LOG = HERE / "unit-mutation-control.log"
OLD = b"return raw_gate / rho"
PLANTED = b"return raw_gate * rho"


def main() -> None:
    original = SOURCE.read_bytes()
    records = []
    try:
        if original.count(OLD) != 1:
            raise RuntimeError(f"expected one source match, got {original.count(OLD)}")
        SOURCE.write_bytes(original.replace(OLD, PLANTED))
        readback = SOURCE.read_bytes()
        if readback.count(PLANTED) != 1 or OLD in readback:
            raise RuntimeError("planted bytes failed read-back")
        proc = subprocess.run(
            [sys.executable, str(SOURCE), "--self-test-only"],
            cwd=HERE,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        records.extend(
            [
                f"PLANTED_READBACK=PASS bytes={PLANTED.decode('ascii')}",
                f"COMMAND={sys.executable} {SOURCE.name} --self-test-only",
                f"EXIT={proc.returncode}",
                proc.stdout,
                proc.stderr,
            ]
        )
        if proc.stdout.count("UNIT_TEST_COUNT=2") != 1:
            raise RuntimeError("mutated harness did not announce exactly two tests")
        if proc.returncode == 0:
            raise RuntimeError("wrong-direction unit conversion did not fail")
    finally:
        SOURCE.write_bytes(original)
        records.append(f"RESTORED={SOURCE.read_bytes() == original}")
        LOG.write_text("\n".join(records) + "\n", encoding="utf-8")
    if SOURCE.read_bytes() != original:
        raise RuntimeError("analysis source was not restored byte-for-byte")
    print("unit mutation control: planted, read back, rejected, and restored")


if __name__ == "__main__":
    main()
