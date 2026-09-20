"""Root-owned sequential development and complete Helicon chip references."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OLD = ROOT/'experiments/quality-september19/vitamin-c-comparator-2'
NATIVE = ROOT/'experiments/ca-before-mhc/full-1/current/output'
HELICON = ROOT/'experiments/helicon-current/program/HeliconFocus.exe'
HELICON_SHA = '29ca62df122163c1295e1e2a416a42acfdf52f20c83d0beed99c4af154d42089'
EXAMPLE = ROOT/'crates/strehl-cli/examples/chip-batch-develop.rs'
spec = importlib.util.spec_from_file_location('chip_comparator_bounds', ROOT/'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def metadata(rows):
    for i, row in enumerate(rows):
        p = Path(row['path'])
        assert p.name == f'DSC{i+1:05d}.ARW'
        st = p.stat()
        assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])


def sources():
    paths = {Path(row['path']) for row in read(OLD/'build/sources.json')}
    paths.discard(ROOT/'crates/strehl-cli/examples/quality-batch-develop.rs')
    paths.update((EXAMPLE, Path(__file__).resolve(), HERE/'plan.md', HERE/'resource-evidence.json',
                  ROOT/'experiments/full-context-placement/run.py',
                  ROOT/'experiments/m193c-output-grid/bounded-process.py',
                  ROOT/'experiments/m12-scorecard/m12-harness.py'))
    for directory in ('crates/strehl-core/src', 'crates/strehl-raw/src', 'crates/strehl-plugin/src',
                      'experiments/native-gpu-gather/src'):
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file())
    # The retained optional GPU dependency now includes these out-of-tree files.
    paths.update(ROOT/'experiments/ca-before-mhc'/n for n in ('gpu.rs', 'prepass.wgsl'))
    return [c.ref(p.resolve()) for p in sorted(paths)]


def immutable(bindings):
    assert all(c.ref(Path(row['path'])) == row for row in bindings)


def job(command, fields, out, *, wall, cpu, gib):
    env, removed = c.b.clean_environment(fields.items())
    c.save(out/'invocation.json', dict(command=command, environment=fields, removed_environment=removed))
    api = c.b.load_job_api(c.b.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    result = c.b.run(command, env, ROOT, out/'process.log', api=api,
        wall_seconds=wall, cpu_seconds=cpu, committed_bytes=gib << 30, log_bytes=16 << 20)
    c.save(out/'process.json', result)
    print(json.dumps({k: result[k] for k in ('exit_code', 'error', 'wall_seconds')}), flush=True)
    assert result['exit_code'] == 0 and result['error'] is None
    assert result['terminal_job_accounting'] and not result['cleanup_errors']
    return result


def format_and_views(master, out, expected_icc):
    import numpy as np
    import tifffile
    from PIL import Image
    with tifffile.TiffFile(master) as tf:
        assert len(tf.pages) == 1
        page = tf.pages[0]
        assert page.shape == (4688, 7032, 3) and page.dtype == np.uint16, 'no trial-resolution/resize substitution'
        icc = bytes(page.tags[34675].value)
        assert icc == expected_icc
        pixels = page.asarray()
    pixel_hash = hashlib.sha256(pixels.astype('<u2', copy=False).tobytes()).hexdigest()
    image = Image.fromarray(((pixels.astype(np.uint32)+128)//257).astype(np.uint8), 'RGB')
    whole, overview = out/'whole.png', out/'overview.png'
    image.save(whole, icc_profile=icc)
    image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    image.save(overview, icc_profile=icc)
    for p in (whole, overview):
        with Image.open(p) as check:
            assert check.info.get('icc_profile') == icc
    return dict(master=c.ref(master), native_whole=c.ref(whole), overview=c.ref(overview),
        rgb16_le_sha256=pixel_hash, icc_sha256=hashlib.sha256(icc).hexdigest(),
        display='round(u16/257); same sRGB ICC; overview only resized',
        watermark_visual_review='pending; dimensions alone do not prove absence')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=('build', 'develop', 'b', 'c'))
    p.add_argument('--out', type=Path, default=HERE/'run-1')
    args = p.parse_args()
    out = args.out.resolve()
    assert out.parent == HERE and out.name.startswith('run-')
    inputs = read(ROOT/'experiments/quality-september14/chip-baseline-1/invocation.json')['inputs']
    assert len(inputs) == 299
    input_dir = Path(inputs[0]['path']).parent
    assert input_dir.name == 'uncapped-IC-chip-cpl'
    assert sorted(p.name for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == '.arw') == [f'DSC{i:05d}.ARW' for i in range(1, 300)]
    metadata(inputs)
    assert c.ref(HELICON)['sha256'] == HELICON_SHA
    native_receipt = read(NATIVE/'receipt.json')
    assert native_receipt['source_count'] == 299 and native_receipt['mode'] == 'off'
    assert native_receipt['tone_bits'] == [999074891, 1064454645, 1057803469]
    assert native_receipt['wb_bits'] == [1070374912, 1065353216, 1076715520]
    if args.stage == 'build':
        assert shutil.disk_usage(HERE).free >= 80 << 30, 'reserve80GiB before development'
        out.mkdir(exist_ok=False)
        build = out/'build'
        build.mkdir()
        EXAMPLE.touch()  # Force the new example's source rebuild, not a cached-test claim.
        bound = sources()
        c.save(build/'sources.json', bound)
        c.save(out/'inputs.json', inputs)
        c.save(out/'bindings.json', dict(native_receipt=c.ref(NATIVE/'receipt.json'),
            native_master=c.ref(NATIVE/'image.tiff'), helicon=c.ref(HELICON),
            resource_evidence=c.ref(HERE/'resource-evidence.json'),
            old_exporter=c.ref(ROOT/'crates/strehl-cli/examples/quality-batch-develop.rs'),
            old_export_build=c.ref(OLD/'build/executable.json'), free_bytes=shutil.disk_usage(HERE).free))
        command = ['cargo', 'build', '-p', 'strehl-cli', '--example', 'chip-batch-develop', '--release',
            '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes', '--jobs', '2',
            '--target-dir', str(ROOT/'target/native-pyramid-profile'), '--locked', '--offline',
            '--message-format=json-render-diagnostics']
        job(command, {'RAYON_NUM_THREADS': '8', 'CARGO_INCREMENTAL': '0'}, build, wall=600, cpu=1800, gib=8)
        log = (build/'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        artifacts = []
        for line in log.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'chip-batch-develop':
                artifacts.append(row['executable'])
        assert len(artifacts) == 1
        exe = build/'chip-batch-develop.exe'
        shutil.copyfile(artifacts[0], exe)
        immutable(bound)
        metadata(inputs)
        c.save(build/'executable.json', c.ref(exe))
        return
    build = out/'build'
    bound = read(build/'sources.json')
    immutable(bound)
    fixed = read(out/'bindings.json')
    for key in ('native_receipt', 'native_master', 'helicon', 'resource_evidence', 'old_exporter', 'old_export_build'):
        assert c.ref(Path(fixed[key]['path'])) == fixed[key]
    assert read(out/'inputs.json') == inputs
    binary = read(build/'executable.json')
    assert c.ref(Path(binary['path'])) == binary
    if args.stage == 'develop':
        assert shutil.disk_usage(out).free >= 80 << 30, 'reserve80GiB before299 TIFF export'
        stage = out/'development'
        stage.mkdir(exist_ok=False)
        config = dict(inputs=[r['path'] for r in inputs], input_dir=str(input_dir), out=str(out/'developed'),
            tone=[.004293, .946441, .55], expected_xyz_to_cam=native_receipt['matrix'],
            fixture_dir=str(ROOT/'experiments/quality-september19/star-matched-source-1/output'),
            fixture_original_u16=str(ROOT/'experiments/quality-september19/star-porous-translation-1/porous-grain/rawler-129.bin'))
        c.save(stage/'config.json', config)
        job([binary['path'], str(stage/'config.json')], {'RAYON_NUM_THREADS': '8'}, stage, wall=600, cpu=2400, gib=3)
        receipt = read(out/'developed/receipt.json')
        assert receipt['status'] == '299_UNALIGNED_NATIVE_RGB16_DEVELOPED' and len(receipt['frames']) == 299
        assert receipt['golden']['differing'] == receipt['golden']['normalized_f32_differences'] == 0
        assert receipt['wb_bits'] == native_receipt['wb_bits'] and receipt['tone_bits'] == native_receipt['tone_bits']
        import tifffile
        with tifffile.TiffFile(NATIVE/'image.tiff') as tf:
            expected_icc = bytes(tf.pages[0].tags[34675].value)
        for i, row in enumerate(receipt['frames']):
            tiff = Path(row['output'])
            assert tiff == out/'developed'/f'DSC{i+1:05d}.tiff'
            with tifffile.TiffFile(tiff) as tf:
                assert len(tf.pages) == 1 and tf.pages[0].shape == (4688, 7032, 3)
                assert str(tf.pages[0].dtype) == 'uint16' and bytes(tf.pages[0].tags[34675].value) == expected_icc
        metadata(inputs)
        immutable(bound)
        c.save(out/'development-complete.json', dict(receipt=c.ref(out/'developed/receipt.json'), source_count=299,
            original_metadata_unchanged=True, all_formats_and_icc_checked=True,
            ca_policy='no CA or alignment applied to prepared TIFFs; native current has held CA',
            scope='same decoder/MHC/WB/matrix/tone; external tone-before-merge and independent geometry'))
        return
    assert read(out/'development-complete.json')['source_count'] == 299
    receipt_path = out/'developed/receipt.json'
    assert c.ref(receipt_path) == read(out/'development-complete.json')['receipt']
    receipt = read(receipt_path)
    prepared = [Path(row['output']) for row in receipt['frames']]
    assert len(prepared) == 299 and [p.stem for p in prepared] == [f'DSC{i:05d}' for i in range(1, 300)]
    expected = [dict(path=str(p), sha256=row['output_sha256'], bytes=row['output_bytes']) for p, row in zip(prepared, receipt['frames'])]
    immutable(expected)  # Explicit list excludes golden.tiff.
    admission = read(HERE/'resource-evidence.json')
    assert admission['root_approved_bounded_attempt'] and admission['external_job_gib'] == 40
    if args.stage == 'c':
        # No automatic C retry after a B resource failure; root must reassess separately.
        assert read(out/'helicon-b/output.json')['complete_299_source_reference']
    assert shutil.disk_usage(out).free >= 20 << 30
    stage = out/f'helicon-{args.stage}'
    stage.mkdir(exist_ok=False)
    manifest = stage/'inputs.txt'
    manifest.write_text('\n'.join(str(p) for p in prepared)+'\n', encoding='utf-8')
    master = stage/'whole-stack.tiff'
    command = [str(HELICON), '-silent', '-noprogress', '-i', str(manifest),
        '-mp:'+{'b': '1', 'c': '2'}[args.stage], *(['-rp:8'] if args.stage == 'b' else []),
        '-sp:4', '-sort:asc', '-tif:u', '-save:'+str(master), '-o', str(stage/'saved-outputs.txt')]
    c.save(stage/'bindings.json', dict(executable=c.ref(HELICON), inputs=expected, manifest=c.ref(manifest),
        development_receipt=c.ref(receipt_path), resource_admission=admission,
        settings=dict(method=args.stage, radius=8 if args.stage == 'b' else 'inactive', smoothing=4,
                      order='ascending', other_alignment_brightness_interpolation_state='unchanged application state; not recovered')))
    try:
        job(command, {}, stage, wall=600, cpu=12000, gib=40)
    finally:
        after = [c.ref(p) for p in prepared]
        c.save(stage/'inputs-after.json', after)
        assert after == expected
        metadata(inputs)
        immutable(bound)
        assert c.ref(HELICON)['sha256'] == HELICON_SHA
    import tifffile
    with tifffile.TiffFile(NATIVE/'image.tiff') as tf:
        expected_icc = bytes(tf.pages[0].tags[34675].value)
    view = format_and_views(master, stage, expected_icc)
    c.save(stage/'output.json', dict(complete_299_source_reference=True, prepared_inputs_unchanged=True,
        original_metadata_unchanged=True, views=view, photographic_review='pending', quality_claim=False))
    (stage/'images.md').write_text('\n\n'.join([
        f'# Complete299-frame Helicon {args.stage.upper()} chip reference',
        f'[RGB16 master]({master.as_posix()})', f'[Native whole image]({(stage/"whole.png").as_posix()})',
        f'![Whole-field overview only]({(stage/"overview.png").as_posix()})',
        f'[Native Current master]({(NATIVE/"image.tiff").as_posix()})'])+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
