# Reproduce the historical M164 artifact without touching the live M164 lane.

from __future__ import annotations

import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter


REPO = Path(__file__).resolve().parents[2]
COMMIT = "19f6f54a7ef5a6622e64c9ed2a2ddb32c1bb76f9"
EXPECTED_SHA256 = (
    "418D2D852DC15B072CB65DD6BAAECAA9B4CBF82843BA825F00B0440ACC733C43"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def run_checked(
    arguments: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        arguments,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed with {completed.returncode}: {arguments}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def replay_m159_blur_ratio() -> tuple[float, float, float]:
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

    def r_box9(image: np.ndarray) -> float:
        return float(np.std(image / uniform_filter(image, size=9) - 1.0))

    # Advance the registered seed through all 128 commissioning trials.
    for _ in range(128):
        baseline = latent + rng.normal(0.0, sigma, latent.shape)
        null = latent + rng.normal(0.0, sigma, latent.shape)
        degraded = null + rng.normal(0.0, 1.5 * sigma, latent.shape)
        captures = [
            latent + rng.normal(0.0, sigma, latent.shape) for _ in range(4)
        ]
        improved = np.mean(captures, axis=0)
        r_box9(baseline)
        r_box9(null)
        r_box9(degraded)
        r_box9(improved)

    texture = latent + 0.025 * np.sin(2 * np.pi * xx / 6.0)
    unblurred_image = texture + rng.normal(0.0, sigma, latent.shape)
    blurred_image = gaussian_filter(unblurred_image, 1.0)
    unblurred = r_box9(unblurred_image)
    blurred = r_box9(blurred_image)
    return unblurred, blurred, blurred / unblurred


def assert_close(actual: float, expected: float, name: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15):
        raise AssertionError(f"{name}: {actual!r} != {expected!r}")


def main() -> None:
    resolved = run_checked(
        ["git", "rev-parse", COMMIT], cwd=REPO
    ).stdout.strip()
    assert resolved == COMMIT

    archive = subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            COMMIT,
            "--",
            "docs/research/M164-m2-repair.md",
            "experiments/M164-m2-repair",
        ],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout

    with tempfile.TemporaryDirectory(prefix="M168-identifiability-") as name:
        root = Path(name)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            bundle.extractall(root)

        experiment = root / "experiments" / "M164-m2-repair"
        result_path = experiment / "commission.json"
        committed = result_path.read_bytes()

        environment = os.environ.copy()
        for variable in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            environment[variable] = "1"

        commissioned = run_checked(
            [sys.executable, "-B", "experiments/M164-m2-repair/commission.py"],
            cwd=root,
            environment=environment,
        )
        regenerated = result_path.read_bytes()
        committed_hash = sha256_bytes(committed)
        regenerated_hash = sha256_bytes(regenerated)

        assert committed_hash == EXPECTED_SHA256
        assert regenerated_hash == EXPECTED_SHA256
        assert committed == regenerated

        result = json.loads(regenerated)
        summaries = result["summaries"]
        mechanism = result["m159_mechanism_probe"]
        crossfit = result["same_resolution_crossfit_probe"]["summaries"]

        expected_figures = {
            "fractional_without_division": (
                mechanism[
                    "additive_box9_over_global_mean_blurred_over_unblurred"
                ],
                0.5713180075739982,
            ),
            "fractional_with_division": (
                mechanism["fractional_r_box9_blurred_over_unblurred"],
                0.5711797973518002,
            ),
            "median_local_mean_ratio": (
                mechanism["median_local_mean_blurred_over_unblurred"],
                0.9996748398406278,
            ),
            "null": (
                summaries["fresh_null"]["q_ein"]["geometric_mean"],
                1.0005350584230779,
            ),
            "added_noise": (
                summaries["noise_degradation"]["q_ein"]["geometric_mean"],
                1.4996543590668319,
            ),
            "denoising": (
                summaries["denoising_improvement"]["q_ein"][
                    "geometric_mean"
                ],
                0.49966266034901213,
            ),
            "pre_noise_blur": (
                summaries["pre_noise_blur"]["q_ein"]["geometric_mean"],
                1.7477860108906,
            ),
            "optical_improvement": (
                summaries["optical_improvement"]["q_ein"]["geometric_mean"],
                0.7615044903960827,
            ),
            "post_blur_naive": (
                summaries["post_blur"]["naive_output_noise_ratio"][
                    "geometric_mean"
                ],
                0.6296206988040738,
            ),
            "post_blur_transfer": (
                summaries["post_blur"]["transfer_ratio"]["geometric_mean"],
                0.6296206988040738,
            ),
            "post_blur_q": (
                summaries["post_blur"]["q_ein"]["geometric_mean"],
                1.0,
            ),
            "post_usm_naive": (
                summaries["post_usm"]["naive_output_noise_ratio"][
                    "geometric_mean"
                ],
                1.3992089852156073,
            ),
            "post_usm_transfer": (
                summaries["post_usm"]["transfer_ratio"]["geometric_mean"],
                1.3992089852156075,
            ),
            "post_usm_q": (
                summaries["post_usm"]["q_ein"]["geometric_mean"],
                1.0,
            ),
            "post_gain_q": (
                summaries["post_gain"]["q_ein"]["geometric_mean"],
                1.0,
            ),
            "maximum_common_transfer_q_departure": (
                summaries["post_blur"]["q_ein"]["max_abs_from_one"],
                2.220446049250313e-16,
            ),
            "blur_plus_denoise_q": (
                summaries["blur_plus_denoise"]["q_ein"]["geometric_mean"],
                0.5831195313963279,
            ),
            "blur_plus_denoise_naive": (
                summaries["blur_plus_denoise"]["naive_output_noise_ratio"][
                    "geometric_mean"
                ],
                0.3333975136733213,
            ),
            "blur_plus_denoise_transfer": (
                summaries["blur_plus_denoise"]["transfer_ratio"][
                    "geometric_mean"
                ],
                0.5717481506321243,
            ),
            "same_resolution_blur_crossfit": (
                crossfit["blur_crossfit"]["geometric_mean"],
                8.016758618164431,
            ),
            "same_resolution_optical_crossfit": (
                crossfit["optical_improvement_crossfit"]["geometric_mean"],
                10.817810773460156,
            ),
            "same_resolution_denoising_crossfit": (
                crossfit["denoising_improvement_crossfit"]["geometric_mean"],
                0.7896950558543623,
            ),
            "same_resolution_blur_truth_error": (
                crossfit["blur_truth_error"]["geometric_mean"],
                1.7082242382511399,
            ),
            "same_resolution_optical_truth_error": (
                crossfit["optical_improvement_truth_error"]["geometric_mean"],
                0.06748327800205457,
            ),
        }
        for figure, (actual, expected) in expected_figures.items():
            assert_close(float(actual), expected, figure)

        directional = {
            "added_noise_worse": summaries["noise_degradation"]["q_ein"][
                "above_one"
            ],
            "denoising_better": summaries["denoising_improvement"]["q_ein"][
                "below_one"
            ],
            "pre_noise_blur_worse": summaries["pre_noise_blur"]["q_ein"][
                "above_one"
            ],
            "optical_improvement_better": summaries["optical_improvement"][
                "q_ein"
            ]["below_one"],
        }
        assert directional == {
            "added_noise_worse": 256,
            "denoising_better": 256,
            "pre_noise_blur_worse": 256,
            "optical_improvement_better": 256,
        }

        verify_source = (experiment / "verify.py").read_text(encoding="utf-8")
        verify_lines = verify_source.splitlines()
        assert "result = json.loads" in verify_lines[49]
        assert "raw = result" in verify_lines[69]
        assert "default_rng" not in verify_source

        disabled_message = repr("default_rng disabled by M168")
        verify_name = repr("experiments/M164-m2-repair/verify.py")
        main_name = repr("__main__")
        patch = (
            "import numpy as np, runpy; "
            "np.random.default_rng=lambda *a,**k: "
            f"(_ for _ in ()).throw(RuntimeError({disabled_message})); "
            "print(\"DEFAULT_RNG_PATCH=RAISE\"); "
            f"runpy.run_path({verify_name}, run_name={main_name})"
        )
        verified = run_checked(
            [sys.executable, "-c", patch], cwd=root, environment=environment
        )
        assert "PASS: 8 checks" in verified.stdout

        m159_unblurred, m159_blurred, m159_ratio = replay_m159_blur_ratio()
        assert_close(m159_ratio, 0.5712148772282098, "M159 blur ratio")

        print(f"COMMIT={resolved}")
        print(f"COMMISSION_STDOUT={commissioned.stdout.strip()}")
        print(f"COMMITTED_SHA256={committed_hash}")
        print(f"REGENERATED_SHA256={regenerated_hash}")
        print(f"BYTE_IDENTICAL={committed == regenerated}")
        print(
            "M159_R_BOX9="
            f"unblurred={m159_unblurred:.17g} "
            f"blurred={m159_blurred:.17g} ratio={m159_ratio:.17g}"
        )
        for figure, (actual, _) in expected_figures.items():
            value = float(actual)
            rendered = f"{value:.17g}" if 0.0 < abs(value) < 1e-10 else f"{value:.12f}"
            print(f"{figure}={rendered}")
        print(
            "DIRECTIONAL_COUNTS="
            + ",".join(f"{key}:{value}/256" for key, value in directional.items())
        )
        normalized_verify = verified.stdout.strip().replace(str(root), "<TEMP>")
        print("VERIFY_WITH_RNG_DISABLED=" + normalized_verify.replace("\n", " | "))
        print("VERIFY_LOAD_LINE=50")
        print("VERIFY_STORED_SUMMARY_BLOCK=70-90")
        print("PASS: historical reproduction and verifier limitation confirmed")


if __name__ == "__main__":
    main()
