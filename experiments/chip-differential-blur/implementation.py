"""Nested local shift/one-Laplacian discriminator; no RAW decoder or renderer."""
from pathlib import Path
import importlib.util
import sys
import numpy as np
from scipy.ndimage import gaussian_filter, laplace
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT/'experiments/quality-september14/local-green-translation.py'
spec = importlib.util.spec_from_file_location('commissioned_chip_translation', OLD)
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
sample, mapped, continuous = old.sample, old.mapped, old.continuous
SIGMA, RADIUS, MAX_SHIFT, FD_STEP = old.SIGMA, old.RADIUS, old.MAX_SHIFT, old.FD_STEP
MARGIN, SPLIT, GAP = 32, 196, 16
LAPLACIAN_RADIUS = 1


def guide(cfa, origin=(0, 0), usable=None, phase=0):
    """One measured green phase, normalized fixed sigma1.5 Gaussian, f32."""
    assert phase in (0, 1) and cfa.ndim == 2
    y, x = np.indices(cfa.shape)
    mask = ((y+origin[1]) % 2 == phase) & ((x+origin[0]) % 2 == 1-phase)
    if usable is not None:
        mask &= usable
    numerator = gaussian_filter(np.where(mask, cfa, np.float32(0)).astype(np.float32),
                                sigma=SIGMA, mode='mirror', truncate=4.0)
    denominator = gaussian_filter(mask.astype(np.float32), sigma=SIGMA, mode='mirror', truncate=4.0)
    # A fully clipped small island may lack phase support. Do not manufacture
    # a measurement by filling it. This experiment refuses that saved patch.
    if not np.all(denominator > 0):
        raise ValueError('REFUSED: unsupported phase-only normalized guide')
    value = numerator/denominator
    assert value.dtype == np.float32 and np.isfinite(value).all()
    return value


def grids(axis=0, phase=0, origin=(0, 0)):
    assert axis in (0, 1) and phase in (0, 1)
    y, x = np.mgrid[MARGIN:392-MARGIN, MARGIN:392-MARGIN]
    coordinate = x if axis == 0 else y
    def points(p, region):
        sites = (((y+origin[1]) % 2 == p) & ((x+origin[0]) % 2 == 1-p)) & region
        return np.column_stack((x[sites], y[sites])).astype(np.float64)
    return points(phase, coordinate < SPLIT-GAP), points(1-phase, coordinate >= SPLIT+GAP)


def fit(source_train_image, source_test_image, reference_train_values, reference_test_values,
        source_train_xy, source_test_xy, axis=0, joint=False, probe_deltas=()):
    """Variable projection jointly refits shifts, gain, bias and optional Laplacian.

    target = gain*S(mapped+delta) + lap_coefficient*Lap(S)(mapped+delta) + bias.
    beta=lap_coefficient/gain has source-native-pixel-squared units. The Laplacian
    is fixed five-point on a 2-D phase guide; it never filters a frame axis.
    """
    support_radius = RADIUS+LAPLACIAN_RADIUS+MAX_SHIFT+FD_STEP+1
    support_gap = source_test_xy[:, axis].min()-source_train_xy[:, axis].max()-2*support_radius
    if support_gap <= 0:
        raise ValueError('REFUSED: train/holdout source support overlaps')
    train_lap = laplace(source_train_image, mode='mirror') if joint else None
    test_lap = laplace(source_test_image, mode='mirror') if joint else None
    target = np.asarray(reference_train_values, dtype=np.float64)
    held = np.asarray(reference_test_values, dtype=np.float64)
    if np.std(target) < 1e-7:
        raise ValueError('REFUSED: flat target has no shift information')

    def design(image, derivative, positions, delta):
        values = sample(image, positions+delta)
        columns = [values]
        if joint:
            columns.append(sample(derivative, positions+delta))
        columns.append(np.ones_like(values))
        return np.column_stack(columns)

    def profile(delta):
        matrix = design(source_train_image, train_lap, source_train_xy, delta)
        coefficients, _, rank, _ = np.linalg.lstsq(matrix, target, rcond=None)
        return coefficients, matrix@coefficients-target, matrix, rank

    def residual(delta):
        return profile(delta)[1]

    def jacobian(delta):
        columns = []
        for i in (0, 1):
            step = np.zeros(2)
            step[i] = FD_STEP
            columns.append((residual(delta+step)-residual(delta-step))/(2*FD_STEP))
        return np.column_stack(columns)

    solution = least_squares(residual, np.zeros(2), jac=jacobian, bounds=(-MAX_SHIFT, MAX_SHIFT),
                             max_nfev=50, ftol=1e-8, xtol=1e-8, gtol=1e-8)

    def reading(delta):
        coefficients, error, matrix, rank = profile(delta)
        test = design(source_test_image, test_lap, source_test_xy, delta)@coefficients-held
        scales = np.std(matrix[:, :-1], axis=0)
        standardized = (matrix[:, :-1]-matrix[:, :-1].mean(axis=0))/np.maximum(scales, 1e-15)
        condition = float(np.linalg.cond(np.column_stack((standardized, np.ones(len(target))))))
        gain = float(coefficients[0])
        beta = float(coefficients[1]/gain) if joint and gain != 0 else 0.0
        return dict(delta_source_native=np.asarray(delta).tolist(), gain=gain,
                    bias=float(coefficients[-1]), lap_coefficient=float(coefficients[1]) if joint else 0.0,
                    beta_source_native_squared=beta, rank=int(rank), standardized_condition=condition,
                    fit_rmse=float(np.sqrt(np.mean(error**2))),
                    validation_rmse=float(np.sqrt(np.mean(test**2))),
                    validation_mean_error=float(np.mean(test)), validation_max_abs=float(np.max(np.abs(test))))

    before, after = reading(np.zeros(2)), reading(solution.x)
    motion_singular_values = np.linalg.svd(jacobian(solution.x), compute_uv=False)
    motion_condition = float(motion_singular_values[0]/max(motion_singular_values[-1], 1e-30))
    reasons = []
    if not solution.success:
        reasons.append('optimizer-did-not-converge')
    if np.any(np.abs(solution.x) > 3.99):
        reasons.append('translation-at-bound')
    if after['gain'] <= 0:
        reasons.append('nonpositive-gain')
    if after['rank'] != (3 if joint else 2) or after['standardized_condition'] > 1e6:
        reasons.append('rank-or-conditioning')
    if motion_singular_values[0] < 1e-7 or motion_condition > 1e3:
        reasons.append('motion-aperture-or-conditioning')
    if joint and abs(after['beta_source_native_squared']) > 1.0:
        reasons.append('outside-small-differential-blur-domain')
    return dict(model='translation-plus-laplacian' if joint else 'translation', before=before, after=after,
                delta_source_native=solution.x.tolist(), beta_source_native_squared=after['beta_source_native_squared'],
                converged=bool(solution.success), at_translation_bound=bool(np.any(np.abs(solution.x) > 3.99)),
                nfev=int(solution.nfev), status=int(solution.status), optimality=float(solution.optimality),
                motion_singular_values=motion_singular_values.tolist(), motion_condition=motion_condition,
                probes=[reading(np.asarray(delta)) for delta in probe_deltas],
                source_support_gap_native=float(support_gap), fit_samples=len(target), validation_samples=len(held),
                admitted=not reasons, refusal_reasons=reasons)
