from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import (
    BOUND_SOURCE_NAMES,
    CHECKOUT_BOUND_RELATIVE_PATHS,
    EXPERIMENT_DIR,
    PRIVATE_SCRATCH,
    REPO_ROOT,
    EvidenceError,
    ensure_private_path,
    json_digest,
    script_hashes,
    sha256_bytes,
    sha256_file,
    write_json_new,
)
from verify import CLAIM_AUDIT_CHECK_COUNT, fixture_verdict


BASE_FIXTURE_TEXT = r"""{
  "input_path": "D:\\personal\\macro\\coffee-bubbles",
  "source_affected_expected": "1a6fd10c94dcb4b780f6af78c46c62a156c39b71",
  "source_affected_current": "1a6fd10c94dcb4b780f6af78c46c62a156c39b71",
  "source_fixed_expected": "a97275817c58e164f75c7cd3d80ca99444a2a145",
  "source_fixed_current": "a97275817c58e164f75c7cd3d80ca99444a2a145",
  "lineage_parent_ok": true,
  "binary_sha256_expected": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "binary_sha256_current": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "worker_records": {"affected-w1": 1, "affected-w2": 2, "affected-w1-repeat": 1, "fixed-w1": 1, "fixed-w2": 2},
  "run_root_preexisting": false,
  "output_preexisting": false,
  "output_created_after_launch": true,
  "affected_w1_pixels": [[[100, 200, 300], [10, 20, 30]]],
  "affected_w2_pixels": [[[101, 198, 300], [10, 20, 30]]],
  "affected_repeat_pixels": [[[100, 200, 300], [10, 20, 30]]],
  "fixed_w1_pixels": [[[500, 600, 700], [40, 50, 60]]],
  "fixed_w2_pixels": [[[500, 600, 700], [40, 50, 60]]],
  "metadata_a_pixels": [[[7, 8, 9]]],
  "metadata_b_pixels": [[[7, 8, 9]]],
  "metadata_a_file_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "metadata_b_file_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "metadata_expected_relation": "FILE_METADATA_ONLY",
  "expected_difference": {
    "differing_channel_samples": 2,
    "differing_pixels_any_channel": 1,
    "per_channel_differing_samples": {"R": 1, "G": 1, "B": 0},
    "signed_delta_histogram": {"-2": 1, "1": 1},
    "max_absolute_dn16": 2,
    "max_relative_per_pixel_channel": 0.01
  },
  "mechanism_preconditions": true,
  "source_anchor_count": 1,
  "input_manifest_before_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "input_manifest_after_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
  "required_non_null_environment": ["RAYON_NUM_THREADS", "STREHL_PYRAMID_WORKERS"],
  "renderer_environment": {"RAYON_NUM_THREADS": "2", "STREHL_PYRAMID_WORKERS": "2"},
  "settings_invariant": true,
  "secondary_decoder_equal": true,
  "output_binding_ok": true,
  "peak_resident_bytes": 2147483648,
  "expected_verdict": "REDUCTION_ORDER",
  "note": "deliberately ignored inert commissioning note"
}
"""


@dataclass(frozen=True)
class Mutation:
    name: str
    anchor: str
    replacement: str
    expected_error: str
    kind: str = "substantive"
    expected_classification_change: tuple[str, str] | None = None


MUTATIONS = [
    Mutation(
        "wrong-input-provenance",
        '  "input_path": "D:\\\\personal\\\\macro\\\\coffee-bubbles",',
        '  "input_path": "C:\\\\unapproved\\\\coffee-bubbles",',
        "M176-E-INPUT",
    ),
    Mutation(
        "protected-parent-refusal",
        '  "input_path": "D:\\\\personal\\\\macro\\\\coffee-bubbles",',
        '  "input_path": "D:\\\\personal\\\\macro",',
        "M176-E-PROTECTED-PATH",
    ),
    Mutation(
        "forbidden-subtree-refusal",
        '  "input_path": "D:\\\\personal\\\\macro\\\\coffee-bubbles",',
        '  "input_path": "D:\\\\personal\\\\macro\\\\requests\\\\7-aperture-pairs",',
        "M176-E-FORBIDDEN-PATH",
    ),
    Mutation(
        "wrong-affected-source-provenance",
        '  "source_affected_current": "1a6fd10c94dcb4b780f6af78c46c62a156c39b71",',
        '  "source_affected_current": "0a6fd10c94dcb4b780f6af78c46c62a156c39b71",',
        "M176-E-SOURCE",
    ),
    Mutation(
        "wrong-fixed-source-provenance",
        '  "source_fixed_current": "a97275817c58e164f75c7cd3d80ca99444a2a145",',
        '  "source_fixed_current": "b97275817c58e164f75c7cd3d80ca99444a2a145",',
        "M176-E-SOURCE",
    ),
    Mutation(
        "broken-repair-parent-lineage",
        '  "lineage_parent_ok": true,',
        '  "lineage_parent_ok": false,',
        "M176-E-LINEAGE",
    ),
    Mutation(
        "wrong-binary-sha256-provenance",
        '  "binary_sha256_current": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",',
        '  "binary_sha256_current": "baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",',
        "M176-E-BINARY",
    ),
    Mutation(
        "wrong-worker-provenance",
        '  "worker_records": {"affected-w1": 1, "affected-w2": 2, "affected-w1-repeat": 1, "fixed-w1": 1, "fixed-w2": 2},',
        '  "worker_records": {"affected-w1": 1, "affected-w2": 3, "affected-w1-repeat": 1, "fixed-w1": 1, "fixed-w2": 2},',
        "M176-E-WORKER",
    ),
    Mutation(
        "stale-preexisting-output-acceptance",
        '  "output_preexisting": false,',
        '  "output_preexisting": true,',
        "M176-E-STALE",
    ),
    Mutation(
        "stale-output-timestamp-acceptance",
        '  "output_created_after_launch": true,',
        '  "output_created_after_launch": false,',
        "M176-E-STALE",
    ),
    Mutation(
        "same-worker-nondeterminism",
        '  "affected_repeat_pixels": [[[100, 200, 300], [10, 20, 30]]],',
        '  "affected_repeat_pixels": [[[100, 200, 301], [10, 20, 30]]],',
        "M176-E-REPEAT",
        expected_classification_change=("REDUCTION_ORDER", "OTHER_UNRESOLVED"),
    ),
    Mutation(
        "planted-improvement-repair-differing-pixel",
        '  "affected_w2_pixels": [[[101, 198, 300], [10, 20, 30]]],',
        '  "affected_w2_pixels": [[[100, 200, 300], [10, 20, 30]]],',
        "M176-E-CROSS",
        expected_classification_change=("REDUCTION_ORDER", "NOT_REPRODUCED"),
    ),
    Mutation(
        "planted-degradation-fixed-plus-one-dn",
        '  "fixed_w2_pixels": [[[500, 600, 700], [40, 50, 60]]],',
        '  "fixed_w2_pixels": [[[501, 600, 700], [40, 50, 60]]],',
        "M176-E-FIXED",
        expected_classification_change=("REDUCTION_ORDER", "OTHER_UNRESOLVED"),
    ),
    Mutation(
        "tiff-metadata-only-pixel-confusion",
        '  "metadata_b_pixels": [[[7, 8, 9]]],',
        '  "metadata_b_pixels": [[[7, 8, 10]]],',
        "M176-E-METADATA",
    ),
    Mutation(
        "magnitude-sign-histogram-inversion",
        '    "signed_delta_histogram": {"-2": 1, "1": 1},',
        '    "signed_delta_histogram": {"-1": 1, "2": 1},',
        "M176-E-MAGNITUDE",
    ),
    Mutation(
        "mechanism-precondition-removed",
        '  "mechanism_preconditions": true,',
        '  "mechanism_preconditions": false,',
        "M176-E-MECHANISM",
        expected_classification_change=("REDUCTION_ORDER", "OTHER_UNRESOLVED"),
    ),
    Mutation(
        "nonunique-source-mutation-anchor",
        '  "source_anchor_count": 1,',
        '  "source_anchor_count": 2,',
        "M176-E-SOURCE-ANCHOR",
    ),
    Mutation(
        "source-before-after-mutation",
        '  "input_manifest_after_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",',
        '  "input_manifest_after_sha256": "eddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",',
        "M176-E-INPUT-MUTATION",
    ),
    Mutation(
        "missing-renderer-environment",
        '  "renderer_environment": {"RAYON_NUM_THREADS": "2", "STREHL_PYRAMID_WORKERS": "2"},',
        '  "renderer_environment": {"RAYON_NUM_THREADS": null, "STREHL_PYRAMID_WORKERS": "2"},',
        "M176-E-ENV",
    ),
    Mutation(
        "non-worker-setting-drift",
        '  "settings_invariant": true,',
        '  "settings_invariant": false,',
        "M176-E-SETTINGS",
    ),
    Mutation(
        "independent-tiff-decoder-disagreement",
        '  "secondary_decoder_equal": true,',
        '  "secondary_decoder_equal": false,',
        "M176-E-DECODE-DISAGREE",
    ),
    Mutation(
        "output-record-hash-unbound",
        '  "output_binding_ok": true,',
        '  "output_binding_ok": false,',
        "M176-E-OUTPUT-BINDING",
    ),
    Mutation(
        "resident-limit-exceeded",
        '  "peak_resident_bytes": 2147483648,',
        '  "peak_resident_bytes": 4294967297,',
        "M176-E-RESOURCE",
    ),
    Mutation(
        "wrong-mechanism-verdict",
        '  "expected_verdict": "REDUCTION_ORDER",',
        '  "expected_verdict": "NOT_REPRODUCED",',
        "M176-E-VERDICT",
    ),
]

INERT = Mutation(
    "deliberately-inert-note",
    '  "note": "deliberately ignored inert commissioning note"',
    '  "note": "inert mutation survived without touching evidence or verdict"',
    "",
    kind="inert",
)

CLAIM_AUDIT_MUTATIONS = [
    Mutation(
        "stale-invalid-audit-revision",
        ('  "audit": {\n    "revision": "69bdacafbb4a49a198e9f430590033e8a5ed25a2",'),
        ('  "audit": {\n    "revision": "0000000000000000000000000000000000000000",'),
        "M176-E-CLAIM-REVISION",
    ),
    Mutation(
        "missing-m165-row",
        '      "id": "M165",',
        '      "id": "M165-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-m164-future-candidate-row",
        '      "id": "M164-FUTURE-CANDIDATE",',
        '      "id": "M164-FUTURE-CANDIDATE-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-m8-r-row",
        '      "id": "M8-R",',
        '      "id": "M8-R-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-m8-o-row",
        '      "id": "M8-O",',
        '      "id": "M8-O-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-dust-off-row",
        '      "id": "V-MOTE-DUST-OFF",',
        '      "id": "V-MOTE-DUST-OFF-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-shipping-byte-freeze-row",
        '      "id": "SHIPPING-SCALE-CATMULL-ROM-BYTE-FREEZE",',
        '      "id": "SHIPPING-SCALE-CATMULL-ROM-BYTE-FREEZE-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-v-envsurf-workers-row",
        '      "id": "V-ENVSURF-WORKERS",',
        '      "id": "V-ENVSURF-WORKERS-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-m-phase0-split-row",
        '      "id": "M-PHASE0-SPLIT",',
        '      "id": "M-PHASE0-SPLIT-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-build-speed-row",
        '      "id": "BUILD-SPEED",',
        '      "id": "BUILD-SPEED-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-orch-ship-v3-v4-row",
        '      "id": "ORCH-SHIP-V3-V4",',
        '      "id": "ORCH-SHIP-V3-V4-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-v-never-worse-ship-render-row",
        '      "id": "V-NEVERWORSE-SHIP-RENDER",',
        '      "id": "V-NEVERWORSE-SHIP-RENDER-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-scorecard-baseline-row",
        '      "id": "SCORECARD-BASELINE",',
        '      "id": "SCORECARD-BASELINE-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-unsealed-render-resume-paths-row",
        '      "id": "UNSEALED-RENDER-RESUME-PATHS",',
        '      "id": "UNSEALED-RENDER-RESUME-PATHS-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "missing-m172-unit-worker-contract-row",
        '      "id": "M172-UNIT-WORKER-CONTRACT",',
        '      "id": "M172-UNIT-WORKER-CONTRACT-MISSING",',
        "M176-E-CLAIM-IDS",
    ),
    Mutation(
        "wrong-allowed-classification",
        (
            '      "classifications": [\n'
            '        "SURVIVES_UNCONDITIONALLY"\n'
            "      ],\n"
            '      "classification_basis": "historical M12 worker ladder",'
        ),
        (
            '      "classifications": [\n'
            '        "SURVIVES_SAME_WORKER_ONLY"\n'
            "      ],\n"
            '      "classification_basis": "historical M12 worker ladder",'
        ),
        "M176-E-CLAIM-DISPOSITION",
    ),
    Mutation(
        "wrong-allowed-worker-provenance",
        (
            '      "worker_provenance": {\n'
            '        "state": "DECLARED_SWEEP",\n'
            '        "detail": "Registered W=1/2/4/8/16 with six repetitions per completed cell."\n'
            "      },"
        ),
        (
            '      "worker_provenance": {\n'
            '        "state": "EXPLICIT_PIN",\n'
            '        "detail": "Registered W=1/2/4/8/16 with six repetitions per completed cell."\n'
            "      },"
        ),
        "M176-E-CLAIM-DISPOSITION",
    ),
    Mutation(
        "m130-wrong-sanitized-default-provenance",
        (
            '      "worker_provenance": {\n'
            '        "state": "EXPLICIT_PIN",\n'
            '        "detail": "Every comparable A/B render explicitly set Pyramid W=2; the separate registry witness records W=4 and is not the A/B provenance."\n'
            "      },"
        ),
        (
            '      "worker_provenance": {\n'
            '        "state": "DEFAULT_SANITIZED_COMMON",\n'
            '        "detail": "Every comparable A/B render explicitly set Pyramid W=2; the separate registry witness records W=4 and is not the A/B provenance."\n'
            "      },"
        ),
        "M176-E-CLAIM-DISPOSITION",
    ),
    Mutation(
        "damaged-normative-requirement",
        '  "normative_requirement": "Every scored, cached, or hash-frozen render MUST bind workers_requested, workers_resolved, and a versioned reduction_lattice_id containing the exact logical frame partitions and ordered reduction topology to both its whole-file and canonical-pixel SHA-256, and MUST refuse comparison or reuse on any mismatch.",',
        '  "normative_requirement": "Every scored render SHOULD record a worker count.",',
        "M176-E-CLAIM-NORMATIVE",
    ),
    Mutation(
        "fabricated-pinned-worker-group-member",
        '        "V-ca",',
        '        "FABRICATED-NOT-A-GROUP-MEMBER",',
        "M176-E-CLAIM-GROUP-MEMBERS",
    ),
    Mutation(
        "protected-path-shaped-inventory-escape",
        '          "path": "crates/strehl-cli/src/bin/strehl-common-input.rs",',
        '          "path": "../outside/strehl-common-input.rs",',
        "M176-E-CLAIM-PATH",
    ),
    Mutation(
        "missing-symbol-semantic-anchor",
        '          "anchor": "merge.add_frame(&refs, &luma, &variance, &mut frame_workspace);"',
        '          "anchor": ""',
        "M176-E-CLAIM-ANCHOR",
    ),
    Mutation(
        "nonexistent-evidence-path-with-nonempty-anchor",
        '          "path": "crates/strehl-cli/src/bin/strehl-common-input.rs",',
        '          "path": "crates/strehl-cli/src/bin/does-not-exist-m176.rs",',
        "M176-E-CLAIM-EVIDENCE-PATH",
    ),
    Mutation(
        "fabricated-nonempty-anchor-in-existing-evidence",
        '          "anchor": "merge.add_frame(&refs, &luma, &variance, &mut frame_workspace);"',
        '          "anchor": "M176 FABRICATED NONEMPTY ANCHOR ABSENT FROM THE BLOB"',
        "M176-E-CLAIM-EVIDENCE-ANCHOR",
    ),
    Mutation(
        "missing-revision-search-hit",
        '        "path": "docs/research/BUILD-CROP.md",',
        '        "path": "docs/research/BUILD-CROP-MISSING.md",',
        "M176-E-CLAIM-SEARCH",
    ),
    Mutation(
        "status-replacement-falsely-marked-applied",
        '    "status_edit_performed": false,',
        '    "status_edit_performed": true,',
        "M176-E-CLAIM-STATUS",
    ),
    Mutation(
        "m176-falsely-credited-with-renderer-repair",
        '    "m176_renderer_change": "NONE",',
        '    "m176_renderer_change": "REPAIR_LANDED",',
        "M176-E-CLAIM-BOUNDARY",
    ),
    Mutation(
        "missing-remaining-uncertainty",
        '      "id": "U4",',
        '      "id": "U4-MISSING",',
        "M176-E-CLAIM-UNCERTAINTY",
    ),
]

CHECKOUT_POLICY_MUTATIONS = [
    Mutation(
        "checkout-json-eol-policy-corrupted",
        "*.json text eol=lf",
        "*.json text eol=crlf",
        "M176-E-CHECKOUT-EOL",
    ),
]


def mutate_unique_full_line(text: str, mutation: Mutation) -> str:
    lines = text.splitlines()
    anchor_lines = mutation.anchor.splitlines()
    replacement_lines = mutation.replacement.splitlines()
    matches = [
        index
        for index in range(len(lines) - len(anchor_lines) + 1)
        if lines[index : index + len(anchor_lines)] == anchor_lines
    ]
    count = len(matches)
    if count != 1:
        raise EvidenceError(
            "M176-E-COMMISSION-ANCHOR",
            f"{mutation.name}: expected unique full-line block, found {count}",
        )
    index = matches[0]
    return (
        "\n".join(
            [*lines[:index], *replacement_lines, *lines[index + len(anchor_lines) :]]
        )
        + "\n"
    )


def run_fixture(
    python: Path,
    sandbox: Path,
    fixture: Path,
    result: Path,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            str(python),
            str(sandbox / "verify.py"),
            "--fixture",
            str(fixture),
            "--result",
            str(result),
        ],
        cwd=sandbox,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )


def run_claim_audit(
    python: Path,
    sandbox: Path,
    claim_audit: Path,
    result: Path,
    repo_root: Path,
    status_file: Path,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            str(python),
            str(sandbox / "verify.py"),
            "--claim-audit",
            str(claim_audit),
            "--repo-root",
            str(repo_root),
            "--status-file",
            str(status_file),
            "--result",
            str(result),
        ],
        cwd=sandbox,
        env=os.environ.copy(),
        capture_output=True,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--scratch-name", default="commission")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    try:
        evidence_dir = args.evidence_dir.resolve()
        result_file = (
            args.result.resolve()
            if args.result is not None
            else evidence_dir / "commission.json"
        )
        repo_root = REPO_ROOT.resolve()
        status_file = (repo_root / "docs" / "STATUS.md").resolve()
        status_sha_before = sha256_file(status_file)
        scratch = ensure_private_path(PRIVATE_SCRATCH / args.scratch_name)
        if scratch.exists():
            raise EvidenceError("M176-E-STALE", f"commission scratch exists: {scratch}")
        scratch.mkdir(parents=True)
        sandbox = scratch / "sandbox"
        sandbox.mkdir()
        source_names = list(BOUND_SOURCE_NAMES)
        for relative in CHECKOUT_BOUND_RELATIVE_PATHS:
            destination = sandbox / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(EXPERIMENT_DIR / Path(relative), destination)
        production_before = script_hashes()
        sandbox_before = {name: sha256_file(sandbox / name) for name in source_names}
        fixture = sandbox / "fixture.json"
        fixture.write_text(BASE_FIXTURE_TEXT, encoding="utf-8", newline="\n")
        baseline_fixture_sha = sha256_file(fixture)
        baseline_result = sandbox / "baseline-result.json"
        baseline_run = run_fixture(
            Path(sys.executable), sandbox, fixture, baseline_result
        )
        if baseline_run.returncode != 0:
            raise EvidenceError(
                "M176-E-COMMISSION",
                "baseline fixture failed: "
                + baseline_run.stderr.decode("utf-8", errors="replace"),
            )
        baseline_result_bytes = baseline_result.read_bytes()
        baseline_verdict = fixture_verdict(json.loads(BASE_FIXTURE_TEXT))
        require_baseline = "REDUCTION_ORDER"
        if baseline_verdict != require_baseline:
            raise EvidenceError(
                "M176-E-COMMISSION",
                f"baseline verdict is {baseline_verdict}, expected {require_baseline}",
            )

        claim_audit_source = evidence_dir / "claim-audit.json"
        claim_audit_source_sha = sha256_file(claim_audit_source)
        claim_audit_text = claim_audit_source.read_text(encoding="utf-8")
        claim_audit = sandbox / "out" / "claim-audit.json"
        baseline_claim_sha = sha256_file(claim_audit)
        baseline_claim_result = sandbox / "baseline-claim-audit-result.json"
        baseline_claim_run = run_claim_audit(
            Path(sys.executable),
            sandbox,
            claim_audit,
            baseline_claim_result,
            repo_root,
            status_file,
        )
        if baseline_claim_run.returncode != 0:
            raise EvidenceError(
                "M176-E-COMMISSION",
                "baseline claim audit failed: "
                + baseline_claim_run.stderr.decode("utf-8", errors="replace"),
            )
        baseline_claim_result_bytes = baseline_claim_result.read_bytes()
        baseline_claim_document = json.loads(
            baseline_claim_result_bytes.decode("utf-8")
        )
        if (
            baseline_claim_document.get("all_pass") is not True
            or baseline_claim_document.get("checks_run") != CLAIM_AUDIT_CHECK_COUNT
        ):
            raise EvidenceError(
                "M176-E-COMMISSION",
                "baseline claim audit did not report every named check",
            )

        mutation_results: list[dict[str, Any]] = []
        killed = 0
        for index, mutation in enumerate(MUTATIONS, start=1):
            mutated = mutate_unique_full_line(BASE_FIXTURE_TEXT, mutation)
            fixture.write_text(mutated, encoding="utf-8", newline="\n")
            mutated_fixture = json.loads(mutated)
            classification = fixture_verdict(mutated_fixture)
            if mutation.expected_classification_change is not None:
                expected_before, expected_after = (
                    mutation.expected_classification_change
                )
                if (
                    baseline_verdict != expected_before
                    or classification != expected_after
                ):
                    raise EvidenceError(
                        "M176-E-COMMISSION",
                        f"{mutation.name}: classification {baseline_verdict}->{classification}, "
                        f"expected {expected_before}->{expected_after}",
                    )
            result_path = sandbox / f"mutation-{index:02d}-result.json"
            completed = run_fixture(Path(sys.executable), sandbox, fixture, result_path)
            stderr = completed.stderr.decode("utf-8", errors="replace")
            did_kill = (
                completed.returncode != 0
                and mutation.expected_error in stderr
                and not result_path.exists()
            )
            if not did_kill:
                raise EvidenceError(
                    "M176-E-COMMISSION",
                    f"{mutation.name} survived or failed for the wrong reason: "
                    f"exit={completed.returncode}, stderr={stderr!r}",
                )
            killed += 1
            mutation_results.append(
                {
                    "name": mutation.name,
                    "kind": mutation.kind,
                    "target": "fixture",
                    "anchor": mutation.anchor,
                    "anchor_count": 1,
                    "expected_error": mutation.expected_error,
                    "exit_code": completed.returncode,
                    "killed": did_kill,
                    "raw_output_sha256": sha256_bytes(
                        completed.stdout + b"\0" + completed.stderr
                    ),
                    "classification_before": baseline_verdict,
                    "classification_after": classification,
                }
            )
            fixture.write_text(BASE_FIXTURE_TEXT, encoding="utf-8", newline="\n")
            if sha256_file(fixture) != baseline_fixture_sha:
                raise EvidenceError(
                    "M176-E-COMMISSION-RESTORE",
                    f"{mutation.name}: fixture was not restored byte-identically",
                )

        claim_mutation_results: list[dict[str, Any]] = []
        claim_killed = 0
        for index, mutation in enumerate(CLAIM_AUDIT_MUTATIONS, start=1):
            mutated = mutate_unique_full_line(claim_audit_text, mutation)
            claim_audit.write_text(mutated, encoding="utf-8", newline="\n")
            result_path = sandbox / f"claim-mutation-{index:02d}-result.json"
            completed = run_claim_audit(
                Path(sys.executable),
                sandbox,
                claim_audit,
                result_path,
                repo_root,
                status_file,
            )
            stderr = completed.stderr.decode("utf-8", errors="replace")
            did_kill = (
                completed.returncode != 0
                and mutation.expected_error in stderr
                and not result_path.exists()
            )
            if not did_kill:
                raise EvidenceError(
                    "M176-E-COMMISSION",
                    f"{mutation.name} survived or failed for the wrong reason: "
                    f"exit={completed.returncode}, stderr={stderr!r}",
                )
            claim_killed += 1
            claim_mutation_results.append(
                {
                    "name": mutation.name,
                    "kind": mutation.kind,
                    "target": "claim-audit",
                    "anchor": mutation.anchor,
                    "anchor_count": 1,
                    "expected_error": mutation.expected_error,
                    "exit_code": completed.returncode,
                    "killed": did_kill,
                    "raw_output_sha256": sha256_bytes(
                        completed.stdout + b"\0" + completed.stderr
                    ),
                }
            )
            claim_audit.write_text(
                claim_audit_text,
                encoding="utf-8",
                newline="\n",
            )
            if sha256_file(claim_audit) != baseline_claim_sha:
                raise EvidenceError(
                    "M176-E-COMMISSION-RESTORE",
                    f"{mutation.name}: claim audit was not restored byte-identically",
                )

        policy_path = sandbox / ".gitattributes"
        policy_text = policy_path.read_text(encoding="utf-8")
        baseline_policy_sha = sha256_file(policy_path)
        policy_mutation_results: list[dict[str, Any]] = []
        policy_killed = 0
        for index, mutation in enumerate(CHECKOUT_POLICY_MUTATIONS, start=1):
            mutated = mutate_unique_full_line(policy_text, mutation)
            policy_path.write_text(mutated, encoding="utf-8", newline="\n")
            result_path = sandbox / f"policy-mutation-{index:02d}-result.json"
            completed = run_claim_audit(
                Path(sys.executable),
                sandbox,
                claim_audit,
                result_path,
                repo_root,
                status_file,
            )
            stderr = completed.stderr.decode("utf-8", errors="replace")
            did_kill = (
                completed.returncode != 0
                and mutation.expected_error in stderr
                and not result_path.exists()
            )
            if not did_kill:
                raise EvidenceError(
                    "M176-E-COMMISSION",
                    f"{mutation.name} survived or failed for the wrong reason: "
                    f"exit={completed.returncode}, stderr={stderr!r}",
                )
            policy_killed += 1
            policy_mutation_results.append(
                {
                    "name": mutation.name,
                    "kind": mutation.kind,
                    "target": ".gitattributes",
                    "anchor": mutation.anchor,
                    "anchor_count": 1,
                    "expected_error": mutation.expected_error,
                    "exit_code": completed.returncode,
                    "killed": did_kill,
                    "raw_output_sha256": sha256_bytes(
                        completed.stdout + b"\0" + completed.stderr
                    ),
                }
            )
            policy_path.write_text(policy_text, encoding="utf-8", newline="\n")
            if sha256_file(policy_path) != baseline_policy_sha:
                raise EvidenceError(
                    "M176-E-COMMISSION-RESTORE",
                    f"{mutation.name}: EOL policy was not restored byte-identically",
                )

        inert_text = mutate_unique_full_line(BASE_FIXTURE_TEXT, INERT)
        fixture.write_text(inert_text, encoding="utf-8", newline="\n")
        inert_result = sandbox / "inert-result.json"
        inert_run = run_fixture(Path(sys.executable), sandbox, fixture, inert_result)
        inert_survived = (
            inert_run.returncode == 0
            and inert_result.read_bytes() == baseline_result_bytes
            and fixture_verdict(json.loads(inert_text)) == baseline_verdict
        )
        if not inert_survived:
            raise EvidenceError(
                "M176-E-COMMISSION",
                "deliberately inert mutation changed evidence, verdict, or exit status",
            )
        fixture.write_text(BASE_FIXTURE_TEXT, encoding="utf-8", newline="\n")
        if sha256_file(fixture) != baseline_fixture_sha:
            raise EvidenceError(
                "M176-E-COMMISSION-RESTORE",
                "inert fixture was not restored byte-identically",
            )

        production_after = script_hashes()
        sandbox_after = {name: sha256_file(sandbox / name) for name in source_names}
        if production_before != production_after or sandbox_before != sandbox_after:
            raise EvidenceError(
                "M176-E-COMMISSION-RESTORE",
                "source files changed during mutation commissioning",
            )
        if (
            sha256_file(claim_audit_source) != claim_audit_source_sha
            or sha256_file(claim_audit) != baseline_claim_sha
        ):
            raise EvidenceError(
                "M176-E-COMMISSION-RESTORE",
                "claim-audit source or sandbox copy changed during commissioning",
            )
        status_sha_after = sha256_file(status_file)
        if status_sha_before != status_sha_after:
            raise EvidenceError(
                "M176-E-COMMISSION-RESTORE",
                "STATUS changed while proposal-only commissioning was running",
            )
        evidence_names = [
            "analysis.json",
            "builds.json",
            "claim-audit.json",
            "input-after.json",
            "input-before.json",
            "lineage.json",
            "provenance.json",
            "resource-estimate.json",
            "runs.json",
            "source-evidence.json",
            "verification.json",
        ]
        evidence_hashes = {
            name: sha256_file(evidence_dir / name) for name in evidence_names
        }
        report = {
            "schema": "strehl-m176-mutation-commission-v2",
            "all_pass": True,
            "counts": {
                "checks_run": (
                    1
                    + len(MUTATIONS)
                    + 1
                    + 1
                    + len(CLAIM_AUDIT_MUTATIONS)
                    + len(CHECKOUT_POLICY_MUTATIONS)
                ),
                "fixture_baseline_named_checks": len(
                    json.loads(baseline_result_bytes.decode("utf-8"))["checks"]
                ),
                "claim_audit_baseline_named_checks": baseline_claim_document[
                    "checks_run"
                ],
                "fixture_mutations_planted": len(MUTATIONS),
                "fixture_mutations_killed": killed,
                "claim_audit_mutations_planted": len(CLAIM_AUDIT_MUTATIONS),
                "claim_audit_mutations_killed": claim_killed,
                "checkout_policy_mutations_planted": len(CHECKOUT_POLICY_MUTATIONS),
                "checkout_policy_mutations_killed": policy_killed,
                "substantive_mutations_planted": len(MUTATIONS)
                + len(CLAIM_AUDIT_MUTATIONS)
                + len(CHECKOUT_POLICY_MUTATIONS),
                "substantive_mutations_killed": killed + claim_killed + policy_killed,
                "inert_controls_planted": 1,
                "inert_controls_survived": 1,
            },
            "baseline": {
                "verdict": baseline_verdict,
                "fixture_sha256": baseline_fixture_sha,
                "result_sha256": sha256_bytes(baseline_result_bytes),
                "raw_output_sha256": sha256_bytes(
                    baseline_run.stdout + b"\0" + baseline_run.stderr
                ),
            },
            "claim_audit_baseline": {
                "checks_run": baseline_claim_document["checks_run"],
                "claim_count": baseline_claim_document["claim_count"],
                "material_file_count": baseline_claim_document["material_file_count"],
                "claim_audit_sha256": baseline_claim_sha,
                "result_sha256": sha256_bytes(baseline_claim_result_bytes),
                "raw_output_sha256": sha256_bytes(
                    baseline_claim_run.stdout + b"\0" + baseline_claim_run.stderr
                ),
            },
            "fixture_mutations": mutation_results,
            "claim_audit_mutations": claim_mutation_results,
            "checkout_policy_mutations": policy_mutation_results,
            "substantive_mutations": [
                *mutation_results,
                *claim_mutation_results,
                *policy_mutation_results,
            ],
            "inert_control": {
                "name": INERT.name,
                "anchor": INERT.anchor,
                "anchor_count": 1,
                "survived": inert_survived,
                "verdict_before": baseline_verdict,
                "verdict_after": fixture_verdict(json.loads(inert_text)),
                "evidence_identical": inert_result.read_bytes()
                == baseline_result_bytes,
                "raw_output_sha256": sha256_bytes(
                    inert_run.stdout + b"\0" + inert_run.stderr
                ),
            },
            "binding": {
                "production_source_sha256_before": production_before,
                "production_source_sha256_after": production_after,
                "sandbox_source_sha256_before": sandbox_before,
                "sandbox_source_sha256_after": sandbox_after,
                "sources_restored_byte_identically": True,
                "fixture_restored_byte_identically_after_every_mutation": True,
                "claim_audit_restored_byte_identically_after_every_mutation": True,
                "eol_policy_restored_byte_identically_after_every_mutation": True,
                "eol_policy_sha256_before": baseline_policy_sha,
                "eol_policy_sha256_after": sha256_file(policy_path),
                "claim_audit_source_sha256_before": claim_audit_source_sha,
                "claim_audit_source_sha256_after": sha256_file(claim_audit_source),
                "status_sha256_before": status_sha_before,
                "status_sha256_after": status_sha_after,
                "status_untouched_during_commissioning": True,
                "evidence_sha256": evidence_hashes,
                "python_version": sys.version,
                "python_executable": str(Path(sys.executable)),
                "python_executable_sha256": sha256_file(Path(sys.executable)),
            },
        }
        report["binding"]["commission_payload_hash_scope"] = (
            "canonical JSON of this document before commission_payload_sha256 is added"
        )
        report["binding"]["commission_payload_sha256"] = json_digest(report)
        write_json_new(result_file, report)
        print(json.dumps(report["counts"], sort_keys=True))
        return 0
    except (EvidenceError, OSError, KeyError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
