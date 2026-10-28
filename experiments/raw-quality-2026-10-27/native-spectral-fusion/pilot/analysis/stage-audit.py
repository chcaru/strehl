"""Read-only fixed controls5 original/CFA/final-camera stage accounting.

No producer import, FFT, demosaic, RAW decoder, reconstruction or new fixture.
Root schedules: python -B -X faulthandler stage-audit.py --out <fresh-output>.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = ROOT / 'outputs/raw-quality-2026-10-27/native-spectral-controls-5/output/receipt.json'
SOURCE_SHA = 'c747fc882838b755a65683681ea4f9b17b338bdb7b56e39d27ee67a891677010'
CASE_NAMES = ('constant-colours', 'flat-noise-a', 'flat-noise-b', 'neutral-structure',
              'independent-colours', 'green-diamond', 'shared-bin-conflict',
              'red-cancellation-diverse', 'near-fine-far-coarse', 'crossed-glint-sign-inversion')
PHASES = ((0, 0), (1, 0), (0, 1), (1, 1))
CHANNELS = (0, 1, 1, 2)
MEANS = (2048., 3072., 2560.)
ORIGIN = (256, 256)
RANK_RELATIVE = 1e-10


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ref(path):
    p = Path(path).resolve()
    before = p.stat()
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    after = p.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'changed during hash')
    return dict(path=str(p), sha256=h.hexdigest(), bytes=after.st_size, mtime_ns=after.st_mtime_ns)


def read(path):
    p = Path(path)
    require(p.stat().st_size < 4 << 20, 'bounded receipt required')
    return json.loads(p.read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def bits(values):
    return [struct.unpack('<f', struct.pack('<I', v))[0] for v in values]


def describe(np, values, x, y, modes, channel, transfers=None, shift=(0., 0.)):
    columns = [np.ones(values.size, dtype=np.float64)]
    for m in modes:
        phase = 2 * np.pi * (m['fx'] * (x - shift[0]) + m['fy'] * (y - shift[1])) + m['phase']
        columns.append(np.cos(phase).ravel() * np.sinc(m['fx']) * np.sinc(m['fy']))
    design = np.stack(columns, axis=1)
    observed = np.asarray(values, dtype=np.float64).ravel()
    require(np.isfinite(observed).all(), 'nonfinite saved field')
    u, s, _ = np.linalg.svd(design, full_matrices=False)
    rank = int(np.count_nonzero(s > RANK_RELATIVE * s[0]))
    coefficients = None
    if rank == design.shape[1]:
        coefficients = np.linalg.lstsq(design, observed, rcond=RANK_RELATIVE)[0]
    projection = u[:, :rank] @ (u[:, :rank].T @ observed)
    transfer = [1.] * len(modes) if transfers is None else transfers
    expected_coeff = np.asarray([MEANS[channel]] + [m['amplitudes'][channel] * t for m, t in zip(modes, transfer)])
    expected = design @ expected_coeff
    estimates = None if coefficients is None else [dict(component=k,
        measured_amplitude_dn=float(coefficients[k + 1]), expected_amplitude_dn=float(expected_coeff[k + 1]),
        recovery=None if expected_coeff[k + 1] == 0 else float(coefficients[k + 1] / expected_coeff[k + 1]))
        for k in range(len(modes))]
    return dict(samples=int(values.size), basis_columns=int(design.shape[1]), rank=rank,
        rank_relative_cutoff=RANK_RELATIVE, singular_values=s.tolist(),
        condition_number=None if rank < design.shape[1] else float(s[0] / s[-1]),
        component_status='IDENTIFIABLE_IN_DECLARED_BASIS' if coefficients is not None else 'UNIDENTIFIABLE_COMPONENTS',
        component_estimates=estimates, constant_estimate_dn=None if coefficients is None else float(coefficients[0]),
        mean_error_dn=float(np.mean(observed - expected)), target_rmse_dn=float(np.sqrt(np.mean((observed - expected)**2))),
        orthogonal_remainder_rms_dn=float(np.sqrt(np.mean((observed - projection)**2))),
        basis_fit_is_not_sampling_identification=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to((ROOT / 'outputs').resolve()) and not out.exists(), 'fresh workspace output required')
    out.mkdir(parents=True)
    started = time.perf_counter()
    bindings = {}

    def remember(path, expected=None):
        r = ref(path)
        if expected is not None:
            require((r['sha256'], r['bytes']) == (expected['sha256'], expected['bytes']), 'bound saved artifact differs')
        if r['path'] in bindings:
            require(bindings[r['path']] == r, 'input changed during analysis')
        bindings[r['path']] = r
        return Path(r['path'])

    state = dict(status='INCOMPLETE_NATIVE_SPECTRAL_STAGE_AUDIT', complete=False,
        quality_claim=False, photographic_admission=False, cases=[])
    try:
        import numpy as np
        remember(__file__)
        remember(SOURCE)
        require(bindings[str(SOURCE.resolve())]['sha256'] == SOURCE_SHA, 'only frozen controls5 permitted')
        source = read(SOURCE)
        require(source['complete'] and source['controls_pass'] and not source['quality_pass'], 'controls5 status differs')
        require(tuple(c['name'] for c in source['cases']) == CASE_NAMES, 'fixed case population differs')
        yy, xx = np.indices((64, 64), dtype=np.float64)
        x, y = xx + ORIGIN[0], yy + ORIGIN[1]
        phase = 2 * (yy.astype(int) % 2) + xx.astype(int) % 2
        masks = {name: phase == i for i, name in enumerate(('R', 'G1', 'G2', 'B'))}
        masks['G-combined'] = masks['G1'] | masks['G2']
        rows = []
        for case in source['cases']:
            modes = case['component_truth']
            row = dict(name=case['name'], inherited_quality_pass=case['quality_pass'], original_sources=[], arms={})
            shifts = case['source_shifts'] or [[0., 0.]] * len(case['sources'])
            for i, original in enumerate(case['sources']):
                path = remember(original['original']['path'], original['original'])
                require(original['original']['shape'] == [640, 640] and path.stat().st_size == 640 * 640 * 2, 'original extent')
                raw = np.memmap(path, dtype='<u2', shape=(640, 640), mode='r')
                require(not raw.flags.writeable, 'readonly originals required')
                patch = raw[256:320, 256:320].astype(np.float64) - 512.
                original_scores = {}
                for name, mask in masks.items():
                    channel = 0 if name == 'R' else 2 if name == 'B' else 1
                    original_scores[name] = describe(np, patch[mask], x[mask], y[mask], modes, channel,
                        transfers=case['component_transfers'][i], shift=shifts[i])
                row['original_sources'].append(dict(source_id=original['source_id'], scores=original_scores,
                    original_rect_xywh=[256, 256, 64, 64], source_shift=shifts[i],
                    basis_evaluated_in_original_coordinates=True, no_alignment_or_interpolation=True))
                del patch
                raw._mmap.close()
            for arm, arm_record in case['arms'].items():
                receipt_path = remember(arm_record['development_receipt']['path'], arm_record['development_receipt'])
                native = read(receipt_path)
                require(native['complete'] and native['status'] == 'COMPLETE_NATIVE_CFA_DEVELOPMENT'
                    and native['native_dimensions'] == [64, 64] and native['active_origin_xy'] == list(ORIGIN)
                    and native['physical_pattern'] == 'RGGB' and native['demosaic_stages'] == 1
                    and native['signed_cfa_copy_bit_exact'] and native['pixel_readback_exact'], 'native receipt differs')
                cfa_path = remember(native['cfa']['path'], native['cfa'])
                camera_path = remember(native['camera_rgb']['path'], native['camera_rgb'])
                require(cfa_path.stat().st_size == 64 * 64 * 4 and camera_path.stat().st_size == 64 * 64 * 3 * 4, 'stage extent')
                cfa = np.fromfile(cfa_path, dtype='<f4').reshape(64, 64).astype(np.float64)
                camera = np.fromfile(camera_path, dtype='<f4').reshape(64, 64, 3).astype(np.float64)
                development = native['development']
                black, white = bits(development['levels_bits'])
                camera *= (white - black) / np.asarray(bits(development['wb_bits']))
                phases = {}
                for name, mask in masks.items():
                    channel = 0 if name == 'R' else 2 if name == 'B' else 1
                    a = describe(np, cfa[mask], x[mask], y[mask], modes, channel)
                    b = describe(np, camera[..., channel][mask], x[mask], y[mask], modes, channel)
                    delta = camera[..., channel][mask] - np.maximum(cfa[mask], 0.)
                    phases[name] = dict(cfa=a, final_camera_at_known_sites=b,
                        known_site_max_abs_difference_dn=float(np.max(np.abs(delta))),
                        known_site_rms_difference_dn=float(np.sqrt(np.mean(delta * delta))))
                channels = {}
                for channel, name in enumerate(('R', 'G', 'B')):
                    known = masks['R'] if channel == 0 else masks['B'] if channel == 2 else masks['G-combined']
                    full = describe(np, camera[..., channel], x, y, modes, channel)
                    inferred = describe(np, camera[..., channel][~known], x[~known], y[~known], modes, channel)
                    # Reproduce the existing full-camera component scorer, not a new admission.
                    if full['component_estimates'] is not None:
                        for estimate in full['component_estimates']:
                            saved = next(v for v in arm_record['scores']['components']
                                if v['component'] == estimate['component'] and v['channel'] == channel)
                            require(abs(saved['measured_amplitude'] - estimate['measured_amplitude_dn']) <= 1e-7,
                                'saved headline component score not reproduced')
                    channels[name] = dict(final_camera_complete=full, final_camera_inferred_sites=inferred,
                        dense_camera_grid_is_not_independent_original_sampling=True)
                row['arms'][arm] = dict(phases=phases, channels=channels,
                    negative_cfa_count=int(np.count_nonzero(cfa < 0)),
                    inherited_scores=arm_record['scores'])
            rows.append(row)
        for old in bindings.values():
            require(ref(old['path']) == old, 'saved input bytes/metadata changed')
        state.update(status='COMPLETE_NATIVE_SPECTRAL_STAGE_AUDIT', complete=True, cases=rows,
            source_receipt_sha256=SOURCE_SHA, original_source_count=sum(len(c['sources']) for c in source['cases']),
            delivered_arm_count=20, input_bindings=list(bindings.values()), inputs_unchanged=True,
            score_reproduction_tolerance_dn=1e-7, RAW_reads=0, GPU_calls=0, producer_imports=0,
            command=[sys.executable, '-B', '-X', 'faulthandler', str(Path(__file__).resolve()), '--out', str(out)],
            libraries=dict(python=sys.version, numpy=np.__version__),
            thread_environment={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
            fits_are_only_small_saved_array_component_descriptions=True,
            limitations=['Rank-deficient physical-phase bases have no individual coefficient estimates.',
                'Full camera-grid basis rank is not evidence of independent original sample information.',
                'Original source panels are in their own physical coordinates and compared with their declared shift/blur plant.',
                'An error appearing at inferred camera sites localizes its producing stage, not a unique physical cause.',
                'Final MHC can expose inconsistency already present between fused phases; this does not establish that MHC alone is defective.',
                'No new quality gate, reconstruction, blur calibration or photographic admission.'],
            elapsed_seconds_qpc=time.perf_counter() - started)
        save(out / 'receipt.json', state)
        print(json.dumps(dict(status=state['status'], complete=True, cases=len(rows), arms=20)), flush=True)
    except BaseException as error:
        state.update(error=repr(error), elapsed_seconds_qpc=time.perf_counter() - started)
        save(out / 'receipt.json', state)
        raise


if __name__ == '__main__':
    main()
