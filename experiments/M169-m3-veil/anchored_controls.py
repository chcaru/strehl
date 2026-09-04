"""Line-anchored M3 null, degradation, and improvement controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

from full_commission import arm_summary, one_sided_veil_delta
from m3_checker_v2 import (
    SiteProfiles,
    load_checker_definition,
    score_site,
    sha256_file,
)


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TEMPLATE = HERE / "fixtures" / "control-template.json"
OUT = HERE / "out" / "anchored-controls.json"
CONFIG_OUT = HERE / "out" / "control-configs"
UPSTREAM = REPO / "experiments" / "M161-m3-ratification"
EXPECTED = {
    "m3-checker-definition-v2.json": (
        "578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca"
    ),
    "m3_checker_v2.py": (
        "05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda"
    ),
    "../M152-site-census/out/census-manifest.json": (
        "35d5058afc1f310923ba2a3e5bf0cd3b91b3eb2df0e8d4868c22099de7bcd38d"
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def replace_unique_full_line(text: str, old_line: str, new_line: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line == old_line]
    if len(matches) != 1:
        raise RuntimeError(
            "MUTATION_TARGET_NOT_UNIQUE: expected exactly one full-line match "
            f"for {old_line!r}, found {len(matches)}"
        )
    lines[matches[0]] = new_line
    return "\n".join(lines) + "\n"


def mutate_fixture(
    original: str,
    *,
    name: str,
    profile_mutation: str,
    amplitude: float,
) -> tuple[str, list[dict[str, str]]]:
    changes = [
        (
            '  "name": "flat_residual_null",',
            f'  "name": "{name}",',
        ),
        (
            '  "profile_mutation": "identity",',
            f'  "profile_mutation": "{profile_mutation}",',
        ),
        (
            '  "amplitude_fraction_of_step": 0.0,',
            f'  "amplitude_fraction_of_step": {amplitude},',
        ),
    ]
    text = original
    audit: list[dict[str, str]] = []
    for old_line, new_line in changes:
        text = replace_unique_full_line(text, old_line, new_line)
        audit.append(
            {
                "anchor_sha256": sha256_bytes(old_line.encode("utf-8")),
                "replacement_sha256": sha256_bytes(new_line.encode("utf-8")),
            }
        )
    return text, audit


def resolve_profile_plant(
    name: str, amplitude: float
) -> Callable[[np.ndarray, np.ndarray, float], np.ndarray]:
    if name == "identity":
        return lambda output, offsets, step: output.copy()
    if name == "one_sided_veil":
        return lambda output, offsets, step: output + one_sided_veil_delta(
            offsets, step, amplitude
        )
    raise RuntimeError(f"unknown profile mutation {name!r}")


def resolve_patch_plant(
    name: str,
) -> Callable[[np.ndarray, float], np.ndarray]:
    if name == "identity":
        return lambda patch, step: patch.copy()
    raise RuntimeError(f"unknown patch mutation {name!r}")


def run_arm(
    config_text: str, definition: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    config = json.loads(config_text)
    summary, _ = arm_summary(
        str(config["name"]),
        resolve_profile_plant(
            str(config["profile_mutation"]),
            float(config["amplitude_fraction_of_step"]),
        ),
        resolve_patch_plant(str(config["patch_mutation"])),
        definition,
        float(config["amplitude_fraction_of_step"]),
        noise_sigma_fraction=float(config["noise_sigma_fraction_of_step"]),
    )
    return config, summary


def main() -> int:
    definition, definition_sha = load_checker_definition()
    freeze_checks: dict[str, bool] = {}
    for relative, expected in EXPECTED.items():
        local = (HERE / relative).resolve()
        if relative.startswith("../"):
            local = (REPO / "experiments" / relative[3:]).resolve()
        upstream = (
            (UPSTREAM / relative).resolve()
            if not relative.startswith("../")
            else local
        )
        local_hash = sha256_file(local)
        upstream_hash = sha256_file(upstream)
        freeze_checks[relative] = local_hash == expected == upstream_hash
    if not all(freeze_checks.values()) or definition_sha != EXPECTED[
        "m3-checker-definition-v2.json"
    ]:
        raise RuntimeError(f"frozen M161 inputs changed: {freeze_checks}")

    original = TEMPLATE.read_text(encoding="utf-8")
    missing_anchor_hard_error = False
    try:
        replace_unique_full_line(
            original,
            '  "profile_mutation": "missing-control-anchor",',
            '  "profile_mutation": "identity",',
        )
    except RuntimeError as error:
        missing_anchor_hard_error = "found 0" in str(error)
    if not missing_anchor_hard_error:
        raise RuntimeError("missing mutation anchor did not hard-error")

    red_text, red_audit = mutate_fixture(
        original,
        name="planted_6pct_one_sided_far_veil",
        profile_mutation="one_sided_veil",
        amplitude=0.06,
    )
    improved_text, improved_audit = mutate_fixture(
        original,
        name="planted_improvement_0_5pct_one_sided_far_veil",
        profile_mutation="one_sided_veil",
        amplitude=0.005,
    )
    configs = {
        "flat_residual_null": original,
        "planted_6pct_one_sided_far_veil": red_text,
        "planted_improvement_0_5pct_one_sided_far_veil": improved_text,
    }
    CONFIG_OUT.mkdir(parents=True, exist_ok=True)
    for name, text in configs.items():
        (CONFIG_OUT / f"{name}.json").write_text(text, encoding="utf-8")

    _, null = run_arm(original, definition)
    _, defect = run_arm(red_text, definition)
    _, improved = run_arm(improved_text, definition)
    offsets = np.arange(-400.0, 401.0, 1.0)
    literal_flat = np.full(offsets.shape, 0.5, dtype=np.float64)
    literal_flat_result = score_site(
        SiteProfiles(
            site_id="LITERAL-FLAT-DOMAIN-GUARD",
            capture_id="m3-razor-control",
            offsets_native_px=offsets,
            source_profiles=literal_flat[None, :],
            output_profile=literal_flat.copy(),
            normalization_source_index=0,
            far_reference_source_index=0,
            sharp_source_index=0,
            output_patch=np.full((128, 128), 0.5, dtype=np.float64),
            sharp_source_patch=np.full((128, 128), 0.5, dtype=np.float64),
        ),
        definition,
    )
    literal_flat_record = {
        "site_id": literal_flat_result["site_id"],
        "status": literal_flat_result["status"],
        "reason": literal_flat_result["reason"],
        "affected": literal_flat_result["affected"],
        "nonfinite_metrics_omitted_from_json": True,
    }
    checks = {
        "missing_anchor_hard_errors": missing_anchor_hard_error,
        "flat_residual_null_passes": null["verdict"] == "PASS",
        "flat_residual_null_has_zero_affected_sites": null["affected_edge_count"]
        == 0,
        "planted_defect_is_red": defect["verdict"] == "FAIL",
        "planted_defect_detected_at_every_site": defect["affected_edge_rate"]
        == 1.0,
        "planted_defect_breaks_literal_maximum": not defect["checks"][
            "headline_maximum"
        ],
        "improvement_is_green": improved["verdict"] == "PASS",
        "improvement_has_zero_affected_sites": improved["affected_edge_count"]
        == 0,
        "improvement_reduces_median_v_e": improved["median_v_e"]
        < defect["median_v_e"],
        "improvement_reduces_maximum": improved["maximum_max_h_v"]
        < defect["maximum_max_h_v"],
        "literal_flat_no_edge_fails_closed": literal_flat_result["status"]
        == "INVALID_OUTPUT_CHARGED"
        and literal_flat_result["reason"] == "nonpositive_source_step",
    }
    result = {
        "schema": "m169-m3-anchored-controls-v1",
        "checker_definition_sha256": definition_sha,
        "checker_source_sha256": sha256_file(HERE / "m3_checker_v2.py"),
        "template_sha256": sha256_file(TEMPLATE),
        "mutation_method": (
            "in-memory replacement of exact unique full lines; zero or multiple "
            "matches hard-error before any control runs"
        ),
        "missing_anchor_probe": "HARD_ERROR_CONFIRMED",
        "mutation_audit": {
            "defect": red_audit,
            "improvement": improved_audit,
        },
        "flat_null_interpretation": (
            "eligible edge whose output-minus-reference residual is identically "
            "flat zero; a literal no-edge field is outside M3 and fails closed "
            "as nonpositive_source_step"
        ),
        "literal_flat_no_edge_domain_guard": literal_flat_record,
        "arms": {
            "flat_residual_null": null,
            "planted_defect": defect,
            "planted_improvement": improved,
        },
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    write_json(OUT, result)
    print(
        "FLAT_NULL %s h50=%.6f v50=%.6f max=%.6f affected=%d/%d"
        % (
            "GREEN" if null["verdict"] == "PASS" else "RED",
            null["median_h_e"],
            null["median_v_e"],
            null["maximum_max_h_v"],
            null["affected_edge_count"],
            null["site_count"],
        )
    )
    print(
        "DEFECT %s h50=%.6f v50=%.6f max=%.6f affected=%d/%d"
        % (
            "RED" if defect["verdict"] == "FAIL" else "GREEN",
            defect["median_h_e"],
            defect["median_v_e"],
            defect["maximum_max_h_v"],
            defect["affected_edge_count"],
            defect["site_count"],
        )
    )
    print(
        "IMPROVEMENT %s h50=%.6f v50=%.6f max=%.6f affected=%d/%d"
        % (
            "GREEN" if improved["verdict"] == "PASS" else "RED",
            improved["median_h_e"],
            improved["median_v_e"],
            improved["maximum_max_h_v"],
            improved["affected_edge_count"],
            improved["site_count"],
        )
    )
    print(
        "LITERAL_FLAT DOMAIN_REFUSAL status=%s reason=%s"
        % (literal_flat_result["status"], literal_flat_result["reason"])
    )
    print("MISSING_ANCHOR HARD_ERROR")
    print("ANCHORED_CONTROLS " + result["verdict"])
    return 0 if result["verdict"] == "PASS" else 5


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
