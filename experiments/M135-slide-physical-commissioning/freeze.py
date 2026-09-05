#!/usr/bin/env python3
"""Write or check the dependency/source freeze for the M135 slide instrument."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import instrument as M


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_MANIFEST = HERE / "freeze-manifest.json"
SOURCE_NAMES = (
    ".gitattributes",
    "PREREGISTRATION.md",
    "README.md",
    "AMENDMENT-1.md",
    "AMENDMENT-2.md",
    "AMENDMENT-3.md",
    "AMENDMENT-4.md",
    "AMENDMENT-5.md",
    "AMENDMENT-6.md",
    "AMENDMENT-7.md",
    "AMENDMENT-8.md",
    "AMENDMENT-9.md",
    "AMENDMENT-10.md",
    "AMENDMENT-11.md",
    "AMENDMENT-12.md",
    "AMENDMENT-13.md",
    "AMENDMENT-14.md",
    "AMENDMENT-15.md",
    "Cargo.toml",
    "Cargo.lock",
    "config.json",
    "artifact-schemas.json",
    "role-ledger.template.json",
    "instrument.py",
    "commission.py",
    "freeze.py",
    r"src\main.rs",
)
COMMISSION_NAMES = (
    "commission-run1-failed.json",
    "commission-run2-failed.json",
    "commission-run3-failed.json",
    "commission-run4-nondeterministic-before.json",
    "commission-run4-nondeterministic-after.json",
    "commission-run5-nondeterministic-before.json",
    "commission-run5-nondeterministic-after.json",
    "commission.json",
)


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "--no-pager", *arguments],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if completed.returncode != 0:
        raise M.InstrumentError(
            f"git {' '.join(arguments)} failed: {completed.stderr}"
        )
    return completed.stdout.strip()


def source_record(path: Path) -> dict[str, Any]:
    relative = str(path.relative_to(REPO)).replace("/", "\\")
    if path.name == ".gitattributes" or path.suffix.lower() in {
        ".py",
        ".md",
        ".json",
        ".toml",
        ".lock",
        ".rs",
    }:
        normalized = path.read_text(encoding="utf-8").encode("utf-8")
        digest = M.sha256_bytes(normalized)
        return {
            "path": relative,
            "bytes": len(normalized),
            "sha256": digest,
            "normalized_text_sha256": digest,
            "hash_domain": "UTF-8 text after universal-newline normalization",
        }
    return {
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": M.sha256_file(path),
        "hash_domain": "file bytes",
    }


def exiftool_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise M.InstrumentError(f"missing ExifTool binary: {path}")
    completed = subprocess.run(
        [str(path), "-ver"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if completed.returncode != 0:
        raise M.InstrumentError(
            f"ExifTool -ver failed with {completed.returncode}: "
            f"{completed.stderr}"
        )
    return {
        "path": str(path.absolute()),
        "bytes": path.stat().st_size,
        "sha256": M.sha256_file(path),
        "version": completed.stdout.strip(),
        "version_command": [str(path.absolute()), "-ver"],
    }


def rawpy_libraw_version() -> str | None:
    import rawpy

    value = getattr(rawpy, "libraw_version", None)
    if value is None:
        return None
    if isinstance(value, tuple):
        return ".".join(str(part) for part in value)
    return str(value)


def documented_commands() -> dict[str, Any]:
    lane = r"experiments\M135-slide-physical-commissioning"
    return {
        "prior_art": (
            r"python experiments\ORCH-drift-check\prior_art.py "
            r"burned slide physical commissioning detail instrument"
        ),
        "commission": (
            rf"python -B {lane}\commission.py --config {lane}\config.json "
            rf"--output {lane}\commission.json"
        ),
        "freeze_check": (
            rf"python -B {lane}\freeze.py check "
            rf"--manifest {lane}\freeze-manifest.json"
        ),
        "crosscheck_build": (
            r"cargo build --release --locked --manifest-path "
            r"experiments\M135-slide-physical-commissioning\Cargo.toml"
        ),
        "environment": {
            **M.load_config(HERE / "config.json")["environment"]["required"],
            "STREHL_ALIGN": None,
            "STREHL_WARPMAP": None,
            "STREHL_FIX_HALO": None,
            "STREHL_COVER": None,
            "STREHL_RESAMPLER": None,
            "RAYON_NUM_THREADS": None,
        },
        "data_commands": [
            "instrument.py --config config.json inventory --session-root <AUTHORIZED_SESSION_ROOT> --exiftool <EXIFTOOL> --output stage-a-inventory.json",
            "instrument.py --config config.json decode --inventory stage-a-inventory.json --rawler-crosscheck-bin <M135_CROSSCHECK_BINARY> --output stage-b-decode.json",
            "instrument.py --config config.json range --inventory stage-a-inventory.json --decode stage-b-decode.json --output stage-c-range.json",
            "instrument.py --config config.json roles --inventory stage-a-inventory.json --ledger role-ledger.template.json --output stage-d-roles.json",
            "instrument.py --config config.json flat --inventory stage-a-inventory.json --decode stage-b-decode.json --roles stage-d-roles.json --ledger role-ledger.template.json --output stage-e-flat.json",
            "instrument.py --config config.json summarize --inventory stage-a-inventory.json --decode stage-b-decode.json --range stage-c-range.json --roles stage-d-roles.json --flat stage-e-flat.json --output summary.json",
        ],
    }


def collect_manifest(
    exiftool: Path,
    *,
    source_tree_parent_commit: str | None = None,
) -> dict[str, Any]:
    config = M.load_config(HERE / "config.json")
    commissioning = {
        name: source_record(HERE / name) for name in COMMISSION_NAMES
    }
    final_commission = json.loads(
        (HERE / "commission.json").read_text(encoding="utf-8")
    )
    if final_commission.get("status") != "COMMISSIONED":
        raise M.InstrumentError("final commission.json is not COMMISSIONED")
    source_parent = source_tree_parent_commit or git_output("rev-parse", "HEAD")
    prereg_path = HERE / "PREREGISTRATION.md"
    existing = M.EXISTING_INSTRUMENT
    dependency = M.dependency_record()
    dependency["rawpy_libraw_version"] = rawpy_libraw_version()
    manifest = {
        "schema": "m135-slide-freeze-v1",
        "label": M.LABEL,
        "status": "FROZEN",
        "source_tree_parent_commit": source_parent,
        "commit_identity_rule": (
            "the claiming commit is the commit containing this manifest; "
            "embedding its SHA would be circular"
        ),
        "preregistration": {
            **source_record(prereg_path),
            "git_commit": git_output(
                "log",
                "-1",
                "--format=%H",
                "--",
                str(prereg_path.relative_to(REPO)).replace("\\", "/"),
            ),
            "must_remain_unmodified": True,
        },
        "existing_estimator": {
            **source_record(existing),
            "git_commit": git_output(
                "log",
                "-1",
                "--format=%H",
                "--",
                str(existing.relative_to(REPO)).replace("\\", "/"),
            ),
            "normalized_hash_expected_by_comparison_contract": (
                "b2243292d92b8edc386b11b68e01740d0365bc4d633d728771d421be0732bbf1"
            ),
        },
        "source_files": [
            source_record(HERE / name) for name in SOURCE_NAMES
        ],
        "commissioning_artifacts": commissioning,
        "dependencies": {
            **dependency,
            "exiftool": exiftool_record(exiftool),
        },
        "external_decoder_path": {
            "decision": (
                "use a lane-local executable over the existing safe "
                "strehl-raw/rawler API; no GPL/LGPL source was read"
            ),
            "cargo_manifest": source_record(M.CROSSCHECK_MANIFEST),
            "cargo_lock": source_record(M.CROSSCHECK_LOCK),
            "rust_source": source_record(M.CROSSCHECK_SOURCE),
            "build_command": documented_commands()["crosscheck_build"],
            "runtime_contract": (
                "all rawpy visible pixels in every frame must equal the "
                "leading overlap of rawler's active area bit for bit"
            ),
        },
        "documented_commands": documented_commands(),
        "config_sha256": M.config_sha256(HERE / "config.json"),
        "artifact_schemas_sha256": M.normalized_text_sha256(
            HERE / "artifact-schemas.json"
        ),
    }
    if (
        manifest["existing_estimator"]["normalized_text_sha256"]
        != manifest["existing_estimator"][
            "normalized_hash_expected_by_comparison_contract"
        ]
    ):
        raise M.InstrumentError("existing estimator normalized hash drift")
    M.validate_artifact(manifest)
    return manifest


def check_manifest(path: Path) -> dict[str, Any]:
    frozen = M.load_json_object(path)
    M.validate_artifact(frozen)
    exiftool = Path(frozen["dependencies"]["exiftool"]["path"])
    current = collect_manifest(
        exiftool,
        source_tree_parent_commit=frozen["source_tree_parent_commit"],
    )
    if current != frozen:
        keys = sorted(
            key for key in set(current) | set(frozen) if current.get(key) != frozen.get(key)
        )
        raise M.InstrumentError(
            "freeze drift in top-level fields: " + ", ".join(keys)
        )
    return {
        "schema": "m135-slide-freeze-check-v1",
        "status": "PASS",
        "manifest": str(path.absolute()),
        "manifest_sha256": M.sha256_file(path),
        "source_file_count": len(frozen["source_files"]),
        "commissioning_artifact_count": len(
            frozen["commissioning_artifacts"]
        ),
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write")
    write.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    write.add_argument("--exiftool", type=Path, required=True)
    check = commands.add_parser("check")
    check.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "write":
            payload = collect_manifest(args.exiftool.absolute())
            M.write_json(args.manifest.absolute(), payload)
            output = {
                "status": "FROZEN",
                "manifest": str(args.manifest.absolute()),
                "manifest_sha256": M.sha256_file(args.manifest.absolute()),
            }
        else:
            output = check_manifest(args.manifest.absolute())
        print(json.dumps(output, sort_keys=True))
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "argv": [str(Path(sys.executable).absolute()), *sys.argv],
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
