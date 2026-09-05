"""Independent result adjudication for the frozen M189 synthetic commission."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESULT = HERE / "out" / "commission.json"
SOURCE_NAMES = (
    "PREREGISTRATION.md",
    "metric.py",
    "commission.py",
    "verify.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def adjudicate(data: dict[str, object]) -> dict[str, bool]:
    measurements = data["measurements"]
    ratios = data["score_ratios"]
    raw = data["raw_coherent_ratios"]
    assert isinstance(measurements, dict)
    assert isinstance(ratios, dict)
    assert isinstance(raw, dict)

    gain = {
        name: float(record["weighted_noise_gain"])
        for name, record in measurements.items()
    }
    return {
        "P0_identity": abs(float(ratios["identity"]) - 1.0) <= 1e-12,
        "P1_improvement": float(ratios["optical_improved"]) > 1.05,
        "P2_optical_degradation": float(ratios["optical_degraded"]) < 0.95,
        "P3_post_blur": float(ratios["post_blur"]) < 0.95,
        "P4_post_usm": 0.98 <= float(ratios["post_usm"]) <= 1.01,
        "P5_usm_intervention": (
            float(raw["post_usm"]) > 1.05 and gain["post_usm"] > 1.05
        ),
        "P6_optical_noise_null": all(
            0.97 <= gain[name] <= 1.03
            for name in ("base", "optical_improved", "optical_degraded")
        ),
        "P7_adaptive_attack": (
            float(ratios["adaptive_renoise_usm"]) > 1.05
            and 0.97 <= gain["adaptive_renoise_usm"] <= 1.03
        ),
        "P8_flat_specificity": (
            float(measurements["flat"]["score"])
            < float(measurements["base"]["score"])
        ),
    }


def source_check(data: dict[str, object]) -> bool:
    recorded = data["source"]["sha256"]
    return all(sha256(HERE / name) == recorded[name] for name in SOURCE_NAMES)


def self_test(data: dict[str, object]) -> list[str]:
    mutations = {
        "P0_identity": ("score_ratios", "identity", 1.1),
        "P1_improvement": ("score_ratios", "optical_improved", 1.0),
        "P2_optical_degradation": ("score_ratios", "optical_degraded", 1.0),
        "P3_post_blur": ("score_ratios", "post_blur", 1.0),
        "P4_post_usm": ("score_ratios", "post_usm", 1.02),
        "P7_adaptive_attack": ("score_ratios", "adaptive_renoise_usm", 1.0),
    }
    failures = []
    for predicate, (section, key, value) in mutations.items():
        mutated = copy.deepcopy(data)
        mutated[section][key] = value
        if adjudicate(mutated)[predicate]:
            failures.append(predicate)

    mutated = copy.deepcopy(data)
    mutated["raw_coherent_ratios"]["post_usm"] = 1.0
    if adjudicate(mutated)["P5_usm_intervention"]:
        failures.append("P5_usm_intervention")

    mutated = copy.deepcopy(data)
    for name in ("base", "optical_improved", "optical_degraded"):
        mutated["measurements"][name]["weighted_noise_gain"] = 1.10
    if adjudicate(mutated)["P6_optical_noise_null"]:
        failures.append("P6_optical_noise_null")

    mutated = copy.deepcopy(data)
    mutated["measurements"]["flat"]["score"] = mutated["measurements"]["base"]["score"]
    if adjudicate(mutated)["P8_flat_specificity"]:
        failures.append("P8_flat_specificity")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    data = json.loads(RESULT.read_text(encoding="utf-8"))
    predicates = adjudicate(data)
    source_ok = source_check(data)
    for name, passed in predicates.items():
        print(f"{name}: {'GREEN' if passed else 'RED'}")
    print(f"SOURCE_HASHES: {'GREEN' if source_ok else 'RED'}")

    self_test_failures = self_test(data) if args.self_test else []
    if args.self_test:
        print(
            "CHECKER_SELF_TEST: "
            + ("GREEN" if not self_test_failures else "RED")
        )
        if self_test_failures:
            print("missed_mutations=" + ",".join(self_test_failures))

    required = all(predicates.values()) and source_ok and not self_test_failures
    print("VERDICT: " + ("GREEN" if required else "RED"))
    return 0 if required else 1


if __name__ == "__main__":
    raise SystemExit(main())
