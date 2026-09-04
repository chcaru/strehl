"""Score frozen M3 profile packages after commissioning and host release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from m3_checker_v2 import (
    SiteProfiles,
    load_checker_definition,
    paired_p99,
    score_site,
    sha256_file,
    summarize,
    validate_geometry,
)


HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "measurement-contract.json"
CENSUS = HERE.parent / "M152-site-census" / "out" / "census-manifest.json"
COMMISSION = HERE / "out" / "commission-v2.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def parse_comparator(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("expected NAME=MANIFEST")
    return name, Path(path)


def expected_sites() -> dict[str, str]:
    manifest = read_json(CENSUS)
    rows = manifest["m3"]["sufficiency"]["selected_sites"]
    return {str(row["site_id"]): str(row["capture_id"]) for row in rows}


def load_site(path: Path, row: dict[str, Any]) -> SiteProfiles:
    if sha256_file(path) != str(row["sha256"]):
        raise RuntimeError(f"profile payload hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as payload:
        required = {
            "offsets_native_px",
            "source_profiles",
            "output_profile",
            "normalization_source_index",
            "far_reference_source_index",
            "sharp_source_index",
            "output_patch",
            "sharp_source_patch",
        }
        missing = sorted(required - set(payload.files))
        if missing:
            raise RuntimeError(f"{path}: missing arrays {missing}")
        return SiteProfiles(
            site_id=str(row["site_id"]),
            capture_id=str(row["capture_id"]),
            offsets_native_px=np.array(payload["offsets_native_px"], copy=True),
            source_profiles=np.array(payload["source_profiles"], copy=True),
            output_profile=np.array(payload["output_profile"], copy=True),
            normalization_source_index=int(payload["normalization_source_index"]),
            far_reference_source_index=int(payload["far_reference_source_index"]),
            sharp_source_index=int(payload["sharp_source_index"]),
            output_patch=np.array(payload["output_patch"], copy=True),
            sharp_source_patch=np.array(payload["sharp_source_patch"], copy=True),
        )


def source_signature(site: SiteProfiles) -> str:
    digest = hashlib.sha256()
    for value in (
        site.offsets_native_px,
        site.source_profiles,
        np.asarray(site.normalization_source_index, dtype=np.int64),
        np.asarray(site.far_reference_source_index, dtype=np.int64),
        np.asarray(site.sharp_source_index, dtype=np.int64),
        site.sharp_source_patch,
    ):
        if value is None:
            digest.update(b"<none>")
            continue
        array = np.ascontiguousarray(value)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(array.shape).encode("ascii"))
        digest.update(memoryview(array).tobytes())
    return digest.hexdigest()


def load_package(
    manifest_path: Path,
    definition: dict[str, Any],
    definition_sha: str,
    expected: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    manifest_path = manifest_path.resolve()
    manifest = read_json(manifest_path)
    if manifest.get("schema") != "m161-m3-profile-package-v1":
        raise RuntimeError(f"{manifest_path}: unexpected package schema")
    if manifest.get("checker_definition_sha256") != definition_sha:
        raise RuntimeError(f"{manifest_path}: checker definition hash mismatch")
    if (
        manifest.get("census_manifest_sha256")
        != definition["site_population"]["manifest_sha256"]
    ):
        raise RuntimeError(f"{manifest_path}: census manifest hash mismatch")
    common = manifest.get("common_input", {})
    required_common = {
        "same_hashed_tiffs_all_arms": True,
        "linear_transfer_pass": True,
        "native_size_pass": True,
        "post_processing_none": True,
        "strehl_adapter_identity_pass": True,
    }
    failures = [
        name for name, required in required_common.items() if common.get(name) != required
    ]
    if failures:
        raise RuntimeError(
            f"{manifest_path}: common-input contract failed: {','.join(failures)}"
        )
    fingerprints = (
        "input_manifest_sha256",
        "input_pixel_payload_set_sha256",
        "run_manifest_sha256",
        "output_sha256",
    )
    malformed = [
        name
        for name in fingerprints
        if len(str(common.get(name, ""))) != 64
        or any(character not in "0123456789abcdef" for character in str(common[name]))
    ]
    if malformed:
        raise RuntimeError(
            f"{manifest_path}: missing or malformed fingerprints: "
            + ",".join(malformed)
        )

    geometry_rows = manifest.get("geometry_by_capture", {})
    if set(geometry_rows) != set(definition["site_population"]["required_capture_ids"]):
        raise RuntimeError(f"{manifest_path}: incomplete capture geometry")
    geometry_results = {
        capture: validate_geometry(values, definition)
        for capture, values in geometry_rows.items()
    }
    failed_geometry = [
        capture
        for capture, result in geometry_results.items()
        if result["verdict"] != "PASS"
    ]
    if failed_geometry:
        raise RuntimeError(
            f"{manifest_path}: UNMEASURED_WARP_INADEQUATE: "
            + ",".join(sorted(failed_geometry))
        )

    rows = manifest.get("sites", [])
    package_sites = {str(row["site_id"]): row for row in rows}
    if set(package_sites) != set(expected):
        missing = sorted(set(expected) - set(package_sites))
        extra = sorted(set(package_sites) - set(expected))
        raise RuntimeError(
            f"{manifest_path}: site mismatch missing={missing[:5]} extra={extra[:5]}"
        )
    scored = []
    source_signatures: dict[str, str] = {}
    for site_id in sorted(expected):
        row = package_sites[site_id]
        if str(row.get("capture_id")) != expected[site_id]:
            raise RuntimeError(f"{manifest_path}: capture mismatch at {site_id}")
        payload_path = (manifest_path.parent / str(row["payload"])).resolve()
        site = load_site(payload_path, row)
        source_signatures[site_id] = source_signature(site)
        scored.append(score_site(site, definition))
    return (
        {
            "product_id": str(manifest["product_id"]),
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "geometry": geometry_results,
            "common_input": {name: common[name] for name in fingerprints},
            "summary": summarize(scored, definition=definition),
        },
        scored,
        source_signatures,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument(
        "--comparator", action="append", default=[], type=parse_comparator
    )
    parser.add_argument("--out", type=Path, default=HERE / "out" / "m3-score.json")
    args = parser.parse_args()

    contract = read_json(CONTRACT)
    release = (HERE / contract["host_release_record"]).resolve()
    if not release.is_file():
        raise RuntimeError("host release record absent; refusing to score")
    commission = read_json(COMMISSION)
    if commission.get("verdict") != "PASS":
        raise RuntimeError("M3 v2 checker is not commissioned")

    definition, definition_sha = load_checker_definition()
    if commission.get("checker_definition_sha256") != definition_sha:
        raise RuntimeError("commissioning belongs to another checker definition")
    expected = expected_sites()
    candidate_record, candidate_rows, candidate_sources = load_package(
        args.candidate, definition, definition_sha, expected
    )
    if candidate_record["product_id"] != "strehl":
        raise RuntimeError("candidate package product_id must be strehl")
    comparators: dict[str, dict[str, Any]] = {}
    comparator_rows: dict[str, list[dict[str, Any]]] = {}
    comparator_sources: dict[str, dict[str, str]] = {}
    for name, path in args.comparator:
        record, rows, sources = load_package(
            path, definition, definition_sha, expected
        )
        if record["product_id"] != name:
            raise RuntimeError(
                f"comparator alias {name} does not match package product_id "
                f"{record['product_id']}"
            )
        comparators[name] = record
        comparator_rows[name] = rows
        comparator_sources[name] = sources
    required_names = {
        item["product_id"]
        for item in contract["required_products"]
        if item["role"] == "required_comparator"
    }
    if not required_names.issubset(comparators):
        raise RuntimeError(
            "required comparators absent: "
            + ",".join(sorted(required_names - set(comparators)))
        )
    common_keys = ("input_manifest_sha256", "input_pixel_payload_set_sha256")
    for name, record in comparators.items():
        mismatched = [
            key
            for key in common_keys
            if record["common_input"][key]
            != candidate_record["common_input"][key]
        ]
        if mismatched:
            raise RuntimeError(
                f"{name}: common-input fingerprints differ: {','.join(mismatched)}"
            )
        if comparator_sources[name] != candidate_sources:
            raise RuntimeError(
                f"{name}: externally warped source profiles or source selections differ"
            )

    comparison = paired_p99(candidate_rows, comparator_rows)
    absolute = candidate_record["summary"]
    overall = (
        "PASS"
        if absolute["verdict"] == "PASS" and comparison["verdict"] == "PASS"
        else "FAIL"
    )
    result = {
        "schema": "m161-m3-score-v1",
        "checker_definition_sha256": definition_sha,
        "commission_sha256": sha256_file(COMMISSION),
        "candidate": candidate_record,
        "comparators": comparators,
        "paired_comparison": comparison,
        "verdict": overall,
    }
    write_json(args.out, result)
    print(overall)
    return 0 if overall == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
