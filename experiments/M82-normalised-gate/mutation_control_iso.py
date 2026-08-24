"""Plant, reject, and byte-restore M82's ISO-pair admission mutation."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "bee_iso_admission.py"
OLD = b"admitted = gap <= tolerance  # M82_ISO_CORE_ADMISSION"
PLANTED = b"admitted = gap >= tolerance  # M82_ISO_CORE_ADMISSION"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    log = HERE / "mutation-control-iso.log"
    original = SOURCE.read_bytes()
    records = [f"ORIGINAL_SHA256={digest(original)}"]
    try:
        if original.count(OLD) != 1:
            raise RuntimeError(f"expected one source match, got {original.count(OLD)}")
        SOURCE.write_bytes(original.replace(OLD, PLANTED))
        readback = SOURCE.read_bytes()
        records.extend(
            [
                f"PLANTED_SHA256={digest(readback)}",
                f"PLANTED_READBACK={readback.count(PLANTED) == 1 and OLD not in readback}",
                f"PLANTED_BYTES={PLANTED.decode('ascii')}",
            ]
        )
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
                f"COMMAND={sys.executable} {SOURCE.name} --self-test-only",
                f"EXIT={proc.returncode}",
                f"STDOUT={proc.stdout.rstrip()}",
                f"STDERR={proc.stderr.rstrip()}",
            ]
        )
        if proc.returncode == 0:
            raise RuntimeError("reversed admission comparison did not fail")
    finally:
        SOURCE.write_bytes(original)
        restored = SOURCE.read_bytes()
        records.extend(
            [
                f"RESTORED_SHA256={digest(restored)}",
                f"RESTORED={restored == original}",
            ]
        )
        log.write_text("\n".join(records) + "\n", encoding="utf-8")
    if SOURCE.read_bytes() != original:
        raise RuntimeError("analysis source was not restored byte-for-byte")
    print("ISO mutation control: planted, read back, rejected, and restored")


if __name__ == "__main__":
    main()
