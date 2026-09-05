"""Verify M182 artifacts, semantic controls, and canonical report rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results.json"
REPORT = ROOT / "docs" / "research" / "M182-kernel-trade.md"
KERNELS = (
    "nearest",
    "bilinear",
    "catmull-rom",
    "clamped-catmull-rom",
    "lanczos2",
    "lanczos3",
)
LINEAR_KERNELS = tuple(k for k in KERNELS if k != "clamped-catmull-rom")
DISPLAY = {
    "nearest": "Nearest",
    "bilinear": "Bilinear",
    "catmull-rom": "CatmullRom",
    "clamped-catmull-rom": "ClampedCatmullRom",
    "lanczos2": "Lanczos2",
    "lanczos3": "Lanczos3",
}
SOURCES = {
    "crates/strehl-core/src/restore.rs": ROOT
    / "crates"
    / "strehl-core"
    / "src"
    / "restore.rs",
    "crates/strehl-core/src/align.rs": ROOT
    / "crates"
    / "strehl-core"
    / "src"
    / "align.rs",
    "crates/strehl-cli/src/align_cmd.rs": ROOT
    / "crates"
    / "strehl-cli"
    / "src"
    / "align_cmd.rs",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def expected_report_lines(result: dict) -> dict[str, str]:
    lines: dict[str, str] = {
        "frequency-convention": (
            "**CANONICAL FREQUENCY CONVENTION:** `f` is cycles per gather-plane sample; "
            "plane Nyquist is `0.5`; for a demosaiced output "
            "`f_output cycles/pixel = f_plane / 2`."
        ),
        "method-counts": (
            "**CANONICAL METHOD COUNTS:** raw-tap extrema use `1,000,001` phases; "
            "the complete tap-sum table uses `4,097`; shipping tap/overshoot probes use "
            "`131,072`; MTF uses `64` phases at `257` frequencies including DC and Nyquist."
        ),
        "commission-summary": (
            "**CANONICAL COMMISSION RESULT:** `74` checks passed; `74` planted defects "
            "caught; `0` missed; `2/2` inert arms survived; the sharpened positive "
            "control remained above baseline."
        ),
    }

    raw = result["raw_taps"]
    effective = result["shipping_effective_tap_probe"]
    for kernel in KERNELS:
        name = DISPLAY[kernel]
        if kernel == "clamped-catmull-rom":
            line = (
                f"| {name} | N/A (pre-clamp: CatmullRom) | N/A (pre-clamp: CatmullRom) | "
                "N/A (nonlinear) | N/A (nonlinear) | N/A (nonlinear) | "
                f"`{effective[kernel]['maximum_constant_dc_error']:.3e}` |"
            )
        else:
            r = raw[kernel]
            e = effective[kernel]
            line = (
                f"| {name} | `{r['most_negative_raw_tap']:+.9f}` | "
                f"`{r['maximum_raw_negative_mass']:.9f}` | "
                f"`[{r['raw_sum_min']:.12f}, {r['raw_sum_max']:.12f}]` | "
                f"`{e['most_negative_effective_delta_response']:+.9f}` | "
                f"`{e['maximum_effective_negative_mass']:.9f}` | "
                f"`{e['maximum_constant_dc_error']:.3e}` |"
            )
        lines[f"tap-{kernel}"] = line

    proof = {
        "nearest": "cannot: one-hot copy",
        "bilinear": "cannot: convex weights",
        "catmull-rom": "can: negative lobes",
        "clamped-catmull-rom": "cannot after destructive support clamp",
        "lanczos2": "can: negative lobes",
        "lanczos3": "can: negative lobes",
    }
    for kernel in KERNELS:
        row = result["overshoot"][kernel]
        step = row["step"]
        impulse = row["impulse"]
        lines[f"overshoot-{kernel}"] = (
            f"| {DISPLAY[kernel]} | {proof[kernel]} | "
            f"`{step['dn']:.6f} DN ({100 * step['fraction_of_1000_dn_range']:.6f}%)` | "
            f"`{impulse['dn']:.6f} DN "
            f"({100 * impulse['fraction_of_1000_dn_range']:.6f}%)` |"
        )

    for kernel in KERNELS:
        row = result["mtf"][kernel]
        cells = []
        for index in ("64", "128", "192"):
            point = row["selected"][index]
            cells.append(
                f"`{point['mtf']:.6f} / {point['relative_to_catmull_rom']:.6f}x`"
            )
        if row["mtf50_frequency_plane"] is None:
            mtf50 = "not reached"
        else:
            mtf50 = (
                f"`{row['mtf50_nyquist_fraction']:.6f} Nyq "
                f"({row['mtf50_frequency_plane']:.6f} c/plane; "
                f"{row['mtf50_relative_to_catmull_rom']:.6f}x CR)`"
            )
        if row["mtf10_frequency_plane"] is None:
            mtf10 = "not reached"
        else:
            mtf10 = (
                f"`{row['mtf10_nyquist_fraction']:.6f} Nyq "
                f"({row['mtf10_frequency_plane']:.6f} c/plane; "
                f"{row['mtf10_relative_to_catmull_rom']:.6f}x CR)`"
            )
        lines[f"mtf-{kernel}"] = (
            f"| {DISPLAY[kernel]} | {cells[0]} | {cells[1]} | {cells[2]} | "
            f"{mtf50} | {mtf10} |"
        )
        errors = [
            row["selected"][index]["rms_error_relative_to_unit_amplitude_truth"]
            for index in ("64", "128", "192")
        ]
        lines[f"fidelity-{kernel}"] = (
            f"| {DISPLAY[kernel]} | `{errors[0]:.6f}` | `{errors[1]:.6f}` | "
            f"`{errors[2]:.6f}` |"
        )

    condition = result["restoration"]["conditioning"]
    ideal = result["restoration"]["ideal_inverse"]
    for kernel in KERNELS:
        c = condition[kernel]
        if not c["restoration_supported"]:
            suffix = "N/A | N/A | N/A | N/A"
        else:
            inv = ideal[kernel]
            suffix = (
                f"`{c['maximum_inverse_gain_1d']:.6f}x / "
                f"{c['maximum_inverse_gain_2d_diagonal']:.6f}x` | "
                f"`{inv['noise_sd_ratio_1d']:.6f}x / {inv['noise_sd_ratio_2d']:.6f}x` | "
                f"`[{inv['minimum_realized_gain']:.6f}, "
                f"{inv['maximum_realized_gain']:.6f}]` | yes"
            )
        star = "*" if kernel == "clamped-catmull-rom" else ""
        lines[f"conditioning-{kernel}"] = (
            f"| {DISPLAY[kernel]} | "
            f"`{c['minimum_in_band_mtf_1d']:.6f}{star}` | "
            f"`{c['minimum_in_band_mtf_2d_diagonal']:.6f}{star}` | {suffix} |"
        )

    trade = result["restoration"]["bilinear_trade"]
    for key, row in trade.items():
        lambda_label = f"{row['lambda_noise_to_signal']:.3f}".rstrip("0").rstrip(".")
        if lambda_label == "":
            lambda_label = "0"
        noise = (
            "see R1"
            if row["lambda_noise_to_signal"] == 0.0
            else f"`{row['noise_sd_ratio_2d']:.6f}x`"
        )
        cells = []
        for index in ("64", "128", "192", "256"):
            point = row["selected"][index]
            cells.append(
                f"`{point['restored_mtf']:.6f} / "
                f"{point['relative_to_unrestored_catmull_rom']:.6f}x`"
            )
        lines[f"restore-trade-{key}"] = (
            f"| `{lambda_label}` | {noise} | {cells[0]} | {cells[1]} | "
            f"{cells[2]} | {cells[3]} | "
            f"`{100 * row['fraction_of_sampled_band_at_or_above_catmull_rom']:.4f}%` | "
            f"`{row['minimum_relative_to_catmull_rom']:.6f}x` |"
        )

    direction = result["controls"]["mtf_direction_control"]
    lines["control-mtf-direction"] = (
        "| MTF direction (`f=0.375`) | "
        f"`{direction['baseline']:.6f}` baseline; "
        f"`{direction['inert_dc_offset']:.6f}` after inert `+137 DN`; "
        f"`{direction['sharpened']:.6f}` sharpened; "
        f"`{direction['blurred']:.6f}` blurred | PASS |"
    )
    cross = result["controls"]["model_vs_shipping_mtf"]
    lines["control-model-shipping"] = (
        "| model vs shipping sampler | "
        f"max `|delta MTF| = {cross['maximum_absolute_error']:.3e}` "
        f"(bar `< {cross['tolerance']:.1e}`) | PASS |"
    )
    apply = result["controls"]["restore_application_noise_prediction"]
    lines["control-noise-application"] = (
        "| restoration noise application | "
        f"measured `{apply['measured_sd_ratio']:.6f}x`, tap-energy prediction "
        f"`{apply['predicted_sd_ratio_from_realized_taps']:.6f}x`, "
        f"`|delta|={apply['absolute_error']:.6f}` (bar `< {apply['tolerance']:.3f}`) | PASS |"
    )
    lines["control-null-arms"] = (
        "| structural/null arms | convex step+impulse zeros; high-noise restoration "
        "identity; production `restore::selftest` | PASS |"
    )

    for source, digest in result["source"]["files"].items():
        lines[f"source-{source}"] = f"| `{source}` | `{digest}` |"
    artifacts = result["artifacts"]
    lines["artifact-probe"] = (
        f"| `probe.tsv` | `{artifacts['probe_tsv_lines']}` lines | "
        f"`{artifacts['probe_tsv_sha256']}` |"
    )
    lines["artifact-mtf"] = (
        f"| `mtf-curve.csv` | `{artifacts['mtf_curve_lines']}` lines | "
        f"`{artifacts['mtf_curve_sha256']}` |"
    )
    lines["artifact-restoration"] = (
        f"| `restoration-curve.csv` | `{artifacts['restoration_curve_lines']}` lines | "
        f"`{artifacts['restoration_curve_sha256']}` |"
    )
    lines["artifact-tap-phases"] = (
        f"| `tap-phase-sums.csv` | `{artifacts['tap_phase_sums_lines']}` lines | "
        f"`{artifacts['tap_phase_sums_sha256']}` |"
    )
    return lines


def semantic_checks(result: dict) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def add(check_id: str, passed: bool, detail: str) -> None:
        checks.append((check_id, bool(passed), detail))

    add("S01-schema", result["schema"] == "m182-kernel-trade-v1", result["schema"])
    anchors = result["source"]["anchors"]
    add(
        "S02-source-anchors",
        len(anchors) == 12 and all(row["count"] == 1 for row in anchors),
        f"{len(anchors)} anchors",
    )
    add(
        "S03-source-hashes",
        all(sha256(SOURCES[name]) == digest for name, digest in result["source"]["files"].items()),
        "current source bytes match measurement manifest",
    )
    raw = result["raw_taps"]
    add(
        "S04-convex-raw-taps",
        all(
            raw[kernel]["most_negative_raw_tap"] == 0.0
            and raw[kernel]["maximum_raw_negative_mass"] == 0.0
            for kernel in ("nearest", "bilinear")
        ),
        "nearest and bilinear are non-negative",
    )
    add(
        "S05-negative-lobes",
        all(
            raw[kernel]["most_negative_raw_tap"] < 0.0
            and raw[kernel]["maximum_raw_negative_mass"] > 0.0
            for kernel in ("catmull-rom", "lanczos2", "lanczos3")
        )
        and not raw["clamped-catmull-rom"]["tap_defined"],
        "three linear negative-lobe kernels and nonlinear clamp",
    )
    effective = result["shipping_effective_tap_probe"]
    add(
        "S06-shipping-dc",
        all(effective[kernel]["maximum_constant_dc_error"] <= 1e-6 for kernel in KERNELS),
        "constant response within 1e-6",
    )
    overshoot = result["overshoot"]
    add(
        "S07-overshoot-discrimination",
        all(
            overshoot[kernel][plant]["dn"] == 0.0
            for kernel in ("nearest", "bilinear", "clamped-catmull-rom")
            for plant in ("step", "impulse")
        )
        and all(
            overshoot[kernel][plant]["dn"] > 0.0
            for kernel in ("catmull-rom", "lanczos2", "lanczos3")
            for plant in ("step", "impulse")
        ),
        "three exact-zero and three positive kernels",
    )
    wanted_support = {
        "nearest": True,
        "bilinear": True,
        "catmull-rom": True,
        "clamped-catmull-rom": False,
        "lanczos2": True,
        "lanczos3": True,
    }
    add(
        "S08-restoration-support",
        result["restoration_supported"] == wanted_support,
        str(result["restoration_supported"]),
    )
    cross = result["controls"]["model_vs_shipping_mtf"]
    add(
        "S09-model-shipping-crosscheck",
        cross["maximum_absolute_error"] < cross["tolerance"],
        f"{cross['maximum_absolute_error']:.3e}",
    )
    direction = result["controls"]["mtf_direction_control"]
    add(
        "S10-mtf-direction",
        abs(direction["inert_dc_offset"] - direction["baseline"]) < 1e-9
        and direction["sharpened"] > 1.2 * direction["baseline"]
        and direction["blurred"] < 0.8 * direction["baseline"],
        "inert unchanged, sharpen up, blur down",
    )
    apply = result["controls"]["restore_application_noise_prediction"]
    add(
        "S11-restoration-application",
        abs(
            apply["measured_sd_ratio"]
            - apply["predicted_sd_ratio_from_realized_taps"]
        )
        < apply["tolerance"],
        f"error {apply['absolute_error']:.6f}",
    )
    high = result["restoration"]["high_noise_null"]
    add(
        "S12-high-noise-identity",
        all(
            row["noise_sd_ratio_2d"] == 1.0
            and row["minimum_realized_gain"] == 1.0
            and row["maximum_realized_gain"] == 1.0
            and row["half_taps"] == [1.0, 0.0, 0.0, 0.0, 0.0]
            for row in high.values()
        ),
        "all supported kernels identity",
    )
    condition = result["restoration"]["conditioning"]
    add(
        "S13-conditioning-positive",
        all(
            condition[kernel]["minimum_in_band_mtf_1d"] > 0.0
            for kernel in LINEAR_KERNELS
        )
        and abs(condition["bilinear"]["minimum_in_band_mtf_1d"] - 0.5) < 1e-12,
        "no supported kernel has an in-band zero",
    )
    convention = result["frequency_convention"]
    add(
        "S14-frequency-convention",
        convention["primary"] == "cycles per gather-plane sample"
        and convention["plane_nyquist"] == 0.5
        and convention["demosaiced_output_conversion"] == "divide plane frequency by 2",
        str(convention),
    )
    methods = result["methods"]
    add(
        "S15-method-counts",
        methods["raw_tap_sweep_phases"] == 1_000_001
        and methods["reported_tap_sum_curve_phases"] == 4_097
        and methods["shipping_tap_probe_phases"] == 131_072
        and methods["mtf_phase_average_phases"] == 64
        and methods["mtf_curve_points_inclusive_of_dc_and_nyquist"] == 257,
        str(methods),
    )
    artifacts = result["artifacts"]
    add(
        "S16-probe-artifact",
        sha256(HERE / "probe.tsv") == artifacts["probe_tsv_sha256"]
        and len((HERE / "probe.tsv").read_text(encoding="utf-8").splitlines())
        == artifacts["probe_tsv_lines"],
        "probe hash and line count",
    )
    add(
        "S17-mtf-artifact",
        sha256(HERE / artifacts["mtf_curve"]) == artifacts["mtf_curve_sha256"]
        and len((HERE / artifacts["mtf_curve"]).read_text(encoding="utf-8").splitlines())
        == artifacts["mtf_curve_lines"],
        "MTF curve hash and line count",
    )
    add(
        "S18-restoration-artifact",
        sha256(HERE / artifacts["restoration_curve"])
        == artifacts["restoration_curve_sha256"]
        and len(
            (HERE / artifacts["restoration_curve"]).read_text(encoding="utf-8").splitlines()
        )
        == artifacts["restoration_curve_lines"],
        "restoration curve hash and line count",
    )
    add(
        "S19-tap-phase-artifact",
        sha256(HERE / artifacts["tap_phase_sums"]) == artifacts["tap_phase_sums_sha256"]
        and len(
            (HERE / artifacts["tap_phase_sums"]).read_text(encoding="utf-8").splitlines()
        )
        == artifacts["tap_phase_sums_lines"],
        "tap-phase curve hash and line count",
    )
    ideal_bilinear = result["restoration"]["ideal_inverse"]["bilinear"]
    add(
        "S20-inverse-has-noise-cost",
        ideal_bilinear["noise_sd_ratio_2d"] > 1.8
        and ideal_bilinear["maximum_realized_gain"] > 1.9,
        "bilinear inverse is potent and non-free",
    )
    ideal_high = ideal_bilinear["selected"]["192"]["restored_mtf"]
    catmull_high = result["mtf"]["catmull-rom"]["selected"]["192"]["mtf"]
    add(
        "S21-restoration-recovers-high-band",
        ideal_high > catmull_high,
        f"{ideal_high:.6f} vs {catmull_high:.6f}",
    )
    add(
        "S22-clamped-is-not-an-otf",
        result["mtf"]["clamped-catmull-rom"]["method"].startswith("shipping sampler")
        and not result["restoration"]["ideal_inverse"]["clamped-catmull-rom"][
            "supported"
        ],
        result["mtf"]["clamped-catmull-rom"]["method"],
    )
    return checks


def audit(result: dict, report_text: str) -> tuple[list[str], dict[str, str]]:
    failures = [check_id for check_id, passed, _ in semantic_checks(result) if not passed]
    lines = expected_report_lines(result)
    report_full_lines = report_text.splitlines()
    for line_id, line in lines.items():
        count = report_full_lines.count(line)
        if count != 1:
            failures.append(f"R-{line_id}")
    return failures, lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--print-lines",
        action="store_true",
        help="print canonical report lines instead of requiring the report",
    )
    args = parser.parse_args()
    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    lines = expected_report_lines(result)
    if args.print_lines:
        for line_id, line in lines.items():
            print(f"[{line_id}] {line}")
        print(f"{len(lines)} canonical report checks; {len(semantic_checks(result))} semantic checks")
        return 0
    report = REPORT.read_text(encoding="utf-8")
    failures, _ = audit(result, report)
    total = len(lines) + len(semantic_checks(result))
    if failures:
        for failure in failures:
            print(f"BAD  {failure}")
        print(f"verify: FAILED ({len(failures)} failures across {total} checks)")
        return 1
    print(f"verify: PASS ({total} checks: {len(lines)} report anchors + 22 semantic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
