from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import winreg
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m11_core import (
    COMPARATOR_PRODUCT_IDS,
    GUARD_REGISTRY,
    LANE_ROOT,
    OPTIONAL_COMPARATOR_MODES,
    QUALITY_CRITERION_ID,
    REGISTERED_COMPARATOR_MODES,
    REQUIRED_COMPARATOR_MODES,
    REQUIRED_QUALITY_GATES,
    STREHL_QUALITY_MODE_ID,
    _hash_text,
    alternating_schedule,
    cold_pair_schedule,
    describe,
    evaluate_guard,
    expected_capture_names,
    object_sha256,
    paired_mean_interval,
    path_is_within,
    require_guard,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from m11_runtime import (
    GpuSampler,
    ReadOnlyFileLocks,
    qpc_frequency,
    qpc_ticks,
    run_timed_invocation,
    sha256_file_uncached,
    stage_measurements,
    system_times,
    tiff_witness,
    unapproved_gpu_processes,
)
from synthetic_target import DEFAULT_ICC


ROOT = LANE_ROOT.parents[1]
CONTRACT_PATH = LANE_ROOT / "contract.json"
SCORECARD_PATH = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
SYNTHETIC_TARGET = LANE_ROOT / "synthetic_target.py"
LIVE_REPLAY = LANE_ROOT / "live_replay.py"
PYTHON_EXECUTABLE = Path(sys.executable).resolve(strict=True)
REGISTERED_COUNTS = (33, 105, 299)
WORKER_LADDER = (1, 2, 4, 8, 16)
CANONICAL_SCORED_REPETITION = 1
QUALITY_CELLS = (
    ("bee-1-cpl", 33),
    ("coffee-bean", 105),
    ("bee-1-cpl", 299),
)
SYNTHETIC_STAGES = ["load", "register", "stack", "color", "write"]
RUN_IDENTITY_FIELDS = (
    "segment",
    "arm",
    "role",
    "mode_id",
    "setting_id",
    "stack_id",
    "count",
    "workers",
    "settings_sha256",
    "input_manifest_sha256",
    "input_content_sha256",
    "output_contract_sha256",
    "output_sha256",
    "pixel_sha256",
    "phase",
    "repetition",
    "direction",
    "position",
    "campaign_sha256",
    "authorization_sha256",
    "contract_sha256",
    "measured_commit",
    "campaign_attempt_id",
)
COMMISSION_SOURCE_PATHS = (
    LANE_ROOT / "m11_core.py",
    LANE_ROOT / "m11_runtime.py",
    LANE_ROOT / "m11_harness.py",
    LANE_ROOT / "synthetic_target.py",
    LANE_ROOT / "live_replay.py",
    LANE_ROOT / "mutation_commission.py",
    LANE_ROOT / "test_m11_harness.py",
    LANE_ROOT / "test_runtime.py",
    LANE_ROOT / "campaign-template.json",
    LANE_ROOT / "quality-manifest-template.json",
    LANE_ROOT / "real-run-authorization-template.json",
    LANE_ROOT / "observer-hash-control-template.json",
    LANE_ROOT / "m12-worker16-export-template.json",
    LANE_ROOT / "live-replay-registration-template.json",
    LANE_ROOT / "adapter-identity-template.json",
    LANE_ROOT / "adapter-identity-commission-template.json",
    LANE_ROOT / "staged-input-manifest-template.json",
    LANE_ROOT / "m12-measurement-manifest-template.json",
    LANE_ROOT / "m12-worker16-records-template.json",
    LANE_ROOT / "m12-campaign-template.json",
    LANE_ROOT / "quality-checker-commission-template.json",
    LANE_ROOT / "quality-evidence-template.json",
    LANE_ROOT / "quality-corpus-evidence-template.json",
    LANE_ROOT / "signed-acquisition-trace-template.json",
    LANE_ROOT / "acquisition-signature-commission-template.json",
    LANE_ROOT / "actual-reboot-receipt-template.json",
    LANE_ROOT / "native-dimensions-evidence-template.json",
    LANE_ROOT / "native-dimensions-commission-template.json",
)


def repository_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def command_file_arguments(
    argv: list[Any],
    *,
    cwd: Path,
) -> set[Path]:
    files = set()
    resolved_cwd = cwd.resolve(strict=True)
    for raw_token in argv:
        token = str(raw_token)
        candidates = [token]
        if token.startswith(("-", "/")) and "=" in token:
            candidates.append(token.split("=", 1)[1])
        for candidate in candidates:
            try:
                path = Path(candidate)
                if not path.is_absolute():
                    path = resolved_cwd / path
                if path.is_file():
                    files.add(path.resolve(strict=True))
            except (OSError, ValueError):
                continue
    return files


def canonicalize_command_file_arguments(
    argv: list[str],
    *,
    cwd: Path,
) -> list[str]:
    resolved_cwd = cwd.resolve(strict=True)
    canonical = []
    for token in argv:
        prefix = ""
        candidate = token
        if token.startswith(("-", "/")) and "=" in token:
            option, candidate = token.split("=", 1)
            prefix = f"{option}="
        path = Path(candidate)
        if not path.is_absolute():
            path = resolved_cwd / path
        if path.is_file():
            canonical.append(prefix + str(path.resolve(strict=True)))
        else:
            canonical.append(token)
    return canonical


def require_bound_command_files(
    argv: list[Any],
    bound_paths: set[Path],
    *,
    cwd: Path,
    allowed_data_paths: set[Path] | None = None,
) -> None:
    referenced = command_file_arguments(argv, cwd=cwd)
    allowed = bound_paths | (allowed_data_paths or set())
    if not referenced.issubset(allowed):
        extras = sorted(str(path) for path in referenced - allowed)
        raise ValueError(f"command references unbound file arguments: {extras}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def quality_cell_id(capture_id: str, count: int) -> str:
    return f"{capture_id}:N{count}"


def quality_envelope_complete_for_cell(
    *,
    decisions: dict[str, str],
    available_modes: set[str],
    qualified_comparator_modes: set[str],
    strehl_qualified: bool,
) -> bool:
    return (
        set(decisions) == REGISTERED_COMPARATOR_MODES | {STREHL_QUALITY_MODE_ID}
        and all(
            status in {"QUALITY_QUALIFIED", "QUALITY_FAILED"}
            for mode_id, status in decisions.items()
            if mode_id in available_modes
        )
        and all(
            decisions.get(mode_id) == "UNAVAILABLE"
            for mode_id in OPTIONAL_COMPARATOR_MODES - available_modes
        )
        and REQUIRED_COMPARATOR_MODES <= qualified_comparator_modes
        and strehl_qualified
    )


def comparator_quality_fingerprint(
    quality_data: dict[str, Any],
    quality_result: dict[str, Any],
    *,
    mode_id: str,
    cell_id: str,
    count: int,
) -> dict[str, Any]:
    quality_mode = quality_data["modes"][mode_id]
    quality_cell = quality_mode["cell_qualifications"][cell_id]
    return {
        "mode_id": mode_id,
        "binary_sha256": quality_mode["binary_sha256"],
        "settings_sha256": quality_mode["settings_sha256"],
        "input_manifest_sha256": quality_cell["input_manifest_sha256"],
        "output_contract_sha256": quality_mode["output_contract_sha256"],
        "count": count,
        "executable_bundle_sha256": quality_result["mode_results"][mode_id][
            "executable_bundle_sha256"
        ],
    }


def read_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"))


def parse_json_line(line: str) -> Any:
    return strict_json_loads(line)


def write_json(path: Path, value: Any) -> None:
    require_guard(
        "G01-owned-output",
        {"path": str(path), "lane_root": str(LANE_ROOT)},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, allow_nan=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def append_jsonl(path: Path, value: Any) -> None:
    require_guard(
        "G01-owned-output",
        {"path": str(path), "lane_root": str(LANE_ROOT)},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, allow_nan=False, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())


def load_contract() -> dict[str, Any]:
    contract = read_json(CONTRACT_PATH)
    if contract.get("schema") != "m153-m11-contract-v1":
        raise ValueError("unsupported M153 contract schema")
    actual_scorecard = sha256_file(SCORECARD_PATH)
    expected_scorecard = contract["scorecard"]["sha256"]
    if actual_scorecard != expected_scorecard:
        raise ValueError(
            "scorecard bytes changed after M153 contract freeze: "
            f"expected {expected_scorecard}, got {actual_scorecard}"
        )
    return contract


def contract_hash() -> dict[str, Any]:
    contract = load_contract()
    return {
        "schema": contract["schema"],
        "path": str(CONTRACT_PATH.relative_to(ROOT)),
        "sha256": sha256_file(CONTRACT_PATH),
        "scorecard_sha256": contract["scorecard"]["sha256"],
    }


def commission_source_bindings_current(
    source_bindings: dict[str, Any],
) -> bool:
    try:
        return set(source_bindings) == {
            path.name for path in COMMISSION_SOURCE_PATHS
        } and all(
            Path(row["path"]).resolve(strict=True) == path.resolve(strict=True)
            and sha256_file(path) == row["sha256"]
            for path in COMMISSION_SOURCE_PATHS
            for row in (source_bindings[path.name],)
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False


def commission_runtime_binding_current(commission: dict[str, Any]) -> bool:
    try:
        binding = commission["runtime"]["python_executable"]
        executable = PYTHON_EXECUTABLE
        return Path(binding["path"]).resolve(strict=True) == executable and binding[
            "sha256"
        ] == sha256_file(executable)
    except (KeyError, OSError, TypeError, ValueError):
        return False


def directory_snapshot(path: Path) -> dict[str, Any]:
    rows = []
    total_bytes = 0
    with os.scandir(path) as entries:
        for entry in entries:
            stat = entry.stat(follow_symlinks=False)
            row = {
                "name": entry.name,
                "is_file": entry.is_file(follow_symlinks=False),
                "is_dir": entry.is_dir(follow_symlinks=False),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "attributes": getattr(stat, "st_file_attributes", None),
            }
            rows.append(row)
            if row["is_file"]:
                total_bytes += int(row["size"])
    rows.sort(key=lambda row: row["name"].casefold())
    return {
        "path": str(path),
        "enumeration": "os.scandir including hidden/system entries (Get-ChildItem -Force semantics)",
        "file_count": sum(bool(row["is_file"]) for row in rows),
        "entry_count": len(rows),
        "total_bytes": total_bytes,
        "sha256": object_sha256(rows),
    }


def capture_row(spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(spec["source_path"])
    if not path.is_dir():
        raise FileNotFoundError(path)
    before = directory_snapshot(path)
    with os.scandir(path) as entries:
        files = sorted(
            (
                entry
                for entry in entries
                if entry.is_file(follow_symlinks=False)
                and Path(entry.name).suffix.casefold() == ".arw"
            ),
            key=lambda entry: entry.name.casefold(),
        )
    actual = [entry.name.upper() for entry in files]
    first_number = int(Path(spec["first_file"]).stem[3:])
    expected = [
        f"DSC{number:05d}.ARW"
        for number in range(first_number, first_number + int(spec["frame_count"]))
    ]
    row = {
        "path": str(path),
        "count": len(files),
        "first": files[0].name if files else None,
        "last": files[-1].name if files else None,
        "total_arw_bytes": sum(
            entry.stat(follow_symlinks=False).st_size for entry in files
        ),
        "evidence_class": spec["evidence_class"],
        "missing": sorted(set(expected) - set(actual)),
        "unexpected": sorted(set(actual) - set(expected)),
    }
    after = directory_snapshot(path)
    require_guard("G03-readonly-snapshot", {"before": before, "after": after})
    return row, {"before": before, "after": after}


def census(output: Path) -> int:
    output = output.resolve()
    contract = load_contract()
    captures: dict[str, Any] = {}
    snapshots: dict[str, Any] = {}
    for stack_id, spec in contract["inputs"].items():
        captures[stack_id], snapshots[stack_id] = capture_row(spec)
    capture_guard = require_guard(
        "G02-capture-contract",
        {"captures": captures},
    )
    result = {
        "schema": "m153-input-census-v1",
        "evidence_tag": "VERIFIED_METADATA_ONLY",
        "generated_utc": utc_now(),
        "contract": contract_hash(),
        "access_scope": (
            "Read-only directory metadata and ARW names/counts/sizes only; no RAW "
            "decode, render, output, metric, or visual outcome was read."
        ),
        "holdout_ruling": {
            "bee-1-cpl": "HOLDOUT - PERFORMANCE; not development material",
            "coffee-bean": "FIXED HISTORICAL BENCHMARK - NOT HOLDOUT",
        },
        "captures": captures,
        "readonly_snapshots": snapshots,
        "guards": [capture_guard.to_json()]
        + [
            require_guard(
                "G03-readonly-snapshot",
                snapshots[stack_id],
            ).to_json()
            for stack_id in sorted(snapshots)
        ],
        "status": "PASS",
    }
    write_json(output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "bee-1-cpl": captures["bee-1-cpl"]["count"],
                "coffee-bean": captures["coffee-bean"]["count"],
            },
            sort_keys=True,
        )
    )
    return 0


def read_artifact_binding(
    path: Path,
    expected_sha256: str,
    *,
    uncached: bool = False,
) -> dict[str, Any]:
    path = repository_path(path)
    actual = sha256_file_uncached(path) if uncached else sha256_file(path)
    return {
        "path": str(path.resolve()),
        "expected_sha256": expected_sha256,
        "actual_sha256": actual,
        "verified": actual == expected_sha256,
        "read_mode": "WINDOWS_NO_BUFFERING" if uncached else "BUFFERED",
    }


def load_bound_json(reference: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    path = repository_path(reference["path"])
    binding = read_artifact_binding(path, reference["sha256"])
    require_guard("G04-artifact-binding", {"artifacts": [binding]})
    return read_json(path), binding


def run_commissioned_checker(
    *,
    artifact_path: Path,
    payload_sha256: str,
    checker_artifact: dict[str, Any],
    checker_support_artifacts: list[dict[str, Any]],
    commission: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run a frozen checker against the exact payload being accepted."""

    references = [checker_artifact, *checker_support_artifacts]
    bindings = [
        read_artifact_binding(
            repository_path(reference["path"]),
            reference["sha256"],
        )
        for reference in references
    ]
    require_guard("G04-artifact-binding", {"artifacts": bindings})
    normalized_bundle = [
        {"path": binding["path"], "sha256": binding["actual_sha256"]}
        for binding in bindings
    ]
    template = commission.get("verification_argv", [])
    if (
        not isinstance(template, list)
        or not template
        or "{artifact}" not in "\0".join(str(token) for token in template)
        or "{payload_sha256}" not in "\0".join(str(token) for token in template)
        or any(
            str(token).casefold()
            in {"-c", "-m", "/c", "-command", "-encodedcommand", "-e"}
            for token in template
        )
    ):
        raise ValueError("checker verification command is not safely bound")
    argv = [
        str(token).format_map(
            {
                "artifact": str(artifact_path.resolve(strict=True)),
                "payload_sha256": payload_sha256,
            }
        )
        for token in template
    ]
    argv = canonicalize_command_file_arguments(argv, cwd=ROOT)
    if repository_path(argv[0]).resolve(strict=True) != Path(
        bindings[0]["path"]
    ).resolve(strict=True):
        raise ValueError("checker command does not launch its primary bound artifact")
    bound_paths = {Path(binding["path"]).resolve(strict=True) for binding in bindings}
    referenced_paths = command_file_arguments(argv, cwd=ROOT) - {
        artifact_path.resolve(strict=True)
    }
    if referenced_paths != bound_paths:
        raise ValueError(
            "checker command must reference every and only declared checker artifacts"
        )
    locked_paths = [Path(binding["path"]) for binding in bindings]
    with ReadOnlyFileLocks([artifact_path, *locked_paths]):
        locked_bindings = [
            read_artifact_binding(
                Path(binding["path"]),
                binding["actual_sha256"],
            )
            for binding in bindings
        ]
        require_guard("G04-artifact-binding", {"artifacts": locked_bindings})
        locked_artifact = read_json(artifact_path)
        locked_payload = {
            key: value
            for key, value in locked_artifact.items()
            if key != "commission_artifact"
        }
        if object_sha256(locked_payload) != payload_sha256:
            raise ValueError("checker payload changed before verification")
        result = subprocess.run(
            argv,
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=float(commission.get("verification_timeout_seconds", 120.0)),
        )
        post_bindings = [
            read_artifact_binding(
                Path(binding["path"]),
                binding["actual_sha256"],
            )
            for binding in bindings
        ]
        require_guard("G04-artifact-binding", {"artifacts": post_bindings})
    observed = strict_json_loads(result.stdout)
    if (
        observed.get("schema") != "m153-commissioned-check-result-v1"
        or observed.get("status") != "PASS"
        or observed.get("artifact_payload_sha256") != payload_sha256
        or observed.get("checker_bundle_sha256") != object_sha256(normalized_bundle)
        or observed.get("mutations_killed") != observed.get("mutations_total")
        or int(observed.get("mutations_total", 0)) < 1
        or observed.get("inert_survived") != 1
    ):
        raise ValueError("commissioned checker did not accept the exact payload")
    return observed, bindings


def checker_bundle_approved(kind: str, bundle_sha256: str) -> bool:
    policy = load_contract().get("external_checkers", {}).get(kind, {})
    return policy.get("status") == "RATIFIED" and bundle_sha256 in policy.get(
        "approved_bundle_sha256", []
    )


def quality_evidence_valid(
    evidence: dict[str, Any],
    *,
    evidence_path: Path,
    schema: str,
    capture_id: str,
    count: int,
    mode_id: str,
    axis: str | None,
    fingerprint: dict[str, Any],
    scorecard_sha256: str,
) -> bool:
    if (
        evidence.get("schema") != schema
        or evidence.get("evidence_tag") != "MEASURED"
        or evidence.get("verdict") not in {"PASS", "FAIL"}
        or evidence.get("capture_id") != capture_id
        or evidence.get("count") != count
        or evidence.get("mode_id") != mode_id
        or evidence.get("scorecard_sha256") != scorecard_sha256
    ):
        return False
    if axis is not None and evidence.get("axis") != axis:
        return False
    for field in (
        "measured_commit",
        "binary_sha256",
        "executable_bundle_sha256",
        "settings_sha256",
        "input_manifest_sha256",
        "output_contract_sha256",
    ):
        if evidence.get(field) != fingerprint.get(field):
            return False
    payload = {
        key: value for key, value in evidence.items() if key != "commission_artifact"
    }
    try:
        commission, commission_binding = load_bound_json(
            evidence["commission_artifact"]
        )
        checker_result, checker_bindings = run_commissioned_checker(
            artifact_path=evidence_path,
            payload_sha256=object_sha256(payload),
            checker_artifact=evidence["checker_artifact"],
            checker_support_artifacts=evidence.get(
                "checker_support_artifacts",
                [],
            ),
            commission=commission,
        )
        require_guard(
            "G04-artifact-binding",
            {"artifacts": [commission_binding, *checker_bindings]},
        )
    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.SubprocessError,
    ):
        return False
    return (
        commission.get("schema") == "m153-quality-checker-commission-v1"
        and commission.get("status") == "PASS"
        and commission.get("checker_sha256") == checker_bindings[0]["actual_sha256"]
        and commission.get("checker_bundle_sha256")
        == checker_result["checker_bundle_sha256"]
        and checker_bundle_approved(
            "quality",
            checker_result["checker_bundle_sha256"],
        )
        and commission.get("scorecard_sha256") == scorecard_sha256
        and commission.get("evidence_schema") == schema
        and commission.get("accepted_evidence_payload_sha256") == object_sha256(payload)
        and commission.get("mutations_killed") == commission.get("mutations_total")
        and int(commission.get("mutations_total", 0)) >= 1
        and commission.get("inert_survived") == 1
        and checker_result.get("mutations_killed") == commission.get("mutations_killed")
        and checker_result.get("mutations_total") == commission.get("mutations_total")
        and checker_result.get("inert_survived") == commission.get("inert_survived")
        and checker_result.get("verdict") == evidence.get("verdict")
    )


def quality_corpus_evidence_valid(
    evidence: dict[str, Any],
    *,
    evidence_path: Path,
    mode_id: str,
    fingerprint: dict[str, Any],
    scorecard_sha256: str,
) -> tuple[bool, dict[str, Any]]:
    required_fingerprint_fields = (
        "measured_commit",
        "binary_sha256",
        "executable_bundle_sha256",
        "settings_sha256",
        "output_contract_sha256",
    )
    outputs = evidence.get("quality_outputs", [])
    structural = (
        evidence.get("schema") == "m153-m11-quality-corpus-evidence-v1"
        and evidence.get("evidence_tag") == "MEASURED"
        and evidence.get("verdict") in {"PASS", "FAIL"}
        and evidence.get("mode_id") == mode_id
        and evidence.get("scorecard_sha256") == scorecard_sha256
        and all(
            evidence.get(field) == fingerprint.get(field)
            for field in required_fingerprint_fields
        )
        and isinstance(outputs, list)
        and bool(outputs)
        and all(
            isinstance(row, dict)
            and bool(row.get("capture_id"))
            and _hash_text(row.get("input_manifest_sha256"))
            and _hash_text(row.get("output_sha256"))
            and _hash_text(row.get("pixel_sha256"))
            for row in outputs
        )
        and evidence.get("all_readings_hash_bound") is True
        and evidence.get("no_timing_cell_setting_difference") is True
    )
    payload = {
        key: value for key, value in evidence.items() if key != "commission_artifact"
    }
    try:
        commission, commission_binding = load_bound_json(
            evidence["commission_artifact"]
        )
        checker_result, checker_bindings = run_commissioned_checker(
            artifact_path=evidence_path,
            payload_sha256=object_sha256(payload),
            checker_artifact=evidence["checker_artifact"],
            checker_support_artifacts=evidence.get(
                "checker_support_artifacts",
                [],
            ),
            commission=commission,
        )
        require_guard(
            "G04-artifact-binding",
            {"artifacts": [commission_binding, *checker_bindings]},
        )
    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.SubprocessError,
    ):
        return False, {}
    commissioned = (
        commission.get("schema") == "m153-quality-checker-commission-v1"
        and commission.get("status") == "PASS"
        and commission.get("checker_sha256") == checker_bindings[0]["actual_sha256"]
        and commission.get("checker_bundle_sha256")
        == checker_result["checker_bundle_sha256"]
        and checker_bundle_approved(
            "quality",
            checker_result["checker_bundle_sha256"],
        )
        and commission.get("scorecard_sha256") == scorecard_sha256
        and commission.get("evidence_schema") == evidence.get("schema")
        and commission.get("accepted_evidence_payload_sha256") == object_sha256(payload)
        and commission.get("mutations_killed") == commission.get("mutations_total")
        and int(commission.get("mutations_total", 0)) >= 1
        and commission.get("inert_survived") == 1
        and checker_result.get("mutations_killed") == commission.get("mutations_killed")
        and checker_result.get("mutations_total") == commission.get("mutations_total")
        and checker_result.get("inert_survived") == commission.get("inert_survived")
        and checker_result.get("verdict") == evidence.get("verdict")
    )
    return structural and commissioned, evidence


def validate_quality_manifest(
    path: Path,
    *,
    uncached_executables: bool = False,
) -> dict[str, Any]:
    source_manifest = {
        "path": str(path.resolve(strict=True)),
        "sha256": sha256_file(path),
    }
    manifest = read_json(path)
    modes = manifest.get("modes", {})
    registered_quality_modes = REGISTERED_COMPARATOR_MODES | {STREHL_QUALITY_MODE_ID}
    required_cells = {
        quality_cell_id(capture_id, count) for capture_id, count in QUALITY_CELLS
    }
    contract = load_contract()
    scorecard_sha256 = contract["scorecard"]["sha256"]
    criterion_status = (
        "SCORECARD_DEFINED"
        if contract["quality_qualification"]["current_status"] == "SCORECARD_DEFINED"
        else "UNRATIFIED"
    )
    if set(modes) != registered_quality_modes:
        return {
            "source_manifest": source_manifest,
            "status": "UNMEASURED",
            "reason": (
                "quality manifest must account for the Strehl 16-worker "
                "denominator and every registered comparator mode"
            ),
            "qualified_modes": [],
            "qualified_modes_by_cell": {
                cell_id: [] for cell_id in sorted(required_cells)
            },
            "strehl_qualified_by_cell": {
                cell_id: False for cell_id in sorted(required_cells)
            },
            "mode_results": {},
        }
    availability_by_mode = {
        mode_id: modes[mode_id].get("availability")
        for mode_id in sorted(registered_quality_modes)
    }
    unavailable_optional_modes = {
        mode_id: modes[mode_id].get("unavailable_reason")
        for mode_id in sorted(OPTIONAL_COMPARATOR_MODES)
        if availability_by_mode[mode_id] == "UNAVAILABLE"
    }
    availability_valid = (
        all(
            availability_by_mode[mode_id] == "AVAILABLE"
            for mode_id in REQUIRED_COMPARATOR_MODES | {STREHL_QUALITY_MODE_ID}
        )
        and all(
            availability_by_mode[mode_id] in {"AVAILABLE", "UNAVAILABLE"}
            for mode_id in OPTIONAL_COMPARATOR_MODES
        )
        and all(
            isinstance(reason, str) and bool(reason.strip())
            for reason in unavailable_optional_modes.values()
        )
    )
    if not availability_valid:
        return {
            "source_manifest": source_manifest,
            "status": "UNMEASURED",
            "reason": (
                "the Strehl denominator and required comparators must be AVAILABLE; "
                "each optional Helicon mode must be AVAILABLE or record a non-empty "
                "UNAVAILABLE reason"
            ),
            "availability_by_mode": availability_by_mode,
            "unavailable_optional_modes": unavailable_optional_modes,
            "qualified_modes": [],
            "qualified_modes_by_cell": {
                cell_id: [] for cell_id in sorted(required_cells)
            },
            "strehl_qualified_by_cell": {
                cell_id: False for cell_id in sorted(required_cells)
            },
            "mode_results": {},
        }
    available_modes = {
        mode_id
        for mode_id, availability in availability_by_mode.items()
        if availability == "AVAILABLE"
    }
    results: dict[str, Any] = {}
    qualified_by_cell: dict[str, list[str]] = {
        cell_id: [] for cell_id in sorted(required_cells)
    }
    decision_by_cell: dict[str, dict[str, str]] = {
        cell_id: {} for cell_id in sorted(required_cells)
    }
    for mode_id in sorted(modes):
        mode = dict(modes[mode_id])
        if mode_id not in available_modes:
            for cell_id in sorted(required_cells):
                decision_by_cell[cell_id][mode_id] = "UNAVAILABLE"
            results[mode_id] = {
                "availability": "UNAVAILABLE",
                "unavailable_reason": mode.get("unavailable_reason"),
                "cell_results": {},
                "all_required_cells_present": True,
            }
            continue
        cell_results = {}
        try:
            mode_executable_bindings = executable_artifact_guard(
                mode,
                uncached=uncached_executables,
            )
            mode_executable_bundle_sha256 = executable_bundle_sha256(
                mode_executable_bindings
            )
            mode_executable_bundle_valid = (
                mode.get("executable_bundle_sha256") == mode_executable_bundle_sha256
            )
        except (KeyError, OSError, TypeError, ValueError):
            mode_executable_bundle_sha256 = None
            mode_executable_bundle_valid = False
        corpus_fingerprint = {
            "measured_commit": mode.get("measured_commit"),
            "binary_sha256": mode.get("binary_sha256"),
            "executable_bundle_sha256": mode_executable_bundle_sha256,
            "settings_sha256": mode.get("settings_sha256"),
            "output_contract_sha256": mode.get("output_contract_sha256"),
        }
        try:
            corpus_evidence, corpus_binding = load_bound_json(
                mode["quality_corpus_artifact"]
            )
            corpus_evidence_valid, corpus_evidence = quality_corpus_evidence_valid(
                corpus_evidence,
                evidence_path=repository_path(mode["quality_corpus_artifact"]["path"]),
                mode_id=mode_id,
                fingerprint=corpus_fingerprint,
                scorecard_sha256=scorecard_sha256,
            )
            require_guard(
                "G04-artifact-binding",
                {"artifacts": [corpus_binding]},
            )
        except (
            FileNotFoundError,
            KeyError,
            TypeError,
            ValueError,
            subprocess.SubprocessError,
        ):
            corpus_binding = None
            corpus_evidence = {}
            corpus_evidence_valid = False
        corpus_result = corpus_evidence.get("result", {})
        corpus_gates = corpus_result.get("quality_gates", {})
        corpus_m1 = corpus_result.get("replacement_m1", {})
        corpus_m4 = corpus_result.get("retained_m4", {})
        corpus_pass = (
            corpus_evidence_valid
            and corpus_evidence.get("verdict") == "PASS"
            and corpus_result.get("common_input_transfer_geometry") == "PASS"
            and set(corpus_gates) == set(REQUIRED_QUALITY_GATES)
            and all(corpus_gates.get(axis) == "PASS" for axis in REQUIRED_QUALITY_GATES)
        )
        cell_qualifications = mode.get("cell_qualifications", {})
        for capture, count in QUALITY_CELLS:
            cell_id = quality_cell_id(capture, count)
            capture_evidence = cell_qualifications.get(cell_id, {})
            expected_cell_fields = {
                "capture_id",
                "count",
                "input_manifest_sha256",
                "output_sha256",
                "pixel_sha256",
                "transfer_artifact",
                "geometry_artifact",
                "axis_artifacts",
            }
            cell_declaration_valid = (
                set(capture_evidence) == expected_cell_fields
                and capture_evidence.get("capture_id") == capture
                and capture_evidence.get("count") == count
            )
            fingerprint = {
                "measured_commit": mode.get("measured_commit"),
                "binary_sha256": mode.get("binary_sha256"),
                "executable_bundle_sha256": mode_executable_bundle_sha256,
                "settings_sha256": mode.get("settings_sha256"),
                "input_manifest_sha256": capture_evidence.get("input_manifest_sha256"),
                "output_contract_sha256": mode.get("output_contract_sha256"),
                "output_sha256": capture_evidence.get("output_sha256"),
                "pixel_sha256": capture_evidence.get("pixel_sha256"),
                "count": count,
            }
            artifact_rows = []
            evidence_rows: dict[str, dict[str, Any] | None] = {}
            evidence_paths: dict[str, Path | None] = {}
            references = {
                "transfer": capture_evidence.get("transfer_artifact"),
                "geometry": capture_evidence.get("geometry_artifact"),
                **{
                    axis: capture_evidence.get("axis_artifacts", {}).get(axis)
                    for axis in REQUIRED_QUALITY_GATES
                },
            }
            for evidence_id, reference in references.items():
                try:
                    evidence, binding = load_bound_json(reference)
                    artifact_rows.append(binding)
                    evidence_rows[evidence_id] = evidence
                    evidence_paths[evidence_id] = repository_path(reference["path"])
                except (FileNotFoundError, KeyError, TypeError, ValueError):
                    artifact_rows.append(
                        {
                            "path": str(
                                reference.get("path", "")
                                if isinstance(reference, dict)
                                else ""
                            ),
                            "expected_sha256": (
                                reference.get("sha256")
                                if isinstance(reference, dict)
                                else None
                            ),
                            "actual_sha256": None,
                            "verified": False,
                        }
                    )
                    evidence_rows[evidence_id] = None
                    evidence_paths[evidence_id] = None
            artifact_result = evaluate_guard(
                "G04-artifact-binding",
                {"artifacts": artifact_rows},
            )
            transfer = evidence_rows.get("transfer")
            geometry = evidence_rows.get("geometry")
            axis_valid = {
                axis: (
                    evidence_rows.get(axis) is not None
                    and quality_evidence_valid(
                        evidence_rows[axis],
                        evidence_path=evidence_paths[axis],
                        schema="m153-quality-axis-evidence-v1",
                        capture_id=capture,
                        count=count,
                        mode_id=mode_id,
                        axis=axis,
                        fingerprint=fingerprint,
                        scorecard_sha256=scorecard_sha256,
                    )
                )
                for axis in REQUIRED_QUALITY_GATES
            }
            transfer_valid = transfer is not None and quality_evidence_valid(
                transfer,
                evidence_path=evidence_paths["transfer"],
                schema="m153-transfer-evidence-v1",
                capture_id=capture,
                count=count,
                mode_id=mode_id,
                axis=None,
                fingerprint=fingerprint,
                scorecard_sha256=scorecard_sha256,
            )
            geometry_valid = geometry is not None and quality_evidence_valid(
                geometry,
                evidence_path=evidence_paths["geometry"],
                schema="m153-geometry-evidence-v1",
                capture_id=capture,
                count=count,
                mode_id=mode_id,
                axis=None,
                fingerprint=fingerprint,
                scorecard_sha256=scorecard_sha256,
            )
            axis_passes = {
                axis: axis_valid[axis] and evidence_rows[axis].get("verdict") == "PASS"
                for axis in REQUIRED_QUALITY_GATES
            }
            transfer_pass = transfer_valid and transfer.get("verdict") == "PASS"
            geometry_pass = geometry_valid and geometry.get("verdict") == "PASS"
            evidence_complete = (
                cell_declaration_valid
                and mode_executable_bundle_valid
                and artifact_result.passed
                and transfer_valid
                and geometry_valid
                and corpus_pass
                and all(axis_valid.values())
            )
            decision_status = (
                "QUALITY_QUALIFIED"
                if evidence_complete
                and transfer_pass
                and geometry_pass
                and all(axis_passes.values())
                else "QUALITY_FAILED"
                if evidence_complete
                else "UNMEASURED"
            )
            qualification = {
                **fingerprint,
                "mode_id": mode_id,
                "capture_id": capture,
                "count": count,
                "status": decision_status,
                "criterion_id": QUALITY_CRITERION_ID,
                "criterion_status": criterion_status,
                "input_output_transfer": "PASS" if transfer_pass else "UNMEASURED",
                "geometry_and_site_retention": (
                    "PASS" if geometry_pass else "UNMEASURED"
                ),
                "quality_gates": {
                    axis: "PASS" if passed else "UNMEASURED"
                    for axis, passed in axis_passes.items()
                },
                "replacement_m1": {
                    "instrument_status": corpus_m1.get("instrument_status"),
                    "decision": corpus_m1.get("decision"),
                    "artifact_sha256": (
                        mode["quality_corpus_artifact"].get("sha256")
                        if isinstance(mode.get("quality_corpus_artifact"), dict)
                        else None
                    ),
                },
                "retained_flat_power": {
                    **corpus_m4,
                    "artifact_sha256": (
                        mode["quality_corpus_artifact"].get("sha256")
                        if isinstance(mode.get("quality_corpus_artifact"), dict)
                        else None
                    ),
                },
                "evidence_output_sha256": {
                    evidence_id: evidence_rows[evidence_id].get("output_sha256")
                    for evidence_id in references
                    if evidence_rows[evidence_id] is not None
                },
                "evidence_pixel_sha256": {
                    evidence_id: evidence_rows[evidence_id].get("pixel_sha256")
                    for evidence_id in references
                    if evidence_rows[evidence_id] is not None
                },
                "bound_artifacts_verified": artifact_result.passed,
                "quality_corpus_verified": corpus_pass,
            }
            quality_result = evaluate_guard(
                "G05-quality-qualified",
                qualification,
            )
            cell_results[cell_id] = {
                "artifact_binding": artifact_result.to_json(),
                "quality": quality_result.to_json(),
                "decision_status": decision_status,
                "evidence_complete": evidence_complete,
                "count": count,
                "output_sha256": fingerprint["output_sha256"],
                "pixel_sha256": fingerprint["pixel_sha256"],
            }
            decision_by_cell[cell_id][mode_id] = decision_status
            if artifact_result.passed and quality_result.passed:
                qualified_by_cell[cell_id].append(mode_id)
        results[mode_id] = {
            "availability": "AVAILABLE",
            "executable_bundle_sha256": mode_executable_bundle_sha256,
            "executable_bundle_valid": mode_executable_bundle_valid,
            "quality_corpus_verified": corpus_pass,
            "quality_corpus_artifact": corpus_binding,
            "cell_results": cell_results,
            "all_required_cells_present": (set(cell_qualifications) == required_cells),
        }
    comparator_qualified_by_cell = {
        cell_id: sorted(set(values) & REGISTERED_COMPARATOR_MODES)
        for cell_id, values in qualified_by_cell.items()
    }
    strehl_qualified_by_cell = {
        cell_id: STREHL_QUALITY_MODE_ID in values
        for cell_id, values in qualified_by_cell.items()
    }
    qualified = sorted(
        set.intersection(
            *(set(values) for values in comparator_qualified_by_cell.values())
        )
    )
    envelope_complete_by_cell = {
        cell_id: quality_envelope_complete_for_cell(
            decisions=decisions,
            available_modes=available_modes,
            qualified_comparator_modes=set(comparator_qualified_by_cell[cell_id]),
            strehl_qualified=strehl_qualified_by_cell[cell_id],
        )
        for cell_id, decisions in decision_by_cell.items()
    }
    envelope_complete = all(envelope_complete_by_cell.values())
    return {
        "source_manifest": source_manifest,
        "status": "PASS" if envelope_complete else "UNMEASURED",
        "reason": (
            None
            if envelope_complete
            else "the required per-capture quality modes did not all qualify or the optional-mode availability envelope is incomplete"
        ),
        "criterion_id": QUALITY_CRITERION_ID,
        "required_modes": sorted(REQUIRED_COMPARATOR_MODES),
        "required_strehl_mode": STREHL_QUALITY_MODE_ID,
        "optional_modes": sorted(OPTIONAL_COMPARATOR_MODES),
        "availability_by_mode": availability_by_mode,
        "unavailable_optional_modes": unavailable_optional_modes,
        "qualified_modes": qualified,
        "qualified_modes_by_cell": comparator_qualified_by_cell,
        "strehl_qualified_by_cell": strehl_qualified_by_cell,
        "decision_by_cell": decision_by_cell,
        "envelope_complete_by_cell": envelope_complete_by_cell,
        "mode_results": results,
    }


def host_load_sample(seconds: float) -> dict[str, Any]:
    frequency = qpc_frequency()
    started_qpc_ticks = qpc_ticks()
    start = system_times()
    time.sleep(seconds)
    end = system_times()
    finalized_qpc_ticks = qpc_ticks()
    elapsed = (finalized_qpc_ticks - started_qpc_ticks) / frequency
    total = end["total_100ns"] - start["total_100ns"]
    busy = end["busy_100ns"] - start["busy_100ns"]
    return {
        "requested_seconds": seconds,
        "elapsed_seconds": elapsed,
        "qpc_frequency": frequency,
        "started_qpc_ticks": started_qpc_ticks,
        "finalized_qpc_ticks": finalized_qpc_ticks,
        "busy_fraction": busy / total if total > 0 else None,
    }


def host_preflight(
    seconds: float,
    hardware_probe: dict[str, Any],
) -> dict[str, Any]:
    sampler = GpuSampler(hardware_probe)
    sampler.start()
    try:
        sampler.wait_ready()
        cpu = host_load_sample(seconds)
    finally:
        sampler.stop()
    frequency = int(cpu["qpc_frequency"])
    started = int(cpu["started_qpc_ticks"])
    finalized = int(cpu["finalized_qpc_ticks"])
    samples = [
        sample
        for sample in sampler.samples
        if started <= int(sample["qpc_ticks"]) <= finalized
    ]
    illegal_gpu = unapproved_gpu_processes(
        samples,
        hardware_probe.get("os_display_process_allowlist", []),
        set(),
    )
    expected_minimum_samples = max(1, math.floor(cpu["elapsed_seconds"] / 0.010) - 1)
    tolerance = math.ceil(frequency * 0.015)
    sample_ticks = [int(sample["qpc_ticks"]) for sample in samples]
    temporal_coverage = (
        bool(sample_ticks)
        and sample_ticks == sorted(sample_ticks)
        and all(int(sample["qpc_frequency"]) == frequency for sample in samples)
        and sample_ticks[0] <= started + tolerance
        and sample_ticks[-1] >= finalized - tolerance
        and all(
            later - earlier <= tolerance
            for earlier, later in zip(sample_ticks, sample_ticks[1:])
        )
    )
    return {
        **cpu,
        "sample_interval_ms": 10,
        "hardware_samples": samples,
        "hardware_sample_count": len(samples),
        "minimum_required_hardware_samples": expected_minimum_samples,
        "hardware_sample_coverage_pass": (
            hardware_probe.get("kind") == "synthetic-zero"
            or (len(samples) >= expected_minimum_samples and temporal_coverage)
        ),
        "hardware_errors": sampler.errors,
        "hardware_throttle_observed": any(
            sample["hardware_throttle"] for sample in samples
        ),
        "unapproved_gpu_processes": illegal_gpu,
        "gpu_process_allowlist_pass": not illegal_gpu,
    }


def active_power_plan() -> str:
    result = subprocess.run(
        ["powercfg", "/getactivescheme"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    return result.stdout.strip()


def thermal_reading(config: dict[str, Any]) -> float:
    argv = [str(token) for token in config.get("argv", [])]
    if not argv:
        raise ValueError("a bound thermal probe command is required")
    result = subprocess.run(
        argv,
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=float(config.get("timeout_seconds", 5.0)),
    )
    match = re.search(r"-?[0-9]+(?:\.[0-9]+)?", result.stdout)
    if match is None:
        raise ValueError("thermal probe emitted no numeric temperature")
    return float(match.group(0))


def validate_host_instruments(campaign: dict[str, Any]) -> dict[str, Any]:
    artifacts = []
    for name in ("thermal_probe", "gpu_probe"):
        probe = campaign["host"][name]
        if probe.get("kind") != "command":
            raise ValueError(f"real campaign {name} must be a bound command")
        binding = read_artifact_binding(
            repository_path(probe["path"]),
            probe["sha256"],
        )
        artifacts.append(binding)
        argv = [str(token) for token in probe.get("argv", [])]
        argv = canonicalize_command_file_arguments(argv, cwd=ROOT)
        if not argv or repository_path(argv[0]).resolve(strict=True) != repository_path(
            probe["path"]
        ).resolve(strict=True):
            raise ValueError(f"{name} command does not launch its bound artifact")
        require_bound_command_files(
            argv,
            {Path(binding["path"]).resolve(strict=True)},
            cwd=ROOT,
        )
        probe["argv"] = argv
        probe["cwd"] = str(ROOT.resolve(strict=True))
    gpu_probe = campaign["host"]["gpu_probe"]
    if (
        gpu_probe.get("output_protocol") != "persistent-json-lines-v1"
        or not math.isclose(
            float(gpu_probe.get("interval_seconds", math.nan)),
            0.010,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or not isinstance(gpu_probe.get("os_display_process_allowlist"), list)
    ):
        raise ValueError(
            "GPU/thermal/throttle process probe must sample at exactly 10 ms "
            "and declare its OS-display-process allowlist"
        )
    for allowed in gpu_probe["os_display_process_allowlist"]:
        if not isinstance(allowed, dict) or allowed.get("role") != "OS_DISPLAY_PROCESS":
            raise ValueError("GPU allowlist may contain only OS display processes")
        binding = read_artifact_binding(
            repository_path(allowed["image_path"]),
            allowed["sha256"],
        )
        artifacts.append(binding)
    observer, observer_binding = load_bound_json(
        campaign["conditions"]["observer_hash_control"]
    )
    artifacts.append(observer_binding)
    require_guard("G04-artifact-binding", {"artifacts": artifacts})
    if (
        observer.get("schema") != "m153-observer-hash-control-v1"
        or observer.get("status") != "PASS"
        or observer.get("observer_on_output_sha256")
        != observer.get("observer_off_output_sha256")
        or observer.get("observer_on_pixel_sha256")
        != observer.get("observer_off_pixel_sha256")
    ):
        raise ValueError("observer-on/off output hash control did not pass")
    return {
        "artifact_bindings": artifacts,
        "observer_hash_control": observer,
    }


def validate_live_registration(campaign: dict[str, Any]) -> dict[str, Any]:
    registration, binding = load_bound_json(campaign["live_replay_registration"])
    contract = load_contract()
    if (
        contract.get("live_replay", {}).get("status") != "RATIFIED"
        or registration.get("schema") != "m153-live-replay-registration-v1"
        or registration.get("status") != "RATIFIED"
        or not registration.get("approved_by")
        or not registration.get("approved_utc")
        or registration.get("contract_sha256") != sha256_file(CONTRACT_PATH)
        or registration.get("protocol_sha256") != object_sha256(contract["live_replay"])
    ):
        raise ValueError("live replay protocol is not ratified and hash-bound")
    return binding


def validate_signed_acquisition_trace(
    reference: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trace_path = repository_path(reference["path"])
    trace, trace_binding = load_bound_json(reference)
    payload = {
        key: value for key, value in trace.items() if key != "commission_artifact"
    }
    commission, commission_binding = load_bound_json(trace["commission_artifact"])
    checker_result, checker_bindings = run_commissioned_checker(
        artifact_path=trace_path,
        payload_sha256=object_sha256(payload),
        checker_artifact=trace["checker_artifact"],
        checker_support_artifacts=trace.get("checker_support_artifacts", []),
        commission=commission,
    )
    frames = trace.get("frames", [])
    offsets = [
        (
            float(frame.get("shutter_close_offset_seconds", math.nan)),
            float(frame.get("file_available_offset_seconds", math.nan)),
        )
        for frame in frames
    ]
    if (
        trace.get("schema") != "m153-signed-acquisition-trace-v1"
        or trace.get("evidence_tag") != "MEASURED"
        or trace.get("verdict") != "PASS"
        or trace.get("capture_id") != "bee-1-cpl"
        or trace.get("count") != 100
        or len(frames) != 100
        or [str(frame.get("name", "")).upper() for frame in frames]
        != expected_capture_names("bee-1-cpl", 100)
        or not all(
            math.isfinite(shutter) and math.isfinite(available) and available >= shutter
            for shutter, available in offsets
        )
        or offsets[0][0] != 0.0
        or any(
            later[0] < earlier[0] or later[1] < earlier[1]
            for earlier, later in zip(offsets, offsets[1:])
        )
        or not isinstance(trace.get("owner_signature"), dict)
        or not trace["owner_signature"].get("signer")
        or not trace["owner_signature"].get("algorithm")
        or not trace["owner_signature"].get("signature")
        or commission.get("schema")
        != "m153-acquisition-signature-checker-commission-v1"
        or commission.get("status") != "PASS"
        or commission.get("checker_sha256") != checker_bindings[0]["actual_sha256"]
        or commission.get("checker_bundle_sha256")
        != checker_result["checker_bundle_sha256"]
        or not checker_bundle_approved(
            "acquisition_trace",
            checker_result["checker_bundle_sha256"],
        )
        or commission.get("scorecard_sha256") != load_contract()["scorecard"]["sha256"]
        or commission.get("accepted_evidence_payload_sha256") != object_sha256(payload)
        or checker_result.get("verdict") != "PASS"
    ):
        raise ValueError("live acquisition trace is not signed and commissioned")
    return trace, [trace_binding, commission_binding, *checker_bindings]


def validate_frozen_campaign(
    campaign: dict[str, Any],
    *,
    uncached_executables: bool = False,
) -> None:
    if (
        campaign.get("schema") != "m153-m11-campaign-v1"
        or campaign.get("status") != "FROZEN"
        or campaign.get("baseline_frozen_before_candidate") is not True
        or campaign.get("host", {}).get("dedicated") is not True
        or campaign.get("host", {}).get("m139_released") is not True
        or not campaign.get("host", {}).get("power_plan")
    ):
        raise ValueError("campaign/host is not frozen and released for measurement")
    start_interval = campaign.get("conditions", {}).get("start_temperature_interval_c")
    if (
        not math.isclose(
            float(campaign.get("conditions", {}).get("preload_sample_seconds", 0.0)),
            60.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or not isinstance(start_interval, list)
        or len(start_interval) != 2
        or not all(isinstance(value, (int, float)) for value in start_interval)
        or not all(math.isfinite(float(value)) for value in start_interval)
        or float(start_interval[0]) > float(start_interval[1])
    ):
        raise ValueError(
            "campaign must freeze a 60-second preflight and start-temperature interval"
        )
    expected_cache_states = {
        "comparative-warm": "WARM",
        "comparative-cold": "COLD_RESET",
        "product-warm": "WARM",
        "product-cold": "COLD_RESET",
        "live": "WARM",
    }
    segments = campaign.get("segments", {})
    if set(segments) != set(expected_cache_states) or any(
        segments[name].get("cache_state") != cache_state
        for name, cache_state in expected_cache_states.items()
    ):
        raise ValueError("campaign segment names/cache states do not match M11")
    measured_commit = campaign.get("measured_commit")
    if (
        not isinstance(measured_commit, str)
        or len(measured_commit) not in {40, 64}
        or any(
            character not in "0123456789abcdefABCDEF" for character in measured_commit
        )
    ):
        raise ValueError("campaign measured_commit is not a full commit hash")
    baseline_ids = [
        setting_id
        for setting_id, setting in campaign.get("settings", {}).items()
        if setting.get("role") == "frozen-default-baseline"
    ]
    if len(baseline_ids) != 1:
        raise ValueError("campaign must register exactly one frozen default baseline")
    baseline = campaign["settings"][baseline_ids[0]]
    frozen = campaign.get("frozen_baseline", {})
    if (
        frozen.get("binary_path") != baseline.get("binary_path")
        or baseline.get("arm") != "product"
        or frozen.get("binary_sha256") != baseline.get("binary_sha256")
        or frozen.get("settings_sha256") != baseline.get("settings_sha256")
        or frozen.get("settings_payload") != baseline.get("settings_payload")
    ):
        raise ValueError("frozen baseline declaration does not match its setting")
    candidate_roles = (
        "strehl-common",
        "candidate-cpu",
        "candidate-hybrid",
        "candidate-live",
    )
    by_role = {
        role: [
            setting
            for setting in campaign.get("settings", {}).values()
            if setting.get("role") == role
        ]
        for role in candidate_roles
    }
    if (
        len(by_role["strehl-common"]) != len(WORKER_LADDER)
        or {int(setting.get("workers", -1)) for setting in by_role["strehl-common"]}
        != set(WORKER_LADDER)
        or len(by_role["candidate-cpu"]) != 1
        or int(by_role["candidate-cpu"][0].get("workers", -1)) != 16
        or len(by_role["candidate-hybrid"]) != 1
        or len(by_role["candidate-live"]) != 1
        or {
            setting.get("mode_id")
            for setting in by_role["strehl-common"]
            if int(setting.get("workers", -1)) == 16
        }
        != {STREHL_QUALITY_MODE_ID}
        or len(
            {
                setting.get("binary_sha256")
                for rows in by_role.values()
                for setting in rows
            }
        )
        != 1
    ):
        raise ValueError(
            "common-merge worker ladder and product CPU-16, hybrid, and live arms "
            "must use one candidate build"
        )
    candidate_bundles = {
        executable_bundle_sha256(
            executable_artifact_guard(
                setting,
                uncached=uncached_executables,
            )
        )
        for rows in by_role.values()
        for setting in rows
    }
    if len(candidate_bundles) != 1:
        raise ValueError(
            "comparative, product, hybrid, and live arms must use one complete "
            "candidate executable bundle"
        )
    if (
        len(
            {
                object_sha256(worker_ladder_signature(setting))
                for setting in by_role["strehl-common"]
            }
        )
        != 1
    ):
        raise ValueError(
            "common-merge worker-ladder settings may differ only in worker count"
        )
    if by_role["strehl-common"][0].get("arm") != "comparative" or any(
        setting.get("arm") != "product"
        for role in ("candidate-cpu", "candidate-hybrid", "candidate-live")
        for setting in by_role[role]
    ):
        raise ValueError("candidate roles are assigned to the wrong M11 arm")


def current_windows_boot_id() -> str:
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        (
            r"SYSTEM\CurrentControlSet\Control\Session Manager"
            r"\Memory Management\PrefetchParameters"
        ),
    ) as key:
        return str(winreg.QueryValueEx(key, "BootId")[0])


def reset_cold_cache(
    *,
    provider: dict[str, Any],
    position_key: str,
    campaign_sha256: str,
    previously_used_boot_ids: set[str],
) -> dict[str, Any]:
    provider_path = repository_path(provider["path"])
    provider_binding = read_artifact_binding(
        provider_path,
        provider["sha256"],
    )
    require_guard("G04-artifact-binding", {"artifacts": [provider_binding]})
    values = {
        "position_key": position_key,
        "campaign_sha256": campaign_sha256,
    }
    argv = expand_argv(provider["argv"], values, cwd=ROOT)
    argv = canonicalize_command_file_arguments(argv, cwd=ROOT)
    launched_provider = Path(argv[0])
    if not launched_provider.is_absolute():
        launched_provider = ROOT / launched_provider
    if launched_provider.resolve(strict=True) != provider_path.resolve(strict=True):
        raise ValueError("cold-reset command does not launch its bound provider")
    require_bound_command_files(
        argv,
        {provider_path.resolve(strict=True)},
        cwd=ROOT,
    )
    result = subprocess.run(
        argv,
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=float(provider.get("timeout_seconds", 120.0)),
    )
    receipt = strict_json_loads(result.stdout)
    if receipt.get("provider_sha256") != provider_binding["actual_sha256"]:
        raise ValueError("cold-reset receipt does not identify its bound provider")
    receipt_sha256 = object_sha256(receipt)
    current_boot_id = current_windows_boot_id()
    require_guard(
        "G15-cold-receipt",
        {
            "receipt": receipt,
            "receipt_sha256": receipt_sha256,
            "previously_used_boot_ids": sorted(previously_used_boot_ids),
            "current_windows_boot_id": current_boot_id,
            "position_key": position_key,
            "campaign_sha256": campaign_sha256,
        },
    )
    previously_used_boot_ids.add(str(receipt["windows_boot_id"]))
    return {
        "receipt": receipt,
        "receipt_sha256": receipt_sha256,
        "windows_boot_id": current_boot_id,
        "provider": provider_binding,
        "position_key": position_key,
        "campaign_sha256": campaign_sha256,
    }


def clean_child_environment(
    fixed: dict[str, Any], private: dict[str, Path]
) -> tuple[dict[str, str], dict[str, str | None]]:
    env = os.environ.copy()
    prefixes = ("STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
    for name in list(env):
        if name.startswith(prefixes):
            env.pop(name, None)
    for name, value in fixed.items():
        env[str(name)] = str(value)
    env["TEMP"] = str(private["temp"])
    env["TMP"] = str(private["temp"])
    env["STREHL_CACHE_DIR"] = str(private["cache"])
    env["STREHL_WARPMAP"] = str(private["warpmap"])
    declared_names = set(fixed) | {
        "TEMP",
        "TMP",
        "STREHL_CACHE_DIR",
        "STREHL_WARPMAP",
        "RAYON_NUM_THREADS",
        "STREHL_PYRAMID_WORKERS",
    }
    declared = {name: env.get(name) for name in sorted(declared_names)}
    return env, declared


def expand_argv(
    tokens: list[Any],
    values: dict[str, Any],
    *,
    cwd: Path = ROOT,
) -> list[str]:
    expanded = [str(token).format_map(values) for token in tokens]
    if not expanded:
        raise ValueError("command template expanded to an empty argv")
    executable = Path(expanded[0])
    if not executable.is_absolute():
        executable = cwd.resolve(strict=True) / executable
    expanded[0] = str(executable.resolve(strict=True))
    return expanded


def validate_authorization(
    campaign_path: Path,
    campaign: dict[str, Any],
    authorization_path: Path,
) -> dict[str, Any]:
    contract = load_contract()
    authorization = read_json(authorization_path)
    if authorization.get("schema") != "m153-real-run-authorization-v1":
        raise ValueError("unsupported real-run authorization schema")
    commission_path = repository_path(authorization["commission"]["path"])
    commission = read_json(commission_path)
    commission_binding = read_artifact_binding(
        commission_path,
        authorization["commission"]["artifact_sha256"],
    )
    require_guard(
        "G04-artifact-binding",
        {"artifacts": [commission_binding]},
    )
    if not isinstance(authorization.get("build_audit"), dict):
        raise ValueError("real-run authorization is missing its build audit")
    audit, audit_binding = load_bound_json(authorization["build_audit"])
    if (
        not commission_source_bindings_current(commission.get("source_bindings", {}))
        or not commission_runtime_binding_current(commission)
        or audit.get("schema") != "m153-build-audit-v1"
        or audit.get("status") != "PASS"
        or audit.get("source_bindings_pass") is not True
        or audit.get("census_internal_checks_pass") is not True
        or audit.get("guard_count") != len(GUARD_REGISTRY)
        or audit.get("guard_ids") != sorted(GUARD_REGISTRY)
        or audit.get("contract", {}).get("sha256") != sha256_file(CONTRACT_PATH)
        or audit.get("formal_m11_verdict") != "UNMEASURED"
    ):
        raise ValueError("formal commission or build audit is stale/incomplete")
    actual_contract_sha256 = sha256_file(CONTRACT_PATH)
    actual_campaign_sha256 = sha256_file(campaign_path)
    payload = {
        "real_run_requested": authorization.get("real_run_requested"),
        "authorized_by": authorization.get("authorized_by"),
        "m139_host_release": authorization.get("m139_host_release"),
        "authorized_contract_sha256": authorization.get("contract_sha256"),
        "actual_contract_sha256": actual_contract_sha256,
        "authorized_campaign_sha256": authorization.get("campaign_sha256"),
        "actual_campaign_sha256": actual_campaign_sha256,
        "contract_allows_real_run": contract.get("real_run_authorized"),
        "commission": {
            **commission,
            "artifact_sha256": commission_binding["actual_sha256"],
        },
        "build_audit": {
            **audit,
            "artifact_sha256": audit_binding["actual_sha256"],
        },
    }
    require_guard("G18-commissioning-required", payload)
    if campaign.get("status") != "FROZEN":
        raise ValueError("campaign must have status FROZEN")
    if campaign.get("contract", {}).get("sha256") != actual_contract_sha256:
        raise ValueError("campaign is not bound to the current M153 contract")
    return authorization


def executable_artifact_guard(
    declaration: dict[str, Any],
    *,
    uncached: bool = False,
) -> list[dict[str, Any]]:
    references = declaration.get("executable_artifacts")
    if not isinstance(references, list) or not references:
        raise ValueError("executable_artifacts must explicitly bind the complete build")
    artifacts = [
        read_artifact_binding(
            repository_path(artifact["path"]),
            artifact["sha256"],
            uncached=uncached,
        )
        for artifact in references
    ]
    require_guard("G04-artifact-binding", {"artifacts": artifacts})
    binary_path = repository_path(declaration["binary_path"]).resolve(strict=True)
    binary_bindings = [
        artifact
        for artifact in artifacts
        if Path(artifact["path"]).resolve(strict=True) == binary_path
    ]
    if (
        len(binary_bindings) != 1
        or binary_bindings[0]["actual_sha256"] != declaration["binary_sha256"]
    ):
        raise ValueError("binary declaration is not uniquely hash-bound")
    return artifacts


def executable_bundle_sha256(artifacts: list[dict[str, Any]]) -> str:
    return object_sha256(
        sorted(
            (
                {
                    "path": str(Path(artifact["path"]).resolve(strict=True)),
                    "sha256": artifact["actual_sha256"],
                }
                for artifact in artifacts
            ),
            key=lambda artifact: artifact["path"].casefold(),
        )
    )


def process_images_match_bound_artifacts(
    process_tree: dict[str, Any],
    bound_artifacts: list[dict[str, Any]],
) -> bool:
    try:
        allowed = {
            str(Path(row["path"]).resolve(strict=True)).casefold(): row.get(
                "sha256",
                row.get("actual_sha256"),
            )
            for row in bound_artifacts
        }
        observed = process_tree["process_lifetimes"]
        return bool(observed) and all(
            allowed.get(str(Path(row["image_path"]).resolve(strict=True)).casefold())
            == row["image_sha256"]
            for row in observed
        )
    except (KeyError, OSError, TypeError, ValueError):
        return False


def setting_artifact_guard(
    setting: dict[str, Any],
    *,
    uncached: bool = False,
) -> list[dict[str, Any]]:
    artifacts = executable_artifact_guard(setting, uncached=uncached)
    binary_path = repository_path(setting["binary_path"]).resolve(strict=True)
    template = (
        setting.get("live_replay", {}).get("stacker_argv", [])
        if setting.get("live_replay")
        else setting.get("argv", [])
    )
    if not template:
        raise ValueError(f"{setting['mode_id']} has no command template")
    command_cwd = repository_path(
        (
            setting.get("live_replay", {}).get("stacker_cwd", ROOT)
            if setting.get("live_replay")
            else setting.get("cwd", ROOT)
        )
    ).resolve(strict=True)
    executable = Path(str(template[0]))
    if not executable.is_absolute():
        executable = command_cwd / executable
    executable = executable.resolve(strict=True)
    if executable != binary_path:
        raise ValueError(
            f"{setting['mode_id']} command does not launch its frozen binary"
        )
    require_bound_command_files(
        template,
        {Path(artifact["path"]).resolve(strict=True) for artifact in artifacts},
        cwd=command_cwd,
    )
    serialized = "\0".join(str(token) for token in template)
    required_input_placeholder = (
        "{spool}" if setting.get("live_replay") else "{input_dir}"
    )
    if (
        required_input_placeholder not in serialized
        or "{output}" not in serialized
        or "{count}" not in serialized
    ):
        raise ValueError(
            f"{setting['mode_id']} command must bind input, count, and output placeholders"
        )
    if setting.get("live_replay") and (
        "{input_dir}" in serialized
        or "{run_root}" in serialized
        or any(
            "{input_dir}" in str(value) or "{run_root}" in str(value)
            for value in setting.get("environment", {}).values()
        )
    ):
        raise ValueError(
            f"{setting['mode_id']} exposes pre-availability live source paths"
        )
    if setting.get("role") in {
        "strehl-common",
        "candidate-cpu",
        "candidate-hybrid",
        "frozen-default-baseline",
    }:
        workers = int(setting.get("workers", -1))
        binding = setting.get("worker_binding", {})
        kind = binding.get("kind")
        worker_bound = False
        if kind == "argv":
            flag = str(binding.get("flag", ""))
            worker_bound = any(
                str(template[index]) == flag and str(template[index + 1]) == "{workers}"
                for index in range(len(template) - 1)
            )
        elif kind == "environment":
            name = binding.get("name")
            worker_bound = name in {
                "RAYON_NUM_THREADS",
                "STREHL_PYRAMID_WORKERS",
            } and str(setting.get("environment", {}).get(name)) == str(workers)
        if (
            workers < 1
            or (
                setting.get("role") in {"candidate-cpu", "frozen-default-baseline"}
                and workers != 16
            )
            or not worker_bound
        ):
            raise ValueError(
                f"{setting['mode_id']} does not operationally bind its worker count"
            )
    expected_settings = object_sha256(setting["settings_payload"])
    if setting["settings_sha256"] != expected_settings:
        raise ValueError(
            f"{setting['mode_id']} settings hash mismatch: "
            f"expected {expected_settings}, got {setting['settings_sha256']}"
        )
    if setting.get("arm") == "product":
        payload = setting["settings_payload"]
        if (
            payload.get("build") != setting["binary_sha256"]
            or not isinstance(payload.get("common"), dict)
            or not isinstance(payload.get("acceleration_mode"), str)
            or not payload["acceleration_mode"]
            or "{acceleration_mode}" not in serialized
        ):
            raise ValueError(
                f"{setting['mode_id']} product settings are not operationally bound"
            )
    return artifacts


def product_operational_signature(setting: dict[str, Any]) -> dict[str, Any]:
    template = (
        setting.get("live_replay", {}).get("stacker_argv", [])
        if setting.get("live_replay")
        else setting.get("argv", [])
    )
    return {
        "argv_after_executable": template[1:],
        "cwd": str(repository_path(setting.get("cwd", ROOT)).resolve(strict=False)),
        "environment": setting.get("environment", {}),
        "workers": int(setting.get("workers", 16)),
        "output_contract": setting.get("output_contract"),
        "required_stages": setting.get("required_stages"),
        "numeric_stage_timings_required": setting.get("numeric_stage_timings_required"),
    }


def worker_ladder_signature(setting: dict[str, Any]) -> dict[str, Any]:
    signature = json.loads(json.dumps(setting))
    signature.pop("mode_id", None)
    signature.pop("workers", None)
    environment = dict(signature.get("environment", {}))
    binding = signature.get("worker_binding", {})
    if binding.get("kind") == "environment":
        environment.pop(str(binding.get("name")), None)
    signature["environment"] = environment
    signature["cwd"] = str(
        repository_path(signature.get("cwd", ROOT)).resolve(strict=False)
    )
    return signature


def verify_staged_input(
    *,
    input_dir: Path,
    manifest: dict[str, Any],
    kind: str,
    uncached: bool = False,
) -> dict[str, Any]:
    resolved_dir = input_dir.resolve(strict=True)
    if not path_is_within(resolved_dir, LANE_ROOT):
        raise ValueError(
            f"staged input resolves outside the owned tree: {input_dir} -> "
            f"{resolved_dir}"
        )
    rows = manifest.get("files", [])
    if not rows:
        raise ValueError("input manifest has no files")
    names = [str(row.get("name", "")) for row in rows]
    if len(names) != len(set(name.casefold() for name in names)):
        raise ValueError("input manifest contains duplicate names")
    actual_volume_id = str(resolved_dir.stat().st_dev)
    if manifest.get("volume_id") != actual_volume_id:
        raise ValueError(
            "staged-input volume identity does not match the frozen manifest"
        )
    extensions = {".tif", ".tiff"} if kind == "common-tiff" else {".arw"}
    actual_names = sorted(
        (
            entry.name
            for entry in os.scandir(resolved_dir)
            if entry.is_file(follow_symlinks=False)
            and Path(entry.name).suffix.casefold() in extensions
        ),
        key=str.casefold,
    )
    if [name.casefold() for name in actual_names] != [
        name.casefold() for name in names
    ]:
        raise ValueError("staged files differ from the ordered input manifest")
    verified_rows = []
    for row in rows:
        path = resolved_dir / row["name"]
        resolved_file = path.resolve(strict=True)
        if not path_is_within(resolved_file, resolved_dir):
            raise ValueError(f"staged file escapes through a reparse point: {path}")
        actual_hash = (
            sha256_file_uncached(resolved_file)
            if uncached
            else sha256_file(resolved_file)
        )
        actual_bytes = resolved_file.stat().st_size
        if actual_hash != row.get("sha256") or actual_bytes != row.get("bytes"):
            raise ValueError(f"staged artifact changed after freeze: {path}")
        verified = {
            "name": row["name"],
            "sha256": actual_hash,
            "bytes": actual_bytes,
        }
        if kind == "common-tiff":
            if uncached:
                if not _hash_text(row.get("pixel_sha256")) or not isinstance(
                    row.get("image_description"), str
                ):
                    raise ValueError(
                        "cold common-TIFF manifest lacks its frozen pixel witness"
                    )
                verified["pixel_sha256"] = row["pixel_sha256"]
                verified["image_description"] = row["image_description"]
            else:
                witness = tiff_witness(
                    resolved_file,
                    manifest["image_contract"],
                )
                if not witness["tiff_valid"]:
                    raise ValueError(f"common TIFF violates input contract: {path}")
                if row.get("pixel_sha256") != witness["pixel_sha256"]:
                    raise ValueError(f"common TIFF pixel hash mismatch: {path}")
                verified["pixel_sha256"] = witness["pixel_sha256"]
                verified["image_description"] = witness["image_description"]
        verified_rows.append(verified)
    ordered_hash = object_sha256(
        [{"name": row["name"], "sha256": row["sha256"]} for row in verified_rows]
    )
    if ordered_hash != manifest.get("ordered_input_sha256"):
        raise ValueError("ordered staged-input hash does not match manifest")
    return {
        "kind": kind,
        "resolved_dir": str(resolved_dir),
        "files": verified_rows,
        "ordered_input_sha256": ordered_hash,
        "volume_id": actual_volume_id,
        "image_contract": manifest.get("image_contract"),
    }


def verify_cell_input_content(
    cell: dict[str, Any],
    *,
    segment_name: str,
    input_dir_override: Path | None = None,
    uncached: bool = False,
) -> str:
    manifest_path = repository_path(cell["input_manifest_path"])
    binding = read_artifact_binding(
        manifest_path,
        cell["input_manifest_sha256"],
    )
    require_guard("G04-artifact-binding", {"artifacts": [binding]})
    manifest = read_json(manifest_path)
    input_dir = (
        input_dir_override
        if input_dir_override is not None
        else repository_path(cell["input_dir"])
    ).resolve(strict=True)
    if not path_is_within(input_dir, LANE_ROOT):
        raise ValueError("per-run input verification escaped the owned staging tree")
    if str(input_dir.stat().st_dev) != manifest.get("volume_id"):
        raise ValueError("per-run input volume changed after campaign preflight")
    kind = "common-tiff" if segment_name.startswith("comparative") else "native-arw"
    extensions = {".tif", ".tiff"} if kind == "common-tiff" else {".arw"}
    rows = manifest.get("files", [])
    count = int(cell["count"])
    if count < 1 or len(rows) < count:
        raise ValueError("input manifest does not contain the timed prefix")
    actual_names = sorted(
        (
            entry.name
            for entry in os.scandir(input_dir)
            if entry.is_file(follow_symlinks=False)
            and Path(entry.name).suffix.casefold() in extensions
        ),
        key=str.casefold,
    )
    manifest_names = [str(row.get("name", "")) for row in rows[:count]]
    if [name.casefold() for name in actual_names] != [
        name.casefold() for name in manifest_names
    ]:
        raise ValueError("staged files changed after campaign preflight")
    verified_prefix = []
    for row in rows[:count]:
        path = (input_dir / row["name"]).resolve(strict=True)
        if not path_is_within(path, input_dir):
            raise ValueError("staged input escaped through a reparse point")
        actual_hash = sha256_file_uncached(path) if uncached else sha256_file(path)
        actual_bytes = path.stat().st_size
        if actual_hash != row.get("sha256") or actual_bytes != row.get("bytes"):
            raise ValueError(f"staged artifact changed after preflight: {path}")
        verified_prefix.append(
            {
                "name": row["name"],
                "sha256": actual_hash,
                "bytes": actual_bytes,
            }
        )
    return object_sha256(
        {
            "kind": kind,
            "count": count,
            "files": verified_prefix,
        }
    )


def create_invocation_input_snapshot(
    cell: dict[str, Any],
    destination: Path,
) -> tuple[Path, list[Path]]:
    source_dir = repository_path(cell["input_dir"]).resolve(strict=True)
    manifest = read_json(repository_path(cell["input_manifest_path"]))
    count = int(cell["count"])
    rows = manifest.get("files", [])
    if count < 1 or len(rows) < count:
        raise ValueError("input manifest does not contain the invocation prefix")
    destination = destination.resolve()
    require_guard(
        "G01-owned-output",
        {"path": str(destination), "lane_root": str(LANE_ROOT)},
    )
    destination.mkdir(parents=True, exist_ok=False)
    snapshot_paths = []
    for row in rows[:count]:
        source = (source_dir / row["name"]).resolve(strict=True)
        target = destination / row["name"]
        if not path_is_within(source, source_dir):
            raise ValueError("staged input escaped through a reparse point")
        os.link(source, target)
        snapshot_paths.append(target)
    return destination, snapshot_paths


def validate_input_provenance(
    *,
    manifest: dict[str, Any],
    staged: dict[str, Any],
    cell: dict[str, Any],
    kind: str,
    census_sha256: str,
) -> list[dict[str, Any]]:
    contract = load_contract()
    stack_id = str(cell["stack_id"])
    source_root = Path(contract["inputs"][stack_id]["source_path"]).resolve(strict=True)
    if (
        manifest.get("schema") != "m153-staged-input-manifest-v1"
        or manifest.get("contract_sha256") != sha256_file(CONTRACT_PATH)
        or manifest.get("census_sha256") != census_sha256
        or manifest.get("stack_id") != stack_id
        or Path(manifest.get("source_path", "")).resolve(strict=True) != source_root
    ):
        raise ValueError("input manifest is not bound to the registered capture")
    source_count = (
        int(contract["inputs"][stack_id]["frame_count"])
        if kind == "common-tiff"
        else int(cell["count"])
    )
    expected_sources = expected_capture_names(stack_id, source_count)
    rows = manifest["files"]
    if [str(row.get("source_name", "")).upper() for row in rows] != expected_sources:
        raise ValueError("input manifest source sequence is not the registered prefix")
    for row, staged_row in zip(rows, staged["files"]):
        source_path = Path(row["source_path"]).resolve(strict=True)
        expected_path = (source_root / row["source_name"]).resolve(strict=True)
        source_stat = source_path.stat()
        if (
            source_path != expected_path
            or source_stat.st_size != int(row["source_bytes"])
            or source_stat.st_mtime_ns != int(row["source_mtime_ns"])
            or sha256_file(source_path) != row["source_sha256"]
            or not isinstance(row.get("source_exif"), dict)
            or not row["source_exif"]
            or object_sha256(row["source_exif"]) != row["source_exif_sha256"]
        ):
            raise ValueError(f"staged input is not provenance-bound to {expected_path}")
        if kind == "native-arw":
            if (
                staged_row["name"].upper() != row["source_name"].upper()
                or staged_row["sha256"] != row["source_sha256"]
            ):
                raise ValueError("native staged copy differs from its source ARW")
    bindings = []
    if kind == "common-tiff":
        decoder = manifest.get("decoder", {})
        decoder_artifacts = decoder.get("artifacts", [])
        if (
            not isinstance(decoder_artifacts, list)
            or not decoder_artifacts
            or sum(
                artifact.get("role") == "decoder-executable"
                for artifact in decoder_artifacts
                if isinstance(artifact, dict)
            )
            != 1
        ):
            raise ValueError("common-TIFF decoder executable is not uniquely bound")
        bindings = [
            read_artifact_binding(
                repository_path(artifact["path"]),
                artifact["sha256"],
            )
            for artifact in decoder_artifacts
        ]
        pattern_binding = read_artifact_binding(
            repository_path(decoder["deterministic_pattern_map"]["path"]),
            decoder["deterministic_pattern_map"]["sha256"],
        )
        bindings.append(pattern_binding)
        require_guard("G04-artifact-binding", {"artifacts": bindings})
        settings_sha256 = object_sha256(decoder.get("settings"))
        if (
            not decoder.get("converter_id")
            or decoder.get("settings_sha256") != settings_sha256
        ):
            raise ValueError("common-TIFF decoder/settings provenance is incomplete")
        decoder_artifacts_sha256 = object_sha256(
            [
                {
                    "path": binding["path"],
                    "sha256": binding["actual_sha256"],
                }
                for binding in bindings
            ]
        )
        for row, staged_row in zip(rows, staged["files"]):
            description = strict_json_loads(staged_row["image_description"])
            if description != {
                "decoder_artifacts_sha256": decoder_artifacts_sha256,
                "decoder_settings_sha256": settings_sha256,
                "source_arw_sha256": row["source_sha256"],
            }:
                raise ValueError(
                    "common TIFF does not embed the exact source/decoder provenance"
                )
    return bindings


def validate_native_dimensions(
    *,
    manifest: dict[str, Any],
    stack_id: str,
    image_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence_path = repository_path(manifest["native_dimensions_evidence"]["path"])
    evidence, evidence_binding = load_bound_json(manifest["native_dimensions_evidence"])
    commission, commission_binding = load_bound_json(evidence["commission_artifact"])
    payload = {
        key: value for key, value in evidence.items() if key != "commission_artifact"
    }
    checker_result, checker_bindings = run_commissioned_checker(
        artifact_path=evidence_path,
        payload_sha256=object_sha256(payload),
        checker_artifact=evidence["checker_artifact"],
        checker_support_artifacts=evidence.get("checker_support_artifacts", []),
        commission=commission,
    )
    expected_sources = [
        {
            "name": row["source_name"],
            "sha256": row["source_sha256"],
        }
        for row in manifest["files"]
    ]
    if (
        evidence.get("schema") != "m153-native-dimensions-evidence-v1"
        or evidence.get("evidence_tag") != "MEASURED"
        or evidence.get("verdict") != "PASS"
        or evidence.get("stack_id") != stack_id
        or evidence.get("source_files") != expected_sources
        or evidence.get("active_height") != image_contract.get("height")
        or evidence.get("active_width") != image_contract.get("width")
        or commission.get("schema") != "m153-dimensions-checker-commission-v1"
        or commission.get("status") != "PASS"
        or commission.get("checker_sha256") != checker_bindings[0]["actual_sha256"]
        or commission.get("checker_bundle_sha256")
        != checker_result["checker_bundle_sha256"]
        or not checker_bundle_approved(
            "native_dimensions",
            checker_result["checker_bundle_sha256"],
        )
        or commission.get("accepted_evidence_payload_sha256") != object_sha256(payload)
        or commission.get("mutations_killed") != commission.get("mutations_total")
        or int(commission.get("mutations_total", 0)) < 1
        or commission.get("inert_survived") != 1
        or checker_result.get("mutations_killed") != commission.get("mutations_killed")
        or checker_result.get("mutations_total") != commission.get("mutations_total")
        or checker_result.get("inert_survived") != commission.get("inert_survived")
        or checker_result.get("verdict") != evidence.get("verdict")
    ):
        raise ValueError("native output dimensions are not commissioned")
    return [evidence_binding, commission_binding, *checker_bindings]


def load_adapter_identity(
    campaign: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    identity_path = repository_path(campaign["common_tiff_adapter_identity"]["path"])
    identity, identity_binding = load_bound_json(
        campaign["common_tiff_adapter_identity"]
    )
    commission, commission_binding = load_bound_json(identity["commission_artifact"])
    payload = {
        key: value for key, value in identity.items() if key != "commission_artifact"
    }
    checker_result, checker_bindings = run_commissioned_checker(
        artifact_path=identity_path,
        payload_sha256=object_sha256(payload),
        checker_artifact=identity["checker_artifact"],
        checker_support_artifacts=identity.get("checker_support_artifacts", []),
        commission=commission,
    )
    if (
        identity.get("schema") != "m153-strehl-common-adapter-identity-v1"
        or identity.get("status") != "PASS"
        or identity.get("contract_sha256") != sha256_file(CONTRACT_PATH)
        or commission.get("schema") != "m153-adapter-identity-commission-v1"
        or commission.get("status") != "PASS"
        or commission.get("checker_sha256") != checker_bindings[0]["actual_sha256"]
        or commission.get("checker_bundle_sha256")
        != checker_result["checker_bundle_sha256"]
        or not checker_bundle_approved(
            "adapter_identity",
            checker_result["checker_bundle_sha256"],
        )
        or commission.get("accepted_identity_payload_sha256") != object_sha256(payload)
        or commission.get("mutations_killed") != commission.get("mutations_total")
        or int(commission.get("mutations_total", 0)) < 1
        or commission.get("inert_survived") != 1
        or checker_result.get("mutations_killed") != commission.get("mutations_killed")
        or checker_result.get("mutations_total") != commission.get("mutations_total")
        or checker_result.get("inert_survived") != commission.get("inert_survived")
        or checker_result.get("verdict") != identity.get("status")
    ):
        raise ValueError("Strehl common-TIFF adapter identity is uncommissioned")
    return identity, [
        identity_binding,
        *checker_bindings,
        commission_binding,
    ]


def validate_segment_inputs(
    *,
    campaign: dict[str, Any],
    segment_name: str,
    segment: dict[str, Any],
    uncached_executables: bool = False,
) -> dict[tuple[str, int, str], list[dict[str, Any]]]:
    settings = campaign["settings"]
    quality_data = None
    quality_result = None
    adapter_identity = None
    census, census_binding = load_bound_json(
        {
            "path": campaign["inputs"]["census_path"],
            "sha256": campaign["inputs"]["census_sha256"],
        }
    )
    if (
        census.get("schema") != "m153-input-census-v1"
        or census.get("status") != "PASS"
        or census.get("contract", {}).get("sha256") != sha256_file(CONTRACT_PATH)
        or not evaluate_guard(
            "G02-capture-contract",
            {"captures": census.get("captures", {})},
        ).passed
    ):
        raise ValueError("campaign census is stale or invalid")
    shared_bindings = [census_binding]
    bindings_by_cell = {}
    comparative_manifest_by_stack: dict[str, str] = {}
    if segment_name.startswith("comparative"):
        quality_reference = campaign["quality_qualification"]
        quality_path = repository_path(quality_reference["path"])
        binding = read_artifact_binding(
            quality_path,
            quality_reference["sha256"],
        )
        require_guard("G04-artifact-binding", {"artifacts": [binding]})
        shared_bindings.append(binding)
        adapter_identity, adapter_bindings = load_adapter_identity(campaign)
        shared_bindings.extend(adapter_bindings)
        quality_data = read_json(quality_path)
        quality_result = validate_quality_manifest(
            quality_path,
            uncached_executables=uncached_executables,
        )
        if quality_result["status"] != "PASS":
            raise ValueError(
                "comparative run refused: quality envelope is not fully bound"
            )
    for cell in segment["cells"]:
        input_dir = repository_path(cell["input_dir"])
        if not path_is_within(input_dir, LANE_ROOT):
            raise ValueError(
                f"renderer input must be a staged owned copy, got {input_dir}"
            )
        input_path = repository_path(cell["input_manifest_path"])
        input_binding = read_artifact_binding(
            input_path,
            cell["input_manifest_sha256"],
        )
        require_guard("G04-artifact-binding", {"artifacts": [input_binding]})
        bindings_by_cell[
            (
                str(cell["stack_id"]),
                int(cell["count"]),
                str(cell["input_manifest_sha256"]),
            )
        ] = [*shared_bindings, input_binding]
        input_manifest = read_json(input_path)
        input_kind = (
            "common-tiff" if segment_name.startswith("comparative") else "native-arw"
        )
        staged = verify_staged_input(
            input_dir=input_dir,
            manifest=input_manifest,
            kind=input_kind,
            uncached=segment.get("cache_state") == "COLD_RESET",
        )
        provenance_bindings = validate_input_provenance(
            manifest=input_manifest,
            staged=staged,
            cell=cell,
            kind=input_kind,
            census_sha256=census_binding["actual_sha256"],
        )
        image_contract = staged.get("image_contract")
        if not isinstance(image_contract, dict):
            raise ValueError("staged input manifest lacks its image contract")
        dimension_bindings = validate_native_dimensions(
            manifest=input_manifest,
            stack_id=str(cell["stack_id"]),
            image_contract=image_contract,
        )
        if any(
            settings[setting_id].get("output_contract") != image_contract
            for setting_id in cell["settings"]
        ):
            raise ValueError(
                "timed output contract differs from commissioned native dimensions"
            )
        bindings_by_cell[
            (
                str(cell["stack_id"]),
                int(cell["count"]),
                str(cell["input_manifest_sha256"]),
            )
        ].extend([*provenance_bindings, *dimension_bindings])
        if segment_name.startswith("comparative"):
            if quality_data is None or quality_result is None:
                raise AssertionError("comparative quality preflight was not loaded")
            if adapter_identity is None:
                raise AssertionError("comparative adapter identity was not loaded")
            full_count = int(load_contract()["inputs"][cell["stack_id"]]["frame_count"])
            expected_stems = [
                Path(name).stem
                for name in expected_capture_names(cell["stack_id"], full_count)
            ]
            actual_stems = [Path(row["name"]).stem.upper() for row in staged["files"]]
            if (
                len(staged["files"]) != full_count
                or actual_stems != expected_stems
                or int(cell["count"])
                not in {
                    "bee-1-cpl": {33, 299},
                    "coffee-bean": {105},
                }.get(str(cell["stack_id"]), set())
            ):
                raise ValueError(
                    "comparative input must be the full registered capture; "
                    "the bound {count} command argument selects its prefix"
                )
            prior_manifest = comparative_manifest_by_stack.setdefault(
                str(cell["stack_id"]),
                input_binding["actual_sha256"],
            )
            if prior_manifest != input_binding["actual_sha256"]:
                raise ValueError(
                    "comparative prefixes for one capture must share one full "
                    "common-TIFF manifest"
                )
            common_modes = []
            timed_comparator_modes = set()
            strehl_settings = [
                settings[setting_id]
                for setting_id in cell["settings"]
                if settings[setting_id]["role"] == "strehl-common"
            ]
            expected_strehl_workers = (
                set(WORKER_LADDER) if segment_name == "comparative-warm" else {16}
            )
            proof = adapter_identity.get("captures", {}).get(
                cell["stack_id"],
                {},
            )
            staged_pixels = [row["pixel_sha256"] for row in staged["files"]]
            if (
                len(strehl_settings) != len(expected_strehl_workers)
                or {int(setting.get("workers", -1)) for setting in strehl_settings}
                != expected_strehl_workers
                or adapter_identity.get("candidate_binary_sha256")
                not in {setting["binary_sha256"] for setting in strehl_settings}
                or len({setting["binary_sha256"] for setting in strehl_settings}) != 1
                or adapter_identity.get("candidate_settings_sha256")
                not in {setting["settings_sha256"] for setting in strehl_settings}
                or len({setting["settings_sha256"] for setting in strehl_settings}) != 1
                or proof.get("input_manifest_sha256") != input_binding["actual_sha256"]
                or proof.get("common_pixel_sha256") != staged_pixels
                or proof.get("internal_pixel_sha256") != staged_pixels
            ):
                raise ValueError(
                    "Strehl internal pre-merge frames are not bit-identical "
                    "to the registered common TIFFs"
                )
            for setting_id in cell["settings"]:
                setting = settings[setting_id]
                output_contract = setting["output_contract"]
                if image_contract != output_contract:
                    raise ValueError(
                        "comparative input and output representation contracts differ"
                    )
                common_modes.append(
                    {
                        "input_manifest_sha256": input_binding["actual_sha256"],
                        "ordered_input_sha256": staged["ordered_input_sha256"],
                        "volume_id": staged["volume_id"],
                        "dimensions": [
                            image_contract["height"],
                            image_contract["width"],
                            image_contract.get("samples_per_pixel", 3),
                        ],
                        "bit_depth": image_contract["bits_per_sample"],
                        "icc_sha256": image_contract["icc_sha256"],
                        "compression": image_contract["compression"],
                    }
                )
                quality_timed_mode = setting["role"] == "comparator" or (
                    setting["role"] == "strehl-common"
                    and int(setting.get("workers", -1)) == 16
                )
                if not quality_timed_mode:
                    continue
                mode_id = setting["mode_id"]
                if setting["role"] == "comparator":
                    timed_comparator_modes.add(mode_id)
                cell_id = quality_cell_id(
                    str(cell["stack_id"]),
                    int(cell["count"]),
                )
                qualified_for_cell = (
                    mode_id in set(quality_result["qualified_modes_by_cell"][cell_id])
                    if setting["role"] == "comparator"
                    else quality_result["strehl_qualified_by_cell"][cell_id]
                    and mode_id == STREHL_QUALITY_MODE_ID
                )
                if not qualified_for_cell:
                    raise ValueError(
                        f"{mode_id} is not quality-qualified on {cell['stack_id']}"
                    )
                qualification = comparator_quality_fingerprint(
                    quality_data,
                    quality_result,
                    mode_id=mode_id,
                    cell_id=cell_id,
                    count=int(cell["count"]),
                )
                require_guard(
                    "G08-settings-fingerprint",
                    {
                        "timed": {
                            "mode_id": mode_id,
                            "binary_sha256": setting["binary_sha256"],
                            "executable_bundle_sha256": executable_bundle_sha256(
                                executable_artifact_guard(
                                    setting,
                                    uncached=segment.get("cache_state") == "COLD_RESET",
                                )
                            ),
                            "settings_sha256": setting["settings_sha256"],
                            "input_manifest_sha256": input_binding["actual_sha256"],
                            "output_contract_sha256": object_sha256(output_contract),
                            "count": int(cell["count"]),
                        },
                        "qualified": qualification,
                    },
                )
            require_guard(
                "G06-common-input-identity",
                {"modes": common_modes},
            )
            held_fixed_hashes = [object_sha256(mode) for mode in common_modes]
            require_guard(
                "G19-arm-symmetry",
                {
                    "comparison": "comparative",
                    "changed_factor_groups": ["program-and-frozen-mode"],
                    "held_fixed_sha256": held_fixed_hashes,
                    "confounds": [],
                },
            )
            expected_comparator_modes = set(
                quality_result["qualified_modes_by_cell"][
                    quality_cell_id(str(cell["stack_id"]), int(cell["count"]))
                ]
            )
            if timed_comparator_modes != expected_comparator_modes:
                raise ValueError(
                    "comparative segment must time every and only "
                    "quality-qualified comparator mode"
                )
        else:
            require_guard(
                "G07-native-prefix",
                {
                    "stack_id": cell["stack_id"],
                    "count": int(cell["count"]),
                    "ordered_names": [row["name"] for row in staged["files"]],
                    "ordered_sha256": [row["sha256"] for row in staged["files"]],
                },
            )
            if segment_name == "live":
                trace, trace_bindings = validate_signed_acquisition_trace(
                    cell["cadence_manifest"]
                )
                staged_by_name = {
                    str(row["name"]).upper(): row for row in staged["files"]
                }
                expected_frames = [
                    {
                        "name": trace_frame["name"],
                        "staged_path": str(
                            input_dir
                            / staged_by_name[str(trace_frame["name"]).upper()]["name"]
                        ),
                        "sha256": staged_by_name[str(trace_frame["name"]).upper()][
                            "sha256"
                        ],
                        "shutter_close_offset_seconds": trace_frame[
                            "shutter_close_offset_seconds"
                        ],
                        "file_available_offset_seconds": trace_frame[
                            "file_available_offset_seconds"
                        ],
                    }
                    for trace_frame in trace["frames"]
                ]
                if cell.get("frames") != expected_frames:
                    raise ValueError(
                        "live cell frames do not match its signed acquisition trace"
                    )
                bindings_by_cell[
                    (
                        str(cell["stack_id"]),
                        int(cell["count"]),
                        str(cell["input_manifest_sha256"]),
                    )
                ].extend(trace_bindings)
            by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for setting_id in cell["settings"]:
                by_role[settings[setting_id]["role"]].append(settings[setting_id])
            candidate_cpu_16 = [
                setting
                for setting in by_role["candidate-cpu"]
                if int(setting.get("workers", -1)) == 16
            ]
            if segment_name == "product-warm" and (
                len(by_role["candidate-cpu"]) != 1
                or int(by_role["candidate-cpu"][0].get("workers", -1)) != 16
                or len(by_role["candidate-hybrid"]) != 1
                or len(by_role["frozen-default-baseline"]) != 1
            ):
                raise ValueError(
                    "each warm product cell must include candidate CPU-16, hybrid, "
                    "and frozen baseline"
                )
            if (
                len(candidate_cpu_16) == 1
                and len(by_role["frozen-default-baseline"]) == 1
            ):
                candidate_setting = candidate_cpu_16[0]
                baseline_setting = by_role["frozen-default-baseline"][0]
                candidate = candidate_setting["settings_payload"]
                baseline = baseline_setting["settings_payload"]
                confounds = []
                if candidate.get("common") != baseline.get("common"):
                    confounds.append("non-build-settings")
                if candidate.get("acceleration_mode") != baseline.get(
                    "acceleration_mode"
                ):
                    confounds.append("acceleration-mode")
                if product_operational_signature(
                    candidate_setting
                ) != product_operational_signature(baseline_setting):
                    confounds.append("operational-command-or-environment")
                if candidate_setting.get("binary_sha256") == baseline_setting.get(
                    "binary_sha256"
                ):
                    confounds.append("build-not-different")
                require_guard(
                    "G19-arm-symmetry",
                    {
                        "comparison": "product-baseline",
                        "changed_factor_groups": ["build"],
                        "held_fixed_sha256": [
                            object_sha256(candidate.get("common")),
                            object_sha256(baseline.get("common")),
                        ],
                        "confounds": confounds,
                    },
                )
            if len(candidate_cpu_16) == 1 and len(by_role["candidate-hybrid"]) == 1:
                candidate_setting = candidate_cpu_16[0]
                hybrid_setting = by_role["candidate-hybrid"][0]
                candidate = candidate_setting["settings_payload"]
                hybrid = hybrid_setting["settings_payload"]
                confounds = []
                if candidate.get("common") != hybrid.get("common"):
                    confounds.append("non-acceleration-settings")
                if candidate.get("build") != hybrid.get("build"):
                    confounds.append("build")
                if candidate_setting.get("executable_artifacts") != hybrid_setting.get(
                    "executable_artifacts"
                ):
                    confounds.append("executable-artifacts")
                if candidate.get("acceleration_mode") == hybrid.get(
                    "acceleration_mode"
                ):
                    confounds.append("acceleration-mode-not-different")
                if product_operational_signature(
                    candidate_setting
                ) != product_operational_signature(hybrid_setting):
                    confounds.append("operational-command-or-environment")
                require_guard(
                    "G19-arm-symmetry",
                    {
                        "comparison": "product-acceleration",
                        "changed_factor_groups": ["acceleration-mode"],
                        "held_fixed_sha256": [
                            object_sha256(candidate.get("common")),
                            object_sha256(hybrid.get("common")),
                        ],
                        "confounds": confounds,
                    },
                )
    return bindings_by_cell


def records_match_campaign_identity(
    records: list[dict[str, Any]],
    expected: dict[str, Any],
) -> bool:
    """Reject record reuse unless every row has the exact frozen identity."""

    fields = (
        "campaign_sha256",
        "authorization_sha256",
        "contract_sha256",
        "measured_commit",
    )
    return all(
        all(record.get(field) == expected.get(field) for field in fields)
        for record in records
    )


def campaign_attempt_path(campaign_sha256: str) -> Path:
    if not _hash_text(campaign_sha256):
        raise ValueError("campaign attempt ledger requires a SHA-256 identity")
    return LANE_ROOT / "out" / "campaign-attempts" / f"{campaign_sha256}.jsonl"


def records_file_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sha256": None, "record_count": 0}
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    for line in lines:
        parse_json_line(line)
    return {
        "sha256": sha256_file(path),
        "record_count": len(lines),
    }


def campaign_attempt_history(
    campaign_sha256: str,
    *,
    required_attempt_ids: set[str] | None = None,
    required_records_path: Path | None = None,
) -> dict[str, Any]:
    path = campaign_attempt_path(campaign_sha256)
    rows = (
        [
            parse_json_line(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if path.exists()
        else []
    )
    records_paths: set[str] = set()
    structurally_valid = True
    for row in rows:
        try:
            state = str(row["state"])
            structurally_valid &= (
                row.get("schema") == "m153-campaign-attempt-v1"
                and row.get("campaign_sha256") == campaign_sha256
                and isinstance(row.get("attempt_id"), str)
                and bool(row["attempt_id"])
                and state in {"STARTED", "COMPLETED", "ABORTED"}
                and isinstance(row.get("records_path"), str)
                and bool(row["records_path"])
            )
            records_paths.add(str(Path(row["records_path"]).resolve()))
        except (KeyError, TypeError, ValueError):
            structurally_valid = False
    pairs = [rows[index : index + 2] for index in range(0, len(rows), 2)]
    sequence_valid = (
        bool(rows)
        and len(rows) % 2 == 0
        and all(
            len(pair) == 2
            and pair[0].get("state") == "STARTED"
            and pair[1].get("state") == "COMPLETED"
            and pair[0].get("attempt_id") == pair[1].get("attempt_id")
            and pair[0].get("segment") == pair[1].get("segment")
            and pair[0].get("records_path") == pair[1].get("records_path")
            and pair[0].get("records_before_sha256")
            == (None if index == 0 else pairs[index - 1][1].get("records_after_sha256"))
            and int(pair[0].get("records_before_count", -1))
            == (
                0
                if index == 0
                else int(pairs[index - 1][1].get("records_after_count", -2))
            )
            and int(pair[1].get("records_after_count", -1))
            >= int(pair[0].get("records_before_count", 0))
            for index, pair in enumerate(pairs)
        )
    )
    completed_ids = {str(pair[0]["attempt_id"]) for pair in pairs if len(pair) == 2}
    required = required_attempt_ids or set()
    required_records = (
        str(required_records_path.resolve())
        if required_records_path is not None
        else None
    )
    current_state = (
        records_file_state(required_records_path)
        if required_records_path is not None
        else None
    )
    last_after = pairs[-1][1] if pairs and len(pairs[-1]) == 2 else {}
    return {
        "path": str(path),
        "exists": path.exists(),
        "row_count": len(rows),
        "completed_attempt_ids": sorted(completed_ids),
        "required_attempt_ids": sorted(required),
        "records_paths": sorted(records_paths),
        "required_records_path": required_records,
        "current_records": current_state,
        "valid": (
            structurally_valid
            and sequence_valid
            and required.issubset(completed_ids)
            and len(records_paths) == 1
            and (required_records is None or records_paths == {required_records})
            and (
                current_state is None
                or (
                    current_state["sha256"] == last_after.get("records_after_sha256")
                    and current_state["record_count"]
                    == int(last_after.get("records_after_count", -1))
                )
            )
        ),
    }


def begin_campaign_attempt(
    *,
    campaign_sha256: str,
    segment_name: str,
    records_path: Path,
) -> dict[str, Any]:
    history = campaign_attempt_history(
        campaign_sha256,
        required_records_path=records_path,
    )
    if history["exists"] and not history["valid"]:
        raise RuntimeError(
            "campaign was durably invalidated or uses a different frozen records path"
        )
    before = records_file_state(records_path)
    if not history["exists"] and before["record_count"] != 0:
        raise RuntimeError(
            "records exist without the canonical campaign attempt history"
        )
    attempt = {
        "schema": "m153-campaign-attempt-v1",
        "campaign_sha256": campaign_sha256,
        "attempt_id": uuid.uuid4().hex,
        "segment": segment_name,
        "records_path": str(records_path),
        "records_before_sha256": before["sha256"],
        "records_before_count": before["record_count"],
        "state": "STARTED",
        "observed_utc": utc_now(),
    }
    append_jsonl(campaign_attempt_path(campaign_sha256), attempt)
    return attempt


def finish_campaign_attempt(attempt: dict[str, Any], state: str) -> None:
    if state not in {"COMPLETED", "ABORTED"}:
        raise ValueError("campaign attempt terminal state is invalid")
    terminal = {**attempt, "state": state, "observed_utc": utc_now()}
    if state == "COMPLETED":
        current = records_file_state(Path(attempt["records_path"]))
        terminal["records_after_sha256"] = current["sha256"]
        terminal["records_after_count"] = current["record_count"]
    append_jsonl(
        campaign_attempt_path(str(attempt["campaign_sha256"])),
        terminal,
    )


def _run_segment_impl(
    *,
    campaign_path: Path,
    authorization_path: Path,
    segment_name: str,
    work: Path,
    records_path: Path,
    attempt_box: dict[str, Any],
) -> int:
    campaign_path = campaign_path.resolve()
    authorization_path = authorization_path.resolve()
    work = work.resolve()
    records_path = records_path.resolve()
    contract = load_contract()
    campaign = read_json(campaign_path)
    authorization = validate_authorization(
        campaign_path,
        campaign,
        authorization_path,
    )
    cold_segment = (
        campaign.get("segments", {}).get(segment_name, {}).get("cache_state")
        == "COLD_RESET"
    )
    validate_frozen_campaign(
        campaign,
        uncached_executables=cold_segment,
    )
    host_instruments = validate_host_instruments(campaign)
    segment = campaign["segments"][segment_name]
    segment_bindings = []
    if segment_name == "live":
        segment_bindings.append(validate_live_registration(campaign))
    if segment.get("cache_state") == "COLD_RESET":
        cold_provider = segment["cold_reset_provider"]
        cold_provider_path = repository_path(cold_provider["path"])
        cold_provider_binding = read_artifact_binding(
            cold_provider_path,
            cold_provider["sha256"],
        )
        require_guard(
            "G04-artifact-binding",
            {"artifacts": [cold_provider_binding]},
        )
        segment_bindings.append(cold_provider_binding)
    require_guard(
        "G01-owned-output",
        {"path": str(work), "lane_root": str(LANE_ROOT)},
    )
    require_guard(
        "G01-owned-output",
        {"path": str(records_path), "lane_root": str(LANE_ROOT)},
    )
    work.mkdir(parents=True, exist_ok=True)
    settings = campaign["settings"]
    setting_bindings = {}
    for setting_id in {
        setting_id for cell in segment["cells"] for setting_id in cell["settings"]
    }:
        setting = settings[setting_id]
        setting_bindings[setting_id] = setting_artifact_guard(
            setting,
            uncached=cold_segment,
        )
        expected_stages = {
            "load",
            "registration",
            "fold",
            "colour",
            "write",
        }
        if not segment_name.startswith("comparative"):
            expected_stages = {
                "decode",
                "registration",
                "fold",
                "colour",
                "write",
            }
        if set(setting.get("required_stages", [])) != expected_stages:
            raise ValueError(
                f"{setting_id} must expose exactly the registered stage set "
                f"{sorted(expected_stages)}"
            )
        numeric = set(setting.get("numeric_stage_timings_required", []))
        if setting.get("role") != "comparator" and numeric != expected_stages:
            raise ValueError(
                f"{setting_id} must report numeric CPU/wall values for every stage"
            )
        if setting.get("role") == "comparator" and not numeric.issubset(
            expected_stages
        ):
            raise ValueError(f"{setting_id} names unknown numeric stages")
    input_bindings = validate_segment_inputs(
        campaign=campaign,
        segment_name=segment_name,
        segment=segment,
        uncached_executables=cold_segment,
    )
    commission_path = repository_path(authorization["commission"]["path"])
    commission = read_json(commission_path)
    run_bindings = [
        read_artifact_binding(campaign_path, sha256_file(campaign_path)),
        read_artifact_binding(
            authorization_path,
            sha256_file(authorization_path),
        ),
        read_artifact_binding(CONTRACT_PATH, sha256_file(CONTRACT_PATH)),
        read_artifact_binding(
            commission_path,
            authorization["commission"]["artifact_sha256"],
        ),
        read_artifact_binding(
            repository_path(authorization["build_audit"]["path"]),
            authorization["build_audit"]["sha256"],
        ),
        read_artifact_binding(
            Path(commission["runtime"]["python_executable"]["path"]),
            commission["runtime"]["python_executable"]["sha256"],
        ),
        *[
            read_artifact_binding(
                repository_path(binding["path"]),
                binding["sha256"],
            )
            for binding in commission["source_bindings"].values()
        ],
    ]
    existing_records = (
        [
            parse_json_line(line)
            for line in records_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if records_path.exists()
        else []
    )
    campaign_sha256 = sha256_file(campaign_path)
    authorization_sha256 = sha256_file(authorization_path)
    contract_sha256 = sha256_file(CONTRACT_PATH)
    expected_identity = {
        "campaign_sha256": campaign_sha256,
        "authorization_sha256": authorization_sha256,
        "contract_sha256": contract_sha256,
        "measured_commit": campaign["measured_commit"],
    }
    if not records_match_campaign_identity(existing_records, expected_identity):
        raise ValueError("records file contains a different campaign identity")
    attempt = begin_campaign_attempt(
        campaign_sha256=campaign_sha256,
        segment_name=segment_name,
        records_path=records_path,
    )
    attempt_box["attempt"] = attempt
    used_cold_boot_ids = {
        str(record["cold_reset"]["windows_boot_id"])
        for record in existing_records
        if isinstance(record.get("cold_reset"), dict)
        and record["cold_reset"].get("windows_boot_id") is not None
    }
    for cell in segment["cells"]:
        setting_ids = list(cell["settings"])
        cold_pair_segment = segment.get("cache_state") == "COLD_RESET"
        schedule = (
            cold_pair_schedule(setting_ids, repetitions=6)
            if cold_pair_segment
            else alternating_schedule(setting_ids, repetitions=6)
        )
        schedule_guard_rows = [
            {**row, "accepted": True, "pair_complete": True} for row in schedule
        ]
        require_guard(
            "G13-schedule-complete",
            {
                "settings": setting_ids,
                "repetitions": 6,
                "schedule_kind": ("cold-pairs" if cold_pair_segment else "ordinary"),
                "records": schedule_guard_rows,
            },
        )
        completed_pair_ids: set[str] = set()
        if cold_pair_segment:
            prior_pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for prior in existing_records:
                if (
                    prior.get("segment") == segment_name
                    and prior.get("stack_id") == cell["stack_id"]
                    and int(prior.get("count", -1)) == int(cell["count"])
                ):
                    prior_pairs[str(prior.get("pair_id"))].append(prior)
            for pair_id, pair_rows in prior_pairs.items():
                if (
                    len(pair_rows) != 2
                    or {row.get("pair_member") for row in pair_rows} != {"cold", "warm"}
                    or not all(row.get("pair_complete") is True for row in pair_rows)
                ):
                    raise ValueError(
                        "partial cold/warm pair invalidates the campaign; "
                        "selective rerun is forbidden"
                    )
                completed_pair_ids.add(pair_id)
        pending_cold_record: dict[str, Any] | None = None
        for row_index, schedule_row in enumerate(schedule):
            if cold_pair_segment and schedule_row["pair_id"] in completed_pair_ids:
                continue
            setting_id = schedule_row["setting_id"]
            setting = settings[setting_id]
            pair_suffix = f"-{schedule_row['pair_member']}" if cold_pair_segment else ""
            run_tag = (
                f"{segment_name}-{cell['stack_id']}-n{cell['count']}-"
                f"r{schedule_row['repetition']}-{schedule_row['position']}-"
                f"{setting_id}{pair_suffix}"
            )
            run_root = work / "runs" / run_tag
            private = {name: run_root / name for name in ("temp", "cache", "warpmap")}
            owned_paths = [
                run_root,
                *private.values(),
                run_root / "master.tiff",
                run_root / "invocation-manifest.json",
                run_root / "measurement-receipt.json",
                run_root / "stdout.log",
                run_root / "stderr.log",
                run_root / "spool",
                run_root / "live-epoch.json",
                run_root / "input",
            ]
            for owned_path in owned_paths:
                require_guard(
                    "G01-owned-output",
                    {"path": str(owned_path), "lane_root": str(LANE_ROOT)},
                )
            for path in private.values():
                path.mkdir(parents=True, exist_ok=False)
            input_snapshot_dir, input_snapshot_paths = create_invocation_input_snapshot(
                cell,
                run_root / "input",
            )
            input_binding_rows = input_bindings[
                (
                    str(cell["stack_id"]),
                    int(cell["count"]),
                    str(cell["input_manifest_sha256"]),
                )
            ]
            locked_artifacts_by_path = {
                str(Path(binding["path"]).resolve(strict=True)): {
                    "path": str(Path(binding["path"]).resolve(strict=True)),
                    "sha256": binding["actual_sha256"],
                }
                for binding in (
                    *run_bindings,
                    *host_instruments["artifact_bindings"],
                    *segment_bindings,
                    *setting_bindings[setting_id],
                    *input_binding_rows,
                )
            }
            if (
                segment_name == "live"
                and str(PYTHON_EXECUTABLE) not in locked_artifacts_by_path
            ):
                raise ValueError(
                    "live replay Python executable is not in the frozen "
                    "candidate executable bundle"
                )
            locked_artifacts = sorted(
                locked_artifacts_by_path.values(),
                key=lambda binding: binding["path"].casefold(),
            )
            input_locks = ReadOnlyFileLocks(
                [
                    *([] if segment_name == "live" else input_snapshot_paths),
                    *[Path(binding["path"]) for binding in locked_artifacts],
                ]
            )
            locked_artifact_preflight = [
                read_artifact_binding(
                    Path(binding["path"]),
                    binding["sha256"],
                    uncached=cold_pair_segment,
                )
                for binding in locked_artifacts
            ]
            require_guard(
                "G04-artifact-binding",
                {"artifacts": locked_artifact_preflight},
            )
            artifact_read_modes = {
                str(Path(binding["path"]).resolve(strict=True)): binding["read_mode"]
                for binding in locked_artifact_preflight
            }
            locked_artifacts = [
                {
                    **binding,
                    "preflight_read_mode": artifact_read_modes[binding["path"]],
                }
                for binding in locked_artifacts
            ]
            output_path = run_root / "master.tiff"
            manifest_path = run_root / "invocation-manifest.json"
            stdout_path = run_root / "stdout.log"
            stderr_path = run_root / "stderr.log"
            values = {
                "output": str(output_path),
                "input_dir": str(input_snapshot_dir),
                "count": int(cell["count"]),
                "workers": int(setting.get("workers", 16)),
                "acceleration_mode": setting.get("settings_payload", {}).get(
                    "acceleration_mode",
                    "",
                ),
                "temp": str(private["temp"]),
                "cache": str(private["cache"]),
                "warpmap": str(private["warpmap"]),
                "run_root": str(run_root.resolve()),
                "spool": str((run_root / "spool").resolve()),
                "live_marker": str((run_root / "live-epoch.json").resolve()),
            }
            env, declared = clean_child_environment(
                setting.get("environment", {}),
                private,
            )
            input_content_sha256 = verify_cell_input_content(
                cell,
                segment_name=segment_name,
                input_dir_override=input_snapshot_dir,
                uncached=cold_pair_segment,
            )
            input_preflight_completed_qpc_ticks = qpc_ticks()
            cold_reset = None
            if cold_pair_segment and schedule_row["pair_member"] == "cold":
                cold_reset = reset_cold_cache(
                    provider=segment["cold_reset_provider"],
                    position_key=run_tag,
                    campaign_sha256=campaign_sha256,
                    previously_used_boot_ids=used_cold_boot_ids,
                )
            preload = host_preflight(
                float(campaign["conditions"]["preload_sample_seconds"]),
                campaign["host"]["gpu_probe"],
            )
            preload_pass = (
                preload["busy_fraction"] is not None
                and preload["busy_fraction"]
                <= float(contract["conditions"]["preload_host_busy_max"])
                and preload["hardware_sample_coverage_pass"]
                and not preload["hardware_errors"]
                and not preload["hardware_throttle_observed"]
                and preload["gpu_process_allowlist_pass"]
            )
            if not preload_pass:
                raise RuntimeError(
                    "host is not quiet; aborting rather than recording a timing"
                )
            power_before = active_power_plan()
            if power_before != campaign["host"]["power_plan"]:
                raise RuntimeError(
                    "active power plan does not match the frozen campaign"
                )
            thermal_before = thermal_reading(campaign["host"]["thermal_probe"])
            live_marker_path = None
            live_spec_lock = None
            invocation_bindings: list[dict[str, Any]] = []
            argv: list[str]
            setting_cwd = repository_path(setting.get("cwd", ROOT)).resolve(strict=True)
            if segment_name == "live":
                live = setting["live_replay"]
                replay_spec_path = work / "runs" / run_tag / "live-replay.json"
                stacker_cwd = repository_path(live.get("stacker_cwd", ROOT)).resolve(
                    strict=True
                )
                stacker_argv = expand_argv(
                    live["stacker_argv"],
                    values,
                    cwd=stacker_cwd,
                )
                stacker_argv = canonicalize_command_file_arguments(
                    stacker_argv,
                    cwd=stacker_cwd,
                )
                require_bound_command_files(
                    stacker_argv,
                    {
                        Path(binding["path"]).resolve(strict=True)
                        for binding in locked_artifacts
                    },
                    cwd=stacker_cwd,
                )
                invocation_frames = [
                    {
                        **frame,
                        "staged_path": str(
                            input_snapshot_dir / Path(frame["staged_path"]).name
                        ),
                    }
                    for frame in cell["frames"]
                ]
                replay_spec = {
                    "schema": "m153-live-replay-v1",
                    "signed_acquisition_trace_verified": True,
                    "frames": invocation_frames,
                    "spool_dir": values["spool"],
                    "marker_path": values["live_marker"],
                    "allowed_stacker_directories": [
                        values[name] for name in ("spool", "temp", "cache", "warpmap")
                    ],
                    "cadence_manifest": cell["cadence_manifest"],
                    "native_input_manifest": {
                        "path": cell["input_manifest_path"],
                        "sha256": cell["input_manifest_sha256"],
                    },
                    "stacker_argv": stacker_argv,
                    "stacker_cwd": str(stacker_cwd),
                }
                write_json(replay_spec_path, replay_spec)
                invocation_bindings.append(
                    read_artifact_binding(
                        replay_spec_path,
                        sha256_file(replay_spec_path),
                    )
                )
                live_spec_binding = invocation_bindings[-1]
                live_spec_lock = ReadOnlyFileLocks([replay_spec_path])
                require_guard(
                    "G04-artifact-binding",
                    {
                        "artifacts": [
                            read_artifact_binding(
                                replay_spec_path,
                                live_spec_binding["actual_sha256"],
                            )
                        ]
                    },
                )
                locked_artifacts.append(
                    {
                        "path": str(replay_spec_path.resolve(strict=True)),
                        "sha256": live_spec_binding["actual_sha256"],
                    }
                )
                argv = [
                    str(PYTHON_EXECUTABLE),
                    str(LIVE_REPLAY),
                    "--spec",
                    str(replay_spec_path),
                ]
                live_marker_path = Path(values["live_marker"])
            else:
                argv = expand_argv(setting["argv"], values, cwd=setting_cwd)
                argv = canonicalize_command_file_arguments(
                    argv,
                    cwd=setting_cwd,
                )
            require_bound_command_files(
                argv,
                {
                    Path(binding["path"]).resolve(strict=True)
                    for binding in locked_artifacts
                },
                cwd=setting_cwd,
                allowed_data_paths=(
                    {replay_spec_path.resolve(strict=True)}
                    if segment_name == "live"
                    else set()
                ),
            )
            record = run_timed_invocation(
                argv=argv,
                cwd=setting_cwd,
                env=env,
                declared_environment=declared,
                output_path=output_path,
                invocation_manifest_path=manifest_path,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                output_contract=setting["output_contract"],
                run_identity={
                    "evidence_tag": "MEASURED",
                    "segment": segment_name,
                    "arm": setting["arm"],
                    "role": setting["role"],
                    "mode_id": setting["mode_id"],
                    "setting_id": setting_id,
                    "stack_id": cell["stack_id"],
                    "count": int(cell["count"]),
                    **schedule_row,
                    "workers": int(setting.get("workers", 16)),
                    "settings_sha256": setting["settings_sha256"],
                    "input_manifest_sha256": cell["input_manifest_sha256"],
                    "input_content_sha256": input_content_sha256,
                    "output_contract_sha256": object_sha256(setting["output_contract"]),
                    "campaign_sha256": campaign_sha256,
                    "authorization_sha256": authorization_sha256,
                    "contract_sha256": contract_sha256,
                    "measured_commit": campaign["measured_commit"],
                    "campaign_attempt_id": attempt["attempt_id"],
                    "baseline_frozen_before_candidate": campaign[
                        "baseline_frozen_before_candidate"
                    ],
                },
                required_stages=setting["required_stages"],
                numeric_stage_timings_required=setting.get(
                    "numeric_stage_timings_required",
                    setting["required_stages"],
                ),
                gpu_config=campaign["host"]["gpu_probe"],
                live_marker_path=live_marker_path,
                process_image_bindings=locked_artifacts,
            )
            if not process_images_match_bound_artifacts(
                record["process_tree"],
                locked_artifacts,
            ):
                raise RuntimeError(
                    "observed process image is outside the frozen executable bundle"
                )
            record["artifact_bindings"] = [
                *run_bindings,
                *host_instruments["artifact_bindings"],
                *segment_bindings,
                *invocation_bindings,
                *setting_bindings[setting_id],
                *input_binding_rows,
            ]
            thermal_after = thermal_reading(campaign["host"]["thermal_probe"])
            power_after = active_power_plan()
            input_postflight_started_qpc_ticks = qpc_ticks()
            input_content_sha256_after = verify_cell_input_content(
                cell,
                segment_name=segment_name,
                input_dir_override=input_snapshot_dir,
            )
            input_postflight_completed_qpc_ticks = qpc_ticks()
            if input_content_sha256_after != input_content_sha256:
                raise RuntimeError("staged input changed during timed invocation")
            locked_artifact_postflight = [
                read_artifact_binding(
                    Path(binding["path"]),
                    binding["sha256"],
                )
                for binding in locked_artifacts
            ]
            require_guard(
                "G04-artifact-binding",
                {"artifacts": locked_artifact_postflight},
            )
            if live_spec_lock is not None:
                live_spec_lock.close()
            input_locks.close()
            record["input_verification"] = {
                "content_sha256": input_content_sha256,
                "snapshot_path": str(input_snapshot_dir),
                "snapshot_files": [path.name for path in input_snapshot_paths],
                "write_and_delete_locks_held_during_timing": True,
                "locked_artifacts": locked_artifacts,
                "locked_artifacts_preflight_verified": True,
                "locked_artifacts_postflight_verified": True,
                "qpc_frequency": qpc_frequency(),
                "preflight_completed_qpc_ticks": input_preflight_completed_qpc_ticks,
                "postflight_started_qpc_ticks": input_postflight_started_qpc_ticks,
                "postflight_completed_qpc_ticks": (
                    input_postflight_completed_qpc_ticks
                ),
            }
            conditions_payload = {
                "dedicated_host": campaign["host"]["dedicated"],
                "m139_released_host": campaign["host"]["m139_released"],
                "preload_quiet_pass": preload_pass,
                "preload_duration_seconds": preload["requested_seconds"],
                "preload_elapsed_seconds": preload["elapsed_seconds"],
                "preload_cpu_formula": (
                    "(DeltaKernel-DeltaIdle+DeltaUser)/(DeltaKernel+DeltaUser)"
                ),
                "external_busy_fraction": record["telemetry"]["external_busy_fraction"],
                "external_busy_max": contract["conditions"]["during_external_busy_max"],
                "power_plan_before": power_before,
                "power_plan_after": power_after,
                "thermal_before_c": thermal_before,
                "thermal_after_c": thermal_after,
                "thermal_delta_max_c": campaign["conditions"]["thermal_delta_max_c"],
                "start_temperature_min_c": campaign["conditions"][
                    "start_temperature_interval_c"
                ][0],
                "start_temperature_max_c": campaign["conditions"][
                    "start_temperature_interval_c"
                ][1],
                "telemetry_sample_interval_ms": record["telemetry"][
                    "sample_interval_ms"
                ],
                "hardware_throttle_observed": record["telemetry"][
                    "hardware_throttle_observed"
                ],
                "gpu_process_allowlist_pass": record["telemetry"][
                    "gpu_process_allowlist_pass"
                ],
                "cache_state": (
                    "COLD_RESET"
                    if cold_pair_segment and schedule_row["pair_member"] == "cold"
                    else "WARM"
                ),
                "input_preflight_io": (
                    "WINDOWS_NO_BUFFERING" if cold_pair_segment else "BUFFERED"
                ),
                "executable_preflight_io": (
                    "WINDOWS_NO_BUFFERING"
                    if all(
                        binding["preflight_read_mode"] == "WINDOWS_NO_BUFFERING"
                        for binding in locked_artifacts
                    )
                    else "BUFFERED"
                ),
                "observer_hash_control": "PASS",
            }
            conditions = require_guard(
                "G12-controlled-conditions",
                conditions_payload,
            )
            record["conditions"] = {
                **conditions_payload,
                "preload": preload,
                "guard": conditions.to_json(),
            }
            record["pair_complete"] = not cold_pair_segment
            if cold_pair_segment:
                record["pair_id"] = schedule_row["pair_id"]
                record["pair_member"] = schedule_row["pair_member"]
                if schedule_row["pair_member"] == "warm":
                    if pending_cold_record is None:
                        raise RuntimeError("cold/warm schedule lost its cold member")
                    cold_reset = pending_cold_record["cold_reset"]
            record["cold_reset"] = cold_reset
            record["sequence_index"] = row_index
            records_to_finalize = [record]
            if cold_pair_segment and schedule_row["pair_member"] == "cold":
                pending_cold_record = record
                continue
            if cold_pair_segment:
                if pending_cold_record is None:
                    raise RuntimeError("cold/warm schedule lost its cold member")
                pending_cold_record["pair_complete"] = True
                record["pair_complete"] = True
                records_to_finalize = [pending_cold_record, record]
            for finalized_record in records_to_finalize:
                receipt_path = (
                    Path(finalized_record["invocation_manifest"]["path"]).parent
                    / "measurement-receipt.json"
                )
                write_json(
                    receipt_path,
                    {
                        "schema": "m153-measurement-receipt-v1",
                        "record": finalized_record,
                    },
                )
                finalized_record["measurement_receipt"] = {
                    "path": str(receipt_path.resolve(strict=True)),
                    "sha256": sha256_file(receipt_path),
                }
                append_jsonl(records_path, finalized_record)
            if cold_pair_segment:
                return 0
    return 0


def run_segment(
    *,
    campaign_path: Path,
    authorization_path: Path,
    segment_name: str,
    work: Path,
    records_path: Path,
) -> int:
    attempt_box: dict[str, Any] = {}
    try:
        result = _run_segment_impl(
            campaign_path=campaign_path,
            authorization_path=authorization_path,
            segment_name=segment_name,
            work=work,
            records_path=records_path,
            attempt_box=attempt_box,
        )
    except BaseException:
        if "attempt" in attempt_box:
            finish_campaign_attempt(attempt_box["attempt"], "ABORTED")
        raise
    if "attempt" in attempt_box:
        finish_campaign_attempt(attempt_box["attempt"], "COMPLETED")
    return result


def synthetic_command(
    output: Path, sleep_ms: float, child_ms: float | None = None
) -> list[str]:
    command = [
        str(PYTHON_EXECUTABLE),
        str(SYNTHETIC_TARGET),
        "render",
        "--output",
        str(output),
        "--sleep-ms",
        str(sleep_ms),
    ]
    if child_ms is not None:
        command.extend(["--spawn-child-ms", str(child_ms)])
    return command


def synthetic_contract() -> dict[str, Any]:
    return {
        "width": 4,
        "height": 4,
        "samples_per_pixel": 3,
        "bits_per_sample": 16,
        "icc_sha256": sha256_bytes(DEFAULT_ICC),
    }


def synthetic_invocation(
    *,
    work: Path,
    scenario: str,
    arm: str,
    repetition: int,
    position: int,
    sleep_ms: float,
    child_ms: float | None = None,
) -> dict[str, Any]:
    tag = f"{scenario}-r{repetition}-p{position}-{arm}"
    run_root = work / tag
    output = run_root / "master.tiff"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    frozen_paths = [PYTHON_EXECUTABLE, SYNTHETIC_TARGET.resolve(strict=True)]
    expected_hashes = {path: sha256_file(path) for path in frozen_paths}
    with ReadOnlyFileLocks(frozen_paths):
        if any(sha256_file(path) != digest for path, digest in expected_hashes.items()):
            raise RuntimeError("synthetic commission artifact changed before launch")
        record = run_timed_invocation(
            argv=synthetic_command(output, sleep_ms, child_ms),
            cwd=LANE_ROOT,
            env=env,
            declared_environment={"PYTHONDONTWRITEBYTECODE": "1"},
            output_path=output,
            invocation_manifest_path=run_root / "invocation-manifest.json",
            stdout_path=run_root / "stdout.log",
            stderr_path=run_root / "stderr.log",
            output_contract=synthetic_contract(),
            run_identity={
                "evidence_tag": "SYNTHETIC_COMMISSIONING_ONLY",
                "scenario": scenario,
                "arm": arm,
                "phase": "warmup" if repetition == 0 else "scored",
                "repetition": repetition,
                "position": position,
                "known_sleep_seconds": (
                    child_ms / 1000.0 if child_ms is not None else sleep_ms / 1000.0
                ),
            },
            required_stages=SYNTHETIC_STAGES,
            numeric_stage_timings_required=SYNTHETIC_STAGES,
            gpu_config={"kind": "synthetic-zero", "source": "synthetic-zero"},
            child_expected=child_ms is not None,
        )
        if any(sha256_file(path) != digest for path, digest in expected_hashes.items()):
            raise RuntimeError("synthetic commission artifact changed during launch")
    if (
        Path(record["process_tree"]["root_image"]["path"]).resolve(strict=True)
        != PYTHON_EXECUTABLE
    ):
        raise RuntimeError("synthetic commission launched an unexpected interpreter")
    return record


def run_paired_commission(
    *,
    work: Path,
    scenario: str,
    sleeps_ms: dict[str, float],
) -> dict[str, Any]:
    settings = ["A", "B"]
    schedule = alternating_schedule(settings, repetitions=6)
    records: list[dict[str, Any]] = []
    for row in schedule:
        records.append(
            synthetic_invocation(
                work=work,
                scenario=scenario,
                arm=row["setting_id"],
                repetition=int(row["repetition"]),
                position=int(row["position"]),
                sleep_ms=sleeps_ms[row["setting_id"]],
            )
        )
    scored = [record for record in records if record["phase"] == "scored"]
    by_repetition: dict[int, dict[str, float]] = defaultdict(dict)
    for record in scored:
        by_repetition[int(record["repetition"])][record["arm"]] = float(
            record["wall_seconds"]
        )
    differences = [
        by_repetition[repetition]["B"] - by_repetition[repetition]["A"]
        for repetition in sorted(by_repetition)
    ]
    interval = paired_mean_interval(differences)
    schedule_rows = [
        {
            "phase": record["phase"],
            "repetition": record["repetition"],
            "direction": (
                "forward"
                if int(record["repetition"]) % 2 or int(record["repetition"]) == 0
                else "reverse"
            ),
            "position": record["position"],
            "setting_id": record["arm"],
            "accepted": record["accepted"],
            "pair_complete": True,
        }
        for record in records
    ]
    schedule_guard = require_guard(
        "G13-schedule-complete",
        {
            "settings": settings,
            "repetitions": 6,
            "records": schedule_rows,
        },
    )
    return {
        "arms": {
            "A": {
                "definition": f"synthetic_target sleep_ms={sleeps_ms['A']}",
                "scored_wall_seconds": [
                    by_repetition[repetition]["A"]
                    for repetition in sorted(by_repetition)
                ],
            },
            "B": {
                "definition": f"synthetic_target sleep_ms={sleeps_ms['B']}",
                "scored_wall_seconds": [
                    by_repetition[repetition]["B"]
                    for repetition in sorted(by_repetition)
                ],
            },
        },
        "held_fixed": [
            "Python executable",
            "synthetic target bytes",
            "4x4 uint16 RGB TIFF payload",
            "ICC",
            "working volume",
            "finalization and hash path",
            "six alternating sweeps",
        ],
        "only_difference": (
            "none; output paths are per-run necessities"
            if sleeps_ms["A"] == sleeps_ms["B"]
            else f"arm B has {(sleeps_ms['B'] - sleeps_ms['A']) / 1000.0:.6f} "
            "seconds of planted in-process sleep"
        ),
        "paired_differences_seconds_b_minus_a": differences,
        "paired_interval": interval,
        "arm_a_dispersion": describe(
            by_repetition[repetition]["A"] for repetition in sorted(by_repetition)
        ),
        "arm_b_dispersion": describe(
            by_repetition[repetition]["B"] for repetition in sorted(by_repetition)
        ),
        "schedule_guard": schedule_guard.to_json(),
        "maximum_single_invocation_seconds": max(
            float(record["wall_seconds"]) for record in records
        ),
    }


def commission(output: Path, work: Path, formal_scorecard_control: bool) -> int:
    output = output.resolve()
    work = work.resolve()
    load_contract()
    require_guard(
        "G01-owned-output",
        {"path": str(work), "lane_root": str(LANE_ROOT)},
    )
    require_guard(
        "G01-owned-output",
        {"path": str(output), "lane_root": str(LANE_ROOT)},
    )
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    null = run_paired_commission(
        work=work,
        scenario="flat-null",
        sleeps_ms={"A": 4.0, "B": 4.0},
    )
    null_interval = null["paired_interval"]
    null_pass = (
        null_interval["covers_no_difference"]
        and null["maximum_single_invocation_seconds"] < 1.0
    )
    plant_seconds = 1.0 if formal_scorecard_control else 0.08
    planted = run_paired_commission(
        work=work,
        scenario="planted-effect",
        sleeps_ms={"A": 4.0, "B": 4.0 + plant_seconds * 1000.0},
    )
    planted_interval = planted["paired_interval"]
    plant_estimate = float(planted_interval["estimate_seconds"])
    plant_pass = (
        plant_estimate > 0.0
        and abs(plant_estimate - plant_seconds) <= 0.05
        and float(planted_interval["lower_seconds"])
        <= plant_seconds
        <= float(planted_interval["upper_seconds"])
        and not planted_interval["covers_no_difference"]
        and (
            formal_scorecard_control
            or planted["maximum_single_invocation_seconds"] < 1.0
        )
    )
    async_record = synthetic_invocation(
        work=work,
        scenario="async-child",
        arm="child-writer",
        repetition=1,
        position=0,
        sleep_ms=0.0,
        child_ms=75.0,
    )
    child_tail = (
        int(async_record["process_drained_qpc_ticks"])
        - int(async_record["process_tree"]["root_exit_qpc_ticks"])
    ) / int(async_record["qpc_frequency"])
    async_pass = (
        async_record["process_tree"]["process_count_total"] >= 2
        and child_tail >= 0.04
        and async_record["finalized_qpc_ticks"]
        >= async_record["process_drained_qpc_ticks"]
        and async_record["wall_seconds"] < 1.0
    )
    status = "PASS" if null_pass and plant_pass and async_pass else "FAIL"
    result = {
        "schema": (
            "m153-formal-commission-v1"
            if formal_scorecard_control
            else "m153-development-commission-v1"
        ),
        "evidence_tag": (
            "VERIFIED_SYNTHETIC_FORMAL_CONTROL"
            if formal_scorecard_control
            else "VERIFIED_SYNTHETIC_DEVELOPMENT_ONLY"
        ),
        "generated_utc": utc_now(),
        "host": {
            "node": platform.node(),
            "platform": platform.platform(),
            "python": sys.version,
        },
        "runtime": {
            "python_executable": {
                "path": str(PYTHON_EXECUTABLE),
                "sha256": sha256_file(PYTHON_EXECUTABLE),
            }
        },
        "contract": contract_hash(),
        "source_bindings": {
            path.name: {
                "path": str(path.resolve()),
                "sha256": sha256_file(path),
            }
            for path in COMMISSION_SOURCE_PATHS
        },
        "scope": (
            "Scorecard-required one-second synthetic control. This is not an M11 "
            "capture timing measurement."
            if formal_scorecard_control
            else "Sub-second synthetic commissioning only. This is not an M11 "
            "timing measurement and contains no capture output."
        ),
        "flat_null": {
            **null,
            "decision": "NO_DETECTED_DIFFERENCE" if null_pass else "FAIL",
            "pass": null_pass,
        },
        "planted_effect": {
            **planted,
            "planted_seconds": plant_seconds,
            "tolerance_seconds": 0.05,
            "recovered_seconds": plant_estimate,
            "pass": plant_pass,
        },
        "asynchronous_child": {
            "planted_child_delay_seconds": 0.075,
            "root_exit_to_tree_drain_seconds": child_tail,
            "process_count_total": async_record["process_tree"]["process_count_total"],
            "wall_seconds": async_record["wall_seconds"],
            "output_sha256": async_record["output"]["output_sha256"],
            "manifest_sha256": async_record["invocation_manifest"]["sha256"],
            "pass": async_pass,
        },
        "formal_scorecard_control": (
            {
                "status": "PASS" if plant_pass else "FAIL",
                "required_plant_seconds": 1.0,
                "observed_plant_seconds": plant_estimate,
                "tolerance_seconds": 0.05,
            }
            if formal_scorecard_control
            else {
                "status": "NOT_RUN",
                "required_plant_seconds": 1.0,
                "tolerance_seconds": 0.05,
                "reason": (
                    "M153 was ordered to run only sub-second synthetic workloads "
                    "while M139 owns the timing host."
                ),
            }
        ),
        "flat_null_pass": null_pass,
        "async_child_pass": async_pass,
        "formal_plant_seconds": 1.0 if formal_scorecard_control else None,
        "observed_plant_seconds": (
            plant_estimate if formal_scorecard_control else None
        ),
        "real_timing_authorized": False,
        "status": status,
    }
    write_json(output, result)
    print(
        json.dumps(
            {
                "status": status,
                "null_seconds": null_interval["estimate_seconds"],
                "null_ci_seconds": [
                    null_interval["lower_seconds"],
                    null_interval["upper_seconds"],
                ],
                "plant_seconds": plant_estimate,
                "plant_ci_seconds": [
                    planted_interval["lower_seconds"],
                    planted_interval["upper_seconds"],
                ],
                "async_tail_seconds": child_tail,
            },
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


def qualified_mode_ids(
    quality_path: Path | None,
) -> tuple[dict[str, set[str]], dict[str, Any]]:
    if quality_path is None:
        return {quality_cell_id(*cell): set() for cell in QUALITY_CELLS}, {
            "status": "UNMEASURED",
            "reason": "no quality manifest supplied",
        }
    result = validate_quality_manifest(quality_path)
    return {
        cell_id: set(modes)
        for cell_id, modes in result["qualified_modes_by_cell"].items()
    }, result


def group_scored(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str, int, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("accepted") is True and record.get("phase") == "scored":
            groups[
                (
                    str(record.get("segment")),
                    str(record.get("stack_id")),
                    int(record.get("count", -1)),
                    str(record.get("setting_id")),
                )
            ].append(record)
    return groups


def setting_signature_consistent(
    records: list[dict[str, Any]],
    *,
    role: str,
    counts: tuple[int, ...],
    mode_id: str | None = None,
    workers: int | None = None,
) -> bool:
    """Require one frozen setting id/hash for a role and mode at every count."""

    signatures: set[tuple[Any, Any]] = set()
    seen_counts: set[int] = set()
    for record in records:
        if (
            record.get("role") != role
            or (mode_id is not None and record.get("mode_id") != mode_id)
            or (workers is not None and int(record.get("workers", -1)) != workers)
        ):
            continue
        count = record.get("count")
        if count not in counts:
            continue
        signatures.add((record.get("setting_id"), record.get("settings_sha256")))
        seen_counts.add(count)
    return seen_counts == set(counts) and len(signatures) == 1


def record_identity_matches(
    record: dict[str, Any],
    invocation_identity: dict[str, Any],
    *,
    campaign_sha256: str,
    authorization_sha256: str,
    measured_commit: str,
) -> bool:
    return (
        all(
            invocation_identity.get(field) == record.get(field)
            for field in RUN_IDENTITY_FIELDS
        )
        and record.get("campaign_sha256") == campaign_sha256
        and record.get("authorization_sha256") == authorization_sha256
        and record.get("contract_sha256") == sha256_file(CONTRACT_PATH)
        and record.get("measured_commit") == measured_commit
        and isinstance(record.get("campaign_attempt_id"), str)
        and bool(record["campaign_attempt_id"])
    )


def measurement_receipt_valid(record: dict[str, Any]) -> bool:
    try:
        reference = record["measurement_receipt"]
        path = Path(reference["path"]).resolve(strict=True)
        if (
            not path_is_within(path, LANE_ROOT)
            or sha256_file(path) != reference["sha256"]
        ):
            return False
        record_without_receipt = dict(record)
        record_without_receipt.pop("measurement_receipt")
        return read_json(path) == {
            "schema": "m153-measurement-receipt-v1",
            "record": record_without_receipt,
        }
    except (KeyError, OSError, TypeError, ValueError):
        return False


def record_artifacts_intact(record: dict[str, Any]) -> bool:
    try:
        if (
            record.get("schema") != "m153-run-record-v1"
            or record.get("evidence_tag") != "MEASURED"
            or record.get("accepted") is not True
        ):
            return False
        output_path = Path(record["output"]["path"]).resolve(strict=True)
        manifest_path = Path(record["invocation_manifest"]["path"]).resolve(strict=True)
        measurement_receipt_path = Path(record["measurement_receipt"]["path"]).resolve(
            strict=True
        )
        if (
            not path_is_within(output_path, LANE_ROOT)
            or not path_is_within(
                manifest_path,
                LANE_ROOT,
            )
            or not path_is_within(measurement_receipt_path, LANE_ROOT)
        ):
            return False
        if not measurement_receipt_valid(record):
            return False
        artifacts = [
            read_artifact_binding(
                output_path,
                record["output"]["output_sha256"],
            ),
            read_artifact_binding(
                manifest_path,
                record["invocation_manifest"]["sha256"],
            ),
            read_artifact_binding(
                measurement_receipt_path,
                record["measurement_receipt"]["sha256"],
            ),
            *[
                read_artifact_binding(
                    Path(binding["path"]),
                    binding["expected_sha256"],
                )
                for binding in record["artifact_bindings"]
            ],
        ]
        require_guard("G04-artifact-binding", {"artifacts": artifacts})
        bound_hashes = {binding["actual_sha256"] for binding in artifacts}
        if not {
            record["campaign_sha256"],
            record["authorization_sha256"],
            record["contract_sha256"],
            record["input_manifest_sha256"],
        }.issubset(bound_hashes):
            return False
        campaign_candidates = [
            Path(binding["path"])
            for binding in artifacts
            if binding["actual_sha256"] == record["campaign_sha256"]
        ]
        if len(campaign_candidates) != 1:
            return False
        campaign = read_json(campaign_candidates[0])
        validate_frozen_campaign(campaign)
        authorization_candidates = []
        for binding in artifacts:
            if binding["actual_sha256"] != record["authorization_sha256"]:
                continue
            candidate_path = Path(binding["path"]).resolve(strict=True)
            try:
                candidate = read_json(candidate_path)
            except (OSError, TypeError, ValueError):
                continue
            if candidate.get("schema") == "m153-real-run-authorization-v1":
                authorization_candidates.append(candidate_path)
        if len(authorization_candidates) != 1:
            return False
        authorization = validate_authorization(
            campaign_candidates[0],
            campaign,
            authorization_candidates[0],
        )
        commission = read_json(repository_path(authorization["commission"]["path"]))
        contract_candidates = [
            Path(binding["path"]).resolve(strict=True)
            for binding in artifacts
            if binding["actual_sha256"] == record["contract_sha256"]
        ]
        if contract_candidates != [CONTRACT_PATH.resolve(strict=True)]:
            return False
        segment = campaign.get("segments", {}).get(record.get("segment"))
        if not isinstance(segment, dict):
            return False
        cells = [
            cell
            for cell in segment.get("cells", [])
            if cell.get("stack_id") == record.get("stack_id")
            and int(cell.get("count", -1)) == int(record.get("count", -1))
            and cell.get("input_manifest_sha256") == record.get("input_manifest_sha256")
            and record.get("setting_id") in cell.get("settings", [])
        ]
        expected_cache_state = (
            "WARM"
            if segment.get("cache_state") == "COLD_RESET"
            and record.get("pair_member") == "warm"
            else segment.get("cache_state")
        )
        if len(cells) != 1 or expected_cache_state != record.get("conditions", {}).get(
            "cache_state"
        ):
            return False
        cell = cells[0]
        current_input_content_sha256 = verify_cell_input_content(
            cell,
            segment_name=str(record["segment"]),
        )
        input_verification = record.get("input_verification", {})
        run_root = manifest_path.parent
        input_snapshot_dir = (run_root / "input").resolve(strict=True)
        snapshot_input_content_sha256 = verify_cell_input_content(
            cell,
            segment_name=str(record["segment"]),
            input_dir_override=input_snapshot_dir,
        )
        expected_snapshot_files = [
            str(row["name"])
            for row in read_json(repository_path(cell["input_manifest_path"]))["files"][
                : int(cell["count"])
            ]
        ]
        if (
            current_input_content_sha256 != record.get("input_content_sha256")
            or snapshot_input_content_sha256 != record.get("input_content_sha256")
            or input_verification.get("content_sha256")
            != record.get("input_content_sha256")
            or input_verification.get("snapshot_path") != str(input_snapshot_dir)
            or input_verification.get("snapshot_files") != expected_snapshot_files
            or input_verification.get("write_and_delete_locks_held_during_timing")
            is not True
            or input_verification.get("locked_artifacts_preflight_verified") is not True
            or input_verification.get("locked_artifacts_postflight_verified")
            is not True
            or int(input_verification.get("qpc_frequency", -1))
            != int(record.get("qpc_frequency", -2))
            or int(input_verification.get("preflight_completed_qpc_ticks", -1))
            > int(record.get("started_qpc_ticks", -1))
            or int(input_verification.get("postflight_started_qpc_ticks", -1))
            < int(record.get("finalized_qpc_ticks", -1))
            or int(input_verification.get("postflight_completed_qpc_ticks", -1))
            < int(input_verification.get("postflight_started_qpc_ticks", -1))
        ):
            return False
        setting = campaign.get("settings", {}).get(record.get("setting_id"))
        if (
            not isinstance(setting, dict)
            or setting.get("role") != record.get("role")
            or setting.get("mode_id") != record.get("mode_id")
            or int(setting.get("workers", 16)) != int(record.get("workers", -1))
            or setting.get("settings_sha256") != record.get("settings_sha256")
            or object_sha256(setting.get("output_contract"))
            != record.get("output_contract_sha256")
        ):
            return False
        setting_artifacts = setting_artifact_guard(setting)
        host_artifacts = validate_host_instruments(campaign)["artifact_bindings"]
        execution_artifacts = [*setting_artifacts, *host_artifacts]
        if segment.get("cache_state") == "COLD_RESET":
            cold_provider = segment["cold_reset_provider"]
            execution_artifacts.append(
                read_artifact_binding(
                    repository_path(cold_provider["path"]),
                    cold_provider["sha256"],
                )
            )
        if record.get("segment") == "live":
            execution_artifacts.append(
                read_artifact_binding(LIVE_REPLAY, sha256_file(LIVE_REPLAY))
            )
            execution_artifacts.append(
                read_artifact_binding(
                    Path(commission["runtime"]["python_executable"]["path"]),
                    commission["runtime"]["python_executable"]["sha256"],
                )
            )
        expected_execution_locks = {
            str(Path(binding["path"]).resolve(strict=True)): binding["actual_sha256"]
            for binding in execution_artifacts
        }
        recorded_binding_map = {
            str(Path(binding["path"]).resolve(strict=True)): binding["actual_sha256"]
            for binding in record["artifact_bindings"]
        }
        locked_rows = input_verification.get("locked_artifacts", [])
        locked_map = {
            str(Path(binding["path"]).resolve(strict=True)): binding["sha256"]
            for binding in locked_rows
        }
        if (
            len(locked_map) != len(locked_rows)
            or not set(expected_execution_locks).issubset(locked_map)
            or any(
                locked_map[path] != digest
                for path, digest in expected_execution_locks.items()
            )
            or any(
                recorded_binding_map.get(path) != digest
                for path, digest in locked_map.items()
            )
            or (
                record.get("segment") in {"comparative-cold", "product-cold"}
                and any(
                    row.get("preflight_read_mode") != "WINDOWS_NO_BUFFERING"
                    for row in locked_rows
                )
            )
        ):
            return False
        invocation = read_json(manifest_path)
        expected_tag = (
            f"{record['segment']}-{record['stack_id']}-n{record['count']}-"
            f"r{record['repetition']}-{record['position']}-{record['setting_id']}"
            + (
                f"-{record['pair_member']}"
                if record.get("pair_member") in {"cold", "warm"}
                else ""
            )
        )
        if (
            run_root.name != expected_tag
            or run_root.parent.name != "runs"
            or output_path != (run_root / "master.tiff").resolve(strict=True)
            or measurement_receipt_path
            != (run_root / "measurement-receipt.json").resolve(strict=True)
        ):
            return False
        private = {name: run_root / name for name in ("temp", "cache", "warpmap")}
        values = {
            "output": str(output_path),
            "input_dir": str(input_snapshot_dir),
            "count": int(cell["count"]),
            "workers": int(setting.get("workers", 16)),
            "acceleration_mode": setting.get("settings_payload", {}).get(
                "acceleration_mode",
                "",
            ),
            "temp": str(private["temp"]),
            "cache": str(private["cache"]),
            "warpmap": str(private["warpmap"]),
            "run_root": str(run_root.resolve()),
            "spool": str((run_root / "spool").resolve()),
            "live_marker": str((run_root / "live-epoch.json").resolve()),
        }
        _expected_env, expected_declared = clean_child_environment(
            setting.get("environment", {}),
            private,
        )
        expected_cwd = repository_path(setting.get("cwd", ROOT)).resolve(strict=True)
        if record.get("segment") == "live":
            replay_spec_path = run_root / "live-replay.json"
            stacker_cwd = repository_path(
                setting["live_replay"].get("stacker_cwd", ROOT)
            ).resolve(strict=True)
            expected_stacker_argv = expand_argv(
                setting["live_replay"]["stacker_argv"],
                values,
                cwd=stacker_cwd,
            )
            expected_stacker_argv = canonicalize_command_file_arguments(
                expected_stacker_argv,
                cwd=stacker_cwd,
            )
            expected_frames = [
                {
                    **frame,
                    "staged_path": str(
                        input_snapshot_dir / Path(frame["staged_path"]).name
                    ),
                }
                for frame in cell["frames"]
            ]
            expected_replay = {
                "schema": "m153-live-replay-v1",
                "signed_acquisition_trace_verified": True,
                "frames": expected_frames,
                "spool_dir": values["spool"],
                "marker_path": values["live_marker"],
                "allowed_stacker_directories": [
                    values[name] for name in ("spool", "temp", "cache", "warpmap")
                ],
                "cadence_manifest": cell["cadence_manifest"],
                "native_input_manifest": {
                    "path": cell["input_manifest_path"],
                    "sha256": cell["input_manifest_sha256"],
                },
                "stacker_argv": expected_stacker_argv,
                "stacker_cwd": str(stacker_cwd),
            }
            if read_json(replay_spec_path) != expected_replay:
                return False
            expected_argv = [
                str(PYTHON_EXECUTABLE),
                str(LIVE_REPLAY.resolve(strict=True)),
                "--spec",
                str(replay_spec_path.resolve(strict=True)),
            ]
        else:
            expected_argv = expand_argv(
                setting["argv"],
                values,
                cwd=expected_cwd,
            )
            expected_argv = canonicalize_command_file_arguments(
                expected_argv,
                cwd=expected_cwd,
            )
        identity = invocation.get("run_identity", {})
        if (
            not record_identity_matches(
                record,
                identity,
                campaign_sha256=sha256_file(campaign_candidates[0]),
                authorization_sha256=sha256_file(authorization_candidates[0]),
                measured_commit=campaign["measured_commit"],
            )
            or invocation.get("schema") != "m153-invocation-manifest-v1"
            or invocation.get("argv") != expected_argv
            or invocation.get("argv") != record.get("argv")
            or invocation.get("cwd") != str(expected_cwd)
            or invocation.get("declared_environment") != expected_declared
            or invocation.get("qpc_frequency") != record.get("qpc_frequency")
            or invocation.get("process_started_qpc_ticks")
            != record.get("started_qpc_ticks")
            or invocation.get("process_drained_qpc_ticks")
            != record.get("process_drained_qpc_ticks")
            or invocation.get("process_tree") != record.get("process_tree")
            or invocation.get("output") != record.get("output")
            or invocation.get("stage_banners")
            != record.get("telemetry", {}).get("stage_banners")
            or invocation.get("stage_measurements")
            != record.get("telemetry", {}).get("stage_measurements")
            or invocation.get("gpu", {}).get("source")
            != record.get("telemetry", {}).get("gpu_source")
            or invocation.get("gpu", {}).get("samples", [])
            != record.get("telemetry", {}).get("hardware_samples", [])[
                : len(invocation.get("gpu", {}).get("samples", []))
            ]
        ):
            return False
        for stream in ("stdout", "stderr"):
            stream_path = Path(invocation[stream]["path"]).resolve(strict=True)
            if (
                not path_is_within(stream_path, LANE_ROOT)
                or sha256_file(stream_path) != invocation[stream]["sha256"]
            ):
                return False
        log_text = (
            Path(invocation["stdout"]["path"]).read_text(
                encoding="utf-8",
                errors="replace",
            )
            + "\n"
            + Path(invocation["stderr"]["path"]).read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
        observed_stage_measurements = stage_measurements(log_text)
        observed_stage_banners = sorted(
            {row["stage"] for row in observed_stage_measurements}
        )
        if (
            invocation.get("stage_measurements") != observed_stage_measurements
            or invocation.get("stage_banners") != observed_stage_banners
            or record.get("telemetry", {}).get("required_stages")
            != setting.get("required_stages")
            or record.get("telemetry", {}).get("numeric_stage_timings_required")
            != setting.get(
                "numeric_stage_timings_required",
                setting.get("required_stages"),
            )
        ):
            return False
        output_witness = tiff_witness(output_path, setting["output_contract"])
        if (
            output_witness.get("tiff_valid") is not True
            or output_witness != record.get("output")
            or output_witness != invocation.get("output")
            or invocation.get("output_flush_succeeded") is not True
        ):
            return False
        root_image = invocation.get("process_tree", {}).get("root_image", {})
        expected_root_path = Path(expected_argv[0]).resolve(strict=True)
        process_lifetimes = invocation.get("process_tree", {}).get(
            "process_lifetimes",
            [],
        )
        if (
            Path(root_image.get("path", "")).resolve(strict=True) != expected_root_path
            or root_image.get("sha256") != sha256_file(expected_root_path)
            or any(
                not row.get("image_path") or not _hash_text(row.get("image_sha256"))
                for row in process_lifetimes
            )
            or not process_images_match_bound_artifacts(
                invocation.get("process_tree", {}),
                locked_rows,
            )
        ):
            return False
        candidate_binary_path = repository_path(setting["binary_path"]).resolve(
            strict=True
        )
        if record.get("segment") == "live":
            process_images = {
                str(Path(row["image_path"]).resolve(strict=True))
                for row in process_lifetimes
                if row.get("image_path")
            }
            if str(candidate_binary_path) not in process_images:
                return False
        elif expected_root_path != candidate_binary_path:
            return False
        frequency = int(record["qpc_frequency"])
        started = int(record["started_qpc_ticks"])
        drained = int(record["process_drained_qpc_ticks"])
        finalized = int(record["finalized_qpc_ticks"])
        wall = (finalized - started) / frequency
        if (
            finalized < drained
            or not math.isclose(
                float(record["wall_seconds"]),
                wall,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            or not math.isclose(
                float(record["telemetry"]["wall_seconds"]),
                wall,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            return False
        finalization = record["finalization"]
        if (
            finalization.get("output_sha256") != record["output"]["output_sha256"]
            or finalization.get("pixel_sha256") != record["output"]["pixel_sha256"]
            or finalization.get("manifest_sha256")
            != record["invocation_manifest"]["sha256"]
            or finalization.get("qpc_frequency") != frequency
            or finalization.get("process_drained_qpc_ticks") != drained
            or finalization.get("finalized_qpc_ticks") != finalized
        ):
            return False
        process_payload = {
            **record["process_tree"],
            "child_expected": False,
        }
        expected_guards = {
            "G09-process-tree-drained": evaluate_guard(
                "G09-process-tree-drained",
                process_payload,
            ),
            "G10-deliverable-finalized": evaluate_guard(
                "G10-deliverable-finalized",
                finalization,
            ),
            "G11-telemetry-complete": evaluate_guard(
                "G11-telemetry-complete",
                record["telemetry"],
            ),
        }
        live_marker = invocation.get("live_marker")
        if live_marker is not None:
            marker_path = Path(live_marker["path"]).resolve(strict=True)
            if (
                not path_is_within(marker_path, LANE_ROOT)
                or sha256_file(marker_path) != live_marker["sha256"]
            ):
                return False
            expected_guards["G16-live-epoch"] = evaluate_guard(
                "G16-live-epoch",
                {
                    **live_marker,
                    "marker_qpc_frequency": live_marker.get("qpc_frequency"),
                    "qpc_frequency": frequency,
                    "process_started_qpc_ticks": started,
                    "finalized_qpc_ticks": finalized,
                    "latency_seconds": record["live_latency_seconds"],
                },
            )
        elif record.get("live_latency_seconds") is not None:
            return False
        recorded_guards = {row.get("guard_id"): row for row in record.get("guards", [])}
        if (
            set(recorded_guards) != set(expected_guards)
            or any(not result.passed for result in expected_guards.values())
            or any(
                recorded_guards[guard_id] != result.to_json()
                for guard_id, result in expected_guards.items()
            )
            or evaluate_guard(
                "G12-controlled-conditions",
                record["conditions"],
            ).to_json()
            != record["conditions"]["guard"]
            or not record["conditions"]["guard"]["passed"]
        ):
            return False
        cold_reset = record.get("cold_reset")
        if (segment["cache_state"] == "COLD_RESET") != (cold_reset is not None):
            return False
        if cold_reset is not None:
            receipt = cold_reset["receipt"]
            if (
                cold_reset["receipt_sha256"] != object_sha256(receipt)
                or receipt.get("provider_sha256")
                != cold_reset["provider"]["actual_sha256"]
                or not evaluate_guard(
                    "G15-cold-receipt",
                    {
                        "receipt": receipt,
                        "receipt_sha256": cold_reset["receipt_sha256"],
                        "previously_used_boot_ids": [],
                        "current_windows_boot_id": cold_reset["windows_boot_id"],
                        "position_key": cold_reset["position_key"],
                        "campaign_sha256": cold_reset["campaign_sha256"],
                    },
                ).passed
            ):
                return False
        return record.get("accepted") is True
    except (KeyError, OSError, TypeError, ValueError):
        return False


def complete_cell_records(
    records: list[dict[str, Any]],
    *,
    segment: str,
    stack_id: str,
    count: int,
    setting_id: str,
    role: str,
    workers: int | None = None,
    require_live: bool = False,
) -> list[dict[str, Any]] | None:
    matches = [
        record
        for record in records
        if record.get("segment") == segment
        and record.get("stack_id") == stack_id
        and int(record.get("count", -1)) == count
        and record.get("setting_id") == setting_id
        and record.get("role") == role
        and (workers is None or int(record.get("workers", -1)) == workers)
    ]
    warmups = [record for record in matches if record.get("phase") == "warmup"]
    scored = [record for record in matches if record.get("phase") == "scored"]
    if (
        len(matches) != 7
        or len(warmups) != 1
        or warmups[0].get("repetition") != 0
        or warmups[0].get("accepted") is not True
        or len(scored) != 6
        or sorted(int(record.get("repetition", -1)) for record in scored)
        != list(range(1, 7))
    ):
        return None
    if segment.endswith("-cold") and any(
        not record.get("cold_reset", {}).get("receipt_sha256") for record in matches
    ):
        return None
    if any(
        record.get("accepted") is not True
        or record.get("pair_complete") is not True
        or not record_artifacts_intact(record)
        or not record.get("guards")
        or not all(guard.get("passed") is True for guard in record.get("guards", []))
        or record.get("conditions", {}).get("guard", {}).get("passed") is not True
        for record in matches
    ):
        return None
    for record in scored:
        repetition = int(record["repetition"])
        expected_direction = "forward" if repetition % 2 else "reverse"
        if record.get("direction") != expected_direction:
            return None
        if require_live and (
            record.get("live_latency_seconds") is None
            or not any(
                guard.get("guard_id") == "G16-live-epoch"
                and guard.get("passed") is True
                for guard in record.get("guards", [])
            )
        ):
            return None
    if len({record.get("settings_sha256") for record in matches}) != 1:
        return None
    if len({record.get("input_manifest_sha256") for record in matches}) != 1:
        return None
    for field in (
        "campaign_sha256",
        "authorization_sha256",
        "contract_sha256",
        "measured_commit",
    ):
        if len({record.get(field) for record in matches}) != 1:
            return None
    return sorted(scored, key=lambda record: int(record["repetition"]))


def complete_alternating_schedule(
    records: list[dict[str, Any]],
    *,
    segment: str,
    stack_id: str,
    count: int,
    setting_ids: list[str],
) -> bool:
    selected = [
        record
        for record in records
        if record.get("segment") == segment
        and record.get("stack_id") == stack_id
        and int(record.get("count", -1)) == count
        and record.get("setting_id") in setting_ids
    ]
    ordered = sorted(
        selected,
        key=lambda record: int(
            record.get("started_qpc_ticks", record.get("started_qpc_ns", -1))
        ),
    )
    result = evaluate_guard(
        "G13-schedule-complete",
        {
            "settings": setting_ids,
            "repetitions": 6,
            "records": ordered,
        },
    )
    return result.passed


def complete_cold_pair_cell_records(
    records: list[dict[str, Any]],
    *,
    segment: str,
    stack_id: str,
    count: int,
    setting_id: str,
    role: str,
    workers: int | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]] | None:
    matches = [
        record
        for record in records
        if record.get("segment") == segment
        and record.get("stack_id") == stack_id
        and int(record.get("count", -1)) == count
        and record.get("setting_id") == setting_id
        and record.get("role") == role
        and (workers is None or int(record.get("workers", -1)) == workers)
    ]
    if len(matches) != 12 or any(
        record.get("phase") != "scored"
        or record.get("accepted") is not True
        or record.get("pair_complete") is not True
        or not record_artifacts_intact(record)
        or not record.get("guards")
        or not all(guard.get("passed") is True for guard in record["guards"])
        or record.get("conditions", {}).get("guard", {}).get("passed") is not True
        for record in matches
    ):
        return None
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for repetition in range(1, 7):
        pair_rows = [
            record
            for record in matches
            if int(record.get("repetition", -1)) == repetition
        ]
        if (
            len(pair_rows) != 2
            or {row.get("pair_member") for row in pair_rows} != {"cold", "warm"}
            or len({row.get("pair_id") for row in pair_rows}) != 1
        ):
            return None
        cold = next(row for row in pair_rows if row["pair_member"] == "cold")
        warm = next(row for row in pair_rows if row["pair_member"] == "warm")
        if (
            cold.get("cold_reset") != warm.get("cold_reset")
            or cold.get("conditions", {}).get("cache_state") != "COLD_RESET"
            or warm.get("conditions", {}).get("cache_state") != "WARM"
            or int(cold.get("started_qpc_ticks", -1))
            >= int(warm.get("started_qpc_ticks", -1))
            or Path(cold["invocation_manifest"]["path"]).parent
            == Path(warm["invocation_manifest"]["path"]).parent
            or any(
                cold.get(field) != warm.get(field)
                for field in (
                    "settings_sha256",
                    "input_manifest_sha256",
                    "input_content_sha256",
                    "output_contract_sha256",
                )
            )
        ):
            return None
        pairs.append((cold, warm))
    if (
        len(
            {
                str(cold.get("cold_reset", {}).get("windows_boot_id", ""))
                for cold, _warm in pairs
            }
        )
        != 6
    ):
        return None
    return pairs


def warmup_setting_order(
    records: list[dict[str, Any]],
    *,
    segment: str,
    stack_id: str,
    count: int,
    setting_ids: set[str],
) -> list[str]:
    positions = {}
    for setting_id in setting_ids:
        candidates = [
            int(record.get("position", -1))
            for record in records
            if record.get("segment") == segment
            and record.get("stack_id") == stack_id
            and int(record.get("count", -1)) == count
            and record.get("setting_id") == setting_id
            and record.get("phase") == "warmup"
        ]
        if len(candidates) != 1:
            return []
        positions[setting_id] = candidates[0]
    if sorted(positions.values()) != list(range(len(setting_ids))):
        return []
    return [
        setting_id
        for setting_id, _position in sorted(
            positions.items(),
            key=lambda item: item[1],
        )
    ]


def verdict(values: list[bool], complete: bool) -> str:
    if not complete:
        return "UNMEASURED"
    return "PASS" if all(values) else "FAIL"


def aggregate_verdict(values: list[str]) -> str:
    if "FAIL" in values:
        return "FAIL"
    if values and all(value == "PASS" for value in values):
        return "PASS"
    return "UNMEASURED"


def m11_publication_verdict(bars: dict[str, dict[str, Any]]) -> str:
    return aggregate_verdict(
        [
            bars.get("comparative", {}).get("verdict", "UNMEASURED"),
            bars.get("retained_m12_cross_worker_identity", {}).get(
                "verdict",
                "UNMEASURED",
            ),
        ]
    )


def all_timed_outputs_match_quality(
    rows: list[dict[str, Any]] | None,
    qualification: dict[str, Any],
) -> bool:
    if not rows:
        return False
    expected = (
        qualification.get("output_sha256"),
        qualification.get("pixel_sha256"),
    )
    return all(
        (
            row.get("output", {}).get("output_sha256"),
            row.get("output", {}).get("pixel_sha256"),
        )
        == expected
        for row in rows
    )


def cross_worker_byte_identity(by_worker: dict[str, dict[str, Any]]) -> bool:
    if set(by_worker) != {str(workers) for workers in WORKER_LADDER} or not all(
        cell.get("complete") is True for cell in by_worker.values()
    ):
        return False
    if not all(
        len(cell.get("output_sha256", [])) == 6
        and len(cell.get("pixel_sha256", [])) == 6
        and len(cell.get("settings_sha256", [])) == 1
        and len(cell.get("input_manifest_sha256", [])) == 1
        and len(cell.get("input_content_sha256", [])) == 1
        for cell in by_worker.values()
    ):
        return False
    canonical_index = CANONICAL_SCORED_REPETITION - 1
    output_hashes = {
        cell.get("output_sha256", [])[canonical_index] for cell in by_worker.values()
    }
    pixel_hashes = {
        cell.get("pixel_sha256", [])[canonical_index] for cell in by_worker.values()
    }
    settings_hashes = {cell["settings_sha256"][0] for cell in by_worker.values()}
    input_hashes = {cell["input_manifest_sha256"][0] for cell in by_worker.values()}
    input_content_hashes = {
        cell["input_content_sha256"][0] for cell in by_worker.values()
    }
    return (
        len(output_hashes) == 1
        and len(pixel_hashes) == 1
        and len(settings_hashes) == 1
        and len(input_hashes) == 1
        and len(input_content_hashes) == 1
    )


def summarize(
    records_path: Path,
    output: Path,
    quality_path: Path | None,
) -> int:
    records_path = records_path.resolve(strict=True)
    output = output.resolve()
    quality_path = quality_path.resolve(strict=True) if quality_path else None
    contract = load_contract()
    if (
        contract.get("m12_bridge", {}).get("canonical_scored_repetition")
        != CANONICAL_SCORED_REPETITION
    ):
        raise ValueError("contract does not freeze the canonical M12-S repetition")
    records = [
        parse_json_line(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    campaign_identity_complete = bool(records) and records_match_campaign_identity(
        records,
        {
            field: records[0].get(field)
            for field in (
                "campaign_sha256",
                "authorization_sha256",
                "contract_sha256",
                "measured_commit",
            )
        },
    )
    if campaign_identity_complete:
        campaign_identity_complete = records[0].get("contract_sha256") == sha256_file(
            CONTRACT_PATH
        )
    record_attempt_ids = {
        str(record.get("campaign_attempt_id"))
        for record in records
        if isinstance(record.get("campaign_attempt_id"), str)
        and bool(record["campaign_attempt_id"])
    }
    attempt_history = (
        campaign_attempt_history(
            str(records[0]["campaign_sha256"]),
            required_attempt_ids=record_attempt_ids,
            required_records_path=records_path,
        )
        if records and _hash_text(records[0].get("campaign_sha256"))
        else {
            "path": None,
            "exists": False,
            "row_count": 0,
            "completed_attempt_ids": [],
            "required_attempt_ids": sorted(record_attempt_ids),
            "records_paths": [],
            "required_records_path": str(records_path),
            "valid": False,
        }
    )
    campaign_identity_complete &= (
        len(record_attempt_ids) >= 1
        and all(
            record.get("campaign_attempt_id") in record_attempt_ids
            for record in records
        )
        and attempt_history["valid"]
    )
    quality_matches_campaign = False
    if campaign_identity_complete and quality_path is not None:
        try:
            campaign_bindings = [
                binding
                for binding in records[0].get("artifact_bindings", [])
                if binding.get("actual_sha256") == records[0].get("campaign_sha256")
            ]
            if len(campaign_bindings) == 1:
                campaign = read_json(
                    Path(campaign_bindings[0]["path"]).resolve(strict=True)
                )
                campaign_quality = campaign["quality_qualification"]
                quality_matches_campaign = repository_path(
                    campaign_quality["path"]
                ).resolve(strict=True) == quality_path and campaign_quality[
                    "sha256"
                ] == sha256_file(quality_path)
        except (KeyError, OSError, TypeError, ValueError):
            quality_matches_campaign = False
    campaign_identity_complete &= quality_matches_campaign
    groups = group_scored(records)
    qualified_by_cell, quality = qualified_mode_ids(quality_path)
    settings_meta: dict[str, dict[str, Any]] = {}
    for record in records:
        setting_id = str(record.get("setting_id"))
        candidate_meta = {
            "role": record.get("role"),
            "mode_id": record.get("mode_id"),
            "workers": record.get("workers"),
        }
        if setting_id in settings_meta and settings_meta[setting_id] != candidate_meta:
            raise ValueError(f"setting metadata changed within records: {setting_id}")
        settings_meta[setting_id] = candidate_meta

    group_stats = {
        "|".join(str(value) for value in key): describe(
            float(row["wall_seconds"]) for row in rows
        )
        for key, rows in groups.items()
    }
    comparative_rows: dict[str, Any] = {}
    comparative_passes: list[bool] = []
    comparative_minima: dict[str, dict[str, float]] = {}
    comparative_complete = campaign_identity_complete
    cross_worker_cells: dict[str, dict[str, Any]] = {}
    cross_worker_passes: list[bool] = []
    cross_worker_complete = campaign_identity_complete
    statistic_payloads: dict[str, dict[str, Any]] = {}
    statistic_guards: list[dict[str, Any]] = []
    for count, stack in ((33, "bee-1-cpl"), (105, "coffee-bean"), (299, "bee-1-cpl")):
        cell_id = quality_cell_id(stack, count)
        matching = {
            setting: rows
            for (segment, stack_id, cell_count, setting), rows in groups.items()
            if segment == "comparative-warm"
            and stack_id == stack
            and cell_count == count
        }
        strehl_ids_by_worker: dict[int, list[str]] = {
            workers: [
                setting
                for setting in matching
                if settings_meta[setting]["role"] == "strehl-common"
                and int(settings_meta[setting].get("workers", -1)) == workers
            ]
            for workers in WORKER_LADDER
        }
        strehl_ids = [
            setting
            for setting_ids in strehl_ids_by_worker.values()
            for setting in setting_ids
        ]
        comparator_ids_by_mode = {
            settings_meta[setting]["mode_id"]: setting
            for setting in matching
            if settings_meta[setting]["role"] == "comparator"
            and settings_meta[setting]["mode_id"]
            in qualified_by_cell.get(cell_id, set())
        }
        comparator_ids = [
            setting
            for setting in matching
            if settings_meta[setting]["role"] == "comparator"
            and settings_meta[setting]["mode_id"]
            in qualified_by_cell.get(cell_id, set())
        ]
        strehl_cells = {
            workers: (
                complete_cell_records(
                    records,
                    segment="comparative-warm",
                    stack_id=stack,
                    count=count,
                    setting_id=setting_ids[0],
                    role="strehl-common",
                    workers=workers,
                )
                if len(setting_ids) == 1
                else None
            )
            for workers, setting_ids in strehl_ids_by_worker.items()
        }
        strehl_cell_16 = strehl_cells[16]
        strehl_qualification = (
            quality.get("mode_results", {})
            .get(STREHL_QUALITY_MODE_ID, {})
            .get("cell_results", {})
            .get(cell_id, {})
        )
        strehl_timed_outputs_match_quality = all_timed_outputs_match_quality(
            strehl_cell_16,
            strehl_qualification,
        )
        by_worker: dict[str, dict[str, Any]] = {}
        all_output_sha256: set[str] = set()
        all_pixel_sha256: set[str] = set()
        for workers in WORKER_LADDER:
            rows = strehl_cells[workers]
            output_sha256 = [row["output"]["output_sha256"] for row in rows or []]
            pixel_sha256 = [row["output"]["pixel_sha256"] for row in rows or []]
            all_output_sha256.update(output_sha256)
            all_pixel_sha256.update(pixel_sha256)
            by_worker[str(workers)] = {
                "complete": rows is not None,
                "setting_id": (
                    strehl_ids_by_worker[workers][0]
                    if len(strehl_ids_by_worker[workers]) == 1
                    else None
                ),
                "settings_sha256": sorted(
                    {row.get("settings_sha256") for row in rows or []}
                ),
                "input_manifest_sha256": sorted(
                    {row.get("input_manifest_sha256") for row in rows or []}
                ),
                "input_content_sha256": sorted(
                    {row.get("input_content_sha256") for row in rows or []}
                ),
                "output_sha256": output_sha256,
                "pixel_sha256": pixel_sha256,
                "canonical_scored_repetition": CANONICAL_SCORED_REPETITION,
                "canonical_output_sha256": (
                    output_sha256[CANONICAL_SCORED_REPETITION - 1]
                    if len(output_sha256) == 6
                    else None
                ),
                "canonical_pixel_sha256": (
                    pixel_sha256[CANONICAL_SCORED_REPETITION - 1]
                    if len(pixel_sha256) == 6
                    else None
                ),
            }
        ladder_complete = all(rows is not None for rows in strehl_cells.values())
        count_identity_pass = ladder_complete and cross_worker_byte_identity(by_worker)
        cross_worker_complete &= ladder_complete
        cross_worker_passes.append(count_identity_pass)
        cross_worker_cells[str(count)] = {
            "verdict": verdict([count_identity_pass], ladder_complete),
            "track": "common-merge",
            "by_worker": by_worker,
            "canonical_scored_repetition": CANONICAL_SCORED_REPETITION,
            "distinct_canonical_output_sha256": sorted(
                {
                    cell["canonical_output_sha256"]
                    for cell in by_worker.values()
                    if cell["canonical_output_sha256"] is not None
                }
            ),
            "distinct_canonical_pixel_sha256": sorted(
                {
                    cell["canonical_pixel_sha256"]
                    for cell in by_worker.values()
                    if cell["canonical_pixel_sha256"] is not None
                }
            ),
            "all_scored_distinct_output_sha256_disclosure": sorted(all_output_sha256),
            "all_scored_distinct_pixel_sha256_disclosure": sorted(all_pixel_sha256),
        }
        comparator_cells = {
            setting: complete_cell_records(
                records,
                segment="comparative-warm",
                stack_id=stack,
                count=count,
                setting_id=setting,
                role="comparator",
            )
            for setting in comparator_ids
        }
        comparator_timed_outputs_match_quality: dict[str, bool] = {}
        for setting, rows in comparator_cells.items():
            mode_id = str(settings_meta[setting]["mode_id"])
            qualification = (
                quality.get("mode_results", {})
                .get(mode_id, {})
                .get("cell_results", {})
                .get(cell_id, {})
            )
            comparator_timed_outputs_match_quality[setting] = (
                all_timed_outputs_match_quality(
                    rows,
                    qualification,
                )
            )
        schedule_settings = warmup_setting_order(
            records,
            segment="comparative-warm",
            stack_id=stack,
            count=count,
            setting_ids=set(matching),
        )
        schedule_complete = bool(schedule_settings) and complete_alternating_schedule(
            records,
            segment="comparative-warm",
            stack_id=stack,
            count=count,
            setting_ids=schedule_settings,
        )
        exact_setting_set = set(matching) == set(strehl_ids + comparator_ids)
        cross_worker_complete &= schedule_complete and exact_setting_set
        cross_worker_cells[str(count)]["verdict"] = verdict(
            [count_identity_pass],
            ladder_complete and schedule_complete and exact_setting_set,
        )
        complete = (
            strehl_cell_16 is not None
            and ladder_complete
            and quality.get("envelope_complete_by_cell", {}).get(cell_id) is True
            and quality.get("strehl_qualified_by_cell", {}).get(cell_id) is True
            and settings_meta[strehl_ids_by_worker[16][0]].get("mode_id")
            == STREHL_QUALITY_MODE_ID
            and strehl_timed_outputs_match_quality
            and bool(qualified_by_cell.get(cell_id, set()))
            and set(comparator_ids_by_mode) == qualified_by_cell.get(cell_id, set())
            and len(comparator_ids_by_mode) == len(comparator_ids)
            and all(cell is not None for cell in comparator_cells.values())
            and all(comparator_timed_outputs_match_quality.values())
            and exact_setting_set
            and schedule_complete
        )
        comparative_complete &= complete
        if not complete:
            comparative_rows[str(count)] = {
                "status": "UNMEASURED",
                "reason": "missing six-run strehl or quality-qualified comparator cell",
            }
            continue
        if strehl_cell_16 is None:
            raise AssertionError("complete comparative cell lost its Strehl records")
        strehl_min = min(float(row["wall_seconds"]) for row in strehl_cell_16)
        comparator_minima = {
            setting: min(
                float(row["wall_seconds"]) for row in comparator_cells[setting] or []
            )
            for setting in comparator_ids
        }
        fastest = min(
            comparator_minima,
            key=lambda setting_id: (
                comparator_minima[setting_id],
                COMPARATOR_PRODUCT_IDS[str(settings_meta[setting_id]["mode_id"])],
                str(settings_meta[setting_id]["mode_id"]),
            ),
        )
        ratio = comparator_minima[fastest] / strehl_min
        row_pass = ratio >= 2.0
        comparative_passes.append(row_pass)
        comparative_minima[str(count)] = {
            "strehl": strehl_min,
            "comparator": comparator_minima[fastest],
        }
        comparative_rows[str(count)] = {
            "status": "PASS" if row_pass else "FAIL",
            "strehl_setting_id": strehl_ids_by_worker[16][0],
            "strehl_workers": 16,
            "strehl_mode_id": STREHL_QUALITY_MODE_ID,
            "strehl_all_timed_outputs_match_quality": (
                strehl_timed_outputs_match_quality
            ),
            "strehl_input_manifest_sha256": strehl_cell_16[0]["input_manifest_sha256"],
            "strehl_minimum_wall_seconds": strehl_min,
            "strehl_wall_seconds": [
                float(row["wall_seconds"]) for row in strehl_cell_16
            ],
            "selected_fastest_qualified_comparator": fastest,
            "comparator_minimum_wall_seconds": comparator_minima[fastest],
            "selected_comparator_all_timed_outputs_match_quality": (
                comparator_timed_outputs_match_quality[fastest]
            ),
            "strehl_throughput_ratio": ratio,
            "bar": 2.0,
            "formula": "comparator minimum wall / strehl minimum wall",
        }
        statistic_payloads[str(count)] = {
            "strehl_wall_seconds": [
                float(row["wall_seconds"]) for row in strehl_cell_16
            ],
            "qualified_comparator_wall_seconds": {
                setting: [
                    float(row["wall_seconds"])
                    for row in comparator_cells[setting] or []
                ]
                for setting in comparator_ids
            },
            "comparator_identity": {
                setting: {
                    "product_id": COMPARATOR_PRODUCT_IDS[
                        str(settings_meta[setting]["mode_id"])
                    ],
                    "mode_id": str(settings_meta[setting]["mode_id"]),
                }
                for setting in comparator_ids
            },
            "selected_fastest_comparator": fastest,
            "strehl_throughput_ratio": ratio,
        }
    comparative_complete &= setting_signature_consistent(
        records,
        role="strehl-common",
        counts=REGISTERED_COUNTS,
        workers=16,
    )
    for workers in WORKER_LADDER:
        cross_worker_complete &= setting_signature_consistent(
            records,
            role="strehl-common",
            counts=REGISTERED_COUNTS,
            workers=workers,
        )
    comparator_modes = {
        str(record.get("mode_id"))
        for record in records
        if record.get("segment") == "comparative-warm"
        and record.get("role") == "comparator"
    }
    for mode_id in comparator_modes:
        required_counts = tuple(
            count
            for count, stack in (
                (33, "bee-1-cpl"),
                (105, "coffee-bean"),
                (299, "bee-1-cpl"),
            )
            if mode_id in qualified_by_cell.get(quality_cell_id(stack, count), set())
        )
        comparative_complete &= bool(required_counts) and setting_signature_consistent(
            records,
            role="comparator",
            mode_id=mode_id,
            counts=required_counts,
        )
    pooled_ratio = (
        sum(row["comparator"] for row in comparative_minima.values())
        / sum(row["strehl"] for row in comparative_minima.values())
        if len(comparative_minima) == len(REGISTERED_COUNTS)
        else None
    )
    pooled_pass = pooled_ratio is not None and pooled_ratio >= 2.0
    comparative_complete &= pooled_ratio is not None
    comparative_passes.append(pooled_pass)
    if pooled_ratio is not None:
        statistic_guards.append(
            require_guard(
                "G20-aggregate-reduction",
                {
                    "statistic_kind": "comparative",
                    "capture_minima": {
                        count: {
                            "strehl_minimum_wall_seconds": row["strehl"],
                            "selected_comparator_minimum_wall_seconds": row[
                                "comparator"
                            ],
                        }
                        for count, row in comparative_minima.items()
                    },
                    "capture_ratios": {
                        count: row["comparator"] / row["strehl"]
                        for count, row in comparative_minima.items()
                    },
                    "pooled_ratio": pooled_ratio,
                    "all_bars_pass": (
                        all(
                            row["comparator"] / row["strehl"] >= 2.0
                            for row in comparative_minima.values()
                        )
                        and pooled_pass
                    ),
                },
            ).to_json()
        )

    def product_cells(role: str, segment: str = "product-warm") -> dict[str, Any]:
        cells: dict[str, Any] = {}
        for count, stack in (
            (33, "bee-1-cpl"),
            (105, "coffee-bean"),
            (299, "bee-1-cpl"),
        ):
            expected_workers = (
                16
                if role
                in {
                    "candidate-cpu",
                    "frozen-default-baseline",
                }
                else None
            )
            setting_ids = [
                setting
                for (
                    segment_id,
                    stack_id,
                    cell_count,
                    setting,
                ), _rows in groups.items()
                if segment_id == segment
                and stack_id == stack
                and cell_count == count
                and settings_meta[setting]["role"] == role
                and (
                    expected_workers is None
                    or int(settings_meta[setting].get("workers", -1))
                    == expected_workers
                )
            ]
            cell = (
                complete_cell_records(
                    records,
                    segment=segment,
                    stack_id=stack,
                    count=count,
                    setting_id=setting_ids[0],
                    role=role,
                    workers=expected_workers,
                )
                if len(setting_ids) == 1
                else None
            )
            if cell is None:
                cells[str(count)] = None
            else:
                walls = [float(row["wall_seconds"]) for row in cell]
                cells[str(count)] = {
                    "setting_id": setting_ids[0],
                    "input_manifest_sha256": next(
                        iter({row["input_manifest_sha256"] for row in cell})
                    ),
                    "wall_seconds": walls,
                    "minimum_wall_seconds": min(walls),
                    "minimum_seconds_per_frame": min(walls) / count,
                    "dispersion": describe(walls),
                    "baseline_frozen_before_candidate": all(
                        row.get("baseline_frozen_before_candidate") is True
                        for row in cell
                    ),
                }
        return cells

    cpu_cells = product_cells("candidate-cpu")
    hybrid_cells = product_cells("candidate-hybrid")
    baseline_cells = product_cells("frozen-default-baseline")
    cpu_complete = all(value is not None for value in cpu_cells.values())
    hybrid_complete = all(value is not None for value in hybrid_cells.values())
    baseline_complete = all(
        value is not None and value["baseline_frozen_before_candidate"] is True
        for value in baseline_cells.values()
    )
    cpu_complete &= campaign_identity_complete
    hybrid_complete &= campaign_identity_complete
    baseline_complete &= campaign_identity_complete
    cpu_complete &= setting_signature_consistent(
        records,
        role="candidate-cpu",
        counts=REGISTERED_COUNTS,
        workers=16,
    )
    hybrid_complete &= setting_signature_consistent(
        records,
        role="candidate-hybrid",
        counts=REGISTERED_COUNTS,
    )
    baseline_complete &= setting_signature_consistent(
        records,
        role="frozen-default-baseline",
        counts=REGISTERED_COUNTS,
    )
    product_schedule_complete = True
    for count, stack in ((33, "bee-1-cpl"), (105, "coffee-bean"), (299, "bee-1-cpl")):
        cells_for_count = (
            cpu_cells[str(count)],
            hybrid_cells[str(count)],
            baseline_cells[str(count)],
        )
        if any(cell is None for cell in cells_for_count):
            product_schedule_complete = False
            continue
        setting_ids = {
            str(cell["setting_id"]) for cell in cells_for_count if cell is not None
        }
        all_setting_ids = {
            str(record.get("setting_id"))
            for record in records
            if record.get("segment") == "product-warm"
            and record.get("stack_id") == stack
            and int(record.get("count", -1)) == count
        }
        if all_setting_ids != setting_ids:
            product_schedule_complete = False
        order = warmup_setting_order(
            records,
            segment="product-warm",
            stack_id=stack,
            count=count,
            setting_ids=setting_ids,
        )
        product_schedule_complete &= bool(order) and complete_alternating_schedule(
            records,
            segment="product-warm",
            stack_id=stack,
            count=count,
            setting_ids=order,
        )
    cpu_complete &= product_schedule_complete
    hybrid_complete &= product_schedule_complete
    baseline_complete &= product_schedule_complete
    cpu_checks = [
        value["minimum_seconds_per_frame"] <= 0.15
        for value in cpu_cells.values()
        if value is not None
    ]
    hybrid_checks = [
        value["minimum_seconds_per_frame"] <= 0.06
        for value in hybrid_cells.values()
        if value is not None
    ]
    baseline_ratios: dict[str, float] = {}
    if cpu_complete and baseline_complete:
        for count in ("33", "105", "299"):
            baseline_ratios[count] = (
                cpu_cells[count]["minimum_wall_seconds"]
                / baseline_cells[count]["minimum_wall_seconds"]
            )
    baseline_ok = bool(baseline_ratios) and all(
        ratio <= 2.0 for ratio in baseline_ratios.values()
    )
    if cpu_complete and baseline_complete:
        for count in ("33", "105", "299"):
            if count not in statistic_payloads:
                continue
            payload = {
                **statistic_payloads[count],
                "candidate_wall_seconds": cpu_cells[count]["wall_seconds"],
                "baseline_wall_seconds": baseline_cells[count]["wall_seconds"],
                "candidate_default_wall_ratio": baseline_ratios[count],
                "headline_statistic": "minimum_of_six",
                "dispersion_reported": True,
            }
            statistic_guards.append(
                require_guard("G14-statistic-direction", payload).to_json()
            )

    required_cold_cells: list[tuple[str, str, int, str, str, int | None]] = []
    for (segment_id, stack_id, count, setting), rows in groups.items():
        role = settings_meta[setting]["role"]
        if (
            count in REGISTERED_COUNTS
            and segment_id == "comparative-warm"
            and (
                role == "strehl-common"
                and int(settings_meta[setting].get("workers", -1)) == 16
                or (
                    role == "comparator"
                    and settings_meta[setting]["mode_id"]
                    in qualified_by_cell.get(
                        quality_cell_id(stack_id, count),
                        set(),
                    )
                )
            )
        ):
            required_cold_cells.append(
                (
                    "comparative",
                    stack_id,
                    count,
                    setting,
                    role,
                    16 if role == "strehl-common" else None,
                )
            )
        if (
            count in REGISTERED_COUNTS
            and segment_id == "product-warm"
            and role
            in {
                "candidate-cpu",
                "candidate-hybrid",
            }
        ):
            required_cold_cells.append(
                (
                    "product",
                    stack_id,
                    count,
                    setting,
                    role,
                    16 if role == "candidate-cpu" else None,
                )
            )
    cold_overheads: dict[str, dict[str, Any]] = {}
    cold_complete_by_arm = {
        arm: campaign_identity_complete
        and any(row[0] == arm for row in required_cold_cells)
        for arm in ("comparative", "product")
    }
    cold_boot_ids_by_arm: dict[str, list[str]] = {
        "comparative": [],
        "product": [],
    }
    for arm, stack, count, setting, role, workers in required_cold_cells:
        pairs = complete_cold_pair_cell_records(
            records,
            segment=f"{arm}-cold",
            stack_id=stack,
            count=count,
            setting_id=setting,
            role=role,
            workers=workers,
        )
        if pairs is None:
            cold_complete_by_arm[arm] = False
            continue
        key = "|".join((arm, stack, setting, str(count)))
        paired_differences = [
            float(warm["wall_seconds"]) * -1.0 + float(cold["wall_seconds"])
            for cold, warm in pairs
        ]
        reduction_guard = require_guard(
            "G20-aggregate-reduction",
            {
                "statistic_kind": "cold",
                "cold_wall_seconds": [
                    float(cold["wall_seconds"]) for cold, _warm in pairs
                ],
                "warm_wall_seconds": [
                    float(warm["wall_seconds"]) for _cold, warm in pairs
                ],
                "paired_cold_minus_warm_seconds": paired_differences,
                "maximum_seconds": max(paired_differences),
                "all_pairs_pass": all(value <= 20.0 for value in paired_differences),
            },
        )
        statistic_guards.append(reduction_guard.to_json())
        cold_overheads[key] = {
            "paired_cold_minus_warm_seconds": paired_differences,
            "maximum_seconds": max(paired_differences),
            "dispersion": describe(paired_differences),
            "all_pairs_pass": all(value <= 20.0 for value in paired_differences),
        }
        cold_boot_ids_by_arm[arm].extend(
            str(cold["cold_reset"]["windows_boot_id"]) for cold, _warm in pairs
        )
    all_cold_boot_ids = [
        boot_id for values in cold_boot_ids_by_arm.values() for boot_id in values
    ]
    if len(all_cold_boot_ids) != len(set(all_cold_boot_ids)):
        cold_complete_by_arm = {"comparative": False, "product": False}
    cold_schedule_groups: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for arm, stack, count, setting, _role, _workers in required_cold_cells:
        cold_schedule_groups[(arm, stack, count)].add(setting)
    for (arm, stack, count), setting_ids in cold_schedule_groups.items():
        # QPC values are not comparable across the reboots that separate cold
        # pairs. JSONL append order is the durable cross-boot campaign order.
        selected = [
            record
            for record in records
            if record.get("segment") == f"{arm}-cold"
            and record.get("stack_id") == stack
            and int(record.get("count", -1)) == count
            and record.get("setting_id") in setting_ids
        ]
        if not selected:
            cold_complete_by_arm[arm] = False
            continue
        schedule_result = evaluate_guard(
            "G13-schedule-complete",
            {
                "settings": sorted(
                    setting_ids,
                    key=lambda setting_id: min(
                        int(row.get("position", -1))
                        for row in selected
                        if row.get("setting_id") == setting_id
                        and int(row.get("repetition", -1)) == 1
                        and row.get("pair_member") == "cold"
                    ),
                ),
                "repetitions": 6,
                "schedule_kind": "cold-pairs",
                "records": selected,
            },
        )
        cold_complete_by_arm[arm] &= schedule_result.passed
    for arm in ("comparative", "product"):
        expected_cells = sum(row[0] == arm for row in required_cold_cells)
        observed_pair_members = sum(
            record.get("segment") == f"{arm}-cold"
            and record.get("phase") == "scored"
            and record.get("accepted") is True
            for record in records
        )
        observed_overheads = sum(key.startswith(f"{arm}|") for key in cold_overheads)
        cold_complete_by_arm[arm] &= (
            observed_overheads == expected_cells
            and observed_pair_members == expected_cells * 12
            and len(cold_boot_ids_by_arm[arm]) == expected_cells * 6
        )
    cold_bar_values = {
        key: value
        for key, value in cold_overheads.items()
        if key.startswith("product|")
    }
    cold_ok = (
        cold_complete_by_arm["product"]
        and len(cold_bar_values) == 6
        and all(value["all_pairs_pass"] for value in cold_bar_values.values())
    )
    comparative_cold_values = {
        key: value
        for key, value in cold_overheads.items()
        if key.startswith("comparative|")
    }

    live_setting_ids = sorted(
        {
            str(record.get("setting_id"))
            for record in records
            if record.get("segment") == "live"
            and record.get("stack_id") == "bee-1-cpl"
            and int(record.get("count", -1)) == 100
            and record.get("role") == "candidate-live"
        }
    )
    live_records = (
        complete_cell_records(
            records,
            segment="live",
            stack_id="bee-1-cpl",
            count=100,
            setting_id=live_setting_ids[0],
            role="candidate-live",
            require_live=True,
        )
        if len(live_setting_ids) == 1
        else None
    )
    live_values = [
        float(record["live_latency_seconds"]) for record in live_records or []
    ]
    extra_live_records = [
        record
        for record in records
        if record.get("segment") == "live"
        and (
            record.get("stack_id") != "bee-1-cpl"
            or int(record.get("count", -1)) != 100
            or record.get("role") != "candidate-live"
        )
    ]
    live_order = warmup_setting_order(
        records,
        segment="live",
        stack_id="bee-1-cpl",
        count=100,
        setting_ids=set(live_setting_ids),
    )
    live_complete = (
        campaign_identity_complete
        and len(live_values) == 6
        and not extra_live_records
        and bool(live_order)
        and complete_alternating_schedule(
            records,
            segment="live",
            stack_id="bee-1-cpl",
            count=100,
            setting_ids=live_order,
        )
    )
    live_reduction_guard = None
    if len(live_values) == 6:
        live_reduction_guard = require_guard(
            "G20-aggregate-reduction",
            {
                "statistic_kind": "live",
                "latency_seconds": live_values,
                "maximum_seconds": max(live_values),
                "all_replays_pass": all(value <= 10.0 for value in live_values),
            },
        )
        statistic_guards.append(live_reduction_guard.to_json())
    live_ok = (
        live_complete
        and live_reduction_guard is not None
        and live_reduction_guard.passed
        and max(live_values) <= 10.0
    )

    bars = {
        "comparative": {
            "verdict": verdict(comparative_passes, comparative_complete),
            "by_count": comparative_rows,
            "pooled": {
                "status": (
                    "PASS"
                    if pooled_pass
                    else "FAIL"
                    if pooled_ratio is not None
                    else "UNMEASURED"
                ),
                "strehl_sum_of_capture_minima_seconds": (
                    sum(row["strehl"] for row in comparative_minima.values())
                    if pooled_ratio is not None
                    else None
                ),
                "fastest_qualified_comparator_sum_of_capture_minima_seconds": (
                    sum(row["comparator"] for row in comparative_minima.values())
                    if pooled_ratio is not None
                    else None
                ),
                "ratio": pooled_ratio,
                "bar": 2.0,
                "formula": "sum_c(T_c) / sum_c(S_c)",
            },
        },
        "native_cpu_16": {
            "verdict": verdict(cpu_checks, cpu_complete),
            "bar_seconds_per_frame": 0.15,
            "by_count": cpu_cells,
        },
        "native_hybrid": {
            "verdict": verdict(hybrid_checks, hybrid_complete),
            "bar_seconds_per_frame": 0.06,
            "by_count": hybrid_cells,
        },
        "cold_overhead": {
            "verdict": verdict([cold_ok], cold_complete_by_arm["product"]),
            "bar_seconds": 20.0,
            "by_cell": cold_overheads,
            "bar_applies_to": sorted(cold_bar_values),
            "comparative_cold": {
                "status": (
                    "COMPLETE" if cold_complete_by_arm["comparative"] else "UNMEASURED"
                ),
                "by_cell": comparative_cold_values,
                "diagnostic_only": True,
            },
        },
        "live_first_100": {
            "verdict": verdict([live_ok], live_complete),
            "bar_seconds": 10.0,
            "maximum_latency_seconds": max(live_values) if live_values else None,
            "dispersion": describe(live_values) if live_values else None,
        },
        "candidate_default_baseline": {
            "verdict": verdict([baseline_ok], cpu_complete and baseline_complete),
            "bar_ratio": 2.0,
            "by_count": baseline_ratios,
        },
        "retained_m12_cross_worker_identity": {
            "verdict": verdict(cross_worker_passes, cross_worker_complete),
            "track": "common-merge",
            "required_workers": list(WORKER_LADDER),
            "by_count": cross_worker_cells,
            "rule": (
                "the canonical highest-precision output (frozen as scored "
                "repetition 1) at workers 1/2/4/8/16 must be mutually "
                "byte-identical for each registered N; within-worker repeat "
                "determinism is disclosed separately and does not gate M11"
            ),
        },
    }
    publication_components = (
        "comparative",
        "retained_m12_cross_worker_identity",
    )
    product_native_components = (
        "native_cpu_16",
        "native_hybrid",
        "cold_overhead",
        "live_first_100",
        "candidate_default_baseline",
    )
    overall = m11_publication_verdict(bars)
    product_native_verdicts = [
        bars[name]["verdict"] for name in product_native_components
    ]
    product_native_report_verdict = aggregate_verdict(product_native_verdicts)
    result = {
        "schema": "m153-m11-summary-v1",
        "evidence_tag": "MEASURED" if records else "UNMEASURED",
        "generated_utc": utc_now(),
        "records": {
            "path": str(records_path),
            "sha256": sha256_file(records_path),
            "count": len(records),
        },
        "campaign_identity_complete": campaign_identity_complete,
        "campaign_attempt_history": attempt_history,
        "quality_qualification": quality,
        "group_dispersion": group_stats,
        "statistic_guards": statistic_guards,
        "bars": bars,
        "overall_m11_verdict": overall,
        "publication_gate_verdict": overall,
        "publication_gate_components": list(publication_components),
        "product_native_report_verdict": product_native_report_verdict,
        "product_native_report_components": list(product_native_components),
        "product_native_does_not_determine_publication_verdict": True,
        "headline_rule": "minimum per setting after one warm-up and six alternating sweeps",
    }
    write_json(output, result)
    print(json.dumps({"overall_m11_verdict": overall}, sort_keys=True))
    return 0 if overall != "INVALID" else 1


def m12_bridge(
    m11_summary_path: Path,
    records_path: Path,
    output: Path,
) -> int:
    m11_summary_path = m11_summary_path.resolve(strict=True)
    records_path = records_path.resolve(strict=True)
    output = output.resolve()
    summary_data = read_json(m11_summary_path)
    if summary_data.get("schema") != "m153-m11-summary-v1":
        raise ValueError("unsupported M11 summary schema")
    submitted_summary = summary_data
    summary_recomputed = False
    try:
        quality_source = submitted_summary["quality_qualification"]["source_manifest"]
        quality_path = repository_path(quality_source["path"]).resolve(strict=True)
        recompute_root = LANE_ROOT / "work" / "m12-summary-recompute"
        recompute_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=recompute_root) as temporary:
            recomputed_path = Path(temporary) / "summary.json"
            summarize(records_path, recomputed_path, quality_path)
            recomputed_summary = read_json(recomputed_path)
        submitted_comparable = {
            key: value
            for key, value in submitted_summary.items()
            if key != "generated_utc"
        }
        recomputed_comparable = {
            key: value
            for key, value in recomputed_summary.items()
            if key != "generated_utc"
        }
        summary_recomputed = submitted_comparable == recomputed_comparable
        summary_data = recomputed_summary
    except (KeyError, OSError, TypeError, ValueError):
        summary_recomputed = False
    records_sha256 = sha256_file(records_path)
    summary_record_binding = submitted_summary.get("records", {})
    records_bound = (
        summary_record_binding.get("sha256") == records_sha256
        and Path(summary_record_binding.get("path", "")).resolve(strict=True)
        == records_path.resolve(strict=True)
        and int(summary_record_binding.get("count", -1))
        == len(
            [
                line
                for line in records_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        )
    )
    records = [
        parse_json_line(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cells: dict[str, Any] = {}
    complete = True
    for count in REGISTERED_COUNTS:
        stack = "coffee-bean" if count == 105 else "bee-1-cpl"
        setting_ids = sorted(
            {
                str(record.get("setting_id"))
                for record in records
                if record.get("segment") == "comparative-warm"
                and record.get("role") == "strehl-common"
                and int(record.get("workers", -1)) == 16
                and int(record.get("count", -1)) == count
                and record.get("stack_id") == stack
            }
        )
        matches = (
            complete_cell_records(
                records,
                segment="comparative-warm",
                stack_id=stack,
                count=count,
                setting_id=setting_ids[0],
                role="strehl-common",
                workers=16,
            )
            if len(setting_ids) == 1
            else None
        )
        cell_complete = matches is not None
        complete &= cell_complete
        rows = matches or []
        cells[str(count)] = {
            "complete": cell_complete,
            "record_count": len(rows),
            "settings_sha256": sorted(
                {record.get("settings_sha256") for record in rows}
            ),
            "input_manifest_sha256": sorted(
                {record.get("input_manifest_sha256") for record in rows}
            ),
            "input_content_sha256": sorted(
                {record.get("input_content_sha256") for record in rows}
            ),
            "output_sha256": [record["output"]["output_sha256"] for record in rows],
            "pixel_sha256": [record["output"]["pixel_sha256"] for record in rows],
            "invocation_manifest_sha256": [
                record["invocation_manifest"]["sha256"] for record in rows
            ],
            "peak_private_committed_bytes": [
                record["process_tree"]["peak_private_committed_bytes"]
                for record in rows
            ],
            "wall_seconds": [record["wall_seconds"] for record in rows],
        }
    m11_pass = summary_data.get("overall_m11_verdict") == "PASS"
    campaign_identity_complete = bool(records) and records_match_campaign_identity(
        records,
        {
            field: records[0].get(field)
            for field in (
                "campaign_sha256",
                "authorization_sha256",
                "contract_sha256",
                "measured_commit",
            )
        },
    )
    common_setting_consistent = setting_signature_consistent(
        records,
        role="strehl-common",
        counts=REGISTERED_COUNTS,
        workers=16,
    )
    expected_bars = {
        "comparative",
        "native_cpu_16",
        "native_hybrid",
        "cold_overhead",
        "live_first_100",
        "candidate_default_baseline",
        "retained_m12_cross_worker_identity",
    }
    bars = summary_data.get("bars", {})
    publication_bars_pass = set(bars) == expected_bars and all(
        bars[name].get("verdict") == "PASS"
        for name in (
            "comparative",
            "retained_m12_cross_worker_identity",
        )
    )
    quality = summary_data.get("quality_qualification", {})
    quality_source = quality.get("source_manifest", {})
    try:
        quality_current = validate_quality_manifest(
            repository_path(quality_source["path"]).resolve(strict=True)
        )
        quality_bound = (
            quality_source.get("sha256")
            == sha256_file(repository_path(quality_source["path"]))
            and quality_current == quality
            and quality.get("status") == "PASS"
        )
    except (KeyError, OSError, TypeError, ValueError):
        quality_bound = False
    summary_common_cells = bars.get("comparative", {}).get("by_count", {})
    summary_identity_cells = bars.get(
        "retained_m12_cross_worker_identity",
        {},
    ).get("by_count", {})
    summary_cells_match = all(
        cells[str(count)]["complete"]
        and summary_common_cells.get(str(count), {}).get("strehl_setting_id")
        == next(
            (
                str(record.get("setting_id"))
                for record in records
                if record.get("segment") == "comparative-warm"
                and record.get("role") == "strehl-common"
                and int(record.get("workers", -1)) == 16
                and int(record.get("count", -1)) == count
            ),
            None,
        )
        and summary_common_cells.get(str(count), {}).get("strehl_wall_seconds")
        == cells[str(count)]["wall_seconds"]
        and summary_common_cells.get(str(count), {}).get("strehl_input_manifest_sha256")
        == cells[str(count)]["input_manifest_sha256"][0]
        and summary_identity_cells.get(str(count), {})
        .get("by_worker", {})
        .get("16", {})
        .get("output_sha256")
        == cells[str(count)]["output_sha256"]
        and summary_identity_cells.get(str(count), {})
        .get("by_worker", {})
        .get("16", {})
        .get("pixel_sha256")
        == cells[str(count)]["pixel_sha256"]
        for count in REGISTERED_COUNTS
    )
    status = (
        "ELIGIBLE"
        if (
            m11_pass
            and publication_bars_pass
            and quality_bound
            and summary_cells_match
            and summary_recomputed
            and complete
            and records_bound
            and campaign_identity_complete
            and common_setting_consistent
            and summary_data.get("campaign_identity_complete") is True
        )
        else "UNMEASURED"
    )
    result = {
        "schema": "m153-m11-to-m12-bridge-v1",
        "evidence_tag": "MEASURED" if records else "UNMEASURED",
        "generated_utc": utc_now(),
        "m11_summary": {
            "path": str(m11_summary_path),
            "sha256": sha256_file(m11_summary_path),
            "verdict": summary_data.get("overall_m11_verdict"),
        },
        "records": {
            "path": str(records_path),
            "sha256": records_sha256,
            "matches_summary_binding": records_bound,
        },
        "summary_integrity": {
            "summary_recomputed_from_records": summary_recomputed,
            "publication_bars_pass": publication_bars_pass,
            "quality_binding_current": quality_bound,
            "worker16_cells_match": summary_cells_match,
            "campaign_identity_complete": campaign_identity_complete,
            "common_merge_setting_consistent": common_setting_consistent,
        },
        "worker16_cells": cells,
        "retained_m12_cross_worker_identity": bars.get(
            "retained_m12_cross_worker_identity",
            {},
        ),
        "join_rule": (
            "M12 must match these exact settings, whole-file hashes, and "
            "highest-precision common-merge pixel hashes for N=33/105/299. "
            "This bridge cannot turn PASS unless the M11 common-merge publication "
            "verdict is PASS; product-native M12 disclosures remain separate."
        ),
        "status": status,
    }
    write_json(output, result)
    print(json.dumps({"status": status}, sort_keys=True))
    return 0


def validate_m12_export(
    m12: dict[str, Any],
    m11_records_reference: dict[str, Any],
) -> list[dict[str, Any]]:
    """Reconstruct M11 common-merge W16 vectors from its exact record file."""

    references = {
        str(row.get("role")): row
        for row in m12.get("source_artifacts", [])
        if isinstance(row, dict)
    }
    if set(references) != {
        "campaign",
        "measurement-manifest",
        "worker16-records",
    }:
        raise ValueError(
            "M12 export must bind its campaign, manifest, and worker-16 records"
        )
    bindings = {
        role: read_artifact_binding(
            repository_path(reference["path"]),
            reference["sha256"],
        )
        for role, reference in references.items()
    }
    require_guard("G04-artifact-binding", {"artifacts": list(bindings.values())})
    if (
        repository_path(references["worker16-records"]["path"]).resolve(strict=True)
        != repository_path(m11_records_reference["path"]).resolve(strict=True)
        or references["worker16-records"]["sha256"] != m11_records_reference["sha256"]
    ):
        raise ValueError("M12 worker-16 source is not the M11 campaign record file")
    campaign = read_json(repository_path(references["campaign"]["path"]))
    manifest = read_json(repository_path(references["measurement-manifest"]["path"]))
    records_path = repository_path(references["worker16-records"]["path"])
    records = [
        parse_json_line(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cells = m12.get("worker16_cells", {})
    campaign_sha256 = bindings["campaign"]["actual_sha256"]
    records_sha256 = bindings["worker16-records"]["actual_sha256"]
    input_references = manifest.get("input_manifests", {})
    if set(input_references) != {"33", "105", "299"}:
        raise ValueError("M12 manifest does not bind every registered input")
    input_bindings = {
        count: read_artifact_binding(
            repository_path(reference["path"]),
            reference["sha256"],
        )
        for count, reference in input_references.items()
    }
    require_guard(
        "G04-artifact-binding",
        {"artifacts": list(input_bindings.values())},
    )
    reconstructed: dict[str, dict[str, Any]] = {}
    for count in ("33", "105", "299"):
        stack_id = "coffee-bean" if count == "105" else "bee-1-cpl"
        setting_ids = sorted(
            {
                str(row.get("setting_id"))
                for row in records
                if row.get("segment") == "comparative-warm"
                and row.get("role") == "strehl-common"
                and int(row.get("workers", -1)) == 16
                and int(row.get("count", -1)) == int(count)
                and row.get("stack_id") == stack_id
            }
        )
        scored = (
            complete_cell_records(
                records,
                segment="comparative-warm",
                stack_id=stack_id,
                count=int(count),
                setting_id=setting_ids[0],
                role="strehl-common",
                workers=16,
            )
            if len(setting_ids) == 1
            else None
        )
        if scored is None:
            raise ValueError("M12 source lacks a complete passing M11 worker-16 cell")
        reconstructed[count] = {
            "workers": 16,
            "warmups": 1,
            "scored_repetitions": 6,
            "schedule_status": "PASS",
            "settings_sha256": sorted({row.get("settings_sha256") for row in scored}),
            "input_manifest_sha256": sorted(
                {row.get("input_manifest_sha256") for row in scored}
            ),
            "input_content_sha256": sorted(
                {row.get("input_content_sha256") for row in scored}
            ),
            "output_sha256": [
                row.get("output", {}).get("output_sha256") for row in scored
            ],
            "pixel_sha256": [
                row.get("output", {}).get("pixel_sha256") for row in scored
            ],
        }
    m11_measured_commits = {
        row.get("measured_commit")
        for row in records
        if row.get("segment") == "comparative-warm"
        and row.get("role") == "strehl-common"
        and int(row.get("workers", -1)) == 16
        and int(row.get("count", -1)) in REGISTERED_COUNTS
    }
    if (
        m12.get("schema") != "m153-m12-worker16-export-v1"
        or m12.get("track") != "common-merge"
        or m12.get("status") != "COMPLETE"
        or m12.get("worker16_status") != "PASS"
        or set(cells) != {"33", "105", "299"}
        or reconstructed != cells
        or campaign.get("schema") != "m153-m12-campaign-v1"
        or campaign.get("m11_joint_track") != "common-merge"
        or campaign.get("status") != "FROZEN"
        or not isinstance(campaign.get("measured_commit"), str)
        or len(campaign["measured_commit"]) not in {40, 64}
        or any(
            character not in "0123456789abcdefABCDEF"
            for character in campaign["measured_commit"]
        )
        or m11_measured_commits != {campaign["measured_commit"]}
        or campaign.get("worker16_input_manifest_sha256")
        != {
            count: binding["actual_sha256"] for count, binding in input_bindings.items()
        }
        or any(
            len(cell.get("input_content_sha256", [])) != 1 for cell in cells.values()
        )
        or campaign.get("worker16_input_content_sha256")
        != {count: cell["input_content_sha256"][0] for count, cell in cells.items()}
        or any(
            cell.get("input_manifest_sha256")
            != [input_bindings[count]["actual_sha256"]]
            for count, cell in cells.items()
        )
        or campaign.get("worker16_settings_sha256")
        != {count: cell.get("settings_sha256") for count, cell in cells.items()}
        or manifest.get("schema") != "m153-m12-measurement-manifest-v1"
        or manifest.get("m11_joint_track") != "common-merge"
        or manifest.get("status") != "FROZEN"
        or manifest.get("campaign", {}).get("sha256") != campaign_sha256
        or repository_path(manifest.get("campaign", {}).get("path", "")).resolve(
            strict=True
        )
        != repository_path(references["campaign"]["path"]).resolve(strict=True)
        or manifest.get("worker16_records", {}).get("sha256") != records_sha256
        or repository_path(
            manifest.get("worker16_records", {}).get("path", "")
        ).resolve(strict=True)
        != records_path.resolve(strict=True)
        or manifest.get("worker16_settings_sha256")
        != {count: cell.get("settings_sha256") for count, cell in cells.items()}
        or manifest.get("worker16_input_manifest_sha256")
        != campaign.get("worker16_input_manifest_sha256")
        or manifest.get("worker16_input_content_sha256")
        != campaign.get("worker16_input_content_sha256")
        or len({cell["settings_sha256"][0] for cell in cells.values()}) != 1
    ):
        raise ValueError("M12 worker-16 export provenance is incomplete")
    return [*bindings.values(), *input_bindings.values()]


def m12_join(
    bridge_path: Path,
    m12_cells_path: Path,
    output: Path,
) -> int:
    bridge_path = bridge_path.resolve(strict=True)
    m12_cells_path = m12_cells_path.resolve(strict=True)
    output = output.resolve()
    submitted_bridge = read_json(bridge_path)
    bridge = submitted_bridge
    bridge_recomputed = False
    try:
        summary_reference = submitted_bridge["m11_summary"]
        records_reference = submitted_bridge["records"]
        recompute_root = LANE_ROOT / "work" / "m12-bridge-recompute"
        recompute_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=recompute_root) as temporary:
            recomputed_path = Path(temporary) / "bridge.json"
            m12_bridge(
                repository_path(summary_reference["path"]),
                repository_path(records_reference["path"]),
                recomputed_path,
            )
            recomputed_bridge = read_json(recomputed_path)
        submitted_comparable = {
            key: value
            for key, value in submitted_bridge.items()
            if key != "generated_utc"
        }
        recomputed_comparable = {
            key: value
            for key, value in recomputed_bridge.items()
            if key != "generated_utc"
        }
        bridge_recomputed = submitted_comparable == recomputed_comparable
        bridge = recomputed_bridge
    except (KeyError, OSError, TypeError, ValueError):
        bridge_recomputed = False
    m12 = read_json(m12_cells_path)
    m11_cells = bridge.get("worker16_cells", {})
    try:
        validate_m12_export(m12, bridge["records"])
        m12_source_current = True
    except (KeyError, OSError, TypeError, ValueError):
        m12_source_current = False
    try:
        summary_reference = bridge["m11_summary"]
        records_reference = bridge["records"]
        summary_path = repository_path(summary_reference["path"]).resolve(strict=True)
        records_path = repository_path(records_reference["path"]).resolve(strict=True)
        source_summary = read_json(summary_path)
        source_records = [
            parse_json_line(line)
            for line in records_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        bridge_source_current = (
            bridge.get("schema") == "m153-m11-to-m12-bridge-v1"
            and sha256_file(summary_path) == summary_reference["sha256"]
            and sha256_file(records_path) == records_reference["sha256"]
            and records_reference.get("matches_summary_binding") is True
            and source_summary.get("overall_m11_verdict") == "PASS"
            and source_summary.get("records", {}).get("sha256")
            == records_reference["sha256"]
            and repository_path(
                source_summary.get("records", {}).get("path", "")
            ).resolve(strict=True)
            == records_path
            and all(
                (
                    rows := complete_cell_records(
                        source_records,
                        segment="comparative-warm",
                        stack_id=("coffee-bean" if int(count) == 105 else "bee-1-cpl"),
                        count=int(count),
                        setting_id=next(
                            (
                                str(record.get("setting_id"))
                                for record in source_records
                                if record.get("segment") == "comparative-warm"
                                and record.get("role") == "strehl-common"
                                and int(record.get("workers", -1)) == 16
                                and int(record.get("count", -1)) == int(count)
                            ),
                            "",
                        ),
                        role="strehl-common",
                        workers=16,
                    )
                )
                is not None
                and [row["output"]["output_sha256"] for row in rows]
                == cell.get("output_sha256")
                and [row["output"]["pixel_sha256"] for row in rows]
                == cell.get("pixel_sha256")
                and sorted({row.get("settings_sha256") for row in rows})
                == cell.get("settings_sha256")
                and sorted({row.get("input_manifest_sha256") for row in rows})
                == cell.get("input_manifest_sha256")
                and sorted({row.get("input_content_sha256") for row in rows})
                == cell.get("input_content_sha256")
                for count, cell in m11_cells.items()
            )
        )
        quality = source_summary.get("quality_qualification", {})
        quality_reference = quality.get("source_manifest", {})
        quality_current = validate_quality_manifest(
            repository_path(quality_reference["path"]).resolve(strict=True)
        )
        bridge_source_current &= (
            quality_reference.get("sha256")
            == sha256_file(repository_path(quality_reference["path"]))
            and quality_current == quality
            and quality.get("status") == "PASS"
        )
    except (KeyError, OSError, TypeError, ValueError):
        bridge_source_current = False
    normalized_m11 = {
        count: {
            "settings_sha256": cell.get("settings_sha256"),
            "input_manifest_sha256": cell.get("input_manifest_sha256"),
            "input_content_sha256": cell.get("input_content_sha256"),
            "output_sha256": cell.get("output_sha256"),
            "pixel_sha256": cell.get("pixel_sha256"),
        }
        for count, cell in m11_cells.items()
    }
    payload = {
        "bridge_status": bridge.get("status"),
        "m11": {
            "verdict": bridge.get("m11_summary", {}).get("verdict"),
            "cross_worker_identity_verdict": bridge.get(
                "retained_m12_cross_worker_identity",
                {},
            ).get("verdict"),
            "worker16_cells": normalized_m11,
        },
        "m12": {
            "worker16_cells": m12.get("worker16_cells", {}),
        },
    }
    guard = evaluate_guard("G17-m12-joint", payload)
    prerequisites_complete = (
        bridge.get("status") == "ELIGIBLE"
        and bridge_recomputed
        and bridge_source_current
        and m12_source_current
        and set(normalized_m11) == {"33", "105", "299"}
        and set(m12.get("worker16_cells", {})) == {"33", "105", "299"}
    )
    status = (
        "PASS"
        if (
            guard.passed
            and bridge_recomputed
            and bridge_source_current
            and m12_source_current
        )
        else "FAIL"
        if prerequisites_complete
        else "UNMEASURED"
    )
    result = {
        "schema": "m153-m11-m12-joint-v1",
        "generated_utc": utc_now(),
        "m11_bridge": {
            "path": str(bridge_path),
            "sha256": sha256_file(bridge_path),
        },
        "m12_cells": {
            "path": str(m12_cells_path),
            "sha256": sha256_file(m12_cells_path),
        },
        "guard": guard.to_json(),
        "bridge_recomputed_from_records": bridge_recomputed,
        "bridge_source_current": bridge_source_current,
        "m12_source_current": m12_source_current,
        "status": status,
    }
    write_json(output, result)
    print(json.dumps({"status": status}, sort_keys=True))
    return 0 if status == "PASS" else 2


def audit(
    output: Path,
    commission_path: Path,
    mutation_path: Path,
    census_path: Path,
) -> int:
    output = output.resolve()
    commission_path = commission_path.resolve(strict=True)
    mutation_path = mutation_path.resolve(strict=True)
    census_path = census_path.resolve(strict=True)
    contract = load_contract()
    commission_data = read_json(commission_path)
    mutation_data = read_json(mutation_path)
    census_data = read_json(census_path)
    guards = sorted(GUARD_REGISTRY)
    source_bindings = commission_data.get("source_bindings", {})
    source_binding_pass = commission_source_bindings_current(source_bindings)
    census_pass = (
        census_data.get("schema") == "m153-input-census-v1"
        and census_data.get("status") == "PASS"
        and census_data.get("evidence_tag") == "VERIFIED_METADATA_ONLY"
        and evaluate_guard(
            "G02-capture-contract",
            {"captures": census_data.get("captures", {})},
        ).passed
        and set(census_data.get("readonly_snapshots", {}))
        == {"bee-1-cpl", "coffee-bean"}
        and all(
            evaluate_guard("G03-readonly-snapshot", snapshot).passed
            for snapshot in census_data.get("readonly_snapshots", {}).values()
        )
    )
    checks = {
        "commission_pass": commission_data.get("status") == "PASS",
        "mutation_pass": mutation_data.get("status") == "PASS",
        "mutation_guard_set_current": mutation_data.get("guard_ids") == guards,
        "mutation_source_current": (
            mutation_data.get("source", {}).get("sha256")
            == sha256_file(LANE_ROOT / "m11_core.py")
        ),
        "mutation_runtime_current": commission_runtime_binding_current(mutation_data),
        "all_guard_mutations_killed": (
            mutation_data.get("substantive_killed")
            == mutation_data.get("substantive_total")
            == len(guards)
        ),
        "inert_mutation_survived": (
            mutation_data.get("inert_survived") == 1
            and mutation_data.get("inert_total") == 1
        ),
        "commission_contract_current": (
            commission_data.get("contract", {}).get("sha256")
            == sha256_file(CONTRACT_PATH)
        ),
        "census_contract_current": (
            census_data.get("contract", {}).get("sha256") == sha256_file(CONTRACT_PATH)
        ),
        "source_bindings_current": source_binding_pass,
        "commission_runtime_current": commission_runtime_binding_current(
            commission_data
        ),
        "census_internal_checks_pass": census_pass,
        "no_real_timing_in_commission": (
            commission_data.get("real_timing_authorized") is False
        ),
    }
    status = all(checks.values())
    result = {
        "schema": "m153-build-audit-v1",
        "evidence_tag": "VERIFIED",
        "generated_utc": utc_now(),
        "contract": contract_hash(),
        "commission": {
            "path": str(commission_path.relative_to(ROOT)),
            "sha256": sha256_file(commission_path),
            "status": commission_data.get("status"),
            "formal_scorecard_control": commission_data.get("formal_scorecard_control"),
        },
        "mutation_commission": {
            "path": str(mutation_path.relative_to(ROOT)),
            "sha256": sha256_file(mutation_path),
            "status": mutation_data.get("status"),
            "substantive_killed": mutation_data.get("substantive_killed"),
            "substantive_total": mutation_data.get("substantive_total"),
            "inert_survived": mutation_data.get("inert_survived"),
        },
        "input_census": {
            "path": str(census_path.relative_to(ROOT)),
            "sha256": sha256_file(census_path),
            "status": census_data.get("status"),
            "contract_sha256": census_data.get("contract", {}).get("sha256"),
        },
        "source_bindings_pass": source_binding_pass,
        "census_internal_checks_pass": census_pass,
        "checks": checks,
        "guard_count": len(guards),
        "guard_ids": guards,
        "real_timing_run_count": 0,
        "real_run_authorized_in_contract": contract.get("real_run_authorized"),
        "formal_m11_verdict": "UNMEASURED",
        "status": "PASS" if status else "FAIL",
    }
    write_json(output, result)
    print(json.dumps({"status": result["status"]}, sort_keys=True))
    return 0 if status else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="M153 fail-closed M11 two-arm timing harness"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("contract-hash")

    census_parser = subparsers.add_parser("census")
    census_parser.add_argument("--output", type=Path, required=True)

    quality_parser = subparsers.add_parser("quality-check")
    quality_parser.add_argument("--manifest", type=Path, required=True)
    quality_parser.add_argument("--output", type=Path)

    commission_parser = subparsers.add_parser("commission")
    commission_parser.add_argument("--output", type=Path, required=True)
    commission_parser.add_argument("--work", type=Path, required=True)
    commission_parser.add_argument(
        "--formal-scorecard-control",
        action="store_true",
        help="run the required 1.000-second plant; do not use during M139",
    )

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--campaign", type=Path, required=True)
    run_parser.add_argument("--authorization", type=Path, required=True)
    run_parser.add_argument("--segment", required=True)
    run_parser.add_argument("--work", type=Path, required=True)
    run_parser.add_argument("--records", type=Path, required=True)

    summary_parser = subparsers.add_parser("summarize")
    summary_parser.add_argument("--records", type=Path, required=True)
    summary_parser.add_argument("--output", type=Path, required=True)
    summary_parser.add_argument("--quality", type=Path)

    bridge_parser = subparsers.add_parser("m12-bridge")
    bridge_parser.add_argument("--m11-summary", type=Path, required=True)
    bridge_parser.add_argument("--records", type=Path, required=True)
    bridge_parser.add_argument("--output", type=Path, required=True)

    join_parser = subparsers.add_parser("m12-join")
    join_parser.add_argument("--bridge", type=Path, required=True)
    join_parser.add_argument("--m12-cells", type=Path, required=True)
    join_parser.add_argument("--output", type=Path, required=True)

    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--output", type=Path, required=True)
    audit_parser.add_argument("--commission", type=Path, required=True)
    audit_parser.add_argument("--mutation", type=Path, required=True)
    audit_parser.add_argument("--census", type=Path, required=True)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "contract-hash":
        print(json.dumps(contract_hash(), indent=2, sort_keys=True))
        return 0
    if args.command == "census":
        return census(args.output)
    if args.command == "quality-check":
        result = validate_quality_manifest(args.manifest)
        if args.output is not None:
            write_json(args.output, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    if args.command == "commission":
        return commission(
            args.output,
            args.work,
            args.formal_scorecard_control,
        )
    if args.command == "run":
        return run_segment(
            campaign_path=args.campaign,
            authorization_path=args.authorization,
            segment_name=args.segment,
            work=args.work,
            records_path=args.records,
        )
    if args.command == "summarize":
        return summarize(args.records, args.output, args.quality)
    if args.command == "m12-bridge":
        return m12_bridge(args.m11_summary, args.records, args.output)
    if args.command == "m12-join":
        return m12_join(args.bridge, args.m12_cells, args.output)
    if args.command == "audit":
        return audit(args.output, args.commission, args.mutation, args.census)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
