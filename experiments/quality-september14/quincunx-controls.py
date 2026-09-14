"""Independent tiny known-truth tests; no photographs or camera calibration fit."""
from pathlib import Path
import importlib.util
import hashlib
import json
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WITH_D="--coherent-green-mhc-rb" in sys.argv
WITH_C="--coherent" in sys.argv or WITH_D
INTERIOR_32="--interior-32" in sys.argv
OUT=HERE/("coherent-green-mhc-rb-controls-1" if WITH_D else "coherent-controls-1" if WITH_C else "quincunx-controls-2")
if INTERIOR_32:OUT=HERE/"ri-baselines-trim32-1"
AUTHOR=HERE/"quincunx-chroma.py"
EXPECTED="9e8fe10dd89b54924513b1f42b212609a9586f1da72e7a7eda499225ee18b9aa"
COHERENT=HERE/"coherent-chroma.py"
COHERENT_EXPECTED="c1a91bb4ae35587fde7ce7fe44b7e33265a895545836a636d7a929d4f6432447"
N,TRIM=96,32 if INTERIOR_32 else 12
Y,X=np.mgrid[:N,:N]
R=(X%2==0)&(Y%2==0)
G=(X+Y)%2==1
B=(X%2==1)&(Y%2==1)
CORE=np.s_[TRIM:-TRIM,TRIM:-TRIM]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def save(path,value):
    def numpy_scalar(v):
        if isinstance(v,np.generic):return v.item()
        raise TypeError(type(v).__name__)
    with path.open("x",encoding="utf-8") as f:
        json.dump(value,f,indent=2,allow_nan=False,default=numpy_scalar)
        f.write("\n")

def mosaic(truth):
    a=np.empty((N,N),dtype=np.float32)
    for c,mask in enumerate((R,G,B)):a[mask]=truth[...,c][mask]
    return a

def identity(cfa,rgb):
    return {name:bool(np.array_equal(cfa[mask].view(np.uint32),rgb[...,c][mask].view(np.uint32)))
            for c,(name,mask) in enumerate(zip(("R","G","B"),(R,G,B)))}

def metrics(rgb,truth):
    error=rgb[CORE].astype(np.float64)-truth[CORE].astype(np.float64)
    chroma=np.stack((error[...,0]-error[...,1],error[...,2]-error[...,1]),axis=-1)
    return dict(rgb_rmse=float(np.sqrt(np.mean(error**2))),chroma_rmse=float(np.sqrt(np.mean(chroma**2))),
                green_mse=float(np.mean(error[...,1]**2)),signed_bias_rgb=np.mean(error,axis=(0,1)).tolist())

def regression(candidate,reference):
    # Frozen practical numerical bar: >5% increase and >0.0005 absolute RMSE.
    return candidate>reference*1.05 and candidate-reference>0.0005

def main():
    started=time.process_time()
    OUT.mkdir(exist_ok=False)
    assert hashlib.sha256(AUTHOR.read_bytes()).hexdigest()==EXPECTED
    if WITH_C:assert hashlib.sha256(COHERENT.read_bytes()).hexdigest()==COHERENT_EXPECTED
    # These bars are written before the first arm evaluation.
    save(OUT/"design.json",dict(shape=[N,N],trim=TRIM,
        invariants="All known CFA samples bit-identical; noiseless flat RGB bias max<1e-6; candidate green unchanged by arbitrary R/B replacement.",
        quality_bar="A >5% and >0.0005 absolute increase in truth RGB RMSE on a reconstructable in-band neutral or independent-chroma case blocks broad promotion. Chroma RMSE and green MSE are also reported; no amplitude-only pass.",
        power="Wrong known sample must fail identity; a neutralized genuine chromatic pattern and a one-pixel-shifted pattern must fail direct truth metrics despite attractive chroma/energy.",
        diamond_counterexample="(.30,.30) and the sign-flipped (-.20,-.20) wave coincide at green sites; reconstructed green cannot recover both. Alias must be disclosed, not excluded from results.",
        noise="Injected Gaussian sensor surrogate: g=1/4096, read_sigma=.0006 before WB, WB=(1.5986,1,2.709); same draw/calibration for every arm. It tests operators, not actual camera calibration.",
        metric_failure="RMSE may favour blur if truth itself is blurred; here analytic full RGB truth is fixed independently and phase/frequency are not fitted. Camera-coordinate chroma RMSE is not a perceptual colour metric.",
        extra_arm="D replaces only MHC green with C green, retaining MHC R/B bit-exact; all fixtures/bars retained." if WITH_D else
            "C only; all prior fixtures/bars retained. C intentionally reads R/B curvature, so green-only independence remains Q's contract; C sensitivity is recorded." if WITH_C else None))
    Q=load("independent_quincunx_author",AUTHOR)
    C=load("independent_coherent_author",COHERENT) if WITH_C else None
    mhc_path=ROOT/"experiments/M95-demosaic/src/m95dem.py"
    M=load("independent_existing_mhc",mhc_path)
    def arms(cfa):
        mhc=M.demosaic_mhc(cfa)
        result=dict(mhc=mhc,mhc_cdiff=Q.mhc_cdiff(cfa,mhc),quincunx_cdiff=Q.quincunx_cdiff(cfa))
        if C is not None:result["coherent_cdiff"]=C.coherent_cdiff(cfa)
        if WITH_D:
            d=mhc.copy()
            d[...,1]=C.coherent_green(cfa)
            assert np.array_equal(d[...,0].view(np.uint32),mhc[...,0].view(np.uint32))
            assert np.array_equal(d[...,2].view(np.uint32),mhc[...,2].view(np.uint32))
            result["coherent_green_mhc_rb"]=d
        return result
    arm_names=("mhc","mhc_cdiff","quincunx_cdiff")+(("coherent_cdiff",) if WITH_C else ())+(("coherent_green_mhc_rb",) if WITH_D else ())
    # FLAT FIRST, coloured as well as neutral; no real image consumed.
    flat_rows=[]
    flat_invariants=[]
    for colour in ([.32,.32,.32],[.18,.37,.61]):
        truth=np.broadcast_to(np.array(colour,dtype=np.float32),(N,N,3)).copy()
        cfa=mosaic(truth)
        for name,rgb in arms(cfa).items():
            row=dict(colour=colour,arm=name,metrics=metrics(rgb,truth),sample_identity=identity(cfa,rgb))
            flat_rows.append(row)
            flat_invariants.append(all(row["sample_identity"].values()) and max(abs(v) for v in row["metrics"]["signed_bias_rgb"])<1e-6)
    assert all(flat_invariants),"flat or sample invariant failed before texture tests"
    rng=np.random.default_rng(9132026)
    truth=np.full((N,N,3),.32,dtype=np.float32)
    cfa=mosaic(truth)
    wb=np.array([1.5986,1,2.709],dtype=np.float64)
    sigma=wb*np.sqrt((.32/wb)/4096+.0006**2)
    noise_rows=[]
    for trial in range(6):
        perturb=np.zeros((N,N),dtype=np.float32)
        for c,mask in enumerate((R,G,B)):
            perturb[mask]=rng.normal(0,sigma[c],int(mask.sum())).astype(np.float32)
        for name,rgb in arms(cfa+perturb).items():
            noise_rows.append(dict(trial=trial,arm=name,metrics=metrics(rgb,truth),sample_identity=identity(cfa+perturb,rgb)))
    noise_summary={name:{key:float(np.mean([r["metrics"][key] for r in noise_rows if r["arm"]==name]))
                         for key in ("rgb_rmse","chroma_rmse","green_mse")}
                   for name in arm_names}
    # Independent intervention on the channel path, not the author's helper.
    rbchanged=cfa.copy()
    rbchanged[R|B]=rng.uniform(-.4,1.4,int((R|B).sum())).astype(np.float32)
    q_delta=float(np.max(np.abs(Q.quincunx_green(cfa)[CORE]-Q.quincunx_green(rbchanged)[CORE])))
    m_delta=float(np.max(np.abs(M.demosaic_mhc(cfa)[CORE][...,1]-M.demosaic_mhc(rbchanged)[CORE][...,1])))
    c_delta=float(np.max(np.abs(C.coherent_green(cfa)[CORE]-C.coherent_green(rbchanged)[CORE]))) if WITH_C else None
    assert q_delta==0 and m_delta>.01,"green-channel independence control lacks power"
    save(OUT/"flat-first.json",dict(noiseless=flat_rows,noise=noise_rows,noise_summary=noise_summary,
        injected_post_wb_sigma=sigma.tolist(),rb_intervention=dict(quincunx_max_green_change=q_delta,mhc_max_green_change=m_delta,
            coherent_max_green_change=c_delta),
        scope="Noiseless bias separated from random noisy truth error. Signed noisy bias is finite-sample only; no camera noise claim."))
    cases=[]
    for frequency in (.08,.20,.30):
        for orientation,fx,fy in (("x",frequency,0),("y",0,frequency),
            ("diag-plus",frequency/np.sqrt(2),frequency/np.sqrt(2)),
            ("diag-minus",frequency/np.sqrt(2),-frequency/np.sqrt(2))):
            for phase in (.17,1.13):
                theta=2*np.pi*(fx*X+fy*Y)+phase
                for kind in ("neutral","independent-chroma"):
                    if kind=="neutral":
                        field=.35+.12*np.cos(theta)
                        truth=np.stack((field,field,field),axis=-1).astype(np.float32)
                    else:
                        # Genuine independently phased R and B detail, green constant.
                        truth=np.stack((.42+.10*np.cos(theta+.41),np.full_like(theta,.35),
                                        .29+.10*np.sin(theta-.27)),axis=-1).astype(np.float32)
                    a=mosaic(truth)
                    results={name:dict(metrics=metrics(rgb,truth),sample_identity=identity(a,rgb))
                             for name,rgb in arms(a).items()}
                    assert all(all(r["sample_identity"].values()) for r in results.values())
                    independently_reconstructable=kind=="neutral" or (abs(fx)<.25 and abs(fy)<.25)
                    q=results["quincunx_cdiff"]["metrics"]
                    flags={name:regression(q["rgb_rmse"],results[name]["metrics"]["rgb_rmse"])
                           for name in ("mhc","mhc_cdiff")}
                    cases.append(dict(kind=kind,frequency=frequency,orientation=orientation,phase=phase,fx=fx,fy=fy,
                        within_green_diamond=abs(fx)+abs(fy)<.5,independent_chroma_within_rb_band=abs(fx)<.25 and abs(fy)<.25,
                        broad_promotion_bar_applicable=independently_reconstructable,results=results,regresses_vs=flags))
                    if WITH_C:
                        c=results["coherent_cdiff"]["metrics"]
                        cases[-1]["coherent_regresses_vs"]={name:regression(c["rgb_rmse"],results[name]["metrics"]["rgb_rmse"])
                                                          for name in ("mhc","mhc_cdiff")}
                    if WITH_D:
                        d=results["coherent_green_mhc_rb"]["metrics"]
                        cases[-1]["coherent_green_mhc_rb_regresses_vs"]={name:regression(d["rgb_rmse"],results[name]["metrics"]["rgb_rmse"])
                                                                      for name in ("mhc","mhc_cdiff")}
    # A green-sampling alias counterexample, independent of kernel design.
    phase=.43
    hi=.35+.12*np.cos(2*np.pi*(.30*X+.30*Y)+phase)
    lo=.35-.12*np.cos(2*np.pi*(-.20*X-.20*Y)+phase)
    high=np.repeat(hi[...,None],3,axis=2).astype(np.float32)
    low=np.repeat(lo[...,None],3,axis=2).astype(np.float32)
    high_out=arms(mosaic(high));low_out=arms(mosaic(low))
    alias=dict(green_sample_difference=float(np.max(np.abs(hi[G]-lo[G]))),
        quincunx_green_output_difference=float(np.max(np.abs(high_out["quincunx_cdiff"][CORE][...,1]-low_out["quincunx_cdiff"][CORE][...,1]))),
        high_truth_results={name:metrics(v,high) for name,v in high_out.items()},
        low_truth_results={name:metrics(v,low) for name,v in low_out.items()})
    assert alias["green_sample_difference"]<1e-10 and alias["quincunx_green_output_difference"]<1e-6
    assert alias["high_truth_results"]["quincunx_cdiff"]["green_mse"]>.001,"required alias disclosure was not exercised"
    # Commission the choice of quality gate with adversarial wrong answers.
    theta=2*np.pi*(.2*X)+.17
    colourful=np.stack((.4+.1*np.cos(theta),np.full_like(theta,.35),.3+.1*np.sin(theta)),axis=-1).astype(np.float32)
    neutralized=np.repeat(colourful[...,1,None],3,axis=2)
    displaced=np.roll(colourful,1,axis=1)
    sabotaged=arms(mosaic(colourful))["quincunx_cdiff"].copy()
    sabotaged[...,0][R]+=np.float32(.02)
    power=dict(neutralized_metrics=metrics(neutralized,colourful),same_amplitude_wrong_phase_metrics=metrics(displaced,colourful),
               damaged_known_sample_identity=identity(mosaic(colourful),sabotaged))
    assert power["neutralized_metrics"]["chroma_rmse"]>.03
    assert power["same_amplitude_wrong_phase_metrics"]["rgb_rmse"]>.03
    assert not power["damaged_known_sample_identity"]["R"]
    failures=[dict(kind=r["kind"],frequency=r["frequency"],orientation=r["orientation"],phase=r["phase"],regresses_vs=r["regresses_vs"],
                   rmse={name:v["metrics"]["rgb_rmse"] for name,v in r["results"].items()})
              for r in cases if r["broad_promotion_bar_applicable"] and any(r["regresses_vs"].values())]
    c_failures=[]
    frozen_preserved=None
    if WITH_C:
        c_failures=[dict(kind=r["kind"],frequency=r["frequency"],orientation=r["orientation"],phase=r["phase"],
            regresses_vs=r["coherent_regresses_vs"],rmse={name:v["metrics"]["rgb_rmse"] for name,v in r["results"].items()})
            for r in cases if r["broad_promotion_bar_applicable"] and any(r["coherent_regresses_vs"].values())]
    if WITH_C and TRIM==12:
        # Prove the previous fixtures, metrics and decisions were not tuned.
        old=json.loads((HERE/"quincunx-controls-2/result.json").read_text())
        old_flat=json.loads((HERE/"quincunx-controls-2/flat-first.json").read_text())
        assert len(cases)==len(old["cases"])
        for prior,current in zip(old["cases"],cases):
            for key,value in prior.items():
                if key=="results":
                    assert all(current[key][name]==arm for name,arm in value.items())
                else:assert current[key]==value
        old_names=("mhc","mhc_cdiff","quincunx_cdiff")
        assert [r for r in flat_rows if r["arm"] in old_names]==old_flat["noiseless"]
        assert [r for r in noise_rows if r["arm"] in old_names]==old_flat["noise"]
        for key,value in old["alias_counterexample"].items():
            if key in ("high_truth_results","low_truth_results"):
                assert all(alias[key][name]==arm for name,arm in value.items())
            else:assert alias[key]==value
        assert power==old["negative_controls"]
        frozen_preserved=True
    d_failures=[]
    if WITH_D:
        d_failures=[dict(kind=r["kind"],frequency=r["frequency"],orientation=r["orientation"],phase=r["phase"],
            regresses_vs=r["coherent_green_mhc_rb_regresses_vs"],rmse={name:v["metrics"]["rgb_rmse"] for name,v in r["results"].items()})
            for r in cases if r["broad_promotion_bar_applicable"] and any(r["coherent_green_mhc_rb_regresses_vs"].values())]
    if WITH_D and TRIM==12:
        prior_c=json.loads((HERE/"coherent-controls-1/result.json").read_text())
        for prior,current in zip(prior_c["cases"],cases):
            for key,value in prior.items():
                if key=="results":assert all(current[key][name]==arm for name,arm in value.items())
                else:assert current[key]==value
        for name,values in prior_c["flat_summary"].items():assert noise_summary[name]==values
        for key,value in prior_c["alias_counterexample"].items():
            if key in ("high_truth_results","low_truth_results"):
                assert all(alias[key][name]==arm for name,arm in value.items())
            else:assert alias[key]==value
        assert power==prior_c["negative_controls"]
    result=dict(status="CONTROLS_EXECUTED",broad_promotion_pass=not failures,predefined_bar_failures=failures,
        cases=cases,alias_counterexample=alias,negative_controls=power,flat_summary=noise_summary,
        sources={str(AUTHOR):EXPECTED,str(mhc_path):hashlib.sha256(mhc_path.read_bytes()).hexdigest()},
        cpu_seconds=time.process_time()-started,evaluation_trim=TRIM,
        scope="Analytic operator comparison only; no RAW reads, sensor calibration validation, or image-quality claim from noise alone.")
    if WITH_C:
        assert hashlib.sha256(COHERENT.read_bytes()).hexdigest()==COHERENT_EXPECTED
        result.update(coherent_broad_promotion_pass=not c_failures,coherent_predefined_bar_failures=c_failures,
            frozen_prior_inputs_and_results_identical=frozen_preserved,coherent_rb_green_intervention_change=c_delta)
        result["sources"][str(COHERENT)]=COHERENT_EXPECTED
    if WITH_D:
        result.update(coherent_green_mhc_rb_broad_promotion_pass=not d_failures,
            coherent_green_mhc_rb_predefined_bar_failures=d_failures,
            frozen_coherent_inputs_and_results_identical=True if TRIM==12 else None,d_red_blue_bit_identical_to_mhc=True)
    assert hashlib.sha256(AUTHOR.read_bytes()).hexdigest()==EXPECTED
    save(OUT/"result.json",result)
    print(json.dumps(dict(broad_promotion_pass=not failures,failed_cases=len(failures),flat=noise_summary,
        alias_high_green_mse=alias["high_truth_results"]["quincunx_cdiff"]["green_mse"],cpu_seconds=result["cpu_seconds"],
        coherent_pass=not c_failures if WITH_C else None,coherent_failed_cases=len(c_failures),frozen_prior_results=frozen_preserved,
        coherent_green_mhc_rb_pass=not d_failures if WITH_D else None,coherent_green_mhc_rb_failed_cases=len(d_failures))))

if __name__=="__main__":main()
