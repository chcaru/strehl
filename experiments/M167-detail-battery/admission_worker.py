"""Evaluator-owned single-packet worker for M167 admission."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


def load_candidate(path: Path):
    spec = importlib.util.spec_from_file_location("m167_candidate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("worker requires exactly one constant candidate path")
    candidate = load_candidate(Path(sys.argv[1]))
    image = np.load(sys.stdin.buffer, allow_pickle=False)
    record = candidate.score(image)
    if not isinstance(record, dict):
        raise TypeError("candidate result is not an object")
    sys.stdout.write(
        json.dumps(record, sort_keys=True, allow_nan=False) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
