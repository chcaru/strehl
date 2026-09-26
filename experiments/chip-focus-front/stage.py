"""Fixed sparse toned-RGB extraction. Root executes; no RAW or full aligned volume."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEVELOPED = ROOT / 'experiments/chip-competitor/run-1/developed'
DEVELOPMENT_COMPLETE = DEVELOPED.parent / 'development-complete.json'
AFTER = DEVELOPED.parent / 'helicon-c/inputs-after.json'
INPUT_ORDER = ROOT / 'outputs/quality-september25/chip-fixed/input-order.json'
WARP = ROOT / 'experiments/quality-september14/chip-baseline-1/chip.warpmap.txt'
TARGETS = ROOT / 'experiments/chip-stock-selectivity/targets.json'
WARP_SHA = 'ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922'
RECEIPT_SHA = '97f198664496c18ebb7723450e240163983cf00a5499e1db0695bdd0f4c3bf9c'
ICC_SHA = '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
X_GRID = [500, 1600, 2700, 3800, 4900, 6000]
Y_GRID = [350, 1070, 1790, 2510, 3230, 3950]
NAMED = [('rail-crossing', 1290, 1150), ('upper-colour', 1292, 452),
         ('central-stipple', 3232, 1562), ('lower-array', 822, 3052),
         ('lower-colour', 4922, 3272), ('surface-scratches', 5112, 1512),
         ('upper-left-contact-grid', 304, 592)]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ref(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def map_native(points, transform, crop_xy=(133, 89), centre_native=(3516, 2344)):
    import numpy as np
    p = np.asarray(points, dtype=np.float64)
    require(p.shape[-1] == 2 and len(transform) == 4, 'Point/transform shape')
    ar, ai, br, bi = transform
    require(np.isfinite(p).all() and np.isfinite(transform).all() and ar*ar+ai*ai > 0, 'Invalid mapping')
    dx = p[..., 0] + 2*crop_xy[0] - centre_native[0]
    dy = p[..., 1] + 2*crop_xy[1] - centre_native[1]
    return np.stack((centre_native[0] + ar*dx - ai*dy + 2*br,
                     centre_native[1] + ai*dx + ar*dy + 2*bi), axis=-1)


def source_rectangle(positions):
    import numpy as np
    require(np.isfinite(positions).all(), 'Nonfinite source coordinates')
    floor = np.floor(positions)
    # Cubic uses floor-1 through floor+2. Upper bounds are exclusive.
    return [int(floor[..., 0].min())-1, int(floor[..., 1].min())-1,
            int(floor[..., 0].max())+3, int(floor[..., 1].max())+3]


def sample_rgb(image, positions):
    import cv2
    import numpy as np
    require(image.ndim == 3 and image.shape[2] == 3 and image.dtype == np.uint16, 'Expected RGB16 source')
    points = np.asarray(positions, dtype=np.float64)
    require(points.ndim == 3 and points.shape[2] == 2, 'Expected spatial coordinate grid')
    x0, y0, x1, y1 = source_rectangle(points)
    require(0 <= x0 < x1 <= image.shape[1] and 0 <= y0 < y1 <= image.shape[0], 'Untrusted source support')
    local = np.array(image[y0:y1, x0:x1], dtype=np.float32, copy=True) / np.float32(65535)
    px = np.asarray(points[..., 0]-x0, dtype=np.float32)
    py = np.asarray(points[..., 1]-y0, dtype=np.float32)
    result = cv2.remap(local, px, py, interpolation=cv2.INTER_CUBIC,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    require(result.dtype == np.float32 and np.isfinite(result).all(), 'Nonfinite sample')
    return result


_KERNELS = None


def band_power(luma):
    import cv2
    import numpy as np
    global _KERNELS
    require(luma.shape == (192, 192) and luma.dtype == np.float32 and np.isfinite(luma).all(), 'Expected finite f32 spatial192 luma')
    if _KERNELS is None:
        _KERNELS = {s: cv2.getGaussianKernel(8*s+1, s, cv2.CV_32F) for s in (1, 2, 4, 8)}
    blurred = {s: cv2.sepFilter2D(luma, cv2.CV_32F, k, k, borderType=cv2.BORDER_REPLICATE)
               for s, k in _KERNELS.items()}
    values = []
    for a, b in ((1, 2), (4, 8)):
        band = blurred[a][32:160, 32:160] - blurred[b][32:160, 32:160]
        values.append(np.mean(band * band, dtype=np.float32))
    result = np.asarray(values, dtype=np.float32)
    require(np.isfinite(result).all() and (result >= 0).all(), 'Invalid band power')
    return result


def grid():
    rows = []
    for r, y in enumerate(Y_GRID):
        for c, x in enumerate(X_GRID):
            if (r, c) == (4, 4):
                continue
            rows.append(dict(name=f'grid-r{r}-c{c}', xy_native=[x, y], grid_row=r, grid_col=c,
                             is_target=False, train=(r//2+c//2) % 2 == 0))
    rows.extend(dict(name=name, xy_native=[x, y], grid_row=-1, grid_col=-1, is_target=True, train=False)
                for name, x, y in NAMED)
    require(len(rows) == 42 and sum(r['train'] for r in rows) == 19, 'Frozen spatial split')
    for i, a in enumerate(rows):
        x, y = a['xy_native']
        require(0 <= x-96 and x+96 <= 6500 and 0 <= y-96 and y+96 <= 4332, 'Patch outside delivered output')
        for b in rows[:i]:
            bx, by = b['xy_native']
            require(abs(x-bx) >= 192 or abs(y-by) >= 192, 'Overlapping192 native supports')
    return rows


def plan():
    import numpy as np
    require(sha(WARP) == WARP_SHA, 'Changed held map')
    lines = WARP.read_text(encoding='utf-8').splitlines()
    for header in ('frames 299', 'reference 149', 'plane 3516x2344', 'stack-name uncapped-IC-chip-cpl'):
        require(header in lines, f'Wrong map header: {header}')
    transforms, bits = {}, {}
    for line in lines:
        fields = line.split()
        if fields and fields[0].isdigit():
            require(len(fields) >= 6 and fields[1] == 'placed', 'Unplaced/incomplete source')
            i = int(fields[0])
            require(i not in transforms, 'Duplicate source ordinal')
            bits[i] = fields[2:6]
            transforms[i] = [struct.unpack('>d', bytes.fromhex(v))[0] for v in bits[i]]
    require(set(transforms) == set(range(299)), 'Missing/extra source ordinal')
    ar, ai, br, bi = transforms[149]
    # Stored gauge normalization has f64 roundoff. Preserve its exact map values.
    # This bounds displacement from identity throughout the active native domain.
    reference_residual_bound = float(np.hypot(ar-1.0, ai)*np.hypot(3516, 2344)
                                     + 2*np.hypot(br, bi))
    require(np.isfinite(reference_residual_bound) and reference_residual_bound <= 1e-9,
            'Reference gauge differs by more than1e-9 native pixel')
    targets = read(TARGETS)
    require(targets['native_size'] == [6500, 4332] and targets['crop'] == [133, 89, 3250, 2166], 'Target output gauge')
    derived = [(r['name'], r['native_xywh'][0]+r['native_xywh'][2]//2,
                r['native_xywh'][1]+r['native_xywh'][3]//2) for r in targets['regions']]
    require(derived == NAMED, 'Changed independently frozen target centres')
    patches = grid()
    frames = []
    corner_delta = np.array([[-96, -96], [95, -96], [-96, 95], [95, 95]], dtype=np.float64)
    for i in range(299):
        supports = []
        for patch in patches:
            points = map_native(corner_delta + np.array(patch['xy_native']), transforms[i])
            x0, y0, x1, y1 = source_rectangle(points)
            require(0 <= x0 < x1 <= 7032 and 0 <= y0 < y1 <= 4688, f'Source{i} patch{patch["name"]} unsupported')
            supports.append([x0, y0, x1, y1])
        frames.append(dict(ordinal=i, transform=transforms[i], transform_bits=bits[i], source_rectangles_xyxy=supports))
    return dict(schema=1, patches=patches, frames=frames, source_ordinals=list(range(299)),
                native_size=[6500, 4332], crop_quad=[133, 89, 3250, 2166], reference_ordinal=149,
                source_native_size=[7032, 4688], centre_native=[3516, 2344],
                support_native=192, core_native=128, gaussian_sigmas=[1, 2, 4, 8], gaussian_radius_sigma=4,
                bands=[[1, 2], [4, 8]], statistic='mean squared2D spatialDoG in central128²; f32',
                luma_weights=[0.2126, 0.7152, 0.0722], sampler='OpenCV INTER_CUBIC, A=-.75, phase table1/32',
                train_sites=19, heldout_sites=23, warp=ref(WARP), targets=ref(TARGETS),
                support_preflight_all_299=True, spatial192_supports_disjoint=True,
                reference_transform=transforms[149], reference_transform_bits=bits[149],
                reference_identity_residual_bound_native=reference_residual_bound,
                reference_identity_residual_limit_native=1e-9,
                reference_transform_replaced=False)


def stage_controls():
    path = HERE / 'independent-controls.py'
    spec = importlib.util.spec_from_file_location('chip_focus_front_independent_stage_controls', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.stage_controls(sys.modules[__name__])


def extract(out):
    start = time.perf_counter()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[key] = '8'
    import cv2
    import numpy as np
    import tifffile
    cv2.setNumThreads(8)
    # Generated addressing and constant controls precede every photographic open.
    controls = stage_controls()
    save(out / 'stage-controls.json', controls)
    design = plan()
    save(out / 'plan.json', design)
    receipt_path = DEVELOPED / 'receipt.json'
    require(sha(receipt_path) == RECEIPT_SHA and read(DEVELOPMENT_COMPLETE)['receipt'] == ref(receipt_path), 'Changed developer receipt')
    prior = read(receipt_path)
    require(prior['status'] == '299_UNALIGNED_NATIVE_RGB16_DEVELOPED' and len(prior['frames']) == 299, 'Incomplete prepared stack')
    require(prior['golden']['differing'] == prior['golden']['normalized_f32_differences'] == 0, 'Developer commissioning absent')
    prior_hashes = read(AFTER)
    require(len(prior_hashes) == 299, 'Incomplete retained input-after hashes')
    order = read(INPUT_ORDER)
    if isinstance(order, dict):
        order = order['inputs']
    require(len(order) == 299, 'Incomplete current source order')
    file_stats = []
    for i, (row, previous, source) in enumerate(zip(prior['frames'], prior_hashes, order)):
        path = DEVELOPED / f'DSC{i+1:05d}.tiff'
        require(row['ordinal'] == i and Path(row['output']) == path and Path(previous['path']) == path, 'Prepared TIFF source order')
        require(row['input'] == source['path'] and row['input_sha256'] == source['sha256'] and row['input_bytes'] == source['bytes'], 'Current/previous original identity mismatch')
        require(row['output_sha256'] == previous['sha256'] and row['output_bytes'] == previous['bytes'], 'Retained TIFF identities disagree')
        require(row['output_wh'] == [7032, 4688] and row['raw_active_xywh'] == [0, 0, 7032, 4688], 'Mixed source geometry')
        require(row['input_wb_bits'] == prior['wb_bits'] and not row['held_wb_differs'], 'Mixed source development')
        st = path.stat()
        require(st.st_size == row['output_bytes'], 'Prepared TIFF length changed')
        file_stats.append((st.st_size, st.st_mtime_ns))
    xy = np.array([p['xy_native'] for p in design['patches']], dtype=np.float64)
    mask = np.array([p['train'] for p in design['patches']], dtype=np.bool_)
    contrast = np.empty((299, 42, 2), dtype=np.float32)
    means = np.empty((299, 42), dtype=np.float32)
    yy, xx = np.indices((192, 192), dtype=np.float64)
    offsets = np.stack((xx-96, yy-96), axis=-1)
    readings = []
    icc = None
    for i, (row, frame) in enumerate(zip(prior['frames'], design['frames'])):
        path = Path(row['output'])
        with tifffile.TiffFile(path) as tif:
            require(len(tif.pages) == 1 and tif.pages[0].shape == (4688, 7032, 3) and tif.pages[0].dtype == np.uint16, 'Changed TIFF header')
            profile = bytes(tif.pages[0].tags[34675].value)
        require(hashlib.sha256(profile).hexdigest() == ICC_SHA and (icc is None or profile == icc), 'Changed TIFF colour profile')
        icc = profile
        image = tifffile.memmap(path, mode='r')
        digest = hashlib.sha256()
        for j, centre in enumerate(xy):
            positions = map_native(offsets+centre, frame['transform'])
            require(source_rectangle(positions) == frame['source_rectangles_xyxy'][j], 'Full-grid/corner support discrepancy')
            rgb = sample_rgb(image, positions)
            digest.update(rgb.astype('<f4', copy=False).tobytes())
            luma = rgb[..., 0]*np.float32(.2126) + rgb[..., 1]*np.float32(.7152) + rgb[..., 2]*np.float32(.0722)
            contrast[i, j] = band_power(luma)
            means[i, j] = np.mean(luma[32:160, 32:160], dtype=np.float32)
        del image
        st = path.stat()
        require((st.st_size, st.st_mtime_ns) == file_stats[i], 'TIFF metadata changed during read')
        readings.append(dict(ordinal=i, file=str(path), retained_file_sha256=row['output_sha256'],
                             bytes=st.st_size, mtime_ns=st.st_mtime_ns,
                             sampled_rgb_f32_sha256=digest.hexdigest(), metadata_before_after_equal=True,
                             sampled_sites=42, source_support_verified=True))
        if i % 25 == 0 or i == 298:
            print(f'Extracted source {i+1}/299, all42 fixed sites', flush=True)
    require(np.isfinite(contrast).all() and np.isfinite(means).all() and (contrast >= 0).all(), 'Invalid complete curves')
    for row, expected in zip(prior['frames'], file_stats):
        st = Path(row['output']).stat()
        require((st.st_size, st.st_mtime_ns) == expected, 'TIFF metadata changed after extraction')
    np.savez(out / 'curves.npz', contrast=contrast, xy_native=xy, train_mask=mask,
             source_ordinals=np.arange(299, dtype=np.int64), patch_mean_luma=means,
             patch_names=np.array([p['name'] for p in design['patches']]),
             grid_row=np.array([p['grid_row'] for p in design['patches']], dtype=np.int64),
             grid_col=np.array([p['grid_col'] for p in design['patches']], dtype=np.int64),
             is_target=np.array([p['is_target'] for p in design['patches']], dtype=np.bool_))
    save(out / 'source-reads.json', readings)
    save(out / 'receipt.json', dict(status='COMPLETE_FIXED_299_SOURCE_CURVES', schema=1,
         plan=ref(out/'plan.json'), controls=ref(out/'stage-controls.json'), curves=ref(out/'curves.npz'),
         source_reads=ref(out/'source-reads.json'), developer_receipt=ref(receipt_path),
         development_completion=ref(DEVELOPMENT_COMPLETE), retained_after_hashes=ref(AFTER), current_input_order=ref(INPUT_ORDER),
         source_count=299, patch_count=42, train_sites=19, heldout_sites=23, all_ordered_sources=True,
         contrast_shape=list(contrast.shape), contrast_dtype=str(contrast.dtype), icc_sha256=ICC_SHA,
         development={k:prior[k] for k in ('levels','wb_bits','tone_bits','xyz_to_cam_bits','matrix_source','scope')},
         current_tiff_metadata_unchanged=True, fresh_complete_tiff_content_hashes=False,
         sampled_values_hashed=True, no_original_raw_reads=True, no_temporal_filtering=True,
         full_aligned_frames_retained=0, elapsed_seconds=time.perf_counter()-start,
         opencv_version=cv2.__version__, numpy_version=np.__version__, tifffile_version=tifffile.__version__,
         limitations=['Toned RGB; no calibrated DN/noise sigma', 'Prepared sources CA-off; current native merge CA-on',
                      'Current full TIFF content not rehashed; retained hashes plus present metadata and actual sample hashes',
                      'Mapped interpolation can affect contrast; these curves are not geometric truth'],
         quality_qualification=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out != HERE and HERE in out.parents, 'Output must be a fresh experiment subdirectory')
    out.mkdir(parents=True, exist_ok=False)
    save(out/'started.json', dict(runner=ref(Path(__file__)), command=sys.argv,
         stage_plan=ref(HERE/'stage-plan.md'), independent_controls=ref(HERE/'independent-controls.py')))
    try:
        extract(out)
    except Exception as error:
        save(out/'refusal.json', dict(status='REFUSED', type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
