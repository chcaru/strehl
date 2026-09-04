#!/usr/bin/env python3
"""Exercise artifact and core-source replacement races against the M138 adapter."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ADAPTER_PATH = HERE / "m138_adapter.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def load_adapter() -> Any:
    source = ADAPTER_PATH.read_bytes()
    module = types.ModuleType("m138_adapter_race_subject")
    module.__file__ = str(ADAPTER_PATH)
    module.__package__ = ""
    sys.modules[module.__name__] = module
    try:
        exec(
            compile(source, str(ADAPTER_PATH), "exec", dont_inherit=True),
            module.__dict__,
        )
    finally:
        sys.modules.pop(module.__name__, None)
    return module


def parse_json_bytes(data: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def invoke(
    runtime: Path, request: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(runtime / "m138_adapter.py"),
            "--m138-evaluate",
            str(request),
        ],
        cwd=runtime,
        check=False,
        capture_output=True,
        timeout=120,
    )


def is_refusal(completed: subprocess.CompletedProcess[bytes]) -> bool:
    error = parse_json_bytes(completed.stderr)
    return bool(
        completed.returncode != 0
        and completed.stdout == b""
        and error is not None
        and error.get("status") == "INSTRUMENT_INVALID"
    )


def is_invalid_without_boolean(
    completed: subprocess.CompletedProcess[bytes], capture_id: str
) -> bool:
    output = parse_json_bytes(completed.stdout)
    return bool(
        completed.returncode == 0
        and completed.stderr == b""
        and output is not None
        and output.get("detail_state_by_capture")
        == {capture_id: "INSTRUMENT_INVALID"}
        and output.get("detail_pass_by_capture") == {}
    )


def is_detail_fail(
    completed: subprocess.CompletedProcess[bytes], capture_id: str
) -> bool:
    output = parse_json_bytes(completed.stdout)
    return bool(
        completed.returncode == 0
        and completed.stderr == b""
        and output is not None
        and output.get("detail_state_by_capture")
        == {capture_id: "DETAIL_FAIL"}
        and output.get("detail_pass_by_capture") == {capture_id: False}
    )


def atomic_replace(path: Path, data: bytes, serial: int) -> None:
    replacement = path.with_name(f".{path.name}.race-{os.getpid()}-{serial}")
    replacement.write_bytes(data)
    os.replace(replacement, path)


def toggle_file(
    path: Path,
    first: bytes,
    second: bytes,
    stop: threading.Event,
) -> None:
    serial = 0
    while not stop.is_set():
        for data in (first, second):
            if stop.is_set():
                break
            try:
                atomic_replace(path, data, serial)
                serial += 1
            except PermissionError:
                time.sleep(0.001)
            time.sleep(0)


def run_race(
    runtime: Path,
    request: Path,
    path: Path,
    first: bytes,
    second: bytes,
    attempts: int,
    classify: Any,
) -> dict[str, Any]:
    stop = threading.Event()
    thread = threading.Thread(
        target=toggle_file,
        args=(path, first, second, stop),
        daemon=True,
    )
    counts: dict[str, int] = {}
    unsafe: list[dict[str, Any]] = []
    thread.start()
    try:
        for attempt in range(attempts):
            completed = invoke(runtime, request)
            label = classify(completed)
            counts[label] = counts.get(label, 0) + 1
            if label == "unsafe":
                unsafe.append(
                    {
                        "attempt": attempt + 1,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout.decode(
                            "utf-8", errors="replace"
                        ),
                        "stderr": completed.stderr.decode(
                            "utf-8", errors="replace"
                        ),
                    }
                )
    finally:
        stop.set()
        thread.join(timeout=5)
        atomic_replace(path, first, attempts + 1)
    return {"attempts": attempts, "counts": counts, "unsafe": unsafe}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.flags.isolated != 1:
        raise SystemExit("invoke through python -I")
    if args.attempts < 8 or args.attempts > 128:
        raise SystemExit("--attempts must be between 8 and 128")

    adapter = load_adapter()
    scratch = HERE / f".m138-adapter-race-{os.getpid()}"
    if scratch.exists():
        raise SystemExit(f"race scratch already exists: {scratch}")

    try:
        scratch.mkdir()
        production_runtime = adapter.load_runtime()
        contract = copy.deepcopy(production_runtime.core_contract)
        bound = adapter.require_core_module().synthetic_binding(contract)
        for capture_id in ("race-missing-flat", "race-valid-fail"):
            adapter.add_synthetic_capture(bound, contract, capture_id)
        runtime = adapter.copy_self_test_runtime(scratch, bound)
        evidence = scratch / "evidence"
        payloads = evidence / "payloads"
        payloads.mkdir(parents=True)

        missing_payload = adapter.synthetic_payload_for(
            contract, bound, "race-missing-flat", information=0.70
        )
        del missing_payload["modes"]["candidate"]["flat_control"]
        fail_payload = adapter.synthetic_payload_for(
            contract, bound, "race-valid-fail", information=0.70
        )
        missing_path = payloads / "artifact-race.json"
        fail_path = payloads / "stable-fail.json"
        adapter.write_json(missing_path, missing_payload)
        adapter.write_json(fail_path, fail_payload)
        missing_bytes = missing_path.read_bytes()
        fail_bytes = fail_path.read_bytes()
        missing_ref = adapter.make_ref(missing_path, evidence)
        fail_ref = adapter.make_ref(fail_path, evidence)
        binding_hashes = adapter.self_test_binding_hashes(runtime, bound)

        missing_request = {
            "schema": "m135-m138-evaluate-request/v1",
            "capture_ids": ["race-missing-flat"],
            "artifacts": [missing_ref],
            "binding_hashes": binding_hashes,
            "comparisons": [
                {
                    "capture_id": "race-missing-flat",
                    "payload": missing_ref,
                }
            ],
        }
        missing_request_path = evidence / "artifact-race-request.json"
        adapter.write_json(missing_request_path, missing_request)

        fail_request = {
            "schema": "m135-m138-evaluate-request/v1",
            "capture_ids": ["race-valid-fail"],
            "artifacts": [fail_ref],
            "binding_hashes": binding_hashes,
            "comparisons": [
                {"capture_id": "race-valid-fail", "payload": fail_ref}
            ],
        }
        fail_request_path = evidence / "stable-fail-request.json"
        adapter.write_json(fail_request_path, fail_request)

        stable_missing = invoke(runtime, missing_request_path)
        stable_fail = invoke(runtime, fail_request_path)

        missing_path.write_bytes(fail_bytes)
        replaced_artifact = invoke(runtime, missing_request_path)
        missing_path.write_bytes(missing_bytes)

        def classify_artifact(
            completed: subprocess.CompletedProcess[bytes],
        ) -> str:
            if is_refusal(completed):
                return "refusal"
            if is_invalid_without_boolean(completed, "race-missing-flat"):
                return "registered-invalid"
            return "unsafe"

        artifact_race = run_race(
            runtime,
            missing_request_path,
            missing_path,
            missing_bytes,
            fail_bytes,
            args.attempts,
            classify_artifact,
        )

        core_path = runtime / "comparison_checker.py"
        good_core = core_path.read_bytes()
        sentinel = scratch / "malicious-core-executed.txt"
        malicious_core = good_core + (
            "\nPath("
            + repr(str(sentinel))
            + ").write_text('EXECUTED', encoding='utf-8')\n"
        ).encode("utf-8")
        core_path.write_bytes(malicious_core)
        replaced_core = invoke(runtime, fail_request_path)
        core_path.write_bytes(good_core)
        if sentinel.exists():
            sentinel.unlink()

        def classify_core(
            completed: subprocess.CompletedProcess[bytes],
        ) -> str:
            if sentinel.exists():
                return "unsafe"
            if is_refusal(completed):
                return "refusal"
            if is_detail_fail(completed, "race-valid-fail"):
                return "registered-detail-fail"
            return "unsafe"

        core_race = run_race(
            runtime,
            fail_request_path,
            core_path,
            good_core,
            malicious_core,
            args.attempts,
            classify_core,
        )
        sentinel_absent = not sentinel.exists()

        checks = {
            "stable_missing_flat_invalid_without_boolean": (
                is_invalid_without_boolean(
                    stable_missing, "race-missing-flat"
                )
            ),
            "stable_valid_fail_has_boolean_false": is_detail_fail(
                stable_fail, "race-valid-fail"
            ),
            "replaced_artifact_refuses_without_stdout": is_refusal(
                replaced_artifact
            ),
            "artifact_race_never_emits_scientific_conclusion": (
                not artifact_race["unsafe"]
            ),
            "replaced_core_refuses_without_stdout": is_refusal(replaced_core),
            "replaced_core_does_not_execute_sentinel": sentinel_absent,
            "core_race_never_executes_or_misreports": (
                not core_race["unsafe"] and sentinel_absent
            ),
        }
        result = {
            "schema": "m135-m138-adapter-race-verification/v1",
            "adapter_sha256": sha256_bytes(ADAPTER_PATH.read_bytes()),
            "checker_bundle_manifest_sha256": sha256_bytes(
                (HERE / "m138-checker-bundle.json").read_bytes()
            ),
            "fixture_hashes": {
                "registered_missing_flat": sha256_bytes(missing_bytes),
                "replacement_valid_fail": sha256_bytes(fail_bytes),
                "registered_core": sha256_bytes(good_core),
                "replacement_core": sha256_bytes(malicious_core),
            },
            "checks": checks,
            "check_count": len(checks),
            "passed_check_count": sum(
                1 for value in checks.values() if value
            ),
            "artifact_race": artifact_race,
            "core_race": core_race,
            "status": "PASS" if all(checks.values()) else "FAIL",
        }
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)

    encoded = canonical_json_bytes(result) + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
