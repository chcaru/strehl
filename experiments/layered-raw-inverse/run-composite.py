"""Root-owned bounded paired experiment; independent controls run first."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'composite_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
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
    frozen = json.loads((source.parent / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'convergence.py', 'composite-prior.py', 'composite-prior-plan.md',
        'independent-composite-score.py', 'independent-composite-plan.md',
        'independent-composite-review.md', 'run-composite.py'))
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    fields = {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
              'PYTHONDONTWRITEBYTECODE': '1'}

    def run(script, arguments, destination, limit):
        destination.mkdir()
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / script), *arguments]
        c.job(command, fields, destination, wall=limit)
        assert all(c.ref(Path(row['path'])) == row for row in sources)

    run('independent-composite-score.py', ['commission', '--out', str(out / 'commission')],
        out / 'commission-process', 60)
    controls = json.loads((out / 'commission/result.json').read_text())
    assert controls['passed'], 'Prior commissioning failed; no optimization permitted'
    run('composite-prior.py', ['--source', str(source), '--out', str(out / 'output')],
        out / 'fit-process', 600)
    run('independent-composite-score.py', ['score', '--source', str(source),
        '--comparison', str(out / 'output'), '--out', str(out / 'scored')],
        out / 'scoring-process', 90)
    c.save(out / 'completion.json', {
        'instrument_completed': True, 'sources_unchanged': True,
        'commission': c.ref(out / 'commission/result.json'),
        'fit': c.ref(out / 'output/result.json'),
        'independent_scores': c.ref(out / 'scored/result.json'),
        'scope': 'Only prior placement changes; same generated original CFA and optimizer. No photo admission.'})
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
