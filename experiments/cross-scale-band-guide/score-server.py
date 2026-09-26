"""Bounded native bridge: one source in flight; no RAW access or image cache.

Binary stdin/stdout only: u32-LE JSON length, UTF8 JSON, then declared LE-f32
payload. All diagnostic text goes to stderr. Original source coefficients are
never reconstructed here; the caller consumes returned weights in native Rust.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
GENERIC_SHA = '587e373f6d6afb81e120ca74c4c0094a86b1abd4a020724de38e1b4397ba8003'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def exact(stream, count):
    result = bytearray(count)
    view = memoryview(result)
    offset = 0
    while offset < count:
        got = stream.readinto(view[offset:])
        need(got is not None and got > 0, 'truncated bridge payload')
        offset += got
    return result


def read_header(stream):
    count = struct.unpack('<I', exact(stream, 4))[0]
    need(0 < count <= 65536, 'invalid bridge header length')
    return json.loads(exact(stream, count))


def write_header(stream, value):
    data = json.dumps(value, allow_nan=False, separators=(',', ':')).encode()
    need(len(data) <= 65536, 'response header too large')
    stream.write(struct.pack('<I', len(data)))
    stream.write(data)
    stream.flush()


def module():
    import hashlib
    path = HERE / 'generic-consumer.py'
    need(hashlib.sha256(path.read_bytes()).hexdigest() == GENERIC_SHA, 'generic consumer changed')
    spec = importlib.util.spec_from_file_location('native_stream_generic', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def serve(args):
    generic = module()
    helper, scorer = generic.imports()
    need(generic.sha(args.weights) == args.weights_sha256, 'model binding differs')
    need(not args.receipt.exists(), 'fresh server receipt required')
    np, torch = helper.runtime()
    torch.cuda.set_per_process_memory_fraction(min(1., 8 * 1024**3 / torch.cuda.get_device_properties(0).total_memory))
    torch.cuda.reset_peak_memory_stats()
    model = scorer.load_model(args.weights, torch)
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    started = time.monotonic()
    start = read_header(stdin)
    need(start['op'] == 'start' and start['schema'] == 1, 'start command required')
    sizes, n, value_range = start['sizes'], start['source_count'], start['range']
    bands = len(sizes) - 1
    need(bands in (3, 7) and 1 <= n <= 70 and math.isfinite(value_range) and value_range > 0,
         'bounded3/7band N1..70 scope')
    need(all(len(s) == 2 and all(isinstance(v, int) and v > 0 for v in s) for s in sizes), 'invalid sizes')
    need(all(sizes[k+1] == [(sizes[k][0]+1)//2, (sizes[k][1]+1)//2] for k in range(bands)), 'pyramid recurrence differs')
    need(sizes[0][0] <= 3460 and sizes[0][1] <= 2306, 'full-domain bound exceeded')
    indices = start['score_indices']
    need(indices and indices == sorted(set(indices)) and all(isinstance(i, int) and 0 <= i < n for i in indices), 'score order invalid')
    pixels = [w*h for w, h in sizes[:-1]]
    total = [torch.zeros((1, 4, h, w), device='cuda') for w, h in sizes[:-1]]
    square = [torch.zeros_like(v) for v in total]
    statistics = None
    seen, scored = 0, 0
    records = []
    write_header(stdout, {'ok': True, 'op': 'start', 'model_sha256': args.weights_sha256,
                         'generic_consumer_sha256': GENERIC_SHA,
                         'scorer_sha256': generic.SCORER_SHA, 'consumer_sha256': generic.OLD_SHA})

    def arrays(channels):
        result = []
        for w, h in sizes[:-1]:
            values = np.frombuffer(exact(stdin, channels*w*h*4), dtype='<f4').reshape(1, channels, h, w)
            need(bool(np.isfinite(values).all()), 'nonfinite native payload')
            result.append(torch.from_numpy(values).to('cuda'))
        return result

    with torch.no_grad():
        while True:
            command = read_header(stdin)
            op = command.get('op')
            if op == 'stats':
                need(statistics is None and seen < n and command['index'] == seen
                     and command['floats'] == 4*sum(pixels), 'statistics order/length differs')
                c = arrays(4)
                for k in range(bands):
                    total[k] = total[k] + c[k]
                    square[k] = square[k] + c[k].square()
                del c
                seen += 1
                write_header(stdout, {'ok': True, 'op': op, 'index': seen-1})
            elif op == 'finish-stats':
                need(statistics is None and seen == n, 'incomplete or repeated statistics')
                statistics = []
                for k in range(bands):
                    mean, second = total[k]/n, square[k]/n
                    scale = (second.mean(1, keepdim=True)+(value_range/16384.)**2).sqrt()
                    sd = (second-mean.square()).clamp_min(0).sqrt()
                    need(bool(torch.isfinite(scale).all() and (scale > 0).all()), 'invalid context scale')
                    statistics.append({'mean': mean/scale, 'sd': sd/scale, 'scale': scale})
                total.clear()
                square.clear()
                write_header(stdout, {'ok': True, 'op': op, 'source_count': seen})
            elif op == 'score':
                need(statistics is not None and scored < len(indices) and command['index'] == indices[scored]
                     and command['floats'] == 9*sum(pixels), 'score order/length differs')
                torch.cuda.synchronize()
                clock = time.monotonic()
                coefficients = arrays(4)
                old_features = arrays(5)
                # The ordinal is a protocol check, never a model input. This is a
                # one-source local view of the same frozen generic feature API.
                case = {'bands': bands, 'meta': {'source_count': n, 'range': value_range},
                        'arrays': {f'features-{k}': v for k, v in enumerate(old_features)}}
                output = []
                for k in range(bands):
                    features = generic.source_features(case, 0, k, statistics, coefficients, helper, scorer, torch)
                    weight = generic.score_source(model, features, torch)[:, 0]
                    need(bool(torch.isfinite(weight).all() and (weight > 0).all() and (weight <= 2).all()), 'invalid model weight')
                    output.append(weight.cpu().numpy().astype('<f4', copy=False))
                    del features, weight
                del coefficients, old_features, case
                torch.cuda.synchronize()
                elapsed = time.monotonic()-clock
                write_header(stdout, {'ok': True, 'op': op, 'index': indices[scored], 'floats': sum(pixels), 'seconds': elapsed})
                for value in output:
                    stdout.write(value.tobytes())
                stdout.flush()
                records.append({'index': indices[scored], 'seconds': elapsed})
                scored += 1
            elif op == 'finish':
                need(seen == n and statistics is not None and scored == len(indices), 'premature finish')
                need(generic.sha(args.weights) == args.weights_sha256, 'model changed while serving')
                receipt = {'schema': 1, 'source_count': n, 'sizes': sizes, 'scored_indices': indices,
                           'model_sha256': args.weights_sha256, 'generic_consumer_sha256': GENERIC_SHA,
                           'scorer_sha256': generic.SCORER_SHA, 'consumer_sha256': generic.OLD_SHA,
                           'source_chunk': 1, 'network_tile': 256, 'truth_read': False,
                           'statistics': 'sequential-f32-sums-and-squares', 'scores': records,
                           'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
                           'peak_cuda_reserved_bytes': torch.cuda.max_memory_reserved(),
                           'seconds': time.monotonic()-started}
                generic.save(args.receipt, receipt)
                write_header(stdout, {'ok': True, 'op': op, 'receipt_sha256': generic.sha(args.receipt)})
                return
            else:
                raise RuntimeError('unexpected bridge operation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--weights-sha256', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    try:
        serve(args)
    except Exception as error:
        # A refusal is terminal; no zero/uniform fallback or output rescue.
        try:
            write_header(sys.stdout.buffer, {'ok': False, 'error': str(error)})
        finally:
            raise
