"""Turn cached M-PHASE0-CURV response curves into the registered verdict."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np

import curvlib as C
import measure


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
WIDTH = measure.VISIBLE_SHAPE[1]
HEIGHT = measure.VISIBLE_SHAPE[0]
BOOTSTRAP_REPS = 2000
BOOTSTRAP_SEED = 0xC5_2026


def json_clean(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_clean(v) for v in value]
    if isinstance(value, np.generic):
        return json_clean(value.item())
    return value


def load_curves(stack_id: str) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    manifest_path = OUT / f"{stack_id}-measure.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing {manifest_path}; run measure.py first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    npz_path = ROOT / str(manifest["response_npz"])
    if C.sha256_file(npz_path) != manifest["response_npz_sha256"]:
        raise RuntimeError(f"{stack_id}: cached response hash mismatch")
    with np.load(npz_path) as loaded:
        arrays = {key: loaded[key].copy() for key in loaded.files}
    return manifest, arrays


def extract_peaks(arrays: dict[str, np.ndarray]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    x = arrays["x_sensor"]
    y = arrays["y_sensor"]
    for site in range(len(x)):
        peak = C.peaks_for_site(
            arrays["response_g1"][:, site],
            arrays["response_g2"][:, site],
            clip_g1=arrays["clip_g1"][:, site],
            clip_g2=arrays["clip_g2"][:, site],
            mean_g1=arrays["mean_g1"][:, site],
            mean_g2=arrays["mean_g2"][:, site],
        )
        rows.append(
            {
                "site": site,
                "grid_col": site % measure.NX,
                "grid_row": site // measure.NX,
                "x_sensor": float(x[site]),
                "y_sensor": float(y[site]),
                **peak,
            }
        )
    return rows


def write_peak_csv(stack_id: str, rows: list[dict[str, object]]) -> Path:
    path = OUT / f"{stack_id}-peaks.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def arrays_from_rows(
    rows: list[dict[str, object]],
    key: str,
    field_fraction: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray([float(row["x_sensor"]) for row in rows])
    y = np.asarray([float(row["y_sensor"]) for row in rows])
    z = np.asarray([float(row[key]) for row in rows])
    valid = np.asarray([bool(row["valid"]) for row in rows])
    if field_fraction < 1.0:
        valid &= np.abs(x - WIDTH / 2.0) <= field_fraction * WIDTH / 2.0
        valid &= np.abs(y - HEIGHT / 2.0) <= field_fraction * HEIGHT / 2.0
    valid &= np.isfinite(z)
    return x[valid], y[valid], z[valid]


def complete_gate(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> dict[str, object]:
    if len(z) == 0:
        return {
            "n": 0,
            "occupied_blocks": 0,
            "conservative_v_span": 0.0,
            "enough_sites": False,
            "enough_blocks": False,
            "enough_span": False,
            "sites_v_negative": 0,
            "sites_v_positive": 0,
            "actual_v_span": 0.0,
            "enough_each_side": False,
            "pass": False,
        }
    gate = C.surface_gate(x, y, WIDTH, HEIGHT)
    side_negative = side_positive = 0
    v_span = 0.0
    if len(z) >= 12:
        preliminary = C.fit_surface(x, y, z, WIDTH, HEIGHT)
        xn, yn = C.normalised_coordinates(x, y, WIDTH, HEIGHT)
        axis = np.asarray(preliminary["gradient_unit"], dtype=float)
        v = -axis[1] * xn + axis[0] * yn
        side_negative = int(np.sum(v < 0.0))
        side_positive = int(np.sum(v > 0.0))
        v_span = float(np.ptp(v))
    gate.update(
        {
            "sites_v_negative": side_negative,
            "sites_v_positive": side_positive,
            "actual_v_span": v_span,
            "enough_each_side": side_negative >= 30 and side_positive >= 30,
        }
    )
    gate["pass"] = bool(
        gate["pass"]
        and gate["enough_each_side"]
        and v_span >= 1.2
    )
    return gate


def fit_registered(
    rows: list[dict[str, object]],
    *,
    key: str = "k_primary_avg",
    degree: int = 3,
    field_fraction: float = 1.0,
    retain_samples: bool = False,
    robust: bool = True,
) -> dict[str, object]:
    x, y, z = arrays_from_rows(rows, key, field_fraction)
    gate = complete_gate(x, y, z)
    result: dict[str, object] = {
        "key": key,
        "degree": degree,
        "field_fraction": field_fraction,
        "robust": robust,
        "gate": gate,
        "scorable": bool(gate["pass"]),
    }
    if not gate["pass"]:
        result.update(
            {
                "q_h_frames": None,
                "classification": "UNSCORABLE",
                "fit": None,
                "bootstrap": None,
            }
        )
        return result
    fit = C.fit_surface(
        x,
        y,
        z,
        WIDTH,
        HEIGHT,
        degree=degree,
        robust=robust,
    )
    bootstrap = C.block_bootstrap(
        x,
        y,
        z,
        WIDTH,
        HEIGHT,
        degree=degree,
        robust=robust,
        reps=BOOTSTRAP_REPS,
        seed=BOOTSTRAP_SEED,
    )
    classification = C.classify_interval(
        float(fit["q_h_frames"]), bootstrap["ci95"]
    )
    if not retain_samples:
        bootstrap = {k: v for k, v in bootstrap.items() if k != "q_samples"}
    result.update(
        {
            "q_h_frames": float(fit["q_h_frames"]),
            "classification": classification,
            "fit": fit,
            "bootstrap": bootstrap,
        }
    )
    return result


def summary_without_samples(result: dict[str, object]) -> dict[str, object]:
    copied = dict(result)
    if isinstance(copied.get("bootstrap"), dict):
        copied["bootstrap"] = {
            k: v for k, v in copied["bootstrap"].items() if k != "q_samples"
        }
    return copied


def shift_rows_quarter_width(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    shift = int(round(measure.NX / 4.0))
    keys = [
        "k_primary_avg",
        "k_centroid_avg",
        "k_primary_g1",
        "k_primary_g2",
        "k_centroid_g1",
        "k_centroid_g2",
        "discrete_peak",
        "curve_noise",
        "prominence_sigma",
        "adjusted_r2",
        "concave",
        "interior",
        "vertex_inside",
        "green_agreement_frames",
        "peak_clip_fraction",
        "peak_min_signal_dn",
        "valid",
    ]
    shifted = [dict(row) for row in rows]
    for key in keys:
        grid = np.asarray([row[key] for row in rows], dtype=object).reshape(
            measure.NY, measure.NX
        )
        rolled = np.roll(grid, shift=shift, axis=1).ravel()
        for row, value in zip(shifted, rolled):
            row[key] = value
    return shifted


def detected_sign(result: dict[str, object]) -> int:
    if result["classification"] not in {"MATERIAL", "DETECTED-SMALL"}:
        return 0
    q = float(result["q_h_frames"])
    return 1 if q > 0.0 else -1


def ladder_flip(results: Iterable[dict[str, object]]) -> dict[str, object]:
    rows = list(results)
    classes = [str(row["classification"]) for row in rows]
    signs = [detected_sign(row) for row in rows]
    material_negligible = "MATERIAL" in classes and "NEGLIGIBLE" in classes
    sign_flip = 1 in signs and -1 in signs
    return {
        "classes": classes,
        "detected_signs": signs,
        "material_negligible_flip": material_negligible,
        "detected_sign_flip": sign_flip,
        "flip": bool(material_negligible or sign_flip),
    }


def choose_verdict(
    stacks: dict[str, dict[str, object]],
    ladders: dict[str, list[dict[str, object]]],
    placebo: dict[str, object],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    flips = {
        name: ladder_flip(rungs)
        for name, rungs in ladders.items()
    }
    flipped = [name for name, result in flips.items() if result["flip"]]
    if flipped:
        return "NOT ROBUST", [f"registered flip in {', '.join(flipped)} ladder"]

    primary = stacks["primary-f5p6"]
    p_sign = detected_sign(primary)
    aperture = [stacks["aperture-f8"], stacks["aperture-f11"]]
    independent = [stacks["target-flat-ruler"], stacks["target-dime"]]
    if (
        primary["classification"] == "MATERIAL"
        and p_sign != 0
        and all(detected_sign(row) == p_sign for row in aperture)
        and any(detected_sign(row) == p_sign for row in independent)
    ):
        verdict = "SURVIVE"
        reasons.append("material primary replicated across aperture and target")
    elif (
        all(
            stacks[name]["classification"] == "NEGLIGIBLE"
            for name in ("primary-f5p6", "aperture-f8", "aperture-f11")
        )
        and not any(detected_sign(row) for row in independent)
    ):
        verdict = "KILL"
        reasons.append("all controlled apertures negligible; no independent detection")
    else:
        verdict = "NARROWED"
        reasons.append("registered SURVIVE and KILL replication bars were not both met")

    if bool(placebo.get("applicable")) and not bool(placebo.get("reduced_below_half")):
        verdict = "NARROWED"
        reasons.append("spatial shift retained at least half the detected magnitude")
    return verdict, reasons


def analyse_all() -> dict[str, object]:
    stack_rows: dict[str, list[dict[str, object]]] = {}
    manifests: dict[str, dict[str, object]] = {}
    peak_paths: dict[str, Path] = {}
    stack_results: dict[str, dict[str, object]] = {}
    primary_full: dict[str, object] | None = None

    for stack_id in measure.STACKS:
        print(f"peaks: {stack_id}", file=sys.stderr, flush=True)
        manifest, arrays = load_curves(stack_id)
        rows = extract_peaks(arrays)
        peak_path = write_peak_csv(stack_id, rows)
        manifests[stack_id] = manifest
        stack_rows[stack_id] = rows
        peak_paths[stack_id] = peak_path
        print(f"fit/bootstrap: {stack_id}", file=sys.stderr, flush=True)
        result = fit_registered(
            rows,
            retain_samples=stack_id == "primary-f5p6",
        )
        result["peak_csv"] = str(peak_path.relative_to(ROOT)).replace("\\", "/")
        result["peak_csv_sha256"] = C.sha256_file(peak_path)
        result["stack_id"] = stack_id
        result["role"] = manifest["role"]
        result["frames"] = manifest["frames"]
        result["active_width"] = WIDTH
        result["active_height"] = HEIGHT
        if stack_id == "primary-f5p6":
            primary_full = result
        stack_results[stack_id] = summary_without_samples(result)

    assert primary_full is not None
    primary_rows = stack_rows["primary-f5p6"]
    degree = [
        fit_registered(primary_rows, degree=d)
        if d != 3
        else summary_without_samples(primary_full)
        for d in (2, 3, 4)
    ]
    peak_estimator = [
        summary_without_samples(primary_full),
        fit_registered(primary_rows, key="k_centroid_avg"),
    ]
    field_radius = [
        fit_registered(primary_rows, field_fraction=f)
        if f != 1.0
        else summary_without_samples(primary_full)
        for f in (0.6, 0.8, 1.0)
    ]
    green = [
        fit_registered(primary_rows, key="k_primary_g1"),
        fit_registered(primary_rows, key="k_primary_g2"),
        summary_without_samples(primary_full),
    ]
    ordinary_least_squares = fit_registered(primary_rows, robust=False)

    shifted = fit_registered(shift_rows_quarter_width(primary_rows))
    if primary_full["classification"] in {"MATERIAL", "DETECTED-SMALL"} and shifted[
        "scorable"
    ]:
        ratio = abs(float(shifted["q_h_frames"])) / max(
            abs(float(primary_full["q_h_frames"])), 1e-12
        )
        placebo = {
            "applicable": True,
            "shift_columns": int(round(measure.NX / 4.0)),
            "shifted": shifted,
            "absolute_q_ratio": ratio,
            "reduced_below_half": ratio < 0.5,
        }
    else:
        placebo = {
            "applicable": False,
            "shift_columns": int(round(measure.NX / 4.0)),
            "shifted": shifted,
            "absolute_q_ratio": None,
            "reduced_below_half": None,
        }

    ladders = {
        "aperture": [
            stack_results["primary-f5p6"],
            stack_results["aperture-f8"],
            stack_results["aperture-f11"],
        ],
        "target": [
            stack_results["primary-f5p6"],
            stack_results["target-flat-ruler"],
            stack_results["target-dime"],
            stack_results["grid-1-sw1"],
            stack_results["grid-1-sw4"],
            stack_results["grid-1-sw10"],
            stack_results["grid-2-sw4"],
            stack_results["grid-2-sw10"],
        ],
        "degree": degree,
        "peak-estimator": peak_estimator,
        "field-radius": field_radius,
        "green-replicate": green,
    }
    verdict, verdict_reasons = choose_verdict(stack_results, ladders, placebo)
    results = {
        "schema": 1,
        "verdict": verdict,
        "verdict_reasons": verdict_reasons,
        "primary": primary_full,
        "stacks": stack_results,
        "sensitivities": {
            "degree": degree,
            "peak_estimator": peak_estimator,
            "field_radius": field_radius,
            "green": green,
            "ordinary_least_squares": ordinary_least_squares,
        },
        "spatial_shift_placebo": placebo,
        "ladder_checks": {
            name: ladder_flip(rungs) for name, rungs in ladders.items()
        },
        "measurement_manifests": {
            stack_id: {
                "path": f"out/{stack_id}-measure.json",
                "response_sha256": manifest["response_npz_sha256"],
                "frames": manifest["frames"],
            }
            for stack_id, manifest in manifests.items()
        },
        "commission": {
            "path": "out/commission.json",
            "sha256": C.sha256_file(OUT / "commission.json"),
        },
        "bootstrap_reps": BOOTSTRAP_REPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    clean = json_clean(results)
    (OUT / "results.json").write_text(
        json.dumps(clean, indent=2) + "\n", encoding="utf-8"
    )
    return clean  # type: ignore[return-value]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = analyse_all()
    primary = result["primary"]
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "q_h_frames": primary["q_h_frames"],
                "ci95": None
                if primary["bootstrap"] is None
                else primary["bootstrap"]["ci95"],
                "classification": primary["classification"],
                "valid_sites": primary["gate"]["n"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
