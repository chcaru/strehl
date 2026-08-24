"""Reduce M81's gate-4 versus corrected-unit gate-4 paired runs."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STACKS = ("wrapped-text-1", "109MSDCF", "coffee-bean", "foam", "bee-1")

GATE_ROW = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)%"
    r"\s+([-+0-9.]+)%\s+([-+0-9.]+)x$"
)
HP_ROW = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)x\s+"
    r"\[\s*([-+0-9.]+)x \.\.\s*([-+0-9.]+)x\]"
)
SELECTOR_ROW = re.compile(
    r"^selector gate 0 : q\s+([-+0-9.]+) \+/-\s+([-+0-9.]+) DN\^2"
    r"\s+z\s+([-+0-9.]+)\s+target\s+(\S+)"
)
DETAIL_MEASURED = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)x\s+(\S+)\s+"
    r"([-+0-9.]+)x\s+([-+0-9.]+)\s+([-+0-9.]+)"
)
DETAIL_NA = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+N/A\s+NO TARGET\s+"
    r"([-+0-9.]+)x\s+([-+0-9.]+)\s+([-+0-9.]+)"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def two_rows(lines: list[str], header: str, pattern: re.Pattern[str]) -> list:
    start = next(i for i, line in enumerate(lines) if header in line)
    rows = []
    for line in lines[start + 1 :]:
        if match := pattern.match(line):
            rows.append(match)
            if len(rows) == 2:
                return rows
        elif rows and not line.strip():
            break
    raise RuntimeError(f"{header}: found {len(rows)} rows")


def detail_rows(lines: list[str]) -> list[dict]:
    start = next(i for i, line in enumerate(lines) if "q signal" in line)
    rows = []
    for line in lines[start + 1 :]:
        if match := DETAIL_MEASURED.match(line):
            rows.append(
                {
                    "printed_gate": float(match.group(1)),
                    "q_signal_power_dn2": float(match.group(2)),
                    "retention": float(match.group(3)),
                    "detail_verdict": match.group(4),
                    "structure": float(match.group(5)),
                    "raw_rms": float(match.group(6)),
                    "controlled_noise_rms": float(match.group(7)),
                }
            )
        elif match := DETAIL_NA.match(line):
            rows.append(
                {
                    "printed_gate": float(match.group(1)),
                    "q_signal_power_dn2": float(match.group(2)),
                    "retention": None,
                    "detail_verdict": "NO TARGET",
                    "structure": float(match.group(3)),
                    "raw_rms": float(match.group(4)),
                    "controlled_noise_rms": float(match.group(5)),
                }
            )
        if len(rows) == 2:
            return rows
    raise RuntimeError(f"detail table: found {len(rows)} rows")


def main() -> None:
    unit = json.loads((HERE / "unit-results.json").read_text(encoding="utf-8"))
    binary = json.loads((HERE / "unit-binary.json").read_text(encoding="utf-8"))
    m77_path = (
        REPO / "experiments" / "M77-gate-sweep" / "out" / "01b-rois.json"
    )
    m77 = json.loads(m77_path.read_text(encoding="utf-8"))
    out = {
        "bars": {"Q_ratio_min": 1.01, "D_ratio_min": 0.98},
        "binary": binary,
        "m77_roi_source_sha256": sha256(m77_path),
        "stacks": {},
    }
    for stack in STACKS:
        lines = (HERE / f"unit-arms-{stack}.log").read_text(
            encoding="utf-8-sig"
        ).splitlines()
        headers = {
            key: [line.split("=", 1)[1] for line in lines if line.startswith(key + "=")]
            for key in ("commit", "sha256", "STACK", "CANDIDATE_GATE", "exit")
        }
        if any(len(value) != 1 for value in headers.values()):
            raise RuntimeError(f"{stack}: incomplete or duplicate evidence headers")
        if (
            headers["commit"][0] != binary["commit"]
            or headers["sha256"][0] != binary["sha256"]
            or headers["STACK"][0] != stack
            or headers["exit"][0] != "0"
        ):
            raise RuntimeError(f"{stack}: evidence provenance differs")
        recorded_candidate = float(headers["CANDIDATE_GATE"][0])
        if abs(recorded_candidate - unit["candidate_gate"][stack]) > 5e-10:
            raise RuntimeError(f"{stack}: candidate gate differs from unit solve")
        gates = two_rows(lines, "mean n_eff", GATE_ROW)
        hp = two_rows(lines, "hp sd DN", HP_ROW)
        selector = next(
            (SELECTOR_ROW.match(line) for line in lines if SELECTOR_ROW.match(line)),
            None,
        )
        if selector is None:
            raise RuntimeError(f"{stack}: selector detail control missing")
        details = detail_rows(lines)
        arms = []
        for index, name in enumerate(("control", "candidate")):
            gate_row, hp_row, detail = gates[index], hp[index], details[index]
            q = detail["q_signal_power_dn2"]
            arms.append(
                {
                    "name": name,
                    "printed_gate": float(gate_row.group(1)),
                    "mean_n_eff": float(gate_row.group(3)),
                    "singleton_percent": float(gate_row.group(4)),
                    "boundary_percent": float(gate_row.group(5)),
                    "predicted_sigma_gain": float(gate_row.group(6)),
                    "H_hp_sd_dn": float(hp_row.group(2)),
                    "hp_ratio": float(hp_row.group(3)),
                    "hp_ratio_range": [
                        float(hp_row.group(4)),
                        float(hp_row.group(5)),
                    ],
                    "D_signal_amplitude_dn": math.sqrt(max(q, 0.0)),
                    **detail,
                }
            )
        control, candidate = arms
        d_ratio = (
            candidate["D_signal_amplitude_dn"] / control["D_signal_amplitude_dn"]
            if control["D_signal_amplitude_dn"] > 0
            else math.nan
        )
        h_ratio = candidate["H_hp_sd_dn"] / control["H_hp_sd_dn"]
        q_ratio = d_ratio / h_ratio
        m77_row = m77[stack]
        selector_target = selector.group(4)
        readable = bool(m77_row["k1_met"]) and selector_target == "MEASURABLE"
        numerical_pass = d_ratio >= 0.98 and q_ratio >= 1.01
        if not readable:
            verdict = "unreadable"
        elif numerical_pass:
            verdict = "pass"
        else:
            verdict = "fail"
        out["stacks"][stack] = {
            "frames": next(
                int(line.split(":", 1)[1].split()[0])
                for line in lines
                if line.startswith("frames")
            ),
            "candidate_gate": unit["candidate_gate"][stack],
            "selector_detail": {
                "q_signal_power_dn2": float(selector.group(1)),
                "signal_standard_error": float(selector.group(2)),
                "z": float(selector.group(3)),
                "target": selector_target,
            },
            "arms": arms,
            "ratios": {
                "D_candidate_over_control": d_ratio,
                "H_candidate_over_control": h_ratio,
                "Q_candidate_over_control": q_ratio,
            },
            "controls": {
                "M77_flat_contamination_max": m77_row["flat_roi"]["contam_max"],
                "M77_flat_control_pass": bool(m77_row["k1_met"]),
                "M80_detail_target_measurable": selector_target == "MEASURABLE",
                "M80_acceptance_readable": readable,
                "candidate_model_sigma_floor_pass": (
                    candidate["predicted_sigma_gain"] <= 1.0
                ),
                "candidate_singleton_floor_exposure": (
                    candidate["singleton_percent"] > 0.0
                ),
            },
            "numerical_acceptance_pass": numerical_pass,
            "acceptance_verdict": verdict,
        }
    out["accepted_stacks"] = sum(
        row["acceptance_verdict"] == "pass" for row in out["stacks"].values()
    )
    out["five_of_five_pass"] = out["accepted_stacks"] == len(STACKS)
    out["single_frame_floor_pass"] = all(
        row["controls"]["candidate_model_sigma_floor_pass"]
        and not row["controls"]["candidate_singleton_floor_exposure"]
        for row in out["stacks"].values()
    )
    (HERE / "unit-arms-results.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )
    for stack, row in out["stacks"].items():
        ratios = row["ratios"]
        print(
            f"{stack:16} D={ratios['D_candidate_over_control']:.6f} "
            f"H={ratios['H_candidate_over_control']:.6f} "
            f"Q={ratios['Q_candidate_over_control']:.6f} "
            f"readable={row['controls']['M80_acceptance_readable']} "
            f"singleton={row['arms'][1]['singleton_percent']:.2f}% "
            f"verdict={row['acceptance_verdict']}"
        )
    print(
        f"paired acceptance: {out['accepted_stacks']}/5; "
        f"single-frame floor={out['single_frame_floor_pass']}"
    )


if __name__ == "__main__":
    main()
