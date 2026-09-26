"""Independent revision-2 loss qualification. Root runs; no held pixels are read.

Choice points: derive annotation support from scene construction, compare a
float64 boolean-indexed objective with the f32 training implementation, mutate
both sides of the clipped boundary, and differentiate along the complete head
gradient on the preselected new training colour case. This commissions training
mechanics, not photographic quality or independent validation.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
SUBJECT = HERE/'develop.py'
DIRECTION_CASE = 'train-weak-colour-v0-n17-b3'


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def new_annotations():
    """Independent fixed output-native support, chosen before any fit results."""
    rows = {}
    def add(identity, flat=False, roi=None, excluded=None, shape=(144,160)):
        rows[identity] = {'id':identity, 'native_shape':list(shape), 'flat':flat,
            'roi_xyxy':roi or [], 'excluded_xyxy':excluded or []}
    for v,n in enumerate((5,9,17,5)):
        add(f'train-flat-v{v}-n{n}-b3', flat=True)
    for family,count in (('natural-layers',10),('compound-texture',4)):
        for v in range(count):
            n = (5,9,17)[v%3] if family == 'natural-layers' else (5,9)[v%2]
            add(f'train-{family}-v{v}-n{n}-b3', roi=[[39,27,121,119]])
    add('train-unclipped-glint-v0-n9-b3', roi=[[59,55,82,79]])
    add('train-clipped-glint-v0-n9-b3', excluded=[[59,55,82,79]],
        roi=[[111,33,140,118],[81,53,96,96]])
    add(DIRECTION_CASE, roi=[[33,27,120,112]])
    add('train-near-fine-far-coarse-v0-n17-b3', roi=[[46,24,114,124]])
    add('train-flat-v4-n5-b7', flat=True, shape=(2048,2048))
    windows = []
    for j in range(8):
        cx = 2080*(.15+.23*(j%4))-16
        cy = 2080*(.30 if j<4 else .70)-16
        radius = 1.5*(70 if j<4 else 170)
        windows.append([math.floor(cx-radius),math.floor(cy-radius),
                        math.ceil(cx+radius),math.ceil(cy+radius)])
    add('train-multiscale-gabor-v0-n5-b7', roi=windows, shape=(2048,2048))
    return rows


def old_annotations(paths):
    # Previous independent commission fixed these source-native rectangles.
    source = {
        'held-curved-bright-occlusion-n9':[[55,43,135,130]],
        'held-near-fine-far-coarse-n5':[[66,42,130,138]],
        'held-unclipped-point-glint-n5':[[77,73,100,96]],
        'held-weak-colour-dots-n5':[[49,43,136,128]],
        'held-clipped-point-glint-n5':[[127,49,156,134],[98,69,113,110]],
    }
    result = {}
    for path in paths:
        identity = path.parent.name
        result[identity] = {'id':identity, 'native_shape':[144,160],
            'flat':'flat' in identity,
            'roi_xyxy':[[v-16 for v in r] for r in source.get(identity,[])],
            'excluded_xyxy':[[61,57,84,80]] if identity=='held-clipped-point-glint-n5' else []}
    return result


def expected_masks(annotation, np):
    h,w = annotation['native_shape']
    valid = np.ones((h,w), dtype=bool)
    for x0,y0,x1,y1 in annotation['excluded_xyxy']:
        valid[y0:y1,x0:x1] = False
    roi = np.zeros((h,w), dtype=np.float64)
    areas = []
    for x0,y0,x1,y1 in annotation['roi_xyxy']:
        region = np.zeros((h,w), dtype=bool)
        region[y0:y1,x0:x1] = True
        region &= valid
        areas.append(int(region.sum()))
        roi[region] += 1/(areas[-1]*len(annotation['roi_xyxy']))
    return valid,roi,areas


def inspect_masks(subject, expected, actual, np, torch):
    reports = []
    for identity,annotation in expected.items():
        found = actual[identity]
        subject.need(all(found[k] == v for k,v in annotation.items()),
                     f'construction annotation differs: {identity}')
        h,w = annotation['native_shape']
        case = {'meta':{'level_sizes':[[w//2,h//2]]}}
        valid,roi,flat = subject.masks(found,case,torch)
        v,r,areas = expected_masks(annotation,np)
        va,ra = valid[0].cpu().numpy(),roi[0].cpu().numpy()
        subject.need(np.array_equal(va,v),f'valid support differs: {identity}')
        subject.need(np.array_equal(ra>0,r>0) and np.allclose(ra,r,rtol=2e-7,atol=0),
                     f'equal-region normalization differs: {identity}')
        subject.need(float(flat[0]) == float(annotation['flat']), 'flat scope differs')
        reports.append({'id':identity,'excluded_pixels':int((~v).sum()),
            'roi_areas_after_exclusion':areas, 'roi_mass':float(ra.sum(dtype=np.float64)),
            'roi_max_abs_error':float(np.max(np.abs(ra-r)))})
    return reports


def independent_loss(error, weights, annotation, np):
    """Float64 boolean selection; no imported scorer/mask math."""
    e = error.astype(np.float64)
    valid,roi,_ = expected_masks(annotation,np)
    chroma = np.stack((e[...,0]-e[...,1],e[...,2]-e[...,1]),axis=-1)
    rgb = float(np.mean(e[valid]**2))
    colour = float(np.mean(chroma[valid]**2))
    dx,dy = np.diff(e[...,1],axis=1),np.diff(e[...,1],axis=0)
    gradient = .5*(np.mean(dx[valid[:,1:] & valid[:,:-1]]**2)
                    +np.mean(dy[valid[1:,:] & valid[:-1,:]]**2))
    roi_colour = float(np.sum(np.mean(chroma**2,axis=-1)*roi))
    roi_joint = float(np.sum((np.mean(e**2,axis=-1)+2*np.mean(chroma**2,axis=-1))*roi))
    kl = 0.
    if annotation['flat']:
        for weight in weights:
            p = weight.astype(np.float64)/weight.astype(np.float64).sum(axis=0,keepdims=True)
            kl += float(np.mean(np.sum(p*np.log(p*len(p)),axis=0)))/len(weights)
    parts = {'rgb_mse':rgb,'chroma_mse':colour,'green_gradient_mse':float(gradient),
        'flat_kl':kl,'roi_rgb_chroma_mse':roi_joint,'roi_chroma_mse':roi_colour}
    return rgb+2*colour+.25*gradient+.01*kl+.25*roi_joint,parts


def measured_loss(subject, scorer, annotation, error, weights, torch):
    h,w = annotation['native_shape']
    truth = torch.zeros((h,w,3),device='cuda')
    case = {'meta':{'level_sizes':[[w//2,h//2]]},'arrays':{'truth-rgb':truth}}
    valid,roi,flat = subject.masks(annotation,case,torch)
    result = {'rgb':torch.from_numpy(error).cuda()[None],
              'weights':[torch.from_numpy(v).cuda() for v in weights]}
    item = {'case':case,'valid':valid,'roi':roi,'flat':flat}
    total,parts = subject.objective(result,item,scorer,torch)
    return float(total),{key:float(value[0]) for key,value in parts.items()}


def loss_controls(subject, scorer, annotations, np, torch):
    ids = ['train-flat-v0-n5-b3','train-clipped-glint-v0-n9-b3',
           'train-unclipped-glint-v0-n9-b3',DIRECTION_CASE]
    y,x = np.mgrid[:144,:160]
    error = np.stack((.03*np.sin(.13*x+.19*y), .04*np.cos(.17*x-.11*y),
                     .02*np.sin(.23*y+.07*x)),axis=-1).astype(np.float32)
    weights = [np.broadcast_to(np.array([.4,1.,1.6],dtype=np.float32)[:,None,None],
                              (3,4,5)).copy() for _ in range(3)]
    reports = []
    for identity in ids:
        annotation = annotations[identity]
        expected,ep = independent_loss(error,weights,annotation,np)
        actual,ap = measured_loss(subject,scorer,annotation,error,weights,torch)
        for key in ep:
            subject.need(math.isclose(ap[key],ep[key],rel_tol=5e-6,abs_tol=1e-10),
                         f'independent objective component differs: {identity}/{key}')
        subject.need(math.isclose(actual,expected,rel_tol=5e-6,abs_tol=1e-10),
                     'independent complete objective differs')
        reports.append({'id':identity,'actual':actual,'independent':expected,
                        'components':ap,'maximum_component_error':max(abs(ep[k]-ap[k]) for k in ep)})
    uniform = [np.ones_like(v) for v in weights]
    points = [(59,55,'inside-corner',False),(81,78,'inside-opposite',False),
              (58,55,'outside-left',True),(82,78,'outside-right',True)]
    mutations = []
    for xx,yy,label,live in points:
        changed = np.zeros((144,160,3),dtype=np.float32)
        changed[yy,xx] = [.3,.8,-.2]
        clipped,_ = measured_loss(subject,scorer,annotations[ids[1]],changed,uniform,torch)
        genuine,_ = measured_loss(subject,scorer,annotations[ids[2]],changed,uniform,torch)
        subject.need((clipped>0) == live and genuine>0,'clipped boundary/genuine detail control differs')
        mutations.append({'point':[xx,yy],'kind':label,'clipped_loss':clipped,'genuine_loss':genuine})
    # An excluded-error destroyer must not alter any global, ROI or gradient term.
    changed = error.copy(); changed[55:79,59:82] += np.float32(1.7)
    before,_ = measured_loss(subject,scorer,annotations[ids[1]],error,uniform,torch)
    after,_ = measured_loss(subject,scorer,annotations[ids[1]],changed,uniform,torch)
    subject.need(before == after,'excluded target or crossing gradient leaks into objective')
    return {'float64_reference':reports,'boundary_mutations':mutations,
            'excluded_core_arbitrary_error_invariant':True,
            'failure_inputs':'Wrong chroma multiplier, pixel/edge denominator, ROI area weighting, clipped corner or crossing-stencil inclusion fail these comparisons.'}


def direction(subject, generic, helper, scorer, specs, annotations, np, torch):
    spec, = [s for s in specs if Path(s['path']).parent.name == DIRECTION_CASE]
    case = generic.load_case(spec,np,torch)
    subject.need(case['truth_read'] and spec['split']=='training','direction must use training only')
    valid,roi,flat = subject.masks(annotations[DIRECTION_CASE],case,torch)
    item = {'case':case,'valid':valid,'roi':roi,'flat':flat}
    statistics = generic.prepare_statistics(case,torch)
    model = scorer.make_model(torch)
    with torch.no_grad():
        indices = torch.arange(model.head.weight.numel(),device='cuda',dtype=torch.float32)
        model.head.weight.copy_((.017*torch.cos(.7*indices+.3)).reshape_as(model.head.weight))
        model.head.bias.fill_(-.011)
    def loss(backward):
        result = generic.render(case,torch,mode='model',model=model,statistics=statistics,
            keep_weights=True,gradients=backward,checkpoint_activations=backward)
        value,_ = subject.objective(result,item,scorer,torch)
        return value
    value = loss(True)
    grad, = torch.autograd.grad(value,model.head.weight)
    norm = float(torch.linalg.vector_norm(grad))
    subject.need(math.isfinite(norm) and norm>0,'complete-head direction is not live')
    unit = grad/norm
    saved = model.head.weight.detach().clone()
    epsilon = .01
    with torch.no_grad():
        model.head.weight.copy_(saved-epsilon*unit)
        descent = float(loss(False))
        model.head.weight.copy_(saved+epsilon*unit)
        ascent = float(loss(False))
        model.head.weight.copy_(saved)
    finite_difference = (ascent-descent)/(2*epsilon)
    relative = abs(finite_difference-norm)/norm
    subject.need(relative<=.05 and descent<float(value)<ascent,
                 'complete revision2 objective finite difference/descent/ascent failed')
    return {'case':DIRECTION_CASE,'case_sha256':case['sha256'],
        'direction':'unit full-head gradient; conditioning only, no case/quality selection',
        'epsilon':epsilon,'relative_tolerance':.05,'autograd':norm,
        'central_difference':finite_difference,'relative_error':relative,
        'objective':float(value),'descent':descent,'ascent':ascent,
        'source_inputs':case['bindings'],'fresh_validation_read':False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase',choices=['qualify'])
    parser.add_argument('--dataset',type=Path,required=True)
    parser.add_argument('--annotations',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    subject = module(SUBJECT,'independent_revision2_subject')
    binding = {'source_sha256':subject.sha(SUBJECT),'dataset_sha256':subject.sha(args.dataset),
        'annotations_sha256':subject.sha(args.annotations),'checker_sha256':subject.sha(__file__)}
    generic,helper,scorer = subject.modules()
    specs = generic.declared_cases(args.dataset,'train')
    annotations = json.loads(args.annotations.read_text())
    subject.need(annotations['schema']==1 and annotations['split']=='training', 'training annotation scope')
    actual = {row['id']:row for row in annotations['cases']}
    expected = new_annotations()
    subject.need(len(actual)==len(annotations['cases'])==24 and set(actual)==set(expected)
                 =={Path(s['path']).parent.name for s in specs},'training24 identity differs')
    subject.need(subject.sha(subject.OLD_DATASET)==subject.OLD_DATASET_SHA,'old developer data differs')
    old = helper.manifest(subject.OLD_DATASET)
    paths = old['training']+old['heldout']
    prior = old_annotations(paths)
    declared_prior = subject.old_annotations(paths)
    subject.need(len(prior)==19,'old19 coverage differs')
    np,torch = subject.runtime(helper)
    mask_report = inspect_masks(subject,{**prior,**expected},{**declared_prior,**actual},np,torch)
    # Flat/noise behavior is checked first within these independent loss controls.
    controls = loss_controls(subject,scorer,expected,np,torch)
    derivative = direction(subject,generic,helper,scorer,specs,expected,np,torch)
    for key,path in [('source_sha256',SUBJECT),('dataset_sha256',args.dataset),
                     ('annotations_sha256',args.annotations),('checker_sha256',Path(__file__))]:
        subject.need(subject.sha(path)==binding[key],f'qualification binding changed: {key}')
    result = {'schema':1,**binding,'passed':True,'status':'INDEPENDENT_REVISION2_LOSS_QUALIFIED',
        'generic_consumer_sha256':subject.GENERIC_SHA,'old_dataset_sha256':subject.OLD_DATASET_SHA,
        'all43_are_training_cases':True,'fresh_validation_read':False,'photographic_admission':False,
        'annotation_controls':mask_report,'loss_controls':controls,'direction':derivative,
        'limitation':'Loss/source commissioning only; native reconstruction, cost, fresh preservation and photographic evidence remain separate.'}
    subject.need(not args.out.exists(),'fresh qualification output required')
    args.out.mkdir()
    subject.save(args.out/'qualification.json',result)


if __name__=='__main__':
    main()
