"""Measure and bootstrap the products emitted by ``strehl --split-out``."""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


THRESHOLD = 1.0 / 7.0
MIN_RING_SAMPLES = 16
BOOTSTRAPS = 1_000
SEED = 0xD8_2026


def add_ring(dst: dict[str, float], row: dict[str, str]) -> None:
    dst["count"] += int(row["count"])
    dst["cross"] += float(row["cross"])
    dst["power_even"] += float(row["power_even"])
    dst["power_odd"] += float(row["power_odd"])


def classify(
    rings: list[dict[str, float]],
    *,
    last_bin_fallback: bool = False,
    ignore_ring_gaps: bool = False,
    false_above_tail: bool = False,
) -> dict[str, float | str | None]:
    usable: list[tuple[int, float, float]] = []
    for ring in rings:
        den = math.sqrt(ring["power_even"] * ring["power_odd"])
        if ring["count"] >= MIN_RING_SAMPLES and den > 0.0 and math.isfinite(den):
            frc = ring["cross"] / den
            if math.isfinite(frc):
                usable.append((int(ring["radius"]), ring["frequency"], frc))
    if len(usable) < 4:
        return {"outcome": "INSUFFICIENT", "frequency_or_bound": None}
    if usable[0][2] < THRESHOLD:
        return {
            "outcome": "CENSORED_BELOW",
            "frequency_or_bound": usable[0][1],
        }
    for i in range(1, len(usable) - 2):
        _, f0, y0 = usable[i - 1]
        _, f1, y1 = usable[i]
        consecutive = all(
            right[0] == left[0] + 1
            for left, right in zip(usable[i - 1 : i + 2], usable[i : i + 3])
        )
        if (
            y0 >= THRESHOLD
            and all(y < THRESHOLD for _, _, y in usable[i : i + 3])
            and (ignore_ring_gaps or consecutive)
        ):
            dy = y0 - y1
            t = min(1.0, max(0.0, (y0 - THRESHOLD) / dy)) if abs(dy) > 2.2e-16 else 1.0
            return {
                "outcome": "MEASURED",
                "frequency_or_bound": f0 + t * (f1 - f0),
            }
    _, last_frequency, last_frc = usable[-1]
    if last_bin_fallback:
        return {"outcome": "MEASURED", "frequency_or_bound": last_frequency}
    if false_above_tail or last_frc >= THRESHOLD:
        return {
            "outcome": "CENSORED_ABOVE",
            "frequency_or_bound": last_frequency,
        }
    return {"outcome": "INSUFFICIENT", "frequency_or_bound": None}


def quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    at = p * (len(ordered) - 1)
    lo = int(math.floor(at))
    hi = int(math.ceil(at))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - at) + ordered[hi] * (at - lo)


def band_frc(rings: list[dict[str, float]], lo: float, hi: float) -> float:
    selected = [r for r in rings if lo <= r["frequency"] < hi]
    cross = sum(r["cross"] for r in selected)
    pa = sum(r["power_even"] for r in selected)
    pb = sum(r["power_odd"] for r in selected)
    return cross / math.sqrt(pa * pb)


def null_stats(path: Path) -> dict[str, float | int]:
    with Image.open(path) as image:
        width, height = image.size
        codes = np.asarray(image, dtype=np.int32)
    values = codes.astype(np.float64) - 32768.0
    absolute = np.abs(values)
    n = int(values.size)
    assert n == width * height
    return {
        "pixels": n,
        "mean_dn": float(np.mean(values)),
        "rms_dn": float(np.sqrt(np.mean(values * values))),
        "median_abs_dn": float(np.median(absolute)),
        "p95_abs_dn": float(np.percentile(absolute, 95)),
        "saturated_pixels": int(np.count_nonzero((codes == 0) | (codes == 65535))),
    }


def load_products(product_dir: Path) -> tuple[list[dict[str, float]], list[list[dict[str, float]]]]:
    aggregate: list[dict[str, float]] = []
    with (product_dir / "frc.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            aggregate.append(
                {
                    "radius": int(row["radius"]),
                    "frequency": float(row["frequency"]),
                    "count": int(row["count"]),
                    "cross": float(row["cross"]),
                    "power_even": float(row["power_even"]),
                    "power_odd": float(row["power_odd"]),
                }
            )

    by_tile: dict[tuple[int, int], dict[int, dict[str, float]]] = {}
    with (product_dir / "frc-tiles.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (int(row["tile_x"]), int(row["tile_y"]))
            radius = int(row["radius"])
            by_tile.setdefault(key, {})[radius] = {
                "radius": radius,
                "frequency": float(row["frequency"]),
                "count": int(row["count"]),
                "cross": float(row["cross"]),
                "power_even": float(row["power_even"]),
                "power_odd": float(row["power_odd"]),
            }
    tiles = [[rings[r] for r in sorted(rings)] for _, rings in sorted(by_tile.items())]
    if not tiles or any(len(tile) != len(aggregate) for tile in tiles):
        raise RuntimeError("tile spectra are incomplete or do not match the aggregate rings")
    return aggregate, tiles


def bootstrap(tiles: list[list[dict[str, float]]]) -> dict[str, object]:
    rng = random.Random(SEED)
    outcomes: Counter[str] = Counter()
    measured: list[float] = []
    above: list[float] = []
    below: list[float] = []
    for _ in range(BOOTSTRAPS):
        sampled = [tiles[rng.randrange(len(tiles))] for _ in tiles]
        rings = [
            {
                "radius": source["radius"],
                "frequency": source["frequency"],
                "count": 0,
                "cross": 0.0,
                "power_even": 0.0,
                "power_odd": 0.0,
            }
            for source in tiles[0]
        ]
        for tile in sampled:
            for dst, src in zip(rings, tile):
                dst["count"] += src["count"]
                dst["cross"] += src["cross"]
                dst["power_even"] += src["power_even"]
                dst["power_odd"] += src["power_odd"]
        result = classify(rings)
        outcome = str(result["outcome"])
        outcomes[outcome] += 1
        value = result["frequency_or_bound"]
        if value is not None:
            {"MEASURED": measured, "CENSORED_ABOVE": above, "CENSORED_BELOW": below}[
                outcome
            ].append(float(value))

    summary: dict[str, object] = {
        "resamples": BOOTSTRAPS,
        "seed": SEED,
        "outcome_counts": dict(outcomes),
        "measured_fraction": len(measured) / BOOTSTRAPS,
    }
    if len(measured) >= 0.9 * BOOTSTRAPS:
        summary["measured_median"] = statistics.median(measured)
        summary["measured_95_percentile_interval"] = [
            quantile(measured, 0.025),
            quantile(measured, 0.975),
        ]
    if above:
        summary["censored_above_bounds"] = [min(above), max(above)]
    if below:
        summary["censored_below_bounds"] = [min(below), max(below)]
    return summary


def tile_outcomes(product_dir: Path) -> dict[str, object]:
    counts: Counter[str] = Counter()
    measured: list[float] = []
    with (product_dir / "acuity.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            counts[row["outcome"]] += 1
            if row["outcome"] == "MEASURED":
                measured.append(float(row["frequency_or_bound"]))
    return {
        "counts": dict(counts),
        "measured_median": statistics.median(measured) if measured else None,
        "measured_range": [min(measured), max(measured)] if measured else None,
    }


def check_rust_manifest(product_dir: Path, point: dict[str, object]) -> None:
    line = next(
        line
        for line in (product_dir / "README.txt").read_text(encoding="utf-8").splitlines()
        if line.startswith("global_outcome=")
    )
    outcome_field, frequency_field = line.split("; ", 1)
    rust_outcome = outcome_field.split("=", 1)[1]
    if rust_outcome != point["outcome"]:
        raise RuntimeError(
            f"Python/Rust crossing class mismatch: {point['outcome']} vs "
            f"{rust_outcome}"
        )
    if point["frequency_or_bound"] is not None:
        rust_value = float(frequency_field.split("=", 1)[1].split()[0])
        if abs(rust_value - float(point["frequency_or_bound"])) > 5e-12:
            raise RuntimeError(
                f"Python/Rust crossing mismatch: {point['frequency_or_bound']} vs {rust_value}"
            )


def self_test(
    last_bin_fallback: bool, ignore_ring_gaps: bool, false_above_tail: bool
) -> None:
    def rings(values: list[float | None]) -> list[dict[str, float]]:
        return [
            {
                "radius": i + 1,
                "frequency": (i + 1) / 10,
                "count": 16 if value is not None else 0,
                "cross": value if value is not None else 0.0,
                "power_even": 1.0 if value is not None else 0.0,
                "power_odd": 1.0 if value is not None else 0.0,
            }
            for i, value in enumerate(values)
        ]

    measured = classify(rings([0.4, 0.2, 0.1, 0.05, 0.04]))
    assert measured["outcome"] == "MEASURED"
    assert abs(float(measured["frequency_or_bound"]) - 0.2571428571428572) < 1e-14
    below = classify(rings([0.1, 0.05, 0.02, 0.01]))
    assert below == {"outcome": "CENSORED_BELOW", "frequency_or_bound": 0.1}
    above = classify(
        rings([0.9, 0.8, 0.7, 0.6, 0.5]),
        last_bin_fallback=last_bin_fallback,
    )
    assert above == {"outcome": "CENSORED_ABOVE", "frequency_or_bound": 0.5}
    gapped = classify(
        rings([0.4, 0.1, None, 0.05, 0.04]),
        ignore_ring_gaps=ignore_ring_gaps,
    )
    assert gapped == {"outcome": "INSUFFICIENT", "frequency_or_bound": None}
    short_tail = classify(
        rings([0.9, 0.8, 0.1, 0.05]),
        false_above_tail=false_above_tail,
    )
    assert short_tail == {"outcome": "INSUFFICIENT", "frequency_or_bound": None}
    print(
        "MEASURE CHECKER GREEN: fixed crossing, both censor classes, "
        "gapped and short-tail refusal"
    )


def main() -> int:
    if "--self-test" in sys.argv:
        self_test(
            "--plant-last-bin" in sys.argv,
            "--plant-compress-gaps" in sys.argv,
            "--plant-false-above-tail" in sys.argv,
        )
        return 0
    product_dir = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent / "out" / "real-109" / "products"
    )
    aggregate, tiles = load_products(product_dir)
    point = classify(aggregate)
    check_rust_manifest(product_dir, point)
    result = {
        "status": "MEASURED",
        "product_dir": str(product_dir),
        "tile_count": len(tiles),
        "point_estimate": point,
        "bootstrap": bootstrap(tiles),
        "aggregate_frc": {
            "0.02_to_0.10": band_frc(aggregate, 0.02, 0.10),
            "0.10_to_0.25": band_frc(aggregate, 0.10, 0.25),
            "0.35_to_0.48": band_frc(aggregate, 0.35, 0.48),
        },
        "tile_outcomes": tile_outcomes(product_dir),
        "null_product": null_stats(product_dir / "null-signed.tiff"),
        "threshold": THRESHOLD,
        "minimum_ring_samples": MIN_RING_SAMPLES,
        "uncertainty_scope": (
            "deterministic spatial tile bootstrap; measures field-composition "
            "sensitivity, not shared-sensor/common-mode bias"
        ),
    }
    destination = product_dir.parent / "measurement.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
