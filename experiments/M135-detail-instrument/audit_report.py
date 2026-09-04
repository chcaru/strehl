"""Structural and source-citation audit for the M135 report."""

from __future__ import annotations

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
    adapter_bootstrap_verification = json.loads(
        (HERE / "m138-adapter-bootstrap-verification.json").read_text(
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
        or adapter_verification.get("check_count") != 25
        or adapter_verification.get("passed_check_count") != 25
        or not isinstance(adapter_checks, dict)
        or set(adapter_checks.values()) != {True}
    ):
        findings.append({"kind": "adapter_verification"})
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
        adapter_bootstrap_verification.get("status") != "PASS"
        or adapter_bootstrap_verification.get("check_count") != 10
        or adapter_bootstrap_verification.get("passed_check_count") != 10
        or set(adapter_bootstrap_verification.get("checks", {}).values()) != {True}
        or adapter_bootstrap_verification.get("adapter_sha256")
        != raw_sha256(HERE / "m138_adapter.py")
        or adapter_bootstrap_verification.get("bundle_sha256")
        != raw_sha256(HERE / "m138-checker-bundle.json")
    ):
        findings.append({"kind": "adapter_bootstrap_verification"})
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
    if (
        adapter_manifest.get("status") != "PASS_INTERFACE_ONLY_PHYSICAL_UNBOUND"
        or adapter_manifest.get("physical_binding_state") != "UNBOUND"
        or adapter_manifest.get("claim_bearing_detail_decision_available") is not False
    ):
        findings.append({"kind": "adapter_manifest_overclaim"})
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
        adapter_verification_manifest.get("final", {}).get("raw_sha256")
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
    if raw_sha256(HERE / "m138-adapter-bootstrap-verification.json") != (
        adapter_verification_manifest.get("bootstrap_order", {}).get("raw_sha256")
    ):
        findings.append({"kind": "adapter_bootstrap_verification_hash"})
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
        "adapter_bootstrap_checks": len(
            adapter_bootstrap_verification.get("checks", {})
        ),
        "adapter_binding_state": adapter_description.get("binding_state"),
        "adapter_independent_review": "PENDING",
        "findings": findings,
    }
    output_path = Path(__file__).resolve().parent / "audit.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
