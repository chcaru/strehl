"""Independent fixed-score and optimizer commissioning; no original-source reads."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'learned-band-guide'
NATIVE = OLD / 'replay-1/output/screen.json'
CONSUMER_SHA = 'b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987'
DATASET_SHA = '0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19'
NATIVE_SHA = '1f3e67c0d20fbb7a3381d86ce8fc9de20267c56689da04fd3fb43ae5d0cb8c23'
IDS = ['held-flat-n5', 'held-flat-n9', 'held-curved-bright-occlusion-n9',
       'held-near-fine-far-coarse-n5', 'held-unclipped-point-glint-n5',
       'held-clipped-point-glint-n5', 'held-weak-colour-dots-n5']
WINDOWS = {
    'interior': [30,30,162,146],
    'curved-bright-boundary-positive': [55,43,135,130],
    'near-fine-far-coarse-positive': [66,42,130,138],
    'genuine-unclipped-glint': [77,73,100,96],
    'glint-adjacent-near-detail': [127,49,156,134],
    'unclipped-spread-outside-core': [98,69,113,110],
    'weak-colour-components': [49,43,136,128],
}
BINDINGS = {}


def need(value, message):
    if not value:
        raise RuntimeError(message)


def read(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    BINDINGS[str(path)] = hashlib.sha256(data).hexdigest()
    return data


def load(path):
    return json.loads(read(path))


def sha(path):
    return hashlib.sha256(read(path)).hexdigest()


def blob(parent, row, np):
    path = (Path(parent) / row['file']).resolve()
    need(row['dtype'] == '<f4' and path.suffix == '.f32', 'expected f32 blob')
    data = read(path)
    need(hashlib.sha256(data).hexdigest() == row['sha256'], 'changed blob')
    a = np.frombuffer(data, dtype='<f4').reshape(row['shape'])
    need(bool(np.isfinite(a).all()), 'nonfinite blob')
    return a


def templates(case_id, np):
    """Independent analytic held-family components, ordered finite f32 blur."""
    f = np.float32
    yy, xx = np.indices((176,192), dtype=np.float32)
    zero = np.zeros((176,192,3), dtype=np.float32)
    def bump(cx,cy,sx,sy):
        dx = (xx-f(cx))/f(sx)
        dy = (yy-f(cy))/f(sy)
        return np.exp(f(-.5)*(dx*dx+dy*dy))
    def coloured(a, values):
        return a[...,None]*np.asarray(values,dtype=np.float32)
    if 'flat-' in case_id:
        base = zero+f(.25)
        near, far = zero.copy(), zero.copy()
    elif 'curved-' in case_id:
        dx,dy=(xx-f(94))/f(32),(yy-f(87))/f(36)
        a=(dx*dx+dy*dy<=f(1)).astype(np.float32)
        px,py=np.remainder(xx-f(62),f(9))-f(4.5),np.remainder(yy-f(53),f(11))-f(5.5)
        nd=coloured(np.exp(f(-.5)*(px*px+py*py)/(f(1.2)*f(1.2))),[.038,.032,.028])
        fd=coloured(bump(123,87,1.5,21),[.07,.06,.05])
        base=(a*f(.09)+(f(1)-a)*f(.66))[...,None]+zero
        near,far=a[...,None]*nd,(f(1)-a)[...,None]*fd
    elif 'near-fine-' in case_id:
        centre=f(96)+f(10)*np.sin((yy-f(88))/f(21))
        a=(np.abs(xx-centre)<f(4)).astype(np.float32)
        nd=coloured(np.where(np.floor(yy/f(4)).astype(int)%2==0,f(1),f(-1)),[.09,.07,.08])
        dx,dy=xx-f(101),yy-f(89)
        radius=np.sqrt(dx*dx+dy*dy)
        fd=coloured(np.cos(f(2)*f(np.pi)*f(.026)*radius+f(.43)),[.055,.065,.05])
        base=(a*f(.28)+(f(1)-a)*f(.18))[...,None]+zero
        near,far=a[...,None]*nd,(f(1)-a)[...,None]*fd
    elif 'point-glint-' in case_id:
        a=(xx>f(117)+f(5)*np.sin((yy-f(88))/f(17))).astype(np.float32)
        px,py=np.remainder(xx-f(18),f(8))-f(4),np.remainder(yy-f(25),f(10))-f(5)
        nd=coloured(((np.abs(px)<f(1.3))|(np.abs(py)<f(1.3))).astype(np.float32),[.045,.04,.055])
        peak=2.4 if 'held-clipped-' in case_id else .65
        fd=(f(peak)*bump(88,84,1.6,1.6))[...,None]+zero
        base=(a*f(.22)+(f(1)-a)*f(.17))[...,None]+zero
        near,far=a[...,None]*nd,(f(1)-a)[...,None]*fd
    else:
        need('weak-colour-' in case_id, 'unknown held fixture')
        nd=zero.copy()
        for j,(cx,cy) in enumerate([(65,63),(101,63),(65,107),(101,107)]):
            signed=np.asarray([1 if (j+c)%2==0 else -1 for c in range(3)],dtype=np.float32)
            nd=nd+(np.asarray([.055,.012,.038],dtype=np.float32)*signed)[None,None,:]*bump(cx,cy,1.6,5.5)[...,None]
        fd=coloured(((np.abs(xx-f(124))<f(2))&(yy>f(51))&(yy<f(124))).astype(np.float32),[.025,.010,.045])
        a=(xx<f(113)).astype(np.float32)
        base=(a*f(.18)+(f(1)-a)*f(.18))[...,None]+zero
        near,far=a[...,None]*nd,(f(1)-a)[...,None]*fd
    kernel=[]
    mass=f(0)
    for j in range(7):
        q=(f(j)-f(3))/f(.7)
        w=f(math.exp(float(f(-.5)*(q*q))))
        kernel.append(w)
        mass=f(mass+w)
    kernel=[f(w/mass) for w in kernel]
    def blur(v):
        padded=np.pad(v,((0,0),(3,3),(0,0)),mode='edge')
        tmp=np.zeros_like(v)
        for j,w in enumerate(kernel):
            tmp=tmp+w*padded[:,j:j+192]
        padded=np.pad(tmp,((3,3),(0,0),(0,0)),mode='edge')
        out=np.zeros_like(v)
        for j,w in enumerate(kernel):
            out=out+w*padded[j:j+176]
        return out[16:160,16:176]
    return {'base':blur(base),'near':blur(near),'far':blur(far),'truth':blur((base+near)+far)}


def score(case, rgb, window, np):
    need(rgb.shape==(144,160,3) and bool(np.isfinite(rgb).all()), 'RGB shape/finite')
    x0,y0,x1,y1=WINDOWS[window]
    def crop(a):
        return a[y0-16:y1-16,x0-16:x1-16].astype(np.float64).reshape(-1,3)
    value=crop(rgb)
    e=value-crop(case['truth'])
    a,b=crop(case['near']),crop(case['far'])
    y=value-crop(case['base'])
    coeff=[[None,None] for _ in range(3)]
    sd=[]
    condition=[None]*3
    for c in range(3):
        ac,bc,yc=[v[:,c]-v[:,c].mean() for v in (a,b,y)]
        aa,ab,bb,ay,by=[float(np.dot(u,v)) for u,v in [(ac,ac),(ac,bc),(bc,bc),(ac,yc),(bc,yc)]]
        sa,sb=math.sqrt(max(aa,0)/len(a)),math.sqrt(max(bb,0)/len(a))
        sd.append([sa,sb])
        if sa>=.001 and sb>=.001:
            det=aa*bb-ab*ab
            if det/(aa*bb)>.05:
                coeff[c]=[(ay*bb-by*ab)/det,(by*aa-ay*ab)/det]
                r=abs(ab/math.sqrt(aa*bb))
                condition[c]=(1+r)/(1-r)
        elif sa>=.001:
            coeff[c][0],condition[c]=ay/aa,1.0
        elif sb>=.001:
            coeff[c][1],condition[c]=by/bb,1.0
    return {'rgb_rmse':float(np.sqrt(np.mean(e*e))),
            'green_rmse':float(np.sqrt(np.mean(e[:,1]**2))),
            'chroma_rmse':float(np.sqrt(np.mean(np.stack([e[:,0]-e[:,1],e[:,2]-e[:,1]],axis=1)**2))),
            'signed_rgb_bias':float(e.mean()),'near_far_coefficients':coeff,
            'template_sd':sd,'standardized_condition':condition}


def safe(reference, candidate):
    return all(candidate[k]<=1.10*reference[k] for k in ('rgb_rmse','green_rmse','chroma_rmse'))


def retained(reference, candidate):
    for rr,cc in zip(reference['near_far_coefficients'],candidate['near_far_coefficients']):
        for r,c in zip(rr,cc):
            if r is not None and r>=.5 and (c is None or min(1,max(0,c))<.9*min(r,1)):
                return False
    return True


def judge(case,rgb,np):
    rows=[]
    eligible=unqualified=0
    for window in case['windows']:
        c,u,p=[score(case,v,window,np) for v in (case['canonical'],case['uniform'],rgb)]
        for ref in (c,u):
            for pair in ref['near_far_coefficients']:
                for value in pair:
                    if value is not None:
                        eligible+=int(value>=.5)
                        unqualified+=int(value<.5)
        rows.append({'window':window,'native_xyxy':WINDOWS[window],'canonical':c,'uniform':u,'candidate':p,
                     'preservation_pass':safe(c,p) and safe(u,p) and retained(c,p) and retained(u,p)})
    positive=None
    for row in rows:
        if row['window'].endswith('-positive'):
            better=min(row['canonical']['rgb_rmse'],row['uniform']['rgb_rmse'])
            positive={'window':row['window'],'candidate_rgb_rmse':row['candidate']['rgb_rmse'],
                      'better_reference_rgb_rmse':better,'pass':row['candidate']['rgb_rmse']<=.95*better}
    preservation=all(r['preservation_pass'] for r in rows)
    pp=positive is None or positive['pass']
    return {'id':case['id'],'windows':rows,'positive':positive,'preservation_pass':preservation,
            'positive_pass':pp,'pass':preservation and pp,'eligible_reference_components':eligible,
            'unqualified_reference_components':unqualified}


def compare_tree(a,b,tolerance):
    if isinstance(a,list):
        need(isinstance(b,list) and len(a)==len(b), 'score list shape differs')
        return max([compare_tree(x,y,tolerance) for x,y in zip(a,b)]+[0.0])
    if a is None or b is None:
        need(a is None and b is None,'score availability differs')
        return 0.0
    need(math.isfinite(a) and math.isfinite(b),'nonfinite score')
    delta=abs(a-b)
    need(delta<=tolerance,f'native score parity failed: {a} vs {b}, tolerance {tolerance}')
    return delta


def load_cases(dataset,np):
    need(sha(dataset)==DATASET_SHA and sha(NATIVE)==NATIVE_SHA,'retained dataset/native screen changed')
    data=load(dataset)
    need(data['schema']==1 and len(data['heldout'])==7,'fixed seven cases')
    native=load(NATIVE)
    need(native['dataset_sha256']==sha(dataset) and native['mechanical_pass'] is True,'retained native binding')
    cases=[]
    parities=[]
    for ident,path,row in zip(IDS,data['heldout'],native['cases']):
        path=Path(path).resolve()
        need(path.parent.name==ident and row['id']==ident,'fixed flat-first case order')
        meta=load(path)
        t=templates(ident,np)
        truth=blob(path.parent,meta['arrays']['truth-rgb'],np)
        te=float(np.max(np.abs(t['truth']-truth)))
        need(te<=2e-7,'independent analytic truth mismatch')
        c={'id':ident,'path':path,'meta':meta,**t,'truth':truth,
           'canonical':blob(path.parent,meta['arrays']['canonical-rgb'],np),
           'uniform':blob(path.parent,meta['arrays']['uniform-rgb'],np),
           'windows':[r['window'] for r in row['windows']]}
        parity={'id':ident,'truth_max_abs':te,'errors_max_abs':0.0,'coefficients_max_abs':0.0,'template_sd_max_abs':0.0}
        for w in row['windows']:
            need(WINDOWS[w['window']]==w['native_xyxy'],'native window changed')
            for arm in ('canonical','uniform'):
                s=score(c,c[arm],w['window'],np)
                for key in ('rgb_rmse','green_rmse','chroma_rmse','signed_rgb_bias'):
                    parity['errors_max_abs']=max(parity['errors_max_abs'],compare_tree(s[key],w[arm][key],2e-7))
                for key in ('near_far_coefficients','standardized_condition'):
                    parity['coefficients_max_abs']=max(parity['coefficients_max_abs'],compare_tree(s[key],w[arm][key],2e-4))
                for computed,saved in zip(s['near_far_coefficients'],w[arm]['near_far_coefficients']):
                    need(all((a is not None and a>=.5)==(b is not None and b>=.5) for a,b in zip(computed,saved)),
                         'reference component eligibility changed')
                parity['template_sd_max_abs']=max(parity['template_sd_max_abs'],compare_tree(s['template_sd'],w[arm]['template_sd'],2e-7))
        cases.append(c)
        parities.append(parity)
    need([c['id'] for c in cases]==IDS,'case coverage')
    truths=[judge(c,c['truth'],np) for c in cases]
    need(all(r['pass'] for r in truths),'known truth cannot pass checker')
    thin,colour=cases[3],cases[6]
    rng=np.random.default_rng(0x97650b13)
    noise=(cases[0]['truth']+np.float32(.10)*rng.standard_normal((144,160,3)).astype(np.float32)).astype(np.float32)
    destroyers={
        'erased_near_detail':judge(thin,thin['truth']-thin['near'],np),
        'erased_far_depth':judge(thin,thin['truth']-thin['far'],np),
        'added_noise':judge(cases[0],noise,np),
        'erased_image':judge(colour,np.zeros((144,160,3),np.float32),np),
    }
    need(all(not d['pass'] for d in destroyers.values()),'known destroyer accepted')
    return cases,{'native_reference_parity':parities,'known_truth_pass':True,'destroyers':destroyers,
                  'destroyers_rejected':True,'noise_destroyer_independent_seeded_numpy':True}


def consumer():
    path=OLD/'train.py'
    need(sha(path)==CONSUMER_SHA,'commissioned consumer changed before import')
    spec=importlib.util.spec_from_file_location('frozen_band_consumer',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sha(path)
    return module


def prediction(row,case,np):
    need(Path(row['case']).resolve()==case['path'] and row['case_sha256']==sha(case['path']),'prediction case binding')
    need(set(row['arrays'])=={'cfa','rgb','weights-0','weights-1','weights-2'},'prediction array set')
    arrays={k:blob(Path(),v,np) for k,v in row['arrays'].items()}
    need(arrays['cfa'].shape==(4,72,80) and arrays['rgb'].shape==(144,160,3),'prediction image shape')
    return arrays


def replay(case,pred,t,np,torch):
    loaded=t.load_case(case['path'],np,torch,truth=True,goldens=True)
    for item in loaded['bindings']:
        need(sha(item['file'])==item['sha256'],'consumer input changed')
    batch=t.batched([loaded],torch)
    weights=[]
    for k,(w,h) in enumerate(((80,72),(40,36),(20,18))):
        a=pred[f'weights-{k}']
        need(a.shape==(case['meta']['source_count'],h,w),'free-weight shape')
        need(bool((a>=0).all()) and bool((a<=1.000001).all()),'finite nonnegative exp weights required')
        need(float(np.max(np.abs(a.max(axis=0)-1)))<=1e-6,'exp-max normalization changed')
        weights.append(torch.from_numpy(a.copy()).to('cuda')[None])
    with torch.no_grad():
        cfa,rgb,_=t.reconstruct(batch,weights,torch)
    ce=float(np.max(np.abs(cfa[0].cpu().numpy()-pred['cfa'])))
    re=float(np.max(np.abs(rgb[0].cpu().numpy()-pred['rgb'])))
    need(ce<=.02 and re<=5e-6,'final saved weights do not reproduce saved output')
    return batch,{'id':case['id'],'cfa_max_abs_dn':ce,'rgb_max_abs':re,'all_boundaries_included':True}


def directional(batch,t,torch):
    logits=[torch.zeros_like(batch[f'prescribed-weights-{k}'],requires_grad=True) for k in range(3)]
    def loss(values):
        weights=[torch.exp(v-v.amax(dim=1,keepdim=True)) for v in values]
        _,rgb,_=t.reconstruct(batch,weights,torch)
        return (rgb-batch['prescribed-rgb']).square().mean()
    objective=loss(logits)
    grad=torch.autograd.grad(objective,logits)
    need(all(bool(torch.isfinite(g).all()) for g in grad),'nonfinite autograd')
    maximum=max(float(g.abs().max()) for g in grad)
    need(maximum>0,'zero gradient cannot commission optimizer')
    direction=[-g.detach()/maximum for g in grad]
    ad=sum(float((g*d).sum()) for g,d in zip(grad,direction))
    eps=.01
    with torch.no_grad():
        plus=float(loss([v+eps*d for v,d in zip(logits,direction)]))
        minus=float(loss([v-eps*d for v,d in zip(logits,direction)]))
    fd=(plus-minus)/(2*eps)
    relative=abs(fd-ad)/abs(ad)
    need(ad<0 and math.isfinite(fd) and relative<=.05,'directional finite difference disagrees')
    need(plus<float(objective)<minus,'descent/ascent foil not exercised')
    return {'objective0':float(objective),'objective_plus':plus,'objective_minus':minus,
            'autograd_directional_derivative':ad,'finite_difference':fd,'relative_error':relative,
            'epsilon':eps,'direction':'-gradient/max_abs_gradient','max_abs_gradient':maximum,
            'wrong_direction_rejected':True,'passed':True}


def objective_check(stated,actual):
    need(math.isfinite(stated) and abs(stated-actual)<=1e-12+1e-6*abs(actual),'saved objective mismatch')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('phase',choices=['check-commission','check'])
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--commission',type=Path)
    p.add_argument('--predictions',type=Path)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    need(not args.out.exists(),'fresh independent output required')
    args.out.mkdir()
    t=consumer()
    np,torch=t.runtime()
    cases,commissioned=load_cases(args.dataset,np)
    sha(OLD/'independent-fixtures.rs')
    common={'schema':1,'dataset':str(args.dataset.resolve()),'dataset_sha256':sha(args.dataset),
            'checker_sha256':sha(__file__),'consumer_sha256':sha(OLD/'train.py'),
            'oracle_fitted_truth_not_heldout':True,'photographic_replay_admitted':False,
            'native_score_port':commissioned}
    if args.phase=='check-commission':
        need(args.commission is not None,'commission directory required')
        fit_path=args.commission/'fit.json'
        fit=load(fit_path)
        need(fit['schema']==1 and fit['target_kind']=='prescribed-rgb' and fit['phase']=='commission'
             and fit['status']=='FINAL_STEP_COMPLETE','known feasible completed fit required')
        need(fit['source_sha256']==sha(HERE/'solve.py'),'commission solver source changed')
        need(fit['dataset_sha256']==common['dataset_sha256'] and fit['consumer_sha256']==common['consumer_sha256'],'commission source binding')
        need(fit['steps']==1024 and fit['learning_rate']==.03 and fit['start']=='uniform-zero-logits'
             and fit['final_only'] is True and fit['cap_seconds']==180 and fit['adam_epsilon']==1e-15,'fixed optimizer changed')
        need(len(fit['cases'])==2,'exactly two commissioning cases')
        rows=[]
        for c,row in zip((cases[0],cases[2]),fit['cases']):
            pred=prediction(row['prediction'],c,np)
            batch,parity=replay(c,pred,t,np,torch)
            target=blob(c['path'].parent,c['meta']['arrays']['prescribed-rgb'],np)
            initial=float(np.mean((c['uniform'].astype(np.float64)-target)**2))
            final=float(np.mean((pred['rgb'].astype(np.float64)-target)**2))
            objective_check(row['initial_mse'],initial)
            objective_check(row['final_mse'],final)
            need(initial>1e-12 and final<=.10*initial,'known-feasible target recovery failed')
            rows.append({'id':c['id'],'initial_mse':initial,'final_mse':final,'ratio':final/initial,
                         'target_sha256':c['meta']['arrays']['prescribed-rgb']['sha256'],
                         'replay':parity,'directional':directional(batch,t,torch),'passed':True})
        result={**common,'passed':True,'mechanical_pass':True,'fit':str(fit_path.resolve()),'fit_sha256':sha(fit_path),
                'source_sha256':fit['source_sha256'],'cases':rows,'status':'COMMISSION_COMPLETE'}
        destination=args.out/'commission.json'
    else:
        need(args.predictions is not None,'predictions required')
        predictions=load(args.predictions)
        need(predictions['dataset_sha256']==common['dataset_sha256'],'oracle dataset changed')
        need(predictions['phase']=='solve' and predictions['truth_assisted_oracle'] is True
             and predictions['consumer_sha256']==CONSUMER_SHA
             and predictions['source_sha256']==sha(HERE/'solve.py'),'oracle prediction provenance differs')
        fit=load(args.predictions.parent/'fit.json')
        need(fit['phase']=='solve' and fit['status']=='FINAL_STEP_COMPLETE'
             and fit['target_kind']=='truth-rgb' and fit['steps']==1024
             and fit['learning_rate']==.03 and fit['adam_epsilon']==1e-15 and fit['final_only'] is True
             and fit['start']=='uniform-zero-logits' and fit['cap_seconds']==180,'fixed oracle fit changed')
        need(fit['predictions_sha256']==sha(args.predictions) and fit['consumer_sha256']==CONSUMER_SHA
             and fit['dataset_sha256']==DATASET_SHA and fit['source_sha256']==sha(HERE/'solve.py'),'oracle fit binding differs')
        need(len(predictions['records'])==7,'exactly seven oracle cases')
        rows=[]
        parities=[]
        need(len(fit['cases'])==7,'oracle fit case count')
        for c,row,fitted in zip(cases,predictions['records'],fit['cases']):
            need(fitted['prediction']==row,'fit/prediction records differ')
            pred=prediction(row,c,np)
            _,parity=replay(c,pred,t,np,torch)
            objective_check(fitted['initial_mse'],float(np.mean((c['uniform'].astype(np.float64)-c['truth'])**2)))
            objective_check(fitted['final_mse'],float(np.mean((pred['rgb'].astype(np.float64)-c['truth'])**2)))
            parities.append(parity)
            rows.append(judge(c,pred['rgb'],np))
        result={**common,'status':'ORACLE_SCREEN_COMPLETE','mechanical_pass':True,'cases':rows,
                'weight_replay':parities,'predictions_sha256':sha(args.predictions),
                'all_fixed_screen_guards_pass':all(r['pass'] for r in rows),
                'positive_cases_with_preservation':[r['id'] for r in rows if r['positive'] is not None and r['pass']],
                'candidate_nominated':False,'failed_search_proves_ceiling':False}
        destination=args.out/'screen.json'
    result['inputs']=[{'path':path,'sha256':value} for path,value in sorted(BINDINGS.items())]
    with destination.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,allow_nan=False)


if __name__=='__main__':
    main()
