#!/usr/bin/env python3
"""Fail-closed content checks for the M166 rehearsal report."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    report = root.parents[1] / "docs" / "research" / (
        "M166-reference-dominance-rehearsal.md"
    )
    prior = root.parents[1] / "docs" / "research" / (
        "M166-reference-information-dominance-physical.md"
    )
    output = root / "report-verification.json"
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append(
            {"name": name, "passed": bool(condition), "detail": detail}
        )

    try:
        text = report.read_text(encoding="utf-8")
        prior_text = prior.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        prior_normalized = " ".join(prior_text.split())
        first_nonempty = next(line for line in text.splitlines() if line)

        required = {
            "headline": "REHEARSAL SPECIFIED: 1,092 frames",
            "corrected score": "combined score is `1,215`, not `1,147`",
            "complete witness": "`TC0-DOM-sw4-A`",
            "second density": "`TC0-DOM-sw10-B`",
            "zero-frame stop": "blocks the rehearsal at zero frames",
            "four strips": "rows `1-2`, `3-4`, `5-6`, and `7-8`",
            "non-holdout marker": "D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE",
            "fresh validation after repair": (
                "requires a fresh independently seeded D2 panel as well as "
                "a fresh sitting"
            ),
            "partial refusal": "merely partial result is overall `UNMEASURED`",
            "no transfer guarantee": (
                "A rehearsal pass cannot guarantee that the independent "
                "scored session passes"
            ),
            "Viltrox aberration": "**Viltrox aberration",
            "transmission loss": "**Viltrox transmission loss",
            "focus error": "**focus error**",
            "bare-lens pupil": "**bare-lens pupil behavior**",
            "one sitting": "one uninterrupted `1,092`-frame sitting",
            "score omits controls": "score does not contain",
            "unrelated combined omission": (
                "They neither enter the M1 reference nor the M1 scored-path "
                "witness"
            ),
            "optional full dress": (
                "full-dress endurance rehearsal that also repeats those "
                "unrelated inputs would be `1,407` frames"
            ),
            "owner text": "## 8. Paste-ready owner-facing capture text",
            "final owner stop": "One missing, > invalid, null, weak or failed cell",
            "no absolute timing": "No absolute duration is asserted",
            "running verification": "PASS: 11/11 checks",
        }

        check(
            "report starts with required lead",
            first_nonempty == "**REHEARSAL SPECIFIED: 1,092 frames**",
            first_nonempty,
        )
        for name, needle in required.items():
            check(name, needle in normalized, needle)

        forbidden_positive_instructions = [
            "capture three > fixed-focus strips",
            "TC0-DOM-S01-R01-03",
            "Frame total:** `1,147`",
        ]
        for forbidden in forbidden_positive_instructions:
            check(
                f"forbidden stale instruction absent: {forbidden}",
                forbidden not in normalized,
                forbidden,
            )

        check(
            "prior report carries supersession banner",
            "> **SUPERSEDED IN PART.**" in prior_text
            and "corrects the combined scored total from `1,147` to > `1,215`"
            in prior_normalized,
            "supersession banner and corrected total",
        )

        passed = sum(1 for item in checks if item["passed"])
        result = {
            "status": "PASS" if passed == len(checks) else "FAIL",
            "passed": passed,
            "total": len(checks),
            "checks": checks,
        }
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"{result['status']}: {passed}/{len(checks)} checks")
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "passed": 0,
            "total": len(checks),
            "checks": checks,
            "error": f"{type(exc).__name__}: {exc}",
        }
        try:
            output.write_text(
                json.dumps(failure, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        print(f"FAIL: {failure['error']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
