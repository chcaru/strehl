"""Independent geometric integrals for the declared M25 numerical model.

Expected values contain no Bessel or closed-form diffraction OTF. This is
component commissioning, not a camera PSF calibration or full producer result.
"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
M25=ROOT/"experiments/m25-simulator/src"
sys.path.insert(0,str(M25))
from strehl_sim import optics as subject


def integral(fun,a,b,n):
    x,w=np.polynomial.legendre.leggauss(n)
    q=a+(x+1)*(b-a)/2
    return float(np.dot(w,fun(q))*(b-a)/2)


def pupil_overlap(f,cutoff,n=512):
    # Two radius1 pupils separated by2rho. Four congruent lens quarters,
    # each bounded by x in[rho,1], y in[0,sqrt(1-x*x)]. Normalize by pi.
    rho=abs(float(f))/cutoff
    if rho>=1: return 0.0
    return 4/np.pi*integral(lambda x:np.sqrt(np.maximum(0,1-x*x)),rho,1,n)


def disc_cosine(f,diameter,n=512):
    # Marginal area of the unit disc at x is2sqrt(1-x*x). Fourier phase
    # uses radius=diameter/2 in sensor-pixel units, keeping its sign.
    return 2/np.pi*integral(lambda x:np.sqrt(np.maximum(0,1-x*x))*np.cos(np.pi*diameter*f*x),-1,1,n)


def main():
    cutoff=5.12/(0.535*16)
    frequencies=np.array([0,.02,.08,.16,.29,.5,cutoff,cutoff*1.1])
    rows=[]
    for diameter in [0.,4.,12.]:
        for f in frequencies:
            d=disc_cosine(f,diameter)
            p=pupil_overlap(f,cutoff)
            convergence=max(abs(d-disc_cosine(f,diameter,256)),abs(p-pupil_overlap(f,cutoff,256)))
            actual_d=float(subject.defocus_otf(np.array([f]),diameter)[0])
            actual_p=float(subject.diffraction_otf(np.array([f]),cutoff)[0])
            assert convergence<=1e-5
            assert abs(actual_d-d)<=.002 and abs(actual_p-p)<=.002
            rows.append(dict(frequency=float(f),diameter=diameter,disc_integral=d,pupil_integral=p,
                             actual_disc=actual_d,actual_pupil=actual_p,quadrature_change=convergence))
    assert any(r["disc_integral"]<-.05 for r in rows), "negative lobe was never exercised"
    controls={}
    for name in ["disc-radius-substitution","absolute-disc","deleted-diffraction","doubled-aperture","changed-wavelength"]:
        errors=[]
        for r in rows:
            f,d=r["frequency"],r["diameter"]
            if name=="disc-radius-substitution":
                got=float(subject.defocus_otf(np.array([f]),d*2)[0]); expected=r["disc_integral"]
            elif name=="absolute-disc":
                got=abs(r["actual_disc"]); expected=r["disc_integral"]
            elif name=="deleted-diffraction":
                got=1.; expected=r["pupil_integral"]
            else:
                wrong_cutoff=cutoff/2 if name=="doubled-aperture" else 5.12/(.610*16)
                got=float(subject.diffraction_otf(np.array([f]),wrong_cutoff)[0]); expected=r["pupil_integral"]
            errors.append(abs(got-expected))
        assert max(errors)>.002, f"{name} had no power to fail"
        controls[name]=dict(max_absolute_error=max(errors),rejected=True)
    # Re-chosen periodic asymmetric grid/phase. The product FFT blur is the
    # subject; expected field comes directly from the geometric integrals.
    h,w,s=288,384,4
    y,x=np.mgrid[:h*s,:w*s]
    qx=(x+.5)/s-48-.5
    qy=(y+.5)/s-48-.5
    waves=[(1/12,1/24,.73,1800.),(1/16,-1/8,-.46,900.)]
    image=np.full(qx.shape,12000.)
    for fx,fy,phase,amp in waves:
        image+=amp*np.cos(2*np.pi*(fx*qx+fy*qy)+phase)
    cache=subject.OtfCache(image.shape,s,5.12,16)
    periodic=[]
    for diameter in [0.,4.,12.]:
        actual=subject.blur(image,cache.total(diameter,535,True))
        expected=np.full(image.shape,12000.)
        for fx,fy,phase,amp in waves:
            f=float(np.hypot(fx,fy))
            gain=disc_cosine(f,diameter)*pupil_overlap(f,cutoff)
            expected+=amp*gain*np.cos(2*np.pi*(fx*qx+fy*qy)+phase)
        rms=float(np.sqrt(np.mean((actual-expected)**2)))
        # The declared field is electrons; normalized fixed-color DN uses0.25.
        assert rms*.25<=.5
        periodic.append(dict(diameter=diameter,rms_electrons=rms,rms_dn=rms*.25,
                             dc_error_electrons=float(actual.mean()-12000.)))
    source=M25/"strehl_sim/optics.py"
    evidence=dict(schema="m194b-independent-optics-v1",pass_=True,
                  scope="declared scalar numerical OTF and FFT component only; not full producer or camera",
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  grid=dict(active=[288,192],margin=48,supersample=4),
                  rows=rows,negative_controls=controls,periodic=periodic)
    (HERE/"independent-optics.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps(dict(pass_=True,point_checks=len(rows),negative_controls=len(controls),periodic=periodic)))


if __name__=="__main__": main()
