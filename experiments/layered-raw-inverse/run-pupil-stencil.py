"""Root-owned bounded joint-pupil kernel and quadrature commissioning."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'pupil_stencil_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    frozen = json.loads((HERE / 'free-visibility-1/sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in frozen)
    paths = {Path(row['path']) for row in frozen}
    paths.update(HERE / name for name in (
        'pupil-stencil.py', 'pupil-stencil-plan.md', 'pupil-stencil-design.md',
        'pupil-kernel-feasibility.md', 'pupil-stencil-controls.py',
        'pupil-stencil-independent-plan.md', 'independent-pupil-stencil-review.md',
        'run-pupil-stencil.py'))
    torch_lib = Path(sys.executable).parent / 'Lib/site-packages/torch/lib'
    paths.update(torch_lib / name for name in (
        'nvrtc64_120_0.dll', 'nvrtc-builtins64_128.dll', 'cudart64_12.dll'))
    paths.add(Path('C:/Windows/System32/nvcuda.dll'))
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in sorted(paths)]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    process = out / 'control-process'
    process.mkdir()
    fields = {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
              'PYTHONDONTWRITEBYTECODE': '1', 'CUDA_CACHE_DISABLE': '1'}
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
               str(HERE / 'pupil-stencil-controls.py'), '--out', str(out / 'output')]
    env, removed = c.b.clean_environment(fields.items())
    c.save(process / 'invocation.json', dict(command=command, environment=fields,
        removed_environment=removed, runner=c.ref(Path(__file__))))
    api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, process / 'process.log', api=api,
        wall_seconds=240, cpu_seconds=3600, log_bytes=16 << 20, committed_bytes=8 << 30)
    c.save(process / 'process.json', result)
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        independent_result=c.ref(out / 'output/result.json'),
        scope='Fixed-pupil forward/adjoint and numerical quadrature; no fit, quality or photographic admission'))
    print(json.dumps({'completed': True, 'wall_seconds': result['wall_seconds'],
        'result': c.ref(out / 'output/result.json')}), flush=True)


if __name__ == '__main__':
    main()
