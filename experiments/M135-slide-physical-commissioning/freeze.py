#!/usr/bin/env python3
"""Write or check the dependency/source freeze for the M135 slide instrument."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import instrument as M


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_MANIFEST = HERE / "freeze-manifest.json"
DEFAULT_CROSSCHECK_BINARY = (
    HERE
    / "target"
    / "release"
    / (
        "m135-slide-raw-crosscheck.exe"
        if sys.platform == "win32"
        else "m135-slide-raw-crosscheck"
    )
)
SOURCE_NAMES = (
    ".gitattributes",
    "PREREGISTRATION.md",
    "README.md",
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
AMENDMENT_RE = re.compile(r"^AMENDMENT-(\d+)\.md$")
COMMISSION_NAMES = (
    "commission-run1-failed.json",
    "commission-run2-failed.json",
    "commission-run3-failed.json",
    "commission-run4-nondeterministic-before.json",
    "commission-run4-nondeterministic-after.json",
    "commission-run5-nondeterministic-before.json",
    "commission-run5-nondeterministic-after.json",
    "commission-run6-failed.json",
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


def lane_source_paths() -> list[Path]:
    amendments = []
    for path in HERE.glob("AMENDMENT-*.md"):
        match = AMENDMENT_RE.fullmatch(path.name)
        if match is not None:
            amendments.append((int(match.group(1)), path))
    amendments.sort()
    observed = [number for number, _ in amendments]
    expected = list(range(1, len(amendments) + 1))
    if observed != expected:
        raise M.InstrumentError(
            f"amendment sequence is not contiguous: {observed}"
        )
    return [HERE / name for name in SOURCE_NAMES] + [
        path for _, path in amendments
    ]


def _run_text(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if completed.returncode != 0:
        raise M.InstrumentError(
            f"{subprocess.list2cmdline(command)} failed with "
            f"{completed.returncode}: {completed.stderr}"
        )
    return completed.stdout


def _tool_record(name: str, arguments: list[str]) -> dict[str, Any]:
    raw_path = shutil.which(name)
    if raw_path is None:
        raise M.InstrumentError(f"required tool is absent from PATH: {name}")
    path = Path(raw_path).absolute()
    command = [name, *arguments]
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": M.sha256_file(path),
        "version_command": command,
        "version_output": _run_text(command, REPO).strip(),
    }


def _cargo_environment() -> dict[str, Any]:
    names = (
        "CARGO_HOME",
        "CARGO_TARGET_DIR",
        "CARGO_BUILD_TARGET",
        "CARGO_BUILD_RUSTC",
        "CARGO_BUILD_RUSTFLAGS",
        "CARGO_ENCODED_RUSTFLAGS",
        "CARGO_INCREMENTAL",
        "RUSTC",
        "RUSTC_WRAPPER",
        "RUSTC_WORKSPACE_WRAPPER",
        "RUSTFLAGS",
        "RUSTUP_TOOLCHAIN",
    )
    return {name: os.environ.get(name) for name in names}


def _cargo_home_config() -> dict[str, Any] | None:
    cargo_home = Path(
        os.environ.get("CARGO_HOME", str(Path.home() / ".cargo"))
    ).absolute()
    paths = [
        path
        for path in (cargo_home / "config", cargo_home / "config.toml")
        if path.is_file()
    ]
    if not paths:
        return None
    return M.semantic_file_closure(paths)


def _package_build_files(package_root: Path) -> list[Path]:
    selected = []
    for path in package_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(package_root)
        if any(
            part.casefold() in {"target", ".git", "__pycache__"}
            for part in relative.parts
        ):
            continue
        if (
            path.name in {"Cargo.toml", "build.rs"}
            or path.suffix.casefold() == ".rs"
            or (relative.parts and relative.parts[0].casefold() == "src")
        ):
            selected.append(path)
    return selected


def _repository_cargo_context_files() -> list[Path]:
    candidates = [
        REPO / "Cargo.toml",
        REPO / "Cargo.lock",
        REPO / "rust-toolchain",
        REPO / "rust-toolchain.toml",
        REPO / ".cargo" / "config",
        REPO / ".cargo" / "config.toml",
        HERE / "Cargo.lock",
    ]
    return [path for path in candidates if path.is_file()]


def cargo_dependency_closure() -> dict[str, Any]:
    relative_manifest = str(M.CROSSCHECK_MANIFEST.relative_to(REPO)).replace(
        "/", "\\"
    )
    command = [
        "cargo",
        "metadata",
        "--locked",
        "--format-version",
        "1",
        "--manifest-path",
        relative_manifest,
    ]
    raw = _run_text(command, REPO)
    try:
        metadata = json.loads(raw)
    except json.JSONDecodeError as error:
        raise M.InstrumentError(f"cargo metadata returned invalid JSON: {error}")
    local_packages = []
    closure_paths = set(_repository_cargo_context_files())
    for package in metadata.get("packages", []):
        manifest = Path(package["manifest_path"]).absolute()
        if package.get("source") is not None or not M.path_is_within(
            manifest, REPO
        ):
            continue
        package_root = manifest.parent
        files = _package_build_files(package_root)
        closure_paths.update(files)
        local_packages.append(
            {
                "name": package["name"],
                "version": package["version"],
                "manifest_path": str(manifest.relative_to(REPO)).replace(
                    "/", "\\"
                ),
                "targets": [
                    {
                        "name": target["name"],
                        "kind": target["kind"],
                        "src_path": str(
                            Path(target["src_path"])
                            .absolute()
                            .relative_to(REPO)
                        ).replace("/", "\\"),
                    }
                    for target in package.get("targets", [])
                ],
                "selected_file_count": len(files),
            }
        )
    if {row["name"] for row in local_packages} != {
        "m135-slide-raw-crosscheck",
        "strehl-core",
        "strehl-raw",
    }:
        raise M.InstrumentError(
            "unexpected local Cargo dependency closure: "
            + ", ".join(sorted(row["name"] for row in local_packages))
        )
    file_records = [
        source_record(path)
        for path in sorted(
            closure_paths,
            key=lambda item: str(item.relative_to(REPO)).casefold(),
        )
    ]
    resolved_packages = sorted(
        (
            {
                "name": package["name"],
                "version": package["version"],
                "source": package.get("source"),
                "checksum": package.get("checksum"),
            }
            for package in metadata.get("packages", [])
        ),
        key=lambda row: (
            row["name"],
            row["version"],
            str(row["source"]),
        ),
    )
    workspace_root = Path(metadata["workspace_root"]).absolute()
    rustc = _tool_record("rustc", ["--version", "--verbose"])
    rustc["sysroot_command"] = ["rustc", "--print", "sysroot"]
    rustc["sysroot"] = _run_text(
        rustc["sysroot_command"], REPO
    ).strip()
    return {
        "metadata_command": command,
        "metadata_command_line_windows": subprocess.list2cmdline(command),
        "metadata_cwd": "<REPOSITORY_ROOT>",
        "metadata_environment": _cargo_environment(),
        "workspace_root": str(workspace_root.relative_to(REPO)).replace(
            "/", "\\"
        ),
        "local_packages": sorted(
            local_packages, key=lambda row: row["name"]
        ),
        "resolved_packages": resolved_packages,
        "files": file_records,
        "file_count": len(file_records),
        "byte_count": sum(record["bytes"] for record in file_records),
        "aggregate_sha256": M.canonical_json_sha256(file_records),
        "aggregate_domain": (
            "canonical JSON over every selected local Cargo closure file "
            "record, including root/lane locks and workspace/toolchain config"
        ),
        "cargo": _tool_record("cargo", ["--version", "--verbose"]),
        "rustc": rustc,
        "cargo_home_config": _cargo_home_config(),
        "selection_rule": (
            "cargo metadata local packages plus every Cargo.toml/build.rs, "
            "every Rust source, every file below src, root Cargo.toml/"
            "Cargo.lock, lane Cargo.lock, rust-toolchain, and repository "
            ".cargo config when present"
        ),
    }


def crosscheck_executable_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise M.InstrumentError(f"missing crosscheck executable: {path}")
    return {
        "file_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": M.sha256_file(path),
        "hash_domain": "exact executable file bytes",
        "default_check_path": str(
            DEFAULT_CROSSCHECK_BINARY.relative_to(HERE)
        ).replace("/", "\\"),
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


def documented_commands() -> dict[str, Any]:
    lane = r"experiments\M135-slide-physical-commissioning"
    return {
        "prior_art": (
            r"python experiments\ORCH-drift-check\prior_art.py "
            r"burned slide physical commissioning detail instrument"
        ),
        "commission": (
            rf"python -B {lane}\commission.py --config {lane}\config.json "
            rf"--output {lane}\commission.json --freeze-manifest "
            rf"{lane}\freeze-manifest.json --crosscheck-bin "
            rf"{lane}\target\release\m135-slide-raw-crosscheck.exe"
        ),
        "freeze_create": (
            rf"python -B {lane}\freeze.py create --manifest "
            rf"{lane}\freeze-manifest.json --exiftool <EXIFTOOL> "
            rf"--crosscheck-bin "
            rf"{lane}\target\release\m135-slide-raw-crosscheck.exe"
        ),
        "freeze_check": (
            rf"python -B {lane}\freeze.py check "
            rf"--manifest {lane}\freeze-manifest.json --crosscheck-bin "
            rf"<M135_CROSSCHECK_BINARY>"
        ),
        "crosscheck_build": (
            r"cargo build --release --locked --manifest-path "
            r"experiments\M135-slide-physical-commissioning\Cargo.toml"
        ),
        "crosscheck_build_defaults": {
            "profile": "release",
            "target": "host default",
            "features": "default",
            "all_features": False,
            "no_default_features": False,
            "jobs": "Cargo default",
            "target_dir": (
                r"experiments\M135-slide-physical-commissioning\target"
            ),
        },
        "cargo_environment": _cargo_environment(),
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
            "instrument.py --config config.json decode --inventory stage-a-inventory.json --rawler-crosscheck-bin <M135_CROSSCHECK_BINARY> --freeze-manifest freeze-manifest.json --output stage-b-decode.json",
            "instrument.py --config config.json range --inventory stage-a-inventory.json --decode stage-b-decode.json --output stage-c-range.json",
            "instrument.py --config config.json roles --inventory stage-a-inventory.json --ledger role-ledger.template.json --output stage-d-roles.json",
            "instrument.py --config config.json flat --inventory stage-a-inventory.json --decode stage-b-decode.json --roles stage-d-roles.json --ledger role-ledger.template.json --output stage-e-flat.json",
            "instrument.py --config config.json summarize --inventory stage-a-inventory.json --decode stage-b-decode.json --range stage-c-range.json --roles stage-d-roles.json --flat stage-e-flat.json --output summary.json",
        ],
    }


def collect_manifest(
    exiftool: Path,
    crosscheck_binary: Path,
    *,
    source_tree_parent_commit: str | None = None,
    git_commit_overrides: dict[str, str] | None = None,
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
    commit_overrides = git_commit_overrides or {}
    prereg_commit = commit_overrides.get("preregistration") or git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        str(prereg_path.relative_to(REPO)).replace("\\", "/"),
    )
    existing_commit = commit_overrides.get("existing_estimator") or git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        str(existing.relative_to(REPO)).replace("\\", "/"),
    )
    cargo_closure = cargo_dependency_closure()
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
            "git_commit": prereg_commit,
            "must_remain_unmodified": True,
        },
        "existing_estimator": {
            **source_record(existing),
            "git_commit": existing_commit,
            "normalized_hash_expected_by_comparison_contract": (
                "b2243292d92b8edc386b11b68e01740d0365bc4d633d728771d421be0732bbf1"
            ),
        },
        "source_files": [source_record(path) for path in lane_source_paths()],
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
            "build_defaults": documented_commands()[
                "crosscheck_build_defaults"
            ],
            "build_environment": _cargo_environment(),
            "cargo_dependency_closure": cargo_closure,
            "executable": crosscheck_executable_record(crosscheck_binary),
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


def check_manifest(
    path: Path, crosscheck_binary: Path | None = None
) -> dict[str, Any]:
    frozen = M.load_json_object(path)
    M.validate_artifact(frozen)
    executable = frozen.get("external_decoder_path", {}).get("executable", {})
    if crosscheck_binary is None:
        relative = executable.get("default_check_path")
        if not isinstance(relative, str) or not relative:
            raise M.InstrumentError(
                "freeze manifest lacks the default crosscheck path"
            )
        crosscheck_binary = (HERE / relative).absolute()
    exiftool = Path(frozen["dependencies"]["exiftool"]["path"])
    current = collect_manifest(
        exiftool,
        crosscheck_binary,
        source_tree_parent_commit=frozen["source_tree_parent_commit"],
        git_commit_overrides={
            "preregistration": frozen["preregistration"]["git_commit"],
            "existing_estimator": frozen["existing_estimator"][
                "git_commit"
            ],
        },
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
        "cargo_closure_file_count": frozen["external_decoder_path"][
            "cargo_dependency_closure"
        ]["file_count"],
        "crosscheck_executable_sha256": executable["sha256"],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("create", "write"):
        write = commands.add_parser(name)
        write.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
        write.add_argument("--exiftool", type=Path, required=True)
        write.add_argument(
            "--crosscheck-bin",
            type=Path,
            default=DEFAULT_CROSSCHECK_BINARY,
        )
    check = commands.add_parser("check")
    check.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    check.add_argument("--crosscheck-bin", type=Path)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"create", "write"}:
            payload = collect_manifest(
                args.exiftool.absolute(),
                args.crosscheck_bin.absolute(),
            )
            M.write_json(args.manifest.absolute(), payload)
            output = {
                "status": "FROZEN",
                "manifest": str(args.manifest.absolute()),
                "manifest_sha256": M.sha256_file(args.manifest.absolute()),
            }
        else:
            output = check_manifest(
                args.manifest.absolute(),
                (
                    args.crosscheck_bin.absolute()
                    if args.crosscheck_bin is not None
                    else None
                ),
            )
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
