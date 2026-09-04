#!/usr/bin/env python3
"""Independent, read-only audit of the frozen Phase-1 W1 width gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Sequence


HERE = Path(__file__).resolve().parent
PHASE1 = HERE.parent / "PHASE1-DESIGN"
RESULTS = PHASE1 / "results"
OUT = HERE / "out"
CAPTURES = ("flat-on-ruler", "coffee-bubbles", "113MSDCF")
ROIS = ("detail", "flat")
WIDTH_FILES = {capture: RESULTS / f"width-{capture}.json" for capture in CAPTURES}


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )


def contiguous_ranges(values: Iterable[float], grid: Sequence[float]) -> list[list[float]]:
    ordered = sorted(values)
    if not ordered:
        return []
    positions = {value: index for index, value in enumerate(grid)}
    groups = [[ordered[0], ordered[0]]]
    previous = positions[ordered[0]]
    for value in ordered[1:]:
        position = positions[value]
        if position == previous + 1:
            groups[-1][1] = value
        else:
            groups.append([value, value])
        previous = position
    return groups


def validate_series(
    legacy: float,
    candidate: Sequence[float],
    stored_ratio: Sequence[float],
    stored_error: Sequence[float],
) -> tuple[list[float], list[float], float, float]:
    if not math.isfinite(legacy) or legacy <= 0:
        raise AuditError(f"invalid legacy n_eff: {legacy}")
    if not (len(candidate) == len(stored_ratio) == len(stored_error)):
        raise AuditError("candidate/ratio/error lengths differ")
    ratios = [float(value) / legacy for value in candidate]
    errors = [abs(value - 1.0) for value in ratios]
    ratio_delta = max(abs(a - float(b)) for a, b in zip(ratios, stored_ratio, strict=True))
    error_delta = max(abs(a - float(b)) for a, b in zip(errors, stored_error, strict=True))
    if ratio_delta > 1e-12 or error_delta > 1e-12:
        raise AuditError(
            f"stored width arithmetic disagrees: ratio_delta={ratio_delta:.3e}, "
            f"error_delta={error_delta:.3e}"
        )
    if any(float(b) + 1e-12 < float(a) for a, b in zip(candidate, candidate[1:])):
        raise AuditError("candidate mean n_eff is not monotone in k")
    return ratios, errors, ratio_delta, error_delta


def intersect(sets: Sequence[set[float]]) -> set[float]:
    if not sets:
        return set()
    return set.intersection(*(set(values) for values in sets))


def frozen_hashes() -> dict[str, str]:
    run = load_json(RESULTS / "run.json")
    expected = run["hashes"]
    current = {}
    for relative, expected_hash in expected.items():
        path = RESULTS / relative
        got = sha256(path)
        if got != expected_hash:
            raise AuditError(f"frozen artifact hash mismatch: {relative}: {got} != {expected_hash}")
        current[relative] = got
    return current


def self_test() -> dict:
    candidate = [1.0, 1.9, 2.0, 2.1, 3.0]
    legacy = 2.0
    ratios = [value / legacy for value in candidate]
    errors = [abs(value - 1.0) for value in ratios]
    validate_series(legacy, candidate, ratios, errors)
    null_state = "GREEN"

    corrupt = list(ratios)
    corrupt[2] += 0.01
    try:
        validate_series(legacy, candidate, corrupt, errors)
    except AuditError:
        arithmetic_plant = "RED"
    else:
        raise AuditError("planted ratio corruption was not detected")

    grid = (0.0, 0.05, 0.10, 0.15, 0.20)
    common = intersect(({0.05, 0.10, 0.15}, {0.10, 0.15, 0.20}))
    if common != {0.10, 0.15}:
        raise AuditError(f"null intersection failed: {sorted(common)}")
    disjoint = intersect(({0.0, 0.05}, {0.15, 0.20}))
    if disjoint:
        raise AuditError(f"planted disjoint intervals were missed: {sorted(disjoint)}")
    intersection_plant = "RED"
    if contiguous_ranges(common, grid) != [[0.10, 0.15]]:
        raise AuditError("contiguous range reduction failed")

    propagation = variance_propagation_counterexample()
    if propagation["constant_null_relative_error"] > 1e-15:
        raise AuditError("constant-variance propagation null did not stay quiet")
    if abs(propagation["heteroscedastic_plant_relative_error"]) < 0.01:
        raise AuditError("heteroscedastic propagation plant did not fire")

    require_text("sentinel present", ("sentinel",))
    try:
        require_text("control text", ("sentinel",))
    except AuditError:
        report_plant = "RED"
    else:
        raise AuditError("planted report omission was not detected")

    result = {
        "status": "PASS",
        "null": {
            "consistent_width_arithmetic": null_state,
            "overlapping_intervals": "GREEN",
            "constant_variance_propagation": "GREEN",
            "report_required_text_present": "GREEN",
        },
        "plant": {
            "corrupted_stored_ratio": arithmetic_plant,
            "disjoint_intervals": intersection_plant,
            "heteroscedastic_variance_propagation": "RED",
            "report_required_text_missing": report_plant,
        },
    }
    print(
        "audit self-test: "
        "consistent-width=null=GREEN "
        "corrupted-ratio=plant=RED "
        "overlap=null=GREEN "
        "disjoint=plant=RED "
        "constant-variance=null=GREEN "
        "heteroscedastic-variance=plant=RED "
        "report-present=null=GREEN "
        "report-missing=plant=RED"
    )
    return result


def variance_propagation_counterexample() -> dict:
    kernel = [1.0 / 16.0, 4.0 / 16.0, 6.0 / 16.0, 4.0 / 16.0, 1.0 / 16.0]
    beta = sum(weight * weight for weight in kernel)

    def exact(variance: Sequence[float]) -> float:
        return sum(weight * weight * value for weight, value in zip(kernel, variance, strict=True))

    def scalar_beta_times_gaussian(variance: Sequence[float]) -> float:
        return beta * sum(weight * value for weight, value in zip(kernel, variance, strict=True))

    constant = [1.0] * len(kernel)
    heteroscedastic = [1.0, 1.0, 10.0, 1.0, 1.0]
    constant_exact = exact(constant)
    constant_approx = scalar_beta_times_gaussian(constant)
    plant_exact = exact(heteroscedastic)
    plant_approx = scalar_beta_times_gaussian(heteroscedastic)
    return {
        "scope": "one-dimensional reduce5 kernel; proves the propagation form is not exact in general",
        "kernel": kernel,
        "constant_null_exact": constant_exact,
        "constant_null_approximation": constant_approx,
        "constant_null_relative_error": abs(constant_approx / constant_exact - 1.0),
        "heteroscedastic_plant": heteroscedastic,
        "heteroscedastic_plant_exact": plant_exact,
        "heteroscedastic_plant_approximation": plant_approx,
        "heteroscedastic_plant_relative_error": plant_approx / plant_exact - 1.0,
    }


def require_text(text: str, required: Sequence[str]) -> None:
    missing = [value for value in required if value not in text]
    if missing:
        raise AuditError(f"required report text missing: {missing}")


def audit() -> dict:
    source_hashes_before = frozen_hashes()
    gate = load_json(RESULTS / "gate.json")
    manifest = load_json(RESULTS / "preregistered-manifest.json")
    k_grid = tuple(float(value) for value in manifest["analysis"]["k_grid"])
    width_bar = float(gate["bars"]["width"])
    if len(k_grid) != 161 or k_grid[0] != 0.0 or k_grid[-1] != 8.0:
        raise AuditError("unexpected frozen k grid")

    rows = []
    predicate_sets: list[set[float]] = []
    sets_by_band: dict[int, list[set[float]]] = {band: [] for band in range(7)}
    sets_by_capture_band: dict[tuple[str, int], list[set[float]]] = {}
    maximum_ratio_delta = 0.0
    maximum_error_delta = 0.0

    for capture in CAPTURES:
        payload = load_json(WIDTH_FILES[capture])
        if payload["capture"] != capture:
            raise AuditError(f"capture identity mismatch in {WIDTH_FILES[capture]}")
        if [entry["band"] for entry in payload["bands"]] != list(range(7)):
            raise AuditError(f"band order mismatch in {WIDTH_FILES[capture]}")
        for band_row in payload["bands"]:
            band = int(band_row["band"])
            if tuple(band_row["rois"]) != ROIS:
                raise AuditError(f"ROI order/content mismatch at {capture} band {band}")
            for roi in ROIS:
                values = band_row["rois"][roi]
                candidate = [float(value) for value in values["candidate_mean_neff"]]
                ratios, errors, ratio_delta, error_delta = validate_series(
                    float(values["legacy_mean_neff"]),
                    candidate,
                    values["ratio"],
                    values["width_error"],
                )
                maximum_ratio_delta = max(maximum_ratio_delta, ratio_delta)
                maximum_error_delta = max(maximum_error_delta, error_delta)
                admissible = {
                    k for k, error in zip(k_grid, errors, strict=True) if error <= width_bar + 1e-12
                }
                predicate_sets.append(admissible)
                sets_by_band[band].append(admissible)
                sets_by_capture_band.setdefault((capture, band), []).append(admissible)
                rows.append(
                    {
                        "capture": capture,
                        "frames": int(payload["frames"]),
                        "band": band,
                        "roi": roi,
                        "legacy_mean_neff": float(values["legacy_mean_neff"]),
                        "legacy_fraction_of_frames": float(values["legacy_mean_neff"])
                        / int(payload["frames"]),
                        "candidate_neff_k0": candidate[0],
                        "candidate_neff_k8": candidate[-1],
                        "candidate_k8_fraction_of_frames": candidate[-1] / int(payload["frames"]),
                        "ratio_k8": ratios[-1],
                        "admissible_k_count": len(admissible),
                        "admissible_k_ranges": contiguous_ranges(admissible, k_grid),
                    }
                )

    global_intersection = intersect(predicate_sets)
    band_summary = []
    for band in range(7):
        band_sets = sets_by_band[band]
        band_intersection = intersect(band_sets)
        band_summary.append(
            {
                "band": band,
                "predicates": len(band_sets),
                "predicates_with_any_k": sum(bool(values) for values in band_sets),
                "all_predicates_intersection": sorted(band_intersection),
                "all_predicates_ranges": contiguous_ranges(band_intersection, k_grid),
            }
        )

    capture_band_summary = []
    for capture in CAPTURES:
        for band in range(7):
            values = intersect(sets_by_capture_band[(capture, band)])
            capture_band_summary.append(
                {
                    "capture": capture,
                    "band": band,
                    "both_roi_intersection": sorted(values),
                    "both_roi_ranges": contiguous_ranges(values, k_grid),
                }
            )

    disjoint_witnesses = []
    for left_index, left in enumerate(rows):
        if not left["admissible_k_count"]:
            continue
        left_values = {
            k
            for interval in left["admissible_k_ranges"]
            for k in k_grid
            if interval[0] <= k <= interval[1]
        }
        for right in rows[left_index + 1 :]:
            if not right["admissible_k_count"]:
                continue
            right_values = {
                k
                for interval in right["admissible_k_ranges"]
                for k in k_grid
                if interval[0] <= k <= interval[1]
            }
            if left_values.isdisjoint(right_values):
                disjoint_witnesses.append(
                    {
                        "left": {
                            key: left[key] for key in ("capture", "band", "roi", "admissible_k_ranges")
                        },
                        "right": {
                            key: right[key]
                            for key in ("capture", "band", "roi", "admissible_k_ranges")
                        },
                        "same_capture": left["capture"] == right["capture"],
                        "same_band": left["band"] == right["band"],
                    }
                )

    legacy_spans = []
    for capture in CAPTURES:
        for roi in ROIS:
            profile = [row["legacy_mean_neff"] for row in rows if row["capture"] == capture and row["roi"] == roi]
            low = min(profile)
            high = max(profile)
            legacy_spans.append(
                {
                    "capture": capture,
                    "roi": roi,
                    "minimum": low,
                    "maximum": high,
                    "max_over_min": high / low,
                    "fractional_span_over_min": high / low - 1.0,
                }
            )

    gate_crosscheck_failures = []
    for index, gate_row in enumerate(gate["width_grid"]):
        expected_failures = {
            (row["capture"], int(row["band"]), row["roi"])
            for row in rows
            if k_grid[index]
            not in {
                k
                for interval in row["admissible_k_ranges"]
                for k in k_grid
                if interval[0] <= k <= interval[1]
            }
        }
        recorded_failures = {
            (entry["capture"], int(entry["band"]), entry["roi"]) for entry in gate_row["failures"]
        }
        if expected_failures != recorded_failures:
            gate_crosscheck_failures.append(
                {
                    "k": k_grid[index],
                    "missing": sorted(expected_failures - recorded_failures),
                    "extra": sorted(recorded_failures - expected_failures),
                }
            )
    if gate_crosscheck_failures:
        raise AuditError(f"gate.json failure ledger disagrees at {len(gate_crosscheck_failures)} k values")

    nonempty = [row for row in rows if row["admissible_k_count"]]
    empty = [row for row in rows if not row["admissible_k_count"]]
    commission = load_json(RESULTS / "commissioning.json")
    affine = commission["affine_validation"]
    standardization = {
        "status": commission["status"],
        "frozen_nu_eff": [float(value) for value in commission["frozen_nu_eff"]],
        "measured_nu_eff": [float(value) for value in affine["measured_nu_eff"]],
        "overall_coverage_by_band": [float(value) for value in affine["overall_by_band"]],
        "worst_frame_coverage_by_band": [float(value) for value in affine["worst_frame_by_band"]],
        "median_frame_coverage_by_band": [float(value) for value in affine["median_frame_by_band"]],
        "analytic_nu_coverage_by_band": [
            float(value) for value in affine["analytic_nu_coverage_by_band"]
        ],
        "beta_fit_diagnostics": [
            {
                "band": int(row["band"]),
                "log_rms": float(row["log_rms"]),
                "max_abs_log": float(row["max_abs_log"]),
                "max_multiplicative_factor": math.exp(float(row["max_abs_log"])),
            }
            for row in commission["affine_calibration"]["fit_diagnostics"]
        ],
        "commissioning_control_ids": [row["id"] for row in commission["rows"]],
    }
    source_hashes_after = frozen_hashes()
    if source_hashes_before != source_hashes_after:
        raise AuditError("frozen source hashes changed during read-only audit")

    result = {
        "schema": 1,
        "source": {
            "phase1_results": RESULTS.relative_to(HERE.parent).as_posix(),
            "hashes_before": source_hashes_before,
            "hashes_after": source_hashes_after,
            "frozen_unchanged": True,
        },
        "grid": list(k_grid),
        "width_bar": width_bar,
        "gate_record": {
            "verdict": gate["verdict"],
            "width_survivors": gate["width_survivors"],
            "metrics_empty": gate["metrics"] == {},
            "render_provenance_empty": gate["render_provenance"] == {},
        },
        "arithmetic_crosscheck": {
            "maximum_ratio_delta": maximum_ratio_delta,
            "maximum_width_error_delta": maximum_error_delta,
            "gate_failure_ledger_mismatches": gate_crosscheck_failures,
        },
        "legacy_profiles": rows,
        "legacy_cross_band_spans": legacy_spans,
        "predicate_counts": {
            "total": len(rows),
            "with_any_admissible_k": len(nonempty),
            "with_no_admissible_k": len(empty),
        },
        "global_width_intersection": sorted(global_intersection),
        "global_width_ranges": contiguous_ranges(global_intersection, k_grid),
        "band_summary": band_summary,
        "capture_band_summary": capture_band_summary,
        "disjoint_nonempty_witnesses": disjoint_witnesses,
        "standardization_commissioning": standardization,
        "variance_propagation_counterexample": variance_propagation_counterexample(),
    }
    return result


def write_csvs(result: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "legacy-neff.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("capture", "frames", "band", "roi", "legacy_mean_neff"),
        )
        writer.writeheader()
        for row in result["legacy_profiles"]:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    with (OUT / "width-intervals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "capture",
                "band",
                "roi",
                "candidate_neff_k0",
                "candidate_neff_k8",
                "legacy_fraction_of_frames",
                "candidate_k8_fraction_of_frames",
                "ratio_k8",
                "admissible_k_count",
                "admissible_k_ranges",
            ),
        )
        writer.writeheader()
        for row in result["legacy_profiles"]:
            out = {key: row[key] for key in writer.fieldnames}
            out["admissible_k_ranges"] = json.dumps(out["admissible_k_ranges"], separators=(",", ":"))
            writer.writerow(out)


def format_interval(ranges: Sequence[Sequence[float]]) -> str:
    if not ranges:
        return "∅"
    if len(ranges) != 1:
        raise AuditError(f"report formatter expected one interval, got {ranges}")
    low, high = ranges[0]
    return f"[{low:.2f}, {high:.2f}]"


def verify_report() -> dict:
    result = audit()
    report_path = HERE / "REPORT.md"
    text = report_path.read_text(encoding="utf-8")
    rows = result["legacy_profiles"]
    for capture in CAPTURES:
        capture_rows = [row for row in rows if row["capture"] == capture]
        frames = capture_rows[0]["frames"]
        for band in range(7):
            detail = next(row for row in capture_rows if row["band"] == band and row["roi"] == "detail")
            flat = next(row for row in capture_rows if row["band"] == band and row["roi"] == "flat")
            expected = (
                f"| {capture} (`{frames}`) | {band} | {detail['legacy_mean_neff']:.3f} | "
                f"{format_interval(detail['admissible_k_ranges'])} | "
                f"{flat['legacy_mean_neff']:.3f} | "
                f"{format_interval(flat['admissible_k_ranges'])} |"
            )
            require_text(text, (expected,))
    require_text(
        text,
        (
            "**H2.**",
            "`16 of 42`",
            "`26 of 42`",
            "**[V] 18 of 18**",
            "**[V] 0.01690 to 0.69209**",
            "`width_survivors=[]`, `metrics={}`",
            "## Could not determine",
        ),
    )
    return {"status": "PASS", "report": report_path.name, "profile_rows_checked": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--audit", action="store_true")
    group.add_argument("--verify-report", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        write_json(OUT / "commissioning.json", self_test())
        return 0
    if args.verify_report:
        result = verify_report()
        write_json(OUT / "report-check.json", result)
        print(f"report check: {result}")
        return 0
    result = audit()
    write_json(OUT / "audit.json", result)
    write_csvs(result)
    print(
        f"audit: predicates={result['predicate_counts']} "
        f"global_width_intersection={result['global_width_intersection']} "
        f"frozen_unchanged={result['source']['frozen_unchanged']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
