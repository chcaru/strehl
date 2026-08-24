"""Reduce M81 calibration logs against the pre-registered controls."""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
STACK_RE = re.compile(r"^STACK=(.+)$")
CONFIG_RE = re.compile(r"^M81_CONFIG frames=(\d+) workers=(\d+) analysis=(\d+)x(\d+)")
SPECTRAL_RE = re.compile(
    r"^M81_SPECTRAL scale=([0-9.]+) n_eff=([-+0-9.eE]+) "
    r"bands=([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+) "
    r"textured=(\d+) frames=(\d+)"
)
GATE_RE = re.compile(
    r"^M81_GATE target=([-+0-9.eE]+) gate=([-+0-9.eE]+) "
    r"realised=([-+0-9.eE]+) bracket=([-+0-9.eE]+),([-+0-9.eE]+) "
    r"gate_zero=([-+0-9.eE]+) gate_widest=([-+0-9.eE]+) unreachable=(\d+)"
)


def main() -> None:
    reference = json.loads((HERE / "reference.json").read_text(encoding="utf-8"))
    rows: dict[str, dict] = {}
    current = None
    for line in (HERE / "calibration.log").read_text(encoding="utf-8-sig").splitlines():
        if match := STACK_RE.match(line):
            current = match.group(1)
            rows[current] = {"targets": []}
        elif current is not None and (match := CONFIG_RE.match(line)):
            rows[current]["frames"] = int(match.group(1))
            rows[current]["workers"] = int(match.group(2))
            rows[current]["analysis"] = [int(match.group(3)), int(match.group(4))]
        elif current is not None and (match := SPECTRAL_RE.match(line)):
            rows[current]["targets"].append(
                {
                    "scale": float(match.group(1)),
                    "n_eff": float(match.group(2)),
                    "per_band_n_eff": [float(match.group(i)) for i in range(3, 6)],
                    "textured_patches": int(match.group(6)),
                }
            )
        elif current is not None and (match := GATE_RE.match(line)):
            rows[current]["gate"] = {
                "target": float(match.group(1)),
                "value": float(match.group(2)),
                "realised": float(match.group(3)),
                "bracket": [float(match.group(4)), float(match.group(5))],
                "gate_zero": float(match.group(6)),
                "gate_widest": float(match.group(7)),
                "unreachable": int(match.group(8)),
            }

    for stack, row in rows.items():
        if len(row["targets"]) != 3 or "gate" not in row:
            raise RuntimeError(f"{stack}: incomplete calibration log")
        nominal = row["targets"][1]["n_eff"]
        python_nominal = reference["stacks"][stack]["targets"][1]["n_eff"]
        values = [target["n_eff"] for target in row["targets"]]
        row["controls"] = {
            "S1_python_relative_error": abs(nominal - python_nominal) / abs(python_nominal),
            "S1_pass": abs(nominal - python_nominal) / abs(python_nominal) <= 0.02,
            "S4_span_over_nominal": (max(values) - min(values)) / nominal,
            "S4_pass": (max(values) - min(values)) / nominal <= 0.20,
            "S5_pass": (
                1.0 <= nominal <= row["frames"]
                and row["targets"][1]["textured_patches"] > 0
            ),
            "G2_relative_error": abs(row["gate"]["realised"] - nominal) / nominal,
            "G2_pass": abs(row["gate"]["realised"] - nominal) / nominal <= 0.01,
            "G3_pass": row["gate"]["bracket"][0]
            <= nominal
            <= row["gate"]["bracket"][1],
            "G4_pass": (
                row["gate"]["gate_zero"] == 1.0
                and row["gate"]["gate_widest"] == row["frames"]
                and row["gate"]["unreachable"] == 0
            ),
        }
    result = {
        "bars": {
            "S1_python_relative_error_max": 0.02,
            "S4_span_over_nominal_max": 0.20,
            "G2_relative_error_max": 0.01,
        },
        "stacks": rows,
    }
    (HERE / "calibration-results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    for stack, row in rows.items():
        controls = row["controls"]
        print(
            f"{stack:16} T*={row['gate']['value']:10.6f} "
            f"S1={controls['S1_python_relative_error']:.3e} "
            f"S4={controls['S4_span_over_nominal']:.6g} "
            f"G2={controls['G2_relative_error']:.3e} "
            f"S4_pass={controls['S4_pass']}"
        )


if __name__ == "__main__":
    main()
