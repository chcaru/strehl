#!/usr/bin/env python3
"""Evidence-reading reference adjudicator for the corrected M138 W1 gate.

This program does not render a campaign. It rejects the draft contract, verifies
sealed artifact hashes, executes bound extractors/checkers, recomputes every
scored quantity, and refuses submitted verdict-bearing values.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT_PATH = HERE / "corrected-gate-contract.json"
PREREG_PATH = HERE / "corrected-gate-preregistration.md"


SOURCE_ANCHORS = (
    ("experiments/PHASE1-DESIGN/measure.py", 29, 31, "FLAT_BAR = 0.90"),
    ("experiments/PHASE1-DESIGN/measure.py", 129, 141, "def exponent_at"),
    ("experiments/PHASE1-DESIGN/measure.py", 171, 180, "winner = np.argmax"),
    ("experiments/PHASE1-DESIGN/measure.py", 235, 250, "va_pyr = R.gaussian_pyramid"),
    ("experiments/PHASE1-DESIGN/measure.py", 407, 422, "weights[:, below] = 1.0"),
    ("experiments/PHASE1-DESIGN/measure.py", 443, 460, "np.clip"),
    ("experiments/PHASE1-DESIGN/measure.py", 568, 575, "if survivors:"),
    ("experiments/PHASE1-DESIGN/reference.py", 625, 633, "if band >= 4"),
    ("experiments/PHASE1-DESIGN/reference.py", 666, 727, "worst_frame_by_band"),
    (
        "experiments/PHASE1-DESIGN/reference.py",
        1052,
        1064,
        '"overall": coverage["overall_by_band"]',
    ),
    (
        "experiments/PHASE1-DESIGN/reference.py",
        1080,
        1134,
        "laplacian_pyramid(transformed, 1)[0]",
    ),
    ("experiments/PHASE1-DESIGN/reference.py", 1135, 1200, "math.sqrt(0.70)"),
    ("crates/strehl-core/src/pyramid.rs", 372, 384, "pub fn build_gaussian"),
    ("crates/strehl-core/src/merge.rs", 421, 427, "maximum over N frames"),
    (
        "experiments/M135-detail-instrument/PREREGISTRATION.md",
        7,
        12,
        "does not qualify a physical",
    ),
    (
        "experiments/M135-detail-instrument/PREREGISTRATION.md",
        26,
        53,
        "They may never create a win",
    ),
    (
        "experiments/M135-detail-instrument/PREREGISTRATION.md",
        127,
        149,
        "Planted optical improvement",
    ),
    ("experiments/M135-detail-instrument/instrument.py", 207, 260, '"status": "OK"'),
    ("docs/research/M62-sqrt-n.md", 32, 45, "exactly √N"),
    ("docs/research/M62-sqrt-n.md", 64, 70, "real branch is not run"),
    ("docs/proposals/2026-09-phase1-design.md", 226, 230, "d_hull = max"),
    ("docs/proposals/2026-09-phase1-design.md", 312, 316, "Width match"),
    ("docs/proposals/2026-09-phase1-design.md", 340, 350, "No common value means"),
    (
        "docs/proposals/2026-09-sota-scorecard.md",
        633,
        635,
        "UCB95(sigma_strehl / min(sigma_comparator)) <=0.950",
    ),
    ("docs/proposals/2026-08-sota-path.md", 2517, 2521, "<=0.90"),
    (
        "experiments/PHASE1-DESIGN/PREREGISTRATION.md",
        167,
        203,
        "Only width survivors are rendered",
    ),
    (
        "experiments/PHASE1-DESIGN/results/gate.json",
        1,
        1,
        '"seconds":263.6871026000008',
    ),
    ("experiments/PHASE1-DESIGN/results/run.json", 1, 1, '"pareto_rendered":false'),
)

HISTORICAL_ANCHORS = (
    (
        "f5658e5d:docs/proposals/2026-09-phase1-design.md",
        280,
        286,
        "upper 95% bound must be `<= 0.90`",
    ),
)

REQUIRED_DOCUMENT_TEXT = (
    "# M138 corrected W1 gate draft",
    "NOT FROZEN",
    "Width is diagnostic, never dispositive",
    "Minimum effect remains named and unbound",
    "The temporal decision boundary is `1.0`",
    "`64` sites retained only as the lowest admissible evidence count",
    "Raw sealed evidence contract",
    "PRE-CLAMP",
    "M135 executable interface",
    "UNSUPPORTED",
    "missing required artifact",
    "Could not determine",
    "No submitted scalar, array, or status string may carry a verdict",
    "four unique source-capture identities",
    "hash-bound benchmark artifact",
    "Every `PHASE1_GO` carries",
    "licenses no scorecard M2 claim",
    "`delta_required` remains unbound",
)

HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")


class EvidenceError(RuntimeError):
    """A malformed, missing, unhashed, or contradictory evidence artifact."""


def load_json(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            value = json.load(stream)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_seed(base: int, label: str) -> int:
    suffix = int(hashlib.sha256(label.encode("utf-8")).hexdigest()[:16], 16)
    return (base ^ suffix) % (2**63)


def percentile_higher(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(values, probability, method="higher"))


def wilson_interval(
    successes: int, trials: int, confidence: float
) -> tuple[float, float]:
    if not 0 <= successes <= trials or trials <= 0:
        raise EvidenceError("invalid binomial counts")
    if not 0.0 < confidence < 1.0:
        raise EvidenceError("invalid confidence")
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    radius = (
        z
        * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def one_sided_wilson_lower(successes: int, trials: int, confidence: float) -> float:
    if not 0 <= successes <= trials or trials <= 0:
        raise EvidenceError("invalid binomial counts")
    z = NormalDist().inv_cdf(confidence)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    radius = (
        z
        * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
        / denominator
    )
    return max(0.0, center - radius)


def tau_keys(contract: dict[str, Any]) -> list[str]:
    cfg = contract["threshold_coordinate"]
    start = int(round(float(cfg["grid_start"]) * 100))
    stop = int(round(float(cfg["grid_stop"]) * 100))
    step = int(round(float(cfg["grid_step"]) * 100))
    if (start, stop, step) != (0, 100, 1):
        raise EvidenceError("the frozen tau grid must be 0.00 through 1.00 by 0.01")
    return [f"{value / 100:.2f}" for value in range(start, stop + 1, step)]


def validate_contract(contract: dict[str, Any], *, test_mode: bool = False) -> None:
    if contract.get("schema") != 4:
        raise EvidenceError("unsupported contract schema")
    if contract.get("status") not in {
        "DRAFT_PENDING_THIRD_INDEPENDENT_REVIEW",
        "FROZEN_BEFORE_CORRECTED_GATE_OUTCOME_GENERATION",
    }:
        raise EvidenceError("invalid contract status")
    if contract["output_gate"].get("width_role") != "DIAGNOSTIC_ONLY":
        raise EvidenceError("width was promoted back into the gate")
    if (
        contract["hull_instrument"].get("measurement_stage")
        != "PRE_CLAMP_RECONSTRUCTION"
    ):
        raise EvidenceError("hull measurement is not pre-clamp")
    if contract["hull_instrument"].get("post_clamp_evidence_forbidden") is not True:
        raise EvidenceError("post-clamp hull evidence was not forbidden")
    if float(contract["noise_instrument"]["natural_null_power_ratio"]) != 1.0:
        raise EvidenceError("temporal-noise boundary must be the natural null at 1.0")
    if contract["noise_instrument"].get("power_ratio_upper95") is not None:
        raise EvidenceError("the unsupported 0.90 temporal threshold remains")
    if tau_keys(contract)[0] != "0.00" or tau_keys(contract)[-1] != "1.00":
        raise EvidenceError("tau endpoints changed")
    if int(contract["threshold_coordinate"]["robust_neighbour_steps"]) != 1:
        raise EvidenceError("robust-neighbour rule changed")
    detail = contract["detail_instrument"]
    if detail.get("valid_decision_states") != ["DETAIL_PASS", "DETAIL_FAIL"]:
        raise EvidenceError("M135 valid decision states changed")
    if detail.get("invalid_decision_state") != "INSTRUMENT_INVALID":
        raise EvidenceError("M135 invalid decision state changed")
    if contract["status"] == "FROZEN_BEFORE_CORRECTED_GATE_OUTCOME_GENERATION":
        if not isinstance(contract["activation"].get("independent_review"), dict):
            raise EvidenceError("frozen contract lacks independent-review binding")
        if not HEX40.fullmatch(str(contract["activation"].get("frozen_commit", ""))):
            raise EvidenceError("frozen contract lacks frozen commit")
        if contract["noise_instrument"].get("binding_state") != "BOUND":
            raise EvidenceError("frozen contract lacks temporal-noise binding")
        if contract["capture_ledgers"].get("binding_state") != "BOUND":
            raise EvidenceError("frozen contract lacks capture ledgers")
        if contract["cost"].get("binding_state") != "BOUND":
            raise EvidenceError("frozen contract lacks representative cost benchmark")
    noise = contract["noise_instrument"]
    if noise.get("commissioning_transforms") != {
        "null": "IDENTITY",
        "inflation_defect": "DOUBLE_CANDIDATE_TEMPORAL_POWER",
        "averaging_improvement": "HALVE_CANDIDATE_TEMPORAL_POWER",
        "common_scene_placebo": ("ADD_IDENTICAL_SCENE_TERM_TO_BOTH_CANDIDATE_REPEATS"),
    }:
        raise EvidenceError("temporal commissioning transforms changed")
    if noise.get("reference") != "LEGACY_STREHL":
        raise EvidenceError("W1 temporal reference changed")
    if noise.get("scorecard_m2_claim") != "NOT_LICENSED":
        raise EvidenceError("W1 was allowed to license scorecard M2")
    if noise.get("minimum_effect_symbol") != "delta_required":
        raise EvidenceError("minimum-effect symbol changed")
    if noise.get("unbound_minimum_effect_claim") != "DIRECTION_ONLY":
        raise EvidenceError("unbound minimum-effect claim changed")
    if noise.get("scorecard_m2_reference") != "SHIPPING_COMPARATOR":
        raise EvidenceError("scorecard M2 reference changed")
    if (
        noise.get("power_analysis_requirement")
        != "REQUIRED_ONLY_WHEN_MINIMUM_EFFECT_BOUND"
    ):
        raise EvidenceError("minimum-effect power requirement changed")
    if noise.get("minimum_effect_binding_state") not in {"UNBOUND", "BOUND"}:
        raise EvidenceError("invalid minimum-effect binding state")
    if noise.get("minimum_effect_binding_state") == "UNBOUND" and any(
        noise.get(field) is not None
        for field in (
            "required_rms_reduction",
            "effect_requirement",
            "pilot_evidence",
        )
    ):
        raise EvidenceError("unbound minimum effect carries bound evidence")
    if noise.get("effect_output_schema") != "m138-achieved-temporal-effect/v1":
        raise EvidenceError("achieved-effect output schema changed")
    if noise.get("required_go_effect_phases") != ["development", "holdout"]:
        raise EvidenceError("required GO effect phases changed")
    if noise.get("required_effect_cell_fields") != [
        "estimated_power_ratio",
        "simultaneous_confidence_lower",
        "simultaneous_confidence_upper",
        "simultaneous_one_sided_upper",
    ]:
        raise EvidenceError("required achieved-effect cell fields changed")
    if (
        contract["evidence_contract"].get("adjudication_output_schema")
        != "m138-adjudication/v2"
    ):
        raise EvidenceError("adjudication output schema changed")
    if (
        contract["evidence_contract"].get("rule")
        != "No submitted scalar, array, or status string may carry a verdict. "
        "Every quantity the gate scores must be recomputed by the adjudicator "
        "from a hash-bound artifact, and every artifact reference that is "
        "required to be independent must be verified distinct."
    ):
        raise EvidenceError("raw-evidence authority rule changed")
    if "status" in contract["cost"]:
        raise EvidenceError("cost status strings are forbidden")
    if test_mode:
        return
    standard = contract["standardisation"]
    if standard["required_band_indices"] != list(range(7)):
        raise EvidenceError("all seven bands are required")
    if standard["coverage_checkpoints"] != [
        0.01,
        0.05,
        0.25,
        0.5,
        0.75,
        0.95,
        0.99,
    ]:
        raise EvidenceError("coverage checkpoints changed")
    if int(standard["calibration_replicates"]) != 4095:
        raise EvidenceError("calibration replicate count changed")
    if int(standard["validation_replicates"]) != 8192:
        raise EvidenceError("validation replicate count changed")
    if float(standard["maximum_absolute_admission_error"]) != 0.03:
        raise EvidenceError("calibration error bar changed")
    if int(standard["physical_null_minimum_sites_per_stratum"]) != 256:
        raise EvidenceError("physical-null site floor changed")
    if float(standard["physical_null_familywise_confidence"]) != 0.99:
        raise EvidenceError("physical-null confidence changed")
    if float(standard["focus_power_checkpoint"]) != 0.5:
        raise EvidenceError("focus-power checkpoint changed")
    if float(noise["familywise_confidence"]) != 0.95:
        raise EvidenceError("noise familywise confidence changed")
    if float(noise["power_target"]) != 0.95:
        raise EvidenceError("noise power target changed")
    if int(noise["bootstrap_replicates"]) != 8192:
        raise EvidenceError("noise bootstrap replicate count changed")


def validate_sources(contract: dict[str, Any]) -> None:
    for relative, expected in contract["source_baseline"]["files"].items():
        path = ROOT / Path(relative)
        if not path.exists():
            raise EvidenceError(f"missing pinned source: {relative}")
        got = sha256(path)
        if got != expected:
            raise EvidenceError(f"source hash drift: {relative}: {got} != {expected}")
    for spec, expected in contract["source_baseline"]["historical_blobs"].items():
        try:
            payload = subprocess.check_output(["git", "show", spec], cwd=ROOT)
        except subprocess.CalledProcessError as error:
            raise EvidenceError(
                f"cannot read pinned historical blob: {spec}"
            ) from error
        got = hashlib.sha256(payload).hexdigest()
        if got != expected:
            raise EvidenceError(f"historical blob drift: {spec}: {got} != {expected}")
    for relative, first, last, needle in SOURCE_ANCHORS:
        lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
        if first < 1 or last > len(lines):
            raise EvidenceError(
                f"citation range outside file: {relative}:{first}-{last}"
            )
        if needle not in "\n".join(lines[first - 1 : last]):
            raise EvidenceError(
                f"citation anchor missing: {relative}:{first}-{last}: {needle!r}"
            )
    for spec, first, last, needle in HISTORICAL_ANCHORS:
        payload = subprocess.check_output(["git", "show", spec], cwd=ROOT)
        lines = payload.decode("utf-8").splitlines()
        if needle not in "\n".join(lines[first - 1 : last]):
            raise EvidenceError(
                f"historical citation anchor missing: {spec}:{first}-{last}"
            )


def validate_document() -> None:
    text = PREREG_PATH.read_text(encoding="utf-8")
    collapsed = " ".join(text.split())
    for required in REQUIRED_DOCUMENT_TEXT:
        if " ".join(required.split()) not in collapsed:
            raise EvidenceError(
                f"preregistration is missing required text: {required!r}"
            )
    for relative, first, last, _ in SOURCE_ANCHORS:
        citation = f"`{relative}:{first}-{last}`"
        if citation not in text:
            raise EvidenceError(f"preregistration is missing citation {citation}")
    for spec, first, last, _ in HISTORICAL_ANCHORS:
        citation = f"`{spec}:{first}-{last}`"
        if citation not in text:
            raise EvidenceError(f"preregistration is missing citation {citation}")


def checked_ref(
    ref: Any,
    base: Path,
    allowed_root: Path,
    label: str,
) -> Path:
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
        raise EvidenceError(f"{label}: artifact reference must contain path and sha256")
    relative = ref["path"]
    expected = ref["sha256"]
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise EvidenceError(f"{label}: artifact path must be non-empty and relative")
    if not isinstance(expected, str) or not HEX64.fullmatch(expected):
        raise EvidenceError(f"{label}: invalid sha256")
    path = (base / relative).resolve()
    root = allowed_root.resolve()
    if path != root and root not in path.parents:
        raise EvidenceError(f"{label}: artifact escapes allowed root")
    if not path.is_file():
        raise EvidenceError(f"{label}: missing required artifact: {path}")
    got = sha256(path)
    if got != expected:
        raise EvidenceError(f"{label}: artifact hash mismatch: {got} != {expected}")
    return path


def checked_json_ref(
    ref: Any,
    base: Path,
    allowed_root: Path,
    label: str,
) -> tuple[Path, dict[str, Any]]:
    path = checked_ref(ref, base, allowed_root, label)
    return path, load_json(path)


def verify_ref_list(
    refs: Any,
    base: Path,
    allowed_root: Path,
    label: str,
) -> None:
    if not isinstance(refs, list) or not refs:
        raise EvidenceError(f"{label}: expected non-empty artifact-reference list")
    for index, ref in enumerate(refs):
        checked_ref(ref, base, allowed_root, f"{label}[{index}]")


def checked_distinct_refs(
    refs: Any,
    base: Path,
    allowed_root: Path,
    label: str,
    *,
    expected_count: int,
    distinct_hashes: bool,
) -> list[Path]:
    if not isinstance(refs, list) or len(refs) != expected_count:
        raise EvidenceError(f"{label}: expected {expected_count} artifact references")
    paths = [
        checked_ref(ref, base, allowed_root, f"{label}[{index}]")
        for index, ref in enumerate(refs)
    ]
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise EvidenceError(f"{label}: duplicate artifact reference")
    if distinct_hashes:
        hashes = [sha256(path) for path in paths]
        if len(set(hashes)) != len(hashes):
            raise EvidenceError(f"{label}: independently required artifacts are equal")
    return paths


def checked_unique_strings(values: Any, count: int, label: str) -> list[str]:
    if (
        not isinstance(values, list)
        or len(values) != count
        or any(not isinstance(value, str) or not value for value in values)
        or len(set(values)) != count
    ):
        raise EvidenceError(f"{label}: expected {count} unique identities")
    return values


def reject_supplied_conclusions(
    value: Any, forbidden: set[str], path: str = "$"
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                raise EvidenceError(f"{path}.{key}: supplied conclusion is forbidden")
            reject_supplied_conclusions(child, forbidden, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_supplied_conclusions(child, forbidden, f"{path}[{index}]")


def valid_ledger(ledger: Any, selected_sites: int | None) -> bool:
    if not isinstance(ledger, dict):
        return False
    detail = ledger.get("detail")
    hull = ledger.get("hull")
    noise = ledger.get("noise")
    if not isinstance(detail, list) or not detail or len(detail) != len(set(detail)):
        return False
    if not isinstance(hull, list) or not hull or len(hull) != len(set(hull)):
        return False
    if not isinstance(noise, dict) or not noise:
        return False
    for values in (detail, hull):
        if any(not isinstance(value, str) or not value for value in values):
            return False
    for capture, sites in noise.items():
        if not isinstance(capture, str) or not capture:
            return False
        if (
            not isinstance(sites, list)
            or not sites
            or len(sites) != len(set(sites))
            or any(not isinstance(site, str) or not site for site in sites)
        ):
            return False
        if selected_sites is not None and len(sites) != selected_sites:
            return False
    return True


def ledgers_are_disjoint(development: dict[str, Any], holdout: dict[str, Any]) -> bool:
    return bool(
        set(development["detail"]).isdisjoint(holdout["detail"])
        and set(development["hull"]).isdisjoint(holdout["hull"])
        and set(development["noise"]).isdisjoint(holdout["noise"])
    )


def compatibility_values(values: Any, trials: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if (
        array.ndim != 1
        or len(array) != trials
        or not np.all(np.isfinite(array))
        or np.any(array < 0.0)
        or np.any(array > 1.0)
    ):
        raise EvidenceError(f"{label}: invalid trial-level compatibility values")
    return array


def curve_max_error(values: Any, checkpoints: list[float], trials: int) -> float:
    compatibility = compatibility_values(values, trials, "coverage")
    maximum = 0.0
    for checkpoint in checkpoints:
        admitted = int(np.count_nonzero(compatibility <= checkpoint))
        maximum = max(maximum, abs(admitted / trials - checkpoint))
    return maximum


def validate_standardisation(
    document: dict[str, Any],
    base: Path,
    evidence_root: Path,
    contract: dict[str, Any],
    *,
    require_pass: bool,
) -> float:
    cfg = contract["standardisation"]
    reject_supplied_conclusions(
        document,
        set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
    )
    if (
        document.get("schema")
        != contract["evidence_contract"]["standardisation_schema"]
    ):
        raise EvidenceError("wrong standardisation evidence schema")
    if int(document.get("calibration_replicates", -1)) != int(
        cfg["calibration_replicates"]
    ):
        raise EvidenceError("standardisation calibration count mismatch")
    if int(document.get("validation_replicates", -1)) != int(
        cfg["validation_replicates"]
    ):
        raise EvidenceError("standardisation validation count mismatch")
    if document.get("winner_selection") != "PRODUCTION_EXACT_STACK":
        raise EvidenceError(
            "standardisation did not execute production winner selection"
        )
    if document.get("noise_stage") != "POISSON_GAUSSIAN_BEFORE_WARP":
        raise EvidenceError("standardisation noise was not generated before warp")
    checked_ref(
        document.get("generator"), base, evidence_root, "standardisation.generator"
    )
    checked_ref(
        document.get("calibration_bank_manifest"),
        base,
        evidence_root,
        "standardisation.calibration_bank_manifest",
    )
    checked_ref(
        document.get("noise_model"),
        base,
        evidence_root,
        "standardisation.noise_model",
    )
    manifests = document.get("manifests")
    if not isinstance(manifests, list) or not manifests:
        raise EvidenceError("standardisation manifest list is empty")
    manifest_sizes: dict[str, int] = {}
    for manifest in manifests:
        digest = str(manifest.get("sha256", ""))
        stack_size = int(manifest.get("stack_size", -1))
        if not HEX64.fullmatch(digest) or stack_size < 2 or digest in manifest_sizes:
            raise EvidenceError("invalid or duplicate standardisation manifest")
        manifest_sizes[digest] = stack_size

    bands = [int(value) for value in cfg["required_band_indices"]]
    anchors = [float(value) for value in cfg["q_over_f_anchors"]]
    gains = range(int(cfg["required_gain_modes"]))
    quantiles = range(int(cfg["required_signal_quantiles"]))
    required = {
        (digest, frame, band, anchor, gain, quantile)
        for digest, stack_size in manifest_sizes.items()
        for frame in range(stack_size)
        for band in bands
        for anchor in anchors
        for gain in gains
        for quantile in quantiles
    }
    cells = document.get("validation_cells")
    if not isinstance(cells, list):
        raise EvidenceError("standardisation validation_cells missing")
    seen: set[tuple[str, int, int, float, int, int]] = set()
    maximum_error = 0.0
    validation_trials = int(cfg["validation_replicates"])
    checkpoints = [float(value) for value in cfg["coverage_checkpoints"]]
    offsets = [float(value) for value in cfg["focus_offset_sigma_anchors"]]
    focus_confidence = float(cfg["physical_null_familywise_confidence"])
    for cell in cells:
        key = (
            str(cell.get("manifest_sha256", "")),
            int(cell.get("frame_ordinal", -1)),
            int(cell.get("band", -1)),
            float(cell.get("q_over_f_anchor", math.nan)),
            int(cell.get("gain_mode", -1)),
            int(cell.get("signal_quantile", -1)),
        )
        if key in seen:
            raise EvidenceError(f"duplicate standardisation cell: {key}")
        seen.add(key)
        maximum_error = max(
            maximum_error,
            curve_max_error(
                cell.get("compatibility_u"), checkpoints, validation_trials
            ),
        )
        focus = cell.get("focus_power")
        if not isinstance(focus, list) or len(focus) != len(offsets):
            raise EvidenceError(f"missing focus-power ladder: {key}")
        got_offsets = [float(row.get("offset_sigma", math.nan)) for row in focus]
        if got_offsets != offsets:
            raise EvidenceError(f"wrong focus-power offsets: {key}")
        power_checkpoint = float(cfg["focus_power_checkpoint"])
        intervals = []
        for row in focus:
            values = compatibility_values(
                row.get("compatibility_u"),
                validation_trials,
                f"focus power {key}",
            )
            admitted = int(np.count_nonzero(values <= power_checkpoint))
            intervals.append(
                wilson_interval(admitted, validation_trials, focus_confidence)
            )
        if not all(
            next_interval[1] < previous_interval[0]
            for previous_interval, next_interval in zip(intervals, intervals[1:])
        ):
            raise EvidenceError(f"focus-power ladder lacks ordered separation: {key}")
    if seen != required:
        missing = len(required - seen)
        extra = len(seen - required)
        raise EvidenceError(
            f"standardisation stratum coverage mismatch: missing={missing}, extra={extra}"
        )

    sessions = cfg.get("physical_null_sessions")
    if not isinstance(sessions, list) or not sessions:
        raise EvidenceError("physical-null sessions are not bound")
    physical = document.get("physical_null_cells")
    if not isinstance(physical, list):
        raise EvidenceError("physical_null_cells missing")
    physical_required = {
        (session, band, gain)
        for session in sessions
        for band in bands
        for gain in gains
    }
    physical_seen: set[tuple[str, int, int]] = set()
    predicate_count = len(physical_required) * len(checkpoints)
    family_confidence = float(cfg["physical_null_familywise_confidence"])
    cell_confidence = 1.0 - (1.0 - family_confidence) / predicate_count
    minimum_sites = int(cfg["physical_null_minimum_sites_per_stratum"])
    for cell in physical:
        key = (
            str(cell.get("session_id", "")),
            int(cell.get("band", -1)),
            int(cell.get("gain_mode", -1)),
        )
        if key in physical_seen:
            raise EvidenceError(f"duplicate physical-null cell: {key}")
        physical_seen.add(key)
        values = np.asarray(cell.get("compatibility_u"), dtype=np.float64)
        if (
            values.ndim != 1
            or len(values) < minimum_sites
            or not np.all(np.isfinite(values))
            or np.any(values < 0.0)
            or np.any(values > 1.0)
        ):
            raise EvidenceError(f"invalid physical-null trials: {key}")
        for checkpoint in checkpoints:
            admitted = int(np.count_nonzero(values <= checkpoint))
            trials = len(values)
            lower, upper = wilson_interval(admitted, trials, cell_confidence)
            if not lower <= checkpoint <= upper:
                raise EvidenceError(
                    f"physical-null coverage fails at {key}, checkpoint={checkpoint}"
                )
    if physical_seen != physical_required:
        raise EvidenceError("physical-null stratum coverage mismatch")
    if require_pass and maximum_error > float(cfg["maximum_absolute_admission_error"]):
        raise EvidenceError(
            f"standardisation maximum admission error {maximum_error:.9g} exceeds bar"
        )
    return maximum_error


def artifact_refs_from_request(
    request: dict[str, Any],
    base: Path,
    evidence_root: Path,
    label: str,
) -> None:
    refs = request.get("artifacts")
    verify_ref_list(refs, base, evidence_root, f"{label}.artifacts")


def verify_detail_binding(
    contract: dict[str, Any],
    contract_path: Path,
) -> dict[str, Path]:
    binding = contract["detail_instrument"]
    if binding.get("binding_state") != "BOUND":
        raise EvidenceError("physical M135 binding is absent")
    fields = (
        "checker_entrypoint",
        "checker_bundle_manifest",
        "environment_manifest",
        "physical_preregistration",
        "comparison_rule",
        "commissioning_request",
    )
    paths = {
        field: checked_ref(
            binding.get(field),
            contract_path.parent,
            ROOT,
            f"detail_instrument.{field}",
        )
        for field in fields
    }
    bundle = load_json(paths["checker_bundle_manifest"])
    if bundle.get("schema") != binding["bundle_manifest_schema"]:
        raise EvidenceError("M135 checker bundle manifest has wrong schema")
    verify_ref_list(
        bundle.get("files"),
        paths["checker_bundle_manifest"].parent,
        ROOT,
        "M135 checker bundle",
    )
    if sha256(paths["checker_entrypoint"]) not in {
        ref["sha256"] for ref in bundle["files"]
    }:
        raise EvidenceError(
            "M135 checker entrypoint is absent from its bundle manifest"
        )
    return paths


def run_m135_checker(
    mode: str,
    request_path: Path,
    binding_paths: dict[str, Path],
    contract: dict[str, Any],
) -> dict[str, Any]:
    checker = binding_paths["checker_entrypoint"]
    command = [
        sys.executable,
        "-I",
        str(checker),
        "--m138-commission" if mode == "commission" else "--m138-evaluate",
        str(request_path),
    ]
    completed = subprocess.run(
        command,
        cwd=checker.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise EvidenceError(
            f"M135 checker {mode} failed with exit {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise EvidenceError(
            f"M135 checker {mode} did not emit one JSON object"
        ) from error
    expected_hashes = {
        "checker_sha256": sha256(checker),
        "checker_bundle_manifest_sha256": sha256(
            binding_paths["checker_bundle_manifest"]
        ),
        "environment_manifest_sha256": sha256(binding_paths["environment_manifest"]),
        "physical_preregistration_sha256": sha256(
            binding_paths["physical_preregistration"]
        ),
        "comparison_rule_sha256": sha256(binding_paths["comparison_rule"]),
        "request_sha256": sha256(request_path),
    }
    if output.get("schema") != contract["detail_instrument"]["interface_schema"]:
        raise EvidenceError(f"M135 checker {mode} returned the wrong schema")
    for field, expected in expected_hashes.items():
        if output.get(field) != expected:
            raise EvidenceError(f"M135 checker {mode} returned wrong {field}")
    return output


def commission_m135(
    binding_paths: dict[str, Path],
    contract: dict[str, Any],
) -> None:
    request_path = binding_paths["commissioning_request"]
    request = load_json(request_path)
    reject_supplied_conclusions(
        request,
        set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
    )
    if request.get("schema") != "m135-m138-commission-request/v1":
        raise EvidenceError("M135 commissioning request has wrong schema")
    artifact_refs_from_request(request, request_path.parent, ROOT, "M135 commission")
    output = run_m135_checker("commission", request_path, binding_paths, contract)
    controls = output.get("controls")
    expected = set(contract["detail_instrument"]["required_commissioning_controls"])
    if not isinstance(controls, dict) or set(controls) != expected:
        raise EvidenceError("M135 commissioning controls are incomplete")
    if not all(controls[name] is True for name in expected):
        raise EvidenceError("M135 physical commissioning failed")


def evaluate_m135(
    request_ref: Any,
    base: Path,
    evidence_root: Path,
    expected_captures: list[str],
    binding_paths: dict[str, Path],
    contract: dict[str, Any],
    cache: dict[str, dict[str, Any]],
) -> bool:
    request_path = checked_ref(
        request_ref, base, evidence_root, "M135 evaluation request"
    )
    request_hash = sha256(request_path)
    if request_hash not in cache:
        request = load_json(request_path)
        reject_supplied_conclusions(
            request,
            set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
        )
        if request.get("schema") != "m135-m138-evaluate-request/v1":
            raise EvidenceError("M135 evaluation request has wrong schema")
        if request.get("capture_ids") != expected_captures:
            raise EvidenceError("M135 evaluation request capture ledger mismatch")
        artifact_refs_from_request(
            request, request_path.parent, evidence_root, "M135 evaluate"
        )
        cache[request_hash] = run_m135_checker(
            "evaluate", request_path, binding_paths, contract
        )
    output = cache[request_hash]
    states = output.get(contract["detail_instrument"]["decision_state_field"])
    passes = output.get("detail_pass_by_capture")
    if not isinstance(states, dict) or set(states) != set(expected_captures):
        raise EvidenceError("M135 checker returned the wrong state ledger")
    if not isinstance(passes, dict):
        raise EvidenceError("M135 checker omitted its valid-decision Boolean map")
    valid_states = set(contract["detail_instrument"]["valid_decision_states"])
    invalid_state = contract["detail_instrument"]["invalid_decision_state"]
    valid_captures: set[str] = set()
    invalid_captures: list[str] = []
    for capture_id in expected_captures:
        state = states[capture_id]
        if state == invalid_state:
            if capture_id in passes:
                raise EvidenceError(
                    f"M135 coerced internally invalid {capture_id} to a Boolean"
                )
            invalid_captures.append(capture_id)
            continue
        if state not in valid_states:
            raise EvidenceError(
                f"M135 returned unknown state for {capture_id}: {state}"
            )
        valid_captures.add(capture_id)
        expected_boolean = state == "DETAIL_PASS"
        if type(passes.get(capture_id)) is not bool:
            raise EvidenceError(f"M135 omitted valid decision for {capture_id}")
        if passes[capture_id] is not expected_boolean:
            raise EvidenceError(f"M135 state/Boolean disagreement for {capture_id}")
    if set(passes) != valid_captures:
        raise EvidenceError("M135 Boolean map contains an invalid capture")
    if invalid_captures:
        raise EvidenceError(
            "M135 detail instrument internally invalid for "
            + ", ".join(sorted(invalid_captures))
        )
    return all(passes.values())


def verify_temporal_extractor_binding(
    contract: dict[str, Any],
    contract_path: Path,
) -> dict[str, Path]:
    binding = contract["noise_instrument"]
    fields = (
        "extractor_entrypoint",
        "extractor_bundle_manifest",
        "extractor_environment_manifest",
    )
    paths = {
        field: checked_ref(
            binding.get(field),
            contract_path.parent,
            ROOT,
            f"noise_instrument.{field}",
        )
        for field in fields
    }
    bundle = load_json(paths["extractor_bundle_manifest"])
    if bundle.get("schema") != binding["extractor_bundle_manifest_schema"]:
        raise EvidenceError("temporal extractor bundle manifest has wrong schema")
    verify_ref_list(
        bundle.get("files"),
        paths["extractor_bundle_manifest"].parent,
        ROOT,
        "temporal extractor bundle",
    )
    if sha256(paths["extractor_entrypoint"]) not in {
        ref["sha256"] for ref in bundle["files"]
    }:
        raise EvidenceError(
            "temporal extractor entrypoint is absent from its bundle manifest"
        )
    return paths


def run_temporal_extractor(
    mode: str,
    request_path: Path,
    capture_id: str,
    extractor_paths: dict[str, Path],
    contract: dict[str, Any],
) -> dict[str, Any]:
    extractor = extractor_paths["extractor_entrypoint"]
    command = [
        sys.executable,
        "-I",
        str(extractor),
        "--m138-pilot" if mode == "PILOT" else "--m138-scored",
        str(request_path),
        "--capture-id",
        capture_id,
    ]
    completed = subprocess.run(
        command,
        cwd=extractor.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if completed.returncode != 0:
        raise EvidenceError(
            f"temporal extractor {mode.lower()} failed with exit "
            f"{completed.returncode}: {completed.stderr.strip()}"
        )
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise EvidenceError(
            f"temporal extractor {mode.lower()} did not emit one JSON object"
        ) from error
    expected = {
        "schema": contract["noise_instrument"]["extractor_interface_schema"],
        "mode": mode,
        "extractor_sha256": sha256(extractor),
        "request_sha256": sha256(request_path),
        "capture_id": capture_id,
    }
    for field, value in expected.items():
        if output.get(field) != value:
            raise EvidenceError(
                f"temporal extractor {mode.lower()} returned wrong {field}"
            )
    return output


def powers_from_extractor_output(
    output: dict[str, Any],
    expected_sites: list[str],
    pair_names: tuple[str, str],
    contract: dict[str, Any],
) -> dict[str, dict[str, np.ndarray]]:
    if output.get("site_ids") != expected_sites:
        raise EvidenceError(
            f"{output.get('capture_id')}: temporal extractor site ledger mismatch"
        )
    planes = contract["noise_instrument"]["required_cfa_planes"]
    rows = output.get("planes")
    if not isinstance(rows, dict) or set(rows) != set(planes):
        raise EvidenceError(
            f"{output.get('capture_id')}: temporal extractor planes incomplete"
        )
    result: dict[str, dict[str, np.ndarray]] = {}
    for plane in planes:
        pairs = rows[plane]
        if not isinstance(pairs, dict) or set(pairs) != set(pair_names):
            raise EvidenceError(
                f"{output.get('capture_id')}/{plane}: extractor pair ledger mismatch"
            )
        result[plane] = {}
        for pair_name in pair_names:
            row = pairs[pair_name]
            if not isinstance(row, dict) or set(row) != {
                "squared_difference_sum",
                "sample_count",
            }:
                raise EvidenceError(
                    f"{output.get('capture_id')}/{plane}/{pair_name}: "
                    "extractor sufficient statistics malformed"
                )
            sums = np.asarray(row["squared_difference_sum"], dtype=np.float64)
            counts = np.asarray(row["sample_count"])
            if (
                sums.ndim != 1
                or len(sums) != len(expected_sites)
                or counts.shape != sums.shape
                or not np.all(np.isfinite(sums))
                or np.any(sums <= 0.0)
                or not np.issubdtype(counts.dtype, np.integer)
                or np.any(counts <= 0)
            ):
                raise EvidenceError(
                    f"{output.get('capture_id')}/{plane}/{pair_name}: "
                    "invalid extractor sufficient statistics"
                )
            powers = 0.5 * sums / counts.astype(np.float64)
            if not np.all(np.isfinite(powers)) or np.any(powers <= 0.0):
                raise EvidenceError(
                    f"{output.get('capture_id')}/{plane}/{pair_name}: "
                    "recomputed temporal site power is invalid"
                )
            result[plane][pair_name] = powers
    return result


def parse_noise_cells(
    document: dict[str, Any],
    request_path: Path,
    evidence_root: Path,
    expected_noise: dict[str, list[str]],
    contract: dict[str, Any],
    extractor_paths: dict[str, Path],
) -> list[dict[str, Any]]:
    reject_supplied_conclusions(
        document,
        set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
    )
    if set(document) != {"schema", "captures"}:
        raise EvidenceError("temporal-noise request contains unregistered fields")
    if document.get("schema") != contract["evidence_contract"]["noise_schema"]:
        raise EvidenceError("wrong temporal-noise evidence schema")
    captures = document.get("captures")
    if not isinstance(captures, dict) or set(captures) != set(expected_noise):
        raise EvidenceError("temporal-noise capture ledger mismatch")
    cells: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    seen_source_hashes: set[str] = set()
    seen_output_paths: set[Path] = set()
    for capture_id, expected_sites in expected_noise.items():
        capture = captures[capture_id]
        if not isinstance(capture, dict) or set(capture) != {
            "site_ids",
            "site_manifest",
            "source_capture_ids",
            "source_captures",
            "candidate_outputs",
            "legacy_outputs",
        }:
            raise EvidenceError(f"{capture_id}: temporal request fields are incomplete")
        if capture.get("site_ids") != expected_sites:
            raise EvidenceError(f"{capture_id}: temporal site ledger mismatch")
        checked_ref(
            capture.get("site_manifest"),
            request_path.parent,
            evidence_root,
            f"{capture_id}.site_manifest",
        )
        source_ids = checked_unique_strings(
            capture.get("source_capture_ids"), 2, f"{capture_id}.source_capture_ids"
        )
        if seen_source_ids.intersection(source_ids):
            raise EvidenceError(
                f"{capture_id}: source-capture identity reused across captures"
            )
        seen_source_ids.update(source_ids)
        source_paths = checked_distinct_refs(
            capture.get("source_captures"),
            request_path.parent,
            evidence_root,
            f"{capture_id}.source_captures",
            expected_count=2,
            distinct_hashes=True,
        )
        source_hashes = {sha256(path) for path in source_paths}
        if seen_source_hashes.intersection(source_hashes):
            raise EvidenceError(
                f"{capture_id}: independent source artifact reused across captures"
            )
        seen_source_hashes.update(source_hashes)
        candidate_paths = checked_distinct_refs(
            capture.get("candidate_outputs"),
            request_path.parent,
            evidence_root,
            f"{capture_id}.candidate_outputs",
            expected_count=2,
            distinct_hashes=True,
        )
        legacy_paths = checked_distinct_refs(
            capture.get("legacy_outputs"),
            request_path.parent,
            evidence_root,
            f"{capture_id}.legacy_outputs",
            expected_count=2,
            distinct_hashes=True,
        )
        if len({path.resolve() for path in candidate_paths + legacy_paths}) != 4:
            raise EvidenceError(
                f"{capture_id}: candidate/legacy output roles reuse an artifact"
            )
        resolved_outputs = {path.resolve() for path in candidate_paths + legacy_paths}
        if seen_output_paths.intersection(resolved_outputs):
            raise EvidenceError(f"{capture_id}: output artifact reused across captures")
        seen_output_paths.update(resolved_outputs)
        output = run_temporal_extractor(
            "SCORED",
            request_path,
            capture_id,
            extractor_paths,
            contract,
        )
        powers = powers_from_extractor_output(
            output,
            expected_sites,
            ("candidate", "legacy"),
            contract,
        )
        for plane in contract["noise_instrument"]["required_cfa_planes"]:
            cells.append(
                {
                    "capture_id": capture_id,
                    "plane": plane,
                    "candidate": powers[plane]["candidate"],
                    "legacy": powers[plane]["legacy"],
                }
            )
    return cells


def transform_noise_cells(
    cells: list[dict[str, Any]],
    transform: str,
) -> list[dict[str, Any]]:
    if transform in {"IDENTITY", "ADD_IDENTICAL_SCENE_TERM_TO_BOTH_CANDIDATE_REPEATS"}:
        factor = 1.0
    elif transform == "DOUBLE_CANDIDATE_TEMPORAL_POWER":
        factor = 2.0
    elif transform == "HALVE_CANDIDATE_TEMPORAL_POWER":
        factor = 0.5
    else:
        raise EvidenceError(f"unknown registered temporal transform: {transform}")
    return [
        {
            "capture_id": cell["capture_id"],
            "plane": cell["plane"],
            "candidate": np.asarray(cell["candidate"], dtype=np.float64) * factor,
            "legacy": np.asarray(cell["legacy"], dtype=np.float64).copy(),
        }
        for cell in cells
    ]


def noise_acceptance_upper(contract: dict[str, Any]) -> float:
    cfg = contract["noise_instrument"]
    if cfg["minimum_effect_binding_state"] == "UNBOUND":
        return float(cfg["natural_null_power_ratio"])
    required_rms = cfg.get("required_rms_reduction")
    if not isinstance(required_rms, (int, float)) or not 0.0 < required_rms < 1.0:
        raise EvidenceError("bound minimum effect lacks a valid RMS reduction")
    return (1.0 - float(required_rms)) ** 2


def bootstrap_noise(
    cells: list[dict[str, Any]],
    contract: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    cfg = contract["noise_instrument"]
    replicates = int(cfg["bootstrap_replicates"])
    confidence = float(cfg["familywise_confidence"])
    rng = np.random.default_rng(stable_seed(int(cfg["bootstrap_seed"]), label))
    observed: list[float] = []
    errors: list[np.ndarray] = []
    cell_labels: list[tuple[str, str]] = []
    by_capture: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        by_capture.setdefault(cell["capture_id"], []).append(cell)
    for capture_id in sorted(by_capture):
        capture_cells = sorted(by_capture[capture_id], key=lambda row: row["plane"])
        size = len(capture_cells[0]["candidate"])
        if any(len(row["candidate"]) != size for row in capture_cells):
            raise EvidenceError(f"{capture_id}: plane site counts differ")
        picks = rng.integers(0, size, size=(replicates, size))
        for row in capture_cells:
            candidate = row["candidate"]
            legacy = row["legacy"]
            theta = math.log(float(candidate.mean() / legacy.mean()))
            sampled = np.log(candidate[picks].mean(axis=1) / legacy[picks].mean(axis=1))
            observed.append(theta)
            errors.append(sampled - theta)
            cell_labels.append((capture_id, row["plane"]))
    error_matrix = np.column_stack(errors)
    q_upper = percentile_higher(np.max(error_matrix, axis=1), confidence)
    q_two_sided = percentile_higher(np.max(np.abs(error_matrix), axis=1), confidence)
    theta = np.asarray(observed)
    upper = np.exp(theta + q_upper)
    lower_two = np.exp(theta - q_two_sided)
    upper_two = np.exp(theta + q_two_sided)
    effect_by_capture_plane: dict[str, dict[str, dict[str, float]]] = {}
    for index, (capture_id, plane) in enumerate(cell_labels):
        effect_by_capture_plane.setdefault(capture_id, {})[plane] = {
            "estimated_power_ratio": float(np.exp(theta[index])),
            "simultaneous_confidence_lower": float(lower_two[index]),
            "simultaneous_confidence_upper": float(upper_two[index]),
            "simultaneous_one_sided_upper": float(upper[index]),
        }
    return {
        "point": np.exp(theta),
        "upper": upper,
        "lower_two_sided": lower_two,
        "upper_two_sided": upper_two,
        "score": -float(np.max(theta)),
        "passes_superiority": bool(np.all(upper < 1.0)),
        "minimum_guaranteed_rms_reduction": 1.0 - math.sqrt(float(np.max(upper))),
        "effect_by_capture_plane": effect_by_capture_plane,
    }


def achieved_effect_payload(
    summary: dict[str, Any],
    expected_noise: dict[str, list[str]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    cfg = contract["noise_instrument"]
    cells = summary.get("effect_by_capture_plane")
    expected_captures = set(expected_noise)
    expected_planes = set(cfg["required_cfa_planes"])
    if not isinstance(cells, dict) or set(cells) != expected_captures:
        raise EvidenceError("achieved effect lacks the registered capture ledger")
    for capture_id, planes in cells.items():
        if not isinstance(planes, dict) or set(planes) != expected_planes:
            raise EvidenceError(
                f"{capture_id}: achieved effect lacks the registered CFA planes"
            )
        for plane, row in planes.items():
            if not isinstance(row, dict) or set(row) != set(
                cfg["required_effect_cell_fields"]
            ):
                raise EvidenceError(
                    f"{capture_id}/{plane}: achieved effect fields are incomplete"
                )
            estimate = float(row["estimated_power_ratio"])
            lower = float(row["simultaneous_confidence_lower"])
            upper = float(row["simultaneous_confidence_upper"])
            decision_upper = float(row["simultaneous_one_sided_upper"])
            if (
                not all(
                    math.isfinite(value)
                    for value in (estimate, lower, upper, decision_upper)
                )
                or min(estimate, lower, upper, decision_upper) <= 0.0
                or not lower <= estimate <= upper
            ):
                raise EvidenceError(
                    f"{capture_id}/{plane}: achieved effect interval is invalid"
                )
    minimum_state = cfg["minimum_effect_binding_state"]
    required_rms = cfg.get("required_rms_reduction")
    if minimum_state == "UNBOUND":
        minimum_effect = {
            "symbol": cfg["minimum_effect_symbol"],
            "binding_state": "UNBOUND",
            "required_rms_reduction": None,
            "required_power_ratio_upper": None,
            "claim": cfg["unbound_minimum_effect_claim"],
        }
    else:
        if not isinstance(required_rms, (int, float)):
            raise EvidenceError("bound minimum effect lacks its RMS value")
        minimum_effect = {
            "symbol": cfg["minimum_effect_symbol"],
            "binding_state": "BOUND",
            "required_rms_reduction": float(required_rms),
            "required_power_ratio_upper": noise_acceptance_upper(contract),
            "claim": "PREREGISTERED_MINIMUM_EFFECT_MET",
        }
    payload = {
        "schema": cfg["effect_output_schema"],
        "estimand": "P_candidate / P_legacy",
        "reference": cfg["reference"],
        "decision_boundary": float(cfg["natural_null_power_ratio"]),
        "familywise_confidence": float(cfg["familywise_confidence"]),
        "interval_method": "SIMULTANEOUS_TWO_SIDED_MAX_ABSOLUTE_BOOTSTRAP",
        "decision_bound_method": "SIMULTANEOUS_ONE_SIDED_MAX_BOOTSTRAP",
        "by_capture_and_plane": cells,
        "maximum_simultaneous_one_sided_upper": float(np.max(summary["upper"])),
        "minimum_guaranteed_rms_reduction": float(
            summary["minimum_guaranteed_rms_reduction"]
        ),
        "minimum_effect": minimum_effect,
        "scorecard_m2": {
            "licensed": False,
            "reference": cfg["scorecard_m2_reference"],
            "reason": (
                "W1 compares candidate Strehl with legacy Strehl; scorecard M2 "
                "compares Strehl with a shipping comparator and has separate bars."
            ),
        },
    }
    validate_achieved_effect_output(payload, expected_noise, contract)
    return payload


def validate_achieved_effect_output(
    payload: Any,
    expected_noise: dict[str, list[str]],
    contract: dict[str, Any],
) -> None:
    cfg = contract["noise_instrument"]
    if not isinstance(payload, dict) or set(payload) != {
        "schema",
        "estimand",
        "reference",
        "decision_boundary",
        "familywise_confidence",
        "interval_method",
        "decision_bound_method",
        "by_capture_and_plane",
        "maximum_simultaneous_one_sided_upper",
        "minimum_guaranteed_rms_reduction",
        "minimum_effect",
        "scorecard_m2",
    }:
        raise EvidenceError("achieved-effect verdict object is incomplete")
    if (
        payload["schema"] != cfg["effect_output_schema"]
        or payload["estimand"] != "P_candidate / P_legacy"
        or payload["reference"] != "LEGACY_STREHL"
        or float(payload["decision_boundary"]) != 1.0
        or float(payload["familywise_confidence"])
        != float(cfg["familywise_confidence"])
        or payload["interval_method"] != "SIMULTANEOUS_TWO_SIDED_MAX_ABSOLUTE_BOOTSTRAP"
        or payload["decision_bound_method"] != "SIMULTANEOUS_ONE_SIDED_MAX_BOOTSTRAP"
    ):
        raise EvidenceError("achieved-effect verdict metadata is invalid")
    cells = payload["by_capture_and_plane"]
    if not isinstance(cells, dict) or set(cells) != set(expected_noise):
        raise EvidenceError("achieved-effect verdict capture ledger is incomplete")
    required_planes = set(cfg["required_cfa_planes"])
    decision_uppers: list[float] = []
    for capture_id, planes in cells.items():
        if not isinstance(planes, dict) or set(planes) != required_planes:
            raise EvidenceError(
                f"{capture_id}: achieved-effect verdict plane ledger is incomplete"
            )
        for plane, row in planes.items():
            if not isinstance(row, dict) or set(row) != set(
                cfg["required_effect_cell_fields"]
            ):
                raise EvidenceError(
                    f"{capture_id}/{plane}: achieved-effect verdict cell is incomplete"
                )
            estimate = float(row["estimated_power_ratio"])
            lower = float(row["simultaneous_confidence_lower"])
            upper = float(row["simultaneous_confidence_upper"])
            decision_upper = float(row["simultaneous_one_sided_upper"])
            if (
                not all(
                    math.isfinite(value)
                    for value in (estimate, lower, upper, decision_upper)
                )
                or min(estimate, lower, upper, decision_upper) <= 0.0
                or not lower <= estimate <= upper
            ):
                raise EvidenceError(
                    f"{capture_id}/{plane}: achieved-effect verdict values are invalid"
                )
            decision_uppers.append(decision_upper)
    maximum_upper = max(decision_uppers)
    reported_maximum = float(payload["maximum_simultaneous_one_sided_upper"])
    reported_rms = float(payload["minimum_guaranteed_rms_reduction"])
    if (
        not math.isfinite(reported_maximum)
        or not math.isclose(
            reported_maximum,
            maximum_upper,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        or not math.isclose(
            reported_rms,
            1.0 - math.sqrt(maximum_upper),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
    ):
        raise EvidenceError("achieved-effect aggregate values are inconsistent")
    minimum = payload["minimum_effect"]
    if (
        not isinstance(minimum, dict)
        or set(minimum)
        != {
            "symbol",
            "binding_state",
            "required_rms_reduction",
            "required_power_ratio_upper",
            "claim",
        }
        or minimum.get("symbol") != cfg["minimum_effect_symbol"]
        or minimum.get("binding_state") != cfg["minimum_effect_binding_state"]
    ):
        raise EvidenceError("achieved-effect minimum binding is invalid")
    if minimum["binding_state"] == "UNBOUND" and (
        minimum["required_rms_reduction"] is not None
        or minimum["required_power_ratio_upper"] is not None
        or minimum["claim"] != "DIRECTION_ONLY"
    ):
        raise EvidenceError("unbound achieved effect claims a magnitude")
    if minimum["binding_state"] == "BOUND" and (
        not isinstance(minimum["required_rms_reduction"], (int, float))
        or float(minimum["required_rms_reduction"])
        != float(cfg["required_rms_reduction"])
        or not isinstance(minimum["required_power_ratio_upper"], (int, float))
        or not math.isclose(
            float(minimum["required_power_ratio_upper"]),
            noise_acceptance_upper(contract),
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        or minimum["claim"] != "PREREGISTERED_MINIMUM_EFFECT_MET"
    ):
        raise EvidenceError("bound achieved effect misstates its power target")
    scorecard = payload["scorecard_m2"]
    if (
        not isinstance(scorecard, dict)
        or set(scorecard) != {"licensed", "reference", "reason"}
        or scorecard.get("licensed") is not False
        or scorecard.get("reference") != cfg["scorecard_m2_reference"]
        or not isinstance(scorecard.get("reason"), str)
        or not scorecard["reason"].strip()
    ):
        raise EvidenceError("achieved-effect output incorrectly licenses M2")


def validate_go_output(
    output: Any,
    ledgers: dict[str, Any],
    contract: dict[str, Any],
) -> None:
    if not isinstance(output, dict) or set(output) != {
        "schema",
        "verdict",
        "selected_tau",
        "achieved_effect",
    }:
        raise EvidenceError("PHASE1_GO lacks its mandatory achieved effect")
    if (
        output["schema"] != contract["evidence_contract"]["adjudication_output_schema"]
        or output["verdict"] != contract["verdicts"]["go"]
    ):
        raise EvidenceError("PHASE1_GO metadata is invalid")
    effects = output["achieved_effect"]
    if not isinstance(effects, dict) or set(effects) != set(
        contract["noise_instrument"]["required_go_effect_phases"]
    ):
        raise EvidenceError("PHASE1_GO effect phases are incomplete")
    for phase in contract["noise_instrument"]["required_go_effect_phases"]:
        validate_achieved_effect_output(
            effects[phase],
            ledgers[phase]["noise"],
            contract,
        )
        if float(effects[phase]["maximum_simultaneous_one_sided_upper"]) >= float(
            contract["noise_instrument"]["natural_null_power_ratio"]
        ):
            raise EvidenceError("PHASE1_GO achieved effect does not clear the null")
        if contract["noise_instrument"][
            "minimum_effect_binding_state"
        ] == "BOUND" and float(
            effects[phase]["maximum_simultaneous_one_sided_upper"]
        ) > noise_acceptance_upper(contract):
            raise EvidenceError(
                "PHASE1_GO achieved effect does not meet the bound minimum"
            )


def parse_noise_pilot(
    document: dict[str, Any],
    request_path: Path,
    evidence_root: Path,
    contract: dict[str, Any],
    extractor_paths: dict[str, Path],
) -> list[dict[str, Any]]:
    reject_supplied_conclusions(
        document,
        set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
    )
    if set(document) != {"schema", "captures"}:
        raise EvidenceError("temporal-noise pilot contains unregistered fields")
    if document.get("schema") != contract["noise_instrument"]["pilot_request_schema"]:
        raise EvidenceError("wrong temporal-noise pilot schema")
    captures = document.get("captures")
    if not isinstance(captures, dict) or not captures:
        raise EvidenceError("noise pilot has no captures")
    cells: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    seen_source_paths: set[Path] = set()
    seen_source_hashes: set[str] = set()
    for capture_id, capture in captures.items():
        if not isinstance(capture, dict) or set(capture) != {
            "target_capture_id",
            "site_ids",
            "site_manifest",
            "source_capture_ids",
            "source_outputs",
        }:
            raise EvidenceError(f"{capture_id}: pilot request fields are incomplete")
        target_capture_id = capture.get("target_capture_id")
        if not isinstance(target_capture_id, str) or not target_capture_id:
            raise EvidenceError(f"{capture_id}: pilot target capture is missing")
        source_ids = checked_unique_strings(
            capture.get("source_capture_ids"),
            4,
            f"{capture_id}.pilot_source_capture_ids",
        )
        if seen_source_ids.intersection(source_ids):
            raise EvidenceError(f"{capture_id}: pilot source-capture identity reused")
        seen_source_ids.update(source_ids)
        source_paths = checked_distinct_refs(
            capture.get("source_outputs"),
            request_path.parent,
            evidence_root,
            f"{capture_id}.pilot_source_outputs",
            expected_count=4,
            distinct_hashes=True,
        )
        resolved = {path.resolve() for path in source_paths}
        hashes = {sha256(path) for path in source_paths}
        if seen_source_paths.intersection(resolved):
            raise EvidenceError(f"{capture_id}: pilot output artifact reused")
        if seen_source_hashes.intersection(hashes):
            raise EvidenceError(f"{capture_id}: pilot output hash reused")
        seen_source_paths.update(resolved)
        seen_source_hashes.update(hashes)
        sites = capture.get("site_ids")
        if (
            not isinstance(sites, list)
            or len(sites) < 64
            or len(sites) != len(set(sites))
            or any(not isinstance(site, str) or not site for site in sites)
        ):
            raise EvidenceError(f"{capture_id}: pilot needs at least 64 unique sites")
        checked_ref(
            capture.get("site_manifest"),
            request_path.parent,
            evidence_root,
            f"{capture_id}.pilot_site_manifest",
        )
        output = run_temporal_extractor(
            "PILOT",
            request_path,
            capture_id,
            extractor_paths,
            contract,
        )
        powers = powers_from_extractor_output(
            output,
            sites,
            ("pair_a", "pair_b"),
            contract,
        )
        for plane in contract["noise_instrument"]["required_cfa_planes"]:
            cells.append(
                {
                    "capture_id": capture_id,
                    "target_capture_id": target_capture_id,
                    "plane": plane,
                    "candidate": powers[plane]["pair_a"],
                    "legacy": powers[plane]["pair_b"],
                }
            )
    return cells


def pilot_power(
    cells: list[dict[str, Any]],
    sites: int,
    rms_reduction: float,
    contract: dict[str, Any],
    label: str,
) -> dict[str, float | int]:
    cfg = contract["noise_instrument"]
    if sites < 1 or any(len(cell["candidate"]) < sites for cell in cells):
        raise EvidenceError(
            "power analysis requests more sites than the pilot contains"
        )
    replicates = int(cfg["bootstrap_replicates"])
    confidence = float(cfg["familywise_confidence"])
    rng = np.random.default_rng(stable_seed(int(cfg["bootstrap_seed"]), label))
    errors: list[np.ndarray] = []
    by_capture: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        by_capture.setdefault(cell["capture_id"], []).append(cell)
    for capture_id in sorted(by_capture):
        capture_cells = sorted(by_capture[capture_id], key=lambda row: row["plane"])
        available = len(capture_cells[0]["candidate"])
        picks = rng.integers(0, available, size=(replicates, sites))
        for row in capture_cells:
            candidate = row["candidate"]
            legacy = row["legacy"]
            theta = math.log(float(candidate.mean() / legacy.mean()))
            sampled = np.log(candidate[picks].mean(axis=1) / legacy[picks].mean(axis=1))
            errors.append(sampled - theta)
    error_matrix = np.column_stack(errors)
    max_error = np.max(error_matrix, axis=1)
    q_upper = percentile_higher(max_error, confidence)
    shift = 2.0 * math.log(1.0 - rms_reduction)
    success = int(
        np.count_nonzero(np.max(error_matrix + shift + q_upper, axis=1) < 0.0)
    )
    lower = one_sided_wilson_lower(success, replicates, confidence)
    return {
        "sites": sites,
        "successes": success,
        "trials": replicates,
        "point_power": success / replicates,
        "lower_confidence_power": lower,
    }


def verify_noise_binding(
    contract: dict[str, Any],
    contract_path: Path,
    ledgers: dict[str, Any],
) -> dict[str, Any]:
    cfg = contract["noise_instrument"]
    if cfg.get("binding_state") != "BOUND":
        raise EvidenceError("temporal-noise extractor and site binding is absent")
    extractor_paths = verify_temporal_extractor_binding(contract, contract_path)
    sites = cfg.get("selected_sites_per_capture")
    if not isinstance(sites, int) or sites < 64:
        raise EvidenceError("selected temporal site count is not bound")
    minimum_state = cfg["minimum_effect_binding_state"]
    rms = cfg.get("required_rms_reduction")
    requirement_ref = cfg.get("effect_requirement")
    pilot_ref = cfg.get("pilot_evidence")
    if minimum_state == "UNBOUND":
        if any(value is not None for value in (rms, requirement_ref, pilot_ref)):
            raise EvidenceError(
                "unbound minimum effect carries a value, requirement, or pilot"
            )
        return {
            "extractor_paths": extractor_paths,
            "minimum_effect_binding_state": "UNBOUND",
            "effect_requirement_sha256": None,
            "pilot_sha256": None,
            "power_at_64_sites": None,
            "power_at_selected_sites": None,
        }
    if not isinstance(rms, (int, float)) or not 0.0 < float(rms) < 1.0:
        raise EvidenceError("bound minimum effect lacks a valid RMS reduction")
    requirement_path, requirement = checked_json_ref(
        requirement_ref,
        contract_path.parent,
        ROOT,
        "noise effect requirement",
    )
    if requirement.get("schema") != cfg["effect_requirement_schema"]:
        raise EvidenceError("noise effect requirement has wrong schema")
    if float(requirement.get("required_rms_reduction", math.nan)) != float(rms):
        raise EvidenceError("noise effect requirement disagrees with contract")
    if requirement.get("authority") != cfg["required_effect_authority"]:
        raise EvidenceError("noise effect requirement lacks the registered authority")
    checked_ref(
        requirement.get("approval_artifact"),
        requirement_path.parent,
        ROOT,
        "noise effect approval",
    )
    if (
        not isinstance(requirement.get("claim_text"), str)
        or not requirement["claim_text"].strip()
    ):
        raise EvidenceError("noise effect requirement lacks claim text")
    pilot_path, pilot = checked_json_ref(
        pilot_ref,
        contract_path.parent,
        ROOT,
        "noise pilot evidence",
    )
    cells = parse_noise_pilot(
        pilot,
        pilot_path,
        ROOT,
        contract,
        extractor_paths,
    )
    pilot_mapping: dict[str, str] = {}
    for cell in cells:
        prior = pilot_mapping.setdefault(cell["capture_id"], cell["target_capture_id"])
        if prior != cell["target_capture_id"]:
            raise EvidenceError("noise pilot capture has inconsistent target mapping")
    pilot_targets = list(pilot_mapping.values())
    required_targets = set(ledgers["development"]["noise"]) | set(
        ledgers["holdout"]["noise"]
    )
    if (
        len(pilot_targets) != len(set(pilot_targets))
        or set(pilot_targets) != required_targets
    ):
        raise EvidenceError("noise pilot does not map exactly to every scored capture")
    at_64: dict[str, Any] = {}
    selected_power: dict[str, Any] = {}
    for phase in ("development", "holdout"):
        target_ids = set(ledgers[phase]["noise"])
        phase_cells = [
            cell for cell in cells if cell["target_capture_id"] in target_ids
        ]
        at_64[phase] = pilot_power(
            phase_cells,
            64,
            float(rms),
            contract,
            f"power-at-64-{phase}",
        )
        selected_power[phase] = pilot_power(
            phase_cells,
            sites,
            float(rms),
            contract,
            f"power-at-selected-{phase}",
        )
        if selected_power[phase]["lower_confidence_power"] < float(cfg["power_target"]):
            raise EvidenceError(
                f"selected temporal site count misses {phase} familywise power target"
            )
    return {
        "extractor_paths": extractor_paths,
        "minimum_effect_binding_state": "BOUND",
        "effect_requirement_sha256": sha256(requirement_path),
        "pilot_sha256": sha256(pilot_path),
        "power_at_64_sites": at_64,
        "power_at_selected_sites": selected_power,
    }


def finite_positive_samples(value: Any, minimum: int, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if (
        array.ndim != 1
        or len(array) < minimum
        or not np.all(np.isfinite(array))
        or np.any(array <= 0.0)
    ):
        raise EvidenceError(f"{label}: expected finite positive timing samples")
    return array


def verify_cost_binding(
    contract: dict[str, Any],
    contract_path: Path,
) -> dict[str, float]:
    cfg = contract["cost"]
    if cfg.get("binding_state") != "BOUND":
        raise EvidenceError("campaign cost remains unsupported")
    fields = (
        "benchmark_artifact",
        "workload_manifest",
        "benchmark_runner",
        "benchmark_runner_bundle",
        "environment_manifest",
    )
    paths = {
        field: checked_ref(
            cfg.get(field),
            contract_path.parent,
            ROOT,
            f"cost.{field}",
        )
        for field in fields
    }
    bundle = load_json(paths["benchmark_runner_bundle"])
    if bundle.get("schema") != cfg["runner_bundle_schema"]:
        raise EvidenceError("cost runner bundle has wrong schema")
    verify_ref_list(
        bundle.get("files"),
        paths["benchmark_runner_bundle"].parent,
        ROOT,
        "cost runner bundle",
    )
    if sha256(paths["benchmark_runner"]) not in {
        ref["sha256"] for ref in bundle["files"]
    }:
        raise EvidenceError("cost benchmark runner is absent from its bundle")

    workload = load_json(paths["workload_manifest"])
    if set(workload) != {"schema", "units"}:
        raise EvidenceError("cost workload manifest contains unregistered fields")
    if workload.get("schema") != cfg["workload_schema"]:
        raise EvidenceError("cost workload manifest has wrong schema")
    units = workload.get("units")
    required_counts = {
        "calibration_cells",
        "candidate_render_arms",
        "legacy_render_arms",
        "scoring_arms",
    }
    if (
        not isinstance(units, dict)
        or set(units) != required_counts
        or any(
            not isinstance(units[name], list)
            or not units[name]
            or len(units[name]) != len(set(units[name]))
            or any(not isinstance(unit, str) or not unit for unit in units[name])
            for name in units
        )
    ):
        raise EvidenceError("cost workload unit ledgers are incomplete or invalid")
    counts = {name: len(units[name]) for name in units}

    benchmark = load_json(paths["benchmark_artifact"])
    if set(benchmark) != {
        "schema",
        "runner_sha256",
        "runner_bundle_sha256",
        "environment_sha256",
        "workload_sha256",
        "render_orders",
        "measurements",
    }:
        raise EvidenceError("cost benchmark contains unregistered fields")
    if benchmark.get("schema") != cfg["benchmark_schema"]:
        raise EvidenceError("cost benchmark artifact has wrong schema")
    expected_hashes = {
        "runner_sha256": sha256(paths["benchmark_runner"]),
        "runner_bundle_sha256": sha256(paths["benchmark_runner_bundle"]),
        "environment_sha256": sha256(paths["environment_manifest"]),
        "workload_sha256": sha256(paths["workload_manifest"]),
    }
    for field, expected in expected_hashes.items():
        if benchmark.get(field) != expected:
            raise EvidenceError(f"cost benchmark returned wrong {field}")
    orders = benchmark.get("render_orders")
    if (
        not isinstance(orders, list)
        or len(orders) != len(cfg["required_render_orders"])
        or set(orders) != set(cfg["required_render_orders"])
    ):
        raise EvidenceError("cost benchmark lacks both registered render orders")
    measurements = benchmark.get("measurements")
    required_measurements = set(cfg["required_measurements"])
    if not isinstance(measurements, dict) or set(measurements) != required_measurements:
        raise EvidenceError("cost benchmark measurements are incomplete")
    minimum = int(cfg["minimum_warm_repetitions_per_measurement"])
    samples = {
        name: finite_positive_samples(
            measurements[name],
            minimum,
            f"cost.{name}",
        )
        for name in required_measurements
    }
    unit = {name: float(np.median(values)) for name, values in samples.items()}
    exclusive_seconds = (
        unit["calibration_cell_seconds"] * counts["calibration_cells"]
        + unit["candidate_render_arm_seconds"] * counts["candidate_render_arms"]
        + unit["legacy_render_arm_seconds"] * counts["legacy_render_arms"]
        + unit["scoring_arm_seconds"] * counts["scoring_arms"]
    )
    contention = float(np.max(samples["contention_multiplier"]))
    if contention < 1.0:
        raise EvidenceError("cost contention multiplier must be at least one")
    exclusive_hours = exclusive_seconds / 3600.0
    shared_hours = exclusive_hours * contention
    reported_exclusive = cfg.get("reported_exclusive_wall_hours")
    reported_shared = cfg.get("reported_shared_host_wall_hours")
    if (
        not isinstance(reported_exclusive, (int, float))
        or not math.isfinite(float(reported_exclusive))
        or not math.isclose(
            float(reported_exclusive), exclusive_hours, rel_tol=1e-12, abs_tol=1e-12
        )
    ):
        raise EvidenceError("reported exclusive cost was not derived from benchmark")
    if (
        not isinstance(reported_shared, (int, float))
        or not math.isfinite(float(reported_shared))
        or not math.isclose(
            float(reported_shared), shared_hours, rel_tol=1e-12, abs_tol=1e-12
        )
    ):
        raise EvidenceError("reported shared-host cost was not derived from benchmark")
    return {
        "exclusive_wall_hours": exclusive_hours,
        "shared_host_wall_hours": shared_hours,
    }


def validate_frozen_bindings(
    contract: dict[str, Any],
    contract_path: Path,
) -> dict[str, Any]:
    if contract["status"] != contract["activation"]["required_status"]:
        raise EvidenceError("contract is a draft and is not frozen")
    checked_ref(
        contract["activation"].get("independent_review"),
        contract_path.parent,
        ROOT,
        "independent review",
    )
    if not HEX40.fullmatch(str(contract["activation"].get("frozen_commit", ""))):
        raise EvidenceError("frozen commit is absent")
    detail_paths = verify_detail_binding(contract, contract_path)
    ledgers = contract["capture_ledgers"]
    selected_sites = contract["noise_instrument"].get("selected_sites_per_capture")
    if ledgers.get("binding_state") != "BOUND":
        raise EvidenceError("capture ledgers are unbound")
    if not valid_ledger(ledgers.get("development"), selected_sites):
        raise EvidenceError("development ledger is invalid")
    if not valid_ledger(ledgers.get("holdout"), selected_sites):
        raise EvidenceError("holdout ledger is invalid")
    if not ledgers_are_disjoint(ledgers["development"], ledgers["holdout"]):
        raise EvidenceError("development and holdout ledgers are not disjoint")
    noise_binding = verify_noise_binding(contract, contract_path, ledgers)
    cost = verify_cost_binding(contract, contract_path)
    return {
        "detail_paths": detail_paths,
        "noise_binding": noise_binding,
        "cost": cost,
    }


def verify_pipeline(
    pipeline: Any,
    base: Path,
    evidence_root: Path,
) -> None:
    if not isinstance(pipeline, dict) or set(pipeline) != {
        "candidate_merge",
        "legacy_merge",
        "candidate_postprocess",
        "legacy_postprocess",
    }:
        raise EvidenceError("pipeline evidence is incomplete")
    checked_ref(
        pipeline["candidate_merge"],
        base,
        evidence_root,
        "candidate merge bundle",
    )
    checked_ref(pipeline["legacy_merge"], base, evidence_root, "legacy merge bundle")
    candidate_post = checked_ref(
        pipeline["candidate_postprocess"],
        base,
        evidence_root,
        "candidate postprocess bundle",
    )
    legacy_post = checked_ref(
        pipeline["legacy_postprocess"],
        base,
        evidence_root,
        "legacy postprocess bundle",
    )
    if sha256(candidate_post) != sha256(legacy_post):
        raise EvidenceError("candidate and legacy postprocess pipeline hashes differ")


def evaluate_hull(
    document: dict[str, Any],
    base: Path,
    evidence_root: Path,
    expected_captures: list[str],
    contract: dict[str, Any],
) -> bool:
    cfg = contract["hull_instrument"]
    reject_supplied_conclusions(
        document,
        set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
    )
    if document.get("schema") != contract["evidence_contract"]["hull_schema"]:
        raise EvidenceError("wrong hull evidence schema")
    if document.get("measurement_stage") != cfg["measurement_stage"]:
        raise EvidenceError("hull evidence is not PRE_CLAMP")
    captures = document.get("captures")
    if not isinstance(captures, dict) or set(captures) != set(expected_captures):
        raise EvidenceError("hull capture ledger mismatch")
    planes = contract["noise_instrument"]["required_cfa_planes"]
    maximum = 0.0
    for capture_id, capture in captures.items():
        checked_ref(
            capture.get("extractor"),
            base,
            evidence_root,
            f"{capture_id}.hull_extractor",
        )
        verify_ref_list(
            capture.get("source_outputs"),
            base,
            evidence_root,
            f"{capture_id}.hull_source_outputs",
        )
        rows = capture.get("planes")
        if not isinstance(rows, dict) or set(rows) != set(planes):
            raise EvidenceError(f"{capture_id}: hull planes incomplete")
        for plane in planes:
            row = rows[plane]
            reconstructed = np.asarray(
                row.get("reconstructed_preclamp_quantized_dn"), dtype=np.float64
            )
            lower = np.asarray(row.get("aligned_input_min_dn"), dtype=np.float64)
            upper = np.asarray(row.get("aligned_input_max_dn"), dtype=np.float64)
            if (
                reconstructed.ndim != 1
                or lower.shape != reconstructed.shape
                or upper.shape != reconstructed.shape
                or len(reconstructed) == 0
                or not np.all(np.isfinite(reconstructed))
                or not np.all(np.isfinite(lower))
                or not np.all(np.isfinite(upper))
                or np.any(lower > upper)
            ):
                raise EvidenceError(f"{capture_id}/{plane}: invalid hull arrays")
            excess = np.maximum.reduce(
                (
                    lower - reconstructed,
                    np.zeros_like(reconstructed),
                    reconstructed - upper,
                )
            )
            maximum = max(maximum, float(excess.max()))
    return maximum <= float(cfg["maximum_excess_dn"])


def load_arm_evidence(
    arm: dict[str, Any],
    base: Path,
    evidence_root: Path,
    ledger: dict[str, Any],
    contract: dict[str, Any],
    binding_paths: dict[str, Path],
    noise_binding: dict[str, Any],
    caches: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    forbidden = set(contract["evidence_contract"]["forbidden_supplied_conclusions"])
    reject_supplied_conclusions(arm, forbidden)
    allowed = {
        "pipeline",
        "m135_request",
        "noise_evidence",
        "hull_evidence",
        "width_diagnostics",
    }
    if set(arm) - allowed or not {
        "pipeline",
        "m135_request",
        "noise_evidence",
        "hull_evidence",
    }.issubset(arm):
        raise EvidenceError(f"{label}: arm evidence fields are incomplete")
    verify_pipeline(arm["pipeline"], base, evidence_root)
    detail_pass = evaluate_m135(
        arm["m135_request"],
        base,
        evidence_root,
        ledger["detail"],
        binding_paths,
        contract,
        caches["m135"],
    )
    noise_path, noise_document = checked_json_ref(
        arm["noise_evidence"],
        base,
        evidence_root,
        f"{label}.noise_evidence",
    )
    noise_hash = sha256(noise_path)
    if noise_hash not in caches["noise"]:
        cells = parse_noise_cells(
            noise_document,
            noise_path,
            evidence_root,
            ledger["noise"],
            contract,
            noise_binding["extractor_paths"],
        )
        caches["noise"][noise_hash] = bootstrap_noise(cells, contract, label)
    noise_summary = caches["noise"][noise_hash]
    noise_pass = noise_summary["passes_superiority"] and bool(
        np.all(noise_summary["upper"] <= noise_acceptance_upper(contract))
    )
    hull_path, hull_document = checked_json_ref(
        arm["hull_evidence"],
        base,
        evidence_root,
        f"{label}.hull_evidence",
    )
    hull_hash = sha256(hull_path)
    if hull_hash not in caches["hull"]:
        caches["hull"][hull_hash] = evaluate_hull(
            hull_document,
            hull_path.parent,
            evidence_root,
            ledger["hull"],
            contract,
        )
    return {
        "passes": bool(detail_pass and noise_pass and caches["hull"][hull_hash]),
        "noise_summary": noise_summary,
    }


def validate_noise_commissioning_summaries(
    summaries: dict[str, dict[str, Any]],
) -> None:
    null = summaries["null"]
    placebo = summaries["common_scene_placebo"]
    if not (
        np.all(null["lower_two_sided"] <= 1.0)
        and np.all(null["upper_two_sided"] >= 1.0)
        and np.all(placebo["lower_two_sided"] <= 1.0)
        and np.all(placebo["upper_two_sided"] >= 1.0)
    ):
        raise EvidenceError("temporal-noise null/placebo commissioning failed")
    if not (
        summaries["inflation_defect"]["score"] < null["score"]
        and not summaries["inflation_defect"]["passes_superiority"]
        and summaries["averaging_improvement"]["score"] > null["score"]
        and summaries["averaging_improvement"]["passes_superiority"]
    ):
        raise EvidenceError("temporal-noise bidirectional commissioning failed")


def validate_commissioning(
    document: dict[str, Any],
    base: Path,
    evidence_root: Path,
    main_standard_ref: dict[str, str],
    contract: dict[str, Any],
    binding_paths: dict[str, Path],
    noise_binding: dict[str, Any],
) -> None:
    reject_supplied_conclusions(
        document,
        set(contract["evidence_contract"]["forbidden_supplied_conclusions"]),
    )
    if document.get("schema") != contract["evidence_contract"]["commissioning_schema"]:
        raise EvidenceError("wrong commissioning evidence schema")
    controls = document.get("standardisation_controls")
    if not isinstance(controls, dict) or set(controls) != {
        "null",
        "wrong_stack_defect",
        "omitted_warp_defect",
    }:
        raise EvidenceError("standardisation commissioning controls incomplete")
    if controls["null"] != main_standard_ref:
        raise EvidenceError("standardisation null is not the scored evidence")
    scores: dict[str, float] = {}
    for name, ref in controls.items():
        path, evidence = checked_json_ref(
            ref, base, evidence_root, f"standardisation control {name}"
        )
        maximum_error = validate_standardisation(
            evidence,
            path.parent,
            evidence_root,
            contract,
            require_pass=name == "null",
        )
        scores[name] = (
            float(contract["standardisation"]["maximum_absolute_admission_error"])
            - maximum_error
        )
    if not (
        scores["null"] >= 0.0
        and scores["null"] > scores["wrong_stack_defect"]
        and scores["null"] > scores["omitted_warp_defect"]
        and scores["wrong_stack_defect"] < 0.0
        and scores["omitted_warp_defect"] < 0.0
    ):
        raise EvidenceError("standardisation bidirectional commissioning failed")

    if set(document) != {
        "schema",
        "standardisation_controls",
        "noise_control_ledger",
        "noise_base",
    }:
        raise EvidenceError("commissioning evidence contains unregistered fields")
    ledger = document.get("noise_control_ledger")
    selected_sites = int(contract["noise_instrument"]["selected_sites_per_capture"])
    if not valid_ledger(ledger, selected_sites):
        raise EvidenceError("noise commissioning ledger invalid")
    path, evidence = checked_json_ref(
        document.get("noise_base"),
        base,
        evidence_root,
        "noise commissioning base",
    )
    base_cells = parse_noise_cells(
        evidence,
        path,
        evidence_root,
        ledger["noise"],
        contract,
        noise_binding["extractor_paths"],
    )
    transforms = contract["noise_instrument"]["commissioning_transforms"]
    summaries: dict[str, dict[str, Any]] = {}
    transformed: dict[str, list[dict[str, Any]]] = {}
    for name, transform in transforms.items():
        transformed[name] = transform_noise_cells(base_cells, transform)
        summaries[name] = bootstrap_noise(
            transformed[name],
            contract,
            f"commission-{name}",
        )
    validate_noise_commissioning_summaries(summaries)
    for base_cell, placebo_cell in zip(
        transformed["null"], transformed["common_scene_placebo"]
    ):
        if not (
            np.array_equal(base_cell["candidate"], placebo_cell["candidate"])
            and np.array_equal(base_cell["legacy"], placebo_cell["legacy"])
        ):
            raise EvidenceError("common-scene placebo did not cancel exactly")
    commission_m135(binding_paths, contract)


def adjudicate_result(
    result_path: Path,
    contract_path: Path = CONTRACT_PATH,
    *,
    verify_sources: bool = True,
    test_mode: bool = False,
) -> dict[str, Any]:
    verdicts: dict[str, str] = {}
    output_schema = "m138-adjudication/v2"
    try:
        contract = load_json(contract_path)
        verdicts = contract["verdicts"]
        output_schema = contract["evidence_contract"]["adjudication_output_schema"]
        validate_contract(contract, test_mode=test_mode)
        if contract["status"] != contract["activation"]["required_status"]:
            raise EvidenceError("contract is a draft and is not frozen")
        if verify_sources:
            validate_sources(contract)
        checked_ref(
            contract["activation"].get("independent_review"),
            contract_path.parent,
            ROOT,
            "independent review",
        )
        if not HEX40.fullmatch(str(contract["activation"].get("frozen_commit", ""))):
            raise EvidenceError("frozen commit is absent")
        if contract["detail_instrument"].get("binding_state") != "BOUND":
            return {
                "schema": output_schema,
                "verdict": verdicts["blocked_detail"],
                "reason": "physical M135 binding is absent",
            }
        bindings = validate_frozen_bindings(contract, contract_path)
        binding_paths = bindings["detail_paths"]
        noise_binding = bindings["noise_binding"]
        ledgers = contract["capture_ledgers"]

        result = load_json(result_path)
        forbidden = set(contract["evidence_contract"]["forbidden_supplied_conclusions"])
        reject_supplied_conclusions(result, forbidden)
        if result.get("schema") != contract["evidence_contract"]["result_schema"]:
            raise EvidenceError("wrong result manifest schema")
        if result.get("contract_sha256") != sha256(contract_path):
            raise EvidenceError("result does not bind the exact contract")
        if set(result) - {
            "schema",
            "contract_sha256",
            "standardisation",
            "commissioning",
            "development",
            "holdout",
        }:
            raise EvidenceError("result manifest contains unregistered fields")
        evidence_root = result_path.parent.resolve()
        standard_path, standard = checked_json_ref(
            result.get("standardisation"),
            result_path.parent,
            evidence_root,
            "result.standardisation",
        )
        validate_standardisation(
            standard,
            standard_path.parent,
            evidence_root,
            contract,
            require_pass=True,
        )
        commission_path, commission = checked_json_ref(
            result.get("commissioning"),
            result_path.parent,
            evidence_root,
            "result.commissioning",
        )
        validate_commissioning(
            commission,
            commission_path.parent,
            evidence_root,
            result["standardisation"],
            contract,
            binding_paths,
            noise_binding,
        )
        development_path, development = checked_json_ref(
            result.get("development"),
            result_path.parent,
            evidence_root,
            "result.development",
        )
        reject_supplied_conclusions(development, forbidden)
        if (
            development.get("schema")
            != contract["evidence_contract"]["development_schema"]
        ):
            raise EvidenceError("wrong development evidence schema")
        if development.get("ledger") != ledgers["development"]:
            raise EvidenceError("development evidence ledger mismatch")
        arms = development.get("arms")
        keys = tau_keys(contract)
        if not isinstance(arms, dict) or set(arms) != set(keys):
            raise EvidenceError("development threshold grid is incomplete")
        caches: dict[str, Any] = {"m135": {}, "noise": {}, "hull": {}}
        arm_results = {
            key: load_arm_evidence(
                arms[key],
                development_path.parent,
                evidence_root,
                ledgers["development"],
                contract,
                binding_paths,
                noise_binding,
                caches,
                f"development-{key}",
            )
            for key in keys
        }
        passing = {
            index for index, key in enumerate(keys) if arm_results[key]["passes"]
        }
        robust = [
            index
            for index in range(1, len(keys) - 1)
            if {index - 1, index, index + 1}.issubset(passing)
        ]
        if not robust:
            return {
                "schema": output_schema,
                "verdict": verdicts["refuted_development"],
                "reason": "no three-adjacent output-quality operating interval",
            }
        selected = keys[max(robust)]
        development_effect = achieved_effect_payload(
            arm_results[selected]["noise_summary"],
            ledgers["development"]["noise"],
            contract,
        )
        if result.get("holdout") is None:
            return {
                "schema": output_schema,
                "verdict": verdicts["awaiting_holdout"],
                "selected_tau": selected,
                "achieved_effect": {"development": development_effect},
            }
        holdout_path, holdout = checked_json_ref(
            result["holdout"],
            result_path.parent,
            evidence_root,
            "result.holdout",
        )
        reject_supplied_conclusions(holdout, forbidden)
        if holdout.get("schema") != contract["evidence_contract"]["holdout_schema"]:
            raise EvidenceError("wrong holdout evidence schema")
        if holdout.get("tau") != selected:
            raise EvidenceError(
                "holdout threshold differs from selected development threshold"
            )
        if holdout.get("ledger") != ledgers["holdout"]:
            raise EvidenceError("holdout evidence ledger mismatch")
        holdout_result = load_arm_evidence(
            holdout.get("arm"),
            holdout_path.parent,
            evidence_root,
            ledgers["holdout"],
            contract,
            binding_paths,
            noise_binding,
            caches,
            f"holdout-{selected}",
        )
        holdout_effect = achieved_effect_payload(
            holdout_result["noise_summary"],
            ledgers["holdout"]["noise"],
            contract,
        )
        effect = {
            "development": development_effect,
            "holdout": holdout_effect,
        }
        if not holdout_result["passes"]:
            return {
                "schema": output_schema,
                "verdict": verdicts["refuted_holdout"],
                "selected_tau": selected,
                "achieved_effect": effect,
            }
        go_output = {
            "schema": output_schema,
            "verdict": verdicts["go"],
            "selected_tau": selected,
            "achieved_effect": effect,
        }
        validate_go_output(go_output, ledgers, contract)
        return go_output
    except (
        EvidenceError,
        ArithmeticError,
        IndexError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        subprocess.SubprocessError,
    ) as error:
        return {
            "schema": output_schema,
            "verdict": verdicts.get("invalid_instrument", "INSTRUMENT_INVALID"),
            "reason": str(error),
        }


def ref_for(path: Path, base: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(base).as_posix(),
        "sha256": sha256(path),
    }


def make_uniform_compatibility(trials: int, error: float = 0.0) -> list[float]:
    return [
        max(0.0, min(1.0, (index + 0.5) / trials - error)) for index in range(trials)
    ]


def make_power_compatibility(
    trials: int, admission_rate: float, checkpoint: float
) -> list[float]:
    admitted = int(round(admission_rate * trials))
    return [checkpoint / 2.0] * admitted + [(1.0 + checkpoint) / 2.0] * (
        trials - admitted
    )


def make_standardisation(
    contract: dict[str, Any],
    manifest_sha: str,
    artifact_ref: dict[str, str],
    *,
    error: float = 0.0,
) -> dict[str, Any]:
    cfg = contract["standardisation"]
    validation_trials = int(cfg["validation_replicates"])
    focus_trials = validation_trials
    focus_rates = np.linspace(0.98, 0.02, len(cfg["focus_offset_sigma_anchors"]))
    cells = []
    for frame in range(2):
        for band in cfg["required_band_indices"]:
            for anchor in cfg["q_over_f_anchors"]:
                for gain in range(cfg["required_gain_modes"]):
                    for quantile in range(cfg["required_signal_quantiles"]):
                        cells.append(
                            {
                                "manifest_sha256": manifest_sha,
                                "frame_ordinal": frame,
                                "band": band,
                                "q_over_f_anchor": anchor,
                                "gain_mode": gain,
                                "signal_quantile": quantile,
                                "compatibility_u": make_uniform_compatibility(
                                    validation_trials, error
                                ),
                                "focus_power": [
                                    {
                                        "offset_sigma": offset,
                                        "compatibility_u": make_power_compatibility(
                                            focus_trials,
                                            float(rate),
                                            float(cfg["focus_power_checkpoint"]),
                                        ),
                                    }
                                    for offset, rate in zip(
                                        cfg["focus_offset_sigma_anchors"],
                                        focus_rates,
                                    )
                                ],
                            }
                        )
    physical = []
    physical_trials = max(4096, int(cfg["physical_null_minimum_sites_per_stratum"]))
    for session in cfg["physical_null_sessions"]:
        for band in cfg["required_band_indices"]:
            for gain in range(cfg["required_gain_modes"]):
                physical.append(
                    {
                        "session_id": session,
                        "band": band,
                        "gain_mode": gain,
                        "compatibility_u": make_uniform_compatibility(physical_trials),
                    }
                )
    return {
        "schema": contract["evidence_contract"]["standardisation_schema"],
        "calibration_replicates": cfg["calibration_replicates"],
        "validation_replicates": cfg["validation_replicates"],
        "winner_selection": "PRODUCTION_EXACT_STACK",
        "noise_stage": "POISSON_GAUSSIAN_BEFORE_WARP",
        "generator": artifact_ref,
        "calibration_bank_manifest": artifact_ref,
        "noise_model": artifact_ref,
        "manifests": [{"sha256": manifest_sha, "stack_size": 2}],
        "validation_cells": cells,
        "physical_null_cells": physical,
    }


def make_noise_evidence(
    contract: dict[str, Any],
    ledger: dict[str, list[str]],
    root: Path,
    prefix: str,
    ratio: float,
) -> dict[str, Any]:
    planes = contract["noise_instrument"]["required_cfa_planes"]
    captures: dict[str, Any] = {}
    for capture_id, sites in ledger.items():
        base_power = np.asarray(
            [1.0 + 0.001 * (index % 3) for index in range(len(sites))],
            dtype=np.float64,
        )
        source_paths = []
        for repeat in ("a", "b"):
            path = root / f"{prefix}-{capture_id}-source-{repeat}.bin"
            path.write_bytes(f"{prefix}:{capture_id}:source:{repeat}\n".encode("utf-8"))
            source_paths.append(path)
        output_specs = {
            "candidate-a": np.zeros(len(sites), dtype=np.float64),
            "candidate-b": np.sqrt(2.0 * ratio * base_power),
            "legacy-a": np.zeros(len(sites), dtype=np.float64),
            "legacy-b": np.sqrt(2.0 * base_power),
        }
        output_paths: dict[str, Path] = {}
        for role, values in output_specs.items():
            path = root / f"{prefix}-{capture_id}-{role}.json"
            write_json(
                path,
                {
                    "artifact_id": f"{prefix}:{capture_id}:{role}",
                    "site_ids": sites,
                    "planes": {plane: values.tolist() for plane in planes},
                },
            )
            output_paths[role] = path
        site_manifest = root / f"{prefix}-{capture_id}-sites.json"
        write_json(site_manifest, {"capture_id": capture_id, "site_ids": sites})
        captures[capture_id] = {
            "site_ids": sites,
            "site_manifest": ref_for(site_manifest, root),
            "source_capture_ids": [
                f"{prefix}-{capture_id}-repeat-a",
                f"{prefix}-{capture_id}-repeat-b",
            ],
            "source_captures": [ref_for(path, root) for path in source_paths],
            "candidate_outputs": [
                ref_for(output_paths["candidate-a"], root),
                ref_for(output_paths["candidate-b"], root),
            ],
            "legacy_outputs": [
                ref_for(output_paths["legacy-a"], root),
                ref_for(output_paths["legacy-b"], root),
            ],
        }
    return {
        "schema": contract["evidence_contract"]["noise_schema"],
        "captures": captures,
    }


def make_pilot_evidence(
    contract: dict[str, Any],
    root: Path,
    targets: dict[str, str],
    sites: list[str],
    *,
    anticorrelated: bool = False,
) -> dict[str, Any]:
    planes = contract["noise_instrument"]["required_cfa_planes"]
    captures: dict[str, Any] = {}
    for pilot_id, target_id in targets.items():
        if anticorrelated:
            pair_a = np.asarray(
                [0.5 if index % 2 == 0 else 1.5 for index in range(len(sites))],
                dtype=np.float64,
            )
            pair_b = np.asarray(
                [1.5 if index % 2 == 0 else 0.5 for index in range(len(sites))],
                dtype=np.float64,
            )
        else:
            pair_a = np.asarray(
                [1.0 + 0.001 * (index % 3) for index in range(len(sites))],
                dtype=np.float64,
            )
            pair_b = pair_a.copy()
        values = (
            np.zeros(len(sites), dtype=np.float64),
            np.sqrt(2.0 * pair_a),
            np.zeros(len(sites), dtype=np.float64),
            np.sqrt(2.0 * pair_b),
        )
        outputs: list[Path] = []
        for index, row in enumerate(values, start=1):
            path = root / f"{pilot_id}-burst-{index}.json"
            write_json(
                path,
                {
                    "artifact_id": f"{pilot_id}:burst:{index}",
                    "site_ids": sites,
                    "planes": {plane: row.tolist() for plane in planes},
                },
            )
            outputs.append(path)
        site_manifest = root / f"{pilot_id}-sites.json"
        write_json(site_manifest, {"capture_id": pilot_id, "site_ids": sites})
        captures[pilot_id] = {
            "target_capture_id": target_id,
            "site_ids": sites,
            "site_manifest": ref_for(site_manifest, root),
            "source_capture_ids": [
                f"{pilot_id}-source-{index}" for index in range(1, 5)
            ],
            "source_outputs": [ref_for(path, root) for path in outputs],
        }
    return {
        "schema": contract["noise_instrument"]["pilot_request_schema"],
        "captures": captures,
    }


def make_hull_evidence(
    contract: dict[str, Any],
    captures: list[str],
    artifact_ref: dict[str, str],
    excess: float,
    *,
    stage: str = "PRE_CLAMP_RECONSTRUCTION",
) -> dict[str, Any]:
    return {
        "schema": contract["evidence_contract"]["hull_schema"],
        "measurement_stage": stage,
        "captures": {
            capture_id: {
                "extractor": artifact_ref,
                "source_outputs": [artifact_ref],
                "planes": {
                    plane: {
                        "reconstructed_preclamp_quantized_dn": [0.0, 5.0 + excess],
                        "aligned_input_min_dn": [0.0, 0.0],
                        "aligned_input_max_dn": [10.0, 5.0],
                    }
                    for plane in contract["noise_instrument"]["required_cfa_planes"]
                },
            }
            for capture_id in captures
        },
    }


def fake_checker_source() -> str:
    return r"""import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--m138-evaluate")
mode.add_argument("--m138-commission")
args = parser.parse_args()
request_path = Path(args.m138_evaluate or args.m138_commission)
request = json.loads(request_path.read_text(encoding="utf-8"))
binding = request["binding_hashes"]
base = {
    "schema": "m135-m138-checker/v1",
    "checker_sha256": sha(Path(__file__)),
    "checker_bundle_manifest_sha256": binding["checker_bundle_manifest_sha256"],
    "environment_manifest_sha256": binding["environment_manifest_sha256"],
    "physical_preregistration_sha256": binding["physical_preregistration_sha256"],
    "comparison_rule_sha256": binding["comparison_rule_sha256"],
    "request_sha256": sha(request_path),
}
if args.m138_commission:
    controls = request["control_values"]
    base["controls"] = {
        "physical_null_stays_null": controls["null"] == controls["identity"],
        "pre_noise_blur_lowers_information": controls["blur"] < controls["identity"],
        "pre_noise_optical_improvement_raises_information": (
            controls["improvement"] > controls["identity"]
        ),
        "missing_flat_control_refuses": controls["missing_flat"] == "REFUSED",
        "artifact_hash_mutation_refuses": controls["hash_mutation"] == "REFUSED",
    }
else:
    states = {}
    passes = {}
    for row in request["comparisons"]:
        capture_id = row["capture_id"]
        if "force_state" in row:
            states[capture_id] = row["force_state"]
            if "force_boolean" in row:
                passes[capture_id] = row["force_boolean"]
            continue
        if row["candidate"] is None or row["legacy"] is None:
            states[capture_id] = "INSTRUMENT_INVALID"
            continue
        passed = sum(row["candidate"]) >= sum(row["legacy"])
        states[capture_id] = "DETAIL_PASS" if passed else "DETAIL_FAIL"
        passes[capture_id] = passed
    base["detail_state_by_capture"] = states
    base["detail_pass_by_capture"] = passes
print(json.dumps(base, sort_keys=True))
"""


def fake_temporal_extractor_source() -> str:
    return r"""import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_ref(request_path, ref):
    path = (request_path.parent / ref["path"]).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def pair_stats(left, right, planes, sites):
    result = {}
    for plane in planes:
        a = left["planes"][plane]
        b = right["planes"][plane]
        if left["site_ids"] != sites or right["site_ids"] != sites:
            raise SystemExit("site ledger mismatch")
        result[plane] = {
            "squared_difference_sum": [
                float((x - y) * (x - y)) for x, y in zip(a, b)
            ],
            "sample_count": [1 for _ in sites],
        }
    return result


parser = argparse.ArgumentParser()
mode = parser.add_mutually_exclusive_group(required=True)
mode.add_argument("--m138-scored")
mode.add_argument("--m138-pilot")
parser.add_argument("--capture-id", required=True)
args = parser.parse_args()
request_path = Path(args.m138_scored or args.m138_pilot)
request = json.loads(request_path.read_text(encoding="utf-8"))
capture = request["captures"][args.capture_id]
sites = capture["site_ids"]
planes = ["R", "G1", "G2", "B"]
if args.m138_scored:
    candidate = [read_ref(request_path, ref) for ref in capture["candidate_outputs"]]
    legacy = [read_ref(request_path, ref) for ref in capture["legacy_outputs"]]
    candidate_stats = pair_stats(candidate[0], candidate[1], planes, sites)
    legacy_stats = pair_stats(legacy[0], legacy[1], planes, sites)
    rows = {
        plane: {
            "candidate": candidate_stats[plane],
            "legacy": legacy_stats[plane],
        }
        for plane in planes
    }
    mode_name = "SCORED"
else:
    bursts = [read_ref(request_path, ref) for ref in capture["source_outputs"]]
    pair_a = pair_stats(bursts[0], bursts[1], planes, sites)
    pair_b = pair_stats(bursts[2], bursts[3], planes, sites)
    rows = {
        plane: {"pair_a": pair_a[plane], "pair_b": pair_b[plane]}
        for plane in planes
    }
    mode_name = "PILOT"
print(json.dumps({
    "schema": "m138-temporal-extractor/v1",
    "mode": mode_name,
    "extractor_sha256": sha(Path(__file__)),
    "request_sha256": sha(request_path),
    "capture_id": args.capture_id,
    "site_ids": sites,
    "planes": rows,
}, sort_keys=True))
"""


def run_self_test(contract: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory(prefix="m138-selftest-", dir=HERE) as directory:
        root = Path(directory)
        artifact = root / "artifact.bin"
        artifact.write_bytes(b"sealed evidence\n")
        artifact_ref = ref_for(artifact, root)
        review = root / "independent-review.txt"
        review.write_text("synthetic self-test review\n", encoding="utf-8")
        checker = root / "m135-checker.py"
        checker.write_text(fake_checker_source(), encoding="utf-8")
        temporal_extractor = root / "temporal-extractor.py"
        temporal_extractor.write_text(
            fake_temporal_extractor_source(),
            encoding="utf-8",
        )
        for name in (
            "environment.json",
            "temporal-environment.json",
            "physical-preregistration.md",
            "comparison-rule.json",
            "effect-requirement.json",
            "effect-approval.txt",
            "cost-environment.json",
            "cost-runner.py",
        ):
            (root / name).write_text(f"{name}\n", encoding="utf-8")
        write_json(
            root / "checker-bundle.json",
            {
                "schema": contract["detail_instrument"]["bundle_manifest_schema"],
                "files": [ref_for(checker, root)],
            },
        )
        write_json(
            root / "temporal-extractor-bundle.json",
            {
                "schema": contract["noise_instrument"][
                    "extractor_bundle_manifest_schema"
                ],
                "files": [ref_for(temporal_extractor, root)],
            },
        )

        bound = copy.deepcopy(contract)
        bound["status"] = "FROZEN_BEFORE_CORRECTED_GATE_OUTCOME_GENERATION"
        bound["activation"] = {
            "required_status": "FROZEN_BEFORE_CORRECTED_GATE_OUTCOME_GENERATION",
            "independent_review": ref_for(review, root),
            "frozen_commit": "1" * 40,
            "rule": contract["activation"]["rule"],
        }
        standard = bound["standardisation"]
        standard.update(
            {
                "calibration_replicates": 31,
                "validation_replicates": 100,
                "q_over_f_anchors": [0.0, 2.0],
                "coverage_checkpoints": [0.25, 0.5, 0.75],
                "physical_null_minimum_sites_per_stratum": 64,
                "focus_offset_sigma_anchors": [0.0, 2.0, 4.0],
                "required_band_indices": [0, 1],
                "required_gain_modes": 1,
                "required_signal_quantiles": 1,
                "physical_null_sessions": ["physical-null"],
            }
        )
        noise = bound["noise_instrument"]
        noise.update(
            {
                "binding_state": "BOUND",
                "bootstrap_replicates": 256,
                "minimum_effect_binding_state": "UNBOUND",
                "required_rms_reduction": None,
                "effect_requirement": None,
                "pilot_evidence": None,
                "selected_sites_per_capture": 64,
                "extractor_entrypoint": ref_for(temporal_extractor, root),
                "extractor_bundle_manifest": ref_for(
                    root / "temporal-extractor-bundle.json", root
                ),
                "extractor_environment_manifest": ref_for(
                    root / "temporal-environment.json", root
                ),
            }
        )
        effect_requirement = {
            "schema": noise["effect_requirement_schema"],
            "required_rms_reduction": 0.20,
            "authority": noise["required_effect_authority"],
            "approval_artifact": ref_for(root / "effect-approval.txt", root),
            "claim_text": "synthetic self-test effect requirement",
            "basis": "synthetic self-test only",
        }
        write_json(root / "effect-requirement.json", effect_requirement)

        sites = [f"s{index:03d}" for index in range(64)]
        development_ledger = {
            "detail": ["detail-development"],
            "noise": {"noise-development": sites},
            "hull": ["hull-development"],
        }
        holdout_ledger = {
            "detail": ["detail-holdout"],
            "noise": {"noise-holdout": sites},
            "hull": ["hull-holdout"],
        }
        bound["capture_ledgers"] = {
            "binding_state": "BOUND",
            "development": development_ledger,
            "holdout": holdout_ledger,
            "binding_rule": contract["capture_ledgers"]["binding_rule"],
            "evidence_tag": "VERIFIED-PREREGISTERED",
        }
        pilot = make_pilot_evidence(
            bound,
            root,
            {
                "pilot-development": "noise-development",
                "pilot-holdout": "noise-holdout",
            },
            sites,
        )
        write_json(root / "pilot.json", pilot)

        binding = bound["detail_instrument"]
        binding.update(
            {
                "binding_state": "BOUND",
                "checker_entrypoint": ref_for(checker, root),
                "checker_bundle_manifest": ref_for(root / "checker-bundle.json", root),
                "environment_manifest": ref_for(root / "environment.json", root),
                "physical_preregistration": ref_for(
                    root / "physical-preregistration.md", root
                ),
                "comparison_rule": ref_for(root / "comparison-rule.json", root),
            }
        )
        binding_hashes = {
            "checker_bundle_manifest_sha256": sha256(root / "checker-bundle.json"),
            "environment_manifest_sha256": sha256(root / "environment.json"),
            "physical_preregistration_sha256": sha256(
                root / "physical-preregistration.md"
            ),
            "comparison_rule_sha256": sha256(root / "comparison-rule.json"),
        }
        commission_request = {
            "schema": "m135-m138-commission-request/v1",
            "artifacts": [artifact_ref],
            "binding_hashes": binding_hashes,
            "control_values": {
                "null": 1.0,
                "identity": 1.0,
                "blur": 0.5,
                "improvement": 1.5,
                "missing_flat": "REFUSED",
                "hash_mutation": "REFUSED",
            },
        }
        write_json(root / "m135-commission-request.json", commission_request)
        binding["commissioning_request"] = ref_for(
            root / "m135-commission-request.json", root
        )
        cost = bound["cost"]
        workload = {
            "schema": cost["workload_schema"],
            "units": {
                "calibration_cells": [f"calibration-{index}" for index in range(10)],
                "candidate_render_arms": [f"candidate-{index}" for index in range(101)],
                "legacy_render_arms": ["legacy-development", "legacy-holdout"],
                "scoring_arms": [f"score-{index}" for index in range(102)],
            },
        }
        write_json(root / "cost-workload.json", workload)
        write_json(
            root / "cost-runner-bundle.json",
            {
                "schema": cost["runner_bundle_schema"],
                "files": [ref_for(root / "cost-runner.py", root)],
            },
        )
        benchmark = {
            "schema": cost["benchmark_schema"],
            "runner_sha256": sha256(root / "cost-runner.py"),
            "runner_bundle_sha256": sha256(root / "cost-runner-bundle.json"),
            "environment_sha256": sha256(root / "cost-environment.json"),
            "workload_sha256": sha256(root / "cost-workload.json"),
            "render_orders": ["candidate-first", "legacy-first"],
            "measurements": {
                "calibration_cell_seconds": [1.0, 1.0],
                "candidate_render_arm_seconds": [2.0, 2.0],
                "legacy_render_arm_seconds": [3.0, 3.0],
                "scoring_arm_seconds": [0.5, 0.5],
                "contention_multiplier": [1.25, 1.25],
            },
        }
        write_json(root / "cost-benchmark.json", benchmark)
        exclusive_hours = (10.0 + 202.0 + 6.0 + 51.0) / 3600.0
        cost.update(
            {
                "binding_state": "BOUND",
                "benchmark_artifact": ref_for(root / "cost-benchmark.json", root),
                "workload_manifest": ref_for(root / "cost-workload.json", root),
                "benchmark_runner": ref_for(root / "cost-runner.py", root),
                "benchmark_runner_bundle": ref_for(
                    root / "cost-runner-bundle.json", root
                ),
                "environment_manifest": ref_for(root / "cost-environment.json", root),
                "reported_exclusive_wall_hours": exclusive_hours,
                "reported_shared_host_wall_hours": exclusive_hours * 1.25,
            }
        )
        contract_path = root / "contract.json"
        write_json(contract_path, bound)
        validate_contract(bound, test_mode=True)
        validate_frozen_bindings(bound, contract_path)
        effect_bound = copy.deepcopy(bound)
        effect_bound["noise_instrument"].update(
            {
                "minimum_effect_binding_state": "BOUND",
                "required_rms_reduction": 0.20,
                "effect_requirement": ref_for(root / "effect-requirement.json", root),
                "pilot_evidence": ref_for(root / "pilot.json", root),
            }
        )
        effect_bound_path = root / "effect-bound-contract.json"
        write_json(effect_bound_path, effect_bound)
        validate_contract(effect_bound, test_mode=True)
        validate_frozen_bindings(effect_bound, effect_bound_path)

        manifest_sha = "a" * 64
        clean_standard = make_standardisation(
            bound, manifest_sha, artifact_ref, error=0.0
        )
        wrong_standard = make_standardisation(
            bound, manifest_sha, artifact_ref, error=0.10
        )
        omitted_standard = make_standardisation(
            bound, manifest_sha, artifact_ref, error=-0.10
        )
        write_json(root / "standard.json", clean_standard)
        write_json(root / "wrong-stack.json", wrong_standard)
        write_json(root / "omitted-warp.json", omitted_standard)

        for name, ratio in (
            ("noise-pass", 0.50),
            ("noise-fail", 1.50),
            ("noise-null", 1.00),
        ):
            write_json(
                root / f"{name}-development.json",
                make_noise_evidence(
                    bound,
                    development_ledger["noise"],
                    root,
                    name,
                    ratio,
                ),
            )
        write_json(
            root / "noise-pass-holdout.json",
            make_noise_evidence(
                bound,
                holdout_ledger["noise"],
                root,
                "noise-pass-holdout",
                0.50,
            ),
        )
        write_json(
            root / "hull-pass-development.json",
            make_hull_evidence(bound, development_ledger["hull"], artifact_ref, 0.5),
        )
        write_json(
            root / "hull-fail-holdout.json",
            make_hull_evidence(bound, holdout_ledger["hull"], artifact_ref, 2.0),
        )
        write_json(
            root / "hull-pass-holdout.json",
            make_hull_evidence(bound, holdout_ledger["hull"], artifact_ref, 0.5),
        )

        evaluate_request = {
            "schema": "m135-m138-evaluate-request/v1",
            "capture_ids": development_ledger["detail"],
            "artifacts": [artifact_ref],
            "binding_hashes": binding_hashes,
            "comparisons": [
                {
                    "capture_id": "detail-development",
                    "candidate": [2.0, 2.0],
                    "legacy": [1.0, 1.0],
                }
            ],
        }
        write_json(root / "m135-evaluate.json", evaluate_request)
        holdout_evaluate_request = copy.deepcopy(evaluate_request)
        holdout_evaluate_request["capture_ids"] = holdout_ledger["detail"]
        holdout_evaluate_request["comparisons"][0]["capture_id"] = "detail-holdout"
        write_json(root / "m135-evaluate-holdout.json", holdout_evaluate_request)

        commissioning = {
            "schema": bound["evidence_contract"]["commissioning_schema"],
            "standardisation_controls": {
                "null": ref_for(root / "standard.json", root),
                "wrong_stack_defect": ref_for(root / "wrong-stack.json", root),
                "omitted_warp_defect": ref_for(root / "omitted-warp.json", root),
            },
            "noise_control_ledger": development_ledger,
            "noise_base": ref_for(root / "noise-null-development.json", root),
        }
        write_json(root / "commissioning.json", commissioning)

        pipeline = {
            "candidate_merge": artifact_ref,
            "legacy_merge": artifact_ref,
            "candidate_postprocess": artifact_ref,
            "legacy_postprocess": artifact_ref,
        }
        passing_arm = {
            "pipeline": pipeline,
            "m135_request": ref_for(root / "m135-evaluate.json", root),
            "noise_evidence": ref_for(root / "noise-pass-development.json", root),
            "hull_evidence": ref_for(root / "hull-pass-development.json", root),
            "width_diagnostics": {"ignored": True},
        }
        holdout_arm = {
            "pipeline": pipeline,
            "m135_request": ref_for(root / "m135-evaluate-holdout.json", root),
            "noise_evidence": ref_for(root / "noise-pass-holdout.json", root),
            "hull_evidence": ref_for(root / "hull-pass-holdout.json", root),
            "width_diagnostics": {"ignored": True},
        }
        development = {
            "schema": bound["evidence_contract"]["development_schema"],
            "ledger": development_ledger,
            "arms": {key: copy.deepcopy(passing_arm) for key in tau_keys(bound)},
        }
        write_json(root / "development.json", development)
        holdout = {
            "schema": bound["evidence_contract"]["holdout_schema"],
            "tau": "0.99",
            "ledger": holdout_ledger,
            "arm": copy.deepcopy(holdout_arm),
        }
        write_json(root / "holdout.json", holdout)
        result = {
            "schema": bound["evidence_contract"]["result_schema"],
            "contract_sha256": sha256(contract_path),
            "standardisation": ref_for(root / "standard.json", root),
            "commissioning": ref_for(root / "commissioning.json", root),
            "development": ref_for(root / "development.json", root),
            "holdout": ref_for(root / "holdout.json", root),
        }
        write_json(root / "result.json", result)
        green = adjudicate_result(
            root / "result.json",
            contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert green["schema"] == "m138-adjudication/v2", green
        assert green["verdict"] == "PHASE1_GO", green
        assert green["selected_tau"] == "0.99", green
        json.dumps(green, allow_nan=False)
        assert set(green["achieved_effect"]) == {"development", "holdout"}, green
        for phase, capture_id in (
            ("development", "noise-development"),
            ("holdout", "noise-holdout"),
        ):
            achieved = green["achieved_effect"][phase]
            assert achieved["reference"] == "LEGACY_STREHL", achieved
            assert achieved["scorecard_m2"]["licensed"] is False, achieved
            assert achieved["minimum_effect"] == {
                "symbol": "delta_required",
                "binding_state": "UNBOUND",
                "required_rms_reduction": None,
                "required_power_ratio_upper": None,
                "claim": "DIRECTION_ONLY",
            }, achieved
            rows = achieved["by_capture_and_plane"]
            assert set(rows) == {capture_id}, achieved
            assert set(rows[capture_id]) == {"R", "G1", "G2", "B"}, achieved
            for row in rows[capture_id].values():
                assert math.isclose(
                    row["estimated_power_ratio"],
                    0.5,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ), row
                assert (
                    row["simultaneous_confidence_lower"]
                    <= row["estimated_power_ratio"]
                    <= row["simultaneous_confidence_upper"]
                ), row
        bound_effect_result = copy.deepcopy(result)
        bound_effect_result["contract_sha256"] = sha256(effect_bound_path)
        write_json(root / "bound-effect-result.json", bound_effect_result)
        bound_effect_verdict = adjudicate_result(
            root / "bound-effect-result.json",
            effect_bound_path,
            verify_sources=False,
            test_mode=True,
        )
        assert bound_effect_verdict["verdict"] == "PHASE1_GO", bound_effect_verdict
        for achieved in bound_effect_verdict["achieved_effect"].values():
            minimum = achieved["minimum_effect"]
            assert minimum["symbol"] == "delta_required", achieved
            assert minimum["binding_state"] == "BOUND", achieved
            assert minimum["required_rms_reduction"] == 0.20, achieved
            assert math.isclose(
                minimum["required_power_ratio_upper"],
                0.64,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ), achieved
            assert minimum["claim"] == "PREREGISTERED_MINIMUM_EFFECT_MET", achieved
        strict_effect_requirement = copy.deepcopy(effect_requirement)
        strict_effect_requirement["required_rms_reduction"] = 0.40
        write_json(
            root / "strict-effect-requirement.json",
            strict_effect_requirement,
        )
        strict_effect_bound = copy.deepcopy(effect_bound)
        strict_effect_bound["noise_instrument"]["required_rms_reduction"] = 0.40
        strict_effect_bound["noise_instrument"]["effect_requirement"] = ref_for(
            root / "strict-effect-requirement.json",
            root,
        )
        strict_effect_bound_path = root / "strict-effect-bound-contract.json"
        write_json(strict_effect_bound_path, strict_effect_bound)
        validate_contract(strict_effect_bound, test_mode=True)
        validate_frozen_bindings(strict_effect_bound, strict_effect_bound_path)
        strict_effect_result = copy.deepcopy(result)
        strict_effect_result["contract_sha256"] = sha256(strict_effect_bound_path)
        write_json(root / "strict-effect-result.json", strict_effect_result)
        strict_effect_verdict = adjudicate_result(
            root / "strict-effect-result.json",
            strict_effect_bound_path,
            verify_sources=False,
            test_mode=True,
        )
        assert strict_effect_verdict["verdict"] in {
            "PHASE1_REFUTED_NO_ROBUST_GLOBAL_TAU",
            "PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT",
        }, strict_effect_verdict
        bare_go = {
            "schema": "m138-adjudication/v2",
            "verdict": "PHASE1_GO",
            "selected_tau": "0.99",
        }
        try:
            validate_go_output(bare_go, bound["capture_ledgers"], bound)
        except EvidenceError:
            pass
        else:
            raise AssertionError("bare PHASE1_GO was accepted")
        incomplete_go = copy.deepcopy(green)
        del incomplete_go["achieved_effect"]["holdout"]["by_capture_and_plane"][
            "noise-holdout"
        ]["R"]["simultaneous_confidence_upper"]
        try:
            validate_go_output(incomplete_go, bound["capture_ledgers"], bound)
        except EvidenceError:
            pass
        else:
            raise AssertionError("PHASE1_GO with incomplete effect was accepted")

        try:
            validate_noise_commissioning_summaries(
                {
                    "null": {
                        "score": 0.0,
                        "lower_two_sided": np.asarray([0.9]),
                        "upper_two_sided": np.asarray([1.1]),
                    },
                    "common_scene_placebo": {
                        "lower_two_sided": np.asarray([0.9]),
                        "upper_two_sided": np.asarray([1.1]),
                    },
                    "inflation_defect": {
                        "score": -0.1,
                        "passes_superiority": True,
                    },
                    "averaging_improvement": {
                        "score": 0.1,
                        "passes_superiority": True,
                    },
                }
            )
        except EvidenceError:
            pass
        else:
            raise AssertionError(
                "commissioning accepted inflation that passed superiority"
            )

        missing = copy.deepcopy(result)
        missing["development"] = {
            "path": "required-but-missing.json",
            "sha256": "0" * 64,
        }
        write_json(root / "missing.json", missing)
        missing_result = adjudicate_result(
            root / "missing.json",
            contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert missing_result["verdict"] == "INSTRUMENT_INVALID", missing_result
        assert "missing required artifact" in missing_result["reason"], missing_result

        missing_curve = copy.deepcopy(clean_standard)
        del missing_curve["validation_cells"][0]["compatibility_u"]
        write_json(root / "missing-curve.json", missing_curve)
        missing_curve_result = copy.deepcopy(result)
        missing_curve_result["standardisation"] = ref_for(
            root / "missing-curve.json", root
        )
        write_json(root / "missing-curve-result.json", missing_curve_result)
        assert (
            adjudicate_result(
                root / "missing-curve-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        missing_power = make_noise_evidence(
            bound,
            development_ledger["noise"],
            root,
            "missing-temporal-output",
            0.50,
        )
        missing_power["captures"]["noise-development"]["candidate_outputs"][0] = {
            "path": "missing-temporal-output.bin",
            "sha256": "0" * 64,
        }
        write_json(root / "missing-temporal-output.json", missing_power)
        missing_power_development = copy.deepcopy(development)
        missing_power_development["arms"]["0.50"]["noise_evidence"] = ref_for(
            root / "missing-temporal-output.json", root
        )
        write_json(
            root / "missing-site-power-development.json",
            missing_power_development,
        )
        missing_power_result = copy.deepcopy(result)
        missing_power_result["development"] = ref_for(
            root / "missing-site-power-development.json", root
        )
        write_json(root / "missing-site-power-result.json", missing_power_result)
        assert (
            adjudicate_result(
                root / "missing-site-power-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        duplicate_output = load_json(root / "noise-pass-development.json")
        duplicate_output["captures"]["noise-development"]["candidate_outputs"][1] = (
            duplicate_output["captures"]["noise-development"]["candidate_outputs"][0]
        )
        write_json(root / "duplicate-output.json", duplicate_output)
        duplicate_development = copy.deepcopy(development)
        duplicate_development["arms"]["0.50"]["noise_evidence"] = ref_for(
            root / "duplicate-output.json", root
        )
        write_json(root / "duplicate-output-development.json", duplicate_development)
        duplicate_result = copy.deepcopy(result)
        duplicate_result["development"] = ref_for(
            root / "duplicate-output-development.json", root
        )
        write_json(root / "duplicate-output-result.json", duplicate_result)
        duplicate_verdict = adjudicate_result(
            root / "duplicate-output-result.json",
            contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert duplicate_verdict["verdict"] == "INSTRUMENT_INVALID", duplicate_verdict
        assert "duplicate artifact reference" in duplicate_verdict["reason"]

        supplied_power = load_json(root / "noise-pass-development.json")
        supplied_power["captures"]["noise-development"]["candidate_site_power"] = [
            0.01
        ] * 64
        write_json(root / "supplied-power.json", supplied_power)
        supplied_power_development = copy.deepcopy(development)
        supplied_power_development["arms"]["0.50"]["noise_evidence"] = ref_for(
            root / "supplied-power.json", root
        )
        write_json(
            root / "supplied-power-development.json",
            supplied_power_development,
        )
        supplied_power_result = copy.deepcopy(result)
        supplied_power_result["development"] = ref_for(
            root / "supplied-power-development.json", root
        )
        write_json(root / "supplied-power-result.json", supplied_power_result)
        assert (
            adjudicate_result(
                root / "supplied-power-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        missing_m135_request = copy.deepcopy(evaluate_request)
        missing_m135_request["artifacts"] = [
            {"path": "missing-m135-input.bin", "sha256": "0" * 64}
        ]
        write_json(root / "missing-m135-request.json", missing_m135_request)
        missing_m135_development = copy.deepcopy(development)
        missing_m135_development["arms"]["0.50"]["m135_request"] = ref_for(
            root / "missing-m135-request.json", root
        )
        write_json(root / "missing-m135-development.json", missing_m135_development)
        missing_m135_result = copy.deepcopy(result)
        missing_m135_result["development"] = ref_for(
            root / "missing-m135-development.json", root
        )
        write_json(root / "missing-m135-result.json", missing_m135_result)
        assert (
            adjudicate_result(
                root / "missing-m135-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        null_detail_request = copy.deepcopy(evaluate_request)
        null_detail_request["comparisons"][0]["candidate"] = None
        write_json(root / "null-detail-request.json", null_detail_request)
        null_detail_development = copy.deepcopy(development)
        null_detail_development["arms"]["0.50"]["m135_request"] = ref_for(
            root / "null-detail-request.json", root
        )
        write_json(root / "null-detail-development.json", null_detail_development)
        null_detail_result = copy.deepcopy(result)
        null_detail_result["development"] = ref_for(
            root / "null-detail-development.json", root
        )
        write_json(root / "null-detail-result.json", null_detail_result)
        null_verdict = adjudicate_result(
            root / "null-detail-result.json",
            contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert null_verdict["verdict"] == "INSTRUMENT_INVALID", null_verdict
        assert "internally invalid" in null_verdict["reason"], null_verdict

        invalid_with_false_request = copy.deepcopy(evaluate_request)
        invalid_with_false_request["comparisons"][0].update(
            {
                "force_state": "INSTRUMENT_INVALID",
                "force_boolean": False,
            }
        )
        write_json(
            root / "invalid-with-false-request.json",
            invalid_with_false_request,
        )
        invalid_with_false_development = copy.deepcopy(development)
        invalid_with_false_development["arms"]["0.50"]["m135_request"] = ref_for(
            root / "invalid-with-false-request.json", root
        )
        write_json(
            root / "invalid-with-false-development.json",
            invalid_with_false_development,
        )
        invalid_with_false_result = copy.deepcopy(result)
        invalid_with_false_result["development"] = ref_for(
            root / "invalid-with-false-development.json", root
        )
        write_json(
            root / "invalid-with-false-result.json",
            invalid_with_false_result,
        )
        invalid_with_false = adjudicate_result(
            root / "invalid-with-false-result.json",
            contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert invalid_with_false["verdict"] == "INSTRUMENT_INVALID"
        assert "coerced internally invalid" in invalid_with_false["reason"]

        null_with_false_request = copy.deepcopy(evaluate_request)
        null_with_false_request["comparisons"][0].update(
            {
                "force_state": None,
                "force_boolean": False,
            }
        )
        write_json(root / "null-with-false-request.json", null_with_false_request)
        null_with_false_development = copy.deepcopy(development)
        null_with_false_development["arms"]["0.50"]["m135_request"] = ref_for(
            root / "null-with-false-request.json", root
        )
        write_json(
            root / "null-with-false-development.json",
            null_with_false_development,
        )
        null_with_false_result = copy.deepcopy(result)
        null_with_false_result["development"] = ref_for(
            root / "null-with-false-development.json", root
        )
        write_json(root / "null-with-false-result.json", null_with_false_result)
        null_with_false = adjudicate_result(
            root / "null-with-false-result.json",
            contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert null_with_false["verdict"] == "INSTRUMENT_INVALID"
        assert "returned unknown state" in null_with_false["reason"]

        failed_detail_request = copy.deepcopy(evaluate_request)
        failed_detail_request["comparisons"][0]["candidate"] = [0.5, 0.5]
        write_json(root / "failed-detail-request.json", failed_detail_request)
        detail_no_point = copy.deepcopy(development)
        failed_detail_arm = copy.deepcopy(passing_arm)
        failed_detail_arm["m135_request"] = ref_for(
            root / "failed-detail-request.json", root
        )
        detail_no_point["arms"] = {
            key: copy.deepcopy(failed_detail_arm) for key in tau_keys(bound)
        }
        write_json(root / "detail-no-point.json", detail_no_point)
        failed_detail_result = copy.deepcopy(result)
        failed_detail_result["development"] = ref_for(
            root / "detail-no-point.json", root
        )
        failed_detail_result["holdout"] = None
        write_json(root / "failed-detail-result.json", failed_detail_result)
        assert (
            adjudicate_result(
                root / "failed-detail-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT"
        )

        alternate_pipeline = root / "alternate-postprocess.bin"
        alternate_pipeline.write_bytes(b"different postprocess\n")
        pipeline_mismatch = copy.deepcopy(development)
        pipeline_mismatch["arms"]["0.50"]["pipeline"]["candidate_postprocess"] = (
            ref_for(alternate_pipeline, root)
        )
        write_json(root / "pipeline-mismatch-development.json", pipeline_mismatch)
        pipeline_result = copy.deepcopy(result)
        pipeline_result["development"] = ref_for(
            root / "pipeline-mismatch-development.json", root
        )
        write_json(root / "pipeline-mismatch-result.json", pipeline_result)
        assert (
            adjudicate_result(
                root / "pipeline-mismatch-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        wrong_hash = copy.deepcopy(result)
        wrong_hash["standardisation"]["sha256"] = "0" * 64
        write_json(root / "wrong-hash-result.json", wrong_hash)
        assert (
            adjudicate_result(
                root / "wrong-hash-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        injected = copy.deepcopy(development)
        injected["arms"]["0.50"]["detail_pass"] = True
        write_json(root / "injected-development.json", injected)
        injected_result = copy.deepcopy(result)
        injected_result["development"] = ref_for(
            root / "injected-development.json", root
        )
        write_json(root / "injected-result.json", injected_result)
        assert (
            adjudicate_result(
                root / "injected-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        injected_effect = copy.deepcopy(development)
        injected_effect["arms"]["0.50"]["achieved_effect"] = {
            "estimated_power_ratio": 0.01
        }
        write_json(root / "injected-effect-development.json", injected_effect)
        injected_effect_result = copy.deepcopy(result)
        injected_effect_result["development"] = ref_for(
            root / "injected-effect-development.json", root
        )
        write_json(root / "injected-effect-result.json", injected_effect_result)
        assert (
            adjudicate_result(
                root / "injected-effect-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        postclamp = make_hull_evidence(
            bound,
            development_ledger["hull"],
            artifact_ref,
            0.0,
            stage="POST_CLAMP",
        )
        write_json(root / "hull-postclamp.json", postclamp)
        postclamp_development = copy.deepcopy(development)
        postclamp_development["arms"]["0.50"]["hull_evidence"] = ref_for(
            root / "hull-postclamp.json", root
        )
        write_json(root / "postclamp-development.json", postclamp_development)
        postclamp_result = copy.deepcopy(result)
        postclamp_result["development"] = ref_for(
            root / "postclamp-development.json", root
        )
        write_json(root / "postclamp-result.json", postclamp_result)
        assert (
            adjudicate_result(
                root / "postclamp-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        no_point = copy.deepcopy(development)
        failing = copy.deepcopy(passing_arm)
        failing["noise_evidence"] = ref_for(root / "noise-fail-development.json", root)
        no_point["arms"] = {key: copy.deepcopy(failing) for key in tau_keys(bound)}
        write_json(root / "no-point-development.json", no_point)
        no_point_result = copy.deepcopy(result)
        no_point_result["development"] = ref_for(
            root / "no-point-development.json", root
        )
        no_point_result["holdout"] = None
        write_json(root / "no-point-result.json", no_point_result)
        assert (
            adjudicate_result(
                root / "no-point-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT"
        )

        holdout_fail = copy.deepcopy(holdout)
        holdout_fail["arm"]["hull_evidence"] = ref_for(
            root / "hull-fail-holdout.json", root
        )
        write_json(root / "holdout-fail.json", holdout_fail)
        holdout_result = copy.deepcopy(result)
        holdout_result["holdout"] = ref_for(root / "holdout-fail.json", root)
        write_json(root / "holdout-result.json", holdout_result)
        assert (
            adjudicate_result(
                root / "holdout-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "PHASE1_REFUTED_HOLDOUT"
        )

        width_mutation = copy.deepcopy(development)
        for arm in width_mutation["arms"].values():
            arm["width_diagnostics"] = {"corrupted": 1e99}
        write_json(root / "width-development.json", width_mutation)
        width_result = copy.deepcopy(result)
        width_result["development"] = ref_for(root / "width-development.json", root)
        write_json(root / "width-result.json", width_result)
        assert (
            adjudicate_result(
                root / "width-result.json",
                contract_path,
                verify_sources=False,
                test_mode=True,
            )
            == green
        )

        bad_detail_request = copy.deepcopy(commission_request)
        bad_detail_request["control_values"]["improvement"] = 0.5
        write_json(root / "bad-detail-commission-request.json", bad_detail_request)
        bad_detail_contract = copy.deepcopy(bound)
        bad_detail_contract["detail_instrument"]["commissioning_request"] = ref_for(
            root / "bad-detail-commission-request.json", root
        )
        bad_detail_contract_path = root / "bad-detail-contract.json"
        write_json(bad_detail_contract_path, bad_detail_contract)
        bad_detail_result = copy.deepcopy(result)
        bad_detail_result["contract_sha256"] = sha256(bad_detail_contract_path)
        write_json(root / "bad-detail-result.json", bad_detail_result)
        assert (
            adjudicate_result(
                root / "bad-detail-result.json",
                bad_detail_contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        unbound_detail_contract = copy.deepcopy(bound)
        unbound_detail_contract["detail_instrument"]["binding_state"] = "UNBOUND"
        unbound_detail_contract_path = root / "unbound-detail-contract.json"
        write_json(unbound_detail_contract_path, unbound_detail_contract)
        unbound_detail_result = copy.deepcopy(result)
        unbound_detail_result["contract_sha256"] = sha256(unbound_detail_contract_path)
        write_json(root / "unbound-detail-result.json", unbound_detail_result)
        assert (
            adjudicate_result(
                root / "unbound-detail-result.json",
                unbound_detail_contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "BLOCKED_DETAIL_INSTRUMENT"
        )
        try:
            validate_frozen_bindings(
                unbound_detail_contract,
                unbound_detail_contract_path,
            )
        except EvidenceError:
            pass
        else:
            raise AssertionError("frozen check accepted unbound M135")

        unsupported_cost_contract = copy.deepcopy(bound)
        unsupported_cost_contract["cost"] = copy.deepcopy(contract["cost"])
        unsupported_cost_contract_path = root / "unsupported-cost-contract.json"
        write_json(unsupported_cost_contract_path, unsupported_cost_contract)
        unsupported_cost_result = copy.deepcopy(result)
        unsupported_cost_result["contract_sha256"] = sha256(
            unsupported_cost_contract_path
        )
        write_json(root / "unsupported-cost-result.json", unsupported_cost_result)
        assert (
            adjudicate_result(
                root / "unsupported-cost-result.json",
                unsupported_cost_contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        contradictory_effect_contract = copy.deepcopy(bound)
        contradictory_effect_contract["noise_instrument"]["required_rms_reduction"] = (
            0.20
        )
        contradictory_effect_path = root / "contradictory-effect-contract.json"
        write_json(contradictory_effect_path, contradictory_effect_contract)
        contradictory_effect_result = copy.deepcopy(result)
        contradictory_effect_result["contract_sha256"] = sha256(
            contradictory_effect_path
        )
        write_json(
            root / "contradictory-effect-result.json",
            contradictory_effect_result,
        )
        contradictory_effect_verdict = adjudicate_result(
            root / "contradictory-effect-result.json",
            contradictory_effect_path,
            verify_sources=False,
            test_mode=True,
        )
        assert contradictory_effect_verdict["verdict"] == "INSTRUMENT_INVALID"
        assert "unbound minimum effect" in contradictory_effect_verdict["reason"]

        bound_without_pilot = copy.deepcopy(effect_bound)
        bound_without_pilot["noise_instrument"]["pilot_evidence"] = None
        bound_without_pilot_path = root / "bound-without-pilot-contract.json"
        write_json(bound_without_pilot_path, bound_without_pilot)
        try:
            validate_frozen_bindings(bound_without_pilot, bound_without_pilot_path)
        except EvidenceError:
            pass
        else:
            raise AssertionError("bound minimum effect was accepted without a pilot")

        null_cost_benchmark = copy.deepcopy(benchmark)
        null_cost_benchmark["measurements"]["scoring_arm_seconds"] = [None, None]
        write_json(root / "null-cost-benchmark.json", null_cost_benchmark)
        null_cost_contract = copy.deepcopy(bound)
        null_cost_contract["cost"]["benchmark_artifact"] = ref_for(
            root / "null-cost-benchmark.json", root
        )
        null_cost_contract_path = root / "null-cost-contract.json"
        write_json(null_cost_contract_path, null_cost_contract)
        null_cost_result = copy.deepcopy(result)
        null_cost_result["contract_sha256"] = sha256(null_cost_contract_path)
        write_json(root / "null-cost-result.json", null_cost_result)
        null_cost_verdict = adjudicate_result(
            root / "null-cost-result.json",
            null_cost_contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert null_cost_verdict["verdict"] == "INSTRUMENT_INVALID"
        assert "finite positive timing samples" in null_cost_verdict["reason"]

        duplicate_pilot = copy.deepcopy(pilot)
        first_pilot = duplicate_pilot["captures"]["pilot-development"]
        first_pilot["source_outputs"][1] = first_pilot["source_outputs"][0]
        write_json(root / "duplicate-pilot.json", duplicate_pilot)
        duplicate_pilot_contract = copy.deepcopy(effect_bound)
        duplicate_pilot_contract["noise_instrument"]["pilot_evidence"] = ref_for(
            root / "duplicate-pilot.json", root
        )
        duplicate_pilot_contract_path = root / "duplicate-pilot-contract.json"
        write_json(duplicate_pilot_contract_path, duplicate_pilot_contract)
        duplicate_pilot_result = copy.deepcopy(result)
        duplicate_pilot_result["contract_sha256"] = sha256(
            duplicate_pilot_contract_path
        )
        write_json(root / "duplicate-pilot-result.json", duplicate_pilot_result)
        duplicate_pilot_verdict = adjudicate_result(
            root / "duplicate-pilot-result.json",
            duplicate_pilot_contract_path,
            verify_sources=False,
            test_mode=True,
        )
        assert duplicate_pilot_verdict["verdict"] == "INSTRUMENT_INVALID"
        assert "duplicate artifact reference" in duplicate_pilot_verdict["reason"]

        malformed_review_contract = copy.deepcopy(bound)
        malformed_review_contract["activation"]["independent_review"] = {
            "path": "independent-review.txt",
            "sha256": "0" * 64,
        }
        malformed_review_path = root / "malformed-review-contract.json"
        write_json(malformed_review_path, malformed_review_contract)
        try:
            validate_frozen_bindings(malformed_review_contract, malformed_review_path)
        except EvidenceError:
            pass
        else:
            raise AssertionError("frozen check accepted malformed review binding")

        null_ledger_contract = copy.deepcopy(bound)
        null_ledger_contract["capture_ledgers"]["development"] = None
        null_ledger_path = root / "null-ledger-contract.json"
        write_json(null_ledger_path, null_ledger_contract)
        try:
            validate_frozen_bindings(null_ledger_contract, null_ledger_path)
        except EvidenceError:
            pass
        else:
            raise AssertionError("frozen check accepted null capture ledger")

        unbound_extractor_contract = copy.deepcopy(bound)
        unbound_extractor_contract["noise_instrument"]["extractor_entrypoint"] = None
        unbound_extractor_path = root / "unbound-extractor-contract.json"
        write_json(unbound_extractor_path, unbound_extractor_contract)
        try:
            validate_frozen_bindings(
                unbound_extractor_contract,
                unbound_extractor_path,
            )
        except EvidenceError:
            pass
        else:
            raise AssertionError("frozen check accepted unbound temporal extractor")

        weak_effect_requirement = copy.deepcopy(effect_requirement)
        weak_effect_requirement["required_rms_reduction"] = 1e-6
        write_json(root / "weak-effect-requirement.json", weak_effect_requirement)
        low_power_pilot = make_pilot_evidence(
            bound,
            root,
            {
                "low-power-pilot-development": "noise-development",
                "low-power-pilot-holdout": "noise-holdout",
            },
            sites,
            anticorrelated=True,
        )
        write_json(root / "low-power-pilot.json", low_power_pilot)
        low_power_contract = copy.deepcopy(effect_bound)
        low_power_contract["noise_instrument"]["required_rms_reduction"] = 1e-6
        low_power_contract["noise_instrument"]["effect_requirement"] = ref_for(
            root / "weak-effect-requirement.json", root
        )
        low_power_contract["noise_instrument"]["pilot_evidence"] = ref_for(
            root / "low-power-pilot.json", root
        )
        low_power_contract_path = root / "low-power-contract.json"
        write_json(low_power_contract_path, low_power_contract)
        low_power_result = copy.deepcopy(result)
        low_power_result["contract_sha256"] = sha256(low_power_contract_path)
        write_json(root / "low-power-result.json", low_power_result)
        assert (
            adjudicate_result(
                root / "low-power-result.json",
                low_power_contract_path,
                verify_sources=False,
                test_mode=True,
            )["verdict"]
            == "INSTRUMENT_INVALID"
        )

        draft_result = adjudicate_result(
            root / "result.json",
            CONTRACT_PATH,
            verify_sources=False,
        )
        assert draft_result["verdict"] == "INSTRUMENT_INVALID", draft_result
        assert "draft" in draft_result["reason"], draft_result

    print(
        "self-test: raw-evidence GO=GREEN achieved-effect=MANDATORY "
        "bound-effect=GREEN strict-bound=RED bare-GO=RED incomplete-effect=RED "
        "direction-only-minimum=UNBOUND M2-claim=FALSE missing-artifact=RED "
        "missing-curve=RED missing-temporal-output=RED duplicate-output=RED "
        "supplied-power=RED supplied-effect=RED missing-M135-input=RED "
        "M135-null-state=INSTRUMENT_INVALID "
        "M135-invalid-plus-boolean=INSTRUMENT_INVALID "
        "M135-unknown-plus-boolean=INSTRUMENT_INVALID M135-valid-fail=REFUTED "
        "pipeline-mismatch=RED hash-mutation=RED supplied-boolean=RED "
        "postclamp-hull=RED M135-improvement-missing=RED M135-unbound=BLOCKED "
        "unsupported-cost=RED null-cost=RED contradictory-effect=RED "
        "bound-without-pilot=RED duplicate-pilot=RED "
        "malformed-frozen-bindings=RED underpowered-design=RED improvement=GREEN "
        "development-refutation=RED holdout-refutation=RED width-irrelevance=GREEN"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()
    if not (args.check or args.self_test or args.result):
        parser.error("choose --check, --self-test, or --result")
    try:
        contract = load_json(args.contract)
        validate_contract(contract)
        if args.check:
            validate_sources(contract)
            validate_document()
            if contract["status"] == contract["activation"]["required_status"]:
                validate_frozen_bindings(contract, args.contract)
                print("frozen specification and bindings check: PASS")
            else:
                print("draft specification check: PASS (not frozen)")
        if args.self_test:
            run_self_test(contract)
    except EvidenceError as error:
        print(
            json.dumps(
                {"verdict": "INSTRUMENT_INVALID", "reason": str(error)},
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    if args.result:
        verdict = adjudicate_result(args.result, args.contract)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 2 if verdict["verdict"] == "INSTRUMENT_INVALID" else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
