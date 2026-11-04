"""Synthetic-only commissioning of the frozen original-sampling hypothesis."""
import importlib.util,json,sys,hashlib,argparse,math
from pathlib import Path
core_path=Path(__file__).with_name("repeat-forward-model.py")
spec=importlib.util.spec_from_file_location("original_forward",core_path);core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);np=core.np


def checks(protocol):
    full=protocol["full_quad_geometry"];center=np.array(protocol["positions_sensor"][0]);side=protocol["fit_side_sensor"]
    pull={"a":[1.017,.021],"b":[.31,-.27]}
    ref=np.array([[center[0]+2.3,center[1]-1.8],[center[0]-.7,center[1]+3.1]])
    # Independent absolute-sensor affine matrix, no inverse_sensor/apply_at call.
    a,b=np.array(pull["a"]),np.array(pull["b"]);matrix=np.array([[a[0],-a[1]],[a[1],a[0]]]);c=np.array(full)+.5
    source=(ref-c)@matrix.T+c+2*b
    assert np.max(np.abs(core.inverse_sensor(source,pull,full)-ref))<1e-9
    n=protocol["basis_axis"];knots=np.r_[np.zeros(4),np.arange(1,n-3)*side/(n-3),np.full(4,side)]
    greville=np.array([knots[i+1:i+4].mean() for i in range(n)])
    xx,yy=np.meshgrid(greville,greville,indexing="ij")
    constant=np.full(n*n,1200,dtype=np.float32);linear=(100+3*xx-2*yy).reshape(-1).astype(np.float32)
    counts=[]
    for color in range(3):
        sites=core.original_sites(pull,full,center,side,color);rows=core.rows(sites,pull,full,center,side,n)
        ref_oracle=(sites-c-2*b)@np.linalg.inv(matrix).T+c-center+side/2
        assert np.max(np.abs(rows@constant-1200))<.002
        assert np.max(np.abs(rows@linear-(100+3*ref_oracle[:,0]-2*ref_oracle[:,1])))<.0002
        counts.append(len(sites))
    # Exact full residual covariance, with a small independent analytic LS oracle.
    rng=np.random.default_rng(913);train=rng.normal(size=(80,4)).astype(np.float32);held=rng.normal(size=(9,4)).astype(np.float32)
    vt=np.linspace(2,4,80,dtype=np.float32);vh=np.linspace(3,5,9,dtype=np.float32)
    fitted=core.linear_fit(train,held,vt,vh)
    normal=train.astype(float).T@(train.astype(float)/vt[:,None])
    h=held.astype(float)@np.linalg.solve(normal,train.astype(float).T/vt)
    cov=h@np.diag(vt)@h.T
    assert np.max(np.abs(cov-fitted["covariance"]))<1e-5
    z=np.linalg.solve(fitted["residual_cholesky"],np.eye(9,dtype=np.float32))
    assert np.max(np.abs(z@(cov+np.diag(vh))@z.T-np.eye(9)))<1e-5
    # Held values are not an argument to fit_operator; modifying them cannot refit.
    coeff=fitted["B"].copy();training=rng.normal(size=80).astype(np.float32)
    p1=coeff@(training/fitted["sigma"]);p2=fitted["B"]@(training/fitted["sigma"])
    assert np.array_equal(p1,p2)
    try:core.linear_fit(train,held,np.zeros(80,dtype=np.float32),vh)
    except core.Unknown:pass
    else:raise AssertionError("zero variance must refuse")
    return {"pass":True,"checks":["absolute sensor inverse","all-CFA aperture partition/linear","full WLS covariance independent f64 oracle","held source excluded from predictor","zero variance refusal"],"site_counts":counts}


def pull_set(protocol,mode):
    pulls=[[v["consuming_color_pulls"][c] for v in protocol["sources"]] for c in range(3)]
    if mode=="duplicate-phase":pulls=[[dict(a=x[0]["a"],b=x[0]["b"]) for _ in x] for x in pulls]
    if mode=="one-axis":pulls=[[{"a":[1.,0.],"b":[j/12,0.]} for j in range(6)] for _ in range(3)]
    return pulls


def structural(protocol,mode):
    center=np.array(protocol["positions_sensor"][0]);full=protocol["full_quad_geometry"];side=protocol["fit_side_sensor"];pulls=pull_set(protocol,mode);out=[]
    for color in range(3):
        sites=[core.original_sites(p,full,center,side,color) for p in pulls[color]]
        a=[core.rows(x,p,full,center,side,protocol["basis_axis"]) for x,p in zip(sites,pulls[color])]
        low=[core.rows(x,p,full,center,side,protocol["restricted_basis_axis"]) for x,p in zip(sites,pulls[color])]
        for hold in range(6):
            allowed=core.original_sites(pulls[color][hold],full,center,protocol["score_side_sensor"],color)
            index={tuple(xy):i for i,xy in enumerate(sites[hold])};held_idx=[index[tuple(xy)] for xy in allowed]
            train=[i for i in range(6) if i!=hold];at=np.concatenate([a[i] for i in train]);ah=a[hold][held_idx]
            variance=np.full(len(at),276.,dtype=np.float32);vh=np.full(len(ah),276.,dtype=np.float32)
            result={"color":color,"held_acquisition":protocol["target_globals"][hold],"train_original_sites":len(at),"held_original_sites":len(ah)}
            try:
                f=core.linear_fit(at,ah,variance,vh,protocol["scaled_gram_condition_max"],protocol["maximum_prediction_variance_to_held_variance"])
                result.update({k:v for k,v in f.items() if k not in ["B","sigma","covariance","residual_cholesky"]})
                lo=core.linear_fit(np.concatenate([low[i] for i in train]),low[hold][held_idx],variance,vh,protocol["scaled_gram_condition_max"],protocol["maximum_prediction_variance_to_held_variance"])
                result["restricted_condition"]=lo["condition"]
            except core.Unknown as e:result.update(eligible=False,reason=str(e))
            out.append(result)
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument("out",type=Path);ap.add_argument("--mode",choices=["controls","structure"],required=True);a=ap.parse_args();assert not a.out.exists()
    path=Path(__file__).with_name("repeat-forward-protocol.json");pb=path.read_bytes();p=json.loads(pb)
    assert p["product_admission"] is False and len(p["target_globals"])==len(set(p["target_globals"]))==6
    assert not set(p["target_globals"])&set(p["guide_globals"])
    result={"command":sys.argv,"protocol_sha256":hashlib.sha256(pb).hexdigest(),"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"model_sha256":hashlib.sha256(core_path.read_bytes()).hexdigest(),"raw_reads":0,"product_admission":False,"controls":checks(p)}
    if a.mode=="structure":result["structural"]={mode:structural(p,mode) for mode in ["measured","duplicate-phase","one-axis"]}
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8");print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":main()
