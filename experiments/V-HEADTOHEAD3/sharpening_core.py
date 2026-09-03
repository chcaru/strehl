"""Preregistered sharpening-discriminator primitives.

Only the 0.20--0.25 cyc/native-px band is claim-bearing.  Nothing in this
module computes or prints a numerical result above 0.25 cyc/px.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import tifffile
from scipy import ndimage

from ordinal import (
    crop_centered,
    midrank_field,
    overlap_after_shift,
    phase_correction,
)


SOURCE_0 = Path(r"D:\edited\macro\test2")
SOURCE_40 = Path(r"D:\edited\macro\test")
PMAX_0 = SOURCE_0 / "2026-05-09-12.12.17 ZS PMax.tif"
PMAX_40 = SOURCE_40 / "2026-05-07-21.31.06 ZS PMax.tif"
STREHL = Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff")

SELECT_IDS = (4, 20, 36, 52)
TRAIN_IDS = (1, 9, 17, 25, 33, 41, 49, 57)
HOLDOUT_IDS = (6, 14, 22, 30, 38, 46, 54, 62)
SIDE = 512
SEED = 20260904
UNLICENSED = "UNLICENSED_GT_0.25"
FIT_EDGES = np.arange(0.02, 0.201, 0.01, dtype=np.float64)


@dataclass(frozen=True)
class Model:
    sigma: float
    amount: float
    train_loss: float
    train_identity_loss: float
    holdout_loss: float
    holdout_identity_loss: float


def source_path(root: Path, identity: int) -> Path:
    return root / f"20260507-DSC{identity:05d}.tif"


def green(path: Path) -> np.ndarray:
    a = tifffile.memmap(path)
    if a.shape != (4672, 7008, 3):
        raise ValueError(f"{path}: expected 4672x7008x3, got {a.shape}")
    return a[:, :, 1]


def source_manifest() -> list[tuple[Path, Path]]:
    pairs = [(source_path(SOURCE_0, i), source_path(SOURCE_40, i)) for i in range(1, 64)]
    for a, b in pairs:
        if not a.is_file() or not b.is_file():
            raise FileNotFoundError(f"missing source pair: {a}, {b}")
    return pairs


def _window(shape: tuple[int, int]) -> np.ndarray:
    return np.hanning(shape[0])[:, None] * np.hanning(shape[1])[None, :]


def frequency_radius(shape: tuple[int, int]) -> np.ndarray:
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    return np.sqrt(fx * fx + fy * fy)


def licensed_mask(shape: tuple[int, int], band_scale: float = 1.0) -> np.ndarray:
    r = frequency_radius(shape)
    return (r >= 0.20 * band_scale) & (r < 0.25 * band_scale)


def q25(a: np.ndarray, band_scale: float = 1.0) -> float:
    """Licensed-band energy per fixed average-rank variance.

    The denominator is Parseval's expected windowed energy from the rank
    variance.  It does not inspect any other measured frequency band.
    """
    q = midrank_field(np.asarray(a))
    q -= np.mean(q)
    var = float(np.mean(q * q))
    if not var > 0:
        raise ValueError("Q25 requires a non-constant crop")
    w = _window(q.shape)
    z = q * w
    power = np.abs(np.fft.fft2(z)) ** 2
    num = float(np.sum(power[licensed_mask(q.shape, band_scale)], dtype=np.float64))
    den = q.size * float(np.sum(w * w, dtype=np.float64)) * var
    if not den > 0:
        raise ValueError("Q25 denominator is not positive")
    return num / den


def raw_q25(a: np.ndarray, band_scale: float = 1.0) -> float:
    x = np.asarray(a, np.float64)
    x -= np.mean(x)
    var = float(np.mean(x * x))
    if not var > 0:
        raise ValueError("raw Q25 requires a non-constant crop")
    w = _window(x.shape)
    power = np.abs(np.fft.fft2(x * w)) ** 2
    num = float(np.sum(power[licensed_mask(x.shape, band_scale)], dtype=np.float64))
    return num / (x.size * float(np.sum(w * w)) * var)


def rail_fraction(a: np.ndarray) -> float:
    x = np.asarray(a)
    if np.issubdtype(x.dtype, np.integer):
        info = np.iinfo(x.dtype)
        return float(np.mean((x == info.min) | (x == info.max)))
    return float(np.mean((x == 0.0) | (x == 1.0)))


def site_score(a: np.ndarray) -> float:
    q = midrank_field(np.asarray(a))
    sm = ndimage.gaussian_filter(q, 1.0, mode="reflect")
    gy, gx = np.gradient(sm)
    return float(np.quantile(np.hypot(gy, gx), 0.95))


def site_digest(rows: Sequence[tuple[int, int, float]]) -> str:
    h = hashlib.sha256()
    for y, x, score in rows:
        h.update(f"{y},{x},{score:.17g}\n".encode("ascii"))
    return h.hexdigest().upper()


def select_sites() -> dict:
    """Select sites from four Sharpness-0 frames and no other pixel source."""
    images = [green(source_path(SOURCE_0, i)) for i in SELECT_IDS]
    h, w = images[0].shape
    centres = [
        (y, x)
        for y in range(512, h - 383, 512)
        for x in range(512, w - 383, 512)
    ]
    rows: list[tuple[int, int, float]] = []
    rejected = 0
    for y, x in centres:
        crops = [crop_centered(im, y, x, SIDE) for im in images]
        if any(c is None or rail_fraction(c) > 0.01 for c in crops):
            rejected += 1
            continue
        score = max(site_score(c) for c in crops if c is not None)
        rows.append((y, x, score))
    result: dict[str, object] = {
        "selection_ids": list(SELECT_IDS),
        "candidate_count": len(centres),
        "eligible_count": len(rows),
        "rejected_count": rejected,
        "digest": site_digest(rows),
    }
    for parity in (0, 1):
        part = sorted(
            (r for r in rows if ((r[0] // 512 + r[1] // 512) % 2) == parity),
            key=lambda r: (r[2], r[0], r[1]),
        )
        if len(part) < 24:
            raise RuntimeError(f"parity {parity}: only {len(part)} eligible candidates")
        result[f"flat_{parity}"] = [[y, x] for y, x, _ in part[:12]]
        result[f"detail_{parity}"] = [[y, x] for y, x, _ in part[-12:]]
        result[f"flat_score_{parity}"] = [float(r[2]) for r in part[:12]]
        result[f"detail_score_{parity}"] = [float(r[2]) for r in part[-12:]]
    return result


def robust_normalise(a: np.ndarray, reference_scale: float | None = None) -> tuple[np.ndarray, float]:
    x = np.asarray(a, np.float64)
    q25_, q75_ = np.quantile(x, [0.25, 0.75])
    scale = float(q75_ - q25_) if reference_scale is None else float(reference_scale)
    if not scale > 0:
        raise ValueError("zero robust scale")
    return (x - np.mean(x)) / scale, scale


def radial_band_powers(
    a: np.ndarray,
    edges: np.ndarray = FIT_EDGES,
    reference_scale: float | None = None,
) -> tuple[np.ndarray, float]:
    x, scale = robust_normalise(a, reference_scale)
    w = _window(x.shape)
    power = np.abs(np.fft.fft2(x * w)) ** 2
    r = frequency_radius(x.shape)
    out = np.asarray(
        [
            np.sum(power[(r >= lo) & (r < hi)], dtype=np.float64)
            for lo, hi in zip(edges[:-1], edges[1:])
        ],
        np.float64,
    )
    return out, scale


def aggregate_transfer(
    root0: Path,
    root40: Path,
    identities: Sequence[int],
    sites: Sequence[Sequence[int]],
) -> dict:
    p0 = np.zeros(len(FIT_EDGES) - 1, np.float64)
    p40 = np.zeros_like(p0)
    count = 0
    for identity in identities:
        a = green(source_path(root0, identity))
        b = green(source_path(root40, identity))
        for y, x in sites:
            ca = crop_centered(a, y, x, SIDE)
            cb = crop_centered(b, y, x, SIDE)
            if ca is None or cb is None:
                raise RuntimeError(f"source crop out of bounds: frame {identity} {(y, x)}")
            pa, scale = radial_band_powers(ca)
            pb, _ = radial_band_powers(cb, reference_scale=scale)
            p0 += pa
            p40 += pb
            count += 1
    amp = np.sqrt(np.maximum(p40, 1e-300) / np.maximum(p0, 1e-300))
    return {
        "count": count,
        "p0": p0,
        "p40": p40,
        "amplitude": amp,
        "centres": 0.5 * (FIT_EDGES[:-1] + FIT_EDGES[1:]),
    }


def usm_gain(f: np.ndarray, sigma: float, amount: float) -> np.ndarray:
    x = np.asarray(f, np.float64)
    return 1.0 + amount * (1.0 - np.exp(-2.0 * np.pi**2 * sigma**2 * x**2))


def transfer_loss(transfer: dict, sigma: float, amount: float) -> float:
    obs = np.asarray(transfer["amplitude"], np.float64)
    pred = usm_gain(np.asarray(transfer["centres"]), sigma, amount)
    return float(np.median(np.abs(np.log(obs) - np.log(pred))))


def fit_model(train: dict, holdout: dict) -> tuple[Model, list[list[float]]]:
    sigmas = np.round(np.arange(0.30, 2.501, 0.05), 2)
    amounts = np.round(np.arange(0.00, 3.001, 0.05), 2)
    table: list[list[float]] = []
    best: tuple[float, float, float] | None = None
    for sigma in sigmas:
        for amount in amounts:
            loss = transfer_loss(train, float(sigma), float(amount))
            table.append([float(sigma), float(amount), loss])
            if best is None or (loss, sigma, amount) < (best[2], best[0], best[1]):
                best = (float(sigma), float(amount), loss)
    assert best is not None
    sigma, amount, train_loss = best
    model = Model(
        sigma=sigma,
        amount=amount,
        train_loss=train_loss,
        train_identity_loss=transfer_loss(train, 1.0, 0.0),
        holdout_loss=transfer_loss(holdout, sigma, amount),
        holdout_identity_loss=transfer_loss(holdout, 1.0, 0.0),
    )
    return model, table


def usm(a: np.ndarray, sigma: float, amount: float) -> np.ndarray:
    x = np.asarray(a, np.float64)
    return x + amount * (x - ndimage.gaussian_filter(x, sigma, mode="reflect"))


def rank_hull_delta(a: np.ndarray, b: np.ndarray, tau: float = 0.01) -> tuple[float, float, float]:
    """Return B-outside-A minus A-outside-B and the two component rates."""
    qa = midrank_field(np.asarray(a))
    qb = midrank_field(np.asarray(b))
    alo = ndimage.minimum_filter(qa, size=3, mode="nearest")
    ahi = ndimage.maximum_filter(qa, size=3, mode="nearest")
    blo = ndimage.minimum_filter(qb, size=3, mode="nearest")
    bhi = ndimage.maximum_filter(qb, size=3, mode="nearest")
    b_out = float(np.mean((qb < alo - tau) | (qb > ahi + tau)))
    a_out = float(np.mean((qa < blo - tau) | (qa > bhi + tau)))
    return b_out - a_out, b_out, a_out


def bootstrap_log_ratio(
    site_logs: Sequence[float],
    *,
    seed: int = SEED,
    n_boot: int = 10_000,
) -> dict:
    x = np.asarray(site_logs, np.float64)
    if x.ndim != 1 or len(x) < 6:
        raise ValueError("need at least six independent sites")
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot, np.float64)
    for i in range(n_boot):
        draws[i] = float(np.mean(x[rng.integers(0, len(x), len(x))]))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "n": int(len(x)),
        "point_log": float(np.mean(x)),
        "point": float(np.exp(np.mean(x))),
        "ci_low": float(np.exp(lo)),
        "ci_high": float(np.exp(hi)),
    }


def bootstrap_mean(
    sites: Sequence[float],
    *,
    seed: int = SEED,
    n_boot: int = 10_000,
) -> dict:
    x = np.asarray(sites, np.float64)
    if x.ndim != 1 or len(x) < 6:
        raise ValueError("need at least six independent sites")
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot, np.float64)
    for i in range(n_boot):
        draws[i] = float(np.mean(x[rng.integers(0, len(x), len(x))]))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "n": int(len(x)),
        "point": float(np.mean(x)),
        "ci_low": float(lo),
        "ci_high": float(hi),
    }


def registered_pair(
    reference: np.ndarray,
    moving: np.ndarray,
    centre: Sequence[float],
    side: int = SIDE,
    max_shift: int = 32,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, float]]:
    cy, cx = map(float, centre)
    pad = max_shift + 8
    large_side = side + 2 * pad
    a_large = crop_centered(reference, cy, cx, large_side)
    b_large = crop_centered(moving, cy, cx, large_side)
    if a_large is None or b_large is None:
        raise ValueError(f"registered crop out of bounds at {centre}")
    corr = phase_correction(
        midrank_field(a_large),
        midrank_field(b_large),
        max_shift=max_shift,
    )
    a = crop_centered(reference, cy, cx, side)
    b = crop_centered(moving, cy - corr[0], cx - corr[1], side)
    if a is None or b is None:
        raise ValueError(f"corrected crop out of bounds at {centre}: {corr[:2]}")
    return a, b, corr


def source_holdout_rows(
    sites: Sequence[Sequence[int]],
    sigma: float,
    amount: float,
) -> dict:
    by_site: dict[tuple[int, int], dict[str, list[float]]] = {
        (int(y), int(x)): {"actual_pred": [], "sharp_base": [], "hull": []}
        for y, x in sites
    }
    for identity in HOLDOUT_IDS:
        a = green(source_path(SOURCE_0, identity))
        b = green(source_path(SOURCE_40, identity))
        for y, x in sites:
            ca, cb, corr = registered_pair(a, b, (y, x), max_shift=8)
            if corr[:2] != (0, 0):
                # Matching Lightroom exports should be pixel-coincident.  A
                # nonzero correction is recorded by failing closed.
                raise RuntimeError(
                    f"source pair {identity} site {(y, x)} correction {corr[:2]}"
                )
            pred = usm(ca, sigma, amount)
            rec = by_site[(int(y), int(x))]
            rec["actual_pred"].append(math.log(q25(cb) / q25(pred)))
            rec["sharp_base"].append(math.log(q25(cb) / q25(ca)))
            rec["hull"].append(rank_hull_delta(ca, cb)[0])
    return {
        "actual_pred": [float(np.median(v["actual_pred"])) for v in by_site.values()],
        "sharp_base": [float(np.median(v["sharp_base"])) for v in by_site.values()],
        "hull": [float(np.median(v["hull"])) for v in by_site.values()],
    }


def verdict(flags: dict[str, bool]) -> str:
    artifact = all(
        flags.get(k, False)
        for k in (
            "advantage",
            "model",
            "reproduces",
            "flat_output",
            "corroboration",
            "spatial",
        )
    )
    real = all(
        flags.get(k, False)
        for k in (
            "advantage",
            "original_trail",
            "model",
            "no_carry",
            "flat_null",
            "hull_null",
            "usm_still_trails",
            "spatial",
        )
    )
    if artifact and real:
        raise ValueError("contradictory verdict predicates")
    return (
        "ARTIFACT"
        if artifact
        else "REAL DEFICIT -- RETROSPECTIVE MODEL-CONDITIONAL"
        if real
        else "INDETERMINATE"
    )


def quadrant_signs(values: dict[tuple[int, int], float]) -> list[float]:
    rows: list[float] = []
    for qy in (0, 1):
        for qx in (0, 1):
            v = [
                value
                for (y, x), value in values.items()
                if (y >= 4672 / 2) == bool(qy) and (x >= 7008 / 2) == bool(qx)
            ]
            if v:
                rows.append(float(np.mean(v)))
    return rows


def leave_one_out_same_direction(values: Iterable[float]) -> bool:
    x = np.asarray(list(values), np.float64)
    if len(x) < 2:
        return False
    signs = [float(np.mean(np.delete(x, i))) > 0 for i in range(len(x))]
    return all(signs) or not any(signs)
