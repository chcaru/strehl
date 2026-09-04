#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "m138_adjudicate_invoke", args.source.resolve()
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load adjudicator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    verdict = module.adjudicate_result(
        args.result.resolve(),
        args.contract.resolve(),
        verify_sources=False,
        test_mode=True,
    )
    print(json.dumps(verdict, sort_keys=True, allow_nan=False))
    return 2 if verdict.get("verdict") == "INSTRUMENT_INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
