"""Attribute M159's coffee-bean residual gap within Strehl.

The inherited residual rewards blur.  This analysis therefore couples it to a
commissioned, explicitly non-truth-referenced structure-collapse proxy and
refuses to call a quieter arm a win when that proxy falls.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
M159_DIR = PROJECT / "experiments" / "M159-noise-clause"
M159_RESULTS = M159_DIR / "results.json"
M159_MEASURE = M159_DIR / "measure.py"
DEFAULT_OUTPUT_ROOT = Path(r"C:\dev\strehl-out\M162-noise-regression")

FORK_PATH = Path(r"C:\dev\macro\out\coffee-bean\stack.tif")
FORK_SHA256 = "8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E"
FROZEN_V6_PATH = Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff")
FROZEN_V6_SHA256 = "F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC"
CURRENT_EXE_SHA256 = "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7"
CURRENT_COMMIT = "6af834dac08d6605aee7ea3ad75809fdf6313770"
HISTORICAL_EXE_SHA256 = (
    "CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6"
)
HISTORICAL_COMMIT = "b9b6921edc7ecec95443509b0778b4ed48404871"

PRIMARY_ARMS = (
    "v6-g2-full",
    "v6-g4p5-full",
    "v6-g2-plane",
    "v6-g4p5-plane",
    "v6-g2-full-white-floor",
    "v6-g2-full-ca-off",
)
HISTORICAL_ARM = "b9b-ship-v2-reconstruction"

TILE = 384
STEP = 192
DETAIL_SITE_COUNT = 12
BOOTSTRAP_TRIALS = 20_000
BOOTSTRAP_SEED = 162


def load_m159() -> Any:
    spec = importlib.util.spec_from_file_location("m159_measure", M159_MEASURE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {M159_MEASURE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M159 = load_m159()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise RuntimeError(f"required input is missing: {path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(
            f"SHA-256 mismatch for {path}\nexpected {expected}\nactual   {actual}"
        )


def summary(values: Iterable[float]) -> dict[str, float]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        raise RuntimeError("cannot summarize an empty sample")
    return {
        "min": float(np.min(array)),
        "p25": float(np.percentile(array, 25)),
        "median": float(np.median(array)),
        "p75": float(np.percentile(array, 75)),
        "max": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def bootstrap_median(
    values: Iterable[float], seed: int = BOOTSTRAP_SEED
) -> list[float]:
    array = np.asarray(list(values), dtype=np.float64)
    if array.size == 0:
        raise RuntimeError("cannot bootstrap an empty sample")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, array.size, (BOOTSTRAP_TRIALS, array.size))
    medians = np.median(array[indices], axis=1)
    return [float(x) for x in np.percentile(medians, [2.5, 97.5])]


def ratio_record(
    values: Iterable[float],
    numerator: str,
    denominator: str,
    seed: int,
) -> dict[str, Any]:
    ratios = [float(x) for x in values]
    record: dict[str, Any] = summary(ratios)
    record["bootstrap_95pct_interval_for_site_median"] = bootstrap_median(
        ratios, seed
    )
    record["numerator"] = numerator
    record["denominator"] = denominator
    record["site_values"] = ratios
    return record


def band_residual(image: np.ndarray) -> np.ndarray:
    image64 = np.asarray(image, dtype=np.float64)
    return uniform_filter(image64, size=5, mode="reflect") - uniform_filter(
        image64, size=13, mode="reflect"
    )


def robust_floor(residual: np.ndarray) -> tuple[float, float]:
    center = float(np.median(residual))
    floor = 1.4826 * float(np.median(np.abs(residual - center)))
    return center, floor


def noise_tail_factor() -> float:
    rng = np.random.default_rng(162_001)
    residual = band_residual(rng.normal(size=(1024, 1024)))
    center, floor = robust_floor(residual)
    tail = float(np.percentile(np.abs(residual - center), 99.5))
    if floor <= 0:
        raise RuntimeError("pure-noise proxy calibration produced a zero floor")
    return tail / floor


@dataclass(frozen=True)
class ProxyValue:
    amplitude: float
    robust_floor: float
    tail: float


def structure_proxy(image: np.ndarray, tail_factor: float) -> ProxyValue:
    residual = band_residual(image)
    center, floor = robust_floor(residual)
    tail = float(np.percentile(np.abs(residual - center), 99.5))
    amplitude = math.sqrt(max(tail * tail - (tail_factor * floor) ** 2, 0.0))
    return ProxyValue(amplitude=amplitude, robust_floor=floor, tail=tail)


def fractional_box9(image: np.ndarray) -> float:
    return M159.highpass_fractional_rms(np.asarray(image, dtype=np.float64))


def synthetic_field(size: int = TILE) -> np.ndarray:
    yy, xx = np.mgrid[:size, :size]
    latent = np.full((size, size), 0.45, dtype=np.float64)
    for x0 in (35, 77, 121, 168, 222, 278, 330):
        if x0 + 3 < size:
            latent[:, x0 : x0 + 3] += 0.10
    for y0 in (48, 111, 176, 251, 319):
        if y0 + 2 < size:
            latent[y0 : y0 + 2, 30 : size - 34] -= 0.07
    for cy, cx, radius, amplitude in (
        (80, 90, 5, 0.12),
        (140, 270, 7, -0.09),
        (270, 130, 6, 0.11),
        (310, 300, 4, -0.10),
    ):
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 < radius * radius
        latent[mask] += amplitude
    latent += 0.015 * np.sin(2.0 * np.pi * yy / 60.0)
    return latent


def commission_proxy() -> dict[str, Any]:
    tail_factor = noise_tail_factor()
    latent = synthetic_field()
    blurred = gaussian_filter(latent, sigma=0.8, mode="reflect")
    rng = np.random.default_rng(162)

    null_ratios: list[float] = []
    degradation_ratios: list[float] = []
    improvement_ratios: list[float] = []
    noise_challenge_ratios: list[float] = []
    blur_residual_ratios: list[float] = []

    for _ in range(128):
        first = latent + rng.normal(0.0, 0.004, latent.shape)
        second = latent + rng.normal(0.0, 0.004, latent.shape)
        degraded = blurred + rng.normal(0.0, 0.004, latent.shape)
        noisy = latent + rng.normal(0.0, 0.012, latent.shape)

        first_proxy = structure_proxy(first, tail_factor).amplitude
        second_proxy = structure_proxy(second, tail_factor).amplitude
        degraded_proxy = structure_proxy(degraded, tail_factor).amplitude
        noisy_proxy = structure_proxy(noisy, tail_factor).amplitude
        if min(first_proxy, second_proxy, degraded_proxy, noisy_proxy) <= 0:
            raise RuntimeError("commissioning proxy collapsed to zero")

        null_ratios.append(second_proxy / first_proxy)
        degradation_ratios.append(degraded_proxy / first_proxy)
        improvement_ratios.append(first_proxy / degraded_proxy)
        noise_challenge_ratios.append(noisy_proxy / first_proxy)
        blur_residual_ratios.append(
            fractional_box9(degraded) / fractional_box9(first)
        )

    null_summary = summary(null_ratios)
    degradation_summary = summary(degradation_ratios)
    improvement_summary = summary(improvement_ratios)
    noise_summary = summary(noise_challenge_ratios)
    trap_summary = summary(blur_residual_ratios)

    checks = {
        "movable_null": (
            null_summary["min"] < 1.0
            and null_summary["max"] > 1.0
            and null_summary["max"] - null_summary["min"] >= 0.01
            and abs(null_summary["median"] - 1.0) <= 0.01
        ),
        "planted_degradation": (
            degradation_summary["max"] < 1.0
            and degradation_summary["median"] <= 0.90
        ),
        "planted_improvement": (
            improvement_summary["min"] > 1.0
            and improvement_summary["median"] >= 1.10
        ),
        "added_noise_not_rewarded": noise_summary["median"] <= 1.05,
        "blur_trap": (
            trap_summary["median"] < 0.90
            and degradation_summary["median"] < 0.90
        ),
    }
    record = {
        "schema": 1,
        "seed": 162,
        "trials": 128,
        "noise_tail_factor": tail_factor,
        "proxy": (
            "sqrt(max(p99.5(|box5-box13 - median|)^2 - "
            "(K * 1.4826*MAD)^2, 0))"
        ),
        "movable_null_second_over_first": {
            **null_summary,
            "trials_below_1": sum(x < 1.0 for x in null_ratios),
            "trials_above_1": sum(x > 1.0 for x in null_ratios),
        },
        "planted_degradation_blur_over_original": degradation_summary,
        "planted_improvement_original_over_blur": improvement_summary,
        "added_noise_sigma3_over_original": noise_summary,
        "blurred_over_original_box9_residual": trap_summary,
        "checks": checks,
        "passed": all(checks.values()),
    }
    return record


class StrehlReader:
    def __init__(self, path: Path):
        self.path = path
        self.image = tifffile.memmap(path, mode="r")
        if self.image.ndim != 3 or self.image.shape[2] != 3:
            raise RuntimeError(f"unexpected TIFF shape for {path}: {self.image.shape}")
        if self.image.dtype != np.uint16:
            raise RuntimeError(f"expected uint16 Strehl TIFF at {path}, got {self.image.dtype}")
        self.tone = M159.parse_strehl_tone(path)

    @property
    def shape(self) -> tuple[int, ...]:
        return tuple(int(x) for x in self.image.shape)

    def raw_box(self, y: int, x: int, size: int) -> np.ndarray:
        return np.asarray(self.image[y : y + size, x : x + size, :]).copy()

    def linear_green_box(self, y: int, x: int, size: int) -> np.ndarray:
        raw = self.raw_box(y, x, size)
        rgb = raw.astype(np.float64) / 65535.0
        return M159.inverse_strehl_render(rgb, self.tone)[:, :, 1]

    def close(self) -> None:
        del self.image


def boxes_overlap(
    first: tuple[int, int, int], second: tuple[int, int, int]
) -> bool:
    y1, x1, size1 = first
    y2, x2, size2 = second
    return not (
        y1 + size1 <= y2
        or y2 + size2 <= y1
        or x1 + size1 <= x2
        or x2 + size2 <= x1
    )


def select_detail_sites(
    flat_sites: list[dict[str, Any]], tail_factor: float
) -> dict[str, Any]:
    fork = tifffile.memmap(FORK_PATH, mode="r")
    if fork.dtype != np.float32:
        raise RuntimeError(f"expected float32 fork TIFF, got {fork.dtype}")
    height, width, _ = fork.shape
    flat_boxes = [
        (
            int(site["boxes_y_x_size"]["fork"][0]),
            int(site["boxes_y_x_size"]["fork"][1]),
            int(site["boxes_y_x_size"]["fork"][2]),
        )
        for site in flat_sites
    ]
    counts = {
        "candidate_grid": 0,
        "excluded_reference_headroom": 0,
        "excluded_reference_mean": 0,
        "excluded_flat_overlap": 0,
        "excluded_zero_proxy": 0,
        "eligible_for_ranking": 0,
    }
    ranked: list[dict[str, Any]] = []
    for y in range(200, height - 200 - TILE, STEP):
        for x in range(200, width - 200 - TILE, STEP):
            counts["candidate_grid"] += 1
            box = np.asarray(fork[y : y + TILE, x : x + TILE, :])
            if bool(np.any(box >= 0.98)):
                counts["excluded_reference_headroom"] += 1
                continue
            green = np.asarray(box[:, :, 1], dtype=np.float64)
            mean = float(np.mean(green))
            if not 0.08 < mean < 0.75:
                counts["excluded_reference_mean"] += 1
                continue
            coordinate = (y, x, TILE)
            if any(boxes_overlap(coordinate, flat) for flat in flat_boxes):
                counts["excluded_flat_overlap"] += 1
                continue
            proxy = structure_proxy(green, tail_factor)
            if proxy.amplitude <= 0:
                counts["excluded_zero_proxy"] += 1
                continue
            counts["eligible_for_ranking"] += 1
            ranked.append(
                {
                    "reference_y": y,
                    "reference_x": x,
                    "reference_size": TILE,
                    "reference_mean": mean,
                    "reference_proxy": proxy.amplitude,
                }
            )
    del fork

    ranked.sort(key=lambda item: item["reference_proxy"], reverse=True)
    selected: list[dict[str, Any]] = []
    for candidate in ranked:
        coordinate = (
            candidate["reference_y"],
            candidate["reference_x"],
            candidate["reference_size"],
        )
        if any(
            boxes_overlap(
                coordinate,
                (
                    item["reference_y"],
                    item["reference_x"],
                    item["reference_size"],
                ),
            )
            for item in selected
        ):
            continue
        selected.append(candidate)
        if len(selected) == DETAIL_SITE_COUNT:
            break
    if len(selected) != DETAIL_SITE_COUNT:
        raise RuntimeError(
            f"only {len(selected)} non-overlapping detail sites survived; "
            f"{DETAIL_SITE_COUNT} were preregistered"
        )
    for rank, site in enumerate(selected, start=1):
        site["rank"] = rank
    return {
        "method": (
            "fork-only 384px grid; reject fork RGB >=0.98, green mean outside "
            "(0.08,0.75), overlap with M159 flats, and zero proxy; greedily "
            "freeze the top twelve non-overlapping proxy boxes"
        ),
        "counts": counts,
        "selected": selected,
    }


def load_arm(output_root: Path, arm: str) -> tuple[Path, dict[str, Any]]:
    manifest_path = output_root / "manifests" / f"{arm}.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"missing render manifest for {arm}: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("arm") != arm or manifest.get("exit_code") != 0:
        raise RuntimeError(f"invalid render manifest for {arm}")
    expected_exe_hash = (
        HISTORICAL_EXE_SHA256 if arm == HISTORICAL_ARM else CURRENT_EXE_SHA256
    )
    expected_commit = (
        HISTORICAL_COMMIT if arm == HISTORICAL_ARM else CURRENT_COMMIT
    )
    if manifest.get("executable_sha256") != expected_exe_hash:
        raise RuntimeError(f"unexpected executable hash in manifest for {arm}")
    if manifest.get("commit") != expected_commit:
        raise RuntimeError(f"unexpected source commit in manifest for {arm}")

    source_manifest = output_root / "source-manifest.json"
    if not source_manifest.is_file():
        raise RuntimeError(f"missing source manifest: {source_manifest}")
    if sha256(source_manifest) != manifest.get("source_manifest_sha256"):
        raise RuntimeError(f"source manifest changed after rendering {arm}")

    executable = Path(manifest["executable"])
    require_hash(executable, expected_exe_hash)
    warpmap = Path(manifest["warpmap"])
    require_hash(warpmap, str(manifest["warpmap_sha256"]))

    path = Path(manifest["output"])
    if not path.is_file():
        raise RuntimeError(f"render output for {arm} is missing: {path}")
    actual = sha256(path)
    if actual != manifest.get("output_sha256"):
        raise RuntimeError(
            f"render output hash changed for {arm}\n"
            f"manifest {manifest.get('output_sha256')}\nactual   {actual}"
        )
    return path, manifest


def pixel_comparison(first_path: Path, second_path: Path) -> dict[str, Any]:
    first = tifffile.memmap(first_path, mode="r")
    second = tifffile.memmap(second_path, mode="r")
    if first.shape != second.shape or first.dtype != second.dtype:
        record = {
            "pixel_identical": False,
            "first_shape": list(first.shape),
            "second_shape": list(second.shape),
            "first_dtype": str(first.dtype),
            "second_dtype": str(second.dtype),
            "reason": "shape or dtype mismatch",
        }
        del first, second
        return record

    first_digest = hashlib.sha256()
    second_digest = hashlib.sha256()
    differing = 0
    max_abs_delta = 0
    for y in range(0, first.shape[0], 32):
        a = np.ascontiguousarray(first[y : y + 32])
        b = np.ascontiguousarray(second[y : y + 32])
        first_digest.update(a.tobytes())
        second_digest.update(b.tobytes())
        difference = a != b
        differing += int(np.count_nonzero(difference))
        if np.any(difference):
            delta = np.abs(a.astype(np.int32) - b.astype(np.int32))
            max_abs_delta = max(max_abs_delta, int(np.max(delta)))
    total = int(np.prod(first.shape))
    record = {
        "pixel_identical": differing == 0,
        "first_pixel_sha256": first_digest.hexdigest().upper(),
        "second_pixel_sha256": second_digest.hexdigest().upper(),
        "differing_samples": differing,
        "total_samples": total,
        "differing_fraction": differing / total,
        "max_abs_delta_dn": max_abs_delta,
        "shape": list(first.shape),
        "dtype": str(first.dtype),
    }
    del first, second
    return record


def mapped_box(
    detail_site: dict[str, Any],
    current_box_size: int,
    geometry: Any | None,
) -> tuple[int, int, int]:
    if geometry is None:
        center_y = detail_site["reference_y"] + detail_site["reference_size"] / 2
        center_x = detail_site["reference_x"] + detail_site["reference_size"] / 2
        m159_geometry = next(
            item
            for item in json.loads(M159_RESULTS.read_text(encoding="utf-8"))[
                "geometry"
            ].values()
            if item["reference"] == "focus-stack fork"
            and item["target"] == "strehl DELIVER-V6"
        )
        scale = float(m159_geometry["scale"])
        angle = math.radians(float(m159_geometry["rotation_deg"]))
        a = scale * math.cos(angle)
        b = scale * math.sin(angle)
        center_ref_y = 4672 / 2
        center_ref_x = 7008 / 2
        xx = center_x - center_ref_x
        yy = center_y - center_ref_y
        target_x = (
            a * xx
            - b * yy
            + center_ref_x
            + float(m159_geometry["translation_x_px"])
        )
        target_y = (
            b * xx
            + a * yy
            + center_ref_y
            + float(m159_geometry["translation_y_px"])
        )
        size = current_box_size
        return (
            int(round(target_y - size / 2)),
            int(round(target_x - size / 2)),
            size,
        )
    return geometry.box(
        int(detail_site["reference_y"]),
        int(detail_site["reference_x"]),
        int(detail_site["reference_size"]),
    )


def score_arm(
    arm: str,
    path: Path,
    file_hash: str,
    flat_sites: list[dict[str, Any]],
    detail_sites: list[dict[str, Any]],
    tail_factor: float,
    historical_geometry: Any | None = None,
) -> dict[str, Any]:
    reader = StrehlReader(path)
    expected_current_shape = (4688, 7032, 3)
    if historical_geometry is None and reader.shape != expected_current_shape:
        reader.close()
        raise RuntimeError(
            f"{arm} shape {reader.shape} does not match current-arm shape "
            f"{expected_current_shape}"
        )

    flat_records: list[dict[str, Any]] = []
    for site in flat_sites:
        if historical_geometry is None:
            y, x, size = (int(v) for v in site["boxes_y_x_size"]["strehl"])
        else:
            y, x, size = historical_geometry.box(
                int(site["reference_y"]), int(site["reference_x"]), TILE
            )
        green = reader.linear_green_box(y, x, size)
        residual = fractional_box9(green)
        fork_residual = float(site["fractional_rms"]["fork"])
        flat_records.append(
            {
                "rank": int(site["rank"]),
                "reference_y": int(site["reference_y"]),
                "reference_x": int(site["reference_x"]),
                "box_y_x_size": [y, x, size],
                "fractional_box9_residual": residual,
                "arm_over_fork": residual / fork_residual,
                "linear_green_mean": float(np.mean(green)),
            }
        )

    detail_records: list[dict[str, Any]] = []
    current_size = int(flat_sites[0]["boxes_y_x_size"]["strehl"][2])
    for site in detail_sites:
        y, x, size = mapped_box(site, current_size, historical_geometry)
        if y < 0 or x < 0 or y + size > reader.shape[0] or x + size > reader.shape[1]:
            reader.close()
            raise RuntimeError(f"mapped detail site is out of bounds for {arm}")
        raw = reader.raw_box(y, x, size)
        green = reader.linear_green_box(y, x, size)
        proxy = structure_proxy(green, tail_factor)
        span = float(np.percentile(green, 99.5) - np.percentile(green, 0.5))
        detail_records.append(
            {
                "rank": int(site["rank"]),
                "reference_y": int(site["reference_y"]),
                "reference_x": int(site["reference_x"]),
                "box_y_x_size": [y, x, size],
                "structure_proxy": proxy.amplitude,
                "robust_noise_floor": proxy.robust_floor,
                "upper_tail": proxy.tail,
                "linear_green_mean": float(np.mean(green)),
                "linear_green_p99p5_minus_p0p5": span,
                "raw_clip_fraction": float(np.mean(raw == 65535)),
            }
        )
    reader.close()
    return {
        "path": str(path),
        "sha256": file_hash,
        "flat_sites": flat_records,
        "flat_arm_over_fork": summary(
            item["arm_over_fork"] for item in flat_records
        ),
        "detail_sites": detail_records,
        "detail_structure_proxy": summary(
            item["structure_proxy"] for item in detail_records
        ),
    }


def paired_values(
    scored: dict[str, Any],
    numerator: str,
    denominator: str,
    section: str,
    field: str,
) -> list[float]:
    left = scored[numerator][section]
    right = scored[denominator][section]
    if len(left) != len(right):
        raise RuntimeError(f"site count mismatch: {numerator} versus {denominator}")
    return [
        float(a[field]) / float(b[field])
        for a, b in zip(left, right, strict=True)
    ]


def clipping_guard(
    scored: dict[str, Any], candidate: str, baseline: str
) -> dict[str, Any]:
    candidate_sites = scored[candidate]["detail_sites"]
    baseline_sites = scored[baseline]["detail_sites"]
    deltas = [
        float(a["raw_clip_fraction"]) - float(b["raw_clip_fraction"])
        for a, b in zip(candidate_sites, baseline_sites, strict=True)
    ]
    maximum = max(deltas)
    return {
        "max_added_clip_fraction": maximum,
        "sites_with_added_clipping": sum(delta > 0 for delta in deltas),
        "passed": maximum <= 0.0,
    }


def evaluate_reversion(
    scored: dict[str, Any], candidate: str, baseline: str, seed: int
) -> dict[str, Any]:
    residual = ratio_record(
        paired_values(
            scored,
            baseline,
            candidate,
            "flat_sites",
            "fractional_box9_residual",
        ),
        baseline,
        candidate,
        seed,
    )
    detail = ratio_record(
        paired_values(
            scored,
            candidate,
            baseline,
            "detail_sites",
            "structure_proxy",
        ),
        candidate,
        baseline,
        seed + 1,
    )
    mean_ratio = ratio_record(
        paired_values(
            scored,
            candidate,
            baseline,
            "detail_sites",
            "linear_green_mean",
        ),
        candidate,
        baseline,
        seed + 2,
    )
    span_ratio = ratio_record(
        paired_values(
            scored,
            candidate,
            baseline,
            "detail_sites",
            "linear_green_p99p5_minus_p0p5",
        ),
        candidate,
        baseline,
        seed + 3,
    )
    clipping = clipping_guard(scored, candidate, baseline)
    residual_material = (
        residual["median"] >= 1.10
        and residual["bootstrap_95pct_interval_for_site_median"][0] > 1.0
    )
    detail_holds = (
        detail["median"] >= 0.98
        and detail["bootstrap_95pct_interval_for_site_median"][0] >= 0.95
    )
    gain_holds = 0.99 <= mean_ratio["median"] <= 1.01
    admissible = residual_material and detail_holds and gain_holds and clipping["passed"]
    return {
        "residual_quieting_baseline_over_candidate": residual,
        "detail_candidate_over_baseline": detail,
        "linear_mean_candidate_over_baseline": mean_ratio,
        "linear_span_candidate_over_baseline": span_ratio,
        "clipping_guard": clipping,
        "checks": {
            "material_residual_improvement": residual_material,
            "detail_proxy_holds": detail_holds,
            "linear_mean_holds": gain_holds,
            "no_added_clipping": clipping["passed"],
        },
        "admissible_regression_fix": admissible,
    }


def evaluate_gather_trade(
    scored: dict[str, Any], full: str, plane: str, seed: int
) -> dict[str, Any]:
    residual = ratio_record(
        paired_values(
            scored, full, plane, "flat_sites", "fractional_box9_residual"
        ),
        full,
        plane,
        seed,
    )
    detail = ratio_record(
        paired_values(
            scored, full, plane, "detail_sites", "structure_proxy"
        ),
        full,
        plane,
        seed + 1,
    )
    mean_ratio = ratio_record(
        paired_values(
            scored,
            full,
            plane,
            "detail_sites",
            "linear_green_mean",
        ),
        full,
        plane,
        seed + 2,
    )
    clipping = clipping_guard(scored, full, plane)
    residual_cost = (
        residual["median"] >= 1.10
        and residual["bootstrap_95pct_interval_for_site_median"][0] > 1.0
    )
    detail_gain = (
        detail["median"] >= 1.10
        and detail["bootstrap_95pct_interval_for_site_median"][0] > 1.0
    )
    gain_holds = 0.99 <= mean_ratio["median"] <= 1.01
    return {
        "residual_full_over_plane": residual,
        "detail_full_over_plane": detail,
        "linear_mean_full_over_plane": mean_ratio,
        "clipping_guard": clipping,
        "checks": {
            "material_residual_cost": residual_cost,
            "material_detail_proxy_gain": detail_gain,
            "linear_mean_holds": gain_holds,
            "no_added_clipping": clipping["passed"],
        },
        "admissible_trade": (
            residual_cost and detail_gain and gain_holds and clipping["passed"]
        ),
    }


def evaluate_gate_trade(
    scored: dict[str, Any], gate2: str, gate4p5: str, seed: int
) -> dict[str, Any]:
    residual = ratio_record(
        paired_values(
            scored,
            gate2,
            gate4p5,
            "flat_sites",
            "fractional_box9_residual",
        ),
        gate2,
        gate4p5,
        seed,
    )
    detail = ratio_record(
        paired_values(
            scored,
            gate2,
            gate4p5,
            "detail_sites",
            "structure_proxy",
        ),
        gate2,
        gate4p5,
        seed + 1,
    )
    mean_ratio = ratio_record(
        paired_values(
            scored,
            gate2,
            gate4p5,
            "detail_sites",
            "linear_green_mean",
        ),
        gate2,
        gate4p5,
        seed + 2,
    )
    clipping = clipping_guard(scored, gate2, gate4p5)
    residual_cost = (
        residual["median"] >= 1.10
        and residual["bootstrap_95pct_interval_for_site_median"][0] > 1.0
    )
    detail_gain = (
        detail["median"] >= 1.10
        and detail["bootstrap_95pct_interval_for_site_median"][0] > 1.0
    )
    gain_holds = 0.99 <= mean_ratio["median"] <= 1.01
    return {
        "residual_gate2_over_gate4p5": residual,
        "detail_gate2_over_gate4p5": detail,
        "linear_mean_gate2_over_gate4p5": mean_ratio,
        "clipping_guard": clipping,
        "checks": {
            "material_residual_cost": residual_cost,
            "material_detail_proxy_gain": detail_gain,
            "linear_mean_holds": gain_holds,
            "no_added_clipping": clipping["passed"],
        },
        "admissible_trade": (
            residual_cost and detail_gain and gain_holds and clipping["passed"]
        ),
        "scope": (
            "The source record conflicts on whether gate 2.0 was intended to "
            "remain the product default. This proxy cannot exclude dense "
            "low-contrast texture loss, so any verdict is scoped to its stated "
            "blindness."
        ),
    }


def factorial_interaction(
    scored: dict[str, Any], section: str, field: str, seed: int
) -> dict[str, Any]:
    g2_full = scored["v6-g2-full"][section]
    g45_full = scored["v6-g4p5-full"][section]
    g2_plane = scored["v6-g2-plane"][section]
    g45_plane = scored["v6-g4p5-plane"][section]
    values = []
    for a, b, c, d in zip(
        g45_full, g2_full, g45_plane, g2_plane, strict=True
    ):
        values.append(
            math.log(float(a[field]) / float(b[field]))
            - math.log(float(c[field]) / float(d[field]))
        )
    record: dict[str, Any] = summary(values)
    record["bootstrap_95pct_interval_for_site_median"] = bootstrap_median(
        values, seed
    )
    record["definition"] = (
        "log(gate4.5/gate2 at full gather) - "
        "log(gate4.5/gate2 at plane gather)"
    )
    record["site_values"] = values
    return record


def gap_closure(scored: dict[str, Any], candidate: str) -> dict[str, Any]:
    baseline_sites = scored["v6-g2-full"]["flat_sites"]
    candidate_sites = scored[candidate]["flat_sites"]
    values = []
    for baseline, arm in zip(baseline_sites, candidate_sites, strict=True):
        baseline_gap = math.log(float(baseline["arm_over_fork"]))
        if abs(baseline_gap) < 1e-12:
            continue
        values.append(
            math.log(
                float(baseline["fractional_box9_residual"])
                / float(arm["fractional_box9_residual"])
            )
            / baseline_gap
        )
    return {
        **summary(values),
        "bootstrap_95pct_interval_for_site_median": bootstrap_median(
            values, BOOTSTRAP_SEED + 90
        ),
        "definition": (
            "log(baseline residual / candidate residual) divided by "
            "log(baseline residual / fork residual), per frozen site"
        ),
    }


def make_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# M162 analysis result",
        "",
        f"**Automatic verdict: {result['verdict']}**",
        "",
        f"Baseline pixels reproduce DELIVER-V6: "
        f"**{result['baseline_reproduction']['pixel_identical']}**.",
        "",
        "## Current arms",
        "",
        "| arm | median arm/fork residual |",
        "|---|---:|",
    ]
    for arm in PRIMARY_ARMS:
        median = result["arms"][arm]["flat_arm_over_fork"]["median"]
        lines.append(f"| `{arm}` | `{median:.6f}x` |")
    lines.extend(
        [
            "",
            "## Regression tests",
            "",
            "| candidate | residual quieting | detail proxy | admissible |",
            "|---|---:|---:|---|",
        ]
    )
    for candidate, record in result["regression_tests"].items():
        residual = record["residual_quieting_baseline_over_candidate"]["median"]
        detail = record["detail_candidate_over_baseline"]["median"]
        lines.append(
            f"| `{candidate}` | `{residual:.6f}x` | `{detail:.6f}x` | "
            f"**{record['admissible_regression_fix']}** |"
        )
    lines.extend(
        [
            "",
            "## Gate attribution",
            "",
            "The intent record for gate `2.0` is conflicted. Gate `4.5` is an "
            "eligible regression reversion under the same residual, proxy, "
            "gain, and clipping guards as the other candidates.",
            "",
            "| residual g2/g4.5 | detail g2/g4.5 | admissible trade |",
            "|---:|---:|---|",
        ]
    )
    gate_trade = result["gate_trade_test"]
    gate_residual = gate_trade["residual_gate2_over_gate4p5"]["median"]
    gate_detail = gate_trade["detail_gate2_over_gate4p5"]["median"]
    lines.append(
        f"| `{gate_residual:.6f}x` | `{gate_detail:.6f}x` | "
        f"**{gate_trade['admissible_trade']}** |"
    )
    lines.extend(
        [
            "",
            "## Gather trade tests",
            "",
            "| gate | residual full/plane | detail full/plane | admissible trade |",
            "|---|---:|---:|---|",
        ]
    )
    for gate, record in result["gather_trade_tests"].items():
        residual = record["residual_full_over_plane"]["median"]
        detail = record["detail_full_over_plane"]["median"]
        lines.append(
            f"| {gate} | `{residual:.6f}x` | `{detail:.6f}x` | "
            f"**{record['admissible_trade']}** |"
        )
    lines.extend(
        [
            "",
            "The structure statistic is a collapse proxy, not a truth-referenced "
            "detail measurement. See `PREREGISTRATION.md` for its blindness and "
            "the decision thresholds.",
            "",
        ]
    )
    return "\n".join(lines)


def run_analysis(
    output_root: Path,
    include_historical: bool,
    commissioning: dict[str, Any],
) -> dict[str, Any]:
    require_hash(FORK_PATH, FORK_SHA256)
    require_hash(FROZEN_V6_PATH, FROZEN_V6_SHA256)
    m159_result = json.loads(M159_RESULTS.read_text(encoding="utf-8"))
    coffee = next(
        subject
        for subject in m159_result["subjects"]
        if subject.get("subject") == "coffee-bean"
    )
    flat_sites = coffee["sites"]
    tail_factor = float(commissioning["noise_tail_factor"])
    detail_selection = select_detail_sites(flat_sites, tail_factor)

    paths: dict[str, Path] = {}
    manifests: dict[str, dict[str, Any]] = {}
    for arm in PRIMARY_ARMS:
        paths[arm], manifests[arm] = load_arm(output_root, arm)

    baseline_reproduction = pixel_comparison(
        paths["v6-g2-full"], FROZEN_V6_PATH
    )
    current_warpmaps = {
        str(manifest["warpmap_sha256"]) for manifest in manifests.values()
    }
    if len(current_warpmaps) != 1:
        raise RuntimeError(
            f"current arms do not share one warpmap: {sorted(current_warpmaps)}"
        )

    scored: dict[str, Any] = {}
    for arm in PRIMARY_ARMS:
        scored[arm] = score_arm(
            arm,
            paths[arm],
            str(manifests[arm]["output_sha256"]),
            flat_sites,
            detail_selection["selected"],
            tail_factor,
        )

    expected_site_ratios = [
        float(site["strehl_over_comparator"]["fork"]) for site in flat_sites
    ]
    measured_site_ratios = [
        float(site["arm_over_fork"])
        for site in scored["v6-g2-full"]["flat_sites"]
    ]
    site_ratio_deltas = [
        abs(measured - expected)
        for measured, expected in zip(
            measured_site_ratios, expected_site_ratios, strict=True
        )
    ]
    expected_median = float(
        coffee["raw_best_comparator_distribution"]["median"]
    )
    measured_median = float(
        scored["v6-g2-full"]["flat_arm_over_fork"]["median"]
    )
    m159_statistic_reproduction = {
        "expected_median": expected_median,
        "measured_median": measured_median,
        "absolute_median_delta": abs(measured_median - expected_median),
        "max_absolute_site_ratio_delta": max(site_ratio_deltas),
        "matched": (
            abs(measured_median - expected_median) <= 1e-12
            and max(site_ratio_deltas) <= 1e-12
        ),
    }

    historical_geometry = None
    if include_historical:
        historical_path, historical_manifest = load_arm(
            output_root, HISTORICAL_ARM
        )
        manifests[HISTORICAL_ARM] = historical_manifest
        fork_arm = M159.Arm("focus-stack fork", FORK_PATH, "linear-float")
        historical_arm = M159.Arm(
            "b9b SHIP-V2 reconstruction",
            historical_path,
            "strehl-srgb-u16",
        )
        historical_geometry = M159.fit_geometry(fork_arm, historical_arm)
        scored[HISTORICAL_ARM] = score_arm(
            HISTORICAL_ARM,
            historical_path,
            str(historical_manifest["output_sha256"]),
            flat_sites,
            detail_selection["selected"],
            tail_factor,
            historical_geometry,
        )

    gate_counterfactual = evaluate_reversion(
        scored, "v6-g4p5-full", "v6-g2-full", BOOTSTRAP_SEED + 10
    )
    gate_counterfactual["passes_reversion_checks"] = gate_counterfactual[
        "admissible_regression_fix"
    ]
    gate_counterfactual["eligible_for_regression_verdict"] = True
    gate_counterfactual["intent_status"] = (
        "UNRESOLVED CONFLICT: early ORCH notes provisionally retained 2.0; "
        "later README measurements call 2.0 wrong and recommend 4.5."
    )
    regression_tests = {
        "v6-g4p5-full": gate_counterfactual,
        "v6-g2-full-white-floor": evaluate_reversion(
            scored,
            "v6-g2-full-white-floor",
            "v6-g2-full",
            BOOTSTRAP_SEED + 20,
        ),
        "v6-g2-full-ca-off": evaluate_reversion(
            scored, "v6-g2-full-ca-off", "v6-g2-full", BOOTSTRAP_SEED + 30
        ),
    }
    gate_plane_test = evaluate_reversion(
        scored, "v6-g4p5-plane", "v6-g2-plane", BOOTSTRAP_SEED + 40
    )
    gate_plane_test["passes_reversion_checks"] = gate_plane_test[
        "admissible_regression_fix"
    ]
    gate_plane_test["eligible_for_regression_verdict"] = False
    gate_plane_test["admissible_regression_fix"] = False
    gate_plane_test["ineligible_reason"] = (
        "This is interaction corroboration on the non-delivered plane-gather "
        "configuration, not a direct reversion of DELIVER-V6."
    )
    gate_trade_test = evaluate_gate_trade(
        scored, "v6-g2-full", "v6-g4p5-full", BOOTSTRAP_SEED + 45
    )
    gather_trade_tests = {
        "gate-2.0": evaluate_gather_trade(
            scored, "v6-g2-full", "v6-g2-plane", BOOTSTRAP_SEED + 50
        ),
        "gate-4.5": evaluate_gather_trade(
            scored, "v6-g4p5-full", "v6-g4p5-plane", BOOTSTRAP_SEED + 60
        ),
    }
    interactions = {
        "flat_residual": factorial_interaction(
            scored,
            "flat_sites",
            "fractional_box9_residual",
            BOOTSTRAP_SEED + 70,
        ),
        "detail_proxy": factorial_interaction(
            scored,
            "detail_sites",
            "structure_proxy",
            BOOTSTRAP_SEED + 80,
        ),
    }

    admissible_regressions = [
        arm
        for arm, record in regression_tests.items()
        if record["admissible_regression_fix"]
    ]
    admissible_trades = [
        gate
        for gate, record in gather_trade_tests.items()
        if record["admissible_trade"]
    ]
    if gate_trade_test["admissible_trade"]:
        admissible_trades.append("gate-2.0")
    if not baseline_reproduction["pixel_identical"]:
        verdict = "UNRESOLVED"
        verdict_reason = "the M162 baseline did not reproduce DELIVER-V6 pixels"
    elif not m159_statistic_reproduction["matched"]:
        verdict = "UNRESOLVED"
        verdict_reason = "the inherited M159 statistic did not reproduce M159"
    elif admissible_regressions:
        verdict = "REGRESSION"
        verdict_reason = (
            "at least one current-binary reversion materially lowered residual "
            "while the commissioned structure proxy and guards held"
        )
    elif admissible_trades:
        verdict = "TRADE"
        verdict_reason = (
            "no admissible regression reversion was found and at least one "
            "attributed choice paid residual for a material structure-proxy gain"
        )
    else:
        verdict = "UNRESOLVED"
        verdict_reason = "neither preregistered classification rule passed"

    result: dict[str, Any] = {
        "schema": 1,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "commissioning": commissioning,
        "fixed_inputs": {
            "fork": {
                "path": str(FORK_PATH),
                "sha256": FORK_SHA256,
            },
            "frozen_deliver_v6": {
                "path": str(FROZEN_V6_PATH),
                "sha256": FROZEN_V6_SHA256,
            },
            "m159_results": {
                "path": str(M159_RESULTS),
                "sha256": sha256(M159_RESULTS),
            },
        },
        "baseline_reproduction": baseline_reproduction,
        "m159_statistic_reproduction": m159_statistic_reproduction,
        "current_warpmap_sha256": next(iter(current_warpmaps)),
        "detail_selection": detail_selection,
        "arms": scored,
        "gate_4p5_counterfactual": gate_counterfactual,
        "gate_trade_test": gate_trade_test,
        "regression_tests": regression_tests,
        "gate_4p5_plane_corroboration": gate_plane_test,
        "gather_trade_tests": gather_trade_tests,
        "factorial_interactions": interactions,
        "log_gap_closure": {
            arm: gap_closure(scored, arm)
            for arm in (
                "v6-g4p5-full",
                "v6-g2-plane",
                "v6-g4p5-plane",
                "v6-g2-full-white-floor",
                "v6-g2-full-ca-off",
            )
        },
        "render_manifests": manifests,
    }
    if historical_geometry is not None:
        result["historical_geometry"] = historical_geometry.as_dict()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="render root written by render.ps1",
    )
    parser.add_argument(
        "--commission-only",
        action="store_true",
        help="run and persist synthetic controls without reading any real image",
    )
    parser.add_argument(
        "--include-historical",
        action="store_true",
        help="also require and score the conditional b9b SHIP-V2 reconstruction",
    )
    args = parser.parse_args()

    commissioning = commission_proxy()
    (HERE / "commissioning.json").write_text(
        json.dumps(commissioning, indent=2) + "\n", encoding="utf-8"
    )
    if not commissioning["passed"]:
        print(json.dumps(commissioning, indent=2))
        return 2
    if args.commission_only:
        print(json.dumps(commissioning, indent=2))
        return 0

    result = run_analysis(args.output_root, args.include_historical, commissioning)
    (HERE / "results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (HERE / "results.md").write_text(make_markdown(result), encoding="utf-8")
    print(make_markdown(result))
    return 0 if result["verdict"] in {"REGRESSION", "TRADE"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
