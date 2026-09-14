"""Frozen RI comparison with the authorized parity-preserving boundary adapter."""
from pathlib import Path
import importlib.util
import json
import hashlib
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/"residual-interpolation-controls-1"
ADAPTER=HERE/"residual-interpolation.py"
EXPECTED="9147ee3c9a56af99654fe3e9fa7088f7e2d9cf95cd6736fc96372ced4ac2abd3"
# Root authorized reflect-pad32/crop32 with the unchanged measured-sample guard.
EXECUTION_RELEASED=True

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def save(path,value):
    with path.open("x",encoding="utf-8") as f:
        json.dump(value,f,indent=2,allow_nan=False,default=lambda v:v.item())
        f.write("\n")

def main():
    assert EXECUTION_RELEASED,"RI controls held pending known-sample guard diagnosis"
    started=time.process_time()
    assert hashlib.sha256(ADAPTER.read_bytes()).hexdigest()==EXPECTED
    base32=json.loads((HERE/"ri-baselines-trim32-1/result.json").read_text())
    base12=json.loads((HERE/"coherent-green-mhc-rb-controls-1/result.json").read_text())
    flat32=json.loads((HERE/"ri-baselines-trim32-1/flat-first.json").read_text())
    flat12=json.loads((HERE/"coherent-green-mhc-rb-controls-1/flat-first.json").read_text())
    assert base32["evaluation_trim"]==32 and len(base32["cases"])==len(base12["cases"])==48
    OUT.mkdir(exist_ok=False)
    save(OUT/"design.json",dict(status="FROZEN_BEFORE_RI",shape=[96,96],trims=[12,32],
        interpretation={12:"boundary-exposed for RI; retained old reading",32:"conservative common interior; all previous arms recomputed before RI"},
        bars="Same >5% plus >0.0005 absolute truth-RGB-RMSE regression bar. Shipped MHC and unshipped MHC-CDIFF comparisons reported separately. Chroma RMSE and green MSE retained.",
        inputs="Same 48 analytic signals, two flat colours, six fixed noise draws, alias pair and metric sabotage controls. Separate RAW-headroom integration check is not a tuned quality fixture.",
        source_sha256=EXPECTED,
        fixed_reference_units="Normalized WB CFA times255; fixed RI spatial sigma1, guided eps0, variance floor1e-5*255^2; no fitted noise and no per-image tuning.",
        boundary_check="Compare central trim32 against unpadded reference; fixed strict comparison tolerance16*f32epsilon*max(1,absolute central values). Excess is reported, not hidden by restoring samples or widening tolerance."))
    T=load("ri_fixed_truth_controls",HERE/"quincunx-controls.py")
    M=load("ri_fixed_mhc",ROOT/"experiments/M95-demosaic/src/m95dem.py")
    RI=load("ri_frozen_adapter",ADAPTER)
    def metric(rgb,truth,trim):
        T.CORE=np.s_[trim:-trim,trim:-trim]
        return T.metrics(rgb,truth)
    diagnostics=[]
    boundary_checks=[]
    def reconstruct(cfa,label):
        try:rgb=RI.ri(cfa)
        except Exception as error:
            save(OUT/"refusal.json",dict(input=label,error=repr(error),adapter_diagnostic=RI.LAST_DIAGNOSTIC))
            raise
        equal=T.identity(cfa,rgb)
        assert all(equal.values()),"candidate violated measured-sample identity"
        diagnostics.append(dict(input=label,sample_identity=equal,adapter=RI.LAST_DIAGNOSTIC))
        # Separate defensible boundary choice: unpadded published operator.
        reference_source=np.zeros((96,96,3),dtype=np.float32)
        for channel,mask in enumerate((T.R,T.G,T.B)):
            reference_source[...,channel][mask]=cfa[mask]*np.float32(255)
        direct=RI.demosaic_RI(reference_source,"rggb",np.float32(1),"RI")/np.float32(255)
        delta=np.abs(rgb[32:-32,32:-32]-direct[32:-32,32:-32])
        bound=float(16*np.finfo(np.float32).eps*max(1,float(np.max(np.abs(rgb[32:-32,32:-32]))),
                  float(np.max(np.abs(direct[32:-32,32:-32])))))
        boundary_checks.append(dict(input=label,max_abs_normalized=float(delta.max()),strict_bound_normalized=bound,
            within_strict_roundoff_comparison=bool(delta.max()<=bound),rmse=float(np.sqrt(np.mean(delta.astype(np.float64)**2)))))
        return rgb
    # FLAT FIRST. Match the original two flat colours and six independent draws.
    flats=[]
    for colour in ([.32,.32,.32],[.18,.37,.61]):
        truth=np.broadcast_to(np.array(colour,dtype=np.float32),(96,96,3)).copy()
        rgb=reconstruct(T.mosaic(truth),"flat-"+str(colour))
        for trim in (12,32):
            m=metric(rgb,truth,trim)
            flats.append(dict(colour=colour,trim=trim,metrics=m))
            assert max(abs(v) for v in m["signed_bias_rgb"])<1e-6,"frozen flat-bias bar failed"
    rng=np.random.default_rng(9132026)
    truth=np.full((96,96,3),.32,dtype=np.float32)
    cfa=T.mosaic(truth)
    wb=np.array([1.5986,1,2.709],dtype=np.float64)
    sigma=wb*np.sqrt((.32/wb)/4096+.0006**2)
    noise=[]
    for trial in range(6):
        perturb=np.zeros((96,96),dtype=np.float32)
        for c,mask in enumerate((T.R,T.G,T.B)):
            perturb[mask]=rng.normal(0,sigma[c],int(mask.sum())).astype(np.float32)
        noisy=cfa+perturb
        mhc=M.demosaic_mhc(noisy)
        for trim,baseline in ((12,flat12),(32,flat32)):
            previous=next(r for r in baseline["noise"] if r["arm"]=="mhc" and r["trial"]==trial)
            assert metric(mhc,truth,trim)==previous["metrics"],"frozen noise draw/truth changed"
        rgb=reconstruct(noisy,f"flat-noise-{trial}")
        noise.append(dict(trial=trial,input_sha256=hashlib.sha256(noisy.tobytes()).hexdigest(),
                          readings={trim:metric(rgb,truth,trim) for trim in (12,32)}))
    save(OUT/"flat-first.json",dict(noiseless=flats,noise=noise,
        noise_summary={trim:{key:float(np.mean([r["readings"][trim][key] for r in noise]))
                            for key in ("rgb_rmse","chroma_rmse","green_mse")} for trim in (12,32)},
        injected_post_wb_sigma=sigma.tolist(),scope="Synthetic operator test, not measured camera noise."))
    cases=[]
    for index,(old12,old32) in enumerate(zip(base12["cases"],base32["cases"])):
        fields=("kind","frequency","orientation","phase","fx","fy","broad_promotion_bar_applicable")
        assert all(old12[k]==old32[k] for k in fields)
        theta=2*np.pi*(old12["fx"]*T.X+old12["fy"]*T.Y)+old12["phase"]
        if old12["kind"]=="neutral":
            field=.35+.12*np.cos(theta)
            truth=np.stack((field,field,field),axis=-1).astype(np.float32)
        else:
            truth=np.stack((.42+.10*np.cos(theta+.41),np.full_like(theta,.35),
                            .29+.10*np.sin(theta-.27)),axis=-1).astype(np.float32)
        cfa=T.mosaic(truth)
        mhc=M.demosaic_mhc(cfa)
        for trim,old in ((12,old12),(32,old32)):
            assert metric(mhc,truth,trim)==old["results"]["mhc"]["metrics"],"frozen signal/truth changed"
        rgb=reconstruct(cfa,f"signal-{index}")
        row={k:old12[k] for k in fields}
        row["input_sha256"]=hashlib.sha256(cfa.tobytes()).hexdigest()
        row["readings"]={}
        for trim,old in ((12,old12),(32,old32)):
            m=metric(rgb,truth,trim)
            row["readings"][trim]=dict(ri=m,previous=old["results"],
                regresses_vs_shipped_mhc=T.regression(m["rgb_rmse"],old["results"]["mhc"]["metrics"]["rgb_rmse"]),
                regresses_vs_unshipped_mhc_cdiff=T.regression(m["rgb_rmse"],old["results"]["mhc_cdiff"]["metrics"]["rgb_rmse"]))
        cases.append(row)
    phase=.43
    hi=.35+.12*np.cos(2*np.pi*(.30*T.X+.30*T.Y)+phase)
    lo=.35-.12*np.cos(2*np.pi*(-.20*T.X-.20*T.Y)+phase)
    alias=[]
    for label,field in (("high",hi),("low",lo)):
        truth=np.repeat(field[...,None],3,axis=2).astype(np.float32)
        rgb=reconstruct(T.mosaic(truth),"alias-"+label)
        alias.append(dict(truth=label,readings={trim:dict(ri=metric(rgb,truth,trim),
            previous=old["alias_counterexample"][label+"_truth_results"])
            for trim,old in ((12,base12),(32,base32))}))
    # Re-run the same destructive metric controls at both evaluation crops.
    theta=2*np.pi*(.2*T.X)+.17
    colourful=np.stack((.4+.1*np.cos(theta),np.full_like(theta,.35),.3+.1*np.sin(theta)),axis=-1).astype(np.float32)
    neutralized=np.repeat(colourful[...,1,None],3,axis=2)
    displaced=np.roll(colourful,1,axis=1)
    power=[]
    for trim,old in ((12,base12),(32,base32)):
        neut=metric(neutralized,colourful,trim);shift=metric(displaced,colourful,trim)
        assert neut==old["negative_controls"]["neutralized_metrics"]
        assert shift==old["negative_controls"]["same_amplitude_wrong_phase_metrics"]
        assert neut["chroma_rmse"]>.03 and shift["rgb_rmse"]>.03
        power.append(dict(trim=trim,neutralized_metrics=neut,same_amplitude_wrong_phase_metrics=shift))
    # Separate integration check: actual normalized RAW-WB headroom above one.
    headroom=[]
    for colour in ([1.35,.8,1.7],[-.02,.4,1.3]):
        truth=np.broadcast_to(np.array(colour,dtype=np.float32),(96,96,3)).copy()
        rgb=reconstruct(T.mosaic(truth),"headroom-"+str(colour))
        m=metric(rgb,truth,32)
        assert rgb[...,2].max()>1.2,"reference normalization clipped RAW headroom"
        assert m["rgb_rmse"]<1e-5,"normalized constant/headroom is not preserved"
        headroom.append(dict(colour=colour,metrics=m,min_rgb=rgb.min(axis=(0,1)).tolist(),max_rgb=rgb.max(axis=(0,1)).tolist()))
    summary={}
    for trim in (12,32):
        eligible=[r for r in cases if r["broad_promotion_bar_applicable"]]
        summary[trim]=dict(shipped_mhc_regressions=sum(r["readings"][trim]["regresses_vs_shipped_mhc"] for r in eligible),
            unshipped_mhc_cdiff_regressions=sum(r["readings"][trim]["regresses_vs_unshipped_mhc_cdiff"] for r in eligible),
            only_unshipped_comparator_failures=sum(r["readings"][trim]["regresses_vs_unshipped_mhc_cdiff"] and
                not r["readings"][trim]["regresses_vs_shipped_mhc"] for r in eligible))
    assert hashlib.sha256(ADAPTER.read_bytes()).hexdigest()==EXPECTED
    save(OUT/"result.json",dict(status="RI_CONTROLS_EXECUTED",cases=cases,summary=summary,alias_pair=alias,
        power_controls=power,headroom_integration=headroom,adapter_diagnostics=diagnostics,
        boundary_checks=boundary_checks,boundary_strict_comparison_pass=all(r["within_strict_roundoff_comparison"] for r in boundary_checks),
        frozen_signals_noise_and_metric_controls_verified=True,adapter_sha256=EXPECTED,cpu_seconds=time.process_time()-started))
    print(json.dumps(summary))

if __name__=="__main__":main()
