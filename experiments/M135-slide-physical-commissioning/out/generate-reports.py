from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


LABEL = "DEVELOPMENT — NEVER A SCORE"
AUTHORIZED_COMMIT = "0511594d3e31a3f2ef4f204ce1ddf88ac6f147da"
MODEL = "gpt-5.6-sol"

OUT = Path(__file__).resolve().parent
LANE = OUT.parent
REPO = LANE.parents[1]
PROJECT_AGENTS = REPO / "AGENTS.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, relative_to: Path | None = None) -> dict[str, Any]:
    shown = path if relative_to is None else path.relative_to(relative_to)
    return {
        "path": str(shown).replace("/", "\\"),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def normalized_relative(value: str) -> str:
    return value.replace("\\", "/")


def histogram(values: list[Any]) -> list[dict[str, Any]]:
    counts = Counter(value for value in values if value is not None)
    return [
        {"value": value, "frame_count": count}
        for value, count in sorted(
            counts.items(), key=lambda item: (type(item[0]).__name__, str(item[0]))
        )
    ]


def tag_summary(frames: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [frame.get(field) for frame in frames]
    return {
        "missing_count": sum(value is None for value in values),
        "histogram": histogram(values),
    }


def fmt_hist(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "none"
    return ", ".join(
        f"`{entry['value']}` × {entry['frame_count']}" for entry in entries
    )


def jnum(value: Any) -> str:
    if value is None:
        return "not computed"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


inventory = read_json(OUT / "stage-a-inventory.json")
decode = read_json(OUT / "stage-b-decode.json")
range_result = read_json(OUT / "stage-c-range.json")
roles = read_json(OUT / "stage-d-roles.json")
flat = read_json(OUT / "stage-e-flat.json")
summary = read_json(OUT / "summary.json")
session_before = read_json(OUT / "session-snapshot-before.json")
session_after = read_json(OUT / "session-snapshot-after.json")
session_invariance = read_json(OUT / "session-invariance.json")
source_before = read_json(OUT / "source-tree-before.json")
source_after = read_json(OUT / "source-tree-after.json")
source_invariance = read_json(OUT / "source-tree-invariance.json")
freeze_manifest = read_json(LANE / "freeze-manifest.json")

scientific_artifacts = {
    "inventory": inventory,
    "decode": decode,
    "range": range_result,
    "roles": roles,
    "flat": flat,
    "summary": summary,
}
for name, artifact in scientific_artifacts.items():
    if artifact["label"] != LABEL:
        raise RuntimeError(f"{name} label drifted: {artifact['label']!r}")

command_files = [
    "build.json",
    "freeze-pre.json",
    "stage-a-command.json",
    "stage-b-command.json",
    "stage-c-command.json",
    "stage-d-command.json",
    "stage-e-command.json",
    "summary-command.json",
]
command_records = [read_json(OUT / name) for name in command_files]
for record in command_records:
    if record["label"] != LABEL:
        raise RuntimeError(f"command label drifted: {record['stage']}")
    log_path = OUT / record["stdout_stderr_file"]
    record["stdout_stderr"] = file_record(log_path, OUT)

freeze_line = json.loads((OUT / "freeze-pre.log").read_text(encoding="utf-8"))
if freeze_line["status"] != "PASS":
    raise RuntimeError("pre-data freeze check was not PASS")

filesystem_before = {
    normalized_relative(row["relative_path"]): row for row in session_before["files"]
}
filesystem_after = {
    normalized_relative(row["relative_path"]): row for row in session_after["files"]
}
inventory_frames = [
    frame
    for stack in inventory["stacks"].values()
    for frame in stack["frames"]
]
inventory_paths = {
    normalized_relative(frame["relative_path"]): frame for frame in inventory_frames
}

if filesystem_before != filesystem_after:
    raise RuntimeError("authorized-session snapshots differ")
if set(filesystem_before) != set(inventory_paths):
    missing_from_inventory = sorted(set(filesystem_before) - set(inventory_paths))
    missing_from_filesystem = sorted(set(inventory_paths) - set(filesystem_before))
    raise RuntimeError(
        "filesystem/inventory population mismatch: "
        f"missing inventory={missing_from_inventory[:3]}, "
        f"missing filesystem={missing_from_filesystem[:3]}"
    )
if sum(row["bytes"] for row in filesystem_before.values()) != sum(
    frame["byte_size"] for frame in inventory_frames
):
    raise RuntimeError("filesystem/inventory byte totals differ")

exif_counts: dict[str, dict[str, int]] = {}
for command in inventory["exiftool"]["commands"]:
    match = re.search(r"(\d+) image files read", command["stderr"])
    if match is None:
        raise RuntimeError(f"cannot parse ExifTool population: {command['stderr']!r}")
    exif_counts.setdefault(command["group"], {})[command["mode"]] = int(match.group(1))

focus_fields = [
    "FocusPosition",
    "FocusPosition2",
    "FocusPosition3",
    "FocusDistance",
    "FocusDistance2",
]
setting_fields = [
    "ExposureTime",
    "ISO",
    "FNumber",
    "FocalLength",
    "LensModel",
    "LensType3",
    "ImageStabilization",
    "Orientation",
    "CameraOrientation",
    "ReleaseMode",
    "Model",
    "Make",
    "ImageWidth",
    "ImageHeight",
    "ExifImageWidth",
    "ExifImageHeight",
]
formatted_fields = [
    "formatted_ImageStabilization",
    "formatted_Orientation",
    "formatted_CameraOrientation",
    "formatted_ReleaseMode",
    "formatted_LensModel",
    "formatted_LensType3",
    "formatted_Model",
]

stack_evidence: dict[str, Any] = {}
for stack_name, stack in inventory["stacks"].items():
    frames = stack["frames"]
    observed = len(frames)
    numeric_count = exif_counts[stack_name]["numeric"]
    formatted_count = exif_counts[stack_name]["formatted"]
    if not (
        observed
        == stack["observed_frames"]
        == numeric_count
        == formatted_count
    ):
        raise RuntimeError(f"population mismatch in {stack_name}")
    stack_evidence[stack_name] = {
        "role": stack["role"],
        "expected_frames": stack["expected_frames"],
        "observed_frames": observed,
        "count_matches": stack["count_matches"],
        "filesystem_frames": sum(
            path == stack_name or path.startswith(stack_name + "/")
            for path in filesystem_before
        ),
        "exiftool_numeric_frames": numeric_count,
        "exiftool_formatted_frames": formatted_count,
        "bytes": sum(frame["byte_size"] for frame in frames),
        "first_capture_time": frames[0]["capture_time"],
        "last_capture_time": frames[-1]["capture_time"],
        "focus_tags": {
            field: tag_summary(frames, field) for field in focus_fields
        },
        "settings": {
            field: tag_summary(frames, field) for field in setting_fields
        },
        "formatted_settings": {
            field: tag_summary(frames, field) for field in formatted_fields
        },
        "capture_units": stack["capture_units"],
        "exposure_time_histogram": stack["exposure_time_histogram"],
    }

inventory_by_path = {
    normalized_relative(frame["relative_path"]): frame for frame in inventory_frames
}
decode_by_path = {
    normalized_relative(frame["relative_path"]): frame for frame in decode["frames"]
}
decode_checks = {
    "frame_count": len(decode["frames"]),
    "path_population_equal_to_inventory": set(decode_by_path) == set(inventory_by_path),
    "raw_sha256_matches_inventory_every_frame": all(
        decode_by_path[path]["raw_sha256"] == inventory_by_path[path]["raw_sha256"]
        for path in inventory_by_path
    ),
    "status_pass_count": sum(frame["status"] == "PASS" for frame in decode["frames"]),
    "crosscheck_returncode_zero_count": sum(
        frame["rawler_crosscheck"]["returncode"] == 0 for frame in decode["frames"]
    ),
    "payload_matches_rawpy_count": sum(
        frame["rawler_crosscheck"]["comparison"]["payload_matches_rawpy"]
        for frame in decode["frames"]
    ),
    "binary_hash_matches_every_frame": all(
        frame["rawler_crosscheck"]["binary_sha256"]
        == decode["decoder_contract"]["frozen_binary_sha256"]
        for frame in decode["frames"]
    ),
    "rawpy_visible_shapes": sorted(
        {
            tuple(frame["rawpy"]["visible_mosaic_shape_yx"])
            for frame in decode["frames"]
        }
    ),
    "rawler_active_shapes": sorted(
        {
            tuple(frame["rawler_crosscheck"]["active_shape_yx"])
            for frame in decode["frames"]
        }
    ),
    "rawler_buffer_shapes": sorted(
        {
            tuple(frame["rawler_crosscheck"]["buffer_shape_yx"])
            for frame in decode["frames"]
        }
    ),
    "canonical_overlap_shapes": sorted(
        {
            tuple(frame["rawler_crosscheck"]["rawpy_overlap_shape_yx"])
            for frame in decode["frames"]
        }
    ),
    "trailing_active_columns_not_scored": sorted(
        {
            frame["rawler_crosscheck"]["trailing_active_columns_not_in_rawpy"]
            for frame in decode["frames"]
        }
    ),
    "group_counts": dict(
        sorted(Counter(frame["group"] for frame in decode["frames"]).items())
    ),
}
if not all(
    [
        decode_checks["path_population_equal_to_inventory"],
        decode_checks["raw_sha256_matches_inventory_every_frame"],
        decode_checks["status_pass_count"] == decode_checks["frame_count"],
        decode_checks["crosscheck_returncode_zero_count"] == decode_checks["frame_count"],
        decode_checks["payload_matches_rawpy_count"] == decode_checks["frame_count"],
        decode_checks["binary_hash_matches_every_frame"],
    ]
):
    raise RuntimeError("independent Stage B aggregation did not fully pass")

range_evidence = {
    "status": range_result["status"],
    "frequency_contract": range_result["frequency_contract"],
    "equivalence_bars": range_result["equivalence_bars"],
    "lattice_rows": range_result["lattice"]["rows"],
    "lattice_columns": range_result["lattice"]["columns"],
    "lattice_coordinate_count": len(range_result["lattice"]["normalized_xy"]),
    "lattice_coordinates": range_result["lattice"]["normalized_xy"],
    "stack_results": {
        name: {
            "status": result["status"],
            "reason": result["reason"],
            "site_curve_count": len(result.get("site_curves", [])),
            "site_curves": result.get("site_curves", []),
        }
        for name, result in range_result["stacks"].items()
    },
    "joint_sites": range_result["joint_sites"],
    "robust_fit": range_result["robust_fit"],
    "node_density": range_result["node_density"],
}

role_evidence = {
    "status": roles["status"],
    "role_ledger_path": roles["role_ledger_path"],
    "role_ledger_sha256": roles["role_ledger_sha256"],
    "missing_roles": roles["missing_roles"],
    "predicates": roles["predicates"],
    "site_evidence": roles["site_evidence"],
    "sampling_ratio": roles["sampling_ratio"],
    "j_tr_computed": roles["j_tr_computed"],
    "j_tr": roles["j_tr"],
    "score_callback_called": roles["score_callback_called"],
    "violations": roles["violations"],
}

flat_groups: list[dict[str, Any]] = []
for group in flat["exposure_groups"]:
    item: dict[str, Any] = {
        "exposure_seconds": group.get("exposure_seconds", 6.0),
        "frame_count": group.get("frame_count", 65),
        "status": group["status"],
    }
    if "reason" in group:
        item.update(
            {
                "reason": group["reason"],
                "observed_statistic": None,
                "phase_scramble_q99": None,
                "phase_scramble_p_upper": None,
                "phase_scramble_count": None,
                "null_statistic": None,
                "frequency_power": None,
            }
        )
    else:
        repeatability = group["repeatability"]
        item.update(
            {
                "split_frame_counts": group["split_frame_counts"],
                "temporal_split_rule": group["temporal_split_rule"],
                "frequency_power": group["frequency_power"],
                "statistic": repeatability["statistic"],
                "statistic_definition": repeatability["statistic_definition"],
                "observed_statistic": repeatability["observed_repeatable_power"],
                "phase_scramble_q99": repeatability["phase_scramble_q99"],
                "phase_scramble_p_upper": repeatability["phase_scramble_p_upper"],
                "phase_scramble_count": repeatability["phase_scramble_count"],
                "null_statistic": repeatability["null_statistic"],
                "structured_alpha": repeatability["structured_alpha"],
                "pair_repeatable_power": repeatability["pair_repeatable_power"],
                "repeatable_to_total_power_ratio": repeatability[
                    "repeatable_to_total_power_ratio"
                ],
            }
        )
    flat_groups.append(item)

flat_evidence = {
    "status": flat["status"],
    "certificate_sufficient": flat["certificate_sufficient"],
    "insufficiency_reason": flat["insufficiency_reason"],
    "frequency_contract": flat["frequency_contract"],
    "exposure_groups": flat_groups,
    "core_probe": flat["core_probe"],
}

artifact_paths = {
    "stage_a_inventory": OUT / "stage-a-inventory.json",
    "stage_b_decode": OUT / "stage-b-decode.json",
    "stage_c_range": OUT / "stage-c-range.json",
    "stage_d_roles": OUT / "stage-d-roles.json",
    "stage_e_flat": OUT / "stage-e-flat.json",
    "summary": OUT / "summary.json",
}
artifact_records = {
    name: file_record(path, LANE) for name, path in artifact_paths.items()
}

for name, expected in summary["artifact_hashes"].items():
    key = {
        "inventory_sha256": "stage_a_inventory",
        "decode_sha256": "stage_b_decode",
        "range_sha256": "stage_c_range",
        "roles_sha256": "stage_d_roles",
        "flat_sha256": "stage_e_flat",
    }[name]
    if artifact_records[key]["sha256"] != expected:
        raise RuntimeError(f"summary artifact hash mismatch: {name}")

evidence = {
    "schema": "m135-executor-evidence-v1",
    "label": LABEL,
    "not_independent_verification": True,
    "inventory": {
        "status": inventory["status"],
        "filesystem_population": {
            "regular_file_count": session_before["regular_file_count"],
            "regular_file_bytes": session_before["regular_file_bytes"],
            "listing_sha256": session_before["regular_file_listing_sha256"],
            "reparse_file_count": session_before["reparse_file_count"],
        },
        "filesystem_equals_inventory_population": set(filesystem_before)
        == set(inventory_paths),
        "filesystem_equals_inventory_bytes": sum(
            row["bytes"] for row in filesystem_before.values()
        )
        == sum(frame["byte_size"] for frame in inventory_frames),
        "unexpected_arw": inventory["unexpected_arw"],
        "source_snapshot": inventory["source_snapshot"],
        "stacks": stack_evidence,
    },
    "coarse_encoder": inventory["coarse_encoder"],
    "decode": {
        "status": decode["status"],
        "decoder_contract": decode["decoder_contract"],
        "checks": decode_checks,
    },
    "image_range": range_evidence,
    "roles": role_evidence,
    "flat": flat_evidence,
    "summary": {
        key: value
        for key, value in summary.items()
        if key not in {"invocation"}
    },
    "session_invariance": session_invariance,
    "source_invariance": source_invariance,
    "scientific_artifacts": artifact_records,
}

evidence_path = OUT / "executor-evidence.json"
evidence_path.write_text(
    json.dumps(evidence, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    encoding="utf-8",
    newline="\n",
)

command_outcomes = {
    "build": "CROSSCHECK_BUILD_HASH_MATCH",
    "pre-data-freeze-check": freeze_line["status"],
    "stage-a-inventory": inventory["status"],
    "stage-b-decode": decode["status"],
    "stage-c-range": range_result["status"],
    "stage-d-roles": roles["status"],
    "stage-e-flat": flat["status"],
    "summary": summary["status"],
}

source_files = {
    "project_agents": PROJECT_AGENTS,
    "lane_readme": LANE / "README.md",
    "preregistration": LANE / "PREREGISTRATION.md",
    "amendment_16": LANE / "AMENDMENT-16.md",
    "config": LANE / "config.json",
    "instrument": LANE / "instrument.py",
    "freeze": LANE / "freeze.py",
    "artifact_schemas": LANE / "artifact-schemas.json",
    "role_ledger_template": LANE / "role-ledger.template.json",
    "cargo_manifest": LANE / "Cargo.toml",
    "cargo_lock": LANE / "Cargo.lock",
    "crosscheck_source": LANE / "src" / "main.rs",
    "freeze_manifest": LANE / "freeze-manifest.json",
}

execution_inputs = [
    path
    for path in sorted(OUT.iterdir(), key=lambda candidate: candidate.name)
    if path.is_file()
    and path.name
    not in {
        "executor-evidence.json",
        "generate-reports.py",
    }
]
execution_input_hashes = {
    path.name: file_record(path, LANE) for path in execution_inputs
}

manifest = {
    "schema": "m135-burned-slide-physical-commissioning-run-manifest-v1",
    "label": LABEL,
    "model": MODEL,
    "verification_scope": {
        "statement": "Author-executed commissioning; not independently verified by this executor.",
        "independent_pass_source": "The authorizing instruction supplied an independent PASS for the authorized-session read.",
        "independent_pass_commit": AUTHORIZED_COMMIT,
        "executor_check": "The frozen source closure was mechanically byte-compared with the supplied-PASS commit before access and remained invariant through the run.",
    },
    "authorization": {
        "m139_host_quiet_lock": "explicitly released by the authorizing instruction",
        "authorized_session_root": inventory["source_root"],
        "session_status": "deliberately burned development session",
        "d_drive_policy": "strictly read-only",
        "score_bearing": False,
    },
    "write_scope": {
        "owned": [
            "experiments\\M135-slide-physical-commissioning\\out\\",
            "experiments\\M135-slide-physical-commissioning\\RESULTS.md",
            "experiments\\M135-slide-physical-commissioning\\run-manifest.json",
        ],
        "recorded_build_target": str(
            LANE / "target" / "release" / "m135-slide-raw-crosscheck.exe"
        ),
        "recorded_build_target_note": "The exact frozen README build command necessarily used the lane's ignored target directory; no target file is included in the result commit.",
        "scratch": str(OUT / "scratch"),
        "cache": str(OUT / "cache"),
        "scratch_file_count_after_run": 0,
        "cache_file_count_after_run": 0,
        "d_drive_files_created": 0,
    },
    "repository": {
        "root": str(REPO),
        "source_head_at_start": source_before["execution_head"],
        "source_head_after_run": source_after["execution_head_after_run"],
        "shared_head_changed_during_run": source_before["execution_head"]
        != source_after["execution_head_after_run"],
        "independently_authorized_commit": AUTHORIZED_COMMIT,
        "authorized_commit_path_diff_before": source_before[
            "authorized_commit_diff_lines"
        ],
        "authorized_commit_path_diff_after": source_after[
            "authorized_commit_diff_lines"
        ],
        "frozen_source_snapshot_before": file_record(
            OUT / "source-tree-before.json", LANE
        ),
        "frozen_source_snapshot_after": file_record(
            OUT / "source-tree-after.json", LANE
        ),
        "frozen_source_invariance": source_invariance,
    },
    "environment": {
        "frozen_instrument_environment": inventory["invocation"]["environment"],
        "build_and_process_environment": command_records[0]["environment"],
        "scratch_overrides": {
            "TEMP": str(OUT / "scratch"),
            "TMP": str(OUT / "scratch"),
            "TMPDIR": str(OUT / "scratch"),
            "XDG_CACHE_HOME": str(OUT / "cache"),
        },
    },
    "commands": [
        {
            **record,
            "outcome": command_outcomes[record["stage"]],
        }
        for record in command_records
    ],
    "tools": {
        "python": freeze_manifest["dependencies"]["python"],
        "python_packages": freeze_manifest["dependencies"]["packages"],
        "python_distributions": freeze_manifest["dependencies"]["distributions"],
        "rawpy_libraw_version": freeze_manifest["dependencies"][
            "rawpy_libraw_version"
        ],
        "exiftool": freeze_manifest["dependencies"]["exiftool"],
        "cargo": freeze_manifest["external_decoder_path"][
            "cargo_dependency_closure"
        ]["cargo"],
        "rustc": freeze_manifest["external_decoder_path"][
            "cargo_dependency_closure"
        ]["rustc"],
        "cargo_dependency_closure": {
            key: freeze_manifest["external_decoder_path"][
                "cargo_dependency_closure"
            ][key]
            for key in ("aggregate_sha256", "byte_count", "file_count")
        },
        "crosscheck_executable": {
            "path": decode["decoder_contract"]["binary_path"],
            "bytes": decode["decoder_contract"]["frozen_binary_bytes"],
            "sha256": decode["decoder_contract"]["frozen_binary_sha256"],
        },
    },
    "source_hashes": {
        name: file_record(path, REPO) for name, path in source_files.items()
    },
    "scientific_artifacts": artifact_records,
    "execution_evidence": {
        "executor_evidence": file_record(evidence_path, LANE),
        "inputs": execution_input_hashes,
    },
    "scientific_outcomes": {
        "inventory": {
            "evidence_classes": ["MEASURED", "VERIFIED"],
            "status": inventory["status"],
            "filesystem_equals_exiftool_population": True,
        },
        "coarse_encoder_range": {
            "evidence_classes": ["MEASURED", "VERIFIED"],
            "status": summary["coarse_encoder"],
        },
        "image_derived_range": {
            "evidence_classes": ["COULD NOT DETERMINE"],
            "status": summary["image_range"],
            "fit": range_result["robust_fit"],
            "node_density": range_result["node_density"],
        },
        "full_j_tr_identifiability": {
            "evidence_classes": ["MEASURED", "VERIFIED"],
            "status": summary["identifiability"],
            "j_tr_computed": summary["j_tr_computed"],
            "j_tr": summary["j_tr"],
            "score_callback_called": roles["score_callback_called"],
        },
        "real_optical_intervention": {
            "evidence_classes": ["COULD NOT DETERMINE"],
            "status": summary["real_optical_intervention"],
        },
        "flat_diagnostics": {
            "evidence_classes": ["MEASURED", "COULD NOT DETERMINE"],
            "status": summary["flat_diagnostic"],
            "groups": flat_groups,
        },
        "physical_binding": {
            "evidence_classes": ["VERIFIED"],
            "status": summary["physical_binding"],
        },
        "session_invariance": {
            "evidence_classes": ["VERIFIED"],
            "status": "UNCHANGED" if session_invariance["unchanged"] else "CHANGED",
        },
    },
    "summary_recomputation": {
        "inventory": summary["inventory_recomputed_from_bound_inputs"],
        "decode": summary["decode_recomputed_from_bound_inputs"],
        "range": summary["range_recomputed_from_bound_inputs"],
        "flat": summary["flat_recomputed_from_bound_inputs"],
        "artifact_link_checks": summary["artifact_link_checks"],
    },
    "authorized_session_invariance": session_invariance,
    "anomalies": [
        {
            "type": "post-processing comparison false negative",
            "first_command_exit_code": 2,
            "preserved_artifact": "out\\session-invariance-powershell-false-negative.json",
            "preserved_output": "out\\session-invariance-powershell-false-negative.log",
            "resolution": "Compared the two already-captured JSON snapshots structurally in Python without re-enumerating D:\\; all 657 records and all aggregate fields were identical.",
            "scientific_stage_affected": False,
        },
        {
            "type": "NumPy deprecation warning",
            "commands": ["stage-c-range", "stage-e-flat", "summary"],
            "message": "np.cross on 2-dimensional vectors is deprecated",
            "exit_codes": [0, 0, 0],
            "code_or_configuration_changed": False,
        },
    ],
}

manifest_path = LANE / "run-manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    encoding="utf-8",
    newline="\n",
)

lines: list[str] = []
add = lines.append
add("# M135 burned-slide physical commissioning results")
add("")
add(f"**{LABEL}.**")
add("")
add(
    "This is an authorized author-executed commissioning run on a deliberately "
    "burned development session. It is not an independent verification, does "
    "not populate M1, does not bind M138, and makes no score or SOTA claim."
)
add("")
add("## Verdicts")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add("| Question | Evidence class | Frozen outcome | Ruling |")
add("|---|---|---|---|")
add(
    f"| Inventory | MEASURED + VERIFIED | `{summary['inventory']}` | "
    "All 657 regular files are the 657 inventoried/ExifTool-populated ARWs. |"
)
add(
    f"| Coarse encoder range | MEASURED + VERIFIED | "
    f"`{summary['coarse_encoder']}` | Both tilted stacks have complete "
    "`FocusPosition2` minima 57 and maxima 59. |"
)
add(
    f"| Image-derived range | COULD NOT DETERMINE | "
    f"`{summary['image_range']}` | Both frozen low-pass quadrilateral selectors "
    "refused; no range fit or node-density ratio exists. |"
)
add(
    f"| Full `J_TR` identifiability | MEASURED + VERIFIED | "
    f"`{summary['identifiability']}` | `j_tr_computed=false`, `j_tr=null`; "
    "no ratio is identifiable. |"
)
add(
    f"| Real optical intervention | COULD NOT DETERMINE | "
    f"`{summary['real_optical_intervention']}` | The preregistered Stage A/C "
    "predicate did not establish equivalent physical range. |"
)
add(
    f"| Flat diagnostics | MEASURED + COULD NOT DETERMINE | "
    f"`{summary['flat_diagnostic']}` | 1 s and 2.5 s are structured; 6 s was "
    "refused for clipping. |"
)
add(
    f"| Physical binding | VERIFIED | `{summary['physical_binding']}` | "
    "Missing reference/calibration roles and insufficient flat evidence leave "
    "the session unbound. |"
)
add(
    "| Session invariance | VERIFIED | `UNCHANGED` | Before/after "
    "`Get-ChildItem -Force` snapshots contain the same 657 records and "
    "26,156,716,032 bytes. |"
)
add("")
add("## Exact command outcomes")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add("| Command stage | Exit | Duration (s) | Outcome |")
add("|---|---:|---:|---|")
for record in command_records:
    add(
        f"| `{record['stage']}` | {record['exit_code']} | "
        f"{record['duration_seconds']:.6f} | "
        f"`{command_outcomes[record['stage']]}` |"
    )
add("")
add(
    "Every frozen command captured `$LASTEXITCODE` immediately after the "
    "process and before displaying or filtering output. No frozen command "
    "exited 1 or 2. Scientific negatives at exit 0 were retained and the run "
    "continued as preregistered."
)
add("")
add("## Inventory and metadata")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add("### Population equality")
add("")
add("| Population | Frames | Bytes / evidence |")
add("|---|---:|---|")
add(
    f"| Filesystem, `Get-ChildItem -Force`, regular non-reparse files | "
    f"{session_before['regular_file_count']} | "
    f"{session_before['regular_file_bytes']} bytes; listing SHA-256 "
    f"`{session_before['regular_file_listing_sha256']}` |"
)
add(
    f"| Stage A inventory | {len(inventory_frames)} | "
    f"{sum(frame['byte_size'] for frame in inventory_frames)} bytes |"
)
add(
    f"| ExifTool numeric population | {sum(v['numeric'] for v in exif_counts.values())} | "
    "All four per-stack commands exited 0. |"
)
add(
    f"| ExifTool formatted population | {sum(v['formatted'] for v in exif_counts.values())} | "
    "All four per-stack commands exited 0. |"
)
add("")
add(
    "The path populations are exactly equal, `unexpected_arw=[]`, and Stage A's "
    "own before/after source snapshot is unchanged."
)
add("")
add("### Per-stack frames and timestamps")
add("")
add("| Stack | Frames | Bytes | First timestamp | Last timestamp |")
add("|---|---:|---:|---|---|")
for name in (
    "tilted-sw4-cpl",
    "tilted-sw10-cpl",
    "flat-sw4-cpl",
    "very-tilted-all-axis-sw10-cpl",
):
    row = stack_evidence[name]
    add(
        f"| `{name}` | {row['observed_frames']} | {row['bytes']} | "
        f"`{row['first_capture_time']}` | `{row['last_capture_time']}` |"
    )
add("")
add("### Focus tags and complete `FocusPosition2` histograms")
add("")
add("| Stack | `FocusPosition2` histogram; missing | `FocusDistance2` histogram; missing | Other requested focus tags |")
add("|---|---|---|---|")
for name in (
    "tilted-sw4-cpl",
    "tilted-sw10-cpl",
    "flat-sw4-cpl",
    "very-tilted-all-axis-sw10-cpl",
):
    focus = stack_evidence[name]["focus_tags"]
    add(
        f"| `{name}` | {fmt_hist(focus['FocusPosition2']['histogram'])}; "
        f"{focus['FocusPosition2']['missing_count']} missing | "
        f"{fmt_hist(focus['FocusDistance2']['histogram'])}; "
        f"{focus['FocusDistance2']['missing_count']} missing | "
        f"`FocusPosition` {focus['FocusPosition']['missing_count']} missing; "
        f"`FocusPosition3` {focus['FocusPosition3']['missing_count']} missing; "
        f"`FocusDistance` {focus['FocusDistance']['missing_count']} missing |"
    )
add("")
add("### Capture settings")
add("")
add("| Stack | Exposure histogram | ISO | f-number | Reported focal length |")
add("|---|---|---|---|---|")
for name in (
    "tilted-sw4-cpl",
    "tilted-sw10-cpl",
    "flat-sw4-cpl",
    "very-tilted-all-axis-sw10-cpl",
):
    settings = stack_evidence[name]["settings"]
    add(
        f"| `{name}` | {fmt_hist(settings['ExposureTime']['histogram'])} s | "
        f"{fmt_hist(settings['ISO']['histogram'])} | "
        f"{fmt_hist(settings['FNumber']['histogram'])} | "
        f"{fmt_hist(settings['FocalLength']['histogram'])} mm |"
    )
add("")
add(
    "All 657 frames report Sony `ILCE-7CM2`, lens "
    "`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` (`LensType3=33094`), "
    "image stabilization `1` / `On`, raw and camera orientation `1` / "
    "`Horizontal (normal)`, release mode `5` / `Exposure Bracketing`, raw "
    "buffer dimensions 7168×5120, and EXIF dimensions 7008×4672."
)
add("")
add("## Decoder crosscheck")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"Stage B is `{decode['status']}` on {decode_checks['frame_count']} of "
    f"{decode_checks['frame_count']} frames. Every RAW SHA-256 matches Stage A; "
    "every rawler process returned 0; and every canonical 4688×7028 overlap "
    "matched rawpy bit for bit. Rawler's full active area is 4688×7032 inside "
    "a 5120×7168 buffer; the four trailing active columns are recorded and "
    "excluded from statistics. The frozen executable is "
    f"{decode['decoder_contract']['frozen_binary_bytes']} bytes with SHA-256 "
    f"`{decode['decoder_contract']['frozen_binary_sha256']}`."
)
add("")
add("## Coarse encoder range")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    "`tilted-sw4-cpl`: `57×76, 58×80, 59×26`, zero missing. "
    "`tilted-sw10-cpl`: `57×38, 58×40, 59×14`, zero missing. "
    "Both minima are 57 and both maxima are 59, so the frozen coarse predicate "
    "is `COARSE_ENCODER_RANGE_EQUAL`. This is equality of the reported coarse "
    "encoder range only, not image-derived physical equivalence."
)
add("")
add("## Image-derived range")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"The frozen result is `{range_result['status']}`. For each tilted stack the "
    "recorded reason is `no low-pass quadrilateral satisfied the frozen "
    "selector`. The artifact preserves the fixed 8×8 lattice's 64 normalized "
    "coordinates, registration stop 0.06 cyc/native px, focus band "
    "[0.06, 0.20] cyc/native px, and the bars: at least 48 joint eligible sites, "
    "|a|≤0.02, |b−1|≤0.04, q95(|residual|)≤0.03."
)
add("")
add(
    "No site curve was emitted because the low-pass quadrilateral prerequisite "
    "failed for both stacks. The exact frozen outputs are: eligible count 0, "
    "`u4=null`, `u10=null`, `robust_fit=null`, and `node_density=null`. No site, "
    "crop, threshold, registration, decoder, or frame subset was changed or "
    "imputed."
)
add("")
add("## Full `J_TR` identifiability")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"Stage D returned `{roles['status']}` from the unmodified ledger SHA-256 "
    f"`{roles['role_ledger_sha256']}`. Missing roles are: "
    + ", ".join(f"`{role}`" for role in roles["missing_roles"])
    + "."
)
add("")
add(
    "`j_tr_computed=false`, `j_tr=null`, `sampling_ratio=null`, and "
    "`score_callback_called=false`. Therefore no `J_TR(sw4)/J_TR(sw10)` ratio "
    "was computed or inferred. Treating sw4 as truth would use the claimed "
    "improvement arm as its own reference and is circular."
)
add("")
add("## Real optical intervention")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"The summary reports `{summary['real_optical_intervention']}`. Distinct "
    "sw4/sw10 files and equal coarse encoder endpoints were measured, but the "
    "frozen Stage C physical-range predicate was undetermined. Consequently "
    "`REAL_OPTICAL_ARM_PRESENT` is not reported, and no improvement direction "
    "is claimed without identifiable `J_TR`."
)
add("")
add("## Flat diagnostics")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add("| Exposure | Frames / splits | Observed statistic | Phase-scramble q99 | Null / p-value | Status |")
add("|---:|---|---:|---:|---|---|")
for group in flat_groups:
    if group["observed_statistic"] is None:
        add(
            f"| {jnum(group['exposure_seconds'])} s | {group['frame_count']} | "
            "not computed | not computed | not computed; clipping refusal | "
            f"`{group['status']}` |"
        )
    else:
        add(
            f"| {jnum(group['exposure_seconds'])} s | {group['frame_count']} / "
            f"{group['split_frame_counts']} | {jnum(group['observed_statistic'])} | "
            f"{jnum(group['phase_scramble_q99'])} | "
            f"`{group['null_statistic']}`, 255 draws, "
            f"`p_upper={jnum(group['phase_scramble_p_upper'])}` | "
            f"`{group['status']}` |"
        )
add("")
for group in flat_groups:
    if group["frequency_power"] is None:
        add(
            f"- {jnum(group['exposure_seconds'])} s: `{group['reason']}`; "
            "the observed statistic, q99, and p-value are COULD NOT DETERMINE."
        )
    else:
        powers = ", ".join(
            f"{jnum(cell['frequency_native_cyc_per_px'])}: "
            f"{jnum(cell['mean_power'])}"
            for cell in group["frequency_power"]
        )
        add(
            f"- {jnum(group['exposure_seconds'])} s frequency power "
            f"(cyc/native px: mean power): {powers}."
        )
add("")
add(
    f"The aggregate frozen state is `{flat['status']}`. The existing M135 core "
    f"probe was `{flat['core_probe']['status']}` and was not invoked because "
    "the four modulo splits are not independent captures. A quiet flat would "
    "be necessary but insufficient; these results cannot bind M138."
)
add("")
add("## Physical binding")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"The terminal physical binding is `{summary['physical_binding']}`. The "
    "reference/calibration role gate is absent, the 6 s flat group is "
    "undetermined, and the quiet-flat condition is explicitly necessary but "
    "not sufficient."
)
add("")
add("## Session and source invariance")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"Before Stage A and after summary, the authorized session contained "
    f"{session_before['regular_file_count']} regular files totaling "
    f"{session_before['regular_file_bytes']} bytes. Both snapshots have listing "
    f"SHA-256 `{session_before['regular_file_listing_sha256']}` and all 657 "
    "path/size/creation-time/write-time/attribute records compare equal. There "
    "were zero reparse files. Stage A independently recorded matching "
    "before/after stat digest "
    f"`{inventory['source_snapshot']['before']['stat_digest_sha256']}`, and "
    "Stage B rebound every RAW SHA-256 before decoding."
)
add("")
add(
    f"The frozen tracked source closure contains {source_before['file_count']} "
    "files with aggregate SHA-256 "
    f"`{source_before['aggregate_sha256']}` before and after. The shared "
    f"repository HEAD moved from `{source_before['execution_head']}` to "
    f"`{source_after['execution_head_after_run']}` during the long run, but the "
    "path-scoped frozen source bytes remained identical to the independently "
    f"authorized commit `{AUTHORIZED_COMMIT}` and locally unchanged."
)
add("")
add(
    "A post-processing PowerShell string reconstruction returned a false "
    "negative and exit 2 despite identical stored listing digests. Its artifact "
    "and output are preserved. A structural comparison of the two already "
    "captured JSON snapshots, without a new D:\\ enumeration, found every "
    "record equal. No scientific stage was rerun or changed."
)
add("")
add("## Provenance and frozen recomputation")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    f"Pre-data freeze check: `PASS`; freeze-manifest SHA-256 "
    f"`{freeze_line['manifest_sha256']}`. Crosscheck executable: "
    f"{freeze_line['crosscheck_executable_sha256']}. Stage artifact SHA-256 "
    "values are recorded in `run-manifest.json` and match the terminal "
    "`summary.json` links."
)
add("")
add(
    "The summary recomputed inventory, every-frame dual decode, image range, "
    "and flat diagnostics from bound inputs; all four recomputation flags and "
    "all eight artifact-link checks are true."
)
add("")
add("## Unanswered questions")
add("")
add(f"**Label for every result in this section: {LABEL}.**")
add("")
add(
    "1. Whether sw4 and sw10 cover equivalent physical focus range remains "
    "undetermined because neither frozen low-pass quadrilateral selector found "
    "a valid region."
)
add(
    "2. The full `J_TR` contrast, its arm ratio, and any improvement direction "
    "remain unidentified until independent same-site R1/R2, Y1/Y2, calibration, "
    "and matched-flat evidence exists."
)
add(
    "3. The 6 s flat-group repeatability statistic remains undetermined because "
    "all 65 frames triggered the frozen clipping refusal."
)
add(
    "4. No result here licenses M138 binding, a score, a comparator "
    "qualification, or a SOTA statement."
)
add("")

results_path = LANE / "RESULTS.md"
results_path.write_text(
    "\n".join(lines),
    encoding="utf-8",
    newline="\n",
)

print(
    json.dumps(
        {
            "executor_evidence": file_record(evidence_path, LANE),
            "results": file_record(results_path, LANE),
            "run_manifest": file_record(manifest_path, LANE),
        },
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )
)
