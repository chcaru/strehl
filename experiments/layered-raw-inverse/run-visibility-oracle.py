"""Root-owned two-case fixed-visibility diagnostic with independent scoring."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'visibility_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    source, reference = HERE / 'screen-1/output', HERE / 'composite-1/output'
    frozen = json.loads((source.parent / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'convergence.py', 'composite-prior.py', 'independent-composite-score.py', 'visibility-oracle.py',
        'visibility-oracle-plan.md', 'visibility-oracle-controls.py',
        'visibility-oracle-independent-plan.md', 'independent-visibility-oracle-review.md',
        'run-visibility-oracle.py'))
    for case in ('flat', 'layered'):
        paths.update(source / case / 'two-layer' / name for name in ('state.pt', 'receipt.json', 'reconstruction.npz'))
        paths.add(source / case / 'observations-u16.npy')
        paths.update(reference / case / 'original' / name for name in
                     ('state.pt', 'receipt.json', 'reconstruction.npz', 'predicted-cfa-2.npy', 'predicted-cfa-6.npy'))
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

    run('visibility-oracle-controls.py', ['prepare', '--out', str(out / 'alpha')],
        out / 'prepare-process', 60)
    alpha_files = [c.ref(p) for p in sorted((out / 'alpha').iterdir()) if p.is_file()]
    assert alpha_files
    run('visibility-oracle.py', ['--source', str(source), '--alpha-root', str(out / 'alpha'),
        '--out', str(out / 'output')], out / 'fit-process', 180)
    assert all(c.ref(Path(row['path'])) == row for row in alpha_files)
    run('visibility-oracle-controls.py', ['score', '--source', str(source),
        '--oracle', str(out / 'output'), '--reference', str(reference), '--out', str(out / 'scored')],
        out / 'scoring-process', 90)
    assert all(c.ref(Path(row['path'])) == row for row in alpha_files)
    c.save(out / 'completion.json', {
        'instrument_completed': True, 'sources_unchanged': True, 'alpha_immutable': alpha_files,
        'fit': c.ref(out / 'output/result.json'),
        'independent_scores': c.ref(out / 'scored/result.json'),
        'scope': 'Known visibility intervention only; original sheet prior and solver unchanged. No photo admission.'})
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
