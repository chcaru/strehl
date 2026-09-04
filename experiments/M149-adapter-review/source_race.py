from __future__ import annotations

import argparse
import copy
import hashlib
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
    completed_record,
    invalid_and_fail_payloads,
    invoke_adapter,
    prepare_bound_runtime,
    sha256_bytes,
    sha256_file,
    write_json,
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
        description="Reproduce M149's verified-core source hash/use race."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "strehl-M149-source-race-run",
    )
    parser.add_argument("--attempts", type=int, default=80)
    parser.add_argument("--swap-interval", type=float, default=0.002)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    work = args.work_dir.resolve()
    if work.exists():
        shutil.rmtree(work)
    runtime = work / "runtime"
    evidence = work / "evidence"
    payload_dir = evidence / "payloads"
    payload_dir.mkdir(parents=True)

    core_module, contract, binding = prepare_bound_runtime(
        args.source_dir.resolve(), runtime
    )
    invalid, _ = invalid_and_fail_payloads(core_module, contract, binding)
    payload_path = payload_dir / "invalid.json"
    write_json(payload_path, invalid)
    ref = {
        "path": "payloads/invalid.json",
        "sha256": sha256_file(payload_path),
    }
    request = {
        "schema": "m135-m138-evaluate-request/v1",
        "capture_ids": ["invalid"],
        "artifacts": [copy.deepcopy(ref)],
        "binding_hashes": binding_hashes(runtime, binding),
        "comparisons": [
            {"capture_id": "invalid", "payload": copy.deepcopy(ref)}
        ],
    }
    request_path = evidence / "missing-flat-request.json"
    write_json(request_path, request)
    command_mode = "evaluate"

    baseline = invoke_adapter(runtime, command_mode, request_path)
    baseline_output = parse_output(baseline.stdout)
    expected_invalid = bool(
        baseline.returncode == 0
        and baseline_output is not None
        and baseline_output.get("detail_state_by_capture")
        == {"invalid": "INSTRUMENT_INVALID"}
        and baseline_output.get("detail_pass_by_capture") == {}
    )

    core_path = runtime / "comparison_checker.py"
    registered_core = core_path.read_bytes()
    marker = work / "UNVERIFIED_CORE_FORCED_FALSE"
    line_end = b"\r\n" if b"\r\n" in registered_core else b"\n"
    plant = line_end.join(
        [
            b"",
            b"# M149 unregistered replacement",
            b"def adjudicate(payload, binding, contract):",
            (
                "    Path(r'"
                + str(marker).replace("\\", "\\\\")
                + "').write_text('EXECUTED', encoding='utf-8')"
            ).encode("utf-8"),
            b'    return decision(contract, "DETAIL_FAIL", payload.get("capture_id"), reason="M149 unverified core forced scientific failure")',
            b"",
        ]
    )
    unregistered_core = registered_core + plant

    stop = threading.Event()

    def swapper() -> None:
        use_bad = False
        while not stop.is_set():
            swap_path = runtime / "comparison_checker.swap"
            swap_path.write_bytes(
                unregistered_core if use_bad else registered_core
            )
            try:
                os.replace(swap_path, core_path)
            except PermissionError:
                if swap_path.exists():
                    swap_path.unlink()
            use_bad = not use_bad
            time.sleep(args.swap_interval)

    observed = None
    counts: dict[str, int] = {}
    thread = threading.Thread(target=swapper, daemon=True)
    thread.start()
    try:
        for attempt in range(1, args.attempts + 1):
            if marker.exists():
                marker.unlink()
            completed = invoke_adapter(runtime, command_mode, request_path)
            key = f"exit-{completed.returncode}"
            counts[key] = counts.get(key, 0) + 1
            output = parse_output(completed.stdout)
            converted = bool(
                output is not None
                and output.get("detail_state_by_capture")
                == {"invalid": "DETAIL_FAIL"}
                and output.get("detail_pass_by_capture") == {"invalid": False}
            )
            if marker.exists() and converted:
                observed = {
                    "attempt": attempt,
                    "sentinel_executed": True,
                    **completed_record(completed),
                }
                break
    finally:
        stop.set()
        thread.join()

    reproduced = observed is not None
    report = {
        "schema": "m149-adapter-source-race-v1",
        "status": "FAIL_RACE_REPRODUCED" if reproduced else "PASS_NO_RACE_OBSERVED",
        "source_dir": str(args.source_dir.resolve()),
        "work_dir": str(work),
        "adapter_sha256": sha256_file(runtime / "m138_adapter.py"),
        "request_sha256": sha256_file(request_path),
        "registered_core_sha256": sha256_bytes(registered_core),
        "unregistered_core_sha256": sha256_bytes(unregistered_core),
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
