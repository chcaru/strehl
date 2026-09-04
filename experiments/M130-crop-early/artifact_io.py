"""Deterministic JSON and input-provenance helpers for M130."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable


SELF_HASH_RULE = (
    "SHA-256 of UTF-8 JSON with sorted keys, compact separators, "
    "ensure_ascii=false, allow_nan=false, after removing integrity.self_sha256"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def file_record(path: Path) -> dict[str, Any]:
    path = path.resolve()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def frame_manifest(
    directory: Path,
    *,
    capture_identifier: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """Hash a deterministic ARW prefix without writing to the capture."""

    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError(f"capture directory does not exist: {directory}")
    paths = sorted(
        (path for path in directory.iterdir() if path.suffix.lower() == ".arw"),
        key=lambda path: path.name.lower(),
    )
    if limit is not None:
        if limit < 1:
            raise ValueError("capture manifest limit must be positive")
        if len(paths) < limit:
            raise ValueError(
                f"{directory}: requested {limit} frames but found {len(paths)}"
            )
        paths = paths[:limit]
    if not paths:
        raise ValueError(f"capture directory has no ARW frames: {directory}")
    frames = [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]
    manifest_payload = {
        "capture_identifier": capture_identifier,
        "frames": frames,
    }
    return {
        "capture_identifier": capture_identifier,
        "path": str(directory),
        "frame_count": len(frames),
        "total_bytes": sum(int(frame["bytes"]) for frame in frames),
        "first_frame": frames[0]["name"],
        "last_frame": frames[-1]["name"],
        "manifest_definition": (
            "SHA-256 of canonical JSON containing capture_identifier and the "
            "ordered name/bytes/content-sha256 frame records"
        ),
        "manifest_sha256": canonical_sha256(manifest_payload),
        "frames": frames,
    }


def path_state(directory: Path) -> list[dict[str, int | str]]:
    """Cheap before/after mutation canary for a read-only capture directory."""

    return [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        for path in sorted(directory.resolve().iterdir(), key=lambda item: item.name.lower())
    ]


def canonical_sha256(document: Any) -> str:
    encoded = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def self_hash(document: dict[str, Any]) -> str:
    payload = copy.deepcopy(document)
    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        integrity.pop("self_sha256", None)
    return canonical_sha256(payload)


def seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(document)
    integrity = sealed.setdefault("integrity", {})
    integrity["algorithm"] = "SHA-256"
    integrity["self_hash_rule"] = SELF_HASH_RULE
    integrity.pop("self_sha256", None)
    integrity["self_sha256"] = self_hash(sealed)
    return sealed


def write_artifact(path: Path, document: dict[str, Any]) -> dict[str, Any]:
    """Seal and atomically write one stable, pretty-printed JSON document."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    sealed = seal(document)
    text = json.dumps(
        sealed,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return sealed


def read_verified_artifact(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path}: artifact root must be a JSON object")
    integrity = document.get("integrity")
    if not isinstance(integrity, dict):
        raise ValueError(f"{path}: missing integrity object")
    expected = integrity.get("self_sha256")
    actual = self_hash(document)
    if expected != actual:
        raise ValueError(
            f"{path}: self SHA-256 mismatch: recorded {expected!r}, computed {actual}"
        )
    return document


def require_keys(mapping: dict[str, Any], keys: Iterable[str], *, where: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(f"{where}: missing required keys: {', '.join(missing)}")
