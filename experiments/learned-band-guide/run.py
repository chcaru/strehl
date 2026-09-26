"""Root-owned bounded orchestration; experiment sources own the scientific tests."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('learned_guide_jobs', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def run_job(command, fields, out, wall, cpu, memory):
    env, removed = c.b.clean_environment(fields.items())
    c.save(out / 'invocation.json', dict(command=command, environment=fields, removed_environment=removed))
    api = c.b.load_job_api(c.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out / 'process.log', api=api,
        wall_seconds=wall, cpu_seconds=cpu, log_bytes=16 << 20, committed_bytes=memory)
    c.save(out / 'process.json', result)
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'native', 'commission', 'train', 'infer'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--test')
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--commission', type=Path)
    parser.add_argument('--weights', type=Path)
    parser.add_argument('--inference', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    if args.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        prior = json.loads((ROOT / 'experiments/variance-stabilized-guide/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in prior if Path(row['path']).suffix in ('.rs', '.toml', '.lock')}
        paths.update(p for p in HERE.iterdir() if p.suffix in ('.rs', '.md', '.py'))
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
    inputs = [c.ref(path.resolve()) for path in (args.dataset, args.weights)
              if path is not None and path.is_file()]
    if args.phase == 'train':
        assert args.dataset is not None
        preflight = args.dataset.resolve().parent / 'pretraining.json'
        pre = json.loads(preflight.read_text())
        flags = ('truth_pass', 'headroom_live', 'protected_witnesses_live', 'destroyers_rejected')
        assert pre['status'] == 'PRETRAINING_COMPLETE'
        assert all(pre[key] is True for key in flags) and pre['pretraining_qualified'] is True
        inputs.append(c.ref(preflight))
    c.save(out / 'bindings.json', dict(sources=sources, runner=c.ref(Path(__file__))))
    c.save(out / 'inputs.json', inputs)
    if args.phase == 'native':
        assert args.test in ('independent_arithmetic_controls', 'export_dataset', 'replay_dataset')
        exe = build / 'cli-tests.exe'
        assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
        config = dict(out=str(out / 'output'))
        for key in ('dataset', 'weights', 'inference'):
            path = getattr(args, key)
            if path is not None:
                config[key] = str(path.resolve())
        c.save(out / 'config.json', config)
        fields = dict(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_ALIGN='1',
            STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
            STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
            STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
            STREHL_LEARNED_BAND_GUIDE_CONFIG=str(out / 'config.json'))
        command = [str(exe), 'merge_cmd::learned_band_guide::independent_controls::' + args.test,
                   '--exact', '--nocapture', '--test-threads=1']
        run_job(command, fields, out, 300, 900, 4 << 30)
        assert 'test result: ok. 1 passed;' in (out / 'process.log').read_text()
    else:
        assert args.dataset is not None
        command = [sys.executable, '-I', '-B', '-X', 'faulthandler', str(HERE / 'train.py'),
                   args.phase, '--dataset', str(args.dataset.resolve()), '--out', str(out / 'output')]
        if args.phase == 'train':
            assert args.commission is not None
            command += ['--commission', str(args.commission.resolve())]
        if args.phase == 'infer':
            assert args.weights is not None
            command += ['--weights', str(args.weights.resolve())]
        fields = dict(CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='137', CUBLAS_WORKSPACE_CONFIG=':4096:8')
        run_job(command, fields, out, 360 if args.phase == 'train' else 180, 1800, 8 << 30)
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    assert all(c.ref(Path(row['path'])) == row for row in inputs)
    c.save(out / 'completion.json', dict(process_completed=True, sources_unchanged=True,
        scope='Execution receipt only; independent scientific admission is separate.'))


if __name__ == '__main__':
    main()
