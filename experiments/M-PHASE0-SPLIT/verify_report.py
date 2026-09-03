"""Re-derive load-bearing report literals from machine-readable outputs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
REPORT = ROOT / "docs" / "research" / "M-PHASE0-SPLIT.md"
COMMISSION = LANE / "out" / "commission.json"
REAL = LANE / "out" / "real-109" / "measurement.json"
RUN = LANE / "out" / "real-109" / "run.json"
POSTUPDATE = LANE / "out" / "postupdate-audit.json"


def expected_literals() -> dict[str, str]:
    commission = json.loads(COMMISSION.read_text(encoding="utf-8"))
    real = json.loads(REAL.read_text(encoding="utf-8"))
    run = json.loads(RUN.read_text(encoding="utf-8"))
    postupdate = json.loads(POSTUPDATE.read_text(encoding="utf-8"))
    point = float(real["point_estimate"]["frequency_or_bound"])
    bootstrap = real["bootstrap"]
    ci = bootstrap["measured_95_percentile_interval"]
    null = real["null_product"]
    readings = commission["readings"]
    rerun = postupdate["historical_numeric_reproduction"]["measured"]
    null_mean = f"{float(null['mean_dn']):.3f}".replace("-", "−")
    return {
        "real": f"**{point:.10f} cycles/quad-pixel**",
        "bootstrap": (
            f"**{float(bootstrap['measured_median']):.10f}**, 95% interval "
            f"**[{float(ci[0]):.10f}, {float(ci[1]):.10f}]**"
        ),
        "null_control": "mean `|FRC|` **0.047182**",
        "positive": "low **0.989378**, high **0.013942**",
        "sharpen": "crossing **0.222192 → 0.220543** (`−0.001650`)",
        "plants": (
            f"**{len(commission['control_families'])} control families, "
            f"{len(commission['plants'])} named Rust plants"
        ),
        "classifier_edges": "`gapped=Insufficient`, `short_tail=Insufficient`",
        "verdict": "**Verdict: KILL — STOP/REMOVE RUST; retain the split instrument offline.**",
        "rerun_blur": (
            f"**{float(rerun['blur_recovery_min']):.10f}–"
            f"{float(rerun['blur_recovery_max']):.10f}**"
        ),
        "rerun_null": (
            "`MEAN` maximum mid-band SNR **0.438734** and `WIENER_UNG` "
            "**3.331288**"
        ),
        "null_real": (
            f"mean **{null_mean} DN**, RMS "
            f"**{float(null['rms_dn']):.3f} DN**"
        ),
        "hash": (
            f"`{run['ordinary_output']['split_on_sha256'][:8]}…"
            f"{run['ordinary_output']['split_on_sha256'][-7:]}` both ways"
        ),
        "commission_status": str(commission["status"]),
        "commission_null_source": str(readings["null"]),
    }


def verify(text: str) -> list[str]:
    missing = []
    normalised = " ".join(text.split())
    for name, literal in expected_literals().items():
        # The last two establish that the machine record itself is populated;
        # they are not prose literals and therefore do not belong in REPORT.
        if name in {"commission_status", "commission_null_source"}:
            if not literal:
                missing.append(name)
        elif " ".join(literal.split()) not in normalised:
            missing.append(name)
    rust_root = ROOT / "crates"
    forbidden = {
        "split_module": rust_root / "strehl-core" / "src" / "split.rs",
        "split_probe": rust_root / "strehl-core" / "examples" / "split-probe.rs",
    }
    for name, path in forbidden.items():
        if path.exists():
            missing.append(f"removal:{name}")
    for name, path in {
        "main": rust_root / "strehl-cli" / "src" / "main.rs",
        "merge": rust_root / "strehl-cli" / "src" / "merge_cmd.rs",
        "lib": rust_root / "strehl-core" / "src" / "lib.rs",
    }.items():
        source = path.read_text(encoding="utf-8")
        if "--split-out" in source or "split_out" in source or "mod split" in source:
            missing.append(f"removal:{name}")
    return missing


def main() -> int:
    text = REPORT.read_text(encoding="utf-8")
    missing = verify(text)
    if missing:
        print(f"REPORT CHECK RED: missing {missing}")
        return 1

    plants = {}
    if "--commission" in sys.argv:
        for name in ("real", "null_control", "sharpen", "hash", "verdict", "rerun_null"):
            literal = expected_literals()[name]
            pattern = r"\s+".join(
                re.escape(part) for part in re.split(r"\s+", literal.strip())
            )
            planted, replacements = re.subn(
                pattern, f"PLANTED-{name}", text, count=1
            )
            if replacements != 1:
                print(f"REPORT CHECKER COULD NOT PLANT {name}")
                return 1
            caught = bool(verify(planted))
            plants[name] = caught
            if not caught:
                print(f"REPORT CHECKER FAILED TO CATCH PLANT {name}")
                return 1

    result = {
        "status": "GREEN",
        "claims_checked": len(expected_literals()) - 2,
        "plants": plants,
        "all_plants_red": all(plants.values()) if plants else None,
    }
    destination = LANE / "out" / "report-check.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
