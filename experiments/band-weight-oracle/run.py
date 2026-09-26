"""Bounded root execution of a truth-assisted representation diagnostic."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('oracle_jobs', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['commission', 'check-commission', 'solve', 'check'])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--dataset', type=Path, default=ROOT / 'experiments/learned-band-guide/export-1/output/dataset.json')
    p.add_argument('--commission', type=Path)
    p.add_argument('--qualification', type=Path)
    p.add_argument('--predictions', type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    dataset = args.dataset.resolve()
    paths = {dataset, ROOT / 'experiments/learned-band-guide/train.py',
             ROOT / 'experiments/full-context-placement/run.py',
             ROOT / 'experiments/m193c-output-grid/bounded-process.py',
             ROOT / 'experiments/m12-scorecard/m12-harness.py',
             ROOT / 'experiments/learned-band-guide/commission-1/output/commission.json',
             ROOT / 'experiments/learned-band-guide/independent-fixtures.rs',
             ROOT / 'experiments/learned-band-guide/replay-1/output/screen.json',
             ROOT / 'experiments/learned-band-guide/export-1/output/pretraining.json'}
    paths.update(p.resolve() for p in HERE.iterdir() if p.suffix in ('.py', '.md'))
    for case in json.loads(dataset.read_text())['heldout']:
        cp = Path(case)
        paths.add(cp)
        paths.update(cp.parent / row['file'] for row in json.loads(cp.read_text())['arrays'].values())
    for path in (args.commission, args.qualification, args.predictions):
        if path is not None:
            if path.is_dir():
                paths.update(p.resolve() for p in path.rglob('*') if p.is_file())
            else:
                paths.add(path.resolve())
    inputs = [c.ref(path) for path in sorted(paths)]
    c.save(out / 'inputs.json', inputs)
    script = 'independent-check.py' if args.phase.startswith('check') else 'solve.py'
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / script),
               args.phase, '--dataset', str(dataset), '--out', str(out / 'output')]
    if args.commission is not None:
        command += ['--commission', str(args.commission.resolve())]
    if args.predictions is not None:
        command += ['--predictions', str(args.predictions.resolve())]
    if args.phase == 'solve':
        assert args.qualification is not None and args.commission is not None
        assert args.qualification.resolve() == (args.commission / 'commission.json').resolve()
        qualification = json.loads(args.qualification.read_text())
        assert qualification['passed'] is True
    fields = dict(CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='137', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env, removed = c.b.clean_environment(fields.items())
    c.save(out / 'invocation.json', dict(command=command, environment=fields, removed_environment=removed))
    api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out / 'process.log', api=api,
        wall_seconds=240, cpu_seconds=1800, log_bytes=16 << 20, committed_bytes=8 << 30)
    c.save(out / 'process.json', result)
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    assert all(c.ref(Path(row['path'])) == row for row in inputs)
    c.save(out / 'completion.json', dict(process_completed=True, inputs_unchanged=True,
        scope='Truth-assisted diagnostic only. No learned-model, photograph or deployment admission.'))


if __name__ == '__main__':
    main()
