from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAND2_SRC = REPO / "experiments" / "M-CAND2" / "src"
sys.path.insert(0, str(CAND2_SRC))

import cand2 as core  # noqa: E402


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    metadata = read_json(HERE / "capture-metadata-audit.json")
    focus = read_json(HERE / "focus-coverage-audit.json")
    m55 = read_json(HERE / "m55-audit.json")
    downstream = read_json(
        REPO
        / "experiments"
        / "M-CAND2"
        / "out"
        / "amendment-downstream-gate.json"
    )

    sw4_focus = focus["stacks"]["tilted-sw4"]
    sw10_focus = focus["stacks"]["tilted-sw10"]
    coverage_count = min(
        sw4_focus["both_metrics_qualifying_sites"]["1.05"],
        sw10_focus["both_metrics_qualifying_sites"]["1.05"],
    )
    tail_peaks = {
        stack: {
            metric: focus["stacks"][stack][metric]["peaks_in_tail_bucket"]
            for metric in ("tenengrad", "laplacian")
        }
        for stack in ("tilted-sw4", "tilted-sw10")
    }
    record = {
        "protocol": "M131-capture-admissibility-v1",
        "candidate_2_registered_structure": {
            "observation_set_fields": [
                field.name for field in dataclasses.fields(core.ObservationSet)
            ],
            "dimension": core.DIMENSION,
            "templates": core.TEMPLATE_COUNT,
            "folds": 5,
            "sites_per_block": 96,
            "covariance_train_count_per_fold": 384,
            "target_band": [core.TASK_BAND_LOW, core.TASK_BAND_HIGH],
            "target_amplitude": core.SIGNAL_AMPLITUDE,
        },
        "gates": {
            "task_and_streams": {
                "passed": False,
                "candidate_requires": [
                    "the same predeclared physical plus/minus target task under each system",
                    "independent zero-target covariance observations",
                    "separate derivative plus/minus observations",
                    "separate held-out plus/minus observations",
                    "five acquisition blocks with 96 paired sites each",
                ],
                "capture_supplies": [
                    "one 182-frame dense sweep of one natural target state",
                    "one 92-frame sparse sweep of the same natural target state",
                    "three flat exposure stacks, but no matched target alternatives",
                ],
                "reason": (
                    "Dense and sparse are acquisition systems, not the target "
                    "classes. Relabelling them plus/minus is exactly "
                    "label-swap invariant in d-prime squared and measures "
                    "capture distinguishability."
                ),
                "m55_class_swap_exact": m55["class_swap_test"][
                    "exact_at_float_precision"
                ],
            },
            "image_coverage": {
                "passed": coverage_count == 64,
                "required_sites": 64,
                "qualifying_sites_in_both_stacks_and_metrics_at_1p05": (
                    coverage_count
                ),
                "sw4": sw4_focus["both_metrics_qualifying_sites"],
                "sw10": sw10_focus["both_metrics_qualifying_sites"],
                "reason": (
                    "One fixed grid site peaks at the opening boundary; a "
                    "64-interior-peak claim is not available."
                ),
            },
            "tail": {
                "passed_for_observed_grid_coverage": all(
                    value == 0
                    for stack in tail_peaks.values()
                    for value in stack.values()
                ),
                "tail_peaks": tail_peaks,
                "focus_bucket_ratio": metadata[
                    "tilted_sw4_over_sw10_focus_bucket_ratios"
                ],
                "observed_direction": (
                    "No qualified grid site peaks in either final EXIF bucket, "
                    "so the 26/14 mismatch has no observed route to create a "
                    "dense advantage in this input-only coverage audit."
                ),
                "failure_direction": (
                    "If a task peak did lie in the unmatched tail, the dense "
                    "arm's relative two-frame deficit would omit dense "
                    "samples and bias it downward. Different physical "
                    "endpoints would make the sign indeterminate."
                ),
            },
            "ibis_and_geometry": {
                "passed": False,
                "all_six_stacks_ibis_on": metadata["checks"][
                    "all_six_stacks_ibis_on"
                ],
                "image_motion": {
                    "sw4_increment_rms_raw_px": sw4_focus[
                        "phase_correlation"
                    ]["increment_raw_px"]["rms"],
                    "sw10_increment_rms_raw_px": sw10_focus[
                        "phase_correlation"
                    ]["increment_raw_px"]["rms"],
                    "sw4_detrended_rms_raw_px": sw4_focus[
                        "phase_correlation"
                    ]["detrended_residual_raw_px"]["rms"],
                    "sw10_detrended_rms_raw_px": sw10_focus[
                        "phase_correlation"
                    ]["detrended_residual_raw_px"]["rms"],
                },
                "existing_product_map_evidence": {
                    "source": "docs/research/cover-default.md:590-599",
                    "sw4_heldout_error_px": 8.66210205971497,
                    "sw10_heldout_error_px": 12.095237912344203,
                    "product_usability_limit_px": 4.0,
                    "sw4_full_k": 0.9676287511847108,
                    "sw4_92_subset_k": 0.9676287511847108,
                    "sw10_k": 0.9652763795078986,
                    "subset_vs_independent_k_difference": (
                        0.002352371676812237
                    ),
                    "registered_difference_limit": 0.001,
                },
                "reason": (
                    "The two sweeps have independent sensor-motion histories "
                    "and fail the existing input-only product geometry gate. "
                    "A scored-detail warp would leak the outcome."
                ),
            },
        },
        "historical_candidate_state": {
            "candidate_status": downstream["candidate_status"],
            "eligible_for_downstream_arms": downstream["eligible"],
            "mandatory_classifications": downstream[
                "mandatory_classifications"
            ],
        },
        "overall": {
            "verdict": "UNCOMMISSIONED_NO_LAWFUL_TARGET_TASK",
            "clears_blocker_a": False,
            "reason": (
                "The exact Candidate 2 estimand cannot be instantiated, the "
                "64-site coverage claim fails 63/64, and cross-capture "
                "IBIS/geometry is confounded."
            ),
        },
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"task={record['gates']['task_and_streams']['passed']} "
        f"coverage={coverage_count}/64 "
        f"tail={record['gates']['tail']['passed_for_observed_grid_coverage']} "
        f"geometry={record['gates']['ibis_and_geometry']['passed']}"
    )
    return 0 if record["overall"]["clears_blocker_a"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "capture-admissibility.json",
    )
    args = parser.parse_args()
    return run(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
