"""Root-owned bounded build and generated test; no photographic replay route."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('raw_affinity_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'controls'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    out.mkdir()
    if args.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        previous = json.loads((ROOT / 'experiments/through-focus-events/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in previous}
        paths.update(p for p in HERE.iterdir() if p.suffix in ('.rs', '.py', '.md'))
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
    fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
                  STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
                  STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
                  STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
                  STREHL_RAW_AFFINITY_SUPPORT_OUT=str(out / 'output'))
    operator = out / 'operator'
    operator.mkdir()
    prefix = 'merge_cmd::raw_affinity_support::independent_controls::'
    c.job([str(exe), prefix + 'independent_raw_affinity_operator_controls',
           '--exact', '--nocapture', '--test-threads=1'], fields, operator, wall=60)
    operator_log = (operator / 'process.log').read_text()
    assert 'test result: ok. 1 passed;' in operator_log and 'RAW_AFFINITY_OPERATOR' in operator_log
    command = [str(exe), prefix + 'independent_raw_affinity_actual_truth_screen',
               '--exact', '--nocapture', '--test-threads=1']
    c.job(command, fields, out, wall=180)
    log = (out / 'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert 'RAW_AFFINITY_SCREEN' in log
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    screen = out / 'output/screen.json'
    decision = json.loads(screen.read_text())
    assert decision['status'] == 'SCREEN_COMPLETE' and len(decision['cases']) == 13
    c.save(out / 'completion.json', dict(instrument_completed=True, sources_unchanged=True,
        executable=c.ref(exe), process=c.ref(out / 'process.json'), screen=c.ref(screen),
        photographic_replay_admitted=decision['photographic_replay_admitted'],
        scope='Generated screen only; read independent quality decision separately.'))


if __name__ == '__main__':
    main()
