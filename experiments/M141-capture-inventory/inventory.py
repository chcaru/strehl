r"""Build a metadata-only inventory of every RAW capture under D:\personal\macro.

The capture trees are read-only inputs. This script invokes ExifTool only for
metadata and writes reusable JSON/CSV summaries beside this file.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CAPTURE_ROOT = Path(r"D:\personal\macro")
DEFAULT_EDITED_ROOT = Path(r"D:\edited\macro")
DEFAULT_EXIFTOOL = Path(
    r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe"
)
HERE = Path(__file__).resolve().parent

EXIF_TAGS = (
    "FileName",
    "Directory",
    "DateTimeOriginal",
    "SubSecDateTimeOriginal",
    "CreateDate",
    "ISO",
    "ExposureTime",
    "FNumber",
    "FocalLength",
    "FocusDistance2",
    "FocusPosition2",
    "ImageStabilization",
    "LensModel",
    "LensType3",
    "ReleaseMode",
    "SequenceNumber",
    "SequenceImageNumber",
    "SequenceLength",
    "CameraModelName",
    "Model",
    "Make",
    "Quality",
    "WhiteBalance",
    "LongExposureNoiseReduction",
    "HighISONoiseReduction",
)

CSV_FIELDS = (
    "stack_id",
    "scope",
    "request_group",
    "subject_or_name",
    "path",
    "frame_count",
    "first_file",
    "last_file",
    "first_capture_at",
    "last_capture_at",
    "duration_seconds",
    "capture_contiguous",
    "filename_sequence_contiguous",
    "timestamp_monotonic",
    "median_gap_seconds",
    "max_gap_seconds",
    "continuity_threshold_seconds",
    "iso_values",
    "exposure_seconds_values",
    "aperture_values",
    "focal_length_mm_values",
    "focus_distance_m_values",
    "image_stabilization_values",
    "release_mode_values",
    "step_width",
    "step_width_status",
    "cpl",
    "cpl_source",
    "magnification",
    "magnification_status",
    "setting_segment_count",
    "arw_bytes",
    "other_file_count",
    "numeric_status",
)

SEGMENT_FIELDS = (
    "stack_id",
    "segment_index",
    "frame_count",
    "first_file",
    "last_file",
    "first_capture_at",
    "last_capture_at",
    "iso",
    "exposure_seconds",
    "aperture",
    "focal_length_mm",
    "image_stabilization",
    "release_mode",
    "numeric_status",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_snapshot(path: Path) -> dict[str, Any]:
    file_count = 0
    total_bytes = 0
    for base, _, names in os.walk(path):
        for name in names:
            item = Path(base) / name
            stat = item.stat()
            file_count += 1
            total_bytes += stat.st_size
    return {
        "path": str(path),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "numeric_status": "VERIFIED",
        "method": "recursive filesystem enumeration including hidden files",
    }


def run_exiftool(
    exiftool: Path,
    capture_root: Path,
    *,
    numeric: bool,
    tags: tuple[str, ...],
) -> list[dict[str, Any]]:
    command = [
        str(exiftool),
        "-json",
        "-r",
        "-ext",
        "ARW",
    ]
    if numeric:
        command.append("-n")
    command.extend(f"-{tag}" for tag in tags)
    command.extend(["--", str(capture_root)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=True,
    )
    return json.loads(completed.stdout)


def normalise_path(path: str | Path) -> str:
    return str(Path(path)).replace("/", "\\")


def parse_capture_time(record: dict[str, Any]) -> datetime:
    raw = record.get("SubSecDateTimeOriginal") or record.get("DateTimeOriginal")
    if not raw:
        raise ValueError(f"capture timestamp missing: {record.get('SourceFile')}")
    for fmt in (
        "%Y:%m:%d %H:%M:%S.%f%z",
        "%Y:%m:%d %H:%M:%S%z",
        "%Y:%m:%d %H:%M:%S.%f",
        "%Y:%m:%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(str(raw), fmt)
        except ValueError:
            pass
    raise ValueError(f"unsupported capture timestamp {raw!r}")


def serial_number(filename: str) -> int | None:
    match = re.search(r"(\d+)$", Path(filename).stem)
    return int(match.group(1)) if match else None


def value_counts(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = collections.Counter(
        "<MISSING>" if record.get(key) is None else record[key] for record in records
    )
    return [
        {"value": value, "frame_count": count, "numeric_status": "VERIFIED"}
        for value, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def scalar_values(records: list[dict[str, Any]], key: str) -> str:
    values = sorted(
        {
            "<MISSING>" if record.get(key) is None else str(record[key])
            for record in records
        }
    )
    return "|".join(values)


def infer_step_width(relative_path: str) -> dict[str, Any]:
    matches = re.findall(
        r"(?:^|[-\\])sw(\d+)(?:[-\\]|$)", relative_path.lower()
    )
    values = sorted({int(value) for value in matches})
    if len(values) == 1:
        return {
            "value": values[0],
            "status": "INHERITED",
            "source": relative_path,
            "basis": "directory-name label; Sony EXIF does not expose step width",
        }
    return {
        "value": None,
        "status": "not_recoverable",
        "source": relative_path,
        "basis": "not encoded in the path and not exposed by Sony EXIF",
    }


def cpl_classification(relative_path: str, capture_root: Path) -> dict[str, str]:
    lower = relative_path.lower()
    if "subject-focus-sweep-no-cpl" in lower:
        return {
            "value": "no",
            "source": relative_path,
            "basis": "directory-name label",
        }
    if "subject-focus-sweep-with-cpl" in lower:
        return {
            "value": "yes",
            "source": relative_path,
            "basis": "directory-name label",
        }
    if lower == r"flat-fields\flat-fields":
        return {
            "value": "mixed",
            "source": r"experiments\BUILD-DEFECT\src\44-cpl-label.py",
            "basis": "capture timeline labels block 1 with CPL and block 2 bare",
        }
    if lower.startswith(r"requests\6-11-extended-dark-frames"):
        return {
            "value": "not_applicable",
            "source": str(capture_root / "requests" / "6-11-extended-dark-frames" / "README.md"),
            "basis": "lens-capped dark capture",
        }
    if "-cpl" in lower:
        return {
            "value": "yes",
            "source": relative_path,
            "basis": "directory-name label",
        }
    if lower.startswith(r"requests\10-paper-iso-var"):
        return {
            "value": "yes",
            "source": str(capture_root / "requests" / "10-paper-iso-var" / "README.md"),
            "basis": "capture README",
        }
    if lower.startswith(
        r"requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
    ):
        return {
            "value": "yes",
            "source": str(
                capture_root
                / "requests"
                / "12-bee-iso-var-no-bracket-32-repeat-diff-light"
                / "README.md"
            ),
            "basis": "capture README",
        }
    if lower in {"109msdcf", "112msdcf", "113msdcf", "119msdcf"}:
        return {
            "value": "no",
            "source": r"experiments\m61-ptc-high-iso\src\18-cpl-date-rule.py",
            "basis": "owner-supplied CPL date rule, checked against EXIF dates",
        }
    if lower == "coffee-bean":
        return {
            "value": "unknown",
            "source": r"experiments\m61-ptc-high-iso\src\18-cpl-date-rule.py",
            "basis": "owner could not recall this stack",
        }
    if lower in {"coffee-bubbles", "foam", "wrapped-text-1", "wrapped-text-2"}:
        return {
            "value": "yes",
            "source": r"experiments\m61-ptc-high-iso\src\18-cpl-date-rule.py",
            "basis": "owner-supplied CPL date rule, checked against EXIF dates",
        }
    return {
        "value": "unknown",
        "source": relative_path,
        "basis": "no physical filter state in EXIF or capture-side label",
    }


def subject_name(relative_path: str) -> str:
    lower = relative_path.lower()
    mapping = (
        (r"requests\10-paper-iso-var", "printer paper"),
        (
            r"requests\12-bee-iso-var-no-bracket-32-repeat-diff-light",
            "bee head",
        ),
        (r"requests\19-razor-edge", "razor edge"),
        (r"requests\30-calibration-grid", "microscope calibration grid"),
        (r"requests\6-11-extended-dark-frames", "lens-capped dark frames"),
        (r"requests\7-aperture-pairs", "fabric weave"),
        (r"requests\8-tilted-planar", "inclined metal ruler"),
        (
            r"requests\misc-diagnostic\flat-round-3v-battery-cpl",
            "round 3V battery",
        ),
        (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl",
            "high-resolution calibration slide",
        ),
        (
            r"requests\misc-diagnostic\razor-flat-vertical-slightly-tilted-sw1-cpl",
            "razor edge",
        ),
    )
    for prefix, subject in mapping:
        if lower.startswith(prefix):
            return subject
    return Path(relative_path).name


def request_group(relative_path: str) -> str | None:
    parts = Path(relative_path).parts
    if not parts or parts[0].lower() != "requests":
        return None
    return parts[1] if len(parts) > 1 else "requests"


def setting_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("ISO"),
        record.get("ExposureTime"),
        record.get("FNumber"),
        record.get("FocalLength"),
        record.get("ImageStabilization"),
        record.get("ReleaseMode"),
    )


def make_segments(
    stack_id: str, records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    segments: list[list[dict[str, Any]]] = []
    for record in records:
        if not segments or setting_key(segments[-1][-1]) != setting_key(record):
            segments.append([record])
        else:
            segments[-1].append(record)
    output = []
    for index, segment in enumerate(segments, start=1):
        first = segment[0]
        last = segment[-1]
        output.append(
            {
                "stack_id": stack_id,
                "segment_index": index,
                "frame_count": len(segment),
                "first_file": first["FileName"],
                "last_file": last["FileName"],
                "first_capture_at": first["_capture_time_text"],
                "last_capture_at": last["_capture_time_text"],
                "iso": first.get("ISO"),
                "exposure_seconds": first.get("ExposureTime"),
                "aperture": first.get("FNumber"),
                "focal_length_mm": first.get("FocalLength"),
                "image_stabilization": first.get("ImageStabilization"),
                "release_mode": first.get("ReleaseMode"),
                "numeric_status": "VERIFIED",
            }
        )
    return output


def stack_record(
    capture_root: Path,
    directory: Path,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    relative_path = normalise_path(directory.relative_to(capture_root))
    stack_id = relative_path
    records = sorted(records, key=lambda record: record["FileName"].lower())
    for record in records:
        timestamp = parse_capture_time(record)
        record["_capture_time"] = timestamp
        record["_capture_time_text"] = (
            record.get("SubSecDateTimeOriginal")
            or record.get("DateTimeOriginal")
        )

    serials = [serial_number(record["FileName"]) for record in records]
    serials_present = all(value is not None for value in serials)
    filename_contiguous = bool(serials_present) and all(
        right == left + 1 for left, right in zip(serials, serials[1:])
    )
    gaps = [
        (right["_capture_time"] - left["_capture_time"]).total_seconds()
        for left, right in zip(records, records[1:])
    ]
    timestamp_monotonic = all(gap >= 0 for gap in gaps)
    positive_gaps = [gap for gap in gaps if gap >= 0]
    median_gap = statistics.median(positive_gaps) if positive_gaps else 0.0
    max_gap = max(positive_gaps) if positive_gaps else 0.0
    exposure_values = [
        float(record["ExposureTime"])
        for record in records
        if record.get("ExposureTime") is not None
    ]
    max_exposure = max(exposure_values, default=0.0)
    continuity_threshold = max(60.0, 10.0 * median_gap, 2.0 * max_exposure + 10.0)
    break_rows = []
    for left, right, gap in zip(records, records[1:], gaps):
        if gap > continuity_threshold:
            break_rows.append(
                {
                    "after_file": left["FileName"],
                    "before_file": right["FileName"],
                    "gap_seconds": gap,
                    "numeric_status": "VERIFIED",
                }
            )
    capture_contiguous = (
        filename_contiguous and timestamp_monotonic and not break_rows
    )
    duration = (
        records[-1]["_capture_time"] - records[0]["_capture_time"]
    ).total_seconds()
    step_width = infer_step_width(relative_path)
    cpl = cpl_classification(relative_path, capture_root)
    segments = make_segments(stack_id, records)
    all_files = [item for item in directory.iterdir() if item.is_file()]
    arw_files = [item for item in all_files if item.suffix.lower() == ".arw"]
    source_files = {normalise_path(record["SourceFile"]).lower() for record in records}
    actual_files = {normalise_path(item).lower() for item in arw_files}
    if source_files != actual_files:
        missing = sorted(actual_files - source_files)
        extra = sorted(source_files - actual_files)
        raise RuntimeError(
            f"ExifTool/filesystem mismatch for {directory}: "
            f"missing={missing[:3]} extra={extra[:3]}"
        )
    return (
        {
            "stack_id": stack_id,
            "scope": "request" if request_group(relative_path) else "general",
            "request_group": request_group(relative_path),
            "subject_or_name": subject_name(relative_path),
            "path": str(directory),
            "frame_count": len(records),
            "first_file": records[0]["FileName"],
            "last_file": records[-1]["FileName"],
            "first_capture_at": records[0]["_capture_time_text"],
            "last_capture_at": records[-1]["_capture_time_text"],
            "duration_seconds": duration,
            "capture_contiguous": capture_contiguous,
            "filename_sequence_contiguous": filename_contiguous,
            "timestamp_monotonic": timestamp_monotonic,
            "median_gap_seconds": median_gap,
            "max_gap_seconds": max_gap,
            "continuity_threshold_seconds": continuity_threshold,
            "continuity_breaks": break_rows,
            "settings": {
                "iso": value_counts(records, "ISO"),
                "exposure_seconds": value_counts(records, "ExposureTime"),
                "aperture": value_counts(records, "FNumber"),
                "focal_length_mm": value_counts(records, "FocalLength"),
                "focus_distance_m": value_counts(records, "FocusDistance2"),
                "focus_position_2": value_counts(records, "FocusPosition2"),
                "image_stabilization": value_counts(
                    records, "_formatted_ImageStabilization"
                ),
                "release_mode": value_counts(records, "_formatted_ReleaseMode"),
                "lens_model": value_counts(records, "LensModel"),
                "camera_model": value_counts(records, "_formatted_Model"),
            },
            "step_width": step_width,
            "cpl": cpl,
            "magnification": {
                "value": None,
                "status": "not_recoverable_from_metadata",
                "source": str(directory),
                "basis": (
                    "Sony RAW metadata supplies focal length and coarse focus "
                    "distance, not an independently measured reproduction ratio"
                ),
            },
            "setting_segment_count": len(segments),
            "arw_bytes": sum(item.stat().st_size for item in arw_files),
            "other_file_count": len(all_files) - len(arw_files),
            "numeric_status": "VERIFIED",
            "numeric_source": "ExifTool metadata and recursive filesystem enumeration",
        },
        segments,
    )


def flatten_stack(record: dict[str, Any]) -> dict[str, Any]:
    settings = record["settings"]
    return {
        "stack_id": record["stack_id"],
        "scope": record["scope"],
        "request_group": record["request_group"],
        "subject_or_name": record["subject_or_name"],
        "path": record["path"],
        "frame_count": record["frame_count"],
        "first_file": record["first_file"],
        "last_file": record["last_file"],
        "first_capture_at": record["first_capture_at"],
        "last_capture_at": record["last_capture_at"],
        "duration_seconds": record["duration_seconds"],
        "capture_contiguous": record["capture_contiguous"],
        "filename_sequence_contiguous": record["filename_sequence_contiguous"],
        "timestamp_monotonic": record["timestamp_monotonic"],
        "median_gap_seconds": record["median_gap_seconds"],
        "max_gap_seconds": record["max_gap_seconds"],
        "continuity_threshold_seconds": record["continuity_threshold_seconds"],
        "iso_values": scalar_values_from_counts(settings["iso"]),
        "exposure_seconds_values": scalar_values_from_counts(
            settings["exposure_seconds"]
        ),
        "aperture_values": scalar_values_from_counts(settings["aperture"]),
        "focal_length_mm_values": scalar_values_from_counts(
            settings["focal_length_mm"]
        ),
        "focus_distance_m_values": scalar_values_from_counts(
            settings["focus_distance_m"]
        ),
        "image_stabilization_values": scalar_values_from_counts(
            settings["image_stabilization"]
        ),
        "release_mode_values": scalar_values_from_counts(
            settings["release_mode"]
        ),
        "step_width": record["step_width"]["value"],
        "step_width_status": record["step_width"]["status"],
        "cpl": record["cpl"]["value"],
        "cpl_source": record["cpl"]["source"],
        "magnification": record["magnification"]["value"],
        "magnification_status": record["magnification"]["status"],
        "setting_segment_count": record["setting_segment_count"],
        "arw_bytes": record["arw_bytes"],
        "other_file_count": record["other_file_count"],
        "numeric_status": record["numeric_status"],
    }


def scalar_values_from_counts(counts: list[dict[str, Any]]) -> str:
    return "|".join(str(item["value"]) for item in counts)


def slide_characterisation(
    capture_root: Path, stacks: list[dict[str, Any]]
) -> dict[str, Any]:
    prefix = (
        r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
    )
    rows = {
        record["stack_id"]: record
        for record in stacks
        if record["stack_id"].lower().startswith(prefix)
    }
    expected_suffixes = {
        "flat": (
            r"flat-sw4-cpl\flat-et6s-sw4-cpl",
            r"flat-sw4-cpl\flat-et2.5s-sw4-cpl",
            r"flat-sw4-cpl\flat-et1s-sw4-cpl",
        ),
        "tilted-sw4": (r"tilted-sw4-cpl",),
        "tilted-sw10": (r"tilted-sw10-cpl",),
        "very-tilted-all-axis-sw10": (
            r"very-tilted-all-axis-sw10-cpl",
        ),
    }
    science = {
        "flat": (
            "Natural depth-null and real-photon SNR ladder; useful for "
            "flat-path identity, cover/resampling diagnostics, and detecting "
            "invented structure. The three exposure settings are not matched "
            "repeat realizations."
        ),
        "tilted-sw4": (
            "Dense monotonic depth ramp for development-only coverage, "
            "planarity/order, and geometry commissioning; paired with "
            "tilted-sw10 it is a denser-sampling optical-improvement arm."
        ),
        "tilted-sw10": (
            "Sparse monotonic depth ramp for development-only coverage "
            "commissioning and the lower-sampling member of the sw4/sw10 "
            "optical-improvement pair."
        ),
        "very-tilted-all-axis-sw10": (
            "Strong all-axis depth ramp for development-only field geometry, "
            "plane/order, and difficult coverage commissioning; its geometry "
            "differs from tilted-sw10, so it is not a repeat."
        ),
    }
    output: dict[str, Any] = {}
    all_members: list[dict[str, Any]] = []
    for label, suffixes in expected_suffixes.items():
        members = []
        for suffix in suffixes:
            stack_id = prefix + "\\" + suffix
            if stack_id not in rows:
                raise RuntimeError(f"missing expected slide stack: {stack_id}")
            members.append(rows[stack_id])
        all_members.extend(members)
        output[label] = {
            "path": (
                str(
                    capture_root
                    / Path(prefix)
                    / ("flat-sw4-cpl" if label == "flat" else suffixes[0])
                )
            ),
            "member_stack_ids": [member["stack_id"] for member in members],
            "frame_count": sum(member["frame_count"] for member in members),
            "step_width": members[0]["step_width"],
            "tilt_condition": {
                "flat": "flat/fronto-parallel plane",
                "tilted-sw4": "tilted plane",
                "tilted-sw10": "tilted plane",
                "very-tilted-all-axis-sw10": "very tilted on x/y/z axes",
            }[label],
            "exposure_seconds": sorted(
                {
                    item["value"]
                    for member in members
                    for item in member["settings"]["exposure_seconds"]
                    if item["value"] != "<MISSING>"
                }
            ),
            "first_capture_at": min(member["first_capture_at"] for member in members),
            "last_capture_at": max(member["last_capture_at"] for member in members),
            "all_member_stacks_contiguous": all(
                member["capture_contiguous"] for member in members
            ),
            "member_stack_count": len(members),
            "scientific_use": science[label],
            "numeric_status": "VERIFIED",
            "science_status": "INHERITED",
            "science_sources": [
                r"docs\STATUS.md:2496-2551",
                r"docs\proposals\2026-09-sota-scorecard.md:283-288",
                r"docs\proposals\2026-09-sota-scorecard.md:337-350",
            ],
        }
    ordered = sorted(all_members, key=lambda record: record["first_capture_at"])
    inter_stack_gaps = []
    for left, right in zip(ordered, ordered[1:]):
        left_time = parse_timestamp_text(left["last_capture_at"])
        right_time = parse_timestamp_text(right["first_capture_at"])
        inter_stack_gaps.append(
            {
                "from": left["stack_id"],
                "to": right["stack_id"],
                "seconds": (right_time - left_time).total_seconds(),
                "numeric_status": "VERIFIED",
            }
        )
    return {
        "four_directory_groups": output,
        "six_stack_session": {
            "frame_count": sum(member["frame_count"] for member in all_members),
            "first_capture_at": ordered[0]["first_capture_at"],
            "last_capture_at": ordered[-1]["last_capture_at"],
            "inter_stack_gaps": inter_stack_gaps,
            "physical_session_ruling": "one session unit",
            "holdout_ruling": "BURNED — deliberately spent development; not holdout",
            "ruling_status": "INHERITED",
            "ruling_sources": [
                r"docs\proposals\2026-09-sota-scorecard.md:36-41",
                r"docs\proposals\2026-09-sota-scorecard.md:337-350",
                r"docs\STATUS.md:2535-2551",
                r"experiments\cover-default\slide-series-preregistration.md:9-15",
            ],
        },
    }


def parse_timestamp_text(raw: str) -> datetime:
    for fmt in (
        "%Y:%m:%d %H:%M:%S.%f%z",
        "%Y:%m:%d %H:%M:%S%z",
        "%Y:%m:%d %H:%M:%S.%f",
        "%Y:%m:%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    raise ValueError(raw)


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(
    capture_root: Path,
    edited_root: Path,
    exiftool: Path,
    output_dir: Path,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not capture_root.is_dir():
        raise RuntimeError(f"missing capture root: {capture_root}")
    if not edited_root.is_dir():
        raise RuntimeError(f"missing edited root: {edited_root}")
    if not exiftool.is_file():
        raise RuntimeError(f"missing ExifTool: {exiftool}")

    before = {
        str(capture_root): tree_snapshot(capture_root),
        str(capture_root / "requests"): tree_snapshot(capture_root / "requests"),
        str(edited_root): tree_snapshot(edited_root),
    }
    records = run_exiftool(
        exiftool,
        capture_root,
        numeric=True,
        tags=EXIF_TAGS,
    )
    formatted_records = run_exiftool(
        exiftool,
        capture_root,
        numeric=False,
        tags=(
            "FileName",
            "Directory",
            "ImageStabilization",
            "ReleaseMode",
            "LensType3",
            "Model",
            "SequenceLength",
        ),
    )
    formatted_by_source = {
        normalise_path(record["SourceFile"]).lower(): record
        for record in formatted_records
    }
    if len(formatted_by_source) != len(records):
        raise RuntimeError(
            "numeric/formatted ExifTool record counts differ: "
            f"{len(records)} != {len(formatted_by_source)}"
        )
    for record in records:
        source = normalise_path(record["SourceFile"]).lower()
        formatted = formatted_by_source.get(source)
        if formatted is None:
            raise RuntimeError(f"missing formatted ExifTool record: {source}")
        for key, value in formatted.items():
            if key not in {"SourceFile", "FileName", "Directory"}:
                record[f"_formatted_{key}"] = value
    by_directory: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for record in records:
        directory = normalise_path(record.get("Directory") or Path(record["SourceFile"]).parent)
        by_directory[directory.lower()].append(record)

    stacks = []
    segments = []
    for directory_key in sorted(by_directory):
        stack, stack_segments = stack_record(
            capture_root,
            Path(normalise_path(by_directory[directory_key][0]["Directory"])),
            by_directory[directory_key],
        )
        stacks.append(stack)
        segments.extend(stack_segments)

    filesystem_arws = list(capture_root.rglob("*.ARW"))
    if len(filesystem_arws) != len(records):
        raise RuntimeError(
            f"ARW count mismatch: filesystem={len(filesystem_arws)} "
            f"ExifTool={len(records)}"
        )
    after = {
        str(capture_root): tree_snapshot(capture_root),
        str(capture_root / "requests"): tree_snapshot(capture_root / "requests"),
        str(edited_root): tree_snapshot(edited_root),
    }
    unchanged = before == after
    if not unchanged:
        raise RuntimeError("read-only source tree snapshot changed during inventory")

    manifest = {
        "schema": "M141-capture-inventory-v1",
        "scope": {
            "capture_root": str(capture_root),
            "definition": (
                "one stack entry per directory containing one or more ARW files"
            ),
            "metadata_only": True,
            "pixels_read": False,
            "stacker_run": False,
        },
        "method": {
            "exiftool": str(exiftool),
            "exiftool_version": subprocess.run(
                [str(exiftool), "-ver"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            ).stdout.strip(),
            "tags": list(EXIF_TAGS),
            "continuity": (
                "VERIFIED yes only when DSC file numbers are consecutive, EXIF "
                "times are monotonic, and no inter-frame gap exceeds max(60 s, "
                "10x the median gap, 2x the longest exposure + 10 s)."
            ),
            "step_width": (
                "INHERITED from an swN path label; Sony EXIF has no usable "
                "step-width field."
            ),
            "magnification": (
                "Not recovered: Sony EXIF records focal length and coarse focus "
                "distance, not independently measured reproduction ratio."
            ),
        },
        "summary": {
            "stack_directory_count": len(stacks),
            "request_stack_directory_count": sum(
                stack["scope"] == "request" for stack in stacks
            ),
            "general_stack_directory_count": sum(
                stack["scope"] == "general" for stack in stacks
            ),
            "arw_frame_count": len(records),
            "request_arw_frame_count": sum(
                stack["frame_count"]
                for stack in stacks
                if stack["scope"] == "request"
            ),
            "general_arw_frame_count": sum(
                stack["frame_count"]
                for stack in stacks
                if stack["scope"] == "general"
            ),
            "all_arw_image_stabilization": sorted(
                {
                    item["value"]
                    for stack in stacks
                    for item in stack["settings"]["image_stabilization"]
                }
            ),
            "numeric_status": "VERIFIED",
        },
        "source_tree_before": before,
        "source_tree_after": after,
        "source_trees_unchanged_during_inventory": unchanged,
        "stacks": stacks,
        "setting_segments": segments,
        "new_slide": slide_characterisation(capture_root, stacks),
    }
    manifest_path = output_dir / "capture-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_csv(
        output_dir / "capture-stacks.csv",
        CSV_FIELDS,
        [flatten_stack(record) for record in stacks],
    )
    write_csv(output_dir / "capture-segments.csv", SEGMENT_FIELDS, segments)
    checks = {
        "schema": "M141-inventory-checks-v1",
        "manifest": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "stack_directory_count": len(stacks),
        "request_stack_directory_count": sum(
            stack["scope"] == "request" for stack in stacks
        ),
        "general_stack_directory_count": sum(
            stack["scope"] == "general" for stack in stacks
        ),
        "arw_frame_count": len(records),
        "stack_frame_sum": sum(stack["frame_count"] for stack in stacks),
        "all_filename_sequences_contiguous": all(
            stack["filename_sequence_contiguous"] for stack in stacks
        ),
        "noncontiguous_stack_ids": [
            stack["stack_id"]
            for stack in stacks
            if not stack["capture_contiguous"]
        ],
        "source_trees_unchanged_during_inventory": unchanged,
        "new_slide_frame_count": manifest["new_slide"]["six_stack_session"][
            "frame_count"
        ],
        "numeric_status": "VERIFIED",
    }
    (output_dir / "inventory-checks.json").write_text(
        json.dumps(checks, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(checks, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--edited-root", type=Path, default=DEFAULT_EDITED_ROOT)
    parser.add_argument("--exiftool", type=Path, default=DEFAULT_EXIFTOOL)
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    return run(
        args.capture_root.resolve(),
        args.edited_root.resolve(),
        args.exiftool.resolve(),
        args.output_dir.resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
