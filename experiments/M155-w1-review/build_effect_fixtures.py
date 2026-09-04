#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reset(source: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


def update_development_result(root: Path, development: dict[str, Any]) -> None:
    write(root / "development.json", development)
    result = load(root / "result.json")
    result["development"]["sha256"] = sha(root / "development.json")
    write(root / "result.json", result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)

    root = reset(source, destination / "missing-noise")
    development = load(root / "development.json")
    del development["arms"]["0.50"]["noise_evidence"]
    update_development_result(root, development)

    root = reset(source, destination / "supplied-effect")
    development = load(root / "development.json")
    development["arms"]["0.50"]["achieved_effect"] = {"estimated_power_ratio": 0.01}
    update_development_result(root, development)

    root = reset(source, destination / "incomplete-effect")
    noise_path = root / "noise-pass-development.json"
    noise = load(noise_path)
    capture = noise["captures"]["noise-development"]
    output_ref = capture["candidate_outputs"][0]
    output_path = root / output_ref["path"]
    output = load(output_path)
    del output["planes"]["R"]
    write(output_path, output)
    output_ref["sha256"] = sha(output_path)
    write(noise_path, noise)
    development = load(root / "development.json")
    new_noise_hash = sha(noise_path)
    for arm in development["arms"].values():
        arm["noise_evidence"]["sha256"] = new_noise_hash
    update_development_result(root, development)

    root = reset(source, destination / "missing-holdout")
    result = load(root / "result.json")
    result["holdout"] = None
    write(root / "result.json", result)

    root = reset(source, destination / "supplied-result-effect")
    result = load(root / "result.json")
    result["achieved_effect"] = {"development": {}}
    write(root / "result.json", result)

    root = reset(source, destination / "supplied-unlisted-effect")
    development = load(root / "development.json")
    development["simultaneous_confidence_lower"] = 0.0
    development["simultaneous_confidence_upper"] = 0.0
    development["minimum_guaranteed_rms_reduction"] = 1.0
    update_development_result(root, development)

    root = reset(source, destination / "supplied-m2-claim")
    development = load(root / "development.json")
    development["scorecard_m2"] = {
        "licensed": True,
        "reference": "SHIPPING_COMPARATOR",
        "reason": "producer claims M2",
    }
    update_development_result(root, development)

    root = reset(source, destination / "unbound-zero")
    contract = load(root / "contract.json")
    contract["noise_instrument"]["required_rms_reduction"] = 0.0
    write(root / "contract-unbound-zero.json", contract)
    result = load(root / "result.json")
    result["contract_sha256"] = sha(root / "contract-unbound-zero.json")
    write(root / "result-unbound-zero.json", result)

    print(
        json.dumps(
            {
                "cases": sorted(
                    path.name for path in destination.iterdir() if path.is_dir()
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
