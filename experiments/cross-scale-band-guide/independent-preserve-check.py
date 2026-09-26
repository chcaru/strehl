"""Independent local-contrast loss commissioning; root executes, training only."""
from pathlib import Path
import argparse
import importlib.util
import json
import math

HERE=Path(__file__).resolve().parent


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def direct(signal,target,valid,np):
    """f64, selected pixels explicitly mean-centered; no pooled moments/padding."""
    h,w=valid.shape; shape=(3,(h+15)//16,(w+15)//16)
    p=np.zeros(shape); v=np.zeros(shape); n=np.zeros((1,*shape[1:])); eligible=np.zeros(shape,bool)
    for iy,y in enumerate(range(0,h,16)):
        for ix,x in enumerate(range(0,w,16)):
            mask=valid[y:y+32,x:x+32].astype(bool)
            n[0,iy,ix]=mask.sum()
            if not mask.any(): continue
            t=target[y:y+32,x:x+32][mask].astype(np.float64)
            s=signal[y:y+32,x:x+32][mask].astype(np.float64)
            t-=t.mean(axis=0); s-=s.mean(axis=0)
            variance=np.mean(t*t,axis=0)
            v[:,iy,ix]=variance
            p[:,iy,ix]=np.mean(t*s,axis=0)/np.maximum(variance,1e-6)
            eligible[:,iy,ix]=(mask.sum()>=16)&(variance>=1e-6)
    return {'projection':p,'variance':v,'eligible':eligible,'valid_count':n}


def controls(subject,base,scorer,np,torch):
    def tensor(a): return torch.from_numpy(np.asarray(a,dtype=np.float32)).cuda()[None]
    def call(candidate,target,canonical,valid,flat=False):
        rgb,t,ref,v=map(tensor,(candidate,target,canonical,valid))
        flag=torch.tensor([float(flat)],device='cuda')
        penalty,parts=subject.contrast_preservation(rgb,t,ref,v,flag,torch)
        item={'case':{'arrays':{'truth-rgb':t[0]}},'valid':v,'roi':torch.zeros_like(v),
              'flat':flag,'canonical':ref}
        result={'rgb':rgb,'weights':[torch.ones((3,2,2),device='cuda') for _ in range(3)]}
        total,_=subject.objective(result,item,scorer,torch)
        previous,_=base.objective(result,item,scorer,torch)
        subject.need(abs(float(total)-float(previous)-float(penalty))<1e-9,'old objective/addition differs')
        return float(penalty),float(total),{k:float(v[0]) for k,v in parts.items()}
    h,w=40,48; y,x=np.mgrid[:h,:w]
    structure=np.cos(2*np.pi*x/8)[...,None]*np.array([.025,.035,.045])
    target=(.25+structure).astype(np.float32); valid=np.ones((h,w),np.float32)
    rows=[]
    # Flat first: added noise must not masquerade as preserved detail.
    constant=np.full_like(target,.25)
    noisy=constant+np.float32(.03)*np.cos(2*np.pi*y/8)[...,None].astype(np.float32)
    penalty,total,parts=call(noisy,constant,constant,valid,True)
    subject.need(penalty==0 and total>0,'flat noise control not live/blind as declared')
    rows.append({'name':'flat-noise','penalty':penalty,'complete_loss':total,'parts':parts})
    experiments=[('attenuation',.8,1.,4e-5),('subunit-equal',.65,.65,0.),
                 ('subunit-shortfall',.55,.65,1e-5),('capped-reference',1.,1.3,0.),
                 ('contrast-gain',1.25,1.,0.)]
    for name,gain,reference,expected in experiments:
        candidate=(.25+gain*structure).astype(np.float32)
        canonical=(.25+reference*structure).astype(np.float32)
        penalty,total,parts=call(candidate,target,canonical,valid)
        subject.need(math.isclose(penalty,expected,rel_tol=2e-5,abs_tol=2e-12),'known projection control differs: '+name)
        if name=='contrast-gain': subject.need(total>0,'absolute objective missed contrast gain')
        rows.append({'name':name,'penalty':penalty,'expected_penalty':expected,'complete_loss':total,'parts':parts})
    orthogonal=(target+.02*np.cos(2*np.pi*y/8)[...,None]).astype(np.float32)
    doubled=(.25+np.cos(2*np.pi*x/4)[...,None]*np.array([.025,.035,.045])).astype(np.float32)
    phase=(.25+np.sin(2*np.pi*x/8)[...,None]*np.array([.025,.035,.045])).astype(np.float32)
    for name,candidate,expected in [('orthogonal-noise',orthogonal,0.),
                                    ('doubled-frequency',doubled,.001),('quarter-phase',phase,.001)]:
        penalty,total,parts=call(candidate,target,target,valid)
        subject.need(math.isclose(penalty,expected,rel_tol=2e-5,abs_tol=2e-12) and total>0,'noise/phase control differs')
        rows.append({'name':name,'penalty':penalty,'expected_penalty':expected,'complete_loss':total,'parts':parts})
    # Odd partial windows and an excluded first address independently exercise
    # count normalization, valid anchors, clipping boundaries and cache parity.
    y,x=np.mgrid[:53,:47]
    t=(.21+.027*np.sin(.39*x+.21*y)[...,None]*np.array([1.,.7,1.3])).astype(np.float32)
    c=(.21+.73*(t-.21)+.003*np.cos(.25*x)[...,None]).astype(np.float32)
    ref=(.21+.91*(t-.21)).astype(np.float32)
    v=np.ones((53,47),np.float32); v[:4,:5]=0; v[18:39,20:37]=0; v[48:,32:]=0
    expected=direct(c,t,v,np); measured=subject.local_contrast_projection(tensor(c),tensor(t),tensor(v),torch)
    for key in ('projection','variance','valid_count'):
        actual=measured[key][0].cpu().numpy()
        subject.need(np.allclose(actual,expected[key],rtol=2e-5,atol=2e-7 if key=='projection' else 2e-10),
                     'independent masked centered reference differs: '+key)
    subject.need(np.array_equal(measured['eligible'][0].cpu().numpy(),expected['eligible']), 'independent eligibility differs')
    reference=direct(ref,t,v,np)
    eligible=expected['eligible']
    expected_loss=.001*np.mean(np.maximum(np.clip(reference['projection'],0,1)-expected['projection'],0)[eligible]**2)
    before,_,_=call(c,t,ref,v)
    subject.need(math.isclose(before,expected_loss,rel_tol=2e-5,abs_tol=1e-10),'direct lower-bound mean differs')
    changed=[a.copy() for a in (c,t,ref)]
    for i,a in enumerate(changed): a[v==0]=[37.,-19.,11.][i]
    after,_,_=call(*changed,v)
    subject.need(before==after,'excluded targets/canonical/candidate influence loss or rounding')
    live=c.copy(); live[4,5]+=[.07,-.08,.09]
    live_loss,_,_=call(live,t,ref,v)
    subject.need(live_loss!=before,'valid boundary mutation was not exercised')
    cached=subject.local_contrast_projection(tensor(ref),tensor(t),tensor(v),torch)
    penalty,_=subject.contrast_preservation(tensor(c),tensor(t),None,tensor(v),torch.zeros(1,device='cuda'),torch,reference=cached)
    subject.need(float(penalty[0])==before,'cached/direct training reference differs')
    # One below and one above each eligibility cutoff; no equality-rounding claim.
    eligibility=[]
    for count,sd in ((15,.01),(16,.01),(16,.0009),(16,.0011)):
        yy,xx=np.mgrid[:20,:20]; mask=np.zeros((20,20),np.float32); mask[0,:count]=1
        truth=(.25+sd*np.where(xx%2,1.,-1.)[...,None]*np.ones(3)).astype(np.float32)
        actual=subject.local_contrast_projection(tensor(truth),tensor(truth),tensor(mask),torch)
        qualified=bool(actual['eligible'][0,:,0,0].all())
        subject.need(qualified==(count==16 and sd>.001),'count/variance cutoff is not live')
        eligibility.append({'count':count,'sd':sd,'qualified':qualified})
    return {'analytic_controls':rows,'masked_f64_penalty':expected_loss,'masked_f32_penalty':before,
        'odd_native_shape':[53,47],'window_shape':measured['window_shape'],
        'excluded_all_three_images_invariant':True,'valid_boundary_live':True,
        'cached_reference_exact':True,'eligibility_controls':eligibility,
        'blind_directions':'Gain, DC bias and target-orthogonal noise can evade the one-sided projection term; complete image errors remain necessary.'}


def direction(subject,generic,scorer,specs,annotation,np,torch):
    spec,=[r for r in specs if Path(r['path']).parent.name=='train-weak-colour-v0-n17-b3']
    case=generic.load_case(spec,np,torch)
    row=case['meta']['arrays']['canonical-rgb']; path=Path(case['path']).parent/row['file']
    subject.need(subject.sha(path)==row['sha256'],'training canonical hash differs')
    canonical=torch.from_numpy(np.fromfile(path,dtype='<f4').reshape(row['shape'])).cuda()[None]
    valid,roi,flat=subject.masks(annotation,case,torch)
    with torch.no_grad():
        reference=subject.local_contrast_projection(canonical,case['arrays']['truth-rgb'].cuda()[None],valid,torch)
    item={'case':case,'valid':valid,'roi':roi,'flat':flat,'contrast_reference':reference}
    statistics=generic.prepare_statistics(case,torch)
    model=scorer.make_model(torch)
    with torch.no_grad():
        i=torch.arange(model.head.weight.numel(),device='cuda')
        model.head.weight.copy_((.017*torch.cos(.7*i+.3)).reshape_as(model.head.weight)); model.head.bias.fill_(-.011)
    def objective(backward):
        result=generic.render(case,torch,mode='model',model=model,statistics=statistics,
                              keep_weights=True,gradients=backward,checkpoint_activations=backward)
        return subject.objective(result,item,scorer,torch)
    value,parts=objective(True)
    contrast=float(parts['contrast_preservation_loss'][0])
    subject.need(contrast>0,'new preservation term inactive on fixed direction case')
    grad,=torch.autograd.grad(value,model.head.weight)
    norm=float(torch.linalg.vector_norm(grad)); subject.need(math.isfinite(norm) and norm>0,'gradient is not live')
    unit=grad/norm; saved=model.head.weight.detach().clone(); epsilon=.01
    with torch.no_grad():
        model.head.weight.copy_(saved-epsilon*unit); descent=float(objective(False)[0])
        model.head.weight.copy_(saved+epsilon*unit); ascent=float(objective(False)[0])
        model.head.weight.copy_(saved)
    fd=(ascent-descent)/(2*epsilon); relative=abs(fd-norm)/norm
    subject.need(relative<=.05 and descent<float(value)<ascent,'complete preservation objective derivative differs')
    return {'case':Path(case['path']).parent.name,'case_sha256':case['sha256'],'canonical_sha256':row['sha256'],
        'epsilon':epsilon,'direction':'unit full-head gradient, conditioning only','autograd':norm,
        'central_difference':fd,'relative_error':relative,'objective':float(value),'descent':descent,'ascent':ascent,
        'live_preservation_penalty':contrast}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('phase',choices=['qualify'])
    for name in ('dataset','annotations','out'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    subject=module(HERE/'preserve.py','independent_preserve_subject')
    base=module(HERE/'develop.py','independent_previous_objective')
    previous=module(HERE/'independent-develop-check.py','independent_known_support')
    sources=[HERE/'preserve.py',HERE/'develop.py',HERE/'independent-develop-check.py',Path(__file__),args.dataset,args.annotations]
    bindings={str(p.resolve()):subject.sha(p) for p in sources}
    generic,helper,scorer=subject.modules(); specs=generic.declared_cases(args.dataset,'train')
    annotations={r['id']:r for r in json.loads(args.annotations.read_text())['cases']}
    expected=previous.new_annotations(); subject.need(set(annotations)==set(expected),'fixed training annotations differ')
    old=helper.manifest(subject.OLD_DATASET); paths=old['training']+old['heldout']
    np,torch=subject.runtime(helper)
    support=previous.inspect_masks(subject,{**previous.old_annotations(paths),**expected},
        {**subject.old_annotations(paths),**annotations},np,torch)
    tests=controls(subject,base,scorer,np,torch)
    derivative=direction(subject,generic,scorer,specs,annotations['train-weak-colour-v0-n17-b3'],np,torch)
    subject.need(all(subject.sha(p)==value for p,value in bindings.items()),'bound source/data changed')
    subject.need(not args.out.exists(),'fresh output required'); args.out.mkdir()
    subject.save(args.out/'qualification.json',{'schema':1,'passed':True,
        'status':'INDEPENDENT_PRESERVATION_LOSS_QUALIFIED','source_sha256':subject.sha(HERE/'preserve.py'),
        'dataset_sha256':subject.sha(args.dataset),'annotations_sha256':subject.sha(args.annotations),
        'checker_sha256':subject.sha(__file__),'fixed_support':support,'controls':tests,'direction':derivative,
        'inputs':bindings,'fresh_validation_read':False,'photographic_admission':False,
        'limitation':'Mechanical loss qualification. Reused challenge scores are regressions, not a new independent validation.'})


if __name__=='__main__':
    main()
