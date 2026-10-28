"""Fixed final-CFA completion controls. Root alone executes this file."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SAVED = ROOT / 'outputs/raw-quality-2026-10-27/native-spectral-controls-5/output/receipt.json'
SAVED_SHA = 'c747fc882838b755a65683681ea4f9b17b338bdb7b56e39d27ee67a891677010'
NAMES = ('constant-colours', 'flat-noise-a', 'flat-noise-b', 'neutral-structure',
         'independent-colours', 'green-diamond', 'shared-bin-conflict',
         'red-cancellation-diverse', 'near-fine-far-coarse', 'crossed-glint-sign-inversion')
LIMIT = 8 << 30


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ref(path):
    p = Path(path).resolve()
    a = p.stat()
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    b = p.stat()
    require((a.st_size, a.st_mtime_ns) == (b.st_size, b.st_mtime_ns), 'file changed during hashing')
    return dict(path=str(p), sha256=h.hexdigest(), bytes=b.st_size, mtime_ns=b.st_mtime_ns)


def binding(value):
    return {k: value[k] for k in ('path', 'sha256', 'bytes')}


def read(path):
    p = Path(path)
    require(p.stat().st_size < 16 << 20, 'oversized JSON')
    return json.loads(p.read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def load(path):
    name = 'final_cfa_completion_controls_producer'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def array_file(np, path, values, dtype='<f4'):
    a = np.ascontiguousarray(values, dtype=dtype)
    require(np.isfinite(a).all(), 'nonfinite saved array')
    with Path(path).open('xb') as f:
        f.write(a.tobytes())
    r = ref(path)
    r.update(shape=list(a.shape), dtype='f32le' if a.itemsize == 4 else 'f64le')
    return r


def masks(np, hw, origin):
    y, x = np.indices(hw, dtype=np.int64)
    p = 2 * ((y + origin[1]) % 2) + (x + origin[0]) % 2
    return (p == 0, (p == 1) | (p == 2), p == 3)


def normalise(np, cfa, development, origin):
    bits = lambda v: np.asarray(v, dtype=np.uint32).view(np.float32)
    black, white = bits(development['levels_bits'])
    wb = bits(development['wb_bits'])
    require(wb[1] == np.float32(1), 'held green WB differs')
    span = np.float32(white - black)
    result = np.empty_like(cfa, dtype=np.float32)
    for channel, mask in enumerate(masks(np, cfa.shape, origin)):
        gain = np.float32(wb[channel] / wb[1])
        # Literal native max0 * gain * 1.0 / f32 range, no reciprocal.
        value = np.maximum(cfa[mask], np.float32(0))
        value = np.multiply(value, gain, dtype=np.float32)
        value = np.multiply(value, np.float32(1), dtype=np.float32)
        result[mask] = np.divide(value, span, dtype=np.float32)
    return result


def parity(np, actual, expected):
    a, b = np.asarray(actual, dtype=np.float64), np.asarray(expected, dtype=np.float64)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), 'parity shape/finite')
    d = a - b
    maximum = float(np.max(np.abs(d)))
    rms = float(np.sqrt(np.mean(d * d)))
    maxbar = 3e-6 * max(1., float(np.max(np.abs(b))))
    rmsbar = 6e-7 * max(1., float(np.sqrt(np.mean(b * b))))
    return dict(max_abs=maximum, rms=rms, maximum_bar=maxbar, rms_bar=rmsbar,
                pass_=maximum <= maxbar and rms <= rmsbar)


def direct_reference(np, cfa, origin):
    """Independent full complex f64 DFT, explicit frequency mask, no FFT/helper."""
    h, w = cfa.shape
    ly, lx = 2 * (h - 1), 2 * (w - 1)
    sy = np.minimum(np.arange(ly), ly - np.arange(ly))
    sx = np.minimum(np.arange(lx), lx - np.arange(lx))
    extended = cfa[np.ix_(sy, sx)].astype(np.float64)
    ey = np.exp(-2j * np.pi * np.outer(np.arange(ly), np.arange(ly)) / ly) / np.sqrt(ly)
    ex = np.exp(-2j * np.pi * np.outer(np.arange(lx), np.arange(lx)) / lx) / np.sqrt(lx)
    yy = np.arange(ly)
    xx = np.arange(lx)
    ky = np.where(yy <= ly // 2, yy, yy - ly)
    kx = np.where(xx <= lx // 2, xx, xx - lx)
    outputs, weights = [], []
    for channel, known in enumerate(masks(np, (ly, lx), origin)):
        weight = np.empty((ly, lx), dtype=np.float64)
        for j, fy in enumerate(ky):
            for i, fx in enumerate(kx):
                if channel == 1:
                    lhs, rhs = 2 * (abs(int(fx)) * ly + abs(int(fy)) * lx), lx * ly
                    weight[j, i] = 2. if lhs < rhs else 1. if lhs == rhs else 0.
                else:
                    ax, ay = 4 * abs(int(fx)), 4 * abs(int(fy))
                    vx = 2. if ax < lx else 1. if ax == lx else 0.
                    vy = 2. if ay < ly else 1. if ay == ly else 0.
                    weight[j, i] = vx * vy
        spectrum = ey @ np.where(known, extended, 0.) @ ex.T
        reconstructed = ey.conj().T @ (spectrum * weight) @ ex.conj()
        require(float(np.max(np.abs(reconstructed.imag))) < 1e-10, 'direct reference conjugacy')
        outputs.append(reconstructed.real[:h, :w])
        weights.append(weight[:, :lx // 2 + 1])
    return np.stack(outputs, -1), weights


def component_scores(np, camera_dn, truth, components, origin=(256, 256)):
    y, x = np.indices(camera_dn.shape[:2], dtype=np.float64)
    x += origin[0]
    y += origin[1]
    columns = [np.ones_like(x)]
    for m in components:
        columns.append(np.cos(2 * np.pi * (m['fx'] * x + m['fy'] * y) + m['phase'])
                       * np.sinc(m['fx']) * np.sinc(m['fy']))
    design = np.stack([v.ravel() for v in columns], 1)
    singular = np.linalg.svd(design, compute_uv=False)
    rank = int(np.count_nonzero(singular > 1e-10 * singular[0]))
    rows = []
    if rank == design.shape[1]:
        fitted = np.linalg.lstsq(design, camera_dn.reshape(-1, 3), rcond=1e-10)[0]
        for k, mode in enumerate(components):
            for c, amp in enumerate(mode['amplitudes']):
                value = float(fitted[k + 1, c])
                bar = max(3., .1 * max(abs(v) for v in mode['amplitudes'])) if amp == 0 else max(1., .2 * abs(amp))
                error = abs(value - amp)
                rows.append(dict(component=k, channel=c, expected_amplitude_dn=amp,
                    amplitude_dn=value, absolute_error_dn=error, bar_dn=bar, pass_=error <= bar))
    error = camera_dn - truth
    chroma = error[..., [0, 2]] - error[..., 1, None]
    return dict(rgb_rmse_dn=float(np.sqrt(np.mean(error ** 2))),
        chroma_rmse_dn=float(np.sqrt(np.mean(chroma ** 2))), components=rows,
        basis_rank=rank, basis_columns=int(design.shape[1]),
        dense_camera_rank_is_not_original_CFA_identifiability=True)


def native_write(np, renderer, development_ref, camera_ref, source_ref, directory, hw, origin):
    cfg = dict(schema=1, camera_rgb=binding(camera_ref), source_receipt=binding(source_ref),
        width=hw[1], height=hw[0], active_origin_xy=list(origin), units='normalized-camera-RGB',
        development_receipt=binding(development_ref), out_dir=str(directory / 'native'),
        expected_executable_sha256=renderer['sha256'], parity_reference=None)
    save(directory / 'native-config.json', cfg)
    command = [renderer['path'], str(directory / 'native-config.json')]
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=30, check=False)
    (directory / 'native.log').write_text(p.stdout, encoding='utf-8')
    save(directory / 'native-process.json', dict(command=command, returncode=p.returncode))
    require(p.returncode == 0, 'native normalized-camera writer failed: ' + p.stdout)
    receipt = read(directory / 'native/receipt.json')
    require(receipt['status'] == 'COMPLETE_NORMALIZED_CAMERA_NATIVE_DEVELOPMENT'
            and receipt['complete'] and receipt['signed_camera_copy_bit_exact']
            and receipt['writer_completion_stages'] == 0
            and receipt['writer_demosaic_calls'] == 0 and receipt['input_clamp_applied'] is False
            and receipt['normalization_applied'] is False and receipt['pixel_readback_exact']
            and receipt['retained_input_bytes_and_metadata_unchanged']
            and receipt['native_dimensions'] == [hw[1], hw[0]]
            and receipt['active_origin_xy'] == list(origin)
            and receipt['quality_claim'] is False and receipt['photographic_admission'] is False,
            'native writer contract')
    for key in ('camera_rgb', 'rgb16', 'linear_rgb32'):
        actual = ref(receipt[key]['path'])
        require(actual['sha256'] == receipt[key]['sha256'] and actual['bytes'] == receipt[key]['bytes'],
                'native output binding')
    require(receipt['camera_rgb']['sha256'] == camera_ref['sha256'], 'writer changed camera values')
    return ref(directory / 'native/receipt.json')


def mechanics(np, torch, engine, out, development):
    rows, flags = [], []
    rng = np.random.default_rng(27411)
    # Exact finite-period oracle on signed data, odd/even extents and all phases.
    for hw, origin in [((9, 11), (0, 0)), ((10, 12), (1, 0)), ((13, 9), (0, 1)), ((9, 13), (1, 1))]:
        source = rng.normal(.2, .1, hw).astype(np.float32)
        expected, weights = direct_reference(np, source, origin)
        before = source.copy()
        completed = engine.complete_normalized(torch.from_numpy(source).cuda(), origin)
        pre = completed.pre_restore_rgb.cpu().numpy()
        final = completed.camera_rgb.cpu().numpy()
        a, b = parity(np, pre, expected), parity(np, final, expected)
        exact = all(np.array_equal(final[..., c][m], source[m]) for c, m in enumerate(masks(np, hw, origin)))
        mask_exact = all(np.array_equal(engine.mask(*hw, name).cpu().numpy(), weights[c])
                         for c, name in enumerate(('R', 'G', 'B')))
        flags.extend([a['pass_'], b['pass_'], exact, mask_exact, np.array_equal(source, before)])
        folder = out / f'dft-{hw[0]}-{hw[1]}-{origin[0]}-{origin[1]}'
        folder.mkdir()
        rows.append(dict(shape=hw, origin=origin, before_restore=a, complete=b,
            known_sites_bit_exact=exact, integer_masks_exact=mask_exact,
            source=array_file(np, folder / 'source.f32le', source),
            actual=array_file(np, folder / 'actual.f32le', final),
            oracle=array_file(np, folder / 'oracle.f64le', expected, '<f8'), evidence=completed.evidence))
    impulses = []
    for edge in (True, False):
        for phase, (dx, dy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
            source = np.zeros((13, 13), np.float32)
            x, y = (dx, dy) if edge else (6 + dx, 6 + dy)
            source[y, x] = np.float32(.5)
            expected, _ = direct_reference(np, source, (0, 0))
            result = engine.complete_normalized(torch.from_numpy(source).cuda(), (0, 0))
            check = parity(np, result.pre_restore_rgb.cpu().numpy(), expected)
            flags.append(check['pass_'])
            impulses.append(dict(edge=edge, phase=phase, xy=[x, y], before_restore=check))
    # Complete native normalization includes negatives, all colors, finite high values.
    raw = np.resize(np.array([-32., -0., .001, 1., 511.3, 14848., 18000.], dtype=np.float32), (11, 13))
    normalization = []
    for origin in ((0, 0), (1, 1)):
        expected = normalise(np, raw, development, origin)
        actual = engine.complete(torch.from_numpy(raw).cuda(), development, origin)
        exact = np.array_equal(actual.normalized_cfa.cpu().numpy().view(np.uint32), expected.view(np.uint32))
        flags.append(exact)
        normalization.append(dict(origin=origin, native_arithmetic_bits_exact=exact, evidence=actual.evidence))
    # Compatible green mode lies inside the diamond but outside either square green grid.
    y, x = np.indices((17, 17), dtype=np.float64)
    truth = np.broadcast_to(np.array([.2, .25, .3]), (17, 17, 3)).copy()
    truth[..., 1] += .05 * np.cos(2 * np.pi * .3125 * x) * np.cos(2 * np.pi * .0625 * y)
    source = np.empty((17, 17), np.float32)
    for c, m in enumerate(masks(np, source.shape, (0, 0))):
        source[m] = truth[..., c][m]
    ordinary = engine.complete_normalized(torch.from_numpy(source).cuda(), (0, 0))
    positive = parity(np, ordinary.camera_rgb.cpu().numpy(), truth)
    green_folder = out / 'green-diamond-mechanics'
    green_folder.mkdir()
    positive['actual'] = array_file(np, green_folder / 'actual.f32le', ordinary.camera_rgb.cpu().numpy())
    positive['truth'] = array_file(np, green_folder / 'truth.f64le', truth, '<f8')
    flags.append(positive['pass_'])
    foils = {}
    for name in ('green-square', 'swap-rb', 'double-gain'):
        wrong = engine.complete_normalized(torch.from_numpy(source).cuda(), (0, 0), diagnostic_foil=name)
        check = parity(np, wrong.pre_restore_rgb.cpu().numpy(), truth)
        check['actual_pre_restore'] = array_file(np, green_folder / (name + '.f32le'), wrong.pre_restore_rgb.cpu().numpy())
        foils[name] = check
        flags.append(not check['pass_'])
    # Wrong missing-site scorer itself cannot pass a flat field with a displaced inferred value.
    broken = ordinary.camera_rgb.cpu().numpy().copy()
    broken[0, 0, 1] += .02
    foils['missing-site-corruption'] = parity(np, broken, truth)
    flags.append(not foils['missing-site-corruption']['pass_'])
    return dict(dft=rows, impulses=impulses, normalization=normalization, green_diamond=positive, foils=foils), flags


def adverses(np, torch, engine, out):
    records = []
    # Identical finite CFA has two incompatible RGB truths. Both truths are retained.
    y, x = np.indices((41, 41), dtype=np.float64)
    neutral = np.repeat((.2 + .05 * np.cos(2 * np.pi * .3 * x))[..., None], 3, axis=2)
    chromatic = neutral.copy()
    chromatic[..., 0] = .2 + .05 * np.cos(2 * np.pi * .2 * x)
    chromatic[..., 2] = .2 - .05 * np.cos(2 * np.pi * .2 * x)
    samples = []
    for truth in (neutral, chromatic):
        cfa = np.empty((41, 41), np.float32)
        for c, m in enumerate(masks(np, cfa.shape, (0, 0))):
            cfa[m] = truth[..., c][m]
        samples.append(cfa)
    require(np.array_equal(samples[0], samples[1]), 'declared ambiguity must have bit-identical CFA')
    a = engine.complete_normalized(torch.from_numpy(samples[0]).cuda(), (0, 0)).camera_rgb.cpu().numpy()
    b = engine.complete_normalized(torch.from_numpy(samples[1]).cuda(), (0, 0)).camera_rgb.cpu().numpy()
    require(np.array_equal(a, b), 'same-input ambiguity output differs')
    folder = out / 'neutral-chromatic-ambiguity'
    folder.mkdir()
    records.append(dict(name=folder.name, source=array_file(np, folder / 'same-cfa.f32le', samples[0]),
        actual=array_file(np, folder / 'actual.f32le', a),
        neutral_truth=array_file(np, folder / 'neutral-truth.f64le', neutral, '<f8'),
        chromatic_truth=array_file(np, folder / 'chromatic-truth.f64le', chromatic, '<f8'),
        neutral_error=parity(np, a, neutral), chromatic_error=parity(np, a, chromatic),
        identical_input_and_output=True, no_universal_recovery_requirement=True))
    # Full-field affine and discontinuity errors include the real reflection defect.
    y, x = np.indices((33, 35), dtype=np.float64)
    affine = np.stack([.12 + .003 * x + .001 * y, .2 + .001 * x - .002 * y,
                       .28 - .002 * x + .001 * y], -1)
    step = np.repeat((.1 + .3 * (x >= 17))[..., None], 3, axis=2)
    for name, truth in (('affine-boundary', affine), ('neutral-step-ringing', step)):
        source = np.empty(truth.shape[:2], np.float32)
        for c, m in enumerate(masks(np, source.shape, (1, 0))):
            source[m] = truth[..., c][m]
        actual = engine.complete_normalized(torch.from_numpy(source).cuda(), (1, 0)).camera_rgb.cpu().numpy()
        folder = out / name
        folder.mkdir()
        error = actual.astype(np.float64) - truth
        overshoot = max(0., float(np.max(actual) - np.max(truth)), float(np.min(truth) - np.min(actual)))
        records.append(dict(name=name, source=array_file(np, folder / 'source.f32le', source),
            actual=array_file(np, folder / 'actual.f32le', actual),
            truth=array_file(np, folder / 'truth.f64le', truth, '<f8'),
            whole_field_rms=float(np.sqrt(np.mean(error ** 2))), whole_field_max=float(np.max(np.abs(error))),
            overshoot_normalized=overshoot, descriptive_quality_pass=bool(np.max(np.abs(error)) <= .01 and overshoot <= .005),
            no_exact_affine_or_no_ringing_claim=True))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--renderer-binding', required=True, type=Path)
    parser.add_argument('--development-receipt', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / 'outputs').resolve()) and not out.exists(), 'fresh workspace output required')
    out.mkdir(parents=True)
    started = time.perf_counter()
    inputs = {}

    def remember(path, expected=None):
        value = ref(path)
        if expected is not None:
            require(value['sha256'] == expected['sha256'] and value['bytes'] == expected['bytes'], 'bound input differs')
        if value['path'] in inputs:
            require(inputs[value['path']] == value, 'input changed during controls')
        inputs[value['path']] = value
        return value

    state = dict(status='INCOMPLETE_FINAL_CFA_COLOR_CONTROLS', complete=False, controls_pass=False,
        quality_pass=False, quality_claim=False, photographic_admission=False, cases=[], mechanics={})
    try:
        import numpy as np
        import torch
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        require(not torch.is_autocast_enabled(), 'autocast enabled')
        for p in (__file__, HERE / 'controls-protocol.md', HERE / 'spectral-completion.py',
                  HERE / 'brief.md', args.renderer_binding, args.development_receipt):
            remember(p)
        require(remember(SAVED)['sha256'] == SAVED_SHA, 'only fixed controls5 allowed')
        saved = read(SAVED)
        require(saved['complete'] and saved['controls_pass'] and tuple(c['name'] for c in saved['cases']) == NAMES, 'saved case census')
        renderer_config = read(args.renderer_binding)
        renderer = renderer_config.get('executable', renderer_config)
        remember(renderer['path'], renderer)
        development_ref = remember(args.development_receipt)
        development = read(args.development_receipt)
        module = load(HERE / 'spectral-completion.py')
        for path in module.source_dependencies():
            remember(path)
        engine = module.SpectralCompletion(torch, device_limit_bytes=LIMIT)
        state['runtime_before'] = engine.metadata(strict=True)
        state['threads'] = dict(cpu=4, interop=1, tf32=False, autocast=False)
        flags = []
        # The actual saved constant and two noisy-flat cases are completed first.
        for case in saved['cases']:
            case_out = out / case['name']
            case_out.mkdir()
            truth_ref = remember(case['truth']['path'], case['truth'])
            require(truth_ref['bytes'] == 64 * 64 * 3 * 8, 'truth extent')
            truth = np.fromfile(truth_ref['path'], dtype='<f8').reshape(64, 64, 3)
            row = dict(name=case['name'], inherited_quality_pass=case['quality_pass'], arms={})
            for arm in ('candidate', 'uniform'):
                old_ref = case['arms'][arm]['development_receipt']
                remember(old_ref['path'], old_ref)
                old = read(old_ref['path'])
                require(old['complete'] and old['native_dimensions'] == [64, 64]
                    and old['active_origin_xy'] == [256, 256] and old['demosaic_stages'] == 1,
                    'saved native contract')
                require(old['development'] == {k: development[k] for k in old['development']}, 'held development mismatch')
                cfa_ref = remember(old['cfa']['path'], old['cfa'])
                camera_ref = remember(old['camera_rgb']['path'], old['camera_rgb'])
                require(cfa_ref['bytes'] == 64 * 64 * 4 and camera_ref['bytes'] == 64 * 64 * 3 * 4, 'saved stage extent')
                cfa = np.fromfile(cfa_ref['path'], dtype='<f4').reshape(64, 64)
                baseline = np.fromfile(camera_ref['path'], dtype='<f4').reshape(64, 64, 3)
                device_input = torch.from_numpy(cfa.copy()).cuda()
                result = engine.complete(device_input, development, (256, 256))
                actual = result.camera_rgb.cpu().numpy()
                normalized = result.normalized_cfa.cpu().numpy()
                expected_normalized = normalise(np, cfa, development, (256, 256))
                norm_exact = np.array_equal(normalized.view(np.uint32), expected_normalized.view(np.uint32))
                input_exact = np.array_equal(device_input.cpu().numpy().view(np.uint32), cfa.view(np.uint32))
                site_exact = all(np.array_equal(actual[..., c][m].view(np.uint32), normalized[m].view(np.uint32))
                                 for c, m in enumerate(masks(np, cfa.shape, (256, 256))))
                pre = result.pre_restore_rgb.cpu().numpy()
                pre_checks = [parity(np, pre[..., c][m], normalized[m])
                              for c, m in enumerate(masks(np, cfa.shape, (256, 256)))]
                require(np.isfinite(actual).all(), 'nonfinite completed camera')
                flags.extend([norm_exact, input_exact, site_exact, all(v['pass_'] for v in pre_checks)])
                target = case_out / arm
                target.mkdir()
                output_camera = array_file(np, target / 'camera-rgb-normalized.f32le', actual)
                output_norm = array_file(np, target / 'normalized-cfa.f32le', normalized)
                producer_record = dict(status='COMPLETE_FINAL_CFA_COLOR_COMPLETION', complete=True,
                    width=64, height=64, active_origin_xy=[256, 256], units='normalized-camera-RGB',
                    input_cfa=cfa_ref, normalized_cfa=output_norm, camera_rgb=output_camera,
                    completion_stages=1, evidence=result.evidence, quality_claim=False, photographic_admission=False)
                save(target / 'completion.json', producer_record)
                native = native_write(np, renderer, development_ref, output_camera,
                    ref(target / 'completion.json'), target, (64, 64), (256, 256))
                developed = read(native['path'])
                require(developed['material_metadata'] == old['material_metadata']
                        and developed['linear_material_metadata'] == old['linear_material_metadata'],
                        'same-CFA native development material differs')
                wb = np.array([struct.unpack('<f', struct.pack('<I', v))[0] for v in development['wb_bits']])
                black, white = [struct.unpack('<f', struct.pack('<I', v))[0] for v in development['levels_bits']]
                actual_dn = actual.astype(np.float64) * (white - black) / wb
                baseline_dn = baseline.astype(np.float64) * (white - black) / wb
                score = component_scores(np, actual_dn, truth, case['component_truth'])
                baseline_score = component_scores(np, baseline_dn, truth, case['component_truth'])
                inherited = case['arms'][arm]['scores']
                require(all(abs(baseline_score[k] - inherited[k]) <= 1e-7
                            for k in ('rgb_rmse_dn', 'chroma_rmse_dn')), 'MHC scorer reproduction')
                require(all(abs(v['amplitude_dn'] - inherited['components'][i]['measured_amplitude']) <= 1e-7
                            for i, v in enumerate(baseline_score['components'])), 'MHC component scorer reproduction')
                comparison = {k: dict(value=score[k], baseline=baseline_score[k],
                    bar=1.15 * baseline_score[k] + .5, pass_=score[k] <= 1.15 * baseline_score[k] + .5)
                    for k in ('rgb_rmse_dn', 'chroma_rmse_dn')}
                quality = all(v['pass_'] for v in comparison.values()) and all(v['pass_'] for v in score['components'])
                row['arms'][arm] = dict(cfa_input=cfa_ref, camera=output_camera, native_receipt=native,
                    normalization_bits_exact=norm_exact, input_bits_unchanged=input_exact, known_sites_bits_exact=site_exact,
                    pre_restoration_known_sites=pre_checks,
                    scores=score, same_CFA_MHC_scores=baseline_score, image_bars=comparison, quality_pass=quality,
                    inherited_scores=case['arms'][arm]['scores'], producer=result.evidence)
                del result, device_input
            row['quality_pass'] = all(a['quality_pass'] for a in row['arms'].values())
            state['cases'].append(row)
            save(case_out / 'comparison.json', row)
        state['mechanics'], extra_flags = mechanics(np, torch, engine, out, development)
        flags.extend(extra_flags)
        state['adverses'] = adverses(np, torch, engine, out)
        state['runtime_after'] = engine.metadata(strict=True)
        torch.cuda.synchronize()
        peaks = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
        require(max(peaks.values()) <= LIMIT, 'Torch memory bound exceeded')
        for value in inputs.values():
            require(ref(value['path']) == value, 'input changed after controls')
        state.update(status='COMPLETE_FINAL_CFA_COLOR_CONTROLS', complete=True, controls_pass=all(flags),
            quality_pass=all(c['quality_pass'] for c in state['cases'])
                and all(a.get('descriptive_quality_pass', True) for a in state['adverses']),
            saved_cases_quality_pass=all(c['quality_pass'] for c in state['cases']),
            incompatible_truth_pair_is_descriptive_not_universal_pass_requirement=True,
            source_bindings=list(inputs.values()),
            inputs_unchanged=True, original_RAW_reads=0, saved_case_count=10, delivered_arm_count=20,
            gpu_peaks=peaks, libraries=dict(python=sys.version, numpy=np.__version__, torch=torch.__version__),
            elapsed_seconds_qpc=time.perf_counter() - started,
            command=[sys.executable, '-B', '-X', 'faulthandler', str(Path(__file__).resolve()),
                     '--out', str(out), '--renderer-binding', str(args.renderer_binding.resolve()),
                     '--development-receipt', str(args.development_receipt.resolve())])
        save(out / 'receipt.json', state)
        print(json.dumps({k: state[k] for k in ('status', 'complete', 'controls_pass', 'quality_pass')}), flush=True)
    except BaseException as error:
        state.update(error=repr(error), traceback=traceback.format_exc(), source_bindings=list(inputs.values()),
                     elapsed_seconds_qpc=time.perf_counter() - started)
        save(out / 'receipt.json', state)
        raise


if __name__ == '__main__':
    main()
