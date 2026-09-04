"""Independent audit of the M115 evidence cited by proposal D8.

This script does not open RAW files. It re-derives the advertised quantities
from the preserved byte-pinned M115 rerun and checks the historical source
blobs and the algebra that separates P_sig from normalized SNR/FRC.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path


LANE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
SPLIT = ROOT / "experiments" / "M-PHASE0-SPLIT"
RERUN = SPLIT / "out" / "m115-rerun"
RESULT = LANE / "d8-audit.json"


def git_text(commit: str, relative: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )


def git_blob(commit: str, relative: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{commit}:{relative}"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def power(values: list[complex]) -> float:
    return sum(abs(value) ** 2 for value in values) / len(values)


def cross(a: list[complex], b: list[complex]) -> float:
    return sum((x * y.conjugate()).real for x, y in zip(a, b)) / len(a)


def split_stats(a: list[complex], b: list[complex]) -> tuple[float, float, float, float]:
    psig = cross(a, b)
    pnoise = 0.5 * power([x - y for x, y in zip(a, b)])
    parm = 0.5 * (power(a) + power(b))
    snr = psig / pnoise
    frc = psig / math.sqrt(power(a) * power(b))
    return psig, pnoise, snr, frc


def rel_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1e-30)


def main() -> int:
    manifest = json.loads(
        (RERUN / "rerun-manifest.json").read_text(encoding="utf-8")
    )
    instrument = json.loads(
        (RERUN / "s03_instrument.json").read_text(encoding="utf-8")
    )
    phase0 = json.loads(
        (SPLIT / "out" / "postupdate-audit.json").read_text(encoding="utf-8")
    )

    commit = manifest["historical_commit"]
    base = "experiments/M115-deconv-headroom/src"
    source_blobs = {
        name: git_blob(commit, f"{base}/{name}")
        for name in manifest["source_blobs"]
    }
    blob_checks = {
        name: source_blobs[name] == expected
        for name, expected in manifest["source_blobs"].items()
    }

    library = git_text(commit, f"{base}/m115lib.py")
    controls = git_text(commit, f"{base}/s03_instrument.py")
    source_semantics = {
        "split_definitions_present": all(
            text in library
            for text in (
                "Ps = rb.cross(oa, ob)",
                "Pn = 0.5 * rb.power(oa - ob)",
                "Pa = 0.5 * (rb.power(oa) + rb.power(ob))",
            )
        ),
        "c2_filters_captured_cube_before_split": all(
            text in controls
            for text in (
                "cb = L.blur_cube(cube, sb)",
                "sp = L.split_channel(cb, g, rn_e, s0, crop, want=[arm])",
            )
        ),
        "blur_cube_filters_every_realized_frame": all(
            text in library
            for text in (
                "for k in range(cube.shape[0]):",
                "out[k] = fourier_gauss_blur(cube[k], sb).astype(np.float32)",
            )
        ),
        "c3_filters_completed_half_outputs": (
            "Ag, Bg = L.freq_gain(A, af), L.freq_gain(Bo, af)" in controls
        ),
        "reported_naive_gain_is_rms_gradient": (
            "ng = float(np.sqrt(gy1 / gy0))" in controls
        ),
    }

    c2 = instrument["C2"]["109MSDCF"]["res"]
    recoveries = [
        float(value)
        for arm in ("MEAN", "FRAME*")
        for value in c2[arm]["recovery"]
    ]
    c3 = instrument["C3"]["109MSDCF"]["rows"]
    filter_snr_ratios = {
        name: float(row["snr_ratio"]) for name, row in c3.items()
    }
    max_filter_move = max(abs(value - 1.0) for value in filter_snr_ratios.values())
    max_naive_rms = max(float(row["naive_grad_gain"]) for row in c3.values())

    c9 = instrument["C9"]["109MSDCF"]["rows"]
    identity_min = min(float(row["consistency"]) for row in c9.values())
    identity_max = max(float(row["consistency"]) for row in c9.values())
    direct_identity_max_absolute_error = 0.0
    direct_identity_scale = 0.0
    for row in instrument["C1p"]["arms"].values():
        for psig, pnoise, parm in zip(row["Ps"], row["Pn"], row["Pa"]):
            direct_identity_max_absolute_error = max(
                direct_identity_max_absolute_error,
                abs(float(psig) + float(pnoise) - float(parm)),
            )
            direct_identity_scale = max(direct_identity_scale, abs(float(parm)))
    direct_identity_scaled_error = (
        direct_identity_max_absolute_error / direct_identity_scale
    )

    a = [2.0 + 0.5j, 1.2 - 0.4j, 3.1 + 1.1j, 0.8 + 0.2j]
    b = [1.7 + 0.4j, 1.0 - 0.3j, 2.8 + 1.0j, 0.9 + 0.1j]
    base_stats = split_stats(a, b)
    scale_results = {}
    for name, gain in (("blur_like", 0.5 + 0.0j), ("sharpen_like", 2.0 + 0.0j)):
        filtered = split_stats(
            [gain * value for value in a],
            [gain * value for value in b],
        )
        scale_results[name] = {
            "power_gain": abs(gain) ** 2,
            "psig_ratio": filtered[0] / base_stats[0],
            "snr_ratio": filtered[2] / base_stats[2],
            "frc_ratio": filtered[3] / base_stats[3],
        }

    null_bar = float(instrument["C1p"]["bar"])
    null_max = {
        name: float(row["mx"]) for name, row in instrument["C1p"]["arms"].items()
    }
    null_failed = sorted(name for name, value in null_max.items() if value >= null_bar)
    common_mode_frc = float(
        phase0["transfer_and_meaning"]["common_mode_adversary_low_band_frc"]
    )

    checks = {
        "historical_sources_match_manifest": all(blob_checks.values()),
        "source_semantics_confirmed": all(source_semantics.values()),
        "blur_range_reproduces": (
            round(min(recoveries), 4) == 0.9938
            and round(max(recoveries), 4) == 0.9974
            and len(recoveries) == 8
        ),
        "filter_move_reproduces_0_54_percent": round(100.0 * max_filter_move, 2)
        == 0.54,
        "naive_gain_reproduces_8_25x": round(max_naive_rms, 2) == 8.25,
        "identity_reproduces": (
            round(identity_min, 4) == 1.0
            and round(identity_max, 4) == 1.0
            and direct_identity_scaled_error < 1e-10
        ),
        "common_filter_scales_psig": all(
            rel_error(row["psig_ratio"], row["power_gain"]) < 1e-12
            for row in scale_results.values()
        ),
        "common_filter_leaves_snr_and_frc_unchanged": all(
            abs(row["snr_ratio"] - 1.0) < 1e-12
            and abs(row["frc_ratio"] - 1.0) < 1e-12
            for row in scale_results.values()
        ),
        "historical_null_failed": (
            instrument["C1p"]["passed"] is False
            and null_failed == ["MEAN", "WIENER_UNG"]
        ),
        "common_mode_adversary_is_strong": common_mode_frc > 0.9,
        "phase0_verdict_is_kill": phase0["verdict"] == "STOP_REMOVE_RUST",
    }

    output = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": {
            "historical_commit": commit,
            "source_blobs": source_blobs,
            "source_blob_checks": blob_checks,
            "rerun_manifest": str(
                (RERUN / "rerun-manifest.json").relative_to(ROOT)
            ).replace("\\", "/"),
            "rerun_result": str(
                (RERUN / "s03_instrument.json").relative_to(ROOT)
            ).replace("\\", "/"),
        },
        "headline_reproduction": {
            "blur_recovery_min": min(recoveries),
            "blur_recovery_max": max(recoveries),
            "blur_recovery_count": len(recoveries),
            "filter_snr_ratios": filter_snr_ratios,
            "filter_max_fractional_move": max_filter_move,
            "filter_max_percent_move": 100.0 * max_filter_move,
            "naive_gradient_rms_gain": max_naive_rms,
            "naive_gradient_energy_ratio": max_naive_rms**2,
            "identity_min": identity_min,
            "identity_max": identity_max,
            "direct_identity_max_absolute_error": direct_identity_max_absolute_error,
            "direct_identity_global_scaled_error": direct_identity_scaled_error,
        },
        "source_semantics": source_semantics,
        "structural_probe": {
            "base_psig": base_stats[0],
            "base_pnoise": base_stats[1],
            "base_snr": base_stats[2],
            "base_frc": base_stats[3],
            "common_filter_results": scale_results,
            "interpretation": (
                "P_sig follows common-filter power and is sharpening-sensitive; "
                "normalized split SNR and ideal FRC cancel the same filter and "
                "are therefore also blind to post-render blur."
            ),
        },
        "failed_transfer_controls": {
            "historical_null_bar": null_bar,
            "historical_null_max_snr": null_max,
            "historical_null_failed_arms": null_failed,
            "common_mode_adversary_low_band_frc": common_mode_frc,
            "phase0_verdict": phase0["verdict"],
        },
        "ruling": {
            "P_sig": "REJECT_AS_M1: blur-responsive but common-gain/sharpening-sensitive",
            "R_SNR": (
                "AUXILIARY_ONLY: useful noise-efficiency coordinate, but blind "
                "to common post-render blur and not commissioned for self-tuning"
            ),
            "FRC": (
                "REJECT_AS_ABSOLUTE_ACUITY: ideal common-filter invariance is "
                "the same property as post-render-blur blindness"
            ),
            "half_difference": (
                "DIAGNOSTIC_ONLY: omits common-mode structure and can be driven "
                "to zero by averaging the two halves"
            ),
            "D8_as_M1": "NO_GO",
            "replacement": "J_TR information plus veto-only T_TR and U_TR",
        },
        "checks": checks,
    }
    RESULT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
