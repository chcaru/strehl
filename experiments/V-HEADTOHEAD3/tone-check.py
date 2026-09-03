"""End-to-end real-pixel tone plant for V-HEADTOHEAD3.

The transformed comparator is a lazy view, so no protected capture or large
scratch TIFF is written.  Every registration, gate, stratum and spectrum is
rerun through the transformed pixels.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from ordinal import (
    PAIRS,
    SAMPLE_STEP,
    bootstrap_effect,
    candidate_centres,
    fit_geometry,
    green_memmap,
    measure_roi,
    midrank_field,
)


class CubicToneView:
    """Strictly increasing normalised gamma-3 map of an array-like image."""

    def __init__(self, base: np.ndarray, lo: float, hi: float):
        if not hi > lo:
            raise ValueError("tone endpoints must be ordered")
        self.base = base
        self.lo = float(lo)
        self.hi = float(hi)
        self.shape = base.shape
        self.dtype = np.dtype(np.float64)

    def transform(self, x: np.ndarray | float) -> np.ndarray:
        z = (np.asarray(x, np.float64) - self.lo) / (self.hi - self.lo)
        return z**3

    def __getitem__(self, item):
        return self.transform(self.base[item])


def container_rails(a: np.ndarray) -> tuple[float, float]:
    if np.issubdtype(a.dtype, np.integer):
        info = np.iinfo(a.dtype)
        return float(info.min), float(info.max)
    return 0.0, 1.0


def evaluate(rows: list[dict]) -> dict:
    eligible = [r for r in rows if r["reason"] is None]
    textures = np.asarray([r["texture"] for r in eligible])
    flat_cut = float(np.quantile(textures, 0.25))
    detail_cut = float(np.quantile(textures, 0.50))
    flat = np.asarray(
        [r["log_ratio"] for r in eligible if r["texture"] <= flat_cut]
    )
    detail = np.asarray(
        [r["log_ratio"] for r in eligible if r["texture"] >= detail_cut]
    )
    return {
        "reasons": [r["reason"] for r in rows],
        "flat_cut": flat_cut,
        "detail_cut": detail_cut,
        "effect": bootstrap_effect(detail, flat),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pair", choices=tuple(PAIRS), default="113", nargs="?")
    args = parser.parse_args(argv)
    pair = PAIRS[args.pair]
    geometry = fit_geometry(pair.strehl, pair.comparator)
    sg = green_memmap(pair.strehl)
    cg = green_memmap(pair.comparator)
    rails = container_rails(cg)
    toned = CubicToneView(cg, *rails)
    toned_rails = (
        float(toned.transform(rails[0])),
        float(toned.transform(rails[1])),
    )

    sampled_original = midrank_field(np.asarray(cg[::SAMPLE_STEP, ::SAMPLE_STEP]))
    sampled_toned = midrank_field(np.asarray(toned[::SAMPLE_STEP, ::SAMPLE_STEP]))
    geometry_rank_delta = float(np.max(np.abs(sampled_original - sampled_toned)))

    original = []
    transformed = []
    centres = candidate_centres(sg.shape)
    for i, centre in enumerate(centres, 1):
        original.append(
            measure_roi(
                sg,
                cg,
                centre,
                geometry,
                comparator_rails=rails,
            )
        )
        transformed.append(
            measure_roi(
                sg,
                toned,
                centre,
                geometry,
                comparator_rails=toned_rails,
            )
        )
        if i % 12 == 0 or i == len(centres):
            print(f"tone-plant progress {i}/{len(centres)}", flush=True)

    a = evaluate(original)
    b = evaluate(transformed)
    same_reasons = a["reasons"] == b["reasons"]
    cut_delta = max(
        abs(a["flat_cut"] - b["flat_cut"]),
        abs(a["detail_cut"] - b["detail_cut"]),
    )
    fields = (
        "r_detail",
        "r_flat",
        "detail_ci_low",
        "detail_ci_high",
        "flat_ci_low",
        "flat_ci_high",
    )
    effect_delta = max(
        abs(x - y)
        for field in fields
        for x, y in zip(a["effect"][field], b["effect"][field])
    )
    row_delta = 0.0
    for ra, rb in zip(original, transformed):
        if ra["reason"] is None and rb["reason"] is None:
            row_delta = max(
                row_delta,
                float(
                    np.max(
                        np.abs(
                            np.asarray(ra["log_ratio"])
                            - np.asarray(rb["log_ratio"])
                        )
                    )
                ),
            )
    passed = (
        geometry_rank_delta <= 1e-10
        and same_reasons
        and cut_delta <= 1e-10
        and row_delta <= 1e-10
        and effect_delta <= 1e-10
    )
    print(
        "END_TO_END_TONE "
        f"{'GREEN' if passed else 'FAIL'} pair={args.pair} "
        f"geometry_rank_delta={geometry_rank_delta:.3e} "
        f"same_roi_decisions={same_reasons} cut_delta={cut_delta:.3e} "
        f"row_delta={row_delta:.3e} effect_delta={effect_delta:.3e}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
