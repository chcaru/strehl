"""Commission every M182 check with uniquely anchored in-memory defects."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import verify


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "check-commission.json"
INERT_REPORT_LINE = (
    "**INERT COMMISSION ANCHOR:** This sentence carries no measured value; "
    "changing it must stay green."
)


def get_path(value: Any, path: tuple[Any, ...]) -> Any:
    for part in path:
        value = value[part]
    return value


def set_path(value: Any, path: tuple[Any, ...], replacement: Any) -> None:
    target = value
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement


def replace_unique_full_line(text: str, old: str, new: str, label: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line == old]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: mutation anchor matched {len(matches)} full lines, expected one"
        )
    lines[matches[0]] = new
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def ledger_line(check_id: str, path: tuple[Any, ...], value: Any) -> str:
    pointer = "/" + "/".join(str(part) for part in path)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"{check_id}\t{pointer}\t{payload}"


def semantic_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "S01-schema",
            "path": ("schema",),
            "new": "BROKEN",
            "defect": "wrong result schema",
        },
        {
            "id": "S02-bar-definition",
            "path": ("bar", "documents_disagree"),
            "new": True,
            "defect": "six-GiB documents falsely declared conflicting",
        },
        {
            "id": "S03-warm-lifecycle",
            "path": ("bar", "warm_semantics", "accepted_warmup_invocations"),
            "new": 0,
            "defect": "warm-up process population erased",
        },
        {
            "id": "S04-harness-lifecycle-anchors",
            "path": ("bar", "harness_source_lines", "first_sample"),
            "new": 0,
            "defect": "monitor start anchor moved",
        },
        {
            "id": "S05-m139-peak",
            "path": ("m139", "maximum_job_peak_bytes"),
            "new": 0,
            "defect": "canonical Job peak corrupted",
        },
        {
            "id": "S06-independent-counters",
            "path": ("m139", "maximum_sampled_private_bytes"),
            "new": 0,
            "defect": "sampled peak no longer agrees with Job peak",
        },
        {
            "id": "S07-active-chunk-model",
            "path": ("m139", "matrix", 0, "active_chunks"),
            "new": 99,
            "defect": "active chunk count no longer follows partition formula",
        },
        {
            "id": "S08-scaling-fit",
            "path": ("m139", "active_chunk_fit", "r_squared"),
            "new": 0.0,
            "defect": "whole-worker fit has no explanatory power",
        },
        {
            "id": "S09-fresh-reproduction",
            "path": ("reproduction", "rows", 0, "relative_delta"),
            "new": 1.0,
            "defect": "fresh reproduction is 100 percent off",
        },
        {
            "id": "S10-geometry",
            "path": ("allocation_accounting", "geometry", "plane_width"),
            "new": 0,
            "defect": "allocation geometry corrupted",
        },
        {
            "id": "S11-consumer-arithmetic",
            "path": (
                "allocation_accounting",
                "consumers_bytes_per_active_chunk",
                "band_merge",
            ),
            "new": 0,
            "defect": "largest source allocation erased",
        },
        {
            "id": "S12-top-three-order",
            "path": ("allocation_accounting", "top_three", 0, "name"),
            "new": "gate_floor_probe",
            "defect": "consumer rank order corrupted",
        },
        {
            "id": "S13-attribution-closure",
            "path": (
                "allocation_accounting",
                "source_accounted_bytes_per_active_chunk",
            ),
            "new": 0,
            "defect": "source attribution no longer closes",
        },
        {
            "id": "S14-measured-source-provenance",
            "path": (
                "provenance",
                "measured_source",
                "crates/strehl-core/src/pyramid.rs",
                "sha256",
            ),
            "new": "0" * 64,
            "defect": "measured source blob identity corrupted",
        },
        {
            "id": "S15-input-evidence-provenance",
            "path": ("provenance", "closeout_sha256"),
            "new": "0" * 64,
            "defect": "M139 closeout identity corrupted",
        },
        {
            "id": "S16-current-memory-revision",
            "path": (
                "bounded_implementation",
                "current_memory_files_last_commit",
                "merge_cmd",
            ),
            "new": "0" * 40,
            "defect": "current memory-owning revision changed",
        },
        {
            "id": "S17-bounded-memory-result",
            "path": ("bounded_implementation", "n299_w16_job_peak_bytes"),
            "new": 7 << 30,
            "defect": "bounded implementation planted above the bar",
        },
        {
            "id": "S18-saving-arithmetic",
            "path": ("bounded_implementation", "saving_from_m139_peak_bytes"),
            "new": 0,
            "defect": "observed saving arithmetic corrupted",
        },
        {
            "id": "S19-plan-reaches-bar",
            "path": ("plan", "bounded_change_reachable"),
            "new": False,
            "defect": "plan falsely marked unreachable",
        },
        {
            "id": "S20-probe-directions",
            "path": ("probe_commission", "status"),
            "new": "FAILED",
            "defect": "bidirectional meter commissioning failed",
        },
    ]


def failed_semantic_ids(
    result: dict[str, Any],
    *,
    record_overrides: dict[str, dict[str, Any]] | None = None,
    own_text_override: str | None = None,
) -> set[str]:
    return {
        check_id
        for check_id, passed, _ in verify.semantic_checks(
            result,
            record_overrides=record_overrides,
            own_text_override=own_text_override,
        )
        if not passed
    }


def main() -> int:
    result = verify.read_json(verify.RESULTS)
    report = verify.REPORT.read_text(encoding="utf-8")
    baseline_failures, report_lines = verify.audit(result, report)
    semantic = verify.semantic_checks(result)
    expected_total = len(report_lines) + len(semantic)
    if baseline_failures:
        raise RuntimeError(f"baseline is RED before commissioning: {baseline_failures}")
    if expected_total != 44:
        raise RuntimeError(f"registered check count changed: {expected_total}, expected 44")
    print(f"BASELINE GREEN: {expected_total}/{expected_total} checks passed")

    report_results = []
    missed = []
    for line_id, line in report_lines.items():
        mutated = replace_unique_full_line(
            report,
            line,
            f"{line} [PLANTED DEFECT {line_id}]",
            f"report {line_id}",
        )
        failures, _ = verify.audit(result, mutated)
        target = f"R-{line_id}"
        caught = any(failure.startswith(f"{target}:") for failure in failures)
        report_results.append(
            {
                "check": target,
                "anchor_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest().upper(),
                "caught": caught,
            }
        )
        if not caught:
            missed.append(target)

    specs = semantic_specs()
    semantic_ids = [row[0] for row in semantic]
    external_ids = [
        "S21-product-run-witnesses",
        "S22-holdout-exclusion",
        "S23-m172-boundary-and-n7",
    ]
    if [spec["id"] for spec in specs] + external_ids != semantic_ids:
        raise RuntimeError("semantic mutation specs do not match verifier order")

    ledger_lines = [
        ledger_line(spec["id"], spec["path"], get_path(result, spec["path"]))
        for spec in specs
    ]
    ledger_lines.extend(
        [
            ledger_line(
                "S21-product-run-witnesses",
                ("external", "pre-n33-w1", "output_removed_after_hash"),
                True,
            ),
            ledger_line(
                "S22-holdout-exclusion",
                ("external", "owned_text_contains_prohibited_name"),
                False,
            ),
            ledger_line(
                "S23-m172-boundary-and-n7",
                ("m172_evidence_boundary", "m172_answered_step3"),
                False,
            ),
        ]
    )
    if len(ledger_lines) != len(set(ledger_lines)):
        raise RuntimeError("semantic commissioning ledger has duplicate full-line anchors")
    ledger = "\n".join(ledger_lines) + "\n"

    semantic_results = []
    for spec, anchor in zip(specs, ledger_lines, strict=False):
        replacement = ledger_line(spec["id"], spec["path"], spec["new"])
        replace_unique_full_line(ledger, anchor, replacement, spec["id"])
        mutated = deepcopy(result)
        set_path(mutated, spec["path"], spec["new"])
        caught = spec["id"] in failed_semantic_ids(mutated)
        semantic_results.append(
            {
                "check": spec["id"],
                "defect": spec["defect"],
                "anchor_sha256": hashlib.sha256(anchor.encode("utf-8")).hexdigest().upper(),
                "caught": caught,
            }
        )
        if not caught:
            missed.append(spec["id"])

    records = {
        "pre-n33-w1": verify.read_json(HERE / "pre-n33-w1.json"),
    }
    record_anchor = ledger_lines[-3]
    record_replacement = ledger_line(
        "S21-product-run-witnesses",
        ("external", "pre-n33-w1", "output_removed_after_hash"),
        False,
    )
    replace_unique_full_line(
        ledger, record_anchor, record_replacement, "S21-product-run-witnesses"
    )
    records["pre-n33-w1"]["probe"]["output_removed_after_hash"] = False
    caught = "S21-product-run-witnesses" in failed_semantic_ids(
        result, record_overrides=records
    )
    semantic_results.append(
        {
            "check": "S21-product-run-witnesses",
            "defect": "hashed TIFF removal witness planted false",
            "anchor_sha256": hashlib.sha256(record_anchor.encode("utf-8")).hexdigest().upper(),
            "caught": caught,
        }
    )
    if not caught:
        missed.append("S21-product-run-witnesses")

    holdout_anchor = ledger_lines[-2]
    holdout_replacement = ledger_line(
        "S22-holdout-exclusion",
        ("external", "owned_text_contains_prohibited_name"),
        True,
    )
    replace_unique_full_line(
        ledger, holdout_anchor, holdout_replacement, "S22-holdout-exclusion"
    )
    ordinary_text = report + verify.REPORT.name
    prohibited_name = "7-" + "aperture" + "-pairs"
    caught = "S22-holdout-exclusion" in failed_semantic_ids(
        result, own_text_override=ordinary_text + prohibited_name
    )
    semantic_results.append(
        {
            "check": "S22-holdout-exclusion",
            "defect": "prohibited holdout name planted into owned-text view",
            "anchor_sha256": hashlib.sha256(holdout_anchor.encode("utf-8")).hexdigest().upper(),
            "caught": caught,
        }
    )
    if not caught:
        missed.append("S22-holdout-exclusion")

    boundary_anchor = ledger_lines[-1]
    boundary_replacement = ledger_line(
        "S23-m172-boundary-and-n7",
        ("m172_evidence_boundary", "m172_answered_step3"),
        True,
    )
    replace_unique_full_line(
        ledger, boundary_anchor, boundary_replacement, "S23-m172-boundary-and-n7"
    )
    broken_boundary = deepcopy(result)
    broken_boundary["m172_evidence_boundary"]["m172_answered_step3"] = True
    caught = "S23-m172-boundary-and-n7" in failed_semantic_ids(broken_boundary)
    semantic_results.append(
        {
            "check": "S23-m172-boundary-and-n7",
            "defect": "M172 falsely credited with independent allocation attribution",
            "anchor_sha256": hashlib.sha256(boundary_anchor.encode("utf-8")).hexdigest().upper(),
            "caught": caught,
        }
    )
    if not caught:
        missed.append("S23-m172-boundary-and-n7")

    inert_report = replace_unique_full_line(
        report,
        INERT_REPORT_LINE,
        INERT_REPORT_LINE.replace("changing", "editing"),
        "report inert arm",
    )
    inert_report_failures, _ = verify.audit(result, inert_report)
    inert_result = deepcopy(result)
    inert_result["_commission_note"] = "harmless metadata"
    inert_result_failures, _ = verify.audit(inert_result, report)
    inert_arms = {
        "unmeasured_report_sentence_stayed_green": not inert_report_failures,
        "unread_result_metadata_stayed_green": not inert_result_failures,
    }

    probe = verify.read_json(verify.COMMISSION)
    positive_controls = {
        "allocation_up_preserved": probe["deltas"][
            "allocation_plant_minus_baseline_bytes"
        ]
        >= 192 * (1 << 20),
        "saving_down_preserved": probe["deltas"][
            "baseline_minus_saving_plant_bytes"
        ]
        >= 128 * (1 << 20),
        "inert_meter_arm_preserved": probe["deltas"][
            "absolute_inert_minus_baseline_bytes"
        ]
        <= 16 * (1 << 20),
    }

    caught_count = sum(row["caught"] for row in report_results + semantic_results)
    result_doc = {
        "schema": "m182-memory-check-commission-v1",
        "baseline_checks": expected_total,
        "baseline_passed": expected_total,
        "report_mutations": report_results,
        "semantic_mutations": semantic_results,
        "planted_defects": expected_total,
        "caught": caught_count,
        "missed": missed,
        "inert_arms": inert_arms,
        "positive_controls": positive_controls,
        "status": (
            "COMMISSIONED"
            if caught_count == expected_total
            and not missed
            and all(inert_arms.values())
            and all(positive_controls.values())
            else "FAILED"
        ),
    }
    OUTPUT.write_text(json.dumps(result_doc, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result_doc["status"],
                "baseline": f"{expected_total}/{expected_total}",
                "caught": f"{caught_count}/{expected_total}",
                "missed": missed,
                "inert_arms": inert_arms,
                "positive_controls": positive_controls,
            },
            indent=2,
        )
    )
    return 0 if result_doc["status"] == "COMMISSIONED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
