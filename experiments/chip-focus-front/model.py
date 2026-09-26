"""One bounded planar-front fit; no data loading, source election or quality gate."""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares, minimize_scalar


SCHEMA = 1
KNOTS = np.linspace(0.0, 1.0, 7)
MAX_NFEV = 300


def _inputs(xy_native, contrast):
    xy = np.asarray(xy_native, dtype=np.float64)
    curves = np.asarray(contrast, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] != 2 or curves.ndim != 3:
        raise ValueError("expected xy[P,2] and contrast[K,P,2]")
    if curves.shape[1:] != (xy.shape[0], 2) or curves.shape[0] < 9:
        raise ValueError("two bands, matching sites and at least nine frames required")
    if not np.isfinite(xy).all() or not np.isfinite(curves).all():
        raise ValueError("nonfinite coordinates or contrast")
    return xy, curves


def _profile(unit, values):
    """Least squares amplitude >= 0 and free offset, along frame axis zero."""
    gm = unit.mean(axis=0)
    ym = values.mean(axis=0)
    gc = unit - gm
    denominator = np.sum(gc * gc, axis=0)
    numerator = np.sum(gc * (values - ym), axis=0)
    amplitude = np.maximum(np.divide(numerator, denominator,
        out=np.zeros_like(numerator), where=denominator > 1e-30), 0.0)
    offset = ym - amplitude * gm
    return amplitude, offset, unit * amplitude + offset


def _schedule(parameters, frames):
    increments = np.exp(np.r_[parameters, 0.0])
    values = np.r_[0.0, np.cumsum(increments / increments.sum())]
    values[-1] = 1.0
    return np.interp(np.linspace(0.0, 1.0, frames), KNOTS, values), values


def _unit(schedule, xy, plane, sigma):
    centre = xy @ np.asarray(plane[:2]) + plane[2]
    distance = (schedule[:, None] - centre[None, :]) / sigma
    return np.exp(-0.5 * distance * distance)


def _curve_scale(values):
    rms = np.sqrt(np.mean((values - values.mean(axis=0)) ** 2, axis=0))
    floor = max(float(np.max(np.abs(values))) * 1e-12, 1e-30)
    return np.maximum(rms, floor), rms


def fit_model(xy_native, contrast, train_mask):
    """Fit primary front, then secondary width; quality is decided elsewhere."""
    xy, curves = _inputs(xy_native, contrast)
    train = np.asarray(train_mask)
    if train.dtype != np.bool_ or train.shape != (len(xy),) or train.sum() < 6:
        raise ValueError("boolean mask with at least six training sites required")
    centre = 0.5 * (xy.min(axis=0) + xy.max(axis=0))
    scale = 0.5 * (xy.max(axis=0) - xy.min(axis=0))
    if np.any(scale <= 0):
        raise ValueError("a two-dimensional grid is required")
    coords = (xy - centre) / scale
    training_xy = coords[train]
    if np.linalg.matrix_rank(np.c_[training_xy, np.ones(train.sum())]) < 3:
        raise ValueError("training sites do not span a plane")
    frames = curves.shape[0]
    y = curves[:, train, 0]
    normalizer, _ = _curve_scale(y)
    model = {"schema": SCHEMA, "status": "insufficient_temporal_variation",
        "frames": frames, "xy_center": centre.tolist(), "xy_scale": scale.tolist(),
        "plane": None, "schedule_knots": KNOTS.tolist(), "schedule_values": None,
        "widths": None, "train_indices": np.flatnonzero(train).tolist(), "fit": {}}
    if np.count_nonzero(np.any(y != y[0], axis=0)) < 6:
        return model

    # Full-curve moments initialize only; they never elect a source or score truth.
    ordinal = np.linspace(0.0, 1.0, frames)
    weight = np.maximum(y - np.quantile(y, 0.2, axis=0), 0.0)
    mass = weight.sum(axis=0)
    means = np.divide((weight * ordinal[:, None]).sum(axis=0), mass,
        out=np.full(len(mass), 0.5), where=mass > 0)
    variances = np.divide((weight * (ordinal[:, None] - means) ** 2).sum(axis=0),
        mass, out=np.full(len(mass), 0.01), where=mass > 0)
    plane = np.linalg.lstsq(np.c_[training_xy, np.ones(train.sum())], means, rcond=None)[0]
    min_width = 0.5 / (frames - 1)
    max_width = 0.5
    width = float(np.clip(np.median(np.sqrt(variances)), min_width * 1.01, max_width * 0.99))
    lower = np.r_[[-2.0, -2.0, -1.0], np.full(5, -2.0), np.log(min_width)]
    upper = np.r_[[2.0, 2.0, 2.0], np.full(5, 2.0), np.log(max_width)]
    initial = np.clip(np.r_[plane, np.zeros(5), np.log(width)], lower + 1e-8, upper - 1e-8)

    def residual(parameters):
        schedule, _ = _schedule(parameters[3:8], frames)
        unit = _unit(schedule, training_xy, parameters[:3], np.exp(parameters[8]))
        prediction = _profile(unit, y)[2]
        return ((prediction - y) / normalizer).ravel()

    initial_residual = residual(initial)
    result = least_squares(residual, initial, bounds=(lower, upper), method="trf",
        jac="3-point", max_nfev=MAX_NFEV, ftol=1e-8, xtol=1e-8, gtol=1e-8)
    schedule, schedule_values = _schedule(result.x[3:8], frames)
    secondary = curves[:, train, 1]
    secondary_scale, _ = _curve_scale(secondary)

    def secondary_objective(log_width):
        unit = _unit(schedule, training_xy, result.x[:3], np.exp(log_width))
        prediction = _profile(unit, secondary)[2]
        return float(np.mean(((prediction - secondary) / secondary_scale) ** 2))

    secondary_fit = minimize_scalar(secondary_objective,
        bounds=(np.log(min_width), np.log(max_width)), method="bounded",
        options={"maxiter": 96, "xatol": 1e-8})
    model.update(status="fit_completed", plane=result.x[:3].tolist(),
        schedule_values=schedule_values.tolist(),
        widths=[float(np.exp(result.x[8])), float(np.exp(secondary_fit.x))],
        fit={"primary_success": bool(result.success), "primary_status": int(result.status),
            "primary_message": str(result.message), "primary_nfev": int(result.nfev),
            "primary_njev": int(result.njev), "primary_max_nfev": MAX_NFEV,
            "primary_initial_relative_rmse": float(np.sqrt(np.mean(initial_residual ** 2))),
            "primary_final_relative_rmse": float(np.sqrt(np.mean(result.fun ** 2))),
            "primary_optimality": float(result.optimality),
            "primary_bound_flags": (np.minimum(result.x - lower, upper - result.x) < 1e-6).tolist(),
            "secondary_success": bool(secondary_fit.success),
            "secondary_nfev": int(secondary_fit.nfev),
            "secondary_relative_rmse": float(np.sqrt(secondary_fit.fun)),
            "secondary_at_width_bound": bool(min(secondary_fit.x - np.log(min_width),
                np.log(max_width) - secondary_fit.x) < 1e-6),
            "converged": bool(result.success and secondary_fit.success),
            "scope": "optimizer diagnostics only; no predictive or photographic qualification"})
    return model


def predict_profiles(model, xy_native):
    """Unit profiles without access to any held-out curve values."""
    if model.get("schema") != SCHEMA or model.get("status") != "fit_completed":
        raise ValueError("model has no fitted front")
    xy = np.asarray(xy_native, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all():
        raise ValueError("invalid prediction coordinates")
    coords = (xy - np.asarray(model["xy_center"])) / np.asarray(model["xy_scale"])
    schedule = np.interp(np.linspace(0.0, 1.0, model["frames"]),
        model["schedule_knots"], model["schedule_values"])
    return np.stack([_unit(schedule, coords, model["plane"], sigma)
        for sigma in model["widths"]], axis=2)


def evaluate_profiles(model, xy_native, contrast, nuisance_frames=None, score_frames=None):
    """Even-calibrated amplitudes/offsets; default scores disjoint odd frames."""
    xy, curves = _inputs(xy_native, contrast)
    frames = curves.shape[0]
    if frames != model.get("frames"):
        raise ValueError("frame count differs from fitted schedule")
    calibration = np.arange(frames) % 2 == 0 if nuisance_frames is None else np.asarray(nuisance_frames)
    score = np.arange(frames) % 2 == 1 if score_frames is None else np.asarray(score_frames)
    if (calibration.dtype != np.bool_ or score.dtype != np.bool_ or
        calibration.shape != (frames,) or score.shape != (frames,) or
        calibration.sum() < 3 or score.sum() < 3 or np.any(calibration & score)):
        raise ValueError("disjoint boolean calibration/scoring masks with >=3 frames required")
    unit = predict_profiles(model, xy)
    amplitude, offset, _ = _profile(unit[calibration], curves[calibration])
    prediction = unit * amplitude + offset
    constant = np.broadcast_to(curves[calibration].mean(axis=0), curves.shape).copy()
    return {"predicted": prediction, "unit_profiles": unit, "amplitudes": amplitude,
        "offsets": offset, "constant_predictions": constant,
        "score_sse": np.sum((prediction[score] - curves[score]) ** 2, axis=0),
        "constant_score_sse": np.sum((constant[score] - curves[score]) ** 2, axis=0),
        "calibration_sse": np.sum((prediction[calibration] - curves[calibration]) ** 2, axis=0),
        "calibration_frames": calibration, "score_frames": score}
