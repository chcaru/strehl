"""Admission audit for applying the commissioned M8-O checker to foreign renders.

This module does not inspect image samples and does not implement a hull checker.
It verifies provenance/metadata prerequisites before the unchanged checker may run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import tifffile


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "output_hash_matches",
    "all_source_images_present",
    "source_identity_auditable",
    "exact_output_to_source_placement_for_every_frame",
    "exact_resampler_discrete_support",
    "exact_output_crop_rotation_and_scale_map",
    "source_and_output_in_one_documented_linear_rgb_domain",
    "exact_per_frame_photometric_map_into_that_domain",
    "serialization_contract_known",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def tiff_metadata(path: Path) -> dict[str, Any]:
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        tags = {
            tag.name: tag.value
            for tag in page.tags.values()
            if tag.name
            in {
                "ImageDescription",
                "ICCProfile",
                "InterColorProfile",
                "Orientation",
                "Software",
            }
        }
        profile_key = next(
            (
                key
                for key in ("ICCProfile", "InterColorProfile")
                if isinstance(tags.get(key), bytes)
            ),
            None,
        )
        if profile_key is not None:
            icc = tags[profile_key]
            tags[profile_key] = {
                "bytes": len(icc),
                "sha256": hashlib.sha256(icc).hexdigest().upper(),
            }
        return {
            "shape": list(tif.series[0].shape),
            "dtype": str(tif.series[0].dtype),
            "tags": tags,
        }


def log_evidence(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {
            "present": False,
            "transforms": 0,
            "identity_references": 0,
            "contrast_maps": 0,
            "white_balance_maps": 0,
            "linear_rec2020_gamma1": False,
            "crop_size_only": False,
            "resampler_support_named": False,
            "photometric_formula_named": False,
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "present": True,
        "transforms": len(
            re.findall(r"(?m)^aligned_DSC\d+\.tif transform:", text)
        ),
        "identity_references": len(
            re.findall(
                r"(?m)^.*Align (DSC\d+\.tif) to \1\s*$",
                text,
            )
        ),
        "contrast_maps": len(
            re.findall(r"(?m)^aligned_DSC\d+\.tif contrast map:", text)
        ),
        "white_balance_maps": len(
            re.findall(r"(?m)^aligned_DSC\d+\.tif whitebalance:", text)
        ),
        "linear_rec2020_gamma1": (
            "Saved Linear Rec.2020 (D65, gamma 1.0) TIFF:" in text
        ),
        "crop_size_only": bool(
            re.search(r"cropped from \(\d+, \d+\) to \(\d+, \d+\)", text)
        ),
        "resampler_support_named": bool(
            re.search(
                r"(?i)\b(resampler|interpolation kernel|support taps?)\b",
                text,
            )
        ),
        "photometric_formula_named": bool(
            re.search(
                r"(?i)\b(photometric formula|apply contrast as|whitebalance formula)\b",
                text,
            )
        ),
    }


def admit(predicates: dict[str, bool]) -> bool:
    return all(predicates.get(name) is True for name in REQUIRED)


def audit(candidate: dict[str, Any]) -> dict[str, Any]:
    output = Path(candidate["output"])
    output_exists = output.is_file()
    output_hash = sha256(output) if output_exists else None

    source_dir_raw = candidate.get("source_dir")
    source_glob = candidate.get("source_glob")
    source_dir = Path(source_dir_raw) if source_dir_raw else None
    sources = (
        sorted(source_dir.glob(source_glob))
        if source_dir is not None
        and source_glob is not None
        and source_dir.is_dir()
        else []
    )
    expected_sources = int(candidate["expected_sources"])
    all_sources = len(sources) == expected_sources

    geometry_raw = candidate.get("geometry_manifest")
    geometry_path = Path(geometry_raw) if geometry_raw else None
    log = log_evidence(geometry_path)

    metadata = tiff_metadata(output) if output_exists else None
    source_metadata = tiff_metadata(sources[0]) if sources else None

    complete_geometry_log = bool(
        log["present"]
        and log["transforms"] + log["identity_references"] == expected_sources
    )
    documented_linear_domain = bool(
        candidate.get("exact_common_linear_domain_contract") is True
        and candidate.get("source_domain_contract")
        and candidate.get("output_domain_contract")
        and log["linear_rec2020_gamma1"]
        and source_metadata is not None
        and source_metadata["dtype"] == "float32"
        and metadata is not None
        and metadata["dtype"] == "float32"
    )

    predicates = {
        "output_hash_matches": (
            output_hash is not None and output_hash == candidate["sha256"]
        ),
        "all_source_images_present": all_sources,
        "source_identity_auditable": bool(
            all_sources and candidate.get("identity_evidence")
        ),
        "exact_output_to_source_placement_for_every_frame": bool(
            candidate.get("exact_placement_contract") is True
            and complete_geometry_log
        ),
        "exact_resampler_discrete_support": bool(
            candidate.get("exact_resampler_support_contract") is True
            and candidate.get("resampler_support")
            and log["resampler_support_named"]
        ),
        "exact_output_crop_rotation_and_scale_map": bool(
            candidate.get("exact_crop_rotation_scale_contract") is True
            and complete_geometry_log
            and log["crop_size_only"]
        ),
        "source_and_output_in_one_documented_linear_rgb_domain": (
            documented_linear_domain
        ),
        "exact_per_frame_photometric_map_into_that_domain": bool(
            candidate.get("exact_per_frame_photometric_contract") is True
            and candidate.get("per_frame_photometric_contract")
            and log["photometric_formula_named"]
        ),
        "serialization_contract_known": bool(
            metadata is not None
            and (
                (candidate["serialization"] == "uint16"
                 and metadata["dtype"] == "uint16")
                or (
                    candidate["serialization"] == "float32"
                    and metadata["dtype"] == "float32"
                )
            )
        ),
    }
    return {
        "id": candidate["id"],
        "stack": candidate["stack"],
        "output": str(output),
        "observed_sha256": output_hash,
        "source_count": len(sources),
        "expected_sources": expected_sources,
        "output_metadata": metadata,
        "first_source_metadata": source_metadata,
        "geometry_log": log,
        "predicates": predicates,
        "admissible_exact_m8_o": admit(predicates),
        "failed_predicates": [name for name in REQUIRED if not predicates[name]],
    }


def commission() -> int:
    complete = {name: True for name in REQUIRED}
    red_cases = {}
    for name in REQUIRED:
        planted = complete.copy()
        planted[name] = False
        red_cases[name] = not admit(planted)

    damaged = complete.copy()
    damaged["exact_resampler_discrete_support"] = False
    before = admit(damaged)
    damaged["exact_resampler_discrete_support"] = True
    after = admit(damaged)

    checks = {
        "green_untouched_complete_contract": admit(complete),
        "red_every_single_missing_predicate": all(red_cases.values()),
        "improvement_restoring_support_changes_reject_to_admit": (
            not before and after
        ),
    }
    payload = {
        "checks": checks,
        "red_cases": red_cases,
        "passed": all(checks.values()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commission", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "candidate-manifest.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.commission:
        return commission()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    rows = [audit(candidate) for candidate in manifest["comparators"]]
    strehl_rows = []
    for master in manifest["strehl_display_masters"]:
        path = Path(master["output"])
        exists = path.is_file()
        observed_hash = sha256(path) if exists else None
        metadata = tiff_metadata(path) if exists else None
        description = (
            str(metadata["tags"].get("ImageDescription", ""))
            if metadata is not None
            else ""
        )
        strehl_rows.append(
            {
                "stack": master["stack"],
                "output": str(path),
                "observed_sha256": observed_hash,
                "hash_matches": observed_hash == master["sha256"],
                "output_metadata": metadata,
                "is_registered_final_linear_m8_output": bool(
                    metadata is not None
                    and metadata["dtype"] == "uint16"
                    and "For viewing" not in description
                    and "sRGB" not in description
                ),
            }
        )
    payload = {
        "registered_at": manifest["registered_at"],
        "selection_rule": manifest["selection_rule"],
        "checker": str((ROOT / "checker.py").resolve()),
        "checker_sha256": sha256(ROOT / "checker.py"),
        "comparators": rows,
        "strehl_display_masters": strehl_rows,
        "admissible_ids": [
            row["id"] for row in rows if row["admissible_exact_m8_o"]
        ],
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
