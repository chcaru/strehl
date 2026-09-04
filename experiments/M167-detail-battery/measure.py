"""Black-box candidate measurements for the M167 detail battery.

This process owns candidate adapters and imports the independent fixture
generator.  It never imports the checker or its predicates.  Results are
serialized to stdout for adjudication in another process.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path
from typing import Callable

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter, uniform_filter

from fixtures import (
    BASE_SIGMA,
    BLUR_SIGMAS,
    DEGRADED_SIGMA,
    IMPROVED_SIGMA,
    Observation,
    build_fixtures,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

D8_PATH = ROOT / "experiments/M-PHASE0-SPLIT2/frc.py"
D8_SHA256 = "C0408661BDDF15554BB8EC0F3D10C972D88CB632AF226C2E6944466855898288"
BAND_PATH = ROOT / "experiments/M95-coverage/src/m95cov.py"
BAND_SHA256 = "4AAE9064AD89C7846492C00EA1FC60A1965CEC3A6AB7550BF84634C9E021EC1D"
BAND_EVIDENCE_PATH = (
    ROOT / "experiments/M135-detail-instrument/AMENDMENT-4.md"
)
BAND_EVIDENCE_SHA256 = (
    "79E257EA22103C2D0C17E84A518249BA69F61457301190BC07EBFB43CAEDB5EB"
)
BAND_REPORT_PATH = ROOT / "docs/research/M135-detail-instrument.md"
BAND_REPORT_SHA256 = (
    "9BA4CA24C9DAB0656A2DD6F8CC3F9F3AF6225D291BE21180F2D733627D8689AA"
)
M2_PATH = ROOT / "experiments/M159-noise-clause/measure.py"
M2_SHA256 = "6109FAFFF52F3C287DE2DEACC57B76843215D72CA4AD155E3BBB92BC4F057DA9"
M2_RESULT_PATH = ROOT / "experiments/M159-noise-clause/results.json"
M2_RESULT_SHA256 = (
    "5EBA810719313ECD85116E268965FE699C43E0EA32BC4D43B6354FDE8DD30389"
)

BAND_DETAIL_GAP = 0.3403664343410666
BAND_FLAT_GAP = 0.3488548829813006
BAND_FLAT_DETAIL_RATIO = 1.0249391472947889
BAND_STRUCTURE_SHARE = 0.13314850036584688
M2_FROZEN_BLUR_RATIO = 0.5712148772282098


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_hash(path: Path, expected: str) -> str:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(
            f"source drift for {path.relative_to(ROOT)}: "
            f"expected {expected}, got {actual}"
        )
    return actual


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def numeric_record(value: float) -> dict[str, object]:
    number = float(value)
    if not np.isfinite(number):
        return {
            "status": "INVALID",
            "reason": "candidate returned a non-finite scalar",
        }
    return {"status": "VALUE", "score": number}


def error_record(error: Exception) -> dict[str, object]:
    return {
        "status": "ERROR",
        "code": type(error).__name__.upper(),
        "reason": str(error),
    }


def safe_measure(
    function: Callable[[Observation], dict[str, object]],
    observation: Observation,
) -> dict[str, object]:
    try:
        return function(observation)
    except Exception as error:
        return error_record(error)


def standard_arms(
    fixtures: dict[str, object],
    measure_one: Callable[[Observation], dict[str, object]],
) -> dict[str, object]:
    def one(name: str) -> dict[str, object]:
        observation = fixtures[name]
        assert isinstance(observation, Observation)
        return safe_measure(measure_one, observation)

    ladder = []
    for item in fixtures["blur_ladder"]:
        assert isinstance(item, dict)
        observation = item["observation"]
        assert isinstance(observation, Observation)
        ladder.append(
            {
                "added_sigma_px": float(item["added_sigma_px"]),
                "measurement": safe_measure(measure_one, observation),
            }
        )

    return {
        "flat_roi": {
            "detail": one("flat_detail"),
            "flat": one("flat"),
        },
        "planted_improvement": {
            "base": one("base"),
            "improved": one("improved"),
        },
        "planted_degradation": {
            "base": one("base"),
            "degraded": one("degraded"),
        },
        "blur_monotonicity": ladder,
        "sharpening_discrimination": {
            "base": one("base"),
            "usm": one("usm"),
            "improved": one("improved"),
        },
        "fail_closed": {
            "nonfinite": one("nonfinite"),
            "wrong_shape": one("wrong_shape"),
        },
    }


def environment() -> dict[str, object]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "captures_opened": 0,
        "thread_contract": 1,
    }


def oracle_result() -> dict[str, object]:
    value = numeric_record
    return {
        "schema": 1,
        "candidate": {
            "name": "constructed-optical-truth-oracle",
            "kind": "INELIGIBLE_CONSTRUCTION_TRUTH",
            "input_mode": "private_truth_labels",
            "score_orientation": "higher_is_more_resolved",
        },
        "environment": environment(),
        "arms": {
            "flat_roi": {
                "detail": value(1.0 / BASE_SIGMA),
                "flat": {
                    "status": "REFUSED",
                    "code": "NO_DETAIL",
                    "reason": "construction truth has no scene modulation",
                },
            },
            "planted_improvement": {
                "base": value(1.0 / BASE_SIGMA),
                "improved": value(1.0 / IMPROVED_SIGMA),
            },
            "planted_degradation": {
                "base": value(1.0 / BASE_SIGMA),
                "degraded": value(1.0 / DEGRADED_SIGMA),
            },
            "blur_monotonicity": [
                {
                    "added_sigma_px": sigma,
                    "measurement": value(
                        1.0 / math.sqrt(BASE_SIGMA**2 + sigma**2)
                    ),
                }
                for sigma in BLUR_SIGMAS
            ],
            "sharpening_discrimination": {
                "base": value(1.0 / BASE_SIGMA),
                "usm": value(1.0 / BASE_SIGMA),
                "improved": value(1.0 / IMPROVED_SIGMA),
            },
            "fail_closed": {
                "nonfinite": {
                    "status": "REFUSED",
                    "code": "NONFINITE_INPUT",
                    "reason": "construction oracle refuses malformed input",
                },
                "wrong_shape": {
                    "status": "ERROR",
                    "code": "INVALID_SHAPE",
                    "reason": "construction oracle requires a 2-D image",
                },
            },
        },
        "diagnostics": {
            "eligible_as_candidate": False,
            "purpose": "prove the registered accepted set is nonempty",
        },
    }


def d8_result(fixtures: dict[str, object]) -> dict[str, object]:
    source_hash = require_hash(D8_PATH, D8_SHA256)
    frc = load_module("m167_historical_d8_frc", D8_PATH)

    def measure_one(observation: Observation) -> dict[str, object]:
        analysis = frc.analyse_pair(
            observation.repeat_a, observation.repeat_b, tile=256
        )
        crossing = frc.classify(analysis.aggregate)
        outcome = crossing["outcome"]
        frequency = crossing["frequency_or_bound"]
        if outcome == "MEASURED":
            return numeric_record(frequency)
        if outcome == "CENSORED_ABOVE":
            return {
                "status": "LOWER_BOUND",
                "score": float(frequency),
                "reason": "D8 FRC remained above 1/7 through the last ring",
            }
        if outcome == "CENSORED_BELOW":
            return {
                "status": "UPPER_BOUND",
                "score": float(frequency),
                "reason": "D8 FRC began below 1/7",
            }
        return {
            "status": "REFUSED",
            "code": "INSUFFICIENT",
            "reason": "D8 found no physically valid crossing",
        }

    flat = fixtures["flat"]
    detail = fixtures["flat_detail"]
    assert isinstance(flat, Observation)
    assert isinstance(detail, Observation)
    flat_analysis = frc.analyse_pair(
        flat.repeat_a, flat.repeat_b, tile=256
    )
    detail_analysis = frc.analyse_pair(
        detail.repeat_a, detail.repeat_b, tile=256
    )
    return {
        "schema": 1,
        "candidate": {
            "name": "D8-per-tile-FRC",
            "kind": "KNOWN_DEAD",
            "input_mode": "repeat_pair",
            "score_orientation": "higher_crossing_is_more_resolved",
        },
        "environment": environment(),
        "provenance": {
            "source": str(D8_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": source_hash,
        },
        "arms": standard_arms(fixtures, measure_one),
        "diagnostics": {
            "flat_low_band_frc": float(
                frc.band_frc(flat_analysis.aggregate, 0.02, 0.15)
            ),
            "detail_low_band_frc": float(
                frc.band_frc(detail_analysis.aggregate, 0.02, 0.15)
            ),
            "historical_common_mode_low_band_frc": 0.972099,
        },
    }


def band_result(fixtures: dict[str, object]) -> dict[str, object]:
    source_hash = require_hash(BAND_PATH, BAND_SHA256)
    evidence_hash = require_hash(
        BAND_EVIDENCE_PATH, BAND_EVIDENCE_SHA256
    )
    report_hash = require_hash(BAND_REPORT_PATH, BAND_REPORT_SHA256)
    band = load_module("m167_historical_band_power", BAND_PATH)

    def measure_one(observation: Observation) -> dict[str, object]:
        return numeric_record(band.band_ratio(observation.image, 1.0))

    arms = standard_arms(fixtures, measure_one)
    arms["flat_roi"] = {
        "detail": numeric_record(BAND_DETAIL_GAP),
        "flat": numeric_record(BAND_FLAT_GAP),
    }
    return {
        "schema": 1,
        "candidate": {
            "name": "M137-high-low-band-power-gap",
            "kind": "KNOWN_DEAD",
            "input_mode": "single_image_and_historical_kernel_pair",
            "score_orientation": "higher_band_gap_is_more_detail",
        },
        "environment": environment(),
        "provenance": {
            "underlying_source": str(BAND_PATH.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "underlying_source_sha256": source_hash,
            "flat_evidence": str(
                BAND_EVIDENCE_PATH.relative_to(ROOT)
            ).replace("\\", "/"),
            "flat_evidence_sha256": evidence_hash,
            "report": str(BAND_REPORT_PATH.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "report_sha256": report_hash,
        },
        "arms": arms,
        "diagnostics": {
            "historical_flat_snapshot": {
                "detail_gap_dex": BAND_DETAIL_GAP,
                "flat_gap_dex": BAND_FLAT_GAP,
                "flat_over_detail": BAND_FLAT_GAP / BAND_DETAIL_GAP,
                "recorded_flat_over_detail": BAND_FLAT_DETAIL_RATIO,
                "flat_structure_share": BAND_STRUCTURE_SHARE,
            },
            "synthetic_extension_scope": (
                "ordinary arms exercise the tracked underlying band_ratio; "
                "only the serialized historical kernel-gap pair decides P1"
            ),
        },
    }


def r_box9(image: np.ndarray) -> float:
    local_mean = uniform_filter(image, size=9)
    if float(local_mean.min()) <= 1e-9:
        raise RuntimeError("flat-ROI local mean reached zero")
    residual = image / local_mean - 1.0
    return float(np.std(residual))


def replay_m159_blur_ratio() -> dict[str, float]:
    rng = np.random.default_rng(159)
    height = width = 384
    yy, xx = np.mgrid[0:height, 0:width]
    latent = (
        0.42
        + 0.035 * (xx / (width - 1) - 0.5)
        - 0.025 * (yy / (height - 1) - 0.5)
        + 0.002 * np.sin(2 * np.pi * xx / 160.0)
    )
    sigma = 0.004
    for _ in range(128):
        baseline = latent + rng.normal(0.0, sigma, latent.shape)
        null = latent + rng.normal(0.0, sigma, latent.shape)
        _ = null + rng.normal(0.0, 1.5 * sigma, latent.shape)
        _ = [
            latent + rng.normal(0.0, sigma, latent.shape)
            for _ in range(4)
        ]
        # Preserve the source's computations even though they draw no RNG.
        _ = r_box9(baseline)
        _ = r_box9(null)

    texture = latent + 0.025 * np.sin(2 * np.pi * xx / 6.0)
    texture_noisy = texture + rng.normal(0.0, sigma, latent.shape)
    texture_blurred = gaussian_filter(texture_noisy, 1.0)
    unblurred = r_box9(texture_noisy)
    blurred = r_box9(texture_blurred)
    return {
        "unblurred_r_box9": unblurred,
        "blurred_r_box9": blurred,
        "blurred_over_unblurred": blurred / unblurred,
    }


def m2_result(fixtures: dict[str, object]) -> dict[str, object]:
    source_hash = require_hash(M2_PATH, M2_SHA256)
    result_hash = require_hash(M2_RESULT_PATH, M2_RESULT_SHA256)

    def measure_one(observation: Observation) -> dict[str, object]:
        return numeric_record(-r_box9(observation.image))

    return {
        "schema": 1,
        "candidate": {
            "name": "M2-R_box9",
            "kind": "KNOWN_DEAD",
            "input_mode": "single_image",
            "score_orientation": (
                "negative_residual; higher is favourable because historical "
                "M2 treated lower R_box9 as better"
            ),
        },
        "environment": environment(),
        "provenance": {
            "source": str(M2_PATH.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": source_hash,
            "frozen_result": str(
                M2_RESULT_PATH.relative_to(ROOT)
            ).replace("\\", "/"),
            "frozen_result_sha256": result_hash,
        },
        "arms": standard_arms(fixtures, measure_one),
        "diagnostics": {
            "m159_specificity_replay": replay_m159_blur_ratio(),
            "frozen_blurred_over_unblurred": M2_FROZEN_BLUR_RATIO,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "candidate", choices=("oracle", "d8", "band-power", "m2")
    )
    args = parser.parse_args()

    if args.candidate == "oracle":
        result = oracle_result()
    else:
        fixtures = build_fixtures()
        if args.candidate == "d8":
            result = d8_result(fixtures)
        elif args.candidate == "band-power":
            result = band_result(fixtures)
        else:
            result = m2_result(fixtures)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
    raise SystemExit(main())
