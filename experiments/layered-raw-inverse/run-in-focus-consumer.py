"""Root-owned read-only evaluation of a separately declared output consumer."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'in_focus_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    frozen = json.loads((HERE / 'matrix-cauchy-1/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'in-focus-consumer.py', 'in-focus-consumer-plan.md',
        'in-focus-consumer-assessment.md', 'optical-output-independent-critique.md',
        'in-focus-controls.py', 'in-focus-independent-plan.md',
        'independent-in-focus-review.md', 'run-in-focus-consumer.py'))
    for run in ('visibility-1', 'shot-prior-1', 'cauchy-1', 'matrix-cauchy-1'):
        paths.add(HERE / run / 'scored/result.json')
        for case in ('flat', 'layered'):
            folder = HERE / run / 'output' / case / 'fixed-alpha'
            paths.update(folder / name for name in ('reconstruction.npz', 'receipt.json'))
    for case in ('flat', 'layered'):
        folder = HERE / 'screen-1/output' / case
        paths.update(folder / name for name in (
            'truth-rgb-f32.npy', 'mean-rgb-f32.npy', 'oracle-bound-rgb-f32.npy',
            'far-only/reconstruction.npz', 'far-only/receipt.json'))
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    fields = {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
              'PYTHONDONTWRITEBYTECODE': '1'}

    def run(script, arguments, destination):
        destination.mkdir()
        c.job([sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / script), *arguments],
              fields, destination, wall=60)
        assert all(c.ref(Path(row['path'])) == row for row in sources)

    run('in-focus-controls.py', ['commission', '--out', str(out / 'commission')],
        out / 'commission-process')
    assert json.loads((out / 'commission/result.json').read_text())['passed']
    run('in-focus-consumer.py', ['--out', str(out / 'delivered')], out / 'delivery-process')
    run('in-focus-controls.py', ['score', '--candidate', str(out / 'delivered'),
        '--out', str(out / 'scored')], out / 'scoring-process')
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_scores=c.ref(out / 'scored/result.json'),
        scope='Separate fixed in-focus consumer; no fit, old-result reclassification, or photographic admission'))
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
