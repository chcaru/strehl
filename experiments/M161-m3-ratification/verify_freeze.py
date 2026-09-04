"""Verify the pre-output M161 M3 freeze without opening image pixels."""

from __future__ import annotations

import json
from pathlib import Path

from m3_checker_v2 import sha256_file


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "freeze-manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    for relative, expected in manifest["files"].items():
        path = HERE / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
        else:
            actual = sha256_file(path)
            if actual != expected:
                failures.append(f"hash {relative}: {actual} != {expected}")
    for relative, expected in manifest["upstream"].items():
        path = (HERE / relative).resolve()
        if not path.is_file():
            failures.append(f"missing upstream {relative}")
        else:
            actual = sha256_file(path)
            if actual != expected:
                failures.append(f"upstream hash {relative}: {actual} != {expected}")
    if failures:
        print("FAIL")
        for failure in failures:
            print(failure)
        return 3
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
