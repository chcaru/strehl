#!/usr/bin/env python3
"""Fail-closed M165 ProPhoto input-semantics evidence gate.

This gate evaluates an input contract. It does not compare image quality.
Every path artifact is loaded through ``ReadOnce`` and all hashing and parsing
uses the returned immutable bytes object.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import types
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
STREHL_ROOT = HERE.parents[1]
REFERENCE_SCHEMA = "m165-prophoto-semantics-reference-v1"
WITNESS_SCHEMA = "m165-prophoto-semantics-witnesses-v1"
RESULT_SCHEMA = "m165-prophoto-semantics-result-v1"


class GateFailure(RuntimeError):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("ascii")
        + b"\n"
    )
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(encoded)
    os.replace(partial, path)


def parse_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateFailure("MALFORMED_JSON", f"{label}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateFailure("MALFORMED_JSON", f"{label}: top level is not an object")
    return value


class ReadOnce:
    def __init__(self) -> None:
        self._seen: dict[str, str] = {}
        self.records: list[dict[str, Any]] = []

    def read(self, label: str, path: Path) -> bytes:
        resolved = path.resolve()
        key = os.path.normcase(str(resolved))
        if key in self._seen:
            raise GateFailure(
                "PATH_READ_MULTIPLE",
                f"{resolved} requested as {label!r} after {self._seen[key]!r}",
            )
        self._seen[key] = label
        try:
            data = bytes(resolved.read_bytes())
        except OSError as exc:
            raise GateFailure("PATH_READ_FAILED", f"{label}: {resolved}: {exc}") from exc
        self.records.append(
            {
                "label": label,
                "path": str(resolved),
                "read_count": 1,
                "bytes": len(data),
                "sha256": sha256(data),
            }
        )
        return data

    def adopt_locked(self, label: str, path: Path, data: bytes) -> bytes:
        resolved = path.resolve()
        key = os.path.normcase(str(resolved))
        if key in self._seen:
            raise GateFailure(
                "PATH_READ_MULTIPLE",
                f"{resolved} requested as {label!r} after {self._seen[key]!r}",
            )
        self._seen[key] = label
        immutable = bytes(data)
        self.records.append(
            {
                "label": label,
                "path": str(resolved),
                "read_count": 1,
                "read_method": "CreateFileW-held-handle",
                "bytes": len(immutable),
                "sha256": sha256(immutable),
            }
        )
        return immutable


class Ledger:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(
        self,
        check_id: str,
        arm: str,
        passed: bool,
        failure_class: str,
        summary: str,
        evidence: Any | None = None,
    ) -> bool:
        record: dict[str, Any] = {
            "id": check_id,
            "arm": arm,
            "status": "PASS" if passed else "RED",
            "failure_class": None if passed else failure_class,
            "summary": summary,
        }
        if evidence is not None:
            record["evidence"] = evidence
        self.checks.append(record)
        return passed

    def require(
        self,
        check_id: str,
        arm: str,
        passed: bool,
        failure_class: str,
        summary: str,
        evidence: Any | None = None,
    ) -> None:
        if not self.add(
            check_id, arm, passed, failure_class, summary, evidence=evidence
        ):
            raise GateFailure(failure_class, summary)


def check_file_bytes(
    ledger: Ledger,
    check_id: str,
    label: str,
    data: bytes,
    expected: dict[str, Any],
) -> None:
    actual = {"bytes": len(data), "sha256": sha256(data)}
    passed = (
        actual["bytes"] == expected.get("bytes")
        and actual["sha256"] == expected.get("sha256")
    )
    ledger.require(
        check_id,
        "ARTIFACT_IDENTITY",
        passed,
        "ARTIFACT_IDENTITY_MISMATCH",
        f"{label} byte identity",
        {"actual": actual, "expected": expected},
    )


def resolve_strehl(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return STREHL_ROOT / path


def count_line_block(text: str, lines: list[str]) -> int:
    source = text.splitlines()
    width = len(lines)
    if width == 0:
        return 0
    return sum(source[index : index + width] == lines for index in range(len(source)))


def verify_anchor_groups(
    ledger: Ledger,
    check_id: str,
    arm: str,
    text: str,
    anchors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    valid = True
    for anchor in anchors:
        lines = anchor.get("lines")
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise GateFailure("ANCHOR_SPEC_INVALID", f"{check_id}: malformed anchor")
        count = count_line_block(text, lines)
        observations.append(
            {"id": anchor.get("id"), "count": count, "lines": lines}
        )
        valid = valid and count == 1
    ledger.require(
        check_id,
        arm,
        valid,
        "SOURCE_ANCHOR_NOT_UNIQUE",
        f"{check_id} exact full-line anchors are unique",
        observations,
    )
    return observations


def s15fixed16(data: bytes) -> float:
    if len(data) != 4:
        raise GateFailure("ICC_MALFORMED", "s15Fixed16 value has wrong size")
    return struct.unpack(">i", data)[0] / 65536.0


def parse_icc(profile: bytes, label: str) -> dict[str, Any]:
    if len(profile) < 132:
        raise GateFailure("ICC_MALFORMED", f"{label}: shorter than ICC header")
    declared_size = struct.unpack(">I", profile[0:4])[0]
    if declared_size != len(profile) or profile[36:40] != b"acsp":
        raise GateFailure(
            "ICC_MALFORMED",
            f"{label}: size/signature mismatch ({declared_size}, {len(profile)})",
        )
    count = struct.unpack(">I", profile[128:132])[0]
    table_end = 132 + count * 12
    if table_end > len(profile):
        raise GateFailure("ICC_MALFORMED", f"{label}: tag table exceeds profile")
    tags: dict[str, bytes] = {}
    tag_ranges: list[dict[str, Any]] = []
    for index in range(count):
        at = 132 + index * 12
        signature = profile[at : at + 4].decode("ascii", errors="strict")
        offset, size = struct.unpack(">II", profile[at + 4 : at + 12])
        if offset < table_end or size <= 0 or offset + size > len(profile):
            raise GateFailure(
                "ICC_MALFORMED", f"{label}: tag {signature} range is invalid"
            )
        if signature in tags:
            raise GateFailure(
                "ICC_MALFORMED", f"{label}: duplicate tag {signature}"
            )
        tags[signature] = profile[offset : offset + size]
        tag_ranges.append(
            {"signature": signature, "offset": offset, "bytes": size}
        )

    def xyz(signature: str) -> list[float]:
        value = tags.get(signature)
        if value is None or len(value) < 20 or value[:4] != b"XYZ ":
            raise GateFailure(
                "ICC_MALFORMED", f"{label}: {signature} is not an XYZ tag"
            )
        return [s15fixed16(value[8 + i * 4 : 12 + i * 4]) for i in range(3)]

    def curve(signature: str) -> float:
        value = tags.get(signature)
        if value is None or len(value) < 14 or value[:4] != b"curv":
            raise GateFailure(
                "ICC_MALFORMED", f"{label}: {signature} is not a curve tag"
            )
        entries = struct.unpack(">I", value[8:12])[0]
        if entries != 1:
            raise GateFailure(
                "ICC_MALFORMED",
                f"{label}: {signature} is not a one-value gamma curve",
            )
        return struct.unpack(">H", value[12:14])[0] / 256.0

    desc = tags.get("desc")
    if desc is None or len(desc) < 13 or desc[:4] != b"desc":
        raise GateFailure("ICC_MALFORMED", f"{label}: missing v2 description")
    desc_length = struct.unpack(">I", desc[8:12])[0]
    if desc_length <= 0 or 12 + desc_length > len(desc):
        raise GateFailure("ICC_MALFORMED", f"{label}: invalid description length")
    try:
        description = desc[12 : 12 + desc_length].rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError as exc:
        raise GateFailure("ICC_MALFORMED", f"{label}: non-ASCII description") from exc

    version = profile[8] + ((profile[9] >> 4) / 10.0)
    return {
        "bytes": len(profile),
        "sha256": sha256(profile),
        "version": version,
        "class": profile[12:16].decode("ascii", errors="strict"),
        "color_space": profile[16:20].decode("ascii", errors="strict"),
        "pcs": profile[20:24].decode("ascii", errors="strict"),
        "header_illuminant_xyz": [
            s15fixed16(profile[68:72]),
            s15fixed16(profile[72:76]),
            s15fixed16(profile[76:80]),
        ],
        "description": description,
        "matrix_xyz": {
            "rXYZ": xyz("rXYZ"),
            "gXYZ": xyz("gXYZ"),
            "bXYZ": xyz("bXYZ"),
            "wtpt": xyz("wtpt"),
        },
        "gamma": {
            "rTRC": curve("rTRC"),
            "gTRC": curve("gTRC"),
            "bTRC": curve("bTRC"),
        },
        "tag_ranges": tag_ranges,
    }


def max_abs_difference(left: Iterable[float], right: Iterable[float]) -> float:
    pairs = list(zip(left, right, strict=True))
    return max(abs(a - b) for a, b in pairs) if pairs else 0.0


def parse_cpp_matrix(text: str, name: str) -> list[list[float]]:
    pattern = re.compile(
        rf"const double LibRaw_constants::{re.escape(name)}\[3\]\[3\]\s*=\s*"
        r"\{(?P<body>.*?)\};",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise GateFailure(
            "LIBRAW_MATRIX_PARSE_FAILED",
            f"{name}: expected one matrix declaration, found {len(matches)}",
        )
    values = [
        float(value)
        for value in re.findall(
            r"[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?",
            matches[0].group("body"),
        )
    ]
    if len(values) != 9:
        raise GateFailure(
            "LIBRAW_MATRIX_PARSE_FAILED",
            f"{name}: expected 9 matrix values, found {len(values)}",
        )
    return [values[index : index + 3] for index in range(0, 9, 3)]


def module_from_bytes(name: str, source: bytes, origin: Path) -> types.ModuleType:
    try:
        code = compile(source.decode("utf-8"), str(origin), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise GateFailure("LOCK_ADAPTER_LOAD_FAILED", str(exc)) from exc
    module = types.ModuleType(name)
    module.__file__ = str(origin)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except BaseException as exc:
        raise GateFailure("LOCK_ADAPTER_LOAD_FAILED", str(exc)) from exc
    return module


def stable_tiff_summary(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        key: parsed[key]
        for key in (
            "shape",
            "dtype",
            "decoded_pixel_sha256",
            "compression",
            "photometric",
            "planar_configuration",
            "bits_per_sample",
            "icc_sha256",
        )
    }


def lcms_patch_codes(
    profile: bytes,
    patches: Any,
    Image: Any,
    ImageCms: Any,
    np: Any,
) -> Any:
    try:
        transform = ImageCms.buildTransformFromOpenProfiles(
            ImageCms.ImageCmsProfile(BytesIO(profile)),
            ImageCms.createProfile("sRGB"),
            "RGB",
            "RGB",
            renderingIntent=0,
            flags=0,
        )
        image = Image.fromarray(patches.reshape(1, -1, 3), "RGB")
        return np.asarray(ImageCms.applyTransform(image, transform)).reshape(-1, 3)
    except (OSError, ValueError, ImageCms.PyCMSError) as exc:
        raise GateFailure("LITTLECMS_PROFILE_REJECTED", str(exc)) from exc


def xyz_to_xy(xyz: Iterable[float]) -> list[float]:
    values = list(xyz)
    total = sum(values)
    if total <= 0:
        raise GateFailure("PROFILE_NUMERIC_INVALID", "XYZ has non-positive sum")
    return [values[0] / total, values[1] / total]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalized_html_text(data: bytes, label: str) -> str:
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateFailure("EXTERNAL_SOURCE_INVALID", f"{label}: not UTF-8") from exc
    parser = TextExtractor()
    parser.feed(decoded)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def run_git(repo: Path, args: list[str]) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise GateFailure("GIT_UNAVAILABLE", str(exc)) from exc
    if completed.returncode != 0:
        reason = completed.stderr.decode("utf-8", errors="replace")[-1000:]
        raise GateFailure("GIT_OBJECT_READ_FAILED", reason)
    return bytes(completed.stdout)


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def parse_tiff_from_bytes(
    data: bytes, label: str, tifffile_module: Any, np: Any
) -> dict[str, Any]:
    try:
        with tifffile_module.TiffFile(BytesIO(data)) as tif:
            if len(tif.pages) != 1:
                raise GateFailure(
                    "TIFF_STORAGE_MISMATCH", f"{label}: expected one TIFF page"
                )
            page = tif.pages[0]
            array = page.asarray()
            tags = {int(tag.code): tag.value for tag in page.tags.values()}
            icc_tag = page.tags.get(34675)
            icc = bytes(icc_tag.value) if icc_tag is not None else None
            compression = int(page.compression)
            photometric = int(page.photometric)
            planar = int(page.planarconfig)
            bitspersample = int(page.bitspersample)
            rows_per_strip = int(tags.get(278, page.imagelength))
            strip_ranges = []
            payload_hash = hashlib.sha256()
            for offset, byte_count in zip(
                page.dataoffsets, page.databytecounts, strict=True
            ):
                end = int(offset) + int(byte_count)
                if int(offset) < 0 or end > len(data):
                    raise GateFailure(
                        "TIFF_STORAGE_MISMATCH",
                        f"{label}: strip [{offset},{end}) exceeds {len(data)} bytes",
                    )
                payload_hash.update(data[int(offset) : end])
                strip_ranges.append(
                    {
                        "start": int(offset),
                        "end": end,
                        "bytes": int(byte_count),
                    }
                )
            icc_range = None
            if icc_tag is not None:
                icc_start = int(icc_tag.valueoffset)
                icc_end = icc_start + int(icc_tag.valuebytecount)
                if icc_start < 0 or icc_end > len(data):
                    raise GateFailure(
                        "TIFF_STORAGE_MISMATCH",
                        f"{label}: ICC [{icc_start},{icc_end}) exceeds {len(data)} bytes",
                    )
                icc_range = {
                    "start": icc_start,
                    "end": icc_end,
                    "bytes": int(icc_tag.valuebytecount),
                    "sha256": sha256(data[icc_start:icc_end]),
                }
    except GateFailure:
        raise
    except (OSError, ValueError, TypeError, struct.error) as exc:
        raise GateFailure("TIFF_MALFORMED", f"{label}: {exc}") from exc
    decoded_pixel_sha256 = sha256(np.ascontiguousarray(array).tobytes())
    return {
        "hash_algorithm": "SHA-256",
        "file_range": {
            "start": 0,
            "end": len(data),
            "bytes": len(data),
            "sha256": sha256(data),
        },
        "file_bytes": len(data),
        "file_sha256": sha256(data),
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "pixel_sha256": decoded_pixel_sha256,
        "decoded_pixel_sha256": decoded_pixel_sha256,
        "pixel_payload_ranges": strip_ranges,
        "pixel_payload_sha256": payload_hash.hexdigest(),
        "compression": compression,
        "photometric": photometric,
        "planar_configuration": planar,
        "bits_per_sample": bitspersample,
        "rows_per_strip": rows_per_strip,
        "icc": icc,
        "icc_sha256": sha256(icc) if icc is not None else None,
        "icc_range": icc_range,
        "tag_codes": sorted(tags),
    }


def profile_patch_witnesses(
    profile: bytes,
    expectations: dict[str, Any],
    Image: Any,
    ImageCms: Any,
    colour: Any,
    np: Any,
) -> dict[str, Any]:
    patches = np.asarray(expectations["patches_rgb8"], dtype=np.uint8)
    if patches.ndim != 2 or patches.shape[1] != 3:
        raise GateFailure("REFERENCE_INVALID", "patches_rgb8 must be Nx3")
    try:
        source_profile = ImageCms.ImageCmsProfile(BytesIO(profile))
        srgb_profile = ImageCms.createProfile("sRGB")
        transform = ImageCms.buildTransformFromOpenProfiles(
            source_profile, srgb_profile, "RGB", "RGB", renderingIntent=0, flags=0
        )
        image = Image.fromarray(patches.reshape(1, -1, 3), "RGB")
        lcms = np.asarray(ImageCms.applyTransform(image, transform)).reshape(-1, 3)
    except (OSError, ValueError, ImageCms.PyCMSError) as exc:
        raise GateFailure("LITTLECMS_PROFILE_REJECTED", str(exc)) from exc

    prophoto = colour.RGB_COLOURSPACES["ProPhoto RGB"]
    srgb = colour.RGB_COLOURSPACES["sRGB"]
    normalized = patches.astype(np.float64) / 255.0
    linear_result = colour.RGB_to_RGB(
        normalized,
        prophoto,
        srgb,
        chromatic_adaptation_transform="Bradford",
        apply_cctf_decoding=False,
        apply_cctf_encoding=True,
    )
    nonlinear_result = colour.RGB_to_RGB(
        normalized,
        prophoto,
        srgb,
        chromatic_adaptation_transform="Bradford",
        apply_cctf_decoding=True,
        apply_cctf_encoding=True,
    )
    linear_codes = np.rint(np.clip(linear_result, 0.0, 1.0) * 255.0).astype(np.uint8)
    nonlinear_codes = np.rint(np.clip(nonlinear_result, 0.0, 1.0) * 255.0).astype(
        np.uint8
    )
    differences = np.abs(lcms.astype(np.int16) - linear_codes.astype(np.int16))
    alternative_differences = np.abs(
        lcms.astype(np.int16) - nonlinear_codes.astype(np.int16)
    )
    return {
        "input_rgb8": patches.tolist(),
        "littlecms_linear_profile_to_srgb8": lcms.tolist(),
        "colour_linear_prophoto_to_srgb8": linear_codes.tolist(),
        "colour_standard_romm_to_srgb8": nonlinear_codes.tolist(),
        "maximum_lcms_colour_code_difference": int(differences.max()),
        "nonlinear_alternative_differences": alternative_differences.tolist(),
    }


def run_fork_matrix(
    ledger: Ledger,
    reader: ReadOnce,
    run_label: str,
    fork_executable: Path,
    output_root: Path,
    linear_input_path: Path,
    gamma18_input_path: Path,
    shifted_input_path: Path,
    linear_input: dict[str, Any],
    gamma18_input: dict[str, Any],
    shifted_input: dict[str, Any],
    tifffile_module: Any,
    np: Any,
) -> dict[str, Any]:
    flags = ["auto", "srgb", "linear-srgb", "linear-rec2020", "none"]
    cases = [
        (profile_id, input_path, input_colorspace)
        for profile_id, input_path in (
            ("gamma1", linear_input_path),
            ("gamma18", gamma18_input_path),
        )
        for input_colorspace in flags
    ]
    cases.append(("pixel-shift", shifted_input_path, "auto"))
    results: list[dict[str, Any]] = []
    for profile_id, input_path, input_colorspace in cases:
        case_id = f"{profile_id}-{input_colorspace}"
        output_path = output_root / "fork-runs" / run_label / f"{case_id}.tiff"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.unlink(missing_ok=True)
        command = [
            str(fork_executable),
            f"--output={output_path}",
            "--threads=1",
            "--batchsize=2",
            "--no-opencl",
            "--no-align",
            "--no-whitebalance",
            "--no-contrast",
            "--consistency=0",
            "--denoise=0",
            f"--input-colorspace={input_colorspace}",
            "--output-colorspace=srgb",
            "--output-bitdepth=16",
            str(input_path),
            str(input_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                cwd=output_path.parent,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise GateFailure(
                "FORK_EXECUTION_TIMEOUT", f"{case_id}: process did not complete"
            ) from exc
        except OSError as exc:
            raise GateFailure(
                "FORK_EXECUTION_FAILED", f"{case_id}: {exc}"
            ) from exc
        if completed.returncode != 0 or not output_path.is_file():
            raise GateFailure(
                "FORK_EXECUTION_FAILED",
                f"{case_id}: exit {completed.returncode}; "
                f"{completed.stderr[-1000:]}",
            )
        output_data = reader.read(f"fork-output-{run_label}-{case_id}", output_path)
        parsed = parse_tiff_from_bytes(
            output_data,
            f"fork output {case_id}",
            tifffile_module,
            np,
        )
        results.append(
            {
                "case_id": case_id,
                "input_profile": profile_id,
                "input_colorspace": input_colorspace,
                "exit_code": completed.returncode,
                "input_path_occurrences": command.count(str(input_path)),
                "output": stable_tiff_summary(parsed),
            }
        )

    profile_results = [
        record
        for record in results
        if record["input_profile"] in {"gamma1", "gamma18"}
    ]
    shifted_results = [
        record for record in results if record["input_profile"] == "pixel-shift"
    ]
    profile_payloads = {
        record["output"]["decoded_pixel_sha256"] for record in profile_results
    }
    shifted_payloads = {
        record["output"]["decoded_pixel_sha256"] for record in shifted_results
    }
    icc_values = {record["output"]["icc_sha256"] for record in results}
    shapes = {tuple(record["output"]["shape"]) for record in results}
    dtypes = {record["output"]["dtype"] for record in results}
    input_pixels_equal = (
        linear_input["decoded_pixel_sha256"]
        == gamma18_input["decoded_pixel_sha256"]
    )
    input_profiles_differ = (
        linear_input["icc_sha256"] != gamma18_input["icc_sha256"]
        and linear_input["icc_sha256"] is not None
        and gamma18_input["icc_sha256"] is not None
    )
    profile_inert = (
        len(profile_results) == 10
        and profile_payloads == {linear_input["decoded_pixel_sha256"]}
        and icc_values == {None}
        and len(shapes) == 1
        and dtypes == {"uint16"}
        and input_pixels_equal
        and input_profiles_differ
        and all(record["input_path_occurrences"] == 2 for record in results)
    )
    null_moves = (
        len(shifted_results) == 1
        and shifted_input["decoded_pixel_sha256"]
        != linear_input["decoded_pixel_sha256"]
        and shifted_payloads == {shifted_input["decoded_pixel_sha256"]}
        and shifted_payloads != profile_payloads
    )
    summary = {
        "run_count": len(results),
        "profile_invariance_run_count": len(profile_results),
        "movable_null_run_count": len(shifted_results),
        "input_colorspaces": flags,
        "input_pixels_equal": input_pixels_equal,
        "input_profiles_differ": input_profiles_differ,
        "profile_invariance_output_decoded_pixel_hashes": sorted(profile_payloads),
        "shifted_input_decoded_pixel_sha256": shifted_input[
            "decoded_pixel_sha256"
        ],
        "shifted_output_decoded_pixel_hashes": sorted(shifted_payloads),
        "output_icc_hashes": sorted(
            value if value is not None else "ABSENT" for value in icc_values
        ),
        "output_shapes": [list(value) for value in sorted(shapes)],
        "output_dtypes": sorted(dtypes),
        "runs": results,
    }
    ledger.require(
        "FORK_RUNTIME_UINT16_ICC_INERT",
        "CONSUMER_FORK_RUNTIME",
        profile_inert,
        "FORK_RUNTIME_SEMANTICS_MISMATCH",
        "frozen fork uint16 outputs are ICC/profile/flag-inert and omit ICC",
        summary,
    )
    ledger.require(
        "FORK_RUNTIME_PIXEL_NULL_MOVES",
        "CONSUMER_FORK_RUNTIME",
        null_moves,
        "FORK_RUNTIME_NULL_FROZEN",
        "fork output changes when the uint16 pixel payload changes",
        {
            "baseline_input": linear_input["decoded_pixel_sha256"],
            "baseline_outputs": sorted(profile_payloads),
            "shifted_input": shifted_input["decoded_pixel_sha256"],
            "shifted_outputs": sorted(shifted_payloads),
        },
    )
    return summary


@dataclass
class Inputs:
    reference: Path
    witnesses: Path
    output: Path
    run_label: str
    libraw_source: Path
    libraw_colorconst: Path
    romm_registry: Path
    zerene_doc: Path
    tiff: Path
    tiff_origin: str
    fork_input_linear: Path
    fork_input_gamma18: Path
    fork_input_shifted: Path
    out_root: Path


def execute(inputs: Inputs, ledger: Ledger, reader: ReadOnce) -> dict[str, Any]:
    reference_data = reader.read("reference", inputs.reference)
    witness_data = reader.read("witnesses", inputs.witnesses)
    reference = parse_json_bytes(reference_data, "reference")
    witnesses = parse_json_bytes(witness_data, "witnesses")
    ledger.require(
        "REFERENCE_SCHEMAS",
        "ARTIFACT_IDENTITY",
        reference.get("schema") == REFERENCE_SCHEMA
        and witnesses.get("schema") == WITNESS_SCHEMA,
        "REFERENCE_SCHEMA_MISMATCH",
        "reference and witness schemas are pinned",
        {
            "reference": reference.get("schema"),
            "witnesses": witnesses.get("schema"),
        },
    )

    artifacts: dict[str, bytes] = {}
    for artifact_id, expected in reference["artifacts"].items():
        data = reader.read(artifact_id, resolve_strehl(expected["path"]))
        check_file_bytes(
            ledger,
            f"ARTIFACT_{artifact_id.upper()}",
            artifact_id,
            data,
            expected,
        )
        artifacts[artifact_id] = data
    fork_lock_adapter = module_from_bytes(
        "m165_prophoto_locked_fork_adapter",
        artifacts["fork_consumer_adapter"],
        resolve_strehl(reference["artifacts"]["fork_consumer_adapter"]["path"]),
    )
    if not all(
        hasattr(fork_lock_adapter, name)
        for name in ("locked_input", "file_information", "ConsumerFailure")
    ):
        raise GateFailure(
            "LOCK_ADAPTER_LOAD_FAILED",
            "fork adapter does not expose the frozen locked-input API",
        )

    settings = parse_json_bytes(artifacts["settings"], "settings")
    ledger.require(
        "SETTINGS_DECLARATION",
        "PRODUCER_DECLARATION",
        settings.get("schema") == "m165-common-input-settings-v1"
        and settings.get("postprocess", {}).get("output_color") == "ProPhoto"
        and settings.get("postprocess", {}).get("output_bps") == 16
        and settings.get("postprocess", {}).get("gamma") == [1.0, 1.0]
        and settings.get("output", {}).get("color_space")
        == "linear ProPhoto RGB D50",
        "SETTINGS_DECLARATION_MISMATCH",
        "settings declare 16-bit linear ProPhoto RGB D50",
        settings.get("postprocess"),
    )

    anchor_observations: dict[str, Any] = {}
    for artifact_id in ("converter", "strehl_common_tiff", "strehl_cli"):
        try:
            text = artifacts[artifact_id].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GateFailure(
                "SOURCE_DECODE_FAILED", f"{artifact_id}: not UTF-8"
            ) from exc
        anchor_observations[artifact_id] = verify_anchor_groups(
            ledger,
            f"SOURCE_ANCHORS_{artifact_id.upper()}",
            "SOURCE_ANCHORS",
            text,
            reference["source_anchors"][artifact_id],
        )

    source_pin = parse_json_bytes(artifacts["source_pin"], "source pin")
    fork_source = reference["fork_source"]
    source_entries = {
        entry.get("path"): entry
        for entry in source_pin.get("source_subtree", {}).get("files", [])
        if isinstance(entry, dict)
    }
    pin_matches = (
        source_pin.get("schema") == "m165-fork-source-pin-v1"
        and source_pin.get("commit", {}).get("resolved") == fork_source["commit"]
    )
    for blob in fork_source["blobs"]:
        entry = source_entries.get(blob["path"])
        pin_matches = pin_matches and entry is not None and all(
            entry.get(key) == blob[key]
            for key in ("bytes", "git_blob_sha1", "sha256")
        )
    ledger.require(
        "FORK_SOURCE_PIN_CONTENTS",
        "SOURCE_ANCHORS",
        pin_matches,
        "FORK_SOURCE_PIN_MISMATCH",
        "source pin names the exact commit and relevant blobs",
    )

    repo = Path(fork_source["repository"])
    resolved_commit = run_git(
        repo, ["rev-parse", f"{fork_source['commit']}^{{commit}}"]
    ).decode("ascii").strip()
    ledger.require(
        "FORK_COMMIT_AVAILABLE",
        "SOURCE_ANCHORS",
        resolved_commit == fork_source["commit"],
        "FORK_COMMIT_MISMATCH",
        "pinned fork commit is available",
        {"resolved": resolved_commit, "expected": fork_source["commit"]},
    )
    git_object_records: list[dict[str, Any]] = []
    for blob in fork_source["blobs"]:
        blob_data = run_git(repo, ["cat-file", "blob", blob["git_blob_sha1"]])
        actual = {
            "bytes": len(blob_data),
            "git_blob_sha1": git_blob_sha1(blob_data),
            "sha256": sha256(blob_data),
        }
        expected = {
            key: blob[key] for key in ("bytes", "git_blob_sha1", "sha256")
        }
        ledger.require(
            f"FORK_BLOB_{Path(blob['path']).stem.upper()}",
            "SOURCE_ANCHORS",
            actual == expected,
            "FORK_BLOB_IDENTITY_MISMATCH",
            f"{blob['path']} blob identity",
            {"actual": actual, "expected": expected},
        )
        try:
            blob_text = blob_data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GateFailure(
                "SOURCE_DECODE_FAILED", f"{blob['path']}: not UTF-8"
            ) from exc
        anchors = verify_anchor_groups(
            ledger,
            f"FORK_ANCHORS_{Path(blob['path']).stem.upper()}",
            "SOURCE_ANCHORS",
            blob_text,
            blob["anchors"],
        )
        git_object_records.append(
            {
                "path": blob["path"],
                "read_count": 1,
                **actual,
                "anchors": anchors,
            }
        )

    local_witness_data: dict[str, bytes] = {}
    libraw_expected = reference["local_witnesses"]["libraw"]
    for item_id, expected in libraw_expected.items():
        data = reader.read(f"libraw-{item_id}", Path(expected["path"]))
        check_file_bytes(
            ledger,
            f"LIBRAW_{item_id.upper()}",
            f"LibRaw {item_id}",
            data,
            expected,
        )
        local_witness_data[f"libraw-{item_id}"] = data
    opencv_expected = reference["local_witnesses"]["opencv_tiff_source"]
    opencv_data = reader.read("opencv-tiff-source", Path(opencv_expected["path"]))
    check_file_bytes(
        ledger,
        "OPENCV_TIFF_SOURCE_IDENTITY",
        "OpenCV TIFF source",
        opencv_data,
        opencv_expected,
    )
    try:
        opencv_text = opencv_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateFailure("SOURCE_DECODE_FAILED", "OpenCV TIFF source") from exc
    forbidden_counts = {
        anchor: opencv_text.count(anchor)
        for anchor in opencv_expected["forbidden_anchors"]
    }
    ledger.require(
        "OPENCV_TIFF_NO_ICC_HANDLING",
        "CONSUMER_FORK_SOURCE",
        all(count == 0 for count in forbidden_counts.values()),
        "OPENCV_ICC_HANDLING_DRIFT",
        "pinned OpenCV TIFF codec source has no ICC profile handling anchor",
        forbidden_counts,
    )

    external_paths = {
        "libraw_postprocessing": inputs.libraw_source,
        "libraw_colorconst": inputs.libraw_colorconst,
        "romm_registry": inputs.romm_registry,
        "zerene_color_management": inputs.zerene_doc,
    }
    external_data: dict[str, bytes] = {}
    external_text: dict[str, str] = {}
    for source_id, path in external_paths.items():
        expected = reference["external_sources"][source_id]
        data = reader.read(source_id, path)
        if "sha256" in expected and "bytes" in expected:
            check_file_bytes(
                ledger,
                f"EXTERNAL_{source_id.upper()}",
                source_id,
                data,
                expected,
            )
        else:
            ledger.require(
                f"EXTERNAL_{source_id.upper()}",
                "EXTERNAL_REFERENCES",
                bool(data) and expected.get("identity_mode")
                == "live-content-anchor-gated",
                "EXTERNAL_SOURCE_INVALID",
                f"{source_id} live source is non-empty and anchor-gated",
                {
                    "identity_mode": expected.get("identity_mode"),
                    "non_empty": bool(data),
                },
            )
        external_data[source_id] = data
        if source_id.startswith("libraw_"):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise GateFailure(
                    "EXTERNAL_SOURCE_INVALID", f"{source_id}: not UTF-8"
                ) from exc
        else:
            text = normalized_html_text(data, source_id)
        external_text[source_id] = text
        counts = {
            anchor: text.count(anchor) for anchor in expected["text_anchors"]
        }
        anchors_valid = (
            all(count == 1 for count in counts.values())
            if source_id.startswith("libraw_")
            else all(count >= 1 for count in counts.values())
        )
        ledger.require(
            f"EXTERNAL_ANCHORS_{source_id.upper()}",
            "EXTERNAL_REFERENCES",
            anchors_valid,
            "EXTERNAL_SOURCE_ANCHOR_DRIFT",
            (
                f"{source_id} exact source anchors are unique"
                if source_id.startswith("libraw_")
                else f"{source_id} semantic anchors are present"
            ),
            counts,
        )
    zerene_forbidden = {
        anchor: external_text["zerene_color_management"].count(anchor)
        for anchor in reference["external_sources"]["zerene_color_management"][
            "forbidden_internal_pipeline_anchors"
        ]
    }
    ledger.require(
        "ZERENE_INTERNAL_PIPELINE_NOT_DOCUMENTED",
        "CONSUMER_ZERENE",
        all(count == 0 for count in zerene_forbidden.values()),
        "ZERENE_CLASSIFICATION_DRIFT",
        "vendor color-management page contains no PMax or DMap pipeline statement",
        zerene_forbidden,
    )

    try:
        import cv2
        import colour
        import numpy as np
        import PIL
        from PIL import Image, ImageCms, _imagingcms
        import rawpy
        from rawpy import _rawpy
        import tifffile
    except ImportError as exc:
        raise GateFailure("RUNTIME_IMPORT_FAILED", str(exc)) from exc

    runtime = reference["runtime"]
    python_data = reader.read("python-executable", Path(sys.executable))
    ledger.require(
        "RUNTIME_PYTHON",
        "RUNTIME_IDENTITY",
        ".".join(str(value) for value in sys.version_info[:3])
        == runtime["python"]["version"]
        and len(python_data) == runtime["python"]["executable_bytes"]
        and sha256(python_data) == runtime["python"]["executable_sha256"],
        "PYTHON_RUNTIME_DRIFT",
        "Python executable version and hash are pinned",
        {
            "version": ".".join(str(value) for value in sys.version_info[:3]),
            "bytes": len(python_data),
            "sha256": sha256(python_data),
        },
    )
    imagingcms_data = reader.read("pillow-imagingcms", Path(_imagingcms.__file__))
    ledger.require(
        "RUNTIME_PILLOW_LCMS",
        "RUNTIME_IDENTITY",
        PIL.__version__ == runtime["pillow"]["version"]
        and ImageCms.core.littlecms_version
        == runtime["pillow"]["littlecms_version"]
        and len(imagingcms_data) == runtime["pillow"]["imagingcms_bytes"]
        and sha256(imagingcms_data)
        == runtime["pillow"]["imagingcms_sha256"],
        "PILLOW_LCMS_RUNTIME_DRIFT",
        "Pillow and LittleCMS versions and extension hash are pinned",
        {
            "pillow": PIL.__version__,
            "littlecms": ImageCms.core.littlecms_version,
            "bytes": len(imagingcms_data),
            "sha256": sha256(imagingcms_data),
        },
    )
    colour_root = Path(colour.__file__).resolve().parent
    colour_sources: dict[str, Any] = {}
    colour_valid = colour.__version__ == runtime["colour_science"]["version"]
    for source_id in ("dataset_source", "transfer_source"):
        expected = runtime["colour_science"][source_id]
        data = reader.read(
            f"colour-{source_id}", colour_root / expected["relative_path"]
        )
        actual = {"bytes": len(data), "sha256": sha256(data)}
        colour_sources[source_id] = actual
        colour_valid = colour_valid and actual == {
            "bytes": expected["bytes"],
            "sha256": expected["sha256"],
        }
    ledger.require(
        "RUNTIME_COLOUR_SCIENCE",
        "RUNTIME_IDENTITY",
        colour_valid,
        "COLOUR_SCIENCE_RUNTIME_DRIFT",
        "colour-science version and ProPhoto sources are pinned",
        {"version": colour.__version__, "sources": colour_sources},
    )
    rawpy_data = reader.read("rawpy-extension", Path(_rawpy.__file__))
    params_output_color = int(
        rawpy.Params(
            output_color=rawpy.ColorSpace.ProPhoto,
            output_bps=16,
            gamma=(1.0, 1.0),
        ).output_color
    )
    ledger.require(
        "RUNTIME_RAWPY_LIBRAW",
        "RUNTIME_IDENTITY",
        rawpy.__version__ == runtime["rawpy"]["version"]
        and list(rawpy.libraw_version) == runtime["rawpy"]["libraw_version"]
        and params_output_color == runtime["rawpy"]["params_output_color"]
        and len(rawpy_data) == runtime["rawpy"]["extension_bytes"]
        and sha256(rawpy_data) == runtime["rawpy"]["extension_sha256"],
        "RAWPY_LIBRAW_RUNTIME_DRIFT",
        "rawpy/LibRaw version, enum mapping, and extension hash are pinned",
        {
            "rawpy": rawpy.__version__,
            "libraw": list(rawpy.libraw_version),
            "params_output_color": params_output_color,
            "bytes": len(rawpy_data),
            "sha256": sha256(rawpy_data),
        },
    )
    ledger.require(
        "RUNTIME_NUMERIC_TIFF",
        "RUNTIME_IDENTITY",
        np.__version__ == runtime["numpy_version"]
        and tifffile.__version__ == runtime["tifffile_version"]
        and cv2.__version__ == runtime["cv2_version"],
        "NUMERIC_TIFF_RUNTIME_DRIFT",
        "NumPy, tifffile, and cv2 versions are pinned",
        {
            "numpy": np.__version__,
            "tifffile": tifffile.__version__,
            "cv2": cv2.__version__,
        },
    )

    profile_expectations = reference["profile_expectations"]
    m165_profile = parse_icc(artifacts["linear_profile"], "M165 profile")
    structural_profile = (
        m165_profile["version"] == profile_expectations["version"]
        and m165_profile["class"] == profile_expectations["class"]
        and m165_profile["color_space"] == profile_expectations["color_space"]
        and m165_profile["pcs"] == profile_expectations["pcs"]
        and m165_profile["description"] == profile_expectations["description"]
    )
    ledger.require(
        "PROFILE_ICC_STRUCTURE",
        "PROFILE_DECLARATION",
        structural_profile,
        "PROFILE_ICC_STRUCTURE_MISMATCH",
        "M165 profile is ICC v2.1 monitor RGB-to-XYZ with frozen description",
        m165_profile,
    )
    transfer_gamma = profile_expectations["transfer_gamma"]
    gamma_valid = all(
        abs(value - transfer_gamma) <= 1e-12
        for value in m165_profile["gamma"].values()
    )
    ledger.require(
        "PROFILE_LINEAR_TRC",
        "PROFILE_DECLARATION",
        gamma_valid,
        "PROFILE_TRC_MISMATCH",
        "M165 profile has gamma-1 TRCs",
        m165_profile["gamma"],
    )
    xyz_tolerance = reference["tolerances"]["icc_fixed_xyz"]
    xyz_differences = {
        tag: max_abs_difference(
            m165_profile["matrix_xyz"][tag],
            profile_expectations["matrix_xyz"][tag],
        )
        for tag in ("rXYZ", "gXYZ", "bXYZ", "wtpt")
    }
    illuminant_difference = max_abs_difference(
        m165_profile["header_illuminant_xyz"],
        profile_expectations["header_illuminant_xyz"],
    )
    ledger.require(
        "PROFILE_XYZ_NUMERICS",
        "PROFILE_NUMERIC",
        max([*xyz_differences.values(), illuminant_difference]) <= xyz_tolerance,
        "PROFILE_XYZ_NUMERIC_MISMATCH",
        "M165 profile colorants, whitepoint, and header illuminant match reference",
        {
            "tag_max_abs_differences": xyz_differences,
            "header_illuminant_max_abs_difference": illuminant_difference,
            "tolerance": xyz_tolerance,
        },
    )

    try:
        lcms_profile = ImageCms.ImageCmsProfile(BytesIO(artifacts["linear_profile"]))
        core_profile = lcms_profile.profile
        lcms_profile_data = {
            "description": core_profile.profile_description,
            "version": core_profile.version,
            "class": core_profile.device_class,
            "color_space": core_profile.xcolor_space,
            "pcs": core_profile.connection_space,
            "whitepoint_xyz": list(core_profile.media_white_point[0]),
            "whitepoint_xy": list(core_profile.media_white_point[1][:2]),
            "primaries_xy": [
                list(core_profile.red_primary[1][:2]),
                list(core_profile.green_primary[1][:2]),
                list(core_profile.blue_primary[1][:2]),
            ],
        }
    except (OSError, ValueError, ImageCms.PyCMSError) as exc:
        raise GateFailure("LITTLECMS_PROFILE_REJECTED", str(exc)) from exc
    expected_colour = profile_expectations["colour_science"]
    lcms_meta_valid = (
        lcms_profile_data["description"] == profile_expectations["description"]
        and lcms_profile_data["version"] == profile_expectations["version"]
        and lcms_profile_data["class"] == profile_expectations["class"]
        and lcms_profile_data["color_space"] == profile_expectations["color_space"]
        and lcms_profile_data["pcs"] == profile_expectations["pcs"]
        and max_abs_difference(
            lcms_profile_data["whitepoint_xy"],
            expected_colour["whitepoint_xy"],
        )
        <= reference["tolerances"]["whitepoint_xy"]
        and max(
            max_abs_difference(actual, expected)
            for actual, expected in zip(
                lcms_profile_data["primaries_xy"],
                expected_colour["primaries_xy"],
                strict=True,
            )
        )
        <= reference["tolerances"]["primary_xy"]
    )
    ledger.require(
        "PROFILE_LITTLECMS_METADATA",
        "PROFILE_NUMERIC",
        lcms_meta_valid,
        "PROFILE_LITTLECMS_METADATA_MISMATCH",
        "LittleCMS independently parses D50 ProPhoto primaries and profile class",
        lcms_profile_data,
    )

    colour_space = colour.RGB_COLOURSPACES["ProPhoto RGB"]
    colour_data = {
        "name": colour_space.name,
        "primaries_xy": np.asarray(colour_space.primaries).tolist(),
        "whitepoint_xy": np.asarray(colour_space.whitepoint).tolist(),
        "encoding_function": colour_space.cctf_encoding.__name__,
        "decoding_function": colour_space.cctf_decoding.__name__,
    }
    colour_valid = (
        colour_data["name"] == expected_colour["name"]
        and max(
            max_abs_difference(actual, expected)
            for actual, expected in zip(
                colour_data["primaries_xy"],
                expected_colour["primaries_xy"],
                strict=True,
            )
        )
        <= 1e-12
        and max_abs_difference(
            colour_data["whitepoint_xy"], expected_colour["whitepoint_xy"]
        )
        <= 1e-12
        and "ROMMRGB" in colour_data["encoding_function"]
        and "ROMMRGB" in colour_data["decoding_function"]
    )
    ledger.require(
        "PROFILE_COLOUR_SCIENCE_DATASET",
        "PROFILE_NUMERIC",
        colour_valid,
        "PROFILE_COLOUR_SCIENCE_DATASET_MISMATCH",
        "colour-science identifies ProPhoto as standard nonlinear ROMM RGB",
        colour_data,
    )

    midpoint_code = 32768.0 / 65535.0
    midpoint_if_srgb = float(
        colour.cctf_decoding(midpoint_code, function="sRGB")
    )
    midpoint_semantic_difference = midpoint_code - midpoint_if_srgb
    ledger.require(
        "FORK_UINT16_MIDPOINT_SEMANTIC_DIVERGENCE",
        "CONSUMER_FORK_SOURCE",
        midpoint_semantic_difference
        >= reference["tolerances"]["fork_midpoint_minimum_linear_difference"],
        "FORK_UINT16_SEMANTIC_DIFFERENCE_TOO_SMALL",
        "the fork's sRGB-OETF assumption gives a different linear meaning to uint16 midpoint",
        {
            "uint16_code": 32768,
            "m165_linear_normalized": midpoint_code,
            "fork_srgb_decoded_linear": midpoint_if_srgb,
            "linear_difference": midpoint_semantic_difference,
            "minimum": reference["tolerances"][
                "fork_midpoint_minimum_linear_difference"
            ],
        },
    )

    patch_witness = profile_patch_witnesses(
        artifacts["linear_profile"],
        profile_expectations,
        Image,
        ImageCms,
        colour,
        np,
    )
    ledger.require(
        "PROFILE_PATCH_LCMS_COLOUR_AGREEMENT",
        "PROFILE_NUMERIC",
        patch_witness["maximum_lcms_colour_code_difference"]
        <= reference["tolerances"]["lcms_colour_patch_codes"],
        "PROFILE_PATCH_WITNESS_MISMATCH",
        "LittleCMS and colour-science linear-ProPhoto transforms agree",
        {
            "maximum_code_difference": patch_witness[
                "maximum_lcms_colour_code_difference"
            ],
            "tolerance": reference["tolerances"]["lcms_colour_patch_codes"],
        },
    )
    patch_inputs = patch_witness["input_rgb8"]
    neutral_index = patch_inputs.index([128, 128, 128])
    actual_linear_neutral = patch_witness[
        "littlecms_linear_profile_to_srgb8"
    ][neutral_index][0]
    actual_colour_linear_neutral = patch_witness[
        "colour_linear_prophoto_to_srgb8"
    ][neutral_index][0]
    expected_linear_neutral = profile_expectations["linear_neutral_128_srgb8"]
    ledger.add(
        "PROFILE_NUMERIC_NEUTRAL",
        "PROFILE_NUMERIC",
        actual_linear_neutral == expected_linear_neutral
        and actual_colour_linear_neutral == expected_linear_neutral,
        "PROFILE_NUMERIC_NEUTRAL_MISMATCH",
        "linearized ProPhoto neutral 128 maps to the pinned sRGB code",
        {
            "littlecms": actual_linear_neutral,
            "colour_science": actual_colour_linear_neutral,
            "expected": expected_linear_neutral,
        },
    )
    nonlinear_neutral = patch_witness["colour_standard_romm_to_srgb8"][
        neutral_index
    ][0]
    minimum_separation = profile_expectations[
        "standard_romm_minimum_neutral_separation_codes"
    ]
    alternative_valid = (
        nonlinear_neutral == profile_expectations["nonlinear_neutral_128_srgb8"]
        and actual_linear_neutral - nonlinear_neutral >= minimum_separation
        and sum(
            max(row) >= minimum_separation
            for row in patch_witness["nonlinear_alternative_differences"]
        )
        >= 4
    )
    ledger.require(
        "PROFILE_LINEAR_VS_STANDARD_ROMM_SEPARATION",
        "PROFILE_NUMERIC",
        alternative_valid,
        "PROFILE_NONLINEAR_ALTERNATIVE_NOT_REJECTED",
        "multiple neutral/colored patches reject standard nonlinear ROMM semantics",
        {
            "linear_neutral": actual_linear_neutral,
            "standard_romm_neutral": nonlinear_neutral,
            "minimum_neutral_separation": minimum_separation,
            "patches": patch_witness,
        },
    )

    generated_spec = witnesses["libraw_generated_profile"]
    generated_provenance = generated_spec.get("provenance", {})
    try:
        generated_profile_bytes = base64.b64decode(
            generated_spec["base64"], validate=True
        )
    except (ValueError, TypeError) as exc:
        raise GateFailure("WITNESS_BASE64_INVALID", str(exc)) from exc
    generated_identity_valid = (
        len(generated_profile_bytes) == generated_spec["bytes"]
        and sha256(generated_profile_bytes) == generated_spec["sha256"]
        and generated_provenance.get("dcraw_emu_sha256")
        == libraw_expected["dcraw_emu"]["sha256"]
        and generated_provenance.get("libraw_sha256")
        == libraw_expected["library"]["sha256"]
        and generated_provenance.get("output_tiff_bytes") == 197685456
        and generated_provenance.get("output_tiff_sha256")
        == "6ba60c78bcca542ecd5996bb25b7460b5e5b4cbaca32394af1447c91342f1133"
        and generated_provenance.get("source_sha256")
        == "1b9ad0bac914f017aee35dc36ccec9a69d3f8c8284c604ff9bce0cc9bcd2d38a"
        and generated_provenance.get("invocation")
        == [
            "dcraw_emu.exe",
            "-w",
            "-q",
            "3",
            "-o",
            "4",
            "-6",
            "-W",
            "-g",
            "1",
            "1",
            "-T",
            "-t",
            "0",
        ]
    )
    ledger.require(
        "LIBRAW_GENERATED_PROFILE_IDENTITY",
        "PRODUCER_SEMANTICS",
        generated_identity_valid,
        "LIBRAW_PROFILE_WITNESS_IDENTITY_MISMATCH",
        "embedded LibRaw generated-profile witness decodes to pinned bytes",
        {
            "bytes": len(generated_profile_bytes),
            "sha256": sha256(generated_profile_bytes),
            "provenance": generated_provenance,
        },
    )
    generated_profile = parse_icc(
        generated_profile_bytes, "LibRaw generated profile witness"
    )
    generated_numeric_differences = {
        tag: max_abs_difference(
            generated_profile["matrix_xyz"][tag],
            generated_spec["matrix_xyz"][tag],
        )
        for tag in ("rXYZ", "gXYZ", "bXYZ", "wtpt")
    }
    generated_profile_valid = (
        generated_profile["description"] == generated_spec["description"]
        and max(generated_numeric_differences.values()) <= 1e-12
        and all(abs(value - 1.0) <= 1e-12 for value in generated_profile["gamma"].values())
    )
    ledger.require(
        "LIBRAW_GENERATED_PROFILE_PARSE",
        "PRODUCER_SEMANTICS",
        generated_profile_valid,
        "LIBRAW_PROFILE_WITNESS_PARSE_MISMATCH",
        "LibRaw witness independently parses as ProPhoto D65 gamma 1",
        {
            "profile": generated_profile,
            "numeric_differences": generated_numeric_differences,
        },
    )
    libraw_source_counts = {
        anchor: external_text["libraw_postprocessing"].count(anchor)
        for anchor in reference["external_sources"]["libraw_postprocessing"][
            "text_anchors"
        ]
    }
    source_mapping_valid = (
        params_output_color == 4
        and all(count == 1 for count in libraw_source_counts.values())
    )
    ledger.require(
        "LIBRAW_OUTPUT_COLOR_4_MAPPING",
        "PRODUCER_SEMANTICS",
        source_mapping_valid,
        "LIBRAW_OUTPUT_COLOR_MAPPING_MISMATCH",
        "rawpy output_color 4 maps to LibRaw prophoto_rgb and its companion profile metadata",
        {
            "rawpy_params_output_color": params_output_color,
            "source_anchor_counts": libraw_source_counts,
        },
    )

    libraw_prophoto_matrix = np.asarray(
        parse_cpp_matrix(
            external_text["libraw_colorconst"],
            "prophoto_rgb",
        ),
        dtype=np.float64,
    )
    independent_bradford_matrix = np.asarray(
        colour.matrix_RGB_to_RGB(
            colour.RGB_COLOURSPACES["sRGB"],
            colour.RGB_COLOURSPACES["ProPhoto RGB"],
            "Bradford",
        ),
        dtype=np.float64,
    )
    independent_unadapted_matrix = np.asarray(
        colour.matrix_RGB_to_RGB(
            colour.RGB_COLOURSPACES["sRGB"],
            colour.RGB_COLOURSPACES["ProPhoto RGB"],
            None,
        ),
        dtype=np.float64,
    )
    adapted_matrix_difference = float(
        np.max(np.abs(libraw_prophoto_matrix - independent_bradford_matrix))
    )
    unadapted_matrix_difference = float(
        np.max(np.abs(libraw_prophoto_matrix - independent_unadapted_matrix))
    )
    matrix_semantics_valid = (
        adapted_matrix_difference
        <= reference["tolerances"]["libraw_matrix_to_bradford"]
        and unadapted_matrix_difference
        >= reference["tolerances"]["libraw_matrix_unadapted_minimum"]
    )
    ledger.require(
        "LIBRAW_PROPHOTO_MATRIX_D50_COMPATIBLE",
        "PRODUCER_SEMANTICS",
        matrix_semantics_valid,
        "LIBRAW_PROPHOTO_MATRIX_SEMANTICS_MISMATCH",
        "LibRaw prophoto_rgb matches an independent Bradford D50-adapted transform",
        {
            "libraw_prophoto_rgb": libraw_prophoto_matrix.tolist(),
            "independent_bradford_srgb_to_prophoto": (
                independent_bradford_matrix.tolist()
            ),
            "independent_unadapted_srgb_to_prophoto": (
                independent_unadapted_matrix.tolist()
            ),
            "maximum_abs_difference_to_bradford": adapted_matrix_difference,
            "maximum_abs_difference_to_unadapted": unadapted_matrix_difference,
            "tolerances": {
                "maximum_to_bradford": reference["tolerances"][
                    "libraw_matrix_to_bradford"
                ],
                "minimum_to_unadapted": reference["tolerances"][
                    "libraw_matrix_unadapted_minimum"
                ],
            },
        },
    )

    patch_array = np.asarray(profile_expectations["patches_rgb8"], dtype=np.uint8)
    generated_patch_codes = lcms_patch_codes(
        generated_profile_bytes,
        patch_array,
        Image,
        ImageCms,
        np,
    )
    m165_patch_codes = np.asarray(
        patch_witness["littlecms_linear_profile_to_srgb8"],
        dtype=np.uint8,
    )
    generated_patch_difference = int(
        np.max(
            np.abs(
                generated_patch_codes.astype(np.int16)
                - m165_patch_codes.astype(np.int16)
            )
        )
    )
    generated_profile_operationally_equivalent = (
        generated_patch_difference
        <= reference["tolerances"]["generated_profile_patch_codes"]
    )
    ledger.require(
        "LIBRAW_GENERATED_PROFILE_OPERATIONAL_EQUIVALENCE",
        "PRODUCER_SEMANTICS",
        generated_profile_operationally_equivalent,
        "LIBRAW_GENERATED_PROFILE_OPERATIONAL_MISMATCH",
        "LibRaw and M165 gamma-1 profiles transform frozen patches identically",
        {
            "maximum_code_difference": generated_patch_difference,
            "tolerance": reference["tolerances"][
                "generated_profile_patch_codes"
            ],
            "profile_bytes_identical": (
                generated_profile["sha256"] == m165_profile["sha256"]
            ),
        },
    )

    white_delta = [
        generated_profile["matrix_xyz"]["wtpt"][index]
        - m165_profile["matrix_xyz"]["wtpt"][index]
        for index in range(3)
    ]
    colorant_deltas = {
        tag: [
            generated_profile["matrix_xyz"][tag][index]
            - m165_profile["matrix_xyz"][tag][index]
            for index in range(3)
        ]
        for tag in ("rXYZ", "gXYZ", "bXYZ")
    }
    white_xy_delta = [
        xyz_to_xy(generated_profile["matrix_xyz"]["wtpt"])[index]
        - xyz_to_xy(m165_profile["matrix_xyz"]["wtpt"])[index]
        for index in range(2)
    ]
    producer_compatible = (
        source_mapping_valid
        and matrix_semantics_valid
        and generated_profile_operationally_equivalent
    )
    producer_semantics = {
        "claim_basis": witnesses["producer_claims"]["claim_basis"],
        "assumption_under_test": (
            "rawpy/LibRaw output-color 4 with gamma 1 emits linear "
            "D50-adapted ProPhoto samples operationally described by the "
            "embedded M165 profile"
        ),
        "embedded_profile_declaration": "PROVED",
        "libraw_pixel_to_embedded_profile_semantics": (
            "D50_COMPATIBLE_EXACT_PROFILE_BYTE_IDENTITY_NOT_CLAIMED"
            if producer_compatible
            else "NOT_PROVED"
        ),
        "m165_profile_sha256": m165_profile["sha256"],
        "libraw_generated_profile_sha256": generated_profile["sha256"],
        "generated_profile_bytes_identical": (
            generated_profile["sha256"] == m165_profile["sha256"]
        ),
        "generated_profile_patch_maximum_code_difference": (
            generated_patch_difference
        ),
        "libraw_matrix_maximum_abs_difference_to_bradford": (
            adapted_matrix_difference
        ),
        "libraw_matrix_maximum_abs_difference_to_unadapted": (
            unadapted_matrix_difference
        ),
        "generated_profile_whitepoint_is_metadata_not_pixel_space_proof": True,
        "media_white_xyz_delta_libraw_minus_m165": white_delta,
        "media_white_xy_delta_libraw_minus_m165": white_xy_delta,
        "colorant_xyz_deltas_libraw_minus_m165": colorant_deltas,
        "maximum_abs_colorant_xyz_delta": max(
            abs(value)
            for values in colorant_deltas.values()
            for value in values
        ),
    }
    ledger.require(
        "PRODUCER_PIXEL_PROFILE_COMPATIBILITY",
        "PRODUCER_SEMANTICS",
        producer_compatible,
        "PRODUCER_SEMANTICS_NOT_PROVED",
        "producer transform is consistent with the embedded linear D50 ProPhoto semantics",
        producer_semantics,
    )

    tiff_data = reader.read("audited-common-tiff", inputs.tiff)
    tiff_audit = parse_tiff_from_bytes(
        tiff_data, "audited common TIFF", tifffile, np
    )
    tiff_storage_valid = (
        len(tiff_audit["shape"]) == 3
        and tiff_audit["shape"][2] == 3
        and tiff_audit["dtype"] == "uint16"
        and tiff_audit["compression"] == 1
        and tiff_audit["photometric"] == 2
        and tiff_audit["planar_configuration"] == 1
        and tiff_audit["bits_per_sample"] == 16
        and tiff_audit["icc_sha256"] == m165_profile["sha256"]
        and tiff_audit["icc_range"] is not None
        and tiff_audit["icc_range"]["sha256"] == m165_profile["sha256"]
        and tiff_audit["pixel_payload_sha256"]
        == tiff_audit["decoded_pixel_sha256"]
    )
    ledger.require(
        "TIFF_STORAGE",
        "TIFF_STORAGE",
        tiff_storage_valid,
        "TIFF_STORAGE_MISMATCH",
        "audited TIFF is uncompressed chunky unsigned RGB16 with frozen ICC",
        {"origin": inputs.tiff_origin, **{k: v for k, v in tiff_audit.items() if k != "icc"}},
    )

    fork_executable = resolve_strehl(
        reference["artifacts"]["fork_executable"]["path"]
    )
    lock_records: list[dict[str, Any]] = []
    try:
        with ExitStack() as locks:
            locked_inputs: dict[str, bytes] = {}
            for label, path in (
                ("fork-input-gamma1", inputs.fork_input_linear),
                ("fork-input-gamma18", inputs.fork_input_gamma18),
                ("fork-input-pixel-shift", inputs.fork_input_shifted),
            ):
                data, before, handle = locks.enter_context(
                    fork_lock_adapter.locked_input(path.resolve())
                )
                locked_inputs[label] = reader.adopt_locked(label, path, data)
                lock_records.append(
                    {
                        "label": label,
                        "before": before,
                        "handle": handle,
                        "sha256": sha256(data),
                        "bytes": len(data),
                    }
                )

            linear_input = parse_tiff_from_bytes(
                locked_inputs["fork-input-gamma1"],
                "fork gamma-1 input",
                tifffile,
                np,
            )
            gamma18_input = parse_tiff_from_bytes(
                locked_inputs["fork-input-gamma18"],
                "fork gamma-1.8 input",
                tifffile,
                np,
            )
            shifted_input = parse_tiff_from_bytes(
                locked_inputs["fork-input-pixel-shift"],
                "fork pixel-shift input",
                tifffile,
                np,
            )
            fork_input_valid = (
                linear_input["dtype"] == "uint16"
                and gamma18_input["dtype"] == "uint16"
                and shifted_input["dtype"] == "uint16"
                and linear_input["decoded_pixel_sha256"]
                == gamma18_input["decoded_pixel_sha256"]
                and shifted_input["decoded_pixel_sha256"]
                != linear_input["decoded_pixel_sha256"]
                and linear_input["icc_sha256"] == m165_profile["sha256"]
                and gamma18_input["icc_sha256"]
                not in (None, m165_profile["sha256"])
                and shifted_input["icc_sha256"] == m165_profile["sha256"]
                and linear_input["compression"]
                == gamma18_input["compression"]
                == shifted_input["compression"]
                == 1
                and linear_input["pixel_payload_sha256"]
                == linear_input["decoded_pixel_sha256"]
                and gamma18_input["pixel_payload_sha256"]
                == gamma18_input["decoded_pixel_sha256"]
                and shifted_input["pixel_payload_sha256"]
                == shifted_input["decoded_pixel_sha256"]
                and linear_input["planar_configuration"]
                == gamma18_input["planar_configuration"]
                == shifted_input["planar_configuration"]
                == 1
            )
            ledger.require(
                "FORK_PROFILE_FIXTURE_CONTRAST",
                "CONSUMER_FORK_RUNTIME",
                fork_input_valid,
                "FORK_PROFILE_FIXTURE_INVALID",
                "locked fork fixtures have exact uint16 pixels and distinct valid ICC TRCs",
                {
                    "gamma1": stable_tiff_summary(linear_input),
                    "gamma18": stable_tiff_summary(gamma18_input),
                    "pixel_shift": stable_tiff_summary(shifted_input),
                },
            )
            gamma18_profile = parse_icc(
                gamma18_input["icc"], "gamma-1.8 fixture profile"
            )
            try:
                gamma18_lcms = ImageCms.ImageCmsProfile(
                    BytesIO(gamma18_input["icc"])
                )
                gamma18_lcms_description = (
                    gamma18_lcms.profile.profile_description
                )
            except (OSError, ValueError, ImageCms.PyCMSError) as exc:
                raise GateFailure("FORK_PROFILE_FIXTURE_INVALID", str(exc)) from exc
            ledger.require(
                "FORK_PROFILE_FIXTURE_TRC",
                "CONSUMER_FORK_RUNTIME",
                all(
                    abs(value - 1.80078125) <= 1e-12
                    for value in gamma18_profile["gamma"].values()
                )
                and gamma18_lcms_description == profile_expectations["description"],
                "FORK_PROFILE_FIXTURE_INVALID",
                "contrast fixture is accepted by LittleCMS with gamma-1.8 TRCs",
                {
                    "gamma": gamma18_profile["gamma"],
                    "littlecms_description": gamma18_lcms_description,
                },
            )

            fork_runtime = run_fork_matrix(
                ledger,
                reader,
                inputs.run_label,
                fork_executable,
                inputs.out_root,
                inputs.fork_input_linear,
                inputs.fork_input_gamma18,
                inputs.fork_input_shifted,
                linear_input,
                gamma18_input,
                shifted_input,
                tifffile,
                np,
            )
            metadata_unchanged = True
            for record in lock_records:
                after = fork_lock_adapter.file_information(record["handle"])
                metadata_unchanged = (
                    metadata_unchanged and after == record["before"]
                )
            ledger.require(
                "FORK_LOCKED_INPUT_HANDOFF",
                "READ_AUDIT",
                metadata_unchanged,
                "INPUT_CHANGED_DURING_CONSUMPTION",
                "one verifier read stayed locked through every consumer exit",
                {
                    "api": "CreateFileW",
                    "desired_access": "GENERIC_READ",
                    "share_mode": "FILE_SHARE_READ",
                    "locked_input_count": len(lock_records),
                    "hash_and_parse_same_memory": True,
                    "consumer_path_opens_expected": True,
                    "held_through_consumer_exit": True,
                    "metadata_unchanged": metadata_unchanged,
                    "inputs": [
                        {
                            "label": record["label"],
                            "bytes": record["bytes"],
                            "sha256": record["sha256"],
                        }
                        for record in lock_records
                    ],
                },
            )
    except fork_lock_adapter.ConsumerFailure as exc:
        raise GateFailure(exc.failure_class, str(exc)) from exc

    interpretations = witnesses["consumer_interpretations"]
    consumers = [
        {
            "consumer_id": "strehl",
            "required": True,
            "classification": "HONORS_FROZEN_SAMPLE_SEMANTICS",
            "limitation": interpretations["strehl"]["limitation"],
            "claim_basis": interpretations["strehl"]["claim_basis"],
        },
        {
            "consumer_id": "focus-stack-fork",
            "required": True,
            "classification": "DIVERGES",
            "reason": interpretations["focus-stack-fork"]["reason"],
            "claim_basis": interpretations["focus-stack-fork"]["claim_basis"],
        },
        {
            "consumer_id": "zerene-pmax",
            "required": True,
            "classification": "PROPHOTO_UNPROVABLE_WITHOUT_LICENSED_CONTROLLED_RUN_OR_VENDOR_STATEMENT_ON_INTERNAL_PIXEL_PIPELINE",
            "claim_basis": interpretations["zerene-pmax"]["claim_basis"],
        },
        {
            "consumer_id": "zerene-dmap",
            "required": True,
            "classification": "PROPHOTO_UNPROVABLE_WITHOUT_LICENSED_CONTROLLED_RUN_OR_VENDOR_STATEMENT_ON_INTERNAL_PIXEL_PIPELINE",
            "claim_basis": interpretations["zerene-dmap"]["claim_basis"],
        },
    ]
    interpretation_valid = all(
        interpretations[item["consumer_id"]]["classification"]
        == item["classification"]
        for item in consumers
    )
    ledger.require(
        "CONSUMER_CLASSIFICATIONS",
        "CONSUMER_PARTITION",
        interpretation_valid,
        "CONSUMER_CLASSIFICATION_MISMATCH",
        "consumer classifications match source/runtime evidence",
        consumers,
    )
    counts: dict[str, int] = {}
    for consumer in consumers:
        classification = consumer["classification"]
        counts[classification] = counts.get(classification, 0) + 1
    expected_partition = reference["consumer_partition"]
    partition_valid = (
        len(consumers) == expected_partition["required_count"]
        and sum(counts.values()) == expected_partition["required_count"]
        and counts == expected_partition["expected_counts"]
    )
    consumer_partition = {
        "required_total": len(consumers),
        "counts": counts,
        "sum": sum(counts.values()),
        "sum_matches_total": sum(counts.values()) == len(consumers),
        "expected": expected_partition,
        "optional": witnesses["optional_consumers"],
    }
    ledger.require(
        "CONSUMER_REQUIRED_PARTITION",
        "CONSUMER_PARTITION",
        partition_valid,
        "CONSUMER_PARTITION_MISMATCH",
        "required consumer partition is exhaustive and totals four",
        consumer_partition,
    )

    headline_valid = (
        producer_compatible
        and counts.get("DIVERGES") == 1
        and reference["headline_verdict"] == "PROPHOTO_DISPROVED"
    )
    ledger.require(
        "HEADLINE_VERDICT",
        "VERDICT",
        headline_valid,
        "HEADLINE_VERDICT_MISMATCH",
        "required fork divergence forces PROPHOTO_DISPROVED despite producer compatibility",
        {
            "producer_d50_compatible": producer_compatible,
            "fork_diverges": counts.get("DIVERGES") == 1,
            "zerene_unprovable": counts.get(
                "PROPHOTO_UNPROVABLE_WITHOUT_LICENSED_CONTROLLED_RUN_OR_VENDOR_STATEMENT_ON_INTERNAL_PIXEL_PIPELINE"
            )
            == 2,
        },
    )

    read_counts = {
        record["path"]: record["read_count"] for record in reader.records
    }
    ledger.require(
        "PATH_READ_COUNTS",
        "READ_AUDIT",
        bool(read_counts) and max(read_counts.values()) <= 1,
        "PATH_READ_MULTIPLE",
        "every verifier path artifact was read at most once",
        {
            "path_count": len(read_counts),
            "maximum_read_count": max(read_counts.values()),
            "consumer_reopens_are_locked": True,
        },
    )

    return {
        "reference_sha256": sha256(reference_data),
        "witnesses_sha256": sha256(witness_data),
        "source_anchors": anchor_observations,
        "git_object_audit": git_object_records,
        "m165_profile": m165_profile,
        "littlecms_profile": lcms_profile_data,
        "colour_science_profile": colour_data,
        "profile_patch_witness": patch_witness,
        "libraw_generated_profile": generated_profile,
        "producer_semantics": producer_semantics,
        "tiff_audit": {
            "origin": inputs.tiff_origin,
            **{key: value for key, value in tiff_audit.items() if key != "icc"},
        },
        "fork_runtime": fork_runtime,
        "consumers": consumers,
        "consumer_partition": consumer_partition,
        "path_read_audit": [
            {
                "label": record["label"],
                "path": record["path"],
                "read_count": record["read_count"],
                "read_method": record.get("read_method", "Path.read_bytes"),
            }
            for record in reader.records
        ],
    }


def partitions(checks: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    status_counts = {"PASS": 0, "RED": 0}
    by_arm: dict[str, dict[str, int]] = {}
    for check in checks:
        status = check["status"]
        status_counts[status] += 1
        arm = check["arm"]
        arm_counts = by_arm.setdefault(arm, {"PASS": 0, "RED": 0})
        arm_counts[status] += 1
    total = len(checks)
    check_partition = {
        **status_counts,
        "total": total,
        "sum": sum(status_counts.values()),
        "sum_matches_total": sum(status_counts.values()) == total,
    }
    arm_partition = []
    for arm in sorted(by_arm):
        counts = by_arm[arm]
        arm_total = sum(counts.values())
        arm_partition.append(
            {
                "arm": arm,
                **counts,
                "total": arm_total,
                "sum": arm_total,
                "sum_matches_total": True,
            }
        )
    return check_partition, arm_partition


def parse_args() -> Inputs:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=HERE / "reference.json")
    parser.add_argument("--witnesses", type=Path, default=HERE / "witnesses.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--libraw-source", type=Path, required=True)
    parser.add_argument("--libraw-colorconst", type=Path, required=True)
    parser.add_argument("--romm-registry", type=Path, required=True)
    parser.add_argument("--zerene-doc", type=Path, required=True)
    parser.add_argument("--tiff", type=Path, required=True)
    parser.add_argument(
        "--tiff-origin", choices=("development-common", "tifffile-fixture"), required=True
    )
    parser.add_argument("--fork-input-linear", type=Path, required=True)
    parser.add_argument("--fork-input-gamma18", type=Path, required=True)
    parser.add_argument("--fork-input-shifted", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, default=HERE / "out")
    values = parser.parse_args()
    return Inputs(
        reference=values.reference,
        witnesses=values.witnesses,
        output=values.output,
        run_label=values.run_label,
        libraw_source=values.libraw_source,
        libraw_colorconst=values.libraw_colorconst,
        romm_registry=values.romm_registry,
        zerene_doc=values.zerene_doc,
        tiff=values.tiff,
        tiff_origin=values.tiff_origin,
        fork_input_linear=values.fork_input_linear,
        fork_input_gamma18=values.fork_input_gamma18,
        fork_input_shifted=values.fork_input_shifted,
        out_root=values.out_root,
    )


def main() -> int:
    inputs = parse_args()
    ledger = Ledger()
    reader = ReadOnce()
    evidence: dict[str, Any] = {}
    fatal_failure: dict[str, str] | None = None
    try:
        evidence = execute(inputs, ledger, reader)
    except GateFailure as exc:
        fatal_failure = {
            "failure_class": exc.failure_class,
            "reason": str(exc),
        }
        if not ledger.checks or ledger.checks[-1]["failure_class"] != exc.failure_class:
            ledger.add(
                "FATAL_GATE_ERROR",
                "FAIL_CLOSED",
                False,
                exc.failure_class,
                str(exc),
            )

    check_partition, arm_partition = partitions(ledger.checks)
    failure_classes = sorted(
        {
            check["failure_class"]
            for check in ledger.checks
            if check["failure_class"] is not None
        }
    )
    passed = fatal_failure is None and check_partition["RED"] == 0
    result = {
        "schema": RESULT_SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "headline_verdict": "PROPHOTO_DISPROVED" if passed else "INDETERMINATE",
        "scope": "input-contract-only-not-quality-comparison",
        "run_label": inputs.run_label,
        "failure_classes": failure_classes,
        "fatal_failure": fatal_failure,
        "check_partition": check_partition,
        "arm_partition": arm_partition,
        "checks": ledger.checks,
        "evidence": evidence,
    }
    write_json(inputs.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "headline_verdict": result["headline_verdict"],
                "failure_classes": failure_classes,
                "check_partition": check_partition,
                "output": str(inputs.output.resolve()),
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
