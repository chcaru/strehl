"""Shared numerical machinery for M-PHASE0-CURV.

The RAW reader lives in measure.py.  This module operates only on response
curves and spatial peak tables, which lets commission.py exercise the full
peak-and-surface estimator without touching the capture library.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import ndimage
from scipy.signal import savgol_filter


MAD_NORMAL = 0.6744897501960817
FOURTH_DIFF_NORM = math.sqrt(70.0)
HUBER_C = 1.345
PRIMARY_DEGREE = 3


@dataclass(frozen=True)
class Peak:
    primary: float
    centroid: float
    discrete: int
    noise: float
    prominence_sigma: float
    adjusted_r2: float
    concave: bool
    interior: bool
    vertex_inside: bool

    @property
    def shape_ok(self) -> bool:
        return (
            self.concave
            and self.interior
            and self.vertex_inside
            and self.adjusted_r2 >= 0.80
            and self.prominence_sigma >= 6.0
            and math.isfinite(self.primary)
            and math.isfinite(self.centroid)
        )


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def area_average_2x2(plane: np.ndarray) -> np.ndarray:
    """Area-average one green lattice to the measurement lattice."""
    p = np.asarray(plane, dtype=np.float32)
    if p.ndim != 2:
        raise ValueError(f"green plane must be 2-D, got {p.shape}")
    h = p.shape[0] - p.shape[0] % 2
    w = p.shape[1] - p.shape[1] % 2
    p = p[:h, :w]
    return 0.25 * (
        p[0::2, 0::2]
        + p[0::2, 1::2]
        + p[1::2, 0::2]
        + p[1::2, 1::2]
    )


def focus_response(plane: np.ndarray, box: int = 17) -> tuple[np.ndarray, np.ndarray]:
    """Registered 2-D normalised squared-Sobel response and local level."""
    p = np.asarray(plane, dtype=np.float32)
    if p.ndim != 2:
        raise ValueError(
            "focus_response accepts one 2-D frame plane; a cube would let "
            "separable filters touch the frame axis"
        )
    gx = ndimage.sobel(p, axis=1, mode="reflect")
    gy = ndimage.sobel(p, axis=0, mode="reflect")
    energy = ndimage.uniform_filter(gx * gx + gy * gy, size=box, mode="reflect")
    level = ndimage.uniform_filter(p, size=box, mode="reflect")
    response = energy / np.maximum(level, 32.0) ** 2
    return response.astype(np.float32, copy=False), level.astype(np.float32, copy=False)


def fourth_difference_sigma(curve: np.ndarray) -> float:
    """Noise SD from a fourth difference, independent of smooth cubic signal."""
    c = np.asarray(curve, dtype=np.float64)
    if c.ndim != 1 or c.size < 5 or not np.all(np.isfinite(c)):
        return float("nan")
    d = np.convolve(c, np.array([1.0, -4.0, 6.0, -4.0, 1.0]), mode="valid")
    med = float(np.median(d))
    mad = float(np.median(np.abs(d - med)))
    return mad / (MAD_NORMAL * FOURTH_DIFF_NORM)


def peak_curve(curve: np.ndarray, width_coupling: float = 0.0) -> Peak:
    """Registered seven-point log-quadratic and half-height centroid.

    ``width_coupling`` is zero in the instrument.  Commissioning sets it to a
    non-zero value to plant the exact defect "reported position depends on
    response width".
    """
    c = np.asarray(curve, dtype=np.float64)
    bad = Peak(
        primary=float("nan"),
        centroid=float("nan"),
        discrete=-1,
        noise=float("nan"),
        prominence_sigma=0.0,
        adjusted_r2=float("-inf"),
        concave=False,
        interior=False,
        vertex_inside=False,
    )
    if c.ndim != 1 or c.size < 11 or not np.all(np.isfinite(c)):
        return bad
    if np.any(c <= 0):
        # The physical response is squared energy divided by squared signal and
        # is positive.  Refuse malformed synthetic or cached input.
        return bad

    smooth = savgol_filter(c, 9, 3, mode="interp")
    j = int(np.argmax(smooth))
    interior = 4 <= j <= c.size - 5
    sigma = fourth_difference_sigma(c)
    if not math.isfinite(sigma):
        return bad
    sigma_eff = max(sigma, np.finfo(np.float64).eps)
    prominence = float((smooth[j] - np.median(smooth)) / sigma_eff)

    if not interior:
        return Peak(
            primary=float(j),
            centroid=float(j),
            discrete=j,
            noise=sigma,
            prominence_sigma=prominence,
            adjusted_r2=float("-inf"),
            concave=False,
            interior=False,
            vertex_inside=False,
        )

    xx = np.arange(j - 3, j + 4, dtype=np.float64)
    baseline = float(np.percentile(smooth, 10.0))
    peak_height = max(float(smooth[j] - baseline), np.finfo(np.float64).eps)
    yy = np.log(np.maximum(smooth[j - 3 : j + 4] - baseline, peak_height * 1e-8))
    coef = np.polyfit(xx, yy, 2)
    a, b, _ = (float(v) for v in coef)
    concave = a < 0.0
    vertex = -b / (2.0 * a) if concave else float(j)
    vertex_inside = (j - 3.0) <= vertex <= (j + 3.0)
    fitted = np.polyval(coef, xx)
    ss_res = float(np.sum((yy - fitted) ** 2))
    ss_tot = float(np.sum((yy - np.mean(yy)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("-inf")
    # Seven points, intercept plus two fitted terms.
    adjusted = 1.0 - (1.0 - r2) * 6.0 / 4.0 if math.isfinite(r2) else r2

    half = baseline + 0.5 * peak_height
    lo = hi = j
    while lo > 0 and smooth[lo - 1] >= half:
        lo -= 1
    while hi < c.size - 1 and smooth[hi + 1] >= half:
        hi += 1
    weights = np.maximum(smooth[lo : hi + 1] - baseline, 0.0)
    indices = np.arange(lo, hi + 1, dtype=np.float64)
    centroid = (
        float(np.dot(indices, weights) / np.sum(weights))
        if float(np.sum(weights)) > 0.0
        else float(j)
    )

    if width_coupling:
        # Deliberate commissioning defect.  A correct peak location is
        # independent of the width of the above-half region.
        vertex += width_coupling * float(hi - lo + 1)

    return Peak(
        primary=float(vertex),
        centroid=centroid,
        discrete=j,
        noise=sigma,
        prominence_sigma=prominence,
        adjusted_r2=adjusted,
        concave=concave,
        interior=interior,
        vertex_inside=vertex_inside,
    )


def peaks_for_site(
    curve_g1: np.ndarray,
    curve_g2: np.ndarray,
    *,
    clip_g1: np.ndarray | None = None,
    clip_g2: np.ndarray | None = None,
    mean_g1: np.ndarray | None = None,
    mean_g2: np.ndarray | None = None,
    bypass_reality: bool = False,
    width_coupling: float = 0.0,
) -> dict[str, float | int | bool]:
    c1 = np.asarray(curve_g1, dtype=np.float64)
    c2 = np.asarray(curve_g2, dtype=np.float64)
    avg = 0.5 * (c1 + c2)
    p = peak_curve(avg, width_coupling=width_coupling)
    p1 = peak_curve(c1, width_coupling=width_coupling)
    p2 = peak_curve(c2, width_coupling=width_coupling)

    green_agreement = (
        abs(p1.primary - p2.primary)
        if math.isfinite(p1.primary) and math.isfinite(p2.primary)
        else float("inf")
    )
    j = int(np.clip(p.discrete, 0, max(len(avg) - 1, 0)))
    clip = 0.0
    level = float("inf")
    if clip_g1 is not None and clip_g2 is not None and len(avg):
        lo, hi = max(0, j - 1), min(len(avg), j + 2)
        clip = float(
            max(
                np.max(np.asarray(clip_g1)[lo:hi]),
                np.max(np.asarray(clip_g2)[lo:hi]),
            )
        )
    if mean_g1 is not None and mean_g2 is not None and len(avg):
        level = float(
            min(np.asarray(mean_g1)[j], np.asarray(mean_g2)[j])
        )

    valid = (
        p.shape_ok
        and math.isfinite(p1.primary)
        and math.isfinite(p2.primary)
        and green_agreement <= 3.0
        and clip < 0.001
        and level > 32.0
    )
    if bypass_reality:
        # Deliberate E4 defect: an argmax is always promoted to a "valid peak".
        valid = math.isfinite(p.primary)

    return {
        "k_primary_avg": float(p.primary),
        "k_centroid_avg": float(p.centroid),
        "k_primary_g1": float(p1.primary),
        "k_primary_g2": float(p2.primary),
        "k_centroid_g1": float(p1.centroid),
        "k_centroid_g2": float(p2.centroid),
        "discrete_peak": int(p.discrete),
        "curve_noise": float(p.noise),
        "prominence_sigma": float(p.prominence_sigma),
        "adjusted_r2": float(p.adjusted_r2),
        "green_agreement_frames": float(green_agreement),
        "peak_clip_fraction": float(clip),
        "peak_min_signal_dn": float(level),
        "valid": bool(valid),
    }


def _irls(
    design: np.ndarray,
    values: np.ndarray,
    *,
    robust: bool = True,
    max_iter: int = 50,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.asarray(design, dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    weights = np.ones(len(y), dtype=np.float64)
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    for _ in range(max_iter if robust else 1):
        sw = np.sqrt(weights)
        nxt = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        residual = y - X @ nxt
        if not robust:
            beta = nxt
            break
        scale = np.median(np.abs(residual - np.median(residual))) / MAD_NORMAL
        scale = max(float(scale), 1e-12)
        cutoff = HUBER_C * scale
        new_weights = np.minimum(1.0, cutoff / np.maximum(np.abs(residual), 1e-12))
        if np.max(np.abs(nxt - beta)) <= 1e-10 and np.max(
            np.abs(new_weights - weights)
        ) <= 1e-8:
            beta = nxt
            weights = new_weights
            break
        beta = nxt
        weights = new_weights
    return beta, y - X @ beta, weights


def normalised_coordinates(
    x_sensor: np.ndarray,
    y_sensor: np.ndarray,
    width_sensor: float,
    height_sensor: float,
) -> tuple[np.ndarray, np.ndarray]:
    scale = height_sensor / 2.0
    x = (np.asarray(x_sensor, dtype=np.float64) - width_sensor / 2.0) / scale
    y = (np.asarray(y_sensor, dtype=np.float64) - height_sensor / 2.0) / scale
    return x, y


def _registered_design(u: np.ndarray, v: np.ndarray, degree: int) -> np.ndarray:
    columns = [np.ones_like(u)]
    columns.extend(u**d for d in range(1, degree + 1))
    columns.extend([v, u * v, u * u * v, v * v])
    return np.column_stack(columns)


def fit_surface(
    x_sensor: np.ndarray,
    y_sensor: np.ndarray,
    z_frame: np.ndarray,
    width_sensor: float,
    height_sensor: float,
    *,
    degree: int = PRIMARY_DEGREE,
    robust: bool = True,
    defect: str | None = None,
) -> dict[str, object]:
    """Fit the registered tilted-plane nuisance model and cross-track bowl."""
    x, y = normalised_coordinates(x_sensor, y_sensor, width_sensor, height_sensor)
    z = np.asarray(z_frame, dtype=np.float64)
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[finite], y[finite], z[finite]
    if len(z) < 12:
        raise ValueError("surface fit needs at least 12 finite sites")

    if defect == "naive_radial":
        X = np.column_stack([np.ones_like(x), x, y, x * x + y * y])
        beta, residual, weights = _irls(X, z, robust=robust)
        return {
            "q_h_frames": float(beta[-1]),
            "coefficients": beta.tolist(),
            "gradient_unit": [float("nan"), float("nan")],
            "residual_rms": float(np.sqrt(np.mean(residual**2))),
            "residual_p95_abs": float(np.percentile(np.abs(residual), 95)),
            "n": int(len(z)),
            "downweighted_fraction": float(np.mean(weights < 0.999)),
            "degree": 1,
            "defect": defect,
        }

    lin = np.column_stack([np.ones_like(x), x, y])
    lin_beta, _, _ = _irls(lin, z, robust=True)
    gradient = np.asarray(lin_beta[1:3], dtype=np.float64)
    norm = float(np.linalg.norm(gradient))
    if norm < 1e-10:
        axis = np.array([1.0, 0.0])
    else:
        axis = gradient / norm
    u = axis[0] * x + axis[1] * y
    v = -axis[1] * x + axis[0] * y

    X = _registered_design(u, v, degree)
    if defect == "drop_linear":
        # Exact E6 plant: remove the constant and all first-order protection,
        # while retaining the q column at the end.
        X = np.column_stack([u * u, u**3, u * v, u * u * v, v * v])
    beta, residual, weights = _irls(X, z, robust=robust)
    q = float(beta[-1])
    if defect == "invert_q":
        q = -q
    return {
        "q_h_frames": q,
        "coefficients": beta.tolist(),
        "gradient_unit": axis.tolist(),
        "gradient_norm": norm,
        "residual_rms": float(np.sqrt(np.mean(residual**2))),
        "residual_p95_abs": float(np.percentile(np.abs(residual), 95)),
        "n": int(len(z)),
        "downweighted_fraction": float(np.mean(weights < 0.999)),
        "degree": int(degree),
        "defect": defect,
    }


def block_bootstrap(
    x_sensor: np.ndarray,
    y_sensor: np.ndarray,
    z_frame: np.ndarray,
    width_sensor: float,
    height_sensor: float,
    *,
    degree: int = PRIMARY_DEGREE,
    robust: bool = True,
    reps: int = 2000,
    seed: int = 0xC5_2026,
) -> dict[str, object]:
    x = np.asarray(x_sensor, dtype=np.float64)
    y = np.asarray(y_sensor, dtype=np.float64)
    z = np.asarray(z_frame, dtype=np.float64)
    bx = np.clip((x / width_sensor * 5).astype(int), 0, 4)
    by = np.clip((y / height_sensor * 4).astype(int), 0, 3)
    block = by * 5 + bx
    occupied = np.unique(block)
    if len(occupied) < 12:
        raise ValueError(f"only {len(occupied)} occupied spatial blocks")

    rng = np.random.default_rng(seed)
    values: list[float] = []
    attempts = 0
    while len(values) < reps and attempts < reps * 3:
        attempts += 1
        chosen = rng.choice(occupied, size=len(occupied), replace=True)
        indices = np.concatenate([np.flatnonzero(block == b) for b in chosen])
        try:
            q = float(
                fit_surface(
                    x[indices],
                    y[indices],
                    z[indices],
                    width_sensor,
                    height_sensor,
                    degree=degree,
                    robust=robust,
                )["q_h_frames"]
            )
        except (ValueError, np.linalg.LinAlgError):
            continue
        if math.isfinite(q):
            values.append(q)
    if len(values) != reps:
        raise RuntimeError(f"bootstrap produced {len(values)}/{reps} finite fits")
    a = np.asarray(values)
    return {
        "seed": int(seed),
        "reps": int(reps),
        "occupied_blocks": int(len(occupied)),
        "q_samples": a.tolist(),
        "q_mean": float(np.mean(a)),
        "q_sd": float(np.std(a, ddof=1)),
        "ci95": [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))],
    }


def classify_interval(q: float, ci95: Iterable[float]) -> str:
    lo, hi = (float(v) for v in ci95)
    if lo >= 0.50 or hi <= -0.50:
        return "MATERIAL"
    if (lo > 0.0 or hi < 0.0) and abs(float(q)) >= 0.25:
        return "DETECTED-SMALL"
    if lo >= -0.25 and hi <= 0.25:
        return "NEGLIGIBLE"
    return "UNRESOLVED"


def detected_sign(result: dict[str, object]) -> int:
    """Sign of a registered detection, or zero for a non-detection."""
    if result["classification"] not in {"MATERIAL", "DETECTED-SMALL"}:
        return 0
    q = float(result["q_h_frames"])
    return 1 if q > 0.0 else -1


def ladder_flip(results: Iterable[dict[str, object]]) -> dict[str, object]:
    """Apply the registered MATERIAL/NEGLIGIBLE and detected-sign tests."""
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


def choose_lane_verdict(
    stacks: dict[str, dict[str, object]],
    ladders: dict[str, list[dict[str, object]]],
    placebo: dict[str, object],
    *,
    defect_ignore_ladders: bool = False,
) -> tuple[str, list[str]]:
    """Apply the preregistered lane decision tree.

    ``defect_ignore_ladders`` exists only so commissioning can plant the exact
    primary-only decision defect in this production path.
    """
    reasons: list[str] = []
    if not defect_ignore_ladders:
        flipped = [
            name for name, rungs in ladders.items() if ladder_flip(rungs)["flip"]
        ]
        if flipped:
            return "NOT ROBUST", [
                f"registered flip in {', '.join(flipped)} ladder"
            ]

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

    if bool(placebo.get("applicable")) and not bool(
        placebo.get("reduced_below_half")
    ):
        verdict = "NARROWED"
        reasons.append("spatial shift retained at least half the detected magnitude")
    return verdict, reasons


def surface_gate(
    x_sensor: np.ndarray,
    y_sensor: np.ndarray,
    width_sensor: float,
    height_sensor: float,
) -> dict[str, object]:
    x, y = normalised_coordinates(x_sensor, y_sensor, width_sensor, height_sensor)
    # Direction-independent early diagnostic only.  This is not a lower bound
    # on the eventual cross-track span for an arbitrary rotated point cloud;
    # analyse.complete_gate enforces the actual fitted-v span.
    conservative_span = min(float(np.ptp(x)), float(np.ptp(y)))
    bx = np.clip((np.asarray(x_sensor) / width_sensor * 5).astype(int), 0, 4)
    by = np.clip((np.asarray(y_sensor) / height_sensor * 4).astype(int), 0, 3)
    blocks = np.unique(by * 5 + bx)
    return {
        "n": int(len(x)),
        "occupied_blocks": int(len(blocks)),
        "conservative_v_span": conservative_span,
        "enough_sites": bool(len(x) >= 180),
        "enough_blocks": bool(len(blocks) >= 12),
        "enough_span": bool(conservative_span >= 1.2),
        "pass": bool(len(x) >= 180 and len(blocks) >= 12),
    }


def complete_surface_gate(
    x_sensor: np.ndarray,
    y_sensor: np.ndarray,
    z_frame: np.ndarray,
    width_sensor: float,
    height_sensor: float,
    *,
    defect_conservative_span: bool = False,
) -> dict[str, object]:
    """Registered site/block/side/fitted-cross-track support gate."""
    x = np.asarray(x_sensor, dtype=np.float64)
    y = np.asarray(y_sensor, dtype=np.float64)
    z = np.asarray(z_frame, dtype=np.float64)
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
    gate = surface_gate(x, y, width_sensor, height_sensor)
    side_negative = side_positive = 0
    v_span = 0.0
    if len(z) >= 12:
        preliminary = fit_surface(x, y, z, width_sensor, height_sensor)
        xn, yn = normalised_coordinates(x, y, width_sensor, height_sensor)
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
    passed = bool(
        gate["pass"]
        and gate["enough_each_side"]
        and v_span >= 1.2
    )
    if defect_conservative_span:
        # Deliberate E10 defect: treat the smaller sensor-axis span as a lower
        # bound on a rotated point cloud's fitted cross-track span.
        passed = passed and bool(gate["enough_span"])
    gate["pass"] = passed
    return gate
