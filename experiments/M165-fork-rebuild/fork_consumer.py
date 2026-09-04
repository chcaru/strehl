#!/usr/bin/env python3
"""Locked one-read adapter for the pinned focus-stack consumer."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any, Iterator


ATTESTATION_SCHEMA = "m165-consumer-input-attestation-v1"
HASH_RE_LENGTH = 64
TIFF_TAGS = {
    "width": 256,
    "height": 257,
    "bits": 258,
    "compression": 259,
    "photometric": 262,
    "description": 270,
    "strip_offsets": 273,
    "samples_per_pixel": 277,
    "rows_per_strip": 278,
    "strip_byte_counts": 279,
    "planar": 284,
    "sample_format": 339,
    "icc": 34675,
}
TIFF_TYPES = {1: 1, 2: 1, 3: 2, 4: 4, 7: 1}

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class ConsumerFailure(RuntimeError):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


class ByHandleFileInformation(ctypes.Structure):
    _fields_ = [
        ("file_attributes", wintypes.DWORD),
        ("creation_time", wintypes.FILETIME),
        ("last_access_time", wintypes.FILETIME),
        ("last_write_time", wintypes.FILETIME),
        ("volume_serial_number", wintypes.DWORD),
        ("file_size_high", wintypes.DWORD),
        ("file_size_low", wintypes.DWORD),
        ("number_of_links", wintypes.DWORD),
        ("file_index_high", wintypes.DWORD),
        ("file_index_low", wintypes.DWORD),
    ]


def require(condition: bool, failure_class: str, message: str) -> None:
    if not condition:
        raise ConsumerFailure(failure_class, message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_hash(value: str) -> bool:
    return (
        len(value) == HASH_RE_LENGTH
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def checked_range(data: bytes, offset: int, length: int, label: str) -> bytes:
    require(
        offset >= 0
        and length >= 0
        and offset <= len(data)
        and length <= len(data) - offset,
        "TIFF_RANGE_INVALID",
        f"{label} [{offset},{offset + length}) exceeds {len(data)} bytes",
    )
    return data[offset : offset + length]


def parse_common_tiff(data: bytes) -> dict[str, Any]:
    require(
        len(data) >= 8 and data[:4] == b"II*\x00",
        "TIFF_HEADER_REJECTED",
        "input is not a little-endian classic TIFF",
    )

    def u16(offset: int, label: str) -> int:
        return struct.unpack("<H", checked_range(data, offset, 2, label))[0]

    def u32(offset: int, label: str) -> int:
        return struct.unpack("<I", checked_range(data, offset, 4, label))[0]

    ifd_offset = u32(4, "IFD offset")
    entry_count = u16(ifd_offset, "IFD entry count")
    table_start = ifd_offset + 2
    checked_range(data, table_start, entry_count * 12 + 4, "IFD table")
    require(
        u32(table_start + entry_count * 12, "next IFD") == 0,
        "TIFF_MULTI_IMAGE_REJECTED",
        "common TIFF must contain exactly one image",
    )

    entries: dict[int, tuple[int, int, bytes]] = {}
    for index in range(entry_count):
        offset = table_start + index * 12
        tag = u16(offset, "IFD tag")
        kind = u16(offset + 2, "IFD type")
        count = u32(offset + 4, "IFD count")
        require(
            tag in TIFF_TAGS.values(),
            "TIFF_TAG_REJECTED",
            f"TIFF tag {tag} is outside the common-input allowlist",
        )
        require(
            tag not in entries,
            "TIFF_TAG_DUPLICATE",
            f"duplicate TIFF tag {tag}",
        )
        entries[tag] = (kind, count, checked_range(data, offset + 8, 4, "IFD value"))

    missing = sorted(set(TIFF_TAGS.values()).difference(entries))
    require(
        not missing,
        "TIFF_TAG_MISSING",
        f"required TIFF tags are absent: {missing}",
    )

    def field_bytes(tag: int) -> bytes:
        kind, count, inline = entries[tag]
        unit = TIFF_TYPES.get(kind)
        require(
            unit is not None,
            "TIFF_TYPE_REJECTED",
            f"tag {tag} uses unsupported TIFF type {kind}",
        )
        length = unit * count
        if length <= 4:
            return inline[:length]
        return checked_range(
            data, struct.unpack("<I", inline)[0], length, f"tag {tag}"
        )

    def numbers(tag: int) -> list[int]:
        kind, count, _ = entries[tag]
        raw = field_bytes(tag)
        if kind == 3:
            return list(struct.unpack("<" + "H" * count, raw))
        if kind == 4:
            return list(struct.unpack("<" + "I" * count, raw))
        raise ConsumerFailure(
            "TIFF_TYPE_REJECTED", f"tag {tag} is not SHORT or LONG"
        )

    def scalar(tag: int, label: str) -> int:
        values = numbers(tag)
        require(
            len(values) == 1,
            "TIFF_FIELD_INVALID",
            f"{label} must contain one value",
        )
        return values[0]

    width = scalar(TIFF_TAGS["width"], "ImageWidth")
    height = scalar(TIFF_TAGS["height"], "ImageLength")
    require(width > 0 and height > 0, "TIFF_DIMENSIONS_INVALID", "zero dimension")
    bits = numbers(TIFF_TAGS["bits"])
    sample_format = numbers(TIFF_TAGS["sample_format"])
    compression = scalar(TIFF_TAGS["compression"], "Compression")
    photometric = scalar(TIFF_TAGS["photometric"], "PhotometricInterpretation")
    samples = scalar(TIFF_TAGS["samples_per_pixel"], "SamplesPerPixel")
    planar = scalar(TIFF_TAGS["planar"], "PlanarConfiguration")
    require(bits == [16, 16, 16], "TIFF_BITS_INVALID", "expected 16-bit RGB")
    require(
        sample_format == [1, 1, 1],
        "TIFF_SAMPLE_FORMAT_INVALID",
        "expected unsigned integer RGB samples",
    )
    require(compression == 1, "TIFF_COMPRESSION_INVALID", "expected uncompressed TIFF")
    require(photometric == 2, "TIFF_PHOTOMETRIC_INVALID", "expected RGB TIFF")
    require(samples == 3, "TIFF_SAMPLES_INVALID", "expected three samples per pixel")
    require(planar == 1, "TIFF_PLANAR_INVALID", "expected contiguous RGB samples")

    rows_per_strip = scalar(TIFF_TAGS["rows_per_strip"], "RowsPerStrip")
    offsets = numbers(TIFF_TAGS["strip_offsets"])
    byte_counts = numbers(TIFF_TAGS["strip_byte_counts"])
    expected_strips = (height + rows_per_strip - 1) // rows_per_strip
    require(
        rows_per_strip > 0
        and len(offsets) == expected_strips
        and len(byte_counts) == expected_strips,
        "TIFF_STRIP_INVALID",
        "strip tables do not cover the image",
    )

    digest = hashlib.sha256()
    ranges: list[dict[str, int]] = []
    occupied: list[tuple[int, int]] = []
    total = 0
    row_bytes = width * samples * 2
    for index, (offset, count) in enumerate(zip(offsets, byte_counts, strict=True)):
        rows = min(rows_per_strip, height - index * rows_per_strip)
        require(
            count == rows * row_bytes,
            "TIFF_STRIP_INVALID",
            f"strip {index} has {count} bytes, expected {rows * row_bytes}",
        )
        payload = checked_range(data, offset, count, f"pixel strip {index}")
        end = offset + count
        require(
            all(end <= start0 or offset >= end0 for start0, end0 in occupied),
            "TIFF_STRIP_OVERLAP",
            f"pixel strip {index} overlaps another strip",
        )
        occupied.append((offset, end))
        digest.update(payload)
        ranges.append({"start": offset, "end_exclusive": end})
        total += count
    require(
        total == width * height * samples * 2,
        "TIFF_PAYLOAD_SIZE_INVALID",
        "pixel payload byte count differs from dimensions",
    )

    icc = field_bytes(TIFF_TAGS["icc"])
    require(
        len(icc) >= 128 and icc[36:40] == b"acsp",
        "TIFF_ICC_INVALID",
        "embedded ICC is absent or malformed",
    )
    description = field_bytes(TIFF_TAGS["description"])
    require(
        description.endswith(b"\0"),
        "TIFF_PROVENANCE_INVALID",
        "ImageDescription is not NUL terminated",
    )
    try:
        provenance = json.loads(description[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConsumerFailure(
            "TIFF_PROVENANCE_INVALID", f"ImageDescription is not UTF-8 JSON: {exc}"
        ) from exc
    require(
        isinstance(provenance, dict),
        "TIFF_PROVENANCE_INVALID",
        "ImageDescription provenance is not an object",
    )

    return {
        "width": width,
        "height": height,
        "bits_per_sample": bits,
        "sample_format": sample_format,
        "compression": compression,
        "photometric": photometric,
        "planar_configuration": planar,
        "strip_count": len(ranges),
        "file_bytes": len(data),
        "file_sha256": sha256(data),
        "pixel_payload_bytes": total,
        "pixel_payload_sha256": digest.hexdigest(),
        "whole_file_hash": {
            "algorithm": "sha256",
            "ranges": [{"start": 0, "end_exclusive": len(data)}],
        },
        "pixel_payload_hash": {
            "algorithm": "sha256-concatenated-ranges-in-listed-order",
            "ranges": ranges,
        },
        "icc_sha256": sha256(icc),
        "provenance": provenance,
    }


def file_information(handle: int) -> dict[str, int]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ByHandleFileInformation),
    ]
    kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
    info = ByHandleFileInformation()
    if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
        raise ConsumerFailure(
            "INPUT_METADATA_FAILED",
            f"GetFileInformationByHandle failed with WinError {ctypes.get_last_error()}",
        )
    return {
        "volume_serial_number": int(info.volume_serial_number),
        "file_index": (int(info.file_index_high) << 32) | int(info.file_index_low),
        "file_size": (int(info.file_size_high) << 32) | int(info.file_size_low),
        "last_write_filetime": (
            int(info.last_write_time.dwHighDateTime) << 32
        )
        | int(info.last_write_time.dwLowDateTime),
    }


@contextmanager
def locked_input(path: Path) -> Iterator[tuple[bytes, dict[str, int], int]]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.CreateFileW(
        str(path),
        GENERIC_READ,
        FILE_SHARE_READ,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        raise ConsumerFailure(
            "INPUT_LOCK_FAILED",
            f"CreateFileW failed with WinError {ctypes.get_last_error()}",
        )
    fd = -1
    stream = None
    try:
        fd = msvcrt.open_osfhandle(int(handle), os.O_RDONLY | os.O_BINARY)
        handle = None
        stream = os.fdopen(fd, "rb", closefd=True)
        fd = -1
        os_handle = msvcrt.get_osfhandle(stream.fileno())
        before = file_information(os_handle)
        data = stream.read()
        after_read = file_information(os_handle)
        require(
            before == after_read and len(data) == before["file_size"],
            "INPUT_CHANGED_DURING_READ",
            "input identity, size, or last-write metadata changed during the read",
        )
        yield data, before, os_handle
    finally:
        if stream is not None:
            stream.close()
        elif fd >= 0:
            os.close(fd)
        elif handle not in (None, INVALID_HANDLE_VALUE):
            kernel32.CloseHandle(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--consumer-id", required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--executable-sha256", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--attestation", required=True)
    return parser.parse_args()


def attestation_argument(argv: list[str]) -> Path | None:
    for index, token in enumerate(argv):
        if token == "--attestation" and index + 1 < len(argv):
            return Path(argv[index + 1])
        if token.startswith("--attestation="):
            return Path(token.split("=", 1)[1])
    return None


def run_consumer(args: argparse.Namespace) -> dict[str, Any]:
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    attestation_path = Path(args.attestation).resolve()
    executable = Path(args.executable).resolve()
    require(
        args.consumer_id == "focus-stack-fork",
        "CONSUMER_ID_INVALID",
        "this adapter is frozen for focus-stack-fork",
    )
    require(
        valid_hash(args.executable_sha256),
        "EXECUTABLE_HASH_INVALID",
        "--executable-sha256 must be lowercase SHA-256",
    )
    require(input_path.is_file(), "INPUT_ABSENT", f"input is absent: {input_path}")
    require(
        executable.is_file(),
        "EXECUTABLE_ABSENT",
        f"consumer executable is absent: {executable}",
    )
    require(
        output_path not in {input_path, attestation_path},
        "OUTPUT_PATH_INVALID",
        "output must not alias input or attestation",
    )
    require(
        not output_path.exists(),
        "OUTPUT_ALREADY_EXISTS",
        f"refusing stale output: {output_path}",
    )
    executable_data = executable.read_bytes()
    executable_sha = sha256(executable_data)
    require(
        executable_sha == args.executable_sha256,
        "EXECUTABLE_HASH_MISMATCH",
        f"consumer executable is {executable_sha}, expected {args.executable_sha256}",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    invocation = [
        str(executable),
        f"--output={output_path}",
        "--threads=1",
        "--batchsize=2",
        "--no-opencl",
        "--no-align",
        "--no-whitebalance",
        "--no-contrast",
        "--consistency=0",
        "--denoise=0",
        "--input-colorspace=none",
        "--output-colorspace=srgb",
        "--output-bitdepth=16",
        str(input_path),
        str(input_path),
    ]

    with locked_input(input_path) as (input_data, before, os_handle):
        snapshot = parse_common_tiff(input_data)
        completed = subprocess.run(
            invocation,
            check=False,
            capture_output=True,
            text=True,
            cwd=output_path.parent,
        )
        after = file_information(os_handle)
        require(
            before == after,
            "INPUT_CHANGED_DURING_CONSUMPTION",
            "input identity, size, or last-write metadata changed while consumer ran",
        )
    require(
        completed.returncode == 0,
        "CONSUMER_EXIT_NONZERO",
        f"focus-stack exited {completed.returncode}: {completed.stderr[-1000:]}",
    )
    require(
        output_path.is_file() and output_path.stat().st_size > 0,
        "CONSUMER_OUTPUT_ABSENT",
        "focus-stack returned success without a non-empty output",
    )
    output_data = output_path.read_bytes()
    complete_invocation = [sys.executable, str(Path(__file__).resolve())] + sys.argv[1:]
    return {
        "schema": ATTESTATION_SCHEMA,
        "status": "PASS",
        "commissioning_only": True,
        "consumer_id": args.consumer_id,
        "consumer_executable": {
            "path": str(executable),
            "bytes": len(executable_data),
            "sha256": executable_sha,
        },
        "input_path": str(input_path),
        "input_file_sha256": snapshot["file_sha256"],
        "input_pixel_payload_sha256": snapshot["pixel_payload_sha256"],
        "whole_file_hash": snapshot["whole_file_hash"],
        "pixel_payload_hash": snapshot["pixel_payload_hash"],
        "read_contract": {
            "artifact_read_count": 1,
            "hash_and_parse_same_memory": True,
        },
        "locked_handoff": {
            "api": "CreateFileW",
            "desired_access": "GENERIC_READ",
            "share_mode": "FILE_SHARE_READ",
            "held_through_consumer_exit": True,
            "file_information_before": before,
            "file_information_after": after,
            "metadata_unchanged": before == after,
        },
        "tiff": snapshot,
        "complete_invocation": complete_invocation,
        "consumer_invocation": invocation,
        "input_path_occurrences_in_consumer_invocation": invocation.count(
            str(input_path)
        ),
        "exit_code": completed.returncode,
        "process_stdout": completed.stdout,
        "process_stderr": completed.stderr,
        "process_stdout_sha256": sha256(completed.stdout.encode("utf-8")),
        "process_stderr_sha256": sha256(completed.stderr.encode("utf-8")),
        "outputs": [
            {
                "path": str(output_path),
                "bytes": len(output_data),
                "sha256": sha256(output_data),
            }
        ],
    }


def main() -> int:
    destination = attestation_argument(sys.argv[1:])
    try:
        args = parse_args()
        destination = Path(args.attestation)
        report = run_consumer(args)
        write_json(destination, report)
        print(json.dumps(report, sort_keys=True))
        return 0
    except BaseException as exc:
        failure_class = (
            exc.failure_class
            if isinstance(exc, ConsumerFailure)
            else type(exc).__name__.upper()
        )
        report = {
            "schema": ATTESTATION_SCHEMA,
            "status": "FAIL",
            "failure_class": failure_class,
            "reason": str(exc),
        }
        if destination is not None:
            try:
                write_json(destination, report)
            except BaseException:
                pass
        print(json.dumps(report, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
