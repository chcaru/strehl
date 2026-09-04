#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("fixture", type=Path)
    p.add_argument("scratch", type=Path)
    a = p.parse_args()
    root = a.scratch.resolve()
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(a.fixture.resolve(), root)
    spec = importlib.util.spec_from_file_location("m138_at64_probe", a.source.resolve())
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    contract = m.load_json(root / "effect-bound-contract.json")
    sites = ["s{:03d}".format(i) for i in range(256)]
    contract["noise_instrument"]["selected_sites_per_capture"] = 256
    for phase in ("development", "holdout"):
        capture = next(iter(contract["capture_ledgers"][phase]["noise"]))
        contract["capture_ledgers"][phase]["noise"][capture] = sites
    pilot = m.make_pilot_evidence(
        contract,
        root,
        {"pilot-development": "noise-development", "pilot-holdout": "noise-holdout"},
        sites,
        anticorrelated=True,
    )
    low = 0.2
    pair_a = np.asarray([low if i % 2 == 0 else 2.0 - low for i in range(256)])
    pair_b = np.asarray([2.0 - low if i % 2 == 0 else low for i in range(256)])
    values = (
        np.zeros(256),
        np.sqrt(2.0 * pair_a),
        np.zeros(256),
        np.sqrt(2.0 * pair_b),
    )
    for capture in pilot["captures"].values():
        for ref, row in zip(capture["source_outputs"], values):
            path = root / ref["path"]
            output = m.load_json(path)
            output["site_ids"] = sites
            output["planes"] = {
                plane: row.tolist()
                for plane in contract["noise_instrument"]["required_cfa_planes"]
            }
            m.write_json(path, output)
            ref["sha256"] = sha(path)
    m.write_json(root / "pilot-at64-fails.json", pilot)
    contract["noise_instrument"]["pilot_evidence"] = {
        "path": "pilot-at64-fails.json",
        "sha256": sha(root / "pilot-at64-fails.json"),
    }
    m.write_json(root / "contract-at64-fails.json", contract)
    m.validate_contract(contract, test_mode=True)
    bindings = m.validate_frozen_bindings(contract, root / "contract-at64-fails.json")
    power = bindings["noise_binding"]
    output = {
        "binding_accepted": True,
        "target": contract["noise_instrument"]["power_target"],
        "at_64": {
            phase: power["power_at_64_sites"][phase]["lower_confidence_power"]
            for phase in ("development", "holdout")
        },
        "at_256": {
            phase: power["power_at_selected_sites"][phase]["lower_confidence_power"]
            for phase in ("development", "holdout")
        },
    }
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
