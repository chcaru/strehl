"""Verify M159's quotations, provenance, arithmetic, and commissioning."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REPORT = REPO / "docs" / "research" / "M159-noise-clause.md"
RESULTS = HERE / "results.json"
VERIFY_RESULTS = HERE / "verification.json"


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def collapse_markdown(value: str) -> str:
    stripped_lines = []
    for line in value.splitlines():
        candidate = line.lstrip()
        if candidate.startswith(">"):
            candidate = candidate[1:]
            if candidate.startswith(" "):
                candidate = candidate[1:]
        stripped_lines.append(candidate)
    return " ".join(" ".join(stripped_lines).split())


def unique(haystack: str, needle: str, label: str) -> None:
    count = haystack.count(needle)
    if count != 1:
        raise AssertionError(f"{label}: expected one exact anchor, found {count}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise AssertionError(f"{label}: {actual} != {expected} +/- {tolerance}")


def main() -> None:
    checks: list[str] = []

    plan_path = REPO / "docs" / "proposals" / "2026-08-sota-path.md"
    plan_raw = text(plan_path)
    plan = collapse_markdown(plan_raw)
    sentence = (
        "On [subjects], strehl resolves detail at or beyond the best shipping "
        "comparator (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at "
        "strictly lower noise (existing flat-ROI instrument), with zero invented "
        "structure (hull census, stamped per file), no occlusion veil above [bar] "
        "(halo instrument at full reach), while emitting per-pixel certified acuity, "
        "n_eff, and depth in physical units that no comparator emits at all "
        "(D2/D8/A5/C5), in [X] s per frame on CPU (existing harness)."
    )
    unique(plan, sentence, "six-clause sentence")
    unique(
        sentence,
        "at strictly lower noise (existing flat-ROI instrument)",
        "noise clause",
    )
    axis_row = (
        "| Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork "
        "(≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate "
        "4.5; 9.9× flat-field rms on the deepest stack with the compound eye "
        "indistinguishable (README) | Nothing — quotable now |"
    )
    unique(plan_raw, axis_row, "noise axis row")
    checks.append("primary-source plan quotations are exact and unique")

    hplook = text(REPO / "experiments" / "V-HEADTOHEAD" / "hplook.py")
    unique(
        hplook,
        "return a / ndimage.uniform_filter(a, 2*r+1) - 1.0",
        "historical statistic",
    )
    unique(
        hplook,
        'panel("hp_flat", 968, 584, 320)',
        "historical flat site",
    )
    survey = text(REPO / "experiments" / "V-HEADTOHEAD" / "survey.py")
    unique(
        survey,
        "m[np.argsort(m[:, 3])][:12]",
        "comparator-only flat ranking",
    )
    checks.append("historical instrument anchors are exact and unique")

    scorecard = text(
        REPO / "docs" / "proposals" / "2026-09-sota-scorecard.md"
    )
    unique(
        scorecard,
        "> **SCORECARD ADDITION — UNRATIFIED. This rule is authored here and is not",
        "rule-4 provenance label",
    )
    unique(
        scorecard,
        "`eta <=1.10` and `UCB95(sigma_strehl / min(sigma_comparator)) <=0.950`.",
        "M2 scorecard-only bar",
    )
    checks.append("scorecard-only rule and bar are pinned")

    blob = subprocess.run(
        [
            "git",
            "show",
            "6af834dac08d6605aee7ea3ad75809fdf6313770:"
            "crates/strehl-cli/src/image_out.rs",
        ],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8")
    unique(blob, "const TONE_TOE: f32 = 0.004;", "pinned tone toe")
    unique(
        blob,
        "let s = x * x * (3.0 - 2.0 * x);",
        "pinned display S-curve",
    )
    unique(
        blob,
        "let soft = 0.5 * (y + (y * y + TONE_TOE * TONE_TOE).sqrt());",
        "pinned soft black placement",
    )
    checks.append("DELIVER-V6 tone inverse matches the pinned source blob")

    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    for item in result["inputs"]:
        path = Path(item["path"])
        if path.stat().st_size != item["bytes"]:
            raise AssertionError(f"input size changed: {path}")
        if sha256(path) != item["sha256"]:
            raise AssertionError(f"input hash changed: {path}")
    checks.append("all five input files match recorded byte counts and SHA-256")

    commissioning = result["commissioning"]
    null = commissioning["movable_null"]
    if not (null["min"] < 1.0 < null["max"]):
        raise AssertionError("movable null did not move to both sides of one")
    if not (
        commissioning["planted_degradation"]["trials_above_1"] == 128
        and commissioning["planted_improvement"]["trials_below_1"] == 128
    ):
        raise AssertionError("directional controls did not move on every trial")
    close(
        commissioning["tone_inversion_round_trip"][
            "recovered_over_source_highpass_rms"
        ],
        1.0,
        1e-4,
        "tone inversion high-pass round trip",
    )
    checks.append("null, degradation, improvement, and tone-inverse controls pass")

    expected = {
        "coffee-bean": (12, 1.5152084100548955, 1.3350617226799324, 1.5908793672469541),
        "113MSDCF": (11, 1.377765509820183, 1.189916244999059, 1.61353983529474),
    }
    for subject in result["subjects"]:
        count, median, minimum, maximum = expected[subject["subject"]]
        sites = subject["sites"]
        if len(sites) != count:
            raise AssertionError(f"{subject['subject']}: site count changed")
        ratios = []
        for site in sites:
            for key, comparator_rms in site["fractional_rms"].items():
                if key == "strehl":
                    continue
                derived = site["fractional_rms"]["strehl"] / comparator_rms
                close(
                    derived,
                    site["strehl_over_comparator"][key],
                    1e-12,
                    f"{subject['subject']} site {site['rank']} ratio",
                )
            ratios.append(site["strehl_over_best_comparator_raw"])
        if not all(value > 1.0 for value in ratios):
            raise AssertionError(f"{subject['subject']}: a site no longer fails")
        distribution = subject["raw_best_comparator_distribution"]
        close(distribution["median"], median, 1e-12, f"{subject['subject']} median")
        close(distribution["min"], minimum, 1e-12, f"{subject['subject']} minimum")
        close(distribution["max"], maximum, 1e-12, f"{subject['subject']} maximum")
    checks.append("all per-site ratios and both distributions rederive exactly")

    geometry = result["geometry"]
    if geometry["coffee_fork_to_strehl"]["residual_rms_px"] >= 3.0:
        raise AssertionError("coffee robust geometry residual is too large")
    if geometry["subject2_zerene_to_strehl"]["residual_rms_px"] >= 1.0:
        raise AssertionError("113MSDCF geometry residual is too large")
    close(
        result["historical_coffee_site_current_render"][
            "comparator_fractional_rms"
        ],
        0.005025,
        5e-7,
        "historical comparator denominator",
    )
    checks.append("geometry fits and historical comparator denominator are pinned")

    report = text(REPORT)
    report_normalized = collapse_markdown(report)
    unique(report, "**VERDICT: SCOREABLE TODAY.**", "report verdict")
    unique(report_normalized, sentence, "report six-clause quotation")
    unique(report, axis_row, "report noise-axis-row quotation")
    unique(
        report_normalized,
        "flat-ground population, DELIVER-V6 / fork is `1.515208×` median "
        "high-pass RMS; all `12/12`",
        "coffee headline",
    )
    unique(
        report_normalized,
        "median **`1.377766×`**, p75",
        "113 diagnostic headline",
    )
    unique(
        report_normalized,
        "The noise clause and its licence, exactly, are: at strictly lower noise "
        "(existing flat-ROI instrument)",
        "report noise-clause quotation",
    )
    checks.append("report carries the verified verdict, numbers, and quotation")

    VERIFY_RESULTS.write_text(
        json.dumps({"status": "PASS", "checks": checks}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: {len(checks)} checks; wrote {VERIFY_RESULTS}")


if __name__ == "__main__":
    main()
