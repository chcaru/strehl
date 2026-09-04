from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


LANE_ROOT = Path(__file__).resolve().parent
FORBIDDEN_SOURCE_ROOTS = (
    Path(r"D:\personal\macro"),
    Path(r"D:\edited\macro"),
)
REQUIRED_COMPARATOR_MODES = {
    "zerene-pmax",
    "zerene-dmap",
    "fork-best-known",
}
OPTIONAL_COMPARATOR_MODES = {
    "helicon-a",
    "helicon-b",
    "helicon-c",
}
REGISTERED_COMPARATOR_MODES = REQUIRED_COMPARATOR_MODES | OPTIONAL_COMPARATOR_MODES
COMMERCIAL_COMPARATOR_MODES = {
    "zerene-pmax",
    "zerene-dmap",
    "helicon-a",
    "helicon-b",
    "helicon-c",
}
STREHL_QUALITY_MODE_ID = "strehl-common-16"
COMPARATOR_PRODUCT_IDS = {
    "zerene-pmax": "zerene-stacker",
    "zerene-dmap": "zerene-stacker",
    "fork-best-known": "best-known-source-fork",
    "helicon-a": "helicon-focus",
    "helicon-b": "helicon-focus",
    "helicon-c": "helicon-focus",
}
REQUIRED_QUALITY_GATES = ("M1", "M2", "M3", "M8")
QUALITY_CRITERION_ID = "scorecard-v1.10-m11-quality-corpus-and-timed-output-v1"
INERT_MUTATION_SENTINEL = "m153-inert-v1"  # MUTATION_ANCHOR:INERT


@dataclass(frozen=True)
class GuardResult:
    guard_id: str
    name: str
    passed: bool
    failure: str | None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


Guard = Callable[[dict[str, Any]], bool]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def strict_json_loads(text: str) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON value is forbidden: {value}")

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"non-finite JSON number is forbidden: {value}")
        return parsed

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key is forbidden: {key}")
            result[key] = value
        return result

    return json.loads(
        text,
        parse_constant=reject_constant,
        parse_float=finite_float,
        object_pairs_hook=unique_object,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path, block_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def object_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _normal_path(path: str | Path) -> str:
    return os.path.normcase(str(Path(path).resolve(strict=False)))


def path_is_within(path: str | Path, root: str | Path) -> bool:
    candidate = _normal_path(path)
    boundary = _normal_path(root)
    try:
        return os.path.commonpath((candidate, boundary)) == boundary
    except ValueError:
        return False


def _hash_text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _commit_text(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def expected_capture_names(stack_id: str, count: int) -> list[str]:
    starts = {"bee-1-cpl": 1, "coffee-bean": 16}
    if stack_id not in starts or count < 1:
        return []
    first = starts[stack_id]
    return [f"DSC{number:05d}.ARW" for number in range(first, first + count)]


def g01_owned_output(payload: dict[str, Any]) -> bool:
    path = payload.get("path", "")
    lane_root = payload.get("lane_root", str(LANE_ROOT))
    valid = (
        bool(path)
        and path_is_within(path, lane_root)
        and not any(path_is_within(path, root) for root in FORBIDDEN_SOURCE_ROOTS)
    )
    return valid  # MUTATION_ANCHOR:G01


def g02_capture_contract(payload: dict[str, Any]) -> bool:
    captures = payload.get("captures", {})
    expected = {
        "bee-1-cpl": {
            "path": _normal_path(r"D:\personal\macro\bee-1-cpl"),
            "count": 299,
            "first": "DSC00001.ARW",
            "last": "DSC00299.ARW",
            "evidence_class": "HOLDOUT - PERFORMANCE",
        },
        "coffee-bean": {
            "path": _normal_path(r"D:\personal\macro\coffee-bean"),
            "count": 105,
            "first": "DSC00016.ARW",
            "last": "DSC00120.ARW",
            "evidence_class": "FIXED HISTORICAL BENCHMARK - NOT HOLDOUT",
        },
    }
    normalized = {
        key: {
            **value,
            "path": _normal_path(value.get("path", "")),
        }
        for key, value in captures.items()
        if isinstance(value, dict)
    }
    valid = set(normalized) == set(expected) and all(
        normalized[name].get("path") == requirement["path"]
        and normalized[name].get("count") == requirement["count"]
        and normalized[name].get("first") == requirement["first"]
        and normalized[name].get("last") == requirement["last"]
        and normalized[name].get("evidence_class") == requirement["evidence_class"]
        and normalized[name].get("missing") == []
        and normalized[name].get("unexpected") == []
        for name, requirement in expected.items()
    )
    return valid  # MUTATION_ANCHOR:G02


def g03_readonly_snapshot(payload: dict[str, Any]) -> bool:
    before = payload.get("before", {})
    after = payload.get("after", {})
    valid = (
        _hash_text(before.get("sha256"))
        and before.get("sha256") == after.get("sha256")
        and before.get("file_count") == after.get("file_count")
        and before.get("total_bytes") == after.get("total_bytes")
    )
    return valid  # MUTATION_ANCHOR:G03


def g04_artifact_binding(payload: dict[str, Any]) -> bool:
    artifacts = payload.get("artifacts", [])
    valid = bool(artifacts) and all(
        artifact.get("verified") is True
        and _hash_text(artifact.get("expected_sha256"))
        and artifact.get("expected_sha256") == artifact.get("actual_sha256")
        for artifact in artifacts
    )
    return valid  # MUTATION_ANCHOR:G04


def g05_quality_qualified(payload: dict[str, Any]) -> bool:
    gates = payload.get("quality_gates", {})
    m1 = payload.get("replacement_m1", {})
    flat_power = payload.get("retained_flat_power", {})
    evidence_ids = {"transfer", "geometry", *REQUIRED_QUALITY_GATES}
    evidence_output_sha256 = payload.get("evidence_output_sha256", {})
    evidence_pixel_sha256 = payload.get("evidence_pixel_sha256", {})
    valid = (
        payload.get("status") == "QUALITY_QUALIFIED"
        and payload.get("criterion_id") == QUALITY_CRITERION_ID
        and payload.get("criterion_status") == "SCORECARD_DEFINED"
        and payload.get("mode_id")
        in REGISTERED_COMPARATOR_MODES | {STREHL_QUALITY_MODE_ID}
        and payload.get("capture_id") in {"bee-1-cpl", "coffee-bean"}
        and (
            (payload.get("capture_id"), int(payload.get("count", -1)))
            in {
                ("bee-1-cpl", 33),
                ("coffee-bean", 105),
                ("bee-1-cpl", 299),
            }
        )
        and _commit_text(payload.get("measured_commit"))
        and _hash_text(payload.get("binary_sha256"))
        and _hash_text(payload.get("executable_bundle_sha256"))
        and _hash_text(payload.get("settings_sha256"))
        and _hash_text(payload.get("input_manifest_sha256"))
        and _hash_text(payload.get("output_contract_sha256"))
        and _hash_text(payload.get("output_sha256"))
        and _hash_text(payload.get("pixel_sha256"))
        and set(evidence_output_sha256) == evidence_ids
        and set(evidence_output_sha256.values()) == {payload.get("output_sha256")}
        and set(evidence_pixel_sha256) == evidence_ids
        and set(evidence_pixel_sha256.values()) == {payload.get("pixel_sha256")}
        and payload.get("input_output_transfer") == "PASS"
        and payload.get("geometry_and_site_retention") == "PASS"
        and set(gates) == set(REQUIRED_QUALITY_GATES)
        and all(gates.get(gate) == "PASS" for gate in REQUIRED_QUALITY_GATES)
        and m1.get("instrument_status") == "ADMITTED"
        and m1.get("decision") == "PASS"
        and _hash_text(m1.get("artifact_sha256"))
        and flat_power.get("population_counts")
        == {"medication-pill": 84, "bee": 83, "foam": 83}
        and int(flat_power.get("invalid_tile_count", -1)) == 0
        and set(flat_power.get("capture_median_q_flat", {}))
        == {"medication-pill", "bee", "foam"}
        and all(
            float(value) <= 1.0
            for value in flat_power.get("capture_median_q_flat", {}).values()
        )
        and float(flat_power.get("pooled_median_q_flat", math.inf)) <= 1.0
        and int(flat_power.get("eligible_site_channel_count", -1)) == 750
        and int(flat_power.get("transfer_failed_site_channels", -1)) == 0
        and float(flat_power.get("gain_min", -math.inf)) >= 0.995
        and float(flat_power.get("gain_max", math.inf)) <= 1.005
        and float(flat_power.get("residual_max", math.inf)) <= 0.005
        and flat_power.get("same_output_joint_tuple_verified") is True
        and _hash_text(flat_power.get("artifact_sha256"))
        and payload.get("quality_corpus_verified") is True
        and payload.get("bound_artifacts_verified") is True
    )
    return valid  # MUTATION_ANCHOR:G05


def g06_common_input_identity(payload: dict[str, Any]) -> bool:
    modes = payload.get("modes", [])
    identity_fields = (
        "input_manifest_sha256",
        "ordered_input_sha256",
        "volume_id",
        "dimensions",
        "bit_depth",
        "icc_sha256",
        "compression",
    )
    valid = (
        len(modes) >= 2
        and modes[0].get("compression") == "NONE"
        and modes[0].get("bit_depth") == 16
        and _hash_text(modes[0].get("input_manifest_sha256"))
        and _hash_text(modes[0].get("ordered_input_sha256"))
        and _hash_text(modes[0].get("icc_sha256"))
        and bool(modes[0].get("volume_id"))
        and len(modes[0].get("dimensions", [])) == 3
        and all(int(value) > 0 for value in modes[0].get("dimensions", []))
        and all(
            mode.get(field) == modes[0].get(field)
            for mode in modes[1:]
            for field in identity_fields
        )
    )
    return valid  # MUTATION_ANCHOR:G06


def g07_native_prefix(payload: dict[str, Any]) -> bool:
    stack_id = payload.get("stack_id", "")
    count = int(payload.get("count", 0))
    allowed_counts = {
        "bee-1-cpl": {33, 96, 97, 98, 99, 100, 299},
        "coffee-bean": {105},
    }
    actual = [str(name).upper() for name in payload.get("ordered_names", [])]
    expected = expected_capture_names(stack_id, count)
    valid = (
        count in allowed_counts.get(stack_id, set())
        and actual == expected
        and len(payload.get("ordered_sha256", [])) == count
        and all(_hash_text(value) for value in payload.get("ordered_sha256", []))
    )
    return valid  # MUTATION_ANCHOR:G07


def g08_settings_fingerprint(payload: dict[str, Any]) -> bool:
    timed = payload.get("timed", {})
    qualified = payload.get("qualified", {})
    fields = (
        "mode_id",
        "binary_sha256",
        "executable_bundle_sha256",
        "settings_sha256",
        "input_manifest_sha256",
        "output_contract_sha256",
    )
    valid = all(
        _hash_text(timed.get(field)) and timed.get(field) == qualified.get(field)
        for field in fields[1:]
    ) and (
        timed.get("mode_id") == qualified.get("mode_id")
        and int(timed.get("count", -1)) == int(qualified.get("count", -2))
    )
    return valid  # MUTATION_ANCHOR:G08


def g09_process_tree_drained(payload: dict[str, Any]) -> bool:
    valid = (
        int(payload.get("qpc_frequency", 0)) > 0
        and payload.get("job_assigned_before_resume") is True
        and payload.get("root_returncode") == 0
        and payload.get("active_processes_final") == 0
        and payload.get("process_images_preverified_before_timing") is True
        and int(payload.get("process_count_total", 0)) >= 1
        and int(payload.get("sample_count", 0)) >= 1
        and int(payload.get("sample_interval_ms", 0)) == 10
        and int(payload.get("missed_intervals", -1)) == 0
        and float(payload.get("max_gap_ms", math.inf)) <= 15.0
        and len(payload.get("process_lifetimes", []))
        == int(payload.get("process_count_total", 0))
        and all(
            bool(row.get("image_path")) and _hash_text(row.get("image_sha256"))
            for row in payload.get("process_lifetimes", [])
        )
        and int(payload.get("drained_qpc_ticks", -1))
        >= int(payload.get("root_exit_qpc_ticks", 0))
        and (
            not payload.get("child_expected")
            or int(payload.get("process_count_total", 0)) >= 2
        )
    )
    return valid  # MUTATION_ANCHOR:G09


def g10_deliverable_finalized(payload: dict[str, Any]) -> bool:
    valid = (
        int(payload.get("qpc_frequency", 0)) > 0
        and payload.get("exclusive_open_succeeded") is True
        and payload.get("output_flush_succeeded") is True
        and payload.get("manifest_flush_succeeded") is True
        and payload.get("manifest_structurally_valid") is True
        and payload.get("tiff_valid") is True
        and payload.get("highest_precision") is True
        and payload.get("compression") == "NONE"
        and _hash_text(payload.get("output_sha256"))
        and _hash_text(payload.get("pixel_sha256"))
        and _hash_text(payload.get("manifest_sha256"))
        and int(payload.get("finalized_qpc_ticks", 0))
        >= int(payload.get("process_drained_qpc_ticks", 0))
    )
    return valid  # MUTATION_ANCHOR:G10


def g11_telemetry_complete(payload: dict[str, Any]) -> bool:
    stages = set(payload.get("stage_banners", []))
    required_stages = set(payload.get("required_stages", []))
    numeric_required = set(payload.get("numeric_stage_timings_required", []))
    measurements = {
        row.get("stage"): row
        for row in payload.get("stage_measurements", [])
        if isinstance(row, dict)
    }
    gpu_samples = payload.get("gpu_utilization_percent", [])
    cpu_samples = payload.get("cpu_samples", [])
    hardware_samples = payload.get("hardware_samples", [])
    synthetic = payload.get("synthetic_telemetry") is True
    frequency = int(payload.get("qpc_frequency", 0))
    started = int(payload.get("started_qpc_ticks", -1))
    finalized = int(payload.get("finalized_qpc_ticks", -1))
    wall_seconds = float(payload.get("wall_seconds", -1.0))
    process_cpu_seconds = float(payload.get("process_tree_cpu_seconds", -1.0))
    logical_processors = int(payload.get("logical_processor_count", 0))
    system_start = payload.get("system_times_start", {})
    system_end = payload.get("system_times_end", {})
    system_busy_seconds = (
        int(system_end.get("busy_100ns", -1)) - int(system_start.get("busy_100ns", 0))
    ) / 10_000_000.0
    expected_busy_fraction = (
        process_cpu_seconds / (wall_seconds * logical_processors)
        if wall_seconds > 0.0 and logical_processors > 0
        else math.nan
    )
    expected_external_busy_fraction = (
        max(0.0, system_busy_seconds - process_cpu_seconds)
        / (wall_seconds * logical_processors)
        if wall_seconds > 0.0 and logical_processors > 0
        else math.nan
    )

    def covers_timed_interval(samples: list[dict[str, Any]]) -> bool:
        if frequency <= 0 or finalized <= started or not samples:
            return False
        ticks = [int(sample.get("qpc_ticks", -1)) for sample in samples]
        sample_interval_seconds = float(payload.get("sample_interval_ms", 0)) / 1000.0
        tolerance = math.ceil(frequency * sample_interval_seconds * 1.5)
        return (
            ticks == sorted(ticks)
            and all(
                int(sample.get("qpc_frequency", 0)) == frequency
                and started <= tick <= finalized
                for sample, tick in zip(samples, ticks)
            )
            and ticks[0] <= started + tolerance
            and ticks[-1] >= finalized - tolerance
            and all(
                later - earlier <= tolerance for earlier, later in zip(ticks, ticks[1:])
            )
        )

    valid = (
        wall_seconds > 0.0
        and process_cpu_seconds >= 0.0
        and int(payload.get("process_tree_counter_failures", -1)) == 0
        and logical_processors >= 1
        and system_busy_seconds >= 0.0
        and math.isclose(
            float(payload.get("busy_fraction", math.nan)),
            expected_busy_fraction,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        and math.isclose(
            float(payload.get("external_busy_fraction", math.nan)),
            expected_external_busy_fraction,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        and int(payload.get("read_bytes", -1)) >= 0
        and int(payload.get("write_bytes", -1)) >= 0
        and int(payload.get("sample_count", 0)) >= 1
        and payload.get("sample_interval_ms") == 10
        and (synthetic or int(payload.get("missed_intervals", -1)) == 0)
        and len(cpu_samples) == int(payload.get("sample_count", 0))
        and all(
            int(sample.get("qpc_frequency", 0)) > 0
            and int(sample.get("qpc_ticks", -1)) >= 0
            and int(sample.get("idle_100ns", -1)) >= 0
            and int(sample.get("kernel_100ns", -1)) >= 0
            and int(sample.get("user_100ns", -1)) >= 0
            for sample in cpu_samples
        )
        and bool(payload.get("gpu_source"))
        and bool(gpu_samples)
        and all(0.0 <= float(sample) <= 100.0 for sample in gpu_samples)
        and len(hardware_samples) == len(gpu_samples)
        and (
            synthetic
            or (
                covers_timed_interval(cpu_samples)
                and len(cpu_samples)
                >= max(
                    1,
                    math.floor(
                        float(payload.get("wall_seconds", 0.0))
                        / (float(payload.get("sample_interval_ms", 0)) / 1000.0)
                    )
                    - 1,
                )
            )
        )
        and (
            synthetic
            or len(hardware_samples)
            >= max(
                1,
                math.floor(
                    float(payload.get("wall_seconds", 0.0))
                    / (float(payload.get("sample_interval_ms", 0)) / 1000.0)
                )
                - 1,
            )
        )
        and (synthetic or covers_timed_interval(hardware_samples))
        and all(
            int(sample.get("qpc_frequency", 0)) > 0
            and int(sample.get("qpc_ticks", -1)) >= 0
            and math.isfinite(float(sample.get("thermal_c", math.nan)))
            and sample.get("hardware_throttle") is False
            and isinstance(sample.get("gpu_processes"), list)
            for sample in hardware_samples
        )
        and payload.get("hardware_throttle_observed") is False
        and payload.get("gpu_process_allowlist_pass") is True
        and payload.get("unapproved_gpu_processes") == []
        and required_stages.issubset(stages)
        and numeric_required.issubset(measurements)
        and all(
            measurements[stage].get("wall_seconds") is not None
            and float(measurements[stage]["wall_seconds"]) >= 0.0
            and measurements[stage].get("cpu_seconds") is not None
            and float(measurements[stage]["cpu_seconds"]) >= 0.0
            for stage in numeric_required
        )
    )
    return valid  # MUTATION_ANCHOR:G11


def g12_controlled_conditions(payload: dict[str, Any]) -> bool:
    thermal_delta = abs(
        float(payload.get("thermal_after_c", math.inf))
        - float(payload.get("thermal_before_c", -math.inf))
    )
    valid = (
        payload.get("preload_quiet_pass") is True
        and math.isclose(
            float(payload.get("preload_duration_seconds", math.nan)),
            60.0,
            rel_tol=0.0,
            abs_tol=0.05,
        )
        and float(payload.get("preload_elapsed_seconds", -math.inf)) >= 60.0
        and payload.get("preload_cpu_formula")
        == "(DeltaKernel-DeltaIdle+DeltaUser)/(DeltaKernel+DeltaUser)"
        and float(payload.get("external_busy_fraction", math.inf))
        <= float(payload.get("external_busy_max", -math.inf))
        and payload.get("power_plan_before") == payload.get("power_plan_after")
        and bool(payload.get("power_plan_before"))
        and thermal_delta <= float(payload.get("thermal_delta_max_c", -math.inf))
        and float(payload.get("thermal_before_c", math.inf))
        >= float(payload.get("start_temperature_min_c", math.inf))
        and float(payload.get("thermal_before_c", -math.inf))
        <= float(payload.get("start_temperature_max_c", -math.inf))
        and payload.get("telemetry_sample_interval_ms") == 10
        and payload.get("hardware_throttle_observed") is False
        and payload.get("gpu_process_allowlist_pass") is True
        and payload.get("cache_state") in {"WARM", "COLD_RESET"}
        and (
            payload.get("cache_state") != "COLD_RESET"
            or payload.get("input_preflight_io") == "WINDOWS_NO_BUFFERING"
        )
        and (
            payload.get("cache_state") != "COLD_RESET"
            or payload.get("executable_preflight_io") == "WINDOWS_NO_BUFFERING"
        )
        and payload.get("observer_hash_control") == "PASS"
    )
    return valid  # MUTATION_ANCHOR:G12


def alternating_schedule(
    settings: Iterable[str], repetitions: int = 6
) -> list[dict[str, Any]]:
    ordered = list(settings)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("at least one unique setting is required")
    rows: list[dict[str, Any]] = []
    for position, setting in enumerate(ordered):
        rows.append(
            {
                "phase": "warmup",
                "repetition": 0,
                "direction": "forward",
                "position": position,
                "setting_id": setting,
            }
        )
    for repetition in range(1, repetitions + 1):
        direction = "forward" if repetition % 2 else "reverse"
        sweep = ordered if direction == "forward" else list(reversed(ordered))
        for position, setting in enumerate(sweep):
            rows.append(
                {
                    "phase": "scored",
                    "repetition": repetition,
                    "direction": direction,
                    "position": position,
                    "setting_id": setting,
                }
            )
    return rows


def cold_pair_schedule(
    settings: Iterable[str], repetitions: int = 6
) -> list[dict[str, Any]]:
    ordered = list(settings)
    if not ordered or len(set(ordered)) != len(ordered):
        raise ValueError("at least one unique setting is required")
    rows: list[dict[str, Any]] = []
    for repetition in range(1, repetitions + 1):
        direction = "forward" if repetition % 2 else "reverse"
        sweep = ordered if direction == "forward" else list(reversed(ordered))
        for position, setting in enumerate(sweep):
            pair_id = f"r{repetition}-{setting}"
            for pair_member in ("cold", "warm"):
                rows.append(
                    {
                        "phase": "scored",
                        "repetition": repetition,
                        "direction": direction,
                        "position": position,
                        "setting_id": setting,
                        "pair_id": pair_id,
                        "pair_member": pair_member,
                    }
                )
    return rows


def g13_schedule_complete(payload: dict[str, Any]) -> bool:
    settings = payload.get("settings", [])
    repetitions = int(payload.get("repetitions", 6))
    schedule_kind = payload.get("schedule_kind", "ordinary")
    fields = ["phase", "repetition", "direction", "position", "setting_id"]
    if schedule_kind == "cold-pairs":
        fields.extend(("pair_id", "pair_member"))
    actual = [
        {key: row.get(key) for key in fields}
        for row in payload.get("records", [])
        if row.get("accepted") is True
    ]
    try:
        expected = (
            cold_pair_schedule(settings, repetitions)
            if schedule_kind == "cold-pairs"
            else alternating_schedule(settings, repetitions)
        )
    except (TypeError, ValueError):
        expected = []
    valid = (
        actual == expected
        and len(actual) == len(payload.get("records", []))
        and all(row.get("pair_complete") is True for row in payload.get("records", []))
        and schedule_kind in {"ordinary", "cold-pairs"}
    )
    return valid  # MUTATION_ANCHOR:G13


def g14_statistic_direction(payload: dict[str, Any]) -> bool:
    strehl = [float(value) for value in payload.get("strehl_wall_seconds", [])]
    comparators = {
        key: [float(value) for value in values]
        for key, values in payload.get("qualified_comparator_wall_seconds", {}).items()
    }
    candidate = [float(value) for value in payload.get("candidate_wall_seconds", [])]
    baseline = [float(value) for value in payload.get("baseline_wall_seconds", [])]
    comparator_mins = {
        key: min(values) for key, values in comparators.items() if values
    }
    comparator_identity = payload.get("comparator_identity", {})
    fastest = (
        min(
            comparator_mins,
            key=lambda setting_id: (
                comparator_mins[setting_id],
                comparator_identity.get(setting_id, {}).get("product_id", ""),
                comparator_identity.get(setting_id, {}).get("mode_id", ""),
            ),
        )
        if comparator_mins
        else None
    )
    expected_speedup = (
        comparator_mins[fastest] / min(strehl)
        if fastest is not None and strehl
        else math.nan
    )
    expected_regression = (
        min(candidate) / min(baseline) if candidate and baseline else math.nan
    )
    valid = (
        len(strehl) == 6
        and all(len(values) == 6 for values in comparators.values())
        and len(candidate) == 6
        and len(baseline) == 6
        and payload.get("selected_fastest_comparator") == fastest
        and set(comparator_identity) == set(comparators)
        and all(
            comparator_identity.get(setting_id, {}).get("product_id")
            == COMPARATOR_PRODUCT_IDS.get(
                comparator_identity.get(setting_id, {}).get("mode_id")
            )
            for setting_id in comparators
        )
        and math.isclose(
            float(payload.get("strehl_throughput_ratio", math.nan)),
            expected_speedup,
            rel_tol=1e-12,
        )
        and math.isclose(
            float(payload.get("candidate_default_wall_ratio", math.nan)),
            expected_regression,
            rel_tol=1e-12,
        )
        and payload.get("headline_statistic") == "minimum_of_six"
        and payload.get("dispersion_reported") is True
    )
    return valid  # MUTATION_ANCHOR:G14


def g15_cold_receipt(payload: dict[str, Any]) -> bool:
    receipt = payload.get("receipt", {})
    previously_used_boot_ids = {
        str(value) for value in payload.get("previously_used_boot_ids", [])
    }
    boot_id = str(receipt.get("windows_boot_id", ""))
    valid = (
        _hash_text(payload.get("receipt_sha256"))
        and receipt.get("schema") == "m153-actual-reboot-receipt-v1"
        and receipt.get("method") == "ACTUAL_REBOOT"
        and bool(boot_id)
        and boot_id not in previously_used_boot_ids
        and boot_id == str(payload.get("current_windows_boot_id", ""))
        and receipt.get("reset_complete") is True
        and receipt.get("no_prior_m11_invocation_this_boot") is True
        and receipt.get("position_key") == payload.get("position_key")
        and bool(receipt.get("issued_utc"))
        and _hash_text(receipt.get("provider_sha256"))
        and _hash_text(receipt.get("campaign_sha256"))
        and receipt.get("campaign_sha256") == payload.get("campaign_sha256")
    )
    return valid  # MUTATION_ANCHOR:G15


def g16_live_epoch(payload: dict[str, Any]) -> bool:
    frequency = int(payload.get("qpc_frequency", 0))
    shutter_close = int(payload.get("frame_100_shutter_close_qpc_ticks", -1))
    available = int(payload.get("frame_100_available_qpc_ticks", -1))
    completed = int(payload.get("finalized_qpc_ticks", -1))
    reported = float(payload.get("latency_seconds", math.nan))
    valid = (
        payload.get("count") == 100
        and payload.get("signed_acquisition_trace_verified") is True
        and payload.get("frame_100_source_hash_verified") is True
        and payload.get("frame_100_atomic_hardlink_reveal") is True
        and payload.get("preavailability_read_locks_enforced") is True
        and _hash_text(payload.get("cadence_manifest_sha256"))
        and frequency > 0
        and int(payload.get("marker_qpc_frequency", -1)) == frequency
        and shutter_close >= int(payload.get("process_started_qpc_ticks", 0))
        and available >= shutter_close
        and completed >= available
        and math.isclose(
            reported,
            (completed - shutter_close) / frequency,
            rel_tol=1e-12,
        )
    )
    return valid  # MUTATION_ANCHOR:G16


def g17_m12_joint(payload: dict[str, Any]) -> bool:
    m11 = payload.get("m11", {})
    m12 = payload.get("m12", {})
    m11_cells = m11.get("worker16_cells", {})
    m12_cells = m12.get("worker16_cells", {})
    valid = (
        payload.get("bridge_status") == "ELIGIBLE"
        and m11.get("verdict") == "PASS"
        and m11.get("cross_worker_identity_verdict") == "PASS"
        and set(m11_cells) == {"33", "105", "299"}
        and set(m12_cells) == {"33", "105", "299"}
        and all(
            len(m11_cells[count].get("settings_sha256", [])) == 1
            and all(
                _hash_text(value)
                for value in m11_cells[count].get("settings_sha256", [])
            )
            and len(m11_cells[count].get("input_manifest_sha256", [])) == 1
            and all(
                _hash_text(value)
                for value in m11_cells[count].get("input_manifest_sha256", [])
            )
            and len(m11_cells[count].get("input_content_sha256", [])) == 1
            and all(
                _hash_text(value)
                for value in m11_cells[count].get("input_content_sha256", [])
            )
            and len(m11_cells[count].get("output_sha256", [])) == 6
            and all(
                _hash_text(value) for value in m11_cells[count].get("output_sha256", [])
            )
            and len(m11_cells[count].get("pixel_sha256", [])) == 6
            and all(
                _hash_text(value) for value in m11_cells[count].get("pixel_sha256", [])
            )
            and m11_cells[count].get("settings_sha256")
            == m12_cells[count].get("settings_sha256")
            and m11_cells[count].get("input_manifest_sha256")
            == m12_cells[count].get("input_manifest_sha256")
            and m11_cells[count].get("input_content_sha256")
            == m12_cells[count].get("input_content_sha256")
            and m11_cells[count].get("output_sha256")
            == m12_cells[count].get("output_sha256")
            and m11_cells[count].get("pixel_sha256")
            == m12_cells[count].get("pixel_sha256")
            for count in ("33", "105", "299")
        )
    )
    return valid  # MUTATION_ANCHOR:G17


def g18_commissioning_required(payload: dict[str, Any]) -> bool:
    commission = payload.get("commission", {})
    build_audit = payload.get("build_audit", {})
    valid = (
        payload.get("real_run_requested") is True
        and payload.get("authorized_by") == "M153_ORCHESTRATOR"
        and _hash_text(payload.get("actual_contract_sha256"))
        and payload.get("actual_contract_sha256")
        == payload.get("authorized_contract_sha256")
        and _hash_text(payload.get("actual_campaign_sha256"))
        and payload.get("actual_campaign_sha256")
        == payload.get("authorized_campaign_sha256")
        and payload.get("contract_allows_real_run") is True
        and commission.get("schema") == "m153-formal-commission-v1"
        and commission.get("status") == "PASS"
        and commission.get("contract", {}).get("sha256")
        == payload.get("actual_contract_sha256")
        and commission.get("flat_null_pass") is True
        and commission.get("async_child_pass") is True
        and commission.get("formal_slowdown_seconds") == 1.0
        and 0.95 <= float(commission.get("observed_slowdown_seconds", math.nan)) <= 1.05
        and commission.get("formal_speedup_seconds") == -1.0
        and -1.05
        <= float(commission.get("observed_speedup_seconds", math.nan))
        <= -0.95
        and commission.get("slowdown_pass") is True
        and commission.get("speedup_pass") is True
        and commission.get("comparative_ratio_bidirectional_pass") is True
        and _hash_text(commission.get("artifact_sha256"))
        and build_audit.get("schema") == "m153-build-audit-v1"
        and build_audit.get("status") == "PASS"
        and build_audit.get("source_bindings_pass") is True
        and build_audit.get("census_internal_checks_pass") is True
        and int(build_audit.get("guard_count", 0)) == len(GUARD_REGISTRY)
        and build_audit.get("contract", {}).get("sha256")
        == payload.get("actual_contract_sha256")
        and build_audit.get("formal_m11_verdict") == "UNMEASURED"
        and _hash_text(build_audit.get("artifact_sha256"))
    )
    return valid  # MUTATION_ANCHOR:G18


def g19_arm_symmetry(payload: dict[str, Any]) -> bool:
    allowed_factor = {
        "comparative": "program-and-frozen-mode",
        "product-baseline": "build",
        "product-acceleration": "acceleration-mode",
    }.get(payload.get("comparison"))
    held_fixed = payload.get("held_fixed_sha256", [])
    valid = (
        allowed_factor is not None
        and payload.get("changed_factor_groups") == [allowed_factor]
        and len(held_fixed) >= 2
        and all(_hash_text(value) for value in held_fixed)
        and len(set(held_fixed)) == 1
        and payload.get("confounds") == []
    )
    return valid  # MUTATION_ANCHOR:G19


def g20_aggregate_reduction(payload: dict[str, Any]) -> bool:
    kind = payload.get("statistic_kind")
    valid = False
    if kind == "comparative":
        cells = payload.get("capture_minima", {})
        if set(cells) == {"33", "105", "299"}:
            strehl = {
                count: float(row["strehl_minimum_wall_seconds"])
                for count, row in cells.items()
            }
            comparator = {
                count: float(row["selected_comparator_minimum_wall_seconds"])
                for count, row in cells.items()
            }
            if all(value > 0.0 for value in strehl.values()) and all(
                value > 0.0 for value in comparator.values()
            ):
                ratios = {count: comparator[count] / strehl[count] for count in cells}
                pooled = sum(comparator.values()) / sum(strehl.values())
                valid = (
                    payload.get("capture_ratios") == ratios
                    and math.isclose(
                        float(payload.get("pooled_ratio", math.nan)),
                        pooled,
                        rel_tol=1e-12,
                    )
                    and payload.get("all_bars_pass")
                    is (
                        all(ratio >= 2.0 for ratio in ratios.values()) and pooled >= 2.0
                    )
                )
    elif kind == "cold":
        cold = [float(value) for value in payload.get("cold_wall_seconds", [])]
        warm = [float(value) for value in payload.get("warm_wall_seconds", [])]
        differences = [
            cold_value - warm_value for cold_value, warm_value in zip(cold, warm)
        ]
        valid = (
            len(cold) == 6
            and len(warm) == 6
            and payload.get("paired_cold_minus_warm_seconds") == differences
            and math.isclose(
                float(payload.get("maximum_seconds", math.nan)),
                max(differences, default=math.nan),
                rel_tol=1e-12,
            )
            and payload.get("all_pairs_pass")
            is all(value <= 20.0 for value in differences)
        )
    elif kind == "live":
        latencies = [float(value) for value in payload.get("latency_seconds", [])]
        valid = (
            len(latencies) == 6
            and math.isclose(
                float(payload.get("maximum_seconds", math.nan)),
                max(latencies, default=math.nan),
                rel_tol=1e-12,
            )
            and payload.get("all_replays_pass")
            is all(value <= 10.0 for value in latencies)
        )
    return valid  # MUTATION_ANCHOR:G20


GUARD_REGISTRY: dict[str, tuple[str, Guard]] = {
    "G01-owned-output": ("outputs stay in the owned M153 tree", g01_owned_output),
    "G02-capture-contract": (
        "registered capture identity and evidence class",
        g02_capture_contract,
    ),
    "G03-readonly-snapshot": ("source snapshot is unchanged", g03_readonly_snapshot),
    "G04-artifact-binding": (
        "artifact hashes match frozen expectations",
        g04_artifact_binding,
    ),
    "G05-quality-qualified": (
        "timed M11 mode passes the bound quality criterion",
        g05_quality_qualified,
    ),
    "G06-common-input-identity": (
        "comparative arms consume identical TIFF bytes",
        g06_common_input_identity,
    ),
    "G07-native-prefix": (
        "native arm consumes the exact registered ARW prefix",
        g07_native_prefix,
    ),
    "G08-settings-fingerprint": (
        "timed and quality-qualified settings are identical",
        g08_settings_fingerprint,
    ),
    "G09-process-tree-drained": (
        "all descendants finish inside the timer",
        g09_process_tree_drained,
    ),
    "G10-deliverable-finalized": (
        "TIFF and manifest are closed, flushed, and hashed",
        g10_deliverable_finalized,
    ),
    "G11-telemetry-complete": (
        "CPU, load, GPU, IO, and stages are present",
        g11_telemetry_complete,
    ),
    "G12-controlled-conditions": (
        "recorded power, thermal, load, and cache controls pass",
        g12_controlled_conditions,
    ),
    "G13-schedule-complete": (
        "warm-up and six alternating sweeps are complete",
        g13_schedule_complete,
    ),
    "G14-statistic-direction": (
        "minima and ratio directions implement M11",
        g14_statistic_direction,
    ),
    "G15-cold-receipt": (
        "each cold run has a unique actual-reboot receipt",
        g15_cold_receipt,
    ),
    "G16-live-epoch": (
        "live latency starts at frame 100 shutter close",
        g16_live_epoch,
    ),
    "G17-m12-joint": ("M12 worker-16 cells are the M11-passing outputs", g17_m12_joint),
    "G18-commissioning-required": (
        "real runs require formal null, slowdown, speedup, and ratio controls",
        g18_commissioning_required,
    ),
    "G19-arm-symmetry": (
        "each comparison changes one registered factor group",
        g19_arm_symmetry,
    ),
    "G20-aggregate-reduction": (
        "pooled, paired-cold, and maximum-live reductions implement M11",
        g20_aggregate_reduction,
    ),
}


def evaluate_guard(guard_id: str, payload: dict[str, Any]) -> GuardResult:
    if guard_id not in GUARD_REGISTRY:
        raise KeyError(f"unknown guard {guard_id!r}")
    name, predicate = GUARD_REGISTRY[guard_id]
    try:
        passed = bool(predicate(payload))
        failure = None if passed else f"{guard_id} rejected the supplied evidence"
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        passed = False
        failure = f"{guard_id} could not validate evidence: {error}"
    return GuardResult(guard_id, name, passed, failure)


def require_guard(guard_id: str, payload: dict[str, Any]) -> GuardResult:
    result = evaluate_guard(guard_id, payload)
    if not result.passed:
        raise ValueError(result.failure)
    return result


def describe(values: Iterable[float]) -> dict[str, float | int]:
    samples = [float(value) for value in values]
    if not samples:
        raise ValueError("at least one sample is required")
    median = statistics.median(samples)
    mad = statistics.median(abs(value - median) for value in samples)
    return {
        "count": len(samples),
        "minimum": min(samples),
        "median": median,
        "maximum": max(samples),
        "range": max(samples) - min(samples),
        "mad": mad,
        "scaled_mad": 1.4826 * mad,
        "mean": statistics.fmean(samples),
        "sample_sd": statistics.stdev(samples) if len(samples) > 1 else 0.0,
        "relative_range": (
            (max(samples) - min(samples)) / min(samples) if min(samples) > 0.0 else None
        ),
    }


_T_CRITICAL_975 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def paired_mean_interval(differences: Iterable[float]) -> dict[str, Any]:
    samples = [float(value) for value in differences]
    if len(samples) < 2:
        raise ValueError("at least two paired differences are required")
    estimate = statistics.fmean(samples)
    standard_error = statistics.stdev(samples) / math.sqrt(len(samples))
    critical = _T_CRITICAL_975.get(len(samples) - 1, 1.96)
    half_width = critical * standard_error
    return {
        "method": "two-sided paired-mean t interval",
        "confidence": 0.95,
        "pairs": len(samples),
        "estimate_seconds": estimate,
        "standard_error_seconds": standard_error,
        "lower_seconds": estimate - half_width,
        "upper_seconds": estimate + half_width,
        "no_difference_seconds": 0.0,
        "covers_no_difference": estimate - half_width <= 0.0 <= estimate + half_width,
        "dispersion": describe(samples),
    }
