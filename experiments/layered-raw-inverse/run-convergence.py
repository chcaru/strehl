"""Root-owned bounded continuation and separately executed independent scoring."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'convergence_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
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
    old_sources = json.loads((source.parent / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in old_sources)
    paths = {Path(row['path']) for row in old_sources}
    paths.update(HERE / name for name in (
        'convergence.py', 'convergence-plan.md', 'independent-convergence-score.py',
        'independent-convergence-plan.md', 'independent-convergence-review.md',
        'independent-convergence-storage-review.md',
        'run-convergence.py'))
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    fields = {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
              'PYTHONDONTWRITEBYTECODE': '1'}
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / 'convergence.py'),
               '--source', str(source), '--out', str(out / 'output')]
    c.job(command, fields, out, wall=180)
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    continued = json.loads((out / 'output/result.json').read_text())
    for arm in continued['arms']:
        receipt = json.loads(Path(arm['receipt']).read_text())
        assert receipt['noncontiguous_gradients_converted'] > 0
        assert all(row['gradient_storage_logical_exact'] for row in receipt['closure_history']
                   if row['evaluation_status'] == 'complete')
    scoring = out / 'scoring-process'
    scoring.mkdir()
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
               str(HERE / 'independent-convergence-score.py'), '--source', str(source),
               '--continuation', str(out / 'output'), '--out', str(out / 'scored')]
    c.job(command, fields, scoring, wall=60)
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    c.save(out / 'completion.json', {
        'instrument_completed': True, 'sources_unchanged': True,
        'continuation': c.ref(out / 'output/result.json'),
        'independent_scores': c.ref(out / 'scored/result.json'),
        'scope': 'Three fixed saved states, unchanged objective; first screen and optical refusal remain.'})
    print(json.dumps({'completed': True, 'scores': c.ref(out / 'scored/result.json')}), flush=True)


if __name__ == '__main__':
    main()
