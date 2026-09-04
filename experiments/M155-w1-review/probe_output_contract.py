#!/usr/bin/env python3
import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("fixture", type=Path)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location(
        "m138_output_probe", a.source.resolve()
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    root = a.fixture.resolve()
    contract = module.load_json(root / "contract.json")
    verdict = module.adjudicate_result(
        root / "result.json",
        root / "contract.json",
        verify_sources=False,
        test_mode=True,
    )
    ledgers = contract["capture_ledgers"]
    cases = {}
    missing_phase = copy.deepcopy(verdict)
    del missing_phase["achieved_effect"]["holdout"]
    cases["missing_holdout_effect"] = missing_phase
    m2_true = copy.deepcopy(verdict)
    m2_true["achieved_effect"]["development"]["scorecard_m2"]["licensed"] = True
    cases["m2_license_true"] = m2_true
    incomplete = copy.deepcopy(verdict)
    del incomplete["achieved_effect"]["holdout"]["by_capture_and_plane"][
        "noise-holdout"
    ]["R"]["simultaneous_confidence_upper"]
    cases["incomplete_r_cell"] = incomplete
    output = {}
    for name, value in cases.items():
        try:
            module.validate_go_output(value, ledgers, contract)
        except module.EvidenceError as error:
            output[name] = {"accepted": False, "reason": str(error)}
        else:
            output[name] = {"accepted": True}
    print(json.dumps(output, sort_keys=True))
    return 0 if all(not row["accepted"] for row in output.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
