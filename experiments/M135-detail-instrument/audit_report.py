"""Structural and source-citation audit for the M135 report."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "research" / "M135-detail-instrument.md"
HERE = Path(__file__).resolve().parent


def normalize(text: str) -> str:
    lines = [re.sub(r"^\s*>\s?", "", line) for line in text.splitlines()]
    return " ".join(" ".join(lines).split())


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def canonical_json_sha256(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    report = REPORT.read_text(encoding="utf-8")
    findings = []
    commission = json.loads(
        (Path(__file__).resolve().parent / "commission.json").read_text(
            encoding="utf-8"
        )
    )
    d8_audit = json.loads(
        (Path(__file__).resolve().parent / "d8-audit.json").read_text(
            encoding="utf-8"
        )
    )
    flat_verification = json.loads(
        (Path(__file__).resolve().parent / "flat-verification.json").read_text(
            encoding="utf-8"
        )
    )
    comparison_verification = json.loads(
        (HERE / "comparison-verification.json").read_text(encoding="utf-8")
    )
    comparison_manifest = json.loads(
        (HERE / "comparison-rule-manifest.json").read_text(encoding="utf-8")
    )
    comparison_contract = json.loads(
        (HERE / "comparison-contract.json").read_text(encoding="utf-8")
    )
    comparison_binding = json.loads(
        (HERE / "comparison-binding.json").read_text(encoding="utf-8")
    )
    adapter_verification = json.loads(
        (HERE / "m138-adapter-verification.json").read_text(encoding="utf-8")
    )
    adapter_pre_m149_verification = json.loads(
        (HERE / "m138-adapter-verification-run5-pre-m149.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_threshold_verification = json.loads(
        (
            HERE / "m138-adapter-verification-run6-pre-threshold-fix.json"
        ).read_text(encoding="utf-8")
    )
    adapter_failed_verification = json.loads(
        (HERE / "m138-adapter-verification-run2-failed.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_bootstrap_verification = json.loads(
        (HERE / "m138-adapter-verification-run3-pre-bootstrap.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_m149_bootstrap = json.loads(
        (HERE / "m138-adapter-bootstrap-verification-run2-pre-m149.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_source_verification = json.loads(
        (HERE / "m138-adapter-verification-run4-pre-source-loader.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_source_bootstrap = json.loads(
        (
            HERE
            / "m138-adapter-bootstrap-verification-run1-pre-source-loader.json"
        ).read_text(encoding="utf-8")
    )
    adapter_manifest = json.loads(
        (HERE / "m138-adapter-result-manifest.json").read_text(encoding="utf-8")
    )
    adapter_contract = json.loads(
        (HERE / "m138-adapter-contract.json").read_text(encoding="utf-8")
    )
    adapter_bundle = json.loads(
        (HERE / "m138-checker-bundle.json").read_text(encoding="utf-8")
    )
    adapter_description = json.loads(
        (HERE / "m138-adapter-description.json").read_text(encoding="utf-8")
    )
    adapter_source_text = (HERE / "m138_adapter.py").read_text(encoding="utf-8")
    adapter_mutation = json.loads(
        (HERE / "m138-adapter-mutation-verification.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_threshold_mutation = json.loads(
        (
            HERE / "m138-adapter-mutation-verification-run1-pre-threshold-fix.json"
        ).read_text(encoding="utf-8")
    )
    adapter_race = json.loads(
        (HERE / "m138-adapter-race-verification.json").read_text(
            encoding="utf-8"
        )
    )
    adapter_pre_threshold_race = json.loads(
        (
            HERE / "m138-adapter-race-verification-run1-pre-threshold-fix.json"
        ).read_text(encoding="utf-8")
    )
    m149_reanchor_manifest = json.loads(
        (HERE / "m149-mutation-manifest-reanchored.json").read_text(
            encoding="utf-8"
        )
    )
    m149_mutation = json.loads(
        (HERE / "m149-mutation-verification.json").read_text(encoding="utf-8")
    )
    m149_mutation_control = json.loads(
        (HERE / "m149-mutation-control.json").read_text(encoding="utf-8")
    )
    m149_artifact_control = json.loads(
        (HERE / "m149-artifact-race-control.json").read_text(encoding="utf-8")
    )
    m149_source_control = json.loads(
        (HERE / "m149-source-race-control.json").read_text(encoding="utf-8")
    )
    m149_artifact_race = json.loads(
        (HERE / "m149-artifact-race-retest.json").read_text(encoding="utf-8")
    )
    m149_source_race = json.loads(
        (HERE / "m149-source-race-retest.json").read_text(encoding="utf-8")
    )
    comparison_rerun = json.loads(
        (HERE / "comparison-verification-rerun-m149.json").read_text(
            encoding="utf-8"
        )
    )

    citation_pattern = re.compile(
        r"(?:(?P<revision>[0-9a-f]{7,40}):)?"
        r"(?P<path>(?:docs|experiments)/[A-Za-z0-9_./-]+)"
        r":(?P<ranges>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)"
    )
    for match in citation_pattern.finditer(report):
        revision = match.group("revision")
        relative = match.group("path")
        path = ROOT / Path(relative)
        if revision is not None:
            try:
                source = subprocess.check_output(
                    ["git", "show", f"{revision}:{relative}"],
                    cwd=ROOT,
                    text=True,
                    encoding="utf-8",
                )
            except subprocess.CalledProcessError:
                findings.append(
                    {"kind": "missing_revision_file", "citation": match.group(0)}
                )
                continue
            line_count = len(source.splitlines())
        else:
            if not path.exists():
                findings.append(
                    {"kind": "missing_file", "citation": match.group(0)}
                )
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        for line_range in match.group("ranges").split(","):
            if "-" in line_range:
                start_text, end_text = line_range.split("-", maxsplit=1)
                start, end = int(start_text), int(end_text)
            else:
                start = end = int(line_range)
            if start < 1 or end < start or end > line_count:
                findings.append(
                    {
                        "kind": "line_range",
                        "citation": match.group(0),
                        "invalid_range": line_range,
                        "line_count": line_count,
                    }
                )

    quote_checks = {
        "docs/proposals/2026-09-sota-scorecard.md": [
            "The burned grid and the development-only high-resolution slide may "
            "commission a new instrument but may never provide its scored value.",
            "Every primary metric is a hard gate. No win compensates for a loss.",
        ],
        "docs/research/M-CAND1.md": [
            "The observed increase is a failure of this finite estimator, not of DPI.",
        ],
        "docs/research/M-PHASE0-SLANTEDGE.md": [
            "Independent 33-step PCHIP linearisation is the one clean success",
        ],
        "docs/research/M-FRC-VIABILITY.md": [
            "Pre-noise transfer is different: it attenuates or strengthens the "
            "latent signal before fresh downstream noise, so repeat correlation "
            "should move.",
            "FRC is safe-by-null for common invertible postfilters, but it is "
            "responsive to pre-noise information transfer.",
        ],
        "docs/research/M115-deconv-headroom.md": [
            "nothing that uses one capture of one sensor can separate a static "
            "sensor pattern from a static scene.",
        ],
        "docs/research/M-PHASE0-SPLIT.md": [
            "the exact historical M115 numbers reproduce, but their controls "
            "do not transfer to the common-mode and data-dependent-tuning "
            "failures on which D8 depends.",
        ],
        "docs/research/M-PHASE0-SPLIT2.md": [
            "Even then, repeated exposures share stable sensor structure",
        ],
        "docs/proposals/2026-08-sota-path.md": [
            "Per-tile FRC between the two half-renders is a spatially-resolved, "
            "model-free certified-resolution map",
        ],
        "experiments/M134-kernel-frontier/M137-clamped-detail.md": [
            "The flat null shows that the gap cannot be called resolved detail; "
            "it is at least substantially, and plausibly predominantly, noise "
            "amplification or another within-hull kernel-transfer effect.",
        ],
        "7fb925bf:experiments/M138-w1-gate-audit/corrected-gate-preregistration.md": [
            "a Boolean supplied by a result file is not admissible evidence.",
            "A failure of calibration cannot be reported as a merge failure.",
        ],
    }
    for relative, quotes in quote_checks.items():
        if re.match(r"^[0-9a-f]{7,40}:", relative):
            revision, path = relative.split(":", maxsplit=1)
            source_text = subprocess.check_output(
                ["git", "show", f"{revision}:{path}"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
            )
        else:
            source_text = (ROOT / relative).read_text(encoding="utf-8")
        source = normalize(source_text)
        for quote in quotes:
            if normalize(quote) not in source:
                findings.append(
                    {"kind": "quote_mismatch", "path": relative, "quote": quote}
                )

    required_sections = [
        "## 0. D8-versus-blindness ruling",
        "## 2. What has already failed",
        "### 2.9 The second flat-null failure",
        "## 3. The precise impossibility result",
        "## 4. Candidate architecture A",
        "## 5. Candidate architecture B",
        "## 7. Frozen challenge battery and outcome",
        "## 8. Admission decision",
        "## 8.1 M138 consumer interface",
        "## 9. Could not determine",
    ]
    for heading in required_sections:
        if heading not in report:
            findings.append({"kind": "missing_heading", "heading": heading})

    if commission.get("status") != "PASS":
        findings.append({"kind": "commission_status", "value": commission.get("status")})
    failed_gates = [name for name, passed in commission.get("gates", {}).items() if not passed]
    if failed_gates:
        findings.append({"kind": "failed_gates", "gates": failed_gates})
    if len(commission.get("gates", {})) != 25:
        findings.append(
            {
                "kind": "gate_count",
                "value": len(commission.get("gates", {})),
                "expected": 25,
            }
        )
    if d8_audit.get("status") != "PASS":
        findings.append({"kind": "d8_audit_status", "value": d8_audit.get("status")})
    failed_d8_checks = [
        name for name, passed in d8_audit.get("checks", {}).items() if not passed
    ]
    if failed_d8_checks:
        findings.append({"kind": "failed_d8_checks", "checks": failed_d8_checks})
    if flat_verification.get("status") != "PASS":
        findings.append(
            {
                "kind": "flat_verification_status",
                "value": flat_verification.get("status"),
            }
        )
    failed_flat_checks = [
        name
        for name, passed in flat_verification.get("checks", {}).items()
        if not passed
    ]
    if failed_flat_checks:
        findings.append(
            {"kind": "failed_flat_verification_checks", "checks": failed_flat_checks}
        )
    if comparison_verification.get("status") != "PASS":
        findings.append(
            {
                "kind": "comparison_verification_status",
                "value": comparison_verification.get("status"),
            }
        )
    failed_comparison_checks = [
        name
        for name, passed in comparison_verification.get("checks", {}).items()
        if not passed
    ]
    if failed_comparison_checks:
        findings.append(
            {
                "kind": "failed_comparison_checks",
                "checks": failed_comparison_checks,
            }
        )
    if comparison_contract.get("status") != "PHYSICAL_UNBOUND":
        findings.append(
            {
                "kind": "comparison_contract_state",
                "value": comparison_contract.get("status"),
            }
        )
    if comparison_binding.get("state") != "UNBOUND":
        findings.append(
            {
                "kind": "comparison_binding_state",
                "value": comparison_binding.get("state"),
            }
        )
    if (
        comparison_manifest.get("physical_binding_state") != "UNBOUND"
        or comparison_manifest.get("claim_bearing_detail_decision_available")
        is not False
    ):
        findings.append({"kind": "comparison_manifest_overclaim"})

    manifest_files = comparison_manifest.get("files", {})
    hash_targets = {
        "comparison-contract.json": HERE / "comparison-contract.json",
        "comparison_checker.py": HERE / "comparison_checker.py",
        "comparison-binding.json": HERE / "comparison-binding.json",
        "CONSUMER-PREREGISTRATION.md": HERE / "CONSUMER-PREREGISTRATION.md",
        "CONSUMER-AMENDMENT-1.md": HERE / "CONSUMER-AMENDMENT-1.md",
        "instrument.py": HERE / "instrument.py",
    }
    for name, path in hash_targets.items():
        expected = manifest_files.get(name, {})
        if "raw_sha256" in expected and raw_sha256(path) != expected["raw_sha256"]:
            findings.append({"kind": "comparison_raw_hash", "path": name})
        if (
            "normalized_text_sha256" in expected
            and normalized_text_sha256(path) != expected["normalized_text_sha256"]
        ):
            findings.append({"kind": "comparison_text_hash", "path": name})
        if (
            "canonical_sha256" in expected
            and canonical_json_sha256(path) != expected["canonical_sha256"]
        ):
            findings.append({"kind": "comparison_canonical_hash", "path": name})
    verification_manifest = comparison_manifest.get("verification", {})
    if raw_sha256(HERE / "comparison-verification.json") != verification_manifest.get(
        "raw_sha256"
    ):
        findings.append({"kind": "comparison_verification_hash"})
    if verification_manifest.get("status") != "PASS" or verification_manifest.get(
        "checks"
    ) != len(comparison_verification.get("checks", {})):
        findings.append({"kind": "comparison_verification_manifest"})

    adapter_checks = adapter_verification.get("checks", {})
    if (
        adapter_verification.get("status") != "PASS"
        or adapter_verification.get("check_count") != 56
        or adapter_verification.get("passed_check_count") != 56
        or not isinstance(adapter_checks, dict)
        or set(adapter_checks.values()) != {True}
        or adapter_checks.get("guard_commission_blur_contract_threshold")
        is not True
        or adapter_checks.get(
            "guard_commission_improvement_contract_threshold"
        )
        is not True
        or adapter_checks.get(
            "commission_blur_threshold_rejects_marginal_control"
        )
        is not True
        or adapter_checks.get(
            "commission_improvement_threshold_rejects_marginal_control"
        )
        is not True
        or adapter_checks.get("bundle_member_hash_refuses") is not True
    ):
        findings.append({"kind": "adapter_verification"})
    if (
        adapter_pre_threshold_verification.get("status") != "PASS"
        or adapter_pre_threshold_verification.get("check_count") != 51
        or adapter_pre_threshold_verification.get("passed_check_count") != 51
    ):
        findings.append({"kind": "adapter_pre_threshold_verification_history"})
    if (
        adapter_pre_m149_verification.get("status") != "PASS"
        or adapter_pre_m149_verification.get("check_count") != 25
        or adapter_pre_m149_verification.get("passed_check_count") != 25
        or set(adapter_pre_m149_verification.get("checks", {}).values())
        != {True}
    ):
        findings.append({"kind": "adapter_pre_m149_verification_history"})
    failed_adapter_checks = adapter_failed_verification.get("checks", {})
    if (
        adapter_failed_verification.get("status") != "FAIL"
        or adapter_failed_verification.get("check_count") != 25
        or adapter_failed_verification.get("passed_check_count") != 24
        or {
            name for name, passed in failed_adapter_checks.items() if not passed
        }
        != {"unbound_status_is_explicit"}
    ):
        findings.append({"kind": "adapter_failed_run_history"})
    if (
        adapter_pre_bootstrap_verification.get("status") != "PASS"
        or adapter_pre_bootstrap_verification.get("check_count") != 25
        or adapter_pre_bootstrap_verification.get("passed_check_count") != 25
        or set(adapter_pre_bootstrap_verification.get("checks", {}).values())
        != {True}
    ):
        findings.append({"kind": "adapter_pre_bootstrap_run_history"})
    if (
        adapter_pre_m149_bootstrap.get("status") != "PASS"
        or adapter_pre_m149_bootstrap.get("check_count") != 10
        or adapter_pre_m149_bootstrap.get("passed_check_count") != 10
        or set(adapter_pre_m149_bootstrap.get("checks", {}).values()) != {True}
    ):
        findings.append({"kind": "adapter_pre_m149_bootstrap_history"})
    mutation_rows = adapter_mutation.get("mutations", [])
    if (
        adapter_mutation.get("status") != "PASS"
        or adapter_mutation.get("base_probe_count") != 27
        or adapter_mutation.get("base_probe_passed_count") != 27
        or adapter_mutation.get("substantive_mutation_count") != 27
        or adapter_mutation.get("killed_mutation_count") != 27
        or adapter_mutation.get("inert_mutation_survived") is not True
        or len(mutation_rows) != 27
        or any(row.get("killed") is not True for row in mutation_rows)
        or any(
            row.get("expected_failed_check")
            not in row.get("failed_checks", [])
            for row in mutation_rows
        )
    ):
        findings.append({"kind": "adapter_mutation_coverage"})
    if (
        adapter_pre_threshold_mutation.get("status") != "PASS"
        or adapter_pre_threshold_mutation.get("substantive_mutation_count") != 25
        or adapter_pre_threshold_mutation.get("killed_mutation_count") != 25
        or adapter_pre_threshold_mutation.get("inert_mutation_survived") is not True
    ):
        findings.append({"kind": "adapter_pre_threshold_mutation_history"})
    race_checks = adapter_race.get("checks", {})
    if (
        adapter_race.get("status") != "PASS"
        or adapter_race.get("check_count") != 7
        or adapter_race.get("passed_check_count") != 7
        or set(race_checks.values()) != {True}
        or adapter_race.get("artifact_race", {}).get("unsafe") != []
        or adapter_race.get("core_race", {}).get("unsafe") != []
        or adapter_race.get("artifact_race", {}).get("attempts") != 128
        or adapter_race.get("core_race", {}).get("attempts") != 128
    ):
        findings.append({"kind": "adapter_race_verification"})
    if (
        adapter_pre_threshold_race.get("status") != "PASS"
        or adapter_pre_threshold_race.get("check_count") != 7
        or adapter_pre_threshold_race.get("passed_check_count") != 7
    ):
        findings.append({"kind": "adapter_pre_threshold_race_history"})
    current_adapter_sha256 = raw_sha256(HERE / "m138_adapter.py")
    expected_old_anchor_ids = {
        "artifact-hash-guard",
        "byte-replay-guard",
        "common-binding-hash-guard",
        "physical-binding-hash-guard",
        "environment-match-guard",
        "commission-null-lower-bound",
        "commission-missing-flat-reason",
        "bundle-member-verification",
        "null-invalid-refusal",
        "null-status",
        "null-center-q05",
        "null-center-q95",
        "null-upper",
        "blur-invalid-refusal",
        "blur-status",
        "improvement-invalid-refusal",
        "improvement-status",
        "missing-not-applicable-refusal",
        "missing-status",
    }
    reconciliation_rows = m149_reanchor_manifest.get("reconciliations", [])
    manifest_mutations = m149_reanchor_manifest.get("behavioral_mutations", [])
    if (
        m149_reanchor_manifest.get("entry_count") != 32
        or m149_reanchor_manifest.get("substantive_entry_count") != 31
        or m149_reanchor_manifest.get("inert_entry_count") != 1
        or m149_reanchor_manifest.get("previous_anchor_error_count") != 19
        or m149_reanchor_manifest.get("reconciled_present_count") != 19
        or m149_reanchor_manifest.get("reconciled_gone_count") != 0
        or m149_reanchor_manifest.get("adapter_sha256") != current_adapter_sha256
        or {row.get("id") for row in reconciliation_rows}
        != expected_old_anchor_ids
        or any(row.get("disposition") != "present" for row in reconciliation_rows)
        or len(manifest_mutations) != 32
    ):
        findings.append({"kind": "m149_reanchor_manifest"})
    normalized_adapter_source = adapter_source_text.replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    for row in manifest_mutations:
        anchor = row.get("anchor")
        if not isinstance(anchor, str) or normalized_adapter_source.count(anchor) != 1:
            findings.append(
                {"kind": "m149_reanchor_count", "mutation": row.get("id")}
            )
            continue
        line = normalized_adapter_source[: normalized_adapter_source.index(anchor)].count(
            "\n"
        ) + 1
        if (
            row.get("current_path")
            != "experiments/M135-detail-instrument/m138_adapter.py"
            or row.get("current_line") != line
            or row.get("predicate_disposition") != "present"
        ):
            findings.append(
                {"kind": "m149_reanchor_location", "mutation": row.get("id")}
            )
    m149_mutation_rows = m149_mutation.get("results", [])
    applied_substantive = [
        row
        for row in m149_mutation_rows
        if row.get("load_bearing_expectation") == "RED"
        and row.get("result") != "ANCHOR_ERROR"
    ]
    killed_substantive = [
        row for row in applied_substantive if row.get("result") == "RED"
    ]
    if (
        m149_mutation.get("status") != "PASS_ALL_SUBSTANTIVE_RED"
        or m149_mutation.get("mutation_count") != 32
        or m149_mutation.get("anchor_errors") != []
        or m149_mutation.get("surviving_substantive_mutations") != []
        or m149_mutation.get("inert_control_failures") != []
        or len(applied_substantive) != 31
        or len(killed_substantive) != 31
    ):
        findings.append({"kind": "m149_reanchored_mutation_coverage"})
    threshold_results = {
        row.get("id"): row for row in m149_mutation_rows
    }
    if not {
        "commission_blur_threshold_rejects_marginal_control",
        "guard_commission_blur_contract_threshold",
    }.issubset(
        set(threshold_results.get("commission-blur-threshold", {}).get(
            "failed_checks", []
        ))
    ):
        findings.append({"kind": "m149_blur_threshold_mutation"})
    if not {
        "commission_improvement_threshold_rejects_marginal_control",
        "guard_commission_improvement_contract_threshold",
    }.issubset(
        set(threshold_results.get("commission-improvement-threshold", {}).get(
            "failed_checks", []
        ))
    ):
        findings.append({"kind": "m149_improvement_threshold_mutation"})
    if (
        m149_mutation_control.get("status") != "FAIL_SURVIVORS"
        or m149_mutation_control.get("mutation_count") != 32
        or m149_mutation_control.get("anchor_errors") != []
        or m149_mutation_control.get("inert_control_failures") != []
        or not {
            "commission-blur-threshold",
            "commission-improvement-threshold",
        }.issubset(
            set(
                m149_mutation_control.get(
                    "surviving_substantive_mutations", []
                )
            )
        )
    ):
        findings.append({"kind": "m149_mutation_positive_control"})
    for label, control, sentinel_required in (
        ("artifact", m149_artifact_control, False),
        ("source", m149_source_control, True),
    ):
        observed = control.get("observed")
        if (
            control.get("status") != "FAIL_RACE_REPRODUCED"
            or control.get("baseline_is_invalid_without_boolean") is not True
            or not isinstance(observed, dict)
            or (
                sentinel_required
                and observed.get("sentinel_executed") is not True
            )
        ):
            findings.append({"kind": f"m149_{label}_race_positive_control"})
    if (
        m149_artifact_race.get("status") != "PASS_NO_RACE_OBSERVED"
        or m149_artifact_race.get("adapter_sha256") != current_adapter_sha256
        or m149_artifact_race.get("baseline_is_invalid_without_boolean") is not True
        or m149_artifact_race.get("historical_fixture_hashes_match") is not True
        or m149_artifact_race.get("registered_invalid_artifact_sha256")
        != "de4523fc4a1c41ced93da0c29a2aa2ea25062ae67248b1e09334d2d78bd7c574"
        or m149_artifact_race.get("unregistered_fail_artifact_sha256")
        != "2aca17c001945544ec60a85eff9a88763d5d77a808817f621673cda855e5e84a"
        or m149_artifact_race.get("observed") is not None
        or sum(m149_artifact_race.get("attempt_counts", {}).values()) != 128
        or any(
            m149_artifact_race.get("attempt_counts", {}).get(key, 0) == 0
            for key in ("exit-0", "exit-2")
        )
    ):
        findings.append({"kind": "m149_artifact_race_retest"})
    if (
        m149_source_race.get("status") != "PASS_NO_RACE_OBSERVED"
        or m149_source_race.get("adapter_sha256") != current_adapter_sha256
        or m149_source_race.get("baseline_is_invalid_without_boolean") is not True
        or m149_source_race.get("registered_core_sha256")
        != "a8f92dbfc436e7a0ffab0fd0cc8bbc9d6708cc829f0435a5bdda510e2a30af5b"
        or m149_source_race.get("observed") is not None
        or sum(m149_source_race.get("attempt_counts", {}).values()) != 128
        or any(
            m149_source_race.get("attempt_counts", {}).get(key, 0) == 0
            for key in ("exit-0", "exit-2")
        )
    ):
        findings.append({"kind": "m149_source_race_retest"})
    if (
        comparison_rerun.get("status") != "PASS"
        or len(comparison_rerun.get("checks", {})) != 14
        or set(comparison_rerun.get("checks", {}).values()) != {True}
    ):
        findings.append({"kind": "comparison_rerun"})
    for label, artifact, expected_checks in (
        ("adapter_pre_source_run_history", adapter_pre_source_verification, 25),
        ("adapter_pre_source_bootstrap_history", adapter_pre_source_bootstrap, 5),
    ):
        if (
            artifact.get("status") != "PASS"
            or artifact.get("check_count") != expected_checks
            or artifact.get("passed_check_count") != expected_checks
            or set(artifact.get("checks", {}).values()) != {True}
        ):
            findings.append({"kind": label})
    if (
        adapter_contract.get("schema") != "m135-m138-adapter-contract-v1"
        or canonical_json_sha256(HERE / "m138-adapter-contract.json")
        != "30453f8901c0b121a48771d35c9cf735da88358bb441794b918de77b267903e2"
    ):
        findings.append({"kind": "adapter_contract_hash"})
    expected_coverage_summary = {
        "ordinary_checks": 56,
        "local_substantive_mutations_applied": 27,
        "local_substantive_mutations_killed": 27,
        "m149_manifest_entries": 32,
        "m149_substantive_mutations_applied": 31,
        "m149_substantive_mutations_killed": 31,
        "m149_manifest_entries_unapplied": 0,
        "m149_inert_mutations_green": 1,
    }
    if (
        adapter_manifest.get("schema")
        != "m135-m138-adapter-result-manifest-v3"
        or adapter_manifest.get("status")
        != "PASS_INTERFACE_ONLY_PHYSICAL_UNBOUND_M149_THRESHOLD_REPAIR_AWAITING_REVIEW"
        or adapter_manifest.get("physical_binding_state") != "UNBOUND"
        or adapter_manifest.get("claim_bearing_detail_decision_available") is not False
        or adapter_manifest.get("independent_review_state")
        != "M149_SECOND_SEND_BACK_REPAIRED_AWAITING_REATTACK"
        or adapter_manifest.get("coverage_summary") != expected_coverage_summary
    ):
        findings.append({"kind": "adapter_manifest_overclaim"})
    required_result_files = {
        "M138-ADAPTER-AMENDMENT-8.md",
        "m138_adapter.py",
        "m138-checker-bundle.json",
        "m138-adapter-description.json",
        "m138-adapter-verification.json",
        "m138-adapter-mutation-verification.json",
        "m138-adapter-race-verification.json",
        "m149-mutation-manifest-reanchored.json",
        "m149-mutation-verification.json",
        "m149-mutation-control.json",
        "m149-artifact-race-control.json",
        "m149-source-race-control.json",
        "m149-artifact-race-retest.json",
        "m149-source-race-retest.json",
        "m138-adapter-verification-run6-pre-threshold-fix.json",
        "m138-adapter-mutation-verification-run1-pre-threshold-fix.json",
        "m138-adapter-race-verification-run1-pre-threshold-fix.json",
        "m138-adapter-result-manifest-run2-pre-threshold-fix.json",
    }
    if not required_result_files.issubset(
        set(adapter_manifest.get("files", {}))
    ):
        findings.append({"kind": "adapter_manifest_missing_file"})
    for name, hashes in adapter_manifest.get("files", {}).items():
        path = HERE / name
        if not path.is_file() or raw_sha256(path) != hashes.get("raw_sha256"):
            findings.append({"kind": "adapter_manifest_hash", "path": name})
    adapter_contract_manifest = adapter_manifest.get("adapter_contract", {})
    if (
        raw_sha256(HERE / "m138-adapter-contract.json")
        != adapter_contract_manifest.get("raw_sha256")
        or canonical_json_sha256(HERE / "m138-adapter-contract.json")
        != adapter_contract_manifest.get("canonical_sha256")
    ):
        findings.append({"kind": "adapter_contract_manifest"})
    adapter_verification_manifest = adapter_manifest.get("verification", {})
    if raw_sha256(HERE / "m138-adapter-verification.json") != (
        adapter_verification_manifest.get("read_once_behavior", {}).get(
            "raw_sha256"
        )
    ):
        findings.append({"kind": "adapter_final_verification_hash"})
    if raw_sha256(HERE / "m138-adapter-verification-run2-failed.json") != (
        adapter_verification_manifest.get("amendment_1_run", {}).get("raw_sha256")
    ):
        findings.append({"kind": "adapter_failed_verification_hash"})
    if raw_sha256(HERE / "m138-adapter-verification-run3-pre-bootstrap.json") != (
        adapter_verification_manifest.get("pre_bootstrap_hardening", {}).get(
            "raw_sha256"
        )
    ):
        findings.append({"kind": "adapter_pre_bootstrap_verification_hash"})
    if raw_sha256(
        HERE / "m138-adapter-bootstrap-verification-run2-pre-m149.json"
    ) != (
        adapter_verification_manifest.get("pre_m149_bootstrap", {}).get(
            "raw_sha256"
        )
    ):
        findings.append({"kind": "adapter_pre_m149_bootstrap_hash"})
    if raw_sha256(HERE / "m138-adapter-verification-run4-pre-source-loader.json") != (
        adapter_verification_manifest.get("pre_source_loader_hardening", {}).get(
            "raw_sha256"
        )
    ):
        findings.append({"kind": "adapter_pre_source_verification_hash"})
    if raw_sha256(
        HERE / "m138-adapter-bootstrap-verification-run1-pre-source-loader.json"
    ) != adapter_verification_manifest.get("pre_source_loader_bootstrap", {}).get(
        "raw_sha256"
    ):
        findings.append({"kind": "adapter_pre_source_bootstrap_hash"})
    if raw_sha256(HERE / "m138-adapter-verification-run5-pre-m149.json") != (
        adapter_verification_manifest.get("pre_m149_behavior", {}).get("raw_sha256")
    ):
        findings.append({"kind": "adapter_pre_m149_verification_hash"})
    if raw_sha256(HERE / "m138-adapter-mutation-verification.json") != (
        adapter_verification_manifest.get("mutation_coverage", {}).get("raw_sha256")
    ):
        findings.append({"kind": "adapter_mutation_verification_hash"})
    if raw_sha256(HERE / "m138-adapter-race-verification.json") != (
        adapter_verification_manifest.get("replacement_races", {}).get("raw_sha256")
    ):
        findings.append({"kind": "adapter_race_verification_hash"})
    if raw_sha256(HERE / "m149-artifact-race-retest.json") != (
        adapter_verification_manifest.get("m149_artifact_race_retest", {}).get(
            "raw_sha256"
        )
    ):
        findings.append({"kind": "m149_artifact_race_retest_hash"})
    if raw_sha256(HERE / "m149-source-race-retest.json") != (
        adapter_verification_manifest.get("m149_source_race_retest", {}).get(
            "raw_sha256"
        )
    ):
        findings.append({"kind": "m149_source_race_retest_hash"})
    for name, key in (
        (
            "m138-adapter-verification-run6-pre-threshold-fix.json",
            "pre_threshold_behavior",
        ),
        (
            "m138-adapter-mutation-verification-run1-pre-threshold-fix.json",
            "pre_threshold_local_mutation",
        ),
        (
            "m138-adapter-race-verification-run1-pre-threshold-fix.json",
            "pre_threshold_race",
        ),
        ("m149-mutation-manifest-reanchored.json", "m149_reanchored_manifest"),
        ("m149-mutation-verification.json", "m149_reanchored_mutation"),
        ("m149-mutation-control.json", "m149_mutation_positive_control"),
        ("m149-artifact-race-control.json", "m149_artifact_race_control"),
        ("m149-source-race-control.json", "m149_source_race_control"),
    ):
        if raw_sha256(HERE / name) != adapter_verification_manifest.get(
            key, {}
        ).get("raw_sha256"):
            findings.append({"kind": f"{key}_hash"})
    if (
        adapter_verification.get("adapter_sha256")
        != raw_sha256(HERE / "m138_adapter.py")
        or adapter_verification.get("adapter_contract_canonical_sha256")
        != canonical_json_sha256(HERE / "m138-adapter-contract.json")
    ):
        findings.append({"kind": "adapter_verification_identity"})
    if (
        adapter_bundle.get("schema") != "m135-checker-bundle/v1"
        or adapter_bundle.get("rule_id") != "m135-m138-adapter-v1"
    ):
        findings.append({"kind": "adapter_bundle_schema"})
    else:
        expected_bundle_files = {
            "comparison_checker.py",
            "m138_adapter.py",
            "comparison-contract.json",
            "comparison-binding.json",
            "m138-adapter-environment.json",
            "m138-adapter-contract.json",
            "instrument.py",
            "M138-ADAPTER-PREREGISTRATION.md",
            *(f"M138-ADAPTER-AMENDMENT-{i}.md" for i in range(1, 9)),
        }
        bundle_files = {
            ref.get("path") for ref in adapter_bundle.get("files", [])
        }
        if bundle_files != expected_bundle_files:
            findings.append(
                {
                    "kind": "adapter_bundle_membership",
                    "missing": sorted(expected_bundle_files - bundle_files),
                    "unexpected": sorted(bundle_files - expected_bundle_files),
                }
            )
        for ref in adapter_bundle.get("files", []):
            path = HERE / ref.get("path", "")
            if not path.is_file() or raw_sha256(path) != ref.get("sha256"):
                findings.append(
                    {"kind": "adapter_bundle_hash", "path": ref.get("path")}
                )
    if (
        adapter_description.get("binding_state") != "UNBOUND"
        or adapter_description.get("checker_sha256")
        != raw_sha256(HERE / "m138_adapter.py")
        or adapter_description.get("checker_bundle_manifest_sha256")
        != raw_sha256(HERE / "m138-checker-bundle.json")
        or adapter_description.get("environment_manifest_sha256")
        != raw_sha256(HERE / "m138-adapter-environment.json")
        or adapter_description.get("comparison_rule_sha256")
        != raw_sha256(HERE / "comparison-contract.json")
        or adapter_manifest.get("production_description") != adapter_description
    ):
        findings.append({"kind": "adapter_production_description"})
    adapter_tree = ast.parse(adapter_source_text)
    functions = {
        node.name: node
        for node in adapter_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    forbidden_reopens = {
        "read_bytes",
        "read_text",
        "open",
        "file_sha256",
        "normalized_text_sha256",
        "load_json_object",
    }
    for function_name in (
        "install_core_module",
        "load_core_payload",
        "common_output",
        "refusal_object",
        "process_evaluate",
        "process_commission",
    ):
        function = functions.get(function_name)
        if function is None:
            findings.append(
                {"kind": "adapter_read_once_function_missing", "function": function_name}
            )
            continue
        called_names = {
            node.func.attr
            if isinstance(node.func, ast.Attribute)
            else node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Attribute, ast.Name))
        }
        reopened = sorted(called_names & forbidden_reopens)
        if reopened:
            findings.append(
                {
                    "kind": "adapter_verified_path_reopen",
                    "function": function_name,
                    "calls": reopened,
                }
            )
    if (
        "compile(source.data, str(source.path), \"exec\""
        not in adapter_source_text
        or "module.load_json = verified_load_json" not in adapter_source_text
        or "verify_snapshot_digest(" not in adapter_source_text
    ):
        findings.append({"kind": "adapter_read_once_structure"})

    output = {
        "status": "PASS" if not findings else "FAIL",
        "citation_count": len(list(citation_pattern.finditer(report))),
        "citation_range_count": sum(
            len(match.group("ranges").split(","))
            for match in citation_pattern.finditer(report)
        ),
        "verified_tags": report.count("**VERIFIED."),
        "assumed_tags": report.count("**ASSUMED."),
        "d8_checks": len(d8_audit.get("checks", {})),
        "flat_checks": len(flat_verification.get("checks", {})),
        "comparison_checks": len(comparison_verification.get("checks", {})),
        "comparison_binding_state": comparison_binding.get("state"),
        "adapter_checks": len(adapter_checks),
        "adapter_local_mutations_killed": adapter_mutation.get(
            "killed_mutation_count"
        ),
        "adapter_manifest_mutations_applied": len(applied_substantive),
        "adapter_manifest_mutations_killed": len(killed_substantive),
        "adapter_manifest_mutations_unapplied": len(
            m149_mutation.get("anchor_errors", [])
        ),
        "adapter_race_checks": len(race_checks),
        "m149_artifact_race_attempts": sum(
            m149_artifact_race.get("attempt_counts", {}).values()
        ),
        "m149_source_race_attempts": sum(
            m149_source_race.get("attempt_counts", {}).values()
        ),
        "adapter_binding_state": adapter_description.get("binding_state"),
        "adapter_independent_review": (
            "M149_SECOND_SEND_BACK_REPAIRED_AWAITING_REATTACK"
        ),
        "findings": findings,
    }
    output_path = Path(__file__).resolve().parent / "audit.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
