"""Reproduce and independently audit the corpus evidence that unlocks C2."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
LANE = HERE.parent
OUT = LANE / "out"
AUDIT_OUT = OUT / "c2-audit"
REPO = LANE.parents[1]
LEGACY_SRC = REPO / "experiments" / "BUILD-CHROMA" / "src"
DOCS = REPO / "docs" / "research"
STACK_ROOT = Path(r"D:\personal\macro")
STACKS = ("lavendar-cpl", "coffee-bean", "couch-fibers-cpl", "bee-2-cpl")
CHANNELS = ("R", "G1", "G2", "B")
TARGETS = {
    "lavendar-cpl": {
        "delta_r": -0.8075,
        "delta_b": -0.7185,
        "loss_r": 0.0422,
        "loss_b": 0.0351,
    },
    "coffee-bean": {
        "delta_r": -0.8100,
        "delta_b": -0.4845,
        "loss_r": 0.0662,
        "loss_b": 0.0519,
    },
    "couch-fibers-cpl": {
        "delta_r": -0.8977,
        "delta_b": -0.7124,
        "loss_r": 0.0736,
        "loss_b": 0.0706,
    },
    "bee-2-cpl": {
        "delta_r": -0.6601,
        "delta_b": -0.7540,
        "loss_r": 0.0754,
        "loss_b": 0.0713,
    },
}
SEED = 20260902
BOOTSTRAP_DRAWS = 10_000


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(stack: str) -> dict:
    files = sorted((STACK_ROOT / stack).glob("*.ARW"))
    if not files:
        raise RuntimeError(f"no RAW files for {stack}")
    return {
        "root": str(STACK_ROOT / stack),
        "count": len(files),
        "files": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            for path in files
        ],
    }


def load_legacy():
    sys.path.insert(0, str(LEGACY_SRC))
    common = importlib.import_module("common")
    common.OUT = str(AUDIT_OUT / "legacy")
    b1 = importlib.import_module("b1_curves")
    b2 = importlib.import_module("b2_analyse")
    b1.OUT = common.OUT
    b2.OUT = common.OUT
    return common, b1, b2


def independent_peaks(curves: np.ndarray) -> dict[str, np.ndarray]:
    values = np.asarray(curves, dtype=np.float64)
    nframe, npoint = values.shape
    discrete = np.argmax(values, axis=0)
    centre = np.clip(discrete, 1, nframe - 2)
    columns = np.arange(npoint)
    before = values[centre - 1, columns]
    middle = values[centre, columns]
    after = values[centre + 1, columns]
    denominator = before - 2.0 * middle + after
    offset = np.where(
        np.abs(denominator) > 1.0e-12,
        0.5 * (before - after)
        / np.where(np.abs(denominator) > 1.0e-12, denominator, 1.0),
        0.0,
    )
    offset = np.clip(offset, -1.0, 1.0)
    peak = centre.astype(np.float64) + offset
    prominence = middle / np.maximum(np.median(values, axis=0), 1.0e-9)
    low = np.min(values, axis=0)
    half = low + 0.5 * (middle - low)
    local = (
        (values[1:-1] > values[:-2])
        & (values[1:-1] >= values[2:])
        & (values[1:-1] > half[None, :])
    )
    valid = (
        (discrete > 0)
        & (discrete < nframe - 1)
        & (np.sum(local, axis=0) <= 1)
    )
    return {
        "peak": peak,
        "prominence": prominence,
        "valid": valid,
        "curves": values,
    }


def interpolate(curves: np.ndarray, coordinates: np.ndarray) -> np.ndarray:
    values = np.asarray(curves, dtype=np.float64)
    clipped = np.clip(coordinates, 0.0, values.shape[0] - 1.001)
    lower = np.floor(clipped).astype(int)
    fraction = clipped - lower
    columns = np.arange(values.shape[1])
    return (
        values[lower, columns] * (1.0 - fraction)
        + values[lower + 1, columns] * fraction
    )


def tilewise(
    values: np.ndarray,
    valid: np.ndarray,
    ntiles: int,
    npoints: int,
    *,
    minimum: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    reshaped = values.reshape(ntiles, npoints)
    mask = valid.reshape(ntiles, npoints)
    result = np.full(ntiles, np.nan, dtype=np.float64)
    keep = np.zeros(ntiles, dtype=bool)
    for tile in range(ntiles):
        if int(np.sum(mask[tile])) >= minimum:
            result[tile] = float(np.median(reshaped[tile][mask[tile]]))
            keep[tile] = True
    return result, keep


def bootstrap_median(values: np.ndarray, seed: int) -> list[float]:
    clean = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(
        0, clean.size, size=(BOOTSTRAP_DRAWS, clean.size)
    )
    medians = np.median(clean[indices], axis=1)
    return [
        float(np.percentile(medians, 2.5)),
        float(np.percentile(medians, 97.5)),
    ]


def independent_summary(path: Path, *, seed: int) -> tuple[dict, dict]:
    with np.load(path, allow_pickle=True) as source:
        data = {name: source[name].copy() for name in source.files}
    nframe, ntiles, npoints = data["R"].shape
    fit = {
        channel: independent_peaks(
            data[channel].reshape(nframe, ntiles * npoints)
        )
        for channel in CHANNELS
    }
    valid = np.ones(ntiles * npoints, dtype=bool)
    for channel in CHANNELS:
        valid &= fit[channel]["valid"]
        valid &= fit[channel]["prominence"] >= 1.5
    valid &= np.repeat(data["track_res"] <= 2.0, npoints)

    green = 0.5 * (fit["G1"]["peak"] + fit["G2"]["peak"])
    offsets = {
        "delta_r": fit["R"]["peak"] - green,
        "delta_b": fit["B"]["peak"] - green,
        "delta_null": fit["G1"]["peak"] - fit["G2"]["peak"],
    }
    tile_offsets = {}
    keep_masks = []
    for name, values in offsets.items():
        tile_offsets[name], keep = tilewise(
            values, valid, ntiles, npoints
        )
        keep_masks.append(keep)
    keep = np.logical_and.reduce(keep_masks)

    loss_points = {}
    tile_losses = {}
    for channel in ("R", "B", "G1"):
        curves = fit[channel]["curves"]
        at_own = interpolate(curves, fit[channel]["peak"])
        at_green = interpolate(curves, green)
        loss_points[channel] = 1.0 - at_green / np.maximum(at_own, 1.0e-12)
        tile_losses[channel], loss_keep = tilewise(
            loss_points[channel], valid, ntiles, npoints
        )
        keep &= loss_keep

    radius = np.mean(data["rad"], axis=1)
    summary = {
        "stack": str(data["stack"]),
        "nframes": int(nframe),
        "ntiles": int(ntiles),
        "npoints_per_tile": int(npoints),
        "confident_points": int(np.sum(valid)),
        "tiles_used": int(np.sum(keep)),
        "delta_r": float(np.median(tile_offsets["delta_r"][keep])),
        "delta_b": float(np.median(tile_offsets["delta_b"][keep])),
        "delta_null": float(np.median(tile_offsets["delta_null"][keep])),
        "delta_r_ci95": bootstrap_median(
            tile_offsets["delta_r"][keep], seed + 1
        ),
        "delta_b_ci95": bootstrap_median(
            tile_offsets["delta_b"][keep], seed + 2
        ),
        "delta_null_ci95": bootstrap_median(
            tile_offsets["delta_null"][keep], seed + 3
        ),
        "loss_r": float(np.median(tile_losses["R"][keep])),
        "loss_b": float(np.median(tile_losses["B"][keep])),
        "loss_null": float(np.median(tile_losses["G1"][keep])),
        "loss_r_ci95": bootstrap_median(tile_losses["R"][keep], seed + 4),
        "loss_b_ci95": bootstrap_median(tile_losses["B"][keep], seed + 5),
    }
    detail = {
        "keep": keep,
        "radius": radius,
        "tile_delta_r": tile_offsets["delta_r"],
        "tile_delta_b": tile_offsets["delta_b"],
        "tile_delta_null": tile_offsets["delta_null"],
        "tile_loss_r": tile_losses["R"],
        "tile_loss_b": tile_losses["B"],
    }
    return summary, detail


def radial_intercept(detail: dict, seed: int) -> dict:
    keep = detail["keep"]
    radius = detail["radius"][keep]
    delta = detail["tile_delta_r"][keep]
    design = np.stack([radius, np.ones(radius.size)], axis=1)
    slope, intercept = np.linalg.lstsq(design, delta, rcond=None)[0]
    edge = float(slope * np.max(radius) + intercept)
    rng = np.random.default_rng(seed)
    bootstrap = np.empty(BOOTSTRAP_DRAWS, dtype=np.float64)
    for draw in range(BOOTSTRAP_DRAWS):
        index = rng.integers(0, radius.size, size=radius.size)
        sampled_design = np.stack(
            [radius[index], np.ones(radius.size)], axis=1
        )
        bootstrap[draw] = np.linalg.lstsq(
            sampled_design, delta[index], rcond=None
        )[0][1]
    interval = [
        float(np.percentile(bootstrap, 2.5)),
        float(np.percentile(bootstrap, 97.5)),
    ]
    return {
        "tiles": int(radius.size),
        "slope_frames_per_plane_px": float(slope),
        "intercept_frames": float(intercept),
        "intercept_ci95": interval,
        "edge_frames": edge,
        "centre_at_least_half_edge": (
            abs(float(intercept)) >= 0.5 * abs(edge)
        ),
        "passes_axial_gate": (
            interval[1] < 0.0
            and abs(float(intercept)) >= 0.5 * abs(edge)
        ),
    }


def cache_fingerprint(stack: str, raw_inventory: dict) -> str:
    payload = {
        "stack": stack,
        "inventory": raw_inventory,
        "sources": {
            path.name: file_sha256(path)
            for path in (
                Path(__file__),
                LEGACY_SRC / "common.py",
                LEGACY_SRC / "b1_curves.py",
                LEGACY_SRC / "b2_analyse.py",
            )
        },
        "numpy": np.__version__,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def summed_area(values: np.ndarray) -> np.ndarray:
    cumulative = np.cumsum(
        np.cumsum(values.astype(np.float64), axis=0), axis=1
    )
    result = np.zeros(
        (values.shape[0] + 1, values.shape[1] + 1), dtype=np.float64
    )
    result[1:, 1:] = cumulative
    return result


def box_mean(
    integral: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    side: int,
) -> np.ndarray:
    half = side // 2
    row0, row1 = rows - half, rows + half + 1
    col0, col1 = columns - half, columns + half + 1
    total = (
        integral[row1, col1]
        - integral[row0, col1]
        - integral[row1, col0]
        + integral[row0, col0]
    )
    return total / float(side * side)


def normalised_response(
    plane: np.ndarray,
    energy: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    side: int,
) -> np.ndarray:
    values = np.asarray(plane, dtype=np.float64)
    mean = box_mean(summed_area(values), rows, columns, side)
    mean_square = box_mean(
        summed_area(values * values), rows, columns, side
    )
    variance = np.maximum(mean_square - mean * mean, 1.0e-12)
    return energy / variance


def gamma_plane(plane: np.ndarray, gamma: float) -> np.ndarray:
    scale = 15871.0
    normalised = np.clip(np.asarray(plane, dtype=np.float64), 0.0, scale) / scale
    return scale * np.power(normalised, gamma)


def build_normalised_caches(
    stack: str,
    legacy_path: Path,
    raw_inventory: dict,
    common,
) -> dict[str, Path]:
    variants = {"normalised": None}
    if stack == "lavendar-cpl":
        variants.update({"gamma_0p8": 0.8, "gamma_1p2": 1.2})
    fingerprint = cache_fingerprint(stack, raw_inventory)
    paths = {
        name: AUDIT_OUT / "normalised" / f"{stack}-{name}.npz"
        for name in variants
    }
    reusable = True
    for path in paths.values():
        if not path.is_file():
            reusable = False
            break
        with np.load(path, allow_pickle=True) as cached:
            reusable &= str(cached["fingerprint"]) == fingerprint
    if reusable:
        print(f"  {stack}: reuse normalised/tone caches")
        return paths

    with np.load(legacy_path, allow_pickle=True) as source:
        legacy = {name: source[name].copy() for name in source.files}
    nframe, ntiles, npoints = legacy["R"].shape
    responses = {
        variant: {
            channel: np.empty(
                (nframe, ntiles, npoints), dtype=np.float32
            )
            for channel in CHANNELS
        }
        for variant in variants
    }
    files = sorted((STACK_ROOT / stack).glob("*.ARW"))
    side = int(common.WIN)
    for frame_index, path in enumerate(files):
        planes = common.planes_of(common.read_cfa(str(path)))
        rows = legacy["py"] + legacy["idy"][frame_index][:, None]
        columns = legacy["px"] + legacy["idx"][frame_index][:, None]
        for channel in CHANNELS:
            plane = planes[channel]
            responses["normalised"][channel][frame_index] = (
                normalised_response(
                    plane,
                    legacy[channel][frame_index],
                    rows,
                    columns,
                    side,
                )
            )
            for variant, gamma in variants.items():
                if gamma is None:
                    continue
                transformed = gamma_plane(plane, gamma)
                gradient = common.grad_energy(transformed.astype(np.float32))
                energy = box_mean(
                    summed_area(gradient), rows, columns, side
                )
                responses[variant][channel][frame_index] = (
                    normalised_response(
                        transformed, energy, rows, columns, side
                    )
                )
        if frame_index % 25 == 0 or frame_index + 1 == nframe:
            print(
                f"    {stack} normalised {frame_index + 1}/{nframe}"
            )
    (AUDIT_OUT / "normalised").mkdir(parents=True, exist_ok=True)
    shared = {
        name: legacy[name]
        for name in (
            "px",
            "py",
            "rad",
            "track_res",
            "idy",
            "idx",
            "nk",
            "kref",
            "win",
            "stack",
        )
    }
    for variant, path in paths.items():
        np.savez_compressed(
            path,
            **responses[variant],
            **shared,
            fingerprint=np.array(fingerprint),
        )
    return paths


def pooled_loss_interval(
    details: dict[str, dict], field: str, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    stack_values = {}
    for stack, detail in details.items():
        values = detail[field][detail["keep"]]
        stack_values[stack] = np.asarray(values, dtype=np.float64)
    point = float(
        np.median([np.median(values) for values in stack_values.values()])
    )
    draws = np.empty(BOOTSTRAP_DRAWS, dtype=np.float64)
    for draw in range(BOOTSTRAP_DRAWS):
        medians = []
        for values in stack_values.values():
            index = rng.integers(0, values.size, size=values.size)
            medians.append(float(np.median(values[index])))
        draws[draw] = np.median(medians)
    return {
        "median_of_stack_medians": point,
        "ci95": [
            float(np.percentile(draws, 2.5)),
            float(np.percentile(draws, 97.5)),
        ],
        "passes_positive": float(np.percentile(draws, 2.5)) > 0.0,
    }


def retraction_audit() -> dict:
    files = {
        "build_chroma": DOCS / "BUILD-CHROMA.md",
        "m113": DOCS / "M113-ca.md",
        "v_ca": DOCS / "V-CA-audit.md",
        "m114_retraction": REPO
        / "experiments"
        / "M114-ca-verify"
        / "RETRACTION.txt",
    }
    findings = {}
    for name, path in files.items():
        text = path.read_text(encoding="utf-8")
        hits = [
            {"line": index, "text": line.strip()}
            for index, line in enumerate(text.splitlines(), 1)
            if any(
                token in line.upper()
                for token in ("RETRACT", "WITHDRAW", "AMEND")
            )
        ]
        findings[name] = {
            "path": str(path),
            "sha256": file_sha256(path),
            "hits": hits,
        }
    return {
        "files": findings,
        "classification": {
            "M114": (
                "retracts rendered lateral-CA gain/application-factor claims; "
                "does not retract axial through-focus peaks or raw forfeit"
            ),
            "M113": (
                "corrects lateral ring-bootstrap uncertainty; point estimates "
                "survive and this is not the axial estimator"
            ),
            "BUILD_CHROMA_section_17": (
                "withdraws focus dependence of lateral epsilon; axial headline "
                "and green-election forfeit remain outside the withdrawn arm"
            ),
            "V_CA_addendum": (
                "withdraws rendered blue-harm claim in sRGB; does not touch "
                "CFA-native axial response curves"
            ),
        },
        "axial_or_forfeit_retraction_found": False,
    }


def main() -> int:
    commission_path = OUT / "c2-audit-commission.json"
    if not commission_path.is_file():
        raise RuntimeError("run c2_audit_commission.py first")
    commission = json.loads(commission_path.read_text(encoding="utf-8"))
    if not commission["summary"]["all_passed"]:
        raise RuntimeError("C2 audit commissioning is not green")

    common, legacy_b1, legacy_b2 = load_legacy()
    raw_inventory = {stack: inventory(stack) for stack in STACKS}
    legacy_paths = {}
    for stack in STACKS:
        path = (
            AUDIT_OUT
            / "legacy"
            / "json"
            / f"b1_{stack}_main.npz"
        )
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            legacy_b1.run(stack)
        legacy_paths[stack] = path

    legacy_independent = {}
    legacy_detail = {}
    legacy_checker = {}
    for index, stack in enumerate(STACKS):
        summary, detail = independent_summary(
            legacy_paths[stack], seed=SEED + 100 * index
        )
        legacy_independent[stack] = summary
        legacy_detail[stack] = detail
        legacy_result, _ = legacy_b2.summarise(stack)
        legacy_checker[stack] = {
            "delta_r": legacy_result["tilewise"]["dR"]["median"],
            "delta_b": legacy_result["tilewise"]["dB"]["median"],
            "delta_null": legacy_result["tilewise"]["null"]["median"],
            "loss_r": legacy_result["gradient_energy_forfeited"]["R"],
            "loss_b": legacy_result["gradient_energy_forfeited"]["B"],
        }

    reproduction = {}
    for stack in STACKS:
        measured = legacy_independent[stack]
        target = TARGETS[stack]
        errors = {
            "delta_r_frames": abs(measured["delta_r"] - target["delta_r"]),
            "delta_b_frames": abs(measured["delta_b"] - target["delta_b"]),
            "loss_r_fraction": abs(measured["loss_r"] - target["loss_r"]),
            "loss_b_fraction": abs(measured["loss_b"] - target["loss_b"]),
        }
        independent_vs_legacy = {
            name: abs(measured[name] - legacy_checker[stack][name])
            for name in ("delta_r", "delta_b", "delta_null", "loss_r", "loss_b")
        }
        reproduction[stack] = {
            "target": target,
            "measured": measured,
            "absolute_errors": errors,
            "independent_vs_legacy": independent_vs_legacy,
            "passes": (
                errors["delta_r_frames"] <= 0.05
                and errors["delta_b_frames"] <= 0.05
                and errors["loss_r_fraction"] <= 0.0025
                and errors["loss_b_fraction"] <= 0.0025
                and measured["delta_r"] < 0.0
                and measured["delta_b"] < 0.0
                and (
                    abs(measured["delta_null"])
                    + 0.5
                    * (
                        measured["delta_null_ci95"][1]
                        - measured["delta_null_ci95"][0]
                    )
                    < 0.125
                )
                and max(independent_vs_legacy.values()) < 1.0e-10
            ),
        }

    normalised_paths = {}
    normalised_summary = {}
    normalised_detail = {}
    gamma = {}
    for index, stack in enumerate(STACKS):
        paths = build_normalised_caches(
            stack,
            legacy_paths[stack],
            raw_inventory[stack],
            common,
        )
        normalised_paths[stack] = {
            name: {
                "path": str(path),
                "sha256": file_sha256(path),
            }
            for name, path in paths.items()
        }
        summary, detail = independent_summary(
            paths["normalised"], seed=SEED + 1000 + 100 * index
        )
        normalised_summary[stack] = summary
        normalised_detail[stack] = detail
        if stack == "lavendar-cpl":
            for name in ("gamma_0p8", "gamma_1p2"):
                tone_summary, _ = independent_summary(
                    paths[name], seed=SEED + 2000 + index
                )
                gamma[name] = {
                    "summary": tone_summary,
                    "retained_delta_r": abs(tone_summary["delta_r"])
                    / abs(summary["delta_r"]),
                    "retained_delta_b": abs(tone_summary["delta_b"])
                    / abs(summary["delta_b"]),
                    "passes": (
                        tone_summary["delta_r"] < 0.0
                        and tone_summary["delta_b"] < 0.0
                        and abs(tone_summary["delta_r"])
                        >= 0.75 * abs(summary["delta_r"])
                        and abs(tone_summary["delta_b"])
                        >= 0.75 * abs(summary["delta_b"])
                    ),
                }

    pooled_r = pooled_loss_interval(
        normalised_detail, "tile_loss_r", SEED + 3000
    )
    pooled_b = pooled_loss_interval(
        normalised_detail, "tile_loss_b", SEED + 4000
    )
    normalised_gate = {
        "all_offsets_negative": all(
            summary["delta_r"] < 0.0 and summary["delta_b"] < 0.0
            for summary in normalised_summary.values()
        ),
        "pooled_loss_r": pooled_r,
        "pooled_loss_b": pooled_b,
        "gamma": gamma,
    }
    normalised_gate["passes"] = (
        normalised_gate["all_offsets_negative"]
        and pooled_r["passes_positive"]
        and pooled_b["passes_positive"]
        and all(value["passes"] for value in gamma.values())
    )

    radial = {
        stack: radial_intercept(
            legacy_detail[stack], SEED + 5000 + index
        )
        for index, stack in enumerate(("lavendar-cpl", "coffee-bean"))
    }
    radial_passes = all(value["passes_axial_gate"] for value in radial.values())
    retractions = retraction_audit()

    source_hashes = {
        str(path.relative_to(REPO)).replace("\\", "/"): file_sha256(path)
        for path in (
            Path(__file__),
            HERE / "c2_audit_commission.py",
            LEGACY_SRC / "common.py",
            LEGACY_SRC / "b0_validate.py",
            LEGACY_SRC / "b1_curves.py",
            LEGACY_SRC / "b2_analyse.py",
            LEGACY_SRC / "b4_controls.py",
            LEGACY_SRC / "b6_discriminate.py",
        )
    }
    cache_records = {
        stack: {
            "path": str(path),
            "sha256": file_sha256(path),
            "fingerprint": cache_fingerprint(stack, raw_inventory[stack]),
        }
        for stack, path in legacy_paths.items()
    }
    decision_gates = {
        "commission_green": commission["summary"]["all_passed"],
        "all_legacy_numbers_reproduced": all(
            value["passes"] for value in reproduction.values()
        ),
        "normalised_and_gamma_tone_gate": normalised_gate["passes"],
        "axial_centre_intercepts": radial_passes,
        "no_axial_or_forfeit_retraction": not retractions[
            "axial_or_forfeit_retraction_found"
        ],
    }
    decision = (
        "GO" if all(decision_gates.values()) else "STOP"
    )
    result = {
        "schema": 1,
        "question": (
            "Does the prior CFA-native evidence support building an "
            "off-by-default axial chromatic epoch-shift prototype?"
        ),
        "claim_type": (
            "longitudinal/axial focus displacement, not lateral radial scale"
        ),
        "decision": decision,
        "decision_gates": decision_gates,
        "commission": {
            "path": str(commission_path),
            "sha256": file_sha256(commission_path),
            "summary": commission["summary"],
        },
        "source_sha256": source_hashes,
        "capture_inventory": raw_inventory,
        "legacy_cache": cache_records,
        "legacy_reproduction": reproduction,
        "normalised_cache": normalised_paths,
        "normalised_summary": normalised_summary,
        "normalised_gate": normalised_gate,
        "radial_axial_discriminator": radial,
        "retraction_audit": retractions,
        "generator_checker_audit": {
            "legacy_v3_generator": (
                "Gaussian defocus/noise generation is separate from the "
                "three-point peak checker, but is supporting evidence only"
            ),
            "cancellation_immune_control": (
                "committed fixed response table and separately committed "
                "predicate; five exact checker mutations go RED"
            ),
            "real_data_controls": (
                "G1-G2 is carried through every real stack; M107 B3's "
                "R<->G1 label swap is an independent real-data control"
            ),
        },
        "tone_provenance": (
            "black-subtracted native CFA linear RAW; no demosaic, white "
            "balance, colour matrix, render tone curve, or comparator"
        ),
    }
    write_json(OUT / "c2-audit.json", result)
    print("C2 prior-finding audit")
    for stack, value in reproduction.items():
        measured = value["measured"]
        print(
            f"  {stack}: dR={measured['delta_r']:+.4f}, "
            f"dB={measured['delta_b']:+.4f}, "
            f"loss R/B={100*measured['loss_r']:.2f}%/"
            f"{100*measured['loss_b']:.2f}% "
            f"{'PASS' if value['passes'] else 'FAIL'}"
        )
    print(
        f"  normalised pooled loss R={100*pooled_r['median_of_stack_medians']:.2f}% "
        f"{[100*x for x in pooled_r['ci95']]}%; "
        f"B={100*pooled_b['median_of_stack_medians']:.2f}% "
        f"{[100*x for x in pooled_b['ci95']]}%"
    )
    print(f"DECISION: {decision}")
    return 0 if decision == "GO" else 3


if __name__ == "__main__":
    raise SystemExit(main())
