"""Resource-bound the six descriptive fits and preserve their exact inputs."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('real_fit_job', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    sources = [c.ref(HERE / name) for name in ('model.py', 'real-check.py', 'real-plan.md', 'real-run.py')]
    c.save(out / 'bindings.json', dict(sources=sources, python=c.ref(Path(sys.executable))))
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / 'real-check.py'),
               '--witness', str(args.witness.resolve()), '--out', str(out / 'output')]
    fields = dict(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
    env, removed = c.b.clean_environment(fields.items())
    c.save(out / 'invocation.json', dict(command=command, environment=fields, removed_environment=removed))
    api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    process = c.b.run(command, env, ROOT, out / 'process.log', api=api,
                      wall_seconds=240, cpu_seconds=360, log_bytes=1 << 20, committed_bytes=1 << 30)
    c.save(out / 'process.json', process)
    print(json.dumps({k: process[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    result = out / 'output/result.json'
    record = json.loads(result.read_text())
    assert record['status'] == 'COMPLETE_DESCRIPTIVE_ONLY' and len(record['cases']) == 6
    c.save(out / 'completion.json', dict(result=c.ref(result), sources_unchanged=True,
        native_noise_calibration=False, ownership_claim=False, image_quality_claim=False))


if __name__ == '__main__':
    main()
