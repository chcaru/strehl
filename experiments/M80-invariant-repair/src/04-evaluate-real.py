"""Apply M80's pre-registered N1/P2 bars to the four real-ROI runs."""

from __future__ import annotations

import json
import pathlib
import re


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parent / "out"
STACKS = ("wrapped-text-1", "wrapped-text-2")
SELECTOR_RE = re.compile(
    r"^selector gate 0\s+:\s+q\s+([+-][0-9.]+)\s+DN\^2\s+"
    r"STRUCTURE\s+([0-9.]+)x.*?k\(L/R\)\s+([0-9.]+)/\s*([0-9.]+)",
    re.MULTILINE,
)
ROW_RE = re.compile(
    r"^\s+([0-9.]+)\s+([+-][0-9.]+)\s+([0-9.]+)x\s+"
    r"(\S+)\s+([0-9.]+)x\s+([0-9.]+)\s+([0-9.]+)\s+"
    r"([0-9.]+)\s+([0-9.]+)",
    re.MULTILINE,
)


def parse(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sm = SELECTOR_RE.search(text)
    if sm is None:
        raise RuntimeError(f"missing selector row in {path}")
    rows = {}
    for match in ROW_RE.finditer(text):
        gate, q, retention, verdict, structure, raw, control, k_l, k_r = match.groups()
        rows[gate] = {
            "q_signal_power": float(q),
            "retention": float(retention),
            "verdict": verdict,
            "structure": float(structure),
            "raw_rms": float(raw),
            "controlled_noise_rms": float(control),
            "inflation_left": float(k_l),
            "inflation_right": float(k_r),
        }
    for gate in ("0.00", "4.00"):
        if gate not in rows:
            raise RuntimeError(f"missing gate {gate} in {path}")
    return {
        "selector": {
            "q_signal_power": float(sm.group(1)),
            "structure": float(sm.group(2)),
            "inflation_left": float(sm.group(3)),
            "inflation_right": float(sm.group(4)),
        },
        "rows": rows,
    }


def main() -> None:
    result = {}
    lines = []
    all_pass = True
    for stack in STACKS:
        arms = {}
        for arm in ("B2", "B1"):
            path = OUT / f"03-{arm}-{stack}.log"
            arms[arm] = parse(path)
        b2 = arms["B2"]
        b1 = arms["B1"]
        n1_checks = {
            "selector_structure": 0.90 <= b2["selector"]["structure"] <= 1.10,
            "gate0_structure": 0.90 <= b2["rows"]["0.00"]["structure"] <= 1.10,
            "gate4_structure": 0.90 <= b2["rows"]["4.00"]["structure"] <= 1.10,
            "gate4_retention": 0.90 <= b2["rows"]["4.00"]["retention"] <= 1.10,
        }
        p2_checks = {
            "gate0_structure": b1["rows"]["0.00"]["structure"] >= 3.0,
            "gate4_structure": b1["rows"]["4.00"]["structure"] >= 3.0,
        }
        passed = all(n1_checks.values()) and all(p2_checks.values())
        all_pass &= passed
        result[stack] = {
            "N1": n1_checks,
            "P2": p2_checks,
            "pass": passed,
            "arms": arms,
        }
        lines.extend(
            [
                f"{stack}:",
                "  N1 B2 selector/gate0/gate4 STRUCTURE = "
                f"{b2['selector']['structure']:.3f} / "
                f"{b2['rows']['0.00']['structure']:.3f} / "
                f"{b2['rows']['4.00']['structure']:.3f}; "
                f"gate4 RETENTION={b2['rows']['4.00']['retention']:.3f}; "
                f"pass={all(n1_checks.values())}",
                "  P2 B1 gate0/gate4 STRUCTURE = "
                f"{b1['rows']['0.00']['structure']:.3f} / "
                f"{b1['rows']['4.00']['structure']:.3f}; "
                f"pass={all(p2_checks.values())}",
                "  gate0 measured inflation k(L/R) = "
                f"{b2['selector']['inflation_left']:.3f}/"
                f"{b2['selector']['inflation_right']:.3f}",
            ]
        )
    result["all_pass"] = all_pass
    lines.append(f"all_pass={all_pass}")
    (OUT / "04-evaluate-real.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    text = "\n".join(lines) + "\n"
    (OUT / "04-evaluate-real.log").write_text(text, encoding="utf-8")
    print(text, end="")
    if not all_pass:
        raise SystemExit("M80 real-control bar failed")


if __name__ == "__main__":
    main()
