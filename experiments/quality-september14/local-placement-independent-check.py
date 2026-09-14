"""Saved-output audit only: no consumer execution or original RAW reads."""
from pathlib import Path
import hashlib
import json
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
OUT = HERE / 'local-placement-consumer-1'
receipt = json.loads((OUT / 'receipt.json').read_text())
manifest_path = HERE / 'local-placement-consumer-inputs-1/manifest.json'
manifest = json.loads(manifest_path.read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(manifest_path) == receipt['input_manifest_sha256']
assert receipt['frames'] == [146, 147, 148, 149, 150, 151, 152, 153]
assert [f['index'] for f in manifest['frames']] == receipt['frames']
assert receipt['reference'] == manifest['reference_index'] == 149
assert receipt['full_quad_geometry'] == [3516, 2344]
assert receipt['crop_quad_xywh'] == [666, 552, 196, 196]
assert receipt['level_sides'] == [196, 98, 49, 25, 13]
assert receipt['actual_laplacian_bands'] == 4
for source, support in zip(manifest['frames'], receipt['support']):
    assert source['index'] == support['frame']
    assert source['source'] == support['source']
    assert source['source_xywh'] == support['retained']
    assert source['delta_source_native'] == support['delta_source_native']
    assert support['identity_model'] == 'ILCE-7CM2'
    assert support['identity_lens_type3'] == 33094
    assert 'eps_r: -0.0005084' in support['ca'] and 'eps_b: Some(0.0001744)' in support['ca']
    assert len(support['stencils']) == 6
    x, y, w, h = support['retained']
    for stencil in support['stencils']:
        left, top, right, bottom = stencil['inclusive_source_bounds']
        assert x <= left <= right < x+w and y <= top <= bottom < y+h

# Deliberately asymmetric odd-origin region, different from the viewing trim.
# Address samples by global CFA parity, rather than the writer's slot formula.
x, y, w, h = 73, 91, 117, 83
yy, xx = np.mgrid[y:y+h, x:x+w]
plane_index = np.where((1104+yy) % 2 == 0,
                       np.where((1332+xx) % 2 == 0, 0, 1),
                       np.where((1332+xx) % 2 == 0, 2, 3))
wb = np.asarray(manifest['wb_bits'], dtype=np.uint32).view(np.float32)
gain = np.asarray([wb[0], wb[1], wb[1], wb[2]], dtype=np.float32)
rows = []
collapsed = {}
for arm in ('original', 'corrected'):
    result = {'arm': arm, 'hashes': {}}
    for suffix in ('collapsed-planes.f32', 'cfa.f32', 'mhc-camera-rgb.f32',
                   'camera-linear.tiff', 'interleave-control.tiff', 'product.tiff'):
        black = OUT / f'{arm}-black-{suffix}'
        white = OUT / f'{arm}-white-{suffix}'
        assert black.read_bytes() == white.read_bytes(), (arm, suffix)
        result['hashes'][suffix] = digest(black)
    record = next(r['output'] for r in receipt['outputs'] if r['output']['arm'] == arm+'-black')
    assert result['hashes']['collapsed-planes.f32'] == record['collapsed_sha256']
    assert result['hashes']['camera-linear.tiff'] == record['linear_tiff_sha256']
    assert result['hashes']['product.tiff'] == record['product_tiff_sha256']
    assert (OUT/f'{arm}-black-camera-linear.tiff').read_bytes() == (OUT/f'{arm}-black-interleave-control.tiff').read_bytes()
    planes = np.fromfile(OUT/f'{arm}-black-collapsed-planes.f32', '<f4').reshape(4,196,196)
    collapsed[arm] = planes.view(np.uint32)
    cfa = np.fromfile(OUT/f'{arm}-black-cfa.f32', '<f4').reshape(392,392)
    expected = (np.maximum(planes[plane_index, yy//2, xx//2], np.float32(0))*gain[plane_index])/np.float32(15360-512)
    actual = cfa[y:y+h,x:x+w]
    assert np.array_equal(expected.view(np.uint32), actual.view(np.uint32))
    wrong_index = np.asarray([0,2,1,3])[plane_index]
    wrong = (np.maximum(planes[wrong_index, yy//2, xx//2], np.float32(0))*gain[wrong_index])/np.float32(15360-512)
    mismatch = int(np.count_nonzero(wrong.view(np.uint32) != actual.view(np.uint32)))
    assert mismatch > 0, 'green-plane exchange destroyer has no power'
    product = tifffile.imread(OUT/f'{arm}-black-product.tiff')
    white = tifffile.imread(OUT/f'{arm}-white-product.tiff')
    assert product.shape == (392,392,3) and product.dtype == np.uint16
    assert np.array_equal(product[y:y+h,x:x+w], white[y:y+h,x:x+w])
    wrong_crop = product[x:x+h,y:y+w]
    assert not np.array_equal(product[y:y+h,x:x+w], wrong_crop)
    result.update(cfa_region_words_exact=int(actual.size), swapped_green_plane_mismatches=mismatch,
                  swapped_xy_region_rejected=True)
    rows.append(result)
changed = int(np.count_nonzero(collapsed['original'] != collapsed['corrected']))
assert changed == receipt['changed_collapsed_f32_words'] == 153322
process = json.loads((HERE/'local-placement-actual-1-process.json').read_text())
assert process['exit_code'] == 0 and process['error'] is None and not process['cleanup_errors']
assert process['terminal_job_accounting'] and process['job_accounting']['active_processes'] == 0
result = dict(status='SAVED_OUTPUT_AUDIT_PASS', command='python -I -B experiments/quality-september14/local-placement-independent-check.py',
              script_sha256=digest(Path(__file__)), receipt_sha256=digest(OUT/'receipt.json'),
              region_native_xywh=[x,y,w,h], all_black_white_artifacts_byte_exact=True,
              changed_collapsed_f32_words=changed, rows=rows,
              wall_seconds=process['wall_seconds'], child_cpu_seconds=process['job_accounting']['total_cpu_100ns']/1e7,
              scope='Saved artifacts only; no RAW decode, reconstruction, quality metric, or speed comparison.')
with (HERE/'local-placement-consumer-independent-runtime.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
