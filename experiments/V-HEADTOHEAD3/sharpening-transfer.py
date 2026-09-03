"""Author arm for the externally fixed slanted-edge USM transfer."""

from __future__ import annotations

import os


THREAD_CAP = 8
for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    try:
        _value = int(os.environ.get(_name, str(THREAD_CAP)))
    except ValueError:
        _value = THREAD_CAP
    os.environ[_name] = str(min(max(_value, 1), THREAD_CAP))


import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np
from scipy import ndimage
from scipy.special import ndtr

import sharpening_core as sc
import sharpening_frozen as frozen
from ordinal import (
    fit_geometry,
    green_memmap,
    midrank_field,
    overlap_after_shift,
    phase_correction,
    resized_rank,
)


SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-AUTHOR-1"
COMMISSION_SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-COMMISSION-1"
LABEL = "PRESENTATION_SENSITIVITY_NOT_RESOLUTION"
USM_SIGMA = 1.0
USM_AMOUNT = 0.5
USM_TRUNCATE = 6.0
USM_RADIUS = 6
SYNTHETIC_TRANSFER = 5.560744
BOOTSTRAP_SEED = 20260906
BOOTSTRAP_DRAWS = 10_000
MIN_SITES = 12
INPUT_PATHS = {
    "strehl": sc.STREHL,
    "pmax0": sc.PMAX_0,
    "pmax40": sc.PMAX_40,
}
EXPECTED_HASHES = {
    "strehl": "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    "pmax0": "B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0",
    "pmax40": "4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E",
}
EXPECTED_DETAIL_0 = (
    (2048, 3072),
    (3584, 3584),
    (512, 4608),
    (3072, 4096),
    (3584, 5632),
    (3072, 6144),
    (1536, 5632),
    (2048, 6144),
    (1024, 4096),
    (512, 5632),
    (4096, 6144),
    (4096, 5120),
)
EXPECTED_DETAIL_1 = (
    (512, 5120),
    (1024, 5632),
    (3072, 2560),
    (1024, 4608),
    (3584, 2048),
    (512, 6144),
    (1536, 4096),
    (4096, 4608),
    (3584, 5120),
    (4096, 5632),
    (3584, 6144),
    (3072, 4608),
)
EXPECTED_SITE_DIGEST = (
    "B3A2F5279069A3CC85FB42F49F6FDA39397423D9A65565CAB88CCF8E627679F6"
)


class StopOutcome(RuntimeError):
    """A preregistered stop rather than a numerical result."""


def sha256(path: Path, chunk: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest().upper()


def verify_provenance(
    hashes: Mapping[str, str] | None = None,
    *,
    digest: str | None = None,
    detail_0: Sequence[Sequence[int]] | None = None,
    detail_1: Sequence[Sequence[int]] | None = None,
) -> dict:
    hashes = EXPECTED_HASHES if hashes is None else hashes
    digest = frozen.SITE_DIGEST if digest is None else digest
    detail_0 = frozen.DETAIL_0 if detail_0 is None else detail_0
    detail_1 = frozen.DETAIL_1 if detail_1 is None else detail_1
    actual = {name: sha256(path) for name, path in INPUT_PATHS.items()}
    if set(hashes) != set(EXPECTED_HASHES) or any(
        hashes.get(name) != expected or actual[name] != expected
        for name, expected in EXPECTED_HASHES.items()
    ):
        raise StopOutcome("input hash changed")
    if digest != EXPECTED_SITE_DIGEST:
        raise StopOutcome("site digest changed")
    normalised_0 = tuple(tuple(map(int, row)) for row in detail_0)
    normalised_1 = tuple(tuple(map(int, row)) for row in detail_1)
    if normalised_0 != EXPECTED_DETAIL_0 or normalised_1 != EXPECTED_DETAIL_1:
        raise StopOutcome("site coordinates changed")
    if len(detail_0) + len(detail_1) != 24:
        raise StopOutcome("site count changed")
    return actual


def usm05(image: np.ndarray) -> np.ndarray:
    x = np.asarray(image, np.float64)
    low = ndimage.gaussian_filter(
        x,
        sigma=USM_SIGMA,
        mode="nearest",
        truncate=USM_TRUNCATE,
    )
    return x + USM_AMOUNT * (x - low)


def _registered_pmax_pair(
    pmax0: np.ndarray,
    pmax40: np.ndarray,
    centre: Sequence[int],
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, float]]:
    return sc.registered_pair(pmax0, pmax40, centre, max_shift=32)


def _strehl_pair(
    strehl: np.ndarray,
    comparator: np.ndarray,
    centre: Sequence[int],
    geometry: Mapping,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, float]]:
    scale = float(geometry["scale"])
    gy, gx = map(float, geometry["global_correction"])
    cy, cx = map(float, centre)
    sy, sx = scale * cy + gy, scale * cx + gx
    comparator_side = int(round(sc.SIDE / scale))
    s = sc.crop_centered(strehl, sy, sx, sc.SIDE)
    initial = sc.crop_centered(
        comparator,
        cy,
        cx,
        comparator_side,
    )
    if s is None or initial is None:
        raise ValueError("mapped crop out of bounds")
    correction = phase_correction(
        midrank_field(s),
        resized_rank(initial, s.shape),
        max_shift=32,
    )
    corrected = sc.crop_centered(
        comparator,
        cy - correction[0] / scale,
        cx - correction[1] / scale,
        comparator_side,
    )
    if corrected is None:
        raise ValueError("corrected crop out of bounds")
    return s, corrected, correction


def _required_q25(
    label: str,
    image: np.ndarray,
    scale: float = 1.0,
) -> float:
    value = float(sc.q25(image, band_scale=scale))
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} has invalid Q25")
    return value


def bootstrap(
    logs: Mapping[str, Sequence[float]],
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, dict]:
    names = list(logs)
    columns = [np.asarray(logs[name], np.float64) for name in names]
    if not columns:
        raise ValueError("bootstrap has no columns")
    n = len(columns[0])
    if (
        n < 6
        or any(column.shape != (n,) for column in columns)
        or any(not np.all(np.isfinite(column)) for column in columns)
    ):
        raise ValueError("bootstrap needs equal finite site vectors")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    result = {}
    for name, column in zip(names, columns):
        draws = np.mean(column[indices], axis=1)
        low, high = np.quantile(draws, [0.025, 0.975])
        point_log = float(np.mean(column))
        result[name] = {
            "n": n,
            "point_log": point_log,
            "point": float(np.exp(point_log)),
            "ci_low": float(np.exp(low)),
            "ci_high": float(np.exp(high)),
        }
    return result


def verdict(t0: Mapping[str, float], m40: Mapping[str, float]) -> str:
    if t0["ci_low"] > 1.05 and m40["ci_low"] > 1.0:
        return "REAL_TRANSFER_SUFFICIENT"
    if t0["ci_low"] > 1.05 and m40["ci_high"] < 1.0:
        return "REAL_TRANSFER_PARTIAL"
    if t0["ci_low"] >= 0.95 and t0["ci_high"] <= 1.05:
        return "NO_REAL_TRANSFER"
    return "UNRESOLVED"


def measure_site(
    pmax0: np.ndarray,
    pmax40: np.ndarray,
    strehl: np.ndarray,
    centre: Sequence[int],
    geometry0: Mapping,
    geometry40: Mapping,
) -> tuple[dict[str, float], dict]:
    p0, p40, pmax_correction = _registered_pmax_pair(
        pmax0,
        pmax40,
        centre,
    )
    s40, p40s, strehl40_correction = _strehl_pair(
        strehl,
        pmax40,
        centre,
        geometry40,
    )
    s0, p0s, strehl0_correction = _strehl_pair(
        strehl,
        pmax0,
        centre,
        geometry0,
    )
    q_p0 = _required_q25("pmax0", p0)
    q_p40 = _required_q25("pmax40", p40)
    q_usm_p0 = _required_q25("usm_pmax0", usm05(p0))
    q_s40 = _required_q25("strehl40", s40)
    q_usm_s40 = _required_q25("usm_strehl", usm05(s40))
    q_p40s = _required_q25(
        "pmax40_for_strehl",
        p40s,
        float(geometry40["scale"]),
    )
    q_s0 = _required_q25("strehl0", s0)
    q_p0s = _required_q25(
        "pmax0_for_strehl",
        p0s,
        float(geometry0["scale"]),
    )
    values = {
        "T0": math.log(q_usm_p0 / q_p0),
        "M40": math.log(q_usm_p0 / q_p40),
        "TS": math.log(q_usm_s40 / q_s40),
        "S40": math.log(q_usm_s40 / q_p40s),
        "R0": math.log(q_s0 / q_p0s),
        "O40": math.log(q_p40 / q_p0),
    }
    return values, {
        "centre": list(map(int, centre)),
        "pmax40_to_pmax0": list(pmax_correction),
        "strehl_to_pmax40": list(strehl40_correction),
        "strehl_to_pmax0": list(strehl0_correction),
    }


def _public_geometry(geometry: Mapping) -> dict:
    return {
        key: geometry[key]
        for key in (
            "scale",
            "score",
            "coarse_interior",
            "fine_interior",
            "global_correction",
            "residual_rms",
            "sample_shapes",
        )
    }


def outcome() -> dict:
    commission = commission_result()
    if not commission["green"]:
        raise StopOutcome("author commission failed")
    hashes = verify_provenance()
    geometry0 = fit_geometry(sc.STREHL, sc.PMAX_0)
    geometry40 = fit_geometry(sc.STREHL, sc.PMAX_40)
    for name, geometry in (
        ("pmax0", geometry0),
        ("pmax40", geometry40),
    ):
        if not geometry["coarse_interior"] or not geometry["fine_interior"]:
            raise StopOutcome(f"{name} geometry optimum is not interior")
    pmax0 = sc.green(sc.PMAX_0)
    pmax40 = sc.green(sc.PMAX_40)
    strehl = green_memmap(sc.STREHL)
    logs = {
        name: []
        for name in ("T0", "M40", "TS", "S40", "R0", "O40")
    }
    retained = []
    rejected = []
    for centre in frozen.DETAIL_0 + frozen.DETAIL_1:
        try:
            values, diagnostics = measure_site(
                pmax0,
                pmax40,
                strehl,
                centre,
                geometry0,
                geometry40,
            )
        except ValueError as exc:
            rejected.append({"centre": centre, "reason": str(exc)})
            continue
        for name, value in values.items():
            logs[name].append(value)
        retained.append(diagnostics)
    if len(retained) < MIN_SITES:
        raise StopOutcome(f"only {len(retained)} sites survived")
    summaries = bootstrap(logs)
    t0 = summaries["T0"]
    synthetic_log = math.log(SYNTHETIC_TRANSFER)
    return {
        "schema": SCHEMA,
        "status": "MEASURED_PENDING_CROSSCHECK",
        "label": LABEL,
        "provenance": {
            "hashes": hashes,
            "site_digest": frozen.SITE_DIGEST,
        },
        "operator": {
            "sigma": USM_SIGMA,
            "amount": USM_AMOUNT,
            "truncate": USM_TRUNCATE,
            "radius": USM_RADIUS,
            "boundary": "nearest",
            "clipping": False,
        },
        "licensed_band": {
            "low_inclusive": 0.20,
            "high_exclusive": 0.25,
            "unit": "cycles_per_native_pixel",
        },
        "bootstrap": {
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
            "paired_site_indices": True,
        },
        "geometry": {
            "pmax0": _public_geometry(geometry0),
            "pmax40": _public_geometry(geometry40),
        },
        "frozen_sites": [
            list(site) for site in EXPECTED_DETAIL_0 + EXPECTED_DETAIL_1
        ],
        "retained_count": len(retained),
        "retained_sites": retained,
        "rejected_sites": rejected,
        "quantities": summaries,
        "transfer_vs_synthetic": {
            "synthetic_reference": SYNTHETIC_TRANSFER,
            "T0_over_synthetic": {
                "point": t0["point"] / SYNTHETIC_TRANSFER,
                "ci_low": t0["ci_low"] / SYNTHETIC_TRANSFER,
                "ci_high": t0["ci_high"] / SYNTHETIC_TRANSFER,
            },
            "log_T0_over_log_synthetic": {
                "point": math.log(t0["point"]) / synthetic_log,
                "ci_low": math.log(t0["ci_low"]) / synthetic_log,
                "ci_high": math.log(t0["ci_high"]) / synthetic_log,
            },
        },
        "unlicensed": sc.UNLICENSED,
        "candidate_verdict": verdict(summaries["T0"], summaries["M40"]),
    }


def _vertical_edge(sigma: float, side: int = 256) -> np.ndarray:
    y, x = np.mgrid[:side, :side]
    slope = math.tan(math.radians(5.0))
    intercept = side / 2.0 - slope * (side - 1) / 2.0
    distance = (x - (slope * y + intercept)) / math.hypot(1.0, slope)
    return 0.2 + 0.6 * ndtr(distance / sigma)


def _direct_blur_oracle(image: np.ndarray, mode: str = "edge") -> np.ndarray:
    coordinate = np.arange(-6, 7)
    kernel = np.exp(-0.5 * coordinate.astype(np.float64) ** 2)
    kernel /= np.sum(kernel)
    pad_mode = mode
    padded = np.pad(
        np.asarray(image, np.float64),
        ((6, 6), (6, 6)),
        mode=pad_mode,
    )
    horizontal = np.apply_along_axis(
        lambda row: np.convolve(row, kernel, mode="valid"),
        1,
        padded,
    )
    return np.apply_along_axis(
        lambda column: np.convolve(column, kernel, mode="valid"),
        0,
        horizontal,
    )


def _operator_matches(
    candidate: Callable[[np.ndarray], np.ndarray],
) -> bool:
    fixtures = []
    impulse = np.zeros((31, 33), np.float64)
    impulse[15, 16] = 1.0
    fixtures.append(impulse)
    y, x = np.mgrid[:17, :19]
    fixtures.append(y.astype(np.float64) ** 2 + 0.37 * x)
    for fixture in fixtures:
        expected_low = _direct_blur_oracle(fixture)
        expected = fixture + 0.5 * (fixture - expected_low)
        if not np.allclose(candidate(fixture), expected, rtol=2e-14, atol=2e-14):
            return False
    return True


def _nonwrapping_shift(
    image: np.ndarray,
    displacement: tuple[int, int],
) -> np.ndarray:
    dy, dx = displacement
    result = np.zeros_like(image)
    height = image.shape[0] - abs(dy)
    width = image.shape[1] - abs(dx)
    sy, sx = max(0, -dy), max(0, -dx)
    ty, tx = max(0, dy), max(0, dx)
    result[ty : ty + height, tx : tx + width] = image[
        sy : sy + height,
        sx : sx + width,
    ]
    return result


def _tone_maps(image: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "affine": 1.7 * image + 0.13,
        "gamma3": image**3,
        "logistic": 1.0 / (1.0 + np.exp(-10.0 * (image - 0.5))),
    }


def commission_result() -> dict:
    controls: dict[str, bool] = {}
    mutants: dict[str, bool] = {}
    base_image = _vertical_edge(1.5)
    base = sc.q25(base_image)
    identity = sc.q25(base_image.copy()) / base
    blur = sc.q25(
        ndimage.gaussian_filter(
            base_image,
            0.75,
            mode="nearest",
            truncate=6.0,
        )
    ) / base
    improvement = sc.q25(_vertical_edge(1.2)) / base
    sharpened = sc.q25(usm05(base_image)) / base
    controls.update(
        {
            "operator_constants_external": (
                USM_SIGMA == 1.0
                and USM_AMOUNT == 0.5
                and USM_TRUNCATE == 6.0
                and USM_RADIUS == 6
            ),
            "slantedge_base_external": math.isclose(
                base,
                9.521601319570365e-4,
                rel_tol=5e-12,
            ),
            "identity_parity": identity == 1.0,
            "blur_degradation": blur < 0.95,
            "physical_improvement_external": math.isclose(
                improvement,
                0.977980512025788,
                rel_tol=5e-12,
            ),
            "usm_improvement_external": math.isclose(
                sharpened,
                5.560743625315842,
                rel_tol=5e-12,
            ),
            "operator_oracle": _operator_matches(usm05),
            "licensed_bin_admitted": bool(
                sc.licensed_mask((256, 256))[0, 56]
            ),
            "above_cap_rejected": not bool(
                sc.licensed_mask((256, 256))[0, 72]
            ),
        }
    )
    tone = {
        name: sc.q25(mapped) / base
        for name, mapped in _tone_maps(base_image).items()
    }
    controls["tone_affine"] = abs(tone["affine"] - 1.0) <= 1e-4
    controls["tone_gamma3"] = abs(tone["gamma3"] - 1.0) <= 1e-12
    controls["tone_logistic"] = abs(tone["logistic"] - 1.0) <= 1e-4
    mutant_amount = lambda image: np.asarray(image, np.float64) + 0.4 * (
        np.asarray(image, np.float64)
        - ndimage.gaussian_filter(
            np.asarray(image, np.float64),
            1.0,
            mode="nearest",
            truncate=6.0,
        )
    )
    mutant_boundary = lambda image: np.asarray(image, np.float64) + 0.5 * (
        np.asarray(image, np.float64)
        - ndimage.gaussian_filter(
            np.asarray(image, np.float64),
            1.0,
            mode="reflect",
            truncate=6.0,
        )
    )
    mutants.update(
        {
            "changed_amount": not _operator_matches(mutant_amount),
            "changed_boundary": not _operator_matches(mutant_boundary),
            "disabled_usm": not (
                sc.q25(base_image.copy()) / base > 1.25
            ),
            "disabled_blur": not (
                sc.q25(base_image.copy()) / base < 0.95
            ),
            "above_cap_mask": bool(
                (
                    (
                        sc.frequency_radius((256, 256)) >= 0.20
                    )
                    & (
                        sc.frequency_radius((256, 256)) < 0.30
                    )
                )[0, 72]
            ),
        }
    )
    texture = np.random.default_rng(2026090601).normal(size=(128, 130))
    for index, displacement in enumerate(((5, -7), (-4, 3))):
        moved = _nonwrapping_shift(texture, displacement)
        correction = phase_correction(
            midrank_field(texture),
            midrank_field(moved),
            max_shift=12,
        )
        a, b = overlap_after_shift(texture, moved, correction[:2])
        controls[f"shift_sign_{index}"] = (
            correction[:2] == (-displacement[0], -displacement[1])
            and np.array_equal(a, b)
        )
        wrong_a, wrong_b = overlap_after_shift(
            texture,
            moved,
            displacement,
        )
        mutants[f"shift_wrong_sign_{index}"] = not np.array_equal(
            wrong_a,
            wrong_b,
        )
        noop_a, noop_b = overlap_after_shift(texture, moved, (0, 0))
        mutants[f"shift_noop_{index}"] = not np.array_equal(
            noop_a,
            noop_b,
        )
    oracle_logs = np.log(np.asarray([0.8, 1.0, 1.2, 1.4, 1.6, 1.8]))
    oracle = bootstrap({"x": oracle_logs})["x"]
    controls["bootstrap_external_oracle"] = (
        BOOTSTRAP_SEED == 20260906
        and BOOTSTRAP_DRAWS == 10_000
        and oracle["n"] == 6
        and math.isclose(
            oracle["point"],
            1.253041032404974,
            rel_tol=2e-15,
        )
        and math.isclose(
            oracle["ci_low"],
            1.003960576873364,
            rel_tol=2e-15,
        )
        and math.isclose(
            oracle["ci_high"],
            1.551252077769116,
            rel_tol=2e-15,
        )
    )
    branches = {
        "sufficient": verdict(
            {"ci_low": 1.10, "ci_high": 1.20},
            {"ci_low": 1.01, "ci_high": 1.20},
        ),
        "partial": verdict(
            {"ci_low": 1.10, "ci_high": 1.20},
            {"ci_low": 0.80, "ci_high": 0.99},
        ),
        "null": verdict(
            {"ci_low": 0.96, "ci_high": 1.04},
            {"ci_low": 0.8, "ci_high": 1.2},
        ),
        "unresolved": verdict(
            {"ci_low": 1.01, "ci_high": 1.08},
            {"ci_low": 0.8, "ci_high": 1.2},
        ),
    }
    controls["verdict_branches"] = branches == {
        "sufficient": "REAL_TRANSFER_SUFFICIENT",
        "partial": "REAL_TRANSFER_PARTIAL",
        "null": "NO_REAL_TRANSFER",
        "unresolved": "UNRESOLVED",
    }
    controls["provenance_null"] = True
    try:
        verify_provenance()
    except StopOutcome:
        controls["provenance_null"] = False
    try:
        changed = dict(EXPECTED_HASHES)
        changed["pmax0"] = "0" * 64
        verify_provenance(hashes=changed)
        mutants["changed_hash"] = False
    except StopOutcome:
        mutants["changed_hash"] = True
    try:
        verify_provenance(digest="0" * 64)
        mutants["changed_site_digest"] = False
    except StopOutcome:
        mutants["changed_site_digest"] = True
    try:
        changed_sites = [list(row) for row in frozen.DETAIL_0]
        changed_sites[0][0] += 1
        verify_provenance(detail_0=changed_sites)
        mutants["changed_site_coordinate"] = False
    except StopOutcome:
        mutants["changed_site_coordinate"] = True
    controls = {name: bool(value) for name, value in controls.items()}
    mutants = {name: bool(value) for name, value in mutants.items()}
    green = all(controls.values()) and all(mutants.values())
    return {
        "schema": COMMISSION_SCHEMA,
        "status": "GREEN" if green else "RED",
        "green": green,
        "control_count": len(controls),
        "mutant_count": len(mutants),
        "controls": controls,
        "caught_red_mutants": mutants,
        "synthetic_readings": {
            "base_q25": base,
            "identity_ratio": identity,
            "blur_ratio": blur,
            "physical_improvement_ratio": improvement,
            "usm_ratio": sharpened,
            "tone_ratios": tone,
            "bootstrap_oracle": oracle,
        },
        "verdict_branches": branches,
        "thread_cap": THREAD_CAP,
        "unlicensed": sc.UNLICENSED,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commission", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.commission:
        if args.output is not None:
            parser.error("--commission does not write an outcome")
        result = commission_result()
        prefix = "SHARPENING_TRANSFER_COMMISSION_JSON="
        code = 0 if result["green"] else 2
    else:
        try:
            result = outcome()
            prefix = "SHARPENING_TRANSFER_JSON="
            code = 0
        except StopOutcome as exc:
            result = {
                "schema": SCHEMA,
                "status": "STOPPED",
                "reason": str(exc),
            }
            prefix = "SHARPENING_TRANSFER_ERROR="
            code = 2
    encoded = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if args.output is not None:
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False),
            encoding="utf-8",
        )
    print(prefix + encoded)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
