"""One bounded, exact-consumer star replay with three focused-source observers.

No merge/registration change. Root executes after independent review.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT / 'experiments/quality-september19'
BASELINE = OLD / 'star-full-context-placement/baseline-1'
PRIOR_OBSERVER = OLD / 'star-matched-source-1'
DEFAULT_BUILD = ROOT / 'experiments/through-focus-events/build-1'
SELECTED = (116, 118, 120)
ROI = [472, 1352, 328, 328]
EXPECTED_PIXEL_SHA256 = 'c6a5d6a68bc67950ebfc351ef3130ccd1b84b9bf33a7934f2d40cb1822022df9'
EXPECTED_MAP_SHA256 = '6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1'
EXPECTED_BASELINE_FILE_SHA256 = '5fc6c3ab8e2bcb64ee9d1383586f0c3763d6dbc709968a218bf36b9d654420ae'
EXPECTED_OBSERVER_SOURCE_SHA256 = '093e25703bd86a303c95edbc557c253359365557d396364baa7dbdb9b6782111'

COMMON = ROOT / 'experiments/full-context-placement/run.py'
spec = importlib.util.spec_from_file_location('star_focused_attribution_common', COMMON)
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def require_current_sources(rows):
    mismatches = []
    for row in rows:
        path = Path(row['path'])
        if not path.is_file() or c.ref(path) != row:
            mismatches.append(str(path))
    if mismatches:
        raise RuntimeError('Executable source bindings are stale; do not run or relax: '
                           + '; '.join(mismatches))


def pixel_hash(array):
    # Explicit little-endian RGB16 samples, independent of TIFF software tag.
    return hashlib.sha256(array.astype('<u2', copy=False).tobytes(order='C')).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--build', type=Path, default=DEFAULT_BUILD)
    args = parser.parse_args()
    out = args.out.resolve()
    build = args.build.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    assert build.is_relative_to(ROOT / 'experiments')
    out.mkdir(parents=True)

    sources = read_json(build / 'sources.json')
    require_current_sources(sources)
    exe = build / 'cli-tests.exe'
    executable = read_json(build / 'executable.json')
    assert c.ref(exe) == executable
    observer_source = ROOT / 'experiments/quality-september14/matched-source-tests.rs'
    assert c.ref(observer_source)['sha256'] == EXPECTED_OBSERVER_SOURCE_SHA256
    assert c.ref(observer_source) in sources, 'Actual observer source missing from fresh manifest'
    assert 'Compiling strehl-cli' in (build / 'process.log').read_text(encoding='utf-8', errors='replace')

    invocation = read_json(BASELINE / 'invocation.json')
    cfg = read_json(BASELINE / 'config.json')
    baseline_receipt = read_json(BASELINE / 'output/receipt.json')
    prior_neutrality = read_json(PRIOR_OBSERVER / 'observer-nonperturbation.json')
    baseline_inputs = read_json(BASELINE / 'inputs.json')
    baseline_image = BASELINE / 'output/replay.tiff'
    assert c.ref(baseline_image)['sha256'] == EXPECTED_BASELINE_FILE_SHA256
    assert prior_neutrality['different_rgb16_samples'] == 0
    assert prior_neutrality['baseline_pixel_sha256'] == EXPECTED_PIXEL_SHA256
    assert cfg['frames'] == 259 and cfg['observe'] is False
    assert cfg['tone'] == dict(black=.01566, white=.51099, contrast=.55)
    assert baseline_receipt['crop_quad_xywh'] == [77, 52, 3362, 2240]
    assert baseline_receipt['native_map_reference'] == 129
    assert baseline_receipt['source_frame_count'] == 259
    warp = Path(cfg['map'])
    assert c.ref(warp) == baseline_inputs['warp']
    assert c.ref(warp)['sha256'] == EXPECTED_MAP_SHA256
    rawdir = Path(cfg['dir'])
    assert rawdir.is_absolute() and rawdir.name == 'star-sand-cpl'
    # iterdir includes hidden/system directory entries, unlike non-Force PS listing.
    files = sorted(p for p in rawdir.iterdir() if p.is_file() and p.suffix.upper() == '.ARW')
    assert [p.name for p in files] == [f'DSC{i:05d}.ARW' for i in range(16, 275)]
    inputs = [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns) for p in files]
    assert inputs == baseline_inputs['inputs']
    selected_originals = [dict(source_index0=i, binding=c.ref(files[i])) for i in SELECTED]

    cfg.update(out=str(out / 'output'), observe=True,
               regions=[dict(name=f'porous-focused-{i}', frame=i, x=ROI[0], y=ROI[1],
                             width=ROI[2], height=ROI[3]) for i in SELECTED])
    c.save(out / 'config.json', cfg)
    fields = dict(invocation['environment'])
    assert 'STREHL_LOCAL_PLACEMENT_FILE' not in fields
    fields.update(STREHL_MATCHED_SOURCE_CONFIG=str(out / 'config.json'), STREHL_FINE_SUPPORT='off')
    command = [str(exe), 'merge_cmd::matched_source_tests::matched_source_actual_consumer',
               '--exact', '--ignored', '--nocapture', '--test-threads=1']
    references = [c.ref(path) for path in [warp, baseline_image,
        BASELINE / 'config.json', BASELINE / 'output/receipt.json', BASELINE / 'inputs.json',
        BASELINE / 'invocation.json', PRIOR_OBSERVER / 'observer-nonperturbation.json',
        PRIOR_OBSERVER / 'merged-patch-verification.json',
        OLD / 'star-focus-locator-1/receipt.json', OLD / 'star-focus-locator-1/report.md']]
    bindings = dict(executable=executable, sources=sources, references=references,
        runner=c.ref(Path(__file__)), common=c.ref(COMMON),
        bounded_process=c.ref(ROOT / 'experiments/m193c-output-grid/bounded-process.py'),
        windows_job=c.ref(ROOT / 'experiments/m12-scorecard/m12-harness.py'),
        plan=c.ref(HERE / 'plan.md'))
    c.save(out / 'bindings.json', bindings)
    c.save(out / 'inputs.json', dict(all259_metadata=inputs, selected3_content=selected_originals,
        scope='All259 size/mtime checked; only selected116/118/120 have full-file SHA256 before/after.'))
    c.save(out / 'preregistration.json', dict(selected_frames=list(SELECTED), frame_count=259,
        selected_filenames=[files[i].name for i in SELECTED], reference=129, native_output_roi=ROI,
        crop_quad_xywh=[77,52,3362,2240], observer=True, correction=False,
        expected_final_rgb16le_sha256=EXPECTED_PIXEL_SHA256,
        baseline=references[1], executable=executable,
        source_selection='Existing photograph-confirmed detail-bearing sources; not universal best on the sloping surface.',
        limitation='Raw patches are centre-mapped and even-rounded without CA or resampling. Compare gathered versus merged for exact-grid missing-feature attribution.',
        observer_check='Current observer-on entire RGB16 output must equal retained canonical observer-off baseline; no separate current observer-off full replay.',
        prior_neutrality_scope='Same unchanged hook passed earlier125/129/133; that does not alone prove these new sources neutral.',
        job_limits=dict(wall_seconds=600, cpu_seconds=3600, committed_bytes=16 << 30, log_bytes=16 << 20)))

    c.job(command, fields, out, wall=600)
    log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'test result: ok. 1 passed;' in log
    for row in inputs:
        stat = Path(row['path']).stat()
        assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    assert all(c.ref(Path(row['binding']['path'])) == row['binding'] for row in selected_originals)
    require_current_sources(sources + references)
    assert c.ref(exe) == executable
    for key in ('runner', 'common', 'bounded_process', 'windows_job', 'plan'):
        assert c.ref(Path(bindings[key]['path'])) == bindings[key]

    import numpy as np
    import tifffile
    from PIL import Image
    receipt = read_json(out / 'output/receipt.json')
    for key in ('crop_quad_xywh', 'tone_bits', 'wb_bits', 'levels', 'source_frame_count', 'native_map_reference'):
        assert receipt[key] == baseline_receipt[key], f'Canonical mismatch: {key}'
    assert receipt['raw_count'] == receipt['gathered_count'] == receipt['merged_count'] == 3
    assert len(receipt['patches']) == 9
    full = tifffile.imread(out / 'output/replay.tiff')
    baseline = tifffile.imread(baseline_image)
    with tifffile.TiffFile(baseline_image) as tif:
        tag = tif.pages[0].tags.get(34675)
        baseline_icc = bytes(tag.value) if tag is not None else None
    assert full.shape == baseline.shape == (4480, 6724, 3)
    assert full.dtype == baseline.dtype == np.uint16
    differing = int(np.count_nonzero(full != baseline))
    neutral = dict(different_rgb16_samples=differing, total_rgb16_samples=int(full.size),
        expected_pixel_sha256=EXPECTED_PIXEL_SHA256, baseline_pixel_sha256=pixel_hash(baseline),
        observed_pixel_sha256=pixel_hash(full), baseline_file=c.ref(baseline_image),
        observed_file=c.ref(out / 'output/replay.tiff'),
        scope='Entire current observer-on RGB16 versus retained observer-off canonical; TIFF metadata can differ.')
    c.save(out / 'observer-nonperturbation.json', neutral)
    assert differing == 0 and neutral['baseline_pixel_sha256'] == neutral['observed_pixel_sha256'] == EXPECTED_PIXEL_SHA256

    views = []
    patches = []
    seen = set()
    for record in receipt['patches']:
        key = (record['frame'], record['stage'])
        assert key not in seen and key[0] in SELECTED and key[1] in ('raw', 'gathered', 'merged')
        seen.add(key)
        assert record['reference_output_xywh'] == ROI and record['trim'] == 4
        assert record['width'] == record['height'] == 336
        stem = record['stem']
        assert Path(stem).name == stem
        with tifffile.TiffFile(out / 'output' / (stem + '.tiff')) as tif:
            image = tif.asarray()
            tag = tif.pages[0].tags.get(34675)
            icc = bytes(tag.value) if tag is not None else None
        assert icc == baseline_icc, 'Patch colour profile differs from canonical full output'
        assert image.shape == (336, 336, 3) and image.dtype == np.uint16
        native = image[4:332, 4:332]
        filename = stem + '-native.png'
        png = Image.fromarray(((native.astype(np.uint32) + 128) // 257).astype(np.uint8))
        png.save(out / filename, **({'icc_profile': icc} if icc is not None else {}))
        views.append(dict(frame=key[0], stage=key[1], file=filename, rgb16_sha256=pixel_hash(native),
            reference_output_xywh=ROI, padded_origin_xy=record['padded_origin_xy'], coordinates=record['coordinates'],
            icc_sha256=hashlib.sha256(icc).hexdigest() if icc is not None else None,
            colour_management='ICC preserved' if icc is not None else 'Consistent untagged TIFF and PNG; no profile invented',
            artifacts=[c.ref(out / 'output' / (stem + suffix))
                       for suffix in ('.tiff', '-cfa.f32', '-mhc-camera-rgb.f32')]))
        if key[1] == 'merged':
            exact = int(np.count_nonzero(native != baseline[1352:1680, 472:800]))
            inner = int(np.count_nonzero(image[20:316, 20:316] != baseline[1368:1664, 488:784]))
            wrong = int(np.count_nonzero(native != baseline[1352:1680, 474:802]))
            patches.append(dict(frame=key[0], different_rgb16_samples=exact,
                independently_trimmed_inner_differences=inner, wrong_x_plus_two_different_samples=wrong))
            assert exact == inner == 0 and wrong > 0
    assert seen == {(i, s) for i in SELECTED for s in ('raw', 'gathered', 'merged')}
    c.save(out / 'native-views.json', views)
    c.save(out / 'merged-patch-verification.json', dict(checks=patches,
        scope='Same merged field repeated3times; exact full-image lookup, alternate trim and wrong-location placebo.'))
    c.save(out / 'completion.json', dict(status='FOCUSED_SOURCE_ATTRIBUTION_READY',
        selected_frames=list(SELECTED), source_frame_count=259, observer_pixel_identical=True,
        original_metadata_unchanged=True, selected_original_content_unchanged=True,
        full_image=c.ref(out / 'output/replay.tiff'), receipt=c.ref(out / 'output/receipt.json'),
        photographically_reviewed=False))
    print(json.dumps(dict(differing_rgb16_samples=differing, native_views=len(views))), flush=True)


if __name__ == '__main__':
    main()
