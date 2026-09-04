"""Verified-byte launcher for the M164 production dominance reader."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA = "m164-dominance-verdict/v1"
FREEZE_SCHEMA = "m164-dominance-freeze/v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(encoded)
    os.replace(partial, path)


def _refusal(
    output: Path,
    *,
    code: str,
    pointer: str,
    detail: str,
    manifest_path: str | None = None,
    manifest_sha256: str | None = None,
    evidence_path: str | None = None,
    evidence_sha256: str | None = None,
) -> int:
    _write(
        output,
        {
            "schema": SCHEMA,
            "status": "UNMEASURED",
            "claim": "M164_REFERENCE_INFORMATION_DOMINANCE_GX",
            "manifest": {
                "path": manifest_path,
                "sha256": manifest_sha256,
                "verified_bytes_consumed": False,
            },
            "evidence": {
                "path": evidence_path,
                "sha256": evidence_sha256,
                "verified_bytes_consumed": False,
            },
            "reasons": [
                {"code": code, "pointer": pointer, "detail": detail}
            ],
            "family_result": None,
        },
    )
    return 2


def _strict_json(data: bytes) -> Any:
    def object_without_duplicates(
        pairs: list[tuple[str, Any]],
    ) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate object key {key!r}")
            value[key] = item
        return value

    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=object_without_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-standard constant {value}")
        ),
    )


def _inside(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    try:
        root = Path(args.repo_root).resolve(strict=True)
        freeze_path = _inside(root, Path(args.freeze))
        freeze_bytes = freeze_path.read_bytes()
    except (OSError, ValueError) as error:
        return _refusal(
            output,
            code="INPUT_UNRESOLVABLE",
            pointer="$freeze",
            detail=str(error),
        )

    try:
        freeze = _strict_json(freeze_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        return _refusal(
            output,
            code="FREEZE_RECORD_JSON",
            pointer="$freeze",
            detail=str(error),
        )
    required = {
        "schema",
        "manifest_path",
        "manifest_sha256",
        "checker_core_path",
        "checker_core_sha256",
        "launcher_path",
        "launcher_sha256",
    }
    if (
        not isinstance(freeze, dict)
        or set(freeze) != required
        or freeze.get("schema") != FREEZE_SCHEMA
        or any(
            not isinstance(freeze.get(key), str)
            for key in required
        )
    ):
        return _refusal(
            output,
            code="FREEZE_RECORD_SCHEMA",
            pointer="$freeze",
            detail="freeze record must contain exactly the v1 required fields",
        )

    try:
        manifest_resolved = _inside(root, Path(args.manifest))
        manifest_relative = str(manifest_resolved.relative_to(root))
    except (OSError, ValueError) as error:
        return _refusal(
            output,
            code="INPUT_UNRESOLVABLE",
            pointer="$manifest",
            detail=str(error),
        )
    if manifest_relative != freeze["manifest_path"]:
        return _refusal(
            output,
            code="MANIFEST_PATH_BINDING",
            pointer="$freeze.manifest_path",
            detail=(
                f"freeze binds {freeze['manifest_path']}, "
                f"reader received {manifest_relative}"
            ),
            manifest_path=manifest_relative,
        )

    try:
        launcher_bytes = Path(__file__).resolve(strict=True).read_bytes()
    except OSError as error:
        return _refusal(
            output,
            code="INPUT_UNRESOLVABLE",
            pointer="$launcher",
            detail=str(error),
            manifest_path=manifest_relative,
        )
    launcher_sha = _sha256(launcher_bytes)
    if launcher_sha != freeze["launcher_sha256"]:
        return _refusal(
            output,
            code="LAUNCHER_SHA256",
            pointer="$freeze.launcher_sha256",
            detail=(
                f"expected {freeze['launcher_sha256']}, consumed "
                f"{launcher_sha}"
            ),
            manifest_path=manifest_relative,
        )

    try:
        core_path = _inside(root, root / freeze["checker_core_path"])
        core_bytes = core_path.read_bytes()
    except (OSError, ValueError) as error:
        return _refusal(
            output,
            code="CHECKER_CORE_UNRESOLVABLE",
            pointer="$freeze.checker_core_path",
            detail=str(error),
            manifest_path=manifest_relative,
        )
    core_sha = _sha256(core_bytes)
    if core_sha != freeze["checker_core_sha256"]:
        return _refusal(
            output,
            code="CHECKER_CORE_SHA256",
            pointer="$freeze.checker_core_sha256",
            detail=(
                f"expected {freeze['checker_core_sha256']}, consumed "
                f"{core_sha}"
            ),
            manifest_path=manifest_relative,
        )

    try:
        manifest_bytes = manifest_resolved.read_bytes()
    except OSError as error:
        return _refusal(
            output,
            code="INPUT_UNRESOLVABLE",
            pointer="$manifest",
            detail=str(error),
            manifest_path=manifest_relative,
        )
    manifest_sha = _sha256(manifest_bytes)
    if manifest_sha != freeze["manifest_sha256"]:
        return _refusal(
            output,
            code="MANIFEST_SHA256",
            pointer="$freeze.manifest_sha256",
            detail=(
                f"expected {freeze['manifest_sha256']}, consumed "
                f"{manifest_sha}"
            ),
            manifest_path=manifest_relative,
            manifest_sha256=manifest_sha,
        )

    evidence_bytes: bytes | None = None
    evidence_relative: str | None = None
    if args.evidence:
        try:
            evidence_resolved = _inside(root, Path(args.evidence))
            evidence_relative = str(evidence_resolved.relative_to(root))
            evidence_bytes = evidence_resolved.read_bytes()
        except (OSError, ValueError) as error:
            return _refusal(
                output,
                code="EVIDENCE_UNRESOLVABLE",
                pointer="$evidence",
                detail=str(error),
                manifest_path=manifest_relative,
                manifest_sha256=manifest_sha,
            )

    namespace: dict[str, Any] = {
        "__name__": "m164_verified_reader_core",
        "__file__": "<verified-reader-core-bytes>",
    }
    try:
        exec(
            compile(core_bytes, "<verified-reader-core-bytes>", "exec"),
            namespace,
        )
        result = namespace["run"](
            repository_root=str(root),
            manifest_path=manifest_relative,
            manifest_bytes=manifest_bytes,
            manifest_sha256=manifest_sha,
            evidence_path=evidence_relative,
            evidence_bytes=evidence_bytes,
            runtime_hashes={
                "reader-core": core_sha,
                "reader-launcher": launcher_sha,
            },
        )
    except Exception as error:
        return _refusal(
            output,
            code="DOMINANCE_FAMILY",
            pointer="$checker",
            detail=f"verified checker refused: {type(error).__name__}: {error}",
            manifest_path=manifest_relative,
            manifest_sha256=manifest_sha,
            evidence_path=evidence_relative,
            evidence_sha256=(
                _sha256(evidence_bytes)
                if evidence_bytes is not None
                else None
            ),
        )

    _write(output, result)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
