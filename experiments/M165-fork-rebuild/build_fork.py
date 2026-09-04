#!/usr/bin/env python3
"""Rebuild and freeze the pinned focus-stack fork twice on Windows."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


SCHEMA = "m165-fork-build-freeze-v1"
EXPECTED_SOURCE_SCHEMA = "m165-fork-source-pin-v1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class BuildFailure(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path, label: str) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise BuildFailure(f"cannot read {label} {path}: {exc}") from exc
    return {
        "label": label,
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def require_success(
    command: list[str],
    *,
    label: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> bytes:
    completed = run(command, cwd=cwd, env=env)
    if completed.returncode != 0:
        tail = completed.stdout.decode("utf-8", errors="replace")[-8000:]
        raise BuildFailure(f"{label} failed ({completed.returncode}):\n{tail}")
    return completed.stdout


def load_pin(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildFailure(f"cannot load source pin {path}: {exc}") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != EXPECTED_SOURCE_SCHEMA
        or value.get("status") != "FROZEN"
    ):
        raise BuildFailure("source pin is not a frozen M165 fork source manifest")
    commit = value.get("commit", {}).get("resolved")
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        raise BuildFailure("source pin does not contain a full commit SHA-1")
    return data, value


def vc_environment(vcvars: Path, work: Path) -> dict[str, str]:
    launcher = work / "capture-vc-environment.cmd"
    launcher.write_text(
        "\r\n".join(
            (
                "@echo off",
                f'call "{vcvars}" >nul 2>&1',
                "if errorlevel 1 exit /b 1",
                "set",
                "",
            )
        ),
        encoding="ascii",
        newline="",
    )
    completed = run(
        [os.environ["COMSPEC"], "/d", "/c", str(launcher)],
        cwd=work,
    )
    if completed.returncode != 0:
        raise BuildFailure(
            f"vcvars64 failed ({completed.returncode}): "
            + completed.stdout.decode("utf-8", errors="replace")[-4000:]
        )
    environment = os.environ.copy()
    for raw_line in completed.stdout.decode("utf-8", errors="replace").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        environment[key] = value
    return environment


def extract_and_verify_source(
    repo: Path,
    commit: str,
    source_pin: dict[str, Any],
    work: Path,
    label: str,
) -> tuple[Path, dict[str, Any]]:
    source = work / f"source-{label}"
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)

    expected_files = source_pin["source_subtree"]["files"]
    expected: dict[str, dict[str, Any]] = {}
    for item in expected_files:
        prefix = "focus-stack/"
        path = item["path"]
        if not path.startswith(prefix):
            raise BuildFailure(f"source pin path is outside focus-stack: {path}")
        relative = path[len(prefix) :]
        expected[relative] = item
        blob = run(
            ["git", "-C", str(repo), "cat-file", "blob", item["git_blob_sha1"]]
        )
        if blob.returncode != 0:
            raise BuildFailure(
                f"cannot extract source blob {item['git_blob_sha1']}: "
                + blob.stdout.decode("utf-8", errors="replace")[-4000:]
            )
        if len(blob.stdout) != item["bytes"] or sha256_bytes(blob.stdout) != item["sha256"]:
            raise BuildFailure(f"Git blob differs from source pin: {path}")
        target = source / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob.stdout)

    actual_paths = sorted(
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file()
    )
    if actual_paths != sorted(expected):
        missing = sorted(set(expected).difference(actual_paths))
        extra = sorted(set(actual_paths).difference(expected))
        raise BuildFailure(f"extracted source set differs: missing={missing}, extra={extra}")

    checked: list[dict[str, Any]] = []
    for relative in actual_paths:
        record = file_record(source / relative, relative)
        reference = expected[relative]
        if (
            record["bytes"] != reference["bytes"]
            or record["sha256"] != reference["sha256"]
        ):
            raise BuildFailure(f"source file differs from pin: {relative}")
        checked.append(
            {
                "path": f"focus-stack/{relative}",
                "mode": reference["mode"],
                "git_blob_sha1": reference["git_blob_sha1"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
            }
        )
    source_manifest_sha = sha256_bytes(canonical_json(checked))
    expected_manifest_sha = source_pin["source_subtree"]["manifest_sha256"]
    if source_manifest_sha != expected_manifest_sha:
        raise BuildFailure(
            f"source manifest is {source_manifest_sha}, expected {expected_manifest_sha}"
        )
    return source, {
        "file_count": len(checked),
        "manifest_sha256": source_manifest_sha,
    }


def build_one(
    *,
    repo: Path,
    commit: str,
    source_pin: dict[str, Any],
    work: Path,
    label: str,
    opencv_build: Path,
    cmake_executable: Path,
    base_environment: dict[str, str],
    source_date_epoch: int,
) -> dict[str, Any]:
    source, source_check = extract_and_verify_source(
        repo, commit, source_pin, work, label
    )
    build = work / f"build-{label}"
    if build.exists():
        shutil.rmtree(build)

    compiler_flags = [
        "/Brepro",
        "/experimental:deterministic",
        "/EHsc",
        "/wd4005",
        f'/DGIT_VERSION=\\"{commit}\\"',
        f"/pathmap:{source}=C:\\m165\\focus-stack",
    ]
    environment = base_environment.copy()
    environment["SOURCE_DATE_EPOCH"] = str(source_date_epoch)
    environment["CL"] = " ".join(compiler_flags)

    configure = [
        str(cmake_executable),
        "-S",
        str(source),
        "-B",
        str(build),
        "-G",
        "NMake Makefiles",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_TESTS=OFF",
        f"-DOpenCV_DIR={opencv_build}",
        "-DCMAKE_EXE_LINKER_FLAGS=/Brepro",
        "-DCMAKE_STATIC_LINKER_FLAGS=/Brepro",
    ]
    build_command = [
        str(cmake_executable),
        "--build",
        str(build),
        "--config",
        "Release",
    ]
    configure_log = require_success(
        configure, label=f"configure build {label}", env=environment
    )
    build_log = require_success(
        build_command, label=f"compile build {label}", env=environment
    )
    log = work / f"build-{label}.log"
    log.write_bytes(configure_log + build_log)

    executable = build / "focus-stack.exe"
    executable_record = file_record(executable, f"focus-stack build {label}")
    runtime_environment = environment.copy()
    opencv_bin = opencv_build / "x64" / "vc16" / "bin"
    runtime_environment["PATH"] = (
        str(opencv_bin) + os.pathsep + runtime_environment["PATH"]
    )
    version = require_success(
        [str(executable), "--version"],
        label=f"version probe build {label}",
        env=runtime_environment,
    ).decode("utf-8", errors="replace")
    first_lines = version.splitlines()[:2]
    if not first_lines or commit not in first_lines[0]:
        raise BuildFailure(f"build {label} version banner does not bind commit")
    if "built 1 1" not in first_lines[0]:
        raise BuildFailure(f"build {label} did not neutralize __DATE__/__TIME__")

    return {
        "label": label,
        "source_path": str(source),
        "build_path": str(build),
        "source_check": source_check,
        "configure_argv": configure,
        "build_argv": build_command,
        "compiler_environment_flags": compiler_flags,
        "source_date_epoch": source_date_epoch,
        "log": file_record(log, f"build {label} log"),
        "executable": executable_record,
        "version_banner": first_lines,
    }


def tool_record(path: Path, label: str) -> dict[str, Any]:
    return file_record(path, label)


def build_freeze(args: argparse.Namespace) -> dict[str, Any]:
    frozen = datetime.fromisoformat(args.frozen_utc.replace("Z", "+00:00"))
    if frozen.utcoffset() is None:
        raise BuildFailure("--frozen-utc must include an offset")

    repo = Path(args.repo).resolve()
    source_pin_path = Path(args.source_pin).resolve()
    source_pin_bytes, source_pin = load_pin(source_pin_path)
    commit = source_pin["commit"]["resolved"]
    if commit != args.commit:
        raise BuildFailure(f"requested commit {args.commit} differs from pin {commit}")

    vcvars = Path(args.vcvars).resolve()
    opencv_build = Path(args.opencv_build).resolve()
    work = Path(args.work).resolve()
    bin_dir = Path(args.bin).resolve()
    work.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)

    base_environment = vc_environment(vcvars, work)
    cmake_value = shutil.which("cmake", path=base_environment["PATH"])
    if cmake_value is None:
        raise BuildFailure("cmake is absent from the Visual Studio environment")
    cmake_path = Path(cmake_value).resolve()
    source_time = datetime.fromisoformat(
        source_pin["commit"]["committer_utc_offset_time"]
    )
    source_date_epoch = int(source_time.timestamp())

    builds = [
        build_one(
            repo=repo,
            commit=commit,
            source_pin=source_pin,
            work=work,
            label=label,
            opencv_build=opencv_build,
            cmake_executable=cmake_path,
            base_environment=base_environment,
            source_date_epoch=source_date_epoch,
        )
        for label in ("a", "b")
    ]
    first = builds[0]["executable"]
    second = builds[1]["executable"]
    identical = (
        first["sha256"] == second["sha256"]
        and first["bytes"] == second["bytes"]
        and Path(first["path"]).read_bytes() == Path(second["path"]).read_bytes()
    )
    if not identical:
        raise BuildFailure(
            f"clean builds differ: {first['sha256']} versus {second['sha256']}"
        )

    executable = bin_dir / "focus-stack.exe"
    opencv_dll = bin_dir / "opencv_world4130.dll"
    shutil.copyfile(first["path"], executable)
    shutil.copyfile(
        opencv_build / "x64" / "vc16" / "bin" / "opencv_world4130.dll",
        opencv_dll,
    )
    runtime_names = (
        "msvcp140.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "concrt140.dll",
    )
    runtime_paths: list[Path] = []
    for name in runtime_names:
        source = Path(os.environ["WINDIR"]) / "System32" / name
        target = bin_dir / name
        shutil.copyfile(source, target)
        runtime_paths.append(target)

    bundle_paths = [executable, opencv_dll, *runtime_paths]
    runtime_bundle = [
        file_record(path, path.name.lower()) for path in bundle_paths
    ]
    portable_bundle = [
        {
            "label": item["label"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
        }
        for item in runtime_bundle
    ]

    cl_path = Path(base_environment["VCToolsInstallDir"]) / "bin" / "Hostx64" / "x64" / "cl.exe"
    link_path = cl_path.with_name("link.exe")
    lib_path = cl_path.with_name("lib.exe")
    nmake_path = cl_path.with_name("nmake.exe")
    compiler_probe = run(
        [str(cl_path), "/Bv"], env=base_environment
    ).stdout.decode("utf-8", errors="replace")
    cmake_version = require_success(
        [str(cmake_path), "--version"], label="cmake version", env=base_environment
    ).decode("utf-8", errors="replace").splitlines()[0]

    return {
        "schema": SCHEMA,
        "status": "FROZEN",
        "frozen_utc": frozen.isoformat(),
        "source": {
            "commit_sha1": commit,
            "tree_sha1": source_pin["source_subtree"]["git_tree_sha1"],
            "manifest_sha256": source_pin["source_subtree"]["manifest_sha256"],
            "source_pin_path": str(source_pin_path),
            "source_pin_sha256": sha256_bytes(source_pin_bytes),
        },
        "build_recipe": {
            "generator": "NMake Makefiles",
            "configuration": "Release",
            "build_tests": False,
            "source_date_epoch": source_date_epoch,
            "canonical_source_path": r"C:\m165\focus-stack",
            "compiler_flags": builds[0]["compiler_environment_flags"],
            "executable_linker_flags": ["/Brepro"],
            "static_linker_flags": ["/Brepro"],
            "build_script": file_record(Path(__file__).resolve(), "build_fork.py"),
        },
        "toolchain": {
            "vcvars64": tool_record(vcvars, "vcvars64.bat"),
            "cl": tool_record(cl_path, "cl.exe"),
            "link": tool_record(link_path, "link.exe"),
            "lib": tool_record(lib_path, "lib.exe"),
            "nmake": tool_record(nmake_path, "nmake.exe"),
            "cmake": tool_record(cmake_path, "cmake.exe"),
            "compiler_probe": compiler_probe.splitlines(),
            "cmake_version": cmake_version,
            "vc_tools_version": base_environment.get("VCToolsVersion"),
            "windows_sdk_version": base_environment.get("WindowsSDKVersion"),
        },
        "dependencies": {
            "opencv_version": "4.13.0",
            "opencv_import_library": file_record(
                opencv_build / "x64" / "vc16" / "lib" / "opencv_world4130.lib",
                "opencv_world4130.lib",
            ),
            "runtime_bundle": runtime_bundle,
            "runtime_bundle_sha256": sha256_bytes(canonical_json(portable_bundle)),
            "system_dependencies_not_bundled": [
                "Windows API-set DLLs",
                "KERNEL32.dll",
                "USER32.dll",
                "GDI32.dll",
                "ADVAPI32.dll",
                "ole32.dll",
                "OLEAUT32.dll",
                "COMDLG32.dll",
                "WS2_32.dll",
                "MFPlat.dll",
                "MF.dll",
                "MFReadWrite.dll",
                "dxgi.dll",
                "d3d11.dll",
                "SHLWAPI.dll",
            ],
        },
        "reproducibility": {
            "verdict": "BIT_REPRODUCIBLE_TWO_CLEAN_PATHS_SAME_HOST",
            "build_count": 2,
            "byte_identical": True,
            "differing_bytes": 0,
            "builds": builds,
        },
        "frozen_executable": file_record(executable, "focus-stack.exe"),
        "hash_contract": {
            "algorithm": "SHA-256",
            "bytes": "[0,file_size)",
        },
        "freeze_order": {
            "executable_hash_recorded_before_rendering": True,
            "pre_freeze_executions": ["--version"],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--source-pin", required=True)
    parser.add_argument("--vcvars", required=True)
    parser.add_argument("--opencv-build", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--bin", required=True)
    parser.add_argument("--frozen-utc", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    try:
        result = build_freeze(args)
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
