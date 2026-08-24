"""Reproduce M77's flat-null retention and evaluate the registered i.i.d. term.

This file is committed unrun with PREREGISTRATION.md. It reads M77's own logs,
never M77's prose table or SYNTHESIS.
"""

from __future__ import annotations

import json
import math
import pathlib
import re


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
M77_OUT = ROOT / "experiments" / "M77-gate-sweep" / "out"
OUT = HERE.parent / "out"
STACKS = ("wrapped-text-1", "wrapped-text-2")
EXPECTED = {
    "wrapped-text-1": {0.0: 9.963, 4.0: 9.188},
    "wrapped-text-2": {0.0: 8.819, 4.0: 6.791},
}

FRAME_RE = re.compile(r"^frames\s+:\s+(\d+)\s+from", re.MULTILINE)
BASE_RE = re.compile(
    r"^single frame\s+\d+\s*:\s+corrected\s+([0-9.]+)\s+"
    r"raw rms\s+([0-9.]+)\s+model noise\s+([0-9.]+)",
    re.MULTILINE,
)
ROW_RE = re.compile(
    r"^\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+\S+\s+"
    r"([0-9.]+)\s+([0-9.]+)",
    re.MULTILINE,
)


def harmonic(n: int) -> float:
    return math.fsum(1.0 / k for k in range(1, n + 1))


def parse_log(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm = FRAME_RE.search(text)
    bm = BASE_RE.search(text)
    if fm is None or bm is None:
        raise RuntimeError(f"missing frame/base row in {path}")
    rows = {}
    for gate, corrected, retention, raw_rms, model_noise in ROW_RE.findall(text):
        rows[float(gate)] = {
            "corrected": float(corrected),
            "retention_printed": float(retention),
            "raw_rms": float(raw_rms),
            "model_noise": float(model_noise),
        }
    for gate in (0.0, 4.0):
        if gate not in rows:
            raise RuntimeError(f"missing gate {gate:g} in {path}")
    return {
        "frames": int(fm.group(1)),
        "base": {
            "corrected": float(bm.group(1)),
            "raw_rms": float(bm.group(2)),
            "model_noise": float(bm.group(3)),
        },
        "rows": rows,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    result = {}
    lines = []
    passed = True
    for stack in STACKS:
        path = M77_OUT / f"07-B2-{stack}.log"
        d = parse_log(path)
        base = d["base"]
        n = d["frames"]
        h_n = harmonic(n)
        stack_out = {
            "source": str(path.relative_to(ROOT)),
            "N": n,
            "H_N": h_n,
            "sqrt_H_N": math.sqrt(h_n),
            "base": base,
            "gates": {},
        }
        lines.append(f"{stack}: N={n} H_N={h_n:.9f} sqrt(H_N)={math.sqrt(h_n):.9f}")
        for gate in (0.0, 4.0):
            row = d["rows"][gate]
            recomputed = row["corrected"] / base["corrected"]
            expected = EXPECTED[stack][gate]
            # Both corrected operands are printed to four decimals.  Propagate
            # that quantisation instead of pretending the displayed endpoints
            # are exact; the RETENTION column itself is printed from the
            # unrounded values.
            half_ulp = 0.00005
            ratio_interval = [
                (row["corrected"] - half_ulp) / (base["corrected"] + half_ulp),
                (row["corrected"] + half_ulp) / (base["corrected"] - half_ulp),
            ]
            expected_interval = [expected - 0.0005, expected + 0.0005]
            intervals_overlap = (
                ratio_interval[1] >= expected_interval[0]
                and ratio_interval[0] <= expected_interval[1]
            )
            ok = (
                abs(row["retention_printed"] - expected) <= 0.0005
                and intervals_overlap
            )
            passed &= ok
            row_out = {
                **row,
                "retention_recomputed": recomputed,
                "retention_interval_from_printed_operands": ratio_interval,
                "expected": expected,
                "R1_pass": ok,
            }
            if gate == 0.0:
                observed_excess = (
                    row["raw_rms"] ** 2
                    - row["model_noise"] ** 2
                    - base["corrected"] ** 2
                )
                analytic_excess = (h_n - 1.0) * row["model_noise"] ** 2
                signed_after = row["raw_rms"] ** 2 - h_n * row["model_noise"] ** 2
                residual_power = signed_after - base["corrected"] ** 2
                corrected_after = math.sqrt(max(0.0, signed_after))
                retention_after = corrected_after / base["corrected"]
                residual_fraction = (
                    residual_power / observed_excess
                    if observed_excess != 0.0
                    else math.nan
                )
                a1 = (
                    abs(residual_fraction) <= 0.20
                    and 0.80 <= retention_after <= 1.20
                    and signed_after > 0.0
                )
                row_out["analytic"] = {
                    "observed_selection_excess_power": observed_excess,
                    "analytic_excess_power": analytic_excess,
                    "analytic_over_observed": analytic_excess / observed_excess,
                    "signed_power_after_subtraction": signed_after,
                    "corrected_after": corrected_after,
                    "retention_after": retention_after,
                    "residual_power_vs_base": residual_power,
                    "residual_fraction_of_observed_excess": residual_fraction,
                    "A1_pass": a1,
                }
                lines.append(
                    "  gate 0 analytic: "
                    f"observed_excess={observed_excess:.6f} "
                    f"analytic={analytic_excess:.6f} "
                    f"residual={residual_power:.6f} "
                    f"residual_fraction={residual_fraction:.6f} "
                    f"retention_after={retention_after:.6f} A1={a1}"
                )
            stack_out["gates"][f"{gate:g}"] = row_out
            lines.append(
                f"  gate {gate:g}: printed={row['retention_printed']:.3f} "
                f"recomputed={recomputed:.6f} "
                f"interval=[{ratio_interval[0]:.6f},{ratio_interval[1]:.6f}] "
                f"expected={expected:.3f} R1={ok}"
            )
        result[stack] = stack_out

    result["R1_pass"] = passed
    (OUT / "01-reproduce-and-derive.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    lines.append(f"R1_pass={passed}")
    text = "\n".join(lines) + "\n"
    (OUT / "01-reproduce-and-derive.log").write_text(text, encoding="utf-8")
    print(text, end="")
    if not passed:
        raise SystemExit("R1 failed: M77 headline values did not reproduce")


if __name__ == "__main__":
    main()
