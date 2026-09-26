"""Fixed independent estimator controls; root owns model intake and execution."""
from pathlib import Path
import hashlib
import json
import numpy as np

SHAPE=(586,880)
SCALE=np.array([880/6268,586/4176],dtype=np.float64)
INTERIOR=np.array([3258.,3028.,328.,328.])


def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def coordinates():
    yy,xx=np.indices(SHAPE,dtype=np.float64)
    native=np.stack(((xx+.5)/SCALE[0]-.5,(yy+.5)/SCALE[1]-.5),axis=-1)
    mask=np.all((native>=INTERIOR[:2])&(native<INTERIOR[:2]+INTERIOR[2:]),axis=-1)
    return xx,yy,native,mask


def stats(flow,native,mask):
    values=flow.astype(np.float64)/SCALE
    median=np.median(values[mask],axis=0)
    spread=float(np.quantile(np.linalg.norm(values[mask]-median,axis=1),.9))
    mid=INTERIOR[:2]+INTERIOR[2:]/2
    quadrants=[]
    for bottom in (False,True):
        for right in (False,True):
            part=mask&((native[...,0]>=mid[0])==right)&((native[...,1]>=mid[1])==bottom)
            assert np.count_nonzero(part)>0
            quadrants.append(np.median(values[part],axis=0))
    q=np.array(quadrants)
    separation=float(np.max(np.linalg.norm(q[:,None,:]-q[None,:,:],axis=-1)))
    return median,dict(p90_deviation_native=spread,quadrant_medians_native=q.tolist(),quadrant_max_distance_native=separation)


def judge_pair(forward,backward,source_a):
    """Same fixed judge for controls and all eight photographic pairs."""
    assert forward.shape==backward.shape==(*SHAPE,2)
    assert np.asarray(source_a).shape==(2,)
    if not (np.isfinite(forward).all() and np.isfinite(backward).all() and np.isfinite(source_a).all()):
        return dict(admitted=False,reasons=['nonfinite_flow_or_similarity'])
    xx,yy,native,mask=coordinates()
    fm,fs=stats(forward,native,mask);bm,bs=stats(backward,native,mask)
    ar,ai=source_a
    source=np.array([ar*fm[0]-ai*fm[1],ai*fm[0]+ar*fm[1]])
    x=xx[mask]+forward[...,0][mask];y=yy[mask]+forward[...,1][mask]
    covered=bool(np.all((x>=0)&(x<SHAPE[1]-1)&(y>=0)&(y<SHAPE[0]-1)))
    cycle=None
    if covered:
        ix=np.floor(x).astype(int);iy=np.floor(y).astype(int)
        fx=(x-ix)[:,None];fy=(y-iy)[:,None]
        reverse=(1-fy)*((1-fx)*backward[iy,ix]+fx*backward[iy,ix+1])+fy*((1-fx)*backward[iy+1,ix]+fx*backward[iy+1,ix+1])
        cycle=float(np.quantile(np.linalg.norm((forward[mask]+reverse)/SCALE,axis=1),.9))
    closure=float(np.linalg.norm(fm+bm));reasons=[]
    if np.linalg.norm(source)>=4:reasons.append('source_translation_bound')
    if max(fs['p90_deviation_native'],bs['p90_deviation_native'])>.75:reasons.append('within_field_spread')
    if max(fs['quadrant_max_distance_native'],bs['quadrant_max_distance_native'])>.75:reasons.append('quadrant_disagreement')
    if closure>.5:reasons.append('median_forward_backward_closure')
    if not covered or cycle>.75:reasons.append('sampled_forward_backward_cycle')
    return dict(admitted=not reasons,reasons=reasons,native_median=fm.tolist(),
        reverse_native_median=bm.tolist(),source_native_translation=source.tolist(),
        forward=fs,reverse=bs,median_closure_native=closure,cycle_p90_native=cycle,
        reverse_sample_coverage=covered,interior_count=int(np.count_nonzero(mask)))


def texture(shift=(0.,0.),blur=0.,seed=5813):
    """Independent analytic translation and blur, without image resampling."""
    rng=np.random.default_rng(seed);yy,xx=np.indices(SHAPE,dtype=np.float64)
    x=xx-shift[0]*SCALE[0];y=yy-shift[1]*SCALE[1]
    rgb=np.full((*SHAPE,3),.5,dtype=np.float64)
    for i in range(48):
        frequency=np.exp(rng.uniform(np.log(.008),np.log(.18)))
        angle=rng.uniform(0,2*np.pi);fx=frequency*np.cos(angle);fy=frequency*np.sin(angle)
        phases=rng.uniform(0,2*np.pi,3)
        amplitude=.008*np.exp(-2*np.pi**2*blur**2*frequency**2)
        wave=2*np.pi*(fx*x+fy*y)
        for c in range(3):rgb[...,c]+=amplitude*np.cos(wave+phases[c])
    assert np.min(rgb)>0 and np.max(rgb)<1
    return rgb.astype(np.float32)


def address_controls(operator):
    # Literal dyadic examples, independent of photographic fit and model output.
    points=np.array([[3134.,2088.],[3234.,2288.]])
    identity=operator.mapped_source(points,[1.,0.,0.,0.])
    shifted=operator.mapped_source(points,[1.125,.03125,3.,-4.])
    assert np.array_equal(identity,np.array([[3516.,2344.],[3616.,2544.]]))
    assert np.array_equal(shifted,np.array([[3522.,2336.],[3628.25,2564.125]]))
    flow=np.empty((*SHAPE,2),np.float32);flow[:]=np.array([2.25,-1.75])*SCALE
    reduced=operator.reduce_flow(flow,[1.07,.012])
    assert np.allclose(reduced['source_native_translation'],[2.4285,-1.8455],rtol=0,atol=2e-6)
    return dict(passed=True,identity_native=identity.tolist(),nonidentity_native=shifted.tolist(),
        expected_source_vector=[2.4285,-1.8455],observed_source_vector=reduced['source_native_translation'],
        scope='Coordinate/vector arithmetic only; not TIFF filtering/remap or native-gather commissioning')


def run_controls(operator,model,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    addresses=address_controls(operator)
    shift=np.array([2.25,-1.75]);a=np.array([1.07,.012])
    sharp=texture();translated=texture(shift);blurred=texture(blur=1.5)
    rng=np.random.default_rng(73159)
    flat0=(.45+rng.normal(0,.01,(*SHAPE,3))).astype(np.float32)
    flat1=(.45+rng.normal(0,.01,(*SHAPE,3))).astype(np.float32)
    xx,yy,native,mask=coordinates();mid=INTERIOR[0]+INTERIOR[2]/2
    right=native[...,0]>=mid
    depth0=np.where(right[...,None],texture(seed=8173),sharp)
    depth1=np.where(right[...,None],texture((-2.5,0),seed=8173),texture((2.5,0)))
    cases=[('flat_noise',flat0,flat1),('fractional',sharp,translated),('static_defocus',sharp,blurred),('two_depths',depth0,depth1)]
    results=[]
    for name,reference,source in cases:
        flow=operator.infer_pair(model,reference,source)
        back=operator.infer_pair(model,source,reference)
        assert flow.dtype==back.dtype==np.float32
        result=judge_pair(flow,back,a)
        reduction=operator.reduce_flow(flow,a)
        if 'native_median' in result:
            assert np.allclose(reduction['native_median'],result['native_median'],rtol=0,atol=1e-6)
            assert np.allclose(reduction['source_native_translation'],result['source_native_translation'],rtol=0,atol=1e-6)
            assert reduction['interior_count']==result['interior_count']
        extra={}
        if name=='fractional':
            valid='native_median' in result
            errors=[float(np.linalg.norm(np.array(result['native_median'])-shift)),float(np.linalg.norm(np.array(result['reverse_native_median'])+shift))] if valid else [None,None]
            # Independently reverse the judge to require admission in both directions.
            reverse_judge=judge_pair(back,flow,a)
            passed=bool(valid and result['admitted'] and reverse_judge['admitted'] and max(errors)<=.5)
            extra=dict(truth_output_native=shift.tolist(),truth_source_native=[2.4285,-1.8455],
                source_vector_error_native=float(np.linalg.norm(np.array(result['source_native_translation'])-np.array([2.4285,-1.8455]))) if valid else None,
                truth_error_native=errors,reverse_admitted=reverse_judge['admitted'])
        elif name in ('static_defocus','flat_noise'):
            # A refused estimate is safe for this null; an admitted false shift is not.
            reverse_judge=judge_pair(back,flow,a)
            false_move=max(float(np.linalg.norm(result['source_native_translation'])),float(np.linalg.norm(reverse_judge['source_native_translation']))) if 'native_median' in result else None
            passed=bool((not result['admitted'] and not reverse_judge['admitted']) or (false_move is not None and false_move<=.25))
            extra=dict(false_movement_native=false_move,reverse_admitted=reverse_judge['admitted'],flat_registration_information_claim=False)
        else:
            parts=[mask&(native[...,0]<mid-16),mask&(native[...,0]>=mid+16)]
            medians=[np.median((flow.astype(np.float64)/SCALE)[part],axis=0) for part in parts]
            truth=[np.array([2.5,0.]),np.array([-2.5,0.])]
            errors=[float(np.linalg.norm(m-t)) for m,t in zip(medians,truth)]
            exercised=bool(np.isfinite(errors).all() and max(errors)<=.75)
            passed=bool(not result['admitted'] and exercised)
            extra=dict(half_truth_native=[v.tolist() for v in truth],half_medians_native=[v.tolist() for v in medians],half_error_native=errors,mixed_motion_exercised=exercised)
        stem=name.replace('_','-')
        np.save(out/f'{stem}-forward.npy',flow);np.save(out/f'{stem}-reverse.npy',back)
        results.append(dict(name=name,passed=passed,input_hashes=[digest(reference),digest(source)],
            flow_hashes=[digest(flow),digest(back)],judge=result,**extra))
    receipt=dict(schema=1,mechanical_pass=True,address_controls=addresses,passed=all(row['passed'] for row in results),
        controls_pass=all(row['passed'] for row in results),inference_calls=8,cases=results,
        photographic_quality_admitted=False,actual_consumer_commissioned=False,
        scope='Generated880x586 inputs bypass actual TIFF INTER_AREA/map staging; no staging/native-gather, RAW calibration or photographic-truth claim')
    (out/'controls.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return receipt
