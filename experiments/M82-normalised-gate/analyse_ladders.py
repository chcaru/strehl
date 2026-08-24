"""Parse M82's fresh CLI ladders and solve the registered sigma requests."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import m82lib as M

GATE_ROW = re.compile(
    r"^\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)\s+([-+0-9.]+)%"
    r"\s+([-+0-9.]+)%\s+([-+0-9.]+)x$"
)


def one_field(lines: list[str], name: str) -> str:
    prefix = name + "="
    values = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    if len(values) != 1:
        raise RuntimeError(f"{name}: expected one value, found {len(values)}")
    return values[0]


def parse_ladder(path: Path, stack: str, binary: dict) -> list[dict]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if one_field(lines, "STACK") != stack:
        raise RuntimeError(f"{path.name}: stack header differs")
    if one_field(lines, "commit") != binary["commit"]:
        raise RuntimeError(f"{path.name}: binary commit differs")
    if one_field(lines, "sha256") != binary["sha256"]:
        raise RuntimeError(f"{path.name}: binary hash differs")
    if one_field(lines, "exit") != "0":
        raise RuntimeError(f"{path.name}: process did not exit zero")
    frames = next(
        int(line.split(":", 1)[1].split()[0])
        for line in lines
        if line.startswith("frames")
    )
    if frames != M.STACKS[stack]["n"]:
        raise RuntimeError(f"{path.name}: expected N={M.STACKS[stack]['n']}, got {frames}")
    start = next(i for i, line in enumerate(lines) if "mean n_eff" in line)
    rows = []
    for line in lines[start + 1 :]:
        if match := GATE_ROW.match(line):
            rows.append(
                {
                    "gate": float(match.group(1)),
                    "tolerance": float(match.group(2)),
                    "mean_n_eff": float(match.group(3)),
                    "singleton_percent": float(match.group(4)),
                    "boundary_percent": float(match.group(5)),
                    "predicted_sigma_gain": float(match.group(6)),
                }
            )
        elif rows and not line.strip():
            break
    if tuple(row["gate"] for row in rows) != M.LADDER_GATES:
        raise RuntimeError(f"{path.name}: ladder differs from registration")
    gains = [row["predicted_sigma_gain"] for row in rows]
    if any(right > left + 1e-12 for left, right in zip(gains, gains[1:])):
        raise RuntimeError(f"{path.name}: sigma-gain ladder increases")
    return rows


def main() -> None:
    M.self_tests()
    if "--self-test-only" in sys.argv:
        return
    binary = json.loads((M.HERE / "binary.json").read_text(encoding="utf-8"))
    output = {
        "requests": list(M.REQUESTS),
        "primary_request": M.PRIMARY_REQUEST,
        "binary": binary,
        "stacks": {},
    }
    for stack in M.ORIGINAL_STACKS:
        path = M.HERE / f"ladder-{stack}.log"
        rows = parse_ladder(path, stack, binary)
        solves = {f"{request:.2f}": M.solve_gate(rows, request) for request in M.REQUESTS}
        output["stacks"][stack] = {
            "n": M.STACKS[stack]["n"],
            "log_sha256": M.sha256(path),
            "rows": rows,
            "solves": solves,
            "sigma_monotone": True,
        }
        print(
            f"{stack:16} "
            + " ".join(
                f"S{request:.2f}=T{solves[f'{request:.2f}']['gate']:.7f}"
                for request in M.REQUESTS
            )
        )
    (M.HERE / "ladder-results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
