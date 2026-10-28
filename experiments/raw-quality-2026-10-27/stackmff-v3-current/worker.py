"""Bounded consumer-tile RGB comparison; original RAW reconstruction is unchanged."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time

import cv2
import numpy as np
import torch
import tifffile
from PIL import Image

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
CORE = 256
GPU_LIMIT = 24 << 30


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def binding(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(4 << 20):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def tile(ctx, model, adapter, bridge, rect):
    spec = adapter.tile_spec(rect, (ctx.width, ctx.height))
    started = time.perf_counter()
    rgb = bridge.gather_tile(ctx, spec['read_rect'])
    gathered = time.perf_counter()
    assert rgb.dtype == np.uint16 and rgb.shape[0] == 299 and rgb.shape[-1] == 3
    result = adapter.predict_tile(model, rgb, spec)
    torch.cuda.synchronize()
    finished = time.perf_counter()
    fused = result['fused']
    assert fused.dtype == np.uint16 and fused.shape == (rect[3], rect[2], 3)
    assert np.isfinite(result['fused_float']).all()
    allocated, reserved = torch.cuda.max_memory_allocated(), torch.cuda.max_memory_reserved()
    assert max(allocated, reserved) <= GPU_LIMIT, (allocated, reserved)
    stats = dict(core_rect=list(rect), read_rect=list(spec['read_rect']),
                 source_count=rgb.shape[0], gather_seconds=gathered-started,
                 inference_seconds=finished-gathered, total_seconds=finished-started,
                 peak_cuda_allocated_bytes=allocated, peak_cuda_reserved_bytes=reserved,
                 model_metadata=result['metadata'])
    del rgb
    return result, stats


def views(args):
    full = args.full.resolve()
    receipt = json.loads((full / 'receipt.json').read_text())
    assert receipt['complete'] and receipt['source_count'] == 299
    master = full / 'stack-master.tiff'
    assert binding(master) == receipt['master']
    with tifffile.TiffFile(master) as tf:
        rgb = tf.asarray()
        icc = bytes(tf.pages[0].tags[34675].value)
    display = np.rint(rgb.astype(np.float32) / np.float32(257)).astype(np.uint8)
    Image.fromarray(display).save(args.out / 'complete-stack.jpg', quality=96, subsampling=0, icc_profile=icc)
    witnesses = [('background-black',3800,500), ('dark-elytron',2750,2120),
        ('turquoise-scales',2120,1340), ('elytron-seam',2950,1960),
        ('bright-wing-rim',4050,1810), ('thorax-texture',4520,2560),
        ('upper-leg-hairs',1820,640), ('blue-joint',2680,850),
        ('upper-occlusion',3850,1300), ('eye-and-antenna',5350,2920)]
    saved = []
    for name, x, y in witnesses:
        path = args.out / (name + '.png')
        Image.fromarray(display[y:y+384,x:x+384]).save(path, icc_profile=icc)
        saved.append(dict(name=name, origin=[x,y], size=[384,384], image=binding(path)))
    save(args.out / 'receipt.json', dict(complete=True, mechanical_pass=True, quality_claim=False,
         status='COMPLETE_COMPARATOR_VIEWS', master=binding(master), witnesses=saved,
         complete_image=binding(args.out / 'complete-stack.jpg'),
         display='Already developed sRGB16 divided by257, nearest rounding; no extra tone or sharpening.'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--stage', choices=('cost','full','views'), required=True)
    p.add_argument('--full', type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    if a.stage == 'views':
        views(a)
        return
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    cv2.setNumThreads(1)
    assert torch.cuda.is_available()
    total_gpu = torch.cuda.get_device_properties(0).total_memory
    torch.cuda.set_per_process_memory_fraction(min(GPU_LIMIT, total_gpu) / total_gpu, 0)
    bridge = module('stackmff_input_bridge', AREA / 'input-bridge.py')
    adapter = module('stackmff_model_adapter', AREA / 'model-adapter.py')
    preparation_start = time.perf_counter()
    print(json.dumps(dict(stage='validate-input-headers')), flush=True)
    ctx = bridge.load_manifest()
    headers = bridge.check_headers(ctx)
    save(a.out / 'headers.json', headers)
    print(json.dumps(dict(stage='hash-all299-inputs-before', bytes=sum(p.stat().st_size for p in ctx.paths))), flush=True)
    before = bridge.hash_inputs(ctx)
    save(a.out / 'inputs-before.json', before)
    assert len(before) == 299
    print(json.dumps(dict(stage='load-pinned-model')), flush=True)
    model = adapter.load_model(a.upstream, device='cuda')
    preparation_seconds = time.perf_counter() - preparation_start
    torch.cuda.reset_peak_memory_stats()
    total_tiles = math.ceil(ctx.width / CORE) * math.ceil(ctx.height / CORE)
    rows = []
    if a.stage == 'cost':
        # Fixed upper-leg hair location, all299 sources, two unchanged calls.
        rect = (1792,512,CORE,CORE)
        for repetition in range(2):
            result, row = tile(ctx, model, adapter, bridge, rect)
            row['repetition'] = repetition
            rows.append(row)
            if repetition == 0:
                first = result['fused'].copy()
            else:
                delta = result['fused'].astype(np.int32) - first.astype(np.int32)
                row['repeat_pixels_exact'] = bool(np.array_equal(first, result['fused']))
                row['repeat_max_u16_difference'] = int(np.abs(delta).max())
                assert row['repeat_max_u16_difference'] <= 1, 'repeat exceeds fixed compositor precision allowance'
            print(json.dumps(row), flush=True)
            del result
        np.save(a.out / 'cost-tile.npy', first, allow_pickle=False)
    else:
        output = np.empty((ctx.height, ctx.width, 3), dtype=np.uint16)
        covered = 0
        for y in range(0,ctx.height,CORE):
            for x in range(0,ctx.width,CORE):
                rect = (x,y,min(CORE,ctx.width-x),min(CORE,ctx.height-y))
                result, row = tile(ctx, model, adapter, bridge, rect)
                output[y:y+rect[3],x:x+rect[2]] = result['fused']
                rows.append(row)
                covered += rect[2]*rect[3]
                print(json.dumps(dict(tile=len(rows), total_tiles=total_tiles, **row)), flush=True)
                del result
        assert covered == ctx.width*ctx.height and len(rows) == total_tiles
        master = a.out / 'stack-master.tiff'
        tifffile.imwrite(master, output, photometric='rgb', compression=None, metadata=None,
            software='Strehl research: pinned StackMFF V3 RGB comparator',
            extratags=[(34675,7,len(ctx.icc),ctx.icc,False)])
        with tifffile.TiffFile(master) as tf:
            assert np.array_equal(tf.asarray(), output)
            assert bytes(tf.pages[0].tags[34675].value) == ctx.icc
        del output
    preservation_start = time.perf_counter()
    print(json.dumps(dict(stage='hash-all299-inputs-after')), flush=True)
    preservation = bridge.verify_inputs(ctx, before)
    preservation_seconds = time.perf_counter() - preservation_start
    save(a.out / 'input-preservation.json', preservation)
    save(a.out / 'tiles.json', rows)
    receipt = dict(complete=True, mechanical_pass=True, quality_claim=False,
        status='COMPLETE_STACKMFF_V3_' + a.stage.upper(), source_count=299,
        output_wh=[ctx.width,ctx.height], tiles_completed=len(rows), full_tile_count=total_tiles,
        input_preservation=preservation, input_contract=ctx.metadata,
        preparation_seconds=preparation_seconds, preservation_seconds=preservation_seconds,
        upstream=binding(a.upstream / 'download-receipt.json'),
        torch=torch.__version__, cuda=torch.version.cuda, opencv=cv2.__version__,
        gpu=torch.cuda.get_device_name(), workers=4, precision='float32, TF32 disabled',
        gpu_allocator_cap_bytes=min(GPU_LIMIT, total_gpu),
        peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),
        native_RAW_reconstruction=False, whole_workflow_comparison=False,
        comparator='Pinned learned RGB fusion with retained Strehl placement and fixed prior development')
    if a.stage == 'cost':
        receipt['tile_time_projection_seconds'] = max(r['total_seconds'] for r in rows) * total_tiles
        receipt['projection_is_measurement'] = False
        receipt['projection_excludes'] = 'Process startup, input validation/hash sweeps, model loading, complete export and other host-load variation.'
    else:
        receipt['master'] = binding(master)
    save(a.out / 'receipt.json', receipt)


if __name__ == '__main__':
    main()
