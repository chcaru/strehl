"""Run the independent, small algebra falsifier under existing job limits."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('relative_screen_job', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    sources = [c.ref(HERE / name) for name in ('model.py', 'independent-controls.py',
                                             'independent-brief.md', 'independent-plan.md', 'screen-run.py')]
    c.save(out / 'bindings.json', dict(sources=sources, python=c.ref(Path(sys.executable))))
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
               str(HERE / 'independent-controls.py'), '--out', str(out / 'output')]
    try:
        fields = dict(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
        env, removed = c.b.clean_environment(fields.items())
        c.save(out / 'invocation.json', dict(command=command, environment=fields, removed_environment=removed))
        api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
        process = c.b.run(command, env, ROOT, out / 'process.log', api=api,
                          wall_seconds=120, cpu_seconds=180, log_bytes=1 << 20, committed_bytes=1 << 30)
        c.save(out / 'process.json', process)
        print(json.dumps({k: process[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
        assert process['exit_code'] == 0 and process['error'] is None
        assert process['terminal_job_accounting'] and not process['cleanup_errors']
    finally:
        assert all(c.ref(Path(row['path'])) == row for row in sources), 'Source changed during execution'
        process = json.loads((out / 'process.json').read_text())
        screen = out / 'output/screen.json'
        result = json.loads(screen.read_text()) if screen.exists() else None
        c.save(out / 'completion.json', dict(process=c.ref(out / 'process.json'),
            screen=c.ref(screen) if screen.exists() else None, sources_unchanged=True,
            status=result['status'] if result else 'NO_SCREEN_RESULT', exit_code=process['exit_code'],
            actual_consumer_admitted=False,
            scope='Algebra and model adequacy falsifier only; no native covariance, ownership or image-quality admission.'))


if __name__ == '__main__':
    main()
