#!/usr/bin/env python3
r"""Audit D:\personal\macro\requests without decoding or modifying captures.

The script enumerates every file, reads selected EXIF fields from every ARW,
groups them by leaf capture directory, and compares those directories with the
scorecard's explicit capture table. Input-tree snapshots before and after the
EXIF pass must match exactly.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REQUEST_ROOT = Path(r"D:\personal\macro\requests")
SCORECARD = REPO / "docs/proposals/2026-09-sota-scorecard.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
BASE_REV = "1bb4c9f8"
EXIFTOOL = Path(r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe")
TAGS = (
    "FileName",
    "Directory",
    "DateTimeOriginal",
    "ISO",
    "ExposureTime",
    "FNumber",
    "FocalLength",
    "ImageStabilization",
    "CameraModelName",
    "LensModel",
)


def emit(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8"))


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def git_blob(revision: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout.decode("utf-8").replace("\r\n", "\n")


def tree_snapshot(root: Path) -> dict[str, Any]:
    rows: list[tuple[str, int, int]] = []
    total_bytes = 0
    for base, _, names in os.walk(root):
        for name in names:
            path = Path(base) / name
            stat = path.stat()
            relative = str(path.relative_to(root)).replace("/", "\\")
            rows.append((relative, stat.st_size, stat.st_mtime_ns))
            total_bytes += stat.st_size
    rows.sort(key=lambda row: row[0].casefold())
    digest = hashlib.sha256()
    for relative, size, modified_ns in rows:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(modified_ns).encode("ascii"))
        digest.update(b"\n")
    return {
        "file_count": len(rows),
        "total_bytes": total_bytes,
        "path_size_mtime_sha256": digest.hexdigest().upper(),
    }


def exif_records(root: Path) -> list[dict[str, Any]]:
    command = [
        str(EXIFTOOL),
        "-json",
        "-r",
        "-ext",
        "ARW",
        "-n",
        *(f"-{tag}" for tag in TAGS),
        "--",
        str(root),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return json.loads(completed.stdout.decode("utf-8"))


def capture_table_paths(scorecard: str) -> set[str]:
    start = scorecard.index("### 2.2 Scored and control captures")
    end = scorecard.index("### 2.3 Holdout units and burn log", start)
    section = scorecard[start:end]
    return {
        match.group("path")
        for match in re.finditer(
            r"(?m)^\| `(?P<path>requests\\[^`]+)` \|", section
        )
    }


def value_counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    values = collections.Counter(
        "<MISSING>" if record.get(key) is None else str(record[key])
        for record in records
    )
    return dict(sorted(values.items()))


def relative_directory(record: dict[str, Any], root: Path) -> str:
    directory = Path(str(record["Directory"]))
    return str(directory.relative_to(root)).replace("/", "\\")


def build_audit() -> dict[str, Any]:
    if not REQUEST_ROOT.is_dir():
        raise RuntimeError(f"missing request root: {REQUEST_ROOT}")
    if not EXIFTOOL.is_file():
        raise RuntimeError(f"missing ExifTool: {EXIFTOOL}")

    before = tree_snapshot(REQUEST_ROOT)
    records = exif_records(REQUEST_ROOT)
    after = tree_snapshot(REQUEST_ROOT)
    if before != after:
        raise RuntimeError("request tree changed during read-only audit")

    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        grouped[relative_directory(record, REQUEST_ROOT)].append(record)

    arw_count = sum(
        1
        for base, _, names in os.walk(REQUEST_ROOT)
        for name in names
        if Path(name).suffix.lower() == ".arw"
    )
    if len(records) != arw_count:
        raise RuntimeError(
            f"ExifTool returned {len(records)} records for {arw_count} ARWs"
        )

    stacks = []
    for relative in sorted(grouped, key=str.casefold):
        stack_records = sorted(
            grouped[relative], key=lambda record: str(record["FileName"]).casefold()
        )
        stacks.append(
            {
                "path": f"requests\\{relative}",
                "frame_count": len(stack_records),
                "first_file": stack_records[0]["FileName"],
                "last_file": stack_records[-1]["FileName"],
                "first_datetime": min(
                    str(record["DateTimeOriginal"]) for record in stack_records
                ),
                "last_datetime": max(
                    str(record["DateTimeOriginal"]) for record in stack_records
                ),
                "exif": {
                    key: value_counts(stack_records, key)
                    for key in (
                        "ISO",
                        "ExposureTime",
                        "FNumber",
                        "FocalLength",
                        "ImageStabilization",
                        "CameraModelName",
                        "LensModel",
                    )
                },
            }
        )

    stack_paths = {stack["path"] for stack in stacks}
    current_paths = capture_table_paths(read_utf8(SCORECARD))
    baseline_paths = capture_table_paths(git_blob(BASE_REV, SCORECARD_PATH))
    version = subprocess.run(
        [str(EXIFTOOL), "-ver"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.decode("ascii").strip()

    return {
        "schema": "M160-request-registration-audit-v1",
        "method": (
            "Recursive filesystem enumeration and numeric EXIF metadata only; "
            "no image pixels decoded. The path/size/mtime tree fingerprint was "
            "identical before and after."
        ),
        "request_root": str(REQUEST_ROOT),
        "scorecard_baseline_revision": BASE_REV,
        "exiftool_version": version,
        "tree_before": before,
        "tree_after": after,
        "arw_count": arw_count,
        "stack_count": len(stacks),
        "baseline_registered_count": len(stack_paths & baseline_paths),
        "baseline_unregistered": sorted(stack_paths - baseline_paths, key=str.casefold),
        "current_registered_count": len(stack_paths & current_paths),
        "current_unregistered": sorted(stack_paths - current_paths, key=str.casefold),
        "scorecard_paths_not_on_disk": sorted(
            current_paths - stack_paths, key=str.casefold
        ),
        "stacks": stacks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if bool(args.out) == bool(args.verify):
        parser.error("provide exactly one of --out or --verify")

    audit = build_audit()
    if args.out:
        output = args.out.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(audit, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        emit(
            f"WROTE {output} stacks={audit['stack_count']} "
            f"arws={audit['arw_count']} "
            f"baseline_unregistered={len(audit['baseline_unregistered'])} "
            f"current_unregistered={len(audit['current_unregistered'])}"
        )
        return 0

    expected = json.loads(args.verify.resolve().read_text(encoding="utf-8"))
    if audit != expected:
        emit("VERDICT RED: live request audit differs from committed result")
        return 1
    emit(
        f"VERDICT GREEN: stacks={audit['stack_count']} arws={audit['arw_count']} "
        f"registered={audit['current_registered_count']} "
        f"unregistered={len(audit['current_unregistered'])} "
        f"tree_sha256={audit['tree_after']['path_size_mtime_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
