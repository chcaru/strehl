"""Source-bound verifier for the revised M189 research report."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = ROOT / "docs" / "research" / "M189-noise-colour-detail.md"


def read_committed_json(path: str) -> dict:
    blob = subprocess.run(
        ["git", "-C", str(ROOT), "show", "HEAD:" + path],
        check=True,
        capture_output=True,
    ).stdout
    return json.loads(blob.decode("utf-8"))


def expected_strings() -> dict[str, int]:
    v1 = read_committed_json(
        "experiments/M189-noise-colour-detail/out/v1-commission.json"
    )
    v2 = read_committed_json(
        "experiments/M189-noise-colour-detail/out/v2-commission.json"
    )
    repeat = read_committed_json(
        "experiments/M189-noise-colour-detail/out/repeat-attack-witness.json"
    )
    return {
        f"{v1['score_ratios']['optical_improved']:.9f}": 1,
        f"{v1['score_ratios']['post_usm']:.9f}": 1,
        f"{v2['score_ratios']['optical_improved']:.9f}": 3,
        f"{v2['score_ratios']['optical_degraded']:.9f}": 2,
        f"{v2['score_ratios']['post_blur']:.9f}": 2,
        f"{v2['score_ratios']['post_usm']:.9f}": 3,
        f"{v2['local_score_ratios']['optical_improved']:.9f}": 1,
        f"{v2['local_score_ratios']['post_blur']:.9f}": 1,
        f"{v2['local_score_ratios']['post_usm']:.9f}": 1,
        f"{v2['score_ratios']['adaptive_renoise_usm']:.9f}": 1,
        (
            f"{v2['measurements']['adaptive_renoise_usm']['weighted_noise_gain']:.9f}"
        ): 1,
        f"{repeat['cross_statistics']['world_g']['coherence']:.12f}": 1,
    }


def citation_errors(text: str) -> list[str]:
    pattern = re.compile(
        r"`([^`\n]+\.(?:md|html|rs)):"
        r"(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)`"
    )
    errors = []
    for path, ranges in pattern.findall(text):
        blob = subprocess.run(
            ["git", "-C", str(ROOT), "show", "HEAD:" + path],
            capture_output=True,
        )
        if blob.returncode != 0:
            errors.append(f"missing citation blob {path}")
            continue
        try:
            lines = blob.stdout.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            errors.append(f"non-UTF8 citation blob {path}")
            continue
        for item in ranges.split(","):
            if "-" in item:
                start, end = map(int, item.split("-", 1))
            else:
                start = end = int(item)
            if not 1 <= start <= end <= len(lines):
                errors.append(
                    f"citation out of range {path}:{item}, lines={len(lines)}"
                )
    return errors


def check(text: str) -> list[str]:
    errors = []
    required = (
        "**Status: INSTRUMENT VIABLE WITH DECLARED LIMITATION;",
        "**Threat ruling:** proprietary comparator re-noising is **UNKNOWN, NOT SHOWN",
        "A repeat-pair cross-statistic does **not** close the adaptive re-noise attack.",
        "This is **not yet M1 admission**",
    )
    for value in required:
        if value not in text:
            errors.append("missing conclusion: " + value)

    forbidden = (
        "No `experiments/M189-noise-colour-detail/` candidate is created.",
        "Nothing claim-bearing.",
        "No M189 candidate, holdout reading, or capture request was run.",
    )
    for value in forbidden:
        if value in text:
            errors.append("stale conclusion remains: " + value)

    for value, count in expected_strings().items():
        actual = text.count(value)
        if actual != count:
            errors.append(
                f"value occurrence mismatch {value}: expected {count}, got {actual}"
            )
    errors.extend(citation_errors(text))
    return errors


def mutation_self_test(text: str) -> list[str]:
    mutations = {
        "status": (
            "INSTRUMENT VIABLE WITH DECLARED LIMITATION",
            "NO-GO — BLIND TO REAL IMPROVEMENT",
        ),
        "positive": ("2.920107520", "1.000000000"),
        "usm": ("0.733681365", "1.733681365"),
        "threat": ("UNKNOWN, NOT SHOWN", "ABSENT"),
        "repeat": (
            "does **not** close the adaptive re-noise attack",
            "does close the adaptive re-noise attack",
        ),
    }
    missed = []
    for name, (old, new) in mutations.items():
        mutated = text.replace(old, new, 1)
        if not check(mutated):
            missed.append(name)
    return missed


def main() -> int:
    text = REPORT.read_text(encoding="utf-8")
    errors = check(text)
    missed = mutation_self_test(text)
    print(f"REPORT_LINES={len(text.splitlines())}")
    print(f"PINNED_VALUES={len(expected_strings())}")
    print(f"CITATIONS={'GREEN' if not citation_errors(text) else 'RED'}")
    print(f"CLAIMS={'GREEN' if not errors else 'RED'}")
    print(f"MUTATION_SELF_TEST={'GREEN' if not missed else 'RED'}")
    for error in errors:
        print("ERROR: " + error)
    if missed:
        print("MISSED_MUTATIONS=" + ",".join(missed))
    passed = not errors and not missed
    print("VERDICT: " + ("GREEN" if passed else "RED"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
