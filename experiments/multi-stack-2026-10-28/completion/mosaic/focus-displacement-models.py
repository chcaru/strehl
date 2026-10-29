"""Fixed FIT-only model family; original ordinals are covariates, never depth.

Select a model by five spatial-block folds over FIT sites only. Evaluate the
selected model once on the independent held sites. No window/weight search.
The saved point cloud is diagnostic; this does not create output geometry.
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

NAMES = ('affine', 'quadratic', 'affine_a', 'affine_ab', 'affine_focus_cross',
         'quadratic_ab', 'quadratic_focus_cross', 'affine_focus_squared')
RULE = ('fixed-eight-model-family; coordinates/1000quad; original ordinals normalized by '
        'declared pass lengths; five folds=(3*floor(x/512)+floor(y/512))mod5; '
        'select minimum pooled FIT-fold RMS with listed-order tie; ordinary unweighted '
        'least squares; reject rank deficiency; no held-data selection; joint ordinal '
        'permutation seed20261029; half-quad final bar unchanged')


def design(features, name):
    x, y, a, b = features.T
    affine = [np.ones(len(x)), x, y]
    quadratic = affine + [x*x, x*y, y*y]
    return np.array({
        'affine': affine,
        'quadratic': quadratic,
        'affine_a': affine + [a],
        'affine_ab': affine + [a, b],
        'affine_focus_cross': affine + [a, b, x*a, y*a, x*b, y*b],
        'quadratic_ab': quadratic + [a, b],
        'quadratic_focus_cross': quadratic + [a, b, x*a, y*a, x*b, y*b],
        'affine_focus_squared': affine + [a, b, a*a, a*b, b*b],
    }[name]).T


def fit(features, target, name):
    matrix = design(features, name)
    coefficients, _, rank, singular = np.linalg.lstsq(matrix, target, rcond=None)
    if rank != matrix.shape[1] or len(features) < 2*matrix.shape[1]:
        raise ValueError('insufficient independent FIT rows')
    return coefficients, float(singular[0]/singular[-1])


def stats(error):
    error = np.linalg.norm(error, axis=1)
    return dict(count=len(error), rms_quad=float(np.sqrt(np.mean(error**2))),
                median_quad=float(np.median(error)), maximum_quad=float(error.max()),
                within_half_quad=int(np.count_nonzero(error <= .5)))


def cross_validate(features, target, points):
    fold = ((3*np.floor(points[:, 0]/512)+np.floor(points[:, 1]/512)) % 5).astype(int)
    assert set(fold) == set(range(5)), 'all five fixed spatial folds required'
    results = []
    for name in NAMES:
        prediction = np.full(target.shape, np.nan)
        conditions = []
        try:
            for value in range(5):
                train, test = fold != value, fold == value
                coefficients, condition = fit(features[train], target[train], name)
                prediction[test] = design(features[test], name) @ coefficients
                conditions.append(condition)
            results.append(dict(model=name, result=stats(prediction-target),
                                maximum_condition=max(conditions), folds=np.bincount(fold).tolist()))
        except ValueError as error:
            results.append(dict(model=name, refusal=str(error)))
    selected = min((r for r in results if 'result' in r), key=lambda r: r['result']['rms_quad'])
    return selected['model'], results


def controls():
    rng = np.random.default_rng(20261029)
    points = rng.uniform([0, 0], [3515, 2343], (180, 2))
    ordinals = rng.uniform(-.5, .5, (180, 2))
    features = np.c_[points/1000, ordinals]
    x, y, a, b = features.T
    # Two-view ordinal-dependent parallax with measured-order several-quad
    # curvature. The generating expression is independent of design() assembly.
    target = np.c_[-45 + 2*x - y + 7*a - 3*b + 4*x*a,
                   -10 - x + .4*y + 5*b - 2*y*a]
    chosen, table = cross_validate(features, target, points)
    assert chosen in ('affine_focus_cross', 'quadratic_focus_cross')
    assert min(r['result']['rms_quad'] for r in table if 'result' in r) < 1e-10
    affine = next(r for r in table if r['model'] == 'affine')['result']['rms_quad']
    assert affine > 2., 'plant must expose omitted ordinal dependence'
    scrambled = features.copy()
    scrambled[:, 2:] = features[rng.permutation(len(features)), 2:]
    _, foil = cross_validate(scrambled, target, points)
    assert min(r['result']['rms_quad'] for r in foil if 'result' in r) > 2.
    # An unobserved depth jump is not licensed by a smooth fitted model.
    held = rng.uniform([0, 0], [3515, 2343], (20, 2))
    hf = np.c_[held/1000, rng.uniform(-.5, .5, (20, 2))]
    coefficients, _ = fit(features, target, chosen)
    prediction = design(hf, chosen) @ coefficients
    jump_truth = prediction + [4., -3.]
    jump = stats(prediction-jump_truth)
    assert jump['within_half_quad'] == 0 and jump['rms_quad'] == 5.
    return dict(positive_selected=chosen, omitted_ordinal_rms_quad=affine,
                shuffled_ordinal_best_cv_rms_quad=min(r['result']['rms_quad'] for r in foil if 'result' in r),
                unobserved_depth_jump=jump)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sites', type=Path)
    parser.add_argument('--pass-lengths', nargs=2, required=True, type=int)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    control = controls()  # Always before opening real observations.
    data = json.loads(args.sites.read_text())
    rows = [r['receipt'] for r in data['records']]
    fit_mask = np.array([r['candidate']['role'] == 'fit' for r in rows])
    points = np.array([r['candidate']['point_a_quad'] for r in rows])
    targets = np.array([r['refined_b_quad'] for r in rows])-points
    ordinals = np.array([[r['candidate']['source_a'], r['candidate']['source_b']-args.pass_lengths[0]] for r in rows])
    assert np.all(ordinals >= 0) and np.all(ordinals < args.pass_lengths)
    features = np.c_[points/1000, ordinals/(np.array(args.pass_lengths)-1)-.5]
    chosen, table = cross_validate(features[fit_mask], targets[fit_mask], points[fit_mask])
    coefficients, condition = fit(features[fit_mask], targets[fit_mask], chosen)
    prediction = design(features, chosen) @ coefficients
    residual = prediction-targets
    rng = np.random.default_rng(20261029)
    foil_features = features[fit_mask].copy()
    foil_features[:, 2:] = foil_features[rng.permutation(len(foil_features)), 2:]
    foil_name, foil = cross_validate(foil_features, targets[fit_mask], points[fit_mask])
    affine, _ = fit(features[fit_mask], targets[fit_mask], 'affine')
    affine_residual = targets[fit_mask]-design(features[fit_mask], 'affine') @ affine
    corr = np.corrcoef(np.c_[features[fit_mask], affine_residual].T)[:4, 4:]
    result = dict(schema='strehl.mosaic-focus-displacement-models.v1', command=sys.argv,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  input_sites_sha256=hashlib.sha256(args.sites.read_bytes()).hexdigest(),
                  rule=RULE, controls=control, pass_lengths=args.pass_lengths,
                  selected_by_fit_only_cv=chosen, fit_cv_models=table,
                  shuffled_ordinal_fit_cv_models=foil, shuffled_ordinal_selected=foil_name,
                  fit=stats(residual[fit_mask]), heldout=stats(residual[~fit_mask]),
                  coefficients=coefficients.tolist(), condition=condition,
                  fit_affine_residual_correlations=dict(zip(('x', 'y', 'source_ordinal_a', 'source_ordinal_b'), corr.tolist())),
                  observations=[dict(id=r['candidate']['id'], role=r['candidate']['role'],
                      point_quad=points[i].tolist(), original_ordinals=ordinals[i].tolist(),
                      measured_displacement_quad=targets[i].tolist(),prediction_quad=prediction[i].tolist(),
                      residual_quad=residual[i].tolist()) for i,r in enumerate(rows)],
                  scope='Conditional saved-native diagnostic only. Ordinal covariates can reflect within-pass placement error or parallax; they are not physical depth. No output map, visibility, hull or photographic certificate.')
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('selected_by_fit_only_cv','fit','heldout','fit_affine_residual_correlations')},indent=2))


if __name__ == '__main__':
    main()
