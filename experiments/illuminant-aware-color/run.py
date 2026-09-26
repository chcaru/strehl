"""Bounded two-capture matrix comparison from retained complete CFA caches."""
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


gen = load('illuminant_existing_build', ROOT/'experiments/consistent-reconstruction/run.py')
band, g, c = gen.band, gen.g, gen.c
read, save, ref = gen.read, gen.save, gen.ref
FILTER = 'merge_cmd::illuminant_aware_color::independent_controls::'
TEST_NAMES = ('independent_d65_equivalence_controls', 'independent_warm_colour_controls',
              'independent_interpolation_controls', 'independent_metadata_refusal_controls')
ENV = 'STREHL_ILLUMINANT_AWARE_COLOR_CONFIG'
CAPTURES = (
    ('opal103', 'experiments/opal-headroom/cache-1', 'baseline', [6792, 4528]),
    ('marigold4', 'experiments/garnet-spatial-trace/marigold4-fixed-1', 'candidate', [6268, 4176]),
)
SCOPE = 'Fixed 3000K matrix intervention; no spatial ghosting/glare recovery or absolute photographic colour accuracy claim.'
OLD_REQUIRED = gen.required_paths


def required_paths():
    paths = OLD_REQUIRED()
    paths.update(HERE/name for name in ('run.py', 'design.md', 'operator.rs', 'implementation.rs',
                                      'independent-controls.rs', 'independent-plan.md', 'targets.json'))
    paths.add(ROOT/'experiments/quality-september25/next-after-reconstruction.md')
    assert all(path.is_file() for path in paths)
    assert '/../../experiments/illuminant-aware-color/implementation.rs' in (
        ROOT/'crates/strehl-cli/src/merge_cmd.rs').read_text(encoding='utf-8')
    return paths


gen.required_paths = required_paths


def good_process(folder, count=None):
    process = read(folder/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    if count is not None:
        assert re.findall(r'test result: ok\. (\d+) passed;', (folder/'process.log').read_text()) == [str(count)]
    return process


def build_binding(build_dir):
    good_process(build_dir)
    assert 'Compiling strehl-cli' in (build_dir/'process.log').read_text(encoding='utf-8', errors='replace')
    sources = read(build_dir/'sources.json')
    g.unchanged(sources)
    recorded = {row['path']:row for row in sources}
    for path in required_paths():
        row = ref(path.resolve())
        assert recorded[row['path']] == row
    exe = (build_dir/'cli-tests.exe').resolve()
    assert ref(exe) == read(build_dir/'executables.json')['cli-tests']
    return exe, sources


def controls(out, build_dir):
    exe, sources = build_binding(build_dir)
    names = re.findall(r'#\[test\]\s*fn\s+(\w+)', (HERE/'independent-controls.rs').read_text())
    assert len(names) == 4 and set(names) == set(TEST_NAMES)
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe)))
    band.job([str(exe), FILTER, '--nocapture', '--test-threads=1'], band.fields(), out,
             wall=120, cpu=600, gib=4)
    good_process(out, 4)
    log = (out/'process.log').read_text()
    assert all(FILTER+name in log for name in names)
    flat = re.findall(r'ILLUMINANT_FLAT (\{[^\n]+\})', log)
    assert len(flat) == 1
    save(out/'flat-propagation.json', json.loads(flat[0]))
    g.unchanged(sources)
    save(out/'completion.json', dict(instrument_completed=True, tests=names, count=4,
        sources_unchanged=True, process=ref(out/'process.json'), scope=SCOPE))


def image(path, dimensions):
    import numpy as np
    import tifffile
    with tifffile.TiffFile(path) as file:
        rgb = file.asarray()
        icc = bytes(file.pages[0].tags[34675].value)
        assert len(file.pages) == 1 and rgb.dtype == np.uint16
        assert rgb.shape == (dimensions[1], dimensions[0], 3) and icc
    return rgb, icc, hashlib.sha256(rgb.astype('<u2', copy=False).tobytes()).hexdigest()


def recipe(out):
    captures, bindings = [], []
    for name, parent, arm, native in CAPTURES:
        directory = ROOT/parent
        retained = read(directory/'config.json')
        source = retained['inputs'][0]
        cache = directory/'output'/f'{arm}-cache.json'
        baseline = directory/'output'/f'{arm}.tiff'
        metadata = read(cache)
        assert metadata['frames'] == (155 if name == 'opal103' else 488)
        assert metadata['crop'] == ([60,40,3396,2264] if name == 'opal103' else [191,128,3134,2088])
        assert [2*metadata['crop'][2], 2*metadata['crop'][3]] == native
        source_path = Path(source['path'])
        assert source_path.stat().st_size == source['bytes'] and ref(source_path)['sha256'] == source['sha256']
        pixels, icc, digest = image(baseline, native)
        del pixels
        binary = cache.parent/metadata['binary']
        assert ref(binary)['sha256'] == metadata['binary_sha256']
        captures.append(dict(name=name, source=str(source_path), source_bytes=source['bytes'],
            source_sha256=source['sha256'], cache=str(cache), cache_sha256=ref(cache)['sha256'],
            baseline=str(baseline), baseline_sha256=ref(baseline)['sha256'], baseline_pixels_sha256=digest))
        bindings.extend(ref(path.resolve()) for path in (directory/'config.json', cache, binary, baseline))
    return dict(schema=1, phase='metadata', shot_kelvin=3000.0, out_dir=str(out/'output'),
                captures=captures, metadata_receipt=None, metadata_receipt_sha256=None), bindings


def validate(run):
    import numpy as np
    good_process(run, 1)
    config = read(run/'config.json')
    binding = read(run/'bindings.json')
    assert binding['config'] == ref(run/'config.json')
    g.unchanged(binding['retained'])
    data = read(run/'output/receipt.json')
    assert data['schema'] == 1 and data['phase'] == config['phase']
    assert data['shot_kelvin'] == config['shot_kelvin'] == 3000.0
    assert data['temperature_is_declared_assumption'] is True
    assert data['physical_color_calibration_established'] is False
    assert len(data['captures']) == len(config['captures']) == 2
    if data['phase'] == 'metadata':
        assert data['source_count'] == 2 and data['original_metadata_unchanged']
        admitted = all(row['admitted'] for row in data['captures'])
        assert data['admitted'] == admitted
        assert data['status'] == ('METADATA_AVAILABLE' if admitted else 'METADATA_REFUSED')
    else:
        assert data['phase'] == 'cached' and data['status'] == 'COMPARISON_COMPLETE'
        assert data['source_reads'] == 0 and data['actual_tone_pinned']
        assert data['matrix_only_changed'] and data['cache_unchanged']
        assert data['photographic_quality_verdict'] is None
        meta_path = Path(config['metadata_receipt'])
        assert ref(meta_path)['sha256'] == config['metadata_receipt_sha256']
        original_metadata = read(meta_path)
        assert original_metadata['admitted'] and original_metadata['status'] == 'METADATA_AVAILABLE'
    for i, ((name, _, _, native), capture, row) in enumerate(zip(CAPTURES, config['captures'], data['captures'])):
        assert capture['name'] == name and row['input'] == capture
        cache_path = Path(capture['cache'])
        assert ref(cache_path)['sha256'] == capture['cache_sha256']
        cache = read(cache_path)
        assert cache['frames'] == (155 if name == 'opal103' else 488)
        binary = cache_path.parent/cache['binary']
        assert ref(binary)['sha256'] == cache['binary_sha256']
        assert binary.stat().st_size == cache['binary_bytes'] == native[0]*native[1]*4
        if data['phase'] == 'metadata':
            assert row == read(run/'output'/f'{name}-metadata.json')
            assert row['cache_wb_d65_exact'] and row['source_unchanged'] and row['iso'] == 100.0
            assert row['levels_bits'] == cache['levels_bits'] and len(row['active_u16_sha256']) == 64
            metadata = row['camera_metadata']
            assert metadata['camera'] == 'ILCE-7CM2'
            assert metadata['wb_gains_bits'] == cache['wb_gains_bits']
            assert metadata['selected_matrix_bits'] == cache['xyz_to_cam_bits']
            assert metadata['selected_source'] == cache['xyz_source'] == 'decoder color_matrix[D65]'
            if row['admitted']:
                assert row['refusal'] is None and row['selection'] is not None
                labels = [m['name'] for m in metadata['matrices']]
                assert labels.count('A') == labels.count('D65') == 1
                for key, label in (('warm', 'A'), ('cool', 'D65')):
                    assert row['selection'][key] == next(m for m in metadata['matrices'] if m['name'] == label)
                assert (np.asarray(metadata['direct_matrix_bits'], dtype='<u4').view('<f4') == 0).all()
            else:
                assert row['selection'] is None and isinstance(row['refusal'], str) and row['refusal']
                continue
        else:
            assert row == read(run/'output'/f'{name}-receipt.json') and row['name'] == name
            assert row['native_dimensions'] == native
            assert row['matrix_only_changed'] and row['baseline_current_rgb16_icc_exact']
            assert row['baseline_pinned_rewrite_exact'] and row['cache_unchanged']
            assert original_metadata['captures'][i]['input'] == capture
            assert row['selection'] == original_metadata['captures'][i]['selection']
            expected = dict(row['baseline_resolved'])
            bits = np.asarray(row['selection']['transform']['matrix'], dtype='<f4').view('<u4').tolist()
            expected['matrix_bits'] = bits
            assert row['candidate_resolved'] == expected
            assert row['candidate_resolved']['matrix_bits'] != row['baseline_resolved']['matrix_bits']
            assert row['cache_plane_sha256'] == cache['plane_sha256']
            assert row['cache_binary_sha256'] == cache['binary_sha256']
            with binary.open('rb') as stream:
                for digest in cache['plane_sha256']:
                    raw = stream.read(native[0]*native[1])
                    assert hashlib.sha256(raw).hexdigest() == digest
                    assert np.isfinite(np.frombuffer(raw, dtype='<f4')).all()
                assert stream.read(1) == b''
            baseline = Path(capture['baseline'])
            assert ref(baseline)['sha256'] == capture['baseline_sha256']
            rgb, icc, digest = image(baseline, native); del rgb
            assert digest == capture['baseline_pixels_sha256'] == row['current_rgb16_le_sha256']
            for arm in ('current', 'pinned', 'candidate'):
                path = run/'output'/f'{name}-{arm}.tiff'
                assert Path(row[arm+'_path']).resolve() == path.resolve()
                assert ref(path)['sha256'] == row[arm+'_sha256']
                pixels, profile, actual = image(path, native); del pixels
                assert profile == icc
                assert actual == (digest if arm != 'candidate' else row['candidate_rgb16_le_sha256'])
        selection = row['selection']
        assert selection['shot_kelvin'] == 3000.0
        assert selection['warm_kelvin'] == 2856.0 and selection['cool_kelvin'] == 6504.0
        expected_fraction = (1/3000-1/6504)/(1/2856-1/6504)
        assert abs(selection['warm_fraction']-expected_fraction) < 1e-12
        transform = selection['transform']
        assert np.isfinite(np.asarray(transform['matrix'])).all()
        assert all(math.isfinite(v) and v > 0 for v in transform['source_white_xyz'])
        assert math.isfinite(transform['unnormalized_white_y']) and transform['unnormalized_white_y'] > 0
    return data


def execute(phase, out, build_dir, control_dir, metadata_dir):
    exe, sources = build_binding(build_dir)
    good_process(control_dir, 4)
    control = read(control_dir/'completion.json')
    assert control['instrument_completed'] and control['count'] == 4 and control['sources_unchanged']
    assert control['process'] == ref(control_dir/'process.json')
    assert read(control_dir/'bindings.json') == dict(sources=sources, executable=ref(exe))
    out.mkdir(exist_ok=False)
    if phase == 'cached':
        assert metadata_dir is not None
        metadata = validate(metadata_dir)
        assert metadata['phase'] == 'metadata' and metadata['admitted']
        config = read(metadata_dir/'config.json')
        retained = list(read(metadata_dir/'bindings.json')['retained'])
        retained.append(ref(metadata_dir/'config.json'))
        config['out_dir'] = str(out/'output')
        config['metadata_receipt'] = str(metadata_dir/'output/receipt.json')
        config['metadata_receipt_sha256'] = ref(Path(config['metadata_receipt']))['sha256']
        retained.append(ref(Path(config['metadata_receipt'])))
    else:
        config, retained = recipe(out)
    config['phase'] = phase
    save(out/'config.json', config)
    save(out/'bindings.json', dict(executable=ref(exe), sources=sources, retained=retained,
        controls=ref(control_dir/'completion.json'), config=ref(out/'config.json'), scope=SCOPE))
    env = band.fields(); env[ENV] = str(out/'config.json')
    test = 'merge_cmd::illuminant_aware_color::'+('metadata_pair' if phase == 'metadata' else 'cached_pair')
    band.job([str(exe), test, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
             wall=300, cpu=1800, gib=8)
    good_process(out, 1)
    g.unchanged(sources+retained)
    data = validate(out)
    save(out/'completion.json', dict(phase=phase, instrument_completed=True, sources_and_caches_unchanged=True,
        receipt=ref(out/'output/receipt.json'), process=ref(out/'process.json'), scope=SCOPE))


def views(run, out):
    import numpy as np
    from PIL import Image
    done = read(run/'completion.json')
    assert done['phase'] == 'cached' and done['instrument_completed']
    assert done['receipt'] == ref(run/'output/receipt.json') and done['process'] == ref(run/'process.json')
    data = validate(run)
    targets = read(HERE/'targets.json')
    out.mkdir(exist_ok=False)
    full_images, tiles = [], []
    for row, (name, _, _, native) in zip(data['captures'], CAPTURES):
        assert row['name'] == name and targets[name]['native_dimensions'] == native
        for arm in ('current', 'candidate'):
            master = Path(row[arm+'_path'])
            rgb, icc, digest = image(master, native)
            assert digest == row[arm+'_rgb16_le_sha256']
            canvas = Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
            full = out/f'{name}-{arm}-full.jpg'
            canvas.save(full, quality=98, subsampling=0, icc_profile=icc)
            overview = canvas.copy(); overview.thumbnail((1617,1617), Image.Resampling.LANCZOS)
            overview_path = out/f'{name}-{arm}-overview.png'
            overview.save(overview_path, icc_profile=icc)
            full_images.append(dict(name=name, arm=arm, master=ref(master), full=ref(full),
                                    overview=ref(overview_path), native_dimensions=native))
            for target in targets[name]['targets']:
                x,y,w,h = target['native_xywh']
                assert 0 <= x < x+w <= native[0] and 0 <= y < y+h <= native[1] and (w,h) == (384,384)
                path = out/f"{name}-{arm}-{target['name']}.png"
                canvas.crop((x,y,x+w,y+h)).save(path, icc_profile=icc)
                tiles.append(dict(name=name, arm=arm, target=target['name'], native_xywh=[x,y,w,h], file=ref(path)))
            del rgb, canvas, overview
    assert len(full_images) == 4 and len(tiles) == 14
    save(out/'completion.json', dict(full_images=full_images, native_tiles=tiles, targets=ref(HERE/'targets.json'),
        run_completion=ref(run/'completion.json'), conversion='Identical RGB16-to8 mapping; retained ICC; no resampling of native tiles.', scope=SCOPE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build', 'controls', 'metadata', 'cached', 'views'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--controls', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--run', type=Path)
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
        assert args.build is not None and args.controls is not None
        execute(args.phase, out, args.build.resolve(), args.controls.resolve(),
                args.metadata.resolve() if args.metadata else None)


if __name__ == '__main__':
    main()
