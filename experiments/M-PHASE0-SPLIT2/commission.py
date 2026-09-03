"""Commission every SPLIT2 instrument before any real RAW pixel is read."""

from __future__ import annotations

import cmath
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

import frc


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
PLANTS = ("N1", "P1", "S1", "C1", "C2", "C3", "G1", "G2", "T1")


def smooth_signal(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    image = 18.0 * rng.normal(size=(n, n))
    for _ in range(5):
        image = sum(
            np.roll(np.roll(image, dy, axis=0), dx, axis=1)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
        ) / 9.0
    return image


def fixed_planes(n: int = 8) -> tuple[np.ndarray, np.ndarray]:
    a = np.empty((n, n), dtype=np.float64)
    b = np.empty((n, n), dtype=np.float64)
    for y in range(n):
        for x in range(n):
            shared = (
                math.sin(2.0 * math.pi * x / n)
                + 0.35 * math.cos(2.0 * math.pi * (x + 2.0 * y) / n)
                + 0.03 * x * y
            )
            independent = 0.17 * math.sin(2.0 * math.pi * (3.0 * x + y) / n)
            a[y, x] = shared
            b[y, x] = 0.8 * shared + independent
    return a, b


def direct_dft_spectrum(a: np.ndarray, b: np.ndarray) -> frc.Spectrum:
    """External O(N^4) predicate; it does not call NumPy's FFT."""
    n = a.shape[0]
    window = np.asarray(
        [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]
    )
    aw = (a - float(np.mean(a))) * window[:, None] * window[None, :]
    bw = (b - float(np.mean(b))) * window[:, None] * window[None, :]

    def dft(image: np.ndarray, kx: int, ky: int) -> complex:
        total = 0j
        for y in range(n):
            for x in range(n):
                phase = -2.0j * math.pi * (kx * x + ky * y) / n
                total += float(image[y, x]) * cmath.exp(phase)
        return total

    result = frc.Spectrum.zeros(n // 2 + 1)
    for ky_index in range(n):
        ky = ky_index if ky_index <= n // 2 else ky_index - n
        for kx_index in range(n):
            kx = kx_index if kx_index <= n // 2 else kx_index - n
            radius = int(math.floor(math.hypot(kx, ky) + 0.5))
            if radius == 0 or radius > n // 2:
                continue
            fa = dft(aw, kx_index, ky_index)
            fb = dft(bw, kx_index, ky_index)
            result.count[radius] += 1.0
            result.cross[radius] += (fa * fb.conjugate()).real
            result.power_a[radius] += abs(fa) ** 2
            result.power_b[radius] += abs(fb) ** 2
            result.noise[radius] += 0.5 * abs(fa - fb) ** 2
    return result


def maximum_relative_spectrum_error() -> float:
    a, b = fixed_planes()
    got = frc.spectrum_tile(a, b)
    expected = direct_dft_spectrum(a, b)
    maximum = 0.0
    for field in ("count", "cross", "power_a", "power_b", "noise"):
        actual = getattr(got, field)
        wanted = getattr(expected, field)
        relative = np.abs(actual - wanted) / np.maximum(1.0, np.abs(wanted))
        maximum = max(maximum, float(np.max(relative)))
    return maximum


def curve(values: list[float | None]) -> frc.Spectrum:
    result = frc.Spectrum.zeros(len(values) + 1)
    for index, value in enumerate(values, 1):
        if value is None:
            continue
        result.count[index] = frc.MIN_RING_SAMPLES
        result.cross[index] = value
        result.power_a[index] = 1.0
        result.power_b[index] = 1.0
        result.noise[index] = 1.0
    return result


def exact_fourier_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    n = image.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    mtf = np.exp(-2.0 * math.pi**2 * sigma**2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(image) * mtf, s=image.shape)


def nonlinear_shrink(image: np.ndarray, strength: float) -> np.ndarray:
    """A nonlinear, per-image shrinker whose gain depends on observed power."""
    image = np.asarray(image, dtype=np.float64)
    n = image.shape[0]
    transformed = np.fft.rfft2(image)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    frequency = np.hypot(fx, fy)
    power = np.abs(transformed) ** 2
    noise_power = float(np.median(power[(frequency >= 0.40) & (frequency < 0.49)]))
    gain = np.maximum(0.0, 1.0 - strength * noise_power / np.maximum(power, 1e-30))
    return np.fft.irfft2(transformed * gain, s=image.shape)


def tune_on_training(
    train_a: np.ndarray,
    train_b: np.ndarray,
) -> tuple[float, list[dict[str, float]]]:
    candidates = (0.0, 0.5, 1.0, 2.0, 4.0)
    rows = []
    for strength in candidates:
        out_a = nonlinear_shrink(train_a, strength)
        out_b = nonlinear_shrink(train_b, strength)
        analysis = frc.analyse_pair(out_a, out_b, tile=64)
        rows.append(
            {
                "strength": strength,
                "score": frc.band_frc(analysis.aggregate, 0.15, 0.35),
            }
        )
    selected = max(rows, key=lambda row: row["score"])
    return float(selected["strength"]), rows


def held_out_tuner(
    train_a: np.ndarray,
    train_b: np.ndarray,
    evaluate_c: np.ndarray,
    evaluate_d: np.ndarray,
    *,
    leak_evaluation: bool,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    strength, training_rows = tune_on_training(train_a, train_b)
    base_c = nonlinear_shrink(evaluate_c, strength)
    base_d = nonlinear_shrink(evaluate_d, strength)
    if not leak_evaluation:
        analysis = frc.analyse_pair(base_c, base_d, tile=64)
        return base_c, base_d, {
            "selected_strength": strength,
            "selected_leak": 0.0,
            "training_candidates": training_rows,
            "evaluation_high_band_frc": frc.band_frc(
                analysis.aggregate, 0.30, 0.48
            ),
        }

    # Plant T1 is a realistic held-out violation: use the evaluation pair to
    # tune how much shared data leaks into each nominally independent output.
    # At full leakage the pair is algebraically identical, so FRC reaches its
    # exact structural ceiling even though no latent information was added.
    guide = 0.5 * (base_c + base_d)
    leak_rows = []
    for leak in (0.0, 0.25, 0.5, 0.75, 1.0):
        out_c = (1.0 - leak) * base_c + leak * guide
        out_d = (1.0 - leak) * base_d + leak * guide
        analysis = frc.analyse_pair(out_c, out_d, tile=64)
        leak_rows.append(
            {
                "leak": leak,
                "score": frc.band_frc(analysis.aggregate, 0.30, 0.48),
            }
        )
    selected = max(leak_rows, key=lambda row: row["score"])
    leak = float(selected["leak"])
    out_c = (1.0 - leak) * base_c + leak * guide
    out_d = (1.0 - leak) * base_d + leak * guide
    return out_c, out_d, {
        "selected_strength": strength,
        "selected_leak": leak,
        "training_candidates": training_rows,
        "leak_candidates": leak_rows,
        "evaluation_high_band_frc": float(selected["score"]),
    }


def tuner_control(plant: str) -> dict[str, object]:
    n = 256
    signal = smooth_signal(n, 0x710E)
    rng = np.random.default_rng(0xDADA)
    repeats = [signal + 1.8 * rng.normal(size=(n, n)) for _ in range(4)]
    leak = plant == "T1"
    out_c, _, details = held_out_tuner(*repeats, leak_evaluation=leak)

    # Fixed external lineage predicate: the tuner did not generate this
    # checkerboard, and only D is perturbed. A held-out C product cannot change.
    yy, xx = np.indices((n, n))
    external = 50.0 * np.where((xx + yy) % 2 == 0, 1.0, -1.0)
    changed_d = repeats[3] + external
    changed_c, _, changed_details = held_out_tuner(
        repeats[0],
        repeats[1],
        repeats[2],
        changed_d,
        leak_evaluation=leak,
    )
    cross_talk = float(np.max(np.abs(changed_c - out_c)))
    return {
        **details,
        "perturbed_selected_leak": changed_details["selected_leak"],
        "external_c_output_max_change": cross_talk,
        "external_predicate": "perturb D only; C output must be bit-identical",
    }


def stability_control(plant: str) -> dict[str, object]:
    n = 256
    signal = smooth_signal(n, 0x57AB1E)
    rng = np.random.default_rng(0x51A8)
    frames = [signal + 0.002 * rng.normal(size=(n, n)) for _ in range(4)]
    if plant == "G1":
        frames[2] = np.roll(frames[2], 1, axis=1)
    elif plant == "G2":
        frames[2] = exact_fourier_blur(frames[2], 1.0)
    return frc.stability_gate(frames)


def acceptance(plant: str) -> dict[str, object]:
    if plant not in ("", *PLANTS):
        raise ValueError(f"unknown plant {plant!r}")
    external_dft_error = maximum_relative_spectrum_error()

    n = 256
    rng_a = np.random.default_rng(0x123456)
    rng_b = np.random.default_rng(0xABCDEF)
    null_a = rng_a.normal(size=(n, n))
    null_b = null_a.copy() if plant == "N1" else rng_b.normal(size=(n, n))
    null = frc.analyse_pair(null_a, null_b, tile=64)
    null_mean = frc.mean_abs_frc(null.aggregate)
    null_t = frc.max_ring_null_t(null.tiles)
    null_bands = [
        frc.band_frc(null.aggregate, low, high) for low, high in frc.NULL_BANDS
    ]

    common_a = null_a.copy()
    common_b = (rng_b.normal(size=(n, n)) if plant == "N1" else null_b.copy())
    yy, xx = np.indices((n, n))
    fixed = 2.0 * np.sin(2.0 * math.pi * 5.0 * xx / 64.0)
    fixed += np.cos(2.0 * math.pi * 3.0 * yy / 64.0)
    common = frc.analyse_pair(common_a + fixed, common_b + fixed, tile=64)
    common_low = frc.band_frc(common.aggregate, 0.02, 0.15)

    signal = smooth_signal(n, 0xA11CE55E)
    positive_rng_a = np.random.default_rng(0x13579B)
    positive_rng_b = np.random.default_rng(0x2468AC)
    positive_a = signal + 1.2 * positive_rng_a.normal(size=(n, n))
    positive_b = signal + 1.2 * positive_rng_b.normal(size=(n, n))
    positive = frc.analyse_pair(
        positive_a,
        positive_b,
        tile=64,
        wrong_conjugate=plant == "P1",
    )
    positive_low = frc.band_frc(positive.aggregate, 0.02, 0.10)
    positive_high = frc.band_frc(positive.aggregate, 0.35, 0.48)
    identity = frc.analyse_pair(signal, signal, tile=64)
    identity_values = identity.aggregate.frc()
    identity_error = float(
        np.max(np.abs(identity_values[np.isfinite(identity_values)] - 1.0))
    )

    sharpened_a = frc.unsharp(positive_a)
    sharpened_b = frc.unsharp(positive_b)
    sharpened = frc.analyse_pair(sharpened_a, sharpened_b, tile=64)
    positive_values = positive.aggregate.frc()
    sharpened_values = sharpened.aggregate.frc()
    valid = np.isfinite(positive_values) & np.isfinite(sharpened_values)
    maximum_ring_move = float(
        np.max(np.abs(positive_values[valid] - sharpened_values[valid]))
    )
    acuity_gain = frc.gradient_acuity(sharpened_a) / frc.gradient_acuity(positive_a)
    crossing_before = frc.classify(positive.aggregate)
    crossing_after = frc.classify(sharpened.aggregate)
    if (
        crossing_before["outcome"] != "MEASURED"
        or crossing_after["outcome"] != "MEASURED"
    ):
        raise AssertionError(
            f"sharpening control needs measured crossings: "
            f"{crossing_before}, {crossing_after}"
        )
    crossing_move = float(crossing_after["frequency_or_bound"]) - float(
        crossing_before["frequency_or_bound"]
    )
    checked_crossing_move = acuity_gain - 1.0 if plant == "S1" else crossing_move

    censored = frc.classify(
        curve([0.9, 0.8, 0.7, 0.6, 0.5]),
        last_bin_fallback=plant == "C1",
    )
    gapped = frc.classify(
        curve([0.4, 0.1, None, 0.05, 0.04]),
        ignore_ring_gaps=plant == "C2",
    )
    short_tail = frc.classify(
        curve([0.9, 0.8, 0.1, 0.05]),
        false_above_tail=plant == "C3",
    )

    stability_error = None
    stability = None
    try:
        stability = stability_control(plant)
    except ValueError as error:
        stability_error = str(error)

    tuner = tuner_control(plant)
    result = {
        "plant": plant or None,
        "fixed_external_dft_max_relative_error": external_dft_error,
        "null": {
            "mean_abs_frc": null_mean,
            "max_ring_abs_t": null_t,
            "bands": null_bands,
        },
        "common_mode": {"low_band_frc": common_low},
        "positive": {
            "low_band_frc": positive_low,
            "high_band_frc": positive_high,
            "identity_max_error": identity_error,
        },
        "sharpening": {
            "maximum_ring_frc_move": maximum_ring_move,
            "naive_acuity_gain": acuity_gain,
            "crossing_before": crossing_before,
            "crossing_after": crossing_after,
            "crossing_move": crossing_move,
            "checked_crossing_move": checked_crossing_move,
        },
        "classifier": {
            "censored": censored,
            "gapped": gapped,
            "short_tail": short_tail,
        },
        "stability": stability,
        "stability_error": stability_error,
        "data_dependent_tuner": tuner,
    }
    print("READINGS " + json.dumps(result, allow_nan=True, sort_keys=True))

    assert external_dft_error <= 1e-9
    assert null_mean < 0.05
    assert null_t < 4.0
    assert all(abs(value) < 0.08 for value in null_bands)
    assert abs(common_low) >= 0.08
    assert positive_low >= 0.90
    assert positive_high <= 0.60
    assert positive_low - positive_high >= 0.25
    assert identity_error <= 1e-12
    assert acuity_gain >= 1.25
    assert checked_crossing_move <= 1e-6
    assert abs(checked_crossing_move) <= 1.0 / 64.0
    assert censored["outcome"] == "CENSORED_ABOVE"
    assert gapped["outcome"] == "INSUFFICIENT"
    assert short_tail["outcome"] == "INSUFFICIENT"
    assert stability_error is None
    assert tuner["external_c_output_max_change"] == 0.0
    return result


def internal(plant: str) -> int:
    try:
        acceptance(plant)
    except Exception as error:
        print(f"COMMISSION RED {plant or 'CLEAN'}: {type(error).__name__}: {error}")
        return 1
    print(f"COMMISSION GREEN {plant or 'CLEAN'}")
    return 0


def run_child(plant: str) -> subprocess.CompletedProcess[str]:
    arguments = [sys.executable, str(Path(__file__).resolve()), "--internal"]
    if plant:
        arguments.extend(["--plant", plant])
    return subprocess.run(
        arguments,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    plant = ""
    if "--plant" in sys.argv:
        plant = sys.argv[sys.argv.index("--plant") + 1]
    if "--internal" in sys.argv:
        return internal(plant)

    clean = run_child("")
    if clean.returncode != 0:
        print(clean.stdout)
        raise RuntimeError(f"clean commissioning returned {clean.returncode}")
    marker = next(
        line.removeprefix("READINGS ")
        for line in clean.stdout.splitlines()
        if line.startswith("READINGS ")
    )
    readings = json.loads(marker)

    plants = {}
    plant_readings = {}
    plant_measurements = {}
    for name in PLANTS:
        proc = run_child(name)
        plants[name] = proc.returncode
        plant_readings[name] = proc.stdout.strip().splitlines()[-1]
        reading_line = next(
            (
                line.removeprefix("READINGS ")
                for line in proc.stdout.splitlines()
                if line.startswith("READINGS ")
            ),
            None,
        )
        if reading_line is not None:
            plant_measurements[name] = json.loads(reading_line)
        if proc.returncode != 1:
            print(proc.stdout)
            raise RuntimeError(f"{name} returned {proc.returncode}, expected RED exit 1")

    result = {
        "status": "COMMISSIONED_GREEN",
        "clean_exit": clean.returncode,
        "plants": plants,
        "plant_readings": plant_readings,
        "plant_measurements": plant_measurements,
        "all_plants_red": all(code == 1 for code in plants.values()),
        "control_families": [
            "fixed_external_direct_dft",
            "independent_noise_null",
            "common_mode_adversary",
            "positive_and_full_effect",
            "identical_sharpening",
            "endpoint_gap_and_tail_refusal",
            "pixel_shift_and_focus_stability",
            "held_out_data_dependent_tuner_lineage",
        ],
        "readings": readings,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "commission.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"COMMISSION FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
