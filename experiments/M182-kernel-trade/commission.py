"""Commission every M182 verifier check with in-memory mutations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import verify


HERE = Path(__file__).resolve().parent
OUT = HERE / "commission.json"
INERT_REPORT_LINE = (
    "**INERT COMMISSION ANCHOR:** changing this sentence alone must not affect "
    "any measurement check."
)


def get_path(doc: Any, path: tuple[Any, ...]) -> Any:
    value = doc
    for part in path:
        value = value[part]
    return value


def set_path(doc: Any, path: tuple[Any, ...], value: Any) -> None:
    target = doc
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


def ledger_line(check_id: str, path: tuple[Any, ...], value: Any) -> str:
    pointer = "/" + "/".join(str(part) for part in path)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"{check_id}\t{pointer}\t{payload}"


def replace_unique_full_line(text: str, old: str, new: str, label: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line == old]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: mutation anchor must match exactly one full line, found {len(matches)}"
        )
    lines[matches[0]] = new
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def semantic_specs(result: dict) -> list[dict]:
    direction = result["controls"]["mtf_direction_control"]
    return [
        {
            "id": "S01-schema",
            "path": ("schema",),
            "new": "m182-kernel-trade-BROKEN",
            "defect": "wrong result schema",
        },
        {
            "id": "S02-source-anchors",
            "path": ("source", "anchors", 0, "count"),
            "new": 0,
            "defect": "required production-source anchor absent",
        },
        {
            "id": "S03-source-hashes",
            "path": ("source", "files", "crates/strehl-core/src/restore.rs"),
            "new": "0" * 64,
            "defect": "measured restore.rs identity does not match current bytes",
        },
        {
            "id": "S04-convex-raw-taps",
            "path": ("raw_taps", "bilinear", "maximum_raw_negative_mass"),
            "new": 0.01,
            "defect": "bilinear plant contains a negative tap",
        },
        {
            "id": "S05-negative-lobes",
            "path": ("raw_taps", "lanczos3", "most_negative_raw_tap"),
            "new": 0.0,
            "defect": "negative-lobe kernel falsely reported non-negative",
        },
        {
            "id": "S06-shipping-dc",
            "path": (
                "shipping_effective_tap_probe",
                "catmull-rom",
                "maximum_constant_dc_error",
            ),
            "new": 0.01,
            "defect": "shipping gather changes a constant plane",
        },
        {
            "id": "S07-overshoot-discrimination",
            "path": ("overshoot", "bilinear", "step", "dn"),
            "new": 1.0,
            "defect": "convex bilinear step reports out-of-range output",
        },
        {
            "id": "S08-restoration-support",
            "path": ("restoration_supported", "clamped-catmull-rom"),
            "new": True,
            "defect": "nonlinear clamped kernel falsely declared restorable",
        },
        {
            "id": "S09-model-shipping-crosscheck",
            "path": (
                "controls",
                "model_vs_shipping_mtf",
                "maximum_absolute_error",
            ),
            "new": 0.1,
            "defect": "MTF model disagrees with shipping sampler",
        },
        {
            "id": "S10-mtf-direction",
            "path": ("controls", "mtf_direction_control", "sharpened"),
            "new": direction["baseline"],
            "defect": "positive sharpened arm cannot move above baseline",
        },
        {
            "id": "S11-restoration-application",
            "path": (
                "controls",
                "restore_application_noise_prediction",
                "measured_sd_ratio",
            ),
            "new": 2.0,
            "defect": "applied noise gain disagrees with returned FIR energy",
        },
        {
            "id": "S12-high-noise-identity",
            "path": (
                "restoration",
                "high_noise_null",
                "bilinear",
                "noise_sd_ratio_2d",
            ),
            "new": 1.1,
            "defect": "noise-dominated restoration is not identity",
        },
        {
            "id": "S13-conditioning-positive",
            "path": (
                "restoration",
                "conditioning",
                "bilinear",
                "minimum_in_band_mtf_1d",
            ),
            "new": 0.0,
            "defect": "bilinear has a planted in-band zero",
        },
        {
            "id": "S14-frequency-convention",
            "path": ("frequency_convention", "primary"),
            "new": "cycles per output pixel",
            "defect": "frequency axis silently changed by two",
        },
        {
            "id": "S15-method-counts",
            "path": ("methods", "raw_tap_sweep_phases"),
            "new": 1,
            "defect": "dense tap sweep collapsed to one phase",
        },
        {
            "id": "S16-probe-artifact",
            "path": ("artifacts", "probe_tsv_sha256"),
            "new": "0" * 64,
            "defect": "raw Rust probe artifact changed",
        },
        {
            "id": "S17-mtf-artifact",
            "path": ("artifacts", "mtf_curve_sha256"),
            "new": "0" * 64,
            "defect": "MTF curve artifact changed",
        },
        {
            "id": "S18-restoration-artifact",
            "path": ("artifacts", "restoration_curve_sha256"),
            "new": "0" * 64,
            "defect": "restoration curve artifact changed",
        },
        {
            "id": "S19-tap-phase-artifact",
            "path": ("artifacts", "tap_phase_sums_sha256"),
            "new": "0" * 64,
            "defect": "per-phase tap-sum artifact changed",
        },
        {
            "id": "S20-inverse-has-noise-cost",
            "path": (
                "restoration",
                "ideal_inverse",
                "bilinear",
                "noise_sd_ratio_2d",
            ),
            "new": 1.0,
            "defect": "potent bilinear inverse falsely reported noise-free",
        },
        {
            "id": "S21-restoration-recovers-high-band",
            "path": (
                "restoration",
                "ideal_inverse",
                "bilinear",
                "selected",
                "192",
                "restored_mtf",
            ),
            "new": 0.0,
            "defect": "restoration positive arm cannot recover upper-band MTF",
        },
        {
            "id": "S22-clamped-is-not-an-otf",
            "path": ("mtf", "clamped-catmull-rom", "method"),
            "new": "restore::gather_mtf linear OTF",
            "defect": "nonlinear clamp falsely presented as a linear OTF",
        },
    ]


def main() -> int:
    result = json.loads(verify.RESULTS.read_text(encoding="utf-8"))
    report = verify.REPORT.read_text(encoding="utf-8")
    baseline_failures, report_lines = verify.audit(result, report)
    semantic = verify.semantic_checks(result)
    expected_total = len(report_lines) + len(semantic)
    if baseline_failures:
        raise RuntimeError(f"baseline is RED before commissioning: {baseline_failures}")
    print(f"BASELINE GREEN: {expected_total}/{expected_total} checks passed")

    report_mutations = []
    report_missed = []
    for line_id, line in report_lines.items():
        mutated = replace_unique_full_line(
            report,
            line,
            f"{line} [PLANTED DEFECT {line_id}]",
            f"report {line_id}",
        )
        failures, _ = verify.audit(result, mutated)
        caught = f"R-{line_id}" in failures
        report_mutations.append(
            {
                "check": f"R-{line_id}",
                "anchor_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest().upper(),
                "caught": caught,
            }
        )
        if not caught:
            report_missed.append(f"R-{line_id}")

    specs = semantic_specs(result)
    if [row["id"] for row in specs] != [row[0] for row in semantic]:
        raise RuntimeError("semantic commissioning specs do not cover checks in verifier order")
    ledger_lines = [
        ledger_line(spec["id"], spec["path"], get_path(result, spec["path"]))
        for spec in specs
    ]
    if len(set(ledger_lines)) != len(ledger_lines):
        raise RuntimeError("semantic mutation ledger contains duplicate full-line anchors")
    ledger = "\n".join(ledger_lines) + "\n"

    semantic_mutations = []
    semantic_missed = []
    for spec, anchor in zip(specs, ledger_lines):
        replacement = ledger_line(spec["id"], spec["path"], spec["new"])
        # Commission the mutation mechanism itself: the old structured fact
        # must be a unique full line before the cloned object is changed.
        replace_unique_full_line(ledger, anchor, replacement, spec["id"])
        mutated = deepcopy(result)
        set_path(mutated, spec["path"], spec["new"])
        failures, _ = verify.audit(mutated, report)
        caught = spec["id"] in failures
        semantic_mutations.append(
            {
                "check": spec["id"],
                "path": "/" + "/".join(str(part) for part in spec["path"]),
                "defect": spec["defect"],
                "anchor": anchor,
                "caught": caught,
            }
        )
        if not caught:
            semantic_missed.append(spec["id"])

    # Inert arm 1: mutate a unique, explicitly noncanonical report sentence.
    inert_report = replace_unique_full_line(
        report,
        INERT_REPORT_LINE,
        "**INERT COMMISSION ANCHOR:** harmless wording changed in memory.",
        "inert-report",
    )
    inert_report_failures, _ = verify.audit(result, inert_report)

    # Inert arm 2: alter unconsumed metadata, anchored through the same unique
    # full-line ledger discipline as every semantic defect.
    inert_path = ("environment", "repository_head_at_measurement")
    inert_anchor = ledger_line("INERT-result-metadata", inert_path, get_path(result, inert_path))
    replace_unique_full_line(
        inert_anchor + "\n",
        inert_anchor,
        ledger_line("INERT-result-metadata", inert_path, "harmless-in-memory-value"),
        "inert-result",
    )
    inert_result = deepcopy(result)
    set_path(inert_result, inert_path, "harmless-in-memory-value")
    inert_result_failures, _ = verify.audit(inert_result, report)

    direction = result["controls"]["mtf_direction_control"]
    positive_preserved = direction["sharpened"] > direction["baseline"]
    missed = report_missed + semantic_missed
    defects_caught = sum(row["caught"] for row in report_mutations + semantic_mutations)
    defects_planted = len(report_mutations) + len(semantic_mutations)
    inert = [
        {
            "id": "inert-report-wording",
            "survived": not inert_report_failures,
            "unexpected_failures": inert_report_failures,
        },
        {
            "id": "inert-unconsumed-result-metadata",
            "survived": not inert_result_failures,
            "unexpected_failures": inert_result_failures,
        },
    ]
    document = {
        "schema": "m182-commission-v1",
        "baseline": {
            "checks_passed": expected_total,
            "checks_failed": 0,
            "report_checks": len(report_lines),
            "semantic_checks": len(semantic),
        },
        "mutations": {
            "defects_planted": defects_planted,
            "defects_caught": defects_caught,
            "defects_missed": len(missed),
            "missed_ids": missed,
            "all_anchors_unique_full_lines": True,
            "report": report_mutations,
            "semantic": semantic_mutations,
        },
        "inert_arms": {
            "survived": sum(row["survived"] for row in inert),
            "total": len(inert),
            "arms": inert,
        },
        "positive_control": {
            "preserved": positive_preserved,
            "baseline_mtf": direction["baseline"],
            "sharpened_mtf": direction["sharpened"],
            "ratio": direction["sharpened"] / direction["baseline"],
        },
    }
    OUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(
        f"REPORT DEFECTS: {len(report_mutations) - len(report_missed)}/"
        f"{len(report_mutations)} caught"
    )
    print(
        f"SEMANTIC DEFECTS: {len(semantic_mutations) - len(semantic_missed)}/"
        f"{len(semantic_mutations)} caught"
    )
    print(f"DEFECTS MISSED: {len(missed)}")
    print(
        f"INERT ARMS: {sum(row['survived'] for row in inert)}/{len(inert)} survived"
    )
    print(
        "POSITIVE CONTROL: "
        f"{'preserved' if positive_preserved else 'FAILED'} "
        f"({direction['sharpened']:.6f} > {direction['baseline']:.6f})"
    )
    print(f"wrote {OUT.relative_to(verify.ROOT)}")

    if missed or not all(row["survived"] for row in inert) or not positive_preserved:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
