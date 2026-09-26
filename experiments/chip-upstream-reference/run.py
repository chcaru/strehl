"""Pinned stock upstream inventory and one complete299-TIFF workflow reference."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREPARED = ROOT/'experiments/chip-competitor/run-1'
BINARY = HERE/'program-1/focus-stack.exe'
PROGRAM = HERE/'program-manifest.json'
BINARY_SHA = 'e256176d70bec54bb51a448b2adc452e7f49d21bc5042b40689a3257bbfdee9e'
DEVELOPER_SHA = '97f198664496c18ebb7723450e240163983cf00a5499e1db0695bdd0f4c3bf9c'
ICC_SHA = '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
FLAGS = ['--no-whitebalance', '--no-contrast', '--threads=8', '--batchsize=4', '--no-opencl']

spec = importlib.util.spec_from_file_location('upstream_existing_job', ROOT/'experiments/chip-competitor/run.py')
jobs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = jobs
spec.loader.exec_module(jobs)
read, save, ref = jobs.read, jobs.c.save, jobs.c.ref


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sources():
    paths = [HERE/name for name in ('run.py','plan.md','independent-review.md','program-manifest.json','prepare-program.py')]
    paths += [ROOT/name for name in ('experiments/chip-competitor/run.py',
        'experiments/full-context-placement/run.py','experiments/m193c-output-grid/bounded-process.py',
        'experiments/m12-scorecard/m12-harness.py')]
    return [ref(p) for p in paths]


def unchanged(rows):
    require(all(ref(Path(row['path'])) == row for row in rows), 'Bound content changed')


def prepared():
    receipt_path = PREPARED/'developed/receipt.json'
    complete = read(PREPARED/'development-complete.json')
    require(ref(receipt_path) == complete['receipt'] and complete['receipt']['sha256'] == DEVELOPER_SHA
            and complete['source_count'] == 299 and complete['all_formats_and_icc_checked'], 'Wrong development receipt')
    receipt, originals = read(receipt_path), read(PREPARED/'inputs.json')
    require(receipt['status'] == '299_UNALIGNED_NATIVE_RGB16_DEVELOPED' and len(receipt['frames']) == len(originals) == 299
            and receipt['golden']['differing'] == receipt['golden']['normalized_f32_differences'] == 0,
            'Incomplete development or failed decoder/developer witness')
    require(receipt['wb_bits'] == [1070374912,1065353216,1076715520]
            and receipt['tone_bits'] == [999074891,1064454645,1057803469], 'Prepared development differs')
    rows = []
    for i, (frame, original) in enumerate(zip(receipt['frames'], originals)):
        path = PREPARED/'developed'/f'DSC{i+1:05d}.tiff'
        require(frame['ordinal'] == i and Path(frame['output']) == path and frame['output_wh'] == [7032,4688]
                and frame['input'] == original['path']
                and isinstance(frame['input_sha256'],str) and len(frame['input_sha256']) == 64
                and all(c in '0123456789abcdef' for c in frame['input_sha256'])
                and frame['input_bytes'] == original['bytes'] and Path(original['path']).name == f'DSC{i+1:05d}.ARW',
                'Prepared order/original binding mismatch')
        rows.append(dict(path=str(path), sha256=frame['output_sha256'], bytes=frame['output_bytes']))
    require(len({row['path'] for row in rows}) == 299 and all(Path(row['path']).name != 'golden.tiff' for row in rows),
            'Duplicate or golden input')
    return rows, dict(developer=ref(receipt_path), completion=ref(PREPARED/'development-complete.json'),
        original_order_receipt=ref(PREPARED/'inputs.json'), original_raw_read=False, original_metadata_not_rechecked=True,
        original_hash_scope='Original SHA256 values come only from the pinned developer receipt; order receipt supplies path/bytes/mtime',
        input_format='299 full7032x4688 RGB16; unaligned, CAoff, same MHC/WB/matrix/tone',
        source_count=299, source_order='DSC00001.tiff through DSC00299.tiff', golden_excluded=True)


def binary():
    manifest = read(PROGRAM)
    require(manifest['schema'] == 1 and manifest['source_bundle_unchanged'] and manifest['no_installation']
            and manifest['additional_dependency'] == 'libprotobuf.dll' and len(manifest['files']) == 30,
            'Wrong staged runtime provenance')
    files = manifest['files']
    require(all(Path(row['path']).parent == BINARY.parent for row in files)
            and {Path(row['path']).name for row in files} == {p.name for p in BINARY.parent.iterdir()
                if p.suffix.lower() in ('.exe','.dll')}, 'Unbound staged executable/DLL')
    unchanged(files)
    common = manifest['all_original_common_binaries_exact']
    require(len(common) == 28 and all((row['original']['sha256'],row['original']['bytes']) ==
            (row['complete_cached']['sha256'],row['complete_cached']['bytes']) for row in common),
            'Original/common runtime identity differs')
    require(next(row['sha256'] for row in files if Path(row['path']).name == 'libprotobuf.dll') ==
            '36e7e36b191edf2ef74eb9063146b8b91c47b0c37dcdeb100b2562fb075657b1', 'Wrong missing dependency')
    common_names = {Path(row['original']['path']).name for row in common}
    require({Path(row['path']).name for row in files}-common_names == {'libprotobuf.dll','libprotoc.dll'}
            and next(row['sha256'] for row in files if Path(row['path']).name == 'libprotoc.dll') ==
            'c68420e9f91ec6fb257e162c5fd031584136035a098ebec2332dc0acd350b5b6', 'Wrong additional runtime files')
    row = ref(BINARY)
    require(row['sha256'] == BINARY_SHA, 'Pinned upstream executable differs')
    return row


def inventory(out):
    bindings = sources()
    save(out/'sources.json', bindings)
    executable = binary()
    # Root already ran these exact staged bytes under prepare-program.py's timeout.
    # Do not copy or execute them again merely to normalize stdout versus stderr.
    attempts = read(PROGRAM)['inventory']
    require([a['argument'] for a in attempts] == ['--version','--help'], 'Wrong retained inventory')
    version_text = attempts[0]['stdout']+attempts[0]['stderr']
    help_text = attempts[1]['stdout']+attempts[1]['stderr']
    require(attempts[0]['returncode'] == 0 and '1.3-42-g0cd289e' in version_text
            and '4.12.0' in version_text and attempts[1]['returncode'] == 1 and 'Usage:' in help_text,
            'Pinned runtime version/help health differs')
    required = [flag.split('=')[0] for flag in FLAGS]+['--output']
    flags_present = all(flag in help_text for flag in required)
    unchanged(bindings)
    require(binary() == executable, 'Upstream executable changed during inventory')
    save(out/'inventory.json', dict(schema=1, executable=executable, attempts=attempts, required_flags=required,
        required_flags_present=flags_present, inventory_passed=flags_present, program_manifest=ref(PROGRAM),
        inventory_execution='Retained root version/help calls;0/1 expected exits, combined stdout+stderr',
        no_image_inputs_supplied=True, complete_render_authorized_by_this_phase=False))


def checked_inventory(folder):
    data = read(folder/'inventory.json')
    require(data['inventory_passed'] and data['required_flags_present'] and data['executable'] == binary(),
            'Successful pinned binary version/help inventory required before full run')
    unchanged(read(folder/'sources.json'))
    require(data['program_manifest'] == ref(PROGRAM) and data['attempts'] == read(PROGRAM)['inventory'],
            'Retained runtime inventory changed')
    return ref(folder/'inventory.json')


def scan(rows, formats):
    import numpy as np
    import tifffile
    records = []
    for i, expected in enumerate(rows):
        path = Path(expected['path'])
        st = path.stat()
        actual = ref(path)
        require(actual == expected, f'Prepared TIFF content differs at ordinal{i}')
        if formats:
            with tifffile.TiffFile(path) as tif:
                require(len(tif.pages) == 1 and tif.pages[0].shape == (4688,7032,3)
                        and tif.pages[0].dtype == np.uint16
                        and hashlib.sha256(bytes(tif.pages[0].tags[34675].value)).hexdigest() == ICC_SHA,
                        'Prepared TIFF format/ICC differs')
        require((path.stat().st_size,path.stat().st_mtime_ns) == (st.st_size,st.st_mtime_ns), 'TIFF changed while scanned')
        records.append(dict(**actual,mtime_ns=st.st_mtime_ns))
        if (i+1)%50 == 0 or i == 298:
            print(f'Content verified{i+1}/299 prepared TIFFs',flush=True)
    return records


def views(master, out):
    import numpy as np
    import tifffile
    from PIL import Image
    with tifffile.TiffFile(master) as tif:
        require(len(tif.pages) == 1 and len(tif.pages[0].shape) == 3 and tif.pages[0].shape[2] == 3
                and tif.pages[0].dtype == np.uint8, 'Expected actual upstream8bit RGB TIFF')
        page = tif.pages[0]
        pixels = page.asarray()
        embedded = bytes(page.tags[34675].value) if 34675 in page.tags else None
    require(0 < pixels.shape[1] <= 7032 and 0 < pixels.shape[0] <= 4688, 'Unexpected upstream output canvas')
    # Missing ICC is labelled, not silently represented as embedded vendor metadata.
    image = Image.fromarray(pixels,'RGB')
    options = dict(icc_profile=embedded) if embedded else {}
    whole, overview = out/'whole.png',out/'overview.png'
    image.save(whole,**options)
    image.thumbnail((1800,1800),Image.Resampling.LANCZOS)
    image.save(overview,**options)
    with Image.open(whole) as check:
        require(check.size == (pixels.shape[1],pixels.shape[0])
                and np.array_equal(np.asarray(check),pixels), 'Whole PNG changed vendor pixels')
    return dict(master=ref(master),native_whole=ref(whole),overview=ref(overview),
        width=pixels.shape[1],height=pixels.shape[0],dtype='uint8',rgb8_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
        embedded_icc_sha256=hashlib.sha256(embedded).hexdigest() if embedded else None,
        display='No colour transform or tone adjustment; untagged if vendor omits ICC; overview only resized',
        geometry='Vendor default alignment and common-area crop; not the held native reference gauge')


def full(out, inventory_folder):
    checked = checked_inventory(inventory_folder)
    bindings = sources()
    save(out/'sources.json',bindings)
    executable = binary()
    rows, provenance = prepared()
    save(out/'prepared.json',dict(inputs=rows,**provenance))
    before = scan(rows,True)
    save(out/'inputs-before.json',before)
    master = out/'whole-stack.tiff'
    command = [str(BINARY),f'--output={master.relative_to(ROOT).as_posix()}',*FLAGS,
        *[Path(row['path']).relative_to(ROOT).as_posix() for row in rows]]
    command_chars = len(subprocess.list2cmdline(command))
    require(command_chars < 32760, 'Windows command line too long')
    save(out/'bindings.json',dict(executable=executable,inventory=checked,prepared=ref(out/'prepared.json'),
        command_chars=command_chars,settings=dict(threads=8,batchsize=4,opencl=False,
        whitebalance_correction=False,contrast_correction=False,alignment='stock default neighbour alignment',
        default_crop=True,other_defaults='unchanged pinned vendor defaults'),
        limits=dict(vendor_wall_seconds=900,vendor_cpu_seconds=18000,vendor_committed_bytes=24<<30),
        scope='External complete workflow reference,8bit output; not our CFA recipe, pure merge test or SOTA claim'))
    start = time.perf_counter()
    try:
        jobs.job(command,{},out,wall=900,cpu=18000,gib=24)
    finally:
        after = scan(rows,False)
        save(out/'inputs-after.json',after)
        require(after == before, 'Prepared TIFF content or metadata changed across vendor run')
        require(binary() == executable, 'Vendor binary changed')
        unchanged(bindings)
        require(prepared() == (rows,provenance), 'Prepared provenance changed')
    result = views(master,out)
    save(out/'output.json',dict(complete_299_source_reference=True,prepared_inputs_unchanged=True,
        before_after_fresh_content_hashes=299,original_raw_read=False,original_metadata_not_rechecked=True,
        elapsed_vendor_and_postcheck_seconds=time.perf_counter()-start,views=result,
        photographic_review='pending',quality_claim=False))
    (out/'images.md').write_text('\n\n'.join(['# Complete299-source stock upstream reference',
        'External8bit workflow with independent neighbour alignment and default crop; quality review pending.',
        f'[Complete vendor TIFF]({master.as_posix()})',f'[Native whole PNG]({(out/"whole.png").as_posix()})',
        f'![Whole-field overview]({(out/"overview.png").as_posix()})'])+'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('inventory','full'))
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--inventory',type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.parent == HERE and out != HERE, 'Fresh experiment-owned output required')
    out.mkdir(exist_ok=False)
    if args.phase == 'inventory':
        inventory(out)
    else:
        require(args.inventory is not None, 'Explicit successful inventory required')
        full(out,args.inventory.resolve())


if __name__ == '__main__':
    main()
