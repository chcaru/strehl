"""Bounded shared-source-field build, independent screen and complete RAW pair."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('shared_field_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'controls', 'full'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--screen', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir()
    if args.phase == 'build':
        for path in ['crates/strehl-cli/src/merge_cmd.rs', 'crates/strehl-core/src/pyramid.rs']:
            (ROOT / path).touch()
        paths = set(c.source_paths())
        for name in ['shared-source-field', 'donor-consistency', 'boundary-cfa-wavelet',
                     'complex-wavelet-merge', 'all-cfa-wavelet', 'complete-cfa-wavelet',
                     'phase-packed-rgb', 'fine-support-guidance', 'green-match-rgb']:
            paths.update((ROOT / 'experiments' / name).glob('*.rs'))
        paths.update(HERE.glob('*.md'))
        paths.update(HERE.glob('*.py'))
        paths.update(ROOT / name for name in ['crates/strehl-core/src/pyramid.rs',
            'crates/strehl-core/src/boxfilter.rs', 'experiments/native-correction-variance/core-bridge.rs',
            'crates/strehl-cli/src/merge_cmd/gatefloor.rs', 'crates/strehl-cli/Cargo.toml',
            'crates/strehl-core/Cargo.toml'])
        sources = [c.ref(path.resolve()) for path in sorted(paths)]
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
    fields = dict(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_SHARED_SOURCE_FIELD_OUT=str(out / 'output'))
    command = [str(exe), 'merge_cmd::shared_source_field::independent_controls::',
        '--nocapture', '--test-threads=1']
    inputs = []
    if args.phase == 'full':
        assert args.screen is not None
        sd = args.screen.resolve()
        screen = sd / 'output/screen.json'
        assert json.loads(screen.read_text())['photographic_replay_admitted'] is True
        sb = json.loads((sd / 'bindings.json').read_text())
        assert sb['sources'] == sources and sb['executable'] == c.ref(exe)
        c.save(out / 'screen-binding.json', c.ref(screen))
        inputs = json.loads((ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/invocation.json').read_text())['inputs']
        assert len(inputs) == 70
        warp = ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
        warp_ref = c.ref(warp)
        assert warp_ref['sha256'] == '84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f'
        config = dict(schema=1, source_dir=str(Path(inputs[0]['path']).parent), warp_map=str(warp),
            warp_map_sha256=warp_ref['sha256'], out_dir=str(out / 'output'),
            expected_crop=[28, 19, 3460, 2306], max_extra_inset_quads=0,
            expected_xyz_to_cam=[[.7460, -.2365, -.0588], [-.5687, 1.3442, .2474], [-.0624, .1156, .6584]],
            tone=[.090420, .914606, .55])
        c.save(out / 'config.json', config)
        c.save(out / 'inputs.json', dict(inputs=inputs, map=warp_ref))
        fields.update(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_WARPMAP=str(warp),
            STREHL_SHARED_SOURCE_FIELD_FULL_CONFIG=str(out / 'config.json'))
        command = [str(exe), 'merge_cmd::shared_source_field::full_stack::vitamin_c_complete_pair',
            '--exact', '--ignored', '--nocapture', '--test-threads=1']
    def check_inputs():
        for row in inputs:
            st = Path(row['path']).stat()
            assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    check_inputs()
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), runner=c.ref(Path(__file__))))
    c.job(command, fields, out, wall=600 if args.phase == 'full' else 180)
    log = (out / 'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    check_inputs()
    if args.phase == 'controls':
        screen = out / 'output/screen.json'
        result = json.loads(screen.read_text())
        c.save(out / 'completion.json', dict(screen=c.ref(screen), sources_unchanged=True,
            photographic_replay_admitted=result['photographic_replay_admitted']))
        return
    import numpy as np
    import tifffile
    reference = ROOT / 'experiments/phase-packed-rgb/full-1/output/baseline.tiff'
    assert c.ref(reference)['sha256'] == 'c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21'
    baseline = out / 'output/baseline.tiff'
    candidate = out / 'output/candidate.tiff'
    assert np.array_equal(tifffile.imread(baseline), tifffile.imread(reference))
    assert c.ref(warp) == warp_ref
    for path in [baseline, candidate]:
        with tifffile.TiffFile(path) as tif:
            assert tif.pages[0].shape == (4612, 6920, 3) and tif.pages[0].dtype == np.uint16
    c.save(out / 'completion.json', dict(baseline=c.ref(baseline), candidate=c.ref(candidate),
        receipt=c.ref(out / 'output/receipt.json'), shape=[4612, 6920, 3],
        original_metadata_unchanged=True, map_unchanged=True, baseline_pixels_identical=True,
        reference=c.ref(reference), sources_unchanged=True, photographic_promotion=False,
        scope='Complete held RAW pair for independent photographic review; no default promotion.'))


if __name__ == '__main__':
    main()
