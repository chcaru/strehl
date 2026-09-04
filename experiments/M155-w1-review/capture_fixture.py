#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path


class FixtureCaptured(RuntimeError):
    pass


def load_module(source: Path):
    spec = importlib.util.spec_from_file_location("m138_adjudicate_capture", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load adjudicator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    module = load_module(args.source.resolve())
    destination = args.destination.resolve()
    if destination.exists():
        shutil.rmtree(destination)
    original = module.adjudicate_result
    captured = False

    def capture(result_path, contract_path=module.CONTRACT_PATH, **kwargs):
        nonlocal captured
        if captured:
            raise RuntimeError("capture called twice")
        captured = True
        shutil.copytree(Path(result_path).parent, destination)
        raise FixtureCaptured()

    module.adjudicate_result = capture
    try:
        module.run_self_test(module.load_json(args.contract.resolve()))
    except FixtureCaptured:
        pass
    finally:
        module.adjudicate_result = original
    if not captured:
        raise RuntimeError("self-test never reached adjudication")
    verdict = original(
        destination / "result.json",
        destination / "contract.json",
        verify_sources=False,
        test_mode=True,
    )
    print(json.dumps({"captured": captured, "baseline": verdict}, sort_keys=True))
    return 0 if verdict.get("verdict") == "PHASE1_GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
