"""Root-owned read-only attribution of saved reconstruction colour errors."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'colour_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    frozen = json.loads((HERE / 'cauchy-1/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(p for p in HERE.glob('colour-error*') if p.is_file() and p.suffix in ('.py', '.md'))
    paths.update(HERE / name for name in ('colour-error-decomposition.py', 'colour-error-controls.py',
        'independent-colour-error-review.md', 'run-colour-error.py'))
    for run in ('visibility-1', 'shot-prior-1', 'cauchy-1'):
        paths.add(HERE / run / 'scored/result.json')
        for case in ('flat', 'layered'):
            paths.add(HERE / run / 'output' / case / 'fixed-alpha/reconstruction.npz')
            paths.add(HERE / 'screen-1/output' / case / 'truth-rgb-f32.npy')
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

    run('colour-error-controls.py', ['commission', '--out', str(out / 'commission')],
        out / 'commission-process')
    assert json.loads((out / 'commission/result.json').read_text())['passed']
    run('colour-error-decomposition.py', ['--out', str(out / 'decomposed')], out / 'decompose-process')
    run('colour-error-controls.py', ['score', '--candidate', str(out / 'decomposed'),
        '--out', str(out / 'scored')], out / 'scoring-process')
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_scores=c.ref(out / 'scored/result.json'),
        scope='Read-only colour-error scale decomposition; no fit, restoration, or optical-nullspace claim'))
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
