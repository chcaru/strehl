"""Run the frozen M164 common-transfer-veto commissioning battery."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import scipy
import tifffile
from scipy import ndimage, stats

import transfer_veto as veto


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "commissioning.json"
Q = 1.0 / 65535.0
SEED = 164
CROP_SIZE = 512
CROP_ORIGINS = (
    (512, 512),
    (2500, 512),
    (5000, 512),
    (512, 2500),
    (2500, 2500),
    (5000, 2500),
)
SOURCES = (
    {
        "name": "coffee-bean",
        "path": Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff"),
        "sha256": "F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC",
    },
    {
        "name": "113MSDCF",
        "path": Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
        "sha256": "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    },
)

BLUR_SIGMAS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.60, 0.80, 1.00, 1.50, 2.00, 3.00)
USM_AMOUNTS = (0.001, 0.002, 0.005, 0.010, 0.020, 0.050, 0.100, 0.200, 0.500, 1.000)
GAIN_DELTAS = (0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.010, 0.020)
SHIFT_DISTANCES = (0.05, 0.10, 0.20, 0.35, 0.50)
IMPROVEMENT_NOISE_LSB = (0.0, 0.25, 0.50, 1.0, 2.0, 4.0, 8.0, 16.0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest().upper()


def quantize(values: np.ndarray) -> np.ndarray:
    return np.rint(np.clip(values, 0.0, 1.0) * 65535.0) / 65535.0


def srgb_inverse(values: np.ndarray) -> np.ndarray:
    return np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )


def load_crops() -> tuple[list[dict[str, Any]], list[np.ndarray]]:
    records: list[dict[str, Any]] = []
    crops: list[np.ndarray] = []
    for source in SOURCES:
        path = source["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual_hash = sha256_file(path)
        if actual_hash != source["sha256"]:
            raise RuntimeError(f"source hash mismatch: {path}")
        image = tifffile.memmap(path, mode="r")
        if image.shape != (4688, 7032, 3) or image.dtype != np.uint16:
            raise RuntimeError(
                f"unexpected source layout for {path}: {image.shape} {image.dtype}"
            )
        for index, (x, y) in enumerate(CROP_ORIGINS):
            encoded = (
                np.asarray(
                    image[y : y + CROP_SIZE, x : x + CROP_SIZE, 1],
                    dtype=np.float64,
                )
                / 65535.0
            )
            linear = srgb_inverse(encoded)
            low, high = np.quantile(linear, (0.005, 0.995))
            if not high > low:
                raise RuntimeError(f"degenerate crop {source['name']} {index}")
            normalized = 0.10 + 0.80 * np.clip((linear - low) / (high - low), 0.0, 1.0)
            crop = quantize(normalized)
            crop_id = f"{source['name']}-{index}"
            records.append(
                {
                    "id": crop_id,
                    "source": source["name"],
                    "origin_xy": [x, y],
                    "linear_percentiles_before_mapping": [float(low), float(high)],
                    "minimum": float(crop.min()),
                    "maximum": float(crop.max()),
                    "sha256_linear_u16_values": sha256_array(
                        np.rint(crop * 65535.0).astype(np.uint16)
                    ),
                }
            )
            crops.append(crop)
        del image
    return records, crops


def finite_or_none(value: Any) -> Any:
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (int, np.integer, bool)):
        return value.item() if isinstance(value, np.generic) else value
    return value


def compact(result: dict[str, Any], **labels: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        **labels,
        "status": result["status"],
        "fired": bool(result["fired"]),
        "difference_rms_lsb": finite_or_none(result.get("difference_rms_lsb")),
    }
    if "families" not in result:
        return record
    record["selected_family"] = result["selected_family"]
    record["firing_families"] = result["firing_families"]
    record["families"] = {}
    for family in result["families"]:
        record["families"][family["family"]] = {
            key: finite_or_none(family[key])
            for key in (
                "fired",
                "difference_rms_lsb",
                "kernel_effect_rms_lsb",
                "residual_rms_lsb",
                "residual_over_difference",
                "informative_tiles",
                "tile_q90",
                "fold_disagreement",
            )
        }
    return record


def selected_metric(record: dict[str, Any], key: str) -> float | None:
    family = record.get("selected_family")
    if family is None:
        return None
    value = record["families"][family][key]
    return None if value is None else float(value)


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    fires = sum(bool(record["fired"]) for record in records)
    metrics: dict[str, Any] = {}
    for key in (
        "difference_rms_lsb",
        "kernel_effect_rms_lsb",
        "residual_rms_lsb",
        "residual_over_difference",
        "tile_q90",
        "fold_disagreement",
    ):
        values: list[float] = []
        for record in records:
            if key == "difference_rms_lsb":
                value = record.get(key)
            else:
                value = selected_metric(record, key)
            if value is not None and np.isfinite(value):
                values.append(float(value))
        if values:
            metrics[key] = {
                "minimum": float(np.min(values)),
                "median": float(np.median(values)),
                "maximum": float(np.max(values)),
            }
    return {
        "trials": len(records),
        "fires": fires,
        "fire_rate": fires / len(records) if records else None,
        "selected_metrics": metrics,
    }


def group_by_strength(
    records: list[dict[str, Any]], strength_key: str, ordered: tuple[float, ...]
) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for strength in ordered:
        matching = [
            record
            for record in records
            if math.isclose(float(record[strength_key]), strength, rel_tol=0, abs_tol=1e-12)
        ]
        groups[f"{strength:g}"] = summarize(matching)
    reliable: float | None = None
    for index, strength in enumerate(ordered):
        tails = [
            groups[f"{later:g}"]["fires"] == groups[f"{later:g}"]["trials"]
            for later in ordered[index:]
        ]
        if all(tails):
            reliable = strength
            break
    return {
        "strength_key": strength_key,
        "by_strength": groups,
        "reliable_threshold": reliable,
    }


def evaluate_prepared(
    prepared: veto.PreparedTransferVeto,
    image_b: np.ndarray,
    **labels: Any,
) -> dict[str, Any]:
    return compact(prepared.evaluate(quantize(image_b)), **labels)


def interpolation_roundtrip(image: np.ndarray, distance: float) -> np.ndarray:
    moved = ndimage.shift(
        image,
        shift=(distance, distance),
        order=1,
        mode="reflect",
        prefilter=False,
    )
    return ndimage.shift(
        moved,
        shift=(-distance, -distance),
        order=1,
        mode="reflect",
        prefilter=False,
    )


def box_down_bilinear_up(image: np.ndarray) -> np.ndarray:
    low = image.reshape(
        image.shape[0] // 2,
        2,
        image.shape[1] // 2,
        2,
    ).mean(axis=(1, 3))
    output_y = (np.arange(image.shape[0], dtype=np.float64) + 0.5) / 2.0 - 0.5
    output_x = (np.arange(image.shape[1], dtype=np.float64) + 0.5) / 2.0 - 0.5
    yy, xx = np.meshgrid(output_y, output_x, indexing="ij")
    return ndimage.map_coordinates(
        low,
        (yy, xx),
        order=1,
        mode="reflect",
        prefilter=False,
    )


def smooth_random_mask(rng: np.random.Generator, shape: tuple[int, int]) -> np.ndarray:
    field = ndimage.gaussian_filter(
        rng.normal(size=shape), sigma=45.0, mode="reflect"
    )
    low, high = np.quantile(field, (0.10, 0.90))
    scaled = np.clip((field - low) / max(high - low, 1e-12), 0.0, 1.0)
    return scaled * scaled * (3.0 - 2.0 * scaled)


def noise_pair(
    scene: np.ndarray, rng: np.random.Generator, level_lsb: float
) -> tuple[np.ndarray, np.ndarray]:
    modulation = 0.60 + 0.80 * np.sqrt(scene)
    sigma = level_lsb * Q * modulation
    return (
        quantize(scene + rng.normal(size=scene.shape) * sigma),
        quantize(scene + rng.normal(size=scene.shape) * sigma),
    )


def run() -> dict[str, Any]:
    crop_records, crops = load_crops()
    rng = np.random.default_rng(SEED)

    identity: list[dict[str, Any]] = []
    disturbance: list[dict[str, Any]] = []
    blur: list[dict[str, Any]] = []
    sharpening: list[dict[str, Any]] = []
    scalar_gain: list[dict[str, Any]] = []
    blur_gain: list[dict[str, Any]] = []
    resampling: list[dict[str, Any]] = []
    common_improvement: list[dict[str, Any]] = []

    yy, xx = np.mgrid[:CROP_SIZE, :CROP_SIZE]
    disk = np.exp(
        -(
            (yy - 0.37 * CROP_SIZE) ** 2
            + (xx - 0.63 * CROP_SIZE) ** 2
        )
        / (2.0 * 22.0**2)
    )

    for crop_record, scene in zip(crop_records, crops, strict=True):
        crop_id = crop_record["id"]
        prepared = veto.prepare_transfer_veto(scene, Q)
        identity.append(compact(prepared.evaluate(scene), crop=crop_id))
        disturbance.append(
            evaluate_prepared(
                prepared,
                scene + 32.0 * Q * disk,
                crop=crop_id,
                disturbance_lsb=32.0,
            )
        )

        for sigma in BLUR_SIGMAS:
            blurred = ndimage.gaussian_filter(
                scene, sigma=sigma, mode="reflect", truncate=4.0
            )
            blur.append(
                evaluate_prepared(prepared, blurred, crop=crop_id, sigma=sigma)
            )

        radius_blur = ndimage.gaussian_filter(
            scene, sigma=1.0, mode="reflect", truncate=4.0
        )
        for amount in USM_AMOUNTS:
            sharpened = scene + amount * (scene - radius_blur)
            sharpening.append(
                evaluate_prepared(
                    prepared,
                    sharpened,
                    crop=crop_id,
                    radius=1.0,
                    amount=amount,
                )
            )

        for delta in GAIN_DELTAS:
            scalar_gain.append(
                evaluate_prepared(
                    prepared,
                    scene * (1.0 + delta),
                    crop=crop_id,
                    gain_delta=delta,
                )
            )

        for sigma in (0.40, 0.80, 1.50):
            blurred = ndimage.gaussian_filter(
                scene, sigma=sigma, mode="reflect", truncate=4.0
            )
            for gain in (0.97, 1.03):
                blur_gain.append(
                    evaluate_prepared(
                        prepared,
                        gain * blurred,
                        crop=crop_id,
                        sigma=sigma,
                        gain=gain,
                    )
                )

        for distance in SHIFT_DISTANCES:
            resampling.append(
                evaluate_prepared(
                    prepared,
                    interpolation_roundtrip(scene, distance),
                    crop=crop_id,
                    kind="bilinear-shift-roundtrip",
                    distance=distance,
                )
            )
        resampling.append(
            evaluate_prepared(
                prepared,
                box_down_bilinear_up(scene),
                crop=crop_id,
                kind="box-down-bilinear-up-2x",
                distance=2.0,
            )
        )

        blurred_a = quantize(
            ndimage.gaussian_filter(
                scene, sigma=0.80, mode="reflect", truncate=4.0
            )
        )
        common_b = quantize(
            blurred_a
            + 0.50
            * (
                blurred_a
                - ndimage.gaussian_filter(
                    blurred_a, sigma=1.0, mode="reflect", truncate=4.0
                )
            )
        )
        common_result = compact(
            veto.prepare_transfer_veto(blurred_a, Q).evaluate(common_b),
            crop=crop_id,
            amount=0.50,
        )
        mse_a = float(np.mean((blurred_a - scene) ** 2))
        mse_b = float(np.mean((common_b - scene) ** 2))
        common_result["truth_mse_a"] = mse_a
        common_result["truth_mse_b"] = mse_b
        common_result["truth_mse_ratio_b_over_a"] = mse_b / mse_a
        common_result["truth_improved"] = mse_b < mse_a
        common_improvement.append(common_result)
        print(f"transfer arms: {crop_id}", flush=True)

    legitimate: dict[str, list[dict[str, Any]]] = {
        "independent_heteroscedastic_noise": [],
        "local_resolved_detail": [],
        "spatially_varying_transfer": [],
    }
    noise_levels = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
    for trial in range(48):
        scene = crops[trial % len(crops)]
        crop_id = crop_records[trial % len(crops)]["id"]
        level = noise_levels[trial % len(noise_levels)]
        image_a, image_b = noise_pair(scene, rng, level)
        legitimate["independent_heteroscedastic_noise"].append(
            compact(
                veto.prepare_transfer_veto(image_a, Q).evaluate(image_b),
                trial=trial,
                crop=crop_id,
                noise_lsb=level,
            )
        )

        mask = smooth_random_mask(rng, scene.shape)
        local_blur = ndimage.gaussian_filter(
            scene, sigma=1.20, mode="reflect", truncate=4.0
        )
        local_a = quantize(mask * local_blur + (1.0 - mask) * scene)
        local_b = quantize((1.0 - mask) * local_blur + mask * scene)
        legitimate["local_resolved_detail"].append(
            compact(
                veto.prepare_transfer_veto(local_a, Q).evaluate(local_b),
                trial=trial,
                crop=crop_id,
            )
        )

        phase = rng.uniform(0.0, 2.0 * np.pi)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        coordinate = (
            math.cos(angle) * xx / CROP_SIZE
            + math.sin(angle) * yy / CROP_SIZE
        )
        strength = 0.65 * np.sin(2.0 * np.pi * coordinate + phase)
        detail = scene - ndimage.gaussian_filter(
            scene, sigma=1.0, mode="reflect", truncate=4.0
        )
        varying_b = quantize(scene + strength * detail)
        legitimate["spatially_varying_transfer"].append(
            compact(
                veto.prepare_transfer_veto(scene, Q).evaluate(varying_b),
                trial=trial,
                crop=crop_id,
            )
        )
        if trial % 8 == 7:
            print(f"legitimate differences: {trial + 1}/48 per family", flush=True)

    optical_improvement: list[dict[str, Any]] = []
    improvement_rng = np.random.default_rng(SEED + 1)
    for crop_record, scene in zip(crop_records, crops, strict=True):
        mean_a = ndimage.gaussian_filter(
            scene, sigma=0.80, mode="reflect", truncate=4.0
        )
        mean_b = ndimage.gaussian_filter(
            scene, sigma=0.40, mode="reflect", truncate=4.0
        )
        for noise_lsb in IMPROVEMENT_NOISE_LSB:
            image_a = quantize(
                mean_a + improvement_rng.normal(size=scene.shape) * noise_lsb * Q
            )
            image_b = quantize(
                mean_b + improvement_rng.normal(size=scene.shape) * noise_lsb * Q
            )
            record = compact(
                veto.prepare_transfer_veto(image_a, Q).evaluate(image_b),
                crop=crop_record["id"],
                noise_lsb=noise_lsb,
            )
            mse_a = float(np.mean((image_a - scene) ** 2))
            mse_b = float(np.mean((image_b - scene) ** 2))
            record["truth_mse_a"] = mse_a
            record["truth_mse_b"] = mse_b
            record["truth_mse_ratio_b_over_a"] = mse_b / mse_a
            record["truth_improved"] = mse_b < mse_a
            optical_improvement.append(record)
        print(f"optical improvement: {crop_record['id']}", flush=True)

    legitimate_flat = [
        record for family in legitimate.values() for record in family
    ]
    false_positives = sum(record["fired"] for record in legitimate_flat)
    false_positive_upper = float(
        stats.beta.ppf(
            0.95,
            false_positives + 1,
            len(legitimate_flat) - false_positives,
        )
    )

    resampling_by_kind = {
        kind: summarize(
            [record for record in resampling if record["kind"] == kind]
        )
        for kind in ("bilinear-shift-roundtrip", "box-down-bilinear-up-2x")
    }
    shift_records = [
        record
        for record in resampling
        if record["kind"] == "bilinear-shift-roundtrip"
    ]

    instrument_path = HERE / "transfer_veto.py"
    result = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "instrument commissioning on burned development renders; "
            "not a scored M1, M2, or M9 result"
        ),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "tifffile": tifffile.__version__,
            "platform": platform.platform(),
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "thread_environment": {
                name: os.environ.get(name)
                for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "inputs": [
            {
                "name": source["name"],
                "path": str(source["path"]),
                "sha256": source["sha256"],
                "bytes": source["path"].stat().st_size,
            }
            for source in SOURCES
        ],
        "crops": crop_records,
        "instrument": {
            "path": str(instrument_path.relative_to(ROOT)),
            "sha256": sha256_file(instrument_path),
            "quantization_step": Q,
            "thresholds": {
                "minimum_difference_lsb": veto.MIN_DIFFERENCE_LSB,
                "minimum_kernel_effect_lsb": veto.MIN_KERNEL_EFFECT_LSB,
                "minimum_informative_tiles": veto.MIN_INFORMATIVE_TILES,
                "informative_tile_lsb": veto.INFORMATIVE_TILE_LSB,
                "maximum_residual_over_difference": veto.MAX_RESIDUAL_OVER_DIFFERENCE,
                "maximum_residual_lsb": veto.MAX_RESIDUAL_LSB,
                "maximum_tile_q90": veto.MAX_TILE_Q90,
                "maximum_fold_disagreement": veto.MAX_FOLD_DISAGREEMENT,
            },
        },
        "identity": {
            "summary": summarize(identity),
            "trials": identity,
        },
        "movable_null_disturbance": {
            "summary": summarize(disturbance),
            "trials": disturbance,
        },
        "gaussian_blur": {
            **group_by_strength(blur, "sigma", BLUR_SIGMAS),
            "trials": blur,
        },
        "unsharp_mask": {
            **group_by_strength(sharpening, "amount", USM_AMOUNTS),
            "radius_px": 1.0,
            "trials": sharpening,
        },
        "scalar_gain": {
            **group_by_strength(scalar_gain, "gain_delta", GAIN_DELTAS),
            "trials": scalar_gain,
        },
        "blur_plus_gain": {
            "summary": summarize(blur_gain),
            "trials": blur_gain,
        },
        "resampling": {
            "bilinear_shift_roundtrip": group_by_strength(
                shift_records, "distance", SHIFT_DISTANCES
            ),
            "by_kind": resampling_by_kind,
            "trials": resampling,
        },
        "legitimate_differences": {
            "overall": {
                **summarize(legitimate_flat),
                "one_sided_clopper_pearson_95_upper": false_positive_upper,
            },
            "by_family": {
                name: summarize(records) for name, records in legitimate.items()
            },
            "trials": legitimate,
        },
        "planted_improvement": {
            "fresh_noise_optical": {
                "by_noise_lsb": {
                    f"{level:g}": summarize(
                        [
                            record
                            for record in optical_improvement
                            if math.isclose(
                                float(record["noise_lsb"]),
                                level,
                                rel_tol=0,
                                abs_tol=1e-12,
                            )
                        ]
                    )
                    for level in IMPROVEMENT_NOISE_LSB
                },
                "all_truth_improved": all(
                    record["truth_improved"] for record in optical_improvement
                ),
                "trials": optical_improvement,
            },
            "truth_improving_common_usm": {
                "summary": summarize(common_improvement),
                "all_truth_improved": all(
                    record["truth_improved"] for record in common_improvement
                ),
                "mse_ratio_b_over_a": {
                    "minimum": float(
                        min(
                            record["truth_mse_ratio_b_over_a"]
                            for record in common_improvement
                        )
                    ),
                    "median": float(
                        np.median(
                            [
                                record["truth_mse_ratio_b_over_a"]
                                for record in common_improvement
                            ]
                        )
                    ),
                    "maximum": float(
                        max(
                            record["truth_mse_ratio_b_over_a"]
                            for record in common_improvement
                        )
                    ),
                },
                "trials": common_improvement,
            },
        },
    }
    result["commissioning_checks"] = {
        "identity_does_not_fire": result["identity"]["summary"]["fires"] == 0,
        "null_probe_moved": min(
            record["difference_rms_lsb"] for record in disturbance
        )
        > max(record["difference_rms_lsb"] for record in identity),
        "local_disturbance_does_not_fire": result["movable_null_disturbance"][
            "summary"
        ]["fires"]
        == 0,
        "blur_has_reliable_threshold": result["gaussian_blur"][
            "reliable_threshold"
        ]
        is not None,
        "sharpening_has_reliable_threshold": result["unsharp_mask"][
            "reliable_threshold"
        ]
        is not None,
        "gain_has_reliable_threshold": result["scalar_gain"]["reliable_threshold"]
        is not None,
        "blur_gain_all_fire": result["blur_plus_gain"]["summary"]["fires"]
        == result["blur_plus_gain"]["summary"]["trials"],
        "shift_resampling_has_reliable_threshold": result["resampling"][
            "bilinear_shift_roundtrip"
        ]["reliable_threshold"]
        is not None,
        "twofold_resampling_all_fire": result["resampling"]["by_kind"][
            "box-down-bilinear-up-2x"
        ]["fires"]
        == result["resampling"]["by_kind"]["box-down-bilinear-up-2x"]["trials"],
        "legitimate_difference_false_positives_zero": false_positives == 0,
        "fresh_noise_arm_truth_improves": result["planted_improvement"][
            "fresh_noise_optical"
        ]["all_truth_improved"],
        "common_usm_truth_improves": result["planted_improvement"][
            "truth_improving_common_usm"
        ]["all_truth_improved"],
        "common_usm_fires": result["planted_improvement"][
            "truth_improving_common_usm"
        ]["summary"]["fires"]
        == len(common_improvement),
    }
    return result


def main() -> int:
    try:
        result = run()
        OUTPUT.write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result["commissioning_checks"], indent=2, sort_keys=True))
        print(f"wrote {OUTPUT}")
        return 0
    except Exception as error:
        failure = {
            "schema": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "commissioning_failed": True,
            "error": f"{type(error).__name__}: {error}",
        }
        OUTPUT.write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"FAIL: {failure['error']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
