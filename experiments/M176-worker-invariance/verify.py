from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import numpy as np

from analyze import array_difference, build_analysis, metadata_relation
from common import (
    APPROVED_INPUT,
    BOUND_SOURCE_NAMES,
    CHECKOUT_BOUND_RELATIVE_PATHS,
    EXPERIMENT_DIR,
    MAX_RESIDENT_BYTES,
    PRIVATE_SCRATCH,
    REPO_ROOT,
    EvidenceError,
    capture_manifest,
    ensure_private_path,
    guard_capture_path,
    json_digest,
    read_json,
    script_hashes,
    sha256_bytes,
    sha256_file,
    source_tree_manifest,
    write_json_new,
)


AFFECTED = "1a6fd10c94dcb4b780f6af78c46c62a156c39b71"
FIXED = "a97275817c58e164f75c7cd3d80ca99444a2a145"
REPAIR = "fc2abb499126a56302de7f21f527de5613be34e7"
EXPECTED_BASE_RUNS = [
    "affected-w1",
    "affected-w2",
    "affected-w1-repeat",
    "fixed-w1",
    "fixed-w2",
]
AUDIT_REVISION = "69bdacafbb4a49a198e9f430590033e8a5ed25a2"
EXACT_NORMATIVE_REQUIREMENT = (
    "Every scored, cached, or hash-frozen render MUST bind workers_requested, "
    "workers_resolved, and a versioned reduction_lattice_id containing the exact "
    "logical frame partitions and ordered reduction topology to both its whole-file "
    "and canonical-pixel SHA-256, and MUST refuse comparison or reuse on any mismatch."
)
EXACT_STATUS_REPLACEMENT = (
    "**M176 narrows the blast radius.** The affected Pyramid backend made final-render "
    "bytes depend on its logical worker decomposition, but not every repository hash "
    "is a Pyramid final-render hash. The historical M139 cross-worker FAIL; pre-merge "
    "M8-R and M165 checks; M164 witness and blocked checker; estimator-era results; "
    "M117 warp-cache clearance; and M175 transfer sentinel survive. The shipping "
    "Scale + Catmull-Rom freeze and M130 equality at explicit W=2 remain valid at their "
    "recorded worker topology, not as cross-worker determinism evidence. V-MOTE's "
    "wrong-map/OFF "
    "equality and DELIVER-V6's generalized determinism wording must be conditioned on "
    "a common worker lattice; M8-O v1.4 and the metadata-only `--exposure` whole-file "
    "difference were already superseded. M-COVER-BORDER's mixed-history profile is "
    "the one confirmed worker-caused false difference, superseded by its pinned-worker "
    "rerun. V-ENVSURF's N=3 W=3/W=1 equality is an exact observation and a confirmed "
    "false-agreement surface if generalized, not proof of invariance. M-PHASE0-SPLIT's "
    "fixed-W=1 null preserves its KILL verdict; BUILD-SPEED's W=1/2/4/8 treatment is "
    "valid without admitting absolute timing; ORCH's 26 equal V3/V4 files do not prove "
    "two runs of one binary; and V-NEVERWORSE's shipping-master rerender identity "
    "survives only within its common unresolved topology. SCORECARD-BASELINE remains "
    "UNMEASURED, render_all/gallery/finalpass resume paths remain unsealed, and M172's "
    "unit worker contract is not a full final-TIFF ladder.\n\n"
    "Exact equal bytes remain exact observations; they do not prove cross-worker "
    "determinism without matching requested/resolved workers and reduction lattice. "
    "V-ENVSURF confirms that equal bytes can be a false-agreement surface when "
    "generalized, while no cancellation of an independent scientific treatment by "
    "worker rounding was measured; stale-render reuse is a separate material "
    "false-agreement risk. "
    + EXACT_NORMATIVE_REQUIREMENT
    + " The M172 repair was already present at audit revision "
    "`69bdacafbb4a49a198e9f430590033e8a5ed25a2`; M176 lands no renderer repair."
)
CLASSIFICATION_ENUM = (
    "CONDITIONED_UNRECORDED",
    "IRRELEVANT_PREMERGE",
    "SUPERSEDED",
    "SURVIVES_SAME_WORKER_ONLY",
    "SURVIVES_UNCONDITIONALLY",
    "VOID_AS_DETERMINISM_EVIDENCE",
)
WORKER_PROVENANCE_ENUM = (
    "DECLARED_SWEEP",
    "DEFAULT_SANITIZED_COMMON",
    "ESTIMATOR_NOT_PYRAMID",
    "EXPLICIT_PIN",
    "EXTERNAL_SINGLE_THREAD",
    "FUTURE_CONTRACT_UNBOUND",
    "INHERITED_UNRECOVERABLE",
    "MIXED_HISTORY_CONFIRMED",
    "NOT_APPLICABLE_PREMERGE",
    "RECORDED_NOT_ASSERTED",
    "SAME_PROCESS_COMMON_DEFAULT",
)
EXPOSURE_ENUM = (
    "CONFIRMED",
    "MATERIAL",
    "NONE",
    "NOT_OBSERVED",
    "POSSIBLE",
    "SEPARATE_NON_WORKER",
)
REQUIRED_CLAIM_IDS = (
    "M139",
    "M8-R",
    "M8-O",
    "M165",
    "M164-WITNESS",
    "M164-FUTURE-CANDIDATE",
    "M164-BLOCKED-CHECKER",
    "SHIPPING-SCALE-CATMULL-ROM-BYTE-FREEZE",
    "M130",
    "V-MOTE-DUST-OFF",
    "M-COVER-BORDER",
    "PINNED-WORKER-PYRAMID-GROUPS",
    "M-PHASE0",
    "SAME-PROCESS-DEFAULT-AB-GROUPS",
    "DELIVER-V6",
    "ESTIMATOR-PREMERGE-GROUPS",
    "METADATA-ONLY-EXPOSURE",
    "WARP-CACHE-M117",
    "M175",
    "SCORED-RUN-MANIFEST-M153",
    "FINALPASS-CACHE",
    "M162",
    "V-ENVSURF-WORKERS",
    "M-PHASE0-SPLIT",
    "BUILD-SPEED",
    "ORCH-SHIP-V3-V4",
    "V-NEVERWORSE-SHIP-RENDER",
    "SCORECARD-BASELINE",
    "UNSEALED-RENDER-RESUME-PATHS",
    "M172-UNIT-WORKER-CONTRACT",
)
EXPECTED_CLAIM_RULINGS = {
    "M139": (("SURVIVES_UNCONDITIONALLY",), "DECLARED_SWEEP"),
    "M8-R": (("IRRELEVANT_PREMERGE",), "EXPLICIT_PIN"),
    "M8-O": (("SUPERSEDED",), "EXPLICIT_PIN"),
    "M165": (("IRRELEVANT_PREMERGE",), "NOT_APPLICABLE_PREMERGE"),
    "M164-WITNESS": (("IRRELEVANT_PREMERGE",), "NOT_APPLICABLE_PREMERGE"),
    "M164-FUTURE-CANDIDATE": (
        ("CONDITIONED_UNRECORDED",),
        "FUTURE_CONTRACT_UNBOUND",
    ),
    "M164-BLOCKED-CHECKER": (
        ("SURVIVES_UNCONDITIONALLY",),
        "NOT_APPLICABLE_PREMERGE",
    ),
    "SHIPPING-SCALE-CATMULL-ROM-BYTE-FREEZE": (
        ("SURVIVES_SAME_WORKER_ONLY", "VOID_AS_DETERMINISM_EVIDENCE"),
        "RECORDED_NOT_ASSERTED",
    ),
    "M130": (("SURVIVES_SAME_WORKER_ONLY",), "EXPLICIT_PIN"),
    "V-MOTE-DUST-OFF": (
        ("CONDITIONED_UNRECORDED", "SURVIVES_SAME_WORKER_ONLY"),
        "INHERITED_UNRECOVERABLE",
    ),
    "M-COVER-BORDER": (("SUPERSEDED",), "MIXED_HISTORY_CONFIRMED"),
    "PINNED-WORKER-PYRAMID-GROUPS": (
        ("SURVIVES_SAME_WORKER_ONLY",),
        "EXPLICIT_PIN",
    ),
    "M-PHASE0": (("SURVIVES_UNCONDITIONALLY",), "DECLARED_SWEEP"),
    "SAME-PROCESS-DEFAULT-AB-GROUPS": (
        ("SURVIVES_SAME_WORKER_ONLY",),
        "SAME_PROCESS_COMMON_DEFAULT",
    ),
    "DELIVER-V6": (
        ("CONDITIONED_UNRECORDED", "VOID_AS_DETERMINISM_EVIDENCE"),
        "INHERITED_UNRECOVERABLE",
    ),
    "ESTIMATOR-PREMERGE-GROUPS": (
        ("SURVIVES_UNCONDITIONALLY",),
        "ESTIMATOR_NOT_PYRAMID",
    ),
    "METADATA-ONLY-EXPOSURE": (
        ("SUPERSEDED", "VOID_AS_DETERMINISM_EVIDENCE"),
        "ESTIMATOR_NOT_PYRAMID",
    ),
    "WARP-CACHE-M117": (
        ("IRRELEVANT_PREMERGE", "SURVIVES_UNCONDITIONALLY"),
        "NOT_APPLICABLE_PREMERGE",
    ),
    "M175": (("SURVIVES_UNCONDITIONALLY",), "EXTERNAL_SINGLE_THREAD"),
    "SCORED-RUN-MANIFEST-M153": (
        ("CONDITIONED_UNRECORDED",),
        "FUTURE_CONTRACT_UNBOUND",
    ),
    "FINALPASS-CACHE": (
        ("CONDITIONED_UNRECORDED",),
        "FUTURE_CONTRACT_UNBOUND",
    ),
    "M162": (
        ("CONDITIONED_UNRECORDED",),
        "FUTURE_CONTRACT_UNBOUND",
    ),
    "V-ENVSURF-WORKERS": (
        ("SURVIVES_UNCONDITIONALLY", "VOID_AS_DETERMINISM_EVIDENCE"),
        "RECORDED_NOT_ASSERTED",
    ),
    "M-PHASE0-SPLIT": (
        ("SURVIVES_SAME_WORKER_ONLY", "SUPERSEDED"),
        "EXPLICIT_PIN",
    ),
    "BUILD-SPEED": (
        ("SURVIVES_UNCONDITIONALLY", "SURVIVES_SAME_WORKER_ONLY"),
        "DECLARED_SWEEP",
    ),
    "ORCH-SHIP-V3-V4": (
        ("SURVIVES_SAME_WORKER_ONLY", "VOID_AS_DETERMINISM_EVIDENCE"),
        "RECORDED_NOT_ASSERTED",
    ),
    "V-NEVERWORSE-SHIP-RENDER": (
        ("SURVIVES_SAME_WORKER_ONLY",),
        "DEFAULT_SANITIZED_COMMON",
    ),
    "SCORECARD-BASELINE": (
        ("SURVIVES_SAME_WORKER_ONLY", "CONDITIONED_UNRECORDED"),
        "RECORDED_NOT_ASSERTED",
    ),
    "UNSEALED-RENDER-RESUME-PATHS": (
        ("CONDITIONED_UNRECORDED",),
        "FUTURE_CONTRACT_UNBOUND",
    ),
    "M172-UNIT-WORKER-CONTRACT": (
        ("SURVIVES_UNCONDITIONALLY",),
        "DECLARED_SWEEP",
    ),
}
EXPECTED_GROUP_MEMBERS = {
    "PINNED-WORKER-PYRAMID-GROUPS": (
        "M-FLATNULL",
        "M8-v2",
        "M142",
        "BUILD-RESAMP",
        "V-ca",
        "V-chroma2",
        "BUILD-CHROMA",
    ),
    "M-PHASE0": (
        "W=1/2/4/8/16 scaling",
        "fixed-W queue pairs",
    ),
    "SAME-PROCESS-DEFAULT-AB-GROUPS": (
        "M126",
        "BUILD-BLEND",
        "soft-gate controls",
        "band-floor controls",
        "M-COVER-NATIVE",
    ),
    "ESTIMATOR-PREMERGE-GROUPS": (
        "M2",
        "M18",
        "M95",
        "M97",
        "M100",
        "M105",
        "M107",
        "M109",
        "M111",
        "M114",
        "M116",
        "M117",
        "M121",
        "M122",
        "M124",
    ),
}
REQUIRED_MATERIAL_PATHS = tuple(
    sorted(
        (
            "AGENTS.md",
            "crates/strehl-cli/src/align_cmd.rs",
            "crates/strehl-cli/src/bin/strehl-common-input.rs",
            "crates/strehl-cli/src/main.rs",
            "crates/strehl-cli/src/merge_cmd.rs",
            "crates/strehl-cli/src/stack.rs",
            "crates/strehl-cli/tests/byte-freeze.rs",
            "crates/strehl-cli/tests/byte-freezes.tsv",
            "crates/strehl-cli/tests/data/coffee-bean-20.warpmap.txt",
            "crates/strehl-core/src/merge.rs",
            "crates/strehl-core/src/pyramid.rs",
            "crates/strehl-core/src/warpmap.rs",
            "crates/strehl-raw/src/common_tiff.rs",
            "docs/STATUS.md",
            "docs/proposals/2026-09-sota-scorecard.md",
            "docs/research/BUILD-CHROMA.md",
            "docs/research/BUILD-DEFECT.md",
            "docs/research/DELIVER-V6.md",
            "docs/research/M-COVER-BORDER.md",
            "docs/research/M-COVER-NATIVE.md",
            "docs/research/M-FLATNULL.md",
            "docs/research/M-PHASE0-PIPE.md",
            "docs/research/M-PHASE0-SPLIT.md",
            "docs/research/M108-freeze-test.md",
            "docs/research/M117-cache-audit.md",
            "docs/research/M124-resampler-flag.md",
            "docs/research/M126-composite.md",
            "docs/research/M130-crop-early.md",
            "docs/research/M136-m8-census-groundtruth.md",
            "docs/research/M136-m8-passability.md",
            "docs/research/M139-m12-campaign.md",
            "docs/research/M162-noise-regression.md",
            "docs/research/M164-dominance-manifest.md",
            "docs/research/M164-reference-dominance.md",
            "docs/research/M165-common-input.md",
            "docs/research/M166-reference-dominance-rehearsal.md",
            "docs/research/M175-fork-arm.md",
            "docs/research/M18-merge-implemented.md",
            "docs/research/M2-baseline-skeleton.md",
            "docs/research/M8-overshoot.md",
            "docs/research/M97n-cache-key.md",
            "docs/research/ORCH-veiling.md",
            "docs/research/SCORECARD-BASELINE.md",
            "docs/research/SYNTHESIS.md",
            "docs/research/V-ENVSURF.md",
            "docs/research/V-MOTE.md",
            "docs/research/V-ca.md",
            "docs/research/V-chroma2.md",
            "experiments/BUILD-RESAMP/render6-h2h.ps1",
            "experiments/BUILD-SPEED/REPORT.md",
            "experiments/BUILD-SPEED/worker_sweep.ps1",
            "experiments/DELIVER-V6/render.ps1",
            "experiments/M-COVER-BORDER/load_render.py",
            "experiments/M-PHASE0-PIPE/measure.py",
            "experiments/M-PHASE0-SPLIT/out/real-109/run.json",
            "experiments/M126-default-audit/composite/run_arms.ps1",
            "experiments/M142-m8o-execute/run-clamped-m8o.ps1",
            "experiments/M153-m11-harness/campaign-template.json",
            "experiments/M153-m11-harness/m11_harness.py",
            "experiments/M153-m11-harness/quality-manifest-template.json",
            "experiments/M164-dominance-manifest/production-manifest-v1.freeze.json",
            "experiments/M164-dominance-manifest/production-manifest-v1.json",
            "experiments/M164-dominance-manifest/reader_core.py",
            "experiments/M165-common-input/commission.py",
            "experiments/M165-common-input/consumer_gate.py",
            "experiments/M172-worker-memory/measure_memory.py",
            "experiments/M175-fork-arm/PRE-RENDER-FREEZE.json",
            "experiments/M175-fork-arm/RUN-MANIFEST.json",
            "experiments/M162-noise-regression/render.ps1",
            "experiments/M8-overshoot/run.ps1",
            "experiments/ORCH-drift-check/intervrender.ps1",
            "experiments/SCORECARD-BASELINE/out/RENDER-MANIFEST.json",
            "experiments/SCORECARD-BASELINE/out/RUN-MANIFEST.json",
            "experiments/SCORECARD-BASELINE/render.py",
            "experiments/V-NEVERWORSE/RESULT.md",
            "experiments/V-NEVERWORSE/vn_lib.py",
            "experiments/cover-default/m8-v2/run_v2.ps1",
            "experiments/m12-scorecard/m12-harness.py",
            "scripts/check-defaults.py",
            "scripts/finalpass.ps1",
            "scripts/gallery-ab.ps1",
            "scripts/render_all.ps1",
        )
    )
)
SEARCH_SOURCE_PATHS = (
    ":(glob)docs/research/*.md",
    ":(glob)experiments/**/*.md",
    ":(glob)experiments/**/*.py",
    ":(glob)experiments/**/*.ps1",
    ":(glob)experiments/**/*.json",
    ":(glob)crates/strehl-cli/tests/**/*.rs",
    ":(glob)crates/strehl-cli/tests/**/*.tsv",
    "crates/strehl-cli/src/merge_cmd.rs",
    "crates/strehl-cli/src/stack.rs",
    "crates/strehl-core/src/pyramid.rs",
    ":(exclude,glob)experiments/**/out/**",
    ":(exclude,glob)experiments/**/results/**",
    ":(exclude,glob)experiments/**/banked/**",
    ":(exclude,glob)experiments/**/artifacts/**",
    ":(exclude,glob)experiments/**/logs/**",
    ":(exclude,glob)experiments/M139*/**",
    ":(exclude,glob)experiments/**/M139*/**",
)
SEARCH_SCRIPT_PATHS = (":(glob)scripts/*.ps1",)
SEARCH_QUERIES = (
    (
        "worker-control-and-topology",
        (
            r"STREHL_PYRAMID_WORKERS|--chunks(=|[[:space:]])|worker[- ]count|"
            r"worker threads?|worker sweep|worker ladder|reduction order|"
            r"canonical chunks?|logical frame partitions?"
        ),
        SEARCH_SOURCE_PATHS,
    ),
    (
        "worker-near-byte-bit-freeze-tiff-output-pixel-hash",
        (
            r"(worker|chunks).{0,100}(byte|bit|freeze|hash|TIFF|output|pixel)|"
            r"(byte|bit|freeze|hash|TIFF|output|pixel).{0,100}(worker|chunks)"
        ),
        SEARCH_SOURCE_PATHS,
    ),
    (
        "resume-cache-skip-scripts",
        (
            r"(Test-Path|Length|\.ok).{0,120}(tif|output|render)|"
            r"(tif|output|render).{0,120}(Test-Path|Length|\.ok)"
        ),
        SEARCH_SCRIPT_PATHS,
    ),
)
CLAIM_AUDIT_CHECK_COUNT = 11
EXPECTED_GITATTRIBUTES = (
    "*.py text eol=lf",
    "*.json text eol=lf",
    "*.md text eol=lf",
    ".gitignore text eol=lf",
    ".gitattributes text eol=lf",
)
SEARCH_COVERAGE_TERMS = (
    "STREHL_PYRAMID_WORKERS",
    "legacy --chunks",
    "worker-count and worker-thread controls",
    "reduction-order and canonical-chunk language",
    "byte/bit identity and byte freezes near worker controls",
    "TIFF/output/pixel hashes near worker controls",
    "resume/cache TIFF skips in repository scripts",
)


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise EvidenceError(code, detail)


def validate_group_members(claims: list[dict[str, Any]]) -> None:
    declared_group_ids = {claim["id"] for claim in claims if "group_members" in claim}
    require(
        declared_group_ids == set(EXPECTED_GROUP_MEMBERS),
        "M176-E-CLAIM-GROUP-MEMBERS",
        "claims declaring group_members do not match the explicit contract set",
    )
    by_id = {claim["id"]: claim for claim in claims}
    for claim_id, expected_members in EXPECTED_GROUP_MEMBERS.items():
        actual_members = by_id[claim_id]["group_members"]
        require(
            isinstance(actual_members, list)
            and tuple(actual_members) == expected_members,
            "M176-E-CLAIM-GROUP-MEMBERS",
            f"{claim_id}: group_members differs from the exact declared tuple",
        )


def fixture_verdict(fixture: dict[str, Any]) -> str:
    a1 = np.asarray(fixture["affected_w1_pixels"], dtype=np.uint16)
    a2 = np.asarray(fixture["affected_w2_pixels"], dtype=np.uint16)
    ar = np.asarray(fixture["affected_repeat_pixels"], dtype=np.uint16)
    f1 = np.asarray(fixture["fixed_w1_pixels"], dtype=np.uint16)
    f2 = np.asarray(fixture["fixed_w2_pixels"], dtype=np.uint16)
    if not np.array_equal(a1, ar):
        return "OTHER_UNRESOLVED"
    if np.array_equal(a1, a2):
        return "NOT_REPRODUCED"
    if not np.array_equal(f1, f2):
        return "OTHER_UNRESOLVED"
    if not fixture["mechanism_preconditions"]:
        return "OTHER_UNRESOLVED"
    return "REDUCTION_ORDER"


def validate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    guard_capture_path(fixture["input_path"])
    require(
        fixture["source_affected_current"]
        == fixture["source_affected_expected"]
        == AFFECTED,
        "M176-E-SOURCE",
        "affected source provenance mismatch",
    )
    require(
        fixture["source_fixed_current"] == fixture["source_fixed_expected"] == FIXED,
        "M176-E-SOURCE",
        "fixed source provenance mismatch",
    )
    require(
        fixture["lineage_parent_ok"] is True,
        "M176-E-LINEAGE",
        "repair parent/descendant relation is false",
    )
    require(
        fixture["binary_sha256_current"] == fixture["binary_sha256_expected"],
        "M176-E-BINARY",
        "binary SHA-256 provenance mismatch",
    )
    require(
        fixture["worker_records"]
        == {
            "affected-w1": 1,
            "affected-w2": 2,
            "affected-w1-repeat": 1,
            "fixed-w1": 1,
            "fixed-w2": 2,
        },
        "M176-E-WORKER",
        "worker provenance does not match the registered arms",
    )
    require(
        fixture["run_root_preexisting"] is False
        and fixture["output_preexisting"] is False
        and fixture["output_created_after_launch"] is True,
        "M176-E-STALE",
        "stale or pre-existing output was accepted",
    )

    affected_w1 = np.asarray(fixture["affected_w1_pixels"], dtype=np.uint16)
    affected_w2 = np.asarray(fixture["affected_w2_pixels"], dtype=np.uint16)
    affected_repeat = np.asarray(fixture["affected_repeat_pixels"], dtype=np.uint16)
    fixed_w1 = np.asarray(fixture["fixed_w1_pixels"], dtype=np.uint16)
    fixed_w2 = np.asarray(fixture["fixed_w2_pixels"], dtype=np.uint16)
    require(
        np.array_equal(affected_w1, affected_repeat),
        "M176-E-REPEAT",
        "affected same-worker repeat changed pixels",
    )
    require(
        not np.array_equal(affected_w1, affected_w2),
        "M176-E-CROSS",
        "affected cross-worker output unexpectedly became pixel-identical",
    )
    require(
        np.array_equal(fixed_w1, fixed_w2),
        "M176-E-FIXED",
        "fixed build changed pixels across workers",
    )

    meta_a = np.asarray(fixture["metadata_a_pixels"], dtype=np.uint16)
    meta_b = np.asarray(fixture["metadata_b_pixels"], dtype=np.uint16)
    meta_relation = metadata_relation(
        fixture["metadata_a_file_sha256"],
        fixture["metadata_b_file_sha256"],
        _fixture_pixel_token(meta_a),
        _fixture_pixel_token(meta_b),
    )
    require(
        meta_relation == fixture["metadata_expected_relation"] == "FILE_METADATA_ONLY",
        "M176-E-METADATA",
        f"metadata-only distinction failed: {meta_relation}",
    )

    measured = array_difference(affected_w1, affected_w2)
    expected = fixture["expected_difference"]
    require(
        measured["signed_delta_histogram"] == expected["signed_delta_histogram"]
        and measured["per_channel_differing_samples"]
        == expected["per_channel_differing_samples"]
        and measured["differing_channel_samples"]
        == expected["differing_channel_samples"]
        and measured["differing_pixels_any_channel"]
        == expected["differing_pixels_any_channel"]
        and measured["max_absolute_dn16"] == expected["max_absolute_dn16"]
        and math.isclose(
            measured["max_relative_per_pixel_channel"],
            expected["max_relative_per_pixel_channel"],
            rel_tol=0.0,
            abs_tol=1e-15,
        ),
        "M176-E-MAGNITUDE",
        "signed delta or magnitude computation is wrong",
    )
    require(
        fixture["mechanism_preconditions"] is True,
        "M176-E-MECHANISM",
        "mechanism precondition is absent",
    )
    require(
        fixture["source_anchor_count"] == 1,
        "M176-E-SOURCE-ANCHOR",
        "source mutation anchor is not unique",
    )
    require(
        fixture["input_manifest_before_sha256"]
        == fixture["input_manifest_after_sha256"],
        "M176-E-INPUT-MUTATION",
        "source before/after manifest differs",
    )
    environment = fixture["renderer_environment"]
    require(
        all(
            name in environment and environment[name] is not None
            for name in fixture["required_non_null_environment"]
        ),
        "M176-E-ENV",
        "required renderer environment is missing",
    )
    require(
        fixture["settings_invariant"] is True,
        "M176-E-SETTINGS",
        "a non-worker setting changed between arms",
    )
    require(
        fixture["secondary_decoder_equal"] is True,
        "M176-E-DECODE-DISAGREE",
        "independent decoder paths disagree",
    )
    require(
        fixture["output_binding_ok"] is True,
        "M176-E-OUTPUT-BINDING",
        "output hash is not bound to its run record",
    )
    require(
        fixture["peak_resident_bytes"] <= MAX_RESIDENT_BYTES,
        "M176-E-RESOURCE",
        "resident memory exceeded the stop rule",
    )
    verdict = fixture_verdict(fixture)
    require(
        verdict == fixture["expected_verdict"],
        "M176-E-VERDICT",
        f"expected {fixture['expected_verdict']}, derived {verdict}",
    )
    return {
        "schema": "strehl-m176-fixture-verification-v1",
        "verdict": verdict,
        "checks": [
            "input-provenance",
            "source-and-lineage-provenance",
            "binary-provenance",
            "worker-provenance",
            "fresh-output",
            "same-worker-determinism",
            "affected-cross-worker-difference",
            "fixed-worker-invariance",
            "tiff-metadata-vs-pixels",
            "magnitude-and-sign",
            "mechanism-precondition",
            "unique-source-anchor",
            "source-before-after",
            "environment-completeness",
            "settings-invariance",
            "independent-decoder",
            "output-binding",
            "resource-stop-rule",
            "verdict",
        ],
    }


def _fixture_pixel_token(value: np.ndarray) -> str:
    return sha256_file_token(np.ascontiguousarray(value).tobytes())


def sha256_file_token(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


class CheckRunner:
    def __init__(self) -> None:
        self.results: list[dict[str, str]] = []

    def run(self, name: str, function: Callable[[], None]) -> None:
        function()
        self.results.append({"name": name, "status": "PASS"})


def git_output(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    require(completed.returncode == 0, "M176-E-GIT", completed.stderr.strip())
    return completed.stdout.strip()


def git_output_at(repo_root: Path, args: list[str], code: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(
        completed.returncode == 0,
        code,
        completed.stderr.strip() or f"git {' '.join(args)} failed",
    )
    return completed.stdout.strip()


def git_bytes_at(
    repo_root: Path,
    args: list[str],
    code: str,
    detail: str,
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
    )
    require(completed.returncode == 0, code, detail)
    return completed.stdout


def require_repo_relative_path(value: Any, context: str) -> str:
    require(
        isinstance(value, str) and bool(value),
        "M176-E-CLAIM-PATH",
        f"{context}: path is not a nonempty string",
    )
    require(
        "\\" not in value and ":" not in value,
        "M176-E-CLAIM-PATH",
        f"{context}: path is not repository-relative POSIX form",
    )
    parsed = PurePosixPath(value)
    require(
        not parsed.is_absolute()
        and ".." not in parsed.parts
        and "." not in parsed.parts
        and str(parsed) == value,
        "M176-E-CLAIM-PATH",
        f"{context}: path escapes or is not canonical: {value!r}",
    )
    return value


def git_blob_at(repo_root: Path, revision: str, path: str) -> bytes:
    spec = f"{revision}:{path}"
    object_type = (
        git_bytes_at(
            repo_root,
            ["cat-file", "-t", spec],
            "M176-E-CLAIM-EVIDENCE-PATH",
            f"{spec}: cited path does not resolve to a Git object",
        )
        .decode("ascii", errors="strict")
        .strip()
    )
    require(
        object_type == "blob",
        "M176-E-CLAIM-EVIDENCE-PATH",
        f"{spec}: cited path resolves as {object_type!r}, not a blob",
    )
    return git_bytes_at(
        repo_root,
        ["cat-file", "blob", spec],
        "M176-E-CLAIM-EVIDENCE-PATH",
        f"{spec}: cited blob could not be read",
    )


def validate_evidence_citations(
    claims: list[dict[str, Any]],
    repo_root: Path,
    inventory_paths: set[str],
) -> dict[str, int]:
    blob_cache: dict[str, str] = {}
    evidence_count = 0
    for claim in claims:
        evidence = claim["evidence"]
        require(
            isinstance(evidence, list) and bool(evidence),
            "M176-E-CLAIM-ANCHOR",
            f"{claim['id']}: no evidence anchors",
        )
        for index, item in enumerate(evidence):
            context = f"{claim['id']}.evidence[{index}]"
            path = require_repo_relative_path(item["path"], context)
            anchor = item["anchor"]
            require(
                item["revision"] == AUDIT_REVISION
                and item["anchor_kind"] in {"content", "heading", "semantic", "symbol"}
                and isinstance(anchor, str)
                and bool(anchor.strip())
                and "line" not in item
                and re.fullmatch(
                    r"\s*(?:(?:line|lines)\s+)?\d+(?:[-:]\d+)?\s*",
                    anchor,
                    flags=re.IGNORECASE,
                )
                is None,
                "M176-E-CLAIM-ANCHOR",
                f"{context}: bare line number or absent exact anchor",
            )
            if path not in blob_cache:
                payload = git_blob_at(repo_root, AUDIT_REVISION, path)
                try:
                    blob_cache[path] = payload.decode("utf-8", errors="strict")
                except UnicodeDecodeError as error:
                    raise EvidenceError(
                        "M176-E-CLAIM-EVIDENCE-DECODE",
                        f"{AUDIT_REVISION}:{path}: UTF-8 decode failed: {error}",
                    ) from error
            count = blob_cache[path].count(anchor)
            require(
                count == 1,
                "M176-E-CLAIM-EVIDENCE-ANCHOR",
                f"{context}: exact anchor occurs {count} times in {AUDIT_REVISION}:{path}",
            )
            require(
                path in inventory_paths,
                "M176-E-CLAIM-PATH",
                f"{context}: cited path is absent from material inventory",
            )
            evidence_count += 1
    return {
        "evidence_items_resolved": evidence_count,
        "unique_blobs_decoded": len(blob_cache),
    }


def revision_search(repo_root: Path) -> tuple[dict[str, list[str]], list[str]]:
    by_query: dict[str, list[str]] = {}
    union: set[str] = set()
    prefix = f"{AUDIT_REVISION}:"
    for name, pattern, pathspecs in SEARCH_QUERIES:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "grep",
                "-Iil",
                "-E",
                "-e",
                pattern,
                AUDIT_REVISION,
                "--",
                *pathspecs,
            ],
            capture_output=True,
            check=False,
        )
        require(
            completed.returncode in {0, 1},
            "M176-E-CLAIM-SEARCH",
            completed.stderr.decode("utf-8", errors="replace").strip()
            or f"{name}: revision-bound Git search failed",
        )
        try:
            output = completed.stdout.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise EvidenceError(
                "M176-E-CLAIM-SEARCH",
                f"{name}: Git search path output is not UTF-8: {error}",
            ) from error
        paths: set[str] = set()
        for line in output.splitlines():
            require(
                line.startswith(prefix),
                "M176-E-CLAIM-SEARCH",
                f"{name}: unexpected Git search result {line!r}",
            )
            path = require_repo_relative_path(line[len(prefix) :], f"{name}.result")
            paths.add(path)
        by_query[name] = sorted(paths)
        union.update(paths)
    return by_query, sorted(union)


def _run_private_git(
    cwd: Path,
    args: list[str],
    code: str = "M176-E-CHECKOUT-EOL",
) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        code,
        completed.stderr.decode("utf-8", errors="replace").strip()
        or f"private Git command failed: {' '.join(args)}",
    )
    return completed.stdout


def _require_lf_attributes(repo: Path, paths: tuple[str, ...]) -> None:
    output = _run_private_git(repo, ["check-attr", "text", "eol", "--", *paths])
    observed: dict[tuple[str, str], str] = {}
    for raw_line in output.decode("utf-8", errors="strict").splitlines():
        path, attribute, value = raw_line.split(": ", 2)
        observed[(path.replace("\\", "/"), attribute)] = value
    for path in paths:
        require(
            observed.get((path, "text")) == "set"
            and observed.get((path, "eol")) == "lf",
            "M176-E-CHECKOUT-EOL",
            f"{path}: expected Git attributes text=set and eol=lf",
        )


def verify_checkout_stability(
    experiment_dir: Path,
    checkout_contract: dict[str, Any],
) -> dict[str, Any]:
    bound_paths = tuple(checkout_contract["bound_paths"])
    require(
        checkout_contract["policy_file"] == ".gitattributes"
        and checkout_contract["core_autocrlf"] is True
        and tuple(checkout_contract["required_policy_lines"]) == EXPECTED_GITATTRIBUTES
        and bound_paths == CHECKOUT_BOUND_RELATIVE_PATHS
        and set(BOUND_SOURCE_NAMES).issubset(bound_paths),
        "M176-E-CHECKOUT-EOL",
        "checkout-stability contract or bound path set drifted",
    )
    policy = (experiment_dir / ".gitattributes").read_text(
        encoding="utf-8",
        errors="strict",
    )
    require(
        tuple(policy.splitlines()) == EXPECTED_GITATTRIBUTES
        and policy.endswith("\n")
        and "\r" not in policy,
        "M176-E-CHECKOUT-EOL",
        ".gitattributes is not the exact LF worktree policy",
    )
    before: dict[str, str] = {}
    for index, relative in enumerate(bound_paths):
        path_text = require_repo_relative_path(
            relative, f"checkout.bound_paths[{index}]"
        )
        path = experiment_dir / Path(path_text)
        require(
            path.is_file(),
            "M176-E-CHECKOUT-EOL",
            f"checkout-bound file is missing: {path_text}",
        )
        payload = path.read_bytes()
        require(
            b"\r" not in payload,
            "M176-E-CHECKOUT-EOL",
            f"checkout-bound file is not LF-only: {path_text}",
        )
        before[path_text] = sha256_bytes(payload)

    PRIVATE_SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="m176-checkout-",
        dir=PRIVATE_SCRATCH,
    ) as scratch_text:
        scratch = Path(scratch_text)
        source = scratch / "source"
        clone = scratch / "clone"
        source.mkdir()
        for relative in bound_paths:
            destination = source / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(experiment_dir / Path(relative), destination)
        _run_private_git(source, ["init", "--quiet"])
        _run_private_git(source, ["config", "core.autocrlf", "true"])
        _run_private_git(source, ["config", "user.name", "M176 Checkout Verifier"])
        _run_private_git(source, ["config", "user.email", "m176@invalid.example"])
        _require_lf_attributes(source, bound_paths)
        _run_private_git(source, ["add", "--all"])
        _run_private_git(source, ["commit", "--quiet", "-m", "M176 checkout fixture"])
        tracked = (
            _run_private_git(source, ["ls-files"])
            .decode("utf-8", errors="strict")
            .splitlines()
        )
        require(
            tuple(tracked) == bound_paths,
            "M176-E-CHECKOUT-EOL",
            "private source repository did not track exactly the bound M176 tree",
        )
        completed = subprocess.run(
            [
                "git",
                "-c",
                "core.autocrlf=true",
                "clone",
                "--quiet",
                str(source),
                str(clone),
            ],
            capture_output=True,
            check=False,
        )
        require(
            completed.returncode == 0,
            "M176-E-CHECKOUT-EOL",
            completed.stderr.decode("utf-8", errors="replace").strip()
            or "private core.autocrlf=true clone failed",
        )
        _run_private_git(clone, ["config", "core.autocrlf", "true"])
        _require_lf_attributes(clone, bound_paths)
        after = {
            relative: sha256_file(clone / Path(relative)) for relative in bound_paths
        }
        require(
            after == before,
            "M176-E-CHECKOUT-EOL",
            "core.autocrlf=true checkout changed one or more bound M176 bytes",
        )
    return {
        "bound_path_count": len(bound_paths),
        "core_autocrlf": True,
        "bytes_identical": True,
        "comparison": "per-path SHA-256 of worktree bytes before and after checkout",
    }


def validate_commission_payload_binding(document: dict[str, Any]) -> None:
    clone = json.loads(json.dumps(document))
    binding = clone["binding"]
    expected = binding.pop("commission_payload_sha256")
    require(
        binding["commission_payload_hash_scope"]
        == "canonical JSON of this document before commission_payload_sha256 is added"
        and json_digest(clone) == expected,
        "M176-E-COMMISSION",
        "commission output payload binding is absent or mismatched",
    )


def verify_claim_audit(
    claim_audit_path: Path,
    repo_root: Path,
    status_file: Path,
) -> dict[str, Any]:
    document = read_json(claim_audit_path)
    runner = CheckRunner()

    def audit_revision() -> None:
        require(
            document["schema"] == "strehl-m176-claim-audit-v2",
            "M176-E-CLAIM-REVISION",
            "claim-audit schema mismatch",
        )
        audit = document["audit"]
        require(
            audit["revision"] == AUDIT_REVISION
            and audit["revision_object_type"] == "commit"
            and audit["source_line_count"] == 172
            and audit["moving_worktree_excluded"] is True
            and audit["m139_artifact_policy"]
            == "COMMITTED_REPORT_ONLY_NO_OUTPUT_ARTIFACTS",
            "M176-E-CLAIM-REVISION",
            "audit basis, transcript extent, or M139 boundary drifted",
        )
        object_type = git_output_at(
            repo_root,
            ["cat-file", "-t", f"{AUDIT_REVISION}^{{commit}}"],
            "M176-E-CLAIM-REVISION",
        )
        require(
            object_type == "commit",
            "M176-E-CLAIM-REVISION",
            f"audit revision resolved as {object_type!r}, not commit",
        )

    runner.run("audit-revision-is-valid-fixed-commit", audit_revision)

    claims = document["claims"]

    def high_stakes_ids() -> None:
        declared = document["required_claim_ids"]
        actual = [claim["id"] for claim in claims]
        require(
            tuple(declared) == REQUIRED_CLAIM_IDS,
            "M176-E-CLAIM-IDS",
            "declared high-stakes claim ID contract drifted",
        )
        require(
            len(actual) == len(REQUIRED_CLAIM_IDS)
            and len(set(actual)) == len(actual)
            and set(actual) == set(REQUIRED_CLAIM_IDS),
            "M176-E-CLAIM-IDS",
            "required high-stakes claim IDs do not occur exactly once",
        )

    runner.run(
        "all-required-high-stakes-claim-ids-occur-exactly-once",
        high_stakes_ids,
    )

    def dispositions() -> None:
        require(
            tuple(document["classification_enum"]) == CLASSIFICATION_ENUM,
            "M176-E-CLAIM-DISPOSITION",
            "classification enum drifted",
        )
        require(
            tuple(document["worker_provenance_state_enum"]) == WORKER_PROVENANCE_ENUM,
            "M176-E-CLAIM-DISPOSITION",
            "worker-provenance enum drifted",
        )
        require(
            tuple(document["exposure_state_enum"]) == EXPOSURE_ENUM,
            "M176-E-CLAIM-DISPOSITION",
            "false-agreement/difference exposure enum drifted",
        )
        by_id = {claim["id"]: claim for claim in claims}
        validate_group_members(claims)
        for claim_id, (classifications, worker_state) in EXPECTED_CLAIM_RULINGS.items():
            claim = by_id[claim_id]
            require(
                tuple(claim["classifications"]) == classifications
                and all(value in CLASSIFICATION_ENUM for value in classifications),
                "M176-E-CLAIM-DISPOSITION",
                f"{claim_id}: classification changed",
            )
            worker = claim["worker_provenance"]
            require(
                worker["state"] == worker_state
                and worker_state in WORKER_PROVENANCE_ENUM
                and isinstance(worker["detail"], str)
                and bool(worker["detail"].strip()),
                "M176-E-CLAIM-DISPOSITION",
                f"{claim_id}: worker provenance is absent or wrong",
            )
            require(
                isinstance(claim["claim_or_contract"], str)
                and bool(claim["claim_or_contract"].strip())
                and isinstance(claim["consequence"], str)
                and bool(claim["consequence"].strip()),
                "M176-E-CLAIM-DISPOSITION",
                f"{claim_id}: claim/contract or consequence is absent",
            )
            for field in ("false_agreement_exposure", "false_difference_exposure"):
                exposure = claim[field]
                require(
                    exposure["state"] in EXPOSURE_ENUM
                    and isinstance(exposure["detail"], str)
                    and bool(exposure["detail"].strip()),
                    "M176-E-CLAIM-DISPOSITION",
                    f"{claim_id}: {field} is not explicit",
                )
            for field in ("current_score_survives", "current_verdict_survives"):
                require(
                    claim[field] is None or isinstance(claim[field], bool),
                    "M176-E-CLAIM-DISPOSITION",
                    f"{claim_id}: {field} must be boolean or null",
                )
            require(
                isinstance(claim["survival_detail"], str)
                and bool(claim["survival_detail"].strip()),
                "M176-E-CLAIM-DISPOSITION",
                f"{claim_id}: survival detail is absent",
            )

    runner.run(
        "classification-enum-worker-provenance-consequence-survival-explicit",
        dispositions,
    )

    def normative_requirement() -> None:
        require(
            document["normative_requirement"] == EXACT_NORMATIVE_REQUIREMENT
            and "\n" not in document["normative_requirement"],
            "M176-E-CLAIM-NORMATIVE",
            "the exact one-line scored/cache/hash-freeze requirement is absent",
        )

    runner.run(
        "exact-one-line-scored-cache-hash-freeze-requirement",
        normative_requirement,
    )

    def inventory_paths() -> None:
        inventory = document["material_file_inventory"]
        paths = inventory["paths"]
        evidence_paths = {
            item["path"] for claim in claims for item in claim["evidence"]
        }
        additional = inventory["additional_material_search_paths"]
        require(
            inventory["basis_revision"] == AUDIT_REVISION
            and inventory["count"] == len(paths)
            and len(paths) == len(set(paths))
            and paths == sorted(paths)
            and set(REQUIRED_MATERIAL_PATHS).issubset(paths)
            and additional == sorted(set(additional))
            and set(paths) == evidence_paths | set(additional),
            "M176-E-CLAIM-PATH",
            "material inventory is not the sorted evidence/additional-search union",
        )
        for index, path in enumerate(paths):
            canonical = require_repo_relative_path(path, f"inventory[{index}]")
            object_type = (
                git_bytes_at(
                    repo_root,
                    ["cat-file", "-t", f"{AUDIT_REVISION}:{canonical}"],
                    "M176-E-CLAIM-PATH",
                    f"inventory[{index}]: path is absent at the audit revision",
                )
                .decode("ascii", errors="strict")
                .strip()
            )
            require(
                object_type == "blob",
                "M176-E-CLAIM-PATH",
                f"inventory[{index}]: path resolves as {object_type!r}, not a blob",
            )

    citation_summary: dict[str, int] = {}

    def citation_resolution() -> None:
        citation_summary.update(
            validate_evidence_citations(
                claims,
                repo_root,
                set(document["material_file_inventory"]["paths"]),
            )
        )

    runner.run(
        "revision-bound-evidence-paths-exist-and-exact-anchors-occur-once",
        citation_resolution,
    )
    runner.run(
        "material-inventory-is-sorted-evidence-plus-search-union-at-revision",
        inventory_paths,
    )

    search_summary: dict[str, Any] = {}

    def search_completeness() -> None:
        protocol = document["revision_search"]
        expected_queries = [
            {
                "name": name,
                "pattern": pattern,
                "pathspecs": list(pathspecs),
            }
            for name, pattern, pathspecs in SEARCH_QUERIES
        ]
        require(
            protocol["revision"] == AUDIT_REVISION
            and protocol["engine"] == "git grep over commit tree"
            and protocol["flags"] == ["-I", "-i", "-l", "-E"]
            and protocol["command_template"]
            == "git grep -Iil -E -e <pattern> <revision> -- <pathspecs...>"
            and protocol["coverage_terms"] == list(SEARCH_COVERAGE_TERMS)
            and protocol["queries"] == expected_queries,
            "M176-E-CLAIM-SEARCH",
            "revision-bound Git search protocol drifted or was narrowed",
        )
        by_query, candidates = revision_search(repo_root)
        require(
            protocol["candidate_count"] == len(candidates)
            and protocol["candidate_paths"] == candidates,
            "M176-E-CLAIM-SEARCH",
            "declared search candidate path set differs from the audit revision",
        )
        inventory = set(document["material_file_inventory"]["paths"])
        exclusions = protocol["explicit_exclusions"]
        exclusion_paths = [item["path"] for item in exclusions]
        require(
            exclusion_paths == sorted(set(exclusion_paths))
            and all(
                isinstance(item["disposition"], str)
                and bool(item["disposition"].strip())
                for item in exclusions
            ),
            "M176-E-CLAIM-SEARCH",
            "search exclusions are duplicated, reordered, or lack dispositions",
        )
        for index, path in enumerate(exclusion_paths):
            require_repo_relative_path(path, f"revision_search.exclusion[{index}]")
        require(
            not (inventory & set(exclusion_paths))
            and set(candidates) == (inventory & set(candidates)) | set(exclusion_paths),
            "M176-E-CLAIM-SEARCH",
            "a revision-bound search hit is unaccounted or both material and excluded",
        )
        search_summary.update(
            {
                "candidate_count": len(candidates),
                "material_candidate_count": len(inventory & set(candidates)),
                "excluded_candidate_count": len(exclusion_paths),
                "query_candidate_counts": {
                    name: len(paths) for name, paths in by_query.items()
                },
            }
        )

    runner.run(
        "revision-bound-worker-hash-and-resume-search-is-complete",
        search_completeness,
    )

    checkout_summary: dict[str, Any] = {}

    def checkout_stability() -> None:
        experiment_dir = claim_audit_path.resolve().parent.parent
        require(
            claim_audit_path.resolve().parent.name == "out",
            "M176-E-CHECKOUT-EOL",
            "claim audit is not in the checkout-bound out directory",
        )
        checkout_summary.update(
            verify_checkout_stability(
                experiment_dir,
                document["checkout_stability"],
            )
        )

    runner.run(
        "checkout-byte-stability-under-core-autocrlf-true",
        checkout_stability,
    )

    def status_replacement() -> None:
        status = document["status_replacement"]
        worktree_status_before = sha256_file(status_file)
        require(
            status["target_path"] == "docs/STATUS.md"
            and status["target_revision"] == AUDIT_REVISION
            and status["old_semantic_anchor"]
            == "**Every hash pin in this repository is therefore"
            and status["proposed_replacement"] == EXACT_STATUS_REPLACEMENT
            and status["status_edit_performed"] is False
            and status["lane_write_boundary"] == "PROPOSAL_ONLY_STATUS_NOT_WRITTEN"
            and status["route_to"] == "orchestrator",
            "M176-E-CLAIM-STATUS",
            "STATUS replacement is absent, changed, or marked as applied",
        )
        blob = git_output_at(
            repo_root,
            ["rev-parse", f"{AUDIT_REVISION}:docs/STATUS.md"],
            "M176-E-CLAIM-STATUS",
        )
        require(
            status["target_blob_sha1"] == blob,
            "M176-E-CLAIM-STATUS",
            "STATUS replacement target blob is not audit-revision-bound",
        )
        target_text = git_blob_at(
            repo_root,
            AUDIT_REVISION,
            "docs/STATUS.md",
        ).decode("utf-8", errors="strict")
        require(
            target_text.count(status["old_semantic_anchor"]) == 1,
            "M176-E-CLAIM-STATUS",
            "overbroad STATUS statement is not a unique semantic anchor",
        )
        expected_status_path = (repo_root / "docs" / "STATUS.md").resolve()
        require(
            status_file.resolve() == expected_status_path
            and status_file.is_file()
            and status["worktree_state_before_lane"] == "PREEXISTING_MODIFIED",
            "M176-E-CLAIM-STATUS",
            "STATUS path or its pre-existing worktree state was hidden",
        )
        require(
            sha256_file(status_file) == worktree_status_before,
            "M176-E-CLAIM-STATUS",
            "STATUS changed while the proposal-only check was running",
        )

    runner.run(
        "status-replacement-present-target-bound-and-status-byte-untouched",
        status_replacement,
    )

    def repair_boundary() -> None:
        boundary = document["current_repair_boundary"]
        require(
            boundary
            == {
                "affected_source": AFFECTED,
                "audit_revision": AUDIT_REVISION,
                "audit_revision_contains_fixed_control": True,
                "fixed_control": FIXED,
                "full_post_fix_m12_worker_ladder_claimed": False,
                "m176_renderer_change": "NONE",
                "repair_commit": REPAIR,
                "repair_owner": "M172",
                "repair_parent_count": 1,
            },
            "M176-E-CLAIM-BOUNDARY",
            "current repair boundary drifted",
        )
        require(
            git_output_at(
                repo_root,
                ["rev-parse", f"{REPAIR}^"],
                "M176-E-CLAIM-BOUNDARY",
            )
            == AFFECTED,
            "M176-E-CLAIM-BOUNDARY",
            "repair's sole parent is not the affected source",
        )
        for older, newer in ((REPAIR, FIXED), (FIXED, AUDIT_REVISION)):
            completed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "merge-base",
                    "--is-ancestor",
                    older,
                    newer,
                ],
                capture_output=True,
                check=False,
            )
            require(
                completed.returncode == 0,
                "M176-E-CLAIM-BOUNDARY",
                f"{older} is not an ancestor of {newer}",
            )

    runner.run(
        "current-repair-boundary-is-m172-and-m176-lands-no-repair",
        repair_boundary,
    )

    def uncertainties() -> None:
        values = document["uncertainties"]
        require(
            [item["id"] for item in values] == ["U1", "U2", "U3", "U4", "U5", "U6"]
            and all(
                isinstance(item["text"], str) and bool(item["text"].strip())
                for item in values
            ),
            "M176-E-CLAIM-UNCERTAINTY",
            "remaining uncertainties are incomplete",
        )

    runner.run("remaining-uncertainties-are-explicit", uncertainties)

    return {
        "schema": "strehl-m176-claim-audit-verification-v1",
        "all_pass": True,
        "checks_run": len(runner.results),
        "checks": runner.results,
        "audit_revision": AUDIT_REVISION,
        "claim_count": len(claims),
        "material_file_count": len(document["material_file_inventory"]["paths"]),
        "citation_resolution": citation_summary,
        "revision_search": search_summary,
        "checkout_stability": checkout_summary,
        "claim_audit_sha256": sha256_file(claim_audit_path),
        "source_sha256": script_hashes(),
        "status_target_blob_sha1": document["status_replacement"]["target_blob_sha1"],
        "status_worktree_untouched_during_check": True,
    }


def preserved_reproduction_verification(evidence_dir: Path) -> dict[str, Any]:
    verification_path = evidence_dir / "verification.json"
    previous = read_json(verification_path)
    if previous["schema"] == "strehl-m176-verification-v1":
        commission_path = evidence_dir / "commission.json"
        commission = read_json(commission_path)
        expected = commission["binding"]["evidence_sha256"]["verification.json"]
        actual = sha256_file(verification_path)
        require(
            commission["all_pass"] is True
            and expected == actual
            and previous["all_pass"] is True
            and previous["checks_run"] == len(previous["checks"])
            and all(item["status"] == "PASS" for item in previous["checks"]),
            "M176-E-INTEGRATION-BINDING",
            "legacy independent verification is not intact and fully passing",
        )
        immutable = {
            name: digest
            for name, digest in commission["binding"]["evidence_sha256"].items()
            if name != "verification.json"
        }
        reproduction = {
            "schema": previous["schema"],
            "verification_sha256": actual,
            "legacy_commission_sha256": sha256_file(commission_path),
            "all_pass": True,
            "checks_run": previous["checks_run"],
            "checks": previous["checks"],
            "mechanism_verdict": previous["mechanism_verdict"],
            "production_script_sha256": previous["script_sha256"],
            "immutable_evidence_sha256": immutable,
            "preservation_mode": (
                "Prior independent production verification retained by SHA-256; "
                "integration regeneration performs no build, render, or capture access."
            ),
        }
    else:
        require(
            previous["schema"] == "strehl-m176-integration-verification-v2",
            "M176-E-INTEGRATION-BINDING",
            f"unsupported prior verification schema {previous['schema']!r}",
        )
        reproduction = previous["reproduction_verification"]
    for name, digest in reproduction["immutable_evidence_sha256"].items():
        require(
            sha256_file(evidence_dir / name) == digest,
            "M176-E-INTEGRATION-BINDING",
            f"production evidence changed after independent verification: {name}",
        )
    return reproduction


def verify_integration(
    evidence_dir: Path,
    claim_audit_path: Path,
    repo_root: Path,
    status_file: Path,
) -> dict[str, Any]:
    reproduction = preserved_reproduction_verification(evidence_dir)
    claim = verify_claim_audit(claim_audit_path, repo_root, status_file)
    preserved_checks = [
        {"name": item["name"], "status": "PASS_PRESERVED_BY_SHA256"}
        for item in reproduction["checks"]
    ]
    analysis = read_json(evidence_dir / "analysis.json")
    provenance = read_json(evidence_dir / "provenance.json")
    require(
        analysis["mechanism_verdict"]
        == reproduction["mechanism_verdict"]
        == "REDUCTION_ORDER",
        "M176-E-INTEGRATION-BINDING",
        "mechanism verdict moved after production verification",
    )
    require(
        provenance["script_sha256"] == reproduction["production_script_sha256"]
        and provenance["preregistration_sha256"]
        == reproduction["production_script_sha256"]["preregistration.json"],
        "M176-E-INTEGRATION-BINDING",
        "historical render-time source hashes moved during LF integration",
    )
    production_binding_check = {
        "name": "historical-render-time-source-byte-binding-preserved",
        "status": "PASS",
    }
    checks = [*preserved_checks, production_binding_check, *claim["checks"]]
    return {
        "schema": "strehl-m176-integration-verification-v2",
        "all_pass": True,
        "counts": {
            "reproduction_checks_preserved": len(preserved_checks),
            "historical_production_binding_checks": 1,
            "claim_audit_checks_run": claim["checks_run"],
            "checks_run": len(checks),
        },
        "checks": checks,
        "mechanism_verdict": analysis["mechanism_verdict"],
        "reproduction_verification": reproduction,
        "claim_audit_verification": claim,
        "claim_audit_sha256": claim["claim_audit_sha256"],
        "integration_script_sha256": script_hashes(),
        "integration_scope": (
            "Claim/report integration only; no build, render, capture access, or "
            "renderer repair."
        ),
    }


def normalize_argv(argv: list[str]) -> list[str]:
    value = list(argv)
    value[0] = "<BINARY>"
    out_index = value.index("--out") + 1
    value[out_index] = "<OUTPUT>"
    return value


def verify_production(evidence_dir: Path, require_commission: bool) -> dict[str, Any]:
    prereg = read_json(EXPERIMENT_DIR / "preregistration.json")
    provenance = read_json(evidence_dir / "provenance.json")
    lineage = read_json(evidence_dir / "lineage.json")
    builds_doc = read_json(evidence_dir / "builds.json")
    runs_doc = read_json(evidence_dir / "runs.json")
    source = read_json(evidence_dir / "source-evidence.json")
    resource = read_json(evidence_dir / "resource-estimate.json")
    analysis = read_json(evidence_dir / "analysis.json")
    before = read_json(evidence_dir / "input-before.json")
    after = read_json(evidence_dir / "input-after.json")
    builds = {build["label"]: build for build in builds_doc["builds"]}
    records = {record["run_id"]: record for record in runs_doc["runs"]}
    runner = CheckRunner()

    def prereg_binding() -> None:
        require(
            provenance["preregistration_sha256"]
            == sha256_file(EXPERIMENT_DIR / "preregistration.json"),
            "M176-E-PREREG",
            "preregistration hash changed",
        )
        require(
            provenance["script_sha256"] == script_hashes(),
            "M176-E-SCRIPT-BINDING",
            "production script hashes changed after rendering",
        )
        require(
            sha256_file(Path(sys.executable))
            == builds_doc["tooling"]["python_executable"]["sha256"],
            "M176-E-PYTHON-BINDING",
            "Python executable changed",
        )

    runner.run("preregistration-production-python-binding", prereg_binding)

    def input_integrity() -> None:
        guard_capture_path(before["root"])
        require(
            before == after,
            "M176-E-INPUT-MUTATION",
            "stored before/after manifests differ",
        )
        current = capture_manifest(APPROVED_INPUT)
        require(
            current == before,
            "M176-E-INPUT-MUTATION",
            "current approved input differs from the pre-render manifest",
        )

    runner.run("approved-input-before-after-current-integrity", input_integrity)

    def lineage_check() -> None:
        require(
            lineage["repair_parent"] == AFFECTED
            and git_output(["rev-parse", f"{REPAIR}^"]) == AFFECTED,
            "M176-E-SOURCE",
            "affected revision is not the repair's sole parent",
        )
        require(
            lineage["fixed_source"] == FIXED
            and lineage["repair_is_ancestor_of_fixed"] is True,
            "M176-E-LINEAGE",
            "fixed revision does not contain repair",
        )
        require(
            git_output(["show", "-s", "--format=%s", FIXED])
            == "Bound Pyramid worker memory",
            "M176-E-SOURCE",
            "fixed commit subject mismatch",
        )

    runner.run("git-lineage-identifies-affected-and-fixed", lineage_check)

    def source_archives() -> None:
        for label, commit in [("affected", AFFECTED), ("fixed", FIXED)]:
            build = builds[label]
            require(
                build["source_commit"] == commit
                and build["source_tree"]
                == git_output(["rev-parse", f"{commit}^{{tree}}"]),
                "M176-E-SOURCE",
                f"{label} source commit/tree mismatch",
            )
            actual = source_tree_manifest(Path(build["source_directory"]))
            require(
                actual == build["archive"]["extracted"],
                "M176-E-SOURCE-MUTATION",
                f"{label} archived source changed after build",
            )
            require(
                build["target_preexisting"] is False
                and build["archive"]["git_exit_code"] == 0
                and build["archive"]["tar_exit_code"] == 0,
                "M176-E-STALE",
                f"{label} archive/target freshness is false",
            )

    runner.run("independent-git-archives-remain-byte-bound", source_archives)

    def binaries() -> None:
        for label, commit in [("affected", AFFECTED), ("fixed", FIXED)]:
            build = builds[label]
            binary = Path(build["binary"]["path"])
            require(
                not build["binary_preexisting"]
                and sha256_file(binary) == build["binary"]["sha256"],
                "M176-E-BINARY",
                f"{label} binary is stale or hash-mismatched",
            )
            require(
                commit in build["binary_version_text"],
                "M176-E-BINARY",
                f"{label} binary does not identify its source",
            )

    runner.run("fresh-binary-source-sha256-provenance", binaries)

    def run_order_workers() -> None:
        actual_ids = [record["run_id"] for record in runs_doc["runs"]]
        expected = list(EXPECTED_BASE_RUNS)
        if runs_doc["fallback_w3_used"]:
            expected.insert(3, "affected-w3")
        require(actual_ids == expected, "M176-E-WORKER", f"run order is {actual_ids}")
        expected_workers = {
            "affected-w1": 1,
            "affected-w2": 2,
            "affected-w1-repeat": 1,
            "affected-w3": 3,
            "fixed-w1": 1,
            "fixed-w2": 2,
        }
        for run_id, record in records.items():
            require(
                record["workers"] == expected_workers[run_id]
                and int(record["renderer_environment"]["STREHL_PYRAMID_WORKERS"])
                == expected_workers[run_id]
                and record["rayon_threads"] == 2,
                "M176-E-WORKER",
                f"{run_id} worker/Rayon provenance mismatch",
            )

    runner.run("registered-arm-order-worker-and-rayon-provenance", run_order_workers)

    def fresh_outputs() -> None:
        require(
            provenance["scratch_run_preexisting"] is False
            and provenance["evidence_directory_preexisting"] is False,
            "M176-E-STALE",
            "production root freshness was not established",
        )
        for run_id, record in records.items():
            require(
                record["output"]["preexisting"] is False
                and record["output"]["created_after_launch_check"] is True,
                "M176-E-STALE",
                f"{run_id} accepted a pre-existing output",
            )

    runner.run("stale-preexisting-output-refusal", fresh_outputs)

    def environments() -> None:
        expected_names = set(prereg["renderer_environment"])
        base_hashes = {
            record["environment_except_worker_sha256"] for record in records.values()
        }
        require(
            len(base_hashes) == 1, "M176-E-ENV", "non-worker child environment changed"
        )
        for label, names in provenance["renderer_environment_names_discovered"].items():
            require(
                set(names).issubset(expected_names),
                "M176-E-ENV",
                f"{label} has unrecorded environment names",
            )
        reference: dict[str, Any] | None = None
        for record in records.values():
            environment = record["renderer_environment"]
            require(
                set(environment) == expected_names,
                "M176-E-ENV",
                "environment key set drift",
            )
            non_worker = {
                name: value
                for name, value in environment.items()
                if name != "STREHL_PYRAMID_WORKERS"
            }
            if reference is None:
                reference = non_worker
            require(
                non_worker == reference, "M176-E-ENV", "non-worker renderer env drift"
            )
            require(
                environment["STREHL_ALIGN"] == "0"
                and environment["STREHL_DEFECT"] == "off"
                and environment["STREHL_FIX_CA"] == "off",
                "M176-E-ENV",
                "required off switches are missing",
            )

    runner.run("all-renderer-environment-recorded-only-worker-varies", environments)

    def settings() -> None:
        expected_template = prereg["render"]["argv_template"]
        expected_suffix = [
            "<OUTPUT>" if item == "<PRIVATE_UNIQUE_OUTPUT>" else item
            for item in expected_template[1:]
        ]
        for run_id, record in records.items():
            normalized = normalize_argv(record["argv"])
            require(
                normalized[1:] == expected_suffix,
                "M176-E-SETTINGS",
                f"{run_id} argv differs from preregistration",
            )

    runner.run("all-non-output-argv-settings-identical", settings)

    def output_binding() -> None:
        output_paths: set[str] = set()
        for run_id, record in records.items():
            require(
                record["input"] == APPROVED_INPUT,
                "M176-E-INPUT",
                f"{run_id} input mismatch",
            )
            output = ensure_private_path(record["output"]["path"])
            require(
                str(output) not in output_paths,
                "M176-E-OUTPUT-BINDING",
                "output path reused",
            )
            output_paths.add(str(output))
            require(
                sha256_file(output) == record["output"]["sha256"],
                "M176-E-OUTPUT-BINDING",
                f"{run_id} TIFF hash mismatch",
            )
            for stream in ("stdout", "stderr"):
                item = record[stream]
                require(
                    sha256_file(Path(item["path"])) == item["sha256"],
                    "M176-E-OUTPUT-BINDING",
                    f"{run_id} raw {stream} hash mismatch",
                )
            require(
                record["binary_sha256"]
                == builds["affected" if run_id.startswith("affected") else "fixed"][
                    "binary"
                ]["sha256"],
                "M176-E-BINARY",
                f"{run_id} binary binding mismatch",
            )

    runner.run("tiff-log-binary-run-record-binding", output_binding)

    regenerated: dict[str, Any] = {}

    def independent_decode() -> None:
        regenerated.update(build_analysis(evidence_dir))
        require(
            regenerated["independent_decoder_corroboration"]["all_images_equal"]
            is True,
            "M176-E-DECODE-DISAGREE",
            "independent TIFF decoders disagree",
        )

    runner.run("independent-tiff-decoder-corroboration", independent_decode)

    def same_worker() -> None:
        require(
            analysis["comparisons"]["affected_w1_vs_repeat"]["pixel_identical"] is True,
            "M176-E-REPEAT",
            "affected W1 repeat differs",
        )

    runner.run("affected-fixed-worker-repeat-is-deterministic", same_worker)

    def affected_cross() -> None:
        comparison = analysis["comparisons"][source["affected_comparison"]]
        if analysis["mechanism_verdict"] == "REDUCTION_ORDER":
            require(
                comparison["pixel_identical"] is False,
                "M176-E-CROSS",
                "REDUCTION_ORDER lacks affected cross-worker pixel difference",
            )

    runner.run(
        "affected-cross-worker-equality-or-difference-classified", affected_cross
    )

    def fixed_invariance() -> None:
        if analysis["mechanism_verdict"] == "REDUCTION_ORDER":
            require(
                analysis["comparisons"]["fixed_w1_vs_w2"]["pixel_identical"] is True,
                "M176-E-FIXED",
                "fixed build is not worker-invariant",
            )

    runner.run("fixed-build-worker-invariance", fixed_invariance)

    def metadata_semantics() -> None:
        for comparison in analysis["comparisons"].values():
            relation = comparison["file_pixel_relation"]
            require(
                relation
                in {
                    "PIXELS_DIFFER",
                    "FILE_METADATA_ONLY",
                    "FILE_AND_PIXELS_IDENTICAL",
                },
                "M176-E-METADATA",
                f"unknown file/pixel relation {relation}",
            )
            require(
                (relation == "PIXELS_DIFFER") is (not comparison["pixel_identical"]),
                "M176-E-METADATA",
                "file difference was confused with decoded-pixel difference",
            )

    runner.run("whole-file-versus-decoded-pixel-semantics", metadata_semantics)

    def magnitude_sign() -> None:
        require(
            regenerated == analysis,
            "M176-E-MAGNITUDE",
            "fresh decoded magnitude/sign analysis differs from committed evidence",
        )
        for comparison in analysis["comparisons"].values():
            require(
                comparison["signed_delta_direction"] == "B_MINUS_A"
                and comparison["max_absolute_over_65535"]
                == comparison["max_absolute_dn16"] / 65535.0,
                "M176-E-MAGNITUDE",
                "delta sign or normalized magnitude drifted",
            )

    runner.run("decoded-magnitude-sign-and-normalization-recomputed", magnitude_sign)

    def mechanism() -> None:
        allowed = {
            "REDUCTION_ORDER",
            "NOT_REPRODUCED",
            "FILE_METADATA_ONLY",
            "BOUNDARY",
            "SELECTION_TIE",
            "OTHER_UNRESOLVED",
        }
        require(
            analysis["mechanism_verdict"] in allowed,
            "M176-E-VERDICT",
            "verdict is outside preregistered taxonomy",
        )
        if analysis["mechanism_verdict"] == "REDUCTION_ORDER":
            require(
                all(source["mechanism_preconditions"].values())
                and source["runtime_preconditions"]["alignment_off_all_runs"]
                and source["runtime_preconditions"]["coverage_boundary_excluded"],
                "M176-E-MECHANISM",
                "REDUCTION_ORDER preconditions are not all true",
            )
        excerpt_paths = {
            "affected_worker_chunk_count": (
                "affected",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "affected_parallel_chunks": (
                "affected",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "affected_left_to_right_absorb": (
                "affected",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "fixed_canonical_chunk_count": (
                "fixed",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "fixed_canonical_chunk_size": (
                "fixed",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "fixed_canonical_iteration": (
                "fixed",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "fixed_left_to_right_absorb": (
                "fixed",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "soft_power_default": (
                "affected",
                "crates/strehl-core/src/pyramid.rs",
            ),
            "f32_numerator": (
                "affected",
                "crates/strehl-core/src/pyramid.rs",
            ),
            "f32_absorb": (
                "affected",
                "crates/strehl-core/src/pyramid.rs",
            ),
        }
        for name, excerpt in source["excerpts"].items():
            label, relative = excerpt_paths[name]
            path = Path(builds[label]["source_directory"]) / relative
            lines = path.read_text(encoding="utf-8").splitlines()
            anchor_matches = [line for line in lines if line == excerpt["anchor"]]
            first, last = excerpt["range"]
            actual_excerpt = "\n".join(lines[first - 1 : last]) + "\n"
            require(
                len(anchor_matches) == 1
                and lines[excerpt["line"] - 1] == excerpt["anchor"]
                and sha256_file(path) == excerpt["file_sha256"]
                and actual_excerpt == excerpt["excerpt"],
                "M176-E-SOURCE-ANCHOR",
                f"source excerpt {name} lost its unique full-line anchor or binding",
            )

    runner.run("source-mechanism-preconditions-and-verdict", mechanism)

    def path_confinement() -> None:
        guard_capture_path(runs_doc["input"])
        ensure_private_path(provenance["scratch_run_root"])
        for record in records.values():
            ensure_private_path(record["output"]["path"])
            require(
                record["renderer_environment"]["STREHL_WARPMAP"] is None,
                "M176-E-PATH",
                "warp-map path was configured despite alignment-off protocol",
            )

    runner.run("protected-forbidden-path-confinement", path_confinement)

    def source_before_after() -> None:
        require(
            before["manifest_sha256"]
            == after["manifest_sha256"]
            == provenance["input_manifest_before_sha256"]
            == provenance["input_manifest_after_sha256"],
            "M176-E-INPUT-MUTATION",
            "before/after capture source binding differs",
        )

    runner.run("source-before-after-byte-and-metadata-manifest", source_before_after)

    def resource_check() -> None:
        require(
            resource["within_limits"] is True,
            "M176-E-RESOURCE",
            "preflight did not pass",
        )
        for record in records.values():
            memory = record["memory_observation"]
            require(
                not memory["stopped_for_limit"]
                and memory["peak_working_set_bytes"] <= MAX_RESIDENT_BYTES,
                "M176-E-RESOURCE",
                f"{record['run_id']} exceeded resident stop rule",
            )

    runner.run("resource-estimate-and-observed-resident-stop-rule", resource_check)

    def fallback_check() -> None:
        w1_w2_equal = analysis["comparisons"]["affected_w1_vs_w2"]["pixel_identical"]
        require(
            runs_doc["fallback_w3_used"] is w1_w2_equal,
            "M176-E-FALLBACK",
            "W3 fallback use does not match the preregistered trigger",
        )
        require(
            not any(record["workers"] > 3 for record in records.values()),
            "M176-E-WORKER",
            "worker count exceeded W3",
        )

    runner.run("w3-fallback-trigger-and-ceiling", fallback_check)

    if require_commission:

        def commission_check() -> None:
            commission = read_json(evidence_dir / "commission.json")
            validate_commission_payload_binding(commission)
            counts = commission["counts"]
            require(
                counts["substantive_mutations_planted"]
                == counts["substantive_mutations_killed"]
                and counts["fixture_mutations_planted"]
                == counts["fixture_mutations_killed"]
                and counts["claim_audit_mutations_planted"]
                == counts["claim_audit_mutations_killed"]
                and counts["checkout_policy_mutations_planted"]
                == counts["checkout_policy_mutations_killed"]
                and counts["inert_controls_planted"]
                == counts["inert_controls_survived"]
                == 1,
                "M176-E-COMMISSION",
                "mutation commissioning counts are not fully killed/survived",
            )
            require(
                commission["binding"]["production_source_sha256_before"]
                == commission["binding"]["production_source_sha256_after"]
                == script_hashes(),
                "M176-E-COMMISSION",
                "production sources changed during mutation commissioning",
            )
            require(
                "claim-audit.json" in commission["binding"]["evidence_sha256"]
                and commission["binding"][
                    "claim_audit_restored_byte_identically_after_every_mutation"
                ]
                is True
                and commission["binding"][
                    "eol_policy_restored_byte_identically_after_every_mutation"
                ]
                is True
                and commission["binding"]["status_untouched_during_commissioning"]
                is True,
                "M176-E-COMMISSION",
                "claim-audit or STATUS commissioning binding is absent",
            )
            for name, digest in commission["binding"]["evidence_sha256"].items():
                require(
                    sha256_file(evidence_dir / name) == digest,
                    "M176-E-COMMISSION",
                    f"commissioned evidence changed: {name}",
                )

        runner.run("mutation-commissioning-binding-and-counts", commission_check)

    return {
        "schema": "strehl-m176-verification-v1",
        "all_pass": True,
        "checks_run": len(runner.results),
        "checks": runner.results,
        "mechanism_verdict": analysis["mechanism_verdict"],
        "script_sha256": script_hashes(),
        "python": {
            "version": sys.version,
            "executable": str(Path(sys.executable)),
            "executable_sha256": sha256_file(Path(sys.executable)),
        },
        "commission_required": require_commission,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--evidence-dir", type=Path)
    group.add_argument("--fixture", type=Path)
    group.add_argument("--claim-audit", type=Path)
    group.add_argument("--integration-evidence-dir", type=Path)
    parser.add_argument("--integration-claim-audit", type=Path)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--require-commission", action="store_true")
    args = parser.parse_args()
    try:
        repo_root = args.repo_root.resolve()
        status_file = (
            args.status_file.resolve()
            if args.status_file is not None
            else (repo_root / "docs" / "STATUS.md").resolve()
        )
        if args.fixture is not None:
            result = validate_fixture(read_json(args.fixture))
        elif args.claim_audit is not None:
            result = verify_claim_audit(
                args.claim_audit.resolve(),
                repo_root,
                status_file,
            )
        elif args.integration_evidence_dir is not None:
            require(
                args.integration_claim_audit is not None,
                "M176-E-CLAIM",
                "--integration-claim-audit is required in integration mode",
            )
            result = verify_integration(
                args.integration_evidence_dir.resolve(),
                args.integration_claim_audit.resolve(),
                repo_root,
                status_file,
            )
        else:
            result = verify_production(args.evidence_dir, args.require_commission)
            if args.write_report:
                write_json_new(args.evidence_dir / "verification.json", result)
        if args.result is not None:
            write_json_new(args.result, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (EvidenceError, KeyError, OSError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
