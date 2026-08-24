"""Prove M84's metric self-test rejects a declared pitch 10% too large."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

OLD = b'"declared_pitch_mm": 1.0'
PLANTED = b'"declared_pitch_mm": 1.1'


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("selftest", type=Path)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()

    original = args.fixture.read_bytes()
    original_hash = digest(original)
    records = [f"ORIGINAL_SHA256={original_hash}"]
    caught: BaseException | None = None
    try:
        match_count = original.count(OLD)
        records.append(f"ORIGINAL_MATCH_COUNT={match_count}")
        if match_count != 1:
            raise RuntimeError(
                f"expected exactly one declared-pitch byte string, got {match_count}"
            )
        planted = original.replace(OLD, PLANTED)
        args.fixture.write_bytes(planted)
        readback = args.fixture.read_bytes()
        if readback != planted or readback.count(PLANTED) != 1:
            raise RuntimeError("10% wrong-pitch plant failed byte read-back")
        records.append("PLANTED_READBACK=PASS declared_pitch_mm=1.1")
        process = subprocess.run(
            [sys.executable, str(args.selftest), str(args.fixture)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        records.extend(
            [
                f"COMMAND={sys.executable} {args.selftest} {args.fixture}",
                f"EXIT={process.returncode}",
                "STDOUT_BEGIN",
                process.stdout,
                "STDOUT_END",
                "STDERR_BEGIN",
                process.stderr,
                "STDERR_END",
            ]
        )
        if process.returncode == 0:
            raise RuntimeError("10% wrong-pitch plant was not rejected")
        combined = process.stdout + process.stderr
        if "PITCH_SCALE_ERROR" not in combined:
            raise RuntimeError("failure did not name the pitch / scale error")
    except BaseException as error:
        caught = error
    finally:
        args.fixture.write_bytes(original)
        restored = args.fixture.read_bytes()
        records.extend(
            [
                f"RESTORED_SHA256={digest(restored)}",
                f"RESTORED_BYTE_FOR_BYTE={restored == original}",
            ]
        )
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text("\n".join(records) + "\n", encoding="utf-8")

    if args.fixture.read_bytes() != original:
        raise RuntimeError("fixture was not restored byte-for-byte")
    if digest(args.fixture.read_bytes()) != original_hash:
        raise RuntimeError("restored fixture hash differs from original")
    if caught is not None:
        raise caught
    print(
        "PITCH_MUTATION_CONTROL_PASS planted=+10% readback=pass "
        "rejected=pass restored=pass",
        flush=True,
    )


if __name__ == "__main__":
    main()
