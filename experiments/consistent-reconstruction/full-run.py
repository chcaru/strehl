"""One explicitly authorized complete chip observation; preserves the failed screen."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gen = load('consistent_generated_runner', HERE/'run.py')
shared = load('consistent_chip_recipe', ROOT/'experiments/chip-shared-source-observation/run.py')
band, g, c = gen.band, gen.g, gen.c
read, save, ref = gen.read, gen.save, gen.ref
TARGETS = shared.TARGETS
OLD_SCREEN = HERE/'controls-1/output/screen.json'
OLD_SHA = '63ea41b7eb9be8bc6e8e4450c0649fddff87865773fdd69f76a1844203c59ac0'
FULL = 'merge_cmd::consistent_reconstruction_full::complete_pair'
SCOPE = ('One separately authorized complete chip observation of unchanged reconstruction. '
         'Generated glint and coarse-detail harms remain; no general qualification or default promotion.')

# Reuse the frozen generated build/control functions without editing that file.
# Every extra dependency is included BEFORE compilation and required again at use.
generated_required_paths = gen.required_paths


def required_paths():
    paths = generated_required_paths()
    paths.update((HERE/'full-run.py', HERE/'full-adapter.rs', HERE/'full-plan.md',
                  Path(shared.__file__).resolve(), TARGETS, shared.s.RETAINED,
                  Path(shared.s.__file__).resolve()))
    assert all(path.is_file() for path in paths)
    assert '/../../experiments/consistent-reconstruction/full-adapter.rs' in (
        ROOT/'crates/strehl-cli/src/merge_cmd.rs').read_text(encoding='utf-8')
    return paths


gen.required_paths = required_paths


def controls(out, build_dir):
    gen.controls(out, build_dir)
    assert ref(OLD_SCREEN)['sha256'] == OLD_SHA
    current = out/'output/screen.json'
    exact = current.read_bytes() == OLD_SCREEN.read_bytes()
    save(out/'historical-comparison.json', dict(exact=exact,
        historical=ref(OLD_SCREEN), current=ref(current),
        disposition='RETAINED' if exact else 'STOP_FOR_ROOT_REVIEW', scope=SCOPE))
    assert exact, 'Generated result changed; preserve both and stop before RAW.'


def bindings(build_dir, control_dir):
    sources = read(build_dir/'sources.json')
    g.unchanged(sources)
    recorded = {row['path']: row for row in sources}
    for path in required_paths():
        current = ref(path.resolve())
        assert recorded.get(current['path']) == current
    exe = (build_dir/'cli-tests.exe').resolve()
    assert ref(exe) == read(build_dir/'executables.json')['cli-tests']
    built = read(build_dir/'process.json')
    assert built['exit_code'] == 0 and built['error'] is None and built['terminal_job_accounting'] and not built['cleanup_errors']
    control = read(control_dir/'completion.json')
    assert control['instrument_completed'] and control['sources_unchanged']
    assert control['controls_executed'] == 4 and control['cases_executed'] == 12
    assert control['numerical_pass'] and control['contact_positive']
    assert not control['preservation_pass'] and not control['candidate_qualified']
    assert control['photographic_replay_admitted'] is False
    assert control['screen'] == ref(control_dir/'output/screen.json')
    assert control['process'] == ref(control_dir/'process.json')
    process = read(control_dir/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting'] and not process['cleanup_errors']
    cb = read(control_dir/'bindings.json')
    assert cb['sources'] == sources and cb['executable'] == ref(exe)
    compare = read(control_dir/'historical-comparison.json')
    assert compare['exact'] and compare['current'] == control['screen']
    assert compare['historical'] == ref(OLD_SCREEN) and ref(OLD_SCREEN)['sha256'] == OLD_SHA
    return exe, sources


def validate(run):
    import numpy as np
    output = run/'output'
    data, config = read(output/'receipt.json'), read(run/'config.json')
    process = read(run/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    assert data['schema'] == 1 and data['phase'] == 'full' and data['mode'] == 'consistent-reconstruction'
    assert data['source_count'] == data['probe_source_count'] == 299 and data['canonical_passes'] == 1
    assert data['crop'] == [133, 89, 3250, 2166] and data['native_dimensions'] == [6500, 4332]
    assert data['threads'] == 8 and data['map_sha256'] == config['warp_map_sha256']
    assert data['tone_policy'] == 'automatic-baseline-then-exact-pinned-candidate'
    for key in ('held_state_bit_exact', 'observer_on_off_tiff_byte_exact', 'actual_tone_pinned',
                'baseline_pinned_rewrite_exact', 'original_metadata_unchanged', 'root_observation_authorized'):
        assert data[key] is True, key
    for key in ('generated_candidate_qualified', 'generated_preservation_pass',
                'generated_photographic_replay_admitted', 'general_promotion'):
        assert data[key] is False, key
    assert data['all_colour_site_support_checks'] == [True]*299
    assert data['frames'] == read(output/'source-evidence.json')
    assert [row['index'] for row in data['frames']] == list(range(299))
    assert all(row['source_unchanged'] for row in data['frames'])
    for prefix in ('accumulator', 'hull'):
        assert data[prefix+'_before_sha256'] == data[prefix+'_after_sha256']
    targets = data['canonical_coefficients_sha256']
    assert len(targets) == 4 and all(len(row) == 8 for row in targets)
    assert data['coefficients_after_sha256'] == targets
    meta = data['cache_metadata']
    assert meta['frames'] == 299 and meta['reference'] == 149
    assert meta['full_geometry'] == [3516, 2344] and meta['crop'] == data['crop']
    assert meta['plane_order'] == ['R', 'G1', 'G2', 'B'] and meta['map_sha256'] == data['map_sha256']

    # Check saved coefficient extents against actual bytes, never just a receipt.
    cc = data['coefficient_cache']
    cc_path = output/'canonical-coefficients.json'
    assert Path(cc['path']).resolve() == cc_path.resolve() and ref(cc_path)['sha256'] == cc['sha256']
    cm = read(cc_path)
    binary = output/'canonical-coefficients.f32'
    assert cm['binary'] == binary.name and cm['metadata'] == meta
    assert cm['encoding'] == 'little-endian-f32' and cm['target_sha256'] == targets
    assert cm['plane_order'] == meta['plane_order']
    assert binary.stat().st_size == cm['binary_bytes'] == cc['binary_bytes']
    assert ref(binary)['sha256'] == cm['binary_sha256'] == cc['binary_sha256']
    sizes, w, h = [], 3250, 2166
    for _ in range(8):
        sizes.append([w, h]); w, h = (w+1)//2, (h+1)//2
    assert len(cm['layout']) == 32
    offset = 0
    with binary.open('rb') as stream:
        for i, row in enumerate(cm['layout']):
            plane, level = divmod(i, 8)
            size = sizes[level]
            assert row['plane'] == plane and row['level'] == level and row['size'] == size
            count = size[0]*size[1]*4
            assert row['offset_bytes'] == offset and row['bytes'] == count
            raw = stream.read(count)
            assert len(raw) == count and hashlib.sha256(raw).hexdigest() == row['sha256'] == targets[plane][level]
            assert np.isfinite(np.frombuffer(raw, dtype='<f4')).all()
            offset += count
        assert stream.read(1) == b'' and offset == cm['binary_bytes']

    solver = read(output/'solver-results.json')
    assert solver['max_iterations'] == 32 and abs(solver['error_rms_limit_dn']-.02) < 1e-9
    assert solver['preconditioner'] == 'S S-transpose' and solver['solves'] == data['solves']
    assert len(data['solves']) == 4 and len(data['baseline_pre_hull_sha256']) == 4
    assert len(data['candidate_pre_hull_sha256']) == len(data['pre_hull_delta_l2']) == 4
    for i, solve in enumerate(data['solves']):
        assert solve == read(output/f'solve-plane-{i}.json') and solve['plane'] == i
        if solve['admitted']:
            assert solve['converged'] and solve['refusal'] is None and 0 <= solve['iterations'] <= 32
            for name in ('error_bound_rms', 'relative_residual', 'initial_objective', 'objective',
                         'correction_rhs_norm', 'correction_residual_norm', 'correction_objective', 'final_rounding_bound'):
                assert math.isfinite(solve[name]) and solve[name] >= 0, name
            assert solve['error_bound_rms'] <= .02 and solve['objective'] <= solve['initial_objective']
            assert data['candidate_pre_hull_sha256'][i] == solve['last_iterate_sha256']
            assert math.isfinite(data['pre_hull_delta_l2'][i]) and data['pre_hull_delta_l2'][i] >= 0
        else:
            assert not solve['converged'] or solve['refusal'] is not None
            assert data['candidate_pre_hull_sha256'][i] is None and data['pre_hull_delta_l2'][i] is None
    valid = all(row['admitted'] for row in data['solves'])
    assert data['candidate_valid'] == solver['candidate_valid'] == valid
    assert data['numerical_refusal'] == (not valid)
    assert data['status'] == ('OBSERVATION_COMPLETE' if valid else 'NUMERICAL_REFUSAL')

    rgb, expected_icc, expected_digest = shared.image(Path(config['expected_baseline']))
    del rgb
    assert ref(Path(config['expected_baseline']))['sha256'] == config['expected_baseline_sha256']
    assert expected_digest == config['expected_baseline_pixels_sha256'] == data['baseline_rgb16_le_sha256']
    for arm in ('baseline', 'candidate') if valid else ('baseline',):
        path = output/(arm+'.tiff')
        assert ref(path)['sha256'] == data[arm+'_sha256']
        rgb, icc, digest = shared.image(path)
        del rgb
        assert icc == expected_icc and digest == data[arm+'_rgb16_le_sha256']
        cache_path = output/(arm+'-cache.json')
        cache_ref = data[arm+'_cache']
        assert Path(cache_ref['path']).resolve() == cache_path.resolve()
        assert ref(cache_path)['sha256'] == cache_ref['sha256']
        cache = read(cache_path)
        mutable = {'binary', 'binary_bytes', 'binary_sha256', 'plane_sha256', 'arm'}
        assert {k:v for k,v in cache.items() if k not in mutable} == {k:v for k,v in meta.items() if k not in mutable}
        assert cache['arm'] == arm and cache['binary'] == arm+'-planes.f32'
        raw_path = output/cache['binary']
        assert raw_path.stat().st_size == cache['binary_bytes'] == 4*3250*2166*4
        assert ref(raw_path)['sha256'] == cache['binary_sha256'] == cache_ref['binary_sha256']
        assert cache['plane_sha256'] == data[arm+'_planes_sha256'] and len(cache['plane_sha256']) == 4
        with raw_path.open('rb') as stream:
            for digest in cache['plane_sha256']:
                raw = stream.read(3250*2166*4)
                assert hashlib.sha256(raw).hexdigest() == digest
                assert np.isfinite(np.frombuffer(raw, dtype='<f4')).all()
    if not valid:
        assert all(not (output/name).exists() for name in ('candidate.tiff', 'candidate-cache.json', 'candidate-planes.f32'))
        assert all(data[key] is None for key in ('candidate_cache', 'candidate_sha256', 'candidate_rgb16_le_sha256',
                                               'candidate_planes_sha256', 'final_delta_l2'))
    placebo = read(output/'observer-placebo.json')
    assert placebo['whole_tiff_byte_exact'] and placebo['actual_finish_planes_exact']
    assert placebo['coefficient_cache'] == cc
    for arm, name in (('off', 'baseline-pinned-rewrite.tiff'), ('on', 'baseline-observer-on.tiff')):
        path = output/name
        assert Path(data['observer_'+arm+'_path']).resolve() == path.resolve() == Path(placebo[arm+'_path']).resolve()
        assert ref(path)['sha256'] == data['observer_'+arm+'_sha256'] == placebo[arm+'_sha256']
    assert placebo['off_sha256'] == placebo['on_sha256']
    rgb, icc, digest = shared.image(output/'baseline-pinned-rewrite.tiff')
    del rgb
    assert icc == expected_icc and digest == expected_digest
    return data


def full(out, build_dir, control_dir):
    exe, sources = bindings(build_dir, control_dir)
    out.mkdir(exist_ok=False)
    config, baseline_bindings, ordered = shared.recipe(out)
    config['mode'] = 'consistent-reconstruction'
    save(out/'config.json', config)
    save(out/'input-order.json', ordered)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe),
        screen=ref(control_dir/'completion.json'), historical_comparison=ref(control_dir/'historical-comparison.json'),
        baseline=baseline_bindings, config=ref(out/'config.json'), targets=ref(TARGETS),
        root_authorized_observation=True, scope=SCOPE))
    env = band.fields()
    env.update(STREHL_WARPMAP=config['warp_map'], STREHL_CONSISTENT_RECONSTRUCTION_CONFIG=str(out/'config.json'))
    band.job([str(exe), FULL, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
             wall=1800, cpu=12000, gib=16)
    assert re.findall(r'test result: ok\. (\d+) passed;', (out/'process.log').read_text()) == ['1']
    g.unchanged(sources)
    for row in baseline_bindings:
        assert ref(Path(row['path'])) == row
    for row in ordered:
        stat = Path(row['path']).stat()
        assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    assert ref(Path(config['warp_map']))['sha256'] == config['warp_map_sha256']
    data = validate(out)
    save(out/'completion.json', dict(status=data['status'], phase='full', source_count=299, reference=149,
        sources_unchanged=True, baseline_current_production_pixels_and_icc_exact=True,
        actual_tone_pinned=True, original_metadata_unchanged=True,
        receipt=ref(out/'output/receipt.json'), process=ref(out/'process.json'),
        candidate_valid=data['candidate_valid'], generated_general_qualification=False,
        photographic_replay_admitted=False, visual_verdict=None, scope=SCOPE))


def views(run, out):
    import numpy as np
    from PIL import Image
    done = read(run/'completion.json')
    assert done['candidate_valid'] and done['baseline_current_production_pixels_and_icc_exact']
    assert done['receipt'] == ref(run/'output/receipt.json') and done['process'] == ref(run/'process.json')
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
        rgb, icc, digest = shared.image(path)
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
            assert 0 <= x < x+w <= 6500 and 0 <= y < y+h <= 4332
            assert (w, h) in ((384, 384), (512, 512))
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
        gen.build(out)
    elif args.phase == 'controls':
        assert args.build is not None
        controls(out, args.build.resolve())
    elif args.phase == 'views':
        assert args.run is not None
        views(args.run.resolve(), out)
    else:
        assert args.build is not None and args.controls is not None and args.execute_approved_observation
        full(out, args.build.resolve(), args.controls.resolve())


if __name__ == '__main__':
    main()
