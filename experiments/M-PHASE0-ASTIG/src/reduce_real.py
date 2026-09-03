"""Fit registered peaks and aggregate field maps from frozen RAW statistics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
OUT = ROOT / "out"
CACHE = OUT / "cache"
sys.path.insert(0, str(HERE))

import astiglib as A  # noqa: E402
import real_measure as R  # noqa: E402


SECTOR_CODE = {0: "centre", 1: "left", 2: "right", 3: "top", 4: "bottom"}
OMIT_VARIANTS = tuple(f"omit-{sector}" for sector in ("left", "right", "top", "bottom"))


def stable_seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little")


def summary(values) -> dict | None:
    a = np.asarray(values, dtype=np.float64)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    lo, hi = np.quantile(a, [0.025, 0.975])
    return {
        "n": int(len(a)),
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "sd": float(np.std(a, ddof=1)) if len(a) > 1 else 0.0,
        "lo95": float(lo),
        "hi95": float(hi),
        "width95": float(hi - lo),
    }


def huber_plane(x: np.ndarray, y: np.ndarray, values: np.ndarray) -> np.ndarray:
    design = np.column_stack((np.ones(len(x)), x, y))
    weight = np.ones(len(x))
    beta = np.linalg.lstsq(design, values, rcond=None)[0]
    for _ in range(20):
        residual = values - design @ beta
        scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
        if scale <= 1e-12:
            break
        u = np.abs(residual) / (1.345 * scale)
        new_weight = np.ones_like(u)
        mask = u > 1
        new_weight[mask] = 1.0 / u[mask]
        lhs = design.T @ (new_weight[:, None] * design)
        rhs = design.T @ (new_weight * values)
        new_beta = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
        if np.max(np.abs(new_beta - beta)) < 1e-10:
            beta = new_beta
            break
        beta, weight = new_beta, new_weight
    return beta


def sector_xy(sector: str, radius: float) -> tuple[float, float]:
    return {
        "centre": (0.0, 0.0),
        "left": (-radius, 0.0),
        "right": (radius, 0.0),
        "top": (0.0, -radius),
        "bottom": (0.0, radius),
    }[sector]


def aggregate_radius(rows: list[dict], radius: float, bootstraps: int) -> dict:
    candidates = [
        row
        for row in rows
        if row["radius"] == radius
        and row["sector"] != "centre"
        and row["valid_for_map"]
    ]
    result = {
        "radius": radius,
        "valid_sectors": [x["sector"] for x in candidates],
        "valid_sector_count": len(candidates),
        "sector_deltas": {x["sector"]: x["estimate"]["delta"] for x in candidates},
    }
    if len(candidates) < 3:
        result["valid"] = False
        result["reason"] = "fewer than three valid cardinal sectors"
        return result
    point = float(np.median([x["estimate"]["delta"] for x in candidates]))
    boot = np.full(bootstraps, np.nan)
    xboot = np.full(bootstraps, np.nan)
    yboot = np.full(bootstraps, np.nan)
    for b in range(bootstraps):
        by_sector = {
            x["sector"]: x["estimate"]["bootstrap_samples"]["delta"][b]
            for x in candidates
        }
        finite = [v for v in by_sector.values() if np.isfinite(v)]
        if len(finite) >= 3:
            boot[b] = np.median(finite)
        xv = [by_sector[s] for s in ("left", "right") if s in by_sector]
        yv = [by_sector[s] for s in ("top", "bottom") if s in by_sector]
        if len(xv) == 2 and np.all(np.isfinite(xv)):
            xboot[b] = np.median(xv)
        if len(yv) == 2 and np.all(np.isfinite(yv)):
            yboot[b] = np.median(yv)
    point_x = [
        x["estimate"]["delta"]
        for x in candidates
        if x["sector"] in ("left", "right")
    ]
    point_y = [
        x["estimate"]["delta"]
        for x in candidates
        if x["sector"] in ("top", "bottom")
    ]
    result.update(
        {
            "valid": True,
            "delta": point,
            "abs_delta": abs(point),
            "bootstrap": summary(boot),
            "horizontal_axis": {
                "delta": float(np.median(point_x)) if len(point_x) == 2 else None,
                "bootstrap": summary(xboot),
            },
            "vertical_axis": {
                "delta": float(np.median(point_y)) if len(point_y) == 2 else None,
                "bootstrap": summary(yboot),
            },
            "same_sign_count": max(
                sum(x["estimate"]["delta"] > 0 for x in candidates),
                sum(x["estimate"]["delta"] < 0 for x in candidates),
            ),
            "_bootstrap_samples": boot,
        }
    )
    return result


def field_geometry(rows: list[dict], bootstraps: int) -> dict:
    valid = [x for x in rows if x["valid_for_map"]]
    if len(valid) < 6:
        return {"valid": False, "reason": "fewer than six valid tiles"}
    xy = np.asarray([sector_xy(x["sector"], x["radius"]) for x in valid])
    mu = np.asarray([x["estimate"]["mu"] for x in valid])
    beta = huber_plane(xy[:, 0], xy[:, 1], mu)
    residual = mu - np.column_stack((np.ones(len(mu)), xy)) @ beta
    radial = np.column_stack((np.ones(len(mu)), xy[:, 0] ** 2 + xy[:, 1] ** 2))
    bowl = np.linalg.lstsq(radial, residual, rcond=None)[0]
    slopes = np.full(bootstraps, np.nan)
    for b in range(bootstraps):
        mb = np.asarray(
            [x["estimate"]["bootstrap_samples"]["mu"][b] for x in valid]
        )
        if np.all(np.isfinite(mb)):
            bb = huber_plane(xy[:, 0], xy[:, 1], mb)
            slopes[b] = math.hypot(bb[1], bb[2])
    return {
        "valid": True,
        "tiles": len(valid),
        "plane": {
            "intercept": float(beta[0]),
            "x_slope_frames_per_field": float(beta[1]),
            "y_slope_frames_per_field": float(beta[2]),
            "slope_magnitude_frames_per_field": float(math.hypot(beta[1], beta[2])),
            "slope_bootstrap": summary(slopes),
        },
        "field_curvature_bowl_frames_per_r2": float(bowl[1]),
        "mu_residual_rms_frames": float(np.sqrt(np.mean(residual * residual))),
    }


def reduce_stack(
    stack: R.Stack,
    cache: np.lib.npyio.NpzFile,
    source_variant: str,
    output_variant: str,
    fit_mode: str,
    baseline: float | None,
    bootstraps: int,
) -> dict | None:
    key = f"stats__{source_variant}"
    if key not in cache.files:
        return None
    stats = cache[key]
    clips = cache[f"clip__{source_variant}"]
    centres = cache[f"centres__{source_variant}"]
    rows = []
    for i, centre in enumerate(centres):
        sector = SECTOR_CODE[int(round(centre[3]))]
        radius = float(centre[2])
        clip_fraction = float(np.max(clips[:, i]))
        estimate = A.measure_stats(
            stats[:, i],
            sector,
            bootstraps=bootstraps,
            seed=stable_seed(f"{stack.name}|{output_variant}|{i}") % (2**63 - 1),
            fit_mode=fit_mode,
            baseline=baseline,
            keep_bootstrap=True,
        )
        rows.append(
            {
                "tile_index": i,
                "sector": sector,
                "radius": radius,
                "cy": int(round(centre[0])),
                "cx": int(round(centre[1])),
                "max_clip_fraction": clip_fraction,
                "clip_gate_pass": clip_fraction < 0.0001,
                "valid_for_map": bool(
                    estimate.get("valid_after_uncertainty")
                    and clip_fraction < 0.0001
                ),
                "estimate": estimate,
            }
        )
    omitted_sector = (
        output_variant.removeprefix("omit-")
        if output_variant in OMIT_VARIANTS
        else None
    )
    aggregation_rows = [
        row for row in rows if row["sector"] != omitted_sector
    ]
    radii = [
        aggregate_radius(aggregation_rows, radius, bootstraps)
        for radius in A.RADII
        if stack.role != "flat-control"
    ]
    geometry = (
        field_geometry(aggregation_rows, bootstraps)
        if stack.role != "flat-control"
        else {"valid": False, "reason": "flat control has one tile"}
    )
    centre = next((x for x in rows if x["sector"] == "centre"), None)
    flat_refused = None
    if stack.role == "flat-control":
        flat_refused = not rows[0]["estimate"]["valid"]

    # Bootstrap samples have served their aggregation purpose. Keep the
    # aggregate samples only until cross-stack combination below.
    for row in rows:
        row["estimate"].pop("bootstrap_samples", None)
    return {
        "stack": {
            "name": stack.name,
            "path": stack.path,
            "role": stack.role,
            "setup": stack.setup,
            "step_width": stack.step_width,
            "aperture": stack.aperture,
            "frames": stats.shape[0],
        },
        "variant": output_variant,
        "source_variant": source_variant,
        "fit_mode": fit_mode,
        "baseline": "percentile-5" if baseline is None else baseline,
        "tiles": rows,
        "radii": radii,
        "field_geometry": geometry,
        "centre_null": centre,
        "flat_control_refused": flat_refused,
    }


def primary_pair(records: list[dict], bootstraps: int) -> dict | None:
    selected = [
        x
        for x in records
        if x["stack"]["name"] in ("grid1-sw4", "grid2-sw4")
    ]
    if len(selected) != 2:
        return None
    outer = []
    for record in selected:
        row = next(x for x in record["radii"] if x["radius"] == 0.90)
        if not row.get("valid"):
            return {"valid": False, "reason": f"{record['stack']['name']} outer invalid"}
        outer.append((record["stack"]["name"], row))
    points = [x[1]["delta"] for x in outer]
    setup_mean = float(np.mean(points))
    # Hierarchical paired bootstrap: resample the two physical setups, then use
    # the same bootstrap index within each selected setup.
    rng = np.random.default_rng(A.BOOTSTRAP_SEED ^ 0xD4)
    samples = np.full(bootstraps, np.nan)
    source = [x[1]["_bootstrap_samples"] for x in outer]
    for b in range(bootstraps):
        chosen = rng.integers(0, 2, size=2)
        vals = [source[j][b] for j in chosen]
        if np.all(np.isfinite(vals)):
            samples[b] = np.mean(vals)
    signed = summary(samples)
    magnitude = summary(np.abs(samples))
    return {
        "valid": True,
        "definition": (
            "abs(mean(delta_grid1-sw4(r=.90), delta_grid2-sw4(r=.90)))"
        ),
        "setup_points": {name: row["delta"] for name, row in outer},
        "signed_mean": setup_mean,
        "D4_abs_frames": abs(setup_mean),
        "signed_bootstrap": signed,
        "magnitude_bootstrap": magnitude,
        "_bootstrap_samples": samples,
    }


def remove_private_samples(value):
    if isinstance(value, dict):
        for key in list(value):
            if key.startswith("_"):
                del value[key]
            else:
                remove_private_samples(value[key])
    elif isinstance(value, list):
        for item in value:
            remove_private_samples(item)


def variant_spec(name: str) -> tuple[str, str, float | None]:
    if name == "linear":
        return "primary", "linear", None
    if name == "log-no-baseline":
        return "primary", "log", 0.0
    if name in OMIT_VARIANTS:
        return "primary", "log", None
    if name in R.VARIANTS:
        return name, "log", None
    raise ValueError(f"unknown variant {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        default="primary",
        choices=tuple(R.VARIANTS) + ("linear", "log-no-baseline") + OMIT_VARIANTS,
    )
    parser.add_argument("--bootstraps", type=int, default=2_000)
    args = parser.parse_args()
    source_variant, fit_mode, baseline = variant_spec(args.variant)
    records = []
    cache_hashes = {}
    for stack in R.STACKS:
        target = CACHE / f"{stack.name}.npz"
        if not target.exists():
            continue
        cache_hashes[stack.name] = hashlib.sha256(target.read_bytes()).hexdigest()
        with np.load(target, allow_pickle=False) as cache:
            record = reduce_stack(
                stack,
                cache,
                source_variant,
                args.variant,
                fit_mode,
                baseline,
                args.bootstraps,
            )
        if record is not None:
            records.append(record)
            outer = next(
                (x for x in record["radii"] if x["radius"] == 0.90),
                None,
            )
            print(
                f"{stack.name:18s} valid tiles "
                f"{sum(x['valid_for_map'] for x in record['tiles']):2d}; "
                f"outer delta {outer.get('delta') if outer else 'control'}"
            )
    pair = primary_pair(records, args.bootstraps)
    result = {
        "schema_version": 1,
        "variant": args.variant,
        "bootstraps": args.bootstraps,
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        "invocation": (
            "PYTHONIOENCODING=utf-8; "
            "PYTHONPATH=<repo>\\experiments\\M-PHASE0-ASTIG\\src; "
            f"python experiments\\M-PHASE0-ASTIG\\src\\reduce_real.py "
            f"--variant {args.variant} --bootstraps {args.bootstraps}"
        ),
        "source_sha256": {
            "reduce_real.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "astiglib.py": hashlib.sha256((HERE / "astiglib.py").read_bytes()).hexdigest(),
            "real_measure.py": hashlib.sha256(
                (HERE / "real_measure.py").read_bytes()
            ).hexdigest(),
        },
        "cache_sha256": cache_hashes,
        "primary_pair": pair,
        "records": records,
    }
    remove_private_samples(result)
    target = OUT / (
        "real-primary.json"
        if args.variant == "primary"
        else f"sensitivity-{args.variant}.json"
    )
    target.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
