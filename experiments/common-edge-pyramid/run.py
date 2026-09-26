"""Two bounded native jobs; reuse the existing process owner and build recipe."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('common_edge_jobs', ROOT / 'experiments/cross-scale-band-guide/run.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
c = previous.c


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'controls'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    if args.phase == 'build':
        out.mkdir()
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        old_sources = read(ROOT / 'experiments/cross-scale-band-guide/build-4/sources.json')
        paths = {Path(row['path']) for row in old_sources}
        paths.update(HERE.glob('*.rs'))
        sources = [c.ref(path) for path in sorted(paths)]
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
    sources = read(build / 'sources.json')
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == read(build / 'executable.json')
    paths = [Path(__file__), HERE / 'plan.md', HERE / 'independent-plan.md',
        ROOT / 'experiments/cross-scale-band-guide/run.py',
        ROOT / 'experiments/learned-band-guide/run.py',
        ROOT / 'experiments/full-context-placement/run.py',
        ROOT / 'experiments/m193c-output-grid/bounded-process.py',
        ROOT / 'experiments/m12-scorecard/m12-harness.py']
    inputs = [c.ref(path) for path in paths]
    out.mkdir()
    (out / 'output').mkdir()
    c.save(out / 'bindings.json', dict(sources=sources, inputs=inputs, executable=c.ref(exe)))
    env = dict(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_CA_BEFORE_MHC='off', STREHL_COMMON_EDGE_PYRAMID_OUT=str(out / 'output'))
    command = [str(exe), 'merge_cmd::common_edge_pyramid::independent_controls::',
        '--ignored', '--nocapture', '--test-threads=1']
    previous.old.run_job(command, env, out, 300, 1800, 8 << 30)
    assert 'test result: ok. 2 passed;' in (out / 'process.log').read_text()
    assert all(c.ref(Path(row['path'])) == row for row in sources + inputs)
    assert (out / 'output/screen.json').is_file() and (out / 'output/operator.json').is_file()
    c.save(out / 'completion.json', dict(process_completed=True, sources_unchanged=True,
        inputs_unchanged=True, photographic_admission=False,
        scope='Fixed generated native screen and independent operator controls. Read the scientific decisions separately.'))


if __name__ == '__main__':
    main()
