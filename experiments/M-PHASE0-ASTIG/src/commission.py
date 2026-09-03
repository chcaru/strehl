"""Commission every M-PHASE0-ASTIG instrument before real measurement."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
sys.path.insert(0, str(HERE))

import astiglib as A  # noqa: E402
import fixed_predicate as F  # noqa: E402
import truth_factory as T  # noqa: E402


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT.parents[1],
        text=True,
    ).strip()


def measured_delta(
    delta: float,
    sector: str,
    *,
    centre: float = 9.0,
    frames: int = 19,
    size: int = 128,
    seed: int = 20260902,
    noise_sd: float = 3.0,
    bootstraps: int = 0,
    defect: str | None = None,
) -> dict:
    cube, truth = T.oriented_cube(
        delta,
        sector=sector,
        centre=centre,
        frames=frames,
        size=size,
        seed=seed,
        noise_sd=noise_sd,
    )
    estimate = A.measure_cube(
        cube,
        sector,
        bootstraps=bootstraps,
        seed=A.BOOTSTRAP_SEED + seed % 10_000,
        defect=defect,
    )
    return {"truth": truth, "estimate": estimate}


def p1_known_split(defect: str | None = None) -> tuple[bool, dict]:
    rows = {}
    for i, sector in enumerate(A.SECTORS):
        rows[sector] = measured_delta(
            4.0,
            sector,
            seed=20260910 + i,
            bootstraps=600,
            defect=defect,
        )
    readings = [
        row["estimate"]["delta"]
        for row in rows.values()
        if row["estimate"].get("valid_after_uncertainty")
    ]
    passed = len(readings) == 4 and max(abs(x - 4.0) for x in readings) <= 0.20
    return passed, {
        "criterion": "four sectors recover planted +4.00 within 0.20 frame",
        "readings": readings,
        "estimator_full_effect_mean": float(np.mean(readings)) if readings else None,
        "rows": rows,
    }


def p2_dose_ladder(defect: str | None = None) -> tuple[bool, dict]:
    doses = (0.0, 1.0, 2.0, 4.0)
    readings = []
    rows = []
    for i, dose in enumerate(doses):
        row = measured_delta(
            dose,
            "right",
            seed=20260930 + i,
            defect=defect,
        )
        rows.append(row)
        readings.append(row["estimate"]["delta"])
    readable = all(x is not None for x in readings)
    expected = []
    errors = []
    if readable:
        full = float(readings[-1])
        expected = [full * d / 4.0 for d in doses]
        errors = [abs(float(x) - e) for x, e in zip(readings, expected)]
        limits = [0.10, 0.10, max(0.10, 0.10 * expected[2]), max(0.10, 0.10 * full)]
        passed = (
            all(float(a) < float(b) for a, b in zip(readings[:-1], readings[1:]))
            and abs(float(readings[0])) < 0.10
            and all(e <= lim for e, lim in zip(errors, limits))
        )
    else:
        passed = False
    return passed, {
        "criterion": "0/1/2/4 readings monotone and track calibrated full reading",
        "doses": list(doses),
        "readings": readings,
        "calibrated_expected": expected,
        "absolute_errors": errors,
        "rows": rows,
    }


def common_shift(sector: str, radius: float = 0.90) -> float:
    x = radius if sector == "right" else -radius if sector == "left" else 0.0
    return 6.0 * x + 3.0 * radius * radius


def p3_curvature_rejection(defect: str | None = None) -> tuple[bool, dict]:
    rows = {}
    passed = True
    for i, sector in enumerate(A.SECTORS):
        shift = common_shift(sector)
        base = measured_delta(
            4.0,
            sector,
            centre=20.0,
            frames=49,
            size=96,
            seed=20261010 + i,
            noise_sd=2.0,
            defect=defect,
        )
        moved = measured_delta(
            4.0,
            sector,
            centre=20.0 + shift,
            frames=49,
            size=96,
            seed=20261010 + i,
            noise_sd=2.0,
            defect=defect,
        )
        b = base["estimate"]
        m = moved["estimate"]
        if b["delta"] is None or m["delta"] is None:
            item_ok = False
            delta_change = mu_change = mu_error = None
        else:
            delta_change = float(m["delta"] - b["delta"])
            mu_change = float(m["mu"] - b["mu"])
            mu_error = float(mu_change - shift)
            item_ok = (
                abs(delta_change) < 0.10
                and abs(mu_error) <= max(0.05, 0.05 * abs(shift))
            )
        passed = passed and item_ok
        rows[sector] = {
            "common_shift": shift,
            "delta_change": delta_change,
            "mu_change": mu_change,
            "mu_error": mu_error,
            "passed": item_ok,
            "base": base,
            "moved": moved,
        }
    return passed, {
        "criterion": "6-frame ramp + 3-frame bowl moves mu within 5% and delta <0.10",
        "rows": rows,
    }


def p4_cardinal_mapping(defect: str | None = None) -> tuple[bool, dict]:
    readings = {}
    for i, sector in enumerate(A.SECTORS):
        row = measured_delta(4.0, sector, seed=20261030 + i, defect=defect)
        readings[sector] = row["estimate"]["delta"]
    vals = [x for x in readings.values() if x is not None]
    passed = (
        len(vals) == 4
        and all(x > 0 for x in vals)
        and max(vals) - min(vals) < 0.20
    )
    return passed, {
        "criterion": "all cardinal sectors same positive sign, range <0.20 frame",
        "readings": readings,
        "range": float(max(vals) - min(vals)) if len(vals) == 4 else None,
    }


def p5_axis_reversal(defect: str | None = None) -> tuple[bool, dict]:
    cube, truth = T.oriented_cube(
        4.0,
        sector="right",
        centre=9.0,
        frames=19,
        seed=20261050,
        noise_sd=2.0,
    )
    forward = A.measure_cube(cube, "right", bootstraps=0, defect=defect)
    reverse = A.measure_cube(cube[::-1], "right", bootstraps=0, defect=defect)
    total = (
        None
        if forward["delta"] is None or reverse["delta"] is None
        else float(forward["delta"] + reverse["delta"])
    )
    passed = total is not None and abs(total) < 0.10
    return passed, {
        "criterion": "reversing focus order flips delta; forward + reverse <0.10",
        "truth": truth,
        "forward": forward,
        "reverse": reverse,
        "sum": total,
    }


def p6_flat_refusal(defect: str | None = None) -> tuple[bool, dict]:
    cube, truth = T.oriented_cube(
        0.0,
        flat=True,
        sector="right",
        centre=9.0,
        frames=19,
        seed=20261060,
        noise_sd=8.0,
    )
    result = A.measure_cube(cube, "right", bootstraps=0, defect=defect)
    passed = not result["valid"]
    return passed, {
        "criterion": "flat noisy cube must refuse rather than return a split",
        "truth": truth,
        "estimate": result,
    }


def p7_external_predicate(defect: str | None = None) -> tuple[bool, dict]:
    fit_defect = "integer-argmax" if defect == "integer-argmax" else None
    p1 = A.fit_log_peak(
        F.CURVE_1,
        baseline=0.0,
        apply_gates=True,
        defect=fit_defect,
    )
    p2 = A.fit_log_peak(
        F.CURVE_2,
        baseline=0.0,
        apply_gates=True,
        defect=fit_defect,
    )
    split = (
        None
        if p1.z is None or p2.z is None
        else float(p2.z - p1.z)
    )
    passed = (
        p1.valid
        and p2.valid
        and split is not None
        and abs(split - F.SPLIT) <= F.TOLERANCE
    )
    return passed, {
        "criterion": "literal external curves recover 4.125 +/- 0.02",
        "fixed_peaks": [F.PEAK_1, F.PEAK_2],
        "fixed_split": F.SPLIT,
        "tolerance": F.TOLERANCE,
        "peak_1": as_plain(p1),
        "peak_2": as_plain(p2),
        "split": split,
        "input_source": "fixed_predicate.py literals; estimator never generated them",
    }


def as_plain(value) -> dict:
    return {
        field: getattr(value, field)
        for field in (
            "valid",
            "z",
            "index",
            "offset",
            "baseline",
            "prominence",
            "log_curvature",
            "reason",
        )
    }


def p8_uncertainty(defect: str | None = None) -> tuple[bool, dict]:
    pairs, truth = T.response_blocks(1.0, datasets=100)
    points = []
    reported = []
    coverage = 0
    valid = 0
    rows = []
    for i, (ex, ey) in enumerate(pairs):
        stats = A.response_block_stats(ex, ey)
        result = A.measure_stats(
            stats,
            "right",
            bootstraps=500,
            seed=A.BOOTSTRAP_SEED + i,
            defect=defect,
        )
        ok = bool(result.get("valid_after_uncertainty"))
        if ok:
            valid += 1
            points.append(float(result["delta"]))
            b = result["bootstrap"]["delta"]
            reported.append(float(b["sd"]))
            covered = b["lo95"] <= truth["delta"] <= b["hi95"]
            coverage += int(covered)
            rows.append(
                {
                    "index": i,
                    "delta": result["delta"],
                    "sd": b["sd"],
                    "lo95": b["lo95"],
                    "hi95": b["hi95"],
                    "covered": covered,
                }
            )
    empirical_sd = float(np.std(points, ddof=1)) if len(points) > 1 else None
    median_se = float(np.median(reported)) if reported else None
    ratio = (
        empirical_sd / median_se
        if empirical_sd is not None and median_se not in (None, 0.0)
        else None
    )
    passed = (
        valid == 100
        and 90 <= coverage <= 99
        and ratio is not None
        and 0.8 <= ratio <= 1.25
    )
    return passed, {
        "criterion": "100 valid; coverage 90..99; empirical SD / median SE 0.8..1.25",
        "truth": truth,
        "valid": valid,
        "coverage": coverage,
        "empirical_sd": empirical_sd,
        "median_reported_se": median_se,
        "sd_over_se": ratio,
        "rows": rows,
    }


CONTROLS = (
    ("P1-known-split", p1_known_split, "pool-arms"),
    ("P2-dose-ladder", p2_dose_ladder, "constant-plus-one"),
    ("P3-curvature-rejection", p3_curvature_rejection, "global-reference"),
    ("P4-cardinal-mapping", p4_cardinal_mapping, "no-vertical-swap"),
    ("P5-axis-reversal", p5_axis_reversal, "absolute-delta"),
    ("P6-flat-refusal", p6_flat_refusal, "force-flat"),
    ("P7-external-predicate", p7_external_predicate, "integer-argmax"),
    ("P8-uncertainty", p8_uncertainty, "independent-bootstrap"),
)


def main() -> None:
    records = []
    for name, function, plant in CONTROLS:
        clean_pass, clean = function()
        planted_pass, planted = function(plant)
        record = {
            "id": name,
            "plant": plant,
            "clean_status": "PASS" if clean_pass else "FAIL",
            "plant_status": "MISSED" if planted_pass else "RED",
            "clean": clean,
            "planted": planted,
        }
        records.append(record)
        print(
            f"{name:24s} clean={record['clean_status']:4s} "
            f"plant({plant})={record['plant_status']}"
        )

    clean_passes = sum(r["clean_status"] == "PASS" for r in records)
    red = sum(r["plant_status"] == "RED" for r in records)
    result = {
        "schema_version": 1,
        "role": "commissioning before any real-effect estimate",
        "provenance": {
            "git_head": git_head(),
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "invocation": (
                "PYTHONIOENCODING=utf-8; "
                "PYTHONPATH=<repo>\\experiments\\M-PHASE0-ASTIG\\src; "
                "python experiments\\M-PHASE0-ASTIG\\src\\commission.py"
            ),
            "source_sha256": {
                p.name: file_sha256(p)
                for p in (
                    HERE / "astiglib.py",
                    HERE / "truth_factory.py",
                    HERE / "fixed_predicate.py",
                    Path(__file__),
                )
            },
        },
        "tally": {
            "controls": len(records),
            "clean_pass": clean_passes,
            "clean_fail": len(records) - clean_passes,
            "plants": len(records),
            "red": red,
            "missed": len(records) - red,
        },
        "records": records,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "commission.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"tally: PASS {clean_passes}/{len(records)}, "
        f"plants RED {red}/{len(records)}"
    )
    print(f"wrote {target}")
    if clean_passes != len(records) or red != len(records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
