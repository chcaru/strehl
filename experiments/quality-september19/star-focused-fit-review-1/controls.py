"""Independent nonidentity-local-anchor controls; generated CFA only."""
from pathlib import Path
import hashlib, importlib.util, json, sys, time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REG=ROOT/'experiments/quality-september14/local-green-translation.py'
EXPECTED='5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196'

def save(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def main():
    start=time.process_time()
    assert hashlib.sha256(REG.read_bytes()).hexdigest()==EXPECTED
    spec=importlib.util.spec_from_file_location('independent_nonidentity_anchor',REG)
    reg=importlib.util.module_from_spec(spec);sys.modules[spec.name]=reg;spec.loader.exec_module(reg)
    centre=complex(360,320);target_origin=(147,93)
    anchor_a=complex(1.014,.003);anchor_b=complex(1.8,-1.2);anchor_origin=(123,64)
    source_a=complex(.997,-.002);source_b=complex(-.65,.95);source_origin=(121,67)
    shape=(448,442);left,right=reg.grids()
    save('preregistration.json',dict(
        registrar_sha256=EXPECTED, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        criterion='Each known source-native residual recovered within 0.05 native px; anchor remains exact zero; wrong sign and doubled displacement worsen validation; ignoring nonidentity anchor must worsen validation.',
        failure_inputs='A registrar subtracting instead of adding source delta, converting source delta twice, treating the local anchor as identity, or using patch-local CFA phase can fail these controls.',
        finite_tolerance_native=.05, centre_native=[centre.real,centre.imag],target_origin_native=target_origin,
        anchor_a=[anchor_a.real,anchor_a.imag],anchor_b_plane=[anchor_b.real,anchor_b.imag],anchor_patch_origin=anchor_origin,
        source_a=[source_a.real,source_a.imag],source_b_plane=[source_b.real,source_b.imag],source_patch_origin=source_origin,
        source_shape=shape,fixture='Analytic continuous Fourier radiance sampled directly on each original CFA lattice, u16 quantization, different nuisance gain/bias, unrelated R/B. No image resampling creates the source samples.',
        scope='No original RAW reads; no map rebasing; no fitted intensity correction; not photographic or alignment-truth evidence on the owner stack.'))
    yy,xx=np.indices(shape)
    def generated(a,b,origin,delta,blur,gain,bias):
        sensor=xx+origin[0]+1j*(yy+origin[1])
        world=centre+(sensor-centre-2*b-complex(*delta))/a
        radiance=reg.continuous(world,blur)*np.float32(gain)+np.float32(bias)
        nongreen=(xx+origin[0]+yy+origin[1])%2==0
        radiance[nongreen]=np.float32(.85)+np.float32(.01)*np.sin(xx[nongreen])
        raw=np.rint(512+14848*radiance).astype(np.uint16)
        assert raw.max()<16383
        return reg.guide((raw.astype(np.float32)-np.float32(512))/np.float32(14848),origin,raw<16383)
    anchor=generated(anchor_a,anchor_b,anchor_origin,(0.,0.),0.,.94,.02)
    anchor_positions=[reg.mapped(p,target_origin,centre,anchor_a,anchor_b,anchor_origin) for p in (left,right)]
    reference=[reg.sample(anchor,p) for p in anchor_positions]
    self_result,_=reg.fit(anchor,*reference,*anchor_positions)
    assert self_result['converged'] and self_result['delta_source_native']==[0.0,0.0]
    assert self_result['before']['validation_rmse']<1e-12
    positions=[reg.mapped(p,target_origin,centre,source_a,source_b,source_origin) for p in (left,right)]
    wrong_anchor_positions=[reg.mapped(p,target_origin,centre,1+0j,0j,anchor_origin) for p in (left,right)]
    wrong_reference=[reg.sample(anchor,p) for p in wrong_anchor_positions]
    results=[]
    for label,known,blur in [('shift',(.61,-.43),0.),('shift-and-blur',(.61,-.43),.45),('blur-only',(0.,0.),.45)]:
        source=generated(source_a,source_b,source_origin,known,blur,1.05,.012)
        result,reading=reg.fit(source,*reference,*positions)
        error=float(np.linalg.norm(np.asarray(result['delta_source_native'])-known))
        assert result['converged'] and not result['at_translation_bound']
        assert result['after']['gain_positive'] and error<.05,(label,error,result)
        result.update(label=label,known_delta_source_native=known,error_native=error,tolerance_native=.05)
        if any(known):
            assert result['after']['validation_rmse']<result['before']['validation_rmse']
            wrong_sign=reading(-np.asarray(known));wrong_double=reading(2*np.asarray(known))
            assert wrong_sign['validation_rmse']>2*result['after']['validation_rmse']
            assert wrong_double['validation_rmse']>2*result['after']['validation_rmse']
            wrong_anchor,_=reg.fit(source,*wrong_reference,*positions)
            assert wrong_anchor['after']['validation_rmse']>2*result['after']['validation_rmse']
            assert np.linalg.norm(np.asarray(wrong_anchor['delta_source_native'])-known)>.05
            result.update(wrong_sign=wrong_sign,wrong_double=wrong_double,identity_anchor_placebo=wrong_anchor)
        results.append(result)
    save('result.json',dict(status='PASS',self_anchor=self_result,cases=results,cpu_seconds=time.process_time()-start))
    print(json.dumps(dict(status='PASS',errors_native=[r['error_native'] for r in results],
        after_validation=[r['after']['validation_rmse'] for r in results],anchor_delta=self_result['delta_source_native'])))

if __name__=='__main__':main()
