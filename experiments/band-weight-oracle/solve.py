"""Fixed truth-assisted weight witness; root executes, independent checker judges."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import time

CONSUMER = Path(__file__).resolve().parents[1] / 'learned-band-guide' / 'train.py'
CONSUMER_SHA = 'b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987'
DATASET_SHA = '0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19'
NATIVE_COMMISSION = CONSUMER.parent / 'commission-1' / 'output' / 'commission.json'
STEPS = 1024
LEARNING_RATE = 0.03
ADAM_EPSILON = 1e-15
FIT_SECONDS = 180.0
EPSILON = 0.01
COMMISSION_CASES = ('held-flat-n5', 'held-curved-bright-occlusion-n9')


def consumer():
    if hashlib.sha256(CONSUMER.read_bytes()).hexdigest() != CONSUMER_SHA:
        raise RuntimeError('commissioned reconstruction helper changed')
    spec = importlib.util.spec_from_file_location('fixed_learned_consumer', CONSUMER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized(logits, torch):
    return [torch.exp(x - x.amax(dim=1, keepdim=True)) for x in logits]


def parameters(batch, torch):
    return [torch.nn.Parameter(torch.zeros_like(batch[f'coeff-{k}'][:, :, 0])) for k in range(3)]


def mse(batch, logits, target, helper, torch):
    _, rgb, _ = helper.reconstruct(batch, normalized(logits, torch), torch)
    return (rgb - target).square().mean()


def directional(case, helper, torch):
    batch = helper.batched([case], torch)
    logits = parameters(batch, torch)
    loss = mse(batch, logits, batch['prescribed-rgb'], helper, torch)
    gradients = torch.autograd.grad(loss, logits)
    maximum = max(float(g.abs().max()) for g in gradients)
    helper.need(maximum > 0 and all(bool(torch.isfinite(g).all()) for g in gradients),
                'known feasible target needs a finite live direction')
    direction = [-g / maximum for g in gradients]
    derivative = sum(float((g.double() * d.double()).sum()) for g, d in zip(gradients, direction))
    with torch.no_grad():
        plus = mse(batch, [x + EPSILON*d for x,d in zip(logits,direction)], batch['prescribed-rgb'], helper, torch)
        minus = mse(batch, [x - EPSILON*d for x,d in zip(logits,direction)], batch['prescribed-rgb'], helper, torch)
    return {'objective0': float(loss.detach()), 'objective_plus': float(plus),
            'objective_minus': float(minus), 'autograd_directional_derivative': derivative,
            'epsilon': EPSILON, 'direction': '-gradient/max_abs_gradient', 'max_abs_gradient': maximum}


def fit(cases, target_kind, helper, torch):
    groups = []
    for count in sorted({c['meta']['source_count'] for c in cases}):
        indices = [i for i,c in enumerate(cases) if c['meta']['source_count'] == count]
        batch = helper.batched([cases[i] for i in indices], torch)
        groups.append((indices, batch, parameters(batch, torch)))
    all_parameters = [p for _,_,ps in groups for p in ps]
    optimizer = torch.optim.Adam(all_parameters, lr=LEARNING_RATE, eps=ADAM_EPSILON)
    initial = [None] * len(cases)
    with torch.no_grad():
        for indices, batch, logits in groups:
            _, rgb, _ = helper.reconstruct(batch, normalized(logits, torch), torch)
            errors = (rgb-batch[target_kind]).square().flatten(1).mean(1)
            for index,error in zip(indices,errors):
                initial[index] = float(error)
    torch.cuda.synchronize()
    started = time.perf_counter()
    history = []
    for step in range(STEPS):
        optimizer.zero_grad(set_to_none=True)
        loss = sum(mse(batch, logits, batch[target_kind], helper, torch) * (len(indices)/len(cases))
                   for indices,batch,logits in groups)
        helper.need(bool(torch.isfinite(loss).detach()), 'nonfinite oracle loss')
        loss.backward()
        helper.need(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in all_parameters),
                    'nonfinite oracle gradient')
        optimizer.step()
        torch.cuda.synchronize()
        helper.need(time.perf_counter()-started <= FIT_SECONDS, 'fixed optimization cap; no partial candidate')
        if step == 0 or (step+1) % 128 == 0:
            row = {'step': step+1, 'rgb_mse_before_update': float(loss.detach())}
            history.append(row)
            print(json.dumps(row), flush=True)
    helper.need(all(bool(torch.isfinite(p).all()) for p in all_parameters), 'nonfinite final logits')
    weights = [None] * len(cases)
    final = [None] * len(cases)
    with torch.no_grad():
        for indices,batch,logits in groups:
            values = normalized(logits, torch)
            _,rgb,_ = helper.reconstruct(batch, values, torch)
            errors = (rgb-batch[target_kind]).square().flatten(1).mean(1)
            for offset,(index,error) in enumerate(zip(indices,errors)):
                weights[index] = [w[offset:offset+1].detach() for w in values]
                final[index] = float(error)
    return weights, initial, final, history, time.perf_counter()-started, sum(p.numel() for p in all_parameters)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['commission', 'solve'])
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--commission', type=Path)
    args = parser.parse_args()
    helper = consumer()
    out = args.out.resolve()
    helper.need(not out.exists(), 'fresh output required')
    helper.need(helper.sha(args.dataset) == DATASET_SHA, 'fixed retained dataset changed')
    native_commission = json.loads(NATIVE_COMMISSION.read_text())
    helper.need(native_commission['passed'] is True and native_commission['source_sha256'] == CONSUMER_SHA
                and native_commission['dataset_sha256'] == DATASET_SHA, 'retained native port commissioning mismatch')
    paths = helper.manifest(args.dataset)
    bindings = {'dataset': str(args.dataset.resolve()), 'dataset_sha256': helper.sha(args.dataset),
                'consumer': str(CONSUMER), 'consumer_sha256': helper.sha(CONSUMER),
                'source_sha256': helper.sha(__file__), 'native_commission': str(NATIVE_COMMISSION),
                'native_commission_sha256': helper.sha(NATIVE_COMMISSION)}
    if args.phase == 'commission':
        chosen = [p for name in COMMISSION_CASES for p in paths['heldout'] if p.parent.name == name]
        helper.need(len(chosen) == 2 and [p.parent.name for p in chosen] == list(COMMISSION_CASES),
                    'fixed flat/curved known-feasible cases missing')
        target_kind = 'prescribed-rgb'
    else:
        helper.need(args.commission is not None, 'independent commissioning receipt required')
        control_path = args.commission.resolve() / 'commission.json'
        control = json.loads(control_path.read_text())
        helper.need(control['passed'] and control['dataset_sha256'] == bindings['dataset_sha256'],
                    'independent commissioning refused or dataset changed')
        fit_path = Path(control['fit']).resolve()
        helper.need(helper.sha(fit_path) == control['fit_sha256'], 'changed commissioning fit')
        prior = json.loads(fit_path.read_text())
        helper.need(prior['phase'] == 'commission' and prior['steps'] == STEPS
                    and prior['learning_rate'] == LEARNING_RATE
                    and prior['adam_epsilon'] == ADAM_EPSILON
                    and all(prior[key] == bindings[key] for key in ('source_sha256','consumer_sha256','dataset_sha256')),
                    'commissioning does not bind this solver/consumer/dataset')
        bindings.update(commission=str(control_path), commission_sha256=helper.sha(control_path))
        chosen = paths['heldout']
        target_kind = 'truth-rgb'
    out.mkdir()
    np, torch = helper.runtime()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    cases = [helper.load_case(p,np,torch,truth=args.phase=='solve',goldens=args.phase=='commission') for p in chosen]
    directions = [directional(case,helper,torch) for case in cases] if args.phase == 'commission' else [None]*len(cases)
    weights, initial, final, history, seconds, count = fit(cases,target_kind,helper,torch)
    records, predictions = [], []
    for index,case in enumerate(cases):
        folder = out / f'case-{index:02}'
        folder.mkdir()
        prediction = helper.write_prediction(folder,case,helper.batched([case],torch),weights[index],torch,np)
        predictions.append(prediction)
        record = {'case':case['path'],'case_sha256':case['sha256'],'initial_mse':initial[index],
                  'final_mse':final[index],'prediction':prediction}
        if directions[index] is not None:
            record['directional'] = directions[index]
        records.append(record)
    common = {'schema':1,**bindings,'phase':args.phase,'target_kind':target_kind,
              'truth_assisted_oracle':args.phase=='solve','generalization_claim':False,'quality_claim':False,
              'global_optimum_or_ceiling_claim':False,'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),
              'float32':True,'deterministic':True,'tf32':False,'seed':helper.SEED}
    helper.save(out/'predictions.json',{**common,'records':predictions})
    helper.save(out/'fit.json',{**common,'status':'FINAL_STEP_COMPLETE','steps':STEPS,'learning_rate':LEARNING_RATE,
        'adam_epsilon':ADAM_EPSILON,
        'start':'uniform-zero-logits','final_only':True,'cap_seconds':FIT_SECONDS,'parameters':count,
        'fit_seconds':seconds,'history':history,'cases':records,'predictions_sha256':helper.sha(out/'predictions.json'),
        'peak_cuda_bytes':torch.cuda.max_memory_allocated()})
    torch.cuda.synchronize()
    helper.save(out/'completion.json',{**common,'completed':True,'wall_seconds':time.perf_counter()-started,
                                      'peak_cuda_bytes':torch.cuda.max_memory_allocated()})


if __name__ == '__main__':
    main()
