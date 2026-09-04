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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    root = args.destination.resolve()
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(source, root)
    pilot = load(root / "pilot.json")
    mappings = (
        ("pilot-development", "noise-pass-development.json", "noise-development"),
        ("pilot-holdout", "noise-pass-holdout.json", "noise-holdout"),
    )
    reused = []
    for pilot_id, noise_name, capture_id in mappings:
        noise = load(root / noise_name)
        scored = noise["captures"][capture_id]
        refs = scored["candidate_outputs"] + scored["legacy_outputs"]
        pilot["captures"][pilot_id]["source_outputs"] = refs
        pilot["captures"][pilot_id]["source_capture_ids"] = [
            scored["source_capture_ids"][0],
            scored["source_capture_ids"][1],
            scored["source_capture_ids"][0] + "-second-render",
            scored["source_capture_ids"][1] + "-second-render",
        ]
        reused.extend(ref["path"] for ref in refs)
    write(root / "pilot-reuses-scored.json", pilot)
    contract = load(root / "effect-bound-contract.json")
    contract["noise_instrument"]["pilot_evidence"] = {
        "path": "pilot-reuses-scored.json",
        "sha256": sha(root / "pilot-reuses-scored.json"),
    }
    write(root / "effect-bound-reused-pilot-contract.json", contract)
    result = load(root / "result.json")
    result["contract_sha256"] = sha(root / "effect-bound-reused-pilot-contract.json")
    write(root / "reused-pilot-result.json", result)
    print(
        json.dumps(
            {"reused_scored_output_paths": reused, "unique_paths": len(set(reused))},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
