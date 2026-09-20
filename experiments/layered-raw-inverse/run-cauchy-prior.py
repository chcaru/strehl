"""Root-owned fixed robust-prior experiment, independently commissioned/scored."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'cauchy_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
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
    frozen = json.loads((HERE / 'shot-prior-1/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'cauchy-prior.py', 'cauchy-prior-plan.md', 'cauchy-prior-controls.py',
        'cauchy-prior-independent-plan.md', 'independent-cauchy-prior-review.md',
        'run-cauchy-prior.py', 'shot-prior-next-assessment.md', 'visibility-update-design.md'))
    paths.add(HERE / 'shot-prior-1/scored/result.json')
    paths.update(p for p in alpha.iterdir() if p.is_file())
    for case in ('flat', 'layered'):
        paths.update(p for p in (reference / case / 'fixed-alpha').iterdir() if p.is_file())
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

    run('cauchy-prior-controls.py', ['commission', '--out', str(out / 'commission')],
        out / 'commission-process', 60)
    assert json.loads((out / 'commission/result.json').read_text())['passed']
    run('cauchy-prior.py', ['--source', str(source), '--alpha-root', str(alpha),
        '--out', str(out / 'output')], out / 'fit-process', 180)
    run('cauchy-prior-controls.py', ['score', '--source', str(source), '--candidate', str(out / 'output'),
        '--reference', str(reference), '--out', str(out / 'scored')], out / 'scoring-process', 90)
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_scores=c.ref(out / 'scored/result.json'),
        scope='One original-scale robust-prior change, oracle alpha, fixed RAW likelihood/solver; no photo admission'))
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
