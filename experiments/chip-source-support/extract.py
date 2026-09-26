"""Fixed two-witness source strips; retained TIFFs only, no fitting or ranking."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import struct
import sys
import time
import traceback
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FRONT = ROOT/'experiments/chip-focus-front'
MEMO = ROOT/'experiments/quality-september25/intercept-next-discriminator.md'
FIT = FRONT/'fit-1'
STAGE = FRONT/'stage-1'
GAUSSIAN = ROOT/'experiments/chip-focus-radiance/full-1'
INTERCEPT = ROOT/'experiments/chip-focus-intercept/native-full-1'
FIXED = [('surface-scratches', [5112, 1512], [194, 200, 206, 213, 219, 225, 231]),
         ('upper-left-contact-grid', [304, 592], [124, 130, 136, 143, 149, 155, 162])]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


s = load('fixed_chip_source_stage', FRONT/'stage.py')
read, save, ref, require = s.read, s.save, s.ref, s.require


def bound(row):
    path = Path(row['path'])
    require(ref(path) == row, f'Changed bound artifact: {path}')
    return path


def array_hash(a):
    return hashlib.sha256(a.tobytes(order='C')).hexdigest()


def header(path, shape, icc_sha):
    import numpy as np
    import tifffile
    with tifffile.TiffFile(path) as tif:
        require(len(tif.pages) == 1 and tif.pages[0].shape == shape
                and tif.pages[0].dtype == np.uint16, 'Wrong complete RGB16 TIFF geometry/type')
        icc = bytes(tif.pages[0].tags[34675].value)
    require(hashlib.sha256(icc).hexdigest() == icc_sha, 'Wrong TIFF ICC')
    return icc


def png16(path, pixels, icc):
    """Lossless RGB16 PNG with ICC; no resize or extra transfer function."""
    import numpy as np
    require(pixels.dtype == np.uint16 and pixels.shape == (128, 128, 3), 'Wrong display core')
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag+data) & 0xffffffff)
    scan = b''.join(b'\0' + row.astype('>u2', copy=False).tobytes() for row in pixels)
    encoded = b'\x89PNG\r\n\x1a\n'
    encoded += chunk(b'IHDR', struct.pack('>IIBBBBB', 128, 128, 16, 2, 0, 0, 0))
    encoded += chunk(b'iCCP', b'sRGB\0\0' + zlib.compress(icc))
    encoded += chunk(b'IDAT', zlib.compress(scan)) + chunk(b'IEND', b'')
    path.write_bytes(encoded)
    # Independent image codec verifies channel order and every stored RGB16 code.
    import cv2
    decoded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    require(decoded is not None and np.array_equal(decoded[..., ::-1], pixels), 'PNG RGB16 round trip differs')


def save_patch(folder, stem, rgb, icc, source_float):
    import numpy as np
    import tifffile
    require(rgb.shape == (128, 128, 3) and np.isfinite(rgb).all(), 'Wrong finite core')
    tif = folder/(stem+'.tiff')
    tifffile.imwrite(tif, rgb, photometric='rgb', metadata=None,
                     extratags=[(34675, 'B', len(icc), icc, False)])
    require(np.array_equal(tifffile.imread(tif), rgb), 'Core TIFF round trip differs')
    if source_float:
        display = np.rint(np.clip(rgb, 0., 1.) * np.float32(65535)).astype(np.uint16)
        limits = dict(min=float(rgb.min()), max=float(rgb.max()),
                      outside_unit_scalar_count=int(np.count_nonzero((rgb < 0.) | (rgb > 1.))))
    else:
        display = rgb
        limits = None
    png = folder/(stem+'.png')
    png16(png, display, icc)
    return dict(master=ref(tif), display=ref(png), shape=list(rgb.shape), dtype=str(rgb.dtype),
                exact_array_sha256=array_hash(rgb), display_rgb16_sha256=array_hash(display),
                display_quantization='nearest RGB16; fixed [0,1] display saturation only' if source_float else 'exact RGB16',
                pre_display_range=limits, spatial_resize=False)


def extract(out):
    import cv2
    import numpy as np
    import tifffile
    cv2.setNumThreads(8)
    start = time.perf_counter()
    # Existing independent known-transform/source-address controls before TIFF reads.
    controls = s.stage_controls()
    save(out/'stage-controls.json', controls)
    design = s.plan()
    stage_receipt = read(STAGE/'receipt.json')
    for name in ('plan', 'curves', 'source_reads', 'developer_receipt', 'development_completion',
                 'retained_after_hashes', 'current_input_order'):
        bound(stage_receipt[name])
    old_plan = read(STAGE/'plan.json')
    require(design == old_plan, 'Current mapping/support plan differs from retained stage')
    fit_receipt = read(FIT/'receipt.json')
    bound(fit_receipt['model']); bound(fit_receipt['stage_receipt'])
    model = read(FIT/'model.json')
    require(model['frames'] == 299 and model['status'] == 'fit_completed', 'Frozen model unavailable')
    require(fit_receipt['predictive_proxy_admitted'] is False, 'Original proxy refusal changed')
    prior = read(s.DEVELOPED/'receipt.json')
    retained = read(s.AFTER)
    order = read(s.INPUT_ORDER)
    if isinstance(order, dict):
        order = order['inputs']
    require(len(prior['frames']) == len(retained) == len(order) == 299, 'Incomplete source order')
    require(prior['golden']['differing'] == prior['golden']['normalized_f32_differences'] == 0,
            'Developer commissioning missing')
    cfg = read(INTERCEPT/'config.json')
    intercept = read(INTERCEPT/'output/receipt.json')
    gaussian = read(GAUSSIAN/'output/receipt.json')
    require(s.sha(FIT/'model.json') == cfg['model_sha256'] == gaussian['model_sha256'] == intercept['model_sha256'],
            'Model differs across observations')
    require(s.sha(GAUSSIAN/'output/receipt.json') == cfg['gaussian_receipt_sha256'], 'Gaussian receipt differs')
    require(intercept['gaussian_source_and_gather_exact'] and intercept['gaussian_development_exact']
            and intercept['resolved_development'] == gaussian['resolved_development'], 'Native comparison bindings differ')
    require(intercept['native_dimensions'] == gaussian['native_dimensions'] == [6500, 4332]
            and intercept['crop'] == gaussian['crop'] == [133, 89, 3250, 2166]
            and cfg['expected_reference'] == 149 and cfg['warp_map_sha256'] == design['warp']['sha256'], 'Native gauge differs')
    shutil.copyfile(STAGE/'curves.npz', out/'temporal-curves.npz')
    require(s.sha(out/'temporal-curves.npz') == stage_receipt['curves']['sha256'], 'Saved complete curves changed')
    schedule = np.interp(np.linspace(0., 1., 299), model['schedule_knots'], model['schedule_values'])
    yy, xx = np.indices((192, 192), dtype=np.float64)
    offsets = np.stack((xx-96, yy-96), axis=-1)
    witnesses, all_source_refs = [], []
    for name, centre, expected in FIXED:
        index = next(i for i, p in enumerate(design['patches']) if p['name'] == name)
        require(design['patches'][index]['xy_native'] == centre and not design['patches'][index]['train'], 'Witness moved/trained')
        xy = (np.array(centre)-np.array(model['xy_center']))/np.array(model['xy_scale'])
        z = float(xy @ np.array(model['plane'][:2]) + model['plane'][2])
        times = z + np.arange(-3, 4) * model['widths'][0]
        selected = [int(np.argmin(np.abs(schedule-t))) for t in times]
        require(selected == expected, 'Fixed model-derived ordinals changed')
        folder = out/name
        folder.mkdir()
        samples = []
        for d, ordinal in zip(range(-3, 4), selected):
            row, previous, raw_id = prior['frames'][ordinal], retained[ordinal], order[ordinal]
            path = s.DEVELOPED/f'DSC{ordinal+1:05d}.tiff'
            require(row['ordinal'] == ordinal and Path(row['output']) == Path(previous['path']) == path, 'Source ordinal/path mismatch')
            require(row['input'] == raw_id['path'] and row['input_sha256'] == raw_id['sha256']
                    and row['input_bytes'] == raw_id['bytes'], 'Original identity differs (no RAW read)')
            require(row['output_sha256'] == previous['sha256'] and row['output_bytes'] == previous['bytes']
                    and row['input_wb_bits'] == prior['wb_bits'] and not row['held_wb_differs'], 'Retained source/development differs')
            before = (path.stat().st_size, path.stat().st_mtime_ns)
            actual_ref = ref(path)
            require(actual_ref['sha256'] == row['output_sha256'] and actual_ref['bytes'] == row['output_bytes'], 'Current selected TIFF content differs')
            icc = header(path, (4688, 7032, 3), s.ICC_SHA)
            frame = design['frames'][ordinal]
            positions = s.map_native(offsets+np.array(centre), frame['transform'])
            rectangle = s.source_rectangle(positions)
            require(rectangle == frame['source_rectangles_xyxy'][index], 'Mapped footprint changed')
            image = tifffile.memmap(path, mode='r')
            support = s.sample_rgb(image, positions)
            del image
            core = support[32:160, 32:160].copy()
            stem = f'source-{ordinal:03d}'
            support_path = folder/(stem+'-support.npy')
            np.save(support_path, support, allow_pickle=False)
            outputs = save_patch(folder, stem, core, icc, True)
            after = (path.stat().st_size, path.stat().st_mtime_ns)
            require(after == before, 'Selected TIFF metadata changed during read')
            samples.append(dict(ordinal=ordinal, tiff_number=ordinal+1, fixed_sigma_offset=d,
                source=actual_ref, original_identity_only=raw_id, mtime_ns=before[1], source_metadata_unchanged=True,
                source_transform=frame['transform'], source_transform_bits=frame['transform_bits'],
                source_rectangle_xyxy=rectangle, latent_time=float(schedule[ordinal]),
                support=ref(support_path), support_shape=list(support.shape), support_dtype=str(support.dtype),
                support_array_sha256=array_hash(support), support_pre_display_range=dict(min=float(support.min()),
                    max=float(support.max()), outside_unit_scalar_count=int(np.count_nonzero((support<0.)|(support>1.)))),
                core=outputs))
            all_source_refs.append(actual_ref)
        witnesses.append(dict(name=name, centre_native=centre, core_native_xywh=[centre[0]-64, centre[1]-64, 128, 128],
                              support_native_xywh=[centre[0]-96, centre[1]-96, 192, 192],
                              saved_curve_patch_index=index, latent_front=z, sigma=model['widths'][0],
                              source_ordinals=selected, samples=samples, native_outputs={}))
        print(f'Extracted all7 fixed sources for {name}', flush=True)
    images = [('current', Path(cfg['expected_baseline']), cfg['expected_baseline_sha256']),
              ('gaussian', GAUSSIAN/'output/candidate.tiff', gaussian['candidate_sha256']),
              ('intercept', INTERCEPT/'output/candidate.tiff', intercept['candidate_sha256'])]
    native_refs = []
    for arm, path, expected_hash in images:
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        actual_ref = ref(path)
        require(actual_ref['sha256'] == expected_hash, 'Native master content changed')
        icc = header(path, (4332, 6500, 3), s.ICC_SHA)
        image = tifffile.memmap(path, mode='r')
        for witness in witnesses:
            x, y, w, h = witness['core_native_xywh']
            crop = np.array(image[y:y+h, x:x+w], copy=True)
            witness['native_outputs'][arm] = save_patch(out/witness['name'], arm, crop, icc, False)
        del image
        require((path.stat().st_size, path.stat().st_mtime_ns) == before, 'Native master metadata changed')
        native_refs.append(dict(arm=arm, source=actual_ref, mtime_ns=before[1], metadata_unchanged=True))
    bindings = [ref(p) for p in (Path(__file__), FRONT/'stage.py', FRONT/'independent-controls.py', MEMO,
                FIT/'model.json', FIT/'receipt.json', STAGE/'receipt.json', STAGE/'plan.json',
                s.DEVELOPED/'receipt.json', s.DEVELOPMENT_COMPLETE, s.AFTER, s.INPUT_ORDER,
                GAUSSIAN/'output/receipt.json', INTERCEPT/'output/receipt.json', INTERCEPT/'config.json')]
    save(out/'receipt.json', dict(schema=1, status='FIXED_SOURCE_STRIPS_EXTRACTED', witnesses=witnesses,
        native_sources=native_refs, bindings=bindings, map=design['warp'], icc_sha256=s.ICC_SHA,
        controls=ref(out/'stage-controls.json'), complete_temporal_curves=ref(out/'temporal-curves.npz'),
        selected_source_count=len(all_source_refs), selected_sources_fresh_content_hashed=True,
        all299_sources_rehashed=False, source_development=stage_receipt['development'],
        native_resolved_development=intercept['resolved_development'], no_original_raw_reads=True,
        no_refit=True, no_source_ranking=True, no_recenter=True, no_spatial_resize=True,
        native_output_crops_unresampled=True, source_sampler=design['sampler'],
        display_policy='fixed RGB16 quantization/saturation only; exact f32 support/core masters retained; no per-image normalization',
        limitations=['Sources are CA-off toned individually demosaiced RGB; native outputs use CA-on CFA gather then final MHC.',
                     'Source map interpolation is the existing proxy sampler, not an exact native gather counterfactual.',
                     'A structure obscured by fixed display saturation or unresolved in these7 samples makes diagnosis inconclusive.'],
        elapsed_seconds=time.perf_counter()-start, physical_cause_asserted=False, visual_verdict=None))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('run', 'extract'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out != HERE and out.is_relative_to(HERE) and not out.exists(), 'Fresh experiment output required')
    out.mkdir(parents=True)
    if args.phase == 'run':
        existing = load('source_strip_existing_job', ROOT/'experiments/band-source-agreement/run.py')
        existing.job([sys.executable, '-I', '-B', '-X', 'faulthandler', str(Path(__file__).resolve()),
                      'extract', '--out', str(out/'output')],
                     dict(OMP_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8', MKL_NUM_THREADS='8'),
                     out, wall=120, cpu=600, gib=4)
    else:
        try:
            extract(out)
        except Exception as error:
            save(out/'refusal.json', dict(status='REFUSED', message=str(error), traceback=traceback.format_exc()))
            raise


if __name__ == '__main__':
    main()
