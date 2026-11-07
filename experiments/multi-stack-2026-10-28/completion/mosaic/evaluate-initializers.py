"""Evaluate frozen FIT-only initializers on production-selected native sites."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

module_path = Path(__file__).with_name('initializer-controls.py')
spec = importlib.util.spec_from_file_location('initializer', module_path)
model_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model_api)
np = model_api.np

parser = argparse.ArgumentParser()
parser.add_argument('sites', type=Path)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
data = json.loads(args.sites.read_text())
rows = [item['receipt'] for item in data['records']]
assert data['passes'] == 2
assert all(r['candidate']['pass_a'] == 0 and r['candidate']['pass_b'] == 1 for r in rows)
points = np.array([r['candidate']['point_a_quad'] + [r['candidate']['source_a']] for r in rows])
targets = np.array([r['refined_b_quad'] for r in rows])
fit_mask = np.array([r['candidate']['role'] == 'fit' for r in rows])
assert int(fit_mask.sum()) == data['fit_sites']
assert int((~fit_mask).sum()) == data['heldout_sites']


def stats(errors):
    if len(errors) == 0:
        return {'count': 0}
    return dict(count=len(errors), rms_quad=float(np.sqrt(np.mean(errors**2))),
                median_quad=float(np.median(errors)), maximum_quad=float(errors.max()),
                within_final_half_quad=int(np.count_nonzero(errors <= .5)))


results = []
for name, use_focus in [('planar_projective', False), ('projective_witness_ordinal', True)]:
    trained = model_api.train(points[fit_mask], targets[fit_mask], use_focus)
    if trained is None:
        results.append(dict(model=name, refused='no supported FIT-only coarse consensus'))
        continue
    matrix, retained = trained
    predicted = model_api.predict(matrix, points, use_focus)
    if predicted is None:
        results.append(dict(model=name, refused='projective denominator leaves bounded domain'))
        continue
    errors = np.linalg.norm(predicted-targets, axis=1)
    # All heldouts remain in the evaluation. Source ordinal is only an untrusted
    # runtime regressor; it is not substituted for a measured metric depth.
    results.append(dict(model=name, coefficients=matrix.tolist(),
                        fit_selected=int(retained.sum()), fit_total=int(fit_mask.sum()),
                        fit_all=stats(errors[fit_mask]), heldout=stats(errors[~fit_mask]),
                        all_errors=[dict(id=r['candidate']['id'],role=r['candidate']['role'],
                                         error_quad=float(e)) for r,e in zip(rows, errors)]))
    # Same design with a fixed shuffled ordinate, same hypothesis search size.
    if use_focus:
        wrong = points.copy()
        wrong[:,2] = np.random.default_rng(model_api.SEED).permutation(wrong[:,2])
        negative = model_api.train(wrong[fit_mask], targets[fit_mask], True)
        wrong_prediction = None if negative is None else model_api.predict(negative[0],wrong,True)
        results.append(dict(model='shuffled_witness_ordinal',
                            refused=wrong_prediction is None,
                            heldout=None if wrong_prediction is None else stats(np.linalg.norm(wrong_prediction[~fit_mask]-targets[~fit_mask],axis=1))))

result=dict(schema='strehl.mosaic-initializer-evaluation.v1',command=sys.argv,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            initializer_source_sha256=hashlib.sha256(module_path.read_bytes()).hexdigest(),
            input_sites_sha256=hashlib.sha256(args.sites.read_bytes()).hexdigest(),
            exact_production_sites=dict(fit=int(fit_mask.sum()),heldout=int((~fit_mask).sum())),
            fixed_nomination_cutoff_quad=model_api.COARSE_INLIER_QUAD,
            fixed_training_trials=model_api.TRIALS, models=results,
            scope='FIT-only diagnostic initializer prediction. No heldout parameter selection, final model certification, source resampling, or photograph. Witness ordinal is not calibrated depth. Final geometry must retain all selected native sites and pass unchanged heldout/loop/Jacobian/coverage gates.')
with args.out.open('x') as f:
    json.dump(result,f,indent=2)
    f.write('\n')
print(json.dumps([{k:v for k,v in r.items() if k not in ['all_errors','coefficients']} for r in results],indent=2))
