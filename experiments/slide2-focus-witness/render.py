"""Complete current-binary slide2 observer pair at independently located frames."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT/'experiments/quality-september20'
BASE = OLD/'slide2-baseline-1'
BUILD = ROOT/'experiments/common-edge-pyramid/build-2'
EXE_SHA = 'e88b8a3983b40aa3fd0a1237eeb87b31d64ce631b0d9af9afda550ce7ff42601'
OBSERVER_SHA = '093e25703bd86a303c95edbc557c253359365557d396364baa7dbdb9b6782111'
spec = importlib.util.spec_from_file_location('slide2_source_bounded', ROOT/'experiments/m193c-output-grid/bounded-process.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def ref(path):
    return dict(path=str(path.resolve()), **b.binding(path))


def pixel_sha(array):
    return hashlib.sha256(array.astype('<u2', copy=False).tobytes()).hexdigest()


def load_configuration(locator):
    """No re-ranking, refitting or relocating: use all fixed nominations."""
    cfg = read(OLD/'slide2-source-config.json')
    selected = read(locator/'locator.json')
    assert selected['schema'] == 1 and selected['reference_index'] == 149
    assert selected['crop_quad_xywh'] == [139,93,3238,2158]
    assert selected['map_sha256'] == '7712a5eb7f74001485bc69b9d9721fe1bde4c0aa8099e28ddf703ede8069c14a'
    assert selected['regions'] == cfg['regions']
    assert selected['fixed_control'] == dict(name='pale-control', frame=149)
    assert set(selected['nominations']) == {'medium-bars','fine-bars','lettering'}
    regions = []
    for region in cfg['regions']:
        indices = [149] if region['name'] == 'pale-control' else selected['nominations'][region['name']]
        assert len(indices) == (1 if region['name'] == 'pale-control' else 2)
        assert all(type(i) is int and 0 <= i < 299 for i in indices)
        assert len(set(indices)) == len(indices)
        if len(indices) == 2:
            assert indices[1] == (indices[0]+2 if indices[0]+2 < 299 else indices[0]-2)
        for index in indices:
            row = dict(region, name=f"{region['name']}-frame-{index:03d}", frame=index)
            assert row['width'] == row['height'] == 384
            assert row['x'] % 2 == row['y'] % 2 == 0
            regions.append(row)
    assert len(regions) == 7 and len({r['name'] for r in regions}) == 7
    return dict(cfg, regions=regions), selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--locator', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    locator = args.locator.resolve()
    assert locator.parent == HERE and locator != out
    assert out.parent == HERE and out.name.startswith('render-') and not out.exists()
    cfg, selected = load_configuration(locator)
    located = read(locator/'completion.json')
    assert located['status'] == 'FOCUS_NEIGHBOURHOODS_READY'
    assert located['passed'] and located['controls_passed']
    assert located['original_metadata_unchanged'] and located['independent_decode_exact']
    assert located['config'] == ref(OLD/'slide2-source-config.json')
    assert located['locator'] == ref(locator/'locator.json')
    assert located['source_inventory'] == ref(locator/'originals-before.json')
    assert located['nominations'] == selected['nominations'] and located['fixed_control'] == selected['fixed_control']
    out.mkdir()
    config_path, plan_path = out/'source-config.json', HERE/'render-plan.md'
    save(config_path, cfg)
    assert cfg['frames'] == 299 and len(cfg['regions']) == 7
    warp = Path(cfg['map'])
    original = read(BASE/'completion.json')
    assert original['original_metadata_and_content_unchanged'] and original['crop_quad_xywh'] == [139,93,3238,2158]
    assert ref(warp) == original['map']
    assert original['map']['sha256'] == '7712a5eb7f74001485bc69b9d9721fe1bde4c0aa8099e28ddf703ede8069c14a'
    assert ref(BASE/'slide2.tiff') == original['master']
    exe = BUILD/'cli-tests.exe'
    executable = read(BUILD/'executable.json')
    assert ref(exe) == executable and executable['sha256'] == EXE_SHA
    source_rows = read(BUILD/'sources.json')
    observer = ROOT/'experiments/quality-september14/matched-source-tests.rs'
    assert any(Path(r['path']) == observer and r['sha256'] == OBSERVER_SHA for r in source_rows)
    assert 'Compiling strehl-cli' in (BUILD/'process.log').read_text(encoding='utf-8', errors='replace')
    build_process = read(BUILD/'process.json')
    assert build_process['exit_code'] == 0 and build_process['error'] is None
    # This fresh retained binary is immutable; later source edits do not rebuild it.
    sources = [ref(p) for p in [Path(__file__), config_path, plan_path, Path(spec.origin),
        ROOT/'experiments/m12-scorecard/m12-harness.py', BUILD/'sources.json', BUILD/'executable.json',
        BUILD/'invocation.json', BUILD/'process.json', BASE/'inputs.json', BASE/'completion.json',
        BASE/'invocation.json', OLD/'slide2-source-config.json', locator/'locator.json',
        locator/'completion.json', locator/'controls.json', locator/'bindings.json', locator/'originals-before.json']]
    save(out/'bindings.json', dict(executable=executable, sources=sources,
        compiled_build_sources=source_rows,
        provenance='Fresh common-edge build2 retains current production arithmetic. Only the existing matched-source test runs; no common-edge intervention. No new compilation.'))
    input_receipt = read(BASE/'inputs.json')
    inputs = input_receipt['inventory']
    rawdir = Path(cfg['dir'])
    def metadata():
        return [dict(path=str(p.resolve()), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns)
                for p in sorted(rawdir.rglob('*')) if p.is_file()]
    assert metadata() == inputs
    assert sorted(p.name for p in rawdir.iterdir() if p.is_file() and p.suffix.upper()=='.ARW') == [f'DSC{i:05d}.ARW' for i in range(1,300)]
    selected_frames = sorted({r['frame'] for r in cfg['regions']})
    selected_sources = [ref(rawdir/f'DSC{i+1:05d}.ARW') for i in selected_frames]
    for row in selected_sources:
        assert row['sha256'] == input_receipt['sha256'][row['path']]
    save(out/'selected-originals.json', selected_sources)
    fields = read(BASE/'invocation.json')['environment']
    fields.update(STREHL_FINE_SUPPORT='off')
    assert 'STREHL_LOCAL_PLACEMENT_FILE' not in fields
    api = b.load_job_api(b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    command = [str(exe), 'merge_cmd::matched_source_tests::matched_source_actual_consumer',
               '--exact', '--ignored', '--nocapture', '--test-threads=1']
    save(out/'preregistration.json', dict(config=cfg, reference=149, crop_quad_xywh=original['crop_quad_xywh'],
        selected_frames=selected_frames, selected_originals=selected_sources, originals_metadata=inputs,
        baseline_scope='New same-executable same-pinned-tone off/on pair; six-decimal TIFF-description tone is not asserted to equal original automatic tone bits.',
        observer_scope='All delivered RGB16 samples and TIFF bytes must be identical on/off; earlier hook placebo retained as historical evidence.',
        original_hash_scope='Full299 content hashes retained from historical baseline. Fresh nominated-original content hashes before/after both renders; all299 metadata/order checked. No fresh all299 content audit claimed.',
        limits=dict(wall_seconds_per_replay=900,cpu_seconds_per_replay=7200,committed_bytes=12<<30)))
    for label, enabled in [('off',False),('on',True)]:
        folder = out/label
        folder.mkdir()
        configuration = dict(cfg, observe=enabled, out=str(folder/'output'))
        save(folder/'config.json', configuration)
        environment, removed = b.clean_environment(dict(fields, STREHL_MATCHED_SOURCE_CONFIG=str(folder/'config.json')).items())
        save(folder/'invocation.json', dict(command=command, environment={k:environment[k] for k in fields}|{'STREHL_MATCHED_SOURCE_CONFIG':str(folder/'config.json')}, removed_environment=removed))
        print('SLIDE2_SOURCE_STAGE',label,flush=True)
        result = b.run(command,environment,ROOT,folder/'process.log',api=api,
            wall_seconds=900,cpu_seconds=7200,committed_bytes=12<<30,log_bytes=16<<20)
        save(folder/'process.json',result)
        assert result['exit_code']==0 and result['error'] is None and result['terminal_job_accounting'] and not result['cleanup_errors']
        assert 'test result: ok. 1 passed;' in (folder/'process.log').read_text(errors='replace')
        assert metadata()==inputs and ref(exe)==executable
        assert all(ref(Path(row['path']))==row for row in sources)
        assert all(ref(Path(row['path']))==row for row in selected_sources)
        assert ref(warp)==original['map']

    import numpy as np
    import tifffile
    from PIL import Image
    receipts = {label:read(out/label/'output/receipt.json') for label in ['off','on']}
    expected_bits = [struct.unpack('<I',struct.pack('<f',cfg['tone'][k]))[0] for k in ['black','white','contrast']]
    for label, receipt in receipts.items():
        assert receipt['crop_quad_xywh']==[139,93,3238,2158] and receipt['source_frame_count']==299 and receipt['native_map_reference']==149
        assert receipt['tone_bits']==expected_bits and receipt['levels']==[512,15360]
        assert receipt['raw_count']==receipt['gathered_count']==receipt['merged_count']==(len(cfg['regions']) if label=='on' else 0)
    assert receipts['on']['wb_bits']==receipts['off']['wb_bits']
    masters={label:out/label/'output/replay.tiff' for label in ['off','on']}
    off,on=[tifffile.imread(masters[k]) for k in ['off','on']]
    assert off.shape==on.shape==(4316,6476,3) and off.dtype==on.dtype==np.uint16
    differences=int(np.count_nonzero(off!=on))
    save(out/'observer-neutrality.json',dict(different_rgb16_samples=differences,off=ref(masters['off']),on=ref(masters['on']),
        off_pixel_sha256=pixel_sha(off),on_pixel_sha256=pixel_sha(on),identical_tiff_bytes=b.binding(masters['off'])==b.binding(masters['on'])))
    assert differences==0 and b.binding(masters['off'])==b.binding(masters['on'])
    with tifffile.TiffFile(masters['off']) as f:
        icc=bytes(f.pages[0].tags[34675].value)
    assert hashlib.sha256(icc).hexdigest()==original['display']['icc_sha256']
    # Retain the relation to the old automatic baseline without calling tone changes a gain.
    historical=tifffile.imread(BASE/'slide2.tiff')
    assert pixel_sha(historical)==original['display']['decoded_rgb16_le_sha256']
    save(out/'historical-baseline-relation.json',dict(different_rgb16_samples=int(np.count_nonzero(off!=historical)),
        max_abs_rgb16=int(np.max(np.abs(off.astype(np.int32)-historical.astype(np.int32)))),
        scope='Different binary and rounded pinned tone; new matched off/on pair is attribution baseline. No quality inference.'))
    del historical
    regions={r['name']:r for r in cfg['regions']}
    seen,views,checks=set(),[],[]
    for record in receipts['on']['patches']:
        name,stage=record['name'],record['stage']
        assert (name,stage) not in seen and name in regions and stage in ['raw','gathered','merged']
        seen.add((name,stage))
        region=regions[name]
        x,y,w,h=[region[k] for k in ['x','y','width','height']]
        assert record['frame']==region['frame'] and record['reference_output_xywh']==[x,y,w,h]
        assert record['trim']==4 and record['width']==record['height']==392
        stem=record['stem']; assert Path(stem).name==stem
        with tifffile.TiffFile(out/'on/output'/f'{stem}.tiff') as f:
            image=f.asarray(); assert bytes(f.pages[0].tags[34675].value)==icc
        assert image.shape==(392,392,3) and image.dtype==np.uint16
        native=image[4:-4,4:-4]
        filename=out/f'{stem}-native.png'
        Image.fromarray(((native.astype(np.uint32)+128)//257).astype(np.uint8)).save(filename,icc_profile=icc)
        views.append(dict(name=name,stage=stage,frame=region['frame'],image=ref(filename),pixel_sha256=pixel_sha(native),
            padded_origin_xy=record['padded_origin_xy'],reference_output_xywh=[x,y,w,h],coordinates=record['coordinates']))
        if stage=='merged':
            exact=int(np.count_nonzero(native!=off[y:y+h,x:x+w]))
            interior=int(np.count_nonzero(native[16:-16,16:-16]!=off[y+16:y+h-16,x+16:x+w-16]))
            placebo=int(np.count_nonzero(native!=off[y:y+h,x+2:x+w+2]))
            assert exact==interior==0
            checks.append(dict(name=name,exact_differences=exact,interior_differences=interior,wrong_x_plus_two_differences=placebo))
    assert seen=={(name,stage) for name in regions for stage in ['raw','gathered','merged']}
    # Pale control may be featureless; the wrong-origin foil must be live on
    # every structured site, never rescued by dropping a nominated frame.
    assert all(r['wrong_x_plus_two_differences'] > 0 for r in checks if not r['name'].startswith('pale-control-'))
    save(out/'native-views.json',views)
    save(out/'merged-slice-checks.json',checks)
    full=Image.fromarray(((off.astype(np.uint32)+128)//257).astype(np.uint8))
    full.save(out/'matched-full.png',icc_profile=icc)
    full.thumbnail((1800,1800),Image.Resampling.LANCZOS)
    full.save(out/'matched-overview-only.png',icc_profile=icc)
    with (out/'images.md').open('x',encoding='utf-8') as f:
        f.write('# Complete matched slide2 baseline\n\n')
        for label,path in [('Observer-off RGB16',masters['off']),('Observer-on RGB16',masters['on']),('Full native PNG',out/'matched-full.png'),('Overview only',out/'matched-overview-only.png')]:
            f.write(f'[{label}]({path.as_posix()})\n\n')
    assert metadata()==inputs and all(ref(Path(row['path']))==row for row in selected_sources)
    save(out/'completion.json',dict(status='SLIDE2_FOCUS_SOURCE_ATTRIBUTION_READY',observer_pixel_and_byte_identical=True,
        selected_frames=selected_frames,regions=list(regions),source_frame_count=299,original_metadata_unchanged=True,
        selected_original_content_unchanged=True,photographically_reviewed=False,quality_gain_claim=False,
        full_image=ref(masters['off']),full_png=ref(out/'matched-full.png'),native_views=len(seen)))
    print('SLIDE2_SOURCE_COMPLETE',flush=True)


if __name__=='__main__':
    main()
