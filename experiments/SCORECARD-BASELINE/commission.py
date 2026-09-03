from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

from common import OUT, bandpass, m1_tile, m2_eta, phase_translation, robust_sigma, write_json


PLANTS = ("M1_BLUR", "M2_NOISE", "M2_BLUR", "GEOMETRY")


def broadband(side: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = rng.normal(size=(side, side))
    transformed = np.fft.rfft2(image)
    fy = np.fft.fftfreq(side)[:, None]
    fx = np.fft.rfftfreq(side)[None, :]
    frequency = np.hypot(fx, fy)
    envelope = np.exp(-((frequency / 0.31) ** 6))
    return np.fft.irfft2(transformed * envelope, s=image.shape)


def edge_width(image: np.ndarray) -> float:
    profile = np.mean(np.asarray(image, dtype=np.float64), axis=0)
    lo = float(np.median(profile[:16]))
    hi = float(np.median(profile[-16:]))
    if hi <= lo:
        raise ValueError("edge polarity is not increasing")
    normalized = (profile - lo) / (hi - lo)

    def crossing(level: float) -> float:
        indices = np.flatnonzero(normalized >= level)
        if not indices.size or indices[0] == 0:
            raise ValueError("edge does not cross requested level")
        right = int(indices[0])
        left = right - 1
        fraction = (level - normalized[left]) / (normalized[right] - normalized[left])
        return left + float(fraction)

    return crossing(0.9) - crossing(0.1)


def run_case(plant: str = "") -> dict[str, object]:
    if plant not in ("", *PLANTS):
        raise ValueError(f"unknown plant {plant}")
    side = 256
    latent = broadband(side, 1001)
    rng = np.random.default_rng(1002)
    reference = latent + 0.05 * rng.normal(size=latent.shape)
    a = latent + 0.15 * rng.normal(size=latent.shape)
    b = latent + 0.15 * rng.normal(size=latent.shape)
    if plant == "M1_BLUR":
        a = gaussian_filter(latent, 1.8) + 0.15 * np.random.default_rng(1003).normal(
            size=latent.shape
        )
        b = gaussian_filter(latent, 1.8) + 0.15 * np.random.default_rng(1004).normal(
            size=latent.shape
        )
    m1 = m1_tile(a, b, reference)

    common_a = a.copy()
    common_b = b.copy()
    yy, xx = np.indices(latent.shape)
    common_pattern = 3.0 * np.sin(2.0 * math.pi * 0.22 * xx)
    common_a += common_pattern
    common_b += common_pattern
    common_result = m1_tile(common_a, common_b, reference)
    flat_reference = 0.02 * np.random.default_rng(1010).normal(size=latent.shape)
    flat_result = m1_tile(
        0.08 * np.random.default_rng(1011).normal(size=latent.shape),
        0.08 * np.random.default_rng(1012).normal(size=latent.shape),
        flat_reference,
    )
    flat_signal_ratio = sum(row["reference_power"] for row in flat_result["bins"]) / max(
        sum(row["noise"] for row in flat_result["bins"]), 1e-30
    )
    sharpened = []
    for image in (a, b):
        sharpened.append(image + 1.5 * (image - gaussian_filter(image, 1.0)))
    sharpened_result = m1_tile(sharpened[0], sharpened[1], reference)

    n = 128
    scene = gaussian_filter(broadband(n, 2001), 3.0)
    rng = np.random.default_rng(2002)
    noise_output = rng.normal(size=(n, n))
    noise_heldout = rng.normal(size=(n, n))
    sigma_one = robust_sigma(bandpass(noise_output, 0.15, 0.35))
    output = scene + noise_output / 4.0
    heldout = scene + noise_heldout / 4.0
    if plant == "M2_NOISE":
        output = output + 0.25 * rng.normal(size=(n, n))
    m2 = m2_eta(output, heldout, sigma_one)

    x = np.arange(n, dtype=np.float64)
    step = np.tile((x >= n // 2).astype(np.float64), (n, 1))
    blurred = gaussian_filter(step, 1.25)
    width_ratio = edge_width(blurred) / edge_width(gaussian_filter(step, 0.45))
    raw_noise = robust_sigma(bandpass(output - heldout, 0.15, 0.35))
    blurred_noise = robust_sigma(
        bandpass(gaussian_filter(output, 1.0) - gaussian_filter(heldout, 1.0), 0.15, 0.35)
    )

    base = broadband(256, 3001)
    moved = np.roll(np.roll(base, 2, axis=0), -3, axis=1)
    if plant == "GEOMETRY":
        moved = np.roll(moved, 1, axis=1)
    geometry = phase_translation(base, moved)

    checks = {
        "external_predicates": {
            "m1_cutoff": m1["f_licensed"],
            "m1_S25": m1["S_25"],
            "m2_eta": m2["eta"],
            "blur_noise_ratio": blurred_noise / raw_noise,
            "blur_width_ratio": width_ratio,
            "geometry_shift": list(geometry),
            "common_mode_cutoff_movement": common_result["f_licensed"]
            - m1["f_licensed"],
            "flat_signal_ratio": flat_signal_ratio,
            "unsharp_cutoff_movement": sharpened_result["f_licensed"]
            - m1["f_licensed"],
        },
        "expected_red": None,
    }
    if plant == "":
        checks["expected_red"] = False
        checks["passed"] = (
            m1["f_licensed"] >= 0.24
            and 0.90 <= m2["eta"] <= 1.10
            and abs(geometry[0] + 2.0) <= 0.06
            and abs(geometry[1] - 3.0) <= 0.06
            and abs(common_result["f_licensed"] - m1["f_licensed"]) <= 0.005
            and flat_signal_ratio < 1.5
            and abs(sharpened_result["f_licensed"] - m1["f_licensed"]) <= 0.005
        )
    elif plant == "M1_BLUR":
        clean = m1_tile(
            latent + 0.08 * np.random.default_rng(41).normal(size=latent.shape),
            latent + 0.08 * np.random.default_rng(42).normal(size=latent.shape),
            reference,
        )
        drop = clean["f_licensed"] - m1["f_licensed"]
        checks["external_predicates"]["cutoff_drop"] = drop
        checks["expected_red"] = True
        checks["passed"] = drop >= 0.02
    elif plant == "M2_NOISE":
        clean_eta = m2_eta(
            scene + noise_output / 4.0,
            scene + noise_heldout / 4.0,
            sigma_one,
        )["eta"]
        increase = m2["eta"] - clean_eta
        checks["external_predicates"]["eta_increase"] = increase
        checks["expected_red"] = True
        checks["passed"] = increase >= 0.20
    elif plant == "M2_BLUR":
        checks["expected_red"] = True
        checks["passed"] = blurred_noise < raw_noise and width_ratio > 1.05
    elif plant == "GEOMETRY":
        checks["expected_red"] = True
        checks["passed"] = abs(geometry[1] - 3.0) >= 0.9
    return checks


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) == 3 and sys.argv[1] == "--plant":
        result = run_case(sys.argv[2])
        print(json.dumps(result, indent=2))
        return 1 if result["passed"] else 0

    null = run_case("")
    rows = []
    all_pass = bool(null["passed"])
    for plant in PLANTS:
        command = [sys.executable, str(Path(__file__).resolve()), "--plant", plant]
        process = subprocess.run(command, capture_output=True, text=True)
        payload = json.loads(process.stdout)
        red = process.returncode != 0 and bool(payload["passed"])
        rows.append(
            {
                "plant": plant,
                "returncode": process.returncode,
                "went_red": red,
                "reading": payload,
                "stderr": process.stderr,
            }
        )
        all_pass &= red
    result = {
        "null_stayed_green": bool(null["passed"]),
        "null": null,
        "plants": rows,
        "all_commissioned": all_pass,
        "thread_caps": {
            key: os.environ.get(key)
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }
    write_json(OUT / "commission.json", result)
    print(json.dumps(result, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
