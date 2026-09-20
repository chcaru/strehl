"""Root-owned paired free-visibility test with fixed predeclared output target."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'free_visibility_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    source = HERE / 'screen-1/output'
    frozen = json.loads((HERE / 'in-focus-2/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'free-visibility.py', 'free-visibility-plan.md',
        'free-visibility-controls.py', 'free-visibility-independent-plan.md',
        'independent-free-visibility-review.md', 'run-free-visibility.py',
        'composite-prior.py', 'in-focus-2/scored/result.json',
        'in-focus-2/commission/result.json', 'in-focus-2/delivered/result.json',
        'independent-in-focus-results.md'))
    paths.update((HERE / 'in-focus-2/delivered').rglob('*.npy'))
    for case in ('flat', 'layered', 'far-only', 'angular-mismatch'):
        paths.update(p for p in (source / case).rglob('*') if p.is_file())
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    fields = {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
              'PYTHONDONTWRITEBYTECODE': '1'}

    def run(script, arguments, destination, limit):
        destination.mkdir()
        c.job([sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / script), *arguments],
              fields, destination, wall=limit)
        assert all(c.ref(Path(row['path'])) == row for row in sources)

    run('free-visibility-controls.py', ['commission', '--out', str(out / 'commission')],
        out / 'commission-process', 60)
    assert json.loads((out / 'commission/result.json').read_text())['passed']
    run('free-visibility.py', ['--source', str(source), '--out', str(out / 'output')],
        out / 'fit-process', 600)
    run('free-visibility-controls.py', ['score', '--source', str(source),
        '--candidate', str(out / 'output'), '--out', str(out / 'scored')],
        out / 'scoring-process', 90)
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_scores=c.ref(out / 'scored/result.json'),
        scope='Same-driver Huber/matrix free-visibility fits; fixed in-focus target; no photographic admission'))
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
