"""Root-executed fixed real-chip cost checkpoint and complete common-field pair."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ca_full_bounds', ROOT/'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
MAP = ROOT/'experiments/quality-september14/chip-baseline-1/chip.warpmap.txt'
MAP_HASH = 'ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922'
OLD_SCREEN_HASH = '769305780eb7e9611776171413684e2eedcecdbf52894e568fba2d2d2435018c'
CROP = [141, 97, 3234, 2150]
TEST = 'merge_cmd::ca_before_mhc_full::chip_actual_consumer'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def job(command, fields, out, cost):
    env, removed = c.b.clean_environment(fields.items())
    c.save(out/'invocation.json', dict(command=command, environment=fields,
        removed_environment=removed, runner=c.ref(Path(__file__))))
    api = c.b.load_job_api(c.b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out/'process.log', api=api,
        wall_seconds=120 if cost else 1800, cpu_seconds=300 if cost else 3600,
        committed_bytes=(12 if cost else 16) << 30, log_bytes=16 << 20)
    c.save(out/'process.json', result)
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    assert 'test result: ok. 1 passed;' in (out/'process.log').read_text(encoding='utf-8')
    return result


def screen_binding(screen, exe):
    old = HERE/'screen-1/output/screen.json'
    assert c.ref(old)['sha256'] == OLD_SCREEN_HASH
    original = read(old)
    assert original['photographic_replay_admitted'] is False
    rerun = screen/'output/screen.json'
    qualification = screen/'output/qualification.json'
    operator = screen/'output/operator.json'
    assert read(rerun) == original, 'original twenty-case result changed'
    q = read(qualification)
    assert q['instrument_passed'] and q['supplementary_colour_admitted']
    assert q['case_count'] == 8 and q['original_screen1_reclassified'] is False
    assert read(operator)['passed']
    process = read(screen/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    invocation = read(screen/'invocation.json')
    assert Path(invocation['command'][0]).resolve() == exe
    assert read(screen/'completion.json')['controls_executed']
    return dict(original_failed_screen=c.ref(old), same_build_original_rerun=c.ref(rerun),
        qualifying_screen=c.ref(qualification), operator=c.ref(operator),
        invocation=c.ref(screen/'invocation.json'), completion=c.ref(screen/'completion.json'))


def write_views(path, out, name):
    import numpy as np
    import tifffile
    from PIL import Image
    with tifffile.TiffFile(path) as tif:
        assert len(tif.pages) == 1 and tif.pages[0].shape == (4300, 6468, 3)
        assert tif.pages[0].dtype == np.uint16
        tag = tif.pages[0].tags.get(34675)
        icc = bytes(tag.value) if tag is not None else None
        pixels = tif.asarray()
    rgb_hash = hashlib.sha256(pixels.astype('<u2', copy=False).tobytes()).hexdigest()
    image = Image.fromarray((pixels >> 8).astype(np.uint8), mode='RGB')
    native = out/(name+'-whole.png')
    overview = out/(name+'-overview.png')
    metadata = {'icc_profile': icc} if icc is not None else {}
    image.save(native, **metadata)
    image.resize((1617, 1075), Image.Resampling.LANCZOS).save(overview, **metadata)
    for display_path in (native, overview):
        with Image.open(display_path) as check:
            assert check.info.get('icc_profile') == icc
    return dict(master=c.ref(path), native_whole=c.ref(native), overview=c.ref(overview),
        rgb16_le_sha256=rgb_hash, icc_sha256=hashlib.sha256(icc).hexdigest() if icc is not None else None,
        display='fixed high byte; overview 1/4, no automatic contrast; TIFF ICC preserved')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=('cost', 'full'))
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--screen', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--cost', type=Path)
    args = p.parse_args()
    build, screen, out = (v.resolve() for v in (args.build, args.screen, args.out))
    assert out.is_relative_to(HERE) and out != HERE
    sources = read(build/'sources.json')
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = (build/'cli-tests.exe').resolve()
    assert c.ref(exe) == read(build/'executables.json')['cli-tests']
    required = {str((HERE/n).resolve()) for n in ('full-implementation.rs', 'full-run.py', 'full-plan.md')}
    assert required <= {row['path'] for row in sources}, 'full adapter/driver must be build-bound'
    admission = screen_binding(screen, exe)
    support = HERE/'support-preflight-1.json'
    preflight = read(support)
    assert preflight['map_sha256'] == MAP_HASH
    assert c.ref(HERE/'support-preflight.py')['sha256'] == preflight['script_sha256']
    assert any(row['crop_quad_xywh'] == CROP and row['sufficient_support'] for row in preflight['cases'])
    assert c.ref(MAP)['sha256'] == MAP_HASH
    inputs = read(ROOT/'experiments/quality-september14/chip-baseline-1/invocation.json')['inputs']
    assert len(inputs) == 299
    source_dir = Path(inputs[0]['path']).parent
    assert source_dir.name == 'uncapped-IC-chip-cpl'
    def check_inputs():
        for i, row in enumerate(inputs):
            path = Path(row['path'])
            assert path.name == f'DSC{i+1:05d}.ARW'
            st = path.stat()
            assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
        assert c.ref(MAP)['sha256'] == MAP_HASH
        assert all(c.ref(Path(row['path'])) == row for row in sources)
    check_inputs()
    selected_original = c.ref(Path(inputs[149]['path']))
    prior_cost = None
    if args.phase == 'full':
        assert args.cost
        cost = args.cost.resolve()
        cb = read(cost/'bindings.json')
        assert cb['sources'] == sources and cb['executable'] == c.ref(exe)
        assert cb['admission'] == admission
        decision = read(cost/'cost-decision.json')
        assert decision['full_pair_feasible']
        for arm in ('current', 'before'):
            assert decision['arms'][arm]['receipt'] == c.ref(cost/arm/'output/receipt.json')
            assert decision['arms'][arm]['process'] == c.ref(cost/arm/'process.json')
        prior_cost = c.ref(cost/'cost-decision.json')
    out.mkdir(exist_ok=False)
    c.save(out/'bindings.json', dict(sources=sources, executable=c.ref(exe), admission=admission,
        support=c.ref(support), runner=c.ref(Path(__file__)), map=c.ref(MAP),
        original_source149=selected_original, prior_cost=prior_cost,
        inspection_plan=c.ref(HERE/'photographic-inspection-plan.md')))
    c.save(out/'inputs.json', inputs)
    results, views = {}, {}
    for arm, mode in (('current', 'off'), ('before', 'before')):
        dest = out/arm
        dest.mkdir()
        config = dict(schema=1, phase=args.phase, mode=mode, source_dir=str(source_dir),
            warp_map=str(MAP), out_dir=str(dest/'output'), expected_crop=CROP,
            tone=[.004293, .946441, .55])
        c.save(dest/'config.json', config)
        fields = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
            STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
            STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
            STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_CA_BEFORE_MHC=mode,
            STREHL_WARPMAP=str(MAP), STREHL_CA_BEFORE_MHC_FULL_CONFIG=str(dest/'config.json'))
        process = job([str(exe), TEST, '--exact', '--ignored', '--nocapture', '--test-threads=1'],
            fields, dest, args.phase == 'cost')
        check_inputs()
        receipt = read(dest/'output/receipt.json')
        assert receipt['phase'] == args.phase and receipt['mode'] == mode
        assert receipt['crop'] == CROP and receipt['native_dimensions'] == [6468, 4300]
        assert receipt['source_count'] == (1 if args.phase == 'cost' else 299)
        assert receipt['observer'] is False and receipt['original_metadata_unchanged']
        assert [f['index'] for f in receipt['frames']] == ([149] if args.phase == 'cost' else list(range(299)))
        results[arm] = receipt
        if args.phase == 'full':
            views[arm] = write_views(dest/'output/image.tiff', out, arm)
            assert views[arm]['rgb16_le_sha256'] == receipt['rgb16_le_sha256']
    assert c.ref(Path(inputs[149]['path'])) == selected_original
    for key in ('plan', 'crop', 'tone_bits', 'wb_bits', 'matrix', 'source_count'):
        assert results['current'][key] == results['before'][key]
    assert [(f['index'], f['active_u16_sha256']) for f in results['current']['frames']] == [
        (f['index'], f['active_u16_sha256']) for f in results['before']['frames']]
    if args.phase == 'full':
        assert views['current']['icc_sha256'] == views['before']['icc_sha256']
    if args.phase == 'cost':
        arms = {}
        for arm, receipt in results.items():
            process = read(out/arm/'process.json')
            estimate = 299*receipt['source_phase_seconds'] + receipt['finish_seconds'] + 120
            peak = process['job_memory']['peak_job_memory_used_bytes']
            arms[arm] = dict(estimated_full_seconds=estimate, maximum_estimate_seconds=1500,
                cost_peak_bytes=peak, feasible=estimate <= 1500 and peak < (12 << 30),
                receipt=c.ref(out/arm/'output/receipt.json'), process=c.ref(out/arm/'process.json'))
        c.save(out/'cost-decision.json', dict(arms=arms, full_pair_feasible=all(v['feasible'] for v in arms.values()),
            full_limits=dict(wall_seconds_per_arm=1800, cpu_seconds_per_arm=3600, committed_bytes=16 << 30),
            scope='Single-source feasibility extrapolation, not a speed benchmark or photographic result.'))
    c.save(out/'completion.json', dict(phase=args.phase, sources_unchanged=True, original_metadata_unchanged=True,
        same_original_source_arrays=True, common_crop=CROP, fresh_current_baseline=True, views=views,
        original_failed_screen_reclassified=False, photographic_promotion=False))


if __name__ == '__main__':
    main()
