from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import common
import controls


ARM = "focus-stack-depthmap-chain-off"
CONTROL = common.ROOT / "controls-depthmap-off"
NOISE_PRESET = Path(r"C:\dev\macro\presets\noise_profile.json")
EXPECTED_NOISE_PRESET_SHA256 = (
    "860A57DB745776E0C50E3FC190320142FDE2D79AF0F85848A659719C7D2AAC1E"
)
BASELINE_OPTIONS = [
    "--no-align",
    "--no-transform",
    "--no-whitebalance",
    "--no-contrast",
    "--nocrop",
    "--input-colorspace=linear-rec2020",
    "--internal-colorspace=linear",
    "--output-colorspace=linear-rec2020",
    "--output-bitdepth=16",
    "--hdr-preserve=off",
    "--threads=6",
]


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def require_full_gate(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    age = dt.datetime.now(dt.timezone.utc) - parse_time(payload["measured_at"])
    if payload.get("class") != "full":
        raise RuntimeError(
            f"host gate class {payload.get('class')!r}, expected 'full'"
        )
    if payload.get("pass") is not True:
        raise RuntimeError("host-load gate did not pass")
    if age.total_seconds() < 0 or age.total_seconds() > 600:
        raise RuntimeError(f"host-load gate is stale: {age.total_seconds():.1f}s")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-gate", type=Path, required=True)
    args = parser.parse_args()

    gate = require_full_gate(args.host_gate)
    if common.COMPARATOR_OPTIONS != BASELINE_OPTIONS:
        raise RuntimeError("baseline comparator invocation changed")
    if common.sha256(NOISE_PRESET) != EXPECTED_NOISE_PRESET_SHA256:
        raise RuntimeError("auto noise-model preset changed")

    common.COMPARATOR_OPTIONS = [
        *BASELINE_OPTIONS,
        "--depthmap-chain=off",
    ]
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
                "only_invocation_delta": "--depthmap-chain=off",
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
                "only_invocation_delta": "--depthmap-chain=off",
            },
        )
        raise


if __name__ == "__main__":
    main()
