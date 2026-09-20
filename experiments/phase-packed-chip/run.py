"""Root-executed unchanged twelve-plane chip observation; no default dispatch."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT/'experiments/phase-packed-rgb'
CA = ROOT/'experiments/ca-before-mhc'
spec = importlib.util.spec_from_file_location('packed_chip_bounds', ROOT/'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
MAP = ROOT/'experiments/quality-september14/chip-baseline-1/chip.warpmap.txt'
MAP_HASH = 'ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922'
BASE = CA/'full-1/current/output/image.tiff'
BASE_FILE = 'c69db8e95e4f26df43632d453027770d1e52baae150ebe0e0916b47fd68f74b4'
BASE_PIXELS = '7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db'
SCREEN_HASH = '431fe14cb2a0b07ad53137f3c080e139b6091d79462b7eba62dfa7232a8b85d1'
CONTROLS_HASH = '572d028a0d83214f9df8ac47634f04e703c855a93d96439a9c8534a5f0b240f9'
CROP = [141, 97, 3234, 2150]
TEST = 'merge_cmd::phase_packed_chip::chip_complete_pair'
FILTER = 'merge_cmd::phase_packed_rgb::independent_controls::'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def bindings():
    paths = set(c.source_paths())
    for folder in (ROOT/'crates', ROOT/'experiments/native-gpu-gather/src'):
        paths.update(p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.rs', '.wgsl', '.toml'))
    for folder in (HERE, OLD, CA):
        paths.update(p for p in folder.iterdir() if p.is_file() and p.suffix in ('.rs', '.wgsl', '.py', '.md'))
    paths.update((ROOT/'experiments/native-gpu-gather/integration.rs', ROOT/'experiments/native-gpu-gather/Cargo.toml'))
    return [c.ref(p.resolve()) for p in sorted(paths)]


def unchanged(sources):
    assert all(c.ref(Path(row['path'])) == row for row in sources), 'bound source changed'


def job(command, fields, out, wall, cpu, gib):
    env, removed = c.b.clean_environment(fields.items())
    c.save(out/'invocation.json', dict(command=command, environment=fields,
        removed_environment=removed, executable=c.ref(Path(command[0])), runner=c.ref(Path(__file__))))
    api = c.b.load_job_api(c.b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out/'process.log', api=api,
        wall_seconds=wall, cpu_seconds=cpu, committed_bytes=gib << 30, log_bytes=16 << 20)
    c.save(out/'process.json', result)
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    return result


def fields(gpu):
    return dict(RAYON_NUM_THREADS='8' if gpu else '2', STREHL_PYRAMID_WORKERS='8',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on' if gpu else 'off',
        STREHL_GPU_SCHEDULE='device', STREHL_GPU_GATHER_LOG='off', STREHL_DEFECT='off',
        STREHL_CA_BEFORE_MHC='off')


def compare_screen(path):
    old_path = OLD/'screen-2/output/screen.json'
    assert c.ref(old_path)['sha256'] == SCREEN_HASH
    assert c.ref(OLD/'independent-controls.rs')['sha256'] == CONTROLS_HASH
    old, new = read(old_path), read(path)
    assert len(new['cases']) == 28 and new['cases'] == old['cases']
    # Only the artifact pathname legitimately changes between fresh directories.
    a, b = copy.deepcopy(old), copy.deepcopy(new)
    a['actual_writer'].pop('tiff')
    b['actual_writer'].pop('tiff')
    assert a == b, 'frozen screen values or decisions changed'
    assert new['photographic_replay_admitted'] is True
    assert Path(new['actual_writer']['tiff']).resolve().parent == path.parent.resolve()
    return dict(retained_screen=c.ref(old_path), fresh_screen=c.ref(path),
        unchanged_28_cases=True, original_flat_limit=1.25, historical_worst_flat_chroma_ratio=1.078951,
        strict_1_05_flat_chroma_pass=False, vitamin_failure=c.ref(OLD/'full-1/photo-comparison-1/photographic-review.md'))


def screen_binding(screen, exe, sources):
    completion = read(screen/'completion.json')
    assert completion['controls_executed'] == 4 and completion['sources_unchanged']
    assert read(screen/'bindings.json') == dict(sources=sources, executable=c.ref(exe))
    process = read(screen/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    invocation = read(screen/'invocation.json')
    assert invocation['command'] == [str(exe), FILTER, '--nocapture', '--test-threads=1']
    assert invocation['executable'] == c.ref(exe)
    return dict(**compare_screen(screen/'output/screen.json'), completion=c.ref(screen/'completion.json'),
        process=c.ref(screen/'process.json'), invocation=c.ref(screen/'invocation.json'))


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
    native, overview = out/(name+'-whole.png'), out/(name+'-overview.png')
    metadata = {'icc_profile': icc} if icc is not None else {}
    image.save(native, **metadata)
    image.resize((1617, 1075), Image.Resampling.LANCZOS).save(overview, **metadata)
    for display in (native, overview):
        with Image.open(display) as check:
            assert check.info.get('icc_profile') == icc
    regions = read(CA/'inspection-1/views.json')['regions']
    assert len(regions) == 7
    patches = []
    for region in regions:
        x, y, w, h = region['output_native_xywh']
        assert 0 <= x < x+w <= 6468 and 0 <= y < y+h <= 4300
        target = out/(region['region']+'-'+name+'.png')
        image.crop((x, y, x+w, y+h)).save(target, **metadata)
        patches.append(dict(region=region['region'], output_native_xywh=[x, y, w, h], image=c.ref(target)))
    return dict(master=c.ref(path), native_whole=c.ref(native), overview=c.ref(overview), regions=patches,
        rgb16_le_sha256=rgb_hash, icc_sha256=hashlib.sha256(icc).hexdigest() if icc is not None else None,
        display='fixed high byte; overview1/4; seven native crops; no automatic contrast; TIFF ICC preserved')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=('build', 'controls', 'cost', 'full'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--build', type=Path)
    p.add_argument('--screen', type=Path)
    p.add_argument('--cost', type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE
    if args.phase == 'build':
        out.mkdir(exist_ok=False)
        (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
        sources = bindings()
        c.save(out/'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--test', 'byte-freeze',
            '--no-run', '--release', '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes',
            '--jobs', '2', '--target-dir', str(ROOT/'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics', '--locked', '--offline']
        c.job(command, dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out)
        log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        artifacts = {}
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'strehl':
                key = 'cli-tests' if row['profile']['test'] else 'strehl'
                assert key not in artifacts
                destination = out/(key+'.exe')
                shutil.copyfile(row['executable'], destination)
                artifacts[key] = c.ref(destination)
        assert set(artifacts) == {'cli-tests', 'strehl'}
        unchanged(sources)
        c.save(out/'executables.json', artifacts)
        return
    assert args.build
    build = args.build.resolve()
    sources = read(build/'sources.json')
    unchanged(sources)
    assert {str((HERE/n).resolve()) for n in ('implementation.rs', 'run.py', 'plan.md', 'independent-plan.md')} <= {r['path'] for r in sources}
    exe = (build/'cli-tests.exe').resolve()
    assert c.ref(exe) == read(build/'executables.json')['cli-tests']
    if args.phase == 'controls':
        out.mkdir(exist_ok=False)
        c.save(out/'bindings.json', dict(sources=sources, executable=c.ref(exe)))
        env = fields(False)
        env['STREHL_PHASE_PACKED_OUT'] = str(out/'output')
        job([str(exe), FILTER, '--nocapture', '--test-threads=1'], env, out, 120, 300, 4)
        assert re.findall(r'test result: ok\. (\d+) passed;', (out/'process.log').read_text()) == ['4']
        admission = compare_screen(out/'output/screen.json')
        unchanged(sources)
        c.save(out/'completion.json', dict(controls_executed=4, sources_unchanged=True, admission=admission))
        return
    assert args.screen
    admission = screen_binding(args.screen.resolve(), exe, sources)
    assert c.ref(MAP)['sha256'] == MAP_HASH and c.ref(BASE)['sha256'] == BASE_FILE
    inputs = read(ROOT/'experiments/quality-september14/chip-baseline-1/invocation.json')['inputs']
    assert len(inputs) == 299
    source_dir = Path(inputs[0]['path']).parent
    assert source_dir.name == 'uncapped-IC-chip-cpl'
    def check_inputs():
        for i, row in enumerate(inputs):
            source = Path(row['path'])
            assert source.name == f'DSC{i+1:05d}.ARW'
            st = source.stat()
            assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
        assert c.ref(MAP)['sha256'] == MAP_HASH
        unchanged(sources)
    check_inputs()
    selected = c.ref(Path(inputs[149]['path']))
    prior_cost = None
    if args.phase == 'full':
        assert args.cost
        cost = args.cost.resolve()
        cb = read(cost/'bindings.json')
        assert cb['sources'] == sources and cb['executable'] == c.ref(exe) and cb['admission'] == admission
        decision = read(cost/'cost-decision.json')
        assert decision['full_pair_feasible'] and decision['receipt'] == c.ref(cost/'output/receipt.json')
        assert decision['process'] == c.ref(cost/'process.json')
        assert read(cost/'completion.json')['sources_unchanged']
        prior_cost = c.ref(cost/'cost-decision.json')
    out.mkdir(exist_ok=False)
    c.save(out/'bindings.json', dict(sources=sources, executable=c.ref(exe), admission=admission, map=c.ref(MAP),
        historical_baseline=c.ref(BASE), original_source149=selected, prior_cost=prior_cost,
        inspection_regions=c.ref(CA/'inspection-1/views.json')))
    c.save(out/'inputs.json', inputs)
    config = dict(schema=1, phase=args.phase, source_dir=str(source_dir), warp_map=str(MAP),
        out_dir=str(out/'output'), expected_crop=CROP, tone=[.004293, .946441, .55])
    c.save(out/'config.json', config)
    env = fields(True)
    env.update(STREHL_ALIGN='1', STREHL_WARPMAP=str(MAP), STREHL_PHASE_PACKED_CHIP_CONFIG=str(out/'config.json'))
    cost_mode = args.phase == 'cost'
    process = job([str(exe), TEST, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
        180 if cost_mode else 1800, 600 if cost_mode else 7200, 16)
    assert 'test result: ok. 1 passed;' in (out/'process.log').read_text()
    check_inputs()
    assert c.ref(Path(inputs[149]['path'])) == selected and c.ref(BASE)['sha256'] == BASE_FILE
    receipt = read(out/'output/receipt.json')
    assert receipt['phase'] == args.phase and receipt['crop'] == CROP and receipt['native_dimensions'] == [6468, 4300]
    assert receipt['source_count'] == (1 if cost_mode else 299) and receipt['observer'] is False
    assert receipt['known4_after_finish'] == receipt['admission'] == 'BIT_EXACT'
    assert receipt['baseline_planes_sha256'] == receipt['candidate_planes_sha256'][:4]
    assert receipt['unsupported_samples'] == 0 and receipt['all299_twelve_pull_preflight']
    assert receipt['original_metadata_unchanged'] and receipt['plan']['per_chunk'] == 75
    assert [f['index'] for f in receipt['frames']] == ([149] if cost_mode else list(range(299)))
    views = {}
    if cost_mode:
        estimate = 299*receipt['source_phase_seconds']+receipt['finish_seconds']+120
        peak = process['job_memory']['peak_job_memory_used_bytes']
        c.save(out/'cost-decision.json', dict(full_pair_feasible=estimate <= 1500 and peak < (12 << 30),
            estimated_full_seconds=estimate, maximum_estimate_seconds=1500, cost_peak_bytes=peak,
            whole_job_cpu_times299_upper_estimate=299*process['job_accounting']['total_cpu_100ns']/1e7,
            cpu_estimate_used_as_gate=False, full_limits=dict(wall_seconds=1800, cpu_seconds=7200, committed_bytes=16 << 30),
            receipt=c.ref(out/'output/receipt.json'), process=c.ref(out/'process.json'),
            scope='Feasibility only; whole-job CPU extrapolation repeats fixed writers/hash/setup and is not an admission predicate.'))
    else:
        import numpy as np
        import tifffile
        base = tifffile.imread(out/'output/baseline.tiff')
        historical = tifffile.imread(BASE)
        assert base.dtype == historical.dtype == np.uint16 and base.shape == historical.shape == (4300, 6468, 3)
        assert np.array_equal(base, historical), 'historical complete baseline differs'
        assert hashlib.sha256(base.astype('<u2', copy=False).tobytes()).hexdigest() == receipt['baseline_rgb16_le_sha256'] == BASE_PIXELS
        del base, historical
        for name in ('baseline', 'candidate'):
            views[name] = write_views(out/'output'/(name+'.tiff'), out, name)
            assert views[name]['rgb16_le_sha256'] == receipt[name+'_rgb16_le_sha256']
        assert views['baseline']['icc_sha256'] == views['candidate']['icc_sha256']
        reference = read(CA/'full-1/current/output/receipt.json')
        assert receipt['baseline_planes_sha256'] == reference['planes_sha256']
        assert [(r['index'], r['active_u16_sha256'], r['beta']) for r in receipt['frames']] == [
            (r['index'], r['active_u16_sha256'], r['beta']) for r in reference['frames']]
    c.save(out/'completion.json', dict(phase=args.phase, sources_unchanged=True, original_metadata_unchanged=True,
        common_crop=CROP, views=views, historical_full_baseline_exact=not cost_mode,
        old_vitamin_failure_preserved=True, strict_flat_guard_pass_claimed=False, photographic_promotion=False))


if __name__ == '__main__':
    main()
