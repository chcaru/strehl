"""Independent result/report checker for M-PHASE0-CURV.

This file deliberately does not import curvlib.  Its small Huber fit and report
parser are a second implementation.  ``--self-test`` commissions the parser
before any real report exists by planting a stale deciding number and a flipped
verdict in memory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import re
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPORT = ROOT.parents[1] / "docs" / "research" / "M-PHASE0-CURV.md"
VERDICTS = {"SURVIVE", "NARROWED", "KILL", "NOT ROBUST", "ALREADY ANSWERED IN CORPUS"}


def parse_report(text: str) -> dict[str, object]:
    vm = re.search(r"^VERDICT:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    qm = re.search(
        r"^DECIDING_Q_H_FRAMES:\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*"
        r"\[\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*\]\s*$",
        text,
        flags=re.MULTILINE,
    )
    if vm is None or qm is None:
        raise ValueError("report lacks pinned VERDICT or DECIDING_Q_H_FRAMES line")
    return {
        "verdict": vm.group(1).strip(),
        "q": float(qm.group(1)),
        "ci95": [float(qm.group(2)), float(qm.group(3))],
    }


def report_matches(text: str, expected: dict[str, object], tol: float = 5e-4) -> bool:
    try:
        got = parse_report(text)
    except ValueError:
        return False
    return bool(
        got["verdict"] == expected["verdict"]
        and abs(float(got["q"]) - float(expected["q"])) <= tol
        and all(
            abs(float(a) - float(b)) <= tol
            for a, b in zip(got["ci95"], expected["ci95"])
        )
    )


def _irls(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    weights = np.ones(len(y))
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(50):
        sw = np.sqrt(weights)
        nxt = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        residual = y - X @ nxt
        mad = np.median(np.abs(residual - np.median(residual)))
        scale = max(float(mad / 0.6744897501960817), 1e-12)
        cutoff = 1.345 * scale
        new_weights = np.minimum(1.0, cutoff / np.maximum(np.abs(residual), 1e-12))
        if np.max(np.abs(nxt - beta)) < 1e-10 and np.max(
            np.abs(new_weights - weights)
        ) < 1e-8:
            beta = nxt
            break
        beta, weights = nxt, new_weights
    return beta


def independent_q(
    rows: list[dict[str, str]],
    width: float,
    height: float,
    key: str = "k_primary_avg",
    degree: int = 3,
) -> float:
    valid = [r for r in rows if r["valid"].lower() == "true"]
    x = np.array([float(r["x_sensor"]) for r in valid])
    y = np.array([float(r["y_sensor"]) for r in valid])
    z = np.array([float(r[key]) for r in valid])
    xn = (x - width / 2.0) / (height / 2.0)
    yn = (y - height / 2.0) / (height / 2.0)
    linear = np.column_stack([np.ones_like(xn), xn, yn])
    b0 = _irls(linear, z)
    g = b0[1:3]
    norm = float(np.linalg.norm(g))
    axis = np.array([1.0, 0.0]) if norm < 1e-10 else g / norm
    u = axis[0] * xn + axis[1] * yn
    v = -axis[1] * xn + axis[0] * yn
    columns = [np.ones_like(u)]
    columns.extend(u**d for d in range(1, degree + 1))
    columns.extend([v, u * v, u * u * v, v * v])
    return float(_irls(np.column_stack(columns), z)[-1])


def self_test() -> dict[str, object]:
    expected = {"verdict": "SURVIVE", "q": 1.25, "ci95": [0.75, 1.75]}
    good = (
        "# fixture\n\n"
        "VERDICT: SURVIVE\n"
        "DECIDING_Q_H_FRAMES: 1.2500 [0.7500, 1.7500]\n"
    )
    number_mutation = good.replace("1.2500", "1.4500", 1)
    verdict_mutation = good.replace("VERDICT: SURVIVE", "VERDICT: KILL")
    result = {
        "baseline_green": report_matches(good, expected),
        "number_plant_red": not report_matches(number_mutation, expected),
        "verdict_plant_red": not report_matches(verdict_mutation, expected),
    }
    result["pass"] = bool(all(result.values()))
    return result


def check_final() -> dict[str, object]:
    result_path = OUT / "results.json"
    if not result_path.exists() or not REPORT.exists():
        raise FileNotFoundError("results.json and final report must both exist")
    results = json.loads(result_path.read_text(encoding="utf-8"))
    primary = results["primary"]
    samples = np.asarray(primary["bootstrap"]["q_samples"], dtype=float)
    ci = [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))]
    checks: dict[str, object] = {}
    checks["bootstrap_reps_2000"] = len(samples) == 2000
    checks["bootstrap_ci"] = bool(
        np.allclose(ci, primary["bootstrap"]["ci95"], rtol=0, atol=1e-10)
    )

    peak_path = ROOT / primary["peak_csv"]
    with peak_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    q2 = independent_q(
        rows,
        float(primary["active_width"]),
        float(primary["active_height"]),
    )
    checks["independent_primary_q"] = abs(q2 - float(primary["q_h_frames"])) <= 5e-8
    checks["independent_q_value"] = q2

    expected = {
        "verdict": results["verdict"],
        "q": primary["q_h_frames"],
        "ci95": primary["bootstrap"]["ci95"],
    }
    report_text = REPORT.read_text(encoding="utf-8")
    checks["report_pins_headline"] = report_matches(report_text, expected)
    parsed = parse_report(report_text)
    checks["verdict_allowed"] = parsed["verdict"] in VERDICTS

    before = json.loads((OUT / "readonly-before.json").read_text(encoding="utf-8"))
    after = json.loads((OUT / "readonly-after.json").read_text(encoding="utf-8"))
    b = {
        row["path"]: (
            row["file_count"],
            row["arw_count"],
            row["total_bytes"],
            row["newest_write_utc"],
        )
        for row in before["captures"]
    }
    a = {
        row["path"]: (
            row["file_count"],
            row["arw_count"],
            row["total_bytes"],
            row["newest_write_utc"],
        )
        for row in after["captures"]
    }
    checks["captures_unchanged"] = a == b
    checks["pass"] = bool(
        all(v for k, v in checks.items() if k not in {"independent_q_value", "pass"})
    )
    return checks


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    result = self_test() if args.self_test else check_final()
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

