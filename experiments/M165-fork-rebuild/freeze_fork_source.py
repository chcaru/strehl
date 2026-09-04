#!/usr/bin/env python3
"""Freeze a retained focus-stack source revision without reading the worktree."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


SCHEMA = "m165-fork-source-pin-v1"


class FreezeFailure(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise FreezeFailure(
            f"git {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_pin(repo: Path, requested_commit: str, frozen_utc: str) -> dict[str, Any]:
    try:
        frozen = datetime.fromisoformat(frozen_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FreezeFailure(f"invalid --frozen-utc: {exc}") from exc
    if frozen.utcoffset() is None:
        raise FreezeFailure("--frozen-utc must include an offset")

    commit = run_git(repo, "rev-parse", f"{requested_commit}^{{commit}}").decode().strip()
    if len(commit) != 40:
        raise FreezeFailure(f"resolved commit is not a full SHA-1: {commit!r}")
    metadata = (
        run_git(
            repo,
            "show",
            "-s",
            "--format=%H%x00%P%x00%aI%x00%cI%x00%s",
            commit,
        )
        .decode("utf-8", errors="strict")
        .rstrip("\n")
        .split("\0")
    )
    if len(metadata) != 5 or metadata[0] != commit:
        raise FreezeFailure("could not parse pinned commit metadata")

    subtree_line = run_git(repo, "ls-tree", commit, "focus-stack").decode().strip()
    fields, subtree_path = subtree_line.split("\t", 1)
    mode, kind, subtree_oid = fields.split()
    if mode != "040000" or kind != "tree" or subtree_path != "focus-stack":
        raise FreezeFailure(f"focus-stack subtree is invalid: {subtree_line!r}")

    raw_entries = run_git(
        repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", "focus-stack"
    )
    entries: list[dict[str, Any]] = []
    for record in raw_entries.split(b"\0"):
        if not record:
            continue
        metadata_bytes, path_bytes = record.split(b"\t", 1)
        file_mode, object_type, object_id = metadata_bytes.decode("ascii").split()
        if object_type != "blob":
            raise FreezeFailure(f"unexpected source object type {object_type!r}")
        path = path_bytes.decode("utf-8")
        blob = run_git(repo, "cat-file", "blob", object_id)
        entries.append(
            {
                "path": path,
                "mode": file_mode,
                "git_blob_sha1": object_id,
                "bytes": len(blob),
                "sha256": sha256(blob),
            }
        )
    entries.sort(key=lambda value: value["path"])
    if not entries:
        raise FreezeFailure("pinned focus-stack subtree contains no files")

    try:
        origin = run_git(repo, "config", "--get", "remote.origin.url").decode().strip()
    except FreezeFailure:
        origin = None

    return {
        "schema": SCHEMA,
        "status": "FROZEN",
        "frozen_utc": frozen.isoformat(),
        "hash_algorithms": {
            "git_object_ids": "SHA-1",
            "file_and_manifest_hashes": "SHA-256",
        },
        "repository": {
            "path": str(repo.resolve()),
            "origin": origin,
        },
        "commit": {
            "requested": requested_commit,
            "resolved": metadata[0],
            "parents": metadata[1].split() if metadata[1] else [],
            "author_utc_offset_time": metadata[2],
            "committer_utc_offset_time": metadata[3],
            "subject": metadata[4],
        },
        "source_subtree": {
            "path": "focus-stack",
            "git_tree_sha1": subtree_oid,
            "file_count": len(entries),
            "total_file_bytes": sum(value["bytes"] for value in entries),
            "manifest_sha256": sha256(canonical_json(entries)),
            "files": entries,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--frozen-utc", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    try:
        result = build_pin(Path(args.repo), args.commit, args.frozen_utc)
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
