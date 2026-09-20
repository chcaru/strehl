"""Bounded phase-aware reconstruction, with a flat-quality stop before layered fits."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'phase_aware_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    frozen = read(HERE / 'pupil-stencil-1/sources.json')
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'phase-aware.py', 'phase-aware-plan.md', 'phase-aware-controls.py',
        'phase-aware-independent-plan.md', 'independent-phase-aware-review.md',
        'run-phase-aware.py', 'in-focus-2/scored/result.json',
        'in-focus-2/delivered/result.json'))
    paths.update((HERE / 'in-focus-2/delivered').rglob('*.npy'))
    old = ROOT / 'experiments/quality-september14'
    paths.update(old / name for name in (
        'chip-corrected-sample-diversity-1.json', 'chip-corrected-sample-diversity.py',
        'chip-local-sample-diversity.py', 'chip-local-sample-diversity-1.json',
        'chip-baseline-1/chip.warpmap.txt', 'local-green-translation-1/result.json'))
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    data_bindings = []
    fields = {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
              'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_CACHE_DISABLE': '1'}

    def unchanged():
        assert all(c.ref(Path(row['path'])) == row for row in sources + data_bindings)

    def run(script, arguments, label, limit):
        unchanged()
        process = out / (label + '-process')
        process.mkdir()
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
                   str(HERE / script), *map(str, arguments)]
        env, removed = c.b.clean_environment(fields.items())
        c.save(process / 'invocation.json', dict(command=command, environment=fields,
            removed_environment=removed, runner=c.ref(Path(__file__))))
        api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
        result = c.b.run(command, env, ROOT, process / 'process.log', api=api,
            wall_seconds=limit, cpu_seconds=3600, log_bytes=16 << 20, committed_bytes=8 << 30)
        c.save(process / 'process.json', result)
        unchanged()
        print(json.dumps(dict(stage=label, exit_code=result['exit_code'],
                              wall_seconds=result['wall_seconds'], error=result['error'])), flush=True)
        assert result['exit_code'] == 0 and result['error'] is None
        assert result['terminal_job_accounting'] and not result['cleanup_errors']

    run('phase-aware-controls.py', ['commission', '--out', out / 'commission'], 'commission', 120)
    assert read(out / 'commission/result.json')['passed']
    run('phase-aware-controls.py', ['generate', '--out', out / 'data'], 'generation', 120)
    assert read(out / 'data/result.json')['passed'], 'independent dense optical adequacy refused'
    data_bindings = [c.ref(p) for p in sorted((out / 'data').rglob('*')) if p.is_file()]
    assert data_bindings
    c.save(out / 'data-bindings.json', data_bindings)
    fits = out / 'fits'

    def fit(case, geometry):
        run('phase-aware.py', ['--data', out / 'data', '--case', case, '--geometry', geometry,
            '--out', fits / case / geometry], case + '-' + geometry, 600)

    def score(case):
        run('phase-aware-controls.py', ['score', '--data', out / 'data', '--fits', fits,
            '--case', case, '--out', out / (case + '-scored')], case + '-scoring', 60)
        return read(out / (case + '-scored') / 'result.json')

    for geometry in ('identity', 'phase'):
        fit('flat', geometry)
    flat = score('flat')
    proceed = flat['continue_layered']
    assert isinstance(proceed, bool)
    if proceed:
        for geometry in ('identity', 'phase', 'wrong'):
            fit('layered', geometry)
        score('layered')
    unchanged()
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        generated_data_unchanged=True, layered_executed=proceed,
        stop_reason=None if proceed else 'fixed flat-quality gate refused the phase-aware candidate',
        flat_score=c.ref(out / 'flat-scored/result.json'),
        layered_score=c.ref(out / 'layered-scored/result.json') if proceed else None,
        scope='Supplied-phase/optics generated reconstruction; no photographic or default admission'))
    print(json.dumps(dict(completed=True, layered_executed=proceed,
                          flat_score=c.ref(out / 'flat-scored/result.json'))), flush=True)


if __name__ == '__main__':
    main()
