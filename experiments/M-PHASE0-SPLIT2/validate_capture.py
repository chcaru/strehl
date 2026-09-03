"""Validate the purported 32-repeat, two-light capture from ARW metadata."""

from __future__ import annotations

import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
CAPTURE = Path(
    r"D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
)
EXPECTED_ISOS = (50, 64, 80, 100, 200, 320, 400, 500, 640)
EXPECTED_REPEATS = 32
EXPECTED_FILES = len(EXPECTED_ISOS) * 2 * EXPECTED_REPEATS
EXPECTED_FIRST_FILE_NUMBER = 296
NAME_RE = re.compile(r"^DSC(\d{5})\.ARW$", re.IGNORECASE)


def number(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return float(numerator) / float(denominator)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if match is None:
        raise ValueError(f"not numeric: {value!r}")
    return float(match.group())


def timestamp(row: dict[str, object]) -> datetime:
    text = str(row.get("DateTimeOriginal") or row.get("CreateDate") or "")
    subsec = str(row.get("SubSecTimeOriginal") or "").strip()
    base = datetime.strptime(text[:19], "%Y:%m:%d %H:%M:%S")
    if subsec.isdigit():
        base = base.replace(microsecond=int((subsec + "000000")[:6]))
    return base


def filename_number(name: str) -> int:
    match = NAME_RE.fullmatch(name)
    if match is None:
        raise ValueError(f"unexpected ARW filename {name!r}")
    return int(match.group(1))


def extract_runs(rows: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    runs: list[list[dict[str, object]]] = []
    for row in rows:
        iso = int(number(row["ISO"]))
        if not runs or int(number(runs[-1][-1]["ISO"])) != iso:
            runs.append([])
        runs[-1].append(row)
    return runs


def validate(rows: list[dict[str, object]]) -> dict[str, object]:
    rows = sorted(rows, key=lambda row: filename_number(str(row["FileName"])))
    if len(rows) != EXPECTED_FILES:
        raise ValueError(f"{len(rows)} ARWs, expected {EXPECTED_FILES}")

    file_numbers = [filename_number(str(row["FileName"])) for row in rows]
    expected_numbers = list(
        range(EXPECTED_FIRST_FILE_NUMBER, EXPECTED_FIRST_FILE_NUMBER + EXPECTED_FILES)
    )
    if file_numbers != expected_numbers:
        raise ValueError("ARW filename sequence is not contiguous")

    iso_counts = Counter(int(number(row["ISO"])) for row in rows)
    expected_counts = {iso: 2 * EXPECTED_REPEATS for iso in EXPECTED_ISOS}
    if dict(sorted(iso_counts.items())) != expected_counts:
        raise ValueError(f"ISO counts {dict(iso_counts)} != {expected_counts}")

    fixed_numeric = {
        "ExposureTime": 1.6,
        "FNumber": 5.6,
        "FocalLength": 200.0,
        "BitsPerSample": 14.0,
    }
    for field, expected in fixed_numeric.items():
        values = [number(row[field]) for row in rows]
        if any(not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-6) for value in values):
            raise ValueError(f"{field} is not fixed at {expected}: {sorted(set(values))}")

    models = {str(row.get("Model", "")).strip() for row in rows}
    if models != {"ILCE-7CM2"}:
        raise ValueError(f"camera model varies: {models}")
    focus_mode_codes = {str(row.get("FocusMode", "")).strip() for row in rows}
    # ExifTool's numeric (-n) Sony FocusMode value 0 is Manual. Keep accepting
    # the printed label so the synthetic validator remains independent of the
    # ExifTool representation.
    focus_modes = {value.lower().replace(" ", "") for value in focus_mode_codes}
    if focus_modes not in ({"0"}, {"manual"}, {"manualfocus"}, {"mf"}):
        raise ValueError(f"focus mode is not fixed manual focus: {focus_mode_codes}")

    times = [timestamp(row) for row in rows]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("capture timestamps are not strictly increasing")

    runs = extract_runs(rows)
    if len(runs) != 2 * len(EXPECTED_ISOS):
        raise ValueError(f"{len(runs)} contiguous ISO runs, expected 18")
    if any(len(run) != EXPECTED_REPEATS for run in runs):
        raise ValueError(f"run lengths are {[len(run) for run in runs]}, expected 32 each")

    pass_isos = []
    for pass_index in range(2):
        values = [int(number(run[0]["ISO"])) for run in runs[pass_index * 9 : (pass_index + 1) * 9]]
        if sorted(values) != list(EXPECTED_ISOS):
            raise ValueError(f"pass {pass_index + 1} ISO set/order is invalid: {values}")
        pass_isos.append(values)

    groups = []
    by_iso_pass: dict[tuple[int, int], dict[str, object]] = {}
    for run_index, run in enumerate(runs):
        pass_index = run_index // len(EXPECTED_ISOS) + 1
        iso = int(number(run[0]["ISO"]))
        run_times = [timestamp(row) for row in run]
        gaps = [
            (right - left).total_seconds()
            for left, right in zip(run_times, run_times[1:])
        ]
        if gaps and max(gaps) >= 5.0:
            raise ValueError(f"ISO {iso} pass {pass_index} has an inter-frame gap >=5 s")
        brightness = [number(row["BrightnessValue"]) for row in run]
        if max(brightness) - min(brightness) >= 0.5:
            raise ValueError(
                f"ISO {iso} pass {pass_index} brightness varies by >=0.5 EV"
            )
        sizes = [int(number(row["FileSize"])) for row in run]
        size_mean = statistics.fmean(sizes)
        size_cv = statistics.pstdev(sizes) / size_mean
        if size_cv >= 0.05:
            raise ValueError(f"ISO {iso} pass {pass_index} file-size CV >=5%")

        focus_fields = {}
        for field in ("FocusDistance", "FocusDistance2", "FocusPosition"):
            values = [
                row[field]
                for row in run
                if field in row and str(row[field]).strip() not in ("", "-")
            ]
            if values:
                focus_fields[field] = sorted({str(value) for value in values})

        group = {
            "group_index": run_index,
            "pass": pass_index,
            "iso": iso,
            "files": [str(row["FileName"]) for row in run],
            "first_timestamp": run_times[0].isoformat(),
            "last_timestamp": run_times[-1].isoformat(),
            "duration_seconds": (run_times[-1] - run_times[0]).total_seconds(),
            "inter_frame_gap_seconds": {
                "median": statistics.median(gaps),
                "maximum": max(gaps),
            },
            "brightness_value_ev": {
                "mean": statistics.fmean(brightness),
                "minimum": min(brightness),
                "maximum": max(brightness),
                "range": max(brightness) - min(brightness),
            },
            "file_size_bytes": {
                "mean": size_mean,
                "cv": size_cv,
            },
            "focus_metadata": focus_fields,
        }
        groups.append(group)
        by_iso_pass[(iso, pass_index)] = group

    light_shifts = {}
    for iso in EXPECTED_ISOS:
        first = by_iso_pass[(iso, 1)]["brightness_value_ev"]["mean"]
        second = by_iso_pass[(iso, 2)]["brightness_value_ev"]["mean"]
        shift = second - first
        if abs(shift) <= 0.5:
            raise ValueError(f"ISO {iso} light-pass shift is only {shift:.3f} EV")
        light_shifts[str(iso)] = shift

    focus_tags = sorted(
        {
            field
            for group in groups
            for field in group["focus_metadata"]
        }
    )
    focus_variation = {
        field: sorted(
            {
                value
                for group in groups
                for value in group["focus_metadata"].get(field, [])
            }
        )
        for field in focus_tags
    }
    if any(len(values) > 1 for values in focus_variation.values()):
        raise ValueError(f"numeric focus metadata varies: {focus_variation}")
    stabilization_rows = [
        row for row in rows if "ImageStabilization" in row
    ]
    if stabilization_rows and len(stabilization_rows) != len(rows):
        raise ValueError(
            f"ImageStabilization is present on only "
            f"{len(stabilization_rows)}/{len(rows)} files"
        )
    stabilization_values = sorted(
        {
            str(row["ImageStabilization"])
            for row in stabilization_rows
        }
    )
    stabilization_labels = [
        {"0": "Off", "1": "On"}.get(value, f"Unknown({value})")
        for value in stabilization_values
    ]

    return {
        "status": "METADATA_VALIDATED",
        "capture": str(CAPTURE),
        "files": len(rows),
        "filename_first": str(rows[0]["FileName"]),
        "filename_last": str(rows[-1]["FileName"]),
        "camera": next(iter(models)),
        "fixed": {
            field: expected for field, expected in fixed_numeric.items()
        }
        | {"FocusMode": "Manual", "FocusModeExifToolNumeric": next(iter(focus_mode_codes))},
        "iso_counts": dict(sorted(iso_counts.items())),
        "pass_iso_order": pass_isos,
        "groups": groups,
        "light_shift_ev_pass2_minus_pass1": light_shifts,
        "focus_numeric_tags_present": focus_tags,
        "focus_numeric_values": focus_variation,
        "image_stabilization_values": stabilization_values,
        "image_stabilization_labels": stabilization_labels,
        "image_stabilization_tag_count": len(stabilization_rows),
        "metadata_limit": (
            "Manual focus and invariant reported focus tags do not prove the "
            "physical focus ring or subject stayed fixed; pixel stability is a separate gate."
        ),
    }


def synthetic_rows() -> list[dict[str, object]]:
    rows = []
    number_value = 296
    for pass_index, order in enumerate(
        (
            (400, 100, 200, 320, 500, 640, 80, 64, 50),
            (100, 640, 400, 50, 200, 64, 500, 80, 320),
        )
    ):
        for iso in order:
            for repeat in range(EXPECTED_REPEATS):
                seconds = len(rows) * 2
                rows.append(
                    {
                        "FileName": f"DSC{number_value:05d}.ARW",
                        "ISO": iso,
                        "ExposureTime": 1.6,
                        "FNumber": 5.6,
                        "FocalLength": 200,
                        "BitsPerSample": 14,
                        "Model": "ILCE-7CM2",
                        "FocusMode": 0,
                        "FocusPosition": "fixed",
                        "DateTimeOriginal": (
                            datetime(2026, 1, 1)
                            .replace(hour=19)
                            .timestamp()
                            + seconds
                        ),
                        "BrightnessValue": 2.0 - pass_index,
                        "FileSize": 40_000_000 + repeat,
                    }
                )
                rows[-1]["DateTimeOriginal"] = datetime.fromtimestamp(
                    rows[-1]["DateTimeOriginal"]
                ).strftime("%Y:%m:%d %H:%M:%S")
                number_value += 1
    return rows


def commission() -> dict[str, object]:
    plants = {}
    for name in ("M1", "M2", "M3", "M4"):
        rows = synthetic_rows()
        if name == "M1":
            rows.pop()
        elif name == "M2":
            rows[17]["ExposureTime"] = 0.8
        elif name == "M3":
            rows[33]["FocusMode"] = 2
        else:
            for row in rows:
                row["BrightnessValue"] = 2.0
        try:
            validate(rows)
        except (KeyError, TypeError, ValueError):
            plants[name] = "RED"
        else:
            plants[name] = "GREEN"
    if any(value != "RED" for value in plants.values()):
        raise RuntimeError(f"metadata validator missed a plant: {plants}")
    return {
        "status": "COMMISSIONED_GREEN",
        "clean_status": validate(synthetic_rows())["status"],
        "plants": plants,
        "all_plants_red": True,
        "external_predicate": "contiguous DSC00296..DSC00871 filename sequence",
    }


def read_metadata() -> list[dict[str, object]]:
    fields = (
        "FileName",
        "FileSize#",
        "DateTimeOriginal",
        "SubSecTimeOriginal",
        "CreateDate",
        "ISO",
        "ExposureTime",
        "FNumber",
        "FocalLength",
        "BitsPerSample",
        "Model",
        "LensModel",
        "FocusMode",
        "FocusDistance",
        "FocusDistance2",
        "FocusPosition",
        "BrightnessValue",
        "WhiteBalance",
        "DriveMode",
        "ImageStabilization",
    )
    command = ["exiftool", "-json", "-n", "-api", "LargeFileSupport=1"]
    command.extend(f"-{field}" for field in fields)
    command.extend(["-ext", "ARW", str(CAPTURE)])
    proc = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"exiftool failed {proc.returncode}: {proc.stderr}")
    rows = json.loads(proc.stdout)
    if not isinstance(rows, list):
        raise RuntimeError("exiftool did not return a JSON list")
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    commissioned = commission()
    (OUT / "validator-commission.json").write_text(
        json.dumps(commissioned, indent=2) + "\n", encoding="utf-8"
    )
    if "--commission-only" in sys.argv:
        print(json.dumps(commissioned, indent=2))
        return 0

    result = validate(read_metadata())
    (OUT / "capture-manifest.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
