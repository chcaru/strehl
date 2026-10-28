"""Complete held-tone GPU dual-tree displays; saved outputs only, no RAW or fitting."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / 'experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json'
MANIFEST_SHA = '826c4ab6c620122449f6575cdd18c0f9ee9cb460f29f6d895e832325d6405888'
WIDTH, HEIGHT = 6896, 4596
CROP = [34, 23, 3448, 2298]
ARMS = ('baseline', 'candidate', 'uniform')


def ref(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4 << 20):
            digest.update(block)
    stat = path.stat()
    return dict(path=str(path), sha256=digest.hexdigest(), bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def check_bound(bound):
    actual = ref(bound['path'])
    assert actual['sha256'] == bound['sha256'] and actual['bytes'] == bound['bytes']
    return Path(actual['path'])


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    source, out = args.input.resolve(), args.out.resolve()
    assert source.is_dir() and source.is_relative_to(ROOT / 'outputs')
    assert out.is_relative_to(ROOT / 'outputs') and not out.exists() and not out.is_relative_to(source)
    assert source.name == 'output' and sys.byteorder == 'little'
    completion_path, process_path = source.parent / 'completion.json', source.parent / 'process.json'
    completion, process = read_json(completion_path), read_json(process_path)
    assert completion['mode'] == 'full' and completion['source_bindings_unchanged'] is True
    assert completion['photographic_improvement_claimed'] is False and completion['expected_test_count'] == 1
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    assert not process['cleanup_errors'] and process['direct_exit_observed'] and process['pipe_eof_observed']
    paths = [Path(__file__).resolve(), MANIFEST, completion_path, process_path]
    report_paths = [check_bound(bound) for bound in completion['reports']]
    receipt_path = source / 'receipt.json'
    assert receipt_path in report_paths
    paths.extend(report_paths)
    paths.extend(check_bound(bound) for bound in completion['worker_receipts'])
    assert len(completion['worker_receipts']) == 2, 'one completed full299 GPU worker required'
    workers = []
    for bound in completion['worker_receipts']:
        worker = read_json(Path(bound['path']))
        assert worker['complete'] is True and worker['source_count'] == 299
        assert worker['source_ids'] == list(range(299)) and worker['device_limit_bytes'] == 24 << 30
        if worker['status'] == 'COMPLETE_DUAL_TREE_CUDA_WORKER':
            assert worker['backend'] == 'torch-cuda-f32'
            assert 0 < worker['peak_allocated_bytes'] <= worker['peak_reserved_bytes'] <= 24 << 30
        else:
            assert worker['status'] == 'COMPLETE_DUAL_TREE_CUDA_BRIDGE'
            assert worker['child_exit_code'] == 0 and worker['parent_in_job'] and worker['child_in_job']
            assert worker['bindings_unchanged'] and worker['probe_draws_total'] == 16 * 299
        workers.append(worker)
    assert {v['status'] for v in workers} == {'COMPLETE_DUAL_TREE_CUDA_WORKER', 'COMPLETE_DUAL_TREE_CUDA_BRIDGE'}
    receipt = read_json(receipt_path)
    assert receipt['status'] == 'COMPLETE299_DUAL_TREE_DIAGNOSTIC' and receipt['mechanical_pass'] is True
    assert receipt['source_count'] == 299 and receipt['noise_probe_draws'] == 16
    assert receipt['native_dimensions'] == [WIDTH, HEIGHT] and receipt['crop_quad'] == CROP and receipt['reference'] == 149
    for key in ('admission', 'quality_claim', 'photographic_admission'):
        assert receipt[key] is False
    for key in ('input_preservation', 'all299_metadata_unchanged', 'processed_original_contents_unchanged',
                'all299_contents_reread', 'baseline_pixel_golden_exact'):
        assert receipt[key] is True, key
    assert receipt['baseline_identity']['exact'] and receipt['baseline_identity']['material_metadata_exact']
    assert receipt['uniform_transform_null']['pass'] and receipt['uniform_transform_null']['before_hull']
    assert receipt['candidate_evidence']['source_ids'] == list(range(299))
    assert receipt['candidate_evidence']['source_count'] == 299
    assert [row['index'] for row in receipt['frame_receipts']] == list(range(299))
    assert all(row['probe']['probe_draws'] == 16 and row['probe']['source_index'] == row['index']
               for row in receipt['frame_receipts'])
    assert ref(MANIFEST)['sha256'] == MANIFEST_SHA
    frozen = read_json(MANIFEST)
    assert len(frozen['witnesses']) == 10 and frozen['source_crop_quad_xywh'] == CROP
    assert frozen['complete_rgb16_dimensions'] == [WIDTH, HEIGHT]
    assert [row['name'] for row in receipt['arms']] == list(ARMS)
    assert len(receipt['pixel_hashes']) == len(receipt['material_metadata']) == 3
    assert receipt['material_metadata'][0] == receipt['material_metadata'][1] == receipt['material_metadata'][2]
    files = {}
    for arm, row in zip(ARMS, receipt['arms']):
        assert row['entire_output'] is True
        files[arm] = {}
        for kind in ('cfa', 'rgb16', 'linear_rgb32'):
            path = check_bound(row[kind])
            assert path.parent == source
            paths.append(path)
            files[arm][kind] = path
        assert files[arm]['cfa'].stat().st_size == WIDTH * HEIGHT * 4
    paths = list(dict.fromkeys(paths))
    before = [ref(path) for path in paths]
    out.mkdir()
    records, common_icc = [], None
    for ordinal, arm in enumerate(ARMS):
        dest = out / arm
        dest.mkdir()
        material = receipt['material_metadata'][ordinal]
        with tifffile.TiffFile(files[arm]['linear_rgb32']) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.float32
            assert tif.pages[0].shape == (HEIGHT, WIDTH, 3)
            linear_icc = bytes(tif.pages[0].tags[34675].value)
            assert hashlib.sha256(linear_icc).hexdigest() == material['linear_rgb32']['icc_sha256']
            assert tif.pages[0].description == material['linear_rgb32']['description']
            linear = tif.asarray()
        assert linear.flags.c_contiguous
        linear_pixels = hashlib.sha256(memoryview(linear).cast('B')).hexdigest()
        assert linear_pixels == receipt['pixel_hashes'][ordinal]['linear_rgb32']
        del linear
        with tifffile.TiffFile(files[arm]['rgb16']) as tif:
            assert len(tif.pages) == 1 and tif.pages[0].dtype == np.uint16
            assert tif.pages[0].shape == (HEIGHT, WIDTH, 3)
            icc = bytes(tif.pages[0].tags[34675].value)
            assert tif.pages[0].description == material['rgb16']['description']
            rgb = tif.asarray()
        assert icc and rgb.flags.c_contiguous
        assert hashlib.sha256(icc).hexdigest() == material['rgb16']['icc_sha256'] == frozen['icc_sha256']
        if common_icc is None:
            common_icc = icc
        assert common_icc == icc
        pixels = hashlib.sha256(memoryview(rgb).cast('B')).hexdigest()
        assert pixels == receipt['pixel_hashes'][ordinal]['rgb16']
        rgb8 = ((rgb.astype(np.uint32) + 128) // 257).astype(np.uint8)
        whole = Image.fromarray(rgb8)
        full = dest / 'complete-stack.jpg'
        whole.save(full, quality=98, subsampling=0, icc_profile=icc)
        with Image.open(full) as check:
            assert check.size == (WIDTH, HEIGHT) and check.info.get('icc_profile') == icc
        whole.thumbnail((1617, 1617), Image.Resampling.LANCZOS)
        overview = dest / 'overview.jpg'
        whole.save(overview, quality=98, subsampling=0, icc_profile=icc)
        crops = []
        for witness in frozen['witnesses']:
            x, y, width, height = witness['rect_xywh']
            assert width == height == 384 and 0 <= x <= WIDTH-width and 0 <= y <= HEIGHT-height
            crop = rgb[y:y+height, x:x+width].copy()
            crop8 = rgb8[y:y+height, x:x+width].copy()
            png, tiff = dest / (witness['name']+'.png'), dest / (witness['name']+'.tiff')
            Image.fromarray(crop8).save(png, icc_profile=icc)
            tifffile.imwrite(tiff, crop, photometric='rgb', metadata=None,
                             extratags=[(34675, 'B', len(icc), icc, False)])
            with tifffile.TiffFile(tiff) as check:
                assert np.array_equal(check.asarray(), crop) and bytes(check.pages[0].tags[34675].value) == icc
            with Image.open(png) as check:
                assert np.array_equal(np.asarray(check), crop8) and check.info.get('icc_profile') == icc
            crops.append(dict(name=witness['name'], native_xywh=[x, y, width, height],
                              exact=True, resampled=False, png=ref(png), tiff=ref(tiff)))
        records.append(dict(arm=arm, master=ref(files[arm]['rgb16']), linear_master=ref(files[arm]['linear_rgb32']),
                            cfa_master=ref(files[arm]['cfa']), full_jpeg=ref(full), overview=ref(overview),
                            rgb16_pixels_sha256=pixels, linear_rgb32_pixels_sha256=linear_pixels, crops=crops))
        del rgb, rgb8, whole
    assert [ref(path) for path in paths] == before, 'bound saved output changed during display export'
    lines = ['# Complete dual-tree GPU observation: no verdict', '',
             'All three complete outputs retain the held writer tone and ICC. Overviews are for orientation; inspect all ten native witnesses after whole images.', '']
    for row in records:
        lines += [f"## {row['arm']}", '',
                  f"![Complete {row['arm']} overview]({Path(row['overview']['path']).as_posix()})", '',
                  f"[Complete-resolution JPEG]({Path(row['full_jpeg']['path']).as_posix()}) · "
                  f"[RGB16 master]({Path(row['master']['path']).as_posix()}) · "
                  f"[Linear RGB32 master]({Path(row['linear_master']['path']).as_posix()}) · "
                  f"[Native CFA master]({Path(row['cfa_master']['path']).as_posix()})", '']
    with (out / 'index.md').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines).rstrip()+'\n')
    result = dict(status='THREE_COMPLETE_DUAL_TREE_GPU_DISPLAYS_READY_NO_VERDICT', command=sys.argv,
                  seconds=time.monotonic()-started, inputs=before, inputs_unchanged=True, arms=records,
                  admission=False, photographic_improvement_claimed=False, RAW_reads=0,
                  source_full_receipt=ref(receipt_path), source_successful_completion=ref(completion_path),
                  native_dimensions=[WIDTH, HEIGHT], crop_quad=CROP, active_native_origin=[68, 46], reference=149,
                  index=ref(out / 'index.md'),
                  display='Held RGB16; (value+128)//257; same original ICC. No retone, new rendering, sharpening or fit.',
                  scope='Complete RGB16/linear/CFA masters linked; full-resolution JPEG; overview only resized; all ten frozen384 witnesses exact.')
    save(out / 'display-receipt.json', result)
    print(json.dumps(dict(status=result['status'], seconds=result['seconds'], receipt=ref(out / 'display-receipt.json'))))


if __name__ == '__main__':
    main()
