"""Parse the exact solved-gate confirmations and M80 companion rows."""

from __future__ import annotations

import json
import re

import m82lib as M

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


def field(lines: list[str], name: str) -> str:
    prefix = name + "="
    values = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    if len(values) != 1:
        raise RuntimeError(f"{name}: expected one value, found {len(values)}")
    return values[0]


def rows_after(
    lines: list[str], header: str, pattern: re.Pattern[str], expected: int
) -> list[re.Match[str]]:
    start = next(i for i, line in enumerate(lines) if header in line)
    rows = []
    for line in lines[start + 1 :]:
        if match := pattern.match(line):
            rows.append(match)
            if len(rows) == expected:
                return rows
        elif rows and not line.strip():
            break
    raise RuntimeError(f"{header}: expected {expected} rows, found {len(rows)}")


def detail_rows(lines: list[str], expected: int) -> list[dict]:
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
        if len(rows) == expected:
            return rows
    raise RuntimeError(f"detail table: expected {expected} rows, found {len(rows)}")


def main() -> None:
    ladder = json.loads((M.HERE / "ladder-results.json").read_text(encoding="utf-8"))
    binary = json.loads((M.HERE / "binary.json").read_text(encoding="utf-8"))
    output = {
        "confirmation_tolerance_absolute": 0.005,
        "binary": binary,
        "stacks": {},
    }
    for stack in M.STACKS:
        path = M.HERE / f"confirm-{stack}.log"
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if (
            field(lines, "STACK") != stack
            or field(lines, "commit") != binary["commit"]
            or field(lines, "sha256") != binary["sha256"]
            or field(lines, "exit") != "0"
        ):
            raise RuntimeError(f"{stack}: confirmation provenance differs")
        recorded_gates = [float(v) for v in field(lines, "SOLVED_GATES").split(",")]
        wanted_gates = [
            ladder["stacks"][stack]["solves"][f"{request:.2f}"]["gate"]
            for request in M.REQUESTS
        ]
        if any(abs(a - b) > 5e-10 for a, b in zip(recorded_gates, wanted_gates)):
            raise RuntimeError(f"{stack}: recorded solved gates differ")
        gate_rows = rows_after(lines, "mean n_eff", GATE_ROW, len(M.REQUESTS))
        hp_rows = rows_after(lines, "hp sd DN", HP_ROW, len(M.REQUESTS))
        details = detail_rows(lines, len(M.REQUESTS))
        selector = next(
            (SELECTOR_ROW.match(line) for line in lines if SELECTOR_ROW.match(line)),
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
                "confirmed": abs(achieved - request) <= 0.005,
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
            f"{stack:16} "
            + " ".join(
                f"S{request:.2f}={targets[f'{request:.2f}']['predicted_sigma_gain']:.4f}"
                f" singleton={targets[f'{request:.2f}']['singleton_percent']:.2f}%"
                for request in M.REQUESTS
            )
        )
    output["all_confirmed"] = all(
        row["all_confirmed"] for row in output["stacks"].values()
    )
    (M.HERE / "confirm-results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(f"all confirmations pass={output['all_confirmed']}")


if __name__ == "__main__":
    main()
