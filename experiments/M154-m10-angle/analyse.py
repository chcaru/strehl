"""Audit the provenance and numerical requirements of M10's ruler angle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent
DEFAULT_SOURCE = Path(r"D:\personal\macro\requests\8-tilted-planar\README.md")
DEFAULT_OUTPUT = HERE / "out" / "analysis.json"

ANGLE_TOKEN = "10" + ".26"
THETA_TOKEN = "theta" + "_ext"
RISE_TOKEN = "1" + ".81"

BASELINE_EXCLUDED_PATHS = {
    Path("docs/research/M154-m10-angle.md"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_source_line(text: str) -> dict[str, Any]:
    subject_lines = [
        line.strip()
        for line in text.splitlines()
        if line.startswith("Subject is a ruler tilted up ")
    ]
    if len(subject_lines) != 1:
        raise ValueError(
            "expected exactly one uniquely anchored ruler subject line, "
            f"found {len(subject_lines)}"
        )
    line = subject_lines[0]
    pattern = re.compile(
        r"angle of approximately "
        + re.escape(ANGLE_TOKEN)
        + r"deg \(measured about: (?P<run>10)cm run against "
        + re.escape(RISE_TOKEN)
        + r"cm rise\)\."
    )
    match = pattern.search(line)
    if match is None:
        raise ValueError("anchored ruler subject line does not match the frozen form")
    return {
        "text": line,
        "run_cm": float(match.group("run")),
        "rise_cm": float(RISE_TOKEN),
    }


def self_test() -> list[str]:
    valid = (
        "Subject is a ruler tilted up (vertically) from left to right at an "
        "angle of approximately "
        + ANGLE_TOKEN
        + "deg (measured about: 10cm run against "
        + RISE_TOKEN
        + "cm rise)."
    )
    parsed = parse_source_line(valid)
    if parsed["run_cm"] != 10.0 or parsed["rise_cm"] != 1.81:
        raise AssertionError("valid source fixture parsed incorrectly")

    planted_value_defect = valid.replace(RISE_TOKEN + "cm rise", "1.80cm rise")
    try:
        parse_source_line(planted_value_defect)
    except ValueError:
        pass
    else:
        raise AssertionError("planted rise-value defect did not make the check fail")

    planted_duplicate_defect = valid + "\n" + valid
    try:
        parse_source_line(planted_duplicate_defect)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "planted duplicate-anchor defect did not make the check fail"
        )

    return [
        "valid anchored source fixture passed",
        "planted rise-value defect failed",
        "planted duplicate-anchor defect failed",
    ]


def excluded_from_head_inventory(relative: str) -> bool:
    path = Path(relative)
    if path.parts[:2] == ("experiments", HERE.name):
        return True
    return path in BASELINE_EXCLUDED_PATHS


def classify_context(context: str, token: str) -> str:
    folded = context.lower()
    if token == THETA_TOKEN:
        return "theta_ext quantity"
    if "ang" + ANGLE_TOKEN + "deg" in folded:
        return "capture identifier"
    if "approximately" in folded and "deg" in folded:
        return "approximate angle assertion"
    if "candidate value" in folded and "deg" in folded:
        return "approximate angle assertion"
    if ANGLE_TOKEN + "-degree" in folded:
        return "angle assertion"
    return "other exact numeric token"


def all_positions(buffer: bytes, needle: bytes) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        position = buffer.find(needle, start)
        if position < 0:
            return positions
        positions.append(position)
        start = position + 1


def is_bounded_decimal(buffer: bytes, position: int, length: int) -> bool:
    decimal_bytes = b"0123456789."
    before = buffer[position - 1] if position > 0 else None
    after_position = position + length
    after = buffer[after_position] if after_position < len(buffer) else None
    return (before is None or before not in decimal_bytes) and (
        after is None or after not in decimal_bytes
    )


def locations(
    buffer: bytes,
    positions: list[int],
) -> dict[int, tuple[int, int, str]]:
    result: dict[int, tuple[int, int, str]] = {}
    line_number = 1
    line_start = 0
    next_newline = buffer.find(b"\n", line_start)
    for position in sorted(set(positions)):
        while next_newline >= 0 and next_newline < position:
            line_number += 1
            line_start = next_newline + 1
            next_newline = buffer.find(b"\n", line_start)
        line_end = next_newline if next_newline >= 0 else len(buffer)
        context_start = max(line_start, position - 500)
        context_end = min(line_end, position + 500)
        context = bytes(buffer[context_start:context_end]).decode(
            "utf-8",
            errors="replace",
        )
        result[position] = (
            line_number,
            position - line_start + 1,
            " ".join(context.strip().split()),
        )
    return result


def scan_content(relative: str, buffer: bytes) -> dict[str, Any]:
    angle_bytes = ANGLE_TOKEN.encode("ascii")
    theta_bytes = THETA_TOKEN.encode("ascii")
    dimension_res = {
        "10 cm run": re.compile(rb"10\s*cm\s+run", re.IGNORECASE),
        "1.81 cm rise": re.compile(
            re.escape(RISE_TOKEN.encode("ascii")) + rb"\s*cm\s+rise",
            re.IGNORECASE,
        ),
    }
    collapsed_re = re.compile(
        rb"approximately\s+" + re.escape(angle_bytes) + rb"\s*deg(?:ree)?",
        re.IGNORECASE,
    )
    raw_angle_positions = all_positions(buffer, angle_bytes)
    angle_positions = [
        position
        for position in raw_angle_positions
        if is_bounded_decimal(buffer, position, len(angle_bytes))
    ]
    theta_positions = all_positions(buffer, theta_bytes)
    collapsed_matches = (
        list(collapsed_re.finditer(buffer)) if raw_angle_positions else []
    )
    dimension_matches = {
        label: list(regex.finditer(buffer)) for label, regex in dimension_res.items()
    }
    event_positions = (
        angle_positions
        + theta_positions
        + [match.start() for match in collapsed_matches]
        + [match.start() for matches in dimension_matches.values() for match in matches]
    )
    position_locations = locations(buffer, event_positions)

    hits: list[dict[str, Any]] = []
    for token, positions in (
        (THETA_TOKEN, theta_positions),
        (ANGLE_TOKEN, angle_positions),
    ):
        for position in positions:
            line_number, column, context = position_locations[position]
            hits.append(
                {
                    "path": relative,
                    "line": line_number,
                    "column": column,
                    "token": token,
                    "classification": classify_context(context, token),
                    "context": context,
                }
            )

    dimension_hits: list[dict[str, Any]] = []
    for label, matches in dimension_matches.items():
        for match in matches:
            line_number, column, context = position_locations[match.start()]
            dimension_hits.append(
                {
                    "path": relative,
                    "line": line_number,
                    "column": column,
                    "dimension": label,
                    "context": context,
                }
            )

    collapsed_hits: list[dict[str, Any]] = []
    for match in collapsed_matches:
        line_number, _, _ = position_locations[match.start()]
        matched = bytes(buffer[match.start() : match.end()]).decode("ascii")
        collapsed_hits.append(
            {
                "path": relative,
                "line": line_number,
                "matched": " ".join(matched.split()),
            }
        )

    path_hits = [
        {"path": relative, "token": token}
        for token in (ANGLE_TOKEN, THETA_TOKEN)
        if token in relative
    ]
    return {
        "raw_angle_hit_count": len(raw_angle_positions),
        "hits": hits,
        "collapsed_hits": collapsed_hits,
        "dimension_hits": dimension_hits,
        "path_hits": path_hits,
    }


def scan_git_head(head: str) -> dict[str, Any]:
    process = subprocess.Popen(
        [
            "git",
            "-C",
            str(PROJECT_ROOT),
            "archive",
            "--format=tar",
            head,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:
        raise RuntimeError("failed to open git archive pipes")

    hits: list[dict[str, Any]] = []
    collapsed_hits: list[dict[str, Any]] = []
    dimension_hits: list[dict[str, Any]] = []
    path_hits: list[dict[str, str]] = []
    raw_angle_hit_count = 0
    raw_angle_file_count = 0
    scanned_file_count = 0
    scanned_bytes = 0

    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            if not member.isfile() or excluded_from_head_inventory(member.name):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"could not extract tracked blob: {member.name}")
            content = extracted.read()
            scanned_file_count += 1
            scanned_bytes += len(content)
            result = scan_content(member.name, content)
            if result["raw_angle_hit_count"]:
                raw_angle_file_count += 1
                raw_angle_hit_count += result["raw_angle_hit_count"]
            hits.extend(result["hits"])
            collapsed_hits.extend(result["collapsed_hits"])
            dimension_hits.extend(result["dimension_hits"])
            path_hits.extend(result["path_hits"])

    stderr = process.stderr.read().decode("utf-8", errors="replace")
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"git archive failed ({return_code}): {stderr}")

    by_classification: dict[str, int] = {}
    by_token: dict[str, int] = {}
    for hit in hits:
        classification = hit["classification"]
        token = hit["token"]
        by_classification[classification] = by_classification.get(classification, 0) + 1
        by_token[token] = by_token.get(token, 0) + 1

    return {
        "scope": {
            "root": str(PROJECT_ROOT),
            "description": (
                "Every regular tracked blob in the immutable Git commit, "
                "including binary files and committed experiment outputs"
            ),
            "git_commit": head,
            "excluded_m154_paths": sorted(
                path.as_posix() for path in BASELINE_EXCLUDED_PATHS
            )
            + ["experiments/M154-m10-angle/**"],
            "matching_mode": (
                "binary-safe byte search over git archive; no filename-suffix filter"
            ),
        },
        "tracked_blobs_scanned": scanned_file_count,
        "bytes_scanned": scanned_bytes,
        "raw_10_26_substring_hit_count": raw_angle_hit_count,
        "raw_10_26_substring_file_count": raw_angle_file_count,
        "hit_count": len(hits),
        "file_count": len({hit["path"] for hit in hits}),
        "counts_by_token": dict(sorted(by_token.items())),
        "counts_by_classification": dict(sorted(by_classification.items())),
        "hits": hits,
        "whitespace_collapsed_phrase_hits": collapsed_hits,
        "source_dimension_hits": dimension_hits,
        "path_hits": path_hits,
    }


def derive_numbers(run_cm: float, rise_cm: float) -> dict[str, Any]:
    slope = rise_cm / run_cm
    angle_deg = math.degrees(math.atan(slope))
    angle_if_run_is_ruler_length_deg = math.degrees(math.asin(slope))
    tangent_vs_sine_relative_difference = (
        math.tan(math.radians(angle_deg)) / math.sin(math.radians(angle_deg)) - 1.0
    )

    truth_budget = 0.025
    required_slope_low = slope / (1.0 + truth_budget)
    required_slope_high = slope / (1.0 - truth_budget)
    required_angle_low = math.degrees(math.atan(required_slope_low))
    required_angle_high = math.degrees(math.atan(required_slope_high))

    final_bar = 0.05
    final_slope_low = slope / (1.0 + final_bar)
    final_slope_high = slope / (1.0 - final_bar)
    final_angle_low = math.degrees(math.atan(final_slope_low))
    final_angle_high = math.degrees(math.atan(final_slope_high))

    assumed_run_low = run_cm - 0.5
    assumed_run_high = run_cm + 0.5
    assumed_rise_low = rise_cm - 0.005
    assumed_rise_high = rise_cm + 0.005
    assumed_slope_low = assumed_rise_low / assumed_run_high
    assumed_slope_high = assumed_rise_high / assumed_run_low
    assumed_angle_low = math.degrees(math.atan(assumed_slope_low))
    assumed_angle_high = math.degrees(math.atan(assumed_slope_high))
    assumed_worst_relative_error = max(
        slope / assumed_slope_low - 1.0,
        1.0 - slope / assumed_slope_high,
    )

    def frozen_slope_error_for_angle(candidate_angle_deg: float) -> float:
        true_slope = math.tan(math.radians(candidate_angle_deg))
        return abs(slope / true_slope - 1.0)

    return {
        "nominal": {
            "run_cm": run_cm,
            "rise_cm": rise_cm,
            "slope": slope,
            "theta_deg": angle_deg,
            "status": (
                "DERIVED nominal from a MEASURED owner note whose uncertainty "
                "and instrument are unrecorded"
            ),
        },
        "geometry_convention": {
            "theta_deg_if_10_cm_is_horizontal_run": angle_deg,
            "theta_deg_if_10_cm_is_distance_along_ruler": (
                angle_if_run_is_ruler_length_deg
            ),
            "relative_difference_tan_theta_vs_sin_theta": (
                tangent_vs_sine_relative_difference
            ),
            "status": (
                "DERIVED; the capture note uses the word 'run', supporting the "
                "horizontal-run interpretation, but does not define endpoints "
                "or the camera-relative coordinate frame"
            ),
        },
        "m10_truth_budget": {
            "maximum_relative_slope_error": truth_budget,
            "required_true_slope_interval_if_nominal_is_frozen": [
                required_slope_low,
                required_slope_high,
            ],
            "required_theta_interval_deg_if_nominal_is_frozen": [
                required_angle_low,
                required_angle_high,
            ],
            "status": "DERIVED from the registered 2.5% truth-slope budget",
        },
        "m10_final_slope_bar": {
            "maximum_relative_slope_error": final_bar,
            "theta_interval_deg_if_nominal_is_frozen": [
                final_angle_low,
                final_angle_high,
            ],
            "status": "DERIVED from the registered 5% final ruler-slope bar",
        },
        "precision_examples": {
            "plus_or_minus_1_deg_worst_relative_slope_error": max(
                frozen_slope_error_for_angle(angle_deg - 1.0),
                frozen_slope_error_for_angle(angle_deg + 1.0),
            ),
            "plus_or_minus_0.5_deg_worst_relative_slope_error": max(
                frozen_slope_error_for_angle(angle_deg - 0.5),
                frozen_slope_error_for_angle(angle_deg + 0.5),
            ),
            "required_minus_deg": angle_deg - required_angle_low,
            "required_plus_deg": required_angle_high - angle_deg,
            "status": "DERIVED",
        },
        "conditional_display_precision_interval": {
            "assumption": (
                "ASSUMED only: 10 cm rounded to nearest 1 cm and 1.81 cm "
                "rounded to nearest 0.01 cm"
            ),
            "run_cm_interval": [assumed_run_low, assumed_run_high],
            "rise_cm_interval": [assumed_rise_low, assumed_rise_high],
            "slope_interval": [assumed_slope_low, assumed_slope_high],
            "theta_interval_deg": [assumed_angle_low, assumed_angle_high],
            "worst_relative_slope_error": assumed_worst_relative_error,
            "qualifies_for_m10_truth_budget": (
                assumed_worst_relative_error <= truth_budget
            ),
        },
        "evidential_interval": {
            "theta_interval_deg": None,
            "reason": (
                "The source says 'approximately' and 'measured about' but "
                "records no instrument, endpoint definition, repeatability, "
                "or uncertainty; no finite uncertainty interval is derivable."
            ),
            "status": "UNMEASURED",
        },
    }


def git_history(search: str, head: str) -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(PROJECT_ROOT),
            "log",
            "--reverse",
            "-S" + search,
            "--format=%H%x09%aI%x09%s",
            head,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = []
    for line in result.stdout.splitlines():
        commit, authored_at, subject = line.split("\t", maxsplit=2)
        rows.append(
            {
                "commit": commit,
                "authored_at": authored_at,
                "subject": subject,
            }
        )
    return rows


def git_head() -> str:
    result = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def analyse(source: Path) -> dict[str, Any]:
    started_at = datetime.now(UTC).isoformat()
    head = git_head()
    source_text = source.read_text(encoding="utf-8")
    source_sha256 = sha256(source)
    source_record = parse_source_line(source_text)
    source_line_number = next(
        index
        for index, line in enumerate(source_text.splitlines(), start=1)
        if line.startswith("Subject is a ruler tilted up ")
    )
    inventory = scan_git_head(head)
    source_sha256_after = sha256(source)
    if source_sha256 != source_sha256_after:
        raise RuntimeError("external README changed during scan; rerun")

    return {
        "schema_version": 3,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scan_started_at_utc": started_at,
        "repository_identity": {
            "head": head,
            "stability_check": (
                "VERIFIED: every scanned byte came from this immutable Git "
                "commit through git archive"
            ),
        },
        "self_tests": self_test(),
        "source_record": {
            "path": str(source),
            "sha256": source_sha256,
            "line_number": source_line_number,
            **source_record,
            "provenance_status": (
                "MEASURED owner capture note; method, instrument, endpoints, "
                "repeatability, and uncertainty are not recorded"
            ),
        },
        "derivation": derive_numbers(
            source_record["run_cm"],
            source_record["rise_cm"],
        ),
        "repository_inventory": inventory,
        "git_history": {
            "capture_identifier": git_history("ang" + ANGLE_TOKEN + "deg", head),
            "approximate_phrase": git_history(
                "approximately " + ANGLE_TOKEN + " deg",
                head,
            ),
            "theta_quantity": git_history(THETA_TOKEN, head),
        },
        "supplemental_working_tree_census": {
            "path": "experiments/M154-m10-angle/out/working-tree-census.json",
            "status": (
                "MEASURED rolling census, not an atomic snapshot and not used "
                "for absence claims"
            ),
        },
        "script_access_scope": {
            "external_files_read_by_this_script": [str(source)],
            "external_capture_files_read_by_this_script": [],
            "note": (
                "This records this script's code path only; it is not an audit "
                "of the surrounding interactive session."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    result = analyse(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    inventory = result["repository_inventory"]
    nominal = result["derivation"]["nominal"]
    required = result["derivation"]["m10_truth_budget"]
    conditional = result["derivation"]["conditional_display_precision_interval"]
    print(f"wrote: {args.output}")
    print(f"source_sha256: {result['source_record']['sha256']}")
    print(f"nominal_theta_deg: {nominal['theta_deg']:.9f}")
    print(
        "required_theta_interval_deg: "
        f"[{required['required_theta_interval_deg_if_nominal_is_frozen'][0]:.9f}, "
        f"{required['required_theta_interval_deg_if_nominal_is_frozen'][1]:.9f}]"
    )
    print(
        "assumed_display_theta_interval_deg: "
        f"[{conditional['theta_interval_deg'][0]:.9f}, "
        f"{conditional['theta_interval_deg'][1]:.9f}]"
    )
    print(
        "assumed_display_worst_relative_slope_error: "
        f"{conditional['worst_relative_slope_error']:.9f}"
    )
    print(
        f"repository_hits: {inventory['hit_count']} in {inventory['file_count']} files"
    )
    print(
        f"collapsed_phrase_hits: {len(inventory['whitespace_collapsed_phrase_hits'])}"
    )
    print(
        "raw_10_26_substring_hits: "
        f"{inventory['raw_10_26_substring_hit_count']} in "
        f"{inventory['raw_10_26_substring_file_count']} files"
    )
    print(f"tracked_blobs_scanned: {inventory['tracked_blobs_scanned']}")
    for line in result["self_tests"]:
        print(f"self_test: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
