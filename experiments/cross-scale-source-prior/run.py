"""Root-executed bounded build and generated screen; no RAW/full-render route."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cross_scale_bounds', ROOT/'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
FILTER = 'merge_cmd::cross_scale_source_prior::independent_controls::'
FEATURES = 'native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def bindings():
    paths = set(c.source_paths())
    for folder in (ROOT/'crates', ROOT/'experiments/native-gpu-gather/src'):
        paths.update(p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.rs', '.wgsl', '.toml'))
    # Current out-of-tree include surfaces; never scan retained image/output trees.
    for suffix in ('*.rs', '*.wgsl'):
        paths.update((ROOT/'experiments').glob('*/'+suffix))
    for folder in (HERE, ROOT/'experiments/native-sensor-transfer/source'):
        paths.update(p for p in folder.iterdir() if p.is_file() and p.suffix in ('.rs', '.wgsl', '.py', '.md'))
    paths.update(ROOT/p for p in ('Cargo.toml', 'Cargo.lock',
        'experiments/native-gpu-gather/Cargo.toml', 'experiments/phase-packed-chip/run.py',
        'experiments/full-context-placement/run.py', 'experiments/m193c-output-grid/bounded-process.py',
        'experiments/m12-scorecard/m12-harness.py'))
    required = ('implementation.rs', 'core-bridge.rs', 'design.md', 'independent-controls.rs', 'independent-plan.md', 'run.py')
    assert all((HERE/name).is_file() for name in required), 'authors must freeze all source/control files before build'
    paths.update(HERE/name for name in required)
    return [c.ref(p.resolve()) for p in sorted(paths)]


def unchanged(sources):
    assert all(c.ref(Path(row['path'])) == row for row in sources), 'bound source changed'


def job(command, fields, out, *, wall, cpu, gib):
    env, removed = c.b.clean_environment(fields.items())
    c.save(out/'invocation.json', dict(command=command, environment=fields,
        removed_environment=removed, runner=c.ref(Path(__file__))))
    api = c.b.load_job_api(c.b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out/'process.log', api=api,
        wall_seconds=wall, cpu_seconds=cpu, committed_bytes=gib << 30, log_bytes=16 << 20)
    c.save(out/'process.json', result)
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build', 'controls'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE
    out.mkdir(exist_ok=False)
    if args.phase == 'build':
        # Both tiny include owners changed: require fresh CLI and core compilation.
        (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
        (ROOT/'crates/strehl-core/src/pyramid.rs').touch()
        sources = bindings()
        c.save(out/'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--test', 'byte-freeze',
            '--no-run', '--release', '--features', FEATURES, '--jobs', '2',
            '--target-dir', str(ROOT/'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        job(command, dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out, wall=600, cpu=1800, gib=16)
        log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
        artifacts = {}
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'strehl':
                key = 'cli-tests' if row['profile']['test'] else 'strehl'
                assert key not in artifacts
                destination = out/(key+'.exe')
                shutil.copyfile(row['executable'], destination)
                artifacts[key] = c.ref(destination)
        assert set(artifacts) == {'cli-tests', 'strehl'}
        unchanged(sources)
        c.save(out/'executables.json', artifacts)
        return
    assert args.build is not None
    build = args.build.resolve()
    sources = read(build/'sources.json')
    unchanged(sources)
    assert {str((HERE/name).resolve()) for name in ('run.py', 'implementation.rs', 'core-bridge.rs',
        'design.md', 'independent-controls.rs', 'independent-plan.md')} <= {r['path'] for r in sources}
    exe = (build/'cli-tests.exe').resolve()
    assert c.ref(exe) == read(build/'executables.json')['cli-tests']
    c.save(out/'bindings.json', dict(sources=sources, executable=c.ref(exe), build_receipt=c.ref(build/'executables.json')))
    fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_SCHEDULE='device',
        STREHL_GPU_GATHER_LOG='on', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_CA_BEFORE_MHC='off', STREHL_CROSS_SCALE_SOURCE_PRIOR_OUT=str(out/'output'))
    job([str(exe), FILTER, '--nocapture', '--test-threads=1'], fields, out, wall=180, cpu=900, gib=4)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    # Independent author contract: operator test plus twelve-case actual truth screen.
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['2']
    assert 'CROSS_SCALE_SOURCE_PRIOR' in log
    screen_path = out/'output/screen.json'
    screen = read(screen_path)
    assert screen['status'] == 'SCREEN_COMPLETE'
    assert isinstance(screen['cases'], list) and len(screen['cases']) == 12
    assert type(screen['photographic_replay_admitted']) is bool
    unchanged(sources)
    assert c.ref(exe) == read(build/'executables.json')['cli-tests']
    c.save(out/'completion.json', dict(instrument_completed=True, controls_executed=2,
        sources_unchanged=True, executable=c.ref(exe), process=c.ref(out/'process.json'),
        screen=c.ref(screen_path), photographic_replay_admitted=screen['photographic_replay_admitted'],
        full_render_available=False, scope='Generated controls only. Successful test execution is not quality admission.'))


if __name__ == '__main__':
    main()
