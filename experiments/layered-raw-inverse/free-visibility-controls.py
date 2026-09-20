"""Independent free-visibility commissioning and fixed-final scoring; no fitting."""
from pathlib import Path
import argparse
import numpy as np
import torch
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('free_visibility_helpers', HERE/'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read, inventory, load = common.sha, common.read, common.inventory, common.load
FOCUS_SHA = '8aa5850574c9882aa6bb252bb21299a1e3625e45240850cd519a3e0649559891'
CASES = ['flat', 'layered', 'far-only', 'angular-mismatch']
FIELDS = ['near_rgb', 'far_rgb', 'alpha', 'pinhole_rgb']
PARAMETERS = ['near', 'far', 'alpha_logit']


def focus_module():
    assert sha(HERE/'in-focus-controls.py') == FOCUS_SHA
    return load(HERE/'in-focus-controls.py', 'free_visibility_frozen_focus_controls')


def commission(control, source, focus):
    optical = focus.commission(control, source)
    if not optical['passed']:
        return dict(status='INADEQUATE_OPTICAL_INSTRUMENT', passed=False, optical=optical)
    author = load(HERE/'free-visibility.py', 'free_visibility_author_controls')
    for name, digest in author.FROZEN.items():
        assert sha(HERE/name) == digest
    config = author.model.Config(**read(source/'layered'/'two-layer'/'receipt.json')['config'])
    y, x = torch.meshgrid(torch.arange(7), torch.arange(11), indexing='ij')
    pattern = torch.stack((x+2*y, 3*x-y, 2*x+4*y), -1).float()
    scale = config.saturation-config.black
    state = author.model._State((1200+13*pattern)/scale, (2700-9*pattern)/scale, 'two-layer', config)
    with torch.no_grad():
        state.alpha_logit.copy_(-1.2+.13*x+.07*y)
    assert [k for k, p in state.named_parameters() if p.requires_grad] == PARAMETERS
    saved = {k: v.clone() for k, v in state.state_dict().items()}
    a = state.fields()[2].detach().numpy().astype(np.float64)
    # Independently enumerate each directed edge's derivative, then sigmoid chain.
    expected = .002*(1-2*a)/a.size
    for axis in [0, 1]:
        edge = np.sign(np.diff(a, axis=axis))
        edge *= .01/edge.size
        if axis == 0:
            expected[:-1] -= edge
            expected[1:] += edge
        else:
            expected[:, :-1] -= edge
            expected[:, 1:] += edge
    expected *= a*(1-a)
    derivatives = {}
    for kind in ['original', 'matrix']:
        actual = author.selected_prior(state, config, kind)
        reference = state.prior() if kind == 'original' else author.matrix.selected_prior(state, config)
        assert torch.equal(actual, reference)
        gradients = torch.autograd.grad(actual, tuple(state.parameters()), retain_graph=True)
        assert all(torch.isfinite(g).all() and bool((g != 0).any()) for g in gradients)
        measured = gradients[2].detach().numpy().astype(np.float64)
        error = float(np.max(np.abs(measured-expected)))
        assert error <= 1e-10+2e-5*float(np.max(np.abs(expected)))
        assert float(np.max(np.abs(expected))) > 1e-6
        derivatives[kind] = dict(logit_max_abs=float(np.max(np.abs(measured))), independent_max_error=error,
                                 all_three_parameters_live=True, unchanged_objective_dispatch=True)
    assert all(torch.equal(state.state_dict()[k], v) for k, v in saved.items())
    return dict(status='PASS', passed=True, optical=optical, live_alpha_prior=derivatives,
                scope='Pure operator commission; no visibility inference or fit performed')


def check_receipt(receipt, directory, old, kind):
    start = read(old/'two-layer'/'receipt.json')
    assert receipt['config'] == start['config'] and receipt['mode'] == 'two-layer'
    assert receipt['prior_kind'] == kind and receipt['visibility'] == 'free-original-sigmoid'
    assert receipt['source_state_sha256'] == sha(old/'two-layer'/'state.pt')
    assert receipt['initial_checkpoint_exact'] and receipt['initial_parameter_names'] == receipt['gradient_parameter_names'] == PARAMETERS
    assert receipt['initial_field_identity'] == {k: True for k in FIELDS}
    assert receipt['training_sha256'] == start['training_sha256']
    assert receipt['train_indices'] == receipt['read_indices'] == start['train_indices']
    assert receipt['source_bindings_unchanged'] and receipt['hard_evaluation_cap'] == 1800
    assert 1 <= receipt['actual_evaluations'] <= 1800 and len(receipt['closure_history']) == receipt['actual_evaluations']
    complete = [r for r in receipt['closure_history'] if r['evaluation_status'] == 'complete']
    assert len(complete) == receipt['completed_evaluations'] and all(r['gradient_storage_logical_exact'] for r in complete)
    for binding in receipt['source_bindings'].values():
        assert sha(binding['path']) == binding['sha256']
    with np.load(directory/'initial-reconstruction.npz', allow_pickle=False) as actual, np.load(old/'two-layer'/'reconstruction.npz', allow_pickle=False) as initial:
        assert all(np.array_equal(actual[k], initial[k]) for k in FIELDS)
    if receipt['status'] == 'numerical_refusal' or receipt['final_objective'] is None:
        return False
    assert receipt['returned_state_accepted'] and receipt['final_objective']['gradient_storage_logical_exact']
    assert receipt['state_sha256'] == sha(directory/'state.pt')
    state = torch.load(directory/'state.pt', map_location='cpu', weights_only=True)
    assert list(state) == PARAMETERS and all(torch.isfinite(v).all() for v in state.values())
    assert sorted(p['index'] for p in receipt['predictions']) == [2, 6]
    for p in receipt['predictions']:
        assert sha(directory/p['path']) == p['sha256']
    assert sorted(p['target'] for p in receipt['images']) == ['in-focus', 'pinhole']
    for p in receipt['images']:
        assert p['path'] == p['target']+'-rgb-f32.npy'
        assert sha(directory/p['path']) == p['sha256']
        assert p['psf_applications'] == int(p['target'] == 'in-focus')
    return True


def paired(control, focus, case, images, arm, components):
    target, candidate, reference = images['truth'], images[arm], images['original']
    bars, detail = {}, {}
    regions = ['whole'] if case == 'flat' else ['core', 'ridge']
    if case == 'far-only':
        regions = ['whole', 'core', 'ridge']
    for region in regions:
        a, b = control.score(candidate, target, region), control.score(reference, target, region)
        for metric in ['rgb_rmse', 'chroma_rmse']:
            bars[region+'_'+metric] = a[metric] <= (1.05 if case == 'flat' else 1.02)*b[metric]
    if case != 'flat':
        names = [('glint', 'core')] if case == 'far-only' else focus.COMPONENTS
        for name, region in names:
            a, b = [focus.component(control, v, components, name, region) for v in [candidate, reference]]
            bars[name+'_component'] = focus.component_guard(a, b)
            detail[name] = dict(candidate=a, paired_free_huber=b)
    return dict(bars=bars, components=detail, passed=bool(all(bars.values())))


def far_only_quality(control, focus, images, arm, components):
    values, bars = {}, {}
    for region in ['whole', 'core', 'ridge']:
        values[region] = {k: control.score(v, images['truth'], region) for k, v in images.items() if k != 'truth'}
        for metric in ['rgb_rmse', 'chroma_rmse']:
            bars[region+'_'+metric] = values[region][arm][metric] <= 1.05*values[region]['far-only'][metric]
    a, o = [focus.component(control, images[k], components, 'glint', 'core') for k in [arm, 'donor-observed']]
    bars['glint_component'] = bool(a['live'] and o['live'] and np.all(np.clip(a['recovery'], 0, 1) >= .8)
        and np.all(np.clip(a['recovery'], 0, 1) >= .98*np.clip(o['recovery'], 0, 1)))
    return dict(regions=values, components=dict(glint=dict(candidate=a, donor=o)), bars=bars, passed=bool(all(bars.values())))


def score(control, source, candidate, focus):
    preserved = HERE/'in-focus-2'/'delivered'
    roots = [source, candidate, preserved]
    before = [inventory(p) for p in roots]
    retained = read(preserved/'result.json')
    assert retained['sources_unchanged'] and retained['source_bindings_before'] == retained['source_bindings_after']
    assert all(sha(p) == digest for p, digest in retained['source_bindings_before'].items())
    for item in retained['artifacts']:
        assert sha(item['path']) == item['sha256'] and sha(item['source_path']) == item['source_sha256']
    top = read(candidate/'result.json')
    assert top['status'] == 'FREE_VISIBILITY_COMPLETE' and Path(top['source_root']).resolve() == source
    assert top['bindings_unchanged'] and not top['visibility_oracle_used'] and not top['real_photo_admission']
    binding = read(candidate/'bindings-before.json')
    assert binding == read(candidate/'bindings-after.json')
    assert all(sha(p) == digest for p, digest in binding.items())
    assert len(top['arms']) == 8 and {(r['case'], r['prior_kind']) for r in top['arms']} == {(c, k) for c in CASES for k in ['original', 'matrix']}
    for row in top['arms']:
        assert sha(row['receipt']) == row['receipt_sha256']
    rows = []
    for case in CASES:
        old = source/case
        latent, raw = control.scene(case), np.load(old/'observations-u16.npy', allow_pickle=False)
        assert np.array_equal(latent['truth'], np.load(old/'truth-rgb-f32.npy', allow_pickle=False))
        assert raw.dtype == np.uint16 and control.digest(raw) == read(old/'result.json')['source_sha256']
        components = focus.transformed_components(latent)
        generator_checks = focus.generator_psf_checks(control, latent)
        images = dict(truth=focus.optical(latent['truth']))
        for arm, filename in [('mean-observed', 'mean-rgb-f32.npy'), ('donor-observed', 'oracle-bound-rgb-f32.npy')]:
            images[arm] = np.load(old/filename, allow_pickle=False)
        # The actual restricted single-depth arm, including in its far-only case.
        with np.load(old/'far-only'/'reconstruction.npz', allow_pickle=False) as data:
            single = data['pinhole_rgb'].copy()
        images['far-only'] = focus.optical(single)
        if case in ['flat', 'layered']:
            saved_target = np.load(preserved/case/'truth-rgb-f32.npy', allow_pickle=False)
            assert np.max(np.abs(images['truth']-saved_target)) <= focus.tolerance(latent['truth'])
            images['truth'] = saved_target
            images['visibility'] = np.load(preserved/case/'visibility-rgb-f32.npy', allow_pickle=False)
            images['far-only'] = np.load(preserved/case/'far-only-rgb-f32.npy', allow_pickle=False)
        receipts, pinholes, complete = {}, {}, {}
        for arm in ['original', 'matrix']:
            directory = candidate/case/arm
            r = receipts[arm] = read(directory/'receipt.json')
            complete[arm] = check_receipt(r, directory, old, arm)
            assert [control.digest(raw[k]) for k in control.TRAIN] == r['training_sha256']
            if complete[arm]:
                with np.load(directory/'reconstruction.npz', allow_pickle=False) as data:
                    pinholes[arm] = data['pinhole_rgb'].copy()
                images[arm] = np.load(directory/'in-focus-rgb-f32.npy', allow_pickle=False)
                assert np.array_equal(pinholes[arm], np.load(directory/'pinhole-rgb-f32.npy', allow_pickle=False))
                assert all(v.dtype == np.float32 and v.shape == (96, 96, 3) and np.isfinite(v).all() for v in [pinholes[arm], images[arm]])
                assert np.max(np.abs(images[arm]-focus.optical(pinholes[arm]))) <= focus.tolerance(pinholes[arm])
        if not all(complete.values()):
            rows.append(dict(case=case, complete=False, arm_complete=complete, statuses={k: r['status'] for k, r in receipts.items()}))
            continue
        for arm in ['original', 'matrix']:
            directory, r = candidate/case/arm, receipts[arm]
            if case in ['flat', 'layered']:
                q = focus.quality(control, case, images, arm, components)
            elif case == 'far-only':
                q = far_only_quality(control, focus, images, arm, components)
            else:
                q = dict(regions={region: {k: control.score(v, images['truth'], region) for k, v in images.items() if k != 'truth'} for region in control.REGIONS}, passed=None)
            pair = paired(control, focus, case, images, arm, components)
            held = []
            for k in control.HELD:
                expected = control.cfa_numpy(control.independent_forward(latent['near'], latent['far'], latent['alpha'], control.FOCI[k], angular=case=='angular-mismatch'))+np.float32(control.BLACK)
                prediction = np.load(directory/f'predicted-cfa-{k}.npy', allow_pickle=False)
                assert prediction.dtype == np.float32 and prediction.shape == raw[k].shape and np.isfinite(prediction).all()
                held.append(dict(index=k, scores=control.prediction_score(prediction, raw[k], expected)))
            held_pass = all(h['scores']['passed'] for h in held)
            if case in ['layered', 'far-only']:
                assert sum(h['scores']['uncensored']['bright']['count'] for h in held) > 0
            pinhole_q = control.quality(case, latent, pinholes[arm], single, images['mean-observed'], images['donor-observed'])
            rows.append(dict(case=case, arm=arm, complete=True, target_quality=q, paired_free_huber=pair,
                heldout=held, heldout_pass=held_pass, pinhole_quality=pinhole_q,
                fixed_target_checks_pass=bool(q['passed'] and pair['passed']) if case != 'angular-mismatch' else None,
                in_family_checks_pass=bool(q['passed'] and pair['passed'] and held_pass) if case != 'angular-mismatch' else None,
                status=r['status'], stationary=r['status']=='stationary_gradient', final_objective=r['final_objective'],
                frozen_generator_psf_checks=generator_checks, source_receipt_sha256=sha(directory/'receipt.json')))
    matched = [r for r in rows if r.get('arm') == 'matrix' and r['case'] != 'angular-mismatch']
    matched_pass = len(matched) == 3 and all(r['in_family_checks_pass'] for r in matched)
    mismatch = next((r for r in rows if r.get('arm') == 'matrix' and r['case'] == 'angular-mismatch'), None)
    assert [inventory(p) for p in roots] == before
    return dict(status='FREE_VISIBILITY_SCORED', records=rows, matrix_all_in_family_checks_pass=matched_pass,
        angular_heldout_refused=None if mismatch is None else not mismatch['heldout_pass'],
        selective_adequacy_demonstrated=bool(matched_pass and mismatch is not None and not mismatch['heldout_pass']),
        automatic_adequacy_gate_implemented=False, source_and_output_immutable=True, source_bindings=before,
        original_pinhole_admission_unchanged=True, real_photo_admission=False,
        physical_adequacy_unchanged=read(source/'layered'/'physical-adequacy.json'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['commission', 'score'])
    parser.add_argument('--source', type=Path, default=HERE/'screen-1'/'output')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert not out.exists()
    control, focus = common.frozen(source), focus_module()
    result = commission(control, source, focus) if args.mode == 'commission' else score(control, source, args.candidate.resolve(), focus)
    result['controls_sha256'] = sha(__file__)
    out.mkdir(parents=True)
    control.save(out/'result.json', control.jsonable(result))
    print('FREE_VISIBILITY_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
