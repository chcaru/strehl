"""Revision 1: signed/cross-scale source scoring on 19 known developer cases.

Only the decision weights are learned. The pinned native-commissioned consumer
still reconstructs original linear CFA coefficients, Mean base, hull and MHC.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import time

ROOT = Path(__file__).resolve().parents[2]
CONSUMER = ROOT / 'experiments/learned-band-guide/train.py'
CONSUMER_SHA = 'b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987'
DATASET_SHA = '0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19'
NATIVE_COMMISSION = CONSUMER.parent / 'commission-1/output/commission.json'
FEATURES = 30
PARAMETERS = 27201
SEED = 137
LEARNING_RATE = .001
ADAM_EPSILON = 1e-8
MAX_STEPS = 2048
CHECKPOINT_INTERVAL = 32
FIT_SECONDS = 180.0
STOP_SECONDS = 170.0
FEATURE_NAMES = ([f'signed-{c}' for c in ('r','g1','g2','b')]
    + [f'set-mean-{c}' for c in ('r','g1','g2','b')]
    + [f'set-sd-{c}' for c in ('r','g1','g2','b')]
    + [f'parent-{c}' for c in ('r','g1','g2','b')]
    + [f'child-{c}' for c in ('r','g1','g2','b')]
    + ['gaussian-g','gaussian-r-minus-g','gaussian-b-minus-g',
       'log-energy-over-floor','log-floor','gaussian-headroom',
       'parent-present','child-present','band-over-six','log-scene-scale'])


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def consumer(dataset):
    need(sha(CONSUMER) == CONSUMER_SHA, 'commissioned consumer changed')
    need(sha(dataset) == DATASET_SHA, 'stage1 requires the fixed19 developer dataset')
    old = json.loads(NATIVE_COMMISSION.read_text())
    need(old['passed'] and old['source_sha256'] == CONSUMER_SHA
         and old['dataset_sha256'] == DATASET_SHA, 'retained native commission differs')
    spec = importlib.util.spec_from_file_location('commissioned_band_consumer', CONSUMER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def reduce_axis(x, torch):
    # Actual finite REDUCE: [1,4,6,4,1]/16 at even centres, replicated edges.
    centres = 2*torch.arange((x.shape[-1]+1)//2, device=x.device)
    result = torch.zeros((*x.shape[:-1], len(centres)), device=x.device, dtype=x.dtype)
    for offset, weight in zip(range(-2,3), (1/16,4/16,6/16,4/16,1/16)):
        result = result + weight*x.index_select(-1, (centres+offset).clamp(0,x.shape[-1]-1))
    return result


def reduce(x, torch):
    return reduce_axis(reduce_axis(x,torch).transpose(-2,-1),torch).transpose(-2,-1)


def build_features(batch, helper, torch):
    coeff = [batch[f'coeff-{k}'] for k in range(3)]
    means, deviations, scales, normalized = [], [], [], []
    for c in coeff:
        mean = c.mean(1, keepdim=True)
        second = c.square().mean(1, keepdim=True)
        sd = (second-mean.square()).clamp_min(0).sqrt()
        epsilon = batch['range'][:,None,None,None,None]/16384.0
        scale = (second.mean(2,keepdim=True)+epsilon.square()).sqrt()
        means.append(mean/scale)
        deviations.append(sd/scale)
        scales.append(scale)
        normalized.append(c/scale)
    result = []
    for k,c in enumerate(coeff):
        b,n,_,h,w = c.shape
        old = batch[f'features-{k}']
        def shared(x):
            return x.expand(b,n,x.shape[2],h,w)
        parent = helper.expand(normalized[k+1],h,w,torch) if k<2 else torch.zeros_like(c)
        child = reduce(normalized[k-1],torch) if k>0 else torch.zeros_like(c)
        need(parent.shape == c.shape and child.shape == c.shape, 'cross-scale phase/extent differs')
        g = old[:,:,2:3]
        # A smoothed radiance feature, NOT a clipping detector or input-hull statistic.
        headroom = 1.0-torch.maximum(torch.maximum(g,g+old[:,:,3:4]),g+old[:,:,4:5])
        one = torch.ones_like(g)
        scale_log = torch.log1p(scales[k]*16384.0/batch['range'][:,None,None,None,None])
        feature = torch.cat((normalized[k],shared(means[k]),shared(deviations[k]),
            parent,child,old[:,:,2:5],old[:,:,:2],headroom,
            one*float(k<2),one*float(k>0),one*(k/6.0),shared(scale_log)),dim=2)
        need(feature.shape == (b,n,FEATURES,h,w) and bool(torch.isfinite(feature).all()),
             'invalid richer feature tensor')
        result.append(feature)
    return result,scales


def make_model(torch):
    class Score(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = torch.nn.Conv2d(FEATURES,32,3)
            self.conv2 = torch.nn.Conv2d(32,32,3)
            self.conv3 = torch.nn.Conv2d(32,32,3)
            self.head = torch.nn.Conv2d(32,1,1)
            torch.nn.init.zeros_(self.head.weight)
            torch.nn.init.zeros_(self.head.bias)

        def forward(self,features):
            b,n,c,h,w = features.shape
            x = features.reshape(b*n,c,h,w)
            for layer in (self.conv1,self.conv2,self.conv3):
                # Explicit concatenation also has deterministic CUDA backward.
                x = torch.cat((x[...,:1],x,x[...,-1:]),dim=-1)
                x = torch.cat((x[...,:1,:],x,x[...,-1:,:]),dim=-2)
                x = torch.nn.functional.silu(layer(x))
            logits = self.head(x).reshape(b,n,h,w)
            return weights_from_logits(logits,torch)
    model = Score().cuda()
    need(sum(p.numel() for p in model.parameters()) == PARAMETERS, 'architecture differs')
    return model


def weights_from_logits(logits,torch):
    need(bool(torch.isfinite(logits).all()), 'nonfinite scores')
    weights = 2*torch.sigmoid(logits.clamp(-30,30))
    need(bool(torch.isfinite(weights).all() and (weights>0).all() and (weights<=2).all()),
         'weights outside fixed positive range')
    return weights


def model_record(model):
    return {'schema':1,'revision':1,'architecture':'30-32-32-32-1',
            'parameters':PARAMETERS,'feature_names':FEATURE_NAMES,
            'state':{key:{'shape':list(value.shape),'values':value.detach().cpu().flatten().tolist()}
                     for key,value in model.state_dict().items()}}


def load_model(path,torch):
    record = json.loads(Path(path).read_text())
    need(record['schema']==1 and record['revision']==1 and record['parameters']==PARAMETERS
         and record['feature_names']==FEATURE_NAMES, 'model convention differs')
    model = make_model(torch)
    state = model.state_dict()
    need(set(record['state'])==set(state), 'state keys differ')
    with torch.no_grad():
        for key,dst in state.items():
            row=record['state'][key]
            need(row['shape']==list(dst.shape), 'state shape differs')
            value=torch.tensor(row['values'],device='cuda',dtype=torch.float32).reshape(dst.shape)
            need(bool(torch.isfinite(value).all()), 'state nonfinite')
            dst.copy_(value)
    model.load_state_dict(state,strict=True)
    return model.eval()


def loss_mask(cases,batch,torch):
    h,w=batch['coeff-0'].shape[-2:]
    valid=torch.ones((len(cases),2*h,2*w),device='cuda',dtype=torch.float32)
    for i,case in enumerate(cases):
        if Path(case['path']).parent.name=='held-clipped-point-glint-n5':
            # Existing GLINT [77,73,100,96], minus the fixed native crop origin16.
            valid[i,57:80,61:84]=0
    return valid


def loss_regions(cases,batch,torch):
    valid=loss_mask(cases,batch,torch)
    roi=torch.zeros_like(valid)
    for i,case in enumerate(cases):
        name=Path(case['path']).parent.name
        windows=[]
        if name=='held-curved-bright-occlusion-n9': windows=[(55,43,135,130)]
        elif name=='held-near-fine-far-coarse-n5': windows=[(66,42,130,138)]
        elif name=='held-unclipped-point-glint-n5': windows=[(77,73,100,96)]
        elif name=='held-weak-colour-dots-n5': windows=[(49,43,136,128)]
        elif name=='held-clipped-point-glint-n5': windows=[(127,49,156,134),(98,69,113,110)]
        for x0,y0,x1,y1 in windows:
            region=torch.zeros_like(valid[i])
            region[y0-16:y1-16,x0-16:x1-16]=1
            region=region*valid[i]
            roi[i]+=region/(region.sum()*len(windows))
    return roi


def per_case_loss(rgb,truth,weights,flat,torch,valid=None,roi=None):
    residual=rgb-truth
    if valid is None:
        valid=torch.ones_like(rgb[...,0])
    count=valid.flatten(1).sum(1)
    rgb_mse=(residual.square()*valid[...,None]).flatten(1).sum(1)/(3*count)
    chroma=torch.stack((residual[...,0]-residual[...,1],residual[...,2]-residual[...,1]),dim=-1)
    chroma_mse=(chroma.square()*valid[...,None]).flatten(1).sum(1)/(2*count)
    green=residual[...,1]
    mx=valid[:,:,1:]*valid[:,:,:-1]
    my=valid[:,1:,:]*valid[:,:-1,:]
    gradient_mse=.5*(((green[:,:,1:]-green[:,:,:-1]).square()*mx).flatten(1).sum(1)/mx.flatten(1).sum(1)
        +((green[:,1:,:]-green[:,:-1,:]).square()*my).flatten(1).sum(1)/my.flatten(1).sum(1))
    kl=torch.zeros_like(rgb_mse)
    for w in weights:
        p=w/w.sum(1,keepdim=True)
        kl=kl+(p*torch.log((p*w.shape[1]).clamp_min(1e-30))).sum(1).flatten(1).mean(1)/len(weights)
    kl=kl*flat
    roi_error=torch.zeros_like(rgb_mse) if roi is None else (
        (residual.square().mean(-1)+.5*chroma.square().mean(-1))*roi).flatten(1).sum(1)
    total=rgb_mse+.5*chroma_mse+.25*gradient_mse+.01*kl+.25*roi_error
    return total,{'rgb_mse':rgb_mse,'chroma_mse':chroma_mse,'green_gradient_mse':gradient_mse,
                  'flat_kl':kl,'roi_rgb_chroma_mse':roi_error}


def predict(model,batch,features,helper,torch):
    weights=[model(f) for f in features]
    cfa,rgb,before=helper.reconstruct(batch,weights,torch)
    return weights,cfa,rgb,before


def groups(cases,helper,torch):
    result=[]
    for n in sorted({c['meta']['source_count'] for c in cases}):
        selected=[c for c in cases if c['meta']['source_count']==n]
        batch=helper.batched(selected,torch)
        features,_=build_features(batch,helper,torch)
        flat=torch.tensor(['flat' in Path(c['path']).parent.name for c in selected],device='cuda',dtype=torch.float32)
        result.append((selected,batch,features,flat,loss_mask(selected,batch,torch),loss_regions(selected,batch,torch)))
    return result


def evaluate(model,batches,helper,torch):
    records=[]
    with torch.no_grad():
        for cases,batch,features,flat,valid,roi in batches:
            weights,_,rgb,_=predict(model,batch,features,helper,torch)
            loss,parts=per_case_loss(rgb,batch['truth-rgb'],weights,flat,torch,valid,roi)
            for i,case in enumerate(cases):
                records.append({'case':case['path'],'case_sha256':case['sha256'],'loss':float(loss[i]),
                                **{key:float(value[i]) for key,value in parts.items()}})
    return sum(r['loss'] for r in records)/len(records),records


def commission(cases,helper,torch,np,out):
    # A separately chosen odd rectangle and corner impulse exercise finite phases.
    a=np.zeros((5,7),dtype=np.float32)
    a[0,0]=1; a[1,4]=-.5; a[4,6]=2
    kernel=np.array([1,4,6,4,1],dtype=np.float32)/16
    expected=np.zeros((3,4),dtype=np.float32)
    for y in range(3):
        for x in range(4):
            for dy in range(-2,3):
                for dx in range(-2,3):
                    expected[y,x]+=kernel[dy+2]*kernel[dx+2]*a[min(4,max(0,2*y+dy)),min(6,max(0,2*x+dx))]
    got=reduce(torch.from_numpy(a).cuda(),torch).cpu().numpy()
    need(np.array_equal(got,expected), 'odd finite reduce differs from independent 2D oracle')
    need(float(got[0,0])==.47265625, 'corner replication control changed')
    # Dyadic parent corner: independent product of even/odd interpolation weights.
    parent=torch.tensor([[1.,0.,0.,0.],[0.,0.,0.,0.],[0.,0.,0.,0.]],device='cuda')
    expanded=helper.expand(parent,5,7,torch)
    expected_expand=torch.tensor([.875,.5,.125,0,0],device='cuda')[:,None]*torch.tensor([.875,.5,.125,0,0,0,0],device='cuda')[None,:]
    need(torch.equal(expanded,expected_expand), 'odd parent expansion phase differs')
    extreme=weights_from_logits(torch.tensor([-1e30,-30.,0.,30.,1e30],device='cuda'),torch)
    need(float(extreme[0])>0 and float(extreme[2])==1., 'extreme finite/zero weights invalid')
    model=make_model(torch)
    rows=[]
    for index,case in enumerate(cases):
        batch=helper.batched([case],torch)
        features,scales=build_features(batch,helper,torch)
        with torch.no_grad():
            zero=[model(f) for f in features]
            need(all(torch.equal(w,torch.ones_like(w)) for w in zero), 'zero-head not exact uniform')
            records=[]
            for label,weights in [('uniform',zero),('prescribed',[batch[f'prescribed-weights-{k}'] for k in range(3)])]:
                cfa,rgb,before=helper.reconstruct(batch,weights,torch)
                ce=float((cfa-batch[f'{label}-cfa']).abs().max())
                re=float((rgb-batch[f'{label}-rgb']).abs().max())
                need(ce<=.02 and re<=5e-6,'fixed native consumer parity failed')
                records.append({'arm':label,'maximum_cfa_error_dn':ce,'maximum_rgb_error':re,'clamped_sites':int((before!=cfa).sum())})
        folder=out/f'case-{index:02}'
        folder.mkdir()
        scale_rows=[]
        for k,scale in enumerate(scales):
            path=folder/f'scale-{k}.f32'
            data=scale.cpu().numpy().astype('<f4',copy=False)
            path.write_bytes(data.tobytes())
            scale_rows.append({'path':str(path),'sha256':sha(path),'shape':list(data.shape)})
        rows.append({'case':case['path'],'case_sha256':case['sha256'],'arms':records,'scene_scales':scale_rows})
    # Use one structured case with a fixed NONZERO head, never a fitted model.
    case=next(c for c in cases if 'near-fine-far-coarse' in c['path'])
    batch=helper.batched([case],torch)
    feature,_=build_features(batch,helper,torch)
    with torch.no_grad():
        model.head.weight.copy_(torch.linspace(-.1,.1,32,device='cuda').reshape_as(model.head.weight))
        original=[model(f) for f in feature]
        perm=torch.arange(batch['coeff-0'].shape[1]-1,-1,-1,device='cuda')
        swapped=dict(batch)
        repeated=dict(batch)
        inverted=dict(batch)
        for k in range(3):
            for key in (f'coeff-{k}',f'features-{k}'):
                swapped[key]=batch[key].index_select(1,perm)
                repeated[key]=torch.cat((batch[key],batch[key]),dim=1)
            inverted[f'coeff-{k}']=-batch[f'coeff-{k}']
        pf,_=build_features(swapped,helper,torch)
        rf,_=build_features(repeated,helper,torch)
        sf,_=build_features(inverted,helper,torch)
        pe=max(float((model(p).index_select(1,perm)-w).abs().max()) for p,w in zip(pf,original))
        re=max(float((model(r)[:,:w.shape[1]]-w).abs().max()) for r,w in zip(rf,original))
        need(pe<=2e-5 and re<=2e-5,'set permutation/full replication changed scores')
        sign=max(float((model(s)-w).abs().max()) for s,w in zip(sf,original))
        need(sign>1e-6 and all(torch.equal(s[:,:,23:25],f[:,:,23:25]) for s,f in zip(sf,feature)),
             'signed contrast control absent or changed old E/F')
        context=[]
        for lo,hi in ((12,16),(16,20)):
            mutant=[f.clone() for f in feature]
            for f in mutant:
                f[:,:,lo:hi]=0
            delta=max(float((model(f)-w).abs().max()) for f,w in zip(mutant,original))
            need(delta>1e-6,'nonzero cross-scale scorer control unexercised')
            context.append(delta)
        need(bool((feature[0][:,:,16:20]==0).all()) and bool((feature[2][:,:,12:16]==0).all()),
             'absent AC context is not zero')
        need(bool((feature[0][:,:,26]==1).all()) and bool((feature[0][:,:,27]==0).all())
             and bool((feature[2][:,:,26]==0).all()) and bool((feature[2][:,:,27]==1).all()), 'validity bits differ')
    need(any(a['clamped_sites']>0 for r in rows for a in r['arms']),'hull clamp never exercised')
    # The pre-existing clipped core is explicitly not sharp-truth supervision.
    pair=[next(c for c in cases if Path(c['path']).parent.name==name) for name in
          ('held-clipped-point-glint-n5','held-unclipped-point-glint-n5')]
    mb=helper.batched(pair,torch)
    valid=loss_mask(pair,mb,torch)
    roi=loss_regions(pair,mb,torch)
    truth=torch.zeros((2,144,160,3),device='cuda')
    mutation=truth.clone(); mutation[:,57:80,61:84]=1
    mw=[torch.ones_like(mb[f'coeff-{k}'][:,:,0]) for k in range(3)]
    masked_loss,_=per_case_loss(mutation,truth,mw,torch.zeros(2,device='cuda'),torch,valid,roi)
    need(float(masked_loss[0])==0 and float(masked_loss[1])>0,'clipped-only supervision mask failed')
    need(bool((roi[valid==0]==0).all()) and bool(torch.allclose(roi.flatten(1).sum(1),torch.ones(2,device='cuda'))),
         'ROI balancing masks are not normalized or include the clipped core')
    return {'passed':True,'cases':rows,'odd_reduce_exact':True,'odd_expand_exact':True,
            'extreme_weights':extreme.tolist(),'source_permutation_max':pe,'source_replication_max':re,
            'nonzero_scorer_sign_delta':sign,'nonzero_scorer_context_deltas':context,
            'clipped_mask_mutation_losses':masked_loss.tolist(),
            'commission_is_arithmetic_not_photographic_quality':True}


def train(cases,helper,torch,out):
    batches=groups(cases,helper,torch)
    model=make_model(torch)
    optimizer=torch.optim.Adam(model.parameters(),lr=LEARNING_RATE,eps=ADAM_EPSILON)
    torch.cuda.synchronize()
    start=time.perf_counter()
    history=[]
    max_head_gradient=0.; max_body_gradient=0.
    def checkpoint(step):
        score,records=evaluate(model,batches,helper,torch)
        path=out/f'checkpoint-{step:04}.json'
        save(path,model_record(model))
        row={'step':step,'score':score,'model':str(path),'model_sha256':sha(path),'cases':records,
             'seconds':time.perf_counter()-start}
        history.append(row)
        print(json.dumps({'checkpoint':step,'developer_loss':score,'seconds':row['seconds']}),flush=True)
    checkpoint(0)
    step=0
    while step<MAX_STEPS and time.perf_counter()-start<STOP_SECONDS:
        optimizer.zero_grad(set_to_none=True)
        total=0.0
        for selected,batch,features,flat,valid,roi in batches:
            weights,_,rgb,_=predict(model,batch,features,helper,torch)
            loss,_=per_case_loss(rgb,batch['truth-rgb'],weights,flat,torch,valid,roi)
            term=loss.sum()/len(cases)
            need(bool(torch.isfinite(term)),'nonfinite training objective')
            term.backward()
            total+=float(term.detach())
        need(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()),'nonfinite gradients')
        max_head_gradient=max(max_head_gradient,float(model.head.weight.grad.abs().max()))
        max_body_gradient=max(max_body_gradient,float(model.conv1.weight.grad.abs().max()))
        optimizer.step()
        step+=1
        torch.cuda.synchronize()
        need(time.perf_counter()-start<FIT_SECONDS,'fixed180s optimizer cap exceeded')
        if step%CHECKPOINT_INTERVAL==0:
            checkpoint(step)
    if history[-1]['step']!=step:
        checkpoint(step)
    need(time.perf_counter()-start<FIT_SECONDS,'checkpoint exceeded180s fit cap')
    best=min(history,key=lambda r:(r['score'],r['step']))
    with (out/'model.json').open('xb') as handle:
        handle.write(Path(best['model']).read_bytes())
    return {'status':'DEVELOPER_FIT_COMPLETE','revision':1,'steps':step,'maximum_steps':MAX_STEPS,
        'learning_rate':LEARNING_RATE,'adam_epsilon':ADAM_EPSILON,'fit_seconds':time.perf_counter()-start,
        'optimization_cap_seconds':FIT_SECONDS,'checkpoint_interval':CHECKPOINT_INTERVAL,
        'selection':'minimum equal-case declared developer loss; earlier step wins ties',
        'chosen_step':best['step'],'chosen_score':best['score'],'initial_score':history[0]['score'],
        'objective_ratio':best['score']/history[0]['score'],'maximum_head_gradient':max_head_gradient,
        'maximum_body_gradient':max_body_gradient,'body_gradient_live':max_body_gradient>0,
        'history':history,'model_sha256':sha(out/'model.json'),'independent_validation':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['commission','train','infer'])
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--commission',type=Path)
    parser.add_argument('--weights',type=Path)
    args=parser.parse_args()
    helper=consumer(args.dataset)
    out=args.out.resolve()
    need(not out.exists(),'fresh output required')
    out.mkdir()
    paths=helper.manifest(args.dataset)
    paths=paths['training']+paths['heldout']
    need(len(paths)==19,'all19 known developer cases required')
    np,torch=helper.runtime()
    torch.cuda.reset_peak_memory_stats()
    started=time.perf_counter()
    common={'schema':1,'revision':1,'source_sha256':sha(__file__),'consumer_sha256':CONSUMER_SHA,
        'dataset':str(args.dataset.resolve()),'dataset_sha256':sha(args.dataset),
        'retained_native_commission_sha256':sha(NATIVE_COMMISSION),'feature_names':FEATURE_NAMES,
        'parameters':PARAMETERS,'seed':SEED,'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),
        'float32':True,'tf32':False,'deterministic':True,'all19_are_developer_cases':True,
        'heldout_claim':False,'photographic_admission':False}
    cases=[helper.load_case(p,np,torch,truth=args.phase=='train',goldens=args.phase=='commission') for p in paths]
    if args.phase=='commission':
        save(out/'commission.json',{**common,**commission(cases,helper,torch,np,out)})
    elif args.phase=='train':
        need(args.commission is not None,'commission required')
        cp=args.commission if args.commission.is_file() else args.commission/'commission.json'
        control=json.loads(cp.read_text())
        need(control['passed'] and control['source_sha256']==common['source_sha256']
             and control['dataset_sha256']==DATASET_SHA,'commission bindings differ')
        need([c['sha256'] for c in cases]==[r['case_sha256'] for r in control['cases']],'case bindings differ')
        save(out/'training.json',{**common,'commission_sha256':sha(cp),**train(cases,helper,torch,out)})
    else:
        need(args.weights is not None,'frozen weights required')
        model=load_model(args.weights,torch)
        records=[]
        for index,case in enumerate(cases):
            batch=helper.batched([case],torch)
            features,_=build_features(batch,helper,torch)
            with torch.no_grad():
                weights=[model(f) for f in features]
            folder=out/f'case-{index:02}'
            folder.mkdir()
            records.append(helper.write_prediction(folder,case,batch,weights,torch,np))
        save(out/'predictions.json',{**common,'model_sha256':sha(args.weights),'truth_read':False,'records':records})
    torch.cuda.synchronize()
    save(out/'completion.json',{**common,'phase':args.phase,'wall_seconds':time.perf_counter()-started,
        'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'completed':True})


if __name__=='__main__':
    main()
