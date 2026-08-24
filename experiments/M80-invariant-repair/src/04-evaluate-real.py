"""Apply M80's refined pre-registered D1 bars to the four real-ROI runs."""

from __future__ import annotations

import json
import pathlib
import re


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parent / "out"
STACKS = ("wrapped-text-1", "wrapped-text-2")
SELECTOR_RE = re.compile(
    r"^selector gate 0\s+:\s+q\s+([+-][0-9.]+)\s+\+/-\s+([0-9.]+)\s+"
    r"DN\^2\s+z\s+([+-][0-9.]+)\s+target\s+(\S+)\s+"
    r"STRUCTURE\s+([0-9.]+)x.*?k\(L/R\)\s+([0-9.]+)/\s*([0-9.]+)",
    re.MULTILINE,
)
ROW_RE = re.compile(
    r"^\s+([0-9.]+)\s+([+-][0-9.]+)\s+"
    r"(?:(?P<retention>[0-9.]+)x\s+(?P<verdict>\S+)|"
    r"(?P<na>N/A)\s+(?P<no_target>NO TARGET))\s+"
    r"([0-9.]+)x\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)",
    re.MULTILINE,
)


def parse(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sm = SELECTOR_RE.search(text)
    if sm is None:
        raise RuntimeError(f"missing selector row in {path}")
    rows = {}
    for match in ROW_RE.finditer(text):
        gate = match.group(1)
        q = match.group(2)
        retention = match.group("retention")
        verdict = match.group("verdict")
        if match.group("na") is not None:
            retention = None
            verdict = match.group("no_target")
        structure, raw, control, k_l, k_r = match.groups()[-5:]
        rows[gate] = {
            "q_signal_power": float(q),
            "retention": None if retention is None else float(retention),
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
            "signal_standard_error": float(sm.group(2)),
            "z": float(sm.group(3)),
            "target": sm.group(4),
            "structure": float(sm.group(5)),
            "inflation_left": float(sm.group(6)),
            "inflation_right": float(sm.group(7)),
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
            "selector_not_measurable": b2["selector"]["target"] == "NOT-MEASURABLE",
            "all_retentions_na": all(
                row["retention"] is None and row["verdict"] == "NO TARGET"
                for row in b2["rows"].values()
            ),
            "selector_structure": 0.90 <= b2["selector"]["structure"] <= 1.10,
            "gate0_structure": 0.90 <= b2["rows"]["0.00"]["structure"] <= 1.10,
            "gate4_structure": 0.90 <= b2["rows"]["4.00"]["structure"] <= 1.10,
        }
        p2_checks = {
            "selector_measurable": b1["selector"]["target"] == "MEASURABLE",
            "gate0_retention_numeric": b1["rows"]["0.00"]["retention"] is not None,
            "gate4_retention_numeric": b1["rows"]["4.00"]["retention"] is not None,
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
                f"target={b2['selector']['target']}; gate4 RETENTION=N/A; "
                f"pass={all(n1_checks.values())}",
                "  P2 B1 gate0/gate4 STRUCTURE = "
                f"{b1['rows']['0.00']['structure']:.3f} / "
                f"{b1['rows']['4.00']['structure']:.3f}; "
                f"target={b1['selector']['target']}; "
                f"gate4 RETENTION={b1['rows']['4.00']['retention']:.3f}; "
                f"pass={all(p2_checks.values())}",
                "  selector q/se/z B2 = "
                f"{b2['selector']['q_signal_power']:+.3f}/"
                f"{b2['selector']['signal_standard_error']:.3f}/"
                f"{b2['selector']['z']:+.3f}",
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
