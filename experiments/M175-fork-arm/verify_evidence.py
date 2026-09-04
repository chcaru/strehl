#!/usr/bin/env python3
"""Independently verify the persisted M175 rebuild and tone-transfer evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import tifffile


COMMIT = "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"
EXECUTABLE_SHA256 = "691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} is not an object")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return completed.stdout.strip()


def main() -> int:
    root = Path(__file__).resolve().parent
    repo = root.parents[1]
    build = load(root / "build-freeze.json")
    source = load(root / "source-pin.json")
    inputs = load(root / "INPUT-MANIFEST.json")
    sites = load(root / "SITE-MANIFEST.json")
    truth = load(root / "TONE-TRUTH.json")
    start = load(root / "render-start.json")
    result = load(root / "render-result.json")
    output = root / "work" / "tone-sentinel" / "output" / "tone-sentinel.tiff"
    executable = root / "bin" / "focus-stack.exe"

    checks: dict[str, bool] = {}
    checks["source_commit"] = source["commit"]["resolved"] == COMMIT
    checks["build_source_commit"] = build["source"]["commit_sha1"] == COMMIT
    build_hashes = [
        item["executable"]["sha256"] for item in build["reproducibility"]["builds"]
    ]
    checks["two_builds"] = len(build_hashes) == 2
    checks["two_builds_byte_identical"] = (
        build["reproducibility"]["byte_identical"]
        and build["reproducibility"]["differing_bytes"] == 0
        and len(set(build_hashes)) == 1
    )
    checks["expected_executable_hash"] = build_hashes == [
        EXECUTABLE_SHA256,
        EXECUTABLE_SHA256,
    ]
    checks["current_executable_hash"] = (
        sha256(executable.read_bytes()) == EXECUTABLE_SHA256
    )
    checks["result_executable_hash"] = (
        result["executable"]["sha256"] == EXECUTABLE_SHA256
    )
    checks["freeze_before_render"] = bool(
        result["freeze_order"]["freeze_precedes_render"]
        and result["freeze_order"]["render_start_precedes_output_creation"]
    )
    checks["output_absent_before_launch"] = bool(start["output_absent_before_launch"])
    checks["eight_input_occurrences"] = len(inputs["inputs"]) == 8
    checks["identical_input_hashes"] = (
        len({item["sha256"] for item in inputs["inputs"]}) == 1
    )
    checks["no_holdout_path"] = "7-aperture-pairs" not in json.dumps(
        [inputs, start, result], sort_keys=True
    ).lower()

    with tifffile.TiffFile(output) as tiff:
        page = tiff.pages[0]
        array = page.asarray()
        checks["single_page"] = len(tiff.pages) == 1
        checks["native_shape"] = list(array.shape) == [4688, 7028, 3]
        checks["uint16"] = array.dtype == np.uint16
        checks["bits_per_sample"] = int(page.bitspersample) == 16
    checks["output_file_hash"] = (
        sha256(output.read_bytes()) == result["output"]["file"]["sha256"]
    )
    checks["decoded_output_matches_input_payload"] = (
        sha256(np.ascontiguousarray(array).tobytes())
        == inputs["inputs"][0]["pixel_payload_sha256"]
    )

    truth_by_step = {
        int(item["step_1_based"]): item for item in truth["sites"]
    }
    measured = []
    for site in sites["sites"]:
        step = int(site["step_1_based"])
        x0, y0, x1, y1 = [int(value) for value in site["roi_xyxy_exclusive"]]
        means = array[y0:y1, x0:x1, :].reshape(-1, 3).mean(axis=0) / 65535.0
        measured.append((step, means))
    selected = [item for item in measured if 2 <= item[0] <= 32]
    x = np.array(
        [truth_by_step[item[0]]["fit_x"] for item in selected], dtype=np.float64
    )
    channel_results = []
    for channel, name in enumerate(("R", "G", "B")):
        y = np.array([item[1][channel] for item in selected], dtype=np.float64)
        design = np.column_stack([x, np.ones_like(x)])
        slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
        residual = y - (slope * x + intercept)
        channel_results.append(
            {
                "channel": name,
                "slope": float(slope),
                "intercept": float(intercept),
                "max_abs_affine_residual": float(np.max(np.abs(residual))),
                "rms_affine_residual": float(np.sqrt(np.mean(residual * residual))),
                "strictly_monotone": bool(np.all(np.diff(y) > 0)),
                "pass": bool(
                    0.995 <= slope <= 1.005
                    and abs(intercept) <= 0.001
                    and np.max(np.abs(residual)) <= 0.002
                    and np.sqrt(np.mean(residual * residual)) <= 0.0005
                    and np.all(np.diff(y) > 0)
                ),
            }
        )
    checks["all_channels_pass_section_1_3"] = all(
        item["pass"] for item in channel_results
    )
    checks["persisted_result_pass"] = (
        result["status"] == "PASS"
        and result["fork_arm_verdict"] == "REBUILT_AND_SECTION_1_3_PASS"
    )

    m165_build = repo / "experiments" / "M165-fork-rebuild" / "build-freeze.json"
    if m165_build.is_file():
        m165 = load(m165_build)
        checks["independent_m165_hash_match"] = (
            m165["frozen_executable"]["sha256"] == EXECUTABLE_SHA256
        )
        independent_reference = {
            "path": str(m165_build.resolve()),
            "git_commit": git(
                repo,
                "log",
                "-1",
                "--format=%H",
                "--",
                m165_build.relative_to(repo).as_posix(),
            ),
            "executable_sha256": m165["frozen_executable"]["sha256"],
        }
    else:
        checks["independent_m165_hash_match"] = False
        independent_reference = {"status": "ABSENT"}

    verification = {
        "schema": "m175-fork-independent-verification-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "channel_results": channel_results,
        "independent_reference": independent_reference,
        "artifacts": {
            "source_pin_sha256": sha256((root / "source-pin.json").read_bytes()),
            "build_freeze_sha256": sha256((root / "build-freeze.json").read_bytes()),
            "pre_render_freeze_sha256": sha256(
                (root / "PRE-RENDER-FREEZE.json").read_bytes()
            ),
            "render_start_sha256": sha256(start_path.read_bytes())
            if (start_path := root / "render-start.json")
            else "",
            "render_result_sha256": sha256((root / "render-result.json").read_bytes()),
            "output_sha256": sha256(output.read_bytes()),
        },
    }
    write(root / "verification.json", verification)
    print(json.dumps(verification, sort_keys=True))
    return 0 if verification["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
