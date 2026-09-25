"""Root-only native coherent estimator screen and separately gated chip observation."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


g = load('native_coherent_bounded_helpers', ROOT/'experiments/cross-scale-source-prior/run.py')
p = load('native_coherent_view_helpers', ROOT/'experiments/phase-packed-chip/run.py')
c = g.c
read = g.read
unchanged = g.unchanged
FILTER = 'merge_cmd::native_coherent_estimator::independent_controls::'
TEST = 'merge_cmd::native_coherent_estimator_chip::chip_complete_pair'
MAP = p.MAP
CROP = p.CROP
BASE = ROOT/'experiments/phase-packed-chip/full-1/output/baseline.tiff'
BASE_FILE = '46692b100544fca30358f2594d5aeeebd3c620f313efc9561b3c2da3f8dcefa2'
BASE_RECEIPT = BASE.parent/'receipt.json'
BASE_RECEIPT_HASH = '93d50cf43c5773bdc507abaa63fe307dfb3884c521c4f7cdfdea484587efb4b9'
BASE_PIXELS = '7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db'
REGIONS = p.CA/'inspection-1/views.json'
REGIONS_HASH = 'e2a44d87584f7ca0ac0424d3827baf4b61404bd7224e0664244b8a215b04517e'
LOCAL_SOURCES = ('implementation.rs', 'design.md',
    'independent-controls.rs', 'independent-plan.md', 'runner.py', 'runner-plan.md')
SCOPE = ('New fixed native whole-source estimator: general qualification and optional '
    'coherent-surface photographic observation are separate preregistered decisions. '
    'A photographic gate pass licenses one observation, not a default change, automatic '
    'scene classifier, general quality claim, or SOTA result.')


def job(command, env, out, **limits):
    c.save(out/'driver.json', dict(driver=c.ref(Path(__file__)), bounded_helper=c.ref(ROOT/'experiments/cross-scale-source-prior/run.py'),
        command=command, limits=limits, scope=SCOPE))
    return g.job(command, env, out, **limits)


def bindings():
    # Keep all actual include surfaces; never bind future output/photographic review files.
    paths = set(c.source_paths())
    for folder in (ROOT/'crates', ROOT/'experiments/native-gpu-gather/src', ROOT/'experiments/native-sensor-transfer/source'):
        paths.update(path for path in folder.rglob('*') if path.is_file() and path.suffix in ('.rs', '.wgsl', '.toml'))
    for suffix in ('*.rs', '*.wgsl'):
        paths.update((ROOT/'experiments').glob('*/'+suffix))
    paths.update(ROOT/name for name in ('Cargo.toml', 'Cargo.lock', 'experiments/native-gpu-gather/Cargo.toml',
        'experiments/cross-scale-source-prior/run.py', 'experiments/phase-packed-chip/run.py',
        'experiments/full-context-placement/run.py', 'experiments/m193c-output-grid/bounded-process.py',
        'experiments/m12-scorecard/m12-harness.py'))
    assert all((HERE/name).is_file() for name in LOCAL_SOURCES)
    paths.update(HERE/name for name in LOCAL_SOURCES)
    paths.update((REGIONS, BASE_RECEIPT))
    # These are fixed before build when present; subsequent outcome reports are excluded.
    for name in ('source-review.md', 'chip-design.md', 'chip-review.md'):
        if (HERE/name).is_file():
            paths.add(HERE/name)
    return [c.ref(path.resolve()) for path in sorted(paths)]


def pins():
    for path, sha in ((MAP, p.MAP_HASH), (BASE_RECEIPT, BASE_RECEIPT_HASH), (REGIONS, REGIONS_HASH)):
        assert c.ref(path)['sha256'] == sha, f'retained binding differs: {path}'


def fields():
    return dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_SCHEDULE='device',
        STREHL_GPU_GATHER_LOG='on', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off', STREHL_CA_BEFORE_MHC='off')


def screen_summary(path):
    screen = read(path)
    assert screen['status'] == 'SCREEN_COMPLETE' and len(screen['cases']) == 12
    for key in ('general_qualification_admitted', 'optional_chip_observation_admitted'):
        assert type(screen[key]) is bool
    assert sorted((row['iso'], row['scene']) for row in screen['cases']) == sorted(
        (iso, scene) for iso in (100.0, 400.0) for scene in
        ('flat', 'broad-bright-contact', 'neutral-glint-depth', 'chromatic-glint-depth',
         'near-fine-far-coarse', 'true-coloured-thin-rays'))
    return dict(screen=c.ref(path), general_qualification_admitted=screen['general_qualification_admitted'],
        optional_chip_observation_admitted=screen['optional_chip_observation_admitted'],
        cases=12, scope=SCOPE)


def screen_binding(screen, exe, sources):
    completion = read(screen/'completion.json')
    assert completion['controls_executed'] == 2 and completion['sources_unchanged']
    assert read(screen/'bindings.json') == dict(sources=sources, executable=c.ref(exe))
    invocation, process = read(screen/'invocation.json'), read(screen/'process.json')
    assert invocation['command'] == [str(exe), FILTER, '--nocapture', '--test-threads=1']
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    assert not process['cleanup_errors']
    decision = screen_summary(screen/'output/screen.json')
    assert completion['decision'] == decision
    assert decision['optional_chip_observation_admitted'] is True, 'optional photo gate refused'
    return dict(**decision, completion=c.ref(screen/'completion.json'),
        invocation=c.ref(screen/'invocation.json'), process=c.ref(screen/'process.json'))


def build(out):
    out.mkdir(exist_ok=False)
    for path in ('crates/strehl-cli/src/merge_cmd.rs', 'crates/strehl-core/src/pyramid.rs'):
        (ROOT/path).touch()
    sources = bindings()
    c.save(out/'sources.json', sources)
    command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--test', 'byte-freeze',
        '--no-run', '--release', '--features', g.FEATURES, '--jobs', '2',
        '--target-dir', str(ROOT/'target/native-pyramid-profile'),
        '--message-format=json-render-diagnostics', '--locked', '--offline']
    job(command, dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out, wall=600, cpu=1800, gib=16)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
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


def controls(out, exe, sources):
    out.mkdir(exist_ok=False)
    c.save(out/'bindings.json', dict(sources=sources, executable=c.ref(exe)))
    env = fields()
    env['STREHL_NATIVE_COHERENT_OUT'] = str(out/'output')
    job([str(exe), FILTER, '--nocapture', '--test-threads=1'], env, out, wall=180, cpu=900, gib=4)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['2']
    assert 'NATIVE_COHERENT {' in log
    decision = screen_summary(out/'output/screen.json')
    unchanged(sources)
    c.save(out/'completion.json', dict(controls_executed=2, sources_unchanged=True,
        decision=decision, scope=SCOPE))


def inputs():
    rows = read(ROOT/'experiments/quality-september14/chip-baseline-1/invocation.json')['inputs']
    assert len(rows) == 299
    directory = Path(rows[0]['path']).parent
    assert directory.name == 'uncapped-IC-chip-cpl'
    assert all(Path(row['path']).parent == directory and Path(row['path']).name == f'DSC{i+1:05d}.ARW'
        for i, row in enumerate(rows))
    return rows, directory


def check_inputs(rows, sources):
    for row in rows:
        st = Path(row['path']).stat()
        assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    pins()
    unchanged(sources)


def validate_receipt(run, phase):
    receipt = read(run/'output/receipt.json')
    assert receipt['phase'] == phase and receipt['crop'] == CROP
    assert receipt['native_dimensions'] == [6468, 4300] and receipt['map_sha256'] == p.MAP_HASH
    assert receipt['source_count'] == (1 if phase == 'cost' else 299)
    assert receipt['plan']['canonical_chunks'] == 4 and receipt['plan']['per_chunk'] == 75
    assert receipt['threads'] == 8 and receipt['original_metadata_unchanged'] is True
    assert receipt['replay_exact'] is True
    assert receipt['observer'] is False and receipt['unsupported_samples'] == 0 and receipt['all299_support_preflight'] is True
    assert receipt['probe_source_count'] == 299
    assert [row['index'] for row in receipt['frames']] == ([149] if phase == 'cost' else list(range(299)))
    reference = read(BASE_RECEIPT)
    expected = {row['index']: row for row in reference['frames']}
    for row in receipt['frames']:
        old = expected[row['index']]
        assert (row['active_u16_sha256'], row['beta']) == (old['active_u16_sha256'], old['beta'])
        assert row['replay_exact'] is True and row['source_unchanged'] is True
    for name in ('baseline', 'candidate'):
        assert c.ref(run/'output'/(name+'.tiff'))['sha256'] == receipt[name+'_sha256']
    if phase == 'cost':
        assert receipt['one_source_mean_exact'] is True
        assert receipt['candidate_planes_sha256'] == receipt['frames'][0]['known4_sha256']
    else:
        assert receipt['baseline_rgb16_le_sha256'] == BASE_PIXELS
        assert receipt['baseline_planes_sha256'] == reference['baseline_planes_sha256']
    return receipt


def observe(args, out, exe, sources, screen):
    rows, directory = inputs()
    check_inputs(rows, sources)
    assert c.ref(BASE)['sha256'] == BASE_FILE
    source149 = c.ref(Path(rows[149]['path']))
    prior_cost = None
    if args.phase == 'full':
        assert args.cost is not None
        cost = args.cost.resolve()
        bound = read(cost/'bindings.json')
        assert bound['sources'] == sources and bound['executable'] == c.ref(exe) and bound['screen_decision'] == screen
        decision = read(cost/'cost-decision.json')
        assert decision['resource_feasible'] and decision['receipt'] == c.ref(cost/'output/receipt.json')
        assert decision['process'] == c.ref(cost/'process.json')
        assert read(cost/'completion.json')['sources_unchanged']
        validate_receipt(cost, 'cost')
        prior_cost = c.ref(cost/'cost-decision.json')
    out.mkdir(exist_ok=False)
    c.save(out/'bindings.json', dict(sources=sources, executable=c.ref(exe), screen_decision=screen,
        map=c.ref(MAP), historical_baseline=c.ref(BASE), historical_baseline_receipt=c.ref(BASE_RECEIPT),
        original_source149=source149, prior_cost=prior_cost, regions=c.ref(REGIONS), scope=SCOPE))
    c.save(out/'inputs.json', rows)
    config = dict(schema=1, phase=args.phase, source_dir=str(directory), warp_map=str(MAP),
        out_dir=str(out/'output'), expected_crop=CROP, tone=[.004293, .946441, .55])
    c.save(out/'config.json', config)
    env = fields()
    env.update(STREHL_WARPMAP=str(MAP), STREHL_NATIVE_COHERENT_ESTIMATOR_CHIP_CONFIG=str(out/'config.json'))
    cost_mode = args.phase == 'cost'
    process = job([str(exe), TEST, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
        wall=180 if cost_mode else 1800, cpu=600 if cost_mode else 7200, gib=16)
    assert re.findall(r'test result: ok\. (\d+) passed;', (out/'process.log').read_text()) == ['1']
    check_inputs(rows, sources)
    assert c.ref(Path(rows[149]['path'])) == source149 and c.ref(BASE)['sha256'] == BASE_FILE
    receipt = validate_receipt(out, args.phase)
    if cost_mode:
        source_time, finish_time = receipt['source_phase_seconds'], receipt['finish_seconds']
        assert all(math.isfinite(t) and t > 0 for t in (source_time, finish_time))
        estimate = 1.25*299*source_time+finish_time+180
        peak = process['job_memory']['peak_job_memory_used_bytes']
        c.save(out/'cost-decision.json', dict(resource_feasible=estimate <= 1500 and peak < (12 << 30),
            estimated_full_seconds=estimate, maximum_estimate_seconds=1500, source_time_multiplier=1.25,
            source_phase_seconds=source_time, finish_seconds=finish_time, setup_allowance_seconds=180,
            cost_peak_bytes=peak, maximum_cost_peak_bytes=12 << 30,
            full_limits=dict(wall_seconds=1800, cpu_seconds=7200, committed_bytes=16 << 30),
            receipt=c.ref(out/'output/receipt.json'), process=c.ref(out/'process.json'),
            screen_decision=screen,
            limitation='One source measures both passes; extrapolation and cost peak cannot guarantee full runtime or peak. No speed or quality claim.'))
    else:
        exact_baseline(out/'output/baseline.tiff')
    c.save(out/'completion.json', dict(phase=args.phase, sources_unchanged=True,
        original_metadata_unchanged=True, historical_full_baseline_exact=not cost_mode,
        receipt=c.ref(out/'output/receipt.json'), screen_decision=screen, scope=SCOPE))


def exact_baseline(path):
    import numpy as np
    import tifffile
    current, historical = tifffile.imread(path), tifffile.imread(BASE)
    assert current.shape == historical.shape == (4300, 6468, 3)
    assert current.dtype == historical.dtype == np.uint16 and np.array_equal(current, historical)
    assert hashlib.sha256(current.astype('<u2', copy=False).tobytes()).hexdigest() == BASE_PIXELS


def finalise(run, out, exe, sources, screen):
    from PIL import Image
    bound = read(run/'bindings.json')
    assert bound['sources'] == sources and bound['executable'] == c.ref(exe) and bound['screen_decision'] == screen
    assert bound['regions'] == c.ref(REGIONS) and bound['historical_baseline'] == c.ref(BASE)
    completion = read(run/'completion.json')
    assert completion['phase'] == 'full' and completion['sources_unchanged'] and completion['historical_full_baseline_exact']
    assert completion['receipt'] == c.ref(run/'output/receipt.json')
    receipt = validate_receipt(run, 'full')
    exact_baseline(run/'output/baseline.tiff')
    out.mkdir(exist_ok=False)
    views = {name: p.write_views(run/'output'/(name+'.tiff'), out, name) for name in ('baseline', 'candidate')}
    assert views['baseline']['icc_sha256'] == views['candidate']['icc_sha256']
    assert views['baseline']['icc_sha256'] is not None, 'held TIFF ICC absent'
    pairs = []
    for left, right in zip(views['baseline']['regions'], views['candidate']['regions']):
        assert left['region'] == right['region'] and left['output_native_xywh'] == right['output_native_xywh']
        with Image.open(left['image']['path']) as a, Image.open(right['image']['path']) as b:
            assert a.size == b.size and a.info.get('icc_profile') == b.info.get('icc_profile')
            pair = Image.new('RGB', (a.width+b.width, a.height))
            pair.paste(a, (0, 0)); pair.paste(b, (a.width, 0))
            path = out/(left['region']+'-baseline-left-candidate-right.png')
            pair.save(path, icc_profile=a.info['icc_profile'])
            with Image.open(path) as check:
                assert check.info.get('icc_profile') == a.info['icc_profile']
                assert check.crop((0, 0, a.width, a.height)).tobytes() == a.tobytes()
                assert check.crop((a.width, 0, a.width+b.width, b.height)).tobytes() == b.tobytes()
        pairs.append(dict(region=left['region'], output_native_xywh=left['output_native_xywh'], image=c.ref(path)))
    assert len(pairs) == 7
    for name in views:
        assert views[name]['rgb16_le_sha256'] == receipt[name+'_rgb16_le_sha256']
    unchanged(sources)
    c.save(out/'completion.json', dict(views=views, pairs=pairs, layout='canonical baseline left; native coherent estimator right',
        receipt=c.ref(run/'output/receipt.json'), full_run_completion=c.ref(run/'completion.json'),
        source_bindings=bound, historical_full_baseline_exact=True, screen_decision=screen,
        visual_verdict=None, scope=SCOPE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build', 'controls', 'cost', 'full', 'finalise'))
    parser.add_argument('--out', type=Path, required=True)
    for name in ('build', 'screen', 'cost', 'run'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    assert args.phase in ('build', 'controls'), 'Full photograph adapter was not completed before interruption; generated screen only.'
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    pins()
    if args.phase == 'build':
        build(out)
        return
    assert args.build is not None
    build_dir = args.build.resolve()
    sources = read(build_dir/'sources.json')
    unchanged(sources)
    assert {str((HERE/name).resolve()) for name in LOCAL_SOURCES} <= {row['path'] for row in sources}
    exe = build_dir/'cli-tests.exe'
    assert c.ref(exe) == read(build_dir/'executables.json')['cli-tests']
    if args.phase == 'controls':
        controls(out, exe, sources)
        return
    assert args.screen is not None
    screen = screen_binding(args.screen.resolve(), exe, sources)
    if args.phase == 'finalise':
        assert args.run is not None
        finalise(args.run.resolve(), out, exe, sources, screen)
    else:
        observe(args, out, exe, sources, screen)


if __name__ == '__main__':
    main()
