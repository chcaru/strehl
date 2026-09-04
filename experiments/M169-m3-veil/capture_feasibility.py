"""Metadata-only feasibility check for the frozen M3 capture population."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CENSUS = REPO / "experiments" / "M152-site-census" / "out" / "census-manifest.json"
DEFINITION = HERE / "m3-checker-definition-v2.json"
OUT = HERE / "out" / "capture-feasibility.json"
EXPECTED_CENSUS_SHA256 = (
    "35d5058afc1f310923ba2a3e5bf0cd3b91b3eb2df0e8d4868c22099de7bcd38d"
)
EXPECTED_DEFINITION_SHA256 = (
    "578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def arw_names(path: Path) -> set[str]:
    return {
        entry.name
        for entry in os.scandir(path)
        if entry.is_file(follow_symlinks=False)
        and Path(entry.name).suffix.casefold() == ".arw"
    }


def main() -> int:
    definition_sha = sha256_file(DEFINITION)
    census_sha = sha256_file(CENSUS)
    definition = read_json(DEFINITION)
    census = read_json(CENSUS)
    selected = census["m3"]["sufficiency"]["selected_sites"]
    selected_counts = Counter(str(row["capture_id"]) for row in selected)
    selected_files: dict[str, set[str]] = {}
    for row in selected:
        selected_files.setdefault(str(row["capture_id"]), set()).add(
            str(row["source_file"])
        )

    expected_ids = list(definition["site_population"]["required_capture_ids"])
    captures: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for row in census["m3"]["capture_results"]:
        capture_id = str(row["capture_id"])
        if capture_id not in expected_ids:
            continue
        path = Path(str(row["path"]))
        exists = path.is_dir()
        names = arw_names(path) if exists else set()
        expected_count = int(row["inventory_frame_count"])
        missing_selected = sorted(selected_files.get(capture_id, set()) - names)
        checks = {
            "directory_exists": exists,
            "arw_count_matches_census": len(names) == expected_count,
            "capture_contiguous": bool(row["capture_contiguous"]),
            "eligible_site_floor_met": int(row["eligible_site_count"])
            >= int(definition["site_population"]["minimum_edges_per_capture"]),
            "required_reach_is_400_native_px": int(row["required_reach_native_px"])
            == 400,
            "all_selected_source_files_exist": not missing_selected,
        }
        captures.append(
            {
                "capture_id": capture_id,
                "path": str(path),
                "inventory_frame_count": expected_count,
                "on_disk_arw_count": len(names),
                "eligible_site_count": int(row["eligible_site_count"]),
                "selected_site_count": int(selected_counts[capture_id]),
                "required_reach_native_px": int(row["required_reach_native_px"]),
                "missing_selected_source_files": missing_selected,
                "checks": checks,
                "verdict": "PASS" if all(checks.values()) else "FAIL",
            }
        )
        for name, passed in checks.items():
            if not passed:
                blockers.append(
                    {
                        "code": "CAPTURE_FEASIBILITY_FAILED",
                        "capture_id": capture_id,
                        "check": name,
                    }
                )

    global_checks = {
        "definition_sha256_matches_m161": definition_sha
        == EXPECTED_DEFINITION_SHA256,
        "census_sha256_matches_frozen_definition": census_sha
        == EXPECTED_CENSUS_SHA256
        == definition["site_population"]["manifest_sha256"],
        "all_required_captures_present": {row["capture_id"] for row in captures}
        == set(expected_ids),
        "census_verdict_sufficient": census["m3"]["sufficiency"]["verdict"]
        == "SUFFICIENT",
        "selected_site_count_is_500": len(selected) == 500,
        "selected_capture_counts_match_frozen_population": dict(selected_counts)
        == {
            "m3-duck-tape": 133,
            "m3-chia": 133,
            "m3-flower-fern": 132,
            "m3-razor-control": 102,
        },
        "all_selected_sites_have_400_native_px_reach": all(
            int(row["reach_native_px"]) == 400 for row in selected
        ),
    }
    for name, passed in global_checks.items():
        if not passed:
            blockers.append({"code": "GLOBAL_FEASIBILITY_FAILED", "check": name})

    result = {
        "schema": "m169-m3-capture-feasibility-v1",
        "method": (
            "metadata/path/hash checks only; directory entries were statted and "
            "no ARW content was opened"
        ),
        "pixel_files_opened": 0,
        "census_manifest": str(CENSUS),
        "census_manifest_sha256": census_sha,
        "checker_definition_sha256": definition_sha,
        "required_veil_reach_native_px": 400,
        "eligible_edges_overall": int(
            census["m3"]["sufficiency"]["eligible_edges_overall"]
        ),
        "selected_site_count": len(selected),
        "selected_site_counts": dict(sorted(selected_counts.items())),
        "captures": captures,
        "checks": global_checks,
        "blockers": blockers,
        "verdict": "PASS" if not blockers else "UNMEASURED_CAPTURE_INADEQUATE",
    }
    write_json(OUT, result)
    print(result["verdict"])
    print(
        "eligible=%d selected=%d reach=%d"
        % (
            result["eligible_edges_overall"],
            result["selected_site_count"],
            result["required_veil_reach_native_px"],
        )
    )
    for row in captures:
        print(
            "%s: disk=%d census=%d eligible=%d selected=%d verdict=%s"
            % (
                row["capture_id"],
                row["on_disk_arw_count"],
                row["inventory_frame_count"],
                row["eligible_site_count"],
                row["selected_site_count"],
                row["verdict"],
            )
        )
    if blockers:
        for blocker in blockers:
            print("BLOCKER " + json.dumps(blocker, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
