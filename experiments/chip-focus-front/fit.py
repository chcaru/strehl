"""Root driver: one registered fit and independent judgment, preserving failure."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent


def ref(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--controls', type=Path, required=True)
    parser.add_argument('--controls-job', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out != HERE and out.is_relative_to(HERE)
    out.mkdir(exist_ok=False)
    start = time.perf_counter()
    controls = json.loads(args.controls.read_text())
    assert controls['controls_pass'] is True
    completed = json.loads((args.controls_job/'completed.json').read_text())
    assert completed['process_completed'] and completed['sources_unchanged']
    bound = json.loads((args.controls_job/'bindings.json').read_text())
    for name in ('model.py', 'independent-controls.py'):
        assert ref(HERE/name) in bound
    invocation = json.loads((args.controls_job/'invocation.json').read_text())
    command = invocation['command']
    assert Path(command[command.index('--out')+1]).resolve() == args.controls.resolve()
    stage = json.loads((args.stage/'receipt.json').read_text())
    assert stage['status'] == 'COMPLETE_FIXED_299_SOURCE_CURVES'
    curves_path = args.stage/'curves.npz'
    assert stage['curves'] == ref(curves_path)
    model = load('chip_front_registered_model', HERE/'model.py')
    review = load('chip_front_independent_judge', HERE/'independent-controls.py')
    with np.load(curves_path, allow_pickle=False) as data:
        xy = data['xy_native'].copy()
        train = data['train_mask'].copy()
        contrast = data['contrast'].copy()
        assert contrast.shape == (299, 42, 2) and contrast.dtype == np.float32
        assert np.array_equal(data['source_ordinals'], np.arange(299))
    fixed_xy, fixed_train = review.fixed_geometry()
    assert np.array_equal(xy, fixed_xy) and np.array_equal(train, fixed_train)
    fitted = model.fit_model(xy, contrast, train)
    judgment = review.judge(model, fitted, xy, contrast, train)
    save(out/'model.json', fitted)
    save(out/'judgment.json', judgment)
    if fitted['status'] == 'fit_completed':
        evaluated = model.evaluate_profiles(fitted, xy, contrast)
        np.savez(out/'predictions.npz', **evaluated)
    save(out/'receipt.json', dict(status='REGISTERED_FIT_EVALUATED',
        controls=ref(args.controls), stage_receipt=ref(args.stage/'receipt.json'),
        controls_job_bindings=ref(args.controls_job/'bindings.json'),
        curves=ref(curves_path), model=ref(out/'model.json'), judgment=ref(out/'judgment.json'),
        predictions=ref(out/'predictions.npz') if fitted['status'] == 'fit_completed' else None,
        elapsed_seconds=time.perf_counter()-start,
        predictive_proxy_admitted=judgment['predictive_proxy_admitted'],
        photographic_quality_admitted=False, fit_attempts=1, command=sys.argv))
    print(json.dumps(dict(status=fitted['status'],
        predictive_proxy_admitted=judgment['predictive_proxy_admitted'],
        coverage_pass=judgment['coverage_pass']), indent=2), flush=True)


if __name__ == '__main__':
    main()
