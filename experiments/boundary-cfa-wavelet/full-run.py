"""Separate observational scope; the original generated admission remains false."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('boundary_full_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['controls', 'cost', 'full'])
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--screen', type=Path, required=True)
    parser.add_argument('--mechanical', type=Path)
    parser.add_argument('--cost', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir()
    build = args.build.resolve()
    sources = json.loads((build / 'sources.json').read_text())
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == json.loads((build / 'executable.json').read_text())
    screen_dir = args.screen.resolve()
    screen = screen_dir / 'output/screen.json'
    screen_data = json.loads(screen.read_text())
    assert screen_data['bounded_photographic_prototype_admitted'] is False
    sb = json.loads((screen_dir / 'bindings.json').read_text())
    assert sb['sources'] == sources and sb['executable'] == c.ref(exe)
    expected_hashes = ['76b42e87ca9a53011af3f8a9d6d81b0925534c9075d67476be3c192a57c8be40',
        '893ef6e6fbf4ab76e42e94a8506cfc7ff4bf94c8d33bd2e86142a2a7335a22b7']
    assert screen_data['observer_neutrality']['on_rgb_sha256'] == expected_hashes
    assert screen_data['observer_neutrality']['off_rgb_sha256'] == expected_hashes
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe),
        runner=c.ref(Path(__file__)), failed_screen=c.ref(screen),
        independent_plan=c.ref(HERE / 'independent-full-plan.md'),
        separate_observational_plan=c.ref(HERE / 'observational-plan.md')))
    fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_BOUNDARY_CFA_WAVELET_OUT=str(out / 'output'))
    if args.phase == 'controls':
        command = [str(exe), 'merge_cmd::boundary_cfa_wavelet::independent_full_controls::',
            '--nocapture', '--test-threads=1']
        c.job(command, fields, out, wall=180)
        log = (out / 'process.log').read_text()
        assert 'test result: ok. 1 passed;' in log
        rows = [json.loads(line.split('BOUNDARY_CFA_FULL_MECHANICAL ', 1)[1])
            for line in log.splitlines() if 'BOUNDARY_CFA_FULL_MECHANICAL ' in line]
        assert len(rows) == 1
        assert all(c.ref(Path(row['path'])) == row for row in sources)
        c.save(out / 'completion.json', dict(mechanical_passed=True, record=rows[0],
            sources_unchanged=True, photographic_promotion=False))
        return
    assert args.mechanical is not None
    mechanical = args.mechanical.resolve()
    mb = json.loads((mechanical / 'bindings.json').read_text())
    assert mb['sources'] == sources and mb['executable'] == c.ref(exe)
    assert json.loads((mechanical / 'completion.json').read_text())['mechanical_passed']
    c.save(out / 'mechanical-binding.json', c.ref(mechanical / 'completion.json'))
    if args.phase == 'full':
        assert args.cost is not None
        cost = args.cost.resolve()
        cb = json.loads((cost / 'bindings.json').read_text())
        assert cb['sources'] == sources and cb['executable'] == c.ref(exe)
        decision = cost / 'root-cost-decision.json'
        assert json.loads(decision.read_text())['observational_full_feasible'] is True
        c.save(out / 'cost-binding.json', dict(decision=c.ref(decision),
            measured=c.ref(cost / 'output/cost.json'), process=c.ref(cost / 'process.json')))
    prior = json.loads((ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/invocation.json').read_text())
    inputs = prior['inputs']
    assert len(inputs) == 70
    warp = ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
    warp_ref = c.ref(warp)
    assert warp_ref['sha256'] == '84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f'
    cfg = dict(schema=1, source_dir=str(Path(inputs[0]['path']).parent), warp_map=str(warp),
        warp_map_sha256=warp_ref['sha256'], out_dir=str(out / 'output'),
        expected_crop=[28, 19, 3460, 2306], max_extra_inset_quads=0,
        expected_xyz_to_cam=[[.7460, -.2365, -.0588], [-.5687, 1.3442, .2474], [-.0624, .1156, .6584]],
        tone=[.090420, .914606, .55])
    c.save(out / 'config.json', cfg)
    c.save(out / 'inputs.json', dict(inputs=inputs, map=warp_ref))
    fields.update(STREHL_WARPMAP=str(warp), STREHL_BOUNDARY_CFA_FULL_CONFIG=str(out / 'config.json'),
        STREHL_BOUNDARY_CFA_PHASE=args.phase)
    command = [str(exe), 'merge_cmd::boundary_cfa_wavelet::full_stack::vitamin_c_observational_pair',
        '--exact', '--ignored', '--nocapture', '--test-threads=1']
    def check_inputs():
        for row in inputs:
            st = Path(row['path']).stat()
            assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    check_inputs()
    c.job(command, fields, out, wall=1800 if args.phase == 'full' else 300)
    log = (out / 'process.log').read_text()
    assert 'test result: ok. 1 passed;' in log
    check_inputs()
    assert c.ref(warp) == warp_ref
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    if args.phase == 'cost':
        c.save(out / 'completion.json', dict(cost=c.ref(out / 'output/cost.json'),
            original_metadata_unchanged=True, map_unchanged=True, sources_unchanged=True,
            photographic_promotion=False))
        return
    import numpy as np
    import tifffile
    reference = ROOT / 'experiments/phase-packed-rgb/full-1/output/baseline.tiff'
    assert c.ref(reference)['sha256'] == 'c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21'
    baseline = out / 'output/baseline.tiff'
    candidate = out / 'output/candidate.tiff'
    assert np.array_equal(tifffile.imread(baseline), tifffile.imread(reference))
    for path in [baseline, candidate]:
        with tifffile.TiffFile(path) as tif:
            assert tif.pages[0].shape == (4612, 6920, 3) and tif.pages[0].dtype == np.uint16
    c.save(out / 'completion.json', dict(baseline=c.ref(baseline), candidate=c.ref(candidate),
        receipt=c.ref(out / 'output/receipt.json'), shape=[4612, 6920, 3],
        original_metadata_unchanged=True, map_unchanged=True, baseline_pixels_identical=True,
        reference=c.ref(reference), sources_unchanged=True, photographic_promotion=False,
        scope='One separately scoped observational photograph; generated admission remains false.'))


if __name__ == '__main__':
    main()
