"""Actual producer arrays against independently integrated scene predictions."""
import os
for key in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"]:
    os.environ[key]="2"
import importlib.util
import json
from pathlib import Path
import uuid
import numpy as np

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    producer=load("m194b_producer_independent_subject",HERE/"produce.py")
    integral=load("m194b_independent_integrals",HERE/"independent-optics.py")
    source_before=producer.bindings()
    scales=np.array([producer.P["geometry"]["scales"][0],1.,producer.P["geometry"]["scales"][-1]])
    focuses=np.array([0.,4.,8.])
    center=(157.,89.); width,height=288,192
    kwargs=dict(width=width,height=height,margin=48,phase_shift=.53,center=center,
                scales=scales,focuses=focuses,seed=90217,noise=True)
    work=HERE/"work"/("independent-producer-"+uuid.uuid4().hex[:10]); work.mkdir(parents=True)
    checks={}; rows={}
    original_function=producer.render.expose
    for mode in ["original","on","placebo"]:
        raw,expected,visits=producer.render_scalar("plane",supersample=4,observer=mode,**kwargs)
        assert producer.render.expose is original_function
        np.save(work/f"{mode}-raw.npy",raw,allow_pickle=False)
        rows[mode]=dict(raw_sha256=producer.array_sha(raw),visits=visits)
        if mode=="on":
            cached=expected
            on_raw=raw
            np.save(work/"on-expected.npy",expected,allow_pickle=False)
            checks["observer-all-indices"]=len(visits)==3 and expected.shape==(3,height,width)
        else:
            checks[f"{mode}-no-cache"]=expected is None
    checks["observer-three-mode-byte-identity"]=len({r["raw_sha256"] for r in rows.values()})==1
    checks["cached-exposure-reproduces-actual-noisy-raw"]=np.array_equal(producer.expose_cached(cached,seed=90217,noise=True),on_raw)
    try:
        with producer.observe_exposure("on"):
            raise RuntimeError("independent cleanup control")
    except RuntimeError: pass
    checks["observer-exception-restores"]=producer.render.expose is original_function
    noiseless=producer.expose_cached(cached,seed=90217,noise=False)
    checks["actual-noiseoff-quantization"]=np.array_equal(noiseless,np.rint(cached*.25+512).clip(0,15360).astype(np.uint16))
    _,cached8,_=producer.render_scalar("plane",supersample=8,observer="on",**dict(kwargs,noise=False))
    np.save(work/"s8-expected.npy",cached8,allow_pickle=False)
    y,x=np.indices((height,width),dtype=float)
    roi=(x>=48)&(x<240)&(y>=48)&(y<144)
    site_scale=np.ones((height,width)); site_scale[::2,::2]=.75; site_scale[1::2,1::2]=.6
    wb=np.ones((height,width)); wb[::2,::2]=float(np.float32(4/3)); wb[1::2,1::2]=float(np.float32(5/3))
    waves=[(1800.,1/16,1/24,.73),(900.,1/8,-1/16,1.63)]
    cutoff=5.12/(.535*16)
    def expected_field(scale,focus,S,wrong=None):
        c=center if wrong!="wrong-center" else (width/2,height/2)
        qx=c[0]+(x-c[0])/scale; qy=c[1]+(y-c[1])/scale
        if wrong=="wrong-inverse": qx=c[0]+(x-c[0])*scale; qy=c[1]+(y-c[1])*scale
        if wrong=="half-pixel-phase": qx+=.5; qy+=.5
        result=np.full((height,width),12000.)
        for amp,fx,fy,phase in waves:
            f=np.hypot(fx,fy)/scale
            transfer=integral.disc_cosine(f,1.5*abs(focus-4))*integral.pupil_overlap(f,cutoff)
            offsets=(np.arange(S)+.5)/S-.5
            if wrong=="point-aperture": aperture=1.
            else:
                pitch=2 if wrong=="quad-aperture" else 1
                aperture=sum(np.exp(2j*np.pi*(fx*i/scale+fy*j/scale)*pitch) for i in offsets for j in offsets)/(S*S)
            result+=amp*transfer*np.real(aperture*np.exp(1j*(2*np.pi*(fx*qx+fy*qy)+phase)))
        channels=site_scale.copy()
        if wrong=="swapped-CFA": channels[::2,::2]=.6; channels[1::2,1::2]=.75
        return result*channels
    agreement=[]; convergence=[]
    for k,(scale,focus) in enumerate(zip(scales,focuses)):
        predicted=expected_field(scale,focus,4)
        dn_error=(cached[k]-predicted)*.25*wb
        parity=[]
        for dy,dx in [(0,0),(0,1),(1,0),(1,1)]:
            parity_mask=roi[dy::2,dx::2]
            values=dn_error[dy::2,dx::2][parity_mask]
            parity.append(dict(rms_dn=float(np.sqrt(np.mean(values**2))),max_abs_dn=float(np.max(abs(values)))))
        agreement.append(dict(index=k,scale=float(scale),focus=float(focus),parity=parity))
        convergence.append(float(np.sqrt(np.mean(((cached8[k]-cached[k])*.25*wb)[roi]**2))))
    checks["actual-cached-scene-pupil-disc-cell-agreement"]=max(p["rms_dn"] for r in agreement for p in r["parity"])<=.5
    checks["rechosen-S4-S8-convergence"]=max(convergence)<=1
    negatives={}
    for wrong in ["wrong-center","wrong-inverse","half-pixel-phase","point-aperture","quad-aperture","swapped-CFA"]:
        errors=[float(np.sqrt(np.mean((((cached[k]-expected_field(s,f,4,wrong))*.25*wb)[roi])**2))) for k,(s,f) in enumerate(zip(scales,focuses))]
        negatives[wrong]=errors
        checks[f"reject-{wrong}"]=max(errors)>.5
    # Analytic RGB has its own continuous cell integration, no M25 optical
    # reference. Direct Gauss-Legendre quadrature supplies the expected colors.
    nodes,weights=np.polynomial.legendre.leggauss(16)
    color_scales=[scales[0],1.,scales[-1]]
    color_errors=[]
    for scale in color_scales:
        got=producer.analytic_color_rgb(width=width,height=height,scale=scale,center=center,phase_shift=-.46)
        qx=center[0]+(x-center[0])/scale; qy=center[1]+(y-center[1])/scale
        def color_wave(amp,fx,fy,phase):
            cell=sum(w1*w2*np.exp(2j*np.pi*(fx*z1/(2*scale)+fy*z2/(2*scale))) for z1,w1 in zip(nodes,weights) for z2,w2 in zip(nodes,weights))/4
            return amp*np.real(cell*np.exp(1j*(2*np.pi*(fx*qx+fy*qy)+phase-.46)))
        lum=3000+color_wave(450,.08,.03,.2)+color_wave(180,.19,-.07,1.1)
        chroma=color_wave(240,.11,.04,.8); green=color_wave(120,.05,-.09,2.)
        target=np.stack([lum+chroma,lum+green,lum-chroma],axis=-1)
        color_errors.append(float(np.max(abs(got-target))))
        assert np.ptp(chroma)>1 and np.ptp(green)>1
        # This also reads the producer's actual mosaicked pre-noise samples.
        e=producer.color_electrons(width=width,height=height,scales=[scale],center=center,phase_shift=-.46)[0]
        wanted=np.empty((height,width))
        wanted[::2,::2]=target[::2,::2,0]/(4/3)/.25
        wanted[::2,1::2]=target[::2,1::2,1]/.25
        wanted[1::2,::2]=target[1::2,::2,1]/.25
        wanted[1::2,1::2]=target[1::2,1::2,2]/(5/3)/.25
        checks[f"color-mosaic-{scale}"]=np.max(abs(e-wanted))<1e-8
    checks["actual-analytic-color-cell-quadrature"]=max(color_errors)<1e-8
    checks={k:bool(v) for k,v in checks.items()}
    source_after=producer.bindings()
    checks["sources-unchanged"]=source_before==source_after
    result=dict(schema="m194b-independent-producer-v1",pass_=all(checks.values()),checks=checks,
                source_before=source_before,source_after=source_after,rows=rows,agreement=agreement,
                s4_s8_rms_dn=convergence,negative_rms_dn=negatives,color_max_abs_dn=color_errors,
                arrays=[dict(path=str(p),sha256=producer.sha(p)) for p in sorted(work.glob("*.npy"))],
                scope="rechosen component producer arrays, not final consumer or benchmark admission")
    (HERE/"independent-producer.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(pass_=result["pass_"],checks=checks,agreement=agreement,convergence=convergence)))
    if not result["pass_"]: raise SystemExit(1)


if __name__=="__main__":main()
