"""Incremental commissioning battery for the M147 preflight.

Each invocation runs one bounded arm and merges its result into
out/commission.json.  This keeps CPU bursts short while another measurement
campaign shares the host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy import ndimage

from preflight import (
    PARAMETERS_SHA256,
    MeasurementRefusal,
    decode_arw,
    estimate_planes,
    evaluate_measurements,
)


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "out" / "commission.json"
DEFAULT_SOURCE = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl\flat-sw4-cpl"
    r"\flat-et1s-sw4-cpl\DSC00042.ARW"
)
NULL_OTHER = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl\flat-sw4-cpl"
    r"\flat-et1s-sw4-cpl\DSC00043.ARW"
)
MASTER_SEED = 147_202_609
NOMINAL_RATIO = 2.0312

RULES: dict[str, Any] = {
    "schema": "m147-commission-rules-v1",
    "uniform_scale_maximum_relative_error": 0.0025,
    "null_maximum_relative_error": 0.0025,
    "mild_nuisance_maximum_relative_error": 0.0025,
    "coverage_claim": 0.95,
    "coverage_trials": 20,
    "coverage_acceptable_count": [18, 20],
    "never_pass_truth_at_or_below": 2.0,
    "alias_required_outcome": "REFUSED",
    "degenerate_required_outcome": "REFUSED",
}
RULES_SHA256 = hashlib.sha256(
    json.dumps(RULES, sort_keys=True, separators=(",", ":")).encode("ascii")
).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def analytic_grid(
    shape: tuple[int, int] = (1536, 2048),
    period: float = 64.0,
    angle_degrees: float = 4.0,
    fundamental: float = 700.0,
    harmonic_2: float = 120.0,
    harmonic_3: float = 40.0,
    noise_sd: float = 2.0,
    seed: int = MASTER_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.indices(shape, dtype=np.float32)
    theta = math.radians(angle_degrees)
    rng = np.random.default_rng(seed)

    def one(dx: float, dy: float) -> np.ndarray:
        xx = x + dx
        yy = y + dy
        u = xx * math.cos(theta) + yy * math.sin(theta)
        v = -xx * math.sin(theta) + yy * math.cos(theta)
        phase_u = 2.0 * math.pi * u / period
        phase_v = 2.0 * math.pi * v / period
        image = (
            2400.0
            + fundamental * (np.cos(phase_u) + np.cos(phase_v))
            + harmonic_2 * (np.cos(2.0 * phase_u) + np.cos(2.0 * phase_v))
            + harmonic_3 * (np.cos(3.0 * phase_u) + np.cos(3.0 * phase_v))
            + 250.0 * (x / max(1, shape[1] - 1))
            - 180.0 * (y / max(1, shape[0] - 1))
        )
        image += rng.normal(0.0, noise_sd, shape)
        return image.astype(np.float32)

    return one(0.0, 0.0), one(0.5, 0.5)


def affine_plane(
    image: np.ndarray,
    scale_y: float,
    scale_x: float,
    rotation_degrees: float = 0.0,
    blur_sigma: float = 0.0,
    gradient_fraction: float = 0.0,
    seed: int = MASTER_SEED,
) -> np.ndarray:
    theta = math.radians(rotation_degrees)
    rotation = np.array(
        [[math.cos(theta), math.sin(theta)], [-math.sin(theta), math.cos(theta)]],
        dtype=np.float64,
    )
    matrix = rotation @ np.diag([1.0 / scale_y, 1.0 / scale_x])
    center = (np.asarray(image.shape, dtype=np.float64) - 1.0) / 2.0
    transformed = ndimage.affine_transform(
        image,
        matrix=matrix,
        offset=center - matrix @ center,
        order=3,
        mode="reflect",
        prefilter=True,
    )
    if blur_sigma > 0.0:
        transformed = ndimage.gaussian_filter(transformed, blur_sigma, mode="reflect")
    if gradient_fraction:
        y, x = np.indices(image.shape, dtype=np.float32)
        ramp = (
            (x / max(1, image.shape[1] - 1) - 0.5)
            + 0.7 * (y / max(1, image.shape[0] - 1) - 0.5)
        )
        transformed = transformed * (1.0 + gradient_fraction * ramp)
    rng = np.random.default_rng(seed)
    transformed = transformed + rng.normal(0.0, 2.0, image.shape)
    return transformed.astype(np.float32)


def affine_planes(
    planes: tuple[np.ndarray, np.ndarray],
    scale_y: float,
    scale_x: float,
    **kwargs: Any,
) -> tuple[np.ndarray, np.ndarray]:
    return tuple(
        affine_plane(plane, scale_y, scale_x, seed=MASTER_SEED + index, **kwargs)
        for index, plane in enumerate(planes)
    )  # type: ignore[return-value]


def perspective_plane(image: np.ndarray, amount: float) -> np.ndarray:
    height, width = image.shape
    y, x = np.indices(image.shape, dtype=np.float32)
    normalized_y = (y - (height - 1) / 2.0) / max(1.0, (height - 1) / 2.0)
    local_inverse_scale = 1.0 + amount * normalized_y
    source_x = (x - (width - 1) / 2.0) * local_inverse_scale + (width - 1) / 2.0
    source_y = (
        (y - (height - 1) / 2.0) * local_inverse_scale
        + (height - 1) / 2.0
    )
    return ndimage.map_coordinates(
        image,
        [source_y, source_x],
        order=3,
        mode="reflect",
        prefilter=True,
    ).astype(np.float32)


def run_pair(
    reference_planes: tuple[np.ndarray, np.ndarray],
    scored_planes: tuple[np.ndarray, np.ndarray],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        reference = estimate_planes(reference_planes, "reference")
        scored = estimate_planes(scored_planes, "TC0")
        decision = evaluate_measurements(reference, scored)
        return {
            "measurement_status": "OK",
            "reference_period_green_px": reference["period_green_px"],
            "scored_period_green_px": scored["period_green_px"],
            "reference_block_count": reference["spatial_block_count"],
            "scored_block_count": scored["spatial_block_count"],
            "decision": decision,
            "elapsed_seconds": time.perf_counter() - started,
        }
    except MeasurementRefusal as refusal:
        return {
            "measurement_status": "REFUSED",
            "reason_code": refusal.code,
            "message": refusal.message,
            "action": refusal.action,
            "diagnostics": refusal.details,
            "elapsed_seconds": time.perf_counter() - started,
        }


def arm_alias(_: Path) -> dict[str, Any]:
    reference = analytic_grid(fundamental=700.0, harmonic_2=80.0)
    # Same physical 64-pixel period, but a much stronger second harmonic in
    # the scored frame.  A harmonic lock would report a false ratio near 2.
    scored = analytic_grid(fundamental=90.0, harmonic_2=900.0, seed=MASTER_SEED + 10)
    result = run_pair(reference, scored)
    result.update(
        {
            "truth_ratio": 1.0,
            "plant": "same 64 px primitive; scored second harmonic dominates",
            "required": "typed refusal; never a numeric PASS",
        }
    )
    result["pass"] = result["measurement_status"] == "REFUSED"
    return result


def arm_alias_third(_: Path) -> dict[str, Any]:
    reference = analytic_grid(
        fundamental=700.0,
        harmonic_2=60.0,
        harmonic_3=30.0,
    )
    scored = analytic_grid(
        fundamental=90.0,
        harmonic_2=20.0,
        harmonic_3=900.0,
        seed=MASTER_SEED + 11,
    )
    result = run_pair(reference, scored)
    result.update(
        {
            "truth_ratio": 1.0,
            "plant": "same 64 px primitive; scored third harmonic dominates",
            "required": "typed refusal; never a numeric PASS",
        }
    )
    result["pass"] = result["measurement_status"] == "REFUSED"
    return result


def arm_anisotropic(_: Path) -> dict[str, Any]:
    reference = analytic_grid()
    scored = affine_planes(
        reference,
        scale_y=1.0 / NOMINAL_RATIO,
        scale_x=1.0 / (NOMINAL_RATIO * 1.03),
        rotation_degrees=3.0,
    )
    result = run_pair(reference, scored)
    result.update(
        {
            "truth_axis_ratios": [NOMINAL_RATIO, NOMINAL_RATIO * 1.03],
            "plant": "3% disagreement between axis sampling ratios",
            "required": "ANISOTROPIC_SCALE_CHANGE refusal",
        }
    )
    result["pass"] = (
        result["measurement_status"] == "REFUSED"
        and result["reason_code"] == "ANISOTROPIC_SCALE_CHANGE"
    )
    return result


def arm_perspective(_: Path) -> dict[str, Any]:
    reference = analytic_grid()
    base_scored = affine_planes(
        reference,
        scale_y=1.0 / NOMINAL_RATIO,
        scale_x=1.0 / NOMINAL_RATIO,
    )
    scored = tuple(perspective_plane(plane, 0.035) for plane in base_scored)
    result = run_pair(reference, scored)  # type: ignore[arg-type]
    result.update(
        {
            "plant": "projective local scale gradient of approximately +/-3.5%",
            "required": "never PASS; local lower envelope must expose the defect",
        }
    )
    result["pass"] = (
        result["measurement_status"] == "REFUSED"
        or result.get("decision", {}).get("verdict") == "FAIL"
    )
    return result


def arm_blur_mild(_: Path) -> dict[str, Any]:
    reference = analytic_grid()
    scored = affine_planes(
        reference,
        scale_y=1.0 / NOMINAL_RATIO,
        scale_x=1.0 / NOMINAL_RATIO,
        rotation_degrees=-4.0,
        blur_sigma=2.5,
        gradient_fraction=0.35,
    )
    result = run_pair(reference, scored)
    result.update(
        {
            "truth_ratio": NOMINAL_RATIO,
            "plant": "2.5 green-pixel Gaussian blur, rotation, and 35% gradient",
            "required": "numeric estimate within 0.25% of truth",
        }
    )
    recovered = result.get("decision", {}).get("sampling_ratio")
    error = (
        abs(float(recovered) / NOMINAL_RATIO - 1.0)
        if recovered is not None
        else None
    )
    result["relative_error"] = error
    result["pass"] = (
        result["measurement_status"] == "OK"
        and error is not None
        and error <= RULES["mild_nuisance_maximum_relative_error"]
    )
    return result


def arm_blur_severe(_: Path) -> dict[str, Any]:
    reference = analytic_grid()
    scored = affine_planes(
        reference,
        scale_y=1.0 / NOMINAL_RATIO,
        scale_x=1.0 / NOMINAL_RATIO,
        blur_sigma=18.0,
    )
    result = run_pair(reference, scored)
    result.update(
        {
            "plant": "18 green-pixel Gaussian blur",
            "required": "typed refusal; never numeric",
        }
    )
    result["pass"] = result["measurement_status"] == "REFUSED"
    return result


def arm_partial_grid(_: Path) -> dict[str, Any]:
    reference = analytic_grid()
    scored = affine_planes(
        reference,
        scale_y=1.0 / NOMINAL_RATIO,
        scale_x=1.0 / NOMINAL_RATIO,
    )
    masked = []
    for plane in scored:
        y, x = np.indices(plane.shape)
        keep = (
            (abs(y - plane.shape[0] / 2.0) < 300)
            & (abs(x - plane.shape[1] / 2.0) < 350)
        )
        background = ndimage.gaussian_filter(plane, 100.0)
        masked.append(np.where(keep, plane, background).astype(np.float32))
    result = run_pair(reference, tuple(masked))  # type: ignore[arg-type]
    result.update(
        {
            "plant": "grid retained only in a 600x700 green-pixel window",
            "required": "GRID_TOO_SMALL or NO_COHERENT_GRID refusal",
        }
    )
    result["pass"] = result["measurement_status"] == "REFUSED"
    return result


def arm_no_grid(_: Path) -> dict[str, Any]:
    shape = (1536, 2048)
    y, x = np.indices(shape, dtype=np.float32)
    rng = np.random.default_rng(MASTER_SEED + 20)
    plane = (
        2200.0
        + 500.0 * x / shape[1]
        - 300.0 * y / shape[0]
        + ndimage.gaussian_filter(rng.normal(0.0, 20.0, shape), 8.0)
    ).astype(np.float32)
    result = run_pair((plane, plane.copy()), (plane.copy(), plane.copy()))
    result.update({"plant": "smooth illumination plus correlated noise"})
    result["pass"] = result["measurement_status"] == "REFUSED"
    return result


def arm_real_null(source: Path) -> dict[str, Any]:
    first = decode_arw(source)
    second = decode_arw(NULL_OTHER)
    result = run_pair(first.green_planes, second.green_planes)
    result.update(
        {
            "truth_ratio": 1.0,
            "source_sha256": first.file_sha256,
            "other_sha256": second.file_sha256,
        }
    )
    recovered = result.get("decision", {}).get("sampling_ratio")
    error = abs(float(recovered) - 1.0) if recovered is not None else None
    result["relative_error"] = error
    result["pass"] = (
        result["measurement_status"] == "OK"
        and error is not None
        and error <= RULES["null_maximum_relative_error"]
        and result["decision"]["interval"]["lower"] <= 1.0
        and result["decision"]["interval"]["upper"] >= 1.0
        and result["decision"]["verdict"] == "FAIL"
    )
    return result


SCALE_ERRORS = {
    "scale-low": -0.010,
    "scale-nominal": 0.0,
    "scale-inside": 0.014,
    "scale-outside": 0.017,
    "scale-large": 0.030,
}
REQUIRED_NONCOVERAGE_ARMS = [
    "alias",
    "alias-third",
    "anisotropic",
    "perspective",
    "blur-mild",
    "blur-severe",
    "partial-grid",
    "no-grid",
    "real-null",
    *SCALE_ERRORS,
]


def arm_scale(source: Path, name: str) -> dict[str, Any]:
    error = SCALE_ERRORS[name]
    truth = NOMINAL_RATIO / (1.0 + error)
    decoded = decode_arw(source)
    scored = affine_planes(
        decoded.green_planes,
        scale_y=1.0 / truth,
        scale_x=1.0 / truth,
    )
    result = run_pair(decoded.green_planes, scored)
    result.update(
        {
            "truth_ratio": truth,
            "tc0_magnification_error_fraction": error,
            "source_sha256": decoded.file_sha256,
        }
    )
    recovered = result.get("decision", {}).get("sampling_ratio")
    relative_error = (
        abs(float(recovered) / truth - 1.0) if recovered is not None else None
    )
    result["relative_error"] = relative_error
    expected_gate = "PASS" if truth > 2.0 else "FAIL"
    result["expected_point_side"] = expected_gate
    # The actual gate is intentionally conservative: a truth just above 2.0
    # may still fail when the lower uncertainty bound crosses 2.0.
    result["pass"] = (
        result["measurement_status"] == "OK"
        and relative_error is not None
        and relative_error <= RULES["uniform_scale_maximum_relative_error"]
        and not (
            truth <= RULES["never_pass_truth_at_or_below"]
            and result["decision"]["verdict"] == "PASS"
        )
    )
    return result


def arm_coverage(_: Path, index: int) -> dict[str, Any]:
    rng = np.random.default_rng(MASTER_SEED + 1000 + index)
    truth = float(rng.uniform(1.94, 2.07))
    reference_period = float(rng.uniform(58.0, 70.0))
    base_angle = float(rng.uniform(-8.0, 8.0))
    relative_angle = float(rng.uniform(-6.0, 6.0))
    shape = (1280, 1792)
    reference = analytic_grid(
        shape=shape,
        period=reference_period,
        angle_degrees=base_angle,
        noise_sd=float(rng.uniform(1.0, 8.0)),
        seed=MASTER_SEED + 2000 + index,
    )
    scored = analytic_grid(
        shape=shape,
        period=reference_period / truth,
        angle_degrees=base_angle + relative_angle,
        noise_sd=float(rng.uniform(1.0, 8.0)),
        seed=MASTER_SEED + 3000 + index,
    )
    blur = float(rng.uniform(0.0, 2.8))
    gradient = float(rng.uniform(-0.35, 0.35))
    scored = tuple(
        affine_plane(
            plane,
            scale_y=1.0,
            scale_x=1.0,
            blur_sigma=blur,
            gradient_fraction=gradient,
            seed=MASTER_SEED + 4000 + 2 * index + phase,
        )
        for phase, plane in enumerate(scored)
    )
    result = run_pair(reference, scored)  # type: ignore[arg-type]
    interval = result.get("decision", {}).get("interval")
    covered = bool(
        interval is not None and interval["lower"] <= truth <= interval["upper"]
    )
    result.update(
        {
            "trial_index": index,
            "truth_ratio": truth,
            "reference_period_green_px_truth": reference_period,
            "relative_rotation_degrees_plant": relative_angle,
            "blur_sigma_green_px": blur,
            "gradient_fraction": gradient,
            "covered": covered,
            "pass": result["measurement_status"] == "OK" and covered,
        }
    )
    return result


ARMS: dict[str, Callable[[Path], dict[str, Any]]] = {
    "alias": arm_alias,
    "alias-third": arm_alias_third,
    "anisotropic": arm_anisotropic,
    "perspective": arm_perspective,
    "blur-mild": arm_blur_mild,
    "blur-severe": arm_blur_severe,
    "partial-grid": arm_partial_grid,
    "no-grid": arm_no_grid,
    "real-null": arm_real_null,
}
COVERAGE_ARMS = {
    f"coverage-{index:02d}": index for index in range(RULES["coverage_trials"])
}


def load_output() -> dict[str, Any]:
    if OUTPUT.exists():
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    return {
        "schema": "m147-commission-v1",
        "rules": RULES,
        "rules_sha256": RULES_SHA256,
        "preflight_parameters_sha256": PARAMETERS_SHA256,
        "source_sha256": {
            "preflight.py": sha256_file(HERE / "preflight.py"),
            "commission.py": sha256_file(Path(__file__).resolve()),
        },
        "arms": {},
    }


def wilson_interval(successes: int, trials: int) -> list[float] | None:
    if trials == 0:
        return None
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denominator
    radius = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / trials
            + z * z / (4.0 * trials * trials)
        )
        / denominator
    )
    return [center - radius, center + radius]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--arm",
        required=True,
        choices=sorted([*ARMS, *SCALE_ERRORS, *COVERAGE_ARMS]),
    )
    parser.add_argument("--source-arw", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    source = args.source_arw.resolve()
    function = ARMS.get(args.arm)
    print(f"Running M147 commissioning arm: {args.arm}")
    started = time.perf_counter()
    if args.arm in COVERAGE_ARMS:
        result = arm_coverage(source, COVERAGE_ARMS[args.arm])
    elif function is None:
        result = arm_scale(source, args.arm)
    else:
        result = function(source)
    result["run_utc"] = datetime.now(timezone.utc).isoformat()
    result["wall_seconds"] = time.perf_counter() - started
    result["preflight_source_sha256"] = sha256_file(HERE / "preflight.py")
    result["commission_source_sha256"] = sha256_file(Path(__file__).resolve())

    output = load_output()
    current_source_hashes = {
        "preflight.py": sha256_file(HERE / "preflight.py"),
        "commission.py": sha256_file(Path(__file__).resolve()),
    }
    if (
        output.get("rules_sha256") != RULES_SHA256
        or output.get("preflight_parameters_sha256") != PARAMETERS_SHA256
        or output.get("source_sha256") != current_source_hashes
    ):
        raise RuntimeError(
            "existing commission artifact belongs to different frozen rules or source"
        )
    output["arms"][args.arm] = result
    coverage_rows = [
        output["arms"][name]
        for name in sorted(COVERAGE_ARMS)
        if name in output["arms"]
    ]
    covered = sum(row.get("covered") is True for row in coverage_rows)
    output["coverage"] = {
        "recorded_trials": len(coverage_rows),
        "covered_trials": covered,
        "observed_fraction": (
            covered / len(coverage_rows) if coverage_rows else None
        ),
        "wilson_95_interval": wilson_interval(covered, len(coverage_rows)),
        "complete": len(coverage_rows) == RULES["coverage_trials"],
        "acceptable_count": RULES["coverage_acceptable_count"],
        "pass": (
            len(coverage_rows) == RULES["coverage_trials"]
            and RULES["coverage_acceptable_count"][0]
            <= covered
            <= RULES["coverage_acceptable_count"][1]
        ),
    }
    required_present = all(name in output["arms"] for name in REQUIRED_NONCOVERAGE_ARMS)
    output["synthetic_commission"] = {
        "required_noncov_arms_present": required_present,
        "all_required_noncov_arms_pass": (
            required_present
            and all(output["arms"][name].get("pass") is True for name in REQUIRED_NONCOVERAGE_ARMS)
        ),
        "coverage_pass": output["coverage"]["pass"],
    }
    output["synthetic_commission"]["pass"] = (
        output["synthetic_commission"]["all_required_noncov_arms_pass"]
        and output["synthetic_commission"]["coverage_pass"]
    )
    output["field_commission"] = {
        "status": "BLOCKED",
        "reason": "real converter-on/converter-off approximately 2.03x pair not yet captured",
    }
    output["all_recorded_arms_pass"] = all(
        arm.get("pass") is True for arm in output["arms"].values()
    )
    output["updated_utc"] = datetime.now(timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
