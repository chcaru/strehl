"""Independent generated truth controls; callable before photographic CFA is read."""
import time
import numpy as np
from scipy.ndimage import map_coordinates

WAVES=((.065,.017,.023,.31),(.042,.039,-.011,1.27),(.038,-.052,.031,.83),(.024,.009,.057,2.11))
A=complex(1.0008,.0003)
B=complex(.13,-.09)
KNOWN=np.array([.43,-.57],dtype=np.float64)

def analytic(z,sx=0.,sy=None):
    """Continuous truth with exact separable Gaussian Fourier attenuation."""
    sy=sx if sy is None else sy
    v=np.full(z.shape,.41,dtype=np.float64)
    for amp,fx,fy,phase in WAVES:
        attenuation=np.exp(-2*np.pi*np.pi*(sx*sx*fx*fx+sy*sy*fy*fy))
        v+=amp*attenuation*np.cos(2*np.pi*(fx*z.real+fy*z.imag)+phase)
    return v.astype(np.float32)

def sample(image,xy):
    return map_coordinates(image,[xy[:,1],xy[:,0]],order=1,mode='nearest',prefilter=False).astype(np.float64)

def unpack(value):
    return value if isinstance(value,dict) else value[0]

def accepted(r):
    return bool(r['admitted'] and r['converged'] and not r['at_translation_bound'] and not r['refusal_reasons'])

def error(r):return float(r['after']['validation_rmse'])

def controls(model):
    started=time.perf_counter();yy,xx=np.mgrid[:392,:392];z=xx+1j*yy
    reference=analytic(z);centre=complex(196,196)
    # Independently verify actual global CFA phase, including an odd origin.
    for phase in (0,1):
        origin=(3,5)
        selected=((yy+origin[1])%2==phase)&((xx+origin[0])%2==1-phase)
        sabotaged=reference.copy();sabotaged[~selected]=np.float32(7.0)
        clean=model.guide(reference,origin=origin,phase=phase)
        bad=model.guide(sabotaged,origin=origin,phase=phase)
        assert np.array_equal(clean,bad),'nonselected CFA sites leak into phase-only guide'
        selected_bad=reference.copy();selected_bad[selected]+=np.float32(.1)
        assert np.max(np.abs(model.guide(selected_bad,origin=origin,phase=phase)-clean))>.09,'selected-phase control is inert'

    def run(label,known=(0.,0.),sigma=0.,phase=1,axis=1,joint=True,kind='normal'):
        train,test=model.grids(axis=axis,phase=phase)
        # Check target sampling phase independently of the grid implementation.
        for xy,p in ((train,phase),(test,1-phase)):
            assert np.all(xy[:,0]%2==1-p) and np.all(xy[:,1]%2==p),'grid phase mismatch'
        coords=[]
        for xy in (train,test):
            mapped=centre+A*(xy[:,0]+1j*xy[:,1]-centre)+2*B
            coords.append(np.column_stack((mapped.real,mapped.imag)))
        expected=np.asarray(known,dtype=float);world=centre+(z-centre-2*B-complex(*expected))/A
        truth=reference
        if kind=='flat':truth=np.full(reference.shape,.41,dtype=np.float32);source=truth.copy()
        elif kind=='edge':
            truth=(.41+.07*np.tanh((xx-191)/7)).astype(np.float32)
            # No rotation: the vertical-edge tangent must be wholly unidentifiable.
            coords=[train.copy(),test.copy()];source=truth.copy()
        elif kind=='one-sided':source=.75*analytic(world)+.25*analytic(world-1.2)
        elif kind=='anisotropic':source=analytic(world,.7,.2)
        else:source=analytic(world,sigma)
        source=source*np.float32(1.06)+np.float32(.017)
        targets=[sample(model.guide(truth,phase=p),xy) for p,xy in ((phase,train),(1-phase,test))]
        guides=[model.guide(source,phase=p) for p in (phase,1-phase)]
        try:
            r=unpack(model.fit(*guides,*targets,*coords,axis=axis,joint=joint,
                              probe_deltas=[-expected] if np.linalg.norm(expected)>0 else ()))
        except ValueError as exception:
            if kind not in ('flat','edge') or not str(exception).startswith('REFUSED:'):
                raise
            r=dict(admitted=False,converged=False,at_translation_bound=False,refusal_reasons=[str(exception)])
        return dict(label=label,phase=phase,split_axis=axis,known_delta_native=expected.tolist(),result=r)

    records=[]
    for name,known,sigma in [('translation',KNOWN,0.),('blur-only',(0.,0.),.45),('mixed',KNOWN,.45)]:
        ordinary=run(name+'-translation-model',known,sigma,joint=False)
        joint=run(name+'-joint-model',known,sigma,joint=True)
        for rec in (ordinary,joint):assert accepted(rec['result']),f"{rec['label']} did not converge/admit"
        r=joint['result'];distance=float(np.linalg.norm(np.asarray(r['delta_source_native'])-known))
        assert distance<.05,f'{name}: joint translation error {distance}'
        expected_beta=-.5*(abs(A)*sigma)**2
        assert abs(float(r['beta_source_native_squared'])-expected_beta)<.03,f'{name}: beta differs from independent Gaussian truth'
        joint.update(translation_error_native=distance,expected_beta=expected_beta)
        if sigma:
            assert error(r)<.75*error(ordinary['result']),f'{name}: blur term fails held-out power'
        else:
            assert error(r)<.2*float(r['before']['validation_rmse']),'correct translation does not improve held-out prediction'
        if np.linalg.norm(known)>0:
            wrong_error=float(r['probes'][0]['validation_rmse'])
            assert wrong_error>r['before']['validation_rmse'] and wrong_error>2*error(r),'wrong-sign evaluator lacks held-out power'
        records.extend([ordinary,joint])
    reciprocal=run('mixed-reciprocal-G1-left-right',KNOWN,.45,phase=0,axis=0)
    rr=reciprocal['result'];assert accepted(rr)
    assert np.linalg.norm(np.asarray(rr['delta_source_native'])-KNOWN)<.05
    assert abs(float(rr['beta_source_native_squared'])+.5*(abs(A)*.45)**2)<.03
    records.append(reciprocal)
    wrong=run('opposite-motion',-KNOWN,0.)
    wr=wrong['result'];assert accepted(wr)
    assert np.linalg.norm(np.asarray(wr['delta_source_native'])+KNOWN)<.05,'motion sign lacks power'
    assert np.linalg.norm(np.asarray(wr['delta_source_native'])-KNOWN)>1.,'opposite-motion control does not distinguish sign'
    records.append(wrong)
    for kind in ('flat','edge'):
        rec=run(kind+'-unidentifiable',kind=kind)
        assert not accepted(rec['result']),f'{kind}: arbitrary motion was admitted'
        records.append(rec)
    asymmetric=run('one-sided-PSF-not-geometric-motion',kind='one-sided')
    ar=asymmetric['result']
    assert np.linalg.norm(np.asarray(ar['delta_source_native']))>.1,'centroid ambiguity control was not exercised'
    asymmetric['interpretation']='No geometric motion planted; asymmetric PSF centroid mimics translation. This is deliberately not admitted as geometric motion.'
    asymmetric['geometric_motion_admitted']=False;records.append(asymmetric)
    anisotropic=run('anisotropic-PSF-outside-scalar-model',kind='anisotropic')
    anisotropic['interpretation']='Directional blur is outside the scalar Laplacian model regardless of a low fit residual.'
    anisotropic['geometric_motion_admitted']=False;records.append(anisotropic)
    elapsed=time.perf_counter()-started;assert elapsed<90,'generated control budget exceeded'
    return dict(status='INDEPENDENT_GENERATED_CONTROLS_PASS',seconds=elapsed,records=records,
        photographic_admission=False,scope='Independent analytic floating-CFA operator controls; not noise calibration or photographic quality.')
