#!/usr/bin/env python3
"""Record the retained fork identity and select the nearest retained revision."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


SCHEMA = "m175-fork-revision-selection-v1"
EXPECTED_FIRST = "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"
UPSTREAM = "https://github.com/PetteriAimonen/focus-stack"


class InspectionFailure(RuntimeError):
    pass


def git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise InspectionFailure(
            f"git {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": sha256(data),
        "last_write_utc": datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat(),
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_history(repo: Path) -> list[dict[str, Any]]:
    raw = git(
        repo,
        "log",
        "--reverse",
        "--all",
        "--format=%H%x00%P%x00%cI%x00%s",
        "--",
        "focus-stack",
    ).decode("utf-8", errors="strict")
    commits: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line:
            continue
        fields = line.split("\0")
        if len(fields) != 4:
            raise InspectionFailure(f"cannot parse history line: {line!r}")
        commits.append(
            {
                "commit_sha1": fields[0],
                "parents": fields[1].split() if fields[1] else [],
                "committer_time": fields[2],
                "subject": fields[3],
            }
        )
    if len(commits) < 2:
        raise InspectionFailure("retained focus-stack history has fewer than two commits")
    return commits


def diff_summary(repo: Path, older: str, newer: str) -> dict[str, int]:
    raw = git(
        repo, "diff", "--numstat", older, newer, "--", "focus-stack"
    ).decode("utf-8", errors="strict")
    files = insertions = deletions = 0
    for line in raw.splitlines():
        if not line:
            continue
        added, removed, _ = line.split("\t", 2)
        files += 1
        if added != "-":
            insertions += int(added)
        if removed != "-":
            deletions += int(removed)
    return {
        "files_changed": files,
        "insertions": insertions,
        "deletions": deletions,
    }


def inspect(repo: Path, archive_log: Path, archive_output: Path) -> dict[str, Any]:
    history = parse_history(repo)
    selected = history[0]
    if selected["commit_sha1"] != EXPECTED_FIRST or selected["parents"]:
        raise InspectionFailure(
            "the earliest retained focus-stack revision is not the scorecard pin"
        )
    following = history[1]
    readme = git(repo, "show", f"{EXPECTED_FIRST}:focus-stack/README.md")
    licence = git(repo, "show", f"{EXPECTED_FIRST}:focus-stack/LICENSE.md")
    if UPSTREAM.encode("ascii") not in readme:
        raise InspectionFailure("selected README does not identify the expected upstream")
    copyright_match = re.search(
        rb"Copyright \(c\) [^\r\n]+", licence, flags=re.IGNORECASE
    )
    if copyright_match is None:
        raise InspectionFailure("selected licence has no copyright line")

    archive_log_record = file_record(archive_log)
    selected_time = datetime.fromisoformat(selected["committer_time"])
    archive_time = datetime.fromisoformat(archive_log_record["last_write_utc"])
    delta_seconds = (selected_time - archive_time).total_seconds()
    if delta_seconds <= 0:
        raise InspectionFailure("selected revision does not postdate the archived run log")

    output_record: dict[str, Any]
    if archive_output.is_file():
        output_record = file_record(archive_output)
    else:
        output_record = {
            "path": str(archive_output.resolve()),
            "status": "ABSENT",
        }

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "repository": {
            "path": str(repo.resolve()),
            "origin": git(repo, "config", "--get", "remote.origin.url")
            .decode("utf-8", errors="strict")
            .strip(),
            "source_subtree": str((repo / "focus-stack").resolve()),
        },
        "identity": {
            "upstream_project": "PetteriAimonen/focus-stack",
            "upstream_url": UPSTREAM,
            "readme_blob_sha1": git(
                repo,
                "rev-parse",
                f"{EXPECTED_FIRST}:focus-stack/README.md",
            )
            .decode()
            .strip(),
            "readme_sha256": sha256(readme),
            "licence_blob_sha1": git(
                repo,
                "rev-parse",
                f"{EXPECTED_FIRST}:focus-stack/LICENSE.md",
            )
            .decode()
            .strip(),
            "licence_sha256": sha256(licence),
            "licence_copyright_line": copyright_match.group(0).decode(
                "utf-8", errors="strict"
            ),
        },
        "archived_run": {
            "log": archive_log_record,
            "output": output_record,
            "producer_identity": "UNKNOWN",
        },
        "selected_revision": selected,
        "selection_basis": {
            "kind": "EARLIEST_AND_NEAREST_RETAINED_SOURCE_AFTER_ARCHIVED_RUN",
            "seconds_after_archived_log_last_write": delta_seconds,
            "not_claimed_as_archived_producer": True,
        },
        "next_retained_revision": {
            **following,
            "diff_from_selected": diff_summary(
                repo, selected["commit_sha1"], following["commit_sha1"]
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--archive-log", required=True)
    parser.add_argument("--archive-output", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    try:
        result = inspect(
            Path(args.repo), Path(args.archive_log), Path(args.archive_output)
        )
    except BaseException as exc:
        result = {
            "schema": SCHEMA,
            "status": "FAIL",
            "failure_class": type(exc).__name__,
            "reason": str(exc),
        }
        write_json(out, result)
        print(json.dumps(result, sort_keys=True))
        return 1
    write_json(out, result)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
