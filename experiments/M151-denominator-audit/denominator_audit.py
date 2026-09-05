#!/usr/bin/env python3
"""Deterministic denominator-provenance corpus scanner and audit checker.

Only direct-child Markdown files in ``docs/research`` and ``docs/proposals``
are in scope.  Markdown structure is intentionally not filtered: prose,
tables, block quotes, and fenced examples all remain reviewable evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = 1
REVIEWER_COUNT = 8
CORPUS_DIRECTORIES = ("docs/research", "docs/proposals")
CORPUS_PATTERNS = ("docs/research/*.md", "docs/proposals/*.md")
FORBIDDEN_PATH = r"D:\personal\macro\requests\7-aperture-pairs"
CLASSIFICATIONS = frozenset(
    {
        "population",
        "fixed_subsample",
        "cap",
        "fixture",
        "unstated",
        "out_of_scope",
    }
)
EVIDENCE_LABELS = frozenset(
    {"MEASURED", "VERIFIED", "DERIVED", "ARGUED", "UNVERIFIED"}
)
REPORT_EVIDENCE_LABELS = (
    "VERIFIED BY RUNNING",
    "INFERRED BY READING",
)
RESOLUTION_STATUSES = frozenset(
    {
        "open",
        "unresolved",
        "needs_repair",
        "repaired",
        "resolved",
        "verified",
        "accepted",
        "not_applicable",
    }
)
NUMBER = r"[+-]?(?:(?:\d+(?:,\d{3})*)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
DETECTORS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "percentage",
        re.compile(
            rf"(?<![\w.]){NUMBER}\s*(?:%(?!\w)|percent(?:age)?s?\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "numeric_fraction",
        re.compile(
            rf"(?<![\w.]){NUMBER}\s*/\s*{NUMBER}(?!\w)",
            re.IGNORECASE,
        ),
    ),
    (
        "number_of_number",
        re.compile(
            rf"(?<![\w.]){NUMBER}\s+(?:out\s+of|of)(?:\s+the)?\s+"
            rf"{NUMBER}(?!\w)",
            re.IGNORECASE,
        ),
    ),
    (
        "rate_or_coverage_claim",
        re.compile(
            r"\b(?:"
            r"rates?|coverage|"
            r"pass(?:ed|es|ing)?|"
            r"success(?:es|ful|fully)?|"
            r"eligible|eligibility|"
            r"qualif(?:y|ies|ied|ying|ication|ications)|"
            r"admit(?:s|ted|ting)?|admissions?"
            r")\b",
            re.IGNORECASE,
        ),
    ),
)


class AuditError(ValueError):
    """A deterministic input or contract error."""


def _lexical_windows_path(value: os.PathLike[str] | str) -> str:
    """Normalize a path lexically, without any filesystem call."""

    raw = os.fspath(value).strip().replace("/", "\\")
    lowered = raw.casefold()
    if lowered.startswith("\\\\?\\unc\\"):
        raw = "\\\\" + raw[8:]
    elif lowered.startswith(("\\\\?\\", "\\\\.\\")):
        raw = raw[4:]
    normalized = ntpath.normpath(raw)
    drive, tail = ntpath.splitdrive(normalized)
    # Win32 ignores trailing spaces and dots in ordinary path components.
    # Canonicalize those aliases only after normpath has interpreted "."/"..".
    components = [
        component.rstrip(" .")
        for component in tail.split("\\")
        if component
    ]
    separator = "\\" if tail.startswith("\\") else ""
    canonical = drive + separator + "\\".join(components)
    return ntpath.normcase(canonical)


def reject_forbidden_path(value: os.PathLike[str] | str) -> None:
    """Reject the forbidden capture tree before resolving or opening a path."""

    normalized = _lexical_windows_path(value)
    forbidden = _lexical_windows_path(FORBIDDEN_PATH)
    if normalized == forbidden or normalized.startswith(forbidden + "\\"):
        raise AuditError(f"forbidden path rejected before filesystem access: {value}")


def checked_path(value: os.PathLike[str] | str) -> Path:
    reject_forbidden_path(value)
    return Path(value)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    reject_forbidden_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    payload = (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    atomic_write(path, payload)


def discover_corpus(repo_root: os.PathLike[str] | str) -> list[tuple[str, Path]]:
    """Return only direct-child ``*.md`` files from the two frozen directories."""

    root = checked_path(repo_root)
    rows: list[tuple[str, Path]] = []
    for relative_directory in CORPUS_DIRECTORIES:
        directory = root / Path(relative_directory)
        if not directory.is_dir():
            raise AuditError(f"required corpus directory is missing: {relative_directory}")
        for path in directory.iterdir():
            if path.is_file() and path.suffix == ".md":
                relative = path.relative_to(root).as_posix()
                rows.append((relative, path))
    rows.sort(key=lambda row: row[0])
    return rows


def git_states(repo_root: os.PathLike[str] | str) -> dict[str, str] | None:
    """Return porcelain XY states, or ``None`` when the root is not a Git tree."""

    root = checked_path(repo_root)
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError:
        return None
    if probe.returncode != 0 or probe.stdout.strip() != b"true":
        return None
    command = [
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--no-renames",
        "--",
        *CORPUS_DIRECTORIES,
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise AuditError(f"git status failed: {detail or result.returncode}")
    states: dict[str, str] = {}
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        text = raw.decode("utf-8", errors="surrogateescape")
        if len(text) < 4:
            raise AuditError(f"malformed git porcelain record: {text!r}")
        states[text[3:].replace("\\", "/")] = text[:2]
    return states


def markdown_context(line: str, inside_fence: bool) -> str:
    if inside_fence or re.match(r"^\s*(?:```|~~~)", line):
        return "fence"
    if re.match(r"^\s*>", line):
        return "quote"
    if "|" in line:
        return "table"
    return "text"


def occurrence_id(
    path: str,
    kind: str,
    source_line: str,
    match_text: str,
    identity_ordinal: int,
) -> str:
    identity = "\0".join(
        (path, kind, source_line, match_text, str(identity_ordinal))
    ).encode("utf-8")
    return "den-" + hashlib.sha256(identity).hexdigest()[:24]


def detect_candidates(path: str, text: str, file_sha256: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    identity_counts: Counter[tuple[str, str, str]] = Counter()
    inside_fence = False
    fence_marker: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        fence = re.match(r"^(`{3,}|~{3,})", stripped)
        context = markdown_context(line, inside_fence)
        matches: list[tuple[int, int, str, str]] = []
        for kind, detector in DETECTORS:
            for match in detector.finditer(line):
                matches.append((match.start(), match.end(), kind, match.group(0)))
        matches.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
        for start, end, kind, match_text in matches:
            identity_key = (kind, line, match_text)
            identity_counts[identity_key] += 1
            ordinal = identity_counts[identity_key]
            rows.append(
                {
                    "schema": "denominator-candidate-v1",
                    "occurrence_id": occurrence_id(
                        path, kind, line, match_text, ordinal
                    ),
                    "path": path,
                    "file_sha256": file_sha256,
                    "line": line_number,
                    "column_start": start + 1,
                    "column_end": end + 1,
                    "kind": kind,
                    "match_text": match_text,
                    "source_line": line,
                    "markdown_context": context,
                    "identity_ordinal": ordinal,
                }
            )
        if fence:
            marker = fence.group(1)[0]
            if not inside_fence:
                inside_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                inside_fence = False
                fence_marker = None
    return rows


def scan_corpus(
    repo_root: os.PathLike[str] | str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = checked_path(repo_root)
    discovered = discover_corpus(root)
    states = git_states(root)
    files: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for relative, path in discovered:
        payload = path.read_bytes()
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AuditError(f"{relative}: not UTF-8: {error}") from error
        digest = sha256_bytes(payload)
        found = detect_candidates(relative, text, digest)
        files.append(
            {
                "path": relative,
                "sha256": digest,
                "lines": len(text.splitlines()),
                "bytes": len(payload),
                "git_state": (
                    "not_git" if states is None else states.get(relative, "clean")
                ),
                "candidate_count": len(found),
            }
        )
        candidates.extend(found)
    candidates.sort(
        key=lambda row: (
            row["path"],
            row["line"],
            row["column_start"],
            row["column_end"],
            row["kind"],
            row["occurrence_id"],
        )
    )
    candidate_payload = jsonl_bytes(candidates)
    unsigned = {
        "schema": "denominator-corpus-manifest-v1",
        "schema_version": SCHEMA_VERSION,
        "patterns": list(CORPUS_PATTERNS),
        "direct_children_only": True,
        "reviewer_count": REVIEWER_COUNT,
        "sharding": "whole-file greedy LPT by candidate_count, stable ties",
        "file_count": len(files),
        "candidate_count": len(candidates),
        "total_lines": sum(row["lines"] for row in files),
        "total_bytes": sum(row["bytes"] for row in files),
        "files": files,
        "corpus_sha256": payload_sha256(files),
        "candidates_sha256": sha256_bytes(candidate_payload),
    }
    return unsigned | {"manifest_sha256": payload_sha256(unsigned)}, candidates


def balanced_shards(
    manifest: dict[str, Any],
    candidates: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assign whole files with deterministic greedy longest-processing-time."""

    by_file: dict[str, list[str]] = defaultdict(list)
    for candidate in candidates:
        by_file[candidate["path"]].append(candidate["occurrence_id"])
    assignments: list[list[dict[str, Any]]] = [[] for _ in range(REVIEWER_COUNT)]
    loads = [0] * REVIEWER_COUNT
    ordered_files = sorted(
        manifest["files"], key=lambda row: (-row["candidate_count"], row["path"])
    )
    for file_row in ordered_files:
        shard_index = min(range(REVIEWER_COUNT), key=lambda index: (loads[index], index))
        assignments[shard_index].append(file_row)
        loads[shard_index] += file_row["candidate_count"]
    shards: list[dict[str, Any]] = []
    for index, assigned in enumerate(assignments):
        assigned_paths = sorted(row["path"] for row in assigned)
        ids = [
            occurrence
            for path in assigned_paths
            for occurrence in by_file.get(path, [])
        ]
        unsigned = {
            "schema": "denominator-review-shard-v1",
            "schema_version": SCHEMA_VERSION,
            "reviewer": f"reviewer-{index + 1:02d}",
            "manifest_sha256": manifest["manifest_sha256"],
            "corpus_sha256": manifest["corpus_sha256"],
            "candidate_count": len(ids),
            "file_count": len(assigned_paths),
            "files": assigned_paths,
            "candidate_ids": ids,
        }
        shards.append(unsigned | {"shard_sha256": payload_sha256(unsigned)})
    return shards


def scan_to_directory(
    repo_root: os.PathLike[str] | str,
    output_directory: os.PathLike[str] | str,
) -> dict[str, Any]:
    reject_forbidden_path(repo_root)
    out = checked_path(output_directory)
    manifest, candidates, shards = build_artifacts(repo_root)
    atomic_json(out / "corpus-manifest.json", manifest)
    atomic_write(out / "candidates.jsonl", jsonl_bytes(candidates))
    shard_directory = out / "shards"
    expected_names = {f"shard-{index:02d}.json" for index in range(1, 9)}
    if shard_directory.is_dir():
        for old_shard in shard_directory.glob("shard-*.json"):
            if old_shard.name not in expected_names and old_shard.is_file():
                old_shard.unlink()
    for index, shard in enumerate(shards, start=1):
        atomic_json(shard_directory / f"shard-{index:02d}.json", shard)
    return manifest


def build_artifacts(
    repo_root: os.PathLike[str] | str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build all deterministic artifacts in memory without writing them."""

    reject_forbidden_path(repo_root)
    manifest, candidates = scan_corpus(repo_root)
    shards = balanced_shards(manifest, candidates)
    loads = [row["candidate_count"] for row in shards]
    manifest = dict(manifest)
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    unsigned["shard_candidate_loads"] = loads
    unsigned["shard_candidate_load_spread"] = max(loads) - min(loads)
    manifest = unsigned | {"manifest_sha256": payload_sha256(unsigned)}
    # Shards bind to the final manifest hash, including the reported load summary.
    shards = balanced_shards(manifest, candidates)
    return manifest, candidates, shards


def read_json(path: os.PathLike[str] | str) -> dict[str, Any]:
    source = checked_path(path)
    try:
        value = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"{source}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise AuditError(f"{source}: expected a JSON object")
    return value


def read_jsonl(path: os.PathLike[str] | str) -> tuple[bytes, list[dict[str, Any]]]:
    source = checked_path(path)
    try:
        payload = source.read_bytes()
        text = payload.decode("ascii")
    except (OSError, UnicodeError) as error:
        raise AuditError(f"{source}: cannot read ASCII JSONL: {error}") from error
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise AuditError(f"{source}:{line_number}: blank JSONL records are forbidden")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise AuditError(f"{source}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(row, dict):
            raise AuditError(f"{source}:{line_number}: expected a JSON object")
        rows.append(row)
    return payload, rows


def validate_manifest_and_candidates(
    manifest_path: os.PathLike[str] | str,
    candidates_path: os.PathLike[str] | str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    reject_forbidden_path(manifest_path)
    reject_forbidden_path(candidates_path)
    manifest = read_json(manifest_path)
    candidate_payload, candidates = read_jsonl(candidates_path)
    errors: list[str] = []
    if manifest.get("schema") != "denominator-corpus-manifest-v1":
        errors.append("manifest schema is not denominator-corpus-manifest-v1")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"manifest schema_version must be {SCHEMA_VERSION}")
    if manifest.get("patterns") != list(CORPUS_PATTERNS):
        errors.append("manifest patterns do not match the frozen corpus scope")
    if manifest.get("direct_children_only") is not True:
        errors.append("manifest direct_children_only must be JSON true")
    if manifest.get("reviewer_count") != REVIEWER_COUNT:
        errors.append(f"manifest reviewer_count must be {REVIEWER_COUNT}")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if manifest.get("manifest_sha256") != payload_sha256(unsigned):
        errors.append("manifest_sha256 mismatch")
    if manifest.get("candidates_sha256") != sha256_bytes(candidate_payload):
        errors.append("candidates_sha256 mismatch")
    if manifest.get("candidate_count") != len(candidates):
        errors.append("manifest candidate_count does not match candidates JSONL")
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest files must be a list")
        files = []
    if manifest.get("file_count") != len(files):
        errors.append("manifest file_count does not match files")
    file_map: dict[str, dict[str, Any]] = {}
    prior_file_path: str | None = None
    hex_digest = re.compile(r"^[0-9a-f]{64}$")
    for index, row in enumerate(files, start=1):
        prefix = f"manifest file record {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        path = row.get("path")
        if not isinstance(path, str):
            errors.append(f"{prefix}: path must be a string")
            continue
        parent, separator, name = path.rpartition("/")
        if (
            parent not in CORPUS_DIRECTORIES
            or separator != "/"
            or not name
            or "/" in name
            or not name.endswith(".md")
        ):
            errors.append(f"{prefix}: path is outside the direct-child corpus scope")
        if prior_file_path is not None and path <= prior_file_path:
            errors.append("manifest files must be sorted by unique path")
        prior_file_path = path
        if path in file_map:
            errors.append(f"{prefix}: duplicate path {path}")
        else:
            file_map[path] = row
        if not isinstance(row.get("sha256"), str) or not hex_digest.fullmatch(
            row["sha256"]
        ):
            errors.append(f"{prefix}: sha256 must be 64 lowercase hexadecimal digits")
        for field in ("lines", "bytes", "candidate_count"):
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{prefix}: {field} must be a non-negative integer")
        if not isinstance(row.get("git_state"), str) or not row["git_state"]:
            errors.append(f"{prefix}: git_state must be a non-empty string")
    if len(file_map) != len(files):
        errors.append("manifest file paths must be unique strings")
    if manifest.get("total_lines") != sum(
        row.get("lines", 0)
        for row in file_map.values()
        if isinstance(row.get("lines"), int) and not isinstance(row.get("lines"), bool)
    ):
        errors.append("manifest total_lines does not match file inventory")
    if manifest.get("total_bytes") != sum(
        row.get("bytes", 0)
        for row in file_map.values()
        if isinstance(row.get("bytes"), int) and not isinstance(row.get("bytes"), bool)
    ):
        errors.append("manifest total_bytes does not match file inventory")
    if manifest.get("corpus_sha256") != payload_sha256(files):
        errors.append("manifest corpus_sha256 does not match file inventory")
    loads = manifest.get("shard_candidate_loads")
    if (
        not isinstance(loads, list)
        or len(loads) != REVIEWER_COUNT
        or not all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in loads
        )
    ):
        errors.append("manifest shard_candidate_loads must contain 8 non-negative integers")
    else:
        if sum(loads) != len(candidates):
            errors.append("manifest shard_candidate_loads do not sum to candidate_count")
        if manifest.get("shard_candidate_load_spread") != max(loads) - min(loads):
            errors.append("manifest shard_candidate_load_spread mismatch")
    ids: set[str] = set()
    counts: Counter[str] = Counter()
    prior_sort_key: tuple[Any, ...] | None = None
    for index, row in enumerate(candidates, start=1):
        prefix = f"candidate record {index}"
        if row.get("schema") != "denominator-candidate-v1":
            errors.append(f"{prefix}: invalid candidate schema")
        occurrence = row.get("occurrence_id")
        if not isinstance(occurrence, str):
            errors.append(f"{prefix}: occurrence_id must be a string")
        elif occurrence in ids:
            errors.append(f"{prefix}: duplicate occurrence_id {occurrence}")
        else:
            ids.add(occurrence)
        path = row.get("path")
        if path not in file_map:
            errors.append(f"{prefix}: unknown corpus path {path!r}")
        else:
            counts[path] += 1
            if row.get("file_sha256") != file_map[path].get("sha256"):
                errors.append(f"{prefix}: file_sha256 does not match manifest")
        required_id_fields = (
            row.get("kind"),
            row.get("source_line"),
            row.get("match_text"),
            row.get("identity_ordinal"),
        )
        if (
            isinstance(path, str)
            and isinstance(required_id_fields[0], str)
            and isinstance(required_id_fields[1], str)
            and isinstance(required_id_fields[2], str)
            and isinstance(required_id_fields[3], int)
        ):
            expected = occurrence_id(path, *required_id_fields)
            if occurrence != expected:
                errors.append(f"{prefix}: occurrence_id does not match stable identity")
        line_number = row.get("line")
        if (
            not isinstance(line_number, int)
            or isinstance(line_number, bool)
            or line_number < 1
        ):
            errors.append(f"{prefix}: line must be a positive integer")
        elif path in file_map and isinstance(file_map[path].get("lines"), int):
            if line_number > file_map[path]["lines"]:
                errors.append(f"{prefix}: line exceeds the file line count")
        start = row.get("column_start")
        end = row.get("column_end")
        source_line = row.get("source_line")
        match_text = row.get("match_text")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 1
            or end <= start
        ):
            errors.append(f"{prefix}: columns must be valid one-based half-open offsets")
        elif isinstance(source_line, str) and isinstance(match_text, str):
            if end - 1 > len(source_line) or source_line[start - 1 : end - 1] != match_text:
                errors.append(f"{prefix}: columns do not select match_text")
        if row.get("kind") not in {name for name, _ in DETECTORS}:
            errors.append(f"{prefix}: unknown detector kind")
        if row.get("markdown_context") not in {"text", "table", "quote", "fence"}:
            errors.append(f"{prefix}: invalid markdown_context")
        ordinal = row.get("identity_ordinal")
        if (
            not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or ordinal < 1
        ):
            errors.append(f"{prefix}: identity_ordinal must be a positive integer")
        sort_key = (
            path,
            line_number,
            start,
            end,
            row.get("kind"),
            occurrence,
        )
        if prior_sort_key is not None:
            try:
                if sort_key < prior_sort_key:
                    errors.append("candidates JSONL is not in deterministic order")
                    prior_sort_key = None
                    continue
            except TypeError:
                errors.append(f"{prefix}: invalid candidate sort fields")
        prior_sort_key = sort_key
    for path, row in file_map.items():
        if row.get("candidate_count") != counts[path]:
            errors.append(f"{path}: candidate_count does not match JSONL")
    return manifest, candidates, errors


def expand_json_paths(
    values: Sequence[os.PathLike[str] | str],
    *,
    suffix: str,
) -> list[Path]:
    for value in values:
        reject_forbidden_path(value)
    paths: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            paths.extend(
                sorted(
                    (
                        child
                        for child in path.iterdir()
                        if child.is_file() and child.suffix == suffix
                    ),
                    key=lambda child: child.name,
                )
            )
        else:
            paths.append(path)
    return paths


def load_and_validate_shards(
    shard_inputs: Sequence[os.PathLike[str] | str],
    manifest: dict[str, Any],
    candidates: Sequence[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, str], list[str]]:
    paths = expand_json_paths(shard_inputs, suffix=".json")
    errors: list[str] = []
    if len(paths) != REVIEWER_COUNT:
        errors.append(f"expected exactly {REVIEWER_COUNT} shard manifests, found {len(paths)}")
    file_owner: dict[str, str] = {}
    candidate_owner: dict[str, str] = {}
    known_files = {
        row.get("path")
        for row in manifest.get("files", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    candidate_map = {
        row.get("occurrence_id"): row
        for row in candidates
        if isinstance(row.get("occurrence_id"), str)
    }
    reviewers: set[str] = set()
    loaded_by_reviewer: dict[str, dict[str, Any]] = {}
    for path in paths:
        shard = read_json(path)
        unsigned = {key: value for key, value in shard.items() if key != "shard_sha256"}
        if shard.get("schema") != "denominator-review-shard-v1":
            errors.append(f"{path}: invalid shard schema")
        if shard.get("shard_sha256") != payload_sha256(unsigned):
            errors.append(f"{path}: shard_sha256 mismatch")
        if shard.get("manifest_sha256") != manifest.get("manifest_sha256"):
            errors.append(f"{path}: manifest_sha256 mismatch")
        reviewer = shard.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer:
            errors.append(f"{path}: reviewer must be a non-empty string")
            continue
        if reviewer in reviewers:
            errors.append(f"{path}: duplicate reviewer {reviewer}")
        reviewers.add(reviewer)
        loaded_by_reviewer[reviewer] = shard
        files = shard.get("files")
        ids = shard.get("candidate_ids")
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            errors.append(f"{path}: files must be a string list")
            files = []
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            errors.append(f"{path}: candidate_ids must be a string list")
            ids = []
        if files != sorted(files) or len(files) != len(set(files)):
            errors.append(f"{path}: files must be sorted and unique")
        if len(ids) != len(set(ids)):
            errors.append(f"{path}: candidate_ids must be unique")
        if shard.get("file_count") != len(files):
            errors.append(f"{path}: file_count mismatch")
        if shard.get("candidate_count") != len(ids):
            errors.append(f"{path}: candidate_count mismatch")
        for file_name in files:
            if file_name not in known_files:
                errors.append(f"{path}: unknown file {file_name}")
            elif file_name in file_owner:
                errors.append(f"{path}: file {file_name} assigned more than once")
            else:
                file_owner[file_name] = reviewer
        for occurrence in ids:
            if occurrence not in candidate_map:
                errors.append(f"{path}: unknown candidate {occurrence}")
            elif occurrence in candidate_owner:
                errors.append(f"{path}: candidate {occurrence} assigned more than once")
            else:
                candidate_owner[occurrence] = reviewer
                candidate_file = candidate_map[occurrence]["path"]
                if candidate_file not in files:
                    errors.append(
                        f"{path}: candidate {occurrence} is separated from its file"
                    )
    missing_files = known_files - set(file_owner)
    if missing_files:
        errors.append(f"shards omit {len(missing_files)} corpus files")
    missing_candidates = set(candidate_map) - set(candidate_owner)
    if missing_candidates:
        errors.append(f"shards omit {len(missing_candidates)} candidates")
    try:
        expected_shards = balanced_shards(manifest, candidates)
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f"cannot reconstruct deterministic shard assignment: {error}")
    else:
        for expected in expected_shards:
            reviewer = expected["reviewer"]
            actual = loaded_by_reviewer.get(reviewer)
            if actual != expected:
                errors.append(
                    f"{reviewer}: shard does not match deterministic balanced assignment"
                )
        expected_loads = [row["candidate_count"] for row in expected_shards]
        if manifest.get("shard_candidate_loads") != expected_loads:
            errors.append("manifest shard_candidate_loads do not match canonical shards")
        if manifest.get("shard_candidate_load_spread") != (
            max(expected_loads) - min(expected_loads)
        ):
            errors.append("manifest shard_candidate_load_spread is not canonical")
    return file_owner, candidate_owner, errors


def validate_ledgers(
    manifest: dict[str, Any],
    candidates: Sequence[dict[str, Any]],
    ledger_inputs: Sequence[os.PathLike[str] | str],
    *,
    file_owner: dict[str, str] | None = None,
    candidate_owner: dict[str, str] | None = None,
) -> list[str]:
    paths = expand_json_paths(ledger_inputs, suffix=".jsonl")
    errors: list[str] = []
    records: list[tuple[Path, int, dict[str, Any]]] = []
    for path in paths:
        _, rows = read_jsonl(path)
        records.extend((path, index, row) for index, row in enumerate(rows, start=1))
    candidate_map = {row["occurrence_id"]: row for row in candidates}
    file_map = {row["path"]: row for row in manifest.get("files", [])}
    dispositions: dict[str, list[str]] = defaultdict(list)
    attestations: dict[str, list[str]] = defaultdict(list)
    for path, line_number, record in records:
        where = f"{path}:{line_number}"
        record_type = record.get("record_type")
        if record_type == "disposition":
            occurrence = record.get("occurrence_id")
            if not isinstance(occurrence, str) or occurrence not in candidate_map:
                errors.append(f"{where}: unknown occurrence_id {occurrence!r}")
                continue
            dispositions[occurrence].append(where)
            candidate = candidate_map[occurrence]
            reviewer = record.get("reviewer")
            if not isinstance(reviewer, str) or not reviewer.strip():
                errors.append(f"{where}: reviewer must be a non-empty string")
            elif candidate_owner is not None and reviewer != candidate_owner.get(occurrence):
                errors.append(f"{where}: reviewer does not own candidate {occurrence}")
            classification = record.get("classification")
            if classification not in CLASSIFICATIONS:
                errors.append(
                    f"{where}: classification must be one of "
                    f"{', '.join(sorted(CLASSIFICATIONS))}"
                )
            chain = record.get("denominator_chain")
            if (
                not isinstance(chain, list)
                or not chain
                or not all(isinstance(item, str) and item.strip() for item in chain)
            ):
                errors.append(
                    f"{where}: denominator_chain must be a non-empty string list"
                )
            if record.get("evidence_label") not in EVIDENCE_LABELS:
                errors.append(
                    f"{where}: evidence_label must be one of "
                    f"{', '.join(sorted(EVIDENCE_LABELS))}"
                )
            consequence = record.get("consequence")
            if not isinstance(consequence, str) or not consequence.strip():
                errors.append(f"{where}: consequence must be a non-empty string")
            if record.get("source_line") != candidate["line"]:
                errors.append(
                    f"{where}: source_line must equal candidate line {candidate['line']}"
                )
            if record.get("resolution_status") not in RESOLUTION_STATUSES:
                errors.append(
                    f"{where}: resolution_status must be one of "
                    f"{', '.join(sorted(RESOLUTION_STATUSES))}"
                )
        elif record_type == "file_attestation":
            file_name = record.get("file")
            if not isinstance(file_name, str) or file_name not in file_map:
                errors.append(f"{where}: unknown attested file {file_name!r}")
                continue
            attestations[file_name].append(where)
            reviewer = record.get("reviewer")
            if not isinstance(reviewer, str) or not reviewer.strip():
                errors.append(f"{where}: reviewer must be a non-empty string")
            elif file_owner is not None and reviewer != file_owner.get(file_name):
                errors.append(f"{where}: reviewer does not own file {file_name}")
            if record.get("complete") is not True:
                errors.append(f"{where}: complete must be JSON true")
            if record.get("sha256") != file_map[file_name]["sha256"]:
                errors.append(f"{where}: attested sha256 does not match manifest")
        else:
            errors.append(f"{where}: unknown record_type {record_type!r}")
    for occurrence in candidate_map:
        count = len(dispositions.get(occurrence, []))
        if count != 1:
            errors.append(
                f"{occurrence}: expected exactly one disposition, found {count}"
            )
    for file_name in file_map:
        count = len(attestations.get(file_name, []))
        if count != 1:
            errors.append(
                f"{file_name}: expected exactly one complete-file attestation, found {count}"
            )
    return errors


def validate_live_artifacts(
    repo_root: os.PathLike[str] | str,
    manifest: dict[str, Any],
    candidates: Sequence[dict[str, Any]] | None = None,
) -> list[str]:
    """Reject an artifact set that no longer describes the live corpus."""

    reject_forbidden_path(repo_root)
    live_manifest, live_candidates, _ = build_artifacts(repo_root)
    errors: list[str] = []
    if manifest != live_manifest:
        errors.append(
            "manifest is stale: it does not exactly match a fresh live-corpus scan"
        )
    if candidates is not None and list(candidates) != live_candidates:
        errors.append(
            "candidates JSONL is stale: it does not exactly match a fresh live-corpus scan"
        )
    return errors


def _strip_block_quotes(line: str) -> tuple[int, str]:
    """Return the Markdown block-quote depth and its remaining content."""

    depth = 0
    remainder = line
    while True:
        marker = re.match(r"^ {0,3}>[ \t]?", remainder)
        if marker is None:
            return depth, remainder
        depth += 1
        remainder = remainder[marker.end() :]


def _strip_list_marker(line: str) -> str | None:
    marker = re.match(r"^ {0,3}(?:[-+*]|\d{1,9}[.)])[ \t]+(.*)$", line)
    return None if marker is None else marker.group(1)


def _is_atx_heading(line: str) -> bool:
    return re.fullmatch(r" {0,3}#{1,6}(?:[ \t]+.*)?", line) is not None


def _is_setext_underline(line: str) -> bool:
    return re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", line) is not None


def _is_thematic_break(line: str) -> bool:
    return (
        re.fullmatch(
            r" {0,3}(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})",
            line,
        )
        is not None
    )


def _fence_opening(line: str) -> tuple[str, int] | None:
    candidate = _strip_list_marker(line)
    if candidate is None:
        candidate = line
    match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", candidate)
    if match is None:
        return None
    marker = match.group(1)
    if marker[0] == "`" and "`" in match.group(2):
        return None
    return marker[0], len(marker)


def _is_fence_closing(line: str, marker: str, minimum_length: int) -> bool:
    return (
        re.fullmatch(
            rf" {{0,3}}{re.escape(marker)}{{{minimum_length},}}[ \t]*",
            line,
        )
        is not None
    )


def _split_table_row(line: str) -> list[str] | None:
    """Split pipes outside escapes and code spans, or return None."""

    stripped = line.strip()
    if not stripped:
        return None
    cells: list[str] = []
    cell: list[str] = []
    pipe_count = 0
    code_ticks = 0
    index = 0
    while index < len(stripped):
        character = stripped[index]
        if character == "\\" and index + 1 < len(stripped):
            cell.append(character)
            cell.append(stripped[index + 1])
            index += 2
            continue
        if character == "`":
            end = index
            while end < len(stripped) and stripped[end] == "`":
                end += 1
            run_length = end - index
            if code_ticks == 0:
                code_ticks = run_length
            elif code_ticks == run_length:
                code_ticks = 0
            cell.extend(stripped[index:end])
            index = end
            continue
        if character == "|" and code_ticks == 0:
            cells.append("".join(cell))
            cell = []
            pipe_count += 1
        else:
            cell.append(character)
        index += 1
    cells.append("".join(cell))
    if pipe_count == 0:
        return None
    if stripped.startswith("|"):
        cells = cells[1:]
    if stripped.endswith("|") and cells:
        cells = cells[:-1]
    return cells


def _is_table_delimiter(cells: list[str] | None) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.strip()) is not None for cell in cells
    )


def _evidence_marker(line: str) -> str | None:
    marker = re.match(r"^\*\*([^*]*):\*\*", line)
    return None if marker is None else marker.group(1)


def _validate_claim_start(
    content: str,
    line_number: int,
    block_name: str,
    errors: list[str],
    *,
    additional_content: bool = False,
) -> bool:
    for label in REPORT_EVIDENCE_LABELS:
        prefix = f"**{label}:**"
        if content.startswith(prefix):
            if not content[len(prefix) :].strip() and not additional_content:
                errors.append(
                    f"report line {line_number}: {block_name} has an empty "
                    f"{label} claim"
                )
            return True
    marker = _evidence_marker(content)
    if marker is not None:
        if not marker.strip():
            errors.append(
                f"report line {line_number}: {block_name} has an empty "
                "evidence label"
            )
        else:
            errors.append(
                f"report line {line_number}: unknown evidence label {marker!r}"
            )
        return False
    errors.append(
        f"report line {line_number}: {block_name} must begin exactly "
        "'**VERIFIED BY RUNNING:**' or '**INFERRED BY READING:**'"
    )
    return False


def _validate_report_lead(
    lead: str,
    line_number: int,
    errors: list[str],
) -> None:
    em_dash = "\N{EM DASH}"
    flip = re.fullmatch(
        rf"VERDICTS FLIP: (-?\d+) {em_dash} (\S(?:.*\S)?)",
        lead,
    )
    if flip is not None:
        if int(flip.group(1)) < 0:
            errors.append(
                f"report line {line_number}: VERDICTS FLIP count must be "
                "non-negative"
            )
        return
    no_flip = re.fullmatch(
        r"NO VERDICT FLIPS: (-?\d+) unstated denominators found, "
        r"none load-bearing",
        lead,
    )
    if no_flip is not None:
        if int(no_flip.group(1)) < 0:
            errors.append(
                f"report line {line_number}: NO VERDICT FLIPS count must be "
                "non-negative"
            )
        return
    if re.fullmatch(r"AUDIT BLOCKED: \S(?:.*\S)?", lead) is not None:
        return
    errors.append(
        f"report line {line_number}: first non-empty line must be an exact "
        "VERDICTS FLIP (with U+2014 EM DASH), NO VERDICT FLIPS, or "
        "AUDIT BLOCKED lead"
    )


def validate_final_report(
    report_path: os.PathLike[str] | str,
    manifest: dict[str, Any],
) -> list[str]:
    path = checked_path(report_path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise AuditError(f"{path}: cannot read final report: {error}") from error
    lines = text.splitlines()
    errors: list[str] = []
    candidate_count = manifest.get("candidate_count")
    file_count = manifest.get("file_count")
    if (
        not isinstance(candidate_count, int)
        or isinstance(candidate_count, bool)
        or candidate_count < 0
        or not isinstance(file_count, int)
        or isinstance(file_count, bool)
        or file_count < 0
    ):
        errors.append(
            "report manifest needs non-negative integer candidate_count and file_count"
        )

    lead_index = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    if lead_index is None:
        errors.append("report has no non-empty lead line")
        return errors
    _validate_report_lead(lines[lead_index], lead_index + 1, errors)

    active_quote_depth: int | None = None
    fence: tuple[str, int, int] | None = None
    index = lead_index + 1
    while index < len(lines):
        line = lines[index]
        line_number = index + 1
        quote_depth, content = _strip_block_quotes(line)

        if fence is not None:
            marker, minimum_length, _ = fence
            if _is_fence_closing(content, marker, minimum_length):
                fence = None
                active_quote_depth = None
            index += 1
            continue

        opening = _fence_opening(content)
        if opening is not None:
            fence = opening[0], opening[1], line_number
            active_quote_depth = None
            index += 1
            continue

        if not line.strip() or (quote_depth > 0 and not content.strip()):
            active_quote_depth = None
            index += 1
            continue

        if _is_atx_heading(content) or _is_thematic_break(content):
            active_quote_depth = None
            index += 1
            continue

        if index + 1 < len(lines):
            next_depth, next_content = _strip_block_quotes(lines[index + 1])
            if (
                content.strip()
                and quote_depth == next_depth
                and _is_setext_underline(next_content)
            ):
                active_quote_depth = None
                index += 2
                continue

        header_cells = _split_table_row(content)
        if index + 1 < len(lines) and header_cells is not None:
            next_depth, next_content = _strip_block_quotes(lines[index + 1])
            delimiter_cells = _split_table_row(next_content)
            if (
                quote_depth == next_depth
                and len(header_cells) == len(delimiter_cells or [])
                and _is_table_delimiter(delimiter_cells)
            ):
                active_quote_depth = None
                index += 2
                while index < len(lines):
                    row_depth, row_content = _strip_block_quotes(lines[index])
                    row_cells = _split_table_row(row_content)
                    if (
                        row_depth != quote_depth
                        or row_cells is None
                    ):
                        break
                    first_cell = row_cells[0].strip() if row_cells else ""
                    has_other_content = any(
                        cell.strip() for cell in row_cells[1:]
                    )
                    _validate_claim_start(
                        first_cell,
                        index + 1,
                        "data table row",
                        errors,
                        additional_content=has_other_content,
                    )
                    index += 1
                continue

        list_content = _strip_list_marker(content)
        if list_content is not None:
            active_quote_depth = (
                quote_depth if list_content.strip() else None
            )
            if active_quote_depth is not None:
                if _is_atx_heading(list_content):
                    active_quote_depth = None
                else:
                    _validate_claim_start(
                        list_content,
                        line_number,
                        "bullet",
                        errors,
                    )
            index += 1
            continue

        is_continuation = (
            active_quote_depth == quote_depth
            or (
                active_quote_depth is not None
                and active_quote_depth > 0
                and quote_depth == 0
            )
        )
        if active_quote_depth is not None and is_continuation:
            marker = _evidence_marker(content)
            if marker is not None:
                if marker not in REPORT_EVIDENCE_LABELS:
                    if marker.strip():
                        errors.append(
                            f"report line {line_number}: unknown evidence "
                            f"label {marker!r}"
                        )
                    else:
                        errors.append(
                            f"report line {line_number}: empty evidence label"
                        )
                else:
                    errors.append(
                        f"report line {line_number}: claim label is hidden "
                        "inside a multiline paragraph; start a new paragraph"
                    )
            index += 1
            continue

        active_quote_depth = quote_depth
        _validate_claim_start(
            content,
            line_number,
            "blockquote paragraph" if quote_depth else "prose paragraph",
            errors,
        )
        index += 1

    if fence is not None:
        errors.append(
            f"report line {fence[2]}: fenced literal block is not closed"
        )
    return errors


def parser() -> argparse.ArgumentParser:
    lane = Path(__file__).parent
    default_root = lane.parent.parent
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="scan the corpus and write deterministic artifacts")
    scan.add_argument("--repo-root", default=str(default_root))
    scan.add_argument("--out", default=str(lane / "out"))

    ledgers = commands.add_parser(
        "validate-ledgers", help="validate manifest, shards, and review ledgers"
    )
    ledgers.add_argument("--manifest", required=True)
    ledgers.add_argument("--candidates", required=True)
    ledgers.add_argument("--shards", nargs="+", required=True)
    ledgers.add_argument("--ledgers", nargs="+", required=True)
    ledgers.add_argument("--repo-root", default=str(default_root))

    report = commands.add_parser(
        "validate-report", help="validate final-report leads and claim labels"
    )
    report.add_argument("--manifest", required=True)
    report.add_argument("--report", required=True)
    report.add_argument("--repo-root", default=str(default_root))

    check = commands.add_parser(
        "check", help="validate manifest, shards, ledgers, and final report"
    )
    check.add_argument("--manifest", required=True)
    check.add_argument("--candidates", required=True)
    check.add_argument("--shards", nargs="+", required=True)
    check.add_argument("--ledgers", nargs="+", required=True)
    check.add_argument("--report", required=True)
    check.add_argument("--repo-root", default=str(default_root))
    return root


def _print_errors(errors: Sequence[str]) -> None:
    for error in errors:
        print(f"RED: {error}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "scan":
            # Both user-controlled paths are rejected before any scan access.
            reject_forbidden_path(args.repo_root)
            reject_forbidden_path(args.out)
            manifest = scan_to_directory(args.repo_root, args.out)
            print(
                "GREEN: "
                f"files={manifest['file_count']} "
                f"lines={manifest['total_lines']} "
                f"bytes={manifest['total_bytes']} "
                f"candidates={manifest['candidate_count']} "
                f"corpus_sha256={manifest['corpus_sha256']}"
            )
            return 0

        reject_forbidden_path(args.manifest)
        reject_forbidden_path(args.repo_root)
        if args.command == "validate-report":
            reject_forbidden_path(args.report)
            manifest = read_json(args.manifest)
            errors = validate_final_report(args.report, manifest)
            errors.extend(validate_live_artifacts(args.repo_root, manifest))
            if errors:
                _print_errors(errors)
                return 1
            print("GREEN: final report format and claim labels validated")
            return 0

        reject_forbidden_path(args.candidates)
        for item in (*args.shards, *args.ledgers):
            reject_forbidden_path(item)
        if args.command == "check":
            reject_forbidden_path(args.report)
        manifest, candidates, errors = validate_manifest_and_candidates(
            args.manifest, args.candidates
        )
        errors.extend(validate_live_artifacts(args.repo_root, manifest, candidates))
        if not errors:
            file_owner, candidate_owner, shard_errors = load_and_validate_shards(
                args.shards, manifest, candidates
            )
            errors.extend(shard_errors)
            errors.extend(
                validate_ledgers(
                    manifest,
                    candidates,
                    args.ledgers,
                    file_owner=file_owner,
                    candidate_owner=candidate_owner,
                )
            )
        if args.command == "check":
            errors.extend(validate_final_report(args.report, manifest))
        if errors:
            _print_errors(errors)
            return 1
        print(
            "GREEN: "
            f"{len(candidates)} dispositions, {manifest['file_count']} "
            "complete-file attestations, 8 shard manifests"
        )
        return 0
    except AuditError as error:
        print(f"RED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
