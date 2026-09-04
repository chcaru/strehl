"""Output scorer for the frozen M152 M3 input-only site population.

Selection is intentionally absent from this module.  The caller must provide a
frozen site ID and source-derived references.  Invalid output data is charged,
never used to delete a site.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy import fft

from census_common import HERE, nearest_rank, sha256_bytes


DEFINITION_PATH = HERE / "m3-checker-definition.json"


def load_checker_definition() -> tuple[dict[str, Any], str]:
    raw = DEFINITION_PATH.read_bytes()
    definition = json.loads(raw)
    if definition.get("schema") != "m152-m3-checker-definition-v1":
        raise RuntimeError("unexpected M152 M3 checker schema")
    return definition, sha256_bytes(raw)


@dataclass(frozen=True)
class SiteProfiles:
    site_id: str
    capture_id: str
    offsets_native_px: np.ndarray
    source_profiles: np.ndarray
    output_profile: np.ndarray
    normalization_source_index: int
    far_reference_source_index: int
    sharp_source_index: int
    output_patch: np.ndarray | None = None
    sharp_source_patch: np.ndarray | None = None


def _range_mask(offsets: np.ndarray, low_abs: float, high_abs: float) -> np.ndarray:
    absolute = np.abs(offsets)
    return (absolute >= low_abs) & (absolute <= high_abs)


def _plateau_masks(
    offsets: np.ndarray, definition: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    bounds = definition["normalization"]["source_plateaus_native_px"]
    left = (offsets >= float(bounds[0][0])) & (offsets <= float(bounds[0][1]))
    right = (offsets >= float(bounds[1][0])) & (offsets <= float(bounds[1][1]))
    return left, right


def _crossing(offsets: np.ndarray, normalized: np.ndarray, level: float) -> float:
    transitions = np.flatnonzero(
        (normalized[:-1] < level) & (normalized[1:] >= level)
    )
    if transitions.size != 1:
        return math.inf
    index = int(transitions[0])
    y0 = float(normalized[index])
    y1 = float(normalized[index + 1])
    if not np.isfinite(y0) or not np.isfinite(y1) or y1 == y0:
        return math.inf
    return float(
        offsets[index]
        + (level - y0) * (offsets[index + 1] - offsets[index]) / (y1 - y0)
    )


def edge_width_10_90(
    offsets: np.ndarray,
    profile: np.ndarray,
    dark: float,
    step: float,
    half_width: float = 32.0,
) -> float:
    support = np.abs(offsets) <= half_width
    x = offsets[support]
    normalized = (profile[support] - dark) / step
    at_10 = _crossing(x, normalized, 0.10)
    at_90 = _crossing(x, normalized, 0.90)
    if not np.isfinite(at_10) or not np.isfinite(at_90) or at_90 <= at_10:
        return math.inf
    return at_90 - at_10


def complex_band_coherence(
    output_patch: np.ndarray,
    reference_patch: np.ndarray,
    low: float = 0.15,
    high: float = 0.25,
) -> float:
    if (
        output_patch.shape != reference_patch.shape
        or output_patch.ndim != 2
        or output_patch.shape[0] != output_patch.shape[1]
        or output_patch.shape[0] < 8
        or not np.all(np.isfinite(output_patch))
        or not np.all(np.isfinite(reference_patch))
    ):
        return 0.0
    size = output_patch.shape[0]
    one = np.hanning(size)
    window = np.outer(one, one)
    window /= math.sqrt(float(np.mean(window * window)))
    output = (output_patch - np.mean(output_patch)) * window
    reference = (reference_patch - np.mean(reference_patch)) * window
    output_fft = fft.fft2(output, norm="ortho", workers=1)
    reference_fft = fft.fft2(reference, norm="ortho", workers=1)
    frequency = fft.fftfreq(size, d=1.0)
    radial = np.sqrt(frequency[:, None] ** 2 + frequency[None, :] ** 2)
    band = (radial >= low) & (radial <= high)
    output_band = output_fft[band]
    reference_band = reference_fft[band]
    output_power = float(np.sum(np.abs(output_band) ** 2))
    reference_power = float(np.sum(np.abs(reference_band) ** 2))
    denominator = math.sqrt(output_power * reference_power)
    if denominator <= 0.0 or not np.isfinite(denominator):
        return 0.0
    numerator = abs(np.sum(output_band * np.conj(reference_band)))
    return float(np.clip(numerator / denominator, 0.0, 1.0))


def invalid_site_result(site: SiteProfiles, reason: str) -> dict[str, Any]:
    return {
        "site_id": site.site_id,
        "capture_id": site.capture_id,
        "h_e": math.inf,
        "v_e": math.inf,
        "v_e_negative_side": math.inf,
        "v_e_positive_side": math.inf,
        "edge_width_ratio": math.inf,
        "rho_edge": 0.0,
        "affected": True,
        "status": "INVALID_OUTPUT_CHARGED",
        "reason": reason,
    }


def score_site(
    site: SiteProfiles, definition: dict[str, Any] | None = None
) -> dict[str, Any]:
    if definition is None:
        definition, _ = load_checker_definition()
    offsets = np.asarray(site.offsets_native_px, dtype=np.float64)
    sources = np.asarray(site.source_profiles, dtype=np.float64)
    output = np.asarray(site.output_profile, dtype=np.float64)
    if (
        offsets.ndim != 1
        or sources.ndim != 2
        or output.ndim != 1
        or sources.shape[1] != offsets.size
        or output.size != offsets.size
        or offsets.size < 2
    ):
        return invalid_site_result(site, "shape_mismatch")
    if (
        not np.all(np.isfinite(offsets))
        or not np.all(np.isfinite(sources))
        or not np.all(np.isfinite(output))
    ):
        return invalid_site_result(site, "nonfinite_profile")
    if not np.all(np.diff(offsets) > 0.0):
        return invalid_site_result(site, "offsets_not_strictly_increasing")
    indices = (
        site.normalization_source_index,
        site.far_reference_source_index,
        site.sharp_source_index,
    )
    if any(index < 0 or index >= sources.shape[0] for index in indices):
        return invalid_site_result(site, "source_index_out_of_range")

    normalization = sources[site.normalization_source_index]
    left_mask, right_mask = _plateau_masks(offsets, definition)
    if not np.any(left_mask) or not np.any(right_mask):
        return invalid_site_result(site, "plateau_support_missing")
    dark = float(np.median(normalization[left_mask]))
    bright = float(np.median(normalization[right_mask]))
    if bright < dark:
        offsets = -offsets[::-1]
        sources = sources[:, ::-1]
        output = output[::-1]
        normalization = sources[site.normalization_source_index]
        left_mask, right_mask = _plateau_masks(offsets, definition)
        dark = float(np.median(normalization[left_mask]))
        bright = float(np.median(normalization[right_mask]))
    step = bright - dark
    if not np.isfinite(step) or step <= 0.0:
        return invalid_site_result(site, "nonpositive_source_step")

    lower = np.min(sources, axis=0)
    upper = np.max(sources, axis=0)
    halo_support = definition["halo"]["support_abs_native_px"]
    veil_support = definition["veil"]["support_abs_native_px"]
    halo_mask = _range_mask(
        offsets, float(halo_support[0]), float(halo_support[1])
    )
    veil_mask = _range_mask(
        offsets, float(veil_support[0]), float(veil_support[1])
    )
    if not np.any(halo_mask) or not np.any(veil_mask):
        return invalid_site_result(site, "metric_support_missing")
    excess = np.maximum.reduce(
        [output - upper, lower - output, np.zeros_like(output)]
    )
    h_e = float(np.max(excess[halo_mask]) / step)

    far = sources[site.far_reference_source_index]
    residual = np.abs(output - far) / step
    negative_veil = (offsets >= -float(veil_support[1])) & (
        offsets <= -float(veil_support[0])
    )
    positive_veil = (offsets >= float(veil_support[0])) & (
        offsets <= float(veil_support[1])
    )
    v_negative = float(np.mean(residual[negative_veil]))
    v_positive = float(np.mean(residual[positive_veil]))
    v_e = float(np.mean(residual[veil_mask]))
    v_side_max_diagnostic = max(v_negative, v_positive)

    sharp = sources[site.sharp_source_index]
    width_support = definition["edge_width"]["support_native_px"]
    width_half = max(abs(float(value)) for value in width_support)
    source_width = edge_width_10_90(
        offsets, sharp, dark, step, half_width=width_half
    )
    output_width = edge_width_10_90(
        offsets, output, dark, step, half_width=width_half
    )
    if (
        not np.isfinite(source_width)
        or source_width <= 0.0
        or not np.isfinite(output_width)
    ):
        width_ratio = math.inf
    else:
        width_ratio = output_width / source_width

    if site.output_patch is None or site.sharp_source_patch is None:
        rho_edge = 0.0
    else:
        rho_band = definition["rho_edge"]["band_cycles_per_native_px"]
        rho_edge = complex_band_coherence(
            np.asarray(site.output_patch, dtype=np.float64),
            np.asarray(site.sharp_source_patch, dtype=np.float64),
            low=float(rho_band[0]),
            high=float(rho_band[1]),
        )

    affected = max(h_e, v_e) > float(
        definition["site_failure"]["threshold_max_h_v"]
    )
    return {
        "site_id": site.site_id,
        "capture_id": site.capture_id,
        "h_e": h_e,
        "v_e": v_e,
        "v_e_negative_side": v_negative,
        "v_e_positive_side": v_positive,
        "v_side_max_diagnostic": v_side_max_diagnostic,
        "edge_width_ratio": width_ratio,
        "rho_edge": rho_edge,
        "affected": bool(affected),
        "status": "OK",
        "reason": None,
    }


def wilson_upper_one_sided(
    failures: int, count: int, z: float = 1.6448536269514722
) -> float:
    if count <= 0:
        return math.inf
    proportion = failures / count
    z2 = z * z
    centre = proportion + z2 / (2.0 * count)
    radius = z * math.sqrt(
        proportion * (1.0 - proportion) / count + z2 / (4.0 * count * count)
    )
    return (centre + radius) / (1.0 + z2 / count)


def summarize(
    site_results: list[dict[str, Any]],
    expected_capture_minimum: int | None = None,
    definition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if definition is None:
        definition, _ = load_checker_definition()
    minimum_total = int(definition["site_population"]["minimum_edges_overall"])
    counts = {}
    for result in site_results:
        capture_id = str(result["capture_id"])
        counts[capture_id] = counts.get(capture_id, 0) + 1
    minimum_capture = (
        int(definition["site_population"]["minimum_edges_per_capture"])
        if expected_capture_minimum is None
        else expected_capture_minimum
    )
    required_captures = set(definition["site_population"]["required_capture_ids"])
    if (
        len(site_results) < minimum_total
        or set(counts) != required_captures
        or (counts and min(counts.values()) < minimum_capture)
    ):
        return {
            "verdict": "UNMEASURED_CAPTURE_INADEQUATE",
            "site_count": len(site_results),
            "per_capture_counts": counts,
        }
    h = np.asarray([result["h_e"] for result in site_results], dtype=np.float64)
    v = np.asarray([result["v_e"] for result in site_results], dtype=np.float64)
    widths = np.asarray(
        [result["edge_width_ratio"] for result in site_results], dtype=np.float64
    )
    coherence = np.asarray(
        [result["rho_edge"] for result in site_results], dtype=np.float64
    )
    affected = int(sum(bool(result["affected"]) for result in site_results))
    count = len(site_results)
    summary = {
        "site_count": count,
        "per_capture_counts": counts,
        "median_h_e": nearest_rank(h, 0.50),
        "median_v_e": nearest_rank(v, 0.50),
        "p99_h_e": nearest_rank(h, 0.99),
        "p99_v_e": nearest_rank(v, 0.99),
        "affected_edge_count": affected,
        "affected_edge_rate": affected / count,
        "affected_edge_wilson_ucb95": wilson_upper_one_sided(affected, count),
        "median_edge_width_ratio": nearest_rank(widths, 0.50),
        "median_rho_edge": nearest_rank(coherence, 0.50),
    }
    bars = definition["bars"]
    checks = {
        "median_h_e": summary["median_h_e"] <= float(bars["median_h_e_max"]),
        "median_v_e": summary["median_v_e"] <= float(bars["median_v_e_max"]),
        "p99_h_e": summary["p99_h_e"] <= float(bars["p99_h_e_max"]),
        "p99_v_e": summary["p99_v_e"] <= float(bars["p99_v_e_max"]),
        "affected_rate": summary["affected_edge_rate"]
        <= float(bars["affected_point_rate_max"]),
        "affected_wilson": summary["affected_edge_wilson_ucb95"]
        <= float(bars["affected_wilson_ucb95_max"]),
        "edge_width": float(bars["median_edge_width_ratio_min"])
        <= summary["median_edge_width_ratio"]
        <= float(bars["median_edge_width_ratio_max"]),
        "rho_edge": summary["median_rho_edge"]
        >= float(bars["median_rho_edge_min"]),
    }
    summary["checks"] = checks
    summary["verdict"] = "PASS" if all(checks.values()) else "FAIL"
    return summary


def paired_p99(
    strehl_results: Iterable[dict[str, Any]],
    comparator_results: dict[str, Iterable[dict[str, Any]]],
) -> dict[str, Any]:
    strehl = {str(row["site_id"]): row for row in strehl_results}
    if not strehl or not comparator_results:
        return {"verdict": "UNMEASURED", "reason": "empty product population"}
    products: dict[str, dict[str, float]] = {}
    for name, rows_iter in comparator_results.items():
        rows = {str(row["site_id"]): row for row in rows_iter}
        if set(rows) != set(strehl):
            return {
                "verdict": "UNMEASURED",
                "reason": f"site mismatch for comparator {name}",
            }
        values = np.asarray(
            [max(float(rows[key]["h_e"]), float(rows[key]["v_e"])) for key in strehl],
            dtype=np.float64,
        )
        products[name] = {"p99_max_h_v": nearest_rank(values, 0.99)}
    best = min(products, key=lambda name: (products[name]["p99_max_h_v"], name))
    strehl_values = np.asarray(
        [
            max(float(strehl[key]["h_e"]), float(strehl[key]["v_e"]))
            for key in strehl
        ],
        dtype=np.float64,
    )
    strehl_p99 = nearest_rank(strehl_values, 0.99)
    best_p99 = products[best]["p99_max_h_v"]
    return {
        "verdict": "PASS" if strehl_p99 <= best_p99 else "FAIL",
        "strehl_p99_max_h_v": strehl_p99,
        "best_comparator": best,
        "best_comparator_p99_max_h_v": best_p99,
        "comparator_p99": products,
    }
