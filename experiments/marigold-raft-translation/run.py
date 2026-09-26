"""Separate public fetch, generated controls, and fixed retained-TIFF pilot phases."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import struct
import sys
import time
import traceback
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RETAINED = ROOT/'experiments/marigold-comparator/run-2'
RECIPE = ROOT/'experiments/full-stack-source-prior/recipes/marigold-4.json'
MAP_SHA = 'd2eb0815191279f9d6fc529d76142e56989d4afdcbc052088ef4e7da530b58c1'
DEVELOPER_SHA = '5b606c6b4bbe8eb4684b323f14d96d38ea51307815e95f57419865e8c225b610'
ICC_SHA = '238ad2596316306a72025bb245cf3c8cd72f1090c8d95af2f38dc090e84ece5b'
INDICES = list(range(108, 117))
ANCHOR = 112
OWN = ('operator.py', 'run.py', 'design.md', 'independent-controls.py', 'independent-plan.md', 'independent-review.md')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def ref(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def unchanged(rows):
    require(all(ref(Path(row['path'])) == row for row in rows), 'A bound file changed')


def sources():
    paths = [HERE/name for name in OWN]
    distribution = importlib.metadata.distribution('torchvision')
    # Bind the installed operator and its immediate optical-flow/preprocessing implementation.
    paths += [Path(distribution.locate_file('torchvision/'+name)) for name in (
        'models/optical_flow/raft.py', 'models/optical_flow/_utils.py', 'ops/misc.py',
        'transforms/_presets.py', 'transforms/functional.py', 'transforms/_functional_tensor.py')]
    paths += [ROOT/name for name in (
        'experiments/band-source-agreement/run.py', 'experiments/cross-scale-source-prior/run.py',
        'experiments/full-context-placement/run.py', 'experiments/chip-stock-selectivity/run.py',
        'experiments/base-band-transfer/run.py', 'experiments/m193c-output-grid/bounded-process.py',
        'experiments/m12-scorecard/m12-harness.py')]
    return [ref(path) for path in paths]


def plan(operator):
    recipe = read(RECIPE)
    warp = Path(recipe['warp_map'])
    require(recipe['expected_reference'] == 244 and recipe['expected_crop'] == [191,128,3134,2088]
            and recipe['expected_full_geometry'] == [3516,2344] and len(recipe['inputs']) == 488,
            'Wrong fixed marigold recipe')
    require(ref(warp)['sha256'] == recipe['warp_map_sha256'] == MAP_SHA, 'Changed held global map')
    lines = warp.read_text().splitlines()
    require('reference 244' in lines and 'frames 488' in lines and 'plane 3516x2344' in lines, 'Wrong map header')
    bits = {}
    for line in lines:
        fields = line.split()
        if fields and fields[0].isdigit():
            i = int(fields[0])
            require(i not in bits and fields[1] == 'placed' and len(fields) >= 6, 'Invalid/unplaced map row')
            bits[i] = fields[2:6]
    require(set(bits) == set(range(488)), 'Incomplete held map')
    developer = RETAINED/'developed/receipt.json'
    completed = read(RETAINED/'development-complete.json')
    require(ref(developer)['sha256'] == DEVELOPER_SHA and ref(developer) == completed['receipt']
            and completed['source_count'] == 488 and completed['current_pixels_icc_exact']
            and completed['all_formats_icc_checked'], 'Wrong retained development')
    developed, fixed = read(developer), read(RETAINED/'fixed.json')
    after, inputs = read(RETAINED/'helicon-b/inputs-after.json'), read(RETAINED/'inputs.json')
    require(developed['status'] == '488_UNALIGNED_NATIVE_RGB16_DEVELOPED'
            and developed['resolved'] == fixed['resolved'] and developed['current_golden']['rgb16_and_icc_exact']
            and developed['golden']['differing'] == developed['golden']['normalized_f32_differences'] == 0,
            'Retained current developer control differs')
    require(len(after) == len(inputs) == len(developed['frames']) == 488, 'Incomplete retained chronology')
    require([{k:v for k,v in row.items() if k != 'mtime_ns'} for row in inputs] == recipe['inputs'], 'Original receipt order differs')
    frames = []
    for i in INDICES:
        row = developed['frames'][i]
        file = RETAINED/'developed'/f'frame-{i:05d}.tiff'
        identity = dict(path=str(file), bytes=row['output_bytes'], sha256=row['output_sha256'])
        require(row['ordinal'] == i and Path(row['output']) == file and after[i] == identity,
                'Retained TIFF ordinal/hash mismatch')
        require(row['input'] == inputs[i]['path'] and row['input_sha256'] == inputs[i]['sha256']
                and row['input_bytes'] == inputs[i]['bytes'] and row['input_wb_bits'] == fixed['cache']['wb_gains_bits'],
                'Original/development binding differs')
        transform = [struct.unpack('>d', bytes.fromhex(v))[0] for v in bits[i]]
        native, sample = operator.proxy_sample_coordinates(transform)
        frames.append(dict(index=i, retained_tiff=identity, original_identity_only=inputs[i],
            transform_bits=bits[i], transform=transform,
            native_coordinate_sha256=operator.array_sha(native), remap_f32_coordinate_sha256=operator.array_sha(sample)))
    return dict(schema=1, indices=INDICES, anchor=ANCHOR, global_reference=244, source_count=488,
        native_wh=list(operator.NATIVE_WH), proxy_wh=list(operator.PROXY_WH), source_proxy_wh=list(operator.SOURCE_PROXY_WH),
        native_support=list(operator.SUPPORT_NATIVE_XYWH), native_interior=list(operator.INTERIOR_NATIVE_XYWH),
        frames=frames, map=ref(warp), recipe=ref(RECIPE), development=ref(developer),
        completion=ref(RETAINED/'development-complete.json'), fixed=ref(RETAINED/'fixed.json'),
        original_order=ref(RETAINED/'inputs.json'), retained_after=ref(RETAINED/'helicon-b/inputs-after.json'),
        no_original_raw_reads=True, original_metadata_not_rechecked=True, no_native_quality_claim=True)


def fetch(out, operator):
    (out/'.gitignore').write_text('*\n', encoding='ascii')
    before = sources()
    request = urllib.request.Request(operator.WEIGHT_URL, headers={'User-Agent':'strehl-fixed-raft-pilot'})
    with urllib.request.urlopen(request, timeout=30) as response:
        require(response.geturl() == operator.WEIGHT_URL, 'Unexpected checkpoint redirect')
        data = response.read((32 << 20)+1)
    require(0 < len(data) <= 32 << 20 and hashlib.sha256(data).hexdigest().startswith(operator.WEIGHT_PREFIX),
            'Checkpoint size or published hash prefix differs')
    file = out/'raft-large-c-t-skht-v2.pth'
    file.write_bytes(data)
    unchanged(before)
    save(out/'manifest.json', dict(status='FETCHED_OFFICIAL_CHECKPOINT_ONLY', checkpoint=ref(file),
        url=operator.WEIGHT_URL, published_sha256_prefix=operator.WEIGHT_PREFIX, sources=before,
        licence_scope='BSD torchvision implementation; separate research checkpoint, no redistribution decision',
        model='Raft_Large_Weights.C_T_SKHT_V2', no_model_execution=True))


def upstream(folder, operator):
    manifest = read(folder/'manifest.json')
    require(manifest['url'] == operator.WEIGHT_URL and manifest['model'] == 'Raft_Large_Weights.C_T_SKHT_V2', 'Wrong model intake')
    unchanged(manifest['sources'])
    checkpoint = Path(manifest['checkpoint']['path'])
    require(checkpoint.parent == folder and ref(checkpoint) == manifest['checkpoint']
            and manifest['checkpoint']['sha256'].startswith(operator.WEIGHT_PREFIX), 'Changed checkpoint')
    return checkpoint


def controls_completed(folder, upstream_folder):
    done = read(folder/'completed.json')
    require(done['phase'] == 'controls' and done['process_completed'] and done['sources_unchanged'], 'Controls job incomplete')
    require(done['upstream_manifest'] == ref(upstream_folder/'manifest.json'), 'Model changed after controls')
    unchanged(read(folder/'bindings.json'))
    receipt = read(folder/'output/controls.json')
    require(done['result'] == ref(folder/'output/controls.json') and receipt['passed']
            and receipt['mechanical_pass'] and receipt['controls_pass'] and receipt['inference_calls'] == 8,
            'Generated controls refused this fixed recipe')
    return receipt


def pilot(out, operator, model, independent):
    import cv2
    import numpy as np
    import tifffile
    cv2.setNumThreads(8)
    design = plan(operator)
    save(out/'plan.json', design)
    images, frames = {}, []
    for frame in design['frames']:
        i = frame['index']
        file = Path(frame['retained_tiff']['path'])
        before = (file.stat().st_size, file.stat().st_mtime_ns)
        require(ref(file) == frame['retained_tiff'], 'Selected TIFF content differs from run-2')
        with tifffile.TiffFile(file) as tif:
            require(len(tif.pages) == 1 and tif.pages[0].shape == (4688,7032,3)
                    and tif.pages[0].dtype == np.uint16
                    and hashlib.sha256(bytes(tif.pages[0].tags[34675].value)).hexdigest() == ICC_SHA, 'Wrong complete source format/ICC')
        source = tifffile.memmap(file, mode='r')
        proxy, coordinates = operator.make_proxy(source, frame['transform'])
        del source
        require(coordinates['native_coordinate_sha256'] == frame['native_coordinate_sha256']
                and coordinates['remap_f32_coordinate_sha256'] == frame['remap_f32_coordinate_sha256'], 'Proxy mapping changed')
        require((file.stat().st_size, file.stat().st_mtime_ns) == before, 'Selected TIFF metadata changed')
        np.save(out/f'proxy-{i}-rgb.npy', proxy, allow_pickle=False)
        display = np.rint(proxy*65535).astype(np.uint16)
        require(cv2.imwrite(str(out/f'proxy-{i}.png'), display[..., ::-1]), 'Proxy display write failed')
        native, sample = operator.proxy_sample_coordinates(frame['transform'])
        np.savez(out/f'proxy-{i}-coordinates.npz', native_f64=native, remap_f32=sample)
        images[i] = proxy
        frames.append(dict(**frame, proxy=ref(out/f'proxy-{i}-rgb.npy'), display=ref(out/f'proxy-{i}.png'),
            coordinates=ref(out/f'proxy-{i}-coordinates.npz'), coordinate_summary=coordinates,
            source_mtime_ns=before[1], source_metadata_unchanged=True,
            display_scope='RGB16 proxy only, no ICC transform or native quality claim'))
    records = []
    for frame in frames:
        i = frame['index']
        if i == ANCHOR:
            continue
        forward = operator.infer_pair(model, images[ANCHOR], images[i])
        reverse = operator.infer_pair(model, images[i], images[ANCHOR])
        a = frame['transform'][:2]
        anchor_a = next(row['transform'][:2] for row in frames if row['index'] == ANCHOR)
        judgement = independent.judge_pair(forward, reverse, a)
        reverse_judgement = independent.judge_pair(reverse, forward, anchor_a)
        reduced = operator.reduce_flow(forward, a)
        require(np.allclose(reduced['native_median'], judgement['native_median'], rtol=0, atol=1e-6)
                and np.allclose(reduced['source_native_translation'], judgement['source_native_translation'], rtol=0, atol=1e-6),
                'Independent displacement reduction differs')
        np.save(out/f'flow-{ANCHOR}-to-{i}.npy', forward, allow_pickle=False)
        np.save(out/f'flow-{i}-to-{ANCHOR}.npy', reverse, allow_pickle=False)
        records.append(dict(index=i, reduction=reduced, judge=judgement, reverse_judge=reverse_judgement,
            admitted=judgement['admitted'] and reverse_judgement['admitted'],
            forward=ref(out/f'flow-{ANCHOR}-to-{i}.npy'), reverse=ref(out/f'flow-{i}-to-{ANCHOR}.npy')))
        print(f"Pair {ANCHOR}->{i}: admitted={records[-1]['admitted']}", flush=True)
    active = any(np.linalg.norm(row['reduction']['source_native_translation']) >= .5 for row in records)
    all_pass = all(row['admitted'] for row in records)
    result = dict(schema=1, status='FIXED_PILOT_ELIGIBLE_FOR_ROOT_REVIEW' if all_pass and active else 'FIXED_PILOT_REFUSED',
        all_eight_admitted=all_pass, at_least_one_translation_ge_half_native=bool(active),
        pilot_eligible_for_review=bool(all_pass and active), pairs=records, frames=frames,
        anchor_index=ANCHOR, anchor_applied_delta=[0.,0.], model_calls=16,
        original_raw_read=False, native_hook_config_emitted=False, native_quality_admitted=False,
        all_selected_tiffs_freshly_content_hashed=True, all488_tiffs_rehashed=False,
        geometry_truth_claim=False, learned_spatial_variation_discarded=True,
        limitation='CA-off developed RGB low-resolution proxies; this is not native CFA sample or quality commissioning')
    save(out/'pilot.json', result)
    return result


def child(args, operator):
    out = args.out/'output'
    out.mkdir()
    start = time.perf_counter()
    checkpoint = upstream(args.upstream, operator)
    if args.phase == 'pilot-child':
        controls_completed(args.controls, args.upstream)
    independent = load('raft_independent_controls', HERE/'independent-controls.py')
    model = operator.load_model(checkpoint)
    result = independent.run_controls(operator, model, out) if args.phase == 'controls-child' else pilot(out, operator, model, independent)
    require(len(model.pilot_metadata['calls']) == (8 if args.phase == 'controls-child' else 16), 'Unexpected inference count')
    save(out/'runtime.json', dict(**model.pilot_metadata, elapsed_seconds=time.perf_counter()-start,
        checkpoint=ref(checkpoint), observational_result=result.get('status', 'GENERATED_CONTROLS_COMPLETE')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('plan','fetch','controls','pilot','controls-child','pilot-child'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--upstream', type=Path)
    parser.add_argument('--controls', type=Path)
    args = parser.parse_args()
    args.out = args.out.resolve()
    require(args.out != HERE and args.out.is_relative_to(HERE), 'Output must be experiment-owned')
    for key in ('upstream', 'controls'):
        if getattr(args, key) is not None:
            setattr(args, key, getattr(args, key).resolve())
    operator = load('fixed_raft_operator', HERE/'operator.py')
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
    if args.phase == 'fetch':
        fetch(args.out, operator)
        return
    require(args.upstream is not None, 'Explicit fetched checkpoint is required')
    upstream(args.upstream, operator)
    if args.phase == 'pilot':
        require(args.controls is not None, 'Explicit controls receipt is required')
        controls_completed(args.controls, args.upstream)
    bindings = sources()
    save(args.out/'bindings.json', bindings)
    band = load('raft_existing_job', ROOT/'experiments/band-source-agreement/run.py')
    command = [sys.executable,'-I','-B','-X','faulthandler',str(Path(__file__).resolve()),args.phase+'-child',
               '--out',str(args.out),'--upstream',str(args.upstream)]
    if args.controls is not None:
        command += ['--controls',str(args.controls)]
    band.job(command, dict(OMP_NUM_THREADS='8', MKL_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8',
                          CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='0', CUBLAS_WORKSPACE_CONFIG=':4096:8'),
             args.out, wall=120, cpu=300, gib=8)
    unchanged(bindings)
    upstream(args.upstream, operator)
    save(args.out/'completed.json', dict(phase=args.phase, process_completed=True, sources_unchanged=True,
        upstream_manifest=ref(args.upstream/'manifest.json'),
        result=ref(args.out/'output'/('controls.json' if args.phase == 'controls' else 'pilot.json')),
        photographic_quality_admitted=False))


if __name__ == '__main__':
    main()
