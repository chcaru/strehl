"""Root-owned bounded build and four independent generated-consumer tests."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('vst_job', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
TESTS = ('independent_transform_controls', 'independent_paired_floor_controls',
         'independent_metric_controls', 'independent_quality_screen')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'controls'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    if args.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        prior = json.loads((ROOT / 'experiments/core-lineage/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in prior}
        paths = {p for p in paths if p.suffix in ('.rs', '.toml', '.lock')}
        paths.update(HERE.glob('*.rs'))
        paths.update(HERE.glob('*.md'))
        paths.update((ROOT / 'experiments/rb-own-guide').glob('*.rs'))
        paths.add(Path(__file__))
        sources = [c.ref(p) for p in sorted(paths)]
        c.save(out / 'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
            '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs', '2', '--target-dir', str(ROOT / 'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        c.job(command, {'RAYON_NUM_THREADS': '8', 'CARGO_INCREMENTAL': '0'}, out, wall=600)
        log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        executables = []
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if (row.get('reason') == 'compiler-artifact' and row.get('executable')
                    and row.get('target', {}).get('name') == 'strehl' and row['profile']['test']):
                executables.append(row['executable'])
        assert len(executables) == 1
        exe = out / 'cli-tests.exe'
        shutil.copyfile(executables[0], exe)
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        c.save(out / 'executable.json', c.ref(exe))
        return
    assert args.build is not None
    build = args.build.resolve()
    sources = json.loads((build / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), runner=c.ref(Path(__file__))))
    fields = dict(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_VARIANCE_STABILIZED_GUIDE_OUT=str(out / 'output'))
    api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    for test in TESTS:
        test_out = out / test.replace('_', '-')
        test_out.mkdir()
        command = [str(exe), 'merge_cmd::variance_stabilized_guide::independent_controls::' + test,
                   '--exact', '--nocapture', '--test-threads=1']
        env, removed = c.b.clean_environment(fields.items())
        c.save(test_out / 'invocation.json', dict(command=command, environment=fields, removed_environment=removed))
        process = c.b.run(command, env, ROOT, test_out / 'process.log', api=api,
            wall_seconds=180, cpu_seconds=300, log_bytes=8 << 20, committed_bytes=2 << 30)
        c.save(test_out / 'process.json', process)
        print(json.dumps(dict(test=test, **{k: process[k] for k in ('exit_code', 'error', 'wall_seconds')})), flush=True)
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        assert process['exit_code'] == 0 and process['error'] is None
        assert process['terminal_job_accounting'] and not process['cleanup_errors']
        assert 'test result: ok. 1 passed;' in (test_out / 'process.log').read_text()
    screen = out / 'output/screen.json'
    result = json.loads(screen.read_text())
    assert result['status'] == 'SCREEN_COMPLETE'
    c.save(out / 'completion.json', dict(screen=c.ref(screen), sources_unchanged=True,
        candidate_nominated=result['candidate_nominated'],
        photographic_replay_admitted=result['photographic_replay_admitted'],
        scope='Generated actual-consumer screen only; no photograph or SOTA claim.'))


if __name__ == '__main__':
    main()
