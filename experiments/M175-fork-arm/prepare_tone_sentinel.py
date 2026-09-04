#!/usr/bin/env python3
"""Freeze M175's common-input tone sentinel and fork settings before rendering."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from typing import Any

import numpy as np
import tifffile


SCHEMA = "m175-fork-pre-render-freeze-v1"
COMMIT = "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"
FORBIDDEN_INSTRUCTIONS = (
    b"Contrast2012",
    b"Sharpness",
    b"Clarity",
    b"Texture",
    b"LuminanceSmoothing",
    b"ToneCurve",
)
SETTINGS = {
    "threads": 1,
    "batchsize": 2,
    "no_opencl": True,
    "no_align": True,
    "no_whitebalance": True,
    "no_contrast": True,
    "consistency": 0,
    "denoise": 0,
    "input_colorspace": "none",
    "output_colorspace": "srgb",
    "output_bitdepth": 16,
}


class PreparationFailure(RuntimeError):
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


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(partial, path)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreparationFailure(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreparationFailure(f"{label} is not a JSON object")
    return value


def load_converter(repo_root: Path) -> tuple[Any, Path]:
    path = repo_root / "experiments" / "M165-common-input" / "converter.py"
    spec = importlib.util.spec_from_file_location("m175_common_tiff_writer", path)
    if spec is None or spec.loader is None:
        raise PreparationFailure(f"cannot import common TIFF writer {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def build_invocation(executable: Path, output: Path, inputs: list[Path]) -> list[str]:
    return [
        str(executable.resolve()),
        f"--output={output.resolve()}",
        "--threads=1",
        "--batchsize=2",
        "--no-opencl",
        "--no-align",
        "--no-whitebalance",
        "--no-contrast",
        "--consistency=0",
        "--denoise=0",
        "--input-colorspace=none",
        "--output-colorspace=srgb",
        "--output-bitdepth=16",
        *[str(path.resolve()) for path in inputs],
    ]


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(__file__).resolve().parent
    repo_root = root.parents[1]
    build_freeze_path = Path(args.build_freeze).resolve()
    source_pin_path = Path(args.source_pin).resolve()
    revision_path = Path(args.revision_selection).resolve()
    executable = Path(args.executable).resolve()
    work = Path(args.work).resolve()
    output = work / "output" / "tone-sentinel.tiff"
    render_result = root / "render-result.json"
    if render_result.exists() or output.exists():
        raise PreparationFailure(
            "refusing to replace a rendered result or its output after settings selection"
        )

    build_freeze = load_json(build_freeze_path, "build freeze")
    source_pin = load_json(source_pin_path, "source pin")
    revision = load_json(revision_path, "revision selection")
    if build_freeze.get("status") != "FROZEN":
        raise PreparationFailure("build freeze status is not FROZEN")
    if source_pin.get("status") != "FROZEN":
        raise PreparationFailure("source pin status is not FROZEN")
    if revision.get("status") != "PASS":
        raise PreparationFailure("revision selection status is not PASS")
    if build_freeze.get("source", {}).get("commit_sha1") != COMMIT:
        raise PreparationFailure("build freeze does not bind the selected commit")
    executable_record = file_record(executable)
    expected_executable_sha = build_freeze.get("frozen_executable", {}).get("sha256")
    if executable_record["sha256"] != expected_executable_sha:
        raise PreparationFailure(
            f"executable is {executable_record['sha256']}, expected {expected_executable_sha}"
        )

    converter, converter_path = load_converter(repo_root)
    converter_record = file_record(converter_path)
    icc = converter.build_linear_prophoto_icc()
    icc_inspection = converter.inspect_linear_prophoto_icc(icc)
    if any(value != 1.0 for value in icc_inspection["trc_gamma"].values()):
        raise PreparationFailure("generated ProPhoto ICC is not linear")

    step_count = 33
    step_width = 64
    height = 128
    ideal = np.linspace(0.02, 0.98, step_count, dtype=np.float64)
    encoded = np.rint(ideal * 65535.0).astype(np.uint16)
    row = np.repeat(encoded, step_width)
    gray = np.repeat(row[np.newaxis, :], height, axis=0)
    rgb = np.repeat(gray[:, :, np.newaxis], 3, axis=2)
    provenance = {
        "schema": "m175-tone-sentinel-input-v1",
        "status": "DEVELOPMENT_ONLY_NOT_A_QUALITY_SCORE",
        "source_kind": "SYNTHETIC_33_STEP_NEUTRAL_LINEAR_RAMP",
        "step_count": step_count,
        "range": [0.02, 0.98],
        "selected_fork_commit": COMMIT,
        "icc_sha256": sha256(icc),
    }

    input_dir = work / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    first = input_dir / "ramp-01.tiff"
    layout = converter.write_common_tiff(first, rgb, icc, provenance)
    first_bytes = first.read_bytes()
    inputs = [first]
    for index in range(2, 9):
        path = input_dir / f"ramp-{index:02d}.tiff"
        path.write_bytes(first_bytes)
        inputs.append(path)

    input_records = []
    for path in inputs:
        inspected = converter.inspect_common_tiff(path)
        data = path.read_bytes()
        hits = [
            token.decode("ascii")
            for token in FORBIDDEN_INSTRUCTIONS
            if token.lower() in data.lower()
        ]
        if hits:
            raise PreparationFailure(
                f"forbidden development instruction found in {path}: {hits}"
            )
        input_records.append(
            {
                **file_record(path),
                "pixel_payload_sha256": inspected["pixel_payload_sha256"],
                "width": inspected["width"],
                "height": inspected["height"],
                "bits_per_sample": inspected["bits_per_sample"],
                "compression": inspected["compression"],
                "icc_sha256": inspected["icc_sha256"],
                "forbidden_instruction_hits": hits,
            }
        )
    if len({item["sha256"] for item in input_records}) != 1:
        raise PreparationFailure("the eight tone-sentinel TIFFs are not byte-identical")

    sample_margin_x = 16
    sample_margin_y = 16
    sites = []
    for index, (ideal_value, encoded_value) in enumerate(zip(ideal, encoded), start=1):
        x0 = (index - 1) * step_width + sample_margin_x
        x1 = index * step_width - sample_margin_x
        sites.append(
            {
                "step_1_based": index,
                "ideal_linear_value": float(ideal_value),
                "encoded_u16": int(encoded_value),
                "fit_x": float(encoded_value / 65535.0),
                "roi_xyxy_exclusive": [x0, sample_margin_y, x1, height - sample_margin_y],
            }
        )

    truth = {
        "schema": "m175-tone-sentinel-truth-v1",
        "status": "FROZEN_BEFORE_RENDERING",
        "step_count": step_count,
        "range": [0.02, 0.98],
        "fit_steps_1_based_inclusive": [2, 32],
        "sites": sites,
    }
    site_manifest = {
        "schema": "m175-tone-sentinel-site-manifest-v1",
        "status": "FROZEN_BEFORE_RENDERING",
        "selection_rule": (
            "Arithmetic central ROI for every predeclared constant step; "
            "16 pixels excluded from each vertical step edge and image top/bottom."
        ),
        "output_shape_expected_hwc": [height, step_count * step_width, 3],
        "sites": [
            {
                "step_1_based": item["step_1_based"],
                "roi_xyxy_exclusive": item["roi_xyxy_exclusive"],
            }
            for item in sites
        ],
    }
    input_manifest = {
        "schema": "m175-tone-sentinel-input-manifest-v1",
        "status": "FROZEN_BEFORE_RENDERING",
        "track": "common-merge",
        "eligibility": "DEVELOPMENT_TRANSFER_SENTINEL_ONLY_NOT_A_QUALITY_SCORE",
        "contract": {
            "copies": 8,
            "identical_bytes": True,
            "step_count": step_count,
            "range": [0.02, 0.98],
            "uncompressed": True,
            "bits_per_sample": [16, 16, 16],
            "sample_format": [1, 1, 1],
            "colour_space": "linear ProPhoto RGB D50",
            "native_dimensions": [step_count * step_width, height],
            "sidecars": [],
        },
        "writer": converter_record,
        "layout": layout,
        "inputs": input_records,
    }
    settings_manifest = {
        "schema": "m175-fork-settings-manifest-v1",
        "status": "FROZEN_BEFORE_RENDERING",
        "selected_commit": COMMIT,
        "settings": SETTINGS,
        "post_stack_processing": [],
        "per_subject_tuning": False,
        "post_result_rebuild_allowed": False,
    }
    run_manifest = {
        "schema": "m175-fork-run-manifest-v1",
        "status": "FROZEN_BEFORE_RENDERING",
        "purpose": "SECTION_1_3_DEVELOPMENT_TRANSFER_ADMISSION_ONLY",
        "quality_score": False,
        "holdout_used": False,
        "source_pin": file_record(source_pin_path),
        "revision_selection": file_record(revision_path),
        "build_freeze": file_record(build_freeze_path),
        "executable": executable_record,
        "runtime_bundle_sha256": build_freeze["dependencies"][
            "runtime_bundle_sha256"
        ],
        "settings": SETTINGS,
        "invocation": build_invocation(executable, output, inputs),
        "output_path": str(output),
        "output_contract": {
            "native_dimensions": [step_count * step_width, height],
            "dtype": "uint16",
            "channels": 3,
            "linear": True,
            "post_stack_processing": [],
        },
        "measurement_runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "tifffile": tifffile.__version__,
        },
    }

    truth_path = root / "TONE-TRUTH.json"
    site_path = root / "SITE-MANIFEST.json"
    input_path = root / "INPUT-MANIFEST.json"
    settings_path = root / "SETTINGS-MANIFEST.json"
    run_path = root / "RUN-MANIFEST.json"
    write_json(truth_path, truth)
    write_json(site_path, site_manifest)
    write_json(input_path, input_manifest)
    write_json(settings_path, settings_manifest)
    write_json(run_path, run_manifest)

    frozen_utc = datetime.now(timezone.utc).isoformat()
    frozen_files = [
        source_pin_path,
        revision_path,
        build_freeze_path,
        root / ".gitattributes",
        root / ".gitignore",
        root / "inspect_fork.py",
        root / "freeze_fork_source.py",
        root / "build_fork.py",
        Path(__file__).resolve(),
        root / "render_tone_sentinel.py",
        truth_path,
        site_path,
        input_path,
        settings_path,
        run_path,
    ]
    result = {
        "schema": SCHEMA,
        "status": "FROZEN",
        "frozen_utc": frozen_utc,
        "selected_commit": COMMIT,
        "executable_sha256": executable_record["sha256"],
        "input_file_sha256": input_records[0]["sha256"],
        "input_pixel_payload_sha256": input_records[0]["pixel_payload_sha256"],
        "all_eight_input_files_byte_identical": True,
        "frozen_files": [file_record(path) for path in frozen_files],
        "freeze_digest_sha256": sha256(
            canonical_json(
                [
                    {
                        "path": str(path.resolve()),
                        "sha256": file_record(path)["sha256"],
                    }
                    for path in frozen_files
                ]
            )
        ),
        "render_output_absent_at_freeze": not output.exists(),
    }
    if not result["render_output_absent_at_freeze"]:
        raise PreparationFailure("render output existed at freeze")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-freeze", required=True)
    parser.add_argument("--source-pin", required=True)
    parser.add_argument("--revision-selection", required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    try:
        result = prepare(args)
    except BaseException as exc:
        result = {
            "schema": SCHEMA,
            "status": "FAIL",
            "failure_class": type(exc).__name__,
            "reason": str(exc),
        }
        write_json(out, result)
        print(json.dumps(result, sort_keys=True))
        return 1
    write_json(out, result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
