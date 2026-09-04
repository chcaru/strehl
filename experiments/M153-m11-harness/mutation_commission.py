from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from m11_core import (
    GUARD_REGISTRY,
    LANE_ROOT,
    require_guard,
    sha256_bytes,
    sha256_file,
)
from m11_runtime import ReadOnlyFileLocks


CORE_PATH = LANE_ROOT / "m11_core.py"
TEST_PATH = LANE_ROOT / "test_m11_harness.py"
PYTHON_EXECUTABLE = Path(sys.executable).resolve(strict=True)


MUTATIONS = {
    "G01-owned-output": "test_g01_owned_output",
    "G02-capture-contract": "test_g02_capture_contract",
    "G03-readonly-snapshot": "test_g03_readonly_snapshot",
    "G04-artifact-binding": "test_g04_artifact_binding",
    "G05-quality-qualified": "test_g05_quality_qualified",
    "G06-common-input-identity": "test_g06_common_input_identity",
    "G07-native-prefix": "test_g07_native_prefix",
    "G08-settings-fingerprint": "test_g08_settings_fingerprint",
    "G09-process-tree-drained": "test_g09_process_tree_drained",
    "G10-deliverable-finalized": "test_g10_deliverable_finalized",
    "G11-telemetry-complete": "test_g11_telemetry_complete",
    "G12-controlled-conditions": "test_g12_controlled_conditions",
    "G13-schedule-complete": "test_g13_schedule_complete",
    "G14-statistic-direction": "test_g14_statistic_direction",
    "G15-cold-receipt": "test_g15_cold_receipt",
    "G16-live-epoch": "test_g16_live_epoch",
    "G17-m12-joint": "test_g17_m12_joint",
    "G18-commissioning-required": "test_g18_commissioning_required",
    "G19-arm-symmetry": "test_g19_arm_symmetry",
    "G20-aggregate-reduction": "test_g20_aggregate_reduction",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply_unique_line_mutation(source: str, anchor: str, replacement: str) -> str:
    lines = source.splitlines()
    matches = [index for index, line in enumerate(lines) if line == anchor]
    if len(matches) != 1:
        raise RuntimeError(
            f"mutation anchor must occur on exactly one full line; "
            f"found {len(matches)} for {anchor!r}"
        )
    lines[matches[0]] = replacement
    suffix = "\n" if source.endswith("\n") else ""
    return "\n".join(lines) + suffix


def run_test(temp: Path, test_name: str | None) -> subprocess.CompletedProcess[str]:
    command = [
        str(PYTHON_EXECUTABLE),
        "-B",
        "-m",
        "unittest",
        "-v",
    ]
    if test_name is None:
        command.append("test_m11_harness")
    else:
        command.append(f"test_m11_harness.GuardMutationTests.{test_name}")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with ReadOnlyFileLocks([PYTHON_EXECUTABLE]):
        return subprocess.run(
            command,
            cwd=temp,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )


def substantive_result(
    *,
    guard_id: str,
    test_name: str,
    source: str,
    temp_root: Path,
) -> dict[str, Any]:
    anchor = f"    return valid  # MUTATION_ANCHOR:{guard_id.split('-', 1)[0]}"
    replacement = f"    return True  # MUTATION_ANCHOR:{guard_id.split('-', 1)[0]}"
    mutated = apply_unique_line_mutation(source, anchor, replacement)
    case_root = temp_root / guard_id
    case_root.mkdir()
    (case_root / "m11_core.py").write_text(mutated, encoding="utf-8", newline="\n")
    shutil.copy2(TEST_PATH, case_root / TEST_PATH.name)
    result = run_test(case_root, test_name)
    expected_failure = f"FAIL: {test_name}"
    killed = (
        result.returncode == 1
        and expected_failure in result.stdout
        and "ERROR:" not in result.stdout
        and "FAILED (failures=1)" in result.stdout
    )
    return {
        "guard_id": guard_id,
        "test": f"GuardMutationTests.{test_name}",
        "anchor": anchor,
        "anchor_count": source.splitlines().count(anchor),
        "original_sha256": sha256_bytes(source.encode("utf-8")),
        "mutated_sha256": sha256_bytes(mutated.encode("utf-8")),
        "returncode": result.returncode,
        "expected_failure_seen": expected_failure in result.stdout,
        "unexpected_error_seen": "ERROR:" in result.stdout,
        "killed": killed,
        "output_tail": result.stdout[-1200:],
    }


def inert_result(source: str, temp_root: Path) -> dict[str, Any]:
    anchor = 'INERT_MUTATION_SENTINEL = "m153-inert-v1"  # MUTATION_ANCHOR:INERT'
    replacement = 'INERT_MUTATION_SENTINEL = "m153-inert-v2"  # MUTATION_ANCHOR:INERT'
    mutated = apply_unique_line_mutation(source, anchor, replacement)
    case_root = temp_root / "INERT"
    case_root.mkdir()
    (case_root / "m11_core.py").write_text(mutated, encoding="utf-8", newline="\n")
    shutil.copy2(TEST_PATH, case_root / TEST_PATH.name)
    result = run_test(case_root, None)
    survived = result.returncode == 0 and "OK" in result.stdout
    return {
        "mutation_id": "INERT",
        "anchor": anchor,
        "anchor_count": source.splitlines().count(anchor),
        "original_sha256": sha256_bytes(source.encode("utf-8")),
        "mutated_sha256": sha256_bytes(mutated.encode("utf-8")),
        "returncode": result.returncode,
        "survived": survived,
        "output_tail": result.stdout[-1200:],
    }


def commission(output: Path, work: Path | None) -> int:
    output = output.resolve()
    if work is not None:
        work = work.resolve()
    require_guard(
        "G01-owned-output",
        {"path": str(output), "lane_root": str(LANE_ROOT)},
    )
    if set(MUTATIONS) != set(GUARD_REGISTRY):
        missing = sorted(set(GUARD_REGISTRY) - set(MUTATIONS))
        extra = sorted(set(MUTATIONS) - set(GUARD_REGISTRY))
        raise RuntimeError(
            f"mutation/guard registry mismatch; missing={missing}, extra={extra}"
        )
    source = CORE_PATH.read_text(encoding="utf-8")
    owned_work = work
    if owned_work is not None:
        require_guard(
            "G01-owned-output",
            {"path": str(owned_work), "lane_root": str(LANE_ROOT)},
        )
        if owned_work.exists():
            shutil.rmtree(owned_work)
        owned_work.mkdir(parents=True)
        context = tempfile.TemporaryDirectory(dir=owned_work)
    else:
        default_work = LANE_ROOT / "work" / "mutations"
        default_work.mkdir(parents=True, exist_ok=True)
        context = tempfile.TemporaryDirectory(dir=default_work)
    with context as temporary:
        temp_root = Path(temporary)
        substantive = [
            substantive_result(
                guard_id=guard_id,
                test_name=test_name,
                source=source,
                temp_root=temp_root,
            )
            for guard_id, test_name in sorted(MUTATIONS.items())
        ]
        inert = inert_result(source, temp_root)
    killed = sum(bool(row["killed"]) for row in substantive)
    status = "PASS" if killed == len(substantive) and inert["survived"] else "FAIL"
    result = {
        "schema": "m153-mutation-commission-v1",
        "evidence_tag": "VERIFIED",
        "generated_utc": utc_now(),
        "source": {
            "path": str(CORE_PATH),
            "sha256": sha256_file(CORE_PATH),
        },
        "runtime": {
            "python_executable": {
                "path": str(PYTHON_EXECUTABLE),
                "sha256": sha256_file(PYTHON_EXECUTABLE),
            }
        },
        "guard_ids": sorted(GUARD_REGISTRY),
        "mutation_ids": sorted(MUTATIONS),
        "substantive_total": len(substantive),
        "substantive_killed": killed,
        "substantive_survived": len(substantive) - killed,
        "inert_total": 1,
        "inert_survived": int(inert["survived"]),
        "inert_killed": int(not inert["survived"]),
        "mutations": substantive,
        "inert_mutation": inert,
        "status": status,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as destination:
        json.dump(result, destination, allow_nan=False, indent=2, sort_keys=True)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())
    print(
        json.dumps(
            {
                "status": status,
                "substantive_killed": killed,
                "substantive_total": len(substantive),
                "inert_survived": int(inert["survived"]),
            },
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work", type=Path)
    args = parser.parse_args()
    return commission(args.output, args.work)


if __name__ == "__main__":
    raise SystemExit(main())
