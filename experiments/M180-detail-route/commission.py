from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = HERE / "work"
OUTPUT = HERE / "evidence" / "commission.json"
BASELINE_VERDICT = "UNDECIDED_REFERENCE_ROUTE_OPEN_PHYSICAL_UNMEASURED"


SOURCES = {
    "fixture": HERE / "evidence" / "model-fixtures.json",
    "m164_report": ROOT / "docs" / "research" / "M164-m2-repair.md",
    "m168_report": ROOT / "docs" / "research" / "M168-m2-identifiability.md",
    "m135_commission": (
        ROOT / "experiments" / "M135-detail-instrument" / "commission.json"
    ),
    "m135_results": (
        ROOT / "experiments" / "M135-detail-instrument" / "RESULTS.md"
    ),
    "dominance_commission": (
        ROOT
        / "experiments"
        / "M164-reference-dominance"
        / "commission.json"
    ),
    "m167_admission": (
        ROOT
        / "experiments"
        / "M167-detail-battery"
        / "admission-results.json"
    ),
    "m167_preregistration": (
        ROOT
        / "experiments"
        / "M167-detail-battery"
        / "PREREGISTRATION.md"
    ),
    "archive_report": (
        ROOT / "docs" / "research" / "M168-cheap-reference-feasibility.md"
    ),
    "slanted_report": (
        ROOT / "docs" / "research" / "M-PHASE0-SLANTEDGE.md"
    ),
}


@dataclass(frozen=True)
class Mutation:
    label: str
    target_check: str
    source: str
    old_line: str
    new_line: str


MUTATIONS = (
    Mutation(
        "collision-operator",
        "collision_operator_valid",
        "fixture",
        '  "impulse_center": 1.0,',
        '  "impulse_center": 0.0,',
    ),
    Mutation(
        "collision-labels",
        "collision_labels_opposite",
        "fixture",
        '  "improvement_label": "prefer_B",',
        '  "improvement_label": "prefer_A",',
    ),
    Mutation(
        "featureless-blindness",
        "featureless_blur_usm_blind",
        "fixture",
        '  "featureless_profile": [0.5, 0.5, 0.5, 0.5, 0.5],',
        '  "featureless_profile": [0.5, 0.5, 0.5, 0.5, 0.6],',
    ),
    Mutation(
        "prior-marginal",
        "marginal_prior_collision",
        "fixture",
        '  "hallucination_signal_probability": 0.5,',
        '  "hallucination_signal_probability": 0.6,',
    ),
    Mutation(
        "reference-link",
        "reference_breaks_collision",
        "fixture",
        '  "reference_link": "same_latent",',
        '  "reference_link": "independent",',
    ),
    Mutation(
        "m164-qualifier",
        "m164_output_only_scope",
        "m164_report",
        "worlds. It cannot reject `B` in the first and reward `B` in the second without",
        "worlds. It can always reject `B` in the first and reward `B` in the second without",
    ),
    Mutation(
        "m168-scope",
        "m168_distribution_free_scope",
        "m168_report",
        (
            "> **WARNING — INFERRED BY READING.** The distribution-free "
            "impossibility is sound, but it must not be shortened to “no "
            "reference-free metric can ever ground the claim.” The words "
            "**“without an assumption or observation outside those outputs” "
            "are load-bearing and may not be dropped.** A prior, restricted "
            "scene model, calibrated generative model, reference, or "
            "controlled target can add identifying information; any resulting "
            "claim inherits that assumption and its scope."
        ),
        (
            "> **WARNING — INFERRED BY READING.** The universal impossibility "
            "is sound, but it must not be shortened to “no reference-free "
            "metric can ever ground the claim.” The words **“without an "
            "assumption or observation outside those outputs” are "
            "load-bearing and may not be dropped.** A prior, restricted scene "
            "model, calibrated generative model, reference, or controlled "
            "target can add identifying information; any resulting claim "
            "inherits that assumption and its scope."
        ),
    ),
    Mutation(
        "m135-estimator-status",
        "m135_estimator_commissioned",
        "m135_commission",
        '  "status": "PASS",',
        '  "status": "FAIL",',
    ),
    Mutation(
        "blur-wrong-sign",
        "m135_blur_defect_direction",
        "m135_commission",
        '      "q95": 0.6315114151966404,',
        '      "q95": 1.0315114151966404,',
    ),
    Mutation(
        "improvement-suppressed",
        "m135_improvement_direction",
        "m135_commission",
        '      "q05": 1.24184002221614,',
        '      "q05": 0.94184002221614,',
    ),
    Mutation(
        "usm-rewarded",
        "m135_usm_not_rewarded",
        "m135_commission",
        '      "maximum": 1.0000000000000007',
        '      "maximum": 1.0200000000000007',
    ),
    Mutation(
        "postblur-transfer-hidden",
        "m135_postblur_transfer_veto",
        "m135_commission",
        '      "q95": 0.687470374432892,',
        '      "q95": 1.0,',
    ),
    Mutation(
        "averaging-promoted",
        "m135_averaging_veto",
        "m135_commission",
        '  "averaging_promotions": 0,',
        '  "averaging_promotions": 1,',
    ),
    Mutation(
        "flat-common-mode-missed",
        "m135_flat_common_mode",
        "m135_commission",
        '    "FLAT_NULL_FAILED": 128',
        '    "FLAT_NULL_FAILED": 127',
    ),
    Mutation(
        "dominance-legitimate-rejected",
        "dominance_legitimate_moves",
        "dominance_commission",
        '    "C3_legitimate_case_is_admitted": true,',
        '    "C3_legitimate_case_is_admitted": false,',
    ),
    Mutation(
        "dominance-compensation",
        "dominance_no_compensation",
        "dominance_commission",
        '    "C8_strong_cells_do_not_compensate": true,',
        '    "C8_strong_cells_do_not_compensate": false,',
    ),
    Mutation(
        "dominance-common-mode-missed",
        "dominance_improvement_shaped_defect",
        "dominance_commission",
        '    "C13_charged_improvement_shaped_case_is_rejected": true,',
        '    "C13_charged_improvement_shaped_case_is_rejected": false,',
    ),
    Mutation(
        "m167-canary-admitted",
        "m167_canary_bites",
        "m167_admission",
        '  "admission_verdict": "REJECTED_BY_BLINDED_ADMISSION",',
        '  "admission_verdict": "ADMITTED",',
    ),
    Mutation(
        "m167-a6-forged",
        "m167_a6_fail_closed",
        "m167_admission",
        '    "A6_capability_sandbox": false',
        '    "A6_capability_sandbox": true',
    ),
    Mutation(
        "m167-schema-assumed",
        "m167_reference_schema_pending",
        "m167_preregistration",
        "- a future explicitly preregistered reference-bearing mode.",
        "- an already available reference-bearing mode.",
    ),
    Mutation(
        "archive-route-forged",
        "archive_route_closed",
        "archive_report",
        (
            "Status: **NO ARCHIVE-ONLY ROUTE; M135 ABSENCE FINDING "
            "INDEPENDENTLY CONFIRMED**"
        ),
        "Status: **ARCHIVE-ONLY ROUTE AVAILABLE**",
    ),
    Mutation(
        "pchip-overclaimed",
        "pchip_is_enabler_only",
        "slanted_report",
        (
            "Independent 33-step PCHIP linearisation is the one clean success: "
            "V3–V5 move"
        ),
        (
            "Independent 33-step PCHIP linearisation is a complete detail "
            "instrument: V3–V5 move"
        ),
    ),
    Mutation(
        "physical-chain-forged",
        "physical_route_uncommissioned",
        "m135_results",
        (
            "Status: **PASS at estimator level; physical capture path not "
            "commissioned**"
        ),
        "Status: **PASS; physical capture path commissioned**",
    ),
)


INERT = Mutation(
    "inert-note",
    "",
    "fixture",
    '  "inert_note": "baseline"',
    '  "inert_note": "changed"',
)


def replace_unique_line(
    source: Path,
    destination: Path,
    old_line: str,
    new_line: str,
) -> int:
    lines = source.read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if line == old_line]
    if len(matches) != 1:
        raise RuntimeError(
            f"{source}: mutation anchor occurred {len(matches)} times: "
            f"{old_line!r}"
        )
    lines[matches[0]] = new_line
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return len(matches)


def run_verifier(overrides: dict[str, Path] | None = None) -> tuple[int, dict]:
    command = [sys.executable, "-B", str(HERE / "verify.py")]
    for source, path in (overrides or {}).items():
        command.extend([f"--{source.replace('_', '-')}", str(path)])
    process = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"verify.py emitted invalid JSON; rc={process.returncode}; "
            f"stdout={process.stdout!r}; stderr={process.stderr!r}"
        ) from exc
    return process.returncode, result


def run_mutation(mutation: Mutation) -> dict[str, Any]:
    case_dir = WORK / mutation.label
    destination = case_dir / SOURCES[mutation.source].name
    planted = replace_unique_line(
        SOURCES[mutation.source],
        destination,
        mutation.old_line,
        mutation.new_line,
    )
    returncode, result = run_verifier({mutation.source: destination})
    checks = result.get("checks", {})
    target_false = checks.get(mutation.target_check) is False
    killed = (
        planted == 1
        and returncode != 0
        and target_false
        and result.get("verdict") != BASELINE_VERDICT
    )
    return {
        "label": mutation.label,
        "target_check": mutation.target_check,
        "source": mutation.source,
        "mutation_anchor_matches": planted,
        "verify_returncode": returncode,
        "target_check_false": target_false,
        "failed_checks": [
            name for name, value in checks.items() if value is False
        ],
        "verdict": result.get("verdict"),
        "killed": killed,
    }


def run_inert() -> dict[str, Any]:
    case_dir = WORK / INERT.label
    destination = case_dir / SOURCES[INERT.source].name
    planted = replace_unique_line(
        SOURCES[INERT.source],
        destination,
        INERT.old_line,
        INERT.new_line,
    )
    returncode, result = run_verifier({INERT.source: destination})
    checks = result.get("checks", {})
    survived = (
        planted == 1
        and returncode == 0
        and result.get("verdict") == BASELINE_VERDICT
        and len(checks) == 23
        and all(value is True for value in checks.values())
    )
    return {
        "label": INERT.label,
        "source": INERT.source,
        "mutation_anchor_matches": planted,
        "verify_returncode": returncode,
        "verdict": result.get("verdict"),
        "checks_run": len(checks),
        "checks_passed": sum(value is True for value in checks.values()),
        "survived": survived,
    }


def main() -> int:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    baseline_returncode, baseline = run_verifier()
    baseline_green = (
        baseline_returncode == 0
        and baseline.get("verdict") == BASELINE_VERDICT
        and baseline.get("counts", {}).get("checks_run") == 23
        and baseline.get("counts", {}).get("checks_failed") == 0
    )

    mutation_results = [run_mutation(mutation) for mutation in MUTATIONS]
    inert_result = run_inert()
    mutations_killed = sum(row["killed"] for row in mutation_results)
    status = (
        "PASS"
        if baseline_green
        and mutations_killed == len(MUTATIONS)
        and inert_result["survived"]
        else "FAIL"
    )
    result = {
        "schema": 1,
        "status": status,
        "baseline": {
            "returncode": baseline_returncode,
            "verdict": baseline.get("verdict"),
            "checks_run": baseline.get("counts", {}).get("checks_run"),
            "checks_passed": baseline.get("counts", {}).get("checks_passed"),
            "green": baseline_green,
        },
        "counts": {
            "checks_run": 23,
            "mutations_planted": len(MUTATIONS),
            "mutations_killed": mutations_killed,
            "inert_controls_run": 1,
            "inert_controls_survived": int(inert_result["survived"]),
        },
        "mutations": mutation_results,
        "inert_control": inert_result,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    OUTPUT.write_text(encoded, encoding="utf-8", newline="\n")
    sys.stdout.write(encoded)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
