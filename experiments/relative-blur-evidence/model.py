"""Bounded RAW-patch forward-model adequacy; never an ownership estimator.

Arrays are four gathered CFA planes [R,G1,G2,B] in black-subtracted DN.
All signal/kernel/FFT arithmetic is float32; SciPy's parameter search uses
double bookkeeping, with each proposed parameter evaluated as float32.
No image loading, source metadata inference, private noise fit, or file writes.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import fft, ndimage, optimize

SUPPORT = 24
MAX_SIGMA = 8.0
MAX_EXTENT = 512
START = (3.0, 1.0, 0.0)
MAX_EVALUATIONS = 800


@dataclass(frozen=True)
class FitResult:
    params: tuple
    covariance: tuple
    status: str
    reasons: tuple
    train_rmse4: tuple
    initial_rmse4: tuple
    nfev: int
    train_pixels: int
    optimizer_success: bool


def _source(a):
    a = np.asarray(a, dtype=np.float32)
    if a.ndim != 3 or a.shape[0] != 4:
        raise ValueError("expected four CFA planes [4,height,width]")
    if min(a.shape[1:]) <= 2 * SUPPORT or max(a.shape[1:]) > MAX_EXTENT:
        raise ValueError("patch extent must be >48 and <=512 quads on both axes")
    if not np.isfinite(a).all():
        raise ValueError("source contains nonfinite samples")
    return a


def valid_mask(shape):
    h, w = tuple(shape)[-2:]
    out = np.zeros((h, w), dtype=bool)
    if h > 2 * SUPPORT and w > 2 * SUPPORT:
        out[SUPPORT:h-SUPPORT, SUPPORT:w-SUPPORT] = True
    return out


def _mask(mask, shape, *, nonempty=True):
    a = np.asarray(mask, dtype=bool)
    if a.shape != tuple(shape)[-2:]:
        raise ValueError("mask geometry mismatch")
    if nonempty and not a.any():
        raise ValueError("empty scoring support")
    return a


def _footprint(mask):
    # Square is a conservative enclosure of the fixed circular kernel support.
    return ndimage.maximum_filter(mask, size=2*SUPPORT+1,
                                  mode="constant", cval=0).astype(bool)


def _clip_mask(mask, shape):
    if mask is None:
        return np.zeros(tuple(shape)[-2:], dtype=bool)
    a = np.asarray(mask, dtype=bool)
    if a.shape == tuple(shape):
        a = np.any(a, axis=0)
    return _mask(a, shape, nonempty=False)


def kernel(params):
    """Unit-mass, centred sampled Gaussian, fixed radius24; identity included.

    Parameters are (sigma_a, sigma_b, theta_radians) in quad coordinates.
    Zero sigma is the limiting delta on that axis, not a new blur floor.
    """
    p = np.asarray(params, dtype=np.float32)
    if p.shape != (3,) or not np.isfinite(p).all():
        raise ValueError("three finite blur parameters required")
    a, b, theta = p
    if min(a, b) < 0 or max(a, b) > MAX_SIGMA or abs(theta) > np.pi/2 + 1e-6:
        raise ValueError("blur parameters outside frozen bounds")
    y, x = np.mgrid[-SUPPORT:SUPPORT+1, -SUPPORT:SUPPORT+1].astype(np.float32)
    c, s = np.cos(theta), np.sin(theta)
    u, v = c*x+s*y, -s*x+c*y
    def energy(t, sigma):
        if sigma == 0:
            return np.where(np.abs(t) <= np.float32(1e-6),
                            np.float32(0), np.float32(np.inf))
        with np.errstate(over="ignore"):
            return np.float32(.5) * np.square(t / sigma)
    k = np.exp(-(energy(u, a) + energy(v, b))).astype(np.float32)
    k[x*x+y*y > SUPPORT*SUPPORT] = 0
    k /= np.sum(k, dtype=np.float32)
    return k


def covariance(params):
    a, b, theta = np.asarray(params, dtype=np.float32)
    c, s = np.cos(theta), np.sin(theta)
    aa, bb = a*a, b*b
    return ((float(c*c*aa+s*s*bb), float(c*s*(aa-bb))),
            (float(c*s*(aa-bb)), float(s*s*aa+c*c*bb)))


class _Predictor:
    def __init__(self, source):
        self.source = source
        self.h, self.w = source.shape[1:]
        self.shape = (fft.next_fast_len(self.h+2*SUPPORT),
                      fft.next_fast_len(self.w+2*SUPPORT))
        self.spectrum = fft.rfftn(source, s=self.shape, axes=(-2, -1), workers=1)

    def __call__(self, params):
        k = kernel(params)
        if k[SUPPORT, SUPPORT] == np.float32(1):
            return self.source.copy()
        ks = fft.rfftn(k, s=self.shape, axes=(-2, -1), workers=1)
        full = fft.irfftn(self.spectrum * ks[None], s=self.shape,
                         axes=(-2, -1), workers=1)
        return full[:, SUPPORT:SUPPORT+self.h,
                    SUPPORT:SUPPORT+self.w].astype(np.float32, copy=False)


def predict(source, params):
    """Forward prediction; unsupported scene borders are NaN, never padded data."""
    source = _source(source)
    out = _Predictor(source)(params)
    out[:, ~valid_mask(source.shape)] = np.nan
    return out


def _rmse(prediction, target, mask):
    d = prediction[:, mask] - target[:, mask]
    return tuple(float(x) for x in np.sqrt(np.mean(d*d, axis=1,
                                                 dtype=np.float32)))


def _refusal(reason, count=0):
    return FitResult((0., 0., 0.), ((0., 0.), (0., 0.)), "refused", (reason,),
                     (float("nan"),)*4, (float("nan"),)*4, 0, count, False)


def fit(source, target, train_mask, *, protected_mask=None, clipped_mask=None):
    """One fixed-start fit and explicit identity arm, with no nuisance fit.

    Status is fitted/ambiguous/refused. "fitted" is numerical/model preparation,
    not statistical compatibility. The clip mask is caller-supplied authority
    for either source; no RAW saturation information is invented from floats.
    """
    source, target = _source(source), _source(target)
    if source.shape != target.shape:
        raise ValueError("source/target geometry differs")
    train = _mask(train_mask, source.shape)
    count = int(train.sum())
    if np.any(train & ~valid_mask(source.shape)):
        return _refusal("missing-source-apron", count)
    stencil = _footprint(train)
    if protected_mask is not None:
        protected = _mask(protected_mask, source.shape, nonempty=False)
        if np.any(stencil & protected):
            return _refusal("protected-support-enters-training-stencil", count)
    if np.any(stencil & _clip_mask(clipped_mask, source.shape)):
        return _refusal("clipped-training-support", count)

    predictor = _Predictor(source)
    identity = _rmse(source, target, train)
    # Only exact/numerical constants are detected here. This is not a private
    # noise estimate or a low-texture significance threshold.
    spread = np.ptp(source[:, stencil], axis=1)
    tol = np.finfo(np.float32).eps * max(1., float(np.max(np.abs(source)))) * 4
    if float(np.max(spread)) <= tol:
        return FitResult((0., 0., 0.), ((0., 0.), (0., 0.)), "ambiguous",
                         ("constant-source-support",), identity, identity,
                         0, count, True)

    def objective(p):
        d = predictor(p)[:, train] - target[:, train]
        value = float(np.mean(d*d, dtype=np.float32))
        if not np.isfinite(value):
            raise ValueError("nonfinite forward-fit objective")
        return value

    result = optimize.minimize(objective, np.asarray(START), method="Powell",
        bounds=((0., MAX_SIGMA), (0., MAX_SIGMA), (-np.pi/2, np.pi/2)),
        options={"maxfev": MAX_EVALUATIONS, "maxiter": 60,
                 "xtol": 1e-4, "ftol": 1e-7})
    params = tuple(float(x) for x in np.asarray(result.x, dtype=np.float32))
    fitted = _rmse(predictor(params), target, train)
    identity_mse = np.mean(np.square(np.asarray(identity, dtype=np.float32)), dtype=np.float32)
    fitted_mse = np.mean(np.square(np.asarray(fitted, dtype=np.float32)), dtype=np.float32)
    if identity_mse <= fitted_mse:
        params, fitted = (0., 0., 0.), identity
    reasons = []
    status = "fitted"
    if max(params[:2]) >= MAX_SIGMA - 1e-3:
        status, reasons = "refused", ["sigma-upper-bound"]
    elif not result.success:
        status, reasons = "refused", ["optimizer-did-not-converge"]
    elif kernel(params)[SUPPORT, SUPPORT] >= np.float32(1-4*np.finfo(np.float32).eps):
        status, reasons = "ambiguous", ["identity-does-not-order-sources"]
    return FitResult(params, covariance(params), status, tuple(reasons), fitted,
                     identity, int(result.nfev), count, bool(result.success))


def error(source, target, params, mask):
    """Per-plane held-out RMS in DN, without a statistical/quality verdict."""
    source, target = _source(source), _source(target)
    if source.shape != target.shape:
        raise ValueError("source/target geometry differs")
    mask = _mask(mask, source.shape)
    if np.any(mask & ~valid_mask(source.shape)):
        raise ValueError("held-out support lacks genuine source apron")
    return _rmse(_Predictor(source)(params), target, mask)


def evaluate(source, target, result, mask, *, rmse_limit4, clipped_mask=None):
    """Explicit caller allowance, not a calibrated ownership probability.

    Status: compatible/ambiguous/refused. Even compatible does not assign a
    source. Call separately on each protected feature; never hide its failure
    in an aggregate bright-core residual.
    """
    source, target = _source(source), _source(target)
    if source.shape != target.shape:
        raise ValueError("source/target geometry differs")
    mask = _mask(mask, source.shape)
    limits = np.asarray(rmse_limit4, dtype=np.float32)
    if limits.shape != (4,) or not np.isfinite(limits).all() or np.any(limits < 0):
        raise ValueError("four finite nonnegative preregistered RMS allowances required")
    reasons = list(result.reasons)
    if np.any(mask & ~valid_mask(source.shape)):
        return {"status": "refused", "reasons": reasons+["missing-source-apron"],
                "rmse4": None, "pixels": int(mask.sum())}
    if np.any(_footprint(mask) & _clip_mask(clipped_mask, source.shape)):
        return {"status": "refused", "reasons": reasons+["clipped-held-out-support"],
                "rmse4": None, "pixels": int(mask.sum())}
    rmse = error(source, target, result.params, mask)
    status = {"fitted": "compatible", "ambiguous": "ambiguous", "refused": "refused"}[result.status]
    if np.any(np.asarray(rmse) > limits):
        status = "refused"
        reasons.append("held-out-residual-exceeds-caller-allowance")
    return {"status": status, "reasons": reasons, "rmse4": rmse,
            "pixels": int(mask.sum()), "rmse_limit4": tuple(float(x) for x in limits)}
