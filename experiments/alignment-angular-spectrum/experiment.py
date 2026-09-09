"""One fixed analytic-image falsifier; root owns execution and interpretation."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, sys
import numpy as np
import scipy
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
RUNGS=(0,8,64,128,144,200,298); REFERENCE=144
R_PLANE=0.5*math.hypot(3516.0,2344.0)
N=512; NR=512; NT=256; FLOOR_RELATIVE=1e-8
ATOMS=((1.0,4.0,14.0,0.0),(.8,8.0,3.0,60.0),(.6,2.5,6.0,125.0))
ARMS=("no-blur","unequal-radial-blur","two-depth-window","radial-null","separable-spectrum-null")
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value;spec.loader.exec_module(value);return value
op=module("angular_spectrum_operator",HERE/"operator.py")
def binding(path):
    raw=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(path,value):
    with path.open("x",encoding="utf-8") as f:json.dump(value,f,indent=2,allow_nan=False);f.write("\n")


def analytic_image(scale, arm, reference):
    """Evaluate transformed Gaussian surfaces and their exact radial convolutions."""
    axis=np.arange(N,dtype=np.float32)-np.float32((N-1)/2)
    x=axis[None,:];y=axis[:,None];s=np.float32(scale)
    atoms=((1.0,6.0,6.0,0.0),) if arm=="radial-null" else ATOMS
    image=np.zeros((N,N),dtype=np.float32)
    for index,(weight,sigma1,sigma2,degrees) in enumerate(atoms):
        cx=cy=np.float32(0)
        if arm=="two-depth-window":
            cx,cy=map(np.float32,(-24,-12) if index==0 else (20,10))
            blur=(.75 if index==0 else 3.0) if reference else (3.0 if index==0 else .75)
        else:
            blur=0.0 if arm=="no-blur" else (.75 if reference else 3.0)
        theta=np.float32(degrees)*np.float32(np.pi/180)
        cosine=np.cos(theta);sine=np.sin(theta)
        dx=x-s*cx;dy=y-s*cy
        u=cosine*dx+sine*dy;v=-sine*dx+cosine*dy
        variance1=s*s*np.float32(sigma1)**np.float32(2)+np.float32(blur)**np.float32(2)
        variance2=s*s*np.float32(sigma2)**np.float32(2)+np.float32(blur)**np.float32(2)
        amplitude=np.float32(weight)*s*s/(np.float32(2*np.pi)*np.sqrt(variance1*variance2))
        image += amplitude*np.exp(np.float32(-.5)*(u*u/variance1+v*v/variance2))
    if arm=="two-depth-window":
        window=np.where(np.abs(axis)<np.float32(64),np.cos(np.float32(np.pi/128)*axis)**np.float32(2),np.float32(0))
        image *= window[:,None]*window[None,:]
    assert image.dtype==np.float32 and np.isfinite(image).all()
    return image


def separable_log_spectrum(scale, reference, radii, angles):
    """Arithmetic-only structured-angle scale-loss null, not a sampled photograph."""
    s=np.float32(scale);sigma=np.float32(.75 if reference else 3.0)
    radial=np.float32(2)*np.log(s)-np.float32(.003)*(s*radii)**np.float32(2)
    radial -= np.float32(2*np.pi*np.pi)*sigma*sigma*(radii/np.float32(N))**np.float32(2)
    angular=np.float32(.3)*np.cos(np.float32(2)*angles)+np.float32(.2)*np.sin(np.float32(4)*angles)
    result=radial[:,None]+angular[None,:]
    assert result.dtype==np.float32
    return result


def summary(rows):
    valid=[abs(row["error_m103_plane_px"]) for row in rows if row["estimate"]["accepted"]]
    return dict(rungs=len(rows),accepted=len(valid),refused=len(rows)-len(valid),
        all_rungs_accepted=len(valid)==len(rows),
        mean_abs_error_m103_plane_px=sum(valid)/len(valid) if valid else None,
        maximum_abs_error_m103_plane_px=max(valid) if valid else None,
        interior_errors={str(row["rung"]):row["error_m103_plane_px"] for row in rows if row["rung"] not in (0,298)},
        note="Refusals remain in every row and count; conditional errors cannot establish full-track accuracy.")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output-dir",type=Path,default=HERE/"run-1")
    args=parser.parse_args();out=args.output_dir.resolve();out.mkdir()
    truth_path=ROOT/"experiments/M103-halfdrift/data/truth-dense.json"
    saved=json.loads(truth_path.read_text(encoding="utf-8"))["ladder"]
    truth={j:float(saved[str(j)]["ln"]) for j in RUNGS}
    scales={j:math.exp(truth[j]-truth[REFERENCE]) for j in RUNGS}
    u=np.linspace(np.log(np.float32(4)),np.log(np.float32(64)),NR,dtype=np.float32)
    radii=np.exp(u);angles=np.arange(NT,dtype=np.float32)*np.float32(2*np.pi/NT)
    du=math.log(64/4)/(NR-1);max_shift=math.floor(.14/du)
    sources=[binding(p) for p in (Path(__file__),HERE/"operator.py",HERE/"independent-controls.py",HERE/"charter.md",truth_path)]
    plan=dict(schema="alignment-angular-spectrum-fixed-v1",rungs=RUNGS,reference=REFERENCE,
        gauge="signed log-scale error relative to rung144 times M103 CFA-plane half-diagonal",m103_plane_radius=R_PLANE,
        image_size=[N,N],polar_shape=[NR,NT],radius_range=[4,64],du=du,max_shift=max_shift,
        central_support=[max_shift,NR-max_shift],log_before_bilinear_polar=True,floor_relative=FLOOR_RELATIVE,
        arms=ARMS,atoms=ATOMS,minimum_rms_log_energy=.01,minimum_scale_information=1e-3,minimum_peak_margin=1e-3,
        truth_ln=truth,geometric_scale=scales,sources=sources,numpy=np.__version__,scipy=scipy.__version__,
        arithmetic="f32 image/descriptor and complex64 FFT; explicit f64 score reductions and gauge reporting",
        consumer="direct descriptor scale, no image NCC refinement",scope="analytic falsifier, no native decode or native-quality claim")
    save(out/"plan.json",plan)
    controls=module("angular_spectrum_independent_controls",HERE/"independent-controls.py")
    witnesses=controls.run(op)
    witnesses["gauge"]=controls.gauge_controls(truth)
    save(out/"controls.json",witnesses)
    rows=[];summaries={}
    for arm in ARMS:
        if arm=="separable-spectrum-null":
            reference_log=separable_log_spectrum(1.0,True,radii,angles)
        else:
            reference_image=analytic_image(1.0,arm,True)
            reference_log=op.log_polar(reference_image,radii,angles,FLOOR_RELATIVE)
            del reference_image
        refs={name:op.descriptor(reference_log,centred) for name,centred in (("ordinary",False),("centred",True))}
        for rung in RUNGS:
            if rung==REFERENCE:
                moving_log=reference_log
            elif arm=="separable-spectrum-null":
                moving_log=separable_log_spectrum(scales[rung],False,radii,angles)
            else:
                image=analytic_image(scales[rung],arm,False)
                moving_log=op.log_polar(image,radii,angles,FLOOR_RELATIVE)
                del image
            for name,centred in (("ordinary",False),("centred",True)):
                moving=op.descriptor(moving_log,centred)
                estimate=op.estimate_scale(refs[name],moving,du,max_shift)
                expected_ln=truth[rung]-truth[REFERENCE]
                error=(estimate["log_scale"]-expected_ln)*R_PLANE if estimate["accepted"] else None
                row=dict(arm=arm,descriptor=name,rung=rung,reference=REFERENCE,expected_scale=scales[rung],
                    expected_log_scale=expected_ln,error_m103_plane_px=error,estimate=estimate,
                    input_kind="analytic log spectrum (arithmetic null)" if arm=="separable-spectrum-null" else "direct analytic image")
                rows.append(row)
                print(json.dumps(dict(arm=arm,descriptor=name,rung=rung,accepted=estimate["accepted"],reason=estimate["reason"],error_m103_plane_px=error)),flush=True)
                del moving
        summaries[arm]={name:summary([r for r in rows if r["arm"]==arm and r["descriptor"]==name]) for name in refs}
        del refs,reference_log,moving_log
    for item in sources:
        assert binding(ROOT/item["path"])==item,"experiment source/input changed during run"
    save(out/"results.json",dict(schema="alignment-angular-spectrum-fixed-v1",status="COMPLETE_UNINTERPRETED",
        rows=rows,summaries=summaries,controls=binding(out/"controls.json"),plan=binding(out/"plan.json"),
        gauge=plan["gauge"],sources=sources,scale_only=True,final_ncc_refinement=False))

if __name__=="__main__":main()
