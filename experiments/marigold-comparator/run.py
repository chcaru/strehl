"""One root-owned complete488-source marigold Helicon B reference; no retries."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import importlib.util
import json
import shutil
import struct
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('existing_chip_comparator',ROOT/'experiments/chip-competitor/run.py')
chip=importlib.util.module_from_spec(spec);sys.modules[spec.name]=chip;spec.loader.exec_module(chip)
read,save,ref,job=chip.read,chip.c.save,chip.c.ref,chip.job
EXAMPLE=ROOT/'crates/strehl-cli/examples/marigold-batch-develop.rs'
RECIPE=ROOT/'experiments/full-stack-source-prior/recipes/marigold-4.json'
CURRENT=ROOT/'experiments/garnet-spatial-trace/marigold4-fixed-1/output'
RESOLVED=ROOT/'experiments/illuminant-aware-color/cached-1/output/marigold4-receipt.json'
GOLDEN=ROOT/'experiments/quality-september19/star-matched-source-1/output'
ORIGINAL_GOLDEN=ROOT/'experiments/quality-september19/star-porous-translation-1/porous-grain/rawler-129.bin'


def unchanged(rows):
    assert all(ref(Path(row['path']))==row for row in rows)


def memory():
    class State(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),*[(n,ctypes.c_ulonglong) for n in
            ('total_physical','available_physical','total_commit','available_commit','total_virtual','available_virtual','extended')]]
    state=State();state.length=ctypes.sizeof(state)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state))
    return {k:getattr(state,k) for k in ('total_physical','available_physical','total_commit','available_commit')}


def chronology():
    recipe=read(RECIPE);rows=recipe['inputs'];assert len(rows)==488
    parent=Path('D:/personal/macro/flower-marigold-cpl')
    for i,row in enumerate(rows):
        directory,number=('stack4.1-offcenter-sw5-cpl',i+21) if i<279 else ('stack4.2-offcenter-sw5-cpl',i-278)
        assert row['index']==i and Path(row['path'])==parent/directory/f'DSC{number:05}.ARW'
        assert Path(row['path']).stat().st_size==row['bytes']
    assert recipe['expected_reference']==244 and recipe['expected_crop']==[191,128,3134,2088]
    assert recipe['warp_map_sha256']=='d2eb0815191279f9d6fc529d76142e56989d4afdcbc052088ef4e7da530b58c1'
    assert ref(Path(recipe['warp_map']))['sha256']==recipe['warp_map_sha256']
    return rows


def metadata(rows):
    for row in rows:
        st=Path(row['path']).stat()
        assert (st.st_size,st.st_mtime_ns)==(row['bytes'],row['mtime_ns'])


def sources():
    # Reuse the established exporter dependency inventory, not all experimental Rust.
    paths={Path(row['path']) for row in chip.sources()}
    paths.add(ROOT/'experiments/chip-competitor/run.py')
    paths.update((EXAMPLE,RECIPE,RESOLVED,CURRENT/'candidate-cache.json',GOLDEN/'receipt.json',ORIGINAL_GOLDEN))
    paths.update(GOLDEN/name for name in ('porous-source-129-frame129-raw-cfa.f32','porous-source-129-frame129-raw.tiff'))
    paths.update(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.md','.json'))
    return [ref(p.resolve()) for p in sorted(paths)]


def capture():
    cache=read(CURRENT/'candidate-cache.json');prior=read(RESOLVED)
    assert prior['baseline_current_rgb16_icc_exact'] and prior['baseline_pinned_rewrite_exact']
    assert cache['frames']==488 and cache['reference']==244 and cache['crop']==[191,128,3134,2088]
    assert cache['full_geometry']==[3516,2344] and cache['plane_order']==['R','G1','G2','B']
    recipe=read(RECIPE)
    assert cache['map_sha256']==recipe['warp_map_sha256']
    # Exact serde Input field order, before attaching filesystem mtime diagnostics.
    ordered=[{key:row[key] for key in ('index','path','identity_name','bytes','sha256')} for row in recipe['inputs']]
    order_bytes=json.dumps(ordered,separators=(',', ':'),ensure_ascii=False).encode('utf-8')
    assert hashlib.sha256(order_bytes).hexdigest()==cache['input_order_sha256']
    assert ref(CURRENT/'candidate-cache.json')['sha256']==prior['input']['cache_sha256']
    assert ref(CURRENT/'candidate.tiff')['sha256']==prior['input']['baseline_sha256']
    assert cache['binary_sha256']==prior['cache_binary_sha256']
    assert prior['current_rgb16_le_sha256']==prior['input']['baseline_pixels_sha256']
    resolved=prior['baseline_resolved']
    assert resolved['tone_bits']==[1008079930,1049460607,1057803469] and resolved['exposure_gain_bits']==1060439283
    assert cache['exposure_stops_bits']==3204448256  # exact -0.5f32
    binary=CURRENT/cache['binary'];assert binary.parent==CURRENT
    return cache,resolved,[ref(CURRENT/'candidate.tiff'),ref(CURRENT/'candidate-cache.json'),ref(RESOLVED)]


def build(out):
    assert shutil.disk_usage(HERE).free>=120<<30
    out.mkdir(exist_ok=False);stage=out/'build';stage.mkdir()
    rows=chronology();rows=[dict(row,mtime_ns=Path(row['path']).stat().st_mtime_ns) for row in rows]
    cache,resolved,fixed=capture()
    assert ref(chip.HELICON)['sha256']==chip.HELICON_SHA
    save(out/'inputs.json',rows);save(out/'fixed.json',dict(cache=cache,resolved=resolved,identities=fixed,helicon=ref(chip.HELICON)))
    EXAMPLE.touch();bound=sources();save(stage/'sources.json',bound)
    command=['cargo','build','-p','strehl-cli','--example','marigold-batch-develop','--release',
        '--features','native-pyramid-profile,native-gpu-gather,native-direct-planes','--jobs','2',
        '--target-dir',str(ROOT/'target/native-pyramid-profile'),'--locked','--offline','--message-format=json-render-diagnostics']
    job(command,dict(RAYON_NUM_THREADS='8',CARGO_INCREMENTAL='0'),stage,wall=600,cpu=1800,gib=8)
    log=(stage/'process.log').read_text(encoding='utf-8',errors='replace');assert 'Compiling strehl-cli' in log
    artifacts=[]
    for line in log.splitlines():
        try: row=json.loads(line)
        except ValueError: continue
        if row.get('reason')=='compiler-artifact' and row.get('executable') and row['target']['name']=='marigold-batch-develop':artifacts.append(row)
    assert len(artifacts)==1 and artifacts[0]['fresh'] is False
    exe=stage/'marigold-batch-develop.exe';shutil.copyfile(artifacts[0]['executable'],exe)
    unchanged(bound);unchanged(fixed);metadata(rows)
    save(stage/'executable.json',ref(exe))


def retained(out):
    bound=read(out/'build/sources.json');unchanged(bound)
    fixed=read(out/'fixed.json');unchanged(fixed['identities'])
    assert fixed['helicon']==ref(chip.HELICON) and fixed['helicon']['sha256']==chip.HELICON_SHA
    rows=read(out/'inputs.json');assert [{k:v for k,v in row.items() if k!='mtime_ns'} for row in rows]==chronology();metadata(rows)
    exe=read(out/'build/executable.json');assert ref(Path(exe['path']))==exe
    assert ref(EXAMPLE) in bound and ref(Path(__file__).resolve()) in bound
    proc=read(out/'build/process.json');assert proc['exit_code']==0 and proc['error'] is None and proc['terminal_job_accounting'] and not proc['cleanup_errors']
    return bound,fixed,rows,exe


def develop(out):
    bound,fixed,rows,exe=retained(out)
    assert shutil.disk_usage(out).free>=120<<30
    stage=out/'development';stage.mkdir(exist_ok=False)
    cache=fixed['cache'];xyz=[[struct.unpack('<f',struct.pack('<I',b))[0] for b in row] for row in cache['xyz_to_cam_bits']]
    cfg=dict(inputs=rows,out=str(out/'developed'),cache_metadata=cache,resolved=fixed['resolved'],
        cache_binary=str(CURRENT/cache['binary']),baseline=str(CURRENT/'candidate.tiff'),
        baseline_sha256=fixed['identities'][0]['sha256'],expected_xyz_to_cam=xyz,
        fixture_dir=str(GOLDEN),fixture_original_u16=str(ORIGINAL_GOLDEN))
    save(stage/'config.json',cfg)
    try: job([exe['path'],str(stage/'config.json')],{'RAYON_NUM_THREADS':'8'},stage,wall=600,cpu=2400,gib=3)
    finally: metadata(rows);unchanged(bound);unchanged(fixed['identities'])
    receipt=read(out/'developed/receipt.json');assert receipt['status']=='488_UNALIGNED_NATIVE_RGB16_DEVELOPED'
    assert receipt['configuration']==cfg and len(receipt['frames'])==488
    assert receipt['golden']['differing']==receipt['golden']['normalized_f32_differences']==0
    assert receipt['current_golden']['rgb16_and_icc_exact'] and receipt['resolved']==fixed['resolved']
    import tifffile
    with tifffile.TiffFile(CURRENT/'candidate.tiff') as tf: expected_icc=bytes(tf.pages[0].tags[34675].value)
    for i,(row,original) in enumerate(zip(receipt['frames'],rows)):
        p=out/'developed'/f'frame-{i:05}.tiff'
        assert row['ordinal']==i and Path(row['output'])==p and row['input']==original['path']
        assert row['input_sha256']==original['sha256'] and row['input_bytes']==original['bytes']
        assert row['input_wb_bits']==cache['wb_gains_bits'] and row['original_metadata_unchanged']
        assert p.stat().st_size==row['output_bytes']
        with tifffile.TiffFile(p) as tf:
            assert len(tf.pages)==1 and tf.pages[0].shape==(4688,7032,3) and str(tf.pages[0].dtype)=='uint16'
            assert bytes(tf.pages[0].tags[34675].value)==expected_icc
    save(out/'development-complete.json',dict(source_count=488,receipt=ref(out/'developed/receipt.json'),
        current_pixels_icc_exact=True,original_metadata_unchanged=True,all_formats_icc_checked=True,
        scope='CA-off unaligned fixed-developed inputs; vendor aligns, develops before fusion; workflow reference only'))


def vendor(out):
    bound,fixed,rows,exe=retained(out)
    completed=read(out/'development-complete.json');assert completed['source_count']==488 and completed['current_pixels_icc_exact']
    receipt_path=out/'developed/receipt.json';assert ref(receipt_path)==completed['receipt']
    receipt=read(receipt_path);prepared=[out/'developed'/f'frame-{i:05}.tiff' for i in range(488)]
    assert [str(p) for p in prepared]==[row['output'] for row in receipt['frames']]
    expected=[dict(path=str(p),sha256=row['output_sha256'],bytes=row['output_bytes']) for p,row in zip(prepared,receipt['frames'])]
    unchanged(expected)
    assert shutil.disk_usage(out).free>=20<<30
    stage=out/'helicon-b';stage.mkdir(exist_ok=False)
    manifest=stage/'inputs.txt';manifest.write_text('\n'.join(map(str,prepared))+'\n',encoding='utf-8')
    master=stage/'whole-stack.tiff'
    command=[str(chip.HELICON),'-silent','-noprogress','-i',str(manifest),'-mp:1','-rp:8','-sp:4','-sort:asc','-tif:u','-save:'+str(master),'-o',str(stage/'saved-outputs.txt')]
    current_memory=memory();save(stage/'resource-preflight.json',dict(memory=current_memory,free_bytes=shutil.disk_usage(out).free,
        required_available_commit_bytes=48<<30,required_available_physical_bytes=46<<30,job_commit_cap_bytes=40<<30))
    assert current_memory['available_commit']>=48<<30 and current_memory['available_physical']>=46<<30,'Insufficient live memory: stop without retry'
    save(stage/'bindings.json',dict(executable=ref(chip.HELICON),inputs=expected,manifest=ref(manifest),
        development=ref(out/'development-complete.json'),development_receipt=ref(receipt_path),sources=bound,
        resource_preflight=ref(stage/'resource-preflight.json'),settings=dict(method='B',radius=8,smoothing=4,order='ascending',
        other_alignment_brightness_interpolation_state='unchanged application state; not recovered'),license_scope='existing trial; no state change'))
    try: job(command,{},stage,wall=600,cpu=12000,gib=40)
    finally:
        after=[ref(p) for p in prepared];save(stage/'inputs-after.json',after);assert after==expected
        metadata(rows);unchanged(bound);unchanged(fixed['identities']);assert ref(chip.HELICON)==fixed['helicon']
    import tifffile
    with tifffile.TiffFile(CURRENT/'candidate.tiff') as tf: expected_icc=bytes(tf.pages[0].tags[34675].value)
    views=chip.format_and_views(master,stage,expected_icc)
    save(stage/'output.json',dict(complete_488_source_reference=True,prepared_inputs_unchanged=True,
        original_metadata_unchanged=True,views=views,photographic_review='pending',quality_claim=False,
        scope='Whole-workflow headroom reference, not mechanism or SOTA; no automated native correspondence claim'))
    (stage/'images.md').write_text('\n\n'.join(['# Complete488-source marigold reference',
        f'[Current complete RGB16 master]({(CURRENT/"candidate.tiff").as_posix()})',
        f'[Helicon B complete RGB16 master]({master.as_posix()})',
        f'[B complete native PNG]({(stage/"whole.png").as_posix()})',
        f'![B whole-field overview only]({(stage/"overview.png").as_posix()})'])+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('build','develop','b'))
    p.add_argument('--out',type=Path,default=HERE/'run-1');args=p.parse_args();out=args.out.resolve()
    assert out.parent==HERE and out.name.startswith('run-')
    {'build':build,'develop':develop,'b':vendor}[args.stage](out)


if __name__=='__main__':main()
