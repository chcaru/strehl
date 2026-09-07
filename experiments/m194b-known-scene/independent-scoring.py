"""Re-choose scorer inputs and integrate analytic targets independently."""
import importlib.util
import json
import math
from pathlib import Path
import uuid
import numpy as np
from scipy.ndimage import gaussian_filter
import tifffile

HERE=Path(__file__).resolve().parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def main():
    score=module("m194b_score",HERE/"score.py")
    independent=module("m194b_independent_integrals",HERE/"independent-optics.py")
    initial_hash=score.sha256(HERE/"score.py")
    y,x=np.indices((136,255),dtype=float); x+=18; y+=30
    mask=((x.astype(int)+3*y.astype(int))%5!=0)
    theta=2*np.pi*(x/17+y/8)
    phases=np.array([.73,-.46,1.27]); amplitudes=np.array([191.,283.,137.])
    truth=2400+amplitudes*np.cos(theta[...,None]+phases)
    result={}; checks={}
    noop=score.error(truth.copy(),truth,mask)
    checks["copy-noop"]=max(noop["mse_dn2"])==0
    shifted=truth+np.array([20.,-20.,0.])
    delta=score.error(shifted,truth,mask)
    assert np.allclose(delta["bias_dn"],[20,-20,0],rtol=0,atol=1e-10)
    assert np.allclose(delta["mse_dn2"],[400,400,0],rtol=0,atol=1e-8)
    checks["signed-known-offset"]=True
    swap=score.error(truth[...,::-1],truth,mask)
    checks["spatial-color-swap"]=min(np.array(swap["mse_dn2"])[[0,2]])>1
    response=score.wave_response(truth,x,y,mask,[(1/17,1/8)])
    assert np.allclose(response["waves"][0]["amplitude_dn"],amplitudes,atol=1e-8)
    assert np.allclose(response["waves"][0]["phase_rad"],phases,atol=1e-10)
    checks["independent-phase-and-amplitude"]=True
    # Apply a real finite spatial kernel, rather than manufacture attenuation
    # with the analytic response formula being checked.
    blurred=gaussian_filter(truth,sigma=(.6,.6,0),mode="wrap")
    blur_response=score.wave_response(blurred,x,y,mask,[(1/17,1/8)])
    q=np.arange(-2,3); kernel=np.exp(-q*q/(2*.6**2)); kernel/=kernel.sum()
    transfer=float(np.dot(kernel,np.cos(2*np.pi*q/17))*np.dot(kernel,np.cos(2*np.pi*q/8)))
    assert np.allclose(blur_response["waves"][0]["amplitude_dn"],amplitudes*transfer,atol=1e-8)
    checks["actual-spatial-blur"]=min(score.error(blurred,truth,mask)["mse_dn2"])>1
    flat=np.full_like(truth,2400.)
    checks["flat-spatial-blur-placebo"]=np.max(abs(gaussian_filter(flat,sigma=(.6,.6,0),mode="wrap")-flat))<1e-10
    # Explicit seven-repeat construction gives closed elementary expectations,
    # unlike another call to variance() on the author's random sample.
    a=np.array([.5,2.,4.]); b=np.array([0.,13.,-7.])
    stack=truth[None]+b+np.arange(-3,4)[:,None,None,None]*a
    temporal=score.repeat_error(stack,truth,mask)
    expected_v=(28/6)*a*a
    expected_mse=b*b+4*a*a
    assert np.allclose(temporal["temporal_variance_dn2"],expected_v,atol=1e-9)
    assert np.allclose(temporal["mse_mean_dn2"],expected_mse,atol=1e-8)
    assert np.allclose(temporal["unclipped_squared_bias_estimate_dn2"],b*b-expected_v/7,atol=1e-8)
    assert temporal["unclipped_squared_bias_estimate_dn2"][0]<0
    checks["seven-repeat-closed-moments-and-negative-correction"]=True
    stable=score.repeat_error(np.repeat(truth[None],7,axis=0),truth,mask)
    checks["structured-signal-not-temporal-noise"]=max(stable["temporal_variance_dn2"])<1e-20
    # Score the frozen target conventions against independent pupil geometry
    # and direct cell quadrature. Use a small off-origin grid, not its own ROI.
    sy,sx=np.indices((13,19),dtype=float); sx+=71; sy+=89
    gx,gw=np.polynomial.legendre.leggauss(32)
    ideal=np.full(sx.shape,12000.); observation=np.full(sx.shape,12000.)
    for amp,fx,fy,phase in [(1800.,1/16,1/24,.2),(900.,1/8,-1/16,1.1)]:
        # Direct weighted integration of the complex cell wave; it does not
        # use scorer sinc() or its product of cosine means.
        integration=sum(w1*w2*np.exp(2j*np.pi*(fx*z1/2+fy*z2/2))
                        for z1,w1 in zip(gx,gw) for z2,w2 in zip(gx,gw))/4
        carrier=np.exp(1j*(2*np.pi*(fx*sx+fy*sy)+phase))
        ideal+=amp*(carrier*integration).real
        finite=sum(np.exp(2j*np.pi*(fx*((i+.5)/4-.5)+fy*((j+.5)/4-.5)))
                   for i in range(4) for j in range(4))/16
        pupil=independent.pupil_overlap(math.hypot(fx,fy),5.12/(.535*16))
        observation+=amp*(carrier*finite*pupil).real
    factor=.25*np.array([.75*float(np.float32(4/3)),1.,.6*float(np.float32(5/3))],dtype=float)
    expected_ideal=ideal[...,None]*factor
    expected_obs=observation[...,None]*factor
    assert np.max(abs(score.target("plane",sx,sy,"ideal")-expected_ideal))<1e-8
    assert np.max(abs(score.target("plane",sx,sy,"observation")-expected_obs))<1e-4
    assert np.max(abs(expected_ideal-expected_obs))>10
    checks["independent-cell-and-pupil-targets"]=True
    # TIFF mutations exercise the decoder, declared fixed DN conversion and
    # distinct file versus pixel identities; no arbitrary file metadata drives
    # a target or command in this component test.
    work=HERE/"work"/("independent-scorer-"+uuid.uuid4().hex[:10]); work.mkdir(parents=True)
    pixels=np.rint(truth*65535/14848).astype(np.uint16)
    for name,software,data in [("base","independent-M194b-A",pixels),
                               ("metadata","independent-M194b-B",pixels),
                               ("copied","independent-M194b-A",pixels.copy())]:
        tifffile.imwrite(work/f"{name}.tif",data,photometric="rgb",metadata=None,software=software,description=score.CAMERA_LINEAR_DESCRIPTION)
    altered=pixels.copy(); altered[70,101,0]+=17
    tifffile.imwrite(work/"pixel.tif",altered,photometric="rgb",metadata=None,software="independent-M194b-A",description=score.CAMERA_LINEAR_DESCRIPTION)
    tifffile.imwrite(work/"unlabelled.tif",pixels,photometric="rgb",metadata=None,software="independent-M194b-A")
    try:
        score.read_tiff(work/"unlabelled.tif")
    except ValueError:
        checks["strict-reader-refuses-unlabelled-color-contract"]=True
    else:
        raise AssertionError("unlabelled TIFF admitted under strict writer contract")
    tiffs={name:score.read_tiff(work/f"{name}.tif") for name in ["base","metadata","copied","pixel"]}
    decoded,info=tiffs["base"]
    assert np.array_equal(decoded,pixels.astype(float)*14848/65535)
    assert info["pixel_sha256"]==tiffs["metadata"][1]["pixel_sha256"]
    assert info["file_sha256"]!=tiffs["metadata"][1]["file_sha256"]
    assert info["file_sha256"]==tiffs["copied"][1]["file_sha256"]
    assert info["pixel_sha256"]!=tiffs["pixel"][1]["pixel_sha256"]
    assert max(score.error(tiffs["pixel"][0],decoded,mask)["mse_dn2"])>0
    checks["actual-TIFF-normalization-file-and-pixel-mutations"]=True
    for name,fn in {
        "empty-mask":lambda:score.error(truth,truth,np.zeros_like(mask)),
        "float-mask":lambda:score.error(truth,truth,mask.astype(float)),
        "nan-rgb":lambda:score.error(truth*np.nan,truth,mask),
        "one-repeat":lambda:score.repeat_error(truth[None],truth,mask),
        "rank-deficient-waves":lambda:score.wave_response(truth,x,y,mask,[(0,0)]),
        "unsupported-color-observation":lambda:score.target("color",sx,sy,"observation"),
    }.items():
        try: fn()
        except (ValueError,np.linalg.LinAlgError): checks[name]=True
        else: checks[name]=False
    assert all(checks.values()),checks
    assert score.sha256(HERE/"score.py")==initial_hash
    result.update(schema="m194b-independent-scorer-v1",pass_=True,source_sha256=initial_hash,
                  checks={name:bool(value) for name,value in checks.items()},temporal=temporal,wave_readout=response,blur=dict(transfer=transfer,readout=blur_response),
                  tiffs={name:row[1] for name,row in tiffs.items()},
                  scope="component mathematics and TIFF decoding; final plan/receipt admission not yet tested")
    (HERE/"independent-scoring.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(pass_=True,checks=len(checks),tiffs=len(tiffs))))


if __name__=="__main__":main()
