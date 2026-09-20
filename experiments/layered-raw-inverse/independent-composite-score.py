"""Independent prior commissioning and fixed-final paired scoring; never fits."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
CASES = ['flat', 'layered', 'far-only', 'angular-mismatch']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def inventory(root):
    return {str(p.resolve()): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def literal_huber(dn, scale):
    total = np.float32(0)
    for axis in [0, 1]:
        delta = np.diff(dn, axis=axis)
        magnitude = np.sqrt(np.sum(delta * delta, axis=-1, dtype=np.float32) + np.float32(1e-12)) / np.float32(scale)
        value = np.where(magnitude <= 2, np.float32(.5) * magnitude * magnitude, 2 * magnitude - 2)
        total += np.mean(value, dtype=np.float32) / np.float32(2)
    return float(total)


def commission(author, control, device):
    scale = float(control.CEILING - control.BLACK)
    gradient = float(np.sqrt(2 * (control.GAIN * 2048 + control.READ_VARIANCE + 1 / 12)))
    y, x = torch.meshgrid(torch.arange(40, device=device), torch.arange(48, device=device), indexing='ij')
    q = torch.sin(x.float() * (2 * np.pi / 8))
    c = torch.tensor([2500, 3200, 2000], dtype=torch.float32, device=device).expand(40, 48, 3)
    d = torch.tensor([400, -300, 500], dtype=torch.float32, device=device).expand_as(c)

    class View:
        def __init__(self, near, far, alpha, single=False):
            self.n, self.b, self.a = near / scale, far / scale, alpha
            self.far = None if single else True
            self.dn_scale, self.gradient_scale = scale, gradient
        def fields(self):
            return self.n, self.b, self.a
        def prior(self):
            return author.model._State.prior(self)

    amplitude = torch.tensor(.02, device=device, requires_grad=True)
    escape = View(c + d, c - d, .5 + amplitude * q)
    varying = .5 + .1 * q
    cancel = View(c + d, (c - varying[..., None] * (c + d)) / (1 - varying[..., None]), varying)
    rows = []
    for name, state in [('coverage-escape', escape), ('contrast-cancelling-flat', cancel)]:
        n, b, a = state.fields()
        dn = (a[..., None] * n + (1 - a[..., None]) * b) * scale
        expected = literal_huber(dn.detach().cpu().numpy(), gradient)
        old = author.image_regularizer(state, 'original')
        new = author.image_regularizer(state, 'composite')
        assert abs(float(new.detach()) - expected) < 5e-5 * max(1, expected)
        delta = author.selected_prior(state, 'composite') - author.selected_prior(state, 'original')
        assert abs(float((delta - (new - old)).detach())) < 5e-5
        if name == 'coverage-escape':
            assert float(old.detach()) < 1e-8 and float(new.detach()) > .01
            derivative = float(torch.autograd.grad(new, amplitude, retain_graph=True)[0])
            assert derivative > 0
            wrong = literal_huber(((n + b) * (.5 * scale)).detach().cpu().numpy(), gradient)
            assert abs(wrong - expected) > .01
        else:
            assert float(new.detach()) < 1e-5 and float(old.detach()) > .1
        rows.append(dict(name=name, independent_image_prior=expected,
                         original_image_prior=float(old.detach()), composite_image_prior=float(new.detach())))
    live = (c + 100 * q[..., None]).clone().requires_grad_(True)
    single = View(live, live, torch.ones_like(q), single=True)
    old = author.selected_prior(single, 'original')
    new = author.selected_prior(single, 'composite')
    go = torch.autograd.grad(old, live, retain_graph=True)[0]
    gn = torch.autograd.grad(new, live)[0]
    assert old.detach().item() == new.detach().item() and torch.equal(go, gn) and bool((go != 0).any())
    return dict(status='PASS', passed=True, cases=rows, one_layer_value_gradient_exact=True,
                wrong_composite_destroyer_live=True, scope='Prior algebra only; not camera calibration or image utility')


def score_paired(control, source, paired):
    before = read(paired / 'bindings-before.json')
    assert before == read(paired / 'bindings-after.json')
    assert all(sha(path) == expected for path, expected in before.items())
    original_files, paired_files = inventory(source), inventory(paired)
    records = []
    for name in CASES:
        old = source / name
        start = read(old / 'two-layer' / 'receipt.json')
        latent = control.scene(name)
        raw = np.load(old / 'observations-u16.npy', allow_pickle=False)
        assert control.digest(raw) == read(old / 'result.json')['source_sha256']
        assert np.array_equal(latent['truth'], np.load(old / 'truth-rgb-f32.npy', allow_pickle=False))
        references = [np.load(old / (label + '-rgb-f32.npy'), allow_pickle=False)
                      for label in ['far-only', 'mean', 'oracle-bound']]
        arms, images = {}, {}
        for kind in ['original', 'composite']:
            directory = paired / name / kind
            receipt = read(directory / 'receipt.json')
            assert receipt['config'] == start['config'] and receipt['mode'] == 'two-layer'
            assert receipt['prior_kind'] == kind and receipt['source_state_sha256'] == sha(old / 'two-layer' / 'state.pt')
            assert receipt['training_sha256'] == start['training_sha256'] and receipt['train_indices'] == list(control.TRAIN)
            assert receipt['read_indices'] == list(control.TRAIN)
            assert receipt['initial_checkpoint_exact'] and receipt['source_bindings_unchanged']
            assert 1 <= receipt['actual_evaluations'] <= 1800
            assert receipt['actual_evaluations'] == len(receipt['closure_history'])
            completed = [r for r in receipt['closure_history'] if r['evaluation_status'] == 'complete']
            assert len(completed) == receipt['completed_evaluations']
            assert all(r['gradient_storage_logical_exact'] for r in completed)
            for binding in receipt['source_bindings'].values():
                assert sha(binding['path']) == binding['sha256']
            if receipt['status'] == 'numerical_refusal' or receipt['final_objective'] is None:
                arms[kind] = dict(complete=False, status=receipt['status'], error=receipt.get('error'))
                continue
            assert receipt['returned_state_accepted'] and receipt['final_objective']['gradient_storage_logical_exact']
            required = ['state.pt', 'reconstruction.npz', 'predicted-cfa-2.npy', 'predicted-cfa-6.npy']
            missing = [p for p in required if not (directory / p).is_file()]
            if missing:
                arms[kind] = dict(complete=False, status='missing_final_artifact', missing=missing)
                continue
            assert receipt['state_sha256'] == sha(directory / 'state.pt')
            for p in receipt['predictions']:
                assert sha(directory / p['path']) == p['sha256']
            with np.load(directory / 'reconstruction.npz', allow_pickle=False) as result:
                image = result['pinhole_rgb'].copy()
            assert image.dtype == np.float32 and image.shape == (96, 96, 3) and np.isfinite(image).all()
            images[kind] = image
            quality = control.quality(name, latent, image, *references)
            held = []
            for k in control.HELD:
                rgb = control.independent_forward(latent['near'], latent['far'], latent['alpha'], control.FOCI[k],
                                                  angular=name == 'angular-mismatch')
                expected = control.cfa_numpy(rgb) + np.float32(control.BLACK)
                predicted = np.load(directory / f'predicted-cfa-{k}.npy', allow_pickle=False)
                assert predicted.dtype == np.float32 and predicted.shape == raw[k].shape and np.isfinite(predicted).all()
                held.append(dict(index=k, scores=control.prediction_score(predicted, raw[k], expected)))
            arms[kind] = dict(complete=True, quality=quality, heldout=held,
                heldout_pass=all(h['scores']['passed'] for h in held), stationary=receipt['status'] == 'stationary_gradient',
                status=receipt['status'], final_objective=receipt['final_objective'], rgb_sha256=control.digest(image))
        paired_bars, components = {}, {}
        if len(images) == 2:
            original, composite = images['original'], images['composite']
            if name == 'flat':
                a, b = control.score(composite, latent['truth']), control.score(original, latent['truth'])
                paired_bars = {key + '_original': a[key] <= 1.05 * b[key] for key in ['rgb_rmse', 'chroma_rmse']}
            else:
                for region in ['core', 'ridge']:
                    a, b = control.score(composite, latent['truth'], region), control.score(original, latent['truth'], region)
                    paired_bars[region + '_rgb'] = a['rgb_rmse'] <= 1.02 * b['rgb_rmse']
            if name in ['layered', 'angular-mismatch']:
                for component_name, region in [('glint', 'core'), ('ridge', 'ridge-detail')]:
                    a = control.component(composite, latent, component_name, region)
                    b = control.component(original, latent, component_name, region)
                    ra, rb = np.array(a['recovery']), np.array(b['recovery'])
                    good = a['live'] and b['live'] and bool(np.all(rb >= .5) and np.all(np.clip(ra, 0, 1) >= .98 * np.minimum(rb, 1)))
                    paired_bars[component_name + '_component'] = good
                    components[component_name] = dict(composite=a, original=b, passed=good)
        complete = len(images) == 2
        passed = complete and bool(arms['composite']['quality']['passed']) and arms['composite']['heldout_pass'] and all(paired_bars.values())
        records.append(dict(name=name, arms=arms, paired_bars=paired_bars, paired_components=components, complete=complete,
            fixed_image_checks_pass=passed if name != 'angular-mismatch' else None,
            interpretation='Mismatch descriptive; failed heldout means screen refusal, no automatic gate' if name == 'angular-mismatch'
                           else 'Original bars plus paired protections; stationarity separate'))
    assert inventory(source) == original_files and inventory(paired) == paired_files
    return dict(status='FINAL_PAIRED_CHECKPOINTS_SCORED', cases=records,
        in_family_image_checks_pass=all(r['fixed_image_checks_pass'] for r in records if r['name'] != 'angular-mismatch'),
        all_stationary=all(a.get('stationary', False) for r in records for a in r['arms'].values()),
        source_immutable=True, paired_outputs_immutable=True, source_files=original_files, paired_files=paired_files,
        physical_adequacy=read(source / 'layered' / 'physical-adequacy.json'), real_photo_admission=False,
        original_screens_remain_failed=True, scope='Matched-budget final objectives; no calibration, canonical or SOTA claim')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['commission', 'score'])
    parser.add_argument('--source', type=Path, default=HERE / 'screen-1' / 'output')
    parser.add_argument('--comparison', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert not out.exists()
    for row in read(source.parent / 'sources.json'):
        assert sha(row['path']) == row['sha256']
    control = load(HERE / 'independent-controls.py', 'frozen_composite_scoring_controls')
    if args.mode == 'commission':
        author = load(HERE / 'composite-prior.py', 'fixed_composite_prior')
        result = commission(author, control, args.device)
    else:
        assert args.comparison is not None
        result = score_paired(control, source, args.comparison.resolve())
    result['scorer_sha256'] = sha(__file__)
    out.mkdir(parents=True)
    control.save(out / 'result.json', result)
    print('COMPOSITE_PRIOR_COMMISSION' if args.mode == 'commission' else 'COMPOSITE_PRIOR_SCORE',
          json.dumps({k:v for k,v in result.items() if k in ['status', 'in_family_image_checks_pass', 'all_stationary', 'real_photo_admission']}), flush=True)


if __name__ == '__main__':
    main()
