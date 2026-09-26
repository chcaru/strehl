"""Variable-level generated-fixture consumer; no training driver or RAW access.

The original expand/MHC and the frozen 27,201-parameter model are imported by
content hash. Fixture arrays stay CPU-backed. Statistics and reconstruction are
O(image); model calls visit one source and one spatial tile, never N CNN
activation volumes. This remains a generated-data adapter, not a full-photo
source loader. Source coefficients/features on disk are the bounded native
fixture export, not a permitted production aligned-frame cache.

A future training caller may request activation checkpointing. It then retains
source input features/coefficients needed for backward, even though it does not
retain all CNN activations. That is still O(N*fixture_pixels) training storage;
large seven-band cases must be processed individually under the root memory
bound. No production-memory or speed claim follows from this module.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'learned-band-guide/train.py'
OLD_SHA = 'b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987'
SCORER = HERE / 'train.py'
SCORER_SHA = '03ddcab38c492557244638d93694b66473a749aaac6f7785fb129be98dfce96f'
FEATURES = 30
DEFAULT_TILE = 256


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def imports():
    modules = []
    for label,path,expected in [('consumer',OLD,OLD_SHA),('scorer',SCORER,SCORER_SHA)]:
        need(sha(path) == expected, f'frozen {label} changed')
        spec = importlib.util.spec_from_file_location(f'generic_frozen_{label}',path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return tuple(modules)


def declared_cases(dataset, purpose):
    """Read only a manifest. Never open the opposite split's case or pixels."""
    need(purpose in ('train','infer','commission'), 'explicit purpose required')
    dataset = Path(dataset).resolve()
    row = json.loads(dataset.read_text())
    need(row['schema'] == 1 and row['split'] in ('training','heldout'), 'explicit split manifest required')
    need(purpose != 'train' or row['split'] == 'training', 'fresh held truth cannot train')
    paths = [Path(p).resolve() if Path(p).is_absolute() else (dataset.parent/p).resolve()
             for p in row['cases']]
    need(paths and len(set(paths)) == len(paths), 'empty or duplicated declared cases')
    need(all(p.name == 'case.json' and p.is_relative_to(dataset.parent) for p in paths),
         'case outside its split export')
    return [{'path':str(p),'split':row['split'],'purpose':purpose,
             'manifest':str(dataset),'manifest_sha256':sha(dataset)} for p in paths]


def load_case(declared, np, torch, *, goldens=False):
    """CPU-backed arrays; only purpose=train can open truth-rgb."""
    purpose = declared['purpose']
    need(purpose in ('train','infer','commission'), 'invalid declared purpose')
    need(purpose != 'train' or declared['split'] == 'training', 'held training forbidden')
    need(not goldens or purpose == 'commission', 'goldens are commissioning-only')
    path = Path(declared['path']).resolve()
    need(sha(declared['manifest']) == declared['manifest_sha256'], 'split manifest changed')
    meta = json.loads(path.read_text())
    sizes = meta['level_sizes']
    bands = len(sizes)-1
    n = meta['source_count']
    need(meta['schema'] == 1 and bands in (3,7) and 2 <= n <= 65, 'declared3/7AC,N2..65 scope')
    need(all(len(s)==2 and all(isinstance(v,int) and v>0 for v in s) for s in sizes), 'level sizes invalid')
    need(all(sizes[k+1] == [(sizes[k][0]+1)//2,(sizes[k][1]+1)//2] for k in range(bands)),
         'finite pyramid recurrence differs')
    w,h = sizes[0]
    need((bands==3 and [w,h]==[80,72]) or
         (bands==7 and [w,h] in ([1024,1024],[1031,1029]) and n<=17), 'fixture geometry/count scope')
    need(meta['original_linear_reconstruction'] and meta['terminal_mean_exact']
         and meta['zero_network_uniform_exact'], 'native reconstruction contract differs')
    need(math.isfinite(meta['range']) and meta['range']>0 and len(meta['wb'])==3
         and all(math.isfinite(v) and v>0 for v in meta['wb']), 'development constants invalid')
    shapes = {'base':[4,sizes[-1][1],sizes[-1][0]],'lower':[4,h,w],'upper':[4,h,w]}
    for k,(wk,hk) in enumerate(sizes[:-1]):
        shapes[f'coeff-{k}'] = [n,4,hk,wk]
        shapes[f'features-{k}'] = [n,10,hk,wk]
        if goldens:
            shapes[f'prescribed-weights-{k}'] = [n,hk,wk]
    if purpose == 'train':
        shapes['truth-rgb'] = [2*h,2*w,3]
    if goldens:
        for label in ('uniform','prescribed'):
            shapes[f'{label}-cfa'] = [4,h,w]
            shapes[f'{label}-rgb'] = [2*h,2*w,3]
        shapes['zero-network-rgb'] = [2*h,2*w,3]
    arrays,bindings,mappings = {},[],[]
    for key,shape in shapes.items():
        row=meta['arrays'][key]
        source=(path.parent/row['file']).resolve()
        need(source.parent==path.parent and source.suffix=='.f32' and row['dtype']=='<f4'
             and row['shape']==shape, 'array path/layout differs')
        need(source.stat().st_size==4*math.prod(shape) and sha(source)==row['sha256'], 'array bytes/hash differ')
        # Private copy-on-write mapping is writable for torch but cannot write source files.
        mapping=np.memmap(source,dtype='<f4',mode='c',shape=tuple(shape))
        need(bool(np.isfinite(mapping).all()), 'nonfinite exported array')
        arrays[key]=torch.from_numpy(mapping)
        mappings.append(mapping)
        bindings.append({'key':key,'path':str(source),'sha256':row['sha256']})
    need(bool(torch.all(arrays['lower']<=arrays['upper'])), 'input hull reversed')
    return {'path':str(path),'sha256':sha(path),'meta':meta,'arrays':arrays,'bindings':bindings,
            'declared':declared,'bands':bands,'mappings':mappings,'truth_read':purpose=='train'}


def prepare_statistics(case, torch, device='cuda'):
    """Streaming f32 sum/second moment; scene variation, never sensor noise."""
    result=[]
    n=case['meta']['source_count']
    with torch.no_grad():
        for k,(w,h) in enumerate(case['meta']['level_sizes'][:-1]):
            total=torch.zeros((1,4,h,w),device=device,dtype=torch.float32)
            square=torch.zeros_like(total)
            for i in range(n):
                c=case['arrays'][f'coeff-{k}'][i:i+1].to(device)
                total=total+c
                square=square+c.square()
            mean=total/n
            second=square/n
            scale=(second.mean(1,keepdim=True)+(case['meta']['range']/16384.)**2).sqrt()
            sd=(second-mean.square()).clamp_min(0).sqrt()
            need(bool(torch.isfinite(scale).all() and (scale>0).all()), 'scene scale invalid')
            result.append({'mean':mean/scale,'sd':sd/scale,'scale':scale})
    return result


def source_features(case, index, k, statistics, source_coeff, helper, scorer, torch):
    """[1,1,30,H,W], using original source AC at each originating level."""
    bands=case['bands']
    n=case['meta']['source_count']
    need(0<=index<n and 0<=k<bands and len(statistics)==bands, 'source/level index invalid')
    c=source_coeff[k]
    _,_,h,w=c.shape
    normalized=c/statistics[k]['scale']
    parent=helper.expand(source_coeff[k+1]/statistics[k+1]['scale'],h,w,torch) if k+1<bands else torch.zeros_like(c)
    child=scorer.reduce(source_coeff[k-1]/statistics[k-1]['scale'],torch) if k>0 else torch.zeros_like(c)
    need(parent.shape==c.shape and child.shape==c.shape, 'cross-scale support shape differs')
    old=case['arrays'][f'features-{k}'][index:index+1,:5].to(c.device)
    g=old[:,2:3]
    headroom=1.-torch.maximum(torch.maximum(g,g+old[:,3:4]),g+old[:,4:5])
    one=torch.ones_like(g)
    log_scale=torch.log1p(statistics[k]['scale']*16384./case['meta']['range'])
    value=torch.cat((normalized,statistics[k]['mean'],statistics[k]['sd'],parent,child,
        old[:,2:5],old[:,:2],headroom,one*float(k+1<bands),one*float(k>0),one*(k/6.),log_scale),dim=1)
    need(value.shape==(1,FEATURES,h,w) and bool(torch.isfinite(value).all()), 'feature convention invalid')
    return value[:,None]


def score_source(model, features, torch, *, tile=DEFAULT_TILE, checkpoint_activations=False):
    """Exact 3-pixel network context; no tile-specific feature normalization."""
    need(features.ndim==5 and features.shape[:3]==(1,1,FEATURES) and tile>=8, 'one-source tile scope')
    h,w=features.shape[-2:]
    if checkpoint_activations:
        from torch.utils.checkpoint import checkpoint
    rows=[]
    for y in range(0,h,tile):
        columns=[]
        end_y=min(h,y+tile)
        y0,y1=max(0,y-3),min(h,end_y+3)
        for x in range(0,w,tile):
            end_x=min(w,x+tile)
            x0,x1=max(0,x-3),min(w,end_x+3)
            piece=features[...,y0:y1,x0:x1]
            scored=checkpoint(model,piece,use_reentrant=False) if checkpoint_activations else model(piece)
            columns.append(scored[...,y-y0:end_y-y0,x-x0:end_x-x0])
        rows.append(torch.cat(columns,dim=-1))
    return torch.cat(rows,dim=-2)


def render(case, torch, *, mode, model=None, statistics=None, weights=None, keep_weights=False,
           gradients=False, checkpoint_activations=False, tile=DEFAULT_TILE):
    """One case, source-streamed weights/accumulation, complete final CFA/RGB."""
    need(mode in ('uniform','prescribed','model','weights'), 'explicit rendering mode')
    need(not gradients or mode=='model', 'gradient mode only for predictor')
    need(not gradients or checkpoint_activations, 'training must checkpoint CNN activations')
    need(mode!='model' or model is not None, 'model required')
    helper,scorer=imports()
    device=next(model.parameters()).device if model is not None else torch.device('cuda')
    bands=case['bands']; sizes=case['meta']['level_sizes']; n=case['meta']['source_count']
    if mode=='weights':
        need(weights is not None and len(weights)==bands and all(
            tuple(v.shape)==(n,sizes[k][1],sizes[k][0]) for k,v in enumerate(weights)),
            'saved weight shape differs')
    if mode=='model' and statistics is None:
        statistics=prepare_statistics(case,torch,device)
    numerator=[torch.zeros((1,4,h,w),device=device,dtype=torch.float32) for w,h in sizes[:-1]]
    denominator=[torch.zeros((1,h,w),device=device,dtype=torch.float32) for w,h in sizes[:-1]]
    saved=[[] for _ in range(bands)] if keep_weights else None
    with torch.set_grad_enabled(gradients):
        for i in range(n):
            source=[case['arrays'][f'coeff-{k}'][i:i+1].to(device) for k in range(bands)]
            for k,(w,h) in enumerate(sizes[:-1]):
                if mode=='uniform':
                    weight=torch.ones((1,h,w),device=device,dtype=torch.float32)
                elif mode=='prescribed':
                    weight=case['arrays'][f'prescribed-weights-{k}'][i:i+1].to(device)
                elif mode=='weights':
                    weight=weights[k][i:i+1].to(device)
                else:
                    feature=source_features(case,i,k,statistics,source,helper,scorer,torch)
                    weight=score_source(model,feature,torch,tile=tile,
                        checkpoint_activations=checkpoint_activations)[:,0]
                need(bool(torch.isfinite(weight).all() and (weight>0).all()), 'weight is not positive finite')
                numerator[k]=numerator[k]+weight[:,None]*(source[k]/65536.)
                denominator[k]=denominator[k]+weight
                if keep_weights:
                    # Generated training retains weight graphs for the flat KL term;
                    # inference records are detached CPU arrays as before.
                    saved[k].append(weight if gradients else weight.detach().cpu())
        fused=[]
        for num,den in zip(numerator,denominator):
            need(bool(torch.isfinite(num).all() and torch.isfinite(den).all() and (den>0).all()),
                 'native scaled accumulation invalid')
            fused.append((num/den[:,None])*65536.)
        cfa=case['arrays']['base'][None].to(device)
        for k in reversed(range(bands)):
            cfa=helper.expand(cfa,sizes[k][1],sizes[k][0],torch)+fused[k]
        before=cfa
        cfa=torch.minimum(torch.maximum(cfa,case['arrays']['lower'][None].to(device)),
                          case['arrays']['upper'][None].to(device))
        wb=torch.tensor([case['meta']['wb']],device=device,dtype=torch.float32)
        ranges=torch.tensor([case['meta']['range']],device=device,dtype=torch.float32)
        rgb=helper.mhc(cfa,wb,ranges,torch)
        need(bool(torch.isfinite(cfa).all() and torch.isfinite(rgb).all()), 'final image nonfinite')
    return {'cfa':cfa,'rgb':rgb,'before_hull':before,
            'weights':[torch.cat(w,dim=0) for w in saved] if keep_weights else None,
            'mode':mode,'source_count':n,'bands':bands,'network_source_chunk':1,'network_tile':tile,
            'truth_read':case['truth_read'],'scene_statistics':'sequential-f32-source-sums'}


def reconstruct(case, weights, torch):
    """Replay saved [N,Hk,Wk] weights without invoking any feature/model path."""
    return render(case,torch,mode='weights',weights=weights)


def write_prediction(out, case, result, np):
    out=Path(out).resolve()
    need(not out.exists() and result['weights'] is not None, 'fresh output and retained weights required')
    out.mkdir()
    arrays={}
    values=[('cfa',result['cfa'][0]),('rgb',result['rgb'][0])]
    values += [(f'weights-{k}',v) for k,v in enumerate(result['weights'])]
    for name,tensor in values:
        value=tensor.detach().cpu().numpy().astype('<f4',copy=False)
        path=out/f'{name}.f32'
        with path.open('xb') as handle:
            handle.write(value.tobytes())
        arrays[name]={'file':str(path),'sha256':sha(path),'shape':list(value.shape),'dtype':'<f4'}
    return {'case':case['path'],'case_sha256':case['sha256'],'arrays':arrays}


def commission(dataset, np, torch, out, *, require_odd_seven=False):
    """Root-callable mechanical parity, never truth scoring or training."""
    helper,scorer=imports()
    out=Path(out).resolve()
    need(not out.exists(), 'fresh commissioning output')
    out.mkdir()
    records=[]; saw_odd_seven=False; saw_hull=False; conventions=None
    for declared in declared_cases(dataset,'commission'):
        case=load_case(declared,np,torch,goldens=True)
        need(not case['truth_read'] and 'truth-rgb' not in case['arrays'], 'commission opened sharp truth')
        rows=[]
        for mode in ('uniform','prescribed'):
            result=render(case,torch,mode=mode)
            cfa=case['arrays'][f'{mode}-cfa'][None].to(result['cfa'].device)
            rgb=case['arrays'][f'{mode}-rgb'][None].to(result['rgb'].device)
            ce=float((result['cfa']-cfa).abs().max()); re=float((result['rgb']-rgb).abs().max())
            need(ce<=.02 and re<=5e-6, 'dynamic reconstruction differs from native complete output')
            changed=int((result['before_hull']!=result['cfa']).sum())
            saw_hull=saw_hull or changed>0
            rows.append({'mode':mode,'maximum_cfa_error_dn':ce,'maximum_rgb_error':re,
                         'all_boundary_pixels_included':True,'clamped_sites':changed})
            del result,cfa,rgb
        sizes=case['meta']['level_sizes']
        saw_odd_seven=saw_odd_seven or (case['bands']==7 and (sizes[0][0]%2!=0 or sizes[0][1]%2!=0))
        # Full-vector convention check on the first compact case, including nonzero scoring.
        if conventions is None and case['bands']==3:
            batch={key:value[None].cuda() for key,value in case['arrays'].items()
                   if key.startswith('coeff-') or key.startswith('features-')}
            batch['range']=torch.tensor([case['meta']['range']],device='cuda')
            expected,_=scorer.build_features(batch,helper,torch)
            statistics=prepare_statistics(case,torch)
            model=scorer.make_model(torch)
            with torch.no_grad():
                model.head.weight.copy_(torch.linspace(-.1,.1,32,device='cuda').reshape_as(model.head.weight))
                feature_error=0.; score_error=0.
                for i in range(case['meta']['source_count']):
                    source=[case['arrays'][f'coeff-{k}'][i:i+1].cuda() for k in range(3)]
                    for k in range(3):
                        value=source_features(case,i,k,statistics,source,helper,scorer,torch)
                        feature_error=max(feature_error,float((value-expected[k][:,i:i+1]).abs().max()))
                        a=score_source(model,value,torch,tile=32)
                        b=model(expected[k][:,i:i+1])
                        score_error=max(score_error,float((a-b).abs().max()))
                need(feature_error<=2e-4 and score_error<=2e-5, 'streamed feature/scorer convention differs')
            conventions={'maximum_feature_error':feature_error,'maximum_nonzero_score_error':score_error,
                         'source_chunk':1,'tile':32,'f32_moment_association_difference_explicit':True}
            del batch,expected,statistics,model
        records.append({'case':case['path'],'case_sha256':case['sha256'],'bands':case['bands'],
                        'source_count':case['meta']['source_count'],'native_size':sizes[0],
                        'truth_read':False,'arms':rows})
        del case
    need(conventions is not None, 'compact fixed-model convention never exercised')
    need(not require_odd_seven or saw_odd_seven, 'required odd seven-band native parity absent')
    receipt={'schema':1,'passed':True,'source_sha256':sha(__file__),'consumer_sha256':OLD_SHA,
        'scorer_sha256':SCORER_SHA,'dataset':str(Path(dataset).resolve()),'dataset_sha256':sha(dataset),
        'truth_read':False,'independent_validation':False,'photographic_admission':False,
        'saw_odd_seven':saw_odd_seven,'saw_input_hull_clamp':saw_hull,
        'conventions':conventions,'records':records,'peak_cuda_bytes':torch.cuda.max_memory_allocated()}
    save(out/'commission.json',receipt)
    return receipt
