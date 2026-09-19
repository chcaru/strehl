"""Bounded build and frozen one-level identity complex-wavelet screen."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('complex_wavelet_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['build', 'controls'])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--build', type=Path)
    a = p.parse_args()
    out = a.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir()
    if a.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        (ROOT / 'crates/strehl-core/src/pyramid.rs').touch()
        paths = set(c.source_paths())
        for directory in [HERE, ROOT / 'experiments/phase-packed-rgb', ROOT / 'experiments/fine-support-guidance', ROOT / 'experiments/green-match-rgb']:
            paths.update(directory.glob('*.rs'))
        paths.update([Path(__file__), HERE / 'independent-plan.md', HERE / 'charter.md',
            ROOT / 'crates/strehl-core/src/pyramid.rs', ROOT / 'crates/strehl-core/src/boxfilter.rs',
            ROOT / 'experiments/native-correction-variance/core-bridge.rs',
            ROOT / 'crates/strehl-cli/Cargo.toml', ROOT / 'crates/strehl-core/Cargo.toml'])
        paths.update(HERE.glob('*.md'))
        paths.update(HERE.glob('*.txt'))
        sources = [c.ref(f.resolve()) for f in sorted(paths)]
        c.save(out / 'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
            '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs', '2', '--target-dir', str(ROOT / 'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        c.job(command, {'RAYON_NUM_THREADS': '8', 'CARGO_INCREMENTAL': '0'}, out)
        log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
        executables = []
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'strehl' and row['profile']['test']:
                executables.append(row['executable'])
        assert len(executables) == 1
        exe = out / 'cli-tests.exe'
        shutil.copyfile(executables[0], exe)
        assert all(c.ref(Path(r['path'])) == r for r in sources)
        c.save(out / 'executable.json', c.ref(exe))
        return
    assert a.build is not None
    build = a.build.resolve()
    sources = json.loads((build / 'sources.json').read_text())
    assert all(c.ref(Path(r['path'])) == r for r in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
    fields = dict(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='off', STREHL_GPU_GATHER_LOG='off',
        STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off', STREHL_COMPLEX_WAVELET_OUT=str(out / 'output'))
    command = [str(exe), 'merge_cmd::complex_wavelet_merge::independent_controls::', '--nocapture', '--test-threads=1']
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), runner=c.ref(Path(__file__))))
    c.job(command, fields, out, wall=180)
    log = (out / 'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert all(c.ref(Path(r['path'])) == r for r in sources)
    screen = out / 'output/screen.json'
    result = json.loads(screen.read_text())
    c.save(out / 'completion.json', dict(screen=c.ref(screen), sources_unchanged=True,
        structural_controls_passed=True, generated_result=result))


if __name__ == '__main__':
    main()
