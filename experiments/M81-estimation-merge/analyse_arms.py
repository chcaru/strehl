"""Reduce M81's paired gate-4/calibrated arm logs."""

from __future__ import annotations

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
DETAIL_ROW = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)x\s+(\S+)\s+"
    r"([-+0-9.]+)x\s+([-+0-9.]+)\s+([-+0-9.]+)"
)


def two_rows(lines: list[str], header: str, pattern: re.Pattern[str]) -> list[re.Match[str]]:
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


def main() -> None:
    calibration = json.loads((HERE / "calibration-results.json").read_text(encoding="utf-8"))
    m77 = json.loads(
        (
            REPO / "experiments" / "M77-gate-sweep" / "out" / "01b-rois.json"
        ).read_text(encoding="utf-8")
    )
    out = {"bars": {"Q_ratio_min": 1.01, "D_ratio_min": 0.98}, "stacks": {}}
    for stack in STACKS:
        lines = (HERE / f"arms-{stack}.log").read_text(encoding="utf-8-sig").splitlines()
        gates = two_rows(lines, "mean n_eff", GATE_ROW)
        hp = two_rows(lines, "hp sd DN", HP_ROW)
        detail = two_rows(lines, "q signal", DETAIL_ROW)
        arms = []
        for index, name in enumerate(("control", "candidate")):
            gate_row, hp_row, detail_row = gates[index], hp[index], detail[index]
            q_signal = float(detail_row.group(2))
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
                    "hp_ratio_range": [float(hp_row.group(4)), float(hp_row.group(5))],
                    "q_signal_power_dn2": q_signal,
                    "D_signal_amplitude_dn": math.sqrt(max(q_signal, 0.0)),
                    "retention": float(detail_row.group(3)),
                    "detail_structure": float(detail_row.group(5)),
                    "detail_raw_rms": float(detail_row.group(6)),
                    "detail_controlled_noise_rms": float(detail_row.group(7)),
                }
            )
        control, candidate = arms
        d_ratio = candidate["D_signal_amplitude_dn"] / control["D_signal_amplitude_dn"]
        h_ratio = candidate["H_hp_sd_dn"] / control["H_hp_sd_dn"]
        q_ratio = d_ratio / h_ratio
        cal = calibration["stacks"][stack]
        m77_row = m77[stack]
        fresh_g2_error = abs(candidate["mean_n_eff"] - cal["gate"]["target"]) / cal["gate"][
            "target"
        ]
        result = {
            "frames": cal["frames"],
            "candidate_gate": cal["gate"]["value"],
            "arms": arms,
            "ratios": {
                "D_candidate_over_control": d_ratio,
                "H_candidate_over_control": h_ratio,
                "Q_candidate_over_control": q_ratio,
            },
            "controls": {
                "G2_solver_relative_error": cal["controls"]["G2_relative_error"],
                "G2_fresh_relative_error": fresh_g2_error,
                "G2_pass": fresh_g2_error <= 0.01,
                "M77_flat_contamination_max": m77_row["flat_roi"]["contam_max"],
                "M77_flat_control_pass": m77_row["k1_met"],
                "M77_detail_ratio": m77_row["k2_ratio"],
                "M77_detail_control_pass": m77_row["k2_met"],
                "M77_flat_stability_pass": m77_row["k5_flat_met"],
                "M77_detail_stability_pass": m77_row["k5_detail_met"],
                "M80_detail_readable_at_both_arms": (
                    control["detail_structure"] >= 3.0
                    and candidate["detail_structure"] >= 3.0
                ),
                "singleton_floor_exposure": candidate["singleton_percent"] > 0.0,
            },
        }
        result["numerical_acceptance_pass"] = (
            q_ratio >= 1.01 and d_ratio >= 0.98 and fresh_g2_error <= 0.01
        )
        out["stacks"][stack] = result

    out["accepted_stacks"] = sum(
        row["numerical_acceptance_pass"] for row in out["stacks"].values()
    )
    (HERE / "arms-results.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8"
    )
    for stack, row in out["stacks"].items():
        ratios = row["ratios"]
        controls = row["controls"]
        print(
            f"{stack:16} D={ratios['D_candidate_over_control']:.6f} "
            f"H={ratios['H_candidate_over_control']:.6f} "
            f"Q={ratios['Q_candidate_over_control']:.6f} "
            f"readable={controls['M80_detail_readable_at_both_arms']} "
            f"pass={row['numerical_acceptance_pass']}"
        )


if __name__ == "__main__":
    main()
