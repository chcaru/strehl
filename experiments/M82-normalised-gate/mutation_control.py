"""Plant, read back, reject and byte-restore M82's core admission mutation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "m82lib.py"
LOG = HERE / "mutation-control.log"
OLD = b"admitted = gap <= tolerance  # M82_CORE_ADMISSION"
PLANTED = b"admitted = gap >= tolerance  # M82_CORE_ADMISSION"


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
        if proc.stdout.count("M82_SELF_TEST_COUNT=4") != 1:
            raise RuntimeError("mutated harness did not announce exactly four tests")
        if proc.returncode == 0:
            raise RuntimeError("reversed admission comparison did not fail")
    finally:
        SOURCE.write_bytes(original)
        records.append(f"RESTORED={SOURCE.read_bytes() == original}")
        LOG.write_text("\n".join(records) + "\n", encoding="utf-8")
    if SOURCE.read_bytes() != original:
        raise RuntimeError("analysis source was not restored byte-for-byte")
    print("mutation control: planted, read back, rejected, and restored")


if __name__ == "__main__":
    main()
