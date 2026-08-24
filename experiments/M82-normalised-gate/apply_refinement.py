"""Fold pre-registered confirmation updates into confirm-results.json."""

from __future__ import annotations

import json

import analyse_confirm as C
import m82lib as M


def main() -> None:
    result_path = M.HERE / "confirm-results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    plan = json.loads((M.HERE / "refinement-plan.json").read_text(encoding="utf-8"))
    binary = result["binary"]
    for entry in plan["entries"]:
        stack = entry["stack"]
        request = entry["request"]
        iteration = int(entry["iteration"])
        path = M.HERE / f"confirm-refine{iteration}-{stack}-{request}.log"
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if (
            C.field(lines, "STACK") != stack
            or C.field(lines, "REQUEST") != request
            or int(C.field(lines, "ITERATION")) != iteration
            or C.field(lines, "commit") != binary["commit"]
            or C.field(lines, "sha256") != binary["sha256"]
            or C.field(lines, "exit") != "0"
        ):
            raise RuntimeError(f"{path.name}: refinement provenance differs")
        gate = float(C.field(lines, "SOLVED_GATE"))
        gate_row = C.rows_after(lines, "mean n_eff", C.GATE_ROW, 1)[0]
        hp_row = C.rows_after(lines, "hp sd DN", C.HP_ROW, 1)[0]
        detail = C.detail_rows(lines, 1)[0]
        target = result["stacks"][stack]["targets"][request]
        attempts = target.setdefault(
            "attempts",
            [
                {
                    "gate": target["solved_gate"],
                    "predicted_sigma_gain": target["predicted_sigma_gain"],
                    "absolute_error": target["absolute_error"],
                    "confirmed": target["confirmed"],
                    "log": f"confirm-{stack}.log",
                }
            ],
        )
        achieved = float(gate_row.group(6))
        absolute_error = abs(achieved - float(request))
        attempts.append(
            {
                "gate": gate,
                "predicted_sigma_gain": achieved,
                "absolute_error": absolute_error,
                "confirmed": absolute_error <= 0.005,
                "log": path.name,
                "log_sha256": M.sha256(path),
            }
        )
        target.update(
            {
                "solved_gate": gate,
                "printed_gate": float(gate_row.group(1)),
                "mean_n_eff": float(gate_row.group(3)),
                "n_eff_over_n": float(gate_row.group(3)) / M.STACKS[stack]["n"],
                "singleton_percent": float(gate_row.group(4)),
                "boundary_percent": float(gate_row.group(5)),
                "predicted_sigma_gain": achieved,
                "absolute_error": absolute_error,
                "confirmed": absolute_error <= 0.005,
                "flat_hp_sd_dn": float(hp_row.group(2)),
                "flat_hp_ratio": float(hp_row.group(3)),
                "flat_hp_ratio_range": [
                    float(hp_row.group(4)),
                    float(hp_row.group(5)),
                ],
                "m80": detail,
                "attempts": attempts,
            }
        )
        print(
            f"{stack} S={request} update={iteration}: gate={gate:.9f} "
            f"achieved={achieved:.4f} error={absolute_error:.4f} "
            f"pass={target['confirmed']}"
        )
    for stack in M.STACKS:
        result["stacks"][stack]["all_confirmed"] = all(
            row["confirmed"]
            for row in result["stacks"][stack]["targets"].values()
        )
    result["all_confirmed"] = all(
        row["all_confirmed"] for row in result["stacks"].values()
    )
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"all confirmations pass={result['all_confirmed']}")


if __name__ == "__main__":
    main()
