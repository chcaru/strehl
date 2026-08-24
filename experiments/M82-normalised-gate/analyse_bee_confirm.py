"""Parse fresh bee solved-gate confirmations and companion diagnostics."""

from __future__ import annotations

import json

import analyse_confirm as C
import m82lib as M


def main() -> None:
    ladder = json.loads(
        (M.HERE / "bee-ladder-results.json").read_text(encoding="utf-8")
    )
    binary = ladder["binary"]
    output = {
        "confirmation_tolerance_absolute": M.CONFIRM_TOLERANCE,
        "binary": binary,
        "stacks": {},
    }
    for stack in M.BEE_SIBLINGS:
        path = M.HERE / f"bee-confirm-{stack}.log"
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if (
            C.field(lines, "STACK") != stack
            or C.field(lines, "DIRECTORY") != M.STACKS[stack]["directory"]
            or C.field(lines, "commit") != binary["commit"]
            or C.field(lines, "sha256") != binary["sha256"]
            or C.field(lines, "exit") != "0"
        ):
            raise RuntimeError(f"{stack}: confirmation provenance differs")
        recorded_gates = [float(v) for v in C.field(lines, "SOLVED_GATES").split(",")]
        wanted_gates = [
            ladder["stacks"][stack]["solves"][f"{request:.2f}"]["gate"]
            for request in M.REQUESTS
        ]
        if len(recorded_gates) != len(wanted_gates) or any(
            abs(a - b) > 5e-10 for a, b in zip(recorded_gates, wanted_gates)
        ):
            raise RuntimeError(f"{stack}: recorded solved gates differ")
        gate_rows = C.rows_after(lines, "mean n_eff", C.GATE_ROW, len(M.REQUESTS))
        hp_rows = C.rows_after(lines, "hp sd DN", C.HP_ROW, len(M.REQUESTS))
        details = C.detail_rows(lines, len(M.REQUESTS))
        selector = next(
            (C.SELECTOR_ROW.match(line) for line in lines if C.SELECTOR_ROW.match(line)),
            None,
        )
        if selector is None:
            raise RuntimeError(f"{stack}: selector detail row missing")
        targets = {}
        for request, solved_gate, gate_row, hp_row, detail in zip(
            M.REQUESTS, wanted_gates, gate_rows, hp_rows, details, strict=True
        ):
            achieved = float(gate_row.group(6))
            targets[f"{request:.2f}"] = {
                "request": request,
                "solved_gate": solved_gate,
                "printed_gate": float(gate_row.group(1)),
                "mean_n_eff": float(gate_row.group(3)),
                "n_eff_over_n": float(gate_row.group(3)) / M.STACKS[stack]["n"],
                "singleton_percent": float(gate_row.group(4)),
                "boundary_percent": float(gate_row.group(5)),
                "predicted_sigma_gain": achieved,
                "absolute_error": abs(achieved - request),
                "confirmed": abs(achieved - request) <= M.CONFIRM_TOLERANCE,
                "flat_hp_sd_dn": float(hp_row.group(2)),
                "flat_hp_ratio": float(hp_row.group(3)),
                "flat_hp_ratio_range": [
                    float(hp_row.group(4)),
                    float(hp_row.group(5)),
                ],
                "m80": detail,
            }
        frames = next(
            int(line.split(":", 1)[1].split()[0])
            for line in lines
            if line.startswith("frames")
        )
        if frames != M.STACKS[stack]["n"]:
            raise RuntimeError(f"{stack}: frame count differs")
        output["stacks"][stack] = {
            "directory": M.STACKS[stack]["directory"],
            "frames": frames,
            "log_sha256": M.sha256(path),
            "selector_m80": {
                "q_signal_power_dn2": float(selector.group(1)),
                "signal_standard_error": float(selector.group(2)),
                "z": float(selector.group(3)),
                "target": selector.group(4),
            },
            "targets": targets,
            "all_confirmed": all(row["confirmed"] for row in targets.values()),
        }
        print(
            f"{stack:8} "
            + " ".join(
                f"S{request:.2f}={targets[f'{request:.2f}']['predicted_sigma_gain']:.4f}"
                f" singleton={targets[f'{request:.2f}']['singleton_percent']:.2f}%"
                for request in M.REQUESTS
            )
        )
    output["all_confirmed"] = all(
        row["all_confirmed"] for row in output["stacks"].values()
    )
    (M.HERE / "bee-confirm-results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(f"all confirmations pass={output['all_confirmed']}")


if __name__ == "__main__":
    main()
