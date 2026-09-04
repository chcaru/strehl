from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAND2_SRC = REPO / "experiments" / "M-CAND2" / "src"
sys.path.insert(0, str(CAND2_SRC))

import cand2 as core  # noqa: E402
import cand2_v2 as display  # noqa: E402


SOURCE_DIR = Path(
    r"C:\Users\chris\.copilot\session-state"
    r"\841ddf83-8ef0-40bd-a341-d2c66d487731"
    r"\files\cand2-postmortem-optics"
)
SOURCES = {
    "degraded": {
        "path": SOURCE_DIR / "degraded-scores.npz",
        "sha256": "8c45a6b0563ae20006ed6c7b49c64d3d8296d0f630fadca5e9e96f3439e61824",
    },
    "improved": {
        "path": SOURCE_DIR / "improved-scores.npz",
        "sha256": "2b5170d8c3332ec9ea4d79ecb1b899d4c68d43135d108fcce6f11e45a68c7ec4",
    },
}
PINNED_TASK_SEED = display.PINNED_TEMPLATE_SEED
NULL_REPEATS = 8
EXPECTED_BASE_D2 = 6.0122885561019395
BASE_TOLERANCE = 1.0e-12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(
    plus: np.ndarray,
    minus: np.ndarray,
    indices: np.ndarray | None = None,
) -> tuple[float, np.ndarray]:
    if indices is not None:
        plus = plus[:, indices]
        minus = minus[:, indices]
    difference = plus.mean(axis=1) - minus.mean(axis=1)
    variance = 0.5 * (
        plus.var(axis=1, ddof=1) + minus.var(axis=1, ddof=1)
    )
    if np.any(variance <= 0.0):
        raise RuntimeError("non-positive held-out variance")
    by_task = difference * difference / variance
    return float(by_task.mean()), by_task


def ratio_for(
    base_plus: np.ndarray,
    base_minus: np.ndarray,
    arm_plus: np.ndarray,
    arm_minus: np.ndarray,
    indices: np.ndarray | None = None,
) -> tuple[float, np.ndarray, np.ndarray]:
    base, base_tasks = score(base_plus, base_minus, indices)
    arm, arm_tasks = score(arm_plus, arm_minus, indices)
    return arm / base, base_tasks, arm_tasks


def jackknife(values: list[float]) -> dict:
    array = np.asarray(values, dtype=np.float64)
    mean = float(array.mean())
    se = math.sqrt(
        (len(array) - 1)
        / len(array)
        * float(np.sum((array - mean) ** 2))
    )
    return {
        "leave_one_block_out": array.tolist(),
        "mean": mean,
        "standard_error": se,
        "normal_ci95": [mean - 1.96 * se, mean + 1.96 * se],
    }


def summarize_variant(
    arm: str,
    variant: str,
    source: dict[str, np.ndarray],
) -> dict:
    base_plus = source[f"{variant}_base_plus"]
    base_minus = source[f"{variant}_base_minus"]
    arm_plus = source[f"{variant}_arm_plus"]
    arm_minus = source[f"{variant}_arm_minus"]
    blocks = source["blocks"]
    macros = source["macros"]
    ratio, base_tasks, arm_tasks = ratio_for(
        base_plus,
        base_minus,
        arm_plus,
        arm_minus,
    )
    task_ratios = arm_tasks / base_tasks
    leave_one = []
    for block in sorted(set(int(value) for value in blocks)):
        indices = np.flatnonzero(blocks != block)
        leave_one.append(
            ratio_for(
                base_plus,
                base_minus,
                arm_plus,
                arm_minus,
                indices,
            )[0]
        )
    macro_subsets = {}
    for label, mask in {
        "even_macros": macros % 2 == 0,
        "odd_macros": macros % 2 == 1,
        "first_half_macros": macros < 48,
        "second_half_macros": macros >= 48,
    }.items():
        macro_subsets[label] = ratio_for(
            base_plus,
            base_minus,
            arm_plus,
            arm_minus,
            np.flatnonzero(mask),
        )[0]
    direction_pass = (
        max(task_ratios) < 1.0
        if arm == "degraded"
        else min(task_ratios) > 1.0
    )
    return {
        "frozen_ratio_of_task_means": ratio,
        "base_d2_by_task": base_tasks.tolist(),
        "arm_d2_by_task": arm_tasks.tolist(),
        "arm_over_base_by_task": task_ratios.tolist(),
        "task_ratio_aggregations": {
            "arithmetic_mean": float(task_ratios.mean()),
            "median": float(np.median(task_ratios)),
            "minimum": float(task_ratios.min()),
            "maximum": float(task_ratios.max()),
            "strict_all_tasks_direction_pass": bool(direction_pass),
        },
        "block_jackknife": jackknife(leave_one),
        "balanced_macro_subsets": macro_subsets,
        "all_subset_directions_pass": bool(
            all(value < 1.0 for value in macro_subsets.values())
            if arm == "degraded"
            else all(value > 1.0 for value in macro_subsets.values())
        ),
    }


def load_sources() -> dict[str, dict[str, np.ndarray]]:
    loaded = {}
    for arm, record in SOURCES.items():
        observed = sha256(record["path"])
        if observed != record["sha256"]:
            raise RuntimeError(f"{arm} score artifact hash changed: {observed}")
        with np.load(record["path"]) as data:
            loaded[arm] = {name: data[name].copy() for name in data.files}
    for key in (
        "native_base_plus",
        "native_base_minus",
        "display_base_plus",
        "display_base_minus",
        "blocks",
        "macros",
    ):
        if not np.array_equal(loaded["degraded"][key], loaded["improved"][key]):
            raise RuntimeError(f"base arrays differ between source arms: {key}")
    return loaded


def null_audit() -> dict:
    backgrounds, inputs = core.load_backgrounds()
    base_data = core.make_observations(backgrounds, PINNED_TASK_SEED, "base")
    base = core.crossfit(base_data, "M131-null-base")
    if base.status != "NUMERIC" or base.d2 is None:
        raise RuntimeError(f"baseline refused: {base.refusal}")
    if not math.isclose(
        base.d2,
        EXPECTED_BASE_D2,
        rel_tol=BASE_TOLERANCE,
        abs_tol=BASE_TOLERANCE,
    ):
        raise RuntimeError(
            f"baseline changed: {base.d2} versus {EXPECTED_BASE_D2}"
        )
    ratios = []
    d2s = []
    for index in range(NULL_REPEATS):
        arm_name = f"M131-independent-null-{index}"
        data = core.make_observations(
            backgrounds,
            PINNED_TASK_SEED,
            arm_name,
        )
        result = core.crossfit(data, arm_name)
        if result.status != "NUMERIC" or result.d2 is None:
            raise RuntimeError(f"null {index} refused: {result.refusal}")
        ratios.append(result.d2 / base.d2)
        d2s.append(result.d2)
    array = np.asarray(ratios, dtype=np.float64)
    return {
        "input_manifest_sha256": inputs["manifest_sha256"],
        "base_d2": base.d2,
        "independent_null_d2": d2s,
        "ratios": ratios,
        "ratio_mean": float(array.mean()),
        "ratio_standard_deviation": float(array.std(ddof=1)),
        "ratio_standard_error": float(
            array.std(ddof=1) / math.sqrt(len(array))
        ),
        "ratio_minimum": float(array.min()),
        "ratio_maximum": float(array.max()),
        "n": len(array),
    }


def self_test(loaded: dict[str, dict[str, np.ndarray]]) -> dict:
    source = loaded["degraded"]
    ratio, _, _ = ratio_for(
        source["native_base_plus"],
        source["native_base_minus"],
        source["native_base_plus"],
        source["native_base_minus"],
    )
    blur_gate_rejects_exact_copy = not ratio < 1.0
    improvement_gate_rejects_exact_copy = not ratio > 1.0
    wrong_arm_ratio, _, _ = ratio_for(
        source["native_base_plus"],
        source["native_base_minus"],
        loaded["improved"]["native_arm_plus"],
        loaded["improved"]["native_arm_minus"],
    )
    blur_gate_rejects_improvement = not wrong_arm_ratio < 1.0
    return {
        "exact_copy_ratio": ratio,
        "blur_gate_rejects_exact_copy": blur_gate_rejects_exact_copy,
        "improvement_gate_rejects_exact_copy": (
            improvement_gate_rejects_exact_copy
        ),
        "improvement_mislabeled_as_blur_ratio": wrong_arm_ratio,
        "blur_gate_rejects_improvement": blur_gate_rejects_improvement,
        "passed": bool(
            blur_gate_rejects_exact_copy
            and improvement_gate_rejects_exact_copy
            and blur_gate_rejects_improvement
        ),
    }


def run(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    core.configure_threads()
    loaded = load_sources()
    variants = {
        arm: {
            variant: summarize_variant(arm, variant, loaded[arm])
            for variant in ("native", "display")
        }
        for arm in ("degraded", "improved")
    }
    null = null_audit()
    test = self_test(loaded)
    all_choices_pass = all(
        variants[arm][variant]["task_ratio_aggregations"][
            "strict_all_tasks_direction_pass"
        ]
        and variants[arm][variant]["all_subset_directions_pass"]
        and (
            variants[arm][variant]["block_jackknife"]["normal_ci95"][1] < 1.0
            if arm == "degraded"
            else variants[arm][variant]["block_jackknife"]["normal_ci95"][0]
            > 1.0
        )
        for arm in ("degraded", "improved")
        for variant in ("native", "display")
    )
    record = {
        "protocol": "M131-synthetic-choice-audit-v1",
        "source_artifacts": {
            arm: {
                "path": str(record["path"]),
                "sha256": record["sha256"],
            }
            for arm, record in SOURCES.items()
        },
        "variants": variants,
        "independent_same_optics_null": null,
        "planted_failure_self_test": test,
        "all_registered_choice_directions_pass": all_choices_pass,
        "interpretation": (
            "The synthetic optical sign is robust within this supplied-target "
            "forward model. This does not establish natural-capture task "
            "admissibility or transfer."
        ),
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"choices={all_choices_pass} "
        f"null={null['ratio_mean']:.6f}+/-"
        f"{null['ratio_standard_error']:.6f} "
        f"self_test={test['passed']}"
    )
    return 0 if all_choices_pass and test["passed"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "synthetic-choice-audit.json",
    )
    args = parser.parse_args()
    return run(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
