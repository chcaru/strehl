#!/usr/bin/env python3
"""Render the already frozen M175 tone sentinel once and score scorecard §1.3."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

import numpy as np
import tifffile


SCHEMA = "m175-fork-tone-sentinel-result-v1"


class RenderFailure(RuntimeError):
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
        raise RenderFailure(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RenderFailure(f"{label} is not a JSON object")
    return value


def git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RenderFailure(
            f"git {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def committed_freeze(
    repo_root: Path, frozen_paths: list[Path]
) -> tuple[str, list[str], list[dict[str, Any]]]:
    records = []
    commits = set()
    for path in frozen_paths:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
        commit = (
            git(repo_root, "log", "-1", "--format=%H", "--", relative)
            .decode("ascii")
            .strip()
        )
        if len(commit) != 40:
            raise RenderFailure(f"no committed pre-render freeze for {relative}")
        committed = git(repo_root, "show", f"{commit}:{relative}")
        current = path.read_bytes()
        if committed != current:
            raise RenderFailure(f"working copy differs from committed freeze: {relative}")
        commits.add(commit)
        records.append(
            {
                "path": relative,
                "commit": commit,
                "sha256": sha256(current),
            }
        )
    guard_commit = git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()
    for commit in commits:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "merge-base",
                "--is-ancestor",
                commit,
                guard_commit,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise RenderFailure(
                f"freeze commit {commit} is not an ancestor of guard {guard_commit}"
            )
    return guard_commit, sorted(commits), records


def normalise_bits(value: Any) -> list[int]:
    if isinstance(value, tuple):
        return [int(item) for item in value]
    return [int(value)] * 3


def inspect_output(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    data = path.read_bytes()
    with tifffile.TiffFile(path) as tiff:
        if len(tiff.pages) != 1:
            raise RenderFailure(f"output has {len(tiff.pages)} TIFF pages")
        page = tiff.pages[0]
        array = page.asarray()
        icc_tag = page.tags.get(34675)
        icc = bytes(icc_tag.value) if icc_tag is not None else None
        offsets = [int(value) for value in page.dataoffsets]
        counts = [int(value) for value in page.databytecounts]
        raw_strips = b"".join(
            data[offset : offset + count] for offset, count in zip(offsets, counts)
        )
        metadata = {
            "width": int(page.imagewidth),
            "height": int(page.imagelength),
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "bits_per_sample": normalise_bits(page.bitspersample),
            "sample_format": str(page.sampleformat),
            "photometric": str(page.photometric),
            "compression": str(page.compression),
            "icc_present": icc is not None,
            "icc_sha256": sha256(icc) if icc is not None else None,
            "strip_count": len(offsets),
            "raw_strip_bytes_sha256": sha256(raw_strips),
            "decoded_pixel_bytes_sha256": sha256(
                np.ascontiguousarray(array).tobytes()
            ),
            "file": file_record(path),
        }
    return array, metadata


def score_transfer(
    array: np.ndarray, truth: dict[str, Any], site_manifest: dict[str, Any]
) -> dict[str, Any]:
    expected_shape = tuple(site_manifest["output_shape_expected_hwc"])
    format_checks = {
        "native_dimensions": tuple(array.shape) == expected_shape,
        "uint16": array.dtype == np.uint16,
        "three_channels": array.ndim == 3 and array.shape[2] == 3,
    }
    if array.ndim != 3 or array.shape[2] != 3:
        raise RenderFailure(f"cannot score non-RGB output shape {array.shape}")
    if tuple(array.shape) != expected_shape:
        raise RenderFailure(
            f"output shape {array.shape} differs from frozen {expected_shape}"
        )

    truth_by_step = {
        int(item["step_1_based"]): item for item in truth["sites"]
    }
    measurements = []
    for site in site_manifest["sites"]:
        step = int(site["step_1_based"])
        x0, y0, x1, y1 = [int(value) for value in site["roi_xyxy_exclusive"]]
        roi = array[y0:y1, x0:x1, :]
        if roi.size == 0:
            raise RenderFailure(f"empty frozen ROI for step {step}")
        channel_means = roi.reshape(-1, 3).mean(axis=0) / 65535.0
        channel_min = roi.reshape(-1, 3).min(axis=0)
        channel_max = roi.reshape(-1, 3).max(axis=0)
        measurements.append(
            {
                "step_1_based": step,
                "fit_x": float(truth_by_step[step]["fit_x"]),
                "channel_mean": [float(value) for value in channel_means],
                "channel_min_u16": [int(value) for value in channel_min],
                "channel_max_u16": [int(value) for value in channel_max],
            }
        )

    fit_start, fit_end = truth["fit_steps_1_based_inclusive"]
    fitted = [
        item
        for item in measurements
        if fit_start <= item["step_1_based"] <= fit_end
    ]
    x = np.array([item["fit_x"] for item in fitted], dtype=np.float64)
    channels = []
    for channel, name in enumerate(("R", "G", "B")):
        y = np.array(
            [item["channel_mean"][channel] for item in fitted], dtype=np.float64
        )
        design = np.column_stack([x, np.ones_like(x)])
        slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
        residual = y - (slope * x + intercept)
        max_abs = float(np.max(np.abs(residual)))
        rms = float(np.sqrt(np.mean(residual * residual)))
        strictly_monotone = bool(np.all(np.diff(y) > 0.0))
        no_interior_clips = all(
            item["channel_min_u16"][channel] > 0
            and item["channel_max_u16"][channel] < 65535
            for item in fitted
        )
        checks = {
            "slope_0_995_to_1_005": 0.995 <= slope <= 1.005,
            "abs_intercept_le_0_001": abs(intercept) <= 0.001,
            "max_abs_affine_residual_le_0_002": max_abs <= 0.002,
            "rms_affine_residual_le_0_0005": rms <= 0.0005,
            "no_interior_step_clips": no_interior_clips,
            "strictly_monotone": strictly_monotone,
        }
        channels.append(
            {
                "channel": name,
                "slope": float(slope),
                "intercept": float(intercept),
                "max_abs_affine_residual": max_abs,
                "rms_affine_residual": rms,
                "checks": checks,
                "pass": all(checks.values()),
            }
        )
    return {
        "fit_steps_1_based_inclusive": [fit_start, fit_end],
        "site_statistic": "arithmetic mean over each frozen central ROI",
        "format_checks": format_checks,
        "measurements": measurements,
        "channels": channels,
        "pass": all(format_checks.values())
        and all(item["pass"] for item in channels),
    }


def render(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(__file__).resolve().parent
    repo_root = root.parents[1]
    result_path = Path(args.out).resolve()
    if result_path.exists():
        raise RenderFailure("refusing to overwrite an existing render result")

    pre_freeze_path = Path(args.pre_render_freeze).resolve()
    build_freeze_path = root / "build-freeze.json"
    source_pin_path = root / "source-pin.json"
    revision_path = root / "revision-selection.json"
    input_manifest_path = root / "INPUT-MANIFEST.json"
    site_manifest_path = root / "SITE-MANIFEST.json"
    run_manifest_path = root / "RUN-MANIFEST.json"
    settings_path = root / "SETTINGS-MANIFEST.json"
    truth_path = root / "TONE-TRUTH.json"
    frozen_paths = [
        root / ".gitignore",
        root / ".gitattributes",
        root / "inspect_fork.py",
        root / "freeze_fork_source.py",
        root / "build_fork.py",
        root / "prepare_tone_sentinel.py",
        root / "render_tone_sentinel.py",
        revision_path,
        source_pin_path,
        build_freeze_path,
        input_manifest_path,
        site_manifest_path,
        run_manifest_path,
        settings_path,
        truth_path,
        pre_freeze_path,
    ]
    pre_render_guard_commit, pre_render_commits, commit_records = committed_freeze(
        repo_root, frozen_paths
    )

    pre_freeze = load_json(pre_freeze_path, "pre-render freeze")
    build_freeze = load_json(build_freeze_path, "build freeze")
    input_manifest = load_json(input_manifest_path, "input manifest")
    site_manifest = load_json(site_manifest_path, "site manifest")
    run_manifest = load_json(run_manifest_path, "run manifest")
    truth = load_json(truth_path, "tone truth")
    if pre_freeze.get("status") != "FROZEN":
        raise RenderFailure("pre-render freeze status is not FROZEN")
    if build_freeze.get("status") != "FROZEN":
        raise RenderFailure("build freeze status is not FROZEN")

    executable = Path(run_manifest["executable"]["path"])
    executable_record = file_record(executable)
    expected_sha = pre_freeze["executable_sha256"]
    if executable_record["sha256"] != expected_sha:
        raise RenderFailure(
            f"executable is {executable_record['sha256']}, expected {expected_sha}"
        )

    inputs = [Path(item["path"]) for item in input_manifest["inputs"]]
    if len(inputs) != 8:
        raise RenderFailure(f"input manifest has {len(inputs)} files, expected 8")
    current_input_records = [file_record(path) for path in inputs]
    for expected, current in zip(input_manifest["inputs"], current_input_records):
        if expected["sha256"] != current["sha256"]:
            raise RenderFailure(f"input changed after freeze: {current['path']}")
    if len({item["sha256"] for item in current_input_records}) != 1:
        raise RenderFailure("the eight rendered inputs are not byte-identical")

    invocation = [str(value) for value in run_manifest["invocation"]]
    output = Path(run_manifest["output_path"])
    if output.exists():
        raise RenderFailure(f"refusing stale output {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    render_started_utc = datetime.now(timezone.utc).isoformat()
    start_record = {
        "schema": "m175-fork-render-start-v1",
        "status": "STARTING",
        "render_started_utc": render_started_utc,
        "pre_render_guard_commit": pre_render_guard_commit,
        "pre_render_commits": pre_render_commits,
        "pre_render_freeze": file_record(pre_freeze_path),
        "executable": executable_record,
        "input_file_sha256": current_input_records[0]["sha256"],
        "input_count": len(inputs),
        "output_absent_before_launch": not output.exists(),
        "invocation": invocation,
    }
    start_path = root / "render-start.json"
    write_json(start_path, start_record)
    start_file_record = file_record(start_path)

    completed = subprocess.run(
        invocation,
        cwd=output.parent,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0 or not output.is_file():
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "failure_class": "RENDER_FAILED",
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "render_start": start_file_record,
            "pre_render_guard_commit": pre_render_guard_commit,
            "pre_render_commits": pre_render_commits,
        }

    array, output_metadata = inspect_output(output)
    transfer = score_transfer(array, truth, site_manifest)
    frozen_utc = datetime.fromisoformat(pre_freeze["frozen_utc"])
    render_started = datetime.fromisoformat(render_started_utc)
    ordering = {
        "pre_render_guard_commit": pre_render_guard_commit,
        "pre_render_commits": pre_render_commits,
        "all_pre_render_files_identical_to_commit": True,
        "committed_files": commit_records,
        "pre_render_freeze_utc": frozen_utc.isoformat(),
        "render_started_utc": render_started.isoformat(),
        "freeze_precedes_render": frozen_utc < render_started,
        "render_start_artifact": start_file_record,
    }
    status = "PASS" if transfer["pass"] and ordering["freeze_precedes_render"] else "BLOCKED"
    return {
        "schema": SCHEMA,
        "status": status,
        "fork_arm_verdict": (
            "REBUILT_AND_SECTION_1_3_PASS"
            if status == "PASS"
            else "BLOCKED_SECTION_1_3_OR_FREEZE_ORDER"
        ),
        "quality_score": False,
        "holdout_used": False,
        "selected_commit": build_freeze["source"]["commit_sha1"],
        "source_tree_sha1": build_freeze["source"]["tree_sha1"],
        "source_manifest_sha256": build_freeze["source"]["manifest_sha256"],
        "executable": executable_record,
        "reproducibility": build_freeze["reproducibility"],
        "runtime_bundle_sha256": build_freeze["dependencies"][
            "runtime_bundle_sha256"
        ],
        "settings": load_json(settings_path, "settings manifest"),
        "input": {
            "count": len(inputs),
            "all_byte_identical": True,
            "file_sha256": current_input_records[0]["sha256"],
            "pixel_payload_sha256": input_manifest["inputs"][0][
                "pixel_payload_sha256"
            ],
            "manifest": file_record(input_manifest_path),
        },
        "invocation": invocation,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "output": output_metadata,
        "section_1_3": transfer,
        "freeze_order": ordering,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre-render-freeze", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    if out.exists():
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "status": "BLOCKED",
                    "failure_class": "RESULT_ALREADY_EXISTS",
                    "reason": f"refusing to overwrite {out.resolve()}",
                },
                sort_keys=True,
            )
        )
        return 1
    try:
        result = render(args)
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
