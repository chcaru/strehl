"""Reduce M81's fresh common-target ladders into corrected-unit constants."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STACKS = (
    "wrapped-text-1",
    "wrapped-text-2",
    "109MSDCF",
    "coffee-bean",
    "foam",
    "bee-1",
)
FIVE = ("wrapped-text-1", "109MSDCF", "coffee-bean", "foam", "bee-1")
SIBLINGS = ("wrapped-text-1", "wrapped-text-2")
TARGET = 4.0
PORTABILITY_BAR = 2.0
EXPECTED_GATES = (
    0.0,
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
    16.0,
    24.0,
    32.0,
    40.0,
    48.0,
    64.0,
    96.0,
    128.0,
)
EXPECTED_N = {
    "wrapped-text-1": 130,
    "wrapped-text-2": 120,
    "109MSDCF": 22,
    "coffee-bean": 105,
    "foam": 100,
    "bee-1": 299,
}

GATE_ROW = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)%"
    r"\s+([-+0-9.]+)%\s+([-+0-9.]+)x$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field(lines: list[str], name: str) -> str:
    prefix = name + "="
    values = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    if len(values) != 1:
        raise RuntimeError(f"{name}: expected one value, found {len(values)}")
    return values[0]


def parse_ladder(path: Path, stack: str, binary: dict) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if field(lines, "STACK") != stack:
        raise RuntimeError(f"{path.name}: stack header differs")
    if field(lines, "commit") != binary["commit"]:
        raise RuntimeError(f"{path.name}: binary commit differs")
    if field(lines, "sha256") != binary["sha256"]:
        raise RuntimeError(f"{path.name}: binary hash differs")
    if field(lines, "exit") != "0":
        raise RuntimeError(f"{path.name}: process did not exit zero")
    frames = next(
        int(line.split(":", 1)[1].split()[0])
        for line in lines
        if line.startswith("frames")
    )
    if frames != EXPECTED_N[stack]:
        raise RuntimeError(f"{path.name}: expected N={EXPECTED_N[stack]}, got {frames}")
    start = next(i for i, line in enumerate(lines) if "mean n_eff" in line)
    rows = []
    for line in lines[start + 1 :]:
        match = GATE_ROW.match(line)
        if match:
            rows.append(
                {
                    "gate": float(match.group(1)),
                    "mean_n_eff": float(match.group(3)),
                    "singleton_percent": float(match.group(4)),
                    "boundary_percent": float(match.group(5)),
                    "predicted_sigma_gain": float(match.group(6)),
                }
            )
        elif rows and not line.strip():
            break
    if len(rows) != 15:
        raise RuntimeError(f"{path.name}: expected 15 ladder rows, got {len(rows)}")
    if tuple(row["gate"] for row in rows) != EXPECTED_GATES:
        raise RuntimeError(f"{path.name}: ladder differs from pre-registration")
    return rows


def solve_gate(ladder: list[dict], target: float) -> dict:
    values = [(row["gate"], row["mean_n_eff"]) for row in ladder]
    monotone = all(b[1] >= a[1] for a, b in zip(values, values[1:]))
    if not monotone:
        raise RuntimeError("n_eff ladder is not non-decreasing")
    positive = [row for row in ladder if row["gate"] > 0.0]
    for lo, hi in zip(positive, positive[1:]):
        n0, n1 = lo["mean_n_eff"], hi["mean_n_eff"]
        if n0 <= target <= n1:
            if n1 == n0:
                gate = lo["gate"]
            else:
                fraction = math.log(target / n0) / math.log(n1 / n0)
                gate = math.exp(
                    math.log(lo["gate"])
                    + fraction * math.log(hi["gate"] / lo["gate"])
                )
            reconstructed = math.exp(
                math.log(n0)
                + math.log(gate / lo["gate"])
                / math.log(hi["gate"] / lo["gate"])
                * math.log(n1 / n0)
            )
            return {
                "gate": gate,
                "bracket": [lo, hi],
                "reconstructed_n_eff": reconstructed,
                "relative_error": abs(reconstructed - target) / target,
            }
    raise RuntimeError(f"target {target} is not bracketed")


def corrected_constant(raw_gate: float, rho: float) -> float:
    return raw_gate / rho


def span(values: list[float]) -> float:
    return max(values) / min(values)


def self_tests() -> None:
    print("UNIT_TEST_COUNT=2")
    plant = [
        {"gate": 1.0, "mean_n_eff": 2.0},
        {"gate": 4.0, "mean_n_eff": 4.0},
        {"gate": 16.0, "mean_n_eff": 8.0},
    ]
    solved = solve_gate(plant, 5.0)["gate"]
    assert abs(solved / 6.25 - 1.0) <= 0.001, solved
    constants = [
        corrected_constant(raw, rho)
        for raw, rho in zip((2.0, 4.0, 8.0), (0.5, 1.0, 2.0), strict=True)
    ]
    assert span(constants) <= 1.0 + 1e-12, constants
    print("UNIT_SELF_TESTS=2/2 PASS")


def source_rhos() -> dict[str, dict[str, float]]:
    b3 = json.loads(
        (
            REPO
            / "experiments"
            / "M69-focus-noise-sd"
            / "out"
            / "97-b-fine-field.json"
        ).read_text(encoding="utf-8")
    )
    p2 = json.loads(
        (
            REPO
            / "experiments"
            / "M69-focus-noise-sd"
            / "out"
            / "80-corpus-rho.json"
        ).read_text(encoding="utf-8")
    )
    return {
        stack: {
            "m69_b3": float(b3["b3"][stack]["coarse"]["rho_true"]),
            "m69_p2": float(p2[stack]["rho_true"]),
        }
        for stack in STACKS
    }


def estimator_result(
    name: str, solved: dict[str, dict], rhos: dict[str, float]
) -> dict:
    constants = {
        stack: corrected_constant(solved[stack]["gate"], rhos[stack])
        for stack in STACKS
    }
    sibling_span = span([constants[stack] for stack in SIBLINGS])
    five_span = span([constants[stack] for stack in FIVE])
    all_span = span(list(constants.values()))
    return {
        "name": name,
        "rho": rhos,
        "corrected_constant": constants,
        "spans": {
            "wrapped_text_siblings": sibling_span,
            "five_m77_stacks": five_span,
            "all_six": all_span,
        },
        "U1_sibling_pass": sibling_span <= PORTABILITY_BAR,
        "U2_five_stack_pass": five_span <= PORTABILITY_BAR,
    }


def main() -> None:
    self_tests()
    if "--self-test-only" in sys.argv:
        return
    calibration = json.loads(
        (HERE / "unit-calibration.json").read_text(encoding="utf-8")
    )
    binary = json.loads((HERE / "unit-binary.json").read_text(encoding="utf-8"))
    for name, relative in (
        ("m69_b3", "experiments/M69-focus-noise-sd/out/97-b-fine-field.json"),
        ("m69_p2", "experiments/M69-focus-noise-sd/out/80-corpus-rho.json"),
    ):
        if calibration["source_hashes"][name] != sha256(REPO / relative):
            raise RuntimeError(f"{name}: source evidence hash changed")
    for stack in STACKS:
        artifact = REPO / calibration["stacks"][stack]["m70_artifact"]
        if calibration["stacks"][stack]["m70_sha256"] != sha256(artifact):
            raise RuntimeError(f"{stack}: M70 texture artifact hash changed")
    source = source_rhos()
    ladders = {}
    solved = {}
    for stack in STACKS:
        ladder = parse_ladder(HERE / f"unit-ladder-{stack}.log", stack, binary)
        ladders[stack] = ladder
        solved[stack] = solve_gate(ladder, TARGET)

    primary_rhos = {
        stack: float(calibration["stacks"][stack]["rho"]) for stack in STACKS
    }
    estimators = {
        "primary_textured_tiles": estimator_result(
            "primary_textured_tiles", solved, primary_rhos
        ),
        "m69_b3_central": estimator_result(
            "m69_b3_central",
            solved,
            {stack: source[stack]["m69_b3"] for stack in STACKS},
        ),
        "m69_p2_central": estimator_result(
            "m69_p2_central",
            solved,
            {stack: source[stack]["m69_p2"] for stack in STACKS},
        ),
    }
    primary = estimators["primary_textured_tiles"]
    primary_pair = (primary["U1_sibling_pass"], primary["U2_five_stack_pass"])
    sensitivity_reversal = any(
        (row["U1_sibling_pass"], row["U2_five_stack_pass"]) != primary_pair
        for name, row in estimators.items()
        if name != "primary_textured_tiles"
    )
    calibration_controls_pass = (
        bool(calibration["controls"]["K1b"]["met"])
        and all(
            calibration["stacks"][stack]["textured_patches"] >= 3
            and calibration["stacks"][stack]["scalar_span_pass"]
            for stack in STACKS
        )
    )
    interpolation_controls_pass = all(
        row["relative_error"] <= 0.01 for row in solved.values()
    )
    unit_pass = (
        calibration_controls_pass
        and interpolation_controls_pass
        and primary["U1_sibling_pass"]
        and primary["U2_five_stack_pass"]
        and not sensitivity_reversal
    )
    result = {
        "target_mean_n_eff": TARGET,
        "portability_bar": PORTABILITY_BAR,
        "binary": binary,
        "raw_target_gate": {stack: solved[stack]["gate"] for stack in STACKS},
        "ladders": ladders,
        "solves": solved,
        "estimators": estimators,
        "controls": {
            "calibration_controls_pass": calibration_controls_pass,
            "interpolation_controls_pass": interpolation_controls_pass,
            "sensitivity_reversal": sensitivity_reversal,
        },
        "candidate_gate": {
            stack: 4.0 * primary_rhos[stack] for stack in FIVE
        },
        "unit_hypothesis_pass": unit_pass,
        "verdict": "SURVIVES" if unit_pass else "REFUTED",
    }
    (HERE / "unit-results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    for stack in STACKS:
        print(
            f"{stack:16} T4={solved[stack]['gate']:10.6f} "
            f"rho={primary_rhos[stack]:.6f} "
            f"C={primary['corrected_constant'][stack]:10.6f}"
        )
    print(
        f"U1 sibling span={primary['spans']['wrapped_text_siblings']:.6f} "
        f"pass={primary['U1_sibling_pass']}"
    )
    print(
        f"U2 five-stack span={primary['spans']['five_m77_stacks']:.6f} "
        f"pass={primary['U2_five_stack_pass']}"
    )
    print(f"UNIT HYPOTHESIS: {result['verdict']}")


if __name__ == "__main__":
    main()
