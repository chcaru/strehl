"""Revision-2 driver. Root executes; training never reads fresh held truth.

Warm-start the selected stage-1 model. Keep its architecture and Adam rate;
change chroma .5 to 2 globally and in the declared ROI term. Cost commissioning
does one complete43-case backward pass with NO optimizer update, large Gabor
first, plus a full evaluation. Full43 remains the only implemented fit schedule:
root must decide whether its measured cost is useful before launching training.
The600-second fit budget includes loading, preparation, evaluations and saves.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import time

HERE=Path(__file__).resolve().parent
OLD_DATASET=HERE.parent/'learned-band-guide/export-1/output/dataset.json'
OLD_DATASET_SHA='0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19'
GENERIC=HERE/'generic-consumer.py'
GENERIC_SHA='587e373f6d6afb81e120ca74c4c0094a86b1abd4a020724de38e1b4397ba8003'
FIT_SECONDS=600.
LEARNING_RATE=.001
ADAM_EPSILON=1e-8
CHECKPOINT_INTERVAL=32
MAX_STEPS=2048
LARGE_FIRST='train-multiscale-gabor-v0-n5-b7'
OLD_FLATS={'train-flat-0','train-flat-1','held-flat-n5','held-flat-n9'}
OLD_ROIS={
    'held-curved-bright-occlusion-n9':[[39,27,119,114]],
    'held-near-fine-far-coarse-n5':[[50,26,114,122]],
    'held-unclipped-point-glint-n5':[[61,57,84,80]],
    'held-weak-colour-dots-n5':[[33,27,120,112]],
    'held-clipped-point-glint-n5':[[111,33,140,118],[82,53,97,94]],
}


def need(ok,message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(8<<20),b''):
            h.update(block)
    return h.hexdigest()


def save(path,value):
    with Path(path).open('x',encoding='utf-8') as handle:
        json.dump(value,handle,indent=2,allow_nan=False)


def modules():
    need(sha(GENERIC)==GENERIC_SHA,'commissioned generic consumer changed')
    spec=importlib.util.spec_from_file_location('revision2_generic',GENERIC)
    generic=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generic)
    helper,scorer=generic.imports()
    return generic,helper,scorer


def runtime(helper):
    np,torch=helper.runtime()
    total=torch.cuda.get_device_properties(0).total_memory
    torch.cuda.set_per_process_memory_fraction(min(1.,(8<<30)/total))
    torch.cuda.reset_peak_memory_stats()
    return np,torch


def old_annotations(paths):
    expected={'train-flat-0','train-flat-1',
        *[f'train-single-depth-cosine-{i}' for i in range(4)],
        *[f'train-straight-checker-layers-{i}' for i in range(4)],
        'train-gaussian-blobs-0','train-gaussian-blobs-1',
        'held-flat-n5','held-flat-n9',*OLD_ROIS}
    need({p.parent.name for p in paths}==expected and len(paths)==19,'old19 identity differs')
    return {p.parent.name:{'id':p.parent.name,'native_shape':[144,160],
        'flat':p.parent.name in OLD_FLATS,
        'excluded_xyxy':[[61,57,84,80]] if p.parent.name=='held-clipped-point-glint-n5' else [],
        'roi_xyxy':OLD_ROIS.get(p.parent.name,[]),
        'coordinate_gauge':'output-native xyxy; exact stage1 known developer annotation'} for p in paths}


def masks(annotation,case,torch):
    w,h=case['meta']['level_sizes'][0]
    need(annotation['native_shape']==[2*h,2*w] and isinstance(annotation['flat'],bool),
         'annotation shape/flat type differs')
    valid=torch.ones((1,2*h,2*w),device='cuda',dtype=torch.float32)
    roi=torch.zeros_like(valid)
    def rectangle(row):
        need(len(row)==4 and all(isinstance(x,int) for x in row),'integer xyxy required')
        x0,y0,x1,y1=row
        need(0<=x0<x1<=2*w and 0<=y0<y1<=2*h,'annotation rectangle outside output-native image')
        return x0,y0,x1,y1
    for row in annotation['excluded_xyxy']:
        x0,y0,x1,y1=rectangle(row)
        valid[:,y0:y1,x0:x1]=0
    need(bool(valid.sum()>0),'no valid training target')
    regions=annotation['roi_xyxy']
    for row in regions:
        x0,y0,x1,y1=rectangle(row)
        region=torch.zeros_like(valid)
        region[:,y0:y1,x0:x1]=1
        region=region*valid
        need(bool(region.sum()>0),'ROI erased by target exclusion')
        roi=roi+region/(region.sum()*len(regions))
    need(bool((roi[valid==0]==0).all()),'ROI includes excluded target')
    return valid,roi,torch.tensor([float(annotation['flat'])],device='cuda')


def training_data(dataset,annotations,np,torch,generic,helper):
    # Split refusal occurs BEFORE any fresh case, annotation or tensor read.
    fresh=generic.declared_cases(dataset,'train')
    need(len(fresh)==24,'declared24 expanded training cases required')
    annotation_json=json.loads(Path(annotations).read_text())
    need(annotation_json['schema']==1 and annotation_json['split']=='training','training annotation scope')
    rows=annotation_json['cases']
    by_id={row['id']:row for row in rows}
    need(len(rows)==24 and len(by_id)==24 and set(by_id)=={Path(c['path']).parent.name for c in fresh},
         'missing/duplicate/extra annotation IDs')
    need(sha(OLD_DATASET)==OLD_DATASET_SHA,'known developer dataset changed')
    old=helper.manifest(OLD_DATASET)
    old_paths=old['training']+old['heldout']
    old_rows=old_annotations(old_paths)
    declared=[{'path':str(p),'split':'training','purpose':'train',
        'manifest':str(OLD_DATASET),'manifest_sha256':OLD_DATASET_SHA} for p in old_paths]+fresh
    cases=[]
    for spec in declared:
        case=generic.load_case(spec,np,torch)
        identity=Path(case['path']).parent.name
        annotation=(old_rows if identity in old_rows else by_id)[identity]
        valid,roi,flat=masks(annotation,case,torch)
        statistics=generic.prepare_statistics(case,torch)
        cases.append({'case':case,'id':identity,'annotation':annotation,'valid':valid,'roi':roi,
                      'flat':flat,'statistics':statistics})
    need(len(cases)==43 and len({c['id'] for c in cases})==43,'43 distinct training cases required')
    return cases


def objective(result,item,scorer,torch):
    rgb=result['rgb']
    truth=item['case']['arrays']['truth-rgb'][None].to(rgb.device)
    weights=[v[None].to(rgb.device) for v in result['weights']]
    old,parts=scorer.per_case_loss(rgb,truth,weights,item['flat'],torch,item['valid'],item['roi'])
    residual=rgb-truth
    chroma=torch.stack((residual[...,0]-residual[...,1],residual[...,2]-residual[...,1]),dim=-1)
    roi_chroma=(chroma.square().mean(-1)*item['roi']).flatten(1).sum(1)
    total=old+1.5*parts['chroma_mse']+.25*1.5*roi_chroma
    parts={**parts,'roi_chroma_mse':roi_chroma,
           'roi_rgb_chroma_mse':parts['roi_rgb_chroma_mse']+1.5*roi_chroma}
    need(bool(torch.isfinite(total).all()),'nonfinite revision2 objective')
    return total.mean(),parts


def parameter_hash(model):
    h=hashlib.sha256()
    for name,value in model.state_dict().items():
        h.update(name.encode('ascii'))
        h.update(value.detach().cpu().numpy().astype('<f4',copy=False).tobytes())
    return h.hexdigest()


def forward(item,model,generic,scorer,torch,backward):
    result=generic.render(item['case'],torch,mode='model',model=model,statistics=item['statistics'],
        keep_weights=True,gradients=backward,checkpoint_activations=backward)
    loss,parts=objective(result,item,scorer,torch)
    if backward:
        (loss/43).backward()
    values={key:float(value.detach()[0]) for key,value in parts.items()}
    row={'id':item['id'],'case':item['case']['path'],'case_sha256':item['case']['sha256'],
         'loss':float(loss.detach()),**values}
    del result,loss,parts
    return row


def evaluate(items,model,generic,scorer,torch):
    rows=[]
    with torch.no_grad():
        for item in items:
            rows.append(forward(item,model,generic,scorer,torch,False))
    return sum(row['loss'] for row in rows)/len(rows),rows


def cost(items,model,generic,scorer,torch,preparation_seconds):
    before=parameter_hash(model)
    ordered=sorted(enumerate(items),key=lambda p:(p[1]['id']!=LARGE_FIRST,p[0]))
    need(ordered[0][1]['id']==LARGE_FIRST,'fixed large Gabor commissioning case missing')
    model.zero_grad(set_to_none=True)
    torch.cuda.synchronize()
    start=time.perf_counter()
    rows=[]
    for _,item in ordered:
        torch.cuda.synchronize()
        now=time.perf_counter()
        row=forward(item,model,generic,scorer,torch,True)
        torch.cuda.synchronize()
        row['forward_backward_seconds']=time.perf_counter()-now
        row['peak_cuda_bytes']=torch.cuda.max_memory_allocated()
        rows.append(row)
        print(json.dumps({'cost_case':item['id'],'seconds':row['forward_backward_seconds'],
                          'peak_cuda_bytes':row['peak_cuda_bytes']}),flush=True)
    backward_seconds=time.perf_counter()-start
    need(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()),'gradient absent/nonfinite')
    head=float(model.head.weight.grad.abs().max()); body=float(model.conv1.weight.grad.abs().max())
    need(head>0 and body>0,'fixed warm model backward is not live')
    after=parameter_hash(model)
    need(before==after,'cost commissioning updated model parameters')
    model.zero_grad(set_to_none=True)
    torch.cuda.synchronize(); start=time.perf_counter()
    value,evaluation=evaluate(items,model,generic,scorer,torch)
    torch.cuda.synchronize(); evaluation_seconds=time.perf_counter()-start
    effective_step=backward_seconds+evaluation_seconds/CHECKPOINT_INTERVAL
    predicted=max(0,math.floor((FIT_SECONDS-preparation_seconds-evaluation_seconds-15)/effective_step))
    return {'schema':1,'passed':True,'status':'FULL43_COST_COMPLETE','complete_cases':43,
        'no_optimizer_update':True,'parameters_before_sha256':before,'parameters_after_sha256':after,
        'first_large_case':LARGE_FIRST,'preparation_seconds':preparation_seconds,
        'full43_forward_backward_seconds':backward_seconds,'full43_evaluation_seconds':evaluation_seconds,
        'projected_complete_updates_in600s':predicted,
        'projection_scope':'Derived from one measured pass; excludes optimizer/save jitter; not a fit or speed benchmark.',
        'schedule_approved':False,'root_schedule_decision_required':True,
        'maximum_head_gradient':head,'maximum_body_gradient':body,'initial_developer_score':value,
        'cases':rows,'evaluation':evaluation}


def fit(items,model,generic,scorer,torch,out,commission,started):
    optimizer=torch.optim.Adam(model.parameters(),lr=LEARNING_RATE,eps=ADAM_EPSILON)
    history=[]
    def checkpoint(step):
        value,rows=evaluate(items,model,generic,scorer,torch)
        path=out/f'checkpoint-{step:04}.json'
        save(path,scorer.model_record(model))
        record={'step':step,'score':value,'model':str(path),'model_sha256':sha(path),
                'cases':rows,'complete_fit_seconds':time.perf_counter()-started}
        history.append(record)
        print(json.dumps({'checkpoint':step,'developer_loss':value,'seconds':record['complete_fit_seconds']}),flush=True)
    checkpoint(0)
    step=0
    step_seconds=commission['full43_forward_backward_seconds']
    eval_seconds=commission['full43_evaluation_seconds']
    while step<MAX_STEPS and time.perf_counter()-started+1.25*(step_seconds+eval_seconds)+10<FIT_SECONDS:
        model.zero_grad(set_to_none=True)
        torch.cuda.synchronize(); now=time.perf_counter()
        for item in items:
            forward(item,model,generic,scorer,torch,True)
        need(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()),'training gradient nonfinite')
        optimizer.step()
        step+=1
        torch.cuda.synchronize()
        step_seconds=max(step_seconds,time.perf_counter()-now)
        need(time.perf_counter()-started<FIT_SECONDS,'complete600s fit bound exceeded')
        if step%CHECKPOINT_INTERVAL==0:
            now=time.perf_counter(); checkpoint(step)
            eval_seconds=max(eval_seconds,time.perf_counter()-now)
    need(step>0,'budget could not complete one declared full43 update')
    if history[-1]['step']!=step:
        checkpoint(step)
    best=min(history,key=lambda r:(r['score'],r['step']))
    with (out/'model.json').open('xb') as handle:
        handle.write(Path(best['model']).read_bytes())
    need(time.perf_counter()-started<FIT_SECONDS,'checkpoint/save exceeded complete600s bound')
    return {'status':'EXPANDED_DEVELOPER_FIT_COMPLETE','training_revision':2,'schedule':'full43',
        'steps':step,'maximum_steps':MAX_STEPS,'learning_rate':LEARNING_RATE,'adam_epsilon':ADAM_EPSILON,
        'optimizer_state':'new Adam moments; only model weights warm-started',
        'chroma_multiplier':2.,'roi_chroma_multiplier':2.,'complete_fit_seconds':time.perf_counter()-started,
        'fit_cap_seconds':FIT_SECONDS,'checkpoint_interval':CHECKPOINT_INTERVAL,
        'selection':'minimum complete training-only declared objective; earlier step wins ties',
        'chosen_step':best['step'],'chosen_score':best['score'],'initial_score':history[0]['score'],
        'history':history,'model_sha256':sha(out/'model.json'),'fresh_validation_read':False}


def main():
    started=time.perf_counter()
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['generic-commission','cost','train','infer'])
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--annotations',type=Path)
    parser.add_argument('--weights',type=Path)
    parser.add_argument('--commission',type=Path)
    parser.add_argument('--qualification',type=Path)
    parser.add_argument('--schedule',choices=['full43'])
    parser.add_argument('--require-odd-seven',action='store_true')
    args=parser.parse_args()
    generic,helper,scorer=modules()
    np,torch=runtime(helper)
    out=args.out.resolve()
    need(not out.exists(),'fresh output required')
    common={'schema':1,'training_revision':2,'source_sha256':sha(__file__),
        'generic_consumer_sha256':GENERIC_SHA,'consumer_sha256':generic.OLD_SHA,'scorer_sha256':generic.SCORER_SHA,
        'dataset':str(args.dataset.resolve()),'dataset_sha256':sha(args.dataset),
        'float32':True,'tf32':False,'deterministic':True,'seed':137,'gpu_budget_bytes':8<<30,
        'gpu_budget_scope':'expanded generated training/inference; not a production-memory claim',
        'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),'photographic_admission':False}
    if args.phase=='generic-commission':
        result=generic.commission(args.dataset,np,torch,out,require_odd_seven=args.require_odd_seven)
        need(result['passed'],'generic native parity refused')
    elif args.phase=='infer':
        need(args.weights is not None,'frozen model required')
        out.mkdir()
        model=scorer.load_model(args.weights,torch)
        records=[]; inputs=[]
        for i,spec in enumerate(generic.declared_cases(args.dataset,'infer')):
            case=generic.load_case(spec,np,torch)
            need(not case['truth_read'],'inference read truth')
            result=generic.render(case,torch,mode='model',model=model,keep_weights=True)
            records.append(generic.write_prediction(out/f'case-{i:02}',case,result,np))
            inputs.extend(case['bindings'])
            del case,result
        save(out/'predictions.json',{**common,'model':str(args.weights.resolve()),'model_sha256':sha(args.weights),
            'truth_read':False,'records':records,'input_tensor_bindings':inputs,
            'checkpoint_selection':False,'validation_result':False})
    else:
        need(args.weights is not None and args.annotations is not None,'explicit warm model and training annotations required')
        model=scorer.load_model(args.weights,torch)
        items=training_data(args.dataset,args.annotations,np,torch,generic,helper)
        out.mkdir()
        preparation_seconds=time.perf_counter()-started
        binding={**common,'warm_model':str(args.weights.resolve()),'warm_model_sha256':sha(args.weights),
            'annotations':str(args.annotations.resolve()),'annotations_sha256':sha(args.annotations),
            'old_dataset_sha256':OLD_DATASET_SHA,'old19_are_developer_cases':True,
            'training_cases':[{'id':item['id'],'case':item['case']['path'],'case_sha256':item['case']['sha256'],
                              'annotation':item['annotation']} for item in items],
            'input_tensor_bindings':[row for item in items for row in item['case']['bindings']],
            'fresh_validation_read':False}
        save(out/'training-inputs.json',binding)
        if args.phase=='cost':
            result=cost(items,model,generic,scorer,torch,preparation_seconds)
            save(out/'cost.json',{**binding,**result})
        else:
            need(args.schedule=='full43' and args.commission is not None and args.qualification is not None,
                 'root must explicitly choose full43 after measured cost and independent loss qualification')
            cp=args.commission if args.commission.is_file() else args.commission/'cost.json'
            control=json.loads(cp.read_text())
            qualified=json.loads(args.qualification.read_text())
            need(qualified['passed'] and qualified['source_sha256']==sha(__file__), 'independent loss/source qualification differs')
            need(control['passed'] and control['no_optimizer_update'] and control['complete_cases']==43,
                 'complete forward/backward cost commissioning required')
            for key in ('generic_consumer_sha256','scorer_sha256','dataset_sha256','annotations_sha256','warm_model_sha256'):
                need(control[key]==binding[key],f'cost binding differs: {key}')
            result=fit(items,model,generic,scorer,torch,out,control,started)
            save(out/'training.json',{**binding,'cost_sha256':sha(cp),'qualification_sha256':sha(args.qualification),**result})
    torch.cuda.synchronize()
    save(out/'completion.json',{**common,'phase':args.phase,'complete_seconds':time.perf_counter()-started,
        'peak_cuda_bytes':torch.cuda.max_memory_allocated(),'peak_cuda_reserved_bytes':torch.cuda.max_memory_reserved(),
        'completed':True})


if __name__=='__main__':
    main()
