"""Adjudicate the triage's D8 premise from rerun and external evidence."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"
M115 = ROOT / "docs" / "research" / "M115-deconv-headroom.md"
M41 = ROOT / "docs" / "research" / "M41-r3-kill-measured.md"
TRIAGE = ROOT / "docs" / "proposals" / "2026-09-phase0-triage.md"
COMMIT = "77c8d5e9ac6ed342cdc841e541c98f87e5c743f8"


def historical_source(name: str) -> str:
    spec = f"{COMMIT}:experiments/M115-deconv-headroom/src/{name}"
    return subprocess.check_output(
        ["git", "show", spec], cwd=ROOT, text=True, encoding="utf-8"
    )


def main() -> int:
    manifest = json.loads(
        (OUT / "m115-rerun" / "rerun-manifest.json").read_text(encoding="utf-8")
    )
    instrument = json.loads(
        (OUT / "m115-rerun" / "s03_instrument.json").read_text(encoding="utf-8")
    )
    prototype = json.loads((OUT / "commission.json").read_text(encoding="utf-8"))
    m115_text = M115.read_text(encoding="utf-8")
    m41_text = M41.read_text(encoding="utf-8")
    triage_text = TRIAGE.read_text(encoding="utf-8")
    source = historical_source("m115lib.py")

    extracted = manifest["extracted"]
    expected_filter = {
        "flat x3": 1.0000,
        "unsharp 1+2f": 0.9986,
        "unsharp 1+6f": 0.9980,
        "inverse taper": 0.9946,
    }
    numeric_checks = {
        "blur_min_0.9938": round(float(extracted["blur_recovery_min"]), 4) == 0.9938,
        "blur_max_0.9974": round(float(extracted["blur_recovery_max"]), 4) == 0.9974,
        "blur_count_8": extracted["blur_recovery_count"] == 8,
        "blur_monotone": extracted["blur_monotone"] is True,
        "filter_readings": all(
            round(float(extracted["filter_snr_ratios"][name]), 4) == expected
            for name, expected in expected_filter.items()
        ),
        "identity_rounds_1.0000": (
            round(float(extracted["identity_min"]), 4) == 1.0
            and round(float(extracted["identity_max"]), 4) == 1.0
        ),
        "published_literals_present": all(
            literal in m115_text
            for literal in (
                "`[0.9938, 0.9974]`",
                "at most **0.54 %**",
                "= **1.0000** on every arm",
            )
        ),
    }

    common_mode_match = re.search(
        r"COMMON_MODE low_band=([\d.]+)", prototype["readings"]["common_mode"]
    )
    if common_mode_match is None:
        raise RuntimeError("prototype common-mode reading is missing")
    common_mode_frc = float(common_mode_match.group(1))

    algebraic_identity = all(
        literal in source
        for literal in (
            "Ps = rb.cross(oa, ob)",
            "Pn = 0.5 * rb.power(oa - ob)",
            "Pa = 0.5 * (rb.power(oa) + rb.power(ob))",
        )
    )
    later_withdrawal = all(
        literal in m41_text
        for literal in (
            "9 of 12 run-of-record detail-ROI crossings are this constant",
            "32 settings, 0 of which are uncensored",
            "The FRC 1/7 crossing is withdrawn",
            "recovery of a planted blur scales as (1 - rho)",
        )
    )
    triage_false_branch = (
        "**If FALSE:** No current merge code changes." in triage_text
        and "Keep the split instrument offline in Python" in triage_text
    )
    summary_controls = sorted(instrument["summary"])
    transfer = {
        "historical_null_passed": bool(instrument["C1p"]["passed"]),
        "historical_null_failed_arms": extracted["null_failed_arms"],
        "common_mode_adversary_low_band_frc": common_mode_frc,
        "common_mode_adversary_violates_null": common_mode_frc > 0.08,
        "power_identity_is_algebraic": algebraic_identity,
        "historical_control_summary": summary_controls,
        "data_dependent_tuning_plant_present": False,
        "later_frc_withdrawal_found": later_withdrawal,
        "triage_false_branch_found": triage_false_branch,
    }

    stop_reasons = []
    if not all(numeric_checks.values()):
        stop_reasons.append("historical headline did not numerically reproduce")
    if not transfer["historical_null_passed"]:
        stop_reasons.append("historical split null failed on two arms")
    if transfer["common_mode_adversary_violates_null"]:
        stop_reasons.append("common-mode structure reads as strong correlated signal")
    if transfer["power_identity_is_algebraic"]:
        stop_reasons.append("the 1.0000 power identity is algebraic, not a control")
    if not transfer["data_dependent_tuning_plant_present"]:
        stop_reasons.append("no plant transfers to a data-dependent per-stack tuner")
    if transfer["later_frc_withdrawal_found"]:
        stop_reasons.append("later commissioned work withdrew the numeric FRC crossing")
    if not transfer["triage_false_branch_found"]:
        raise RuntimeError("could not locate the triage's binding FALSE branch")

    result = {
        "status": "AUDITED",
        "historical_numeric_reproduction": {
            "passed": all(numeric_checks.values()),
            "checks": numeric_checks,
            "measured": extracted,
        },
        "transfer_and_meaning": transfer,
        "verdict": "STOP_REMOVE_RUST" if stop_reasons else "PASS_BUILD",
        "stop_reasons": stop_reasons,
        "interpretation": (
            "Numerical reproduction is necessary but does not establish that "
            "cross-half correlation is scene detail or that the objective can tune itself."
        ),
    }
    destination = OUT / "postupdate-audit.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "STOP_REMOVE_RUST" else 1


if __name__ == "__main__":
    raise SystemExit(main())
