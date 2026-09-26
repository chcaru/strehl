"""Four-call composite contamination screen; root owns all inference."""
from pathlib import Path
import importlib.util
import json
import numpy as np
from scipy.special import ndtr

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('retained_raft_independent_controls',HERE.parent/'marigold-raft-translation/independent-controls.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
SHIFT=np.array([2.25,-1.75])
SOURCE_A=np.array([1.07,.012])


def staging_controls(area_rgb16):
    y,x=np.indices((8,12),dtype=np.uint16)
    image=np.stack([1000+16*x+128*y,2000+32*x+256*y,3000+48*x+384*y],axis=-1).astype(np.uint16)
    # Each mean is exactly integral; no ambiguous u16 half-tie convention.
    means=image.reshape(2,4,3,4,3).mean(axis=(1,3))
    assert np.array_equal(means[0,0],[1216,2432,3648])
    expected=means.astype(np.float32)/np.float32(65535)
    result=area_rgb16(image,(3,2))
    assert result.shape==(2,3,3) and result.dtype==np.float32
    assert np.array_equal(result,expected)
    constant=np.empty((8,12,3),np.uint16);constant[:]=[1024,2048,3072]
    flat=area_rgb16(constant,(3,2))
    assert np.array_equal(flat,np.broadcast_to(np.array([1024,2048,3072],np.float32)/np.float32(65535),(2,3,3)))
    assert not np.array_equal(expected[...,::-1],expected)  # channel-order destroyer is live
    return dict(passed=True,first_block_rgb16_mean=[1216,2432,3648],output_shape=list(result.shape),
        output_sha256=OLD.digest(result),constant_sha256=OLD.digest(flat),channel_destroyer_exercised=True,
        scope='Integer4x area/normalization arithmetic; not real noninteger staging or native-gather commissioning')


def window(distance):
    ramp=np.clip((128-np.abs(distance))/32,0,1)
    return .5-.5*np.cos(np.pi*ramp)


def step_area(t):
    sigma=.55
    def primitive(u):
        z=u/sigma
        return u*ndtr(z)+sigma*np.exp(-.5*z*z)/np.sqrt(2*np.pi)
    return primitive(t+.5)-primitive(t-.5)


def scene(shift=(0.,0.),contaminated=False):
    _,_,native,_=OLD.coordinates();points=native-np.array(shift)
    centre=OLD.INTERIOR[:2]+OLD.INTERIOR[2:]/2
    weight=window(points[...,0]-centre[0])*window(points[...,1]-centre[1])
    distance=(points[...,0]-centre[0])*OLD.SCALE[0]
    edge=step_area(distance)
    base=.5+.55*(OLD.texture(shift).astype(np.float64)-.5)+.18*weight[...,None]*(edge[...,None]-.5)
    if contaminated:
        ghost=step_area(distance-14*OLD.SCALE[0])
        base+=.18*.65*weight[...,None]*(ghost-edge)[...,None]
    assert np.isfinite(base).all() and np.min(base)>0 and np.max(base)<1
    return base.astype(np.float32),weight


def score(forward_admitted,reverse_admitted,forward_median,reverse_median,clean):
    errors=[float(np.linalg.norm(np.array(forward_median)-SHIFT)),float(np.linalg.norm(np.array(reverse_median)+SHIFT))]
    accurate=all(e<=.5 for e in errors)
    passed=(forward_admitted and reverse_admitted and accurate) if clean else ((not forward_admitted or errors[0]<=.5) and (not reverse_admitted or errors[1]<=.5))
    return bool(passed),errors


def run_controls(operator,model,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    clean,weight=scene();corrupt,_=scene(contaminated=True);source,_=scene(SHIFT)
    _,_,_,mask=OLD.coordinates();difference=np.abs(corrupt.astype(np.float64)-clean)
    live=dict(interior_rgb_rms=float(np.sqrt(np.mean(difference[mask]**2))),
        maximum=float(np.max(difference[mask])),
        fraction_changed_ge_001=float(np.mean(np.max(difference[mask],axis=1)>=.01)),
        unchanged_context_fraction=float(np.mean(weight[mask]==0)),
        unchanged_context_exact=bool(np.array_equal(corrupt[mask&(weight==0)],clean[mask&(weight==0)])))
    assert live['interior_rgb_rms']>=.005 and live['maximum']>=.05 and live['fraction_changed_ge_001']>=.02
    assert live['unchanged_context_fraction']>=.25 and live['unchanged_context_exact']
    # Explicitly reject no motion, always-refuse and an internally inverse ghost-following shortcut.
    assert not score(True,True,[0,0],[0,0],True)[0]
    assert not score(False,False,SHIFT,-SHIFT,True)[0]
    wrong=SHIFT-np.array([14.,0.])
    assert not score(True,True,wrong,-wrong,False)[0]
    results=[]
    for name,reference,is_clean in [('clean',clean,True),('contaminated',corrupt,False)]:
        forward=operator.infer_pair(model,reference,source)
        reverse=operator.infer_pair(model,source,reference)
        fj=OLD.judge_pair(forward,reverse,SOURCE_A)
        rj=OLD.judge_pair(reverse,forward,[1.,0.])  # destination is the composite output grid
        assert 'native_median' in fj and 'native_median' in rj
        passed,errors=score(fj['admitted'],rj['admitted'],fj['native_median'],rj['native_median'],is_clean)
        np.save(out/f'{name}-forward.npy',forward);np.save(out/f'{name}-reverse.npy',reverse)
        results.append(dict(name=name,passed=passed,forward_judge=fj,reverse_judge=rj,
            truth_output_native=SHIFT.tolist(),truth_source_native=[2.4285,-1.8455],truth_error_native=errors,
            inputs_sha256=[OLD.digest(reference),OLD.digest(source)],flows_sha256=[OLD.digest(forward),OLD.digest(reverse)]))
    receipt=dict(schema=1,mechanical_pass=True,passed=all(r['passed'] for r in results),
        inference_calls=4,cases=results,contamination=live,scoring_destroyers_exercised=True,
        actual_consumer_commissioned=False,photographic_quality_admitted=False,
        scope='Localized synthetic composite contamination; generated images bypass actual TIFF staging')
    (out/'controls.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return receipt
