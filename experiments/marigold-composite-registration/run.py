"""Fixed composite-reference RAFT pilot; retained RGB16 only, no native mutation."""
from pathlib import Path
import argparse
import importlib.util
import sys
import time
import traceback
import struct
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'experiments/marigold-raft-translation'
INDICES = [112, 152, 320]
CURRENT_SHA = '19e657e419d52adf567ec86472f917ad9b9abfc9b0812131e9bba0eacbae462f'
OWN = ('run.py', 'design.md', 'independent-controls.py', 'independent-plan.md', 'independent-review.md')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


old = load('composite_old_runner', OLD/'run.py')
read, save, ref, require, unchanged = old.read, old.save, old.ref, old.require, old.unchanged


def sources():
    return old.sources() + [ref(HERE/name) for name in OWN]


def plan(operator):
    # The unchanged old preflight pins the complete chronology, map and developer.
    design = old.plan(operator)
    developed = read(old.RETAINED/'developed/receipt.json')
    fixed = read(old.RETAINED/'fixed.json')
    inputs = read(old.RETAINED/'inputs.json')
    after = read(old.RETAINED/'helicon-b/inputs-after.json')
    rows = {}
    for line in Path(design['map']['path']).read_text().splitlines():
        fields = line.split()
        if fields and fields[0].isdigit():
            rows[int(fields[0])] = fields[2:6]
    frames = []
    for i in INDICES:
        row = developed['frames'][i]
        file = old.RETAINED/'developed'/f'frame-{i:05d}.tiff'
        identity = dict(path=str(file), bytes=row['output_bytes'], sha256=row['output_sha256'])
        require(row['ordinal'] == i and Path(row['output']) == file and after[i] == identity,
                'Retained source ordinal/hash mismatch')
        require(row['input'] == inputs[i]['path'] and row['input_sha256'] == inputs[i]['sha256']
                and row['input_bytes'] == inputs[i]['bytes'] and row['input_wb_bits'] == fixed['cache']['wb_gains_bits'],
                'Retained original/development binding differs')
        transform = [struct.unpack('>d', bytes.fromhex(v))[0] for v in rows[i]]
        native, sample = operator.proxy_sample_coordinates(transform)
        frames.append(dict(index=i, retained_tiff=identity, original_identity_only=inputs[i],
            transform_bits=rows[i], transform=transform,
            native_coordinate_sha256=operator.array_sha(native), remap_f32_coordinate_sha256=operator.array_sha(sample)))
    current = fixed['identities'][0]
    require(current['sha256'] == CURRENT_SHA and current['bytes'] == 157055880
            and Path(current['path']) == ROOT/'experiments/garnet-spatial-trace/marigold4-fixed-1/output/candidate.tiff',
            'Wrong current complete master')
    design.update(indices=INDICES, frames=frames, anchor=None, reference_kind='current_complete_composite',
        current=current, current_remapping=False, current_proxy='RGB16 INTER_AREA directly to880x586, then f32/65535',
        reference_destination_linear_map=[1., 0.], current_and_source_development_resolved=fixed['resolved'],
        all_three_or_stop=True, previous_local_activity_refusal_preserved=True)
    return design


def area_rgb16(rgb_u16, target_wh):
    import cv2
    import numpy as np
    require(rgb_u16.dtype == np.uint16 and rgb_u16.ndim == 3 and rgb_u16.shape[2] == 3,
            'Expected RGB16 spatial array')
    require(len(target_wh) == 2 and all(int(v) == v and v > 0 for v in target_wh), 'Invalid target dimensions')
    return cv2.resize(rgb_u16, tuple(target_wh), interpolation=cv2.INTER_AREA).astype(np.float32)/np.float32(65535)


def check_tiff(path, expected, shape):
    import numpy as np
    import tifffile
    before = (path.stat().st_size, path.stat().st_mtime_ns)
    require(ref(path) == expected, 'Selected retained TIFF content differs')
    with tifffile.TiffFile(path) as tif:
        require(len(tif.pages) == 1 and tif.pages[0].shape == shape and tif.pages[0].dtype == np.uint16
                and hashlib.sha256(bytes(tif.pages[0].tags[34675].value)).hexdigest() == old.ICC_SHA,
                'Wrong complete TIFF format or ICC')
    return before


def save_proxy(out, name, image):
    import cv2
    import numpy as np
    np.save(out/f'{name}-rgb.npy', image, allow_pickle=False)
    require(cv2.imwrite(str(out/f'{name}.png'), np.rint(image*65535).astype(np.uint16)[..., ::-1]),
            'Proxy display write failed')
    return dict(array=ref(out/f'{name}-rgb.npy'), display=ref(out/f'{name}.png'))


def controls_completed(folder, upstream_folder, prior_folder):
    old.controls_completed(prior_folder, upstream_folder)
    done = read(folder/'completed.json')
    require(done['phase'] == 'controls' and done['process_completed'] and done['sources_unchanged'],
            'Composite controls job incomplete')
    require(done['upstream_manifest'] == ref(upstream_folder/'manifest.json')
            and done['prior_controls'] == ref(prior_folder/'completed.json'), 'Retained controls/model changed')
    unchanged(read(folder/'bindings.json'))
    receipt = read(folder/'output/controls.json')
    require(done['result'] == ref(folder/'output/controls.json') and receipt['passed']
            and receipt['mechanical_pass'] and receipt['inference_calls'] == 4,
            'Composite-reference falsifier refused this recipe')
    staging = read(folder/'output/staging-controls.json')
    require(done['staging_controls'] == ref(folder/'output/staging-controls.json') and staging['passed'],
            'Composite staging controls incomplete')
    return receipt


def pilot(out, operator, model, independent):
    import cv2
    import numpy as np
    import tifffile
    cv2.setNumThreads(8)
    design = plan(operator)
    save(out/'plan.json', design)
    current_path = Path(design['current']['path'])
    before = check_tiff(current_path, design['current'], (4176,6268,3))
    source = tifffile.memmap(current_path, mode='r')
    current = area_rgb16(source, operator.PROXY_WH)
    del source
    require((current_path.stat().st_size, current_path.stat().st_mtime_ns) == before, 'Current metadata changed')
    current_record = dict(identity=design['current'], proxy=save_proxy(out, 'current', current),
        source_metadata_unchanged=True, mtime_ns=before[1], no_mapping_or_crop_applied=True)
    records, frames = [], []
    for frame in design['frames']:
        i = frame['index']
        path = Path(frame['retained_tiff']['path'])
        before = check_tiff(path, frame['retained_tiff'], (4688,7032,3))
        source = tifffile.memmap(path, mode='r')
        proxy, coordinates = operator.make_proxy(source, frame['transform'])
        del source
        require(coordinates['native_coordinate_sha256'] == frame['native_coordinate_sha256']
                and coordinates['remap_f32_coordinate_sha256'] == frame['remap_f32_coordinate_sha256'],
                'Source proxy coordinates changed')
        require((path.stat().st_size, path.stat().st_mtime_ns) == before, 'Source metadata changed')
        native, sample = operator.proxy_sample_coordinates(frame['transform'])
        np.savez(out/f'proxy-{i}-coordinates.npz', native_f64=native, remap_f32=sample)
        frames.append(dict(**frame, proxy=save_proxy(out, f'proxy-{i}', proxy),
            coordinates=ref(out/f'proxy-{i}-coordinates.npz'), coordinate_summary=coordinates,
            source_metadata_unchanged=True, source_mtime_ns=before[1]))
        forward = operator.infer_pair(model, current, proxy)
        reverse = operator.infer_pair(model, proxy, current)
        a = frame['transform'][:2]
        judge = independent.judge_pair(forward, reverse, a)
        # Reverse destination is the delivered output gauge, not an original sensor frame.
        reverse_judge = independent.judge_pair(reverse, forward, [1., 0.])
        reduced = operator.reduce_flow(forward, a)
        require(np.allclose(reduced['native_median'], judge['native_median'], rtol=0, atol=1e-6)
                and np.allclose(reduced['source_native_translation'], judge['source_native_translation'], rtol=0, atol=1e-6),
                'Independent reduction differs')
        np.save(out/f'flow-current-to-{i}.npy', forward, allow_pickle=False)
        np.save(out/f'flow-{i}-to-current.npy', reverse, allow_pickle=False)
        records.append(dict(index=i, source_a=a, reverse_destination_a=[1.,0.], reduction=reduced,
            judge=judge, reverse_judge=reverse_judge, admitted=judge['admitted'] and reverse_judge['admitted'],
            forward=ref(out/f'flow-current-to-{i}.npy'), reverse=ref(out/f'flow-{i}-to-current.npy')))
        print(f"Current composite <-> source{i}: admitted={records[-1]['admitted']}", flush=True)
    active = any(np.linalg.norm(row['reduction']['source_native_translation']) >= .5 for row in records)
    all_pass = len(records) == 3 and all(row['admitted'] for row in records)
    result = dict(schema=1, status='COMPOSITE_PILOT_ELIGIBLE_FOR_ROOT_REVIEW' if all_pass and active else 'COMPOSITE_PILOT_REFUSED',
        all_three_admitted=all_pass, at_least_one_translation_ge_half_native=bool(active),
        pilot_eligible_for_review=bool(all_pass and active), pairs=records, frames=frames, current=current_record,
        model_calls=6, original_raw_read=False, native_hook_config_emitted=False, native_quality_admitted=False,
        all_selected_tiffs_freshly_content_hashed=True, all488_tiffs_rehashed=False,
        geometry_truth_claim=False, learned_spatial_variation_discarded=True,
        limitation='Current CA-on composite versus CA-off source RGB proxies; composite artifacts can contaminate matching; no native quality claim')
    save(out/'pilot.json', result)
    return result


def child(args, operator):
    out = args.out/'output'
    out.mkdir()
    start = time.perf_counter()
    checkpoint = old.upstream(args.upstream, operator)
    old.controls_completed(args.prior_controls, args.upstream)
    new = load('composite_independent_controls', HERE/'independent-controls.py')
    independent = load('composite_old_judge', OLD/'independent-controls.py')
    if args.phase == 'pilot-child':
        controls_completed(args.controls, args.upstream, args.prior_controls)
    else:
        staging = new.staging_controls(area_rgb16)
        save(out/'staging-controls.json', staging)
        require(staging['passed'], 'Independent composite staging arithmetic failed')
    model = operator.load_model(checkpoint)
    result = new.run_controls(operator, model, out) if args.phase == 'controls-child' else pilot(out, operator, model, independent)
    require(len(model.pilot_metadata['calls']) == (4 if args.phase == 'controls-child' else 6), 'Unexpected inference count')
    save(out/'runtime.json', dict(**model.pilot_metadata, elapsed_seconds=time.perf_counter()-start,
        checkpoint=ref(checkpoint), observational_result=result.get('status', 'COMPOSITE_CONTROLS_COMPLETE')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan','controls','pilot','controls-child','pilot-child'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, default=OLD/'upstream-2')
    parser.add_argument('--prior-controls', type=Path, default=OLD/'controls-1')
    parser.add_argument('--controls', type=Path)
    args = parser.parse_args()
    for key in ('out', 'upstream', 'prior_controls', 'controls'):
        value = getattr(args, key)
        if value is not None:
            setattr(args, key, value.resolve())
    require(args.out != HERE and args.out.is_relative_to(HERE), 'Output must be experiment-owned')
    operator = load('composite_fixed_raft_operator', OLD/'operator.py')
    if args.phase.endswith('-child'):
        try:
            child(args, operator)
        except Exception as error:
            save(args.out/'refusal.json', dict(status='INSTRUMENT_REFUSED', message=str(error), traceback=traceback.format_exc()))
            raise
        return
    args.out.mkdir(parents=True, exist_ok=False)
    if args.phase == 'plan':
        save(args.out/'plan.json', plan(operator))
        return
    old.upstream(args.upstream, operator)
    old.controls_completed(args.prior_controls, args.upstream)
    if args.phase == 'pilot':
        require(args.controls is not None, 'Explicit new controls receipt required')
        controls_completed(args.controls, args.upstream, args.prior_controls)
    bindings = sources()
    save(args.out/'bindings.json', bindings)
    band = load('composite_existing_job', ROOT/'experiments/band-source-agreement/run.py')
    command = [sys.executable,'-I','-B','-X','faulthandler',str(Path(__file__).resolve()),args.phase+'-child',
        '--out',str(args.out),'--upstream',str(args.upstream),'--prior-controls',str(args.prior_controls)]
    if args.controls is not None:
        command += ['--controls',str(args.controls)]
    band.job(command, dict(OMP_NUM_THREADS='8',MKL_NUM_THREADS='8',OPENBLAS_NUM_THREADS='8',
        CUDA_VISIBLE_DEVICES='0',PYTHONHASHSEED='0',CUBLAS_WORKSPACE_CONFIG=':4096:8'), args.out, wall=120,cpu=300,gib=8)
    unchanged(bindings)
    old.upstream(args.upstream, operator)
    save(args.out/'completed.json', dict(phase=args.phase,process_completed=True,sources_unchanged=True,
        upstream_manifest=ref(args.upstream/'manifest.json'), prior_controls=ref(args.prior_controls/'completed.json'),
        staging_controls=ref(args.out/'output/staging-controls.json') if args.phase == 'controls' else None,
        result=ref(args.out/'output'/('controls.json' if args.phase == 'controls' else 'pilot.json')),
        photographic_quality_admitted=False))


if __name__ == '__main__':
    main()
