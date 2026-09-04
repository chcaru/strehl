"""Verify M159's corrected interpretation, provenance, and frozen arithmetic."""

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

    m135 = collapse_markdown(
        text(REPO / "docs" / "research" / "M135-detail-instrument.md")
    )
    unique(
        m135,
        "Therefore a statistic exactly invariant to a family of common post-noise "
        "linear operators cannot distinguish any member of that family from identity.",
        "M135 common-postfilter theorem",
    )
    unique(
        m135,
        "The best available route is `J_TR` plus veto-only `T_TR` and `U_TR`, "
        "measured against an independently captured, higher-sampling, unpredictable "
        "reference.",
        "M135 replacement architecture",
    )
    unique(
        m135,
        "**No scored M1 number is available without a new capture.**",
        "M135 missing scored capture",
    )
    checks.append("M135's impossibility result and physical blocker are pinned")

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
    close(
        commissioning["specificity_challenge"]["blurred_over_unblurred"],
        0.5712148772282098,
        1e-12,
        "blur specificity challenge",
    )
    if commissioning["specificity_challenge"]["blurred_over_unblurred"] >= 1.0:
        raise AssertionError("blur challenge no longer demonstrates the confound")
    if "reports output residual only" not in commissioning["specificity_challenge"][
        "interpretation"
    ]:
        raise AssertionError("specificity interpretation no longer limits claim scope")
    checks.append(
        "null, degradation, improvement, tone, and blur-specificity controls are pinned"
    )

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
    unique(
        report_normalized,
        "**CORRECTION TO `249f77db`: THE OWNER'S COMPARATIVE “STRICTLY LOWER "
        "NOISE” CLAUSE CANNOT BE CLAIMED TODAY.**",
        "corrected report verdict",
    )
    unique(
        report_normalized,
        "On the twelve frozen coffee-paper ROIs, DELIVER-V6's fractional box9 "
        "residual is `1.515208×` the fork's median site value, with all twelve "
        "site ratios above one.",
        "coffee headline",
    )
    unique(
        report_normalized,
        "The answer depends on the noun. A **residual** claim is available today. "
        "A positive comparative **noise** claim is not.",
        "residual-versus-noise distinction",
    )
    unique(
        report_normalized,
        "M158 already completed the document-governance audit.",
        "M158 governance deferral",
    )
    unique(
        report_normalized,
        "**No.** Detail is one gate among several.",
        "J_TR not sole gate",
    )
    checks.append("report carries the corrected verdict, number, and J_TR ruling")

    VERIFY_RESULTS.write_text(
        json.dumps({"status": "PASS", "checks": checks}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: {len(checks)} checks; wrote {VERIFY_RESULTS}")


if __name__ == "__main__":
    main()
