from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
OUT = HERE / "out"
CAPTURE_ROOT = Path(r"D:\personal\macro").resolve()
PROHIBITED_ROOT = Path(
    r"D:\personal\macro\requests\7-aperture-pairs"
).resolve()
M152 = PROJECT / "experiments" / "M152-site-census"

EXPECTED_HASHES = {
    "census-definition.json": (
        "b2e872a6a8214d4fbe379287f52fc57b8f5e61f292aab4c30e96b11d49325879"
    ),
    "census_common.py": (
        "3e36a18d8c7b675f224f4fbe694ef2d16297e3e038df18e61cdb4dead219a680"
    ),
    "m4-freeze.json": (
        "a92b49bd2dc0a661b3319f96e54c7514994292f17f5a0ac0bab0d12cf7cb8d5c"
    ),
}

DETAIL_SPECS = [
    {
        "stack_id": "medication-pill-cpl",
        "geometry": "flat/background sites around medication pill",
        "role": "scored-flat",
        "step_width": None,
        "step_width_status": "not recoverable from path or Sony EXIF",
    },
    {
        "stack_id": "bee-1-cpl",
        "geometry": "flat background sites within bee stack",
        "role": "scored-flat",
        "step_width": None,
        "step_width_status": "not recoverable from path or Sony EXIF",
    },
    {
        "stack_id": "foam",
        "geometry": "fronto-parallel textured foam subject",
        "role": "scored-flat",
        "step_width": None,
        "step_width_status": "not recoverable from path or Sony EXIF",
    },
    {
        "stack_id": "coffee-bubbles",
        "geometry": "fronto-parallel flat-category development subject",
        "role": "development-flat",
        "step_width": None,
        "step_width_status": "fixed focus; no bracket width applies",
    },
    {
        "stack_id": r"flat-fields\flat-fields",
        "geometry": "fronto-parallel defocused paper flat",
        "role": "development-flat-candidate",
        "step_width": None,
        "step_width_status": "fixed focus; no bracket width applies",
    },
    {
        "stack_id": r"flat-fields\subject-focus-sweep-no-cpl",
        "geometry": "fronto-parallel paper focus sweep without CPL",
        "role": "development-flat-candidate",
        "step_width": None,
        "step_width_status": "not recoverable from path or Sony EXIF",
    },
    {
        "stack_id": r"flat-fields\subject-focus-sweep-with-cpl",
        "geometry": "fronto-parallel paper focus sweep with CPL",
        "role": "development-flat-candidate",
        "step_width": None,
        "step_width_status": "not recoverable from path or Sony EXIF",
    },
    {
        "stack_id": r"requests\10-paper-iso-var",
        "geometry": "fronto-parallel paper, fixed focus",
        "role": "development-flat-candidate",
        "step_width": None,
        "step_width_status": "fixed focus; no bracket width applies",
    },
    {
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\flat-sw4-cpl\flat-et1s-sw4-cpl"
        ),
        "geometry": "flat/fronto-parallel calibration slide",
        "role": "development-flat",
        "step_width": 4,
        "step_width_status": "inherited from unique sw4 path label",
    },
    {
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\flat-sw4-cpl\flat-et2.5s-sw4-cpl"
        ),
        "geometry": "flat/fronto-parallel calibration slide",
        "role": "development-flat",
        "step_width": 4,
        "step_width_status": "inherited from unique sw4 path label",
    },
    {
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\flat-sw4-cpl\flat-et6s-sw4-cpl"
        ),
        "geometry": "flat/fronto-parallel calibration slide",
        "role": "development-flat",
        "step_width": 4,
        "step_width_status": "inherited from unique sw4 path label",
    },
    {
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\tilted-sw4-cpl"
        ),
        "geometry": "tilted calibration slide",
        "role": "inventory-only",
        "step_width": 4,
        "step_width_status": "inherited from unique sw4 path label",
    },
    {
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\tilted-sw10-cpl"
        ),
        "geometry": "tilted calibration slide",
        "role": "inventory-only",
        "step_width": 10,
        "step_width_status": "inherited from unique sw10 path label",
    },
    {
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\very-tilted-all-axis-sw10-cpl"
        ),
        "geometry": "very tilted calibration slide on all axes",
        "role": "inventory-only",
        "step_width": 10,
        "step_width_status": "inherited from unique sw10 path label",
    },
]

PROBE_SPECS = [
    {
        "unit_id": "score-medication-pill",
        "stack_id": "medication-pill-cpl",
        "role": "scored-flat",
        "quota": 84,
        "selection": "all",
    },
    {
        "unit_id": "score-bee-background",
        "stack_id": "bee-1-cpl",
        "role": "scored-flat",
        "quota": 83,
        "selection": "all",
    },
    {
        "unit_id": "score-foam",
        "stack_id": "foam",
        "role": "scored-flat",
        "quota": 83,
        "selection": "all",
    },
    {
        "unit_id": "development-coffee-bubbles",
        "stack_id": "coffee-bubbles",
        "role": "development-flat",
        "quota": 100,
        "selection": "all",
    },
    {
        "unit_id": "development-paper-sweep-no-cpl",
        "stack_id": r"flat-fields\subject-focus-sweep-no-cpl",
        "role": "development-flat",
        "quota": 100,
        "selection": "all",
    },
    {
        "unit_id": "development-paper-sweep-with-cpl",
        "stack_id": r"flat-fields\subject-focus-sweep-with-cpl",
        "role": "development-flat",
        "quota": 100,
        "selection": "all",
    },
    {
        "unit_id": "development-slide-flat-et1s",
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\flat-sw4-cpl\flat-et1s-sw4-cpl"
        ),
        "role": "development-flat",
        "quota": 100,
        "selection": "all",
    },
    {
        "unit_id": "development-slide-flat-et2p5s",
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\flat-sw4-cpl\flat-et2.5s-sw4-cpl"
        ),
        "role": "development-flat",
        "quota": 100,
        "selection": "all",
    },
    {
        "unit_id": "development-slide-flat-et6s",
        "stack_id": (
            r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
            r"\flat-sw4-cpl\flat-et6s-sw4-cpl"
        ),
        "role": "development-flat",
        "quota": 100,
        "selection": "all",
    },
]

EXIF_TAGS = [
    "FileName",
    "ISO",
    "ExposureTime",
    "FNumber",
    "FocalLength",
    "FocusDistance2",
    "FocusPosition2",
    "FocusMode",
    "ImageStabilization",
    "ReleaseMode",
    "DateTimeOriginal",
    "SubSecTimeOriginal",
    "Model",
    "LensModel",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )


def json_content_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def compact_census_result(result: dict[str, Any]) -> dict[str, Any]:
    compact = dict(result)
    for key in ("decoded_inputs", "eligible_sites_quality_order"):
        rows = compact.pop(key, [])
        compact[f"{key}_count"] = len(rows)
        compact[f"{key}_content_sha256"] = json_content_sha256(rows)
        compact[f"{key}_preview"] = rows[:2]
    return compact


def is_prohibited(path: Path) -> bool:
    path = path.resolve()
    return path == PROHIBITED_ROOT or PROHIBITED_ROOT in path.parents


def require_allowed(path: Path) -> Path:
    path = path.resolve()
    if is_prohibited(path):
        raise RuntimeError(f"prohibited holdout path refused: {path}")
    try:
        path.relative_to(CAPTURE_ROOT)
    except ValueError as error:
        raise RuntimeError(f"path is outside the read-only capture root: {path}") from error
    return path


def stack_path(stack_id: str) -> Path:
    return require_allowed(CAPTURE_ROOT / Path(stack_id))


def enumerate_stacks() -> list[dict[str, Any]]:
    pending = [CAPTURE_ROOT]
    rows: list[dict[str, Any]] = []
    while pending:
        directory = require_allowed(pending.pop())
        entries = list(os.scandir(directory))
        files = sorted(
            (
                Path(entry.path)
                for entry in entries
                if entry.is_file(follow_symlinks=False)
                and entry.name.lower().endswith(".arw")
            ),
            key=lambda value: value.name.lower(),
        )
        if files:
            rows.append(
                {
                    "stack_id": str(directory.relative_to(CAPTURE_ROOT)),
                    "path": str(directory),
                    "frame_count": len(files),
                    "first_file": files[0].name,
                    "last_file": files[-1].name,
                }
            )
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            child = Path(entry.path).resolve()
            if is_prohibited(child):
                continue
            pending.append(child)
    return sorted(rows, key=lambda row: row["stack_id"].lower())


def exif_rows(directory: Path) -> list[dict[str, Any]]:
    directory = require_allowed(directory)
    tool = shutil.which("exiftool")
    if tool is None:
        raise RuntimeError("exiftool is not available")
    command = [tool, "-json", "-n", "-ext", "ARW"]
    command.extend(f"-{tag}" for tag in EXIF_TAGS)
    command.append(str(directory))
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    rows = json.loads(completed.stdout)
    rows.sort(key=lambda row: str(row["FileName"]).lower())
    if not rows:
        raise RuntimeError(f"no ARWs found in {directory}")
    return rows


def value_counts(rows: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(
        "<MISSING>" if row.get(key) is None else row.get(key) for row in rows
    )
    return [
        {"value": value, "frame_count": count}
        for value, count in sorted(counts.items(), key=lambda item: str(item[0]))
    ]


def exif_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "frame_count": len(rows),
        "first_file": rows[0]["FileName"],
        "last_file": rows[-1]["FileName"],
        "settings": {
            key: value_counts(rows, key)
            for key in (
                "ISO",
                "ExposureTime",
                "FNumber",
                "FocalLength",
                "FocusDistance2",
                "FocusPosition2",
                "FocusMode",
                "ImageStabilization",
                "ReleaseMode",
                "Model",
                "LensModel",
            )
        },
        "first_capture_at": capture_time_text(rows[0]),
        "last_capture_at": capture_time_text(rows[-1]),
    }


def capture_time_text(row: dict[str, Any]) -> str | None:
    base = row.get("DateTimeOriginal")
    if base is None:
        return None
    sub = str(row.get("SubSecTimeOriginal", "")).strip()
    return f"{base}.{sub}" if sub else str(base)


def capture_time(row: dict[str, Any]) -> datetime | None:
    text = capture_time_text(row)
    if text is None:
        return None
    base, _, fractional = text.partition(".")
    parsed = datetime.strptime(base, "%Y:%m:%d %H:%M:%S")
    if fractional:
        parsed = parsed.replace(microsecond=int((fractional + "000000")[:6]))
    return parsed


def continuity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = [capture_time(row) for row in rows]
    if any(value is None for value in times):
        return {
            "capture_contiguous": False,
            "reason": "missing DateTimeOriginal",
        }
    concrete = [value for value in times if value is not None]
    gaps = [
        (right - left).total_seconds()
        for left, right in zip(concrete, concrete[1:])
    ]
    if any(value < 0 for value in gaps):
        return {
            "capture_contiguous": False,
            "reason": "capture timestamps are not monotone",
        }
    positive = [value for value in gaps if value > 0]
    median_gap = statistics.median(positive) if positive else 0.0
    exposures = [
        float(row["ExposureTime"])
        for row in rows
        if row.get("ExposureTime") is not None
    ]
    threshold = max(
        60.0,
        10.0 * median_gap,
        2.0 * max(exposures, default=0.0) + 10.0,
    )
    maximum_gap = max(positive, default=0.0)
    return {
        "capture_contiguous": maximum_gap <= threshold,
        "median_positive_gap_seconds": median_gap,
        "maximum_positive_gap_seconds": maximum_gap,
        "continuity_threshold_seconds": threshold,
    }


def homogeneous_segments(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    keys = ("ISO", "ExposureTime", "FNumber", "FocalLength")
    segments: list[list[dict[str, Any]]] = []
    for row in rows:
        signature = tuple(row.get(key) for key in keys)
        if (
            not segments
            or tuple(segments[-1][-1].get(key) for key in keys) != signature
        ):
            segments.append([row])
        else:
            segments[-1].append(row)
    return segments


def detailed_inventory() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    details: list[dict[str, Any]] = []
    cache: dict[str, list[dict[str, Any]]] = {}
    for spec in DETAIL_SPECS:
        directory = stack_path(spec["stack_id"])
        rows = exif_rows(directory)
        cache[spec["stack_id"]] = rows
        detail = dict(spec)
        detail["path"] = str(directory)
        detail["exif"] = exif_summary(rows)
        detail["continuity"] = continuity(rows)
        details.append(detail)
    return details, cache


def inventory() -> dict[str, Any]:
    started = time.perf_counter()
    stacks = enumerate_stacks()
    details, _ = detailed_inventory()
    artifact = {
        "schema": "m181-m4-flat-inventory-v1",
        "capture_root": str(CAPTURE_ROOT),
        "prohibited_root": str(PROHIBITED_ROOT),
        "prohibited_root_descended": False,
        "stack_directory_count_excluding_prohibited": len(stacks),
        "arw_frame_count_excluding_prohibited": sum(
            int(row["frame_count"]) for row in stacks
        ),
        "stacks": stacks,
        "detailed_flat_and_slide_stacks": details,
        "elapsed_seconds": time.perf_counter() - started,
    }
    write_json(OUT / "inventory.json", artifact)
    print(
        "inventory: "
        f"{artifact['stack_directory_count_excluding_prohibited']} stacks, "
        f"{artifact['arw_frame_count_excluding_prohibited']} ARWs"
    )
    return artifact


def load_m152() -> tuple[Any, Any, dict[str, Any], dict[str, str]]:
    actual_hashes = {
        name: sha256_file(M152 / name) for name in EXPECTED_HASHES
    }
    if actual_hashes != EXPECTED_HASHES:
        raise RuntimeError(
            f"M152 frozen dependency hash mismatch: {actual_hashes!r}"
        )
    sys.path.insert(0, str(M152))
    try:
        import census  # type: ignore
        import census_common  # type: ignore
    finally:
        sys.path.pop(0)
    definition, definition_hash = census_common.load_definition()
    if definition_hash != EXPECTED_HASHES["census-definition.json"]:
        raise RuntimeError("loaded M152 definition hash differs from frozen hash")
    noise = json.loads(
        (M152 / "out" / "noise-calibration.json").read_text(encoding="utf-8")
    )
    if noise["definition_sha256"] != definition_hash:
        raise RuntimeError("M152 noise calibration is bound to another definition")
    return census, census_common, definition, actual_hashes


def select_rows(
    spec: dict[str, Any],
    cache: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = cache[spec["stack_id"]]
    selection = spec["selection"]
    if selection == "all":
        return list(rows)
    if selection["kind"] == "file-list":
        wanted = set(selection["files"])
        chosen = [row for row in rows if row["FileName"] in wanted]
        if len(chosen) != len(wanted):
            raise RuntimeError(f"{spec['unit_id']}: file-list did not resolve")
        return chosen
    raise RuntimeError(f"unknown selection: {selection!r}")


def dynamic_development_specs(
    cache: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    flat_id = r"flat-fields\flat-fields"
    for index, segment in enumerate(homogeneous_segments(cache[flat_id]), start=1):
        halves = [segment]
        if len(segment) == 40:
            halves = [segment[:20], segment[20:]]
        for half_index, rows in enumerate(halves, start=1):
            specs.append(
                {
                    "unit_id": (
                        f"development-flat-fields-segment-{index:02d}"
                        f"-part-{half_index}"
                    ),
                    "stack_id": flat_id,
                    "role": "development-flat",
                    "quota": 100,
                    "selection": {
                        "kind": "file-list",
                        "files": [row["FileName"] for row in rows],
                    },
                }
            )
    paper_id = r"requests\10-paper-iso-var"
    for index, segment in enumerate(homogeneous_segments(cache[paper_id]), start=1):
        iso_values = {row.get("ISO") for row in segment}
        if iso_values.issubset({50, 100, 1000}):
            specs.append(
                {
                    "unit_id": f"development-paper-control-segment-{index:02d}",
                    "stack_id": paper_id,
                    "role": "development-flat",
                    "quota": 100,
                    "selection": {
                        "kind": "file-list",
                        "files": [row["FileName"] for row in segment],
                    },
                }
            )
    return specs


def run_one_probe(
    census: Any,
    definition: dict[str, Any],
    noise: dict[str, Any],
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    directory = stack_path(spec["stack_id"])
    files = [directory / str(row["FileName"]) for row in rows]
    for path in files:
        require_allowed(path)
    iso_values = sorted(
        {float(row["ISO"]) for row in rows if row.get("ISO") is not None}
    )
    if len(iso_values) != 1:
        return {
            "unit_id": spec["unit_id"],
            "stack_id": spec["stack_id"],
            "path": str(directory),
            "role": spec["role"],
            "quota": spec["quota"],
            "selection": spec["selection"],
            "status": "METADATA_INELIGIBLE_VARYING_OR_MISSING_ISO",
            "selected_frame_count": len(rows),
            "iso_values": iso_values,
            "metadata": exif_summary(rows),
        }
    contiguous = continuity(rows)
    if not contiguous["capture_contiguous"]:
        return {
            "unit_id": spec["unit_id"],
            "stack_id": spec["stack_id"],
            "path": str(directory),
            "role": spec["role"],
            "quota": spec["quota"],
            "selection": spec["selection"],
            "status": "METADATA_INELIGIBLE_NONCONTIGUOUS",
            "selected_frame_count": len(rows),
            "iso_values": iso_values,
            "metadata": exif_summary(rows),
            "continuity": contiguous,
        }
    inventory = {
        "path": str(directory),
        "frame_count": len(files),
        "capture_contiguous": True,
        "settings": {"iso": [{"value": iso_values[0], "frame_count": len(files)}]},
    }
    capture = {
        "capture_id": spec["unit_id"],
        "stack_id": spec["stack_id"],
        "path": str(directory),
        "evidence_class": (
            "PROTECTED_INPUT_ONLY"
            if spec["role"] == "scored-flat"
            else "DEVELOPMENT_NOT_HOLDOUT"
        ),
    }
    original_capture_files = census.capture_files

    def selected_capture_files(
        requested_capture: dict[str, Any],
        _: dict[str, dict[str, Any]],
    ) -> tuple[list[Path], dict[str, Any]]:
        if requested_capture["capture_id"] != spec["unit_id"]:
            raise RuntimeError("probe capture substitution")
        return files, inventory

    census.capture_files = selected_capture_files
    started = time.perf_counter()
    try:
        result = census.census_flat_capture(capture, definition, noise, {})
    finally:
        census.capture_files = original_capture_files
    result = compact_census_result(result)
    result.update(
        {
            "unit_id": spec["unit_id"],
            "role": spec["role"],
            "quota": spec["quota"],
            "selection": spec["selection"],
            "status": "MEASURED",
            "selected_frame_count": len(rows),
            "metadata": exif_summary(rows),
            "continuity": contiguous,
            "elapsed_seconds": time.perf_counter() - started,
        }
    )
    return result


def summarize(probes: list[dict[str, Any]]) -> dict[str, Any]:
    measured = {
        row["unit_id"]: row for row in probes if row["status"] == "MEASURED"
    }
    scored_ids = (
        "score-medication-pill",
        "score-bee-background",
        "score-foam",
    )
    scored = {
        unit_id: {
            "eligible": int(measured[unit_id]["eligible_site_count"]),
            "quota": int(measured[unit_id]["quota"]),
            "shortfall": max(
                0,
                int(measured[unit_id]["quota"])
                - int(measured[unit_id]["eligible_site_count"]),
            ),
        }
        for unit_id in scored_ids
    }
    development = [
        {
            "unit_id": row["unit_id"],
            "eligible": int(row["eligible_site_count"]),
            "quota": int(row["quota"]),
        }
        for row in probes
        if row["role"] == "development-flat" and row["status"] == "MEASURED"
    ]
    development.sort(key=lambda row: (-row["eligible"], row["unit_id"]))
    scored_raw_ready = all(row["shortfall"] == 0 for row in scored.values())
    development_raw_ready = any(
        row["eligible"] >= row["quota"] for row in development
    )
    return {
        "eligibility_scope": (
            "M152 RAW green flat-site eligibility only; M166 RGB transfer-plant "
            "rail-margin eligibility remains unmeasured until common TIFFs exist"
        ),
        "scored": scored,
        "selected_scored_sites": sum(
            min(row["eligible"], row["quota"]) for row in scored.values()
        ),
        "required_scored_sites": sum(row["quota"] for row in scored.values()),
        "scored_raw_flat_capture_ready": scored_raw_ready,
        "development_raw_flat_candidates": development,
        "development_raw_flat_candidate_ready": development_raw_ready,
        "final_transfer_site_eligibility": "UNMEASURED_NO_COMMON_TIFF",
        "capture_verdict": (
            "RAW_CAPTURE_FLOORS_MET_FINAL_TRANSFER_ELIGIBILITY_UNMEASURED"
            if scored_raw_ready and development_raw_ready
            else "M4_RETAINED_BLOCKED_CAPTURE"
        ),
    }


def probe() -> dict[str, Any]:
    started = time.perf_counter()
    census, _, definition, hashes = load_m152()
    noise = json.loads(
        (M152 / "out" / "noise-calibration.json").read_text(encoding="utf-8")
    )
    _, cache = detailed_inventory()
    specs = list(PROBE_SPECS) + dynamic_development_specs(cache)
    probes: list[dict[str, Any]] = []
    for index, spec in enumerate(specs, start=1):
        print(f"[{index}/{len(specs)}] {spec['unit_id']}")
        rows = select_rows(spec, cache)
        result = run_one_probe(census, definition, noise, spec, rows)
        probes.append(result)
        partial = {
            "schema": "m181-m4-flat-probe-v1",
            "frozen_dependencies": hashes,
            "noise_calibration_content_sha256": noise["content_sha256"],
            "prohibited_root": str(PROHIBITED_ROOT),
            "prohibited_root_opened": False,
            "probes": probes,
            "summary": None,
            "complete": False,
        }
        write_json(OUT / "flat-probe.partial.json", partial)
        if result["status"] == "MEASURED":
            print(
                f"  eligible={result['eligible_site_count']} "
                f"frames={result['processed_frame_count']}/"
                f"{result['selected_frame_count']}"
            )
        else:
            print(f"  {result['status']}")
    artifact = {
        "schema": "m181-m4-flat-probe-v1",
        "frozen_dependencies": hashes,
        "noise_calibration_content_sha256": noise["content_sha256"],
        "prohibited_root": str(PROHIBITED_ROOT),
        "prohibited_root_opened": False,
        "probes": probes,
        "summary": summarize(probes),
        "elapsed_seconds": time.perf_counter() - started,
        "complete": True,
    }
    write_json(OUT / "flat-probe.json", artifact)
    partial_path = OUT / "flat-probe.partial.json"
    if partial_path.exists():
        partial_path.unlink()
    print(json.dumps(artifact["summary"], indent=2, sort_keys=True))
    return artifact


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("inventory", "probe", "all"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command in {"inventory", "all"}:
        inventory()
    if args.command in {"probe", "all"}:
        probe()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
