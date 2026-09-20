"""Root-owned read-only local objective diagnostic and independent scoring."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'direction_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
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
    checkpoint = HERE / 'visibility-1/output/layered/fixed-alpha'
    frozen = json.loads((HERE / 'visibility-1/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'radiance-direction.py', 'radiance-direction-plan.md',
        'radiance-direction-controls.py', 'radiance-direction-independent-plan.md',
        'independent-radiance-direction-review.md', 'run-radiance-direction.py'))
    paths.update(p for p in checkpoint.iterdir() if p.is_file())
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

    run('radiance-direction-controls.py', ['prepare', '--out', str(out / 'directions')], out / 'prepare-process')
    supplied = [c.ref(p) for p in sorted((out / 'directions').iterdir()) if p.is_file()]
    run('radiance-direction.py', ['--checkpoint', str(checkpoint), '--source', str(source), '--directions', str(out / 'directions'),
        '--out', str(out / 'output')], out / 'probe-process')
    assert supplied and all(c.ref(Path(row['path'])) == row for row in supplied)
    run('radiance-direction-controls.py', ['score', '--source', str(source), '--checkpoint', str(checkpoint),
        '--directions', str(out / 'directions'), '--diagnostic', str(out / 'output'), '--out', str(out / 'scored')],
        out / 'scoring-process')
    assert all(c.ref(Path(row['path'])) == row for row in supplied)
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_scores=c.ref(out / 'scored/result.json'), direction_files=supplied,
        scope='No optimization; separate local objective derivatives and truth changes, no photo admission'))
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
