"""Independent frozen continuous-scene checks of four residual updates."""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
from scipy.ndimage import map_coordinates
import importlib.util

HERE=Path(__file__).resolve().parent
OUT=HERE/"joint-backprojection-controls-1"
AUTHOR=HERE/"joint-cfa-backprojection.py"
EXPECTED="18de9215052d96eb959db3208ed81cace73a82050f5f96b3825a2b86b7b96f8e"
FIXTURE=HERE/"joint-cfa-controls.py"
FIXTURE_SHA="f7f68ab015a01f731585860ec3a875bc30d007185c2fb45743b12210a3842682"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    assert EXPECTED!="AWAITING_AUTHOR_FREEZE"
    start=time.process_time();OUT.mkdir(exist_ok=False)
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest()==FIXTURE_SHA
    F=load("unchanged_joint_truth",FIXTURE)
    F.save(OUT/"prospective-design.json",dict(
        scope="Native1x only. Same continuous scenes, 12 nominal signals, phase layouts, six flat conditions and injected noise draws as preceding joint controls. No RAW reads.",
        initializer="Same-data nine-MHC bilinear-gather mean, unchanged diagnostic comparator. This is not the product Catmull-Rom mean.",
        bars="Any nominal RGB or chroma truth-RMSE increase >5% AND >.0005 absolute over initializer blocks a broad quality claim. Flat RGB or chroma RMSE rise >5% is an explicit noise cost. Require at least two independent-colour signals to improve RGB RMSE >10% AND >.0005 for meaningful signal gain.",
        metric_limits="Truth error penalizes wrong phase, contrast bias and invented texture; no contrast-only or fit-residual quality score. Injected synthetic noise validates operator, not camera calibration.",
        controls="Noiseless flat first; wrong-map texture and flat placebo; same-data alias pair with two different truths; blur mismatch; exact data replication adds no information; no B data must preserve initializer B. Four updates and all parameters fixed before execution.",
        strict_support=[2,61],trim=8,source_sha256=EXPECTED,fixture_sha256=FIXTURE_SHA))
    assert hashlib.sha256(AUTHOR.read_bytes()).hexdigest()==EXPECTED
    J=load("fixed_four_updates",AUTHOR)
    M=load("existing_mhc_for_initial",F.ROOT/"experiments/M95-demosaic/src/m95dem.py")
    def initial(obs,layout):
        rgb=np.zeros((F.SIZE,F.SIZE,3),dtype=np.float32);anchor=None
        for i,((dx,dy),cfa) in enumerate(zip(F.PHASES[layout],obs["images"])):
            dev=M.demosaic_mhc(cfa)
            if i==4:anchor=dev.copy()
            for c in range(3):
                rgb[...,c]+=map_coordinates(dev[...,c],[F.Y-dy,F.X-dx],order=1,prefilter=False,mode="mirror")/np.float32(9)
        return rgb,anchor
    def solve(obs,init):
        init_before=init.copy()
        rgb,diag=J.reconstruct((F.SIZE,F.SIZE),*[obs[k] for k in ("xy","values","variance","channels","valid")],init)
        assert np.array_equal(init,init_before),"operator mutated its initializer"
        assert rgb.dtype==np.float32 and np.isfinite(rgb).all()
        expected=obs["valid"]&np.isfinite(obs["values"])&(obs["variance"]>0)&(obs["xy"][:,0]>=2)&(obs["xy"][:,1]>=2)&(obs["xy"][:,0]<F.SIZE-3)&(obs["xy"][:,1]<F.SIZE-3)
        assert np.array_equal(expected,diag["used_mask"])
        return rgb,{k:v for k,v in diag.items() if not isinstance(v,np.ndarray)}
    def compare(obs,truth,layout):
        init,anchor=initial(obs,layout);rgb,diag=solve(obs,init)
        return dict(updated=F.metrics(rgb,truth),initializer=F.metrics(init,truth),anchor_mhc=F.metrics(anchor,truth),diagnostics=diag),rgb,init
    flats=[]
    for layout in ("coincident","fractional2d"):
        truth=F.scene(F.X,F.Y,"flat",0).astype(np.float32)
        for seed in (None,1001,2003):
            row,_,_=compare(F.observations("flat",0,layout,noise_seed=seed),truth,layout)
            if seed is None:assert row["updated"]["rgb_rmse"]<1e-5
            row["noise_cost"]={key:row["updated"][key]>1.05*row["initializer"][key] for key in ("rgb_rmse","chroma_rmse")} if seed is not None else None
            flats.append(dict(layout=layout,noise_seed=seed,**row))
    F.save(OUT/"flat-first.json",flats)
    print(json.dumps(dict(flats=[{k:r[k] for k in ("layout","noise_seed","updated","initializer","noise_cost")} for r in flats])),flush=True)
    cases=[]
    for f in (.08,.20,.30):
        for orientation in ("x","oblique"):
            for kind in ("neutral","independent-colour"):
                truth=F.scene(F.X,F.Y,kind,f,orientation).astype(np.float32)
                obs=F.observations(kind,f,"fractional2d",orientation)
                assert np.array_equal(obs["images"][4],np.take_along_axis(truth,F.CHANNEL[...,None],axis=-1)[...,0])
                row,_,_=compare(obs,truth,"fractional2d")
                flags={k:row["updated"][k]>1.05*row["initializer"][k] and row["updated"][k]-row["initializer"][k]>.0005 for k in ("rgb_rmse","chroma_rmse")}
                gain=row["updated"]["rgb_rmse"]<.9*row["initializer"]["rgb_rmse"] and row["initializer"]["rgb_rmse"]-row["updated"]["rgb_rmse"]>.0005
                cases.append(dict(kind=kind,frequency=f,orientation=orientation,regression_vs_initializer=flags,meaningful_rgb_gain=gain,**row))
    prior=json.loads((HERE/"joint-cfa-controls-3/result.json").read_text())
    for before,after in zip(prior["nominal_cases"],cases,strict=True):
        assert before["nine_mhc_mean"]==after["initializer"] and before["anchor_mhc"]==after["anchor_mhc"]
    prior_flats=json.loads((HERE/"joint-cfa-controls-3/flat-first.json").read_text())
    for before,after in zip(prior_flats,flats,strict=True):
        assert before["nine_mhc_mean"]==after["initializer"] and before["anchor_mhc"]==after["anchor_mhc"]
    phase_rows=[]
    truth=F.scene(F.X,F.Y,"independent-colour",.30).astype(np.float32)
    for layout in F.PHASES:
        row,_,_=compare(F.observations("independent-colour",.30,layout),truth,layout)
        phase_rows.append(dict(layout=layout,**row))
    correct=F.observations("independent-colour",.30,"fractional2d")
    row,correct_rgb,init=compare(correct,truth,"fractional2d")
    wrong=dict(correct);wrong["xy"]=correct["xy"].copy()
    for k,(dx,dy) in enumerate(F.PHASES["fractional2d"]):wrong["xy"][k*F.SIZE**2:(k+1)*F.SIZE**2]-=np.array([2*dx,2*dy])
    wrong_rgb,wrong_diag=solve(wrong,init)
    blur_row,_,_=compare(F.observations("independent-colour",.30,"fractional2d",blur_mismatch=True),truth,"fractional2d")
    flat=F.observations("flat",0,"fractional2d");flat_init,_=initial(flat,"fractional2d")
    flat_right,_=solve(flat,flat_init);flat["xy"]=wrong["xy"]
    flat_wrong,_=solve(flat,flat_init)
    flat_delta=float(np.max(np.abs(flat_wrong[F.CORE]-flat_right[F.CORE])))
    assert flat_delta<1e-6
    alias_hi=F.observations("r-only",.30,"coincident","x")
    alias_lo=F.observations("r-only",.30,"coincident","x",alias_low=True)
    assert np.array_equal(alias_hi["values"],alias_lo["values"])
    alias_init,_=initial(alias_hi,"coincident")
    high,_=solve(alias_hi,alias_init);low,_=solve(alias_lo,alias_init)
    assert np.array_equal(high,low)
    alias=dict(high_truth=F.metrics(high,F.scene(F.X,F.Y,"r-only",.30,"x").astype(np.float32)),
        low_truth=F.metrics(low,F.scene(F.X,F.Y,"r-only",.30,"x",alias_low=True).astype(np.float32)),inputs_and_outputs_identical=True)
    assert max(alias["high_truth"]["rgb_rmse"],alias["low_truth"]["rgb_rmse"])>.02
    duplicated={k:np.concatenate((correct[k],correct[k])) for k in ("xy","values","variance","channels","valid")}
    twice,_=solve(duplicated,init)
    duplicate_delta=float(np.max(np.abs(twice[F.CORE]-correct_rgb[F.CORE])))
    assert duplicate_delta<2e-6,"exact data replication changed fixed updates beyond f32 rounding"
    absent=dict(correct);absent["valid"]=correct["valid"]&(correct["channels"]!=2)
    absent_rgb,absent_diag=solve(absent,init)
    assert np.array_equal(absent_rgb[...,2],init[...,2])
    failures=[{k:r[k] for k in ("kind","frequency","orientation","regression_vs_initializer")} for r in cases if any(r["regression_vs_initializer"].values())]
    gains=sum(r["kind"]=="independent-colour" and r["meaningful_rgb_gain"] for r in cases)
    mismatch=dict(correct=F.metrics(correct_rgb,truth),wrong_map=F.metrics(wrong_rgb,truth),blur_mismatch=blur_row,
        wrong_map_diagnostics=wrong_diag,wrong_map_flat_placebo_max_delta=flat_delta)
    mismatch["wrong_map_falsifier_exercised"]=mismatch["wrong_map"]["rgb_rmse"]>max(mismatch["correct"]["rgb_rmse"]*1.25,mismatch["correct"]["rgb_rmse"]+.002)
    F.save(OUT/"result.json",dict(nominal_cases=cases,nominal_bar_failures=failures,meaningful_independent_colour_gain_cases=gains,
        phase_cases=phase_rows,mismatch=mismatch,coincident_alias=alias,exact_duplication_max_delta=duplicate_delta,
        no_blue_observations_initializer_preserved=True,unsupported_channel_diagnostic=absent_diag,
        initializer_anchor_and_noise_metrics_exactly_preserved=True,source_sha256=EXPECTED,cpu_seconds=time.process_time()-start))
    assert hashlib.sha256(AUTHOR.read_bytes()).hexdigest()==EXPECTED
    print(json.dumps(dict(nominal_failures=len(failures),meaningful_independent_colour_gains=gains,
        wrong_map_exercised=mismatch["wrong_map_falsifier_exercised"],cpu_seconds=time.process_time()-start)),flush=True)

if __name__=="__main__":main()
