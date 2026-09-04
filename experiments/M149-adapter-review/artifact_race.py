from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import tempfile
import threading
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

from review_common import (
    DEFAULT_SOURCE,
    binding_hashes,
    canonical_bytes,
    completed_record,
    invalid_and_fail_payloads,
    invoke_adapter,
    prepare_bound_runtime,
    sha256_bytes,
    sha256_file,
    write_json,
)

EXPECTED_INVALID_SHA256 = (
    "de4523fc4a1c41ced93da0c29a2aa2ea25062ae67248b1e09334d2d78bd7c574"
)
EXPECTED_FAIL_SHA256 = (
    "2aca17c001945544ec60a85eff9a88763d5d77a808817f621673cda855e5e84a"
)


def parse_output(raw: bytes) -> dict | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce M149's M138-adapter artifact hash/use race."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "strehl-M149-artifact-race-run",
    )
    parser.add_argument("--attempts", type=int, default=80)
    parser.add_argument("--swap-interval", type=float, default=0.002)
    parser.add_argument("--filler-mib", type=int, default=10)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    work = args.work_dir.resolve()
    if work.exists():
        shutil.rmtree(work)
    runtime = work / "runtime"
    evidence = work / "evidence"
    payload_dir = evidence / "payloads"
    payload_dir.mkdir(parents=True)

    core, contract, binding = prepare_bound_runtime(
        args.source_dir.resolve(), runtime
    )
    invalid, fail = invalid_and_fail_payloads(core, contract, binding)
    invalid_bytes = canonical_bytes(invalid)
    fail_bytes = canonical_bytes(fail)

    target = payload_dir / "capture-invalid.json"
    target.write_bytes(invalid_bytes)
    (evidence / "registered-invalid.json").write_bytes(invalid_bytes)
    (evidence / "unregistered-fail.json").write_bytes(fail_bytes)

    filler = evidence / "filler.bin"
    filler.write_bytes(b"0" * (args.filler_mib * 1024 * 1024))

    ref = {
        "path": "payloads/capture-invalid.json",
        "sha256": sha256_bytes(invalid_bytes),
    }
    filler_ref = {"path": "filler.bin", "sha256": sha256_file(filler)}
    request = {
        "schema": "m135-m138-evaluate-request/v1",
        "capture_ids": ["invalid"],
        "artifacts": [copy.deepcopy(ref), filler_ref],
        "binding_hashes": binding_hashes(runtime, binding),
        "comparisons": [
            {"capture_id": "invalid", "payload": copy.deepcopy(ref)}
        ],
    }
    request_path = evidence / "artifact-race-request.json"
    write_json(request_path, request)

    baseline = invoke_adapter(runtime, "evaluate", request_path)
    baseline_output = parse_output(baseline.stdout)
    expected_invalid = bool(
        baseline.returncode == 0
        and baseline_output is not None
        and baseline_output.get("detail_state_by_capture")
        == {"invalid": "INSTRUMENT_INVALID"}
        and baseline_output.get("detail_pass_by_capture") == {}
    )

    stop = threading.Event()

    def swapper() -> None:
        use_fail = False
        while not stop.is_set():
            swap_path = payload_dir / "capture-invalid.swap"
            swap_path.write_bytes(fail_bytes if use_fail else invalid_bytes)
            try:
                os.replace(swap_path, target)
            except PermissionError:
                if swap_path.exists():
                    swap_path.unlink()
            use_fail = not use_fail
            time.sleep(args.swap_interval)

    observed = None
    counts: dict[str, int] = {}
    thread = threading.Thread(target=swapper, daemon=True)
    thread.start()
    try:
        for attempt in range(1, args.attempts + 1):
            completed = invoke_adapter(runtime, "evaluate", request_path)
            key = f"exit-{completed.returncode}"
            counts[key] = counts.get(key, 0) + 1
            output = parse_output(completed.stdout)
            converted = bool(
                output is not None
                and output.get("detail_state_by_capture")
                == {"invalid": "DETAIL_FAIL"}
                and output.get("detail_pass_by_capture") == {"invalid": False}
            )
            if converted:
                observed = {
                    "attempt": attempt,
                    **completed_record(completed),
                }
                break
    finally:
        stop.set()
        thread.join()

    reproduced = observed is not None
    report = {
        "schema": "m149-adapter-artifact-race-v1",
        "status": "FAIL_RACE_REPRODUCED" if reproduced else "PASS_NO_RACE_OBSERVED",
        "source_dir": str(args.source_dir.resolve()),
        "work_dir": str(work),
        "adapter_sha256": sha256_file(runtime / "m138_adapter.py"),
        "request_sha256": sha256_file(request_path),
        "registered_invalid_artifact_sha256": sha256_bytes(invalid_bytes),
        "unregistered_fail_artifact_sha256": sha256_bytes(fail_bytes),
        "historical_fixture_hashes_match": bool(
            sha256_bytes(invalid_bytes) == EXPECTED_INVALID_SHA256
            and sha256_bytes(fail_bytes) == EXPECTED_FAIL_SHA256
        ),
        "filler_bytes": filler.stat().st_size,
        "baseline_is_invalid_without_boolean": expected_invalid,
        "baseline": completed_record(baseline),
        "attempt_counts": counts,
        "observed": observed,
    }
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    print(encoded, end="")
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8", newline="\n")
    if not expected_invalid:
        return 2
    return 1 if reproduced else 0


if __name__ == "__main__":
    raise SystemExit(main())
