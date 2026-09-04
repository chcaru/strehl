from __future__ import annotations

import argparse
import collections
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl"
)
EXIFTOOL = Path(
    r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe"
)
STACKS = {
    "flat-6s": ROOT / "flat-sw4-cpl" / "flat-et6s-sw4-cpl",
    "flat-2p5s": ROOT / "flat-sw4-cpl" / "flat-et2.5s-sw4-cpl",
    "flat-1s": ROOT / "flat-sw4-cpl" / "flat-et1s-sw4-cpl",
    "tilted-sw4": ROOT / "tilted-sw4-cpl",
    "tilted-sw10": ROOT / "tilted-sw10-cpl",
    "very-tilted-all-axis-sw10": ROOT / "very-tilted-all-axis-sw10-cpl",
}
EXPECTED = {
    "flat-6s": 65,
    "flat-2p5s": 61,
    "flat-1s": 60,
    "tilted-sw4": 182,
    "tilted-sw10": 92,
    "very-tilted-all-axis-sw10": 197,
}
EXPECTED_FOCUS = {
    "tilted-sw4": {57: 76, 58: 80, 59: 26},
    "tilted-sw10": {57: 38, 58: 40, 59: 14},
    "very-tilted-all-axis-sw10": {
        56: 10,
        57: 40,
        58: 40,
        59: 41,
        60: 40,
        61: 26,
    },
}
TAGS = (
    "FocusPosition2",
    "ImageStabilization",
    "LensModel",
    "LensType3",
    "ReleaseMode",
    "SequenceLength",
    "DateTimeOriginal",
    "ISO",
    "ExposureTime",
    "FNumber",
    "FocalLength",
)


def exif_records(path: Path, numeric: bool) -> list[dict]:
    command = [str(EXIFTOOL), "-j", "-r", "-ext", "ARW"]
    if numeric:
        command.append("-n")
    command.extend(f"-{tag}" for tag in TAGS)
    command.extend(["--", str(path)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(completed.stdout)


def counts(values) -> dict[str, int]:
    counter = collections.Counter(
        "<MISSING>" if value is None else str(value) for value in values
    )
    return dict(sorted(counter.items()))


def sorted_files(path: Path) -> list[Path]:
    return sorted(
        (
            entry
            for entry in path.iterdir()
            if entry.is_file() and entry.suffix.lower() == ".arw"
        ),
        key=lambda entry: entry.name,
    )


def run(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    if not EXIFTOOL.is_file():
        raise RuntimeError(f"missing exiftool: {EXIFTOOL}")
    rows = {}
    all_ibis_on = True
    counts_match = True
    focus_match = True
    for label, path in STACKS.items():
        files = sorted_files(path)
        numeric = exif_records(path, numeric=True)
        formatted = exif_records(path, numeric=False)
        if len(numeric) != len(files) or len(formatted) != len(files):
            raise RuntimeError(f"ExifTool count mismatch for {label}")
        focus = collections.Counter(
            int(record["FocusPosition2"])
            for record in numeric
            if "FocusPosition2" in record
        )
        observed_focus = dict(sorted(focus.items()))
        expected_focus = EXPECTED_FOCUS.get(label)
        focus_ok = expected_focus is None or observed_focus == expected_focus
        count_ok = len(files) == EXPECTED[label]
        ibis_values = counts(
            record.get("ImageStabilization") for record in numeric
        )
        ibis_on = ibis_values == {"1": len(files)}
        counts_match &= count_ok
        focus_match &= focus_ok
        all_ibis_on &= ibis_on
        rows[label] = {
            "path": str(path),
            "all_file_count": sum(1 for entry in path.iterdir() if entry.is_file()),
            "arw_count": len(files),
            "expected_arw_count": EXPECTED[label],
            "count_matches": count_ok,
            "first_file": files[0].name,
            "last_file": files[-1].name,
            "focus_position_2": {
                "histogram": {str(key): value for key, value in observed_focus.items()},
                "expected": (
                    {str(key): value for key, value in expected_focus.items()}
                    if expected_focus is not None
                    else None
                ),
                "matches": focus_ok,
            },
            "numeric_metadata_counts": {
                tag: counts(record.get(tag) for record in numeric)
                for tag in TAGS
                if tag != "FocusPosition2"
            },
            "formatted_metadata_counts": {
                tag: counts(record.get(tag) for record in formatted)
                for tag in (
                    "ImageStabilization",
                    "LensModel",
                    "LensType3",
                    "ReleaseMode",
                    "SequenceLength",
                )
            },
            "all_image_stabilization_on": ibis_on,
            "first_datetime": min(
                record["DateTimeOriginal"]
                for record in numeric
                if "DateTimeOriginal" in record
            ),
            "last_datetime": max(
                record["DateTimeOriginal"]
                for record in numeric
                if "DateTimeOriginal" in record
            ),
        }

    sw4 = rows["tilted-sw4"]["focus_position_2"]["histogram"]
    sw10 = rows["tilted-sw10"]["focus_position_2"]["histogram"]
    bucket_ratios = {
        key: sw4[key] / sw10[key] for key in sorted(sw10)
    }
    record = {
        "protocol": "M131-capture-metadata-audit-v1",
        "enumeration": (
            "Each directory was enumerated directly, including non-ARW files; "
            "the parent capture trees were separately inventoried with "
            "Get-ChildItem -Force -Recurse -File."
        ),
        "stacks": rows,
        "tilted_sw4_over_sw10_focus_bucket_ratios": bucket_ratios,
        "checks": {
            "all_six_counts_match": counts_match,
            "all_three_focus_histograms_match": focus_match,
            "all_six_stacks_ibis_on": all_ibis_on,
            "converter_identity_from_metadata": (
                "NOT ESTABLISHED; LensModel/LensType3 report Sony protocol "
                "identity, while physical Viltrox identity is owner testimony."
            ),
            "release_mode_semantics": (
                "NOT USED; the corpus is owner-confirmed focus bracketing even "
                "though ExifTool formats ReleaseMode as Exposure Bracketing."
            ),
        },
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"counts={counts_match} focus={focus_match} ibis={all_ibis_on} "
        f"ratios={bucket_ratios}"
    )
    return 0 if counts_match and focus_match and all_ibis_on else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "capture-metadata-audit.json",
    )
    args = parser.parse_args()
    return run(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
