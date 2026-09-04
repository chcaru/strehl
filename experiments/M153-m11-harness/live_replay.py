from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from m11_core import LANE_ROOT, path_is_within, sha256_file, strict_json_loads


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.QueryPerformanceCounter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
kernel32.QueryPerformanceCounter.restype = wt.BOOL
kernel32.QueryPerformanceFrequency.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
kernel32.QueryPerformanceFrequency.restype = wt.BOOL
kernel32.CreateFileW.argtypes = [
    wt.LPCWSTR,
    wt.DWORD,
    wt.DWORD,
    ctypes.c_void_p,
    wt.DWORD,
    wt.DWORD,
    wt.HANDLE,
]
kernel32.CreateFileW.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL

GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def qpc_frequency() -> int:
    value = ctypes.c_longlong()
    if not kernel32.QueryPerformanceFrequency(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(value.value)


def qpc_ticks() -> int:
    value = ctypes.c_longlong()
    if not kernel32.QueryPerformanceCounter(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(value.value)


def read_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"))


def write_json_flushed(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, allow_nan=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def command_path_candidates(argv: list[Any], cwd: Path) -> list[Path]:
    candidates = []
    for raw_token in argv:
        token = str(raw_token)
        values = [token]
        if token.startswith(("-", "/")) and "=" in token:
            values.append(token.split("=", 1)[1])
        for value in values:
            path = Path(value)
            if not path.is_absolute():
                path = cwd / path
            if path.exists():
                candidates.append(path.resolve(strict=True))
    return candidates


class AvailabilityLocks:
    """Deny renderer reads until each source frame becomes available."""

    def __init__(self, paths: list[Path]) -> None:
        self._handles: list[wt.HANDLE | None] = []
        try:
            for path in paths:
                handle = kernel32.CreateFileW(
                    str(path.resolve(strict=True)),
                    GENERIC_READ,
                    0,
                    None,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    None,
                )
                if handle == INVALID_HANDLE_VALUE:
                    raise ctypes.WinError(ctypes.get_last_error())
                self._handles.append(handle)
        except BaseException:
            self.close()
            raise

    def release(self, index: int) -> None:
        handle = self._handles[index]
        if handle is not None:
            if not kernel32.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self._handles[index] = None

    def close(self) -> None:
        for index, handle in enumerate(self._handles):
            if handle is not None:
                kernel32.CloseHandle(handle)
                self._handles[index] = None


def validate_spec(spec_path: Path, spec: dict[str, Any]) -> None:
    if spec.get("schema") != "m153-live-replay-v1":
        raise ValueError("unsupported live replay schema")
    frames = spec.get("frames", [])
    if len(frames) != 100:
        raise ValueError(f"live replay requires exactly 100 frames, got {len(frames)}")
    expected = [f"DSC{number:05d}.ARW" for number in range(1, 101)]
    actual = [str(frame.get("name", "")).upper() for frame in frames]
    if actual != expected:
        raise ValueError("live replay frame names/order do not match DSC00001-DSC00100")
    shutter_offsets = [
        float(frame.get("shutter_close_offset_seconds", -1.0)) for frame in frames
    ]
    availability_offsets = [
        float(frame.get("file_available_offset_seconds", -1.0)) for frame in frames
    ]
    if (
        spec.get("signed_acquisition_trace_verified") is not True
        or shutter_offsets[0] != 0.0
        or any(
            later < earlier
            for earlier, later in zip(shutter_offsets, shutter_offsets[1:])
        )
        or any(
            later < earlier
            for earlier, later in zip(
                availability_offsets,
                availability_offsets[1:],
            )
        )
        or any(
            available < shutter
            for shutter, available in zip(shutter_offsets, availability_offsets)
        )
    ):
        raise ValueError(
            "live replay requires a verified signed trace with monotone shutter "
            "and durable-availability offsets"
        )
    resolved_sources = []
    source_directories: set[Path] = set()
    file_ids = []
    for frame in frames:
        source = Path(frame["staged_path"])
        if source.name.upper() != str(frame["name"]).upper():
            raise ValueError(
                f"live source basename does not match manifest name: {source}"
            )
        if not path_is_within(source, LANE_ROOT):
            raise ValueError(f"live replay source is outside the owned tree: {source}")
        if not source.is_file():
            raise FileNotFoundError(source)
        resolved = source.resolve(strict=True)
        if not path_is_within(resolved, LANE_ROOT):
            raise ValueError(f"live source resolves outside the owned tree: {source}")
        if sha256_file(source) != frame["sha256"]:
            raise ValueError(f"live replay staged hash mismatch: {source}")
        stat = resolved.stat()
        resolved_sources.append(str(resolved).casefold())
        source_directories.add(resolved.parent)
        file_ids.append((stat.st_dev, stat.st_ino))
    if len(set(resolved_sources)) != 100 or len(set(file_ids)) != 100:
        raise ValueError("live replay frames must be 100 distinct staged files")
    spool_parent = Path(spec["spool_dir"]).resolve(strict=False).parent
    if any(
        Path(frame["staged_path"]).stat().st_dev != spool_parent.stat().st_dev
        for frame in frames
    ):
        raise ValueError(
            "live replay requires staged frames and spool on one volume "
            "for atomic hard-link reveal"
        )
    native_manifest_path = Path(spec["native_input_manifest"]["path"])
    native_manifest_hash = spec["native_input_manifest"]["sha256"]
    if sha256_file(native_manifest_path) != native_manifest_hash:
        raise ValueError("live native-input manifest hash mismatch")
    native_manifest = read_json(native_manifest_path)
    native_prefix = native_manifest.get("files", [])[:100]
    if [(row.get("name", "").upper(), row.get("sha256")) for row in native_prefix] != [
        (frame["name"].upper(), frame["sha256"]) for frame in frames
    ]:
        raise ValueError("live frames do not match the frozen native first-100 prefix")
    cadence_path = Path(spec["cadence_manifest"]["path"])
    cadence_hash = spec["cadence_manifest"]["sha256"]
    if sha256_file(cadence_path) != cadence_hash:
        raise ValueError("live cadence manifest hash mismatch")
    cadence = read_json(cadence_path)
    if cadence.get("schema") != "m153-signed-acquisition-trace-v1":
        raise ValueError("live trace has the wrong schema")
    expected_trace_rows = [
        (
            row.get("name", "").upper(),
            float(row.get("shutter_close_offset_seconds", -1.0)),
            float(row.get("file_available_offset_seconds", -1.0)),
        )
        for row in cadence.get("frames", [])
    ]
    actual_trace_rows = [
        (
            frame["name"].upper(),
            float(frame["shutter_close_offset_seconds"]),
            float(frame["file_available_offset_seconds"]),
        )
        for frame in frames
    ]
    if expected_trace_rows != actual_trace_rows:
        raise ValueError("live offsets do not match the bound signed acquisition trace")
    spool = Path(spec["spool_dir"]).resolve(strict=False)
    stacker_cwd = Path(spec.get("stacker_cwd", LANE_ROOT)).resolve(strict=True)
    referenced_paths = command_path_candidates(spec["stacker_argv"], stacker_cwd)
    allowed_directories = {
        Path(path).resolve(strict=False)
        for path in spec.get("allowed_stacker_directories", [])
    }
    expected_allowed_directories = {
        spool,
        *(spool.parent / name for name in ("temp", "cache", "warpmap")),
    }
    if (
        any(
            path == source_dir or path_is_within(path, source_dir)
            for path in [stacker_cwd, *referenced_paths]
            for source_dir in source_directories
        )
        or allowed_directories != expected_allowed_directories
        or any(
            path.is_dir() and path not in allowed_directories
            for path in referenced_paths
        )
    ):
        raise ValueError(
            "stacker command exposes a pre-availability source path or directory"
        )
    for key in ("spool_dir", "marker_path"):
        if not path_is_within(Path(spec[key]), LANE_ROOT):
            raise ValueError(f"{key} is outside the owned tree")


def replay(spec_path: Path) -> int:
    spec = read_json(spec_path)
    validate_spec(spec_path, spec)
    spool = Path(spec["spool_dir"])
    marker = Path(spec["marker_path"])
    if spool.exists():
        raise FileExistsError(f"live spool already exists: {spool}")
    if marker.exists():
        raise FileExistsError(f"live marker already exists: {marker}")
    spool.mkdir(parents=True)
    availability_locks = AvailabilityLocks(
        [Path(frame["staged_path"]) for frame in spec["frames"]]
    )
    stacker: subprocess.Popen[bytes] | None = None
    frequency = qpc_frequency()
    try:
        stacker = subprocess.Popen(
            [str(token) for token in spec["stacker_argv"]],
            cwd=Path(spec.get("stacker_cwd", LANE_ROOT)),
            env=os.environ.copy(),
        )
        start_ticks = qpc_ticks()
        for index, frame in enumerate(spec["frames"], 1):
            target_ticks = start_ticks + round(
                float(frame["file_available_offset_seconds"]) * frequency
            )
            remaining = (target_ticks - qpc_ticks()) / frequency
            if remaining > 0:
                time.sleep(remaining)
            source = Path(frame["staged_path"])
            destination = spool / frame["name"]
            os.link(source, destination)
            availability_locks.release(index - 1)
            if index == 100:
                available_qpc_ticks = qpc_ticks()
                shutter_close_qpc_ticks = start_ticks + round(
                    float(frame["shutter_close_offset_seconds"]) * frequency
                )
                write_json_flushed(
                    marker,
                    {
                        "schema": "m153-live-epoch-v1",
                        "count": 100,
                        "frame_100": frame["name"],
                        "signed_acquisition_trace_verified": True,
                        "frame_100_source_hash_verified": True,
                        "frame_100_atomic_hardlink_reveal": True,
                        "preavailability_read_locks_enforced": True,
                        "qpc_frequency": frequency,
                        "frame_100_shutter_close_qpc_ticks": (shutter_close_qpc_ticks),
                        "frame_100_available_qpc_ticks": available_qpc_ticks,
                        "cadence_manifest_sha256": spec["cadence_manifest"]["sha256"],
                    },
                )
        return stacker.wait()
    finally:
        availability_locks.close()
        if stacker is not None and stacker.poll() is None:
            stacker.kill()
            stacker.wait()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    return replay(args.spec)


if __name__ == "__main__":
    raise SystemExit(main())
