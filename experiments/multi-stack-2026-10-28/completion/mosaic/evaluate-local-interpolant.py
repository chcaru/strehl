"""Evaluate one predeclared FIT-only local model; keep every heldout visible."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

module_path = Path(__file__).with_name('local-interpolant-controls.py')
spec = importlib.util.spec_from_file_location('local_interpolant', module_path)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
np = api.np

parser = argparse.ArgumentParser()
parser.add_argument('sites', type=Path)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
data = json.loads(args.sites.read_text())
rows = [record['receipt'] for record in data['records']]
assert data['passes'] == 2
assert all(r['candidate']['pass_a'] == 0 and r['candidate']['pass_b'] == 1 for r in rows)
p = np.array([r['candidate']['point_a_quad'] for r in rows])
q = np.array([r['refined_b_quad'] for r in rows])
training = np.array([r['candidate']['role'] == 'fit' for r in rows])
assert int(training.sum()) == data['fit_sites']
assert int((~training).sum()) == data['heldout_sites']
model = api.fit(p[training], q[training])
prediction = api.predict(model, p)
errors = np.linalg.norm(prediction-q, axis=1)
distances = np.linalg.norm(p[:, None, :]-p[training][None, :, :], axis=2)
nearest = distances.min(axis=1)
heldout = [dict(id=row['candidate']['id'], error_quad=float(error),
                nearest_fit_quad=float(distance), point_a_quad=point.tolist(),
                displacement_quad=(target-point).tolist(),
                predicted_displacement_quad=(pred-point).tolist())
           for row, point, target, pred, error, distance, fit in
           zip(rows, p, q, prediction, errors, nearest, training) if not fit]
result = dict(schema='strehl.mosaic-local-interpolant-evaluation.v1', command=sys.argv,
              script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              model_source_sha256=hashlib.sha256(module_path.read_bytes()).hexdigest(),
              input_sites_sha256=hashlib.sha256(args.sites.read_bytes()).hexdigest(),
              scale_quad=api.SCALE_QUAD, smoothing=0,
              fit=api.stats(errors[training]), heldout=api.stats(errors[~training]),
              heldout_sites=heldout,
              claim='FIT-only unsmoothed minimum-bending model diagnostic. Same fixed real independent native sites, no heldout-selected constants, output mesh, source resampling, or photographic claim. Training interpolation is not quality evidence.')
with args.out.open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({key:result[key] for key in ['fit','heldout']}, indent=2))
