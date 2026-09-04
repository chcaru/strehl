from __future__ import annotations

import argparse
import json
from pathlib import Path

import common
import controls
from controls_depthmap_off import (
    BASELINE_OPTIONS,
    EXPECTED_NOISE_PRESET_SHA256,
    NOISE_PRESET,
    require_full_gate,
)


ARM = "focus-stack-identity-crop-depthmap-chain-off"
CONTROL = common.ROOT / "controls-identity-crop-depthmap-off"
OPTIONS = [
    option for option in BASELINE_OPTIONS if option != "--nocrop"
] + ["--depthmap-chain=off"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-gate", type=Path, required=True)
    args = parser.parse_args()

    gate = require_full_gate(args.host_gate)
    if common.COMPARATOR_OPTIONS != BASELINE_OPTIONS:
        raise RuntimeError("baseline comparator invocation changed")
    if common.sha256(NOISE_PRESET) != EXPECTED_NOISE_PRESET_SHA256:
        raise RuntimeError("auto noise-model preset changed")

    common.COMPARATOR_OPTIONS = OPTIONS
    controls.CONTROL = CONTROL

    try:
        controls.main()
        result_path = CONTROL / "PASS.json"
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload.update(
            {
                "arm": ARM,
                "host_gate": gate,
                "noise_preset": {
                    "path": str(NOISE_PRESET),
                    "sha256": EXPECTED_NOISE_PRESET_SHA256,
                },
                "invocation_deltas": [
                    "omit --nocrop",
                    "append --depthmap-chain=off",
                ],
            }
        )
        common.atomic_json(result_path, payload)
    except Exception as error:
        CONTROL.mkdir(parents=True, exist_ok=True)
        common.atomic_json(
            CONTROL / "FAIL.json",
            {
                "status": "FAIL",
                "arm": ARM,
                "error": f"{type(error).__name__}: {error}",
                "host_gate": gate,
                "noise_preset": {
                    "path": str(NOISE_PRESET),
                    "sha256": EXPECTED_NOISE_PRESET_SHA256,
                },
                "invocation_deltas": [
                    "omit --nocrop",
                    "append --depthmap-chain=off",
                ],
            },
        )
        raise


if __name__ == "__main__":
    main()
