"""Independent regression checks for the M164 dominance-manifest bundle."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
MANIFEST = HERE / "production-manifest-v1.json"
FREEZE = HERE / "production-manifest-v1.freeze.json"
READER = HERE / "reader.py"
CORE = HERE / "reader_core.py"
COMMISSION = HERE / "commission.py"
PRODUCTION_REFUSAL = OUT / "production-refusal.json"
OUTPUT = OUT / "verification.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "BLIS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    return environment


def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    manifest_bytes = MANIFEST.read_bytes()
    freeze_bytes = FREEZE.read_bytes()
    manifest = json.loads(manifest_bytes)
    freeze = json.loads(freeze_bytes)
    manifest_sha = _sha256(manifest_bytes)

    check(
        "freeze-binds-consumed-manifest-bytes",
        freeze["manifest_sha256"] == manifest_sha,
        {
            "expected": freeze["manifest_sha256"],
            "consumed": manifest_sha,
        },
    )
    check(
        "freeze-binds-checker-core",
        freeze["checker_core_sha256"] == _sha256(CORE.read_bytes()),
        freeze["checker_core_sha256"],
    )
    check(
        "freeze-binds-launcher",
        freeze["launcher_sha256"] == _sha256(READER.read_bytes()),
        freeze["launcher_sha256"],
    )
    check(
        "freeze-paths-are-exact",
        freeze["manifest_path"] == _relative(MANIFEST)
        and freeze["checker_core_path"] == _relative(CORE)
        and freeze["launcher_path"] == _relative(READER),
        {
            "manifest": freeze["manifest_path"],
            "core": freeze["checker_core_path"],
            "launcher": freeze["launcher_path"],
        },
    )

    artifact_checks = []
    for group, records in manifest["artifact_hashes"].items():
        for record in records:
            path = ROOT / record["path"]
            data = path.read_bytes()
            artifact_checks.append(
                {
                    "group": group,
                    "id": record["id"],
                    "expected": record["sha256"],
                    "consumed": _sha256(data),
                }
            )
    check(
        "all-present-artifacts-are-hash-bound",
        all(
            item["expected"] == item["consumed"] for item in artifact_checks
        ),
        artifact_checks,
    )

    check(
        "blocked-values-have-no-default",
        manifest["status"] == "BLOCKED"
        and manifest["dimensions"]["channels"] is None
        and manifest["dimensions"]["field_partitions"] is None
        and manifest["thresholds"]["epsilon_common"] is None
        and manifest["reduction"] is None
        and b"0.08" not in manifest_bytes,
        {
            "status": manifest["status"],
            "commissioning_default_present": b"0.08" in manifest_bytes,
        },
    )
    attributes = (HERE / ".gitattributes").read_text(encoding="utf-8")
    python_paths = [
        HERE / "build_blocked_manifest.py",
        HERE / "commission.py",
        HERE / "reader.py",
        HERE / "reader_core.py",
        HERE / "verify.py",
    ]
    json_paths = [
        MANIFEST,
        FREEZE,
        OUT / "commission.json",
        PRODUCTION_REFUSAL,
    ]
    python_line_endings = {
        path.name: (
            b"\r\n" in path.read_bytes()
            and b"\n" not in path.read_bytes().replace(b"\r\n", b"")
        )
        for path in python_paths
    }
    json_line_endings = {
        path.name: b"\r\n" not in path.read_bytes() for path in json_paths
    }
    check(
        "hash-bound-line-ending-policy",
        "*.py text eol=crlf" in attributes
        and "*.json -text" in attributes
        and all(python_line_endings.values())
        and all(json_line_endings.values()),
        {
            "python_crlf": python_line_endings,
            "json_exact_lf": json_line_endings,
        },
    )
    unresolved_ids = {
        item["id"] for item in manifest.get("unresolved", [])
    }
    expected_unresolved = {
        "production-cell-family",
        "production-numerical-bars",
        "complete-s-reduction",
        "physical-target-geometry",
        "production-software",
        "production-seed",
    }
    check(
        "blocker-ledger-is-complete",
        unresolved_ids == expected_unresolved,
        sorted(unresolved_ids),
    )

    reader_tree = ast.parse(READER.read_text(encoding="utf-8"))
    manifest_reads = [
        node
        for node in ast.walk(reader_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_bytes"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "manifest_resolved"
    ]
    reader_source = READER.read_text(encoding="utf-8")
    core_source = CORE.read_text(encoding="utf-8")
    same_bytes_flow = (
        len(manifest_reads) == 1
        and "manifest_sha = _sha256(manifest_bytes)" in reader_source
        and "manifest_bytes=manifest_bytes" in reader_source
        and "manifest = _json_from_bytes(" in core_source
        and "        manifest_bytes," in core_source
    )
    check(
        "manifest-read-hash-parse-single-byte-flow",
        same_bytes_flow,
        {"manifest_path_read_calls": len(manifest_reads)},
    )

    replay_output = OUT / "verification-production-refusal.json"
    command = [
        sys.executable,
        "-B",
        str(READER),
        "--repo-root",
        str(ROOT),
        "--freeze",
        str(FREEZE),
        "--manifest",
        str(MANIFEST),
        "--output",
        str(replay_output),
    ]
    replay = subprocess.run(
        command,
        cwd=ROOT,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    replay_bytes = replay_output.read_bytes() if replay_output.exists() else b""
    refusal_bytes = (
        PRODUCTION_REFUSAL.read_bytes()
        if PRODUCTION_REFUSAL.exists()
        else b""
    )
    refusal = json.loads(replay_bytes) if replay_bytes else {}
    refusal_codes = {
        reason["code"] for reason in refusal.get("reasons", [])
    }
    required_refusal_codes = {
        "MANIFEST_STATUS",
        "DIMENSIONS_NONEMPTY",
        "FAMILY_CARTESIAN",
        "EPSILON_COMMON_RANGE",
        "POWER_FLOORS_POSITIVE",
        "RANK_CONDITION_BARS",
        "REDUCTION_SPEC",
        "HASH_GROUPS_COMPLETE",
        "UNRESOLVED_FIELDS",
    }
    check(
        "production-reader-refuses-persistently",
        replay.returncode == 2
        and refusal.get("status") == "UNMEASURED"
        and required_refusal_codes.issubset(refusal_codes),
        {
            "returncode": replay.returncode,
            "reason_codes": sorted(refusal_codes),
        },
    )
    check(
        "production-refusal-is-reproducible",
        bool(refusal_bytes) and replay_bytes == refusal_bytes,
        {
            "recorded_sha256": _sha256(refusal_bytes)
            if refusal_bytes
            else None,
            "replay_sha256": _sha256(replay_bytes)
            if replay_bytes
            else None,
        },
    )
    if replay_output.exists():
        replay_output.unlink()

    commission_before = (
        OUT / "commission.json"
    ).read_bytes()
    commission_run = subprocess.run(
        [sys.executable, "-B", str(COMMISSION)],
        cwd=ROOT,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    commission_after = (OUT / "commission.json").read_bytes()
    commission = json.loads(commission_after)
    check(
        "commission-is-byte-reproducible",
        commission_run.returncode == 0
        and commission_before == commission_after,
        {
            "returncode": commission_run.returncode,
            "before_sha256": _sha256(commission_before),
            "after_sha256": _sha256(commission_after),
        },
    )
    check(
        "every-declared-check-fired",
        commission.get("status") == "PASS"
        and not commission.get("missing_checks")
        and not commission.get("failed_cases")
        and commission.get("required_checks")
        == commission.get("observed_checks"),
        {
            "required": len(commission.get("required_checks", [])),
            "observed": len(commission.get("observed_checks", [])),
            "cases": len(commission.get("cases", [])),
        },
    )
    check(
        "improvement-shaped-defect-is-unmeasured",
        any(
            case["id"] == "improvement-contamination"
            and case["status"] == "UNMEASURED"
            and case["directional_control"]["both_metrics_rose"]
            and "DOMINANCE_COMMON_MODE" in case["observed_reason_codes"]
            for case in commission.get("cases", [])
        ),
        next(
            (
                case["directional_control"]
                for case in commission.get("cases", [])
                if case["id"] == "improvement-contamination"
            ),
            None,
        ),
    )
    red_canary = commission.get("red_canary", {})
    check(
        "common-mode-charge-red-canary-is-load-bearing",
        red_canary.get("source_mutation", {}).get("anchor_count") == 1
        and red_canary.get("bad_checker_rewarded_contamination") is True
        and red_canary.get("commission_would_reject_bad_checker") is True,
        red_canary,
    )
    check(
        "all-plants-have-exact-one-anchors",
        commission.get("all_mutations_exactly_once_anchored") is True,
        commission.get("all_mutations_exactly_once_anchored"),
    )

    leftovers = [
        str(path.relative_to(HERE))
        for path in HERE.rglob("*")
        if path.name == "__pycache__"
        or path.name.endswith(".partial")
        or path.name == ".commission-work"
    ]
    check("no-scratch-leftovers", not leftovers, leftovers)

    passed = all(item["passed"] for item in checks)
    result = {
        "schema": "m164-dominance-manifest-verification/v1",
        "status": "PASS" if passed else "FAIL",
        "manifest_sha256": manifest_sha,
        "source_sha256": {
            "reader.py": _sha256(READER.read_bytes()),
            "reader_core.py": _sha256(CORE.read_bytes()),
            "commission.py": _sha256(COMMISSION.read_bytes()),
            "verify.py": _sha256(Path(__file__).read_bytes()),
        },
        "checks": checks,
    }
    _write_json(OUTPUT, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": len(checks),
                "failed": [
                    item["name"] for item in checks if not item["passed"]
                ],
                "manifest_sha256": manifest_sha,
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
