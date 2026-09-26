"""Root-owned bounded build, controls and one complete current-chip observation."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASELINE = ROOT/'outputs/quality-september25/chip-fixed'
TARGETS = ROOT/'experiments/chip-stock-selectivity/targets.json'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


g = load('chip_shared_existing_bounds', ROOT/'experiments/cross-scale-source-prior/run.py')
c = g.c
s = load('chip_shared_fixed_chip', ROOT/'experiments/chip-stock-selectivity/run.py')
read, save, ref = g.read, c.save, c.ref
FILTER = 'merge_cmd::chip_shared_source_observation::independent_controls::'
FULL = 'merge_cmd::chip_shared_source_observation::full::complete_pair'
REQUIRED = ('run.py', 'costs.rs', 'implementation.rs', 'core-bridge.rs', 'full-adapter.rs',
            'design.md', 'independent-controls.rs', 'independent-plan.md', 'integration.md')
SCOPE = ('One separately authorized complete chip observation of the unchanged shared-source field. '
         'Its prior generated harm and failed qualification remain; no general/default promotion.')
OLD_SCREEN = ROOT/'experiments/shared-source-field/controls-1/output/screen.json'
OLD_SCREEN_HASH = '460ed3045c650ac1a8bf3a9819ccc8999b2b1a2e9bcee1ad7fd4abb2ea053d0f'
RETAINED_FILTER = 'merge_cmd::shared_source_field::independent_controls::'


def capacity_copies():
    changes = [('costs.rs', '(1..=70).contains(&frames)', '(1..=299).contains(&frames)'),
               ('core-bridge.rs', 'self.sources<70', 'self.sources<299')]
    records = []
    for name, old, new in changes:
        original = ROOT/'experiments/shared-source-field'/name
        extended = HERE/name
        a, b = original.read_text(), extended.read_text()
        assert a.count(old) == b.count(new) == 1 and b.replace(new, old) == a
        records.append(dict(original=ref(original), extended=ref(extended), old=old, new=new))
    # The literal pinned developer is copied, not independently reimplemented.
    def writer(path):
        text = path.read_text()
        return text[text.index('fn pinned_write('):text.index('fn icc(')]
    assert writer(HERE/'full-adapter.rs') == writer(ROOT/'experiments/band-source-agreement/full-adapter.rs')
    return records


def bindings():
    capacity_copies()
    # Reuse the complete current include/source inventory, not an old binary's
    # validation receipt. The inherited inventory scans sources only.
    paths = {Path(row['path']) for row in g.bindings()}
    # Root deliberately leaves this parallel generated-only lane uncompiled.
    # Exclude only that unreachable folder; all actual compiled sources remain.
    concurrent = (ROOT/'experiments/chromatic-source-evidence').resolve()
    paths = {path for path in paths if not path.resolve().is_relative_to(concurrent)}
    cli_hook = (ROOT/'crates/strehl-cli/src/merge_cmd.rs').read_text(encoding='utf-8')
    assert 'chromatic_source_evidence' not in cli_hook and 'chromatic-source-evidence/' not in cli_hook
    assert all('chromatic-source-evidence/' not in path.read_text(encoding='utf-8')
               for path in paths if path.suffix == '.rs'), 'Concurrent lane became reachable from included Rust.'
    assert all((HERE/name).is_file() for name in REQUIRED), 'Authors must freeze all sources before build.'
    paths.update(HERE/name for name in REQUIRED)
    paths.update((OLD_SCREEN, ROOT/'experiments/shared-source-field/results.md',
                  ROOT/'experiments/shared-source-field/results-review.md',
                  ROOT/'experiments/shared-source-field/charter.md',
                  ROOT/'experiments/band-source-agreement/full-adapter.rs'))
    paths.update((TARGETS, s.RETAINED, Path(s.__file__).resolve(),
                  ROOT/'experiments/chip-stock-selectivity/independent-plan.md'))
    return [ref(path.resolve()) for path in sorted(paths)]


def job(command, fields, out, *, wall, cpu, gib):
    env, removed = c.b.clean_environment(fields.items())
    save(out/'invocation.json', dict(command=command, environment=fields, removed_environment=removed,
         runner=ref(Path(__file__).resolve()), limits=dict(wall_seconds=wall, cpu_seconds=cpu, committed_bytes=gib<<30)))
    api = c.b.load_job_api(c.b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out/'process.log', api=api, wall_seconds=wall,
                    cpu_seconds=cpu, committed_bytes=gib<<30, log_bytes=16<<20)
    save(out/'process.json', result)
    print(json.dumps({key: result[key] for key in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    return result


def fields():
    return dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_SCHEDULE='device',
        STREHL_GPU_GATHER_LOG='on', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off', STREHL_CA_BEFORE_MHC='off')


def build(out):
    out.mkdir(exist_ok=False)
    for name in ('crates/strehl-cli/src/merge_cmd.rs', 'crates/strehl-core/src/pyramid.rs'):
        (ROOT/name).touch()
    sources = bindings()
    save(out/'sources.json', sources)
    command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--test', 'byte-freeze',
        '--no-run', '--release', '--features', g.FEATURES, '--jobs', '2',
        '--target-dir', str(ROOT/'target/native-pyramid-profile'),
        '--message-format=json-render-diagnostics', '--locked', '--offline']
    job(command, dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out, wall=600, cpu=2400, gib=16)
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
            artifacts[key] = ref(destination)
    assert set(artifacts) == {'cli-tests', 'strehl'}
    g.unchanged(sources)
    save(out/'executables.json', artifacts)


def shared_build(path):
    capacity_copies()
    sources = read(path/'sources.json')
    g.unchanged(sources)
    assert {str((HERE/name).resolve()) for name in REQUIRED} <= {row['path'] for row in sources}
    exe = path/'cli-tests.exe'
    assert ref(exe) == read(path/'executables.json')['cli-tests']
    log = (path/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
    return exe, sources


def check_job(path, expected_count):
    process = read(path/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    assert re.findall(r'test result: ok\. (\d+) passed;', (path/'process.log').read_text()) == [str(expected_count)]


def first_differences(old, fresh, path='$'):
    if type(old) is not type(fresh):
        yield dict(path=path, old=old, fresh=fresh)
    elif isinstance(old, dict):
        for key in sorted(old.keys() | fresh.keys()):
            if key not in old or key not in fresh:
                yield dict(path=f'{path}.{key}', old_present=key in old, fresh_present=key in fresh)
            else:
                yield from first_differences(old[key], fresh[key], f'{path}.{key}')
    elif isinstance(old, list):
        if len(old) != len(fresh):
            yield dict(path=path+'.length', old=len(old), fresh=len(fresh))
        for index, (a, b) in enumerate(zip(old, fresh)):
            yield from first_differences(a, b, f'{path}[{index}]')
    elif old != fresh:
        yield dict(path=path, old=old, fresh=fresh)


def controls(out, exe, sources):
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe)))
    save(out/'capacity-copies.json', capacity_copies())
    capacity = out/'capacity';capacity.mkdir()
    job([str(exe), FILTER, '--nocapture', '--test-threads=1'], fields(), capacity, wall=120, cpu=600, gib=4)
    check_job(capacity, 3)
    assert ref(OLD_SCREEN)['sha256'] == OLD_SCREEN_HASH
    retained = out/'retained';retained.mkdir()
    env = fields();env.update(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2',
                              STREHL_GPU_GATHER_LOG='off', STREHL_SHARED_SOURCE_FIELD_OUT=str(retained/'output'))
    job([str(exe), RETAINED_FILTER, '--nocapture', '--test-threads=1'], env, retained, wall=180, cpu=900, gib=4)
    check_job(retained, 2)
    old, fresh = read(OLD_SCREEN), read(retained/'output/screen.json')
    unchanged_screen = fresh == old
    shutil.copyfile(OLD_SCREEN, out/'historical-screen.json')
    from itertools import islice
    save(out/'screen-comparison.json', dict(exact=unchanged_screen,
        historical_screen=ref(out/'historical-screen.json'), fresh_screen=ref(retained/'output/screen.json'),
        first_differences=list(islice(first_differences(old, fresh), 20)),
        difference_limit=20, disposition='RETAINED' if unchanged_screen else 'STOP_FOR_ROOT_REVIEW',
        explanation='Core numeric drift can change the old screen; it is recorded and refused, never silently waived.'))
    g.unchanged(sources)
    save(out/'completion.json', dict(instrument_completed=True, capacity_controls_executed=3,
        retained_controls_executed=2, capacity_passed=True, retained_screen_exact=unchanged_screen,
        prior_screen=ref(OLD_SCREEN), current_screen=ref(retained/'output/screen.json'),
        screen_comparison=ref(out/'screen-comparison.json'),
        photographic_replay_admitted=fresh['photographic_replay_admitted'],
        legacy_general_qualification=False, sources_unchanged=True, scope=SCOPE))
    assert unchanged_screen and fresh['photographic_replay_admitted'] is False, 'Old screen changed; saved all new results and refuse pending root review.'


def screen_binding(path, exe, sources):
    assert read(path/'bindings.json') == dict(sources=sources, executable=ref(exe))
    completion = read(path/'completion.json')
    assert completion['instrument_completed'] and completion['capacity_passed'] and completion['sources_unchanged']
    assert completion['capacity_controls_executed'] == 3 and completion['retained_controls_executed'] == 2
    check_job(path/'capacity', 3);check_job(path/'retained', 2)
    assert completion['retained_screen_exact'] and completion['photographic_replay_admitted'] is False
    assert completion['prior_screen'] == ref(OLD_SCREEN) and ref(OLD_SCREEN)['sha256'] == OLD_SCREEN_HASH
    assert completion['current_screen'] == ref(path/'retained/output/screen.json')
    assert completion['screen_comparison'] == ref(path/'screen-comparison.json')
    comparison = read(path/'screen-comparison.json')
    assert comparison['exact'] and not comparison['first_differences'] and comparison['disposition'] == 'RETAINED'
    assert comparison['historical_screen'] == ref(path/'historical-screen.json')
    assert ref(path/'historical-screen.json')['sha256'] == OLD_SCREEN_HASH
    assert comparison['fresh_screen'] == ref(path/'retained/output/screen.json')
    assert read(path/'retained/output/screen.json') == read(OLD_SCREEN)
    return ref(path/'completion.json')


def image(path):
    import numpy as np
    import tifffile
    with tifffile.TiffFile(path) as file:
        rgb = file.asarray()
        icc = bytes(file.pages[0].tags[34675].value)
        assert len(file.pages) == 1 and rgb.dtype == np.uint16 and rgb.shape == (4332, 6500, 3) and icc
    digest = hashlib.sha256(rgb.astype('<u2', copy=False).tobytes()).hexdigest()
    return rgb, icc, digest


def recipe(out):
    baseline_bindings = [ref(BASELINE/name) for name in s.PINNED]
    assert all(row['sha256'] == s.PINNED[Path(row['path']).name] for row in baseline_bindings)
    delivered, invocation = read(BASELINE/'completion.json'), read(BASELINE/'invocation.json')
    assert delivered['frames'] == invocation['frames'] == 299
    assert delivered['native_dimensions'] == [6500, 4332] and delivered['crop_quad_xywh'] == [133, 89, 3250, 2166]
    assert ref(Path(delivered['master']['path'])) == delivered['master']
    assert ref(Path(delivered['warp_map']['path'])) == delivered['warp_map'] == invocation['existing_map']
    ordered = read(BASELINE/'input-order.json')
    assert [row['index'] for row in ordered] == list(range(299))
    assert len({row['path'] for row in ordered}) == 299
    for row in ordered:
        path = Path(row['path'])
        stat = path.stat()
        assert path.is_absolute() and (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    inputs = [dict(index=row['index'], path=row['path'], identity_name=Path(row['path']).name,
                   bytes=row['bytes'], sha256=row['sha256']) for row in ordered]
    pixels, icc, digest = image(Path(delivered['master']['path']))
    del pixels
    config = dict(schema=1, phase='full', mode='shared-source-field', stack_name='uncapped-IC-chip-cpl', inputs=inputs,
        warp_map=delivered['warp_map']['path'], warp_map_sha256=delivered['warp_map']['sha256'],
        out_dir=str(out/'output'), expected_reference=149, expected_full_geometry=[3516, 2344],
        expected_crop=[133, 89, 3250, 2166], expected_baseline=delivered['master']['path'],
        expected_baseline_sha256=delivered['master']['sha256'], expected_baseline_pixels_sha256=digest,
        expected_camera='ILCE-7CM2', expected_iso=100., exposure_stops=0.,
        tone_policy='automatic-baseline-then-exact-pinned-candidate')
    return config, baseline_bindings, ordered


def validate(run):
    import numpy as np
    config, data = read(run/'config.json'), read(run/'output/receipt.json')
    assert data['phase'] == 'full' and data['mode'] == 'shared-source-field'
    assert data['source_count'] == data['probe_source_count'] == 299
    assert [row['index'] for row in data['frames']] == list(range(299))
    assert data['crop'] == [133, 89, 3250, 2166] and data['native_dimensions'] == [6500, 4332]
    assert data['map_sha256'] == config['warp_map_sha256'] and data['threads'] == 8
    assert data['replay_exact'] and data['original_metadata_unchanged']
    assert data['scalar_pair_bytes'] == 16838484000 and data['source_image_volume'] is False
    assert data['coverage_max_abs_error'] <= 8e-6
    assert data['terminal_base'] == 'unchanged baseline mean' and data['input_hull'] == 'unchanged baseline hull'
    assert data['generated_photographic_replay_admitted'] is False
    assert data['actual_tone_pinned'] and data['baseline_pinned_rewrite_exact']
    assert data['tone_policy'] == config['tone_policy'] == 'automatic-baseline-then-exact-pinned-candidate'
    assert all(row['replay_exact'] and row['source_unchanged'] and len(row['known4_sha256']) == 4 and
               isinstance(row['membership_sha256'], str) and len(row['membership_sha256']) == 64 for row in data['frames'])
    expected, expected_icc, expected_hash = image(Path(config['expected_baseline']))
    assert ref(Path(config['expected_baseline']))['sha256'] == config['expected_baseline_sha256']
    assert expected_hash == config['expected_baseline_pixels_sha256'] == data['baseline_rgb16_le_sha256']
    for arm in ('baseline', 'candidate'):
        path = run/'output'/(arm+'.tiff')
        pixels, icc, digest = image(path)
        assert ref(path)['sha256'] == data[arm+'_sha256'] and digest == data[arm+'_rgb16_le_sha256']
        assert icc == expected_icc
        if arm == 'baseline':
            assert np.array_equal(pixels, expected)
        del pixels
        cache_path = run/'output'/(arm+'-cache.json')
        cache = read(cache_path)
        assert str(cache_path) == data[arm+'_cache']['path'] and ref(cache_path)['sha256'] == data[arm+'_cache']['sha256']
        assert cache['phase'] == 'full' and cache['frames'] == 299 and cache['reference'] == 149 and cache['arm'] == arm
        assert cache['crop'] == config['expected_crop'] and cache['map_sha256'] == config['warp_map_sha256']
        assert cache['tone_policy'] == config['tone_policy']
        binary = run/'output'/cache['binary']
        assert binary.parent == (run/'output') and ref(binary)['sha256'] == cache['binary_sha256'] == data[arm+'_cache']['binary_sha256']
        plane_bytes = 3250*2166*4
        assert binary.stat().st_size == cache['binary_bytes'] == 4*plane_bytes
        plane_hashes = []
        with binary.open('rb') as stream:
            for _ in range(4):
                remaining, h = plane_bytes, hashlib.sha256()
                while remaining:
                    block = stream.read(min(1<<20, remaining))
                    assert block
                    h.update(block)
                    remaining -= len(block)
                plane_hashes.append(h.hexdigest())
            assert not stream.read(1)
        assert plane_hashes == cache['plane_sha256'] == data[arm+'_planes_sha256']
    del expected
    pinned, pinned_icc, pinned_hash = image(run/'output/baseline-pinned-rewrite.tiff')
    assert pinned_icc == expected_icc and pinned_hash == expected_hash
    del pinned
    return data


def full(out, exe, sources, controls_path):
    screen = screen_binding(controls_path, exe, sources)
    out.mkdir(exist_ok=False)
    config, baseline_bindings, ordered = recipe(out)
    save(out/'config.json', config)
    save(out/'input-order.json', ordered)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe), screen=screen,
        baseline=baseline_bindings, config=ref(out/'config.json'), targets=ref(TARGETS),
        root_authorized_observation=True, scope=SCOPE))
    env = fields()
    env.update(STREHL_WARPMAP=config['warp_map'], STREHL_CHIP_SHARED_SOURCE_CONFIG=str(out/'config.json'))
    job([str(exe), FULL, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
        wall=1800, cpu=12000, gib=32)
    assert re.findall(r'test result: ok\. (\d+) passed;', (out/'process.log').read_text()) == ['1']
    g.unchanged(sources)
    for row in baseline_bindings:
        assert ref(Path(row['path'])) == row
    for row in ordered:
        stat = Path(row['path']).stat()
        assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    assert ref(Path(config['warp_map']))['sha256'] == config['warp_map_sha256']
    data = validate(out)
    changed = data['candidate_rgb16_le_sha256'] != data['baseline_rgb16_le_sha256']
    save(out/'completion.json', dict(status='COMPLETE_AWAITING_INDEPENDENT_PHOTOGRAPHIC_REVIEW',
        phase='full', source_count=299, reference=149, sources_unchanged=True,
        baseline_current_production_pixels_and_icc_exact=True, actual_tone_pinned=True,
        candidate_pixels_changed=changed, original_metadata_unchanged=True,
        receipt=ref(out/'output/receipt.json'), process=ref(out/'process.json'),
        generated_general_qualification=read(controls_path/'completion.json')['legacy_general_qualification'],
        photographic_replay_admitted=False, visual_verdict=None, scope=SCOPE))


def views(run, out):
    import numpy as np
    from PIL import Image
    completion = read(run/'completion.json')
    assert completion['phase'] == 'full' and completion['baseline_current_production_pixels_and_icc_exact']
    assert completion['receipt'] == ref(run/'output/receipt.json') and completion['process'] == ref(run/'process.json')
    process = read(run/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    assert ref(TARGETS) == read(run/'bindings.json')['targets']
    data = validate(run)
    targets = read(TARGETS)
    assert targets['native_size'] == [6500, 4332] and targets['crop'] == [133, 89, 3250, 2166]
    assert len(targets['regions']) == 7
    out.mkdir(exist_ok=False)
    tiles, complete = [], []
    for arm in ('baseline', 'candidate'):
        path = run/'output'/(arm+'.tiff')
        rgb, icc, digest = image(path)
        assert digest == data[arm+'_rgb16_le_sha256']
        canvas = Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
        full_path = out/(arm+'-full.jpg')
        canvas.save(full_path, quality=98, subsampling=0, icc_profile=icc)
        overview = canvas.copy()
        overview.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        whole_path = out/(arm+'-overview.png')
        overview.save(whole_path, icc_profile=icc)
        for target in targets['regions']:
            x, y, w, h = target['native_xywh']
            assert 0 <= x < x+w <= 6500 and 0 <= y < y+h <= 4332 and (w, h) in ((384, 384), (512, 512))
            edge = 384 if w == 384 else 256
            for yy in range(y, y+h, edge):
                for xx in range(x, x+w, edge):
                    tile = out/f"{arm}-{target['name']}-{xx}-{yy}.png"
                    canvas.crop((xx, yy, xx+edge, yy+edge)).save(tile, icc_profile=icc)
                    tiles.append(dict(arm=arm, region=target['name'], native_xywh=[xx, yy, edge, edge], file=ref(tile)))
        complete.append(dict(arm=arm, master=ref(path), full_jpeg=ref(full_path), overview=ref(whole_path),
                             native_dimensions=[6500, 4332], icc_sha256=hashlib.sha256(icc).hexdigest()))
        del rgb, canvas, overview
    assert len(tiles) == 50
    save(out/'completion.json', dict(full_images=complete, native_tiles=tiles, targets=ref(TARGETS),
        run_completion=ref(run/'completion.json'), native_size=[6500, 4332], crop=[133, 89, 3250, 2166],
        conversion='Identical (RGB16+128)//257 with retained ICC; native tiles never resampled.',
        visual_verdict=None, scope=SCOPE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build', 'controls', 'full', 'views'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--controls', type=Path)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--execute-approved-observation', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    if args.phase == 'build':
        build(out)
    elif args.phase == 'views':
        assert args.run is not None
        views(args.run.resolve(), out)
    else:
        assert args.build is not None
        exe, sources = shared_build(args.build.resolve())
        if args.phase == 'controls':
            controls(out, exe, sources)
        else:
            assert args.controls is not None and args.execute_approved_observation, 'Root must decide the harmonic contingency before full execution.'
            full(out, exe, sources, args.controls.resolve())


if __name__ == '__main__':
    main()
