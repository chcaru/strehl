#!/usr/bin/env python3
"""Verify the razor ruling, request register, and unchanged scorecard bars."""
from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_SCORECARD = REPO / "docs/proposals/2026-09-sota-scorecard.md"
DEFAULT_AUDIT = HERE / "request-audit.json"
STATUS = REPO / "docs/STATUS.md"
M128 = REPO / "experiments/M128-razor-ladder/PREREGISTRATION.md"
M164_APERTURE = REPO / "docs/research/M164-aperture-identifiability.md"
M166_APERTURE = REPO / "docs/research/M166-aperture-premise.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
BASE_REV = "1bb4c9f8"


@dataclass(frozen=True)
class Check:
    group: str
    name: str
    passed: bool
    detail: str


def emit(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8"))


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def git_blob(revision: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout.decode("utf-8").replace("\r\n", "\n")


def normalise(text: str) -> str:
    lines = [re.sub(r"^\s*>\s?", "", line) for line in text.splitlines()]
    collapsed = re.sub(r"\s+", " ", "\n".join(lines)).strip()
    return collapsed.replace("**", "").replace("*", "").replace("`", "")


def contains(text: str, phrase: str) -> bool:
    return normalise(phrase) in normalise(text)


def section(text: str, start_heading: str, end_heading: str) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[start:end]


def capture_rows(scorecard: str) -> dict[str, dict[str, str]]:
    table = section(
        scorecard,
        "### 2.2 Scored and control captures",
        "### 2.3 Holdout units and burn log",
    )
    rows: dict[str, dict[str, str]] = {}
    for line in table.splitlines():
        match = re.match(r"^\| `(?P<path>requests\\[^`]+)` \|", line)
        if not match:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        path = match.group("path")
        rows[path] = {
            "metadata": cells[1],
            "evidence_class": cells[2],
            "role": cells[3],
        }
    return rows


def metric_rows(text: str, metric: str) -> list[str]:
    return [
        line
        for line in section(
            text, "## 3. Scorecard at a glance", "## 4. Metric cards"
        )
        .splitlines()
        if re.match(rf"^\| {re.escape(metric)} \|", line)
    ]


def result_rows(text: str, metric: str) -> list[str]:
    return [
        line
        for line in section(
            text, "## 6. Honest current position", "## 7. Corrections"
        )
        .splitlines()
        if re.match(rf"^\| {re.escape(metric)} \|", line)
    ]


def add(
    checks: list[Check], group: str, name: str, passed: bool, detail: str
) -> None:
    checks.append(Check(group, name, passed, detail))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, default=DEFAULT_SCORECARD)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    scorecard = read_utf8(args.scorecard.resolve())
    base = git_blob(BASE_REV, SCORECARD_PATH)
    status = read_utf8(STATUS)
    m128 = read_utf8(M128)
    m164_aperture = read_utf8(M164_APERTURE)
    m166_aperture = read_utf8(M166_APERTURE)
    audit = json.loads(args.audit.resolve().read_text(encoding="utf-8"))
    rows = capture_rows(scorecard)
    checks: list[Check] = []

    source_checks = (
        (
            "source.raggedness",
            contains(status, "1.23 green px RMS")
            and contains(status, "0.02 and fails at 0.03 green px RMS")
            and contains(status, "54× over"),
            "M128 straightness evidence present",
        ),
        (
            "source.registration-bias",
            contains(status, "biasing `f_c` by +91.05% at zero wander")
            and contains(status, "self-registration sharpening"),
            "M128 self-registration failure present",
        ),
        (
            "source.required-target",
            contains(status, "a lithographic chrome-on-glass edge, not a razor"),
            "replacement target preserved",
        ),
        (
            "source.six-razor-stacks",
            contains(m128, "Which of the six razor stacks")
            and contains(m128, "the diagonal set's larger slant"),
            "M128 scope covers the six-stack razor family",
        ),
        (
            "source.aperture-two-worlds",
            contains(
                m164_aperture,
                "world A: Y_i = K H_i X",
            )
            and contains(
                m164_aperture,
                "world B: Y_i = H_i X', X'=KX",
            )
            and contains(m164_aperture, "max error = 0"),
            "M164 supplies identical sharpening and latent-scene worlds",
        ),
        (
            "source.aperture-screen-only",
            contains(
                m164_aperture,
                "APERTURE ORDER IS A SCREEN, NOT A TRUTH REFERENCE",
            )
            and contains(m164_aperture, "1.409469446x")
            and contains(m164_aperture, "1.11e-15"),
            "M164 proves correct order and relative attenuation are insufficient",
        ),
        (
            "source.actual-locus-does-not-cancel",
            contains(
                m166_aperture,
                "1.77638",
            )
            and contains(m166_aperture, "1.64144")
            and contains(m166_aperture, "1.91766")
            and contains(m166_aperture, "an aperture-specific component of `0.70697 px`"),
            "M166 measures an aperture-specific razor-locus component",
        ),
        (
            "source.actual-capture-confounds",
            contains(m166_aperture, "Total physical depth differs")
            and contains(
                m166_aperture,
                "the 2× teleconverter is already folded into `FNumber`",
            )
            and contains(
                m166_aperture,
                "Equal-count subsampling removes count confound",
            ),
            "M166 audits depth, teleconverter, and frame-budget premises",
        ),
    )
    for name, passed, detail in source_checks:
        add(checks, "source", name, passed, detail)

    audit_paths = {stack["path"] for stack in audit["stacks"]}
    row_paths = set(rows)
    exact_baseline_missing = {
        r"requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f11-cpl",
        r"requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f5.6-cpl",
        r"requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f8-cpl",
        r"requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f11-cpl",
        r"requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f8-cpl",
        r"requests\7-aperture-pairs\fabric-weave-f14-sw5-cpl",
        r"requests\7-aperture-pairs\fabric-weave-f18-sw5-cpl",
        r"requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso200-sw4-cpl",
        r"requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso400-sw4-cpl",
        r"requests\misc-diagnostic\razor-flat-vertical-slightly-tilted-sw1-cpl",
    }
    audit_checks = (
        (
            "audit.read-only",
            audit["tree_before"] == audit["tree_after"],
            audit["tree_after"]["path_size_mtime_sha256"],
        ),
        (
            "audit.counts",
            audit["tree_after"]["file_count"] == 3918
            and audit["arw_count"] == 3908
            and audit["stack_count"] == 32,
            "files=3918 arws=3908 stacks=32",
        ),
        (
            "audit.baseline-gap",
            set(audit["baseline_unregistered"]) == exact_baseline_missing,
            f"baseline_unregistered={len(audit['baseline_unregistered'])}",
        ),
        (
            "audit.current-complete",
            not audit["current_unregistered"]
            and audit["current_registered_count"] == 32
            and row_paths == audit_paths,
            f"registered={len(row_paths)}/32",
        ),
        (
            "audit.no-ghost-paths",
            not audit["scorecard_paths_not_on_disk"],
            f"missing_on_disk={len(audit['scorecard_paths_not_on_disk'])}",
        ),
    )
    for name, passed, detail in audit_checks:
        add(checks, "audit", name, passed, detail)

    expected = {
        r"requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f5.6-cpl": (
            279,
            "100",
            "2.5",
            "5.6",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f8-cpl": (
            210,
            "100",
            "2.5",
            "8",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\19-razor-edge\diagonal-tilt-all-axes\diagonal-tilt-all-axes-sw4-f11-cpl": (
            143,
            "100",
            "2.5",
            "11",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f8-cpl": (
            50,
            "100",
            "3.2",
            "8",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\19-razor-edge\horizontal-flat\razor-edge-horizontal-flat-sw4-f11-cpl": (
            40,
            "100",
            "3.2",
            "11",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\7-aperture-pairs\fabric-weave-f14-sw5-cpl": (
            83,
            "100",
            "1.3",
            "14",
            "BURNED — DEVELOPMENT ONLY, NOT HOLDOUT",
        ),
        r"requests\7-aperture-pairs\fabric-weave-f18-sw5-cpl": (
            71,
            "100",
            "1.3",
            "18",
            "BURNED — DEVELOPMENT ONLY, NOT HOLDOUT",
        ),
        r"requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso200-sw4-cpl": (
            27,
            "200",
            "13",
            "5.6",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\misc-diagnostic\flat-round-3V-battery-cpl\flat-round-3V-battery-iso400-sw4-cpl": (
            27,
            "400",
            "13",
            "5.6",
            "CONTROL — NOT HOLDOUT",
        ),
        r"requests\misc-diagnostic\razor-flat-vertical-slightly-tilted-sw1-cpl": (
            51,
            "100",
            "10",
            "11",
            "DEVELOPMENT — NOT HOLDOUT",
        ),
    }
    stacks = {stack["path"]: stack for stack in audit["stacks"]}
    for path, (count, iso, exposure, aperture, evidence_class) in expected.items():
        stack = stacks.get(path, {})
        row = rows.get(path, {})
        metadata_ok = (
            stack.get("frame_count") == count
            and stack.get("exif", {}).get("ISO") == {iso: count}
            and stack.get("exif", {}).get("ExposureTime") == {exposure: count}
            and stack.get("exif", {}).get("FNumber") == {aperture: count}
        )
        row_ok = (
            str(count) in row.get("metadata", "")
            and evidence_class in row.get("evidence_class", "")
        )
        add(
            checks,
            "paths",
            f"paths.{path}",
            metadata_ok and row_ok,
            f"n={count} ISO={iso} t={exposure} f/{aperture} {evidence_class}",
        )

    ruling_checks = (
        (
            "ruling.scope",
            contains(
                scorecard,
                "the razor prohibition binds every positive M1/detail use",
            )
            and contains(
                scorecard,
                "not limited to statistics that fit a line, estimate `f_c`, "
                "or self-register the edge",
            ),
            "positive M1 scope is explicit",
        ),
        (
            "ruling.ordering-refused",
            contains(
                scorecard,
                "bars the proposed three-aperture ordering statistic",
            )
            and contains(
                scorecard,
                "A razor result may only reject a candidate in development",
            ),
            "concrete ordering use refused",
        ),
        (
            "ruling.no-cancellation",
            contains(scorecard, "`I_N = S * h_N + epsilon_N`")
            and contains(
                scorecard,
                "the fixed subject `S` remains inside the arm-specific "
                "convolution and therefore does not cancel",
            ),
            "common-subject intuition replaced by operator argument",
        ),
        (
            "ruling.spurious-order",
            contains(
                scorecard,
                "a subject-induced ordering or inversion cannot be excluded",
            )
            and contains(
                scorecard,
                "monotone under those actual operators for every allowed fixed locus",
            ),
            "spurious and inverted ordering addressed",
        ),
        (
            "ruling.two-worlds",
            contains(scorecard, "`Y_i = K H_i X = H_i K X`")
            and contains(scorecard, "common USM raises every score by `1.409469446×`")
            and contains(scorecard, "matches the predicted Airy attenuation to `1.11e-15`")
            and contains(
                scorecard,
                "Aperture order is therefore a necessary screen and useful model "
                "check, not a truth reference",
            ),
            "independent two-world counterexample controls the ruling",
        ),
        (
            "ruling.actual-capture",
            contains(
                scorecard,
                "Common-coordinate locus RMS is "
                "`1.77638/1.64144/1.91766 green px`",
            )
            and contains(scorecard, "`0.70697 px` aperture-specific components")
            and contains(
                scorecard,
                "ExifTool already folds the 2× teleconverter into the reported "
                "focal length and f-number",
            ),
            "actual request-19 confounds are recorded",
        ),
        (
            "ruling.m3-only",
            contains(
                scorecard,
                "The existing broad-boundary exception is specific to M3",
            )
            and contains(
                scorecard,
                "not a straightness-dependent resolution truth",
            ),
            "boundary exception is claim-specific",
        ),
        (
            "ruling.precedent",
            contains(
                scorecard,
                "the defect is common across arms” never overrides a capture's "
                "claim-specific ineligibility",
            ),
            "capture designations cannot be bypassed",
        ),
        (
            "ruling.future-amendment",
            contains(
                scorecard,
                "A future monotonicity proof would require a new pre-results "
                "scorecard amendment",
            ),
            "future relief cannot be inferred after a favourable result",
        ),
        (
            "ruling.fabric-sealed",
            contains(
                scorecard,
                "The three registered fabric-weave holdouts remain sealed",
            )
            and all(
                "HOLDOUT — QUALITY" in rows[path]["evidence_class"]
                for path in (
                    r"requests\7-aperture-pairs\fabric-weave-f5.6-sw5-cpl",
                    r"requests\7-aperture-pairs\fabric-weave-f8-sw5-cpl",
                    r"requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl",
                )
            ),
            "three scored fabric arms remain protected",
        ),
    )
    for name, passed, detail in ruling_checks:
        add(checks, "ruling", name, passed, detail)

    add(
        checks,
        "guard",
        "guard.version",
        scorecard.startswith(
            "# strehl — pre-registered SOTA scorecard\n\n"
            "**Status: SPEC / PRE-REGISTRATION v1.10"
        )
        and scorecard.count("**Revision 1.10 — razor ruling") == 1,
        "v1.10 status and one revision entry",
    )
    for number in range(1, 13):
        metric = f"M{number}"
        before = metric_rows(base, metric)
        after = metric_rows(scorecard, metric)
        add(
            checks,
            "bars",
            f"bars.{metric}",
            bool(before) and bool(after) and after[0] == before[0],
            "success row unchanged from v1.9",
        )
    add(
        checks,
        "guard",
        "guard.m2",
        any("**UNMEASURED — INSTRUMENT VOID.**" in row for row in result_rows(scorecard, "M2")),
        "M2 remains UNMEASURED",
    )
    add(
        checks,
        "guard",
        "guard.m8",
        any(
            "**FAIL** — M8-R `1.030569%` against the achievable bar of exactly `0.0000%`"
            in row
            for row in result_rows(scorecard, "M8")
        ),
        "M8 remains FAIL at the registered value and bar",
    )

    for check in checks:
        emit(
            f"{'PASS' if check.passed else 'FAIL'} "
            f"{check.name}: {check.detail}"
        )
    grouped = collections.defaultdict(lambda: [0, 0])
    for check in checks:
        grouped[check.group][0 if check.passed else 1] += 1
    for group in sorted(grouped):
        passed, failed = grouped[group]
        emit(f"GROUP {group}: pass={passed} fail={failed}")
    passed = sum(check.passed for check in checks)
    failed = len(checks) - passed
    emit(f"SUMMARY total={len(checks)} pass={passed} fail={failed} skip=0")
    emit("VERDICT GREEN" if not failed else "VERDICT RED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
