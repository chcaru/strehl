"""Fixed extra flat seeds; distinguish solver refusal from model mismatch."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEEDS = (2027, 48311, 90217, 314159)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def worker(out):
    import numpy as np
    m = module('flat_stress_model', HERE / 'model.py')
    shape = (4, 256, 256)
    train = np.zeros(shape[1:], bool)
    train[38:84, 38:89] = True
    train[147:199, 38:89] = True
    protected = np.zeros(shape[1:], bool)
    protected[78:218, 130:224] = True
    held = np.zeros(shape[1:], bool)
    held[93:151, 143:184] = True
    records = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        a = np.rint(800 + rng.normal(0, 5, shape)).astype(np.float32)
        b = np.rint(800 + rng.normal(0, 5, shape)).astype(np.float32)
        directions = []
        for source, target in ((a, b), (b, a)):
            fit = m.fit(source, target, train, protected_mask=protected)
            result = m.evaluate(source, target, fit, held, rmse_limit4=np.full(4, 30.0))
            directions.append(dict(fit_status=fit.status, params=fit.params,
                                   fit_reasons=fit.reasons, evaluation=result))
        f, r = [d['evaluation'] for d in directions]
        exclusive = ((f['status'] == 'compatible' and r['status'] == 'refused') or
                     (r['status'] == 'compatible' and f['status'] == 'refused'))
        residual_mismatch = [bool('held-out-residual-exceeds-caller-allowance' in d['evaluation']['reasons'])
                             for d in directions]
        records.append(dict(seed=seed, directions=directions,
                            legacy_exclusive_acceptance=exclusive,
                            genuine_held_out_mismatch=residual_mismatch))
        report = dict(seeds=SEEDS, records=records, source_sigma_dn=5,
                      held_out_limit4=[30]*4, actual_consumer_admitted=False,
                      scope='Flat has no focus order; numerical refusal is not negative model evidence')
        (out / 'screen.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(records[-1]), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--worker', action='store_true')
    args = ap.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE)
    if args.worker:
        worker(out)
        return
    assert not out.exists()
    out.mkdir()
    c = module('flat_stress_job', ROOT / 'experiments/full-context-placement/run.py')
    bindings = [c.ref(HERE / p) for p in ('model.py', 'flat-refusal-stress.py', 'flat-refusal-plan.md')]
    c.save(out / 'bindings.json', dict(sources=bindings, python=c.ref(Path(sys.executable))))
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(Path(__file__)),
               '--worker', '--out', str(out)]
    fields = dict(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
    env, removed = c.b.clean_environment(fields.items())
    c.save(out / 'invocation.json', dict(command=command, environment=fields, removed=removed))
    api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out / 'process.log', api=api,
                     wall_seconds=20, cpu_seconds=30, log_bytes=1 << 20, committed_bytes=1 << 30)
    c.save(out / 'process.json', result)
    assert all(c.ref(Path(row['path'])) == row for row in bindings)
    c.save(out / 'completion.json', dict(process=c.ref(out / 'process.json'),
           screen=c.ref(out / 'screen.json') if (out / 'screen.json').exists() else None,
           sources_unchanged=True, actual_consumer_admitted=False))
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None


if __name__ == '__main__':
    main()
