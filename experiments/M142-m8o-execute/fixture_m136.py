from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import tifffile


U16_MAX = 65535
NUMERIC_REPRESENTATION = (
    "fixture-only identity: P_fixture(z)=z; F_fixture(z)=clamp(z,0,1)"
)
INTERPRETATION_COMMIT = "746cc38a"
INTERPRETATION_CANONICAL_SHA256 = (
    "DBCCCF505D91FB86385D44BE3293A280A54ACE4C0C416945F23CFDFE355A203C"
)
M136_EVIDENCE_DIR = (
    Path(__file__).resolve().parent.parent / "M136-m8o-bar"
).resolve()
INTERPRETATION_PATH = M136_EVIDENCE_DIR / "prospective-interpretations.md"
TRACE_MAGIC = b"M8SITE03"
TRACE_HEADER = struct.Struct("<8s15I6d4f32s32sI")
TRACE_VERSION = 3
TRACE_KERNEL_CATMULL = 0
TRACE_KERNEL_BILINEAR = 1
TRACE_KERNEL_CLAMPED_CATMULL = 2
TRACE_ARITHMETIC_CONTRACT = 1
COMMISSION_FREEZE_SHA256 = "00" * 32
TRACE_NAME_TEMPLATE = (
    "m8-trace-v3-p1-f{frame:08d}-{path_hash}-"
    "s{site_x}{site_y}-{content_hash}.m8site"
)
FAIL_CLOSED_CONTROLS = (
    "trace v2 without black level reports UNMEASURED",
    "missing crop origin reports UNMEASURED",
    "missing or duplicate frame/site trace reports UNMEASURED",
    "producer-supplied hull or contributor mask is ignored",
    "Catmull hard-step is red for M8-R",
    "clamped hard-step, copy, and convex-bilinear controls are green for M8-R",
    "widened-clamp sabotage is red for M8-R",
)
NUMERIC_FIELDS = ("lo", "hi", "tau", "encoded", "expected_violations")
INTERMEDIATE_FIELDS = (
    "g",
    "b",
    "G",
    "R",
    "lo",
    "hi",
    "tau",
    "expected_intermediate_u16",
    "expected_pre_final",
    "green_encoded",
    "red_encoded",
)
CROP_FIELDS = (
    "channels",
    "compact_height",
    "compact_width",
    "expected_wrong_origin_violations",
    "full_height",
    "full_width",
    "normalization",
    "origin_x",
    "origin_y",
    "source_value",
    "transform",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_canonical_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()


def mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    return value


def require_fields(value: dict[str, Any], fields: tuple[str, ...], where: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise ValueError(f"{where} is missing: {', '.join(missing)}")


def integer(value: Any, where: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{where} must be in [{low}, {high}]")
    return value


def number(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{where} must be finite")
    return result


def text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where} must be a non-empty string")
    return value


def load_preregistration(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    preregistration = mapping(
        json.loads(path.read_text(encoding="utf-8")), "preregistration"
    )
    for field in ("protocol", "status", "result"):
        text(preregistration.get(field), f"preregistration.{field}")

    commissioning = mapping(
        preregistration.get("commissioning"), "preregistration.commissioning"
    )
    numeric = mapping(
        commissioning.get("m8_o_numeric_cases"),
        "commissioning.m8_o_numeric_cases",
    )
    if len(numeric) != 8:
        raise ValueError("commissioning.m8_o_numeric_cases must contain eight cases")
    for name, raw_case in numeric.items():
        text(name, "numeric case name")
        case = mapping(raw_case, f"m8_o_numeric_cases.{name}")
        require_fields(case, NUMERIC_FIELDS, f"m8_o_numeric_cases.{name}")
        lo = number(case["lo"], f"{name}.lo")
        hi = number(case["hi"], f"{name}.hi")
        if lo > hi:
            raise ValueError(f"{name}.lo must not exceed {name}.hi")
        if number(case["tau"], f"{name}.tau") < 0:
            raise ValueError(f"{name}.tau must be non-negative")
        integer(case["encoded"], f"{name}.encoded", 0, U16_MAX)
        integer(case["expected_violations"], f"{name}.expected_violations", 0, 1)

    intermediate = mapping(
        commissioning.get("intermediate_quantizer_case"),
        "commissioning.intermediate_quantizer_case",
    )
    require_fields(
        intermediate,
        INTERMEDIATE_FIELDS,
        "commissioning.intermediate_quantizer_case",
    )
    for field in ("g", "G", "R"):
        if number(intermediate[field], f"intermediate_quantizer_case.{field}") <= 0:
            raise ValueError(f"intermediate_quantizer_case.{field} must be positive")
    if number(intermediate["b"], "intermediate_quantizer_case.b") < 0:
        raise ValueError("intermediate_quantizer_case.b must be non-negative")
    lo = number(intermediate["lo"], "intermediate_quantizer_case.lo")
    hi = number(intermediate["hi"], "intermediate_quantizer_case.hi")
    if lo > hi:
        raise ValueError("intermediate_quantizer_case.lo must not exceed hi")
    if number(intermediate["tau"], "intermediate_quantizer_case.tau") < 0:
        raise ValueError("intermediate_quantizer_case.tau must be non-negative")
    expected_pre_final = number(
        intermediate["expected_pre_final"],
        "intermediate_quantizer_case.expected_pre_final",
    )
    if expected_pre_final < 0:
        raise ValueError(
            "intermediate_quantizer_case.expected_pre_final must be non-negative"
        )
    for field in ("expected_intermediate_u16", "green_encoded", "red_encoded"):
        integer(
            intermediate[field],
            f"intermediate_quantizer_case.{field}",
            0,
            U16_MAX,
        )

    crop = mapping(
        commissioning.get("crop_origin_case"), "commissioning.crop_origin_case"
    )
    require_fields(crop, CROP_FIELDS, "commissioning.crop_origin_case")
    dimensions = {
        field: integer(crop[field], f"crop_origin_case.{field}", 1, 1 << 20)
        for field in (
            "channels",
            "compact_height",
            "compact_width",
            "full_height",
            "full_width",
        )
    }
    if dimensions != {
        "channels": 1,
        "compact_height": 2,
        "compact_width": 3,
        "full_height": 8,
        "full_width": 8,
    }:
        raise ValueError("crop_origin_case must describe the frozen 8x8 -> 3x2 case")
    origin_x = integer(crop["origin_x"], "crop_origin_case.origin_x", 0, 1 << 20)
    origin_y = integer(crop["origin_y"], "crop_origin_case.origin_y", 0, 1 << 20)
    if origin_x + dimensions["compact_width"] > dimensions["full_width"]:
        raise ValueError("crop_origin_case exceeds the full width")
    if origin_y + dimensions["compact_height"] > dimensions["full_height"]:
        raise ValueError("crop_origin_case exceeds the full height")
    expected_wrong = integer(
        crop["expected_wrong_origin_violations"],
        "crop_origin_case.expected_wrong_origin_violations",
        0,
        dimensions["compact_width"] * dimensions["compact_height"],
    )
    if expected_wrong != dimensions["compact_width"] * dimensions["compact_height"]:
        raise ValueError("crop_origin_case must expect every compact pixel to differ")
    text(crop["source_value"], "crop_origin_case.source_value")
    text(crop["normalization"], "crop_origin_case.normalization")
    if crop["transform"] != "integer identity":
        raise ValueError("crop_origin_case.transform must be 'integer identity'")
    fail_closed = commissioning.get("fail_closed")
    if (
        not isinstance(fail_closed, list)
        or tuple(fail_closed) != FAIL_CLOSED_CONTROLS
    ):
        raise ValueError("commissioning.fail_closed differs from the frozen seven")
    return preregistration, commissioning


def write_json(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def crop_arrays(crop: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    source_match = re.fullmatch(r"(\d+)\*y\+x", crop["source_value"])
    normalization_match = re.fullmatch(
        r"F\(z\)=z/(\d+) before final-u16 serialization", crop["normalization"]
    )
    if source_match is None or normalization_match is None:
        raise ValueError("crop_origin_case contains an unsupported frozen formula")
    y_scale = int(source_match.group(1))
    divisor = int(normalization_match.group(1))
    if divisor <= 0:
        raise ValueError("crop_origin_case normalization divisor must be positive")

    y, x = np.indices(
        (crop["full_height"], crop["full_width"]), dtype=np.float64
    )
    source = np.asarray(y_scale * y + x, dtype="<f8")
    oy, ox = crop["origin_y"], crop["origin_x"]
    height, width = crop["compact_height"], crop["compact_width"]
    correct_values = source[oy : oy + height, ox : ox + width]
    wrong_values = source[:height, :width]

    def serialize(values: np.ndarray) -> np.ndarray:
        normalized = values / np.float64(divisor)
        if np.any((normalized < 0.0) | (normalized > 1.0)):
            raise ValueError("crop_origin_case values are outside the uint16 domain")
        return np.asarray(np.floor(normalized * U16_MAX + 0.5), dtype="<u2")

    correct = serialize(correct_values)
    wrong = serialize(wrong_values)
    differing = int(np.count_nonzero(correct != wrong))
    if differing != crop["expected_wrong_origin_violations"]:
        raise ValueError(
            "crop-origin TIFFs do not differ at the preregistered pixel count"
        )
    return source, correct, wrong


def trace_filename(
    payload: bytes,
    frame_order: int,
    frame_path: Path,
    site_x: int,
    site_y: int,
) -> str:
    path_hash = hashlib.sha256(str(frame_path).encode("utf-8")).hexdigest()
    content_hash = hashlib.sha256(payload).hexdigest()
    return TRACE_NAME_TEMPLATE.format(
        frame=frame_order,
        path_hash=path_hash,
        site_x=site_x,
        site_y=site_y,
        content_hash=content_hash,
    )


def write_trace(
    directory: Path,
    *,
    artifact_name: str,
    frame_path: Path,
    frame_order: int,
    site_x: int,
    site_y: int,
    channel: int,
    source: np.ndarray,
    gathered: np.ndarray,
    kernel: int = TRACE_KERNEL_CLAMPED_CATMULL,
    b_re: float = 0.25,
    b_im: float = 0.25,
    output_gain: float = 1.0,
    magic: bytes = TRACE_MAGIC,
) -> dict[str, str]:
    source = np.asarray(source, dtype="<f4")
    gathered = np.asarray(gathered, dtype="<f4")
    if source.ndim != 2 or gathered.ndim != 2:
        raise ValueError("synthetic trace source and gathered values must be 2-D")
    full_height, full_width = gathered.shape
    source_height, source_width = source.shape
    if (
        source_height != 2 * full_height
        or source_width != 2 * full_width
        or full_height < 3
        or full_width < 3
    ):
        raise ValueError("synthetic trace source must be exactly 2x a >=3x3 gather")
    encoded_path = str(frame_path).encode("utf-8")
    source_hash = bytes.fromhex(sha256(frame_path))
    header = TRACE_HEADER.pack(
        magic,
        TRACE_VERSION,
        kernel,
        frame_order,
        source_width,
        source_height,
        full_width,
        full_height,
        full_width - 2,
        full_height - 2,
        1,
        1,
        site_x,
        site_y,
        channel,
        TRACE_ARITHMETIC_CONTRACT,
        1.0,
        0.0,
        b_re,
        b_im,
        full_width * 0.5,
        full_height * 0.5,
        0.0,
        1.0,
        1.0,
        output_gain,
        bytes.fromhex(COMMISSION_FREEZE_SHA256),
        source_hash,
        len(encoded_path),
    )
    payload = (
        header
        + encoded_path
        + source.tobytes(order="C")
        + gathered.tobytes(order="C")
    )
    name = trace_filename(payload, frame_order, frame_path, site_x, site_y)
    if Path(artifact_name).name != artifact_name:
        raise ValueError(f"trace artifact name must be direct: {artifact_name!r}")
    (directory / artifact_name).write_bytes(payload)
    return {"artifact": artifact_name, "trace_name": name}


def m8r_kernel_controls() -> dict[str, dict[str, Any]]:
    source = np.zeros((32, 40), dtype="<f4")
    source[:, 18:] = np.float32(1.0)
    constant = np.ones_like(source)
    valid = np.zeros((16, 20), dtype=bool)
    valid[1:15, 1:19] = True

    raw = np.full((16, 20), np.float32(np.nan), dtype="<f4")
    raw[valid] = np.float32(0.0)
    raw[1:15, 8] = np.float32(-0.0625)
    raw[1:15, 9] = np.float32(1.0625)
    raw[1:15, 10:19] = np.float32(1.0)
    clamped = np.where(valid, np.clip(raw, 0.0, 1.0), np.nan).astype("<f4")

    ulp_one = np.nextafter(
        np.float32(1.0), np.float32(np.inf), dtype=np.float32
    ) - np.float32(1.0)
    tau = np.float32(8.0) * ulp_one
    widened_epsilon = np.float32(32.0) * tau
    widened = np.where(
        valid,
        np.clip(raw, -widened_epsilon, np.float32(1.0) + widened_epsilon),
        np.nan,
    ).astype("<f4")

    copy = np.where(valid, np.where(np.indices(valid.shape)[1] >= 9, 1.0, 0.0), np.nan)
    copy = np.asarray(copy, dtype="<f4")
    bilinear = copy.copy()
    bilinear[1:15, 8] = np.float32(0.5)
    bilinear[1:15, 9] = np.float32(1.0)

    planted = np.where(valid, np.float32(1.0), np.float32(np.nan)).astype("<f4")
    planted[5, 5] = np.float32(1.0) + widened_epsilon
    planted[5, 6] = np.float32(1.0) - widened_epsilon

    return {
        "catmull_hard_step": {
            "source": source,
            "gathered": raw,
            "kernel": TRACE_KERNEL_CATMULL,
        },
        "clamped_hard_step": {
            "source": source,
            "gathered": clamped,
            "kernel": TRACE_KERNEL_CLAMPED_CATMULL,
        },
        "widened_clamp_sabotage": {
            "source": source,
            "gathered": widened,
            "kernel": TRACE_KERNEL_CLAMPED_CATMULL,
        },
        "copy_null": {
            "source": source,
            "gathered": copy,
            "kernel": TRACE_KERNEL_CATMULL,
        },
        "clamped_copy_null": {
            "source": source,
            "gathered": copy.copy(),
            "kernel": TRACE_KERNEL_CLAMPED_CATMULL,
        },
        "convex_bilinear_null": {
            "source": source,
            "gathered": bilinear,
            "kernel": TRACE_KERNEL_BILINEAR,
        },
        "explicit_high_low": {
            "source": constant,
            "gathered": planted,
            "kernel": TRACE_KERNEL_CATMULL,
        },
    }


def write_fail_closed_fixtures(
    directory: Path,
    source_frame: Path,
) -> dict[str, Any]:
    controls = m8r_kernel_controls()
    channels = {(0, 0): 0, (1, 0): 1, (0, 1): 1, (1, 1): 2}

    control_traces: dict[str, dict[str, str]] = {}
    for frame_order, name in enumerate(
        (
            "catmull_hard_step",
            "clamped_hard_step",
            "widened_clamp_sabotage",
            "copy_null",
            "clamped_copy_null",
            "convex_bilinear_null",
            "explicit_high_low",
        )
    ):
        control = controls[name]
        control_traces[name] = write_trace(
            directory,
            artifact_name=f"trace-m8r-{name}.bin",
            frame_path=source_frame,
            frame_order=frame_order,
            site_x=0,
            site_y=0,
            channel=0,
            source=control["source"],
            gathered=control["gathered"],
            # Target traces are clamped-Catmull only.  The synthetic arm name
            # identifies the planted gathered values; the header remains on
            # the target contract so commissioning cannot weaken target
            # parsing to accept another kernel.
            kernel=TRACE_KERNEL_CLAMPED_CATMULL,
        )

    complete = [
        write_trace(
            directory,
            artifact_name="trace-complete-s00.bin",
            frame_path=source_frame,
            frame_order=0,
            site_x=0,
            site_y=0,
            channel=0,
            source=controls["copy_null"]["source"],
            gathered=controls["copy_null"]["gathered"],
            kernel=TRACE_KERNEL_CLAMPED_CATMULL,
        )
    ]
    for site_x, site_y in ((1, 0), (0, 1), (1, 1)):
        name = write_trace(
            directory,
            artifact_name=f"trace-complete-s{site_x}{site_y}.bin",
            frame_path=source_frame,
            frame_order=0,
            site_x=site_x,
            site_y=site_y,
            channel=channels[(site_x, site_y)],
            source=controls["clamped_hard_step"]["source"],
            gathered=controls["clamped_hard_step"]["gathered"],
            kernel=TRACE_KERNEL_CLAMPED_CATMULL,
        )
        complete.append(name)
    duplicate = write_trace(
        directory,
        artifact_name="trace-duplicate-s00.bin",
        frame_path=source_frame,
        frame_order=0,
        site_x=0,
        site_y=0,
        channel=0,
        source=controls["copy_null"]["source"],
        gathered=controls["copy_null"]["gathered"],
        kernel=TRACE_KERNEL_CLAMPED_CATMULL,
        output_gain=1.25,
    )

    source = np.asarray(controls["catmull_hard_step"]["source"], dtype="<f4")
    gathered = np.asarray(controls["catmull_hard_step"]["gathered"], dtype="<f4")
    v2_payload_path = str(source_frame).encode("utf-8")
    v2_payload = struct.pack(
        "<8s9I6d2fI",
        b"M8SITE01",
        2,
        0,
        source.shape[1],
        source.shape[0],
        gathered.shape[1],
        gathered.shape[0],
        0,
        0,
        0,
        1.0,
        0.0,
        0.25,
        0.25,
        2.0,
        2.0,
        1.0,
        1.0,
        len(v2_payload_path),
    ) + v2_payload_path + source.tobytes(order="C") + gathered.tobytes(order="C")
    v2_name = trace_filename(v2_payload, 0, source_frame, 0, 0)
    v2_artifact = "trace-v2-without-black.bin"
    (directory / v2_artifact).write_bytes(v2_payload)

    missing_crop_payload = struct.pack(
        "<8s9I",
        TRACE_MAGIC,
        TRACE_VERSION,
        TRACE_KERNEL_CLAMPED_CATMULL,
        0,
        8,
        8,
        4,
        4,
        2,
        2,
    )
    missing_crop_name = trace_filename(
        missing_crop_payload, 0, source_frame, 0, 0
    )
    missing_crop_artifact = "trace-v3-missing-crop.bin"
    (directory / missing_crop_artifact).write_bytes(missing_crop_payload)

    producer_hull = np.full((3, 2, 2), np.float32(-12345.0), dtype="<f4")
    producer_mask = np.zeros((3, 2, 2), dtype=np.uint16)
    np.save(directory / "producer-supplied-hull.npy", producer_hull, allow_pickle=False)
    np.save(
        directory / "producer-supplied-contributor-mask.npy",
        producer_mask,
        allow_pickle=False,
    )

    return {
        "schema_version": 1,
        "source": "commissioning.fail_closed",
        "preregistered_controls": list(FAIL_CLOSED_CONTROLS),
        "source_frame": {
            "path": str(source_frame),
            "sha256": sha256(source_frame),
        },
        "trace_rejection": {
            "v2_without_black_level": {
                "artifact": v2_artifact,
                "trace_name": v2_name,
                "expected_status": "UNMEASURED",
            },
            "missing_crop_origin": {
                "artifact": missing_crop_artifact,
                "trace_name": missing_crop_name,
                "expected_status": "UNMEASURED",
            },
        },
        "frame_site_set": {
            "complete": complete,
            "missing": complete[:-1],
            "duplicate_extra": duplicate,
            "expected_missing_status": "UNMEASURED",
            "expected_duplicate_status": "UNMEASURED",
        },
        "producer_fields": {
            "hull": "producer-supplied-hull.npy",
            "contributor_mask": "producer-supplied-contributor-mask.npy",
            "expected": "ignored",
        },
        "m8_r": {
            "controls": {
                "catmull_hard_step": {
                    **control_traces["catmull_hard_step"],
                    "expected": "red",
                },
                "clamped_hard_step": {
                    **control_traces["clamped_hard_step"],
                    "expected": "green",
                },
                "copy_null": {
                    **control_traces["copy_null"],
                    "expected": "green",
                },
                "clamped_copy_null": {
                    **control_traces["clamped_copy_null"],
                    "expected": "green",
                },
                "convex_bilinear_null": {
                    **control_traces["convex_bilinear_null"],
                    "expected": "green",
                },
                "widened_clamp_sabotage": {
                    **control_traces["widened_clamp_sabotage"],
                    "expected": "red",
                },
                "explicit_high_low": {
                    **control_traces["explicit_high_low"],
                    "expected": "red",
                },
            }
        },
    }


def artifact_inventory(directory: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(directory.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.name != "manifest.json"
    ]


def commission(preregistration_path: Path, output: Path) -> None:
    preregistration_path = preregistration_path.resolve(strict=True)
    interpretation_path = INTERPRETATION_PATH.resolve(strict=True)
    if (
        sha256_canonical_text(interpretation_path)
        != INTERPRETATION_CANONICAL_SHA256
    ):
        raise ValueError(
            "prospective interpretation differs from the pre-target ruling"
        )
    output = output.resolve(strict=False)
    if os.path.lexists(output):
        raise FileExistsError(f"refusing to overwrite existing output: {output}")

    preregistration, commissioning = load_preregistration(preregistration_path)
    numeric = commissioning["m8_o_numeric_cases"]
    intermediate = commissioning["intermediate_quantizer_case"]
    crop = commissioning["crop_origin_case"]
    source, correct, wrong = crop_arrays(crop)

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    renamed = False
    try:
        numeric_cases = {
            name: {
                **{field: case[field] for field in NUMERIC_FIELDS},
                "representation_map": NUMERIC_REPRESENTATION,
            }
            for name, case in numeric.items()
        }
        write_json(
            staging / "m8-o-numeric-cases.json",
            {
                "schema_version": 1,
                "source": "commissioning.m8_o_numeric_cases",
                "case_count": len(numeric_cases),
                "cases": numeric_cases,
            },
        )
        write_json(
            staging / "intermediate-quantizer-case.json",
            {
                "schema_version": 1,
                "source": "commissioning.intermediate_quantizer_case",
                "case": {field: intermediate[field] for field in INTERMEDIATE_FIELDS},
            },
        )
        np.save(staging / "crop-origin-source.npy", source, allow_pickle=False)
        tiff_options = {
            "photometric": "minisblack",
            "metadata": None,
            "datetime": False,
            "software": "fixture_m136.py",
            "compression": None,
            "byteorder": "<",
        }
        tifffile.imwrite(staging / "crop-origin-correct.tiff", correct, **tiff_options)
        tifffile.imwrite(staging / "crop-origin-wrong.tiff", wrong, **tiff_options)
        write_json(
            staging / "crop-origin-case.json",
            {
                "schema_version": 1,
                "source": "commissioning.crop_origin_case",
                "case": {field: crop[field] for field in CROP_FIELDS},
                "source_grid": {
                    "path": "crop-origin-source.npy",
                    "dtype": "float64",
                    "shape": [crop["full_height"], crop["full_width"]],
                },
                "correct_origin_tiff": {
                    "path": "crop-origin-correct.tiff",
                    "dtype": "uint16",
                    "shape": [crop["compact_height"], crop["compact_width"]],
                    "full_plane_origin": [crop["origin_x"], crop["origin_y"]],
                },
                "wrong_origin_tiff": {
                    "path": "crop-origin-wrong.tiff",
                    "dtype": "uint16",
                    "shape": [crop["compact_height"], crop["compact_width"]],
                    "full_plane_origin": [0, 0],
                    "semantics": "compact x,y incorrectly used as full coordinates",
                },
                "serialization": "half-up(clamp(z/divisor, 0, 1) * 65535) to uint16",
            },
        )
        fail_closed = write_fail_closed_fixtures(
            staging, Path(__file__).resolve()
        )
        write_json(staging / "fail-closed-cases.json", fail_closed)

        manifest = {
            "schema": "m136-commissioning-fixture-manifest",
            "schema_version": 1,
            "preregistration": {
                "path": str(preregistration_path),
                "sha256": sha256(preregistration_path),
                "protocol": preregistration["protocol"],
                "status": preregistration["status"],
                "result": preregistration["result"],
            },
            "prospective_interpretation": {
                "path": str(interpretation_path),
                "sha256": sha256(interpretation_path),
                "canonical_sha256": INTERPRETATION_CANONICAL_SHA256,
                "commit": INTERPRETATION_COMMIT,
            },
            "fixture_semantics": {
                "numeric_cases": NUMERIC_REPRESENTATION,
                "intermediate_quantizer_case": (
                    "frozen native-representation inputs and expected outputs"
                ),
                "crop_origin_case": (
                    "8x8 float64 full-plane source; correct and compact-as-full "
                    "origin TIFFs use final half-up uint16 serialization"
                ),
                "fail_closed": (
                    "value-only trace-v3 rejection/completeness fixtures and "
                    "hard-step M8-R potency controls"
                ),
                "artifact_inventory": (
                    "all fixture files except manifest.json, whose self-hash "
                    "would be recursive"
                ),
            },
            "expected_outcomes": {
                "m8_o_numeric_cases": {
                    name: case["expected_violations"]
                    for name, case in numeric.items()
                },
                "intermediate_quantizer_case": {
                    field: intermediate[field]
                    for field in (
                        "expected_intermediate_u16",
                        "expected_pre_final",
                        "green_encoded",
                        "red_encoded",
                    )
                },
                "crop_origin_case": {
                    "expected_wrong_origin_violations": crop[
                        "expected_wrong_origin_violations"
                    ]
                },
                "fail_closed": list(FAIL_CLOSED_CONTROLS),
            },
            "artifacts": artifact_inventory(staging),
        }
        write_json(staging / "manifest.json", manifest)

        if os.path.lexists(output):
            raise FileExistsError(f"refusing to overwrite existing output: {output}")
        os.rename(staging, output)
        renamed = True
    finally:
        if not renamed:
            shutil.rmtree(staging, ignore_errors=True)

    print(f"commissioned M136 fixture: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the M136 fixture")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("commission")
    command.add_argument("--preregistration", required=True, type=Path)
    command.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        commission(args.preregistration, args.output)
    except Exception as error:
        print(f"fixture_m136: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
