"""Build, literal controls and complete externally-labelled donor counterfactual."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('donor_full_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['build', 'controls', 'full'])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--build', type=Path)
    p.add_argument('--screen', type=Path)
    p.add_argument('--observe', action='store_true', help='Record unchanged actual coefficient contributions')
    a = p.parse_args()
    assert not a.observe or a.phase == 'full'
    out = a.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir()
    if a.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        (ROOT / 'crates/strehl-core/src/pyramid.rs').touch()
        paths = set(c.source_paths())
        for directory in [HERE, ROOT / 'experiments/phase-packed-rgb', ROOT / 'experiments/fine-support-guidance', ROOT / 'experiments/green-match-rgb', ROOT / 'experiments/complex-wavelet-merge', ROOT / 'experiments/all-cfa-wavelet', ROOT / 'experiments/complete-cfa-wavelet']:
            paths.update(directory.glob('*.rs'))
        paths.update([Path(__file__), HERE / 'independent-plan.md', HERE / 'charter.md',
            HERE / 'independent-attribution-plan.md',
            ROOT / 'crates/strehl-core/src/pyramid.rs', ROOT / 'crates/strehl-core/src/boxfilter.rs',
            ROOT / 'experiments/native-correction-variance/core-bridge.rs',
            ROOT / 'crates/strehl-cli/Cargo.toml', ROOT / 'crates/strehl-core/Cargo.toml'])
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
        STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off', STREHL_DONOR_CONSISTENCY_OUT=str(out / 'output'))
    command = [str(exe), 'merge_cmd::donor_consistency::independent_controls::', '--nocapture', '--test-threads=1']
    inputs = None
    if a.phase == 'full':
        assert a.screen is not None
        screen_dir = a.screen.resolve()
        screen = screen_dir / 'output/screen.json'
        assert json.loads(screen.read_text())['photographic_replay_admitted']
        sb = json.loads((screen_dir / 'bindings.json').read_text())
        assert sb['sources'] == sources and sb['executable'] == c.ref(exe)
        c.save(out / 'screen-binding.json', c.ref(screen))
        prior = json.loads((ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/invocation.json').read_text())
        inputs = prior['inputs']
        assert len(inputs) == 70
        warp = ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
        warp_ref = c.ref(warp)
        cfg = dict(schema=1, source_dir=str(Path(inputs[0]['path']).parent), warp_map=str(warp),
            warp_map_sha256=warp_ref['sha256'], out_dir=str(out / 'output'),
            expected_crop=[28, 19, 3460, 2306], max_extra_inset_quads=0,
            expected_xyz_to_cam=[[.7460, -.2365, -.0588], [-.5687, 1.3442, .2474], [-.0624, .1156, .6584]],
            tone=[.090420, .914606, .55])
        c.save(out / 'config.json', cfg)
        c.save(out / 'inputs.json', dict(inputs=inputs, map=warp_ref))
        fields.update(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_GPU_GATHER='on',
            STREHL_GPU_SCHEDULE='device', STREHL_WARPMAP=str(warp),
            STREHL_DONOR_CONSISTENCY_FULL_CONFIG=str(out / 'config.json'))
        command = [str(exe), 'merge_cmd::donor_consistency::full_stack::vitamin_c_complete_triplet',
            '--exact', '--ignored', '--nocapture', '--test-threads=1']
        if a.observe:
            fields['STREHL_DONOR_ATTRIBUTION_DIR'] = str(out / 'attribution')
    def check_inputs():
        for r in inputs or []:
            st = Path(r['path']).stat()
            assert (st.st_size, st.st_mtime_ns) == (r['bytes'], r['mtime_ns'])
    check_inputs()
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), runner=c.ref(Path(__file__))))
    c.job(command, fields, out, wall=600 if a.phase == 'full' else 180)
    log = (out / 'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert all(c.ref(Path(r['path'])) == r for r in sources)
    check_inputs()
    if a.phase == 'controls':
        assert 'test result: ok. 3 passed;' in log
        records = {}
        for label in ['DONOR_GEOMETRY', 'DONOR_CONSUMER', 'DONOR_ATTRIBUTION']:
            lines = [line.split(label + ' ', 1)[1] for line in log.splitlines() if label + ' ' in line]
            assert len(lines) == 1, (label, len(lines))
            records[label] = json.loads(lines[0])
        (out / 'output').mkdir()
        screen = out / 'output/screen.json'
        c.save(screen, dict(status='MECHANICAL_CONTROLS_PASSED', records=records,
            photographic_replay_admitted=True,
            scope='Mechanical and immutable attribution controls only; no automatic selector or quality admission'))
        c.save(out / 'completion.json', dict(screen=c.ref(screen), sources_unchanged=True,
            structural_controls_passed=True, photographic_replay_admitted=json.loads(screen.read_text())['photographic_replay_admitted']))
        return
    import numpy as np
    import tifffile
    assert c.ref(warp) == warp_ref
    baseline = out / 'output/baseline.tiff'
    candidate = out / 'output/candidate.tiff'
    expected = 'c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21'
    reference = ROOT / 'experiments/phase-packed-rgb/full-1/output/baseline.tiff'
    assert c.ref(reference)['sha256'] == expected, 'historical baseline binding differs'
    assert np.array_equal(tifffile.imread(baseline), tifffile.imread(reference)), 'actual baseline RGB16 pixels differ'
    late = out / 'output/late.tiff'
    for image in [baseline, candidate, late]:
        with tifffile.TiffFile(image) as tif:
            assert tif.pages[0].shape == (4612, 6920, 3) and tif.pages[0].dtype == np.uint16
    c.save(out / 'completion.json', dict(baseline=c.ref(baseline), candidate=c.ref(candidate), late=c.ref(late),
        shape=[4612, 6920, 3], original_metadata_unchanged=True, map_unchanged=True,
        baseline_pixels_identical=True, baseline_whole_file_identical=c.ref(baseline)['sha256'] == expected,
        reference=c.ref(reference), sources_unchanged=True))
    if a.observe:
        assert (out / 'attribution/receipt.json').is_file()


if __name__ == '__main__':
    main()
