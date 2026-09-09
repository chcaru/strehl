"""Independent saved comparison read; no producer imports, model fit, or RAW decode.

Run once after root releases both four-case comparison arms. All masks/truth below
are fixed before data. TIFF fidelity samples the known CFA channel only; all RGB
pixels are decoded and hashed. This is an operator fixture, not sensor calibration.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
IDS = ('split-offset', 'nonnegative-depth', 'noisy-flat', 'noisy-depth')
W, H, RANGE = 64, 48, 15360 - 512
READ_LIMIT, WRITE_LIMIT = 8 * 1024**2, 256 * 1024
read_bytes = 0
read_refs = []


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(path, cap):
    global read_bytes
    path = Path(path).resolve(strict=True)
    n = path.stat().st_size
    need(0 < n <= cap and read_bytes + n <= READ_LIMIT, 'read bound')
    read_bytes += n
    with path.open('rb') as f:
        raw = f.read(n + 1)
    need(len(raw) == n and path.stat().st_size == n, 'changed saved buffer')
    ref = {'path': str(path), 'bytes': n, 'sha256': hashlib.sha256(raw).hexdigest()}
    read_refs.append(ref)
    return raw, ref


def artifact(ref, directory, name, cap):
    path = (directory / name).resolve(strict=True)
    need(Path(ref['path']).samefile(path), 'saved artifact role')
    raw, actual = read(path, cap)
    need(type(ref['bytes']) is int and ref['bytes'] == actual['bytes']
         and ref['sha256'] == actual['sha256'], 'saved artifact hash/extent')
    return raw, actual


def truth(case):
    y, x = np.indices((H, W), dtype=np.int64)
    if case == 'split-offset':
        value = (x >= 32).astype(np.float64)
    elif case == 'noisy-flat':
        value = np.zeros((H, W), dtype=np.float64)
    else:
        left = np.where(y < 20, 1, 1 + 12 * ((x // 4 + y // 4) % 2))
        right = np.where(y < 20, 3, 3 + 20 * ((x // 5 + y // 3) % 2))
        value = np.where(x < 32, left, right).astype(np.float64)
        if case == 'nonnegative-depth':
            value += 64
    return np.broadcast_to(value, (4, H, W))


def masks():
    # Re-choice: smaller interior regions and two boundary widths, versus the
    # producer's x8..23/40..55 and width8 boundary. All endpoints are half-open.
    out = {}
    for name, rects in (
        ('whole', [(0, 0, 64, 48)]),
        ('flat-left', [(10, 10, 22, 14)]),
        ('flat-right', [(42, 10, 54, 14)]),
        ('texture-left', [(10, 26, 22, 38)]),
        ('texture-right', [(42, 26, 54, 38)]),
        ('boundary-2', [(31, 24, 33, 40)]),
        ('boundary-12', [(26, 24, 38, 40)]),
    ):
        mask = np.zeros((H, W), dtype=bool)
        for x0, y0, x1, y1 in rects:
            mask[y0:y1, x0:x1] = True
        out[name] = (mask, rects)
    return out


MASKS = masks()


def metrics(values, target, mask):
    error = values.astype(np.float64)[:, mask] - target[:, mask]
    def one(v):
        return {'samples': int(v.size), 'bias_dn': float(v.mean()),
                'mae_dn': float(np.abs(v).mean()),
                'rmse_dn': float(np.sqrt(np.mean(v * v))),
                'max_abs_dn': float(np.abs(v).max())}
    return {'pooled': one(error), 'planes': [one(v) for v in error]}


def decoded(raw):
    with tifffile.TiffFile(io.BytesIO(raw)) as tif:
        need(len(tif.pages) == 1, 'one TIFF image')
        page = tif.pages[0]
        need(page.shape == (96, 128, 3) and page.dtype == np.dtype('uint16'),
             'native RGB16 TIFF dimensions/type')
        need(int(page.photometric) == 2 and int(page.planarconfig) == 1,
             'native interleaved RGB TIFF')
        rgb = page.asarray()  # Actual full-image decode, once per TIFF.
    known = np.stack([rgb[dy::2, dx::2, c]
                      for dx, dy, c in ((0, 0, 0), (1, 0, 1), (0, 1, 1), (1, 1, 2))])
    return rgb, known


def arm(directory, signed):
    raw, result_ref = read(directory / 'result.json', 128 * 1024)
    result = json.loads(raw)
    need(result['schema'] == 'native-signed-black-comparison-v1'
         and result['signed'] is signed
         and result['geometry'] == {'width': W, 'height': H}, 'comparison identity')
    need(result['levels'] == {'black': 512.0, 'white': 15360.0}, 'fixed levels')
    need(result['level_sizes'] == [[64, 48], [32, 24], [16, 12]], 'actual pyramid geometry')
    need(result['noise']['gain_dn_per_e'] == 1.0 and result['noise']['read_noise_e'] == 4.0
         and result['noise']['iso'] == 160.0, 'fixed injected model')
    need(result['configured_bands'] == 7 and result['cfa_order'] == ['R', 'G1', 'G2', 'B'],
         'fixed production configuration')
    need([r['id'] for r in result['cases']] == list(IDS), 'fixed four cases')
    rows, buffers = [], {}
    for row in result['cases']:
        case = row['id']
        need(row['source_calls'] == [1] * 5 and row['folds'] == 5, 'actual five folds')
        need(type(row['negative_consumed_values']) is int, 'negative count type')
        need((row['negative_consumed_values'] > 0) == (signed and case != 'nonnegative-depth'),
             'negative consumed exercise')
        observed = row['folds_observed']
        need(len(observed) == 5 and [r['index'] for r in observed] == list(range(5)),
             'ordered consumed records')
        need(all(r['beta_prefix'] == [] for r in observed), 'no-map white-beta path')
        need(all(math.isfinite(r['variance']['min']) and math.isfinite(r['variance']['max'])
                 and 0 <= r['variance']['min'] <= r['variance']['max'] for r in observed),
             'finite actual variance')
        floats, float_ref = artifact(row['collapsed'], directory, case + '.f32', 49152)
        need(len(floats) == 49152, 'four complete CFA planes')
        cfa = np.frombuffer(floats, dtype='<f4').reshape(4, H, W)
        need(np.isfinite(cfa).all(), 'finite actual collapsed values')
        tiff, tiff_ref = artifact(row['tiff'], directory, case + '.tiff', 256 * 1024)
        rgb, known = decoded(tiff)
        clipped = np.maximum(cfa, np.float32(0))
        # Independent known-channel writer check. One output code allows only
        # floating-rounding differences; retain exact discrepancy counts too.
        norm = np.minimum(clipped / np.float32(RANGE), np.float32(1))
        codes = (norm * np.float32(65535) + np.float32(0.5)).astype(np.uint16)
        delta = np.abs(known.astype(np.int32) - codes.astype(np.int32))
        need(int(delta.max()) <= 1, 'known CFA channel writer association')
        target = truth(case)
        views = {'collapsed-signed': cfa, 'collapsed-clipped': clipped,
                 'tiff-known-cfa': known.astype(np.float64) * (RANGE / 65535.0)}
        scores = {view: {name: metrics(values, target, mask)
                         for name, (mask, _) in MASKS.items()} for view, values in views.items()}
        rows.append({'case': case, 'collapsed': float_ref, 'tiff': tiff_ref,
                     'negative_consumed_values': row['negative_consumed_values'],
                     'negative_collapsed_values': int((cfa < 0).sum()),
                     'collapsed_min': float(cfa.min()), 'collapsed_max': float(cfa.max()),
                     'tiff_decoded_samples': int(rgb.size),
                     'tiff_pixels_sha256': hashlib.sha256(rgb.astype('<u2').tobytes()).hexdigest(),
                     'writer_max_code_error': int(delta.max()),
                     'writer_unequal_known_samples': int((delta != 0).sum()),
                     'scores': scores, 'fixture_source_claims': row['fixture']})
        buffers[case] = (floats, tiff, rgb)
    return {'result': result_ref, 'recipe': result['recipe'], 'cases': rows}, buffers


def main():
    start, cpu = time.perf_counter(), time.process_time()
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    need(args.output.resolve().parent == HERE and not args.output.exists(), 'fresh local result')
    _, own_source = read(Path(__file__), 64 * 1024)
    clamped, a = arm(HERE / 'comparison-clamped', False)
    signed, b = arm(HERE / 'comparison-signed', True)
    need(clamped['recipe'] == signed['recipe'], 'same fixed recipe across arms')
    same = {case: {'f32_bytes': a[case][0] == b[case][0],
                   'tiff_bytes': a[case][1] == b[case][1],
                   'decoded_tiff_pixels': bool(np.array_equal(a[case][2], b[case][2]))}
            for case in IDS}
    need(all(same['nonnegative-depth'].values()), 'nonnegative noiseless exact null')
    changes = []
    for ca, cb in zip(clamped['cases'], signed['cases']):
        need(ca['fixture_source_claims'] == cb['fixture_source_claims'], 'same actual source hashes across arms')
        differences = {}
        for view in ca['scores']:
            differences[view] = {}
            for mask in MASKS:
                x, y = ca['scores'][view][mask]['pooled'], cb['scores'][view][mask]['pooled']
                differences[view][mask] = {'signed_minus_clamped_rmse_dn': y['rmse_dn'] - x['rmse_dn'],
                                          'signed_minus_clamped_abs_bias_dn': abs(y['bias_dn']) - abs(x['bias_dn'])}
        changes.append({'case': ca['case'], 'changes': differences})
    result = {'schema': 'native-signed-black-independent-read-v1', 'status': 'SAVED_RESULTS_READ',
              'source_sha256': own_source['sha256'],
              'masks_half_open': {k: rects for k, (_, rects) in MASKS.items()},
              'clamped': clamped, 'signed': signed, 'equality': same, 'paired_changes': changes,
              'reads': read_refs, 'read_bytes': read_bytes,
              'cpu_before_publication': time.process_time() - cpu,
              'wall_before_publication': time.perf_counter() - start,
              'scope': 'Fixed synthetic operator comparison. Spatial errors are not temporal noise estimates. '
                       'Known-channel TIFF fidelity only; interpolated-channel quality is not independently scored. '
                       'One-code writer tolerance is a rounding bound, not a fidelity threshold. '
                       'Neutral CFA truth does not independently establish color/permutation accuracy. '
                       'Negative changes favor signed on that metric; no automatic quality or calibration PASS.'}
    raw = json.dumps(result, allow_nan=False, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    need(len(raw) <= WRITE_LIMIT, 'result write bound')
    with args.output.open('xb') as f:
        f.write(raw)
    print(json.dumps({'result': str(args.output.resolve()), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()}))


if __name__ == '__main__':
    main()
