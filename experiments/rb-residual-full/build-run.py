"""Root fresh build and independent full-scope mechanical controls."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rb_full_build_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'controls'])
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--test', default='merge_cmd::rb_residual_full::independent_controls::')
    args = parser.parse_args()
    build = args.build.resolve()
    assert build.is_relative_to(HERE)
    if args.phase == 'build':
        assert not build.exists()
        build.mkdir()
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        old = json.loads((ROOT / 'experiments/rb-residual-guard/build-1/sources.json').read_text())
        paths = {Path(row['path']) for row in old}
        paths.update(p for p in HERE.iterdir() if p.suffix in ('.rs', '.py', '.md'))
        paths.add(ROOT / 'experiments/rb-residual-guard/controls-1/output/screen.json')
        paths.add(ROOT / 'experiments/rb-residual-guard/results-review.md')
        sources = [c.ref(p) for p in sorted(paths)]
        c.save(build / 'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
            '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs', '2', '--target-dir', str(ROOT / 'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        c.job(command, {'RAYON_NUM_THREADS':'8', 'CARGO_INCREMENTAL':'0'}, build, wall=600)
        log = (build / 'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        exes = []
        for line in log.splitlines():
            try: row = json.loads(line)
            except ValueError: continue
            if (row.get('reason') == 'compiler-artifact' and row.get('executable')
                and row.get('target', {}).get('name') == 'strehl' and row['profile']['test']):
                exes.append(row['executable'])
        assert len(exes) == 1
        exe = build / 'cli-tests.exe'
        shutil.copyfile(exes[0], exe)
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        c.save(build / 'executable.json', c.ref(exe))
        return
    sources = json.loads((build / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
    out = build / 'mechanical-1'
    out.mkdir()
    command = [str(exe), args.test, '--nocapture', '--test-threads=1']
    c.job(command, {'RAYON_NUM_THREADS':'8', 'STREHL_RB_RESIDUAL_GUARD_OUT':str(out / 'output')}, out, wall=120)
    log = (out / 'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    c.save(out / 'completion.json', dict(passed=True, executable=c.ref(exe),
        sources_unchanged=True, process=c.ref(out / 'process.json'), log=c.ref(out / 'process.log')))

if __name__ == '__main__': main()
