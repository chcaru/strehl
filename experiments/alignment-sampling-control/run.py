"""One bounded generated-only job; no RAW files, photographic arrays or renders."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HELPER = ROOT/'experiments/m193c-output-grid/bounded-process.py'


def binding(path):
    value = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(value), sha256=hashlib.sha256(value).hexdigest())


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--qualified-from', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE
    out.mkdir(exist_ok=False)
    previous = ROOT/'experiments/chip-differential-blur'
    paths = [HERE/name for name in ('measure.py', 'run.py', 'design.md', 'independent-controls.py', 'independent-plan.md', 'independent-source-review.md')]
    paths += [previous/name for name in ('implementation.py', 'measure.py', 'independent-controls.py', 'resampling-audit.md',
                                        'run-1/result.json', 'run-1/process.json', 'run-1/sources.json')]
    paths += [HELPER, ROOT/'experiments/m12-scorecard/m12-harness.py',
              ROOT/'experiments/quality-september14/local-green-translation.py']
    if args.qualified_from is not None:
        qualified = args.qualified_from.resolve()
        assert qualified.is_relative_to(HERE) and qualified != out
        assert json.loads((qualified/'result.json').read_text())['saved_photo_phase_eligible']
        paths += [qualified/name for name in ('result.json', 'process.json', 'sources.json')]
    sources = [binding(path) for path in paths]
    save(out/'sources.json', sources)
    spec = importlib.util.spec_from_file_location('alignment_sampling_bounded_process', HELPER)
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper
    spec.loader.exec_module(helper)
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE/'measure.py'), '--out', str(out)]
    if args.qualified_from is not None:
        command += ['--qualified-from', str(qualified)]
    fields = dict(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    env, removed = helper.clean_environment(fields.items())
    save(out/'invocation.json', dict(command=command, cwd=str(ROOT), environment=fields, removed_environment=removed,
                                    python=binding(Path(sys.executable)), limits=dict(wall_seconds=180, cpu_seconds=180, committed_bytes=2<<30)))
    api = helper.load_job_api(helper.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = helper.run(command, env, ROOT, out/'process.log', api=api, wall_seconds=180, cpu_seconds=180,
                        committed_bytes=2<<30, log_bytes=4<<20)
    save(out/'process.json', result)
    assert all(binding(Path(row['path'])) == row for row in sources), 'Bound source changed.'
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    print(json.dumps({key: result[key] for key in ('exit_code', 'error', 'wall_seconds')}), flush=True)


if __name__ == '__main__':
    main()
