"""Commission the M183 rho convention instrument before measurement."""

from __future__ import annotations

from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import uuid

import numpy as np

import analyze as A


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"


def record(name: str, passed: bool, **details) -> dict:
    return {"name": name, "status": "PASS" if passed else "FAIL", **details}


def independent_geometry(grid: int) -> dict:
    """Rational green-pair enumerator independent of analyze.alias_groups."""

    def wrap(value: Fraction) -> Fraction:
        while value < Fraction(-1, 2):
            value += 1
        while value >= Fraction(1, 2):
            value -= 1
        return value

    coords = [
        Fraction(-1, 2) + Fraction(2 * index + 1, 2 * grid)
        for index in range(grid)
    ]
    groups = set()
    ambiguous = 0
    for fy in coords:
        for fx in coords:
            partner = (wrap(fx + Fraction(1, 2)), wrap(fy + Fraction(1, 2)))
            groups.add(tuple(sorted(((fx, fy), partner))))
    for group in groups:
        bases = [
            point
            for point in group
            if abs(point[0]) + abs(point[1]) <= Fraction(1, 2)
        ]
        if len(bases) > 1:
            ambiguous += 1
    return {"groups": len(groups), "ambiguous": ambiguous}


def synthetic_lookup(module: ModuleType, rho: float, scale: float = 1.0):
    powers: dict[tuple[int, int], float] = {}
    for group in module.alias_groups():
        if group["boundary_ambiguous"]:
            for point in group["points"]:
                powers[module.point_key(point)] = 0.0
            continue
        base = group["base_candidates"][0]
        for point in group["points"]:
            powers[module.point_key(point)] = (
                scale
                if module.point_key(point) == module.point_key(base)
                else scale * rho
            )
    return lambda frequency: powers[module.point_key(frequency)]


def boundary_exchange(module: ModuleType) -> tuple[float, float]:
    powers = {}
    for group in module.alias_groups():
        for point in group["points"]:
            x, y = np.asarray(point, dtype=float)
            powers[module.point_key(point)] = float(np.exp(2.7 * x - 1.9 * y))
    before = module.rho_from_power(
        lambda frequency: powers[module.point_key(frequency)]
    )
    exchanged = dict(powers)
    for group in module.alias_groups():
        if not group["boundary_ambiguous"]:
            continue
        first, second = group["points"]
        key_a = module.point_key(first)
        key_b = module.point_key(second)
        exchanged[key_a], exchanged[key_b] = exchanged[key_b], exchanged[key_a]
    after = module.rho_from_power(
        lambda frequency: exchanged[module.point_key(frequency)]
    )
    return before, after


def base_controls(module: ModuleType) -> list[dict]:
    geometry = independent_geometry(8)
    got_groups = module.alias_groups()
    controls = [
        record(
            "C1 white null",
            math.isclose(module.rho_from_power(lambda _: 1.0), 1.0, abs_tol=1e-12),
            observed=module.rho_from_power(lambda _: 1.0),
            expected=1.0,
        ),
    ]
    planted = module.rho_from_power(synthetic_lookup(module, 0.04))
    raised = module.rho_from_power(synthetic_lookup(module, 0.08))
    lowered = module.rho_from_power(synthetic_lookup(module, 0.02))
    inert = module.rho_from_power(synthetic_lookup(module, 0.04, scale=7.0))
    controls.extend(
        [
            record(
                "C2 known rho plant",
                math.isclose(planted, 0.04, rel_tol=0.0, abs_tol=1e-12),
                observed=planted,
                expected=0.04,
            ),
            record(
                "C3 raise direction",
                raised > planted
                and math.isclose(raised / planted, 2.0, abs_tol=1e-12),
                observed=raised,
                ratio=raised / planted,
            ),
            record(
                "C4 lower direction",
                lowered < planted
                and math.isclose(lowered / planted, 0.5, abs_tol=1e-12),
                observed=lowered,
                ratio=lowered / planted,
            ),
            record(
                "C5 inert common scale",
                math.isclose(inert, planted, rel_tol=0.0, abs_tol=1e-12),
                observed=inert,
                expected=planted,
            ),
        ]
    )
    before, after = boundary_exchange(module)
    controls.append(
        record(
            "C6 boundary exchange invariance",
            math.isclose(before, after, rel_tol=0.0, abs_tol=1e-12),
            before=before,
            after=after,
        )
    )
    controls.extend(
        [
            record(
                "C7 independent geometry",
                len(got_groups) == geometry["groups"] == 32
                and sum(1 for group in got_groups if group["boundary_ambiguous"])
                == geometry["ambiguous"]
                == 8,
                instrument_groups=len(got_groups),
                instrument_ambiguous=sum(
                    1 for group in got_groups if group["boundary_ambiguous"]
                ),
                independent=geometry,
            ),
            record(
                "C8 sensor-frequency unit",
                np.allclose(
                    module.physical_frequency(np.array([0.125, -0.25])),
                    np.array([0.125, -0.25]),
                    rtol=0.0,
                    atol=1e-15,
                ),
                observed=module.physical_frequency(
                    np.array([0.125, -0.25])
                ).tolist(),
            ),
        ]
    )
    constant = module.bootstrap_scene_median([0.037] * 6)
    controls.append(
        record(
            "C9 degenerate bootstrap",
            constant["median"] == 0.037
            and constant["interval_95"] == [0.037, 0.037],
            observed=constant,
        )
    )
    synthetic_curves = []
    for index in range(20):
        bars = np.array(
            [
                0.09 if index < 2 else 0.07,
                0.09 if index < 8 else 0.07,
                0.09 if index < 16 else 0.07,
            ],
            dtype=float,
        )
        synthetic_curves.append(
            module.BarCurve(
                metadata=("synthetic", index),
                rhos=np.array([0.01, 0.1, 1.0], dtype=float),
                bars=bars,
            )
        )
    synthetic_classes = [
        module.verdict_at_rho(synthetic_curves, rho)["field centre"]["verdict"]
        for rho in (0.01, 0.1, 1.0)
    ]
    controls.append(
        record(
            "C10 verdict directions",
            synthetic_classes == ["KILL", "NARROWED", "SURVIVE"],
            observed=synthetic_classes,
        )
    )
    return controls


def replace_unique_full_line(text: str, old: str, new: str) -> str:
    """Replace exactly one complete source line or hard-error."""
    lines = text.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if line.rstrip("\r\n") == old
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"mutation anchor must match one full line, got {len(matches)}: {old!r}"
        )
    index = matches[0]
    ending = "\r\n" if lines[index].endswith("\r\n") else "\n"
    if not lines[index].endswith(("\r", "\n")):
        ending = ""
    lines[index] = new + ending
    return "".join(lines)


def load_module(path: Path) -> ModuleType:
    name = f"m183_mutant_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import mutant {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_mutant(
    source: str,
    old: str,
    new: str,
    catcher,
    temp_root: Path,
    name: str,
) -> dict:
    mutated = replace_unique_full_line(source, old, new)
    path = temp_root / f"{name}.py"
    path.write_text(mutated, encoding="utf-8")
    try:
        module = load_module(path)
        caught, details = catcher(module)
        return {
            "name": name,
            "status": "CAUGHT" if caught else "MISSED",
            "anchor": old,
            "replacement": new,
            **details,
        }
    except Exception as error:
        return {
            "name": name,
            "status": "ERROR",
            "anchor": old,
            "replacement": new,
            "exception": f"{type(error).__name__}: {error}",
        }


def main() -> int:
    controls = base_controls(A)
    source_path = HERE / "analyze.py"
    source = source_path.read_text(encoding="utf-8")

    def catch_grid(module):
        geometry = independent_geometry(8)
        return (
            len(module.alias_groups()) != geometry["groups"],
            {
                "observed_groups": len(module.alias_groups()),
                "expected_groups": geometry["groups"],
            },
        )

    def catch_scale(module):
        observed = module.physical_frequency(np.array([0.125, -0.25]))
        return (
            not np.allclose(
                observed, np.array([0.125, -0.25]), rtol=0.0, atol=1e-15
            ),
            {"observed": observed.tolist()},
        )

    def catch_boundary(module):
        before, after = boundary_exchange(module)
        return (
            not math.isclose(before, after, rel_tol=0.0, abs_tol=1e-12),
            {"before": before, "after": after},
        )

    def catch_ratio(module):
        observed = module.rho_from_power(synthetic_lookup(module, 0.04))
        return (
            not math.isclose(observed, 0.04, rel_tol=0.0, abs_tol=1e-12),
            {"observed": observed, "expected": 0.04},
        )

    with tempfile.TemporaryDirectory(prefix="m183-commission-") as temp:
        temp_root = Path(temp)
        mutants = [
            run_mutant(
                source,
                "GRID = 8",
                "GRID = 16",
                catch_grid,
                temp_root,
                "D1-grid-16",
            ),
            run_mutant(
                source,
                "FREQUENCY_SCALE = 1.0",
                "FREQUENCY_SCALE = 2.0",
                catch_scale,
                temp_root,
                "D2-native-frequency-scale",
            ),
            run_mutant(
                source,
                'BOUNDARY = "average"',
                'BOUNDARY = "primary"',
                catch_boundary,
                temp_root,
                "D3-primary-boundary-label",
            ),
            run_mutant(
                source,
                "    return alias_total / (aliases_per_group * base_total)",
                "    return (aliases_per_group * base_total) / alias_total",
                catch_ratio,
                temp_root,
                "D4-invert-ratio",
            ),
        ]

    failed = [control for control in controls if control["status"] != "PASS"]
    missed = [mutant for mutant in mutants if mutant["status"] != "CAUGHT"]
    input_hashes = {
        "scene-estimates.json": A.sha256_file(A.SCENE_ESTIMATES),
        "p1_bar.json": A.sha256_file(A.PHASE_BAR),
    }
    payload = {
        "status": "PASS" if not failed and not missed else "FAIL",
        "known_answer_tally": {
            "pass": len(controls) - len(failed),
            "fail": len(failed),
        },
        "mutation_tally": {
            "caught": len(mutants) - len(missed),
            "missed": len(missed),
        },
        "controls": controls,
        "mutants": mutants,
        "input_sha256": input_hashes,
        "instrument_sha256": A.sha256_file(source_path),
        "preregistration_commit": "014063e498a2f0a1faf627b7bb7534e3163e76cd",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "commission.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    summary = (
        f"known-answer controls: PASS {payload['known_answer_tally']['pass']} / "
        f"FAIL {payload['known_answer_tally']['fail']}\n"
        f"deliberate mutations: CAUGHT {payload['mutation_tally']['caught']} / "
        f"MISSED {payload['mutation_tally']['missed']}\n"
    )
    (OUT / "commission.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
