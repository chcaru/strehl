"""Assemble and validate M82's matched bee ISO-pair decision artifact."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import scipy

import m82lib as M


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    pre_path = M.HERE / "bee-iso-preconditions.json"
    admission_path = M.HERE / "bee-iso-admission.json"
    bee_path = M.HERE / "bee-results.json"
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    bee = json.loads(bee_path.read_text(encoding="utf-8"))
    mutation_log = (M.HERE / "mutation-control-iso.log").read_text(encoding="utf-8")

    require(not pre["pair_exif"]["exif_precondition_pass"], "EXIF unexpectedly passed")
    require(
        not pre["framing"]["framing_precondition_pass"],
        "framing unexpectedly passed",
    )
    require(
        pre["profile_audit"]["classification"] == "MEASUREMENT-BACKED",
        "profile classification changed",
    )
    require(
        admission["provenance"]["preconditions_sha256"] == sha256(pre_path),
        "admission used a different precondition artifact",
    )
    require(
        admission["provenance"]["source_sha256"]
        == sha256(M.HERE / "bee_iso_admission.py"),
        "admission source changed after measurement",
    )
    require(admission["status"] == "NOT ESTABLISHED", "admission status changed")
    require(
        not admission["bars"]["0.70"]["capable"],
        "map instrument unexpectedly passed capability",
    )
    require(
        not admission["map_mutation_control"]["pass"],
        "map permutation unexpectedly passed its registered power rule",
    )
    require("PLANTED_READBACK=True" in mutation_log, "source mutation not read back")
    require("EXIT=1" in mutation_log, "source mutation did not fail self-test")
    require("RESTORED=True" in mutation_log, "source mutation was not restored")
    for stack in ("bee-2", "bee-3"):
        row = bee["stacks"][stack]["targets"]["0.70"]
        require(not row["price_readable"], f"{stack} price unexpectedly readable")
        require(not row["m80_readable"], f"{stack} M80 unexpectedly readable")
        require(
            not bee["stacks"][stack]["flat_precondition_pass"],
            f"{stack} flat precondition unexpectedly passed",
        )

    cross = admission["comparisons"]["0.70"]["cross_iso_full"]
    within2 = admission["comparisons"]["0.70"]["within_bee2_even_odd"]
    within3 = admission["comparisons"]["0.70"]["within_bee3_even_odd"]
    pair = pre["pair_exif"]
    framing = pre["framing"]["real"]
    profile = pre["profile_audit"]
    result = {
        "verdict": "NO SHIP / NOT ESTABLISHED",
        "iso_pair": {
            "premise": "NOT ESTABLISHED",
            "exif": {
                "status": "FAIL",
                "equal_focus_rows": pair["focus_sequence_equal_rows"],
                "total_rows": 299,
                "equal_focus_fraction": pair["focus_sequence_equal_fraction"],
                "maximum_focus_tag_difference_m": pair[
                    "focus_max_absolute_difference_m"
                ],
                "exposure_rows_outside_1pct": pair[
                    "iso_exposure_rows_outside_1pct"
                ],
                "maximum_iso_exposure_difference": pair[
                    "iso_exposure_max_relative_difference"
                ],
            },
            "framing": {
                "status": "NOT ESTABLISHED",
                "shift_green_px": framing[
                    "shift_green_px_to_apply_to_bee3"
                ],
                "raw_pearson": framing["raw_pearson"],
                "highpass_pearson": framing["highpass_pearson"],
                "affine_residual_over_sd": framing[
                    "affine_residual_over_reference_sd"
                ],
                "within_frame_green_sanity": framing[
                    "green_plane_sanity_highpass_pearson"
                ],
                "destructive_control_pass": pre["framing"][
                    "destructive_control"
                ]["pass"],
            },
        },
        "noise_profile": {
            "status": "MEASUREMENT-BACKED SCALARS, NOT EXACT PER-ISO ROWS",
            "maximum_scalar_relative_error": profile[
                "maximum_scalar_relative_error"
            ],
            "pair_gain_ratio_relative_error": profile[
                "pair_ratio_relative_error"
            ],
            "known_omissions": profile["known_omissions"],
            "stale_profile_comment": profile["stale_profile_comment"],
        },
        "admission_map": {
            "status": "NOT ESTABLISHED — INSTRUMENT INCAPABLE",
            "cross_iso": cross,
            "within_bee2": within2,
            "within_bee3": within3,
            "registered_bar": admission["bars"]["0.70"],
            "source_mutation_control": "PASS",
            "map_permutation_control": (
                "FAIL — real map had only "
                f"{admission['map_mutation_control']['spearman_drop']:.6f} "
                "Spearman headroom against the permutation, below 0.20"
            ),
        },
        "sharpness_price": {
            "status": "NOT ESTABLISHED",
            "bee-2": {
                "px": bee["stacks"]["bee-2"]["targets"]["0.70"]["dsig"]["px"],
                "corrected_se_px": bee["stacks"]["bee-2"]["targets"]["0.70"][
                    "dsig"
                ]["corrected_se_px"],
                "flat_precondition": "FAIL",
                "m80": "NO TARGET",
                "readable": False,
            },
            "bee-3": {
                "px": bee["stacks"]["bee-3"]["targets"]["0.70"]["dsig"]["px"],
                "corrected_se_px": bee["stacks"]["bee-3"]["targets"]["0.70"][
                    "dsig"
                ]["corrected_se_px"],
                "flat_precondition": "FAIL",
                "m80": "NO TARGET",
                "readable": False,
            },
        },
        "interpretation": {
            "raw_gate_equality_required": False,
            "why": (
                "The reported sigma-gain coordinate is mean(1/sqrt(n_eff)); "
                "absolute sensor sigma cancels after admission, while the focus "
                "field is divided by sigma before admission. Matched lower-noise "
                "content should therefore need a larger raw gate."
            ),
            "noise_model_failure_established": False,
            "portable_price_established": False,
            "top_level_verdict_changed": False,
        },
        "controls": {
            "exiftool_stderr_empty": all(
                all(size == 0 for size in pre["exif"][stack]["stderr_bytes"].values())
                for stack in ("bee-1", "bee-2", "bee-3")
            ),
            "framing_tile_mutation": pre["framing"]["destructive_control"]["pass"],
            "admission_source_byte_mutation": True,
            "admission_map_tile_mutation": admission["map_mutation_control"]["pass"],
        },
        "candidate_facts": [
            {
                "label": "MEASURED",
                "claim": (
                    "The full EXIF census confirms 299 frames, fixed ISO/f/5.6, "
                    "and nine focus tags in each pair member, but only 265/299 "
                    "filename-paired focus tags agree and 151/299 ISO×exposure "
                    "rows differ by more than 1% (maximum 20%)."
                ),
                "evidence": "bee-iso-preconditions.json",
            },
            {
                "label": "MEASURED",
                "claim": (
                    "First-frame gross registration selects zero translation "
                    "and raw r=0.989985, but the frozen fine-structure bar fails "
                    "(r=0.238946); its within-frame green sanity control also "
                    "fails, so identical fine content is not established."
                ),
                "evidence": "bee-iso-preconditions.json",
            },
            {
                "label": "MEASURED/DERIVED",
                "claim": (
                    "The shipped ISO-100/400 scalar profile is backed by direct "
                    "measurements within 5.32%, and M61's matched-pair gain ratio "
                    "is 1.22% from the ISO ratio, but the profile is a relation "
                    "plus mode fits rather than exact per-ISO rows."
                ),
                "evidence": "bee-iso-preconditions.json; M48; M61; M71",
            },
            {
                "label": "MEASURED",
                "claim": (
                    "The primary admission maps are not a capable spatial "
                    "co-location instrument: within-stack even/odd Spearman is "
                    f"{within2['spearman_log1p']:.4f}/{within3['spearman_log1p']:.4f}, "
                    f"cross-ISO is {cross['spearman_log1p']:.4f}, and the planted "
                    "tile permutation cannot produce the registered 0.20 drop."
                ),
                "evidence": "bee-iso-admission.json",
            },
            {
                "label": "DERIVED",
                "claim": (
                    "The ISO-pair arm cannot establish either a noise-model "
                    "failure or a portable sharpness price; M82 remains "
                    "NO SHIP / NOT ESTABLISHED."
                ),
                "evidence": (
                    "bee-iso-preconditions.json; bee-iso-admission.json; "
                    "bee-results.json"
                ),
            },
        ],
        "provenance": {
            "preregistration_commit": "1a388a383f158806da6af7a740cb88ac5d627eb7",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "files": {
                path.name: sha256(path)
                for path in (
                    M.HERE / "PREREGISTRATION-BEE-ISO.md",
                    M.HERE / "analyse_bee_iso_pair.py",
                    M.HERE / "bee_iso_admission.py",
                    M.HERE / "mutation_control_iso.py",
                    M.HERE / "mutation-control-iso.log",
                    pre_path,
                    admission_path,
                    bee_path,
                )
            },
        },
    }
    output = M.HERE / "bee-iso-results.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['verdict']}; pair={result['iso_pair']['premise']}; "
        f"maps={result['admission_map']['status']}"
    )


if __name__ == "__main__":
    main()
