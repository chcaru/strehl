"""Root-owned fixed colour-gradient coupling test with independent controls."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'matrix_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    source, reference, alpha = HERE / 'screen-1/output', HERE / 'visibility-1/output', HERE / 'visibility-1/alpha'
    frozen = json.loads((HERE / 'cauchy-1/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'matrix-cauchy-prior.py', 'matrix-cauchy-prior-plan.md',
        'matrix-cauchy-controls.py', 'matrix-cauchy-independent-plan.md',
        'independent-matrix-cauchy-review.md', 'run-matrix-cauchy.py',
        'cauchy-1/scored/result.json', 'colour-error-1/scored/result.json'))
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

    run('matrix-cauchy-controls.py', ['commission', '--out', str(out / 'commission')],
        out / 'commission-process', 60)
    assert json.loads((out / 'commission/result.json').read_text())['passed']
    run('matrix-cauchy-prior.py', ['--source', str(source), '--alpha-root', str(alpha),
        '--out', str(out / 'output')], out / 'fit-process', 180)
    run('matrix-cauchy-controls.py', ['score', '--source', str(source), '--candidate', str(out / 'output'),
        '--reference', str(reference), '--out', str(out / 'scored')], out / 'scoring-process', 90)
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_scores=c.ref(out / 'scored/result.json'),
        scope='One spatial-colour gradient coupling prior; fixed known visibility and RAW likelihood; no photo admission'))
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
