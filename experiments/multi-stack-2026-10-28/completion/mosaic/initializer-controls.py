"""FIT-only coarse-model controls; no product policy or heldout tuning.

The third regressor is a runtime focus ordinate, never physical distance.
These plants commission numerical behavior, not that focus is projective depth
in the photographs. All final native/support/mesh gates remain separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np

SEED = 20261028
TRIALS = 256
COARSE_INLIER_QUAD = 2.0
NORMAL = np.array([3516.0, 2344.0, 433.0])
OUTPUT = np.array([3516.0, 2344.0])


def design(points, focus):
    p = points / NORMAL
    return np.c_[p if focus else p[:, :2], np.ones(len(p))]


def fit(points, targets, focus):
    x = design(points, focus)
    y = targets / OUTPUT
    n = x.shape[1]
    rows = []
    for p, q in zip(x, y):
        rows.extend([np.r_[p, np.zeros(n), -q[0] * p],
                     np.r_[np.zeros(n), p, -q[1] * p]])
    a = np.array(rows)
    _, singular, v = np.linalg.svd(a, full_matrices=False)
    # The homogeneous scale is one null direction; a second null direction is
    # a degenerate spatial/focus design, never evidence for a free mapping.
    if singular[-2] <= singular[0] * 1e-8:
        return None
    model = v[-1].reshape(3, n)
    norm = np.linalg.norm(model[-1])
    return model / norm if norm > 0 else None


def predict(model, points, focus):
    h = design(points, focus) @ model.T
    if np.any(np.abs(h[:, 2]) < 0.05):
        return None
    return h[:, :2] / h[:, 2, None] * OUTPUT


def train(points, targets, focus):
    minimum = 6 if focus else 4
    rng = np.random.default_rng(SEED)
    candidates = [np.arange(len(points))]
    candidates += [rng.choice(len(points), minimum, replace=False) for _ in range(TRIALS)]
    best = None
    for indices in candidates:
        model = fit(points[indices], targets[indices], focus)
        predicted = None if model is None else predict(model, points, focus)
        if predicted is None:
            continue
        errors = np.linalg.norm(predicted - targets, axis=1)
        selected = errors <= COARSE_INLIER_QUAD
        count = int(selected.sum())
        if count < max(8, minimum + 2):
            continue
        score = float(np.sum(errors[selected] ** 2))
        if best is None or (-count, score) < best[:2]:
            best = (-count, score, selected)
    if best is None:
        return None
    selected = best[2]
    model = fit(points[selected], targets[selected], focus)
    return model, selected


def run_controls():
    rng = np.random.default_rng(SEED)
    # Smooth strongly curved focus surface: peak index is a supplied runtime
    # coordinate for this plant, with no asserted metric calibration.
    x, y = np.meshgrid(np.linspace(300, 3000, 13), np.linspace(200, 2000, 11))
    z = 60 + 190 * (x / 3516) ** 2 + 70 * np.sin(y / 650)
    points = np.c_[x.ravel(), y.ravel(), z.ravel()]
    roles = (np.indices(x.shape).sum(axis=0).ravel() % 3) == 0
    matrix = np.array([[1.015, .018, .105, .055],
                       [-.012, .990, -.115, .035],
                       [.008, -.012, .018, 1.]])
    exact = predict(matrix, points, True)
    # Actual displacement spans roughly 40-80 quads beyond a planar model.
    noisy = exact + rng.normal(0, .04, exact.shape)
    training = np.flatnonzero(~roles)
    outliers = training[::11]
    noisy[outliers] += [70., -45.]
    actual = train(points[~roles], noisy[~roles], True)
    assert actual is not None
    model, keep = actual
    errors = np.linalg.norm(predict(model, points[roles], True) - exact[roles], axis=1)
    assert float(errors.max()) < .2, errors.max()
    assert not np.any(keep[np.isin(training, outliers)])
    planar = train(points[~roles], noisy[~roles], False)
    planar_errors = None
    if planar is not None:
        planar_errors = np.linalg.norm(predict(planar[0], points[roles], False) - exact[roles], axis=1)
        assert float(np.sqrt(np.mean(planar_errors ** 2))) > 2
    wrong = points.copy()
    wrong[:, 2] = rng.permutation(wrong[:, 2])
    shuffled = train(wrong[~roles], noisy[~roles], True)
    shuffled_errors = None
    if shuffled is not None:
        shuffled_errors = np.linalg.norm(predict(shuffled[0], wrong[roles], True) - exact[roles], axis=1)
        assert float(np.sqrt(np.mean(shuffled_errors ** 2))) > 2
    # Poisoning heldout targets cannot alter the trained coefficients.
    poison = noisy.copy()
    poison[roles] += rng.normal(0, 500, poison[roles].shape)
    duplicate = train(points[~roles], poison[~roles], True)
    assert np.array_equal(model, duplicate[0])
    constant_focus = points.copy()
    constant_focus[:, 2] = 12
    assert fit(constant_focus, exact, True) is None
    return dict(fit_count=int((~roles).sum()), heldout_count=int(roles.sum()),
                rejected_training_outliers=len(outliers),
                heldout_rms_quad=float(np.sqrt(np.mean(errors**2))),
                heldout_maximum_quad=float(errors.max()),
                planar_heldout_rms_quad=None if planar_errors is None else float(np.sqrt(np.mean(planar_errors**2))),
                shuffled_focus_heldout_rms_quad=None if shuffled_errors is None else float(np.sqrt(np.mean(shuffled_errors**2))),
                heldout_poisoning_leaves_training_exact=True,
                constant_focus_degeneracy_refused=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run_controls()
    result.update(schema='strehl.mosaic-initializer-controls.v1', command=sys.argv,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  seed=SEED, fixed_trials=TRIALS,
                  coarse_nomination_cutoff_quad=COARSE_INLIER_QUAD,
                  claim='Numerical commissioning only. Focus ordinate is not metric depth; no real geometry or photograph claim. No heldout-selected model constants.')
    with args.out.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps(result, indent=2))
