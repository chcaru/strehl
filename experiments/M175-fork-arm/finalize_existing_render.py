#!/usr/bin/env python3
"""Finalize the M175 result after a post-render JSON serialization-only failure."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any


SCHEMA = "m175-fork-tone-sentinel-result-v1"


class FinalizeFailure(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": sha256(data),
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalizeFailure(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FinalizeFailure(f"{label} is not a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(partial, path)


def load_measurement_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("m175_render_measurement", path)
    if spec is None or spec.loader is None:
        raise FinalizeFailure(f"cannot import measurement code {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finalize(root: Path) -> dict[str, Any]:
    result_path = root / "render-result.json"
    if result_path.exists():
        raise FinalizeFailure(f"refusing to overwrite {result_path}")
    start_path = root / "render-start.json"
    output = root / "work" / "tone-sentinel" / "output" / "tone-sentinel.tiff"
    if not start_path.is_file() or not output.is_file():
        raise FinalizeFailure("the original render start or output artifact is absent")

    pre_freeze_path = root / "PRE-RENDER-FREEZE.json"
    build_freeze_path = root / "build-freeze.json"
    input_manifest_path = root / "INPUT-MANIFEST.json"
    site_manifest_path = root / "SITE-MANIFEST.json"
    run_manifest_path = root / "RUN-MANIFEST.json"
    settings_path = root / "SETTINGS-MANIFEST.json"
    truth_path = root / "TONE-TRUTH.json"
    start = load_json(start_path, "render start")
    pre_freeze = load_json(pre_freeze_path, "pre-render freeze")
    build_freeze = load_json(build_freeze_path, "build freeze")
    input_manifest = load_json(input_manifest_path, "input manifest")
    site_manifest = load_json(site_manifest_path, "site manifest")
    run_manifest = load_json(run_manifest_path, "run manifest")
    settings = load_json(settings_path, "settings manifest")
    truth = load_json(truth_path, "tone truth")

    if start.get("invocation") != run_manifest.get("invocation"):
        raise FinalizeFailure("persisted render invocation differs from frozen run")
    if not start.get("output_absent_before_launch"):
        raise FinalizeFailure("render start does not prove output absence")
    if start.get("executable", {}).get("sha256") != pre_freeze.get(
        "executable_sha256"
    ):
        raise FinalizeFailure("render start executable differs from pre-render freeze")
    if start.get("input_file_sha256") != pre_freeze.get("input_file_sha256"):
        raise FinalizeFailure("render start input differs from pre-render freeze")

    executable = Path(run_manifest["executable"]["path"])
    if file_record(executable)["sha256"] != pre_freeze["executable_sha256"]:
        raise FinalizeFailure("current executable differs from pre-render freeze")
    inputs = [Path(item["path"]) for item in input_manifest["inputs"]]
    if len(inputs) != 8:
        raise FinalizeFailure("input manifest does not contain eight occurrences")
    for expected, path in zip(input_manifest["inputs"], inputs):
        if file_record(path)["sha256"] != expected["sha256"]:
            raise FinalizeFailure(f"input changed after rendering: {path}")

    measurement_path = root / "render_tone_sentinel.py"
    measurement = load_measurement_module(measurement_path)
    array, output_metadata = measurement.inspect_output(output)
    transfer = measurement.score_transfer(array, truth, site_manifest)
    tiff_contract = {
        "native_dimensions": output_metadata["shape"] == [4688, 7028, 3],
        "bits_per_sample_16_rgb": output_metadata["bits_per_sample"] == [16, 16, 16],
        "dtype_uint16": output_metadata["dtype"] == "uint16",
    }
    start_utc = datetime.fromisoformat(start["render_started_utc"])
    freeze_utc = datetime.fromisoformat(pre_freeze["frozen_utc"])
    output_created_utc = datetime.fromtimestamp(
        output.stat().st_ctime, timezone.utc
    )
    ordering = {
        "pre_render_guard_commit": start["pre_render_guard_commit"],
        "pre_render_commits": start["pre_render_commits"],
        "pre_render_freeze": start["pre_render_freeze"],
        "pre_render_freeze_utc": freeze_utc.isoformat(),
        "render_started_utc": start_utc.isoformat(),
        "output_created_utc": output_created_utc.isoformat(),
        "freeze_precedes_render": freeze_utc < start_utc,
        "render_start_precedes_output_creation": start_utc <= output_created_utc,
        "render_start_artifact": file_record(start_path),
    }
    passed = (
        transfer["pass"]
        and all(tiff_contract.values())
        and ordering["freeze_precedes_render"]
        and ordering["render_start_precedes_output_creation"]
    )
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "BLOCKED",
        "fork_arm_verdict": (
            "REBUILT_AND_SECTION_1_3_PASS"
            if passed
            else "BLOCKED_SECTION_1_3_OR_FREEZE_ORDER"
        ),
        "quality_score": False,
        "holdout_used": False,
        "selected_commit": build_freeze["source"]["commit_sha1"],
        "source_tree_sha1": build_freeze["source"]["tree_sha1"],
        "source_manifest_sha256": build_freeze["source"]["manifest_sha256"],
        "executable": file_record(executable),
        "reproducibility": build_freeze["reproducibility"],
        "runtime_bundle_sha256": build_freeze["dependencies"][
            "runtime_bundle_sha256"
        ],
        "settings": settings,
        "input": {
            "count": 8,
            "all_byte_identical": len(
                {item["sha256"] for item in input_manifest["inputs"]}
            )
            == 1,
            "file_sha256": input_manifest["inputs"][0]["sha256"],
            "pixel_payload_sha256": input_manifest["inputs"][0][
                "pixel_payload_sha256"
            ],
            "manifest": file_record(input_manifest_path),
        },
        "invocation": run_manifest["invocation"],
        "renderer_exit_code": 0,
        "renderer_exit_code_basis": (
            "The original renderer wrapper reached output inspection and result "
            "serialization; its nonzero-exit branch returns before both."
        ),
        "output": output_metadata,
        "output_tiff_contract": tiff_contract,
        "section_1_3": transfer,
        "freeze_order": ordering,
        "measurement_recovery": {
            "no_rerender": True,
            "original_output_reused": True,
            "original_failure": (
                "JSON serialization rejected numpy.bool_ values after rendering "
                "and measurement; the measurement booleans were converted to "
                "built-in bool and this finalizer read the existing TIFF."
            ),
            "measurement_script": file_record(measurement_path),
            "finalizer": file_record(Path(__file__).resolve()),
        },
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    out = root / "render-result.json"
    if out.exists():
        print(f"refusing to overwrite {out}", file=sys.stderr)
        return 1
    try:
        result = finalize(root)
    except BaseException as exc:
        result = {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "failure_class": type(exc).__name__,
            "reason": str(exc),
        }
    write_json(out, result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
