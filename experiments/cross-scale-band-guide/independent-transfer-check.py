"""Fixed fresh-fixture qualification and frozen-model review; root executes."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
PLAN = HERE/'transfer-plan.md'
GENERIC = HERE/'generic-consumer.py'
INPUTS = {}
METRICS = ('rgb_rmse', 'green_rmse', 'chroma_rmse')
IDS = ['fresh-flat-v0-n17-b3', 'fresh-flat-v3-n65-b3',
       'fresh-forked-filaments-v0-n33-b3', 'fresh-serrated-polygon-v0-n17-b3',
       'fresh-unclipped-glint-v2-n17-b3', 'fresh-clipped-glint-v2-n17-b3',
       'fresh-weak-colour-v2-n9-b3', 'fresh-near-fine-far-coarse-v2-n65-b3',
       'fresh-flat-v4-n5-b7', 'fresh-multiscale-gabor-v3-n5-b7']
BOXES = {
    'forked-filaments': [('fork-positive', [63,43,134,137])],
    'serrated-polygon': [('polygon-contact', [83,43,122,137])],
    'near-fine-far-coarse': [('thin-positive', [64,42,131,138])],
    'unclipped-glint': [('genuine-core', [79,75,104,99]), ('adjacent', [128,49,156,134]), ('spread', [103,71,117,112])],
    'clipped-glint': [('adjacent', [128,49,156,134]), ('spread', [103,71,117,112])],
    'weak-colour': [('colour-near', [43,36,110,144]), ('colour-far', [118,47,131,129])],
}


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b''):
            h.update(chunk)
    value = h.hexdigest()
    INPUTS[str(path)] = value
    return value


def load(path):
    sha(path)
    return json.loads(Path(path).read_text())


def array(root, row, np):
    root = Path(root).resolve()
    path = (root/row['file']).resolve()
    need(path.is_relative_to(root) and path.suffix == '.f32' and row['dtype'] == '<f4', 'owned f32 array required')
    need(path.stat().st_size == 4*math.prod(row['shape']) and sha(path) == row['sha256'], 'array shape/hash differs')
    value = np.memmap(path, dtype='<f4', mode='r', shape=tuple(row['shape']))
    need(bool(np.isfinite(value).all()), 'nonfinite array')
    return value


def dataset(path):
    path = Path(path).resolve()
    data = load(path)
    need(data['schema'] == 1 and data['split'] == 'heldout', 'fresh independent split only')
    paths = [(path.parent/p).resolve() for p in data['cases']]
    need([p.parent.name for p in paths] == IDS and len(set(paths)) == 10, 'fixed ten-case scope differs')
    need(all(p.is_relative_to(path.parent) and p.name == 'case.json' for p in paths), 'case outside held export')
    return paths


def read_case(path, np):
    meta = load(path)
    independent = load(path.parent/'independent-truth.json')
    label = independent['label']
    need(label['id'] == path.parent.name and label['training'] is False, 'fresh label differs')
    need(label['n'] == meta['source_count'] and label['bands'] == len(meta['level_sizes'])-1, 'source/level declaration differs')
    w,h = meta['level_sizes'][0]
    need(label['crop_quad_xywh'] == [8,8,w,h] and label['source_active_wh'] == [2*w+32,2*h+32], 'native origin/support differs')
    values = {key: array(path.parent, meta['arrays'][key], np) for key in ('canonical-rgb','uniform-rgb','truth-rgb')}
    values.update({key: array(path.parent, independent['templates'][key], np) for key in ('base','near','far')})
    need(all(v.shape == (2*h,2*w,3) for v in values.values()), 'truth/reference layout differs')
    # Different ordered f32 blur/add paths need not be bit-identical.
    decomposition = float(np.max(np.abs(values['truth-rgb']-(values['base']+values['near']+values['far']))))
    need(decomposition <= 1e-5, 'exported truth/component decomposition differs')
    return {'path': path, 'meta': meta, 'label': label, 'values': values,
            'decomposition_max_abs': decomposition}


def regions(case):
    label = case['label']; family = label['family']
    w,h = [2*v for v in case['meta']['level_sizes'][0]]
    rows = []
    if label['large']:
        rows.append({'name':'interior', 'xyxy':[w//4,h//4,3*w//4,3*h//4]})
        if family == 'multiscale-gabor':
            for j in range(8):
                cx=(w+32)*(.15+.23*(j%4))-16
                cy=(h+32)*(.30 if j<4 else .70)-16
                r=160 if j<4 else 300
                rows.append({'name':f'carrier-{j}', 'carrier':j,
                             'xyxy':[max(0,math.floor(cx-r)),max(0,math.floor(cy-r)),
                                     min(w,math.ceil(cx+r)),min(h,math.ceil(cy+r))]})
    else:
        if family != 'clipped-glint':
            rows.append({'name':'interior', 'xyxy':[14,14,146,130]})
        for name, box in BOXES.get(family, []):
            rows.append({'name':name, 'xyxy':[v-16 for v in box], 'source_native_xyxy':box})
    for row in rows:
        x0,y0,x1,y1=row['xyxy']
        need(0<=x0<x1<=w and 0<=y0<y1<=h, 'fixed score region incomplete')
    return rows


def crop(value, region, np):
    x0,y0,x1,y1=region['xyxy']
    return np.asarray(value[y0:y1,x0:x1], dtype=np.float64)


def carrier(case, region, j, np):
    x0,y0,x1,y1=region['xyxy']; w,h=case['label']['source_active_wh']
    yy,xx=np.mgrid[y0:y1,x0:x1].astype(np.float64)
    dx=xx+16-w*(.15+.23*(j%4)); dy=yy+16-h*(.30 if j<4 else .70)
    sigma=70. if j<4 else 170.
    omega=2*math.pi/(4*2**j); angle=.23*j+.11*case['label']['variant']
    wx,wy=omega*math.cos(angle),omega*math.sin(angle)
    ratio=sigma*sigma/(sigma*sigma+.7**2)
    envelope=ratio*np.exp(-.5*(dx*dx+dy*dy)/(sigma*sigma+.7**2)-.5*.7**2*ratio*(wx*wx+wy*wy))
    scalar=envelope*np.cos(ratio*(wx*dx+wy*dy)+.31*j)
    return scalar[...,None]*np.asarray([.040,.034,.044])


def scene(case, region, np):
    values=case['values']
    result={k:crop(values[k],region,np) for k in ('base','near','far')}
    result['truth']=crop(values['truth-rgb'],region,np)
    if 'carrier' in region:
        near=carrier(case,region,region['carrier'],np)
        reconstructed=sum((carrier(case,region,j,np) for j in range(8)), np.full_like(near,.25))
        delta=float(np.max(np.abs(reconstructed-result['truth'])))
        need(delta<=1e-5, 'independent analytic carrier truth differs')
        result.update(base=result['truth']-near, near=near, far=np.zeros_like(near),
                      analytic_truth_max_abs=delta)
    return result


def score(s, value, np):
    # Same centered two-component projection as the commissioned old checker.
    truth=s['truth'].reshape(-1,3); value=value.reshape(-1,3)
    e=value-truth; a=s['near'].reshape(-1,3); b=s['far'].reshape(-1,3)
    y=value-s['base'].reshape(-1,3)
    coefficients=[[None,None] for _ in range(3)]; sd=[]; conditions=[None]*3
    for c in range(3):
        ac,bc,yc=[v[:,c]-v[:,c].mean() for v in (a,b,y)]
        aa,ab,bb,ay,by=[float(np.dot(u,v)) for u,v in ((ac,ac),(ac,bc),(bc,bc),(ac,yc),(bc,yc))]
        sa,sb=math.sqrt(max(aa,0)/len(a)),math.sqrt(max(bb,0)/len(a)); sd.append([sa,sb])
        if sa>=.001 and sb>=.001:
            determinant=aa*bb-ab*ab
            if determinant/(aa*bb)>.05:
                coefficients[c]=[(ay*bb-by*ab)/determinant,(by*aa-ay*ab)/determinant]
                r=abs(ab/math.sqrt(aa*bb)); conditions[c]=(1+r)/(1-r)
        elif sa>=.001:
            coefficients[c][0],conditions[c]=ay/aa,1.
        elif sb>=.001:
            coefficients[c][1],conditions[c]=by/bb,1.
    return {'rgb_rmse':float(np.sqrt(np.mean(e*e))), 'green_rmse':float(np.sqrt(np.mean(e[:,1]**2))),
            'chroma_rmse':float(np.sqrt(np.mean(np.stack((e[:,0]-e[:,1],e[:,2]-e[:,1]))**2))),
            'near_far_coefficients':coefficients, 'template_sd':sd, 'standardized_condition':conditions}


def judgment(current, uniform, candidate, *, flat, positive):
    refs=[('current',current,1.10 if flat else 1.05)]
    if flat: refs.append(('uniform',uniform,1.10))
    failures=[f'{key}>{limit}*{name}' for name,ref,limit in refs for key in METRICS
              if candidate[key]>limit*ref[key]]
    eligible=[]; unqualified=[]
    for c in range(3):
        for d in range(2):
            reference=current['near_far_coefficients'][c][d]
            value=candidate['near_far_coefficients'][c][d]
            if reference is not None and reference>=.5:
                eligible.append([c,d])
                if value is None or min(1,max(0,value))<.9*min(1,reference):
                    failures.append(f'component-{c}-{d}<0.90*capped-current')
            else:
                unqualified.append([c,d])
    if positive and candidate['rgb_rmse']>.95*current['rgb_rmse']:
        failures.append('positive_RGB_improvement<0.05_current')
    return {'pass':not failures, 'failures':failures, 'eligible_components':eligible,
            'unqualified_components':unqualified,
            'ratios':{name:{k:candidate[k]/ref[k] if ref[k]!=0 else None for k in METRICS}
                      for name,ref in (('current',current),('uniform',uniform))}}


def required(case, region, current):
    family=case['label']['family']; pairs=[]; any_pair=False
    if family=='near-fine-far-coarse' and region['name']=='thin-positive': pairs=[(1,0),(1,1)]
    if family=='unclipped-glint' and region['name']=='genuine-core': pairs=[(1,1)]
    if family=='weak-colour' and region['name']=='colour-near': pairs=[(0,0),(2,0)]
    if 'carrier' in region:
        pairs=[(c,0) for c in range(3)]; any_pair=True
    statuses=[{'channel':c,'component':d,'qualified':current['near_far_coefficients'][c][d] is not None
               and current['near_far_coefficients'][c][d]>=.5} for c,d in pairs]
    passed=(any(r['qualified'] for r in statuses) if any_pair else all(r['qualified'] for r in statuses))
    return {'required':bool(pairs), 'any_channel_suffices':any_pair, 'components':statuses, 'qualified':passed}


def evaluate_case(case, candidate, np, qualify=False):
    rows=[]; flat=case['label']['family']=='flat'
    for region in regions(case):
        s=scene(case,region,np)
        current=score(s,crop(case['values']['canonical-rgb'],region,np),np)
        uniform=score(s,crop(case['values']['uniform-rgb'],region,np),np)
        value=s['truth'] if candidate is None else crop(candidate,region,np)
        judged=judgment(current,uniform,score(s,value,np),flat=flat,positive=region['name'].endswith('-positive'))
        row={**region,'current':current,'uniform':uniform,'candidate':score(s,value,np),'judgment':judged,
             'required_protection':required(case,region,current)}
        if 'analytic_truth_max_abs' in s: row['analytic_truth_max_abs']=s['analytic_truth_max_abs']
        if region['name'].endswith('-positive'):
            row['positive_qualified']=current['rgb_rmse']>0 and uniform['rgb_rmse']>=1.05*current['rgb_rmse']
        if qualify:
            need(judged['pass'], 'exact truth cannot pass fixed fresh score')
            mutants=[]
            if flat:
                rng=np.random.default_rng(0x58e431)
                mutants.append(('added-noise',s['truth']+.1*rng.standard_normal(s['truth'].shape)))
            protection=row['required_protection']
            if protection['required']:
                for component in sorted({p['component'] for p in protection['components'] if p['qualified']}):
                    mutants.append((f'erased-component-{component}',s['truth']-s[('near','far')[component]]))
            row['destroyers']=[]
            for name,mutant in mutants:
                delta=float(np.max(np.abs(mutant-s['truth'])))
                result=judgment(current,uniform,score(s,mutant,np),flat=flat,positive=False)
                need(delta>0 and not result['pass'], 'fresh protected destroyer not live/rejected')
                row['destroyers'].append({'name':name,'maximum_mutation':delta,'judgment':result})
        rows.append(row)
    return {'id':case['label']['id'],'family':case['label']['family'],'source_count':case['label']['n'],
            'bands':case['label']['bands'],'decomposition_max_abs':case['decomposition_max_abs'],
            'regions':rows,'pass':all(r['judgment']['pass'] for r in rows)}


def replay_prediction(path, record, declared, prediction_root, generic, model, np, torch):
    """Verify model -> all weights -> complete output before truth scoring."""
    need(record['case_sha256']==sha(path),'prediction case hash differs')
    native=generic.load_case(declared,np,torch)
    need(not native['truth_read'],'mechanical model replay read truth')
    for binding in native['bindings']:
        need(sha(binding['path'])==binding['sha256'],'replay input binding differs')
    bands=native['bands']; sizes=native['meta']['level_sizes']; n=native['meta']['source_count']
    need(set(record['arrays'])=={'cfa','rgb',*[f'weights-{k}' for k in range(bands)]},'prediction arrays differ')
    arrays={k:array(prediction_root,v,np) for k,v in record['arrays'].items()}
    need(arrays['cfa'].shape==(4,sizes[0][1],sizes[0][0])
         and arrays['rgb'].shape==(2*sizes[0][1],2*sizes[0][0],3),'prediction image shape differs')
    weights=[]; minima=[]
    for k,(w,h) in enumerate(sizes[:-1]):
        a=arrays[f'weights-{k}']
        need(a.shape==(n,h,w) and bool((a>0).all()) and bool((a<=2).all()),'invalid positive bounded weights')
        denominator=np.sum(a,axis=0,dtype=np.float32)
        need(bool(np.isfinite(denominator).all()) and float(denominator.min())>0,'invalid weight denominator')
        minima.append(float(denominator.min()))
        weights.append(torch.from_numpy(np.array(a,copy=True)))
    with torch.no_grad():
        inferred=generic.render(native,torch,mode='model',model=model,keep_weights=True)
        need(len(inferred['weights'])==bands and all(
            np.array_equal(value.cpu().numpy(),arrays[f'weights-{k}'])
            for k,value in enumerate(inferred['weights'])),
            'frozen model does not exactly reproduce every saved weight')
        need(np.array_equal(inferred['cfa'][0].cpu().numpy(),arrays['cfa'])
             and np.array_equal(inferred['rgb'][0].cpu().numpy(),arrays['rgb']),
             'frozen model does not exactly reproduce complete CFA/RGB')
        del inferred
        reconstructed=generic.reconstruct(native,weights,torch)
        need(np.array_equal(reconstructed['cfa'][0].cpu().numpy(),arrays['cfa'])
             and np.array_equal(reconstructed['rgb'][0].cpu().numpy(),arrays['rgb']),
             'saved weights do not exactly reconstruct complete output')
    return {'id':path.parent.name,'model_weights_exact':True,'model_complete_cfa_rgb_exact':True,
            'complete_cfa_rgb_exact':True,'all_boundary_pixels_included':True,
            'truth_read':False,'minimum_denominators':minima}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('qualify','check'))
    for arg in ('dataset','out'): parser.add_argument('--'+arg,type=Path,required=True)
    for arg in ('qualification','predictions','weights','commission'): parser.add_argument('--'+arg,type=Path)
    args=parser.parse_args()
    need(not args.out.exists(),'fresh checker output required'); args.out.mkdir()
    import numpy as np
    paths=dataset(args.dataset); plan_sha=sha(PLAN); checker_sha=sha(__file__)
    common={'schema':1,'dataset_sha256':sha(args.dataset),'plan_sha256':plan_sha,'checker_sha256':checker_sha,
            'known19_scores_separate':True,'fresh_case_count':10,'photographic_replay_admitted':False}
    rows=[]; replay=[]
    if args.phase=='check':
        need(all(p is not None for p in (args.qualification,args.predictions,args.weights,args.commission)), 'check requires qualification/predictions/model/native commission')
        q=load(args.qualification)
        need(q['status']=='FRESH_QUALIFICATION_COMPLETE' and q['dataset_sha256']==common['dataset_sha256']
             and q['plan_sha256']==plan_sha and q['checker_sha256']==checker_sha, 'qualification binding changed')
        predictions=load(args.predictions); model_sha=sha(args.weights)
        need(predictions['model_sha256']==model_sha and predictions['dataset_sha256']==common['dataset_sha256']
             and predictions['truth_read'] is False, 'frozen-model inference binding differs')
        records=predictions['records']; need(len(records)==10, 'fresh prediction coverage differs')
        by_path={Path(r['case']).resolve():r for r in records}
        need(set(by_path)==set(paths), 'fresh prediction case set differs')
        generic_sha=sha(GENERIC); commission=load(args.commission)
        need(commission['passed'] is True and commission['dataset_sha256']==common['dataset_sha256']
             and commission['source_sha256']==generic_sha and commission['saw_odd_seven'] is True,
             'generic native odd-seven commission absent/changed')
        need(predictions['generic_consumer_sha256']==generic_sha, 'inference generic consumer differs')
        spec=importlib.util.spec_from_file_location('independent_transfer_consumer',GENERIC)
        generic=importlib.util.module_from_spec(spec); spec.loader.exec_module(generic)
        helper,scorer=generic.imports(); _,torch=helper.runtime()
        model=scorer.load_model(args.weights,torch)
        declared={Path(d['path']).resolve():d for d in generic.declared_cases(args.dataset,'infer')}
        common.update(model_sha256=model_sha,predictions_sha256=sha(args.predictions),
                      qualification_sha256=sha(args.qualification),generic_native_commission_sha256=sha(args.commission))
        # All ten mechanical replays complete before any candidate quality score.
        for path in paths:
            replay.append(replay_prediction(path,by_path[path],declared[path],args.predictions.parent,
                                            generic,model,np,torch))
        need(sha(args.weights)==model_sha and sha(GENERIC)==generic_sha,'model/consumer changed during replay')
        del model
    # Flat controls precede every sharpness/detail judgment, including the large flat.
    ordered=sorted(paths,key=lambda p:(not p.parent.name.startswith('fresh-flat-'),IDS.index(p.parent.name)))
    for path in ordered:
        case=read_case(path,np); candidate=None
        if args.phase=='check':
            candidate=array(args.predictions.parent,by_path[path]['arrays']['rgb'],np)
        rows.append(evaluate_case(case,candidate,np,qualify=args.phase=='qualify'))
        del case,candidate
    required_rows=[[r['id'],w['name'],w['required_protection']] for r in rows for w in r['regions'] if w['required_protection']['required']]
    positive_rows=[[r['id'],w['name'],w['positive_qualified']] for r in rows for w in r['regions'] if 'positive_qualified' in w]
    need(len(required_rows)==11 and len(positive_rows)==2,'required protection/positive coverage changed')
    qualified=all(p['qualified'] for _,_,p in required_rows) and all(p for _,_,p in positive_rows)
    result={**common,'status':'FRESH_QUALIFICATION_COMPLETE' if args.phase=='qualify' else 'FRESH_SCREEN_COMPLETE',
            'mechanical_pass':True,'qualification_complete':True,'all_required_evidence_qualified':qualified,
            'required_protections':required_rows,'positive_qualification':positive_rows,'cases':rows,
            'all_prospective_scientific_guards_pass':None if args.phase=='qualify' else all(r['pass'] for r in rows),
            'weight_replay':replay}
    if args.phase=='check':
        need(result['required_protections']==q['required_protections'] and result['positive_qualification']==q['positive_qualification'], 'reference eligibility changed after qualification')
    result['inputs']=[{'path':p,'sha256':v} for p,v in sorted(INPUTS.items())]
    destination=args.out/('qualification.json' if args.phase=='qualify' else 'screen.json')
    with destination.open('x',encoding='utf-8') as handle: json.dump(result,handle,indent=2,allow_nan=False)


if __name__=='__main__':
    main()
