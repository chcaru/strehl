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


g = load('band_agreement_existing_bounds', ROOT/'experiments/cross-scale-source-prior/run.py')
c = g.c
s = load('band_agreement_fixed_chip', ROOT/'experiments/chip-stock-selectivity/run.py')
read, save, ref = g.read, c.save, c.ref
FILTER = 'merge_cmd::band_source_agreement::independent_controls::'
FULL = 'merge_cmd::band_source_agreement_full::complete_pair'
REQUIRED = ('run.py', 'operator.rs', 'implementation.rs', 'core-bridge.rs', 'full-adapter.rs',
            'design.md', 'independent-controls.rs', 'independent-plan.md')
SCOPE = ('One complete fixed same-band source-agreement chip observation. Generated quality negatives '
         'remain explicit; mechanical safety is not general quality qualification or a default change.')


def bindings():
    # Reuse the complete current include/source inventory, not an old binary's
    # validation receipt. The inherited inventory scans sources only.
    paths = {Path(row['path']) for row in g.bindings()}
    assert all((HERE/name).is_file() for name in REQUIRED), 'Authors must freeze all sources before build.'
    paths.update(HERE/name for name in REQUIRED)
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
    sources = read(path/'sources.json')
    g.unchanged(sources)
    assert {str((HERE/name).resolve()) for name in REQUIRED} <= {row['path'] for row in sources}
    exe = path/'cli-tests.exe'
    assert ref(exe) == read(path/'executables.json')['cli-tests']
    log = (path/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
    return exe, sources


def controls(out, exe, sources):
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe)))
    env = fields()
    env['STREHL_BAND_SOURCE_AGREEMENT_OUT'] = str(out/'output')
    job([str(exe), FILTER, '--nocapture', '--test-threads=1'], env, out, wall=180, cpu=900, gib=4)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['4']
    assert 'BAND_SOURCE_AGREEMENT ' in log
    screen = read(out/'output/screen.json')
    assert screen['status'] == 'SCREEN_COMPLETE' and len(screen['cases']) == 12
    assert screen['metric_commission']['passed'] and screen['photographic_replay_admitted'] is False
    assert screen['root_review_required'] is True
    assert type(screen['observation_safety_pass']) is bool and type(screen['legacy_general_qualification']) is bool
    g.unchanged(sources)
    assert ref(exe) == read(out/'bindings.json')['executable']
    save(out/'completion.json', dict(instrument_completed=True, controls_executed=4,
        mechanical_safety_pass=screen['observation_safety_pass'],
        legacy_general_qualification=screen['legacy_general_qualification'],
        photographic_replay_admitted=False, root_review_required=True, sources_unchanged=True,
        screen=ref(out/'output/screen.json'), process=ref(out/'process.json'), scope=SCOPE))


def screen_binding(path, exe, sources):
    assert read(path/'bindings.json') == dict(sources=sources, executable=ref(exe))
    completion = read(path/'completion.json')
    process = read(path/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
    assert completion['process'] == ref(path/'process.json') and completion['screen'] == ref(path/'output/screen.json')
    assert completion['instrument_completed'] and completion['controls_executed'] == 4 and completion['sources_unchanged']
    assert completion['mechanical_safety_pass'], 'Generated preservation/destroyer screen failed; full observation refused.'
    screen = read(path/'output/screen.json')
    assert screen['observation_safety_pass'] and screen['photographic_replay_admitted'] is False
    assert completion['legacy_general_qualification'] == screen['legacy_general_qualification']
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
    config = dict(schema=1, phase='full', mode='agreement', stack_name='uncapped-IC-chip-cpl', inputs=inputs,
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
    assert data['phase'] == 'full' and data['mode'] == 'agreement'
    assert data['source_count'] == data['agreement_source_count'] == data['probe_source_count'] == 299
    assert [row['index'] for row in data['frames']] == list(range(299))
    assert data['crop'] == [133, 89, 3250, 2166] and data['native_dimensions'] == [6500, 4332]
    assert data['map_sha256'] == config['warp_map_sha256'] and data['threads'] == 8
    assert data['held_state_bit_exact'] and data['replay_exact'] and data['original_metadata_unchanged']
    assert data['generated_photographic_replay_admitted'] is False
    assert data['actual_tone_pinned'] and data['baseline_pinned_rewrite_exact']
    assert data['tone_policy'] == config['tone_policy'] == 'automatic-baseline-then-exact-pinned-candidate'
    assert all(row['replay_exact'] and row['held_state_bit_exact'] and row['source_unchanged'] and
               row['canonical_weight_sha256'][0] == row['candidate_weight_sha256'][0] for row in data['frames'])
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
    env.update(STREHL_WARPMAP=config['warp_map'], STREHL_BAND_SOURCE_AGREEMENT_CONFIG=str(out/'config.json'))
    job([str(exe), FULL, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
        wall=1800, cpu=12000, gib=24)
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
            assert args.controls is not None
            full(out, exe, sources, args.controls.resolve())


if __name__ == '__main__':
    main()
