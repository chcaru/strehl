"""One fixed tiny score-network fit; root owns all execution and quality decisions."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time

STEPS = 1024
SEED = 137
LEARNING_RATE = 0.001
TRAIN_SECONDS = 300.0


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def runtime():
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    import numpy as np
    import torch
    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)
    need(torch.cuda.is_available(), 'CUDA required; no install or fallback')
    torch.set_default_dtype(torch.float32)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.cuda.set_per_process_memory_fraction(min(1.0, 4*1024**3 / torch.cuda.get_device_properties(0).total_memory))
    return np, torch


def manifest(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    need(data['schema'] == 1 and len(data['training']) == 12 and len(data['heldout']) == 7,
         'fixed12 training/seven held cases in six families required')
    paths = {key: [Path(p).resolve() if Path(p).is_absolute() else (path.parent / p).resolve()
                   for p in data[key]] for key in ('training', 'heldout')}
    need(len(set(paths['training'] + paths['heldout'])) == 19, 'duplicate or overlapping case paths')
    return paths


def load_case(path, np, torch, *, truth, goldens):
    path = Path(path).resolve()
    meta = json.loads(path.read_text())
    need(meta['schema'] == 1 and meta['level_sizes'] == [[80,72],[40,36],[20,18],[10,9]], 'fixed native grid')
    n = meta['source_count']
    need(2 <= n <= 17 and meta['original_linear_reconstruction'] and meta['zero_network_uniform_exact'], 'case scope')
    keys = [f'{name}-{k}' for name in ('coeff', 'features') for k in range(3)] + ['base', 'lower', 'upper']
    if truth:
        keys += ['truth-rgb']
    if goldens:
        keys += [f'prescribed-weights-{k}' for k in range(3)] + ['uniform-cfa','uniform-rgb','prescribed-cfa','prescribed-rgb','zero-network-rgb']
    arrays, bindings = {}, []
    for key in keys:
        row = meta['arrays'][key]
        source = (path.parent / row['file']).resolve()
        need(source.parent == path.parent and source.suffix == '.f32' and row['dtype'] == '<f4', 'owned simple f32 blob required')
        raw = source.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == row['sha256'], 'changed exported tensor')
        a = np.frombuffer(raw, dtype='<f4').copy().reshape(row['shape'])
        need(np.isfinite(a).all(), 'nonfinite tensor')
        arrays[key] = torch.from_numpy(a).to('cuda')
        bindings.append({'file': str(source), 'sha256': row['sha256']})
    for k,(w,h) in enumerate(meta['level_sizes'][:3]):
        need(tuple(arrays[f'coeff-{k}'].shape) == (n,4,h,w) and tuple(arrays[f'features-{k}'].shape) == (n,10,h,w), 'coefficient/feature layout')
    need(tuple(arrays['base'].shape) == (4,9,10) and tuple(arrays['lower'].shape) == (4,72,80)
         and tuple(arrays['upper'].shape) == (4,72,80), 'base/hull layout')
    return {'path': str(path), 'sha256': sha(path), 'meta': meta, 'arrays': arrays, 'bindings': bindings}


def batched(cases, torch):
    need(len({c['meta']['source_count'] for c in cases}) == 1, 'batch source counts differ')
    keys = set(cases[0]['arrays'])
    need(all(set(c['arrays']) == keys for c in cases), 'batch tensor keys differ')
    result = {key: torch.stack([c['arrays'][key] for c in cases]) for key in keys}
    result['wb'] = torch.tensor([c['meta']['wb'] for c in cases], device='cuda')
    result['range'] = torch.tensor([c['meta']['range'] for c in cases], device='cuda')
    return result


def expand_axis(x, length, torch):
    left = torch.cat((x[..., :1], x[..., :-1]), dim=-1)
    right = torch.cat((x[..., 1:], x[..., -1:]), dim=-1)
    even = 0.125*left + 0.75*x + 0.125*right
    odd = 0.5*(x + right)
    return torch.stack((even, odd), dim=-1).flatten(-2)[..., :length]


def expand(x, height, width, torch):
    x = expand_axis(x, width, torch)
    return expand_axis(x.transpose(-2,-1), height, torch).transpose(-2,-1)


G = [(0,0,4),(-1,0,2),(1,0,2),(0,-1,2),(0,1,2),(-2,0,-1),(2,0,-1),(0,-2,-1),(0,2,-1)]
H = [(0,0,5),(-1,0,4),(1,0,4),(-2,0,-1),(2,0,-1),(-1,-1,-1),(1,-1,-1),(-1,1,-1),(1,1,-1),(0,-2,.5),(0,2,.5)]
V = [(0,0,5),(0,-1,4),(0,1,4),(0,-2,-1),(0,2,-1),(-1,-1,-1),(1,-1,-1),(-1,1,-1),(1,1,-1),(-2,0,.5),(2,0,.5)]
X = [(0,0,6),(-1,-1,2),(1,-1,2),(-1,1,2),(1,1,2),(-2,0,-1.5),(2,0,-1.5),(0,-2,-1.5),(0,2,-1.5)]


def mhc(planes, wb, ranges, torch):
    # Existing normalization operation order; RGGB sites stay at their own phases.
    channel_gain = torch.stack((wb[:,0], wb[:,1], wb[:,1], wb[:,2]), dim=1)[:,:,None,None]
    p = planes.clamp_min(0)*channel_gain*1.0/ranges[:,None,None,None]
    top = torch.stack((p[:,0],p[:,1]),dim=-1).flatten(-2)
    bottom = torch.stack((p[:,2],p[:,3]),dim=-1).flatten(-2)
    mosaic = torch.stack((top,bottom),dim=-2).flatten(-3,-2)
    height,width = mosaic.shape[-2:]
    pad = torch.cat((mosaic[...,1:3].flip(-1),mosaic,mosaic[...,-3:-1].flip(-1)),dim=-1)
    pad = torch.cat((pad[...,1:3,:].flip(-2),pad,pad[...,-3:-1,:].flip(-2)),dim=-2)
    def conv(taps):
        result = torch.zeros_like(mosaic)
        for dx,dy,w in taps:
            result = result + w*pad[...,2+dy:2+dy+height,2+dx:2+dx+width]
        return result*0.125
    green,horizontal,vertical,cross = [conv(taps) for taps in (G,H,V,X)]
    rows = torch.arange(height,device=mosaic.device)[:,None]
    cols = torch.arange(width,device=mosaic.device)[None,:]
    red_site = (rows%2==0)&(cols%2==0)
    blue_site = (rows%2==1)&(cols%2==1)
    g1_site = (rows%2==0)&(cols%2==1)
    red = torch.where(red_site,mosaic,torch.where(blue_site,cross,torch.where(g1_site,horizontal,vertical)))
    blue = torch.where(blue_site,mosaic,torch.where(red_site,cross,torch.where(g1_site,vertical,horizontal)))
    green = torch.where(red_site|blue_site,green,mosaic)
    return torch.stack((red,green,blue),dim=-1)


def reconstruct(batch, weights, torch):
    fused = []
    for k in range(3):
        source = batch[f'coeff-{k}']
        numerator = torch.zeros_like(source[:,0])
        denominator = torch.zeros_like(weights[k][:,0])
        for i in range(source.shape[1]):
            numerator = numerator + weights[k][:,i,None]*(source[:,i]/65536.0)
            denominator = denominator + weights[k][:,i]
        need(bool(torch.all(denominator > 0).detach()), 'zero learned denominator')
        fused.append((numerator/denominator[:,None])*65536.0)
    result = batch['base']
    for k in (2,1,0):
        result = expand(result,*fused[k].shape[-2:],torch)+fused[k]
    before = result
    result = torch.minimum(torch.maximum(result,batch['lower']),batch['upper'])
    return result,mhc(result,batch['wb'],batch['range'],torch),before


def make_model(torch):
    class Score(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = torch.nn.Conv2d(10,8,3,padding=0)
            self.conv2 = torch.nn.Conv2d(8,1,1)
            torch.nn.init.zeros_(self.conv2.weight)
            torch.nn.init.zeros_(self.conv2.bias)

        def forward(self, features):
            b,n,c,h,w = features.shape
            x = features.reshape(b*n,c,h,w)
            # Explicit cat keeps deterministic backward through repeated border sites.
            x = torch.cat((x[...,:1],x,x[...,-1:]),dim=-1)
            x = torch.cat((x[...,:1,:],x,x[...,-1:,:]),dim=-2)
            logits = self.conv2(torch.tanh(self.conv1(x))).reshape(b,n,h,w)
            return torch.exp(logits-logits.amax(dim=1,keepdim=True))
    model = Score().cuda()
    need(sum(p.numel() for p in model.parameters()) == 737, 'network architecture changed')
    return model


def weights_from_model(model,batch):
    return [model(batch[f'features-{k}']) for k in range(3)]


def model_json(model):
    result = {'schema':1}
    for key,tensor in [('conv1',model.conv1.weight),('bias1',model.conv1.bias),('conv2',model.conv2.weight),('bias2',model.conv2.bias)]:
        result[key] = tensor.detach().cpu().flatten().tolist()
    return result


def load_model(path,torch):
    row = json.loads(Path(path).read_text())
    need(set(row)=={'schema','conv1','bias1','conv2','bias2'} and row['schema']==1,'fixed model JSON')
    model = make_model(torch)
    with torch.no_grad():
        for key,parameter in [('conv1',model.conv1.weight),('bias1',model.conv1.bias),('conv2',model.conv2.weight),('bias2',model.conv2.bias)]:
            value = torch.tensor(row[key],device='cuda',dtype=torch.float32)
            need(value.numel()==parameter.numel() and bool(torch.isfinite(value).all()),'model weights shape/values')
            parameter.copy_(value.reshape(parameter.shape))
    return model.eval()


def write_prediction(out,case,batch,weights,torch,np):
    with torch.no_grad():
        cfa,rgb,_ = reconstruct(batch,weights,torch)
    blobs = {}
    for name,tensor in [('cfa',cfa[0]),('rgb',rgb[0])] + [(f'weights-{k}',v[0]) for k,v in enumerate(weights)]:
        array = tensor.detach().cpu().numpy().astype('<f4',copy=False)
        path = out / f'{name}.f32'
        with path.open('xb') as handle:
            handle.write(array.tobytes())
        blobs[name] = {'file':str(path.resolve()),'sha256':sha(path),'shape':list(array.shape),'dtype':'<f4'}
    return {'case':case['path'],'case_sha256':case['sha256'],'arrays':blobs}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase',choices=['commission','train','infer'])
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--commission',type=Path)
    p.add_argument('--weights',type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    need(not out.exists(),'fresh output required')
    out.mkdir()
    paths = manifest(args.dataset)
    np,torch = runtime()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    common = {'schema':1,'dataset':str(args.dataset.resolve()),'dataset_sha256':sha(args.dataset),
              'source_sha256':sha(__file__),'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),
              'deterministic':True,'float32':True,'tf32':False,'seed':SEED}
    if args.phase == 'commission':
        records = []
        for path in paths['training']:
            case = load_case(path,np,torch,truth=False,goldens=True)
            batch = batched([case],torch)
            rows = []
            for name in ('uniform','prescribed'):
                weights = [torch.ones_like(batch[f'prescribed-weights-{k}']) if name=='uniform' else batch[f'prescribed-weights-{k}'] for k in range(3)]
                with torch.no_grad():
                    cfa,rgb,before = reconstruct(batch,weights,torch)
                ce = float((cfa-batch[f'{name}-cfa']).abs().max())
                re = float((rgb-batch[f'{name}-rgb']).abs().max())
                need(ce<=0.02 and re<=5e-6,'Python/native reconstruction mismatch')
                rows.append({'arm':name,'maximum_cfa_error_dn':ce,'maximum_rgb_error':re,
                             'comparison_includes_all_boundary_pixels':True,'clamped_sites':int((before!=cfa).sum())})
            need(torch.equal(batch['uniform-rgb'],batch['zero-network-rgb']),'export zero-network is not uniform')
            records.append({'case':str(path),'sha256':case['sha256'],'arms':rows})
        need(any(r['arms'][1]['clamped_sites']>0 for r in records),'input hull never exercised')
        save(out/'commission.json',{**common,'passed':True,'training_only':True,'records':records})
    elif args.phase == 'train':
        need(args.commission is not None,'successful reconstruction commissioning required')
        cp = args.commission/'commission.json'
        control = json.loads(cp.read_text())
        need(control['passed'] and control['source_sha256']==common['source_sha256']
             and control['dataset_sha256']==common['dataset_sha256'],'commission binding differs')
        cases = [load_case(path,np,torch,truth=True,goldens=False) for path in paths['training']]
        need(all(c['meta']['source_count']==5 for c in cases),'fixed training source count5')
        need([c['sha256'] for c in cases]==[r['sha256'] for r in control['records']],'changed training cases')
        batch = batched(cases,torch)
        model = make_model(torch)
        optimizer = torch.optim.Adam(model.parameters(),lr=LEARNING_RATE)
        torch.cuda.synchronize()
        fit_start = time.perf_counter()
        history = []
        for step in range(STEPS):
            optimizer.zero_grad(set_to_none=True)
            weights = weights_from_model(model,batch)
            _,rgb,_ = reconstruct(batch,weights,torch)
            loss = (rgb-batch['truth-rgb']).square().mean()
            need(bool(torch.isfinite(loss).detach()),'nonfinite training loss')
            loss.backward()
            need(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()),'nonfinite training gradient')
            optimizer.step()
            torch.cuda.synchronize()
            need(time.perf_counter()-fit_start<=TRAIN_SECONDS,'fixed training wall cap; no partial model')
            if step==0 or (step+1)%128==0:
                history.append({'step':step+1,'rgb_mse_before_update':float(loss.detach())})
        need(all(bool(torch.isfinite(p).all()) for p in model.parameters()),'nonfinite final model')
        save(out/'model.json',model_json(model))
        save(out/'training.json',{**common,'status':'FINAL_STEP_COMPLETE','steps':STEPS,'learning_rate':LEARNING_RATE,
            'parameters':737,'training_only':True,'training_cases':[{'path':c['path'],'sha256':c['sha256']} for c in cases],
            'commission_sha256':sha(cp),'model_sha256':sha(out/'model.json'),'history':history,
            'fit_seconds':time.perf_counter()-fit_start,'peak_cuda_bytes':torch.cuda.max_memory_allocated(),
            'quality_claim':False,'no_heldout_truth_read':True})
    else:
        need(args.weights is not None,'fixed model required')
        model = load_model(args.weights,torch)
        records = []
        for index,path in enumerate(paths['training']+paths['heldout']):
            case = load_case(path,np,torch,truth=False,goldens=False)
            batch = batched([case],torch)
            with torch.no_grad():
                weights = weights_from_model(model,batch)
            folder = out/f'case-{index:02}'
            folder.mkdir()
            records.append(write_prediction(folder,case,batch,weights,torch,np))
        save(out/'predictions.json',{**common,'model_sha256':sha(args.weights),'truth_read':False,'records':records})
    torch.cuda.synchronize()
    save(out/'completion.json',{**common,'phase':args.phase,'wall_seconds':time.perf_counter()-started,
                              'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'completed':True})


if __name__ == '__main__':
    main()
