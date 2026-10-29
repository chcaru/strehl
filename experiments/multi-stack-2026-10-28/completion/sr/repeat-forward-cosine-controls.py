"""Frozen synthetic original-aperture leave-acquisition-out census.
No original cache reader; no product admission; all optical fields are known plants.
"""
import importlib.util,json,sys,hashlib,argparse,math,copy,concurrent.futures
from pathlib import Path
folder=Path(__file__).parent
s=importlib.util.spec_from_file_location("natural",folder/"repeat-forward-cosine.py");natural=importlib.util.module_from_spec(s);s.loader.exec_module(natural);core=natural.base;np=core.np


def pulls_for(p,case):
    true=[[v["consuming_color_pulls"][c] for v in p["sources"]] for c in range(3)]
    if case!="measured-high":
        phase=[[x,y] for y in [0.,1.] for x in [0.,2/3,4/3]]
        true=[[{"a":[1.,0.],"b":[x/2,y/2]} for x,y in phase] for _ in range(3)]
    fit=copy.deepcopy(true)
    if case=="wrong-geometry":
        for c in range(3):fit[c][5]["b"][0]+=.25
    if case=="wrong-blue-phase":fit[2][5]["b"][0]+=.5
    if case=="duplicate-phase":true=[[copy.deepcopy(x[0]) for _ in x] for x in true];fit=copy.deepcopy(true)
    if case=="one-axis":true=[[{"a":[1.,0.],"b":[j/12,0.]} for j in range(6)] for _ in range(3)];fit=copy.deepcopy(true)
    return true,fit


def expected_signal(sites,pull,full,origin,case,source,color):
    """Independent analytic sensor-square integral of continuous Fourier truth."""
    # Do not reuse inverse_sensor or spline rows in this oracle.
    a=np.array(pull["a"]);b=np.array(pull["b"]);matrix=np.array([[a[0],-a[1]],[a[1],a[0]]]);inv=np.linalg.inv(matrix);center=np.array(full)+.5
    ref=(sites-center-2*b)@inv.T+center-np.asarray(origin)
    dc=20. if case=="flat-low" else 1200.+color*180.
    if case.startswith("flat"):return np.full(len(sites),dc,dtype=np.float32)
    amplitude=2. if case=="weak" else 120.
    sigma=1.8 if case=="common-lowpass" else .8 if source==5 and (case=="unequal-psf" or (case=="blue-blur" and color==2)) else 0.
    motion=np.array([.4,.2]) if source==5 and (case=="motion" or (case=="blue-motion" and color==2)) else np.zeros(2)
    freq=([(.28,.06,1.,.3),(.08,.29,.7,1.1),(.27,-.22,.45,.7)] if color!=1 else [(.29,.25,1.,.3),(.31,-.25,.7,1.1),(.06,.28,.45,.7)])
    result=np.full(len(sites),dc)
    for fx,fy,strength,phase in freq:
        f=np.array([fx,fy]);k=2*math.pi*f
        aperture=np.prod(np.sinc(f@inv))
        optical=math.exp(-.5*sigma*sigma*(k@k))
        result+=amplitude*strength*optical*aperture*np.sin((ref+motion)@k+phase)
    if case=="drift":result+=(source-2.5)*20.
    if case=="phase-drift":result+=40*math.sin(2*math.pi*pull["b"][0])
    if case=="blue-illumination" and source==5 and color==2:result+=40
    if case=="opposite" and source==5:result=2*dc-result
    # Nonbasis low-order curvature/edge plants retain fixed-domain bias failures.
    if case=="curved":result+=.02*(ref[:,0]-80)**2+.01*(ref[:,1]-80)**2
    if case=="edge":result+=180*np.tanh((ref[:,0]+.3*ref[:,1]-80)/.8)
    return result.astype(np.float32)


def patch_job(p,case,patch):
    true,fit=pulls_for(p,case);full=p["full_quad_geometry"];center=np.array(p["positions_sensor"][patch]);side=p["fit_side_sensor"];origin=p["positions_sensor"][0]
    returned=[];footprints=[]
    for color in range(3):
        sites=[core.original_sites(pull,full,center,side,color) for pull in fit[color]]
        for source,xy in enumerate(sites):footprints.append((source,color,xy.tolist()))
        means=[expected_signal(x,pull,full,origin,case,j,color) for j,(x,pull) in enumerate(zip(sites,true[color]))]
        variance=[(p["noise_gain_dn_per_e"]*np.maximum(mu,0)+(p["noise_gain_dn_per_e"]*p["read_noise_e"])**2).astype(np.float32) for mu in means]
        aa=[natural.rows(x,pull,full,center,side,p["basis_axis"]) for x,pull in zip(sites,fit[color])]
        low=[natural.rows(x,pull,full,center,side,p["restricted_basis_axis"]) for x,pull in zip(sites,fit[color])]
        raw_by_seed={}
        for seed in p["seeds"]:
            raw=[]
            for source,(mu,var) in enumerate(zip(means,variance)):
                rng=np.random.default_rng(np.random.SeedSequence([seed,patch,color,source]))
                values=np.clip(np.rint(p["black_dn"]+mu+rng.standard_normal(len(mu)).astype(np.float32)*np.sqrt(var)),0,65535).astype(np.uint16)
                if case=="clipped" and source==5:values[:]=p["white_dn"]
                raw.append(values)
            raw_by_seed[seed]=raw
        for hold in range(6):
            train=[i for i in range(6) if i!=hold];index={tuple(x):j for j,x in enumerate(sites[hold])};hs=core.original_sites(fit[color][hold],full,center,p["score_side_sensor"],color);hi=np.array([index[tuple(x)] for x in hs])
            row={"patch":patch,"color":color,"held_acquisition":p["target_globals"][hold],"held_index":hold,"train_samples":sum(len(sites[i]) for i in train),"held_samples":len(hi)}
            try:
                at=np.concatenate([aa[i] for i in train]);ah=aa[hold][hi];vt=np.concatenate([variance[i] for i in train]);vh=variance[hold][hi]
                f=core.linear_fit(at,ah,vt,vh,p["scaled_gram_condition_max"],p["maximum_prediction_variance_to_held_variance"])
                lo=core.linear_fit(np.concatenate([low[i] for i in train]),low[hold][hi],vt,vh,p["scaled_gram_condition_max"],p["maximum_prediction_variance_to_held_variance"])
                if not f["eligible"]:raise core.Unknown("prediction variance ratio "+str(f["prediction_variance_ratio_max"]))
                native=core.native_weights([sites[i] for i in train],[fit[color][i] for i in train],full,hs,fit[color][hold],color)
                delta=f["B"]-lo["B"];covdelta=delta@delta.T
                row.update(condition=f["condition"],prediction_variance_ratio=f["prediction_variance_ratio_max"],model_reservation_bytes=f["reservation_bytes"],support=True)
                truth=means[hold][hi];train_mean=np.concatenate([means[i] for i in train]);clean=f["B"]@(train_mean/f["sigma"]);native_clean=native@train_mean
                centered_truth=truth.astype(float)-float(truth.mean());power=float(centered_truth@centered_truth)
                row["clean"]={"prediction_mse":float(np.mean((clean-truth)**2)),"native_mse":float(np.mean((native_clean-truth)**2)),"mean_bias":float(np.mean(clean-truth)),"truth_ac_power":power/len(truth),"amplitude_transfer":None if power<1e-12 else float((clean-clean.mean()).astype(float)@centered_truth/power)}
                rows=[]
                for seed,raw in raw_by_seed.items():
                    # Held support never changes its training operator or predictor.
                    training_support=all(np.all(raw[i]<p["white_dn"]) for i in train)
                    held_support=bool(np.all(raw[hold][hi]<p["white_dn"]))
                    y=np.concatenate([raw[i].astype(np.float32)-p["black_dn"] for i in train]);prediction=f["B"]@(y/f["sigma"])
                    if not training_support or not held_support:
                        rows.append({"seed":seed,"support":False,"training_support":training_support,"held_support":held_support});continue
                    observed=raw[hold][hi].astype(np.float32)-p["black_dn"]
                    whitened=np.linalg.solve(f["residual_cholesky"],observed-prediction)
                    diff=delta@(y/f["sigma"]);q=core.Quadratic();q.add(diff,covdelta)
                    rows.append({"seed":seed,"support":True,"whitened_squared_residual":float(whitened.astype(float)@whitened.astype(float)),"detail":q.result(p["envelope_t"]),"held_variance_sum":float(vh.sum()),"prediction_truth_mse":float(np.mean((prediction-truth)**2)),"native_truth_mse":float(np.mean((native@y-truth)**2)),"held_raw_mse":float(np.mean((observed-prediction)**2))})
                row["seeds"]=rows
            except core.Unknown as exc:row.update(support=False,reason=str(exc))
            returned.append(row)
    return returned,footprints


def aggregate(p,rows):
    out=[]
    for color in range(3):
        for held in p["target_globals"]:
            chosen=[v for v in rows if v["color"]==color and v["held_acquisition"]==held]
            assert len(chosen)==25
            for seed in p["seeds"]:
                r={"color":color,"held_acquisition":held,"seed":seed,"product_admission":False}
                if any(not v["support"] for v in chosen):r.update(state="Unknown",reason="geometric/model refusal",failed_patches=[v["patch"] for v in chosen if not v["support"]]);out.append(r);continue
                selected=[next(v for v in q["seeds"] if v["seed"]==seed) for q in chosen]
                if any(not v["support"] for v in selected):r.update(state="Unknown",reason="original support failure");out.append(r);continue
                count=sum(q["held_samples"] for q in chosen);q=sum(v["whitened_squared_residual"] for v in selected);iv=core.interval(q,count,count,1,p["envelope_t"])
                ds={k:sum(v["detail"][k] for v in selected) for k in ["observed","trace","frobenius2"]};ds["operator_bound"]=max(v["detail"]["operator_bound"] for v in selected);di=core.interval(ds["observed"],ds["trace"],ds["frobenius2"],ds["operator_bound"],p["envelope_t"]);vn=sum(v["held_variance_sum"] for v in selected)
                state="Unknown"
                if iv and iv[0]/count>p["whitened_mismatch_fraction"]:state="ForwardModelInconsistent"
                elif iv and iv[1]/count<=p["whitened_mismatch_fraction"] and di and di[0]>vn*p["operator_detail_signal_to_noise_lower_min"]:state="ForwardModelConsistent"
                r.update(state=state,held_samples=count,whitened_energy_per_sample=q/count,mismatch_interval_per_sample=None if iv is None else [v/count for v in iv],operator_detail_interval=di,operator_detail_noise_energy=vn,
                    prediction_truth_mse=sum(v["prediction_truth_mse"]*c["held_samples"] for v,c in zip(selected,chosen))/count,
                    native_truth_mse=sum(v["native_truth_mse"]*c["held_samples"] for v,c in zip(selected,chosen))/count)
                out.append(r)
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument("output",type=Path);ap.add_argument("case",choices=["flat-low","flat-bright","high","weak","common-lowpass","unequal-psf","blue-blur","motion","blue-motion","wrong-geometry","wrong-blue-phase","drift","phase-drift","blue-illumination","opposite","curved","edge","clipped","duplicate-phase","one-axis","measured-high"]);ap.add_argument("--workers",type=int,default=4);args=ap.parse_args();assert not args.output.exists() and 1<=args.workers<=4
    path=folder/"repeat-forward-cosine-protocol.json";p=json.loads(path.read_text());assert not p["product_admission"]
    outputs=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i,result in enumerate(pool.map(lambda j:patch_job(p,args.case,j),range(25))):outputs.append(result);print("patch",i,"complete",file=sys.stderr)
    used={};rows=[]
    for rr,fp in outputs:
        rows.extend(rr)
        for source,color,sites in fp:
            seen=used.setdefault((source,color),set());current=set(map(tuple,sites));assert not seen&current,"training/score original patch footprints overlap";seen.update(current)
    evidence=aggregate(p,rows)
    counts={}
    for e in evidence:counts[e["state"]]=counts.get(e["state"],0)+1
    sources=[Path(__file__),folder/"repeat-forward-model.py",folder/"repeat-forward-cosine.py",path]
    result={"schema":"strehl.original-forward-synthetic.v1","command":sys.argv,"case":args.case,"workers":args.workers,"numpy":np.__version__,"sources":{str(s):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},"rows":rows,"fold_seed_evidence":evidence,"counts":counts,"original_footprints_disjoint":True,"original_reads":0,"product_admission":False,"scope":"Synthetic conditional common-field hypothesis only. Known original-signal oracle variance, finite cosine boundary approximation bias retained. Six folds share training photons; do not pool as iid. No image output, FocusEvidence, physical calibration, optical resolution or real-source admission."}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8");print(json.dumps(counts))
if __name__=="__main__":main()
