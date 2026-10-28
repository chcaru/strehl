"""Root-owned bounded build, original-CFA observation and native graph jobs."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
CAMPAIGN = ROOT / 'outputs/raw-quality-2026-10-27'
HELPERS = AREA.parents[1] / 'insect-placement-observer/run.py'
spec = importlib.util.spec_from_file_location('insect_phase_full_root_helpers', HELPERS)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)
ORDER = ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/input-order.json'
MAP = ROOT / 'outputs/raw-quality-2026-10-26/weevil-107-baseline/alignment.txt'
OBSERVER = CAMPAIGN / 'insect-placement-observe-1/output/pairs.jsonl'
FEATURES = 'native-direct-planes,native-correction-variance,native-gpu-gather'
GRAPH = 'align_cmd::insect_blur_phase_graph::'


def folder(stage, iteration):
    return CAMPAIGN / f'insect-blur-phase-{stage}-{iteration}'


def rust_bindings():
    # Explicit filesystem inventory avoids relying on the shared worktree's
    # external Git metadata. Include path-linked experiment sources as well.
    paths = {ROOT / 'Cargo.toml', ROOT / 'Cargo.lock'}
    for directory in ('crates', 'experiments'):
        paths.update((ROOT / directory).rglob('*.rs'))
        paths.update((ROOT / directory).rglob('Cargo.toml'))
    return [h.ref(path) for path in sorted(paths) if path.is_file()]


def standard_environment():
    fields = dict(OMP_NUM_THREADS='4', MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                  CUBLAS_WORKSPACE_CONFIG=':4096:8', RAYON_NUM_THREADS='4',
                  STREHL_TEST_TMP=str(CAMPAIGN / 'test-tmp'))
    env, removed = h.b.clean_environment(fields.items())
    return fields, env, removed


def bind_local(out, paths):
    rows = [h.ref(path) for path in paths]
    h.save(out / 'source-bindings.json', rows)
    for path in paths:
        if path.parent == AREA or path.parent == AREA.parent:
            name = path.parent.name + '-' + path.stem + '-executed' + path.suffix
            (out / name).write_bytes(path.read_bytes())
    return rows


def finish(out, receipt, bindings):
    h.check_refs(bindings)
    assert receipt['complete'] is True
    assert receipt['quality_claim'] is False and receipt['photographic_admission'] is False
    outputs = [h.ref(p) for p in sorted((out / 'output').rglob('*')) if p.is_file()]
    h.save(out / 'completion.json', dict(reports=outputs, source_bindings_unchanged=True,
           photographic_improvement_claimed=False, status=receipt['status']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('build', 'graph-controls', 'graph-replay', 'cost', 'actual', 'graph-candidate'))
    parser.add_argument('--iteration', type=int, default=1)
    parser.add_argument('--build-iteration', type=int, default=1)
    parser.add_argument('--actual-iteration', type=int, default=1)
    args = parser.parse_args()
    assert min(args.iteration, args.build_iteration, args.actual_iteration) > 0
    out = folder(args.stage, args.iteration)
    out.mkdir(parents=True, exist_ok=False)
    fields, env, removed = standard_environment()
    helpers = [Path(__file__), HELPERS, h.PRIOR, h.prior.HELPER, h.b.HARNESS]
    if args.stage == 'build':
        bindings = rust_bindings()
        h.save(out / 'rust-sources.json', bindings)
        for name in ('graph.rs', 'render.rs'):
            (out / (Path(name).stem + '-executed.rs')).write_bytes((AREA / name).read_bytes())
        command = ['cargo', 'test', '--locked', '--offline', '--release', '-p', 'strehl-cli',
                   '--lib', '--no-run', '--features', FEATURES, '--jobs', '4',
                   '--message-format=json-render-diagnostics']
        env.update(CARGO_INCREMENTAL='0', CARGO_BUILD_JOBS='4')
        bounds = dict(wall_seconds=900, cpu_seconds=3600, committed_bytes=24 << 30, log_bytes=64 << 20)
        h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
               build_environment={'CARGO_INCREMENTAL':'0','CARGO_BUILD_JOBS':'4'}, removed_environment=removed,
               runner=h.ref(__file__), sources=len(bindings), scope='Fresh affected CLI test build; no numerical experiment.'))
        h.observed_run(command, env, out, bounds)
        log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
        rows = []
        for line in log.splitlines():
            try:
                value = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict):
                rows.append(value)
        assert 'Compiling strehl-cli' in log, 'fresh affected compilation required'
        assert any(r.get('reason') == 'build-finished' and r.get('success') for r in rows)
        paths = {r['executable'] for r in rows if r.get('reason') == 'compiler-artifact'
                 and r.get('executable') and r.get('target', {}).get('name') == 'strehl_cli'
                 and r.get('profile', {}).get('test')}
        assert len(paths) == 1
        exe = out / 'strehl-cli-tests.exe'
        shutil.copyfile(next(iter(paths)), exe)
        h.check_refs(bindings)
        h.save(out / 'executable.json', h.ref(exe))
        return
    if args.stage in ('cost', 'actual'):
        paths = helpers + [AREA / 'actual.py', AREA / 'actual-reader-notes.md', AREA / 'brief.md',
                            AREA.parent / 'phase.py', AREA.parent / 'implementation-notes.md']
        bindings = bind_local(out, paths)
        mode = 'cost' if args.stage == 'cost' else 'full'
        command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'actual.py'),
                   '--mode', mode, '--out', str(out / 'output')]
        bounds = dict(wall_seconds=300 if mode == 'cost' else 1500,
                      cpu_seconds=1200 if mode == 'cost' else 6000,
                      committed_bytes=(12 if mode == 'cost' else 16) << 30, log_bytes=32 << 20)
        h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
               removed_environment=removed, python=h.ref(sys.executable), workers=4, cuda_budget_bytes=6 << 30,
               concurrent_work='No other root-scheduled GPU or numerical job.',
               scope='Fixed original-CFA phase correspondences; physical placement and image quality unverified.'))
        h.observed_run(command, env, out, bounds)
        receipt = json.loads((out / 'output/receipt.json').read_text(encoding='utf-8'))
        assert receipt['status'] == 'COMPLETE_INSECT_BLUR_PHASE_ACTUAL'
        assert receipt['mode'] == mode
        assert receipt['pair_count'] == (6 if mode == 'cost' else 2340)
        assert receipt['tile_count'] == receipt['pair_count'] * 96
        assert receipt['retained_input_bytes_and_metadata_unchanged'] is True
        finish(out, receipt, bindings)
        return
    build = folder('build', args.build_iteration)
    executable = json.loads((build / 'executable.json').read_text(encoding='utf-8'))
    h.check_refs([executable])
    build_sources = json.loads((build / 'rust-sources.json').read_text(encoding='utf-8'))
    h.check_refs(build_sources)
    bindings = bind_local(out, helpers + [AREA / 'graph.rs', AREA / 'brief.md'])
    if args.stage == 'graph-controls':
        command = [executable['path'], GRAPH + 'graph_input_and_centroid_controls', '--exact', '--nocapture']
        bounds = dict(wall_seconds=120, cpu_seconds=480, committed_bytes=4 << 30, log_bytes=16 << 20)
        h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
               removed_environment=removed, executable=executable, build=build_sources))
        h.observed_run(command, env, out, bounds)
        assert '1 passed; 0 failed' in (out / 'process.log').read_text(encoding='utf-8')
        h.check_refs(bindings + [executable])
        h.save(out / 'completion.json', dict(test_passed=True, photographic_improvement_claimed=False))
        return
    observations = OBSERVER
    mode = 'replay'
    if args.stage == 'graph-candidate':
        actual = folder('actual', args.actual_iteration)
        completion = json.loads((actual / 'completion.json').read_text(encoding='utf-8'))
        h.check_refs(completion['reports'])
        receipt = json.loads((actual / 'output/receipt.json').read_text(encoding='utf-8'))
        assert receipt['complete'] and receipt['pair_count'] == 2340 and receipt['mode'] == 'full'
        observations = actual / 'output/observations.jsonl'
        mode = 'candidate'
    config = dict(schema=1, mode=mode, out_dir=str(out / 'output'),
                  expected_test_executable_sha256=executable['sha256'],
                  observations=h.ref(observations), observer=h.ref(OBSERVER),
                  held_map=h.ref(MAP), input_order=h.ref(ORDER))
    h.save(out / 'config.json', config)
    fields['STREHL_INSECT_BLUR_PHASE_GRAPH_CONFIG'] = str(out / 'config.json')
    fields['STREHL_WARPMAP'] = str(out / 'output/isolated-unused-sidecar.txt')
    env.update(fields)
    command = [executable['path'], GRAPH + 'fit_and_solve_weevil_phase_maps', '--ignored', '--exact', '--nocapture']
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=8 << 30, log_bytes=32 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
           removed_environment=removed, executable=executable, config=h.ref(out / 'config.json')))
    h.observed_run(command, env, out, bounds)
    receipt = json.loads((out / 'output/receipt.json').read_text(encoding='utf-8'))
    assert receipt['status'] == 'COMPLETE_INSECT_PHASE_GRAPH' and receipt['mode'] == mode
    assert receipt['pair_count'] == 2340 and receipt['inputs_unchanged']
    finish(out, receipt, bindings + [executable])


if __name__ == '__main__':
    main()
