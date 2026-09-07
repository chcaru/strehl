"""Finite preregistered numerical controls for M194b's scoped producer.

Independent expected terms use spatial disc integration, pupil overlap area,
literal midpoint/cell integration and noise moments, never M25's expected OTF.
This is author commissioning; the independent reviewer owns re-chosen checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback

import produce as p
import numpy as np
from strehl_sim import optics as opt

C = p.P["controls"]


def check(name, value, passed, *, expected=None):
    result = {"name":name,"value":value,"pass":bool(passed)}
    if expected is not None:
        result["expected"]=expected
    return result


def summarize(items, **extra):
    return {"status":"pass" if all(x["pass"] for x in items) else "fail",
            "checks":items,**extra}


def save_array(out,name,array):
    path=out/name
    np.save(path,array,allow_pickle=False)
    return {"path":name,"sha256":p.sha(path),"shape":list(array.shape),
            "dtype":str(array.dtype),"array_sha256":p.array_sha(array)}


def wb_mosaic(height,width):
    gains=np.array(p.P["sensor"]["wb"],dtype=np.float32).astype(float)
    result=np.empty((height,width))
    result[::2,::2]=gains[0]
    result[::2,1::2]=gains[1]
    result[1::2,::2]=gains[1]
    result[1::2,1::2]=gains[2]
    return result


def flat_dc(out,state):
    raw,expected,_=p.render_scalar("flat",observer="on",noise=False)
    target=np.full(expected.shape,12000.)
    target[:,::2,::2]*=.75
    target[:,1::2,1::2]*=.6
    error=float(np.max(abs(expected-target))*.25)
    info=save_array(out,"flat-dc-expected-electrons.npy",expected)
    return summarize([check("constant preserved at all nine focus/scales",error,
                            error<=C["dc_max_dn"],expected=0.0)],artifact=info,
                     raw_array_sha256=p.array_sha(raw))


def aperture_cfa_quantization(out,state):
    items=[]
    s,h,w=4,6,8
    xx=(np.arange(w*s)[None,:]+.5)/s-.5
    yy=(np.arange(h*s)[:,None]+.5)/s-.5
    ramp=3+2*xx-1.5*yy
    actual=p.sensor_module.pixel_aperture_integrate(ramp,s)
    want=3+2*np.arange(w)[None,:]-1.5*np.arange(h)[:,None]
    err=float(np.max(abs(actual-want)))
    items.append(check("affine cell midpoint",err,err<=1e-12))
    fx,fy,phase=.125,.0625,.37
    latent=np.cos(2*np.pi*(fx*xx+fy*yy)+phase)
    got=p.sensor_module.pixel_aperture_integrate(latent,s)
    reference=np.array([[sum(math.cos(2*math.pi*(fx*(x+(i+.5)/s-.5)+
        fy*(y+(j+.5)/s-.5))+phase) for j in range(s) for i in range(s))/(s*s)
        for x in range(w)] for y in range(h)])
    finite_error=float(np.max(abs(got-reference)))
    items.append(check("literal finite midpoint sum",finite_error,finite_error<=1e-12))
    finite_factor=(sum(math.cos(2*math.pi*fx*((i+.5)/s-.5)) for i in range(s))/s *
                   sum(math.cos(2*math.pi*fy*((j+.5)/s-.5)) for j in range(s))/s)
    centre=np.cos(2*np.pi*(fx*np.arange(w)[None,:]+fy*np.arange(h)[:,None])+phase)
    items.append(check("finite aperture amplitude",float(np.max(abs(got-centre*finite_factor))),
                       np.max(abs(got-centre*finite_factor))<=1e-12))
    for name,bad in (("point aperture",centre),
                     ("quad pitch aperture",centre*np.sinc(2*fx)*np.sinc(2*fy)),
                     ("omitted half-pixel phase",np.cos(2*np.pi*(fx*(np.arange(w)[None,:]+.5)+
                         fy*(np.arange(h)[:,None]+.5))+phase)*finite_factor)):
        separation=float(np.sqrt(np.mean((bad-reference)**2)))
        items.append(check(f"reject {name}",separation,separation>1e-4))
    channels=np.stack([1000*np.ones((h,w))+np.arange(h)[:,None]*10+np.arange(w)[None,:]+c*100
                       for c in range(3)],axis=-1)
    raw=p.sensor_module.mosaic(channels)
    manual=np.array([[channels[y,x,0 if y%2==0 and x%2==0 else 2 if y%2==1 and x%2==1 else 1]
                      for x in range(w)] for y in range(h)])
    items.append(check("all CFA sites independently addressed",float(np.max(abs(raw-manual))),
                       np.array_equal(raw,manual)))
    swap=p.sensor_module.mosaic(channels[...,::-1])
    items.append(check("reject R/B channel swap",float(np.max(abs(swap-manual))),np.max(abs(swap-manual))==200))
    sensor=p.configured_sensor(w,h)
    levels=np.array([0.,2.-1e-6,2.,2.+1e-6,6.,59392.,59396.])
    exposed=p.sensor_module.expose(levels,160.,sensor,None,np.random.default_rng(1),shot=False,read=False)
    wanted=np.array([512,512,512,513,514,15360,15360],dtype=np.uint16)
    items.append(check("rounding ties and saturation",exposed.tolist(),np.array_equal(exposed,wanted),
                       expected=wanted.tolist()))
    items.append(check("nonzero saturated-control rails",int(np.count_nonzero(exposed==15360)),
                       np.count_nonzero(exposed==15360)==2))
    return summarize(items,continuous_aperture_factor=float(np.sinc(fx)*np.sinc(fy)),
                     finite_midpoint_factor=finite_factor)


def disc_transfer(fx,fy,diameter,nr,nt):
    if diameter==0:
        return 1.0
    theta=2*np.pi*(np.arange(nt)+.5)/nt
    angular=fx*np.cos(theta)+fy*np.sin(theta)
    radii=(diameter/2)*np.sqrt((np.arange(nr)+.5)/nr)
    value=0.
    for part in np.array_split(radii,16):
        value+=float(np.cos(2*np.pi*part[:,None]*angular[None,:]).sum())
    return value/(nr*nt)


def pupil_overlap(normalized_frequency,n):
    v=normalized_frequency
    if v>=1:
        return 0.
    if v<=0:
        return 1.
    # Two unit discs centred at +/-v: separation 2v. Integrate vertical overlap.
    x=-1+v+(np.arange(n)+.5)*(2-2*v)/n
    halfheight=np.minimum(np.sqrt(np.maximum(0.,1-(x-v)**2)),
                          np.sqrt(np.maximum(0.,1-(x+v)**2)))
    return float(2*halfheight.sum()*(2-2*v)/n/math.pi)


def actual_coefficient(fx,fy,transfer,s=2,n=128):
    yy,xx=np.mgrid[:n,:n].astype(float)/s
    ph=2*np.pi*(fx*xx+fy*yy)+.23
    signal=20.+np.cos(ph)
    blurred=opt.blur(signal,transfer)
    coefficient=2*np.mean((blurred-20.)*np.exp(-1j*ph))
    return complex(coefficient),float(abs(blurred.mean()-20.))


def defocus_diffraction(out,state):
    items=[]; rows=[]
    n=128;s=2
    cache=opt.OtfCache((n,n),s,5.12,16.)
    q=C["quadrature"]
    for fx,fy in C["transfer_frequencies"]:
        for diameter in C["defocus_diameters"]:
            want=disc_transfer(fx,fy,diameter,q["disc_radial"],q["disc_angular"])
            refined=disc_transfer(fx,fy,diameter,q["disc_radial"]*2,q["disc_angular"]*2)
            ht=opt.defocus_otf(cache._fr,diameter)
            got,dc=actual_coefficient(fx,fy,ht)
            err=abs(got-refined)
            label=f"disc c={diameter}, f=({fx},{fy})"
            items.append(check(label,err,err<=C["transfer_absolute_error"]))
            items.append(check(label+" independent quadrature convergence",abs(want-refined),
                               abs(want-refined)<=q["max_change"]))
            items.append(check(label+" DC",dc,dc<=C["dc_max_dn"]))
            if diameter:
                bad,_=actual_coefficient(fx,fy,opt.defocus_otf(cache._fr,diameter*2))
                items.append(check(label+" reject radius/diameter",abs(bad-refined),
                                   abs(bad-refined)>C["transfer_absolute_error"]))
            if refined<-.02:
                bad,_=actual_coefficient(fx,fy,np.maximum(0.,ht))
                items.append(check(label+" reject clipped negative lobe",abs(bad-refined),
                                   abs(bad-refined)>C["transfer_absolute_error"]))
            rows.append({"kind":"disc","diameter":diameter,"frequency":[fx,fy],
                         "independent":refined,"measured":[got.real,got.imag]})
    cutoff=5.12/(.535*16.)
    for fx in (0.,.125,.375,.75):
        want=pupil_overlap(fx/cutoff,q["pupil_intervals"])
        refined=pupil_overlap(fx/cutoff,q["pupil_intervals"]*2)
        if fx==0:
            got=float(cache.diffraction(535.)[0,0]); dc=0.
        else:
            got,dc=actual_coefficient(fx,0.,cache.diffraction(535.))
        err=abs(got-refined)
        items.append(check(f"diffraction f={fx}",err,err<=C["transfer_absolute_error"]))
        items.append(check(f"pupil quadrature f={fx}",abs(want-refined),abs(want-refined)<=q["max_change"]))
        if 0<fx<cutoff:
            for name,badtransfer in (("deleted",np.ones_like(cache._fr)),
                ("double wavelength",cache.diffraction(1070.)),
                ("double effective f-number",opt.OtfCache((n,n),s,5.12,32.).diffraction(535.))):
                bad,_=actual_coefficient(fx,0.,badtransfer)
                items.append(check(f"reject diffraction {name} f={fx}",abs(bad-refined),
                                   abs(bad-refined)>C["transfer_absolute_error"]))
        z=complex(got)
        rows.append({"kind":"diffraction","frequency":fx,"independent":refined,
                     "measured":[z.real,z.imag]})
    return summarize(items,transfers=rows,scope="numerical disc/circular-pupil operations; no physical optics validation")


def rounded_normal_variance(sigma):
    cdf=lambda z:.5*(1+math.erf(z/math.sqrt(2)))
    return sum(k*k*(cdf((k+.5)/sigma)-cdf((k-.5)/sigma)) for k in range(-24,25))


def correlation(a,b):
    a=np.asarray(a,dtype=float).ravel(); b=np.asarray(b,dtype=float).ravel()
    a=a-a.mean();b=b-b.mean()
    return float(np.dot(a,b)/np.sqrt(np.dot(a,a)*np.dot(b,b)))


def noise_law(out,state):
    h,w=C["noise_shape"];n=C["noise_repeats"]
    sensor=p.configured_sensor(w,h)
    rng=np.random.default_rng(C["noise_seed"])
    items=[]; rows=[]; cubes={}
    darkvar=rounded_normal_variance(1.)
    for e in C["noise_electron_levels"]:
        raw=np.stack([p.sensor_module.expose(np.full((h,w),e),160.,sensor,None,rng,
                     shot=True,read=True,gain_dn_per_e=.25) for _ in range(n)])
        cubes[e]=raw
        expected=darkvar if e==0 else .25**2*(e+4.**2)+1/12
        tolerance=C["dark_variance_relative_error"] if e==0 else C["bright_variance_relative_error"]
        for name,(oy,ox) in {"R":(0,0),"G1":(0,1),"G2":(1,0),"B":(1,1)}.items():
            var=float(np.var(raw[:,oy::2,ox::2].astype(float),axis=0,ddof=1).mean())
            rel=abs(var/expected-1)
            items.append(check(f"noise E={e} {name}",rel,rel<=tolerance,expected=expected))
            rows.append({"electrons":e,"parity":name,"measured_variance_dn2":var,
                         "expected_variance_dn2":expected,"relative_error":rel})
        spatial=correlation(raw[:,:,:-1],raw[:,:,1:])
        temporal=correlation(raw[:-1],raw[1:])
        items.append(check(f"spatial noise null E={e}",spatial,abs(spatial)<=C["null_abs_correlation"]))
        items.append(check(f"temporal noise null E={e}",temporal,abs(temporal)<=C["null_abs_correlation"]))
    # Changed gain tested on the live exposure code path against unchanged coefficients.
    rng2=np.random.default_rng(C["noise_seed"])
    badgain=np.stack([p.sensor_module.expose(np.full((h,w),4096.),160.,sensor,None,rng2,
        shot=True,read=True,gain_dn_per_e=.5) for _ in range(n)])
    ratio=float(np.var(badgain.astype(float),axis=0,ddof=1).mean()/(.25**2*(4096+16)+1/12))
    items.append(check("reject factor-two gain",ratio,abs(ratio-1)>.01))
    noread=np.stack([p.sensor_module.expose(np.zeros((h,w)),160.,sensor,None,rng2,
        shot=True,read=False,gain_dn_per_e=.25) for _ in range(n)])
    nrv=float(np.var(noread.astype(float),axis=0,ddof=1).mean())
    items.append(check("reject absent read noise at dark",nrv,abs(nrv/darkvar-1)>.02))
    repeated=np.broadcast_to(cubes[4096.][0],cubes[4096.].shape)
    iv=float(np.var(repeated.astype(float),axis=0,ddof=1).mean())
    ic=correlation(repeated[:-1],repeated[1:])
    items.append(check("reject frame-identical variance",iv,iv==0))
    items.append(check("detect frame-identical covariance",ic,ic>=C["identical_noise_min_correlation"]))
    # Matched marginal variance, spatial correlation .25 before quantization.
    rho=C["negative_planted_correlation"]
    a=math.sqrt((1+math.sqrt(1-4*rho*rho))/2);b=rho/a
    white=rng2.normal(size=(n,h,w+1))
    correlated=np.rint(512+a*white[:,:,:-1]+b*white[:,:,1:])
    cv=float(np.var(correlated,axis=0,ddof=1).mean())
    cc=correlation(correlated[:,:,:-1],correlated[:,:,1:])
    items.append(check("matched-variance correlated control",abs(cv/darkvar-1),abs(cv/darkvar-1)<=.02))
    items.append(check("reject correlated noise",cc,cc>=C["negative_min_correlation"]))
    artifact=save_array(out,"noise-controls-dark.npy",cubes[0.])
    return summarize(items,variance_rows=rows,dark_exact_rounded_variance=darkvar,
                     bright_quantization_note="+1/12; unit-DN Gaussian read smoothing leaves <1e-7 DN2 lattice correction",
                     artifact=artifact,calibration_scope="explicit synthetic law only; coefficients shared with product are not camera calibration")


def observer(out,state):
    items=[]; scenes={}
    for scene in C["observer_scenes"]:
        variants={}; reference=None
        for mode in C["observer_modes"]:
            print(f"observer {scene} {mode}",flush=True)
            raw,expected,visits=p.render_scalar(scene,observer=mode,noise=True,seed=C["observer_seed"])
            variants[mode]=save_array(out,f"observer-{scene}-{mode}-raw.npy",raw)
            variants[mode]["visits"]=visits
            if reference is None:
                reference=raw.copy()
            items.append(check(f"{scene} {mode} byte identity",p.array_sha(raw),np.array_equal(raw,reference)))
            if mode=="on":
                info=save_array(out,f"{scene}-expected-electrons.npy",expected)
                state["cache"][scene]=info
                state["arrays"][scene]=expected
                replay=p.expose_cached(expected,seed=C["observer_seed"],noise=True)
                items.append(check(f"{scene} cached exposure replay",p.array_sha(replay),np.array_equal(replay,raw)))
                items.append(check(f"{scene} observes every frame",len(visits),len(visits)==9))
            elif mode=="placebo":
                items.append(check(f"{scene} disabled placebo every frame",len(visits),len(visits)==9 and expected is None))
        scenes[scene]=variants
    return summarize(items,scenes=scenes)


def convergence(out,state):
    if "plane" not in state["arrays"]:
        raise ValueError("commissioned expected plane unavailable")
    base=state["arrays"]["plane"]
    items=[]; variants={}
    weights=wb_mosaic(240,320)*.25
    for label,s,margin in (("s8-margin48",8,48),("s4-margin96",4,96)):
        print(f"convergence {label}",flush=True)
        raw,expected,_=p.render_scalar("plane",observer="on",noise=False,supersample=s,margin=margin)
        info=save_array(out,f"plane-{label}-expected-electrons.npy",expected)
        delta=(expected-base)*weights[None,:,:]
        roi=delta[:,64:176,64:256]
        per_frame=[float(np.sqrt(np.mean(x*x))) for x in roi]
        maxrms=max(per_frame)
        items.append(check(label+" ROI per-frame RMS DN",per_frame,maxrms<=1.0))
        info.update({"max_abs_roi_dn":float(np.max(abs(roi))),"whole_frame_rms_dn":float(np.sqrt(np.mean(delta*delta))),
                     "max_roi_frame_rms_dn":maxrms,"per_frame_roi_rms_dn":per_frame})
        variants[label]=info
    return summarize(items,variants=variants,
        effect_resolution_rule="Do not rank effects smaller than twice observed numerical difference",
        refinement="On failure retain this package; predeclared S16/margin192 requires root memory review, no auto large allocation")


def analytic_color_geometry(out,state):
    items=[]; rgb=p.analytic_color_rgb();null=p.analytic_color_rgb(chroma=False)
    items.append(check("achromatic component null",float(np.max(np.ptp(null,axis=-1))),np.max(np.ptp(null,axis=-1))==0))
    items.append(check("genuine spatial chroma present",float(np.sqrt(np.mean((rgb[...,0]-rgb[...,2])**2))),
                       np.sqrt(np.mean((rgb[...,0]-rgb[...,2])**2))>100))
    expected=p.color_electrons()
    nodes,weights=np.polynomial.legendre.leggauss(12)
    # Literal continuous radiance evaluated over transformed source sensor cells.
    cp=p.P["scenes"]["color"]
    def scalar_value(x,y,channel):
        lum=cp["dc"]+sum(a*math.cos(2*math.pi*(fx*x+fy*y)+ph) for a,fx,fy,ph in cp["luminance_waves"])
        chroma=sum(a*math.cos(2*math.pi*(fx*x+fy*y)+ph) for a,fx,fy,ph in
                   (cp["green_chroma"] if channel==1 else cp["red_blue_chroma"]))
        return lum+chroma if channel!=2 else lum-chroma
    points=[(64,64),(65,64),(64,65),(65,65),(221,143),(238,158)]
    errors=[];wrong_inverse=[];wrong_centre=[];point_sample=[]
    for k,scale in enumerate(p.P["geometry"]["scales"]):
        for x,y in points:
            channel=0 if x%2==0 and y%2==0 else 2 if x%2==1 and y%2==1 else 1
            target=0.
            for i,nx in enumerate(nodes):
                for j,ny in enumerate(nodes):
                    qx=183+(x+nx/2-183)/scale
                    qy=101+(y+ny/2-101)/scale
                    target+=weights[i]*weights[j]*scalar_value(qx,qy,channel)/4
            actual=expected[k,y,x]*.25*p.P["sensor"]["wb"][channel]
            errors.append(abs(actual-target))
            if k!=4:
                wrong_inverse.append(abs(scalar_value(183+(x-183)*scale,101+(y-101)*scale,channel)-target))
                wrong_centre.append(abs(scalar_value(160+(x-160)/scale,120+(y-120)/scale,channel)-target))
            point_sample.append(abs(scalar_value(183+(x-183)/scale,101+(y-101)/scale,channel)-target))
    items.append(check("independent integrated color/CFA at all scales",max(errors),max(errors)<1e-8))
    for name,values in (("inverse scale",wrong_inverse),("center",wrong_centre),("point sampling",point_sample)):
        items.append(check(f"reject color {name}",max(values),max(values)>1e-4))
    scales=np.array(p.P["geometry"]["scales"])
    rungs=np.array(p.P["geometry"]["rungs"])
    chord=scales[0]+(scales[-1]-scales[0])*(rungs-rungs[0])/(rungs[-1]-rungs[0])
    displacement=float(np.max(abs(scales-chord))*np.hypot(183.,139.))
    items.append(check("curvature changes interior placement",displacement,displacement>0))
    items.append(check("chord control leaves endpoints fixed",[float(chord[0]-scales[0]),float(chord[-1]-scales[-1])],
                       chord[0]==scales[0] and abs(chord[-1]-scales[-1])<1e-15))
    return summarize(items,canonical_rgb=save_array(out,"color-canonical-rgb-dn.npy",rgb),
        canonical_null=save_array(out,"color-null-canonical-rgb-dn.npy",null),
        expected=save_array(out,"color-expected-electrons.npy",expected),
        geometry_scope="Known forward map in native active frame4 gauge; independent consumer still must check actual crop and emitted TIFF")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    source_before=p.bindings()
    result={"schema":"m194b-producer-commission-v1","status":"running",
        "preregistration_sha256":p.sha(p.PREREG),"producer_sha256":p.sha(Path(p.__file__)),
        "commission_source_sha256":p.sha(Path(__file__)),"command":sys.argv,
        "source_before":source_before,"groups":{},"cache":{},
        "scope":"author numerical commissioning; independent verifier separately re-chooses"}
    state={"cache":result["cache"],"arrays":{}}
    p.write_json(args.out/"commission.json",result)
    functions=[flat_dc,aperture_cfa_quantization,defocus_diffraction,noise_law,observer,convergence,analytic_color_geometry]
    for name,fn in zip(C["run_order"],functions,strict=True):
        print(f"START {name}",flush=True)
        start=time.perf_counter()
        try:
            group=fn(args.out,state)
        except Exception as exc:
            group={"status":"error","error":repr(exc),"traceback":traceback.format_exc()}
        group["elapsed_seconds"]=time.perf_counter()-start
        result["groups"][name]=group
        p.write_json(args.out/"commission.json",result)
        print(f"END {name}: {group['status']} ({group['elapsed_seconds']:.3f}s)",flush=True)
    result["source_after"]=p.bindings()
    result["source_unchanged"]=result["source_after"]==source_before
    result["status"]="pass" if result["source_unchanged"] and all(g["status"]=="pass" for g in result["groups"].values()) else "fail"
    p.write_json(args.out/"commission.json",result)
    print(json.dumps({"status":result["status"],"out":str(args.out.resolve())}))
    raise SystemExit(0 if result["status"]=="pass" else 1)


if __name__=="__main__":
    main()
