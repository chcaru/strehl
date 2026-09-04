from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
from typing import Any

from review_common import HERE, copy_registered_runtime, rebuild_bundle, sha256_file

DEFAULT_SOURCE = HERE / "fixtures" / "vulnerable-unbound-runtime"
MANIFEST_PATH = HERE / "mutation-manifest.json"


def classify(completed: subprocess.CompletedProcess[bytes]) -> tuple[str, dict[str, Any] | None]:
    parsed = None
    if completed.stdout:
        try:
            value = json.loads(completed.stdout)
            if isinstance(value, dict):
                parsed = value
        except json.JSONDecodeError:
            pass
    green = bool(
        completed.returncode == 0
        and parsed is not None
        and parsed.get("status") == "PASS"
        and set(parsed.get("checks", {}).values()) == {True}
    )
    return ("GREEN" if green else "RED"), parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the exact full-line M149 mutations against the adapter self-test."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "strehl-M149-mutation-run",
    )
    parser.add_argument(
        "--ids",
        help="Comma-separated mutation IDs; default is every behavioral mutation.",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = manifest["behavioral_mutations"]
    if args.ids:
        requested = {value for value in args.ids.split(",") if value}
        known = {row["id"] for row in rows}
        unknown = sorted(requested - known)
        if unknown:
            parser.error(f"unknown mutation IDs: {unknown}")
        rows = [row for row in rows if row["id"] in requested]

    work = args.work_dir.resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    results: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        mutation_id = row["id"]
        runtime = work / f"{index:02d}-{mutation_id}"
        copy_registered_runtime(args.source_dir.resolve(), runtime)
        target = runtime / row["file"]
        text = target.read_text(encoding="utf-8")
        count = text.count(row["anchor"])
        if count != row["anchor_expected_count"]:
            results.append(
                {
                    "id": mutation_id,
                    "result": "ANCHOR_ERROR",
                    "anchor_count": count,
                    "expected_anchor_count": row["anchor_expected_count"],
                }
            )
            continue

        target.write_bytes(
            text.replace(row["anchor"], row["replacement"]).encode("utf-8")
        )
        rebuild_bundle(runtime)
        completed = subprocess.run(
            [sys.executable, "-I", str(target), "--self-test"],
            cwd=runtime,
            capture_output=True,
            check=False,
            timeout=180,
        )
        result, parsed = classify(completed)
        failed_checks = []
        if parsed is not None:
            failed_checks = sorted(
                key
                for key, value in parsed.get("checks", {}).items()
                if value is not True
            )
        results.append(
            {
                "id": mutation_id,
                "result": result,
                "load_bearing_expectation": row["load_bearing_expectation"],
                "matches_load_bearing_expectation": (
                    result == row["load_bearing_expectation"]
                ),
                "observed_original": row["observed_original"],
                "anchor_count": count,
                "mutant_sha256": sha256_file(target),
                "returncode": completed.returncode,
                "status": None if parsed is None else parsed.get("status"),
                "passed_check_count": (
                    None if parsed is None else parsed.get("passed_check_count")
                ),
                "check_count": None if parsed is None else parsed.get("check_count"),
                "failed_checks": failed_checks,
                "stdout": "" if parsed is not None else completed.stdout.decode("utf-8"),
                "stderr": completed.stderr.decode("utf-8"),
            }
        )

    survivors = [
        row["id"]
        for row in results
        if row.get("load_bearing_expectation") == "RED"
        and row.get("result") == "GREEN"
    ]
    inert_failures = [
        row["id"]
        for row in results
        if row.get("load_bearing_expectation") == "GREEN"
        and row.get("result") != "GREEN"
    ]
    anchor_errors = [
        row["id"] for row in results if row.get("result") == "ANCHOR_ERROR"
    ]
    report = {
        "schema": "m149-adapter-mutation-report-v1",
        "source_dir": str(args.source_dir.resolve()),
        "work_dir": str(work),
        "mutation_count": len(results),
        "surviving_substantive_mutations": survivors,
        "inert_control_failures": inert_failures,
        "anchor_errors": anchor_errors,
        "status": (
            "ERROR"
            if anchor_errors or inert_failures
            else "FAIL_SURVIVORS"
            if survivors
            else "PASS_ALL_SUBSTANTIVE_RED"
        ),
        "results": results,
    }
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    print(encoded, end="")
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8", newline="\n")
    if anchor_errors or inert_failures:
        return 2
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
