from __future__ import annotations

import sys

import run


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    pre = run.read_json(run.OUT / "PREFLIGHT.json")
    require(pre["phase"] == "A_Q1_Q2_ONLY", "wrong registered phase")
    require(len(pre["arms"]) == 8, "eight arms were not preregistered")
    require(run.sha256(run.BINARY) == run.BINARY_SHA256, "frozen binary moved")
    require(
        run.cache_snapshot(run.PRIVATE_CACHE) == pre["private_cache"],
        "private cache moved",
    )
    require(
        run.snapshot_files(run.frozen_dependency_paths()) == pre["frozen_dependencies"],
        "frozen dependency moved",
    )

    render_path = run.OUT / "RENDER-MANIFEST.json"
    if not render_path.exists():
        require(
            not any(run.RENDERS.glob("*.tiff")),
            "render exists before the preregistered render manifest",
        )
        print("pre-render verification passed")
        return 0

    renders = run.read_json(render_path)
    require(renders["control"]["returncode"] == 0, "Scale control failed")
    require(renders["control"]["hash_matches"], "Scale control hash mismatch")
    require(renders["crop_interpretable"], "Crop was rendered but is not interpretable")
    require(len(renders["crop_records"]) == 8, "expected eight Crop records")
    for row in renders["crop_records"]:
        require(row["returncode"] == 0, f"{row['name']}: render failed")
        require(row["cache_unchanged"], f"{row['name']}: cache changed")
        require(
            row["same_solve_as_frozen_scale"]["all_match"],
            f"{row['name']}: solve/coverage mismatch",
        )
        require(row["shape_matches_crop_rect"], f"{row['name']}: Crop shape mismatch")

    q1 = run.read_json(run.OUT / "Q1-RESULTS.json")
    require(q1["commissioned_before_real_values"], "ECC was not commissioned first")
    require(q1["audit_exception"] is None, "unchanged audit_geometry.main() failed")
    require(len(q1["rows"]) == 8, "expected eight Q1 rows")
    require(q1["all_crop_geometry_clauses_pass"], "a Crop geometry clause failed")

    q2 = run.read_json(run.OUT / "Q2-GEOMETRY.json")
    require(
        q2["all_outputs_large_enough_for_common_shape"],
        "a Crop output cannot hold the common shape",
    )
    require(not q2["all_outputs_native_size"], "Crop unexpectedly emitted native size")
    require(
        q2["all_common_overlap_retained_at_least_99_percent"],
        "fixed common overlap fell below 99%",
    )
    require(q2["all_sites_survive_at_least_80_percent"], "site survival fell below 80%")
    require(
        q2["all_differential_attrition_at_most_2pp"],
        "differential attrition exceeded 2pp",
    )

    provenance = run.read_json(run.OUT / "PROVENANCE-AUDIT.json")
    require(provenance["all_read_only_guards_pass"], "read-only guard failed")
    require(
        run.protected_fingerprint() == pre["protected_paths"],
        "protected path changed after provenance audit",
    )
    print("post-render Q1/Q2 verification passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise

