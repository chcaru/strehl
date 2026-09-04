"""Commission the M152 M3 checker without opening any holdout output.

Synthetic profiles provide exact null, defect, sign, and improvement arms.
The only real pixels used by this script are untouched RAW inputs from the
registered non-holdout horizontal-razor control.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy import ndimage

from census_common import (
    HERE,
    bilinear_profile,
    decode_green,
    load_definition,
    nearest_rank,
    sha256_file,
)
from m3_checker import (
    SiteProfiles,
    load_checker_definition,
    score_site,
    summarize,
)


OUT = HERE / "out" / "m3-commission.json"
MANIFEST = HERE / "out" / "census-manifest.json"
MASTER_SEED = 152_202_609_04


def write_json(path: Path, value: Any) -> None:
    encoded = json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False
    )
    path.write_text(encoded + "\n", encoding="ascii")


def logistic_profile(
    offsets: np.ndarray, dark: float, step: float, width: float
) -> np.ndarray:
    return dark + step / (1.0 + np.exp(-offsets / width))


def edge_patch(dark: float, step: float, width: float, angle: float) -> np.ndarray:
    yy, xx = np.indices((128, 128), dtype=np.float64)
    x = xx - 63.5
    y = yy - 63.5
    normal = x * math.cos(angle) + y * math.sin(angle)
    texture = 0.006 * step * (
        np.sin(2.0 * math.pi * xx / 5.0)
        + 0.7 * np.sin(2.0 * math.pi * yy / 6.0 + 0.3)
    )
    return logistic_profile(normal, dark, step, width) + texture


def rim_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    negative = (offsets >= -24.0) & (offsets <= -12.0)
    positive = (offsets >= 12.0) & (offsets <= 24.0)
    output[negative] -= amplitude * step
    output[positive] += amplitude * step
    return output


def opposite_sign_rim_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    negative = (offsets >= -24.0) & (offsets <= -12.0)
    positive = (offsets >= 12.0) & (offsets <= 24.0)
    output[negative] += amplitude * step
    output[positive] -= amplitude * step
    return output


def veil_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    support = (np.abs(offsets) >= 16.0) & (np.abs(offsets) <= 200.0)
    output[support] += amplitude * step
    return output


def one_sided_far_veil_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    # Exactly 200 native-pixel samples, +33 through +232 inclusive.  The first
    # scored halo coordinate is +32, so this is a pure test of broad-veil
    # aggregation rather than a disguised narrow-rim test.
    support = (offsets >= 33.0) & (offsets <= 232.0)
    output[support] += amplitude * step
    return output


def planted_patch(
    base: np.ndarray, step: float, rim: float = 0.0, veil: float = 0.0
) -> np.ndarray:
    yy, xx = np.indices(base.shape, dtype=np.float64)
    normal = xx - 63.5
    output = base.copy()
    if rim:
        output[(normal >= -24.0) & (normal <= -12.0)] -= rim * step
        output[(normal >= 12.0) & (normal <= 24.0)] += rim * step
    if veil:
        output[(np.abs(normal) >= 16.0) & (np.abs(normal) <= 63.5)] += veil * step
    return output


def synthetic_population(
    plant: Callable[[np.ndarray, np.ndarray, float], np.ndarray],
    patch_plant: Callable[[np.ndarray, float], np.ndarray],
    checker_definition: dict[str, Any],
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(MASTER_SEED)
    offsets = np.arange(-400.0, 401.0, 1.0)
    capture_ids = checker_definition["site_population"]["required_capture_ids"]
    results: list[dict[str, Any]] = []
    for index in range(500):
        step = float(rng.uniform(0.25, 0.75))
        dark = float(rng.uniform(0.05, 0.15))
        width = float(rng.uniform(1.6, 2.4))
        base = logistic_profile(offsets, dark, step, width)
        # The exact clean source is explicitly present, so a healthy convex
        # input result is inside the source interval at every coordinate.
        ripple = 0.001 * step * np.sin(2.0 * math.pi * offsets / 37.0 + index)
        sources = np.stack([base - ripple, base, base + ripple])
        output = plant(base, offsets, step)
        patch = edge_patch(dark, step, width, angle=0.0)
        output_patch = patch_plant(patch, step)
        site = SiteProfiles(
            site_id=f"SYN-{index + 1:04d}",
            capture_id=capture_ids[index % len(capture_ids)],
            offsets_native_px=offsets,
            source_profiles=sources,
            output_profile=output,
            normalization_source_index=1,
            far_reference_source_index=1,
            sharp_source_index=1,
            output_patch=output_patch,
            sharp_source_patch=patch,
        )
        results.append(score_site(site, checker_definition))
    return results


def arm_summary(
    name: str,
    plant: Callable[[np.ndarray, np.ndarray, float], np.ndarray],
    patch_plant: Callable[[np.ndarray, float], np.ndarray],
    checker_definition: dict[str, Any],
    planted_amplitude: float,
) -> dict[str, Any]:
    results = synthetic_population(plant, patch_plant, checker_definition)
    summary = summarize(results, definition=checker_definition)
    summary["name"] = name
    summary["planted_amplitude_fraction_of_step"] = planted_amplitude
    summary["detection_rate"] = summary["affected_edge_rate"]
    side_max = [
        max(float(result["v_e_negative_side"]), float(result["v_e_positive_side"]))
        for result in results
    ]
    threshold = float(checker_definition["site_failure"]["threshold_max_h_v"])
    summary["proposed_side_max_detection_rate"] = float(
        np.mean(np.asarray(side_max) > threshold)
    )
    return summary


def real_raw_identity_null(
    census_definition: dict[str, Any],
    checker_definition: dict[str, Any],
) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
    selected = [
        site
        for site in manifest["m3"]["sufficiency"]["selected_sites"]
        if site["capture_id"] == "m3-razor-control"
    ][:50]
    if len(selected) != 50:
        raise RuntimeError("frozen manifest does not contain 50 razor-control sites")
    capture = next(
        item
        for item in census_definition["m3"]["captures"]
        if item["capture_id"] == "m3-razor-control"
    )
    source_dir = Path(capture["path"])
    roots = [Path(value) for value in census_definition["allowed_read_roots"]]
    cache: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    decoded_inputs: list[dict[str, Any]] = []
    for site in selected:
        name = str(site["source_file"])
        if name not in cache:
            decoded = decode_green(source_dir / name, roots, registered_iso=100.0)
            cache[name] = decoded
            decoded_inputs.append(decoded.input_record())
        decoded = cache[name]
        offsets, profile = bilinear_profile(
            decoded.green_luma_dn,
            (float(site["y_native_px"]) - 0.5) / 2.0,
            (float(site["x_native_px"]) - 0.5) / 2.0,
            float(site["normal_y"]),
            float(site["normal_x"]),
            reach_native_px=400,
        )
        # An untouched input is both the output-under-null and one legal source
        # profile.  This tests interpolation, orientation, normalization and
        # missing-data behavior without constructing a rendered product.
        source_profiles = profile[None, :]
        patch = np.outer(
            np.ones(128, dtype=np.float64),
            np.interp(
                np.linspace(-32.0, 32.0, 128),
                offsets,
                profile,
            ),
        )
        record = SiteProfiles(
            site_id=str(site["site_id"]),
            capture_id="m3-razor-control",
            offsets_native_px=offsets,
            source_profiles=source_profiles,
            output_profile=profile.copy(),
            normalization_source_index=0,
            far_reference_source_index=0,
            sharp_source_index=0,
            output_patch=patch,
            sharp_source_patch=patch.copy(),
        )
        results.append(score_site(record, checker_definition))
    h = np.asarray([row["h_e"] for row in results])
    v = np.asarray([row["v_e"] for row in results])
    affected = int(sum(bool(row["affected"]) for row in results))
    return {
        "name": "untouched_raw_identity_null",
        "source_capture": capture["path"],
        "source_class": capture["evidence_class"],
        "site_count": len(results),
        "median_h_e": nearest_rank(h, 0.50),
        "p99_h_e": nearest_rank(h, 0.99),
        "median_v_e": nearest_rank(v, 0.50),
        "p99_v_e": nearest_rank(v, 0.99),
        "affected_edge_count": affected,
        "false_positive_rate": affected / len(results),
        "decoded_inputs": decoded_inputs,
        "pass": affected / len(results) <= 0.01,
        "limitation": (
            "identity inclusion tests checker quietness and coordinate plumbing; "
            "it does not commission external warp error"
        ),
    }


def main() -> None:
    census_definition, census_definition_sha = load_definition()
    checker_definition, checker_definition_sha = load_checker_definition()
    actual_manifest_sha = sha256_file(MANIFEST)
    expected_manifest_sha = checker_definition["site_population"]["manifest_sha256"]
    if actual_manifest_sha != expected_manifest_sha:
        raise RuntimeError(
            "checker is pinned to another census manifest: "
            f"expected {expected_manifest_sha}, got {actual_manifest_sha}"
        )

    identity = lambda base, offsets, step: base.copy()
    identity_patch = lambda patch, step: patch.copy()
    rim6 = lambda base, offsets, step: rim_plant(base, offsets, step, 0.06)
    rim6_patch = lambda patch, step: planted_patch(patch, step, rim=0.06)
    opposite6 = lambda base, offsets, step: opposite_sign_rim_plant(
        base, offsets, step, 0.06
    )
    opposite6_patch = lambda patch, step: planted_patch(patch, step, rim=-0.06)
    veil6 = lambda base, offsets, step: veil_plant(base, offsets, step, 0.06)
    veil6_patch = lambda patch, step: planted_patch(patch, step, veil=0.06)
    one_side_far6 = lambda base, offsets, step: one_sided_far_veil_plant(
        base, offsets, step, 0.06
    )
    one_side_far6_patch = lambda patch, step: (
        patch
        + np.where(
            (np.indices(patch.shape)[1] - 63.5 >= 33.0),
            0.06 * step,
            0.0,
        )
    )
    combined6 = lambda base, offsets, step: veil_plant(
        rim_plant(base, offsets, step, 0.06), offsets, step, 0.06
    )
    combined6_patch = lambda patch, step: planted_patch(
        patch, step, rim=0.06, veil=0.06
    )
    improved = lambda base, offsets, step: veil_plant(
        rim_plant(base, offsets, step, 0.005), offsets, step, 0.005
    )
    improved_patch = lambda patch, step: planted_patch(
        patch, step, rim=0.005, veil=0.005
    )
    blurred = lambda base, offsets, step: ndimage.gaussian_filter1d(
        base, sigma=5.0, mode="nearest"
    )
    blurred_patch = lambda patch, step: ndimage.gaussian_filter(
        patch, sigma=5.0, mode="nearest"
    )

    arms = [
        arm_summary(
            "synthetic_healthy_null",
            identity,
            identity_patch,
            checker_definition,
            0.0,
        ),
        arm_summary(
            "planted_6pct_rim",
            rim6,
            rim6_patch,
            checker_definition,
            0.06,
        ),
        arm_summary(
            "planted_6pct_opposite_sign_rim",
            opposite6,
            opposite6_patch,
            checker_definition,
            0.06,
        ),
        arm_summary(
            "planted_6pct_200px_veil",
            veil6,
            veil6_patch,
            checker_definition,
            0.06,
        ),
        arm_summary(
            "planted_6pct_one_sided_far_200px_veil",
            one_side_far6,
            one_side_far6_patch,
            checker_definition,
            0.06,
        ),
        arm_summary(
            "planted_6pct_rim_and_veil",
            combined6,
            combined6_patch,
            checker_definition,
            0.06,
        ),
        arm_summary(
            "planted_improvement_0_5pct_rim_and_veil",
            improved,
            improved_patch,
            checker_definition,
            0.005,
        ),
        arm_summary(
            "planted_blur_guard",
            blurred,
            blurred_patch,
            checker_definition,
            0.0,
        ),
    ]
    by_name = {arm["name"]: arm for arm in arms}
    raw_null = real_raw_identity_null(census_definition, checker_definition)
    assertions = {
        "synthetic_null_passes": by_name["synthetic_healthy_null"]["verdict"]
        == "PASS",
        "raw_null_false_positive_at_most_1pct": raw_null["pass"],
        "positive_rim_detected_at_least_95pct": by_name["planted_6pct_rim"][
            "detection_rate"
        ]
        >= 0.95,
        "opposite_sign_rim_detected_at_least_95pct": by_name[
            "planted_6pct_opposite_sign_rim"
        ]["detection_rate"]
        >= 0.95,
        "veil_detected_at_least_95pct": by_name["planted_6pct_200px_veil"][
            "detection_rate"
        ]
        >= 0.95,
        "one_sided_far_veil_detected_at_least_95pct": by_name[
            "planted_6pct_one_sided_far_200px_veil"
        ]["detection_rate"]
        >= 0.95,
        "proposed_side_max_would_detect_one_sided_far_veil": by_name[
            "planted_6pct_one_sided_far_200px_veil"
        ]["proposed_side_max_detection_rate"]
        >= 0.95,
        "blur_guard_rejects_threefold_blur": (
            by_name["planted_blur_guard"]["median_edge_width_ratio"] > 1.05
            or by_name["planted_blur_guard"]["median_rho_edge"] < 0.90
        ),
        "improvement_reduces_h_by_at_least_5pp": (
            by_name["planted_6pct_rim_and_veil"]["median_h_e"]
            - by_name["planted_improvement_0_5pct_rim_and_veil"]["median_h_e"]
        )
        >= 0.05,
        "improvement_reduces_v_by_at_least_5pp": (
            by_name["planted_6pct_rim_and_veil"]["median_v_e"]
            - by_name["planted_improvement_0_5pct_rim_and_veil"]["median_v_e"]
        )
        >= 0.05,
    }
    failed = [name for name, passed in assertions.items() if not passed]

    result: dict[str, Any] = {
        "schema": "m152-m3-checker-commission-v1",
        "master_seed": MASTER_SEED,
        "census_definition_sha256": census_definition_sha,
        "checker_definition_sha256": checker_definition_sha,
        "checker_source_sha256": sha256_file(HERE / "m3_checker.py"),
        "commission_source_sha256": sha256_file(HERE / "commission_m3.py"),
        "census_manifest_sha256": actual_manifest_sha,
        "candidate_outputs_opened": 0,
        "holdout_outputs_opened": 0,
        "synthetic_site_count_per_arm": 500,
        "arms": arms,
        "untouched_raw_null": raw_null,
        "assertions": assertions,
        "verdict": "PASS" if not failed else "NOT_ADMITTED_COMMISSIONING_FAILED",
        "failed_assertions": failed,
    }
    write_json(OUT, result)
    digest = sha256_file(OUT)
    (OUT.with_suffix(".sha256")).write_text(
        f"{digest}  {OUT.name}\n", encoding="ascii"
    )
    for arm in arms:
        print(
            f"{arm['name']}: median_h={arm['median_h_e']:.6f} "
            f"p99_h={arm['p99_h_e']:.6f} "
            f"median_v={arm['median_v_e']:.6f} "
            f"p99_v={arm['p99_v_e']:.6f} "
            f"affected={arm['affected_edge_rate']:.6f}"
        )
    print(
        "untouched_raw_identity_null: "
        f"median_h={raw_null['median_h_e']:.6f} "
        f"p99_h={raw_null['p99_h_e']:.6f} "
        f"median_v={raw_null['median_v_e']:.6f} "
        f"p99_v={raw_null['p99_v_e']:.6f} "
        f"false_positive={raw_null['false_positive_rate']:.6f}"
    )
    print(f"commission sha256={digest}")
    if failed:
        print("NOT ADMITTED: failed assertions=" + ",".join(failed))
        raise SystemExit(3)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
